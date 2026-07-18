"""Translate FrogLang Primitive/Scheme/Game declarations to EC modules."""

from __future__ import annotations

import copy
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable

from . import canonical_form
from . import ec_ast
from . import expr_translator
from . import oracle_model
from . import stmt_translator
from . import type_collector as tc
from ... import frog_ast
from ... import visitors

#: Binder name for the lifted-``Initialize`` result threaded from the game
#: wrapper's ``main()`` into the adversary's ``distinguish``. Matches the
#: validated multi-oracle template (``tests/integration/ec_templates/
#: multi_oracle_indist.ec``).
INIT_RESULT_NAME = "pk"


def _reduction_init_method(
    reduction: frog_ast.Reduction,
) -> frog_ast.Method | None:
    """Return the reduction's ``Initialize`` method, or ``None`` if absent."""
    for method in reduction.methods:
        if method.signature.name.lower() == "initialize":
            return method
    return None


def _is_pure_forward_init(method: frog_ast.Method) -> bool:
    """True when ``method``'s body is exactly ``return challenger.Initialize();``.

    Such a reduction merely forwards the inner challenger's ``Initialize``
    result unchanged and holds no own state. In the Initialize-lifted design
    (multi-oracle inner game), the game wrapper's ``main()`` has *already* run
    the inner ``Initialize`` and threaded its result into ``distinguish`` as the
    ``pk`` parameter, so the outer init result equals that received ``pk``.
    Re-running the reduction's ``Initialize`` here would call ``challenger.
    Initialize`` (``C.initialize``) a second time, which the restricted
    post-init-only adversary interface forbids (multi-oracle foundation §7,
    blocker B). See ``translate_reduction_adversary``.
    """
    stmts = list(method.block.statements)
    if len(stmts) != 1 or not isinstance(stmts[0], frog_ast.ReturnStatement):
        return False
    expr = stmts[0].expression
    return (
        isinstance(expr, frog_ast.FuncCall)
        and isinstance(expr.func, frog_ast.FieldAccess)
        and isinstance(expr.func.the_object, frog_ast.Variable)
        and expr.func.the_object.name == "challenger"
        and expr.func.name.lower() == "initialize"
    )


def _is_challenger_init_call(expr: frog_ast.Expression) -> bool:
    """True iff ``expr`` is a call ``challenger.Initialize(...)``."""
    return (
        isinstance(expr, frog_ast.FuncCall)
        and isinstance(expr.func, frog_ast.FieldAccess)
        and isinstance(expr.func.the_object, frog_ast.Variable)
        and expr.func.the_object.name == "challenger"
        and expr.func.name.lower() == "initialize"
    )


def _is_module_call_expr(expr: frog_ast.ASTNode) -> bool:
    """Recognize ``E.method(...)`` -- a FuncCall whose func is a FieldAccess."""
    return isinstance(expr, frog_ast.FuncCall) and isinstance(
        expr.func, frog_ast.FieldAccess
    )


def _statement_module_call(
    stmt: frog_ast.Statement,
) -> frog_ast.Expression | None:
    """Return the module-call sub-expression a statement performs, else ``None``.

    Covers the three statement shapes that carry a top-level ``E.method(...)``
    call: an assignment (``x <@ E.m()``), a bare-call statement, and a
    ``return E.m()``. Nested calls in argument position are not counted (they
    are hoisted before this runs).
    """
    if isinstance(stmt, frog_ast.Assignment) and _is_module_call_expr(stmt.value):
        return stmt.value
    if isinstance(stmt, frog_ast.ReturnStatement) and _is_module_call_expr(
        stmt.expression
    ):
        return stmt.expression
    if isinstance(stmt, frog_ast.FuncCall) and _is_module_call_expr(stmt):
        return stmt
    return None


def _count_module_calls(node: frog_ast.ASTNode) -> int:
    """Count every ``E.method(...)`` call anywhere under ``node`` (recursive).

    Includes calls nested in argument / tuple position (e.g. ``return [pk,
    F.evaluate(ss, ct), ct]``), which :func:`_statement_module_call` does not
    see -- the consume-pk gate needs the *total* so it declines a repacking init
    whose repack itself computes with an abstract call (KEMPRF's ``R_KEM``,
    whose repack applies ``F.evaluate``).
    """
    count = 0

    def _tally(n: frog_ast.ASTNode) -> bool:
        nonlocal count
        if _is_module_call_expr(n):
            count += 1
        return False

    visitors.SearchVisitor(_tally).visit(node)
    return count


def init_module_call_count(game: frog_ast.Game) -> int:
    """Number of top-level module calls in ``game``'s ``Initialize`` method.

    Used by the consume-pk assumption-hop bridge tactic to size the init
    backbone peel: after ``inline *`` both byequiv sides run exactly this many
    abstract challenger-``Initialize`` calls (the reduction forwards to the
    challenger's ``Initialize``, whose body holds these calls). Zero if the game
    has no ``Initialize``.
    """
    init = next(
        (m for m in game.methods if m.signature.name.lower() == "initialize"), None
    )
    if init is None:
        return 0
    return sum(
        1 for stmt in init.block.statements if _statement_module_call(stmt) is not None
    )


def reduction_repacks_challenger_init(reduction: frog_ast.Reduction) -> bool:
    """True iff the reduction's ``Initialize`` is a *forward+repack* of the
    challenger's ``Initialize`` while storing challenger-derived state in its
    own fields.

    Such a reduction, lifted to an assumption-adversary, must **consume** the
    leaked ``pk`` -- the assumption game already ran the challenger's
    ``Initialize`` and passed its full result to ``distinguish`` -- rather than
    re-run ``Initialize`` through the reduction (which would call
    ``challenger.Initialize`` a second time, violating the restricted
    post-init-only adversary interface **and** double-initializing the
    challenger). See :meth:`ModuleTranslator._render_consumed_pk_init` and the
    matching backbone-peel bridge tactic in ``proof_translator``.

    Gated to the shape ``_render_consumed_pk_init`` handles: the reduction holds
    field state, its ``Initialize`` is not a pure forward, exactly one top-level
    module call is ``challenger.Initialize()``, and **every** module call is
    top-level (no call nested in argument/tuple position). Every other top-level
    statement is either deterministic plumbing, a ``<$`` sample, or an abstract
    call the reduction makes on its OWN behalf (a *consume-pk-with-computation*
    shape -- e.g. the CFRG ``R_PQ_Bind``, which forwards the KEM_PQ challenger's
    ``Initialize`` **and** does its own ``KEM_T.keygen`` for the T components):
    those the consumed-init rendering keeps verbatim, and the backbone-peel
    bridge sizes to the reduction's full init backbone (challenger calls + the
    reduction's own calls/samples), not just the challenger's.

    A reduction whose ``Initialize`` makes a call NESTED in an expression (e.g.
    KEMPRF's ``R_KEM``, which applies ``F.evaluate`` while repacking, or the CFRG
    ``R_PQ_Bind`` over a *NominalGroup*, whose ``ek_T <- NG.Exp(NG.Generator(),
    dk_T)`` nests ``NG.Generator()``) is left to the re-init path -- the consumed
    rendering seeds types on the un-hoisted body and cannot type a nested
    ``FuncCall`` -- so its export stays byte-identical (nested-call hoisting is a
    separate, deferred extension). A reduction that holds no field state or does
    not delegate ``challenger.Initialize`` is likewise left to the re-init path.
    """
    init = _reduction_init_method(reduction)
    if init is None or not reduction.fields:
        return False
    if _is_pure_forward_init(init):
        return False
    top_calls = [
        call
        for stmt in init.block.statements
        if (call := _statement_module_call(stmt)) is not None
    ]
    # Nested calls (``ek_T <- NG.Exp(NG.Generator(), dk_T)``) and the reduction's
    # own ``<$`` samples are BOTH handled: ``_render_consumed_pk_init`` hoists the
    # nested calls (:func:`canonical_form.hoist_reduction_calls`) before rendering,
    # and the backbone peel is event-aware (``rnd`` per sample). So no
    # nested-call / sample rejection here -- the NominalGroup ``R_PQ_Bind`` (nested
    # ``NG.Generator()`` + seed samples) and the KEMPRF ``R_KEM`` (nested
    # ``F.evaluate``) now take the consume-pk path too.
    challenger_calls = [c for c in top_calls if _is_challenger_init_call(c)]
    if len(challenger_calls) != 1:
        return False
    # The single ``challenger.Initialize()`` must be captured by an ASSIGNMENT
    # (``[...] = challenger.Initialize()``): that is the forward+repack shape
    # ``_render_consumed_pk_init`` rewrites to ``[...] <- pk``. A reduction that
    # calls ``challenger.Initialize()`` as a BARE statement (for side effects,
    # storing nothing -- the multi-oracle INDCCA reductions of GHP18 /
    # StarHunters) is not a repack the consumed rendering can rewrite, so it stays
    # on the re-init path (which re-runs ``Initialize`` and works regardless of
    # the reduction's internal shape).
    return any(
        isinstance(stmt, frog_ast.Assignment) and _is_challenger_init_call(stmt.value)
        for stmt in init.block.statements
    )


def consumed_pk_peel_events(
    reduction: frog_ast.Reduction,
    challenger_init_call_count: int,
    challenger_oracle_type: str,
    method_return_types: dict[tuple[str, str], frog_ast.Type],
) -> list[str]:
    """The consume-pk backbone-peel events, in PEEL (tail-to-front) order.

    Each entry is ``"call"`` (couple with ``wp; call (_: true)``) or ``"sample"``
    (couple with ``wp; rnd``). The full init backbone in *program* order is the
    challenger's own init calls (``challenger_init_call_count`` keygens/samples --
    here counted as calls, the KEM case) followed by the reduction's OWN
    backbone read off its *hoisted* ``Initialize`` (nested calls flattened, so a
    ``NG.Exp(NG.Generator(), dk)`` contributes two calls in ``Generator``-then-
    ``Exp`` order, and seed ``<$`` draws contribute samples). The peel couples the
    backbone tail-to-front, so the list is reversed. Byte-compatible with the
    old call-only count when the reduction has no own samples and no nested calls
    (Generic: empty own backbone; CK/UK ``R_PQ_Bind``: two own ``KEM_T.keygen``
    calls)."""
    hoisted = canonical_form.hoist_reduction_calls(
        reduction, challenger_oracle_type, method_return_types
    )
    init = _reduction_init_method(hoisted)
    own: list[str] = []
    if init is not None:
        for stmt in init.block.statements:
            if isinstance(stmt, frog_ast.ReturnStatement):
                continue
            if isinstance(stmt, frog_ast.Assignment) and _is_challenger_init_call(
                stmt.value
            ):
                continue  # the leaked pk -- its keygens are the challenger's own
            if isinstance(stmt, frog_ast.Sample):
                own.append("sample")
            elif _statement_module_call(stmt) is not None:
                own.append("call")
    backbone = ["call"] * challenger_init_call_count + own
    return list(reversed(backbone))


@dataclass
class MultiOracleSpec:
    """Emission spec for a multi-oracle (Initialize-lifted) game file.

    Built by :meth:`ModuleTranslator.multi_oracle_spec` from a game file's
    :class:`~proof_frog.export.easycrypt.oracle_model.GameOracleModel`. Carries
    everything the wrapper/adversary-type emitters need to produce the
    Initialize-lifted shape:

    - ``init_name`` -- EC oracle name of the lifted ``Initialize`` (lowercased).
    - ``init_return_type`` -- EC type of ``Initialize``'s result, used both as
      the ``main()`` local's type and the ``distinguish`` init parameter type.
    - ``post_init_names`` -- EC names of the adaptive (adversary-facing)
      oracles, used for the ``{O.<m>, ...}`` restriction clause.

    A single-oracle game produces no spec (the emitters take the legacy path),
    so single-oracle output stays byte-identical.
    """

    init_name: str
    init_return_type: ec_ast.EcType
    post_init_names: list[str]

    def oracle_restriction(self, oracle_param: str) -> list[str]:
        """Restriction clause entries ``["<O>.<m>", ...]`` for ``distinguish``."""
        return [f"{oracle_param}.{m}" for m in self.post_init_names]


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

    def deterministic_op_decls(self, prim: frog_ast.Primitive) -> list[ec_ast.OpDecl]:
        """Emit ``op ev_<m> : T0 -> ... -> R.`` per ``deterministic`` method.

        Models a deterministic primitive method as a pure, glob-independent
        function of its arguments (faithful to FrogLang, where
        ``deterministic`` methods are pure functions with no state). Emitted
        *inside* the primitive's abstract theory so each clone gets a distinct
        op (``G_c.ev_evaluate`` vs ``H_c.ev_evaluate``); the matching
        ``declare axiom`` is emitted at section scope by the exporter via
        :meth:`deterministic_axiom`. Built with a theory-mode translator so the
        arg/return types are the theory-local names (``bs_lambda_t`` etc.).
        """
        decls: list[ec_ast.OpDecl] = []
        for sig in prim.methods:
            if not sig.deterministic:
                continue
            arrow = " -> ".join(
                [self._translate_param_type(p.type).text for p in sig.parameters]
                + [self._translate_param_type(sig.return_type).text]
            )
            decls.append(ec_ast.OpDecl(f"ev_{sig.name.lower()}", arrow))
        return decls

    @staticmethod
    def deterministic_axiom(
        module_name: str,
        clone_prefix: str,
        proc_sig: ec_ast.ProcSig,
        type_bindings: dict[str, str],
    ) -> ec_ast.Axiom:
        """Emit ``declare axiom <module>_<m>_det`` (phoare-1 determinism spec).

        Asserts that ``<module>.<m>`` is deterministic, glob-preserving and
        total: it returns ``<clone_prefix>.ev_<m>`` applied to its arguments
        and leaves ``glob <module>`` unchanged with probability 1.
        ``type_bindings`` maps each theory-local EC type name to the concrete
        type the clone binds it to (``bs_lambda_t`` -> ``bs_lambda``); an
        unbound type falls back to ``<clone>.<name>`` (still abstract). This
        makes the binder types match the declared module's proc signature.
        """
        proc = proc_sig.name
        op = f"{clone_prefix}.ev_{proc}"
        binders = [f"(g : (glob {module_name}))"]
        pre_eqs = [f"(glob {module_name}) = g"]
        arg_names: list[str] = []
        for i, pp in enumerate(proc_sig.params):
            arg = f"a{i}"
            arg_names.append(arg)
            arg_type = type_bindings.get(pp.type.text, f"{clone_prefix}.{pp.type.text}")
            binders.append(f"({arg} : {arg_type})")
            pre_eqs.append(f"{pp.name} = {arg}")
        applied = "".join(f" {arg}" for arg in arg_names)
        formula = (
            f"{' '.join(binders)} : "
            f"phoare[ {module_name}.{proc} : "
            f"{' /\\ '.join(pre_eqs)} "
            f"==> (glob {module_name}) = g /\\ res = {op}{applied} ] = 1%r"
        )
        return ec_ast.Axiom(f"{module_name}_{proc}_det", formula, declare=True)

    @staticmethod
    def injective_axiom(
        module_name: str,
        clone_prefix: str,
        proc_sig: ec_ast.ProcSig,
        type_bindings: dict[str, str],
    ) -> ec_ast.Axiom | None:
        """Emit ``declare axiom <module>_<m>_inj`` (joint injectivity of ``ev_<m>``).

        Reflects the primitive's declared ``injective`` modifier: the pure
        function ``<clone_prefix>.ev_<m>`` modelling the method (emitted for
        every ``deterministic`` method) is injective in ALL its arguments
        jointly -- equal outputs force equal argument tuples. This is faithful
        to FrogLang's ``injective`` semantics, which the engine realises as the
        joint rewrite ``f(a0..an) == f(b0..bn) -> a0==b0 /\\ ... /\\ an==bn``
        (``InjectiveEqualitySimplifyTransformer``), the exact analogue of the
        ``deterministic`` -> ``_det`` faithfulness.

        Only meaningful for a method that is ALSO ``deterministic`` (so
        ``ev_<m>`` exists to state injectivity over) and has at least one
        argument; returns ``None`` otherwise. ``type_bindings`` resolves the
        theory-local binder types exactly as :meth:`deterministic_axiom` does.
        """
        if not proc_sig.params:
            return None
        proc = proc_sig.name
        op = f"{clone_prefix}.ev_{proc}"
        binders: list[str] = []
        eqs: list[str] = []
        a_names: list[str] = []
        b_names: list[str] = []
        for i, pp in enumerate(proc_sig.params):
            arg_type = type_bindings.get(pp.type.text, f"{clone_prefix}.{pp.type.text}")
            a_arg, b_arg = f"a{i}", f"b{i}"
            a_names.append(a_arg)
            b_names.append(b_arg)
            binders.append(f"({a_arg} : {arg_type})")
            binders.append(f"({b_arg} : {arg_type})")
            eqs.append(f"{a_arg} = {b_arg}")
        a_app = "".join(f" {a}" for a in a_names)
        b_app = "".join(f" {b}" for b in b_names)
        formula = (
            f"{' '.join(binders)} : "
            f"{op}{a_app} = {op}{b_app} => {' /\\ '.join(eqs)}"
        )
        return ec_ast.Axiom(f"{module_name}_{proc}_inj", formula, declare=True)

    # ----- Statelessness foundation (probabilistic-method analogue of the
    # deterministic ``ev_<m>``/``_det`` foundation). Lets EC reorder two
    # calls to a *stateless* randomized scheme method: each is modelled as
    # sampling a fixed per-method distribution (``d<m>``), realised by an
    # ``Ideal`` module, and the section asserts ``E.<m> ~ Ideal.<m>`` via a
    # ``declare axiom <module>_<m>_sem``. See the chain emitter's
    # stateless-reorder transitivity. -------------------------------------

    def distribution_op_decls(self, prim: frog_ast.Primitive) -> list[ec_ast.OpDecl]:
        """Emit ``op d<m> : T0 -> ... -> R distr.`` per probabilistic method.

        Models a stateless randomized primitive method as sampling a fixed
        distribution parameterized by its value-arguments. Emitted inside
        the primitive's abstract theory (so each clone gets ``<clone>.d<m>``),
        next to the deterministic ``ev_<m>`` ops.
        """
        decls: list[ec_ast.OpDecl] = []
        for sig in prim.methods:
            if sig.deterministic:
                continue
            param_types = [
                self._translate_param_type(p.type).text for p in sig.parameters
            ]
            ret = self._translate_param_type(sig.return_type).text
            arrow = " -> ".join(param_types + [f"{ret} distr"])
            decls.append(ec_ast.OpDecl(f"d{sig.name.lower()}", arrow))
        return decls

    def lossless_axiom_lines(self, prim: frog_ast.Primitive) -> list[str]:
        """Emit ``axiom d<m>_ll : is_lossless ...`` per probabilistic method.

        Only consumed by reorder micros that *drop* an independent sample;
        harmless (unused) for pure-permutation reorders. Emitted inside the
        theory so the lossless fact is available per clone.
        """
        lines: list[str] = []
        for sig in prim.methods:
            if sig.deterministic:
                continue
            name = f"d{sig.name.lower()}"
            n = len(sig.parameters)
            if n == 0:
                lines.append(f"axiom {name}_ll : is_lossless {name}.")
            else:
                binders = " ".join(f"a{i}" for i in range(n))
                applied = " ".join(f"a{i}" for i in range(n))
                lines.append(
                    f"axiom {name}_ll : forall {binders}, "
                    f"is_lossless ({name} {applied})."
                )
        return lines

    def ideal_module_text(
        self, prim: frog_ast.Primitive, scheme_type_name: str = "Scheme"
    ) -> str:
        """Raw EC text for the ``Ideal`` module realizing the primitive.

        Each probabilistic method samples its ``d<m>`` distribution; each
        deterministic method returns ``ev_<m>`` applied to its arguments
        (matching the determinism foundation). Emitted inside the theory so
        ``<clone>.Ideal`` exists for every instance.
        """
        procs: list[str] = []
        for sig in prim.methods:
            name = sig.name.lower()
            params = ", ".join(
                f"{p.name} : {self._translate_param_type(p.type).text}"
                for p in sig.parameters
            )
            ret = self._translate_param_type(sig.return_type).text
            applied = "".join(f" {p.name}" for p in sig.parameters)
            if sig.deterministic:
                body = f"return ev_{name}{applied};"
            else:
                body = f"var r : {ret}; r <$ d{name}{applied}; return r;"
            procs.append(f"  proc {name}({params}) : {ret} = {{ {body} }}")
        inner = "\n".join(procs)
        return f"module Ideal : {scheme_type_name} = {{\n{inner}\n}}."

    @staticmethod
    def stateless_axiom(
        module_name: str, clone_prefix: str, proc_sig: ec_ast.ProcSig
    ) -> ec_ast.Axiom:
        """Emit ``declare axiom <module>_<m>_sem`` (equiv-to-Ideal spec).

        Asserts that ``<module>.<m>`` is observationally ``<clone>.Ideal.<m>``
        (samples the fixed ``d<m>`` distribution) and preserves
        ``glob <module>`` — i.e. the method is stateless. This restricts the
        EC theorem to stateless ``E``, which is exactly what ProofFrog proves
        when its canonicalization reorders the method's calls.
        """
        m = proc_sig.name
        pre = (
            f"={{glob {module_name}, arg}}"
            if proc_sig.params
            else f"={{glob {module_name}}}"
        )
        formula = (
            f": equiv[ {module_name}.{m} ~ {clone_prefix}.Ideal.{m} : "
            f"{pre} ==> ={{res, glob {module_name}}} ]"
        )
        return ec_ast.Axiom(f"{module_name}_{m}_sem", formula, declare=True)

    @staticmethod
    def pres_axiom(module_name: str, method: str) -> ec_ast.Axiom:
        """Emit ``declare axiom <module>_<m>_pres`` (glob-preserving + total).

        Asserts that ``<module>.<m>`` leaves ``glob <module>`` unchanged with
        probability 1 (it is stateless and total) -- the weaker, result-agnostic
        sibling of :meth:`deterministic_axiom`. This is what lets EC drop a
        *dead* abstract scheme call one-sided (``call{i} (<m>_pres g)``): the
        call has no observable effect, exactly the assumption ProofFrog's
        ``Topological Sorting`` makes when it prunes a call the return does not
        depend on. ``arg`` is left unconstrained, so one axiom covers any arity.
        """
        return ec_ast.Axiom(
            f"{module_name}_{method}_pres",
            f"(g : (glob {module_name})) : "
            f"phoare[ {module_name}.{method} : "
            f"(glob {module_name}) = g ==> (glob {module_name}) = g ] = 1%r",
            declare=True,
        )

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
        emit_state_vars: bool = False,
        param_module_types: dict[str, str] | None = None,
        param_primitive_types: dict[str, str] | None = None,
    ) -> ec_ast.Module:
        """Translate a Game.

        A single-primitive game takes exactly one primitive-instance parameter
        (e.g. ``Game Real(SymEnc E)``) and is emitted inside that primitive's
        abstract theory. A MULTI-primitive game (``CGLazyROTwoSeeded(KEM_PQ, NG,
        lambda)``) is emitted at top level after the sub-primitive clones; the
        caller then supplies ``param_module_types`` (each param's EC functor
        type, e.g. ``{"KEM_PQ": "KEM_PQ_c.Scheme", "NG": "NG_c.Scheme"}``) and
        ``param_primitive_types`` (each param's primitive name, for body-call
        ``type_of`` resolution), exactly like :meth:`translate_intermediate_game`.

        ``emit_state_vars`` declares each game-level field as a module-level
        ``var`` (mirroring :meth:`translate_flat_game` /
        :meth:`translate_reduction`). A **multi-oracle stateful** game (a KEM
        ``Initialize`` that sets ``pk``/``sk`` read by a later ``Challenge``)
        keeps that state on the module so the two procs share it; without the
        ``var`` block EC rejects the cross-proc reference with ``unknown
        module-level variable``. Single-oracle games leave this ``False`` and
        emit no ``var`` block, so their output is byte-identical -- their
        fields are inlined to method locals by canonicalization.
        """
        module_typed = [
            p for p in game.parameters if isinstance(p.type, frog_ast.Variable)
        ]
        if len(game.parameters) != 1 and len(module_typed) > 1:
            # A MULTI-PRIMITIVE game (e.g. the seedbased ROM helper
            # ``CGLazyROTwoSeeded(KEM_PQ, NG, lambda)``) is parameterized by
            # more than one primitive, so it cannot live inside a single
            # primitive's abstract theory; the caller emits it at TOP LEVEL
            # (after the sub-primitive clones) and supplies per-param EC/
            # primitive types, exactly like :meth:`translate_intermediate_game`.
            # Non-module (``Int``) params are dropped (compile-time indices).
            if param_module_types is None or param_primitive_types is None:
                raise ValueError(
                    f"multi-primitive game {module_name!r} needs "
                    "param_module_types/param_primitive_types from the caller"
                )
            # A multi-primitive ROM helper game (``CGLazyROTwoSeeded(KEM_PQ, NG,
            # lambda)``) lives INSIDE the theorem primitive's abstract theory,
            # where the sub-primitive clones (``KEM_PQ_c``/``NG_c``) are not in
            # scope. But its body never CALLS those params -- it only samples the
            # RO/seeds over theory-abstract bitstring types -- so the module-typed
            # params are dead. Emit the standard single theory ``Scheme`` functor
            # param (matching the ``Game_<name>(Em, A)`` wrapper's one-arg
            # application), and keep every param in ``body_param_types`` so a
            # (dead) type reference still resolves. This keeps the game in-theory
            # and compiling. If a future multi-primitive game genuinely CALLS a
            # sub-primitive param, EC rejects it (visible), and it needs the
            # separate top-level-emission route instead.
            emitted_type = emitted_param_type or param_type_name
            emitted_module_params = [
                ec_ast.ModuleParam(name=module_typed[0].name, module_type=emitted_type)
            ]
            body_param_types = param_primitive_types
        else:
            if len(game.parameters) == 1:
                param = game.parameters[0]
            else:
                # A foreign assumption game may carry non-module (e.g. ``Int
                # Nkey`` length) parameters alongside its single primitive
                # parameter, like ``Game Real(KDF H, Int Nkey)``. Keep the one
                # module-typed (primitive) parameter and drop the rest -- the
                # Ints surface only inside abstract bitstring-length
                # parameterizations, never as a free EC value.
                assert len(module_typed) == 1, (
                    "single-primitive path expects exactly one module-typed "
                    f"parameter; got {[p.type for p in game.parameters]}"
                )
                param = module_typed[0]
            emitted_type = emitted_param_type or param_type_name
            emitted_module_params = [
                ec_ast.ModuleParam(name=param.name, module_type=emitted_type)
            ]
            body_param_types = {param.name: param_type_name}
        field_types = {fld.name: fld.type for fld in game.fields}
        field_renames = _field_renames_for(game.fields)
        procs = [
            self._translate_method(
                method,
                body_param_types,
                field_types=field_types,
                field_renames=field_renames,
            )
            for method in game.methods
        ]
        module_vars = (
            [
                ec_ast.VarDecl(
                    _ec_field_name(fld.name), self._types.translate_type(fld.type)
                )
                for fld in game.fields
            ]
            if emit_state_vars
            else []
        )
        return ec_ast.Module(
            name=module_name,
            procs=procs,
            params=emitted_module_params,
            implements=implements,
            module_vars=module_vars,
        )

    def translate_intermediate_game(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        game: frog_ast.Game,
        module_name: str,
        param_module_types: dict[str, str],
        param_primitive_types: dict[str, str],
        implements: str | None = None,
        emit_state_vars: bool = False,
    ) -> ec_ast.Module:
        """Translate a multi-primitive intermediate game to an EC module.

        Unlike :meth:`translate_game` (which requires exactly one primitive
        parameter), an in-proof intermediate game such as
        ``Game G_RandKey(KEM K, PRF F)`` carries several primitive-typed
        parameters and is played against the *outer* theorem game's oracle, so
        it ascribes to that oracle type (``implements``).

        ``param_module_types`` gives each parameter its EC functor type
        (``{"K": "K_c.Scheme", "F": "F_c.Scheme"}``) for the emitted signature;
        ``param_primitive_types`` gives each its primitive name
        (``{"K": "KEM", "F": "PRF"}``) so body calls like ``K.encaps(...)`` /
        ``F.evaluate(...)`` resolve through the method-return-type registry.

        ``emit_state_vars`` declares each game-level field as a module-level
        ``var`` (mirroring :meth:`translate_reduction`): a multi-oracle game
        whose ``Initialize`` sets ``pk`` read by a later ``Challenge`` keeps
        that state on the module. The body must be pre-hoisted (see
        :func:`canonical_form.hoist_game_calls`) so nested module calls are
        already lifted to statements.
        """
        # Only module-typed parameters become EC functor params; non-module
        # parameters (e.g. ``Int q`` compile-time indices) are absent from
        # ``param_module_types`` and dropped, so a single-oracle intermediate
        # game like ``Hyb(Int q)`` emits as a parameterless module.
        module_params = [
            ec_ast.ModuleParam(name=p.name, module_type=param_module_types[p.name])
            for p in game.parameters
            if p.name in param_module_types
        ]
        field_types = {fld.name: fld.type for fld in game.fields}
        field_renames = _field_renames_for(game.fields)
        procs = [
            self._translate_method(
                method,
                param_primitive_types,
                field_types=field_types,
                field_renames=field_renames,
            )
            for method in game.methods
        ]
        module_vars = (
            [
                ec_ast.VarDecl(
                    _ec_field_name(fld.name), self._types.translate_type(fld.type)
                )
                for fld in game.fields
            ]
            if emit_state_vars
            else []
        )
        return ec_ast.Module(
            name=module_name,
            procs=procs,
            params=module_params,
            implements=implements,
            module_vars=module_vars,
        )

    def translate_flat_game(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        game: frog_ast.Game,
        module_name: str,
        external_module_types: dict[str, str],
        module_params: list[ec_ast.ModuleParam] | None = None,
        emit_state_vars: bool = False,
        use_canonical_fields: bool = False,
    ) -> ec_ast.Module:
        """Translate a parameterless intermediate game-state AST.

        Unlike :meth:`translate_game`, which expects a game declared with
        one primitive parameter, ``translate_flat_game`` consumes the
        inlined intermediate states produced by the engine's
        canonicalization pipeline (where the scheme parameter has been
        substituted with concrete let-bindings like ``E1``, ``E2``). The
        ``external_module_types`` map binds those let-names to primitive
        type names so calls like ``E1.Enc(...)`` resolve through the
        method-return-type registry.

        ``module_params`` declares EC module parameters on the emitted
        functor. When emitted inside an EC ``section`` with declared
        modules, the flat game must take each declared module as a
        parameter (e.g. ``(E1 : E1_c.Scheme) (E2 : E2_c.Scheme)``) so
        that EC's generalization-over-section finds those references.

        ``emit_state_vars`` declares each game-level field as a module-level
        ``var`` (mirroring :meth:`translate_reduction`). Multi-oracle stateful
        games (e.g. a KEM ``Initialize`` that sets ``sk``/``ctStar`` read by a
        later ``Decaps``) need their shared state to live on the module so the
        relational coupling invariant ``(glob M){1} = (glob M'){2}`` is
        non-vacuous. Single-oracle games (the legacy path) leave this ``False``
        and emit no ``var`` block, so their output is byte-identical -- those
        games' fields are inlined to method locals by canonicalization.
        """
        if game.parameters:
            raise NotImplementedError(
                "translate_flat_game expects a parameterless game; "
                f"got parameters {game.parameters}"
            )
        field_types = {fld.name: fld.type for fld in game.fields}
        # When the state is emitted with a module ``var`` block, canonically
        # rename its fields to type-ordered ``f<NN>`` names so a chain's adjacent
        # flat states name-sort their globs identically (EC orders ``glob`` by
        # name); otherwise the fields inline to locals and only the uppercase
        # lowering applies (byte-identical for non-state-var games).
        # ``use_canonical_fields`` is decided CHAIN-WIDE by the caller (a ROM
        # chain: some state carries an ``fmap`` RO table). It must be uniform
        # across every state of a chain -- an early state (before the RO is
        # inlined) has no map field, so a per-state gate would leave it on
        # stable names while its siblings go canonical, breaking the very
        # glob-name alignment the rename exists to fix.
        field_renames = (
            _canonical_field_renames(game.fields, self._types)
            if emit_state_vars and use_canonical_fields
            else _field_renames_for(game.fields)
        )
        procs = [
            self._translate_method(
                method,
                external_module_types,
                field_types=field_types,
                field_renames=field_renames,
            )
            for method in game.methods
        ]
        module_vars = (
            [
                ec_ast.VarDecl(
                    field_renames.get(fld.name, _ec_field_name(fld.name)),
                    self._types.translate_type(fld.type),
                )
                for fld in game.fields
            ]
            if emit_state_vars
            else []
        )
        return ec_ast.Module(
            name=module_name,
            procs=procs,
            params=list(module_params) if module_params else [],
            implements=None,
            module_vars=module_vars,
        )

    def translate_reduction(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        reduction: frog_ast.Reduction,
        primitive_name: str,
        oracle_type_name: str,
        emitted_primitive_type: str | None = None,
        param_renames: dict[str, str] | None = None,
        param_module_types: dict[str, str] | None = None,
        param_primitive_types: dict[str, str] | None = None,
        allow_void_call: bool = False,
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

        Stateful reductions (those with field declarations) are
        supported: each field becomes a module-level ``var`` declaration,
        and the procedure bodies read/write that shared state. Field
        assignments in the body carry no type annotation, so the
        statement translator renders them as ``<-`` updates to the
        module var rather than fresh locals.
        """
        if not reduction.parameters:
            raise ValueError(
                f"Reduction {reduction.name!r} has no parameters; "
                "need at least the primitive instance parameter."
            )

        # EC requires module parameter names to start with an uppercase
        # letter. The reduction body refers to the challenger by the
        # FrogLang name ``challenger``; we rename it to ``Challenger`` in
        # the generated EC module and alias references through below.
        challenger_ec_name = "Challenger"
        renames = dict(param_renames) if param_renames else {}
        emitted_type = emitted_primitive_type or primitive_name

        # Only module-typed parameters (those whose FrogLang type is a
        # bare ``Variable`` naming a primitive/scheme, e.g. ``KEM KEM1``)
        # become EC functor params. Value parameters (``Int pk1len`` and
        # other non-module types) are compile-time indices that appear only
        # inside bitstring-length types in the body (``BitString<pk1len>``
        # -> the abstract ``bs_pk1len`` type); emitting them as functor
        # params produces an invalid ``pk1len : <Scheme>`` signature. This
        # mirrors :meth:`translate_intermediate_game`'s param filtering.
        module_typed_params = [
            p for p in reduction.parameters if isinstance(p.type, frog_ast.Variable)
        ]
        per_param_types = dict(param_module_types or {})
        module_params: list[ec_ast.ModuleParam] = [
            ec_ast.ModuleParam(
                name=renames.get(p.name, p.name),
                module_type=per_param_types.get(p.name, emitted_type),
            )
            for p in module_typed_params
        ]
        module_params.append(
            ec_ast.ModuleParam(name=challenger_ec_name, module_type=oracle_type_name)
        )

        # Each module-typed param resolves ``type_of`` for calls on it
        # (``NG.Encode(...)`` -> the ``NominalGroup`` method-return-type key).
        # A multi-primitive reduction (e.g. the ROM ``R_Combined(KEM_PQ,
        # NominalGroup NG, PRG G, Label L, ...)``) has params of DIFFERENT
        # primitive types, so mapping them all to the single primary
        # ``primitive_name`` mis-keys every non-primary call. ``param_primitive_types``
        # (from the caller's instance model) gives each param its own primitive
        # type; the fallback to ``primitive_name`` keeps single-primitive
        # reductions byte-identical (there every param IS that primitive).
        param_prim = param_primitive_types or {}
        module_param_types: dict[str, str] = {
            p.name: param_prim.get(p.name, primitive_name) for p in module_typed_params
        }
        module_param_types["challenger"] = oracle_type_name

        module_var_aliases: dict[str, str] = {"challenger": challenger_ec_name}
        for src, dst in renames.items():
            module_var_aliases[src] = dst

        module_vars = [
            ec_ast.VarDecl(
                _ec_field_name(fld.name), self._types.translate_type(fld.type)
            )
            for fld in reduction.fields
        ]
        field_types = {fld.name: fld.type for fld in reduction.fields}
        field_renames = _field_renames_for(reduction.fields)

        procs = [
            self._translate_method(
                method,
                module_param_types,
                module_var_aliases,
                field_types=field_types,
                field_renames=field_renames,
                allow_void_call=allow_void_call,
            )
            for method in reduction.methods
        ]
        return ec_ast.Module(
            name=reduction.name,
            procs=procs,
            params=module_params,
            module_vars=module_vars,
        )

    def multi_oracle_spec(
        self,
        game_file: frog_ast.GameFile,
        model: oracle_model.GameOracleModel | None = None,
        scheme_args: list[frog_ast.Expression] | None = None,
    ) -> MultiOracleSpec | None:
        """Build the Initialize-lifted emission spec, or ``None`` if single-oracle.

        ``model`` defaults to classifying ``game_file`` directly; callers that
        already hold a model (the exporter threads one per game file) pass it to
        avoid re-classifying. Returns ``None`` for single-oracle games so the
        wrapper/adversary emitters take their legacy byte-identical path.

        ``scheme_args`` binds the game's formal scheme parameter(s) to the
        actual instantiation the spec describes, *before* translating the
        ``Initialize`` return type. This matters at top-level (concrete) scope
        when the game's formal scheme-param name collides with a different proof
        let of the same name -- e.g. ``Game Real(KEM K)`` instantiated at the
        outer scheme ``KF`` (``KEM_INDCCA_MultiChal(KF)``) while the proof also
        has an inner ``KEM K``. Without binding, ``K.SharedSecret`` resolves to
        the inner ``K``'s concrete type instead of ``KF``'s, so a wrapper's
        ``Initialize`` result (passed to the outer adversary) gets the wrong
        tuple type. Omitted (theory-mode emission) leaves the formal names in
        place -- the abstract-theory types are theory-local and clone-resolved,
        so that path stays byte-identical.
        """
        if model is None:
            model = oracle_model.classify_game_file(game_file)
        if not model.is_multi_oracle:
            return None
        init_method = next(
            m
            for m in game_file.games[0].methods
            if m.signature.name.lower() == model.init_name
        )
        return_type = init_method.signature.return_type
        if scheme_args:
            ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
            for param, arg in zip(game_file.games[0].parameters, scheme_args):
                ast_map.set(frog_ast.Variable(param.name), copy.deepcopy(arg))
            return_type = visitors.SubstitutionTransformer(ast_map).transform(
                copy.deepcopy(return_type)
            )
        return MultiOracleSpec(
            init_name=model.init_name or "",
            init_return_type=self._translate_param_type(return_type),
            post_init_names=list(model.post_init_names),
        )

    def translate_adversary_type(
        self,
        game_file: frog_ast.GameFile,
        oracle_type_name: str,
        adv_type_name: str | None = None,
        multi_oracle: MultiOracleSpec | None = None,
    ) -> ec_ast.ModuleType:
        """Emit ``module type <Gf>_Adv (O : <oracle>) = { proc distinguish ... }``.

        Single-oracle (``multi_oracle is None``): the adversary's interface is a
        bare ``proc distinguish() : bool``, matching the standard EC pattern for
        games whose adversaries make adaptive oracle queries.

        Multi-oracle (Initialize-lifted): ``distinguish`` gains the lifted-
        ``Initialize`` result as a parameter and is restricted to the post-init
        oracle set, e.g. ``proc distinguish(pk : pubkey) : bool {O.eval,
        O.chk}``. ``Initialize`` is excluded from the adversary's reachable
        oracles because the game wrapper runs it in ``main()`` before the
        adversary starts.

        When ``adv_type_name`` is supplied the caller controls the emitted
        identifier (used for sanitizing names containing non-identifier
        characters like ``$``).
        """
        if multi_oracle is None:
            distinguish = ec_ast.ProcSig(
                name="distinguish",
                params=[],
                return_type=ec_ast.EcType("bool"),
            )
        elif multi_oracle.init_return_type.text == "unit":
            # A lifted Initialize returning ``unit`` (e.g. KDF-PRF, whose init
            # only samples the key into a field) carries no result to thread, and
            # EC rejects an explicit ``unit`` proc argument. The adversary takes
            # no param; the oracle restriction still stands (init is run in
            # ``main`` before the adversary, so ``O.init`` stays excluded).
            distinguish = ec_ast.ProcSig(
                name="distinguish",
                params=[],
                return_type=ec_ast.EcType("bool"),
                oracle_restriction=multi_oracle.oracle_restriction("O"),
            )
        else:
            distinguish = ec_ast.ProcSig(
                name="distinguish",
                params=[
                    ec_ast.ProcParam(INIT_RESULT_NAME, multi_oracle.init_return_type)
                ],
                return_type=ec_ast.EcType("bool"),
                oracle_restriction=multi_oracle.oracle_restriction("O"),
            )
        return ec_ast.ModuleType(
            name=adv_type_name or f"{game_file.name}_Adv",
            procs=[distinguish],
            params=[ec_ast.ModuleParam(name="O", module_type=oracle_type_name)],
        )

    def translate_reduction_adversary(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        reduction: frog_ast.Reduction,
        outer_adversary_type_name: str,
        inner_oracle_type_name: str,
        scheme_module_expr: str,
        reduction_arg_exprs: list[str] | None = None,
        extra_module_params: list[ec_ast.ModuleParam] | None = None,
        inner_multi_oracle: MultiOracleSpec | None = None,
        outer_multi_oracle: MultiOracleSpec | None = None,
        method_return_types: dict[tuple[str, str], frog_ast.Type] | None = None,
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

        Multi-oracle (Initialize-lifted): when ``outer_multi_oracle`` is given,
        ``R_Adv`` must ascribe to the inner Initialize-lifted adversary type, so
        ``distinguish`` gains the inner ``Initialize`` result as a parameter.
        Because the *outer* adversary ``A`` expects the outer ``Initialize``
        result, the body runs ``Initialize`` on the reduction-composed game
        ``R(...)`` and threads *that* into ``A``::

            proc distinguish(pk : <inner_init_ret>) : bool = {
              var b : bool;
              var pk0 : <outer_init_ret>;
              pk0 <@ R(<args>, C).initialize();
              b   <@ A(R(<args>, C)).distinguish(pk0);
              return b;
            }

        **Forward-pk vs re-init (blocker B).** When the inner game is itself
        multi-oracle *and* the reduction's ``Initialize`` is a pure forward
        (``return challenger.Initialize();``), the lifted ``main`` has already
        run the inner ``Initialize``; ``distinguish`` then forwards the received
        ``pk`` directly to ``A`` rather than re-running ``Initialize`` through
        ``R`` (which would call ``C.initialize`` a second time and violate the
        restricted post-init-only adversary interface). Otherwise -- a
        single-oracle inner game, or a reduction whose ``Initialize`` is
        independent of the challenger (generates its own keypair / state) --
        ``distinguish`` re-runs ``R``'s own ``Initialize`` to establish that
        state. EC-compilation validation of the forward-pk shape is pending a
        hand-derived template (Docker required).
        """
        if reduction_arg_exprs is None:
            reduction_arg_exprs = [scheme_module_expr]
        call_args = ", ".join(list(reduction_arg_exprs) + ["C"])
        composed = f"{reduction.name}({call_args})"
        body: list[ec_ast.EcStmt] = [
            ec_ast.VarDecl(name="b", type=ec_ast.EcType("bool"))
        ]
        distinguish_params: list[ec_ast.ProcParam] = []

        def reinit(outer_spec: MultiOracleSpec) -> str:
            # Run the reduction's OWN Initialize to produce the outer-init
            # result (and set the reduction's own state). Type-safe whenever
            # the reduction's Initialize does not call ``challenger.Initialize``.
            outer_init_local = f"{INIT_RESULT_NAME}0"
            # ``pk0`` is literally ``<reduction>(...).initialize()``, so its EC
            # type is the *reduction's own* Initialize return type, not the
            # generic outer game file's. The outer game file (e.g.
            # ``KEM_INDCCA_MultiChal``) is cloned once per scheme, so
            # ``outer_spec.init_return_type`` -- computed from the generic file
            # -- resolves the abstract shared-secret to whichever clone the type
            # environment happens to bind (the inner scheme's), giving the wrong
            # concrete type for the outer reduction. The reduction declares the
            # outer clone's types explicitly (``[KF.PublicKey, KF.SharedSecret,
            # KF.Ciphertext]``), which translate to the correct concrete tuple.
            init_method = _reduction_init_method(reduction)
            pk0_type = (
                self._translate_param_type(init_method.signature.return_type)
                if init_method is not None
                else outer_spec.init_return_type
            )
            body.append(
                ec_ast.VarDecl(
                    name=outer_init_local,
                    type=pk0_type,
                )
            )
            body.append(
                ec_ast.Call(
                    var=outer_init_local,
                    callee=f"{composed}.{outer_spec.init_name}",
                    args="",
                )
            )
            return outer_init_local

        if outer_multi_oracle is None:
            distinguish_args = ""
        elif inner_multi_oracle is not None:
            # Inner game is multi-oracle: its Initialize was lifted into the
            # wrapper's ``main()``, which threads the inner-init result into
            # ``distinguish`` as ``pk``.
            distinguish_params.append(
                ec_ast.ProcParam(INIT_RESULT_NAME, inner_multi_oracle.init_return_type)
            )
            init_method = _reduction_init_method(reduction)
            if init_method is not None and _is_pure_forward_init(init_method):
                # Forward-pk path (blocker B). The reduction's Initialize merely
                # forwards ``challenger.Initialize()``, so the outer init result
                # equals the received ``pk``; re-running it would call
                # ``C.initialize`` again and violate the restricted post-init-only
                # adversary interface.
                distinguish_args = INIT_RESULT_NAME
            elif reduction_repacks_challenger_init(reduction):
                # Consume-pk path. The reduction's Initialize forwards the
                # challenger's Initialize but *repacks* its result (keeping the
                # leaked decaps keys in its own fields, handing the outer
                # adversary only the reduced result). The assumption game already
                # ran the challenger's Initialize and passed the full result as
                # ``pk``, so ``distinguish`` reconstructs the reduction's field
                # state and the outer-init result directly from ``pk`` -- never
                # re-invoking ``C.initialize`` (which would double-initialize the
                # challenger and violate the post-init-only restriction).
                outer_init_local = f"{INIT_RESULT_NAME}0"
                init_ret_type = (
                    self._translate_param_type(init_method.signature.return_type)
                    if init_method is not None
                    else outer_multi_oracle.init_return_type
                )
                body.append(ec_ast.VarDecl(name=outer_init_local, type=init_ret_type))
                consumed_decls, consumed_stmts = self._render_consumed_pk_init(
                    reduction,
                    pk_param_name=INIT_RESULT_NAME,
                    pk0_local_name=outer_init_local,
                    challenger_oracle_type=inner_oracle_type_name,
                    method_return_types=method_return_types or {},
                    reduction_arg_exprs=reduction_arg_exprs,
                )
                body.extend(consumed_decls)
                body.extend(consumed_stmts)
                distinguish_args = outer_init_local
            else:
                distinguish_args = reinit(outer_multi_oracle)
        else:
            # Inner game is single-oracle: nothing is lifted, so ``distinguish``
            # takes no parameter (matching the inner single-oracle adversary
            # type). The reduction supplies the outer-init result by running its
            # own Initialize, which is independent of the inner challenger (it
            # generates its own keypair / state) and so never touches ``C``.
            distinguish_args = reinit(outer_multi_oracle)
        body.append(
            ec_ast.Call(
                var="b",
                callee=f"A({composed}).distinguish",
                args=distinguish_args,
            )
        )
        body.append(ec_ast.Return(expr="b"))
        # ROM: the reduction adversary simulates the theorem game for ``A``, which
        # samples the shared random oracle ONCE up front (see the experiment-main
        # builder). Sample it here too so ``A`` sees a fresh, consistent RO -- the
        # Pr-lemma byequiv against the theorem game is otherwise unalignable (the
        # game samples ``RO_H.h`` but the reduction-composed side never does).
        # Sound: a fresh RO for ``A`` is exactly what the theorem game provides.
        # Gated on registered RO holders, so non-ROM reduction adversaries (every
        # binding/correctness proof) get no sample and stay byte-identical.
        ro_samples: list[ec_ast.EcStmt] = [
            ec_ast.Sample(f"{mod_name}.h", dfun)
            for mod_name, dfun in self._types.function_value_modules()
        ]
        if ro_samples:
            insert_at = next(
                (
                    idx
                    for idx, st in enumerate(body)
                    if not isinstance(st, ec_ast.VarDecl)
                ),
                len(body),
            )
            body[insert_at:insert_at] = ro_samples
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
                    params=distinguish_params,
                    return_type=ec_ast.EcType("bool"),
                    body=body,
                )
            ],
            params=params,
        )

    def _render_consumed_pk_init(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        reduction: frog_ast.Reduction,
        pk_param_name: str,
        pk0_local_name: str,
        challenger_oracle_type: str = "",
        method_return_types: dict[tuple[str, str], frog_ast.Type] | None = None,
        reduction_arg_exprs: list[str] | None = None,
    ) -> tuple[list[ec_ast.VarDecl], list[ec_ast.EcStmt]]:
        """Render the reduction's ``Initialize`` with the challenger's
        ``Initialize()`` result replaced by the leaked ``pk`` parameter.

        Produces the statements that (a) store the challenger-derived decaps
        keys into the reduction's own module fields (qualified ``<R>.<field>``,
        since the assignment is emitted *outside* the reduction) and (b) bind
        the outer-init result to ``pk0_local_name``. Called only when
        :func:`reduction_repacks_challenger_init` holds, so the body's single
        module call is the ``challenger.Initialize()`` (captured by an
        assignment) plus any calls/samples the reduction makes on its own behalf.

        Nested module calls (``ek_T <- NG.Exp(NG.Generator(), dk_T)``) are hoisted
        first via :func:`canonical_form.hoist_reduction_calls` -- EC forbids a
        call inside an expression, and the type-map seeder cannot type a nested
        ``FuncCall`` -- so the statement translator sees only top-level calls. A
        reduction with no nested call is unchanged by the hoist. The returned
        decls/stmts are spliced into ``R_Adv.distinguish`` before the
        ``A(R(...)).distinguish(pk0)`` call.
        """
        if method_return_types:
            reduction = canonical_form.hoist_reduction_calls(
                reduction, challenger_oracle_type, method_return_types
            )
        init = _reduction_init_method(reduction)
        assert init is not None
        field_types = {fld.name: fld.type for fld in reduction.fields}
        field_renames = _field_renames_for(reduction.fields)
        field_names = {fld.name for fld in reduction.fields}

        # Rewrite the body: challenger.Initialize() -> the leaked ``pk``; the
        # ``return E`` becomes ``pk0 <- E`` (the outer-init result binding).
        new_stmts: list[frog_ast.Statement] = []
        ret_expr: frog_ast.Expression | None = None
        for stmt in init.block.statements:
            if isinstance(stmt, frog_ast.ReturnStatement):
                ret_expr = stmt.expression
                continue
            if isinstance(stmt, frog_ast.Assignment) and _is_challenger_init_call(
                stmt.value
            ):
                new_stmts.append(
                    frog_ast.Assignment(
                        stmt.the_type, stmt.var, frog_ast.Variable(pk_param_name)
                    )
                )
            else:
                new_stmts.append(stmt)
        assert ret_expr is not None
        new_stmts.append(
            frog_ast.Assignment(None, frog_ast.Variable(pk0_local_name), ret_expr)
        )

        # Type map (mirrors ``_translate_method``): seed fields first, then the
        # rewritten body's local declarations, then resolve tuple aliases so a
        # projection ``_tup.`i`` types.
        type_map: dict[str, frog_ast.Type] = dict(field_types)
        for stmt in new_stmts:
            _seed_type_map(stmt, type_map)
        for name, t in list(type_map.items()):
            if isinstance(t, (frog_ast.Variable, frog_ast.FieldAccess)):
                resolved = self._types.resolve(t)
                if isinstance(resolved, frog_ast.ProductType):
                    type_map[name] = resolved

        type_of = self._type_of_factory(type_map, {})
        exprs = expr_translator.ExpressionTranslator(
            self._types, type_of, field_renames=field_renames
        )
        # The spliced Initialize is emitted OUTSIDE the reduction module, so the
        # reduction's own functor params (``KEM_PQ``, ``NG``, ...) are not in the
        # adversary's scope. Rewrite each to the module EXPRESSION the adversary
        # applies the reduction with (``KEM_PQ`` -> ``SeededKEMWrapper(
        # KEM_PQ_inner)``), from ``reduction_arg_exprs`` (declaration order,
        # challenger excluded). A ROM reduction also makes OTHER challenger calls
        # besides the ``challenger.Initialize()`` replaced with ``pk`` (a
        # ``challenger.Hash(seed)``); the adversary names the challenger functor
        # param ``C`` (:meth:`translate_reduction_adversary`), so ``challenger``
        # -> ``C`` too (EC modules are uppercase-initial; a bare
        # ``challenger.hash`` is a parse error). A single-primitive reduction
        # whose params ARE the adversary's own params, with a pure forward+repack
        # Initialize (no residual ``challenger`` ref), is byte-identical: the
        # ``<param> -> <param>`` aliases are identity, and no ``challenger``
        # survives.
        module_var_aliases = {
            p.name: e for p, e in zip(reduction.parameters, reduction_arg_exprs or [])
        }
        module_var_aliases["challenger"] = "C"
        stmts = stmt_translator.StatementTranslator(
            self._types,
            exprs,
            module_var_aliases=module_var_aliases,
            type_map=type_map,
        )
        translated = stmts.translate_block(frog_ast.Block(new_stmts))

        # The reduction's own field writes/reads render as bare ``<field>`` (the
        # statement translator has no owning module); qualify them with the
        # reduction's module name so they target ``<R>``'s globals from the
        # adversary wrapper. WRITES qualify the LHS ``st.var``; READS qualify
        # whole-word field occurrences in RHS/args -- a consume-pk-with-
        # computation reduction (CFRG ``R_PQ_Bind``) keygens its own component
        # fields and then packs them (``ek0 <- (ek_PQ_0, ek_T_0)`` reads the
        # field ``ek_T_0``), so the read must resolve to ``R.ek_T_0`` too. A pure
        # forward+repack reduction (the Generic ``LEAK=>HON`` ``R``) packs only
        # the consumed ``pk`` projections and holds no own-computed field it
        # re-reads, so its RHS has no field token and stays byte-identical.
        def _qualify_reads(text: str) -> str:
            for fname in field_names:
                text = re.sub(
                    rf"(?<!\.)\b{re.escape(fname)}\b",
                    f"{reduction.name}.{_ec_field_name(fname)}",
                    text,
                )
            return text

        for st in translated.stmts:
            if isinstance(st, (ec_ast.Assign, ec_ast.Call)) and st.var in field_names:
                st.var = f"{reduction.name}.{_ec_field_name(st.var)}"
            if isinstance(st, ec_ast.Assign):
                st.rhs = _qualify_reads(st.rhs)
            elif isinstance(st, ec_ast.Call):
                st.args = _qualify_reads(st.args)
        return translated.var_decls, translated.stmts

    def translate_game_wrapper(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        wrapper_name: str,
        adversary_type_name: str,
        oracle_module_expr: str,
        extra_module_params: list[ec_ast.ModuleParam] | None = None,
        multi_oracle: MultiOracleSpec | None = None,
    ) -> ec_ast.Module:
        """Emit a ``main()``-wrapper module for one step in the proof.

        The wrapper takes an adversary parameter ``A`` and a single ``main``
        procedure that runs ``A`` against the given oracle module expression.

        Single-oracle (``multi_oracle is None``): ``main`` just runs
        ``b <@ A(<oracle>).distinguish()``.

        Multi-oracle (Initialize-lifted): ``main`` first runs the lifted
        ``Initialize`` on the same oracle module and passes its result to the
        adversary::

            proc main() : bool = {
              var b : bool;
              var pk : <init_ret>;
              pk <@ <oracle>.initialize();
              b  <@ A(<oracle>).distinguish(pk);
              return b;
            }

        Lifting ``Initialize`` into ``main()`` (rather than coupling the two
        games' state in the byequiv precondition) is what makes the
        state-coupling invariant establishable before the adversary runs.

        Args:
            wrapper_name: e.g. ``"Game_step_0"``.
            adversary_type_name: e.g. ``"OneTimeSecrecyLR_Adv"``.
            oracle_module_expr: rendered EC expression for the oracle the
                adversary should be given, e.g.
                ``"OneTimeSecrecyLR_Left(OTP)"`` or
                ``"R1(OTP, OneTimeSecrecy_Real(OTP))"``.
            extra_module_params: additional module parameters before ``A``
                (e.g. declared module instances inside a section).
            multi_oracle: Initialize-lifted spec, or ``None`` for single-oracle.
        """
        # A lifted Initialize returning ``unit`` (e.g. KDF-PRF) carries no result:
        # run it for its side effect but thread no ``pk`` (EC rejects an explicit
        # unit proc argument, and a ``pk : unit`` local would be unused).
        unit_init = (
            multi_oracle is not None and multi_oracle.init_return_type.text == "unit"
        )
        body: list[ec_ast.EcStmt] = [
            ec_ast.VarDecl(name="b", type=ec_ast.EcType("bool"))
        ]
        if multi_oracle is not None and not unit_init:
            body.append(
                ec_ast.VarDecl(
                    name=INIT_RESULT_NAME, type=multi_oracle.init_return_type
                )
            )
        # Sample each shared random oracle ONCE, before the experiment runs --
        # the EC realization of the ProofFrog theorem's ``let: Function<D,R> H
        # <- Function<D,R>;`` (sample the RO, pass it to the experiment). It is
        # read-only thereafter (the adversary touches it only via the game's
        # hash oracle). ``var`` decls must all precede statements, so this lands
        # right after them.
        for mod_name, dfun in self._types.function_value_modules():
            body.append(ec_ast.Sample(f"{mod_name}.h", dfun))
        if multi_oracle is None:
            distinguish_args = ""
        elif unit_init:
            body.append(
                ec_ast.Call(
                    var="",
                    callee=f"{oracle_module_expr}.{multi_oracle.init_name}",
                    args="",
                )
            )
            distinguish_args = ""
        else:
            body.append(
                ec_ast.Call(
                    var=INIT_RESULT_NAME,
                    callee=f"{oracle_module_expr}.{multi_oracle.init_name}",
                    args="",
                )
            )
            distinguish_args = INIT_RESULT_NAME
        body.append(
            ec_ast.Call(
                var="b",
                callee=f"A({oracle_module_expr}).distinguish",
                args=distinguish_args,
            )
        )
        body.append(ec_ast.Return(expr="b"))
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
        multi_oracle: MultiOracleSpec | None = None,
    ) -> ec_ast.Module:
        """Assumption-game ``main()`` wrapper parameterized on ``(E, A)``.

        Single-oracle emits::

            module <wrapper_name> (<E> : <Scheme>, A : <Adv>) = {
              proc main() : bool = {
                var b : bool;
                b <@ A(<side>(<E>)).distinguish();
                return b;
              }
            }

        Multi-oracle (Initialize-lifted) runs ``Initialize`` on ``<side>(<E>)``
        first and threads its result into ``distinguish`` (mirroring
        :meth:`translate_game_wrapper`).

        Lives inside the primitive's abstract theory so the advantage
        axiom can forall-quantify over both the adversary and the
        scheme instance.
        """
        oracle_expr = f"{side_module_name}({scheme_param_name})"
        # A lifted Initialize returning ``unit`` (e.g. KDF-PRF) carries no result:
        # run it for its side effect but thread no ``pk`` (EC rejects an explicit
        # unit proc argument; the adversary type drops the param to match).
        unit_init = (
            multi_oracle is not None and multi_oracle.init_return_type.text == "unit"
        )
        body: list[ec_ast.EcStmt] = [
            ec_ast.VarDecl(name="b", type=ec_ast.EcType("bool"))
        ]
        if multi_oracle is None:
            distinguish_args = ""
        elif unit_init:
            body.append(
                ec_ast.Call(
                    var="",
                    callee=f"{oracle_expr}.{multi_oracle.init_name}",
                    args="",
                )
            )
            distinguish_args = ""
        else:
            body.append(
                ec_ast.VarDecl(
                    name=INIT_RESULT_NAME, type=multi_oracle.init_return_type
                )
            )
            body.append(
                ec_ast.Call(
                    var=INIT_RESULT_NAME,
                    callee=f"{oracle_expr}.{multi_oracle.init_name}",
                    args="",
                )
            )
            distinguish_args = INIT_RESULT_NAME
        body.append(
            ec_ast.Call(
                var="b",
                callee=f"A({oracle_expr}).distinguish",
                args=distinguish_args,
            )
        )
        body.append(ec_ast.Return(expr="b"))
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

    def _translate_method(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        method: frog_ast.Method,
        module_param_types: dict[str, str],
        module_var_aliases: dict[str, str] | None = None,
        field_types: dict[str, frog_ast.Type] | None = None,
        field_renames: dict[str, str] | None = None,
        allow_void_call: bool = False,
    ) -> ec_ast.Proc:
        sig = method.signature
        ec_params = [
            ec_ast.ProcParam(
                expr_translator.mangle_ec_name(p.name, field_renames or {}),
                self._translate_param_type(p.type),
            )
            for p in sig.parameters
        ]
        return_type = self._translate_param_type(sig.return_type)

        type_map: dict[str, frog_ast.Type] = {}
        # Seed enclosing module-level fields first so an oracle body that
        # reads shared state (e.g. a ``_hoisted_0`` field the engine's
        # ``Hoist Deterministic Call to Initialize`` lifts into the game's
        # Initialize and a later oracle consumes) types its references.
        # Parameters and local declarations below override on name clash.
        if field_types:
            type_map.update(field_types)
        for p in sig.parameters:
            type_map[p.name] = p.type
        for stmt in method.block.statements:
            _seed_type_map(stmt, type_map)

        # Resolve tuple-typed aliases to their ProductType so ``type_of`` can
        # type a projection ``k[i]`` whose base is declared via a Set alias
        # (e.g. a scheme param ``Key k`` where ``Key = [BitString<l>,
        # BitString<l>]``). Without this the projection's base resolves to a
        # bare Variable and ``type_of`` raises NotImplementedError -> the whole
        # method body falls back to ``return witness``. Gated to Variable/
        # FieldAccess aliases that resolve to a ProductType, so non-tuple types
        # are untouched.
        for name, t in list(type_map.items()):
            if isinstance(t, (frog_ast.Variable, frog_ast.FieldAccess)):
                resolved = self._types.resolve(t)
                if isinstance(resolved, frog_ast.ProductType):
                    type_map[name] = resolved

        type_of = self._type_of_factory(type_map, module_param_types)
        # Rename a variable reassigned to a CONFLICTING type within a block (the
        # engine's ``__determ_N__`` temp-counter can collide two disjoint-live
        # values on one name across a branch boundary -- a seedbased binding
        # collision branch reassigns an NG-scalar temp with a KEM DecapsKey). EC
        # gives a variable one type, so the reassignment mis-types; the outer
        # binding is dead in the branch, so a scope-local rename is sound.
        # Byte-identical (returns the same list object) when no conflict fires.
        method_statements = _rename_type_conflicting_reuse(
            method.block.statements,
            type_of,
            type_map,
            lambda t: self._types.translate_type(t).text,
        )
        method_block = (
            method.block
            if method_statements is method.block.statements
            else frog_ast.Block(method_statements)
        )
        # Infer types of engine-inlined UNTYPED assignments from their RHS so a
        # later slice/projection of the var types instead of raising. The lazy-RO
        # case-split (``__a <- y0 || y1;`` in one branch, ``__a <- H(x);`` in
        # another) produces such a var used after the ``if`` as a full seed that
        # is then sliced into its per-KEM components. Runs after ``type_of`` is
        # built (it closes over ``type_map`` by reference, so newly-inferred
        # entries feed later inferences) and gap-fills only (``setdefault`` +
        # only where ``type_of`` on the RHS succeeds): a var that already has a
        # type, or whose RHS is not yet typeable, is untouched -- so every proof
        # that already exported is byte-identical (an untyped var used in a
        # type-requiring position that resolves today never reaches here; one
        # that does not resolve today crashes the export, so none exist).
        inferred_untyped = _infer_untyped_assignment_types(
            method_statements, type_of, type_map
        )
        exprs = expr_translator.ExpressionTranslator(
            self._types, type_of, field_renames=field_renames
        )
        stmts = stmt_translator.StatementTranslator(
            self._types,
            exprs,
            module_var_aliases=module_var_aliases,
            allow_void_call=allow_void_call,
            type_map=type_map,
        )
        try:
            translated = stmts.translate_block(method_block, return_type=return_type)
            body: list[ec_ast.EcStmt] = []
            # Declare the locals inferred by ``_infer_untyped_assignment_types``:
            # they are assigned untyped (``v <- rhs`` in an if/for body -- the
            # lazy-RO case-split ``__a3__``), so the statement translator renders
            # them bare (no ``VarDecl``) and EC rejects the undeclared module var.
            # These names are locals (fields/params/typed-assignment vars are
            # pre-seeded into ``type_map``, so the inference skips them), and none
            # is already declared by the statement translator (it declares only
            # typed assignments). Ordered by first-assignment position for
            # determinism; deduped against the translator's own decls defensively.
            already = {d.name for d in translated.var_decls}
            for name in inferred_untyped:
                ec_name = exprs.ec_name(name)
                if ec_name in already:
                    continue
                already.add(ec_name)
                body.append(
                    ec_ast.VarDecl(ec_name, self._types.translate_type(type_map[name]))
                )
            body.extend(translated.var_decls)
            body.extend(translated.stmts)
            # Drop statements after a top-level ``return``. Canonicalization can
            # hoist a return above now-dead code (e.g. "Absorb Redundant Early
            # Return" moving a challenge oracle's ``return false;`` above the
            # decapsulations whose results it no longer reads), which is fine in
            # FrogLang's semantics (the trailing statements are unreachable) but
            # is a parse error in EC, where ``return`` must be a procedure's
            # terminal statement. The tail is unreachable, so dropping it
            # preserves behavior. A clean export never has this shape (it would
            # already be EC-rejected), so this is a no-op for every passing
            # proof.
            for _idx, _st in enumerate(body):
                if isinstance(_st, ec_ast.Return):
                    del body[_idx + 1 :]
                    break
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


def _ec_field_name(name: str) -> str:
    """EC module-global variables must be lowercase-initial.

    A FrogLang game field with an uppercase initial (e.g. the random
    function ``RF``) would otherwise emit ``var RF : ...``, which EC's
    lexer rejects (a module variable is an ``lident``). Lowercasing only
    the first character keeps the rename minimal and collision-resistant
    (``RF`` -> ``rF``); an already-lowercase field is returned unchanged,
    so the common case (and every existing export) is byte-identical.
    """
    if name and name[0].isupper():
        return name[0].lower() + name[1:]
    return name


def _field_renames_for(game_fields: list[frog_ast.Field]) -> dict[str, str]:
    """Rename map for fields whose EC identifier differs from the FrogLang
    name (only uppercase-initial fields); empty for the all-lowercase case."""
    return {
        fld.name: _ec_field_name(fld.name)
        for fld in game_fields
        if _ec_field_name(fld.name) != fld.name
    }


def _canonical_field_renames(
    game_fields: list[frog_ast.Field], types: tc.TypeCollector
) -> dict[str, str]:
    """Rename every state field to a canonical ``f<NN>`` name ordered by EC type.

    A per-hop micro-lemma couples two adjacent flat states with
    ``(glob S1){1} = (glob S2){2}``. EC orders ``glob`` by VARIABLE NAME
    (alphabetical), so two states with the same field-type multiset but
    DIFFERENT names (the engine keeps some semantic ``dk_0``/``_hoisted_0`` and
    standardizes others to ``field1..k``) produce different glob tuple TYPES and
    EC rejects the ``=``. Naming every field ``f00``, ``f01``, ... in EC-type
    order makes the corresponding fields name-sort identically across the chain
    (all-distinct types align uniquely; a stable secondary index by original
    position keeps same-typed fields in a consistent relative order). Zero-padded
    to 2 digits so the ``fNN`` names themselves sort in rank order."""
    ordered = sorted(
        enumerate(game_fields),
        key=lambda p: (types.translate_type(p[1].type).text, p[0]),
    )
    return {fld.name: f"f{rank:02d}" for rank, (_, fld) in enumerate(ordered)}


def _infer_untyped_assignment_types(
    statements: Sequence[frog_ast.Statement],
    type_of: Callable[[frog_ast.Expression], frog_ast.Type],
    type_map: dict[str, frog_ast.Type],
) -> list[str]:
    """Fill ``type_map`` with the types of untyped assignments (``v <- rhs`` with
    no annotation) by evaluating ``type_of`` on the RHS, to a fixpoint (an
    inferred var can feed a later RHS). Descends ``if``/``for`` bodies. Gap-fill:
    ``setdefault`` and only when ``type_of(rhs)`` succeeds, so an already-typed
    var or an untypeable RHS is left as-is. Returns the newly-inferred var names
    in first-assignment order (these are locals -- fields are pre-seeded into
    ``type_map`` -- so the caller can declare them, which the statement
    translator does not do for untyped assignments)."""

    inferred_order: list[str] = []

    def _walk(stmts: Sequence[frog_ast.Statement]) -> int:
        added = 0
        for st in stmts:
            if isinstance(st, frog_ast.IfStatement):
                for block in st.blocks:
                    added += _walk(block.statements)
            elif isinstance(st, frog_ast.GenericFor):
                added += _walk(st.block.statements)
            elif (
                isinstance(st, frog_ast.Assignment)
                and st.the_type is None
                and isinstance(st.var, frog_ast.Variable)
                and st.var.name not in type_map
            ):
                try:
                    inferred = type_of(st.value)
                except (KeyError, NotImplementedError):
                    continue
                type_map.setdefault(st.var.name, inferred)
                if st.var.name not in inferred_order:
                    inferred_order.append(st.var.name)
                added += 1
        return added

    for _ in range(len(type_map) + 4):  # fixpoint; bounded by the var count
        if _walk(statements) == 0:
            break
    return inferred_order


def _rename_type_conflicting_reuse(
    statements: Sequence[frog_ast.Statement],
    type_of: Callable[[frog_ast.Expression], frog_ast.Type],
    type_map: dict[str, frog_ast.Type],
    type_text: Callable[[frog_ast.Type], str],
) -> Sequence[frog_ast.Statement]:
    """Rename an engine ``__determ_N__`` temp reassigned to a type that CONFLICTS
    with its established type WITHIN a block, to a fresh local.

    The engine's ``__determ_N__`` deterministic-call temps (``inlining.py`` counter)
    can collide two disjoint-live-range values on one name across a branch boundary:
    a seedbased binding challenge's collision branch reassigns an outer NG-scalar
    temp (``__determ_3__ : NGScalar`` from ``NG.RandomScalar``) with a KEM DecapsKey
    (``__determ_3__ <- DeriveKeyPair(seed).\\`2``). EC gives a variable ONE type, so
    the reassignment mis-types ("This expression has type ..."). The outer binding is
    dead in that branch (the reassigned value never escapes it -- the branch ends, and
    the sibling/post-branch statements read the outer value), so a scope-local rename
    is sound: substitute the conflicting var -> a fresh name from the reassignment
    onward, discarding the rename at the block boundary. Recurses into ``if``/``for``
    bodies. Returns the original list object unchanged when no conflict fires, so every
    proof without such a collision is byte-identical.

    Gated to ``__determ_``-prefixed temps: this is the documented counter-collision
    artifact, and its conflicts are genuine large type gaps. A bare-name conflict on
    a semantic variable is instead almost always a ``type_of`` under-qualification (two
    same-typed method calls whose return types RENDER differently) -- a false positive
    that must not drive a rename. The fresh var is NOT pre-seeded into ``type_map``, so
    the downstream statement translator (typed reassignment) or
    ``_infer_untyped_assignment_types`` (untyped) declares it -- both paths covered."""
    changed = [False]
    counter = [0]

    def _conflict_type(st: frog_ast.Assignment) -> frog_ast.Type | None:
        if st.the_type is not None:
            return st.the_type
        try:
            return type_of(st.value)
        except (KeyError, NotImplementedError):
            return None

    def _rewrite(stmts: Sequence[frog_ast.Statement]) -> list[frog_ast.Statement]:
        out: list[frog_ast.Statement] = []
        rename: dict[str, str] = {}
        for st in stmts:
            if rename:
                ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                for old, new in rename.items():
                    ast_map.set(frog_ast.Variable(old), frog_ast.Variable(new))
                st = visitors.SubstitutionTransformer(ast_map).transform(st)
            if isinstance(st, frog_ast.IfStatement):
                st = frog_ast.IfStatement(
                    st.conditions,
                    [frog_ast.Block(_rewrite(b.statements)) for b in st.blocks],
                )
            elif isinstance(st, frog_ast.GenericFor):
                st = frog_ast.GenericFor(
                    st.var_type,
                    st.var_name,
                    st.over,
                    frog_ast.Block(_rewrite(st.block.statements)),
                )
            elif isinstance(st, frog_ast.Assignment) and isinstance(
                st.var, frog_ast.Variable
            ):
                v = st.var.name
                prior = type_map.get(v)
                t2 = _conflict_type(st)
                if (
                    v.startswith("__determ_")
                    and prior is not None
                    and t2 is not None
                    and type_text(prior) != type_text(t2)
                ):
                    counter[0] += 1
                    fresh = f"{v}_ty{counter[0]}"
                    rename[v] = fresh
                    st = frog_ast.Assignment(
                        st.the_type, frog_ast.Variable(fresh), st.value
                    )
                    changed[0] = True
            out.append(st)
        return out

    rewritten = _rewrite(statements)
    return rewritten if changed[0] else statements


def _seed_type_map(
    stmt: frog_ast.Statement,
    type_map: dict[str, frog_ast.Type],
    gap_fill: bool = False,
) -> None:
    """Record declared-variable types into the map for the expr translator.

    Recurses into a ``for e in m.entries`` map-iteration loop (a ``GenericFor``)
    so locals declared in its body -- e.g. ``BitString<n> m = e[0];`` whose
    ``m`` is later sliced -- plus the loop variable ``e`` are typed.

    ``if`` branches are descended in **gap-fill** mode (``setdefault`` -- never
    overwriting a type already seeded at the enclosing level): a var declared
    inside a conditional (e.g. an exclusion-sampling case-split
    ``if (s == s0) { BitString<n> a = ...; }``) and then used *after* the ``if``
    otherwise has no type -> ``type_of`` raises and the whole body witness-stubs
    (or, if that var is sliced, the export crashes). Gap-fill is byte-identical:
    it only ADDS an entry for a name the top-level pass left unset, so a proof
    whose top-level and branch reuse a name keeps its top-level type, and a name
    used in a type-requiring position that already resolved is untouched.

    ``gap_fill`` (set only while inside an ``if`` branch) makes every write here
    a ``setdefault``."""

    def _put(name: str, the_type: frog_ast.Type) -> None:
        if gap_fill:
            type_map.setdefault(name, the_type)
        else:
            type_map[name] = the_type

    if isinstance(stmt, (frog_ast.Sample, frog_ast.Assignment)):
        if stmt.the_type is not None and isinstance(stmt.var, frog_ast.Variable):
            _put(stmt.var.name, stmt.the_type)
    elif isinstance(stmt, frog_ast.VariableDeclaration):
        _put(stmt.name, stmt.type)
    elif isinstance(stmt, frog_ast.GenericFor):
        _put(stmt.var_name, stmt.var_type)
        for inner in stmt.block.statements:
            _seed_type_map(inner, type_map, gap_fill)
    elif isinstance(stmt, frog_ast.IfStatement):
        for block in stmt.blocks:
            for inner in block.statements:
                _seed_type_map(inner, type_map, gap_fill=True)
