"""Diagnostics parity between `prove` and the web/CLI diagnostic path.

Commit `1dd8d4c` extracted `ProofEngine.set_up_proof_context` so the
prover and the diagnostic commands (`step-detail`, `inlined-game`,
`canonicalization-trace`, `step-after-transform`, MCP wrappers) share
the same simplification context. Before that, `_setup_engine_for_proof`
silently omitted `sampled_let_names`, `requirements`, sampled-let
`proof_namespace` entries, and `_extract_subsets_pairs()`, so transforms
that consult those fields under-simplified in the diagnostic path.

These tests pin parity on a proof that exercises both `requires:` and a
sampled `Function` let.
"""

import copy
import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from proof_frog import frog_parser, proof_engine
from proof_frog.web_server import (
    _capture_canonicalization_trace,
    _get_file_type,
    _setup_engine_for_proof,
)
from proof_frog import frog_ast

REPO_ROOT = Path(__file__).parent.parent.parent
EXAMPLES = REPO_ROOT / "examples"
PROOF_PATH = str(EXAMPLES / "Proofs" / "KEM" / "HashedElGamalKEM_INDCCA.proof")


def _build_prove_path_engine() -> proof_engine.ProofEngine:
    """Mimic `ProofEngine.prove`'s setup without running the proof."""
    proof_file = frog_parser.parse_proof_file(PROOF_PATH)
    engine = proof_engine.ProofEngine(False)
    suppress = io.StringIO()
    with redirect_stdout(suppress), redirect_stderr(suppress):
        for imp in proof_file.imports:
            imp_path = frog_parser.resolve_import_path(
                imp.filename, PROOF_PATH, allowed_root=str(EXAMPLES)
            )
            file_type = _get_file_type(imp_path)
            root: frog_ast.Primitive | frog_ast.Scheme | frog_ast.GameFile
            match file_type:
                case frog_ast.FileType.PRIMITIVE:
                    root = frog_parser.parse_primitive_file(imp_path)
                case frog_ast.FileType.SCHEME:
                    root = frog_parser.parse_scheme_file(imp_path)
                case frog_ast.FileType.GAME:
                    root = frog_parser.parse_game_file(imp_path)
                case _:
                    raise TypeError(f"Cannot import {file_type}")
            name = imp.rename if imp.rename else root.get_export_name()
            engine.add_definition(name, root)
        engine.set_up_proof_context(proof_file)
    return engine


def _build_diagnostic_path_engine() -> proof_engine.ProofEngine:
    suppress = io.StringIO()
    with redirect_stdout(suppress), redirect_stderr(suppress):
        engine, _proof_file = _setup_engine_for_proof(
            PROOF_PATH, allowed_root=str(EXAMPLES)
        )
    return engine


def test_proof_uses_requires_and_sampled_let() -> None:
    """Guard the fixture: the test only catches regressions if the proof
    actually exercises both `requires:` and a sampled let."""
    diag = _build_diagnostic_path_engine()
    assert "H" in diag.sampled_let_names
    assert len(diag.requirements) >= 1


def test_sampled_let_names_match() -> None:
    diag = _build_diagnostic_path_engine()
    prov = _build_prove_path_engine()
    assert diag.sampled_let_names == prov.sampled_let_names


def test_requirements_match() -> None:
    diag = _build_diagnostic_path_engine()
    prov = _build_prove_path_engine()
    assert [str(r) for r in diag.requirements] == [
        str(r) for r in prov.requirements
    ]


def test_proof_namespace_keys_match() -> None:
    diag = _build_diagnostic_path_engine()
    prov = _build_prove_path_engine()
    assert set(diag.proof_namespace.keys()) == set(prov.proof_namespace.keys())
    # Sampled-let entries must be present (as None) in both namespaces.
    for name in diag.sampled_let_names:
        assert name in diag.proof_namespace
        assert name in prov.proof_namespace
        assert diag.proof_namespace[name] is None
        assert prov.proof_namespace[name] is None


def test_subsets_pairs_match() -> None:
    diag = _build_diagnostic_path_engine()
    prov = _build_prove_path_engine()
    assert [(str(a), str(b)) for a, b in diag.subsets_pairs] == [
        (str(a), str(b)) for a, b in prov.subsets_pairs
    ]


def test_method_lookup_keys_match() -> None:
    diag = _build_diagnostic_path_engine()
    prov = _build_prove_path_engine()
    assert set(diag.method_lookup.keys()) == set(prov.method_lookup.keys())


def test_canonical_form_matches_across_paths() -> None:
    """End-to-end behavioral parity: canonicalizing step 0's game must
    produce the same canonical string from both engines. This catches
    drift in any transform that depends on the proof context."""
    diag = _build_diagnostic_path_engine()
    prov = _build_prove_path_engine()
    proof_file = frog_parser.parse_proof_file(PROOF_PATH)
    step = proof_file.steps[0]
    assert isinstance(step, frog_ast.Step)

    suppress = io.StringIO()
    with redirect_stdout(suppress), redirect_stderr(suppress):
        # pylint: disable=protected-access
        diag_game = diag._get_game_ast(step.challenger, step.reduction)
        prov_game = prov._get_game_ast(step.challenger, step.reduction)
        # pylint: enable=protected-access
        diag_canon = diag.canonicalize_game(copy.deepcopy(diag_game))
        prov_canon = prov.canonicalize_game(copy.deepcopy(prov_game))
    assert str(diag_canon) == str(prov_canon)


def test_canonicalization_trace_succeeds_on_requires_proof() -> None:
    """End-to-end smoke: the diagnostic CLI path must succeed on a proof
    that depends on `requires:` and sampled-let context, exercising
    `_setup_engine_for_proof` -> canonicalize-with-trace."""
    result = _capture_canonicalization_trace(
        PROOF_PATH, 0, allowed_root=str(EXAMPLES)
    )
    assert result["success"] is True
    assert result["converged"] is True
