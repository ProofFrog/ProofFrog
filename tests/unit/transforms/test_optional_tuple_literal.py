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


def _map_game(body: str) -> str:
    return f"""
        Game G() {{
            Map<Int, Int> M;
            Int Test(Int k, Bool c) {{
                {body}
            }}
        }}
        """


@pytest.mark.parametrize("declared", ["[Int, Int]", "[Int, Int]?"])
@pytest.mark.parametrize(
    "rest",
    [
        # Dropped: element 0 is never projected.  Test(k) with k absent from
        # M reads M[k] before inlining and not after.
        "return v[1];",
        # Moved under a branch: with c false the read no longer happens.
        "if (c) { return v[0]; } return v[1];",
        # Moved past a statement that can return first.
        "if (c) { return 0; } return v[0] + v[1];",
        # Moved into a loop body, which may run zero times.
        "Int s = 0; for (Int i = 0 to k) { s = s + v[0]; } return s + v[1];",
    ],
)
def test_undefined_read_element_not_dropped_or_moved(declared: str, rest: str) -> None:
    """F-157: reading an absent map key is observable, so an element that
    indexes a map may not be dropped or moved to where fewer traces reach."""
    game = frog_parser.parse_game(_map_game(f"{declared} v = [M[k], 1]; {rest}"))
    ctx = _ctx()
    assert InlineLocalTupleLiteral().apply(game, ctx) == game
    assert any(
        nm.transform_name == "Inline Local Tuple Literal"
        and "indexes a map or array" in nm.reason
        for nm in ctx.near_misses
    )


@pytest.mark.parametrize("declared", ["[Int, Int]", "[Int, Int]?"])
def test_undefined_read_element_projected_next_still_inlined(declared: str) -> None:
    """Control: every element is projected by the statement right after the
    declaration, so the read stays on the same traces."""
    out = _inline(_map_game(f"{declared} v = [M[k], 1]; return v[0] + v[1];"))
    assert "v" not in out.replace("Void", "")
    assert "return M[k] + 1;" in out


@pytest.mark.parametrize("declared", ["[Int, Int]", "[Int, Int]?"])
def test_index_free_element_still_dropped(declared: str) -> None:
    """Control: no element indexes anything, so dropping one is fine."""
    out = _inline(_map_game(f"{declared} v = [k, 1]; if (c) {{ return 0; }} return v[1];"))
    assert "return 1;" in out and "[k, 1]" not in out


def test_engine_rejects_dropped_map_read_in_optional_tuple() -> None:
    """The optional form of the F-157 attack: the left game reads M[k] and
    the right does not.  (The non-optional form is still accepted through
    other passes; that is the open finding.)"""
    assert not _engine_equal(
        _map_game("""
            [Int, Int]? v = [M[k], 1];
            if (v == None) { return 0; }
            return v[1];
            """),
        _map_game("return 1;"),
    )
