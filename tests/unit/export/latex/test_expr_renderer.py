from proof_frog import frog_parser
from proof_frog.export.latex.expr_renderer import ExprRenderer
from proof_frog.export.latex.macros import MacroRegistry


def render(src: str) -> str:
    expr = frog_parser.parse_expression(src)
    return ExprRenderer(MacroRegistry()).render(expr)


def test_variable_plain_italic() -> None:
    assert render("x") == "x"


def test_subscript_split_trailing_digit() -> None:
    assert render("k0") == "k_{0}"


def test_subscript_split_underscore() -> None:
    assert render("m_b") == "m_{b}"


def test_lambda_keyword() -> None:
    assert render("lambda") == r"\lambda"


def test_plus_default_no_type() -> None:
    assert render("a + b") == "a + b"


def test_set_membership() -> None:
    assert render("a in S") == r"a \in S"


def test_set_difference() -> None:
    assert render(r"S \ T") == r"S \setminus T"


def test_cardinality() -> None:
    assert render("|x|") == "|x|"


def test_function_call_uses_macro_for_algorithm_names() -> None:
    out = render("PRF(k, r)")
    assert r"\PRF(k, r)" in out
