"""Integration test: export OTPSecure.proof and verify EasyCrypt accepts it."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from proof_frog.export.easycrypt import exporter
from proof_frog.export.easycrypt_per_transform import (
    exporter as per_transform_exporter,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"
OTP_PROOF = REPO_ROOT / "examples" / "joy" / "Proofs" / "Ch2" / "OTPSecure.proof"
OTP_LR_PROOF = REPO_ROOT / "examples" / "joy" / "Proofs" / "Ch2" / "OTPSecureLR.proof"
CES_PROOF = EXAMPLES / "joy" / "Proofs" / "Ch2" / "ChainedEncryptionSecure.proof"
EC_SCRIPT = REPO_ROOT / "scripts" / "easycrypt.sh"


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def test_export_otpsecure_produces_nonempty_output() -> None:
    """Smoke test: exporter runs and produces a file with some EC constructs."""
    output = exporter.export_proof_file(str(OTP_PROOF))
    assert "require import" in output
    assert "module" in output
    assert "lemma" in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_otpsecure_typechecks_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: exported .ec file must type-check in EasyCrypt."""
    output = exporter.export_proof_file(str(OTP_PROOF))
    ec_file = tmp_path / "otpsecure.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected exported file.\n"
        f"Exported file:\n{output}\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}\n"
    )


def test_export_otpsecurelr_produces_expected_structure() -> None:
    """Smoke test for the reductions/multi-game proof."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    # Two game files -> two oracle module types.
    assert "module type OneTimeSecrecy_Oracle" in output
    assert "module type OneTimeSecrecyLR_Oracle" in output
    # Both game sides per game file.
    assert "module OneTimeSecrecy_Real" in output
    assert "module OneTimeSecrecy_Random" in output
    assert "module OneTimeSecrecyLR_Left" in output
    assert "module OneTimeSecrecyLR_Right" in output
    # Two reductions as parameterized modules.
    assert "module R1" in output
    assert "module R2" in output
    # Inlining hops emit an equiv lemma; assumption hops do not (their
    # two sides are genuinely non-equivalent). Plus one _pr lemma per hop.
    # OTPSecureLR: 3 inlining + 2 assumption hops -> 3 equiv + 5 pr = 8.
    assert output.count("lemma hop_") == 8


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_otpsecurelr_typechecks_in_easycrypt(tmp_path: Path) -> None:
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    ec_file = tmp_path / "otpsecurelr.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected exported file.\n"
        f"Exported file:\n{output}\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}\n"
    )


def test_export_otpsecure_per_transform_produces_chain_lemmas() -> None:
    """Per-transform exporter emits per-transform micro-lemmas and a chain
    alongside the standard per-hop EC structure (OTP scheme module,
    game-step wrappers, main theorem)."""
    output = per_transform_exporter.export_proof_file_per_transform(str(OTP_PROOF))
    # Standard per-hop EC structure still emitted.
    assert "module OTP : E_c.Scheme" in output
    assert "module Game_step_0" in output
    assert "module Game_step_1" in output
    # Per-transform chain modules named Step_<i>L/R_state_<k>.
    assert "module Step_0L_state_" in output
    assert "module Step_0R_state_" in output
    # Per-transform micro-lemmas + chain lemma.
    assert "lemma micro_0_left_0" in output  # Remove Redundant Copies
    assert "lemma micro_0_left_2" in output  # Uniform XOR Simplification
    assert "lemma canon_bridge_0" in output
    assert "lemma hop_0_chain" in output


def test_export_otpsecure_per_transform_no_admit() -> None:
    """Per-transform export of OTPSecure must close every micro-lemma."""
    output = per_transform_exporter.export_proof_file_per_transform(str(OTP_PROOF))
    assert "admit" not in output, (
        f"Per-transform OTPSecure export still contains admit:\n{output}"
    )


def test_export_otpsecure_per_transform_xor_tactic_uses_diff() -> None:
    """The XOR transform's parametric tactic must reference the actual
    offset and bitstring type from the AST diff."""
    output = per_transform_exporter.export_proof_file_per_transform(str(OTP_PROOF))
    # Slot values for OTPSecure: offset=m, type-suffix=lambda.
    assert "rnd (fun z => xor_lambda z m{2})" in output
    assert "smt(xor_lambda_invol dbs_lambda_fu)" in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_otpsecure_per_transform_typechecks_in_easycrypt(
    tmp_path: Path,
) -> None:
    """End-to-end: per-transform export of OTPSecure must type-check in EC."""
    output = per_transform_exporter.export_proof_file_per_transform(str(OTP_PROOF))
    ec_file = tmp_path / "otpsecure_per_transform.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected per-transform exported file.\n"
        f"Exported file:\n{output}\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}\n"
    )


def test_export_otpsecurelr_per_transform_emits_reductions_and_axioms() -> None:
    """Per-transform export of OTPSecureLR must produce the same standard
    EC infrastructure as per-hop mode: reduction modules, reduction-as-
    adversary lifts, cloned ``*_advantage`` axiom, and axiom-discharged
    assumption hops — and add per-transform chain artifacts on top.
    """
    output = per_transform_exporter.export_proof_file_per_transform(str(OTP_LR_PROOF))
    # Reductions appear as first-class EC modules.
    assert "module R1 (" in output
    assert "module R2 (" in output
    assert "module R1_Adv (" in output
    assert "module R2_Adv (" in output
    # Cloned advantage axiom is available.
    assert "OneTimeSecrecy_advantage" in output
    # Assumption hops are discharged by axiom appeals, not admits.
    assert "E_c.OneTimeSecrecy_advantage OTP (R1_Adv(A)) &m" in output
    assert "E_c.OneTimeSecrecy_advantage OTP (R2_Adv(A)) &m" in output
    # Per-transform chain artifacts are emitted for the 3
    # interchangeability hops.
    assert "lemma hop_0_chain" in output
    assert "lemma hop_2_chain" in output
    assert "lemma hop_4_chain" in output
    # No admits left in the unified pipeline.
    assert "admit" not in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_otpsecurelr_per_transform_typechecks_in_easycrypt(
    tmp_path: Path,
) -> None:
    """End-to-end: per-transform export of OTPSecureLR must type-check in EC.

    Two ``admit.``s remain (the assumption hops); EC still accepts the
    file because ``admit.`` is a legal proof script.
    """
    output = per_transform_exporter.export_proof_file_per_transform(str(OTP_LR_PROOF))
    ec_file = tmp_path / "otpsecurelr_per_transform.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected per-transform OTPSecureLR.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}\n"
    )


def test_export_chained_encryption_per_transform_produces_chain_lemmas() -> None:
    """Per-transform export of ChainedEncryptionSecure must produce the
    full chain skeleton — flat-state modules parametrized over E1/E2,
    micro-lemmas, canon bridges, and per-hop chain lemmas — for each
    of the three interchangeability hops. Verifies that the multi-module
    strengthening (``={m, glob E1, glob E2}``-style specs, ``proc; sp;
    wp; sim.`` canned tactic, ``swap{n}`` permutation tactics for
    inline-style transforms that reorder, and ``byequiv (_: ... ==>
    ...)``-strengthened ``hop_<i>_pr`` proofs) is emitted. The 6
    expected residual admits — 3 × ``Topological Sorting``, 1 ×
    ``Merge Product Samples``, 2 × multi-module assumption hops — are
    documented in
    ``extras/docs/plans/done/2026-05-23-per-transform-shared-translators.md``.
    """
    output = per_transform_exporter.export_proof_file_per_transform(str(CES_PROOF))
    # Standard per-hop EC structure still emitted.
    assert "module ChainedEncryption" in output
    assert "module Game_step_0" in output
    # Flat-state modules are parameterized over the declared instances.
    assert "module Step_0L_state_0 (E1 : E1_c.Scheme, E2 : E2_c.Scheme)" in output
    assert "module Step_0R_state_0 (E1 : E1_c.Scheme, E2 : E2_c.Scheme)" in output
    # Each interchangeability hop has a chain lemma.
    assert "lemma hop_0_chain" in output
    assert "lemma hop_2_chain" in output
    assert "lemma hop_4_chain" in output
    # Module-call statements use the shared statement translator's
    # ``<@`` form (was previously a crash in ``_render_stmt``).
    assert "<@ E1.keygen()" in output
    assert "<@ E2.enc(" in output
    # Product distribution sampling emits ``dA `*` dB`` (Merge Product
    # Samples brings the canonical state here even though the lemma
    # discharging the merge itself still admits).
    assert "`*`" in output
    # Multi-module strengthening: the micro-lemmas, the per-hop chain
    # lemma, and the outer ``hop_<i>`` equiv lemma all include the
    # declared-module ``glob`` equalities in their pre/post.
    assert "={m, glob E1, glob E2}" in output
    assert "={res, glob E1, glob E2}" in output
    # Inline-style canned tactic for multi-module bodies is
    # ``proc; sp; wp; sim.`` (not the single-instance ``proc; sp; auto.``).
    assert "proc; sp; wp; sim." in output
    # ``Inline Single-Use Variables`` reorders adjacent statements in
    # multi-module mode; the exporter detects the permutation and
    # emits the corresponding ``swap{1}`` tactic.
    assert "swap{1}" in output
    # ``hop_<i>_pr`` lemmas use the strengthened ``byequiv`` precondition
    # (``={glob A, glob E1, glob E2}``) so the inner ``conseq hop_<i>``
    # can unify with the strengthened spec.
    assert "byequiv (_: ={glob A, glob E1, glob E2} ==> ={res})" in output
    # The adversary ``call`` propagates the declared-module invariant
    # (``={glob E1, glob E2}``) into the oracle subgoal.
    assert "call (_: ={glob E1, glob E2})" in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_chained_encryption_per_transform_typechecks_in_easycrypt(
    tmp_path: Path,
) -> None:
    """EC verification of per-transform CES.

    The inline-style canned tactics handle abstract module calls in
    multi-module proofs (strengthened ``={glob ...}`` specs, ``proc; sp;
    wp; sim.``, and ``swap{n}`` permutations for reordering transforms).
    EC accepts the file with the 6 documented admits remaining (3 ×
    ``Topological Sorting`` permutation extraction, 1 × ``Merge Product
    Samples`` parametric synthesis, 2 × multi-module assumption hops);
    EC stops at the first ``admit`` so we expect a non-zero exit but no
    ``cannot save an incomplete proof`` / ``[by]: cannot close goals``
    style errors *before* the first admit.
    """
    output = per_transform_exporter.export_proof_file_per_transform(str(CES_PROOF))
    ec_file = tmp_path / "ces_per_transform.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    combined = result.stderr + result.stdout
    assert "parse error" not in combined, (
        f"EC parse error in per-transform CES output:\nstderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}"
    )
    # All non-admit lemmas now close — exit 0 — guarding against any
    # regression in the inline-style canned-tactic robustness work.
    assert result.returncode == 0, (
        f"EC verification failed (exit {result.returncode}); inline-style "
        f"micro-lemmas or _pr lemmas may have regressed.\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout[-2000:]}"
    )


def test_export_otpsecure_lemma_has_no_admit() -> None:
    """OTPSecure's one hop must be discharged with real tactics."""
    output = exporter.export_proof_file(str(OTP_PROOF))
    assert "admit" not in output, (
        f"OTPSecure export still contains admit:\n{output}"
    )


def test_export_otpsecurelr_no_admit() -> None:
    """OTPSecureLR has 5 hops; after Phase 4a, all are discharged in probability form."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    assert "admit" not in output, (
        f"OTPSecureLR export still contains admit:\n{output}"
    )


def test_export_otpsecurelr_emits_advantage_axiom() -> None:
    """The exported file declares the Style B assumption axiom."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    assert "op eps_OneTimeSecrecy : real." in output
    assert "axiom eps_OneTimeSecrecy_pos" in output
    assert "axiom OneTimeSecrecy_advantage" in output


def test_export_otpsecurelr_emits_pr_lemmas() -> None:
    """One probability corollary per hop (5 hops -> 5 _pr lemmas)."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    # 3 inlining-hop equiv lemmas + 5 _pr lemmas = 8. Assumption hops get
    # no equiv lemma (their two sides are genuinely non-equivalent).
    assert output.count("lemma hop_") == 8
    for i in range(5):
        assert f"lemma hop_{i}_pr" in output


def test_export_otpsecurelr_emits_main_theorem() -> None:
    """The exported file declares a chained main_theorem lemma."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    assert "lemma main_theorem" in output
    # Bound: two assumption hops, each contributing eps_OneTimeSecrecy,
    # now qualified through the clone alias E.
    assert "E_c.eps_OneTimeSecrecy + E_c.eps_OneTimeSecrecy" in output
    # Endpoints: step_0 (Game_OTSLR_Left) and step_5 (Game_OTSLR_Right).
    assert "Pr[Game_step_0(A).main() @ &m : res]" in output
    assert "Pr[Game_step_5(A).main() @ &m : res] |" in output


def test_export_otpsecurelr_uses_theory_and_clone() -> None:
    """The exported file wraps the primitive/games in an abstract theory
    and instantiates it via clone for the scheme."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    assert "abstract theory SymEnc_Theory." in output
    assert "end SymEnc_Theory." in output
    assert "clone SymEnc_Theory as E_c" in output
    # Scheme implements the cloned Scheme module type.
    assert "module OTP : E_c.Scheme" in output
    # Adversary / oracle types are qualified externally through the clone.
    assert "E_c.OneTimeSecrecyLR_Adv" in output
    assert "E_c.OneTimeSecrecy_Oracle" in output
    # Axiom and epsilon are referenced through the clone alias.
    assert "E_c.eps_OneTimeSecrecy" in output
    assert "E_c.OneTimeSecrecy_advantage" in output


def test_export_chained_encryption_per_transform_uses_tactic_cache() -> None:
    """With the CES sidecar checked in, the per-transform export must
    consume the cached Topological Sorting tactics — no ``tactic-cache
    miss`` blocks for that transform should remain.

    Today the only residual cache miss is the ``Merge Product Samples``
    micro-lemma (intentionally deferred); the 2 multi-module assumption
    hops admit via a different path (no diagnostic comment).
    """
    output = per_transform_exporter.export_proof_file_per_transform(str(CES_PROOF))
    miss_blocks = output.count("tactic-cache miss")
    # The Topological Sorting cache entries should resolve; only Merge
    # Product Samples (1 lemma) is allowed to remain a miss.
    assert miss_blocks <= 1, (
        f"Expected ≤1 cache misses (Merge Product Samples only); got "
        f"{miss_blocks}.\n{output}"
    )
    # And no Topological Sorting block should appear in a miss
    # diagnostic — they must all be Layer-2 hits now.
    for block_start in range(len(output)):
        idx = output.find("tactic-cache miss", block_start)
        if idx == -1:
            break
        block = output[idx : idx + 500]
        assert "Topological Sorting" not in block, (
            f"Topological Sorting cache lookup unexpectedly missed:\n{block}"
        )
        block_start = idx + 1


def test_export_otpsecure_per_transform_no_layer2_consultation() -> None:
    """OTPSecure's per-transform export must close every micro at
    Layer 1 — no cache lookups should appear in the requested-key list.
    Guards against accidental fall-through to Layer 2/3 if a Layer-1
    canned tactic key gets dropped from the bucket map.
    """
    # pylint: disable=import-outside-toplevel
    from proof_frog.export.easycrypt import exporter as ec_exporter

    ec_exporter.export_proof_file(str(OTP_PROOF), "per-transform")
    keys = getattr(ec_exporter, "_last_requested_cache_keys", [])
    assert keys == [], (
        f"OTPSecure unexpectedly consulted the tactic cache "
        f"({len(keys)} key(s)) — every micro should close at Layer 1."
    )


def test_export_chained_encryption_emits_set_abstract_types() -> None:
    """Set let-bindings in CES become top-level EC type decls (abstract or alias)."""
    output = exporter.export_proof_file(str(CES_PROOF))
    for ty in (
        "IntermediateSpace",
        "KeySpace1",
        "KeySpace2",
        "MessageSpace",
        "CiphertextSpace1",
        "CiphertextSpace2",
    ):
        assert f"type {ty}." in output or f"type {ty} =" in output, (
            f"missing `type {ty}` in:\n{output}"
        )


def test_export_chained_encryption_does_not_crash() -> None:
    """ChainedEncryptionSecure exports without raising."""
    output = exporter.export_proof_file(str(CES_PROOF))
    assert "module" in output  # sanity: got some EC output
    # Two distinct assumption hops; each produces an eps term.
    assert "eps_OneTimeSecrecy" in output
