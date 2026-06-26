"""Tests for DeadGuardedAssignmentElimination.

The pass replaces an assignment ``v = E`` with ``v = false`` when ``v`` is read
solely by a guard ``if (v) { if (G) { return R } }`` whose fall-through is the
same ``R`` -- under ``G`` the result is ``R`` regardless of ``v``. The
soundness condition is that the killed value is never otherwise observed. A
game FIELD persists across oracle calls, so its value can be observed in a
sibling/later oracle (F-099 A2b) or carried from a previous call into the guard
when the assignment is conditional (F-099 A2).
"""

from proof_frog import frog_parser
from proof_frog.transforms.control_flow import DeadGuardedAssignmentElimination
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _make_ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str):
    game = frog_parser.parse_game(source)
    return game, DeadGuardedAssignmentElimination().apply(game, _make_ctx())


def test_local_guarded_assignment_killed() -> None:
    """Positive control: a method-LOCAL boolean read solely by the guard is a
    dead store -- the pass fires (value replaced by false)."""
    game, result = _apply("""
        Game G() {
            Int O(Int x, Bool c) {
                Bool v = false;
                if (x == 1) {
                    v = c;
                }
                if (v) {
                    if (x == 1) {
                        return 0;
                    }
                    return 1;
                }
                return 0;
            }
        }
        """)
    assert result != game, "local dead guarded assignment should be killed"


def test_field_read_in_sibling_oracle_not_killed() -> None:
    """F-099 A2b: the field is also read by a separate Leak oracle, so its
    value is observable -- must DECLINE."""
    game, result = _apply("""
        Game G() {
            Bool v;
            Void Initialize() { v = false; }
            Int O(Int x, Bool c) {
                if (x == 1) { v = c; }
                if (v) {
                    if (x == 1) { return 0; }
                    return 1;
                }
                return 0;
            }
            Bool Leak() { return v; }
        }
        """)
    assert result == game, "field read by a sibling oracle must not be killed"


def test_field_conditionally_assigned_persists_not_killed() -> None:
    """F-099 A2: the field is only conditionally assigned (if (x == 1)), so on
    other calls the guard reads the persisted previous-call value -- must
    DECLINE even though the field is read only by the guard."""
    game, result = _apply("""
        Game G() {
            Bool v;
            Void Initialize() { v = false; }
            Int O(Int x, Bool c) {
                if (x == 1) { v = c; }
                if (v) {
                    if (x == 1) { return 0; }
                    return 1;
                }
                return 0;
            }
        }
        """)
    assert result == game, "conditionally-assigned field must not be killed"


# ---------------------------------------------------------------------------
# RC3 determinism guard (F-100): a non-deterministic dominating guard must
# block the dead-store kill (the path fact from one evaluation does not
# entail the guard's independent re-evaluation).
# ---------------------------------------------------------------------------


def _ctx_with(**namespace) -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=dict(namespace),
        subsets_pairs=[],
    )


def _nondet_prim():
    return frog_parser.parse_primitive_file("Primitive P(Int n) { Bool f(Int x); }")


def _det_prim():
    return frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic Bool f(Int x); }"
    )


def test_nondeterministic_guard_blocks_kill() -> None:
    """The inner guard ``F.f(x)`` is non-deterministic; the path fact from the
    first evaluation does not entail the second, independent one, so the kill
    is declined."""
    game = frog_parser.parse_game("""
        Game G(P F, Int n) {
            Int O(Int x, Bool c) {
                Bool v = false;
                if (F.f(x)) {
                    v = c;
                }
                if (v) {
                    if (F.f(x)) {
                        return 0;
                    }
                    return 1;
                }
                return 0;
            }
        }
        """)
    ctx = _ctx_with(P=_nondet_prim(), F=_nondet_prim())
    result = DeadGuardedAssignmentElimination().apply(game, ctx)
    assert result == game  # kill declined
    assert any(
        nm.transform_name == "Dead Guarded Assignment Elimination"
        for nm in ctx.near_misses
    )


def test_deterministic_guard_still_kills() -> None:
    """Control: with a deterministic guard ``D.f(x)`` the path fact entails
    the guard's re-evaluation, so the dead store is killed."""
    game = frog_parser.parse_game("""
        Game G(D F, Int n) {
            Int O(Int x, Bool c) {
                Bool v = false;
                if (F.f(x)) {
                    v = c;
                }
                if (v) {
                    if (F.f(x)) {
                        return 0;
                    }
                    return 1;
                }
                return 0;
            }
        }
        """)
    ctx = _ctx_with(D=_det_prim(), F=_det_prim())
    result = DeadGuardedAssignmentElimination().apply(game, ctx)
    assert result != game  # the dead store was killed
