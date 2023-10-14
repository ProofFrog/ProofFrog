import os
import sys
import copy
from typing import TypeAlias, Sequence, Tuple, Dict
from colorama import Fore
from . import frog_parser
from . import frog_ast

ProofNamespace: TypeAlias = dict[str, frog_ast.ASTNode]


def prove(proof_file_name: str) -> None:
    proof_file = frog_parser.parse_proof_file(proof_file_name)
    proof_namespace: ProofNamespace = {}

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
        proof_namespace[name] = root

    for game in proof_file.helpers:
        proof_namespace[game.name] = game

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

        current_game_ast = _get_game_ast(proof_namespace, current_step.challenger)
        if current_step.reduction:
            reduction = _get_game_ast(proof_namespace, current_step.reduction)
            assert isinstance(reduction, frog_ast.Reduction)
            current_game_ast = apply_reduction(
                current_game_ast, reduction, proof_namespace
            )

        next_game_ast = _get_game_ast(proof_namespace, next_step.challenger)
        if next_step.reduction:
            reduction = _get_game_ast(proof_namespace, next_step.reduction)
            assert isinstance(reduction, frog_ast.Reduction)
            next_game_ast = apply_reduction(next_game_ast, reduction, proof_namespace)

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


# pylint: disable-next=unused-argument


def apply_reduction(
    challenger: frog_ast.Game, reduction: frog_ast.Reduction, _namespace: ProofNamespace
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
    inlined_game = frog_ast.Game((name, parameters, fields, methods, phases))

    if challenger.has_method("Initialize") and not inlined_game.has_method(
        "Initialize"
    ):
        inlined_game.methods.insert(0, challenger.get_method("Initialize"))

    for method in inlined_game.methods:
        new_statements = inline_challenger_calls(challenger, method.statements)
        method.statements = new_statements

    print("After Inlining:")
    print(inlined_game)
    return inlined_game


def _get_game_ast(
    # Takes in a game from a proof step, and returns the AST associated with that game
    proof_namespace: ProofNamespace,
    challenger: frog_ast.ParameterizedGame | frog_ast.ConcreteGame,
) -> frog_ast.Game:
    if isinstance(challenger, frog_ast.ConcreteGame):
        game_file = proof_namespace[challenger.game.name]
        assert isinstance(game_file, frog_ast.GameFile)
        game = game_file.get_game(challenger.which)
        return instantiate_game(game, challenger.game.args)

    game_node = proof_namespace[challenger.name]
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

    return frog_ast.SubstitutionTransformer(replace_map).transform(game_copy)


def inline_challenger_calls(
    challenger: frog_ast.Game, statements: list[frog_ast.Statement]
) -> list[frog_ast.Statement]:
    # We have to go top to bottom, evaluate inner most first.
    # Start at first statement. Use a visitor to extract the innermost challenger call expression
    # Make it a variable and substitute. Then continue (have to reevaluate first statement again)

    method_look_up = dict(
        zip(
            (("challenger", method.signature.name) for method in challenger.methods),
            challenger.methods,
        )
    )
    new_statements = inline_call(method_look_up, statements)
    if new_statements != statements:
        return inline_call(method_look_up, new_statements)

    return new_statements


# Inline a single challenger call. Goes through statements and first challenger call (as well as innermost)
# will be inlined.


# For each statement, we know what we to substitute the call with: it's going to be the return value
# So then just write a transformer that navigates
# to the first challenger call and returns the expression that is an ASTNode of the return value of the oracle
# And then just recursively do that over and over again until you have a list of statements with no challenger calls


def inline_call(
    method_lookup: Dict[Tuple[str, str], frog_ast.Method],
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

        func_call_exp = frog_ast.SearchVisitor[frog_ast.FuncCallExpression](
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

        transformed_method = frog_ast.SubstitutionTransformer(
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

        changed_statement = frog_ast.ReplaceTransformer(
            func_call_exp, returned_exp
        ).transform(statement)
        new_statements.append(changed_statement)
        new_statements += statements[index + 1 :]
        break

    return new_statements
