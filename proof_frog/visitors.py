from __future__ import annotations
import copy
import functools
import operator
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import (
    Any,
    Optional,
    TypeVar,
    Generic,
    Callable,
    cast,
    final,
    Tuple,
    Dict,
)
import z3
from sympy import Symbol, Rational

from . import frog_ast


@dataclass
class InstantiableType:
    name: str
    members: dict[str, frog_ast.ASTNode]
    superclass: str


@functools.lru_cache(maxsize=None)
def _to_snake_case(camel_case: str) -> str:
    return "".join(["_" + i.lower() if i.isupper() else i for i in camel_case]).lstrip(
        "_"
    )


# ---------------------------------------------------------------------------
# Dispatch caches — avoid repeated hasattr / getattr / _to_snake_case lookups
# ---------------------------------------------------------------------------

_NOT_FOUND = object()

# (visitor_class, node_class) -> (visit_method | None, leave_method | None)
_VISITOR_METHODS_CACHE: dict[tuple[type, type], tuple[Any, Any]] = {}

# (transformer_class, node_class) -> method | _NOT_FOUND
_TRANSFORM_CACHE: dict[tuple[type, type], Any] = {}

# transformer_class -> method | _NOT_FOUND
_TRANSFORM_FALLBACK_CACHE: dict[type, Any] = {}


def _lookup_visitor_methods(cls: type, node_cls: type) -> tuple[Any, Any]:
    """Look up visit/leave methods for a (visitor_class, node_class) pair."""
    key = (cls, node_cls)
    cached = _VISITOR_METHODS_CACHE.get(key)
    if cached is not None:
        return cached
    snake = _to_snake_case(node_cls.__name__)
    visit_method = getattr(cls, "visit_" + snake, None) or getattr(
        cls, "visit_ast_node", None
    )
    leave_method = getattr(cls, "leave_" + snake, None) or getattr(
        cls, "leave_ast_node", None
    )
    result = (visit_method, leave_method)
    _VISITOR_METHODS_CACHE[key] = result
    return result


def _lookup_transform(cls: type, node_cls: type) -> Any:
    """Look up transform method for a (transformer_class, node_class) pair."""
    key = (cls, node_cls)
    cached = _TRANSFORM_CACHE.get(key)
    if cached is not None:
        return cached
    snake = _to_snake_case(node_cls.__name__)
    method = getattr(cls, "transform_" + snake, _NOT_FOUND)
    _TRANSFORM_CACHE[key] = method
    return method


def _lookup_transform_fallback(cls: type) -> Any:
    """Look up transform_ast_node fallback for a transformer class."""
    cached = _TRANSFORM_FALLBACK_CACHE.get(cls)
    if cached is not None:
        return cached
    method = getattr(cls, "transform_ast_node", _NOT_FOUND)
    _TRANSFORM_FALLBACK_CACHE[cls] = method
    return method


def _cow_transform_child(transformer: Any, child: Any) -> Any:
    """Copy-on-write child transformation for Transformer.

    Returns the original object unchanged (by identity) when no
    descendant was modified, enabling fast equality checks upstream.
    """
    if isinstance(child, frog_ast.ASTNode):
        return transformer.transform(child)
    if isinstance(child, list):
        new_items: Optional[list[Any]] = None
        for i, item in enumerate(child):
            new_item = _cow_transform_child(transformer, item)
            if new_item is not item and new_items is None:
                # First change detected — copy preceding unchanged items
                new_items = list(child[:i])
            if new_items is not None:
                new_items.append(new_item)
        return child if new_items is None else new_items
    return child


# Used to represent the return value of our generic visitor
U = TypeVar("U")


class Visitor(ABC, Generic[U]):
    @abstractmethod
    def result(self) -> U:
        pass

    def visit(self, visiting_node: frog_ast.ASTNode) -> U:
        cls = type(self)

        def visit_helper(node: frog_ast.ASTNode) -> None:
            visit_method, leave_method = _lookup_visitor_methods(cls, type(node))

            if visit_method is not None:
                visit_method(self, node)

            def visit_children(child: Any) -> Any:
                if isinstance(child, frog_ast.ASTNode):
                    visit_helper(child)
                if isinstance(child, (list, tuple)):
                    for item in child:
                        visit_children(item)

            for attr in vars(node):
                visit_children(getattr(node, attr))

            if leave_method is not None:
                leave_method(self, node)

        visit_helper(visiting_node)
        return self.result()


# Used to represent the type of Node that is being transformed

T = TypeVar("T", bound=frog_ast.ASTNode)


class Transformer(ABC):
    def transform(self, node: T) -> T:
        cls = type(self)
        node_cls = type(node)

        method = _lookup_transform(cls, node_cls)
        if method is not _NOT_FOUND:
            returned: T = method(self, node)
            return returned
        fallback = _lookup_transform_fallback(cls)
        if fallback is not _NOT_FOUND:
            returned = fallback(self, node)
            if returned:
                return returned

        # Copy-on-write: only create a new node if a child changed
        changed = False
        new_attrs: dict[str, Any] = {}
        for attr_name in vars(node):
            old_val = getattr(node, attr_name)
            new_val = _cow_transform_child(self, old_val)
            new_attrs[attr_name] = new_val
            if new_val is not old_val:
                changed = True

        if not changed:
            return node

        node_copy = copy.copy(node)
        for attr_name, new_val in new_attrs.items():
            setattr(node_copy, attr_name, new_val)
        return node_copy


class ReplaceTransformer(Transformer):
    def __init__(
        self, search_for: frog_ast.ASTNode, replace_with: frog_ast.ASTNode
    ) -> None:
        self.search_for = search_for
        self.replace_with = replace_with

    def transform_ast_node(self, exp: frog_ast.ASTNode) -> Optional[frog_ast.ASTNode]:
        if exp is self.search_for:
            return self.replace_with
        return None


W = TypeVar("W", bound=frog_ast.ASTNode)


class SearchVisitor(Generic[W], Visitor[Optional[W]]):
    def __init__(self, search_predicate: Callable[[frog_ast.ASTNode], bool]) -> None:
        self.node: Optional[W] = None
        self.search_predicate = search_predicate

    def result(self) -> Optional[W]:
        return self.node

    def leave_ast_node(self, node: frog_ast.ASTNode) -> None:
        if not self.node and self.search_predicate(node):
            # If it matches the search predicate, it must have type W
            self.node = cast(W, node)


class VariableCollectionVisitor(Visitor[list[frog_ast.Variable]]):
    def __init__(self) -> None:
        self.variables: list[frog_ast.Variable] = []
        self.enabled = True

    def result(self) -> list[frog_ast.Variable]:
        return self.variables

    def visit_field_access(self, _: frog_ast.FieldAccess) -> None:
        self.enabled = False

    def leave_field_access(self, _: frog_ast.FieldAccess) -> None:
        self.enabled = True

    def visit_variable(self, node: frog_ast.Variable) -> None:
        if node not in self.variables and self.enabled:
            self.variables.append(node)


class BlockTransformer(Transformer, ABC):
    @final
    def transform_block(self, block: frog_ast.Block) -> frog_ast.Block:
        new_block = self._transform_block_wrapper(block)
        return frog_ast.Block(
            [self.transform(statement) for statement in new_block.statements]
        )

    @abstractmethod
    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        pass


class FrogToSympyVisitor(Visitor[Optional[Symbol | int]]):
    def __init__(self, variables: dict[str, Symbol]) -> None:
        self.stack: list[Symbol | int] = []
        self.variables = variables
        self.failed = False

    def result(self) -> Optional[Symbol | int]:
        return self.stack[0] if not self.failed else None

    def leave_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> None:
        if len(self.stack) < 2:
            self.failed = True
            return
        item1 = self.stack.pop()
        item2 = self.stack.pop()
        if binary_operation.operator == frog_ast.BinaryOperators.ADD:
            self.stack.append(item1 + item2)
        elif binary_operation.operator == frog_ast.BinaryOperators.SUBTRACT:
            self.stack.append(item2 - item1)
        elif binary_operation.operator == frog_ast.BinaryOperators.MULTIPLY:
            self.stack.append(item1 * item2)
        elif binary_operation.operator == frog_ast.BinaryOperators.DIVIDE:
            self.stack.append(Rational(item2, item1))
        else:
            self.failed = True

    def leave_unary_operation(self, unary_operation: frog_ast.UnaryOperation) -> None:
        if not self.stack or unary_operation.operator != frog_ast.UnaryOperators.MINUS:
            self.failed = True
            return
        self.stack.append(-self.stack.pop())

    def leave_integer(self, integer: frog_ast.Integer) -> None:
        self.stack.append(integer.num)

    def leave_variable(self, var: frog_ast.Variable) -> None:
        if var.name not in self.variables:
            raise KeyError(f"Undefined variable '{var.name}' in expression")
        self.stack.append(self.variables[var.name])


class SubstitutionTransformer(Transformer):
    def __init__(self, replace_map: frog_ast.ASTMap[frog_ast.ASTNode]) -> None:
        self.replace_map = replace_map

    def transform_ast_node(self, node: frog_ast.ASTNode) -> Optional[frog_ast.ASTNode]:
        try:
            return self.replace_map.get(node)
        except KeyError:
            return None


class InstantiationTransformer(Transformer):
    def __init__(self, namespace: frog_ast.Namespace) -> None:
        self.namespace = dict(namespace)

    def transform_field(self, field: frog_ast.Field) -> frog_ast.ASTNode:
        new_field = frog_ast.Field(
            self.transform(field.type),
            field.name,
            self.transform(field.value) if field.value else None,
        )
        # Set field aliases: convert Tuple of types to ProductType so that
        # Variable substitutions produce a Type node, not an Expression.
        ns_value: frog_ast.ASTNode | None = new_field.value
        if (
            isinstance(ns_value, frog_ast.Tuple)
            and ns_value.values
            and all(isinstance(v, frog_ast.Type) for v in ns_value.values)
        ):
            ns_value = frog_ast.ProductType(
                [v for v in ns_value.values if isinstance(v, frog_ast.Type)]
            )
        self.namespace[field.name] = ns_value
        return new_field

    def transform_variable(self, variable: frog_ast.Variable) -> frog_ast.ASTNode:
        if variable.name in self.namespace:
            value = self.namespace[variable.name]
            if (
                not isinstance(
                    value, (frog_ast.Scheme, frog_ast.Primitive, InstantiableType)
                )
                and value is not None
            ):
                result = copy.deepcopy(value)
                # Convert Tuple of types to ProductType for type-position substitution
                if (
                    isinstance(result, frog_ast.Tuple)
                    and result.values
                    and all(isinstance(v, frog_ast.Type) for v in result.values)
                ):
                    return frog_ast.ProductType(
                        [v for v in result.values if isinstance(v, frog_ast.Type)]
                    )
                return result
        return variable

    def transform_field_access(
        self, field_access: frog_ast.FieldAccess
    ) -> frog_ast.ASTNode:
        if (
            isinstance(field_access.the_object, frog_ast.Variable)
            and field_access.the_object.name in self.namespace
        ):
            value = self.namespace[field_access.the_object.name]
            if isinstance(value, InstantiableType):
                if field_access.name in value.members and not isinstance(
                    value.members[field_access.name], frog_ast.MethodSignature
                ):
                    return copy.deepcopy(value.members[field_access.name])
            elif isinstance(value, (frog_ast.Scheme, frog_ast.Primitive)):
                the_field = next(
                    (
                        field.value
                        for field in value.fields
                        if field.name == field_access.name
                    ),
                    None,
                )
                if the_field is not None:
                    result = copy.deepcopy(the_field)
                    # Convert Tuple of types to ProductType for Set field aliases
                    if (
                        isinstance(result, frog_ast.Tuple)
                        and result.values
                        and all(isinstance(v, frog_ast.Type) for v in result.values)
                    ):
                        return frog_ast.ProductType(
                            [v for v in result.values if isinstance(v, frog_ast.Type)]
                        )
                    return result
        # Handle FuncCall.field case, e.g. UG(K, NG, H, G).EncapsKey.
        # After SubstitutionTransformer replaces a scheme parameter with a FuncCall,
        # type-position field accesses like K.EncapsKey become
        # FuncCall("UG", [K, NG, H, G]).EncapsKey. Look up the field in the named
        # scheme and substitute the scheme's parameters with the FuncCall's args.
        if (
            isinstance(field_access.the_object, frog_ast.FuncCall)
            and isinstance(field_access.the_object.func, frog_ast.Variable)
            and field_access.the_object.func.name in self.namespace
        ):
            func_call = field_access.the_object
            assert isinstance(func_call.func, frog_ast.Variable)
            scheme_def = self.namespace[func_call.func.name]
            if isinstance(scheme_def, (frog_ast.Scheme, frog_ast.Primitive)):
                the_field = next(
                    (
                        field.value
                        for field in scheme_def.fields
                        if field.name == field_access.name
                    ),
                    None,
                )
                if the_field is not None:
                    result = copy.deepcopy(the_field)
                    # Substitute scheme parameters with the FuncCall's actual args
                    param_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                    for idx, param in enumerate(scheme_def.parameters):
                        if idx < len(func_call.args):
                            param_map.set(
                                frog_ast.Variable(param.name),
                                copy.deepcopy(func_call.args[idx]),
                            )
                    result = SubstitutionTransformer(param_map).transform(result)
                    # Further resolve any remaining FieldAccess nodes through the
                    # current namespace (e.g. Variable("K").EncapsKey -> EncapsKeySpace
                    # when K is a concrete instantiated scheme in the namespace).
                    result = InstantiationTransformer(self.namespace).transform(result)
                    # Convert Tuple of types to ProductType for Set field aliases
                    if (
                        isinstance(result, frog_ast.Tuple)
                        and result.values
                        and all(isinstance(v, frog_ast.Type) for v in result.values)
                    ):
                        return frog_ast.ProductType(
                            [v for v in result.values if isinstance(v, frog_ast.Type)]
                        )
                    return result
        return field_access


class InlineTransformer(Transformer):
    def __init__(self, method_lookup: Dict[Tuple[str, str], frog_ast.Method]) -> None:
        self.blocks: list[frog_ast.Block] = []
        self.statement_index = 0
        self.method_lookup = method_lookup
        self.finished = False

    def transform_block(self, block: frog_ast.Block) -> frog_ast.Block:
        if self.finished:
            return block

        self.blocks.append(block)
        for index, statement in enumerate(block.statements):
            self.statement_index = index
            block.statements[index] = self.transform(statement)  # type: ignore
        return self.blocks.pop()

    def transform_func_call(self, exp: frog_ast.FuncCall) -> frog_ast.FuncCall:
        is_inlinable_call = (
            isinstance(exp.func, frog_ast.FieldAccess)
            and isinstance(exp.func.the_object, frog_ast.Variable)
            and (exp.func.the_object.name, exp.func.name) in self.method_lookup
        )
        if not is_inlinable_call or self.finished:
            return exp

        assert isinstance(exp.func, frog_ast.FieldAccess)
        assert isinstance(exp.func.the_object, frog_ast.Variable)

        called_method = copy.deepcopy(
            self.method_lookup[(exp.func.the_object.name, exp.func.name)]
        )

        for var_statement in called_method.block.statements:
            if (
                isinstance(var_statement, (frog_ast.Assignment, frog_ast.Sample))
                and var_statement.the_type is not None
                and isinstance(var_statement.var, frog_ast.Variable)
            ):
                ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                ast_map.set(
                    var_statement.var,
                    frog_ast.Variable(
                        exp.func.the_object.name
                        + "."
                        + exp.func.name
                        + "@"
                        + var_statement.var.name
                        + str(self.statement_index)
                    ),
                )
                called_method = SubstitutionTransformer(ast_map).transform(
                    called_method
                )
        transformed_method = InstantiationTransformer(
            dict(
                zip(
                    (param.name for param in called_method.signature.parameters),
                    (arg for arg in exp.args),
                )
            )
        ).transform(called_method)

        block_to_transform = self.blocks.pop()

        statements_so_far = list(block_to_transform.statements[: self.statement_index])

        statements_so_far += list(transformed_method.block.statements[:-1])

        statements_after = list(
            block_to_transform.statements[self.statement_index + 1 :]
        )

        if not transformed_method.block.statements:
            # Empty method body (e.g. a Void Initialize with no statements):
            # drop the call site entirely and continue with surrounding statements.
            self.blocks.append(frog_ast.Block(statements_so_far + statements_after))
            self.finished = True
            return exp

        final_statement = transformed_method.block.statements[-1]

        if isinstance(final_statement, frog_ast.ReturnStatement):
            returned_exp = final_statement.expression

            changed_statement = ReplaceTransformer(exp, returned_exp).transform(
                block_to_transform.statements[self.statement_index]
            )

            self.blocks.append(
                frog_ast.Block(
                    statements_so_far + [changed_statement] + statements_after
                )
            )
        else:
            self.blocks.append(
                frog_ast.Block(statements_so_far + [final_statement] + statements_after)
            )

        self.finished = True

        return exp


class Z3FormulaVisitor(Visitor[z3.AstRef]):
    # Don't just append Int(var.name), need mapping from name to new name in this formula
    def __init__(
        self,
        type_map: NameTypeMap,
        variable_version_map: Optional[dict[str, int]] = None,
    ) -> None:
        self.stack: list[Optional[z3.AstRef]] = []
        self.type_map = type_map
        self.variable_version_map = variable_version_map
        self.bool_num = 0
        self.expression_formula_map: list[
            tuple[tuple[frog_ast.Expression, dict[str, int]], z3.AstRef]
        ] = []

    def result(self) -> Optional[z3.AstRef]:
        value = self.stack[-1] if self.stack else None
        self.stack = []
        return value

    def set_type_map(self, type_map: NameTypeMap) -> None:
        self.type_map = type_map

    def set_variable_version_map(self, version_map: dict[str, int]) -> None:
        self.variable_version_map = version_map

    def _search_expression_formula_map(
        self, potential: tuple[frog_ast.Expression, dict[str, int]]
    ) -> Optional[z3.AstRef]:
        for item in self.expression_formula_map:
            if item[0] == potential:
                return item[1]
        return None

    def visit_variable(self, var: frog_ast.Variable) -> None:
        name = var.name
        if self.variable_version_map and name in self.variable_version_map:
            name = f"{name}@z3@{self.variable_version_map[name]}"
        var_type = self.type_map.get(var.name)
        if isinstance(var_type, (frog_ast.IntType, frog_ast.ModIntType)):
            self.stack.append(z3.Int(name))
        elif isinstance(var_type, frog_ast.BoolType):
            self.stack.append(z3.Bool(name))
        else:
            self.stack.append(name)

    def visit_integer(self, node: frog_ast.Integer) -> None:
        self.stack.append(node.num)

    def visit_boolean(self, node: frog_ast.Boolean) -> None:
        self.stack.append(node.bool)

    def leave_unary_operation(self, operation: frog_ast.UnaryOperation) -> None:
        if not self.stack or operation.operator == frog_ast.UnaryOperators.SIZE:
            self.stack.append(None)
            return

        val = self.stack.pop()
        if val is None:
            self.stack.append(None)
            return

        if operation.operator == frog_ast.UnaryOperators.NOT:
            self.stack.append(z3.Not(val))
        else:
            self.stack.append(-val)

    def leave_binary_operation(self, operation: frog_ast.BinaryOperation) -> None:
        operators = {
            frog_ast.BinaryOperators.ADD: operator.add,
            frog_ast.BinaryOperators.SUBTRACT: operator.sub,
            frog_ast.BinaryOperators.MULTIPLY: operator.mul,
            frog_ast.BinaryOperators.DIVIDE: operator.truediv,
            frog_ast.BinaryOperators.EQUALS: operator.eq,
            frog_ast.BinaryOperators.NOTEQUALS: operator.ne,
            frog_ast.BinaryOperators.LT: operator.lt,
            frog_ast.BinaryOperators.GT: operator.gt,
            frog_ast.BinaryOperators.GEQ: operator.ge,
            frog_ast.BinaryOperators.LEQ: operator.le,
            frog_ast.BinaryOperators.OR: z3.Or,
            frog_ast.BinaryOperators.AND: z3.And,
        }
        right_item = self.stack.pop() if self.stack else None
        left_item = self.stack.pop() if self.stack else None
        if (
            right_item is not None
            and left_item is not None
            and operation.operator
            in set([frog_ast.BinaryOperators.IN, frog_ast.BinaryOperators.SUBSETS])
        ):
            assert self.variable_version_map is not None
            z3_bool = self._search_expression_formula_map(
                (operation, self.variable_version_map)
            )
            if z3_bool is None:
                z3_bool = z3.Bool(f"@@@unknown_boolean{self.bool_num}")
                self.bool_num += 1
                self.expression_formula_map.append(
                    ((operation, copy.deepcopy(self.variable_version_map)), z3_bool)
                )
            self.stack.append(z3_bool)
            return

        if (
            right_item is not None
            and left_item is not None
            and not isinstance(left_item, str)
            and not isinstance(right_item, str)
            and operation.operator in operators
        ):
            self.stack.append(operators[operation.operator](left_item, right_item))
        else:
            self.stack.append(None)


class AllConstantFieldAccesses(Visitor[bool]):
    def __init__(self, tuple_name: str):
        self.tuple_name = tuple_name
        self.all_constant = True

    def result(self) -> bool:
        return self.all_constant

    def visit_array_access(self, array_access: frog_ast.ArrayAccess) -> None:
        if not isinstance(array_access.the_array, frog_ast.Variable):
            return
        if array_access.the_array.name != self.tuple_name:
            return
        if not isinstance(array_access.index, frog_ast.Integer):
            self.all_constant = False

    def visit_assignment(self, assignment: frog_ast.Assignment) -> None:
        if not isinstance(assignment.var, frog_ast.Variable):
            return
        if assignment.var.name != self.tuple_name:
            return
        if not isinstance(assignment.value, frog_ast.Tuple):
            self.all_constant = False


class FieldOrderingVisitor(Visitor[dict[str, str]]):
    def __init__(self) -> None:
        self.field_num = 0
        self.fields: list[str] = []
        self.field_rename_map: dict[str, str] = {}
        self.in_initialize = False

    def result(self) -> dict[str, str]:
        # Some fields may not be used anywhere apart from Initialize
        # so we will just name any remaining ones sequentially w.r.t to definition order
        for field_name in self.fields:
            if field_name not in self.field_rename_map:
                self.field_num += 1
                self.field_rename_map[field_name] = f"field{self.field_num}"
        return self.field_rename_map

    def visit_method_signature(
        self, method_signature: frog_ast.MethodSignature
    ) -> None:
        if method_signature.name == "Initialize":
            self.in_initialize = True

    def leave_method(self, __: frog_ast.Method) -> None:
        self.in_initialize = False

    def visit_field(self, field: frog_ast.Field) -> None:
        self.fields.append(field.name)

    def visit_variable(self, var: frog_ast.Variable) -> None:
        if (
            var.name in self.fields
            and var.name not in self.field_rename_map
            and not self.in_initialize
        ):
            self.field_num += 1
            self.field_rename_map[var.name] = f"field{self.field_num}"


@dataclass
class NameTypePair:
    name: str
    type: frog_ast.Type


class NameTypeMap:
    def __init__(self) -> None:
        self.type_map: list[NameTypePair] = []

    def set(self, name: str, the_type: frog_ast.Type) -> None:
        for index, item in enumerate(self.type_map):
            if item.name == name:
                self.type_map[index] = NameTypePair(item.name, the_type)
                return
        self.type_map.append(NameTypePair(name=name, type=the_type))

    def get(self, name: str) -> Optional[frog_ast.Type]:
        for item in self.type_map:
            if item.name == name:
                return item.type
        return None

    def remove(self, name: str) -> None:
        for index, item in enumerate(self.type_map):
            if item.name == name:
                del self.type_map[index]
                return

    def __add__(self, other: NameTypeMap) -> NameTypeMap:
        new_map = NameTypeMap()
        for val in self.type_map:
            new_map.set(val.name, val.type)
        for val in other.type_map:
            new_map.set(val.name, val.type)
        return new_map


F = TypeVar("F", bound=Callable[..., Any])


def _test_stop(func: F) -> F:
    def wrapper(self: GetTypeMapVisitor, param: frog_ast.ASTNode) -> None:
        if param is self.stopping_point:
            self.stopped = True
        if not self.stopped:
            func(self, param)

    return cast(F, wrapper)


class GetTypeMapVisitor(Visitor[NameTypeMap]):
    def __init__(self, stopping_point: frog_ast.ASTNode):
        self.stopping_point = stopping_point
        self.stopped = False
        self.type_map = NameTypeMap()

    def result(self) -> NameTypeMap:
        return self.type_map

    @_test_stop
    def visit_field(self, field: frog_ast.Field) -> None:
        self.type_map.set(field.name, field.type)

    @_test_stop
    def visit_assignment(self, assignment: frog_ast.Assignment) -> None:
        if assignment.the_type is not None:
            assert isinstance(assignment.var, frog_ast.Variable)
            self.type_map.set(assignment.var.name, assignment.the_type)

    @_test_stop
    def visit_sample(self, sample: frog_ast.Sample) -> None:
        if sample.the_type is not None:
            assert isinstance(sample.var, frog_ast.Variable)
            self.type_map.set(sample.var.name, sample.the_type)

    @_test_stop
    def visit_unique_sample(self, unique_sample: frog_ast.UniqueSample) -> None:
        if unique_sample.the_type is not None:
            assert isinstance(unique_sample.var, frog_ast.Variable)
            self.type_map.set(unique_sample.var.name, unique_sample.the_type)

    @_test_stop
    def visit_variable_declaration(
        self, variable_declaration: frog_ast.VariableDeclaration
    ) -> None:
        self.type_map.set(variable_declaration.name, variable_declaration.type)

    @_test_stop
    def visit_parameter(self, parameter: frog_ast.Parameter) -> None:
        self.type_map.set(parameter.name, parameter.type)

    @_test_stop
    def visit_ast_node(self, node: frog_ast.ASTNode) -> None:
        pass


def build_game_type_map(
    game: frog_ast.Game, proof_let_types: Optional[NameTypeMap] = None
) -> NameTypeMap:
    """Build a NameTypeMap containing all variable types declared in a game.

    Collects types from fields, method parameters, assignments, and samples.
    Optionally merges with proof-level let types.
    """
    # Use a dummy stopping point that won't match any real node to collect everything
    dummy = frog_ast.Boolean(True)
    type_map = GetTypeMapVisitor(dummy).visit(game)
    if proof_let_types is not None:
        type_map = type_map + proof_let_types
    return type_map


def assigns_variable(
    used_variables: list[frog_ast.Variable], node: frog_ast.ASTNode
) -> bool:
    return isinstance(
        node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
    ) and (
        (node.var in used_variables)
        or (
            isinstance(node.var, frog_ast.ArrayAccess)
            and node.var.the_array in used_variables
        )
    )


class SameFieldVisitor(Visitor[Optional[list[frog_ast.Statement]]]):
    def __init__(self, field_name_pair: tuple[str, str]):
        self.field_name_pair = field_name_pair
        self.are_same = True
        self.paired_statements: list[frog_ast.Statement] = []

    def result(self) -> Optional[list[frog_ast.Statement]]:
        return None if not self.are_same else self.paired_statements

    def visit_block(self, block: frog_ast.Block) -> None:
        if not self.are_same:
            return

        for index, statement in enumerate(block.statements):
            if statement in self.paired_statements:
                continue

            if not isinstance(statement, (frog_ast.Sample, frog_ast.Assignment)):
                continue
            if not isinstance(statement.var, frog_ast.Variable):
                continue
            if statement.var.name not in self.field_name_pair:
                continue

            assigned_name = statement.var.name
            pair_name = (
                self.field_name_pair[0]
                if assigned_name == self.field_name_pair[1]
                else self.field_name_pair[1]
            )

            def contains_func(node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.FuncCall)

            has_func_call = SearchVisitor(contains_func).visit(
                statement
            ) is not None or isinstance(statement, frog_ast.Sample)

            if has_func_call:
                # Assignments with function calls can't be matched by
                # expression equality (the call may return different
                # values each time).  However, a direct copy of the
                # field IS safe: field1 = K.f(); field2 = field1.
                def reads_pair_fc(pn: str, node: frog_ast.ASTNode) -> bool:
                    return isinstance(node, frog_ast.Variable) and node.name == pn

                copy_paired = False
                for subsequent_statement in block.statements[index + 1 :]:
                    if (
                        isinstance(subsequent_statement, frog_ast.Assignment)
                        and isinstance(subsequent_statement.var, frog_ast.Variable)
                        and subsequent_statement.var.name == pair_name
                        and isinstance(subsequent_statement.value, frog_ast.Variable)
                        and subsequent_statement.value.name == assigned_name
                    ):
                        copy_paired = True
                        self.paired_statements.append(subsequent_statement)
                        break
                    if (
                        SearchVisitor(
                            functools.partial(reads_pair_fc, pair_name)
                        ).visit(subsequent_statement)
                        is not None
                    ):
                        break
                if copy_paired:
                    continue
                self.are_same = False
                return

            def reads_pair(pair_name: str, node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.Variable) and node.name == pair_name

            assert isinstance(statement, frog_ast.Assignment)
            used_variables = VariableCollectionVisitor().visit(statement.value)

            assigns_variable_partial = functools.partial(
                assigns_variable, used_variables
            )

            reads_pair_partial = functools.partial(reads_pair, pair_name)
            ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
            ast_map.set(statement.var, frog_ast.Variable(pair_name))
            paired_value = SubstitutionTransformer(ast_map).transform(statement.value)

            paired = False
            for subsequent_statement in block.statements[index + 1 :]:
                if (
                    isinstance(subsequent_statement, frog_ast.Assignment)
                    and isinstance(subsequent_statement.var, frog_ast.Variable)
                    and subsequent_statement.var.name == pair_name
                    and subsequent_statement.value in (paired_value, statement.var)
                ):
                    paired = True
                    self.paired_statements.append(subsequent_statement)
                    break

                if (
                    SearchVisitor(assigns_variable_partial).visit(subsequent_statement)
                    is not None
                ) or (
                    SearchVisitor(reads_pair_partial).visit(subsequent_statement)
                ) is not None:
                    self.are_same = False
                    return
            if not paired:
                self.are_same = False
                return
