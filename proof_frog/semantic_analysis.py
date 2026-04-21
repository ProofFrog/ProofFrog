import os
import sys
import copy
from typing import Optional, TypeVar, Union, TypeAlias
from sympy import Integer, Rational, Symbol
from . import frog_ast
from . import frog_parser
from . import proof_engine
from . import suggestions as _suggestions
from . import visitors


class FailedTypeCheck(Exception):
    pass


def check_well_formed(
    root: frog_ast.Root,
    file_name: str,
    allowed_root: Optional[str] = None,
) -> None:
    parse_cache = name_resolution(root, file_name, allowed_root=allowed_root)

    import_namespace: dict[str, frog_ast.Root | frog_ast.Game] = {}
    file_name_mapping: dict[str, str] = {}
    if isinstance(root, (frog_ast.GameFile, frog_ast.Scheme, frog_ast.ProofFile)):
        for imp in root.imports:
            resolved = frog_parser.resolve_import_path(
                imp.filename, file_name, allowed_root=allowed_root
            )
            parsed_file = parse_cache.get(resolved)
            if parsed_file is None:
                path_hint = ""
                path_suggestion = _suggestions.suggest_path(resolved)
                if path_suggestion:
                    suggested_name = os.path.basename(path_suggestion)
                    path_hint = f" (did you mean '{suggested_name}'?)"
                raise FileNotFoundError(
                    f"{file_name}:{imp.line_num}: imported file not found: "
                    f"'{imp.filename}'{path_hint}"
                )
            name = imp.rename if imp.rename else parsed_file.get_export_name()
            import_namespace[name] = parsed_file
            file_name_mapping[name] = resolved
    if isinstance(root, frog_ast.ProofFile):
        check_proof_well_formed(root, file_name, import_namespace, file_name_mapping)
    else:
        CheckTypeVisitor(import_namespace, file_name, file_name_mapping).visit(root)


def name_resolution(
    initial_root: frog_ast.Root,
    initial_file_name: str,
    allowed_root: Optional[str] = None,
) -> dict[str, frog_ast.Root]:
    all_imports: dict[str, frog_ast.Root] = {}

    def do_name_resolution(root: frog_ast.Root, file_name: str) -> None:
        import_namespace: dict[str, frog_ast.Game | frog_ast.Root] = {}
        if isinstance(root, (frog_ast.GameFile, frog_ast.Scheme, frog_ast.ProofFile)):
            for imp in root.imports:
                resolved = frog_parser.resolve_import_path(
                    imp.filename, file_name, allowed_root=allowed_root
                )
                if resolved in all_imports:
                    definition = all_imports[resolved]
                    import_namespace[
                        imp.rename if imp.rename else definition.get_export_name()
                    ] = definition
                    continue

                try:
                    parsed_file = frog_parser.parse_file(resolved)
                except FileNotFoundError:
                    path_hint = ""
                    path_suggestion = _suggestions.suggest_path(resolved)
                    if path_suggestion:
                        suggested_name = os.path.basename(path_suggestion)
                        path_hint = f" (did you mean '{suggested_name}'?)"
                    raise FileNotFoundError(
                        f"{file_name}:{imp.line_num}: imported file not found: "
                        f"'{imp.filename}'{path_hint}"
                    ) from None
                do_name_resolution(parsed_file, resolved)
                name = imp.rename if imp.rename else parsed_file.get_export_name()
                import_namespace[name] = parsed_file
                all_imports[resolved] = parsed_file
        NameResolutionVisitor(import_namespace, file_name).visit(root)

    do_name_resolution(initial_root, initial_file_name)
    return all_imports


T = TypeVar("T", bound=Union[frog_ast.Primitive, frog_ast.Scheme, frog_ast.Game])
PossibleType: TypeAlias = (
    None | frog_ast.Type | visitors.InstantiableType | list[visitors.InstantiableType]
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

    def visit_scheme(self, scheme: frog_ast.Scheme) -> None:
        # Make 'this' available in scheme method bodies so that
        # this.Method() calls resolve correctly.
        self_type = get_type_from_instantiable(scheme.name, scheme)
        self.variable_type_map_stack[-1]["this"] = self_type

    def visit_game(self, game: frog_ast.Game) -> None:
        game_type = get_type_from_instantiable(game.name, game)
        self.variable_type_map_stack[-1][game.name] = game_type
        self.variable_type_map_stack.append({})

    def leave_game(self, _: frog_ast.Game) -> None:
        self.variable_type_map_stack.pop()

    def visit_parameter(self, param: frog_ast.Parameter) -> None:
        resolved_type: PossibleType = param.type
        if isinstance(param.type, frog_ast.Variable):
            resolved_type = self.get_type(param.type.name)
        elif isinstance(param.type, frog_ast.FieldAccess) and isinstance(
            param.type.the_object, frog_ast.Variable
        ):
            obj_type = self.get_type(param.type.the_object.name)
            if isinstance(obj_type, visitors.InstantiableType):
                member = obj_type.members.get(param.type.name)
                if member is not None:
                    resolved_type = member  # type: ignore[assignment]
        self.variable_type_map_stack[-1][param.name] = resolved_type

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
            # Set field aliases: Set Key = [A, B] stores a ProductType so that
            # when Key appears in a type position, it resolves to [A, B] (a Type).
            if isinstance(field.value, frog_ast.Tuple) and all(
                isinstance(v, frog_ast.Type) for v in field.value.values
            ):
                product = frog_ast.ProductType(
                    [v for v in field.value.values if isinstance(v, frog_ast.Type)]
                )
                product.line_num = field.value.line_num
                product.column_num = field.value.column_num
                self.instantiation_namespace[field.name] = product
            else:
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

    def leave_unique_sample(self, unique_sample: frog_ast.UniqueSample) -> None:
        if unique_sample.the_type is not None:
            assert isinstance(unique_sample.var, frog_ast.Variable)
            self.variable_type_map_stack[-1][
                unique_sample.var.name
            ] = unique_sample.the_type

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
        self.in_parameter_type = False
        self.defining_variable: Optional[frog_ast.Expression] = None

    def _check_duplicate_names(
        self, node: frog_ast.Primitive | frog_ast.Scheme | frog_ast.Game
    ) -> None:
        """Check for duplicated field, method, and parameter names."""
        field_names = [field.name for field in node.fields]
        if len(field_names) != len(set(field_names)):
            print_error(node.fields[0], "Duplicated field name", self.file_name)

        method_signatures = (
            node.methods
            if isinstance(node, frog_ast.Primitive)
            else [method.signature for method in node.methods]
        )
        method_names = [method.name for method in method_signatures]
        if len(method_names) != len(set(method_names)):
            print_error(node.methods[0], "Duplicated method name", self.file_name)

        param_names = [param.name for param in node.parameters]
        if len(param_names) != len(set(param_names)):
            print_error(node, "Duplicated parameter name", self.file_name)

    def visit_primitive(self, primitive: frog_ast.Primitive) -> None:
        self._check_duplicate_names(primitive)

    def visit_method_signature(
        self, method_signature: frog_ast.MethodSignature
    ) -> None:
        parameter_names = [param.name for param in method_signature.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            print_error(method_signature, "Duplicated parameter name", self.file_name)

    def visit_game_file(self, game_file: frog_ast.GameFile) -> None:
        for index, game in enumerate(game_file.games):
            other_game = game_file.games[1 - index]
            other_method_names = [m.signature.name for m in other_game.methods]
            for method_signature in [method.signature for method in game.methods]:
                if not [
                    other
                    for other in other_game.methods
                    if other.signature == method_signature
                ]:
                    # Same name but different signature?
                    if method_signature.name in other_method_names:
                        other_sig = next(
                            m.signature
                            for m in other_game.methods
                            if m.signature.name == method_signature.name
                        )
                        print_error(
                            method_signature,
                            f"Method '{method_signature.name}' has different"
                            f" signatures in {game.name} and"
                            f" {other_game.name}:"
                            f" {method_signature} vs {other_sig}",
                            self.file_name,
                        )
                    else:
                        suggestion = _suggestions.suggest_identifier(
                            method_signature.name, other_method_names
                        )
                        hint = f"did you mean '{suggestion}'?" if suggestion else ""
                        print_error(
                            method_signature,
                            f"{method_signature} does not exist in"
                            f" paired game {other_game.name}",
                            self.file_name,
                            hint=hint,
                        )
            if len(game.parameters) != len(other_game.parameters):
                print_error(
                    game,
                    f"Games must have matching parameters:"
                    f" {game.name} has {len(game.parameters)}"
                    f" but {other_game.name} has"
                    f" {len(other_game.parameters)}",
                    self.file_name,
                )
            for param_index, param in enumerate(game.parameters):
                if param.type != other_game.parameters[param_index].type:
                    print_error(
                        game,
                        f"Parameter {param_index + 1} type mismatch:"
                        f" {game.name} has {param.type}"
                        f" but {other_game.name} has"
                        f" {other_game.parameters[param_index].type}",
                        self.file_name,
                    )

        for param in game_file.games[0].parameters:
            if isinstance(param.type, frog_ast.Variable):
                imported = self.import_namespace.get(param.type.name)
                if isinstance(imported, frog_ast.Scheme):
                    print_error(
                        param,
                        f"Game parameter '{param.name}' has type"
                        f" '{param.type.name}' which is a scheme;"
                        f" game parameters must be primitives",
                        self.file_name,
                    )

        if game_file.games[0].name == game_file.games[1].name:
            print_error(
                game_file, "Cannot have two games with the same name", self.file_name
            )

    def visit_scheme(self, scheme: frog_ast.Scheme) -> None:
        super().visit_scheme(scheme)
        self._check_duplicate_names(scheme)
        if scheme.primitive_name not in self.import_namespace:
            suggestion = _suggestions.suggest_identifier(
                scheme.primitive_name, list(self.import_namespace.keys())
            )
            hint = f"did you mean '{suggestion}'?" if suggestion else ""
            print_error(
                scheme,
                f"Primitive {scheme.primitive_name} is not defined",
                self.file_name,
                hint=hint,
            )
        corresponding_primitive = self.import_namespace[scheme.primitive_name]
        if not isinstance(corresponding_primitive, frog_ast.Primitive):
            print_error(
                scheme, f"{scheme.primitive_name} is not a primitive", self.file_name
            )
            return
        scheme_errors = _check_scheme_against_primitive(scheme, corresponding_primitive)
        for err in scheme_errors:
            print_error(
                scheme,
                f"Scheme {scheme.name} does not correctly implement primitive "
                f"{scheme.primitive_name}: {err}",
                self.file_name,
            )

    def visit_parameter(self, param: frog_ast.Parameter) -> None:
        self.in_parameter_type = True
        super().visit_parameter(param)

    def leave_parameter(self, _: frog_ast.Parameter) -> None:
        self.in_parameter_type = False

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

    def visit_unique_sample(self, unique_sample: frog_ast.UniqueSample) -> None:
        self.defining_variable = unique_sample.var

    def leave_unique_sample(self, unique_sample: frog_ast.UniqueSample) -> None:
        super().leave_unique_sample(unique_sample)
        self.defining_variable = None

    def visit_variable(self, var: frog_ast.Variable) -> None:
        if self.in_field_access or self.defining_variable is var:
            return
        # Check for valid!
        the_type = self.get_type(var.name)
        if the_type is None:
            if self.in_parameter_type:
                type_hint = _suggestions.suggest_type(var.name)
                if type_hint:
                    suffix = (
                        " (type names are capitalized in FrogLang)"
                        if var.name == var.name.lower()
                        else ""
                    )
                    print_error(
                        var,
                        f"Type '{var.name}' is not defined",
                        self.file_name,
                        hint=f"did you mean '{type_hint}'?{suffix}",
                    )
                else:
                    all_type_names = self._gather_type_names()
                    suggestion = _suggestions.suggest_identifier(
                        var.name, all_type_names
                    )
                    hint = f"did you mean '{suggestion}'?" if suggestion else ""
                    print_error(
                        var,
                        f"Type '{var.name}' is not defined; "
                        f"check that it is imported",
                        self.file_name,
                        hint=hint,
                    )
            else:
                qualified_suggestions = self._find_qualified_names(var.name)
                if qualified_suggestions:
                    suggestions_str = " or ".join(
                        f"'{s}'" for s in qualified_suggestions
                    )
                    print_error(
                        var,
                        f"Variable '{var.name}' is not defined."
                        f" Did you mean {suggestions_str}?",
                        self.file_name,
                    )
                else:
                    all_names = self._gather_variable_names()
                    suggestion = _suggestions.suggest_identifier(var.name, all_names)
                    hint = f"did you mean '{suggestion}'?" if suggestion else ""
                    print_error(
                        var,
                        f"Variable '{var.name}' is not defined",
                        self.file_name,
                        hint=hint,
                    )

    def _find_qualified_names(self, field_name: str) -> list[str]:
        """Search scope for InstantiableTypes that have a member matching field_name."""
        results: list[str] = []
        for scope in self.variable_type_map_stack:
            for var_name, var_type in scope.items():
                if (
                    isinstance(var_type, visitors.InstantiableType)
                    and field_name in var_type.members
                ):
                    results.append(f"{var_name}.{field_name}")
        return results

    def _gather_variable_names(self) -> list[str]:
        """Collect all variable names currently in scope."""
        names: list[str] = []
        for scope in self.variable_type_map_stack:
            names.extend(scope.keys())
        return names

    def _gather_type_names(self) -> list[str]:
        """Collect all type/import names currently in scope."""
        names: list[str] = []
        for scope in self.variable_type_map_stack:
            names.extend(scope.keys())
        names.extend(self.import_namespace.keys())
        return names

    def visit_parameterized_game(
        self, parameterized_game: frog_ast.ParameterizedGame
    ) -> None:
        the_type = self.get_type(parameterized_game.name)
        if the_type is None:
            all_names = self._gather_type_names()
            suggestion = _suggestions.suggest_identifier(
                parameterized_game.name, all_names
            )
            hint = f"did you mean '{suggestion}'?" if suggestion else ""
            print_error(
                parameterized_game,
                f"Game {parameterized_game.name} is not defined",
                self.file_name,
                hint=hint,
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

        if isinstance(the_type, frog_ast.FunctionType):
            if field_access.name != "domain":
                print_error(
                    field_access,
                    f"Function has no field '{field_access.name}'"
                    " (only 'domain' is available)",
                    self.file_name,
                )
            return

        if isinstance(the_type, frog_ast.GroupType):
            if field_access.name not in ("generator", "order", "identity"):
                print_error(
                    field_access,
                    f"Group has no field '{field_access.name}'"
                    " (only 'generator', 'order', and 'identity' are available)",
                    self.file_name,
                )
            return

        if isinstance(the_type, frog_ast.MapType):
            if field_access.name not in ("keys", "values", "entries"):
                suggestion = _suggestions.suggest_identifier(
                    field_access.name, ["keys", "values", "entries"]
                )
                hint = f"did you mean '{suggestion}'?" if suggestion else ""
                print_error(
                    field_access,
                    f"Map has no field '{field_access.name}'"
                    " (only 'keys', 'values', and 'entries' are available)",
                    self.file_name,
                    hint=hint,
                )
            return

        if not isinstance(the_type, visitors.InstantiableType):
            print_error(
                field_access,
                f"{field_access.the_object} is not a primitive, scheme, or Game",
                self.file_name,
            )
            return

        if field_access.name not in the_type.members.keys():
            suggestion = _suggestions.suggest_identifier(
                field_access.name, list(the_type.members.keys())
            )
            hint = f"did you mean '{suggestion}'?" if suggestion else ""
            print_error(
                field_access,
                f"{field_access.name} is not a property of {field_access.the_object}",
                self.file_name,
                hint=hint,
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
        if let.name in proof.sampled_let_names:
            # Sampled let entries must have FunctionType
            if not isinstance(let.type, frog_ast.FunctionType):
                print_error(
                    let,
                    f"only Function types can be sampled in let blocks, "
                    f"got {let.type}",
                    file_name,
                )
        # Always visit to register the type in the checker's scope
        type_check_visitor.visit(let)
    for assumption in proof.assumptions:
        type_check_visitor.visit(assumption)
    for lemma in proof.lemmas:
        type_check_visitor.visit(lemma.game)
        lemma_path = os.path.join(os.path.dirname(file_name), lemma.proof_path)
        if not os.path.isfile(lemma_path):
            print_error(
                lemma.game,
                f"lemma proof file not found: '{lemma.proof_path}'",
                file_name,
            )
            raise FailedTypeCheck()

    type_check_visitor.visit(proof.theorem)

    for req in proof.requirements:
        type_check_visitor.visit(req.target)
        target_type = type_check_visitor.get_type_from_ast(req.target)
        if req.kind == "prime":
            if not isinstance(target_type, frog_ast.IntType):
                print_error(
                    req,
                    f"`is prime` requires an integer-typed target, "
                    f"got {_format_type(target_type)}",
                    file_name,
                )
        else:
            print_error(
                req,
                f"unknown structural predicate: `{req.kind}`",
                file_name,
            )

    for helper in proof.helpers:
        import_namespace[helper.name] = helper
    for step in proof.steps:
        type_check_visitor.visit(step)


def _format_type(t: PossibleType) -> str:
    """Format a PossibleType for display in error messages."""
    if isinstance(t, list):
        return "[" + ", ".join(str(item) for item in t) + "]"
    return str(t)


def _truncate_expr(expr: object, max_len: int = 60) -> str:
    """Truncate an expression's string representation for error messages."""
    s = str(expr)
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def print_error(
    location: frog_ast.ASTNode,
    message: str,
    file_name: str = "Unknown",
    hint: str = "",
) -> None:
    line, col = location.line_num, location.column_num
    loc = file_name
    if line >= 0:
        loc += f":{line}:{col}"
    print(f"{loc}: error: {message}", file=sys.stderr)
    if file_name != "Unknown" and os.path.isfile(file_name) and line >= 1:
        try:
            with open(file_name, encoding="utf-8") as f:
                lines = f.readlines()
            if line <= len(lines):
                src = lines[line - 1].rstrip()
                caret = " " * col + "^"
                print(src, file=sys.stderr)
                print(caret, file=sys.stderr)
        except OSError:
            pass
    if hint:
        print(f"  hint: {hint}", file=sys.stderr)
    raise FailedTypeCheck()


def _types_comparable(left_type: PossibleType, right_type: PossibleType) -> bool:
    """Check if two types can be compared with == or !=.

    Allows T == T, T? == None, None == T?, T == T?, and T? == T.
    """
    if left_type == right_type:
        return True
    # T? == None or None == T?
    if isinstance(left_type, frog_ast.OptionalType) and isinstance(
        right_type, frog_ast.NoneExpression
    ):
        return True
    if isinstance(right_type, frog_ast.OptionalType) and isinstance(
        left_type, frog_ast.NoneExpression
    ):
        return True
    # T == T? or T? == T
    left_base = (
        left_type.the_type
        if isinstance(left_type, frog_ast.OptionalType)
        else left_type
    )
    right_base = (
        right_type.the_type
        if isinstance(right_type, frog_ast.OptionalType)
        else right_type
    )
    if left_base == right_base:
        return True
    # Two abstract type variables — needed for requires clauses like
    # S.Message == S.Ciphertext
    if isinstance(left_type, frog_ast.Variable) and isinstance(
        right_type, frog_ast.Variable
    ):
        return True
    # Abstract type variable compared with a concrete set-like type — needed
    # for requires clauses like E.Key == BitString<n>
    if isinstance(left_type, frog_ast.Variable) and isinstance(
        right_type, (frog_ast.BitStringType, frog_ast.ModIntType, frog_ast.SetType)
    ):
        return True
    if isinstance(right_type, frog_ast.Variable) and isinstance(
        left_type, (frog_ast.BitStringType, frog_ast.ModIntType, frog_ast.SetType)
    ):
        return True
    return False


def _extract_null_check_variable(
    condition: frog_ast.Expression,
    operator: frog_ast.BinaryOperators,
) -> Optional[str]:
    """If condition is `x == None` (or `!=`), return x's variable name."""
    if not isinstance(condition, frog_ast.BinaryOperation):
        return None
    if condition.operator != operator:
        return None
    if isinstance(condition.left_expression, frog_ast.Variable) and isinstance(
        condition.right_expression, frog_ast.NoneExpression
    ):
        return condition.left_expression.name
    if isinstance(condition.right_expression, frog_ast.Variable) and isinstance(
        condition.left_expression, frog_ast.NoneExpression
    ):
        return condition.right_expression.name
    return None


def _block_always_returns(block: frog_ast.Block) -> bool:
    """Check if a block always returns (last statement is a return)."""
    if not block.statements:
        return False
    return isinstance(block.statements[-1], frog_ast.ReturnStatement)


def _extract_subsets_pairs(
    instantiated_scheme: frog_ast.Instantiable,
) -> list[tuple[PossibleType, PossibleType]]:
    """Extract type-equality pairs from ``==`` constraints in requires clauses.

    Only ``==`` constraints are used: they guarantee the two types represent
    the same set, so normalizing one to the other preserves sampling
    distributions.  ``subsets`` constraints are excluded because if A ⊊ B,
    replacing ``x <- A`` with ``x <- B`` would change the distribution.
    """
    pairs: list[tuple[PossibleType, PossibleType]] = []
    if not isinstance(instantiated_scheme, frog_ast.Scheme):
        return pairs
    for req in instantiated_scheme.requirements:
        if (
            isinstance(req, frog_ast.BinaryOperation)
            and req.operator == frog_ast.BinaryOperators.EQUALS
        ):
            if isinstance(req.left_expression, frog_ast.Type) and isinstance(
                req.right_expression, frog_ast.Type
            ):
                pairs.append((req.left_expression, req.right_expression))
    return pairs


class CheckTypeVisitor(VariableTypeVisitor):
    # pylint: disable=too-many-positional-arguments,too-many-arguments
    def __init__(
        self,
        import_namespace: dict[str, frog_ast.Root | frog_ast.Game],
        file_name: str,
        file_name_mapping: dict[str, str],
        variable_type_map_stack: VariableTypeMapStackType = None,
        field_value_map: Optional[frog_ast.Namespace] = None,
        subsets_pairs: Optional[list[tuple[PossibleType, PossibleType]]] = None,
    ) -> None:
        super().__init__(import_namespace, variable_type_map_stack, field_value_map)
        self.import_namespace = import_namespace
        self.ast_type_map = frog_ast.ASTMap[PossibleType]()
        self.file_name = file_name
        self.file_name_mapping = file_name_mapping
        self.subsets_pairs: list[tuple[PossibleType, PossibleType]] = (
            subsets_pairs if subsets_pairs is not None else []
        )
        # Expression-level equality constraints from `requires e1 == e2;`
        # where e1 and e2 are numeric expressions (e.g. `F.in == 1`).  These
        # feed into the SymPy substitution dictionary used by compare_types
        # to unify concrete BitString<n> against BitString<symbol> when a
        # constraint pins the symbol to a concrete value.
        self.expression_equality_pairs: list[
            tuple[frog_ast.Expression, frog_ast.Expression]
        ] = []
        self._instantiation_cache: dict[
            tuple[str, tuple[str, ...]], frog_ast.Instantiable
        ] = {}

    def result(self) -> None:
        return None

    def _resolve_type_alias(
        self, t: PossibleType, _seen: frozenset[str] | None = None
    ) -> PossibleType:
        """Resolve Variable and FieldAccess types through known aliases."""
        if _seen is None:
            _seen = frozenset()
        if isinstance(t, frog_ast.Variable):
            if t.name in self.instantiation_namespace:
                if t.name in _seen:
                    return t  # Avoid infinite recursion on self-referencing aliases
                resolved = self.instantiation_namespace[t.name]
                if isinstance(resolved, frog_ast.Type):
                    # Recursively resolve in case the alias is itself a FieldAccess
                    return self._resolve_type_alias(resolved, _seen | {t.name})
            # Also resolve through the variable type map (game/scheme parameters)
            if t.name not in _seen:
                var_type = self.get_type(t.name)
                if var_type is not None and isinstance(var_type, frog_ast.Type):
                    return self._resolve_type_alias(var_type, _seen | {t.name})
        if isinstance(t, frog_ast.FieldAccess) and isinstance(
            t.the_object, frog_ast.Variable
        ):
            obj_type = self.get_type(t.the_object.name)
            if isinstance(obj_type, visitors.InstantiableType):
                member = obj_type.members.get(t.name)
                if member is not None:
                    return self._resolve_type_alias(member, _seen)  # type: ignore[arg-type]
        if isinstance(t, frog_ast.ProductType):
            resolved_types: list[frog_ast.Type] = []
            for sub in t.types:
                resolved_sub = self._resolve_type_alias(sub, _seen)
                if isinstance(resolved_sub, frog_ast.Type):
                    resolved_types.append(resolved_sub)
                else:
                    resolved_types.append(sub)
            return frog_ast.ProductType(resolved_types)
        # Tuple-of-types can appear in type positions after parameter
        # substitution (e.g., Set D = [T1, T2] parsed as Tuple in
        # expression position).  Resolve elements and normalize to
        # ProductType so FieldAccess aliases inside are resolved.
        if isinstance(t, frog_ast.Tuple) and all(
            isinstance(v, frog_ast.Type) for v in t.values
        ):
            resolved_types_t: list[frog_ast.Type] = []
            for sub in t.values:
                resolved_sub = self._resolve_type_alias(sub, _seen)
                if isinstance(resolved_sub, frog_ast.Type):
                    resolved_types_t.append(resolved_sub)
                else:
                    assert isinstance(sub, frog_ast.Type)
                    resolved_types_t.append(sub)
            return frog_ast.ProductType(resolved_types_t)
        if isinstance(t, frog_ast.OptionalType):
            resolved_inner = self._resolve_type_alias(t.the_type, _seen)
            if isinstance(resolved_inner, frog_ast.Type):
                return frog_ast.OptionalType(resolved_inner)
        if isinstance(t, frog_ast.ArrayType):
            resolved_elem = self._resolve_type_alias(t.element_type, _seen)
            if isinstance(resolved_elem, frog_ast.Type):
                return frog_ast.ArrayType(resolved_elem, t.count)
        if isinstance(t, frog_ast.FunctionType):
            resolved_domain = self._resolve_type_alias(t.domain_type, _seen)
            resolved_range = self._resolve_type_alias(t.range_type, _seen)
            if isinstance(resolved_domain, frog_ast.Type) or isinstance(
                resolved_range, frog_ast.Type
            ):
                return frog_ast.FunctionType(
                    (
                        resolved_domain
                        if isinstance(resolved_domain, frog_ast.Type)
                        else t.domain_type
                    ),
                    (
                        resolved_range
                        if isinstance(resolved_range, frog_ast.Type)
                        else t.range_type
                    ),
                )
        if isinstance(t, frog_ast.MapType):
            resolved_key = self._resolve_type_alias(t.key_type, _seen)
            resolved_value = self._resolve_type_alias(t.value_type, _seen)
            if isinstance(resolved_key, frog_ast.Type) or isinstance(
                resolved_value, frog_ast.Type
            ):
                return frog_ast.MapType(
                    (
                        resolved_key
                        if isinstance(resolved_key, frog_ast.Type)
                        else t.key_type
                    ),
                    (
                        resolved_value
                        if isinstance(resolved_value, frog_ast.Type)
                        else t.value_type
                    ),
                )
        return t

    def _normalize_bitstring_params(self, t: PossibleType) -> PossibleType:
        """Normalize BitString parameterizations.

        Replaces FieldAccess expressions (like G.lambda) with the field's
        internal Variable name (like lambda). Uses both requires equality
        constraints and direct Int field lookups.
        """
        if isinstance(t, frog_ast.ProductType):
            normalized = [self._normalize_bitstring_params(sub) for sub in t.types]
            if any(n is not orig for n, orig in zip(normalized, t.types)):
                return frog_ast.ProductType(
                    [
                        n if isinstance(n, frog_ast.Type) else orig
                        for n, orig in zip(normalized, t.types)
                    ]
                )
            return t
        if not isinstance(t, frog_ast.BitStringType) or t.parameterization is None:
            return t
        # Build substitution map: FieldAccess -> Variable
        aliases: dict[str, frog_ast.ASTNode] = {}
        # From requires equality constraints
        for left, right in self.subsets_pairs:
            if isinstance(left, frog_ast.FieldAccess) and isinstance(
                right, frog_ast.Variable
            ):
                aliases[str(left)] = right
            elif isinstance(right, frog_ast.FieldAccess) and isinstance(
                left, frog_ast.Variable
            ):
                aliases[str(right)] = left
        # From InstantiableType Int fields: G.lambda -> Variable("lambda")
        self._collect_field_access_aliases(t.parameterization, aliases)
        if not aliases:
            return t
        new_param = self._substitute_expr(copy.deepcopy(t.parameterization), aliases)
        if isinstance(new_param, frog_ast.Expression):
            return frog_ast.BitStringType(new_param)
        return t

    def _collect_field_access_aliases(
        self, expr: frog_ast.ASTNode, aliases: dict[str, frog_ast.ASTNode]
    ) -> None:
        """Collect FieldAccess -> Variable aliases from Int fields."""
        if isinstance(expr, frog_ast.FieldAccess) and isinstance(
            expr.the_object, frog_ast.Variable
        ):
            obj_type = self.get_type(expr.the_object.name)
            if isinstance(obj_type, visitors.InstantiableType):
                member_val = obj_type.members.get(expr.name)
                if isinstance(member_val, frog_ast.IntType):
                    aliases[str(expr)] = frog_ast.Variable(expr.name)
        elif isinstance(expr, frog_ast.BinaryOperation):
            self._collect_field_access_aliases(expr.left_expression, aliases)
            self._collect_field_access_aliases(expr.right_expression, aliases)

    @staticmethod
    def _substitute_expr(
        expr: frog_ast.ASTNode, aliases: dict[str, frog_ast.ASTNode]
    ) -> frog_ast.ASTNode:
        """Substitute expression nodes by their string representation."""
        key = str(expr)
        if key in aliases:
            return copy.deepcopy(aliases[key])
        if isinstance(expr, frog_ast.BinaryOperation):
            new_left = CheckTypeVisitor._substitute_expr(expr.left_expression, aliases)
            new_right = CheckTypeVisitor._substitute_expr(
                expr.right_expression, aliases
            )
            if isinstance(new_left, frog_ast.Expression) and isinstance(
                new_right, frog_ast.Expression
            ):
                return frog_ast.BinaryOperation(expr.operator, new_left, new_right)
        return expr

    def _build_sympy_subs(self) -> dict[Symbol, Symbol | int]:
        """Build SymPy substitutions from Int field definitions and requires."""
        subs: dict[Symbol, Symbol | int] = {}
        # From primitive/scheme Int fields: map internal name to qualified name.
        # E.g., if F is a PRF with Int out, add Symbol("out") -> Symbol("F.out")
        # so that bare internal names from return types can be resolved.
        for type_map in self.variable_type_map_stack:
            for name, val in type_map.items():
                if isinstance(val, visitors.InstantiableType):
                    for member_name, member_val in val.members.items():
                        if isinstance(member_val, frog_ast.IntType):
                            qualified = f"{name}.{member_name}"
                            subs[Symbol(member_name)] = Symbol(qualified)
        # From instantiation_namespace Int fields: expand local definitions
        # E.g., "stretch" -> 2 * G.lambda means Symbol("stretch") -> 2*Symbol("G.lambda")
        for ns_name, ns_val in self.instantiation_namespace.items():
            if ns_val is None or not isinstance(ns_val, frog_ast.ASTNode):
                continue  # Skip non-AST values
            # Skip non-numeric type aliases (BitStringType, ProductType, etc.)
            # but keep Variables, FieldAccess, and BinaryOperations that
            # represent numeric/symbolic Int field values.
            if isinstance(
                ns_val,
                (
                    frog_ast.BitStringType,
                    frog_ast.ProductType,
                    frog_ast.SetType,
                    frog_ast.BoolType,
                    frog_ast.OptionalType,
                    frog_ast.ModIntType,
                ),
            ):
                continue
            # Skip instantiated schemes/primitives/games stored as AST nodes
            if isinstance(ns_val, (frog_ast.Primitive, frog_ast.Scheme, frog_ast.Game)):
                continue
            sym_val = _ast_to_sympy(ns_val)
            if sym_val is not None:
                subs[Symbol(ns_name)] = sym_val
        # From requires equality pairs (type-level)
        for left, right in self.subsets_pairs:
            if not isinstance(left, frog_ast.ASTNode) or not isinstance(
                right, frog_ast.ASTNode
            ):
                continue
            left_sym = _ast_to_sympy(left)
            right_sym = _ast_to_sympy(right)
            if (
                left_sym is not None
                and right_sym is not None
                and isinstance(left_sym, Symbol)
            ):
                subs[left_sym] = right_sym
        # From requires equality pairs (expression-level, e.g. F.in == 1)
        for left_expr, right_expr in self.expression_equality_pairs:
            left_sym = _ast_to_sympy(left_expr)
            right_sym = _ast_to_sympy(right_expr)
            if left_sym is None or right_sym is None:
                continue
            if isinstance(left_sym, Symbol):
                subs[left_sym] = right_sym
            elif isinstance(right_sym, Symbol):
                subs[right_sym] = left_sym
        return subs

    def check_types(
        self, declared_type: PossibleType, value_type: PossibleType
    ) -> bool:
        """compare_types with subsets constraint and alias awareness."""
        declared_type = self._resolve_type_alias(declared_type)
        value_type = self._resolve_type_alias(value_type)
        # Resolve subsets_pairs through aliases so FieldAccess-based
        # requires constraints match resolved Variable types
        resolved_pairs: list[tuple[PossibleType, PossibleType]] = [
            (self._resolve_type_alias(a), self._resolve_type_alias(b))
            for a, b in self.subsets_pairs
        ]
        # First try with AST-level normalization (handles simple cases
        # like G.lambda -> Variable("lambda") without name collisions)
        norm_declared = self._normalize_bitstring_params(declared_type)
        norm_value = self._normalize_bitstring_params(value_type)
        if compare_types(norm_declared, norm_value, resolved_pairs):
            return True
        # Fall back to SymPy-level substitutions for complex cases
        # (Int field definitions + requires equalities)
        sympy_subs = self._build_sympy_subs()
        return compare_types(declared_type, value_type, resolved_pairs, sympy_subs)

    def print_error(
        self, location: frog_ast.ASTNode, message: str, hint: str = ""
    ) -> None:
        print_error(location, message, self.file_name, hint=hint)

    def _type_alias(self, type_obj: PossibleType) -> str | None:
        """Find a user-facing alias for a resolved type (e.g. 'E.Key' for KS)."""
        if type_obj is None:
            return None
        type_str = str(type_obj)
        for scope in self.variable_type_map_stack:
            for var_name, var_type in scope.items():
                if not isinstance(var_type, visitors.InstantiableType):
                    continue
                for member_name, member_type in var_type.members.items():
                    if str(member_type) == type_str:
                        return f"{var_name}.{member_name}"
        return None

    def _format_type_with_alias(self, type_obj: PossibleType) -> str:
        """Format a type, including its alias if one exists."""
        base = _format_type(type_obj)
        alias = self._type_alias(type_obj)
        if alias and alias != base:
            return f"{base} ({alias})"
        return base

    def get_type_from_ast(self, node: frog_ast.ASTNode) -> PossibleType:
        try:
            result = self.ast_type_map.get(node)
            return self._resolve_type_alias(result)
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

    def visit_scheme(self, scheme: frog_ast.Scheme) -> None:
        super().visit_scheme(scheme)
        # Pre-extract equality/subsets pairs from requires clauses so they
        # are available during method body type checking.
        for req in scheme.requirements:
            self._extract_requires_pairs(req)

    def _extract_requires_pairs(self, expr: frog_ast.Expression) -> None:
        """Recursively extract pairs from requires expressions."""
        if not isinstance(expr, frog_ast.BinaryOperation):
            return
        if expr.operator == frog_ast.BinaryOperators.AND:
            self._extract_requires_pairs(expr.left_expression)
            self._extract_requires_pairs(expr.right_expression)
        elif expr.operator in (
            frog_ast.BinaryOperators.SUBSETS,
            frog_ast.BinaryOperators.EQUALS,
        ):
            left = expr.left_expression
            right = expr.right_expression
            # Value-level equality such as `requires F.in == 1`: at least
            # one operand is a pure Expression (Integer, BinaryOperation,
            # etc.) that is not a Type node.  Record for SymPy substitution
            # in compare_types.  Note: FieldAccess is both an Expression and
            # a Type in the AST hierarchy, so we detect value-level pairs by
            # the presence of a non-Type operand.
            if expr.operator == frog_ast.BinaryOperators.EQUALS and (
                not isinstance(left, frog_ast.Type)
                or not isinstance(right, frog_ast.Type)
            ):
                self.expression_equality_pairs.append((left, right))
                return
            if isinstance(left, frog_ast.Type) and isinstance(right, frog_ast.Type):
                self.subsets_pairs.append((left, right))
                # Warn when a == constraint has the abstract type on the
                # right, since the type normalizer only fires when the
                # left side resolves to a Variable after instantiation.
                # At the AST level, abstract types appear as FieldAccess
                # (E.Key) or Variable (bare type params), while concrete
                # types are BitStringType, ModIntType, etc.
                # E.g. `requires BitString<n> == E.Key` should be written
                # as `requires E.Key == BitString<n>`.
                if expr.operator == frog_ast.BinaryOperators.EQUALS:
                    left_is_concrete = isinstance(
                        expr.left_expression,
                        (frog_ast.BitStringType, frog_ast.ModIntType),
                    )
                    right_is_abstract = isinstance(
                        expr.right_expression,
                        (frog_ast.Variable, frog_ast.FieldAccess),
                    )
                    if left_is_concrete and right_is_abstract:
                        self.print_error(
                            expr,
                            "In type equality constraints, write the abstract"
                            " type parameter on the left: requires"
                            f" {expr.right_expression}"
                            f" == {expr.left_expression}",
                        )

    def visit_primitive(self, primitive: frog_ast.Primitive) -> None:
        self._shared_primitive_scheme_checks(primitive)

    def leave_scheme(self, scheme: frog_ast.Scheme) -> None:
        self._shared_primitive_scheme_checks(scheme)
        for requirement in scheme.requirements:
            requirement_type = self.get_type_from_ast(requirement)
            if not self.check_types(frog_ast.BoolType(), requirement_type):
                self.print_error(
                    requirement,
                    f"Requirements should evaluate to a boolean type, received {requirement_type}",
                )
        # Check that it implements the expected methods

    def leave_if_statement(self, if_statement: frog_ast.IfStatement) -> None:
        for condition in if_statement.conditions:
            condition_type = self.get_type_from_ast(condition)
            if not self.check_types(frog_ast.BoolType(), condition_type):
                self.print_error(
                    condition, f"Condition has type {condition_type}, expected bool"
                )
        # Null-narrowing: if (x == None) { return ...; } narrows x after the if
        if if_statement.conditions and not if_statement.has_else_block():
            var_name = _extract_null_check_variable(
                if_statement.conditions[0], frog_ast.BinaryOperators.EQUALS
            )
            if var_name is not None and _block_always_returns(if_statement.blocks[0]):
                current_type = self.get_type(var_name)
                if isinstance(current_type, frog_ast.OptionalType):
                    self.variable_type_map_stack[-1][var_name] = current_type.the_type

    def leave_numeric_for(self, numeric_for: frog_ast.NumericFor) -> None:
        super().leave_numeric_for(numeric_for)
        start_type = self.get_type_from_ast(numeric_for.start)
        end_type = self.get_type_from_ast(numeric_for.end)
        if not self.check_types(frog_ast.IntType(), start_type):
            self.print_error(
                numeric_for, f"Start expression has type {start_type}, expected Int"
            )
        if not self.check_types(frog_ast.IntType(), end_type):
            self.print_error(
                numeric_for, f"End expression has type {end_type}, expected Int"
            )

    def leave_generic_for(self, generic_for: frog_ast.GenericFor) -> None:
        super().leave_generic_for(generic_for)
        over_type = self.get_type_from_ast(generic_for.over)
        element_type: PossibleType
        if isinstance(over_type, frog_ast.SetType):
            element_type = over_type.parameterization
        elif isinstance(over_type, frog_ast.ArrayType):
            element_type = over_type.element_type
        else:
            self.print_error(
                generic_for,
                f"Must iterate over Set, Array, Map.keys, Map.values, or Map.entries;"
                f" got type {over_type}",
            )
            return
        if element_type is not None and not self.check_types(
            generic_for.var_type, element_type
        ):
            self.print_error(
                generic_for,
                f"Loop variable has type {generic_for.var_type},"
                f" but iteration yields elements of type {element_type}",
            )

    def visit_reduction(self, reduction: frog_ast.Reduction) -> None:
        super().visit_reduction(reduction)

        adversary_definition = self.import_namespace[reduction.play_against.name]
        if not isinstance(adversary_definition, frog_ast.GameFile):
            self.print_error(reduction, "Adversary must be a game file")
            return

        # Build a combined namespace so that scheme FuncCalls in the adversary
        # args (e.g. UG(K, NG, H, G) in KEMCCA(UG(K, NG, H, G)).Adversary) can
        # be expanded to their field types. Scheme/primitive definitions live in
        # import_namespace but not in instantiation_namespace.
        combined_ns: frog_ast.Namespace = {
            **self.instantiation_namespace,
            **{
                name: val
                for name, val in self.import_namespace.items()
                if isinstance(val, (frog_ast.Scheme, frog_ast.Primitive))
            },
        }
        adversary_type = get_type_from_instantiable(
            reduction.play_against.name,
            proof_engine.instantiate(
                adversary_definition.games[0],
                reduction.play_against.args,
                combined_ns,
            ),
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
                    f"Reduction composes with {instantiated_challenger.to_use} "
                    f"which has method '{non_matching_method}', "
                    f"but step's game {step.challenger.game} has no matching method. "
                    f"Check that the reduction's compose clause uses the same "
                    f"parameter types as the step",
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
                the_slice,
                "Slice bounds must be integer constants or simple arithmetic expressions",
            )
            return
        total_length = frog_parser.parse_expression(
            str(end_type_sympy - start_type_sympy)
        )
        self.ast_type_map.set(the_slice, frog_ast.BitStringType(total_length))

    def leave_step_assumption(self, assumption: frog_ast.StepAssumption) -> None:
        expression_type = self.get_type_from_ast(assumption.expression)
        if not self.check_types(frog_ast.BoolType(), expression_type):
            self.print_error(
                assumption, f"Expression has type {expression_type}, expected Bool"
            )

    def leave_induction(self, induction: frog_ast.Induction) -> None:
        start_type = self.get_type_from_ast(induction.start)
        end_type = self.get_type_from_ast(induction.end)
        if not self.check_types(frog_ast.IntType(), start_type):
            self.print_error(
                induction.start, f"Induction start has type {start_type}, expected Int"
            )
        if not self.check_types(frog_ast.IntType(), end_type):
            self.print_error(
                induction.start, f"Induction end has type {end_type}, expected Int"
            )

    def leave_method(self, method: frog_ast.Method) -> None:
        super().leave_method(method)
        expected_type = method.signature.return_type

        if not isinstance(expected_type, frog_ast.Void):
            has_return = visitors.SearchVisitor[frog_ast.ReturnStatement](
                lambda node: isinstance(node, frog_ast.ReturnStatement)
            ).visit(method)
            if has_return is None:
                self.print_error(
                    method,
                    f"method '{method.signature.name}' has return type"
                    f" {expected_type} but is missing a return statement",
                )

        def is_bad_return(node: frog_ast.ASTNode) -> bool:
            if not isinstance(node, frog_ast.ReturnStatement):
                return False

            expr_type = self.get_type_from_ast(node.expression)

            return not self.check_types(expected_type, expr_type)

        bad_return = visitors.SearchVisitor[frog_ast.ReturnStatement](
            is_bad_return
        ).visit(method)
        if bad_return is not None:
            got_type = self.get_type_from_ast(bad_return.expression)
            self.print_error(
                bad_return,
                f"{_truncate_expr(bad_return.expression)} has type"
                f" {self._format_type_with_alias(got_type)},"
                f" expected {expected_type}"
                f" (return type of {method.signature.name})",
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

    def leave_function_type(self, rf_type: frog_ast.FunctionType) -> None:
        self.ast_type_map.set(rf_type, rf_type)

    def leave_mod_int_type(self, mod_int_type: frog_ast.ModIntType) -> None:
        modulus_type = self.get_type_from_ast(mod_int_type.modulus)
        if modulus_type != frog_ast.IntType():
            self.print_error(
                mod_int_type,
                f"ModInt must be parameterized with an integer value, got type {modulus_type}",
            )
        self.ast_type_map.set(mod_int_type, mod_int_type)

    def leave_group_elem_type(self, group_elem_type: frog_ast.GroupElemType) -> None:
        group_type = self.get_type_from_ast(group_elem_type.group)
        if not isinstance(group_type, frog_ast.GroupType):
            self.print_error(
                group_elem_type,
                f"GroupElem must be parameterized with a Group, got type {group_type}",
            )
        self.ast_type_map.set(group_elem_type, group_elem_type)

    def leave_array_access(self, array_access: frog_ast.ArrayAccess) -> None:
        array_type = self.get_type_from_ast(array_access.the_array)
        # Map subscript: T[key] returns the value type
        if isinstance(array_type, frog_ast.MapType):
            index_type = self.get_type_from_ast(array_access.index)
            if not self.check_types(array_type.key_type, index_type):
                self.print_error(
                    array_access,
                    f"Map key type mismatch: expected"
                    f" {self._format_type_with_alias(array_type.key_type)}, got"
                    f" {self._format_type_with_alias(index_type)}",
                )
            self.ast_type_map.set(array_access, array_type.value_type)
            return
        # Tuple indexing: tuple[integer_constant]
        if not isinstance(array_access.index, frog_ast.Integer):
            self.print_error(array_access, "Index must be an integer constant")
            return
        if not isinstance(array_type, frog_ast.ProductType):
            self.print_error(
                array_access, f"Must access a tuple type, received {array_type}"
            )
            return
        index = array_access.index.num
        if index >= len(array_type.types):
            self.print_error(array_access, "Index out of bounds")
        self.ast_type_map.set(array_access, array_type.types[index])

    def leave_array_type(self, array_type: frog_ast.ArrayType) -> None:
        count_type = self.get_type_from_ast(array_type.count)
        if not self.check_types(frog_ast.IntType(), count_type):
            self.print_error(
                array_type, f"Array count has type {count_type}, expected Int"
            )
        self.ast_type_map.set(array_type, array_type)

    def leave_map_type(self, map_type: frog_ast.MapType) -> None:
        self.ast_type_map.set(map_type, map_type)

    def leave_unary_operation(self, unary_op: frog_ast.UnaryOperation) -> None:
        if unary_op.operator == frog_ast.UnaryOperators.NOT:
            expression_type = self.get_type_from_ast(unary_op.expression)
            if not self.check_types(frog_ast.BoolType(), expression_type):
                self.print_error(
                    unary_op,
                    f"{unary_op.expression} has type {expression_type}, expected Bool",
                )
            self.ast_type_map.set(unary_op, frog_ast.BoolType())
        elif unary_op.operator == frog_ast.UnaryOperators.MINUS:
            expression_type = self.get_type_from_ast(unary_op.expression)
            if isinstance(expression_type, frog_ast.ModIntType):
                self.ast_type_map.set(unary_op, expression_type)
            elif self.check_types(frog_ast.IntType(), expression_type):
                self.ast_type_map.set(unary_op, frog_ast.IntType())
            else:
                self.print_error(
                    unary_op,
                    f"{unary_op.expression} has type {expression_type}, expected Int or ModInt",
                )
        elif unary_op.operator == frog_ast.UnaryOperators.SIZE:
            expression_type = self.get_type_from_ast(unary_op.expression)
            if not isinstance(expression_type, frog_ast.SetType):
                self.print_error(
                    unary_op, f"Can only get size of sets, has type {expression_type}"
                )
            self.ast_type_map.set(unary_op, frog_ast.IntType())

    def leave_product_type(self, product_type: frog_ast.ProductType) -> None:
        self.ast_type_map.set(product_type, product_type)

    def leave_binary_operation(self, bin_op: frog_ast.BinaryOperation) -> None:
        left_type = self.get_type_from_ast(bin_op.left_expression)
        right_type = self.get_type_from_ast(bin_op.right_expression)

        if bin_op.operator == frog_ast.BinaryOperators.ADD:
            if isinstance(left_type, frog_ast.ModIntType) and isinstance(
                right_type, frog_ast.ModIntType
            ):
                if not self.check_types(left_type, right_type):
                    self.print_error(
                        bin_op,
                        f"ModInt addition requires matching moduli, got {left_type} and {right_type}",
                    )
                self.ast_type_map.set(bin_op, left_type)
            elif isinstance(left_type, frog_ast.IntType) and isinstance(
                right_type, frog_ast.IntType
            ):
                self.ast_type_map.set(bin_op, frog_ast.IntType())
            elif isinstance(left_type, frog_ast.BitStringType) and isinstance(
                right_type, frog_ast.BitStringType
            ):
                if not self.check_types(left_type, right_type):
                    self.print_error(
                        bin_op,
                        f"Left expression and right expression have different types: {left_type} and {right_type}",
                    )
                self.ast_type_map.set(bin_op, left_type)
            else:
                self.print_error(
                    bin_op,
                    f"Cannot add types {left_type} and {right_type}",
                )
        elif bin_op.operator == frog_ast.BinaryOperators.SUBTRACT:
            if isinstance(left_type, frog_ast.ModIntType) and isinstance(
                right_type, frog_ast.ModIntType
            ):
                if not self.check_types(left_type, right_type):
                    self.print_error(
                        bin_op,
                        f"ModInt subtraction requires matching moduli, got {left_type} and {right_type}",
                    )
                self.ast_type_map.set(bin_op, left_type)
            elif left_type == frog_ast.IntType() and right_type == frog_ast.IntType():
                self.ast_type_map.set(bin_op, frog_ast.IntType())
            else:
                self.print_error(
                    bin_op,
                    f"Can not use operator - with types {left_type} and {right_type}",
                )
        elif bin_op.operator == frog_ast.BinaryOperators.MULTIPLY:
            if isinstance(left_type, frog_ast.ModIntType) and isinstance(
                right_type, frog_ast.ModIntType
            ):
                if not self.check_types(left_type, right_type):
                    self.print_error(
                        bin_op,
                        f"ModInt multiplication requires matching moduli, got {left_type} and {right_type}",
                    )
                self.ast_type_map.set(bin_op, left_type)
            elif left_type == frog_ast.IntType() and right_type == frog_ast.IntType():
                self.ast_type_map.set(bin_op, frog_ast.IntType())
            elif isinstance(left_type, frog_ast.GroupElemType) and isinstance(
                right_type, frog_ast.GroupElemType
            ):
                if not self.check_types(left_type, right_type):
                    self.print_error(
                        bin_op,
                        f"GroupElem multiplication requires matching groups, got {left_type} and {right_type}",
                    )
                self.ast_type_map.set(bin_op, left_type)
            else:
                self.print_error(
                    bin_op,
                    f"Can not use operator * with types {left_type} and {right_type}",
                )
        elif bin_op.operator == frog_ast.BinaryOperators.DIVIDE:
            if isinstance(left_type, frog_ast.ModIntType) and isinstance(
                right_type, frog_ast.ModIntType
            ):
                if not self.check_types(left_type, right_type):
                    self.print_error(
                        bin_op,
                        f"ModInt division requires matching moduli, got {left_type} and {right_type}",
                    )
                self.ast_type_map.set(bin_op, left_type)
            elif left_type == frog_ast.IntType() and right_type == frog_ast.IntType():
                self.ast_type_map.set(bin_op, frog_ast.IntType())
            elif isinstance(left_type, frog_ast.GroupElemType) and isinstance(
                right_type, frog_ast.GroupElemType
            ):
                if not self.check_types(left_type, right_type):
                    self.print_error(
                        bin_op,
                        f"GroupElem division requires matching groups, got {left_type} and {right_type}",
                    )
                self.ast_type_map.set(bin_op, left_type)
            else:
                self.print_error(
                    bin_op,
                    f"Can not use operator / with types {left_type} and {right_type}",
                )
        elif bin_op.operator == frog_ast.BinaryOperators.EXPONENTIATE:
            if isinstance(left_type, frog_ast.ModIntType) and isinstance(
                right_type, frog_ast.IntType
            ):
                self.ast_type_map.set(bin_op, left_type)
            elif isinstance(left_type, frog_ast.GroupElemType) and isinstance(
                right_type, (frog_ast.ModIntType, frog_ast.IntType)
            ):
                self.ast_type_map.set(bin_op, left_type)
            else:
                self.print_error(
                    bin_op,
                    f"Exponentiation requires ModInt or GroupElem base, got {left_type} ^ {right_type}",
                )
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
            if not _types_comparable(left_type, right_type):
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

            # For subsets, both sides just need to be set-like types;
            # the constraint is validated at instantiation time.
            # For union/setminus, the types must be compatible.
            if bin_op.operator != frog_ast.BinaryOperators.SUBSETS:
                satisfied = False
                for l_type in left_types:
                    for r_type in right_types:
                        satisfied = satisfied or self.check_types(l_type, r_type)

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
            if isinstance(right_type, frog_ast.MapType):
                if not self.check_types(right_type.key_type, left_type):
                    self.print_error(
                        bin_op,
                        f"Cannot see if {self._format_type_with_alias(left_type)} is in"
                        f" {self._format_type_with_alias(right_type)}",
                    )
            elif isinstance(right_type, frog_ast.SetType):
                if not right_type.parameterization:
                    self.print_error(
                        bin_op,
                        f"Set type for {bin_op.right_expression} must be parameterized",
                    )
                    return
                if not self.check_types(right_type.parameterization, left_type):
                    self.print_error(
                        bin_op,
                        f"Cannot see if {self._format_type_with_alias(left_type)} is in"
                        f" {self._format_type_with_alias(right_type)}",
                    )
            else:
                self.print_error(
                    bin_op,
                    f"{bin_op.right_expression} has type"
                    f" {self._format_type_with_alias(right_type)}, expected Set or Map",
                )
                return
            self.ast_type_map.set(bin_op, frog_ast.BoolType())

    def leave_integer(self, num: frog_ast.Integer) -> None:
        self.ast_type_map.set(num, frog_ast.IntType())

    def leave_boolean(self, bool_const: frog_ast.Boolean) -> None:
        self.ast_type_map.set(bool_const, frog_ast.BoolType())

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
        self.ast_type_map.set(the_tuple, frog_ast.ProductType(types))

    def leave_set(self, the_set: frog_ast.Set) -> None:
        if not the_set.elements:
            self.print_error(
                the_set,
                "Empty set literal {} is not supported;"
                " set state variables are implicitly initialized to empty",
            )
            return
        element_types: list[frog_ast.Type] = []
        for element in the_set.elements:
            element_type = self.get_type_from_ast(element)
            if not isinstance(element_type, frog_ast.Type):
                self.print_error(
                    the_set,
                    f"{element} should evaluate to a simple type,"
                    f" received {element_type}",
                )
                return
            element_types.append(element_type)
        first_type = element_types[0]
        for i, etype in enumerate(element_types[1:], start=1):
            if not self.check_types(first_type, etype):
                self.print_error(
                    the_set,
                    f"Set element {the_set.elements[i]} has type {etype},"
                    f" expected {first_type}",
                )
                return
        self.ast_type_map.set(the_set, frog_ast.SetType(first_type))

    def leave_field(self, field: frog_ast.Field) -> None:
        super().leave_field(field)
        if field.value:
            the_type = self.get_type_from_ast(field.value)
            if not self.check_types(field.type, the_type):
                self.print_error(
                    field,
                    f"Field initializer has type {the_type}, expected {field.type}",
                )

    def leave_field_access(self, field_acess: frog_ast.FieldAccess) -> None:
        object_type = self.get_type_from_ast(field_acess.the_object)
        if isinstance(object_type, frog_ast.FunctionType):
            if field_acess.name == "domain":
                self.ast_type_map.set(
                    field_acess, frog_ast.SetType(object_type.domain_type)
                )
            else:
                self.print_error(
                    field_acess,
                    f"Function has no field '{field_acess.name}'"
                    " (only 'domain' is available)",
                )
            return
        if isinstance(object_type, frog_ast.GroupType):
            if field_acess.name in ("generator", "identity"):
                self.ast_type_map.set(
                    field_acess,
                    frog_ast.GroupElemType(field_acess.the_object),
                )
            elif field_acess.name == "order":
                self.ast_type_map.set(field_acess, frog_ast.IntType())
            else:
                self.print_error(
                    field_acess,
                    f"Group has no field '{field_acess.name}'"
                    " (only 'generator', 'order', and 'identity' are available)",
                )
            return
        if isinstance(object_type, frog_ast.MapType):
            if field_acess.name == "keys":
                self.ast_type_map.set(
                    field_acess, frog_ast.SetType(object_type.key_type)
                )
            elif field_acess.name == "values":
                self.ast_type_map.set(
                    field_acess, frog_ast.SetType(object_type.value_type)
                )
            elif field_acess.name == "entries":
                self.ast_type_map.set(
                    field_acess,
                    frog_ast.SetType(
                        frog_ast.ProductType(
                            [object_type.key_type, object_type.value_type]
                        )
                    ),
                )
            else:
                self.print_error(
                    field_acess,
                    f"Map has no field '{field_acess.name}'"
                    " (only 'keys', 'values', and 'entries' are available)",
                )
            return
        if not isinstance(object_type, visitors.InstantiableType):
            self.print_error(
                field_acess,
                f"Cannot access field '{field_acess.name}' on type {self._format_type_with_alias(object_type)}",
            )
            return
        member = object_type.members[field_acess.name]  # type: ignore[index]
        # Qualify method signature Int variable references with the object name
        # so that e.g. Variable("lambda") becomes FieldAccess(Variable("G"), "lambda")
        # to distinguish the primitive's internal names from the scheme's local names.
        if isinstance(member, frog_ast.MethodSignature) and isinstance(
            field_acess.the_object, frog_ast.Variable
        ):
            int_fields = {
                k
                for k, v in object_type.members.items()
                if not isinstance(v, frog_ast.MethodSignature)
                and isinstance(v, frog_ast.IntType)
            }
            if int_fields:
                qualify_aliases: dict[str, frog_ast.ASTNode] = {
                    fname: frog_ast.FieldAccess(
                        frog_ast.Variable(field_acess.the_object.name), fname
                    )
                    for fname in int_fields
                }
                member = _substitute_field_aliases(member, qualify_aliases)
        self.ast_type_map.set(field_acess, member)  # type: ignore[arg-type]

    def leave_binary_num(self, binary_num: frog_ast.BinaryNum) -> None:
        self.ast_type_map.set(
            binary_num, frog_ast.BitStringType(frog_ast.Integer(binary_num.length))
        )

    def leave_bit_string_literal(
        self, bit_string_literal: frog_ast.BitStringLiteral
    ) -> None:
        self.ast_type_map.set(
            bit_string_literal, frog_ast.BitStringType(bit_string_literal.length)
        )

    def leave_assignment(self, assignment: frog_ast.Assignment) -> None:
        super().leave_assignment(assignment)
        expected_type = (
            assignment.the_type
            if assignment.the_type is not None
            else self.get_type_from_ast(assignment.var)
        )
        found_type = self.get_type_from_ast(assignment.value)
        if not self.check_types(expected_type, found_type):
            self.print_error(
                assignment,
                f"{_truncate_expr(assignment.value)} has type {found_type}, expected {expected_type}",
            )

    def leave_sample(self, sample: frog_ast.Sample) -> None:
        super().leave_sample(sample)
        if not isinstance(sample.sampled_from, frog_ast.Type):
            self.print_error(
                sample,
                "Right-hand side of '<-' must be a type (for random sampling);"
                " use '=' for assignment from expressions",
            )
            return
        expected_type = (
            sample.the_type
            if sample.the_type is not None
            else self.get_type_from_ast(sample.var)
        )
        found_type = self.get_type_from_ast(sample.sampled_from)
        if not self.check_types(expected_type, found_type):
            self.print_error(
                sample,
                f"{_truncate_expr(sample.sampled_from)} has type {found_type}, expected {expected_type}",
            )

    def leave_unique_sample(self, unique_sample: frog_ast.UniqueSample) -> None:
        super().leave_unique_sample(unique_sample)
        # Check that unique_set has type Set<D> and sampled_from has type D
        set_type = self.get_type_from_ast(unique_sample.unique_set)
        if not isinstance(set_type, frog_ast.SetType):
            self.print_error(
                unique_sample,
                f"Unique sample set must be a Set type, got {set_type}",
            )
            return
        if set_type.parameterization is None:
            self.print_error(
                unique_sample,
                "Unique sample set must be a parameterized Set<D>",
            )
            return
        if not self.check_types(set_type.parameterization, unique_sample.sampled_from):
            self.print_error(
                unique_sample,
                f"Set element type {set_type.parameterization} does not match"
                f" sampled type {unique_sample.sampled_from}",
            )
        expected_type = (
            unique_sample.the_type
            if unique_sample.the_type is not None
            else self.get_type_from_ast(unique_sample.var)
        )
        if not self.check_types(expected_type, unique_sample.sampled_from):
            self.print_error(
                unique_sample,
                f"Declared type {expected_type} does not match"
                f" sampled type {unique_sample.sampled_from}",
            )

    def leave_parameterized_game(
        self, parameterized_game: frog_ast.ParameterizedGame
    ) -> None:
        definition = self.import_namespace[parameterized_game.name]

        if isinstance(definition, frog_ast.GameFile):
            # Type-check instantiation of both games in the pair
            for game in definition.games:
                self._check_instantiation(
                    parameterized_game,
                    game,
                    parameterized_game.args,
                    self._get_file_name_from_instantiable(parameterized_game.name),
                )
            # Set type from first game for field access (e.g., G(E).count)
            self.ast_type_map.set(
                parameterized_game,
                self.instantiate_and_get_type(
                    definition.games[0],
                    parameterized_game.args,
                    parameterized_game.name,
                ),
            )
        elif isinstance(definition, frog_ast.Game):
            # Pass the full variable_type_map_stack so induction variables
            # (substituted into the body) are in scope for the inner checker.
            self._check_instantiation(
                parameterized_game,
                definition,
                parameterized_game.args,
                self._get_file_name_from_instantiable(parameterized_game.name),
                [dict(d) for d in self.variable_type_map_stack],
            )
            self.ast_type_map.set(
                parameterized_game,
                self.instantiate_and_get_type(
                    definition,
                    parameterized_game.args,
                    parameterized_game.name,
                ),
            )
        else:
            print_error(parameterized_game, f"{parameterized_game} is not a Game")

    def leave_concrete_game(self, concrete_game: frog_ast.ConcreteGame) -> None:
        definition = self.import_namespace.get(concrete_game.game.name)
        if not isinstance(definition, frog_ast.GameFile):
            return
        # Find the game matching the concrete name (e.g., "Left", "Real")
        target_game = None
        for game in definition.games:
            if game.name == concrete_game.which:
                target_game = game
                break
        if target_game is None:
            return
        instantiated = proof_engine.instantiate(
            target_game,
            concrete_game.game.args,
            self.instantiation_namespace,
        )
        self.ast_type_map.set(
            concrete_game,
            get_type_from_instantiable(concrete_game.which, instantiated),
        )

    def _check_instantiation(
        self,
        location: frog_ast.ASTNode,
        scheme: frog_ast.Instantiable,
        args: list[frog_ast.Expression],
        file_name: str,
        variable_type_map_stack: VariableTypeMapStackType = None,
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

        # Build parameter bindings sequentially so that later parameters
        # (e.g., Function<D, R>) can be resolved using earlier ones
        # (e.g., Set D = GroupElem<G>).
        param_bindings: dict[str, frog_ast.Expression] = {}
        for index, param in enumerate(scheme.parameters):
            # Resolve the expected type using bindings accumulated so far
            expected_type = param.type
            if param_bindings:
                old_ns = self.instantiation_namespace
                self.instantiation_namespace = {**old_ns, **param_bindings}
                resolved = self._resolve_type_alias(expected_type)
                self.instantiation_namespace = old_ns
                if isinstance(resolved, frog_ast.Type):
                    expected_type = resolved
            if not self.check_types(expected_type, arg_types[index]):
                self.print_error(
                    location,
                    f"Argument {args[index]} has type {arg_types[index]},"
                    f" expected {expected_type}"
                    f" (parameter '{param.name}' of {scheme.name})",
                )
            # Record binding for subsequent parameters
            arg_t = arg_types[index]
            if isinstance(arg_t, frog_ast.Type):
                param_bindings[param.name] = arg_t  # type: ignore[assignment]

        # Check cache to avoid redundant instantiation and type-checking
        cache_key = (scheme.name, tuple(str(a) for a in args))
        cached = self._instantiation_cache.get(cache_key)
        if cached is not None:
            # Re-propagate subsets constraints from the cached result
            subsets_pairs = _extract_subsets_pairs(cached)
            for pair in subsets_pairs:
                if pair not in self.subsets_pairs:
                    self.subsets_pairs.append(pair)
            return cached

        # Build a combined namespace so that scheme/primitive FuncCall args
        # (e.g. UG(K, NG, H, G)) can be expanded to their field types during
        # instantiation. Scheme/primitive definitions live in import_namespace
        # but not in instantiation_namespace.
        combined_ns: frog_ast.Namespace = {
            **self.instantiation_namespace,
            **{
                name: val
                for name, val in self.import_namespace.items()
                if isinstance(val, (frog_ast.Scheme, frog_ast.Primitive))
            },
        }

        instantiated_scheme = proof_engine.instantiate(scheme, args, combined_ns)

        # Extract subsets constraints from requires clauses
        subsets_pairs = _extract_subsets_pairs(instantiated_scheme)
        # Propagate to parent visitor so reduction bodies can use them
        self.subsets_pairs.extend(subsets_pairs)

        stack = (
            variable_type_map_stack
            if variable_type_map_stack is not None
            else [dict(self.variable_type_map_stack[0])]
        )
        CheckTypeVisitor(
            self.import_namespace,
            file_name,
            self.file_name_mapping,
            stack,
            dict(combined_ns),
            self.subsets_pairs,
        ).visit(instantiated_scheme)

        self._instantiation_cache[cache_key] = instantiated_scheme
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
            definition = self.import_namespace[func_call.func.name]
            if isinstance(definition, frog_ast.GameFile):
                # GameFile: instantiate and get type from first game
                instantiated = proof_engine.instantiate(
                    definition.games[0],
                    func_call.args,
                    self.instantiation_namespace,
                )
                self.ast_type_map.set(
                    func_call,
                    get_type_from_instantiable(func_call.func.name, instantiated),
                )
            elif isinstance(definition, frog_ast.Game):
                # Game (including Reduction helpers)
                instantiated = proof_engine.instantiate(
                    definition,
                    func_call.args,
                    self.instantiation_namespace,
                )
                self.ast_type_map.set(
                    func_call,
                    get_type_from_instantiable(func_call.func.name, instantiated),
                )
            elif isinstance(definition, (frog_ast.Scheme, frog_ast.Primitive)):
                instantiated_scheme = self._check_instantiation(
                    func_call,
                    definition,
                    func_call.args,
                    self._get_file_name_from_instantiable(func_call.func.name),
                )
                self.ast_type_map.set(
                    func_call,
                    get_type_from_instantiable(
                        func_call.func.name, instantiated_scheme
                    ),
                )
            else:
                self.print_error(
                    func_call,
                    "Should be a scheme, primitive, or game",
                )
        else:
            func_call_type = self.get_type_from_ast(func_call.func)
            if isinstance(func_call_type, frog_ast.FunctionType):
                # Resolve aliases in domain/range (e.g., Set parameters
                # used as type arguments: Function<D, R>)
                resolved_rf = self._resolve_type_alias(func_call_type)
                if isinstance(resolved_rf, frog_ast.FunctionType):
                    func_call_type = resolved_rf
                if len(func_call.args) != 1:
                    self.print_error(
                        func_call, "Function call requires exactly 1 argument"
                    )
                    return
                arg_type = self.get_type_from_ast(func_call.args[0])
                if not self.check_types(func_call_type.domain_type, arg_type):
                    self.print_error(
                        func_call,
                        f"{func_call.args[0]} has type {self._format_type_with_alias(arg_type)},"
                        f" expected {func_call_type.domain_type}",
                    )
                self.ast_type_map.set(func_call, func_call_type.range_type)
                return
            func_call_signature = func_call_type
            if not isinstance(func_call_signature, frog_ast.MethodSignature):
                self.print_error(
                    func_call,
                    f"Cannot resolve method signature for '{func_call.func}'",
                )
                return
            if len(func_call_signature.parameters) != len(func_call.args):
                self.print_error(
                    func_call,
                    f"Expected {len(func_call_signature.parameters)} argument(s),"
                    f" got {len(func_call.args)}",
                )
            arg_types = [self.get_type_from_ast(arg) for arg in func_call.args]

            for index, arg_type in enumerate(arg_types):
                declared_type = func_call_signature.parameters[index].type
                if not self.check_types(declared_type, arg_type):
                    param_name = func_call_signature.parameters[index].name
                    self.print_error(
                        func_call,
                        f"{func_call.args[index]} has type"
                        f" {self._format_type_with_alias(arg_type)},"
                        f" expected {declared_type}"
                        f" (parameter '{param_name}'"
                        f" of {func_call_signature.name})",
                    )
            self.ast_type_map.set(func_call, func_call_signature.return_type)


class _FieldAccessFlattener(visitors.Transformer):
    """Replace FieldAccess(Variable("G"), "lambda") with Variable("G.lambda")."""

    def transform_field_access(
        self, field_access: frog_ast.FieldAccess
    ) -> frog_ast.ASTNode:
        if isinstance(field_access.the_object, frog_ast.Variable):
            result = frog_ast.Variable(
                f"{field_access.the_object.name}.{field_access.name}"
            )
            result.line_num = field_access.line_num
            result.column_num = field_access.column_num
            return result
        return field_access


def get_sympy_expression(the_type: frog_ast.ASTNode) -> Symbol | int | None:
    """Convert an AST numeric expression to a SymPy expression.

    Handles Variable, FieldAccess (flattened to dotted names), Integer,
    BinaryOperation (+, -, *, /), and UnaryOperation (-) without copying
    or mutating the input tree.
    """
    return _ast_to_sympy(the_type)


def _ast_to_sympy(  # pylint: disable=too-many-return-statements
    node: frog_ast.ASTNode,
) -> Symbol | int | None:
    """Read-only recursive extraction of a SymPy expression from an AST node."""
    if isinstance(node, frog_ast.Integer):
        return node.num
    if isinstance(node, frog_ast.Variable):
        return Symbol(node.name)
    if isinstance(node, frog_ast.FieldAccess):
        if isinstance(node.the_object, frog_ast.Variable):
            return Symbol(f"{node.the_object.name}.{node.name}")
        return None
    if isinstance(node, frog_ast.BinaryOperation):
        left = _ast_to_sympy(node.left_expression)
        right = _ast_to_sympy(node.right_expression)
        if left is None or right is None:
            return None
        if node.operator == frog_ast.BinaryOperators.ADD:
            return left + right
        if node.operator == frog_ast.BinaryOperators.SUBTRACT:
            return left - right
        if node.operator == frog_ast.BinaryOperators.MULTIPLY:
            return left * right
        if node.operator == frog_ast.BinaryOperators.DIVIDE:
            return Rational(left, right)
        return None
    if isinstance(node, frog_ast.UnaryOperation):
        if node.operator == frog_ast.UnaryOperators.MINUS:
            val = _ast_to_sympy(node.expression)
            if val is not None:
                return -val
        return None
    return None


def _check_scheme_against_primitive(
    scheme: frog_ast.Scheme, primitive: frog_ast.Primitive
) -> list[str]:
    """Check that a scheme correctly implements its primitive's interface.

    Returns a list of human-readable mismatch messages (empty if consistent).
    Stricter than has_matching_methods/has_matching_fields:

    - method modifiers (deterministic, injective) must match exactly,
    - return and parameter types are compared with strict_optional=True
      so a scheme returning T cannot satisfy a primitive declaring T?,
    - field declared types must match.

    Initialize/Finalize methods are skipped (mirroring has_matching_methods).
    """
    errors: list[str] = []

    # Field checks: every primitive field must have a same-name scheme field
    # whose declared type matches.
    scheme_fields_by_name = {field.name: field for field in scheme.fields}
    for prim_field in primitive.fields:
        scheme_field = scheme_fields_by_name.get(prim_field.name)
        if scheme_field is None:
            errors.append(
                f"missing field '{prim_field.name}' required by primitive "
                f"{primitive.name}"
            )
            continue
        if not compare_types(prim_field.type, scheme_field.type):
            errors.append(
                f"field '{prim_field.name}' has type {scheme_field.type} but "
                f"primitive {primitive.name} declares type {prim_field.type}"
            )

    # Method checks: every primitive method (besides Initialize/Finalize) must
    # have a same-name scheme method with matching modifiers and types.
    scheme_methods_by_name = {
        method.signature.name: method.signature for method in scheme.methods
    }
    for prim_method in primitive.methods:
        if prim_method.name in ("Initialize", "Finalize"):
            continue
        scheme_sig = scheme_methods_by_name.get(prim_method.name)
        if scheme_sig is None:
            errors.append(
                f"missing method '{prim_method.name}' required by primitive "
                f"{primitive.name}"
            )
            continue
        if prim_method.deterministic and not scheme_sig.deterministic:
            errors.append(
                f"method '{prim_method.name}' is missing the 'deterministic' "
                f"modifier required by primitive {primitive.name}"
            )
        if scheme_sig.deterministic and not prim_method.deterministic:
            errors.append(
                f"method '{prim_method.name}' has a 'deterministic' modifier "
                f"not declared by primitive {primitive.name}"
            )
        if prim_method.injective and not scheme_sig.injective:
            errors.append(
                f"method '{prim_method.name}' is missing the 'injective' "
                f"modifier required by primitive {primitive.name}"
            )
        if scheme_sig.injective and not prim_method.injective:
            errors.append(
                f"method '{prim_method.name}' has an 'injective' modifier "
                f"not declared by primitive {primitive.name}"
            )
        if not compare_types(
            prim_method.return_type, scheme_sig.return_type, strict_optional=True
        ):
            errors.append(
                f"method '{prim_method.name}' return type {scheme_sig.return_type} "
                f"does not match primitive {primitive.name} return type "
                f"{prim_method.return_type}"
            )
        if len(prim_method.parameters) != len(scheme_sig.parameters):
            errors.append(
                f"method '{prim_method.name}' has {len(scheme_sig.parameters)} "
                f"parameter(s) but primitive {primitive.name} declares "
                f"{len(prim_method.parameters)}"
            )
            continue
        for index, prim_param in enumerate(prim_method.parameters):
            scheme_param = scheme_sig.parameters[index]
            if not compare_types(
                prim_param.type, scheme_param.type, strict_optional=True
            ):
                errors.append(
                    f"method '{prim_method.name}' parameter {index} has type "
                    f"{scheme_param.type} but primitive {primitive.name} declares "
                    f"type {prim_param.type}"
                )

    return errors


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


def has_matching_fields(
    needed_primitive: frog_ast.Primitive, scheme: frog_ast.Scheme
) -> bool:
    """Check that every field in the primitive has a corresponding field in the scheme."""
    scheme_field_names = {field.name for field in scheme.fields}
    for field in needed_primitive.fields:
        if field.name not in scheme_field_names:
            return False
    return True


def compare_types(
    declared_type: PossibleType,
    value_type: PossibleType,
    subsets_pairs: Optional[list[tuple[PossibleType, PossibleType]]] = None,
    sympy_subs: Optional[dict[Symbol, Symbol | int]] = None,
    strict_optional: bool = False,
) -> bool:
    if declared_type == value_type:
        return True

    # Check if types are related via requires...subsets constraints.
    # Treated as bidirectional type compatibility since the scheme author
    # asserts the sets are interchangeable in context.
    if subsets_pairs:
        for sub_type, super_type in subsets_pairs:
            if (value_type == sub_type and declared_type == super_type) or (
                value_type == super_type and declared_type == sub_type
            ):
                return True

    if declared_type == frog_ast.SetType() and isinstance(value_type, frog_ast.Type):
        return True

    if isinstance(declared_type, frog_ast.OptionalType) and isinstance(
        value_type, frog_ast.NoneExpression
    ):
        return True

    if isinstance(declared_type, frog_ast.OptionalType):
        # T? can hold T (relaxation disabled when strict_optional is True)
        if not strict_optional and compare_types(
            declared_type.the_type, value_type, subsets_pairs, sympy_subs
        ):
            return True
        # T? can hold S? if T can hold S
        if isinstance(value_type, frog_ast.OptionalType) and compare_types(
            declared_type.the_type,
            value_type.the_type,
            subsets_pairs,
            sympy_subs,
            strict_optional,
        ):
            return True

    # Normalize Tuple-of-types to ProductType for comparison.
    # Set field aliases like Set Key = [A, B] produce Tuple nodes that may
    # appear in type positions via InstantiationTransformer substitution.
    if isinstance(declared_type, frog_ast.Tuple) and all(
        isinstance(v, frog_ast.Type) for v in declared_type.values
    ):
        declared_type = frog_ast.ProductType(
            [v for v in declared_type.values if isinstance(v, frog_ast.Type)]
        )
    if isinstance(value_type, frog_ast.Tuple) and all(
        isinstance(v, frog_ast.Type) for v in value_type.values
    ):
        value_type = frog_ast.ProductType(
            [v for v in value_type.values if isinstance(v, frog_ast.Type)]
        )

    if isinstance(declared_type, frog_ast.ProductType) and isinstance(
        value_type, frog_ast.ProductType
    ):
        return len(declared_type.types) == len(value_type.types) and all(
            compare_types(d, v, subsets_pairs, sympy_subs)
            for d, v in zip(declared_type.types, value_type.types)
        )

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
            declared_type_expression = get_sympy_expression(
                declared_type.parameterization
            )
            value_type_expression = get_sympy_expression(value_type.parameterization)
            # get_sympy_expression returns a raw Python int for Integer
            # literals; wrap so both sides expose .subs() for the
            # substitution loop below.
            if isinstance(declared_type_expression, int):
                declared_type_expression = Integer(declared_type_expression)
            if isinstance(value_type_expression, int):
                value_type_expression = Integer(value_type_expression)
            if sympy_subs and declared_type_expression != value_type_expression:
                # Apply Int field definitions and requires equalities
                # iteratively until fixed point for transitive chains
                for _ in range(10):
                    prev_d = declared_type_expression
                    prev_v = value_type_expression
                    if declared_type_expression is not None:
                        declared_type_expression = declared_type_expression.subs(  # type: ignore[union-attr]
                            sympy_subs
                        )
                    if value_type_expression is not None:
                        value_type_expression = value_type_expression.subs(  # type: ignore[union-attr]
                            sympy_subs
                        )
                    if (
                        declared_type_expression == prev_d
                        and value_type_expression == prev_v
                    ):
                        break
            return bool(declared_type_expression == value_type_expression)
        return True

    if isinstance(declared_type, frog_ast.ModIntType) and isinstance(
        value_type, frog_ast.ModIntType
    ):
        declared_modulus = get_sympy_expression(declared_type.modulus)
        value_modulus = get_sympy_expression(value_type.modulus)
        if declared_modulus is None or value_modulus is None:
            return declared_type == value_type
        bool_value = declared_modulus == value_modulus
        return bool_value

    if isinstance(declared_type, frog_ast.ModIntType) and isinstance(
        value_type, frog_ast.IntType
    ):
        return True

    if isinstance(declared_type, frog_ast.GroupElemType) and isinstance(
        value_type, frog_ast.GroupElemType
    ):
        return str(declared_type.group) == str(value_type.group)

    if isinstance(declared_type, frog_ast.ArrayType) and isinstance(
        value_type, frog_ast.ArrayType
    ):
        if not compare_types(
            declared_type.element_type,
            value_type.element_type,
            subsets_pairs,
            sympy_subs,
        ):
            return False
        d_count = get_sympy_expression(declared_type.count)
        v_count = get_sympy_expression(value_type.count)
        if d_count is None or v_count is None:
            return declared_type.count == value_type.count
        # Wrap raw ints so both sides expose .subs() below.
        if isinstance(d_count, int):
            d_count = Integer(d_count)
        if isinstance(v_count, int):
            v_count = Integer(v_count)
        if sympy_subs and d_count != v_count:
            for _ in range(10):
                prev_d, prev_v = d_count, v_count
                d_count = d_count.subs(sympy_subs)  # type: ignore[union-attr]
                v_count = v_count.subs(sympy_subs)  # type: ignore[union-attr]
                if d_count == prev_d and v_count == prev_v:
                    break
        return bool(d_count == v_count)

    return False


def _substitute_type_node(
    node: frog_ast.ASTNode, aliases: dict[str, frog_ast.ASTNode]
) -> frog_ast.ASTNode:
    """Recursively substitute Variable nodes using field aliases."""
    if isinstance(node, frog_ast.Variable) and node.name in aliases:
        return copy.deepcopy(aliases[node.name])
    if isinstance(node, frog_ast.BitStringType) and node.parameterization is not None:
        new_param = _substitute_type_node(node.parameterization, aliases)
        if isinstance(new_param, frog_ast.Expression):
            result = frog_ast.BitStringType(new_param)
            result.line_num = node.line_num
            result.column_num = node.column_num
            return result
    if isinstance(node, frog_ast.OptionalType):
        new_inner = _substitute_type_node(node.the_type, aliases)
        if isinstance(new_inner, frog_ast.Type):
            result_opt = frog_ast.OptionalType(new_inner)
            result_opt.line_num = node.line_num
            result_opt.column_num = node.column_num
            return result_opt
    if isinstance(node, frog_ast.ProductType):
        new_types: list[frog_ast.Type] = []
        for sub in node.types:
            substituted = _substitute_type_node(sub, aliases)
            if isinstance(substituted, frog_ast.Type):
                new_types.append(substituted)
        result_prod = frog_ast.ProductType(new_types)
        result_prod.line_num = node.line_num
        result_prod.column_num = node.column_num
        return result_prod
    if isinstance(node, frog_ast.BinaryOperation):
        new_left = _substitute_type_node(node.left_expression, aliases)
        new_right = _substitute_type_node(node.right_expression, aliases)
        if isinstance(new_left, frog_ast.Expression) and isinstance(
            new_right, frog_ast.Expression
        ):
            result_bin = frog_ast.BinaryOperation(node.operator, new_left, new_right)
            result_bin.line_num = node.line_num
            result_bin.column_num = node.column_num
            return result_bin
    if isinstance(node, frog_ast.UnaryOperation):
        new_operand = _substitute_type_node(node.expression, aliases)
        if isinstance(new_operand, frog_ast.Expression):
            result_un = frog_ast.UnaryOperation(node.operator, new_operand)
            result_un.line_num = node.line_num
            result_un.column_num = node.column_num
            return result_un
    if isinstance(node, frog_ast.ModIntType):
        new_modulus = _substitute_type_node(node.modulus, aliases)
        if isinstance(new_modulus, frog_ast.Expression):
            result_mi = frog_ast.ModIntType(new_modulus)
            result_mi.line_num = node.line_num
            result_mi.column_num = node.column_num
            return result_mi
    if isinstance(node, frog_ast.GroupElemType):
        new_group = _substitute_type_node(node.group, aliases)
        if isinstance(new_group, frog_ast.Expression):
            result_ge = frog_ast.GroupElemType(new_group)
            result_ge.line_num = node.line_num
            result_ge.column_num = node.column_num
            return result_ge
    if isinstance(node, frog_ast.FieldAccess):
        new_obj = _substitute_type_node(node.the_object, aliases)
        if isinstance(new_obj, frog_ast.Expression):
            result_fa = frog_ast.FieldAccess(new_obj, node.name)
            result_fa.line_num = node.line_num
            result_fa.column_num = node.column_num
            return result_fa
    return node


def _substitute_field_aliases(
    sig: frog_ast.MethodSignature, aliases: dict[str, frog_ast.ASTNode]
) -> frog_ast.MethodSignature:
    """Return a copy of a MethodSignature with field aliases substituted."""
    new_params: list[frog_ast.Parameter] = []
    for param in sig.parameters:
        new_type: frog_ast.Type = param.type
        substituted = _substitute_type_node(param.type, aliases)
        if isinstance(substituted, frog_ast.Type):
            new_type = substituted
        new_param = frog_ast.Parameter(new_type, param.name)
        new_param.line_num = param.line_num
        new_param.column_num = param.column_num
        new_params.append(new_param)
    new_return: frog_ast.Type = sig.return_type
    substituted_ret = _substitute_type_node(sig.return_type, aliases)
    if isinstance(substituted_ret, frog_ast.Type):
        new_return = substituted_ret
    new_sig = frog_ast.MethodSignature(sig.name, new_return, new_params)
    new_sig.line_num = sig.line_num
    new_sig.column_num = sig.column_num
    return new_sig


def get_type_from_instantiable(
    name: str, instantiable: frog_ast.Instantiable, just_methods: bool = False
) -> visitors.InstantiableType:
    type_dict: dict[str, frog_ast.ASTNode] = {}
    if not just_methods:
        for field in instantiable.fields:
            to_set_to: frog_ast.ASTNode | None = (
                field.type if field.type != frog_ast.SetType() else field.value
            )
            if to_set_to is None:
                print_error(instantiable, "Set fields must have corresponding value")
                sys.exit(1)
            # Convert Tuple of types to ProductType for Set field aliases
            if (
                isinstance(to_set_to, frog_ast.Tuple)
                and to_set_to.values
                and all(isinstance(v, frog_ast.Type) for v in to_set_to.values)
            ):
                to_set_to = frog_ast.ProductType(
                    [v for v in to_set_to.values if isinstance(v, frog_ast.Type)]
                )
            type_dict[field.name] = to_set_to
    # Build substitution map from Set field aliases (e.g., "Key" -> Variable("KeySpace"))
    field_aliases: dict[str, frog_ast.ASTNode] = {}
    if not just_methods:
        for field in instantiable.fields:
            if field.type == frog_ast.SetType() and field.value is not None:
                field_aliases[field.name] = type_dict[field.name]

    for method in instantiable.methods:
        if isinstance(method, frog_ast.MethodSignature):
            type_dict[method.name] = method
        else:
            type_dict[method.signature.name] = method.signature

    # Apply field alias substitution to method signatures so that e.g.
    # a method expecting Variable("Key") becomes Variable("KeySpace")
    if field_aliases:
        for key, value in type_dict.items():
            if isinstance(value, frog_ast.MethodSignature):
                type_dict[key] = _substitute_field_aliases(value, field_aliases)

    superclass = (
        instantiable.primitive_name if isinstance(instantiable, frog_ast.Scheme) else ""
    )

    return visitors.InstantiableType(name, type_dict, superclass)
