from proof_frog import frog_ast, frog_parser
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


# --- A1: single-level subscript heuristic (no double subscripts) ---


def test_multi_underscore_single_subscript_level() -> None:
    # kem_pq_nseed must not stack subscripts (a `}_{` double subscript fails
    # under pdflatex). Everything after the first underscore goes verbatim
    # (with literal underscores escaped) into one subscript group.
    out = render("kem_pq_nseed")
    assert out == r"kem_{pq\_nseed}"
    assert "}_{" not in out


def test_underscore_plus_digit_no_double_subscript() -> None:
    assert render("pk_1") == "pk_{1}"
    assert render("H_RO") == "H_{RO}"
    assert "}_{" not in render("x1_y")


def test_trailing_digit_still_subscripts() -> None:
    assert render("x1") == "x_{1}"
    assert render("ss1") == "ss_{1}"


# --- A4: exponentiation operands are braced ---


def test_chained_exponentiation_braces_each_exponent() -> None:
    out = render("a ^ b ^ c")
    # every caret is immediately followed by a brace group
    assert out.count("^") == out.count("^{")
    assert "}_{" not in out


def test_compound_base_exponentiation_is_braced() -> None:
    out = render("(a + b) ^ c")
    assert out.count("^") == out.count("^{")
    assert out.startswith("{")


# --- A5: ConcreteGame renders without an unsupported fallback ---


# --- C2: per-group generator/order macros + member overrides ---


def test_group_generator_and_order_render_as_per_group_macros() -> None:
    r = ExprRenderer(MacroRegistry())
    assert r.render(frog_parser.parse_expression("G.generator")) == r"\genG"
    assert r.render(frog_parser.parse_expression("G.order")) == r"\ordG"


def test_single_group_defaults_to_bare_g_and_q() -> None:
    macros = MacroRegistry()
    r = ExprRenderer(macros)
    r.render(frog_parser.parse_expression("G.generator"))
    r.render(frog_parser.parse_expression("G.order"))
    pre = macros.preamble()
    assert r"\providecommand{\genG}{\ensuremath{g}}" in pre
    assert r"\providecommand{\ordG}{\ensuremath{q}}" in pre


def test_multiple_groups_get_distinct_subscripted_defaults() -> None:
    macros = MacroRegistry()
    r = ExprRenderer(macros)
    assert r.render(frog_parser.parse_expression("G.generator")) == r"\genG"
    assert r.render(frog_parser.parse_expression("H.generator")) == r"\genH"
    pre = macros.preamble()
    assert r"\providecommand{\genG}{\ensuremath{g_{\mathsf{G}}}}" in pre
    assert r"\providecommand{\genH}{\ensuremath{g_{\mathsf{H}}}}" in pre


def test_member_override_takes_precedence_over_group_symbol() -> None:
    expr = frog_parser.parse_expression("G.generator")
    r = ExprRenderer(MacroRegistry(), member_overrides={("G", "generator"): "g"})
    assert r.render(expr) == "g"


def test_member_override_leaves_other_members_unchanged() -> None:
    assert render("E.length") == r"\E.length"


def test_field_member_greek_substitution() -> None:
    # `G.lambda` should Greek-ify the member: `\G.\lambda`.
    assert render("G.lambda") == r"\G.\lambda"


def test_field_member_non_greek_unchanged() -> None:
    assert render("G.stretch") == r"\G.stretch"


def test_lowercase_method_call_is_upright() -> None:
    # A member in call position is a method, so it is set upright via a macro
    # even when lowercase: `G.evaluate(s)` -> `\G.\evaluate(s)`.
    out = render("G.evaluate(s)")
    assert out == r"\G.\evaluate(s)"


def test_data_field_access_stays_italic() -> None:
    # The same member name as a (non-call) data field is NOT macroified.
    assert render("G.stretch") == r"\G.stretch"


def test_member_override_is_configurable() -> None:
    expr = frog_parser.parse_expression("H.digest")
    renderer = ExprRenderer(
        MacroRegistry(), member_overrides={("H", "digest"): r"\delta"}
    )
    assert renderer.render(expr) == r"\delta"


# --- C3: Greek-letter auto-substitution ---


def test_greek_letter_substitution() -> None:
    assert render("sigma") == r"\sigma"
    assert render("Sigma") == r"\Sigma"


def test_greek_letter_with_subscript() -> None:
    assert render("sigma1") == r"\sigma_{1}"


def test_non_greek_token_unchanged() -> None:
    assert render("sig") == "sig"
    assert render("alphabet") == "alphabet"


def test_concrete_game_renders_dotted_without_unsupported() -> None:
    game = frog_ast.ConcreteGame(
        frog_ast.ParameterizedGame("INDCPA", [frog_ast.Variable("E")]), "Left"
    )
    out = ExprRenderer(MacroRegistry()).render(game)
    assert "% unsupported" not in out
    assert "Left" in out
