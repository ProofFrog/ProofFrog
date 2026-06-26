"""RC4 name-capture / non-fresh-binding distinguisher tests for
control_flow.py passes.

Two findings, both name-capture hazards where a pass merges or moves code by
matching binders by NAME without checking the binding KIND or whether the move
crosses a write/rebind of a referenced variable:

* F-084 IfToBooleanAssignment -- merged an ``if (C) { x = ...; } else { ... }``
  whose two branches wrote the SAME name with DIFFERENT binding kinds (a field
  write vs a branch-local typed declaration), or hoisted a branch-local typed
  declaration into the enclosing scope where a later statement references it.
* F-114 IfFalseReturnToConjunction -- moved the negated guard ``!P`` past
  intervening typed-local declarations, one of which rebound a variable read by
  ``P``, so the moved guard read the wrong binding.

For each finding we assert end-to-end through ``ProofEngine.check_equivalent``:

* the NEGATIVE distinguisher (the attack game pair) is REJECTED -- the games
  are genuinely distinguishable, so a sound engine must refuse to certify them
  equivalent; and
* a POSITIVE control with a matching binding kind / capture-free move whose
  rewrite still fires, so the guard declines only on a real hazard.

The fragments are taken from / mirror
``extras/docs/transforms/audit-2026-06/attacks/<PassName>/``.
"""

from __future__ import annotations

from sympy import Symbol

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    engine = ProofEngine()
    engine.variables["n"] = Symbol("n", positive=True, integer=True)
    return engine


# ---------------------------------------------------------------------------
# F-084 IfToBooleanAssignment
# ---------------------------------------------------------------------------


def test_f084_mixed_kind_field_vs_local_rejected() -> None:
    """ATTACK-1: Left.SetFlag writes the FIELD in the then-branch and declares
    a branch-local in the else-branch. Merging by name only would erase the
    field write (becoming a fresh local). Distinguisher
    ``SetFlag(true); Read()`` -> true vs false. Engine must REJECT."""
    left = frog_parser.parse_game("""
        Game Left() {
            Bool flag;
            Void Initialize() { flag = false; }
            Void SetFlag(Bool c) {
                if (c) {
                    flag = true;
                } else {
                    Bool flag = false;
                }
            }
            Bool Read() { return flag; }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right() {
            Bool flag;
            Void Initialize() { flag = false; }
            Void SetFlag(Bool c) {}
            Bool Read() { return flag; }
        }
        """)
    assert not _engine().check_equivalent(left, right).valid


def test_f084_hoisted_decl_captures_later_field_write_rejected() -> None:
    """ATTACK-2: both branches declare a typed local ``flag``; the statement
    after the if writes the FIELD ``flag``. Hoisting ``Bool flag = c;`` into the
    method body would capture the later ``flag = true;``. Distinguisher
    ``SetFlag(false); Read()`` -> true vs false. Engine must REJECT."""
    left = frog_parser.parse_game("""
        Game Left() {
            Bool flag;
            Void Initialize() { flag = false; }
            Void SetFlag(Bool c) {
                if (c) {
                    Bool flag = true;
                } else {
                    Bool flag = false;
                }
                flag = true;
            }
            Bool Read() { return flag; }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right() {
            Bool flag;
            Void Initialize() { flag = false; }
            Void SetFlag(Bool c) {
                Bool flag = true;
            }
            Bool Read() { return flag; }
        }
        """)
    assert not _engine().check_equivalent(left, right).valid


def test_f084_same_binding_plain_assignment_control_accepted() -> None:
    """Positive control: both branches are plain assignments to the SAME
    existing field binding. Merging to ``flag = c;`` is sound, so the engine
    certifies the hand-collapsed twin equivalent."""
    branchy = frog_parser.parse_game("""
        Game A() {
            Bool flag;
            Void Initialize() { flag = false; }
            Void SetFlag(Bool c) {
                if (c) {
                    flag = true;
                } else {
                    flag = false;
                }
            }
            Bool Read() { return flag; }
        }
        """)
    collapsed = frog_parser.parse_game("""
        Game B() {
            Bool flag;
            Void Initialize() { flag = false; }
            Void SetFlag(Bool c) {
                flag = c;
            }
            Bool Read() { return flag; }
        }
        """)
    assert _engine().check_equivalent(branchy, collapsed).valid


# ---------------------------------------------------------------------------
# F-114 IfFalseReturnToConjunction
# ---------------------------------------------------------------------------


def test_f114_guard_var_rebound_by_intervening_decl_rejected() -> None:
    """ATTACK-1d: a shadowing declaration ``Int a = M[b];`` rebinds ``a``,
    which the guard ``a == b`` reads. Moving ``a != b`` past it reads the new
    local. Distinguisher ``O(1, 0)`` with ``M[0] = 0`` -> true vs false.
    Engine must REJECT."""
    left = frog_parser.parse_game("""
        Game Left() {
            Map<Int, Int> M;
            Void Initialize() { M[0] = 0; }
            Bool O(Int a, Int b) {
                if (a == b) {
                    return false;
                }
                Int a = M[b];
                return a == 0 || a == 1;
            }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right() {
            Map<Int, Int> M;
            Void Initialize() { M[0] = 0; }
            Bool O(Int a, Int b) {
                Int c = M[b];
                return (c == 0 || c == 1) && a != b;
            }
        }
        """)
    assert not _engine().check_equivalent(left, right).valid


def test_f114_capture_free_intervening_decl_control_accepted() -> None:
    """Positive control: the intervening declaration introduces a fresh name
    ``z`` not read by the guard, so moving ``a != b`` past it is safe. The
    engine certifies the hand-conjoined twin equivalent."""
    branchy = frog_parser.parse_game("""
        Game A() {
            Bool O(Int a, Int b) {
                if (a == b) {
                    return false;
                }
                Int z = a + b;
                return z == 0 || z == 1;
            }
        }
        """)
    conjoined = frog_parser.parse_game("""
        Game B() {
            Bool O(Int a, Int b) {
                Int z = a + b;
                return (z == 0 || z == 1) && a != b;
            }
        }
        """)
    assert _engine().check_equivalent(branchy, conjoined).valid
