from enum import Enum
from typing import Optional


class ASTNode():
    pass


class Expression(ASTNode):
    pass


class Statement(ASTNode):
    pass


class BasicTypes(Enum):
    SET = 'Set'
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


class ArrayType(Type):
    def __init__(self, element_type: BasicTypes, count: int) -> None:
        super().__init__(BasicTypes.OTHER)
        self.element_type = element_type
        self.count = count

    def _get_string_description(self) -> str:
        return f'Array<{self.element_type}, {self.count}>'


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


class BinaryOperation(Expression):
    def __init__(self, operator: BinaryOperators, left_expression: Expression, right_expression: Expression) -> None:
        self.operator = operator
        self.left_expression = left_expression
        self.right_expression = right_expression

    def __str__(self) -> str:
        return f'{self.left_expression} {self.operator.value} {self.right_expression}'


class BitStringType(Type):
    def __init__(self, parameterization: Optional[Expression] = None) -> None:
        super().__init__(BasicTypes.OTHER)
        self.parameterization = parameterization

    def _get_string_description(self) -> str:
        return f'BitString{"" if not self.parameterization else f"<{self.parameterization}>"}'


class Field(ASTNode):
    def __init__(self, the_type: ASTNode, name: str, value: Optional[Expression]) -> None:
        self.type = the_type
        self.name = name
        self.value = value

    def __str__(self) -> str:
        return f'{self.type} {self.name} = {self.value};'


class Parameter(ASTNode):
    def __init__(self, the_type: ASTNode, name: str) -> None:
        self.type = the_type
        self.name = name

    def __str__(self) -> str:
        return f'{self.type} {self.name}'


class MethodSignature(ASTNode):
    def __init__(self, name: str, return_type: ASTNode, parameters: list[Parameter]) -> None:
        self.name = name
        self.return_type = return_type
        self.parameters = parameters

    def __str__(self) -> str:
        parameter_list_string = ', '.join(
            str(param) for param in self.parameters) if self.parameters else ''
        return f'{self.return_type} {self.name}({parameter_list_string})'


class Primitive(ASTNode):
    def __init__(
            self, name: str, parameters: list[Parameter],
            fields: Optional[list[Field]] = None, methods: Optional[list[MethodSignature]] = None) -> None:
        self.name = name
        self.parameters = parameters
        self.fields = fields or []
        self.methods = methods or []

    def __str__(self) -> str:
        parameter_list_string = ', '.join(
            str(param) for param in self.parameters) if self.parameters else ''

        output_string = f"Primitive {self.name}({parameter_list_string}) {{\n"
        for field in self.fields:
            output_string += f'  {field}\n'
        output_string += '\n'
        for method in self.methods:
            output_string += f'  {method};\n'
        output_string += "}"
        return output_string


class ProductType(Type):
    def __init__(self, types: list[Type]) -> None:
        super().__init__(BasicTypes.OTHER)
        self.types = types

    def _get_string_description(self) -> str:
        return ' * '.join(str(individualType) for individualType in self.types)


class UserType(Type):
    def __init__(self, names: list[str]) -> None:
        super().__init__(BasicTypes.OTHER)
        self.names = names

    def _get_string_description(self) -> str:
        return '.'.join(name for name in self.names)


class FuncCall(Expression):
    def __init__(self, func: Expression, args: list[Expression]) -> None:
        self.func = func
        self.args = args

    def __str__(self) -> str:
        arg_str = ', '.join(str(arg) for arg in self.args)
        return f'{self.func}({arg_str})'


class Variable(Expression):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name


class Tuple(Expression):
    def __init__(self, values: list[Expression]) -> None:
        self.values = values

    def __str__(self) -> str:
        return f'[{", ".join(str(value) for value in self.values)}]'


class ReturnStatement(Statement):
    def __init__(self, expression: Expression):
        self.expression = expression

    def __str__(self) -> str:
        return f'return {self.expression};'


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


class FieldAccess(Expression):
    def __init__(self, the_object: Expression, name: str) -> None:
        self.the_object = the_object
        self.name = name

    def __str__(self) -> str:
        return f'{self.the_object}.{self.name}'


class ArrayAccess(Expression):
    def __init__(self, the_array: Expression, index: Expression) -> None:
        self.the_array = the_array
        self.index = index

    def __str__(self) -> str:
        return f'{self.the_array}[{self.index}]'


class Slice(Expression):
    def __init__(self, the_array: Expression, start: Expression, end: Expression) -> None:
        self.the_array = the_array
        self.start = start
        self.end = end

    def __str__(self) -> str:
        return f'{self.the_array}[{self.start}:{self.end}]'


class VariableDeclaration(Statement):
    def __init__(self, the_type: Type, name: str) -> None:
        self.the_type = the_type
        self.name = name

    def __str__(self) -> str:
        return f'{self.the_type} {self.name};'


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


class Sample(Statement):
    def __init__(self, the_type: Optional[Type], var: Expression, sampled_from: Expression) -> None:
        self.the_type = the_type
        self.var = var
        self.sampled_from = sampled_from

    def __str__(self) -> str:
        return (f'{self.the_type} ' if self.the_type else '') + f'{self.var} <- {self.sampled_from};'


class Assignment(Statement):
    def __init__(self, the_type: Optional[Type], var: Expression, value: Expression) -> None:
        self.the_type = the_type
        self.var = var
        self.value = value

    def __str__(self) -> str:
        return (f'{self.the_type} ' if self.the_type else '') + f'{self.var} = {self.value};'


class Integer(Expression):
    def __init__(self, num: int):
        self.num = num

    def __str__(self) -> str:
        return str(self.num)


class BinaryNum(Expression):
    def __init__(self, num: int):
        self.num = num

    def __str__(self) -> str:
        return bin(self.num)


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


class Import(ASTNode):
    def __init__(self, filename: str, rename: Optional[str]) -> None:
        self.filename = filename
        self.rename = rename

    def __str__(self) -> str:
        return f"import '{self.filename}'" + (f' as {self.rename}' if self.rename else '') + ';'


class Scheme(ASTNode):
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
        parameter_list_string = ', '.join(
            str(param) for param in self.parameters) if self.parameters else ''
        output_string = imports_string + \
            f'Scheme {self.name}({parameter_list_string}) extends {self.primitive_name} {{\n'
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
