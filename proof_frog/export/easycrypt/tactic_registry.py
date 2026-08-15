"""The transform-keyed tactic registry (the exporter's architecture).

The ratified exporter architecture (2026-08-14) requires, verbatim:

    "The tactic attached to a micro-lemma MUST be obtained from the
    transform registry, looked up by that application's transform name,
    and by nothing else. A registered entry MAY inspect the AST or
    rendered bodies AFTER selection."

This module is that registry's declarative core: the map from each
transform name to the tactic ENTRY IDS registered for it, plus the
transform-set constants the selection gates share. Every closure the
chain emitter produces for a micro-lemma is tagged
``(* resolution: <rung> transform="<name>" entry="<id>" *)`` (see
:mod:`resolution`), and the conformance test fails any export whose
``(transform, entry)`` pair is not registered here.

Registration semantics by rung:

* ``synth-static`` / ``synth-param`` closures need a registered
  ``(transform, entry)`` pair.
* ``cached-*`` closures are conforming with a ``transform`` attribute
  alone — the tactic cache is itself keyed by transform (its own
  layer of the registry), so the entry id is the cache.
* ``admit-*`` emissions carry the ``transform`` attribute and no entry
  (an admit names the transform it is waiting on; nothing closed).

Tactic BODIES currently live in :mod:`transform_buckets` (canned /
parametric) and in the chain emitter's gated routes; they migrate here
as the multi-oracle path is rewired through the registry. Until then
this module owns only selection legality, which is what enforcement
needs.
"""

from __future__ import annotations

from .resolution import (
    ADMIT_GUIDED,
    ADMIT_UNGUIDED,
    CACHED_GUIDED,
    CACHED_UNGUIDED,
)
from .transform_buckets import CANNED_TACTIC, PARAMETRIC_TACTIC

# --- Transform-set constants shared with the chain emitter's gates. ---
# (Moved here from ``chain_emitter`` so the registry is the single
# source; ``chain_emitter`` re-imports them.)

REORDER_TRANSFORMS = frozenset(
    {
        "Topological Sorting",
        "Bubble Sort Field Assignments",
        "Stabilize Independent Statements",
    }
)

# Transforms that drop a local tuple and rewrite its projections to the
# components; the stateless ``Ideal`` route's ``_ec_tuple_inline``
# handles them name-independently.
TUPLE_INLINE_TRANSFORMS = frozenset(
    {
        "Inline Local Tuple Literal",
        "Expand Tuples",
    }
)

# Deterministic tuple-projection rewrites whose micro keeps the *whole*
# abstract-call sequence identical (same callees, same order, same
# multiset) and only rearranges deterministic tuple-construction/
# projection plumbing (e.g. ``t <@ KeyGen(); x = t[0]`` <->
# ``r <@ KeyGen(); t = r[0]; x = t``). There is no call reorder at all,
# so the swap routes have nothing to do and the stateless/tuple-walk
# routes are single-module only; in a multi-declared-module body these
# fall through to ``admit``. The functional-twin route closes them: in
# the twins every det call is an ``ev_*`` assignment, so both sides hold
# the same probabilistic calls in the same order and the identical-order
# ``(wp; call)*`` middle leg discharges the plumbing difference via
# ``wp`` + ``skip => /#``.
PLUMBING_REWRITE_TRANSFORMS = frozenset(
    {
        "Collapse Single-Index Tuple Access",
        "Expand Tuples",
        "Inline Single-Use Variables",
        # Inlining a *pure multi-use expression* into its use sites: a
        # local ``label <- concat ... ; F.evaluate(.., label)`` (used
        # twice) becomes ``F.evaluate(.., concat ...)`` at each site. The
        # abstract-call sequence is identical; only a deterministic
        # assignment is dropped and its expression substituted into call
        # args -- ``wp`` collects the inlined assignment, ``skip => /#``
        # equates the substituted expressions. The static ``sp; wp;
        # sim`` leaves that equality open.
        "Inline Multi-Use Pure Expressions",
        # The dual rewrite: a repeated deterministic tuple access
        # (``v.`1`` used several times) is extracted to a CSE local
        # (``__cse_v_0__ <- v.`1``) and the uses rewired to it. Again the
        # abstract-call sequence is identical; the diff is the extra CSE
        # assignments plus the rewired tuple-construction RHS, both
        # absorbed by ``wp`` with ``skip => /#`` closing the
        # construction equality.
        "Extract Repeated Tuple Access",
        # A deterministic copy-alias rewrite that swaps a call argument
        # for its definitional equal (``encodeencapskey(__determ_4__.`1)``
        # <-> ``encodeencapskey(tup_01)`` given ``tup_01 <-
        # __determ_4__.`1``). The abstract-call *sequence* is identical
        # (only one argument expression changed), so the identical-order
        # ``(wp; call)*`` middle leg closes it; the static ``sp; wp;
        # sim`` otherwise leaves that equality open (a 0-admit file EC
        # rejects).
        "Forward Expression Alias",
    }
)

# Transforms whose micros are closed by a chain-emitter-level synthesizer
# rather than a ``transform_buckets`` entry (the dashboard credits them
# from this set).
CHAIN_EMITTER_SYNTH_TRANSFORMS = frozenset(
    TUPLE_INLINE_TRANSFORMS
    | PLUMBING_REWRITE_TRANSFORMS
    | {"Deduplicate Deterministic Calls"}
)

# --- Entry ids for the chain emitter's gated single-oracle routes. ---

ENTRY_CANNED = "canned-static"
ENTRY_DET_REORDER = "det-reorder-twin"
ENTRY_PERM_SWAP_SIM = "perm-swap-sim"
ENTRY_RENDERED_SWAP_SIM = "rendered-swap-sim"
ENTRY_DEAD_SAMPLE_DROP = "dead-sample-drop"
ENTRY_PERM_SWAP_SPWPSIM = "perm-swap-spwpsim"
ENTRY_RENDERED_SWAP_SPWPSIM = "rendered-swap-spwpsim"
ENTRY_ISUV_WALK = "isuv-walk"
ENTRY_MULTI_MODULE_STATIC = "multi-module-static"

# --- Entry ids for the multi-oracle leg moves. ---

ENTRY_IDENTITY_SIM = "identity-sim"
ENTRY_RENAME_SIM = "rename-sim"
ENTRY_SURVIVOR_PEEL = "survivor-peel"
ENTRY_HOIST_PAIR = "hoist-pair"

# UNIVERSAL entries: registered for EVERY transform, explicitly, here.
# Justification (the bystander rule): a chain leg projects one oracle out
# of a whole-game step, so a transform that rewrote some OTHER oracle
# leaves this projection equal (or equal modulo local renaming, or a pure
# statement permutation). The tactic for such a leg -- ``proc; sim`` or
# ``swap``+``sim`` -- is proven outright by EasyCrypt with no
# transform-specific fact, and is the canonical closure for the property
# "this application did not touch this oracle". Under R3 this is one
# implementation explicitly registered for every transform, recorded
# once, in this constant, rather than per-name table rows.
UNIVERSAL_ENTRIES = frozenset(
    {
        ENTRY_IDENTITY_SIM,
        ENTRY_RENAME_SIM,
        ENTRY_PERM_SWAP_SIM,
    }
)

# The survivor peel serves the field-set-changing transforms: a
# cardinality-differing state pair can only be produced by a transform
# that adds or removes fields, and the peel's two honest gates (unbroken
# or paired backbone; bodies equal under the coupling's field renaming)
# hold exactly for the remove-a-field-keep-the-survivor shape.
FIELD_SET_TRANSFORMS = frozenset(
    {
        "Remove redundant variables for fields",
        "Remove unnecessary statements and fields",
        "Inline Single-Use Field",
        "Localize Init-Only Field Sample",
        "Remove Duplicate Fields",
        "Hoist Field Pure Alias",
    }
)


def param_entry_id(transform_name: str) -> str:
    """Entry id of the parametric synthesizer registered for a transform."""
    return f"param:{PARAMETRIC_TACTIC[transform_name].__name__}"


def _build_registry() -> dict[str, frozenset[str]]:
    reg: dict[str, set[str]] = {}

    def add(transform: str, entry: str) -> None:
        reg.setdefault(transform, set()).add(entry)

    for name, body in CANNED_TACTIC.items():
        if body:
            add(name, ENTRY_CANNED)
    for name in PARAMETRIC_TACTIC:
        add(name, param_entry_id(name))
    for name in REORDER_TRANSFORMS:
        add(name, ENTRY_PERM_SWAP_SIM)
        add(name, ENTRY_RENDERED_SWAP_SIM)
        add(name, ENTRY_DEAD_SAMPLE_DROP)
    # The multi-module branch runs only for CANNED-bucket transforms with
    # a static body; its swap synthesizers and static fallback serve
    # exactly those transforms.
    for name, body in CANNED_TACTIC.items():
        if body:
            add(name, ENTRY_PERM_SWAP_SPWPSIM)
            add(name, ENTRY_RENDERED_SWAP_SPWPSIM)
            add(name, ENTRY_MULTI_MODULE_STATIC)
    add("Inline Single-Use Variables", ENTRY_ISUV_WALK)
    # The functional-twin deterministic-reorder route: registered for the
    # transform families its gates were designed and validated against.
    # If a real export fires it on a transform outside this list, the
    # conformance test fails and the registration (or the gate) is
    # revisited explicitly — that is the enforcement working, not an
    # error to paper over.
    for name in (
        REORDER_TRANSFORMS
        | PLUMBING_REWRITE_TRANSFORMS
        | TUPLE_INLINE_TRANSFORMS
        | {"Deduplicate Deterministic Calls"}
    ):
        add(name, ENTRY_DET_REORDER)
    # Observed and explicitly ratified: the 2026-08-14 corpus conformance
    # scan found the det-reorder route closing 2 Normalize Commutative
    # Chains micros (a commutative-chain rewrite with the abstract-call
    # sequence identical — the plumbing-rewrite shape, EC-checked). One
    # explicit registration per R3, never fallthrough.
    add("Normalize Commutative Chains", ENTRY_DET_REORDER)
    # Multi-oracle leg moves (the universal sim/swap entries are handled
    # by ``is_registered`` via UNIVERSAL_ENTRIES, not per-name rows).
    for name in FIELD_SET_TRANSFORMS:
        add(name, ENTRY_SURVIVOR_PEEL)
    add("Hoist Deterministic Call to Initialize", ENTRY_HOIST_PAIR)
    return {name: frozenset(entries) for name, entries in reg.items()}


TACTIC_REGISTRY: dict[str, frozenset[str]] = _build_registry()


def is_registered(transform_name: str, entry_id: str) -> bool:
    """True iff ``entry_id`` is registered for ``transform_name``.

    The universal entries (see :data:`UNIVERSAL_ENTRIES`) are registered
    for every transform by policy — the bystander rule — so they are
    accepted for any name.
    """
    if entry_id in UNIVERSAL_ENTRIES:
        return True
    return entry_id in TACTIC_REGISTRY.get(transform_name, frozenset())


def registered_transforms() -> frozenset[str]:
    """Transforms with at least one registered synthesizing entry."""
    return frozenset(TACTIC_REGISTRY)


def is_conforming_tag(rung: str, transform: str | None, entry: str | None) -> bool:
    """Decide whether one emitted resolution tag conforms.

    ``synth-*`` closures need a registered ``(transform, entry)`` pair;
    ``cached-*`` and ``admit-*`` need the transform attribute only (the
    cache is transform-keyed by construction; an admit closes nothing).
    Tags on non-micro bodies (hop lemmas, bridges) are outside this
    predicate's scope — the conformance test selects which tags it
    applies to.
    """
    if rung in (CACHED_GUIDED, CACHED_UNGUIDED, ADMIT_GUIDED, ADMIT_UNGUIDED):
        return transform is not None
    if transform is None or entry is None:
        return False
    return is_registered(transform, entry)
