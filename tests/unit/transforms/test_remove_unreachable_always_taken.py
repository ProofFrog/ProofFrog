"""Remove Unreachable replaces an if-statement that is always taken (F-413).

When the path facts at an if with one condition and no else imply its
condition (the earlier returning tests failed and together with this one
cover every execution, or an earlier assignment fixes it), and the condition
makes no call, the if is replaced by its block. Before, the pass dropped the
unreachable statements after a covering run of returning ifs but kept the
last if of the run, so the method appeared to run off its end, and a side
written with a plain return did not meet it.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext, run_pipeline
from proof_frog.transforms.control_flow import (
    RemoveUnreachable,
    RemoveUnreachableTransformer,
)
from proof_frog.transforms.pipelines import CORE_PIPELINE
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _method(source: str) -> frog_ast.Method:
    method = frog_parser.parse_method(source)
    return RemoveUnreachableTransformer(method).transform(method)


def _assert_method(source: str, expected: str) -> None:
    assert _method(source) == frog_parser.parse_method(expected)


def _apply(source: str) -> frog_ast.Game:
    return RemoveUnreachable().apply(frog_parser.parse_game(source), _ctx())


def _assert_game_unchanged(source: str) -> None:
    assert _apply(source) == frog_parser.parse_game(source)


# ---------------------------------------------------------------------------
# The if is replaced by its block
# ---------------------------------------------------------------------------


def test_complement_after_return_becomes_its_block() -> None:
    # The canonical Decrypt shape: the unreachable final return was dropped,
    # and the always-true second test stayed.
    _assert_method(
        """
        Int f(Int x, Set<Int> S) {
            if (x in S) {
                return 1;
            }
            if (!(x in S)) {
                return 1;
            }
            return x;
        }
        """,
        """
        Int f(Int x, Set<Int> S) {
            if (x in S) {
                return 1;
            }
            return 1;
        }
        """,
    )


def test_cover_meets_a_single_return_in_core_pipeline() -> None:
    covered = """
    Game G() {
        Set<Int> S;
        Int Enc(Int m) {
            S = S union {m};
            return m;
        }
        Int? Dec(Int c) {
            if (c in S) {
                return None;
            }
            if (!(c in S)) {
                return None;
            }
            return c;
        }
    }
    """
    single = """
    Game G() {
        Set<Int> S;
        Int Enc(Int m) {
            S = S union {m};
            return m;
        }
        Int? Dec(Int c) {
            return None;
        }
    }
    """
    left = run_pipeline(frog_parser.parse_game(covered), CORE_PIPELINE, _ctx())
    right = run_pipeline(frog_parser.parse_game(single), CORE_PIPELINE, _ctx())
    assert left == right
    assert "if" not in str(left.get_method("Dec"))


def test_condition_implied_by_earlier_assignment() -> None:
    # A block that does not return keeps the statements after the if.
    _assert_method(
        """
        Int f(Int x) {
            Int y = 5;
            if (y == 5) {
                x = x + 1;
            }
            return x;
        }
        """,
        """
        Int f(Int x) {
            Int y = 5;
            x = x + 1;
            return x;
        }
        """,
    )


def test_condition_implied_inside_nested_block() -> None:
    # The inner block inherits the fact that `b` was false.
    _assert_method(
        """
        Int f(Bool b, Bool c, Int x) {
            if (b) {
                return 1;
            }
            if (c) {
                if (!b) {
                    x = 1;
                }
            }
            return x;
        }
        """,
        """
        Int f(Bool b, Bool c, Int x) {
            if (b) {
                return 1;
            }
            if (c) {
                x = 1;
            }
            return x;
        }
        """,
    )


def test_returning_block_drops_the_statements_after_it() -> None:
    # The statements after the if are unreachable once its block returns,
    # so its local `y` clashing with a later one does not matter.
    _assert_method(
        """
        Int f(Bool b) {
            if (b) {
                return 1;
            }
            if (!b) {
                Int y = 2;
                return y;
            }
            Int y = 3;
            return y;
        }
        """,
        """
        Int f(Bool b) {
            if (b) {
                return 1;
            }
            Int y = 2;
            return y;
        }
        """,
    )


def test_block_local_not_named_later_is_moved_out() -> None:
    game = _apply("""
        Game G() {
            Int c;
            Int Test(Bool b) {
                if (b) {
                    return 1;
                }
                if (!b) {
                    Int t = 2;
                    c = t;
                }
                return c;
            }
        }
        """)
    assert game == frog_parser.parse_game("""
        Game G() {
            Int c;
            Int Test(Bool b) {
                if (b) {
                    return 1;
                }
                Int t = 2;
                c = t;
                return c;
            }
        }
        """)


# ---------------------------------------------------------------------------
# The if is kept (the near misses are tested in test_near_misses.py)
# ---------------------------------------------------------------------------


def test_condition_with_call_kept() -> None:
    # Distinguisher if replaced: F.Get need not be deterministic, and its
    # evaluation may have an effect, which removing the test would drop.
    _assert_game_unchanged("""
        Game G(F f) {
            Set<Int> S;
            Int Test(Int x) {
                if (x in S) {
                    return 1;
                }
                if (!(x in S) || F.Get(x) in S) {
                    return 2;
                }
                return 3;
            }
        }
        """)


def test_write_between_tests_kept() -> None:
    # Distinguisher if replaced: after S gains x, !(x in S) is false, so
    # Test(x) for a fresh x returns 3, not 2.
    _assert_game_unchanged("""
        Game G() {
            Set<Int> S;
            Int Test(Int x) {
                if (x in S) {
                    return 1;
                }
                S = S union {x};
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
        }
        """)


def test_write_in_kept_branch_kept() -> None:
    # Distinguisher if replaced: when c holds, S becomes T, which need not
    # hold x, so the second test may fail.
    _assert_game_unchanged("""
        Game G() {
            Set<Int> S;
            Set<Int> T;
            Int Test(Int x, Bool c) {
                if (x in S) {
                    return 1;
                }
                if (c) {
                    S = T;
                }
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
        }
        """)


def test_condition_not_implied_kept() -> None:
    _assert_game_unchanged("""
        Game G() {
            Set<Int> S;
            Set<Int> T;
            Int Test(Int x) {
                if (x in S) {
                    return 1;
                }
                if (!(x in T)) {
                    return 2;
                }
                return 3;
            }
        }
        """)


def test_if_with_else_kept() -> None:
    _assert_game_unchanged("""
        Game G() {
            Int c;
            Int Test(Bool b) {
                if (b) {
                    return 1;
                }
                if (!b) {
                    c = 1;
                } else {
                    c = 2;
                }
                return c;
            }
        }
        """)


def test_block_local_named_later_kept() -> None:
    # Distinguisher if moved out: `return y;` would read the block's local
    # (2) instead of the field y.
    _assert_game_unchanged("""
        Game G() {
            Int c;
            Int y;
            Int Test(Bool b) {
                if (b) {
                    return 1;
                }
                if (!b) {
                    Int y = 2;
                    c = y;
                }
                return y;
            }
        }
        """)
