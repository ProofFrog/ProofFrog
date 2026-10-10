import pytest
from proof_frog import proof_engine, frog_parser
from proof_frog.proof_engine import ProofEngine
from proof_frog.transforms.structural import remove_duplicate_fields


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 100;
                field2 = field1;
            }
            Int f() {
                Int value = field1 + field2;
                return value;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                field1 = 100;
            }
            Int f() {
                Int value = field1 + field1;
                return value;
            }
        }""",
        ),
        (
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 100;
                field2 = field1;
            }
            Int f() {
                field1 = 200;
                Int value = field1 + field2;
                return value;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 100;
                field2 = field1;
            }
            Int f() {
                field1 = 200;
                Int value = field1 + field2;
                return value;
            }
        }""",
        ),
        (
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 100;
                field2 = field1;
            }
            Int f() {
                field2 = 200;
                Int value = field1 + field2;
                return value;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 100;
                field2 = field1;
            }
            Int f() {
                field2 = 200;
                Int value = field1 + field2;
                return value;
            }
        }""",
        ),
        (
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                field1 = 100;
                field1 = field1;
            }
            Int f() {
                Int value = 2 * field1;
                return value;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                field1 = 100;
                field1 = field1;
            }
            Int f() {
                Int value = 2 * field1;
                return value;
            }
        }""",
        ),
        (
            """
        Game Test() {
            BitString field1;
            BitString field2;
            BitString Initialize() {
                field1 <- BitString;
                field2 <- BitString;
                return field1;
            }
        }""",
            """
        Game Test() {
            BitString field1;
            BitString field2;
            BitString Initialize() {
                field1 <- BitString;
                field2 <- BitString;
                return field1;
            }
        }""",
        ),
        # Direct field copy after function call: field1 = f(); field2 = field1
        # should be merged (the copy is safe, doesn't replicate the call)
        (
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = challenger.g();
                field2 = field1;
            }
            Int f() {
                return field1 + field2;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                field1 = challenger.g();
            }
            Int f() {
                return field1 + field1;
            }
        }""",
        ),
        # Two independent function calls should NOT be merged
        (
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = challenger.g();
                field2 = challenger.g();
            }
            Int f() {
                return field1 + field2;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = challenger.g();
                field2 = challenger.g();
            }
            Int f() {
                return field1 + field2;
            }
        }""",
        ),
    ],
)
def test_remove_duplicate_fields(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(method)
    expected_ast = frog_parser.parse_game(expected)

    print("EXPECTED", expected_ast)
    transformed_ast = proof_engine.remove_duplicate_fields(game_ast)
    print("TRANSFORMED", transformed_ast)
    assert transformed_ast == expected_ast


def _merges(source: str) -> bool:
    game = frog_parser.parse_game(source)
    return len(remove_duplicate_fields(game).fields) < len(game.fields)


def _engine_equal(left: str, right: str) -> bool:
    return (
        ProofEngine()
        .check_equivalent(frog_parser.parse_game(left), frog_parser.parse_game(right))
        .valid
    )


class TestInitialValues:
    """Two fields every write updates alike are duplicates only if they also
    start equal."""

    @pytest.mark.parametrize(
        "fields",
        [
            # The reproducer: `Flip` toggles both, so they never meet.
            "BitString<1> h = 0b0; BitString<1> n = 0b1;",
            "BitString<1> h = 0b0; BitString<1> n;",
            "BitString<1> h; BitString<1> n = 0b1;",
        ],
    )
    def test_different_initial_values_not_merged(self, fields: str) -> None:
        assert not _merges(f"""
            Game G() {{
                {fields}
                Void Flip() {{
                    h = h + 0b1;
                    n = n + 0b1;
                }}
                BitString<1> Get() {{
                    return n;
                }}
            }}
            """)

    def test_initializers_that_call_not_merged(self) -> None:
        """Each initializer's call may return a different value."""
        assert not _merges("""
            Game G() {
                Int a = S.F();
                Int b = S.F();
                Int Get() {
                    return a - b;
                }
            }
            """)

    def test_initialize_writing_one_field_not_merged(self) -> None:
        assert not _merges("""
            Game G() {
                Int a = 0;
                Int b = 0;
                Void Initialize() {
                    a = 1;
                }
                Int Get() {
                    return b;
                }
            }
            """)

    def test_initialize_writing_different_values_not_merged(self) -> None:
        assert not _merges("""
            Game G() {
                Int a;
                Int b;
                Void Initialize() {
                    a = 0;
                    b = 1;
                }
                Int Get() {
                    return b;
                }
            }
            """)

    def test_initialize_overwriting_different_initializers_not_merged(self) -> None:
        """Sound to merge, since Initialize runs first, but the pass does not
        reason about Initialize order and declines."""
        assert not _merges("""
            Game G() {
                Int a = 0;
                Int b = 1;
                Void Initialize() {
                    a = 5;
                    b = 5;
                }
                Int Get() {
                    return b;
                }
            }
            """)

    @pytest.mark.parametrize(
        "fields",
        [
            "BitString<1> h = 0b0; BitString<1> n = 0b0;",
            "BitString<1> h; BitString<1> n;",
            "BitString<1> h = 0^1; BitString<1> n = 0^1;",
        ],
    )
    def test_equal_initial_values_merged(self, fields: str) -> None:
        assert _merges(f"""
            Game G() {{
                {fields}
                Void Flip() {{
                    h = h + 0b1;
                    n = n + 0b1;
                }}
                BitString<1> Get() {{
                    return n;
                }}
            }}
            """)

    def test_equal_initializers_reading_a_parameter_merged(self) -> None:
        assert _merges("""
            Game G(Int lambda) {
                Int a = lambda;
                Int b = lambda;
                Int Get() {
                    return a + b;
                }
            }
            """)

    def test_counters_set_in_initialize_merged(self) -> None:
        """Two counters with no initializer that Initialize sets to 0 and
        nothing else uses."""
        game = frog_parser.parse_game("""
            Game G() {
                Int primSealsI;
                Int primSealsR;
                Bool closed;
                Int primOpensI;
                Void Initialize() {
                    primSealsI = 0;
                    primSealsR = 1;
                    closed = false;
                    primOpensI = 0;
                }
                Bool Close() {
                    closed = true;
                    return closed;
                }
            }
            """)
        result = remove_duplicate_fields(game)
        assert [field.name for field in result.fields] == [
            "primSealsR",
            "closed",
            "primOpensI",
        ]


class TestEndToEnd:
    def test_rejects_merge_of_fields_with_different_initializers(self) -> None:
        """After `Flip()`, `Both()` returns [0b0, 0b0] in Left and
        [0b0, 0b1] in Right."""
        assert not _engine_equal(
            """
            Game Left() {
                BitString<1> h = 0b0;
                BitString<1> n = 0b1;
                Void Initialize() {
                }
                Void Flip() {
                    h = h + 0b1;
                    n = n + 0b1;
                }
                [BitString<1>, BitString<1>] Both() {
                    return [0^1, n];
                }
            }
            """,
            """
            Game Right() {
                BitString<1> h = 0b0;
                Void Initialize() {
                }
                Void Flip() {
                    h = h + 0b1;
                }
                [BitString<1>, BitString<1>] Both() {
                    return [0^1, h];
                }
            }
            """,
        )

    def test_accepts_merge_of_fields_with_equal_initializers(self) -> None:
        assert _engine_equal(
            """
            Game Left() {
                BitString<1> h = 0b0;
                BitString<1> n = 0b0;
                Void Flip() {
                    h = h + 0b1;
                    n = n + 0b1;
                }
                BitString<1> Get() {
                    return n;
                }
            }
            """,
            """
            Game Right() {
                BitString<1> h = 0b0;
                Void Flip() {
                    h = h + 0b1;
                }
                BitString<1> Get() {
                    return h;
                }
            }
            """,
        )
