import pytest
from proof_frog import dependencies, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            """
            Game G() {
                Int field;
                Int f() {
                    return field;
                }
            }
            """,
            """
            Game G() {
                Int field;
                Int f() {
                    return field;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int field;
                Int f() {
                    return 2;
                }
            }
            """,
            """
            Game G() {
                Int f() {
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int field;
                Int f() {
                    if (field > 2) {
                        return 1;
                    }
                    return 2;
                }
            }
            """,
            """
            Game G() {
                Int field;
                Int f() {
                    if (field > 2) {
                        return 1;
                    }
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int field;
                Int f() {
                    if (field > 2) {
                        return 1;
                    } else {
                        return 2;
                    }
                }
            }
            """,
            """
            Game G() {
                Int field;
                Int f() {
                    if (field > 2) {
                        return 1;
                    } else {
                        return 2;
                    }
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int field;
                Int f() {
                    Int x = 1;
                    if (field > 2) {
                        x = 2;
                    }
                    return x;
                }
            }
            """,
            """
            Game G() {
                Int field;
                Int f() {
                    Int x = 1;
                    if (field > 2) {
                        x = 2;
                    }
                    return x;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Int f() {
                    if (field1 > 2) {
                        field2 = 2;
                    }
                    return 0;
                }
                Int g() {
                    return field2;
                }
            }
            """,
            """
            Game G() {
                Int field1;
                Int field2;
                Int f() {
                    if (field1 > 2) {
                        field2 = 2;
                    }
                    return 0;
                }
                Int g() {
                    return field2;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int field;
                Int f() {
                    Int x = 1;
                    Int y = 2;
                    if (y == 2) {
                        x = 2;
                        field = field + 1;
                    }
                    return x;
                }
            }
            """,
            """
            Game G() {
                Int f() {
                    Int x = 1;
                    Int y = 2;
                    if (y == 2) {
                        x = 2;
                    }
                    return x;
                }
            }
            """,
        ),
    ],
)
def test_unnecessary_field_visitor(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(method)
    expected_ast = frog_parser.parse_game(expected)
    print("expected AST", expected_ast)
    transformed_ast = dependencies.remove_unnecessary_fields(game_ast)
    print("transformed AST", transformed_ast)
    assert expected_ast == transformed_ast


def test_f319_field_read_only_in_index_position_is_kept() -> None:
    """F-319: a field `F` read only in the index of a write to another (kept)
    field, `M[F] = v`, is necessary -- dropping it while `M[F] = v` survives
    emits a game with a dangling reference to the undeclared `F`. The game-wide
    fixpoint must keep `F` (and its setter) so the output stays well-formed."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<Int, Int> M;
            Int F;
            Void Initialize() { F = 0; }
            Void Store(Int v) { M[F] = v; }
            Map<Int, Int> Get() { return M; }
        }
        """
    )
    result = dependencies.remove_unnecessary_fields(game)
    out = str(result)
    assert "Int F;" in out, "the index field F must be kept (no dangling reference)"
    assert "F = 0" in out, "F's setter must be kept"
    assert "M[F]" in out, "the kept write M[F]=v must still reference a declared F"


def test_f319_genuinely_unnecessary_field_still_removed() -> None:
    """F-319 positive control: a field that is neither returned nor read in a
    kept write's index is still removed (the fixpoint does not over-keep)."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int U;
            Int M;
            Void Initialize() { U = 5; M = 3; }
            Int Get() { return M; }
        }
        """
    )
    result = dependencies.remove_unnecessary_fields(game)
    out = str(result)
    assert "Int U;" not in out, "a genuinely unnecessary field must still be removed"
    assert "Int M;" in out, "a necessary field must be kept"


def test_f320_loop_carried_write_not_deleted() -> None:
    """F-320: a loop-carried write whose reviving read is EARLIER in the body
    text but executes in a LATER iteration (via the back-edge) must not be
    deleted. For `for (...) { y = y + x; x = x + 1; }` a single reverse pass
    marks `x = x + 1` dead before `y = y + x` makes `x` necessary; the liveness
    fixpoint revives it, so the loop-carried increment survives."""
    method = frog_parser.parse_method(
        """
        Int Sum(Int n) {
            Int x = 0;
            Int y = 0;
            for (Int i = 0 to n) {
                y = y + x;
                x = x + 1;
            }
            return y;
        }
        """
    )
    result = dependencies.remove_unnecessary_statements(
        [], method.block, outer_names=set()
    )
    out = str(result)
    assert "x = x + 1" in out, "the loop-carried increment must not be deleted"
    assert "y = y + x" in out
