"""Tests that ProofEngine._extract_subsets_pairs distinguishes == and subsets.

Both ``==`` and ``subsets`` constraints are extracted into ``subsets_pairs``
(safe for normalizing type annotations).  But only ``==`` constraints are
added to ``equality_pairs`` (safe for normalizing sampling distributions),
because ``subsets`` allows A ⊊ B where ``x <- A`` ≠ ``x <- B``.

F-333: constraints are harvested only from schemes in the theorem's
dependency cone, so each test wires the scheme (bound as ``S``) into the
theorem game; `test_decoy_scheme_out_of_cone_not_harvested` covers the
complementary case.
"""

from proof_frog import frog_ast
from proof_frog.proof_engine import ProofEngine


def _proof_file_referencing(*names: str) -> frog_ast.ProofFile:
    """A minimal ProofFile whose theorem references the given let-names, so
    schemes bound under those names fall inside the dependency cone."""
    theorem = frog_ast.ParameterizedGame(
        "TheoremGame", [frog_ast.Variable(n) for n in names]
    )
    return frog_ast.ProofFile(
        imports=[],
        helpers=[],
        lets=[],
        assumptions=[],
        lemmas=[],
        max_calls=None,
        theorem=theorem,
        steps=[],
    )


def _make_engine_with_scheme(
    scheme: frog_ast.Scheme, in_cone: bool = True
) -> ProofEngine:
    """Create a ProofEngine, inject a scheme as ``S``, and run the harvest.

    ``in_cone`` controls whether the minimal proof file's theorem references
    ``S`` (so its requirements are honored) or not (so they are scoped out).
    """
    engine = ProofEngine()
    engine.proof_namespace["S"] = scheme
    proof_file = _proof_file_referencing("S") if in_cone else _proof_file_referencing()
    engine._extract_subsets_pairs(proof_file)  # pylint: disable=protected-access
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


def test_decoy_scheme_out_of_cone_not_harvested() -> None:
    """F-333: a scheme not referenced by the theorem (a decoy in the let:
    block only) has NONE of its requirements harvested, so it cannot inject
    an equality license into an unrelated game."""
    req = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS,
        frog_ast.Variable("KeySpace"),
        frog_ast.BitStringType(frog_ast.Integer(128)),
    )
    engine = _make_engine_with_scheme(_make_scheme(req), in_cone=False)
    assert len(engine.subsets_pairs) == 0
    assert len(engine.equality_pairs) == 0
