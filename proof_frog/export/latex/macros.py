"""Macro registry for LaTeX export.

Collects identifiers that should be rendered as macros (algorithm names,
scheme names, game names, security properties, adversaries) and emits a
preamble of ``\\providecommand`` lines so user redefinitions in their own
preamble win.
"""

from __future__ import annotations

# LaTeX builtins we must not redefine: ``\providecommand`` silently no-ops
# against an already-defined command, so a generated ``\S`` would keep
# rendering as the section sign rather than our ``\mathsf{S}``. Names listed
# here are renamed (``Frog``-prefixed) so the readable body still shows the
# original identifier. Extend as needed.
_LATEX_BUILTINS = {
    # Math operators (\mathop names defined by base LaTeX).
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
    # Single-letter / short text-mode commands defined by base LaTeX:
    # special letters \i \j \l \o \L \O \P \S \SS \AA, accent commands
    # \H \t \c \d \b \u \v \r \k (these take an argument), and the \aa..\th
    # ligatures. A crypto identifier named e.g. S (a set), H (a hash), P (a
    # party), or lowercase c/d/i/j would otherwise mis-render.
    "S",
    "P",
    "H",
    "L",
    "O",
    "i",
    "j",
    "l",
    "o",
    "t",
    "c",
    "d",
    "b",
    "u",
    "v",
    "r",
    "k",
    "a",
    "AA",
    "aa",
    "AE",
    "ae",
    "OE",
    "oe",
    "DH",
    "dh",
    "TH",
    "th",
    "SS",
    "ss",
    "NG",
    "ng",
    "DJ",
    "dj",
}

# Math-mode escapes for characters that are LaTeX-special inside a ``\mathsf``
# body. ``_`` is handled structurally by ``_mathsf_body`` /
# ``register_security_notion`` and so is escaped only where it is meant to be a
# literal (e.g. inside a subscript group).
_MATHSF_SPECIALS = {
    "$": r"\$",
    "#": r"\#",
    "%": r"\%",
    "&": r"\&",
    "{": r"\{",
    "}": r"\}",
}

# LaTeX macro names may contain only letters, so a token built by dropping
# non-letters collapses digit-suffixed siblings onto one command (``Decaps0``,
# ``Decaps1`` -> ``\Decaps``) and ``\providecommand`` keeps only the first body.
# Spell digits out so distinct names keep distinct tokens; the displayed body
# still shows the original digit.
_DIGIT_WORDS = {
    "0": "Zero",
    "1": "One",
    "2": "Two",
    "3": "Three",
    "4": "Four",
    "5": "Five",
    "6": "Six",
    "7": "Seven",
    "8": "Eight",
    "9": "Nine",
}


def _escape_mathsf(s: str) -> str:
    """Escape LaTeX specials (except ``_``) for display inside ``\\mathsf{}``."""
    return "".join(_MATHSF_SPECIALS.get(ch, ch) for ch in s)


class MacroRegistry:
    """Tracks identifiers that should render as LaTeX macros."""

    def __init__(self) -> None:
        # name -> (macro_token_without_backslash, body)
        self._entries: dict[str, tuple[str, str]] = {}
        # (group_name, kind) -> macro_token, for group generators/orders. Each
        # group gets its own macro so multiple groups stay distinct; the default
        # body is computed at preamble time (single group -> bare g/q).
        self._group_symbols: dict[tuple[str, str], str] = {}

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
        display = _escape_mathsf(name).replace("_", r"\text{-}")
        body = rf"\ensuremath{{\mathsf{{{display}}}}}"
        self._entries[name] = (token, body)
        return "\\" + token

    def register_group_symbol(self, group_name: str, kind: str) -> str:
        """Register a group's generator or order as a per-group macro.

        ``kind`` is ``"generator"`` or ``"order"``. Returns the LaTeX token
        (e.g. ``\\genG`` / ``\\ordG``). The default body is filled in at
        ``preamble()`` time: a single group renders as the conventional bare
        ``g`` / ``q``; with several groups each is disambiguated by a group
        subscript (``g_{\\mathsf{G}}``). Users override the ``\\providecommand``
        to pick their own symbols.
        """
        token = self._group_token(group_name, kind)
        self._group_symbols[(group_name, kind)] = token
        return "\\" + token

    @staticmethod
    def _group_token(group_name: str, kind: str) -> str:
        prefix = "gen" if kind == "generator" else "ord"
        letters = "".join(ch for ch in group_name if ch.isalpha()) or "Grp"
        return prefix + letters

    @staticmethod
    def _mathsf_body(name: str) -> str:
        if "_" not in name:
            return rf"\mathsf{{{_escape_mathsf(name)}}}"
        head, _, tail = name.partition("_")
        tail_body = _escape_mathsf(tail).replace("_", r"\_")
        return rf"\mathsf{{{_escape_mathsf(head)}}}_{{\mathsf{{{tail_body}}}}}"

    @staticmethod
    def _safe_token(name: str) -> str:
        # LaTeX macro names may contain only letters. Spell out digits (so
        # ``Decaps0``/``Decaps1`` stay distinct) and strip other non-letters
        # (e.g. ``G_RO`` -> ``GRO``); the displayed body still shows the
        # original name verbatim.
        token = "".join(
            _DIGIT_WORDS[ch] if ch.isdigit() else ch
            for ch in name
            if ch.isalpha() or ch.isdigit()
        )
        if not token:
            token = "Frog"
        if token in _LATEX_BUILTINS:
            token = "Frog" + token
        return token

    def preamble(self) -> str:
        lines = []
        lines.extend(self._group_symbol_lines())
        for _, (tok, body) in sorted(self._entries.items()):
            lines.append(rf"\providecommand{{\{tok}}}{{{body}}}")
        return "\n".join(lines) + ("\n" if lines else "")

    def _group_symbol_lines(self) -> list[str]:
        groups = {group for (group, _kind) in self._group_symbols}
        single = len(groups) == 1
        lines = []
        for (group, kind), token in sorted(self._group_symbols.items()):
            base = "g" if kind == "generator" else "q"
            body = base if single else rf"{base}_{{{self._mathsf_body(group)}}}"
            lines.append(rf"\providecommand{{\{token}}}{{\ensuremath{{{body}}}}}")
        return lines
