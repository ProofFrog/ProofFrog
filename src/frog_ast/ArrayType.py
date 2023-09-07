from .Type import Type, BasicTypes


class ArrayType(Type):
    def __init__(self, elementType, count):
        super().__init__(BasicTypes.Other)
        self.elementType = elementType
        self.count = count

    def _get_string_description(self):
        return f'Array<{self.elementType}, {self.count}>'
