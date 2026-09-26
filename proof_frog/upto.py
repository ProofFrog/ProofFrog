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

import copy
import dataclasses
from typing import Optional

from . import frog_ast

REVEAL = "__reveal"
"""Engine-internal oracle appended to flag games; not a FrogLang identifier."""


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
