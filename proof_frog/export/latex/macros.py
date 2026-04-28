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
        body = rf"\ensuremath{{{self._mathsf_body(name)}}}"
        self._entries[name] = (token, body)
        return "\\" + token

    def register_security_notion(self, name: str) -> str:
        """Register a security-notion name. Underscores render as hyphens.

        E.g. ``LEAK_BIND_K_CT_ROM`` renders ``\\mathsf{LEAK\\text{-}BIND\\text{-}K\\text{-}CT\\text{-}ROM}``
        rather than the algorithm-style first-underscore-as-subscript.
        """
        token = self._safe_token(name)
        body = rf"\ensuremath{{\mathsf{{{name.replace('_', r'\text{-}')}}}}}"
        self._entries[name] = (token, body)
        return "\\" + token

    @staticmethod
    def _mathsf_body(name: str) -> str:
        if "_" not in name:
            return rf"\mathsf{{{name}}}"
        head, _, tail = name.partition("_")
        return rf"\mathsf{{{head}}}_{{\mathsf{{{tail.replace('_', '\\_')}}}}}"

    @staticmethod
    def _safe_token(name: str) -> str:
        # LaTeX macro names may contain only letters. Strip non-letters
        # (e.g. ``G_RO`` -> ``GRO``); the displayed body still shows the
        # original name verbatim.
        token = "".join(ch for ch in name if ch.isalpha())
        if not token:
            token = "Frog"
        if token in _LATEX_BUILTINS:
            token = "Frog" + token
        return token

    def preamble(self) -> str:
        lines = []
        for _, (tok, body) in sorted(self._entries.items()):
            lines.append(rf"\providecommand{{\{tok}}}{{{body}}}")
        return "\n".join(lines) + ("\n" if lines else "")
