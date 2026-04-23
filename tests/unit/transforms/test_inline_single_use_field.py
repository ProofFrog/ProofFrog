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
        # Basic: ct_PQ inlined within Initialize, then field4 cross-method
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
                Void Initialize() {
                }
                Int PK() {
                    return 42;
                }
                Int CT() {
                    return 42;
                }
            }
            """,
        ),
        # Field used in expression — cascades to cross-method
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
                Void Initialize() {
                }
                Int PK() {
                    return 42 + 1;
                }
                Int CT() {
                    return 42 + 1;
                }
            }
            """,
        ),
        # Pure field used in two places — cascades
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
                Void Initialize() {
                }
                Int PK() {
                    return 42 + 1 + 42;
                }
                Int CT() {
                    return 42 + 1 + 42;
                }
            }
            """,
        ),
        # Pure field used across methods with no free vars
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
                Void Initialize() {
                }
                Int PK() {
                    return 42 + 42;
                }
                Int CT() {
                    return 42;
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
        # Non-pure expression: field4 aliases ct_PQ cross-method,
        # ct_PQ (non-pure, multi-use) stays
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
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = F.evaluate(1);
                }
                Int PK() {
                    return ct_PQ;
                }
                Int CT() {
                    return ct_PQ;
                }
            }
            """,
        ),
        # Free variable modified between def and use — field4 aliases ct_PQ
        # cross-method (ct_PQ stable); field3 NOT cross-method (use-before-def)
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
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = field3 + 1;
                    field3 = 99;
                }
                Int PK() {
                    return ct_PQ + field3;
                }
                Int CT() {
                    return ct_PQ + field3;
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
        # Pure expression used twice — cascades fully
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
                Void Initialize() {
                }
                Int PK() {
                    return 42 + 1 + 42;
                }
                Int CT() {
                    return 42 + 1 + 42;
                }
            }
            """,
        ),
        # Non-pure expression: field3/field4 alias ct_PQ cross-method
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
                Int ct_PQ;
                Void Initialize() {
                    ct_PQ = F.evaluate(1);
                }
                Int PK() {
                    return ct_PQ + 1 + ct_PQ;
                }
                Int CT() {
                    return ct_PQ + 1 + ct_PQ;
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


def test_cross_method_pure_field_referencing_field() -> None:
    """A pure field used across methods where the expression's free variables
    are all fields should be inlined — cascades fully."""
    source = """
    Game Test() {
        Int fieldA;
        Int fieldB;
        Void Initialize() {
            fieldA = 42;
            fieldB = fieldA + 1;
        }
        Int Query() {
            return fieldB;
        }
    }
    """
    expected = """
    Game Test() {
        Void Initialize() {
        }
        Int Query() {
            return 42 + 1;
        }
    }
    """
    _transform_and_compare(source, expected)


def test_cross_method_field_referencing_local_not_inlined() -> None:
    """A field used across methods whose expression references a local
    variable (not a field) is NOT inlined unless the local-promotion
    branch fires.  With the concat-shape gate, promotion only applies
    to bitstring-concatenation RHS; this pure-arithmetic case does not
    qualify, so the game is unchanged."""
    source = """
    Game Test() {
        Int fieldB;
        Void Initialize() {
            Int x = 42;
            fieldB = x + 1;
        }
        Int Query() {
            return fieldB;
        }
    }
    """
    expected = source  # no change
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
