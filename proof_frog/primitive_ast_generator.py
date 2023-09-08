from parsing.PrimitiveVisitor import PrimitiveVisitor
from parsing.PrimitiveParser import PrimitiveParser
import frog_ast


class PrimitiveASTGenerator(PrimitiveVisitor):
    def visitProgram(self, ctx: PrimitiveParser.ProgramContext):
        name = ctx.ID().getText()
        param_list = [] if not ctx.paramList() else self.visit(ctx.paramList())
        field_list = []
        if ctx.primitiveBody().initializedField():
            for field in ctx.primitiveBody().initializedField():
                field_list.append(self.visit(field))

        method_list = []
        if ctx.primitiveBody().methodSignature():
            for method_signature in ctx.primitiveBody().methodSignature():
                method_list.append(self.visit(method_signature))

        return frog_ast.Primitive(name, param_list, field_list, method_list)

    def visitParamList(self, ctx):
        result = []
        for variable in ctx.variable():
            result.append(frog_ast.Parameter(self.visit(variable.type_()),
                          variable.id_().getText()))
        return result

    def visitLvalueType(self, ctx):
        return frog_ast.UserType(ctx.lvalue().id_()[0].getText())

    def visitOptionalType(self, ctx):
        the_type = self.visit(ctx.type_())
        the_type.optional = True
        return the_type

    def visitBoolType(self, ctx):
        return frog_ast.Type(frog_ast.BasicTypes.BOOL)

    def visitBitStringType(self, ctx):
        if not ctx.bitstring().integerExpression():
            return frog_ast.BitStringType()
        return frog_ast.BitStringType(self.visit(ctx.bitstring().integerExpression()))

    def visitProductType(self, ctx):
        return frog_ast.ProductType(self.visit(individualType) for individualType in ctx.type_())

    def visitSetType(self, ctx):
        return frog_ast.Type(frog_ast.BasicTypes.SET)

    def visitInitializedField(self, ctx):
        return frog_ast.Field(
            self.visit(ctx.variable().type_()),
            ctx.variable().id_().getText(),
            self.visit(ctx.expression()))

    def visitIntegerExpression(self, ctx):
        if ctx.lvalue():
            return frog_ast.VariableExpression(ctx.getText())

        operator = None
        if ctx.PLUS():
            operator = frog_ast.BinaryOperators.ADD
        elif ctx.SUBTRACT():
            operator = frog_ast.BinaryOperators.SUBTRACT
        elif ctx.TIMES():
            operator = frog_ast.BinaryOperators.MULTIPLY
        elif ctx.DIVIDE():
            operator = frog_ast.BinaryOperators.DIVIDE

        return frog_ast.BinaryOperation(
            operator,
            self.visit(ctx.integerExpression()[0]),
            self.visit(ctx.integerExpression()[1])
        )

    def visitArrayType(self, ctx):
        return frog_ast.ArrayType(self.visit(ctx.type_()), self.visit(ctx.integerExpression()))

    def visitVariableExp(self, ctx):
        if len(ctx.ID()) != 1:
            raise ValueError("Multiple ID access")
        return frog_ast.VariableExpression(ctx.ID()[0].getText())

    def visitMethodSignature(self, ctx):
        return frog_ast.MethodSignature(
            ctx.id_().getText(),
            self.visit(ctx.type_()),
            [] if not ctx.paramList() else self.visit(ctx.paramList()))
