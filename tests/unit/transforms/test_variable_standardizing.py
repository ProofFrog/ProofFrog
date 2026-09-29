"""Tests for scope-aware local variable standardization.

The name-collision cases exercise statement reordering that puts an existing
``vN`` local before another local. The scope tests pin bare declarations,
shadowing, loop binders, and type lengths.
"""

import pytest
from proof_frog import frog_parser, proof_engine
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.alpha_rename import AlphaRename
from proof_frog.transforms.standardization import VariableStandardizingTransformer
from proof_frog.visitors import NameTypeMap


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


def test_parameter_name_collision_skipped() -> None:
    """When a method parameter is named v1, locals must skip v1 and use v2."""
    game = frog_parser.parse_game("""
    Game Test() {
        BitString<n> Oracle(BitString<n> v1) {
            BitString<n> x = foo();
            return x + v1;
        }
    }
    """)
    expected = frog_parser.parse_game("""
    Game Test() {
        BitString<n> Oracle(BitString<n> v1) {
            BitString<n> v2 = foo();
            return v2 + v1;
        }
    }
    """)
    result = VariableStandardizingTransformer().transform(game)
    print("EXPECTED", expected)
    print("RESULT  ", result)
    # The local 'x' should become v2 (not v1, which is a parameter)
    assert (
        result == expected
    ), "Local variable should skip vN names that collide with parameters"


def test_parameter_v2_with_two_locals() -> None:
    """With parameter v2 and two locals, should produce v1 and v3 (skip v2)."""
    game = frog_parser.parse_game("""
    Game Test() {
        BitString<n> Oracle(BitString<n> v2) {
            BitString<n> x = foo();
            BitString<n> y = x + v2;
            return y;
        }
    }
    """)
    expected = frog_parser.parse_game("""
    Game Test() {
        BitString<n> Oracle(BitString<n> v2) {
            BitString<n> v1 = foo();
            BitString<n> v3 = v1 + v2;
            return v3;
        }
    }
    """)
    result = VariableStandardizingTransformer().transform(game)
    print("EXPECTED", expected)
    print("RESULT  ", result)
    assert (
        result == expected
    ), "Locals should be v1, v3 (skipping v2 which is a parameter)"


def test_equivalent_statement_orderings() -> None:
    """Two games differing only in statement ordering produce the same canonical form."""
    game1 = frog_parser.parse_game(_GAME_SNIPPET1)
    game2 = frog_parser.parse_game(_GAME_SNIPPET2)
    engine = proof_engine.ProofEngine(verbose=False)
    assert engine.check_equivalent(game1, game2)


def test_bare_declaration_and_shadowed_field_keep_their_bindings() -> None:
    game = frog_parser.parse_game("""
    Game G() {
        Int x;
        Int O(Bool c) {
            Int y;
            y = x;
            if (c) {
                Int x = 1;
                y = y + x;
            }
            return y + x;
        }
    }
    """)
    expected = frog_parser.parse_game("""
    Game G() {
        Int x;
        Int O(Bool c) {
            Int v1;
            v1 = x;
            if (c) {
                Int v2 = 1;
                v1 = v1 + v2;
            }
            return v1 + x;
        }
    }
    """)
    assert VariableStandardizingTransformer().transform(game) == expected


def test_loop_binder_does_not_capture_outer_local() -> None:
    game = frog_parser.parse_game("""
    Game G() {
        Int O() {
            Int x = 5;
            for (Int x = 0 to 2) {
                x = x + 1;
            }
            return x;
        }
    }
    """)
    expected = frog_parser.parse_game("""
    Game G() {
        Int O() {
            Int v1 = 5;
            for (Int v2 = 0 to 2) {
                v2 = v2 + 1;
            }
            return v1;
        }
    }
    """)
    assert VariableStandardizingTransformer().transform(game) == expected


def test_length_type_tracks_renamed_local_on_repeated_passes() -> None:
    game = frog_parser.parse_game("""
    Game G() {
        Int O() {
            Int n = 8;
            BitString<n> x <- BitString<n>;
            return |x|;
        }
    }
    """)
    standardizer = VariableStandardizingTransformer()
    once = standardizer.transform(game)
    twice = standardizer.transform(once)
    assert once == twice
    assert "BitString<v1> v2 <- BitString<v1>" in str(once)


def test_local_numbering_restarts_in_each_method() -> None:
    game = frog_parser.parse_game("""
    Game G() {
        Int First() {
            Int first = foo();
            return first + first;
        }
        Int Send() {
            Int second = bar();
            return second + second;
        }
    }
    """)
    result = VariableStandardizingTransformer().transform(game)
    assert "Int v1 = foo()" in str(result)
    assert "Int v1 = bar()" in str(result)
    assert "v2" not in str(result)


def test_free_name_bound_in_another_branch_is_reserved() -> None:
    """``v1`` is bound in one branch and free in the fall-through return. A
    whole-method ``references - binders`` set does not reserve it, and the
    outer local then captures the free read."""
    game = frog_parser.parse_game("""
    Game G() {
        Int O(Bool c) {
            Int x = 0;
            if (c) {
                Int v1 = 1;
                return v1;
            }
            return x + v1;
        }
    }
    """)
    expected = frog_parser.parse_game("""
    Game G() {
        Int O(Bool c) {
            Int v2 = 0;
            if (c) {
                Int v3 = 1;
                return v3;
            }
            return v2 + v1;
        }
    }
    """)
    assert VariableStandardizingTransformer().transform(game) == expected


def test_free_name_read_before_its_binder_is_reserved() -> None:
    game = frog_parser.parse_game("""
    Game G() {
        Int O() {
            Int out = v1;
            Int v1 = 0;
            return out + v1;
        }
    }
    """)
    expected = frog_parser.parse_game("""
    Game G() {
        Int O() {
            Int v2 = v1;
            Int v3 = 0;
            return v2 + v3;
        }
    }
    """)
    assert VariableStandardizingTransformer().transform(game) == expected


def test_sample_domain_follows_renamed_local() -> None:
    """AlphaRename rewrites ``Sample.sampled_from`` as an expression, so the
    standardizer must too, or the ``__aN__`` name survives there."""
    game = frog_parser.parse_game("""
    Game G() {
        BitString<8> O() {
            BitString<8> s = foo();
            BitString<8> x <- s;
            return x;
        }
    }
    """)
    ctx = PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )
    alpha = AlphaRename().apply(game, ctx)
    assert "<- __a" in str(alpha)
    result = VariableStandardizingTransformer().transform(alpha)
    assert "__a" not in str(result)
    assert "BitString<8> v2 <- v1" in str(result)
    assert VariableStandardizingTransformer().transform(game) == result
