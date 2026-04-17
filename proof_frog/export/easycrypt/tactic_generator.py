"""Generate EasyCrypt tactic scripts from canonicalization traces.

Scope: trace-driven generator with a small per-transform handler
registry. Unknown transforms fall back to ``admit`` with a comment
identifying the offending transform.
"""

from __future__ import annotations

from typing import Callable, Optional

from ... import frog_ast

# Transforms that the prelude (``proc. inline *.``) and closer
# (``wp. auto.``) collectively discharge. No tactic emitted for these.
# Names match ``TransformPass.name`` strings in ``proof_frog/transforms/``.
_ABSORBED: frozenset[str] = frozenset(
    {
        "Remove Redundant Copies",
        "Inline Single-Use Variables",
        "Collapse Assignment",
        "Forward Expression Alias",
        "Inline Multi-Use Pure Expressions",
        "Hoist Field Pure Alias",
        "Inline Single-Use Field",
        "Simplify Returns",
        "Remove unnecessary statements and fields",
        "Remove redundant variables for fields",
        "Simplify Nots",
        "Reflexive Comparison",
        "Variable Standardization",
        "Standardize Field Names",
        "Redundant Conditional Return",
        "Dead Null Guard Elimination",
        "Subset Type Normalization",
        "Remove Duplicate Fields",
        "Expand Tuples",
        "Fold Tuple Literal Indexing",
        "Simplify tuples that are copies of their fields",
        "Collapse Single-Index Tuple Access",
        "Symbolic Computation",
    }
)


# Type of a handler. Returns the tactic line(s) to insert before the closer,
# or None to fall back to admit.
_Handler = Callable[
    [frog_ast.Game, frog_ast.Game, str],
    Optional[list[str]],
]


_HANDLERS: dict[str, _Handler] = {}  # populated below


def generate(
    left_trace: dict[str, object],
    right_trace: dict[str, object],
    left_ast: frog_ast.Game,
    right_ast: frog_ast.Game,
    method_name: str,
) -> list[str]:
    """Produce EC tactic lines for an interchangeability hop.

    Returns a list of lines suitable to assign to ``ec_ast.Lemma.body``.
    Always ends with ``"qed."``. May contain an admit fallback when the
    trace contains an unhandled transform.
    """
    left_fired = _flatten_transforms(left_trace)
    right_fired = _flatten_transforms(right_trace)
    # When the same non-absorbed transform fires on both sides, the two
    # simplifications cancel out at the EC level (both EC programs shrink
    # by the same step); emit the handler only for the asymmetric residue.
    left_residual = _strip_matching(left_fired, right_fired)
    right_residual = _strip_matching(right_fired, left_fired)
    fired = left_residual + right_residual
    handled_lines: list[str] = []
    for name in fired:
        if name in _ABSORBED:
            continue
        handler = _HANDLERS.get(name)
        if handler is None:
            return [
                f"admit. (* unhandled transform: {name} *)",
                "qed.",
            ]
        produced = handler(left_ast, right_ast, method_name)
        if produced is None:
            return [
                f"admit. (* handler for {name} returned None *)",
                "qed.",
            ]
        handled_lines.extend(produced)
    if handled_lines:
        return ["proc.", "inline *.", "wp.", *handled_lines, "qed."]
    return ["proc.", "inline *.", "wp.", "auto.", "qed."]


def _flatten_transforms(trace: dict[str, object]) -> list[str]:
    iterations = trace.get("iterations", [])
    assert isinstance(iterations, list)
    flat: list[str] = []
    for it in iterations:
        assert isinstance(it, dict)
        names = it.get("transforms_applied", [])
        assert isinstance(names, list)
        flat.extend(names)
    return flat


def _strip_matching(xs: list[str], ys: list[str]) -> list[str]:
    """Return xs with one occurrence of each item in ys removed (if present)."""
    remaining = list(ys)
    out: list[str] = []
    for x in xs:
        if x in remaining:
            remaining.remove(x)
        else:
            out.append(x)
    return out


def _uniform_xor_handler(
    left: frog_ast.Game,
    _right: frog_ast.Game,
    method_name: str,
) -> Optional[list[str]]:
    """Handler for ``Uniform XOR Simplification``.

    Heuristic (sufficient for OTPSecure; will generalize later):
    1. Find the method on ``left`` whose name lower-cases to ``method_name``.
    2. Find the unique Sample of a BitString in that method.
    3. Use the bitstring's EC type name to pick the right xor op.
    4. Use the method's first parameter as the offset.
    5. Emit ``rnd`` with the bijection ``fun z => xor_<bs> z <param>{2}``
       (self-inverse) and a closing line that discharges subgoals via
       ``smt`` with the xor-involution and distribution-funiform axioms.

    Returns None if any precondition fails.
    """
    method = next(
        (m for m in left.methods if m.signature.name.lower() == method_name),
        None,
    )
    if method is None:
        return None
    sample: frog_ast.Sample | None = None
    for stmt in method.block.statements:
        if isinstance(stmt, frog_ast.Sample) and isinstance(
            stmt.the_type, frog_ast.BitStringType
        ):
            if sample is not None:
                return None  # ambiguous -- multiple samples
            sample = stmt
    if sample is None or not method.signature.parameters:
        return None
    offset = method.signature.parameters[0].name
    bs_type = sample.the_type
    assert isinstance(bs_type, frog_ast.BitStringType)
    bs_name = _bitstring_name(bs_type)
    xor_op = f"xor_{bs_name}"
    distr = f"dbs_{bs_name}"
    return [
        f"rnd (fun z => {xor_op} z {offset}{{2}})"
        f" (fun z => {xor_op} z {offset}{{2}}).",
        f"auto => />; progress; smt({xor_op}_invol {distr}_fu).",
    ]


def _bitstring_name(t: frog_ast.BitStringType) -> str:
    """Return the sanitized length suffix used after ``bs_`` / ``xor_`` / ``dbs_``.

    For ``BitString<lambda>`` this returns ``"lambda"``, which combines with
    the prefixes emitted by ``type_collector`` (e.g. ``xor_lambda``).
    """
    import re  # pylint: disable=import-outside-toplevel

    text = str(t.parameterization) if t.parameterization else ""
    sanitized = re.sub(r"\W+", "_", text).strip("_")
    return sanitized or "default"


_HANDLERS["Uniform XOR Simplification"] = _uniform_xor_handler
