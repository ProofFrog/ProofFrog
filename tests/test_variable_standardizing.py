"""Tests for VariableStandardizingTransformer.

Exercises a naming-collision bug that occurs when the topological sort
reorders statements, causing VariableStandardizingTransformer to rename
a variable to a name that already exists in the block.

Root cause: VST iterates over the original statement list while renaming
in the current (accumulated) block. After renaming v3→v1, the old v1
is also named "v1", so the next rename step incorrectly renames both.

Fix: two-phase rename — first to collision-safe intermediates, then to v1, v2, ...
"""
import pytest
from proof_frog import frog_parser, proof_engine
from proof_frog.transforms.standardization import VariableStandardizingTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Simulates the post-topological-sort state of Snippet 1.
        # Original: v1=foo(), v2=v1+m, v3=foo(), return v3+v2
        # After topo sort: v3 moves to position 0 (v1 and v3 are independent,
        # and the DFS-then-Kahn sort happens to put v3 first).
        # VST must standardize this to the same form as Snippet 2 below.
        (
            """
            BitString<n> f(BitString<n> m) {
                BitString<n> v3 = foo();
                BitString<n> v1 = foo();
                BitString<n> v2 = v1 + m;
                return v3 + v2;
            }
            """,
            """
            BitString<n> f(BitString<n> m) {
                BitString<n> v1 = foo();
                BitString<n> v2 = foo();
                BitString<n> v3 = v2 + m;
                return v1 + v3;
            }
            """,
        ),
        # Simulates the post-topological-sort state of Snippet 2.
        # Original: v1=foo(), v2=foo(), v3=v1+m, return v2+v3
        # After topo sort: v2 moves to position 0.
        # Must produce the identical standardized form as Snippet 1 above.
        (
            """
            BitString<n> f(BitString<n> m) {
                BitString<n> v2 = foo();
                BitString<n> v1 = foo();
                BitString<n> v3 = v1 + m;
                return v2 + v3;
            }
            """,
            """
            BitString<n> f(BitString<n> m) {
                BitString<n> v1 = foo();
                BitString<n> v2 = foo();
                BitString<n> v3 = v2 + m;
                return v1 + v3;
            }
            """,
        ),
        # Simple case: already canonical, no reordering needed.
        (
            """
            BitString<n> f(BitString<n> m) {
                BitString<n> v1 = foo();
                BitString<n> v2 = v1 + m;
                return v2;
            }
            """,
            """
            BitString<n> f(BitString<n> m) {
                BitString<n> v1 = foo();
                BitString<n> v2 = v1 + m;
                return v2;
            }
            """,
        ),
    ],
)
def test_variable_standardizing_no_collision(method: str, expected: str) -> None:
    """VST correctly renames variables even when the target name already exists."""
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    result = VariableStandardizingTransformer().transform(method_ast)
    print("EXPECTED", expected_ast)
    print("RESULT  ", result)
    assert result == expected_ast


# Full games with the two semantically equivalent but differently-ordered bodies.
# foo() is used as a function call placeholder: CollapseAssignmentTransformer
# skips assignments that contain function calls, so these assignments stay
# separate and the topological sort reordering is what the VST must handle.
_GAME_SNIPPET1 = """
Game Test() {
    BitString<n> Oracle(BitString<n> m) {
        BitString<n> v1 = foo();
        BitString<n> v2 = v1 + m;
        BitString<n> v3 = foo();
        return v3 + v2;
    }
}
"""

_GAME_SNIPPET2 = """
Game Test() {
    BitString<n> Oracle(BitString<n> m) {
        BitString<n> v1 = foo();
        BitString<n> v2 = foo();
        BitString<n> v3 = v1 + m;
        return v2 + v3;
    }
}
"""


def test_equivalent_statement_orderings() -> None:
    """Two games differing only in statement ordering produce the same canonical form."""
    game1 = frog_parser.parse_game(_GAME_SNIPPET1)
    game2 = frog_parser.parse_game(_GAME_SNIPPET2)
    engine = proof_engine.ProofEngine(verbose=False)
    assert engine.check_equivalent(game1, game2)
