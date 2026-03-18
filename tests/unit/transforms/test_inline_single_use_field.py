import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import InlineSingleUseFieldTransformer


def _transform_and_compare(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = InlineSingleUseFieldTransformer().transform(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "source,expected",
    [
        # Basic: field ct_PQ assigned once, used once in another field assignment
        (
            """
            Game Test() {
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = 42;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return field4;
                }
                Int CT() {
                    return field4;
                }
            }
            """,
            """
            Game Test() {
                Int field4;
                Void Initialize() {
                    field4 = 42;
                }
                Int PK() {
                    return field4;
                }
                Int CT() {
                    return field4;
                }
            }
            """,
        ),
        # Field used in expression (not just plain copy)
        (
            """
            Game Test() {
                Int field3;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = 42;
                    field3 = ct_PQ + 1;
                }
                Int PK() {
                    return field3;
                }
                Int CT() {
                    return field3;
                }
            }
            """,
            """
            Game Test() {
                Int field3;
                Void Initialize() {
                    field3 = 42 + 1;
                }
                Int PK() {
                    return field3;
                }
                Int CT() {
                    return field3;
                }
            }
            """,
        ),
        # Pure field used in two places within same method — SHOULD be inlined
        (
            """
            Game Test() {
                Int field3;
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = 42;
                    field3 = ct_PQ + 1;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return field3 + field4;
                }
                Int CT() {
                    return field3 + field4;
                }
            }
            """,
            """
            Game Test() {
                Int field3;
                Int field4;
                Void Initialize() {
                    field3 = 42 + 1;
                    field4 = 42;
                }
                Int PK() {
                    return field3 + field4;
                }
                Int CT() {
                    return field3 + field4;
                }
            }
            """,
        ),
        # Field used across methods — should NOT be inlined
        (
            """
            Game Test() {
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = 42;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return ct_PQ + field4;
                }
                Int CT() {
                    return field4;
                }
            }
            """,
            """
            Game Test() {
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = 42;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return ct_PQ + field4;
                }
                Int CT() {
                    return field4;
                }
            }
            """,
        ),
        # Field assigned multiple times — should NOT be inlined
        (
            """
            Game Test() {
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = 1;
                    ct_PQ = 2;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return field4;
                }
                Int CT() {
                    return field4;
                }
            }
            """,
            """
            Game Test() {
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = 1;
                    ct_PQ = 2;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return field4;
                }
                Int CT() {
                    return field4;
                }
            }
            """,
        ),
        # Expression with function call — still inlinable if single use
        (
            """
            Game Test() {
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = F.evaluate(1);
                    field4 = ct_PQ;
                }
                Int PK() {
                    return field4;
                }
                Int CT() {
                    return field4;
                }
            }
            """,
            """
            Game Test() {
                Int field4;
                Void Initialize() {
                    field4 = F.evaluate(1);
                }
                Int PK() {
                    return field4;
                }
                Int CT() {
                    return field4;
                }
            }
            """,
        ),
        # Free variable modified between def and use — should NOT be inlined
        (
            """
            Game Test() {
                Int field3;
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = field3 + 1;
                    field3 = 99;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return field4 + field3;
                }
                Int CT() {
                    return field4 + field3;
                }
            }
            """,
            """
            Game Test() {
                Int field3;
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = field3 + 1;
                    field3 = 99;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return field4 + field3;
                }
                Int CT() {
                    return field4 + field3;
                }
            }
            """,
        ),
    ],
)
def test_inline_single_use_field(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)


@pytest.mark.parametrize(
    "source,expected",
    [
        # Pure expression (tuple index) used twice in same method — should be inlined
        (
            """
            Game Test() {
                Int field3;
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = 42;
                    field3 = ct_PQ + 1;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return field3 + field4;
                }
                Int CT() {
                    return field3 + field4;
                }
            }
            """,
            """
            Game Test() {
                Int field3;
                Int field4;
                Void Initialize() {
                    field3 = 42 + 1;
                    field4 = 42;
                }
                Int PK() {
                    return field3 + field4;
                }
                Int CT() {
                    return field3 + field4;
                }
            }
            """,
        ),
        # Non-pure expression (function call) used twice — should NOT be inlined
        (
            """
            Game Test() {
                Int field3;
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = F.evaluate(1);
                    field3 = ct_PQ + 1;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return field3 + field4;
                }
                Int CT() {
                    return field3 + field4;
                }
            }
            """,
            """
            Game Test() {
                Int field3;
                Int field4;
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = F.evaluate(1);
                    field3 = ct_PQ + 1;
                    field4 = ct_PQ;
                }
                Int PK() {
                    return field3 + field4;
                }
                Int CT() {
                    return field3 + field4;
                }
            }
            """,
        ),
    ],
)
def test_inline_multi_use_pure_field(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)


def test_inline_orphaned_untyped_variable() -> None:
    """An untyped assignment to a variable NOT in the fields list should be
    inlined — this happens when RemoveUnnecessaryFields removes a field
    declaration but leaves the assignment statement."""
    source = """
    Game Test() {
        Int field4;
        Void Initialize() {
            ct_PQ = K.evaluate(1);
            field4 = ct_PQ;
        }
        Int PK() {
            return field4;
        }
        Int CT() {
            return field4;
        }
    }
    """
    expected = """
    Game Test() {
        Int field4;
        Void Initialize() {
            field4 = K.evaluate(1);
        }
        Int PK() {
            return field4;
        }
        Int CT() {
            return field4;
        }
    }
    """
    _transform_and_compare(source, expected)
