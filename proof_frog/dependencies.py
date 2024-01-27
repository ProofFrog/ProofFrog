from __future__ import annotations
import functools
from typing import Optional, Callable
from . import visitors
from . import frog_ast


def generate_dependency_graph(
    block: frog_ast.Block,
    fields,
    proof_namespace: frog_ast.Namespace,
    return_depends_on_fields=True,
) -> DependencyGraph:
    dependency_graph = DependencyGraph()
    for statement in block.statements:
        dependency_graph.add_node(Node(statement))

    def add_dependency(node_in_graph: Node, statement: frog_ast.Statement) -> None:
        node_in_graph.add_neighbour(dependency_graph.get_node(statement))

    for index, statement in enumerate(block.statements):
        node_in_graph = dependency_graph.get_node(statement)
        earlier_statements = list(block.statements[:index])
        earlier_statements.reverse()

        def contains_return(node: frog_ast.ASTNode) -> bool:
            return isinstance(node, frog_ast.ReturnStatement)

        if visitors.SearchVisitor(contains_return).visit(statement):
            for preceding_statement in block.statements[:index]:
                if (
                    return_depends_on_fields
                    and isinstance(
                        preceding_statement, (frog_ast.Sample, frog_ast.Assignment)
                    )
                    and isinstance(preceding_statement.var, frog_ast.Variable)
                    and preceding_statement.var.name in [field.name for field in fields]
                ) or visitors.SearchVisitor(contains_return).visit(
                    preceding_statement
                ) is not None:
                    add_dependency(node_in_graph, preceding_statement)

        variables = visitors.VariableCollectionVisitor().visit(statement)
        for variable in variables:
            for depends_on in earlier_statements:
                if variable.name in proof_namespace:
                    continue

                def search_for_assignment(
                    variable: frog_ast.Variable, node: frog_ast.ASTNode
                ) -> bool:
                    return node == variable

                if (
                    visitors.SearchVisitor(
                        functools.partial(search_for_assignment, variable)
                    ).visit(depends_on)
                    is not None
                ):
                    add_dependency(node_in_graph, depends_on)
                    break

    return dependency_graph


class Node:
    def __init__(self, statement: frog_ast.Statement) -> None:
        self.in_neighbours: list[Node] = []
        self.statement = statement

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Node):
            return False
        return (
            self.in_neighbours == __value.in_neighbours
            and self.statement == __value.statement
        )

    def add_neighbour(self, neighbour: Node) -> None:
        if not neighbour in self.in_neighbours:
            self.in_neighbours.append(neighbour)


class DependencyGraph:
    def __init__(self, nodes: Optional[list[Node]] = None) -> None:
        self.nodes: list[Node] = nodes if nodes else []

    def add_node(self, new_node: Node) -> None:
        self.nodes.append(new_node)

    def get_node(self, statement: frog_ast.Statement) -> Node:
        for potential_node in self.nodes:
            if potential_node.statement == statement:
                return potential_node
        raise ValueError("Statement not found in graph")

    def find_node(
        self, predicate: Callable[[frog_ast.Statement], bool]
    ) -> Optional[Node]:
        for node in self.nodes:
            if predicate(node.statement):
                return node
        return None

    def __str__(self) -> str:
        result = ""
        for node in self.nodes:
            result += f'{node.statement} depends on: {"nothing" if not node.in_neighbours else ""}\n'
            for neighbour in node.in_neighbours:
                result += f"  - {neighbour.statement}\n"
        return result

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, DependencyGraph):
            return False
        return self.nodes == __value.nodes