"""Per-document state tracking for the ProofFrog LSP server."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import unquote

from proof_frog import frog_ast
from proof_frog.frog_parser import ParseError


@dataclass
class DocumentState:
    """Cached state for a single open document."""

    uri: str
    file_path: str
    file_type: frog_ast.FileType
    source: str = ""
    ast: frog_ast.Root | None = None
    last_good_ast: frog_ast.Root | None = None
    parse_errors: list[ParseError] = field(default_factory=list)
    version: int = 0


def uri_to_path(uri: str) -> str:
    """Convert a file:// URI to a local filesystem path."""
    if uri.startswith("file://"):
        return unquote(uri[7:])
    return unquote(uri)


def file_type_from_path(path: str) -> frog_ast.FileType | None:
    """Determine the FrogLang file type from a file extension."""
    ext = os.path.splitext(path)[1].lstrip(".")
    try:
        return frog_ast.FileType(ext)
    except ValueError:
        return None
