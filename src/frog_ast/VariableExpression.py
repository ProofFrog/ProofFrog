from .Expression import Expression


class VariableExpression(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return str(self.name)
