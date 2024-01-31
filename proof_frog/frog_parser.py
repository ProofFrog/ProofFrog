import os
from typing import Type
from antlr4 import FileStream, InputStream, CommonTokenStream
from .parsing.PrimitiveVisitor import PrimitiveVisitor
from .parsing.PrimitiveParser import PrimitiveParser
from .parsing.PrimitiveLexer import PrimitiveLexer
from .parsing.SchemeVisitor import SchemeVisitor
from .parsing.SchemeParser import SchemeParser
from .parsing.SchemeLexer import SchemeLexer
from .parsing.GameVisitor import GameVisitor
from .parsing.GameParser import GameParser
from .parsing.GameLexer import GameLexer
from .parsing.ProofVisitor import ProofVisitor
from .parsing.ProofParser import ProofParser
from .parsing.ProofLexer import ProofLexer
from . import frog_ast


def _binary_operation(
    operator: frog_ast.BinaryOperators,
    visit: Type[PrimitiveVisitor.visit],
    ctx: Type[PrimitiveParser.ExpressionContext],
) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(
        operator, visit(ctx.expression()[0]), visit(ctx.expression()[1])
    )


# pylint: disable-next=too-many-public-methods
class _SharedAST(PrimitiveVisitor, SchemeVisitor, GameVisitor, ProofVisitor):  # type: ignore[misc]
    def visitParamList(
        self, ctx: PrimitiveParser.ParamListContext
    ) -> list[frog_ast.Parameter]:
        result = []
        for variable in ctx.variable():
            result.append(
                frog_ast.Parameter(
                    super().visit(variable.type_()), variable.id_().getText()
                )
            )
        return result

    def visitOptionalType(
        self, ctx: PrimitiveParser.OptionalTypeContext
    ) -> frog_ast.Type:
        return frog_ast.OptionalType(self.visit(ctx.type_()))

    def visitBoolType(self, __: PrimitiveParser.BoolTypeContext) -> frog_ast.Type:
        return frog_ast.BoolType()

    def visitVoidType(self, __: PrimitiveParser.VoidTypeContext) -> frog_ast.Void:
        return frog_ast.Void()

    def visitBitStringType(
        self, ctx: PrimitiveParser.BitStringTypeContext
    ) -> frog_ast.BitStringType:
        if not ctx.bitstring().integerExpression():
            return frog_ast.BitStringType()
        return frog_ast.BitStringType(self.visit(ctx.bitstring().integerExpression()))

    def visitProductType(
        self, ctx: PrimitiveParser.ProductTypeContext
    ) -> frog_ast.BinaryOperation:
        expression = self.visit(ctx.type_()[-1])
        reversed_list = ctx.type_().copy()[:-1]
        reversed_list.reverse()
        for the_type in reversed_list:
            expression = frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.MULTIPLY, self.visit(the_type), expression
            )
        assert isinstance(expression, frog_ast.BinaryOperation)
        return expression

    def visitSetType(self, ctx: PrimitiveParser.SetTypeContext) -> frog_ast.SetType:
        return frog_ast.SetType(
            self.visit(ctx.set_().type_()) if ctx.set_().type_() else None
        )

    def visitField(self, ctx: PrimitiveParser.FieldContext) -> frog_ast.Field:
        return frog_ast.Field(
            self.visit(ctx.variable().type_()),
            ctx.variable().id_().getText(),
            self.visit(ctx.expression()) if ctx.expression() else None,
        )

    def visitInitializedField(
        self, ctx: PrimitiveParser.InitializedFieldContext
    ) -> frog_ast.Field:
        return frog_ast.Field(
            self.visit(ctx.variable().type_()),
            ctx.variable().id_().getText(),
            self.visit(ctx.expression()),
        )

    def visitEqualsExp(
        self, ctx: PrimitiveParser.EqualsExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.EQUALS, self.visit, ctx)

    def visitNotEqualsExp(
        self, ctx: PrimitiveParser.NotEqualsExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.NOTEQUALS, self.visit, ctx)

    def visitGtExp(self, ctx: PrimitiveParser.GtExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.GT, self.visit, ctx)

    def visitLtExp(self, ctx: PrimitiveParser.LtExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.LT, self.visit, ctx)

    def visitGeqExp(
        self, ctx: PrimitiveParser.GeqExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.GEQ, self.visit, ctx)

    def visitLeqExp(
        self, ctx: PrimitiveParser.LeqExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.LEQ, self.visit, ctx)

    def visitAndExp(
        self, ctx: PrimitiveParser.AndExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.AND, self.visit, ctx)

    def visitSubsetsExp(
        self, ctx: PrimitiveParser.SubsetsExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.SUBSETS, self.visit, ctx)

    def visitInExp(self, ctx: PrimitiveParser.InExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.IN, self.visit, ctx)

    def visitOrExp(self, ctx: PrimitiveParser.OrExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.OR, self.visit, ctx)

    def visitUnionExp(
        self, ctx: PrimitiveParser.UnionExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.UNION, self.visit, ctx)

    def visitSetMinusExp(
        self, ctx: PrimitiveParser.SetMinusExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.SETMINUS, self.visit, ctx)

    def visitAddExp(
        self, ctx: PrimitiveParser.AddExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.ADD, self.visit, ctx)

    def visitSubtractExp(
        self, ctx: PrimitiveParser.SubtractExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.SUBTRACT, self.visit, ctx)

    def visitMultiplyExp(
        self, ctx: PrimitiveParser.MultiplyExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.MULTIPLY, self.visit, ctx)

    def visitDivideExp(
        self, ctx: PrimitiveParser.DivideExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.DIVIDE, self.visit, ctx)

    def visitCreateSetExp(
        self, ctx: PrimitiveParser.CreateSetExpContext
    ) -> frog_ast.Set:
        return frog_ast.Set(
            [self.visit(element) for element in ctx.expression()]
            if ctx.expression()
            else []
        )

    def visitMethod(self, ctx: PrimitiveParser.MethodContext) -> frog_ast.Method:
        return frog_ast.Method(
            self.visit(ctx.methodSignature()), self.visit(ctx.block())
        )

    def visitIntegerExpression(
        self, ctx: PrimitiveParser.IntegerExpressionContext
    ) -> frog_ast.Expression:
        if ctx.INT():
            return frog_ast.Integer(int(ctx.INT().getText()))
        if ctx.BINARYNUM():
            return frog_ast.BinaryNum(int(ctx.BINARYNUM().getText(), 2))

        if ctx.lvalue():
            exp: frog_ast.Expression = self.visit(ctx.lvalue())
            return exp

        operator: frog_ast.BinaryOperators
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
            self.visit(ctx.integerExpression()[1]),
        )

    def visitVarDeclWithValueStatement(
        self, ctx: PrimitiveParser.VarDeclWithValueStatementContext
    ) -> frog_ast.Assignment:
        return frog_ast.Assignment(
            self.visit(ctx.type_()),
            self.visit(ctx.lvalue()),
            self.visit(ctx.expression()),
        )

    def visitAssignmentStatement(
        self, ctx: PrimitiveParser.AssignmentStatementContext
    ) -> frog_ast.Assignment:
        return frog_ast.Assignment(
            None, self.visit(ctx.lvalue()), self.visit(ctx.expression())
        )

    def visitSampleStatement(
        self, ctx: PrimitiveParser.SampleStatementContext
    ) -> frog_ast.Sample:
        return frog_ast.Sample(
            None, self.visit(ctx.lvalue()), self.visit(ctx.expression())
        )

    def visitBlock(self, ctx: PrimitiveParser.BlockContext) -> frog_ast.Block:
        return frog_ast.Block([self.visit(statement) for statement in ctx.statement()])

    def visitNumericForStatement(
        self, ctx: PrimitiveParser.NumericForStatementContext
    ) -> frog_ast.NumericFor:
        return frog_ast.NumericFor(
            ctx.id_().getText(),
            self.visit(ctx.expression()[0]),
            self.visit(ctx.expression()[1]),
            self.visit(ctx.block()),
        )

    def visitGenericForStatement(
        self, ctx: PrimitiveParser.GenericForStatementContext
    ) -> frog_ast.GenericFor:
        return frog_ast.GenericFor(
            self.visit(ctx.type_()),
            ctx.id_().getText(),
            self.visit(ctx.expression()),
            self.visit(ctx.block()),
        )

    def visitIntExp(self, ctx: PrimitiveParser.IntExpContext) -> frog_ast.Integer:
        return frog_ast.Integer(int(ctx.INT().getText()))

    def visitBoolExp(self, ctx: PrimitiveParser.BoolExpContext) -> frog_ast.Boolean:
        return frog_ast.Boolean(ctx.bool_().getText() == "true")

    def visitBinaryNumExp(
        self, ctx: PrimitiveParser.BinaryNumExpContext
    ) -> frog_ast.BinaryNum:
        return frog_ast.BinaryNum(int(ctx.BINARYNUM().getText(), 2))

    def visitVarDeclWithSampleStatement(
        self, ctx: PrimitiveParser.VarDeclWithSampleStatementContext
    ) -> frog_ast.Sample:
        return frog_ast.Sample(
            self.visit(ctx.type_()),
            self.visit(ctx.lvalue()),
            self.visit(ctx.expression()),
        )

    def visitVarDeclStatement(
        self, ctx: PrimitiveParser.VarDeclStatementContext
    ) -> frog_ast.VariableDeclaration:
        return frog_ast.VariableDeclaration(
            self.visit(ctx.type_()), ctx.id_().getText()
        )

    def visitArrayType(
        self, ctx: PrimitiveParser.ArrayTypeContext
    ) -> frog_ast.ArrayType:
        return frog_ast.ArrayType(
            self.visit(ctx.type_()), self.visit(ctx.integerExpression())
        )

    def visitMapType(self, ctx: PrimitiveParser.MapTypeContext) -> frog_ast.MapType:
        return frog_ast.MapType(self.visit(ctx.type_()[0]), self.visit(ctx.type_()[1]))

    def visitNotExp(
        self, ctx: PrimitiveParser.NotExpContext
    ) -> frog_ast.UnaryOperation:
        return frog_ast.UnaryOperation(
            frog_ast.UnaryOperators.NOT, self.visit(ctx.expression())
        )

    def visitIntType(self, ctx: PrimitiveParser.IntTypeContext) -> frog_ast.Type:
        return frog_ast.IntType()

    def visitSizeExp(
        self, ctx: PrimitiveParser.SizeExpContext
    ) -> frog_ast.UnaryOperation:
        return frog_ast.UnaryOperation(
            frog_ast.UnaryOperators.SIZE, self.visit(ctx.expression())
        )

    def visitNoneExp(self, __: PrimitiveParser.NoneExpContext) -> frog_ast.ASTNone:
        return frog_ast.ASTNone()

    def visitParenExp(
        self, ctx: PrimitiveParser.ParenExpContext
    ) -> frog_ast.Expression:
        exp: frog_ast.Expression = self.visit(ctx.expression())
        return exp

    def visitLvalue(self, ctx: PrimitiveParser.LvalueExpContext) -> frog_ast.Expression:
        expression: frog_ast.Expression
        i = 1
        if ctx.parameterizedGame():
            expression = self.visit(ctx.parameterizedGame())
            assert isinstance(expression, frog_ast.ParameterizedGame)
            if ctx.getChildCount() > 3:
                expression = frog_ast.ConcreteGame(
                    expression, ctx.getChild(2).getText()
                )
                i = 3
        else:
            expression = frog_ast.Variable(ctx.id_()[0].getText())

        while i < ctx.getChildCount():
            if ctx.getChild(i).getText() == ".":
                expression = frog_ast.FieldAccess(
                    expression, ctx.getChild(i + 1).getText()
                )
                i += 2
            else:
                index_expression: frog_ast.Expression = self.visit(ctx.getChild(i + 1))
                expression = frog_ast.ArrayAccess(expression, index_expression)
                i += 3

        return expression

    def visitCreateTupleExp(
        self, ctx: PrimitiveParser.CreateTupleExpContext
    ) -> frog_ast.Tuple:
        return frog_ast.Tuple([self.visit(exp) for exp in ctx.expression()])

    def visitReturnStatement(
        self, ctx: PrimitiveParser.ReturnStatementContext
    ) -> frog_ast.ReturnStatement:
        return frog_ast.ReturnStatement(self.visit(ctx.expression()))

    def visitFunctionCallStatement(
        self, ctx: PrimitiveParser.FunctionCallStatementContext
    ) -> frog_ast.FuncCall:
        return frog_ast.FuncCall(
            self.visit(ctx.expression()),
            self.visit(ctx.argList()) if ctx.argList() else [],
        )

    def visitFnCallExp(
        self, ctx: PrimitiveParser.FnCallExpContext
    ) -> frog_ast.FuncCall:
        return frog_ast.FuncCall(
            self.visit(ctx.expression()),
            self.visit(ctx.argList()) if ctx.argList() else [],
        )

    def visitSliceExp(self, ctx: PrimitiveParser.SliceExpContext) -> frog_ast.Slice:
        return frog_ast.Slice(
            self.visit(ctx.expression()),
            self.visit(ctx.integerExpression()[0]),
            self.visit(ctx.integerExpression()[1]),
        )

    def visitArgList(
        self, ctx: PrimitiveParser.ArgListContext
    ) -> list[frog_ast.Expression]:
        return [self.visit(exp) for exp in ctx.expression()]

    def visitLvalueExp(
        self, ctx: PrimitiveParser.LvalueExpContext
    ) -> frog_ast.Expression:
        exp: frog_ast.Expression = self.visit(ctx.lvalue())
        return exp

    def visitMethodSignature(
        self, ctx: PrimitiveParser.MethodSignatureContext
    ) -> frog_ast.MethodSignature:
        return frog_ast.MethodSignature(
            ctx.id_().getText(),
            self.visit(ctx.type_()),
            [] if not ctx.paramList() else self.visit(ctx.paramList()),
        )

    def visitModuleImport(
        self, ctx: PrimitiveParser.ModuleImportContext
    ) -> frog_ast.Import:
        return frog_ast.Import(
            ctx.FILESTRING().getText().strip("'"),
            ctx.ID().getText() if ctx.ID() else "",
        )

    def visitIfStatement(
        self, ctx: PrimitiveParser.IfStatementContext
    ) -> frog_ast.IfStatement:
        return frog_ast.IfStatement(
            [self.visit(exp) for exp in ctx.expression()],
            [self.visit(block) for block in ctx.block()],
        )

    def visitGamePhase(self, ctx: PrimitiveParser.GamePhaseContext) -> frog_ast.Phase:
        oracles = [oracle.getText() for oracle in ctx.id_()]
        method_list = []
        for method in ctx.method():
            method_list.append(self.visit(method))
        return frog_ast.Phase(oracles, method_list)

    def visitGame(self, ctx: PrimitiveParser.GameContext) -> frog_ast.Game:
        return frog_ast.Game(_parse_game_body(self.visit, ctx))


class _PrimitiveASTGenerator(_SharedAST, PrimitiveVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: PrimitiveParser.ProgramContext) -> frog_ast.Primitive:
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


class _SchemeASTGenerator(_SharedAST, SchemeVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: SchemeParser.ProgramContext) -> frog_ast.Scheme:
        scheme_ctx = ctx.scheme()

        imports = [self.visit(im) for im in ctx.moduleImport()]

        name = scheme_ctx.ID()[0].getText()
        param_list = (
            [] if not scheme_ctx.paramList() else self.visit(scheme_ctx.paramList())
        )
        primitive_name = scheme_ctx.ID()[1].getText()
        field_list = []
        requirement_list = []
        method_list = []

        if scheme_ctx.schemeBody().field():
            for field in scheme_ctx.schemeBody().field():
                field_list.append(self.visit(field))
        if scheme_ctx.schemeBody().REQUIRES():
            for requirement in scheme_ctx.schemeBody().expression():
                requirement_list.append(self.visit(requirement))
        for method in scheme_ctx.schemeBody().method():
            method_list.append(self.visit(method))

        return frog_ast.Scheme(
            imports,
            name,
            param_list,
            primitive_name,
            field_list,
            requirement_list,
            method_list,
        )


class _GameASTGenerator(_SharedAST, GameVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: GameParser.ProgramContext) -> frog_ast.GameFile:
        imports = [self.visit(im) for im in ctx.moduleImport()]
        game1: frog_ast.Game = self.visit(ctx.game()[0])
        game2: frog_ast.Game = self.visit(ctx.game()[1])
        return frog_ast.GameFile(
            imports, (game1, game2), ctx.gameExport().ID().getText()
        )


class _ProofASTGenerator(_SharedAST, ProofVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: ProofParser.ProgramContext) -> frog_ast.ProofFile:
        game_list = []
        for i in range(ctx.proofHelpers().getChildCount()):
            game_list.append(self.visit(ctx.proofHelpers().getChild(i)))

        proof = ctx.proof()
        lets = []
        if proof.lets():
            for let in proof.lets().field():
                lets.append(self.visit(let))

        assumptions = []
        max_calls = None
        if proof.assumptions():
            for assumption in proof.assumptions().parameterizedGame():
                assumptions.append(self.visit(assumption))
            if proof.assumptions().CALLS():
                max_calls = self.visit(proof.assumptions().expression())
        return frog_ast.ProofFile(
            [self.visit(im) for im in ctx.moduleImport()],
            game_list,
            lets,
            assumptions,
            max_calls,
            self.visit(proof.theorem().parameterizedGame()),
            self.visit(proof.gameList()),
        )

    def visitParameterizedGame(
        self, ctx: ProofParser.ParameterizedGameContext
    ) -> frog_ast.ParameterizedGame:
        return frog_ast.ParameterizedGame(
            ctx.ID().getText(), self.visit(ctx.argList()) if ctx.argList() else []
        )

    def visitReduction(self, ctx: ProofParser.ReductionContext) -> frog_ast.Reduction:
        return frog_ast.Reduction(
            _parse_game_body(self.visit, ctx),
            self.visit(ctx.parameterizedGame()),
            self.visit(ctx.gameAdversary().parameterizedGame()),
        )

    def visitGameList(
        self, ctx: ProofParser.GameListContext
    ) -> list[frog_ast.ProofStep]:
        steps = []
        for child in ctx.getChildren():
            if child.getText() == ";":
                continue
            steps.append(self.visit(child))
        return steps

    def visitReductionStep(
        self, ctx: ProofParser.ReductionStepContext
    ) -> frog_ast.ProofStep:
        return frog_ast.Step(
            self.visit(ctx.concreteGame()),
            self.visit(ctx.parameterizedGame()),
            self.visit(ctx.gameAdversary().parameterizedGame()),
        )

    def visitConcreteGame(
        self, ctx: ProofParser.ConcreteGameContext
    ) -> frog_ast.ConcreteGame:
        return frog_ast.ConcreteGame(
            self.visit(ctx.parameterizedGame()), ctx.ID().getText()
        )

    def visitStepAssumption(
        self, ctx: ProofParser.StepAssumptionContext
    ) -> frog_ast.StepAssumption:
        return frog_ast.StepAssumption(self.visit(ctx.expression()))

    def visitRegularStep(
        self, ctx: ProofParser.RegularStepContext
    ) -> frog_ast.ProofStep:
        return frog_ast.Step(
            self.visit(ctx.getChild(0)),
            None,
            self.visit(ctx.gameAdversary().parameterizedGame()),
        )

    def visitInduction(self, ctx: ProofParser.InductionContext) -> frog_ast.Induction:
        return frog_ast.Induction(
            ctx.ID().getText(),
            self.visit(ctx.integerExpression()[0]),
            self.visit(ctx.integerExpression()[1]),
            self.visit(ctx.gameList()),
        )


def _parse_game_body(
    visit: Type[PrimitiveVisitor.visit], ctx: ProofParser.GameContext
) -> frog_ast.GameBody:
    name: str = ctx.ID().getText()
    param_list: list[frog_ast.Parameter] = (
        visit(ctx.paramList()) if ctx.paramList() else []
    )
    field_list: list[frog_ast.Field] = []
    if ctx.gameBody().field():
        for field in ctx.gameBody().field():
            field_list.append(visit(field))
    methods: list[frog_ast.Method] = []
    if ctx.gameBody().method():
        for method in ctx.gameBody().method():
            methods.append(visit(method))

    phase_list: list[frog_ast.Phase] = []
    if ctx.gameBody().gamePhase():
        for phase in ctx.gameBody().gamePhase():
            phase_list.append(visit(phase))

    return (name, param_list, field_list, methods, phase_list)


def _get_parser(
    input_: str,
    lexer_functor: type[PrimitiveLexer],
    parser_functor: type[PrimitiveParser],
) -> PrimitiveParser:
    input_stream: InputStream | FileStream
    if os.path.isfile(input_):
        input_stream = FileStream
    else:
        input_stream = InputStream
    lexer = lexer_functor(input_stream(input_))
    return parser_functor(CommonTokenStream(lexer))


def parse_primitive_file(primitive: str) -> frog_ast.Primitive:
    ast: frog_ast.Primitive = _PrimitiveASTGenerator().visit(
        _get_parser(primitive, PrimitiveLexer, PrimitiveParser).program()
    )
    return ast


def parse_scheme_file(scheme: str) -> frog_ast.Scheme:
    ast: frog_ast.Scheme = _SchemeASTGenerator().visit(
        _get_parser(scheme, SchemeLexer, SchemeParser).program()
    )
    return ast


def parse_expression(expression: str) -> frog_ast.Expression:
    ast: frog_ast.Expression = _SharedAST().visit(
        _get_parser(expression, GameLexer, GameParser).expression()
    )
    return ast


def parse_game_file(game_file: str) -> frog_ast.GameFile:
    ast: frog_ast.GameFile = _GameASTGenerator().visit(
        _get_parser(game_file, GameLexer, GameParser).program()
    )
    return ast


def parse_proof_file(proof_file: str) -> frog_ast.ProofFile:
    ast: frog_ast.ProofFile = _ProofASTGenerator().visit(
        _get_parser(proof_file, ProofLexer, ProofParser).program()
    )
    return ast


def parse_game(game: str) -> frog_ast.Game:
    ast: frog_ast.Game = _SharedAST().visit(
        _get_parser(game, GameLexer, GameParser).game()
    )
    return ast


def parse_reduction(reduction: str) -> frog_ast.Reduction:
    ast: frog_ast.Reduction = _ProofASTGenerator().visit(
        _get_parser(reduction, ProofLexer, ProofParser).reduction()
    )
    return ast


def parse_method(method: str) -> frog_ast.Method:
    ast: frog_ast.Method = _SharedAST().visit(
        _get_parser(method, GameLexer, GameParser).method()
    )
    return ast
