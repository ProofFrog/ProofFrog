"""Translate proof hop structure into EC lemmas.

Phase 2 scope: plain steps (``Game(E).Side``) and composed steps
(``Game(E).Side compose R(args)``). Every hop becomes one
``admit``-bodied equiv lemma. Induction is not supported.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ec_ast
from ... import frog_ast


@dataclass
class ResolvedStep:
    """The EC module expression and oracle name referenced by a step."""

    module_expr: str
    oracle_name: str


class StepResolver:
    """Resolve a FrogLang proof step to its EC module expression."""

    def __init__(
        self,
        module_name_by_concrete_game: dict[tuple[str, str], str],
        oracle_name_by_game_file: dict[str, str],
        primitive_name: str,
    ) -> None:
        self._module_names = module_name_by_concrete_game
        self._oracle_names = oracle_name_by_game_file
        self._primitive_name = primitive_name

    @property
    def primitive_name(self) -> str:
        return self._primitive_name

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
        game_module_expr = f"{self._module_names[key]}(E)"
        oracle = self._oracle_names[game_file_name]

        if step.reduction is None:
            return ResolvedStep(module_expr=game_module_expr, oracle_name=oracle)

        red = step.reduction
        module_expr = f"{red.name}(E, {game_module_expr})"
        return ResolvedStep(module_expr=module_expr, oracle_name=oracle)


def translate_hops(
    resolver: StepResolver,
    steps: list[frog_ast.ProofStep],
) -> list[ec_ast.Lemma]:
    """Produce one admit-bodied equiv lemma per adjacent-step pair."""
    lemmas: list[ec_ast.Lemma] = []
    for i in range(len(steps) - 1):
        a, b = steps[i], steps[i + 1]
        if not isinstance(a, frog_ast.Step) or not isinstance(b, frog_ast.Step):
            raise NotImplementedError(
                "Only simple Step entries are supported (no Induction)."
            )
        ra = resolver.resolve(a)
        rb = resolver.resolve(b)
        lemmas.append(
            ec_ast.Lemma(
                name=f"hop_{i}",
                module_args=[ec_ast.ModuleParam("E", resolver.primitive_name)],
                left=f"{ra.module_expr}.{ra.oracle_name}",
                right=f"{rb.module_expr}.{rb.oracle_name}",
                precondition="true",
                postcondition="={res}",
            )
        )
    return lemmas
