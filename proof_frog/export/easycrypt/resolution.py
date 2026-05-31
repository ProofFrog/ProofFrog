"""The automation ladder: how each transform/hop resolution was closed.

A single ranked scale (best-automated first) measuring *how much of the
proof is attributable to the exporter's own machinery* for one resolved
transform application or whole-hop body:

1. ``synth-static``    -- a fixed canned tactic; no per-instance logic.
2. ``synth-param``     -- the tactic is computed from the hop's structure
                          (swap counts, a synthesized cascade); still fully
                          automatic, no human and no cache.
3. ``cached-guided``   -- closed from a sidecar entry that the exporter
                          *scaffolded*: it recognized the hop class and
                          emitted a fill template (the ``STRATEGY``/``TO
                          CACHE`` guided admit) that a human filled and we
                          stored. The exporter understands the shape.
4. ``cached-unguided`` -- closed from a sidecar entry the exporter did
                          *not* scaffold: a human derived the tactic from
                          scratch and we merely captured the result.
5. ``admit-guided``    -- an open ``admit.``, but the exporter emitted a
                          targeted fill template for this exact hop (the
                          unfilled form of ``cached-guided`` -- cheap to
                          promote).
6. ``admit-unguided``  -- an open ``admit.`` with no scaffolding.

A seventh, proof-level state -- ``blocked`` -- sits below the ladder: the
proof exports to ``.ec`` text but the result does not EasyCrypt-compile (a
structural gap upstream of hop resolution, e.g. a primary-scheme
``requires``-equality mismatch). It is *not* a per-resolution tag because
the exporter cannot detect non-compilation on its own; the dashboard
carries it as a maintained list.

The descent is monotone in one quantity -- the fraction of the proof the
exporter accounts for: fixed > computed > scaffolded-and-filled >
captured-from-scratch > scaffolded-but-open > open. The two sub-splits
(static-vs-parametric within Synthesized, guided-vs-unguided within
Cached/Admit) never compete because they live in different closure bands,
which is why this is one ladder rather than two axes.

Each resolved body is prefixed with a machine-readable
``(* resolution: <token> *)`` comment (see :func:`tag`) so the dashboard
can tally the ladder exactly rather than infer it from admit-counting.
"""

from __future__ import annotations

import re

SYNTH_STATIC = "synth-static"
SYNTH_PARAM = "synth-param"
CACHED_GUIDED = "cached-guided"
CACHED_UNGUIDED = "cached-unguided"
ADMIT_GUIDED = "admit-guided"
ADMIT_UNGUIDED = "admit-unguided"
BLOCKED = "blocked"

# The per-resolution ladder, best-automated first. ``BLOCKED`` is a
# proof-level state, not a per-resolution tag, so it is excluded here.
LADDER = [
    SYNTH_STATIC,
    SYNTH_PARAM,
    CACHED_GUIDED,
    CACHED_UNGUIDED,
    ADMIT_GUIDED,
    ADMIT_UNGUIDED,
]

# Rungs counted as "automated" (no open hole): Synthesized + Cached.
AUTOMATED = {SYNTH_STATIC, SYNTH_PARAM, CACHED_GUIDED, CACHED_UNGUIDED}

# Human-readable labels for the dashboard / docs.
DISPLAY = {
    SYNTH_STATIC: "Synthesized - static",
    SYNTH_PARAM: "Synthesized - parametric",
    CACHED_GUIDED: "Cached - with guidance",
    CACHED_UNGUIDED: "Cached - without guidance",
    ADMIT_GUIDED: "Admit - with guidance",
    ADMIT_UNGUIDED: "Admit - without guidance",
    BLOCKED: "Blocked - does not EC-compile",
}

TAG_RE = re.compile(r"\(\* resolution: ([\w-]+) \*\)")
"""Matches an emitted resolution tag; group 1 is the rung token."""


def tag(token: str) -> str:
    """Render the machine-readable resolution tag for one rung token."""
    return f"(* resolution: {token} *)"
