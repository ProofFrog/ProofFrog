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
from .type_collector import TypeCollector
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


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def uniform_xor_tactic(
    app: TransformApplication,
    _types: TypeCollector | None = None,
    **_kwargs: object,  # accept the unified caller's extra kwargs
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

    # The back-walk count (wp/call/rnd after the bijection site) must
    # match what EC actually sees, which is the *hoisted* form: nested
    # module-call expressions become standalone ``<@`` assignments. If
    # the caller supplied the normalization context, hoist first.
    # pylint: disable=import-outside-toplevel
    import copy as _copy

    from .canonical_form import _normalize_for_ec as _norm_ec

    _ext = _kwargs.get("external_module_types")
    _mrt = _kwargs.get("method_return_types")
    if isinstance(_ext, dict) and isinstance(_mrt, dict):
        before_block = (
            _norm_ec(_copy.deepcopy(app.game_before), _ext, _mrt).methods[0].block
        )
        after_block = (
            _norm_ec(_copy.deepcopy(app.game_after), _ext, _mrt).methods[0].block
        )
    else:
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
    # Back-walk the after-block from the end: each statement past the
    # uniform sample needs a tactic to discharge before ``rnd`` can fire
    # at the bijection site. ``wp`` covers the return; ``call (_: true)``
    # covers each module-call assignment; ``rnd.`` (no bijection)
    # covers any non-targeted sample. Statements *before* the uniform
    # sample close via ``auto``.
    stmts_after = list(after_block.statements)
    uniform_idx: int | None = None
    for i, s in enumerate(stmts_after):
        if (
            isinstance(s, frog_ast.Sample)
            and isinstance(s.var, frog_ast.Variable)
            and s.var.name == uniform_var
        ):
            uniform_idx = i
            break
    if uniform_idx is None:
        return None
    tail_tactics: list[str] = []
    for s in stmts_after[uniform_idx + 1 :]:
        if isinstance(s, frog_ast.ReturnStatement):
            tail_tactics.append("wp.")
        elif isinstance(s, frog_ast.Assignment) and isinstance(
            s.value, frog_ast.FuncCall
        ):
            tail_tactics.append("call (_: true).")
        elif isinstance(s, frog_ast.Sample):
            tail_tactics.append("rnd.")
        elif isinstance(s, frog_ast.Assignment):
            tail_tactics.append("wp.")
        else:
            return None
    # The bijection at the uniform-var sample; back-walking runs these
    # in reverse order so the tail tactics come first.
    tactic = ["proc.", *reversed(tail_tactics)]
    tactic.append(
        f"rnd (fun z => {xor_op} z {offset_ec}{{2}}) "
        f"(fun z => {xor_op} z {offset_ec}{{2}})."
    )
    tactic.append(f"auto => />; progress; smt({xor_op}_invol {distr}_fu).")
    return tactic


def inline_single_use_variables_tactic(
    app: TransformApplication,
    _types: TypeCollector | None = None,
    **_kwargs: object,  # accept and ignore optional context kwargs
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
    # The back-walker only works when the body's shape is
    # ``(samples)*; (calls)*; (deterministic-assignment-or-something)*;
    # return`` and EXACTLY mirrors that shape on both sides. The walker
    # produces ``wp; (call; wp)*; (rnd)*; skip`` which assumes all
    # samples precede all calls; bail when the order is interleaved.
    if not _shape_is_samples_then_calls(app.game_before.methods[0]):
        return None
    if not _shape_is_samples_then_calls(app.game_after.methods[0]):
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
    # the leading samples.
    for _ in range(call_count):
        tactics.append("call (_: true).")
        tactics.append("wp.")
    for _ in range(sample_count):
        tactics.append("rnd.")
    tactics.append("skip => />.")
    return tactics


def _shape_is_samples_then_calls(method: frog_ast.Method) -> bool:
    """True if the post-hoist body is ``(sample)*; (call|assign)*; return``.

    Walks the hoisted method body. Once a non-sample statement is seen,
    no further sample may appear. This is the canonical shape the
    ``inline_single_use_variables_tactic`` back-walker is built for; mixed
    interleavings (``sample; call; sample; call``) defeat its ``rnd; rnd``
    bulk emission since each pair would need to be back-walked through
    its own call.
    """
    saw_non_sample = False
    for stmt in method.block.statements:
        if isinstance(stmt, frog_ast.Sample):
            if saw_non_sample:
                return False
        elif isinstance(stmt, (frog_ast.Assignment, frog_ast.ReturnStatement)):
            saw_non_sample = True
        else:
            return False
    return True


def _sympy_normalize_int_arith(game: frog_ast.Game) -> None:
    """Replace int arithmetic sub-expressions with sympy-canonical forms.

    Walks every ``BitStringType`` parameterization and ``Slice``
    start/end on the game in place, replacing pure integer arithmetic
    (``BinaryOperation`` over ``Variable`` / ``Integer`` / ``BinaryOperation``)
    with the result of parsing the sympy-canonical string back into an
    AST. This matches the canonicalization that ``TypeCollector.
    _bitstring_name`` and ``expr_translator._canonical_int_str`` apply
    when generating EC source, so AST-level equality after this pass
    matches EC-level equality for these positions.
    """
    # pylint: disable=import-outside-toplevel
    from .type_collector import _canonical_arith_str

    def canon(expr: frog_ast.Expression) -> frog_ast.Expression:
        # Parse the sympy-canonical string back into a tiny AST. We
        # only need to handle ``a + b``, ``a * b``, ``a - b`` over
        # ``Variable`` / ``Integer`` — which is the shape sympy emits
        # for the parameterizations we see in practice.
        canonical = _canonical_arith_str(expr)
        return _parse_simple_arith(canonical) or expr

    def walk_expr(expr: frog_ast.Expression) -> None:
        if isinstance(expr, frog_ast.Slice):
            expr.start = canon(expr.start)
            expr.end = canon(expr.end)
            walk_expr(expr.the_array)
            return
        if isinstance(expr, frog_ast.BinaryOperation):
            walk_expr(expr.left_expression)
            walk_expr(expr.right_expression)
            return
        if isinstance(expr, frog_ast.FuncCall):
            for a in expr.args:
                walk_expr(a)

    def walk_type(t: frog_ast.Type | None) -> None:
        if t is None:
            return
        if isinstance(t, frog_ast.BitStringType) and t.parameterization is not None:
            t.parameterization = canon(t.parameterization)

    def walk_stmt(s: frog_ast.Statement) -> None:
        if isinstance(s, frog_ast.VariableDeclaration):
            walk_type(s.type)
            return
        if isinstance(s, (frog_ast.Sample, frog_ast.Assignment)):
            walk_type(s.the_type)
            if isinstance(s, frog_ast.Assignment):
                walk_expr(s.value)
            elif isinstance(s, frog_ast.Sample) and isinstance(
                s.sampled_from, frog_ast.Type
            ):
                walk_type(s.sampled_from)
            return
        if isinstance(s, frog_ast.ReturnStatement):
            walk_expr(s.expression)

    for method in game.methods:
        for stmt in method.block.statements:
            walk_stmt(stmt)


def _parse_simple_arith(s: str) -> frog_ast.Expression | None:
    """Parse a sympy-canonical arithmetic string into a tiny AST.

    Handles ``Variable`` (identifier, possibly a Python keyword like
    ``lambda``), ``Integer``, and ``+``/``*``/``-`` over them. Returns
    ``None`` for shapes outside that grammar.

    We can't use Python's ``ast`` module directly because the
    identifiers we see (``lambda``) clash with Python keywords; instead
    we run a tiny precedence-climbing parser over a hand-rolled
    tokenizer.
    """
    tokens = _tokenize_arith(s)
    if tokens is None:
        return None
    pos = [0]

    def parse_atom() -> frog_ast.Expression | None:
        if pos[0] >= len(tokens):
            return None
        tok = tokens[pos[0]]
        if tok == "(":
            pos[0] += 1
            expr = parse_addsub()
            if pos[0] >= len(tokens) or tokens[pos[0]] != ")":
                return None
            pos[0] += 1
            return expr
        if tok == "-":
            pos[0] += 1
            inner = parse_atom()
            if inner is None:
                return None
            return frog_ast.UnaryOperation(frog_ast.UnaryOperators.MINUS, inner)
        if tok.isdigit():
            pos[0] += 1
            return frog_ast.Integer(int(tok))
        if tok.replace("_", "").isalnum() and not tok[0].isdigit():
            pos[0] += 1
            return frog_ast.Variable(tok)
        return None

    def parse_mul() -> frog_ast.Expression | None:
        left = parse_atom()
        if left is None:
            return None
        while pos[0] < len(tokens) and tokens[pos[0]] in ("*", "/"):
            op_tok = tokens[pos[0]]
            pos[0] += 1
            right = parse_atom()
            if right is None:
                return None
            op = (
                frog_ast.BinaryOperators.MULTIPLY
                if op_tok == "*"
                else frog_ast.BinaryOperators.DIVIDE
            )
            left = frog_ast.BinaryOperation(op, left, right)
        return left

    def parse_addsub() -> frog_ast.Expression | None:
        left = parse_mul()
        if left is None:
            return None
        while pos[0] < len(tokens) and tokens[pos[0]] in ("+", "-"):
            op_tok = tokens[pos[0]]
            pos[0] += 1
            right = parse_mul()
            if right is None:
                return None
            op = (
                frog_ast.BinaryOperators.ADD
                if op_tok == "+"
                else frog_ast.BinaryOperators.SUBTRACT
            )
            left = frog_ast.BinaryOperation(op, left, right)
        return left

    result = parse_addsub()
    if pos[0] != len(tokens):
        return None
    return result


def _tokenize_arith(s: str) -> list[str] | None:
    tokens: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c in "+-*/()":
            tokens.append(c)
            i += 1
            continue
        if c.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            tokens.append(s[i:j])
            i = j
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < len(s) and (s[j].isalnum() or s[j] == "_"):
                j += 1
            tokens.append(s[i:j])
            i = j
            continue
        return None
    return tokens


def _xor_arg_swaps_only(
    before: frog_ast.Expression,
    after: frog_ast.Expression,
    swaps: list[frog_ast.Type],
) -> bool:
    """Return True if ``after`` equals ``before`` modulo swapped XOR args.

    Records each swap site's operand type into ``swaps`` so the caller
    can emit ``xor_<suffix>_commut`` axioms for the relevant types. The
    operand type is reconstructed from ``before.left_expression`` via
    :func:`_expr_bs_type` (a best-effort inference that handles bare
    Variable + Slice cases — sufficient for the canonical-chain shapes
    we currently see).
    """
    if isinstance(before, frog_ast.BinaryOperation) and isinstance(
        after, frog_ast.BinaryOperation
    ):
        if before.operator != after.operator:
            return False
        # ADD on BitString is XOR (commutative).
        is_xor_add = before.operator == frog_ast.BinaryOperators.ADD
        if (
            is_xor_add
            and before.left_expression == after.right_expression
            and before.right_expression == after.left_expression
        ):
            inferred = _expr_bs_type(before.left_expression)
            if inferred is None:
                return False
            swaps.append(inferred)
            return True
        return _xor_arg_swaps_only(
            before.left_expression, after.left_expression, swaps
        ) and _xor_arg_swaps_only(
            before.right_expression, after.right_expression, swaps
        )
    if isinstance(before, frog_ast.FuncCall) and isinstance(after, frog_ast.FuncCall):
        if before.func != after.func or len(before.args) != len(after.args):
            return False
        return all(
            _xor_arg_swaps_only(b, a, swaps) for b, a in zip(before.args, after.args)
        )
    return before == after


def _expr_bs_type(e: frog_ast.Expression) -> frog_ast.Type | None:
    """Best-effort inference of an expression's BitString type.

    Handles the cases that appear in the chain-emitter's micros:
    ``Slice`` (length = ``end - start``) and ``Variable`` (looked up
    later via the surrounding sample). Returns ``None`` otherwise. The
    caller treats ``None`` as "can't synthesize this swap" and bails.
    """
    if isinstance(e, frog_ast.Slice):
        return frog_ast.BitStringType(
            frog_ast.BinaryOperation(frog_ast.BinaryOperators.SUBTRACT, e.end, e.start)
        )
    # Bare Variable: its type is fixed by the sample/assignment that
    # binds it; we'd need the surrounding type map to resolve. For the
    # shapes that surface today, at least one operand of every XOR swap
    # we see is a Slice — so returning None here is acceptable.
    return None


def normalize_commutative_chains_tactic(  # pylint: disable=too-many-branches,too-many-locals
    app: TransformApplication,
    types: TypeCollector | None = None,
    **kwargs: object,
) -> list[str] | None:
    """Synthesize an EC tactic for ``Normalize Commutative Chains`` when
    the diff is a pure XOR-argument swap.

    The canned ``proc; sim.`` fallback can't close micros where the
    engine reorders XOR arguments (``xor a b`` → ``xor b a``) because
    ``sim`` doesn't see the commutativity. This synthesizer detects
    return-statement diffs that consist *only* of XOR arg swaps, walks
    the method's local-variable bindings to enumerate the locals,
    extracts module-typed externals from the method's body (anything
    appearing as the receiver of a ``<@`` call), and emits::

        proc.
        conseq (_: _ ==> ={glob <M1>, glob <M2>, <L1>, <L2>, ...});
            first by progress; smt(xor_<suffix1>_commut ...).
        sim.

    Returns ``None`` when the diff isn't a clean XOR-swap, no
    bitstring suffix can be inferred, or the method shape doesn't
    fit the conseq-then-sim pattern.
    """
    if len(app.game_before.methods) != 1 or len(app.game_after.methods) != 1:
        return None
    # Normalize through the EC pipeline first: sympy-canonicalize int
    # arithmetic (so ``2 * lambda`` vs ``lambda * 2`` no longer counts
    # as a diff) and hoist nested module calls (matching what EC sees).
    # Falls back to raw-AST comparison when normalization context isn't
    # available (older test fixtures that call the synthesizer directly).
    # pylint: disable=import-outside-toplevel
    import copy

    from .canonical_form import _normalize_for_ec

    ext_types = kwargs.get("external_module_types")
    method_rets = kwargs.get("method_return_types")
    if isinstance(ext_types, dict) and isinstance(method_rets, dict):
        before_game = _normalize_for_ec(
            copy.deepcopy(app.game_before), ext_types, method_rets
        )
        after_game = _normalize_for_ec(
            copy.deepcopy(app.game_after), ext_types, method_rets
        )
    else:
        before_game = app.game_before
        after_game = app.game_after
    # sympy-canonicalize int sub-expressions on both sides so e.g.
    # ``2 * lambda`` and ``lambda * 2`` (which EC's TypeCollector
    # collapses to the same ``bs_2_lambda``) compare equal at the AST
    # level. Without this, statement-level diff detection sees an
    # apparent change in every type annotation and slice index that
    # the engine's commutative-chain rewriter touched, even though
    # those positions disappear in the EC output.
    _sympy_normalize_int_arith(before_game)
    _sympy_normalize_int_arith(after_game)
    before_method = before_game.methods[0]
    after_method = after_game.methods[0]
    before_stmts = list(before_method.block.statements)
    after_stmts = list(after_method.block.statements)
    if len(before_stmts) != len(after_stmts):
        return None
    swap_types: list[frog_ast.Type] = []
    found_diff = False
    for b, a in zip(before_stmts, after_stmts):
        if b == a:
            continue
        if found_diff:
            return None
        if not (
            isinstance(b, frog_ast.ReturnStatement)
            and isinstance(a, frog_ast.ReturnStatement)
        ):
            return None
        if not _xor_arg_swaps_only(b.expression, a.expression, swap_types):
            return None
        found_diff = True
    if not found_diff or not swap_types:
        return None

    # Enumerate locals: every variable bound by a Sample / Assignment /
    # VariableDeclaration in the method body.
    locals_: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        if name not in seen:
            seen.add(name)
            locals_.append(name)

    for stmt in before_stmts:
        if isinstance(stmt, frog_ast.VariableDeclaration):
            _add(stmt.name)
        elif isinstance(stmt, (frog_ast.Sample, frog_ast.Assignment)):
            if isinstance(stmt.var, frog_ast.Variable):
                _add(stmt.var.name)

    # Externals: receivers of ``<@`` calls. We walk Assignment.value
    # for ``FuncCall(FieldAccess(Variable(M), ...), ...)`` and collect
    # ``M``. These become ``glob M`` in the conseq.
    externals: list[str] = []
    seen_ext: set[str] = set()
    for stmt in before_stmts:
        if isinstance(stmt, frog_ast.Assignment) and isinstance(
            stmt.value, frog_ast.FuncCall
        ):
            func = stmt.value.func
            if isinstance(func, frog_ast.FieldAccess) and isinstance(
                func.the_object, frog_ast.Variable
            ):
                name = func.the_object.name
                if name not in seen_ext:
                    seen_ext.add(name)
                    externals.append(name)

    # Emit ``={glob M1, ..., L1, L2, ...}`` for the conseq postcondition.
    eq_terms = [f"glob {m}" for m in externals] + locals_
    if not eq_terms:
        return None
    eq_str = "={" + ", ".join(eq_terms) + "}"

    # Collect xor_<suffix>_commut axioms for each swap site. The EC
    # type name comes from the TypeCollector (matches how
    # ``type_collector.emit()`` derives axiom names), not from a
    # syntactic suffix of the parameterization expression — sympy
    # canonicalization may reduce ``lambda - 0`` to ``lambda``.
    if types is None:
        return None
    axiom_names: list[str] = []
    for t in swap_types:
        ec_type = types.translate_type(t)
        bs_name = ec_type.text
        if not bs_name.startswith("bs_") and bs_name != "bs":
            return None
        suffix = bs_name.removeprefix("bs_") if bs_name != "bs" else ""
        ax = f"xor_{suffix}_commut" if suffix else "xor_commut"
        if ax not in axiom_names:
            axiom_names.append(ax)

    return [
        "proc.",
        f"conseq (_: _ ==> {eq_str}); first by progress; "
        f"smt({' '.join(axiom_names)}).",
        "sim.",
    ]


# pylint: disable=too-many-locals
def merge_uniform_samples_tactic(
    app: TransformApplication,
    types: TypeCollector | None = None,
    **_kwargs: object,  # accept and ignore optional context kwargs
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
    # Partial-merge soundness gate: ``|L| + |R| != |RES|`` would emit an
    # unsound ``concat_<L>_<R>_<RES>`` distribution-split axiom (the
    # image of concat has 2^(|L|+|R|) elements, |RES| has 2^|RES|).
    # In practice merges from the engine are always full (the engine
    # only merges when the lengths sum to the merged type), but guard
    # defensively so a future shape can't introduce false axioms.
    if not _lengths_sum_equal(len_l, len_r, len_res):
        return _partial_split_admit("Merge Uniform Samples", name_l, name_r, name_res)
    # Ensure the concat triple is registered so the round-trip and
    # distribution-split axioms get emitted in TypeCollector.emit() (the
    # collector's emit runs after the chain renderer, so on-demand
    # registration here is honored).
    types.register_concat(name_l, name_r, name_res)
    eq_args_strong = _kwargs.get("eq_args_strong")
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
        eq_args_strong=(eq_args_strong if isinstance(eq_args_strong, str) else ""),
    )


# pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-arguments,too-many-positional-arguments
def split_uniform_samples_tactic(
    app: TransformApplication,
    types: TypeCollector | None = None,
    *,
    helpers: list[str] | None = None,
    name_prefix: str = "",
    module_param_sig: str = "",
    module_param_args: str = "",
    left_module_ref: str = "",
    right_module_ref: str = "",
    eq_args_strong: str = "",
    eq_post_strong: str = "",
    **_extra_kwargs: object,  # accept the unified caller's extra kwargs
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
    # Partial-split case: ``|L| + |R| < |RES|``. Introduce an augmented
    # intermediate that adds a dummy ``gap`` sample on the RIGHT and a
    # ``Mid`` that mediates the bijection via concat3. The straight 2-way
    # bijection would emit an unsound ``concat`` axiom (image
    # cardinality ``2^(|L|+|R|)`` vs ``2^|RES|``); the 3-way decomposition
    # is sound because ``|L|+|R|+|GAP| = |RES|``.
    if not _lengths_sum_equal(len_l, len_r, len_res):
        # The partial-split helpers support two source-layout shapes for
        # the augmented intermediate: ``tail-gap`` (slices at ``[0..|L|]``
        # and ``[|L|..|L|+|R|]``; unused window is the tail) and
        # ``mid-gap`` (slices at ``[0..|L|]`` and
        # ``[|RES|-|R|..|RES|]``; unused window is between L and R).
        # Walk only the statements *after* ``s_orig`` so the sample's
        # own declaration doesn't count as a bare use. Any other layout
        # (head-gap, interleaved, or non-slice use) falls back to
        # ``_partial_split_admit``.
        layout = _classify_partial_split_layout(
            before_stmts[common + 1 :],
            s_orig.var.name,
            len_l,
            len_r,
            len_res,
        )
        if layout is None:
            return _partial_split_admit(
                "Split Uniform Samples", name_l, name_r, name_res
            )
        # The simple Mid/Aug bodies emit a 2-way return concat
        # ``concat_<L>_<R>_to_<ret_type>`` and assume the procedure's
        # return is ``concat (slice_L) (slice_R)``. If the before-game
        # wraps each slice in a module call (e.g.
        # ``return G.evaluate(slice_L) || G.evaluate(slice_R)``), the
        # procedure return is ``concat (call_out_L) (call_out_R)``
        # instead. Detect that specific shape and route to the
        # module-call-tail variant. Otherwise, if the tail contains any
        # module calls we don't recognize, bail to a structured admit.
        modcall_info = _detect_module_call_tail_pattern(
            before_stmts[common + 1 :],
            s_orig.var.name,
        )
        if modcall_info is not None:
            modcall = _partial_split_helpers_modcall(
                types=types,
                len_l=len_l,
                len_r=len_r,
                len_res=len_res,
                name_l=name_l,
                name_r=name_r,
                name_res=name_res,
                ret_type=_return_bs_name(app, types),
                orig_var=_ec_ident(s_orig.var.name),
                a_var=_ec_ident(s_a.var.name),
                b_var=_ec_ident(s_b.var.name),
                helpers=helpers,
                name_prefix=name_prefix,
                module_param_sig=module_param_sig,
                module_param_args=module_param_args,
                left_module_ref=left_module_ref,
                right_module_ref=right_module_ref,
                eq_args_strong=eq_args_strong,
                eq_post_strong=eq_post_strong,
                layout=layout,
                module_name=modcall_info["module"],
                method_name=modcall_info["method"],
            )
            if modcall is not None:
                return modcall
            return _partial_split_admit(
                "Split Uniform Samples", name_l, name_r, name_res
            )
        if _has_module_call_tail(
            before_stmts[common + 1 :],
            s_orig.var.name,
        ):
            return _partial_split_admit(
                "Split Uniform Samples", name_l, name_r, name_res
            )
        partial = _partial_split_helpers(
            types=types,
            len_l=len_l,
            len_r=len_r,
            len_res=len_res,
            name_l=name_l,
            name_r=name_r,
            name_res=name_res,
            ret_type=_return_bs_name(app, types),
            orig_var=_ec_ident(s_orig.var.name),
            a_var=_ec_ident(s_a.var.name),
            b_var=_ec_ident(s_b.var.name),
            helpers=helpers,
            name_prefix=name_prefix,
            module_param_sig=module_param_sig,
            module_param_args=module_param_args,
            left_module_ref=left_module_ref,
            right_module_ref=right_module_ref,
            eq_args_strong=eq_args_strong,
            eq_post_strong=eq_post_strong,
            layout=layout,
        )
        if partial is not None:
            return partial
        return _partial_split_admit("Split Uniform Samples", name_l, name_r, name_res)
    # Register the concat triple so the round-trip + distribution-split
    # axioms get emitted in TypeCollector.emit(). For Split the (l, r,
    # res) concat doesn't appear in the actual game bodies (only slices
    # do); without this call the axioms would be missing.
    types.register_concat(name_l, name_r, name_res)
    # The engine's split can emit either orientation: ``a_var`` may
    # replace either ``slice(orig, 0, |L|)`` or
    # ``slice(orig, |L|, |L|+|R|)``. Detect which by walking the after-
    # tail (post the two new samples) in parallel with the before-tail
    # (post the original sample) and matching the first variable use
    # against the first slice. Swap ``(a_var, b_var)`` in the tactic
    # invariant if the engine's orientation is reversed.
    before_tail = before_stmts[common + 1 :]
    after_tail = after_stmts[common + 2 :]
    first_slice = _find_first_slice_of(before_tail, s_orig.var.name)
    first_var = _find_first_var_use(after_tail, {s_a.var.name, s_b.var.name})
    swap_split = False
    if first_slice is not None and first_var is not None:
        first_is_left = (
            isinstance(first_slice.start, frog_ast.Integer)
            and first_slice.start.num == 0
        )
        # When the first use is the LEFT half, the first-used variable
        # should be ``a_var``; when it's the RIGHT half, ``b_var``. If
        # the engine's mapping is reversed (5_10 hop 2 surfaces this:
        # ``y = r0[lambda..2*lambda]`` on the left side becomes
        # ``y = r0_0`` on the right), the invariant binding ``a`` ↔ left
        # half must be flipped — and so must the rndsem* bijection's
        # component order in the HEAD subgoal.
        if first_is_left and first_var == s_b.var.name:
            swap_split = True
        elif not first_is_left and first_var == s_a.var.name:
            swap_split = True
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
        swap_split=swap_split,
        eq_args_strong=eq_args_strong,
    )


def _find_first_slice_of(
    stmts: list[frog_ast.Statement], orig_name: str
) -> frog_ast.Slice | None:
    """Return the first ``Slice`` over ``orig_name`` encountered in
    left-to-right depth-first traversal of ``stmts``."""

    def walk(node: object) -> frog_ast.Slice | None:
        if isinstance(node, frog_ast.Slice) and isinstance(
            node.the_array, frog_ast.Variable
        ):
            if node.the_array.name == orig_name:
                return node
        if isinstance(node, frog_ast.BinaryOperation):
            return walk(node.left_expression) or walk(node.right_expression)
        if isinstance(node, frog_ast.UnaryOperation):
            return walk(node.expression)
        if isinstance(node, frog_ast.FuncCall):
            for a in node.args:
                r = walk(a)
                if r is not None:
                    return r
        if isinstance(node, frog_ast.Slice):
            return walk(node.the_array)
        if isinstance(node, frog_ast.Assignment):
            return walk(node.value)
        if isinstance(node, frog_ast.Sample):
            return walk(node.sampled_from)
        if isinstance(node, frog_ast.ReturnStatement):
            return walk(node.expression)
        return None

    for stmt in stmts:
        r = walk(stmt)
        if r is not None:
            return r
    return None


def _find_first_var_use(stmts: list[frog_ast.Statement], names: set[str]) -> str | None:
    """Return the name of the first ``Variable`` in ``names`` used in
    left-to-right depth-first traversal."""

    def walk(node: object) -> str | None:
        if isinstance(node, frog_ast.Variable) and node.name in names:
            return node.name
        if isinstance(node, frog_ast.BinaryOperation):
            return walk(node.left_expression) or walk(node.right_expression)
        if isinstance(node, frog_ast.UnaryOperation):
            return walk(node.expression)
        if isinstance(node, frog_ast.FuncCall):
            for a in node.args:
                r = walk(a)
                if r is not None:
                    return r
            return walk(node.func)
        if isinstance(node, frog_ast.Slice):
            return walk(node.the_array)
        if isinstance(node, frog_ast.FieldAccess):
            return walk(node.the_object)
        if isinstance(node, frog_ast.Assignment):
            r = walk(node.value)
            if r is not None:
                return r
            return walk(node.var)
        if isinstance(node, frog_ast.Sample):
            r = walk(node.sampled_from)
            if r is not None:
                return r
            return walk(node.var)
        if isinstance(node, frog_ast.ReturnStatement):
            return walk(node.expression)
        return None

    for stmt in stmts:
        r = walk(stmt)
        if r is not None:
            return r
    return None


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


def _lengths_sum_equal(len_l: str, len_r: str, len_res: str) -> bool:
    """Return True iff ``len_l + len_r == len_res`` as integer expressions.

    Used to distinguish full splits (where ``concat (l, r) → res`` is a
    bijection on supports) from partial splits (where the source has
    extra bits that get discarded). Sympy canonicalization tolerates
    syntactic variants like ``lambda + lambda`` vs ``2 * lambda``.

    Python keywords (notably ``lambda`` — common in crypto length
    expressions) are renamed to safe aliases before sympify because
    sympy's parser delegates to Python's ``compile`` and chokes on
    keywords even when they appear in ``locals``.

    Returns False whenever sympy can't decide — the safe direction for
    the synthesizers (they fall back to admit rather than emit a
    bijection-based proof that might rely on an unsound axiom).
    """
    # pylint: disable=import-outside-toplevel
    try:
        import keyword as _kw

        from sympy import Symbol, simplify, sympify
    except ImportError:
        return False
    names = set(re.findall(r"[A-Za-z_]\w*", f"{len_l} {len_r} {len_res}"))
    # Rename any Python keyword identifier (e.g. ``lambda``) to a safe
    # alias so sympy's compile-based parser accepts the expression.
    renames = {n: f"_{n}_sym_" for n in names if _kw.iskeyword(n)}

    def _safe(s: str) -> str:
        out = s
        for old, new in renames.items():
            out = re.sub(rf"\b{re.escape(old)}\b", new, out)
        return out

    safe_names = {renames.get(n, n) for n in names}
    locals_ = {n: Symbol(n) for n in safe_names}
    try:
        e_l = sympify(_safe(len_l), locals=locals_)
        e_r = sympify(_safe(len_r), locals=locals_)
        e_res = sympify(_safe(len_res), locals=locals_)
        return bool(simplify((e_l + e_r) - e_res) == 0)
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def _collect_slice_ranges_for_var(
    node: object, var_name: str
) -> list[tuple[frog_ast.Expression, frog_ast.Expression]] | None:
    """Return (start, end) pairs of every ``Slice`` over ``var_name``.

    Returns ``None`` if ``var_name`` appears as a bare ``Variable``
    outside of a ``Slice`` — that signals the source variable is used
    for something other than slicing (e.g. passed whole to a method),
    so the partial-split synthesizer's assumptions are violated.
    """
    found: list[tuple[frog_ast.Expression, frog_ast.Expression]] = []
    bad = False

    def walk(n: object) -> None:
        nonlocal bad
        if isinstance(n, frog_ast.Slice):
            arr = n.the_array
            if isinstance(arr, frog_ast.Variable) and arr.name == var_name:
                found.append((n.start, n.end))
                walk(n.start)
                walk(n.end)
                return
        if isinstance(n, frog_ast.Variable) and n.name == var_name:
            bad = True
            return
        if isinstance(n, frog_ast.ASTNode):
            for attr in vars(n):
                walk(getattr(n, attr))
        elif isinstance(n, (list, tuple)):
            for item in n:
                walk(item)

    walk(node)
    if bad:
        return None
    return found


def _classify_partial_split_layout(
    tail_stmts: list[frog_ast.Statement],
    orig_var_name: str,
    len_l: str,
    len_r: str,
    len_res: str,
) -> str | None:
    """Classify the partial-split slice layout for a ``Split Uniform Samples``
    application.

    Returns one of:

    * ``"tail-gap"`` — slices are ``[0..|L|]`` and ``[|L|..|L|+|R|]``; the
      unused window is at the tail (``[|L|+|R|..|RES|]``). Both 5_8_b's
      hop_2 (TriplingPRG) and any future ``[L][R][gap]`` source layout.
    * ``"mid-gap"`` — slices are ``[0..|L|]`` and ``[|RES|-|R|..|RES|]``;
      the unused window is between L and R
      (``[|L|..|L|+|gap|]``). 5_8_a's hop_2 has this shape.
    * ``None`` — neither layout matches (head-gap, interleaved, or the
      source variable is referenced outside a slice). The caller falls
      back to ``_partial_split_admit``.

    ``tail_stmts`` are the statements following the orig sample
    declaration; walking only the tail avoids counting the declaration
    itself as a bare use of the source variable.
    """
    ranges = _collect_slice_ranges_for_var(tail_stmts, orig_var_name)
    if ranges is None or len(ranges) != 2:
        return None
    add_l_r = _add_canonical(len_l, len_r)
    res_minus_r = _subtract_canonical(len_res, len_r)
    actual: list[tuple[str, str]] = [(str(s), str(e)) for s, e in ranges]
    if add_l_r is not None:
        tail_gap = [("0", len_l), (len_l, add_l_r)]
        if _ranges_set_equal(actual, tail_gap):
            return "tail-gap"
    if res_minus_r is not None:
        mid_gap = [("0", len_l), (res_minus_r, len_res)]
        if _ranges_set_equal(actual, mid_gap):
            return "mid-gap"
    return None


def _has_module_call_tail(
    tail_stmts: list[frog_ast.Statement], orig_var_name: str
) -> bool:
    """Return True if the tail wraps slices of ``orig_var_name`` in
    module-method calls (e.g. ``G.evaluate(slice ...)``) before reaching
    the return.

    The simple-concat Mid/Aug template emits a return concat that
    assumes the procedure return is ``concat (slice_L) (slice_R)`` (a
    direct concat of the two slices). When each slice is instead an
    argument to a module call, the procedure return type doesn't equal
    ``|L| + |R|`` and the emitted ``concat_<L>_<R>_to_<ret>`` axiom would
    be unsound. The module-call-tail variant
    (``_detect_module_call_tail_pattern``) handles this shape; this
    coarser check is used as a fallback gate when the richer pattern
    isn't recognized.
    """

    def has_module_call(node: object) -> bool:
        if isinstance(node, frog_ast.FuncCall) and isinstance(
            node.func, frog_ast.FieldAccess
        ):
            return True
        if isinstance(node, frog_ast.ASTNode):
            for attr in vars(node):
                if has_module_call(getattr(node, attr)):
                    return True
            return False
        if isinstance(node, (list, tuple)):
            return any(has_module_call(item) for item in node)
        return False

    _ = orig_var_name  # captured for future tail-aware variants
    return has_module_call(tail_stmts)


def _detect_module_call_tail_pattern(
    tail_stmts: list[frog_ast.Statement], orig_var_name: str
) -> dict[str, str] | None:
    """Detect the specific tail shape ``return M.f(slice_L(orig)) ||
    M.f(slice_R(orig))`` and return the module/method names.

    Used by the partial-split synthesizer to emit Mid/Aug bodies that
    splice the post-slice ``M.f(...)`` calls verbatim, so the return
    concat in the helper modules matches the actual flat-state module's
    return (``concat (M.f result) (M.f result)``, with the call's output
    bitstring type, not the slice's input bitstring type).

    Returns ``None`` if the tail isn't a single ``ReturnStatement`` whose
    expression is ``BinaryOp(OR, FuncCall1, FuncCall2)`` with both calls
    targeting the same ``module.method`` and arguments that are slices of
    ``orig_var_name``.
    """
    if len(tail_stmts) != 1:
        return None
    stmt = tail_stmts[0]
    if not isinstance(stmt, frog_ast.ReturnStatement):
        return None
    expr = stmt.expression
    if not isinstance(expr, frog_ast.BinaryOperation):
        return None
    if expr.operator != frog_ast.BinaryOperators.OR:
        return None
    left, right = expr.left_expression, expr.right_expression
    if not (
        isinstance(left, frog_ast.FuncCall) and isinstance(right, frog_ast.FuncCall)
    ):
        return None
    if not (
        isinstance(left.func, frog_ast.FieldAccess)
        and isinstance(right.func, frog_ast.FieldAccess)
    ):
        return None
    if not (
        isinstance(left.func.the_object, frog_ast.Variable)
        and isinstance(right.func.the_object, frog_ast.Variable)
    ):
        return None
    if (
        left.func.name != right.func.name
        or left.func.the_object.name != right.func.the_object.name
    ):
        return None
    if len(left.args) != 1 or len(right.args) != 1:
        return None
    arg_l, arg_r = left.args[0], right.args[0]
    if not (isinstance(arg_l, frog_ast.Slice) and isinstance(arg_r, frog_ast.Slice)):
        return None
    if not (
        isinstance(arg_l.the_array, frog_ast.Variable)
        and isinstance(arg_r.the_array, frog_ast.Variable)
    ):
        return None
    if arg_l.the_array.name != orig_var_name or arg_r.the_array.name != orig_var_name:
        return None
    return {
        "module": left.func.the_object.name,
        "method": left.func.name,
    }


def _ranges_set_equal(
    actual: list[tuple[str, str]], expected: list[tuple[str, str]]
) -> bool:
    """Set-equality of two range lists where each (a, b) entry is
    compared as integer expressions via sympy. Order-insensitive.
    """
    # pylint: disable=import-outside-toplevel
    try:
        import keyword as _kw

        from sympy import Symbol, simplify, sympify
    except ImportError:
        return False
    if len(actual) != len(expected):
        return False
    all_strs = " ".join(s for pair in actual + expected for s in pair)
    names = set(re.findall(r"[A-Za-z_]\w*", all_strs))
    renames = {n: f"_{n}_sym_" for n in names if _kw.iskeyword(n)}

    def _safe(s: str) -> str:
        out = s
        for old, new in renames.items():
            out = re.sub(rf"\b{re.escape(old)}\b", new, out)
        return out

    safe_names = {renames.get(n, n) for n in names}
    locals_ = {n: Symbol(n) for n in safe_names}

    def _norm(pair: tuple[str, str]) -> tuple[object, object] | None:
        try:
            a = simplify(sympify(_safe(pair[0]), locals=locals_))
            b = simplify(sympify(_safe(pair[1]), locals=locals_))
            return (a, b)
        except Exception:  # pylint: disable=broad-exception-caught
            return None

    actual_norm = [_norm(p) for p in actual]
    expected_norm = [_norm(p) for p in expected]
    if any(p is None for p in actual_norm + expected_norm):
        return False
    remaining = list(expected_norm)
    for ap in actual_norm:
        match_idx = next(
            (i for i, ep in enumerate(remaining) if ep == ap),
            None,
        )
        if match_idx is None:
            return False
        remaining.pop(match_idx)
    return not remaining


def _return_bs_name(app: TransformApplication, types: TypeCollector) -> str | None:
    """Extract the bitstring type name of the after-game's return value.

    The return type is e.g. ``BitString<lambda + lambda>`` which collapses
    to ``bs_2_lambda`` via :meth:`TypeCollector.translate_type`. Used to
    name the 2-way concat op in the return statements of synthesized
    helper modules.
    """
    if not app.game_after.methods:
        return None
    ret_type = app.game_after.methods[0].signature.return_type
    bs = _resolve_bs_type(ret_type)
    if bs is None:
        return None
    return _bs_name_via_collector(types, bs)


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def _partial_split_helpers(
    *,
    types: TypeCollector,
    len_l: str,
    len_r: str,
    len_res: str,
    name_l: str,
    name_r: str,
    name_res: str,
    ret_type: str | None,
    orig_var: str,
    a_var: str,
    b_var: str,
    helpers: list[str] | None,
    name_prefix: str,
    module_param_sig: str,
    module_param_args: str,
    left_module_ref: str,
    right_module_ref: str,
    eq_args_strong: str,
    eq_post_strong: str,
    layout: str,
) -> list[str] | None:
    """Emit helper modules + sub-lemmas for a partial-split micro and
    return the chain-through-them tactic body.

    Strategy (see prototype in ``scripts/_taclab/partial_split.ec``):

    * ``Mid`` module: samples 3 indep ``bs_<L>``/``bs_<R>``/``bs_<GAP>``
      pieces in the source-layout order, builds ``r := concat3 ...``,
      returns the 2-way concat of two slices of ``r``.
    * ``Aug`` module: samples the same 3 pieces in the same order,
      returns ``concat a b`` directly (the gap is dead).
    * ``left_to_mid``: relate ``r <$ dbs_<RES>`` to the 3-sample form via
      ``rndsem*{2} 0`` + ``rnd identity`` + ``dbs_<RES>_split3`` axiom.
    * ``mid_to_aug``: trivial after slice-of-concat3 rewrites (the two
      slice axioms naming the L and R pieces of the concat3).
    * ``aug_to_right``: drop the dead ``gap`` sample via ``rnd{1}``
      + ``dbs_<GAP>_ll``. For ``mid-gap`` layouts, a leading
      ``swap{1} 2 1`` first reorders the side-1 samples so the dead
      gap sample lands at the tail.
    * Main tactic: ``transitivity Aug; [smt | smt | (transitivity Mid;
      [smt | smt | apply left_to_mid | apply mid_to_aug]) | apply
      aug_to_right]``.

    The ``layout`` parameter selects between ``"tail-gap"`` (slices
    ``[0..|L|]`` + ``[|L|..|L|+|R|]``; concat3 piece order
    ``(L, R, GAP)``) and ``"mid-gap"`` (slices ``[0..|L|]`` +
    ``[|RES|-|R|..|RES|]``; concat3 piece order ``(L, GAP, R)``).

    Returns ``None`` if any prerequisite is missing (gap length not
    sympifiable, no helpers list, etc.).
    """
    if (
        helpers is None
        or not name_prefix
        or not module_param_sig
        or ret_type is None
        or not left_module_ref
        or not right_module_ref
        or not eq_args_strong
        or not eq_post_strong
        or layout not in ("tail-gap", "mid-gap")
    ):
        return None
    gap_len = _subtract_canonical(len_res, _add_canonical(len_l, len_r))
    if gap_len is None:
        return None
    name_gap = types.register_bs_by_length_str(gap_len)
    # Register the concat3 op in the source-layout order so the emitted
    # ``slice_concat3_p1/p2/p3`` axioms index the pieces in the order the
    # Mid module assembles them via ``concat3 ...``.
    if layout == "tail-gap":
        types.register_concat3(name_l, name_r, name_gap, name_res)
        piece1, piece2, piece3 = name_l, name_r, name_gap
    else:  # mid-gap
        types.register_concat3(name_l, name_gap, name_r, name_res)
        piece1, piece2, piece3 = name_l, name_gap, name_r
    # The 2-way return concat (e.g. ``concat_bs_lambda_bs_lambda_to_bs_2_lambda``).
    types.register_concat(name_l, name_r, ret_type)
    ret_concat_op = f"concat_{name_l}_{name_r}_to_{ret_type}"
    concat3_op = f"concat3_{piece1}_{piece2}_{piece3}_to_{name_res}"
    slice_l = f"slice_{name_res}_to_{name_l}"
    slice_r = f"slice_{name_res}_to_{name_r}"
    distr_l = f"d{name_l}"
    distr_r = f"d{name_r}"
    distr_gap = f"d{name_gap}"
    split3_axiom = f"d{name_res}_split3_{piece1}_{piece2}_{piece3}"
    axiom_prefix = f"{piece1}_{piece2}_{piece3}_{name_res}"
    p1_axiom = f"slice_concat3_p1_{axiom_prefix}"
    p2_axiom = f"slice_concat3_p2_{axiom_prefix}"
    p3_axiom = f"slice_concat3_p3_{axiom_prefix}"
    len_l_p = _bs_length_arg(len_l)
    len_res_p = _bs_length_arg(len_res)
    # Use the sympy-canonical sum so the slice end argument matches what
    # the rest of the EC file emits (e.g. ``2 * lambda`` not ``lambda +
    # lambda``); without this, ``sim`` fails to match the two slices.
    canonical_sum = _add_canonical(len_l, len_r)
    len_lr = _bs_length_arg(canonical_sum) if canonical_sum else f"({len_l} + {len_r})"
    canonical_l_gap = _add_canonical(len_l, gap_len)
    len_l_gap = (
        _bs_length_arg(canonical_l_gap) if canonical_l_gap else f"({len_l} + {gap_len})"
    )
    # Per-layout sample sequence, concat3 call, R-slice start, and the
    # axioms naming the L and R pieces in the concat3. Mid and Aug share
    # the sample order so ``mid_to_aug`` is trivial via the rnd-rnd-rnd
    # lockstep; the dead-gap sample sits in source-layout position.
    if layout == "tail-gap":
        sample_seq = [
            f"      {a_var} <$ {distr_l};",
            f"      {b_var} <$ {distr_r};",
            f"      _gap <$ {distr_gap};",
        ]
        concat3_call = f"{concat3_op} {a_var} {b_var} _gap"
        r_slice_start = len_l_p
        r_slice_end = len_lr
        mid_to_aug_axioms = f"{p1_axiom} {p2_axiom}"
        aug_to_right_reorder: list[str] = []
    else:  # mid-gap
        sample_seq = [
            f"      {a_var} <$ {distr_l};",
            f"      _gap <$ {distr_gap};",
            f"      {b_var} <$ {distr_r};",
        ]
        concat3_call = f"{concat3_op} {a_var} _gap {b_var}"
        r_slice_start = len_l_gap
        r_slice_end = len_res_p
        mid_to_aug_axioms = f"{p1_axiom} {p3_axiom}"
        # The right module samples ``a, b`` in that order. Swap the
        # side-1 gap and b samples so the first two statements pair off
        # with the right side under the seq-2-2 invariant below.
        aug_to_right_reorder = ["  swap{1} 2 1."]
    mid_mod = f"Mid_{name_prefix}"
    aug_mod = f"Aug_{name_prefix}"
    l2m = f"left_to_mid_{name_prefix}"
    m2a = f"mid_to_aug_{name_prefix}"
    a2r = f"aug_to_right_{name_prefix}"
    l2a = f"left_to_aug_{name_prefix}"
    mid_inst = f"{mid_mod}{module_param_args}"
    aug_inst = f"{aug_mod}{module_param_args}"
    # Mid module.
    helpers.append(
        "\n".join(
            [
                f"  module {mid_mod} {module_param_sig} = {{",
                f"    proc query() : {ret_type} = {{",
                f"      var {orig_var} : {name_res};",
                f"      var {a_var}, {b_var} : {name_l};",
                f"      var _gap : {name_gap};",
                *sample_seq,
                f"      {orig_var} <- {concat3_call};",
                f"      return {ret_concat_op}",
                f"               ({slice_l} {orig_var} 0 {len_l_p})",
                f"               ({slice_r} {orig_var} {r_slice_start}"
                f" {r_slice_end});",
                "    }",
                "  }.",
            ]
        )
    )
    # Aug module.
    helpers.append(
        "\n".join(
            [
                f"  module {aug_mod} {module_param_sig} = {{",
                f"    proc query() : {ret_type} = {{",
                f"      var {a_var}, {b_var} : {name_l};",
                f"      var _gap : {name_gap};",
                *sample_seq,
                f"      return {ret_concat_op} {a_var} {b_var};",
                "    }",
                "  }.",
            ]
        )
    )
    spec = f"({eq_args_strong} ==> {eq_post_strong})"
    # left_to_mid sub-lemma.
    helpers.append(
        "\n".join(
            [
                f"  lemma {l2m} :",
                f"    equiv [ {left_module_ref}.query ~ {mid_inst}.query :",
                f"            {eq_args_strong} ==> {eq_post_strong} ].",
                "  proof.",
                "  proc.",
                f"  seq 1 4 : ({eq_args_strong} /\\ {orig_var}{{1}} = {orig_var}{{2}});"
                f" last by auto.",
                "  rndsem*{2} 0.",
                f"  conseq (: {eq_args_strong} ==>"
                f" {eq_args_strong} /\\ {orig_var}{{1}} = {orig_var}{{2}}) => //.",
                f"  rnd (fun (z : {name_res}) => z) (fun (z : {name_res}) => z);"
                f" skip => />.",
                f"  rewrite -{split3_axiom} /=; smt({split3_axiom}).",
                "  qed.",
            ]
        )
    )
    # mid_to_aug sub-lemma.
    helpers.append(
        "\n".join(
            [
                f"  lemma {m2a} :",
                f"    equiv [ {mid_inst}.query ~ {aug_inst}.query :",
                f"            {eq_args_strong} ==> {eq_post_strong} ].",
                "  proof.",
                f"  proc; wp; rnd; rnd; rnd; skip => /> *; smt({mid_to_aug_axioms}).",
                "  qed.",
            ]
        )
    )
    # aug_to_right sub-lemma.
    helpers.append(
        "\n".join(
            [
                f"  lemma {a2r} :",
                f"    equiv [ {aug_inst}.query ~ {right_module_ref}.query :",
                f"            {eq_args_strong} ==> {eq_post_strong} ].",
                "  proof.",
                "  proc.",
                *aug_to_right_reorder,
                f"  seq 2 2 : ({eq_args_strong} /\\ {a_var}{{1}} = {a_var}{{2}}"
                f" /\\ {b_var}{{1}} = {b_var}{{2}}).",
                "  by auto.",
                "  rnd{1}.",
                f"  by auto; smt({distr_gap}_ll).",
                "  qed.",
            ]
        )
    )
    # left_to_aug wrapper that chains via Mid.
    helpers.append(
        "\n".join(
            [
                f"  lemma {l2a} :",
                f"    equiv [ {left_module_ref}.query ~ {aug_inst}.query :",
                f"            {eq_args_strong} ==> {eq_post_strong} ].",
                "  proof.",
                f"  transitivity {mid_inst}.query {spec} {spec};"
                f" [ smt() | smt() | apply {l2m} | apply {m2a} ].",
                "  qed.",
            ]
        )
    )
    # Main tactic body for the micro lemma: transitivity through Aug.
    return [
        f"transitivity {aug_inst}.query {spec} {spec};"
        f" [ smt() | smt() | apply {l2a} | apply {a2r} ].",
    ]


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-statements,too-many-branches
def _partial_split_helpers_modcall(
    *,
    types: TypeCollector,
    len_l: str,
    len_r: str,
    len_res: str,
    name_l: str,
    name_r: str,
    name_res: str,
    ret_type: str | None,
    orig_var: str,
    a_var: str,
    b_var: str,
    helpers: list[str] | None,
    name_prefix: str,
    module_param_sig: str,
    module_param_args: str,
    left_module_ref: str,
    right_module_ref: str,
    eq_args_strong: str,
    eq_post_strong: str,
    layout: str,
    module_name: str,
    method_name: str,
) -> list[str] | None:
    """Module-call-tail variant of :func:`_partial_split_helpers`.

    Handles the partial-split case where each used slice of the source
    bitstring is wrapped in a module-method call before contributing to
    the procedure's return, i.e. the before-game's tail is

        return M.f(slice_L(orig)) || M.f(slice_R(orig))

    The state module's hoisted EC body becomes

        orig <$ dRES;
        _r0 <@ M.f(slice_L orig 0 |L|);
        _r1 <@ M.f(slice_R orig <r_start> <r_end>);
        return concat_<eval_ret>_<eval_ret>_to_<ret_type> _r0 _r1;

    The simple ``_partial_split_helpers`` would emit Mid/Aug bodies whose
    return is ``concat (slice_L) (slice_R)`` — the wrong shape (and
    triggers an unsound ``concat_<L>_<R>_to_<ret_type>`` axiom, since
    ``|L| + |R| ≠ |ret_type|`` in this case). The module-call-tail
    variant splices the ``M.f`` calls into the helper modules so the
    helpers' returns match the state modules' returns.

    Mirror of the simple helpers' chain structure: ``Mid`` mediates the
    distribution rewrite via concat3; ``Aug`` matches the after-state
    plus a dead gap sample; sub-lemmas ``left_to_mid`` / ``mid_to_aug``
    / ``aug_to_right`` / ``left_to_aug`` close the chain; the main
    tactic is ``transitivity Aug; [smt | smt | apply left_to_aug | apply
    aug_to_right]``.

    Returns ``None`` if any prerequisite is missing.
    """
    if (
        helpers is None
        or not name_prefix
        or not module_param_sig
        or ret_type is None
        or not left_module_ref
        or not right_module_ref
        or not eq_args_strong
        or not eq_post_strong
        or layout not in ("tail-gap", "mid-gap")
    ):
        return None
    ret_len = types.bs_length_for(ret_type)
    if ret_len is None:
        return None
    # ``M.f`` returns the bitstring whose length is half the procedure
    # return: the return is ``concat (M.f a) (M.f b)`` of two equal-length
    # pieces. If the length isn't evenly halvable in sympy, bail.
    eval_ret_len = _divide_canonical(ret_len, "2")
    if eval_ret_len is None:
        return None
    eval_ret = types.register_bs_by_length_str(eval_ret_len)
    # Register the proper return concat ``eval_ret + eval_ret -> ret_type``.
    types.register_concat(eval_ret, eval_ret, ret_type)
    gap_len = _subtract_canonical(len_res, _add_canonical(len_l, len_r))
    if gap_len is None:
        return None
    name_gap = types.register_bs_by_length_str(gap_len)
    if layout == "tail-gap":
        types.register_concat3(name_l, name_r, name_gap, name_res)
        piece1, piece2, piece3 = name_l, name_r, name_gap
    else:
        types.register_concat3(name_l, name_gap, name_r, name_res)
        piece1, piece2, piece3 = name_l, name_gap, name_r
    concat3_op = f"concat3_{piece1}_{piece2}_{piece3}_to_{name_res}"
    ret_concat_op = f"concat_{eval_ret}_{eval_ret}_to_{ret_type}"
    slice_l = f"slice_{name_res}_to_{name_l}"
    slice_r = f"slice_{name_res}_to_{name_r}"
    distr_l = f"d{name_l}"
    distr_r = f"d{name_r}"
    distr_gap = f"d{name_gap}"
    split3_axiom = f"d{name_res}_split3_{piece1}_{piece2}_{piece3}"
    axiom_prefix = f"{piece1}_{piece2}_{piece3}_{name_res}"
    p1_axiom = f"slice_concat3_p1_{axiom_prefix}"
    p2_axiom = f"slice_concat3_p2_{axiom_prefix}"
    p3_axiom = f"slice_concat3_p3_{axiom_prefix}"
    len_l_p = _bs_length_arg(len_l)
    len_res_p = _bs_length_arg(len_res)
    canonical_sum = _add_canonical(len_l, len_r)
    len_lr = _bs_length_arg(canonical_sum) if canonical_sum else f"({len_l} + {len_r})"
    canonical_l_gap = _add_canonical(len_l, gap_len)
    len_l_gap = (
        _bs_length_arg(canonical_l_gap) if canonical_l_gap else f"({len_l} + {gap_len})"
    )
    if layout == "tail-gap":
        sample_seq = [
            f"      {a_var} <$ {distr_l};",
            f"      {b_var} <$ {distr_r};",
            f"      _gap <$ {distr_gap};",
        ]
        concat3_call = f"{concat3_op} {a_var} {b_var} _gap"
        r_slice_start = len_l_p
        r_slice_end = len_lr
        r_piece_axiom = p2_axiom
        aug_to_right_reorder: list[str] = []
    else:  # mid-gap
        sample_seq = [
            f"      {a_var} <$ {distr_l};",
            f"      _gap <$ {distr_gap};",
            f"      {b_var} <$ {distr_r};",
        ]
        concat3_call = f"{concat3_op} {a_var} _gap {b_var}"
        r_slice_start = len_l_gap
        r_slice_end = len_res_p
        r_piece_axiom = p3_axiom
        aug_to_right_reorder = ["  swap{1} 2 1."]
    mid_mod = f"Mid_{name_prefix}"
    aug_mod = f"Aug_{name_prefix}"
    l2m = f"left_to_mid_{name_prefix}"
    m2a = f"mid_to_aug_{name_prefix}"
    a2r = f"aug_to_right_{name_prefix}"
    l2a = f"left_to_aug_{name_prefix}"
    mid_inst = f"{mid_mod}{module_param_args}"
    aug_inst = f"{aug_mod}{module_param_args}"
    # Mid module — same head as the simple variant, but the tail splices
    # the ``M.f(slice ...)`` calls and a return that concats the two
    # call results via the proper ``eval_ret + eval_ret -> ret_type`` op.
    helpers.append(
        "\n".join(
            [
                f"  module {mid_mod} {module_param_sig} = {{",
                f"    proc query() : {ret_type} = {{",
                f"      var {orig_var} : {name_res};",
                f"      var {a_var}, {b_var} : {name_l};",
                f"      var _gap : {name_gap};",
                f"      var _r0, _r1 : {eval_ret};",
                *sample_seq,
                f"      {orig_var} <- {concat3_call};",
                f"      _r0 <@ {module_name}.{method_name}"
                f"({slice_l} {orig_var} 0 {len_l_p});",
                f"      _r1 <@ {module_name}.{method_name}"
                f"({slice_r} {orig_var} {r_slice_start} {r_slice_end});",
                f"      return {ret_concat_op} _r0 _r1;",
                "    }",
                "  }.",
            ]
        )
    )
    # Aug module — same as the after-state plus a dead ``_gap`` sample.
    helpers.append(
        "\n".join(
            [
                f"  module {aug_mod} {module_param_sig} = {{",
                f"    proc query() : {ret_type} = {{",
                f"      var {a_var}, {b_var} : {name_l};",
                f"      var _gap : {name_gap};",
                f"      var _r0, _r1 : {eval_ret};",
                *sample_seq,
                f"      _r0 <@ {module_name}.{method_name}({a_var});",
                f"      _r1 <@ {module_name}.{method_name}({b_var});",
                f"      return {ret_concat_op} _r0 _r1;",
                "    }",
                "  }.",
            ]
        )
    )
    spec = f"({eq_args_strong} ==> {eq_post_strong})"
    # left_to_mid: seq 1 4 pairs the single sample on side 1 with the
    # 3-sample + concat3 head on side 2; the remaining tail (2 calls +
    # return) is identical under ``orig{1}=orig{2}``, so ``sim`` closes.
    helpers.append(
        "\n".join(
            [
                f"  lemma {l2m} :",
                f"    equiv [ {left_module_ref}.query ~ {mid_inst}.query :",
                f"            {eq_args_strong} ==> {eq_post_strong} ].",
                "  proof.",
                "  proc.",
                f"  seq 1 4 : ({eq_args_strong} /\\ {orig_var}{{1}}"
                f" = {orig_var}{{2}}); last by sim.",
                "  rndsem*{2} 0.",
                f"  conseq (: {eq_args_strong} ==>"
                f" {eq_args_strong} /\\ {orig_var}{{1}} = {orig_var}{{2}}) => //.",
                f"  rnd (fun (z : {name_res}) => z) (fun (z : {name_res}) => z);"
                f" skip => />.",
                f"  rewrite -{split3_axiom} /=; smt({split3_axiom}).",
                "  qed.",
            ]
        )
    )
    # mid_to_aug: the 3 samples pair off lockstep; the side-1 ``orig``
    # assignment + the slice-axiom rewrites supply the
    # ``slice_L orig 0 |L| = a`` and ``slice_R orig <r_start> <r_end> = b``
    # equations that make the call-arg side conditions discharge.
    inv_strong = (
        f"{eq_args_strong} /\\ {a_var}{{1}}={a_var}{{2}}"
        f" /\\ {b_var}{{1}}={b_var}{{2}} /\\ _gap{{1}}=_gap{{2}}"
        f" /\\ {slice_l} {orig_var}{{1}} 0 {len_l_p} = {a_var}{{2}}"
        f" /\\ {slice_r} {orig_var}{{1}} {r_slice_start} {r_slice_end}"
        f" = {b_var}{{2}}"
    )
    helpers.append(
        "\n".join(
            [
                f"  lemma {m2a} :",
                f"    equiv [ {mid_inst}.query ~ {aug_inst}.query :",
                f"            {eq_args_strong} ==> {eq_post_strong} ].",
                "  proof.",
                "  proc.",
                f"  seq 4 3 : ({inv_strong}).",
                f"  - by auto; smt({p1_axiom} {r_piece_axiom}).",
                "  wp.",
                "  call (_: true).",
                "  wp.",
                "  call (_: true).",
                "  skip => />.",
                "  qed.",
            ]
        )
    )
    # aug_to_right: the right (state-after) module has the same body as
    # Aug minus the dead ``_gap`` sample. For ``mid-gap`` the gap sits in
    # source-layout position 2, so ``swap{1} 2 1`` first moves it to the
    # tail; both layouts then close via ``seq 2 2 + rnd{1} + ll``.
    helpers.append(
        "\n".join(
            [
                f"  lemma {a2r} :",
                f"    equiv [ {aug_inst}.query ~ {right_module_ref}.query :",
                f"            {eq_args_strong} ==> {eq_post_strong} ].",
                "  proof.",
                "  proc.",
                *aug_to_right_reorder,
                f"  seq 2 2 : ({eq_args_strong} /\\ {a_var}{{1}}={a_var}{{2}}"
                f" /\\ {b_var}{{1}}={b_var}{{2}}).",
                "  by auto.",
                "  seq 1 0 : "
                f"({eq_args_strong} /\\ {a_var}{{1}}={a_var}{{2}}"
                f" /\\ {b_var}{{1}}={b_var}{{2}}).",
                f"  - by rnd{{1}}; auto; smt({distr_gap}_ll).",
                "  sim.",
                "  qed.",
            ]
        )
    )
    # left_to_aug wrapper.
    helpers.append(
        "\n".join(
            [
                f"  lemma {l2a} :",
                f"    equiv [ {left_module_ref}.query ~ {aug_inst}.query :",
                f"            {eq_args_strong} ==> {eq_post_strong} ].",
                "  proof.",
                f"  transitivity {mid_inst}.query {spec} {spec};"
                f" [ smt() | smt() | apply {l2m} | apply {m2a} ].",
                "  qed.",
            ]
        )
    )
    return [
        f"transitivity {aug_inst}.query {spec} {spec};"
        f" [ smt() | smt() | apply {l2a} | apply {a2r} ].",
    ]


def _add_canonical(a: str, b: str) -> str | None:
    """Return canonical-sum of two integer expression strings via sympy,
    or ``None`` on sympify failure (Python keyword fallback included).
    """
    return _binop_canonical(a, b, "+")


def _subtract_canonical(a: str, b: str | None) -> str | None:
    """Return canonical-difference ``a - b``, or ``None`` on failure."""
    if b is None:
        return None
    return _binop_canonical(a, b, "-")


def _divide_canonical(a: str, b: str) -> str | None:
    """Return canonical ``a / b``, or ``None`` on failure or non-integer."""
    return _binop_canonical(a, b, "/")


def _binop_canonical(a: str, b: str, op: str) -> str | None:
    # pylint: disable=import-outside-toplevel
    try:
        import keyword as _kw

        from sympy import Symbol, simplify, sympify
    except ImportError:
        return None
    names = set(re.findall(r"[A-Za-z_]\w*", f"{a} {b}"))
    renames = {n: f"_{n}_sym_" for n in names if _kw.iskeyword(n)}
    inv_renames = {v: k for k, v in renames.items()}

    def _safe(s: str) -> str:
        out = s
        for old, new in renames.items():
            out = re.sub(rf"\b{re.escape(old)}\b", new, out)
        return out

    safe_names = {renames.get(n, n) for n in names}
    locals_ = {n: Symbol(n) for n in safe_names}
    try:
        ea = sympify(_safe(a), locals=locals_)
        eb = sympify(_safe(b), locals=locals_)
        if op == "+":
            result = simplify(ea + eb)
        elif op == "-":
            result = simplify(ea - eb)
        else:  # "/"
            result = simplify(ea / eb)
    except Exception:  # pylint: disable=broad-exception-caught
        return None
    out = str(result)
    # Reverse the keyword-renaming.
    for old, new in inv_renames.items():
        out = re.sub(rf"\b{re.escape(old)}\b", new, out)
    return out


def _partial_split_admit(
    transform_name: str, name_l: str, name_r: str, name_res: str
) -> list[str]:
    """Return a structured-admit micro body for partial-split shapes.

    Emitted when a ``Split Uniform Samples`` / ``Merge Uniform Samples``
    application has ``|L| + |R| != |RES|`` — i.e. the source bitstring
    has unused bits that the engine discards via dead-code elimination.
    The existing bijection-based tactic would otherwise register an
    *unsound* ``concat_<L>_<R>_<RES>`` axiom claiming a two-piece concat
    produces ``RES`` (image cardinality ``2^(|L|+|R|)`` vs ``RES`` space
    ``2^|RES|`` — different for partial splits). The chain-fallback in
    ``exporter.emit_chain_for_hop`` sees the ``admit.`` and replaces the
    outer ``hop_<i>`` with admit so the file remains compilable.
    """
    return [
        "(* parametric tactic miss",
        f"   transform: {transform_name!r}",
        f"   reason:    partial split ({name_l} + {name_r} != {name_res});",
        "              the sound marginal-distribution tactic is not yet",
        "              implemented (followup #4 of the TriplingPRG plan).",
        "   *)",
        "admit.",
    ]


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def _merge_tactic_body(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
    eq_args_strong: str = "",
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
    # Multi-module proofs require ``={glob X1, glob X2, ...}`` carried
    # through the transitivity intermediate; otherwise the residual
    # ``={glob P}`` (etc.) goal at qed time can't be discharged.
    if eq_args_strong:
        eq_inv = eq_args_strong
    else:
        eq_inv = "={glob G}"
    return [
        "proc.",
        "transitivity {2}",
        f"  {{ {merged_var} <$ dmap ({distr_l} `*` {distr_r})",
        f"                          (fun (p : {name_l} * {name_r}) =>",
        f"                             {concat_op} p.`1 p.`2); }}",
        f"  ({eq_inv} ==>",
        f"   {eq_inv} /\\ {concat_op} {l_var}{{1}} {r_var}{{1}} ="
        f" {merged_var}{{2}})",
        f"  ({eq_inv} ==> {eq_inv} /\\ ={{{merged_var}}}).",
        "- by smt().",
        "- by smt().",
        f"- seq 2 1 : ({eq_inv} /\\",
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
def _split_tactic_body(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
    swap_split: bool = False,
    eq_args_strong: str = "",
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
    # When the engine's split orientation maps the FIRST new sample to
    # the RIGHT half (e.g. ``y = slice(r0, lambda, 2*lambda)`` on the
    # left becomes ``y = r0_0`` on the right), prepend ``swap{2} 1 1``
    # so the two new samples appear in (left-half, right-half) order on
    # side 2, and pass the *swapped* names as ``a``/``b`` so the standard
    # invariant ``slice 0 |L| = a`` / ``slice |L| 2|L| = b`` lines up
    # with the post-swap sample order. The TAIL goal's deterministic
    # assignments then carry through automatically.
    if swap_split:
        a_var, b_var = b_var, a_var
    # In multi-module proofs, the equiv carries an enriched pre/post
    # that includes ``={glob G, glob P, ...}``. Each globs needs to be
    # preserved through the invariant; otherwise the TAIL leaves
    # un-discharged ``={glob P}`` (etc.) at qed time. Default to the
    # single-module shape ``={glob G}`` when the caller doesn't supply
    # ``eq_args_strong``.
    if eq_args_strong:
        eq_glob_inv = eq_args_strong
        eq_glob_pre = eq_args_strong
        eq_glob_post = eq_args_strong + f" /\\ ={{{orig_var}}}"
    else:
        eq_glob_inv = "={glob G}"
        eq_glob_pre = "={glob G}"
        eq_glob_post = "={glob G, " + orig_var + "}"
    prelude = ["proc."]
    if swap_split:
        prelude.append("swap{2} 1 1.")
    return [
        *prelude,
        f"seq 1 2 : ({eq_glob_inv} /\\",
        f"           {slice_l} {orig_var}{{1}} 0 {len_l_p} = {a_var}{{2}} /\\",
        f"           {slice_r} {orig_var}{{1}} {len_l_p} {len_sum} ="
        f" {b_var}{{2}}).",
        "- (* HEAD: sample step. *)",
        "  transitivity {1}",
        f"    {{ {orig_var} <$ dmap ({distr_l} `*` {distr_r})",
        f"                          (fun (p : {name_l} * {name_r}) =>",
        f"                             {concat_op} p.`1 p.`2); }}",
        f"    ({eq_glob_pre} ==> {eq_glob_post})",
        f"    ({eq_glob_pre} ==>",
        f"     {eq_glob_inv} /\\",
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
        # ``auto`` (not ``skip``) is needed when the deterministic tail
        # contains an assignment like ``y = slice(orig, ...)`` ahead of
        # the call: ``skip`` only closes the leaf, while ``auto`` peels
        # off head/tail wp/sp to feed the invariant through. The locked-
        # in proofs that use plain ``skip => /> *`` have no such pre-
        # call assignment.
        "  auto => /> *.",
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
    """Return ``(uniform_var_name, dropped_operand_expr)`` if the XOR
    simplification fires at this position. ``before`` is
    ``BinaryOperation(ADD, u, m)`` (in either order) and ``after`` is
    just ``u``; or the same shape nested inside a matching containing
    expression. Else ``None``.

    The recursion handles cases where the XOR simplification happens
    inside a larger expression — most commonly a concatenation in the
    return position (``(u + m) || rest`` → ``u || rest``), but also
    nested concatenations on either side. We descend through any
    ``BinaryOperation`` whose operator and untouched side match between
    before and after, locating the single sub-position where the XOR is
    dropped.
    """
    if isinstance(after, frog_ast.Variable):
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
    if (
        isinstance(before, frog_ast.BinaryOperation)
        and isinstance(after, frog_ast.BinaryOperation)
        and before.operator == after.operator
    ):
        # Descend into whichever side differs (the other must match
        # structurally). If both sides differ, the diff isn't a single
        # XOR-drop and we bail.
        left_eq = before.left_expression == after.left_expression
        right_eq = before.right_expression == after.right_expression
        if left_eq and not right_eq:
            return _xor_dropped_operand(before.right_expression, after.right_expression)
        if right_eq and not left_eq:
            return _xor_dropped_operand(before.left_expression, after.left_expression)
    return None
