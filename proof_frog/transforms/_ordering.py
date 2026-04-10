"""Structural sort key for AST nodes.

Provides a single ``node_sort_key`` function that returns a recursively
constructed tuple for any AST node.  The key is structural (based on AST
shape), recursive, deterministic, and name-aware-but-name-secondary.

Used by ``NormalizeCommutativeChains`` and ``StabilizeIndependentStatements``
to order operands and statements without depending on ``__str__`` output.
"""

from __future__ import annotations

from .. import frog_ast


def node_sort_key(node: frog_ast.ASTNode) -> tuple:  # type: ignore[type-arg]
    """Return a comparable tuple that captures the structural shape of *node*.

    Type tags are fixed integers grouped by AST category so that simpler
    nodes sort before complex ones:

    - Expressions: 0-29
    - Types: 30-49
    - Statements: 50-69
    - Fallback: 999
    """
    # -- Expressions (0-29) ---------------------------------------------------
    # Variable also extends Type, but tag 0 is appropriate in both contexts.
    if isinstance(node, frog_ast.Variable):
        return (0, node.name)

    if isinstance(node, frog_ast.Integer):
        return (1, node.num)

    if isinstance(node, frog_ast.Boolean):
        return (2, int(node.bool))

    if isinstance(node, frog_ast.NoneExpression):
        return (3,)

    if isinstance(node, frog_ast.BinaryNum):
        return (4, node.num, node.length)

    if isinstance(node, frog_ast.BitStringLiteral):
        return (5, node.bit, node_sort_key(node.length))

    if isinstance(node, frog_ast.GroupGenerator):
        return (6, node_sort_key(node.group))

    if isinstance(node, frog_ast.GroupOrder):
        return (7, node_sort_key(node.group))

    if isinstance(node, frog_ast.FieldAccess):
        return (8, node_sort_key(node.the_object), node.name)

    if isinstance(node, frog_ast.ArrayAccess):
        return (9, node_sort_key(node.the_array), node_sort_key(node.index))

    if isinstance(node, frog_ast.Slice):
        return (
            10,
            node_sort_key(node.the_array),
            node_sort_key(node.start),
            node_sort_key(node.end),
        )

    if isinstance(node, frog_ast.UnaryOperation):
        return (11, node.operator.name, node_sort_key(node.expression))

    # BinaryOperation also extends Type; tag 12 in both contexts.
    if isinstance(node, frog_ast.BinaryOperation):
        return (
            12,
            node.operator.name,
            node_sort_key(node.left_expression),
            node_sort_key(node.right_expression),
        )

    if isinstance(node, frog_ast.FuncCall):
        return (13, node_sort_key(node.func), *(node_sort_key(a) for a in node.args))

    if isinstance(node, frog_ast.Tuple):
        return (14, *(node_sort_key(v) for v in node.values))

    if isinstance(node, frog_ast.Set):
        return (15, *(node_sort_key(e) for e in node.elements))

    if isinstance(node, frog_ast.ParameterizedGame):
        return (16, node.name, *(node_sort_key(a) for a in node.args))

    if isinstance(node, frog_ast.ConcreteGame):
        return (17, node_sort_key(node.game), node.which)

    # -- Types (30-49) --------------------------------------------------------
    if isinstance(node, frog_ast.IntType):
        return (30,)

    if isinstance(node, frog_ast.BoolType):
        return (31,)

    if isinstance(node, frog_ast.Void):
        return (32,)

    if isinstance(node, frog_ast.BitStringType):
        if node.parameterization is not None:
            return (33, node_sort_key(node.parameterization))
        return (33,)

    if isinstance(node, frog_ast.ModIntType):
        return (34, node_sort_key(node.modulus))

    if isinstance(node, frog_ast.GroupType):
        return (35,)

    if isinstance(node, frog_ast.GroupElemType):
        return (36, node_sort_key(node.group))

    if isinstance(node, frog_ast.ArrayType):
        return (37, node_sort_key(node.element_type), node_sort_key(node.count))

    if isinstance(node, frog_ast.MapType):
        return (38, node_sort_key(node.key_type), node_sort_key(node.value_type))

    if isinstance(node, frog_ast.SetType):
        if node.parameterization is not None:
            return (39, node_sort_key(node.parameterization))
        return (39,)

    if isinstance(node, frog_ast.FunctionType):
        return (40, node_sort_key(node.domain_type), node_sort_key(node.range_type))

    if isinstance(node, frog_ast.OptionalType):
        return (41, node_sort_key(node.the_type))

    if isinstance(node, frog_ast.ProductType):
        return (42, *(node_sort_key(t) for t in node.types))

    # -- Statements (50-69) ---------------------------------------------------
    if isinstance(node, frog_ast.Assignment):
        type_key = node_sort_key(node.the_type) if node.the_type else ()
        value_key = node_sort_key(node.value) if node.value else ()
        return (50, node_sort_key(node.var), type_key, value_key)

    if isinstance(node, frog_ast.Sample):
        type_key = node_sort_key(node.the_type) if node.the_type else ()
        return (
            51,
            node_sort_key(node.var),
            type_key,
            node_sort_key(node.sampled_from),
        )

    if isinstance(node, frog_ast.UniqueSample):
        type_key = node_sort_key(node.the_type) if node.the_type else ()
        return (
            52,
            node_sort_key(node.var),
            type_key,
            node_sort_key(node.unique_set),
            node_sort_key(node.sampled_from),
        )

    if isinstance(node, frog_ast.ReturnStatement):
        return (53, node_sort_key(node.expression))

    if isinstance(node, frog_ast.IfStatement):
        return (
            54,
            *(node_sort_key(c) for c in node.conditions),
            *(node_sort_key(b) for b in node.blocks),
        )

    if isinstance(node, frog_ast.NumericFor):
        return (
            55,
            node.name,
            node_sort_key(node.start),
            node_sort_key(node.end),
            node_sort_key(node.block),
        )

    if isinstance(node, frog_ast.GenericFor):
        return (
            56,
            node_sort_key(node.var_type),
            node.var_name,
            node_sort_key(node.over),
            node_sort_key(node.block),
        )

    if isinstance(node, frog_ast.VariableDeclaration):
        return (57, node_sort_key(node.type), node.name)

    if isinstance(node, frog_ast.Block):
        return (58, *(node_sort_key(s) for s in node.statements))

    # -- Fallback -------------------------------------------------------------
    return (999, str(node))
