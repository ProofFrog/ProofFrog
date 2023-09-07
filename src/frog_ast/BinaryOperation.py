from .Expression import Expression
from enum import Enum


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
    def __init__(self, operator, leftExpression, rightExpression):
        self.operator = operator
        self.leftExpression = leftExpression
        self.rightExpression = rightExpression

    def __str__(self):
        return f'{self.leftExpression} {self.operator.value} {self.rightExpression}'
