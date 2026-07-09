"""Translate FrogLang statements to EasyCrypt statements.

Supported: VariableDeclaration, Sample, ReturnStatement (including
return-value lifting for module calls), and Assignment whose RHS is a
FuncCall on a module parameter (e.g. ``E.method(...)``). Nested module
calls in argument position (``f(g(x))``) are flattened into preceding
``<@`` statements, since EC has no nested proc calls. All ``var`` decls
for locally-declared variables are hoisted to the top of the enclosing
proc (handled by translate_block).
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ec_ast
from . import expr_translator
from . import type_collector as tc
from ... import frog_ast


@dataclass
class TranslatedBlock:
    """Pair of var declarations to hoist and the remaining statements."""

    var_decls: list[ec_ast.VarDecl]
    stmts: list[ec_ast.EcStmt]


class StatementTranslator:
    """Translate a FrogLang Block to an EC var-decl list + stmt list."""

    def __init__(
        self,
        types: tc.TypeCollector,
        exprs: expr_translator.ExpressionTranslator,
        module_var_aliases: dict[str, str] | None = None,
        allow_void_call: bool = False,
    ) -> None:
        self._types = types
        self._exprs = exprs
        self._module_var_aliases: dict[str, str] = dict(module_var_aliases or {})
        # When True, a bare module-call statement whose (unit) result is
        # discarded -- e.g. a reduction's ``challenger.Initialize();`` -- is
        # rendered as a result-less EC call. Off by default so every existing
        # caller keeps its byte-identical behavior (such a statement otherwise
        # raises NotImplementedError -> the method body falls back to
        # ``return witness``). Enabled only by the group-only export path.
        self._allow_void_call = allow_void_call

    def translate_block(
        self,
        block: frog_ast.Block,
        return_type: ec_ast.EcType | None = None,
    ) -> TranslatedBlock:
        """Translate every statement; hoist all var decls to the front.

        ``return_type`` is the proc's EC return type, used to type the
        fresh variable when lifting a module call in return position
        (``return E.method(...)``). The call's result type equals the
        proc's declared return type, which is always concretely
        translatable — unlike the oracle method's abstract signature type
        (e.g. INDOT$'s ``E.Ciphertext``), which the TypeCollector can't
        resolve on its own.
        """
        decls: list[ec_ast.VarDecl] = []
        stmts: list[ec_ast.EcStmt] = []
        statements = list(block.statements)
        for i, stmt in enumerate(statements):
            rest = statements[i + 1 :]
            # Guarded early return: ``if (g) { ...; return X; } <rest>; return Y``
            # (a case-split oracle -- e.g. the CFRG binding reductions'
            # ``Challenge`` forwarding to ``challenger.Challenge`` on a
            # collision guard). EC procedures are single-exit, so lower this to
            # a result variable set in both branches, with ``rest`` becoming the
            # ``else``. Only fires on this exact shape (single-condition ``if``,
            # no ``else``, then-block ending in a return, a fall-through final
            # return); any other control flow falls through to the per-statement
            # translator, whose ``NotImplementedError`` yields the historical
            # ``return witness`` stub -- so unaffected bodies stay byte-identical.
            if (
                isinstance(stmt, frog_ast.IfStatement)
                and self._is_guarded_early_return(stmt)
                and rest
                and isinstance(rest[-1], frog_ast.ReturnStatement)
            ):
                self._handle_guarded_early_return(stmt, rest, decls, stmts, return_type)
                return TranslatedBlock(decls, stmts)
            self._translate_stmt(stmt, decls, stmts, return_type)
        return TranslatedBlock(decls, stmts)

    @staticmethod
    def _is_guarded_early_return(stmt: frog_ast.Statement) -> bool:
        """True for ``if (g) { ...; return X; }`` with no ``else`` clause."""
        return (
            isinstance(stmt, frog_ast.IfStatement)
            and len(stmt.conditions) == 1
            and not stmt.has_else_block()
            and len(stmt.blocks) == 1
            and bool(stmt.blocks[0].statements)
            and isinstance(stmt.blocks[0].statements[-1], frog_ast.ReturnStatement)
        )

    def _handle_guarded_early_return(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        if_stmt: frog_ast.IfStatement,
        rest: list[frog_ast.Statement],
        decls: list[ec_ast.VarDecl],
        stmts: list[ec_ast.EcStmt],
        return_type: ec_ast.EcType | None,
    ) -> None:
        if return_type is None:
            raise NotImplementedError(
                "guarded early return needs the proc return type for the "
                "result variable"
            )
        then_block = list(if_stmt.blocks[0].statements)
        # Reserve a result name that avoids every hoister-introduced ``_rN`` in
        # the then-block and the fall-through ``rest`` (translated below), not
        # just the already-emitted prefix.
        avoid = _collect_bound_names(then_block) | _collect_bound_names(rest)
        result = _fresh_name_avoiding(decls, stmts, avoid)
        decls.append(ec_ast.VarDecl(result, return_type))

        then_stmts: list[ec_ast.EcStmt] = []
        for s in then_block[:-1]:
            self._translate_stmt(s, decls, then_stmts, return_type)
        self._lower_return_to(result, then_block[-1], decls, then_stmts)

        else_stmts: list[ec_ast.EcStmt] = []
        for s in rest[:-1]:
            self._translate_stmt(s, decls, else_stmts, return_type)
        self._lower_return_to(result, rest[-1], decls, else_stmts)

        guard = self._exprs.translate(if_stmt.conditions[0])
        stmts.append(ec_ast.If(guard, then_stmts, else_stmts))
        stmts.append(ec_ast.Return(result))

    def _lower_return_to(
        self,
        result: str,
        ret_stmt: frog_ast.Statement,
        decls: list[ec_ast.VarDecl],
        out_stmts: list[ec_ast.EcStmt],
    ) -> None:
        """Render ``return X`` as an assignment ``result <- X`` / ``result <@ X``."""
        assert isinstance(ret_stmt, frog_ast.ReturnStatement)
        expr = ret_stmt.expression
        if _is_module_call(expr):
            assert isinstance(expr, frog_ast.FuncCall)
            callee = self._render_module_call_target(expr.func)
            args = self._render_call_args(expr, decls, out_stmts)
            out_stmts.append(ec_ast.Call(result, callee, args))
            return
        out_stmts.append(ec_ast.Assign(result, self._exprs.translate(expr)))

    def _translate_stmt(
        self,
        stmt: frog_ast.Statement,
        decls: list[ec_ast.VarDecl],
        stmts: list[ec_ast.EcStmt],
        return_type: ec_ast.EcType | None = None,
    ) -> None:
        if isinstance(stmt, frog_ast.Sample):
            self._handle_sample(stmt, decls, stmts)
            return
        if isinstance(stmt, frog_ast.VariableDeclaration):
            self._handle_var_decl(stmt, decls)
            return
        if isinstance(stmt, frog_ast.Assignment):
            self._handle_assign(stmt, decls, stmts)
            return
        if isinstance(stmt, frog_ast.ReturnStatement):
            if _is_module_call(stmt.expression):
                call = stmt.expression
                assert isinstance(call, frog_ast.FuncCall)
                # The lifted call's result is returned directly, so its
                # type is the proc's declared return type. Prefer that
                # (always concretely translatable) over the oracle
                # method's abstract signature type, which may be an
                # unresolvable cross-scheme alias like ``E.Ciphertext``.
                if return_type is not None:
                    ec_type = return_type
                else:
                    ec_type = self._types.translate_type(self._exprs.type_of(call))
                args = self._render_call_args(call, decls, stmts)
                fresh = _fresh_name(decls, stmts)
                decls.append(ec_ast.VarDecl(fresh, ec_type))
                callee = self._render_module_call_target(call.func)
                stmts.append(ec_ast.Call(fresh, callee, args))
                stmts.append(ec_ast.Return(fresh))
                return
            # The returned expression may embed module calls (EC has no calls
            # inside expressions): e.g. the KDF collision-resistance challenger
            # returns ``H.evaluate(x0) == H.evaluate(x1) && x0 != x1``. Hoist
            # every embedded call into a preceding ``<@`` statement, then
            # return the now call-free expression.
            hoisted = self._hoist_calls_in_expr(stmt.expression, decls, stmts)
            stmts.append(ec_ast.Return(self._exprs.translate(hoisted)))
            return
        if (
            self._allow_void_call
            and isinstance(stmt, frog_ast.FuncCall)
            and _is_module_call(stmt)
        ):
            # A bare module call whose (unit) result is discarded, e.g. a
            # reduction's ``challenger.Initialize();``. EC renders it without a
            # result binding (``Challenger.initialize();``).
            callee = self._render_module_call_target(stmt.func)
            args = self._render_call_args(stmt, decls, stmts)
            stmts.append(ec_ast.Call("", callee, args))
            return
        raise NotImplementedError(
            f"Statement translation not implemented for "
            f"{type(stmt).__name__}: {stmt}"
        )

    def _handle_sample(
        self,
        stmt: frog_ast.Sample,
        decls: list[ec_ast.VarDecl],
        stmts: list[ec_ast.EcStmt],
    ) -> None:
        var = _require_variable(stmt.var)
        # A sample's distribution type is its declared annotation when
        # present. The engine's canonicalization can inline an assignment
        # into the sample (e.g. ``sk = a`` folded into ``a <$ d`` yields
        # ``sk <$ d`` with no annotation); in that case the sampled
        # variable's own type is the distribution type, which ``type_of``
        # recovers from the module-field / local type map.
        the_type = stmt.the_type
        if the_type is None:
            the_type = self._exprs.type_of(stmt.var)
        ec_type = self._types.translate_type(the_type)
        decls.append(ec_ast.VarDecl(var.name, ec_type))
        distr = self._types.distr_for(ec_type)
        stmts.append(ec_ast.Sample(var.name, distr))

    def _handle_var_decl(
        self,
        stmt: frog_ast.VariableDeclaration,
        decls: list[ec_ast.VarDecl],
    ) -> None:
        ec_type = self._types.translate_type(stmt.type)
        decls.append(ec_ast.VarDecl(stmt.name, ec_type))

    def _handle_assign(
        self,
        stmt: frog_ast.Assignment,
        decls: list[ec_ast.VarDecl],
        stmts: list[ec_ast.EcStmt],
    ) -> None:
        var = _require_variable(stmt.var)
        if stmt.the_type is not None:
            ec_type = self._types.translate_type(stmt.the_type)
            decls.append(ec_ast.VarDecl(var.name, ec_type))
        if _is_module_call(stmt.value):
            call = stmt.value
            assert isinstance(call, frog_ast.FuncCall)
            callee = self._render_module_call_target(call.func)
            args = self._render_call_args(call, decls, stmts)
            stmts.append(ec_ast.Call(var.name, callee, args))
            return
        rhs = self._exprs.translate(stmt.value)
        stmts.append(ec_ast.Assign(var.name, rhs))

    def _render_module_call_target(self, func: frog_ast.Expression) -> str:
        """Render ``E.KeyGen`` as ``E.keygen``; apply module-var aliases.

        A scheme self-call (``this.DeriveKeyPair`` in FrogLang) renders as
        the bare sibling proc name ``derivekeypair``: EC has no ``this``,
        and within a module a sibling procedure is called by name (it must
        be defined earlier in the module, which scheme-method emission
        order guarantees)."""
        assert isinstance(func, frog_ast.FieldAccess)
        obj = func.the_object
        assert isinstance(obj, frog_ast.Variable)
        if obj.name == "this":
            return func.name.lower()
        obj_name = self._module_var_aliases.get(obj.name, obj.name)
        return f"{obj_name}.{func.name.lower()}"

    def _render_call_args(
        self,
        call: frog_ast.FuncCall,
        decls: list[ec_ast.VarDecl],
        stmts: list[ec_ast.EcStmt],
    ) -> str:
        """Render a module call's arguments as a comma-separated string,
        lifting any nested module call into a preceding ``<@`` statement.

        EC has no nested procedure calls: ``f(g(x))`` with ``f``, ``g``
        both proc calls must become ``r <@ g(x); ... <@ f(r)``. FrogLang
        oracle bodies can nest them (e.g. NGCorrectness's
        ``ElementToSharedSecret(Exp(Exp(Generator(), a), b))``). The
        engine's canonicalization already flattens these in the chain
        flat-states, but the raw oracle/reduction module is emitted from
        the un-canonicalized AST, so we flatten here to match.
        """
        return ", ".join(self._lift_expr(a, decls, stmts) for a in call.args)

    def _lift_expr(
        self,
        expr: frog_ast.Expression,
        decls: list[ec_ast.VarDecl],
        stmts: list[ec_ast.EcStmt],
    ) -> str:
        """Render ``expr`` as an EC expression string. If it is itself a
        module call, lift it (and any calls it nests) into preceding
        ``<@`` statements and return the fresh result variable."""
        if _is_module_call(expr):
            assert isinstance(expr, frog_ast.FuncCall)
            args = self._render_call_args(expr, decls, stmts)
            ec_type = self._types.translate_type(self._exprs.type_of(expr))
            fresh = _fresh_name(decls, stmts)
            decls.append(ec_ast.VarDecl(fresh, ec_type))
            callee = self._render_module_call_target(expr.func)
            stmts.append(ec_ast.Call(fresh, callee, args))
            return fresh
        return self._exprs.translate(expr)

    def _hoist_calls_in_expr(
        self,
        expr: frog_ast.Expression,
        decls: list[ec_ast.VarDecl],
        stmts: list[ec_ast.EcStmt],
    ) -> frog_ast.Expression:
        """Rewrite ``expr``, lifting every embedded module call into a
        preceding ``<@`` statement and substituting the fresh result variable
        in its place. Returns a call-free expression. Children are visited
        left-to-right so the hoisted statements run in source evaluation order.
        Fresh nodes are constructed rather than mutating ``expr`` in place,
        since a method AST may be translated more than once (raw module +
        canonicalized chain states)."""
        if _is_module_call(expr):
            assert isinstance(expr, frog_ast.FuncCall)
            # Nested-call args evaluate before this call, so hoist them first.
            arg_strs = [
                self._exprs.translate(self._hoist_calls_in_expr(a, decls, stmts))
                for a in expr.args
            ]
            ec_type = self._types.translate_type(self._exprs.type_of(expr))
            fresh = _fresh_name(decls, stmts)
            decls.append(ec_ast.VarDecl(fresh, ec_type))
            callee = self._render_module_call_target(expr.func)
            stmts.append(ec_ast.Call(fresh, callee, ", ".join(arg_strs)))
            return frog_ast.Variable(fresh)
        if isinstance(expr, frog_ast.BinaryOperation):
            return frog_ast.BinaryOperation(
                expr.operator,
                self._hoist_calls_in_expr(expr.left_expression, decls, stmts),
                self._hoist_calls_in_expr(expr.right_expression, decls, stmts),
            )
        if isinstance(expr, frog_ast.UnaryOperation):
            return frog_ast.UnaryOperation(
                expr.operator,
                self._hoist_calls_in_expr(expr.expression, decls, stmts),
            )
        if isinstance(expr, frog_ast.Tuple):
            return frog_ast.Tuple(
                [self._hoist_calls_in_expr(v, decls, stmts) for v in expr.values]
            )
        if isinstance(expr, frog_ast.FuncCall):
            # A non-module call (an operator-like builtin, e.g. concat/slice):
            # keep the head, recurse into args.
            return frog_ast.FuncCall(
                expr.func,
                [self._hoist_calls_in_expr(a, decls, stmts) for a in expr.args],
            )
        if isinstance(expr, frog_ast.FieldAccess):
            return frog_ast.FieldAccess(
                self._hoist_calls_in_expr(expr.the_object, decls, stmts),
                expr.name,
            )
        if isinstance(expr, frog_ast.ArrayAccess):
            return frog_ast.ArrayAccess(
                self._hoist_calls_in_expr(expr.the_array, decls, stmts),
                self._hoist_calls_in_expr(expr.index, decls, stmts),
            )
        if isinstance(expr, frog_ast.Slice):
            return frog_ast.Slice(
                self._hoist_calls_in_expr(expr.the_array, decls, stmts),
                self._hoist_calls_in_expr(expr.start, decls, stmts),
                self._hoist_calls_in_expr(expr.end, decls, stmts),
            )
        return expr


def _fresh_name(decls: list[ec_ast.VarDecl], stmts: list[ec_ast.EcStmt]) -> str:
    """Return a var name not used by any decl or stmt in the current block."""
    return _fresh_name_avoiding(decls, stmts, set())


def _fresh_name_avoiding(
    decls: list[ec_ast.VarDecl], stmts: list[ec_ast.EcStmt], avoid: set[str]
) -> str:
    """Like :func:`_fresh_name` but also avoids the names in ``avoid``.

    Used when a fresh name must dodge identifiers that are not yet emitted as
    EC statements -- e.g. hoister-introduced ``_rN`` locals still living in the
    untranslated fall-through of a guarded early return.
    """
    used = {d.name for d in decls} | set(avoid)
    for s in stmts:
        if isinstance(s, (ec_ast.Assign, ec_ast.Sample, ec_ast.Call)):
            used.add(s.var)
    i = 0
    while True:
        candidate = f"_r{i}"
        if candidate not in used:
            return candidate
        i += 1


def _collect_bound_names(frog_stmts: list[frog_ast.Statement]) -> set[str]:
    """Names bound by decls/assignments/samples in ``frog_stmts`` (recursive)."""
    names: set[str] = set()
    for s in frog_stmts:
        if isinstance(s, frog_ast.VariableDeclaration):
            names.add(s.name)
        elif isinstance(s, (frog_ast.Assignment, frog_ast.Sample)):
            if isinstance(s.var, frog_ast.Variable):
                names.add(s.var.name)
        elif isinstance(s, frog_ast.IfStatement):
            for blk in s.blocks:
                names |= _collect_bound_names(list(blk.statements))
    return names


def _require_variable(expr: frog_ast.Expression) -> frog_ast.Variable:
    if not isinstance(expr, frog_ast.Variable):
        raise NotImplementedError(
            f"LHS must be a simple variable in skeleton; got {type(expr).__name__}"
        )
    return expr


def _is_module_call(expr: frog_ast.Expression) -> bool:
    """Recognize ``E.method(...)`` — a FuncCall whose func is a FieldAccess."""
    if not isinstance(expr, frog_ast.FuncCall):
        return False
    return isinstance(expr.func, frog_ast.FieldAccess)
