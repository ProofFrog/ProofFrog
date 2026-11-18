"""Tests for GuardedTrueReturnToCondition.

The pass folds ``if (C) { S; return true; } return false;`` into
``if (C) { S; } return C;`` (and ``if (C) { return true; } return false;``
into ``return C;``) when ``C`` makes no call and ``S`` writes and rebinds no
variable ``C`` reads.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext, run_pipeline
from proof_frog.transforms.control_flow import GuardedTrueReturnToCondition
from proof_frog.transforms.pipelines import CORE_PIPELINE
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str) -> frog_ast.Game:
    return GuardedTrueReturnToCondition().apply(frog_parser.parse_game(source), _ctx())


def _assert_unchanged(source: str) -> None:
    assert _apply(source) == frog_parser.parse_game(source)


# ---------------------------------------------------------------------------
# The pass fires
# ---------------------------------------------------------------------------


def test_field_write_in_branch_folds() -> None:
    # The shape `return b && Q()` takes once Q (count, return true) is inlined.
    source = """
    Game G() {
        Int c;
        Bool Test(Bool b) {
            if (b) {
                c = c + 1;
                return true;
            }
            return false;
        }
    }
    """
    expected = """
    Game G() {
        Int c;
        Bool Test(Bool b) {
            if (b) {
                c = c + 1;
            }
            return b;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_empty_branch_folds_to_return_of_condition() -> None:
    source = """
    Game G() {
        Bool Test(Int x, Int y) {
            if (x == y) {
                return true;
            }
            return false;
        }
    }
    """
    expected = """
    Game G() {
        Bool Test(Int x, Int y) {
            return x == y;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_condition_reading_a_map_folds() -> None:
    # Reads are total and depend only on what they read (no call): the branch
    # writes another field, so the condition keeps its value.
    source = """
    Game G() {
        Map<Int, Int> M;
        Int c;
        Bool Test(Int k, Int v) {
            if (k in M && M[k] == v) {
                c = c + 1;
                return true;
            }
            return false;
        }
    }
    """
    expected = """
    Game G() {
        Map<Int, Int> M;
        Int c;
        Bool Test(Int k, Int v) {
            if (k in M && M[k] == v) {
                c = c + 1;
            }
            return k in M && M[k] == v;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_branch_with_its_own_return_folds() -> None:
    # A return inside the branch exits both forms the same way.
    source = """
    Game G() {
        Int c;
        Bool Test(Bool b, Bool d) {
            if (b) {
                if (d) {
                    return false;
                }
                c = c + 1;
                return true;
            }
            return false;
        }
    }
    """
    expected = """
    Game G() {
        Int c;
        Bool Test(Bool b, Bool d) {
            if (b) {
                if (d) {
                    return false;
                }
                c = c + 1;
            }
            return b;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_nested_block_folds() -> None:
    source = """
    Game G() {
        Int c;
        Bool Test(Bool a, Bool b) {
            if (a) {
                if (b) {
                    c = c + 1;
                    return true;
                }
                return false;
            }
            return true;
        }
    }
    """
    expected = """
    Game G() {
        Int c;
        Bool Test(Bool a, Bool b) {
            if (a) {
                if (b) {
                    c = c + 1;
                }
                return b;
            }
            return true;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_both_forms_canonicalize_alike() -> None:
    # The two forms the pass exists for meet in the core pipeline.
    guarded = """
    Game G() {
        Int c;
        Void Initialize() { c = 0; }
        Bool Test(Bool b) {
            if (b) {
                c = c + 1;
                return true;
            }
            return false;
        }
        Int Count() { return c; }
    }
    """
    returns_condition = """
    Game G() {
        Int c;
        Void Initialize() { c = 0; }
        Bool Test(Bool b) {
            if (b) {
                c = c + 1;
            }
            return b;
        }
        Int Count() { return c; }
    }
    """
    assert run_pipeline(
        frog_parser.parse_game(guarded), CORE_PIPELINE, _ctx()
    ) == run_pipeline(frog_parser.parse_game(returns_condition), CORE_PIPELINE, _ctx())


# ---------------------------------------------------------------------------
# The pass declines: one test per precondition
# ---------------------------------------------------------------------------


def test_condition_with_call_unchanged() -> None:
    # Distinguisher if folded: F.Check need not be deterministic, so the
    # second evaluation in `return F.Check(x);` may be false after the branch
    # ran (the original returns true there), or the call may have an effect
    # that now happens twice.
    _assert_unchanged("""
    Game G() {
        Int c;
        Bool Test(Int x) {
            if (F.Check(x)) {
                c = c + 1;
                return true;
            }
            return false;
        }
    }
    """)


def test_branch_writes_condition_variable_unchanged() -> None:
    # Distinguisher if folded: the first Test() returns true in the original,
    # while `return c == 0;` after `c = c + 1` returns false.
    _assert_unchanged("""
    Game G() {
        Int c;
        Bool Test() {
            if (c == 0) {
                c = c + 1;
                return true;
            }
            return false;
        }
    }
    """)


def test_branch_element_write_to_condition_map_unchanged() -> None:
    # Distinguisher if folded: Test(k) on a fresh k returns true in the
    # original, while `return !(k in M);` after `M[k] = v` returns false.
    _assert_unchanged("""
    Game G() {
        Map<Int, Int> M;
        Bool Test(Int k, Int v) {
            if (!(k in M)) {
                M[k] = v;
                return true;
            }
            return false;
        }
    }
    """)


def test_branch_uniq_insertion_into_condition_set_unchanged() -> None:
    # Distinguisher if folded: the first Test() returns true in the original,
    # while `return |S| == 0;` after the draw inserted into S returns false.
    _assert_unchanged("""
    Game G() {
        Set<BitString<8>> S;
        BitString<8> last;
        Bool Test() {
            if (|S| == 0) {
                BitString<8> x <-uniq[S] BitString<8>;
                last = x;
                return true;
            }
            return false;
        }
    }
    """)


def test_branch_rebinding_condition_name_unchanged() -> None:
    # The local's scope ends with the branch, so the fold would read the
    # field; but passes that substitute by name are not scope-aware, so a
    # branch that rebinds a name the condition reads is left alone.
    _assert_unchanged("""
    Game G() {
        Bool f;
        Int c;
        Bool Test() {
            if (f) {
                Bool f = false;
                c = c + 1;
                return true;
            }
            return false;
        }
    }
    """)


def test_statement_between_if_and_return_false_unchanged() -> None:
    # `return false;` must follow the if directly: here the trailing return
    # runs after `c = 0;`, which the fold would have to account for.
    _assert_unchanged("""
    Game G() {
        Int c;
        Bool Test(Bool b) {
            if (b) {
                c = c + 1;
                return true;
            }
            c = 0;
            return false;
        }
    }
    """)


def test_else_block_unchanged() -> None:
    _assert_unchanged("""
    Game G() {
        Int c;
        Bool Test(Bool b) {
            if (b) {
                c = c + 1;
                return true;
            } else {
                c = 0;
            }
            return false;
        }
    }
    """)


def test_else_if_chain_unchanged() -> None:
    _assert_unchanged("""
    Game G() {
        Int c;
        Bool Test(Bool b, Bool d) {
            if (b) {
                c = c + 1;
                return true;
            } else if (d) {
                c = 0;
            }
            return false;
        }
    }
    """)


def test_swapped_literals_unchanged() -> None:
    # `if (C) { S; return false; } return true;` is not this shape.
    _assert_unchanged("""
    Game G() {
        Int c;
        Bool Test(Bool b) {
            if (b) {
                c = c + 1;
                return false;
            }
            return true;
        }
    }
    """)
