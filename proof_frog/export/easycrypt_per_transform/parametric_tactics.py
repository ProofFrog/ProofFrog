"""Bucket 1b — parametric EC tactic synthesizers.

Each synthesizer takes a :class:`TransformApplication` and (optionally) a
:class:`TypeCollector` and returns the rendered EC tactic body (list of
lines), or ``None`` if synthesis fails (falls back to ``admit.``). The
synthesizer reads slot values directly from the AST diff between
``app.game_before`` and ``app.game_after``; no heuristics, no fallback
guessing. The ``TypeCollector`` argument lets a synthesizer look up the
bit-length expression of a registered abstract bitstring (via
``bs_length_for``) and register additional slice/concat ops on demand
(e.g. ``Split Uniform Samples`` needs a ``(l, l, 2l)`` concat that may
not appear elsewhere in the game body).
"""

from __future__ import annotations

import re

# ``_bs_length_arg`` duplicates the body of ``type_collector._paren_int``
# — kept in this module to avoid an extra cross-layer import for a
# three-line helper.
# pylint: disable=duplicate-code

from ... import frog_ast
from ..easycrypt.type_collector import TypeCollector
from ...transforms._base import TransformApplication


# Mirrors the mangler in exporter.py — duplicated here to avoid a
# circular import. Keep them in sync.
def _ec_ident(name: str) -> str:
    mangled = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not mangled or not mangled[0].islower():
        mangled = "v_" + mangled
    return mangled


def _ec_expr(e: frog_ast.Expression) -> str | None:
    """Render an expression to EC syntax, or return None if unsupported.

    Mirrors a subset of the exporter's renderer — kept narrow because
    a parametric synthesizer only needs to render the *offset* operand
    of a uniform-XOR transform.
    """
    if isinstance(e, frog_ast.Variable):
        return _ec_ident(e.name)
    return None


def _bitstring_suffix(t: frog_ast.Type) -> str | None:
    """Compute the EC type suffix for a BitString.

    For ``BitString<lambda>`` returns ``"lambda"``. Mirrors
    type_collector's naming convention so emitted tactics reference the
    same op symbols as the preamble.
    """
    if not isinstance(t, frog_ast.BitStringType):
        return None
    text = str(t.parameterization) if t.parameterization is not None else ""
    sanitized = re.sub(r"\W+", "_", text).strip("_")
    return sanitized or None


# pylint: disable=too-many-locals
def uniform_xor_tactic(
    app: TransformApplication, _types: TypeCollector | None = None
) -> list[str] | None:
    """Synthesize the EC tactic for ``Uniform XOR Simplification``.

    The transform rewrites a single occurrence ``u + m`` (where ``u`` is
    a single-use uniform BitString sample and ``+`` is XOR) to ``u``.
    Strategy:

    1. Walk the top-level statements of the (single) oracle method in
       both ``game_before`` and ``game_after`` in parallel.
    2. Find the first pair whose contained expression differs: the
       ``before`` side has a ``BinaryOperation(ADD, u, m)`` and the
       ``after`` side has just ``u``. The other operand ``m`` is the
       offset; the uniform sample's type gives the bitstring suffix.
    3. Emit::

           rnd (fun z => xor_<suffix> z <offset>{2})
               (fun z => xor_<suffix> z <offset>{2}).
           auto => />; progress; smt(xor_<suffix>_invol dbs_<suffix>_fu).

    Returns ``None`` if the diff doesn't match this exact pattern (e.g.
    transform fired inside a nested block, or both operands changed,
    or the type isn't BitString). The caller then falls back to
    ``admit.``.
    """
    if len(app.game_before.methods) != 1 or len(app.game_after.methods) != 1:
        return None

    before_block = app.game_before.methods[0].block
    after_block = app.game_after.methods[0].block

    if len(before_block.statements) != len(after_block.statements):
        return None

    # Find the changed pair.
    changed_pair: tuple[frog_ast.Statement, frog_ast.Statement] | None = None
    for b, a in zip(before_block.statements, after_block.statements):
        if b != a:
            if changed_pair is not None:
                return None  # ambiguous — more than one statement changed
            changed_pair = (b, a)

    if changed_pair is None:
        return None

    b_stmt, a_stmt = changed_pair
    before_expr = _expr_of(b_stmt)
    after_expr = _expr_of(a_stmt)
    if before_expr is None or after_expr is None:
        return None

    diff = _xor_dropped_operand(before_expr, after_expr)
    if diff is None:
        return None
    uniform_var, dropped_expr = diff

    # The uniform variable was sampled somewhere earlier in the block —
    # find that Sample to read its type.
    sample_type: frog_ast.Type | None = None
    for s in before_block.statements:
        if isinstance(s, frog_ast.Sample) and isinstance(s.var, frog_ast.Variable):
            if s.var.name == uniform_var:
                sample_type = s.the_type
                break
    if sample_type is None:
        return None

    suffix = _bitstring_suffix(sample_type)
    if suffix is None:
        return None

    offset_ec = _ec_expr(dropped_expr)
    if offset_ec is None:
        return None

    xor_op = f"xor_{suffix}"
    distr = f"dbs_{suffix}"
    return [
        "proc.",
        f"rnd (fun z => {xor_op} z {offset_ec}{{2}}) "
        f"(fun z => {xor_op} z {offset_ec}{{2}}).",
        f"auto => />; progress; smt({xor_op}_invol {distr}_fu).",
    ]


def inline_single_use_variables_tactic(
    app: TransformApplication,
    _types: TypeCollector | None = None,
) -> list[str] | None:
    """Synthesize the EC tactic for ``Inline Single-Use Variables``.

    The transform inlines a deterministic single-use assignment into its
    use site, so ``app.game_after`` has fewer top-level statements than
    ``app.game_before``. When the inlined assignment crosses a procedure
    call boundary, ``proc; sp; wp; sim.`` can't close the equiv because
    ``sp`` and ``wp`` don't traverse procedure calls — the head/tail
    statements they would push are blocked by the call.

    EC's body translator hoists nested module calls (e.g. a
    ``G.evaluate(...)`` inside a return expression) into fresh
    assignments before the return. The synthesized tactic walks the
    post-hoist after-game back-to-front, emitting one EC tactic per
    statement:

    * ``wp.`` to eat the return statement.
    * For each *post-hoist* module-call assignment (counted as
      top-level calls + nested calls anywhere in non-return statements
      + nested calls in the return expression): ``call (_: true). wp.``
    * For each leading sample: ``rnd.``
    * ``skip => />.`` to close.

    Returns ``None`` if the after-game shape isn't (one method, one
    sample, N module calls, deterministic exprs, single return).
    """
    if len(app.game_before.methods) != 1 or len(app.game_after.methods) != 1:
        return None
    stmts = list(app.game_after.methods[0].block.statements)
    if not stmts or not isinstance(stmts[-1], frog_ast.ReturnStatement):
        return None

    # Recognize the expected shape: an optional sample + deterministic
    # assignments + a return. Count module calls anywhere in the body.
    sample_count = 0
    call_count = 0
    for stmt in stmts:
        if isinstance(stmt, frog_ast.Sample):
            sample_count += 1
            continue
        if isinstance(stmt, frog_ast.Assignment):
            call_count += _count_module_calls(stmt.value)
            continue
        if isinstance(stmt, frog_ast.ReturnStatement):
            call_count += _count_module_calls(stmt.expression)
            continue
        # Unknown statement shape (e.g. IfStatement) — bail out.
        return None
    if sample_count > 1:
        return None
    # The back-walker emits ``call (_: true).`` at each call position;
    # EC matches the calls left↔right in lockstep. If the IsUV transform
    # reorders calls (e.g. CES inlines a tuple whose component-call order
    # differs between before/after on the post-hoist EC body), the call
    # tactics fire at mismatched positions and EC reports
    # "<E2>.method reduces to ... and <E1>.method reduces to ...".
    # Detect this by comparing the (module, method) call signatures in
    # both games; bail to the static fallback if they disagree.
    before_calls = _module_call_signature(app.game_before.methods[0])
    after_calls = _module_call_signature(app.game_after.methods[0])
    if before_calls is None or before_calls != after_calls:
        return None

    tactics: list[str] = ["proc.", "wp."]
    # Back-walk through call_count hoisted call assignments, then
    # any leading sample.
    for _ in range(call_count):
        tactics.append("call (_: true).")
        tactics.append("wp.")
    if sample_count == 1:
        tactics.append("rnd.")
    tactics.append("skip => />.")
    return tactics


# pylint: disable=too-many-locals
def merge_uniform_samples_tactic(
    app: TransformApplication, types: TypeCollector | None = None
) -> list[str] | None:
    """Synthesize the EC tactic for ``Merge Uniform Samples``.

    The transform replaces two consecutive independent uniform samples
    (``a <$ d_<l>; b <$ d_<r>``) whose only use is ``concat a b`` with a
    single uniform sample of the combined bitstring type
    (``z <$ d_<l+r>``). The synthesizer matches that exact shape on the
    method's top-level statements:

    * ``game_before``: sample of bitstring type ``<L>``, then sample of
      ``<R>``, then a ``return concat_<L>_<R>_<RES> <l_var> <r_var>;``
    * ``game_after``: a single sample of ``<RES>``, then ``return <var>;``

    The emitted tactic uses ``transitivity`` to introduce an intermediate
    that samples from ``dmap (d_<L> `*` d_<R>) concat``, then closes the
    two halves via ``rndsem*{1}`` + ``rnd`` with the slice/concat
    bijection and the per-clone distribution-split axiom (emitted by
    ``TypeCollector.emit()`` alongside the round-trip axioms).
    """
    if types is None:
        return None
    if len(app.game_before.methods) != 1 or len(app.game_after.methods) != 1:
        return None
    # Drop ``VariableDeclaration`` stmts — they are translator hoists and
    # don't affect the executable-shape match we're trying to do.
    before_stmts = [
        s
        for s in app.game_before.methods[0].block.statements
        if not isinstance(s, frog_ast.VariableDeclaration)
    ]
    after_stmts = [
        s
        for s in app.game_after.methods[0].block.statements
        if not isinstance(s, frog_ast.VariableDeclaration)
    ]
    if len(before_stmts) < 3 or len(after_stmts) < 2:
        return None
    # Walk the common prefix until divergence.
    common = 0
    while (
        common < min(len(before_stmts), len(after_stmts))
        and before_stmts[common] == after_stmts[common]
    ):
        common += 1
    # After the common prefix, expect:
    #   before tail: Sample, Sample, [ReturnStatement(concat l r)]
    #   after  tail: Sample, [ReturnStatement(merged_var)]
    # — i.e. before-tail is one longer and the last stmt of each is a
    # ReturnStatement whose expression matches the concat/var pattern.
    if len(before_stmts) - common != 3 or len(after_stmts) - common != 2:
        return None
    s_l, s_r, s_ret_before = (
        before_stmts[common],
        before_stmts[common + 1],
        before_stmts[common + 2],
    )
    s_merged, s_ret_after = after_stmts[common], after_stmts[common + 1]
    if not (
        isinstance(s_l, frog_ast.Sample)
        and isinstance(s_r, frog_ast.Sample)
        and isinstance(s_merged, frog_ast.Sample)
        and isinstance(s_ret_before, frog_ast.ReturnStatement)
        and isinstance(s_ret_after, frog_ast.ReturnStatement)
    ):
        return None
    # The before return must be ``concat l_var r_var`` (BinaryOperation
    # OR on two bitstring operands renders as concat), the after return
    # must be the merged variable. Verify by AST shape.
    if not isinstance(s_ret_after.expression, frog_ast.Variable):
        return None
    if not (
        isinstance(s_l.var, frog_ast.Variable)
        and isinstance(s_r.var, frog_ast.Variable)
        and isinstance(s_merged.var, frog_ast.Variable)
        and s_ret_after.expression.name == s_merged.var.name
    ):
        return None
    if not (
        isinstance(s_ret_before.expression, frog_ast.BinaryOperation)
        and s_ret_before.expression.operator == frog_ast.BinaryOperators.OR
        and isinstance(s_ret_before.expression.left_expression, frog_ast.Variable)
        and isinstance(s_ret_before.expression.right_expression, frog_ast.Variable)
        and s_ret_before.expression.left_expression.name == s_l.var.name
        and s_ret_before.expression.right_expression.name == s_r.var.name
    ):
        return None
    if not (
        isinstance(s_l.var, frog_ast.Variable)
        and isinstance(s_r.var, frog_ast.Variable)
        and isinstance(s_merged.var, frog_ast.Variable)
    ):
        return None
    # The tail after the merged sample should be the same on both sides
    # modulo substituting (l_var, r_var) -> (merged_var via slices). The
    # synthesizer doesn't try to verify that — the ``rnd`` + ``sim`` flow
    # below relies on the equiv post matching after the slice rewrites.
    # We only need the types here.
    bs_l = _resolve_bs_type(s_l.the_type or s_l.sampled_from)
    bs_r = _resolve_bs_type(s_r.the_type or s_r.sampled_from)
    bs_res = _resolve_bs_type(s_merged.the_type or s_merged.sampled_from)
    if bs_l is None or bs_r is None or bs_res is None:
        return None
    name_l = _bs_name_via_collector(types, bs_l)
    name_r = _bs_name_via_collector(types, bs_r)
    name_res = _bs_name_via_collector(types, bs_res)
    if name_l is None or name_r is None or name_res is None:
        return None
    len_l = types.bs_length_for(name_l)
    len_r = types.bs_length_for(name_r)
    len_res = types.bs_length_for(name_res)
    if len_l is None or len_r is None or len_res is None:
        return None
    # Ensure the concat triple is registered so the round-trip and
    # distribution-split axioms get emitted in TypeCollector.emit() (the
    # collector's emit runs after the chain renderer, so on-demand
    # registration here is honored).
    types.register_concat(name_l, name_r, name_res)
    return _merge_tactic_body(
        l_var=_ec_ident(s_l.var.name),
        r_var=_ec_ident(s_r.var.name),
        merged_var=_ec_ident(s_merged.var.name),
        name_l=name_l,
        name_r=name_r,
        name_res=name_res,
        len_l=len_l,
        len_r=len_r,
        len_res=len_res,
    )


# pylint: disable=too-many-locals
def split_uniform_samples_tactic(
    app: TransformApplication, types: TypeCollector | None = None
) -> list[str] | None:
    """Synthesize the EC tactic for ``Split Uniform Samples``.

    The transform replaces a single uniform sample of bitstring type
    ``<RES>`` (= ``<L> + <R>``) that is only used via two non-overlapping
    slices ``[0, |L|)`` and ``[|L|, |L|+|R|)`` with two independent
    uniform samples of ``<L>`` and ``<R>`` and rewrites the slice uses
    to bare variables. The synthesizer matches:

    * ``game_before``: a sample ``z <$ d_<RES>``, then any sequence of
      deterministic statements / module calls using
      ``slice_<RES>_to_<L> z 0 <|L|>`` and
      ``slice_<RES>_to_<R> z <|L|> (<|L|>+<|R|>)``.
    * ``game_after``: two samples ``a <$ d_<L>; b <$ d_<R>`` in the
      same position, with the slice uses replaced by ``a`` / ``b``.

    The emitted tactic mirrors :func:`merge_uniform_samples_tactic` but
    in reverse: introduces an intermediate that samples
    ``z <$ dmap (d_<L> `*` d_<R>) concat`` (using the new
    ``concat_<L>_<R>_<RES>`` op, auto-registered here), threads through
    the unchanged module-call tail via ``sim``, then closes the second
    transitivity branch via ``rnd`` with a slice/concat bijection.
    """
    if types is None:
        return None
    if len(app.game_before.methods) != 1 or len(app.game_after.methods) != 1:
        return None
    # Drop ``VariableDeclaration`` stmts — they are translator hoists and
    # don't affect the executable-shape match we're trying to do.
    before_stmts = [
        s
        for s in app.game_before.methods[0].block.statements
        if not isinstance(s, frog_ast.VariableDeclaration)
    ]
    after_stmts = [
        s
        for s in app.game_after.methods[0].block.statements
        if not isinstance(s, frog_ast.VariableDeclaration)
    ]
    if len(before_stmts) < 2 or len(after_stmts) < 3:
        return None
    common = 0
    while (
        common < min(len(before_stmts), len(after_stmts))
        and before_stmts[common] == after_stmts[common]
    ):
        common += 1
    if len(before_stmts) <= common or len(after_stmts) - common < 2:
        return None
    s_orig = before_stmts[common]
    s_a, s_b = after_stmts[common], after_stmts[common + 1]
    if not (
        isinstance(s_orig, frog_ast.Sample)
        and isinstance(s_a, frog_ast.Sample)
        and isinstance(s_b, frog_ast.Sample)
    ):
        return None
    if not (
        isinstance(s_orig.var, frog_ast.Variable)
        and isinstance(s_a.var, frog_ast.Variable)
        and isinstance(s_b.var, frog_ast.Variable)
    ):
        return None
    bs_res = _resolve_bs_type(s_orig.the_type or s_orig.sampled_from)
    bs_l = _resolve_bs_type(s_a.the_type or s_a.sampled_from)
    bs_r = _resolve_bs_type(s_b.the_type or s_b.sampled_from)
    if bs_l is None or bs_r is None or bs_res is None:
        return None
    name_res = _bs_name_via_collector(types, bs_res)
    name_l = _bs_name_via_collector(types, bs_l)
    name_r = _bs_name_via_collector(types, bs_r)
    if name_l is None or name_r is None or name_res is None:
        return None
    len_l = types.bs_length_for(name_l)
    len_r = types.bs_length_for(name_r)
    len_res = types.bs_length_for(name_res)
    if len_l is None or len_r is None or len_res is None:
        return None
    # Register the concat triple so the round-trip + distribution-split
    # axioms get emitted in TypeCollector.emit(). For Split the (l, r,
    # res) concat doesn't appear in the actual game bodies (only slices
    # do); without this call the axioms would be missing.
    types.register_concat(name_l, name_r, name_res)
    return _split_tactic_body(
        orig_var=_ec_ident(s_orig.var.name),
        a_var=_ec_ident(s_a.var.name),
        b_var=_ec_ident(s_b.var.name),
        name_l=name_l,
        name_r=name_r,
        name_res=name_res,
        len_l=len_l,
        len_r=len_r,
        len_res=len_res,
    )


def _resolve_bs_type(
    node: frog_ast.Type | frog_ast.Expression | None,
) -> frog_ast.BitStringType | None:
    """Return ``node`` if it's a BitStringType, else None.

    A Sample's ``the_type`` may be the declared FrogLang type
    (``BitString<lambda>``) or the sampled distribution expression
    (``BitString<lambda>`` as a type-valued expression). We only need
    the type form here.
    """
    if isinstance(node, frog_ast.BitStringType):
        return node
    return None


def _bs_name_via_collector(
    types: TypeCollector, bs: frog_ast.BitStringType
) -> str | None:
    """Compute the abstract bitstring name (e.g. ``bs_lambda``) via the
    collector's standard naming. Idempotent — calling this with the same
    type yields the same name and a no-op registration.
    """
    try:
        ec_type = types.translate_type(bs)
    except NotImplementedError:
        return None
    name = ec_type.text
    if not name.startswith("bs"):
        return None
    return name


def _bs_length_arg(s: str) -> str:
    """Parenthesize a bit-length string for use as a slice/concat
    int argument. Atomic identifiers / literals stay bare; compound
    expressions get wrapped.
    """
    if s.startswith("(") and s.endswith(")"):
        return s
    if any(op in s for op in "+-*/ "):
        return f"({s})"
    return s


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def _merge_tactic_body(
    *,
    l_var: str,
    r_var: str,
    merged_var: str,
    name_l: str,
    name_r: str,
    name_res: str,
    len_l: str,
    len_r: str,
    len_res: str,
) -> list[str]:
    """Render the EC tactic body for a ``Merge Uniform Samples`` micro
    parameterized by the (l, r, res) bitstring names + lengths + the
    variable names in the actual game bodies. The skeleton: introduce
    an intermediate ``dmap-of-dprod`` sample via ``transitivity``, then
    close LEFT~intermediate by ``rndsem*{1}`` + ``rnd`` with the slice/
    concat bijection (plus the round-trip axioms) and intermediate~RIGHT
    by the per-clone ``dbs_<RES>_split`` axiom.
    """
    # pylint: disable=duplicate-code
    concat_op = f"concat_{name_l}_{name_r}_to_{name_res}"
    slice_l = f"slice_{name_res}_to_{name_l}"
    slice_r = f"slice_{name_res}_to_{name_r}"
    distr_l = f"d{name_l}"
    distr_r = f"d{name_r}"
    distr_res = f"d{name_res}"
    len_l_p = _bs_length_arg(len_l)
    # The slice's end argument uses ``<RES>``'s bit-length (the SOURCE
    # length when slicing the merged bitstring). The expression
    # translator's sympy canonicalization renders this as ``2 * lambda``
    # not ``lambda + lambda``, so we must use the collector's canonical
    # form to match what the actual game bodies emit.
    len_sum = _bs_length_arg(len_res)
    split_axiom = f"{distr_res}_split_{name_l}_{name_r}"
    concat_id = f"concat_slices_id_{name_l}_{name_r}_{name_res}"
    slice_concat_l = f"slice_concat_left_{name_l}_{name_r}_{name_res}"
    slice_concat_r = f"slice_concat_right_{name_l}_{name_r}_{name_res}"
    _ = len_r  # captured for symmetry / future use
    return [
        "proc.",
        "transitivity {2}",
        f"  {{ {merged_var} <$ dmap ({distr_l} `*` {distr_r})",
        f"                          (fun (p : {name_l} * {name_r}) =>",
        f"                             {concat_op} p.`1 p.`2); }}",
        "  (={glob G} ==>",
        f"   ={{glob G}} /\\ {concat_op} {l_var}{{1}} {r_var}{{1}} ="
        f" {merged_var}{{2}})",
        f"  (={{glob G}} ==> ={{glob G, {merged_var}}}).",
        "- by smt().",
        "- by smt().",
        "- seq 2 1 : (={glob G} /\\",
        f"             {merged_var}{{2}} = {concat_op} {l_var}{{1}}"
        f" {r_var}{{1}}); last by auto.",
        "  rndsem*{1} 0.",
        f"  rnd (fun (p : {name_l} * {name_r}) => {concat_op} p.`1 p.`2)",
        f"      (fun (z : {name_res}) =>",
        f"         ({slice_l} z 0 {len_l_p},",
        f"          {slice_r} z {len_l_p} {len_sum})).",
        "  skip => />.",
        f"  split; first by smt({concat_id}).",
        "  move => _.",
        "  split.",
        "  + move => xR HxR.",
        "    rewrite dmap1E /(\\o) /pred1 /=.",
        f"    rewrite -(dmap_dprodE {distr_l} {distr_r}",
        f"                          (fun p : {name_l} * {name_r} => p))" " dmap_id.",
        "    apply mu_eq => p /=.",
        f"    smt({concat_id} {slice_concat_l} {slice_concat_r}).",
        "  + move => _ p Hp; split.",
        "    * smt(supp_dmap supp_dprod dprod_dlet dmap_dprodE dmap_id).",
        f"    * by smt({slice_concat_l} {slice_concat_r}).",
        f"- rnd (fun (z : {name_res}) => z) (fun (z : {name_res}) => z).",
        "  skip => />.",
        f"  smt({split_axiom}).",
    ]


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def _split_tactic_body(
    *,
    orig_var: str,
    a_var: str,
    b_var: str,
    name_l: str,
    name_r: str,
    name_res: str,
    len_l: str,
    len_r: str,
    len_res: str,
) -> list[str]:
    """Render the EC tactic body for a ``Split Uniform Samples`` micro.

    Inverse direction of :func:`_merge_tactic_body`. Structure:

    * ``seq 1 2 : INV`` peels off the sample step, leaving the
      deterministic tail (module calls + return on the original ``<RES>``
      variable) under the invariant
      ``slice <orig>{1} 0 |L| = <a>{2} /\\ slice <orig>{1} |L| (|L|+|R|)
      = <b>{2}``.
    * HEAD sub-goal: closed via ``transitivity`` through the dmap-of-
      dprod intermediate (uses the per-clone ``dbs_<RES>_split`` axiom
      for the LEFT-to-intermediate hop and ``rnd`` with the slice/concat
      bijection for the intermediate-to-RIGHT hop).
    * TAIL sub-goal: ``call (_: true); skip => /> *`` closes the
      deterministic tail because the call args match through the
      invariant and the return concat agrees.
    """
    # pylint: disable=duplicate-code
    concat_op = f"concat_{name_l}_{name_r}_to_{name_res}"
    slice_l = f"slice_{name_res}_to_{name_l}"
    slice_r = f"slice_{name_res}_to_{name_r}"
    distr_l = f"d{name_l}"
    distr_r = f"d{name_r}"
    distr_res = f"d{name_res}"
    len_l_p = _bs_length_arg(len_l)
    # See note in ``_merge_tactic_body``: the slice end uses <RES>'s
    # canonical bit length so the synthesized invariant matches the
    # body's emitted slice arguments verbatim.
    len_sum = _bs_length_arg(len_res)
    split_axiom = f"{distr_res}_split_{name_l}_{name_r}"
    concat_id = f"concat_slices_id_{name_l}_{name_r}_{name_res}"
    slice_concat_l = f"slice_concat_left_{name_l}_{name_r}_{name_res}"
    slice_concat_r = f"slice_concat_right_{name_l}_{name_r}_{name_res}"
    _ = len_r  # captured for symmetry / future use
    return [
        "proc.",
        "seq 1 2 : (={glob G} /\\",
        f"           {slice_l} {orig_var}{{1}} 0 {len_l_p} = {a_var}{{2}} /\\",
        f"           {slice_r} {orig_var}{{1}} {len_l_p} {len_sum} ="
        f" {b_var}{{2}}).",
        "- (* HEAD: sample step. *)",
        "  transitivity {1}",
        f"    {{ {orig_var} <$ dmap ({distr_l} `*` {distr_r})",
        f"                          (fun (p : {name_l} * {name_r}) =>",
        f"                             {concat_op} p.`1 p.`2); }}",
        f"    (={{glob G}} ==> ={{glob G, {orig_var}}})",
        "    (={glob G} ==>",
        "     ={glob G} /\\",
        f"     {slice_l} {orig_var}{{1}} 0 {len_l_p} = {a_var}{{2}} /\\"
        f"     {slice_r} {orig_var}{{1}} {len_l_p} {len_sum} ="
        f" {b_var}{{2}}).",
        "  + by smt().",
        "  + by smt().",
        f"  + rnd (fun (z : {name_res}) => z) (fun (z : {name_res}) => z).",
        "    skip => />.",
        f"    smt({split_axiom}).",
        "  + rndsem*{2} 0.",
        f"    rnd (fun (z : {name_res}) =>",
        f"           ({slice_l} z 0 {len_l_p},",
        f"            {slice_r} z {len_l_p} {len_sum}))",
        f"        (fun (p : {name_l} * {name_r}) =>" f" {concat_op} p.`1 p.`2).",
        "    skip => />.",
        f"    split; first by smt({slice_concat_l} {slice_concat_r}).",
        "    move => _.",
        "    split.",
        "    * move => p Hp.",
        "      rewrite dmap1E /(\\o) /pred1 /=.",
        f"      rewrite -(dmap_dprodE {distr_l} {distr_r}",
        f"                            (fun q : {name_l} * {name_r} => q))" " dmap_id.",
        "      apply mu_eq => q /=.",
        f"      smt({slice_concat_l} {slice_concat_r} {concat_id}).",
        "    * move => _ z Hz; split.",
        f"      - rewrite -(dmap_dprodE {distr_l} {distr_r}",
        f"                              (fun p : {name_l} * {name_r} => p))"
        " dmap_id.",
        "        rewrite supp_dprod /=.",
        f"        smt({distr_l}_full {distr_r}_full).",
        f"      - by smt({slice_concat_l} {slice_concat_r}).",
        "- (* TAIL: invariant supplies the slice/var equalities so the "
        "call args match  *)",
        "  (* and the return concats agree. *)",
        "  call (_: true).",
        "  skip => /> *.",
    ]


def _module_call_signature(
    method: frog_ast.Method,
) -> list[tuple[str, str]] | None:
    """Return the in-order (module-object, method-name) sequence of
    module calls in ``method``'s top-level body, including calls nested
    in expressions (which the EC hoister later lifts into their own
    assignments in left-to-right order). Returns ``None`` if any
    statement contains nested control flow this walker doesn't model.
    """
    sig: list[tuple[str, str]] = []
    for stmt in method.block.statements:
        if isinstance(stmt, frog_ast.Sample):
            _collect_call_sig(stmt.sampled_from, sig)
            continue
        if isinstance(stmt, frog_ast.Assignment):
            _collect_call_sig(stmt.value, sig)
            continue
        if isinstance(stmt, frog_ast.ReturnStatement):
            _collect_call_sig(stmt.expression, sig)
            continue
        if isinstance(stmt, frog_ast.VariableDeclaration):
            continue
        return None
    return sig


def _collect_call_sig(expr: frog_ast.Expression, out: list[tuple[str, str]]) -> None:
    if isinstance(expr, frog_ast.FuncCall):
        if isinstance(expr.func, frog_ast.FieldAccess) and isinstance(
            expr.func.the_object, frog_ast.Variable
        ):
            out.append((expr.func.the_object.name, expr.func.name))
        for a in expr.args:
            _collect_call_sig(a, out)
        return
    if isinstance(expr, frog_ast.BinaryOperation):
        _collect_call_sig(expr.left_expression, out)
        _collect_call_sig(expr.right_expression, out)
        return
    if isinstance(expr, frog_ast.UnaryOperation):
        _collect_call_sig(expr.expression, out)
        return
    if isinstance(expr, frog_ast.Slice):
        _collect_call_sig(expr.the_array, out)
        _collect_call_sig(expr.start, out)
        _collect_call_sig(expr.end, out)
        return
    if isinstance(expr, frog_ast.Tuple):
        for v in expr.values:
            _collect_call_sig(v, out)
        return
    if isinstance(expr, frog_ast.ArrayAccess):
        _collect_call_sig(expr.the_array, out)
        _collect_call_sig(expr.index, out)
        return
    if isinstance(expr, frog_ast.FieldAccess):
        _collect_call_sig(expr.the_object, out)


def _count_module_calls(expr: frog_ast.Expression) -> int:
    """Count module-method FuncCalls (``E.method(...)`` shape) in ``expr``."""
    if isinstance(expr, frog_ast.FuncCall):
        n = 0
        if isinstance(expr.func, frog_ast.FieldAccess):
            n = 1
        for a in expr.args:
            n += _count_module_calls(a)
        return n
    if isinstance(expr, frog_ast.BinaryOperation):
        return _count_module_calls(expr.left_expression) + _count_module_calls(
            expr.right_expression
        )
    if isinstance(expr, frog_ast.UnaryOperation):
        return _count_module_calls(expr.expression)
    if isinstance(expr, frog_ast.Slice):
        return (
            _count_module_calls(expr.the_array)
            + _count_module_calls(expr.start)
            + _count_module_calls(expr.end)
        )
    if isinstance(expr, frog_ast.Tuple):
        return sum(_count_module_calls(v) for v in expr.values)
    if isinstance(expr, frog_ast.ArrayAccess):
        return _count_module_calls(expr.the_array) + _count_module_calls(expr.index)
    if isinstance(expr, frog_ast.FieldAccess):
        return _count_module_calls(expr.the_object)
    return 0


def _expr_of(stmt: frog_ast.Statement) -> frog_ast.Expression | None:
    """Return the expression contained in a Return or Assignment, else None."""
    if isinstance(stmt, frog_ast.ReturnStatement):
        return stmt.expression
    if isinstance(stmt, frog_ast.Assignment):
        return stmt.value
    return None


def _xor_dropped_operand(
    before: frog_ast.Expression, after: frog_ast.Expression
) -> tuple[str, frog_ast.Expression] | None:
    """Return ``(uniform_var_name, dropped_operand_expr)`` if ``before`` is
    ``BinaryOperation(ADD, u, m)`` (in either order) and ``after`` is just
    ``u``. Else ``None``."""
    if not isinstance(after, frog_ast.Variable):
        return None
    if not isinstance(before, frog_ast.BinaryOperation):
        return None
    if before.operator != frog_ast.BinaryOperators.ADD:
        return None
    if (
        isinstance(before.left_expression, frog_ast.Variable)
        and before.left_expression.name == after.name
    ):
        return (after.name, before.right_expression)
    if (
        isinstance(before.right_expression, frog_ast.Variable)
        and before.right_expression.name == after.name
    ):
        return (after.name, before.left_expression)
    return None
