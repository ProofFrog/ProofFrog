"""Tests that ProofEngine._extract_subsets_pairs distinguishes == and subsets.

Both ``==`` and ``subsets`` constraints are extracted into ``subsets_pairs``
(safe for normalizing type annotations).  But only ``==`` constraints are
added to ``equality_pairs`` (safe for normalizing sampling distributions),
because ``subsets`` allows A ⊊ B where ``x <- A`` ≠ ``x <- B``.
"""

from proof_frog import frog_ast
from proof_frog.proof_engine import ProofEngine


def _make_engine_with_scheme(scheme: frog_ast.Scheme) -> ProofEngine:
    """Create a ProofEngine and inject a scheme into its namespace."""
    engine = ProofEngine()
    engine.proof_namespace["S"] = scheme
    engine._extract_subsets_pairs()  # pylint: disable=protected-access
    return engine


def _make_scheme(*requirements: frog_ast.Expression) -> frog_ast.Scheme:
    """Create a minimal scheme with the given requires clauses."""
    return frog_ast.Scheme(
        "TestScheme",
        [],
        [],
        [],
        [],
        list(requirements),
        None,
    )


def test_equality_constraint_in_both() -> None:
    """An ``==`` constraint should appear in both subsets_pairs and equality_pairs."""
    req = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS,
        frog_ast.Variable("KeySpace"),
        frog_ast.BitStringType(frog_ast.Integer(128)),
    )
    engine = _make_engine_with_scheme(_make_scheme(req))
    assert len(engine.subsets_pairs) == 1
    assert len(engine.equality_pairs) == 1


def test_subsets_constraint_not_in_equality_pairs() -> None:
    """A ``subsets`` constraint should be in subsets_pairs (for annotations)
    but NOT in equality_pairs (for sampling), because A ⊊ B changes the
    sampling distribution."""
    req = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.SUBSETS,
        frog_ast.Variable("KeySpace"),
        frog_ast.BitStringType(frog_ast.Integer(128)),
    )
    engine = _make_engine_with_scheme(_make_scheme(req))
    assert (
        len(engine.subsets_pairs) == 1
    ), "subsets constraints should be in subsets_pairs for annotation normalization"
    assert len(engine.equality_pairs) == 0, (
        "subsets constraints must NOT be in equality_pairs — "
        "replacing sampling from A with B when A ⊊ B changes distribution"
    )
