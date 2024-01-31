# Generated from proof_frog/antlr/Primitive.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .PrimitiveParser import PrimitiveParser
else:
    from PrimitiveParser import PrimitiveParser

# This class defines a complete generic visitor for a parse tree produced by PrimitiveParser.

class PrimitiveVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by PrimitiveParser#program.
    def visitProgram(self, ctx:PrimitiveParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#primitiveBody.
    def visitPrimitiveBody(self, ctx:PrimitiveParser.PrimitiveBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#game.
    def visitGame(self, ctx:PrimitiveParser.GameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#gameBody.
    def visitGameBody(self, ctx:PrimitiveParser.GameBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#gamePhase.
    def visitGamePhase(self, ctx:PrimitiveParser.GamePhaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#field.
    def visitField(self, ctx:PrimitiveParser.FieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#initializedField.
    def visitInitializedField(self, ctx:PrimitiveParser.InitializedFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#method.
    def visitMethod(self, ctx:PrimitiveParser.MethodContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#block.
    def visitBlock(self, ctx:PrimitiveParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#varDeclStatement.
    def visitVarDeclStatement(self, ctx:PrimitiveParser.VarDeclStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#varDeclWithValueStatement.
    def visitVarDeclWithValueStatement(self, ctx:PrimitiveParser.VarDeclWithValueStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#varDeclWithSampleStatement.
    def visitVarDeclWithSampleStatement(self, ctx:PrimitiveParser.VarDeclWithSampleStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#assignmentStatement.
    def visitAssignmentStatement(self, ctx:PrimitiveParser.AssignmentStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#sampleStatement.
    def visitSampleStatement(self, ctx:PrimitiveParser.SampleStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#functionCallStatement.
    def visitFunctionCallStatement(self, ctx:PrimitiveParser.FunctionCallStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#returnStatement.
    def visitReturnStatement(self, ctx:PrimitiveParser.ReturnStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#ifStatement.
    def visitIfStatement(self, ctx:PrimitiveParser.IfStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#numericForStatement.
    def visitNumericForStatement(self, ctx:PrimitiveParser.NumericForStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#genericForStatement.
    def visitGenericForStatement(self, ctx:PrimitiveParser.GenericForStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#lvalue.
    def visitLvalue(self, ctx:PrimitiveParser.LvalueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#methodSignature.
    def visitMethodSignature(self, ctx:PrimitiveParser.MethodSignatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#paramList.
    def visitParamList(self, ctx:PrimitiveParser.ParamListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#createSetExp.
    def visitCreateSetExp(self, ctx:PrimitiveParser.CreateSetExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#inExp.
    def visitInExp(self, ctx:PrimitiveParser.InExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#andExp.
    def visitAndExp(self, ctx:PrimitiveParser.AndExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#fnCallExp.
    def visitFnCallExp(self, ctx:PrimitiveParser.FnCallExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#lvalueExp.
    def visitLvalueExp(self, ctx:PrimitiveParser.LvalueExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#boolExp.
    def visitBoolExp(self, ctx:PrimitiveParser.BoolExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#addExp.
    def visitAddExp(self, ctx:PrimitiveParser.AddExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#notEqualsExp.
    def visitNotEqualsExp(self, ctx:PrimitiveParser.NotEqualsExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#geqExp.
    def visitGeqExp(self, ctx:PrimitiveParser.GeqExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#notExp.
    def visitNotExp(self, ctx:PrimitiveParser.NotExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#noneExp.
    def visitNoneExp(self, ctx:PrimitiveParser.NoneExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#gtExp.
    def visitGtExp(self, ctx:PrimitiveParser.GtExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#ltExp.
    def visitLtExp(self, ctx:PrimitiveParser.LtExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#subtractExp.
    def visitSubtractExp(self, ctx:PrimitiveParser.SubtractExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#equalsExp.
    def visitEqualsExp(self, ctx:PrimitiveParser.EqualsExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#multiplyExp.
    def visitMultiplyExp(self, ctx:PrimitiveParser.MultiplyExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#subsetsExp.
    def visitSubsetsExp(self, ctx:PrimitiveParser.SubsetsExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#unionExp.
    def visitUnionExp(self, ctx:PrimitiveParser.UnionExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#intExp.
    def visitIntExp(self, ctx:PrimitiveParser.IntExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#sizeExp.
    def visitSizeExp(self, ctx:PrimitiveParser.SizeExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#typeExp.
    def visitTypeExp(self, ctx:PrimitiveParser.TypeExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#leqExp.
    def visitLeqExp(self, ctx:PrimitiveParser.LeqExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#orExp.
    def visitOrExp(self, ctx:PrimitiveParser.OrExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#createTupleExp.
    def visitCreateTupleExp(self, ctx:PrimitiveParser.CreateTupleExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#setMinusExp.
    def visitSetMinusExp(self, ctx:PrimitiveParser.SetMinusExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#divideExp.
    def visitDivideExp(self, ctx:PrimitiveParser.DivideExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#binaryNumExp.
    def visitBinaryNumExp(self, ctx:PrimitiveParser.BinaryNumExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#parenExp.
    def visitParenExp(self, ctx:PrimitiveParser.ParenExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#sliceExp.
    def visitSliceExp(self, ctx:PrimitiveParser.SliceExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#argList.
    def visitArgList(self, ctx:PrimitiveParser.ArgListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#variable.
    def visitVariable(self, ctx:PrimitiveParser.VariableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#parameterizedGame.
    def visitParameterizedGame(self, ctx:PrimitiveParser.ParameterizedGameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#arrayType.
    def visitArrayType(self, ctx:PrimitiveParser.ArrayTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#intType.
    def visitIntType(self, ctx:PrimitiveParser.IntTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#lvalueType.
    def visitLvalueType(self, ctx:PrimitiveParser.LvalueTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#optionalType.
    def visitOptionalType(self, ctx:PrimitiveParser.OptionalTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#mapType.
    def visitMapType(self, ctx:PrimitiveParser.MapTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#voidType.
    def visitVoidType(self, ctx:PrimitiveParser.VoidTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#setType.
    def visitSetType(self, ctx:PrimitiveParser.SetTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#bitStringType.
    def visitBitStringType(self, ctx:PrimitiveParser.BitStringTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#boolType.
    def visitBoolType(self, ctx:PrimitiveParser.BoolTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#productType.
    def visitProductType(self, ctx:PrimitiveParser.ProductTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#integerExpression.
    def visitIntegerExpression(self, ctx:PrimitiveParser.IntegerExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#bitstring.
    def visitBitstring(self, ctx:PrimitiveParser.BitstringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#set.
    def visitSet(self, ctx:PrimitiveParser.SetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#bool.
    def visitBool(self, ctx:PrimitiveParser.BoolContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#moduleImport.
    def visitModuleImport(self, ctx:PrimitiveParser.ModuleImportContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PrimitiveParser#id.
    def visitId(self, ctx:PrimitiveParser.IdContext):
        return self.visitChildren(ctx)



del PrimitiveParser