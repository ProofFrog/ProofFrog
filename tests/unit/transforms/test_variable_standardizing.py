"""Tests for scope-aware local variable standardization.

The name-collision cases exercise statement reordering that puts an existing
``vN`` local before another local. The scope tests pin bare declarations,
shadowing, loop binders, and type lengths.
"""

import pytest
from proof_frog import frog_ast, frog_parser, proof_engine, visitors
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


@pytest.mark.parametrize(
    "draw,expected",
    [
        ("BitString<8> x <- s;", "BitString<8> v2 <- v1;"),
        ("BitString<8> x <-uniq[T] s;", "BitString<8> v2 <-uniq[T] v1;"),
        ("BitString<8> x <- s \\ {s};", "BitString<8> v2 <- v1 \\ {v1};"),
    ],
)
def test_bare_local_name_as_sampling_domain_follows_its_binder(
    draw: str, expected: str
) -> None:
    """Defensive: a draw whose domain is a local VALUE has no meaning, but it
    is not rejected today. The typechecker only requires the right-hand side
    of ``<-`` to be a ``Type``, which a bare ``Variable`` is, so this shape
    reaches the engine. Under position-sensitive scoping the name is the
    local, AlphaRename renames it with its binder, and the standardizer must
    do the same or the ``__aN__`` name survives there with no binder.

    The well-formed case, a local in a length argument of the domain
    (``BitString<n>``), is ``test_length_type_tracks_renamed_local_on_repeated_passes``.
    """
    game = frog_parser.parse_game(f"""
    Game G() {{
        Set<BitString<8>> T;
        BitString<8> O() {{
            BitString<8> s = foo();
            {draw}
            return x;
        }}
    }}
    """)
    ctx = PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )
    alpha = AlphaRename().apply(game, ctx)
    assert "__a0__;" in str(alpha) or "__a0__ \\" in str(alpha)
    result = VariableStandardizingTransformer().transform(alpha)
    assert "__a" not in str(result)
    assert expected in str(result)
    assert VariableStandardizingTransformer().transform(game) == result


def test_type_name_as_sampling_domain_is_left_alone() -> None:
    """A domain name with no local binder (a ``Set`` let, a type alias) is
    not a local and keeps its name."""
    game = frog_parser.parse_game("""
    Game G(Set K) {
        Set<K> T;
        K O() {
            K a <- K;
            K b <-uniq[T] K;
            return a;
        }
    }
    """)
    result = str(VariableStandardizingTransformer().transform(game))
    assert "K v1 <- K;" in result
    assert "K v2 <-uniq[T] K;" in result


def test_name_used_only_as_signature_length_is_reserved() -> None:
    """``v1`` occurs only as a length argument in the signature, where it
    names an outer value (a game parameter that instantiation substituted
    in). No local may be given that name."""
    game = frog_parser.parse_game("""
    Game G() {
        BitString<v1> O(BitString<v1> m) {
            Int a = 5;
            return m;
        }
    }
    """)
    expected = frog_parser.parse_game("""
    Game G() {
        BitString<v1> O(BitString<v1> m) {
            Int v2 = 5;
            return m;
        }
    }
    """)
    assert VariableStandardizingTransformer().transform(game) == expected


def test_name_used_only_in_signature_return_type_is_reserved() -> None:
    game = frog_parser.parse_game("""
    Game G() {
        Array<Int, v1> O() {
            Array<Int, v2> a = foo();
            return a;
        }
    }
    """)
    result = str(VariableStandardizingTransformer().transform(game))
    assert "Array<Int, v1> O()" in result
    assert "Array<Int, v2> v3 = foo();" in result


# One method per binder form. In each, ``v1`` is used OUTSIDE the scope of
# the local binder that carries the same name, so it is free there and must
# stay reserved, and ``w`` is bound wherever it is used.
_SCOPE_CASES = [
    # typed assignment: the right-hand side is evaluated before the binder
    "Int O() { Int v1 = v1 + 1; Int w = 2; return w; }",
    # typed sample: the domain's length is evaluated before the binder
    "Int O() { BitString<v1> v1 <- BitString<v1>; Int w = 2; return w; }",
    # typed unique sample: exclusion set evaluated before the binder
    "Int O() { Int w = 2; BitString<8> v1 <-uniq[v1] BitString<8>; return w; }",
    # bare declaration: read above it
    "Int O() { Int w = v1; Int v1; v1 = 2; return w + v1; }",
    # branch-local binder, read after the branch
    "Int O(Bool c) { Int w = 0; if (c) { Int v1 = 1; w = v1; } return w + v1; }",
    # else-branch binder, read in the then-branch
    "Int O(Bool c) { Int w = 0; if (c) { w = v1; } else { Int v1 = 1; w = v1; } return w; }",
    # numeric loop binder: bounds are outside its scope, and so is the tail
    "Int O() { Int w = 0; for (Int v1 = v1 to 3) { w = w + v1; } return w; }",
    "Int O() { Int w = 0; for (Int v1 = 0 to 3) { w = w + v1; } return w + v1; }",
    # generic loop binder: the iterated set and its type are outside its scope
    "Int O() { Int w = 0; for (Int v1 in v1) { w = w + v1; } return w; }",
    "Int O() { Int w = 0; for (BitString<v1> v1 in S) { w = w + 1; } return w; }",
    # binder inside a loop body, read after the loop
    "Int O() { Int w = 0; for (Int i = 0 to 3) { Int v1 = i; w = w + v1; } return w + v1; }",
    # untyped write and element write to a name with no binder
    "Int O() { Int w = 0; v1 = w; return w; }",
    "Int O() { Int w = 0; v1[w] = w; return w; }",
    # bare call statement
    "Void O() { Int w = 0; foo(v1, w); }",
]


@pytest.mark.parametrize("method_code", _SCOPE_CASES)
def test_free_names_agree_with_the_rename_walk(method_code: str) -> None:
    """The free names and the renaming come from one scope walk. For every
    binder form: a name used outside its binder's scope is reported free, is
    left untouched by the renaming, and is never minted; a name used only
    under its binder is not reported free and does not survive."""
    method = frog_parser.parse_method(method_code)
    transformer = VariableStandardizingTransformer()
    parameters = {param.name for param in method.signature.parameters}

    # pylint: disable=protected-access
    free = transformer._free_names(method, parameters)
    # pylint: enable=protected-access
    assert "v1" in free
    assert "w" not in free
    assert not free & parameters

    renamed = transformer.transform_method(method)
    names = visitors.referenced_variable_names(renamed)
    # Every free name is still there, and no binder was given one.
    assert free <= names
    binders = _binder_names(renamed)
    assert not binders & free
    # ``w`` was only ever a local, so it is gone; the local ``v1`` became
    # another name, so every remaining ``v1`` is the free one.
    assert "w" not in names
    assert "v1" not in binders


def _binder_names(method: frog_ast.Method) -> set[str]:
    names: set[str] = set()

    def collect(node: frog_ast.ASTNode) -> bool:
        if isinstance(node, frog_ast.NumericFor):
            names.add(node.name)
        elif isinstance(node, frog_ast.GenericFor):
            names.add(node.var_name)
        elif isinstance(node, frog_ast.VariableDeclaration):
            names.add(node.name)
        elif (
            isinstance(
                node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            )
            and node.the_type is not None
            and isinstance(node.var, frog_ast.Variable)
        ):
            names.add(node.var.name)
        return False

    visitors.SearchVisitor(collect).visit(method)
    return names


def test_collecting_free_names_leaves_the_method_and_counter_alone() -> None:
    method = frog_parser.parse_method(
        "Int O(Bool c) { Int a = 1; if (c) { Int b = a; } return a + q; }"
    )
    before = str(method)
    transformer = VariableStandardizingTransformer()
    # pylint: disable=protected-access
    assert transformer._free_names(method, {"c"}) == {"q"}
    assert transformer._counter == 0
    assert transformer._free is None
    # pylint: enable=protected-access
    assert str(method) == before
