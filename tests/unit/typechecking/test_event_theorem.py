"""Checker rules for event theorems (``event <flag> of <game>``)."""

import shutil
from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis

FIXTURES = Path(__file__).resolve().parents[2] / "integration" / "upto_fixtures"

EVENT_PROOF = """
import 'BadGuess.game';
import 'RandomTargetGuessing.game';

proof:

let:
    Set S;

assume:
    RandomTargetGuessing(S);

theorem:
    event bad of BadGuess(S);

games:
    BadGuess(S).Right against BadGuess(S).Adversary;
    RandomTargetGuessing(S).Real compose R(S) against BadGuess(S).Adversary;
    RandomTargetGuessing(S).Ideal compose R(S) against BadGuess(S).Adversary;

Reduction R(Set S) compose RandomTargetGuessing(S) against BadGuess(S).Adversary {
    Bool bad;

    Void Initialize() {
        challenger.Initialize();
        bad = false;
    }

    Bool Eq(S c) {
        if (challenger.Eq(c)) {
            bad = true;
        }
        return false;
    }
}
"""

PARENT_PROOF = """
import 'TargetGuess.game';
import 'BadGuess.game';

proof:

let:
    Set S;

lemma:
    event bad of BadGuess(S) by 'lemma.proof';

theorem:
    TargetGuess(S);

games:
    TargetGuess(S).Left against TargetGuess(S).Adversary;
    BadGuess(S).Left compose R(S) against TargetGuess(S).Adversary;
    BadGuess(S).Right compose R(S) against TargetGuess(S).Adversary;
    TargetGuess(S).Right against TargetGuess(S).Adversary;

Reduction R(Set S) compose BadGuess(S) against TargetGuess(S).Adversary {
    Void Initialize() {
        challenger.Initialize();
    }

    Bool Eq(S c) {
        return challenger.Eq(c);
    }
}
"""

INIT_EVENT_PROOF = """
import 'InitCollision.game';
import 'RandomTargetGuessing.game';

proof:

let:
    Set S;

assume:
    RandomTargetGuessing(S);

theorem:
    event bad of InitCollision(S) at Initialize;

games:
    InitCollision(S).Ideal against InitCollision(S).Adversary;
    RandomTargetGuessing(S).Real compose R(S) against InitCollision(S).Adversary;
    RandomTargetGuessing(S).Ideal compose R(S) against InitCollision(S).Adversary;

Reduction R(Set S) compose RandomTargetGuessing(S) against InitCollision(S).Adversary {
    Bool bad;

    Void Initialize() {
        challenger.Initialize();
        S y <- S;
        bad = false;
        if (challenger.Eq(y)) {
            bad = true;
        }
    }
}
"""


def _check(tmp_path: Path, src: str, extra: dict[str, str] | None = None) -> None:
    for fixture in FIXTURES.glob("*.game"):
        shutil.copy(fixture, tmp_path / fixture.name)
    for name, text in (extra or {}).items():
        (tmp_path / name).write_text(text)
    (tmp_path / "lemma.proof").write_text(EVENT_PROOF)
    path = tmp_path / "t.proof"
    path.write_text(src)
    semantic_analysis.check_well_formed(frog_parser.parse_file(str(path)), str(path))


def _rejects(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    src: str,
    text: str,
    extra: dict[str, str] | None = None,
) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check(tmp_path, src, extra)
    err = capsys.readouterr().err
    assert text in err, err


def test_event_proof_accepted(tmp_path: Path) -> None:
    _check(tmp_path, EVENT_PROOF)


def test_parent_with_event_lemma_accepted(tmp_path: Path) -> None:
    _check(tmp_path, PARENT_PROOF)


def test_init_event_proof_accepted(tmp_path: Path) -> None:
    _check(tmp_path, INIT_EVENT_PROOF)


def test_e1_game_without_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _rejects(
        tmp_path,
        capsys,
        EVENT_PROOF.replace("event bad of BadGuess(S)", "event oops of BadGuess(S)"),
        "no `Bool oops` field",
    )


def test_e1_on_lemma(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _rejects(
        tmp_path,
        capsys,
        PARENT_PROOF.replace("event bad of BadGuess(S) by", "event oops of BadGuess(S) by"),
        "no `Bool oops` field",
    )


def test_e1_event_on_non_game(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _rejects(
        tmp_path,
        capsys,
        EVENT_PROOF.replace("event bad of BadGuess(S);", "event bad of Nope(S);"),
        "Nope",
    )


def test_e2_first_step_other_game(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = EVENT_PROOF.replace(
        "    BadGuess(S).Right against BadGuess(S).Adversary;\n", ""
    )
    _rejects(tmp_path, capsys, src, "first step must be a side of BadGuess(S)")


def test_e2_other_adversary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = EVENT_PROOF.replace(
        "RandomTargetGuessing(S).Ideal compose R(S) against BadGuess(S).Adversary;",
        "RandomTargetGuessing(S).Ideal against RandomTargetGuessing(S).Adversary;",
    )
    _rejects(tmp_path, capsys, src, "against BadGuess(S).Adversary")


def test_e2_pair_only_as_first_step(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = EVENT_PROOF.replace(
        "    RandomTargetGuessing(S).Real compose",
        "    BadGuess(S).Left against BadGuess(S).Adversary;\n"
        "    RandomTargetGuessing(S).Real compose",
    )
    _rejects(tmp_path, capsys, src, "only as the first step")


def test_e3_reduction_without_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = EVENT_PROOF.replace("    Bool bad;\n\n    Void Initialize() {\n        challenger", "    Void Initialize() {\n        challenger").replace(
        "        bad = false;\n    }\n\n    Bool Eq", "    }\n\n    Bool Eq"
    ).replace("            bad = true;\n", "")
    _rejects(tmp_path, capsys, src, "must declare `Bool bad`")


def test_e3_intermediate_game_without_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = EVENT_PROOF.replace(
        "Reduction R(Set S)",
        "Game G(Set S) {\n    S t;\n    Void Initialize() { t <- S; }\n"
        "    Bool Eq(S c) { return false; }\n}\n\nReduction R(Set S)",
    ).replace(
        "    RandomTargetGuessing(S).Real compose",
        "    G(S) against BadGuess(S).Adversary;\n    RandomTargetGuessing(S).Real compose",
    )
    _rejects(tmp_path, capsys, src, "must declare `Bool bad`")


def test_e4_flag_raised_in_oracle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = EVENT_PROOF.replace("event bad of BadGuess(S);", "event bad of BadGuess(S) at Initialize;")
    _rejects(tmp_path, capsys, src, "only in Initialize")


def test_e4_initialize_parameters(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pair = (FIXTURES / "InitCollision.game").read_text().replace(
        "[S, S] Initialize()", "[S, S] Initialize(S z)"
    )
    _rejects(
        tmp_path,
        capsys,
        INIT_EVENT_PROOF.replace("InitCollision", "InitCollisionP"),
        "no parameters",
        extra={"InitCollisionP.game": pair.replace("InitCollision;", "InitCollisionP;")},
    )


def test_e4_early_return(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pair = (FIXTURES / "InitCollision.game").read_text().replace(
        "        if (x == y) {\n            bad = true;\n        }",
        "        if (x == y) {\n            bad = true;\n            return [y, x];\n        }",
    )
    _rejects(
        tmp_path,
        capsys,
        INIT_EVENT_PROOF.replace("InitCollision", "InitCollisionR"),
        "early return",
        extra={"InitCollisionR.game": pair.replace("InitCollision;", "InitCollisionR;")},
    )


def test_e4_reduction_with_oracle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = INIT_EVENT_PROOF.replace(
        "        if (challenger.Eq(y)) {\n            bad = true;\n        }\n    }\n",
        "        if (challenger.Eq(y)) {\n            bad = true;\n        }\n    }\n\n"
        "    Bool Collided() {\n        return false;\n    }\n",
    )
    _rejects(tmp_path, capsys, src, "only Initialize")


def test_both_routes_is_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = PARENT_PROOF.replace(
        "lemma:", "assume:\n    BadGuess(S);\n\nlemma:"
    )
    _rejects(tmp_path, capsys, src, "both")


def test_placement_rule_is_checker_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = PARENT_PROOF.replace(
        "        return challenger.Eq(c);",
        "        challenger.Initialize();\n        return challenger.Eq(c);",
    )
    _rejects(tmp_path, capsys, src, "challenger.Initialize")


def test_bound_atom_event_accepted(tmp_path: Path) -> None:
    src = PARENT_PROOF.replace(
        "games:", "bound:\n    advantage(event bad of BadGuess(S) compose R);\n\ngames:"
    )
    _check(tmp_path, src)


def test_bound_atom_event_not_in_scope(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = PARENT_PROOF.replace(
        "games:", "bound:\n    advantage(event other of BadGuess(S) compose R);\n\ngames:"
    )
    _rejects(tmp_path, capsys, src, "not an assumed or lemma")
