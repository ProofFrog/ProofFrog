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

_SCHEME_KEYWORDS = ["Scheme", "extends", "requires", "import", "this"]

_GAME_KEYWORDS = ["Game", "export", "as", "import"]

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


def _resolve_module(state: DocumentState, module_name: str) -> frog_ast.Root | None:
    """Resolve a module name to its parsed AST (import or let binding)."""
    namespace = _resolve_import_namespace(state)
    if module_name in namespace:
        _, parsed = namespace[module_name]
        return parsed
    return _resolve_let_binding(state, module_name, namespace)


def _find_method_signature(
    parsed: frog_ast.Root, method_name: str
) -> frog_ast.MethodSignature | None:
    """Find a method signature by name in a parsed primitive or scheme."""
    if isinstance(parsed, frog_ast.Primitive):
        for ms in parsed.methods:
            if ms.name == method_name:
                return ms
    elif isinstance(parsed, frog_ast.Scheme):
        for method in parsed.methods:
            if method.signature.name == method_name:
                return method.signature
    return None


def get_signature_help(
    state: DocumentState, position: lsp.Position
) -> lsp.SignatureHelp | None:
    """Return signature help for a function call at the given position."""
    lines = state.source.splitlines()
    if position.line >= len(lines):
        return None
    line_text = lines[position.line]
    col = position.character

    # Walk backwards from cursor to find the matching '(' and count commas
    paren_depth = 0
    active_param = 0
    paren_pos = -1
    for i in range(col - 1, -1, -1):
        ch = line_text[i]
        if ch == ")":
            paren_depth += 1
        elif ch == "(":
            if paren_depth == 0:
                paren_pos = i
                break
            paren_depth -= 1
        elif ch == "," and paren_depth == 0:
            active_param += 1

    if paren_pos < 0:
        return None

    # Extract the dotted name before the '('
    name_end = paren_pos
    name_start = paren_pos
    while name_start > 0 and (
        line_text[name_start - 1].isalnum() or line_text[name_start - 1] in "_."
    ):
        name_start -= 1
    full_name = line_text[name_start:name_end]

    if "." not in full_name:
        return None

    parts = full_name.rsplit(".", 1)
    module_name, method_name = parts[0], parts[1]

    parsed = _resolve_module(state, module_name)
    if parsed is None:
        return None

    sig = _find_method_signature(parsed, method_name)
    if sig is None:
        return None

    param_infos = [
        lsp.ParameterInformation(label=f"{p.type} {p.name}") for p in sig.parameters
    ]

    return lsp.SignatureHelp(
        signatures=[
            lsp.SignatureInformation(
                label=str(sig),
                parameters=param_infos,
            )
        ],
        active_signature=0,
        active_parameter=active_param,
    )


def _resolve_let_binding(
    state: DocumentState,
    name: str,
    namespace: dict[str, tuple[str, frog_ast.Root]],
) -> frog_ast.Root | None:
    """If *name* is a let: binding in a proof, resolve it to its primitive/scheme type."""
    ast = state.ast or state.last_good_ast
    if not isinstance(ast, frog_ast.ProofFile):
        return None
    for let_field in ast.lets:
        if let_field.name == name:
            # The type name (e.g. "SymEnc") refers to an import
            type_name = str(let_field.type)
            if type_name in namespace:
                _, parsed = namespace[type_name]
                return parsed
            return None
    return None


def _items_for_parsed(parsed: frog_ast.Root) -> list[lsp.CompletionItem]:
    """Return completion items for members of a parsed primitive/scheme/game."""
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


def _complete_module_members(
    state: DocumentState, module_name: str
) -> list[lsp.CompletionItem]:
    """Return completion items for members of a module (after 'Module.')."""
    namespace = _resolve_import_namespace(state)

    # Direct import (e.g. SymEnc.KeyGen)
    if module_name in namespace:
        _, parsed = namespace[module_name]
        return _items_for_parsed(parsed)

    # Let binding in a proof (e.g. E2.KeyGen where E2 is defined in let:)
    resolved = _resolve_let_binding(state, module_name, namespace)
    if resolved is not None:
        return _items_for_parsed(resolved)

    return []
