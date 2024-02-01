from __future__ import annotations
from enum import Enum
from abc import ABC, abstractmethod
from typing import Optional, TypeAlias, Sequence


class FileType(Enum):
    PRIMITIVE = "primitive"
    SCHEME = "scheme"
    GAME = "game"
    PROOF = "proof"


class ASTNode(ABC):
    def __eq__(self, other: object) -> bool:
        if self is other:
            return True

        if type(self) is not type(other):
            return False

        # Compare all attributes
        return all(
            getattr(self, attr) == getattr(other, attr) for attr in self.__dict__
        )


Namespace: TypeAlias = dict[str, Optional[ASTNode]]


class Root(ASTNode):
    @abstractmethod
    def get_export_name(self) -> str:
        pass


class Expression(ASTNode):
    pass


class Statement(ASTNode):
    pass


class Type(ASTNode, ABC):
    pass


class IntType(Type):
    def __init__(self) -> None:
        pass

    def __str__(self) -> str:
        return "Int"


class BoolType(Type):
    def __init__(self) -> None:
        pass

    def __str__(self) -> str:
        return "Bool"


class Void(Type):
    def __init__(self) -> None:
        pass

    def __str__(self) -> str:
        return "Void"


class ArrayType(Type):
    def __init__(self, element_type: Type, count: Expression) -> None:
        self.element_type = element_type
        self.count = count

    def __str__(self) -> str:
        return f"Array<{self.element_type}, {self.count}>"


class MapType(Type):
    def __init__(self, key_type: Type, value_type: Type) -> None:
        self.key_type = key_type
        self.value_type = value_type

    def __str__(self) -> str:
        return f"Map<{self.key_type}, {self.value_type}>"


class SetType(Type):
    def __init__(self, parameterization: Optional[Expression] = None) -> None:
        self.parameterization = parameterization

    def __str__(self) -> str:
        return f'Set{"" if not self.parameterization else f"<{self.parameterization}>"}'


class BitStringType(Type):
    def __init__(self, parameterization: Optional[Expression] = None) -> None:
        self.parameterization = parameterization

    def __str__(self) -> str:
        return f'BitString{"" if not self.parameterization else f"<{self.parameterization}>"}'


class OptionalType(Type):
    def __init__(self, the_type: Type) -> None:
        self.the_type = the_type

    def __str__(self) -> str:
        return f"{self.the_type}?"


class BinaryOperators(Enum):
    EQUALS = "=="
    NOTEQUALS = "!="
    GT = ">"
    LT = "<"
    GEQ = ">="
    LEQ = "<="

    AND = "&&"
    SUBSETS = "subsets"
    IN = "in"
    OR = "||"
    UNION = "union"
    SETMINUS = "\\"

    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"


class UnaryOperators(Enum):
    NOT = "!"
    SIZE = "|"


class BinaryOperation(Expression):
    def __init__(
        self,
        operator: BinaryOperators,
        left_expression: Expression,
        right_expression: Expression,
    ) -> None:
        self.operator = operator
        self.left_expression = left_expression
        self.right_expression = right_expression

    def __str__(self) -> str:
        return f"{self.left_expression} {self.operator.value} {self.right_expression}"


class UnaryOperation(Expression):
    def __init__(self, operator: UnaryOperators, expression: Expression) -> None:
        self.operator = operator
        self.expression = expression

    def __str__(self) -> str:
        if self.operator == UnaryOperators.NOT:
            return f"!({self.expression})"
        if self.operator == UnaryOperators.SIZE:
            return f"|{self.expression}|"
        return "UNDEFINED UNARY OPERATOR"


class Set(Expression):
    def __init__(self, elements: list[Expression]) -> None:
        self.elements = elements

    def __str__(self) -> str:
        elements_string = (
            ", ".join(str(element) for element in self.elements)
            if self.elements
            else ""
        )
        return f"{{{elements_string}}}"


class Field(ASTNode):
    def __init__(self, the_type: Type, name: str, value: Optional[Expression]) -> None:
        self.type = the_type
        self.name = name
        self.value = value

    def __str__(self) -> str:
        if self.value:
            return f"{self.type} {self.name} = {self.value};"
        return f"{self.type} {self.name};"


class Parameter(ASTNode):
    def __init__(self, the_type: Type, name: str) -> None:
        self.type = the_type
        self.name = name

    def __str__(self) -> str:
        return f"{self.type} {self.name}"


class MethodSignature(ASTNode):
    def __init__(
        self, name: str, return_type: Type, parameters: list[Parameter]
    ) -> None:
        self.name = name
        self.return_type = return_type
        self.parameters = parameters

    def __str__(self) -> str:
        return (
            f"{self.return_type} {self.name}({_parameter_list_string(self.parameters)})"
        )


class Primitive(Root):
    def __init__(
        self,
        name: str,
        parameters: list[Parameter],
        fields: list[Field],
        methods: list[MethodSignature],
    ) -> None:
        self.name = name
        self.parameters = parameters
        self.fields = fields
        self.methods = methods

    def __str__(self) -> str:
        output_string = (
            f"Primitive {self.name}({_parameter_list_string(self.parameters)}) {{\n"
        )
        for field in self.fields:
            output_string += f"{field}\n"
        output_string += "\n"
        for method in self.methods:
            output_string += f"{method};\n"
        output_string += "}"
        return pretty_print(output_string)

    def get_export_name(self) -> str:
        return self.name


class FuncCall(Expression, Statement):
    def __init__(self, func: Expression, args: list[Expression]) -> None:
        self.func = func
        self.args = args

    def __str__(self) -> str:
        arg_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.func}({arg_str})"


class Variable(Expression, Type):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name


class Tuple(Expression):
    def __init__(self, values: list[Expression]) -> None:
        self.values = values

    def __str__(self) -> str:
        return f'[{", ".join(str(value) for value in self.values)}]'


class ReturnStatement(Statement):
    def __init__(self, expression: Expression):
        self.expression = expression

    def __str__(self) -> str:
        return f"return {self.expression};"


class Block(Statement):
    def __init__(self, statements: Sequence[Statement]):
        self.statements = statements

    def __str__(self) -> str:
        return "\n".join(str(statement) for statement in self.statements) + "\n"

    def __add__(self, other: Block) -> Block:
        return Block(list(self.statements) + list(other.statements))


class IfStatement(Statement):
    def __init__(self, conditions: list[Expression], blocks: list[Block]):
        self.conditions = conditions
        self.blocks = blocks

    def __str__(self) -> str:
        output_string = ""
        for i, condition in enumerate(self.conditions):
            if i == 0:
                output_string += f"if ({condition}) {{\n"
            else:
                output_string += f"}} else if ({condition}) {{\n"
            output_string += str(self.blocks[i])

        if self.has_else_block():
            output_string += f"}} else {{\n{self.blocks[-1]}"

        output_string += "}\n"

        return output_string

    def has_else_block(self) -> bool:
        return len(self.blocks) > len(self.conditions)


class FieldAccess(Expression, Type):
    def __init__(self, the_object: Expression, name: str) -> None:
        self.the_object = the_object
        self.name = name

    def __str__(self) -> str:
        return f"{self.the_object}.{self.name}"


class ArrayAccess(Expression):
    def __init__(self, the_array: Expression, index: Expression) -> None:
        self.the_array = the_array
        self.index = index

    def __str__(self) -> str:
        return f"{self.the_array}[{self.index}]"


class Slice(Expression):
    def __init__(
        self, the_array: Expression, start: Expression, end: Expression
    ) -> None:
        self.the_array = the_array
        self.start = start
        self.end = end

    def __str__(self) -> str:
        return f"{self.the_array}[{self.start} : {self.end}]"


class VariableDeclaration(Statement):
    def __init__(self, the_type: Type, name: str) -> None:
        self.the_type = the_type
        self.name = name

    def __str__(self) -> str:
        return f"{self.the_type} {self.name};"


class NumericFor(Statement):
    def __init__(self, name: str, start: Expression, end: Expression, block: Block):
        self.name = name
        self.start = start
        self.end = end
        self.block = block

    def __str__(self) -> str:
        return (
            f"for (Int {self.name} = {self.start} to {self.end}) {{\n{self.block}\n}}"
        )


class GenericFor(Statement):
    def __init__(self, var_type: Type, var_name: str, over: Expression, block: Block):
        self.var_type = var_type
        self.var_name = var_name
        self.over = over
        self.block = block

    def __str__(self) -> str:
        output_string = f"for ({self.var_type} {self.var_name} in {self.over}) {{\n"
        output_string += str(self.block)
        output_string += "}"
        return output_string


class Sample(Statement):
    def __init__(
        self, the_type: Optional[Type], var: Expression, sampled_from: Expression
    ) -> None:
        self.the_type = the_type
        self.var = var
        self.sampled_from = sampled_from

    def __str__(self) -> str:
        return (
            f"{self.the_type} " if self.the_type else ""
        ) + f"{self.var} <- {self.sampled_from};"


class Assignment(Statement):
    def __init__(
        self, the_type: Optional[Type], var: Expression, value: Expression
    ) -> None:
        self.the_type = the_type
        self.var = var
        self.value = value

    def __str__(self) -> str:
        return (
            f"{self.the_type} " if self.the_type else ""
        ) + f"{self.var} = {self.value};"


class Integer(Expression):
    def __init__(self, num: int) -> None:
        self.num = num

    def __str__(self) -> str:
        return str(self.num)


class Boolean(Expression):
    def __init__(self, the_bool: bool) -> None:
        self.bool = the_bool

    def __str__(self) -> str:
        return str(self.bool).lower()


class ASTNone(Expression):
    def __init__(self) -> None:
        pass

    def __str__(self) -> str:
        return "None"


class BinaryNum(Expression):
    def __init__(self, num: int):
        self.num = num

    def __str__(self) -> str:
        return bin(self.num)


class Method(ASTNode):
    def __init__(self, signature: MethodSignature, block: Block) -> None:
        self.signature = signature
        self.block = block

    def __str__(self) -> str:
        output_string = f"{self.signature} {{\n"
        output_string += "}\n"
        return f"{self.signature} {{ \n{self.block}\n}}"


class Import(ASTNode):
    def __init__(self, filename: str, rename: Optional[str]) -> None:
        self.filename = filename
        self.rename = rename

    def __str__(self) -> str:
        return (
            f"import '{self.filename}'"
            + (f" as {self.rename}" if self.rename else "")
            + ";"
        )


class Scheme(Root):
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        imports: list[Import],
        name: str,
        parameters: list[Parameter],
        primitive_name: str,
        fields: list[Field],
        requirements: list[Expression],
        methods: list[Method],
    ) -> None:
        self.name = name
        self.parameters = parameters
        self.primitive_name = primitive_name
        self.fields = fields
        self.requirements = requirements
        self.methods = methods
        self.imports = imports

    def __str__(self) -> str:
        imports_string = ("\n".join(str(im) for im in self.imports)) + "\n\n"
        output_string = (
            imports_string
            + f"Scheme {self.name}({_parameter_list_string(self.parameters)}) extends {self.primitive_name} {{\n"
        )
        for requirement in self.requirements:
            output_string += f"requires {requirement};\n"
        output_string += "\n"
        for field in self.fields:
            output_string += f"{field}\n"
        output_string += "\n"
        for method in self.methods:
            output_string += f"{method}\n"
        output_string += "}"
        return pretty_print(output_string)

    def get_export_name(self) -> str:
        return self.name


class Phase(ASTNode):
    def __init__(self, oracles: list[str], methods: list[Method]):
        self.oracles = oracles
        self.methods = methods

    def __str__(self) -> str:
        output_string = "Phase {\n"
        output_string += "\n".join(f"{method}" for method in self.methods)
        oracle_list_str = ", ".join(self.oracles) if self.oracles else ""
        output_string += f"oracles: [{oracle_list_str}];"
        output_string += "}"
        return output_string


GameBody: TypeAlias = tuple[
    str, list[Parameter], list[Field], list[Method], list[Phase]
]


class Game(ASTNode):
    def __init__(self, body: GameBody) -> None:
        self.name = body[0]
        self.parameters = body[1]
        self.fields = body[2]
        self.methods = body[3]
        self.phases = body[4]

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Game):
            return False
        return (
            self.parameters == __value.parameters
            and self.fields == __value.fields
            and self.methods == __value.methods
            and self.phases == __value.phases
        )

    def __str__(self) -> str:
        output_string = f"{self._get_signature()}\n"
        for field in self.fields:
            output_string += f"{field}\n"
        output_string += "\n"
        for method in self.methods:
            output_string += f"{method}\n"
        if self.phases:
            for phase in self.phases:
                output_string += f"{phase}\n"
        output_string += "}"
        return pretty_print(output_string)

    def _get_signature(self) -> str:
        return f"Game {self.name}({_parameter_list_string(self.parameters)}) {{"

    def get_method(self, name: str) -> Method:
        for method in self.methods:
            if method.signature.name == name:
                return method

        raise ValueError(f"No method with name {name} for game {self.name}")

    def has_method(self, name: str) -> bool:
        return any(method.signature.name == name for method in self.methods)


class ParameterizedGame(Expression):
    def __init__(self, name: str, args: list[Expression]):
        self.name = name
        self.args = args

    def __str__(self) -> str:
        arg_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({arg_str})"


class ConcreteGame(Expression):
    def __init__(self, game: ParameterizedGame, which: str):
        self.game = game
        self.which = which

    def __str__(self) -> str:
        return f"{self.game}.{self.which}"


class Reduction(Game):
    def __init__(
        self, body: GameBody, to_use: ParameterizedGame, play_against: ParameterizedGame
    ) -> None:
        super().__init__(body)
        self.to_use = to_use
        self.play_against = play_against

    def _get_signature(self) -> str:
        return pretty_print(
            f"Reduction {self.name}("
            f"{_parameter_list_string(self.parameters)}"
            f") compose {self.to_use} against {self.play_against}.Adversary {{"
        )


class GameFile(Root):
    def __init__(
        self, imports: list[Import], games: tuple[Game, Game], name: str
    ) -> None:
        self.imports = imports
        self.games = games
        self.name = name

    def __str__(self) -> str:
        output_string = ("\n".join(str(im) for im in self.imports)) + "\n\n"
        output_string += f"{self.games[0]}\n\n{self.games[1]}\n\n"
        output_string += f"export as {self.name};"
        return output_string

    def get_export_name(self) -> str:
        return self.name

    def get_game(self, name: str) -> Game:
        if self.games[0].name == name:
            return self.games[0]
        if self.games[1].name == name:
            return self.games[1]
        raise ValueError(f"No game found with name {name}")


class Step(ASTNode):
    def __init__(
        self,
        challenger: ConcreteGame | ParameterizedGame,
        reduction: Optional[ParameterizedGame],
        adversary: ParameterizedGame,
    ):
        self.challenger = challenger
        self.reduction = reduction
        self.adversary = adversary

    def __str__(self) -> str:
        if self.reduction:
            return f"{self.challenger} compose {self.reduction} against {self.adversary}.Adversary;"
        return f"{self.challenger} against {self.adversary}.Adversary;"


class StepAssumption(ASTNode):
    def __init__(self, expression: Expression) -> None:
        self.expression = expression

    def __str__(self) -> str:
        return f"assume {self.expression};"


class Induction(ASTNode):
    def __init__(
        self,
        name: str,
        start: Expression,
        end: Expression,
        steps: list[Step | StepAssumption],
    ):
        self.name = name
        self.start = start
        self.end = end
        self.steps = steps

    def __str__(self) -> str:
        output_string = f"induction({self.name} from {self.start} to {self.end}) {{\n"
        output_string += "\n".join(f"{  step}" for step in self.steps)
        output_string += "\n}\n"
        return output_string


ProofStep: TypeAlias = Step | Induction | StepAssumption


class ProofFile(Root):
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        imports: list[Import],
        helpers: list[Game],
        lets: list[Field],
        assumptions: list[ParameterizedGame],
        max_calls: Optional[Variable],
        theorem: ParameterizedGame,
        steps: list[ProofStep],
    ) -> None:
        self.imports = imports
        self.helpers = helpers
        self.lets = lets
        self.max_calls = max_calls
        self.assumptions = assumptions
        self.theorem = theorem
        self.steps = steps

    def __str__(self) -> str:
        output_string = ("\n".join(str(im) for im in self.imports)) + "\n\n"
        output_string += ("\n".join(str(game) for game in self.helpers)) + "\n\n"

        output_string += "proof:\n"
        output_string += "let:\n"
        for let in self.lets:
            output_string += f"  {let}\n"

        output_string += "\nassume:\n"
        for assumption in self.assumptions:
            output_string += f"  {assumption};\n"

        if self.max_calls:
            output_string += f"  calls <= {self.max_calls};\n"
        output_string += f"theorem:\n  {self.theorem};\n"
        output_string += "games:\n"
        for step in self.steps:
            output_string += f"  {step}\n"
        return output_string

    def get_export_name(self) -> str:
        # We should never be proving more than one thing, so this doesn't need to be unique.
        return "Proof"


def _parameter_list_string(parameters: list[Parameter]) -> str:
    return ", ".join(str(param) for param in parameters) if parameters else ""


def pretty_print(program: str) -> str:
    lines = program.split("\n")
    indent = 0
    output_string = ""
    for line in lines:
        if line == "":
            continue
        if "}" in line:
            indent -= 1
        output_string += ("  " * indent) + line + "\n"
        if "{" in line:
            indent += 1
    return output_string


def expand_tuple_type(the_type: BinaryOperation) -> list[Type]:
    unfolded_types: list[Type] = []
    expanded_type: Type | Expression = the_type
    while isinstance(expanded_type, BinaryOperation):
        left_expr = expanded_type.left_expression
        assert isinstance(left_expr, Type)
        unfolded_types.append(left_expr)
        expanded_type = expanded_type.right_expression
    assert isinstance(expanded_type, Type)
    unfolded_types.append(expanded_type)
    return unfolded_types
