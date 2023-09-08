# Generated from src/antlr/Game.g4 by ANTLR 4.13.0
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


    # Visit a parse tree produced by GameParser#game.
    def visitGame(self, ctx:GameParser.GameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#gameBody.
    def visitGameBody(self, ctx:GameParser.GameBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#gamePhase.
    def visitGamePhase(self, ctx:GameParser.GamePhaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#gameExport.
    def visitGameExport(self, ctx:GameParser.GameExportContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#field.
    def visitField(self, ctx:GameParser.FieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#initializedField.
    def visitInitializedField(self, ctx:GameParser.InitializedFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#simpleStatement.
    def visitSimpleStatement(self, ctx:GameParser.SimpleStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#statement.
    def visitStatement(self, ctx:GameParser.StatementContext):
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


    # Visit a parse tree produced by GameParser#notEqualsExp.
    def visitNotEqualsExp(self, ctx:GameParser.NotEqualsExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#addExp.
    def visitAddExp(self, ctx:GameParser.AddExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#geqExp.
    def visitGeqExp(self, ctx:GameParser.GeqExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#createArrayExp.
    def visitCreateArrayExp(self, ctx:GameParser.CreateArrayExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#notExp.
    def visitNotExp(self, ctx:GameParser.NotExpContext):
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


    # Visit a parse tree produced by GameParser#concatenateExp.
    def visitConcatenateExp(self, ctx:GameParser.ConcatenateExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#variableExp.
    def visitVariableExp(self, ctx:GameParser.VariableExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#leqExp.
    def visitLeqExp(self, ctx:GameParser.LeqExpContext):
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


    # Visit a parse tree produced by GameParser#arrayAccessExp.
    def visitArrayAccessExp(self, ctx:GameParser.ArrayAccessExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#argList.
    def visitArgList(self, ctx:GameParser.ArgListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#variable.
    def visitVariable(self, ctx:GameParser.VariableContext):
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


    # Visit a parse tree produced by GameParser#moduleImport.
    def visitModuleImport(self, ctx:GameParser.ModuleImportContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#methodBody.
    def visitMethodBody(self, ctx:GameParser.MethodBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by GameParser#id.
    def visitId(self, ctx:GameParser.IdContext):
        return self.visitChildren(ctx)



del GameParser