"""RC3 determinism-guard distinguisher tests for control_flow.py passes.

Each finding (F-071, F-087, F-100, F-107, F-111, F-116, F-118) corresponds
to a control-flow canonicalization pass that DELETED / DEDUPED / DUPLICATED
/ FOLDED code containing a non-deterministic call without a purity check.
Two textual copies of a non-deterministic call denote independent draws, so
those rewrites are unsound.

For each finding we assert two things end-to-end through
``ProofEngine.check_equivalent`` (CORE_PIPELINE + standardization + Z3
residual):

* the NEGATIVE distinguisher (the attack game pair) is REJECTED -- the two
  games are genuinely distinguishable, so a sound engine must refuse to
  certify them equivalent; and
* a POSITIVE control whose corresponding deterministic twin still fires, so
  the guard is principled (declines on non-determinism only, not always).

These are deliberately small hand-built FrogLang fragments taken from
``extras/docs/transforms/audit-2026-06/attacks/<PassName>/``.
"""

from __future__ import annotations

from sympy import Symbol

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine_with(**namespace) -> ProofEngine:
    engine = ProofEngine()
    engine.variables["n"] = Symbol("n", positive=True, integer=True)
    for name, root in namespace.items():
        engine.proof_namespace[name] = root
    return engine


def _nondet_prim() -> object:
    """Unannotated primitive: ``eval``/``f``/``F`` are non-deterministic."""
    return frog_parser.parse_primitive_file("""
        Primitive P(Int n) {
            BitString<n> eval();
            Bool f(Int x);
            Int call(Int x);
        }
        """)


def _det_prim() -> object:
    """Primitive with deterministic methods (purity-guard positive control)."""
    return frog_parser.parse_primitive_file("""
        Primitive D(Int n) {
            deterministic BitString<n> eval(BitString<n> x);
            deterministic Bool f(Int x);
            deterministic Int call(Int x);
        }
        """)


# ---------------------------------------------------------------------------
# F-071 UniqExclusionBranchElimination
# ---------------------------------------------------------------------------


def test_f071_uniq_exclusion_nondet_element_rejected() -> None:
    """Real folds ``b == F.eval()`` to false using a <-uniq exclusion whose
    element is a non-deterministic call. The second ``F.eval()`` is an
    independent draw, so Real returns true with probability 2^-n while
    Random never does -- engine must REJECT."""
    real = frog_parser.parse_game("""
        Game Real(P F, Int n) {
            Bool Oracle() {
                BitString<n> b <-uniq[{F.eval()}] BitString<n>;
                if (b == F.eval()) {
                    return true;
                }
                return false;
            }
        }
        """)
    random = frog_parser.parse_game("""
        Game Random(P F, Int n) {
            Bool Oracle() {
                BitString<n> b <-uniq[{F.eval()}] BitString<n>;
                return false;
            }
        }
        """)
    engine = _engine_with(P=_nondet_prim(), F=_nondet_prim())
    assert not engine.check_equivalent(real, random).valid


def test_f071_uniq_exclusion_deterministic_still_fires() -> None:
    """Positive control: ``b <-uniq[{a}]`` with a plain sampled ``a`` lets
    the pass fold ``a == b`` to false; the two games are equivalent."""
    real = frog_parser.parse_game("""
        Game Real(Int n) {
            Bool Oracle() {
                BitString<n> a <- BitString<n>;
                BitString<n> b <-uniq[{a}] BitString<n>;
                if (a == b) {
                    return true;
                }
                return false;
            }
        }
        """)
    random = frog_parser.parse_game("""
        Game Random(Int n) {
            Bool Oracle() {
                BitString<n> a <- BitString<n>;
                BitString<n> b <-uniq[{a}] BitString<n>;
                return false;
            }
        }
        """)
    engine = _engine_with()
    assert engine.check_equivalent(real, random).valid


# ---------------------------------------------------------------------------
# F-087 RedundantConditionalReturn
# ---------------------------------------------------------------------------


def test_f087_redundant_conditional_return_nondet_guard_rejected() -> None:
    """``if (F.f(x)) { return 1; } return 1;`` has the body match the
    fall-through, but dropping the guard discards an evaluation of the
    non-deterministic ``F.f(x)``. Real evaluates the call; Ideal never
    does -- engine must REJECT."""
    real = frog_parser.parse_game("""
        Game Real(P F, Int n) {
            Int Oracle(Int x) {
                if (F.f(x)) {
                    return 1;
                }
                return 1;
            }
        }
        """)
    ideal = frog_parser.parse_game("""
        Game Ideal(P F, Int n) {
            Int Oracle(Int x) {
                return 1;
            }
        }
        """)
    engine = _engine_with(P=_nondet_prim(), F=_nondet_prim())
    assert not engine.check_equivalent(real, ideal).valid


def test_f087_redundant_conditional_return_deterministic_still_fires() -> None:
    """Positive control: a deterministic guard ``D.f(x)`` evaluated in the
    dropped if has no observable effect, so the redundant guard folds."""
    real = frog_parser.parse_game("""
        Game Real(D F, Int n) {
            Int Oracle(Int x) {
                if (F.f(x)) {
                    return 1;
                }
                return 1;
            }
        }
        """)
    ideal = frog_parser.parse_game("""
        Game Ideal(D F, Int n) {
            Int Oracle(Int x) {
                return 1;
            }
        }
        """)
    engine = _engine_with(D=_det_prim(), F=_det_prim())
    assert engine.check_equivalent(real, ideal).valid


# ---------------------------------------------------------------------------
# F-100 DeadGuardedAssignmentElimination
# ---------------------------------------------------------------------------


def test_f100_dead_guarded_assignment_nondet_guard_rejected() -> None:
    """Left's inner guard ``F.f(x)`` is non-deterministic; the path fact
    from the first evaluation is wrongly treated as entailing the second,
    independent one, so ``v = c`` would be killed to ``v = false``. Right is
    that post-kill image. The games are distinguishable -- engine REJECTS."""
    left = frog_parser.parse_game("""
        Game Left(P F, Int n) {
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
    right = frog_parser.parse_game("""
        Game Right(P F, Int n) {
            Int O(Int x, Bool c) {
                Bool v = false;
                if (F.f(x)) {
                    v = false;
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
    engine = _engine_with(P=_nondet_prim(), F=_nondet_prim())
    assert not engine.check_equivalent(left, right).valid


# ---------------------------------------------------------------------------
# F-107 RemoveUnreachable (Case B dedup)
# ---------------------------------------------------------------------------


def test_f107_remove_unreachable_nondet_condition_rejected() -> None:
    """Two structurally-identical return-conditions ``F.f(x)`` each guard an
    independent draw; deduping the second deletes a live evaluation. Left has
    both ifs; Right deletes the second -- engine must REJECT."""
    left = frog_parser.parse_game("""
        Game Left(P F, Int n) {
            Int O(Int x) {
                if (F.f(x)) {
                    return 1;
                }
                if (F.f(x)) {
                    return 2;
                }
                return 3;
            }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right(P F, Int n) {
            Int O(Int x) {
                if (F.f(x)) {
                    return 1;
                }
                return 3;
            }
        }
        """)
    engine = _engine_with(P=_nondet_prim(), F=_nondet_prim())
    assert not engine.check_equivalent(left, right).valid


# ---------------------------------------------------------------------------
# F-111 AbsorbRedundantEarlyReturn
# ---------------------------------------------------------------------------


def test_f111_absorb_early_return_nondet_guard_rejected() -> None:
    """Left's early ``if (F.f(x)) { return 7; }`` guard is non-deterministic;
    absorbing it duplicates ``!F.f(x)`` into the intervening guard, creating
    independent re-evaluations. Right is the absorbed image -- engine
    REJECTS."""
    left = frog_parser.parse_game("""
        Game Left(P F, Int n) {
            Int O(Int x, Bool q) {
                if (F.f(x)) {
                    return 7;
                }
                if (q) {
                    return 5;
                }
                return 7;
            }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right(P F, Int n) {
            Int O(Int x, Bool q) {
                if (!F.f(x) && q) {
                    return 5;
                }
                return 7;
            }
        }
        """)
    engine = _engine_with(P=_nondet_prim(), F=_nondet_prim())
    assert not engine.check_equivalent(left, right).valid


# ---------------------------------------------------------------------------
# F-116 IfFalseReturnToConjunction
# ---------------------------------------------------------------------------


def test_f116_if_false_return_nondet_trailing_rejected() -> None:
    """Left skips the non-deterministic ``F.f(x)`` when ``x == 0`` (returns
    false immediately); Right (the conjunction image ``F.f(x) && x != 0``)
    always evaluates it. Distinguishable -- engine REJECTS."""
    left = frog_parser.parse_game("""
        Game Left(P F, Int n) {
            Bool Test(Int x) {
                if (x == 0) {
                    return false;
                }
                return F.f(x);
            }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right(P F, Int n) {
            Bool Test(Int x) {
                return F.f(x) && x != 0;
            }
        }
        """)
    engine = _engine_with(P=_nondet_prim(), F=_nondet_prim())
    assert not engine.check_equivalent(left, right).valid


def test_f116_if_false_return_deterministic_still_fires() -> None:
    """Positive control: with a deterministic ``D.f(x)`` the conjunction
    rewrite is exact, so the two games are equivalent."""
    left = frog_parser.parse_game("""
        Game Left(D F, Int n) {
            Bool Test(Int x) {
                if (x == 0) {
                    return false;
                }
                return F.f(x);
            }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right(D F, Int n) {
            Bool Test(Int x) {
                return F.f(x) && x != 0;
            }
        }
        """)
    engine = _engine_with(D=_det_prim(), F=_det_prim())
    assert engine.check_equivalent(left, right).valid


# ---------------------------------------------------------------------------
# F-118 FoldEquivalentReturnBranch
# ---------------------------------------------------------------------------


def test_f118_fold_equivalent_return_nondet_field_rhs_rejected() -> None:
    """Both sides initialize a field from a non-deterministic call. Collapse
    keeps an ``if (a == k) { return F.eval(); } return a;`` case-split that
    is NOT equivalent to the branchless ``return a;`` once the engine refuses
    to expand the field to a textual copy of the non-deterministic call --
    engine must REJECT."""
    collapse = frog_parser.parse_game("""
        Game Collapse(P F, Int n) {
            BitString<n> a;
            Void Initialize() {
                a = F.eval();
            }
            BitString<n> O(BitString<n> k) {
                if (a == k) {
                    return F.eval();
                }
                return a;
            }
        }
        """)
    branchless = frog_parser.parse_game("""
        Game Branchless(P F, Int n) {
            BitString<n> a;
            Void Initialize() {
                a = F.eval();
            }
            BitString<n> O(BitString<n> k) {
                return a;
            }
        }
        """)
    engine = _engine_with(P=_nondet_prim(), F=_nondet_prim())
    assert not engine.check_equivalent(collapse, branchless).valid
