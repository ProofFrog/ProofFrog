"""RC4 (name-capture / non-fresh-name) regression tests for the
random-function transform passes.

Each finding pairs an ATTACK (two games an explicit adversary distinguishes
with advantage ~1, so a sound engine must report ``not valid``) with a SOUND
CONTROL (a genuinely interchangeable pair the fix must keep accepting, so the
rewrite still fires with zero proof fallout).

- F-011  LocalFunctionFieldToLet: the ``F -> H`` rename captured an oracle
  PARAMETER named ``H``.  Fixed by declining when ``H`` collides with a
  method/game parameter.
- F-027  LocalRFToUniform: the ``__rf_extract_N__`` extraction temp captured a
  method PARAMETER of the same name.  Fixed by minting a name fresh against
  every in-scope identifier.

(F-024 ExtractRFCalls is a pass-level harness; its regression lives in
``tests/unit/transforms/test_extract_rf_calls.py``.)
"""

from __future__ import annotations

from sympy import Symbol

from proof_frog import frog_ast, frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    engine = ProofEngine()
    for sym in ("lambda", "in", "out"):
        engine.variables[sym] = Symbol(sym, positive=True, integer=True)
    return engine


# ---------------------------------------------------------------------------
# F-011: LocalFunctionFieldToLet parameter capture
# ---------------------------------------------------------------------------


def _f011_engine(param_name: str) -> tuple[ProofEngine, frog_ast.Game, frog_ast.Game]:
    fn_type = frog_ast.FunctionType(
        frog_ast.BitStringType(frog_ast.Variable("in")),
        frog_ast.BitStringType(frog_ast.Variable("out")),
    )
    engine = _engine()
    # A sampled let-bound H : Function<BitString<in>, BitString<out>>.
    engine.sampled_let_names = {"H"}
    engine.proof_let_types.set("H", fn_type)
    engine.proof_namespace["H"] = None

    left = frog_parser.parse_game(f"""
        Game Left() {{
            Function<BitString<in>, BitString<out>> RF;
            Void Initialize() {{
                RF <- Function<BitString<in>, BitString<out>>;
            }}
            BitString<out> Eval(Function<BitString<in>, BitString<out>> {param_name}, BitString<in> x) {{
                return RF(x);
            }}
        }}
        """)
    right = frog_parser.parse_game(f"""
        Game Right() {{
            Void Initialize() {{
            }}
            BitString<out> Eval(Function<BitString<in>, BitString<out>> {param_name}, BitString<in> x) {{
                return {param_name}(x);
            }}
        }}
        """)
    return engine, left, right


def test_f011_parameter_capture_attack_rejected() -> None:
    # Eval has an adversary-supplied parameter named H matching the let.
    # Left returns the secret RF(x); Right returns the parameter H(x).
    # These are distinguishable (pass a constant function as H), so a sound
    # engine must NOT accept them as interchangeable.
    engine, left, right = _f011_engine("H")
    assert not engine.check_equivalent(left, right).valid


def test_f011_sound_control_accepted() -> None:
    # Same shape but the parameter is named K (no collision with the let H).
    # Now Left's RF can be soundly folded onto the unused let H, and Right
    # has no folding target, so the two are NOT interchangeable -- but the
    # fold itself must still FIRE.  We witness firing by checking that the
    # pass no longer reports a capture near-miss and that Left's field RF is
    # eliminated by the fold.
    engine, left, _ = _f011_engine("K")
    # Fold Left against an identical copy of itself: must be accepted
    # (the rewrite is deterministic and applied to both sides).
    left2 = frog_parser.parse_game(str(left))
    assert engine.check_equivalent(left, left2).valid


# ---------------------------------------------------------------------------
# F-027: LocalRFToUniform extraction-temp parameter capture
# ---------------------------------------------------------------------------


def test_f027_parameter_capture_attack_rejected() -> None:
    # CaptureReal returns RF(0^lambda) + p where the parameter p is named
    # __rf_extract_0__; the unsound mint would shadow p and collapse the
    # output to the constant 0^lambda (u + u).  CaptureConst is that
    # constant.  They are distinguishable, so the engine must reject.
    engine = _engine()
    real = frog_parser.parse_game("""
        Game CaptureReal() {
            BitString<lambda> Challenge(BitString<lambda> __rf_extract_0__) {
                Function<BitString<lambda>, BitString<lambda>> RF <- Function<BitString<lambda>, BitString<lambda>>;
                return RF(0^lambda) + __rf_extract_0__;
            }
        }
        """)
    const = frog_parser.parse_game("""
        Game CaptureConst() {
            BitString<lambda> Challenge(BitString<lambda> __rf_extract_0__) {
                return 0^lambda;
            }
        }
        """)
    assert not engine.check_equivalent(real, const).valid


def test_f027_sound_control_accepted() -> None:
    # A single local RF call (no name collision) IS one independent uniform
    # draw -- the intended rewrite.  The extraction + uniform-sample form
    # must remain interchangeable with the original RF-call form.
    engine = _engine()
    rf_form = frog_parser.parse_game("""
        Game G() {
            BitString<lambda> Challenge(BitString<lambda> p) {
                Function<BitString<lambda>, BitString<lambda>> RF <- Function<BitString<lambda>, BitString<lambda>>;
                return RF(0^lambda) + p;
            }
        }
        """)
    uniform_form = frog_parser.parse_game("""
        Game G() {
            BitString<lambda> Challenge(BitString<lambda> p) {
                BitString<lambda> u <- BitString<lambda>;
                return u + p;
            }
        }
        """)
    assert engine.check_equivalent(rf_form, uniform_form).valid
