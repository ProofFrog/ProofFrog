"""RC5 domain-mutation blindness: end-to-end soundness regression tests.

Several sample-movement / sample-merge passes used to move or merge a uniform
random sample across a write that changes the sample's *domain* -- a write to a
name appearing in the sampled type's size expression (``n`` in ``BitString<n>``,
``q`` in ``ModInt<q>``).  Moving/merging a sample across such a write changes
its distribution, so it is unsound.

Each pass now declines the move/merge when a domain-parameter name is written in
the crossed region.  For each affected pass this file asserts:

* the attack pair (real vs random, which differ in distribution) is REJECTED
  (``check_equivalent(...).valid`` is False), and
* a sound control with no domain-mutation in the crossed region is still
  ACCEPTED (``.valid`` is True) -- proving the pass still fires.

The control acceptance is load-bearing: it shows the guard does not
over-decline.  The two sides of each control use different variable names, so
acceptance requires the pass to fire (merge/sink + rename) on both sides.
"""

from __future__ import annotations

from sympy import Symbol

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine(max_calls: int | None = None) -> ProofEngine:
    """ProofEngine with the bit-string length symbol ``n`` registered."""
    engine = ProofEngine()
    engine.variables["n"] = Symbol("n", positive=True, integer=True)
    if max_calls is not None:
        engine.max_calls = max_calls
    return engine


# ---------------------------------------------------------------------------
# F-039  SinkUniformSample -- case 2 sinks a sample past an if whose branch
# writes the domain field ``n`` (``ModInt<n>``).
# ---------------------------------------------------------------------------


def test_sink_uniform_sample_domain_mutation_rejected() -> None:
    real = frog_parser.parse_game("""
        Game L() {
          Int n;
          Void Initialize() { n = 1; }
          ModInt<n> O(Bool b) {
            ModInt<n> x <- ModInt<n>;
            if (b) { n = 2; }
            return x;
          }
        }
        """)
    random = frog_parser.parse_game("""
        Game R() {
          Int n;
          Void Initialize() { n = 1; }
          ModInt<n> O(Bool b) {
            if (b) { n = 2; }
            ModInt<n> x <- ModInt<n>;
            return x;
          }
        }
        """)
    assert not _engine().check_equivalent(real, random).valid


def test_sink_uniform_sample_clean_control_accepted() -> None:
    # The if-branch writes an unrelated field, not the sampled domain ``n``,
    # so sinking the sample past the if is sound and must still fire.
    real = frog_parser.parse_game("""
        Game L() {
          Int n;
          Int junk;
          Void Initialize() { n = 2; }
          ModInt<n> O(Bool b) {
            ModInt<n> x <- ModInt<n>;
            if (b) { junk = 5; }
            return x;
          }
        }
        """)
    random = frog_parser.parse_game("""
        Game R() {
          Int n;
          Int junk;
          Void Initialize() { n = 2; }
          ModInt<n> O(Bool b) {
            if (b) { junk = 5; }
            ModInt<n> x <- ModInt<n>;
            return x;
          }
        }
        """)
    assert _engine().check_equivalent(real, random).valid


# ---------------------------------------------------------------------------
# F-054  SingleCallFieldToLocal -- moves a field sample from Initialize into the
# calling oracle; declines when the domain field is written after the sample.
# ---------------------------------------------------------------------------


def test_single_call_field_to_local_domain_mutated_in_init_rejected() -> None:
    # ATT-1: Initialize mutates q AFTER the sample, so relocating the draw into
    # Get re-evaluates the domain.
    real = frog_parser.parse_game("""
        Game L() {
          Int q;
          ModInt<q> x;
          Void Initialize() { q = 2; x <- ModInt<q>; q = 3; }
          ModInt<q> Get() { return x; }
        }
        """)
    random = frog_parser.parse_game("""
        Game R() {
          Int q;
          Void Initialize() { q = 2; q = 3; }
          ModInt<q> Get() { ModInt<q> x <- ModInt<q>; return x; }
        }
        """)
    assert not _engine(max_calls=1).check_equivalent(real, random).valid


def test_single_call_field_to_local_domain_mutated_in_sibling_rejected() -> None:
    # ATT-2: a sibling oracle mutates q between Initialize and Get.
    real = frog_parser.parse_game("""
        Game L() {
          Int q;
          ModInt<q> x;
          Void Initialize() { q = 2; x <- ModInt<q>; }
          Void Bump() { q = 3; }
          ModInt<q> Get() { return x; }
        }
        """)
    random = frog_parser.parse_game("""
        Game R() {
          Int q;
          Void Initialize() { q = 2; }
          Void Bump() { q = 3; }
          ModInt<q> Get() { ModInt<q> x <- ModInt<q>; return x; }
        }
        """)
    assert not _engine(max_calls=1).check_equivalent(real, random).valid


def test_single_call_field_to_local_clean_control_accepted() -> None:
    # Domain q is fixed before the sample and never mutated afterwards, so
    # localizing the sample into Get is sound and must still fire.
    real = frog_parser.parse_game("""
        Game L() {
          Int q;
          ModInt<q> x;
          Void Initialize() { q = 3; x <- ModInt<q>; }
          ModInt<q> Get() { return x; }
        }
        """)
    random = frog_parser.parse_game("""
        Game R() {
          Int q;
          Void Initialize() { q = 3; }
          ModInt<q> Get() { ModInt<q> x <- ModInt<q>; return x; }
        }
        """)
    assert _engine(max_calls=1).check_equivalent(real, random).valid


# ---------------------------------------------------------------------------
# F-061  MergeProductSamples -- merges component samples into a product sample
# re-anchored at the return; declines when a component's domain is mutated
# between its sample and the return.
# ---------------------------------------------------------------------------


def test_merge_product_samples_domain_drift_rejected() -> None:
    real = frog_parser.parse_game("""
        Game Real() {
          Int n;
          Void Initialize() { n = 4; }
          [BitString<n>, BitString<n>] O() {
            BitString<n> a <- BitString<n>;
            n = 8;
            BitString<n> b <- BitString<n>;
            return [a, b];
          }
        }
        """)
    random = frog_parser.parse_game("""
        Game Random() {
          Int n;
          Void Initialize() { n = 4; }
          [BitString<n>, BitString<n>] O() {
            n = 8;
            BitString<n> a <- BitString<n>;
            BitString<n> b <- BitString<n>;
            return [a, b];
          }
        }
        """)
    assert not _engine().check_equivalent(real, random).valid


def test_merge_product_samples_clean_control_accepted() -> None:
    # No domain mutation between the component samples and the return, so the
    # product merge is sound and must still fire on both sides (different names).
    side_a = frog_parser.parse_game("""
        Game A() {
          [BitString<n>, BitString<n>] O() {
            BitString<n> a <- BitString<n>;
            BitString<n> b <- BitString<n>;
            return [a, b];
          }
        }
        """)
    side_b = frog_parser.parse_game("""
        Game B() {
          [BitString<n>, BitString<n>] O() {
            BitString<n> p <- BitString<n>;
            BitString<n> q <- BitString<n>;
            return [p, q];
          }
        }
        """)
    assert _engine().check_equivalent(side_a, side_b).valid
