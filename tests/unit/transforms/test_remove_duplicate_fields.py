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

    def test_copy_paired_different_initial_values_not_merged(self) -> None:
        """`b = a` pairs every write, but before any `Put` the fields hold
        different values."""
        assert not _merges("""
            Game G() {
                Int a = 0;
                Int b = 1;
                Void Put(Int k) {
                    a = k;
                    b = a;
                }
                Int Get() {
                    return b;
                }
            }
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


class TestUnpairedWrites:
    """The pass pairs only whole-field assignments and samples.  Any other
    write to a field changes it alone, so the pair is not merged."""

    @pytest.mark.parametrize(
        "the_type, write",
        [
            ("Map<Int, Int>", "A[k] = 1;"),
            ("Map<Int, BitString<8>>", "A[k] <- BitString<8>;"),
            ("Array<Int, 4>", "A[0] = 1;"),
            ("Array<Array<Int, 4>, 4>", "A[0][1] = 1;"),
            ("[Int, Int]", "A[0] = 1;"),
            ("Map<Int, Int>", "if (k == 0) { A[k] = 1; }"),
            # Paired element writes keep the fields equal, but the pass does
            # not pair them.
            ("Map<Int, Int>", "A[k] = 1; B[k] = 1;"),
        ],
    )
    def test_element_write_not_merged(self, the_type: str, write: str) -> None:
        assert not _merges(f"""
            Game G() {{
                {the_type} A;
                {the_type} B;
                Void Put(Int k) {{
                    {write}
                }}
                {the_type} Get() {{
                    return B;
                }}
            }}
            """)

    def test_element_write_in_initialize_not_merged(self) -> None:
        assert not _merges("""
            Game G() {
                Map<Int, Int> A;
                Map<Int, Int> B;
                Void Initialize() {
                    A[0] = 1;
                }
                Bool Has(Int k) {
                    return k in B;
                }
            }
            """)

    @pytest.mark.parametrize(
        "write",
        [
            "a <-uniq[S] BitString<8>;",
            "a <- BitString<8> \\ S;",
        ],
    )
    def test_exclusion_sample_not_merged(self, write: str) -> None:
        assert not _merges(f"""
            Game G() {{
                Set<BitString<8>> S;
                BitString<8> a;
                BitString<8> b;
                Void Draw() {{
                    {write}
                }}
                BitString<8> Get() {{
                    return b;
                }}
            }}
            """)

    def test_uniq_insertion_not_merged(self) -> None:
        """`x <-uniq[A] T` adds x to A."""
        assert not _merges("""
            Game G() {
                Set<BitString<8>> A;
                Set<BitString<8>> B;
                BitString<8> Draw() {
                    BitString<8> x <-uniq[A] BitString<8>;
                    return x;
                }
                Int Get() {
                    return |B|;
                }
            }
            """)

    @pytest.mark.parametrize(
        "body",
        [
            # A local of the same name: its write is not a field write.
            "Int a = 5; b = 5;",
            "Int a; a = 5; b = 5;",
            # A typed partner declares a local, so it does not pair.
            "a = 5; Int b = 5;",
            "a = 5; Int b = a;",
            # A loop binder of the kept name would capture the renamed reads.
            "for (Int a = 0 to 3) { s = s + b; }",
            "for (Int a in T) { s = s + b; }",
        ],
    )
    def test_rebinding_not_merged(self, body: str) -> None:
        """AlphaRename renames such locals first; the pass does not rely on
        it."""
        assert not _merges(f"""
            Game G() {{
                Int a;
                Int b;
                Set<Int> T;
                Void Initialize() {{
                    a = 0;
                    b = 0;
                }}
                Int Use() {{
                    Int s = 0;
                    {body}
                    return s + b;
                }}
            }}
            """)

    def test_parameter_of_either_name_not_merged(self) -> None:
        """Parameter `a` hides field `a` in `Put`, so `a = 1` writes the
        parameter and `Get` still returns 0."""
        assert not _merges("""
            Game G() {
                Int a = 0;
                Int b = 0;
                Void Put(Int a) {
                    a = 1;
                    b = 1;
                }
                Int Get() {
                    return a;
                }
            }
            """)

    @pytest.mark.parametrize(
        "write",
        [
            "M[k] = 1;",
            "BitString<8> x <-uniq[S] BitString<8>;",
            "BitString<8> x <- BitString<8> \\ A;",
            "for (Int i = 0 to 3) { M[i] = i; }",
        ],
    )
    def test_writes_to_other_fields_merged(self, write: str) -> None:
        assert _merges(f"""
            Game G() {{
                Map<Int, Int> M;
                Set<BitString<8>> S;
                Set<BitString<8>> A;
                Set<BitString<8>> B;
                Void Put(Int k) {{
                    {write}
                }}
                Int Get() {{
                    return |A| + |B|;
                }}
            }}
            """)


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

    def test_rejects_merge_of_copy_paired_fields_with_different_initializers(
        self,
    ) -> None:
        """Before any `Put`, `Get()` returns 1 in Left and 0 in Right."""
        assert not _engine_equal(
            """
            Game Left() {
                Int a = 0;
                Int b = 1;
                Void Put(Int k) {
                    a = k;
                    b = a;
                }
                Int Get() {
                    return b;
                }
            }
            """,
            """
            Game Right() {
                Int a = 0;
                Void Put(Int k) {
                    a = k;
                }
                Int Get() {
                    return a;
                }
            }
            """,
        )

    def test_initializer_near_miss_reaches_diagnosis(self) -> None:
        """The near miss is matched to the failing hop's diff hunks."""
        result = ProofEngine().check_equivalent(
            frog_parser.parse_game("""
                Game Left() {
                    Int h = 0;
                    Int n = 1;
                    Void Flip() {
                        h = h + 1;
                        n = n + 1;
                    }
                    Int Both() {
                        return n + h;
                    }
                }
                """),
            frog_parser.parse_game("""
                Game Right() {
                    Int h = 0;
                    Void Flip() {
                        h = h + 1;
                    }
                    Int Both() {
                        return h + 7;
                    }
                }
                """),
        )
        assert not result.valid
        assert result.diagnosis is not None
        assert any(
            "Fields 'h' and 'n' not merged" in explanation.reason
            for explanation in result.diagnosis.explanations
        )

    def test_rejects_merge_of_maps_written_by_element(self) -> None:
        """After `Put(0)`, `Get(0)` returns None in Left and 1 in Right."""
        game = """
            Game {side}() {{
                Map<Int, Int> A;
                Map<Int, Int> B;
                Void Put(Int k) {{
                    A[k] = 1;
                }}
                Int? Get(Int k) {{
                    if (k in {read}) {{
                        return {read}[k];
                    }}
                    return None;
                }}
            }}
            """
        assert not _engine_equal(
            game.format(side="Left", read="B"), game.format(side="Right", read="A")
        )

    def test_rejects_merge_of_sets_grown_by_uniq(self) -> None:
        """After `Draw()`, `Size()` returns 0 in Left and 1 in Right."""
        game = """
            Game {side}() {{
                Set<BitString<8>> A;
                Set<BitString<8>> B;
                BitString<8> Draw() {{
                    BitString<8> x <-uniq[A] BitString<8>;
                    return x;
                }}
                Int Size() {{
                    return |{read}|;
                }}
            }}
            """
        assert not _engine_equal(
            game.format(side="Left", read="B"), game.format(side="Right", read="A")
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
