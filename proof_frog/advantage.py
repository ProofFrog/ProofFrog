"""Synthesize the advantage bound a verified game-hopping proof establishes.

This is a pure fold over a proof's verified hops and carries no dependency on
the canonicalization transforms or the SMT/symbolic solvers used during
verification. It runs *after* a proof succeeds and turns the qualitative hop
sequence into a quantitative concrete-security bound.

The mathematical core is small. For left/right indistinguishability games the
distinguishing advantage is a metric, so the advantage across a sequence of
hops is bounded (triangle inequality) by the sum of the per-hop losses.
ProofFrog equivalence hops are *perfect* (they are established by
canonicalization, not statistical reasoning), so they contribute ``0``; only
assumption hops and lemma hops contribute terms. The result is represented as a
SymPy expression over opaque ``Adv_i`` symbols (one per distinct instantiated
assumption/adversary pair) so that collection, sums, and later inequality
comparison are all SymPy-native, with a side table mapping each symbol back to
the security notion and constructed adversary it stands for.

Inductive proofs are not yet supported: their bound is a symbolic sum over the
loop range, which the current fold does not synthesize. Such proofs report an
unsupported bound rather than a wrong one.

Helper assumption games (``examples/Games/Helpers/``) may *declare* a concrete
statistical advantage bound via an ``advantage <= ...`` clause whose free
variables are the games' set/scalar parameters and per-oracle query counts
``count_<Oracle>``. When a ``by_assumption`` hop resolves to such a game, its
opaque ``Adv`` term is replaced by the declared expression: set parameters come
from the assumption instantiation, and each ``count_<Oracle>`` is *derived* by
counting how many times the composed reduction invokes that oracle -- yielding a
bound in the theorem game's own per-oracle query counts (e.g. ``count_CTXT``).
Genuine cryptographic assumptions carry no clause and stay symbolic by design.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional, Sequence

import sympy

from . import frog_ast
from . import visitors

if TYPE_CHECKING:  # avoid an import cycle with proof_engine at runtime
    from .proof_engine import HopResult


class _UnconvertibleBound(Exception):
    """A declared advantage bound uses arithmetic this fold cannot convert."""


@dataclasses.dataclass(frozen=True)
class AdvTerm:
    """A single advantage term: a security notion for a constructed adversary.

    ``notion`` is the assumed (or lemma) security game the term measures
    against, e.g. ``PRFSecurity(F)``. ``adversary`` is the display name of the
    adversary playing it: a constructed reduction ``B1``, ``B2``, ... or ``A``
    when the notion is played directly (no reduction).
    """

    notion: frog_ast.ParameterizedGame
    adversary: str
    # The constructed adversary as a reduction over the notion, or ``None`` when
    # the notion is played directly (adversary ``A``). Carried so the Tier-3
    # bound checker can match a claim's ``advantage(notion compose reduction)``
    # reference to this term by the exact ``(notion, reduction)`` pair, rather
    # than by the display name ``adversary`` (``B1``, ``B2``, ...).
    reduction: Optional[frog_ast.ParameterizedGame] = None
    # When the notion is a helper game carrying a declared ``advantage`` clause,
    # its instantiated statistical bound (a SymPy expression over derived
    # per-oracle query counts and opaque set-cardinality symbols). ``None`` for
    # genuine cryptographic assumptions, which stay opaque ``Adv`` terms.
    statistical: Optional[sympy.Expr] = None


@dataclasses.dataclass
class HopInfo:
    """The bound-relevant summary of a single proof hop.

    ``kind`` is ``"equivalent"`` (contributes 0), ``"by_assumption"``, or
    ``"by_lemma"``. For the latter two, ``notion`` is the licensing security
    game and ``reduction`` the constructed adversary composed with it (or
    ``None`` when the notion is played directly against the adversary).
    ``statistical`` carries a resolved helper-game bound (see
    :func:`resolve_statistical`); ``note`` explains why a helper bound was left
    symbolic (e.g. an unbounded query count).
    """

    kind: str
    notion: frog_ast.ParameterizedGame | None = None
    reduction: frog_ast.ParameterizedGame | None = None
    statistical: Optional[sympy.Expr] = None
    note: str = ""


@dataclasses.dataclass
class AdvantageBound:
    """The advantage bound established by a proof.

    ``expression`` is a SymPy expression over the ``Adv_i`` symbols keyed in
    ``terms``. When ``supported`` is False the bound could not be synthesized
    (see ``note``) and ``expression`` is meaningless.
    """

    expression: sympy.Expr
    terms: dict[sympy.Symbol, AdvTerm]
    supported: bool = True
    note: str = ""
    # Per-hop contribution, aligned 1:1 with the input hop sequence: the
    # ``AdvTerm`` a hop contributed, or None for an equivalence (0-loss) hop.
    hop_terms: list[AdvTerm | None] = dataclasses.field(default_factory=list)
    # Non-fatal remarks (e.g. a helper statistical bound left symbolic because
    # the proof declares no query-count bound). Printed alongside the bound.
    notes: list[str] = dataclasses.field(default_factory=list)

    def is_trivial(self) -> bool:
        """True when the proof establishes a zero (perfect) advantage bound."""
        return self.supported and sympy.expand(self.expression) == 0

    def substituted_expression(self) -> sympy.Expr:
        """The bound with each helper ``Adv`` symbol replaced by its bound.

        Opaque cryptographic terms keep their ``Adv_i`` symbol; helper terms
        carrying a declared statistical bound are substituted in. This is the
        fully SymPy-native form used for later inequality comparison (Tier 3).
        """
        subs = {
            symbol: term.statistical
            for symbol, term in self.terms.items()
            if term.statistical is not None
        }
        return self.expression.subs(subs) if subs else self.expression

    def _ordered_coefficients(self) -> list[tuple[sympy.Expr, AdvTerm]]:
        """(coefficient, term) pairs in the symbols' insertion (hop) order."""
        coeffs = sympy.expand(self.expression).as_coefficients_dict()
        ordered: list[tuple[sympy.Expr, AdvTerm]] = []
        for symbol, term in self.terms.items():
            coeff = coeffs.get(symbol, sympy.Integer(0))
            if coeff != 0:
                ordered.append((coeff, term))
        return ordered

    def render(
        self,
        term_renderer: Optional[Callable[[AdvTerm], str]] = None,
        *,
        mul: str = " * ",
        joiner: str = " + ",
    ) -> str:
        """Render the bound as a string.

        ``term_renderer`` formats a single ``AdvTerm`` (default plain text
        ``Adv^notion(adversary)``); ``mul`` and ``joiner`` join coefficients
        and terms so callers (e.g. the LaTeX exporter) can supply their own
        punctuation.
        """
        if not self.supported:
            return f"(not synthesized: {self.note})"
        render_term = term_renderer or _default_term_renderer
        parts: list[str] = []
        # Opaque cryptographic terms render individually in hop order; concrete
        # statistical terms are summed into a single trailing expression, so
        # repeated helper losses collapse (e.g. two reductions each losing a
        # birthday term read as one q(q-1)/|S|) and vanishing terms drop out.
        statistical_total: sympy.Expr = sympy.Integer(0)
        for coeff, term in self._ordered_coefficients():
            if term.statistical is not None:
                statistical_total += coeff * term.statistical
            elif coeff == 1:
                parts.append(render_term(term))
            else:
                parts.append(f"{coeff}{mul}{render_term(term)}")
        statistical_total = sympy.simplify(statistical_total)
        if statistical_total != 0:
            parts.append(_render_statistical(statistical_total))
        if not parts:
            return "0"
        return joiner.join(parts)


def _default_term_renderer(term: AdvTerm) -> str:
    return f"Adv^{term.notion}({term.adversary})"


def _render_statistical(expr: sympy.Expr) -> str:
    """Render a helper statistical bound as plain FrogLang-style arithmetic."""
    return str(expr).replace("**", "^")


_ARITH_BINOPS: dict[
    frog_ast.BinaryOperators, Callable[[sympy.Expr, sympy.Expr], sympy.Expr]
] = {
    frog_ast.BinaryOperators.ADD: lambda a, b: a + b,
    frog_ast.BinaryOperators.SUBTRACT: lambda a, b: a - b,
    frog_ast.BinaryOperators.MULTIPLY: lambda a, b: a * b,
    frog_ast.BinaryOperators.DIVIDE: lambda a, b: a / b,
    frog_ast.BinaryOperators.EXPONENTIATE: lambda a, b: a**b,
}


def _frog_arith_to_sympy(
    expr: frog_ast.ASTNode,
    on_advantage: Optional[
        Callable[["frog_ast.AdvantageReference"], sympy.Expr]
    ] = None,
) -> sympy.Expr:
    """Convert a numeric FrogLang advantage-bound expression to SymPy.

    Handles the small arithmetic fragment an ``advantage`` clause (or a proof's
    claimed ``bound:``) may use: integer literals, variables, ``+ - * / ^`` and
    unary minus, plus set cardinality ``|X|`` and scalar size/order leaves (a
    field access like ``G.order`` or a group order) -- all rendered as opaque
    positive symbols named by their instantiated form, since the fold does not
    reason about type sizes. A claimed bound additionally contains
    :class:`~proof_frog.frog_ast.AdvantageReference` atoms, resolved by the
    optional ``on_advantage`` callback (absent for helper-game clauses, which
    carry no such atom). Anything outside this fragment raises
    :class:`_UnconvertibleBound`.
    """
    if isinstance(expr, frog_ast.AdvantageReference):
        if on_advantage is None:
            raise _UnconvertibleBound(str(expr))
        return on_advantage(expr)
    if isinstance(expr, frog_ast.Integer):
        return sympy.Integer(expr.num)
    if isinstance(expr, frog_ast.Variable):
        return sympy.Symbol(expr.name, nonnegative=True)
    if isinstance(expr, (frog_ast.FieldAccess, frog_ast.GroupOrder)):
        # A scalar size/order operand introduced by instantiation (e.g. a game
        # parameter `order` bound to `G.order`): treat as an opaque positive
        # magnitude rather than reasoning about its value.
        return sympy.Symbol(str(expr), positive=True)
    if isinstance(expr, frog_ast.UnaryOperation):
        if expr.operator == frog_ast.UnaryOperators.SIZE:
            return sympy.Symbol(f"|{expr.expression}|", positive=True)
        if expr.operator == frog_ast.UnaryOperators.MINUS:
            return -_frog_arith_to_sympy(expr.expression, on_advantage)
        raise _UnconvertibleBound(str(expr))
    if isinstance(expr, frog_ast.BinaryOperation):
        combiner = _ARITH_BINOPS.get(expr.operator)
        if combiner is None:
            raise _UnconvertibleBound(str(expr))
        return combiner(
            _frog_arith_to_sympy(expr.left_expression, on_advantage),
            _frog_arith_to_sympy(expr.right_expression, on_advantage),
        )
    raise _UnconvertibleBound(str(expr))


def count_monotonicity_issue(
    bound: frog_ast.Expression,
) -> Optional[tuple[str, bool]]:
    """Check a declared bound is nondecreasing in each ``count_<Oracle>``.

    Returns ``None`` when the bound is provably nondecreasing in every oracle
    count it uses; otherwise ``(count_name, provably_decreasing)`` where
    ``provably_decreasing`` is True if the bound is provably *decreasing* in that
    count and False if monotonicity merely could not be decided.

    This is a Tier-2 soundness guardrail. The count over-approximation
    (``if``-branches summed, loops multiplied) and the integer ``calls <= N`` pin
    both substitute an *upper bound* for a query count; that preserves the
    advantage *upper* bound only when the declared bound is nondecreasing in the
    count. The test is the discrete forward difference ``f(c+1) - f(c) >= 0``
    over integer counts -- not the continuous derivative, which the birthday
    bound ``c(c-1)/(2|S|)`` fails for real ``c`` in ``(0, 1)`` while being
    nondecreasing over the integers. Set/scalar parameters are treated as
    positive (their real domain).
    """
    try:
        expr = _frog_arith_to_sympy(bound)
    except _UnconvertibleBound:
        return None
    positive = {
        s: sympy.Symbol(str(s), positive=True)
        for s in expr.free_symbols
        if not str(s).startswith("count_")
    }
    expr = expr.subs(positive)
    undecided: Optional[str] = None
    for sym in sorted(
        (s for s in expr.free_symbols if str(s).startswith("count_")), key=str
    ):
        delta = sympy.simplify(expr.subs(sym, sym + 1) - expr)
        nonneg = delta.is_nonnegative
        if nonneg is True:
            continue
        if nonneg is False:
            return str(sym), True
        if undecided is None:
            undecided = str(sym)
    if undecided is not None:
        return undecided, False
    return None


def _challenger_oracle(node: frog_ast.ASTNode) -> Optional[str]:
    """If *node* is a ``challenger.<Oracle>(...)`` call, return the oracle name."""
    if not isinstance(node, frog_ast.FuncCall):
        return None
    func = node.func
    if (
        isinstance(func, frog_ast.FieldAccess)
        and isinstance(func.the_object, frog_ast.Variable)
        and func.the_object.name == "challenger"
    ):
        return func.name
    return None


def _count_calls_in_statements(
    statements: Sequence[frog_ast.Statement], oracle: str
) -> sympy.Expr:
    """Count ``challenger.<oracle>`` invocations across straight-line/loop code.

    A ``for`` loop multiplies its body's count by the loop's (upper-bounded)
    trip count; an ``if``/``else`` sums its branches (a sound upper bound, since
    at most one runs); ordinary statements contribute one per syntactic call
    site. Raises :class:`_UnconvertibleBound` if a construct's multiplicity
    cannot be bounded.
    """
    total: sympy.Expr = sympy.Integer(0)
    for stmt in statements:
        if isinstance(stmt, frog_ast.NumericFor):
            trips = (
                _frog_arith_to_sympy(stmt.end)
                - _frog_arith_to_sympy(stmt.start)
                + sympy.Integer(1)
            )
            total += trips * _count_calls_in_statements(stmt.block.statements, oracle)
        elif isinstance(stmt, frog_ast.GenericFor):
            size = sympy.Symbol(f"|{stmt.over}|", positive=True)
            total += size * _count_calls_in_statements(stmt.block.statements, oracle)
        elif isinstance(stmt, frog_ast.IfStatement):
            for block in stmt.blocks:
                total += _count_calls_in_statements(block.statements, oracle)
        else:
            total += sympy.Integer(_count_calls_in_expression(stmt, oracle))
    return total


def _count_calls_in_expression(node: frog_ast.ASTNode, oracle: str) -> int:
    """Count ``challenger.<oracle>`` call sites in a straight-line statement."""
    count = 0
    stack: list[object] = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, frog_ast.ASTNode):
            if _challenger_oracle(current) == oracle:
                count += 1
            stack.extend(getattr(current, attr) for attr in vars(current))
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return count


def _derive_oracle_count(reduction: frog_ast.Reduction, oracle: str) -> sympy.Expr:
    """The number of ``challenger.<oracle>`` invocations *reduction* makes.

    Each reduction method implements one outer (theorem-game) oracle, so it is
    invoked ``count_<method>`` times (or once, for ``Initialize``); multiply by
    how many times that method calls ``oracle`` and sum. The result is an
    expression in the theorem game's per-oracle query counts.
    """
    total: sympy.Expr = sympy.Integer(0)
    for method in reduction.methods:
        per_call = _count_calls_in_statements(method.block.statements, oracle)
        if per_call == 0:
            continue
        name = method.signature.name
        invocations: sympy.Expr = (
            sympy.Integer(1)
            if name == "Initialize"
            else sympy.Symbol(f"count_{name}", nonnegative=True)
        )
        total += invocations * per_call
    return total


def resolve_statistical(
    notion: frog_ast.ParameterizedGame,
    reduction: Optional[frog_ast.ParameterizedGame],
    definition_lookup: Mapping[str, object],
    max_calls: Optional[frog_ast.Expression],
) -> tuple[Optional[sympy.Expr], str]:
    """Resolve a helper game's declared statistical bound for one hop.

    Returns ``(expr, "")`` when ``notion`` names a game file carrying an
    ``advantage`` clause and it resolves cleanly: game parameters substituted by
    ``notion``'s arguments, and each ``count_<Oracle>`` in the bound replaced by
    how many times the composed ``reduction`` invokes that oracle (an expression
    in the theorem game's per-oracle query counts). A directly-played hop (no
    reduction) leaves the count as a free ``count_<Oracle>`` symbol. When the
    proof declares an integer ``calls <= N`` cap, the surviving query-count
    symbols are pinned to ``N`` (a sound upper bound). Returns ``(None, note)``
    when there is no clause (term stays opaque by design) or it cannot be
    resolved.
    """
    game_file = definition_lookup.get(notion.name)
    if not isinstance(game_file, frog_ast.GameFile) or game_file.advantage is None:
        return None, ""

    # Soundness guardrail: deriving/pinning counts substitutes an upper bound
    # for a query count, which is only sound when the bound is nondecreasing in
    # that count. If we cannot establish that, keep the term opaque.
    issue = count_monotonicity_issue(game_file.advantage.bound)
    if issue is not None:
        name, decreasing = issue
        why = "decreases" if decreasing else "is not provably nondecreasing"
        return None, (
            f"statistical bound for {notion.name} left symbolic: it {why} in"
            f" {name}, so the count over-approximation/pin could be unsound"
        )

    # Substitute the games' set/scalar parameters by the assumption's arguments
    # (so e.g. |S| becomes |BitString<F.in>|); oracle-count names are disjoint.
    replace: frog_ast.ASTMap[frog_ast.ASTNode] = frog_ast.ASTMap(identity=False)
    for param, arg in zip(game_file.games[0].parameters, notion.args):
        replace.set(frog_ast.Variable(param.name), arg)
    substituted = visitors.SubstitutionTransformer(replace).transform(
        game_file.advantage.bound
    )
    try:
        expr = _frog_arith_to_sympy(substituted)
    except _UnconvertibleBound as exc:
        return None, f"statistical bound for {notion.name} left symbolic: {exc}"

    # Replace each helper oracle count by how the reduction drives that oracle.
    count_symbols = [s for s in expr.free_symbols if str(s).startswith("count_")]
    if reduction is not None and count_symbols:
        reduction_def = definition_lookup.get(reduction.name)
        if not isinstance(reduction_def, frog_ast.Reduction):
            return None, (
                f"statistical bound for {notion.name} left symbolic: reduction"
                f" '{reduction.name}' definition unavailable"
            )
        try:
            derived = {
                sym: _derive_oracle_count(reduction_def, str(sym)[len("count_") :])
                for sym in count_symbols
            }
        except _UnconvertibleBound as exc:
            return None, (
                f"statistical bound for {notion.name} left symbolic:"
                f" unbounded query count ({exc})"
            )
        expr = expr.subs(derived)

    # A concrete `calls <= N` cap pins the remaining query counts (sound, since
    # statistical bounds are monotone increasing in the query counts).
    if isinstance(max_calls, frog_ast.Integer):
        expr = expr.subs(
            {
                s: sympy.Integer(max_calls.num)
                for s in expr.free_symbols
                if str(s).startswith("count_")
            }
        )
    return expr, ""


def synthesize_from_hops(hops: Sequence[HopInfo]) -> AdvantageBound:
    """Fold a sequence of hop summaries into an advantage bound.

    Equivalence hops contribute 0. Each assumption/lemma hop contributes one
    advantage term; hops sharing the same notion *and* constructed adversary
    collapse to a single term (so a symmetric two-sided use of one reduction
    reads ``2 * Adv^X(B)``). Distinct reductions are numbered ``B1``, ``B2``,
    ... in order of first appearance.
    """
    expression: sympy.Expr = sympy.Integer(0)
    terms: dict[sympy.Symbol, AdvTerm] = {}
    symbol_by_key: dict[tuple[str, str], sympy.Symbol] = {}
    adversary_by_reduction: dict[str, str] = {}
    hop_terms: list[AdvTerm | None] = []
    notes: list[str] = []

    for hop in hops:
        if hop.kind not in ("by_assumption", "by_lemma") or hop.notion is None:
            hop_terms.append(None)
            continue
        if hop.reduction is not None:
            reduction_key = str(hop.reduction)
            if reduction_key not in adversary_by_reduction:
                adversary_by_reduction[reduction_key] = (
                    f"B{len(adversary_by_reduction) + 1}"
                )
            adversary = adversary_by_reduction[reduction_key]
        else:
            adversary = "A"

        if hop.note and hop.note not in notes:
            notes.append(hop.note)
        key = (str(hop.notion), adversary)
        if key not in symbol_by_key:
            symbol = sympy.Symbol(f"Adv_{len(symbol_by_key)}", nonnegative=True)
            symbol_by_key[key] = symbol
            terms[symbol] = AdvTerm(
                notion=hop.notion,
                adversary=adversary,
                reduction=hop.reduction,
                statistical=hop.statistical,
            )
        expression += symbol_by_key[key]
        hop_terms.append(terms[symbol_by_key[key]])

    return AdvantageBound(
        expression=expression, terms=terms, hop_terms=hop_terms, notes=notes
    )


def side_flip_game(
    a: frog_ast.Step, b: frog_ast.Step
) -> frog_ast.ParameterizedGame | None:
    """Return the shared underlying game if (a, b) is a side-flip, else None.

    A side-flip is the middle hop of the standard four-step reduction pattern:
    both steps have a ``ConcreteGame`` challenger over the same underlying
    ``ParameterizedGame`` (same name and str-equal args), the same reduction
    (str-equal or both None), and differ only in ``which`` (the side). This is
    the structural signature of a hop justified by indistinguishability.
    """
    ca, cb = a.challenger, b.challenger
    if not (
        isinstance(ca, frog_ast.ConcreteGame) and isinstance(cb, frog_ast.ConcreteGame)
    ):
        return None
    if ca.game.name != cb.game.name:
        return None
    if [str(x) for x in ca.game.args] != [str(x) for x in cb.game.args]:
        return None
    if str(a.reduction) != str(b.reduction):
        return None
    if ca.which == cb.which:
        return None
    return ca.game


def synthesize_from_steps(
    steps: Sequence[frog_ast.ProofStep],
    assumed_game_names: set[str],
) -> AdvantageBound:
    """Synthesize the bound from a proof's game-step sequence.

    Used by consumers (e.g. the LaTeX exporter) that have the proof AST but
    not a verified engine run. A hop contributes a loss term only when it is a
    side-flip over an assumed (or lemma) security game; every other hop is
    treated as a perfect equivalence. Inductive proofs are unsupported.
    """
    if any(isinstance(step, frog_ast.Induction) for step in steps):
        return AdvantageBound(
            expression=sympy.Integer(0),
            terms={},
            supported=False,
            note="inductive proofs are not yet supported",
        )
    game_steps = [s for s in steps if isinstance(s, frog_ast.Step)]
    hops: list[HopInfo] = []
    for current, following in zip(game_steps, game_steps[1:]):
        flip = side_flip_game(current, following)
        if flip is not None and flip.name in assumed_game_names:
            hops.append(
                HopInfo(
                    kind="by_assumption",
                    notion=flip,
                    reduction=current.reduction,
                )
            )
        else:
            hops.append(HopInfo(kind="equivalent"))
    return synthesize_from_hops(hops)


def synthesize_from_hop_results(
    hop_results: Sequence["HopResult"],
    definition_lookup: Optional[Mapping[str, object]] = None,
    max_calls: Optional[frog_ast.Expression] = None,
) -> AdvantageBound:
    """Synthesize the bound from a proof engine's ``hop_results``.

    Returns an unsupported bound for inductive proofs (detected by inner hops
    at ``depth > 0`` or an ``induction_rollover`` hop), whose bound is a
    symbolic sum this fold does not yet compute.

    When ``definition_lookup`` (a name -> definition map, e.g. the engine's
    ``definition_namespace``) is supplied, ``by_assumption`` hops whose notion
    names a helper game with a declared ``advantage`` clause are resolved to
    their concrete statistical bound, with per-oracle query counts derived from
    the composed reduction (and pinned by an integer ``max_calls`` cap).
    Assumptions without a clause stay opaque.
    """
    for result in hop_results:
        if result.depth > 0 or result.kind == "induction_rollover":
            return AdvantageBound(
                expression=sympy.Integer(0),
                terms={},
                supported=False,
                note="inductive proofs are not yet supported",
            )

    hops: list[HopInfo] = []
    for result in hop_results:
        statistical: Optional[sympy.Expr] = None
        note = ""
        if definition_lookup is not None and result.justification is not None:
            statistical, note = resolve_statistical(
                result.justification,
                result.reduction,
                definition_lookup,
                max_calls,
            )
        hops.append(
            HopInfo(
                kind=result.kind,
                notion=result.justification,
                reduction=result.reduction,
                statistical=statistical,
                note=note,
            )
        )
    return synthesize_from_hops(hops)


# ---------------------------------------------------------------------------
# Tier 3 -- check a proof's author-claimed ``bound:`` against the synthesized
# bound. The claim is verified iff ``claimed >= synthesized`` over the whole
# nonnegativity region of the advantage/count/parameter symbols, so a
# "verified" claim is a valid (possibly loose) upper bound, never an
# independent proof. The check is one-sided-safe: an omitted or under-weighted
# term leaves a residual that is not provably nonnegative, reported as NOT
# verified rather than silently accepted.
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class BoundCheckResult:
    """The outcome of checking a claimed bound against the synthesized one.

    ``status`` is ``"verified"`` (the claim is a valid upper bound on the
    synthesized bound), ``"not_verified"`` (the claim is provably smaller on
    some point of the nonnegativity region -- ``witness`` gives one), or
    ``"undecided"`` (the solver could not decide, e.g. a non-polynomial
    comparison or unconvertible arithmetic). ``detail`` is a human-readable
    explanation; ``claimed`` / ``synthesized`` are the compared SymPy forms.
    """

    status: str
    detail: str = ""
    claimed: Optional[sympy.Expr] = None
    synthesized: Optional[sympy.Expr] = None
    witness: dict[str, str] = dataclasses.field(default_factory=dict)


def _has_symbolic_exponent(expr: sympy.Expr) -> bool:
    """True if *expr* contains a power with a non-constant exponent.

    Such terms (e.g. ``2 ** lambda``) are transcendental for the real solver,
    which decides only polynomial/rational arithmetic; the checker degrades
    these to ``undecided`` rather than risk an unsound verdict.
    """
    for power in expr.atoms(sympy.Pow):
        if not power.exp.is_number:
            return True
    return False


def _sympy_to_z3(expr: sympy.Expr, z3_vars: Mapping[str, Any]) -> Any:
    """Translate a rational-arithmetic SymPy expression to a Z3 real term.

    Handles the fragment the checker produces: symbols (looked up in
    ``z3_vars``), integer/rational constants, sums, products, and integer
    powers (negative powers become reciprocals). Raises
    :class:`_UnconvertibleBound` for anything else (e.g. a symbolic exponent,
    already screened out before this is called).
    """
    import z3  # pylint: disable=import-outside-toplevel

    if isinstance(expr, sympy.Symbol):
        return z3_vars[str(expr)]
    if isinstance(expr, sympy.Integer):
        return z3.RealVal(int(expr))
    if isinstance(expr, sympy.Rational):
        return z3.RealVal(f"{expr.p}/{expr.q}")
    if isinstance(expr, sympy.Add):
        terms = [_sympy_to_z3(arg, z3_vars) for arg in expr.args]
        result = terms[0]
        for term in terms[1:]:
            result = result + term
        return result
    if isinstance(expr, sympy.Mul):
        factors = [_sympy_to_z3(arg, z3_vars) for arg in expr.args]
        result = factors[0]
        for factor in factors[1:]:
            result = result * factor
        return result
    if isinstance(expr, sympy.Pow):
        base = _sympy_to_z3(expr.base, z3_vars)
        exponent = expr.exp
        if not (isinstance(exponent, sympy.Integer) and exponent != 0):
            raise _UnconvertibleBound(str(expr))
        power = int(exponent)
        magnitude = z3.RealVal(1)
        for _ in range(abs(power)):
            magnitude = magnitude * base
        return magnitude if power > 0 else z3.RealVal(1) / magnitude
    raise _UnconvertibleBound(str(expr))


def _z3_constraints_for(
    symbols: Sequence[sympy.Symbol], z3_vars: Mapping[str, Any]
) -> list[Any]:
    """Domain constraints for the checker's symbols, from SymPy assumptions.

    Cardinalities/orders (``positive``) and unqualified parameters map to
    ``> 0``; advantage and query-count symbols (``nonnegative``) map to
    ``>= 0``. The modeled real region is a superset of the true integer domain
    (counts are nonnegative integers; cardinalities/parameters are >= 1), which
    keeps ``residual >= 0`` over this region sufficient for the integer domain.
    """
    constraints: list[Any] = []
    for sym in symbols:
        var = z3_vars[str(sym)]
        if sym.is_nonnegative and not sym.is_positive:
            constraints.append(var >= 0)
        else:
            constraints.append(var > 0)
    return constraints


def _decide_nonnegative(residual: sympy.Expr) -> tuple[str, dict[str, str]]:
    """Decide whether *residual* is ``>= 0`` over its symbols' domain.

    Returns ``("verified", {})`` when provably nonnegative, ``("not_verified",
    witness)`` when a domain point makes it negative, or ``("undecided", {})``
    when the solver cannot decide (non-polynomial, or ``unknown``/timeout).
    """
    residual = sympy.expand(residual)
    if residual == 0 or residual.is_nonnegative:
        return "verified", {}
    if _has_symbolic_exponent(residual):
        return "undecided", {}

    import z3  # pylint: disable=import-outside-toplevel

    symbols = sorted(residual.free_symbols, key=str)
    z3_vars: dict[str, Any] = {str(sym): z3.Real(str(sym)) for sym in symbols}
    try:
        z3_residual = _sympy_to_z3(residual, z3_vars)
    except _UnconvertibleBound:
        return "undecided", {}

    solver = z3.Solver()
    solver.set("timeout", 5000)
    for constraint in _z3_constraints_for(symbols, z3_vars):
        solver.add(constraint)
    solver.add(z3_residual < 0)
    verdict = solver.check()
    if verdict == z3.unsat:
        return "verified", {}
    if verdict == z3.sat:
        model = solver.model()
        witness = {str(sym): str(model.eval(z3_vars[str(sym)])) for sym in symbols}
        return "not_verified", witness
    return "undecided", {}


def check_claimed_bound(
    claim: frog_ast.Expression, bound: AdvantageBound
) -> BoundCheckResult:
    """Check a proof's claimed ``bound:`` against the synthesized ``bound``.

    Each ``advantage(notion compose reduction)`` reference in the claim is
    matched to the synthesized term with the same notion and reduction (a helper
    term resolves to its statistical expression, mirroring
    :meth:`AdvantageBound.substituted_expression`). The reduction may be written
    as a bare name -- the readable default -- matched by reduction *name*, or
    with its full argument list, matched exactly (falling back to the name). An
    unmatched reference becomes a fresh nonnegative slack symbol (which can only
    enlarge the claim, so it never yields an unsound ``verified``). The claim is
    ``verified`` iff ``claimed - synthesized`` is nonnegative over the whole
    domain.
    """
    if not bound.supported:
        return BoundCheckResult(
            "undecided", f"synthesized bound unavailable: {bound.note}"
        )

    # Index synthesized terms by (notion, full-reduction-str) for an exact match
    # and by (notion, reduction-name) for a bare-name match. A name collision
    # (same reduction name, different args) lets the later term win; the earlier
    # one then stays uncovered in the residual, so the check fails closed
    # (reports not-verified) rather than falsely passing.
    by_full: dict[tuple[str, str | None], tuple[sympy.Symbol, AdvTerm]] = {}
    by_name: dict[tuple[str, str | None], tuple[sympy.Symbol, AdvTerm]] = {}
    for symbol, term in bound.terms.items():
        notion = str(term.notion)
        reduction_name = None if term.reduction is None else term.reduction.name
        by_full[(notion, str(term.reduction) if term.reduction else None)] = (
            symbol,
            term,
        )
        by_name[(notion, reduction_name)] = (symbol, term)
    extra_counter = [0]

    def on_advantage(ref: frog_ast.AdvantageReference) -> sympy.Expr:
        notion = str(ref.notion)
        entry: Optional[tuple[sympy.Symbol, AdvTerm]]
        if ref.reduction is None:
            entry = by_name.get((notion, None))
        elif ref.reduction.args:
            entry = by_full.get((notion, str(ref.reduction))) or by_name.get(
                (notion, ref.reduction.name)
            )
        else:
            entry = by_name.get((notion, ref.reduction.name))
        if entry is not None:
            symbol, term = entry
            return term.statistical if term.statistical is not None else symbol
        # The claim names an adversary the proof does not construct; give it a
        # fresh nonnegative symbol so it only adds slack (never a false pass).
        extra_counter[0] += 1
        return sympy.Symbol(f"AdvUnmatched_{extra_counter[0]}", nonnegative=True)

    try:
        claimed = _frog_arith_to_sympy(claim, on_advantage)
    except _UnconvertibleBound as exc:
        return BoundCheckResult(
            "undecided", f"claimed bound uses unsupported arithmetic: {exc}"
        )

    synthesized = bound.substituted_expression()
    status, witness = _decide_nonnegative(claimed - synthesized)
    detail = {
        "verified": "claim is a valid upper bound on the synthesized bound",
        "not_verified": "claim is smaller than the synthesized bound on some"
        " nonnegative assignment",
        "undecided": "could not decide the claim against the synthesized bound",
    }[status]
    return BoundCheckResult(
        status=status,
        detail=detail,
        claimed=claimed,
        synthesized=synthesized,
        witness=witness,
    )
