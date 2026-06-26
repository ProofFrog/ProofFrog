"""RC3 soundness regression: LazyMapScan non-deterministic-key guard.

End-to-end engine tests for the F-142 fix in
``proof_frog.transforms.map_iteration.LazyMapScan``.

The literal-equality branch of the scan rewrite

    for ([K, V] e in M.entries) { if (e[0] == key) { return Body(e); } }
        -->  if (key in M) { return Body[e[0]:=key, e[1]:=M[key]]; }

re-evaluates ``key`` at independent fresh sites (the membership test, the
``M[key]`` lookup, and every substituted ``e[0]``), whereas the input loop
evaluates it once per iteration. If ``key`` contains a non-deterministic
call those sites draw independently and the output distribution differs
(verdict §8, Attacks 1 and 3). The fix declines on a non-deterministic key.

These tests assert:
  * NEGATIVE: a game whose scan key is an unannotated primitive call
    ``NN.draw()`` is NOT proved equivalent to the direct-lookup form.
  * POSITIVE (control, verdict §6): a deterministic key (here a plain
    parameter) must still canonicalize to the direct-lookup form.
"""

from __future__ import annotations

from sympy import Symbol

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    engine = ProofEngine()
    engine.variables["n"] = Symbol("n", positive=True, integer=True)
    return engine


_ND_PRIMITIVE = """
Primitive ND() {
    BitString<8> draw();
}
"""


def test_nondeterministic_key_scan_not_equivalent_to_lookup() -> None:
    """Attack 1 (verdict §8): a non-deterministic scan key must NOT be
    accepted as equivalent to the direct membership-test + lookup form.

    Input draws ``NN.draw()`` once per iteration; the candidate output draws
    it independently at the membership test and the lookup, so the return
    distribution differs (``p`` vs ``p^2`` plus undefined lookups)."""
    prim = frog_parser.parse_primitive_file(_ND_PRIMITIVE)
    real = frog_parser.parse_game("""
        Game Real(ND NN) {
            Map<BitString<8>, BitString<16>> M;
            Void Store(BitString<8> k, BitString<16> v) {
                M[k] = v;
            }
            BitString<16> Lookup() {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == NN.draw()) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """)
    direct = frog_parser.parse_game("""
        Game Direct(ND NN) {
            Map<BitString<8>, BitString<16>> M;
            Void Store(BitString<8> k, BitString<16> v) {
                M[k] = v;
            }
            BitString<16> Lookup() {
                if (NN.draw() in M) {
                    return M[NN.draw()];
                }
                return 0b0000000000000000;
            }
        }
        """)
    engine = _engine()
    engine.proof_namespace["ND"] = prim
    engine.proof_namespace["NN"] = prim
    result = engine.check_equivalent(real, direct)
    assert not result.valid, (
        "LazyMapScan accepted a non-deterministic scan key as equivalent to "
        "direct lookup -- the F-142 soundness guard regressed."
    )


def test_deterministic_key_scan_still_equivalent_to_lookup() -> None:
    """Positive control (verdict §6): a deterministic scan key (a plain
    parameter) must still canonicalize to the direct-lookup form, so the
    guard did not over-fire."""
    pre = frog_parser.parse_game("""
        Game Pre() {
            Map<BitString<8>, BitString<16>> M;
            Void Store(BitString<8> k, BitString<16> v) {
                M[k] = v;
            }
            BitString<16> Lookup(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """)
    post = frog_parser.parse_game("""
        Game Post() {
            Map<BitString<8>, BitString<16>> M;
            Void Store(BitString<8> k, BitString<16> v) {
                M[k] = v;
            }
            BitString<16> Lookup(BitString<8> arg) {
                if (arg in M) {
                    return M[arg];
                }
                return 0b0000000000000000;
            }
        }
        """)
    engine = _engine()
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail
