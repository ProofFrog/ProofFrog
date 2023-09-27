import os
import sys
import copy
from typing import TypeAlias
from colorama import Fore
import frog_parser
import frog_ast

ProofNamespace: TypeAlias = dict[str, frog_ast.ASTNode]


def prove(proof_file_name: str) -> None:
    proof_file = frog_parser.parse_proof(proof_file_name)
    proof_namespace: ProofNamespace = {}

    for imp in proof_file.imports:
        file_type = _get_file_type(imp.filename)
        root: frog_ast.Root
        match file_type:
            case frog_ast.FileType.PRIMITIVE:
                root = frog_parser.parse_primitive(imp.filename)
            case frog_ast.FileType.SCHEME:
                root = frog_parser.parse_scheme(imp.filename)
            case frog_ast.FileType.GAME:
                root = frog_parser.parse_game(imp.filename)
            case frog_ast.FileType.PROOF:
                raise TypeError("Cannot import proofs")

        name = imp.rename if imp.rename else root.get_export_name()
        proof_namespace[name] = root

    for game in proof_file.helpers:
        proof_namespace[game.name] = game

    current_step: frog_ast.ProofStep
    next_step: frog_ast.ProofStep

    for i in range(0, len(proof_file.steps)-1):
        current_step = proof_file.steps[i]
        next_step = proof_file.steps[i+1]
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
            current_game_ast = inline(current_game_ast, reduction)

        next_game_ast = _get_game_ast(proof_namespace, next_step.challenger)
        if next_step.reduction:
            reduction = _get_game_ast(proof_namespace, next_step.reduction)
            assert isinstance(reduction, frog_ast.Reduction)
            next_game_ast = inline(next_game_ast, reduction)

        print("Current Game:")
        print(current_game_ast)
        print("Next Game:")
        print(next_game_ast)
        if current_game_ast == next_game_ast:
            print("Inline Success!")
            continue

        print("Step failed!")
        print(Fore.RED + 'Proof Failed!')
        sys.exit(1)

    print(Fore.GREEN + "Proof Suceeded!")


def inline(challenger: frog_ast.Game, reduction: frog_ast.Reduction) -> frog_ast.Game:
    print("Reduction to apply:")
    print(reduction)
    print("Challenger:")
    print(challenger)
    name = 'Inlined'
    parameters = challenger.parameters
    fields = challenger.fields
    phases = challenger.phases
    methods = copy.deepcopy(reduction.methods)
    inlined_game = frog_ast.Game((name, parameters, fields, methods, phases))
    apply_reduction(challenger, inlined_game)
    print("After Inlining:")
    print(inlined_game)
    return inlined_game


def apply_reduction(challenger: frog_ast.Game, reduced_game: frog_ast.Game) -> None:
    for method in reduced_game.methods:
        return_stmt = method.statements[-1]
        if isinstance(return_stmt, frog_ast.ReturnStatement) and _is_challenger_call(return_stmt.expression):
            assert isinstance(return_stmt.expression, frog_ast.FuncCallExpression)
            assert isinstance(return_stmt.expression.func, frog_ast.FieldAccess)
            assert isinstance(return_stmt.expression.args[0], frog_ast.Variable)

            called_method = copy.deepcopy(challenger.get_method(return_stmt.expression.func.name))
            v = frog_ast.VariableSubstitution(
                called_method.signature.parameters[0].name, return_stmt.expression.args[0].name)
            called_method.accept(v)
            method.statements.pop()
            method.statements = method.statements + called_method.statements


def _get_game_ast(
    # Takes in a game from a proof step, and returns the AST associated with that game
    proof_namespace: ProofNamespace,
    challenger: frog_ast.ParameterizedGame | frog_ast.ConcreteGame
) -> frog_ast.Game:
    if isinstance(challenger, frog_ast.ConcreteGame):
        game = proof_namespace[challenger.game.name]
        assert isinstance(game, frog_ast.GameFile)
        return game.get_game(challenger.which)
    game = proof_namespace[challenger.name]
    assert isinstance(game, frog_ast.Game)
    return game


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip('.')
    return frog_ast.FileType(extension)


def _is_by_assumption(
        proof_file: frog_ast.ProofFile, current_step: frog_ast.Step, next_step: frog_ast.Step) -> bool:
    if not isinstance(
            current_step.challenger, frog_ast.ConcreteGame) or not isinstance(
            next_step.challenger, frog_ast.ConcreteGame):
        return False
    return bool(
        current_step.challenger.game == next_step.challenger.game and current_step.reduction and current_step.reduction
        == next_step.reduction and current_step.adversary == next_step.
        adversary and current_step.challenger.game in proof_file.assumptions)


def _is_challenger_call(exp: frog_ast.Expression) -> bool:
    return isinstance(
        exp, frog_ast.FuncCallExpression) and isinstance(
        exp.func, frog_ast.FieldAccess) and isinstance(
        exp.func.the_object, frog_ast.Variable) and exp.func.the_object.name == 'challenger'
