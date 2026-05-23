"""Parse -> unparse -> parse -> unparse fixed-point tests for every
new surface form introduced on the ``dev`` branch.

Each case feeds a minimal source through one round-trip; the second
unparse must equal the first. This catches both straight loss-of-info
in the unparser and AST shapes that re-parse to a different tree.
"""

from proof_frog import frog_ast, frog_parser


def _roundtrip_idempotent_proof(src: str) -> None:
    ast1 = frog_parser.parse_string(src, frog_ast.FileType.PROOF)
    text1 = str(ast1)
    ast2 = frog_parser.parse_string(text1, frog_ast.FileType.PROOF)
    text2 = str(ast2)
    assert text1 == text2, f"\n--- text1 ---\n{text1}\n--- text2 ---\n{text2}"


def _roundtrip_idempotent_game(src: str) -> None:
    method = frog_parser.parse_method(src)
    text1 = str(method)
    method2 = frog_parser.parse_method(text1)
    text2 = str(method2)
    assert text1 == text2, f"\n--- text1 ---\n{text1}\n--- text2 ---\n{text2}"


_PROOF_PREAMBLE = """
Game Dummy(Group G) {
    BitString<1> Oracle() {
        return 0^1;
    }
}

proof:
let:
    Group G;
assume:

"""


_PROOF_TAIL = """
theorem:
    Dummy(G);

games:
    Dummy(G) against Dummy(G).Adversary;
"""


def test_requires_prime_roundtrip() -> None:
    _roundtrip_idempotent_proof(
        _PROOF_PREAMBLE + "requires:\n    G.order is prime;\n" + _PROOF_TAIL
    )


def test_requires_multiple_entries_roundtrip() -> None:
    _roundtrip_idempotent_proof(
        _PROOF_PREAMBLE
        + "requires:\n    G.order is prime;\n    G.order is prime;\n"
        + _PROOF_TAIL
    )


def test_set_minus_sample_with_type_roundtrip() -> None:
    _roundtrip_idempotent_game(
        """
        BitString<8> f() {
            Set<BitString<8>> S = {};
            BitString<8> x <- BitString<8> \\ S;
            return x;
        }
        """
    )


def test_set_minus_sample_without_type_roundtrip() -> None:
    _roundtrip_idempotent_game(
        """
        BitString<8> f(BitString<8> x) {
            Set<BitString<8>> S = {};
            x <- BitString<8> \\ S;
            return x;
        }
        """
    )


def test_generic_for_over_array_roundtrip() -> None:
    _roundtrip_idempotent_game(
        """
        Int f(Array<Int, 4> arr) {
            Int total = 0;
            for (Int x in arr) {
                total = total + x;
            }
            return total;
        }
        """
    )


def test_generic_for_over_map_keys_roundtrip() -> None:
    _roundtrip_idempotent_game(
        """
        Int f(Map<Int, Bool> M) {
            Int n = 0;
            for (Int k in M.keys) {
                n = n + 1;
            }
            return n;
        }
        """
    )


def test_generic_for_over_map_values_roundtrip() -> None:
    _roundtrip_idempotent_game(
        """
        Int f(Map<Int, Bool> M) {
            Int n = 0;
            for (Bool v in M.values) {
                n = n + 1;
            }
            return n;
        }
        """
    )


def test_generic_for_over_map_entries_roundtrip() -> None:
    _roundtrip_idempotent_game(
        """
        Int f(Map<Int, Bool> M) {
            Int n = 0;
            for ([Int, Bool] e in M.entries) {
                n = n + 1;
            }
            return n;
        }
        """
    )
