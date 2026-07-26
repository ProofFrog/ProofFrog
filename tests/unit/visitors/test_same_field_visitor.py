import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "game,pair,expected",
    [
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    field1 = 0;
                    field2 = 1;
                }
            }
            """,
            ("field1", "field2"),
            False,
        ),
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    field1 = 1;
                    field2 = 1;
                }
            }
            """,
            ("field1", "field2"),
            True,
        ),
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    Int x = 3;
                    field1 = x;
                    field2 = x;
                }
            }
            """,
            ("field1", "field2"),
            True,
        ),
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    Int x = 3;
                    field1 = x;
                    x = 5;
                    field2 = x;
                }
            }
            """,
            ("field1", "field2"),
            False,
        ),
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    field1 = challenger.g();
                    field2 = challenger.g();
                }
            }
            """,
            ("field1", "field2"),
            False,
        ),
        (
            """
            Game G() {
                Set<Int> s1;
                Set<Int> s2;
                Void f() {
                    Int x = 5;
                    s1 = s1 union x;
                    s2 = s2 union x;
                }
            }
            """,
            ("s1", "s2"),
            True,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    Int a = 2;
                    x = 5;
                    y = 5;
                    a = a + 1;
                    a = a * a;
                    a = a + x + y;
                    x = x + 1;
                    y = y + 1;
                }
            }
            """,
            ("x", "y"),
            True,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    x = 5;
                    if (True) {
                        y = 10;
                    }
                    y = 5;
                }
            }
            """,
            ("x", "y"),
            False,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    [Int, Int] a = [5, 10];
                    x = a[0];
                    y = a[0];
                }
            }
            """,
            ("x", "y"),
            True,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    [Int, Int] a = [5, 10];
                    x = a[0];
                    a[0] = 100;
                    y = a[0];
                }
            }
            """,
            ("x", "y"),
            False,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    [Int, Int] a = [5, 10];
                    x = a[0];
                    a = [20, 30];
                    y = a[0];
                }
            }
            """,
            ("x", "y"),
            False,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    x = 5;
                    y = 5;

                    x = 10;
                    Int a = y;
                    y = 10;
                    return a;
                }
            }
            """,
            ("x", "y"),
            False,
        ),
        # Direct field copy after function call: field1 = f(); field2 = field1
        # This IS a valid duplicate — the copy doesn't replicate the call.
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    field1 = challenger.g();
                    field2 = field1;
                }
            }
            """,
            ("field1", "field2"),
            True,
        ),
        # Two independent function calls — NOT the same
        # (each call may return a different value)
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    field1 = challenger.g();
                    field2 = challenger.h();
                }
            }
            """,
            ("field1", "field2"),
            False,
        ),
        # Direct copy but pair field read before copy — NOT safe
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Int f() {
                    field1 = challenger.g();
                    Int x = field2;
                    field2 = field1;
                    return x;
                }
            }
            """,
            ("field1", "field2"),
            False,
        ),
    ],
)
def test_same_field_visitor(game: str, pair: tuple[str, str], expected: bool) -> None:
    game_ast = frog_parser.parse_game(game)

    print("GAME", game_ast)
    are_the_same = visitors.SameFieldVisitor(pair).visit(game_ast)

    if expected:
        assert isinstance(are_the_same, list)
    else:
        assert are_the_same is None


def test_f298_early_return_between_paired_writes_not_same() -> None:
    """F-298: `f1 = 1; if (b) { return 0; } f2 = 1;` -- the two writes are
    separated by an early return, so on the `Mark(true)` trace `f1` is written
    but `f2` is not. The fields are NOT equal on every trace, so SameFieldVisitor
    must report them as not-the-same (the pass must not merge them)."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int f1;
            Int f2;
            Void Initialize() { f1 = 0; f2 = 0; }
            Int Mark(Bool b) {
                f1 = 1;
                if (b) { return 0; }
                f2 = 1;
                return 1;
            }
            Int GetTwo() { return f2; }
        }
        """
    )
    result = visitors.SameFieldVisitor(("f1", "f2")).visit(game)
    assert result is None, "writes separated by an early return must not be paired"


def test_f298_copy_behind_early_return_not_same() -> None:
    """F-298 copy path: `f1 = G.rand(); if (b) { return 0; } f2 = f1;` -- the
    copy that would equate the fields is skippable via the early return, so they
    are not equal on every trace."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int f1;
            Int f2;
            Void Initialize() { f1 = 0; f2 = 0; }
            Int Mark(Bool b) {
                f1 = G.rand();
                if (b) { return 0; }
                f2 = f1;
                return 1;
            }
            Int GetTwo() { return f2; }
        }
        """
    )
    result = visitors.SameFieldVisitor(("f1", "f2")).visit(game)
    assert result is None, "a copy behind an early return must not be paired"


def test_f298_adjacent_writes_still_paired() -> None:
    """F-298 positive control: with no early return between them, the two equal
    writes still pair (a return BEFORE both writes is fine -- both are skipped
    together)."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int f1;
            Int f2;
            Void Initialize() { f1 = 0; f2 = 0; }
            Void Mark() {
                f1 = 1;
                f2 = 1;
            }
        }
        """
    )
    result = visitors.SameFieldVisitor(("f1", "f2")).visit(game)
    assert isinstance(result, list), "adjacent equal writes should still pair"


def test_f299_structurally_identical_unpaired_twin_not_conflated() -> None:
    """F-299: the paired-statement exemption must match by IDENTITY, not
    structural equality. `MarkF2Only` writes `f2 = 1` with no matching `f1 = 1`,
    so f1 and f2 are not always equal. Because that write is structurally
    identical to `MarkBoth`'s already-paired `f2 = 1`, a structural `in` test
    wrongly exempted it from analysis and reported the fields as mergeable. With
    identity matching the unpaired twin is analyzed and the visitor declines."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int f1;
            Int f2;
            Void Initialize() { f1 = 0; f2 = 0; }
            Void MarkBoth() { f1 = 1; f2 = 1; }
            Void MarkF2Only() { f2 = 1; }
            Int Get() { return f2; }
        }
        """
    )
    result = visitors.SameFieldVisitor(("f1", "f2")).visit(game)
    assert result is None, "an unpaired identical-looking twin write must decline the merge"


def test_f299_genuinely_equal_fields_still_merge() -> None:
    """F-299 positive control: when every write keeps the fields equal, they
    still pair (identity matching does not over-decline legitimate merges)."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int f1;
            Int f2;
            Void Initialize() { f1 = 0; f2 = 0; }
            Void MarkA() { f1 = 1; f2 = 1; }
            Void MarkB() { f1 = 2; f2 = 2; }
            Int Get() { return f2; }
        }
        """
    )
    result = visitors.SameFieldVisitor(("f1", "f2")).visit(game)
    assert isinstance(result, list), "genuinely-equal fields should still merge"
