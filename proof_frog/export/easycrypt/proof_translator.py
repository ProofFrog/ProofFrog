"""Translate proof hop structure into EC lemmas.

Phase 2 scope: plain steps (``Game(E).Side``) and composed steps
(``Game(E).Side compose R(args)``). Every hop becomes one
``admit``-bodied equiv lemma. Induction is not supported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import ec_ast
from ... import frog_ast


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


def translate_hops(
    resolver: StepResolver,
    steps: list[frog_ast.ProofStep],
    body_for_hop: Callable[[int, frog_ast.Step, frog_ast.Step], list[str]],
) -> list[ec_ast.Lemma]:
    """Produce one equiv lemma per adjacent-step pair.

    ``body_for_hop(i, step_a, step_b)`` returns the list of tactic lines
    (ending with ``"qed."``) for hop ``i``. The body is wrapped by the
    lemma's ``proof. ... qed.`` framing in the pretty-printer.
    """
    lemmas: list[ec_ast.Lemma] = []
    for i in range(len(steps) - 1):
        a, b = steps[i], steps[i + 1]
        if not isinstance(a, frog_ast.Step) or not isinstance(b, frog_ast.Step):
            raise NotImplementedError(
                "Only simple Step entries are supported (no Induction)."
            )
        ra = resolver.resolve(a)
        rb = resolver.resolve(b)
        body = body_for_hop(i, a, b)
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
