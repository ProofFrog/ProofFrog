from __future__ import annotations
import dataclasses
from enum import Enum
from abc import ABC, abstractmethod
from typing import Optional, TypeAlias, Sequence, TypeVar, Generic, Tuple as PyTuple


@dataclasses.dataclass(frozen=True)
class SourceOrigin:
    """Tracks where an AST node originated in the user's source code."""

    file: str
    line: int
    col: int
    original_text: str
    transform_chain: tuple[str, ...]


class FileType(Enum):
    PRIMITIVE = "primitive"
    SCHEME = "scheme"
    GAME = "game"
    PROOF = "proof"


class ASTNode(ABC):
    def __init__(self) -> None:
        self.line_num: int = -1
        self.column_num: int = -1
        self.origin: SourceOrigin | None = None

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True

        if type(self) is not type(other):
            return False

        # Compare all attributes
        return all(
            (
                True
                if attr in {"line_num", "column_num", "origin"}
                else getattr(self, attr) == getattr(other, attr)
            )
            for attr in self.__dict__
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
    def __str__(self) -> str:
        return "Int"


class BoolType(Type):
    def __str__(self) -> str:
        return "Bool"


class Void(Type):
    def __str__(self) -> str:
        return "Void"


class ArrayType(Type):
    def __init__(self, element_type: Type, count: Expression) -> None:
        super().__init__()
        self.element_type = element_type
        self.count = count

    def __str__(self) -> str:
        return f"Array<{self.element_type}, {self.count}>"


class MapType(Type):
    def __init__(self, key_type: Type, value_type: Type) -> None:
        super().__init__()
        self.key_type = key_type
        self.value_type = value_type

    def __str__(self) -> str:
        return f"Map<{self.key_type}, {self.value_type}>"


class SetType(Type):
    def __init__(self, parameterization: Optional[Type] = None) -> None:
        super().__init__()
        self.parameterization = parameterization

    def __str__(self) -> str:
        return f'Set{"" if not self.parameterization else f"<{self.parameterization}>"}'


class BitStringType(Type):
    def __init__(self, parameterization: Optional[Expression] = None) -> None:
        super().__init__()
        self.parameterization = parameterization

    def __str__(self) -> str:
        return f'BitString{"" if not self.parameterization else f"<{self.parameterization}>"}'


class ModIntType(Type):
    def __init__(self, modulus: Expression) -> None:
        super().__init__()
        self.modulus = modulus

    def __str__(self) -> str:
        return f"ModInt<{self.modulus}>"


class GroupType(Type):
    """The ``Group`` declaration type (like ``Int`` or ``Set``)."""

    def __str__(self) -> str:
        return "Group"


class GroupElemType(Type):
    """Element of an abelian cyclic group: ``GroupElem<G>``."""

    def __init__(self, group: Expression) -> None:
        super().__init__()
        self.group = group

    def __str__(self) -> str:
        return f"GroupElem<{self.group}>"


class ProductType(Type):
    def __init__(self, types: list[Type]) -> None:
        super().__init__()
        self.types = types

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ProductType):
            return self.types == other.types
        # ProductType([A, B]) == Tuple([A, B]) when elements match,
        # since Set field aliases produce ProductType in expression positions
        # where Tuple would normally appear.
        if isinstance(other, Tuple):
            return list(self.types) == other.values
        return False

    def __str__(self) -> str:
        return f'[{", ".join(str(t) for t in self.types)}]'


class FunctionType(Type):
    def __init__(self, domain_type: Type, range_type: Type) -> None:
        super().__init__()
        self.domain_type = domain_type
        self.range_type = range_type

    def __str__(self) -> str:
        return f"Function<{self.domain_type}, {self.range_type}>"


class OptionalType(Type):
    def __init__(self, the_type: Type) -> None:
        super().__init__()
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
    EXPONENTIATE = "^"

    def precedence(self) -> int:
        """Return precedence level (higher binds tighter)."""
        if self == BinaryOperators.EXPONENTIATE:
            return 5
        if self in (BinaryOperators.MULTIPLY, BinaryOperators.DIVIDE):
            return 4
        if self in (BinaryOperators.ADD, BinaryOperators.SUBTRACT):
            return 3
        if self in (
            BinaryOperators.EQUALS,
            BinaryOperators.NOTEQUALS,
            BinaryOperators.GT,
            BinaryOperators.LT,
            BinaryOperators.GEQ,
            BinaryOperators.LEQ,
            BinaryOperators.IN,
            BinaryOperators.SUBSETS,
        ):
            return 2
        # AND, OR, UNION, SETMINUS
        return 1


class UnaryOperators(Enum):
    NOT = "!"
    SIZE = "|"
    MINUS = "-"


class BinaryOperation(Expression, Type):
    def __init__(
        self,
        operator: BinaryOperators,
        left_expression: Expression,
        right_expression: Expression,
    ) -> None:
        super().__init__()
        self.operator = operator
        self.left_expression = left_expression
        self.right_expression = right_expression

    @staticmethod
    def _parenthesize(
        child: Expression,
        parent_prec: int,
        is_right: bool,
        right_assoc: bool = False,
    ) -> str:
        """Wrap child in parens if needed based on precedence."""
        if isinstance(child, BinaryOperation):
            child_prec = child.operator.precedence()
            if child_prec < parent_prec:
                return f"({child})"
            if child_prec == parent_prec:
                # Left-assoc: parenthesize right child at equal prec
                # Right-assoc: parenthesize left child at equal prec
                if (not right_assoc and is_right) or (right_assoc and not is_right):
                    return f"({child})"
        return str(child)

    def __str__(self) -> str:
        prec = self.operator.precedence()
        right_assoc = self.operator == BinaryOperators.EXPONENTIATE
        left = self._parenthesize(
            self.left_expression, prec, is_right=False, right_assoc=right_assoc
        )
        right = self._parenthesize(
            self.right_expression, prec, is_right=True, right_assoc=right_assoc
        )
        return f"{left} {self.operator.value} {right}"


class UnaryOperation(Expression):
    def __init__(self, operator: UnaryOperators, expression: Expression) -> None:
        super().__init__()
        self.operator = operator
        self.expression = expression

    def __str__(self) -> str:
        if self.operator == UnaryOperators.NOT:
            return f"!({self.expression})"
        if self.operator == UnaryOperators.SIZE:
            return f"|{self.expression}|"
        if self.operator == UnaryOperators.MINUS:
            return f"-{self.expression}"
        return "UNDEFINED UNARY OPERATOR"


class Set(Expression):
    def __init__(self, elements: list[Expression]) -> None:
        super().__init__()
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
        super().__init__()
        self.type = the_type
        self.name = name
        self.value = value

    def __str__(self) -> str:
        if self.value:
            return f"{self.type} {self.name} = {self.value};"
        return f"{self.type} {self.name};"


class Parameter(ASTNode):
    def __init__(self, the_type: Type, name: str) -> None:
        super().__init__()
        self.type = the_type
        self.name = name

    def __str__(self) -> str:
        return f"{self.type} {self.name}"


class MethodSignature(
    ASTNode
):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        name: str,
        return_type: Type,
        parameters: list[Parameter],
        deterministic: bool = False,
        injective: bool = False,
    ) -> None:
        super().__init__()
        self.name = name
        self.return_type = return_type
        self.parameters = parameters
        self.deterministic = deterministic
        self.injective = injective

    def __str__(self) -> str:
        modifiers = ""
        if self.deterministic:
            modifiers += "deterministic "
        if self.injective:
            modifiers += "injective "
        return (
            f"{modifiers}{self.return_type} {self.name}"
            f"({_parameter_list_string(self.parameters)})"
        )


class Primitive(Root):
    def __init__(
        self,
        name: str,
        parameters: list[Parameter],
        fields: list[Field],
        methods: list[MethodSignature],
    ) -> None:
        super().__init__()
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
        super().__init__()
        self.func = func
        self.args = args

    def __str__(self) -> str:
        arg_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.func}({arg_str})"


class Variable(Expression, Type):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def __str__(self) -> str:
        return self.name


class Tuple(Expression):
    def __init__(self, values: list[Expression]) -> None:
        super().__init__()
        self.values = values

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Tuple):
            return self.values == other.values
        if isinstance(other, ProductType):
            return self.values == list(other.types)
        return False

    def __str__(self) -> str:
        return f'[{", ".join(str(value) for value in self.values)}]'


def tuple_literal_values(node: object) -> list[Expression] | None:
    """Return the element list if *node* is a tuple literal, else ``None``.

    Set-alias fields whose type is a ``ProductType`` may carry tuple literals
    in expression positions (field initialisers, assignment RHS) as
    ``ProductType`` nodes rather than ``Tuple`` nodes, with the elements
    stored on ``.types``.  This helper hides that quirk so callers can treat
    both representations uniformly.
    """
    if isinstance(node, Tuple):
        return list(node.values)
    if isinstance(node, ProductType):
        return list(node.types)  # type: ignore[arg-type,return-value]
    return None


class ReturnStatement(Statement):
    def __init__(self, expression: Expression):
        super().__init__()
        self.expression = expression

    def __str__(self) -> str:
        return f"return {self.expression};"


class Block(Statement):
    def __init__(self, statements: Sequence[Statement]):
        super().__init__()
        self.statements = statements

    def __str__(self) -> str:
        return (
            "\n".join(
                (
                    str(statement) + ";"
                    if isinstance(statement, FuncCall)
                    else str(statement)
                )
                for statement in self.statements
            )
            + "\n"
        )

    def __add__(self, other: Block) -> Block:
        return Block(list(self.statements) + list(other.statements))


class IfStatement(Statement):
    def __init__(self, conditions: list[Expression], blocks: list[Block]):
        super().__init__()
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
        super().__init__()
        self.the_object = the_object
        self.name = name

    def __str__(self) -> str:
        return f"{self.the_object}.{self.name}"


class ArrayAccess(Expression):
    def __init__(self, the_array: Expression, index: Expression) -> None:
        super().__init__()
        self.the_array = the_array
        self.index = index

    def __str__(self) -> str:
        return f"{self.the_array}[{self.index}]"


class Slice(Expression):
    def __init__(
        self, the_array: Expression, start: Expression, end: Expression
    ) -> None:
        super().__init__()
        self.the_array = the_array
        self.start = start
        self.end = end

    def __str__(self) -> str:
        return f"{self.the_array}[{self.start} : {self.end}]"


class VariableDeclaration(Statement):
    def __init__(self, the_type: Type, name: str) -> None:
        super().__init__()
        self.type = the_type
        self.name = name

    def __str__(self) -> str:
        return f"{self.type} {self.name};"


class NumericFor(Statement):
    def __init__(self, name: str, start: Expression, end: Expression, block: Block):
        super().__init__()
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
        super().__init__()
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
        super().__init__()
        self.the_type = the_type
        self.var = var
        self.sampled_from = sampled_from

    def __str__(self) -> str:
        return (
            f"{self.the_type} " if self.the_type else ""
        ) + f"{self.var} <- {self.sampled_from};"


class UniqueSample(Statement):
    def __init__(
        self,
        the_type: Optional[Type],
        var: Expression,
        unique_set: Expression,
        sampled_from: Type,
    ) -> None:
        super().__init__()
        self.the_type = the_type
        self.var = var
        self.unique_set = unique_set
        self.sampled_from = sampled_from

    def __str__(self) -> str:
        return (
            f"{self.the_type} " if self.the_type else ""
        ) + f"{self.var} <-uniq[{self.unique_set}] {self.sampled_from};"


class Assignment(Statement):
    def __init__(
        self, the_type: Optional[Type], var: Expression, value: Expression
    ) -> None:
        super().__init__()
        self.the_type = the_type
        self.var = var
        self.value = value

    def __str__(self) -> str:
        return (
            f"{self.the_type} " if self.the_type else ""
        ) + f"{self.var} = {self.value};"


class Integer(Expression):
    def __init__(self, num: int) -> None:
        super().__init__()
        self.num = num

    def __str__(self) -> str:
        return str(self.num)


class Boolean(Expression):
    def __init__(self, the_bool: bool) -> None:
        super().__init__()
        self.bool = the_bool

    def __str__(self) -> str:
        return str(self.bool).lower()


class NoneExpression(Expression, Type):
    def __str__(self) -> str:
        return "None"


class BinaryNum(Expression):
    """A binary literal written as ``0bXYZ``.

    Carries both the integer value and the explicit bit length.  The length
    is the number of ``0``/``1`` digits after ``0b`` in the source, so
    ``0b0`` has length 1, ``0b00`` has length 2, ``0b101`` has length 3.
    Two ``BinaryNum`` nodes with the same ``num`` but different ``length``
    represent different bitstrings (they live in different ``BitString<n>``
    types).
    """

    def __init__(self, num: int, length: int):
        super().__init__()
        self.num = num
        self.length = length

    def __str__(self) -> str:
        # Render with leading zeros to preserve the explicit length.
        return "0b" + format(self.num, f"0{self.length}b")


class BitStringLiteral(Expression):
    """A bitstring literal: 0^n (all zeros) or 1^n (all ones)."""

    def __init__(self, bit: int, length: Expression) -> None:
        super().__init__()
        self.bit = bit
        self.length = length

    def __str__(self) -> str:
        if isinstance(self.length, BinaryOperation):
            return f"{self.bit}^({self.length})"
        return f"{self.bit}^{self.length}"


class GroupGenerator(Expression):
    """The canonical generator of a cyclic group: ``G.generator``."""

    def __init__(self, group: Expression) -> None:
        super().__init__()
        self.group = group

    def __str__(self) -> str:
        return f"{self.group}.generator"


class GroupOrder(Expression):
    """The order of a cyclic group: ``G.order``."""

    def __init__(self, group: Expression) -> None:
        super().__init__()
        self.group = group

    def __str__(self) -> str:
        return f"{self.group}.order"


class Method(ASTNode):
    def __init__(self, signature: MethodSignature, block: Block) -> None:
        super().__init__()
        self.signature = signature
        self.block = block

    def __str__(self) -> str:
        output_string = f"{self.signature} {{\n"
        output_string += "}\n"
        return f"{self.signature} {{ \n{self.block}\n}}"


class Import(ASTNode):
    def __init__(self, filename: str, rename: Optional[str]) -> None:
        super().__init__()
        self.filename = filename
        self.rename = rename

    def __str__(self) -> str:
        return (
            f"import '{self.filename}'"
            + (f" as {self.rename}" if self.rename else "")
            + ";"
        )


class Scheme(Root):
    # pylint: disable=too-many-positional-arguments,too-many-arguments
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
        super().__init__()
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


GameBody: TypeAlias = tuple[str, list[Parameter], list[Field], list[Method]]


class Game(ASTNode):
    def __init__(self, body: GameBody) -> None:
        super().__init__()
        self.name = body[0]
        self.parameters = body[1]
        self.fields = body[2]
        self.methods = body[3]

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Game):
            return False
        return (
            self.parameters == __value.parameters
            and self.fields == __value.fields
            and self.methods == __value.methods
        )

    def __str__(self) -> str:
        output_string = f"{self._get_signature()}\n"
        for field in self.fields:
            output_string += f"{field}\n"
        output_string += "\n"
        for method in self.methods:
            output_string += f"{method}\n"
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
        super().__init__()
        self.name = name
        self.args = args

    def __str__(self) -> str:
        arg_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({arg_str})"


class ConcreteGame(Expression):
    def __init__(self, game: ParameterizedGame, which: str):
        super().__init__()
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
        super().__init__()
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
        super().__init__()
        self.challenger = challenger
        self.reduction = reduction
        self.adversary = adversary

    def __str__(self) -> str:
        if self.reduction:
            return f"{self.challenger} compose {self.reduction} against {self.adversary}.Adversary;"
        return f"{self.challenger} against {self.adversary}.Adversary;"


class StepAssumption(ASTNode):
    def __init__(self, expression: Expression) -> None:
        super().__init__()
        self.expression = expression

    def __str__(self) -> str:
        return f"assume {self.expression};"


class Induction(ASTNode):
    def __init__(
        self,
        name: str,
        start: Expression,
        end: Expression,
        steps: list[Step | StepAssumption | Induction],
    ):
        super().__init__()
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


class Lemma(ASTNode):
    """A lemma entry: a security property proven by another proof file."""

    def __init__(self, game: ParameterizedGame, proof_path: str) -> None:
        super().__init__()
        self.game = game
        self.proof_path = proof_path

    def __str__(self) -> str:
        return f"{self.game} by '{self.proof_path}';"


class StructuralRequirement(ASTNode):
    """A structural fact declared in a proof's ``requires:`` block.

    ``kind`` is a tag naming the predicate (initially only ``"prime"``);
    ``target`` is the expression the predicate applies to (e.g. ``G.order``).
    """

    def __init__(self, kind: str, target: Expression) -> None:
        super().__init__()
        self.kind = kind
        self.target = target

    def __str__(self) -> str:
        return f"{self.target} is {self.kind}"


class ProofFile(Root):
    # pylint: disable=too-many-positional-arguments,too-many-arguments
    def __init__(
        self,
        imports: list[Import],
        helpers: list[Game],
        lets: list[Field],
        assumptions: list[ParameterizedGame],
        lemmas: list[Lemma],
        max_calls: Optional[Variable],
        theorem: ParameterizedGame,
        steps: list[ProofStep],
        requirements: Optional[list[StructuralRequirement]] = None,
    ) -> None:
        super().__init__()
        self.imports = imports
        self.helpers = helpers
        self.lets = lets
        self.sampled_let_names: set[str] = set()
        self.max_calls = max_calls
        self.assumptions = assumptions
        self.lemmas = lemmas
        self.theorem = theorem
        self.steps = steps
        self.requirements = requirements if requirements is not None else []

    def __str__(self) -> str:
        output_string = ("\n".join(str(im) for im in self.imports)) + "\n\n"
        output_string += ("\n".join(str(game) for game in self.helpers)) + "\n\n"

        output_string += "proof:\n"
        output_string += "let:\n"
        for let in self.lets:
            if let.name in self.sampled_let_names:
                output_string += f"  {let.type} {let.name} <- {let.type};\n"
            else:
                output_string += f"  {let}\n"

        output_string += "\nassume:\n"
        for assumption in self.assumptions:
            output_string += f"  {assumption};\n"

        if self.max_calls:
            output_string += f"  calls <= {self.max_calls};\n"

        if self.requirements:
            output_string += "\nrequires:\n"
            for req in self.requirements:
                output_string += f"  {req};\n"

        if self.lemmas:
            output_string += "\nlemma:\n"
            for lemma in self.lemmas:
                output_string += f"  {lemma}\n"

        output_string += f"theorem:\n  {self.theorem};\n"
        output_string += "games:\n"
        for step in self.steps:
            output_string += f"  {step}\n"
        return output_string

    def get_export_name(self) -> str:
        # We should never be proving more than one thing, so this doesn't need to be unique.
        return "Proof"


Instantiable: TypeAlias = Primitive | Scheme | Game


VT = TypeVar("VT")


class ASTMap(Generic[VT]):
    def __init__(self, identity: bool = True) -> None:
        self.__list: list[PyTuple[ASTNode, VT]] = []
        self.__identity = identity

    def __compare(self, key1: ASTNode, key2: ASTNode) -> bool:
        return (self.__identity and key1 is key2) or (
            not self.__identity and key1 == key2
        )

    def get(self, key: ASTNode) -> VT:
        for potential_key, value in self.__list:
            if self.__compare(key, potential_key):
                return value
        raise KeyError()

    def set(self, key: ASTNode, value: VT) -> None:
        for index, (potential_key, _) in enumerate(self.__list):
            if self.__compare(key, potential_key):
                self.__list[index] = (key, value)
        self.__list.append((key, value))

    def __str__(self) -> str:
        return_val = ""
        for item in self.__list:
            return_val += str(item[0]) + " => " + str(item[1]) + "\n"
        return return_val


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
