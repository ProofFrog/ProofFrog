# pylint: disable=duplicate-code
"""Classification of ProofFrog transforms into EC-tactic buckets.

Each transform falls into one of three buckets:

* :data:`Bucket.CANNED` — a fixed EC tactic script discharges the
  per-application equiv lemma. The script either has no slots (1a,
  stored as a static string list in :data:`CANNED_TACTIC`) or has slots
  filled from the :class:`TransformApplication` diff (1b, stored as a
  callable in :data:`PARAMETRIC_TACTIC`).
* :data:`Bucket.INTERACTIVE` — no fixed script and no parametric
  template yet; tractable for Claude with the EasyCrypt MCP server but
  the prototype emits ``admit.``.
* :data:`Bucket.OPEN` — substantial probabilistic reasoning required
  (ROM, PRF libraries). Always ``admit.``.

Entries here use the engine's human-readable ``name`` (e.g.
``"Remove Redundant Copies"``), not the Python class name.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable

from .type_collector import TypeCollector
from ...transforms._base import TransformApplication
from . import parametric_tactics


class Bucket(Enum):
    CANNED = "canned"
    INTERACTIVE = "interactive"
    OPEN = "open"


TRANSFORM_BUCKET: dict[str, Bucket] = {
    # --- Bucket 1: canned tactic (static or parametric) ---
    "Remove Redundant Copies": Bucket.CANNED,
    "Inline Single-Use Variables": Bucket.CANNED,
    "Collapse Assignment": Bucket.CANNED,
    "Forward Expression Alias": Bucket.CANNED,
    "Hoist Field Pure Alias": Bucket.CANNED,
    "Inline Single-Use Field": Bucket.CANNED,
    "Simplify Returns": Bucket.CANNED,
    "Remove unnecessary statements and fields": Bucket.CANNED,
    "Topological Sorting": Bucket.CANNED,
    "Bubble Sort Field Assignments": Bucket.CANNED,
    "Stabilize Independent Statements": Bucket.CANNED,
    "Branch Elimination": Bucket.CANNED,
    "Reflexive Comparison": Bucket.CANNED,
    "Simplify Ifs": Bucket.CANNED,
    "Variable Standardization": Bucket.CANNED,
    # Capture-avoiding rename of bound locals to fresh ``__aN__`` names
    # (the global ``AlphaRename`` canonicalization pass). Like ``Variable
    # Standardization`` it only renames locals, so both EC bodies are
    # structurally identical and ``proc; auto.`` closes the equiv.
    "Alpha Rename": Bucket.CANNED,
    "Standardize Field Names": Bucket.CANNED,
    # NB: ``Standardize Parameters`` is intentionally absent. The exporter
    # excludes that pass from a hop's canonicalization chain (see
    # ``exporter._EXPORT_SKIP_PASSES``), so it never surfaces as a micro. It is
    # left OPEN (default) deliberately: were it to escape the skip, a name-based
    # ``proc; auto.`` could not close it (the two sides carry different
    # parameter names), so an honest visible ``admit`` is preferable to a
    # silently-non-closing canned tactic.
    "Subset Type Normalization": Bucket.CANNED,
    # ``Symbolic Computation`` and ``Normalize Commutative Chains`` only
    # rewrite at the FrogLang type level (sympy-canonical bitstring
    # parameterizations) or commute already-equal sub-expressions; on the
    # EC body they are no-ops once the expression translator canonicalizes
    # int arguments to slice/concat. ``proc; sim.`` closes them.
    "Symbolic Computation": Bucket.CANNED,
    "Normalize Commutative Chains": Bucket.CANNED,
    # Parametric (Bucket 1b): canned template with slots from the diff.
    "Uniform XOR Simplification": Bucket.CANNED,
    # Additive-group analogue of Uniform XOR: ``u +/- m -> u`` over
    # ModInt<q>. Synthesizer emits an ``rnd`` bijection over add/sub.
    "Uniform ModInt Simplification": Bucket.CANNED,
    # Parametric synthesizer in ``parametric_tactics`` emits a
    # ``transitivity`` + ``rndsem`` + ``rnd`` tactic that uses the per-
    # clone distribution-split axiom plus slice/concat round-trip axioms
    # (emitted by ``TypeCollector.emit()``) to close the equiv.
    "Merge Uniform Samples": Bucket.CANNED,
    "Split Uniform Samples": Bucket.CANNED,
    # --- Bucket 2: interactive/cached ---
    "Uniform GroupElem Simplification": Bucket.INTERACTIVE,
    "Simplifying Splices": Bucket.INTERACTIVE,
    "Merge Product Samples": Bucket.INTERACTIVE,
    "Sink Uniform Sample": Bucket.INTERACTIVE,
    "XOR Cancellation": Bucket.INTERACTIVE,
    "XOR Identity": Bucket.INTERACTIVE,
    "Single Call Field To Local": Bucket.INTERACTIVE,
    "Counter Guarded Field To Local": Bucket.INTERACTIVE,
    # --- Bucket 3: open / ROM / PRF ---
    "Local RF To Uniform": Bucket.OPEN,
    "Challenge Exclusion RF To Uniform": Bucket.OPEN,
    "Unique RF Simplification": Bucket.OPEN,
    "Extract RF Calls": Bucket.OPEN,
    "Distinct Const RF To Uniform": Bucket.OPEN,
    "Fresh Input RF To Uniform": Bucket.OPEN,
}


# Bucket 1a — static canned tactic scripts.
CANNED_TACTIC: dict[str, list[str]] = {
    "Remove Redundant Copies": ["proc; sp; auto."],
    "Inline Single-Use Variables": ["proc; sp; auto."],
    "Collapse Assignment": ["proc; sp; auto."],
    "Forward Expression Alias": ["proc; sp; auto."],
    "Hoist Field Pure Alias": ["proc; sp; auto."],
    "Inline Single-Use Field": ["proc; sp; auto."],
    "Simplify Returns": ["proc; wp; auto."],
    "Remove unnecessary statements and fields": ["proc; auto."],
    "Branch Elimination": ["proc; auto."],
    "Reflexive Comparison": ["proc; auto."],
    "Simplify Ifs": ["proc; auto."],
    "Variable Standardization": ["proc; auto."],
    # Pure local-variable rename (capture avoidance); structurally a no-op
    # on the EC body, same as ``Variable Standardization``.
    "Alpha Rename": ["proc; auto."],
    "Standardize Field Names": ["proc; auto."],
    # Type-system rename only (e.g. KeySpace2 -> IntermediateSpace via a
    # ``requires`` subsets clause). EC's clone-driven type aliases make
    # this a structural no-op on both sides.
    "Subset Type Normalization": ["proc; sim."],
    # No-op on the EC body once int args to slice/concat are sympy-
    # canonicalized (see ``expr_translator._canonical_int_str``); both
    # bodies are syntactically identical so ``sim`` matches them.
    "Symbolic Computation": ["proc; sim."],
    "Normalize Commutative Chains": ["proc; sim."],
    # Pure-reorder transforms are handled in ``exporter._tactic_for`` by
    # synthesizing ``swap{1} pos delta.`` tactics from the AST diff
    # (``_permutation_swaps``); the empty list here keeps them
    # classified as ``Bucket.CANNED`` for ``classify()`` but signals
    # "synthesize, don't use a static body". Falls back to ``admit.``
    # when the diff isn't a pure permutation (e.g. ``Topological
    # Sorting`` may also drop dead samples).
    "Topological Sorting": [],
    "Bubble Sort Field Assignments": [],
    "Stabilize Independent Statements": [],
}


# Bucket 1b — parametric tactic synthesizers. Each callable takes the
# TransformApplication plus an optional TypeCollector (for synthesizers
# that need to look up bit-length expressions or register slice/concat
# ops on demand) and returns the rendered tactic body (or None to fall
# back to admit if synthesis fails).
PARAMETRIC_TACTIC: dict[
    str,
    Callable[..., list[str] | None],
] = {
    "Uniform XOR Simplification": parametric_tactics.uniform_xor_tactic,
    "Uniform ModInt Simplification": parametric_tactics.uniform_modint_tactic,
    "Inline Single-Use Variables": (
        parametric_tactics.inline_single_use_variables_tactic
    ),
    "Merge Uniform Samples": parametric_tactics.merge_uniform_samples_tactic,
    "Split Uniform Samples": parametric_tactics.split_uniform_samples_tactic,
    "Normalize Commutative Chains": (
        parametric_tactics.normalize_commutative_chains_tactic
    ),
}


def classify(transform_name: str) -> Bucket:
    """Return the bucket for ``transform_name`` (defaults to OPEN)."""
    return TRANSFORM_BUCKET.get(transform_name, Bucket.OPEN)


def tactic_body(
    transform_name: str,
    app: TransformApplication | None = None,
    types: TypeCollector | None = None,
) -> list[str] | None:
    """Return the canned tactic body for ``transform_name``.

    Tries the parametric synthesizer (1b) first when ``app`` is provided
    — synthesizers inspect the application's AST and tune the tactic to
    the specific structure, so they should win when both kinds are
    registered for a transform. ``types`` is passed through for
    synthesizers that need it (Split/Merge Uniform Samples). Falls back
    to the static body (1a) otherwise. Returns ``None`` if neither is
    available (caller falls back to ``admit.``).
    """
    if app is not None and transform_name in PARAMETRIC_TACTIC:
        synthesized = PARAMETRIC_TACTIC[transform_name](app, types)
        if synthesized is not None:
            return synthesized
    static = CANNED_TACTIC.get(transform_name)
    if static:
        return static
    return None
