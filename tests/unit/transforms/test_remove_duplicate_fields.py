import pytest
from proof_frog import proof_engine, frog_ast, frog_parser
from proof_frog.proof_engine import ProofEngine
from proof_frog.transforms.control_flow import RemoveStatementTransformer
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
    """The pass pairs whole-field assignments and samples, and matching
    element writes (``TestPairedElementWrites``).  Any other write to a field
    changes it alone, so the pair is not merged."""

    @pytest.mark.parametrize(
        "the_type, write",
        [
            ("Map<Int, Int>", "A[k] = 1;"),
            ("Map<Int, BitString<8>>", "A[k] <- BitString<8>;"),
            ("Array<Int, 4>", "A[0] = 1;"),
            ("Array<Array<Int, 4>, 4>", "A[0][1] = 1;"),
            ("[Int, Int]", "A[0] = 1;"),
            ("Map<Int, Int>", "if (k == 0) { A[k] = 1; }"),
            # A nested element write does not pair.
            ("Array<Array<Int, 4>, 4>", "A[0][1] = 1; B[0][1] = 1;"),
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


class TestPairedElementWrites:
    """`A[i] = v; ...; B[i] = v;` in one block keeps two equal fields equal
    when neither write makes a call, `i` and `v` read neither field, and
    nothing in between can return, uses either field, or changes what `i`
    or `v` reads."""

    @staticmethod
    def _game(put: str, the_type: str = "Map<Int, Int>") -> str:
        return f"""
            Game G() {{
                {the_type} A;
                {the_type} B;
                Int ell;
                Int Put(Int k, Int v, Bool b) {{
                    {put}
                    return 0;
                }}
                {the_type} Get() {{
                    return B;
                }}
            }}
            """

    @pytest.mark.parametrize(
        "put",
        [
            "A[k] = v;\nB[k] = v;",
            # Either field may come first.
            "B[k] = v;\nA[k] = v;",
            # Statements in between that touch neither field nor change
            # `k` or `v` (reading them is fine).
            "A[k] = v;\nInt y = k + v;\nell = y;\nB[k] = v;",
            # The shape a reduction's copy of a challenger table takes.
            "ell = ell + 1;\nA[ell] = v;\nB[ell] = v;",
            # Several pairs in a row, and a pair in a nested block.
            "A[k] = v;\nB[k] = v;\nA[v] = k;\nB[v] = k;",
            "if (b) {\nA[k] = v;\nB[k] = v;\n}",
            # A return before both writes skips both.
            "if (b) {\nreturn 1;\n}\nA[k] = v;\nB[k] = v;",
        ],
        ids=[
            "adjacent",
            "reversed",
            "unrelated_between",
            "counter_key",
            "two_pairs",
            "nested_block",
            "return_before_both",
        ],
    )
    def test_paired_element_writes_merged(self, put: str) -> None:
        assert _merges(self._game(put))

    def test_array_and_tuple_element_writes_merged(self) -> None:
        assert _merges(self._game("A[0] = v;\nB[0] = v;", "Array<Int, 4>"))
        assert _merges(self._game("A[1] = v;\nB[1] = v;", "[Int, Int]"))

    def test_merge_deletes_the_second_write(self) -> None:
        merged = remove_duplicate_fields(
            frog_parser.parse_game(self._game("A[k] = v;\nInt y = k;\nB[k] = v;"))
        )
        assert merged == frog_parser.parse_game("""
            Game G() {
                Map<Int, Int> A;
                Int ell;
                Int Put(Int k, Int v, Bool b) {
                    A[k] = v;
                    Int y = k;
                    return 0;
                }
                Map<Int, Int> Get() {
                    return A;
                }
            }
            """)

    @pytest.mark.parametrize(
        "put",
        [
            # Two calls may return different values: after Put, B[k] and
            # A[k] differ, which Get shows.
            "A[k] = S.F(v);\nB[k] = S.F(v);",
            # The second index reads A after the first write: Put(_, 5, _)
            # on empty maps sets A[0] and B[1].
            "A[|A|] = v;\nB[|A|] = v;",
            # The second value reads A after the first write: B[k] holds 1,
            # the merged A[k] holds 0.
            "A[k] = |A|;\nB[k] = |A|;",
            # The reply reads B between the writes: 0 on the first Put, but
            # 1 after the merge (B is A, already written).
            "A[k] = v;\nell = |B|;\nB[k] = v;",
            # A write to `v` in between: B[k] holds v + 1, A[k] holds v.
            "A[k] = v;\nv = v + 1;\nB[k] = v;",
            # A write to `k` in between: the writes go to different keys.
            "A[k] = v;\nk = k + 1;\nB[k] = v;",
            # A return in between: Put(_, _, true) writes A only.
            "A[k] = v;\nif (b) {\nreturn 1;\n}\nB[k] = v;",
            # Different blocks: Put(_, _, false) writes A only.
            "A[k] = v;\nif (b) {\nB[k] = v;\n}",
            # Different keys or values.
            "A[k] = v;\nB[v] = v;",
            "A[k] = v;\nB[k] = k;",
            # Another write to A in between (two pairs interleaved): not
            # modelled, so not merged, although A and B do end up equal.
            "A[k] = v;\nA[v] = k;\nB[k] = v;\nB[v] = k;",
        ],
        ids=[
            "call",
            "index_reads_field",
            "value_reads_field",
            "other_field_read_between",
            "value_written_between",
            "index_written_between",
            "return_between",
            "different_blocks",
            "different_key",
            "different_value",
            "interleaved",
        ],
    )
    def test_element_writes_not_merged(self, put: str) -> None:
        assert not _merges(self._game(put))

    @pytest.mark.parametrize(
        "put",
        [
            # An element write to a map the value reads: B[k] holds 1, the
            # merged A[k] holds M's old entry.
            "A[k] = M[0];\nM[0] = 1;\nB[k] = M[0];",
            # A local declared in between shadows the field `ell` the value
            # reads, so the second write stores 5.
            "A[k] = ell;\nInt ell = 5;\nB[k] = ell;",
        ],
        ids=["map_element_written_between", "read_field_shadowed_between"],
    )
    def test_change_to_what_the_write_reads_not_merged(self, put: str) -> None:
        assert not _merges(f"""
            Game G() {{
                Map<Int, Int> M;
                Map<Int, Int> A;
                Map<Int, Int> B;
                Int ell;
                Void Put(Int k) {{
                    {put}
                }}
                Map<Int, Int> Get() {{
                    return B;
                }}
            }}
            """)

    def test_one_partner_per_write(self) -> None:
        """F-299's rule for element writes: `B[k] = v;` alone in `Put2` is
        not paired by the structurally equal pair in `Put1`.  After
        `Put2(0, 1)`, B[0] is 1 and A has no key 0."""
        assert not _merges("""
            Game G() {
                Map<Int, Int> A;
                Map<Int, Int> B;
                Void Put1(Int k, Int v) {
                    A[k] = v;
                    B[k] = v;
                }
                Void Put2(Int k, Int v) {
                    B[k] = v;
                }
                Map<Int, Int> Get() {
                    return A;
                }
            }
            """)


class TestWritesBetweenPairedWrites:
    """`g = e; ...; f = e;` pairs only if nothing in between writes a
    variable that `e` reads, the receiver of a member access included."""

    @staticmethod
    def _game(value: str, write: str) -> str:
        return f"""
            Game G() {{
                Map<Int, Bool> M;
                Map<Int, Bool> N;
                Map<Int, Int> A;
                Int f;
                Int g;
                Void O() {{
                    g = {value};
                    {write}
                    f = {value};
                }}
                Int Get() {{
                    return f + g;
                }}
            }}
            """

    @staticmethod
    def _merges_f_and_g(source: str) -> bool:
        # Run to a fixed point: the pass merges one pair per call, and `M`
        # and `N` merge first when neither is written.
        game = frog_parser.parse_game(source)
        while True:
            merged = remove_duplicate_fields(game)
            if len(merged.fields) == len(game.fields):
                break
            game = merged
        names = {field.name for field in game.fields}
        return "f" not in names or "g" not in names

    @pytest.mark.parametrize(
        "value, write",
        [
            ("A[|M.keys|]", "M[7] = true;"),
            ("|M.keys|", "M[7] = true;"),
            ("|M.values| + 1", "M = N;"),
            ("A[|M.keys|]", "if (|N| == 0) { M[7] = true; }"),
            # The rest of the read set is still checked.
            ("A[|M.keys|]", "A[7] = 1;"),
        ],
    )
    def test_write_to_read_variable_not_merged(self, value: str, write: str) -> None:
        assert not self._merges_f_and_g(self._game(value, write))

    @pytest.mark.parametrize(
        "value, write",
        [
            ("A[|M.keys|]", ""),
            ("A[|M.keys|]", "N[7] = true;"),
            ("|M.keys|", "A[7] = 1;"),
        ],
    )
    def test_write_to_unread_variable_merged(self, value: str, write: str) -> None:
        assert self._merges_f_and_g(self._game(value, write))


class TestDeletesOnlyPairedWrites:
    """F-382: the merge deletes the second write of each pair it found, and
    no other statement, however equal it looks."""

    _MERGED = """
        Game G() {
            Int d;
            Void Initialize() {
                d = 0;
            }
            Void A0(Int z) {
                d = d + z;
            }
            Void A1(Int z) {
                d = d + z;
            }
            Int Get() {
                return d;
            }
        }
        """

    @staticmethod
    def _game(a0: str, a1: str) -> str:
        return f"""
            Game G() {{
                Int d;
                Int r;
                Void Initialize() {{
                    d = 0;
                    r = 0;
                }}
                Void A0(Int z) {{
                    {a0}
                }}
                Void A1(Int z) {{
                    {a1}
                }}
                Int Get() {{
                    return d;
                }}
            }}
            """

    @pytest.mark.parametrize(
        "a0, a1",
        [
            # Opposite orders: A0's second write `d = d + z;` equals A1's
            # first, and A1's second `r = r + z;` equals A0's first. A
            # structural match deleted all four and left both oracles empty.
            ("r = r + z; d = d + z;", "d = d + z; r = r + z;"),
            ("d = d + z; r = r + z;", "r = r + z; d = d + z;"),
            # Same order everywhere: the equal second writes are each paired
            # in their own oracle, so both go.
            ("r = r + z; d = d + z;", "r = r + z; d = d + z;"),
            ("d = d + z; r = r + z;", "d = d + z; r = r + z;"),
        ],
        ids=["opposite_r_first", "opposite_d_first", "same_r_first", "same_d_first"],
    )
    def test_each_method_keeps_one_write(self, a0: str, a1: str) -> None:
        source = self._game(a0, a1)
        game = frog_parser.parse_game(source)
        merged = remove_duplicate_fields(game)
        assert merged == frog_parser.parse_game(self._MERGED)
        assert game == frog_parser.parse_game(source)

    def test_remove_statement_transformer_matches_by_identity(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                Int d;
                Void A0(Int z) {
                    d = d + z;
                }
                Void A1(Int z) {
                    d = d + z;
                    if (z == 0) {
                        d = d + z;
                    }
                }
            }
            """)
        a0_write = game.methods[0].block.statements[0]
        branch = game.methods[1].block.statements[1]
        assert isinstance(branch, frog_ast.IfStatement)
        nested_write = branch.blocks[0].statements[0]
        assert a0_write == nested_write and a0_write is not nested_write

        result = RemoveStatementTransformer([nested_write]).transform(game)

        assert result.methods[0].block.statements == [a0_write]
        assert result.methods[1].block.statements[0] == a0_write
        result_branch = result.methods[1].block.statements[1]
        assert isinstance(result_branch, frog_ast.IfStatement)
        assert not result_branch.blocks[0].statements
        # Copy-on-write: the input keeps the removed statement.
        assert branch.blocks[0].statements == [nested_write]


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

    def test_accepts_merge_of_maps_written_by_paired_elements(self) -> None:
        assert _engine_equal(
            """
            Game Left() {
                Map<Int, Int> A;
                Map<Int, Int> B;
                Int ell;
                Int Put(Int v) {
                    ell = ell + 1;
                    A[ell] = v;
                    B[ell] = v;
                    return ell;
                }
                Int? Get(Int k) {
                    if (k in B) {
                        return B[k];
                    }
                    return None;
                }
            }
            """,
            """
            Game Right() {
                Map<Int, Int> A;
                Int ell;
                Int Put(Int v) {
                    ell = ell + 1;
                    A[ell] = v;
                    return ell;
                }
                Int? Get(Int k) {
                    if (k in A) {
                        return A[k];
                    }
                    return None;
                }
            }
            """,
        )

    def test_rejects_merge_when_index_reads_the_field(self) -> None:
        """`Put(5)` on empty maps sets A[0] and B[1], so `Get(1)` returns 5
        in Left and None in Right."""
        game = """
            Game {side}() {{
                Map<Int, Int> A;
                Map<Int, Int> B;
                Void Put(Int v) {{
                    A[|A|] = v;
                    B[|A|] = v;
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
