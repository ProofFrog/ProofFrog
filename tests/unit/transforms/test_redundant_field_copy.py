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
