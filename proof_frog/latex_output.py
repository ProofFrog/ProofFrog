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

    def leave_parameter(self, parameter: frog_ast.Parameter):
        type_str = self.stack.pop()
        if self.parameters != "":
            self.parameters += ","
        self.parameters += parameter.name
        if not self.in_game_parameters:
            self.parameters += " \\in " + type_str

    def visit_method(self, method: frog_ast.Method):
        self.in_game_parameters = False
        if method.signature.name == "Initialize":
            print(
                f"\\procedureblock[linenumbering, space=auto]{{{self.escape_name(self.property_name)}-{self.escape_name(self.game_name)}$^\\adv_{self.parameters}$}}{{"
            )
            self.in_initialize = True
            self.parameters = ""
        else:
            self.parameters = ""
            self.visit(method.signature)
            print(
                f"\\procedureblock[linenumbering, space=auto]{{{self.get_oracle_name(method.signature.name)}(${self.parameters}$)}}{{"
            )

    def leave_block(self, block: frog_ast.Block):
        stmts = []
        for statement in block.statements:
            stmts.append(self.stack.pop())
        stmts.reverse()
        stmts_str = "\\\\ \n".join(stmts)
        self.stack.append(stmts_str)

    def leave_method(self, _: frog_ast.Method):
        oracle_list = ",".join(self.oracles)
        print(self.stack.pop())
        if self.in_initialize:
            print(f"\\\\ \\pcreturn \\adv^{{{oracle_list}}}()")
            self.in_initialize = False
        print("}")

    def visit_variable(self, var: frog_ast.Variable):
        self.stack.append(self.convert_name(var.name))

    def leave_set(self, the_set: frog_ast.Set):
        if not the_set.elements:
            self.stack.append("\\emptyset")
            return
        items = []
        for _ in the_set.elements:
            items.append(self.stack.pop())
        items_str = ", ".join(items)
        self.stack.append(f"\\{{ {items_str} \\}}")

    def leave_field_access(self, field_access: frog_ast.FieldAccess):
        the_object = self.stack.pop()
        self.stack.append(f"{the_object}.{self.convert_name(field_access.name)}")

    def leave_func_call(self, call: frog_ast.FuncCall):
        args = []
        for _ in call.args:
            args.append(self.stack.pop())
        args.reverse()

        name = self.stack.pop()
        arg_str = ", ".join(args)
        self.stack.append(f"{name}({arg_str})")

    def leave_assignment(self, assignment: frog_ast.Assignment):
        value = self.stack.pop()
        name = self.stack.pop()
        if assignment.the_type:
            self.stack.pop()
        self.stack.append(f"{name} \\leftarrow {value}")

    def leave_sample(self, sample: frog_ast.Sample):
        value = self.stack.pop()
        name = self.stack.pop()
        if sample.the_type:
            self.stack.pop()
        self.stack.append(f"{name} \\sample {value}")

    def leave_return_statement(self, return_val: frog_ast.ReturnStatement):
        value = self.stack.pop()
        self.stack.append(f"\\pcreturn {value}")

    def leave_binary_operation(self, bin_op: frog_ast.BinaryOperation):
        rhs = self.stack.pop()
        lhs = self.stack.pop()
        operation_map = {
            frog_ast.BinaryOperators.UNION: "\\cup",
            frog_ast.BinaryOperators.IN: "\\in",
        }
        self.stack.append(f"{lhs} {operation_map[bin_op.operator]} {rhs}")

    def leave_if_statement(self, if_stmt: frog_ast.IfStatement):
        block_strs = []
        condition_strs = []
        for block in if_stmt.blocks:
            block_strs.append(self.stack.pop())
        for cond in if_stmt.conditions:
            condition_strs.append(self.stack.pop())
        block_strs.reverse()
        condition_strs.reverse()
        final_str = ""
        for index, condition_str in enumerate(condition_strs):
            if_type = "\pcif" if index == 0 else "\pcelseif"
            final_str += f"{if_type} {condition_str} \pcthen \\\\\n"
            final_str += block_strs[index] + "\\\\\n"
        if if_stmt.has_else_block():
            final_str += f"\pcelse\\\\\n {block_strs[-1]} \n"
        final_str += "\pcendif"
        self.stack.append(final_str)

    def visit_a_s_t_none(self, _: frog_ast.ASTNone) -> None:
        self.stack.append("\\bot")

    def convert_name(self, name: str) -> str:
        name_lookup = {
            "KeyGen": "\\kgen",
            "Enc": "\\enc",
            "Dec": "\\dec",
            "Ciphertext": "\\mathcal{C}",
            "Message": "\\mathcal{M}",
            "Key": "\\mathcal{K}",
        }
        return self.escape_name(name) if name not in name_lookup else name_lookup[name]

    def get_oracle_name(self, name: str) -> str:
        return f"\\Oracle{{{self.escape_name(name)}}}"

    def escape_name(self, name: str) -> str:
        return name.replace("$", "\\$")
