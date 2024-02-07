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
    List,
    Dict,
)
import z3
from sympy import Symbol

from . import frog_ast
from . import frog_parser


def _to_snake_case(camel_case: str) -> str:
    return "".join(["_" + i.lower() if i.isupper() else i for i in camel_case]).lstrip(
        "_"
    )


# Used to represent the return value of our generic visitor
U = TypeVar("U")


class Visitor(ABC, Generic[U]):
    @abstractmethod
    def result(self) -> U:
        pass

    def visit(self, visiting_node: frog_ast.ASTNode) -> U:
        def visit_helper(node: frog_ast.ASTNode) -> None:
            visit_name = "visit_" + _to_snake_case(type(node).__name__)
            if hasattr(self, visit_name):
                getattr(self, visit_name)(node)
            elif hasattr(self, "visit_ast_node"):
                getattr(self, "visit_ast_node")(node)

            def visit_children(child: Any) -> Any:
                if isinstance(child, frog_ast.ASTNode):
                    visit_helper(child)
                if isinstance(child, list):
                    for item in child:
                        visit_children(item)

            for attr in vars(node):
                visit_children(getattr(node, attr))

            leave_name = "leave_" + _to_snake_case(type(node).__name__)
            if hasattr(self, leave_name):
                getattr(self, leave_name)(node)
            elif hasattr(self, "leave_ast_node"):
                getattr(self, "leave_ast_node")(node)

        visit_helper(visiting_node)
        return self.result()


# Used to represent the type of Node that is being transformed

T = TypeVar("T", bound=frog_ast.ASTNode)


class Transformer(ABC):
    def transform(self, node: T) -> T:
        method_name = "transform_" + _to_snake_case(type(node).__name__)
        if hasattr(self, method_name):
            returned: T = getattr(self, method_name)(node)
            return returned
        if hasattr(self, "transform_ast_node"):
            returned = getattr(self, "transform_ast_node")(node)
            if returned:
                return returned

        node_copy = copy.deepcopy(node)

        def visit_children(child: Any) -> Any:
            if isinstance(child, frog_ast.ASTNode):
                return self.transform(child)
            if isinstance(child, list):
                return [visit_children(item) for item in child]
            return child

        for attr in vars(node_copy):
            setattr(node_copy, attr, visit_children(getattr(node, attr)))
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


class RedundantCopyTransformer(BlockTransformer):
    def _transform_block_wrapper(
        self,
        block: frog_ast.Block,
    ) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            # Potentially, could be a redundant copy
            if (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.value, frog_ast.Variable)
            ):
                # Search through the remaining statements to see if the variable was ever used again.
                original_name = statement.value.name

                def original_used(original_name: str, node: frog_ast.ASTNode) -> bool:
                    return (
                        isinstance(node, frog_ast.Variable)
                        and node.name == original_name
                    )

                remaining_block = frog_ast.Block(
                    copy.deepcopy(block.statements[index + 1 :])
                )
                used_again = SearchVisitor[frog_ast.Variable](
                    functools.partial(original_used, original_name)
                ).visit(remaining_block)
                # If it was used again, just move on. This ain't gonna work.
                if used_again:
                    continue

                assert isinstance(statement.var, frog_ast.Variable)

                copy_name = statement.var.name

                def copy_used(copy_name: str, node: frog_ast.ASTNode) -> bool:
                    return (
                        isinstance(node, frog_ast.Variable) and node.name == copy_name
                    )

                while True:
                    copy_found = SearchVisitor[frog_ast.Variable](
                        functools.partial(copy_used, copy_name)
                    ).visit(remaining_block)
                    if copy_found is None:
                        break
                    remaining_block = ReplaceTransformer(
                        copy_found, frog_ast.Variable(original_name)
                    ).transform(remaining_block)

                return self.transform_block(
                    frog_ast.Block(copy.deepcopy(block.statements[:index]))
                    + remaining_block
                )
        return block


class RedundantFieldCopyTransformer(BlockTransformer):
    def __init__(self) -> None:
        self.fields: list[str] = []

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.fields = [field.name for field in game.fields]
        new_game = copy.deepcopy(game)
        new_game.methods = [self.transform(method) for method in new_game.methods]
        return new_game

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if (
                isinstance(statement, frog_ast.Assignment)
                and isinstance(statement.var, frog_ast.Variable)
                and statement.var.name in self.fields
            ):
                if not isinstance(statement.value, frog_ast.Variable):
                    continue

                def search_for_other_use(
                    var: frog_ast.Variable, node: frog_ast.ASTNode
                ) -> bool:
                    return node == var

                no_other_uses = True
                decl_index: int
                decl_statement: frog_ast.Assignment
                for other_index, other_statement in enumerate(block.statements):
                    if statement == other_statement:
                        continue
                    if (
                        isinstance(other_statement, frog_ast.Assignment)
                        and other_statement.the_type is not None
                        and other_statement.var == statement.value
                    ):
                        decl_index = other_index
                        decl_statement = other_statement
                        continue
                    if (
                        SearchVisitor(
                            functools.partial(search_for_other_use, statement.var)
                        ).visit(other_statement)
                        is not None
                    ):
                        no_other_uses = False
                if not no_other_uses:
                    continue
                modified_statement = copy.deepcopy(statement)
                modified_statement.value = decl_statement.value
                return self.transform(
                    frog_ast.Block(
                        list(block.statements[:decl_index])
                        + [modified_statement]
                        + list(block.statements[decl_index + 1 : index])
                        + list(block.statements[index + 1 :])
                    )
                )
        return block


class SimplifySpliceTransformer(BlockTransformer):
    def __init__(self, variables: dict[str, Symbol | frog_ast.Expression]) -> None:
        self.variables = variables

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not isinstance(statement, frog_ast.Assignment):
                continue
            if not isinstance(statement.value, frog_ast.BinaryOperation):
                continue
            if not isinstance(
                statement.value.left_expression, frog_ast.Variable
            ) or not isinstance(statement.value.right_expression, frog_ast.Variable):
                continue
            # Concatenate in this context
            if statement.value.operator is not frog_ast.BinaryOperators.OR:
                continue

            # Step 1, find type of variables (to get length)
            # Step 2, determine lengths
            # Step 3, replace, so long as statement and left/right are not changed

            def find_declaration(variable: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(node, (frog_ast.Assignment, frog_ast.Sample))
                    and isinstance(node.var, frog_ast.Variable)
                    and node.var.name == variable
                    and isinstance(node.the_type, frog_ast.BitStringType)
                    and node.the_type.parameterization is not None
                )

            left_declaration = SearchVisitor(
                functools.partial(
                    find_declaration, statement.value.left_expression.name
                )
            ).visit(block)
            right_declaration = SearchVisitor(
                functools.partial(
                    find_declaration, statement.value.right_expression.name
                )
            ).visit(block)
            if left_declaration is None or right_declaration is None:
                continue

            assert isinstance(left_declaration, (frog_ast.Assignment, frog_ast.Sample))
            assert isinstance(right_declaration, (frog_ast.Assignment, frog_ast.Sample))
            assert isinstance(
                left_declaration.the_type, frog_ast.BitStringType
            ) and isinstance(right_declaration.the_type, frog_ast.BitStringType)
            assert (
                left_declaration.the_type.parameterization is not None
                and right_declaration.the_type.parameterization is not None
            )
            left_len = left_declaration.the_type.parameterization
            right_len = left_declaration.the_type.parameterization

            if not isinstance(left_len, frog_ast.Variable) or not isinstance(
                right_len, frog_ast.Variable
            ):
                continue
            if (
                not left_len.name in self.variables
                or not right_len.name in self.variables
            ):
                continue
            end_length = self.variables[left_len.name] + self.variables[right_len.name]

            left_slice = frog_ast.Slice(
                frog_ast.Variable(statement.var.name), frog_ast.Integer(0), left_len
            )
            right_slice = frog_ast.Slice(
                frog_ast.Variable(statement.var.name),
                left_len,
                frog_parser.parse_expression(str(end_length)),
            )

            remaining_block = frog_ast.Block(block.statements[index + 1 :])

            def use_or_reassignment(
                no_touch_vars: list[frog_ast.Variable],
                slices: list[frog_ast.Slice],
                node: frog_ast.ASTNode,
            ) -> bool:
                return (
                    isinstance(node, (frog_ast.Assignment, frog_ast.Sample))
                    and (node.var in no_touch_vars)
                ) or node in slices

            made_transformation = False
            while True:
                to_transform = SearchVisitor[
                    frog_ast.Assignment | frog_ast.Sample | frog_ast.Slice
                ](
                    functools.partial(
                        use_or_reassignment,
                        [statement.var, left_declaration.var, right_declaration.var],
                        [left_slice, right_slice],
                    )
                ).visit(
                    remaining_block
                )

                if (
                    isinstance(to_transform, (frog_ast.Assignment, frog_ast.Sample))
                    or to_transform is None
                ):
                    break

                made_transformation = True

                remaining_block = ReplaceTransformer(
                    to_transform,
                    (
                        left_declaration.var
                        if to_transform == left_slice
                        else right_declaration.var
                    ),
                ).transform(remaining_block)
            if not made_transformation:
                continue
            return self.transform_block(
                frog_ast.Block(copy.deepcopy(block.statements[:index]))
                + remaining_block
            )

        return block


class VariableStandardizingTransformer(BlockTransformer):
    def __init__(self) -> None:
        self.variable_counter = 0

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        new_block = copy.deepcopy(block)
        for statement in new_block.statements:
            if not isinstance(statement, frog_ast.Assignment) and not isinstance(
                statement, frog_ast.Sample
            ):
                continue
            if not isinstance(statement.var, frog_ast.Variable):
                continue

            if statement.the_type is None:
                continue

            self.variable_counter += 1
            expected_name = f"v{self.variable_counter}"
            if statement.var.name == expected_name:
                continue

            def var_used(var: frog_ast.Variable, node: frog_ast.ASTNode) -> bool:
                return node == var

            while True:
                to_transform = SearchVisitor[frog_ast.Variable](
                    functools.partial(var_used, statement.var)
                ).visit(new_block)

                if to_transform is None:
                    break

                new_block = ReplaceTransformer(
                    to_transform, frog_ast.Variable(expected_name)
                ).transform(new_block)
        return new_block


class SubstitutionTransformer(Transformer):
    def __init__(
        self, replace_map: list[Tuple[frog_ast.ASTNode, frog_ast.ASTNode]]
    ) -> None:
        self.replace_map = replace_map

    def _find(self, v: frog_ast.ASTNode) -> Optional[frog_ast.ASTNode]:
        the_list = [item for item in self.replace_map if item[0] == v]
        if the_list:
            return the_list[0][1]
        return None

    def transform_variable(self, v: frog_ast.Variable) -> frog_ast.ASTNode:
        found = self._find(v)
        if found:
            return found
        return v

    def transform_field_access(
        self, field_access: frog_ast.FieldAccess
    ) -> frog_ast.ASTNode:
        found = self._find(field_access)
        if found:
            return found
        return frog_ast.FieldAccess(
            self.transform(field_access.the_object), field_access.name
        )


class InstantiationTransformer(Transformer):
    def __init__(self, namespace: frog_ast.Namespace) -> None:
        self.namespace = copy.deepcopy(namespace)

    def transform_field(self, field: frog_ast.Field) -> frog_ast.ASTNode:
        new_field = frog_ast.Field(
            self.transform(field.type),
            field.name,
            self.transform(field.value) if field.value else None,
        )
        self.namespace[field.name] = new_field.value
        return new_field

    def transform_variable(self, variable: frog_ast.Variable) -> frog_ast.ASTNode:
        if variable.name in self.namespace:
            value = self.namespace[variable.name]
            if (
                not isinstance(value, (frog_ast.Scheme, frog_ast.Primitive))
                and value is not None
            ):
                return copy.deepcopy(value)
        return variable

    def transform_field_access(
        self, field_access: frog_ast.FieldAccess
    ) -> frog_ast.ASTNode:
        if (
            isinstance(field_access.the_object, frog_ast.Variable)
            and field_access.the_object.name in self.namespace
        ):
            value = self.namespace[field_access.the_object.name]
            assert isinstance(value, (frog_ast.Scheme, frog_ast.Primitive))
            the_field = next(
                (
                    field.value
                    for field in value.fields
                    if field.name == field_access.name
                ),
                None,
            )
            if the_field is not None:
                return copy.deepcopy(the_field)
        return field_access


class SymbolicComputationTransformer(Transformer):
    def __init__(self, variables: dict[str, Symbol | frog_ast.Expression]) -> None:
        self.variables = variables
        self.computation_stack: List[Symbol | int | None] = []

    def transform_variable(self, variable: frog_ast.Variable) -> frog_ast.Variable:
        if variable.name in self.variables:
            val = self.variables[variable.name]
            assert isinstance(val, Symbol)
            self.computation_stack.append(val)
        else:
            self.computation_stack.append(None)
        return variable

    def transform_integer(self, integer: frog_ast.Integer) -> frog_ast.Integer:
        self.computation_stack.append(integer.num)
        return integer

    def transform_bit_string_type(
        self, bs_type: frog_ast.BitStringType
    ) -> frog_ast.BitStringType:
        new_bs = frog_ast.BitStringType(
            self.transform(bs_type.parameterization)
            if bs_type.parameterization
            else bs_type.parameterization
        )
        self.computation_stack.append(None)
        return new_bs

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.ASTNode:
        old_len = len(self.computation_stack)
        transformed_left = self.transform(binary_operation.left_expression)
        transformed_right = self.transform(binary_operation.right_expression)
        if len(self.computation_stack) == 2 + old_len:
            simplified_expression = None
            operators = {
                frog_ast.BinaryOperators.ADD: operator.add,
                frog_ast.BinaryOperators.SUBTRACT: operator.sub,
                frog_ast.BinaryOperators.MULTIPLY: operator.mul,
                frog_ast.BinaryOperators.DIVIDE: operator.truediv,
            }
            if (
                binary_operation.operator in operators
                and self.computation_stack[-1] is not None
                and self.computation_stack[-2] is not None
            ):
                simplified_expression = operators[binary_operation.operator](
                    self.computation_stack[-1], self.computation_stack[-2]
                )
            self.computation_stack.pop()
            self.computation_stack.pop()
            if simplified_expression is not None:
                self.computation_stack.append(simplified_expression)
                return frog_parser.parse_expression(str(simplified_expression))
            self.computation_stack.append(None)

        return frog_ast.BinaryOperation(
            binary_operation.operator, transformed_left, transformed_right
        )


class SimplifyIfTransformer(Transformer):
    def transform_if_statement(
        self, if_statement: frog_ast.IfStatement
    ) -> frog_ast.IfStatement:
        new_blocks: list[frog_ast.Block] = copy.deepcopy(if_statement.blocks)
        new_conditions = copy.deepcopy(if_statement.conditions)
        index = 0
        while index < len(new_blocks) - (1 if not if_statement.has_else_block() else 2):
            if new_blocks[index] == new_blocks[index + 1]:
                del new_blocks[index]
                new_conditions[index] = frog_ast.BinaryOperation(
                    frog_ast.BinaryOperators.OR,
                    copy.deepcopy(new_conditions[index]),
                    copy.deepcopy(new_conditions[index + 1]),
                )
                del new_conditions[index + 1]
            else:
                index += 1

        if if_statement.has_else_block():
            if new_blocks[-1] == new_blocks[-2]:
                del new_blocks[-1]
                del new_conditions[-1]

            if not new_conditions:
                new_conditions = [frog_ast.Boolean(True)]
        return frog_ast.IfStatement(new_conditions, new_blocks)


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
                called_method = SubstitutionTransformer(
                    [
                        (
                            var_statement.var,
                            frog_ast.Variable(
                                exp.func.the_object.name
                                + "."
                                + exp.func.name
                                + "@"
                                + var_statement.var.name
                            ),
                        )
                    ]
                ).transform(called_method)
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

        final_statement = transformed_method.block.statements[-1]

        statements_after = list(
            block_to_transform.statements[self.statement_index + 1 :]
        )

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
        if isinstance(self.type_map.get(var.name), frog_ast.IntType):
            self.stack.append(z3.Int(name))
        elif isinstance(self.type_map.get(var.name), frog_ast.BoolType):
            self.stack.append(z3.Bool(name))
        else:
            self.stack.append(name)

    def visit_integer(self, node: frog_ast.Integer) -> None:
        self.stack.append(node.num)

    def visit_boolean(self, node: frog_ast.Boolean) -> None:
        self.stack.append(node.bool)

    def leave_unary_operation(self, operation: frog_ast.UnaryOperation) -> None:
        if operation.operator == frog_ast.UnaryOperators.NOT and self.stack:
            val = self.stack.pop()
            if val is not None:
                self.stack.append(z3.Not(val))
            else:
                self.stack.append(None)
        else:
            self.stack.append(None)

    def leave_binary_operation(self, operation: frog_ast.BinaryOperation) -> None:
        operators = {
            frog_ast.BinaryOperators.ADD: operator.add,
            frog_ast.BinaryOperators.SUBTRACT: operator.sub,
            frog_ast.BinaryOperators.MULTIPLY: operator.mul,
            frog_ast.BinaryOperators.DIVIDE: operator.truediv,
            frog_ast.BinaryOperators.EQUALS: operator.eq,
            frog_ast.BinaryOperators.NOTEQUALS: operator.neg,
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
        ):
            self.stack.append(operators[operation.operator](left_item, right_item))
        else:
            self.stack.append(None)


class SimplifyRangeTransformer(Transformer):
    def __init__(
        self,
        proof_let_types: NameTypeMap,
        game: frog_ast.Game,
        operation: frog_ast.BinaryOperation | frog_ast.UnaryOperation,
    ) -> None:
        self.game = game
        self.proof_let_types = proof_let_types
        type_map = GetTypeMapVisitor(game.methods[0]).visit(game) + proof_let_types
        self.assumed_op = operation
        self.assumed_formula = Z3FormulaVisitor(type_map).visit(operation)
        if self.assumed_formula is not None:
            self.solver = z3.Solver()
            self.solver.add(self.assumed_formula)

    def transform_unary_operation(
        self, unary_operation: frog_ast.UnaryOperation
    ) -> frog_ast.Expression:
        return self._get_op(unary_operation)

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        return self._get_op(binary_operation)

    def _get_op(
        self, operation: frog_ast.BinaryOperation | frog_ast.UnaryOperation
    ) -> frog_ast.Expression:
        if operation == self.assumed_op:
            return frog_ast.Boolean(True)
        if (
            operation.operator
            not in (
                frog_ast.BinaryOperators.EQUALS,
                frog_ast.BinaryOperators.NOTEQUALS,
                frog_ast.BinaryOperators.LEQ,
                frog_ast.BinaryOperators.LT,
                frog_ast.BinaryOperators.GT,
                frog_ast.BinaryOperators.GEQ,
                frog_ast.BinaryOperators.AND,
                frog_ast.BinaryOperators.OR,
                frog_ast.UnaryOperators.NOT,
            )
            or self.assumed_formula is None
        ):
            return operation
        type_map = GetTypeMapVisitor(operation).visit(self.game) + self.proof_let_types
        statement_formula = Z3FormulaVisitor(type_map).visit(operation)
        if statement_formula is None:
            return operation
        self.solver.push()
        self.solver.add(statement_formula)
        satisfied = self.solver.check() == z3.sat
        self.solver.pop()
        if not satisfied:
            return frog_ast.Boolean(False)
        solver = z3.Solver()
        solver.add(z3.Not(z3.Implies(self.assumed_formula, statement_formula)))
        if solver.check() == z3.unsat:
            return frog_ast.Boolean(True)
        return operation


class BranchEliminiationTransformer(BlockTransformer):
    def _transform_block_wrapper(
        self,
        block: frog_ast.Block,
    ) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if isinstance(statement, frog_ast.IfStatement):
                if_statement = statement
                new_if_statement = copy.deepcopy(if_statement)

                i = 0
                while True:
                    if i >= len(new_if_statement.conditions):
                        break
                    condition = new_if_statement.conditions[i]
                    if isinstance(condition, frog_ast.Boolean) and condition.bool:
                        new_if_statement.conditions = if_statement.conditions[: i + 1]
                        new_if_statement.blocks = if_statement.blocks[: i + 1]
                        if i == len(new_if_statement.conditions) - 1 and i > 0:
                            del new_if_statement.conditions[-1]
                        break
                    if isinstance(condition, frog_ast.Boolean) and not condition.bool:
                        del new_if_statement.conditions[i]
                        del new_if_statement.blocks[i]
                    else:
                        i += 1

                prior_block = frog_ast.Block(block.statements[:index])
                remaining_block = frog_ast.Block(block.statements[index + 1 :])

                if not new_if_statement.blocks:
                    return prior_block + remaining_block

                if (
                    len(new_if_statement.conditions) == 1
                    and isinstance(new_if_statement.conditions[0], frog_ast.Boolean)
                    and new_if_statement.conditions[0].bool
                ) or not new_if_statement.conditions:
                    return self.transform_block(
                        prior_block + new_if_statement.blocks[0] + remaining_block
                    )

                if new_if_statement != if_statement:
                    return self.transform_block(
                        prior_block
                        + frog_ast.Block([new_if_statement])
                        + remaining_block
                    )
        return block


class RemoveFieldTransformer(Transformer):
    def __init__(self, fields_to_remove: list[str]) -> None:
        self.fields_to_remove = fields_to_remove

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        new_game = copy.deepcopy(game)
        new_game.fields = [
            field for field in game.fields if field.name not in self.fields_to_remove
        ]

        new_game.methods = [self.transform(method) for method in game.methods]

        return new_game

    def transform_block(self, block: frog_ast.Block) -> frog_ast.Block:
        new_statements: list[frog_ast.Statement] = []

        def to_be_deleted(node: frog_ast.ASTNode) -> bool:
            return (
                isinstance(node, frog_ast.Variable)
                and node.name in self.fields_to_remove
            )

        for statement in block.statements:
            if isinstance(statement, frog_ast.IfStatement):
                new_if = copy.deepcopy(statement)
                i = 0
                while i < len(new_if.conditions):
                    if (
                        SearchVisitor(to_be_deleted).visit(new_if.conditions[i])
                        is not None
                    ):
                        del new_if.conditions[i]
                        del new_if.blocks[i]
                    else:
                        i += 1
                if len(new_if.conditions) > 0:
                    new_statements.append(new_if)
            elif isinstance(statement, frog_ast.NumericFor):
                if (
                    SearchVisitor(to_be_deleted).visit(statement.start) is None
                    and SearchVisitor(to_be_deleted).visit(statement.end) is None
                ):
                    new_statements.append(statement)
            elif isinstance(statement, frog_ast.GenericFor):
                if SearchVisitor(to_be_deleted).visit(statement.over) is None:
                    new_statements.append(statement)
            else:
                if SearchVisitor(to_be_deleted).visit(statement) is None:
                    new_statements.append(statement)
        return frog_ast.Block(
            [self.transform(copy.deepcopy(statement)) for statement in new_statements]
        )


class CollapseAssignmentTransformer(BlockTransformer):
    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not isinstance(statement, (frog_ast.Assignment, frog_ast.Sample)):
                continue
            if not isinstance(statement.var, frog_ast.Variable):
                continue

            def calls_func(node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.FuncCall)

            if SearchVisitor(calls_func).visit(statement) is not None:
                continue

            def uses_var(var: frog_ast.Variable, node: frog_ast.ASTNode) -> bool:
                return node == var

            uses_var_partial = functools.partial(uses_var, statement.var)
            for later_index, later_statement in enumerate(
                block.statements[index + 1 :]
            ):
                contains_var = SearchVisitor(uses_var_partial).visit(later_statement)
                if contains_var is None:
                    continue
                if not isinstance(
                    later_statement, (frog_ast.Assignment, frog_ast.Sample)
                ):
                    break
                if (
                    contains_var
                    and SearchVisitor(uses_var_partial).visit(later_statement.value)
                    is not None
                ):
                    break
                replaced_statement = copy.deepcopy(statement)
                replaced_statement.value = later_statement.value
                return self.transform_block(
                    frog_ast.Block(
                        block.statements[:index]
                        + block.statements[index + 1 : index + later_index]
                        + [replaced_statement]
                        + block.statements[index + later_index + 2 :]
                    )
                )

        return block


class SimplifyReturnTransformer(BlockTransformer):
    def __init__(self) -> None:
        self.fields: list[str] = []

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.fields = [field.name for field in game.fields]
        new_game = copy.deepcopy(game)
        new_game.methods = [self.transform(method) for method in new_game.methods]
        return new_game

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        if not block.statements:
            return block
        last_statement = block.statements[-1]
        if not isinstance(last_statement, frog_ast.ReturnStatement):
            return block
        if not isinstance(last_statement.expression, frog_ast.Variable):
            return block
        if last_statement.expression.name in self.fields:
            return block
        index = len(block.statements) - 1

        def uses_var(variable: frog_ast.Expression, node: frog_ast.ASTNode) -> bool:
            return variable == node

        uses_var_partial = functools.partial(uses_var, last_statement.expression)
        while index >= 0:
            index -= 1
            statement = block.statements[index]
            if SearchVisitor(uses_var_partial).visit(statement) is None:
                continue
            if not isinstance(statement, (frog_ast.Variable, frog_ast.Assignment)):
                break
            if statement.var != last_statement.expression:
                break
            return self.transform_block(
                frog_ast.Block(block.statements[:index])
                + frog_ast.Block(block.statements[index + 1 : -1])
                + frog_ast.Block([frog_ast.ReturnStatement(statement.value)])
            )

        return block


class ExpandTupleTransformer(Transformer):
    def __init__(self) -> None:
        self.to_transform: list[str] = []
        self.lengths: list[int] = []

    def _is_transformable_tuple(
        self, the_type: frog_ast.Type, name: str, search_space: frog_ast.ASTNode
    ) -> bool:
        return (
            isinstance(the_type, frog_ast.BinaryOperation)
            and the_type.operator == frog_ast.BinaryOperators.MULTIPLY
            and AllConstantFieldAccesses(name).visit(search_space)
        )

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        new_fields = []
        for field in game.fields:
            if self._is_transformable_tuple(field.type, field.name, game):
                assert isinstance(field.type, frog_ast.BinaryOperation)
                unfolded_types = frog_ast.expand_tuple_type(field.type)
                for index, the_type in enumerate(unfolded_types):
                    expression = None
                    if field.value:
                        assert isinstance(field.value, frog_ast.Tuple)
                        expression = field.value.values[index]
                    new_fields.append(
                        frog_ast.Field(the_type, f"{field.name}{index}", expression)
                    )
                self.to_transform.append(field.name)
                self.lengths.append(len(unfolded_types))
            else:
                new_fields.append(field)
        return frog_ast.Game(
            (
                game.name,
                game.parameters,
                new_fields,
                [self.transform(method) for method in game.methods],
                [self.transform(phase) for phase in game.phases],
            )
        )

    def transform_block(self, block: frog_ast.Block) -> frog_ast.Block:
        new_statements: list[frog_ast.Statement] = []
        expanded_tuple_count = 0
        for index, statement in enumerate(block.statements):
            # Assigning to the tuple means assigning each individual value
            if (
                isinstance(statement, frog_ast.Assignment)
                and isinstance(statement.var, frog_ast.Variable)
                and statement.var.name in self.to_transform
            ):
                assert isinstance(statement.value, frog_ast.Tuple)
                for index, tuple_value in enumerate(statement.value.values):
                    new_statements.append(
                        frog_ast.Assignment(
                            None,
                            frog_ast.Variable(f"{statement.var}{index}"),
                            tuple_value,
                        )
                    )
            # Asssigning to a tuple element means assigning to that one element
            elif (
                isinstance(statement, (frog_ast.Assignment, frog_ast.Sample))
                and isinstance(statement.var, frog_ast.ArrayAccess)
                and isinstance(statement.var.the_array, frog_ast.Variable)
                and statement.var.the_array.name in self.to_transform
            ):
                assert isinstance(statement.var.index, frog_ast.Integer)
                new_statement = copy.deepcopy(statement)
                new_statement.var = frog_ast.Variable(
                    f"{statement.var.the_array.name}{statement.var.index.num}",
                )
                new_statements.append(new_statement)
            elif (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.var, frog_ast.Variable)
                and self._is_transformable_tuple(
                    statement.the_type, statement.var.name, block
                )
            ):
                assert isinstance(statement.the_type, frog_ast.BinaryOperation)
                unfolded_types = frog_ast.expand_tuple_type(statement.the_type)
                assert isinstance(statement.value, frog_ast.Tuple)
                for index, the_type in enumerate(unfolded_types):
                    new_statements.append(
                        frog_ast.Assignment(
                            the_type,
                            frog_ast.Variable(f"{statement.var.name}{index}"),
                            statement.value.values[index],
                        )
                    )
                self.to_transform.append(statement.var.name)
                self.lengths.append(len(unfolded_types))
                expanded_tuple_count += 1
            else:
                new_statements.append(statement)
        new_block = frog_ast.Block(
            [self.transform(statement) for statement in new_statements]
        )
        self.to_transform = (
            self.to_transform[:-expanded_tuple_count]
            if expanded_tuple_count > 0
            else self.to_transform
        )
        self.lengths = (
            self.lengths[:-expanded_tuple_count]
            if expanded_tuple_count > 0
            else self.lengths
        )
        return new_block

    def transform_array_access(
        self, array_access: frog_ast.ArrayAccess
    ) -> frog_ast.Expression:
        if (
            not isinstance(array_access.the_array, frog_ast.Variable)
            or array_access.the_array.name not in self.to_transform
        ):
            return frog_ast.ArrayAccess(
                self.transform(array_access.the_array),
                self.transform(array_access.index),
            )
        assert isinstance(array_access.index, frog_ast.Integer)
        return frog_ast.Variable(
            f"{array_access.the_array.name}{array_access.index.num}"
        )

    def transform_variable(self, var: frog_ast.Variable) -> frog_ast.Expression:
        if var.name not in self.to_transform:
            return var
        length = self.lengths[self.to_transform.index(var.name)]
        return frog_ast.Tuple(
            [frog_ast.Variable(f"{var.name}{index}") for index in range(length)]
        )


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


class SimplifyNot(Transformer):
    def transform_unary_operation(
        self, unary_op: frog_ast.UnaryOperation
    ) -> frog_ast.Expression:
        if (
            unary_op.operator == frog_ast.UnaryOperators.NOT
            and isinstance(unary_op.expression, frog_ast.BinaryOperation)
            and unary_op.expression.operator == frog_ast.BinaryOperators.EQUALS
        ):
            return frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.NOTEQUALS,
                unary_op.expression.left_expression,
                unary_op.expression.right_expression,
            )
        return unary_op


class FieldOrderingVisitor(Visitor[dict[str, str]]):
    def __init__(self) -> None:
        self.field_num = 0
        self.fields: list[str] = []
        self.field_rename_map: dict[str, str] = {}
        self.in_initialize = False

    def result(self) -> dict[str, str]:
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
    def visit_variable_declaration(
        self, variable_declaration: frog_ast.VariableDeclaration
    ) -> None:
        self.type_map.set(variable_declaration.name, variable_declaration.the_type)

    @_test_stop
    def visit_parameter(self, parameter: frog_ast.Parameter) -> None:
        self.type_map.set(parameter.name, parameter.type)

    @_test_stop
    def visit_ast_node(self, node: frog_ast.ASTNode) -> None:
        pass


class SimplifyTupleTransformer(Transformer):
    def __init__(self, ast: frog_ast.ASTNode) -> None:
        self.ast = ast

    def transform_tuple(self, the_tuple: frog_ast.Tuple) -> frog_ast.Expression:
        if not all(
            isinstance(value, frog_ast.ArrayAccess) for value in the_tuple.values
        ):
            return the_tuple
        if not all(
            isinstance(value.index, frog_ast.Integer) for value in the_tuple.values  # type: ignore
        ):
            return the_tuple
        if not all(
            value.index.num == index for index, value in enumerate(the_tuple.values)  # type: ignore
        ):
            return the_tuple
        if not all(
            isinstance(value.the_array, frog_ast.Variable) for value in the_tuple.values  # type: ignore
        ):
            return the_tuple
        tuple_val_name = the_tuple.values[0].the_array.name  # type: ignore
        if not all(
            value.the_array.name == tuple_val_name for value in the_tuple.values  # type: ignore
        ):
            return the_tuple

        type_map = GetTypeMapVisitor(the_tuple).visit(self.ast)
        tuple_type = type_map.get(tuple_val_name)
        assert isinstance(tuple_type, frog_ast.BinaryOperation)
        expanded_type_array = frog_ast.expand_tuple_type(tuple_type)
        if len(expanded_type_array) == len(the_tuple.values):
            return frog_ast.Variable(tuple_val_name)
        return the_tuple


def assigns_variable(
    used_variables: list[frog_ast.Variable], node: frog_ast.ASTNode
) -> bool:
    return isinstance(node, (frog_ast.Assignment, frog_ast.Sample)) and (
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

            if not isinstance(statement, frog_ast.Assignment):
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

            if SearchVisitor(contains_func).visit(statement) is not None:
                self.are_same = False
                return

            used_variables = VariableCollectionVisitor().visit(statement.value)

            assigns_variable_partial = functools.partial(
                assigns_variable, used_variables
            )

            paired_value = SubstitutionTransformer(
                [(statement.var, frog_ast.Variable(pair_name))]
            ).transform(statement.value)

            paired = False
            for subsequent_statement in block.statements[index + 1 :]:
                if (
                    SearchVisitor(assigns_variable_partial).visit(subsequent_statement)
                    is not None
                ):
                    self.are_same = False
                    return

                if (
                    isinstance(subsequent_statement, frog_ast.Assignment)
                    and isinstance(subsequent_statement.var, frog_ast.Variable)
                    and subsequent_statement.var.name == pair_name
                    and subsequent_statement.value in (paired_value, statement.var)
                ):
                    paired = True
                    self.paired_statements.append(subsequent_statement)
                    break
            if not paired:
                self.are_same = False
                return


class RemoveStatementTransformer(BlockTransformer):
    def __init__(self, to_remove: list[frog_ast.Statement]):
        self.to_remove = to_remove

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        new_statements = []
        for statement in block.statements:
            if statement not in self.to_remove:
                new_statements.append(statement)
        return frog_ast.Block(new_statements)


# Consider case where else if condition might have a return but then the if condition doesn't
# Then in order to check whether it's definitely true we need (not A and B) where A is first condition and B is second.


class RemoveUnreachableTransformer(BlockTransformer):
    def __init__(self, ast: frog_ast.ASTNode):
        self.ast = ast

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        def contains_unconditional_return(block: frog_ast.Block) -> bool:
            return any(
                isinstance(statement, frog_ast.ReturnStatement)
                for statement in block.statements
            )

        used_variables = VariableCollectionVisitor().visit(block)
        variable_version_map = dict((var.name, 0) for var in used_variables)

        def update_version(node: frog_ast.ASTNode) -> None:
            updated = []

            def assigns_variable_search(search_node: frog_ast.ASTNode) -> bool:
                if not isinstance(search_node, (frog_ast.Assignment, frog_ast.Sample)):
                    return False
                var = None
                if isinstance(search_node.var, frog_ast.Variable):
                    var = search_node.var
                if isinstance(search_node.var, frog_ast.ArrayAccess) and isinstance(
                    search_node.var.the_array, frog_ast.Variable
                ):
                    var = search_node.var.the_array

                if var in used_variables and var not in updated:
                    variable_version_map[var.name] += 1
                    updated.append(var)
                    return True
                return False

            while SearchVisitor(assigns_variable_search).visit(node) is not None:
                pass

        formula_so_far = None

        formula_visitor = Z3FormulaVisitor(NameTypeMap())

        for index, statement in enumerate(block.statements):
            if not isinstance(statement, frog_ast.IfStatement):
                update_version(statement)
                continue

            if statement.has_else_block() and all(
                contains_unconditional_return(if_block) for if_block in statement.blocks
            ):
                return frog_ast.Block(block.statements[: index + 1])
            solver = z3.Solver()

            type_map = GetTypeMapVisitor(statement).visit(self.ast)
            formula_visitor.set_type_map(type_map)
            formula_visitor.set_variable_version_map(variable_version_map)
            condition_formulae: list[z3.AstRef] = []
            for condition_index, condition in enumerate(statement.conditions):
                individual_formula = formula_visitor.visit(condition)
                if individual_formula is None:
                    break
                if contains_unconditional_return(statement.blocks[condition_index]):
                    to_get_here = (
                        individual_formula
                        if not condition_formulae
                        else z3.And(
                            *(
                                z3.Not(condition_formula)
                                for condition_formula in condition_formulae
                            ),
                            individual_formula,
                        )
                    )
                    formula_so_far = (
                        z3.Or(to_get_here, formula_so_far)
                        if formula_so_far is not None
                        else to_get_here
                    )
                condition_formulae.append(individual_formula)

            update_version(statement)
            if formula_so_far is not None:
                solver.add(z3.Not(formula_so_far))
            satisfiable = solver.check()
            solver.reset()
            if satisfiable == z3.unsat:
                return frog_ast.Block(block.statements[: index + 1])

        return block
