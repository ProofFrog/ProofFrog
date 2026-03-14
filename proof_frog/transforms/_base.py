# pylint: disable=duplicate-code
# The fixed-point loop pattern is intentionally similar to proof_engine.py
# (which will be replaced by this module in Phase 2).
"""TransformPass ABC, PipelineContext, and pipeline runner."""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Symbol

from .. import frog_ast
from ..visitors import NameTypeMap

_MAX_FIXED_POINT_ITERATIONS = 200


@dataclass
class PipelineContext:
    """Read-only view of engine state needed by transforms."""

    variables: dict[str, Symbol | frog_ast.Expression]
    proof_let_types: NameTypeMap
    proof_namespace: frog_ast.Namespace
    subsets_pairs: list[tuple[frog_ast.Type, frog_ast.Type]]
    sort_game_fn: Optional[Callable[[frog_ast.Game], frog_ast.Game]] = None


class TransformPass(ABC):
    """A single canonicalization pass that can be applied to a Game AST."""

    name: str

    @abstractmethod
    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        """Apply this transformation pass. Return the (possibly new) game AST."""


def run_pipeline(
    game: frog_ast.Game,
    pipeline: list[TransformPass],
    ctx: PipelineContext,
    verbose: bool = False,
    max_iterations: int = _MAX_FIXED_POINT_ITERATIONS,
) -> frog_ast.Game:
    """Run transform passes in a fixed-point loop until convergence."""
    for _ in range(max_iterations):
        new_game = game
        for pass_ in pipeline:
            result = pass_.apply(new_game, ctx)
            if verbose and result != new_game:
                print(f"APPLIED {pass_.name}")
                print(result)
            new_game = result
        if new_game == game:
            break
        game = new_game
    else:
        warnings.warn(
            "Canonicalization did not converge within " f"{max_iterations} iterations",
            stacklevel=3,
        )
    return game


def run_standardization(
    game: frog_ast.Game,
    pipeline: list[TransformPass],
    ctx: PipelineContext,
) -> frog_ast.Game:
    """Run standardization passes once (no fixed-point loop)."""
    for pass_ in pipeline:
        game = pass_.apply(game, ctx)
    return game


# ---------------------------------------------------------------------------
# Traced / diagnostic pipeline runners
# ---------------------------------------------------------------------------


@dataclass
class IterationTrace:
    """Record of one fixed-point iteration."""

    iteration: int
    transforms_applied: list[str]


@dataclass
class PipelineTrace:
    """Full trace of a pipeline run."""

    iterations: list[IterationTrace]
    converged: bool


def run_pipeline_with_trace(
    game: frog_ast.Game,
    pipeline: list[TransformPass],
    ctx: PipelineContext,
    max_iterations: int = _MAX_FIXED_POINT_ITERATIONS,
) -> tuple[frog_ast.Game, PipelineTrace]:
    """Run transform passes in a fixed-point loop, recording which fired."""
    iterations: list[IterationTrace] = []
    converged = False
    for iteration in range(max_iterations):
        transforms_applied: list[str] = []
        new_game = game
        for pass_ in pipeline:
            before = new_game
            new_game = pass_.apply(new_game, ctx)
            if new_game != before:
                transforms_applied.append(pass_.name)
        if new_game == game:
            converged = True
            break
        iterations.append(
            IterationTrace(
                iteration=iteration + 1, transforms_applied=transforms_applied
            )
        )
        game = new_game
    if not converged:
        warnings.warn(
            "Canonicalization did not converge within " f"{max_iterations} iterations",
            stacklevel=3,
        )
    return game, PipelineTrace(iterations=iterations, converged=converged)


def run_pipeline_until(
    game: frog_ast.Game,
    core_pipeline: list[TransformPass],
    std_pipeline: list[TransformPass],
    ctx: PipelineContext,
    transform_name: str,
) -> tuple[frog_ast.Game, bool, list[str]]:
    """Apply transforms up to and including *transform_name* (first iteration).

    Returns ``(game_after, transform_changed_ast, available_names)``.
    """
    available_names = [p.name for p in core_pipeline] + [p.name for p in std_pipeline]

    if transform_name not in available_names:
        return game, False, available_names

    for pass_ in core_pipeline:
        before = game
        game = pass_.apply(game, ctx)
        if pass_.name == transform_name:
            return game, game != before, available_names

    for pass_ in std_pipeline:
        before = game
        game = pass_.apply(game, ctx)
        if pass_.name == transform_name:
            return game, game != before, available_names

    return game, False, available_names
