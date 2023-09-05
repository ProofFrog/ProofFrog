from .Type import Type, BasicTypes

class BitStringType(Type):
	def __init__(self, parameterization = None):
		super().__init__(BasicTypes.Other)
		self.parameterization = parameterization

	def _get_string_description(self):
		return f'BitString{"" if not self.parameterization else f"<{self.parameterization}>"}'