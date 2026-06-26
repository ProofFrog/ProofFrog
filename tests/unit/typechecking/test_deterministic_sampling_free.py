"""F-007: a ``deterministic``-annotated method body must be sampling-free.

Many canonicalization passes trust the ``deterministic`` modifier (via
``has_nondeterministic_call``) to mean same-input/same-output. A scheme method
that declares ``deterministic`` but samples randomness in its body breaks that
promise, so the typechecker must reject it.
"""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis

_PRIMITIVE = """\
Primitive P(Int n) {
    deterministic BitString<n> Det(BitString<n> x);
    BitString<n> Rand(BitString<n> x);
}
"""


def _write_primitive(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "P.primitive").write_text(_PRIMITIVE)


def _check(tmp_path: Path, scheme_body: str) -> None:
    _write_primitive(tmp_path)
    source = (
        "import 'fixtures/P.primitive';\n\n"
        "Scheme S(Int n) extends P {\n" + scheme_body + "}\n"
    )
    file_path = str(tmp_path / "test.scheme")
    Path(file_path).write_text(source)
    root = frog_parser.parse_file(file_path)
    semantic_analysis.check_well_formed(root, file_path)


def test_deterministic_body_with_sample_rejected(tmp_path: Path) -> None:
    """A `deterministic` method sampling via `<-` must fail typechecking."""
    body = (
        "    deterministic BitString<n> Det(BitString<n> x) {\n"
        "        BitString<n> r <- BitString<n>;\n"
        "        return r;\n"
        "    }\n"
        "    BitString<n> Rand(BitString<n> x) {\n"
        "        return x;\n"
        "    }\n"
    )
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check(tmp_path, body)


def test_deterministic_body_with_uniq_sample_rejected(tmp_path: Path) -> None:
    """A `deterministic` method sampling via `<-uniq` must fail typechecking."""
    body = (
        "    deterministic BitString<n> Det(BitString<n> x) {\n"
        "        Set seen = {};\n"
        "        BitString<n> r <-uniq[seen] BitString<n>;\n"
        "        return r;\n"
        "    }\n"
        "    BitString<n> Rand(BitString<n> x) {\n"
        "        return x;\n"
        "    }\n"
    )
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check(tmp_path, body)


def test_deterministic_body_sampling_free_accepted(tmp_path: Path) -> None:
    """A genuinely sampling-free `deterministic` body type-checks."""
    body = (
        "    deterministic BitString<n> Det(BitString<n> x) {\n"
        "        return x;\n"
        "    }\n"
        "    BitString<n> Rand(BitString<n> x) {\n"
        "        return x;\n"
        "    }\n"
    )
    _check(tmp_path, body)  # should not raise


def test_nondeterministic_body_may_sample(tmp_path: Path) -> None:
    """A method NOT annotated `deterministic` may sample freely."""
    body = (
        "    deterministic BitString<n> Det(BitString<n> x) {\n"
        "        return x;\n"
        "    }\n"
        "    BitString<n> Rand(BitString<n> x) {\n"
        "        BitString<n> r <- BitString<n>;\n"
        "        return r;\n"
        "    }\n"
    )
    _check(tmp_path, body)  # should not raise


def test_deterministic_error_message_mentions_sampling(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The error names the method and the sampling-free requirement."""
    body = (
        "    deterministic BitString<n> Det(BitString<n> x) {\n"
        "        BitString<n> r <- BitString<n>;\n"
        "        return r;\n"
        "    }\n"
        "    BitString<n> Rand(BitString<n> x) {\n"
        "        return x;\n"
        "    }\n"
    )
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check(tmp_path, body)
    err = capsys.readouterr().err
    assert "deterministic" in err
    assert "sampling-free" in err
    assert "Det" in err
