from .Type import Type, BasicTypes


class ProductType(Type):
    def __init__(self, types):
        super().__init__(BasicTypes.Other)
        self.types = types

    def _get_string_description(self):
        return ' * '.join(str(individualType) for individualType in self.types)
