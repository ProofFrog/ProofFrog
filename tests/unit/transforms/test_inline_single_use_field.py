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


def test_use_before_definition_not_inlined() -> None:
    """Field used BEFORE its assignment in the same method must NOT be inlined.

    The use at position 0 reads the field value from a *previous* invocation
    of the oracle.  Inlining would substitute the current call's expression,
    which is semantically wrong.
    """
    source = """
    Game Test() {
        Int field;
        Int Oracle(Int x) {
            Int y = field + x;
            field = x + 1;
            return y;
        }
    }
    """
    expected = source  # no change — inlining must be blocked
    _transform_and_compare(source, expected)


def test_use_before_definition_multiple_uses_not_inlined() -> None:
    """Field used both before and after its assignment must NOT be inlined."""
    source = """
    Game Test() {
        Int field;
        Int Oracle(Int x) {
            Int y = field + x;
            field = x + 1;
            Int z = field + 2;
            return y + z;
        }
    }
    """
    expected = source  # no change
    _transform_and_compare(source, expected)


def test_free_variable_reassigned_via_unique_sample_not_inlined() -> None:
    """If a free variable in the expression is reassigned via UniqueSample
    between definition and use, inlining must be blocked."""
    source = """
    Game Test(Int n) {
        Set<BitString<n>> S;
        BitString<n> field;
        BitString<n> Oracle() {
            BitString<n> r <- BitString<n>;
            field = r;
            BitString<n> r <-uniq[S] BitString<n>;
            return field;
        }
    }
    """
    # field must not be inlined because free var r is reassigned
    # via UniqueSample between def and use.
    expected = source
    _transform_and_compare(source, expected)


def test_no_inline_when_field_assigned_in_nested_block() -> None:
    """If a field is assigned at top level AND inside an if-branch in the
    same method, the shallow assignment count sees assign_count=1 and
    incorrectly allows inlining. The nested reassignment is missed, so
    fieldB gets the wrong value (42 instead of 99)."""
    source = """
    Game Test() {
        Int fieldA;
        Int fieldB;
        Int fieldC;
        Void Initialize() {
            fieldA = 42;
            fieldC = 0;
            if (fieldC == 0) {
                fieldA = 99;
            }
            fieldB = fieldA;
        }
        Int Query() {
            return fieldB;
        }
    }
    """
    # fieldA has 2 assignments: top-level (fieldA=42) and nested (fieldA=99).
    # The shallow scan only sees the top-level one. But inlining fieldA=42
    # into fieldB=fieldA would give fieldB=42, when at runtime fieldA is 99.
    # (fieldC may be inlined - that's fine; we only care that fieldA is not)
    expected = """
    Game Test() {
        Int fieldA;
        Int fieldB;
        Void Initialize() {
            fieldA = 42;
            if (0 == 0) {
                fieldA = 99;
            }
            fieldB = fieldA;
        }
        Int Query() {
            return fieldB;
        }
    }
    """
    _transform_and_compare(source, expected)
