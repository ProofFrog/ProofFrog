"""Translate proof hop structure into EC lemmas.

Phase 2 scope: plain steps (``Game(E).Side``) and composed steps
(``Game(E).Side compose R(args)``). Every hop becomes one
``admit``-bodied equiv lemma. Induction is not supported.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Callable

from . import ec_ast
from ... import frog_ast


class HopKind(enum.Enum):
    INLINING = "inlining"
    ASSUMPTION = "assumption"


@dataclass
class ResolvedStep:
    """The EC module expression and oracle name referenced by a step."""

    module_expr: str
    oracle_name: str


class StepResolver:
    """Resolve a FrogLang proof step to its EC module expression.

    Lemmas are specialized to the concrete scheme (passed as
    ``scheme_name``) rather than parameterized over an abstract primitive
    module. This is required because the engine's canonicalization
    inlines scheme methods, and EC-level tactics (``rnd``, ``auto``)
    cannot reason about abstract primitive calls.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        module_name_by_concrete_game: dict[tuple[str, str], str],
        oracle_name_by_game_file: dict[str, str],
        primitive_name: str,
        scheme_name: str,
        oracle_params_by_game_file: dict[str, list[str]] | None = None,
        oracle_params_by_reduction: dict[str, list[str]] | None = None,
        instance_module_expr_by_let_name: dict[str, str] | None = None,
        module_name_by_instance_game: dict[tuple[str, str, str], str] | None = None,
    ) -> None:
        self._module_names = module_name_by_concrete_game
        self._oracle_names = oracle_name_by_game_file
        self._primitive_name = primitive_name
        self._scheme_name = scheme_name
        self._oracle_params = oracle_params_by_game_file or {}
        self._reduction_params = oracle_params_by_reduction or {}
        # Multi-instance mode: when these are provided, ``resolve`` uses
        # per-instance clone-qualified module names and instance module
        # expressions.
        self._instance_module_expr = instance_module_expr_by_let_name or {}
        self._module_name_by_instance_game = module_name_by_instance_game or {}

    def precondition_for(self, step: frog_ast.Step) -> str:
        """Return the EC precondition: ``={arg1, arg2, ...}`` or ``true``.

        A composed step ``Game.Side compose R`` exposes the reduction's
        outer signature; use the reduction's params. A plain step
        ``Game.Side`` exposes the game's own signature.
        """
        if step.reduction is not None:
            params = self._reduction_params.get(step.reduction.name, [])
        else:
            concrete = step.challenger
            if not isinstance(concrete, frog_ast.ConcreteGame):
                return "true"
            params = self._oracle_params.get(concrete.game.name, [])
        if not params:
            return "true"
        return "={" + ", ".join(params) + "}"

    @property
    def primitive_name(self) -> str:
        return self._primitive_name

    @property
    def scheme_name(self) -> str:
        return self._scheme_name

    def resolve(self, step: frog_ast.Step) -> ResolvedStep:
        concrete = step.challenger
        if not isinstance(concrete, frog_ast.ConcreteGame):
            raise NotImplementedError(
                f"Only ConcreteGame steps are supported; got {type(concrete).__name__}"
            )
        game_file_name = concrete.game.name
        side = concrete.which
        oracle = self._oracle_names[game_file_name]

        if self._instance_module_expr:
            # Multi-instance mode.
            if not concrete.game.args or not isinstance(
                concrete.game.args[0], frog_ast.Variable
            ):
                raise ValueError(
                    f"Step's challenger {concrete.game.name} has no instance argument."
                )
            inst_let_name = concrete.game.args[0].name
            inst_expr = self._instance_module_expr[inst_let_name]
            key3 = (inst_let_name, game_file_name, side)
            if key3 not in self._module_name_by_instance_game:
                raise ValueError(
                    f"Step references unknown instance/game side: "
                    f"{inst_let_name}/{game_file_name}.{side}"
                )
            module_name = self._module_name_by_instance_game[key3]
            game_module_expr = f"{module_name}({inst_expr})"
            if step.reduction is None:
                return ResolvedStep(module_expr=game_module_expr, oracle_name=oracle)
            red = step.reduction
            red_arg_exprs: list[str] = []
            for a in red.args:
                if isinstance(a, frog_ast.Variable):
                    red_arg_exprs.append(self._instance_module_expr.get(a.name, a.name))
                else:
                    red_arg_exprs.append(str(a))
            module_expr = f"{red.name}({', '.join(red_arg_exprs)}, {game_module_expr})"
            return ResolvedStep(module_expr=module_expr, oracle_name=oracle)

        key = (game_file_name, side)
        if key not in self._module_names:
            raise ValueError(
                f"Step references unknown game side: {game_file_name}.{side}"
            )
        game_module_expr = f"{self._module_names[key]}({self._scheme_name})"

        if step.reduction is None:
            return ResolvedStep(module_expr=game_module_expr, oracle_name=oracle)

        red = step.reduction
        module_expr = f"{red.name}({self._scheme_name}, {game_module_expr})"
        return ResolvedStep(module_expr=module_expr, oracle_name=oracle)


def translate_assumption_axioms_theory(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    assumption_name: str,
    adversary_type_name: str,
    scheme_type_name: str,
    scheme_param_name: str,
    real_wrapper_name: str,
    random_wrapper_name: str,
) -> list[ec_ast.EcTopDecl]:
    """Emit Style B advantage axiom declarations for inside-theory use.

    The advantage axiom quantifies over the abstract scheme instance
    (``<scheme_param_name> <: <scheme_type_name>``) and the adversary, so
    that after the theory is cloned the axiom applies to any concrete
    scheme the clone binds. The scheme parameter is declared first so the
    adversary's ``{-<scheme_param_name>}`` separation restriction can
    reference it.

    Returns ``[op eps_<name>, axiom eps_<name>_pos, axiom <name>_advantage]``.
    """
    eps_name = f"eps_{assumption_name}"
    advantage_name = f"{assumption_name}_advantage"
    pos_axiom_name = f"{eps_name}_pos"
    formula = (
        f"`| Pr[{real_wrapper_name}({scheme_param_name}, A).main() @ &m : res]"
        f" - Pr[{random_wrapper_name}({scheme_param_name}, A).main() @ &m : res] |"
        f" <= {eps_name}"
    )
    return [
        ec_ast.OpDecl(name=eps_name, signature="real"),
        ec_ast.Axiom(
            name=pos_axiom_name,
            formula=f"0%r <= {eps_name}",
        ),
        ec_ast.Axiom(
            name=advantage_name,
            formula=formula,
            module_args=[
                ec_ast.ModuleParam(
                    name=scheme_param_name, module_type=scheme_type_name
                ),
                ec_ast.ModuleParam(
                    name="A",
                    module_type=(f"{adversary_type_name} {{-{scheme_param_name}}}"),
                ),
            ],
            memory_args=["&m"],
        ),
    ]


def _wrap_apply(wrapper: str, extra_args: list[str] | None) -> str:
    """Return ``Wrapper(E1, E2, A)`` when extra args present, else ``Wrapper(A)``."""
    if extra_args:
        return f"{wrapper}({', '.join(extra_args)}, A)"
    return f"{wrapper}(A)"


def translate_inlining_hop_pr_lemma(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    hop_index: int,
    adversary_type_name: str,
    scheme_module_expr: str,
    left_wrapper_name: str,
    right_wrapper_name: str,
    scheme_footprint: str | None = None,
    wrapper_extra_args: list[str] | None = None,
) -> ec_ast.ProbLemma:
    """Emit a ``hop_<i>_pr`` lemma for an inlining hop.

    The proof discharges ``Pr[L] = Pr[R]`` via ``byequiv`` over the
    existing ``hop_<i>`` equiv lemma.
    """
    left_app = _wrap_apply(left_wrapper_name, wrapper_extra_args)
    right_app = _wrap_apply(right_wrapper_name, wrapper_extra_args)
    statement = (
        f"Pr[{left_app}.main() @ &m : res]" f" = Pr[{right_app}.main() @ &m : res]"
    )
    body = [
        "byequiv => //; proc.",
        f"call (_: true); first by conseq hop_{hop_index}.",
        "auto.",
        "qed.",
    ]
    footprint = (
        scheme_footprint if scheme_footprint is not None else f"-{scheme_module_expr}"
    )
    return ec_ast.ProbLemma(
        name=f"hop_{hop_index}_pr",
        module_args=[
            ec_ast.ModuleParam(
                name="A",
                module_type=f"{adversary_type_name} {{{footprint}}}",
            )
        ],
        memory_args=["&m"],
        statement=statement,
        body=body,
    )


def translate_assumption_hop_pr_lemma(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    hop_index: int,
    adversary_type_name: str,
    scheme_module_expr: str,
    left_wrapper_name: str,
    right_wrapper_name: str,
    assumption_name: str,
    reduction_adv_name: str,
    left_assumption_wrapper: str,
    right_assumption_wrapper: str,
    reverse_direction: bool,
    clone_alias: str | None = None,
    scheme_footprint: str | None = None,
    reduction_adv_extra_args: list[str] | None = None,
    wrapper_extra_args: list[str] | None = None,
) -> ec_ast.ProbLemma:
    """Emit a ``hop_<i>_pr`` lemma for an assumption hop.

    The proof rewrites each side to the corresponding assumption-game
    wrapper instantiated on the reduction-adversary lift, then applies
    the advantage axiom. When ``reverse_direction`` is true the hop goes
    Random->Real (opposite of the axiom) and we normalize via absolute-
    value symmetry before applying the axiom.

    ``reduction_adv_extra_args`` supplies extra module arguments that
    the reduction-adversary wrapper takes before ``A`` (e.g. declared
    module instances ``E1, E2``).
    """
    prefix = f"{clone_alias}." if clone_alias else ""
    eps_ref = f"{prefix}eps_{assumption_name}"
    advantage_ref = f"{prefix}{assumption_name}_advantage"
    left_wrapper_ref = f"{prefix}{left_assumption_wrapper}"
    right_wrapper_ref = f"{prefix}{right_assumption_wrapper}"
    extra = ", ".join(reduction_adv_extra_args) if reduction_adv_extra_args else ""
    adv_applied = (
        f"{reduction_adv_name}({extra}, A)" if extra else f"{reduction_adv_name}(A)"
    )
    left_app = _wrap_apply(left_wrapper_name, wrapper_extra_args)
    right_app = _wrap_apply(right_wrapper_name, wrapper_extra_args)
    statement = (
        f"`| Pr[{left_app}.main() @ &m : res]"
        f" - Pr[{right_app}.main() @ &m : res] |"
        f" <= {eps_ref}"
    )
    if wrapper_extra_args:
        body = [
            "admit.",
            f"(* multi-module assumption hop: {left_wrapper_name} -> "
            f"{right_wrapper_name} via {advantage_ref} *)",
        ]
    else:
        body = [
            f"have hL : Pr[{left_app}.main() @ &m : res]",
            f"        = Pr[{left_wrapper_ref}({scheme_module_expr}, "
            f"{adv_applied}).main() @ &m : res]",
            "  by byequiv => //; proc; inline *; sim.",
            f"have hR : Pr[{right_app}.main() @ &m : res]",
            f"        = Pr[{right_wrapper_ref}({scheme_module_expr}, "
            f"{adv_applied}).main() @ &m : res]",
            "  by byequiv => //; proc; inline *; sim.",
            "rewrite hL hR.",
        ]
        if reverse_direction:
            body.extend(
                [
                    f"have H := {advantage_ref} {scheme_module_expr} "
                    f"({adv_applied}) &m.",
                    "smt().",
                ]
            )
        else:
            body.append(
                f"apply ({advantage_ref} {scheme_module_expr} " f"({adv_applied}) &m)."
            )
    body.append("qed.")
    footprint = (
        scheme_footprint if scheme_footprint is not None else f"-{scheme_module_expr}"
    )
    return ec_ast.ProbLemma(
        name=f"hop_{hop_index}_pr",
        module_args=[
            ec_ast.ModuleParam(
                name="A",
                module_type=f"{adversary_type_name} {{{footprint}}}",
            )
        ],
        memory_args=["&m"],
        statement=statement,
        body=body,
    )


def translate_main_theorem(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    adversary_type_name: str,
    scheme_module_expr: str,
    first_wrapper_name: str,
    last_wrapper_name: str,
    hop_kinds: list[HopKind],
    assumption_names_by_hop: dict[int, str],
    n_hops: int,
    clone_alias: str | None = None,
    assumption_clone_by_hop: dict[int, str] | None = None,
    scheme_footprint: str | None = None,
    wrapper_extra_args: list[str] | None = None,
) -> ec_ast.ProbLemma:
    """Emit the chained main theorem for a sequence of hops.

    The bound is the sum of ``eps_<name>`` for each assumption hop;
    inlining hops contribute zero. If there are no assumption hops, the
    statement is an equality (``Pr[L] = Pr[R]``) rather than a bound.
    """
    default_prefix = f"{clone_alias}." if clone_alias else ""
    per_hop_clones = assumption_clone_by_hop or {}

    def _prefix_for(hop_index: int) -> str:
        override = per_hop_clones.get(hop_index)
        if override:
            return f"{override}."
        return default_prefix

    eps_terms: list[str] = []
    for i, kind in enumerate(hop_kinds):
        if kind is HopKind.ASSUMPTION:
            eps_terms.append(f"{_prefix_for(i)}eps_{assumption_names_by_hop[i]}")

    first_app = _wrap_apply(first_wrapper_name, wrapper_extra_args)
    last_app = _wrap_apply(last_wrapper_name, wrapper_extra_args)
    have_lines = [f"have h{i} := hop_{i}_pr A &m." for i in range(n_hops)]
    if not eps_terms:
        statement = (
            f"Pr[{first_app}.main() @ &m : res]" f" = Pr[{last_app}.main() @ &m : res]"
        )
        body = [*have_lines, "smt().", "qed."]
    else:
        bound = " + ".join(eps_terms)
        statement = (
            f"`| Pr[{first_app}.main() @ &m : res]"
            f" - Pr[{last_app}.main() @ &m : res] |"
            f" <= {bound}"
        )
        pos_args_set = {
            f"{_prefix_for(i)}eps_{assumption_names_by_hop[i]}_pos"
            for i, kind in enumerate(hop_kinds)
            if kind is HopKind.ASSUMPTION
        }
        pos_args = " ".join(sorted(pos_args_set))
        body = [*have_lines, f"smt({pos_args}).", "qed."]

    footprint = (
        scheme_footprint if scheme_footprint is not None else f"-{scheme_module_expr}"
    )
    return ec_ast.ProbLemma(
        name="main_theorem",
        module_args=[
            ec_ast.ModuleParam(
                name="A",
                module_type=f"{adversary_type_name} {{{footprint}}}",
            )
        ],
        memory_args=["&m"],
        statement=statement,
        body=body,
    )


def translate_hops(
    resolver: StepResolver,
    steps: list[frog_ast.ProofStep],
    body_for_hop: Callable[[int, frog_ast.Step, frog_ast.Step], list[str] | None],
) -> list[ec_ast.Lemma]:
    """Produce one equiv lemma per adjacent-step pair.

    ``body_for_hop(i, step_a, step_b)`` returns the list of tactic lines
    (ending with ``"qed."``) for hop ``i``, or ``None`` to skip the
    equiv lemma entirely for that hop (e.g. for assumption hops whose
    two sides are genuinely non-equivalent).
    """
    lemmas: list[ec_ast.Lemma] = []
    for i in range(len(steps) - 1):
        a, b = steps[i], steps[i + 1]
        if not isinstance(a, frog_ast.Step) or not isinstance(b, frog_ast.Step):
            raise NotImplementedError(
                "Only simple Step entries are supported (no Induction)."
            )
        body = body_for_hop(i, a, b)
        if body is None:
            continue
        ra = resolver.resolve(a)
        rb = resolver.resolve(b)
        lemmas.append(
            ec_ast.Lemma(
                name=f"hop_{i}",
                module_args=[],
                left=f"{ra.module_expr}.{ra.oracle_name}",
                right=f"{rb.module_expr}.{rb.oracle_name}",
                precondition=resolver.precondition_for(a),
                postcondition="={res}",
                body=body,
            )
        )
    return lemmas
