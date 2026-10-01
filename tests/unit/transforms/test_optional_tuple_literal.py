"""A tuple literal bound to an optional tuple type is never None.

DeadNullGuardEliminator drops the guard, and InlineLocalTupleLiteral
folds ``v[k]``, as for a non-optional tuple.
"""

import pytest

from proof_frog import frog_parser, visitors
from proof_frog.proof_engine import ProofEngine
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.inlining import InlineLocalTupleLiteral
from proof_frog.transforms.types import DeadNullGuardEliminator
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _dead_null(source: str) -> str:
    game = frog_parser.parse_game(source)
    return str(
        DeadNullGuardEliminator(visitors.build_game_type_map(game)).transform(game)
    )


def _inline(source: str) -> str:
    game = frog_parser.parse_game(source)
    return str(InlineLocalTupleLiteral().apply(game, _ctx()))


def test_guard_on_optional_tuple_literal_removed() -> None:
    out = _dead_null("""
        Game G() {
            Int Test(Int x, Int y) {
                [Int, Int]? v = [x, y];
                if (v == None) {
                    return 0;
                }
                return 1;
            }
        }
        """)
    assert "v == None" not in out


def test_guard_kept_when_tuple_may_be_overwritten() -> None:
    out = _dead_null("""
        Game G() {
            Int Test(Int x, Int y, Bool c) {
                [Int, Int]? v = [x, y];
                if (c) { v = None; }
                if (v == None) {
                    return 0;
                }
                return 1;
            }
        }
        """)
    assert "if (v == None)" in out


def test_optional_tuple_index_inlined() -> None:
    out = _inline("""
        Game G() {
            Int Test(Int x, Int y) {
                [Int, Int]? v = [x, y];
                return v[1];
            }
        }
        """)
    assert "v[1]" not in out
    assert "return y;" in out


def test_optional_tuple_index_not_inlined_after_write() -> None:
    out = _inline("""
        Game G() {
            Int Test(Int x, Int y, Bool c) {
                [Int, Int]? v = [x, y];
                if (c) { v = [y, x]; }
                return v[0];
            }
        }
        """)
    assert "v[0]" in out


def _engine_equal(left: str, right: str) -> bool:
    return (
        ProofEngine()
        .check_equivalent(frog_parser.parse_game(left), frog_parser.parse_game(right))
        .valid
    )


_PROJECT = """
    Game G() {
        Int Test(Int x, Int y, Bool c) {
            return y;
        }
    }
    """


def test_engine_accepts_guarded_optional_tuple() -> None:
    assert _engine_equal(
        """
        Game G() {
            Int Test(Int x, Int y, Bool c) {
                [Int, Int]? v = [x, y];
                if (v == None) {
                    return 0;
                }
                return v[1];
            }
        }
        """,
        _PROJECT,
    )


def test_engine_rejects_overwritten_optional_tuple() -> None:
    assert not _engine_equal(
        """
        Game G() {
            Int Test(Int x, Int y, Bool c) {
                [Int, Int]? v = [x, y];
                if (c) { v = None; }
                if (v == None) {
                    return 0;
                }
                return v[1];
            }
        }
        """,
        _PROJECT,
    )


@pytest.mark.parametrize("declared", ["[Int, Int]", "[Int, Int]?"])
@pytest.mark.parametrize("element", ["v[0]", "v[1]", "v[0] + 1"])
def test_self_referential_element_declined(declared: str, element: str) -> None:
    """A local tuple that shadows a field `v` and reads the field in its own
    initialiser.  Substituting the element for `v[0]` reintroduces a `v[...]`
    access, so the pass used to substitute forever; it now declines."""
    source = f"""
        Game G() {{
            [Int, Int] v;
            Int Test(Int y) {{
                {declared} v = [{element}, y];
                return v[0];
            }}
        }}
        """
    game = frog_parser.parse_game(source)
    ctx = _ctx()
    assert InlineLocalTupleLiteral().apply(game, ctx) == game
    assert any(
        nm.transform_name == "Inline Local Tuple Literal"
        and nm.variable == "v"
        and "outer variable also named 'v'" in nm.reason
        for nm in ctx.near_misses
    )


def test_element_reading_other_field_still_inlined() -> None:
    """Control for the self-reference guard: the element reads a field of a
    different name, so the substitution terminates and the pass fires."""
    out = _inline("""
        Game G() {
            [Int, Int] w;
            Int Test(Int y) {
                [Int, Int] v = [w[0], y];
                return v[0];
            }
        }
        """)
    assert "v" not in out.replace("Void", "")
    assert "return w[0];" in out
