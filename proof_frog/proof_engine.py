from __future__ import annotations
import os
import sys
import copy
import functools
from collections import namedtuple
from typing import TypeAlias, Sequence, Tuple, Dict, Optional, Callable
from colorama import Fore
from sympy import Symbol
from . import frog_parser
from . import frog_ast
from . import visitors

MethodLookup: TypeAlias = Dict[Tuple[str, str], frog_ast.Method]

inline_counter: int = 0


class ProofEngine:
    def __init__(self, proof_file_name: str, verbose: bool) -> None:
        self.proof_file = frog_parser.parse_proof_file(proof_file_name)
        self.definition_namespace: frog_ast.Namespace = {}
        self.proof_namespace: frog_ast.Namespace = {}

        for imp in self.proof_file.imports:
            file_type = _get_file_type(imp.filename)
            root: frog_ast.Root
            match file_type:
                case frog_ast.FileType.PRIMITIVE:
                    root = frog_parser.parse_primitive_file(imp.filename)
                case frog_ast.FileType.SCHEME:
                    root = frog_parser.parse_scheme_file(imp.filename)
                case frog_ast.FileType.GAME:
                    root = frog_parser.parse_game_file(imp.filename)
                case frog_ast.FileType.PROOF:
                    raise TypeError("Cannot import proofs")

            name = imp.rename if imp.rename else root.get_export_name()
            self.definition_namespace[name] = root

        for game in self.proof_file.helpers:
            self.definition_namespace[game.name] = game

        self.variables: dict[str, Symbol | frog_ast.Expression] = {}

        # Here, we are substituting the lets with the parameters they are given
        for let in self.proof_file.lets:
            if isinstance(let.value, frog_ast.FuncCallExpression) and isinstance(
                let.value.func, frog_ast.Variable
            ):
                definition = copy.deepcopy(
                    self.definition_namespace[let.value.func.name]
                )
                if isinstance(definition, frog_ast.Scheme):
                    self.proof_namespace[let.name] = self.instantiate_scheme(
                        definition, let.value.args
                    )
                elif isinstance(definition, frog_ast.Primitive):
                    self.proof_namespace[let.name] = self.instantiate_primitive(
                        definition, let.value.args
                    )
                else:
                    raise TypeError("Must instantiate either a Primitive or Scheme ")
            else:
                self.proof_namespace[let.name] = copy.deepcopy(let.value)
                if isinstance(let.type, frog_ast.IntType):
                    if let.value is not None:
                        self.variables[let.name] = let.value
                    else:
                        sympy_symbol: Symbol = Symbol(let.name)  # type: ignore
                        self.variables[let.name] = sympy_symbol

        self.get_method_lookup()
        self.verbose = verbose

    def prove(self) -> None:
        first_step = self.proof_file.steps[0]
        final_step = self.proof_file.steps[-1]

        assert isinstance(first_step, frog_ast.Step)
        assert isinstance(final_step, frog_ast.Step)

        assert isinstance(first_step.challenger, frog_ast.ConcreteGame)
        assert isinstance(final_step.challenger, frog_ast.ConcreteGame)

        if first_step.challenger.game != self.proof_file.theorem:
            print(Fore.RED + "Proof must start with a game matching theorem")
            print(Fore.RED + f"Theorem: {self.proof_file.theorem}")
            print(Fore.RED + f"First Game: {first_step.challenger}")

        self.prove_steps(self.proof_file.steps)

        if (
            first_step.challenger.game == final_step.challenger.game
            and first_step.challenger.which != final_step.challenger.which
            and first_step.adversary == final_step.adversary
        ):
            print(Fore.GREEN + "Proof Suceeded!")
            return
        print(Fore.YELLOW + "Proof Succeeded, but is incomplete")
        sys.exit(1)

    def prove_steps(self, steps: list[frog_ast.ProofStep]) -> None:
        for i in range(0, len(steps) - 1):
            print(f"===STEP {i}===")
            current_step = steps[i]
            next_step = steps[i + 1]
            print(f"Current: {current_step}")
            print(f"Hop To: {next_step}\n")

            if isinstance(current_step, frog_ast.Step) and isinstance(
                next_step, frog_ast.Induction
            ):
                current_game_ast = self._get_game_ast(
                    current_step.challenger, current_step.reduction
                )
                first_inductive_step = next_step.steps[0]
                assert isinstance(first_inductive_step, frog_ast.Step)
                first_inductive_step = visitors.SubstitutionTransformer(
                    [(frog_ast.Variable(next_step.name), next_step.start)]
                ).transform(first_inductive_step)
                next_game_ast = self._get_game_ast(
                    first_inductive_step.challenger, first_inductive_step.reduction
                )
                self.check_equivalent(current_game_ast, next_game_ast)
                continue

            assert isinstance(current_step, frog_ast.Step)
            assert isinstance(next_step, frog_ast.Step)

            if self._is_by_assumption(current_step, next_step):
                print("Valid by assumption")
                continue

            current_game_ast = self._get_game_ast(
                current_step.challenger, current_step.reduction
            )
            next_game_ast = self._get_game_ast(
                next_step.challenger, next_step.reduction
            )

            self.check_equivalent(current_game_ast, next_game_ast)

    def check_equivalent(
        self, current_game_ast: frog_ast.Game, next_game_ast: frog_ast.Game
    ) -> None:
        AstManipulator = namedtuple("AstManipulator", ["fn", "name"])
        ast_manipulators: list[AstManipulator] = [
            AstManipulator(
                fn=lambda ast: visitors.RemoveTupleTransformer().transform(ast),
                name="Remove Tuples",
            ),
            AstManipulator(
                fn=lambda ast: visitors.SymbolicComputationTransformer(
                    self.variables
                ).transform(ast),
                name="Symbolic Computation",
            ),
            AstManipulator(
                fn=lambda ast: visitors.SimplifySpliceTransformer(
                    self.variables
                ).transform(ast),
                name="Simplifying Splices",
            ),
            AstManipulator(
                fn=lambda ast: visitors.RedundantCopyTransformer().transform(ast),
                name="Remove Redundant Copies",
            ),
            AstManipulator(fn=self.sort_game, name="Topological Sorting"),
            AstManipulator(
                fn=lambda ast: visitors.VariableStandardizingTransformer().transform(
                    ast
                ),
                name="Variable Standardizing",
            ),
        ]

        for index, game in enumerate((current_game_ast, next_game_ast)):
            if index == 0:
                print("SIMPLIFYING CURRENT GAME")
                print(current_game_ast)
            else:
                print("SIMPLIFYING NEXT GAME")
                print(next_game_ast)

            while True:

                def apply_manipulators(game: frog_ast.Game) -> frog_ast.Game:
                    for manipulator in ast_manipulators:
                        new_game = manipulator.fn(game)
                        if self.verbose and game != new_game:
                            print(f"APPLIED {manipulator.name}")
                            print(new_game)
                        game = new_game
                    return game

                new_game = apply_manipulators(game)
                if new_game != game:
                    if index == 0:
                        current_game_ast = new_game
                    else:
                        next_game_ast = new_game
                    game = new_game
                else:
                    break
        print("CURRENT")
        print(current_game_ast)
        print("NEXT")
        print(next_game_ast)

        if current_game_ast == next_game_ast:
            print("Inline Success!")
            return

        print("Step failed!")
        print(Fore.RED + "Proof Failed!")
        sys.exit(1)

    def apply_reduction(
        self,
        challenger: frog_ast.Game,
        reduction: frog_ast.Reduction,
    ) -> frog_ast.Game:
        print("Reduction to apply:")
        print(reduction)
        print("Challenger:")
        print(challenger)
        name = "Inlined"
        parameters = challenger.parameters
        new_fields = [
            frog_ast.Field(field.type, "challenger@" + field.name, field.value)
            for field in challenger.fields
        ]
        fields = new_fields + copy.deepcopy(reduction.fields)
        phases = challenger.phases
        methods = copy.deepcopy(reduction.methods)
        reduced_game = frog_ast.Game((name, parameters, fields, methods, phases))

        if challenger.has_method("Initialize") and not reduced_game.has_method(
            "Initialize"
        ):
            reduced_game.methods.insert(0, challenger.get_method("Initialize"))

        return reduced_game

    # Takes in a game from a proof step, and returns the AST associated with that game
    def _get_game_ast(
        self,
        challenger: frog_ast.ParameterizedGame | frog_ast.ConcreteGame,
        reduction: Optional[frog_ast.ParameterizedGame] = None,
    ) -> frog_ast.Game:
        game: frog_ast.Game
        if isinstance(challenger, frog_ast.ConcreteGame):
            game_file = self.definition_namespace[challenger.game.name]
            assert isinstance(game_file, frog_ast.GameFile)
            game = self.instantiate_game(
                game_file.get_game(challenger.which), challenger.game.args
            )
        else:
            game_node = self.definition_namespace[challenger.name]
            assert isinstance(game_node, frog_ast.Game)
            game = self.instantiate_game(game_node, challenger.args)

        lookup = copy.deepcopy(self.method_lookup)
        if reduction:
            reduction_ast = self._get_game_ast(reduction)
            assert isinstance(reduction_ast, frog_ast.Reduction)
            for index, method in enumerate(game.methods):
                game.methods[index] = visitors.SubstitutionTransformer(
                    [
                        (
                            frog_ast.Variable(field.name),
                            frog_ast.Variable("challenger@" + field.name),
                        )
                        for field in game.fields
                    ]
                ).transform(method)
            lookup.update(get_challenger_method_lookup(game))
            game = self.apply_reduction(game, reduction_ast)

        while True:
            new_game = visitors.InlineTransformer(lookup).transform(game)
            if game != new_game:
                game = new_game
            else:
                break
        return game

    # Replace a game's parameter list with empty, and instantiate the game with
    # the parameterized value
    def instantiate_game(
        self,
        game: frog_ast.Game,
        parameters: Sequence[frog_ast.ASTNode],
    ) -> frog_ast.Game:
        game_copy = copy.deepcopy(game)
        replace_map: list[Tuple[frog_ast.ASTNode, frog_ast.ASTNode]] = []
        for index, parameter in enumerate(game.parameters):
            replace_map.append((frog_ast.Variable(parameter.name), parameters[index]))

        game_copy.parameters = []

        new_game = visitors.SubstitutionTransformer(replace_map).transform(game_copy)

        new_game = visitors.InstantiationTransformer(self.proof_namespace).transform(
            new_game
        )

        return new_game

    def get_method_lookup(self) -> None:
        self.method_lookup: MethodLookup = {}

        for name, node in self.proof_namespace.items():
            if isinstance(node, frog_ast.Scheme):
                for method in node.methods:
                    self.method_lookup[(name, method.signature.name)] = method

    def _is_by_assumption(
        self,
        current_step: frog_ast.Step,
        next_step: frog_ast.Step,
    ) -> bool:
        if not isinstance(
            current_step.challenger, frog_ast.ConcreteGame
        ) or not isinstance(next_step.challenger, frog_ast.ConcreteGame):
            return False
        return bool(
            current_step.challenger.game == next_step.challenger.game
            and current_step.reduction
            and current_step.reduction == next_step.reduction
            and current_step.adversary == next_step.adversary
            and current_step.challenger.game in self.proof_file.assumptions
        )

    def sort_game(self, game: frog_ast.Game) -> frog_ast.Game:
        new_game = copy.deepcopy(game)
        for method in new_game.methods:
            method.block = self.sort_block(game, method.block)
        return new_game

    def sort_block(self, game: frog_ast.Game, block: frog_ast.Block) -> frog_ast.Block:
        graph = generate_dependency_graph(block, self.proof_namespace)

        def is_return(node: frog_ast.ASTNode) -> bool:
            return node in block.statements and isinstance(
                node, frog_ast.ReturnStatement
            )

        dfs_stack: list[Node] = []
        if graph.find_node(is_return):
            dfs_stack.append(graph.find_node(is_return))
        dfs_stack_visited = [False] * len(block.statements)
        dfs_sorted_statements: list[frog_ast.Statement] = []
        while dfs_stack:
            node = dfs_stack.pop()
            dfs_sorted_statements.append(node.statement)
            if not dfs_stack_visited[block.statements.index(node.statement)]:
                dfs_stack_visited[block.statements.index(node.statement)] = True
                for neighbour in node.in_neighbours:
                    dfs_stack.append(neighbour)

        for statement in block.statements:

            def uses_field(node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.Variable) and node.name in [
                    field.name for field in game.fields
                ]

            found = visitors.SearchVisitor(uses_field).visit(statement)
            if statement not in dfs_sorted_statements and found is not None:
                dfs_sorted_statements.append(statement)

        dfs_sorted_statements.reverse()

        sorted_statements: list[frog_ast.Statement] = []
        stack: list[Node] = []

        for statement in dfs_sorted_statements:
            if not graph.get_node(statement).in_neighbours:
                stack.append(graph.get_node(statement))
        while stack:
            node = stack.pop()
            sorted_statements.append(node.statement)
            for other_node in graph.nodes:
                if node in other_node.in_neighbours:
                    other_node.in_neighbours.remove(node)
                    if not other_node.in_neighbours:
                        stack.append(other_node)

        return frog_ast.Block(sorted_statements)

    # I want to be able to instantiate primitives and schemes
    # What does this entail? For primitives, all I have are fields and
    # method signatures. So I'd like to:
    # 1 - Set fields to values gotten from the proof namespace
    # 2 - Change method signatures: either those that rely on external values,
    #     or those that refer to the fields
    # 3 - For schemes, might need to change things in the method bodies.
    def instantiate_primitive(
        self,
        primitive: frog_ast.Primitive,
        args: list[frog_ast.Expression],
    ) -> frog_ast.Primitive:
        replace_map: list[Tuple[frog_ast.ASTNode, frog_ast.ASTNode]] = []
        for index, parameter in enumerate(primitive.parameters):
            replace_map.append(
                (frog_ast.Variable(parameter.name), copy.deepcopy(args[index]))
            )
        new_primitive = visitors.SubstitutionTransformer(replace_map).transform(
            primitive
        )
        new_primitive.parameters.clear()
        return visitors.InstantiationTransformer(self.proof_namespace).transform(
            new_primitive
        )

    def instantiate_scheme(
        self,
        scheme: frog_ast.Scheme,
        args: list[frog_ast.Expression],
    ) -> frog_ast.Scheme:
        replace_map: list[Tuple[frog_ast.ASTNode, frog_ast.ASTNode]] = []
        for index, parameter in enumerate(scheme.parameters):
            replace_map.append(
                (frog_ast.Variable(parameter.name), copy.deepcopy(args[index]))
            )
        new_scheme = visitors.SubstitutionTransformer(replace_map).transform(scheme)
        new_scheme.parameters.clear()
        return visitors.InstantiationTransformer(self.proof_namespace).transform(
            new_scheme
        )


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip(".")
    return frog_ast.FileType(extension)


def get_challenger_method_lookup(challenger: frog_ast.Game) -> MethodLookup:
    return dict(
        zip(
            (("challenger", method.signature.name) for method in challenger.methods),
            challenger.methods,
        )
    )


def generate_dependency_graph(
    block: frog_ast.Block, proof_namespace: frog_ast.Namespace
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

        if isinstance(statement, frog_ast.ReturnStatement):
            if index > 0:
                add_dependency(node_in_graph, block.statements[index - 1])

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
