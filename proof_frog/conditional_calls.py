"""Calls that are evaluated only conditionally keep their condition (F-372).

``&&`` and ``||`` on ``Bool`` evaluate their right operand only when the left
operand does not decide the result, and an ``else if`` condition is evaluated
only when every earlier condition is false. The method inliner
(:class:`visitors.InlineTransformer`) puts a callee's statements in front of
the statement that holds the call, so a call in one of these positions would
run on traces where it is never evaluated. That changes nothing when the
callee's body has no effect (it draws only from types and reads state), but
it is wrong when it has one: a draw whose domain may be empty (it may not
complete, which the adversary observes) or a write to a variable outside the
callee (a challenger field, an exclusion set a ``<-uniq`` draw inserts into).

:func:`make_conditional_calls_explicit` rewrites each such position into
explicit control flow before the inliner reaches the call:

- ``if (C0) {B0} else if (C1) {B1} ...``, with such a call in ``C1``, becomes
  ``if (C0) {B0} else { if (C1) {B1} ... }``;
- ``return L && R;`` becomes ``if (L) { return R; } return false;`` and
  ``return L || R;`` becomes ``if (L) { return true; } return R;``;
- any other ``L && R`` (``L || R``) becomes ``Bool t = L; if (t) { t = R; }``
  (``if (!t)``) in front of the statement, which then reads ``t``.

Only a position whose right operand makes such a call is rewritten, so every
other call is inlined exactly as before. A position is rewritten only when
its statement evaluates no inlinable or ``challenger`` call before it: the
inliner takes that earlier call first, so the effects keep their order.
"""

from __future__ import annotations

import copy
from typing import Optional

from . import dependencies, frog_ast, visitors

MethodKey = tuple[str, str]
MethodLookup = dict[MethodKey, frog_ast.Method]


class UntypedConditionalCallError(Exception):
    """An ``||`` whose right operand makes a call with an effect, and whose
    operand types are unknown, so it may be a short-circuit ``||`` on
    ``Bool`` or a concatenation of bit strings. Inlining the call either way
    could be wrong, so the game is not resolved."""


def _method_call(node: frog_ast.ASTNode) -> Optional[MethodKey]:
    """``(object, method)`` when *node* is a call ``object.method(...)``."""
    if not isinstance(node, frog_ast.FuncCall):
        return None
    func = node.func
    if isinstance(func, frog_ast.FieldAccess) and isinstance(
        func.the_object, frog_ast.Variable
    ):
        return (func.the_object.name, func.name)
    return None


def _callee_key(node: frog_ast.ASTNode, lookup: MethodLookup) -> Optional[MethodKey]:
    """The lookup key of *node* when it is a call the inliner inlines."""
    key = _method_call(node)
    return key if key in lookup else None


def _orders_effects(node: frog_ast.ASTNode, lookup: MethodLookup) -> bool:
    """True when *node* is a call whose place among the effects of a
    statement matters: one the inliner inlines, or a ``challenger`` call
    (inlined once the reduction is composed)."""
    key = _method_call(node)
    return key is not None and (key in lookup or key[0] == "challenger")


# The attribute holding the name each binder statement declares.
_BINDER_NAME = {
    frog_ast.VariableDeclaration: "name",
    frog_ast.NumericFor: "name",
    frog_ast.GenericFor: "var_name",
}


def _declared_names(method: frog_ast.Method) -> set[str]:
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


def _written_names(block: frog_ast.Block) -> set[str]:
    """Every name a statement of *block* writes: the base of each l-value
    (an element or tuple write included) and the exclusion set of each
    ``<-uniq`` draw, which the draw inserts into."""
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

    def collect(node: frog_ast.ASTNode) -> bool:
        if isinstance(
            node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            add_target(node.var)
        if isinstance(node, frog_ast.UniqueSample) and node.surface_form == "uniq":
            names.update(visitors.referenced_variable_names(node.unique_set))
        if isinstance(node, frog_ast.DestructuringBinding):
            names.update(node.names)
        return False

    visitors.SearchVisitor(collect).visit(block)
    return names


class _EffectOracle:
    """Decides, once per callee, whether inlining it has an effect."""

    def __init__(
        self,
        game: frog_ast.Game,
        lookup: MethodLookup,
        proof_namespace: frog_ast.Namespace,
    ) -> None:
        self.game = game
        self.lookup = lookup
        self.proof_namespace = proof_namespace
        self.cache: dict[MethodKey, bool] = {}

    def _module_fields(self, owner: str) -> set[str]:
        """The fields holding runtime values that the callee's body can name:
        a scheme instance's own fields, or the challenger's fields (renamed
        ``challenger@<name>`` in the composed game). A ``Set`` alias field
        (``Set Key = BitString<n>;``) names a type."""
        fields: list[frog_ast.Field] = []
        if owner == "challenger":
            fields = self.game.fields
        else:
            instance = self.proof_namespace.get(owner)
            if isinstance(instance, (frog_ast.Scheme, frog_ast.Primitive)):
                fields = instance.fields
        return {
            field.name
            for field in fields
            if not (
                isinstance(field.type, frog_ast.SetType)
                and field.type.parameterization is None
            )
        }

    def has_effect(self, key: MethodKey) -> bool:
        if key in self.cache:
            return self.cache[key]
        # A call cycle cannot be inlined anyway; while one is explored, a
        # callee met again counts as having an effect (the safe answer).
        self.cache[key] = True
        method = self.lookup[key]
        declared = _declared_names(method)
        value_names = declared | self._module_fields(key[0])
        effect = (
            dependencies.may_not_complete(method.block, value_names)
            or bool(_written_names(method.block) - declared)
            or self.makes_effectful_call(method.block)
        )
        self.cache[key] = effect
        return effect

    def makes_effectful_call(self, node: frog_ast.ASTNode) -> bool:
        """True when *node* contains a call whose inlined body has an
        effect."""

        def effectful(inner: frog_ast.ASTNode) -> bool:
            key = _callee_key(inner, self.lookup)
            return key is not None and self.has_effect(key)

        return visitors.SearchVisitor(effectful).visit(node) is not None


class _SiteFinder:
    """Finds the first ``&&`` / ``||`` of a statement, in the inliner's
    traversal order, whose right operand makes a call with an effect."""

    def __init__(
        self,
        oracle: _EffectOracle,
        type_map: visitors.NameTypeMap,
        proof_namespace: frog_ast.Namespace,
    ) -> None:
        self.oracle = oracle
        self.type_map = type_map
        self.proof_namespace = proof_namespace
        self.seen_call = False
        self.deferred = False

    def _bool_operand(self, expr: frog_ast.Expression) -> Optional[bool]:
        """True if *expr* is a ``Bool``, False if it is a bit string, None if
        its type is unknown."""
        if (
            isinstance(expr, frog_ast.BinaryOperation)
            and expr.operator == frog_ast.BinaryOperators.OR
        ):
            return self._bool_or(expr)
        the_type: Optional[frog_ast.ASTNode] = visitors.expression_type(
            expr, self.type_map, self.proof_namespace
        )
        key = _callee_key(expr, self.oracle.lookup)
        if the_type is None and key is not None:
            the_type = self.oracle.lookup[key].signature.return_type
        if isinstance(the_type, frog_ast.BoolType):
            return True
        if isinstance(the_type, frog_ast.BitStringType):
            return False
        return None

    def _bool_or(self, expr: frog_ast.BinaryOperation) -> Optional[bool]:
        """Whether an ``||`` is the Boolean one (both operands have one
        type, so either operand decides)."""
        left = self._bool_operand(expr.left_expression)
        right = self._bool_operand(expr.right_expression)
        if left is True or right is True:
            return True
        if left is False or right is False:
            return False
        return None

    def _is_site(self, node: frog_ast.ASTNode) -> bool:
        if not (
            isinstance(node, frog_ast.BinaryOperation)
            and node.operator
            in (frog_ast.BinaryOperators.AND, frog_ast.BinaryOperators.OR)
            and self.oracle.makes_effectful_call(node.right_expression)
        ):
            return False
        if node.operator == frog_ast.BinaryOperators.AND:
            return True
        is_bool = self._bool_or(node)
        if is_bool is None:
            raise UntypedConditionalCallError(
                f"cannot tell whether '{node}' is a Boolean '||' (whose right "
                "operand is evaluated only when the left one is false) or a "
                "concatenation, and its right operand makes a call with an "
                "effect"
            )
        return is_bool

    def find(self, node: frog_ast.ASTNode) -> Optional[frog_ast.BinaryOperation]:
        """The first site in *node*, or None. Sets ``deferred`` when the
        first site comes after a call that orders effects."""
        if self.deferred:
            return None
        if self._is_site(node):
            if self.seen_call:
                self.deferred = True
                return None
            assert isinstance(node, frog_ast.BinaryOperation)
            return node
        # pylint: disable-next=protected-access
        for attr in visitors._child_fields(node):
            child = getattr(node, attr)
            children = child if isinstance(child, list) else [child]
            for item in children:
                if isinstance(item, frog_ast.ASTNode) and not isinstance(
                    item, frog_ast.Block
                ):
                    found = self.find(item)
                    if found is not None or self.deferred:
                        return found
        if _orders_effects(node, self.oracle.lookup):
            self.seen_call = True
        return None


def _own_expressions(statement: frog_ast.Statement) -> list[frog_ast.ASTNode]:
    """The parts of *statement* it evaluates itself, in the inliner's
    traversal order (nested blocks excluded; of an ``if``, only the first
    condition, since an ``else if`` condition is split off first)."""
    if isinstance(statement, frog_ast.IfStatement):
        return [statement.conditions[0]]
    if isinstance(statement, frog_ast.NumericFor):
        return [statement.start, statement.end]
    if isinstance(statement, frog_ast.GenericFor):
        return [statement.over]
    if isinstance(statement, (frog_ast.Block, frog_ast.VariableDeclaration)):
        return []
    return [statement]


class _Rewriter:
    """Rewrites one game's conditional sites (see the module docstring)."""

    def __init__(
        self,
        game: frog_ast.Game,
        lookup: MethodLookup,
        proof_namespace: frog_ast.Namespace,
        proof_let_types: Optional[visitors.NameTypeMap],
    ) -> None:
        self.game = game
        self.lookup = lookup
        self.proof_namespace = proof_namespace
        self.proof_let_types = proof_let_types
        self.oracle = _EffectOracle(game, lookup, proof_namespace)
        self.taken = dependencies.game_value_names(
            game
        ) | visitors.referenced_variable_names(game)
        self.type_map = visitors.NameTypeMap()

    def _fresh(self, site: frog_ast.BinaryOperation) -> str:
        """A name for the temporary, after the first call in the site's
        right operand that has an effect (``P.Pick@cond0``)."""
        keys: list[MethodKey] = []

        def effectful(node: frog_ast.ASTNode) -> bool:
            key = _callee_key(node, self.lookup)
            if key is not None and self.oracle.has_effect(key):
                keys.append(key)
                return True
            return False

        visitors.SearchVisitor(effectful).visit(site.right_expression)
        base = f"{keys[0][0]}.{keys[0][1]}@cond"
        index = 0
        while f"{base}{index}" in self.taken:
            index += 1
        name = f"{base}{index}"
        self.taken.add(name)
        return name

    def rewrite_method(self, method: frog_ast.Method) -> frog_ast.Method:
        self.type_map = visitors.build_method_type_map(
            self.game, method, self.proof_let_types
        )
        new_block = self._rewrite_block(method.block)
        if new_block is method.block:
            return method
        new_method = copy.copy(method)
        new_method.block = new_block
        return new_method

    def _rewrite_block(self, block: frog_ast.Block) -> frog_ast.Block:
        new_statements: list[frog_ast.Statement] = []
        changed = False
        for statement in block.statements:
            inner = self._rewrite_nested(statement)
            replacement = self._rewrite_statement(inner)
            if replacement is None:
                new_statements.append(inner)
                changed = changed or inner is not statement
            else:
                new_statements.extend(replacement)
                changed = True
        if not changed:
            return block
        return frog_ast.Block(new_statements)

    def _rewrite_nested(self, statement: frog_ast.Statement) -> frog_ast.Statement:
        """*statement* with the blocks nested in it rewritten."""
        if isinstance(statement, frog_ast.IfStatement):
            blocks = [self._rewrite_block(block) for block in statement.blocks]
            if all(old is new for old, new in zip(statement.blocks, blocks)):
                return statement
            return frog_ast.IfStatement(list(statement.conditions), blocks)
        if isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
            loop_block = self._rewrite_block(statement.block)
            if loop_block is statement.block:
                return statement
            loop = copy.copy(statement)
            loop.block = loop_block
            return loop
        if isinstance(statement, frog_ast.Block):
            return self._rewrite_block(statement)
        return statement

    def _rewrite_statement(
        self, statement: frog_ast.Statement
    ) -> Optional[list[frog_ast.Statement]]:
        """The statements replacing *statement*, or None to keep it."""
        if isinstance(statement, frog_ast.IfStatement):
            for index in range(1, len(statement.conditions)):
                if self.oracle.makes_effectful_call(statement.conditions[index]):
                    return [_split_else_if(statement, index)]
        finder = _SiteFinder(self.oracle, self.type_map, self.proof_namespace)
        site: Optional[frog_ast.BinaryOperation] = None
        for part in _own_expressions(statement):
            site = finder.find(part)
            if site is not None or finder.deferred:
                break
        if site is None:
            return None
        is_and = site.operator == frog_ast.BinaryOperators.AND
        if (
            isinstance(statement, frog_ast.ReturnStatement)
            and statement.expression is site
        ):
            if is_and:
                return [
                    frog_ast.IfStatement(
                        [site.left_expression],
                        [
                            frog_ast.Block(
                                [frog_ast.ReturnStatement(site.right_expression)]
                            )
                        ],
                    ),
                    frog_ast.ReturnStatement(frog_ast.Boolean(False)),
                ]
            return [
                frog_ast.IfStatement(
                    [site.left_expression],
                    [
                        frog_ast.Block(
                            [frog_ast.ReturnStatement(frog_ast.Boolean(True))]
                        )
                    ],
                ),
                frog_ast.ReturnStatement(site.right_expression),
            ]
        temp = self._fresh(site)
        guard: frog_ast.Expression = frog_ast.Variable(temp)
        if not is_and:
            guard = frog_ast.UnaryOperation(frog_ast.UnaryOperators.NOT, guard)
        return [
            frog_ast.Assignment(
                frog_ast.BoolType(), frog_ast.Variable(temp), site.left_expression
            ),
            frog_ast.IfStatement(
                [guard],
                [
                    frog_ast.Block(
                        [
                            frog_ast.Assignment(
                                None, frog_ast.Variable(temp), site.right_expression
                            )
                        ]
                    )
                ],
            ),
            _ReplaceFirst(site, frog_ast.Variable(temp)).transform(statement),
        ]


class _ReplaceFirst(visitors.Transformer):
    """Replaces the first occurrence of one node (by identity, in traversal
    order, the order :class:`_SiteFinder` searches in) and no other: a
    second occurrence of the same object is a second evaluation."""

    def __init__(
        self, search_for: frog_ast.ASTNode, replace_with: frog_ast.ASTNode
    ) -> None:
        self.search_for = search_for
        self.replace_with = replace_with
        self.done = False

    def transform_ast_node(self, node: frog_ast.ASTNode) -> Optional[frog_ast.ASTNode]:
        if not self.done and node is self.search_for:
            self.done = True
            return self.replace_with
        return None


def _split_else_if(statement: frog_ast.IfStatement, index: int) -> frog_ast.IfStatement:
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


def make_conditional_calls_explicit(
    game: frog_ast.Game,
    lookup: MethodLookup,
    proof_namespace: frog_ast.Namespace,
    proof_let_types: Optional[visitors.NameTypeMap] = None,
) -> frog_ast.Game:
    """*game* with every conditionally evaluated call that has an effect
    given explicit control flow (module docstring); *game* itself when there
    is none. *lookup* is the inliner's method lookup."""
    rewriter = _Rewriter(game, lookup, proof_namespace, proof_let_types)
    methods = [rewriter.rewrite_method(method) for method in game.methods]
    if all(old is new for old, new in zip(game.methods, methods)):
        return game
    new_game = copy.copy(game)
    new_game.methods = methods
    return new_game
