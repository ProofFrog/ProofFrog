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
            [dict[str, frog_ast.Type], dict[str, str]],
            Callable[[frog_ast.Expression], frog_ast.Type],
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
        procs = [self._translate_method(method, {}) for method in scheme.methods]
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
        implements: str | None = None,
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
        module_param_types = {param.name: param_type_name}
        procs = [
            self._translate_method(method, module_param_types)
            for method in game.methods
        ]
        return ec_ast.Module(
            name=module_name,
            procs=procs,
            params=[ec_ast.ModuleParam(name=param.name, module_type=param_type_name)],
            implements=implements,
        )

    def translate_reduction(
        self,
        reduction: frog_ast.Reduction,
        primitive_name: str,
        oracle_type_name: str,
    ) -> ec_ast.Module:
        """Translate a Reduction to a multi-parameter EC module.

        EC signature::

            module R (E : <primitive_name>, Challenger : <oracle_type_name>)
              = { ... }

        The reduction's parameter names are preserved, with all
        parameters assumed to be primitive-typed. A final challenger
        parameter (renamed to ``Challenger`` to satisfy EC's uppercase
        module-parameter convention) is appended; reduction-body
        references to ``challenger.METHOD(args)`` are rewritten to
        ``Challenger.method(args)``.
        """
        if not reduction.parameters:
            raise ValueError(
                f"Reduction {reduction.name!r} has no parameters; "
                "need at least the primitive instance parameter."
            )
        if reduction.fields:
            raise NotImplementedError(
                f"Stateful reductions (with field declarations) are not "
                f"supported yet: {reduction.name!r} has fields {reduction.fields}"
            )

        # EC requires module parameter names to start with an uppercase
        # letter. The reduction body refers to the challenger by the
        # FrogLang name ``challenger``; we rename it to ``Challenger`` in
        # the generated EC module and alias references through below.
        challenger_ec_name = "Challenger"

        module_params: list[ec_ast.ModuleParam] = [
            ec_ast.ModuleParam(name=p.name, module_type=primitive_name)
            for p in reduction.parameters
        ]
        module_params.append(
            ec_ast.ModuleParam(name=challenger_ec_name, module_type=oracle_type_name)
        )

        module_param_types: dict[str, str] = {
            p.name: primitive_name for p in reduction.parameters
        }
        module_param_types["challenger"] = oracle_type_name

        module_var_aliases = {"challenger": challenger_ec_name}

        procs = [
            self._translate_method(method, module_param_types, module_var_aliases)
            for method in reduction.methods
        ]
        return ec_ast.Module(
            name=reduction.name,
            procs=procs,
            params=module_params,
        )

    def translate_game_file_oracle(
        self, game_file: frog_ast.GameFile, oracle_type_name: str
    ) -> ec_ast.ModuleType:
        """Emit the oracle module type for a GameFile.

        Uses the oracle methods of the first game side; both sides must
        expose the same method names.
        """
        left_names = {m.signature.name for m in game_file.games[0].methods}
        right_names = {m.signature.name for m in game_file.games[1].methods}
        if left_names != right_names:
            raise ValueError(
                f"Game sides {game_file.games[0].name} and "
                f"{game_file.games[1].name} of {game_file.name} expose "
                f"different oracle methods: {left_names} vs {right_names}"
            )
        sigs = [self._translate_sig(m.signature) for m in game_file.games[0].methods]
        return ec_ast.ModuleType(oracle_type_name, sigs)

    def _translate_sig(self, sig: frog_ast.MethodSignature) -> ec_ast.ProcSig:
        params = [
            ec_ast.ProcParam(p.name, self._translate_param_type(p.type))
            for p in sig.parameters
        ]
        ret = self._translate_param_type(sig.return_type)
        return ec_ast.ProcSig(sig.name.lower(), params, ret)

    def _translate_method(
        self,
        method: frog_ast.Method,
        module_param_types: dict[str, str],
        module_var_aliases: dict[str, str] | None = None,
    ) -> ec_ast.Proc:
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

        type_of = self._type_of_factory(type_map, module_param_types)
        exprs = expr_translator.ExpressionTranslator(self._types, type_of)
        stmts = stmt_translator.StatementTranslator(
            self._types, exprs, module_var_aliases=module_var_aliases
        )
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
