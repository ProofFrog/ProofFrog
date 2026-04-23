"""Tests for ``ContractGeneratorExpToField``.

Rewrites ``G.generator ^ v`` subexpressions as ``F`` (and
``G.generator ^ (v*X)`` as ``F ^ X``) when a same-game field ``F`` is
assigned once at top level of ``Initialize`` with RHS ``G.generator ^ v``
and ``F`` is multi-use.  Complements ``RefactorGroupElemFieldExp`` by
operating on arbitrary expression positions, not just field-RHS.
"""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser, visitors
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.inlining import ContractGeneratorExpToField


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=visitors.NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return ContractGeneratorExpToField().apply(game, _ctx())


# --------------------------------------------------------------------------
# Positive
# --------------------------------------------------------------------------


def test_contracts_bare_generator_exp_subexpression() -> None:
    """``pk = G.generator ^ a`` exists; a use site of ``G.generator ^ a``
    in Initialize post-inline form is contracted to ``pk``."""
    source = """
    Game G(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
        GroupElem<G> pk;
        BitString<n> val;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            pk = G.generator ^ a;
            val = H((G.generator ^ a) ^ r);
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    expected = """
    Game G(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
        GroupElem<G> pk;
        BitString<n> val;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            pk = G.generator ^ a;
            val = H(pk ^ r);
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(expected), str(got)


def test_contracts_post_power_of_power_form() -> None:
    """``pk = G.generator ^ a`` and a use site ``G.generator ^ (a*r)`` —
    post power-of-power fold — is contracted to ``pk ^ r``."""
    source = """
    Game G(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
        GroupElem<G> pk;
        BitString<n> val;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            pk = G.generator ^ a;
            val = H(G.generator ^ (a * r));
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    expected = """
    Game G(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
        GroupElem<G> pk;
        BitString<n> val;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            pk = G.generator ^ a;
            val = H(pk ^ r);
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(expected), str(got)


def test_contracts_in_non_initialize_method() -> None:
    """Use site in a non-Initialize method is also rewritten."""
    source = """
    Game G(Group G) {
        GroupElem<G> pk;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            pk = G.generator ^ a;
        }
        GroupElem<G> Oracle(ModInt<G.order> r) {
            return G.generator ^ (a * r);
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    expected = """
    Game G(Group G) {
        GroupElem<G> pk;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            pk = G.generator ^ a;
        }
        GroupElem<G> Oracle(ModInt<G.order> r) {
            return pk ^ r;
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(expected), str(got)


def test_handles_commuted_product() -> None:
    """``G.generator ^ (r * a)`` (a on right) is also contracted."""
    source = """
    Game G(Group G) {
        GroupElem<G> pk;
        GroupElem<G> cached;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            pk = G.generator ^ a;
            cached = G.generator ^ (r * a);
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    expected = """
    Game G(Group G) {
        GroupElem<G> pk;
        GroupElem<G> cached;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            pk = G.generator ^ a;
            cached = pk ^ r;
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(expected), str(got)


# --------------------------------------------------------------------------
# Negative
# --------------------------------------------------------------------------


def test_does_not_fire_when_field_single_use() -> None:
    """If ``pk`` is only used in its own RHS definition (no other
    reads), contraction would leave pk as 'single-use' for
    InlineSingleUseField to unwind, re-triggering power-of-power.
    Guard against this by requiring F to be multi-use."""
    source = """
    Game G(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
        GroupElem<G> pk;
        BitString<n> val;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            pk = G.generator ^ a;
            val = H(G.generator ^ (a * r));
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(source), str(got)


def test_does_not_fire_when_field_reassigned() -> None:
    """If pk is reassigned in a method, contraction's soundness is
    broken — it assumes pk's value at Init-end is G.generator ^ a."""
    source = """
    Game G(Group G) {
        GroupElem<G> pk;
        GroupElem<G> other;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            pk = G.generator ^ a;
            other = G.generator ^ a;
        }
        Void Reset(GroupElem<G> g) {
            pk = g;
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(source), str(got)


def test_does_not_fire_when_exponent_not_bare_variable() -> None:
    """RHS must be ``G.generator ^ <bare Variable>``, not an arbitrary
    expression."""
    source = """
    Game G(Group G) {
        GroupElem<G> pk;
        GroupElem<G> other;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> b <- ModInt<G.order>;
            pk = G.generator ^ (a + b);
            other = G.generator ^ (a + b);
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(source), str(got)


def test_does_not_fire_when_exponent_reassigned() -> None:
    """The exponent variable ``a`` must be sampled once and not reassigned."""
    source = """
    Game G(Group G) {
        GroupElem<G> pk;
        GroupElem<G> other;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            pk = G.generator ^ a;
            a = a + 1;
            other = G.generator ^ a;
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(source), str(got)


def test_does_not_contract_before_defining_assignment_in_initialize() -> None:
    """In Initialize, if the use site precedes ``pk``'s defining
    assignment, contraction would produce use-before-define.  The
    transform must skip rewriting at that position."""
    source = """
    Game G(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
        GroupElem<G> pk;
        BitString<n> val;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            val = H(G.generator ^ (a * r));
            pk = G.generator ^ a;
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    got = _apply(source)
    # val's RHS must NOT reference pk (since pk is defined afterwards).
    init = next(m for m in got.methods if m.signature.name == "Initialize")
    val_assign = next(
        s
        for s in init.block.statements
        if isinstance(s, frog_ast.Assignment)
        and isinstance(s.var, frog_ast.Variable)
        and s.var.name == "val"
    )
    from proof_frog.visitors import VariableCollectionVisitor  # pylint: disable=import-outside-toplevel

    free_vars = {
        v.name for v in VariableCollectionVisitor().visit(val_assign.value)
    }
    assert "pk" not in free_vars, f"val's RHS references pk: {free_vars}"


def test_contracts_after_defining_assignment_in_initialize() -> None:
    """When the use site is AFTER ``pk = G.generator ^ a`` in Initialize,
    contraction is sound and should fire."""
    source = """
    Game G(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
        GroupElem<G> pk;
        BitString<n> val;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            pk = G.generator ^ a;
            val = H(G.generator ^ (a * r));
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    expected = """
    Game G(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
        GroupElem<G> pk;
        BitString<n> val;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            pk = G.generator ^ a;
            val = H(pk ^ r);
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(expected), str(got)


def test_does_not_rewrite_field_own_defining_assignment() -> None:
    """The statement ``pk = G.generator ^ a`` itself must not be rewritten
    to ``pk = pk`` — that would be a tautology and wipe out the sample.
    The pk field is read elsewhere so the multi-use guard is satisfied."""
    source = """
    Game G(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
        GroupElem<G> pk;
        BitString<n> cached;

        Void Initialize() {
            ModInt<G.order> a <- ModInt<G.order>;
            ModInt<G.order> r <- ModInt<G.order>;
            pk = G.generator ^ a;
            cached = H(G.generator ^ (a * r));
        }
        GroupElem<G> Read() {
            return pk;
        }
    }
    """
    got = _apply(source)
    # Find pk's assignment and ensure it still has G.generator ^ a (not pk = pk)
    init = next(m for m in got.methods if m.signature.name == "Initialize")
    pk_assign = next(
        s
        for s in init.block.statements
        if isinstance(s, frog_ast.Assignment)
        and isinstance(s.var, frog_ast.Variable)
        and s.var.name == "pk"
    )
    assert isinstance(pk_assign.value, frog_ast.BinaryOperation)
    assert pk_assign.value.operator == frog_ast.BinaryOperators.EXPONENTIATE
    # Verify RHS is G.generator ^ a, not contracted to a self-reference.
    assert isinstance(pk_assign.value.right_expression, frog_ast.Variable)
    assert pk_assign.value.right_expression.name == "a"
