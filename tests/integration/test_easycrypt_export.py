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
PRG_5_8_E_PROOF = REPO_ROOT / "examples" / "joy_old" / "5_Exercises" / "5_8_e.proof"
PRG_5_8_F_PROOF = REPO_ROOT / "examples" / "joy_old" / "5_Exercises" / "5_8_f.proof"
PRG_5_10_PROOF = REPO_ROOT / "examples" / "joy_old" / "5_Exercises" / "5_10.proof"
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


def test_export_5_10_concrete_foreign_otp_closes_cross_primitive_hops() -> None:
    """``5_10`` proves ``PRGSecurity(H)`` (``H = PRG_5_10(G)``) via a
    three-stage hybrid that routes through ``INDOT$(P)`` for ``P = OTP``.

    Two of its hops are *cross-primitive inlining* hops
    (``PRGSecurity(G).Random ∘ R1 ≡ INDOT$(P).Real ∘ R3`` and the
    reverse): the engine proves them by inlining OTP's concrete body
    (``Enc(k,m) = k + m``). For an *abstract* INDOT$-secure ``P`` these
    are not valid, so they can only close when EC sees OTP concretely.

    The exporter emits ``OTP`` as a concrete top-level module
    (``module OTP : P_c.Scheme``) and binds ``P := OTP``, while keeping
    the abstract ``P_c`` theory + ``eps_INDOT_`` axiom so the advantage
    bound is preserved. EC's ``inline *`` then unfolds OTP on the wrapper
    side and the chain bridge closes.

    Locks in:

    * The concrete foreign module is emitted as ``module OTP : P_c.Scheme``
      (not an abstract ``declare module P``).
    * The abstract foreign theory + advantage axiom survive (the bound
      still references ``P_c.eps_INDOT_``).
    * Zero admits in the final export (both cross-primitive bridges close).
    """
    output = exporter.export_proof_file(str(PRG_5_10_PROOF))
    assert "module OTP : P_c.Scheme" in output, (
        "Expected the foreign OTP instance to be emitted as a concrete "
        "module ascribing to its clone's Scheme type."
    )
    assert "declare module P " not in output, (
        "OTP must be a concrete module, not an abstract ``declare module``."
    )
    assert "P_c.eps_INDOT_" in output, (
        "The abstract foreign theory + INDOT$ advantage axiom must be "
        "kept so the proof's advantage bound is preserved."
    )
    assert "admit." not in output, (
        f"Expected zero admits after concrete OTP closes the two "
        f"cross-primitive inlining bridges. Got {output.count('admit.')}."
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_5_10_typechecks_in_easycrypt(tmp_path: Path) -> None:
    """EC accepts the ``5_10`` export end-to-end with zero admits.

    Exercises the multi-primitive theory architecture (two abstract
    theories, three clones, a cross-primitive reduction) together with
    the concrete-foreign-OTP emission that closes the cross-primitive
    inlining-hop bridges via ``inline *``.
    """
    output = exporter.export_proof_file(str(PRG_5_10_PROOF))
    ec_file = tmp_path / "5_10.ec"
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
        f"EC parse error in 5_10 output:\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    assert result.returncode == 0, (
        f"EC verification failed (exit {result.returncode}); the "
        f"concrete-foreign-OTP cross-primitive export may have regressed.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


def test_export_5_8_e_hoists_scheme_and_reduction_calls() -> None:
    """``5_8_e``'s scheme and reduction bodies contain primitive calls
    nested in expressions (e.g. ``G.evaluate(s) + G.evaluate(0^lambda)``
    in the scheme, ``challenger.Query() + G.evaluate(0^lambda)`` in
    R1). EC does not permit module-procedure calls inside expressions,
    so the exporter pre-hoists them into separate ``<@`` call
    statements. Without this, the bodies fall back to ``return witness;``
    and the per-hop wrapper-to-flat-state bridge fails because inlining
    ``witness`` cannot align with the engine's already-inlined flat
    states.

    Locks in:

    * The scheme body renders both ``G.evaluate`` calls as ``<@``
      statements, not ``return witness;``.
    * The reductions R1 and R2 render their nested primitive/challenger
      calls as ``<@`` statements before the return.
    * Only the two cross-primitive bridge admits remain (out of scope
      per the fourth-pass architectural limitation).
    """
    output = exporter.export_proof_file(str(PRG_5_8_E_PROOF))
    # The scheme body must NOT fall back to ``return witness;``.
    assert "module PRG_5_8_e" in output
    scheme_section = output.split("module PRG_5_8_e", 1)[1].split("}", 1)[0]
    assert "return witness" not in scheme_section, (
        "PRG_5_8_e scheme body fell back to ``return witness;``; the "
        "scheme-call hoister did not fire on its source body."
    )
    # Both G.evaluate calls hoisted as <@ statements.
    assert scheme_section.count("<@ G.evaluate") == 2
    # Reduction R1 hoists the challenger.Query call.
    r1_section = output.split("module R1 ", 1)[1].split("}.", 1)[0]
    assert "<@ Challenger.query()" in r1_section
    assert "<@ G.evaluate(zero_lambda)" in r1_section
    # Reduction R2 hoists the nested G.evaluate inside Challenger.ctxt.
    r2_section = output.split("module R2 ", 1)[1].split("}.", 1)[0]
    assert "<@ G.evaluate(zero_lambda)" in r2_section
    # Both cross-primitive deterministic-reorder hops (hop_1, hop_3) close
    # via the hop-level cascades cached in the proof's ``.tactics.toml``
    # sidecar -- 0 admits (see test_export_5_8_e_concretizes_pseudootp).
    assert output.count("admit.") == 0, (
        f"Expected 0 admits (both hops closed from the sidecar cache). "
        f"Got {output.count('admit.')}."
    )


def test_export_5_8_e_concretizes_pseudootp() -> None:
    """5_8_e's foreign ``P = PseudoOTP(lambda, 2*lambda, G)`` is a non-ground
    scheme. The exporter concretizes it as an EC functor
    ``module PseudoOTP (G : G_c.Scheme) : P_c.Scheme`` applied as
    ``PseudoOTP(G)`` (so ``inline *`` can unfold it), and its two
    cross-primitive deterministic-reorder hops close via the hop-level
    cascades cached in the proof's ``.tactics.toml`` sidecar (keyed on the
    hops' canonical games). Result: 0 admits, and the export type-checks in
    EC (covered by test_export_5_8_e_typechecks_in_easycrypt).
    """
    output = exporter.export_proof_file(str(PRG_5_8_E_PROOF))
    # PseudoOTP emitted as a functor, applied to the declared module G,
    # with no abstract ``declare module P``.
    assert "module PseudoOTP (G : G_c.Scheme) : P_c.Scheme" in output
    assert "PseudoOTP(G)" in output
    assert "declare module P " not in output
    # The advantage axiom application parenthesizes the functor application.
    assert "advantage (PseudoOTP(G))" in output
    # Hops closed from the sidecar cache: cascade tactics present, 0 admits.
    assert "call{1} (G_evaluate_det" in output
    assert output.count("admit.") == 0


def test_export_emits_guided_template_for_uncached_det_reorder_hop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cross-primitive deterministic-reorder hop with no sidecar entry
    falls back to a Layer-3 *guided-template* admit: a structured admit
    annotated with the reorder cascade strategy, the determinism axioms in
    scope, and the canonical keys needed to author a sidecar entry. 5_8_f's
    two cross-primitive hops are normally closed from its sidecar; here we
    force the sidecar lookup empty so the export exhibits the guidance --
    exactly the path that authored that sidecar.
    """
    from proof_frog.export.easycrypt import tactic_cache as _tc

    monkeypatch.setattr(
        _tc,
        "relative_sidecar_path",
        lambda _p: Path("/nonexistent.proof.tactics.toml"),
    )
    output = exporter.export_proof_file(str(PRG_5_8_F_PROOF))
    assert "guided" in output and "STRATEGY" in output
    assert "G_evaluate_det" in output
    # The guidance includes how to cache the filled tactic.
    assert "transform = " in output and "TO CACHE" in output


def test_export_5_8_f_base_resolves_foreign_field_lengths() -> None:
    """5_8_f's primary scheme ``PRG_5_8_f`` defines ``Int lambda = 2*G.lambda``
    and slices on ``G.lambda``. The exporter must resolve every bitstring
    length to the proof's base ``lambda``, so the same length never acquires
    two EC type names (the ``requires``-equality "Phase 5D" gap). Since
    ``G = PRG(lambda, 2*lambda)``, ``G.lambda = lambda`` and ``G.stretch =
    2*lambda``; ``H.lambda = 2*lambda``, ``H.stretch = lambda``; and every
    ``G.evaluate`` output is ``3*lambda``.
    """
    output = exporter.export_proof_file(str(PRG_5_8_F_PROOF))
    # G's clone: seed = bs_lambda (G.lambda), output = bs_3_lambda.
    assert "type bs_lambda_t <- bs_lambda," in output
    assert "type bs_lambda_stretch_t <- bs_3_lambda," in output
    # H's clone: seed = bs_2_lambda (2*G.lambda), output also = bs_3_lambda.
    assert "type bs_lambda_t <- bs_2_lambda," in output
    # The scheme module matches the clone: evaluate takes bs_2_lambda -> bs_3_lambda.
    assert "proc evaluate(s : bs_2_lambda) : bs_3_lambda" in output
    # The slices feed G.evaluate at its real domain (bs_lambda), not a
    # splintered foreign-field name.
    assert "slice_bs_2_lambda_to_bs_lambda" in output
    assert "bs_2_G_lambda" not in output  # the pre-fix splinter is gone


def test_export_emits_determinism_specs_for_abstract_methods() -> None:
    """Each ``deterministic`` method of a declared (abstract) primitive
    module gets a glob-independent ``op ev_<m>`` in its theory and a
    section-scope ``declare axiom <m>_det`` (a phoare-1 spec asserting it
    is a pure, glob-preserving, total function == ``ev_<m>``).

    This is the sound foundation for reordering two deterministic
    abstract calls in EC (see the EC spike in the plan doc). The axioms
    are additive: existing tactics ignore them and all locked proofs
    still type-check (covered by the Docker-gated tests).

    ``5_8_e`` declares ``G <: G_c.Scheme`` (PRG, ``deterministic
    evaluate``); its ``P = PseudoOTP(...)`` is concretized as a functor so
    has no ``declare module``. CES declares ``E1``/``E2 <: *_c.Scheme``
    (SymEnc, ``deterministic Dec`` -- the 2-arg path).
    """
    prg_out = exporter.export_proof_file(str(PRG_5_8_E_PROOF))
    # Theory-level op modelling each deterministic method as a pure
    # function of its arguments (cloned per instance, e.g. G_c.ev_evaluate).
    assert "op ev_evaluate : bs_lambda_t -> bs_lambda_stretch_t." in prg_out
    # Section-scope determinism axiom over the declared PRG module ``G``.
    assert "declare axiom G_evaluate_det (g : (glob G))" in prg_out
    assert "res = G_c.ev_evaluate a0 ] = 1%r." in prg_out

    # CES exercises the SymEnc 2-arg deterministic ``Dec`` path.
    ces_out = exporter.export_proof_file(str(CES_PROOF))
    assert "op ev_dec :" in ces_out
    assert "declare axiom E1_dec_det (g : (glob E1)) (a0 :" in ces_out


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_5_8_e_typechecks_in_easycrypt(
    tmp_path: Path,
) -> None:
    """EC accepts the ``5_8_e`` export end-to-end (with the two
    cross-primitive bridge admits gated by structured comments).

    Locks in that the scheme/reduction body hoisting produces an EC
    file that compiles cleanly: the non-admit hops close via the
    standard chain + canned-bridge tactics, and the two admitted hops
    are the only ones that don't (and are architectural, not tactic).
    """
    output = exporter.export_proof_file(str(PRG_5_8_E_PROOF))
    ec_file = tmp_path / "5_8_e.ec"
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
        f"EC parse error in 5_8_e output:\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    assert result.returncode == 0, (
        f"EC verification failed (exit {result.returncode}); the "
        f"non-admit portions of the 5_8_e export may have regressed.\n"
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
