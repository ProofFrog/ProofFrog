"""Integration tests for the EasyCrypt exporter.

The exporter always emits a per-transform canonicalization chain for
each interchangeability hop. There is a single export entry point
(``proof_frog.export.easycrypt.exporter.export_proof_file``); tests
cover the structural shape of its output and end-to-end EC acceptance.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from proof_frog.export.easycrypt import exporter


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"
OTP_PROOF = REPO_ROOT / "examples" / "joy" / "Proofs" / "Ch2" / "OTPSecure.proof"
OTP_LR_PROOF = REPO_ROOT / "examples" / "joy" / "Proofs" / "Ch2" / "OTPSecureLR.proof"
CES_PROOF = EXAMPLES / "joy" / "Proofs" / "Ch2" / "ChainedEncryptionSecure.proof"
TPRG_PROOF = REPO_ROOT / "examples" / "Proofs" / "PRG" / "TriplingPRG_PRGSecurity.proof"
PRG_5_8_A_PROOF = REPO_ROOT / "examples" / "joy_old" / "5_Exercises" / "5_8_a.proof"
PRG_5_8_B_PROOF = REPO_ROOT / "examples" / "joy_old" / "5_Exercises" / "5_8_b.proof"
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


# ---------------------------------------------------------------------------
# OTPSecure (single-instance, single-hop, no reductions)
# ---------------------------------------------------------------------------


def test_export_otpsecure_produces_chain_and_closes() -> None:
    """OTPSecure export emits the standard structure (scheme module,
    game-step wrappers) plus the per-transform chain (flat-state modules,
    micro-lemmas, ``hop_<i>_chain`` lemma), and closes every micro-lemma
    with no admits. Also pins that the XOR transform's parametric tactic
    references the actual offset and bitstring type from the AST diff.
    """
    output = exporter.export_proof_file(str(OTP_PROOF))
    # Basic EC scaffolding.
    assert "require import" in output
    assert "module" in output
    assert "lemma" in output
    # Standard EC structure.
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
    # XOR parametric tactic uses the actual offset (m) and type (lambda).
    assert "rnd (fun z => xor_lambda z m{2})" in output
    assert "smt(xor_lambda_invol dbs_lambda_fu)" in output
    # Every micro-lemma closes.
    assert "admit" not in output


def test_export_otpsecure_no_layer2_consultation() -> None:
    """OTPSecure must close every micro at Layer 1 — no cache lookups
    should appear in the requested-key list. Guards against accidental
    fall-through to Layer 2/3 if a Layer-1 canned tactic key gets dropped
    from the bucket map.
    """
    exporter.export_proof_file(str(OTP_PROOF))
    keys = getattr(exporter, "_last_requested_cache_keys", [])
    assert keys == [], (
        f"OTPSecure unexpectedly consulted the tactic cache "
        f"({len(keys)} key(s)) — every micro should close at Layer 1."
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_otpsecure_typechecks_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: OTPSecure export must type-check in EasyCrypt."""
    output = exporter.export_proof_file(str(OTP_PROOF))
    ec_file = tmp_path / "otpsecure.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected exported file.\n"
        f"Exported file:\n{output}\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}\n"
    )


# ---------------------------------------------------------------------------
# OTPSecureLR (single-instance, multiple hops, reductions, assumption hops)
# ---------------------------------------------------------------------------


def test_export_otpsecurelr_produces_expected_structure() -> None:
    """Per-transform OTPSecureLR export emits:

    * The full theory wrap + clone for the SymEnc primitive
      (``abstract theory SymEnc_Theory`` / ``clone SymEnc_Theory as E_c``).
    * Module types and game modules for both game files (the inner
      ``OneTimeSecrecy`` assumption game plus the outer
      ``OneTimeSecrecyLR`` game).
    * Both reductions (``R1``, ``R2``) and their adversary lifts
      (``R1_Adv``, ``R2_Adv``).
    * The cloned ``OneTimeSecrecy_advantage`` axiom plus ``eps`` op and
      positivity axiom.
    * Per-hop probability lemmas (``hop_<i>_pr`` for each of the 5
      hops) and a chained main theorem with the expected bound and
      endpoints.
    * Assumption hops discharged by axiom appeals (not admits).
    * Per-transform chain artifacts for each of the 3 interchangeability
      hops.
    """
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    # Theory wrap + clone.
    assert "abstract theory SymEnc_Theory." in output
    assert "end SymEnc_Theory." in output
    assert "clone SymEnc_Theory as E_c" in output
    assert "module OTP : E_c.Scheme" in output
    assert "E_c.OneTimeSecrecyLR_Adv" in output
    assert "E_c.OneTimeSecrecy_Oracle" in output
    # Oracle module types for both game files.
    assert "module type OneTimeSecrecy_Oracle" in output
    assert "module type OneTimeSecrecyLR_Oracle" in output
    # Both sides of each game.
    assert "module OneTimeSecrecy_Real" in output
    assert "module OneTimeSecrecy_Random" in output
    assert "module OneTimeSecrecyLR_Left" in output
    assert "module OneTimeSecrecyLR_Right" in output
    # Reductions + adversary lifts.
    assert "module R1" in output
    assert "module R2" in output
    assert "module R1_Adv (" in output
    assert "module R2_Adv (" in output
    # Cloned advantage axiom + eps op + positivity axiom.
    assert "op eps_OneTimeSecrecy : real." in output
    assert "axiom eps_OneTimeSecrecy_pos" in output
    assert "axiom OneTimeSecrecy_advantage" in output
    assert "E_c.eps_OneTimeSecrecy" in output
    assert "E_c.OneTimeSecrecy_advantage" in output
    # Assumption hops discharged by axiom appeals, not admits.
    assert "E_c.OneTimeSecrecy_advantage OTP (R1_Adv(A)) &m" in output
    assert "E_c.OneTimeSecrecy_advantage OTP (R2_Adv(A)) &m" in output
    # Per-hop probability lemmas: one per hop (5 hops -> 5 _pr lemmas).
    for i in range(5):
        assert f"lemma hop_{i}_pr" in output
    # Main theorem with the expected bound and endpoints.
    assert "lemma main_theorem" in output
    assert "E_c.eps_OneTimeSecrecy + E_c.eps_OneTimeSecrecy" in output
    assert "Pr[Game_step_0(A).main() @ &m : res]" in output
    assert "Pr[Game_step_5(A).main() @ &m : res] |" in output
    # Per-transform chain artifacts for the 3 interchangeability hops.
    assert "lemma hop_0_chain" in output
    assert "lemma hop_2_chain" in output
    assert "lemma hop_4_chain" in output
    # No admits left.
    assert "admit" not in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_otpsecurelr_typechecks_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: OTPSecureLR export must type-check in EC."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    ec_file = tmp_path / "otpsecurelr.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected OTPSecureLR.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}\n"
    )


# ---------------------------------------------------------------------------
# ChainedEncryptionSecure (multi-instance, multi-module)
# ---------------------------------------------------------------------------


def test_export_chained_encryption_produces_chain_lemmas() -> None:
    """ChainedEncryptionSecure export produces the full chain skeleton —
    flat-state modules parametrized over E1/E2, micro-lemmas, canon
    bridges, and per-hop chain lemmas — for each of the three
    interchangeability hops. Verifies the multi-module strengthening
    (``={m, glob E1, glob E2}``-style specs, ``proc; sp; wp; sim.``
    canned tactic, ``swap{n}`` permutation tactics for inline-style
    transforms that reorder, and ``byequiv (_: ... ==> ...)``-strengthened
    ``hop_<i>_pr`` proofs).
    """
    output = exporter.export_proof_file(str(CES_PROOF))
    # Standard EC structure.
    assert "module ChainedEncryption" in output
    assert "module Game_step_0" in output
    # Two distinct assumption hops; each produces an eps term.
    assert "eps_OneTimeSecrecy" in output
    # Set let-bindings in CES become top-level EC type decls.
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


def test_export_chained_encryption_uses_tactic_cache() -> None:
    """With the CES sidecar checked in, the export must consume all
    cached tactics — no ``tactic-cache miss`` blocks should remain.
    Covers both Topological Sorting and Merge Product Samples.
    """
    output = exporter.export_proof_file(str(CES_PROOF))
    miss_blocks = output.count("tactic-cache miss")
    assert miss_blocks == 0, (
        f"Expected 0 cache misses; got {miss_blocks}.\n{output}"
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_chained_encryption_typechecks_in_easycrypt(
    tmp_path: Path,
) -> None:
    """EC verification of CES, end-to-end with zero admits.

    The chain + Layer-2 tactic cache cover all interchangeability
    micro-lemmas (Topological Sorting, Merge Product Samples, etc.),
    and the multi-module assumption hops (``hop_1_pr``, ``hop_3_pr``)
    close via the byequiv/inline*/sim + advantage-axiom template. The
    file must exit 0 in EC with no ``admit.`` remaining.
    """
    output = exporter.export_proof_file(str(CES_PROOF))
    assert "admit." not in output, (
        f"CES export still contains admit; the 0-admit baseline has "
        f"regressed:\n{output}"
    )
    ec_file = tmp_path / "ces.ec"
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
        f"EC parse error in CES output:\nstderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}"
    )
    assert result.returncode == 0, (
        f"EC verification failed (exit {result.returncode}); inline-style "
        f"micro-lemmas or _pr lemmas may have regressed.\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout[-2000:]}"
    )


# ---------------------------------------------------------------------------
# TriplingPRG (PRG-family, single primitive re-instantiated)
# ---------------------------------------------------------------------------


def test_export_tripling_prg_does_not_crash() -> None:
    """TriplingPRG_PRGSecurity exports without raising.

    First single-primitive proof beyond SymEnc that the exporter handles:
    PRG primitive with ``Int``-valued field parameters (``lambda``,
    ``stretch``), a scheme (TriplingPRG) that re-instantiates the same
    primitive with different stretch, and two reductions over
    PRGSecurity. Exercises the abstract-bitstring-type clone bindings
    and the sympy canonicalization of bitstring length expressions.
    """
    output = exporter.export_proof_file(str(TPRG_PROOF))
    # Sanity: structural artifacts that the architecture must produce.
    assert "abstract theory PRG_Theory" in output
    assert "clone PRG_Theory as G_c" in output
    assert "clone PRG_Theory as T_c" in output
    # Per-clone bitstring type bindings: G has stretch=lambda (output
    # bs_lambda + lambda = bs_2_lambda); T has stretch=2*lambda (output
    # bs_lambda + 2*lambda = bs_3_lambda). sympy canonicalization
    # collapses ``lambda + 2 * lambda`` -> ``3*lambda``.
    assert "bs_lambda_stretch_t <- bs_2_lambda" in output
    assert "bs_lambda_stretch_t <- bs_3_lambda" in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_tripling_prg_typechecks_in_easycrypt(
    tmp_path: Path,
) -> None:
    """EC accepts the TriplingPRG export with 0 admits.

    All three interchangeability hops (``hop_0``, ``hop_2``, ``hop_4``)
    close end-to-end: ``hop_0``'s chain runs through canned + parametric
    tactics, and ``hop_2`` / ``hop_4`` are closed by the
    ``Split Uniform Samples`` / ``Merge Uniform Samples`` parametric
    synthesizers (using the slice/concat round-trip + distribution-split
    axioms emitted by ``TypeCollector.emit()``).

    The two assumption hops (``hop_1_pr``, ``hop_3_pr``) also close: the
    advantage axiom emitted by
    ``translate_assumption_axioms_theory`` no longer carries the
    ``{-Em}`` adversary-footprint restriction, which would otherwise
    block ``R1_Adv(G, A)`` (whose body references the declared module
    ``G``). The restriction was redundant for ProofFrog's stateless
    primitive convention and prevented PRG-hybrid-style reductions
    from applying the axiom.
    """
    output = exporter.export_proof_file(str(TPRG_PROOF))
    assert "admit." not in output, (
        "TriplingPRG export should have no admits; regression in the "
        "parametric synthesizers, type-collector axioms, or the relaxed "
        "advantage-axiom emission may have reintroduced one."
    )
    ec_file = tmp_path / "triplingprg.ec"
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
        f"EC parse error in TriplingPRG output:\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    assert result.returncode == 0, (
        f"EC verification failed (exit {result.returncode}); the "
        f"non-admit portions of the TriplingPRG export may have "
        f"regressed.\nstderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


# ---------------------------------------------------------------------------
# joy_old/5_Exercises (partial-split PRG-family proofs)
# ---------------------------------------------------------------------------


def test_export_5_8_b_partial_split_closes_via_augmented_intermediate() -> None:
    """``5_8_b`` exercises the partial-split path of
    ``split_uniform_samples_tactic``.

    The proof's reduction projects a ``bs_3*lambda`` challenger sample
    onto two ``bs_lambda`` slices ``[0, lambda)`` and ``[lambda, 2*lambda)``
    and discards the last ``lambda``-bit window. The engine emits a
    ``Split Uniform Samples`` whose ``|L| + |R| = 2*lambda < 3*lambda =
    |RES|`` — a partial split.

    The straight 2-way bijection axiom would be unsound (image
    cardinality ``2^(2*lambda)`` vs ``2^(3*lambda)``). The synthesizer
    instead routes through an augmented intermediate: register a 3-way
    concat op ``concat3_bs_lambda_bs_lambda_bs_lambda_to_bs_3_lambda``
    with the sound dlet-form ``dbs_3_lambda_split3_...`` axiom, then
    emit per-micro ``Mid``/``Aug`` helper modules plus four sub-lemmas
    that chain L→Mid→Aug→R.

    This test pins both directions: (a) the unsound 2-way axioms must
    not appear, (b) the 3-way concat op + augmented helpers + zero
    admits must appear.
    """
    output = exporter.export_proof_file(str(PRG_5_8_B_PROOF))
    assert "dbs_3_lambda_split_bs_lambda_bs_lambda" not in output, (
        "Unsound 2-way split axiom (image of concat has 2^(2*lambda) "
        "elements but dbs_3_lambda has 2^(3*lambda)) regressed."
    )
    assert "concat_bs_lambda_bs_lambda_to_bs_3_lambda" not in output, (
        "Unsound 2-way concat op for the partial-split case regressed."
    )
    assert (
        "concat3_bs_lambda_bs_lambda_bs_lambda_to_bs_3_lambda" in output
    ), (
        "Expected the sound 3-way concat op for the partial-split path; "
        "the augmented-intermediate synthesizer did not fire."
    )
    assert "dbs_3_lambda_split3_bs_lambda_bs_lambda_bs_lambda" in output, (
        "Expected the sound dlet-form distribution-split axiom for the "
        "3-way decomposition; ``TypeCollector.emit()`` may have skipped it."
    )
    assert "admit." not in output, (
        f"Expected zero admits after the partial-split synthesizer "
        f"closes hop_2 via the augmented intermediate. Got "
        f"{output.count('admit.')} admits."
    )


def test_export_5_8_a_partial_split_mid_gap_with_modcall_tail_closes() -> None:
    """``5_8_a`` exercises the *mid-gap* partial-split shape combined
    with a *module-call tail* — the partial-split synthesizer's hardest
    case so far.

    The proof's R1 reduction samples a ``BS<3*lambda>`` challenger
    output and slices it at ``[0, lambda)`` and ``[2*lambda, 3*lambda)``
    — leaving the *middle* window ``[lambda, 2*lambda)`` unused. Each
    used slice is then passed to ``G.evaluate`` and the two outputs are
    concatenated. The engine emits a ``Split Uniform Samples`` with
    ``|L| + |R| = 2*lambda < 3*lambda = |RES|`` *and* the slices wrapped
    in module calls.

    Locks in:

    * The mid-gap source layout produces a 3-way concat3 op with piece
      order ``(L, GAP, R)`` (not ``(L, R, GAP)``).
    * The module-call-tail branch fires (Mid/Aug bodies splice the
      ``G.evaluate`` calls; the return concat uses
      ``concat_<eval_ret>_<eval_ret>_to_<ret_type>``, not the unsound
      ``concat_<L>_<R>_to_<ret_type>``).
    * The augmented intermediate's ``aug_to_right`` emits a
      ``swap{1} 2 1.`` to move the dead gap sample to the tail before
      dropping it via ``rnd{1}``.
    * Zero admits in the final export.
    """
    output = exporter.export_proof_file(str(PRG_5_8_A_PROOF))
    assert "dbs_6_lambda_split_bs_lambda_bs_lambda" not in output, (
        "Unsound 2-way split axiom regressed: the partial-split path "
        "must not emit a ``concat_<L>_<R>_to_<ret_type>`` axiom when "
        "the return is ``concat (eval_ret) (eval_ret)`` with "
        "|L|+|R| != |ret_type|."
    )
    assert "concat_bs_lambda_bs_lambda_to_bs_6_lambda" not in output, (
        "Unsound 2-way concat op for the module-call-tail partial "
        "split regressed."
    )
    assert (
        "concat3_bs_lambda_bs_lambda_bs_lambda_to_bs_3_lambda" in output
    ), (
        "Expected the 3-way concat op for the mid-gap partial-split "
        "path; the augmented-intermediate synthesizer did not fire."
    )
    assert "swap{1} 2 1." in output, (
        "Expected ``aug_to_right`` to emit ``swap{1} 2 1.`` for the "
        "mid-gap layout (so the dead gap sample lands at the tail "
        "before being dropped via ``rnd{1}``)."
    )
    assert "admit." not in output, (
        f"Expected zero admits after the partial-split synthesizer "
        f"closes hop_2 via the augmented intermediate. Got "
        f"{output.count('admit.')} admits."
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_5_8_a_partial_split_typechecks_in_easycrypt(
    tmp_path: Path,
) -> None:
    """EC accepts the ``5_8_a`` export end-to-end with zero admits.

    The mid-gap layout + module-call tail variants of
    :func:`_partial_split_helpers_modcall` (and the structural fix to
    ``_expr_signature`` that lets the swap-detection find the
    Inline-Single-Use-Variables permutation modulo the hoist's
    fresh-name rename) together close every hop.
    """
    output = exporter.export_proof_file(str(PRG_5_8_A_PROOF))
    ec_file = tmp_path / "5_8_a.ec"
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
        f"EC parse error in 5_8_a output:\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    assert result.returncode == 0, (
        f"EC verification failed (exit {result.returncode}); the "
        f"non-admit portions of the 5_8_a export may have regressed.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_5_8_b_partial_split_typechecks_in_easycrypt(
    tmp_path: Path,
) -> None:
    """EC accepts the ``5_8_b`` export end-to-end with zero admits.

    The partial-split synthesizer routes ``hop_2`` through an augmented
    intermediate (3-way concat bijection), closing it without admits.
    Everything else — the assumption hop, the Real/Random-side chains,
    the reduction-body wrappers — closes via the standard parametric +
    canned tactics. Locks in that the augmented-intermediate path is
    accepted by EC end-to-end.
    """
    output = exporter.export_proof_file(str(PRG_5_8_B_PROOF))
    ec_file = tmp_path / "5_8_b.ec"
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
        f"EC parse error in 5_8_b output:\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    assert result.returncode == 0, (
        f"EC verification failed (exit {result.returncode}); the "
        f"non-admit portions of the 5_8_b export may have regressed.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )
