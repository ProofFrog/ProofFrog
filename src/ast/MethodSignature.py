from .ASTNode import ASTNode

class MethodSignature(ASTNode):
	def __init__(self, name, return_type, parameters):
		self.name = name
		self.return_type = return_type
		self.parameters = parameters

	def __str__(self):
		parameter_list_string = ', '.join(str(param) for param in self.parameters) if self.parameters else ''
		return f'{self.return_type} {self.name}({parameter_list_string});'