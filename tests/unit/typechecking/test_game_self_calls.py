"""A game or reduction may not call a game's methods, its own included.

The engine resolves no such call: it treated ``G.Inc()`` inside ``G`` as a
side-effect-free opaque call and dropped it, so a game whose oracle raised a
counter through its own ``Inc`` was proved equal to one that did not. The
type checker rejects the call. Calls of primitive and scheme methods, a
scheme's ``this.`` calls, and a reduction's ``challenger.`` calls are allowed.
"""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis

_COUNTER_GAMES = """\
Game Left() {
    Int c;
    Void Initialize() {
        c = 0;
    }
    Void Inc() {
        c = c + 1;
    }
    Int Get() {
        LEFT_GET
        return c;
    }
}

Game Right() {
    Int c;
    Void Initialize() {
        c = 0;
    }
    Void Inc() {
        c = c + 1;
    }
    Int Get() {
        RIGHT_GET
        return c;
    }
}

export as Counter;
"""

_TRIVIAL_GAMES = """\
Game Real() {
    Void Initialize() {
    }
}

Game Ideal() {
    Void Initialize() {
    }
}

export as Trivial;
"""

_HELPER_GAME = """\
Game Mid() {
    Int c;
    Void Initialize() {
        c = 0;
    }
    Void Inc() {
        c = c + 1;
    }
    Int Get() {
        MID_GET
        return c;
    }
}

"""

_REDUCTION = """\
Reduction R() compose Trivial() against Counter().Adversary {
    Int c;
    Void Initialize() {
        challenger.Initialize();
        c = 0;
    }
    Void Inc() {
        c = c + 1;
    }
    Int Get() {
        R_GET
        return c;
    }
}

"""

_PROOF_BODY = """\
proof:

assume:
    Trivial();

theorem:
    Counter();

games:
    Counter().Left against Counter().Adversary;
    STEPS
    Counter().Right against Counter().Adversary;
"""

_TWICE_PRIMITIVE = """\
Primitive Twice(Int n) {
    Int lambda = n;

    BitString<lambda> Sample();

    BitString<lambda> Again();
}
"""

_TWICE_SCHEME = """\
import 'Twice.primitive';

Scheme TwiceScheme(Int n) extends Twice {
    Int lambda = n;

    BitString<lambda> Sample() {
        BitString<lambda> r <- BitString<lambda>;
        return r;
    }

    BitString<lambda> Again() {
        return this.Sample();
    }
}
"""

_TWICE_GAMES = """\
import 'Twice.primitive';

Game Real(Twice T) {
    BitString<T.lambda> Get() {
        return T.Again();
    }
}

Game Random(Twice T) {
    BitString<T.lambda> Get() {
        BitString<T.lambda> r <- BitString<T.lambda>;
        return r;
    }
}

export as AgainUniform;
"""


def _check(path: Path) -> None:
    semantic_analysis.check_well_formed(frog_parser.parse_file(str(path)), str(path))


def _write_counter(tmp_path: Path, left_get: str = "", right_get: str = "") -> Path:
    path = tmp_path / "Counter.game"
    path.write_text(
        _COUNTER_GAMES.replace("LEFT_GET", left_get).replace("RIGHT_GET", right_get)
    )
    return path


def _write_proof(
    tmp_path: Path,
    *,
    mid_get: str | None = None,
    r_get: str | None = None,
    reduction_first: bool = False,
) -> Path:
    """A Counter proof with an optional intermediate game Mid and reduction R.

    ``mid_get`` / ``r_get`` is the statement placed before ``return c;`` in
    the helper's ``Get``; ``None`` leaves the helper out.
    """
    _write_counter(tmp_path)
    (tmp_path / "Trivial.game").write_text(_TRIVIAL_GAMES)
    mid = ""
    reduction = ""
    steps = ""
    if mid_get is not None:
        mid = _HELPER_GAME.replace("MID_GET", mid_get)
        steps += "Mid() against Counter().Adversary;\n    "
    if r_get is not None:
        reduction = _REDUCTION.replace("R_GET", r_get)
        steps += (
            "Trivial().Real compose R() against Counter().Adversary;\n    "
            "Trivial().Ideal compose R() against Counter().Adversary;\n    "
        )
    helpers = reduction + mid if reduction_first else mid + reduction
    path = tmp_path / "counter.proof"
    path.write_text(
        "import 'Counter.game';\nimport 'Trivial.game';\n\n"
        + helpers
        + _PROOF_BODY.replace("STEPS", steps)
    )
    return path


def _rejects(path: Path, capsys: pytest.CaptureFixture[str], message: str) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check(path)
    assert message in capsys.readouterr().err


class TestGameCallsRejected:
    def test_game_calling_its_own_method(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _write_counter(tmp_path, left_get="Left.Inc();")
        _rejects(
            path,
            capsys,
            "Game 'Left' may not call its own method 'Inc':"
            " a game may not call its own methods",
        )

    def test_game_using_its_own_method_value(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _write_counter(tmp_path, left_get="Int d = Left.Get();")
        _rejects(path, capsys, "Game 'Left' may not call its own method 'Get'")

    def test_game_calling_its_own_method_through_instantiation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _write_proof(tmp_path, mid_get="Mid().Inc();")
        _rejects(path, capsys, "Game 'Mid' may not call its own method 'Inc'")

    def test_game_calling_the_other_game_of_its_pair(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _write_counter(tmp_path, right_get="Left.Inc();")
        _rejects(path, capsys, "Game 'Right' may not call method 'Inc' of game 'Left'")

    def test_reduction_calling_its_own_oracle(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _write_proof(tmp_path, r_get="R.Inc();")
        _rejects(
            path,
            capsys,
            "Reduction 'R' may not call its own method 'Inc':"
            " a reduction may not call its own methods",
        )

    def test_intermediate_game_calling_its_own_method(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _write_proof(tmp_path, mid_get="Mid.Inc();")
        _rejects(path, capsys, "Game 'Mid' may not call its own method 'Inc'")

    def test_reduction_calling_an_intermediate_game(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _write_proof(tmp_path, mid_get="", r_get="Mid.Inc();")
        _rejects(path, capsys, "Reduction 'R' may not call method 'Inc' of game 'Mid'")

    def test_intermediate_game_calling_a_reduction(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _write_proof(
            tmp_path, r_get="", mid_get="Int d = R.Get();", reduction_first=True
        )
        _rejects(path, capsys, "Game 'Mid' may not call method 'Get' of reduction 'R'")

    def test_intermediate_game_calling_a_game_of_an_imported_pair(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _write_proof(tmp_path, mid_get="Counter().Left.Inc();")
        _rejects(
            path,
            capsys,
            "Game 'Mid' may not call method 'Inc' of game 'Counter().Left'",
        )


class TestAllowedCalls:
    def test_game_without_game_calls(self, tmp_path: Path) -> None:
        _check(_write_counter(tmp_path))

    def test_reduction_calling_its_challenger(self, tmp_path: Path) -> None:
        # R's Initialize calls challenger.Initialize().
        _check(_write_proof(tmp_path, mid_get="", r_get=""))

    def test_game_calling_a_primitive_method(self, tmp_path: Path) -> None:
        (tmp_path / "Twice.primitive").write_text(_TWICE_PRIMITIVE)
        path = tmp_path / "AgainUniform.game"
        path.write_text(_TWICE_GAMES)
        _check(path)

    def test_scheme_calling_its_own_method_via_this(self, tmp_path: Path) -> None:
        (tmp_path / "Twice.primitive").write_text(_TWICE_PRIMITIVE)
        path = tmp_path / "TwiceScheme.scheme"
        path.write_text(_TWICE_SCHEME)
        _check(path)

    def test_proof_over_a_scheme_using_this(self, tmp_path: Path) -> None:
        (tmp_path / "Twice.primitive").write_text(_TWICE_PRIMITIVE)
        (tmp_path / "TwiceScheme.scheme").write_text(_TWICE_SCHEME)
        (tmp_path / "AgainUniform.game").write_text(_TWICE_GAMES)
        path = tmp_path / "again.proof"
        path.write_text(
            "import 'Twice.primitive';\n"
            "import 'TwiceScheme.scheme';\n"
            "import 'AgainUniform.game';\n\n"
            "proof:\n\n"
            "let:\n"
            "    Int n;\n"
            "    TwiceScheme T = TwiceScheme(n);\n\n"
            "theorem:\n"
            "    AgainUniform(T);\n\n"
            "games:\n"
            "    AgainUniform(T).Real against AgainUniform(T).Adversary;\n"
            "    AgainUniform(T).Random against AgainUniform(T).Adversary;\n"
        )
        _check(path)
