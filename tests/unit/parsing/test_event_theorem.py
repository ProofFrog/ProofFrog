"""Parsing of event theorems: ``event <flag> of <game> [at Initialize]``."""

from pathlib import Path

import pytest

from proof_frog import frog_ast, frog_parser

SRC = """
import 'P.game';
proof:
let:
    Set S;
assume:
    event bad of Q(S) at Initialize;
lemma:
    event bad of P(S) by 'P_bad.proof';
theorem:
    event bad of P(S);
bound:
    advantage(event bad of P(S) compose R);
games:
    P(S).Right against P(S).Adversary;
    P(S).Right against P(S).Adversary;
"""


def _parse(tmp_path: Path, src: str) -> frog_ast.ProofFile:
    f = tmp_path / "t.proof"
    f.write_text(src)
    return frog_parser.parse_proof_file(str(f))


def test_event_theorem_parses(tmp_path: Path) -> None:
    pf = _parse(tmp_path, SRC)
    assert isinstance(pf.theorem, frog_ast.EventTheorem)
    assert pf.theorem.flag == "bad" and pf.theorem.game.name == "P"
    assert pf.theorem.at_initialize is False
    assert isinstance(pf.assumptions[0], frog_ast.EventTheorem)
    assert pf.assumptions[0].at_initialize is True
    assert isinstance(pf.lemmas[0].game, frog_ast.EventTheorem)
    assert str(pf.theorem) == "event bad of P(S)"
    assert str(pf.assumptions[0]) == "event bad of Q(S) at Initialize"
    assert pf.theorem.notion().name == "P#event#bad"
    assert pf.assumptions[0].notion().name == "Q#event#bad#init"
    assert pf.theorem.notion().args == pf.theorem.game.args


def test_event_in_bound_atom(tmp_path: Path) -> None:
    pf = _parse(tmp_path, SRC)
    assert pf.claimed_bound is not None
    ref = pf.claimed_bound.bound
    assert isinstance(ref, frog_ast.AdvantageReference)
    assert isinstance(ref.notion, frog_ast.EventTheorem)
    assert str(ref) == "advantage(event bad of P(S) compose R)"


def test_plain_notions_unchanged(tmp_path: Path) -> None:
    src = SRC.replace("event bad of Q(S) at Initialize", "Q(S)").replace(
        "theorem:\n    event bad of P(S);", "theorem:\n    P(S);"
    )
    pf = _parse(tmp_path, src)
    assert isinstance(pf.theorem, frog_ast.ParameterizedGame)
    assert isinstance(pf.assumptions[0], frog_ast.ParameterizedGame)


def test_event_not_equal_to_game() -> None:
    g = frog_ast.ParameterizedGame("P", [frog_ast.Variable("S")])
    e = frog_ast.EventTheorem("bad", g, False)
    assert e != g and g != e and e == frog_ast.EventTheorem("bad", g, False)
    assert e != frog_ast.EventTheorem("bad", g, True)
    assert e != frog_ast.EventTheorem("other", g, False)


def test_at_requires_initialize(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="Initialize"):
        _parse(tmp_path, SRC.replace("at Initialize", "at Setup"))


def test_event_roundtrip() -> None:
    ast1 = frog_parser.parse_string(SRC, frog_ast.FileType.PROOF)
    text1 = str(ast1)
    assert "event bad of Q(S) at Initialize;" in text1
    assert "event bad of P(S) by 'P_bad.proof';" in text1
    ast2 = frog_parser.parse_string(text1, frog_ast.FileType.PROOF)
    assert str(ast2) == text1
