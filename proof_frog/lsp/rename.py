"""Rename support for ProofFrog LSP."""

from __future__ import annotations

import re

from lsprotocol import types as lsp  # type: ignore[import-untyped]

from proof_frog.lsp.document_state import DocumentState


def _find_simple_word_at_position(source: str, position: lsp.Position) -> str:
    """Extract the simple (non-dotted) identifier under the cursor."""
    lines = source.splitlines()
    if position.line >= len(lines):
        return ""
    line_text = lines[position.line]
    if not line_text:
        return ""
    col = min(position.character, len(line_text) - 1)

    start = col
    while start > 0 and (line_text[start - 1].isalnum() or line_text[start - 1] == "_"):
        start -= 1
    end = col
    while end < len(line_text) and (line_text[end].isalnum() or line_text[end] == "_"):
        end += 1

    return line_text[start:end]


def prepare_rename(state: DocumentState, position: lsp.Position) -> lsp.Range | None:
    """Check if the symbol at position can be renamed, return its range."""
    word = _find_simple_word_at_position(state.source, position)
    if not word or not word[0].isalpha():
        return None

    # Don't rename keywords
    keywords = {
        "if",
        "else",
        "for",
        "in",
        "to",
        "return",
        "true",
        "false",
        "None",
        "Primitive",
        "Scheme",
        "Game",
        "Reduction",
        "Phase",
        "proof",
        "let",
        "assume",
        "theorem",
        "games",
        "compose",
        "against",
        "Adversary",
        "induction",
        "from",
        "import",
        "export",
        "as",
        "extends",
        "requires",
        "oracles",
        "subsets",
        "union",
        "Int",
        "Bool",
        "Void",
        "BitString",
        "ModInt",
        "Set",
        "Map",
        "Array",
        "Initialize",
        "Finalize",
    }
    if word in keywords:
        return None

    # Find exact range of the word
    lines = state.source.splitlines()
    line_text = lines[position.line]
    col = min(position.character, len(line_text) - 1)

    start = col
    while start > 0 and (line_text[start - 1].isalnum() or line_text[start - 1] == "_"):
        start -= 1
    end = col
    while end < len(line_text) and (line_text[end].isalnum() or line_text[end] == "_"):
        end += 1

    return lsp.Range(
        start=lsp.Position(line=position.line, character=start),
        end=lsp.Position(line=position.line, character=end),
    )


def rename(
    state: DocumentState, position: lsp.Position, new_name: str
) -> lsp.WorkspaceEdit | None:
    """Rename all occurrences of the symbol at position."""
    word = _find_simple_word_at_position(state.source, position)
    if not word:
        return None

    # Find all whole-word occurrences in the document
    pattern = re.compile(r"\b" + re.escape(word) + r"\b")
    edits: list[lsp.TextEdit] = []

    for line_num, line_text in enumerate(state.source.splitlines()):
        for match in pattern.finditer(line_text):
            # Skip occurrences inside comments
            comment_pos = line_text.find("//")
            if 0 <= comment_pos <= match.start():
                continue
            # Skip occurrences inside string literals
            quote_pos = line_text.find("'")
            if quote_pos >= 0:
                end_quote = line_text.find("'", quote_pos + 1)
                if (
                    end_quote >= 0
                    and match.start() > quote_pos
                    and match.end() <= end_quote
                ):
                    continue

            edits.append(
                lsp.TextEdit(
                    range=lsp.Range(
                        start=lsp.Position(line=line_num, character=match.start()),
                        end=lsp.Position(line=line_num, character=match.end()),
                    ),
                    new_text=new_name,
                )
            )

    if not edits:
        return None

    return lsp.WorkspaceEdit(
        changes={state.uri: edits},
    )
