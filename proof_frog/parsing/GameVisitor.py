# Generated from proof_frog/antlr/Game.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .GameParser import GameParser
else:
    from GameParser import GameParser

# This class defines a complete generic visitor for a parse tree produced by GameParser.

class GameVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by GameParser#program.
    def visitProgram(self, ctx:GameParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#gameExport.
    def visitGameExport(self, ctx:GameParser.GameExportContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#game.
    def visitGame(self, ctx:GameParser.GameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#gameBody.
    def visitGameBody(self, ctx:GameParser.GameBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#gamePhase.
    def visitGamePhase(self, ctx:GameParser.GamePhaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#field.
    def visitField(self, ctx:GameParser.FieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#initializedField.
    def visitInitializedField(self, ctx:GameParser.InitializedFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#method.
    def visitMethod(self, ctx:GameParser.MethodContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#block.
    def visitBlock(self, ctx:GameParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#varDeclStatement.
    def visitVarDeclStatement(self, ctx:GameParser.VarDeclStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#varDeclWithValueStatement.
    def visitVarDeclWithValueStatement(self, ctx:GameParser.VarDeclWithValueStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#varDeclWithSampleStatement.
    def visitVarDeclWithSampleStatement(self, ctx:GameParser.VarDeclWithSampleStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#assignmentStatement.
    def visitAssignmentStatement(self, ctx:GameParser.AssignmentStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#sampleStatement.
    def visitSampleStatement(self, ctx:GameParser.SampleStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#functionCallStatement.
    def visitFunctionCallStatement(self, ctx:GameParser.FunctionCallStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#returnStatement.
    def visitReturnStatement(self, ctx:GameParser.ReturnStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#ifStatement.
    def visitIfStatement(self, ctx:GameParser.IfStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#numericForStatement.
    def visitNumericForStatement(self, ctx:GameParser.NumericForStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#genericForStatement.
    def visitGenericForStatement(self, ctx:GameParser.GenericForStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#lvalue.
    def visitLvalue(self, ctx:GameParser.LvalueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#methodSignature.
    def visitMethodSignature(self, ctx:GameParser.MethodSignatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#paramList.
    def visitParamList(self, ctx:GameParser.ParamListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#createSetExp.
    def visitCreateSetExp(self, ctx:GameParser.CreateSetExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#inExp.
    def visitInExp(self, ctx:GameParser.InExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#andExp.
    def visitAndExp(self, ctx:GameParser.AndExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#fnCallExp.
    def visitFnCallExp(self, ctx:GameParser.FnCallExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#lvalueExp.
    def visitLvalueExp(self, ctx:GameParser.LvalueExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#boolExp.
    def visitBoolExp(self, ctx:GameParser.BoolExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#addExp.
    def visitAddExp(self, ctx:GameParser.AddExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#notEqualsExp.
    def visitNotEqualsExp(self, ctx:GameParser.NotEqualsExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#geqExp.
    def visitGeqExp(self, ctx:GameParser.GeqExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#notExp.
    def visitNotExp(self, ctx:GameParser.NotExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#noneExp.
    def visitNoneExp(self, ctx:GameParser.NoneExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#gtExp.
    def visitGtExp(self, ctx:GameParser.GtExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#ltExp.
    def visitLtExp(self, ctx:GameParser.LtExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#subtractExp.
    def visitSubtractExp(self, ctx:GameParser.SubtractExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#equalsExp.
    def visitEqualsExp(self, ctx:GameParser.EqualsExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#multiplyExp.
    def visitMultiplyExp(self, ctx:GameParser.MultiplyExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#subsetsExp.
    def visitSubsetsExp(self, ctx:GameParser.SubsetsExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#unionExp.
    def visitUnionExp(self, ctx:GameParser.UnionExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#intExp.
    def visitIntExp(self, ctx:GameParser.IntExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#sizeExp.
    def visitSizeExp(self, ctx:GameParser.SizeExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#typeExp.
    def visitTypeExp(self, ctx:GameParser.TypeExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#leqExp.
    def visitLeqExp(self, ctx:GameParser.LeqExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#orExp.
    def visitOrExp(self, ctx:GameParser.OrExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#createTupleExp.
    def visitCreateTupleExp(self, ctx:GameParser.CreateTupleExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#setMinusExp.
    def visitSetMinusExp(self, ctx:GameParser.SetMinusExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#divideExp.
    def visitDivideExp(self, ctx:GameParser.DivideExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#binaryNumExp.
    def visitBinaryNumExp(self, ctx:GameParser.BinaryNumExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#parenExp.
    def visitParenExp(self, ctx:GameParser.ParenExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#sliceExp.
    def visitSliceExp(self, ctx:GameParser.SliceExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#argList.
    def visitArgList(self, ctx:GameParser.ArgListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#variable.
    def visitVariable(self, ctx:GameParser.VariableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#parameterizedGame.
    def visitParameterizedGame(self, ctx:GameParser.ParameterizedGameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#arrayType.
    def visitArrayType(self, ctx:GameParser.ArrayTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#intType.
    def visitIntType(self, ctx:GameParser.IntTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#lvalueType.
    def visitLvalueType(self, ctx:GameParser.LvalueTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#optionalType.
    def visitOptionalType(self, ctx:GameParser.OptionalTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#mapType.
    def visitMapType(self, ctx:GameParser.MapTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#voidType.
    def visitVoidType(self, ctx:GameParser.VoidTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#setType.
    def visitSetType(self, ctx:GameParser.SetTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#bitStringType.
    def visitBitStringType(self, ctx:GameParser.BitStringTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#boolType.
    def visitBoolType(self, ctx:GameParser.BoolTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#productType.
    def visitProductType(self, ctx:GameParser.ProductTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#integerExpression.
    def visitIntegerExpression(self, ctx:GameParser.IntegerExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#bitstring.
    def visitBitstring(self, ctx:GameParser.BitstringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#set.
    def visitSet(self, ctx:GameParser.SetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#bool.
    def visitBool(self, ctx:GameParser.BoolContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#moduleImport.
    def visitModuleImport(self, ctx:GameParser.ModuleImportContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#id.
    def visitId(self, ctx:GameParser.IdContext):
        return self.visitChildren(ctx)



del GameParser