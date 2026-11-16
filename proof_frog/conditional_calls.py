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
other call is inlined exactly as before. The statements a rewrite produces
are rewritten in turn before the inliner runs, so nested positions
(``a && (b || f(x))``) and the first condition of an ``if`` whose
``else if`` was split off are covered too. A position is rewritten only when
its statement evaluates no call before it that the inliner inlines in this
pass: the inliner takes that earlier call first, so the effects keep their
order. (A ``challenger`` call counts only once the reduction is composed;
see :func:`_inliner_takes_first`.)

The temporary form moves ``L`` and ``R`` in front of the statement, ahead of
the parts of the statement written before the position. Each such part that
touches state ``L`` or ``R`` touches is bound to a variable in front of them
first (:mod:`evaluation_order`, F-397's rule): while a reduction is resolved
alone, a ``challenger`` call written before the position runs before a
``challenger`` call in ``L`` (F-372's second review). While a reduction is
resolved alone, the methods of the challenger it will be composed with are
known (*challenger*), so a challenger call with an effect in a conditional
position is rewritten then, and footprints see the challenger's state.
"""

from __future__ import annotations

import copy
from typing import Optional

from . import dependencies, frog_ast, visitors
from .evaluation_order import (
    EvaluationOrder,
    FootprintOracle,
    MethodKey,
    MethodLookup,
    Scope,
    challenger_lookup,
    declared_names,
    game_taken_names,
    map_nested_blocks,
    method_call_key,
    split_else_if,
    written_names,
)


class UntypedConditionalCallError(Exception):
    """An ``||`` whose right operand makes a call with an effect, and whose
    operand types are unknown, so it may be a short-circuit ``||`` on
    ``Bool`` or a concatenation of bit strings. Inlining the call either way
    could be wrong, so the game is not resolved."""


def _callee_key(node: frog_ast.ASTNode, lookup: MethodLookup) -> Optional[MethodKey]:
    """The key of *node* when it is a call of a method in *lookup*."""
    key = method_call_key(node)
    return key if key in lookup else None


def _inliner_takes_first(node: frog_ast.ASTNode, lookup: MethodLookup) -> bool:
    """True when *node* is a call the inliner takes in this pass, before any
    call that comes after it in its statement.

    A ``challenger`` call qualifies only once the reduction is composed (its
    methods are then in *lookup*). While a reduction is resolved alone, the
    inliner passes over it and takes the reduction's own calls after it, so
    waiting for it would leave a conditional call to be inlined
    unconditionally. Rewriting the position then puts the call's body in
    front of the challenger call, where the inliner already puts the body
    of every unconditional call the reduction makes after one; the
    challenger's variables are its own and cannot be the reduction's."""
    return _callee_key(node, lookup) is not None


class _EffectOracle:
    """Decides, once per callee, whether inlining it has an effect."""

    def __init__(
        self,
        game: frog_ast.Game,
        lookup: MethodLookup,
        proof_namespace: frog_ast.Namespace,
        challenger: Optional[frog_ast.Game] = None,
    ) -> None:
        self.game = game
        # The callees whose bodies are known: the inliner's, plus the
        # challenger's while a reduction is resolved alone.
        self.methods = challenger_lookup(challenger)
        self.methods.update(lookup)
        self.challenger = challenger
        self.proof_namespace = proof_namespace
        self.cache: dict[MethodKey, bool] = {}

    def _module_fields(self, owner: str) -> set[str]:
        """The fields holding runtime values that the callee's body can name:
        a scheme instance's own fields, or the challenger's fields (renamed
        ``challenger@<name>`` in the composed game). A ``Set`` alias field
        (``Set Key = BitString<n>;``) names a type."""
        fields: list[frog_ast.Field] = []
        prefix = ""
        if owner == "challenger" and self.challenger is not None:
            # Not composed yet: the challenger's methods already read its
            # fields as `challenger@<name>`, its field list does not.
            fields = self.challenger.fields
            prefix = "challenger@"
        elif owner == "challenger":
            fields = self.game.fields
        else:
            instance = self.proof_namespace.get(owner)
            if isinstance(instance, (frog_ast.Scheme, frog_ast.Primitive)):
                fields = instance.fields
        return {
            prefix + field.name
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
        method = self.methods[key]
        declared = declared_names(method)
        value_names = declared | self._module_fields(key[0])
        effect = (
            dependencies.may_not_complete(method.block, value_names)
            or bool(written_names(method.block) - declared)
            or self.makes_effectful_call(method.block)
        )
        self.cache[key] = effect
        return effect

    def makes_effectful_call(self, node: frog_ast.ASTNode) -> bool:
        """True when *node* contains a call whose inlined body has an
        effect."""

        def effectful(inner: frog_ast.ASTNode) -> bool:
            key = _callee_key(inner, self.methods)
            return key is not None and self.has_effect(key)

        return visitors.SearchVisitor(effectful).visit(node) is not None


class _SiteFinder:
    """Finds the first ``&&`` / ``||`` of a statement, in the inliner's
    traversal order, whose right operand makes a call with an effect."""

    def __init__(
        self,
        oracle: _EffectOracle,
        inlinable: MethodLookup,
        order: EvaluationOrder,
        scope: Scope,
    ) -> None:
        self.oracle = oracle
        self.inlinable = inlinable
        self.order = order
        self.scope = scope
        self.seen_call = False
        self.deferred = False

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
        is_bool = self.order.bool_or(node, self.scope)
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
        if _inliner_takes_first(node, self.inlinable):
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
        challenger: Optional[frog_ast.Game],
    ) -> None:
        self.game = game
        self.lookup = lookup
        self.proof_namespace = proof_namespace
        self.proof_let_types = proof_let_types
        self.oracle = _EffectOracle(game, lookup, proof_namespace, challenger)
        self.taken = game_taken_names(game)
        self.order = EvaluationOrder(
            FootprintOracle(self.oracle.methods), proof_namespace, self.taken
        )
        self.scope: Optional[Scope] = None

    def _effectful_callee(self, site: frog_ast.BinaryOperation) -> str:
        """The first call in the site's right operand that has an effect, as
        ``object.method``: the base of the names the rewrite makes."""
        keys: list[MethodKey] = []

        def effectful(node: frog_ast.ASTNode) -> bool:
            key = _callee_key(node, self.oracle.methods)
            if key is not None and self.oracle.has_effect(key):
                keys.append(key)
                return True
            return False

        visitors.SearchVisitor(effectful).visit(site.right_expression)
        return f"{keys[0][0]}.{keys[0][1]}"

    def _fresh(self, callee: str) -> str:
        """A name for the temporary (``P.Pick@cond@0``). The two ``@`` keep it
        apart from the names the inliner gives a callee's locals
        (``P.Pick@cond0`` for a local ``cond``)."""
        name = self.order.fresh(f"{callee}@cond@")
        # The rewritten statement reads the temporary where the site was, so
        # a site found in it later can still tell a Boolean `||` by it.
        assert self.scope is not None
        self.scope.declare(name, frog_ast.BoolType())
        return name

    def rewrite_method(self, method: frog_ast.Method) -> frog_ast.Method:
        self.scope = Scope(self.game, method, self.proof_let_types)
        new_block = self._rewrite_block(method.block)
        if new_block is method.block:
            return method
        new_method = copy.copy(method)
        new_method.block = new_block
        return new_method

    def _rewrite_block(self, block: frog_ast.Block) -> frog_ast.Block:
        assert self.scope is not None
        self.scope.push()
        new_statements: list[frog_ast.Statement] = []
        changed = False
        for statement in block.statements:
            rewritten = self._rewrite_all(statement)
            new_statements.extend(rewritten)
            for new_statement in rewritten:
                self.scope.declare_statement(new_statement)
            changed = changed or len(rewritten) != 1 or rewritten[0] is not statement
        self.scope.pop()
        if not changed:
            return block
        return frog_ast.Block(new_statements)

    def _rewrite_all(self, statement: frog_ast.Statement) -> list[frog_ast.Statement]:
        """The statements replacing *statement*, with every site in them
        rewritten, those a rewrite produces included.

        The inliner runs between two calls of this rewriter and takes the
        first call it finds, so a site left for the next call would be
        inlined first: the inner position of ``a && (b || f(x))`` once the
        outer one is a guarded ``return``, or a site in the first condition
        of an ``if`` whose ``else if`` was just split off. Each rewrite
        removes one ``&&`` / ``||`` or one ``else if``, so this ends."""
        assert self.scope is not None
        inner = self._rewrite_nested(statement)
        replacement = self._rewrite_statement(inner)
        if replacement is None:
            return [inner]
        result: list[frog_ast.Statement] = []
        for new_statement in replacement:
            rewritten = self._rewrite_all(new_statement)
            result.extend(rewritten)
            for declared in rewritten:
                self.scope.declare_statement(declared)
        return result

    def _rewrite_nested(self, statement: frog_ast.Statement) -> frog_ast.Statement:
        """*statement* with the blocks nested in it rewritten."""
        assert self.scope is not None
        return map_nested_blocks(statement, self._rewrite_block, self.scope)

    def _rewrite_statement(
        self, statement: frog_ast.Statement
    ) -> Optional[list[frog_ast.Statement]]:
        """The statements replacing *statement*, or None to keep it."""
        assert self.scope is not None
        if isinstance(statement, frog_ast.IfStatement):
            for index in range(1, len(statement.conditions)):
                if self.oracle.makes_effectful_call(statement.conditions[index]):
                    return [split_else_if(statement, index)]
        finder = _SiteFinder(self.oracle, self.lookup, self.order, self.scope)
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
        # `L` and `R` move in front of the statement: first bind the parts
        # written before the site that touch what they touch, or what a part
        # bound after them touches (F-397's rule).
        callee = self._effectful_callee(site)
        parts, _ = self.order.locate(statement, site, self.scope)
        pieces = self.order.conflicting(parts, self.order.oracle.of(site), self.scope)
        bound = self.order.bind(statement, pieces, self.scope, f"{callee}@prior@")
        statement = bound[-1]
        temp = self._fresh(callee)
        guard: frog_ast.Expression = frog_ast.Variable(temp)
        if not is_and:
            guard = frog_ast.UnaryOperation(frog_ast.UnaryOperators.NOT, guard)
        return bound[:-1] + [
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


def make_conditional_calls_explicit(
    game: frog_ast.Game,
    lookup: MethodLookup,
    proof_namespace: frog_ast.Namespace,
    proof_let_types: Optional[visitors.NameTypeMap] = None,
    challenger: Optional[frog_ast.Game] = None,
) -> frog_ast.Game:
    """*game* with every conditionally evaluated call that has an effect
    given explicit control flow (module docstring); *game* itself when there
    is none. *lookup* is the inliner's method lookup; *challenger* is the
    challenger a reduction resolved alone will be composed with, whose
    methods are known but not inlined."""
    rewriter = _Rewriter(game, lookup, proof_namespace, proof_let_types, challenger)
    methods = [rewriter.rewrite_method(method) for method in game.methods]
    if all(old is new for old, new in zip(game.methods, methods)):
        return game
    new_game = copy.copy(game)
    new_game.methods = methods
    return new_game
