from enum import Enum
from .ASTNode import ASTNode

class BasicTypes(Enum):
	Set = 'Set'
	Bool = 'Bool'
	Int = 'Int'
	Other = 'Other'

class Type(ASTNode):
	def __init__(self, basic_type):
		self.optional = False # May be modified when AST is being generated
		self.basic_type = basic_type

	def __str__(self):
		typeName = self._get_string_description()
		if (self.optional):
			typeName += '?'
		return typeName

	def _get_string_description(self):
		return str(self.basic_type.value)