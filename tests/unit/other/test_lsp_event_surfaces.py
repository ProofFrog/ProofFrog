"""Editor surfaces for event theorems: LSP symbols/keywords and describe."""

from pathlib import Path

from lsprotocol import types as lsp

from proof_frog import frog_ast, frog_parser
from proof_frog.describe import describe_file
from proof_frog.lsp import completion, rename
from proof_frog.lsp.document_state import DocumentState
from proof_frog.lsp.symbols import get_document_symbols

UPTO = Path(__file__).resolve().parents[2] / "integration" / "upto_fixtures"


def _symbols(name: str) -> list[str]:
    path = UPTO / name
    state = DocumentState(
        uri=path.as_uri(),
        file_path=str(path),
        file_type=frog_ast.FileType.PROOF,
        ast=frog_parser.parse_proof_file(str(path)),
    )
    return [s.name for s in get_document_symbols(state)]


def test_event_theorem_symbol() -> None:
    assert "theorem: event bad of BadGuess(S)" in _symbols("BadGuessEvent.proof")


def test_describe_event_theorem() -> None:
    out = describe_file(str(UPTO / "BadGuessEvent.proof"))
    assert "Theorem: event bad of BadGuess(S);" in out


def test_describe_lists_event_lemma_and_assumption() -> None:
    assert "event bad of BadGuess(S) by 'BadGuessEvent.proof';" in describe_file(
        str(UPTO / "outer.proof")
    )
    assert "  event bad of BadGuess(S);" in describe_file(
        str(UPTO / "outer_opaque.proof")
    )


def test_event_keywords_complete_and_do_not_rename() -> None:
    # pylint: disable=protected-access
    source = "theorem:\n    event bad of P(S) at Initialize;\n"
    state = DocumentState(
        uri="file:///t.proof",
        file_path="/t.proof",
        file_type=frog_ast.FileType.PROOF,
        source=source,
    )
    for keyword in ("event", "of", "at"):
        assert keyword in completion._PROOF_KEYWORDS
        col = source.splitlines()[1].index(f" {keyword} ") + 1
        position = lsp.Position(line=1, character=col)
        assert rename.prepare_rename(state, position) is None, keyword
