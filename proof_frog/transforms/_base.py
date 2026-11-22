# pylint: disable=duplicate-code
# The fixed-point loop pattern is intentionally similar to proof_engine.py
# (which will be replaced by this module in Phase 2).
"""TransformPass ABC, PipelineContext, and pipeline runner."""

from __future__ import annotations

import dataclasses
import warnings
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Optional, Sequence

from sympy import Symbol

from .. import frog_ast
from ..frog_ast import SourceOrigin
from ..visitors import (
    NameTypeMap,
    SearchVisitor,
    lvalue_base_name,
    referenced_variable_names,
    type_position_names,
    walk_children,
)

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
    # The engine's ``sort_game``: sorts and prunes each method of a game,
    # appending ``(method name, draw)`` for every draw it keeps only because
    # its domain may be empty to the list it is given.
    sort_game_fn: Optional[
        Callable[
            [frog_ast.Game, Optional[list[tuple[str, frog_ast.Statement]]]],
            frog_ast.Game,
        ]
    ] = None
    max_calls: Optional[int] = None
    sampled_let_names: set[str] = dataclasses.field(default_factory=set)
    # Each sampled ``let:`` function that a primitive instantiation in the
    # ``let:`` block receives (directly, or inside another entry it is
    # given), mapped to that entry's name. The primitive's methods are
    # opaque and may query the function where no call shows it, so a pass
    # that must know every query of a random function does not take it for
    # one (F-387).
    primitive_held_functions: dict[str, str] = dataclasses.field(default_factory=dict)
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
    ``Function<D,R> H;`` shadows it -- and an unassigned local Function holds
    its type's unspecified default, not the let-function. When a callee name
    is in *shadowed_names* the let-``Function`` classification is NOT applied
    (the call is treated as potentially non-deterministic).
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


def calls_are_deterministic(
    expr: frog_ast.Expression,
    ctx_namespace: frog_ast.Namespace,
    let_types: Optional[NameTypeMap],
    type_map: Optional[NameTypeMap],
    shadowed: set[str],
) -> bool:
    """True if every call in *expr* returns the same value for the same
    arguments: a ``deterministic`` primitive method, a let-bound ``Function``
    (unless a local shadows it), or a variable of ``Function`` type in
    *type_map* (a game field or a local holding a function).

    A ``Function`` held in a game field may be reassigned between two calls,
    so a caller that moves or duplicates such a call must also check that
    nothing in between writes the function's name (its name is among the
    names the expression references, which the passes below check).
    """

    def nondeterministic(node: frog_ast.ASTNode) -> bool:
        if not isinstance(node, frog_ast.FuncCall):
            return False
        signature = _lookup_primitive_method(node.func, ctx_namespace)
        if signature is not None:
            return not signature.deterministic
        if isinstance(node.func, frog_ast.Variable):
            name = node.func.name
            if (
                name not in shadowed
                and let_types is not None
                and isinstance(let_types.get(name), frog_ast.FunctionType)
            ):
                return False
            if type_map is not None and isinstance(
                type_map.get(name), frog_ast.FunctionType
            ):
                return False
        return True

    return SearchVisitor(nondeterministic).visit(expr) is None


def bound_names(method: frog_ast.Method) -> set[str]:
    """:func:`method_bound_names` plus the names of bare declarations
    ``T x;``, which also bind a local that shadows a same-named field."""
    names = method_bound_names(method)

    def _collect(node: frog_ast.ASTNode) -> bool:
        if isinstance(node, frog_ast.VariableDeclaration):
            names.add(node.name)
        return False

    SearchVisitor(_collect).visit(method.block)
    return names


def game_names(game: frog_ast.Game) -> set[str]:
    """Every name *game* binds or mentions: its parameters and fields, each
    method's :func:`bound_names`, and every variable it references (type
    positions included).

    A name a pass adds to *game* (a new field or local) must be none of
    these: otherwise the new binding captures reads of the existing one, or
    a declaration of the existing name captures reads of the new one."""
    names = {param.name for param in game.parameters}
    names |= {field.name for field in game.fields}
    names |= referenced_variable_names(game)
    for method in game.methods:
        names |= bound_names(method)
    return names


def fresh_name(base: str, taken: set[str]) -> str:
    """*base* if it is not in *taken*, else the first ``base@fresh<k>``
    (k = 1, 2, ...) that is not. The name returned is added to *taken*, so
    successive calls with the same set return distinct names."""
    name, k = base, 0
    while name in taken:
        k += 1
        name = f"{base}@fresh{k}"
    taken.add(name)
    return name


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


def _count_type_positions(node: Any, in_type: bool, counts: Counter[str]) -> None:
    """Add to *counts* one for each ``Variable`` in a type position within
    *node*, a length, modulus or size expression included."""
    if isinstance(node, frog_ast.Variable):
        if in_type:
            counts[node.name] += 1
        return
    if isinstance(node, (list, tuple)):
        for item in node:
            _count_type_positions(item, in_type, counts)
        return
    if not isinstance(node, frog_ast.ASTNode):
        return
    for _, child, child_in_type in walk_children(node, in_type):
        _count_type_positions(child, child_in_type, counts)


def _statements(block: frog_ast.Block) -> Iterator[frog_ast.Statement]:
    """Every statement in *block*, at any depth (inside nested blocks, ``if``
    branches and loop bodies); expressions are not entered, since no
    expression declares or writes a variable."""
    for statement in block.statements:
        yield statement
        if isinstance(statement, frog_ast.Block):
            yield from _statements(statement)
        elif isinstance(statement, frog_ast.IfStatement):
            for inner in statement.blocks:
                yield from _statements(inner)
        elif isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
            yield from _statements(statement.block)


def _scan_types_and_changes(
    game: frog_ast.Game,
) -> tuple[Counter[str], set[str]]:
    """One walk of *game*: the count of each name in a type position (the
    declared type of a field, parameter, local or ``for`` binder, a return
    type, a draw's type and domain; a length, modulus or size inside one
    included), and the names :func:`changing_names` describes. Only
    statements are walked, and only the types in them entered, so the walk
    stays cheap enough to run on every pass output (`apply_pass`)."""
    counts: Counter[str] = Counter()
    changed: set[str] = set()

    def _count(node: Optional[frog_ast.ASTNode]) -> None:
        if node is not None:
            _count_type_positions(node, True, counts)

    def _target(target: frog_ast.ASTNode) -> None:
        if isinstance(target, frog_ast.Tuple):
            for value in target.values:
                _target(value)
            return
        base = lvalue_base_name(target)
        if base is not None:
            changed.add(base)

    for field in game.fields:
        _count(field.type)
    for parameter in game.parameters:
        _count(parameter.type)
    for method in game.methods:
        signature = method.signature
        _count(signature.return_type)
        for parameter in signature.parameters:
            _count(parameter.type)
        bindings: Counter[str] = Counter(p.name for p in signature.parameters)
        for inner in _statements(method.block):
            if isinstance(
                inner, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ):
                _count(inner.the_type)
                if inner.the_type is not None and isinstance(
                    inner.var, frog_ast.Variable
                ):
                    bindings[inner.var.name] += 1
                else:
                    _target(inner.var)
                if isinstance(inner, (frog_ast.Sample, frog_ast.UniqueSample)):
                    _count(inner.sampled_from)
                if (
                    isinstance(inner, frog_ast.UniqueSample)
                    and inner.surface_form == "uniq"
                ):
                    changed.update(referenced_variable_names(inner.unique_set))
            elif isinstance(inner, frog_ast.VariableDeclaration):
                _count(inner.type)
                bindings[inner.name] += 1
            elif isinstance(inner, frog_ast.NumericFor):
                bindings[inner.name] += 1
            elif isinstance(inner, frog_ast.GenericFor):
                _count(inner.var_type)
                bindings[inner.var_name] += 1
            elif isinstance(inner, frog_ast.DestructuringBinding):
                bindings.update(inner.names)
        changed.update(name for name, count in bindings.items() if count > 1)
    return counts, changed


def changing_names(game: frog_ast.Game) -> set[str]:
    """Names whose value may change while the game runs: a name written
    other than by its declaration (an assignment or draw without a type, an
    element write, a ``<-uniq`` insertion), or bound more than once in one
    method (two typed declarations, a declaration and a parameter or
    ``for`` binder). A field, a game parameter and a local bound once and
    never written keep their value."""
    return _scan_types_and_changes(game)[1]


def changing_type_name_counts(game: frog_ast.Game) -> Counter[str]:
    """For each name that occurs in a type position of *game* (a modulus,
    length or size included) and whose value may change while the game runs
    (:func:`changing_names`), the number of such occurrences.

    The passes compare types by their text and read a store into a declared
    variable as reading nothing of the variable's type, so a type must name
    only values that stay fixed (F-420; F-367's rule for source files)."""
    counts, changing = _scan_types_and_changes(game)
    return Counter({name: count for name, count in counts.items() if name in changing})


def type_snapshot_names(game: frog_ast.Game) -> frozenset[str]:
    """Each name bound by a typed ``T v = e;`` in *game* that a type of the
    game names (a modulus, length or size included) and whose value ``e``
    reads a name the game changes (:func:`changing_names`).

    The method inliner binds a callee parameter read in a type this way
    (F-420); forwarding ``e`` into the type would name a changing variable
    there, so the forwarding passes keep these variables."""
    in_types = type_position_names(game)
    if not in_types:
        return frozenset()
    changing = changing_names(game)
    names: set[str] = set()

    def _visit(inner: frog_ast.ASTNode) -> bool:
        if (
            isinstance(inner, frog_ast.Assignment)
            and inner.the_type is not None
            and isinstance(inner.var, frog_ast.Variable)
            and inner.var.name in in_types
            and referenced_variable_names(inner.value) & changing
        ):
            names.add(inner.var.name)
        return False

    SearchVisitor(_visit).visit(game)
    return frozenset(names)


def note_type_snapshot(
    ctx: Optional[PipelineContext],
    transform_name: str,
    name: str,
    location: Optional[SourceOrigin] = None,
) -> None:
    """Record that *transform_name* declined to forward *name*, a variable a
    type names whose value reads a variable the game changes."""
    if ctx is None:
        return
    ctx.near_misses.append(
        NearMiss(
            transform_name=transform_name,
            reason=(
                f"Cannot forward '{name}': a type names it, and its value reads "
                f"a variable the game changes; a type must name only values "
                f"that stay fixed"
            ),
            location=location,
            suggestion=None,
            variable=name,
            method=None,
        )
    )


def apply_pass(
    pass_: "TransformPass", game: frog_ast.Game, ctx: PipelineContext
) -> frog_ast.Game:
    """Apply *pass_* to *game*, refusing an output that names a changing
    variable in more type positions than *game* does.

    Every pipeline runner applies passes through this function. A forwarding
    pass that substitutes ``c`` for ``k`` in ``Int k = c; ModInt<k> v;`` when
    the game writes ``c`` would let later passes move the write in front of a
    store into ``v`` or merge the declaration with that store after the
    write (F-420): the refused output is dropped, the game is kept, and a
    near miss names the pass and the variable."""
    result = pass_.apply(game, ctx)
    if result is game:
        return game
    after = changing_type_name_counts(result)
    if not after:
        return result
    before = changing_type_name_counts(game)
    grown = sorted(name for name, count in after.items() if count > before[name])
    if not grown:
        return result
    ctx.near_misses.append(
        NearMiss(
            transform_name=pass_.name,
            reason=(
                f"{pass_.name} would name {', '.join(repr(n) for n in grown)}, "
                "a variable the game changes, in a type; a type must name "
                "only values that stay fixed"
            ),
            location=None,
            suggestion=None,
            variable=grown[0],
            method=None,
        )
    )
    return game


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
            result = apply_pass(pass_, new_game, ctx)
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
        game = apply_pass(pass_, game, ctx)
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
            new_game = apply_pass(pass_, new_game, ctx)
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
        game = apply_pass(pass_, game, ctx)
        if pass_.name == transform_name:
            return game, game != before, available_names

    for pass_ in std_pipeline:
        before = game
        game = apply_pass(pass_, game, ctx)
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
