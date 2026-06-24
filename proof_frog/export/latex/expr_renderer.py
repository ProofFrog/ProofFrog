"""Render FrogLang ``Expression`` AST nodes to LaTeX math.

The renderer is backend-independent. It produces strings suitable for
embedding inside math mode (``$...$``) — the surrounding delimiters are
the caller's responsibility.

Two overloaded operators disambiguate on operand type: ``+`` is XOR
(``\\oplus``) on ``BitString`` else addition; ``||`` is concatenation
(``\\|``) on ``BitString`` else logical OR (``\\lor``). Operand types come
from either the ``type_of`` map (keyed by ``id(node)``, set per-node by an
orchestrator) or the ``name_types`` map (keyed by variable name, built by the
module/proof renderers from the enclosing scope). Without type info we keep
the syntactic default (``+`` / ``\\lor``).
"""

from __future__ import annotations

import re

from ... import frog_ast
from ...visitors import NameTypeMap
from .macros import MacroRegistry

_BINOP_LATEX: dict[frog_ast.BinaryOperators, str] = {
    frog_ast.BinaryOperators.EQUALS: "=",
    frog_ast.BinaryOperators.NOTEQUALS: r"\ne",
    frog_ast.BinaryOperators.GT: ">",
    frog_ast.BinaryOperators.LT: "<",
    frog_ast.BinaryOperators.GEQ: r"\ge",
    frog_ast.BinaryOperators.LEQ: r"\le",
    frog_ast.BinaryOperators.AND: r"\land",
    frog_ast.BinaryOperators.OR: r"\lor",
    frog_ast.BinaryOperators.IN: r"\in",
    frog_ast.BinaryOperators.SUBSETS: r"\subseteq",
    frog_ast.BinaryOperators.UNION: r"\cup",
    frog_ast.BinaryOperators.SETMINUS: r"\setminus",
    frog_ast.BinaryOperators.SUBTRACT: "-",
    frog_ast.BinaryOperators.MULTIPLY: r"\cdot",
    frog_ast.BinaryOperators.DIVIDE: "/",
    frog_ast.BinaryOperators.EXPONENTIATE: "^",
}

# Greek-letter names auto-substitute to their LaTeX command (whole-token match
# only, so `alphabet` stays literal while `alpha1` -> `\alpha_{1}`). Only Greek
# letters with a distinct base-LaTeX command are included (e.g. no `\omicron`,
# and uppercase letters that coincide with Latin glyphs like Alpha/Beta).
_GREEK_LOWER = [
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "zeta",
    "eta",
    "theta",
    "iota",
    "kappa",
    "lambda",
    "mu",
    "nu",
    "xi",
    "pi",
    "rho",
    "sigma",
    "tau",
    "upsilon",
    "phi",
    "chi",
    "psi",
    "omega",
]
_GREEK_UPPER = [
    "Gamma",
    "Delta",
    "Theta",
    "Lambda",
    "Xi",
    "Pi",
    "Sigma",
    "Upsilon",
    "Phi",
    "Psi",
    "Omega",
]
_KEYWORD_VARIABLES = {name: "\\" + name for name in _GREEK_LOWER + _GREEK_UPPER}

# Field members that denote a group's generator/order. On parse paths that
# kept them as a plain ``FieldAccess`` (rather than the dedicated
# ``GroupGenerator`` / ``GroupOrder`` nodes) they are routed to the same
# per-group macro so both paths render identically.
_GROUP_SYMBOL_MEMBERS = {"generator": "generator", "order": "order"}

_SUBSCRIPT_RE = re.compile(r"^(.+?)(\d+)$")

# B4: a closed allow-list of name decorations rendered as math superscripts or
# accents. Matched only at a camelCase boundary (a lowercase letter or digit
# precedes the capitalized suffix), so literals like ``polestar`` and acronym
# runs like ``ABStar`` are left untouched. Source identifiers stay legal
# FrogLang; the operator-disambiguation maps key off the *raw* name, so this is
# invisible to them.
_DECORATION_SUPERSCRIPTS = {"Star": r"^{*}", "Prime": r"^{\prime}"}
_DECORATION_ACCENTS = {"Hat": r"\hat", "Tilde": r"\tilde", "Bar": r"\overline"}
_DECORATION_RE = re.compile(
    r"^(?P<head>.*[a-z0-9])(?P<deco>Star|Prime|Hat|Tilde|Bar)(?P<digits>\d*)$"
)


def _looks_like_algorithm_name(name: str) -> bool:
    if not name:
        return False
    return name[0].isupper() or name.isupper()


class ExprRenderer:
    """Render ``frog_ast.Expression`` nodes to LaTeX math strings."""

    def __init__(
        self,
        macros: MacroRegistry,
        type_of: dict[int, frog_ast.Type] | None = None,
        name_types: NameTypeMap | None = None,
        member_overrides: dict[tuple[str, str], str] | None = None,
    ) -> None:
        self.macros = macros
        self.type_of = type_of or {}
        # Scope-level name -> Type map, refreshed per method by the module/proof
        # renderers. Used to resolve a bare ``Variable`` operand's type when
        # ``type_of`` has no per-node entry.
        self.name_types = name_types
        # Optional ``(object, member) -> symbol`` field-access overrides,
        # consulted before the default rendering (e.g. a user style mapping
        # ``H.digest`` to ``\delta``).
        self.member_overrides = dict(member_overrides or {})

    def render(self, expr: frog_ast.Expression) -> str:
        return self._render(expr)

    # pylint: disable=too-many-return-statements,too-many-branches
    def _render(self, expr: frog_ast.Expression) -> str:
        if isinstance(expr, frog_ast.Variable):
            return self._render_variable(expr.name)
        if isinstance(expr, frog_ast.Integer):
            return str(expr.num)
        if isinstance(expr, frog_ast.Boolean):
            return r"\mathsf{true}" if expr.bool else r"\mathsf{false}"
        if isinstance(expr, frog_ast.NoneExpression):
            return r"\bot"
        if isinstance(expr, frog_ast.BinaryNum):
            return "0b" + format(expr.num, f"0{expr.length}b")
        if isinstance(expr, frog_ast.BitStringLiteral):
            return f"{expr.bit}^{{{self._render(expr.length)}}}"
        if isinstance(expr, frog_ast.GroupGenerator):
            return self._render_group_symbol(expr.group, "generator")
        if isinstance(expr, frog_ast.GroupOrder):
            return self._render_group_symbol(expr.group, "order")
        if isinstance(expr, frog_ast.BinaryOperation):
            return self._render_binop(expr)
        if isinstance(expr, frog_ast.UnaryOperation):
            return self._render_unop(expr)
        if isinstance(expr, frog_ast.FuncCall):
            return self._render_call(expr)
        if isinstance(expr, frog_ast.FieldAccess):
            return self._render_field(expr)
        if isinstance(expr, frog_ast.ArrayAccess):
            return f"{self._render(expr.the_array)}[{self._render(expr.index)}]"
        if isinstance(expr, frog_ast.Slice):
            return (
                f"{self._render(expr.the_array)}["
                f"{self._render(expr.start)} : {self._render(expr.end)}]"
            )
        if isinstance(expr, frog_ast.Set):
            inner = ", ".join(self._render(e) for e in expr.elements)
            return f"\\{{{inner}\\}}"
        if isinstance(expr, frog_ast.Tuple):
            inner = ", ".join(self._render(v) for v in expr.values)
            return f"({inner})"
        # ParameterizedGame in expression position (e.g. as the object of
        # a field access like `G(params).count`).  Render as an algorithm
        # macro call so field-access chains remain readable.
        if isinstance(expr, frog_ast.ParameterizedGame):
            head = self.macros.register_algorithm(expr.name)
            if not expr.args:
                return head
            rendered_args = [self._render(a) for a in expr.args]
            return f"{head}({', '.join(rendered_args)})"
        # ConcreteGame (`G(params).Side`) in expression position, e.g. as the
        # object of a `.count` field access in an assumption expression.
        if isinstance(expr, frog_ast.ConcreteGame):
            head = self._render(expr.game)
            side = self.macros.register_algorithm(expr.which)
            return f"{head}.{side}"
        # A Type used in expression position (e.g. `a <- ModInt<q>;`):
        # delegate to TypeRenderer to avoid the fallback comment.
        if isinstance(expr, frog_ast.Type):
            # pylint: disable=import-outside-toplevel
            from .type_renderer import TypeRenderer

            return TypeRenderer(self).render(expr)
        # Unknown node: emit a math-safe placeholder. A bare `%` comment would
        # comment out the rest of the line — fatal inside a `$...$` span.
        return rf"\text{{[unsupported: {type(expr).__name__}]}}"

    def _render_variable(self, name: str) -> str:
        # A single subscript level only: stacking subscripts (`}_{`) is a
        # pdflatex "Double subscript" error. Split on the *first* underscore and
        # drop everything after it into one subscript group (literal underscores
        # escaped), matching ``macros._mathsf_body``. A bare trailing-digit run
        # subscripts likewise. The head is never itself subscripted, so the two
        # paths can never compound into a double subscript.
        if name in _KEYWORD_VARIABLES:
            return _KEYWORD_VARIABLES[name]
        decorated = self._render_decorated(name)
        if decorated is not None:
            return decorated
        head, sub = self._split_subscript(name)
        return f"{head}_{{{sub}}}" if sub is not None else head

    @staticmethod
    def _split_subscript(token: str) -> tuple[str, str | None]:
        """Split a name into its rendered stem and a single subscript group.

        Subscript components are comma-joined into one group, honoring the
        single-subscript invariant (a stacked ``}_{`` is a pdflatex "Double
        subscript" error): a trailing-digit run on the stem and every
        ``_``-delimited tail segment each become a comma-separated component, so
        ``y0_pq`` -> ``y_{0,pq}`` and ``kem_pq_nseed`` -> ``kem_{pq,nseed}``.
        The stem is mapped through the Greek table and is never itself
        subscripted, so callers can append at most one more axis (a decoration
        superscript) without a double subscript.
        """
        segments = token.split("_")
        stem = segments[0]
        components: list[str] = []
        m = _SUBSCRIPT_RE.match(stem)
        if m:
            stem, digits = m.group(1), m.group(2)
            components.append(digits)
        components.extend(seg for seg in segments[1:] if seg)
        stem = _KEYWORD_VARIABLES.get(stem, stem)
        if not components:
            return stem, None
        return stem, ",".join(components)

    @classmethod
    def _render_decorated(cls, name: str) -> str | None:
        """Render a decorated name (``ctStar`` -> ``ct^{*}``), else ``None`` (B4).

        Superscript decorations (``Star``/``Prime``) sit on a different axis
        from the subscript, so an index composes safely whether it precedes the
        decoration (``ct1Star`` -> ``ct_{1}^{*}``) or follows it
        (``ctStar0`` -> ``ct_{0}^{*}``). Accents (``Hat``/``Tilde``/``Bar``)
        wrap the base with the subscript kept *outside* the accent
        (``mHat0`` -> ``\\hat{m}_{0}``), again avoiding a double subscript.
        """
        m = _DECORATION_RE.match(name)
        if m is None:
            return None
        head, head_sub = cls._split_subscript(m.group("head"))
        sub = head_sub or (m.group("digits") or None)
        subtex = f"_{{{sub}}}" if sub else ""
        deco = m.group("deco")
        if deco in _DECORATION_SUPERSCRIPTS:
            return f"{head}{subtex}{_DECORATION_SUPERSCRIPTS[deco]}"
        return f"{_DECORATION_ACCENTS[deco]}{{{head}}}{subtex}"

    def _operand_type(self, op: frog_ast.Expression) -> frog_ast.Type | None:
        """Resolve an operand's type from ``type_of`` (per-node) or names."""
        per_node = self.type_of.get(id(op))
        if per_node is not None:
            return per_node
        if isinstance(op, frog_ast.Variable) and self.name_types is not None:
            return self.name_types.get(op.name)
        return None

    def _is_bitstring_operand(self, expr: frog_ast.BinaryOperation) -> bool:
        return isinstance(
            self._operand_type(expr.left_expression), frog_ast.BitStringType
        ) or isinstance(
            self._operand_type(expr.right_expression), frog_ast.BitStringType
        )

    def _binop_is_bitstring(self, expr: frog_ast.BinaryOperation) -> bool:
        # A node-level mark (from ``note_bitstring_context``) wins, so a
        # concatenation of method-call operands whose types are otherwise
        # unresolvable still renders as concat/XOR rather than logical-or/plus.
        return isinstance(
            self.type_of.get(id(expr)), frog_ast.BitStringType
        ) or self._is_bitstring_operand(expr)

    def note_bitstring_context(self, expr: frog_ast.Expression) -> None:
        """Mark ``expr`` as BitString-typed so overloaded ``||`` / ``+`` inside
        it render as concatenation / XOR rather than logical-or / addition.

        Recurses through the overloaded operators only. Called by the statement
        renderer when the enclosing context is known to be a BitString (an
        assignment whose declared type is a BitString, or a return in a
        BitString-returning method) — type the per-operand resolver cannot
        recover from bare method-call operands.
        """
        if isinstance(expr, frog_ast.BinaryOperation) and expr.operator in (
            frog_ast.BinaryOperators.OR,
            frog_ast.BinaryOperators.ADD,
        ):
            self.type_of[id(expr)] = frog_ast.BitStringType()
            self.note_bitstring_context(expr.left_expression)
            self.note_bitstring_context(expr.right_expression)

    def _render_binop(self, expr: frog_ast.BinaryOperation) -> str:
        left = self._render(expr.left_expression)
        right = self._render(expr.right_expression)
        op = expr.operator
        # `+` and `||` are overloaded: XOR/concat on BitString, else add/OR.
        if op == frog_ast.BinaryOperators.ADD:
            sym = r"\oplus" if self._binop_is_bitstring(expr) else "+"
            return f"{left} {sym} {right}"
        if op == frog_ast.BinaryOperators.OR:
            sym = r"\|" if self._binop_is_bitstring(expr) else r"\lor"
            return f"{left} {sym} {right}"
        if op == frog_ast.BinaryOperators.EXPONENTIATE:
            # Brace the exponent (so chained `^` never stacks into a "Double
            # superscript") and the base when it is a compound expression or
            # already carries a superscript -- e.g. a decorated base such as
            # `xStar` (`x^{*}`) would otherwise produce `x^{*}^{sk}` (B4).
            needs_brace = (
                isinstance(expr.left_expression, frog_ast.BinaryOperation)
                or "^" in left
            )
            base = f"{{{left}}}" if needs_brace else left
            return f"{base}^{{{right}}}"
        return f"{left} {_BINOP_LATEX[op]} {right}"

    def _render_unop(self, expr: frog_ast.UnaryOperation) -> str:
        inner = self._render(expr.expression)
        if expr.operator == frog_ast.UnaryOperators.NOT:
            return rf"\neg {inner}"
        if expr.operator == frog_ast.UnaryOperators.SIZE:
            return f"|{inner}|"
        if expr.operator == frog_ast.UnaryOperators.MINUS:
            return f"-{inner}"
        return inner

    def _render_call(self, expr: frog_ast.FuncCall) -> str:
        callee = self._render_callee(expr.func)
        args = ", ".join(self._render(a) for a in expr.args)
        return f"{callee}({args})"

    def _render_callee(self, func: frog_ast.Expression) -> str:
        if isinstance(func, frog_ast.Variable) and _looks_like_algorithm_name(
            func.name
        ):
            return self.macros.register_algorithm(func.name)
        if isinstance(func, frog_ast.FieldAccess):
            # In call position the member is a method, so set it upright (as an
            # algorithm name) even when lowercase: `G.evaluate(s)` reads
            # `\G.\mathsf{evaluate}(s)`, matching paper convention.
            return self._render_field(func, member_is_call=True)
        return self._render(func)

    def _member_override(self, obj_name: str | None, member: str) -> str | None:
        if obj_name is not None:
            exact = self.member_overrides.get((obj_name, member))
            if exact is not None:
                return exact
        return self.member_overrides.get(("*", member))

    def _render_group_symbol(self, group: frog_ast.Expression, kind: str) -> str:
        if isinstance(group, frog_ast.Variable):
            return self.macros.register_group_symbol(group.name, kind)
        # Uncommon: the group is a compound expression rather than a bare name.
        return f"{self._render(group)}.{kind}"

    def _render_field(
        self, expr: frog_ast.FieldAccess, member_is_call: bool = False
    ) -> str:
        obj = expr.the_object
        obj_name = obj.name if isinstance(obj, frog_ast.Variable) else None
        override = self._member_override(obj_name, expr.name)
        if override is not None:
            return override
        # A group generator/order member routes to the per-group macro (same as
        # the dedicated GroupGenerator/GroupOrder nodes), unless it is actually
        # a method call of that name.
        if (
            obj_name is not None
            and not member_is_call
            and expr.name in _GROUP_SYMBOL_MEMBERS
        ):
            return self.macros.register_group_symbol(
                obj_name, _GROUP_SYMBOL_MEMBERS[expr.name]
            )
        if isinstance(obj, frog_ast.Variable) and _looks_like_algorithm_name(obj.name):
            head = self.macros.register_algorithm(obj.name)
        else:
            head = self._render(obj)
        # An algorithm-like or call-position member is set upright via a macro;
        # otherwise it renders like a variable, so Greek names (e.g.
        # ``G.lambda`` -> ``\G.\lambda``) and trailing-digit subscripts stay
        # consistent with expression-position identifiers.
        if member_is_call or _looks_like_algorithm_name(expr.name):
            tail = self.macros.register_algorithm(expr.name)
        else:
            tail = self._render_variable(expr.name)
        return f"{head}.{tail}"
