"""Document symbol provider for ProofFrog FrogLang files."""

from __future__ import annotations

from lsprotocol import types as lsp  # type: ignore[import-untyped]

from proof_frog import frog_ast
from proof_frog.lsp.document_state import DocumentState


def _range_from_line(line: int) -> lsp.Range:
    """Create a single-line range from a 1-based line number."""
    zero = max(line - 1, 0)
    return lsp.Range(
        start=lsp.Position(line=zero, character=0),
        end=lsp.Position(line=zero, character=0),
    )


def _method_symbols(methods: list[frog_ast.Method]) -> list[lsp.DocumentSymbol]:
    """Create symbols for a list of methods."""
    symbols: list[lsp.DocumentSymbol] = []
    for method in methods:
        name = method.signature.name
        r = _range_from_line(method.line_num)
        symbols.append(
            lsp.DocumentSymbol(
                name=name,
                kind=lsp.SymbolKind.Method,
                range=r,
                selection_range=r,
            )
        )
    return symbols


def _field_symbols(fields: list[frog_ast.Field]) -> list[lsp.DocumentSymbol]:
    """Create symbols for state/let fields."""
    symbols: list[lsp.DocumentSymbol] = []
    for field in fields:
        r = _range_from_line(field.line_num)
        symbols.append(
            lsp.DocumentSymbol(
                name=field.name,
                kind=lsp.SymbolKind.Field,
                range=r,
                selection_range=r,
            )
        )
    return symbols


def _game_symbols(game: frog_ast.Game) -> lsp.DocumentSymbol:
    """Create a symbol for a Game (or Reduction) with method children."""
    r = _range_from_line(game.line_num)
    is_reduction = isinstance(game, frog_ast.Reduction)
    kind = lsp.SymbolKind.Interface if is_reduction else lsp.SymbolKind.Class
    prefix = "Reduction " if is_reduction else "Game "
    children = _method_symbols(game.methods)
    return lsp.DocumentSymbol(
        name=f"{prefix}{game.name}",
        kind=kind,
        range=r,
        selection_range=r,
        children=children if children else None,
    )


def _step_symbols(
    steps: list[frog_ast.ProofStep],
) -> list[lsp.DocumentSymbol]:
    """Create symbols for proof game steps."""
    symbols: list[lsp.DocumentSymbol] = []
    step_num = 0
    for step in steps:
        if isinstance(step, frog_ast.Step):
            r = _range_from_line(step.line_num)
            symbols.append(
                lsp.DocumentSymbol(
                    name=f"Step {step_num}: {step}",
                    kind=lsp.SymbolKind.Event,
                    range=r,
                    selection_range=r,
                )
            )
            step_num += 1
        elif isinstance(step, frog_ast.StepAssumption):
            r = _range_from_line(step.line_num)
            symbols.append(
                lsp.DocumentSymbol(
                    name=str(step),
                    kind=lsp.SymbolKind.Constant,
                    range=r,
                    selection_range=r,
                )
            )
        elif isinstance(step, frog_ast.Induction):
            r = _range_from_line(step.line_num)
            children = _step_symbols(step.steps)
            symbols.append(
                lsp.DocumentSymbol(
                    name=f"Induction {step.name}",
                    kind=lsp.SymbolKind.Namespace,
                    range=r,
                    selection_range=r,
                    children=children if children else None,
                )
            )
    return symbols


def get_document_symbols(state: DocumentState) -> list[lsp.DocumentSymbol]:
    """Return document symbols for the given file."""
    ast = state.ast
    if ast is None:
        return []

    symbols: list[lsp.DocumentSymbol] = []

    if isinstance(ast, frog_ast.Primitive):
        r = _range_from_line(ast.line_num)
        children: list[lsp.DocumentSymbol] = []
        for ms in ast.methods:
            mr = _range_from_line(ms.line_num)
            children.append(
                lsp.DocumentSymbol(
                    name=ms.name,
                    kind=lsp.SymbolKind.Method,
                    range=mr,
                    selection_range=mr,
                )
            )
        children.extend(_field_symbols(ast.fields))
        symbols.append(
            lsp.DocumentSymbol(
                name=f"Primitive {ast.name}",
                kind=lsp.SymbolKind.Module,
                range=r,
                selection_range=r,
                children=children if children else None,
            )
        )

    elif isinstance(ast, frog_ast.Scheme):
        r = _range_from_line(ast.line_num)
        children = _method_symbols(ast.methods)
        children.extend(_field_symbols(ast.fields))
        symbols.append(
            lsp.DocumentSymbol(
                name=f"Scheme {ast.name}",
                kind=lsp.SymbolKind.Module,
                range=r,
                selection_range=r,
                children=children if children else None,
            )
        )

    elif isinstance(ast, frog_ast.GameFile):
        for game in ast.games:
            symbols.append(_game_symbols(game))

    elif isinstance(ast, frog_ast.ProofFile):
        # Helper games and reductions
        for helper in ast.helpers:
            symbols.append(_game_symbols(helper))

        # Theorem
        theorem_r = _range_from_line(ast.theorem.line_num)
        symbols.append(
            lsp.DocumentSymbol(
                name=f"theorem: {ast.theorem}",
                kind=lsp.SymbolKind.Property,
                range=theorem_r,
                selection_range=theorem_r,
            )
        )

        # Game steps
        step_syms = _step_symbols(ast.steps)
        if step_syms:
            # Find line of first step for the "games:" container
            games_r = _range_from_line(ast.steps[0].line_num)
            symbols.append(
                lsp.DocumentSymbol(
                    name="games",
                    kind=lsp.SymbolKind.Array,
                    range=games_r,
                    selection_range=games_r,
                    children=step_syms,
                )
            )

    return symbols
