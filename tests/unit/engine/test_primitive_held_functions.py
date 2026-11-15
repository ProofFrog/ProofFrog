"""Sampled let: functions that a primitive instantiation receives (F-387),
and let: entries whose value calls a function (F-389).

A primitive's methods are opaque: given ``HLeak L = HLeak(m, H);``, a game
calling ``L.Leak()`` may learn values of the random function ``H`` that no
call ``H(...)`` in the game shows. ``ProofEngine.set_up_proof_context``
records each such function (``primitive_held_functions``) so the passes
that reason about every query of ``H`` decline. A scheme's methods are
inlined into the game, so a scheme given ``H`` does not count.
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser, proof_engine

_PRIMITIVES = {
    "HLeak": """
        Primitive HLeak(Int m, Function<BitString<1>, BitString<m>> H) {
            [BitString<m>, BitString<m>] Leak();
        }
        """,
    "Plain": """
        Primitive Plain(Int m) {
            [BitString<m>, BitString<m>] Leak();
        }
        """,
    "ValueLeak": """
        Primitive ValueLeak(Int m, BitString<m> c) {
            BitString<m> Leak();
        }
        """,
    "Drawer": """
        Primitive Drawer() {
            BitString<1> Draw();
            deterministic BitString<1> Fixed();
        }
        """,
}

_SCHEMES = {
    "Wrap": """
        Scheme Wrap(Int m, Plain L) extends Plain {
            [BitString<m>, BitString<m>] Leak() {
                return L.Leak();
            }
        }
        """,
    "HashUser": """
        Scheme HashUser(Int m, Function<BitString<1>, BitString<m>> H)
            extends Plain {
            [BitString<m>, BitString<m>] Leak() {
                return [H(0b0), H(0b1)];
            }
        }
        """,
    "DrawWrap": """
        Scheme DrawWrap(Drawer R) extends Drawer {
            BitString<1> Draw() {
                return R.Draw();
            }
            deterministic BitString<1> Fixed() {
                return R.Fixed();
            }
        }
        """,
}

_FN = "Function<BitString<1>, BitString<m>>"


def _definitions() -> frog_ast.Namespace:
    namespace: frog_ast.Namespace = {}
    for name, source in _PRIMITIVES.items():
        namespace[name] = frog_parser.parse_string(source, frog_ast.FileType.PRIMITIVE)
    for name, source in _SCHEMES.items():
        namespace[name] = frog_parser.parse_string(source, frog_ast.FileType.SCHEME)
    return namespace


def _proof(lets: str) -> frog_ast.ProofFile:
    source = f"""
    proof:

    let:
        Int m;
        {_FN} H <- {_FN};
        {lets}

    theorem:
        G(m);

    games:
        G(m).Left against G(m).Adversary;
        G(m).Right against G(m).Adversary;
    """
    proof = frog_parser.parse_string(source, frog_ast.FileType.PROOF)
    assert isinstance(proof, frog_ast.ProofFile)
    return proof


def _held(lets: str) -> dict[str, str]:
    proof = _proof(lets)
    # pylint: disable-next=protected-access
    return proof_engine._functions_held_by_primitives(
        proof.lets, proof.sampled_let_names, _definitions()
    )


@pytest.mark.parametrize(
    "lets, held",
    [
        # Given to a primitive directly.
        ("HLeak L = HLeak(m, H);", {"H": "L"}),
        # Given to a primitive inside a scheme instantiation's argument.
        ("Wrap W = Wrap(m, HLeak(m, H));", {"H": "W"}),
        # A value computed from H, given to a primitive.
        ("BitString<m> c = H(0b0); ValueLeak V = ValueLeak(m, c);", {"H": "V"}),
        # A primitive holding H, given to a scheme: the primitive's entry.
        ("HLeak L = HLeak(m, H); Wrap W = Wrap(m, L);", {"H": "L"}),
    ],
)
def test_f387_function_held_by_primitive(lets: str, held: dict[str, str]) -> None:
    assert _held(lets) == held


@pytest.mark.parametrize(
    "lets",
    [
        # A scheme's methods are inlined: their queries of H are calls.
        "HashUser S = HashUser(m, H);",
        # A primitive given nothing of H.
        "Plain L = Plain(m);",
        # A value computed from H that no primitive receives.
        "BitString<m> c = H(0b0);",
        # A primitive given a function that is not sampled.
        f"{_FN} K; HLeak L = HLeak(m, K);",
    ],
)
def test_f387_function_not_held_by_primitive(lets: str) -> None:
    assert not _held(lets)


def _engine(lets: str) -> proof_engine.ProofEngine:
    engine = proof_engine.ProofEngine(verbose=False, parallel=False)
    for name, root in _definitions().items():
        engine.add_definition(name, root)
    engine.set_up_proof_context(_proof(lets))
    return engine


def test_f387_engine_context_records_held_function() -> None:
    engine = _engine("HLeak L = HLeak(m, H);")
    assert engine.primitive_held_functions == {"H": "L"}
    # pylint: disable-next=protected-access
    assert engine._build_context().primitive_held_functions == {"H": "L"}


def test_f389_let_value_calling_function_is_a_value() -> None:
    """``c0 = H(0b0)`` calls the let: function H, not a primitive or scheme:
    set-up used to look H up as a definition and crash. The entry is a value,
    read as H's value at 0b0."""
    engine = _engine("BitString<m> c0 = H(0b0);")
    assert engine.proof_namespace["c0"] == frog_parser.parse_expression("H(0b0)")
    assert not engine.primitive_held_functions


@pytest.mark.parametrize(
    "lets, name, value",
    [
        # A deterministic primitive method in the argument.
        ("Drawer R; BitString<m> c = H(R.Fixed());", "c", "H(R.Fixed())"),
        # A let: function in the argument.
        ("BitString<m> c = H(H(0b0)[0 : 1]);", "c", "H(H(0b0)[0 : 1])"),
        # A let: entry in the argument stays a name: c is H at its one value.
        ("Drawer R; BitString<1> x = R.Draw(); BitString<m> c = H(x);", "c", "H(x)"),
    ],
)
def test_f389_let_value_with_deterministic_argument_is_a_value(
    lets: str, name: str, value: str
) -> None:
    engine = _engine(lets)
    assert engine.proof_namespace[name] == frog_parser.parse_expression(value)


@pytest.mark.parametrize(
    "lets",
    [
        "Drawer R; BitString<m> c = H(R.Draw());",
        "Drawer R; BitString<m> c = H(R.Draw() + R.Fixed());",
        # A scheme method that draws.
        "Drawer R; DrawWrap W = DrawWrap(R); BitString<m> c = H(W.Draw());",
    ],
)
def test_f389_let_value_with_nondeterministic_argument_is_refused(lets: str) -> None:
    """``c = H(R.Draw())`` holds H at one draw; read as its expression at
    every use, each use would draw again, so set-up refuses the entry."""
    with pytest.raises(proof_engine.UnsupportedLetEntryError) as error:
        _engine(lets)
    assert error.value.name == "c"


def test_f389_prove_reports_refused_let_entry_as_failed_proof(
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = proof_engine.ProofEngine(verbose=False, parallel=False)
    for name, root in _definitions().items():
        engine.add_definition(name, root)
    with pytest.raises(proof_engine.FailedProof):
        engine.prove(_proof("Drawer R; BitString<m> c = H(R.Draw());"))
    output = capsys.readouterr().out
    assert "let: entry 'c' = H(R.Draw())" in output
    assert "Proof Failed! (let: entry 'c' is not supported)" in output
