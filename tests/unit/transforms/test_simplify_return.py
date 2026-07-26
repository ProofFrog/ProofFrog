import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import SimplifyReturnTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            """
            Int f() {
                Int a = 1;
                return a;
            }
            """,
            """
            Int f() {
                return 1;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = g();
                return a;
            }
            """,
            """
            Int f() {
                return g();
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                f(b);
                return a;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a;
                f(b);
                return a;
            }
            """,
        ),
    ],
)
def test_simplify_return(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = SimplifyReturnTransformer().transform(game_ast)
    print(transformed_ast)
    assert expected_ast == transformed_ast


@pytest.mark.parametrize(
    "method,expected",
    [
        # Intervening statement reassigns a local that appears in expr
        (
            """
            Int f(Int x) {
                Int v = x + 1;
                x = 10;
                return v;
            }
            """,
            """
            Int f(Int x) {
                Int v = x + 1;
                x = 10;
                return v;
            }
            """,
        ),
        # Intervening statement reassigns a different local in expr
        (
            """
            Int f() {
                Int a = 1;
                Int b = 2;
                Int v = a + b;
                a = 99;
                return v;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = 2;
                Int v = a + b;
                a = 99;
                return v;
            }
            """,
        ),
        # Multiple intervening statements, one modifies a dependency
        (
            """
            Int f(Int x, Int y) {
                Int v = x + y;
                Int z = 5;
                x = z;
                return v;
            }
            """,
            """
            Int f(Int x, Int y) {
                Int v = x + y;
                Int z = 5;
                x = z;
                return v;
            }
            """,
        ),
        # Intervening statement does NOT modify any dependency — should still inline
        (
            """
            Int f(Int x) {
                Int v = x + 1;
                Int z = 99;
                return v;
            }
            """,
            """
            Int f(Int x) {
                Int z = 99;
                return x + 1;
            }
            """,
        ),
    ],
)
def test_simplify_return_dependency_safety(
    method: str,
    expected: str,
) -> None:
    """SimplifyReturn must not inline when intervening statements modify
    free variables of the expression being inlined."""
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = SimplifyReturnTransformer().transform(game_ast)
    print(transformed_ast)
    assert expected_ast == transformed_ast


@pytest.mark.parametrize(
    "game,expected",
    [
        # Field modified between assignment and return
        (
            """
            Game G() {
                Int field1;

                Int f(Int x) {
                    Int v = field1 + x;
                    field1 = 42;
                    return v;
                }
            }
            """,
            """
            Game G() {
                Int field1;

                Int f(Int x) {
                    Int v = field1 + x;
                    field1 = 42;
                    return v;
                }
            }
            """,
        ),
    ],
)
def test_simplify_return_field_dependency(
    game: str,
    expected: str,
) -> None:
    """SimplifyReturn must not inline when intervening statements modify
    a field that the inlined expression depends on."""
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)

    transformed_ast = SimplifyReturnTransformer().transform_game(game_ast)
    print(transformed_ast)
    assert expected_ast == transformed_ast


# RC1 soundness: SimplifyReturn moves a read past the intervening statements.
# The intervening-modification guard was node-kind-incomplete (FieldAccess-blind
# read-set; depth-1-ArrayAccess / Variable-only write-set; blind to <-uniq
# insertion), so these distinguishable shapes were wrongly collapsed (findings
# F-126: A1 uniq-insertion, A2 map-view FieldAccess, A3 nested element write).
@pytest.mark.parametrize(
    "game",
    [
        # A1: `x <-uniq[S] T` inserts into S, so moving `|S|` past it changes
        # the value.  The write is on unique_set, not node.var.
        """
        Game G() {
            Set<BitString<1>> S;
            Int O() {
                Int s = |S|;
                BitString<1> x <-uniq[S] BitString<1>;
                return s;
            }
        }
        """,
        # A2: the read reaches M only through the FieldAccess view `M.keys`;
        # the write `M[0b0] = 0b0` must still be seen.
        """
        Game G() {
            Map<BitString<1>, BitString<1>> M;
            Int O() {
                Int s = |M.keys|;
                M[0b0] = 0b0;
                return s;
            }
        }
        """,
        # A3: nested element write `M[0][1] = 1` mutates `M[0]`, which the
        # read `M[0]` depends on; the l-value base is two levels deep.
        """
        Game G() {
            Map<Int, [Int, Int]> M;
            [Int, Int] O() {
                [Int, Int] s = M[0];
                M[0][1] = 1;
                return s;
            }
        }
        """,
    ],
)
def test_simplify_return_soundness_declines(game: str) -> None:
    """SimplifyReturn must not move a read past an intervening mutation of a
    variable the read depends on, regardless of how the write/read is spelled."""
    game_ast = frog_parser.parse_game(game)
    transformed = SimplifyReturnTransformer().transform_game(game_ast)
    assert str(game_ast) == str(transformed), (
        f"read was wrongly moved past an intervening mutation:\n{transformed}"
    )


@pytest.mark.parametrize(
    "game,expected",
    [
        # FieldAccess read with NO intervening write to M: the complete
        # read-set must not over-block -- the move must still fire.
        (
            """
            Game G() {
                Map<Int, Int> M;
                Int O() {
                    Int s = |M.keys|;
                    Int t = 5;
                    return s;
                }
            }
            """,
            """
            Game G() {
                Map<Int, Int> M;
                Int O() {
                    Int t = 5;
                    return |M.keys|;
                }
            }
            """,
        ),
    ],
)
def test_simplify_return_soundness_still_fires(game: str, expected: str) -> None:
    """The node-kind-complete read-set must not over-decline: a FieldAccess
    read with no intervening write is still inlined into the return."""
    transformed = SimplifyReturnTransformer().transform_game(
        frog_parser.parse_game(game)
    )
    assert frog_parser.parse_game(expected) == transformed


def test_f127_reduction_field_write_preserved() -> None:
    """F-127: SimplifyReturn's field-write protection reads self.fields, which
    was populated only by transform_game. A Reduction (a Game subclass, but
    dispatched via transform_reduction) left it empty, so `f = 7; return f;` in
    a reduction oracle was collapsed to `return 7;`, dropping the observable
    field write. transform_reduction now populates the fields."""
    reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Int f;
            Void Initialize() { f = 0; }
            Int Oracle() {
                f = 7;
                return f;
            }
        }
    """)
    out = SimplifyReturnTransformer().transform(reduction)
    assert isinstance(out, type(reduction))  # still a Reduction
    assert "f = 7" in str(out)  # field write not deleted


def test_f127_reduction_local_still_inlined() -> None:
    """Control for F-127: a genuine typed local in a reduction oracle is still
    inlined into the trailing return."""
    reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Void Initialize() { }
            Int Oracle() {
                Int v = 5;
                return v;
            }
        }
    """)
    out = str(SimplifyReturnTransformer().transform(reduction))
    assert "return 5" in out and "Int v = 5" not in out
