import functools
import sys
from . import frog_ast
from . import visitors


def check_well_formed(root: frog_ast.Root) -> None:
    if isinstance(root, frog_ast.Primitive):
        check_primitive_well_formed(root)


def check_primitive_well_formed(primitive: frog_ast.Primitive) -> None:
    for param in primitive.parameters:

        def is_user_defined(node: frog_ast.ASTNode) -> bool:
            return isinstance(node, (frog_ast.Variable, frog_ast.FieldAccess))

        the_type = visitors.SearchVisitor(is_user_defined).visit(param.type)
        if the_type is not None:
            print_error(
                the_type,
                f"In {', '.join(str(param) for param in primitive.parameters)}, '{the_type}' is not a defined type",
            )
    valid_names = [param.name for param in primitive.parameters]
    for field in primitive.fields + primitive.methods:

        def is_invalid_name(valid_names: list[str], node: frog_ast.ASTNode) -> bool:
            return isinstance(node, frog_ast.Variable) and node.name not in valid_names

        found_invalid = visitors.SearchVisitor(
            functools.partial(is_invalid_name, valid_names)
        ).visit(field)
        if found_invalid is not None:
            print_error(
                field, f"In {field} '{found_invalid}' is not a defined variable"
            )
        valid_names.append(field.name)

    param_names = [param.name for param in primitive.parameters]
    if len(param_names) != len(set(param_names)):
        print_error(primitive.parameters[0], "Duplicated parameter name")
    field_names = [field.name for field in primitive.fields]
    if len(field_names) != len(set(field_names)):
        print_error(primitive.fields[0], "Duplicated field name")
    method_names = [method.name for method in primitive.methods]
    if len(method_names) != len(set(method_names)):
        print_error(primitive.methods[0], "Duplicated method name")

    for method in primitive.methods:
        method_param_names = [param.name for param in method.parameters]
        if len(method_param_names) != len(set(method_param_names)):
            print_error(method, "Duplicated parameter name")


def print_error(location: frog_ast.ASTNode, message: str):
    print(f"Line {location.line_num}, column: {location.column_num}", file=sys.stderr)
    print(message, file=sys.stderr)
    sys.exit(1)
