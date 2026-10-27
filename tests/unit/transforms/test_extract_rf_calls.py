"""Tests for the ExtractRFCalls transform pass.

F-024: the pass hoists an embedded RF-field call into a freshly declared
typed local.  The minted name must be freshened against every identifier in
scope (fields, params, locals); otherwise it can shadow a same-named game
field, and the downstream single-use inliner then discards the field read,
silently changing the game's distribution.
"""

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.random_functions import ExtractRFCalls
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def test_minted_name_avoids_field_collision() -> None:
    # The game already declares a field __rf_extract_0__.  Extracting the
    # embedded RF call must NOT mint that same name (which would shadow the
    # field), so the field read survives.
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Function<BitString<n>, BitString<n>> RF;
            BitString<n> __rf_extract_0__;
            Void Initialize() {
                RF <- Function<BitString<n>, BitString<n>>;
                __rf_extract_0__ = 0^n;
            }
            BitString<n> Oracle(BitString<n> v, BitString<n> m) {
                BitString<n> y = m + RF(v);
                return __rf_extract_0__;
            }
        }
        """)
    out = ExtractRFCalls().apply(game, _ctx())

    # The pre-existing field must remain a field.
    assert any(fld.name == "__rf_extract_0__" for fld in out.fields)

    # The minted local must not collide with the field name.
    oracle = next(m for m in out.methods if m.signature.name == "Oracle")
    minted: list[str] = []
    for stmt in oracle.block.statements:
        if (
            isinstance(stmt, frog_ast.Assignment)
            and stmt.the_type is not None
            and isinstance(stmt.var, frog_ast.Variable)
            and stmt.var.name.startswith("__rf_extract_")
            and isinstance(stmt.value, frog_ast.FuncCall)
        ):
            minted.append(stmt.var.name)
    assert minted, "expected the RF call to be hoisted into a fresh local"
    assert "__rf_extract_0__" not in minted

    # The return still reads the field, not the hoisted RF call.
    ret = oracle.block.statements[-1]
    assert isinstance(ret, frog_ast.ReturnStatement)
    assert isinstance(ret.expression, frog_ast.Variable)
    assert ret.expression.name == "__rf_extract_0__"


def test_minted_name_fresh_without_collision() -> None:
    # No collision: the pass still fires and hoists the embedded call.
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Function<BitString<n>, BitString<n>> RF;
            Void Initialize() {
                RF <- Function<BitString<n>, BitString<n>>;
            }
            BitString<n> Oracle(BitString<n> v, BitString<n> m) {
                return m + RF(v);
            }
        }
        """)
    out = ExtractRFCalls().apply(game, _ctx())
    oracle = next(m for m in out.methods if m.signature.name == "Oracle")
    hoisted = [
        stmt
        for stmt in oracle.block.statements
        if isinstance(stmt, frog_ast.Assignment)
        and isinstance(stmt.value, frog_ast.FuncCall)
        and isinstance(stmt.value.func, frog_ast.Variable)
        and stmt.value.func.name == "RF"
    ]
    assert hoisted, "expected the embedded RF call to be hoisted"


# ---------------------------------------------------------------------------
# Hoisting stays within the statement's own evaluation
# ---------------------------------------------------------------------------

_HOIST_GAME = """
    Game G() {{
        Set<BitString<8>> S;
        Function<BitString<8>, BitString<8>> RF;
        Void Initialize() {{
            RF <- Function<BitString<8>, BitString<8>>;
        }}
        BitString<8> Oracle(BitString<8> c, BitString<8> m, Bool b, Int k) {{
            BitString<8> r <-uniq[S] BitString<8>;
            {body}
        }}
    }}
    """


def _oracle_after(body: str) -> frog_ast.Method:
    game = frog_parser.parse_game(_HOIST_GAME.format(body=body))
    out = ExtractRFCalls().apply(game, _ctx())
    return next(m for m in out.methods if m.signature.name == "Oracle")


def _is_rf_assignment(stmt: frog_ast.Statement) -> bool:
    return (
        isinstance(stmt, frog_ast.Assignment)
        and isinstance(stmt.value, frog_ast.FuncCall)
        and isinstance(stmt.value.func, frog_ast.Variable)
        and stmt.value.func.name == "RF"
    )


def test_call_after_nested_write_not_hoisted() -> None:
    # Hoisting `RF(r)` above the `if` would evaluate it on the drawn `r`, not
    # on `0b00`, and query RF when `b` is false.
    oracle = _oracle_after(
        "if (b) { r = 0b00000000; return RF(r); } return 0b11111111;"
    )
    top = oracle.block.statements
    assert not any(_is_rf_assignment(stmt) for stmt in top)
    branch = top[1]
    assert isinstance(branch, frog_ast.IfStatement)
    inner = branch.blocks[0].statements
    assert isinstance(inner[0], frog_ast.Assignment) and not _is_rf_assignment(inner[0])
    assert _is_rf_assignment(inner[1])
    assert isinstance(inner[2], frog_ast.ReturnStatement)


@pytest.mark.parametrize(
    "body",
    [
        "if (b) { return m + RF(r); } return m;",
        "if (b) { return m; } else { return m + RF(r); }",
        "if (b) { return m; } else if (RF(r) == m) { return c; } return m;",
        "for (Int i = 0 to k) { m = m + RF(r); } return m;",
        "for (BitString<8> e in S) { m = m + RF(e); } return m;",
    ],
)
def test_call_in_branch_loop_or_later_condition_not_hoisted(body: str) -> None:
    # Even with no write before it, a call that does not run on every path
    # stays inside its statement; one in a block is extracted there instead.
    oracle = _oracle_after(body)
    assert not any(_is_rf_assignment(stmt) for stmt in oracle.block.statements)


def test_call_in_branch_extracted_inside_branch() -> None:
    oracle = _oracle_after("if (b) { return m + RF(r); } return m;")
    branch = oracle.block.statements[1]
    assert isinstance(branch, frog_ast.IfStatement)
    inner = branch.blocks[0].statements
    assert _is_rf_assignment(inner[0])
    assert isinstance(inner[1], frog_ast.ReturnStatement)


@pytest.mark.parametrize(
    "body",
    [
        "return m + RF(r);",
        "BitString<8> y = m + RF(r); return y;",
        "if (RF(r) == m) { return c; } return m;",
        "if (RF(r) == m) { r = c; return c; } return m;",
    ],
)
def test_call_in_statement_itself_hoisted(body: str) -> None:
    # The expression of a simple statement and the first condition of an `if`
    # are evaluated before anything else in the statement.
    oracle = _oracle_after(body)
    stmts = oracle.block.statements
    assert _is_rf_assignment(stmts[1])
    rf_args = stmts[1].value.args  # type: ignore[attr-defined]
    assert rf_args == [frog_ast.Variable("r")]
