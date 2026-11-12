"""Passes that use relations between a game's fields across oracle calls.

Canonicalization otherwise reasons about one method at a time, so a relation
that holds between two fields *between* oracle calls (a public key that is
always ``g ^ sk``) is invisible to it. These passes establish such relations
and use them to remove the redundant field, so that two games which keep the
same state in different ways reach the same canonical form.

* :class:`FieldInvariantElimination` -- a field ``a`` that, after
  ``Initialize`` and after every oracle call, equals an expression ``E`` over
  the other fields is removed: each method starts from a local ``a = E``.
  The only ``E`` tried is ``a``'s value at the end of an ``Initialize`` with
  one path, over the fields that hold its drawn values. The relation is
  *proved* before it is used (see below).
* :class:`GeneratorPowerFieldToExponent` -- a group-element field that is
  only ever set to ``g ^ x`` or multiplied by ``g ^ x`` is replaced by a
  ``ModInt`` field holding its exponent, by construction.

Proving the relation (:func:`_preserves`). For ``Initialize`` and for every
oracle that writes ``a`` or a field of ``E``, the method is executed
symbolically along every path: fields start as fresh names (with ``a`` set to
``E`` of those names, the inductive hypothesis, except in ``Initialize``),
parameters and sampled values are fresh names, and every call that is not
known to be deterministic is replaced by a fresh name. At each exit the value
of ``a`` and the value of ``E`` over the final fields must have equal normal
forms (:mod:`._algebra`): equal for *every* value of the fresh names, hence
on every execution. Boolean facts taken from branch conditions prune paths
that cannot run; every other condition is ignored, and loops havoc what they
write, so the check over-approximates the executions. Induction over oracle
calls then gives ``a == E`` at every call boundary, and removing ``a`` is an
exact rewrite.

Removing a field (these passes and :class:`OffsetFusion`). Each pass
rewrites the reads of the removed field that it understands, then
:func:`_unbound_reference` checks that the new game names the field nowhere
else without a binding in scope: not in another field's type or initializer,
not in a signature, and not in a type, sampled-from set or literal length in
a method body outside the locals the pass declares. Otherwise the pass keeps
the field (with a near miss), since such a name would now refer to something
else, such as a proof ``let:`` entry of the same name.
"""

from __future__ import annotations

import copy
import itertools
from collections import OrderedDict
from dataclasses import dataclass, field as dataclass_field
from typing import Callable, Optional

from .. import frog_ast
from ..visitors import (
    NameTypeMap,
    SearchVisitor,
    build_method_type_map,
    expression_type,
    lvalue_base_name,
    reassigns_or_rebinds,
    store_may_change_value,
)
from ._algebra import GroupForm, Normalizer, infer_type, is_order_of
from ._base import (
    NearMiss,
    PipelineContext,
    TransformPass,
    _lookup_primitive_method,
    bound_names,
    calls_are_deterministic,
    fresh_name,
    game_names,
    may_return_before,
)
from ._definedness import note_redeclared_name, redeclared_names

_SYMBOL_PREFIX = "inv@"
_MAX_PATHS = 256
_MAX_CANDIDATES = 6
_CACHE_SIZE = 512


class _Unsupported(Exception):
    """The symbolic executor met a construct it does not model."""


# ---------------------------------------------------------------------------
# Expression substitution
# ---------------------------------------------------------------------------


def _map_expression(
    expr: frog_ast.Expression,
    on_variable: Callable[[frog_ast.Variable], frog_ast.Expression],
    on_call: Optional[Callable[[frog_ast.FuncCall], frog_ast.Expression]] = None,
) -> frog_ast.Expression:
    """Rebuild *expr* bottom-up, mapping variables (and optionally calls).

    Raises :class:`_Unsupported` on a node kind it does not know, so a
    caller never silently skips a subexpression.
    """

    def walk(node: frog_ast.Expression) -> frog_ast.Expression:
        # pylint: disable=too-many-return-statements
        if isinstance(node, frog_ast.Variable):
            return on_variable(node)
        if isinstance(
            node,
            (
                frog_ast.Integer,
                frog_ast.Boolean,
                frog_ast.NoneExpression,
                frog_ast.BinaryNum,
            ),
        ):
            return copy.deepcopy(node)
        # The length of ``0^n`` / ``1^n`` and the group of ``G.generator`` /
        # ``G.order`` are expressions too: ``1^c`` before and after ``c = c +
        # 1`` are different values.
        if isinstance(node, frog_ast.BitStringLiteral):
            return frog_ast.BitStringLiteral(node.bit, walk(node.length))
        if isinstance(node, frog_ast.GroupGenerator):
            return frog_ast.GroupGenerator(walk(node.group))
        if isinstance(node, frog_ast.GroupOrder):
            return frog_ast.GroupOrder(walk(node.group))
        if isinstance(node, frog_ast.FuncCall):
            call = frog_ast.FuncCall(walk(node.func), [walk(a) for a in node.args])
            return on_call(call) if on_call is not None else call
        if isinstance(node, frog_ast.BinaryOperation):
            return frog_ast.BinaryOperation(
                node.operator,
                walk(node.left_expression),
                walk(node.right_expression),
            )
        if isinstance(node, frog_ast.UnaryOperation):
            return frog_ast.UnaryOperation(node.operator, walk(node.expression))
        if isinstance(node, frog_ast.Tuple):
            return frog_ast.Tuple([walk(v) for v in node.values])
        if isinstance(node, frog_ast.Set):
            return frog_ast.Set([walk(e) for e in node.elements])
        if isinstance(node, frog_ast.ArrayAccess):
            return frog_ast.ArrayAccess(walk(node.the_array), walk(node.index))
        if isinstance(node, frog_ast.Slice):
            return frog_ast.Slice(
                walk(node.the_array), walk(node.start), walk(node.end)
            )
        if isinstance(node, frog_ast.FieldAccess):
            return frog_ast.FieldAccess(walk(node.the_object), node.name)
        raise _Unsupported(type(node).__name__)

    return walk(expr)


def _replace_names(
    expr: frog_ast.Expression, mapping: dict[str, frog_ast.Expression]
) -> frog_ast.Expression:
    """Replace each value reference ``Variable(n)`` with ``mapping[n]``."""

    def on_variable(var: frog_ast.Variable) -> frog_ast.Expression:
        if var.name in mapping:
            return copy.deepcopy(mapping[var.name])
        return copy.deepcopy(var)

    return _map_expression(expr, on_variable)


def _free_names(expr: frog_ast.Expression) -> set[str]:
    names: set[str] = set()

    def visit(node: frog_ast.ASTNode) -> bool:
        if isinstance(node, frog_ast.Variable):
            names.add(node.name)
        return False

    SearchVisitor(visit).visit(expr)
    return names


def _mentions(node: frog_ast.ASTNode, name: str) -> bool:
    return (
        SearchVisitor(
            lambda n: isinstance(n, frog_ast.Variable) and n.name == name
        ).visit(node)
        is not None
    )


# ---------------------------------------------------------------------------
# References to a removed field
# ---------------------------------------------------------------------------


def _binding_parts(
    statement: frog_ast.Statement, name: str
) -> Optional[list[Optional[frog_ast.ASTNode]]]:
    """If *statement* declares a local *name*, the parts of it evaluated
    before that binding exists (its type and value); otherwise None."""
    if isinstance(statement, frog_ast.VariableDeclaration):
        return [statement.type] if statement.name == name else None
    if not isinstance(
        statement, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
    ):
        return None
    if statement.the_type is None or statement.var != frog_ast.Variable(name):
        return None
    if isinstance(statement, frog_ast.Assignment):
        return [statement.the_type, statement.value]
    if isinstance(statement, frog_ast.Sample):
        return [statement.the_type, statement.sampled_from]
    return [statement.the_type, statement.unique_set, statement.sampled_from]


def _reads_unbound(statements: list[frog_ast.Statement], name: str) -> bool:
    """True if *statements* name *name* (in any position: a value, a type,
    a literal's length, an l-value) where no local declaration of *name* in
    an enclosing block precedes it."""
    for statement in statements:
        parts = _binding_parts(statement, name)
        if parts is not None:
            # The rest of this block reads the new local.
            return any(p is not None and _mentions(p, name) for p in parts)
        if isinstance(statement, frog_ast.IfStatement):
            if any(_mentions(c, name) for c in statement.conditions) or any(
                _reads_unbound(list(b.statements), name) for b in statement.blocks
            ):
                return True
        elif isinstance(statement, frog_ast.NumericFor):
            if _mentions(statement.start, name) or _mentions(statement.end, name):
                return True
            if statement.name != name and _reads_unbound(
                list(statement.block.statements), name
            ):
                return True
        elif isinstance(statement, frog_ast.GenericFor):
            if _mentions(statement.var_type, name) or _mentions(statement.over, name):
                return True
            if statement.var_name != name and _reads_unbound(
                list(statement.block.statements), name
            ):
                return True
        elif isinstance(statement, frog_ast.Block):
            if _reads_unbound(list(statement.statements), name):
                return True
        elif _mentions(statement, name):
            return True
    return False


def _unbound_reference(
    game: frog_ast.Game, name: str
) -> Optional[tuple[str, Optional[str]]]:
    """Where *game*, from which a pass removed the field *name*, still names
    it with nothing in scope to bind it: (a description, the method or None).

    The pass rewrites the reads it understands into its replacement (or into
    locals it declares). Any other occurrence would now refer to whatever
    else is called *name* (a proof ``let:`` entry, or nothing at all) and
    silently change the game: another field's type or initializer (which
    runs before Initialize, when the removed field held its default), a
    method signature, or, in a method body, a type, a sampled-from set or a
    bit-string literal's length that is not under one of those locals. The
    pass then keeps the field.
    """
    for field in game.fields:
        if _mentions(field, name):
            return f"the declaration of field '{field.name}'", None
    for method in game.methods:
        method_name = method.signature.name
        if _mentions(method.signature, name):
            return f"the signature of '{method_name}'", method_name
        if any(p.name == name for p in method.signature.parameters):
            continue
        if _reads_unbound(list(method.block.statements), name):
            return f"a statement of '{method_name}'", method_name
    return None


def _note_unbound_reference(
    ctx: PipelineContext,
    transform_name: str,
    name: str,
    where: tuple[str, Optional[str]],
) -> None:
    description, method = where
    ctx.near_misses.append(
        NearMiss(
            transform_name=transform_name,
            reason=(
                f"Removing field '{name}' would leave {description} naming "
                f"'{name}' with nothing in scope to bind it"
            ),
            location=None,
            suggestion=(
                f"Name '{name}' only in method bodies, as a value: not in "
                "another field's declaration, a signature or a type"
            ),
            variable=name,
            method=method,
        )
    )


# ---------------------------------------------------------------------------
# Symbolic execution
# ---------------------------------------------------------------------------


@dataclass
class _Path:
    env: dict[str, frog_ast.Expression]
    returned: Optional[frog_ast.Expression] = None
    done: bool = False
    # Truth values of Boolean fresh names that the branch conditions taken on
    # this path force (e.g. after ``if (revealed) { return; }``, the entry
    # value of ``revealed`` is false). Used to drop paths that cannot run.
    facts: dict[str, bool] = dataclass_field(default_factory=dict)

    def moved(self, env: dict[str, frog_ast.Expression]) -> "_Path":
        return _Path(env, facts=self.facts)


def _assume(
    condition: frog_ast.Expression, value: bool, facts: dict[str, bool]
) -> Optional[dict[str, bool]]:
    """*facts* extended with ``condition == value``; None if contradictory.

    Only literal facts about fresh Boolean names are recorded (through ``!``,
    ``&&`` when true and ``||`` when false); any other condition adds
    nothing, which only keeps more paths (sound).
    """
    if isinstance(condition, frog_ast.Boolean):
        return facts if condition.bool == value else None
    if isinstance(condition, frog_ast.Variable) and _is_symbol(condition):
        known = facts.get(condition.name)
        if known is None:
            extended = dict(facts)
            extended[condition.name] = value
            return extended
        return facts if known == value else None
    if (
        isinstance(condition, frog_ast.UnaryOperation)
        and condition.operator == frog_ast.UnaryOperators.NOT
    ):
        return _assume(condition.expression, not value, facts)
    if isinstance(condition, frog_ast.BinaryOperation):
        both = (condition.operator == frog_ast.BinaryOperators.AND and value) or (
            condition.operator == frog_ast.BinaryOperators.OR and not value
        )
        if both:
            left = _assume(condition.left_expression, value, facts)
            if left is None:
                return None
            return _assume(condition.right_expression, value, left)
        either = (condition.operator == frog_ast.BinaryOperators.AND and not value) or (
            condition.operator == frog_ast.BinaryOperators.OR and value
        )
        if either:
            # One side must take *value*; contradictory only if neither can.
            left = _assume(condition.left_expression, value, facts)
            right = _assume(condition.right_expression, value, facts)
            if left is None and right is None:
                return None
            if left is None:
                return right
            if right is None:
                return left
    return facts


def _apply_facts(
    expr: frog_ast.Expression, facts: dict[str, bool]
) -> frog_ast.Expression:
    return _replace_names(
        expr, {name: frog_ast.Boolean(value) for name, value in facts.items()}
    )


class _SymbolicExecutor:
    """Executes a method body over fresh names (see module docstring)."""

    def __init__(
        self,
        type_map: NameTypeMap,
        ctx: PipelineContext,
        counter: itertools.count[int],
    ) -> None:
        self.type_map = type_map
        self.ctx = ctx
        self.symbol_types = NameTypeMap()
        self._counter = counter

    def fresh(self, the_type: Optional[frog_ast.Type]) -> frog_ast.Variable:
        if the_type is None:
            raise _Unsupported("untyped value")
        name = f"{_SYMBOL_PREFIX}{next(self._counter)}"
        self.symbol_types.set(name, copy.deepcopy(the_type))
        return frog_ast.Variable(name)

    def full_type_map(self) -> NameTypeMap:
        return self.type_map + self.symbol_types

    def _is_deterministic_call(self, call: frog_ast.FuncCall) -> bool:
        func = call.func
        if isinstance(func, frog_ast.Variable):
            func_type = self.symbol_types.get(func.name) or (
                self.ctx.proof_let_types.get(func.name)
            )
            return isinstance(func_type, frog_ast.FunctionType)
        signature = _lookup_primitive_method(func, self.ctx.proof_namespace)
        return signature is not None and signature.deterministic

    def _call_type(self, call: frog_ast.FuncCall) -> Optional[frog_ast.Type]:
        signature = _lookup_primitive_method(call.func, self.ctx.proof_namespace)
        if signature is not None:
            return signature.return_type
        return infer_type(call, self.full_type_map())

    def evaluate(
        self,
        expr: frog_ast.Expression,
        env: dict[str, frog_ast.Expression],
    ) -> frog_ast.Expression:
        """The value of *expr* in *env*; non-deterministic calls become fresh."""

        def on_variable(var: frog_ast.Variable) -> frog_ast.Expression:
            if var.name in env:
                return copy.deepcopy(env[var.name])
            return copy.deepcopy(var)

        def on_call(call: frog_ast.FuncCall) -> frog_ast.Expression:
            if self._is_deterministic_call(call):
                return call
            return self.fresh(self._call_type(call))

        return _map_expression(expr, on_variable, on_call)

    def _declared_type(
        self, name: str, the_type: Optional[frog_ast.Type]
    ) -> Optional[frog_ast.Type]:
        return the_type if the_type is not None else self.type_map.get(name)

    def run(
        self, statements: list[frog_ast.Statement], paths: list[_Path]
    ) -> list[_Path]:
        for statement in statements:
            next_paths: list[_Path] = []
            for path in paths:
                if path.done:
                    next_paths.append(path)
                else:
                    next_paths.extend(self._step(statement, path))
            if len(next_paths) > _MAX_PATHS:
                raise _Unsupported("too many paths")
            paths = next_paths
        return paths

    def _havoc(self, env: dict[str, frog_ast.Expression], name: str) -> None:
        env[name] = self.fresh(self.type_map.get(name))

    def _step(  # pylint: disable=too-many-return-statements,too-many-branches
        self, statement: frog_ast.Statement, path: _Path
    ) -> list[_Path]:
        env = path.env
        if isinstance(statement, frog_ast.Assignment):
            value = self.evaluate(statement.value, env)
            if isinstance(statement.var, frog_ast.Variable):
                env = dict(env)
                name = statement.var.name
                declared = self._declared_type(name, statement.the_type)
                if _coerces(declared, infer_type(statement.value, self.type_map)):
                    # e.g. ModInt<q> x = <Int>: x holds the value reduced mod
                    # q, which no FrogLang expression over the Int states.
                    env[name] = self.fresh(declared)
                else:
                    env[name] = value
                return [path.moved(env)]
            base = lvalue_base_name(statement.var)
            if base is None:
                raise _Unsupported("assignment target")
            env = dict(env)
            self._havoc(env, base)
            return [path.moved(env)]
        if isinstance(statement, frog_ast.Sample):
            env = dict(env)
            if isinstance(statement.var, frog_ast.Variable):
                name = statement.var.name
                env[name] = self.fresh(self._declared_type(name, statement.the_type))
            else:
                base = lvalue_base_name(statement.var)
                if base is None:
                    raise _Unsupported("sample target")
                self._havoc(env, base)
            return [path.moved(env)]
        if isinstance(statement, frog_ast.UniqueSample):
            env = dict(env)
            base = lvalue_base_name(statement.var)
            if base is None:
                raise _Unsupported("sample target")
            if isinstance(statement.var, frog_ast.Variable):
                env[base] = self.fresh(self._declared_type(base, statement.the_type))
            else:
                self._havoc(env, base)
            if statement.surface_form == "uniq":
                set_base = lvalue_base_name(statement.unique_set)
                if set_base is None:
                    raise _Unsupported("exclusion set")
                self._havoc(env, set_base)
            return [path.moved(env)]
        if isinstance(statement, frog_ast.VariableDeclaration):
            env = dict(env)
            env[statement.name] = self.fresh(statement.type)
            return [path.moved(env)]
        if isinstance(statement, frog_ast.ReturnStatement):
            return [
                _Path(
                    env,
                    self.evaluate(statement.expression, env),
                    True,
                    path.facts,
                )
            ]
        if isinstance(statement, frog_ast.FuncCall):
            return [path]
        if isinstance(statement, frog_ast.Block):
            return self.run(list(statement.statements), [path])
        if isinstance(statement, frog_ast.IfStatement):
            results: list[_Path] = []
            # ``prefix`` holds on the paths where every earlier condition was
            # false; None once that is impossible.
            prefix: Optional[dict[str, bool]] = path.facts
            for index, block in enumerate(statement.blocks):
                if prefix is None:
                    break
                if index < len(statement.conditions):
                    condition = self.evaluate(statement.conditions[index], env)
                    taken = _assume(condition, True, prefix)
                    if taken is not None:
                        results.extend(
                            self.run(
                                list(block.statements),
                                [_Path(dict(env), facts=taken)],
                            )
                        )
                    prefix = _assume(condition, False, prefix)
                else:
                    results.extend(
                        self.run(
                            list(block.statements), [_Path(dict(env), facts=prefix)]
                        )
                    )
                    prefix = None
            if not statement.has_else_block() and prefix is not None:
                results.append(_Path(dict(env), facts=prefix))
            return results
        if isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
            if (
                SearchVisitor(lambda n: isinstance(n, frog_ast.ReturnStatement)).visit(
                    statement.block
                )
                is not None
            ):
                raise _Unsupported("return inside a loop")
            env = dict(env)
            for name in _written_names(statement.block):
                if name in env or self.type_map.get(name) is not None:
                    self._havoc(env, name)
            return [path.moved(env)]
        raise _Unsupported(type(statement).__name__)


def _coerces(
    declared: Optional[frog_ast.Type], value_type: Optional[frog_ast.Type]
) -> bool:
    """True if storing a value of *value_type* in a variable of *declared*
    type may change it (an Int stored in a ModInt is reduced, a ModInt read
    as an Int is its representative), or the types cannot be compared. A
    tuple, optional, map or other compound target may change a value the
    same way through a ``ModInt`` part (F-370(g)), judged by
    :func:`~proof_frog.visitors.store_may_change_value`."""
    numeric = (frog_ast.IntType, frog_ast.ModIntType)
    if isinstance(declared, numeric):
        return value_type is None or not bool(value_type == declared)
    return store_may_change_value(declared, value_type)


def _written_names(node: frog_ast.ASTNode) -> set[str]:
    names: set[str] = set()

    def visit(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)):
            base = lvalue_base_name(n.var)
            if base is not None:
                names.add(base)
            if (
                isinstance(n, frog_ast.UniqueSample)
                and n.surface_form == "uniq"
                and lvalue_base_name(n.unique_set) is not None
            ):
                names.add(lvalue_base_name(n.unique_set) or "")
        elif isinstance(n, frog_ast.VariableDeclaration):
            names.add(n.name)
        return False

    SearchVisitor(visit).visit(node)
    return names


# ---------------------------------------------------------------------------
# Proving an invariant
# ---------------------------------------------------------------------------


def _initialize(game: frog_ast.Game) -> Optional[frog_ast.Method]:
    for method in game.methods:
        if method.signature.name == "Initialize":
            return method
    return None


def _field_types(game: frog_ast.Game) -> dict[str, frog_ast.Type]:
    return {field.name: field.type for field in game.fields}


def _entry_env(
    game: frog_ast.Game, method: frog_ast.Method, executor: _SymbolicExecutor
) -> dict[str, frog_ast.Expression]:
    env: dict[str, frog_ast.Expression] = {}
    for field in game.fields:
        env[field.name] = executor.fresh(field.type)
    for param in method.signature.parameters:
        env[param.name] = executor.fresh(param.type)
    return env


def _shadows_fields(game: frog_ast.Game, method: frog_ast.Method) -> bool:
    return bool(bound_names(method) & set(_field_types(game)))


def _preserves(
    game: frog_ast.Game,
    target: str,
    expr: frog_ast.Expression,
    ctx: PipelineContext,
) -> tuple[bool, Optional[str]]:
    """Whether ``target == expr`` holds after Initialize and every oracle call.

    Returns (holds, name of the first method where it could not be shown).
    """
    fields = _field_types(game)
    target_type = fields[target]
    expr_fields = _free_names(expr) & set(fields)
    counter = itertools.count()
    for method in game.methods:
        is_init = method.signature.name == "Initialize"
        if not is_init and not reassigns_or_rebinds(
            {target} | expr_fields, method.block
        ):
            continue
        # The executor types names with the method's last-write-wins map, so
        # a name bound more than once would get one type for every binding.
        if _shadows_fields(game, method) or redeclared_names(game, method):
            return False, method.signature.name
        executor = _SymbolicExecutor(
            build_method_type_map(game, method, ctx.proof_let_types), ctx, counter
        )
        try:
            env = _entry_env(game, method, executor)
            if not is_init:
                env[target] = _replace_names(expr, env)
            paths = executor.run(list(method.block.statements), [_Path(env)])
            normalizer = Normalizer(executor.full_type_map())
            for path in paths:
                exit_target = _apply_facts(path.env[target], path.facts)
                exit_expr = _apply_facts(_replace_names(expr, path.env), path.facts)
                if not normalizer.equal(exit_target, exit_expr, target_type):
                    return False, method.signature.name
        except _Unsupported:
            return False, method.signature.name
    return True, None


# ---------------------------------------------------------------------------
# Field invariant elimination
# ---------------------------------------------------------------------------


def _written_outside_initialize(game: frog_ast.Game, name: str) -> bool:
    return any(
        method.signature.name != "Initialize"
        and reassigns_or_rebinds({name}, method.block)
        for method in game.methods
    )


def _is_symbol(expr: frog_ast.Expression) -> bool:
    return isinstance(expr, frog_ast.Variable) and expr.name.startswith(_SYMBOL_PREFIX)


def _is_literal(expr: frog_ast.Expression) -> bool:
    return isinstance(
        expr,
        (
            frog_ast.Integer,
            frog_ast.Boolean,
            frog_ast.NoneExpression,
            frog_ast.BinaryNum,
            frog_ast.BitStringLiteral,
        ),
    )


def _candidates(
    game: frog_ast.Game, ctx: PipelineContext
) -> list[tuple[str, frog_ast.Expression]]:
    """Relations ``a == E`` suggested by the state Initialize leaves behind.

    Only a field written outside Initialize is a candidate (a constant field
    is handled by other passes). ``E`` re-expresses ``a``'s value at the end
    of Initialize through the other fields holding the same values. The
    candidates are suggestions only; :func:`_preserves` decides.
    """
    init = _initialize(game)
    if init is None or _shadows_fields(game, init):
        return []
    executor = _SymbolicExecutor(
        build_method_type_map(game, init, ctx.proof_let_types),
        ctx,
        itertools.count(),
    )
    try:
        paths = executor.run(
            list(init.block.statements), [_Path(_entry_env(game, init, executor))]
        )
    except _Unsupported:
        return []
    if len(paths) != 1:
        return []
    env = paths[0].env
    field_names = [field.name for field in game.fields]
    field_map = NameTypeMap()
    for field in game.fields:
        field_map.set(field.name, field.type)
    field_map = field_map + ctx.proof_let_types
    holders: dict[str, list[str]] = {}
    for name in field_names:
        value = env[name]
        if isinstance(value, frog_ast.Variable) and _is_symbol(value):
            holders.setdefault(value.name, []).append(name)

    result: list[tuple[str, frog_ast.Expression]] = []
    for target in field_names:
        value = env[target]
        if _is_symbol(value):
            continue
        if not _written_outside_initialize(game, target):
            continue
        # A field holding the same value as another one (two flags both
        # reset to false, a copy of a key) may be that field.
        options: list[frog_ast.Expression] = [
            frog_ast.Variable(other)
            for other in field_names
            if other != target
            and env[other] == value
            and _written_outside_initialize(game, other)
        ]
        if _is_literal(value):
            # Only a fellow field can explain a literal; the literal itself
            # (a field that never changes) is not a relation worth proving.
            for option in options:
                if bool(infer_type(option, field_map) == _field_types(game)[target]):
                    result.append((target, option))
            continue
        symbols = sorted(n for n in _free_names(value) if n.startswith(_SYMBOL_PREFIX))
        choices = [[h for h in holders.get(s, []) if h != target] for s in symbols]
        if all(choices):
            for pick in itertools.islice(itertools.product(*choices), _MAX_CANDIDATES):
                options.append(
                    _replace_names(
                        value,
                        {s: frog_ast.Variable(h) for s, h in zip(symbols, pick)},
                    )
                )
        seen: list[frog_ast.Expression] = []
        target_type = _field_types(game)[target]
        for option in options:
            if any(_is_symbol(frog_ast.Variable(n)) for n in _free_names(option)):
                continue
            # The relation is between values of one type: a ModInt field
            # equal to an Int expression would hide the reduction.
            if not bool(infer_type(option, field_map) == target_type):
                continue
            if option in seen or _is_literal(option):
                continue
            seen.append(option)
            result.append((target, option))
    return result


def _substitute_clean(
    statements: list[frog_ast.Statement],
    target: str,
    expr: frog_ast.Expression,
    watched: set[str],
) -> tuple[list[frog_ast.Statement], bool]:
    """Replace reads of *target* by *expr* until something in *watched* is
    written (on some path); return the new statements and whether nothing in
    *watched* was written.

    Up to the first write, the local ``target`` still holds its entry value
    ``expr`` and *expr*'s fields still hold their entry values, so each such
    read equals *expr*.
    """
    mapping = {target: expr}
    out: list[frog_ast.Statement] = []
    clean = True
    for statement in statements:
        if not clean:
            out.append(statement)
            continue
        new_statement = _substitute_statement(statement, mapping, target, expr, watched)
        out.append(new_statement)
        if reassigns_or_rebinds(watched, statement):
            clean = False
    return out, clean


def _substitute_statement(  # pylint: disable=too-many-return-statements
    statement: frog_ast.Statement,
    mapping: dict[str, frog_ast.Expression],
    target: str,
    expr: frog_ast.Expression,
    watched: set[str],
) -> frog_ast.Statement:
    """*statement* with reads of *target* evaluated before any write in it
    replaced by *expr* (a statement not handled is returned unchanged)."""
    if isinstance(statement, frog_ast.Assignment):
        var = statement.var
        if not isinstance(var, frog_ast.Variable):
            return statement
        return frog_ast.Assignment(
            copy.deepcopy(statement.the_type),
            copy.deepcopy(var),
            _replace_names(statement.value, mapping),
        )
    if isinstance(statement, frog_ast.ReturnStatement):
        return frog_ast.ReturnStatement(_replace_names(statement.expression, mapping))
    if isinstance(statement, frog_ast.FuncCall):
        replaced = _replace_names(statement, mapping)
        assert isinstance(replaced, frog_ast.FuncCall)
        return replaced
    if isinstance(statement, frog_ast.IfStatement):
        blocks = [
            frog_ast.Block(
                _substitute_clean(list(block.statements), target, expr, watched)[0]
            )
            for block in statement.blocks
        ]
        return frog_ast.IfStatement(
            [_replace_names(c, mapping) for c in statement.conditions], blocks
        )
    return statement


def _single_assignment_entry(
    body: list[frog_ast.Statement],
    target: str,
    target_type: frog_ast.Type,
    expr: frog_ast.Expression,
    taken: set[str],
) -> list[frog_ast.Statement]:
    """Give the removed field's entry value and its new value separate locals.

    The method starts with the entry value ``E``. When the first write to
    ``target`` is a top-level assignment, the reads before it (and in its
    right-hand side) use a local ``target@entry = E`` (another fresh name if
    *taken*, the names of the game, has that one), and the write declares a
    fresh local ``target``; each local then has one definition, so later
    passes can inline or absorb it. Otherwise ``target`` is one mutable local
    starting at ``E``.
    """
    first = next(
        (i for i, s in enumerate(body) if reassigns_or_rebinds({target}, s)), None
    )
    if first is not None:
        write = body[first]
        if (
            isinstance(write, frog_ast.Assignment)
            and write.the_type is None
            and write.var == frog_ast.Variable(target)
        ):
            entry = fresh_name(f"{target}@entry", taken)
            reads: dict[str, frog_ast.Expression] = {target: frog_ast.Variable(entry)}
            prefix = [_rewrite_statement(s, {}, reads) for s in body[:first]]
            declaration = frog_ast.Assignment(
                copy.deepcopy(target_type),
                frog_ast.Variable(target),
                _replace_names(write.value, reads),
            )
            rest = prefix + [declaration] + body[first + 1 :]
            if _mentions(frog_ast.Block(prefix + [declaration]), entry):
                rest = [
                    frog_ast.Assignment(
                        copy.deepcopy(target_type),
                        frog_ast.Variable(entry),
                        copy.deepcopy(expr),
                    )
                ] + rest
            return rest
    return [
        frog_ast.Assignment(
            copy.deepcopy(target_type), frog_ast.Variable(target), copy.deepcopy(expr)
        )
    ] + body


def _eliminate(
    game: frog_ast.Game, target: str, expr: frog_ast.Expression
) -> Optional[frog_ast.Game]:
    """*game* with field *target* replaced by ``expr`` (see the pass)."""
    target_type = _field_types(game)[target]
    expr_names = _free_names(expr)
    watched = {target} | (expr_names & set(_field_types(game)))
    names = game_names(game)
    new_methods: list[frog_ast.Method] = []
    for method in game.methods:
        if not _mentions(method.block, target):
            new_methods.append(method)
            continue
        if target in bound_names(method) or (bound_names(method) & expr_names):
            return None
        statements = list(copy.deepcopy(method.block.statements))
        if method.signature.name == "Initialize":
            index = next(i for i, s in enumerate(statements) if _mentions(s, target))
            first = statements[index]
            if not (
                isinstance(first, (frog_ast.Assignment, frog_ast.Sample))
                and first.var == frog_ast.Variable(target)
                and first.the_type is None
                and not (
                    isinstance(first, frog_ast.Assignment)
                    and _mentions(first.value, target)
                )
            ):
                return None
            first.the_type = copy.deepcopy(target_type)
        else:
            body, _ = _substitute_clean(statements, target, expr, watched)
            if _mentions(frog_ast.Block(body), target):
                body = _single_assignment_entry(
                    body, target, target_type, expr, set(names)
                )
            statements = body
        new_methods.append(
            frog_ast.Method(copy.deepcopy(method.signature), frog_ast.Block(statements))
        )
    new_fields = [copy.deepcopy(f) for f in game.fields if f.name != target]
    return frog_ast.Game(
        (game.name, copy.deepcopy(game.parameters), new_fields, new_methods)
    )


_proof_cache: "OrderedDict[str, tuple[bool, Optional[str]]]" = OrderedDict()


def _context_fingerprint(ctx: PipelineContext) -> object:
    """What a proof by :func:`_preserves` reads from *ctx*: which calls are
    deterministic (primitive method annotations, let-bound Functions) and the
    let types. Part of the cache key, so a long-lived process (the language
    server) never reuses a verdict across proofs that differ in these."""
    primitives = sorted(
        (
            (
                name,
                [(m.name, m.deterministic, m.return_type) for m in value.methods],
            )
            for name, value in ctx.proof_namespace.items()
            if isinstance(value, frog_ast.Primitive)
        ),
        key=lambda entry: entry[0],
    )
    return (primitives, ctx.proof_let_types)


def _cached_preserves(
    game: frog_ast.Game, target: str, expr: frog_ast.Expression, ctx: PipelineContext
) -> tuple[bool, Optional[str]]:
    # The key is a structural digest of the inputs, not their printed text:
    # two different games can print alike (F-370(d)), and a verdict for one
    # must never answer for the other. A lazy import, since hop_cache imports
    # the transforms package.
    # pylint: disable-next=import-outside-toplevel
    from ..hop_cache import Uncacheable, structural_digest

    try:
        key = structural_digest((game, target, expr, _context_fingerprint(ctx)))
    except Uncacheable:
        return _preserves(game, target, expr, ctx)
    if key in _proof_cache:
        _proof_cache.move_to_end(key)
        return _proof_cache[key]
    result = _preserves(game, target, expr, ctx)
    _proof_cache[key] = result
    if len(_proof_cache) > _CACHE_SIZE:
        _proof_cache.popitem(last=False)
    return result


class FieldInvariantElimination(TransformPass):
    """Remove a field that always equals an expression over other fields.

    A field ``a`` written outside Initialize whose value at the end of
    Initialize can be written as ``E`` over other fields is a candidate.
    If ``a == E`` is proved to hold after Initialize and to be preserved by
    every oracle (module docstring), the field is removed: Initialize keeps
    ``a`` as a local, and every other method that uses ``a`` starts with
    ``a = E;`` and reads ``E`` directly until ``a`` or a field of ``E`` is
    written. Exact, by induction over oracle calls.

    Example: ``pk = g^x; sk = x;`` in Initialize with every update doing
    ``pk = pk * g^d; sk = sk + d;`` (or anything provably equal) removes
    ``pk``, whose reads become ``g ^ sk``.
    """

    name = "Field Invariant Elimination"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        for target, expr in _candidates(game, ctx):
            holds, failed_in = _cached_preserves(game, target, expr, ctx)
            if not holds:
                ctx.near_misses.append(
                    NearMiss(
                        transform_name=self.name,
                        reason=(
                            f"Field '{target}' equals '{expr}' after Initialize, "
                            f"but the engine could not show that method "
                            f"'{failed_in}' preserves the relation"
                        ),
                        location=None,
                        suggestion=(
                            f"Check that '{failed_in}' updates '{target}' and the "
                            "fields it is related to consistently"
                        ),
                        variable=target,
                        method=failed_in,
                    )
                )
                continue
            try:
                new_game = _eliminate(game, target, expr)
            except _Unsupported:
                new_game = None
            if new_game is None:
                continue
            where = _unbound_reference(new_game, target)
            if where is not None:
                _note_unbound_reference(ctx, self.name, target, where)
                continue
            return new_game
        return game


# ---------------------------------------------------------------------------
# Generator-power fields to exponents
# ---------------------------------------------------------------------------


def _writes_of(node: frog_ast.ASTNode, name: str) -> list[frog_ast.Statement]:
    writes: list[frog_ast.Statement] = []

    def visit(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)):
            if lvalue_base_name(n.var) == name:
                writes.append(n)
            elif (
                isinstance(n, frog_ast.UniqueSample)
                and n.surface_form == "uniq"
                and lvalue_base_name(n.unique_set) == name
            ):
                writes.append(n)
        return False

    SearchVisitor(visit).visit(node)
    return writes


@dataclass
class _ExponentWrite:
    """``P = g ^ x`` (relative=False) or ``P = P * g ^ x`` (relative=True)."""

    relative: bool
    exponent: frog_ast.Expression


def _exponent_write(
    value: frog_ast.Expression,
    name: str,
    group: frog_ast.Expression,
    normalizer: Normalizer,
) -> Optional[_ExponentWrite]:
    form = normalizer.normal_form(value, frog_ast.GroupElemType(group))
    if not isinstance(form, GroupForm):
        return None
    generator = normalizer.atoms.symbol(
        frog_ast.FieldAccess(copy.deepcopy(group), "generator")
    )
    self_symbol = normalizer.atoms.symbol(frog_ast.Variable(name))
    if not set(form.bases) <= {generator, self_symbol}:
        return None
    self_power = form.bases.get(self_symbol, 0)
    if self_power not in (0, 1):
        return None
    exponent_poly = form.bases.get(generator, 0)
    # The new field is a ModInt<G.order>: every atom of the exponent must
    # have exactly that type, so that ``p + x`` and ``p = x`` are well typed
    # (an Int atom would make the sum an Int/ModInt mix).
    for symbol in getattr(exponent_poly, "free_symbols", set()):
        atom_type = infer_type(normalizer.atoms.expression(symbol), normalizer.type_map)
        if not (
            isinstance(atom_type, frog_ast.ModIntType)
            and is_order_of(atom_type.modulus, group)
        ):
            return None
    return _ExponentWrite(self_power == 1, normalizer.rebuild_poly(exponent_poly))


class GeneratorPowerFieldToExponent(TransformPass):
    """Keep a generator-power group field as its exponent.

    A ``GroupElem<G>`` field ``P``, written outside Initialize, whose every
    write is (up to the group algebra) ``P = g ^ x`` or ``P = P * g ^ x``,
    and which Initialize sets that way before any read or return, is
    replaced by a ``ModInt<G.order>`` field ``p``: the writes become
    ``p = x`` and ``p = p + x``, and every read of ``P`` becomes ``g ^ p``.
    ``P == g ^ p`` holds after every write by construction, so the rewrite
    is exact. (``g`` generates ``G``, so exponents add modulo the order.)

    Two games that keep the same evolving key once as a group element and
    once as a secret exponent then agree.
    """

    name = "Generator Power Field To Exponent"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        for field in game.fields:
            if not isinstance(field.type, frog_ast.GroupElemType):
                continue
            if field.value is not None:
                continue
            if not _written_outside_initialize(game, field.name):
                continue
            new_game = self._try(game, field, ctx)
            if new_game is not None:
                return new_game
        return game

    def _try(  # pylint: disable=too-many-return-statements
        self, game: frog_ast.Game, field: frog_ast.Field, ctx: PipelineContext
    ) -> Optional[frog_ast.Game]:
        name = field.name
        assert isinstance(field.type, frog_ast.GroupElemType)
        group = field.type.group
        init = _initialize(game)
        if init is None:
            return None
        statements = list(init.block.statements)
        first = next((i for i, s in enumerate(statements) if _mentions(s, name)), None)
        if first is None or may_return_before(statements, first):
            return None
        first_statement = statements[first]
        if not (
            isinstance(first_statement, frog_ast.Assignment)
            and first_statement.var == frog_ast.Variable(name)
            and not _mentions(first_statement.value, name)
        ):
            return None
        # The new field must not be named like anything in the game: a local
        # of that name would capture the rewritten reads and writes (F-370).
        exponent_name = fresh_name(f"{name}@exp", game_names(game))
        rewrites: dict[int, frog_ast.Statement] = {}
        for method in game.methods:
            if name in bound_names(method):
                return None
            method_types = build_method_type_map(game, method, ctx.proof_let_types)
            normalizer = Normalizer(method_types)
            redeclared = redeclared_names(game, method)
            for write in _writes_of(method.block, name):
                if not (
                    isinstance(write, frog_ast.Assignment)
                    and write.var == frog_ast.Variable(name)
                    and write.the_type is None
                ):
                    self._near_miss(
                        ctx, name, method, "is written other than by assignment"
                    )
                    return None
                # Atoms are typed with the method's last-write-wins map.
                clash = sorted(_free_names(write.value) & redeclared)
                if clash:
                    note_redeclared_name(
                        ctx, self.name, clash[0], method.signature.name
                    )
                    return None
                # The group normal form merges equal calls into one atom, which
                # is right only for calls that return the same value each time.
                if not calls_are_deterministic(
                    write.value,
                    ctx.proof_namespace,
                    ctx.proof_let_types,
                    method_types,
                    bound_names(method),
                ):
                    self._near_miss(
                        ctx,
                        name,
                        method,
                        "is assigned a value that makes a non-deterministic call",
                    )
                    return None
                parsed = _exponent_write(write.value, name, group, normalizer)
                if parsed is None:
                    self._near_miss(
                        ctx,
                        name,
                        method,
                        f"is assigned '{write.value}', which is not g^x or {name} * g^x",
                    )
                    return None
                exponent = parsed.exponent
                value: frog_ast.Expression = (
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.ADD,
                        frog_ast.Variable(exponent_name),
                        exponent,
                    )
                    if parsed.relative
                    else exponent
                )
                rewrites[id(write)] = frog_ast.Assignment(
                    None, frog_ast.Variable(exponent_name), value
                )
        power = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE,
            frog_ast.FieldAccess(copy.deepcopy(group), "generator"),
            frog_ast.Variable(exponent_name),
        )
        try:
            new_methods = [
                frog_ast.Method(
                    copy.deepcopy(method.signature),
                    _rewrite_block(method.block, rewrites, {name: power}),
                )
                for method in game.methods
            ]
        except _Unsupported:
            return None
        new_fields: list[frog_ast.Field] = []
        for other in game.fields:
            if other.name == name:
                new_fields.append(
                    frog_ast.Field(
                        frog_ast.ModIntType(
                            frog_ast.FieldAccess(copy.deepcopy(group), "order")
                        ),
                        exponent_name,
                        None,
                    )
                )
            else:
                new_fields.append(copy.deepcopy(other))
        new_game = frog_ast.Game(
            (game.name, copy.deepcopy(game.parameters), new_fields, new_methods)
        )
        where = _unbound_reference(new_game, name)
        if where is not None:
            _note_unbound_reference(ctx, self.name, name, where)
            return None
        return new_game

    def _near_miss(
        self,
        ctx: PipelineContext,
        name: str,
        method: frog_ast.Method,
        why: str,
    ) -> None:
        ctx.near_misses.append(
            NearMiss(
                transform_name=self.name,
                reason=f"Group field '{name}' {why} in '{method.signature.name}'",
                location=None,
                suggestion=(
                    f"Write every update of '{name}' as {name} = g^x or "
                    f"{name} = {name} * g^x"
                ),
                variable=name,
                method=method.signature.name,
            )
        )


def _rewrite_block(
    block: frog_ast.Block,
    rewrites: dict[int, frog_ast.Statement],
    reads: dict[str, frog_ast.Expression],
) -> frog_ast.Block:
    """Replace the statements in *rewrites* (by identity), and every read of
    a name in *reads* by its expression, in all expression positions."""
    out: list[frog_ast.Statement] = []
    for statement in block.statements:
        if id(statement) in rewrites:
            replacement = copy.deepcopy(rewrites[id(statement)])
            assert isinstance(replacement, frog_ast.Assignment)
            replacement.value = _replace_names(replacement.value, reads)
            out.append(replacement)
            continue
        out.append(_rewrite_statement(statement, rewrites, reads))
    return frog_ast.Block(out)


def _rewrite_lvalue(
    target: frog_ast.Expression, reads: dict[str, frog_ast.Expression]
) -> frog_ast.Expression:
    """Rewrite the index expressions of an l-value, never its base."""
    if isinstance(target, frog_ast.Variable):
        return copy.deepcopy(target)
    if isinstance(target, frog_ast.ArrayAccess):
        return frog_ast.ArrayAccess(
            _rewrite_lvalue(target.the_array, reads),
            _replace_names(target.index, reads),
        )
    if isinstance(target, frog_ast.Slice):
        return frog_ast.Slice(
            _rewrite_lvalue(target.the_array, reads),
            _replace_names(target.start, reads),
            _replace_names(target.end, reads),
        )
    if isinstance(target, frog_ast.FieldAccess):
        return frog_ast.FieldAccess(
            _rewrite_lvalue(target.the_object, reads), target.name
        )
    raise _Unsupported("l-value")


def _rewrite_statement(  # pylint: disable=too-many-return-statements
    statement: frog_ast.Statement,
    rewrites: dict[int, frog_ast.Statement],
    reads: dict[str, frog_ast.Expression],
) -> frog_ast.Statement:
    if isinstance(statement, frog_ast.Assignment):
        return frog_ast.Assignment(
            copy.deepcopy(statement.the_type),
            _rewrite_lvalue(statement.var, reads),
            _replace_names(statement.value, reads),
        )
    if isinstance(statement, frog_ast.Sample):
        return frog_ast.Sample(
            copy.deepcopy(statement.the_type),
            _rewrite_lvalue(statement.var, reads),
            copy.deepcopy(statement.sampled_from),
        )
    if isinstance(statement, frog_ast.UniqueSample):
        return frog_ast.UniqueSample(
            copy.deepcopy(statement.the_type),
            _rewrite_lvalue(statement.var, reads),
            _replace_names(statement.unique_set, reads),
            copy.deepcopy(statement.sampled_from),
            statement.surface_form,
        )
    if isinstance(statement, frog_ast.ReturnStatement):
        return frog_ast.ReturnStatement(_replace_names(statement.expression, reads))
    if isinstance(statement, frog_ast.FuncCall):
        replaced = _replace_names(statement, reads)
        assert isinstance(replaced, frog_ast.FuncCall)
        return replaced
    if isinstance(statement, frog_ast.IfStatement):
        return frog_ast.IfStatement(
            [_replace_names(c, reads) for c in statement.conditions],
            [_rewrite_block(b, rewrites, reads) for b in statement.blocks],
        )
    if isinstance(statement, frog_ast.NumericFor):
        return frog_ast.NumericFor(
            statement.name,
            _replace_names(statement.start, reads),
            _replace_names(statement.end, reads),
            _rewrite_block(statement.block, rewrites, reads),
        )
    if isinstance(statement, frog_ast.GenericFor):
        return frog_ast.GenericFor(
            copy.deepcopy(statement.var_type),
            statement.var_name,
            _replace_names(statement.over, reads),
            _rewrite_block(statement.block, rewrites, reads),
        )
    if isinstance(statement, frog_ast.VariableDeclaration):
        return copy.deepcopy(statement)
    if isinstance(statement, frog_ast.Block):
        return _rewrite_block(statement, rewrites, reads)
    raise _Unsupported(type(statement).__name__)


# ---------------------------------------------------------------------------
# Fixed secret plus public offset
# ---------------------------------------------------------------------------

# Depth of OffsetFusion's own probe pipeline runs (it never nests itself).
_FUSION_DEPTH = [0]


class OffsetFusion(TransformPass):
    """Fuse a fixed group element ``g ^ e`` and an evolving offset ``D``.

    The pattern is random self-reducibility: a reduction keeps the
    challenger's fixed public key ``P = g ^ e`` and the sum ``D`` of the
    shifts it has applied, and answers for the secret ``e + D``. A game that
    keeps the evolving secret itself has one field where the reduction has
    two. This pass introduces the field ``s`` (``ModInt<G.order>``) with
    ``s == e + D`` at every call boundary:

    * Initialize computes ``e`` into a local where it wrote ``P``, reads
      ``P`` as ``g ^ e``, and sets ``s = e + D`` before every exit;
    * every other write ``D = w`` becomes ``t = w; s = s + (t - D); D = t;``
      (so ``s - D`` keeps the value ``e``);
    * every read of ``P`` outside Initialize becomes ``g ^ (s - D)``.

    ``P`` is then gone and the rewrite is exact by construction. It is kept
    only if canonicalizing the result removes ``D`` as well, i.e. ``D`` was
    only ever read together with ``P`` (as in ``P * g ^ D`` or
    ``P ^ r * (g ^ r) ^ D``); otherwise the game is left unchanged, so the
    pass never adds a field.
    """

    name = "Offset Fusion"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        if _FUSION_DEPTH[0] > 0:
            return game
        init = _initialize(game)
        if init is None:
            return game
        fields = _field_types(game)
        for fixed in game.fields:
            if not isinstance(fixed.type, frog_ast.GroupElemType):
                continue
            for offset in game.fields:
                offset_type = offset.type
                if not (
                    isinstance(offset_type, frog_ast.ModIntType)
                    and is_order_of(offset_type.modulus, fixed.type.group)
                    and _written_outside_initialize(game, offset.name)
                ):
                    continue
                fused = _fuse(game, init, fixed, offset, ctx)
                if fused is None:
                    continue
                _FUSION_DEPTH[0] += 1
                try:
                    # pylint: disable=import-outside-toplevel,cyclic-import
                    from .pipelines import CORE_PIPELINE
                    from ._base import run_pipeline

                    probe_ctx = copy.copy(ctx)
                    probe_ctx.near_misses = []
                    probe_ctx.pinned_fields = set(ctx.pinned_fields)
                    simplified = run_pipeline(fused, list(CORE_PIPELINE), probe_ctx)
                finally:
                    _FUSION_DEPTH[0] -= 1
                remaining = {f.name for f in simplified.fields}
                if offset.name not in remaining and fixed.name not in remaining:
                    return fused
                ctx.near_misses.append(
                    NearMiss(
                        transform_name=self.name,
                        reason=(
                            f"'{fixed.name}' is a fixed g^e and '{offset.name}' an "
                            f"offset of the same group order, but '{offset.name}' "
                            f"is still read on its own after fusing them"
                        ),
                        location=None,
                        suggestion=(
                            f"Use '{offset.name}' only together with "
                            f"'{fixed.name}' (as {fixed.name} * g^{offset.name})"
                        ),
                        variable=offset.name,
                        method=None,
                    )
                )
        del fields
        return game


def _fuse(  # pylint: disable=too-many-return-statements,too-many-locals
    game: frog_ast.Game,
    init: frog_ast.Method,
    fixed: frog_ast.Field,
    offset: frog_ast.Field,
    ctx: PipelineContext,
) -> Optional[frog_ast.Game]:
    """The fused game, or None if the pattern does not apply."""
    assert isinstance(fixed.type, frog_ast.GroupElemType)
    group = fixed.type.group
    name, offset_name = fixed.name, offset.name
    if fixed.value is not None or offset.value is not None:
        return None
    for method in game.methods:
        bound = bound_names(method)
        # A local or parameter named like P or D would capture g ^ (s - D).
        if name in bound or offset_name in bound:
            return None
    # The new field, Initialize's exponent local and the temporaries of
    # _track_offset must not be named like anything in the game, or they
    # would capture an existing binding's reads (F-370).
    taken = game_names(game)
    fused_name = fresh_name(f"{name}@fused", taken)
    exponent_name = fresh_name(f"{name}@exp", taken)
    # P is written exactly once, at the top level of Initialize, as g ^ e.
    writes = [w for m in game.methods for w in _writes_of(m.block, name)]
    if len(writes) != 1:
        return None
    statements = list(init.block.statements)
    index = next((i for i, s in enumerate(statements) if _mentions(s, name)), None)
    if index is None or statements[index] is not writes[0]:
        return None
    write = statements[index]
    if not (
        isinstance(write, frog_ast.Assignment)
        and write.the_type is None
        and write.var == frog_ast.Variable(name)
    ) or may_return_before(statements, index):
        return None
    init_types = build_method_type_map(game, init, ctx.proof_let_types)
    # Atoms are typed with Initialize's last-write-wins map.
    clash = sorted(_free_names(write.value) & redeclared_names(game, init))
    if clash:
        note_redeclared_name(ctx, OffsetFusion.name, clash[0], "Initialize")
        return None
    if not calls_are_deterministic(
        write.value,
        ctx.proof_namespace,
        ctx.proof_let_types,
        init_types,
        bound_names(init),
    ):
        return None
    normalizer = Normalizer(init_types)
    form = normalizer.normal_form(write.value, frog_ast.GroupElemType(group))
    generator = normalizer.atoms.symbol(
        frog_ast.FieldAccess(copy.deepcopy(group), "generator")
    )
    if not isinstance(form, GroupForm) or set(form.bases) != {generator}:
        return None
    exponent_poly = form.bases[generator]
    for symbol in getattr(exponent_poly, "free_symbols", set()):
        atom_type = infer_type(normalizer.atoms.expression(symbol), normalizer.type_map)
        if not (
            isinstance(atom_type, frog_ast.ModIntType)
            and is_order_of(atom_type.modulus, group)
        ):
            return None
    exponent = normalizer.rebuild_poly(exponent_poly)
    # D is only ever assigned whole.
    for method in game.methods:
        for w in _writes_of(method.block, offset_name):
            if not (
                isinstance(w, frog_ast.Assignment)
                and w.the_type is None
                and w.var == frog_ast.Variable(offset_name)
            ):
                return None

    zq = copy.deepcopy(offset.type)
    generator_ast = frog_ast.FieldAccess(copy.deepcopy(group), "generator")

    def power(exp: frog_ast.Expression) -> frog_ast.Expression:
        return frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE, copy.deepcopy(generator_ast), exp
        )

    def set_fused() -> frog_ast.Statement:
        return frog_ast.Assignment(
            None,
            frog_ast.Variable(fused_name),
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.ADD,
                frog_ast.Variable(exponent_name),
                frog_ast.Variable(offset_name),
            ),
        )

    try:
        new_methods: list[frog_ast.Method] = []
        for method in game.methods:
            if method is init:
                body = (
                    statements[:index]
                    + [
                        frog_ast.Assignment(
                            copy.deepcopy(zq),
                            frog_ast.Variable(exponent_name),
                            exponent,
                        )
                    ]
                    + [
                        _rewrite_statement(
                            s, {}, {name: power(frog_ast.Variable(exponent_name))}
                        )
                        for s in statements[index + 1 :]
                    ]
                )
                new_block = _before_exits(frog_ast.Block(body), set_fused)
            else:
                new_block = _track_offset(
                    method.block,
                    offset_name,
                    fused_name,
                    zq,
                    {
                        name: power(
                            frog_ast.BinaryOperation(
                                frog_ast.BinaryOperators.SUBTRACT,
                                frog_ast.Variable(fused_name),
                                frog_ast.Variable(offset_name),
                            )
                        )
                    },
                    set(taken),
                )
            new_methods.append(
                frog_ast.Method(copy.deepcopy(method.signature), new_block)
            )
    except _Unsupported:
        return None
    new_fields = [copy.deepcopy(f) for f in game.fields if f.name != name]
    new_fields.append(frog_ast.Field(copy.deepcopy(zq), fused_name, None))
    fused = frog_ast.Game(
        (game.name, copy.deepcopy(game.parameters), new_fields, new_methods)
    )
    where = _unbound_reference(fused, name)
    if where is not None:
        _note_unbound_reference(ctx, OffsetFusion.name, name, where)
        return None
    return fused


def _before_exits(
    block: frog_ast.Block, make: Callable[[], frog_ast.Statement]
) -> frog_ast.Block:
    """*block* with ``make()`` inserted before every return and at its end."""

    def walk(b: frog_ast.Block, top: bool) -> frog_ast.Block:
        out: list[frog_ast.Statement] = []
        for statement in b.statements:
            if isinstance(statement, frog_ast.ReturnStatement):
                out.append(make())
                out.append(statement)
            elif isinstance(statement, frog_ast.IfStatement):
                out.append(
                    frog_ast.IfStatement(
                        statement.conditions,
                        [walk(inner, False) for inner in statement.blocks],
                    )
                )
            elif isinstance(statement, frog_ast.Block):
                # A bare block (F-370(i)): a return inside it is an exit too.
                out.append(walk(statement, False))
            elif isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
                if (
                    SearchVisitor(
                        lambda n: isinstance(n, frog_ast.ReturnStatement)
                    ).visit(statement)
                    is not None
                ):
                    raise _Unsupported("return inside a loop")
                out.append(statement)
            else:
                out.append(statement)
        if top and not (out and isinstance(out[-1], frog_ast.ReturnStatement)):
            out.append(make())
        return frog_ast.Block(out)

    return walk(block, True)


def _track_offset(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    block: frog_ast.Block,
    offset: str,
    fused: str,
    zq: frog_ast.Type,
    reads: dict[str, frog_ast.Expression],
    taken: set[str],
    counter: Optional[itertools.count[int]] = None,
) -> frog_ast.Block:
    """Rewrite reads per *reads*, and keep ``fused - offset`` fixed across
    every write ``offset = w`` (``t = w; fused = fused + (t - offset);
    offset = t;``). Each temporary ``t`` is a name not in *taken* (the
    names of the game and the temporaries made so far), added to it."""
    if counter is None:
        counter = itertools.count()
    out: list[frog_ast.Statement] = []
    for statement in block.statements:
        if isinstance(
            statement, frog_ast.Assignment
        ) and statement.var == frog_ast.Variable(offset):
            temp = f"{offset}@next{next(counter)}"
            while temp in taken:
                temp = f"{offset}@next{next(counter)}"
            taken.add(temp)
            new_value = _replace_names(statement.value, reads)
            out.append(
                frog_ast.Assignment(
                    copy.deepcopy(zq), frog_ast.Variable(temp), new_value
                )
            )
            out.append(
                frog_ast.Assignment(
                    None,
                    frog_ast.Variable(fused),
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.ADD,
                        frog_ast.Variable(fused),
                        frog_ast.BinaryOperation(
                            frog_ast.BinaryOperators.SUBTRACT,
                            frog_ast.Variable(temp),
                            frog_ast.Variable(offset),
                        ),
                    ),
                )
            )
            out.append(
                frog_ast.Assignment(
                    None, frog_ast.Variable(offset), frog_ast.Variable(temp)
                )
            )
            continue
        if isinstance(statement, frog_ast.IfStatement):
            out.append(
                frog_ast.IfStatement(
                    [_replace_names(c, reads) for c in statement.conditions],
                    [
                        _track_offset(b, offset, fused, zq, reads, taken, counter)
                        for b in statement.blocks
                    ],
                )
            )
            continue
        if isinstance(statement, frog_ast.Block):
            # A bare block (F-370(i)): its writes of the offset are tracked
            # like the top level's.
            out.append(
                _track_offset(statement, offset, fused, zq, reads, taken, counter)
            )
            continue
        if _writes_of(statement, offset):
            # Only the statement kinds above keep ``fused - offset`` fixed;
            # any other write of the offset (in a loop, say) would not.
            raise _Unsupported("offset written inside a loop or other statement")
        out.append(_rewrite_statement(statement, {}, reads))
    return frog_ast.Block(out)


# ---------------------------------------------------------------------------
# Literal store-to-load forwarding for fields
# ---------------------------------------------------------------------------


class ForwardLiteralFieldWrite(TransformPass):
    """Forward a field's literal value to the reads that follow it.

    After ``f = c;`` (``f`` a field, ``c`` a literal), every read of ``f`` in
    the following statements of the same block, up to the first statement
    that may write ``f``, is replaced by ``c``. Exact: nothing between the
    write and those reads can change ``f`` (calls cannot read or write game
    fields). Lets a counter or offset reset in Initialize simplify away, e.g.
    ``D = 0; s = a + D;`` becomes ``D = 0; s = a + 0;``.

    A ``ModInt`` field holds ``0`` as the ring's zero, but the literal ``0``
    is an ``Int``, so it replaces a read only where the result keeps the
    ``ModInt`` type and value: as an operand of ``+``, or the right operand
    of ``-``, whose other operand is a ``ModInt`` that does not read the
    field (F-379). Elsewhere the ``Int`` would change the operation: ``D ^
    n`` would become the ``Int`` power ``0 ^ n`` (``0 ^ 0`` is the ``Int``
    1), and ``D + D`` the ``Int`` sum ``0 + 0``.
    """

    name = "Forward Literal Field Write"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        field_types = _field_types(game)
        changed = False
        new_methods: list[frog_ast.Method] = []
        for method in game.methods:
            names = {
                name: the_type
                for name, the_type in field_types.items()
                if name not in bound_names(method)
            }
            method_types = build_method_type_map(game, method, ctx.proof_let_types)
            try:
                block = _forward_literals(
                    method.block,
                    names,
                    _ZeroReadCheck(
                        method_types,
                        redeclared_names(game, method),
                        ctx,
                        method.signature.name,
                    ),
                )
            except _Unsupported:
                block = method.block
            if block is not method.block:
                changed = True
                new_methods.append(frog_ast.Method(method.signature, block))
            else:
                new_methods.append(method)
        if not changed:
            return game
        return frog_ast.Game((game.name, game.parameters, game.fields, new_methods))


def _literal_keeps_value(literal: frog_ast.Expression, the_type: frog_ast.Type) -> bool:
    """True if *literal* stored in a field of *the_type* reads back as itself:
    a Bool in a Bool, an integer in an Int, ``0`` in a ModInt (any other
    integer is reduced modulo the modulus), None in an optional. Bit-string
    literals are left alone (their length may be a mutable value)."""
    if isinstance(literal, frog_ast.Boolean):
        return isinstance(the_type, frog_ast.BoolType)
    if isinstance(literal, frog_ast.Integer):
        return isinstance(the_type, frog_ast.IntType) or (
            isinstance(the_type, frog_ast.ModIntType) and literal.num == 0
        )
    if isinstance(literal, frog_ast.NoneExpression):
        return isinstance(the_type, frog_ast.OptionalType)
    return False


class _ZeroReadCheck:
    """Where the literal ``0`` may replace a read of a ``ModInt`` field that
    holds zero (F-379): the literal is an ``Int``, so only where the result
    keeps the ``ModInt`` type and value."""

    def __init__(
        self,
        method_types: NameTypeMap,
        redeclared: set[str],
        ctx: PipelineContext,
        method_name: str,
    ) -> None:
        self.method_types = method_types
        self.redeclared = redeclared
        self.ctx = ctx
        self.method_name = method_name

    def _modint_operand(self, operand: frog_ast.Expression, name: str) -> bool:
        """True if *operand* is a ``ModInt`` that does not read *name*, typed
        by names that have one binding in the method."""
        names = _free_names(operand)
        if name in names or names & self.redeclared:
            return False
        return isinstance(
            expression_type(operand, self.method_types, self.ctx.proof_namespace),
            frog_ast.ModIntType,
        )

    def exact(self, statement: frog_ast.Statement, name: str) -> bool:
        """True if every read of *name* in *statement* is an operand of
        ``+``, or the right operand of ``-``, whose other operand is a
        ``ModInt`` that does not read *name*: ``a + 0`` and ``a - 0`` are
        ``a`` in the ring and as integers alike."""
        read = frog_ast.Variable(name)
        counts = {"reads": 0, "exact": 0}

        def visit(node: frog_ast.ASTNode) -> bool:
            if node == read:
                counts["reads"] += 1
            elif isinstance(node, frog_ast.BinaryOperation):
                left, right = node.left_expression, node.right_expression
                if node.operator == frog_ast.BinaryOperators.ADD:
                    if left == read and self._modint_operand(right, name):
                        counts["exact"] += 1
                    if right == read and self._modint_operand(left, name):
                        counts["exact"] += 1
                elif node.operator == frog_ast.BinaryOperators.SUBTRACT:
                    if right == read and self._modint_operand(left, name):
                        counts["exact"] += 1
            return False

        SearchVisitor(visit).visit(statement)
        return counts["reads"] == counts["exact"]

    def note(self, name: str, statement: frog_ast.Statement) -> None:
        self.ctx.near_misses.append(
            NearMiss(
                transform_name="Forward Literal Field Write",
                reason=(
                    f"The ModInt field '{name}' holds 0, but the literal 0 is "
                    f"an Int, so it is forwarded only into a statement whose "
                    f"every read of '{name}' is an operand of + (or the right "
                    f"operand of -) next to a ModInt operand that reads "
                    f"neither '{name}' nor a name bound twice; "
                    f"'{str(statement).strip()}' is kept"
                ),
                location=None,
                suggestion=None,
                variable=name,
                method=self.method_name,
            )
        )


def _forward_literals(
    block: frog_ast.Block,
    fields: dict[str, frog_ast.Type],
    zero_check: _ZeroReadCheck,
) -> frog_ast.Block:
    statements = list(block.statements)
    changed = False
    for index, statement in enumerate(statements):
        if not (
            isinstance(statement, frog_ast.Assignment)
            and statement.the_type is None
            and isinstance(statement.var, frog_ast.Variable)
            and statement.var.name in fields
            and _literal_keeps_value(statement.value, fields[statement.var.name])
        ):
            continue
        name = statement.var.name
        # Only 0 is forwarded for a ModInt field (_literal_keeps_value).
        ring_zero = isinstance(fields[name], frog_ast.ModIntType)
        end = index + 1
        while end < len(statements) and not reassigns_or_rebinds(
            {name}, statements[end]
        ):
            end += 1
        reads = {name: statement.value}
        for position in range(index + 1, end):
            if not _mentions(statements[position], name):
                continue
            if ring_zero and not zero_check.exact(statements[position], name):
                zero_check.note(name, statements[position])
                continue
            statements[position] = _rewrite_statement(statements[position], {}, reads)
            changed = True
    return frog_ast.Block(statements) if changed else block
