from __future__ import annotations
import functools
import copy
from typing import Optional, Callable, Tuple
from . import visitors
from . import frog_ast


def generate_dependency_graph(
    block: frog_ast.Block,
    fields: list[frog_ast.Field],
    proof_namespace: frog_ast.Namespace,
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
                    isinstance(
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


def unnecessary_statement_info(
    fields: list[str], block: frog_ast.Block
) -> Tuple[frog_ast.ASTMap[bool], list[frog_ast.Variable]]:
    required_map = frog_ast.ASTMap[bool]()

    necessary_vars = [frog_ast.Variable(field) for field in fields]

    def remove_helper(block: frog_ast.Block) -> None:
        for statement in block.statements:
            required_map.set(statement, False)
        nonlocal necessary_vars
        for statement in reversed(block.statements):
            if isinstance(
                statement, frog_ast.ReturnStatement
            ) or visitors.assigns_variable(necessary_vars, statement):
                all_vars = visitors.VariableCollectionVisitor().visit(statement)
                necessary_vars += all_vars
                required_map.set(statement, True)
            elif isinstance(statement, frog_ast.NumericFor):
                necessary_vars += visitors.VariableCollectionVisitor().visit(
                    statement.start
                ) + visitors.VariableCollectionVisitor().visit(statement.end)
                remove_helper(statement.block)
            elif isinstance(
                statement,
                frog_ast.GenericFor,
            ):
                necessary_vars += visitors.VariableCollectionVisitor().visit(
                    statement.over
                )
                remove_helper(statement.block)
            elif isinstance(statement, frog_ast.IfStatement):
                for condition in statement.conditions:
                    necessary_vars += visitors.VariableCollectionVisitor().visit(
                        condition
                    )
                for if_block in statement.blocks:
                    remove_helper(if_block)

    remove_helper(block)
    return (required_map, necessary_vars)


def remove_unnecessary_statements(
    fields: list[str], block: frog_ast.Block
) -> frog_ast.Block:
    (required_map, _) = unnecessary_statement_info(fields, block)

    def construct_new(block: frog_ast.Block) -> frog_ast.Block:
        new_statements: list[frog_ast.Statement] = []
        for statement in block.statements:
            if isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
                new_statement = copy.deepcopy(statement)
                nested_block = construct_new(statement.block)
                new_statement.block = nested_block
                new_statements.append(new_statement)
            elif isinstance(statement, frog_ast.IfStatement):
                new_if_statement = copy.deepcopy(statement)
                nested_blocks = [construct_new(block) for block in statement.blocks]
                new_if_statement.blocks = nested_blocks
                new_statements.append(new_if_statement)
            elif required_map.get(statement):
                new_statements.append(statement)
        return frog_ast.Block(new_statements)

    return construct_new(block)


def remove_unnecessary_fields(game: frog_ast.Game) -> frog_ast.Game:
    necessary_vars = []
    for method in game.methods:
        # We pass an empty list of fields
        # so that we can determine which fields are necessary based solely on return values
        necessary_vars += unnecessary_statement_info([], method.block)[1]

    new_game = copy.deepcopy(game)
    new_game.fields = [
        field
        for field in game.fields
        if frog_ast.Variable(field.name) in necessary_vars
    ]
    actually_necessary_field_names = [field.name for field in new_game.fields]
    for method in new_game.methods:
        method.block = remove_unnecessary_statements(
            actually_necessary_field_names, method.block
        )
    return new_game
