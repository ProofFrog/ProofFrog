from __future__ import annotations
import copy
import functools
import operator
from collections import namedtuple
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

from proof_frog import frog_ast
from proof_frog import frog_parser
from . import frog_ast


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

    def visit(self, node: frog_ast.ASTNode) -> U:
        visit_name = "visit_" + _to_snake_case(type(node).__name__)
        if hasattr(self, visit_name):
            getattr(self, visit_name)(node)
        elif hasattr(self, "visit_ast_node"):
            getattr(self, "visit_ast_node")(node)

        def visit_children(child: Any) -> Any:
            if isinstance(child, frog_ast.ASTNode):
                self.visit(child)
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
        self.field_counter = 0
        self.field_name_map: list[tuple[frog_ast.ASTNode, frog_ast.ASTNode]] = []

    def transform_field(self, field: frog_ast.Field) -> frog_ast.Field:
        self.field_counter += 1
        new_name = "field" + str(self.field_counter)
        self.field_name_map.append(
            (frog_ast.Variable(field.name), frog_ast.Variable(new_name))
        )
        return frog_ast.Field(field.type, new_name, field.value)

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
        return SubstitutionTransformer(self.field_name_map).transform(new_block)


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
    def __init__(self, type_map: NameTypeMap) -> None:
        self.stack: list[Optional[z3.AstRef]] = []
        self.type_map = type_map

    def result(self) -> Optional[z3.AstRef]:
        return self.stack[-1]

    def visit_variable(self, var: frog_ast.Variable) -> None:
        if isinstance(self.type_map.get(var.name), frog_ast.IntType):
            self.stack.append(z3.Int(var.name))
        else:
            self.stack.append(None)

    def visit_integer(self, node: frog_ast.Integer) -> None:
        self.stack.append(node.num)

    def leave_binary_operation(self, op: frog_ast.BinaryOperation) -> None:
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
        right_item = self.stack.pop()
        left_item = self.stack.pop()
        if right_item is not None and left_item is not None:
            self.stack.append(operators[op.operator](left_item, right_item))
        else:
            self.stack.append(None)


class SimplifyRangeTransformer(Transformer):
    def __init__(
        self,
        proof_let_types: NameTypeMap,
        game: frog_ast.Game,
        binary_op: frog_ast.BinaryOperation,
    ) -> None:
        self.game = game
        self.proof_let_types = proof_let_types
        type_map = GetTypeMapVisitor(game.methods[0]).visit(game) + proof_let_types
        self.assumed_formula = Z3FormulaVisitor(type_map).visit(binary_op)
        if self.assumed_formula is not None:
            self.solver = z3.Solver()
            self.solver.add(self.assumed_formula)

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        if (
            binary_operation.operator
            not in (
                frog_ast.BinaryOperators.EQUALS,
                frog_ast.BinaryOperators.NOTEQUALS,
                frog_ast.BinaryOperators.LEQ,
                frog_ast.BinaryOperators.LT,
                frog_ast.BinaryOperators.GT,
                frog_ast.BinaryOperators.GEQ,
                frog_ast.BinaryOperators.AND,
                frog_ast.BinaryOperators.OR,
            )
            or self.assumed_formula is None
        ):
            return binary_operation
        type_map = (
            GetTypeMapVisitor(binary_operation).visit(self.game) + self.proof_let_types
        )
        statement_formula = Z3FormulaVisitor(type_map).visit(binary_operation)
        if statement_formula is None:
            return binary_operation
        self.solver.push()
        self.solver.add(statement_formula)
        satisfied = self.solver.check() == z3.sat
        self.solver.pop()
        if not satisfied:
            return frog_ast.Boolean(False)
        s = z3.Solver()
        s.add(z3.Not(z3.Implies(self.assumed_formula, statement_formula)))
        if s.check() == z3.unsat:
            return frog_ast.Boolean(True)
        return binary_operation


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
    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        if not block.statements:
            return block
        last_statement = block.statements[-1]
        if not isinstance(last_statement, frog_ast.ReturnStatement):
            return block
        if not isinstance(last_statement.expression, frog_ast.Variable):
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

    def _expand_tuple_type(
        self, the_type: frog_ast.BinaryOperation
    ) -> list[frog_ast.Type]:
        unfolded_types: list[frog_ast.Type] = []
        expanded_type: frog_ast.Type | frog_ast.Expression = the_type
        while isinstance(expanded_type, frog_ast.BinaryOperation):
            left_expr = expanded_type.left_expression
            assert isinstance(left_expr, frog_ast.Type)
            unfolded_types.append(left_expr)
            expanded_type = expanded_type.right_expression
        assert isinstance(expanded_type, frog_ast.Type)
        unfolded_types.append(expanded_type)
        return unfolded_types

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        new_fields = []
        for field in game.fields:
            if self._is_transformable_tuple(field.type, field.name, game):
                assert isinstance(field.type, frog_ast.BinaryOperation)
                unfolded_types = self._expand_tuple_type(field.type)
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
                unfolded_types = self._expand_tuple_type(statement.the_type)
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


NameTypePair = namedtuple("NameTypePair", ["name", "type"])


class NameTypeMap:
    def __init__(self):
        self.type_map: list[NameTypePair] = []

    def set(self, name: str, the_type: frog_ast.Type):
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

    def __add__(self, other: NameTypeMap):
        new_map = NameTypeMap()
        for val in self.type_map:
            new_map.set(val.name, val.type)
        for val in other.type_map:
            new_map.set(val.name, val.type)
        return new_map


def _test_stop(func):
    def wrapper(self, param):
        if param is self.stopping_point:
            self.stopped = True
        if not self.stopped:
            func(self, param)

    return wrapper


class GetTypeMapVisitor(Visitor[NameTypeMap]):
    def __init__(self, stopping_point: frog_ast.ASTNode):
        self.stopping_point = stopping_point
        self.stopped = False
        self.type_map = NameTypeMap()

    def result(self) -> NameTypeMap:
        return self.type_map

    @_test_stop
    def visit_field(self, field: frog_ast.Field):
        self.type_map.set(field.name, field.type)

    @_test_stop
    def visit_assignment(self, assignment: frog_ast.Assignment):
        if assignment.the_type is not None:
            assert isinstance(assignment.var, frog_ast.Variable)
            self.type_map.set(assignment.var.name, assignment.the_type)

    @_test_stop
    def visit_sample(self, sample: frog_ast.Sample):
        if sample.the_type is not None:
            assert isinstance(sample.var, frog_ast.Variable)
            self.type_map.set(sample.var.name, sample.the_type)

    @_test_stop
    def visit_variable_declaration(
        self, variable_declaration: frog_ast.VariableDeclaration
    ):
        self.type_map.set(variable_declaration.name, variable_declaration.the_type)

    @_test_stop
    def visit_parameter(self, parameter: frog_ast.Parameter):
        self.type_map.set(parameter.name, parameter.type)

    @_test_stop
    def visit_ast_node(self, node: frog_ast.ASTNode):
        pass
