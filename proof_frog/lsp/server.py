"""ProofFrog Language Server — core server and event handlers."""

# The lsp package uses lazy imports so the main CLI doesn't pay for pygls
# unless the `lsp` command is actually invoked.
# pylint: disable=duplicate-code
# (diagnostics.py and server.py share some structural patterns with web_server.py)

from __future__ import annotations

import logging
from typing import Any

from lsprotocol import types as lsp  # type: ignore[import-untyped]
from pygls.lsp.server import LanguageServer  # type: ignore[import-untyped]

from proof_frog import frog_ast
from proof_frog.lsp.document_state import (
    DocumentState,
    uri_to_path,
    file_type_from_path,
)
from proof_frog.lsp.diagnostics import parse_and_diagnose, check_and_diagnose
from proof_frog.lsp.navigation import goto_definition, hover
from proof_frog.lsp.completion import get_completions, get_signature_help
from proof_frog.lsp.symbols import get_document_symbols
from proof_frog.lsp.rename import (
    prepare_rename as do_prepare_rename,
    rename as do_rename,
)
from proof_frog.lsp.folding import get_folding_ranges
from proof_frog.lsp.proof_features import (
    ProofStepResult,
    run_proof_verification,
    build_code_lenses,
    get_proof_steps_response,
    PROOF_STEPS_METHOD,
    PROOF_VERIFICATION_DONE,
)

logger = logging.getLogger(__name__)


def _publish(
    ls: FrogLanguageServer, uri: str, diagnostics: list[lsp.Diagnostic]
) -> None:
    """Publish diagnostics for a document URI."""
    ls.text_document_publish_diagnostics(  # type: ignore[attr-defined]
        lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
    )


class FrogLanguageServer(LanguageServer):  # type: ignore[misc]
    """Language server for ProofFrog's FrogLang DSL."""

    def __init__(self) -> None:
        super().__init__(
            "prooffrog-lsp",
            "v0.1.0",
            text_document_sync_kind=lsp.TextDocumentSyncKind.Full,
        )
        self.document_states: dict[str, DocumentState] = {}
        self.proof_results: dict[str, list[ProofStepResult]] = {}


server = FrogLanguageServer()


def _get_or_create_state(
    ls: FrogLanguageServer, uri: str, source: str, version: int = 0
) -> DocumentState | None:
    """Return a DocumentState for the given URI, or None if not a FrogLang file."""
    path = uri_to_path(uri)
    ft = file_type_from_path(path)
    if ft is None:
        return None
    if uri in ls.document_states:
        state = ls.document_states[uri]
        state.source = source
        state.version = version
        return state
    state = DocumentState(
        uri=uri, file_path=path, file_type=ft, source=source, version=version
    )
    ls.document_states[uri] = state
    return state


# -- Document synchronization handlers --


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)  # type: ignore[misc]
def did_open(ls: FrogLanguageServer, params: lsp.DidOpenTextDocumentParams) -> None:
    """Parse on open and publish diagnostics."""
    uri = params.text_document.uri
    state = _get_or_create_state(
        ls, uri, params.text_document.text, params.text_document.version
    )
    if state is None:
        return
    diagnostics = parse_and_diagnose(state)
    _publish(ls, uri, diagnostics)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)  # type: ignore[misc]
def did_change(ls: FrogLanguageServer, params: lsp.DidChangeTextDocumentParams) -> None:
    """Re-parse on every change and publish parse diagnostics."""
    uri = params.text_document.uri
    if not params.content_changes:
        return
    new_text = params.content_changes[-1].text
    state = _get_or_create_state(ls, uri, new_text, params.text_document.version)
    if state is None:
        return
    diagnostics = parse_and_diagnose(state)
    _publish(ls, uri, diagnostics)


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)  # type: ignore[misc]
def did_save(ls: FrogLanguageServer, params: lsp.DidSaveTextDocumentParams) -> None:
    """Run semantic analysis on save; also run proof verification for .proof files."""
    uri = params.text_document.uri
    state = ls.document_states.get(uri)
    if state is None:
        return

    # For .proof files, run full proof verification (includes semantic analysis)
    if state.file_type == frog_ast.FileType.PROOF:
        diagnostics, step_results = run_proof_verification(state)
        ls.proof_results[uri] = step_results
        _publish(ls, uri, diagnostics)
        # Notify the client that verification is done so it can refresh the tree
        ls.protocol.notify(  # type: ignore[attr-defined]
            PROOF_VERIFICATION_DONE,
            {"uri": uri, "steps": get_proof_steps_response(step_results)},
        )
        # Ask the client to re-request code lenses with the updated results
        ls.workspace_code_lens_refresh(None)
        return

    diagnostics = check_and_diagnose(state)
    _publish(ls, uri, diagnostics)


@server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)  # type: ignore[misc]
def did_close(ls: FrogLanguageServer, params: lsp.DidCloseTextDocumentParams) -> None:
    """Clean up state and clear diagnostics when a document is closed."""
    uri = params.text_document.uri
    ls.document_states.pop(uri, None)
    ls.proof_results.pop(uri, None)
    _publish(ls, uri, [])


# -- Navigation handlers --


@server.feature(lsp.TEXT_DOCUMENT_DEFINITION)  # type: ignore[misc]
def definition(
    ls: FrogLanguageServer, params: lsp.DefinitionParams
) -> lsp.Location | None:
    """Go to definition for imports and references."""
    state = ls.document_states.get(params.text_document.uri)
    if state is None:
        return None
    return goto_definition(state, params.position)


@server.feature(lsp.TEXT_DOCUMENT_HOVER)  # type: ignore[misc]
def hover_handler(ls: FrogLanguageServer, params: lsp.HoverParams) -> lsp.Hover | None:
    """Show type/interface info on hover."""
    state = ls.document_states.get(params.text_document.uri)
    if state is None:
        return None
    return hover(state, params.position)


# -- Completion handler --


@server.feature(  # type: ignore[misc]
    lsp.TEXT_DOCUMENT_COMPLETION,
    lsp.CompletionOptions(trigger_characters=["."]),
)
def completions(
    ls: FrogLanguageServer, params: lsp.CompletionParams
) -> list[lsp.CompletionItem]:
    """Provide completion items."""
    state = ls.document_states.get(params.text_document.uri)
    if state is None:
        return []
    return get_completions(state, params.position)


# -- Signature help --


@server.feature(  # type: ignore[misc]
    lsp.TEXT_DOCUMENT_SIGNATURE_HELP,
    lsp.SignatureHelpOptions(trigger_characters=["(", ","]),
)
def signature_help(
    ls: FrogLanguageServer, params: lsp.SignatureHelpParams
) -> lsp.SignatureHelp | None:
    """Provide signature help for function calls."""
    state = ls.document_states.get(params.text_document.uri)
    if state is None:
        return None
    return get_signature_help(state, params.position)


# -- Document symbols --


@server.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)  # type: ignore[misc]
def document_symbol(
    ls: FrogLanguageServer, params: lsp.DocumentSymbolParams
) -> list[lsp.DocumentSymbol]:
    """Provide document symbols for the Outline panel."""
    state = ls.document_states.get(params.text_document.uri)
    if state is None:
        return []
    return get_document_symbols(state)


# -- Rename --


@server.feature(lsp.TEXT_DOCUMENT_PREPARE_RENAME)  # type: ignore[misc]
def prepare_rename(
    ls: FrogLanguageServer, params: lsp.PrepareRenameParams
) -> lsp.Range | None:
    """Check if the symbol at position can be renamed."""
    state = ls.document_states.get(params.text_document.uri)
    if state is None:
        return None
    return do_prepare_rename(state, params.position)


@server.feature(lsp.TEXT_DOCUMENT_RENAME)  # type: ignore[misc]
def rename_handler(
    ls: FrogLanguageServer, params: lsp.RenameParams
) -> lsp.WorkspaceEdit | None:
    """Rename all occurrences of the symbol at position."""
    state = ls.document_states.get(params.text_document.uri)
    if state is None:
        return None
    return do_rename(state, params.position, params.new_name)


# -- Folding ranges --


@server.feature(lsp.TEXT_DOCUMENT_FOLDING_RANGE)  # type: ignore[misc]
def folding_range(
    ls: FrogLanguageServer, params: lsp.FoldingRangeParams
) -> list[lsp.FoldingRange]:
    """Provide folding ranges for code blocks."""
    state = ls.document_states.get(params.text_document.uri)
    if state is None:
        return []
    return get_folding_ranges(state)


# -- Proof features --


@server.feature(  # type: ignore[misc]
    lsp.TEXT_DOCUMENT_CODE_LENS,
    lsp.CodeLensOptions(resolve_provider=False),
)
def code_lens(ls: FrogLanguageServer, params: lsp.CodeLensParams) -> list[lsp.CodeLens]:
    """Provide code lenses for proof hop results."""
    uri = params.text_document.uri
    state = ls.document_states.get(uri)
    if state is None or state.file_type != frog_ast.FileType.PROOF:
        return []
    step_results = ls.proof_results.get(uri, [])
    return build_code_lenses(state, step_results)


@server.command(PROOF_STEPS_METHOD)  # type: ignore[misc]
def proof_steps_command(
    ls: FrogLanguageServer, args: list[Any]
) -> list[dict[str, Any]]:
    """Custom command to get proof step results for the tree view."""
    if not args:
        return []
    uri = str(args[0])
    step_results = ls.proof_results.get(uri, [])
    return get_proof_steps_response(step_results)


def run_server() -> None:
    """Start the ProofFrog LSP server on stdio."""
    # Suppress noisy "Cancel notification for unknown message id" warnings
    logging.getLogger("pygls.protocol.json_rpc").setLevel(logging.ERROR)
    server.start_io()
