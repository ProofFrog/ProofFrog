"""`run_pipeline` does not re-apply a pass to a game it already declined on.

The skip is only sound while the pass would see exactly what it saw before:
the same game object and the same ``ctx.pinned_fields``.
"""

import copy

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import (
    PipelineContext,
    TransformPass,
    run_pipeline,
    same_structure,
)
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _game(returned: int = 1) -> frog_ast.Game:
    return frog_parser.parse_game(f"Game G() {{ Int f() {{ return {returned}; }} }}")


class _Counting(TransformPass):
    """Records the games it is applied to; subclasses decide what to return."""

    name = "Counting"

    def __init__(self) -> None:
        self.seen: list[frog_ast.Game] = []

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        self.seen.append(game)
        return self._apply(game, ctx)

    def _apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return game


class _FreshCopy(_Counting):
    """Declines, but hands back an equal copy instead of its input."""

    def _apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return copy.deepcopy(game)


class _ReplaceOnce(_Counting):
    """Rewrites `return 1;` to `return 2;`, then declines."""

    def _apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _game(2) if game == _game(1) else game


class _PinOnFirstCall(_Counting):
    def _apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        if len(self.seen) == 1:
            ctx.pinned_fields.add("pinned")
        return game


class _FireWhenPinned(_Counting):
    """Declines until some field is pinned, then rewrites `return 2;` once."""

    def _apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        if ctx.pinned_fields and game == _game(2):
            return _game(3)
        return game


def test_declining_pass_runs_once_on_a_converged_game() -> None:
    first, second = _Counting(), _Counting()
    game = _game()
    assert run_pipeline(game, [first, second], _ctx()) is game
    assert len(first.seen) == 1
    assert len(second.seen) == 1


def test_equal_copy_counts_as_declining_and_keeps_the_input_object() -> None:
    copier, after = _FreshCopy(), _Counting()
    game = _game()
    assert run_pipeline(game, [copier, after], _ctx()) is game
    assert len(copier.seen) == 1
    # The later pass was handed the original object, not the copy.
    assert after.seen == [game] and after.seen[0] is game


def test_pass_is_reapplied_after_another_pass_changes_the_game() -> None:
    before, rewriter, after = _Counting(), _ReplaceOnce(), _Counting()
    result = run_pipeline(_game(1), [before, rewriter, after], _ctx())
    assert result == _game(2)
    # `before` declined on the original game, then must see the rewritten
    # one; `after` and `rewriter` already declined on it and are skipped.
    assert [g == _game(2) for g in before.seen] == [False, True]
    assert len(rewriter.seen) == 2
    assert len(after.seen) == 1


def test_pass_is_reapplied_when_pinned_fields_change() -> None:
    # Iteration 1: `rewriter` produces `return 2;`, `waiter` declines on it
    # (nothing is pinned yet), `pinner` pins a field. Iteration 2 hands
    # `waiter` that same game object; only the pinned-field check makes the
    # runner apply it again, and it then fires.
    rewriter, waiter, pinner = _ReplaceOnce(), _FireWhenPinned(), _PinOnFirstCall()
    ctx = _ctx()
    result = run_pipeline(_game(1), [rewriter, waiter, pinner], ctx)
    assert ctx.pinned_fields == {"pinned"}
    assert result == _game(3)


def test_pass_that_pins_while_declining_is_applied_again() -> None:
    rewriter, pinner = _ReplaceOnce(), _PinOnFirstCall()
    assert run_pipeline(_game(1), [rewriter, pinner], _ctx()) == _game(2)
    # Its first application changed the context it reads, so that result
    # says nothing about a second application to the same game.
    assert len(pinner.seen) == 2


# --- "unchanged" is exact structure, not `==` --------------------------


def _tuple_game(value: frog_ast.Expression) -> frog_ast.Game:
    game = frog_parser.parse_game("Game G() { Void f() { [Int, Int] t = [1, 2]; } }")
    game.methods[0].block.statements[0].value = value  # type: ignore[union-attr]
    return game


_ELEMENTS = [frog_ast.Integer(1), frog_ast.Integer(2)]


class _ProductToTuple(_Counting):
    """Like Normalize Product-Literal Tuples: a rewrite `==` cannot see."""

    def _apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _tuple_game(frog_ast.Tuple(list(_ELEMENTS)))


def test_same_structure_is_stricter_than_equality() -> None:
    as_product = _tuple_game(frog_ast.ProductType(list(_ELEMENTS)))  # type: ignore[arg-type]
    as_tuple = _tuple_game(frog_ast.Tuple(list(_ELEMENTS)))
    assert as_product == as_tuple
    assert not same_structure(as_product, as_tuple)
    assert same_structure(as_tuple, copy.deepcopy(as_tuple))
    assert same_structure(_game(1), _game(1))
    assert not same_structure(_game(1), _game(2))
    assert not same_structure(frog_ast.Integer(1), frog_ast.Boolean(True))


def test_a_rewrite_invisible_to_equality_still_reaches_later_passes() -> None:
    # Regression: treating an `==`-equal output as "declined" dropped the
    # ProductType -> Tuple rewrite, and a later pass that needs the Tuple
    # (FoldTupleLiteralIndexing) stopped firing, failing real proofs.
    rewriter, after = _ProductToTuple(), _Counting()
    start = _tuple_game(frog_ast.ProductType(list(_ELEMENTS)))  # type: ignore[arg-type]
    run_pipeline(start, [rewriter, after], _ctx())
    value = after.seen[0].methods[0].block.statements[0].value  # type: ignore[union-attr]
    assert type(value) is frog_ast.Tuple
