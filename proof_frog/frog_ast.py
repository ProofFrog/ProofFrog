from __future__ import annotations
from enum import Enum
from abc import ABC, abstractmethod
from typing import Optional, TypeAlias


class FileType(Enum):
    PRIMITIVE = 'primitive'
    SCHEME = 'scheme'
    GAME = 'game'
    PROOF = 'proof'


class ASTNode(ABC):
    @abstractmethod
    def accept(self, v: Visitor) -> None:
        pass

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True

        if type(self) is not type(other):
            return False

        # Compare all attributes
        return all(getattr(self, attr) == getattr(other, attr)
                   for attr in self.__dict__)


class Root(ASTNode):
    @abstractmethod
    def get_export_name(self) -> str:
        pass


class Expression(ASTNode):
    pass


class Statement(ASTNode):
    pass


class BasicTypes(Enum):
    BOOL = 'Bool'
    INT = 'Int'
    OTHER = 'Other'


class Type(ASTNode):
    def __init__(self, basic_type: BasicTypes) -> None:
        self.optional = False  # May be modified when AST is being generated
        self.basic_type = basic_type

    def __str__(self) -> str:
        type_name = self._get_string_description()
        if self.optional:
            type_name += '?'
        return type_name

    def _get_string_description(self) -> str:
        return str(self.basic_type.value)

    def accept(self, v: Visitor) -> None:
        v.visit_type(self)


class ArrayType(Type):
    def __init__(self, element_type: BasicTypes, count: int) -> None:
        super().__init__(BasicTypes.OTHER)
        self.element_type = element_type
        self.count = count

    def _get_string_description(self) -> str:
        return f'Array<{self.element_type}, {self.count}>'

    def accept(self, v: Visitor) -> None:
        v.visit_array_type(self)


class MapType(Type):
    def __init__(self, key_type: Type, value_type: Type) -> None:
        super().__init__(BasicTypes.OTHER)
        self.key_type = key_type
        self.value_type = value_type

    def _get_string_description(self) -> str:
        return f'Map<{self.key_type}, {self.value_type}>'

    def accept(self, v: Visitor) -> None:
        v.visit_map_type(self)
        self.key_type.accept(v)
        self.value_type.accept(v)


class BinaryOperators(Enum):
    EQUALS = '=='
    NOTEQUALS = '!='
    GT = '>'
    LT = '<'
    GEQ = '>='
    LEQ = '<='

    AND = '&&'
    SUBSETS = 'subsets'
    IN = 'in'
    OR = '||'
    UNION = 'union'
    SETMINUS = '\\'

    ADD = '+'
    SUBTRACT = '-'
    MULTIPLY = '*'
    DIVIDE = '/'


class UnaryOperators(Enum):
    NOT = '!'
    SIZE = '|'


class BinaryOperation(Expression):
    def __init__(self, operator: BinaryOperators, left_expression: Expression, right_expression: Expression) -> None:
        self.operator = operator
        self.left_expression = left_expression
        self.right_expression = right_expression

    def __str__(self) -> str:
        return f'{self.left_expression} {self.operator.value} {self.right_expression}'

    def accept(self, v: Visitor) -> None:
        v.visit_binary_operation(self)
        self.left_expression.accept(v)
        self.right_expression.accept(v)


class UnaryOperation(Expression):
    def __init__(self, operator: UnaryOperators, expression: Expression) -> None:
        self.operator = operator
        self.expression = expression

    def __str__(self) -> str:
        if self.operator == UnaryOperators.NOT:
            return f'!({self.expression})'
        if self.operator == UnaryOperators.SIZE:
            return f'|{self.expression}|'
        return 'UNDEFINED UNARY OPERATOR'

    def accept(self, v: Visitor) -> None:
        v.visit_unary_operation(self)
        self.expression.accept(v)


class SetType(Type):
    def __init__(self, parameterization: Optional[Expression] = None) -> None:
        super().__init__(BasicTypes.OTHER)
        self.parameterization = parameterization

    def _get_string_description(self) -> str:
        return f'Set{"" if not self.parameterization else f"<{self.parameterization}>"}'

    def accept(self, v: Visitor) -> None:
        v.visit_set_type(self)
        if self.parameterization:
            self.parameterization.accept(v)


class Set(Expression):
    def __init__(self, elements: list[Expression]) -> None:
        self.elements = elements

    def __str__(self) -> str:
        elements_string = ', '.join(str(element) for element in self.elements) if self.elements else ''
        return f'{{{elements_string}}}'

    def accept(self, v: Visitor) -> None:
        v.visit_set(self)
        for element in self.elements:
            element.accept(v)


class BitStringType(Type):
    def __init__(self, parameterization: Optional[Expression] = None) -> None:
        super().__init__(BasicTypes.OTHER)
        self.parameterization = parameterization

    def _get_string_description(self) -> str:
        return f'BitString{"" if not self.parameterization else f"<{self.parameterization}>"}'

    def accept(self, v: Visitor) -> None:
        v.visit_bit_string_type(self)
        if self.parameterization:
            self.parameterization.accept(v)


class Field(ASTNode):
    def __init__(self, the_type: ASTNode, name: str, value: Optional[Expression]) -> None:
        self.type = the_type
        self.name = name
        self.value = value

    def __str__(self) -> str:
        if self.value:
            return f'{self.type} {self.name} = {self.value};'
        return f'{self.type} {self.name};'

    def accept(self, v: Visitor) -> None:
        v.visit_field(self)
        self.type.accept(v)
        if self.value:
            self.value.accept(v)


class Parameter(ASTNode):
    def __init__(self, the_type: ASTNode, name: str) -> None:
        self.type = the_type
        self.name = name

    def __str__(self) -> str:
        return f'{self.type} {self.name}'

    def accept(self, v: Visitor) -> None:
        v.visit_parameter(self)
        self.type.accept(v)


class MethodSignature(ASTNode):
    def __init__(self, name: str, return_type: ASTNode, parameters: list[Parameter]) -> None:
        self.name = name
        self.return_type = return_type
        self.parameters = parameters

    def __str__(self) -> str:
        return f'{self.return_type} {self.name}({_parameter_list_string(self.parameters)})'

    def accept(self, v: Visitor) -> None:
        v.visit_method_signature(self)
        self.return_type.accept(v)
        for param in self.parameters:
            param.accept(v)


class Primitive(Root):
    def __init__(
            self, name: str, parameters: list[Parameter],
            fields: list[Field], methods: list[MethodSignature]) -> None:
        self.name = name
        self.parameters = parameters
        self.fields = fields
        self.methods = methods

    def __str__(self) -> str:
        output_string = f"Primitive {self.name}({_parameter_list_string(self.parameters)}) {{\n"
        for field in self.fields:
            output_string += f'  {field}\n'
        output_string += '\n'
        for method in self.methods:
            output_string += f'  {method};\n'
        output_string += "}"
        return output_string

    def get_export_name(self) -> str:
        return self.name

    def accept(self, v: Visitor) -> None:
        v.visit_primitive(self)
        for param in self.parameters:
            param.accept(v)
        for field in self.fields:
            field.accept(v)
        for method in self.methods:
            method.accept(v)


class ProductType(Type):
    def __init__(self, types: list[Type]) -> None:
        super().__init__(BasicTypes.OTHER)
        self.types = types

    def _get_string_description(self) -> str:
        return ' * '.join(str(individualType) for individualType in self.types)

    def accept(self, v: Visitor) -> None:
        v.visit_product_type(self)
        for type_ in self.types:
            type_.accept(v)


class UserType(Type):
    def __init__(self, names: list[str]) -> None:
        super().__init__(BasicTypes.OTHER)
        self.names = names

    def _get_string_description(self) -> str:
        return '.'.join(name for name in self.names)

    def accept(self, v: Visitor) -> None:
        v.visit_user_type(self)


class FuncCallExpression(Expression):
    def __init__(self, func: Expression, args: list[Expression]) -> None:
        self.func = func
        self.args = args

    def __str__(self) -> str:
        arg_str = ', '.join(str(arg) for arg in self.args)
        return f'{self.func}({arg_str})'

    def accept(self, v: Visitor) -> None:
        v.visit_func_call_expression(self)
        self.func.accept(v)
        for arg in self.args:
            arg.accept(v)


class FuncCallStatement(Statement):
    def __init__(self, func: Expression, args: list[Expression]) -> None:
        self.func = func
        self.args = args

    def __str__(self) -> str:
        arg_str = ', '.join(str(arg) for arg in self.args)
        return f'{self.func}({arg_str});'

    def accept(self, v: Visitor) -> None:
        v.visit_func_call_statement(self)
        self.func.accept(v)
        for arg in self.args:
            arg.accept(v)


class Variable(Expression):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name

    def accept(self, v: Visitor) -> None:
        v.visit_variable(self)


class Tuple(Expression):
    def __init__(self, values: list[Expression]) -> None:
        self.values = values

    def __str__(self) -> str:
        return f'[{", ".join(str(value) for value in self.values)}]'

    def accept(self, v: Visitor) -> None:
        v.visit_tuple(self)
        for value in self.values:
            value.accept(v)


class ReturnStatement(Statement):
    def __init__(self, expression: Expression):
        self.expression = expression

    def __str__(self) -> str:
        return f'return {self.expression};'

    def accept(self, v: Visitor) -> None:
        v.visit_return_statement(self)
        self.expression.accept(v)


class IfStatement(Statement):
    def __init__(self, conditions: list[Expression], blocks: list[list[Statement]]):
        self.conditions = conditions
        self.blocks = blocks

    def __str__(self) -> str:
        output_string = ''
        for i, condition in enumerate(self.conditions):
            if i == 0:
                output_string += f'if ({condition}) {{\n'
            else:
                output_string += f'  }} else if ({condition}) {{\n'
            for statement in self.blocks[i]:
                output_string += f'      {statement}\n'

        if self.has_else_block():
            output_string += '} else {\n'
            for statement in self.blocks[-1]:
                output_string += f'{statement}\n'

        output_string += '    }\n'

        return output_string

    def has_else_block(self) -> bool:
        return len(self.blocks) > len(self.conditions)

    def accept(self, v: Visitor) -> None:
        v.visit_if_statement(self)
        for condition in self.conditions:
            condition.accept(v)
        for block in self.blocks:
            for statement in block:
                statement.accept(v)


class FieldAccess(Expression):
    def __init__(self, the_object: Expression, name: str) -> None:
        self.the_object = the_object
        self.name = name

    def __str__(self) -> str:
        return f'{self.the_object}.{self.name}'

    def accept(self, v: Visitor) -> None:
        v.visit_field_access(self)
        self.the_object.accept(v)


class ArrayAccess(Expression):
    def __init__(self, the_array: Expression, index: Expression) -> None:
        self.the_array = the_array
        self.index = index

    def __str__(self) -> str:
        return f'{self.the_array}[{self.index}]'

    def accept(self, v: Visitor) -> None:
        v.visit_array_access(self)
        self.the_array.accept(v)
        self.index.accept(v)


class Slice(Expression):
    def __init__(self, the_array: Expression, start: Expression, end: Expression) -> None:
        self.the_array = the_array
        self.start = start
        self.end = end

    def __str__(self) -> str:
        return f'{self.the_array}[{self.start}:{self.end}]'

    def accept(self, v: Visitor) -> None:
        v.visit_slice(self)
        self.the_array.accept(v)
        self.start.accept(v)
        self.end.accept(v)


class VariableDeclaration(Statement):
    def __init__(self, the_type: Type, name: str) -> None:
        self.the_type = the_type
        self.name = name

    def __str__(self) -> str:
        return f'{self.the_type} {self.name};'

    def accept(self, v: Visitor) -> None:
        v.visit_variable_declaration(self)
        self.the_type.accept(v)


class NumericFor(Statement):
    def __init__(self, name: str, start: Expression, end: Expression, statements: list[Statement]):
        self.name = name
        self.start = start
        self.end = end
        self.statements = statements

    def __str__(self) -> str:
        output_string = f'for ({BasicTypes.INT.value} {self.name} = {self.start} to {self.end}) {{\n'
        for statement in self.statements:
            output_string += f'      {statement}\n'
        output_string += '    }'
        return output_string

    def accept(self, v: Visitor) -> None:
        v.visit_numeric_for(self)
        self.start.accept(v)
        self.end.accept(v)
        for statement in self.statements:
            statement.accept(v)


class GenericFor(Statement):
    def __init__(self, var_type: Type, var_name: str, over: Expression, statements: list[Statement]):
        self.var_type = var_type
        self.var_name = var_name
        self.over = over
        self.statements = statements

    def __str__(self) -> str:
        output_string = f'for ({self.var_type} {self.var_name} in {self.over}) {{\n'
        for statement in self.statements:
            output_string += f'      {statement}\n'
        output_string += '    }'
        return output_string

    def accept(self, v: Visitor) -> None:
        v.visit_generic_for(self)
        self.var_type.accept(v)
        self.over.accept(v)
        for statement in self.statements:
            statement.accept(v)


class Sample(Statement):
    def __init__(self, the_type: Optional[Type], var: Expression, sampled_from: Expression) -> None:
        self.the_type = the_type
        self.var = var
        self.sampled_from = sampled_from

    def __str__(self) -> str:
        return (f'{self.the_type} ' if self.the_type else '') + f'{self.var} <- {self.sampled_from};'

    def accept(self, v: Visitor) -> None:
        v.visit_sample(self)
        if self.the_type:
            self.the_type.accept(v)
        self.var.accept(v)
        self.sampled_from.accept(v)


class Assignment(Statement):
    def __init__(self, the_type: Optional[Type], var: Expression, value: Expression) -> None:
        self.the_type = the_type
        self.var = var
        self.value = value

    def __str__(self) -> str:
        return (f'{self.the_type} ' if self.the_type else '') + f'{self.var} = {self.value};'

    def accept(self, v: Visitor) -> None:
        v.visit_assignment(self)
        if self.the_type:
            self.the_type.accept(v)
        self.var.accept(v)
        self.value.accept(v)


class Integer(Expression):
    def __init__(self, num: int):
        self.num = num

    def __str__(self) -> str:
        return str(self.num)

    def accept(self, v: Visitor) -> None:
        v.visit_integer(self)


class ASTNone(Expression):
    def __init__(self) -> None:
        pass

    def __str__(self) -> str:
        return 'None'

    def accept(self, v: Visitor) -> None:
        v.visit_none(self)


class BinaryNum(Expression):
    def __init__(self, num: int):
        self.num = num

    def __str__(self) -> str:
        return bin(self.num)

    def accept(self, v: Visitor) -> None:
        v.visit_binary_num(self)


class Method(Expression):
    def __init__(self, signature: MethodSignature, statements: list[Statement]) -> None:
        self.signature = signature
        self.statements = statements

    def __str__(self) -> str:
        output_string = f'{self.signature} {{\n'
        for statement in self.statements:
            output_string += f'    {statement}\n'
        output_string += '  }\n'
        return output_string

    def accept(self, v: Visitor) -> None:
        v.visit_method(self)
        self.signature.accept(v)
        for statement in self.statements:
            statement.accept(v)


class Import(ASTNode):
    def __init__(self, filename: str, rename: Optional[str]) -> None:
        self.filename = filename
        self.rename = rename

    def __str__(self) -> str:
        return f"import '{self.filename}'" + (f' as {self.rename}' if self.rename else '') + ';'

    def accept(self, v: Visitor) -> None:
        v.visit_import(self)


class Scheme(Root):
    # pylint: disable=too-many-arguments
    def __init__(self, imports: list[Import], name: str, parameters: list[Parameter],
                 primitive_name: str, fields: list[Field],
                 requirements: list[Expression], methods: list[Method]) -> None:
        self.name = name
        self.parameters = parameters
        self.primitive_name = primitive_name
        self.fields = fields
        self.requirements = requirements
        self.methods = methods
        self.imports = imports

    def __str__(self) -> str:
        imports_string = ('\n'.join(str(im) for im in self.imports)) + '\n\n'
        output_string = imports_string + \
            f'Scheme {self.name}({_parameter_list_string(self.parameters)}) extends {self.primitive_name} {{\n'
        for requirement in self.requirements:
            output_string += f'  requires {requirement};\n'
        output_string += '\n'
        for field in self.fields:
            output_string += f'  {field}\n'
        output_string += '\n'
        for method in self.methods:
            output_string += f'  {method}\n'
        output_string += '}'
        return output_string

    def get_export_name(self) -> str:
        return self.name

    def accept(self, v: Visitor) -> None:
        v.visit_scheme(self)
        for imp in self.imports:
            imp.accept(v)
        for param in self.parameters:
            param.accept(v)
        for requirement in self.requirements:
            requirement.accept(v)
        for field in self.fields:
            field.accept(v)
        for method in self.methods:
            method.accept(v)


class Phase(ASTNode):
    def __init__(self, oracles: list[str], methods: list[Method]):
        self.oracles = oracles
        self.methods = methods

    def __str__(self) -> str:
        output_string = 'Phase {\n'
        output_string += '\n'.join(f'    {method}' for method in self.methods)
        oracle_list_str = ', '.join(self.oracles) if self.oracles else ''
        output_string += f'  oracles: [{oracle_list_str}];'
        output_string += '}'
        return output_string

    def accept(self, v: Visitor) -> None:
        v.visit_phase(self)
        for method in self.methods:
            method.accept(v)


GameBody: TypeAlias = tuple[str, list[Parameter], list[Field], list[Method], list[Phase]]


class Game(ASTNode):
    # pylint: disable=too-many-arguments
    def __init__(self, body: GameBody) -> None:
        self.name = body[0]
        self.parameters = body[1]
        self.fields = body[2]
        self.methods = body[3]
        self.phases = body[4]

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Game):
            return False
        return self.parameters == __value.parameters \
            and self.fields == __value.fields \
            and self.methods == __value.methods \
            and self.phases == __value.phases

    def __str__(self) -> str:
        output_string = f'{self._get_signature()}\n'
        for field in self.fields:
            output_string += f'  {field}\n'
        output_string += '\n'
        for method in self.methods:
            output_string += f'  {method}\n'
        if self.phases:
            for phase in self.phases:
                output_string += f'  {phase}\n'
        output_string += '}'
        return output_string

    def _get_signature(self) -> str:
        return f'Game {self.name}({_parameter_list_string(self.parameters)}) {{'

    def get_method(self, name: str) -> Method:
        for method in self.methods:
            if method.signature.name == name:
                return method

        raise ValueError(f"No method with name {name} for game {self.name}")

    def accept(self, v: Visitor) -> None:
        v.visit_game(self)
        for param in self.parameters:
            param.accept(v)
        self._visit_rest(v)

    def _visit_rest(self, v: Visitor) -> None:
        for field in self.fields:
            field.accept(v)
        for method in self.methods:
            method.accept(v)
        for phase in self.phases:
            phase.accept(v)


class ParameterizedGame(ASTNode):
    def __init__(self, name: str, args: list[Expression]):
        self.name = name
        self.args = args

    def __str__(self) -> str:
        arg_str = ', '.join(str(arg) for arg in self.args)
        return f'{self.name}({arg_str})'

    def accept(self, v: Visitor) -> None:
        v.visit_parameterized_game(self)
        for arg in self.args:
            arg.accept(v)


class ConcreteGame(ASTNode):
    def __init__(self, game: ParameterizedGame, which: str):
        self.game = game
        self.which = which

    def __str__(self) -> str:
        return f'{self.game}.{self.which}'

    def accept(self, v: Visitor) -> None:
        v.visit_concrete_game(self)
        self.game.accept(v)


class Reduction(Game):
    def __init__(self, body: GameBody, to_use: ParameterizedGame, play_against: ParameterizedGame) -> None:
        super().__init__(body)
        self.to_use = to_use
        self.play_against = play_against

    def _get_signature(self) -> str:
        return (f'Reduction {self.name}('
                f'{_parameter_list_string(self.parameters)}'
                f') compose {self.to_use} against {self.play_against}.Adversary {{'
                )

    def accept(self, v: Visitor) -> None:
        v.visit_reduction(self)
        for param in self.parameters:
            param.accept(v)
        self.to_use.accept(v)
        self.play_against.accept(v)
        self._visit_rest(v)


class GameFile(Root):
    def __init__(self, imports: list[Import], games: tuple[Game, Game], name: str) -> None:
        self.imports = imports
        self.games = games
        self.name = name

    def __str__(self) -> str:
        output_string = ('\n'.join(str(im) for im in self.imports)) + '\n\n'
        output_string += f'{self.games[0]}\n\n{self.games[1]}\n\n'
        output_string += f'export as {self.name};'
        return output_string

    def get_export_name(self) -> str:
        return self.name

    def get_game(self, name: str) -> Game:
        if self.games[0].name == name:
            return self.games[0]
        if self.games[1].name == name:
            return self.games[1]
        raise ValueError(f"No game found with name {name}")

    def accept(self, v: Visitor) -> None:
        v.visit_game_file(self)
        for imp in self.imports:
            imp.accept(v)
        for game in self.games:
            game.accept(v)


class Step(ASTNode):
    def __init__(
            self, challenger: ConcreteGame | ParameterizedGame, reduction: Optional[ParameterizedGame],
            adversary: ParameterizedGame):
        self.challenger = challenger
        self.reduction = reduction
        self.adversary = adversary

    def __str__(self) -> str:
        if self.reduction:
            return f'{self.challenger} compose {self.reduction} against {self.adversary}.Adversary;'
        return f'{self.challenger} against {self.adversary}.Adversary;'

    def accept(self, v: Visitor) -> None:
        v.visit_step(self)
        self.challenger.accept(v)
        if self.reduction:
            self.reduction.accept(v)
        self.adversary.accept(v)


class Induction(ASTNode):
    def __init__(self, name: str, start: Expression, end: Expression, steps: list[Step | Induction]):
        self.name = name
        self.start = start
        self.end = end
        self.steps = steps

    def __str__(self) -> str:
        output_string = f'induction({self.name} from {self.start} to {self.end}) {{\n'
        output_string += '\n'.join(f'{  step}' for step in self.steps)
        output_string += '\n}\n'
        return output_string

    def accept(self, v: Visitor) -> None:
        v.visit_induction(self)
        self.start.accept(v)
        self.end.accept(v)
        for step in self.steps:
            step.accept(v)


ProofStep: TypeAlias = Step | Induction


class ProofFile(Root):
    # pylint: disable=too-many-arguments
    def __init__(
            self, imports: list[Import],
            helpers: list[Game],
            lets: list[Field],
            assumptions: list[ParameterizedGame], max_calls: Optional[Variable],
            theorem: ParameterizedGame, steps: list[ProofStep]) -> None:
        self.imports = imports
        self.helpers = helpers
        self.lets = lets
        self.max_calls = max_calls
        self.assumptions = assumptions
        self.theorem = theorem
        self.steps = steps

    def __str__(self) -> str:
        output_string = ('\n'.join(str(im) for im in self.imports)) + '\n\n'
        output_string += ('\n'.join(str(game) for game in self.helpers)) + '\n\n'

        output_string += 'proof:\n'
        output_string += 'let:\n'
        for let in self.lets:
            output_string += f'  {let}\n'

        output_string += '\nassume:\n'
        for assumption in self.assumptions:
            output_string += f'  {assumption};\n'

        if self.max_calls:
            output_string += f'  calls <= {self.max_calls};\n'
        output_string += f'theorem:\n  {self.theorem};\n'
        output_string += 'games:\n'
        for step in self.steps:
            output_string += f'  {step}\n'
        return output_string

    def get_export_name(self) -> str:
        # We should never be proving more than one thing, so this doesn't need to be unique.
        return 'Proof'

    def accept(self, v: Visitor) -> None:
        v.visit_proof_file(self)
        for imp in self.imports:
            imp.accept(v)
        for helper in self.helpers:
            helper.accept(v)
        for let in self.lets:
            let.accept(v)
        for assumption in self.assumptions:
            assumption.accept(v)
        if self.max_calls:
            self.max_calls.accept(v)
        self.theorem.accept(v)
        for step in self.steps:
            step.accept(v)


def _parameter_list_string(parameters: list[Parameter]) -> str:
    return ', '.join(str(param) for param in parameters) if parameters else ''


class Visitor():
    def visit_type(self, _: Type) -> None:
        pass

    def visit_array_type(self, _: ArrayType) -> None:
        pass

    def visit_map_type(self, _: MapType) -> None:
        pass

    def visit_binary_operation(self, _: BinaryOperation) -> None:
        pass

    def visit_unary_operation(self, _: UnaryOperation) -> None:
        pass

    def visit_set_type(self, _: SetType) -> None:
        pass

    def visit_set(self, _: Set) -> None:
        pass

    def visit_bit_string_type(self, _: BitStringType) -> None:
        pass

    def visit_field(self, _: Field) -> None:
        pass

    def visit_parameter(self, _: Parameter) -> None:
        pass

    def visit_method_signature(self, _: MethodSignature) -> None:
        pass

    def visit_primitive(self, _: Primitive) -> None:
        pass

    def visit_product_type(self, _: ProductType) -> None:
        pass

    def visit_user_type(self, _: UserType) -> None:
        pass

    def visit_func_call_expression(self, _: FuncCallExpression) -> None:
        pass

    def visit_func_call_statement(self, _: FuncCallStatement) -> None:
        pass

    def visit_variable(self, _: Variable) -> None:
        pass

    def visit_tuple(self, _: Tuple) -> None:
        pass

    def visit_return_statement(self, _: ReturnStatement) -> None:
        pass

    def visit_if_statement(self, _: IfStatement) -> None:
        pass

    def visit_field_access(self, _: FieldAccess) -> None:
        pass

    def visit_array_access(self, _: ArrayAccess) -> None:
        pass

    def visit_slice(self, _: Slice) -> None:
        pass

    def visit_variable_declaration(self, _: VariableDeclaration) -> None:
        pass

    def visit_numeric_for(self, _: NumericFor) -> None:
        pass

    def visit_generic_for(self, _: GenericFor) -> None:
        pass

    def visit_sample(self, _: Sample) -> None:
        pass

    def visit_assignment(self, _: Assignment) -> None:
        pass

    def visit_integer(self, _: Integer) -> None:
        pass

    def visit_none(self, _: ASTNone) -> None:
        pass

    def visit_binary_num(self, _: BinaryNum) -> None:
        pass

    def visit_method(self, _: Method) -> None:
        pass

    def visit_import(self, _: Import) -> None:
        pass

    def visit_scheme(self, _: Scheme) -> None:
        pass

    def visit_phase(self, _: Phase) -> None:
        pass

    def visit_game(self, _: Game) -> None:
        pass

    def visit_parameterized_game(self, _: ParameterizedGame) -> None:
        pass

    def visit_concrete_game(self, _: ConcreteGame) -> None:
        pass

    def visit_reduction(self, _: Reduction) -> None:
        pass

    def visit_game_file(self, _: GameFile) -> None:
        pass

    def visit_step(self, _: Step) -> None:
        pass

    def visit_induction(self, _: Induction) -> None:
        pass

    def visit_proof_file(self, _: ProofFile) -> None:
        pass


class VariableSubstitution(Visitor):
    def __init__(self, find_name: str, replace_name: str) -> None:
        self.find_name = find_name
        self.replace_name = replace_name

    def visit_variable(self, v: Variable) -> None:
        if v.name == self.find_name:
            v.name = self.replace_name
