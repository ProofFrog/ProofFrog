"""Folding range support for ProofFrog LSP."""

from __future__ import annotations

from lsprotocol import types as lsp  # type: ignore[import-untyped]

from proof_frog import frog_ast
from proof_frog.lsp.document_state import DocumentState


def _method_ranges(methods: list[frog_ast.Method]) -> list[lsp.FoldingRange]:
    """Create folding ranges for methods."""
    ranges: list[lsp.FoldingRange] = []
    for method in methods:
        if method.line_num >= 1 and method.block.statements:
            last_stmt = method.block.statements[-1]
            if last_stmt.line_num >= method.line_num:
                ranges.append(
                    lsp.FoldingRange(
                        start_line=method.line_num - 1,
                        end_line=last_stmt.line_num,  # include closing brace
                        kind=lsp.FoldingRangeKind.Region,
                    )
                )
    return ranges


def _game_range(game: frog_ast.Game) -> lsp.FoldingRange | None:
    """Create a folding range for a Game or Reduction."""
    if game.line_num < 1:
        return None
    # Find the last line of the game by looking at its methods
    last_line = game.line_num
    for method in game.methods:
        if method.block.statements:
            last_line = max(last_line, method.block.statements[-1].line_num)
    if last_line > game.line_num:
        return lsp.FoldingRange(
            start_line=game.line_num - 1,
            end_line=last_line,  # include closing brace
            kind=lsp.FoldingRangeKind.Region,
        )
    return None


def get_folding_ranges(state: DocumentState) -> list[lsp.FoldingRange]:
    """Return folding ranges for the document."""
    ast = state.ast or state.last_good_ast
    if ast is None:
        return []

    ranges: list[lsp.FoldingRange] = []

    # Fold comment blocks (3+ consecutive line comments, and block comments)
    lines = state.source.splitlines()
    comment_start: int | None = None
    block_comment_start: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track /* ... */ block comments
        if block_comment_start is None and "/*" in stripped:
            block_comment_start = i
        if block_comment_start is not None and "*/" in stripped:
            if i > block_comment_start:
                ranges.append(
                    lsp.FoldingRange(
                        start_line=block_comment_start,
                        end_line=i,
                        kind=lsp.FoldingRangeKind.Comment,
                    )
                )
            block_comment_start = None
            continue

        if block_comment_start is not None:
            continue

        # Track consecutive // line comments
        if stripped.startswith("//"):
            if comment_start is None:
                comment_start = i
        else:
            if comment_start is not None and i - comment_start >= 3:
                ranges.append(
                    lsp.FoldingRange(
                        start_line=comment_start,
                        end_line=i - 1,
                        kind=lsp.FoldingRangeKind.Comment,
                    )
                )
            comment_start = None
    # Handle comment block at end of file
    if comment_start is not None and len(lines) - comment_start >= 3:
        ranges.append(
            lsp.FoldingRange(
                start_line=comment_start,
                end_line=len(lines) - 1,
                kind=lsp.FoldingRangeKind.Comment,
            )
        )

    if isinstance(ast, frog_ast.Primitive):
        # Fold the entire primitive body
        if ast.line_num >= 1 and (ast.fields or ast.methods):
            last_line = ast.line_num
            for field in ast.fields:
                last_line = max(last_line, field.line_num)
            for ms in ast.methods:
                last_line = max(last_line, ms.line_num)
            if last_line > ast.line_num:
                ranges.append(
                    lsp.FoldingRange(
                        start_line=ast.line_num - 1,
                        end_line=last_line,
                        kind=lsp.FoldingRangeKind.Region,
                    )
                )

    elif isinstance(ast, frog_ast.Scheme):
        ranges.extend(_method_ranges(ast.methods))

    elif isinstance(ast, frog_ast.GameFile):
        for game in ast.games:
            game_range = _game_range(game)
            if game_range:
                ranges.append(game_range)
            ranges.extend(_method_ranges(game.methods))

    elif isinstance(ast, frog_ast.ProofFile):
        # Fold helper games and reductions
        for helper in ast.helpers:
            helper_range = _game_range(helper)
            if helper_range:
                ranges.append(helper_range)
            ranges.extend(_method_ranges(helper.methods))

        # Fold the games: list
        if ast.steps:
            first_step_line = ast.steps[0].line_num
            last_step_line = ast.steps[-1].line_num
            if 1 <= first_step_line < last_step_line:
                ranges.append(
                    lsp.FoldingRange(
                        start_line=first_step_line - 1,
                        end_line=last_step_line - 1,
                        kind=lsp.FoldingRangeKind.Region,
                    )
                )

    return ranges
