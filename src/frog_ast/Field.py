from .ASTNode import ASTNode


class Field(ASTNode):
    def __init__(self, the_type, name, value):
        self.type = the_type
        self.name = name
        self.value = value

    def __str__(self):
        return f'{self.type} {self.name} = {self.value};'
