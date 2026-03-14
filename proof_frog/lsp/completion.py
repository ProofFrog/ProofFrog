"""Completion support for ProofFrog LSP."""

# pylint: disable=duplicate-code
# (shares structural patterns with other LSP modules)

from __future__ import annotations

from lsprotocol import types as lsp  # type: ignore[import-untyped]

from proof_frog import frog_ast
from proof_frog.lsp.document_state import DocumentState
from proof_frog.lsp.navigation import _resolve_import_namespace

# Keywords shared across all file types
_COMMON_KEYWORDS = [
    "if",
    "else",
    "for",
    "in",
    "to",
    "return",
    "true",
    "false",
    "None",
]

# Type keywords available in all file types
_TYPE_KEYWORDS = [
    "Int",
    "Bool",
    "Void",
    "BitString",
    "ModInt",
    "Set",
    "Map",
    "Array",
]

_PRIMITIVE_KEYWORDS = ["Primitive"]

_SCHEME_KEYWORDS = ["Scheme", "extends", "requires", "import"]

_GAME_KEYWORDS = ["Game", "Phase", "oracles", "export", "as", "import"]

_PROOF_KEYWORDS = [
    "Game",
    "Reduction",
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
]


def _keywords_for_file_type(file_type: frog_ast.FileType) -> list[str]:
    """Return the set of keywords appropriate for a file type."""
    base = _COMMON_KEYWORDS + _TYPE_KEYWORDS
    match file_type:
        case frog_ast.FileType.PRIMITIVE:
            return base + _PRIMITIVE_KEYWORDS
        case frog_ast.FileType.SCHEME:
            return base + _SCHEME_KEYWORDS
        case frog_ast.FileType.GAME:
            return base + _GAME_KEYWORDS
        case frog_ast.FileType.PROOF:
            return base + _PROOF_KEYWORDS


def get_completions(
    state: DocumentState, position: lsp.Position
) -> list[lsp.CompletionItem]:
    """Return completion items for the given position."""
    items: list[lsp.CompletionItem] = []

    # Check if we're completing after a dot (e.g. "E.")
    lines = state.source.splitlines()
    if position.line < len(lines):
        line_text = lines[position.line]
        col = position.character

        # Find the prefix before the cursor
        prefix_start = col
        while prefix_start > 0 and (
            line_text[prefix_start - 1].isalnum() or line_text[prefix_start - 1] == "_"
        ):
            prefix_start -= 1

        # Check if there's a dot before the prefix
        dot_pos = prefix_start - 1
        if dot_pos >= 0 and line_text[dot_pos] == ".":
            # Find the module name before the dot
            mod_end = dot_pos
            mod_start = dot_pos
            while mod_start > 0 and (
                line_text[mod_start - 1].isalnum() or line_text[mod_start - 1] == "_"
            ):
                mod_start -= 1
            module_name = line_text[mod_start:mod_end]

            if module_name:
                items = _complete_module_members(state, module_name)
                if items:
                    return items

    # Keyword completions
    for kw in _keywords_for_file_type(state.file_type):
        items.append(
            lsp.CompletionItem(
                label=kw,
                kind=lsp.CompletionItemKind.Keyword,
            )
        )

    # Import name completions (top-level names from imports)
    if state.ast is not None:
        namespace = _resolve_import_namespace(state)
        for name, (_, parsed) in namespace.items():
            kind = lsp.CompletionItemKind.Module
            detail = ""
            if isinstance(parsed, frog_ast.Primitive):
                kind = lsp.CompletionItemKind.Interface
                detail = f"Primitive: {parsed.name}"
            elif isinstance(parsed, frog_ast.Scheme):
                kind = lsp.CompletionItemKind.Class
                detail = f"Scheme: {parsed.name}"
            elif isinstance(parsed, frog_ast.GameFile):
                kind = lsp.CompletionItemKind.Module
                detail = f"Game: {parsed.name}"
            items.append(
                lsp.CompletionItem(
                    label=name,
                    kind=kind,
                    detail=detail,
                )
            )

    return items


def _complete_module_members(
    state: DocumentState, module_name: str
) -> list[lsp.CompletionItem]:
    """Return completion items for members of a module (after 'Module.')."""
    namespace = _resolve_import_namespace(state)
    if module_name not in namespace:
        return []

    _, parsed = namespace[module_name]
    items: list[lsp.CompletionItem] = []

    if isinstance(parsed, frog_ast.Primitive):
        for field in parsed.fields:
            items.append(
                lsp.CompletionItem(
                    label=field.name,
                    kind=lsp.CompletionItemKind.Field,
                    detail=str(field.type),
                )
            )
        for method in parsed.methods:
            items.append(
                lsp.CompletionItem(
                    label=method.name,
                    kind=lsp.CompletionItemKind.Method,
                    detail=str(method),
                )
            )
    elif isinstance(parsed, frog_ast.Scheme):
        for field in parsed.fields:
            items.append(
                lsp.CompletionItem(
                    label=field.name,
                    kind=lsp.CompletionItemKind.Field,
                    detail=str(field.type),
                )
            )
        for scheme_method in parsed.methods:
            items.append(
                lsp.CompletionItem(
                    label=scheme_method.signature.name,
                    kind=lsp.CompletionItemKind.Method,
                    detail=str(scheme_method.signature),
                )
            )
    elif isinstance(parsed, frog_ast.GameFile):
        for game in parsed.games:
            params_str = ", ".join(str(p) for p in game.parameters)
            items.append(
                lsp.CompletionItem(
                    label=game.name,
                    kind=lsp.CompletionItemKind.Class,
                    detail=f"Game {game.name}({params_str})",
                )
            )

    return items
