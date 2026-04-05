import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import RedundantFieldCopyTransformer


@pytest.mark.parametrize(
    "game,expected",
    [
        # Core case: local only used in field copy, should be inlined
        (
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                Int v <- Int;
                field1 = v;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                field1 <- Int;
            }
        }""",
        ),
        # Local used in field copy AND return — must NOT inline
        # (would leave dangling reference)
        (
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v <- Int;
                field1 = v;
                return v;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v <- Int;
                field1 = v;
                return v;
            }
        }""",
        ),
        # Local used in field copy AND another expression — must NOT inline
        (
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v = challenger.g();
                field1 = v;
                return v + 1;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v = challenger.g();
                field1 = v;
                return v + 1;
            }
        }""",
        ),
        # Assignment (not sample) — local only used in field copy
        (
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v = 42;
                field1 = v;
                return field1;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                field1 = 42;
                return field1;
            }
        }""",
        ),
        # RHS is a field, not a local — should NOT transform
        (
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 5;
                field2 = field1;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 5;
                field2 = field1;
            }
        }""",
        ),
        # Field READ between decl and assignment — must NOT inline.
        # In original: field2 = field1 reads old value of field1.
        # If transformed, field1 gets new value before field2 = field1.
        (
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                Int v <- Int;
                field2 = field1;
                field1 = v;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                Int v <- Int;
                field2 = field1;
                field1 = v;
            }
        }""",
        ),
        # Field WRITE between decl and assignment — must NOT inline.
        # In original: field1 ends up with v's value. If transformed,
        # field1 <- Int then field1 = 42 overwrites it.
        (
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                Int v <- Int;
                field1 = 42;
                field1 = v;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                Int v <- Int;
                field1 = 42;
                field1 = v;
            }
        }""",
        ),
        # Duplicate field assignment — v is used in another identical
        # statement, so removing the declaration would leave a dangling
        # reference. The structural-equality skip must not mask this.
        (
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                Int v <- Int;
                field1 = v;
                field1 = v;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                Int v <- Int;
                field1 = v;
                field1 = v;
            }
        }""",
        ),
        # UniqueSample — local only used in field copy, should be inlined
        (
            """
        Game Test() {
            Int field1;
            Set<Int> S;
            Void Initialize() {
                Int v <-uniq[S] Int;
                field1 = v;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Set<Int> S;
            Void Initialize() {
                field1 <-uniq[S] Int;
            }
        }""",
        ),
        # UniqueSample — local used elsewhere, must NOT inline
        (
            """
        Game Test() {
            Int field1;
            Set<Int> S;
            Int Initialize() {
                Int v <-uniq[S] Int;
                field1 = v;
                return v;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Set<Int> S;
            Int Initialize() {
                Int v <-uniq[S] Int;
                field1 = v;
                return v;
            }
        }""",
        ),
    ],
)
def test_redundant_field_copy(
    game: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)

    transformed_ast = RedundantFieldCopyTransformer().transform(game_ast)
    assert transformed_ast == expected_ast
