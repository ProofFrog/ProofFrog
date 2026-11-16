"""The parts of a statement run in the order they are written (F-372, F-397).

A call evaluates its arguments left to right, and so does every operator; a
statement evaluates its parts in the order they are written (the indices of
an element write before the value it stores). Two steps of game resolution
move code in front of the statement it comes from:

- the method inliner (:class:`visitors.InlineTransformer`) puts a callee's
  statements in front of the statement holding the call, and leaves the
  callee's returned expression in place of the call;
- the conditional-call rewrite (:mod:`conditional_calls`) puts the operands
  of a ``&&`` / ``||`` in front of the statement.

The moved code then runs before the parts of the statement written ahead of
it. That changes nothing unless the two touch the same state: a part written
earlier reads a variable the moved code writes (once ``challenger.Read()`` is
inlined into ``challenger.Read() + challenger.Inc()``, its returned
``challenger@c`` is read after ``Inc`` increments it), or it writes state the
moved code reads or writes (a challenger call left in the statement while the
reduction is resolved alone, in front of which a hoisted operand would run
another challenger call).

:meth:`EvaluationOrder.bind` binds each such part to a fresh typed variable,
left to right, in front of the statement before the code is moved: a read of
a variable the moved code writes, a call whose callee touches state the moved
code touches, or a short-circuit operation holding such a call. A bound
part moves ahead of the earlier parts left in place, so it counts as moved
code for them: the parts are examined from last to first, and a part that
conflicts with a part bound after it is bound too. A part touching no such
state stays where it is, so other canonical forms do not change. Draws
from types and calls of abstract primitives and of ``Function`` values
touch no state; the order of independent draws is unobservable, and a
draw that may not complete hides the state of every later step. A
``challenger`` call whose callee is not known reads and writes the
challenger's state.

:func:`order_calls_for_inlining` applies the rule to the call the inliner
takes next in each statement; :mod:`conditional_calls` applies it before it
hoists an operand.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable, Optional

from . import dependencies, frog_ast, visitors

MethodKey = tuple[str, str]
MethodLookup = dict[MethodKey, frog_ast.Method]


class UnorderedCallError(Exception):
    """A part of a statement evaluated before code the engine must move in
    front of the statement touches state that code touches, and it cannot be
    bound to a variable first: its type is unknown, or it is a call
    evaluated only under a short-circuit condition. The game is not
    resolved."""


def _state(owner: str) -> str:
    """The pseudo-variable standing for the state of *owner*'s module, read
    and written by a call whose body is not known. No FrogLang name has this
    form."""
    return f"@state:{owner}"


def method_call_key(node: frog_ast.ASTNode) -> Optional[MethodKey]:
    """``(object, method)`` when *node* is a call ``object.method(...)``."""
    if not isinstance(node, frog_ast.FuncCall):
        return None
    func = node.func
    if isinstance(func, frog_ast.FieldAccess) and isinstance(
        func.the_object, frog_ast.Variable
    ):
        return (func.the_object.name, func.name)
    return None


# The attribute holding the name each binder statement declares.
_BINDER_NAME = {
    frog_ast.VariableDeclaration: "name",
    frog_ast.NumericFor: "name",
    frog_ast.GenericFor: "var_name",
}


def declared_names(method: frog_ast.Method) -> set[str]:
    """The method's parameters and every name it declares (typed writes,
    bare declarations, loop binders): the callee's own variables. A written
    parameter is the callee's own copy, since the inliner binds it."""
    names = {param.name for param in method.signature.parameters}

    def collect(node: frog_ast.ASTNode) -> bool:
        binder = _BINDER_NAME.get(type(node))
        if binder is not None:
            names.add(getattr(node, binder))
        elif isinstance(node, frog_ast.DestructuringBinding):
            names.update(node.names)
        elif isinstance(
            node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            if node.the_type is not None and isinstance(node.var, frog_ast.Variable):
                names.add(node.var.name)
        return False

    visitors.SearchVisitor(collect).visit(method.block)
    return names


def written_names(node: frog_ast.ASTNode) -> set[str]:
    """Every name a statement in *node* writes: the base of each l-value (an
    element or tuple write included) and the exclusion set of each ``<-uniq``
    draw, which the draw inserts into."""
    names: set[str] = set()

    def add_target(target: frog_ast.ASTNode) -> None:
        if isinstance(target, frog_ast.Tuple):
            for value in target.values:
                add_target(value)
            return
        base = visitors.lvalue_base_name(target)
        # An l-value with no variable base is unknown: count it as a write
        # to a name no callee declares.
        names.add(base if base is not None else "")

    def collect(inner: frog_ast.ASTNode) -> bool:
        if isinstance(
            inner, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            add_target(inner.var)
        if isinstance(inner, frog_ast.UniqueSample) and inner.surface_form == "uniq":
            names.update(visitors.referenced_variable_names(inner.unique_set))
        if isinstance(inner, frog_ast.DestructuringBinding):
            names.update(inner.names)
        return False

    visitors.SearchVisitor(collect).visit(node)
    return names


def split_else_if(statement: frog_ast.IfStatement, index: int) -> frog_ast.IfStatement:
    """``if (C0) {B0} ... else if (Ci) {Bi} ...`` with the chain from ``Ci``
    on moved into an ``else`` block, so ``Ci`` is evaluated (and its calls
    run) only when ``C0`` to ``C(i-1)`` are false, as before."""
    nested = frog_ast.IfStatement(
        list(statement.conditions[index:]), list(statement.blocks[index:])
    )
    return frog_ast.IfStatement(
        list(statement.conditions[:index]),
        list(statement.blocks[:index]) + [frog_ast.Block([nested])],
    )


@dataclass(frozen=True)
class Footprint:
    """The names a piece of code may read and may write."""

    reads: frozenset[str] = frozenset()
    writes: frozenset[str] = frozenset()

    def __or__(self, other: Footprint) -> Footprint:
        return Footprint(self.reads | other.reads, self.writes | other.writes)

    def conflicts(self, other: Footprint) -> bool:
        """Whether running the two in the other order can change a value: one
        writes a name the other reads or writes."""
        return bool(self.writes & (other.reads | other.writes)) or bool(
            other.writes & self.reads
        )


class FootprintOracle:
    """Footprints of expressions and statements, through the bodies of the
    callees in *methods* (the inliner's lookup, plus while a reduction is
    resolved alone the methods of the challenger it is composed with)."""

    def __init__(self, methods: MethodLookup) -> None:
        self.methods = methods
        self.cache: dict[MethodKey, Footprint] = {}

    def callee(self, key: MethodKey) -> Footprint:
        """What inlining the body of *key* reads and writes outside the
        callee's own variables."""
        if key in self.cache:
            return self.cache[key]
        # A call cycle cannot be inlined; while one is explored, a callee met
        # again stands for its whole module.
        token = frozenset({_state(key[0])})
        self.cache[key] = Footprint(token, token)
        method = self.methods[key]
        declared = declared_names(method)
        body = self.of(method.block)
        result = Footprint(body.reads - declared, body.writes - declared)
        self.cache[key] = result
        return result

    def call_own(self, call: frog_ast.FuncCall) -> Footprint:
        """The footprint of *call*'s callee, its arguments excluded."""
        key = method_call_key(call)
        if key is None:
            return Footprint()
        if key in self.methods:
            return self.callee(key)
        if key[0] == "challenger":
            token = frozenset({_state("challenger")})
            return Footprint(token, token)
        # An abstract primitive's method touches no state of the game.
        return Footprint()

    def of(self, node: frog_ast.ASTNode) -> Footprint:
        """What evaluating *node* (an expression, a statement or a block) may
        read and write, its calls' callees included."""
        calls: list[frog_ast.FuncCall] = []

        def collect(inner: frog_ast.ASTNode) -> bool:
            if isinstance(inner, frog_ast.FuncCall):
                calls.append(inner)
            return False

        visitors.SearchVisitor(collect).visit(node)
        result = Footprint(
            frozenset(visitors.referenced_variable_names(node)),
            frozenset(written_names(node)),
        )
        for call in calls:
            result = result | self.call_own(call)
        return result


class Scope:
    """The types of the names in scope at a statement of a method: the game's
    fields, the method's parameters, then each enclosing block's
    declarations made so far. A proof ``let:`` type applies only to a name
    the game does not declare (:func:`visitors.with_proof_let_types`)."""

    def __init__(
        self,
        game: frog_ast.Game,
        method: frog_ast.Method,
        proof_let_types: Optional[visitors.NameTypeMap],
    ) -> None:
        self.outer: dict[str, frog_ast.Type] = {}
        for field in game.fields:
            self.outer[field.name] = field.type
        for param in method.signature.parameters:
            self.outer[param.name] = param.type
        self.proof_let_types = proof_let_types
        self.frames: list[dict[str, frog_ast.Type]] = [{}]

    def push(self) -> None:
        self.frames.append({})

    def pop(self) -> None:
        self.frames.pop()

    def declare(self, name: str, the_type: frog_ast.Type) -> None:
        self.frames[-1][name] = the_type

    def declare_statement(self, statement: frog_ast.Statement) -> None:
        """Record the name *statement* declares, if any."""
        if (
            isinstance(
                statement, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            )
            and statement.the_type is not None
            and isinstance(statement.var, frog_ast.Variable)
        ):
            self.declare(statement.var.name, statement.the_type)
        elif isinstance(statement, frog_ast.VariableDeclaration):
            self.declare(statement.name, statement.type)

    def declare_binder(self, loop: frog_ast.NumericFor | frog_ast.GenericFor) -> None:
        """Record the binder of *loop*, in scope in the loop's block."""
        if isinstance(loop, frog_ast.NumericFor):
            self.declare(loop.name, frog_ast.IntType())
        else:
            self.declare(loop.var_name, loop.var_type)

    def get(self, name: str) -> Optional[frog_ast.Type]:
        for frame in reversed(self.frames):
            if name in frame:
                return frame[name]
        if name in self.outer:
            return self.outer[name]
        if self.proof_let_types is not None:
            return self.proof_let_types.get(name)
        return None

    def type_map(self) -> visitors.NameTypeMap:
        """The names in scope as a :class:`visitors.NameTypeMap`."""
        result = visitors.NameTypeMap()
        for name, the_type in self.outer.items():
            result.set(name, the_type)
        for frame in self.frames:
            for name, the_type in frame.items():
                result.set(name, the_type)
        return visitors.with_proof_let_types(result, self.proof_let_types)


def map_nested_blocks(
    statement: frog_ast.Statement,
    rewrite: Callable[[frog_ast.Block], frog_ast.Block],
    scope: Scope,
) -> frog_ast.Statement:
    """*statement* with each block nested in it replaced by ``rewrite(block)``
    (a loop's binder declared in *scope* while its block is rewritten);
    *statement* itself when no block changes."""
    if isinstance(statement, frog_ast.IfStatement):
        blocks = [rewrite(block) for block in statement.blocks]
        if all(old is new for old, new in zip(statement.blocks, blocks)):
            return statement
        return frog_ast.IfStatement(list(statement.conditions), blocks)
    if isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
        scope.push()
        scope.declare_binder(statement)
        loop_block = rewrite(statement.block)
        scope.pop()
        if loop_block is statement.block:
            return statement
        loop = copy.copy(statement)
        loop.block = loop_block
        return loop
    if isinstance(statement, frog_ast.Block):
        return rewrite(statement)
    return statement


def _lvalue_parts(target: frog_ast.ASTNode) -> list[frog_ast.ASTNode]:
    """The expressions an l-value evaluates (its indices and slice bounds, in
    the order written); its base variable is written, not read."""
    if isinstance(target, frog_ast.ArrayAccess):
        return _lvalue_parts(target.the_array) + [target.index]
    if isinstance(target, frog_ast.Slice):
        return _lvalue_parts(target.the_array) + [target.start, target.end]
    if isinstance(target, frog_ast.FieldAccess):
        return _lvalue_parts(target.the_object)
    if isinstance(target, frog_ast.Tuple):
        return [part for value in target.values for part in _lvalue_parts(value)]
    return []


def evaluated_children(node: frog_ast.ASTNode) -> list[frog_ast.ASTNode]:
    """The parts *node* evaluates itself, in the order they are evaluated: no
    nested block, no type, no method name and no l-value base. Of an ``if``,
    every condition (the first is always evaluated; a later one only when
    the earlier ones are false)."""
    children: list[Optional[frog_ast.ASTNode]]
    if isinstance(node, frog_ast.IfStatement):
        children = list(node.conditions)
    elif isinstance(node, frog_ast.NumericFor):
        children = [node.start, node.end]
    elif isinstance(node, frog_ast.GenericFor):
        children = [node.over]
    elif isinstance(node, frog_ast.Assignment):
        children = [*_lvalue_parts(node.var), node.value]
    elif isinstance(node, frog_ast.Sample):
        children = [*_lvalue_parts(node.var)]
    elif isinstance(node, frog_ast.UniqueSample):
        children = [*_lvalue_parts(node.var), node.unique_set]
    elif isinstance(node, frog_ast.FuncCall):
        children = list(node.args)
        # The callee expression runs before the arguments, as the inliner
        # takes it: a `Function` value, or any expression yielding one (a
        # call returning a function, `challenger.GetH()(x)`). Only a method
        # name `obj.m` is not evaluated.
        if method_call_key(node) is None:
            children.insert(0, node.func)
    elif isinstance(node, (frog_ast.Block, frog_ast.VariableDeclaration)):
        children = []
    else:
        type_slots = visitors.TYPE_SLOTS.get(type(node), ())
        children = []
        # pylint: disable-next=protected-access
        for attr in visitors._child_fields(node):
            if attr in type_slots:
                continue
            value = getattr(node, attr)
            for item in value if isinstance(value, list) else [value]:
                children.append(item)
    return [
        child
        for child in children
        if isinstance(child, frog_ast.ASTNode) and not isinstance(child, frog_ast.Block)
    ]


def first_inlinable_call(
    node: frog_ast.ASTNode, lookup: MethodLookup
) -> Optional[frog_ast.FuncCall]:
    """The call :class:`visitors.InlineTransformer` takes first among the
    parts *node* evaluates itself: it takes a call before its arguments."""
    if isinstance(node, frog_ast.FuncCall) and method_call_key(node) in lookup:
        return node
    for child in evaluated_children(node):
        found = first_inlinable_call(child, lookup)
        if found is not None:
            return found
    return None


def _path(
    node: frog_ast.ASTNode, target: frog_ast.ASTNode
) -> Optional[list[tuple[frog_ast.ASTNode, int]]]:
    """The nodes from *node* down to *target* (found by identity), each with
    the position of the next one among its evaluated children."""
    if node is target:
        return []
    for index, child in enumerate(evaluated_children(node)):
        rest = _path(child, target)
        if rest is not None:
            return [(node, index)] + rest
    return None


@dataclass
class _Part:
    """A part of a statement evaluated before some target in it."""

    node: frog_ast.ASTNode
    # Evaluated only under a short-circuit condition that the statement
    # evaluates before it (the part sits in the right operand of a `&&` or
    # a Boolean `||` that also holds the target).
    conditional: bool


class _ReplaceNodes(visitors.Transformer):
    """Replaces given node objects (by identity), occurrence by occurrence in
    traversal order: an object occurring twice is two evaluations."""

    def __init__(self, pairs: list[tuple[frog_ast.ASTNode, frog_ast.ASTNode]]) -> None:
        self.pending: dict[int, list[frog_ast.ASTNode]] = {}
        for old, new in pairs:
            self.pending.setdefault(id(old), []).append(new)
        self.objects = {id(old): old for old, _ in pairs}

    def transform_ast_node(self, node: frog_ast.ASTNode) -> Optional[frog_ast.ASTNode]:
        queue = self.pending.get(id(node))
        if queue and self.objects[id(node)] is node:
            return queue.pop(0)
        return None


class EvaluationOrder:
    """Binds the parts of a statement evaluated before code that is about to
    be moved in front of it (module docstring)."""

    def __init__(
        self,
        oracle: FootprintOracle,
        proof_namespace: frog_ast.Namespace,
        taken: set[str],
    ) -> None:
        self.oracle = oracle
        self.proof_namespace = proof_namespace
        self.taken = taken

    def _type_of(
        self, expr: frog_ast.ASTNode, scope: Scope
    ) -> Optional[frog_ast.ASTNode]:
        key = method_call_key(expr)
        if key is not None and key in self.oracle.methods:
            return self.oracle.methods[key].signature.return_type
        if not isinstance(expr, frog_ast.Expression):
            return None
        return visitors.expression_type(expr, scope.type_map(), self.proof_namespace)

    def is_short_circuit(self, node: frog_ast.ASTNode, scope: Scope) -> bool:
        """Whether *node* evaluates its right operand only conditionally: a
        ``&&``, or an ``||`` not known to be a concatenation."""
        if not isinstance(node, frog_ast.BinaryOperation):
            return False
        if node.operator == frog_ast.BinaryOperators.AND:
            return True
        if node.operator != frog_ast.BinaryOperators.OR:
            return False
        return self.bool_or(node, scope) is not False

    def bool_or(self, node: frog_ast.BinaryOperation, scope: Scope) -> Optional[bool]:
        """True for a Boolean ``||``, False for a concatenation, None if
        unknown; either operand's type decides."""
        for operand in (node.left_expression, node.right_expression):
            if (
                isinstance(operand, frog_ast.BinaryOperation)
                and operand.operator == frog_ast.BinaryOperators.OR
            ):
                inner = self.bool_or(operand, scope)
                if inner is not None:
                    return inner
                continue
            the_type = self._type_of(operand, scope)
            if isinstance(the_type, frog_ast.BoolType):
                return True
            if isinstance(the_type, frog_ast.BitStringType):
                return False
        return None

    def locate(
        self, statement: frog_ast.Statement, target: frog_ast.ASTNode, scope: Scope
    ) -> tuple[list[_Part], int]:
        """The parts of *statement* evaluated before *target*, in evaluation
        order, and the index of the ``if`` condition holding *target* (0 for
        any other statement). For a later condition, the earlier conditions
        come first in the list (they are evaluated only in turn)."""
        # A call statement is an expression evaluated whole.
        roots = (
            [statement]
            if isinstance(statement, frog_ast.Expression)
            else evaluated_children(statement)
        )
        for index, root in enumerate(roots):
            path = _path(root, target)
            if path is None:
                continue
            parts = [_Part(node, False) for node in roots[:index]]
            conditional = False
            for node, position in path:
                children = evaluated_children(node)
                parts.extend(_Part(child, conditional) for child in children[:position])
                if position == len(children) - 1 and self.is_short_circuit(node, scope):
                    conditional = True
            if_index = index if isinstance(statement, frog_ast.IfStatement) else 0
            return parts, if_index
        raise UnorderedCallError(
            f"cannot tell what '{statement}' evaluates before '{target}'"
        )

    def pieces(
        self, node: frog_ast.ASTNode, moved: Footprint, scope: Scope
    ) -> tuple[list[frog_ast.ASTNode], Footprint]:
        """The smallest parts of *node* to bind so that the rest of it touches
        nothing *moved* touches, in evaluation order: a variable *moved*
        writes, a call whose callee conflicts with *moved*, or a short-circuit
        operation whose right operand holds such a call (binding the call
        alone would evaluate it unconditionally).

        A bound piece moves in front of everything evaluated before it that
        stays in place, so it counts as moved code for those parts: the
        parts are examined from last to first, and *moved* grows by the
        footprint of each piece found. Returns the pieces and the grown
        footprint."""
        if not self.oracle.of(node).conflicts(moved):
            return [], moved
        if isinstance(node, frog_ast.Variable):
            return [node], moved | self.oracle.of(node)
        if isinstance(node, frog_ast.FuncCall) and self.oracle.call_own(node).conflicts(
            moved
        ):
            return [node], moved | self.oracle.of(node)
        if isinstance(node, frog_ast.BinaryOperation) and self.is_short_circuit(
            node, scope
        ):
            right, after_right = self.pieces(node.right_expression, moved, scope)
            if any(not isinstance(piece, frog_ast.Variable) for piece in right):
                return [node], moved | self.oracle.of(node)
            left, after_left = self.pieces(node.left_expression, after_right, scope)
            return left + right, after_left
        found: list[frog_ast.ASTNode] = []
        for child in reversed(evaluated_children(node)):
            child_pieces, moved = self.pieces(child, moved, scope)
            found = child_pieces + found
        return found, moved

    def conflicting(
        self, parts: list[_Part], moved: Footprint, scope: Scope
    ) -> list[frog_ast.ASTNode]:
        """The pieces of *parts* to bind (see :meth:`pieces`), in evaluation
        order. The parts are examined from last to first: a part before a
        bound piece that conflicts with it is bound too, so binding keeps
        their order. A piece other than a variable read must be evaluated
        whenever the statement is, or binding it in front of the statement
        would evaluate it more often."""
        found: list[frog_ast.ASTNode] = []
        for part in reversed(parts):
            part_pieces, moved = self.pieces(part.node, moved, scope)
            for piece in part_pieces:
                if part.conditional and not isinstance(piece, frog_ast.Variable):
                    raise UnorderedCallError(
                        f"cannot keep '{piece}' ahead of the code moved in front"
                        " of its statement: it is evaluated only conditionally"
                    )
            found = part_pieces + found
        return found

    def fresh(self, base: str) -> str:
        """A name ``<base><k>`` no binding of the game has."""
        index = 0
        while f"{base}{index}" in self.taken:
            index += 1
        name = f"{base}{index}"
        self.taken.add(name)
        return name

    def bind(
        self,
        statement: frog_ast.Statement,
        pieces: list[frog_ast.ASTNode],
        scope: Scope,
        base: str,
    ) -> list[frog_ast.Statement]:
        """Typed bindings of *pieces*, in order, followed by *statement* with
        each piece replaced by its variable."""
        bindings: list[frog_ast.Statement] = []
        pairs: list[tuple[frog_ast.ASTNode, frog_ast.ASTNode]] = []
        for piece in pieces:
            if isinstance(piece, frog_ast.Variable):
                the_type: Optional[frog_ast.ASTNode] = scope.get(piece.name)
            elif isinstance(piece, frog_ast.BinaryOperation):
                # A short-circuit operation: `&&`, or an `||` that is Boolean.
                is_bool = (
                    piece.operator == frog_ast.BinaryOperators.AND
                    or self.bool_or(piece, scope) is True
                )
                the_type = frog_ast.BoolType() if is_bool else None
            else:
                the_type = self._type_of(piece, scope)
            if not isinstance(the_type, frog_ast.Type) or isinstance(
                the_type, frog_ast.Void
            ):
                raise UnorderedCallError(
                    f"cannot keep '{piece}' ahead of the code moved in front of"
                    " its statement: its type is unknown"
                )
            assert isinstance(piece, frog_ast.Expression)
            name = self.fresh(base)
            bindings.append(
                frog_ast.Assignment(
                    copy.deepcopy(the_type), frog_ast.Variable(name), piece
                )
            )
            pairs.append((piece, frog_ast.Variable(name)))
            scope.declare(name, the_type)
        return bindings + [_ReplaceNodes(pairs).transform(statement)]


def _callee_name(call: frog_ast.FuncCall) -> str:
    key = method_call_key(call)
    assert key is not None
    return f"{key[0]}.{key[1]}"


class _InliningOrder:
    """Walks one game, binding in each statement what must run before the
    call the inliner takes there next."""

    def __init__(
        self,
        game: frog_ast.Game,
        lookup: MethodLookup,
        order: EvaluationOrder,
        proof_let_types: Optional[visitors.NameTypeMap],
    ) -> None:
        self.game = game
        self.lookup = lookup
        self.order = order
        self.proof_let_types = proof_let_types
        self.scope: Optional[Scope] = None

    def method(self, method: frog_ast.Method) -> frog_ast.Method:
        self.scope = Scope(self.game, method, self.proof_let_types)
        block = self.block(method.block)
        if block is method.block:
            return method
        new_method = copy.copy(method)
        new_method.block = block
        return new_method

    def block(self, block: frog_ast.Block) -> frog_ast.Block:
        assert self.scope is not None
        self.scope.push()
        statements: list[frog_ast.Statement] = []
        changed = False
        for statement in block.statements:
            for new_statement in self.statement(statement):
                nested = self.nested(new_statement)
                changed = changed or nested is not statement
                statements.append(nested)
                self.scope.declare_statement(nested)
        self.scope.pop()
        return frog_ast.Block(statements) if changed else block

    def nested(self, statement: frog_ast.Statement) -> frog_ast.Statement:
        """*statement* with the blocks nested in it walked."""
        assert self.scope is not None
        return map_nested_blocks(statement, self.block, self.scope)

    def statement(self, statement: frog_ast.Statement) -> list[frog_ast.Statement]:
        """*statement*, preceded by the bindings the next inlining in it
        needs; or, when the call sits in an ``else if`` condition and a
        condition before it conflicts, the ``if`` with that ``else if``
        moved into an ``else`` block (the walk then reaches the call there)."""
        assert self.scope is not None
        call = first_inlinable_call(statement, self.lookup)
        if call is None:
            return [statement]
        moved = self.order.oracle.of(call)
        parts, if_index = self.order.locate(statement, call, self.scope)
        if if_index > 0:
            assert isinstance(statement, frog_ast.IfStatement)
            if any(self.order.oracle.of(part.node).conflicts(moved) for part in parts):
                return [split_else_if(statement, if_index)]
            return [statement]
        pieces = self.order.conflicting(parts, moved, self.scope)
        if not pieces:
            return [statement]
        return self.order.bind(
            statement, pieces, self.scope, f"{_callee_name(call)}@prior@"
        )


def challenger_lookup(challenger: Optional[frog_ast.Game]) -> MethodLookup:
    """The methods of *challenger* keyed as a reduction calls them."""
    if challenger is None:
        return {}
    return {
        ("challenger", method.signature.name): method for method in challenger.methods
    }


def game_taken_names(game: frog_ast.Game) -> set[str]:
    """Every name *game* binds or mentions, so a new binding avoids them."""
    return dependencies.game_value_names(game) | visitors.referenced_variable_names(
        game
    )


def order_calls_for_inlining(
    game: frog_ast.Game,
    lookup: MethodLookup,
    proof_namespace: frog_ast.Namespace,
    proof_let_types: Optional[visitors.NameTypeMap] = None,
    challenger: Optional[frog_ast.Game] = None,
) -> frog_ast.Game:
    """*game* with, in each statement, every part evaluated before the call
    the inliner takes there next bound to a variable in front of the
    statement where it touches state the callee touches (module docstring);
    *game* itself when there is none. *lookup* is the inliner's method
    lookup; *challenger* is the challenger a reduction resolved alone will be
    composed with, whose methods are known but not inlined."""
    methods = challenger_lookup(challenger)
    methods.update(lookup)
    order = EvaluationOrder(
        FootprintOracle(methods), proof_namespace, game_taken_names(game)
    )
    walker = _InliningOrder(game, lookup, order, proof_let_types)
    new_methods = [walker.method(method) for method in game.methods]
    if all(old is new for old, new in zip(game.methods, new_methods)):
        return game
    new_game = copy.copy(game)
    new_game.methods = new_methods
    return new_game
