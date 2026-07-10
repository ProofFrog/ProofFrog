"""Part 3: type-dependent operator rendering (`+`/`||` disambiguation).

`+` and `||` are overloaded: on ``BitString`` they are XOR and
concatenation; on ``Bool``/``Int`` they are addition and logical OR. The
renderer disambiguates from operand types, supplied either per-node
(``type_of`` keyed by ``id(node)``) or by name (``name_types``).
"""

from pathlib import Path

from proof_frog import frog_ast, frog_parser
from proof_frog.export.latex.backends.cryptocode import CryptocodeBackend
from proof_frog.export.latex.expr_renderer import ExprRenderer
from proof_frog.export.latex.macros import MacroRegistry
from proof_frog.export.latex.module_renderer import ModuleRenderer
from proof_frog.visitors import NameTypeMap

REPO = Path(__file__).resolve().parents[4]


def _or(a: frog_ast.Expression, b: frog_ast.Expression) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(
        operator=frog_ast.BinaryOperators.OR, left_expression=a, right_expression=b
    )


def test_or_on_bitstring_renders_concat_via_id_map() -> None:
    a = frog_ast.Variable(name="a")
    b = frog_ast.Variable(name="b")
    type_of = {id(a): frog_ast.BitStringType()}
    r = ExprRenderer(MacroRegistry(), type_of=type_of)
    assert r.render(_or(a, b)) == r"a \| b"


def test_or_without_type_info_stays_lor() -> None:
    a = frog_ast.Variable(name="a")
    b = frog_ast.Variable(name="b")
    r = ExprRenderer(MacroRegistry())
    assert r.render(_or(a, b)) == r"a \lor b"


def test_or_on_bitstring_via_name_types() -> None:
    a = frog_ast.Variable(name="x")
    b = frog_ast.Variable(name="y")
    name_types = NameTypeMap()
    name_types.set("x", frog_ast.BitStringType())
    name_types.set("y", frog_ast.BitStringType())
    r = ExprRenderer(MacroRegistry(), name_types=name_types)
    assert r.render(_or(a, b)) == r"x \| y"


def test_plus_on_bitstring_via_name_types() -> None:
    a = frog_ast.Variable(name="u")
    b = frog_ast.Variable(name="m")
    name_types = NameTypeMap()
    name_types.set("u", frog_ast.BitStringType())
    r = ExprRenderer(MacroRegistry(), name_types=name_types)
    assert (
        r.render(
            frog_ast.BinaryOperation(
                operator=frog_ast.BinaryOperators.ADD,
                left_expression=a,
                right_expression=b,
            )
        )
        == r"u \oplus m"
    )


def test_or_on_bool_name_types_stays_lor() -> None:
    a = frog_ast.Variable(name="p")
    b = frog_ast.Variable(name="q")
    name_types = NameTypeMap()
    name_types.set("p", frog_ast.BoolType())
    name_types.set("q", frog_ast.BoolType())
    r = ExprRenderer(MacroRegistry(), name_types=name_types)
    assert r.render(_or(a, b)) == r"p \lor q"


def test_tripling_prg_concatenation_renders_correctly() -> None:
    # Integration (plan Step 3): `return x || result2;` where both operands are
    # declared BitString must render as concatenation, not logical OR.
    scheme = str(REPO / "examples/Schemes/PRG/TriplingPRG.scheme")
    s = frog_parser.parse_scheme_file(scheme)
    renderer = ModuleRenderer(CryptocodeBackend())
    out = renderer.render_scheme(s)
    assert r"\lor" not in out
    assert r"x \| \mathit{result}_{2}" in out
