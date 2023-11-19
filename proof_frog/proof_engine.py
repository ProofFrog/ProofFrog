from __future__ import annotations
import os
import sys
import copy
import functools
from typing import TypeAlias, Sequence, Tuple, Dict, Optional, Callable
from colorama import Fore
from . import frog_parser
from . import frog_ast
from . import visitors

MethodLookup: TypeAlias = Dict[Tuple[str, str], frog_ast.Method]

inline_counter: int = 0


def prove(proof_file_name: str) -> None:
    proof_file = frog_parser.parse_proof_file(proof_file_name)
    definition_namespace: frog_ast.Namespace = {}
    proof_namespace: frog_ast.Namespace = {}

    for imp in proof_file.imports:
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
        definition_namespace[name] = root

    for game in proof_file.helpers:
        definition_namespace[game.name] = game

    # Here, we are substituting the lets with the parameters they are given
    for let in proof_file.lets:
        if isinstance(let.value, frog_ast.FuncCallExpression) and isinstance(
            let.value.func, frog_ast.Variable
        ):
            definition = copy.deepcopy(definition_namespace[let.value.func.name])
            if isinstance(definition, frog_ast.Scheme):
                proof_namespace[let.name] = instantiate_scheme(
                    proof_namespace, definition, let.value.args
                )
            elif isinstance(definition, frog_ast.Primitive):
                proof_namespace[let.name] = instantiate_primitive(
                    proof_namespace, definition, let.value.args
                )
            else:
                raise TypeError("Must instantiate either a Primitive or Scheme ")
        else:
            proof_namespace[let.name] = copy.deepcopy(let.value)

    method_lookup: MethodLookup = get_method_lookup(proof_namespace)

    current_step: frog_ast.ProofStep
    next_step: frog_ast.ProofStep

    for i in range(0, len(proof_file.steps) - 1):
        current_step = proof_file.steps[i]
        next_step = proof_file.steps[i + 1]
        # Right now, cannot handle induction.
        assert isinstance(current_step, frog_ast.Step)
        assert isinstance(next_step, frog_ast.Step)

        print(f"===STEP {i}===")
        print(f"Current: {current_step}")
        print(f"Hop To: {next_step}\n")

        if _is_by_assumption(proof_file, current_step, next_step):
            print("Valid by assumption")
            continue

        current_game_ast = _get_game_ast(
            definition_namespace, proof_namespace, current_step.challenger
        )
        current_game_lookup = copy.deepcopy(method_lookup)
        if current_step.reduction:
            reduction = _get_game_ast(
                definition_namespace, proof_namespace, current_step.reduction
            )
            assert isinstance(reduction, frog_ast.Reduction)
            current_game_lookup.update(get_challenger_method_lookup(current_game_ast))
            current_game_ast = apply_reduction(
                current_game_ast, reduction, definition_namespace
            )

        next_game_lookup = copy.deepcopy(method_lookup)
        next_game_ast = _get_game_ast(
            definition_namespace, proof_namespace, next_step.challenger
        )
        if next_step.reduction:
            reduction = _get_game_ast(
                definition_namespace, proof_namespace, next_step.reduction
            )
            assert isinstance(reduction, frog_ast.Reduction)
            next_game_lookup.update(get_challenger_method_lookup(next_game_ast))
            next_game_ast = apply_reduction(
                next_game_ast, reduction, definition_namespace
            )

        current_game_ast = inline_calls(current_game_lookup, current_game_ast)
        next_game_ast = inline_calls(next_game_lookup, next_game_ast)

        current_game_ast = visitors.RedundantCopyTransformer().transform(
            current_game_ast
        )
        next_game_ast = visitors.RedundantCopyTransformer().transform(next_game_ast)

        current_game_ast = visitors.RemoveTupleTransformer().transform(current_game_ast)
        next_game_ast = visitors.RemoveTupleTransformer().transform(next_game_ast)

        current_game_ast = sort_game(current_game_ast, proof_namespace)
        next_game_ast = sort_game(next_game_ast, proof_namespace)

        current_game_ast = visitors.VariableStandardizingTransformer().transform(
            current_game_ast
        )
        next_game_ast = visitors.VariableStandardizingTransformer().transform(
            next_game_ast
        )

        print("Current Game:")
        print(current_game_ast)
        print("Next Game:")
        print(next_game_ast)

        if current_game_ast == next_game_ast:
            print("Inline Success!")
            continue

        print("Step failed!")
        print(Fore.RED + "Proof Failed!")
        sys.exit(1)

    print(Fore.GREEN + "Proof Suceeded!")


def get_method_lookup(definition_namespace: frog_ast.Namespace) -> MethodLookup:
    method_lookup: MethodLookup = {}

    for name, node in definition_namespace.items():
        if isinstance(node, frog_ast.Scheme):
            for method in node.methods:
                method_lookup[(name, method.signature.name)] = method

    return method_lookup


# pylint: disable-next=unused-argument
def apply_reduction(
    challenger: frog_ast.Game,
    reduction: frog_ast.Reduction,
    _namespace: frog_ast.Namespace,
) -> frog_ast.Game:
    print("Reduction to apply:")
    print(reduction)
    print("Challenger:")
    print(challenger)
    name = "Inlined"
    parameters = challenger.parameters
    fields = copy.deepcopy(challenger.fields) + copy.deepcopy(reduction.fields)
    phases = challenger.phases
    methods = copy.deepcopy(reduction.methods)
    reduced_game = frog_ast.Game((name, parameters, fields, methods, phases))

    if challenger.has_method("Initialize") and not reduced_game.has_method(
        "Initialize"
    ):
        reduced_game.methods.insert(0, challenger.get_method("Initialize"))

    return reduced_game


def _get_game_ast(
    # Takes in a game from a proof step, and returns the AST associated with that game
    definition_namespace: frog_ast.Namespace,
    proof_namespace: frog_ast.Namespace,
    challenger: frog_ast.ParameterizedGame | frog_ast.ConcreteGame,
) -> frog_ast.Game:
    if isinstance(challenger, frog_ast.ConcreteGame):
        game_file = definition_namespace[challenger.game.name]
        assert isinstance(game_file, frog_ast.GameFile)
        game = game_file.get_game(challenger.which)
        return instantiate_game(game, challenger.game.args, proof_namespace)

    game_node = definition_namespace[challenger.name]
    assert isinstance(game_node, frog_ast.Game)
    return instantiate_game(game_node, challenger.args, proof_namespace)


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip(".")
    return frog_ast.FileType(extension)


def _is_by_assumption(
    proof_file: frog_ast.ProofFile,
    current_step: frog_ast.Step,
    next_step: frog_ast.Step,
) -> bool:
    if not isinstance(current_step.challenger, frog_ast.ConcreteGame) or not isinstance(
        next_step.challenger, frog_ast.ConcreteGame
    ):
        return False
    return bool(
        current_step.challenger.game == next_step.challenger.game
        and current_step.reduction
        and current_step.reduction == next_step.reduction
        and current_step.adversary == next_step.adversary
        and current_step.challenger.game in proof_file.assumptions
    )


# Replace a game's parameter list with empty, and instantiate the game with
# the parameterized value
def instantiate_game(
    game: frog_ast.Game,
    parameters: Sequence[frog_ast.ASTNode],
    proof_namespace: frog_ast.Namespace,
) -> frog_ast.Game:
    game_copy = copy.deepcopy(game)
    replace_map: list[Tuple[frog_ast.ASTNode, frog_ast.ASTNode]] = []
    for index, parameter in enumerate(game.parameters):
        replace_map.append((frog_ast.Variable(parameter.name), parameters[index]))

    game_copy.parameters = []

    new_game = visitors.SubstitutionTransformer(replace_map).transform(game_copy)

    new_game = visitors.InstantiationTransformer(proof_namespace).transform(new_game)

    return new_game


def get_challenger_method_lookup(challenger: frog_ast.Game) -> MethodLookup:
    return dict(
        zip(
            (("challenger", method.signature.name) for method in challenger.methods),
            challenger.methods,
        )
    )


def inline_calls(lookup: MethodLookup, game: frog_ast.Game) -> frog_ast.Game:
    new_game = copy.deepcopy(game)
    for method in new_game.methods:
        new_block = inline_call(lookup, method.block)
        if new_block != method.block:
            method.block = new_block
            return inline_calls(lookup, new_game)
    return new_game


# Inline a single call. Goes through statements and first challenger call (as well as innermost)
# will be inlined.
# For each statement, we know what we to substitute the call with: it's going to be the return value
# So then just write a transformer that navigates
# to the first challenger call and returns the expression that is an ASTNode of the return value of the oracle
# And then just recursively do that over and over again until you have a list of statements with no challenger calls


def inline_call(
    method_lookup: MethodLookup,
    block: frog_ast.Block,
) -> frog_ast.Block:
    # pylint: disable-next=global-statement
    global inline_counter
    inline_counter += 1
    new_statements: list[frog_ast.Statement] = []
    for index, statement in enumerate(block.statements):

        def is_inlinable_call(exp: frog_ast.ASTNode) -> bool:
            return (
                isinstance(exp, frog_ast.FuncCallExpression)
                and isinstance(exp.func, frog_ast.FieldAccess)
                and isinstance(exp.func.the_object, frog_ast.Variable)
                and (exp.func.the_object.name, exp.func.name) in method_lookup
            )

        func_call_exp = visitors.SearchVisitor[frog_ast.FuncCallExpression](
            is_inlinable_call
        ).visit(statement)

        if not func_call_exp:
            new_statements.append(copy.deepcopy(statement))
            continue

        assert isinstance(func_call_exp.func, frog_ast.FieldAccess)
        assert isinstance(func_call_exp.func.the_object, frog_ast.Variable)
        called_method = copy.deepcopy(
            method_lookup[(func_call_exp.func.the_object.name, func_call_exp.func.name)]
        )

        for var_statement in called_method.block.statements:
            if (
                isinstance(var_statement, (frog_ast.Assignment, frog_ast.Sample))
                and var_statement.the_type is not None
                and isinstance(var_statement.var, frog_ast.Variable)
            ):
                called_method = visitors.SubstitutionTransformer(
                    [
                        (
                            var_statement.var,
                            frog_ast.Variable(
                                str(inline_counter) + var_statement.var.name
                            ),
                        )
                    ]
                ).transform(called_method)

        transformed_method = visitors.SubstitutionTransformer(
            list(
                zip(
                    (
                        frog_ast.Variable(param.name)
                        for param in called_method.signature.parameters
                    ),
                    (arg for arg in func_call_exp.args),
                )
            )
        ).transform(called_method)
        final_statement = transformed_method.block.statements[-1]
        new_statements += transformed_method.block.statements[:-1]
        assert isinstance(final_statement, frog_ast.ReturnStatement)
        returned_exp = final_statement.expression

        changed_statement = visitors.ReplaceTransformer(
            func_call_exp, returned_exp
        ).transform(statement)
        new_statements.append(changed_statement)
        new_statements += block.statements[index + 1 :]
        break
    return frog_ast.Block(new_statements)


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

    def get_node(self, statement: frog_ast.Statement) -> Optional[Node]:
        for potential_node in self.nodes:
            if potential_node.statement == statement:
                return potential_node
        return None

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


def generate_dependency_graph(
    block: frog_ast.Block, proof_namespace: frog_ast.Namespace
) -> DependencyGraph:
    dependency_graph = DependencyGraph()
    for statement in block.statements:
        dependency_graph.add_node(Node(statement))

    def add_dependency(node_in_graph: Node, node: frog_ast.Statement) -> None:
        other_node = dependency_graph.get_node(node)
        assert other_node is not None
        node_in_graph.add_neighbour(other_node)

    for index, statement in enumerate(block.statements):
        node_in_graph = dependency_graph.get_node(statement)
        assert node_in_graph is not None
        earlier_statements = list(block.statements[:index])
        earlier_statements.reverse()

        if isinstance(statement, frog_ast.ReturnStatement):
            for depends_on in earlier_statements:

                def search_for_return(node: frog_ast.ASTNode) -> bool:
                    return isinstance(node, frog_ast.ReturnStatement)

                contains_return = visitors.SearchVisitor(search_for_return).visit(
                    depends_on
                )
                if contains_return is not None:
                    add_dependency(node_in_graph, depends_on)

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


def sort_game(
    game: frog_ast.Game, proof_namespace: frog_ast.Namespace
) -> frog_ast.Game:
    new_game = copy.deepcopy(game)
    for method in new_game.methods:
        method.block = sort_block(method.block, proof_namespace)
    return new_game


def sort_block(
    block: frog_ast.Block, proof_namespace: frog_ast.Namespace
) -> frog_ast.Block:
    new_statement_list: list[frog_ast.Statement] = []
    graph = generate_dependency_graph(block, proof_namespace)
    final_statement = block.statements[-1]
    final_node = graph.get_node(final_statement)
    assert final_node is not None
    queue: list[Node] = [final_node]
    visited: list[bool] = [False] * len(block.statements)
    visited[-1] = True
    while queue:
        node = queue.pop(0)
        new_statement_list.append(node.statement)
        for neighbour in node.in_neighbours:
            if not visited[block.statements.index(neighbour.statement)]:
                visited[block.statements.index(neighbour.statement)] = True
                queue.append(neighbour)
    new_statement_list.reverse()
    return frog_ast.Block(new_statement_list)


# I want to be able to instantiate primitives and schemes
# What does this entail? For primitives, all I have are fields and
# method signatures. So I'd like to:
# 1 - Set fields to values gotten from the proof namespace
# 2 - Change method signatures: either those that rely on external values,
#     or those that refer to the fields
# 3 - For schemes, might need to change things in the method bodies.


def instantiate_primitive(
    proof_namespace: frog_ast.Namespace,
    primitive: frog_ast.Primitive,
    args: list[frog_ast.Expression],
) -> frog_ast.Primitive:
    replace_map: list[Tuple[frog_ast.ASTNode, frog_ast.ASTNode]] = []
    for index, parameter in enumerate(primitive.parameters):
        replace_map.append(
            (frog_ast.Variable(parameter.name), copy.deepcopy(args[index]))
        )
    new_primitive = visitors.SubstitutionTransformer(replace_map).transform(primitive)
    new_primitive.parameters.clear()
    return visitors.InstantiationTransformer(proof_namespace).transform(new_primitive)


def instantiate_scheme(
    proof_namespace: frog_ast.Namespace,
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
    return visitors.InstantiationTransformer(proof_namespace).transform(new_scheme)
