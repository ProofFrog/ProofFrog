"""Translate proof hop structure into EC lemmas.

Skeleton scope: interchangeability hops only. Each hop emits one
``equiv[...]`` lemma whose body is ``admit``. Reductions, assumptions,
and inductions are not supported.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ec_ast
from ... import frog_ast


@dataclass
class GameSideRef:
    """Reference to a concrete game side (what the lemma compares)."""

    ec_module_name: str
    oracle_name: str


class ProofTranslator:
    """Emit one admit-bodied equiv lemma per adjacent proof-step pair."""

    def __init__(self, primitive_name: str) -> None:
        self._primitive_name = primitive_name

    def translate_hops(
        self,
        game_refs: dict[str, GameSideRef],
        steps: list[frog_ast.ProofStep],
    ) -> list[ec_ast.Lemma]:
        """Produce one lemma per adjacent-step pair of interchangeability hops."""
        lemmas: list[ec_ast.Lemma] = []
        hop_index = 0
        for i in range(len(steps) - 1):
            step_a, step_b = steps[i], steps[i + 1]
            if not isinstance(step_a, frog_ast.Step) or not isinstance(
                step_b, frog_ast.Step
            ):
                raise NotImplementedError(
                    "Skeleton handles only simple interchangeability hops"
                )
            ref_a = _step_key(step_a)
            ref_b = _step_key(step_b)
            if ref_a not in game_refs or ref_b not in game_refs:
                raise ValueError(
                    f"Step references unknown game side: {ref_a} or {ref_b}"
                )
            left = game_refs[ref_a]
            right = game_refs[ref_b]
            lemmas.append(
                ec_ast.Lemma(
                    name=f"hop_{hop_index}",
                    module_args=[
                        ec_ast.ModuleParam("E", self._primitive_name),
                    ],
                    left=f"{left.ec_module_name}(E).{left.oracle_name}",
                    right=f"{right.ec_module_name}(E).{right.oracle_name}",
                    precondition="true",
                    postcondition="={res}",
                )
            )
            hop_index += 1
        return lemmas


def _step_key(step: frog_ast.Step) -> str:
    """Produce a stable key identifying which game side this step refers to.

    For ``OneTimeSecrecy(E).Real``, returns ``'Real'``.
    """
    challenger = step.challenger
    if isinstance(challenger, frog_ast.ConcreteGame):
        return challenger.which
    raise NotImplementedError(
        "Phase 1 skeleton only handles ConcreteGame steps (Game.Side)"
    )
