"""Tests for the ExtractRFCalls transform pass.

F-024: the pass hoists an embedded RF-field call into a freshly declared
typed local.  The minted name must be freshened against every identifier in
scope (fields, params, locals); otherwise it can shadow a same-named game
field, and the downstream single-use inliner then discards the field read,
silently changing the game's distribution.
"""

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
