from __future__ import annotations
import os
import re
from typing import Type, Callable
from antlr4 import (
    FileStream,
    InputStream,
    CommonTokenStream,
    BailErrorStrategy,
    ParserRuleContext,
    error as antlr_error,
)
from antlr4.error.ErrorListener import ErrorListener
from .parsing.PrimitiveVisitor import PrimitiveVisitor
from .parsing.PrimitiveParser import PrimitiveParser
from .parsing.PrimitiveLexer import PrimitiveLexer
from .parsing.SchemeVisitor import SchemeVisitor
from .parsing.SchemeParser import SchemeParser
from .parsing.SchemeLexer import SchemeLexer
from .parsing.GameVisitor import GameVisitor
from .parsing.GameParser import GameParser
from .parsing.GameLexer import GameLexer
from .parsing.ProofVisitor import ProofVisitor
from .parsing.ProofParser import ProofParser
from .parsing.ProofLexer import ProofLexer
from . import frog_ast


class _SilentErrorListener(ErrorListener):  # type: ignore[misc]
    """Suppresses ANTLR's default stderr output; errors are reported via exceptions."""

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):  # type: ignore[override, no-untyped-def]  # pylint: disable=too-many-arguments,too-many-positional-arguments
        pass


class _CollectingErrorListener(ErrorListener):  # type: ignore[misc]
    """Records all syntax errors for better error reporting."""

    def __init__(self) -> None:
        self.errors: list[tuple[int, int, str, str]] = (
            []
        )  # (line, column, token_text, msg)

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):  # type: ignore[override, no-untyped-def]  # pylint: disable=too-many-arguments,too-many-positional-arguments
        token_text = offendingSymbol.text if offendingSymbol else ""
        self.errors.append((line, column, token_text, msg))


class ParseError(Exception):
    """A syntax error from the ANTLR parser with location info."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        message: str,
        file_name: str = "",
        line: int = -1,
        column: int = -1,
        token: str = "",
        source_line: str = "",
    ) -> None:
        super().__init__(message)
        self.file_name = file_name
        self.line = line
        self.column = column
        self.token = token
        self.source_line = source_line

    def __str__(self) -> str:
        loc = self.file_name if self.file_name else "<input>"
        if self.line >= 0:
            loc += f":{self.line}:{self.column}"
        header = f"{loc}: parse error: {self.args[0]}"
        if self.source_line:
            caret = " " * self.column + "^"
            return f"{header}\n{self.source_line}\n{caret}"
        return header


# Map ANTLR internal token names to user-friendly descriptions.
_ANTLR_TOKEN_MAP = {
    "ID": "identifier",
    "INT": "integer",
    "SEMI": "';'",
    "L_CURLY": "'{'",
    "R_CURLY": "'}'",
    "L_PAREN": "'('",
    "R_PAREN": "')'",
    "L_SQUARE": "'['",
    "R_SQUARE": "']'",
    "L_ANGLE": "'<'",
    "R_ANGLE": "'>'",
    "EQUALS": "'='",
    "SAMPLES": "'<-'",
    "SAMPUNIQ": "'<-uniq'",
    "COMMA": "','",
    "COLON": "':'",
    "PERIOD": "'.'",
    "FILESTRING": "file path",
}


def _clean_antlr_token_names(msg: str) -> str:
    """Replace ANTLR token names with user-friendly descriptions.

    Also strips the curly-brace set notation that ANTLR uses for expected
    token sets (e.g. ``{ID, SEMI}``), but preserves quoted literal braces
    like ``'}'``.
    """
    # Strip ANTLR set braces, but not quoted literal braces like '}'
    msg = re.sub(r"(?<!')\{(?!')", "", msg)
    msg = re.sub(r"(?<!')\}(?!')", "", msg)
    # Use word-boundary regex to avoid replacing ID inside VOID, etc.
    for token, friendly in _ANTLR_TOKEN_MAP.items():
        msg = re.sub(r"\b" + token + r"\b", friendly, msg)
    return msg


def _eof_hint(source_lines: list[str]) -> str:
    """Generate a hint for unexpected EOF errors by checking brace balance."""
    opens = sum(line.count("{") for line in source_lines)
    closes = sum(line.count("}") for line in source_lines)
    if opens > closes:
        open_word = "brace" if opens == 1 else "braces"
        close_word = "brace" if closes == 1 else "braces"
        return (
            f" (file has {opens} opening {open_word} "
            f"but only {closes} closing {close_word})"
        )
    return ""


def _read_source_lines(source: str) -> list[str]:
    """Read all lines from *source* (a file path or raw text)."""
    try:
        if os.path.isfile(source):
            with open(source, encoding="utf-8") as f:
                return f.readlines()
        return source.splitlines(keepends=True)
    except OSError:
        return []


# Known FrogLang keywords that users might misspell
_KNOWN_KEYWORDS = {
    "Game",
    "Primitive",
    "Scheme",
    "Reduction",
    "Set",
    "Bool",
    "Void",
    "Int",
    "Map",
    "BitString",
    "ModInt",
    "Array",
    "RandomFunctions",
    "return",
    "import",
    "export",
    "if",
    "else",
    "for",
    "true",
    "false",
    "None",
    "this",
    "Phase",
    "deterministic",
    "injective",
    "extends",
}

# Known FrogLang type names (case-sensitive) for detecting lowercase mistakes
_KNOWN_TYPE_NAMES = {
    "int": "Int",
    "bool": "Bool",
    "void": "Void",
    "set": "Set",
    "map": "Map",
    "array": "Array",
    "bitstring": "BitString",
    "modint": "ModInt",
    "string": "BitString",
}


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)  # pylint: disable=arguments-out-of-order
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(
                min(prev_row[j + 1] + 1, curr_row[j] + 1, prev_row[j] + cost)
            )
        prev_row = curr_row
    return prev_row[-1]


def _suggest_keyword(token: str) -> str | None:
    """If *token* is close to a known keyword, return a suggestion."""
    if not token or token.startswith(("'", '"')):
        return None
    # Require the token to be at least 3 characters to avoid spurious
    # matches for short identifiers like "mL" matching "if"
    if len(token) < 3:
        return None
    best, best_dist = None, 3  # max edit distance of 2
    for kw in _KNOWN_KEYWORDS:
        if kw == token:
            continue  # don't suggest the exact same word
        # Only suggest keywords of similar length
        if abs(len(kw) - len(token)) > 2:
            continue
        dist = _levenshtein_distance(token, kw)
        if dist < best_dist:
            best, best_dist = kw, dist
    return best


def _missing_semi_message(next_token: str) -> str:
    """Build a 'missing semicolon' message, tailored to the next token."""
    if next_token in ("}", "]", ")"):
        return f"missing ';' before '{next_token}'"
    return f"missing ';' (found '{next_token}' on next line)"


def _truncate_expecting(msg: str) -> str:
    """Shorten long 'expecting X, Y, Z, ...' lists to at most 5 items."""
    m = re.search(r"expecting (.*)", msg)
    if not m:
        return msg
    items_str = m.group(1)
    items = [s.strip() for s in items_str.split(",")]
    if len(items) <= 5:
        return msg
    kept = ", ".join(items[:5])
    return msg[: m.start(1)] + kept + ", ..."


def _enhance_error_message(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    display_msg: str,
    token_text: str,
    line: int,
    col: int,
    all_lines: list[str],
    source: str,
) -> tuple[str, int, int, str]:
    """Apply heuristics to improve a parse error message.

    Returns (improved_message, line, col, source_line) — the line/col/source_line
    may be adjusted if the heuristic points to a different location.
    """
    source_line = ""
    if 1 <= line <= len(all_lines):
        source_line = all_lines[line - 1].rstrip()

    # --- Heuristic: '}' where ';' expected (missing semicolon on same line) ---
    if token_text == "}" and 1 <= line <= len(all_lines):
        line_text = all_lines[line - 1]
        before = line_text[:col].rstrip()
        if before and not before.endswith((";", "{", "}")):
            return (
                f"missing ';' before '{token_text}'",
                line,
                col,
                source_line,
            )

    # --- Heuristic: double-quoted import string ---
    if 1 <= line <= len(all_lines):
        stripped = all_lines[line - 1].strip()
        if stripped.startswith("import ") and '"' in stripped:
            quote_col = all_lines[line - 1].index('"')
            return (
                "import paths must use single quotes, not double quotes "
                "(e.g. import '../path/to/file';)",
                line,
                quote_col,
                source_line,
            )

    # --- Heuristic: lowercase type name ---
    if token_text in _KNOWN_TYPE_NAMES:
        correct = _KNOWN_TYPE_NAMES[token_text]
        return (
            f"unknown identifier '{token_text}'; did you mean '{correct}'? "
            f"(type names are capitalized in FrogLang)",
            line,
            col,
            source_line,
        )

    # --- Heuristic: 'export' where 'Game' expected (missing second game) ---
    file_ext = os.path.splitext(source)[1] if os.path.isfile(source) else ""
    if (
        token_text == "export"
        and "expecting 'Game'" in display_msg
        and file_ext == ".game"
    ):
        # Count how many 'Game' definitions are in the file
        game_count = sum(
            1
            for ln in all_lines
            if re.match(r"\s*Game\s+", ln.rstrip() if isinstance(ln, str) else ln)
        )
        if game_count < 2:
            return (
                "a .game security property file must contain exactly two Game "
                "definitions (e.g. Left and Right), but only one was found",
                line,
                col,
                source_line,
            )
        # If there are 2+ Game keywords but the parser still chokes,
        # one of them likely has a syntax error
        return (
            "expected another Game definition before 'export'; "
            "check for syntax errors in the Game definitions above",
            line,
            col,
            source_line,
        )

    # --- Heuristic: missing brace (export with expecting '}') ---
    if token_text == "export" and "expecting '}'" in display_msg:
        return (
            "unexpected 'export'; a closing '}' is missing for a Game "
            "or method definition above" + _eof_hint(all_lines),
            line,
            col,
            source_line,
        )

    # --- Heuristic: missing closing '>' in type like BitString<32 ---
    if 1 <= line <= len(all_lines):
        line_text = all_lines[line - 1]
        before_token = line_text[:col]
        # Check if there's an unmatched '<' before the token on the same line
        if "<" in before_token:
            open_angles = before_token.count("<")
            close_angles = before_token.count(">")
            if open_angles > close_angles:
                # Find the position of the last unmatched '<'
                for type_prefix in ("BitString", "ModInt", "Array", "Map", "Set"):
                    if type_prefix in before_token:
                        return (
                            f"unexpected token '{token_text}'; "
                            f"did you forget a closing '>' for {type_prefix}<...>?",
                            line,
                            col,
                            source_line,
                        )
                return (
                    f"unexpected token '{token_text}'; "
                    f"did you forget a closing '>'?",
                    line,
                    col,
                    source_line,
                )

    # --- Heuristic: '=>' used instead of '=' or '<-' ---
    if token_text == ">" and 1 <= line <= len(all_lines):
        line_text = all_lines[line - 1]
        if col >= 1 and line_text[col - 1 : col] == "=":
            return (
                "unexpected '=>'; use '=' for assignment or '<-' for sampling",
                line,
                col - 1,
                source_line,
            )

    # --- Heuristic: '==' used instead of '=' for assignment ---
    if token_text == "==" and 1 <= line <= len(all_lines):
        line_text = all_lines[line - 1]
        # Check if this looks like a variable declaration (Type name == expr)
        before = line_text[:col].strip()
        # If there's a type and identifier before ==, it's likely an assignment
        if re.search(r"\w+\s+\w+\s*$", before):
            return (
                "use '=' for assignment, not '==' (which is the equality operator)",
                line,
                col,
                source_line,
            )

    # --- Heuristic: '=' used inside if-condition (assignment vs comparison) ---
    if token_text == "=" and 1 <= line <= len(all_lines):
        line_text = all_lines[line - 1]
        if "if" in line_text[:col] and "(" in line_text[:col]:
            return (
                "unexpected '=' in condition; use '==' for comparison, not '='",
                line,
                col,
                source_line,
            )

    # --- Heuristic: missing comma in parameter list ---
    if (
        token_text
        and token_text not in ("<EOF>", ";", "}", ")")
        and 1 <= line <= len(all_lines)
    ):
        line_text = all_lines[line - 1]
        # If we're inside parentheses and the previous non-space char is
        # an identifier char, likely a missing comma
        before = line_text[:col]
        if "(" in before and ")" not in before:
            before_stripped = before.rstrip()
            if before_stripped and re.match(r"[a-zA-Z0-9_]", before_stripped[-1]):
                # Check that the unexpected token could be a type or identifier
                if re.match(r"[A-Z]", token_text):
                    return (
                        f"unexpected '{token_text}'; "
                        f"did you forget a ',' between parameters?",
                        line,
                        col,
                        source_line,
                    )

    # --- Heuristic: misspelled keyword (on the offending token itself) ---
    if token_text and re.match(r"[a-zA-Z_]", token_text):
        suggestion = _suggest_keyword(token_text)
        if suggestion:
            return (
                f"unexpected '{token_text}'; did you mean '{suggestion}'?",
                line,
                col,
                source_line,
            )

    # --- Heuristic: misspelled keyword earlier on the line ---
    # If the unexpected token is inside a construct that started with a
    # misspelled keyword (e.g. "fore (Int i = ..." where "fore" should
    # be "for"), point to the misspelled word instead.  Only check the
    # first word on the line (the statement keyword position) to avoid
    # false positives on identifiers like "bar" matching "for".
    if 1 <= line <= len(all_lines):
        line_text = all_lines[line - 1]
        first_word_match = re.match(r"\s*([a-zA-Z_]\w*)", line_text)
        if first_word_match and first_word_match.end() <= col:
            word = first_word_match.group(1)
            suggestion = _suggest_keyword(word)
            if suggestion:
                return (
                    f"'{word}' is not a keyword; did you mean '{suggestion}'?",
                    line,
                    first_word_match.start(1),
                    source_line,
                )

    # --- Heuristic: 'if' without opening brace ---
    # Check if the previous non-blank line is an if/for/else without a brace
    if token_text and token_text not in ("<EOF>",) and 1 <= line <= len(all_lines):
        prev_idx = line - 2  # 0-indexed
        while prev_idx >= 0 and not all_lines[prev_idx].strip():
            prev_idx -= 1
        if prev_idx >= 0:
            prev_stripped = all_lines[prev_idx].rstrip()
            if re.match(r"\s*if\s*\(.*\)\s*$", prev_stripped):
                return (
                    "the body of an 'if' statement must be enclosed in braces { }",
                    prev_idx + 1,
                    len(prev_stripped),
                    prev_stripped,
                )
            if re.match(r"\s*for\s*\(.*\)\s*$", prev_stripped):
                return (
                    "the body of a 'for' loop must be enclosed in braces { }",
                    prev_idx + 1,
                    len(prev_stripped),
                    prev_stripped,
                )
            if re.match(r"\s*else\s*$", prev_stripped):
                return (
                    "the body of an 'else' clause must be enclosed in braces { }",
                    prev_idx + 1,
                    len(prev_stripped),
                    prev_stripped,
                )

    # --- Heuristic: empty game body ---
    if token_text == "}" and "expecting" in display_msg:
        if 1 <= line <= len(all_lines):
            # Look backwards for a Game definition
            for i in range(line - 2, -1, -1):
                if re.match(r"\s*Game\s+", all_lines[i]):
                    return (
                        "Game body cannot be empty; "
                        "it must contain at least one method",
                        line,
                        col,
                        source_line,
                    )
                # Don't look too far back
                if i < line - 10:
                    break

    # --- Heuristic: EOF expecting 'Game' in .game file ---
    if token_text == "<EOF>" and "expecting 'Game'" in display_msg:
        if file_ext == ".game":
            game_count = sum(
                1
                for ln in all_lines
                if re.match(r"\s*Game\s+", ln.rstrip() if isinstance(ln, str) else ln)
            )
            if game_count < 2:
                return (
                    "a .game security property file must contain exactly two "
                    "Game definitions (e.g. Left and Right) followed by an "
                    "'export as <Name>;' statement",
                    line,
                    col,
                    source_line,
                )
            # Check if export is missing
            has_export = any(re.match(r"\s*export\s+", ln) for ln in all_lines)
            if not has_export:
                return (
                    "missing 'export as <Name>;' at end of file",
                    line,
                    col,
                    source_line,
                )

    # --- Heuristic: ';' inside parenthesized expression (missing ')') ---
    if token_text == ";" and 1 <= line <= len(all_lines):
        line_text = all_lines[line - 1]
        before = line_text[:col]
        open_parens = before.count("(") - before.count(")")
        if open_parens > 0:
            return (
                "unexpected ';'; did you forget a closing ')'?",
                line,
                col,
                source_line,
            )

    # --- Heuristic: ')' after comma (trailing comma) ---
    if token_text == ")" and 1 <= line <= len(all_lines):
        line_text = all_lines[line - 1]
        before = line_text[:col].rstrip()
        if before.endswith(","):
            return (
                "unexpected ')' after ','; trailing commas are not allowed "
                "in parameter and argument lists",
                line,
                col,
                source_line,
            )

    # Truncate long expecting lists
    display_msg = _truncate_expecting(display_msg)

    return display_msg, line, col, source_line


def _to_parse_error(
    e: antlr_error.Errors.ParseCancellationException, source: str
) -> ParseError:
    """Extract location info from a BailErrorStrategy exception."""
    file_name = source if os.path.isfile(source) else "<input>"
    line, col, token_text = -1, -1, ""
    inner = e.args[0] if e.args else None
    if inner is not None and hasattr(inner, "offendingToken") and inner.offendingToken:
        tok = inner.offendingToken
        line, col, token_text = tok.line, tok.column, tok.text or ""

    all_lines = _read_source_lines(source)

    if token_text == "<EOF>":
        msg = "unexpected end of file" + _eof_hint(all_lines)
    elif token_text:
        msg = f"unexpected token '{token_text}'"
    else:
        msg = "syntax error"

    # Heuristic: if the offending token starts a new line and the previous
    # non-blank line doesn't end with a semicolon, brace, or colon, the
    # real problem is likely a missing ';' on that previous line.
    if line >= 2 and token_text and token_text != "<EOF>":
        prev_idx = line - 2  # 0-indexed previous line
        while prev_idx >= 0 and not all_lines[prev_idx].strip():
            prev_idx -= 1
        if prev_idx >= 0:
            prev_stripped = all_lines[prev_idx].rstrip()
            if prev_stripped and not prev_stripped.endswith((";", "{", "}", ":")):
                # Don't report missing ';' if the previous line is an
                # if/for/else that requires a block, not a semicolon.
                if not re.match(
                    r"\s*(if\s*\(.*\)|for\s*\(.*\)|else)\s*$", prev_stripped
                ):
                    prev_line_num = prev_idx + 1  # back to 1-indexed
                    prev_col = len(prev_stripped)
                    return ParseError(
                        _missing_semi_message(token_text),
                        file_name=file_name,
                        line=prev_line_num,
                        column=prev_col,
                        token=token_text,
                        source_line=prev_stripped,
                    )

    # Apply enhancement heuristics
    msg, line, col, source_line = _enhance_error_message(
        msg, token_text, line, col, all_lines, source
    )

    return ParseError(
        msg,
        file_name=file_name,
        line=line,
        column=col,
        token=token_text,
        source_line=source_line,
    )


def _reparse_for_error(
    source: str,
    lexer_functor: type[PrimitiveLexer],
    parser_functor: type[PrimitiveParser],
) -> ParseError | None:
    """Re-parse with DefaultErrorStrategy to get a better error location.

    BailErrorStrategy (used for normal parsing) can report errors far from the
    actual problem.  DefaultErrorStrategy does proper recovery and reports at
    the real mismatch point.  Returns None if the reparse finds no errors.
    """
    input_stream: InputStream | FileStream
    if os.path.isfile(source):
        input_stream = FileStream
    else:
        input_stream = InputStream
    lexer = lexer_functor(input_stream(source))
    lexer.removeErrorListeners()
    collector = _CollectingErrorListener()
    parser = parser_functor(CommonTokenStream(lexer))
    parser.removeErrorListeners()
    parser.addErrorListener(collector)
    try:
        parser.program()
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    if not collector.errors:
        return None

    # Heuristic for choosing the most useful error among potentially many:
    # When there are few errors (1-3), the first non-EOF error is usually
    # the root cause.  When there are many errors (4+), earlier ones are
    # often cascading noise from recovery attempts, so prefer the last
    # non-EOF error which tends to be closest to the real problem.
    chosen = collector.errors[0]
    if len(collector.errors) >= 4:
        for err in reversed(collector.errors):
            if err[2] != "<EOF>":
                chosen = err
                break
    else:
        for err in collector.errors:
            if err[2] != "<EOF>":
                chosen = err
                break

    line, col, token_text, antlr_msg = chosen
    file_name = source if os.path.isfile(source) else "<input>"
    all_lines = _read_source_lines(source)

    if token_text == "<EOF>":
        display_msg = "unexpected end of file" + _eof_hint(all_lines)
    elif token_text:
        display_msg = f"unexpected token '{token_text}'"
    else:
        display_msg = "syntax error"

    # Use ANTLR's message when it contains useful context ("expecting"
    # or "missing"), but clean up internal token names for readability.
    if antlr_msg and ("expecting" in antlr_msg or "missing" in antlr_msg):
        cleaned = antlr_msg
        cleaned = cleaned.replace("'in', ", "")
        cleaned = cleaned.replace("extraneous input", "unexpected")
        cleaned = _clean_antlr_token_names(cleaned)
        display_msg = cleaned

    # Apply the same missing-semicolon heuristic as _to_parse_error.
    if line >= 2 and token_text and token_text != "<EOF>":
        prev_idx = line - 2
        while prev_idx >= 0 and not all_lines[prev_idx].strip():
            prev_idx -= 1
        if prev_idx >= 0:
            prev_stripped = all_lines[prev_idx].rstrip()
            if prev_stripped and not prev_stripped.endswith((";", "{", "}", ":")):
                if not re.match(
                    r"\s*(if\s*\(.*\)|for\s*\(.*\)|else)\s*$", prev_stripped
                ):
                    return ParseError(
                        _missing_semi_message(token_text),
                        file_name=file_name,
                        line=prev_idx + 1,
                        column=len(prev_stripped),
                        token=token_text,
                        source_line=prev_stripped,
                    )

    # Apply enhancement heuristics
    display_msg, line, col, source_line = _enhance_error_message(
        display_msg, token_text, line, col, all_lines, source
    )

    return ParseError(
        display_msg,
        file_name=file_name,
        line=line,
        column=col,
        token=token_text,
        source_line=source_line,
    )


def _binary_operation(
    operator: frog_ast.BinaryOperators,
    visit: Type[PrimitiveVisitor.visit],
    ctx: Type[PrimitiveParser.ExpressionContext],
) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(
        operator, visit(ctx.expression()[0]), visit(ctx.expression()[1])
    )


def add_line_number(
    func: Callable[[_SharedAST, ParserRuleContext], frog_ast.ASTNode],
) -> Callable[[_SharedAST, ParserRuleContext], frog_ast.ASTNode]:
    def wrapper(self: _SharedAST, ctx: ParserRuleContext) -> frog_ast.ASTNode:
        result = func(self, ctx)
        if isinstance(result, frog_ast.ASTNode):
            result.line_num = ctx.start.line
            result.column_num = ctx.start.column
        return result

    return wrapper


def line_number_decorator(the_class):  # type: ignore
    class ModifiedClass(the_class):  # type: ignore
        pass

    for name, attr in vars(the_class).items():
        if callable(attr):
            setattr(ModifiedClass, name, add_line_number(attr))
    return ModifiedClass


@line_number_decorator
# pylint: disable-next=too-many-public-methods
class _SharedAST(PrimitiveVisitor, SchemeVisitor, GameVisitor, ProofVisitor):  # type: ignore[misc]
    def visitParamList(
        self, ctx: PrimitiveParser.ParamListContext
    ) -> list[frog_ast.Parameter]:
        result = []
        for variable in ctx.variable():
            result.append(
                frog_ast.Parameter(
                    super().visit(variable.type_()), variable.id_().getText()
                )
            )
        return result

    def visitOptionalType(
        self, ctx: PrimitiveParser.OptionalTypeContext
    ) -> frog_ast.Type:
        return frog_ast.OptionalType(self.visit(ctx.type_()))

    def visitBoolType(self, __: PrimitiveParser.BoolTypeContext) -> frog_ast.Type:
        return frog_ast.BoolType()

    def visitVoidType(self, __: PrimitiveParser.VoidTypeContext) -> frog_ast.Void:
        return frog_ast.Void()

    def visitBitStringType(
        self, ctx: PrimitiveParser.BitStringTypeContext
    ) -> frog_ast.BitStringType:
        if not ctx.bitstring().integerExpression():
            return frog_ast.BitStringType()
        return frog_ast.BitStringType(self.visit(ctx.bitstring().integerExpression()))

    def visitModIntType(
        self, ctx: PrimitiveParser.ModIntTypeContext
    ) -> frog_ast.ModIntType:
        return frog_ast.ModIntType(self.visit(ctx.modint().integerExpression()))

    def visitProductType(
        self, ctx: PrimitiveParser.ProductTypeContext
    ) -> frog_ast.ProductType:
        return frog_ast.ProductType([self.visit(t) for t in ctx.type_()])

    def visitSetType(self, ctx: PrimitiveParser.SetTypeContext) -> frog_ast.SetType:
        return frog_ast.SetType(
            self.visit(ctx.set_().type_()) if ctx.set_().type_() else None
        )

    def visitField(self, ctx: PrimitiveParser.FieldContext) -> frog_ast.Field:
        return frog_ast.Field(
            self.visit(ctx.variable().type_()),
            ctx.variable().id_().getText(),
            self.visit(ctx.expression()) if ctx.expression() else None,
        )

    def visitInitializedField(
        self, ctx: PrimitiveParser.InitializedFieldContext
    ) -> frog_ast.Field:
        return frog_ast.Field(
            self.visit(ctx.variable().type_()),
            ctx.variable().id_().getText(),
            self.visit(ctx.expression()),
        )

    def visitEqualsExp(
        self, ctx: PrimitiveParser.EqualsExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.EQUALS, self.visit, ctx)

    def visitNotEqualsExp(
        self, ctx: PrimitiveParser.NotEqualsExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.NOTEQUALS, self.visit, ctx)

    def visitGtExp(self, ctx: PrimitiveParser.GtExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.GT, self.visit, ctx)

    def visitLtExp(self, ctx: PrimitiveParser.LtExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.LT, self.visit, ctx)

    def visitGeqExp(
        self, ctx: PrimitiveParser.GeqExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.GEQ, self.visit, ctx)

    def visitLeqExp(
        self, ctx: PrimitiveParser.LeqExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.LEQ, self.visit, ctx)

    def visitAndExp(
        self, ctx: PrimitiveParser.AndExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.AND, self.visit, ctx)

    def visitSubsetsExp(
        self, ctx: PrimitiveParser.SubsetsExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.SUBSETS, self.visit, ctx)

    def visitInExp(self, ctx: PrimitiveParser.InExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.IN, self.visit, ctx)

    def visitOrExp(self, ctx: PrimitiveParser.OrExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.OR, self.visit, ctx)

    def visitUnionExp(
        self, ctx: PrimitiveParser.UnionExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.UNION, self.visit, ctx)

    def visitSetMinusExp(
        self, ctx: PrimitiveParser.SetMinusExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.SETMINUS, self.visit, ctx)

    def visitAddExp(
        self, ctx: PrimitiveParser.AddExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.ADD, self.visit, ctx)

    def visitSubtractExp(
        self, ctx: PrimitiveParser.SubtractExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.SUBTRACT, self.visit, ctx)

    def visitMultiplyExp(
        self, ctx: PrimitiveParser.MultiplyExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.MULTIPLY, self.visit, ctx)

    def visitDivideExp(
        self, ctx: PrimitiveParser.DivideExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.DIVIDE, self.visit, ctx)

    def visitExponentiationExp(
        self, ctx: PrimitiveParser.ExponentiationExpContext
    ) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.EXPONENTIATE, self.visit, ctx)

    def visitCreateSetExp(
        self, ctx: PrimitiveParser.CreateSetExpContext
    ) -> frog_ast.Set:
        return frog_ast.Set(
            [self.visit(element) for element in ctx.expression()]
            if ctx.expression()
            else []
        )

    def visitMethod(self, ctx: PrimitiveParser.MethodContext) -> frog_ast.Method:
        return frog_ast.Method(
            self.visit(ctx.methodSignature()), self.visit(ctx.block())
        )

    def visitIntegerExpression(
        self, ctx: PrimitiveParser.IntegerExpressionContext
    ) -> frog_ast.Expression:
        if ctx.L_PAREN():
            exp: frog_ast.Expression = self.visit(ctx.getChild(1))
            return exp
        if ctx.INT():
            return frog_ast.Integer(int(ctx.INT().getText()))
        if ctx.BINARYNUM():
            return frog_ast.BinaryNum(int(ctx.BINARYNUM().getText(), 2))

        if ctx.lvalue():
            exp = self.visit(ctx.lvalue())
            return exp

        operator: frog_ast.BinaryOperators
        if ctx.PLUS():
            operator = frog_ast.BinaryOperators.ADD
        elif ctx.SUBTRACT():
            operator = frog_ast.BinaryOperators.SUBTRACT
        elif ctx.TIMES():
            operator = frog_ast.BinaryOperators.MULTIPLY
        elif ctx.DIVIDE():
            operator = frog_ast.BinaryOperators.DIVIDE

        return frog_ast.BinaryOperation(
            operator,
            self.visit(ctx.integerExpression()[0]),
            self.visit(ctx.integerExpression()[1]),
        )

    def visitVarDeclWithValueStatement(
        self, ctx: PrimitiveParser.VarDeclWithValueStatementContext
    ) -> frog_ast.Assignment:
        return frog_ast.Assignment(
            self.visit(ctx.type_()),
            self.visit(ctx.lvalue()),
            self.visit(ctx.expression()),
        )

    def visitAssignmentStatement(
        self, ctx: PrimitiveParser.AssignmentStatementContext
    ) -> frog_ast.Assignment:
        return frog_ast.Assignment(
            None, self.visit(ctx.lvalue()), self.visit(ctx.expression())
        )

    def visitSampleStatement(
        self, ctx: PrimitiveParser.SampleStatementContext
    ) -> frog_ast.Sample:
        return frog_ast.Sample(
            None, self.visit(ctx.lvalue()), self.visit(ctx.expression())
        )

    def visitBlock(self, ctx: PrimitiveParser.BlockContext) -> frog_ast.Block:
        return frog_ast.Block([self.visit(statement) for statement in ctx.statement()])

    def visitNumericForStatement(
        self, ctx: PrimitiveParser.NumericForStatementContext
    ) -> frog_ast.NumericFor:
        return frog_ast.NumericFor(
            ctx.id_().getText(),
            self.visit(ctx.expression()[0]),
            self.visit(ctx.expression()[1]),
            self.visit(ctx.block()),
        )

    def visitGenericForStatement(
        self, ctx: PrimitiveParser.GenericForStatementContext
    ) -> frog_ast.GenericFor:
        return frog_ast.GenericFor(
            self.visit(ctx.type_()),
            ctx.id_().getText(),
            self.visit(ctx.expression()),
            self.visit(ctx.block()),
        )

    def visitIntExp(self, ctx: PrimitiveParser.IntExpContext) -> frog_ast.Integer:
        return frog_ast.Integer(int(ctx.INT().getText()))

    def visitBoolExp(self, ctx: PrimitiveParser.BoolExpContext) -> frog_ast.Boolean:
        return frog_ast.Boolean(ctx.bool_().getText() == "true")

    def visitBinaryNumExp(
        self, ctx: PrimitiveParser.BinaryNumExpContext
    ) -> frog_ast.BinaryNum:
        return frog_ast.BinaryNum(int(ctx.BINARYNUM().getText(), 2))

    def visitZerosExp(
        self, ctx: PrimitiveParser.ZerosExpContext
    ) -> frog_ast.BitStringLiteral:
        return frog_ast.BitStringLiteral(0, self.visit(ctx.integerAtom()))

    def visitOnesExp(
        self, ctx: PrimitiveParser.OnesExpContext
    ) -> frog_ast.BitStringLiteral:
        return frog_ast.BitStringLiteral(1, self.visit(ctx.integerAtom()))

    def visitIntegerAtom(
        self, ctx: PrimitiveParser.IntegerAtomContext
    ) -> frog_ast.Expression:
        if ctx.INT():
            return frog_ast.Integer(int(ctx.INT().getText()))
        if ctx.lvalue():
            exp: frog_ast.Expression = self.visit(ctx.lvalue())
            return exp
        # Parenthesized: L_PAREN integerExpression R_PAREN
        exp = self.visit(ctx.integerExpression())
        return exp

    def visitVarDeclWithSampleStatement(
        self, ctx: PrimitiveParser.VarDeclWithSampleStatementContext
    ) -> frog_ast.Sample:
        return frog_ast.Sample(
            self.visit(ctx.type_()),
            self.visit(ctx.lvalue()),
            self.visit(ctx.expression()),
        )

    def visitUniqueSampleStatement(
        self, ctx: PrimitiveParser.UniqueSampleStatementContext
    ) -> frog_ast.UniqueSample:
        return frog_ast.UniqueSample(
            self.visit(ctx.type_()[0]),
            self.visit(ctx.lvalue()[0]),
            self.visit(ctx.lvalue()[1]),
            self.visit(ctx.type_()[1]),
        )

    def visitVarDeclStatement(
        self, ctx: PrimitiveParser.VarDeclStatementContext
    ) -> frog_ast.VariableDeclaration:
        return frog_ast.VariableDeclaration(
            self.visit(ctx.type_()), ctx.id_().getText()
        )

    def visitArrayType(
        self, ctx: PrimitiveParser.ArrayTypeContext
    ) -> frog_ast.ArrayType:
        return frog_ast.ArrayType(
            self.visit(ctx.type_()), self.visit(ctx.integerExpression())
        )

    def visitMapType(self, ctx: PrimitiveParser.MapTypeContext) -> frog_ast.MapType:
        return frog_ast.MapType(self.visit(ctx.type_()[0]), self.visit(ctx.type_()[1]))

    def visitRandomFunctionType(
        self, ctx: PrimitiveParser.RandomFunctionTypeContext
    ) -> frog_ast.RandomFunctionType:
        return frog_ast.RandomFunctionType(
            self.visit(ctx.type_()[0]), self.visit(ctx.type_()[1])
        )

    def visitNotExp(
        self, ctx: PrimitiveParser.NotExpContext
    ) -> frog_ast.UnaryOperation:
        return frog_ast.UnaryOperation(
            frog_ast.UnaryOperators.NOT, self.visit(ctx.expression())
        )

    def visitMinusExp(
        self, ctx: PrimitiveParser.MinusExpContext
    ) -> frog_ast.UnaryOperation:
        return frog_ast.UnaryOperation(
            frog_ast.UnaryOperators.MINUS, self.visit(ctx.expression())
        )

    def visitIntType(self, ctx: PrimitiveParser.IntTypeContext) -> frog_ast.IntType:
        return frog_ast.IntType()

    def visitSizeExp(
        self, ctx: PrimitiveParser.SizeExpContext
    ) -> frog_ast.UnaryOperation:
        return frog_ast.UnaryOperation(
            frog_ast.UnaryOperators.SIZE, self.visit(ctx.expression())
        )

    def visitNoneExp(
        self, __: PrimitiveParser.NoneExpContext
    ) -> frog_ast.NoneExpression:
        return frog_ast.NoneExpression()

    def visitParenExp(
        self, ctx: PrimitiveParser.ParenExpContext
    ) -> frog_ast.Expression:
        exp: frog_ast.Expression = self.visit(ctx.expression())
        return exp

    def visitLvalue(self, ctx: PrimitiveParser.LvalueExpContext) -> frog_ast.Expression:
        expression: frog_ast.Expression
        i = 1
        if ctx.parameterizedGame():
            expression = self.visit(ctx.parameterizedGame())
            assert isinstance(expression, frog_ast.ParameterizedGame)
            if ctx.getChildCount() > 3:
                expression = frog_ast.ConcreteGame(
                    expression, ctx.getChild(2).getText()
                )
                i = 3
        elif ctx.THIS():
            expression = frog_ast.Variable("this")
        else:
            expression = frog_ast.Variable(ctx.id_()[0].getText())

        while i < ctx.getChildCount():
            if ctx.getChild(i).getText() == ".":
                expression = frog_ast.FieldAccess(
                    expression, ctx.getChild(i + 1).getText()
                )
                i += 2
            else:
                index_expression: frog_ast.Expression = self.visit(ctx.getChild(i + 1))
                expression = frog_ast.ArrayAccess(expression, index_expression)
                i += 3

        return expression

    def visitCreateTupleExp(
        self, ctx: PrimitiveParser.CreateTupleExpContext
    ) -> frog_ast.Tuple:
        return frog_ast.Tuple([self.visit(exp) for exp in ctx.expression()])

    def visitReturnStatement(
        self, ctx: PrimitiveParser.ReturnStatementContext
    ) -> frog_ast.ReturnStatement:
        return frog_ast.ReturnStatement(self.visit(ctx.expression()))

    def visitFunctionCallStatement(
        self, ctx: PrimitiveParser.FunctionCallStatementContext
    ) -> frog_ast.FuncCall:
        return frog_ast.FuncCall(
            self.visit(ctx.expression()),
            self.visit(ctx.argList()) if ctx.argList() else [],
        )

    def visitFnCallExp(
        self, ctx: PrimitiveParser.FnCallExpContext
    ) -> frog_ast.FuncCall:
        return frog_ast.FuncCall(
            self.visit(ctx.expression()),
            self.visit(ctx.argList()) if ctx.argList() else [],
        )

    def visitSliceExp(self, ctx: PrimitiveParser.SliceExpContext) -> frog_ast.Slice:
        return frog_ast.Slice(
            self.visit(ctx.expression()),
            self.visit(ctx.integerExpression()[0]),
            self.visit(ctx.integerExpression()[1]),
        )

    def visitArgList(
        self, ctx: PrimitiveParser.ArgListContext
    ) -> list[frog_ast.Expression]:
        return [self.visit(exp) for exp in ctx.expression()]

    def visitLvalueExp(
        self, ctx: PrimitiveParser.LvalueExpContext
    ) -> frog_ast.Expression:
        exp: frog_ast.Expression = self.visit(ctx.lvalue())
        return exp

    def visitMethodSignature(
        self, ctx: PrimitiveParser.MethodSignatureContext
    ) -> frog_ast.MethodSignature:
        modifiers = {m.getText() for m in ctx.methodModifier()}
        return frog_ast.MethodSignature(
            ctx.id_().getText(),
            self.visit(ctx.type_()),
            [] if not ctx.paramList() else self.visit(ctx.paramList()),
            deterministic="deterministic" in modifiers,
            injective="injective" in modifiers,
        )

    def visitModuleImport(
        self, ctx: PrimitiveParser.ModuleImportContext
    ) -> frog_ast.Import:
        return frog_ast.Import(
            ctx.FILESTRING().getText().strip("'"),
            ctx.ID().getText() if ctx.ID() else "",
        )

    def visitIfStatement(
        self, ctx: PrimitiveParser.IfStatementContext
    ) -> frog_ast.IfStatement:
        return frog_ast.IfStatement(
            [self.visit(exp) for exp in ctx.expression()],
            [self.visit(block) for block in ctx.block()],
        )

    def visitGamePhase(self, ctx: PrimitiveParser.GamePhaseContext) -> frog_ast.Phase:
        oracles = [oracle.getText() for oracle in ctx.id_()]
        method_list = []
        for method in ctx.method():
            method_list.append(self.visit(method))
        return frog_ast.Phase(oracles, method_list)

    def visitGame(self, ctx: PrimitiveParser.GameContext) -> frog_ast.Game:
        return frog_ast.Game(_parse_game_body(self.visit, ctx))


@line_number_decorator
class _PrimitiveASTGenerator(_SharedAST, PrimitiveVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: PrimitiveParser.ProgramContext) -> frog_ast.Primitive:
        name = ctx.ID().getText()
        param_list = [] if not ctx.paramList() else self.visit(ctx.paramList())
        field_list = []
        if ctx.primitiveBody().initializedField():
            for field in ctx.primitiveBody().initializedField():
                field_list.append(self.visit(field))

        method_list = []
        if ctx.primitiveBody().methodSignature():
            for method_signature in ctx.primitiveBody().methodSignature():
                method_list.append(self.visit(method_signature))

        return frog_ast.Primitive(name, param_list, field_list, method_list)


@line_number_decorator
class _SchemeASTGenerator(_SharedAST, SchemeVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: SchemeParser.ProgramContext) -> frog_ast.Scheme:
        scheme_ctx = ctx.scheme()

        imports = [self.visit(im) for im in ctx.moduleImport()]

        name = scheme_ctx.ID()[0].getText()
        param_list = (
            [] if not scheme_ctx.paramList() else self.visit(scheme_ctx.paramList())
        )
        primitive_name = scheme_ctx.ID()[1].getText()
        field_list = []
        requirement_list = []
        method_list = []

        if scheme_ctx.schemeBody().field():
            for field in scheme_ctx.schemeBody().field():
                field_list.append(self.visit(field))
        if scheme_ctx.schemeBody().REQUIRES():
            for requirement in scheme_ctx.schemeBody().expression():
                requirement_list.append(self.visit(requirement))
        for method in scheme_ctx.schemeBody().method():
            method_list.append(self.visit(method))

        return frog_ast.Scheme(
            imports,
            name,
            param_list,
            primitive_name,
            field_list,
            requirement_list,
            method_list,
        )


@line_number_decorator
class _GameASTGenerator(_SharedAST, GameVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: GameParser.ProgramContext) -> frog_ast.GameFile:
        imports = [self.visit(im) for im in ctx.moduleImport()]
        game1: frog_ast.Game = self.visit(ctx.game()[0])
        game2: frog_ast.Game = self.visit(ctx.game()[1])
        return frog_ast.GameFile(
            imports, (game1, game2), ctx.gameExport().ID().getText()
        )


@line_number_decorator
class _ProofASTGenerator(_SharedAST, ProofVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: ProofParser.ProgramContext) -> frog_ast.ProofFile:
        game_list = []
        for i in range(ctx.proofHelpers().getChildCount()):
            game_list.append(self.visit(ctx.proofHelpers().getChild(i)))

        proof = ctx.proof()
        lets = []
        if proof.lets():
            for let in proof.lets().field():
                lets.append(self.visit(let))

        assumptions = []
        max_calls = None
        if proof.assumptions():
            for assumption in proof.assumptions().parameterizedGame():
                assumptions.append(self.visit(assumption))
            if proof.assumptions().CALLS():
                max_calls = self.visit(proof.assumptions().expression())
        return frog_ast.ProofFile(
            [self.visit(im) for im in ctx.moduleImport()],
            game_list,
            lets,
            assumptions,
            max_calls,
            self.visit(proof.theorem().parameterizedGame()),
            self.visit(proof.gameList()),
        )

    def visitParameterizedGame(
        self, ctx: ProofParser.ParameterizedGameContext
    ) -> frog_ast.ParameterizedGame:
        return frog_ast.ParameterizedGame(
            ctx.ID().getText(), self.visit(ctx.argList()) if ctx.argList() else []
        )

    def visitReduction(self, ctx: ProofParser.ReductionContext) -> frog_ast.Reduction:
        return frog_ast.Reduction(
            _parse_game_body(self.visit, ctx),
            self.visit(ctx.parameterizedGame()),
            self.visit(ctx.gameAdversary().parameterizedGame()),
        )

    def visitGameList(
        self, ctx: ProofParser.GameListContext
    ) -> list[frog_ast.ProofStep]:
        steps = []
        for child in ctx.getChildren():
            if child.getText() == ";":
                continue
            steps.append(self.visit(child))
        return steps

    def visitReductionStep(
        self, ctx: ProofParser.ReductionStepContext
    ) -> frog_ast.ProofStep:
        return frog_ast.Step(
            self.visit(ctx.concreteGame()),
            self.visit(ctx.parameterizedGame()),
            self.visit(ctx.gameAdversary().parameterizedGame()),
        )

    def visitConcreteGame(
        self, ctx: ProofParser.ConcreteGameContext
    ) -> frog_ast.ConcreteGame:
        return frog_ast.ConcreteGame(
            self.visit(ctx.parameterizedGame()), ctx.ID().getText()
        )

    def visitStepAssumption(
        self, ctx: ProofParser.StepAssumptionContext
    ) -> frog_ast.StepAssumption:
        return frog_ast.StepAssumption(self.visit(ctx.expression()))

    def visitRegularStep(
        self, ctx: ProofParser.RegularStepContext
    ) -> frog_ast.ProofStep:
        return frog_ast.Step(
            self.visit(ctx.getChild(0)),
            None,
            self.visit(ctx.gameAdversary().parameterizedGame()),
        )

    def visitInduction(self, ctx: ProofParser.InductionContext) -> frog_ast.Induction:
        return frog_ast.Induction(
            ctx.ID().getText(),
            self.visit(ctx.integerExpression()[0]),
            self.visit(ctx.integerExpression()[1]),
            self.visit(ctx.gameList()),
        )


def _parse_game_body(
    visit: Type[PrimitiveVisitor.visit], ctx: ProofParser.GameContext
) -> frog_ast.GameBody:
    name: str = ctx.ID().getText()
    param_list: list[frog_ast.Parameter] = (
        visit(ctx.paramList()) if ctx.paramList() else []
    )
    field_list: list[frog_ast.Field] = []
    if ctx.gameBody().field():
        for field in ctx.gameBody().field():
            field_list.append(visit(field))
    methods: list[frog_ast.Method] = []
    if ctx.gameBody().method():
        for method in ctx.gameBody().method():
            methods.append(visit(method))

    phase_list: list[frog_ast.Phase] = []
    if ctx.gameBody().gamePhase():
        for phase in ctx.gameBody().gamePhase():
            phase_list.append(visit(phase))

    return (name, param_list, field_list, methods, phase_list)


def _get_parser(
    input_: str,
    lexer_functor: type[PrimitiveLexer],
    parser_functor: type[PrimitiveParser],
) -> PrimitiveParser:
    input_stream: InputStream | FileStream
    if os.path.isfile(input_):
        input_stream = FileStream
    elif input_.endswith((".primitive", ".scheme", ".game", ".proof")):
        raise FileNotFoundError(f"file not found: '{input_}'")
    else:
        input_stream = InputStream
    lexer = lexer_functor(input_stream(input_))
    lexer.removeErrorListeners()
    lexer.addErrorListener(_SilentErrorListener())
    parser = parser_functor(CommonTokenStream(lexer))
    parser.removeErrorListeners()
    parser.addErrorListener(_SilentErrorListener())
    # No way to do this without editing the protected field in antlr's python runtime
    parser._errHandler = BailErrorStrategy()  # pylint: disable=protected-access
    return parser


def parse_primitive_file(primitive: str) -> frog_ast.Primitive:
    try:
        ast: frog_ast.Primitive = _PrimitiveASTGenerator().visit(
            _get_parser(primitive, PrimitiveLexer, PrimitiveParser).program()
        )
        return ast
    except antlr_error.Errors.ParseCancellationException as e:
        better = _reparse_for_error(primitive, PrimitiveLexer, PrimitiveParser)
        raise (better or _to_parse_error(e, primitive)) from e


def parse_scheme_file(scheme: str) -> frog_ast.Scheme:
    try:
        ast: frog_ast.Scheme = _SchemeASTGenerator().visit(
            _get_parser(scheme, SchemeLexer, SchemeParser).program()
        )
        return ast
    except antlr_error.Errors.ParseCancellationException as e:
        better = _reparse_for_error(scheme, SchemeLexer, SchemeParser)
        raise (better or _to_parse_error(e, scheme)) from e


def parse_expression(expression: str) -> frog_ast.Expression:
    try:
        ast: frog_ast.Expression = _SharedAST().visit(
            _get_parser(expression, GameLexer, GameParser).expression()
        )
        return ast
    except antlr_error.Errors.ParseCancellationException as e:
        better = _reparse_for_error(expression, GameLexer, GameParser)
        raise (better or _to_parse_error(e, expression)) from e


def parse_game_file(game_file: str) -> frog_ast.GameFile:
    try:
        ast: frog_ast.GameFile = _GameASTGenerator().visit(
            _get_parser(game_file, GameLexer, GameParser).program()
        )
        return ast
    except antlr_error.Errors.ParseCancellationException as e:
        better = _reparse_for_error(game_file, GameLexer, GameParser)
        raise (better or _to_parse_error(e, game_file)) from e


def parse_proof_file(proof_file: str) -> frog_ast.ProofFile:
    try:
        ast: frog_ast.ProofFile = _ProofASTGenerator().visit(
            _get_parser(proof_file, ProofLexer, ProofParser).program()
        )
        return ast
    except antlr_error.Errors.ParseCancellationException as e:
        better = _reparse_for_error(proof_file, ProofLexer, ProofParser)
        raise (better or _to_parse_error(e, proof_file)) from e


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip(".")
    return frog_ast.FileType(extension)


def resolve_import_path(
    import_path: str,
    importing_file_path: str,
    allowed_root: str | None = None,
) -> str:
    """Resolve an import path relative to the importing file's directory.

    If import_path is absolute, it is returned as-is.
    Otherwise it is resolved relative to the directory of importing_file_path
    and normalised (so '../' components are collapsed).

    When *allowed_root* is provided the resolved path must stay within that
    directory tree; a ``ValueError`` is raised otherwise.
    """
    if os.path.isabs(import_path):
        resolved = import_path
    else:
        resolved = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.abspath(importing_file_path)), import_path
            )
        )
    if allowed_root is not None:
        from pathlib import Path  # pylint: disable=import-outside-toplevel

        if not Path(resolved).resolve().is_relative_to(Path(allowed_root).resolve()):
            raise ValueError(
                f"Import '{import_path}' resolves outside the allowed "
                f"directory '{allowed_root}'"
            )
    return resolved


def _get_parser_from_stream(
    content: str,
    lexer_functor: type[PrimitiveLexer],
    parser_functor: type[PrimitiveParser],
) -> PrimitiveParser:
    """Create a parser from raw source text, always using InputStream."""
    lexer = lexer_functor(InputStream(content))
    lexer.removeErrorListeners()
    lexer.addErrorListener(_SilentErrorListener())
    parser = parser_functor(CommonTokenStream(lexer))
    parser.removeErrorListeners()
    parser.addErrorListener(_SilentErrorListener())
    # No way to do this without editing the protected field in antlr's python runtime
    parser._errHandler = BailErrorStrategy()  # pylint: disable=protected-access
    return parser


def parse_string(content: str, file_type: frog_ast.FileType) -> frog_ast.Root:
    """Parse raw source text for a given file type, returning the AST."""
    parser_map: dict[
        frog_ast.FileType,
        tuple[type[PrimitiveLexer], type[PrimitiveParser], _SharedAST],
    ] = {
        frog_ast.FileType.PRIMITIVE: (
            PrimitiveLexer,
            PrimitiveParser,
            _PrimitiveASTGenerator(),
        ),
        frog_ast.FileType.SCHEME: (SchemeLexer, SchemeParser, _SchemeASTGenerator()),
        frog_ast.FileType.GAME: (GameLexer, GameParser, _GameASTGenerator()),
        frog_ast.FileType.PROOF: (ProofLexer, ProofParser, _ProofASTGenerator()),
    }
    lexer_cls, parser_cls, visitor = parser_map[file_type]
    try:
        parser = _get_parser_from_stream(content, lexer_cls, parser_cls)
        ast: frog_ast.Root = visitor.visit(parser.program())
        return ast
    except antlr_error.Errors.ParseCancellationException as e:
        better = _reparse_for_error(content, lexer_cls, parser_cls)
        raise (better or _to_parse_error(e, content)) from e


def parse_string_collecting_errors(
    content: str,
    file_type: frog_ast.FileType,
    file_name: str = "<input>",
) -> tuple[frog_ast.Root | None, list[ParseError]]:
    """Parse raw source text, collecting all errors instead of raising.

    Returns (ast_or_None, list_of_errors).  If parsing succeeds the error
    list is empty and the AST is returned.  Otherwise the AST is ``None``
    and all discovered errors are in the list.
    """
    # First try the fast path (BailErrorStrategy) which succeeds for valid input
    parser_map: dict[
        frog_ast.FileType,
        tuple[type[PrimitiveLexer], type[PrimitiveParser], _SharedAST],
    ] = {
        frog_ast.FileType.PRIMITIVE: (
            PrimitiveLexer,
            PrimitiveParser,
            _PrimitiveASTGenerator(),
        ),
        frog_ast.FileType.SCHEME: (SchemeLexer, SchemeParser, _SchemeASTGenerator()),
        frog_ast.FileType.GAME: (GameLexer, GameParser, _GameASTGenerator()),
        frog_ast.FileType.PROOF: (ProofLexer, ProofParser, _ProofASTGenerator()),
    }
    lexer_cls, parser_cls, visitor = parser_map[file_type]

    try:
        parser = _get_parser_from_stream(content, lexer_cls, parser_cls)
        ast: frog_ast.Root = visitor.visit(parser.program())
        return ast, []
    except antlr_error.Errors.ParseCancellationException:
        pass

    # Re-parse with DefaultErrorStrategy to collect all errors
    lexer = lexer_cls(InputStream(content))
    lexer.removeErrorListeners()
    collector = _CollectingErrorListener()
    parser2 = parser_cls(CommonTokenStream(lexer))
    parser2.removeErrorListeners()
    parser2.addErrorListener(collector)
    try:
        parser2.program()
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    all_lines = content.splitlines(keepends=True)
    errors: list[ParseError] = []
    for line, col, token_text, antlr_msg in collector.errors:
        if token_text == "<EOF>":
            msg = "unexpected end of file" + _eof_hint(all_lines)
        elif token_text:
            msg = f"unexpected token '{token_text}'"
        else:
            msg = "syntax error"

        if antlr_msg and ("expecting" in antlr_msg or "missing" in antlr_msg):
            cleaned = antlr_msg
            cleaned = cleaned.replace("'in', ", "")
            cleaned = cleaned.replace("{", "")
            cleaned = cleaned.replace("}", "")
            cleaned = cleaned.replace("extraneous input", "unexpected")
            cleaned = _clean_antlr_token_names(cleaned)
            msg = cleaned

        source_line = ""
        if 1 <= line <= len(all_lines):
            source_line = all_lines[line - 1].rstrip()

        errors.append(
            ParseError(
                msg,
                file_name=file_name,
                line=line,
                column=col,
                token=token_text,
                source_line=source_line,
            )
        )

    if not errors:
        errors.append(ParseError("syntax error", file_name=file_name))

    return None, errors


def parse_file(file_name: str) -> frog_ast.Root:
    match _get_file_type(file_name):
        case frog_ast.FileType.PRIMITIVE:
            return parse_primitive_file(file_name)
        case frog_ast.FileType.SCHEME:
            return parse_scheme_file(file_name)
        case frog_ast.FileType.GAME:
            return parse_game_file(file_name)
        case frog_ast.FileType.PROOF:
            return parse_proof_file(file_name)
        case _:
            raise ValueError(f"Invalid File Type ${file_name}")


def parse_game(game: str) -> frog_ast.Game:
    try:
        ast: frog_ast.Game = _SharedAST().visit(
            _get_parser(game, GameLexer, GameParser).game()
        )
        return ast
    except antlr_error.Errors.ParseCancellationException as e:
        raise _to_parse_error(e, game) from e


def parse_reduction(reduction: str) -> frog_ast.Reduction:
    try:
        ast: frog_ast.Reduction = _ProofASTGenerator().visit(
            _get_parser(reduction, ProofLexer, ProofParser).reduction()
        )
        return ast
    except antlr_error.Errors.ParseCancellationException as e:
        raise _to_parse_error(e, reduction) from e


def parse_method(method: str) -> frog_ast.Method:
    try:
        ast: frog_ast.Method = _SharedAST().visit(
            _get_parser(method, GameLexer, GameParser).method()
        )
        return ast
    except antlr_error.Errors.ParseCancellationException as e:
        raise _to_parse_error(e, method) from e
