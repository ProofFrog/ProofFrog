"""Canonical-form serialization for the per-transform tactic cache.

The tactic cache is keyed by ``(transform_name, canonical_text(game_before),
canonical_text(game_after))``. For lookups to be stable across exporter
runs, ``canonical_text`` must be a pure function of the input AST modulo
the same normalization the per-transform exporter applies before
translating to EC source.

This module owns the canonicalization basis. Two layers:

1. :func:`_normalize_for_ec` (and its mangling/hoisting helpers): the
   same pre-pass the per-transform exporter applies to every flat-state
   game before handing it to the shared statement translator. Extracted
   here so the cache lookup sees exactly the same shape that the
   translator does — guarantees the canonical text and the rendered EC
   diverge only in surface syntax. The exporter re-imports these
   helpers from this module to avoid duplication.

2. :func:`canonical_text`: walks the normalized AST and emits a
   deterministic EC-flavored text form. Uses ``str(type)`` for type
   surface syntax (so we don't need to set up the full ``TypeCollector``
   context just to compute a cache key), but otherwise mirrors the EC
   ``proc`` body shape so the cache file is human-skimmable.

Schema version is owned by ``tactic_cache.py``; any change to the output
shape of :func:`canonical_text` (or to :func:`_normalize_for_ec`) forces a
``schema_version`` bump.
"""

from __future__ import annotations

import copy
import re
from typing import Sequence

from ... import frog_ast

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def canonical_text(
    game: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
) -> str:
    """Return a deterministic textual canonical form of ``game``.

    Applies :func:`_normalize_for_ec` to a deep copy of ``game`` (so the
    caller's AST is unaffected), then walks the result emitting EC-like
    procedure source. Same input AST → same output, byte-for-byte.

    The output is *not* required to be parseable EC; it is a cache key
    that should be diff-friendly when human-curated entries are
    inspected in a sidecar TOML file.
    """
    prepared = _normalize_for_ec(
        copy.deepcopy(game), external_module_types, method_return_types
    )
    text = _pretty_print_game(prepared)
    # Trailing newline matches the TOML literal-block round-trip
    # (``'''\n<body>\n'''`` reads as ``<body>\n``), so a sidecar entry
    # written verbatim from the Layer-3 diagnostic compares equal to
    # the export's freshly-computed canonical text.
    if not text.endswith("\n"):
        text += "\n"
    return text


# ---------------------------------------------------------------------------
# AST → canonical text
# ---------------------------------------------------------------------------


def _pretty_print_game(game: frog_ast.Game) -> str:
    lines: list[str] = []
    for method in game.methods:
        lines.extend(_pretty_print_method(method))
    return "\n".join(lines)


def _pretty_print_method(method: frog_ast.Method) -> list[str]:
    sig = method.signature
    param_text = ", ".join(f"{p.name} : {_type_text(p.type)}" for p in sig.parameters)
    out: list[str] = []
    out.append(f"proc {sig.name}({param_text}) : {_type_text(sig.return_type)} = {{")
    for stmt in method.block.statements:
        for line in _pretty_print_stmt(stmt):
            out.append(f"  {line}")
    out.append("}")
    return out


def _pretty_print_stmt(stmt: frog_ast.Statement) -> list[str]:
    if isinstance(stmt, frog_ast.VariableDeclaration):
        return [f"var {stmt.name} : {_type_text(stmt.type)};"]
    if isinstance(stmt, frog_ast.Sample):
        lhs = _pretty_print_expr(stmt.var)
        rhs = _pretty_print_expr(stmt.sampled_from)
        decl = [f"var {lhs} : {_type_text(stmt.the_type)};"] if stmt.the_type else []
        return decl + [f"{lhs} <$ {rhs};"]
    if isinstance(stmt, frog_ast.Assignment):
        lhs = _pretty_print_expr(stmt.var)
        rhs_expr = stmt.value
        decl = [f"var {lhs} : {_type_text(stmt.the_type)};"] if stmt.the_type else []
        if isinstance(rhs_expr, frog_ast.FuncCall) and isinstance(
            rhs_expr.func, frog_ast.FieldAccess
        ):
            obj = rhs_expr.func.the_object
            if isinstance(obj, frog_ast.Variable):
                args = ", ".join(_pretty_print_expr(a) for a in rhs_expr.args)
                return decl + [f"{lhs} <@ {obj.name}.{rhs_expr.func.name}({args});"]
        rhs = _pretty_print_expr(rhs_expr)
        return decl + [f"{lhs} = {rhs};"]
    if isinstance(stmt, frog_ast.ReturnStatement):
        if isinstance(stmt.expression, frog_ast.FuncCall) and isinstance(
            stmt.expression.func, frog_ast.FieldAccess
        ):
            obj = stmt.expression.func.the_object
            if isinstance(obj, frog_ast.Variable):
                args = ", ".join(_pretty_print_expr(a) for a in stmt.expression.args)
                return [f"return <@ {obj.name}.{stmt.expression.func.name}({args});"]
        return [f"return {_pretty_print_expr(stmt.expression)};"]
    if isinstance(stmt, frog_ast.IfStatement):
        out: list[str] = []
        for i, (cond, block) in enumerate(zip(stmt.conditions, stmt.blocks)):
            head = "if" if i == 0 else "elif"
            out.append(f"{head} ({_pretty_print_expr(cond)}) {{")
            for inner in block.statements:
                for line in _pretty_print_stmt(inner):
                    out.append(f"  {line}")
            out.append("}")
        if len(stmt.blocks) > len(stmt.conditions):
            out.append("else {")
            for inner in stmt.blocks[-1].statements:
                for line in _pretty_print_stmt(inner):
                    out.append(f"  {line}")
            out.append("}")
        return out
    return [f"(* unsupported: {type(stmt).__name__} *)"]


def _pretty_print_expr(expr: frog_ast.Expression) -> str:
    if isinstance(expr, frog_ast.Variable):
        return expr.name
    if isinstance(expr, frog_ast.FieldAccess):
        return f"{_pretty_print_expr(expr.the_object)}.{expr.name}"
    if isinstance(expr, frog_ast.FuncCall):
        args = ", ".join(_pretty_print_expr(a) for a in expr.args)
        return f"{_pretty_print_expr(expr.func)}({args})"
    if isinstance(expr, frog_ast.BinaryOperation):
        return (
            f"({_pretty_print_expr(expr.left_expression)} "
            f"{expr.operator} "
            f"{_pretty_print_expr(expr.right_expression)})"
        )
    if isinstance(expr, frog_ast.Tuple):
        return "(" + ", ".join(_pretty_print_expr(v) for v in expr.values) + ")"
    if isinstance(expr, frog_ast.ArrayAccess):
        return (
            f"{_pretty_print_expr(expr.the_array)}"
            f"[{_pretty_print_expr(expr.index)}]"
        )
    return repr(expr)


def _type_text(t: frog_ast.Type | None) -> str:
    if t is None:
        return "?"
    return str(t)


# ---------------------------------------------------------------------------
# Shared normalization (moved from exporter.py)
# ---------------------------------------------------------------------------


def _normalize_for_ec(
    game: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
) -> frog_ast.Game:
    """Make a canonicalized game AST consumable by the shared translators.

    Two passes:

    1. Rewrite local variable names that aren't valid EC local
       identifiers (start with non-lowercase, contain ``.`` or ``@``).
       Synthetic names like ``CE.Enc@k1`` become ``v_CE_Enc_k1``.
       Module references like ``E1`` are not renamed (they don't
       appear in the local-variable name set).
    2. Hoist nested module function-calls into separate
       ``<type> _r0 = E.method(...)`` statements so the shared
       statement translator sees only top-level module calls.
    """
    rename_map = _build_local_rename_map(game)
    if rename_map:
        _apply_rename(game, rename_map)
    for method in game.methods:
        method.block = frog_ast.Block(
            _hoist_block(
                list(method.block.statements),
                external_module_types,
                method_return_types,
            )
        )
    return game


# --- Identifier mangling --------------------------------------------------

_VALID_EC_LOCAL = re.compile(r"^[a-z_][A-Za-z0-9_]*$")


def _ec_ident(name: str) -> str:
    """Mangle ``name`` into a valid EC local variable identifier.

    Replaces non-word characters (``.``, ``@``, etc.) with ``_`` and
    prefixes with ``v_`` if the result doesn't start with a lowercase
    letter or underscore (EC convention for local procedure variables).
    """
    mangled = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not mangled or not (mangled[0].islower() or mangled[0] == "_"):
        mangled = "v_" + mangled
    return mangled


def _build_local_rename_map(game: frog_ast.Game) -> dict[str, str]:
    """Collect names that bind local variables; rename invalid ones."""
    locals_seen: set[str] = set()
    for method in game.methods:
        for p in method.signature.parameters:
            locals_seen.add(p.name)
        _collect_locals(method.block.statements, locals_seen)
    rename_map: dict[str, str] = {}
    for name in locals_seen:
        if not _VALID_EC_LOCAL.match(name):
            rename_map[name] = _ec_ident(name)
    return rename_map


def _collect_locals(stmts: Sequence[frog_ast.Statement], out: set[str]) -> None:
    for stmt in stmts:
        if isinstance(stmt, frog_ast.VariableDeclaration):
            out.add(stmt.name)
        elif isinstance(stmt, frog_ast.Sample) and isinstance(
            stmt.var, frog_ast.Variable
        ):
            out.add(stmt.var.name)
        elif isinstance(stmt, frog_ast.Assignment) and isinstance(
            stmt.var, frog_ast.Variable
        ):
            out.add(stmt.var.name)
        elif isinstance(stmt, frog_ast.IfStatement):
            for block in stmt.blocks:
                _collect_locals(block.statements, out)


def _apply_rename(game: frog_ast.Game, rename_map: dict[str, str]) -> None:
    """Apply ``rename_map`` to every Variable.name and binding-name in place."""
    for method in game.methods:
        for stmt in method.block.statements:
            _rename_stmt(stmt, rename_map)


def _rename_stmt(stmt: frog_ast.Statement, rename: dict[str, str]) -> None:
    if isinstance(stmt, frog_ast.VariableDeclaration):
        if stmt.name in rename:
            stmt.name = rename[stmt.name]
        return
    if isinstance(stmt, frog_ast.Sample):
        _rename_expr(stmt.var, rename)
        _rename_expr(stmt.sampled_from, rename)
        return
    if isinstance(stmt, frog_ast.Assignment):
        _rename_expr(stmt.var, rename)
        _rename_expr(stmt.value, rename)
        return
    if isinstance(stmt, frog_ast.ReturnStatement):
        _rename_expr(stmt.expression, rename)
        return
    if isinstance(stmt, frog_ast.IfStatement):
        for cond in stmt.conditions:
            _rename_expr(cond, rename)
        for block in stmt.blocks:
            for inner in block.statements:
                _rename_stmt(inner, rename)
        return
    if isinstance(stmt, frog_ast.FuncCall):
        _rename_expr(stmt, rename)
        return


def _rename_expr(expr: frog_ast.Expression, rename: dict[str, str]) -> None:
    if isinstance(expr, frog_ast.Variable):
        if expr.name in rename:
            expr.name = rename[expr.name]
        return
    if isinstance(expr, frog_ast.FieldAccess):
        _rename_expr(expr.the_object, rename)
        return
    if isinstance(expr, frog_ast.FuncCall):
        _rename_expr(expr.func, rename)
        for a in expr.args:
            _rename_expr(a, rename)
        return
    if isinstance(expr, frog_ast.BinaryOperation):
        _rename_expr(expr.left_expression, rename)
        _rename_expr(expr.right_expression, rename)
        return
    if isinstance(expr, frog_ast.Tuple):
        for v in expr.values:
            _rename_expr(v, rename)
        return
    if isinstance(expr, frog_ast.ArrayAccess):
        _rename_expr(expr.the_array, rename)
        _rename_expr(expr.index, rename)
        return
    if isinstance(expr, frog_ast.Slice):
        _rename_expr(expr.the_array, rename)
        _rename_expr(expr.start, rename)
        _rename_expr(expr.end, rename)
        return
    if isinstance(expr, frog_ast.UnaryOperation):
        _rename_expr(expr.expression, rename)
        return


# --- Nested module-call hoisting ------------------------------------------


def _is_module_call(
    expr: frog_ast.Expression, external_module_types: dict[str, str]
) -> bool:
    if not isinstance(expr, frog_ast.FuncCall):
        return False
    if not isinstance(expr.func, frog_ast.FieldAccess):
        return False
    obj = expr.func.the_object
    return isinstance(obj, frog_ast.Variable) and obj.name in external_module_types


def _module_call_return_type(
    expr: frog_ast.FuncCall,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
) -> frog_ast.Type | None:
    """Return the per-instance return type of a module call.

    The method-return-type registry holds the generic primitive return
    type (e.g. ``Variable("Ciphertext")``). For a call on a specific
    instance ``E1.Enc(...)`` we want ``E1.Ciphertext`` (which the
    TypeCollector resolves to the concretized ``CiphertextSpace1``).
    """
    if not isinstance(expr.func, frog_ast.FieldAccess):
        return None
    obj = expr.func.the_object
    if not isinstance(obj, frog_ast.Variable):
        return None
    prim = external_module_types.get(obj.name)
    if prim is None:
        return None
    raw_type = method_return_types.get((prim, expr.func.name))
    if raw_type is None:
        return None
    if isinstance(raw_type, frog_ast.Variable):
        return frog_ast.FieldAccess(frog_ast.Variable(obj.name), raw_type.name)
    if isinstance(raw_type, frog_ast.BitStringType):
        # The primitive's signature uses bare field names
        # (``BitString<lambda + stretch>``). Wrap each Variable reference
        # in a ``FieldAccess(<instance>, name)`` so the TypeCollector's
        # alias map resolves it through THIS instance's concretized
        # fields rather than the primary's.
        if raw_type.parameterization is None:
            return raw_type
        return frog_ast.BitStringType(
            _qualify_field_refs(raw_type.parameterization, obj.name)
        )
    return raw_type


def _qualify_field_refs(
    expr: frog_ast.Expression, qualifier: str
) -> frog_ast.Expression:
    """Rewrite each ``Variable(x)`` to ``FieldAccess(Variable(qualifier), x)``.

    Used to specialize a primitive's generic return type to a specific
    instance. The TypeCollector then resolves the qualified name through
    its alias map (e.g. ``G.lambda`` -> ``Variable("lambda")``).
    """
    if isinstance(expr, frog_ast.Variable):
        return frog_ast.FieldAccess(frog_ast.Variable(qualifier), expr.name)
    if isinstance(expr, frog_ast.BinaryOperation):
        return frog_ast.BinaryOperation(
            expr.operator,
            _qualify_field_refs(expr.left_expression, qualifier),
            _qualify_field_refs(expr.right_expression, qualifier),
        )
    if isinstance(expr, frog_ast.UnaryOperation):
        return frog_ast.UnaryOperation(
            expr.operator, _qualify_field_refs(expr.expression, qualifier)
        )
    return expr


class _Hoister:
    """Replace nested module calls in an expression with fresh-name variables."""

    def __init__(
        self,
        external_module_types: dict[str, str],
        method_return_types: dict[tuple[str, str], frog_ast.Type],
        counter: list[int],
    ) -> None:
        self.external_module_types = external_module_types
        self.method_return_types = method_return_types
        self.pre: list[frog_ast.Statement] = []
        self.counter = counter

    def fresh(self) -> str:
        name = f"_r{self.counter[0]}"
        self.counter[0] += 1
        return name

    def visit(self, expr: frog_ast.Expression) -> frog_ast.Expression:
        """Recurse: rewrite all sub-FuncCalls; the *outer* call (if any)
        is processed by the caller separately."""
        if isinstance(expr, frog_ast.FuncCall):
            new_args = [self._hoist_sub(a) for a in expr.args]
            if isinstance(expr.func, frog_ast.FieldAccess):
                new_obj = self.visit(expr.func.the_object)
                new_func: frog_ast.Expression = frog_ast.FieldAccess(
                    new_obj, expr.func.name
                )
            else:
                new_func = self.visit(expr.func)
            return frog_ast.FuncCall(new_func, new_args)
        if isinstance(expr, frog_ast.Tuple):
            return frog_ast.Tuple([self._hoist_sub(v) for v in expr.values])
        if isinstance(expr, frog_ast.BinaryOperation):
            new_left = self._hoist_sub(expr.left_expression)
            new_right = self._hoist_sub(expr.right_expression)
            return frog_ast.BinaryOperation(expr.operator, new_left, new_right)
        if isinstance(expr, frog_ast.ArrayAccess):
            return frog_ast.ArrayAccess(
                self._hoist_sub(expr.the_array), self._hoist_sub(expr.index)
            )
        if isinstance(expr, frog_ast.FieldAccess):
            return frog_ast.FieldAccess(self._hoist_sub(expr.the_object), expr.name)
        if isinstance(expr, frog_ast.Slice):
            return frog_ast.Slice(
                self._hoist_sub(expr.the_array),
                self._hoist_sub(expr.start),
                self._hoist_sub(expr.end),
            )
        if isinstance(expr, frog_ast.UnaryOperation):
            return frog_ast.UnaryOperation(
                expr.operator, self._hoist_sub(expr.expression)
            )
        return expr

    def _hoist_sub(self, expr: frog_ast.Expression) -> frog_ast.Expression:
        """Like ``visit``, but if the result is itself a module call,
        hoist it to a fresh variable."""
        rewritten = self.visit(expr)
        if _is_module_call(rewritten, self.external_module_types):
            assert isinstance(rewritten, frog_ast.FuncCall)
            ret_type = _module_call_return_type(
                rewritten, self.external_module_types, self.method_return_types
            )
            assert (
                ret_type is not None
            ), f"Cannot determine return type for hoisted call: {rewritten}"
            name = self.fresh()
            self.pre.append(
                frog_ast.Assignment(
                    the_type=ret_type,
                    var=frog_ast.Variable(name),
                    value=rewritten,
                )
            )
            return frog_ast.Variable(name)
        return rewritten


def _hoist_block(
    stmts: list[frog_ast.Statement],
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
) -> list[frog_ast.Statement]:
    """Hoist nested module calls in every statement of a block."""
    counter = [0]
    out: list[frog_ast.Statement] = []
    for stmt in stmts:
        new_pre, new_stmt = _hoist_stmt(
            stmt, external_module_types, method_return_types, counter
        )
        out.extend(new_pre)
        out.append(new_stmt)
    return out


def _hoist_stmt(
    stmt: frog_ast.Statement,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    counter: list[int],
) -> tuple[list[frog_ast.Statement], frog_ast.Statement]:
    hoister = _Hoister(external_module_types, method_return_types, counter)
    if isinstance(stmt, frog_ast.Assignment):
        new_value = hoister.visit(stmt.value)
        return hoister.pre, frog_ast.Assignment(
            the_type=stmt.the_type, var=stmt.var, value=new_value
        )
    if isinstance(stmt, frog_ast.Sample):
        new_sampled = hoister.visit(stmt.sampled_from)
        return hoister.pre, frog_ast.Sample(
            the_type=stmt.the_type, var=stmt.var, sampled_from=new_sampled
        )
    if isinstance(stmt, frog_ast.ReturnStatement):
        # Top-level module call in a return: leave intact. Hoist only
        # nested calls.
        if _is_module_call(stmt.expression, external_module_types):
            return hoister.pre, stmt
        new_expr = hoister.visit(stmt.expression)
        return hoister.pre, frog_ast.ReturnStatement(new_expr)
    return [], stmt
