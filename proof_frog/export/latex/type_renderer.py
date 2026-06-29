"""Render FrogLang ``Type`` AST nodes to LaTeX math.

``TypeRenderer`` now lives in :mod:`.expr_renderer`, co-located with
``ExprRenderer`` because the two mutually depend on each other (TypeRenderer
composes an ExprRenderer; ExprRenderer renders a ``Type`` in expression
position via TypeRenderer). Keeping them in one module avoids an import cycle.
This module re-exports ``TypeRenderer`` for backward compatibility.
"""

from __future__ import annotations

from .expr_renderer import TypeRenderer

__all__ = ["TypeRenderer"]
