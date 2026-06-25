"""RC3 (determinism / purity) soundness tests for random-function passes.

These end-to-end tests exercise the ``ChallengeExclusionRFToUniform`` pass
through the full ``ProofEngine.check_equivalent`` pipeline.  They guard the
soundness condition restored by the RC3 determinism guard: the
``H(cf) -> cf <- R`` rewrite is valid only when ``H`` is a genuinely SAMPLED
random function (re-samplable / ROM) and every RF query is visible to the
call-site scan.

Each test pairs a *negative* control (an unsound attack shape the engine must
REJECT) with the corresponding *positive* control (the genuine sampled-RF
shape, which the pass must still fire on so the games are judged equivalent).

The attack shapes mirror judge vectors (a) and (c) of the
ChallengeExclusionRFToUniform verdict.  Vector (d) (a second init RF call
embedded in a larger expression) is covered at pass level in
``tests/unit/transforms/`` because the engine already rejects that end-to-end
shape for unrelated reasons, so it does not yield a meaningful
attack-vs-control engine pair.

New tests are small hand-built FrogLang games (not full proofs) so a failure
points directly at one engine path.
"""

from __future__ import annotations

from sympy import Symbol

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    """ProofEngine with the bit-string length symbol ``n`` registered."""
    engine = ProofEngine()
    engine.variables["n"] = Symbol("n", positive=True, integer=True)
    return engine


# --------------------------------------------------------------------------
# Vector (a): sampledness of H.
#
# ``field = H(cf)`` may be rewritten to ``field <- R`` only when ``H`` is a
# SAMPLED random function.  When ``H`` is a known/standard-model function
# (bound via ``H = F;``), ``H(cf)`` is a fixed value the adversary can
# recompute, so the rewrite is unsound.  ``field`` is made observable via a
# ``Reveal`` oracle so the difference is detectable.
# --------------------------------------------------------------------------


def _challenge_game(init_field: str, h_binding: str) -> str:
    return f"""
    Game G(Int n, Function<BitString<n>, BitString<n>> F) {{
        Function<BitString<n>, BitString<n>> H;
        BitString<n> cf;
        BitString<n> field;
        BitString<n> Initialize() {{
            {h_binding}
            cf <- BitString<n>;
            {init_field}
            return cf;
        }}
        BitString<n> Reveal() {{
            return field;
        }}
        BitString<n>? Query(BitString<n> param) {{
            if (param == cf) {{
                return None;
            }}
            return H(param);
        }}
    }}
    """


_SAMPLED = "H <- Function<BitString<n>, BitString<n>>;"
_KNOWN = "H = F;"
_REAL_FIELD = "field = H(cf);"
_RANDOM_FIELD = "field <- BitString<n>;"


def test_challenge_exclusion_known_function_attack_rejected() -> None:
    """Vector (a): a KNOWN function ``H = F`` must NOT be simplified."""
    engine = _engine()
    real = frog_parser.parse_game(_challenge_game(_REAL_FIELD, _KNOWN))
    random = frog_parser.parse_game(_challenge_game(_RANDOM_FIELD, _KNOWN))
    assert not engine.check_equivalent(real, random).valid


def test_challenge_exclusion_sampled_function_control_fires() -> None:
    """Positive control (a): a genuinely SAMPLED RF still canonicalizes."""
    engine = _engine()
    real = frog_parser.parse_game(_challenge_game(_REAL_FIELD, _SAMPLED))
    random = frog_parser.parse_game(_challenge_game(_RANDOM_FIELD, _SAMPLED))
    result = engine.check_equivalent(real, random)
    assert result.valid, result.failure_detail


# --------------------------------------------------------------------------
# Vector (c): RF reachable through a local alias.
#
# An oracle binds ``Galias = H`` and calls ``Galias(param)``.  This aliased
# query is invisible to the by-name call-site scan, so the exclusion guard is
# absent and the rewrite would be unsound.  The positive control is the same
# game with the RF called directly (no alias), which the pass simplifies.
# --------------------------------------------------------------------------


def _alias_game(init_field: str, *, aliased: bool) -> str:
    if aliased:
        query_body = """
            Function<BitString<n>, BitString<n>> Galias = H;
            return Galias(param);
        """
    else:
        query_body = """
            if (param == cf) {
                return None;
            }
            return H(param);
        """
    return f"""
    Game G(Int n) {{
        Function<BitString<n>, BitString<n>> H;
        BitString<n> cf;
        BitString<n> field;
        BitString<n> Initialize() {{
            H <- Function<BitString<n>, BitString<n>>;
            cf <- BitString<n>;
            {init_field}
            return cf;
        }}
        BitString<n> Reveal() {{
            return field;
        }}
        BitString<n>? Query(BitString<n> param) {{
            {query_body}
        }}
    }}
    """


def test_challenge_exclusion_aliased_rf_attack_rejected() -> None:
    """Vector (c): an RF query through a local alias must block the rewrite."""
    engine = _engine()
    real = frog_parser.parse_game(_alias_game(_REAL_FIELD, aliased=True))
    random = frog_parser.parse_game(_alias_game(_RANDOM_FIELD, aliased=True))
    assert not engine.check_equivalent(real, random).valid


def test_challenge_exclusion_direct_rf_control_fires() -> None:
    """Positive control (c): the same game with a direct RF call simplifies."""
    engine = _engine()
    real = frog_parser.parse_game(_alias_game(_REAL_FIELD, aliased=False))
    random = frog_parser.parse_game(_alias_game(_RANDOM_FIELD, aliased=False))
    result = engine.check_equivalent(real, random)
    assert result.valid, result.failure_detail
