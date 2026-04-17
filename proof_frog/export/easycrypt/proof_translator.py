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
    ) -> None:
        self._module_names = module_name_by_concrete_game
        self._oracle_names = oracle_name_by_game_file
        self._primitive_name = primitive_name
        self._scheme_name = scheme_name
        self._oracle_params = oracle_params_by_game_file or {}
        self._reduction_params = oracle_params_by_reduction or {}

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
        key = (game_file_name, side)
        if key not in self._module_names:
            raise ValueError(
                f"Step references unknown game side: {game_file_name}.{side}"
            )
        game_module_expr = f"{self._module_names[key]}({self._scheme_name})"
        oracle = self._oracle_names[game_file_name]

        if step.reduction is None:
            return ResolvedStep(module_expr=game_module_expr, oracle_name=oracle)

        red = step.reduction
        module_expr = f"{red.name}({self._scheme_name}, {game_module_expr})"
        return ResolvedStep(module_expr=module_expr, oracle_name=oracle)


def translate_assumption_axioms(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    assumption_name: str,
    adversary_type_name: str,
    scheme_module_expr: str,
    real_wrapper_name: str,
    random_wrapper_name: str,
) -> list[ec_ast.EcTopDecl]:
    """Emit Style B advantage axiom + supporting declarations for an assumption.

    Returns a list ``[op eps_<name>, axiom eps_<name>_pos, axiom <name>_advantage]``.
    """
    eps_name = f"eps_{assumption_name}"
    advantage_name = f"{assumption_name}_advantage"
    pos_axiom_name = f"{eps_name}_pos"
    formula = (
        f"`| Pr[{real_wrapper_name}(A).main() @ &m : res]"
        f" - Pr[{random_wrapper_name}(A).main() @ &m : res] |"
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
                    name="A",
                    module_type=f"{adversary_type_name} {{-{scheme_module_expr}}}",
                )
            ],
            memory_args=["&m"],
        ),
    ]


def translate_inlining_hop_pr_lemma(
    hop_index: int,
    adversary_type_name: str,
    scheme_module_expr: str,
    left_wrapper_name: str,
    right_wrapper_name: str,
) -> ec_ast.ProbLemma:
    """Emit a ``hop_<i>_pr`` lemma for an inlining hop.

    The proof discharges ``Pr[L] = Pr[R]`` via ``byequiv`` over the
    existing ``hop_<i>`` equiv lemma.
    """
    statement = (
        f"Pr[{left_wrapper_name}(A).main() @ &m : res]"
        f" = Pr[{right_wrapper_name}(A).main() @ &m : res]"
    )
    body = [
        "byequiv => //; proc.",
        f"call (_: true); first by conseq hop_{hop_index}.",
        "auto.",
        "qed.",
    ]
    return ec_ast.ProbLemma(
        name=f"hop_{hop_index}_pr",
        module_args=[
            ec_ast.ModuleParam(
                name="A",
                module_type=f"{adversary_type_name} {{-{scheme_module_expr}}}",
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
) -> ec_ast.ProbLemma:
    """Emit a ``hop_<i>_pr`` lemma for an assumption hop.

    The proof rewrites each side to the corresponding assumption-game
    wrapper instantiated on the reduction-adversary lift, then applies
    the advantage axiom. When ``reverse_direction`` is true the hop goes
    Random->Real (opposite of the axiom) and we normalize via absolute-
    value symmetry before applying the axiom.
    """
    statement = (
        f"`| Pr[{left_wrapper_name}(A).main() @ &m : res]"
        f" - Pr[{right_wrapper_name}(A).main() @ &m : res] |"
        f" <= eps_{assumption_name}"
    )
    body = [
        f"have hL : Pr[{left_wrapper_name}(A).main() @ &m : res]",
        f"        = Pr[{left_assumption_wrapper}({reduction_adv_name}(A)).main() "
        f"@ &m : res]",
        "  by byequiv => //; proc; inline *; sim.",
        f"have hR : Pr[{right_wrapper_name}(A).main() @ &m : res]",
        f"        = Pr[{right_assumption_wrapper}({reduction_adv_name}(A)).main() "
        f"@ &m : res]",
        "  by byequiv => //; proc; inline *; sim.",
        "rewrite hL hR.",
    ]
    if reverse_direction:
        body.extend(
            [
                f"have H := {assumption_name}_advantage ({reduction_adv_name}(A)) &m.",
                "smt().",
            ]
        )
    else:
        body.append(
            f"apply ({assumption_name}_advantage ({reduction_adv_name}(A)) &m)."
        )
    body.append("qed.")
    return ec_ast.ProbLemma(
        name=f"hop_{hop_index}_pr",
        module_args=[
            ec_ast.ModuleParam(
                name="A",
                module_type=f"{adversary_type_name} {{-{scheme_module_expr}}}",
            )
        ],
        memory_args=["&m"],
        statement=statement,
        body=body,
    )


def translate_main_theorem(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    adversary_type_name: str,
    scheme_module_expr: str,
    first_wrapper_name: str,
    last_wrapper_name: str,
    hop_kinds: list[HopKind],
    assumption_names_by_hop: dict[int, str],
    n_hops: int,
) -> ec_ast.ProbLemma:
    """Emit the chained main theorem for a sequence of hops.

    The bound is the sum of ``eps_<name>`` for each assumption hop;
    inlining hops contribute zero. If there are no assumption hops, the
    statement is an equality (``Pr[L] = Pr[R]``) rather than a bound.
    """
    eps_terms: list[str] = []
    for i, kind in enumerate(hop_kinds):
        if kind is HopKind.ASSUMPTION:
            eps_terms.append(f"eps_{assumption_names_by_hop[i]}")

    have_lines = [f"have h{i} := hop_{i}_pr A &m." for i in range(n_hops)]
    if not eps_terms:
        statement = (
            f"Pr[{first_wrapper_name}(A).main() @ &m : res]"
            f" = Pr[{last_wrapper_name}(A).main() @ &m : res]"
        )
        body = [*have_lines, "smt().", "qed."]
    else:
        bound = " + ".join(eps_terms)
        statement = (
            f"`| Pr[{first_wrapper_name}(A).main() @ &m : res]"
            f" - Pr[{last_wrapper_name}(A).main() @ &m : res] |"
            f" <= {bound}"
        )
        pos_args = " ".join(
            f"eps_{name}_pos" for name in sorted(set(assumption_names_by_hop.values()))
        )
        body = [*have_lines, f"smt({pos_args}).", "qed."]

    return ec_ast.ProbLemma(
        name="main_theorem",
        module_args=[
            ec_ast.ModuleParam(
                name="A",
                module_type=f"{adversary_type_name} {{-{scheme_module_expr}}}",
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
