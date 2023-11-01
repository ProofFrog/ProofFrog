import os
import sys
import copy
from typing import TypeAlias, Sequence, Tuple, Dict
from colorama import Fore
from . import frog_parser
from . import frog_ast
from . import visitors

Namespace: TypeAlias = dict[str, frog_ast.ASTNode]
MethodLookup: TypeAlias = Dict[Tuple[str, str], frog_ast.Method]


def prove(proof_file_name: str) -> None:
    proof_file = frog_parser.parse_proof_file(proof_file_name)
    definition_namespace: Namespace = {}
    proof_namespace: Namespace = {}

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

    # Hack for lets right now. Should substitute parameters, but I'm not. Do that later

    for let in proof_file.lets:
        if isinstance(let.value, frog_ast.FuncCallExpression) and isinstance(
            let.value.func, frog_ast.Variable
        ):
            proof_namespace[let.name] = definition_namespace[let.value.func.name]

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

        current_game_ast = _get_game_ast(definition_namespace, current_step.challenger)
        current_game_lookup = copy.deepcopy(method_lookup)
        if current_step.reduction:
            reduction = _get_game_ast(definition_namespace, current_step.reduction)
            assert isinstance(reduction, frog_ast.Reduction)
            current_game_lookup.update(get_challenger_method_lookup(current_game_ast))
            current_game_ast = apply_reduction(
                current_game_ast, reduction, definition_namespace
            )

        next_game_lookup = copy.deepcopy(method_lookup)
        next_game_ast = _get_game_ast(definition_namespace, next_step.challenger)
        if next_step.reduction:
            reduction = _get_game_ast(definition_namespace, next_step.reduction)
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


def get_method_lookup(definition_namespace: Namespace) -> MethodLookup:
    method_lookup: MethodLookup = {}

    for name, node in definition_namespace.items():
        if isinstance(node, frog_ast.Scheme):
            for method in node.methods:
                method_lookup[(name, method.signature.name)] = method

    return method_lookup


# pylint: disable-next=unused-argument


def apply_reduction(
    challenger: frog_ast.Game, reduction: frog_ast.Reduction, _namespace: Namespace
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
    definition_namespace: Namespace,
    challenger: frog_ast.ParameterizedGame | frog_ast.ConcreteGame,
) -> frog_ast.Game:
    if isinstance(challenger, frog_ast.ConcreteGame):
        game_file = definition_namespace[challenger.game.name]
        assert isinstance(game_file, frog_ast.GameFile)
        game = game_file.get_game(challenger.which)
        return instantiate_game(game, challenger.game.args)

    game_node = definition_namespace[challenger.name]
    assert isinstance(game_node, frog_ast.Game)
    return instantiate_game(game_node, challenger.args)


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
    game: frog_ast.Game, parameters: Sequence[frog_ast.ASTNode]
) -> frog_ast.Game:
    game_copy = copy.deepcopy(game)
    replace_map: dict[str, frog_ast.ASTNode] = {}
    for index, parameter in enumerate(game.parameters):
        replace_map[parameter.name] = parameters[index]

    game_copy.parameters = []

    return visitors.SubstitutionTransformer(replace_map).transform(game_copy)


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
        new_statements = inline_call(lookup, method.statements)
        if new_statements != method.statements:
            method.statements = new_statements
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
    statements: list[frog_ast.Statement],
) -> list[frog_ast.Statement]:
    new_statements: list[frog_ast.Statement] = []
    for index, statement in enumerate(statements):

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
        called_method = method_lookup[
            (func_call_exp.func.the_object.name, func_call_exp.func.name)
        ]

        transformed_method = visitors.SubstitutionTransformer(
            dict(
                zip(
                    (param.name for param in called_method.signature.parameters),
                    (arg for arg in func_call_exp.args),
                )
            )
        ).transform(called_method)
        final_statement = transformed_method.statements[-1]
        new_statements += transformed_method.statements[:-1]
        assert isinstance(final_statement, frog_ast.ReturnStatement)
        returned_exp = final_statement.expression

        changed_statement = visitors.ReplaceTransformer(
            func_call_exp, returned_exp
        ).transform(statement)
        new_statements.append(changed_statement)
        new_statements += statements[index + 1 :]
        break

    return new_statements
