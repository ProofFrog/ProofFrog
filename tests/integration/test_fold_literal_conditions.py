"""End-to-end checks for FoldLiteralConditions through ProofEngine.

Games that differ only by literal-constant conditions must be interchangeable.
Games whose literal conditions select different behavior must be rejected.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from sympy import Symbol

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    engine = ProofEngine()
    engine.variables["n"] = Symbol("n", positive=True, integer=True)
    return engine


_PLAIN = """
    Game Plain() {
        Int count;
        Void Initialize() { count = 0; }
        [Int, Bool]? Query(Int x, Bool b) {
            count = count + x;
            return [count, b];
        }
    }
    """


def test_literal_conditions_fold_accepted() -> None:
    """Each guard is a literal constant, so the games are equal."""
    guarded = frog_parser.parse_game("""
        Game Guarded() {
            Int count;
            Void Initialize() { count = 0; }
            [Int, Bool]? Query(Int x, Bool b) {
                if (None == [1, true, None, x]) {
                    return None;
                }
                if (!(false)) {
                    count = count + x;
                } else {
                    if (0 >= 1) {
                        count = 5;
                    } else {
                        count = 6;
                    }
                }
                if ([x, b] != None) {
                    return [count, b];
                }
                return None;
            }
        }
        """)
    plain = frog_parser.parse_game(_PLAIN)
    assert _engine().check_equivalent(guarded, plain).valid


def test_literal_conditions_selecting_other_branch_rejected() -> None:
    """``!(true)`` and ``1 >= 1`` pick the branches that set count to 6.
    ``Query(1, true)`` returns ``[6, true]`` instead of ``[1, true]``."""
    guarded = frog_parser.parse_game("""
        Game Guarded() {
            Int count;
            Void Initialize() { count = 0; }
            [Int, Bool]? Query(Int x, Bool b) {
                if (!(true)) {
                    count = count + x;
                } else {
                    if (1 >= 1) {
                        count = 6;
                    } else {
                        count = count + x;
                    }
                }
                return [count, b];
            }
        }
        """)
    plain = frog_parser.parse_game(_PLAIN)
    assert not _engine().check_equivalent(guarded, plain).valid


def test_none_against_literal_is_never_equal_rejected() -> None:
    """``[x, b] != None`` always holds, so Guarded always returns None."""
    guarded = frog_parser.parse_game("""
        Game Guarded() {
            Int count;
            Void Initialize() { count = 0; }
            [Int, Bool]? Query(Int x, Bool b) {
                count = count + x;
                if ([x, b] != None) {
                    return None;
                }
                return [count, b];
            }
        }
        """)
    plain = frog_parser.parse_game(_PLAIN)
    assert not _engine().check_equivalent(guarded, plain).valid


def test_none_against_variable_not_folded_rejected() -> None:
    """``None == y`` depends on the argument, so the guard must stay."""
    guarded = frog_parser.parse_game("""
        Game Guarded() {
            Int count;
            Void Initialize() { count = 0; }
            [Int, Bool]? Query(Int x, Bool b, Int? y) {
                count = count + x;
                if (None == y) {
                    return None;
                }
                return [count, b];
            }
        }
        """)
    plain = frog_parser.parse_game("""
        Game Plain() {
            Int count;
            Void Initialize() { count = 0; }
            [Int, Bool]? Query(Int x, Bool b, Int? y) {
                count = count + x;
                return [count, b];
            }
        }
        """)
    assert not _engine().check_equivalent(guarded, plain).valid


_CONSTANT_ONE = """
    Game Plain(Int q) {
        Int Query(Int n) {
            return 1;
        }
    }
    """


def test_optional_bool_not_true_folded_accepted() -> None:
    """``v`` is ``None`` or ``false`` on every path, so ``v != true`` holds.

    After branch duplication each path compares a literal with ``true``.
    """
    guarded = frog_parser.parse_game("""
        Game Guarded(Int q) {
            Int Query(Int n) {
                Bool? v;
                if (n >= q) {
                    v = None;
                } else {
                    v = false;
                }
                if (v != true) {
                    return 1;
                }
                return 2;
            }
        }
        """)
    plain = frog_parser.parse_game(_CONSTANT_ONE)
    assert _engine().check_equivalent(guarded, plain).valid


def test_optional_bool_from_argument_not_folded_rejected() -> None:
    """``v`` comes from the caller and may be ``true``."""
    guarded = frog_parser.parse_game("""
        Game Guarded(Int q) {
            Int Query(Int n, Bool? v) {
                if (v != true) {
                    return 1;
                }
                return 2;
            }
        }
        """)
    plain = frog_parser.parse_game("""
        Game Plain(Int q) {
            Int Query(Int n, Bool? v) {
                return 1;
            }
        }
        """)
    assert not _engine().check_equivalent(guarded, plain).valid


# ---------------------------------------------------------------------------
# Fixtures: the folded shapes reached from type-correct proofs.
#
# The typechecker rejects ``None == [x, b]`` written directly, so the games
# above exist only as ASTs. In the fixtures the shapes arise the way they do
# in practice: a scheme method (``return s == None;``, ``return !f;``,
# ``return a >= b;``) is inlined at a call with literal arguments.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent
FIXTURES = Path(__file__).parent / "fold_literal_fixtures"


def _run_prove(proof_file: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", str(FIXTURES / proof_file)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


@pytest.mark.parametrize(
    "proof_file",
    [
        "FoldNone.proof",  # [x, b] == None over method parameters
        "FoldNot.proof",  # !false
        "FoldGe.proof",  # 0 >= 1
        "DefinedField.proof",  # [x, f] == None, f assigned by Initialize
    ],
)
def test_inlined_literal_condition_folds(proof_file: str) -> None:
    result = _run_prove(proof_file)
    assert "Proof Succeeded" in result.stdout, result.stdout + result.stderr


@pytest.mark.parametrize(
    "proof_file",
    [
        "WrongBranch.proof",  # the literal conditions select the other branch
        "AlwaysNone.proof",  # ![x, b] == None always holds
    ],
)
def test_inlined_literal_condition_selecting_other_behavior_rejected(
    proof_file: str,
) -> None:
    result = _run_prove(proof_file)
    assert "Proof Failed" in result.stdout, result.stdout + result.stderr


@pytest.mark.parametrize(
    "proof_file",
    [
        "UndefField.proof",  # field assigned only by another oracle
        "UndefLocal.proof",  # local declared bare, assigned under an if
        "UndefInitReturn.proof",  # field assigned after Initialize may return
    ],
)
def test_none_fold_keeps_read_of_possibly_unassigned_variable(
    proof_file: str,
) -> None:
    """Real evaluates a tuple that reads a variable which may be unassigned,
    and Random does not. Folding the comparison would drop that read and
    make the games equal, so ``prove`` must fail."""
    result = _run_prove(proof_file)
    assert "Proof Failed" in result.stdout, result.stdout + result.stderr
