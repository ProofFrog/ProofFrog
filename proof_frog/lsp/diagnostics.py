"""Convert ProofFrog parse/semantic errors to LSP diagnostics."""

from __future__ import annotations

import io
import os
import re
import tempfile
from contextlib import redirect_stdout, redirect_stderr

from lsprotocol import types as lsp  # type: ignore[import-untyped]

from proof_frog import frog_parser, semantic_analysis
from proof_frog.lsp.document_state import DocumentState


def _parse_error_location(
    msg: str,
) -> tuple[int, int, str]:
    """Extract line, column, and message from a semantic analysis error.

    Error format: ``filename:line:col: error: message``
    Returns (0-based line, column, message text).  Falls back to (0, 0, msg).
    """
    match = re.search(r":(\d+):(\d+): error: (.+)", msg)
    if match:
        line = max(0, int(match.group(1)) - 1)
        col = int(match.group(2))
        return line, col, match.group(3)
    # Try without column
    match = re.search(r":(\d+): error: (.+)", msg)
    if match:
        line = max(0, int(match.group(1)) - 1)
        return line, 0, match.group(2)
    return 0, 0, msg


def parse_and_diagnose(state: DocumentState) -> list[lsp.Diagnostic]:
    """Parse the document source and return diagnostics.

    Updates ``state.ast`` and ``state.parse_errors`` as a side effect.
    """
    ast, errors = frog_parser.parse_string_collecting_errors(
        state.source, state.file_type, file_name=state.file_path
    )
    state.ast = ast
    if ast is not None and not errors:
        state.last_good_ast = ast
    state.parse_errors = errors

    diagnostics: list[lsp.Diagnostic] = []
    for err in errors:
        line = max(0, err.line - 1)  # LSP uses 0-based lines
        col = max(0, err.column)
        end_col = col + max(1, len(err.token)) if err.token else col + 1
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=line, character=col),
                    end=lsp.Position(line=line, character=end_col),
                ),
                message=str(err.args[0]),
                severity=lsp.DiagnosticSeverity.Error,
                source="prooffrog",
            )
        )
    return diagnostics


def check_and_diagnose(state: DocumentState) -> list[lsp.Diagnostic]:
    """Run semantic analysis on the saved file and return diagnostics.

    This writes the current source to a temporary file so that import
    resolution works correctly, then runs parse + semantic analysis.
    """
    diagnostics: list[lsp.Diagnostic] = []

    # Use the on-disk file if it exists; otherwise write a temp file
    file_path = state.file_path
    tmp_path: str | None = None
    if not os.path.isfile(file_path):
        ext = os.path.splitext(file_path)[1]
        fd, tmp_path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(state.source)
        file_path = tmp_path

    try:
        root = frog_parser.parse_file(file_path)
    except frog_parser.ParseError as e:
        line = max(0, e.line - 1)
        col = max(0, e.column)
        end_col = col + max(1, len(e.token)) if e.token else col + 1
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=line, character=col),
                    end=lsp.Position(line=line, character=end_col),
                ),
                message=str(e.args[0]),
                severity=lsp.DiagnosticSeverity.Error,
                source="prooffrog",
            )
        )
        return diagnostics
    except (FileNotFoundError, ValueError) as e:
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=0),
                ),
                message=str(e),
                severity=lsp.DiagnosticSeverity.Error,
                source="prooffrog",
            )
        )
        return diagnostics
    finally:
        if tmp_path is not None:
            os.unlink(tmp_path)

    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            semantic_analysis.check_well_formed(root, file_path)
    except semantic_analysis.FailedTypeCheck:
        msg = buf.getvalue().strip() or "Type check failed."
        line, col, text = _parse_error_location(msg)
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=line, character=col),
                    end=lsp.Position(line=line, character=999),
                ),
                message=text,
                severity=lsp.DiagnosticSeverity.Error,
                source="prooffrog",
            )
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=999),
                ),
                message=f"Analysis error: {e}",
                severity=lsp.DiagnosticSeverity.Error,
                source="prooffrog",
            )
        )

    return diagnostics
