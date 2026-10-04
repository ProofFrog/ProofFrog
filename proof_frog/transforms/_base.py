# pylint: disable=duplicate-code
# The fixed-point loop pattern is intentionally similar to proof_engine.py
# (which will be replaced by this module in Phase 2).
"""TransformPass ABC, PipelineContext, and pipeline runner."""

from __future__ import annotations

import dataclasses
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from sympy import Symbol

from .. import frog_ast
from ..frog_ast import SourceOrigin
from ..visitors import NameTypeMap, SearchVisitor

_MAX_FIXED_POINT_ITERATIONS = 200

_NON_SEMANTIC = frog_ast.ASTNode._NON_SEMANTIC  # pylint: disable=protected-access


@dataclass
class NearMiss:
    """A transform that almost fired but didn't, with explanation."""

    transform_name: str
    reason: str
    location: SourceOrigin | None
    suggestion: str | None
    variable: str | None
    method: str | None


def deduplicate_near_misses(misses: list[NearMiss]) -> list[NearMiss]:
    """Deduplicate near-misses by (transform_name, method, variable)."""
    seen: set[tuple[str, str | None, str | None]] = set()
    result: list[NearMiss] = []
    for nm in misses:
        key = (nm.transform_name, nm.method, nm.variable)
        if key not in seen:
            seen.add(key)
            result.append(nm)
    return result


@dataclass
class PipelineContext:
    """Read-only view of engine state needed by transforms."""

    variables: dict[str, Symbol | frog_ast.Expression]
    proof_let_types: NameTypeMap
    proof_namespace: frog_ast.Namespace
    subsets_pairs: list[tuple[frog_ast.Type, frog_ast.Type]]
    equality_pairs: set[tuple[str, str]] = dataclasses.field(default_factory=set)
    sort_game_fn: Optional[Callable[[frog_ast.Game], frog_ast.Game]] = None
    max_calls: Optional[int] = None
    sampled_let_names: set[str] = dataclasses.field(default_factory=set)
    near_misses: list[NearMiss] = dataclasses.field(default_factory=list)
    requirements: list[frog_ast.StructuralRequirement] = dataclasses.field(
        default_factory=list
    )
    # Fields created by a canonicalization pass specifically to serve as
    # the canonical container for some expression (e.g. ``<base> ^ X`` by
    # ``HoistGroupExpToInitialize``). ``InlineSingleUseField`` skips
    # these: inlining them would re-expose the pattern and the producing
    # pass would re-create the field on the next fixed-point iteration,
    # never converging. Producers add names here when they create the
    # field; consumers (currently only ``InlineSingleUseField``) consult
    # the set.
    pinned_fields: set[str] = dataclasses.field(default_factory=set)

    def has_prime_order_requirement(self, group_expr: frog_ast.Expression) -> bool:
        """True if the proof declares ``<group_expr>.order is prime``.

        Accepts either the ``FieldAccess(the_object=<group_expr>, name='order')``
        form or the canonical ``GroupOrder(<group_expr>)`` form.
        """
        for req in self.requirements:
            if req.kind != "prime":
                continue
            target = req.target
            if (
                isinstance(target, frog_ast.FieldAccess)
                and target.name == "order"
                and target.the_object == group_expr
            ):
                return True
            if isinstance(target, frog_ast.GroupOrder) and target.group == group_expr:
                return True
        return False


def _lookup_primitive_method(
    func: frog_ast.Expression,
    proof_namespace: frog_ast.Namespace,
) -> frog_ast.MethodSignature | None:
    """Look up the MethodSignature for a call to a primitive method, or None."""
    if not isinstance(func, frog_ast.FieldAccess):
        return None
    if not isinstance(func.the_object, frog_ast.Variable):
        return None
    obj = proof_namespace.get(func.the_object.name)
    if not isinstance(obj, frog_ast.Primitive):
        return None
    for method in obj.methods:
        if method.name == func.name:
            return method
    return None


def has_nondeterministic_call(
    expr: frog_ast.Expression,
    proof_namespace: frog_ast.Namespace,
    proof_let_types: Optional[NameTypeMap] = None,
    shadowed_names: Optional[set[str]] = None,
) -> bool:
    """Return True if *expr* contains a FuncCall to a non-deterministic method.

    Calls to primitive methods annotated ``deterministic`` and calls to
    ``Function<D, R>`` variables are treated as pure for inlining and CSE
    purposes.  Any other FuncCall (including calls to scheme methods, game
    methods, or unannotated primitive methods) is considered non-deterministic.

    *shadowed_names* (F-267): names that are locally bound (declared) in the
    method whose expression this is. A proof-level ``let: Function<D,R> H;`` is
    a known deterministic function, but a same-named METHOD-LOCAL declaration
    ``Function<D,R> H;`` shadows it -- and an unassigned local Function is an
    uninitialized value, so calling it is an observable undefined read, not the
    deterministic let-function. When a callee name is in *shadowed_names* the
    let-``Function`` classification is NOT applied (the call is treated as
    potentially non-deterministic).
    """

    def _is_nondeterministic_call(node: frog_ast.ASTNode) -> bool:
        if not isinstance(node, frog_ast.FuncCall):
            return False
        # Primitive methods annotated ``deterministic`` are pure
        m = _lookup_primitive_method(node.func, proof_namespace)
        if m is not None:
            return not m.deterministic
        # Function<D, R> calls are always deterministic (same input → same
        # output) -- UNLESS the name is shadowed by a method-local binding.
        if (
            proof_let_types is not None
            and isinstance(node.func, frog_ast.Variable)
            and (shadowed_names is None or node.func.name not in shadowed_names)
        ):
            var_type = proof_let_types.get(node.func.name)
            if isinstance(var_type, frog_ast.FunctionType):
                return False
        return True

    return SearchVisitor(_is_nondeterministic_call).visit(expr) is not None


class TransformPass(ABC):
    """A single canonicalization pass that can be applied to a Game AST."""

    name: str

    @abstractmethod
    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        """Apply this transformation pass. Return the (possibly new) game AST."""


def same_structure(left: object, right: object) -> bool:
    """True if two AST values are the same tree, node class for node class.

    Stricter than ``ASTNode.__eq__``: every node must have exactly the same
    class as its counterpart (no ``ProductType``/``Tuple`` cross-equality, no
    subclass overrides), and every scalar the same type and value. Source
    positions are ignored, as in ``__eq__``. Two values for which this holds
    are interchangeable as the input of any pass.
    """
    if left is right:
        return True
    if type(left) is not type(right):
        return False
    if isinstance(left, frog_ast.ASTNode):
        assert isinstance(right, frog_ast.ASTNode)
        left_attrs = vars(left)
        right_attrs = vars(right)
        if len(left_attrs) != len(right_attrs):
            return False
        for name, value in left_attrs.items():
            if name in _NON_SEMANTIC:
                continue
            if name not in right_attrs or not same_structure(value, right_attrs[name]):
                return False
        return True
    if isinstance(left, (list, tuple)):
        assert isinstance(right, (list, tuple))
        return len(left) == len(right) and all(
            same_structure(a, b) for a, b in zip(left, right)
        )
    return bool(left == right)


def run_pipeline(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    game: frog_ast.Game,
    pipeline: list[TransformPass],
    ctx: PipelineContext,
    verbose: bool = False,
    max_iterations: int = _MAX_FIXED_POINT_ITERATIONS,
    verbose_lines: list[str] | None = None,
) -> frog_ast.Game:
    """Run transform passes in a fixed-point loop until convergence.

    If *verbose_lines* is provided, verbose output is appended there instead
    of being printed directly.  This allows callers (e.g. parallel workers)
    to collect output for later ordered printing.

    A pass is not re-applied to a game it has already left unchanged: once
    nothing fires any more, the iteration that confirms the fixed point would
    otherwise re-run every pass on the very game each of them just declined.
    This relies on a pass's output being a function of the game and of
    ``ctx``, whose only state that changes during a run is ``pinned_fields``;
    a skip therefore also requires ``pinned_fields`` to be what it was when
    the pass declined. Near-misses are unaffected: the declining application
    already recorded them, and they are deduplicated.

    "Left unchanged" means :func:`same_structure`, NOT ``==``: AST equality
    is deliberately loose in places (a ``ProductType`` equals a ``Tuple``
    with the same elements), and a pass such as ``Normalize Product-Literal
    Tuples`` makes exactly such a change, which later passes depend on.
    """
    # declined[i]: the game object pass i last left unchanged, with the
    # pinned fields it saw. Holding the game keeps the identity test valid.
    declined: list[tuple[frog_ast.Game, frozenset[str]] | None] = [None] * len(pipeline)
    for _ in range(max_iterations):
        new_game = game
        for index, pass_ in enumerate(pipeline):
            last = declined[index]
            if (
                last is not None
                and last[0] is new_game
                and last[1] == ctx.pinned_fields
            ):
                continue
            pinned_before = frozenset(ctx.pinned_fields)
            result = pass_.apply(new_game, ctx)
            if result is new_game or same_structure(result, new_game):
                # Keep the input object, so that every later pass (and the
                # next iteration) can recognise an unchanged game by identity.
                declined[index] = (
                    (new_game, pinned_before)
                    if pinned_before == ctx.pinned_fields
                    else None
                )
                continue
            declined[index] = None
            if verbose:
                msg1 = f"APPLIED {pass_.name}"
                msg2 = str(result)
                if verbose_lines is not None:
                    verbose_lines.append(msg1)
                    verbose_lines.append(msg2)
                else:
                    print(msg1)
                    print(msg2)
            new_game = result
        if new_game == game:
            break
        game = new_game
    else:
        warnings.warn(
            "Canonicalization did not converge within " f"{max_iterations} iterations",
            stacklevel=3,
        )
    return game


def run_standardization(
    game: frog_ast.Game,
    pipeline: list[TransformPass],
    ctx: PipelineContext,
) -> frog_ast.Game:
    """Run standardization passes once (no fixed-point loop)."""
    for pass_ in pipeline:
        game = pass_.apply(game, ctx)
    return game


# ---------------------------------------------------------------------------
# Traced / diagnostic pipeline runners
# ---------------------------------------------------------------------------


@dataclass
class IterationTrace:
    """Record of one fixed-point iteration."""

    iteration: int
    transforms_applied: list[str]


@dataclass
class PipelineTrace:
    """Full trace of a pipeline run."""

    iterations: list[IterationTrace]
    converged: bool


def run_pipeline_with_trace(
    game: frog_ast.Game,
    pipeline: list[TransformPass],
    ctx: PipelineContext,
    max_iterations: int = _MAX_FIXED_POINT_ITERATIONS,
) -> tuple[frog_ast.Game, PipelineTrace]:
    """Run transform passes in a fixed-point loop, recording which fired."""
    iterations: list[IterationTrace] = []
    converged = False
    for iteration in range(max_iterations):
        transforms_applied: list[str] = []
        new_game = game
        for pass_ in pipeline:
            before = new_game
            new_game = pass_.apply(new_game, ctx)
            if new_game != before:
                transforms_applied.append(pass_.name)
        if new_game == game:
            converged = True
            break
        iterations.append(
            IterationTrace(
                iteration=iteration + 1, transforms_applied=transforms_applied
            )
        )
        game = new_game
    if not converged:
        warnings.warn(
            "Canonicalization did not converge within " f"{max_iterations} iterations",
            stacklevel=3,
        )
    return game, PipelineTrace(iterations=iterations, converged=converged)


def run_pipeline_until(
    game: frog_ast.Game,
    core_pipeline: list[TransformPass],
    std_pipeline: list[TransformPass],
    ctx: PipelineContext,
    transform_name: str,
) -> tuple[frog_ast.Game, bool, list[str]]:
    """Apply transforms up to and including *transform_name* (first iteration).

    Returns ``(game_after, transform_changed_ast, available_names)``.
    """
    available_names = [p.name for p in core_pipeline] + [p.name for p in std_pipeline]

    if transform_name not in available_names:
        return game, False, available_names

    for pass_ in core_pipeline:
        before = game
        game = pass_.apply(game, ctx)
        if pass_.name == transform_name:
            return game, game != before, available_names

    for pass_ in std_pipeline:
        before = game
        game = pass_.apply(game, ctx)
        if pass_.name == transform_name:
            return game, game != before, available_names

    return game, False, available_names


def method_bound_names(method: frog_ast.Method) -> set[str]:
    """The set of names *method* binds locally, i.e. introduces a NEW binding
    for: signature parameters, typed local declarations / samples
    (``T x = ...`` / ``T x <- ...``), and ``for`` binders.

    A plain write to an existing name (``x = ...`` / ``M[k] <- ...`` with no
    declared type) is NOT a binding -- it mutates the field/local already in
    scope and does not create a capturing shadow. A name in this set, when it
    occurs inside *method*, refers to the local binding rather than any
    same-named game field/parameter, so a name-based mover that trusts
    field/param membership must treat it as shadowed (audit RC4:
    F-173/F-178/F-190/F-228)."""
    names = {p.name for p in method.signature.parameters}

    def _collect(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, frog_ast.NumericFor):
            names.add(n.name)
        elif isinstance(n, frog_ast.GenericFor):
            names.add(n.var_name)
        elif (
            isinstance(n, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample))
            and getattr(n, "the_type", None) is not None
            and isinstance(n.var, frog_ast.Variable)
        ):
            names.add(n.var.name)
        return False

    SearchVisitor(_collect).visit(method.block)
    return names


def may_return_before(statements: Sequence[frog_ast.Statement], index: int) -> bool:
    """True if a statement of *statements* before *index* contains a
    ``return`` (at any depth), i.e. the statement at *index* may be skipped.

    A pass that trusts a top-level Initialize definition ``f = e`` at
    *index* (reading ``f`` elsewhere as ``e``) must check this: an earlier
    ``if (c) { return ...; }`` ends Initialize with ``f`` still at its
    initial value (audit F-349)."""

    def _is_return(node: frog_ast.ASTNode) -> bool:
        return isinstance(node, frog_ast.ReturnStatement)

    return any(
        SearchVisitor(_is_return).visit(stmt) is not None for stmt in statements[:index]
    )
