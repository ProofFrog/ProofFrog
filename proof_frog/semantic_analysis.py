import sys
import copy
from typing import Optional, TypeVar, Union, TypeAlias
from sympy import Symbol
from . import frog_ast
from . import frog_parser
from . import proof_engine
from . import visitors


class FailedTypeCheck(Exception):
    pass


def check_well_formed(root: frog_ast.Root, file_name: str) -> None:
    name_resolution(root, file_name)

    import_namespace: dict[str, frog_ast.Root | frog_ast.Game] = {}
    file_name_mapping: dict[str, str] = {}
    if isinstance(root, frog_ast.ProofFile):
        for imp in root.imports:
            parsed_file = frog_parser.parse_file(imp.filename)
            name = imp.rename if imp.rename else parsed_file.get_export_name()
            import_namespace[name] = parsed_file
            file_name_mapping[name] = imp.filename
        check_proof_well_formed(root, file_name, import_namespace, file_name_mapping)
    else:
        print(
            "WARNING: Type checking only ensures names are well-defined for non-proofs"
        )


def name_resolution(initial_root: frog_ast.Root, initial_file_name: str) -> None:
    all_imports: dict[str, frog_ast.Root] = {}

    def do_name_resolution(root: frog_ast.Root, file_name: str) -> None:
        import_namespace: dict[str, frog_ast.Game | frog_ast.Root] = {}
        if isinstance(root, (frog_ast.GameFile, frog_ast.Scheme, frog_ast.ProofFile)):
            for imp in root.imports:
                if imp.filename in all_imports:
                    definition = all_imports[imp.filename]
                    import_namespace[
                        imp.rename if imp.rename else definition.get_export_name()
                    ] = definition
                    continue

                parsed_file = frog_parser.parse_file(imp.filename)
                do_name_resolution(parsed_file, imp.filename)
                name = imp.rename if imp.rename else parsed_file.get_export_name()
                import_namespace[name] = parsed_file
                all_imports[imp.filename] = parsed_file
        NameResolutionVisitor(import_namespace, file_name).visit(root)

    do_name_resolution(initial_root, initial_file_name)


T = TypeVar("T", bound=Union[frog_ast.Primitive, frog_ast.Scheme, frog_ast.Game])
PossibleType: TypeAlias = (
    None
    | frog_ast.Type
    | visitors.InstantiableType
    | list[visitors.InstantiableType]
    | list[frog_ast.Type]
)

VariableTypeMapStackType: TypeAlias = Optional[
    list[
        dict[
            str,
            PossibleType,
        ]
    ]
]


class VariableTypeVisitor(visitors.Visitor[None]):
    def __init__(
        self,
        import_namespace: dict[str, frog_ast.Root | frog_ast.Game],
        variable_type_map_stack: VariableTypeMapStackType = None,
        instantiation_namespace: Optional[frog_ast.Namespace] = None,
    ) -> None:
        self.import_namespace = import_namespace
        self.variable_type_map_stack = (
            variable_type_map_stack if variable_type_map_stack is not None else [{}]
        )
        self.instantiation_namespace: frog_ast.Namespace = (
            instantiation_namespace if instantiation_namespace is not None else {}
        )

    def instantiate_and_get_type(
        self,
        root: T,
        args: list[frog_ast.Expression],
        name: str,
        just_methods: bool = False,
    ) -> visitors.InstantiableType:
        return get_type_from_instantiable(
            name,
            proof_engine.instantiate(root, args, self.instantiation_namespace),
            just_methods,
        )

    def visit_game(self, game: frog_ast.Game) -> None:
        game_type = get_type_from_instantiable(game.name, game)
        self.variable_type_map_stack[-1][game.name] = game_type
        self.variable_type_map_stack.append({})

    def leave_game(self, _: frog_ast.Game) -> None:
        self.variable_type_map_stack.pop()

    def visit_parameter(self, param: frog_ast.Parameter) -> None:
        self.variable_type_map_stack[-1][param.name] = (
            param.type
            if not isinstance(param.type, frog_ast.Variable)
            else self.get_type(param.type.name)
        )

    def leave_field(self, field: frog_ast.Field) -> None:
        was_scheme = False
        if isinstance(field.type, frog_ast.SetType) and not field.type.parameterization:
            the_type = (
                field.value
                if isinstance(field.value, frog_ast.Variable)
                else frog_ast.Variable(field.name)
            )
            self.variable_type_map_stack[-1][field.name] = the_type
        else:
            if isinstance(field.type, frog_ast.Variable):
                if (
                    isinstance(field.value, frog_ast.FuncCall)
                    and isinstance(field.value.func, frog_ast.Variable)
                    and field.value.func.name in self.import_namespace
                ):
                    root = self.import_namespace[field.value.func.name]
                    if not isinstance(
                        root, (frog_ast.Primitive, frog_ast.Scheme, frog_ast.Game)
                    ):
                        print_error(
                            field,
                            f"{field} should be a primitive, scheme, or game to be instantiated",
                        )
                        return
                    instantiated_scheme = proof_engine.instantiate(
                        root,
                        field.value.args,
                        self.instantiation_namespace,
                    )
                    instantiated_type = get_type_from_instantiable(
                        field.value.func.name, instantiated_scheme
                    )
                    self.variable_type_map_stack[-1][field.name] = instantiated_type
                    self.instantiation_namespace[field.name] = instantiated_scheme
                    was_scheme = True
                else:
                    self.variable_type_map_stack[-1][field.name] = self.get_type(
                        field.type.name
                    )
            else:
                self.variable_type_map_stack[-1][field.name] = field.type
        if not was_scheme:
            self.instantiation_namespace[field.name] = field.value

    def visit_reduction(self, reduction: frog_ast.Reduction) -> None:
        reduction_type = get_type_from_instantiable(reduction.name, reduction)
        self.variable_type_map_stack[-1][reduction.name] = reduction_type
        self.variable_type_map_stack.append({})

        if reduction.to_use.name not in self.import_namespace:
            print_error(reduction, f"{reduction.to_use.name} not found in imports")
        if reduction.play_against.name not in self.import_namespace:
            print_error(
                reduction, f"{reduction.play_against.name} not found in imports"
            )
        challenger_definition = self.import_namespace[reduction.to_use.name]
        if not isinstance(challenger_definition, frog_ast.GameFile):
            print_error(reduction, "Challenger should be a game file")
            return

        if len(challenger_definition.games[0].parameters) != len(reduction.to_use.args):
            print_error(
                reduction, "Challenger is being supplied incorrect number of arguments"
            )

        # We've checked earlier that the two games must have the same method signatures,
        # so we can choose an arbitrary one
        self.variable_type_map_stack[-1]["challenger"] = self.instantiate_and_get_type(
            challenger_definition.games[0],
            reduction.to_use.args,
            reduction.to_use.name,
            True,
        )

    def leave_reduction(self, _: frog_ast.Reduction) -> None:
        self.variable_type_map_stack.pop()

    def visit_method(self, method: frog_ast.Method) -> None:
        self.variable_type_map_stack.append(
            dict(
                zip(
                    (param.name for param in method.signature.parameters),
                    (param.type for param in method.signature.parameters),
                )
            )
        )

    def leave_method(self, _: frog_ast.Method) -> None:
        self.variable_type_map_stack.pop()

    def leave_assignment(self, assignment: frog_ast.Assignment) -> None:
        if assignment.the_type is not None:
            assert isinstance(assignment.var, frog_ast.Variable)
            self.variable_type_map_stack[-1][assignment.var.name] = assignment.the_type

    def leave_sample(self, sample: frog_ast.Sample) -> None:
        if sample.the_type is not None:
            assert isinstance(sample.var, frog_ast.Variable)
            self.variable_type_map_stack[-1][sample.var.name] = sample.the_type

    def visit_variable_declaration(
        self, declaration: frog_ast.VariableDeclaration
    ) -> None:
        self.variable_type_map_stack[-1][declaration.name] = declaration.type

    def visit_block(self, _: frog_ast.Block) -> None:
        self.variable_type_map_stack.append({})

    def leave_block(self, _: frog_ast.Block) -> None:
        self.variable_type_map_stack.pop()

    def visit_numeric_for(self, numeric_for: frog_ast.NumericFor) -> None:
        self.variable_type_map_stack.append({numeric_for.name: frog_ast.IntType()})

    def leave_numeric_for(self, _: frog_ast.NumericFor) -> None:
        self.variable_type_map_stack.pop()

    def visit_generic_for(self, generic_for: frog_ast.GenericFor) -> None:
        self.variable_type_map_stack.append(
            {generic_for.var_name: generic_for.var_type}
        )

    def leave_generic_for(self, _: frog_ast.GenericFor) -> None:
        self.variable_type_map_stack.pop()

    def get_type(self, name: str) -> PossibleType:
        for the_map in reversed(self.variable_type_map_stack):
            if name in the_map:
                return the_map[name]
        if name in self.import_namespace:
            instantiable = self.import_namespace[name]
            if isinstance(instantiable, frog_ast.GameFile):
                game_array = [
                    get_type_from_instantiable(game.name, game)
                    for game in instantiable.games
                ]
                return game_array
            if not isinstance(
                instantiable, (frog_ast.Primitive, frog_ast.Scheme, frog_ast.Game)
            ):
                return None
            return get_type_from_instantiable(name, instantiable)

        return None

    def visit_induction(self, induction: frog_ast.Induction) -> None:
        self.variable_type_map_stack.append({})
        self.variable_type_map_stack[-1][induction.name] = frog_ast.IntType()

    def result(self) -> None:
        return None


class NameResolutionVisitor(VariableTypeVisitor):
    def __init__(
        self, import_namespace: dict[str, frog_ast.Root | frog_ast.Game], file_name: str
    ) -> None:
        super().__init__(import_namespace)
        self.file_name = file_name
        self.in_field_access = False
        self.defining_variable: Optional[frog_ast.Expression] = None

    def visit_game_file(self, game_file: frog_ast.GameFile) -> None:
        for index, game in enumerate(game_file.games):
            other_game = game_file.games[1 - index]
            for method_signature in [method.signature for method in game.methods]:
                if not [
                    other
                    for other in other_game.methods
                    if other.signature == method_signature
                ]:
                    print_error(
                        method_signature,
                        f"{method_signature} does not exist in paired game",
                        self.file_name,
                    )
            if len(game.parameters) != len(other_game.parameters):
                print_error(game, "Games must have matching parameters", self.file_name)
            for param_index, param in enumerate(game.parameters):
                if param.type != other_game.parameters[param_index].type:
                    print_error(
                        game, "Games must have matching parameters", self.file_name
                    )

        if game_file.games[0].name == game_file.games[1].name:
            print_error(
                game_file, "Cannot have two games with the same name", self.file_name
            )

    def visit_scheme(self, scheme: frog_ast.Scheme) -> None:
        if scheme.primitive_name not in self.import_namespace:
            print_error(
                scheme,
                f"Primitive {scheme.primitive_name} is not defined",
                self.file_name,
            )
        corresponding_primitive = self.import_namespace[scheme.primitive_name]
        if not isinstance(corresponding_primitive, frog_ast.Primitive):
            print_error(
                scheme, f"{scheme.primitive_name} is not a primitive", self.file_name
            )
            return
        primitive_definition = get_type_from_instantiable(
            scheme.primitive_name, corresponding_primitive, True
        )
        if not has_matching_methods(
            primitive_definition, get_type_from_instantiable(scheme.name, scheme, True)
        ):
            print_error(
                scheme,
                f"Scheme does not correctly implement primitive {scheme.primitive_name}",
            )

    def visit_assignment(self, assignment: frog_ast.Assignment) -> None:
        if assignment.the_type is not None:
            self.defining_variable = assignment.var

    def leave_assignment(self, assignment: frog_ast.Assignment) -> None:
        super().leave_assignment(assignment)
        self.defining_variable = None

    def visit_sample(self, sample: frog_ast.Sample) -> None:
        if sample.the_type is not None:
            self.defining_variable = sample.var

    def leave_sample(self, sample: frog_ast.Sample) -> None:
        super().leave_sample(sample)
        self.defining_variable = None

    def visit_variable(self, var: frog_ast.Variable) -> None:
        if self.in_field_access or self.defining_variable is var:
            return
        # Check for valid!
        the_type = self.get_type(var.name)
        if the_type is None:
            print_error(var, f"Variable {var.name} not defined", self.file_name)

    def visit_parameterized_game(
        self, parameterized_game: frog_ast.ParameterizedGame
    ) -> None:
        the_type = self.get_type(parameterized_game.name)
        if the_type is None:
            print_error(
                parameterized_game,
                f"Game {parameterized_game.name} is not defined",
                self.file_name,
            )

    def leave_concrete_game(self, concrete_game: frog_ast.ConcreteGame) -> None:
        if concrete_game.game.name not in self.import_namespace:
            print_error(
                concrete_game,
                f"Game {concrete_game.game.name} not found",
                self.file_name,
            )
        game_file = self.get_type(concrete_game.game.name)
        if not isinstance(game_file, list):
            print_error(
                concrete_game, f"{concrete_game} does not correspond to a game file"
            )
            return

        if not [
            game
            for game in game_file
            if isinstance(game, visitors.InstantiableType)
            and game.name == concrete_game.which
        ]:
            print_error(
                concrete_game,
                f"Game {concrete_game.which} is not found in {concrete_game.game.name}",
                self.file_name,
            )

    def visit_field_access(self, _: frog_ast.FieldAccess) -> None:
        self.in_field_access = True

    def leave_field_access(self, field_access: frog_ast.FieldAccess) -> None:
        self.in_field_access = False
        name: str
        if not isinstance(
            field_access.the_object,
            (frog_ast.Variable, frog_ast.ParameterizedGame, frog_ast.ConcreteGame),
        ):
            print_error(
                field_access,
                f"Field access {field_access} not understood",
                self.file_name,
            )
            return
        if isinstance(field_access.the_object, frog_ast.ConcreteGame):
            name = field_access.the_object.game.name
        else:
            name = field_access.the_object.name

        the_type = self.get_type(name)

        if isinstance(the_type, list):
            assert isinstance(field_access.the_object, frog_ast.ConcreteGame)
            assert isinstance(the_type[0], visitors.InstantiableType)
            the_type = (
                the_type[0]
                if field_access.the_object.which == the_type[0].name
                else the_type[1]
            )

        if not isinstance(the_type, visitors.InstantiableType):
            print_error(
                field_access,
                f"{field_access.the_object} is not a primitive, scheme, or Game",
                self.file_name,
            )
            return

        if field_access.name not in the_type.members.keys():
            print_error(
                field_access,
                f"{field_access.name} is not a property of {field_access.the_object}",
                self.file_name,
            )


def check_proof_well_formed(
    proof: frog_ast.ProofFile,
    file_name: str,
    import_namespace: dict[str, frog_ast.Root | frog_ast.Game],
    file_name_mapping: dict[str, str],
) -> None:
    type_check_visitor = CheckTypeVisitor(
        import_namespace, file_name, file_name_mapping
    )
    for let in proof.lets:
        type_check_visitor.visit(let)
    for assumption in proof.assumptions:
        type_check_visitor.visit(assumption)

    type_check_visitor.visit(proof.theorem)

    for helper in proof.helpers:
        import_namespace[helper.name] = helper
    for step in proof.steps:
        type_check_visitor.visit(step)


def print_error(
    location: frog_ast.ASTNode, message: str, file_name: str = "Unknown"
) -> None:
    print(f"File: {file_name}")
    print(f"Line {location.line_num}, column: {location.column_num}", file=sys.stderr)
    print(location)
    print(message, file=sys.stderr)
    raise FailedTypeCheck()


class CheckTypeVisitor(VariableTypeVisitor):
    # pylint: disable=too-many-positional-arguments,too-many-arguments
    def __init__(
        self,
        import_namespace: dict[str, frog_ast.Root | frog_ast.Game],
        file_name: str,
        file_name_mapping: dict[str, str],
        variable_type_map_stack: VariableTypeMapStackType = None,
        field_value_map: Optional[frog_ast.Namespace] = None,
    ) -> None:
        super().__init__(import_namespace, variable_type_map_stack, field_value_map)
        self.import_namespace = import_namespace
        self.ast_type_map = frog_ast.ASTMap[PossibleType]()
        self.file_name = file_name
        self.file_name_mapping = file_name_mapping

    def result(self) -> None:
        return None

    def print_error(self, location: frog_ast.ASTNode, message: str) -> None:
        print_error(location, message, self.file_name)

    def get_type_from_ast(self, node: frog_ast.ASTNode) -> PossibleType:
        try:
            return self.ast_type_map.get(node)
        except KeyError:
            self.print_error(node, f"Could not determine type of {node}")
            sys.exit(1)

    def _shared_primitive_scheme_checks(
        self, primitive: frog_ast.Primitive | frog_ast.Scheme
    ) -> None:
        method_signatures = (
            primitive.methods
            if isinstance(primitive, frog_ast.Primitive)
            else [method.signature for method in primitive.methods]
        )

        field_names = [field.name for field in primitive.fields]
        if len(field_names) != len(set(field_names)):
            self.print_error(primitive.fields[0], "Duplicated field name")

        method_names = [method.name for method in method_signatures]
        if len(method_names) != len(set(method_names)):
            self.print_error(primitive.methods[0], "Duplicated method name")

    def visit_primitive(self, primitive: frog_ast.Primitive) -> None:
        self._shared_primitive_scheme_checks(primitive)

    def leave_scheme(self, scheme: frog_ast.Scheme) -> None:
        self._shared_primitive_scheme_checks(scheme)
        for requirement in scheme.requirements:
            requirement_type = self.get_type_from_ast(requirement)
            if not compare_types(frog_ast.BoolType(), requirement_type):
                self.print_error(
                    requirement,
                    f"Requirements should evaluate to a boolean type, received {requirement_type}",
                )
        # Check that it implements the expected methods

    def leave_if_statement(self, if_statement: frog_ast.IfStatement) -> None:
        for condition in if_statement.conditions:
            condition_type = self.get_type_from_ast(condition)
            if not compare_types(frog_ast.BoolType(), condition_type):
                self.print_error(
                    condition, f"Condition has type {condition_type}, expected bool"
                )

    def leave_numeric_for(self, numeric_for: frog_ast.NumericFor) -> None:
        super().leave_numeric_for(numeric_for)
        start_type = self.get_type_from_ast(numeric_for.start)
        end_type = self.get_type_from_ast(numeric_for.end)
        if not compare_types(frog_ast.IntType(), start_type):
            self.print_error(
                numeric_for, f"Start expression has type {start_type}, expected Int"
            )
        if not compare_types(frog_ast.IntType(), end_type):
            self.print_error(
                numeric_for, f"End expression has type {end_type}, expected Int"
            )

    def leave_generic_for(self, generic_for: frog_ast.GenericFor) -> None:
        super().leave_generic_for(generic_for)
        over_set = self.get_type_from_ast(generic_for.over)
        if not isinstance(over_set, frog_ast.SetType):
            self.print_error(
                generic_for, f"Must iterator over finite set, got type {over_set}"
            )

    def visit_reduction(self, reduction: frog_ast.Reduction) -> None:
        super().visit_reduction(reduction)

        adversary_definition = self.import_namespace[reduction.play_against.name]
        if not isinstance(adversary_definition, frog_ast.GameFile):
            self.print_error(reduction, "Adversary must be a game file")
            return

        adversary_type = self.instantiate_and_get_type(
            adversary_definition.games[0],
            reduction.play_against.args,
            reduction.play_against.name,
            True,
        )
        reduction_type = get_type_from_instantiable(reduction.name, reduction, True)
        non_matching_method = has_matching_methods(adversary_type, reduction_type)
        if non_matching_method is not True:
            self.print_error(
                reduction,
                f"{non_matching_method} does not exist in reduction {reduction.name}",
            )

    def visit_none_expression(self, none_expression: frog_ast.NoneExpression) -> None:
        self.ast_type_map.set(none_expression, frog_ast.NoneExpression())

    def visit_method_signature(
        self, method_signature: frog_ast.MethodSignature
    ) -> None:
        parameter_names = [param.name for param in method_signature.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            self.print_error(method_signature, "Duplicated parameter name")

    def visit_step(self, step: frog_ast.Step) -> None:
        if step.adversary.name not in self.import_namespace:
            self.print_error(step, f"{step.adversary.name} not found in imports")
        adversary_definition = self.import_namespace[step.adversary.name]
        if not isinstance(adversary_definition, frog_ast.GameFile):
            self.print_error(
                step, f"{step.adversary.name} must be imported as a game pair"
            )
            return
        adversary_methods = self.instantiate_and_get_type(
            adversary_definition.games[0],
            step.adversary.args,
            step.adversary.name,
            True,
        )
        challenger = step.challenger if step.reduction is None else step.reduction
        if isinstance(challenger, frog_ast.ConcreteGame):
            challenger = challenger.game
        if challenger.name not in self.import_namespace:
            self.print_error(step, f"{challenger.name} not found in imports")
        challenger_definition = self.import_namespace[challenger.name]
        if not isinstance(challenger_definition, (frog_ast.Game, frog_ast.GameFile)):
            self.print_error(step, f"{challenger.name} must be a game")
            return
        instantiated_challenger = proof_engine.instantiate(
            (
                challenger_definition
                if not isinstance(challenger_definition, frog_ast.GameFile)
                else challenger_definition.games[0]
            ),
            challenger.args,
            self.instantiation_namespace,
        )
        instantiated_methods = get_type_from_instantiable(
            challenger.name,
            instantiated_challenger,
            True,
        )

        non_matching_method = has_matching_methods(
            adversary_methods, instantiated_methods
        )
        if non_matching_method is not True:
            self.print_error(
                step,
                f"Method {non_matching_method} required by adversary not found in challenger",
            )

        if step.reduction is not None:
            assert isinstance(instantiated_challenger, frog_ast.Reduction)
            challenger_game_file = self.import_namespace[
                instantiated_challenger.to_use.name
            ]
            if not isinstance(challenger_game_file, frog_ast.GameFile):
                print_error(
                    step, "Instantiated challenger must correspond to a game file"
                )
                return
            challenger_from_reduction = self.instantiate_and_get_type(
                challenger_game_file.games[0],
                instantiated_challenger.to_use.args,
                instantiated_challenger.to_use.name,
                True,
            )
            if not isinstance(step.challenger, frog_ast.ConcreteGame):
                print_error(step, "Step must be a concrete game AST node")
                return

            step_game_file = self.import_namespace[step.challenger.game.name]
            if not isinstance(step_game_file, frog_ast.GameFile):
                print_error(step, "Step game must correspond to a game file")
                return

            step_challenger = self.instantiate_and_get_type(
                step_game_file.games[0],
                step.challenger.game.args,
                step.challenger.game.name,
                True,
            )
            non_matching_method = has_matching_methods(
                challenger_from_reduction, step_challenger
            )
            if non_matching_method is not True:
                self.print_error(
                    step,
                    f"Method {non_matching_method} listed in reduction's composition by not step's composition",
                )

    def leave_slice(self, the_slice: frog_ast.Slice) -> None:
        sliced_expression_type = self.get_type_from_ast(the_slice.the_array)
        if not isinstance(sliced_expression_type, frog_ast.BitStringType):
            self.print_error(
                the_slice,
                f"Slice should be used on bitstring types, received {sliced_expression_type}",
            )
        start_type = self.get_type_from_ast(the_slice.start)
        end_type = self.get_type_from_ast(the_slice.end)
        if not isinstance(start_type, frog_ast.IntType):
            self.print_error(
                the_slice, f"Start slice value should be Integer, received {start_type}"
            )
        if not isinstance(end_type, frog_ast.IntType):
            self.print_error(
                the_slice, f"End slice value should be Integer, received {end_type}"
            )

        start_type_sympy = get_sympy_expression(the_slice.start)
        end_type_sympy = get_sympy_expression(the_slice.end)
        if start_type_sympy is None or end_type_sympy is None:
            self.print_error(
                the_slice, "Could not convert start or end to sympy expression"
            )
            return
        total_length = frog_parser.parse_expression(
            str(end_type_sympy - start_type_sympy)
        )
        self.ast_type_map.set(the_slice, frog_ast.BitStringType(total_length))

    def leave_step_assumption(self, assumption: frog_ast.StepAssumption) -> None:
        expression_type = self.get_type_from_ast(assumption.expression)
        if not compare_types(frog_ast.BoolType(), expression_type):
            self.print_error(
                assumption, f"Expression has type {expression_type}, expected Bool"
            )

    def leave_induction(self, induction: frog_ast.Induction) -> None:
        start_type = self.get_type_from_ast(induction.start)
        end_type = self.get_type_from_ast(induction.end)
        if not compare_types(frog_ast.IntType(), start_type):
            self.print_error(
                induction.start, f"Induction start has type {start_type}, expected Int"
            )
        if not compare_types(frog_ast.IntType(), end_type):
            self.print_error(
                induction.start, f"Induction end has type {end_type}, expected Int"
            )

    def leave_method(self, method: frog_ast.Method) -> None:
        super().leave_method(method)
        expected_type = method.signature.return_type

        def is_bad_return(node: frog_ast.ASTNode) -> bool:
            if not isinstance(node, frog_ast.ReturnStatement):
                return False

            expr_type = self.get_type_from_ast(node.expression)

            return not compare_types(expected_type, expr_type)

        bad_return = visitors.SearchVisitor[frog_ast.ReturnStatement](
            is_bad_return
        ).visit(method)
        if bad_return is not None:
            got_type = self.get_type_from_ast(bad_return.expression)
            self.print_error(
                bad_return,
                f"{bad_return.expression} is of type {got_type}, expected {expected_type}",
            )

    def visit_variable(self, variable: frog_ast.Variable) -> None:
        my_type = self.get_type(variable.name)
        self.ast_type_map.set(variable, my_type)

    def leave_bit_string_type(self, bit_string_type: frog_ast.BitStringType) -> None:
        if bit_string_type.parameterization is not None:
            parameterized_type = self.get_type_from_ast(
                bit_string_type.parameterization
            )
            if parameterized_type != frog_ast.IntType():
                self.print_error(
                    bit_string_type,
                    f"Bit strings must be parameterized with an integer value, got type {parameterized_type}",
                )
        self.ast_type_map.set(bit_string_type, bit_string_type)

    def leave_array_access(self, array_access: frog_ast.ArrayAccess) -> None:
        if not isinstance(array_access.index, frog_ast.Integer):
            self.print_error(array_access, "Index must be an integer constant")
            return
        array_type = self.get_type_from_ast(array_access.the_array)
        if not isinstance(array_type, frog_ast.BinaryOperation):
            self.print_error(
                array_access, f"Must access a tuple type, received {array_type}"
            )
            return
        tuple_type_list = frog_ast.expand_tuple_type(array_type)
        index = array_access.index.num
        if index >= len(tuple_type_list):
            self.print_error(array_access, "Index out of bounds")
        self.ast_type_map.set(array_access, tuple_type_list[index])

    def leave_array_type(self, array_type: frog_ast.ArrayType) -> None:
        count_type = self.get_type_from_ast(array_type.count)
        if not compare_types(frog_ast.IntType(), count_type):
            self.print_error(
                array_type, f"Array count has type {count_type}, expected Int"
            )
        self.ast_type_map.set(array_type, array_type)

    def leave_map_type(self, map_type: frog_ast.MapType) -> None:
        self.ast_type_map.set(map_type, map_type)

    def leave_unary_operation(self, unary_op: frog_ast.UnaryOperation) -> None:
        if unary_op.operator == frog_ast.UnaryOperators.NOT:
            expression_type = self.get_type_from_ast(unary_op.expression)
            if not compare_types(frog_ast.BoolType(), expression_type):
                self.print_error(
                    unary_op,
                    f"{unary_op.expression} has type {expression_type}, expected Bool",
                )
            self.ast_type_map.set(unary_op, frog_ast.BoolType())
        elif unary_op.operator == frog_ast.UnaryOperators.MINUS:
            expression_type = self.get_type_from_ast(unary_op.expression)
            if not compare_types(frog_ast.IntType(), expression_type):
                self.print_error(
                    unary_op,
                    f"{unary_op.expression} has type {expression_type}, expected Int",
                )
            self.ast_type_map.set(unary_op, frog_ast.IntType())
        elif unary_op.operator == frog_ast.UnaryOperators.SIZE:
            expression_type = self.get_type_from_ast(unary_op.expression)
            if not isinstance(expression_type, frog_ast.SetType):
                self.print_error(
                    unary_op, f"Can only get size of sets, has type {expression_type}"
                )
            self.ast_type_map.set(unary_op, frog_ast.IntType())

    def leave_binary_operation(self, bin_op: frog_ast.BinaryOperation) -> None:
        if (
            bin_op.operator == frog_ast.BinaryOperators.MULTIPLY
            and isinstance(bin_op.left_expression, frog_ast.Type)
            and isinstance(bin_op.right_expression, frog_ast.Type)
        ):
            self.ast_type_map.set(bin_op, bin_op)
            return

        left_type = self.get_type_from_ast(bin_op.left_expression)
        right_type = self.get_type_from_ast(bin_op.right_expression)

        if bin_op.operator == frog_ast.BinaryOperators.ADD:
            if not compare_types(left_type, right_type):
                self.print_error(
                    bin_op,
                    f"Left expression and right expression have different types: {left_type} and {right_type}",
                )
            if not isinstance(left_type, frog_ast.IntType) and not isinstance(
                left_type, frog_ast.BitStringType
            ):
                self.print_error(bin_op, "Cannot add types")
            self.ast_type_map.set(bin_op, left_type)
        elif bin_op.operator in (
            frog_ast.BinaryOperators.MULTIPLY,
            frog_ast.BinaryOperators.SUBTRACT,
            bin_op.operator == frog_ast.BinaryOperators.DIVIDE,
        ):
            if left_type != frog_ast.IntType() or right_type != frog_ast.IntType():
                self.print_error(
                    bin_op,
                    f"Can not use operator {bin_op.operator.value} with types {left_type} and {right_type}",
                )
            self.ast_type_map.set(bin_op, frog_ast.IntType())
        elif bin_op.operator == frog_ast.BinaryOperators.AND:
            if left_type == frog_ast.BoolType() and right_type == frog_ast.BoolType():
                self.ast_type_map.set(bin_op, frog_ast.BoolType())
            else:
                self.print_error(
                    bin_op,
                    f"&& operator not supported for {left_type} and {right_type}",
                )
        elif bin_op.operator == frog_ast.BinaryOperators.OR:
            if left_type == frog_ast.BoolType() and right_type == frog_ast.BoolType():
                self.ast_type_map.set(bin_op, frog_ast.BoolType())
            elif isinstance(left_type, frog_ast.BitStringType) and isinstance(
                right_type, frog_ast.BitStringType
            ):
                if left_type.parameterization and right_type.parameterization:
                    first_length = get_sympy_expression(left_type.parameterization)
                    second_length = get_sympy_expression(right_type.parameterization)
                    if first_length is None or second_length is None:
                        print_error(
                            bin_op,
                            "Could not convert first length or second length to sympy expression",
                        )
                        return
                    total_length = first_length + second_length
                    self.ast_type_map.set(
                        bin_op,
                        frog_ast.BitStringType(
                            frog_parser.parse_expression(str(total_length))
                        ),
                    )
                else:
                    self.ast_type_map.set(bin_op, frog_ast.BitStringType(None))
            else:
                self.print_error(
                    bin_op,
                    f"|| operator not supported for {left_type} and {right_type}",
                )
        elif bin_op.operator in (
            frog_ast.BinaryOperators.EQUALS,
            frog_ast.BinaryOperators.NOTEQUALS,
        ):
            if left_type != right_type:
                self.print_error(
                    bin_op,
                    f"Cannot compare different types {left_type} and {right_type}",
                )
            self.ast_type_map.set(bin_op, frog_ast.BoolType())
        elif bin_op.operator in (
            frog_ast.BinaryOperators.LT,
            frog_ast.BinaryOperators.GT,
            frog_ast.BinaryOperators.LEQ,
            frog_ast.BinaryOperators.GEQ,
        ):
            if left_type != frog_ast.IntType() or right_type != frog_ast.IntType():
                self.print_error(
                    bin_op,
                    f"Can only compare Int types, types are {left_type}, {right_type}",
                )
            self.ast_type_map.set(bin_op, frog_ast.BoolType())
        elif bin_op.operator in (
            frog_ast.BinaryOperators.UNION,
            frog_ast.BinaryOperators.SUBSETS,
            frog_ast.BinaryOperators.SETMINUS,
        ):

            def is_parameterized_set(the_type: PossibleType) -> bool:
                return (
                    isinstance(the_type, frog_ast.SetType)
                    and the_type.parameterization is not None
                    or isinstance(the_type, frog_ast.Variable)
                )

            if not is_parameterized_set(left_type) and not is_parameterized_set(
                right_type
            ):
                self.print_error(
                    bin_op,
                    "At least one of the types should be a parameterized set,"
                    f"instead received {left_type} and {right_type}",
                )

            left_types: list[PossibleType] = []
            right_types: list[PossibleType] = []

            def add_possible_types(
                the_type: PossibleType, the_array: list[PossibleType]
            ) -> None:
                the_array.append(the_type)
                if isinstance(the_type, frog_ast.SetType) and the_type.parameterization:
                    the_array.append(the_type.parameterization)

            add_possible_types(left_type, left_types)
            add_possible_types(right_type, right_types)

            satisfied = False
            for l_type in left_types:
                for r_type in right_types:
                    satisfied = satisfied or compare_types(l_type, r_type)

            if not satisfied:
                self.print_error(
                    bin_op,
                    f"Cannot perform set operation {bin_op.operator.value} {left_type} and {right_type}",
                )
            self.ast_type_map.set(
                bin_op,
                (
                    frog_ast.BoolType()
                    if bin_op.operator == frog_ast.BinaryOperators.SUBSETS
                    else left_type
                ),
            )
        elif bin_op.operator == frog_ast.BinaryOperators.IN:
            if not isinstance(right_type, frog_ast.SetType):
                self.print_error(
                    bin_op,
                    f"{bin_op.right_expression} is of type {right_type}, expected Set",
                )
                return
            if not right_type.parameterization:
                self.print_error(
                    bin_op,
                    f"Set type for {bin_op.right_expression} must be parameterized",
                )
                return
            if not compare_types(right_type.parameterization, left_type):
                self.print_error(
                    bin_op, f"Cannot see if {left_type} is in {right_type}"
                )
            self.ast_type_map.set(bin_op, frog_ast.BoolType())

    def leave_integer(self, num: frog_ast.Integer) -> None:
        self.ast_type_map.set(num, frog_ast.IntType())

    def leave_tuple(self, the_tuple: frog_ast.Tuple) -> None:
        types: list[frog_ast.Type] = []
        for expression in the_tuple.values:
            expression_type = self.get_type_from_ast(expression)
            if not isinstance(expression_type, frog_ast.Type):
                print_error(
                    the_tuple,
                    f"{expression} should evaluate to a simple type, received {expression_type}",
                )
                return
            types.append(expression_type)
        self.ast_type_map.set(the_tuple, types)

    def leave_field(self, field: frog_ast.Field) -> None:
        super().leave_field(field)
        if field.value:
            the_type = self.get_type_from_ast(field.value)
            if not compare_types(field.type, the_type):
                self.print_error(field, f"{the_type} is not of type {field.type}")

    def leave_field_access(self, field_acess: frog_ast.FieldAccess) -> None:
        object_type = self.get_type_from_ast(field_acess.the_object)
        if not isinstance(object_type, visitors.InstantiableType):
            self.print_error(field_acess, "Accessing field of non object-type")
            return
        self.ast_type_map.set(field_acess, object_type.members[field_acess.name])  # type: ignore

    def leave_binary_num(self, binary_num: frog_ast.BinaryNum) -> None:
        self.ast_type_map.set(binary_num, frog_ast.BitStringType())

    def leave_assignment(self, assignment: frog_ast.Assignment) -> None:
        super().leave_assignment(assignment)
        expected_type = (
            assignment.the_type
            if assignment.the_type is not None
            else self.get_type_from_ast(assignment.var)
        )
        found_type = self.get_type_from_ast(assignment.value)
        if not compare_types(expected_type, found_type):
            self.print_error(
                assignment,
                f"{assignment.value} has type {found_type}, expected {expected_type}",
            )

    def leave_sample(self, sample: frog_ast.Sample) -> None:
        super().leave_sample(sample)
        expected_type = (
            sample.the_type
            if sample.the_type is not None
            else self.get_type_from_ast(sample.var)
        )
        found_type = self.get_type_from_ast(sample.sampled_from)
        if not compare_types(expected_type, found_type):
            self.print_error(
                sample,
                f"{sample.sampled_from} has type {found_type}, expected {expected_type}",
            )

    def leave_parameterized_game(
        self, parameterized_game: frog_ast.ParameterizedGame
    ) -> None:
        definition = self.import_namespace[parameterized_game.name]

        if isinstance(definition, frog_ast.GameFile):
            for game in definition.games:
                self._check_instantiation(
                    parameterized_game,
                    game,
                    parameterized_game.args,
                    self._get_file_name_from_instantiable(parameterized_game.name),
                )
        elif isinstance(definition, frog_ast.Game):
            self._check_instantiation(
                parameterized_game,
                definition,
                parameterized_game.args,
                self._get_file_name_from_instantiable(parameterized_game.name),
            )
        else:
            print_error(parameterized_game, f"{parameterized_game} is not a Game")

    def _check_instantiation(
        self,
        location: frog_ast.ASTNode,
        scheme: frog_ast.Instantiable,
        args: list[frog_ast.Expression],
        file_name: str,
    ) -> frog_ast.Instantiable:
        expected_args_count = len(scheme.parameters)
        passed_args_count = len(args)
        if expected_args_count != passed_args_count:
            self.print_error(
                location,
                f"Expected {expected_args_count} arguments, received {passed_args_count}",
            )
        param_names = [param.name for param in scheme.parameters]
        if len(param_names) != len(set(param_names)):
            self.print_error(scheme, "Duplicated parameter name")

        arg_types = [self.get_type_from_ast(arg) for arg in args]

        for index, param in enumerate(scheme.parameters):
            if not compare_types(param.type, arg_types[index]):
                self.print_error(
                    location,
                    f"{args[index]} is not of type {param.type}",
                )

        instantiated_scheme = proof_engine.instantiate(
            scheme, args, self.instantiation_namespace
        )

        CheckTypeVisitor(
            self.import_namespace,
            file_name,
            self.file_name_mapping,
            [copy.deepcopy(self.variable_type_map_stack[0])],
            copy.deepcopy(self.instantiation_namespace),
        ).visit(instantiated_scheme)
        return instantiated_scheme

    def _get_file_name_from_instantiable(self, name: str) -> str:
        return (
            self.file_name_mapping[name]
            if name in self.file_name_mapping
            else self.file_name
        )

    def leave_func_call(self, func_call: frog_ast.FuncCall) -> None:
        if (
            isinstance(func_call.func, frog_ast.Variable)
            and func_call.func.name in self.import_namespace
        ):
            scheme = self.import_namespace[func_call.func.name]
            if not isinstance(scheme, (frog_ast.Scheme, frog_ast.Primitive)):
                self.print_error(func_call, "Should be either a scheme or a primitive")
                return
            instantiated_scheme = self._check_instantiation(
                func_call,
                scheme,
                func_call.args,
                self._get_file_name_from_instantiable(func_call.func.name),
            )

            self.ast_type_map.set(
                func_call,
                get_type_from_instantiable(func_call.func.name, instantiated_scheme),
            )
        else:
            func_call_signature = self.get_type_from_ast(func_call.func)
            if not isinstance(func_call_signature, frog_ast.MethodSignature):
                self.print_error(func_call, "Was not able to get method signature")
                return
            if len(func_call_signature.parameters) != len(func_call.args):
                self.print_error(func_call, "Incorrect number of args")
            arg_types = [self.get_type_from_ast(arg) for arg in func_call.args]

            for index, arg_type in enumerate(arg_types):
                declared_type = func_call_signature.parameters[index].type
                if not compare_types(declared_type, arg_type):
                    self.print_error(
                        func_call,
                        f"{func_call.args[index]} is of type {arg_type}, expected {declared_type}",
                    )
            self.ast_type_map.set(func_call, func_call_signature.return_type)


def get_sympy_expression(the_type: frog_ast.ASTNode) -> Symbol | int | None:
    variables = visitors.VariableCollectionVisitor().visit(the_type)
    sympy_variables: dict[str, Symbol] = {
        variable.name: Symbol(variable.name) for variable in variables  # type: ignore
    }
    return visitors.FrogToSympyVisitor(sympy_variables).visit(the_type)


def has_matching_methods(
    needed_methods: visitors.InstantiableType, search_through: visitors.InstantiableType
) -> bool | frog_ast.MethodSignature:
    for method in needed_methods.members.values():
        assert isinstance(method, frog_ast.MethodSignature)
        if method.name in ("Initialize", "Finalize"):
            continue

        found = False
        for other_method in search_through.members.values():
            assert isinstance(other_method, frog_ast.MethodSignature)
            if method.name != other_method.name:
                continue
            if not compare_types(method.return_type, other_method.return_type):
                continue
            if len(method.parameters) != len(other_method.parameters):
                continue
            all_methods_same = True
            for index, param in enumerate(method.parameters):
                if not compare_types(param.type, other_method.parameters[index].type):
                    all_methods_same = False
                    break
            if all_methods_same:
                found = True
        if not found:
            return method
    return True


def compare_types(declared_type: PossibleType, value_type: PossibleType) -> bool:
    if declared_type == value_type:
        return True

    if declared_type == frog_ast.SetType() and isinstance(value_type, frog_ast.Type):
        return True

    if isinstance(declared_type, frog_ast.OptionalType) and isinstance(
        value_type, frog_ast.NoneExpression
    ):
        return True

    if isinstance(declared_type, frog_ast.OptionalType) and compare_types(
        declared_type.the_type, value_type
    ):
        return True

    expanded_declared_type = declared_type
    expanded_value_type = value_type

    if isinstance(declared_type, frog_ast.BinaryOperation):
        try:
            expanded_declared_type = frog_ast.expand_tuple_type(declared_type)
        except ValueError as value_error:
            print_error(declared_type, value_error.args[0])
    if isinstance(value_type, frog_ast.BinaryOperation):
        try:
            expanded_value_type = frog_ast.expand_tuple_type(value_type)
        except ValueError as value_error:
            print_error(value_type, value_error.args[0])
    if isinstance(declared_type, frog_ast.BinaryOperation) or isinstance(
        value_type, frog_ast.BinaryOperation
    ):
        bool_value: bool = expanded_declared_type == expanded_value_type
        return bool_value

    if isinstance(value_type, visitors.InstantiableType) and (
        declared_type == frog_ast.Variable(value_type.name)
        or declared_type == frog_ast.Variable(value_type.superclass)
    ):
        return True

    if isinstance(declared_type, frog_ast.BitStringType) and isinstance(
        value_type, frog_ast.BitStringType
    ):
        if (
            declared_type.parameterization is not None
            and value_type.parameterization is not None
        ):
            declared_type_expression = get_sympy_expression(declared_type)
            value_type_expression = get_sympy_expression(value_type)
            bool_value = declared_type_expression == value_type_expression
            return bool_value
        return True

    return False


def get_type_from_instantiable(
    name: str, instantiable: frog_ast.Instantiable, just_methods: bool = False
) -> visitors.InstantiableType:
    type_dict: dict[str, frog_ast.ASTNode] = {}
    if not just_methods:
        for field in instantiable.fields:
            to_set_to = field.type if field.type != frog_ast.SetType() else field.value
            if to_set_to is None:
                print_error(instantiable, "Set fields must have corresponding value")
                sys.exit(1)
            type_dict[field.name] = to_set_to
    for method in instantiable.methods:
        if isinstance(method, frog_ast.MethodSignature):
            type_dict[method.name] = method
        else:
            type_dict[method.signature.name] = method.signature

    superclass = (
        instantiable.primitive_name if isinstance(instantiable, frog_ast.Scheme) else ""
    )

    return visitors.InstantiableType(name, type_dict, superclass)
