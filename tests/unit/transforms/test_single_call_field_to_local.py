import pytest
from proof_frog import frog_parser
from proof_frog.transforms.sampling import _single_call_field_to_local


@pytest.mark.parametrize(
    "game,expected",
    [
        # Basic case: field sampled in Initialize, used in one oracle
        (
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m + k;
            }
        }""",
            """
        Game Test() {
            Void Initialize() {
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                BitString<lambda> k <- BitString<lambda>;
                return m + k;
            }
        }""",
        ),
        # Multiple fields, both eligible
        (
            """
        Game Test() {
            BitString<lambda> k;
            BitString<lambda> r;
            Void Initialize() {
                k <- BitString<lambda>;
                r <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m + k + r;
            }
        }""",
            """
        Game Test() {
            Void Initialize() {
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                BitString<lambda> k <- BitString<lambda>;
                BitString<lambda> r <- BitString<lambda>;
                return m + k + r;
            }
        }""",
        ),
        # Field used in two oracles: no transformation
        (
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> Enc(BitString<lambda> m) {
                return m + k;
            }
            BitString<lambda> Dec(BitString<lambda> c) {
                return c + k;
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> Enc(BitString<lambda> m) {
                return m + k;
            }
            BitString<lambda> Dec(BitString<lambda> c) {
                return c + k;
            }
        }""",
        ),
        # Field is assigned (not sampled) in Initialize: no transformation
        (
            """
        Game Test() {
            Int k;
            Void Initialize() {
                k = 42;
            }
            Int CTXT() {
                return k;
            }
        }""",
            """
        Game Test() {
            Int k;
            Void Initialize() {
                k = 42;
            }
            Int CTXT() {
                return k;
            }
        }""",
        ),
        # Field is written to in the oracle: no transformation
        (
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                BitString<lambda> result = m + k;
                k <- BitString<lambda>;
                return result;
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                BitString<lambda> result = m + k;
                k <- BitString<lambda>;
                return result;
            }
        }""",
        ),
        # FunctionType field: skip (structured type)
        (
            """
        Game Test() {
            Function<BitString<lambda>, BitString<lambda>> RF;
            Void Initialize() {
                RF <- Function<BitString<lambda>, BitString<lambda>>;
            }
            BitString<lambda> CTXT(BitString<lambda> r) {
                BitString<lambda> z = RF(r);
                return z;
            }
        }""",
            """
        Game Test() {
            Function<BitString<lambda>, BitString<lambda>> RF;
            Void Initialize() {
                RF <- Function<BitString<lambda>, BitString<lambda>>;
            }
            BitString<lambda> CTXT(BitString<lambda> r) {
                BitString<lambda> z = RF(r);
                return z;
            }
        }""",
        ),
        # SetType field: skip (structured type)
        (
            """
        Game Test() {
            Set<BitString<lambda>> S;
            Void Initialize() {
                S <- Set<BitString<lambda>>;
            }
            BitString<lambda> CTXT() {
                BitString<lambda> x <-uniq[S] BitString<lambda>;
                return x;
            }
        }""",
            """
        Game Test() {
            Set<BitString<lambda>> S;
            Void Initialize() {
                S <- Set<BitString<lambda>>;
            }
            BitString<lambda> CTXT() {
                BitString<lambda> x <-uniq[S] BitString<lambda>;
                return x;
            }
        }""",
        ),
        # No Initialize method: no transformation
        (
            """
        Game Test() {
            BitString<lambda> k;
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m + k;
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m + k;
            }
        }""",
        ),
        # Field used elsewhere in Initialize (not just the sample): no transformation
        (
            """
        Game Test() {
            BitString<lambda> k;
            BitString<lambda> stored;
            Void Initialize() {
                k <- BitString<lambda>;
                stored = k;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m + k;
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            BitString<lambda> stored;
            Void Initialize() {
                k <- BitString<lambda>;
                stored = k;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m + k;
            }
        }""",
        ),
        # Field not referenced in any oracle: no transformation
        (
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m;
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m;
            }
        }""",
        ),
        # Mix of eligible and ineligible fields
        (
            """
        Game Test() {
            BitString<lambda> k;
            Function<BitString<lambda>, BitString<lambda>> RF;
            Void Initialize() {
                k <- BitString<lambda>;
                RF <- Function<BitString<lambda>, BitString<lambda>>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                BitString<lambda> z = RF(m);
                return z + k;
            }
        }""",
            """
        Game Test() {
            Function<BitString<lambda>, BitString<lambda>> RF;
            Void Initialize() {
                RF <- Function<BitString<lambda>, BitString<lambda>>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                BitString<lambda> k <- BitString<lambda>;
                BitString<lambda> z = RF(m);
                return z + k;
            }
        }""",
        ),
        # Field with typed sample in Initialize (the_type is not None): no transformation
        # This tests that we only match bare field samples (no type declaration)
        (
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                BitString<lambda> k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m + k;
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                BitString<lambda> k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m + k;
            }
        }""",
        ),
        # Field sampled twice in Initialize: no transformation
        # (regression: second sample overwrites init_sample_idx, only removing
        # the second and leaving a dangling first sample)
        (
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
                k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m + k;
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
                k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                return m + k;
            }
        }""",
        ),
        # Field is written to inside an if-branch in the oracle: no transformation
        # (regression: shallow _is_assigned_in missed nested assignments)
        (
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                BitString<lambda> result = m + k;
                if (m == m) {
                    k <- BitString<lambda>;
                }
                return result;
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> CTXT(BitString<lambda> m) {
                BitString<lambda> result = m + k;
                if (m == m) {
                    k <- BitString<lambda>;
                }
                return result;
            }
        }""",
        ),
    ],
)
def test_single_call_field_to_local(
    game: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)

    transformed_ast = _single_call_field_to_local(game_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert transformed_ast == expected_ast
