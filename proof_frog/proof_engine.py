from __future__ import annotations
import os
import sys
import copy
import functools
from enum import Enum
from collections import namedtuple
from typing import TypeAlias, Sequence, Tuple, Dict, Optional
import z3
from colorama import Fore
from sympy import Symbol
from . import frog_parser
from . import frog_ast
from . import visitors
from . import dependencies

MethodLookup: TypeAlias = Dict[Tuple[str, str], frog_ast.Method]


class WhichGame(Enum):
    NEXT = "next"
    CURRENT = "current"


ProcessedAssumption = namedtuple("ProcessedAssumption", ["assumption", "which"])


class ProofEngine:
    def __init__(self, proof_file_name: str, verbose: bool) -> None:
        self.proof_file = frog_parser.parse_proof_file(proof_file_name)
        self.definition_namespace: frog_ast.Namespace = {}
        self.proof_namespace: frog_ast.Namespace = {}
        self.proof_let_types: visitors.NameTypeMap = visitors.NameTypeMap()

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
            self.proof_let_types.set(let.name, let.type)
            if isinstance(let.value, frog_ast.FuncCall) and isinstance(
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
        self.step_assumptions: list[ProcessedAssumption] = []

    def prove(self) -> None:
        first_step = self.proof_file.steps[0]
        final_step = self.proof_file.steps[-1]

        assert isinstance(first_step, frog_ast.Step)
        assert isinstance(final_step, frog_ast.Step)
        assert isinstance(first_step.challenger, frog_ast.ConcreteGame)
        assert isinstance(final_step.challenger, frog_ast.ConcreteGame)

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

    def prove_steps(self, steps: Sequence[frog_ast.ProofStep]) -> None:
        step_num = 0

        for i in range(0, len(steps) - 1):
            assumptions: list[frog_ast.StepAssumption] = []
            if isinstance(steps[i], frog_ast.StepAssumption):
                continue

            step_num += 1
            current_step = steps[i]
            i += 1
            assumption = steps[i]
            while isinstance(assumption, frog_ast.StepAssumption):
                assumptions.append(assumption)
                i += 1
                if i >= len(steps):
                    return
                assumption = steps[i]

            next_step = steps[i]

            print(f"===STEP {step_num}===")

            current_game_ast: frog_ast.Game
            next_game_ast: frog_ast.Game

            if isinstance(current_step, frog_ast.Step) and isinstance(
                next_step, frog_ast.Step
            ):
                if self._is_by_assumption(current_step, next_step):
                    print(f"Current: {current_step}")
                    print(f"Hop To: {next_step}\n")
                    print("Valid by assumption")
                    continue
                current_game_ast = self._get_game_ast(
                    current_step.challenger, current_step.reduction
                )
                next_game_ast = self._get_game_ast(
                    next_step.challenger, next_step.reduction
                )
            elif isinstance(current_step, frog_ast.Step) and isinstance(
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
                next_step = first_inductive_step
            elif isinstance(current_step, frog_ast.Induction) and isinstance(
                next_step, frog_ast.Step
            ):
                next_game_ast = self._get_game_ast(
                    next_step.challenger, next_step.reduction
                )
                last_inductive_step = next(
                    step
                    for step in current_step.steps[::-1]
                    if isinstance(step, frog_ast.Step)
                )
                assert isinstance(last_inductive_step, frog_ast.Step)
                last_inductive_step = visitors.SubstitutionTransformer(
                    [(frog_ast.Variable(current_step.name), current_step.end)]
                ).transform(last_inductive_step)
                current_game_ast = self._get_game_ast(
                    last_inductive_step.challenger, last_inductive_step.reduction
                )
                current_step = last_inductive_step

            print(f"Current: {current_step}")
            print(f"Hop To: {next_step}\n")

            assert isinstance(current_step, frog_ast.Step)
            assert isinstance(next_step, frog_ast.Step)

            self.set_up_assumptions(assumptions, current_step, next_step)

            self.check_equivalent(current_game_ast, next_game_ast)
            if isinstance(steps[i], frog_ast.Induction):
                the_induction = steps[i]
                assert isinstance(the_induction, frog_ast.Induction)
                self.proof_let_types.set(the_induction.name, frog_ast.IntType())
                self.prove_steps(the_induction.steps)
                # Check induction roll over
                first_step = the_induction.steps[0]
                assert isinstance(first_step, frog_ast.Step)
                assumptions = []
                last_step: frog_ast.Step
                for step in the_induction.steps[::-1]:
                    if isinstance(step, frog_ast.StepAssumption):
                        assumptions.append(step)
                    elif isinstance(step, frog_ast.Step):
                        last_step = step
                        break
                first_step = visitors.SubstitutionTransformer(
                    [
                        (
                            frog_ast.Variable(the_induction.name),
                            frog_ast.BinaryOperation(
                                frog_ast.BinaryOperators.ADD,
                                frog_ast.Variable(the_induction.name),
                                frog_ast.Integer(1),
                            ),
                        )
                    ]
                ).transform(first_step)
                first_step_ast = self._get_game_ast(
                    first_step.challenger, first_step.reduction
                )
                last_step_ast = self._get_game_ast(
                    last_step.challenger, last_step.reduction
                )
                print("CHECKING INDUCTION ROLLOVER")
                print(f"Current: {last_step}")
                print(f"Hop To: {first_step}\n")
                self.set_up_assumptions(assumptions, last_step, first_step)
                self.check_equivalent(last_step_ast, first_step_ast)
                self.proof_let_types.remove(the_induction.name)

    def set_up_assumptions(
        self,
        assumptions: list[frog_ast.StepAssumption],
        current_step: frog_ast.Step,
        next_step: frog_ast.Step,
    ) -> None:
        self.step_assumptions = []
        for assumption in assumptions:
            expression = assumption.expression

            def found_field_access(
                games: tuple[
                    frog_ast.ConcreteGame | frog_ast.ParameterizedGame,
                    frog_ast.ParameterizedGame | None,
                    frog_ast.ConcreteGame | frog_ast.ParameterizedGame,
                    frog_ast.ParameterizedGame | None,
                ],
                node: frog_ast.ASTNode,
            ) -> bool:
                return (
                    isinstance(node, frog_ast.FieldAccess) and node.the_object in games
                )

            found_field_access_partial = functools.partial(
                found_field_access,
                (
                    current_step.challenger,
                    current_step.reduction,
                    next_step.challenger,
                    next_step.reduction,
                ),
            )

            assumption_field = visitors.SearchVisitor[frog_ast.FieldAccess](
                found_field_access_partial
            ).visit(expression)
            applies_to = WhichGame.CURRENT
            while assumption_field is not None:
                new_var = frog_ast.Variable(
                    get_challenger_field_name(assumption_field.name)
                    if (
                        assumption_field.the_object == current_step.challenger
                        and current_step.reduction
                    )
                    or (
                        assumption_field.the_object == next_step.challenger
                        and next_step.reduction
                    )
                    else assumption_field.name
                )
                if assumption_field.the_object in (
                    next_step.challenger,
                    next_step.reduction,
                ):
                    applies_to = WhichGame.NEXT
                expression = visitors.ReplaceTransformer(
                    assumption_field, new_var
                ).transform(expression)
                assumption_field = visitors.SearchVisitor[frog_ast.FieldAccess](
                    found_field_access_partial
                ).visit(expression)
            self.step_assumptions.append(
                ProcessedAssumption(assumption=expression, which=applies_to)
            )

    def check_equivalent(
        self, current_game_ast: frog_ast.Game, next_game_ast: frog_ast.Game
    ) -> None:
        AstManipulator = namedtuple("AstManipulator", ["fn", "name"])
        ast_manipulators: list[AstManipulator] = [
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
            AstManipulator(fn=remove_duplicate_fields, name="Remove Duplicate Fields"),
            AstManipulator(
                fn=lambda ast: visitors.BranchEliminiationTransformer().transform(ast),
                name="Branch Elimination",
            ),
            AstManipulator(
                fn=lambda ast: visitors.RemoveFieldTransformer(
                    dependencies.UnnecessaryFieldVisitor(self.proof_namespace).visit(
                        ast
                    )
                ).transform(ast),
                name="Unnecessary Field Removal",
            ),
            AstManipulator(
                fn=lambda ast: visitors.CollapseAssignmentTransformer().transform(ast),
                name="Collapse Assignment",
            ),
            AstManipulator(
                fn=lambda ast: visitors.SimplifyReturnTransformer().transform(ast),
                name="Simplify Returns",
            ),
            AstManipulator(
                fn=lambda ast: visitors.SimplifyIfTransformer().transform(ast),
                name="Simplify Ifs",
            ),
            AstManipulator(
                fn=lambda ast: visitors.ExpandTupleTransformer().transform(ast),
                name="Expand Tuples",
            ),
            AstManipulator(
                fn=lambda ast: visitors.SimplifyNot().transform(ast),
                name="Simplify Nots",
            ),
            AstManipulator(
                fn=lambda ast: visitors.RedundantFieldCopyTransformer().transform(ast),
                name="Remove redundant variables for fields",
            ),
            AstManipulator(
                fn=lambda ast: visitors.SimplifyTupleTransformer(ast).transform(ast),
                name="Simplify tuples that are copies of their fields",
            ),
            AstManipulator(
                fn=lambda ast: visitors.RemoveUnreachableTransformer(ast).transform(
                    ast
                ),
                name="Remove unreachable blocks of code",
            ),
        ]

        for index, game in enumerate((current_game_ast, next_game_ast)):

            def apply_assumptions(
                which_game: WhichGame, ast: frog_ast.Game
            ) -> frog_ast.ASTNode:
                for assumption in self.step_assumptions:
                    if assumption.which != which_game:
                        continue
                    ast = visitors.SimplifyRangeTransformer(
                        self.proof_let_types, ast, assumption.assumption
                    ).transform(ast)
                return ast

            if index == 0:
                print("SIMPLIFYING CURRENT GAME")
                print(current_game_ast)
                ast_manipulators.append(
                    AstManipulator(
                        fn=functools.partial(apply_assumptions, WhichGame.CURRENT),
                        name="Apply Assumptions",
                    )
                )
            else:
                ast_manipulators.pop()
                print("SIMPLIFYING NEXT GAME")
                print(next_game_ast)
                ast_manipulators.append(
                    AstManipulator(
                        fn=functools.partial(apply_assumptions, WhichGame.NEXT),
                        name="Apply Assumptions",
                    )
                )

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
        current_game_ast = visitors.VariableStandardizingTransformer().transform(
            current_game_ast
        )
        next_game_ast = visitors.VariableStandardizingTransformer().transform(
            next_game_ast
        )
        current_game_ast = standardize_field_names(current_game_ast)
        next_game_ast = standardize_field_names(next_game_ast)
        current_game_ast = dependencies.BubbleSortFieldAssignment().transform(
            current_game_ast
        )
        next_game_ast = dependencies.BubbleSortFieldAssignment().transform(
            next_game_ast
        )

        print("CURRENT")
        print(current_game_ast)
        print("NEXT")
        print(next_game_ast)

        if current_game_ast == next_game_ast:
            print("Inline Success!")
            return

        class AllTrueTransformer(visitors.Transformer):
            def transform_if_statement(
                self, stmt: frog_ast.IfStatement
            ) -> frog_ast.IfStatement:
                return frog_ast.IfStatement(
                    [frog_ast.Boolean(True)] * len(stmt.conditions), stmt.blocks
                )

        def quit_proof() -> None:
            print("Step failed!")
            print(Fore.RED + "Proof Failed!")
            sys.exit(1)

        all_true_current = AllTrueTransformer().transform(current_game_ast)
        all_true_next = AllTrueTransformer().transform(next_game_ast)
        if all_true_current != all_true_next:
            quit_proof()

        found_ifs: list[frog_ast.IfStatement] = []

        def search_for_if(
            found_ifs: list[frog_ast.IfStatement], node: frog_ast.ASTNode
        ) -> bool:
            return isinstance(node, frog_ast.IfStatement) and node not in found_ifs

        while True:
            partial = functools.partial(search_for_if, found_ifs)
            if_current = visitors.SearchVisitor[frog_ast.IfStatement](partial).visit(
                current_game_ast
            )
            if_next = visitors.SearchVisitor[frog_ast.IfStatement](partial).visit(
                next_game_ast
            )
            if if_current is None or if_next is None:
                break
            found_ifs.append(if_current)
            found_ifs.append(if_next)
            for i, condition in enumerate(if_current.conditions):
                if condition == if_next.conditions[i]:
                    continue

                first_if_formula = visitors.Z3FormulaVisitor(
                    visitors.GetTypeMapVisitor(condition).visit(current_game_ast)
                    + self.proof_let_types
                ).visit(condition)
                next_if_formula = visitors.Z3FormulaVisitor(
                    visitors.GetTypeMapVisitor(if_next.conditions[i]).visit(
                        next_game_ast
                    )
                    + self.proof_let_types
                ).visit(if_next.conditions[i])
                if first_if_formula is None or first_if_formula is None:
                    quit_proof()
                solver = z3.Solver()
                solver.add(z3.Not(first_if_formula == next_if_formula))
                if solver.check() != z3.unsat:
                    quit_proof()
        print("Inline Success!")

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
            frog_ast.Field(
                field.type, get_challenger_field_name(field.name), field.value
            )
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
        elif challenger.has_method("Initialize"):
            # Must combine two methods together
            # Do so by inserting an arg = challenger.Initialize() at the beginning
            # and then using the inline transformer
            challenger_initialize = challenger.get_method("Initialize")
            reduction_initialize = reduced_game.get_method("Initialize")
            call_initialize = frog_ast.FuncCall(
                frog_ast.FieldAccess(frog_ast.Variable("challenger"), "Initialize"),
                [],
            )
            if isinstance(challenger_initialize.signature.return_type, frog_ast.Void):
                reduction_initialize.block = (
                    frog_ast.Block([call_initialize]) + reduction_initialize.block
                )

            else:
                param = reduction_initialize.signature.parameters[0]
                reduction_initialize.block = (
                    frog_ast.Block(
                        [
                            frog_ast.Assignment(
                                param.type,
                                frog_ast.Variable(param.name),
                                call_initialize,
                            )
                        ]
                    )
                    + reduction_initialize.block
                )
            reduction_initialize.signature.parameters = []
            reduction_initialize.signature.return_type = (
                challenger_initialize.signature.return_type
            )
            reduction_initialize = visitors.InlineTransformer(
                {("challenger", "Initialize"): challenger_initialize}
            ).transform(reduction_initialize)
            reduced_game.methods[0] = reduction_initialize

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
                            frog_ast.Variable(get_challenger_field_name(field.name)),
                        )
                        for field in game.fields
                    ]
                ).transform(method)
            lookup.update(get_challenger_method_lookup(game))
            game = self.apply_reduction(game, reduction_ast)

        while True:
            new_game = visitors.InlineTransformer(lookup).transform(copy.deepcopy(game))
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
        graph = dependencies.generate_dependency_graph(
            block, game.fields, self.proof_namespace
        )

        def is_return(node: frog_ast.ASTNode) -> bool:
            return node in block.statements and isinstance(
                node, frog_ast.ReturnStatement
            )

        dfs_stack: list[dependencies.Node] = []
        dfs_stack_visited = [False] * len(block.statements)
        dfs_sorted_statements: list[frog_ast.Statement] = []

        def do_dfs() -> None:
            while dfs_stack:
                node = dfs_stack.pop()
                if not dfs_stack_visited[block.statements.index(node.statement)]:
                    dfs_sorted_statements.append(node.statement)
                    dfs_stack_visited[block.statements.index(node.statement)] = True
                    for neighbour in node.in_neighbours:
                        dfs_stack.append(neighbour)

        return_node = graph.find_node(is_return)
        if return_node is not None:
            dfs_stack.append(return_node)
            do_dfs()

        dfs_sorted_statements.reverse()

        for statement in block.statements:

            def uses_field(node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.Variable) and node.name in [
                    field.name for field in game.fields
                ]

            found = visitors.SearchVisitor(uses_field).visit(statement)
            if statement not in dfs_sorted_statements and found is not None:
                dfs_stack.append(graph.get_node(statement))
                do_dfs()

        sorted_statements: list[frog_ast.Statement] = []
        stack: list[dependencies.Node] = []

        for statement in dfs_sorted_statements:
            if not graph.get_node(statement).in_neighbours:
                stack.insert(0, graph.get_node(statement))

        while stack:
            node = stack.pop()
            sorted_statements.append(node.statement)
            for other_node in graph.nodes:
                if node in other_node.in_neighbours:
                    other_node.in_neighbours.remove(node)
                    if not other_node.in_neighbours:
                        stack.insert(0, other_node)

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


def remove_duplicate_fields(game: frog_ast.Game) -> frog_ast.Game:
    for field in game.fields:
        for other_field in game.fields:
            if field.type == other_field.type and field.name < other_field.name:
                duplicated_statements = visitors.SameFieldVisitor(
                    (field.name, other_field.name)
                ).visit(game)
                if duplicated_statements is not None:
                    new_game = copy.deepcopy(game)
                    new_game.fields = [
                        the_field
                        for the_field in game.fields
                        if the_field.name != other_field.name
                    ]
                    return visitors.SubstitutionTransformer(
                        [
                            (
                                frog_ast.Variable(other_field.name),
                                frog_ast.Variable(field.name),
                            )
                        ]
                    ).transform(
                        visitors.RemoveStatementTransformer(
                            duplicated_statements
                        ).transform(new_game)
                    )
    return game


def get_challenger_field_name(name: str) -> str:
    return f"challenger@{name}"


def standardize_field_names(game: frog_ast.Game) -> frog_ast.Game:
    field_rename_map = visitors.FieldOrderingVisitor().visit(game)
    new_game = visitors.SubstitutionTransformer(
        [
            (frog_ast.Variable(field_name), frog_ast.Variable(normalized_name))
            for field_name, normalized_name in field_rename_map.items()
        ]
    ).transform(game)
    for field in new_game.fields:
        field.name = field_rename_map[field.name]
    new_game.fields.sort(key=lambda element: element.name)
    return new_game
