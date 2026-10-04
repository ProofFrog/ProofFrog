"""The hop cache's digest must cover everything an equivalence verdict reads.

A digest that leaves an input out would let a stale "verified" through, so
these tests change each input in turn and require a different key, and check
that a value the serializer does not know disables caching (fail-closed).
"""

import dataclasses
import hashlib
from pathlib import Path

import pytest
import sympy

from proof_frog import frog_ast, frog_parser, hop_cache, proof_engine
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _digest(obj: object) -> str:
    h = hashlib.sha256()
    hop_cache._feed(h, obj)  # pylint: disable=protected-access
    return h.hexdigest()


def _game(body: str, name: str = "G") -> frog_ast.Game:
    return frog_parser.parse_game(f"Game {name}() {{ {body} }}")


def _ctx(**overrides: object) -> PipelineContext:
    let_types = NameTypeMap()
    let_types.set("n", frog_ast.IntType())
    base: dict[str, object] = {
        "variables": {"n": sympy.Symbol("n")},
        "proof_let_types": let_types,
        "proof_namespace": {"n": None},
        "subsets_pairs": [],
    }
    base.update(overrides)
    return PipelineContext(**base)  # type: ignore[arg-type]


LEFT = _game("Int f() { return 1; }")
RIGHT = _game("Int f() { Int x = 1; return x; }")


def _key(cache: hop_cache.HopCache, ctx: PipelineContext | None = None) -> str:
    key = cache.key(ctx if ctx is not None else _ctx(), LEFT, RIGHT, [])
    assert key is not None
    return key


@pytest.fixture(name="cache")
def cache_fixture(tmp_path: Path) -> hop_cache.HopCache:
    return hop_cache.HopCache(tmp_path)


# --- structural digest -------------------------------------------------


def test_digest_ignores_source_positions() -> None:
    a = _game("Int f() { return 1; }")
    b = _game("\n\n   Int f() {\n return 1;\n }")
    assert a == b
    assert _digest(a) == _digest(b)


def test_digest_distinguishes_values_that_print_alike() -> None:
    assert _digest(1) != _digest("1")
    assert _digest(True) != _digest(1)
    assert _digest(None) != _digest("None")
    assert _digest(["ab", "c"]) != _digest(["a", "bc"])
    assert _digest([[1], 2]) != _digest([1, [2]])
    assert _digest(frog_ast.Variable("x")) != _digest("x")


def test_digest_distinguishes_uniq_surface_forms() -> None:
    # `x <-uniq[S] T` (adds the draw to S) and `x <- T \ S` are different
    # constructs that compare unequal; they must not share a digest.
    stateful = _game(
        "Set<BitString<8>> S; Void f() { BitString<8> x <-uniq[S] BitString<8>; }"
    )
    pure = _game(
        "Set<BitString<8>> S; Void f() { BitString<8> x <- BitString<8> \\ S; }"
    )
    assert stateful != pure
    assert _digest(stateful) != _digest(pure)


def test_digest_of_a_set_is_order_independent() -> None:
    assert _digest({("a", "b"), ("c", "d")}) == _digest({("c", "d"), ("a", "b")})
    assert _digest({"a": 1, "b": 2}) == _digest({"b": 2, "a": 1})
    assert _digest({"a": 1, "b": 2}) != _digest({"a": 2, "b": 1})


def test_digest_distinguishes_lists_from_tuples() -> None:
    assert _digest([1, 2]) != _digest((1, 2))


def test_digest_refuses_unknown_types() -> None:
    with pytest.raises(hop_cache.Uncacheable):
        _digest(object())
    with pytest.raises(hop_cache.Uncacheable):
        _digest([1, 2.5])


# --- the hop key covers every input ------------------------------------


def test_key_is_stable(cache: hop_cache.HopCache) -> None:
    assert _key(cache) == _key(cache)


def test_key_depends_on_each_game_and_their_order(cache: hop_cache.HopCache) -> None:
    other = _game("Int f() { return 2; }")
    base = cache.key(_ctx(), LEFT, RIGHT, [])
    assert cache.key(_ctx(), other, RIGHT, []) != base
    assert cache.key(_ctx(), LEFT, other, []) != base
    assert cache.key(_ctx(), RIGHT, LEFT, []) != base


def test_key_depends_on_step_assumptions(cache: hop_cache.HopCache) -> None:
    def assumption(text: str, which: proof_engine.WhichGame) -> object:
        return proof_engine.ProcessedAssumption(
            assumption=frog_parser.parse_expression(text), which=which
        )

    current, nxt = proof_engine.WhichGame.CURRENT, proof_engine.WhichGame.NEXT
    keys = {
        cache.key(_ctx(), LEFT, RIGHT, []),
        cache.key(_ctx(), LEFT, RIGHT, [assumption("x < 3", current)]),
        cache.key(_ctx(), LEFT, RIGHT, [assumption("x < 4", current)]),
        cache.key(_ctx(), LEFT, RIGHT, [assumption("x < 3", nxt)]),
    }
    assert None not in keys
    assert len(keys) == 4


def test_key_depends_on_every_context_input(cache: hop_cache.HopCache) -> None:
    bits = frog_ast.BitStringType(frog_ast.Variable("n"))
    other_types = NameTypeMap()
    other_types.set("n", frog_ast.IntType())
    other_types.set("H", frog_ast.FunctionType(bits, bits))
    requirement = frog_ast.StructuralRequirement(
        "prime", frog_ast.FieldAccess(frog_ast.Variable("G"), "order")
    )
    variants = {
        "variables": {"n": frog_ast.Integer(4)},
        "proof_let_types": other_types,
        "proof_namespace": {"n": None, "S": bits},
        "subsets_pairs": [(bits, frog_ast.Variable("S"))],
        "equality_pairs": {("A", "B")},
        "max_calls": 3,
        "sampled_let_names": {"H"},
        "requirements": [requirement],
        "pinned_fields": {"field1"},
    }
    # Every PipelineContext field is either varied here or a declared
    # non-input, so a new field cannot be added without extending this test.
    non_inputs = (
        hop_cache._CONTEXT_FIELDS_NOT_INPUTS  # pylint: disable=protected-access
    )
    assert set(variants) | non_inputs == {
        f.name for f in dataclasses.fields(PipelineContext)
    }
    base = _key(cache)
    for name, value in variants.items():
        assert _key(cache, _ctx(**{name: value})) != base, name


def test_key_sees_a_method_annotation_in_the_namespace(
    cache: hop_cache.HopCache,
) -> None:
    # `has_nondeterministic_call` reads the `deterministic` modifier from the
    # namespace; the inlined games do not mention it.
    primitive = frog_ast.FileType.PRIMITIVE
    with_det = frog_parser.parse_string(
        "Primitive P() { deterministic Int F(Int x); }", primitive
    )
    without = frog_parser.parse_string("Primitive P() { Int F(Int x); }", primitive)
    assert _key(cache, _ctx(proof_namespace={"P": with_det})) != _key(
        cache, _ctx(proof_namespace={"P": without})
    )


def test_unknown_context_value_disables_caching(cache: hop_cache.HopCache) -> None:
    ctx = _ctx()
    ctx.pinned_fields = object()  # type: ignore[assignment]
    assert cache.key(ctx, LEFT, RIGHT, []) is None
    assert not cache.lookup(None)
    cache.add(None)  # a no-op, not an error


# --- the store ---------------------------------------------------------


def test_added_keys_persist_for_the_same_engine(tmp_path: Path) -> None:
    first = hop_cache.HopCache(tmp_path)
    key = _key(first)
    assert not first.lookup(key)
    first.add(key)
    second = hop_cache.HopCache(tmp_path)
    assert second.lookup(key)
    assert second.hits == 1


def test_a_different_engine_does_not_see_the_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = hop_cache.HopCache(tmp_path)
    key = _key(first)
    first.add(key)
    monkeypatch.setattr(hop_cache, "_ENGINE_FINGERPRINT", "f" * 64)
    other = hop_cache.HopCache(tmp_path)
    assert not other.lookup(key)
    assert _key(other) != key


def test_engine_fingerprint_covers_the_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "pkg"
    (package / "transforms").mkdir(parents=True)
    (package / "hop_cache.py").write_text("x = 1\n")
    (package / "transforms" / "a.py").write_text("y = 1\n")
    monkeypatch.setattr(hop_cache, "__file__", str(package / "hop_cache.py"))

    def fingerprint() -> str:
        monkeypatch.setattr(hop_cache, "_ENGINE_FINGERPRINT", None)
        return hop_cache.engine_fingerprint()

    before = fingerprint()
    assert fingerprint() == before
    (package / "transforms" / "a.py").write_text("y = 2\n")
    assert fingerprint() != before


def test_malformed_cache_lines_are_ignored(tmp_path: Path) -> None:
    cache = hop_cache.HopCache(tmp_path)
    key = _key(cache)
    cache.add(key)
    path = next(tmp_path.glob("hops-*.txt"))
    path.write_text(f"garbage\n{key[:40]}\n{key.upper()}\n\n{key}\n")
    reloaded = hop_cache.HopCache(tmp_path)
    assert reloaded.lookup(key)
    assert not reloaded.lookup("garbage")
    assert len(reloaded._known) == 1  # pylint: disable=protected-access


def test_unwritable_cache_directory_is_not_an_error(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("")
    cache = hop_cache.HopCache(blocker / "sub")
    key = _key(cache)
    cache.add(key)
    assert cache.lookup(key)  # still usable within this run


def test_open_hop_cache_is_off_unless_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(hop_cache.ENV_DIR, str(tmp_path))
    monkeypatch.delenv(hop_cache.ENV_ENABLE, raising=False)
    assert hop_cache.open_hop_cache(None) is None
    assert hop_cache.open_hop_cache(True) is not None
    monkeypatch.setenv(hop_cache.ENV_ENABLE, "1")
    assert hop_cache.open_hop_cache(None) is not None
    assert hop_cache.open_hop_cache(False) is None
    for off in ("0", "false", "no", "off", "", "maybe"):
        monkeypatch.setenv(hop_cache.ENV_ENABLE, off)
        assert hop_cache.open_hop_cache(None) is None, off
    for on in ("1", "true", "YES", " on "):
        monkeypatch.setenv(hop_cache.ENV_ENABLE, on)
        assert hop_cache.open_hop_cache(None) is not None, on



def _fake_key(index: int) -> str:
    return hashlib.sha256(str(index).encode()).hexdigest()


def test_cache_file_is_trimmed_to_its_newest_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hop_cache, "_MAX_ENTRIES", 10)
    monkeypatch.setattr(hop_cache, "_TRIM_TO", 4)
    cache = hop_cache.HopCache(tmp_path)
    for index in range(10):
        cache.add(_fake_key(index))
    path = next(tmp_path.glob("hops-*.txt"))
    assert len(path.read_text().split()) == 10  # at the limit, not over it

    cache.add(_fake_key(10))
    assert path.read_text().split() == [_fake_key(i) for i in range(7, 11)]
    assert not list(tmp_path.glob("*.tmp"))
    # This run still knows every hop it verified; a fresh run sees the kept ones.
    assert cache.lookup(_fake_key(0))
    reloaded = hop_cache.HopCache(tmp_path)
    assert not reloaded.lookup(_fake_key(6))
    assert reloaded.lookup(_fake_key(7)) and reloaded.lookup(_fake_key(10))

    # Counting restarts from the trimmed size.
    for index in range(11, 17):
        cache.add(_fake_key(index))
    assert len(path.read_text().split()) == 10


def test_trim_keeps_entries_appended_by_another_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hop_cache, "_MAX_ENTRIES", 5)
    monkeypatch.setattr(hop_cache, "_TRIM_TO", 3)
    mine = hop_cache.HopCache(tmp_path)
    other = hop_cache.HopCache(tmp_path)
    for index in range(4):
        mine.add(_fake_key(index))
    other.add(_fake_key(100))  # another run appending to the same file
    other.add(_fake_key(3))  # `other` did not load it, so it is written twice
    mine.add(_fake_key(4))  # file now has 7 lines; `mine` counted 5 -> no trim
    mine.add(_fake_key(5))  # `mine` counts 6 -> trim, re-reading the file
    path = next(tmp_path.glob("hops-*.txt"))
    assert path.read_text().split() == [_fake_key(3), _fake_key(4), _fake_key(5)]


# --- only verdicts of the fingerprinted engine are recorded --------------


def test_verdict_from_another_engine_is_not_recorded(tmp_path: Path) -> None:
    cache = hop_cache.HopCache(tmp_path)
    key = _key(cache)
    cache.add(key, verified_by="0" * 64)
    cache.add(key, verified_by="")  # a worker that could not fingerprint itself
    assert not cache.lookup(key)
    cache.add(key, verified_by=cache.fingerprint)
    assert cache.lookup(key)


def test_sources_changed_during_the_run_stop_all_recording(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = hop_cache.HopCache(tmp_path)
    first = _fake_key(1)
    cache.add(first)
    monkeypatch.setattr(hop_cache, "_fingerprint_sources", lambda: "e" * 64)
    cache.add(_fake_key(2))
    monkeypatch.undo()
    cache.add(_fake_key(3))  # stays off for the rest of the run
    reloaded = hop_cache.HopCache(tmp_path)
    assert reloaded.lookup(first)
    assert not reloaded.lookup(_fake_key(2))
    assert not reloaded.lookup(_fake_key(3))
