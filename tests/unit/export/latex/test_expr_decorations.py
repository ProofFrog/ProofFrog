"""B4: name-decoration suffixes render as math accents / superscripts."""

from proof_frog import frog_ast
from proof_frog.export.latex.expr_renderer import ExprRenderer
from proof_frog.export.latex.macros import MacroRegistry


def _r() -> ExprRenderer:
    return ExprRenderer(MacroRegistry())


def _var(name: str) -> str:
    return _r().render(frog_ast.Variable(name))


def test_star_renders_as_superscript_star() -> None:
    # Multi-letter stems render as one italic unit (\mathit); the star sits on
    # the superscript axis.
    assert _var("ctStar") == r"\mathit{ct}^{*}"


def test_prime_renders_as_superscript_prime() -> None:
    assert _var("ekPrime") == r"\mathit{ek}^{\prime}"


def test_hat_renders_as_accent() -> None:
    assert _var("mHat") == r"\hat{m}"


def test_tilde_renders_as_accent() -> None:
    assert _var("xTilde") == r"\tilde{x}"


def test_bar_renders_as_overline() -> None:
    assert _var("yBar") == r"\overline{y}"


def test_star_with_trailing_digit_keeps_both_subscript_and_superscript() -> None:
    # Decoration sits on the superscript axis; the trailing digit subscripts,
    # so the two never collide into a double subscript.
    assert _var("ctStar0") == r"\mathit{ct}_{0}^{*}"


def test_accent_with_trailing_digit_subscripts_outside_the_accent() -> None:
    assert _var("mHat0") == r"\hat{m}_{0}"


def test_digit_before_decoration_subscripts() -> None:
    # An indexed challenge variable (ct1Star, ss2Star) puts the index on the
    # subscript axis and the star on the superscript: ct_{1}^{*}.
    assert _var("ct1Star") == r"\mathit{ct}_{1}^{*}"
    assert _var("ss2Star") == r"\mathit{ss}_{2}^{*}"


def test_false_positive_lowercase_star_stays_literal() -> None:
    # Only the capitalized suffix form is a decoration; a lowercase trailing
    # "star" (e.g. polestar) must not become a superscript -- it stays a plain
    # multi-letter identifier (one italic unit).
    assert _var("polestar") == r"\mathit{polestar}"


def test_single_capital_stem_decorates() -> None:
    # A lone group/scalar name like Z decorates: ZStar -> Z^{*}.
    assert _var("ZStar") == r"Z^{*}"
    assert _var("XPrime") == r"X^{\prime}"


def test_capital_run_stem_decorates() -> None:
    # The greedy rule decorates any non-empty stem, including an all-caps run,
    # so ABStar -> AB^{*} (previously left literal), with the multi-letter stem
    # set as one italic unit.
    assert _var("ABStar") == r"\mathit{AB}^{*}"


def test_bare_decoration_word_stays_literal() -> None:
    # A decoration word with no stem in front is not a decoration; it renders as
    # a plain multi-letter identifier (one italic unit).
    assert _var("Star") == r"\mathit{Star}"


def test_decoration_composes_with_underscore_subscript() -> None:
    # A decoration followed by an `_`-suffix (e.g. an Initialize `_in`
    # parameter) keeps the superscript on its own axis (subscript then
    # superscript, as for `ctStar0`), not a literal "mStar" with the star
    # unrendered.
    assert _var("mStar_in") == r"m_{in}^{*}"
    assert _var("qStar_in") == r"q_{in}^{*}"


def test_accent_composes_with_underscore_subscript() -> None:
    assert _var("yBar_prev") == r"\overline{y}_{prev}"


def test_stem_subscript_and_post_decoration_subscript_combine() -> None:
    # A subscript on the stem and one after the decoration join into a single
    # comma-separated group (no stacked double subscript).
    assert _var("k1Star_pq") == r"k_{1,pq}^{*}"


def test_plain_underscore_subscript_still_works() -> None:
    # Regression: the pre-existing single-subscript paths are unchanged (the
    # multi-letter stem is now one italic unit).
    assert _var("ss_T") == r"\mathit{ss}_{T}"


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
    assert _r().render(expr) == r"{x^{*}}^{\mathit{sk}}"
