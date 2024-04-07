from . import visitors, frog_ast


class LatexVisitor(visitors.Visitor[None]):
    def __init__(self) -> None:
        self.in_initialize = False
        self.in_game_parameters = False
        self.stack = []
        self.property_name = ""
        self.game_name = ""
        self.parameters = ""
        self.oracles = []

    def result(self) -> None:
        pass

    def visit_game_file(self, game_file: frog_ast.GameFile):
        self.property_name = game_file.get_export_name()

    def visit_game(self, game: frog_ast.Game):
        self.game_name = game.name
        self.in_game_parameters = True
        self.parameters = ""
        self.oracles = [
            self.get_oracle_name(method.signature.name)
            for method in game.methods
            if method.signature.name != "Initialize"
        ]

    def visit_parameter(self, parameter: frog_ast.Parameter):
        if self.parameters != "":
            self.parameters += ","
        self.parameters += parameter.name

    def leave_game(self, _: frog_ast.Game):
        self.in_game_parameters = False

    def visit_method(self, method: frog_ast.Method):
        if method.signature.name == "Initialize":
            print(
                f"\\procedureblock[linenumbering]{{{self.property_name}-{self.game_name}$^\\adv_{self.parameters}$}}{{"
            )
            self.in_initialize = True
            self.parameters = ""
        else:
            self.parameters = ""
            self.visit(method.signature)
            print(
                f"\\procedureblock[linenumbering]{{{self.get_oracle_name(method.signature.name)}({self.parameters})}}{{"
            )

    def leave_method(self, _: frog_ast.Method):
        oracle_list = ",".join(self.oracles)
        if self.in_initialize:
            print(f"\\pcreturn \\adv^{{{oracle_list}}}()")
            self.in_initialize = False
        print("}")

    def visit_variable(self, var: frog_ast.Variable):
        self.stack.append(self.convert_name(var.name))

    def visit_set(self, the_set: frog_ast.Set):
        if not the_set.elements:
            self.stack.append("\\emptyset")

    def leave_field_access(self, field_access: frog_ast.FieldAccess):
        the_object = self.stack.pop()
        self.stack.append(f"{the_object}.{self.convert_name(field_access.name)}")

    def leave_func_call(self, call: frog_ast.FuncCall):
        args = []
        for _ in enumerate(call.args):
            args.append(self.stack[-1])
            self.stack.pop()

        name = self.stack.pop()
        self.stack.append(f"{name}()")

    def leave_assignment(self, _: frog_ast.Assignment):
        value = self.stack.pop()
        name = self.stack.pop()
        print(f"{name} \\leftarrow {value}\\\\")

    def leave_return_statement(self, return_val: frog_ast.ReturnStatement):
        value = self.stack.pop()
        print(f"\\pcreturn {value}\\\\")

    def convert_name(self, name: str) -> str:
        if name == "KeyGen":
            return "\\kgen"
        if name == "Enc":
            return "\\enc"
        if name == "Dec":
            return "\\dec"
        return name

    def get_oracle_name(self, name: str) -> str:
        return f"\\Oracle{{{name}}}"
