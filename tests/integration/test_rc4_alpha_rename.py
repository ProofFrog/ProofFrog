"""RC4 alpha-rename: name-capture soundness regression tests.

Several high-footfall passes (BranchElimination F-124, SimplifyIf F-129) rewrite
code by splicing or normalising block-local declarations.  Because FrogLang uses
*position-sensitive* block scoping -- a name used before its local declaration
binds to the enclosing (field/outer) scope, e.g. ``Int out = x;`` reads the field
``x`` even when ``Int x = 0;`` follows -- a name-blind splice/normalisation can
conflate a body-local with an outer binding of the same name and certify a hop a
distinguisher refutes.

The fix is a global pre-pipeline ``AlphaRename`` pass that gives every *typed*
local binder a fresh, globally-unique name (respecting position-sensitive
scope), so no later splice or normalisation has a same-name collision to
mishandle.  ``VariableStandardize`` re-washes the fresh names to ``vN`` at the
end, so sound proofs' final canonical forms are unchanged.

For each finding this file asserts:

* the attack pair (which a written distinguisher separates) is REJECTED
  (``check_equivalent(...).valid`` is False), and
* a sound control (genuinely equivalent games that differ only in local names /
  shadowing shape) is still ACCEPTED -- proving alpha-rename does not break
  completeness.
"""

from __future__ import annotations

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    return ProofEngine()


# ---------------------------------------------------------------------------
# F-124  BranchElimination -- ATK-1: an ``if(true)`` body-local ``y`` shadows an
# outer local ``y``; splicing the body without renaming captures ``return y``.
# Real returns 0^8 with probability 1; Random returns a fresh uniform.
# Distinguisher: call Oracle once, output 1 iff result == 0^8 (advantage ~1).
# ---------------------------------------------------------------------------


def test_branch_elimination_local_shadow_rejected() -> None:
    real = frog_parser.parse_game("""
        Game Real(Int lambda) {
          BitString<8> Oracle() {
            BitString<8> y = 0^8;
            if (true) {
              BitString<8> y <- BitString<8>;
            }
            return y;
          }
        }
        """)
    random = frog_parser.parse_game("""
        Game Random(Int lambda) {
          BitString<8> Oracle() {
            BitString<8> y <- BitString<8>;
            return y;
          }
        }
        """)
    assert not _engine().check_equivalent(real, random).valid


# F-124 ATK-2: an ``if(true)`` body-local ``count`` shadows a game FIELD
# ``count``; splicing converts persistent cross-call state into a per-call
# local.  Real increments the field (returns 1, 2, ...); Random returns 101.
def test_branch_elimination_field_shadow_rejected() -> None:
    real = frog_parser.parse_game("""
        Game Real(Int lambda) {
          Int count;
          Void Initialize() { count = 0; }
          Int Oracle() {
            if (true) {
              Int count = 100;
            }
            count = count + 1;
            return count;
          }
        }
        """)
    random = frog_parser.parse_game("""
        Game Random(Int lambda) {
          Int count;
          Void Initialize() { count = 0; }
          Int Oracle() {
            Int count = 100;
            count = count + 1;
            return count;
          }
        }
        """)
    assert not _engine().check_equivalent(real, random).valid


def test_branch_elimination_clean_control_accepted() -> None:
    # Sound: the if(true) body's sampled value is actually returned, so splicing
    # is correct.  The two sides differ only in the local name (y vs z) and in
    # whether the (always-taken) if wrapper is present -- they ARE equivalent
    # (both return a fresh uniform), so the pass must still accept the hop.
    real = frog_parser.parse_game("""
        Game Real(Int lambda) {
          BitString<8> Oracle() {
            if (true) {
              BitString<8> y <- BitString<8>;
              return y;
            }
            return 0^8;
          }
        }
        """)
    random = frog_parser.parse_game("""
        Game Random(Int lambda) {
          BitString<8> Oracle() {
            BitString<8> z <- BitString<8>;
            return z;
          }
        }
        """)
    assert _engine().check_equivalent(real, random).valid


# ---------------------------------------------------------------------------
# F-129  SimplifyIf -- ATK A1: branch-local normalisation rewrites a field read
# that textually PRECEDES a same-named local declaration, so the THEN branch
# (reads field x) and ELSE branch (reads field z) normalise identically and are
# wrongly merged.  Distinguisher SetX(0); SetZ(1); Probe(false) separates them.
# ---------------------------------------------------------------------------


def test_simplify_if_field_read_before_decl_rejected() -> None:
    left = frog_parser.parse_game("""
        Game Left() {
          Int x;
          Int z;
          Void Initialize() { x = 0; z = 0; }
          Void SetX(Int v) { x = v; }
          Void SetZ(Int v) { z = v; }
          Int Probe(Bool c) {
            if (c) {
              Int out = x;
              Int x = 0;
              return out + x;
            } else {
              Int out = z;
              Int z = 0;
              return out + z;
            }
          }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right() {
          Int x;
          Int z;
          Void Initialize() { x = 0; z = 0; }
          Void SetX(Int v) { x = v; }
          Void SetZ(Int v) { z = v; }
          Int Probe(Bool c) {
            Int out = x;
            Int x2 = 0;
            return out + x2;
          }
        }
        """)
    assert not _engine().check_equivalent(left, right).valid


def test_simplify_if_loop_binder_capture_rejected() -> None:
    # F-129 ATK-A9c: SimplifyIf's `_normalize_block_locals` renames a branch
    # local and (buggily) rewrites a same-named generic-for BINDER use, merging
    # two inequivalent branches.  THEN sums the loop binder `x` over D={1,2}
    # (acc = 3); ELSE sums the sampled local `t` (acc = 2t).  Distinguisher
    # Probe(false); GetAcc() -> 3 (odd) vs 2t (even), advantage 1.  AlphaRename
    # renames the locals (x->fresh, t->fresh) so the THEN loop-binder use and
    # the ELSE local use stay distinct and the buggy merge cannot fire.
    left = frog_parser.parse_game("""
        Game Left() {
          ModInt<16> acc;
          Set<ModInt<16>> D;
          Void Initialize() { acc = 0; D = {1, 2}; }
          Void Probe(Bool c) {
            acc = 0;
            if (c) {
              ModInt<16> x <- ModInt<16>;
              for (ModInt<16> x in D) { acc = acc + x; }
            } else {
              ModInt<16> t <- ModInt<16>;
              for (ModInt<16> x in D) { acc = acc + t; }
            }
          }
          ModInt<16> GetAcc() { return acc; }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right() {
          ModInt<16> acc;
          Set<ModInt<16>> D;
          Void Initialize() { acc = 0; D = {1, 2}; }
          Void Probe(Bool c) {
            acc = 0;
            ModInt<16> x <- ModInt<16>;
            for (ModInt<16> x in D) { acc = acc + x; }
          }
          ModInt<16> GetAcc() { return acc; }
        }
        """)
    assert not _engine().check_equivalent(left, right).valid


def test_simplify_if_identical_branches_control_accepted() -> None:
    # Sound: both branches genuinely read the SAME field x (just with different
    # local names), so merging the if into a single body is correct and the two
    # sides ARE equivalent.  Must still be accepted.
    left = frog_parser.parse_game("""
        Game Left() {
          Int x;
          Void Initialize() { x = 0; }
          Void SetX(Int v) { x = v; }
          Int Probe(Bool c) {
            if (c) {
              Int a = x;
              return a;
            } else {
              Int b = x;
              return b;
            }
          }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right() {
          Int x;
          Void Initialize() { x = 0; }
          Void SetX(Int v) { x = v; }
          Int Probe(Bool c) {
            Int out = x;
            return out;
          }
        }
        """)
    assert _engine().check_equivalent(left, right).valid
