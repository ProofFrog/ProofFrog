import copy
import functools
from . import frog_ast


class RedundantCopyTransformer(frog_ast.Transformer):
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
                used_again = frog_ast.SearchVisitor[frog_ast.Variable](
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
                    copy_found = frog_ast.SearchVisitor[frog_ast.Variable](
                        functools.partial(copy_used, copy_name)
                    ).visit(remaining_statements)
                    if copy_found is None:
                        break
                    remaining_statements = frog_ast.ReplaceTransformer(
                        copy_found, frog_ast.Variable(original_name)
                    ).transform(remaining_statements)

                return copy.deepcopy(statements[:index]) + remaining_statements

        return statements

    def transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        new_method = copy.deepcopy(method)
        new_method.statements = self._remove_redundant_copies(method.statements)
        return new_method

    def transform_if_statement(
        self, statement: frog_ast.IfStatement
    ) -> frog_ast.IfStatement:
        new_if = copy.deepcopy(statement)
        for block in new_if.blocks:
            block = self._remove_redundant_copies(block)
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
