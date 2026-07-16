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

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        types: tc.TypeCollector,
        exprs: expr_translator.ExpressionTranslator,
        module_var_aliases: dict[str, str] | None = None,
        allow_void_call: bool = False,
        type_map: dict[str, frog_ast.Type] | None = None,
    ) -> None:
        self._types = types
        self._exprs = exprs
        # The live FrogLang type map the expr translator's ``type_of`` closes
        # over. When a module call is hoisted out of an expression into a fresh
        # ``<@`` temp, or a local is declared mid-lowering, its type is recorded
        # here so a later ``type_of`` of that name resolves.
        self._type_map: dict[str, frog_ast.Type] = (
            type_map if type_map is not None else {}
        )
        self._module_var_aliases: dict[str, str] = dict(module_var_aliases or {})
        # When True, a bare module-call statement whose (unit) result is
        # discarded -- e.g. a reduction's ``challenger.Initialize();`` -- is
        # rendered as a result-less EC call. Off by default so every existing
        # caller keeps its byte-identical behavior (such a statement otherwise
        # raises NotImplementedError -> the method body falls back to
        # ``return witness``). Enabled only by the group-only export path.
        self._allow_void_call = allow_void_call
        # Every name bound anywhere in the method body currently being
        # translated -- in particular the ``_rN`` temps that
        # ``canonical_form.hoist_*_calls`` introduced into the source AST before
        # translation. A statement-level hoist (``_hoist_calls_in_expr``) or a
        # return-lowering allocates its own fresh ``_rN`` by scanning only the
        # already-emitted prefix, so without this it can re-pick an ``_rN`` that
        # a source hoist uses LATER in the same proc -> EC "duplicated
        # local/parameters name". Seeded at ``translate_block`` entry.
        self._reserved_names: set[str] = set()

    def _is_map(self, expr: frog_ast.Expression) -> bool:
        """True if ``expr`` has a FrogLang finite-map type ``Map<K, V>``."""
        try:
            resolved = self._types.resolve(self._exprs.type_of(expr))
        except (NotImplementedError, KeyError):
            return False
        return isinstance(resolved, frog_ast.MapType)

    def _translate_expr(
        self,
        expr: frog_ast.Expression,
        decls: list[ec_ast.VarDecl],
        out_stmts: list[ec_ast.EcStmt],
    ) -> str:
        """Render a statement-context expression, lifting any embedded module
        call to a preceding ``<@`` (EC has no calls inside expressions). Gated
        on the expr actually containing a module call, so a call-free expr
        takes the direct path unchanged (byte-identical)."""
        if _expr_has_module_call(expr):
            expr = self._hoist_calls_in_expr(expr, decls, out_stmts)
        return self._exprs.translate(expr)

    def _is_optional_expr(self, expr: frog_ast.Expression) -> bool:
        """True if ``expr`` already has an optional (``T?``) type.

        A return of such an expression in an optional proc must NOT be
        re-wrapped in ``Some`` (that would double-wrap to ``T option option``);
        only a base-typed value is coerced up. Errs to ``False`` (wrap) when
        the type is unknown -- the historical behavior for a plain value."""
        try:
            return self._types.translate_type(self._exprs.type_of(expr)).text.endswith(
                " option"
            )
        except (NotImplementedError, KeyError):
            return False

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
        # Reserve every name bound anywhere in this method's source body so a
        # statement-level hoist never re-picks a source ``_rN`` that appears
        # later (see ``self._reserved_names``).
        self._reserved_names = _collect_bound_names(statements)
        # A body with EC-inexpressible control flow (an ``if`` case-split whose
        # branches early-return, a lazy-RO ``if (m == mStar) { return yStar }``
        # exclusion, or a ``for e in m.entries`` map loop) is lowered to a
        # single-exit form: one ``result`` variable, control flow rewritten with
        # ``returned`` flags, and a trailing ``return result``. A straight-line
        # body with no such construct takes the historical per-statement path
        # unchanged (byte-identical).
        if return_type is not None and self._block_needs_lowering(statements):
            result = _fresh_name_avoiding(
                decls, stmts, _collect_bound_names(statements)
            )
            decls.append(ec_ast.VarDecl(result, return_type))
            self._lower_block(statements, decls, stmts, return_type, result)
            stmts.append(ec_ast.Return(result))
            return TranslatedBlock(_dedup_decls(decls), stmts)
        for stmt in statements:
            self._translate_stmt(stmt, decls, stmts, return_type)
        return TranslatedBlock(decls, stmts)

    def _block_needs_lowering(self, statements: list[frog_ast.Statement]) -> bool:
        """True if a top-level statement is a control-flow construct that the
        single-exit lowering handles (a guarded/general ``if`` or a map loop)."""
        return any(
            self._is_guarded_early_return(s)
            or (isinstance(s, frog_ast.IfStatement) and len(s.conditions) == 1)
            or self._is_map_for_early_return(s)
            for s in statements
        )

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
        self._lower_block(then_block, decls, then_stmts, return_type, result)
        else_stmts: list[ec_ast.EcStmt] = []
        self._lower_block(rest, decls, else_stmts, return_type, result)

        guard = self._exprs.translate(if_stmt.conditions[0])
        stmts.append(ec_ast.If(guard, then_stmts, else_stmts))
        stmts.append(ec_ast.Return(result))

    def _lower_block(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-branches
        self,
        statements: list[frog_ast.Statement],
        decls: list[ec_ast.VarDecl],
        out_stmts: list[ec_ast.EcStmt],
        return_type: ec_ast.EcType | None,
        result: str,
        returned_flag: str | None = None,
    ) -> None:
        """Lower a straight-line block into a single-exit form writing ``result``.

        Handles a guarded early return, a general ``if``/``if-else`` whose
        branches may or may not return (lowered with a fresh ``returned`` flag
        so the code after the ``if`` runs only on the no-return paths), a
        map-iteration for-loop, and a bare ``return``; every other statement
        translates in place. ``returned_flag`` (set when lowering a branch of an
        enclosing general ``if``) is propagated so a return deep inside also
        skips the enclosing fall-through."""
        for i, stmt in enumerate(statements):
            rest = statements[i + 1 :]
            if self._is_guarded_early_return(stmt):
                assert isinstance(stmt, frog_ast.IfStatement)
                inner_then: list[ec_ast.EcStmt] = []
                self._lower_block(
                    list(stmt.blocks[0].statements),
                    decls,
                    inner_then,
                    return_type,
                    result,
                    returned_flag,
                )
                inner_else: list[ec_ast.EcStmt] = []
                self._lower_block(
                    rest, decls, inner_else, return_type, result, returned_flag
                )
                guard = self._translate_expr(stmt.conditions[0], decls, out_stmts)
                out_stmts.append(ec_ast.If(guard, inner_then, inner_else))
                return
            if isinstance(stmt, frog_ast.IfStatement) and len(stmt.conditions) == 1:
                self._lower_general_if(
                    stmt, rest, decls, out_stmts, return_type, result, returned_flag
                )
                return
            if self._is_map_for_early_return(stmt):
                assert isinstance(stmt, frog_ast.GenericFor)
                self._lower_map_for(stmt, rest, decls, out_stmts, return_type, result)
                return
            if isinstance(stmt, frog_ast.ReturnStatement):
                self._lower_return_to(
                    result, stmt, decls, out_stmts, return_type, returned_flag
                )
                return
            self._translate_stmt(stmt, decls, out_stmts, return_type)

    def _lower_general_if(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        stmt: frog_ast.IfStatement,
        rest: list[frog_ast.Statement],
        decls: list[ec_ast.VarDecl],
        out_stmts: list[ec_ast.EcStmt],
        return_type: ec_ast.EcType | None,
        result: str,
        returned_flag: str | None,
    ) -> None:
        """Lower ``if (g) { A } [else { B }] <rest>`` where a branch may or may
        not return. A fresh ``flag`` records whether either branch returned;
        ``rest`` runs guarded on ``! flag`` (the no-return continuation), and a
        return inside the ``if`` propagates to any enclosing ``returned_flag``."""
        avoid = _collect_bound_names(rest)
        for blk in stmt.blocks:
            avoid |= _collect_bound_names(list(blk.statements))
        flag = _fresh_name_avoiding(decls, out_stmts, avoid)
        decls.append(ec_ast.VarDecl(flag, ec_ast.EcType("bool")))
        out_stmts.append(ec_ast.Assign(flag, "false"))
        guard = self._translate_expr(stmt.conditions[0], decls, out_stmts)
        then_out: list[ec_ast.EcStmt] = []
        self._lower_block(
            list(stmt.blocks[0].statements), decls, then_out, return_type, result, flag
        )
        else_out: list[ec_ast.EcStmt] = []
        if len(stmt.blocks) > 1:
            self._lower_block(
                list(stmt.blocks[1].statements),
                decls,
                else_out,
                return_type,
                result,
                flag,
            )
        out_stmts.append(ec_ast.If(guard, then_out, else_out))
        fall: list[ec_ast.EcStmt] = []
        self._lower_block(rest, decls, fall, return_type, result, returned_flag)
        if fall:
            out_stmts.append(ec_ast.If(f"! {flag}", fall, []))
        if returned_flag is not None:
            out_stmts.append(
                ec_ast.If(flag, [ec_ast.Assign(returned_flag, "true")], [])
            )

    def _is_map_for_early_return(self, stmt: frog_ast.Statement) -> bool:
        """True for ``for ([K,V] e in m.entries) { ... }`` over a finite map."""
        if not isinstance(stmt, frog_ast.GenericFor):
            return False
        over = stmt.over
        return (
            isinstance(over, frog_ast.FieldAccess)
            and over.name == "entries"
            and self._is_map(over.the_object)
        )

    def _lower_map_for(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        for_stmt: frog_ast.GenericFor,
        rest: list[frog_ast.Statement],
        decls: list[ec_ast.VarDecl],
        out_stmts: list[ec_ast.EcStmt],
        return_type: ec_ast.EcType | None,
        result: str,
    ) -> None:
        """Lower ``for e in m.entries { ...; return X } <rest>`` to an EC while.

        FrogLang iterates the map's entries and may ``return`` mid-loop; EC
        procedures are single-exit, so this emits a found-flag loop over the
        key list ``elems (fdom m)`` -- binding ``e = (k, oget m.[k])`` each
        iteration, firing the match body (which writes ``result`` and sets
        ``found``) only while ``!found`` -- and guards the fall-through
        ``rest`` on ``!found``."""
        over = for_stmt.over
        assert isinstance(over, frog_ast.FieldAccess)
        map_txt = self._exprs.translate(over.the_object)
        map_type = self._types.resolve(self._exprs.type_of(over.the_object))
        assert isinstance(map_type, frog_ast.MapType)
        key_ec = self._types.translate_type(map_type.key_type).text
        # ``T list`` binds ``list`` tighter than ``*``, so a product key type
        # ``A * B`` must be parenthesized: ``(A * B) list``, not ``A * B list``
        # (which EC reads as ``A * (B list)``).
        key_list_ec = f"({key_ec}) list" if " * " in key_ec else f"{key_ec} list"

        e_name = for_stmt.var_name
        decls.append(
            ec_ast.VarDecl(e_name, self._types.translate_type(for_stmt.var_type))
        )
        avoid = (
            _collect_bound_names(list(for_stmt.block.statements))
            | _collect_bound_names(rest)
            | {e_name}
        )
        found = _fresh_name_avoiding(decls, out_stmts, avoid)
        decls.append(ec_ast.VarDecl(found, ec_ast.EcType("bool")))
        keys = _fresh_name_avoiding(decls, out_stmts, avoid)
        decls.append(ec_ast.VarDecl(keys, ec_ast.EcType(key_list_ec)))
        idx = _fresh_name_avoiding(decls, out_stmts, avoid)
        decls.append(ec_ast.VarDecl(idx, ec_ast.EcType("int")))

        out_stmts.append(ec_ast.Assign(found, "false"))
        out_stmts.append(ec_ast.Assign(keys, f"elems (fdom {map_txt})"))
        out_stmts.append(ec_ast.Assign(idx, "0"))

        nth_key = f"nth witness {keys} {idx}"
        loop_body: list[ec_ast.EcStmt] = [
            ec_ast.Assign(e_name, f"({nth_key}, oget {map_txt}.[{nth_key}])")
        ]
        self._lower_loop_body(
            list(for_stmt.block.statements),
            decls,
            loop_body,
            return_type,
            result,
            found,
        )
        loop_body.append(ec_ast.Assign(idx, f"{idx} + 1"))
        out_stmts.append(ec_ast.While(f"{idx} < size {keys}", loop_body))

        fall: list[ec_ast.EcStmt] = []
        self._lower_block(rest, decls, fall, return_type, result)
        if fall:
            out_stmts.append(ec_ast.If(f"! {found}", fall, []))

    def _lower_loop_body(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        statements: list[frog_ast.Statement],
        decls: list[ec_ast.VarDecl],
        out_stmts: list[ec_ast.EcStmt],
        return_type: ec_ast.EcType | None,
        result: str,
        found: str,
    ) -> None:
        r"""Translate a map-loop body whose match arm ends in a ``return``.

        The arm ``if (COND) { ...; return X }`` becomes ``if (COND /\ !found)
        { ...; result <- X; found <- true }`` so the first matching entry wins
        and later iterations are inert; other statements translate in place."""
        for stmt in statements:
            if self._is_guarded_early_return(stmt):
                assert isinstance(stmt, frog_ast.IfStatement)
                body = list(stmt.blocks[0].statements)
                then_stmts: list[ec_ast.EcStmt] = []
                for s in body[:-1]:
                    self._translate_stmt(s, decls, then_stmts, return_type)
                self._lower_return_to(result, body[-1], decls, then_stmts, return_type)
                then_stmts.append(ec_ast.Assign(found, "true"))
                guard = self._translate_expr(stmt.conditions[0], decls, out_stmts)
                out_stmts.append(ec_ast.If(f"({guard}) /\\ ! {found}", then_stmts, []))
            else:
                self._translate_stmt(stmt, decls, out_stmts, return_type)

    def _lower_return_to(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        result: str,
        ret_stmt: frog_ast.Statement,
        decls: list[ec_ast.VarDecl],
        out_stmts: list[ec_ast.EcStmt],
        return_type: ec_ast.EcType | None = None,
        returned_flag: str | None = None,
    ) -> None:
        """Render ``return X`` as an assignment ``result <- X`` / ``result <@ X``.

        When the proc returns an optional (``T?`` -> ``T option``), a ``None``
        return stays ``None`` and any other return is wrapped ``Some (...)``.
        ``returned_flag``, when a branch of a general ``if`` lowers this return,
        is set ``true`` so the code after the ``if`` is skipped."""
        assert isinstance(ret_stmt, frog_ast.ReturnStatement)
        expr = ret_stmt.expression
        optional = return_type is not None and return_type.text.endswith(" option")
        if isinstance(expr, frog_ast.NoneExpression):
            out_stmts.append(ec_ast.Assign(result, "None"))
        else:
            # Wrap ``Some`` only when coercing a *base* value up into the
            # optional; an already-optional expression is returned as-is.
            wrap = optional and not self._is_optional_expr(expr)
            if _is_module_call(expr):
                assert isinstance(expr, frog_ast.FuncCall)
                callee = self._render_module_call_target(expr.func)
                args = self._render_call_args(expr, decls, out_stmts)
                if wrap and return_type is not None:
                    base = ec_ast.EcType(return_type.text[: -len(" option")])
                    tmp = _fresh_name_avoiding(decls, out_stmts, set())
                    decls.append(ec_ast.VarDecl(tmp, base))
                    out_stmts.append(ec_ast.Call(tmp, callee, args))
                    out_stmts.append(ec_ast.Assign(result, f"Some ({tmp})"))
                else:
                    out_stmts.append(ec_ast.Call(result, callee, args))
            else:
                rhs = self._translate_expr(expr, decls, out_stmts)
                if wrap:
                    rhs = f"Some ({rhs})"
                out_stmts.append(ec_ast.Assign(result, rhs))
        if returned_flag is not None:
            out_stmts.append(ec_ast.Assign(returned_flag, "true"))

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
            optional = return_type is not None and return_type.text.endswith(" option")
            if isinstance(stmt.expression, frog_ast.NoneExpression):
                stmts.append(ec_ast.Return("None"))
                return
            # Wrap ``Some`` only when coercing a base value up; an
            # already-optional return (e.g. calling another optional method)
            # passes through unwrapped.
            wrap = optional and not self._is_optional_expr(stmt.expression)
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
                fresh = _fresh_name_avoiding(decls, stmts, self._reserved_names)
                callee = self._render_module_call_target(call.func)
                if wrap and return_type is not None:
                    # The call yields the base ``T``; wrap it ``Some`` to match
                    # the ``T option`` return type.
                    ec_type = ec_ast.EcType(return_type.text[: -len(" option")])
                    decls.append(ec_ast.VarDecl(fresh, ec_type))
                    stmts.append(ec_ast.Call(fresh, callee, args))
                    stmts.append(ec_ast.Return(f"Some ({fresh})"))
                else:
                    decls.append(ec_ast.VarDecl(fresh, ec_type))
                    stmts.append(ec_ast.Call(fresh, callee, args))
                    stmts.append(ec_ast.Return(fresh))
                return
            # The returned expression may embed module calls (EC has no calls
            # inside expressions): e.g. the KDF collision-resistance challenger
            # returns ``H.evaluate(x0) == H.evaluate(x1) && x0 != x1``. Hoist
            # every embedded call into a preceding ``<@`` statement, then
            # return the now call-free expression.
            hoisted = self._hoist_calls_in_expr(stmt.expression, decls, stmts)
            rhs = self._exprs.translate(hoisted)
            if wrap:
                rhs = f"Some ({rhs})"
            stmts.append(ec_ast.Return(rhs))
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
        ec_var = self._exprs.ec_name(var.name)
        decls.append(ec_ast.VarDecl(ec_var, ec_type))
        self._type_map[var.name] = the_type
        distr = self._types.distr_for(ec_type)
        # A Function-field sample from the shared RO's own ``dfun`` is
        # materializing that RO (a lazy-RO assumption game's ``RF <-
        # Function<D,R>`` -- its Honest view IS ``H``): assign ``RF <- RO_H.h``
        # so ``RF = RO_H.h`` holds, rather than sample an independent copy the
        # ROM ``H``->fresh-RF rename would then have to re-couple. ``None`` (the
        # common case / non-ROM) keeps the plain sample.
        ro_ref = self._types.ro_ref_for_dfun(distr)
        if ro_ref is not None:
            stmts.append(ec_ast.Assign(ec_var, ro_ref))
        else:
            stmts.append(ec_ast.Sample(ec_var, distr))

    def _handle_var_decl(
        self,
        stmt: frog_ast.VariableDeclaration,
        decls: list[ec_ast.VarDecl],
    ) -> None:
        ec_type = self._types.translate_type(stmt.type)
        decls.append(ec_ast.VarDecl(self._exprs.ec_name(stmt.name), ec_type))
        self._type_map[stmt.name] = stmt.type

    def _handle_assign(
        self,
        stmt: frog_ast.Assignment,
        decls: list[ec_ast.VarDecl],
        stmts: list[ec_ast.EcStmt],
    ) -> None:
        # Finite-map write ``m[k] = v`` -> the EC functional update
        # ``m <- m.[k <- v]`` (a lazy random-oracle table store). The LHS is
        # an ``ArrayAccess`` on a map-typed array, so it is handled before the
        # simple-variable path below (which rejects a non-Variable LHS).
        if isinstance(stmt.var, frog_ast.ArrayAccess) and self._is_map(
            stmt.var.the_array
        ):
            arr = self._exprs.translate(stmt.var.the_array)
            key = self._exprs.translate(stmt.var.index)
            val = self._exprs.translate(stmt.value)
            stmts.append(ec_ast.Assign(arr, f"{arr}.[{key} <- {val}]"))
            return
        var = _require_variable(stmt.var)
        ec_var = self._exprs.ec_name(var.name)
        if stmt.the_type is not None:
            ec_type = self._types.translate_type(stmt.the_type)
            decls.append(ec_ast.VarDecl(ec_var, ec_type))
            self._type_map[var.name] = stmt.the_type
        if _is_module_call(stmt.value):
            call = stmt.value
            assert isinstance(call, frog_ast.FuncCall)
            callee = self._render_module_call_target(call.func)
            args = self._render_call_args(call, decls, stmts)
            stmts.append(ec_ast.Call(ec_var, callee, args))
            return
        rhs = self._translate_expr(stmt.value, decls, stmts)
        # Reconcile optional-ness across the assignment: canonicalization makes
        # optionals transparent, so a ``T? x = <base expr>`` flat-state decl
        # assigns a base value to an optional local (needs ``Some``), and the
        # reverse (a ``T?`` value into a base local) needs ``oget``. No-op when
        # both sides agree -- so non-optional bodies are byte-identical.
        lhs_opt = self._lhs_is_optional(var, stmt.the_type)
        rhs_opt = self._is_optional_expr(stmt.value)
        if lhs_opt and not rhs_opt:
            rhs = f"Some ({rhs})"
        elif rhs_opt and not lhs_opt:
            rhs = f"oget ({rhs})"
        stmts.append(ec_ast.Assign(ec_var, rhs))

    def _lhs_is_optional(
        self, var: frog_ast.Variable, the_type: frog_ast.Type | None
    ) -> bool:
        """True if the assignment target has an optional (``T?``) type."""
        if the_type is not None:
            return self._types.translate_type(the_type).text.endswith(" option")
        return self._is_optional_expr(var)

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
            frog_type = self._exprs.type_of(expr)
            ec_type = self._types.translate_type(frog_type)
            fresh = _fresh_name_avoiding(decls, stmts, self._reserved_names)
            decls.append(ec_ast.VarDecl(fresh, ec_type))
            self._type_map[fresh] = frog_type
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
            frog_type = self._exprs.type_of(expr)
            ec_type = self._types.translate_type(frog_type)
            fresh = _fresh_name_avoiding(decls, stmts, self._reserved_names)
            decls.append(ec_ast.VarDecl(fresh, ec_type))
            self._type_map[fresh] = frog_type
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


def _expr_has_module_call(expr: frog_ast.Expression) -> bool:
    """True if ``expr`` embeds a module call ``E.m(...)`` anywhere. Mirrors
    :meth:`StatementTranslator._hoist_calls_in_expr`'s traversal."""
    if _is_module_call(expr):
        return True
    if isinstance(expr, frog_ast.BinaryOperation):
        return _expr_has_module_call(expr.left_expression) or _expr_has_module_call(
            expr.right_expression
        )
    if isinstance(expr, frog_ast.UnaryOperation):
        return _expr_has_module_call(expr.expression)
    if isinstance(expr, frog_ast.Tuple):
        return any(_expr_has_module_call(v) for v in expr.values)
    if isinstance(expr, frog_ast.FuncCall):
        return any(_expr_has_module_call(a) for a in expr.args)
    if isinstance(expr, frog_ast.FieldAccess):
        return _expr_has_module_call(expr.the_object)
    if isinstance(expr, frog_ast.ArrayAccess):
        return _expr_has_module_call(expr.the_array) or _expr_has_module_call(
            expr.index
        )
    if isinstance(expr, frog_ast.Slice):
        return (
            _expr_has_module_call(expr.the_array)
            or _expr_has_module_call(expr.start)
            or _expr_has_module_call(expr.end)
        )
    return False


def _dedup_decls(decls: list[ec_ast.VarDecl]) -> list[ec_ast.VarDecl]:
    """Collapse repeated var-decls of the same name, keeping the first.

    EC var-decls are proc-scoped: a name declared in two branches of a
    single-exit-lowered body (e.g. a ``__cse_*`` common-subexpression temp the
    engine extracted in both arms of a case-split, or a source ``_rN`` the
    hoister replicated) would emit two ``var x`` lines -> EC "duplicated
    local/parameters name". Same-named decls here denote the same proc-scope
    variable, so one decl suffices; a genuine type mismatch on the same name
    still surfaces at the assignment sites (EC type-checks those). A body with
    no repeats is unchanged (byte-identical)."""
    seen: set[str] = set()
    out: list[ec_ast.VarDecl] = []
    for d in decls:
        if d.name in seen:
            continue
        seen.add(d.name)
        out.append(d)
    return out


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
        elif isinstance(s, frog_ast.NumericFor):
            names.add(s.name)
            names |= _collect_bound_names(list(s.block.statements))
        elif isinstance(s, frog_ast.GenericFor):
            names |= _collect_bound_names(list(s.block.statements))
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
