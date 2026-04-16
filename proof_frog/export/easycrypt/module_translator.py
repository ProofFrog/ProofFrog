"""Translate FrogLang Primitive/Scheme/Game declarations to EC modules."""

from __future__ import annotations

from typing import Callable

from . import ec_ast
from . import expr_translator
from . import stmt_translator
from . import type_collector as tc
from ... import frog_ast


class ModuleTranslator:
    """Translate Primitive/Scheme/Game declarations into EC modules."""

    def __init__(
        self,
        types: tc.TypeCollector,
        type_of_factory: Callable[
            [dict[str, frog_ast.Type]], Callable[[frog_ast.Expression], frog_ast.Type]
        ],
    ) -> None:
        self._types = types
        self._type_of_factory = type_of_factory

    def translate_primitive(self, prim: frog_ast.Primitive) -> ec_ast.ModuleType:
        """Translate a Primitive to an EC ``module type``."""
        procs: list[ec_ast.ProcSig] = [self._translate_sig(sig) for sig in prim.methods]
        return ec_ast.ModuleType(prim.name, procs)

    def translate_scheme(
        self, scheme: frog_ast.Scheme, primitive_name: str
    ) -> ec_ast.Module:
        """Translate a Scheme to an EC module implementing ``primitive_name``."""
        procs = [self._translate_method(method) for method in scheme.methods]
        return ec_ast.Module(
            name=scheme.name,
            procs=procs,
            implements=primitive_name,
        )

    def translate_game(
        self,
        game: frog_ast.Game,
        module_name: str,
        param_type_name: str,
    ) -> ec_ast.Module:
        """Translate a Game.

        The game must take exactly one parameter, which is the primitive
        instance (e.g. ``Game Real(SymEnc E)``).
        """
        assert len(game.parameters) == 1, (
            "Phase 1 skeleton only handles games with a single "
            f"primitive parameter; got {game.parameters}"
        )
        param = game.parameters[0]
        procs = [self._translate_method(method) for method in game.methods]
        return ec_ast.Module(
            name=module_name,
            procs=procs,
            params=[ec_ast.ModuleParam(name=param.name, module_type=param_type_name)],
        )

    def _translate_sig(self, sig: frog_ast.MethodSignature) -> ec_ast.ProcSig:
        params = [
            ec_ast.ProcParam(p.name, self._translate_param_type(p.type))
            for p in sig.parameters
        ]
        ret = self._translate_param_type(sig.return_type)
        return ec_ast.ProcSig(sig.name.lower(), params, ret)

    def _translate_method(self, method: frog_ast.Method) -> ec_ast.Proc:
        sig = method.signature
        ec_params = [
            ec_ast.ProcParam(p.name, self._translate_param_type(p.type))
            for p in sig.parameters
        ]
        return_type = self._translate_param_type(sig.return_type)

        type_map: dict[str, frog_ast.Type] = {}
        for p in sig.parameters:
            type_map[p.name] = p.type
        for stmt in method.block.statements:
            _seed_type_map(stmt, type_map)

        type_of = self._type_of_factory(type_map)
        exprs = expr_translator.ExpressionTranslator(self._types, type_of)
        stmts = stmt_translator.StatementTranslator(self._types, exprs)
        translated = stmts.translate_block(method.block)

        body: list[ec_ast.EcStmt] = []
        body.extend(translated.var_decls)
        body.extend(translated.stmts)
        return ec_ast.Proc(
            name=sig.name.lower(),
            params=ec_params,
            return_type=return_type,
            body=body,
        )

    def _translate_param_type(self, t: frog_ast.Type) -> ec_ast.EcType:
        return self._types.translate_type(t)


def _seed_type_map(
    stmt: frog_ast.Statement, type_map: dict[str, frog_ast.Type]
) -> None:
    """Record declared-variable types into the map for the expr translator."""
    if isinstance(stmt, (frog_ast.Sample, frog_ast.Assignment)):
        if stmt.the_type is not None and isinstance(stmt.var, frog_ast.Variable):
            type_map[stmt.var.name] = stmt.the_type
    elif isinstance(stmt, frog_ast.VariableDeclaration):
        type_map[stmt.name] = stmt.type
