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
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Callable, Optional, Sequence

import sympy

from . import frog_ast

if TYPE_CHECKING:  # avoid an import cycle with proof_engine at runtime
    from .proof_engine import HopResult


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


@dataclasses.dataclass
class HopInfo:
    """The bound-relevant summary of a single proof hop.

    ``kind`` is ``"equivalent"`` (contributes 0), ``"by_assumption"``, or
    ``"by_lemma"``. For the latter two, ``notion`` is the licensing security
    game and ``reduction`` the constructed adversary composed with it (or
    ``None`` when the notion is played directly against the adversary).
    """

    kind: str
    notion: frog_ast.ParameterizedGame | None = None
    reduction: frog_ast.ParameterizedGame | None = None


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

    def is_trivial(self) -> bool:
        """True when the proof establishes a zero (perfect) advantage bound."""
        return self.supported and sympy.expand(self.expression) == 0

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
        for coeff, term in self._ordered_coefficients():
            rendered = render_term(term)
            if coeff == 1:
                parts.append(rendered)
            else:
                parts.append(f"{coeff}{mul}{rendered}")
        if not parts:
            return "0"
        return joiner.join(parts)


def _default_term_renderer(term: AdvTerm) -> str:
    return f"Adv^{term.notion}({term.adversary})"


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

        key = (str(hop.notion), adversary)
        if key not in symbol_by_key:
            symbol = sympy.Symbol(f"Adv_{len(symbol_by_key)}", nonnegative=True)
            symbol_by_key[key] = symbol
            terms[symbol] = AdvTerm(notion=hop.notion, adversary=adversary)
        expression += symbol_by_key[key]
        hop_terms.append(terms[symbol_by_key[key]])

    return AdvantageBound(expression=expression, terms=terms, hop_terms=hop_terms)


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
) -> AdvantageBound:
    """Synthesize the bound from a proof engine's ``hop_results``.

    Returns an unsupported bound for inductive proofs (detected by inner hops
    at ``depth > 0`` or an ``induction_rollover`` hop), whose bound is a
    symbolic sum this fold does not yet compute.
    """
    for result in hop_results:
        if result.depth > 0 or result.kind == "induction_rollover":
            return AdvantageBound(
                expression=sympy.Integer(0),
                terms={},
                supported=False,
                note="inductive proofs are not yet supported",
            )

    hops = [
        HopInfo(
            kind=result.kind,
            notion=result.justification,
            reduction=result.reduction,
        )
        for result in hop_results
    ]
    return synthesize_from_hops(hops)
