from enum import Enum


class ASTNode():
    pass


class Expression(ASTNode):
    pass


class BasicTypes(Enum):
    SET = 'Set'
    BOOL = 'Bool'
    INT = 'Int'
    OTHER = 'Other'


class Type(ASTNode):
    def __init__(self, basic_type):
        self.optional = False  # May be modified when AST is being generated
        self.basic_type = basic_type

    def __str__(self):
        type_name = self._get_string_description()
        if self.optional:
            type_name += '?'
        return type_name

    def _get_string_description(self):
        return str(self.basic_type.value)


class ArrayType(Type):
    def __init__(self, element_type, count):
        super().__init__(BasicTypes.OTHER)
        self.element_type = element_type
        self.count = count

    def _get_string_description(self):
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
    def __init__(self, operator, left_expression, right_expression):
        self.operator = operator
        self.left_expression = left_expression
        self.right_expression = right_expression

    def __str__(self):
        return f'{self.left_expression} {self.operator.value} {self.right_expression}'


class BitStringType(Type):
    def __init__(self, parameterization=None):
        super().__init__(BasicTypes.OTHER)
        self.parameterization = parameterization

    def _get_string_description(self):
        return f'BitString{"" if not self.parameterization else f"<{self.parameterization}>"}'


class Field(ASTNode):
    def __init__(self, the_type, name, value):
        self.type = the_type
        self.name = name
        self.value = value

    def __str__(self):
        return f'{self.type} {self.name} = {self.value};'


class Parameter(ASTNode):
    def __init__(self, the_type, name):
        self.type = the_type
        self.name = name

    def __str__(self):
        return f'{self.type} {self.name}'


class MethodSignature(ASTNode):
    def __init__(self, name, return_type, parameters):
        self.name = name
        self.return_type = return_type
        self.parameters = parameters

    def __str__(self):
        parameter_list_string = ', '.join(
            str(param) for param in self.parameters) if self.parameters else ''
        return f'{self.return_type} {self.name}({parameter_list_string});'


class Primitive(ASTNode):
    def __init__(self, name, parameters, fields=None, methods=None):
        self.name = name
        self.parameters = parameters
        self.fields = fields or []
        self.methods = methods or []

    def __str__(self):
        parameter_list_string = ', '.join(
            str(param) for param in self.parameters) if self.parameters else ''

        output_string = f"Primitive {self.name}({parameter_list_string}) {{\n"
        for field in self.fields:
            output_string += f'  {field}\n'
        output_string += '\n'
        for method in self.methods:
            output_string += f'  {method}\n'
        output_string += "}"
        return output_string


class ProductType(Type):
    def __init__(self, types):
        super().__init__(BasicTypes.OTHER)
        self.types = types

    def _get_string_description(self):
        return ' * '.join(str(individualType) for individualType in self.types)


class UserType(Type):
    def __init__(self, name):
        super().__init__(BasicTypes.OTHER)
        self.name = name

    def _get_string_description(self):
        return self.name


class VariableExpression(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return str(self.name)