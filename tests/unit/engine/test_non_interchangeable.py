"""Negative tests: games that should NOT canonicalize to uniform.

These correspond to Chapter 2 exercises from Joy of Cryptography where
the distributions are NOT interchangeable with uniform. Each test verifies
the engine does not incorrectly simplify them.
"""

from sympy import Symbol
from proof_frog import frog_parser, proof_engine


def _make_engine() -> proof_engine.ProofEngine:
    engine = proof_engine.ProofEngine(verbose=False)
    engine.variables["lambda"] = Symbol("lambda")
    return engine


def _parse_uniform(size: str) -> proof_engine.frog_ast.Game:
    return frog_parser.parse_game(f"""
    Game Uniform() {{
        BitString<{size}> SAMPLE() {{
            BitString<{size}> r <- BitString<{size}>;
            return r;
        }}
    }}
    """)


def test_exercise_2_9a_triple_xor_closed() -> None:
    """(A + B) || (B + C) || (C + A) must NOT canonicalize to uniform 3n bits.

    The three components XOR to zero, so they are not jointly uniform.
    """
    game = frog_parser.parse_game("""
    Game G() {
        BitString<3 * lambda> SAMPLE() {
            BitString<lambda> a <- BitString<lambda>;
            BitString<lambda> b <- BitString<lambda>;
            BitString<lambda> c <- BitString<lambda>;
            return (a + b) || (b + c) || (c + a);
        }
    }
    """)
    engine = _make_engine()
    canonical = engine.canonicalize_game(game)
    canonical_uniform = engine.canonicalize_game(_parse_uniform("3 * lambda"))
    assert canonical != canonical_uniform, (
        "Exercise 2.9a: (A+B)||(B+C)||(C+A) should NOT be interchangeable with "
        "uniform — the three components XOR to zero"
    )


def test_exercise_2_25a_append_zero_not_ror() -> None:
    """c || 0^1 must NOT canonicalize to uniform (n+1)-bit string.

    The last bit is always 0, so the output is distinguishable from uniform.
    """
    game = frog_parser.parse_game("""
    Game G() {
        BitString<lambda + 1> SAMPLE() {
            BitString<lambda> c <- BitString<lambda>;
            return c || 0^1;
        }
    }
    """)
    engine = _make_engine()
    canonical = engine.canonicalize_game(game)
    canonical_uniform = engine.canonicalize_game(_parse_uniform("lambda + 1"))
    assert canonical != canonical_uniform, (
        "Exercise 2.25a: c||0 should NOT be interchangeable with uniform "
        "— the last bit is always 0"
    )


def test_exercise_2_26a_double_ciphertext_not_ror() -> None:
    """c || c must NOT canonicalize to uniform 2n bits.

    The two halves are always equal, so the output is distinguishable from uniform.
    """
    game = frog_parser.parse_game("""
    Game G() {
        BitString<2 * lambda> SAMPLE() {
            BitString<lambda> c <- BitString<lambda>;
            return c || c;
        }
    }
    """)
    engine = _make_engine()
    canonical = engine.canonicalize_game(game)
    canonical_uniform = engine.canonicalize_game(_parse_uniform("2 * lambda"))
    assert canonical != canonical_uniform, (
        "Exercise 2.26a: c||c should NOT be interchangeable with uniform "
        "— the two halves are always equal"
    )


def test_early_return_guard_is_a_reorder_barrier() -> None:
    """A side-effecting assignment must not be reordered past an early
    return inside an if-statement.

    Left:  on z == target, returns ssStar without modifying T.
           Repeated calls always return ssStar.
    Right: on z == target, inserts T[z] = h FIRST then returns ssStar.
           Repeated calls return T[z] = h, not ssStar.

    These games are observably distinct (the adversary can call Hash(z)
    twice on the same z and compare the results). Canonicalizing them
    to the same form would be unsound.
    """
    left = frog_parser.parse_game("""
    Game Left() {
        BitString<8> ssStar;
        BitString<8> target;
        Map<BitString<8>, BitString<8>> T;

        Void Initialize() {
            ssStar <- BitString<8>;
            target <- BitString<8>;
        }

        BitString<8> Hash(BitString<8> z) {
            if (z in T) {
                return T[z];
            }
            if (z == target) {
                return ssStar;
            }
            BitString<8> h <- BitString<8>;
            T[z] = h;
            return h;
        }
    }
    """)
    right = frog_parser.parse_game("""
    Game Right() {
        BitString<8> ssStar;
        BitString<8> target;
        Map<BitString<8>, BitString<8>> T;

        Void Initialize() {
            ssStar <- BitString<8>;
            target <- BitString<8>;
        }

        BitString<8> Hash(BitString<8> z) {
            if (z in T) {
                return T[z];
            }
            BitString<8> h <- BitString<8>;
            T[z] = h;
            if (z == target) {
                return ssStar;
            }
            return h;
        }
    }
    """)
    engine = _make_engine()
    assert engine.canonicalize_game(left) != engine.canonicalize_game(right), (
        "Topological sort must not reorder T[z] = h past the early-return "
        "guard `if (z == target) return ssStar;` — doing so changes the "
        "observable behavior on a second Hash query at the same z."
    )
