"""Identical-until-bad game pairs and the events they are charged to.

The fundamental lemma of game playing (Bellare-Rogaway 2006, Lemma 2; Shoup
2004, section 5): if two games are *identical until bad* -- for every
adversary and every choice of coins they produce the same oracle answers and
reach the same states up to the first statement ``bad = true;``, which runs
at the same point in both or in neither -- then no adversary distinguishes
them with advantage larger than the probability that ``bad`` is set. That
probability is the same in both games (Bellare-Rogaway 2006, Proposition 3),
so it is one quantity of the pair, written ``event bad of P(a)`` in a proof.

This module holds the parts of that argument that are checked on the raw
parsed game ASTs, before instantiation or canonicalization:

* the flag discipline (``bad`` is reset to ``false`` once at the start and
  only ever raised afterwards, so it is monotone);
* the lockstep check that a pair is identical until its flag
  (:func:`identical_until_bad`);
* the engine-internal *flag game* that turns ``Pr[bad]`` into a
  distinguishing advantage: one side of the pair plus an oracle
  ``__reveal`` returning the flag (``Real``) or ``false`` (``Ideal``). An
  adversary that plays and then calls ``__reveal`` once has advantage
  exactly ``Pr[bad]``;
* the *stripped* flag game for a flag decided in ``Initialize``, whose only
  oracles are ``Initialize`` (with its return value dropped) and
  ``__reveal``;
* the rule that a reduction calls ``challenger.Initialize`` at most once and
  only from its own ``Initialize``.
"""

from __future__ import annotations

import collections
import copy
import dataclasses
import enum
from typing import Optional, Union

import z3

from . import frog_ast

REVEAL = "__reveal"
"""Engine-internal oracle appended to flag games; not a FrogLang identifier."""

SILENCED = "#silenced"
"""Suffix of the engine-internal copy of a helper whose ``__reveal`` says false."""


def is_event_notion(notion: frog_ast.ParameterizedGame) -> bool:
    """Whether *notion* is the synthetic game of an event theorem."""
    return "#event#" in notion.name


def pretty_notion(notion: frog_ast.ParameterizedGame) -> str:
    """``P#event#bad(S)`` -> ``bad of P(S)``; other notions unchanged."""
    if not is_event_notion(notion):
        return str(notion)
    game, rest = notion.name.split("#event#", 1)
    flag, _, init = rest.partition("#")
    args = ", ".join(str(a) for a in notion.args)
    suffix = " at Initialize" if init == "init" else ""
    return f"{flag} of {game}({args}){suffix}"


@dataclasses.dataclass(frozen=True)
class UptoError:
    """A located reason why a pair is not identical until its flag."""

    message: str
    oracle: str = ""
    left_line: int = 0
    right_line: int = 0

    def __str__(self) -> str:
        where = f"{self.oracle}: " if self.oracle else ""
        lines = []
        if self.left_line > 0:
            lines.append(f"left line {self.left_line}")
        if self.right_line > 0:
            lines.append(f"right line {self.right_line}")
        suffix = f" ({', '.join(lines)})" if lines else ""
        return f"{where}{self.message}{suffix}"


# ---------------------------------------------------------------------------
# Generic AST helpers
# ---------------------------------------------------------------------------


def _walk(node: object) -> list[object]:
    """Depth-first list of every node/attribute value reachable from *node*."""
    seen: list[object] = []
    stack: list[object] = [node]
    while stack:
        current = stack.pop()
        seen.append(current)
        if isinstance(current, frog_ast.ASTNode):
            stack.extend(
                getattr(current, attr) for attr in vars(current) if attr != "origin"
            )
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return seen


def _target_name(var: frog_ast.Expression) -> Optional[str]:
    """The variable an assignment target writes: the base of any access chain."""
    while isinstance(var, (frog_ast.ArrayAccess, frog_ast.FieldAccess)):
        var = var.the_array if isinstance(var, frog_ast.ArrayAccess) else var.the_object
    return var.name if isinstance(var, frog_ast.Variable) else None


def _is_flag_assignment(node: object, flag: str, value: bool) -> bool:
    """``<flag> = <value>;`` exactly (no declaration, no access chain)."""
    return (
        isinstance(node, frog_ast.Assignment)
        and node.the_type is None
        and node.var == frog_ast.Variable(flag)
        and node.value == frog_ast.Boolean(value)
    )


def _writes_flag(node: object, flag: str) -> bool:
    """Any statement that writes the field *flag* (assignment or sampling)."""
    return (
        isinstance(node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample))
        and node.the_type is None
        and _target_name(node.var) == flag
    )


def _declares(node: object, name: str) -> bool:
    """Whether *node* introduces a local or loop variable called *name*."""
    if isinstance(node, frog_ast.VariableDeclaration):
        return node.name == name
    if isinstance(node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)):
        return node.the_type is not None and _target_name(node.var) == name
    if isinstance(node, frog_ast.NumericFor):
        return node.name == name
    if isinstance(node, frog_ast.GenericFor):
        return node.var_name == name
    return False


# ---------------------------------------------------------------------------
# Flag field and discipline
# ---------------------------------------------------------------------------


def check_flag_field(game: frog_ast.Game, flag: str) -> Optional[UptoError]:
    """*game* declares ``Bool <flag>``, with no initializer or ``= false``."""
    field = next((f for f in game.fields if f.name == flag), None)
    if field is None or not isinstance(field.type, frog_ast.BoolType):
        return UptoError(f"{game.name} has no `Bool {flag}` field")
    if field.value is not None and field.value != frog_ast.Boolean(False):
        return UptoError(
            f"{game.name}: field `{flag}` may only be initialized to false"
        )
    return None


def _sanctioned_resets(game: frog_ast.Game, flag: str) -> set[int]:
    """Ids of the ``<flag> = false;`` statements the discipline allows.

    A reset is allowed only as a top-level statement of ``Initialize`` that
    no flag write and no return precedes, so the flag is ``false`` when the
    first oracle runs and a raise can never be undone.
    """
    if not game.has_method("Initialize"):
        return set()
    allowed: set[int] = set()
    for stmt in game.get_method("Initialize").block.statements:
        if _is_flag_assignment(stmt, flag, False):
            allowed.add(id(stmt))
            continue
        if any(
            _writes_flag(n, flag) or isinstance(n, frog_ast.ReturnStatement)
            for n in _walk(stmt)
        ):
            break
    return allowed


def check_flag_discipline(game: frog_ast.Game, flag: str) -> Optional[UptoError]:
    """The flag is monotone: reset once in ``Initialize``, then only raised.

    ``<flag>`` is written only by ``<flag> = false;`` at the top of
    ``Initialize`` (before any raise or return; not needed when the field is
    initialized ``false``) and by ``<flag> = true;``. It is never sampled,
    never assigned anything else and never shadowed by a parameter or local.
    Reads are unrestricted.
    """
    resets = _sanctioned_resets(game, flag)
    field = next((f for f in game.fields if f.name == flag), None)
    initialized = field is not None and field.value == frog_ast.Boolean(False)
    if not resets and not initialized:
        return UptoError(
            f"{game.name}.Initialize must start by setting `{flag} = false;`"
            " (before any statement that raises the flag or returns)"
        )
    for method in game.methods:
        name = method.signature.name
        if any(p.name == flag for p in method.signature.parameters):
            return UptoError(f"{game.name}.{name} has a parameter named `{flag}`")
        for node in _walk(method.block):
            if _declares(node, flag):
                return UptoError(f"{game.name}.{name} declares a local named `{flag}`")
            if not _writes_flag(node, flag):
                continue
            if id(node) in resets or _is_flag_assignment(node, flag, True):
                continue
            return UptoError(
                f"{game.name}.{name}: `{flag}` may only be set by `{flag} = true;`"
                f" or reset by `{flag} = false;` at the start of Initialize",
                name,
                getattr(node, "line_num", 0),
            )
    return None


def raised_only_in_initialize(game: frog_ast.Game, flag: str) -> bool:
    """Every ``<flag> = true;`` of *game* lies in ``Initialize``."""
    for method in game.methods:
        if method.signature.name == "Initialize":
            continue
        if any(_is_flag_assignment(n, flag, True) for n in _walk(method.block)):
            return False
    return True


# ---------------------------------------------------------------------------
# The lockstep check
# ---------------------------------------------------------------------------
#
# Both sides of a pair are walked statement by statement under a path
# condition Phi: a list of call-free Boolean facts that hold on both sides
# (their states are equal on every pre-flag prefix). Statements must agree
# syntactically, except that return values, assigned values and map indices
# may differ when Phi entails their equality, and if-arms that Phi rules out
# are pruned. Both sides raising the flag at the same statement ends the
# comparison of that block (everything after is post-bad). Facts are killed
# as soon as a variable they mention is written, and anything containing a
# call stays out of Z3: two occurrences of a non-deterministic call are two
# values, so a text-keyed atom would conflate them.

Phi = list[frog_ast.Expression]

_BOOL_OPERATORS = {
    frog_ast.BinaryOperators.AND,
    frog_ast.BinaryOperators.EQUALS,
    frog_ast.BinaryOperators.NOTEQUALS,
    frog_ast.BinaryOperators.GT,
    frog_ast.BinaryOperators.LT,
    frog_ast.BinaryOperators.GEQ,
    frog_ast.BinaryOperators.LEQ,
    frog_ast.BinaryOperators.IN,
    frog_ast.BinaryOperators.SUBSETS,
}

_RLIMIT = 5_000_000
"""Z3 resource limit per entailment query (deterministic, unlike a timeout)."""


class _Outcome(enum.Enum):
    ENDED = "ended"
    RAISED = "raised"


@dataclasses.dataclass
class _StmtResult:
    learned: Phi
    """Facts that hold after the statement (already valid at the join)."""


_BlocksResult = Union[_Outcome, UptoError]


def _binop(
    op: frog_ast.BinaryOperators, a: frog_ast.Expression, b: frog_ast.Expression
) -> frog_ast.Expression:
    return frog_ast.BinaryOperation(op, a, b)


def _not(e: frog_ast.Expression) -> frog_ast.Expression:
    return frog_ast.UnaryOperation(frog_ast.UnaryOperators.NOT, e)


def _conj(parts: list[frog_ast.Expression]) -> frog_ast.Expression:
    if not parts:
        return frog_ast.Boolean(True)
    out = parts[0]
    for part in parts[1:]:
        out = _binop(frog_ast.BinaryOperators.AND, out, part)
    return out


def _has_call(node: object) -> bool:
    return any(isinstance(n, frog_ast.FuncCall) for n in _walk(node))


def _free_names(node: object) -> set[str]:
    return {n.name for n in _walk(node) if isinstance(n, frog_ast.Variable)}


def _assigned(node: object) -> set[str]:
    """Every name *node* may write or (re)declare, at any depth."""
    names: set[str] = set()
    for n in _walk(node):
        if isinstance(n, (frog_ast.Assignment, frog_ast.Sample)):
            name = _target_name(n.var)
            if name is not None:
                names.add(name)
        elif isinstance(n, frog_ast.UniqueSample):
            for target in (n.var, n.unique_set):
                name = _target_name(target)
                if name is not None:
                    names.add(name)
        elif isinstance(n, frog_ast.VariableDeclaration):
            names.add(n.name)
        elif isinstance(n, frog_ast.NumericFor):
            names.add(n.name)
        elif isinstance(n, frog_ast.GenericFor):
            names.add(n.var_name)
    return names


def _kill(phi: Phi, names: set[str]) -> Phi:
    return [fact for fact in phi if not _free_names(fact) & names]


class _Euf:
    """Encode call-free FrogLang expressions into Z3 (Booleans + EUF atoms).

    Boolean connectives and ``==``/``!=`` are interpreted; every other maximal
    subterm is an opaque constant keyed on its text, of one uninterpreted
    sort (value positions) or Bool (Boolean positions). ``||`` is Boolean OR
    only when an operand is definitely Boolean: it is also bitstring
    concatenation, and collapsing a concatenation to a Bool would be unsound.
    """

    _SORT = z3.DeclareSort("UptoAtom")

    def __init__(self, flag: str) -> None:
        self.flag = flag
        self.opaque: dict[str, z3.ExprRef] = {}
        self.bools: dict[str, z3.BoolRef] = {}

    def definitely_bool(self, e: frog_ast.Expression) -> bool:
        if isinstance(e, frog_ast.Boolean):
            return True
        if isinstance(e, frog_ast.Variable):
            return e.name == self.flag
        if isinstance(e, frog_ast.UnaryOperation):
            return e.operator == frog_ast.UnaryOperators.NOT
        if isinstance(e, frog_ast.BinaryOperation):
            if e.operator in _BOOL_OPERATORS:
                return True
            if e.operator == frog_ast.BinaryOperators.OR:
                return self.definitely_bool(e.left_expression) or self.definitely_bool(
                    e.right_expression
                )
        return False

    def atom(self, e: frog_ast.Expression) -> z3.ExprRef:
        key = str(e)
        if key not in self.opaque:
            self.opaque[key] = z3.Const(f"a{len(self.opaque)}", self._SORT)
        return self.opaque[key]

    def opaque_bool(self, e: frog_ast.Expression) -> z3.BoolRef:
        key = str(e)
        if key not in self.bools:
            self.bools[key] = z3.Bool(f"b{len(self.bools)}")
        return self.bools[key]

    def encode(self, e: frog_ast.Expression) -> z3.BoolRef:
        """*e* in a Boolean position."""
        if isinstance(e, frog_ast.Boolean):
            return z3.BoolVal(e.bool)
        if (
            isinstance(e, frog_ast.UnaryOperation)
            and e.operator == frog_ast.UnaryOperators.NOT
        ):
            return z3.Not(self.encode(e.expression))
        if isinstance(e, frog_ast.BinaryOperation):
            op = e.operator
            left, right = e.left_expression, e.right_expression
            if op == frog_ast.BinaryOperators.AND:
                return z3.And(self.encode(left), self.encode(right))
            if op == frog_ast.BinaryOperators.OR and self.definitely_bool(e):
                return z3.Or(self.encode(left), self.encode(right))
            if op in (
                frog_ast.BinaryOperators.EQUALS,
                frog_ast.BinaryOperators.NOTEQUALS,
            ):
                eq = self.equal(left, right)
                return eq if op == frog_ast.BinaryOperators.EQUALS else z3.Not(eq)
        return self.opaque_bool(e)

    def equal(self, a: frog_ast.Expression, b: frog_ast.Expression) -> z3.BoolRef:
        if self.definitely_bool(a) or self.definitely_bool(b):
            return self.encode(a) == self.encode(b)
        return self.atom(a) == self.atom(b)


def _entails(phi: Phi, goal: frog_ast.Expression, flag: str = "") -> Optional[bool]:
    """Whether the call-free facts *phi* entail *goal*; None if undecided."""
    enc = _Euf(flag)
    solver = z3.Solver()
    solver.set("rlimit", _RLIMIT)
    for fact in phi:
        solver.add(enc.encode(fact))
    solver.add(z3.Not(enc.encode(goal)))
    result = solver.check()
    if result == z3.unsat:
        return True
    if result == z3.sat:
        return False
    return None


def _leaf_equal(
    a: frog_ast.Expression, b: frog_ast.Expression, phi: Phi, flag: str
) -> Optional[bool]:
    if a == b:
        return True
    if _has_call(a) or _has_call(b):
        return False
    return _entails(phi, _binop(frog_ast.BinaryOperators.EQUALS, a, b), flag)


def _cond_equal(
    a: frog_ast.Expression, b: frog_ast.Expression, phi: Phi, flag: str
) -> Optional[bool]:
    if a == b:
        return True
    if _has_call(a) or _has_call(b):
        return False
    # (!a || b) && (!b || a): a Boolean reading even for opaque operands.
    iff = _binop(
        frog_ast.BinaryOperators.AND,
        _binop(frog_ast.BinaryOperators.OR, _not(a), b),
        _binop(frog_ast.BinaryOperators.OR, _not(b), a),
    )
    return _entails(phi, iff, flag)


def _lvalue_equal(
    a: frog_ast.Expression, b: frog_ast.Expression, phi: Phi, flag: str
) -> Optional[bool]:
    """Assignment targets: same variable and access shape; indices by leaf."""
    if isinstance(a, frog_ast.Variable) or isinstance(b, frog_ast.Variable):
        return a == b
    if isinstance(a, frog_ast.ArrayAccess) and isinstance(b, frog_ast.ArrayAccess):
        base = _lvalue_equal(a.the_array, b.the_array, phi, flag)
        if base is not True:
            return base
        return _leaf_equal(a.index, b.index, phi, flag)
    if isinstance(a, frog_ast.FieldAccess) and isinstance(b, frog_ast.FieldAccess):
        if a.name != b.name:
            return False
        return _lvalue_equal(a.the_object, b.the_object, phi, flag)
    return a == b


def _decided(
    result: Optional[bool],
    what: str,
    oracle: str,
    x: frog_ast.ASTNode,
    y: frog_ast.ASTNode,
) -> Optional[UptoError]:
    if result is True:
        return None
    if result is None:
        return UptoError(
            f"could not decide whether {what} agree", oracle, x.line_num, y.line_num
        )
    return UptoError(f"{what} differ", oracle, x.line_num, y.line_num)


def _path(conditions: list[frog_ast.Expression], i: int) -> list[frog_ast.Expression]:
    """Conjuncts of the path condition of arm *i* (else arm: i == len)."""
    parts = [_not(c) for c in conditions[:i]]
    if i < len(conditions):
        parts.insert(0, conditions[i])
    return parts


def _prune(stmt: frog_ast.IfStatement, phi: Phi, flag: str) -> list[frog_ast.Statement]:
    """Drop arms Phi rules out; splice the arm Phi forces; [stmt] if unchanged.

    An undecided query counts as "not entailed": failing to prune only makes
    the comparison stricter.
    """
    kept_conditions: list[frog_ast.Expression] = []
    kept_blocks: list[frog_ast.Block] = []
    for i, block in enumerate(stmt.blocks):
        is_else = i >= len(stmt.conditions)
        if is_else:
            if not kept_blocks:
                return list(block.statements)
            kept_blocks.append(block)
            break
        condition = stmt.conditions[i]
        if _entails(phi, _not(condition), flag) is True:
            continue
        if not kept_blocks and _entails(phi, condition, flag) is True:
            return list(block.statements)
        kept_conditions.append(condition)
        kept_blocks.append(block)
    if not kept_blocks:
        return []
    if len(kept_blocks) == len(stmt.blocks):
        return [stmt]
    pruned = frog_ast.IfStatement(kept_conditions, kept_blocks)
    pruned.line_num, pruned.column_num = stmt.line_num, stmt.column_num
    return [pruned]


def _prune_front(q: collections.deque[frog_ast.Statement], phi: Phi, flag: str) -> None:
    while (
        q and isinstance(q[0], frog_ast.IfStatement) and not _has_call(q[0].conditions)
    ):
        head = q[0]
        replacement = _prune(head, phi, flag)
        if len(replacement) == 1 and replacement[0] is head:
            return
        q.popleft()
        q.extendleft(reversed(replacement))


def _blocks(
    xs: list[frog_ast.Statement],
    ys: list[frog_ast.Statement],
    phi: Phi,
    flag: str,
    oracle: str,
) -> _BlocksResult:
    left, right = collections.deque(xs), collections.deque(ys)
    while True:
        _prune_front(left, phi, flag)
        _prune_front(right, phi, flag)
        if not left and not right:
            return _Outcome.ENDED
        if not left or not right:
            extra = left[0] if left else right[0]
            return UptoError(
                "extra statement",
                oracle,
                extra.line_num if left else 0,
                extra.line_num if right else 0,
            )
        x, y = left.popleft(), right.popleft()
        x_raises = _is_flag_assignment(x, flag, True)
        y_raises = _is_flag_assignment(y, flag, True)
        if x_raises and y_raises:
            return _Outcome.RAISED
        if x_raises or y_raises:
            return UptoError(
                "flag raised at different points", oracle, x.line_num, y.line_num
            )
        result = _stmt(x, y, phi, flag, oracle)
        if isinstance(result, UptoError):
            return result
        phi = _kill(phi, _assigned(x) | _assigned(y)) + result.learned


def _stmt(
    x: frog_ast.Statement,
    y: frog_ast.Statement,
    phi: Phi,
    flag: str,
    oracle: str,
) -> Union[_StmtResult, UptoError]:
    # pylint: disable=too-many-return-statements
    if type(x) is not type(y):
        return UptoError("different statements", oracle, x.line_num, y.line_num)
    if isinstance(x, frog_ast.IfStatement):
        assert isinstance(y, frog_ast.IfStatement)
        return _if_stmt(x, y, phi, flag, oracle)
    if isinstance(x, (frog_ast.NumericFor, frog_ast.GenericFor)):
        header_x = {k: v for k, v in vars(x).items() if k not in _NON_SEMANTIC}
        header_y = {k: v for k, v in vars(y).items() if k not in _NON_SEMANTIC}
        if header_x != header_y:
            return UptoError("loop headers differ", oracle, x.line_num, y.line_num)
        assert isinstance(y, (frog_ast.NumericFor, frog_ast.GenericFor))
        body_phi = _kill(phi, _assigned(x) | _assigned(y))
        out = _blocks(
            list(x.block.statements), list(y.block.statements), body_phi, flag, oracle
        )
        if isinstance(out, UptoError):
            return out
        return _StmtResult([])
    if isinstance(x, frog_ast.ReturnStatement):
        assert isinstance(y, frog_ast.ReturnStatement)
        err = _decided(
            _leaf_equal(x.expression, y.expression, phi, flag),
            "return values",
            oracle,
            x,
            y,
        )
        return err if err is not None else _StmtResult([])
    if isinstance(x, frog_ast.Assignment):
        assert isinstance(y, frog_ast.Assignment)
        return _assignment(x, y, phi, flag, oracle)
    if x == y:
        return _StmtResult([])
    return UptoError("different statements", oracle, x.line_num, y.line_num)


_NON_SEMANTIC = {"line_num", "column_num", "origin", "block"}


def _assignment(
    x: frog_ast.Assignment,
    y: frog_ast.Assignment,
    phi: Phi,
    flag: str,
    oracle: str,
) -> Union[_StmtResult, UptoError]:
    if x.the_type != y.the_type:
        return UptoError("different declared types", oracle, x.line_num, y.line_num)
    err = _decided(
        _lvalue_equal(x.var, y.var, phi, flag), "assignment targets", oracle, x, y
    ) or _decided(
        _leaf_equal(x.value, y.value, phi, flag), "assigned values", oracle, x, y
    )
    if err is not None:
        return err
    learned: Phi = []
    if (
        isinstance(x.var, frog_ast.Variable)
        and not _has_call(x.value)
        and x.var.name not in _free_names(x.value)
    ):
        learned.append(_binop(frog_ast.BinaryOperators.EQUALS, x.var, x.value))
    return _StmtResult(learned)


def _if_stmt(
    x: frog_ast.IfStatement,
    y: frog_ast.IfStatement,
    phi: Phi,
    flag: str,
    oracle: str,
) -> Union[_StmtResult, UptoError]:
    if len(x.conditions) != len(y.conditions) or len(x.blocks) != len(y.blocks):
        return UptoError(
            "if-statements have different arms", oracle, x.line_num, y.line_num
        )
    for cx, cy in zip(x.conditions, y.conditions):
        err = _decided(_cond_equal(cx, cy, phi, flag), "conditions", oracle, x, y)
        if err is not None:
            return err
    candidates: Phi = []
    for i, (bx, by) in enumerate(zip(x.blocks, y.blocks)):
        path = _path(x.conditions, i)
        arm_phi = phi + [c for c in path if not _has_call(c)]
        out = _blocks(list(bx.statements), list(by.statements), arm_phi, flag, oracle)
        if isinstance(out, UptoError):
            return out
        if (
            out is _Outcome.RAISED
            and not _has_call(path)
            and not _returns_before_raise(bx, flag)
        ):
            candidates.append(_not(_conj(path)))
    # Facts learned from raising arms describe the state on entry; any arm
    # that falls through may have changed it, so kill what any arm writes.
    return _StmtResult(_kill(candidates, _assigned(x) | _assigned(y)))


def _returns_before_raise(block: frog_ast.Block, flag: str) -> bool:
    for stmt in block.statements:
        if _is_flag_assignment(stmt, flag, True):
            return False
        if any(isinstance(n, frog_ast.ReturnStatement) for n in _walk(stmt)):
            return True
    return False


def identical_until_bad(pair: frog_ast.GameFile, flag: str) -> Optional[UptoError]:
    """None when the pair's two games are identical until *flag* (W1-W4)."""
    left, right = pair.games
    if left.parameters != right.parameters:
        return UptoError("the two games take different parameters")
    if left.fields != right.fields:
        return UptoError("the two games declare different fields")
    for game in (left, right):
        err = check_flag_field(game, flag) or check_flag_discipline(game, flag)
        if err is not None:
            return err
    if [m.signature for m in left.methods] != [m.signature for m in right.methods]:
        return UptoError("oracle names, order or signatures differ")
    field = next(f for f in left.fields if f.name == flag)
    flag_false = _binop(
        frog_ast.BinaryOperators.EQUALS,
        frog_ast.Variable(flag),
        frog_ast.Boolean(False),
    )
    initialized = field.value == frog_ast.Boolean(False)
    for ml, mr in zip(left.methods, right.methods):
        name = ml.signature.name
        # Before Initialize's reset the flag is only known false when the
        # field is initialized; afterwards it is false on every pre-flag
        # prefix (the discipline makes it monotone).
        phi0: Phi = [] if name == "Initialize" and not initialized else [flag_false]
        out = _blocks(
            list(ml.block.statements), list(mr.block.statements), phi0, flag, name
        )
        if isinstance(out, UptoError):
            return out
    return None


# ---------------------------------------------------------------------------
# Flag games
# ---------------------------------------------------------------------------


def _reveal_method(body: frog_ast.Expression) -> frog_ast.Method:
    return frog_ast.Method(
        frog_ast.MethodSignature(REVEAL, frog_ast.BoolType(), []),
        frog_ast.Block([frog_ast.ReturnStatement(body)]),
    )


def _side(pair: frog_ast.GameFile, side: str) -> frog_ast.Game:
    for game in pair.games:
        if game.name == side:
            return game
    raise KeyError(f"{pair.name} has no side {side}")


def _with_reveal_game(
    game: frog_ast.Game, name: str, body: frog_ast.Expression
) -> frog_ast.Game:
    out = copy.deepcopy(game)
    out.name = name
    out.methods.append(_reveal_method(body))
    return out


def flag_game(
    pair: frog_ast.GameFile, side: str, flag: str, key: str
) -> frog_ast.GameFile:
    """``Real`` = *side* + ``__reveal`` returning *flag*; ``Ideal`` returns false."""
    base = _side(pair, side)
    real = _with_reveal_game(base, "Real", frog_ast.Variable(flag))
    ideal = _with_reveal_game(base, "Ideal", frog_ast.Boolean(False))
    return frog_ast.GameFile(
        list(pair.imports), (real, ideal), key, copy.deepcopy(pair.advantage)
    )


def strip(pair: frog_ast.GameFile, side: str, flag: str, key: str) -> frog_ast.GameFile:
    """The flag game of *side* reduced to ``Initialize`` with its output dropped.

    FrogLang has no bare ``return;``, so the return value cannot be kept but
    emptied: the trailing return is removed and the return type made
    ``Void``. An early return anywhere else in ``Initialize`` is refused.
    """
    base = _side(pair, side)
    init = copy.deepcopy(base.get_method("Initialize"))
    init.signature.return_type = frog_ast.Void()
    stmts = list(init.block.statements)
    if stmts and isinstance(stmts[-1], frog_ast.ReturnStatement):
        stmts.pop()
    if any(
        isinstance(n, frog_ast.ReturnStatement) for n in _walk(frog_ast.Block(stmts))
    ):
        raise ValueError(
            f"{base.name}.Initialize has an early return; not supported at Initialize"
        )
    init.block = frog_ast.Block(stmts)
    stripped = frog_ast.Game(
        (base.name, copy.deepcopy(base.parameters), copy.deepcopy(base.fields), [init])
    )
    return flag_game(
        frog_ast.GameFile(list(pair.imports), (stripped, stripped), key, None),
        base.name,
        flag,
        key,
    )


def with_reveal(game: frog_ast.Game, body: frog_ast.Expression) -> frog_ast.Game:
    """A copy of *game* (a reduction or game) with ``Bool __reveal()`` appended."""
    out = copy.deepcopy(game)
    out.methods.append(_reveal_method(body))
    return out


# ---------------------------------------------------------------------------
# challenger.Initialize placement
# ---------------------------------------------------------------------------


def is_challenger_init_call(node: object) -> bool:
    """Whether *node* is a call `challenger.Initialize(...)`."""
    return (
        isinstance(node, frog_ast.FuncCall)
        and isinstance(node.func, frog_ast.FieldAccess)
        and isinstance(node.func.the_object, frog_ast.Variable)
        and node.func.the_object.name == "challenger"
        and node.func.name == "Initialize"
    )


def check_challenger_init_placement(reduction: frog_ast.Reduction) -> Optional[str]:
    """``challenger.Initialize`` at most once, only inside the reduction's Initialize."""
    for method in reduction.methods:
        calls = [n for n in _walk(method.block) if is_challenger_init_call(n)]
        if method.signature.name != "Initialize" and calls:
            return (
                f"{reduction.name}.{method.signature.name} calls"
                " challenger.Initialize; it may only be called from Initialize"
            )
        if len(calls) > 1:
            return (
                f"{reduction.name}.Initialize calls challenger.Initialize"
                " more than once"
            )
    return None
