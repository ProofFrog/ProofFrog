"""B4: name-decoration suffixes render as math accents / superscripts."""

from proof_frog import frog_ast
from proof_frog.export.latex.expr_renderer import ExprRenderer
from proof_frog.export.latex.macros import MacroRegistry


def _r() -> ExprRenderer:
    return ExprRenderer(MacroRegistry())


def _var(name: str) -> str:
    return _r().render(frog_ast.Variable(name))


def test_star_renders_as_superscript_star() -> None:
    assert _var("ctStar") == r"ct^{*}"


def test_prime_renders_as_superscript_prime() -> None:
    assert _var("ekPrime") == r"ek^{\prime}"


def test_hat_renders_as_accent() -> None:
    assert _var("mHat") == r"\hat{m}"


def test_tilde_renders_as_accent() -> None:
    assert _var("xTilde") == r"\tilde{x}"


def test_bar_renders_as_overline() -> None:
    assert _var("yBar") == r"\overline{y}"


def test_star_with_trailing_digit_keeps_both_subscript_and_superscript() -> None:
    # Decoration sits on the superscript axis; the trailing digit subscripts,
    # so the two never collide into a double subscript.
    assert _var("ctStar0") == r"ct_{0}^{*}"


def test_accent_with_trailing_digit_subscripts_outside_the_accent() -> None:
    assert _var("mHat0") == r"\hat{m}_{0}"


def test_digit_before_decoration_subscripts() -> None:
    # An indexed challenge variable (ct1Star, ss2Star) puts the index on the
    # subscript axis and the star on the superscript: ct_{1}^{*}.
    assert _var("ct1Star") == r"ct_{1}^{*}"
    assert _var("ss2Star") == r"ss_{2}^{*}"


def test_false_positive_lowercase_star_stays_literal() -> None:
    # Only the camelCase capital form is a decoration; a lowercase trailing
    # "star" (e.g. polestar) must not become a superscript.
    assert _var("polestar") == "polestar"


def test_uppercase_boundary_not_decorated() -> None:
    # Decoration requires a camelCase boundary (lowercase/digit before the
    # suffix), so an all-caps run like "ABStar" is left alone.
    assert _var("ABStar") == "ABStar"


def test_plain_underscore_subscript_still_works() -> None:
    # Regression: the pre-existing single-subscript paths are unchanged.
    assert _var("ss_T") == r"ss_{T}"


def test_plain_trailing_digit_subscript_still_works() -> None:
    assert _var("k1") == r"k_{1}"


def test_greek_token_still_wins() -> None:
    assert _var("lambda") == r"\lambda"


def test_decorated_base_of_exponentiation_is_braced() -> None:
    # A superscript decoration on the base of an exponentiation must be braced
    # so the two superscripts do not stack into a pdflatex "Double superscript"
    # error: {x^{*}}^{sk}, not x^{*}^{sk}.
    expr = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EXPONENTIATE,
        frog_ast.Variable("xStar"),
        frog_ast.Variable("sk"),
    )
    assert _r().render(expr) == r"{x^{*}}^{sk}"
