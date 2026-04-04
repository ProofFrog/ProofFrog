"""Tests for the ApplyAssumptions / SimplifyRangeTransformer transform.

Focuses on soundness: ensures Z3 timeouts (unknown results) are handled
correctly and do not cause incorrect simplifications.
"""

import z3

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.assumptions import SimplifyRangeTransformer
from proof_frog.visitors import NameTypeMap


def _make_assumption_and_game(
    assumption_str: str, game_str: str
) -> tuple[frog_ast.BinaryOperation | frog_ast.UnaryOperation, frog_ast.Game]:
    """Parse an assumption expression and a game from strings."""
    assumption_method = frog_parser.parse_method(f"""
        Bool __assume() {{
            return {assumption_str};
        }}
    """)
    assumption_expr = assumption_method.block.statements[0].expression
    game = frog_parser.parse_game(game_str)
    return assumption_expr, game


def _get_first_condition(game: frog_ast.Game) -> frog_ast.Expression:
    """Extract the first if-statement's condition from a game's first method."""
    if_stmt = game.methods[0].block.statements[0]
    assert isinstance(if_stmt, frog_ast.IfStatement)
    return if_stmt.conditions[0]


class TestContradictionCheckSoundness:
    """The contradiction check must only replace with false when Z3
    definitively returns UNSAT, not on timeout (unknown)."""

    def test_z3_unsat_replaces_with_false(self) -> None:
        """When Z3 says assumption AND condition is UNSAT, condition -> false."""
        assumption, game = _make_assumption_and_game(
            "n > 10",
            """
            Game G() {
                Int n;
                Bool Query() {
                    if (n < 5) {
                        return true;
                    }
                    return false;
                }
            }
            """,
        )
        result = SimplifyRangeTransformer(
            NameTypeMap(), game, assumption
        ).transform(game)
        cond = _get_first_condition(result)
        assert isinstance(cond, frog_ast.Boolean)
        assert cond.bool is False

    def test_z3_sat_does_not_replace(self) -> None:
        """When assumption AND condition is SAT and assumption does not imply
        condition, condition stays unchanged."""
        # n > 10 does NOT imply n < 20 (n could be 25), and n>10 AND n<20 is SAT
        assumption, game = _make_assumption_and_game(
            "n > 10",
            """
            Game G() {
                Int n;
                Bool Query() {
                    if (n < 20) {
                        return true;
                    }
                    return false;
                }
            }
            """,
        )
        result = SimplifyRangeTransformer(
            NameTypeMap(), game, assumption
        ).transform(game)
        cond = _get_first_condition(result)
        assert isinstance(cond, frog_ast.BinaryOperation)

    def test_z3_implication_replaces_with_true(self) -> None:
        """When Z3 proves assumption implies condition, condition -> true."""
        # n > 10 implies n > 5
        assumption, game = _make_assumption_and_game(
            "n > 10",
            """
            Game G() {
                Int n;
                Bool Query() {
                    if (n > 5) {
                        return true;
                    }
                    return false;
                }
            }
            """,
        )
        result = SimplifyRangeTransformer(
            NameTypeMap(), game, assumption
        ).transform(game)
        cond = _get_first_condition(result)
        assert isinstance(cond, frog_ast.Boolean)
        assert cond.bool is True

    def test_z3_unknown_does_not_replace_with_false(self) -> None:
        """SOUNDNESS: When Z3 returns unknown (timeout), condition must NOT
        be replaced with false. z3.unknown != z3.sat is True, so the old code
        incorrectly triggers the false replacement."""
        assumption, game = _make_assumption_and_game(
            "n > 10",
            """
            Game G() {
                Int n;
                Bool Query() {
                    if (n < 20) {
                        return true;
                    }
                    return false;
                }
            }
            """,
        )
        transformer = SimplifyRangeTransformer(NameTypeMap(), game, assumption)

        # Patch the solver's check method to return unknown (simulating timeout)
        def fake_check() -> z3.CheckSatResult:
            return z3.unknown

        transformer.solver.check = fake_check  # type: ignore[assignment]
        result = transformer.transform(game)

        cond = _get_first_condition(result)
        # CRITICAL: condition must NOT be Boolean(False)
        assert not (
            isinstance(cond, frog_ast.Boolean) and cond.bool is False
        ), (
            "Soundness bug: Z3 timeout (unknown) caused condition to be "
            "replaced with false"
        )

    def test_exact_match_replaces_with_true(self) -> None:
        """When the condition is structurally identical to the assumption,
        it should be replaced with true (short-circuit path)."""
        assumption, game = _make_assumption_and_game(
            "n > 10",
            """
            Game G() {
                Int n;
                Bool Query() {
                    if (n > 10) {
                        return true;
                    }
                    return false;
                }
            }
            """,
        )
        result = SimplifyRangeTransformer(
            NameTypeMap(), game, assumption
        ).transform(game)
        cond = _get_first_condition(result)
        assert isinstance(cond, frog_ast.Boolean)
        assert cond.bool is True
