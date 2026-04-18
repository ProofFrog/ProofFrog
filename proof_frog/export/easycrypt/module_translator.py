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

    def translate_primitive(
        self, prim: frog_ast.Primitive, name: str | None = None
    ) -> ec_ast.ModuleType:
        """Translate a Primitive to an EC ``module type``.

        If ``name`` is provided it overrides the emitted module type name;
        used when the primitive is wrapped inside an abstract theory and
        exported under the neutral name ``Scheme``.
        """
        procs: list[ec_ast.ProcSig] = [self._translate_sig(sig) for sig in prim.methods]
        return ec_ast.ModuleType(name or prim.name, procs)

    def translate_scheme(
        self,
        scheme: frog_ast.Scheme,
        primitive_name: str,
        module_params: list[ec_ast.ModuleParam] | None = None,
        module_param_types: dict[str, str] | None = None,
    ) -> ec_ast.Module:
        """Translate a Scheme to an EC module implementing ``primitive_name``.

        ``module_params`` declares any scheme-typed parameters on the
        emitted functor (e.g. ``(E1 : E1_c.Scheme) (E2 : E2_c.Scheme)``
        for ``ChainedEncryption``). ``module_param_types`` lets the
        expression/statement translator resolve calls on those
        parameters (e.g. ``E1.enc(...)``) through the corresponding
        primitive's method-return-type registry.
        """
        procs = [
            self._translate_method(method, module_param_types or {})
            for method in scheme.methods
        ]
        return ec_ast.Module(
            name=scheme.name,
            procs=procs,
            params=list(module_params) if module_params else [],
            implements=primitive_name,
        )

    def translate_game(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        game: frog_ast.Game,
        module_name: str,
        param_type_name: str,
        implements: str | None = None,
        emitted_param_type: str | None = None,
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
        emitted_type = emitted_param_type or param_type_name
        procs = [
            self._translate_method(method, module_param_types)
            for method in game.methods
        ]
        return ec_ast.Module(
            name=module_name,
            procs=procs,
            params=[ec_ast.ModuleParam(name=param.name, module_type=emitted_type)],
            implements=implements,
        )

    def translate_reduction(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        reduction: frog_ast.Reduction,
        primitive_name: str,
        oracle_type_name: str,
        emitted_primitive_type: str | None = None,
        param_renames: dict[str, str] | None = None,
        param_module_types: dict[str, str] | None = None,
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
        renames = dict(param_renames) if param_renames else {}
        emitted_type = emitted_primitive_type or primitive_name

        per_param_types = dict(param_module_types or {})
        module_params: list[ec_ast.ModuleParam] = [
            ec_ast.ModuleParam(
                name=renames.get(p.name, p.name),
                module_type=per_param_types.get(p.name, emitted_type),
            )
            for p in reduction.parameters
        ]
        module_params.append(
            ec_ast.ModuleParam(name=challenger_ec_name, module_type=oracle_type_name)
        )

        module_param_types: dict[str, str] = {
            p.name: primitive_name for p in reduction.parameters
        }
        module_param_types["challenger"] = oracle_type_name

        module_var_aliases: dict[str, str] = {"challenger": challenger_ec_name}
        for src, dst in renames.items():
            module_var_aliases[src] = dst

        procs = [
            self._translate_method(method, module_param_types, module_var_aliases)
            for method in reduction.methods
        ]
        return ec_ast.Module(
            name=reduction.name,
            procs=procs,
            params=module_params,
        )

    def translate_adversary_type(
        self, game_file: frog_ast.GameFile, oracle_type_name: str
    ) -> ec_ast.ModuleType:
        """Emit ``module type <Gf>_Adv (O : <oracle>) = { proc distinguish() : bool }``.

        The adversary's interface is a single ``distinguish`` procedure
        returning a bool. This matches the standard EC pattern for
        games whose adversaries make adaptive oracle queries.
        """
        return ec_ast.ModuleType(
            name=f"{game_file.name}_Adv",
            procs=[
                ec_ast.ProcSig(
                    name="distinguish",
                    params=[],
                    return_type=ec_ast.EcType("bool"),
                )
            ],
            params=[ec_ast.ModuleParam(name="O", module_type=oracle_type_name)],
        )

    def translate_reduction_adversary(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        reduction: frog_ast.Reduction,
        outer_adversary_type_name: str,
        inner_oracle_type_name: str,
        scheme_module_expr: str,
        reduction_arg_exprs: list[str] | None = None,
        extra_module_params: list[ec_ast.ModuleParam] | None = None,
    ) -> ec_ast.Module:
        """Lift a Reduction into an adversary against the inner game.

        The resulting module has signature
        ``module <R>_Adv [(<extra>)] (A : <Outer>_Adv) (C : <Inner>_Oracle)``
        and its ``distinguish`` procedure runs ``A`` against the reduction
        ``<R>(<reduction_arg_exprs...>, C)``.

        ``reduction_arg_exprs`` supplies the module expressions passed
        to the reduction's own parameters (one per reduction parameter,
        in declaration order). If omitted, defaults to a single-element
        list ``[scheme_module_expr]`` (legacy single-scheme case).

        ``extra_module_params`` adds extra module parameters before ``A``
        and ``C``. This is needed when the adversary wrapper lives inside
        a section with ``declare module`` and the reduction body references
        those declared modules (EC requires them as explicit parameters).
        """
        if reduction_arg_exprs is None:
            reduction_arg_exprs = [scheme_module_expr]
        call_args = ", ".join(list(reduction_arg_exprs) + ["C"])
        body: list[ec_ast.EcStmt] = [
            ec_ast.VarDecl(name="b", type=ec_ast.EcType("bool")),
            ec_ast.Call(
                var="b",
                callee=f"A({reduction.name}({call_args})).distinguish",
                args="",
            ),
            ec_ast.Return(expr="b"),
        ]
        params = list(extra_module_params) if extra_module_params else []
        params.extend(
            [
                ec_ast.ModuleParam(name="A", module_type=outer_adversary_type_name),
                ec_ast.ModuleParam(name="C", module_type=inner_oracle_type_name),
            ]
        )
        return ec_ast.Module(
            name=f"{reduction.name}_Adv",
            procs=[
                ec_ast.Proc(
                    name="distinguish",
                    params=[],
                    return_type=ec_ast.EcType("bool"),
                    body=body,
                )
            ],
            params=params,
        )

    def translate_game_wrapper(
        self,
        wrapper_name: str,
        adversary_type_name: str,
        oracle_module_expr: str,
        extra_module_params: list[ec_ast.ModuleParam] | None = None,
    ) -> ec_ast.Module:
        """Emit a ``main()``-wrapper module for one step in the proof.

        The wrapper takes an adversary parameter ``A`` and a single ``main``
        procedure that runs ``A`` against the given oracle module expression.

        Args:
            wrapper_name: e.g. ``"Game_step_0"``.
            adversary_type_name: e.g. ``"OneTimeSecrecyLR_Adv"``.
            oracle_module_expr: rendered EC expression for the oracle the
                adversary should be given, e.g.
                ``"OneTimeSecrecyLR_Left(OTP)"`` or
                ``"R1(OTP, OneTimeSecrecy_Real(OTP))"``.
            extra_module_params: additional module parameters before ``A``
                (e.g. declared module instances inside a section).
        """
        body: list[ec_ast.EcStmt] = [
            ec_ast.VarDecl(name="b", type=ec_ast.EcType("bool")),
            ec_ast.Call(
                var="b",
                callee=f"A({oracle_module_expr}).distinguish",
                args="",
            ),
            ec_ast.Return(expr="b"),
        ]
        params = list(extra_module_params) if extra_module_params else []
        params.append(ec_ast.ModuleParam(name="A", module_type=adversary_type_name))
        return ec_ast.Module(
            name=wrapper_name,
            procs=[
                ec_ast.Proc(
                    name="main",
                    params=[],
                    return_type=ec_ast.EcType("bool"),
                    body=body,
                )
            ],
            params=params,
        )

    def translate_theory_game_wrapper(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        wrapper_name: str,
        scheme_param_name: str,
        scheme_type_name: str,
        adversary_type_name: str,
        side_module_name: str,
    ) -> ec_ast.Module:
        """Assumption-game ``main()`` wrapper parameterized on ``(E, A)``.

        Emits::

            module <wrapper_name> (<E> : <Scheme>, A : <Adv>) = {
              proc main() : bool = {
                var b : bool;
                b <@ A(<side>(<E>)).distinguish();
                return b;
              }
            }

        Lives inside the primitive's abstract theory so the advantage
        axiom can forall-quantify over both the adversary and the
        scheme instance.
        """
        body: list[ec_ast.EcStmt] = [
            ec_ast.VarDecl(name="b", type=ec_ast.EcType("bool")),
            ec_ast.Call(
                var="b",
                callee=f"A({side_module_name}({scheme_param_name})).distinguish",
                args="",
            ),
            ec_ast.Return(expr="b"),
        ]
        return ec_ast.Module(
            name=wrapper_name,
            procs=[
                ec_ast.Proc(
                    name="main",
                    params=[],
                    return_type=ec_ast.EcType("bool"),
                    body=body,
                )
            ],
            params=[
                ec_ast.ModuleParam(
                    name=scheme_param_name, module_type=scheme_type_name
                ),
                ec_ast.ModuleParam(name="A", module_type=adversary_type_name),
            ],
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
        try:
            translated = stmts.translate_block(method.block)
            body: list[ec_ast.EcStmt] = []
            body.extend(translated.var_decls)
            body.extend(translated.stmts)
        except NotImplementedError:
            # Fall back to a stub body that returns ``witness``. The
            # proc body still satisfies the module type; proving any
            # lemma that depends on it will fail, and that's fine:
            # the current phase only aims for declaration-level
            # EC acceptance.
            body = [ec_ast.Return(expr="witness")]
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
