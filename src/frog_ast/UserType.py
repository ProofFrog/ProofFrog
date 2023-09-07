from .Type import Type, BasicTypes


class UserType(Type):
    def __init__(self, name):
        super().__init__(BasicTypes.Other)
        self.name = name

    def _get_string_description(self):
        return self.name
