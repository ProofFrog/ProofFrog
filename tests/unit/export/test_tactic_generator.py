"""Unit tests for the EasyCrypt tactic generator."""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser, proof_engine
from proof_frog.export.easycrypt import tactic_generator as tg


OTP_PROOF = "examples/joy/Proofs/Ch2/OTPSecure.proof"


def _make_trace(transforms: list[list[str]]) -> dict[str, object]:
    """Build a trace dict mirroring canonicalize_game_with_trace's shape."""
    iterations = [
        {"iteration": i + 1, "transforms_applied": names}
        for i, names in enumerate(transforms)
    ]
    return {
        "iterations": iterations,
        "total_iterations": len(iterations),
        "converged": True,
    }


def _otpsecure_games() -> tuple[frog_ast.Game, frog_ast.Game]:
    """Return (left, right) game ASTs for OTPSecure's two steps."""
    proof = frog_parser.parse_proof_file(OTP_PROOF)
    engine = proof_engine.ProofEngine()
    for imp in proof.imports:
        path = frog_parser.resolve_import_path(imp.filename, OTP_PROOF)
        root = frog_parser.parse_file(path)
        engine.add_definition(root.get_export_name(), root)
        if isinstance(root, frog_ast.Scheme):
            for sub in root.imports:
                sub_path = frog_parser.resolve_import_path(sub.filename, path)
                sub_root = frog_parser.parse_file(sub_path)
                engine.add_definition(sub_root.get_export_name(), sub_root)
    engine.prove(proof, OTP_PROOF)
    # pylint: disable=protected-access
    left = engine._get_game_ast(proof.steps[0].challenger)
    right = engine._get_game_ast(proof.steps[1].challenger)
    # pylint: enable=protected-access
    return left, right


def test_absorbed_only_trace_emits_universal_template() -> None:
    """A trace that only fires absorbed transforms gets the standard template."""
    left, right = _otpsecure_games()
    trace = _make_trace(
        [["Inline Single-Use Variables", "Remove Redundant Copies"]]
    )
    body = tg.generate(
        left_trace=trace,
        right_trace=_make_trace([]),
        left_ast=left,
        right_ast=right,
        method_name="enc",
    )
    assert body == ["proc.", "inline *.", "sim.", "qed."]
    # sanity: no handler output for absorbed-only traces
    assert all("rnd" not in line for line in body)


def test_unhandled_transform_emits_admit_with_comment() -> None:
    """A trace containing an unregistered transform falls back to admit."""
    left, right = _otpsecure_games()
    trace = _make_trace([["MysteryTransformNobodyHandles"]])
    body = tg.generate(
        left_trace=trace,
        right_trace=_make_trace([]),
        left_ast=left,
        right_ast=right,
        method_name="enc",
    )
    assert any("admit" in line for line in body)
    assert any("MysteryTransformNobodyHandles" in line for line in body)
    assert body[-1] == "qed."


def test_uniform_xor_simplification_emits_rnd_bijection() -> None:
    """A trace with UniformXorSimplification produces an rnd line.

    Uses the actual OTPSecure left game so the bijection extractor has
    something realistic to chew on.
    """
    left, right = _otpsecure_games()
    trace = _make_trace(
        [["Inline Single-Use Field", "Uniform XOR Simplification"]]
    )
    body = tg.generate(
        left_trace=trace,
        right_trace=_make_trace([]),
        left_ast=left,
        right_ast=right,
        method_name="enc",
    )
    rnd_line = next((line for line in body if line.startswith("rnd ")), None)
    assert rnd_line is not None, f"No rnd line in body: {body}"
    assert "xor_" in rnd_line and "{2}" in rnd_line, rnd_line
