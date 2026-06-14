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
    ) -> None:
        self._types = types
        self._exprs = exprs
        self._module_var_aliases: dict[str, str] = dict(module_var_aliases or {})

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
        for stmt in block.statements:
            self._translate_stmt(stmt, decls, stmts, return_type)
        return TranslatedBlock(decls, stmts)

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
            stmts.append(ec_ast.Return(self._exprs.translate(stmt.expression)))
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
        if stmt.the_type is None:
            raise NotImplementedError(
                "Sample without type annotation not supported in Phase 1 skeleton"
            )
        ec_type = self._types.translate_type(stmt.the_type)
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


def _fresh_name(decls: list[ec_ast.VarDecl], stmts: list[ec_ast.EcStmt]) -> str:
    """Return a var name not used by any decl or stmt in the current block."""
    used = {d.name for d in decls}
    for s in stmts:
        if isinstance(s, (ec_ast.Assign, ec_ast.Sample, ec_ast.Call)):
            used.add(s.var)
    i = 0
    while True:
        candidate = f"_r{i}"
        if candidate not in used:
            return candidate
        i += 1


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
