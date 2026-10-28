"""Diagnostic engine for proof hop failures."""

from __future__ import annotations

import dataclasses
import re
from typing import Callable

import sympy

from . import frog_ast
from . import frog_parser
from .transforms._base import NearMiss


@dataclasses.dataclass
class DiffHunk:
    """A single method-level difference between two canonical games."""

    method: str
    current_lines: list[str]
    next_lines: list[str]


def classify_diff(diff_text: str) -> list[DiffHunk]:
    """Parse unified diff from _build_equivalence_diff into DiffHunk objects."""
    hunks: list[DiffHunk] = []
    current_method: str | None = None
    current_lines: list[str] = []
    next_lines: list[str] = []

    for line in diff_text.splitlines():
        header_match = re.match(r"^---\s+(\w+)\s+\(current\)", line)
        if header_match:
            if current_method is not None:
                hunks.append(
                    DiffHunk(
                        method=current_method,
                        current_lines=current_lines,
                        next_lines=next_lines,
                    )
                )
            current_method = header_match.group(1)
            current_lines = []
            next_lines = []
            continue

        if current_method is None:
            continue

        if line.startswith("+++"):
            continue

        stripped = line.lstrip()
        if stripped.startswith("-") and not stripped.startswith("---"):
            current_lines.append(stripped)
        elif stripped.startswith("+") and not stripped.startswith("+++"):
            next_lines.append(stripped)

    if current_method is not None:
        hunks.append(
            DiffHunk(
                method=current_method,
                current_lines=current_lines,
                next_lines=next_lines,
            )
        )

    return hunks


@dataclasses.dataclass
class Explanation:
    """A human-readable explanation for a diff hunk."""

    source_description: str
    reason: str
    suggestion: str | None
    engine_limitation: bool


@dataclasses.dataclass
class Diagnosis:
    """Complete diagnosis of a failed hop."""

    summary: str
    explanations: list[Explanation]
    unmatched_hunks: list[DiffHunk]
    engine_limitations: list[str]


def match_near_misses(
    hunks: list[DiffHunk],
    near_misses: list[NearMiss],
) -> list[tuple[DiffHunk, NearMiss]]:
    """Match near-misses to diff hunks by method and variable overlap."""
    matched: list[tuple[DiffHunk, NearMiss]] = []
    for hunk in hunks:
        for nm in near_misses:
            if nm.method is not None and nm.method != hunk.method:
                continue
            if nm.variable is not None:
                all_diff_text = " ".join(hunk.current_lines + hunk.next_lines)
                if nm.variable not in all_diff_text:
                    continue
            matched.append((hunk, nm))
    return matched


def _strip_diff_prefix(line: str) -> str:
    """Remove leading +/- and whitespace from a diff line."""
    return line.lstrip("+-").strip()


def _extract_expression(line: str) -> str:
    """Extract the core expression from a statement line.

    Strips 'return' prefix and trailing ';' so that operand-order
    comparison works on the expression itself rather than the full
    statement.
    """
    stripped = line.strip()
    if stripped.startswith("return "):
        stripped = stripped[len("return ") :]
    if stripped.endswith(";"):
        stripped = stripped[:-1]
    return stripped.strip()


# The engine normalizes + and * via NormalizeCommutativeChains,
# but || (logical OR on Bool) and && are not yet normalized.
_UNNORMALIZED_COMMUTATIVE_OPS = [" || ", " && "]


def detect_commutativity_diff(hunk: DiffHunk) -> bool:
    """Check if lines differ only in operand order for an operator
    that the engine does not normalize (|| and &&)."""
    if len(hunk.current_lines) != 1 or len(hunk.next_lines) != 1:
        return False
    current = _extract_expression(_strip_diff_prefix(hunk.current_lines[0]))
    next_line = _extract_expression(_strip_diff_prefix(hunk.next_lines[0]))
    if current == next_line:
        return False
    for op in _UNNORMALIZED_COMMUTATIVE_OPS:
        if op in current and op in next_line:
            c_parts = sorted(current.split(op))
            n_parts = sorted(next_line.split(op))
            if c_parts == n_parts:
                return True
    return False


def detect_associativity_diff(hunk: DiffHunk) -> bool:
    """Check if lines differ only in parenthesization of an operator
    that the engine does not normalize (|| and &&)."""
    if len(hunk.current_lines) != 1 or len(hunk.next_lines) != 1:
        return False
    current = _extract_expression(_strip_diff_prefix(hunk.current_lines[0]))
    next_line = _extract_expression(_strip_diff_prefix(hunk.next_lines[0]))
    if current == next_line:
        return False
    current_flat = current.replace("(", "").replace(")", "")
    next_flat = next_line.replace("(", "").replace(")", "")
    if current_flat != next_flat:
        return False
    for op in _UNNORMALIZED_COMMUTATIVE_OPS:
        if op in current and op in next_line:
            return True
    return False


def detect_field_order_diff(hunk: DiffHunk) -> bool:
    """Check if current and next lines are the same set in different order."""
    if not hunk.current_lines or not hunk.next_lines:
        return False
    if len(hunk.current_lines) != len(hunk.next_lines):
        return False
    current_set = sorted(_strip_diff_prefix(line) for line in hunk.current_lines)
    next_set = sorted(_strip_diff_prefix(line) for line in hunk.next_lines)
    return current_set == next_set and [
        _strip_diff_prefix(line) for line in hunk.current_lines
    ] != [_strip_diff_prefix(line) for line in hunk.next_lines]


def detect_extra_temporary_diff(hunk: DiffHunk) -> bool:
    """Check if one side has ``Type v = expr; return v;`` where the other
    has ``return expr;`` directly.

    This happens when the SimplifyReturn transform fires on one game
    but not the other, typically because the games were written differently.
    """
    if not hunk.current_lines or not hunk.next_lines:
        return False

    def _is_assign_then_return(lines: list[str]) -> bool:
        stripped = [_strip_diff_prefix(line) for line in lines]
        if len(stripped) != 2:
            return False
        # Pattern: "Type v = expr;" followed by "return v;"
        first = stripped[0]
        second = stripped[1]
        if not second.startswith("return ") or not first.endswith(";"):
            return False
        ret_var = second[len("return ") :].rstrip(";").strip()
        # Check first line is an assignment to ret_var
        return f" {ret_var} = " in first or f" {ret_var}=" in first

    def _is_direct_return(lines: list[str]) -> bool:
        stripped = [_strip_diff_prefix(line) for line in lines]
        return len(stripped) == 1 and stripped[0].startswith("return ")

    return (
        _is_assign_then_return(hunk.current_lines)
        and _is_direct_return(hunk.next_lines)
    ) or (
        _is_direct_return(hunk.current_lines)
        and _is_assign_then_return(hunk.next_lines)
    )


def _normalize_branch_prefix(line: str) -> str:
    """Strip 'if'/'else if' prefix to get just the condition and body."""
    stripped = line.strip()
    if stripped.startswith("else if "):
        return stripped[len("else if ") :]
    if stripped.startswith("if "):
        return stripped[len("if ") :]
    return stripped


def detect_if_condition_reorder_diff(hunk: DiffHunk) -> bool:
    """Check if if/else-if branches are the same set in different order.

    This detects when two games have the same set of conditional branches
    but listed in different order, which the engine does not normalize.
    """
    if len(hunk.current_lines) < 2 or len(hunk.next_lines) < 2:
        return False
    if len(hunk.current_lines) != len(hunk.next_lines):
        return False
    current_stripped = [_strip_diff_prefix(line) for line in hunk.current_lines]
    next_stripped = [_strip_diff_prefix(line) for line in hunk.next_lines]
    # Check that the lines contain if/else-if patterns
    has_if = any("if (" in line for line in current_stripped)
    if not has_if:
        return False
    # Normalize away if/else-if prefixes so branch reordering is detected
    current_branches = sorted(
        _normalize_branch_prefix(line) for line in current_stripped
    )
    next_branches = sorted(_normalize_branch_prefix(line) for line in next_stripped)
    return current_branches == next_branches and current_stripped != next_stripped


def _split_statement(line: str) -> tuple[str, str] | None:
    """Split ``return e;`` or ``<lhs> = e;`` into a head and the expression."""
    stripped = line.strip()
    if not stripped.endswith(";"):
        return None
    stripped = stripped[:-1].strip()
    if stripped.startswith("return "):
        return "return", stripped[len("return ") :].strip()
    head, sep, expression = stripped.partition(" = ")
    if not sep:
        return None
    return head.strip(), expression.strip()


_RING_OPERATORS = {
    frog_ast.BinaryOperators.ADD: lambda a, b: a + b,
    frog_ast.BinaryOperators.SUBTRACT: lambda a, b: a - b,
    frog_ast.BinaryOperators.MULTIPLY: lambda a, b: a * b,
}


def _ring_value(node: frog_ast.Expression) -> sympy.Expr | None:
    """The polynomial ``node`` denotes, if it is ``+``/``-``/``*``/negation
    over Int literals and names; otherwise ``None``."""
    if isinstance(node, frog_ast.Integer):
        return sympy.Integer(node.num)
    if isinstance(node, (frog_ast.Variable, frog_ast.FieldAccess)):
        return sympy.Symbol(str(node))
    if (
        isinstance(node, frog_ast.UnaryOperation)
        and node.operator == frog_ast.UnaryOperators.MINUS
    ):
        inner = _ring_value(node.expression)
        return None if inner is None else -inner
    if isinstance(node, frog_ast.BinaryOperation) and node.operator in _RING_OPERATORS:
        left = _ring_value(node.left_expression)
        right = _ring_value(node.right_expression)
        if left is None or right is None:
            return None
        return sympy.sympify(_RING_OPERATORS[node.operator](left, right))
    return None


def _has_negated_operand(node: frog_ast.Expression) -> bool:
    """Whether an arithmetic operand in ``node`` is ``-c`` for a literal or
    name ``c``."""
    if not isinstance(node, frog_ast.BinaryOperation):
        return False
    for operand in (node.left_expression, node.right_expression):
        if (
            isinstance(operand, frog_ast.UnaryOperation)
            and operand.operator == frog_ast.UnaryOperators.MINUS
            and isinstance(
                operand.expression,
                (frog_ast.Integer, frog_ast.Variable, frog_ast.FieldAccess),
            )
        ):
            return True
        if _has_negated_operand(operand):
            return True
    return False


def detect_unfolded_negation_diff(hunk: DiffHunk) -> bool:
    """Check if two statements differ only in Int arithmetic that is equal
    as a polynomial, where a side has a negated operand.

    SymbolicComputation does not evaluate a negation, so arithmetic with a
    ``-c`` operand stays unfolded: ``x + -3`` does not meet ``x - 3``, nor
    ``2 + -2`` meet ``0``.  The negation may be written in the game or come
    from an earlier fold (``3 - 5`` becomes ``-2``).  When both operands are
    constants the pass records a near miss, which explains the hunk first.
    """
    if len(hunk.current_lines) != 1 or len(hunk.next_lines) != 1:
        return False
    current = _split_statement(_strip_diff_prefix(hunk.current_lines[0]))
    next_line = _split_statement(_strip_diff_prefix(hunk.next_lines[0]))
    if current is None or next_line is None:
        return False
    if current[0] != next_line[0] or current[1] == next_line[1]:
        return False
    try:
        current_expr = frog_parser.parse_expression(current[1])
        next_expr = frog_parser.parse_expression(next_line[1])
    except frog_parser.ParseError:
        return False
    if not (_has_negated_operand(current_expr) or _has_negated_operand(next_expr)):
        return False
    current_value = _ring_value(current_expr)
    next_value = _ring_value(next_expr)
    if current_value is None or next_value is None:
        return False
    return bool(sympy.expand(current_value - next_value) == 0)


# `x <- T \ E;` or `x <-uniq[E] T;`: a draw whose domain may be empty.
_EXCLUSION_DRAW = re.compile(r"<-uniq\[|<-[^;]*\\")


def detect_possibly_empty_draw_diff(hunk: DiffHunk) -> bool:
    """Check if the sides differ only in draws ``x <- T \\ E;`` /
    ``x <-uniq[E] T;`` present on one side and not the other.

    Such a draw is kept even when its result is unused, because when ``E``
    covers ``T`` it does not complete (the engine cannot tell that ``E``
    never does, e.g. for ``ModInt<q> \\ {0}`` with ``q`` prime).
    """
    current = [_strip_diff_prefix(line) for line in hunk.current_lines]
    next_lines = [_strip_diff_prefix(line) for line in hunk.next_lines]
    current_rest = [line for line in current if not _EXCLUSION_DRAW.search(line)]
    next_rest = [line for line in next_lines if not _EXCLUSION_DRAW.search(line)]
    if current_rest != next_rest:
        return False
    current_draws = sorted(set(current) - set(current_rest))
    next_draws = sorted(set(next_lines) - set(next_rest))
    return current_draws != next_draws


_DETECTORS: list[tuple[Callable[[DiffHunk], bool], str, str]] = []


def _register(
    func: Callable[[DiffHunk], bool], description: str, workaround: str
) -> None:
    _DETECTORS.append((func, description, workaround))


_register(
    detect_commutativity_diff,
    "The engine does not normalize operand order for || and && operators",
    "Reorder operands manually in your intermediate game",
)
_register(
    detect_field_order_diff,
    "The engine does not reorder these statements",
    "Match the statement order from the previous game",
)
_register(
    detect_associativity_diff,
    "The engine does not normalize associativity for || and && operators",
    "Reparenthesize the expression in your intermediate game to match the previous step",
)
_register(
    detect_extra_temporary_diff,
    "One game uses a temporary variable where the other returns directly",
    "Either inline the temporary (use 'return expr;' directly)"
    + " or add the temporary to both games so they match",
)
_register(
    detect_if_condition_reorder_diff,
    "The engine does not reorder if/else-if branches",
    "Match the branch order from the previous game",
)
_register(
    detect_unfolded_negation_diff,
    "The engine does not evaluate a negation in Int arithmetic, so arithmetic"
    + " with a negated operand (written, or left by an earlier fold such as"
    + " '3 - 5' becoming '-2') stays unfolded",
    "Make both games reach the same arithmetic here, for example by writing"
    + " the subtraction or folded value the other game has",
)

_register(
    detect_possibly_empty_draw_diff,
    "The engine keeps a draw 'x <- T \\ E;' or 'x <-uniq[E] T;' even when x is"
    + " unused, and does not move it across a return: when E covers T the"
    + " draw does not complete, which the adversary observes",
    "Keep the same draw at the same place in both games; if its domain is"
    + " never empty, draw from a type or exclude a set literal smaller than"
    + " the type instead",
)

ENGINE_LIMITATION_DETECTORS = _DETECTORS


def diagnose_failure(
    diff_text: str,
    current_near_misses: list[NearMiss],
    next_near_misses: list[NearMiss],
) -> Diagnosis:
    """Produce a structured diagnosis from a diff and near-misses."""
    hunks = classify_diff(diff_text)
    all_near_misses = current_near_misses + next_near_misses
    matched = match_near_misses(hunks, all_near_misses)

    explanations: list[Explanation] = []
    matched_hunk_ids: set[int] = set()

    for hunk, nm in matched:
        matched_hunk_ids.add(id(hunk))
        desc = f"Method '{hunk.method}' differs"
        if nm.location is not None:
            desc += f" (near {nm.location.file}:{nm.location.line})"
        explanations.append(
            Explanation(
                source_description=desc,
                reason=nm.reason,
                suggestion=nm.suggestion,
                engine_limitation=False,
            )
        )

    unmatched = [h for h in hunks if id(h) not in matched_hunk_ids]

    for hunk in unmatched:
        n_lines = len(hunk.current_lines) + len(hunk.next_lines)
        explanations.append(
            Explanation(
                source_description=f"Method '{hunk.method}' differs",
                reason=f"{n_lines} lines differ in canonical form",
                suggestion=None,
                engine_limitation=False,
            )
        )

    # Check engine limitations on unmatched hunks
    engine_limitations: list[str] = []
    for hunk in unmatched:
        for detector, description, workaround in ENGINE_LIMITATION_DETECTORS:
            if detector(hunk):
                engine_limitations.append(
                    f"{description} (in method '{hunk.method}'). "
                    f"Workaround: {workaround}"
                )
                for expl in explanations:
                    if expl.source_description == f"Method '{hunk.method}' differs":
                        expl.engine_limitation = True
                        expl.suggestion = workaround
                break

    if explanations:
        first = explanations[0]
        if first.suggestion is not None:
            # Near-miss match — hedge the summary
            summary = f"{first.source_description} (possible cause: {first.reason})"
        else:
            summary = f"{first.source_description}: {first.reason}"
    elif hunks:
        summary = f"{len(hunks)} method(s) differ in canonical form"
    else:
        summary = "Games differ but no specific differences identified"

    return Diagnosis(
        summary=summary,
        explanations=explanations,
        unmatched_hunks=unmatched,
        engine_limitations=engine_limitations,
    )
