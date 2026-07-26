"""Group-exponent extension of ``InjectiveEqualitySimplify``.

When the engine has a recognized injective wrapper (per the
:mod:`proof_frog.transforms._wrappers` protocol) on both sides of an equality
with the same identity key, the transform rewrites
``wrap(a) == wrap(b)  →  a == b`` (and the corresponding ``!=`` form).

For the :class:`GroupExponentWrapper`, this means ``a^k == b^k → a == b``
when the proof declares ``requires <group>.order is prime;`` and ``k`` is
syntactically known-nonzero (sampled via ``<-uniq[{0}]``).
"""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser, visitors
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.algebraic import InjectiveEqualitySimplify


def _ctx(
    requirements: list[frog_ast.StructuralRequirement] | None = None,
    group_name: str = "G",
) -> PipelineContext:
    ns: frog_ast.Namespace = {group_name: None}
    return PipelineContext(
        variables={},
        proof_let_types=visitors.NameTypeMap(),
        proof_namespace=ns,
        subsets_pairs=[],
        requirements=requirements or [],
    )


def _prime_req(group_name: str = "G") -> frog_ast.StructuralRequirement:
    return frog_ast.StructuralRequirement(
        kind="prime",
        target=frog_ast.FieldAccess(frog_ast.Variable(group_name), "order"),
    )


def _apply(source: str, ctx: PipelineContext) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return InjectiveEqualitySimplify().apply(game, ctx)


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------


def test_group_exp_equality_rewrites_under_prime_and_nonzero() -> None:
    source = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> a;
        GroupElem<G> b;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
        }
        Bool Query() {
            return a ^ sk == b ^ sk;
        }
    }
    """
    expected = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> a;
        GroupElem<G> b;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
        }
        Bool Query() {
            return a == b;
        }
    }
    """
    got = _apply(source, _ctx([_prime_req()]))
    assert got == frog_parser.parse_game(expected), str(got)


def test_group_exp_disequality_rewrites() -> None:
    source = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> a;
        GroupElem<G> b;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
        }
        Bool Query() {
            return a ^ sk != b ^ sk;
        }
    }
    """
    expected = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> a;
        GroupElem<G> b;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
        }
        Bool Query() {
            return a != b;
        }
    }
    """
    got = _apply(source, _ctx([_prime_req()]))
    assert got == frog_parser.parse_game(expected), str(got)


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------


def test_blocked_without_prime_requirement() -> None:
    source = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> a;
        GroupElem<G> b;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
        }
        Bool Query() {
            return a ^ sk == b ^ sk;
        }
    }
    """
    ctx = _ctx([])  # no prime-order requirement
    got = _apply(source, ctx)
    assert got == frog_parser.parse_game(source), str(got)
    misses = [
        nm for nm in ctx.near_misses if nm.transform_name == "Injective Equality Simplify"
    ]
    assert misses, "expected near-miss citing missing prime-order requirement"
    assert any("prime" in nm.reason for nm in misses), [nm.reason for nm in misses]


def test_blocked_when_exponent_not_known_nonzero() -> None:
    source = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> a;
        GroupElem<G> b;

        Void Initialize() {
            sk <- ModInt<G.order>;
        }
        Bool Query() {
            return a ^ sk == b ^ sk;
        }
    }
    """
    ctx = _ctx([_prime_req()])
    got = _apply(source, ctx)
    assert got == frog_parser.parse_game(source), str(got)
    misses = [
        nm for nm in ctx.near_misses if nm.transform_name == "Injective Equality Simplify"
    ]
    assert misses, "expected near-miss citing non-nonzero exponent"
    assert any("nonzero" in nm.reason for nm in misses), [nm.reason for nm in misses]


def test_field_substitution_fires_when_one_side_is_field_var() -> None:
    """``field1 == c^sk`` where ``field1 = g^v1 ^ sk`` (i.e. base is another
    cross-method-visible field) should rewrite via field-RHS substitution
    + exponent factoring to ``field2 == c``."""
    source = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> field1;
        GroupElem<G> field2;
        GroupElem<G> c;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
            ModInt<G.order> v1 <- ModInt<G.order>;
            field2 = G.generator ^ v1;
            field1 = field2 ^ sk;
        }
        Bool Q() {
            return field1 == c ^ sk;
        }
    }
    """
    expected = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> field1;
        GroupElem<G> field2;
        GroupElem<G> c;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
            ModInt<G.order> v1 <- ModInt<G.order>;
            field2 = G.generator ^ v1;
            field1 = field2 ^ sk;
        }
        Bool Q() {
            return field2 == c;
        }
    }
    """
    got = _apply(source, _ctx([_prime_req()]))
    assert got == frog_parser.parse_game(expected), str(got)


def test_field_substitution_blocked_when_rhs_has_local_var() -> None:
    """If the field's RHS references a variable local to Initialize, the
    substitution must NOT fire (the local would become out of scope at the
    use site)."""
    source = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> field1;
        GroupElem<G> c;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
            ModInt<G.order> v1 <- ModInt<G.order>;
            field1 = G.generator ^ (sk * v1);
        }
        Bool Q() {
            return field1 == c ^ sk;
        }
    }
    """
    got = _apply(source, _ctx([_prime_req()]))
    assert got == frog_parser.parse_game(source), str(got)


def test_factoring_fires_when_exponent_is_product() -> None:
    """``g^(sk*v1) == c^sk`` factors as ``(g^v1)^sk == c^sk → g^v1 == c``."""
    source = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> c;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
        }
        Bool Q(ModInt<G.order> v1) {
            return G.generator ^ (sk * v1) == c ^ sk;
        }
    }
    """
    expected = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> c;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
        }
        Bool Q(ModInt<G.order> v1) {
            return G.generator ^ v1 == c;
        }
    }
    """
    got = _apply(source, _ctx([_prime_req()]))
    assert got == frog_parser.parse_game(expected), str(got)


def test_different_exponents_does_not_fire() -> None:
    """``a^k1 == b^k2`` with distinct k's must not simplify."""
    source = """
    Game G(Group G) {
        ModInt<G.order> sk;
        ModInt<G.order> tk;
        GroupElem<G> a;
        GroupElem<G> b;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
            tk <-uniq[{0}] ModInt<G.order>;
        }
        Bool Query() {
            return a ^ sk == b ^ tk;
        }
    }
    """
    got = _apply(source, _ctx([_prime_req()]))
    assert got == frog_parser.parse_game(source), str(got)


def test_f249_method_param_not_resolved_as_group_elem() -> None:
    """F-249: `_expr_is_group_elem_on_game` must NOT type a bare variable by a
    method PARAMETER -- a param is local to its method, and scanning every
    method would launder a `GroupElem<G1>` param in one method onto a
    same-named `GroupElem<G2>` operand in another (applying G1's prime-order
    certificate to a composite-order G2 and rewriting `x^k == y^k -> x == y`)."""
    from proof_frog.transforms._wrappers import _expr_is_group_elem_on_game

    game = frog_parser.parse_game(
        """
        Game G(Group G1, Group G2) {
            GroupElem<G1> Probe(GroupElem<G1> x) {
                return x;
            }
            Bool Test(GroupElem<G2> x) {
                return x == x;
            }
        }
        """
    )
    # `x` is only a method parameter (GroupElem<G1> in Probe, GroupElem<G2> in
    # Test) -- not a game field/parameter -- so it must not resolve.
    assert _expr_is_group_elem_on_game(frog_ast.Variable("x"), game) is None


def test_f249_game_field_still_resolved_as_group_elem() -> None:
    """Positive control: a game FIELD typed GroupElem<G> (truly global) still
    resolves to its group."""
    from proof_frog.transforms._wrappers import _expr_is_group_elem_on_game

    game = frog_parser.parse_game(
        """
        Game G(Group G1) {
            GroupElem<G1> fld;
            Bool Test() {
                return fld == fld;
            }
        }
        """
    )
    assert _expr_is_group_elem_on_game(frog_ast.Variable("fld"), game) is not None


def test_f249_agreeing_method_params_resolve() -> None:
    """Narrowed control: when every method that declares a same-named GroupElem
    parameter agrees on the SAME group, the type is unambiguous and resolves
    (so legitimate method-param group operands still work, e.g. HashedElGamal)."""
    from proof_frog.transforms._wrappers import _expr_is_group_elem_on_game

    game = frog_parser.parse_game(
        """
        Game G(Group G1) {
            GroupElem<G1> A(GroupElem<G1> x) {
                return x;
            }
            Bool B(GroupElem<G1> x) {
                return x == x;
            }
        }
        """
    )
    # `x` is a GroupElem<G1> parameter in BOTH methods -> unambiguous -> resolves.
    assert _expr_is_group_elem_on_game(frog_ast.Variable("x"), game) is not None
