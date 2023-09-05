from .ASTNode import ASTNode

class Primitive(ASTNode):
	def __init__(self, name, parameters, fields = [], methods = []):
		self.name = name
		self.parameters = parameters
		self.fields = fields
		self.methods = methods

	def __str__(self):
		parameter_list_string = ', '.join(str(param) for param in self.parameters) if self.parameters else ''
		
		output_string = f"Primitive {self.name}({parameter_list_string}) {{\n"
		for field in self.fields:
			output_string += f'  {field}\n'
		output_string += '\n'
		for method in self.methods:
			output_string += f'  {method}\n'
		output_string += "}"
		return output_string