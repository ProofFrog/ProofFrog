from __future__ import annotations
import functools
import copy
from typing import Optional, Callable
from . import visitors
from . import frog_ast


def generate_dependency_graph(
    block: frog_ast.Block,
    fields: list[frog_ast.Field],
    proof_namespace: frog_ast.Namespace,
    return_depends_on_fields: bool = True,
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


class UnnecessaryFieldVisitor(visitors.Visitor[list[str]]):
    def __init__(self, proof_namespace: frog_ast.Namespace) -> None:
        self.proof_namespace = proof_namespace
        self.all_fields: list[frog_ast.Field] = []
        self.unnecessary_fields: dict[str, bool] = {}

    def result(self) -> list[str]:
        return self._get_unnecessary_field_list()

    def _get_unnecessary_field_list(self) -> list[str]:
        return [
            field_name
            for field_name, unnecessary in self.unnecessary_fields.items()
            if unnecessary
        ]

    def visit_game(self, game: frog_ast.Game) -> None:
        # Initially, all fields are considered unnecessary
        # We will flip them if we find a method that uses them
        for field in game.fields:
            self.unnecessary_fields[field.name] = True

        self.all_fields = game.fields

    def visit_method(self, method: frog_ast.Method) -> None:
        graph = generate_dependency_graph(
            method.block, self.all_fields, self.proof_namespace, False
        )

        def has_return_statement(node: frog_ast.ASTNode) -> bool:
            return isinstance(node, frog_ast.ReturnStatement)

        def search_dependencies(node: Node) -> None:
            visited = [False] * len(graph.nodes)
            to_visit: list[Node] = [node]
            while to_visit:
                cur = to_visit.pop()
                if not visited[method.block.statements.index(cur.statement)]:
                    visited[method.block.statements.index(cur.statement)] = True

                    def find_field_usage(node: frog_ast.ASTNode) -> bool:
                        return (
                            isinstance(node, frog_ast.Variable)
                            and node.name in self._get_unnecessary_field_list()
                        )

                    found = visitors.SearchVisitor(find_field_usage).visit(
                        cur.statement
                    )
                    while found is not None:
                        self.unnecessary_fields[found.name] = False
                        found = visitors.SearchVisitor(find_field_usage).visit(
                            cur.statement
                        )

                    for neighbour in cur.in_neighbours:
                        to_visit.append(neighbour)

        for node in graph.nodes:
            if visitors.SearchVisitor(has_return_statement).visit(node.statement):
                search_dependencies(node)


class BubbleSortFieldAssignment(visitors.BlockTransformer):
    def __init__(self) -> None:
        self.fields: list[frog_ast.Field] = []

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        new_game = copy.deepcopy(game)
        self.fields = new_game.fields
        new_game.methods = [self.transform(method) for method in new_game.methods]
        return new_game

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        graph = generate_dependency_graph(block, self.fields, {})
        new_statements = list(copy.deepcopy(block.statements))
        while True:
            swapped = False
            for i in range(1, len(new_statements)):
                first = new_statements[i - 1]
                second = new_statements[i]
                if (
                    isinstance(first, (frog_ast.Assignment, frog_ast.Sample))
                    and isinstance(second, (frog_ast.Assignment, frog_ast.Sample))
                    and isinstance(first.var, frog_ast.Variable)
                    and isinstance(second.var, frog_ast.Variable)
                    and first.var.name in [field.name for field in self.fields]
                    and second.var.name in [field.name for field in self.fields]
                    and first.var.name > second.var.name
                    and graph.get_node(first)
                    not in graph.get_node(second).in_neighbours
                ):
                    new_statements[i - 1] = second
                    new_statements[i] = first
                    swapped = True
            if not swapped:
                break
        return frog_ast.Block(new_statements)
