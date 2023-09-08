# Generated from src/antlr/Scheme.g4 by ANTLR 4.13.0
from antlr4 import *
if "." in __name__:
    from .SchemeParser import SchemeParser
else:
    from SchemeParser import SchemeParser

# This class defines a complete generic visitor for a parse tree produced by SchemeParser.

class SchemeVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SchemeParser#program.
    def visitProgram(self, ctx:SchemeParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#scheme.
    def visitScheme(self, ctx:SchemeParser.SchemeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#schemeBody.
    def visitSchemeBody(self, ctx:SchemeParser.SchemeBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#game.
    def visitGame(self, ctx:SchemeParser.GameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#gameBody.
    def visitGameBody(self, ctx:SchemeParser.GameBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#gamePhase.
    def visitGamePhase(self, ctx:SchemeParser.GamePhaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#gameExport.
    def visitGameExport(self, ctx:SchemeParser.GameExportContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#field.
    def visitField(self, ctx:SchemeParser.FieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#initializedField.
    def visitInitializedField(self, ctx:SchemeParser.InitializedFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#simpleStatement.
    def visitSimpleStatement(self, ctx:SchemeParser.SimpleStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#statement.
    def visitStatement(self, ctx:SchemeParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#lvalue.
    def visitLvalue(self, ctx:SchemeParser.LvalueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#methodSignature.
    def visitMethodSignature(self, ctx:SchemeParser.MethodSignatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#paramList.
    def visitParamList(self, ctx:SchemeParser.ParamListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#createSetExp.
    def visitCreateSetExp(self, ctx:SchemeParser.CreateSetExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#inExp.
    def visitInExp(self, ctx:SchemeParser.InExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#andExp.
    def visitAndExp(self, ctx:SchemeParser.AndExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#fnCallExp.
    def visitFnCallExp(self, ctx:SchemeParser.FnCallExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#notEqualsExp.
    def visitNotEqualsExp(self, ctx:SchemeParser.NotEqualsExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#addExp.
    def visitAddExp(self, ctx:SchemeParser.AddExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#geqExp.
    def visitGeqExp(self, ctx:SchemeParser.GeqExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#createArrayExp.
    def visitCreateArrayExp(self, ctx:SchemeParser.CreateArrayExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#notExp.
    def visitNotExp(self, ctx:SchemeParser.NotExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#gtExp.
    def visitGtExp(self, ctx:SchemeParser.GtExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#ltExp.
    def visitLtExp(self, ctx:SchemeParser.LtExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#subtractExp.
    def visitSubtractExp(self, ctx:SchemeParser.SubtractExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#equalsExp.
    def visitEqualsExp(self, ctx:SchemeParser.EqualsExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#multiplyExp.
    def visitMultiplyExp(self, ctx:SchemeParser.MultiplyExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#subsetsExp.
    def visitSubsetsExp(self, ctx:SchemeParser.SubsetsExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#unionExp.
    def visitUnionExp(self, ctx:SchemeParser.UnionExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#intExp.
    def visitIntExp(self, ctx:SchemeParser.IntExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#sizeExp.
    def visitSizeExp(self, ctx:SchemeParser.SizeExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#typeExp.
    def visitTypeExp(self, ctx:SchemeParser.TypeExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#concatenateExp.
    def visitConcatenateExp(self, ctx:SchemeParser.ConcatenateExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#variableExp.
    def visitVariableExp(self, ctx:SchemeParser.VariableExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#leqExp.
    def visitLeqExp(self, ctx:SchemeParser.LeqExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#setMinusExp.
    def visitSetMinusExp(self, ctx:SchemeParser.SetMinusExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#divideExp.
    def visitDivideExp(self, ctx:SchemeParser.DivideExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#binaryNumExp.
    def visitBinaryNumExp(self, ctx:SchemeParser.BinaryNumExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#parenExp.
    def visitParenExp(self, ctx:SchemeParser.ParenExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#sliceExp.
    def visitSliceExp(self, ctx:SchemeParser.SliceExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#arrayAccessExp.
    def visitArrayAccessExp(self, ctx:SchemeParser.ArrayAccessExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#argList.
    def visitArgList(self, ctx:SchemeParser.ArgListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#variable.
    def visitVariable(self, ctx:SchemeParser.VariableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#arrayType.
    def visitArrayType(self, ctx:SchemeParser.ArrayTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#intType.
    def visitIntType(self, ctx:SchemeParser.IntTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#lvalueType.
    def visitLvalueType(self, ctx:SchemeParser.LvalueTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#optionalType.
    def visitOptionalType(self, ctx:SchemeParser.OptionalTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#mapType.
    def visitMapType(self, ctx:SchemeParser.MapTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#setType.
    def visitSetType(self, ctx:SchemeParser.SetTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#bitStringType.
    def visitBitStringType(self, ctx:SchemeParser.BitStringTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#boolType.
    def visitBoolType(self, ctx:SchemeParser.BoolTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#productType.
    def visitProductType(self, ctx:SchemeParser.ProductTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#integerExpression.
    def visitIntegerExpression(self, ctx:SchemeParser.IntegerExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#bitstring.
    def visitBitstring(self, ctx:SchemeParser.BitstringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#set.
    def visitSet(self, ctx:SchemeParser.SetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#moduleImport.
    def visitModuleImport(self, ctx:SchemeParser.ModuleImportContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#methodBody.
    def visitMethodBody(self, ctx:SchemeParser.MethodBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SchemeParser#id.
    def visitId(self, ctx:SchemeParser.IdContext):
        return self.visitChildren(ctx)



del SchemeParser