import copy
import functools
from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar, Generic, Callable, cast
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

    def visit(self, node: frog_ast.ASTNode | list[frog_ast.ASTNode]) -> U:
        if isinstance(node, list):
            for item in node:
                self.visit(item)
            return self.result()

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
        if isinstance(node, list):
            return [self.transform(item) for item in node]

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


class RedundantCopyTransformer(Transformer):
    def _remove_redundant_copies(
        self,
        statements: list[frog_ast.Statement],
    ) -> list[frog_ast.Statement]:
        for index, statement in enumerate(statements):
            # Potentially, could be a redundant copy
            if (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.value, frog_ast.Variable)
            ):
                # Search through the remaining statements to see if the variable was ever used again.
                original_name = statement.value.name

                def original_used(original_name: str, node: frog_ast.ASTNode):
                    return (
                        isinstance(node, frog_ast.Variable)
                        and node.name == original_name
                    )

                remaining_statements = copy.deepcopy(statements[index + 1 :])
                used_again = SearchVisitor[frog_ast.Variable](
                    functools.partial(original_used, original_name)
                ).visit(remaining_statements)
                # If it was used again, just move on. This ain't gonna work.
                if used_again:
                    continue

                copy_name = statement.var.name

                def copy_used(copy_name: str, node: frog_ast.ASTNode):
                    return (
                        isinstance(node, frog_ast.Variable) and node.name == copy_name
                    )

                while True:
                    copy_found = SearchVisitor[frog_ast.Variable](
                        functools.partial(copy_used, copy_name)
                    ).visit(remaining_statements)
                    if copy_found is None:
                        break
                    remaining_statements = ReplaceTransformer(
                        copy_found, frog_ast.Variable(original_name)
                    ).transform(remaining_statements)

                return self._remove_redundant_copies(
                    copy.deepcopy(statements[:index]) + remaining_statements
                )

        return [self.transform(statement) for statement in statements]

    def transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        new_method = copy.deepcopy(method)
        new_method.statements = self._remove_redundant_copies(method.statements)
        return new_method

    def transform_if_statement(
        self, statement: frog_ast.IfStatement
    ) -> frog_ast.IfStatement:
        new_if = copy.deepcopy(statement)
        new_if.blocks = [
            self._remove_redundant_copies(block) for block in new_if.blocks
        ]
        return new_if

    def transform_generic_for(
        self, statement: frog_ast.GenericFor
    ) -> frog_ast.GenericFor:
        new_statement = copy.deepcopy(statement)
        new_statement.statements = self._remove_redundant_copies(
            new_statement.statements
        )
        return new_statement

    def transform_numeric_for(
        self, statement: frog_ast.NumericFor
    ) -> frog_ast.NumericFor:
        new_statement = copy.deepcopy(statement)
        new_statement.statements = self._remove_redundant_copies(
            new_statement.statements
        )
        return new_statement


class SubstitutionTransformer(Transformer):
    def __init__(self, replace_map: dict[str, frog_ast.ASTNode]):
        self.replace_map = replace_map

    def transform_variable(self, v: frog_ast.Variable) -> frog_ast.ASTNode:
        if v.name in self.replace_map:
            return self.replace_map[v.name]
        return v

    def transform_user_type(self, user_type: frog_ast.UserType) -> frog_ast.ASTNode:
        # For user types, only want to change the first name. Others are considered fields.
        if user_type.names[0].name in self.replace_map:
            replaced_var = self.replace_map[user_type.names[0].name]
            assert isinstance(replaced_var, frog_ast.Variable)
            return frog_ast.UserType([replaced_var] + user_type.names[1:])
        return user_type
