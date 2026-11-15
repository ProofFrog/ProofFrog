"""F-337: field-name standardization must not capture a same-named TYPE.

``frog_ast.Variable`` is declared ``class Variable(Expression, Type)`` -- ONE
node class models both "a reference to a value" and "the name of a user-defined
type" (a ``let:``-bound ``Set``, a scheme's ``Set Key = ...`` alias).  Field
standardization used to rename fields with a name-keyed
``SubstitutionTransformer`` over the whole game, which therefore rewrote type
positions too.

A game instantiated so that a field and a set share a spelling (``Set S1`` bound
to a proof-level ``Set KA``, field also named ``KA``) canonicalised to

    Game Left()  { field1 field1; ... field1 <- field1; }

losing the type entirely, whereas a game whose field was named ``k`` kept it
(``KA field1``).  Two consequences:

* a FALSE REJECT: two games differing only in a field's name failed to
  canonicalise together (issue #252); and
* a FALSE ACCEPT: a game sampling from set ``KA`` collapsed onto the same
  canonical form as a game sampling from a *different* set that the proof
  happened to name ``field1`` -- the engine certified a hop between games whose
  collision probabilities are ``1/|KA|`` and ``1/|field1|``.

The games below are written in post-instantiation form (game parameters already
replaced by the proof's ``let:`` names), which is exactly what the engine's
equivalence check receives.
"""

from __future__ import annotations

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    return ProofEngine()


# ---------------------------------------------------------------------------
# ATTACK -- the false accept.
#
# ``left`` draws two independent elements of the set ``KA`` and reports whether
# they collide: Pr[Get() = true] = 1/|KA|.
# ``right`` does the same over a different set, which the proof named ``field1``:
# Pr[Get() = true] = 1/|field1|.
#
# Distinguisher: call Get() once, output its result.  Instantiating
# KA = BitString<1> and field1 = BitString<8> gives advantage 1/2 - 1/256.
# The hop must be REJECTED.
# ---------------------------------------------------------------------------


def test_f337_type_capture_attack_rejected() -> None:
    left = frog_parser.parse_game("""
        Game Left() {
          KA KA;
          Void Initialize() {
            KA <- KA;
          }
          Bool Get() {
            KA y <- KA;
            return y == KA;
          }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right() {
          field1 x;
          Void Initialize() {
            x <- field1;
          }
          Bool Get() {
            field1 y <- field1;
            return y == x;
          }
        }
        """)
    assert not _engine().check_equivalent(left, right).valid


def test_f337_attack_control_without_the_minted_name_rejected() -> None:
    """The same pair with the second set named ``KB`` rather than ``field1``.

    This isolates the defect: only the collision with the name the engine mints
    (``field1``) made the attack pair canonicalise together, so this variant was
    already rejected before the fix and must stay rejected after it.
    """
    left = frog_parser.parse_game("""
        Game Left() {
          KA KA;
          Void Initialize() {
            KA <- KA;
          }
          Bool Get() {
            KA y <- KA;
            return y == KA;
          }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right() {
          KB x;
          Void Initialize() {
            x <- KB;
          }
          Bool Get() {
            KB y <- KB;
            return y == x;
          }
        }
        """)
    assert not _engine().check_equivalent(left, right).valid


# ---------------------------------------------------------------------------
# SOUND CONTROL -- issue #252's own pair.  The two games differ only in the name
# of a field, so this is an identity hop and must be ACCEPTED.  Without this the
# "fix" would be indistinguishable from field standardization simply losing its
# power.
# ---------------------------------------------------------------------------


def test_f337_field_renaming_only_still_accepted() -> None:
    left = frog_parser.parse_game("""
        Game Left() {
          KA KA;
          KA Get() {
            return KA;
          }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right() {
          KA k;
          KA Get() {
            return k;
          }
        }
        """)
    assert _engine().check_equivalent(left, right).valid


def test_f337_field_renaming_with_sampling_still_accepted() -> None:
    """Same sound hop, but with state and a sampled field, so the rename has to
    survive ``Initialize``, a local declaration and an equality test."""
    left = frog_parser.parse_game("""
        Game Left() {
          KA KA;
          Void Initialize() {
            KA <- KA;
          }
          Bool Get() {
            KA y <- KA;
            return y == KA;
          }
        }
        """)
    right = frog_parser.parse_game("""
        Game Right() {
          KA stored;
          Void Initialize() {
            stored <- KA;
          }
          Bool Get() {
            KA y <- KA;
            return y == stored;
          }
        }
        """)
    assert _engine().check_equivalent(left, right).valid
