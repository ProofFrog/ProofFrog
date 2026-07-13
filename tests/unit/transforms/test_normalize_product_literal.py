"""Tests for the NormalizeProductLiteral pass.

Instantiation/inlining substitution converts a Tuple literal whose members
are all bare variables (each ``Variable`` is both ``Expression`` and
``Type``) into a ``ProductType`` node, so tuple literals in expression
positions can arrive at canonicalization as ``ProductType`` nodes.
``NormalizeProductLiteral`` rewrites them back into ``Tuple`` nodes in
value positions so downstream passes (``FoldTupleIndex``,
``TupleEqualityDecompose``, ``RemoveUnreachable``'s Z3 encoding) recognise
them; type positions (declared types, sample spaces, ``|...|`` operands,
the RHS of ``in``/``subsets``) are left untouched.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.control_flow import RemoveUnreachableTransformer
from proof_frog.transforms.tuples import (
    NormalizeProductLiteral,
    NormalizeProductLiteralTransformer,
)
from proof_frog.visitors import NameTypeMap


def _product(*names: str) -> frog_ast.ProductType:
    """A ProductType-as-expression node, as the inliner manufactures them."""
    return frog_ast.ProductType([frog_ast.Variable(n) for n in names])


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _count(game: frog_ast.ASTNode, cls: type) -> int:
    from proof_frog.visitors import SearchVisitor

    total = 0
    remaining = game

    def is_cls(node: frog_ast.ASTNode) -> bool:
        return isinstance(node, cls) and id(node) not in seen

    seen: set[int] = set()
    while True:
        found = SearchVisitor(is_cls).visit(remaining)
        if found is None:
            return total
        seen.add(id(found))
        total += 1


def test_condition_product_literal_becomes_tuple() -> None:
    game = frog_parser.parse_game("""
    Game G(Set S, Set T) {
        S a;
        T b;
        S c;
        T d;
        Bool O() {
            if ([a, b] == [c, d]) {
                return true;
            }
            return false;
        }
    }
    """)
    # Mangle the parsed Tuples into ProductTypes, as the inliner would.
    cond = game.methods[0].block.statements[0].conditions[0]
    cond.left_expression = _product("a", "b")
    cond.right_expression = _product("c", "d")

    out = NormalizeProductLiteral().apply(game, _ctx())
    new_cond = out.methods[0].block.statements[0].conditions[0]
    assert isinstance(new_cond.left_expression, frog_ast.Tuple)
    assert isinstance(new_cond.right_expression, frog_ast.Tuple)
    assert str(new_cond) == "[a, b] == [c, d]"


def test_assignment_value_and_array_access_normalized() -> None:
    game = frog_parser.parse_game("""
    Game G(Set S, Set T) {
        S a;
        T b;
        Bool O() {
            T x = b;
            return true;
        }
    }
    """)
    stmt = game.methods[0].block.statements[0]
    # x = [a, b][1]; with the tuple literal mangled to a ProductType
    stmt.value = frog_ast.ArrayAccess(_product("a", "b"), frog_ast.Integer(1))

    out = NormalizeProductLiteral().apply(game, _ctx())
    new_value = out.methods[0].block.statements[0].value
    assert isinstance(new_value, frog_ast.ArrayAccess)
    assert isinstance(new_value.the_array, frog_ast.Tuple)


def test_size_operand_and_in_rhs_left_alone() -> None:
    game = frog_parser.parse_game("""
    Game G(Set S, Set T) {
        S a;
        T b;
        Bool O() {
            return true;
        }
    }
    """)
    ret = game.methods[0].block.statements[0]
    # return (|[S, T]| == |[S, T]|) — cardinality of a product SPACE: the
    # ProductType under |...| must stay a ProductType.
    size = frog_ast.UnaryOperation(frog_ast.UnaryOperators.SIZE, _product("S", "T"))
    ret.expression = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS, size, frog_ast.Integer(4)
    )
    out = NormalizeProductLiteral().apply(game, _ctx())
    new_ret = out.methods[0].block.statements[0]
    assert isinstance(
        new_ret.expression.left_expression.expression, frog_ast.ProductType
    )

    # a in [S, T] — membership in a product SPACE: RHS stays a ProductType.
    ret2 = frog_ast.ReturnStatement(
        frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.IN,
            frog_ast.Variable("a"),
            _product("S", "T"),
        )
    )
    game.methods[0].block.statements[0] = ret2
    out2 = NormalizeProductLiteral().apply(game, _ctx())
    new_ret2 = out2.methods[0].block.statements[0]
    assert isinstance(new_ret2.expression.right_expression, frog_ast.ProductType)


def test_sample_space_left_alone() -> None:
    game = frog_parser.parse_game("""
    Game G(Set S, Set T) {
        Bool O() {
            S x <- S;
            return true;
        }
    }
    """)
    stmt = game.methods[0].block.statements[0]
    stmt.sampled_from = _product("S", "T")
    out = NormalizeProductLiteral().apply(game, _ctx())
    assert isinstance(
        out.methods[0].block.statements[0].sampled_from, frog_ast.ProductType
    )


def test_near_miss_on_unconvertible_product() -> None:
    game = frog_parser.parse_game("""
    Game G(Set S) {
        S a;
        Bool O() {
            if (a == a) {
                return true;
            }
            return false;
        }
    }
    """)
    cond = game.methods[0].block.statements[0].conditions[0]
    # A ProductType with a genuine (non-Expression) type member cannot be a
    # tuple literal; the pass must decline and record a near-miss.
    cond.right_expression = frog_ast.ProductType(
        [frog_ast.Variable("a"), frog_ast.IntType()]
    )
    ctx = _ctx()
    NormalizeProductLiteral().apply(game, ctx)
    assert any(
        nm.transform_name == "Normalize Product-Literal Tuples"
        for nm in ctx.near_misses
    )


def test_unreachable_qstar_branch_eliminated_after_normalization() -> None:
    """End-to-end regression for the CG INDCCA_T derived-key hop: the
    inlined helper's excluded-query branch is semantically dead given the
    challenge exclusion and the C2PRI abort guard, but arrives with its
    tuple literals mangled into ProductType nodes. After normalization,
    RemoveUnreachable must eliminate it."""
    game = frog_parser.parse_game("""
    Game G(Set CtSpace, Set ElemSpace, Int n) {
        BitString<n> field1;
        CtSpace field3;
        ElemSpace field5;
        Function<CtSpace, BitString<n>> F;

        BitString<8>? Decaps([CtSpace, ElemSpace] ct) {
            if (ct == [field3, field5]) {
                return None;
            }
            CtSpace v7 = ct[0];
            ElemSpace v8 = ct[1];
            BitString<n> v9 = F(v7);
            if (field5 == v8 && (field3 != v7 && field1 == v9)) {
                BitString<8> r <- BitString<8>;
                return r;
            }
            if ([field1, field5] == [v9, v8]) {
                return None;
            }
            BitString<8> out <- BitString<8>;
            return out;
        }
    }
    """)
    # Mangle all three tuple literals into ProductType nodes, as arrives
    # from inlining.
    decaps = game.methods[0]
    stmts = decaps.block.statements
    stmts[0].conditions[0].right_expression = _product("field3", "field5")
    if_stmts = [s for s in stmts if isinstance(s, frog_ast.IfStatement)]
    qstar_if = if_stmts[-1]
    qstar_if.conditions[0].left_expression = _product("field1", "field5")
    qstar_if.conditions[0].right_expression = _product("v9", "v8")

    ctx = _ctx()
    normalized = NormalizeProductLiteral().apply(game, ctx)
    out = RemoveUnreachableTransformer(normalized, ctx).transform(normalized)
    assert str(out).count("if (") == 2, f"dead qStar branch not removed:\n{out}"


def test_unreachable_qstar_branch_eliminated_even_without_normalization() -> None:
    """Defense-in-depth: Z3FormulaVisitor's leave_product_type handler
    encodes ProductType tuple literals componentwise, so RemoveUnreachable
    eliminates the dead branch even on a NOT-yet-normalized AST. (Before
    that handler existed, the mangled literals' children leaked onto the
    visitor stack and produced a wrong formula, and this branch
    survived — the CG INDCCA_T hop failures.)"""
    game = frog_parser.parse_game("""
    Game G(Set CtSpace, Set ElemSpace, Int n) {
        BitString<n> field1;
        CtSpace field3;
        ElemSpace field5;
        Function<CtSpace, BitString<n>> F;

        BitString<8>? Decaps([CtSpace, ElemSpace] ct) {
            if (ct == [field3, field5]) {
                return None;
            }
            CtSpace v7 = ct[0];
            ElemSpace v8 = ct[1];
            BitString<n> v9 = F(v7);
            if (field5 == v8 && (field3 != v7 && field1 == v9)) {
                BitString<8> r <- BitString<8>;
                return r;
            }
            if ([field1, field5] == [v9, v8]) {
                return None;
            }
            BitString<8> out <- BitString<8>;
            return out;
        }
    }
    """)
    decaps = game.methods[0]
    stmts = decaps.block.statements
    stmts[0].conditions[0].right_expression = _product("field3", "field5")
    if_stmts = [s for s in stmts if isinstance(s, frog_ast.IfStatement)]
    qstar_if = if_stmts[-1]
    qstar_if.conditions[0].left_expression = _product("field1", "field5")
    qstar_if.conditions[0].right_expression = _product("v9", "v8")

    ctx = _ctx()
    out = RemoveUnreachableTransformer(game, ctx).transform(game)
    assert str(out).count("if (") == 2, f"dead qStar branch not removed:\n{out}"


def test_transformer_no_change_returns_same_block() -> None:
    game = frog_parser.parse_game("""
    Game G(Set S) {
        S a;
        Bool O() {
            if (a == a) {
                return true;
            }
            return false;
        }
    }
    """)
    out = NormalizeProductLiteralTransformer(_ctx()).transform(game)
    assert out == game
