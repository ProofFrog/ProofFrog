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
PRG_5_8_OTUC_PROOF = (
    REPO_ROOT / "examples" / "joy_old" / "5_Exercises" / "5_8_PseudoOTP_OTUC.proof"
)
PRG_5_10_PROOF = REPO_ROOT / "examples" / "joy_old" / "5_Exercises" / "5_10.proof"
# KEMPRF_INDCPA: the multi-oracle + multi-primitive epic target. EC-compiles
# (exit 0, EasyCrypt-ACCEPTED) but is not yet admit-free -- all per-oracle equiv
# bodies close (init synth-static, challenge via seeded <oracle> cache entries);
# only the 4 assumption-Pr wrapper bridges remain guided admits (M5).
KEMPRF_INDCPA_PROOF = REPO_ROOT / "examples" / "Proofs" / "KEM" / "KEMPRF_INDCPA.proof"
# 2_13: the inner SymEnc primitive's KeyGen/Enc calls are reordered by the
# Inline-Local-Tuple-Literal step, which needs the scheme-statelessness
# foundation to close in EC.
STATELESS_2_13_PROOF = REPO_ROOT / "examples" / "joy_old" / "2_Exercises" / "2_13.proof"
# Primitive-only proofs: the module under attack is an abstract primitive
# instance (``SymEnc E = SymEnc(MS, CS, KS)``), not a concrete scheme, so the
# primary is emitted as a section ``declare module`` with no concrete scheme.
PRIMITIVE_ONLY_2_14_FWD_PROOF = (
    REPO_ROOT / "examples" / "joy_old" / "2_Exercises" / "2_14_Forward.proof"
)
PRIMITIVE_ONLY_2_14_BWD_PROOF = (
    REPO_ROOT / "examples" / "joy_old" / "2_Exercises" / "2_14_Backward.proof"
)
INDOT_DOLLAR_IMPLIES_INDOT_PROOF = (
    REPO_ROOT / "examples" / "Proofs" / "SymEnc" / "INDOT$_implies_INDOT.proof"
)
KEMPRF_INDCPA_PROOF = REPO_ROOT / "examples" / "Proofs" / "KEM" / "KEMPRF_INDCPA.proof"
# ModOTP_INDOT: a primitive-typed-let bound to a concrete scheme
# (``SymEnc E = ModOTP(q)``) with a proof-local single-oracle intermediate
# game (``Game Hyb(Int q)``). Exercises (a) concrete-scheme instantiation for
# an unconditional primitive-typed primary, (b) single-oracle intermediate-game
# body emission, (c) the reversed-direction ModInt rnd bijection.
MODOTP_INDOT_PROOF = REPO_ROOT / "examples" / "Proofs" / "SymEnc" / "ModOTP_INDOT.proof"
# GeneralDoubleSymEnc_INDOT$: Key = [S.Key, T.Key], so canonicalization
# eliminates a local ``k <- (key1, key2)`` (built from two prior abstract
# keygen results) and projects ``k.`1``/``k.`2`` into abstract ``S.enc``/
# ``T.enc``. Two blockers close via two synthesizers over TWO declared modules:
# hop_0's pure-local tuple via the per-method tuple-congruence synthesizer, and
# hop_2's ``Topological Sorting`` (which prunes dead abstract ``S.keygen``/
# ``S.enc`` calls) via the dead-abstract-call-drop synthesizer + ``<M>_<m>_pres``
# glob-preservation axioms. Admit-free + EasyCrypt-accepted.
GENERAL_DOUBLE_SYMENC_PROOF = (
    REPO_ROOT / "examples" / "Proofs" / "SymEnc" / "GeneralDoubleSymEnc_INDOT$.proof"
)
# INDOT$_implies_DoubleSymEnc_INDOT$: the SINGLE-module analogue of
# GeneralDoubleSymEnc. ``Scheme DoubleSymEnc(SymEnc s)`` (lowercase module-typed
# param) double-encrypts with ONE scheme ``s`` under two independent keys, so
# ``Key = [s.Key, s.Key]`` and every abstract call is on the same module. Two
# things had to land: (1) structural -- uppercase the scheme's own param
# (``s`` -> ``S``) for EC, apply the functor to the instance (``DoubleSymEnc(E)``
# not ``DoubleSymEnc(S)``), and resolve ``s.Key`` locals to the inner carrier;
# (2) tactics -- hop_0's tuple ``Inline Local Tuple Literal`` and the reduction
# side's ``Inline Single-Use Variables`` both reorder/relabel two SAME-module
# abstract calls, which a plain ``swap`` cannot do (shared ``glob``). They route
# through the single-module ``Ideal`` stateless route with a data-aware swap.
DOUBLE_SYMENC_PROOF = (
    REPO_ROOT
    / "examples"
    / "Proofs"
    / "SymEnc"
    / "INDOT$_implies_DoubleSymEnc_INDOT$.proof"
)
# 2_15_Backward: the Foo (swap-two-ciphertexts) game implies INDOT, reduced by
# extracting one ciphertext from the Foo pair. Single declared module ``E``.
# Each interchangeability hop canonicalizes a reduction body that builds a local
# pair ``c <- (Enc(KeyGen(), mL), Enc(KeyGen(), mR))`` and returns ``c[0]``: the
# pair is eliminated by ``Expand Tuples`` and a later standardization reorder
# (attributed to ``Inline Single-Use Variables``) transposes the two same-module
# ``E.enc`` calls so the surviving result moves position. ``Expand Tuples`` (the
# tuple-inline sibling) and the same-module enc reorder both route through the
# single-module ``Ideal`` stateless path with a *data-aware* swap -- the lockstep
# ``call (_: true)`` ISUV tactic cannot bridge the relabel (it leaves ``={res}``
# open). Admit-free + EasyCrypt-accepted.
JOY_2_15_BACKWARD_PROOF = (
    REPO_ROOT / "examples" / "joy_old" / "2_Exercises" / "2_15_Backward.proof"
)
# CG_seedbased_HON_BIND_K_PK: a hybrid-KEM binding proof whose flat-game
# endpoints carry a ``_hoisted_0`` field (the engine's ``Hoist Deterministic
# Call to Initialize`` lifts a deterministic call into Initialize as a shared
# field) read by a later oracle. The exporter must type that field reference
# from the module's field declarations, not only from in-method locals.
CG_HON_BIND_K_PK_PROOF = (
    REPO_ROOT
    / "examples"
    / "applications"
    / "cfrg-hybrid-kems"
    / "proofs"
    / "CG"
    / "CG_seedbased_HON_BIND_K_PK.proof"
)
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
    (``={m, glob E1, glob E2}``-style specs, ``proc; ((sp; wp; sim) || sim).``
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
        assert (
            f"type {ty}." in output or f"type {ty} =" in output
        ), f"missing `type {ty}` in:\n{output}"
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
    # Inline-style canned tactic for multi-module bodies is the robust
    # ``proc; ((sp; wp; sim) || sim).`` form (not the single-instance
    # ``proc; sp; auto.``). The ``|| sim`` fallback closes the identical-render
    # ``Symbolic Computation`` shape where ``sp; wp; sim`` errors on equality
    # inference; the left branch keeps every shape that already worked.
    assert "proc; ((sp; wp; sim) || sim)." in output
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
    assert miss_blocks == 0, f"Expected 0 cache misses; got {miss_blocks}.\n{output}"


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


def test_export_hoisted_field_reference_is_typed() -> None:
    """A flat-game ``_hoisted_0`` field read by an oracle exports without a
    ``KeyError: Unknown variable type``.

    The engine's ``Hoist Deterministic Call to Initialize`` lifts a
    deterministic call into the game's Initialize as a shared field
    (``_hoisted_0``); a later oracle consumes it inside an expression. The
    module translator must seed each method's type map from the enclosing
    module's field declarations -- not only from in-method locals -- so the
    expression translator can resolve the field's type. Before the fix this
    whole A-type class (11 cfrg-hybrid-kems + 2 GHP18 proofs) failed to export.
    """
    output = exporter.export_proof_file(str(CG_HON_BIND_K_PK_PROOF))
    # The hoisted field surfaces as a module-level state var in the flat games.
    assert "var _hoisted_0 :" in output


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
    assert (
        "concat_bs_lambda_bs_lambda_to_bs_3_lambda" not in output
    ), "Unsound 2-way concat op for the partial-split case regressed."
    assert "concat3_bs_lambda_bs_lambda_bs_lambda_to_bs_3_lambda" in output, (
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
        "Unsound 2-way concat op for the module-call-tail partial " "split regressed."
    )
    assert "concat3_bs_lambda_bs_lambda_bs_lambda_to_bs_3_lambda" in output, (
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
    assert (
        "declare module P " not in output
    ), "OTP must be a concrete module, not an abstract ``declare module``."
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


def test_export_kemprf_requires_equality_emits_bitstring_type_aliases() -> None:
    """KEMPRF's scheme has two ``requires`` clauses relating a KEM carrier
    set to a PRF BitString type:

        requires K.SharedSecret == BitString<F.lambda>;
        requires K.Ciphertext subsets BitString<F.in>;

    With ``K = KEM(SharedSecretSpace, CiphertextSpace, ...)`` and
    ``F = PRF(lambda, in, out)`` these say ``SharedSecretSpace == bs_lambda``
    and ``CiphertextSpace == bs_in``. The exporter must express these type
    equalities so the scheme module type-checks (``k <- x.`1`` assigns a
    ``SharedSecretSpace`` to a ``bs_lambda``). The set-let carrier is declared
    first, so the BitString type is emitted as an alias of it.
    """
    output = exporter.export_proof_file(str(KEMPRF_INDCPA_PROOF))
    # The BitString types become aliases of the (earlier-declared) set carriers.
    assert "type bs_lambda = SharedSecretSpace." in output
    assert "type bs_in = CiphertextSpace." in output
    # The set carriers stay abstract; the bare abstract BitString decls are gone.
    assert "type SharedSecretSpace." in output
    assert "type CiphertextSpace." in output
    assert "type bs_lambda.\n" not in output
    assert "type bs_in.\n" not in output


def test_export_kemprf_emits_intermediate_game_module() -> None:
    """KEMPRF_INDCPA's step 3 is the bare intermediate game ``G_RandKey(K, F)``.

    The exporter must emit a concrete ``module G_RandKey`` -- a multi-primitive
    functor (params ``K``, ``F``) ascribing to the outer KEM oracle type, with
    the ``pk`` field as module state -- so ``Game_step_3``'s reference to
    ``G_RandKey(K, F).initialize`` resolves in EasyCrypt.
    """
    output = exporter.export_proof_file(str(KEMPRF_INDCPA_PROOF))
    assert (
        "module G_RandKey (K : K_c.Scheme, F : F_c.Scheme) : "
        "KF_c.KEM_INDCPA_MultiChal_Oracle = {" in output
    )
    body = output.split("module G_RandKey", 1)[1].split("}.", 1)[0]
    # The shared KEM public key lives as module state.
    assert "var pk : PKeySpace" in body
    # initialize sets pk from K.keygen; challenge samples a fresh PRF key,
    # runs K.encaps, and applies F.evaluate (the nested call is hoisted).
    assert "proc initialize() : PKeySpace = {" in body
    assert "key <$ dbs_lambda" in body
    assert "<@ K.encaps(pk)" in body
    assert "<@ F.evaluate(key, ct)" in body


def test_export_kemprf_flat_state_field_names_are_ec_identifiers() -> None:
    """The multi-oracle hop's flat-state modules carry inlined reduction state
    whose field names contain ``@`` (``challenger@pk``). EC rejects ``@`` in a
    ``var`` declaration. The normalizer must sanitize the field *declaration*
    names (not just their in-body references) so the module parses.
    """
    output = exporter.export_proof_file(str(KEMPRF_INDCPA_PROOF))
    # The mangled field name must not survive into any declaration/reference.
    assert "challenger@pk" not in output
    assert "challenger@sk" not in output
    # The sanitized form is used consistently (declared as a module var).
    assert "var challenger_pk :" in output


def test_export_kemprf_abstract_footprint_restriction_and_section_order() -> None:
    """M5 blocker A: the abstract scheme modules (and inlining-hop Pr-lemma
    adversaries) must be RESTRICTED from the state-holding modules named in the
    multi-oracle live-state couplings, and those module DEFINITIONS must precede
    ``declare module K/F`` so the restriction names are in scope.

    Without the restriction EC rejects the Pr lemma's
    ``call (_: Chal.pk{1} = G.pk{2})`` ("the module K can write ...pk"); without
    the reorder the restriction names (``G_RandKey``, ``R_MultiPRF``) are not yet
    declared at the ``declare module`` line.
    """
    output = exporter.export_proof_file(str(KEMPRF_INDCPA_PROOF))
    lines = output.splitlines()

    def _line_of(predicate: object) -> int:
        return next(i for i, ln in enumerate(lines) if predicate(ln))  # type: ignore[operator]

    # ``declare module K`` carries the state-module restriction set.
    decl_k = next(ln for ln in lines if ln.strip().startswith("declare module K <:"))
    for mod in ("-G_RandKey", "-R_MultiPRF", "-K_c.KEM_INDCPA_MultiChal_Random"):
        assert mod in decl_k, f"{mod!r} missing from declare module K"

    # The state-holding module definitions precede ``declare module K``.
    declare_k_idx = _line_of(lambda ln: ln.strip().startswith("declare module K <:"))
    grandkey_idx = _line_of(lambda ln: ln.strip().startswith("module G_RandKey "))
    rmultiprf_idx = _line_of(lambda ln: ln.strip().startswith("module R_MultiPRF "))
    assert grandkey_idx < declare_k_idx
    assert rmultiprf_idx < declare_k_idx

    # Both the inlining-hop and the assumption-hop Pr lemmas' adversaries carry
    # the same state-module restriction set. The assumption-hop bridges
    # (``hop_{1,4}_pr`` hL/hR) close via ``byequiv; proc; inline *; sim`` (M5
    # option B), and EC rejects that ``sim`` frame unless ``A`` is separated from
    # the challenger/reduction state modules; the advantage-axiom application is
    # unaffected because the axiom places no restriction on its adversary.
    hop2_pr = next(ln for ln in lines if ln.strip().startswith("lemma hop_2_pr "))
    assert "-G_RandKey" in hop2_pr and "-R_MultiPRF" in hop2_pr
    hop1_pr = next(ln for ln in lines if ln.strip().startswith("lemma hop_1_pr "))
    for mod in ("-G_RandKey", "-R_MultiPRF", "-K_c.KEM_INDCPA_MultiChal_Random"):
        assert mod in hop1_pr, f"{mod!r} missing from hop_1_pr footprint"


def test_export_otuc_foreign_otp_uses_its_own_carrier_types() -> None:
    """OTUC has primary ``P = PseudoOTP(lambda, 2*lambda, G)`` and foreign
    ground ``E = OTP(3*lambda)``. Both schemes extend ``SymEnc`` and share
    field names (``Key``, ``Message``, ``Ciphertext``), but with different
    lengths: PseudoOTP's ``Key = BitString<lambda>`` and ``Message =
    BitString<3*lambda>``; OTP's are all ``BitString<3*lambda>``.

    The exporter must translate OTP's body using *OTP's* carrier types, not
    inherit PseudoOTP's bare aliases from the top-level alias map. The
    ground-scheme bug emitted ``proc enc(k : bs_lambda, m : bs_3_lambda)``
    with ``xor_lambda k m`` (k pinned to primary's ``Key`` width).
    """
    output = exporter.export_proof_file(str(PRG_5_8_OTUC_PROOF))
    # OTP is concretized as a ground foreign module of E_c.Scheme.
    assert "module OTP : E_c.Scheme = {" in output
    otp_body = output.split("module OTP : E_c.Scheme = {", 1)[1].split("}.", 1)[0]
    # All three procs use OTP's own carrier width (bs_3_lambda everywhere);
    # nothing should leak the primary's bs_lambda width through.
    assert "proc keygen() : bs_3_lambda" in otp_body
    assert "k <$ dbs_3_lambda" in otp_body
    assert "proc enc(k : bs_3_lambda, m : bs_3_lambda) : bs_3_lambda" in otp_body
    assert "proc dec(k : bs_3_lambda, c : bs_3_lambda) : bs_3_lambda" in otp_body
    # Body XORs are at the 3*lambda width.
    assert "xor_3_lambda k m" in otp_body
    assert "xor_3_lambda k c" in otp_body
    assert "bs_lambda" not in otp_body
    assert "xor_lambda" not in otp_body
    # E_c clone bindings (sanity) are at bs_3_lambda.
    assert "clone SymEnc_Theory as E_c with" in output
    e_c_block = output.split("clone SymEnc_Theory as E_c with", 1)[1].split(".", 1)[0]
    assert "type key <- bs_3_lambda" in e_c_block
    assert "type message <- bs_3_lambda" in e_c_block
    assert "type ciphertext <- bs_3_lambda" in e_c_block


def test_export_otuc_closes_at_zero_admits() -> None:
    """5_8_PseudoOTP_OTUC was previously ``blocked`` (exported with 2
    cross-primitive admits). With the carrier-name + ``external_module_types``
    fixes, the only foreign primitive on the cross-primitive hops is ``G``
    (a PRG *primitive* instance, no scheme body to inline). The chain emits
    and the per-transform micros close with synth-static throughout —
    bringing OTUC to 0 admits. Pins both: 0 admits, and that the two
    cross-primitive hops emit a chain (not the abstract-bridge admit).
    """
    output = exporter.export_proof_file(str(PRG_5_8_OTUC_PROOF))
    assert output.count("admit.") == 0
    # Both cross-primitive hops emit a chain through Step_<i>{L,R}_state_*
    # rather than the foreign-abstract admit comment.
    assert "module Step_0L_state_0" in output
    assert "module Step_0R_state_0" in output
    assert "module Step_2L_state_0" in output
    assert "module Step_2R_state_0" in output
    assert "cross-primitive inlining hop" not in output


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
def test_export_5_8_PseudoOTP_OTUC_typechecks_in_easycrypt(
    tmp_path: Path,
) -> None:
    """EC accepts the ``5_8_PseudoOTP_OTUC`` export end-to-end with zero
    admits. OTUC has primary ``P : PseudoOTP`` (functor) and foreign ground
    ``E : OTP``; both extend ``SymEnc``. The carrier-alias precedence fix
    (foreign's bare ``Key``/``Message``/``Ciphertext`` beat the primary's
    same-named aliases) gives OTP correct widths. The cross-primitive hops
    (INDOT$ ↔ PRGSecurity) bridge via the standard ``proc; inline*; sp; wp;
    sim`` recipe — possible here because the only foreign-primitive instance
    on the hop is ``G`` (a PRG primitive, no scheme body to inline).
    """
    output = exporter.export_proof_file(str(PRG_5_8_OTUC_PROOF))
    ec_file = tmp_path / "5_8_PseudoOTP_OTUC.ec"
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
        f"EC parse error in OTUC output:\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    assert result.returncode == 0, (
        f"EC verification failed (exit {result.returncode}).\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


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


# ---------------------------------------------------------------------------
# Scheme-statelessness foundation (stateless-scheme abstract-call reorder)
# ---------------------------------------------------------------------------


def test_export_2_13_emits_statelessness_foundation_and_closes() -> None:
    """2_13's Inline-Local-Tuple-Literal step reorders two abstract scheme
    calls. The exporter emits the statelessness foundation (distribution ops,
    ``Ideal`` module, ``E_<m>_sem`` axioms) and synthesizes a
    transitivity-through-``Ideal`` proof, closing the proof with no admits.
    """
    output = exporter.export_proof_file(str(STATELESS_2_13_PROOF))
    # Foundation in the theory.
    assert "op dkeygen :" in output
    assert "op denc :" in output
    assert "module Ideal : Scheme" in output
    # Section-scope statelessness specs.
    assert "declare axiom E_keygen_sem" in output
    assert "declare axiom E_enc_sem" in output
    # Synthesized transitivity through the all-Ideal instantiation + the
    # tuple-inlined intermediate module.
    assert "E_c.Ideal).eavesdrop" in output
    # The augmented-intermediate ``_b`` module: index reflects the chain
    # position of the tuple-inline reorder (after the leading Alpha Rename
    # normalization step the global AlphaRename pass now inserts).
    assert "module Step_0L_state_2b" in output
    # No admits.
    assert "admit." not in output


def test_export_2_13_no_orphan_or_missing_cache_keys() -> None:
    """The synthesized stateless micros must not leave phantom cache lookups:
    once synthesis wins, the cache miss recorded by the admit path is dropped,
    so 2_13 consults the tactic cache zero times.
    """
    exporter.export_proof_file(str(STATELESS_2_13_PROOF))
    keys = getattr(exporter, "_last_requested_cache_keys", [])
    assert keys == [], (
        f"2_13 unexpectedly consulted the tactic cache ({len(keys)} key(s)); "
        "stateless-reorder synthesis should drop the recorded miss."
    )


def test_statelessness_foundation_is_gated() -> None:
    """Proofs whose abstract scheme calls are not reordered must not get the
    foundation (no Ideal module, no _sem axioms) and must still close.
    """
    for proof in (OTP_PROOF, PRG_5_8_A_PROOF, CES_PROOF):
        output = exporter.export_proof_file(str(proof))
        assert "module Ideal" not in output, f"{proof.name} got an Ideal module"
        assert "_sem :" not in output, f"{proof.name} got a stateless axiom"
        assert "admit." not in output, f"{proof.name} regressed to an admit"


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_2_13_typechecks_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: 2_13 export (with the statelessness foundation) type-checks
    in EasyCrypt with zero admits."""
    output = exporter.export_proof_file(str(STATELESS_2_13_PROOF))
    assert "admit." not in output
    ec_file = tmp_path / "2_13.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the 2_13 export.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


# ---------------------------------------------------------------------------
# Pure-local tuple-congruence synthesizer (multi-module ``Inline Local Tuple
# Literal``: ``k <- (key1, key2)`` projected into abstract ``S.enc``/``T.enc``).
# ---------------------------------------------------------------------------


def test_export_general_double_symenc_synthesizes_tuple_congruence() -> None:
    """``GeneralDoubleSymEnc_INDOT$`` hop_0 eliminates a pure-local
    ``k <- (key1, key2)`` over two declared modules and projects ``k.`1``/
    ``k.`2`` into abstract ``S.enc``/``T.enc``. The tuple-congruence
    synthesizer must emit one ``<M>_<m>_eq`` congruence lemma per abstract
    method and close the micro name-independently (``call <M>_<m>_eq`` peeling
    + ``wp`` + ``skip => /#``) as ``synth-param`` -- not the whole-hop admit it
    fell to before (the single-module ``Ideal`` route does not cover two
    declared modules).
    """
    output = exporter.export_proof_file(str(GENERAL_DOUBLE_SYMENC_PROOF))
    # One congruence lemma per abstract method used in the hop.
    assert "(* Per-method congruence lemmas (pure-local tuple inlining) *)" in output
    for name in ("S_keygen_eq", "T_keygen_eq", "S_enc_eq", "T_enc_eq"):
        assert f"lemma {name} :" in output, f"missing congruence lemma {name}"
        assert f"call {name}." in output, f"congruence lemma {name} never applied"
    # The tuple micro now resolves via synth-param (reverse-order congruence
    # peeling + residual smt), not the whole-hop unguided admit.
    assert "skip => /#." in output
    assert "culprits: Inline Local Tuple Literal" not in output
    # The whole hop_0 chain renders (its tuple micro no longer sinks it).
    assert "per-transform chain unrenderable" not in output
    # Both blockers close: the proof is admit-free end to end.
    assert "admit." not in output


def test_export_general_double_symenc_drops_dead_abstract_calls() -> None:
    """``GeneralDoubleSymEnc_INDOT$`` hop_2 is a ``Topological Sorting`` that
    prunes a reduction's dead ``S.keygen(); S.enc(...)`` calls (the challenger
    is ``Random`` so their results feed nothing). Dropping an abstract call
    one-sided is unsound for a stateful module, so the dead-abstract-call-drop
    synthesizer emits ``<M>_<m>_pres`` glob-preservation axioms (the
    stateless-scheme assumption ProofFrog's pruning relies on) and drops each
    call via ``call{1} (<m>_pres g)`` -- resolving the micro as synth-param.
    """
    output = exporter.export_proof_file(str(GENERAL_DOUBLE_SYMENC_PROOF))
    for axiom in ("S_keygen_pres", "S_enc_pres"):
        assert f"declare axiom {axiom} " in output, f"missing pres axiom {axiom}"
        assert f"call{{1}} ({axiom} g_S)." in output, f"{axiom} never applied"
    # The Topological-Sorting prune no longer collapses the hop to admit.
    assert "culprits: Topological Sorting" not in output


def test_congruence_lemmas_are_gated() -> None:
    """Proofs with no pure-local tuple-congruence micro must not get the
    per-method congruence lemmas (byte-identical to before for unaffected
    proofs) and must still close.
    """
    for proof in (OTP_PROOF, PRG_5_8_A_PROOF, CES_PROOF):
        output = exporter.export_proof_file(str(proof))
        assert (
            "(* Per-method congruence lemmas (pure-local tuple inlining) *)"
            not in output
        ), f"{proof.name} got congruence lemmas"
        assert "_pres " not in output, f"{proof.name} got a glob-preservation axiom"
        assert "admit." not in output, f"{proof.name} regressed to an admit"


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_general_double_symenc_typechecks_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: the ``GeneralDoubleSymEnc_INDOT$`` export is admit-free and
    type-checks in EasyCrypt (EXIT 0). hop_0's tuple-congruence micro and hop_2's
    dead-abstract-call drop both close, so the synthesized proofs are real, not
    merely 0-error text -- this is the first clean proof produced by the
    tuple-congruence + dead-call-drop synthesizers."""
    output = exporter.export_proof_file(str(GENERAL_DOUBLE_SYMENC_PROOF))
    assert "admit." not in output
    ec_file = tmp_path / "GeneralDoubleSymEnc.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the GeneralDoubleSymEnc export.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


# ---------------------------------------------------------------------------
# Single-module DoubleSymEnc: lowercase scheme module-param normalization +
# same-module abstract-call reorder/relabel via the single-module Ideal route.
# ---------------------------------------------------------------------------


def test_export_double_symenc_normalizes_lowercase_scheme_param() -> None:
    """``Scheme DoubleSymEnc(SymEnc s)`` has a lowercase module-typed param,
    which is an invalid EC functor-param identifier. The exporter must
    uppercase it (``s`` -> ``S``) in the functor signature AND its body, apply
    the functor to the passed *instance* (``DoubleSymEnc(E)``), resolve the
    body's ``s.Key`` locals to the inner carrier (``KeySpace``, not the
    scheme's own pair ``KeySpace * KeySpace``), and keep ``S`` out of the
    adversary footprint (only the declared ``E`` belongs there).
    """
    output = exporter.export_proof_file(str(DOUBLE_SYMENC_PROOF))
    # Functor param + body uppercased.
    assert "module DoubleSymEnc (S : E_c.Scheme)" in output
    assert "key1 <@ S.keygen();" in output
    # The functor is applied to the instance E, never to the bare param S.
    assert "DoubleSymEnc(E)" in output
    assert "DoubleSymEnc(S)" not in output
    assert "DoubleSymEnc(s)" not in output
    # ``s.Key`` local resolves to the inner key, not the scheme's pair Key.
    assert "var key1 : KeySpace;" in output
    assert "var key1 : KeySpace * KeySpace;" not in output
    # Footprint names the declared instance, not the scheme's own param.
    assert "{-S," not in output and "{-S}" not in output


def test_export_double_symenc_routes_same_module_reorders_through_ideal() -> None:
    """Every abstract call in the single-module DoubleSymEnc is on the same
    module ``E``, so the tuple inline (hop_0 left) and the reduction-side
    ``Inline Single-Use Variables`` (hop_0 right) each transpose/relabel two
    ``E`` calls -- a plain ``swap`` is unsound (the calls share ``glob E``).
    Both must route through the single-module ``Ideal`` stateless route with a
    *data-aware* swap, never emit a bare same-module ``swap`` on ``E``, and
    close admit-free.
    """
    output = exporter.export_proof_file(str(DOUBLE_SYMENC_PROOF))
    # The reduction-side ISUV reorder routes through Ideal (transitivity) with
    # the data-aware swap that accounts for the keygen-result relabel...
    assert "transitivity Step_0R_state_1(E_c.Ideal).ctxt" in output
    assert "proc; swap{1} 3 -2; sim" in output
    # ...and never emits the unsound signature-only same-module swap on E.
    assert "swap{1} 3 -1" not in output
    # The tuple micro's Ideal leg recovers the relabel too (swap before sim).
    assert "proc; swap{1} 2 -1; sim" in output
    # Statelessness foundation is in scope (the route depends on it).
    assert "declare axiom E_keygen_sem" in output
    assert "admit." not in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_double_symenc_typechecks_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: the single-module ``DoubleSymEnc`` export is admit-free and
    EasyCrypt-accepted (EXIT 0). Guards the full stack -- lowercase-param
    normalization, ``s.Key`` carrier resolution, instance-applied functor, and
    the same-module reorder/relabel routed through the ``Ideal`` route -- since
    a 0-admit file EC still rejects is Blocked, not clean.
    """
    output = exporter.export_proof_file(str(DOUBLE_SYMENC_PROOF))
    assert "admit." not in output
    ec_file = tmp_path / "DoubleSymEnc.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the DoubleSymEnc export.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


# ---------------------------------------------------------------------------
# 2_15_Backward: Expand Tuples + same-module enc reorder via the Ideal route.
# ---------------------------------------------------------------------------


def test_export_2_15_backward_routes_expand_tuples_and_reorder_through_ideal() -> None:
    """The single-module ``2_15_Backward`` hops each eliminate a local pair via
    ``Expand Tuples`` and transpose two same-module ``E.enc`` calls (a relabel
    attributed to ``Inline Single-Use Variables``). Neither is plain-``swap``
    safe (the calls share ``glob E``), so both must route through the
    single-module ``Ideal`` stateless path:

    * ``Expand Tuples`` -- the tuple-inline sibling -- builds the ``state_1b``
      intermediate module and bridges it with ``proc; inline*; auto``.
    * the same-module enc reorder uses a *data-aware* swap sequence
      (``swap{1} 3 -2; swap{1} 4 -2``) that accounts for the keygen-result
      relabel a signature-only swap would miss.

    The lockstep ``call (_: true)`` ISUV tactic must NOT be what closes the
    reorder micro (it leaves ``={res}`` open), and no admit may remain.
    """
    output = exporter.export_proof_file(str(JOY_2_15_BACKWARD_PROOF))
    # Statelessness foundation is in scope (the route depends on it).
    assert "declare axiom E_keygen_sem" in output
    assert "declare axiom E_enc_sem" in output
    # Expand Tuples routes through Ideal with the tuple-inline intermediate.
    assert "module Step_0R_state_2b (E : E_c.Scheme)" in output
    assert "transitivity Step_0R_state_2b(E_c.Ideal).eavesdrop" in output
    assert "proc; inline*; auto" in output
    # The same-module enc reorder uses the data-aware swap, not a bare lockstep.
    assert "proc; swap{1} 3 -2; swap{1} 4 -2; sim" in output
    # Admit-free.
    assert "admit." not in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_2_15_backward_typechecks_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: ``2_15_Backward`` is admit-free and EasyCrypt-accepted (EXIT
    0). Guards that routing ``Expand Tuples`` and the same-module enc reorder
    through the ``Ideal`` stateless path actually closes -- a 0-admit file EC
    still rejects would be Blocked, not clean.
    """
    output = exporter.export_proof_file(str(JOY_2_15_BACKWARD_PROOF))
    assert "admit." not in output
    ec_file = tmp_path / "2_15_Backward.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the 2_15_Backward export.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


# ---------------------------------------------------------------------------
# Primitive-only proofs (A2): no concrete Scheme; the module under attack is
# an abstract primitive instance emitted as a section ``declare module``.
# ---------------------------------------------------------------------------


def test_export_primitive_only_emits_declare_module_no_concrete_scheme() -> None:
    """A primitive-security proof (``SymEnc E = SymEnc(MS, CS, KS)``; no
    concrete scheme imported) exports with the primary primitive as an
    abstract section ``declare module E <: E_c.Scheme`` and NO concrete scheme
    module ("Concrete scheme implementation" section). Games/reductions are
    emitted as functors over the declared ``E``. Regression guard for the
    primitive-only entry path in ``export_proof_file``.
    """
    output = exporter.export_proof_file(str(PRIMITIVE_ONLY_2_14_FWD_PROOF))
    assert "clone SymEnc_Theory as E_c" in output
    assert "section Main" in output
    assert "declare module E <: E_c.Scheme" in output
    # No concrete scheme body is translated in primitive-only mode.
    assert "Concrete scheme implementation" not in output
    # The security games are still emitted as functors over the abstract E.
    assert "module Game_step_0 (E : E_c.Scheme" in output


def test_export_dead_sample_drop_synthesizes_one_sided_rnd() -> None:
    """``2_14_Forward``'s codewise hop drops a dead ``mPrime`` sample (the
    reduction samples it but ``Foo.Left`` encrypts only ``m``), which
    ``Topological Sorting`` removes on one side. The dead-sample-drop
    synthesizer must emit a one-sided lossless-sample drop for both the
    forward (``rnd{1}``) and reversed (``rnd{2}``) micro instead of falling
    back to admit. Guards the synth-param path in ``chain_emitter``.

    NB: this asserts the dead-drop micro is *resolved*. The abstract
    call-past-sample reorder (blocker B) is covered by
    ``test_export_2_14_forward_synthesizes_call_past_sample_swap`` and the
    Docker-gated end-to-end test.
    """
    output = exporter.export_proof_file(str(PRIMITIVE_ONLY_2_14_FWD_PROOF))
    assert "+ rnd{1}; auto; smt(dMessageSpace_ll)." in output
    assert "+ rnd{2}; auto; smt(dMessageSpace_ll)." in output
    # The dead-drop micros resolve via synth-param, so the chain no longer
    # collapses to an admit (the Topological-Sorting culprit is gone).
    assert "per-transform chain unrenderable" not in output
    assert "culprits: Topological Sorting" not in output


def test_export_2_14_forward_synthesizes_call_past_sample_swap() -> None:
    """``2_14_Forward``'s hop_2 reorders an abstract ``E.keygen()`` past an
    independent ``mPrime <$ dMessageSpace`` sample under ``Inline Single-Use
    Variables``. The raw transform-application ASTs are normalized differently
    from the rendered flat-state modules the micro lemma relates, so the
    swap must be recomputed from the rendered modules
    (``_rendered_state_swaps``). The forward and reversed micros must each
    emit ``swap{1} 2 -1.`` (synth-param) and the whole proof must export with
    no admits. Guards blocker B."""
    output = exporter.export_proof_file(str(PRIMITIVE_ONLY_2_14_FWD_PROOF))
    # The call-past-sample reorder is now synthesized as an explicit swap on
    # both the forward and reversed micro (rather than collapsing to the canned
    # ``proc; sp; wp; sim.`` that cannot reconcile the reorder).
    assert output.count("swap{1} 2 -1.") >= 2
    # Whole proof closes: no admits anywhere, chain renders end to end.
    assert "admit." not in output
    assert "per-transform chain unrenderable" not in output


def test_export_2_14_backward_synthesizes_call_past_sample_swap() -> None:
    """``2_14_Backward`` is the mirror of ``2_14_Forward`` and carries the same
    abstract call-past-sample reorder. It was 0-admit but previously did NOT
    EC-compile (the canned ``proc; sp; wp; sim.`` cannot reconcile the reorder),
    so it was effectively Blocked despite the dashboard counting it clean. The
    rendered-state swap synthesizer closes it too."""
    output = exporter.export_proof_file(str(PRIMITIVE_ONLY_2_14_BWD_PROOF))
    assert output.count("swap{1} 2 -1.") >= 2
    assert "admit." not in output
    assert "per-transform chain unrenderable" not in output


def test_export_primitive_only_reduction_applied_to_primary_module() -> None:
    """When a reduction's scheme parameter is named differently from the
    instance (``Reduction R1(SymEnc se)`` applied as ``R1(proofE)``), the
    lifted reduction-adversary wrapper applies the reduction to the primary
    declared module, not to the reduction's own formal-parameter name.

    Also exercises EC-module-name normalization: the lowercase instance
    ``proofE`` and reduction params ``se``/``se2`` are uppercased to valid EC
    module identifiers (``ProofE``, ``Se``/``Se2``) — EC theory/module names
    must begin with an uppercase letter.
    """
    output = exporter.export_proof_file(str(INDOT_DOLLAR_IMPLIES_INDOT_PROOF))
    # Lowercase instance/param names are normalized to uppercase-initial.
    assert "clone SymEnc_Theory as ProofE_c" in output
    assert "declare module ProofE <: ProofE_c.Scheme" in output
    assert "A(R1(ProofE, C))" in output
    assert "A(R2(ProofE, C))" in output
    # The original lowercase identifiers must not leak into the EC output.
    assert "proofE" not in output
    assert "A(R1(se, C))" not in output
    assert "A(R2(se2, C))" not in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_primitive_only_indot_typechecks_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: the primitive-only ``INDOT$_implies_INDOT`` export (abstract
    ``declare module``, EC-name normalization) type-checks in EasyCrypt with
    zero admits."""
    output = exporter.export_proof_file(str(INDOT_DOLLAR_IMPLIES_INDOT_PROOF))
    assert "admit." not in output
    ec_file = tmp_path / "indot_implies_indot.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the INDOT$_implies_INDOT export.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
@pytest.mark.parametrize(
    "proof_path, stem",
    [
        (PRIMITIVE_ONLY_2_14_FWD_PROOF, "2_14_forward"),
        (PRIMITIVE_ONLY_2_14_BWD_PROOF, "2_14_backward"),
    ],
)
def test_export_2_14_typechecks_in_easycrypt(
    proof_path: Path, stem: str, tmp_path: Path
) -> None:
    """End-to-end: the primitive-only ``2_14_Forward``/``2_14_Backward`` exports
    type-check in EasyCrypt with zero admits. Exercises both B3 synthesizers
    together — the dead-sample-drop (hop_0) and the abstract call-past-sample
    swap (blocker B) — which previously left these proofs 0-admit but
    non-compiling (the canned ``proc; sp; wp; sim.`` cannot reconcile the
    reorder of an abstract ``E.keygen()`` past an independent ``mPrime <$ d``
    sample)."""
    output = exporter.export_proof_file(str(proof_path))
    assert "admit." not in output
    ec_file = tmp_path / f"{stem}.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the {stem} export.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


# ---------------------------------------------------------------------------
# Multi-oracle stateful indistinguishability — VALIDATED EC TEMPLATE
# ---------------------------------------------------------------------------

EC_TEMPLATES = Path(__file__).parent / "ec_templates"
MULTI_ORACLE_TEMPLATE = EC_TEMPLATES / "multi_oracle_indist.ec"
MULTI_ORACLE_DEADFIELD_TEMPLATE = EC_TEMPLATES / "multi_oracle_deadfield_coupling.ec"
MULTI_ORACLE_ABSTRACT_CALL_TEMPLATE = (
    EC_TEMPLATES / "multi_oracle_abstract_call_coupling.ec"
)
DEAD_SAMPLE_DROP_TEMPLATE = EC_TEMPLATES / "dead_sample_drop.ec"
CALL_PAST_SAMPLE_SWAP_TEMPLATE = EC_TEMPLATES / "call_past_sample_swap.ec"
MARGINAL_SPLIT_TEMPLATE = EC_TEMPLATES / "marginal_split.ec"
SAMPLE_REORDER_TWIN_TEMPLATE = EC_TEMPLATES / "sample_reorder_twin.ec"
MULTI_ORACLE_REDUCTION_ADV_TEMPLATE = (
    EC_TEMPLATES / "multi_oracle_reduction_adversary.ec"
)


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_dead_sample_drop_template_compiles(tmp_path: Path) -> None:
    """Regression tripwire for the dead-sample-drop EC tactic template (B3
    part 1). The shape: a per-transform micro hop where one side carries an
    extra, independent, dead `<$` sample (bound variable unused downstream)
    that ``Topological Sorting`` drops on the other side. The two bodies are
    not whole-body permutations, so ``_permutation_swaps`` cannot handle them;
    the recipe instead moves the dead lossless sample to the front
    (``swap{S}``), splits it off (``seq``), discharges it one-sided
    (``rnd{S}; auto; smt(d<Type>_ll)``), then closes with ``sim``. ``S`` is the
    side carrying the extra sample (1 forward, 2 reversed). If this stops
    compiling, the ``_dead_sample_drop`` synthesizer's target tactic must be
    re-derived before any automation relying on it can be trusted."""
    ec_file = tmp_path / "dead_sample_drop.ec"
    ec_file.write_text(DEAD_SAMPLE_DROP_TEMPLATE.read_text())
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the dead-sample-drop template.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_call_past_sample_swap_template_compiles(tmp_path: Path) -> None:
    """Regression tripwire for the call-past-sample reorder EC tactic template
    (B3 blocker B). The shape: a per-transform micro hop where a
    canonicalization step (e.g. ``Inline Single-Use Variables``) reorders an
    abstract scheme call (``k <@ E.keygen()``) past an INDEPENDENT sample
    (``mPrime <$ d``). The sample is glob-independent, so EC's ``swap`` can move
    it past the abstract call; the recipe is ``proc; swap{1} <pos> <delta>;
    sp; wp; sim`` (the same canned suffix the multi-module emitter uses). The
    swap is computed from the rendered flat-state modules (see
    ``chain_emitter._rendered_state_swaps``), not the raw transform-application
    ASTs. If this stops compiling, that synthesizer's target tactic must be
    re-derived before any automation relying on it can be trusted."""
    ec_file = tmp_path / "call_past_sample_swap.ec"
    ec_file.write_text(CALL_PAST_SAMPLE_SWAP_TEMPLATE.read_text())
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the call-past-sample-swap template.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_multi_oracle_reduction_adversary_template_compiles(tmp_path: Path) -> None:
    """Regression tripwire for the ASSUMPTION-HOP reduction-adversary lift
    (multi-oracle foundation §7, blocker B). The shape: an Initialize-lifted
    multi-oracle game whose adversary is a reduction-lift ``R_Adv(E, A)`` of an
    outer adversary ``A`` through a reduction ``R`` whose ``Initialize`` is a
    pure forward of ``challenger.Initialize()``. ``R_Adv.distinguish`` must
    FORWARD the lifted ``pk`` to ``A`` rather than re-run ``R.initialize`` (which
    would call ``C.init`` a second time and violate the restricted ``{O.challenge}``
    adversary interface). If this stops compiling, the exporter's
    ``translate_reduction_adversary`` forward-pk path must be re-derived. Verified
    end-to-end: compiling KEMPRF_INDCPA.ec confirmed this advances EC past the
    line-1403 interface rejection."""
    ec_file = tmp_path / "multi_oracle_reduction_adversary.ec"
    ec_file.write_text(MULTI_ORACLE_REDUCTION_ADV_TEMPLATE.read_text())
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the multi-oracle reduction-adversary template.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_marginal_split_template_compiles(tmp_path: Path) -> None:
    """Regression tripwire for the marginal partial-split ``Split Uniform
    Samples`` EC tactic template (the PRG-stretch shape: one big sample
    ``orig <$ d_RES`` consumed only via two non-overlapping slices that feed a
    complex downstream tail, with ``|L| + |R| < |RES|``). The recipe builds
    ``Mid``/``Aug`` as surgical copies of the flat states (whole tail verbatim,
    sampling prefix patched) and chains ``S5 ~ Mid ~ Aug ~ S6`` via the
    ``d_RES_split3`` rnd-identity bijection, the ``slice_concat3`` round-trips,
    and a dead-gap drop; see ``_marginal_split_helpers``. If this stops
    compiling, that synthesizer's target tactic must be re-derived before any
    automation relying on it can be trusted."""
    ec_file = tmp_path / "marginal_split.ec"
    ec_file.write_text(MARGINAL_SPLIT_TEMPLATE.read_text())
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the marginal-split template.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_sample_reorder_twin_template_compiles(tmp_path: Path) -> None:
    """Regression tripwire for the functional-twin sample-reorder middle leg.
    The shape: two functionalized twins (every det call already an ``ev``
    assignment) differ only in the order of their ``<$`` samples, with a
    consistent ``_rN`` renaming dragged in by the reorder (so the
    full-signature swap declines). The recipe reorders the samples with
    ``swap{1}`` (each sample is glob/data-independent of everything before it,
    so the hoist is EC-valid), then peels the now-common call+sample backbone
    ``(wp; (call (_: true) || rnd))*``; ``wp`` dissolves the renamed
    deterministic locals and ``skip => /#`` discharges the residual. See
    ``chain_emitter._sample_reorder_swaps`` / ``_det_reorder_leg``. If this
    stops compiling, that middle-leg recipe must be re-derived before any
    automation relying on it (e.g. ``UG_seedbased_Correctness``) can be
    trusted."""
    ec_file = tmp_path / "sample_reorder_twin.ec"
    ec_file.write_text(SAMPLE_REORDER_TWIN_TEMPLATE.read_text())
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the sample-reorder-twin template.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_kemprf_indcpa_compiles_in_easycrypt(tmp_path: Path) -> None:
    """KEMPRF_INDCPA (the multi-oracle + multi-primitive epic target) is
    admit-free AND EasyCrypt ACCEPTS the file (exit 0) -- the M5 "clean"
    milestone. It exercises the lifted-Initialize multi-oracle wrappers, the
    reduction-adversary forward-pk lift (blocker B), the intermediate-game
    module, requires-equality type aliases, multi-primitive type qualification,
    the live-state couplings, the abstract-scheme footprint restrictions, the
    seeded per-oracle challenge bodies, AND the assumption-hop Pr-lemma wrapper
    bridges all composing in EC.

    The four lifted-``Initialize`` per-oracle equiv lemmas
    (``hop_{0,2,3,5}_initialize``) close via the canned inline-equivalence
    tactic under the ``={glob K} /\\ ={glob F}`` coupling; all four ``challenge``
    per-oracle bodies (``hop_{0,2,3,5}_challenge``) close via seeded per-oracle
    (``<oracle>``) tactic-cache entries (the det-axiom finishers + per-hop
    order-swap / distribution-coupling / dead-call-drop variants); and the two
    assumption hops' four Pr-lemma bridges (``hop_{1,4}_pr`` hL/hR) close via
    the synthesized name-independent ``byequiv ...; proc; inline *; sim`` tactic
    under the widened adversary footprint. So this test asserts EC ACCEPTANCE
    (no parse/type/tactic error) AND zero admits. If it regresses to a nonzero
    exit, a structural multi-oracle/multi-primitive gap has reopened; if the
    admit count rises, an init lemma or one of the seeded ``hop_*_challenge``
    cache entries reopened (EC inline-name drift, or a canonical-text shift
    turning a cache hit into a miss -- see the per-oracle tactic-cache design
    doc), or the assumption-bridge tactic stopped closing.
    """
    output = exporter.export_proof_file(str(KEMPRF_INDCPA_PROOF))
    n_admits = len([ln for ln in output.splitlines() if ln.strip() == "admit."])
    assert n_admits == 0, (
        f"expected 0 admits (the M5 'KEMPRF clean' milestone), got {n_admits}; "
        f"an init equiv lemma, one of the seeded hop_*_challenge cache entries, "
        f"or an assumption-hop Pr bridge may have reopened, or a new gap "
        f"appeared."
    )
    # The assumption-hop Pr bridges close via the synthesized name-independent
    # tactic (option B), not admits -- guard the exact bridge shape.
    for hop_i in (1, 4):
        body = output.split(f"lemma hop_{hop_i}_pr ", 1)[1].split("qed.", 1)[0]
        assert "by byequiv (_: " in body and "proc; inline *; sim." in body, (
            f"hop_{hop_i}_pr no longer closes via the synthesized assumption-"
            f"bridge tactic (byequiv; proc; inline *; sim)."
        )
    # The seeded per-oracle cache entries must drive every challenge body to a
    # cached-guided (rung 3) resolution -- a regression to an admit rung means
    # the canonical-text key drifted (cache miss) and the entry is now orphaned.
    for hop_i in (0, 2, 3, 5):
        assert f"lemma hop_{hop_i}_challenge :" in output
        body = output.split(f"lemma hop_{hop_i}_challenge :", 1)[1].split("qed.", 1)[0]
        assert "(* resolution: cached-guided *)" in body, (
            f"hop_{hop_i}_challenge no longer resolves cached-guided; the seeded "
            f"<oracle>:challenge cache entry likely missed (canonical-text drift)."
        )
    ec_file = tmp_path / "kemprf_indcpa.ec"
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
        f"EC parse error in KEMPRF_INDCPA output:\nstderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )
    assert result.returncode == 0, (
        f"EC rejected KEMPRF_INDCPA (exit {result.returncode}); a multi-oracle / "
        f"multi-primitive structural gap has reopened.\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout[-2000:]}"
    )


def test_export_modotp_indot_emits_intermediate_game_module() -> None:
    """ModOTP_INDOT exports a concrete scheme + intermediate-game body.

    The proof binds a primitive-typed let to a concrete scheme
    (``SymEnc E = ModOTP(q)``) with no assumption and interposes a proof-local
    single-oracle intermediate game ``Game Hyb(Int q)``. The exporter must (a)
    instantiate ``module ModOTP`` (not an abstract ``declare module E``), and
    (b) emit ``module Hyb`` (with the ``Int q`` index dropped) referenced as a
    bare ``Hyb`` by the game wrapper and per-hop equiv lemmas. Admit-free,
    cache-free (all synthesized).
    """
    output = exporter.export_proof_file(str(MODOTP_INDOT_PROOF))
    assert "declare module E" not in output
    assert "module ModOTP : E_c.Scheme" in output
    assert "module Hyb : E_c.INDOT_Oracle" in output
    assert "A(Hyb)" in output and "A(Hyb(q))" not in output
    n_admits = len([ln for ln in output.splitlines() if ln.strip() == "admit."])
    assert n_admits == 0, f"expected 0 admits, got {n_admits}"


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_modotp_indot_compiles_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: ModOTP_INDOT export is admit-free AND EC ACCEPTS it.

    Regression tripwire for the single-oracle intermediate-game emission path:
    if the ``Hyb`` module body, its bare reference, the concrete-scheme
    instantiation, or the reversed ModInt bijection regresses, EC rejects the
    file (the intermediate-game reference goes undefined, the abstract-E bridge
    fails to ``inline *``, or the reversed ``rnd`` side-goal becomes false).
    """
    output = exporter.export_proof_file(str(MODOTP_INDOT_PROOF))
    n_admits = len([ln for ln in output.splitlines() if ln.strip() == "admit."])
    assert n_admits == 0, f"expected 0 admits, got {n_admits}"
    ec_file = tmp_path / "modotp_indot.ec"
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
        f"EC parse error in ModOTP_INDOT output:\nstderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )
    assert result.returncode == 0, (
        f"EC rejected ModOTP_INDOT (exit {result.returncode}); the intermediate-"
        f"game emission or concrete-scheme instantiation path has reopened.\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout[-2000:]}"
    )


def test_export_kemprf_indcpa_requests_per_oracle_cache_keys() -> None:
    """The multi-oracle post-init (``challenge``) path consults the per-oracle
    (``<oracle>``) tactic cache: one key per non-assumption hop's challenge
    oracle. All four challenge bodies (``hop_{0,2,3,5}_challenge``) HIT their
    seeded entries (resolve cached-guided). Init oracles never consult the
    cache. Not Docker-gated -- it inspects the requested-key list and the
    emitted resolution tags only."""
    output = exporter.export_proof_file(str(KEMPRF_INDCPA_PROOF))
    keys = getattr(exporter, "_last_requested_cache_keys", [])
    oracle_keys = [k for k in keys if k[0].startswith("<oracle>")]
    # Four non-assumption multi-oracle hops, each requesting its challenge body;
    # init oracles close synth-static and request nothing.
    assert [k[0] for k in oracle_keys] == [
        "<oracle>:challenge"
    ] * 4, f"expected 4 <oracle>:challenge keys, got {[k[0] for k in oracle_keys]}"
    # All four challenge bodies hit their seeded entry -> cached-guided.
    for hop_i in (0, 2, 3, 5):
        body = output.split(f"lemma hop_{hop_i}_challenge :", 1)[1].split("qed.", 1)[0]
        assert (
            "(* resolution: cached-guided *)" in body
        ), f"hop_{hop_i}_challenge expected cached-guided (seeded hit)"


def test_export_single_oracle_proof_requests_no_oracle_cache_keys() -> None:
    """A single-oracle / clean proof never reaches the multi-oracle post-init
    path, so it requests no ``<oracle>`` keys -- byte-identical output is
    preserved. Guards the gating of the per-oracle cache lookup."""
    exporter.export_proof_file(str(OTP_PROOF))
    keys = getattr(exporter, "_last_requested_cache_keys", [])
    assert [k for k in keys if k[0].startswith("<oracle>")] == []


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_multi_oracle_deadfield_coupling_template_compiles(
    tmp_path: Path,
) -> None:
    """Regression tripwire for the LIVE-STATE coupling target shape used when
    two adjacent multi-oracle games have STRUCTURALLY DIFFERENT module state
    (the realistic KEMPRF case, M5 line-1334 blocker). The left endpoint is a
    reduction R(Chal) delegating to an assumption challenger that holds pk + a
    DEAD sk; the right endpoint is a bare game GR holding only pk. Their globs
    differ in shape, so ``(glob R(Chal)){1} = (glob GR){2}`` is ill-typed. The
    fix couples on the shared LIVE state only, naming it directly --
    ``Chal.pk{1} = GR.pk{2}`` (the sub-module's var is nameable even though the
    lemma is about R(Chal); ``proc; inline *; auto`` unfolds the delegation).
    The Pr-lemma structure is unchanged from the identical-state template; only
    the coupling string changes from a glob-equality to a live-state field
    equality -- the single seam the exporter must compute. If this stops
    compiling, the live-state coupling shape must be re-derived before any
    automation relying on it can be trusted."""
    ec_file = tmp_path / "multi_oracle_deadfield_coupling.ec"
    ec_file.write_text(MULTI_ORACLE_DEADFIELD_TEMPLATE.read_text())
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the multi-oracle dead-field coupling template.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_multi_oracle_abstract_call_coupling_template_compiles(
    tmp_path: Path,
) -> None:
    """Regression tripwire for the live-state coupling when the post-init
    oracle CALLS an abstract stateless scheme (the realistic KEMPRF shape:
    ``challenge`` invokes ``K.encaps`` / ``F.evaluate``). Extends the
    deadfield template, whose post-init oracle used only operators and so
    never exercised an abstract call under the live-state coupling. Pins the
    extra load-bearing fact: the abstract scheme module must be RESTRICTED
    from the state-holding modules named in the coupling (``declare module E
    <: Scheme {-Chal, -GR}``) -- otherwise EC rejects the Pr lemma's ``call
    (_: Chal.pk{1} = GR.pk{2})`` with "The module E can write GR.pk" (an
    unrestricted abstract module is assumed to write every in-scope global).
    The adversary is likewise restricted ``{-Chal, -GR, -E}``. If this stops
    compiling, the footprint-restriction approach for abstract-call multi-
    oracle hops must be re-derived."""
    ec_file = tmp_path / "multi_oracle_abstract_call_coupling.ec"
    ec_file.write_text(MULTI_ORACLE_ABSTRACT_CALL_TEMPLATE.read_text())
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the multi-oracle abstract-call coupling template.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_multi_oracle_indist_template_compiles(tmp_path: Path) -> None:
    """Regression tripwire for the multi-oracle stateful indistinguishability
    EC tactic template (the hand-derived target shape the exporter must emit
    for hops between adjacent multi-oracle, stateful games such as
    KEM_INDCCA's Initialize + Decaps). The shape: Initialize is lifted into
    the game wrapper's ``main`` (the adversary gets only the post-init oracles
    plus the init result); a relational state-coupling invariant
    ``(glob L){1} = (glob R){2}`` is established by ``hop_init`` and preserved
    by one per-oracle equiv lemma each; the Pr lemma is ``byequiv; proc;
    call (_: coupling)`` with one ``conseq hop_<oracle>`` per post-init oracle
    then ``call hop_init``. If this stops compiling, the exporter's target
    shape for multi-oracle hops needs to be re-derived before any automation
    relying on it can be trusted."""
    ec_file = tmp_path / "multi_oracle_indist.ec"
    ec_file.write_text(MULTI_ORACLE_TEMPLATE.read_text())
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected the multi-oracle template.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )


# ---------------------------------------------------------------------------
# Hybrid-KEM *_Correctness structural fixes (nested-tuple type + value-param
# drop): these flipped the four expanded *_Correctness proofs from EC-rejected
# (blocked) to EC-accepted-with-whole-hop-admits (the chain battery is the
# remaining work). Pin that the export still EC-compiles.
# ---------------------------------------------------------------------------

CG_EXPANDED_CORRECTNESS = (
    EXAMPLES
    / "applications"
    / "cfrg-hybrid-kems"
    / "proofs"
    / "CG"
    / "CG_expanded_Correctness.proof"
)


def test_export_cg_expanded_correctness_nested_tuple_typed() -> None:
    """The KEMCombiner-style nested ``[[...], [...]]`` KeyGen result must emit
    a *nested* EC tuple type ``(... ) * (... )``, not a flattened one. Before
    the fix the scheme module was internally type-inconsistent (flat type vs
    nested ``.`i`` projections) and EC rejected it."""
    output = exporter.export_proof_file(str(CG_EXPANDED_CORRECTNESS))
    # A flattened nested product would have no parenthesized inner product;
    # the fix emits parens around each product-typed component.
    assert ") * (" in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_cg_expanded_correctness_compiles_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: the CG_expanded_Correctness export must be ACCEPTED by
    EasyCrypt (exit 0). It still carries whole-hop ``admit.`` micros (the
    7-transform chain battery is unsynthesized), so this asserts compilation,
    NOT admit-freeness -- it is the ⛔ -> ⚠ flip guard for the nested-tuple +
    value-param structural fixes. If it stops compiling, one of those fixes
    regressed."""
    output = exporter.export_proof_file(str(CG_EXPANDED_CORRECTNESS))
    ec_file = tmp_path / "cg_expanded_correctness.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected CG_expanded_Correctness.\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout[-2000:]}"
    )
