"""Go-to-definition and hover for ProofFrog LSP."""

# pylint: disable=duplicate-code
# (shares structural patterns with other LSP modules)

from __future__ import annotations

import os

from lsprotocol import types as lsp  # type: ignore[import-untyped]

from proof_frog import frog_ast, frog_parser
from proof_frog.describe import (
    _describe_primitive,
    _describe_scheme,
    _describe_game_file,
)
from proof_frog.lsp.document_state import DocumentState


def _get_imports(ast: frog_ast.Root) -> list[frog_ast.Import]:
    """Extract the import list from any Root AST node."""
    if isinstance(ast, (frog_ast.GameFile, frog_ast.Scheme, frog_ast.ProofFile)):
        return ast.imports
    return []


def _get_fields_and_methods(
    root: frog_ast.Root,
) -> tuple[list[frog_ast.Field], list[frog_ast.MethodSignature | frog_ast.Method]]:
    """Extract fields and methods from a parsed file for hover/completion."""
    if isinstance(root, frog_ast.Primitive):
        return root.fields, root.methods  # type: ignore[return-value]
    if isinstance(root, frog_ast.Scheme):
        return root.fields, root.methods  # type: ignore[return-value]
    if isinstance(root, frog_ast.GameFile):
        fields: list[frog_ast.Field] = []
        methods: list[frog_ast.MethodSignature | frog_ast.Method] = []
        for game in root.games:
            fields.extend(game.fields)
            methods.extend(game.methods)
        return fields, methods
    return [], []


def _resolve_import_namespace(
    state: DocumentState,
) -> dict[str, tuple[str, frog_ast.Root]]:
    """Build {name -> (resolved_path, parsed_root)} for all imports."""
    namespace: dict[str, tuple[str, frog_ast.Root]] = {}
    ast = state.ast or state.last_good_ast
    if ast is None:
        return namespace
    for imp in _get_imports(ast):
        try:
            resolved = frog_parser.resolve_import_path(imp.filename, state.file_path)
            parsed = frog_parser.parse_file(resolved)
            name = imp.rename if imp.rename else parsed.get_export_name()
            namespace[name] = (resolved, parsed)
        except (frog_parser.ParseError, FileNotFoundError, ValueError):
            continue
    return namespace


def _find_import_at_position(
    state: DocumentState, position: lsp.Position
) -> frog_ast.Import | None:
    """Check if the cursor is on an import path string."""
    if state.ast is None:
        return None
    line = position.line + 1  # AST uses 1-based lines
    for imp in _get_imports(state.ast):
        if imp.line_num == line:
            return imp
    return None


def _find_word_at_position(source: str, position: lsp.Position) -> str:
    """Extract the dotted identifier under the cursor (e.g. 'E.KeyGen')."""
    lines = source.splitlines()
    if position.line >= len(lines):
        return ""
    line_text = lines[position.line]
    if not line_text:
        return ""
    col = min(position.character, len(line_text) - 1)

    # Expand from cursor position to capture dotted identifier
    start = col
    while start > 0 and (
        line_text[start - 1].isalnum() or line_text[start - 1] in "_."
    ):
        start -= 1
    end = col
    while end < len(line_text) and (line_text[end].isalnum() or line_text[end] in "_"):
        end += 1

    word = line_text[start:end]
    # Strip leading/trailing dots
    return word.strip(".")


def goto_definition(
    state: DocumentState, position: lsp.Position
) -> lsp.Location | None:
    """Return the location of the definition for the symbol at position."""
    # Check if cursor is on an import statement -> go to that file
    imp = _find_import_at_position(state, position)
    if imp is not None:
        try:
            resolved = frog_parser.resolve_import_path(imp.filename, state.file_path)
            if os.path.isfile(resolved):
                return lsp.Location(
                    uri=f"file://{resolved}",
                    range=lsp.Range(
                        start=lsp.Position(line=0, character=0),
                        end=lsp.Position(line=0, character=0),
                    ),
                )
        except (ValueError, FileNotFoundError):
            pass
        return None

    # Check if cursor is on a dotted name like E.KeyGen
    word = _find_word_at_position(state.source, position)
    if not word:
        return None

    namespace = _resolve_import_namespace(state)

    if "." in word:
        parts = word.split(".", 1)
        prefix, member = parts[0], parts[1]
        if prefix in namespace:
            resolved_path, parsed = namespace[prefix]
            # Find the member in the parsed file
            location = _find_member_location(resolved_path, parsed, member)
            if location is not None:
                return location
            # Fall back to top of file
            return lsp.Location(
                uri=f"file://{resolved_path}",
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=0),
                ),
            )
    elif word in namespace:
        resolved_path, _ = namespace[word]
        return lsp.Location(
            uri=f"file://{resolved_path}",
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=0, character=0),
            ),
        )

    return None


def _find_member_location(
    file_path: str, root: frog_ast.Root, member: str
) -> lsp.Location | None:
    """Find the line of a named member (method/field) within a parsed file."""
    members: list[frog_ast.ASTNode] = []
    if isinstance(root, frog_ast.Primitive):
        members = [*root.fields, *root.methods]
    elif isinstance(root, frog_ast.Scheme):
        members = [*root.fields, *root.methods]
    elif isinstance(root, frog_ast.GameFile):
        for game in root.games:
            if game.name == member:
                line = max(0, game.line_num - 1)
                return lsp.Location(
                    uri=f"file://{file_path}",
                    range=lsp.Range(
                        start=lsp.Position(line=line, character=0),
                        end=lsp.Position(line=line, character=0),
                    ),
                )
            members.extend(game.fields)
            members.extend(game.methods)

    for m in members:
        name: str | None = None
        if isinstance(m, frog_ast.Field):
            name = m.name
        elif isinstance(m, frog_ast.MethodSignature):
            name = m.name
        elif isinstance(m, frog_ast.Method):
            name = m.signature.name
        if name == member and m.line_num >= 1:
            line = m.line_num - 1
            return lsp.Location(
                uri=f"file://{file_path}",
                range=lsp.Range(
                    start=lsp.Position(line=line, character=0),
                    end=lsp.Position(line=line, character=0),
                ),
            )
    return None


def hover(state: DocumentState, position: lsp.Position) -> lsp.Hover | None:
    """Return hover info for the symbol at position."""
    # Check if cursor is on an import
    imp = _find_import_at_position(state, position)
    if imp is not None:
        try:
            resolved = frog_parser.resolve_import_path(imp.filename, state.file_path)
            parsed = frog_parser.parse_file(resolved)
            description: str
            if isinstance(parsed, frog_ast.Primitive):
                description = _describe_primitive(parsed)
            elif isinstance(parsed, frog_ast.Scheme):
                description = _describe_scheme(parsed)
            elif isinstance(parsed, frog_ast.GameFile):
                description = _describe_game_file(parsed)
            else:
                description = str(parsed)
            return lsp.Hover(
                contents=lsp.MarkupContent(
                    kind=lsp.MarkupKind.Markdown,
                    value=f"```\n{description}\n```",
                )
            )
        except (frog_parser.ParseError, FileNotFoundError, ValueError):
            pass
        return None

    word = _find_word_at_position(state.source, position)
    if not word:
        return None

    namespace = _resolve_import_namespace(state)

    # Hover on prefix of dotted name -> show module interface
    if "." in word:
        parts = word.split(".", 1)
        prefix, member = parts[0], parts[1]
        if prefix in namespace:
            _, parsed = namespace[prefix]
            # Show the specific member info
            info = _get_member_info(parsed, member)
            if info:
                return lsp.Hover(
                    contents=lsp.MarkupContent(
                        kind=lsp.MarkupKind.Markdown,
                        value=f"```\n{info}\n```",
                    )
                )
    elif word in namespace:
        _, parsed = namespace[word]
        description = ""
        if isinstance(parsed, frog_ast.Primitive):
            description = _describe_primitive(parsed)
        elif isinstance(parsed, frog_ast.Scheme):
            description = _describe_scheme(parsed)
        elif isinstance(parsed, frog_ast.GameFile):
            description = _describe_game_file(parsed)
        if description:
            return lsp.Hover(
                contents=lsp.MarkupContent(
                    kind=lsp.MarkupKind.Markdown,
                    value=f"```\n{description}\n```",
                )
            )

    return None


def _get_member_info(root: frog_ast.Root, member: str) -> str | None:
    """Get a description string for a specific member of a module."""
    if isinstance(root, frog_ast.Primitive):
        for field in root.fields:
            if field.name == member:
                return f"{field.type} {field.name}"
        for method in root.methods:
            if method.name == member:
                return str(method)
    elif isinstance(root, frog_ast.Scheme):
        for field in root.fields:
            if field.name == member:
                return f"{field.type} {field.name}"
        for scheme_method in root.methods:
            if scheme_method.signature.name == member:
                return str(scheme_method.signature)
    elif isinstance(root, frog_ast.GameFile):
        for game in root.games:
            if game.name == member:
                params_str = ", ".join(str(p) for p in game.parameters)
                return f"Game {game.name}({params_str})"
            for field in game.fields:
                if field.name == member:
                    return f"{field.type} {field.name}"
            for game_method in game.methods:
                if game_method.signature.name == member:
                    return str(game_method.signature)
    return None
