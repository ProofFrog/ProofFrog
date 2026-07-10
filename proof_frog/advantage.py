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
from typing import TYPE_CHECKING, Callable, Mapping, Optional, Sequence

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


def _frog_arith_to_sympy(expr: frog_ast.ASTNode) -> sympy.Expr:
    """Convert a numeric FrogLang advantage-bound expression to SymPy.

    Handles the small arithmetic fragment an ``advantage`` clause may use:
    integer literals, variables, ``+ - * / ^`` and unary minus, plus set
    cardinality ``|X|`` and scalar size/order leaves (a field access like
    ``G.order`` or a group order) -- all rendered as opaque positive symbols
    named by their instantiated form, since the fold does not reason about type
    sizes. Anything outside this fragment raises :class:`_UnconvertibleBound`.
    """
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
            return -_frog_arith_to_sympy(expr.expression)
        raise _UnconvertibleBound(str(expr))
    if isinstance(expr, frog_ast.BinaryOperation):
        combiner = _ARITH_BINOPS.get(expr.operator)
        if combiner is None:
            raise _UnconvertibleBound(str(expr))
        return combiner(
            _frog_arith_to_sympy(expr.left_expression),
            _frog_arith_to_sympy(expr.right_expression),
        )
    raise _UnconvertibleBound(str(expr))


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
                notion=hop.notion, adversary=adversary, statistical=hop.statistical
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
