"""Macro registry for LaTeX export.

Collects identifiers that should be rendered as macros (algorithm names,
scheme names, game names, security properties, adversaries) and emits a
preamble of ``\\providecommand`` lines so user redefinitions in their own
preamble win.
"""

from __future__ import annotations

# A small set of LaTeX builtins we must not redefine. Extend as needed.
_LATEX_BUILTINS = {
    "Pr",
    "Re",
    "Im",
    "log",
    "exp",
    "min",
    "max",
    "gcd",
    "deg",
    "dim",
    "det",
    "ker",
    "lim",
    "sup",
    "inf",
}


class MacroRegistry:
    """Tracks identifiers that should render as LaTeX macros."""

    def __init__(self) -> None:
        # name -> (macro_token_without_backslash, body)
        self._entries: dict[str, tuple[str, str]] = {}

    def register_algorithm(self, name: str) -> str:
        """Register an algorithm/scheme/game/property name.

        Returns the LaTeX token (e.g. ``\\Enc``) to use in output.
        """
        token = self._safe_token(name)
        body = rf"\mathsf{{{name}}}"
        self._entries[name] = (token, body)
        return "\\" + token

    @staticmethod
    def _safe_token(name: str) -> str:
        if name in _LATEX_BUILTINS:
            return "Frog" + name
        return name

    def preamble(self) -> str:
        lines = []
        for _, (tok, body) in sorted(self._entries.items()):
            lines.append(rf"\providecommand{{\{tok}}}{{{body}}}")
        return "\n".join(lines) + ("\n" if lines else "")
