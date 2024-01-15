import functools
import sys
from typing import Optional
from . import frog_ast
from . import frog_parser
from . import visitors


def check_well_formed(root: frog_ast.Root) -> None:
    import_namespace = {}
    if isinstance(root, frog_ast.Primitive):
        check_primitive_well_formed(root, import_namespace)
    if isinstance(root, frog_ast.Scheme):
        for imp in root.imports:
            parsed_file = frog_parser.parse_file(imp.filename)
            name = imp.rename if imp.rename else parsed_file.get_export_name()
            import_namespace[name] = parsed_file
        check_primitive_well_formed(root, import_namespace)

    TypeCheckVisitor(import_namespace, root).visit(root)


def check_primitive_well_formed(
    primitive: frog_ast.Primitive | frog_ast.Scheme, import_namespace
) -> None:
    for param in primitive.parameters:

        def is_user_defined(node: frog_ast.ASTNode) -> bool:
            return isinstance(node, frog_ast.FieldAccess) or (
                isinstance(node, frog_ast.Variable)
                and node.name not in import_namespace
            )

        the_type = visitors.SearchVisitor(is_user_defined).visit(param.type)
        if the_type is not None:
            print_error(
                the_type,
                f"In {', '.join(str(param) for param in primitive.parameters)}, '{the_type}' is not a defined type",
            )
    valid_names = [param.name for param in primitive.parameters]

    method_signatures = (
        primitive.methods
        if isinstance(primitive, frog_ast.Primitive)
        else [method.signature for method in primitive.methods]
    )
    for field in primitive.fields + method_signatures:

        def is_invalid_name(valid_names: list[str], node: frog_ast.ASTNode) -> bool:
            return isinstance(node, frog_ast.Variable) and node.name not in valid_names

        found_invalid = visitors.SearchVisitor(
            functools.partial(is_invalid_name, valid_names)
        ).visit(field)
        if found_invalid is not None:
            print_error(
                field, f"In {field} '{found_invalid}' is not a defined variable"
            )
        if isinstance(field, frog_ast.Field):
            valid_names.append(field.name)

    param_names = [param.name for param in primitive.parameters]
    if len(param_names) != len(set(param_names)):
        print_error(primitive.parameters[0], "Duplicated parameter name")
    field_names = [field.name for field in primitive.fields]
    if len(field_names) != len(set(field_names)):
        print_error(primitive.fields[0], "Duplicated field name")

    method_names = [method.name for method in method_signatures]
    if len(method_names) != len(set(method_names)):
        print_error(primitive.methods[0], "Duplicated method name")

    for method in method_signatures:
        method_param_names = [param.name for param in method.parameters]
        if len(method_param_names) != len(set(method_param_names)):
            print_error(method, "Duplicated parameter name")


def print_error(location: frog_ast.ASTNode, message: str):
    print(f"Line {location.line_num}, column: {location.column_num}", file=sys.stderr)
    print(message, file=sys.stderr)
    sys.exit(2)


class TypeCheckVisitor(visitors.Visitor[None]):
    def __init__(self, import_namespace, root):
        self.variable_type_map_stack = [{}]
        self.type_stack = []
        self.import_namespace = import_namespace
        self.method_return_type = None
        self.root = root

    def result(self) -> None:
        return None

    def visit_parameter(self, param: frog_ast.Parameter) -> None:
        self.variable_type_map_stack[0][param.name] = (
            param.type
            if not isinstance(param.type, frog_ast.Variable)
            else self.get_type(param.type.name)
        )

    def leave_tuple(self, the_tuple: frog_ast.Tuple) -> None:
        list_of_types = []
        for _ in the_tuple.values:
            list_of_types.append(self.type_stack.pop())

        tuple_type = list_of_types[0]
        for next_type in list_of_types[1:]:
            tuple_type = frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.MULTIPLY, next_type, tuple_type
            )
        self.type_stack.append(tuple_type)

    def leave_field(self, field: frog_ast.Field) -> None:
        if isinstance(field.type, frog_ast.SetType):
            self.variable_type_map_stack[0][field.name] = field.value
        else:
            self.variable_type_map_stack[0][field.name] = field.type
        if field.value is None:
            return
        result_type = self.type_stack.pop()
        expected_type = field.type
        # TODO: Figure out what proper value of Sets is
        if result_type != expected_type and not isinstance(
            expected_type, frog_ast.SetType
        ):
            print_error(
                field,
                f"In {field} {field.value} is of type {result_type}, should be {expected_type}",
            )

    def visit_variable(self, var: frog_ast.Variable) -> None:
        to_return = None
        name = var.name
        while True:
            the_type = self.get_type(name)
            if the_type:
                to_return = the_type
            if not isinstance(the_type, frog_ast.Variable):
                break
            name = the_type.name
        if to_return:
            self.type_stack.append(to_return)
            return
        assert False, f"Variable {name} not defined"

    def leave_return_statement(
        self, return_statement: frog_ast.ReturnStatement
    ) -> None:
        expression_type = self.type_stack.pop()
        assert isinstance(self.root, frog_ast.Scheme)
        if not is_sub_type(
            self.method_return_type,
            SimplifyTypeTransformer(self.root.fields).transform(expression_type),
        ):
            print_error(
                return_statement,
                f"In '{return_statement}', {return_statement.expression} is of type {expression_type}, should be of type {self.method_return_type}",
            )

    def leave_field_access(self, field_access: frog_ast.FieldAccess) -> None:
        if not isinstance(field_access.the_object, frog_ast.Variable):
            print_error(field_access, "Nested field access is not supported")

        object_def = self.type_stack.pop()
        if not isinstance(
            object_def,
            (frog_ast.Primitive, frog_ast.Scheme),
        ):
            print_error(
                field_access,
                f"{field_access.the_object.name} is not a primitive or scheme",
            )
            return
        add_field_access_transformer = AddFieldAccessTransformer(
            field_access.the_object.name
        )
        for field in object_def.fields:
            if field.name == field_access.name:
                self.type_stack.append(
                    add_field_access_transformer.transform(field.type)
                )
                return
        for method in object_def.methods:
            signature = (
                method
                if isinstance(method, frog_ast.MethodSignature)
                else method.signature
            )
            if signature.name == field_access.name:
                self.type_stack.append(
                    add_field_access_transformer.transform(signature)
                )
                return

    def visit_scheme(self, scheme: frog_ast.Scheme) -> None:
        if scheme.primitive_name not in self.import_namespace:
            print_error(
                scheme,
                f"In Scheme {scheme.name}, {scheme.primitive_name} is not defined",
            )
        base_primitive = self.import_namespace[scheme.primitive_name]
        if not isinstance(base_primitive, frog_ast.Primitive):
            print_error(
                scheme,
                f"In Scheme {scheme.name}, {scheme.primitive_name} is not a Primitive",
            )
            return
        for field in base_primitive.fields:
            if (
                next(
                    (
                        scheme_field
                        for scheme_field in scheme.fields
                        if scheme_field.name == field.name
                        and scheme_field.type == field.type
                    ),
                    None,
                )
                is None
            ):
                print_error(
                    scheme,
                    f"{base_primitive.name} defines field '{field.name}' which {scheme.name} does not override",
                )

        def is_method_override(
            primitive_signature: frog_ast.MethodSignature,
            scheme_signature: frog_ast.MethodSignature,
        ):
            return (
                is_sub_type(
                    primitive_signature.return_type, scheme_signature.return_type
                )
                and len(primitive_signature.parameters)
                == len(scheme_signature.parameters)
                and all(
                    (
                        param1.type == param2.type
                        for [param1, param2] in zip(
                            primitive_signature.parameters, scheme_signature.parameters
                        )
                    )
                )
            )

        for method in base_primitive.methods:
            if (
                next(
                    (
                        scheme_method
                        for scheme_method in scheme.methods
                        if is_method_override(method, scheme_method.signature)
                    ),
                    None,
                )
                is None
            ):
                print_error(
                    scheme,
                    f"{base_primitive.name} defines method '{method}' which {scheme.name} does not override",
                )

    def visit_method(self, method: frog_ast.Method) -> None:
        self.variable_type_map_stack.append(
            dict(
                zip(
                    (param.name for param in method.signature.parameters),
                    (param.type for param in method.signature.parameters),
                )
            )
        )
        assert isinstance(self.root, frog_ast.Scheme)
        self.method_return_type = SimplifyTypeTransformer(self.root.fields).transform(
            method.signature.return_type
        )

    def visit_if_statement(self, if_statement: frog_ast.IfStatement) -> None:
        for condition in if_statement.conditions:
            self.visit(condition)
            expr_type = self.type_stack.pop()
            if not isinstance(expr_type, frog_ast.BoolType):
                print_error(condition, f"{condition} does not return type bool")

    def leave_method(self, _: frog_ast.Method) -> None:
        self.variable_type_map_stack.pop()

    def visit_assignment(self, assignment: frog_ast.Assignment) -> None:
        if assignment.the_type is not None:
            assert isinstance(assignment.var, frog_ast.Variable)
            self.variable_type_map_stack[-1][assignment.var.name] = assignment.the_type

    def visit_sample(self, assignment: frog_ast.Assignment) -> None:
        if assignment.the_type is not None:
            assert isinstance(assignment.var, frog_ast.Variable)
            self.variable_type_map_stack[-1][assignment.var.name] = assignment.the_type

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

    def leave_bit_string_type(self, node: frog_ast.BitStringType) -> None:
        if not node.parameterization:
            self.type_stack.append(node)
            return
        nested_type = self.type_stack.pop()
        if not isinstance(nested_type, frog_ast.IntType):
            print_error(node, f"In {node}, {nested_type} is not of type Int")
        self.type_stack.append(node)

    def leave_integer(self, _: frog_ast.Integer) -> None:
        self.type_stack.append(frog_ast.IntType())

    def leave_boolean(self, _: frog_ast.Boolean) -> None:
        self.type_stack.append(frog_ast.BoolType())

    def leave_binary_num(self, _: frog_ast.BinaryNum) -> None:
        self.type_stack.append(frog_ast.BitStringType())

    def leave_none_expression(self, _: frog_ast.NoneExpression) -> None:
        self.type_stack.append(frog_ast.NoneExpression())

    def leave_binary_operation(self, binary_op: frog_ast.BinaryOperation) -> None:
        type1 = self.type_stack.pop()
        type2 = self.type_stack.pop()

        if binary_op.operator == frog_ast.BinaryOperators.MULTIPLY:
            if (
                isinstance(binary_op.left_expression, frog_ast.Type)
                and isinstance(binary_op.right_expression, frog_ast.Type)
                and not isinstance(
                    binary_op.left_expression, (frog_ast.Variable, frog_ast.FieldAccess)
                )
                and not isinstance(
                    binary_op.right_expression,
                    (frog_ast.Variable, frog_ast.FieldAccess),
                )
            ):
                self.type_stack.append(binary_op)
                return

        if (
            binary_op.operator == frog_ast.BinaryOperators.EQUALS
            or binary_op.operator == frog_ast.BinaryOperators.NOTEQUALS
        ):
            if type1 != type2:
                print_error(
                    binary_op,
                    f"In {binary_op}, {type1} and {type2} are not the same",
                )
            self.type_stack.append(frog_ast.BoolType())
        if binary_op.operator in set(
            [
                frog_ast.BinaryOperators.ADD,
                frog_ast.BinaryOperators.MULTIPLY,
                frog_ast.BinaryOperators.SUBTRACT,
            ]
        ):
            if type1 != type2:
                print_error(
                    binary_op,
                    f"In {binary_op}, cannot perform operation on {type1} and {type2}",
                )
            self.type_stack.append(type1)
        if binary_op.operator == frog_ast.BinaryOperators.AND:
            if type1 != type2 or not isinstance(type1, frog_ast.BoolType):
                print_error(
                    binary_op,
                    f"In {binary_op}, {type1} or {type2} is not of type Bool",
                )
            self.type_stack.append(frog_ast.BoolType())

    def leave_array_access(self, array_access: frog_ast.ArrayAccess) -> None:
        index_type = self.type_stack.pop()
        array_type = self.type_stack.pop()

        if not isinstance(index_type, frog_ast.IntType):
            print_error(
                array_access,
                f"In {array_access}, {array_access.index} is not of type Int",
            )

        if isinstance(array_type, frog_ast.ArrayType):
            self.type_stack.append(array_type.element_type)
            return

        if (
            isinstance(array_type, frog_ast.BinaryOperation)
            and array_type.operator == frog_ast.BinaryOperators.MULTIPLY
        ):
            if not isinstance(array_access.index, frog_ast.Integer):
                print_error(
                    array_access,
                    f"In {array_access}, must access tuples with direct integers",
                )
            types = []

            def flatten(node: frog_ast.ASTNode):
                if not isinstance(node, frog_ast.BinaryOperation):
                    types.append(node)
                    return
                flatten(node.left_expression)
                flatten(node.right_expression)

            flatten(array_type)

            if array_access.index.num < 0 or array_access.index.num >= len(types):
                print_error(
                    array_access,
                    f"In {array_access}, {array_access.index} is out of bounds",
                )
            self.type_stack.append(types[array_access.index.num])
            return
        print_error(
            array_access,
            f"In {array_access}, {array_access.the_array} is not an indexable type",
        )

    def leave_func_call_expression(
        self, func_call: frog_ast.FuncCallExpression
    ) -> None:
        arg_types = []
        for _ in func_call.args:
            arg_types.insert(0, self.type_stack.pop())
        func_type = self.type_stack.pop()
        self.type_stack.append(func_type.return_type)

    def get_type(self, name: str) -> Optional[frog_ast.Type]:
        for the_map in reversed(self.variable_type_map_stack):
            if name in the_map:
                return the_map[name]
        if name in self.import_namespace:
            return self.import_namespace[name]

        return None


class SimplifyTypeTransformer(visitors.Transformer):
    def __init__(self, fields: list[frog_ast.Field]):
        self.fields = fields

    def transform_variable(self, var: frog_ast.Variable):
        for field in self.fields:
            if field.name == var.name:
                return field.value
        return var

    def transform_field_access(self, field_access: frog_ast.FieldAccess):
        return field_access


def is_sub_type(base_type, maybe_sub_type):
    if base_type == maybe_sub_type:
        return True
    if isinstance(base_type, frog_ast.OptionalType):
        if isinstance(maybe_sub_type, frog_ast.NoneExpression):
            return True
        return is_sub_type(base_type.the_type, maybe_sub_type)
    return False


class AddFieldAccessTransformer(visitors.Transformer):
    def __init__(self, name_of_primitive: str):
        self.name_of_primitive = name_of_primitive

    def transform_variable(self, v: frog_ast.Variable):
        return frog_ast.FieldAccess(frog_ast.Variable(self.name_of_primitive), v.name)
