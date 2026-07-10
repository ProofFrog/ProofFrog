from proof_frog.export.latex import ir
from proof_frog.export.latex.backends.cryptocode import CryptocodeBackend


def test_render_simple_procedure() -> None:
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(
        title=r"\Enc(k, m)",
        lines=[
            ir.Sample(lhs="r", rhs=r"\{0,1\}^\lambda"),
            ir.Assign(lhs="c", rhs=r"\PRF(k, r) \oplus m"),
            ir.Return(expr="(r, c)"),
        ],
    )
    out = b.render_procedure(p)
    assert r"\procedure" in out
    assert r"\Enc(k, m)" in out
    assert r"r \getsr \{0,1\}^\lambda" in out
    assert r"c \gets \PRF(k, r) \oplus m" in out
    assert r"\pcreturn (r, c)" in out


def test_render_empty_procedure_no_blank_body() -> None:
    # A procedure with no rendered lines must emit an empty body "{}", not a
    # whitespace-only "{\n    \n}".  The blank line is a LaTeX \par which breaks
    # cryptocode's \procedure ("Paragraph ended before \@pseudocode was
    # complete").
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(title=r"\Foo()", lines=[])
    out = b.render_procedure(p)
    assert "{\n    \n}" not in out
    assert out.endswith("{}")


def test_render_vstack_boxed() -> None:
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(title=r"\KeyGen()", lines=[ir.Return(expr="k")])
    out = b.render_vstack(ir.VStack(blocks=[p], boxed=True))
    assert r"\begin{pcvstack}[boxed," in out
    assert r"\end{pcvstack}" in out


def test_render_vstack_with_heading() -> None:
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(title=r"\KeyGen()", lines=[ir.Return(expr="k")])
    out = b.render_vstack(ir.VStack(blocks=[p], boxed=True, heading="$T$"))
    # title sits ABOVE the boxed inner stack: an outer pcvstack wraps the
    # heading then the boxed inner pcvstack (two pcvstack envs total).
    assert out.count(r"\begin{pcvstack}") == 2
    assert out.index("$T$") < out.index(r"\begin{pcvstack}[boxed,")
    assert out.index("$T$") < out.index(r"\procedure")


def test_render_hstack_lays_columns_side_by_side() -> None:
    b = CryptocodeBackend()
    left = ir.VStack(blocks=[ir.ProcedureBlock(title=r"\L()", lines=[])])
    right = ir.VStack(blocks=[ir.ProcedureBlock(title=r"\R()", lines=[])])
    out = b.render_hstack(ir.HStack(stacks=[left, right]))
    assert r"\begin{pchstack}" in out
    assert r"\end{pchstack}" in out
    assert r"\pchspace" in out
    assert out.count(r"\begin{pcvstack}") == 2


def test_procedure_indents_lines_by_depth() -> None:
    # A guarded body (depth 1) is prefixed with one \pcind so it reads as
    # nested under its If/For marker; the marker and sibling lines (depth 0)
    # are not (A3).
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(
        title=r"\Decaps(dk, c)",
        lines=[
            ir.If(cond="c = ctStar", depth=0),
            ir.Return(expr=r"\bot", depth=1),
            ir.EndIf(depth=0),
            ir.Return(expr=r"K.Decaps(dk, c)", depth=0),
        ],
    )
    out = b.render_procedure(p)
    assert r"\pcind \pcreturn \bot" in out
    # The unconditional return and the \pcif must NOT carry a \pcind.
    assert r"\pcind \pcif" not in out
    assert r"\pcind \pcreturn K.Decaps" not in out


def test_procedure_indents_nested_depth_twice() -> None:
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(
        title=r"\Foo()",
        lines=[ir.Return(expr="x", depth=2)],
    )
    out = b.render_procedure(p)
    assert r"\pcind\pcind \pcreturn x" in out


def test_required_packages() -> None:
    b = CryptocodeBackend()
    pkgs = b.required_packages()
    names = {p.name for p in pkgs}
    assert "cryptocode" in names


def test_required_packages_includes_adjustbox() -> None:
    # adjustbox supplies \adjustbox{max width=...} used by fit_width (A1).
    b = CryptocodeBackend()
    names = {p.name for p in b.required_packages()}
    assert "adjustbox" in names


def test_required_packages_includes_stmaryrd() -> None:
    # stmaryrd supplies \llbracket / \rrbracket for Iverson-bracketed returns.
    b = CryptocodeBackend()
    names = {p.name for p in b.required_packages()}
    assert "stmaryrd" in names


def test_fit_width_wraps_in_max_width_adjustbox() -> None:
    b = CryptocodeBackend()
    out = b.fit_width("CONTENT")
    # adjustbox shrinks over-wide content; the varwidth wrapper is required so
    # cryptocode's vertical-mode stacks survive adjustbox's LR box and so the
    # natural content width drives the scaling.
    assert out.startswith(r"\adjustbox{max width=\textwidth}{")
    assert r"\begin{varwidth}{4\textwidth}CONTENT\end{varwidth}" in out


def test_figure_body_is_wrapped_to_fit_width() -> None:
    # A wide procedure body must shrink to the text width rather than run off
    # the page (A1). The figure body is wrapped in an adjustbox max-width box.
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(title=r"\Enc(k, m)", lines=[ir.Return(expr="c")])
    out = b.render_figure(ir.Figure(body=p, caption="Game"))
    assert r"\adjustbox{max width=\textwidth}{" in out
    # The procedure itself sits inside the adjustbox, before the caption.
    assert out.index(r"\adjustbox") < out.index(r"\procedure")
    assert out.index(r"\procedure") < out.index(r"\caption")


def test_preamble_extras_defines_getsr() -> None:
    # \getsr is emitted in the body for sampling, but is not a built-in
    # cryptocode command (cryptocode 3.x uses \sample).  The preamble must
    # define \getsr as a providecommand alias so generated documents compile
    # with pdflatex without "Undefined control sequence" errors.
    b = CryptocodeBackend()
    extras = b.preamble_extras()
    assert r"\providecommand{\getsr}{\sample}" in extras


def test_no_dead_experiment_macro() -> None:
    # Games are now titled by notion + side captions, so the old
    # Exp^{notion.side} \Experiment macro is no longer emitted or defined.
    extras = CryptocodeBackend().preamble_extras()
    assert r"\Experiment" not in extras


def test_endif_emits_no_fi() -> None:
    # The closing `fi` marker is dropped: A3 indentation already shows the
    # guarded body's scope, and papers do not number a `fi` line.
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(
        title=r"\Foo()",
        lines=[
            ir.If(cond="x = 1", depth=0),
            ir.Return(expr="x", depth=1),
            ir.EndIf(depth=0),
            ir.Return(expr="y", depth=0),
        ],
    )
    out = b.render_procedure(p)
    assert r"\pcfi" not in out
    assert r"\pcif x = 1 \pcthen" in out
    # Three content lines remain (If, two returns); the dropped EndIf takes no
    # numbered line, so there are exactly two `\\` separators.
    assert out.count(r"\\") == 2


def test_highlighted_line_boxed_with_pfhighlight() -> None:
    # Default diff style "box" wraps a changed line's content in the soft
    # \pfhighlight tint (D1) -- lighter than cryptocode's \gamechange. The
    # \pcind indent stays outside the box.
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(
        title=r"\Enc(m)",
        lines=[
            ir.Assign(lhs="c", rhs=r"\ENC(k, m)", highlight=True),
            ir.Return(expr="c"),
        ],
    )
    out = b.render_procedure(p)
    # \pfhighlight re-enters math mode itself, so its argument is the raw line.
    assert r"\pfhighlight{c \gets \ENC(k, m)}" in out
    # the unchanged return line is not boxed
    assert r"\pfhighlight{\pcreturn c}" not in out
    # the old heavy \gamechange box is no longer emitted
    assert r"\gamechange" not in out


def test_highlighted_line_indent_outside_box() -> None:
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(
        title=r"\O()",
        lines=[ir.Return(expr=r"\bot", depth=1, highlight=True)],
    )
    out = b.render_procedure(p)
    assert r"\pcind \pfhighlight{\pcreturn \bot}" in out


def test_highlighted_line_color_style() -> None:
    # The "color" diff style wraps the content in a color group instead of a
    # box; selectable by the user.
    b = CryptocodeBackend(diff_style="color")
    p = ir.ProcedureBlock(
        title=r"\Enc(m)",
        lines=[ir.Assign(lhs="c", rhs=r"\ENC(k, m)", highlight=True)],
    )
    out = b.render_procedure(p)
    assert r"{\color{blue} c \gets \ENC(k, m)}" in out
    assert r"\gamechange" not in out


def test_default_diff_style_is_box() -> None:
    assert CryptocodeBackend().diff_style == "box"


def test_preamble_defines_soft_pfhighlight() -> None:
    # The soft change-highlight command is a light gray tint (black!8), far
    # lighter than cryptocode's default \gamechange box.
    extras = CryptocodeBackend().preamble_extras()
    assert r"\providecommand{\pfhighlight}[1]{\colorbox{black!8}{$#1$}}" in extras
    # The \todo placeholder macro is gone (no TODO markers in output).
    assert r"\todo" not in extras


def test_render_game_step_is_non_floating() -> None:
    # A proof-sequence game renders as a centered, non-floating block -- no
    # figure float, caption, or label -- so it stays in reading order.
    b = CryptocodeBackend()
    body = ir.VStack(blocks=[ir.ProcedureBlock(title=r"\O()", lines=[ir.Return("k")])])
    out = b.render_game_step(r"$G_1 = \DDH(\G).\Left$", body)
    assert out.startswith(r"\begin{center}")
    assert out.strip().endswith(r"\end{center}")
    assert r"$G_1 = \DDH(\G).\Left$" in out
    assert r"\begin{figure}" not in out
    assert r"\caption" not in out
    assert r"\procedure" in out


def test_render_game_step_heading_only() -> None:
    # A start/end/dedup step has no body: just the heading, still non-floating.
    b = CryptocodeBackend()
    out = b.render_game_step(r"$G_0 = \DDH(\G).\Left$", None)
    assert r"\begin{center}" in out
    assert r"\procedure" not in out
    assert r"\smallskip" not in out


def test_vstack_adds_vertical_space_between_procedures() -> None:
    # A little breathing room between stacked oracles, via pcvstack's space=
    # key. (\pclb takes no argument -- a \pclb[..] would leak literal text.)
    b = CryptocodeBackend()
    v = ir.VStack(
        blocks=[
            ir.ProcedureBlock(title=r"\Oa()", lines=[ir.Return(expr="1")]),
            ir.ProcedureBlock(title=r"\Ob()", lines=[ir.Return(expr="2")]),
        ],
        boxed=True,
    )
    out = b.render_vstack(v)
    assert r"\begin{pcvstack}[boxed,space=\smallskipamount]" in out
    assert r"\pclb[" not in out
