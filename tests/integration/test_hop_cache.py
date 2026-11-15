"""End-to-end behaviour of the opt-in verified-hop cache (`prove --cache`)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from proof_frog import hop_cache, proof_engine, visitors

FIXTURES = Path(__file__).parent / "hop_cache_fixtures"
REPO_ROOT = Path(__file__).parents[2]
EXAMPLES = REPO_ROOT / "examples"

# One proof per engine path the cache sits on: plain reductions, an
# induction (entry, inner, rollover hops), step assumptions, and a lemma.
SAMPLE_PROOFS = [
    "Proofs/SymEnc/ModOTP_INDOT.proof",
    "Proofs/PubKeyEnc/HybridKEMDEM_INDCPA_MultiChal.proof",
    "Proofs/PRG/CounterPRG_PRGSecurity.proof",
    "Proofs/PubKeyEnc/INDCPA_implies_INDCPA_MultiChal.proof",
    "Proofs/KEM/HashedElGamalKEM_INDCCA.proof",
]


def _prove(
    proof: Path,
    cache: hop_cache.HopCache | None,
    verbosity: proof_engine.Verbosity = proof_engine.Verbosity.QUIET,
) -> proof_engine.ProofEngine:
    # pylint: disable=protected-access
    _, engine = proof_engine._verify_proof_file_with_engine(
        str(proof), verbosity=verbosity, hop_cache=cache
    )
    return engine


def _verdicts(engine: proof_engine.ProofEngine) -> list[tuple[int, int, str, bool]]:
    return [(r.step_num, r.depth, r.kind, r.valid) for r in engine.hop_results]


def _equivalence_hops(
    engine: proof_engine.ProofEngine,
) -> list[proof_engine.HopResult]:
    return [
        r for r in engine.hop_results if r.kind in ("equivalent", "induction_rollover")
    ]


@pytest.fixture(name="workdir")
def workdir_fixture(tmp_path: Path) -> Path:
    target = tmp_path / "proofs"
    shutil.copytree(FIXTURES, target)
    return target


@pytest.fixture(name="in_process_pool")
def in_process_pool_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """Take the parallel code path without spawning processes."""
    monkeypatch.delenv("PROOFFROG_SEQUENTIAL", raising=False)

    def run(
        _self: proof_engine.ProofEngine,
        equiv_indices: list[int],
        tasks: list[proof_engine._EquivalenceTask],
    ) -> dict[int, proof_engine.EquivalenceResult]:
        # pylint: disable=protected-access
        return {
            idx: proof_engine._check_equivalent_worker(task)
            for idx, task in zip(equiv_indices, tasks)
        }

    monkeypatch.setattr(proof_engine.ProofEngine, "_run_tasks_in_pool", run)


def test_second_run_reuses_every_equivalence_hop(
    workdir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    proof = workdir / "twice.proof"
    cold = _prove(proof, hop_cache.HopCache(tmp_path / "cache"))
    assert not any(r.cached for r in cold.hop_results)
    assert "cached" not in capsys.readouterr().out

    warm_cache = hop_cache.HopCache(tmp_path / "cache")
    warm = _prove(proof, warm_cache)
    assert all(r.cached for r in _equivalence_hops(warm))
    assert warm_cache.hits == len(_equivalence_hops(warm)) == 1
    assert _verdicts(warm) == _verdicts(cold)
    out = capsys.readouterr().out
    assert "ok (cached)" in out
    assert "1 equivalence hop(s) not re-checked" in out


def test_without_a_cache_nothing_is_reused_or_written(
    workdir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(hop_cache.ENV_DIR, str(tmp_path / "cache"))
    for _ in range(2):
        engine = _prove(workdir / "twice.proof", None)
        assert not any(r.cached for r in engine.hop_results)
    assert not (tmp_path / "cache").exists()


def test_dropping_a_deterministic_annotation_misses_the_cache(
    workdir: Path, tmp_path: Path
) -> None:
    # The hop holds only because Fn.Eval is `deterministic`. The annotation
    # lives in the primitive, not in either inlined game, so a key built from
    # the games alone would wrongly reuse the earlier verdict.
    proof = workdir / "twice.proof"
    _prove(proof, hop_cache.HopCache(tmp_path / "cache"))
    primitive = workdir / "Fn.primitive"
    source = primitive.read_text()
    assert "deterministic " in source
    primitive.write_text(source.replace("deterministic ", ""))

    with pytest.raises(proof_engine.FailedProof):
        _prove(proof, hop_cache.HopCache(tmp_path / "cache"))


def test_editing_a_game_misses_the_cache(workdir: Path, tmp_path: Path) -> None:
    proof = workdir / "twice.proof"
    _prove(proof, hop_cache.HopCache(tmp_path / "cache"))
    game = workdir / "Twice.game"
    game.write_text(game.read_text().replace("return [y, z];", "return [z, y];"))
    engine = _prove(proof, hop_cache.HopCache(tmp_path / "cache"))
    assert not any(r.cached for r in engine.hop_results)


def test_a_failed_hop_is_never_cached(workdir: Path, tmp_path: Path) -> None:
    primitive = workdir / "Fn.primitive"
    primitive.write_text(primitive.read_text().replace("deterministic ", ""))
    for _ in range(2):
        cache = hop_cache.HopCache(tmp_path / "cache")
        with pytest.raises(proof_engine.FailedProof):
            _prove(workdir / "twice.proof", cache)
        assert cache.hits == 0
    assert not list((tmp_path / "cache").glob("hops-*.txt"))


def test_a_different_engine_rechecks(
    workdir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prove(workdir / "twice.proof", hop_cache.HopCache(tmp_path / "cache"))
    monkeypatch.setattr(hop_cache, "_ENGINE_FINGERPRINT", "0" * 64)
    engine = _prove(workdir / "twice.proof", hop_cache.HopCache(tmp_path / "cache"))
    assert not any(r.cached for r in engine.hop_results)


def test_verbose_runs_recheck_and_print_the_games(
    workdir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _prove(workdir / "twice.proof", hop_cache.HopCache(tmp_path / "cache"))
    capsys.readouterr()
    engine = _prove(
        workdir / "twice.proof",
        hop_cache.HopCache(tmp_path / "cache"),
        proof_engine.Verbosity.NORMAL,
    )
    assert not any(r.cached for r in engine.hop_results)
    assert "Inline Success!" in capsys.readouterr().out


@pytest.mark.parametrize("parallel", [False, True])
@pytest.mark.parametrize("proof", SAMPLE_PROOFS)
def test_cached_and_uncached_runs_agree(
    proof: str,
    parallel: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    path = EXAMPLES / proof
    if not path.exists():
        pytest.skip("examples submodule not checked out")
    if parallel:
        request.getfixturevalue("in_process_pool")
    else:
        monkeypatch.setenv("PROOFFROG_SEQUENTIAL", "1")

    plain = _prove(path, None)
    cold = _prove(path, hop_cache.HopCache(tmp_path))
    warm = _prove(path, hop_cache.HopCache(tmp_path))

    assert _verdicts(cold) == _verdicts(plain)
    assert _verdicts(warm) == _verdicts(plain)
    assert not any(r.cached for r in plain.hop_results + cold.hop_results)
    assert _equivalence_hops(warm)
    assert all(r.cached for r in _equivalence_hops(warm))
    # Only equivalence hops are ever served from the cache.
    assert warm.advantage_bound is not None and plain.advantage_bound is not None
    assert str(warm.advantage_bound.substituted_expression()) == str(
        plain.advantage_bound.substituted_expression()
    )


def _cli(args: list[str], cache_dir: Path, enable: str | None) -> str:
    env = {k: v for k, v in os.environ.items() if k != hop_cache.ENV_ENABLE}
    env[hop_cache.ENV_DIR] = str(cache_dir)
    env["PROOFFROG_SEQUENTIAL"] = "1"
    if enable is not None:
        env[hop_cache.ENV_ENABLE] = enable
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_cli_cache_is_off_by_default_and_opt_in(tmp_path: Path) -> None:
    proof = str(FIXTURES / "twice.proof")
    cache_dir = tmp_path / "cache"

    for _ in range(2):
        assert "cached" not in _cli([proof], cache_dir, None)
    assert not cache_dir.exists()

    assert "cached" not in _cli(["--cache", proof], cache_dir, None)
    assert "cached" in _cli(["--cache", proof], cache_dir, None)
    assert "cached" in _cli([proof], cache_dir, "1")
    assert "cached" not in _cli(["--no-cache", proof], cache_dir, "1")
    assert "cached" not in _cli([proof], cache_dir, None)


def _parallel_example() -> Path:
    path = EXAMPLES / "Proofs/PubKeyEnc/HybridKEMDEM_INDCPA_MultiChal.proof"
    if not path.exists():
        pytest.skip("examples submodule not checked out")
    return path


@pytest.mark.usefixtures("in_process_pool")
def test_pool_verdicts_from_a_different_engine_are_not_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A pool worker imports the engine afresh; if the sources changed in the
    # meantime, its verdicts belong to different code and must not be stored.
    real = proof_engine._check_equivalent_worker  # pylint: disable=protected-access

    def other_engine(
        task: proof_engine._EquivalenceTask,  # pylint: disable=protected-access
    ) -> proof_engine.EquivalenceResult:
        result = real(task)
        assert result.engine_fingerprint is not None
        result.engine_fingerprint = "0" * 64
        return result

    monkeypatch.setattr(proof_engine, "_check_equivalent_worker", other_engine)
    path = _parallel_example()
    _prove(path, hop_cache.HopCache(tmp_path))
    warm = _prove(path, hop_cache.HopCache(tmp_path))
    assert not any(r.cached for r in warm.hop_results)


@pytest.mark.usefixtures("in_process_pool")
def test_pool_task_with_separate_let_types_is_not_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The worker reads `task.proof_let_types` besides the context's copy, but
    # the key covers only the context; a task where the two differ is skipped.
    real = proof_engine.ProofEngine._make_task  # pylint: disable=protected-access

    def separate(
        self: proof_engine.ProofEngine, hop: object
    ) -> proof_engine._EquivalenceTask:  # pylint: disable=protected-access
        task = real(self, hop)  # type: ignore[arg-type]
        task.proof_let_types = task.proof_let_types + visitors.NameTypeMap()
        return task

    monkeypatch.setattr(proof_engine.ProofEngine, "_make_task", separate)
    path = _parallel_example()
    _prove(path, hop_cache.HopCache(tmp_path))
    assert not list(tmp_path.glob("hops-*.txt"))
