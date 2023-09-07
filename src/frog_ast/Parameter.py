from .ASTNode import ASTNode


class Parameter(ASTNode):
    def __init__(self, the_type, name):
        self.type = the_type
        self.name = name

    def __str__(self):
        return f'{self.type} {self.name}'
