# pylint: disable=duplicate-code
"""Per-transform EasyCrypt chain emitter.

Emits one EC module per intermediate state of the engine's
canonicalization pipeline and chains them together via per-transform
``micro_*`` lemmas plus a top-level ``hop_<i>_chain`` lemma.

The chain artifacts for each interchangeability hop are emitted by
:func:`emit_chain_for_hop`, which uses the shared translators
(``TypeCollector`` / ``ModuleTranslator``) to render each flat
intermediate-state module. A small pre-pass mangles synthetic identifiers
(``E.KeyGen@k0``) and hoists nested module calls so the shared statement
translator can consume the canonical AST.
"""

from __future__ import annotations

import copy
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Callable, NamedTuple, cast

from ... import frog_ast
from ...transforms._base import TransformApplication
from ...transforms.algebraic import SimplifyNot
from ...visitors import (
    SearchVisitor,
    SubstitutionTransformer,
    VariableCollectionVisitor,
    Visitor,
)
from . import ec_ast
from .expr_text import paren as cc_paren
from .expr_text import split_top_args as cc_split_top_args
from . import module_translator as mt
from . import type_collector as tc
from .canonical_form import _normalize_for_ec, masked_shape
from .resolution import (
    ADMIT_GUIDED,
    ADMIT_UNGUIDED,
    CACHED_UNGUIDED,
    SYNTH_PARAM,
    SYNTH_STATIC,
)
from .resolution import TAG_RE as _RES_TAG_RE
from .resolution import tag as _res_tag
from . import tactic_registry
from .tactic_cache import TacticCache, derivation_scaffold
from .transform_buckets import PARAMETRIC_TACTIC, Bucket, classify, tactic_body

# Engine passes that are pure structural reorderings (modulo dead-code
# drops): we synthesize ``swap{1} pos delta.`` tactics from the AST diff
# instead of relying on a canned tactic body. If the diff isn't a clean
# permutation (e.g. ``Topological Sorting`` may drop dead samples — its
# DFS from the return ignores statements not transitively used by it),
# we fall back to ``admit.``.
# The transform-set gate constants live in ``tactic_registry`` (the
# declarative registry the ratified architecture requires); the local
# ``_``-prefixed names are aliases so the gate code reads unchanged.
_REORDER_TRANSFORMS = tactic_registry.REORDER_TRANSFORMS


def _with_provenance(body: list[str], transform: str, entry: str) -> list[str]:
    """Re-render a route-tagged tactic body with provenance attributes.

    Routes that build their tactic (and its leading resolution tag)
    internally do not know which transform application they are closing;
    the call site does. Rewrite the leading tag with the same rung plus
    ``transform=``/``entry=`` attributes; a body whose head is not a
    resolution tag passes through unchanged.
    """
    if body and (m := _RES_TAG_RE.fullmatch(body[0])):
        return [_res_tag(m.group(1), transform=transform, entry=entry), *body[1:]]
    return body


_TUPLE_INLINE_TRANSFORMS = tactic_registry.TUPLE_INLINE_TRANSFORMS

_PLUMBING_REWRITE_TRANSFORMS = tactic_registry.PLUMBING_REWRITE_TRANSFORMS

# Re-exported for the dashboard, which credits chain-emitter synthesis
# from this set (the bucket tables alone cannot see it).
CHAIN_EMITTER_SYNTH_TRANSFORMS = tactic_registry.CHAIN_EMITTER_SYNTH_TRANSFORMS


@dataclass
class _MicroLemma:
    name: str
    left_module: str
    right_module: str
    transform_name: str
    body: list[str]
    bucket: Bucket


# ---------------------------------------------------------------------------
# Public chain-emission API used by the unified exporter
# ---------------------------------------------------------------------------


@dataclass
class HopChainInfo:
    """Chain-of-states output for one interchangeability hop.

    ``extra_decls`` are raw EC source fragments (modules + micro-lemmas
    + a ``hop_<i>_chain`` lemma) that must be inserted into the file
    *before* the per-hop ``hop_<i>`` equiv lemma. ``tactic_body`` is the
    list of tactic lines for the ``hop_<i>`` equiv lemma's ``proof``
    block; it bridges the wrapper-module expressions to the flat
    intermediate-state modules via ``transitivity`` and discharges via
    ``apply hop_<i>_chain``.

    ``pre_override`` / ``post_override``: when present, the outer
    ``hop_<i>`` equiv lemma's precondition/postcondition are replaced
    with these strings. Used in multi-module proofs to strengthen the
    spec with ``={glob E1, glob E2, ...}`` — without this, the chain
    artifacts (whose bodies make abstract module calls) are not
    provable by ``sim`` because EC cannot relate ``glob E1`` across the
    two equiv sides.

    ``requested_keys`` lists every ``(transform_name, canonical_before,
    canonical_after)`` triple that the chain emitter consulted the
    tactic cache for during this hop — including misses. Used by
    ``cache_report.py`` to compare against the sidecar and produce the
    used / orphan / missing report.
    """

    extra_decls: list[str]
    tactic_body: list[str]
    pre_override: str | None = None
    post_override: str | None = None
    requested_keys: list[tuple[str, str, str]] = field(default_factory=list)
    # (declared module name, clone alias) pairs for which a stateless-scheme
    # reorder micro was synthesized this hop; the exporter emits the
    # statelessness foundation (``d<m>`` ops, ``Ideal`` module, ``<E>_<m>_sem``
    # axioms) for each. Empty when no such reorder fired.
    stateless_modules: set[tuple[str, str]] = field(default_factory=set)
    # (declared module name, method name) pairs for which a pure-local
    # tuple-congruence micro was synthesized this hop; the exporter emits one
    # ``<M>_<m>_eq`` per-method congruence lemma (proved by ``proc true;
    # auto``) for each, deduped across hops and placed before the chain decls.
    # Empty when no tuple-congruence micro fired.
    congruence_methods: set[tuple[str, str]] = field(default_factory=set)
    # (declared module name, EC method name) pairs for which a dead-abstract-
    # call-drop micro (``Topological Sorting`` pruning a dead scheme call) was
    # synthesized this hop; the exporter emits one ``<M>_<m>_pres`` glob-
    # preservation axiom per pair. Empty when no such drop fired.
    pres_methods: set[tuple[str, str]] = field(default_factory=set)


# pylint: disable=too-many-locals,too-many-statements,too-many-arguments,too-many-positional-arguments
def emit_chain_for_hop(
    hop_index: int,
    left_game: frog_ast.Game,
    right_game: frog_ast.Game,
    left_apps: list[TransformApplication],
    right_apps: list[TransformApplication],
    oracle_name: str,
    eq_args: str,
    types: tc.TypeCollector,
    type_of_factory: Callable[
        [dict[str, frog_ast.Type], dict[str, str]],
        Callable[[frog_ast.Expression], frog_ast.Type],
    ],
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_module_params: list[ec_ast.ModuleParam] | None = None,
    tactic_cache: TacticCache | None = None,
    sidecar_relpath: str | None = None,
    det_methods: dict[str, set[str]] | None = None,
) -> HopChainInfo:
    """Emit the per-transform chain artifacts for one interchangeability hop.

    Caller has already obtained the inlined left/right game ASTs (via
    ``engine._get_game_ast``) and run ``canonicalize_game_with_states``
    on each to get the transform-application sequences. This function
    renders the resulting EC chain: intermediate-state modules,
    micro-lemmas between adjacent states, a ``canon_bridge_<i>`` lemma
    between canonical forms (closed by ``proc; sim``), and a
    ``hop_<i>_chain`` lemma proved by ``transitivity`` over the chain.

    Each flat-state module is rendered by mangling synthetic identifiers
    (``E.KeyGen@k0`` -> ``v_E_KeyGen_k0``), hoisting nested module
    function-calls into separate statements (so the shared statement
    translator can consume them), and then translating via
    :meth:`ModuleTranslator.translate_flat_game`.

    Returns the bundle of source fragments plus the tactic body to plug
    into the surrounding ``hop_<i>`` equiv lemma in the per-hop pipeline.
    """
    left_states: list[frog_ast.Game] = [left_game] + [a.game_after for a in left_apps]
    right_states: list[frog_ast.Game] = [right_game] + [
        a.game_after for a in right_apps
    ]

    left_mods = [f"Step_{hop_index}L_state_{k}" for k in range(len(left_states))]
    right_mods = [f"Step_{hop_index}R_state_{k}" for k in range(len(right_states))]

    modules = mt.ModuleTranslator(types, type_of_factory)
    chunks: list[str] = []
    flat_params = list(flat_module_params) if flat_module_params else []
    # When the flat-state modules take parameters (multi-scheme proofs
    # with declared modules inside a section), each equiv-lemma module
    # reference instantiates the functor on the declared modules
    # (e.g. ``Step_0L_state_0(E1, E2)``).
    inst_suffix = (
        "(" + ", ".join(p.name for p in flat_params) + ")" if flat_params else ""
    )

    def mod_ref(name: str) -> str:
        return f"{name}{inst_suffix}"

    # In multi-module proofs (with declared abstract scheme modules
    # passed as functor parameters), every flat-state body contains
    # abstract calls like ``<@ E1.keygen()``. EC cannot prove
    # ``={res}`` for two such bodies from a weak precondition like
    # ``={m}`` alone — it needs ``={glob E1, glob E2, ...}`` as well.
    # We strengthen every chain-internal spec (micros, transitivity
    # steps in the chain, canon_bridge, chain lemma) AND the outer
    # ``hop_<i>`` lemma's spec so the chain composes cleanly.
    multi_module = bool(flat_params)
    if multi_module:
        glob_extras = ", " + ", ".join(f"glob {p.name}" for p in flat_params)
        # Drop any leading ``={`` and trailing ``}`` from eq_args so we
        # can splice in the glob extras. eq_args is one of ``true``
        # (no oracle params) or ``={a, b}``.
        if eq_args.endswith("}"):
            eq_args_strong = eq_args[:-1] + glob_extras + "}"
        else:
            # eq_args is ``true`` (no oracle parameters): switch to
            # ``={glob E1, ...}`` (drop the leading comma).
            eq_args_strong = "={" + glob_extras[2:] + "}"
        eq_post_strong = "={res" + glob_extras + "}"
    else:
        eq_args_strong = eq_args
        eq_post_strong = "={res}"

    for mod_name, state in zip(left_mods, left_states):
        chunks.append(
            _render_flat_state(
                modules,
                mod_name,
                state,
                external_module_types,
                method_return_types,
                flat_params,
            )
        )
    for mod_name, state in zip(right_mods, right_states):
        chunks.append(
            _render_flat_state(
                modules,
                mod_name,
                state,
                external_module_types,
                method_return_types,
                flat_params,
            )
        )

    requested_keys: list[tuple[str, str, str]] = []
    cache = tactic_cache if tactic_cache is not None else TacticCache()

    def _layer2_lookup(
        app: TransformApplication, reversed_dir: bool
    ) -> list[str] | None:
        """Cache lookup (ladder rungs 3/4): consult the sidecar tactic cache.

        Computes canonical text on (game_before, game_after) — or
        swapped for the reversed-direction right micro — and looks up
        ``(transform_name, before_text, after_text)`` in the per-proof
        :class:`TacticCache`. Records the key in ``requested_keys`` so
        the orphan reporter can later diff against the sidecar.
        """
        before_game = app.game_after if reversed_dir else app.game_before
        after_game = app.game_before if reversed_dir else app.game_after
        # Phase-4 Decision 2: the CHANGED REGION with variable names masked.
        before_text, after_text = masked_shape(
            before_game, after_game, external_module_types, method_return_types
        )
        requested_keys.append((app.transform_name, before_text, after_text))
        entry = cache.lookup(app.transform_name, before_text, after_text)
        if entry is None:
            return None
        return entry.tactic.splitlines()

    def _layer3_admit(
        app: TransformApplication, bucket: Bucket, reversed_dir: bool
    ) -> list[str]:
        """Unguided admit (ladder rung 6): ``admit.`` with a diagnostic comment.

        The comment embeds the transform name, the sidecar path, a
        ``grep`` recipe to locate the surrounding lemma by name (no
        line numbers — those would be brittle across edits), and the
        expected canonical pre/post text. A Claude session reading the
        EC file can extract everything it needs to derive a tactic and
        append a new sidecar entry.
        """
        before_game = app.game_after if reversed_dir else app.game_before
        after_game = app.game_before if reversed_dir else app.game_after
        # The SAME key the lookup uses, so the text this diagnostic tells a
        # human to paste into a sidecar is the text the next export looks up.
        before_text, after_text = masked_shape(
            before_game, after_game, external_module_types, method_return_types
        )
        sidecar_display = sidecar_relpath or "<proof_path>.tactics.toml"
        lines: list[str] = [
            "(* tactic-cache miss",
            f"   transform: {app.transform_name!r}",
            f"   bucket:    {bucket.value}",
            f"   sidecar:   {sidecar_display}",
            "   to derive: locate this lemma by name in the .ec file,",
            "              then `bash scripts/easycrypt-goals.sh <ec_file> <line>`",
            "",
            "   expected game_before:",
        ]
        for line in before_text.splitlines() or [""]:
            lines.append(f"     {line}")
        lines.append("")
        lines.append("   expected game_after:")
        for line in after_text.splitlines() or [""]:
            lines.append(f"     {line}")
        lines.append("")
        lines.append("   entry skeleton -- a derivation record is what makes an")
        lines.append("   entry trustworthy to someone who did not derive it, and")
        lines.append("   the negative control is the load-bearing field (a tactic")
        lines.append("   that merely RUNS proves nothing):")
        for line in derivation_scaffold(
            app.transform_name, before_text, after_text, sidecar_display
        ):
            lines.append(f"     {line}")
        lines.append("   *)")
        lines.append("admit.")
        return lines

    # Module-parameter signature derived from ``flat_params``: used by
    # parametric synthesizers (e.g. partial-split ``Split Uniform Samples``)
    # to emit auxiliary helper modules whose functor signatures match the
    # surrounding flat-state modules.
    if flat_params:
        module_param_sig = (
            "(" + ", ".join(f"{p.name} : {p.module_type}" for p in flat_params) + ")"
        )
    else:
        module_param_sig = ""
    module_param_args = inst_suffix

    def _tactic_for(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        app: TransformApplication,
        bucket: Bucket,
        reversed_dir: bool = False,
        helpers: list[str] | None = None,
        name_prefix: str = "",
        left_module_ref: str = "",
        right_module_ref: str = "",
        left_state: frog_ast.Game | None = None,
        right_state: frog_ast.Game | None = None,
    ) -> list[str]:
        """Resolve the tactic body for one transform application.

        In multi-module mode, abstract module calls appear in every
        flat-state body. The default canned tactics (``proc; sp; auto``,
        ``proc; auto``, ``proc; wp; auto``) assume purely deterministic
        bodies and cannot close such equivs. Replacing them with
        ``proc; sp; wp; sim.`` (paired with the strengthened pre/post
        ``={glob X1, ..., glob Xn}``) handles inline-style transforms
        whose AST diff is a deterministic substitution at the head
        (``sp``) or tail (``wp``); ``sim`` then matches the abstract
        call-prefix.

        Some transforms (notably ``Inline Single-Use Variables``) also
        reorder adjacent top-level statements as a side-effect of
        inlining. The reorder is an adjacent transposition between
        ``app.game_before`` and ``app.game_after``; we detect it and
        prepend the matching ``swap{n}`` to the canned chain.

        ``reversed_dir`` is True for the right-side ``_rev`` micros
        (``state_{k+1} ~ state_k``); the swap then applies to the
        left ``state_{k+1}`` (which has the *after* order) and uses
        the same EC ``swap{1}`` direction because the lemma's left
        side is the reordered one in either case.

        Pure-reorder transforms (``Topological Sorting``,
        ``Bubble Sort Field Assignments``, ``Stabilize Independent
        Statements``) take a separate path: they have no canned body and
        instead synthesize ``swap`` tactics from the AST diff. If the
        diff isn't a clean permutation (the engine's ``sort_block`` can
        also drop dead samples — its DFS from the return statement
        skips statements that aren't a transitive dependency of the
        return), we fall back to ``admit.`` with an explanatory comment.
        """
        # Deterministic reorder with no EC-acceptable swap (preempts every
        # swap-based route). Fires on a same-module reorder (EC rejects the
        # ``swap`` -- shared ``glob``) or, for non-tuple transforms, a cross-module
        # reorder whose right->left calls-only alignment is data-invalid (the
        # ``_synth_isuv_walk`` swap would be EC-rejected). Functionalize the det
        # calls to their ``ev_<m>`` form and route through ev-functional twin
        # modules. ``Inline Local Tuple Literal`` micros are excluded from the
        # cross-module case: their tuple-walk aligns the non-tuple side to the
        # inlined tuple side (a valid direction), so they stay byte-identical.
        if (
            left_state is not None
            and right_state is not None
            and (left_module_ref and right_module_ref)
        ):
            det_re = _apply_det_reorder(
                _try_det_reorder(
                    left_state,
                    right_state,
                    left_module_ref.split("(")[0],
                    right_module_ref.split("(")[0],
                    app.transform_name not in _TUPLE_INLINE_TRANSFORMS,
                    # A pure deterministic tuple-projection plumbing rewrite (no
                    # call reorder) routes through the twins only for the
                    # tuple-projection transforms, and only in a multi-declared-
                    # module body -- single-module proofs keep their tuple-walk /
                    # stateless route byte-identical.
                    app.transform_name in _PLUMBING_REWRITE_TRANSFORMS
                    and len(flat_params) > 1,
                )
            )
            if det_re is not None:
                return _with_provenance(
                    det_re, app.transform_name, tactic_registry.ENTRY_DET_REORDER
                )
        # Pure-reorder transforms: synthesize a ``swap`` sequence directly
        # from the AST diff. If the diff isn't a clean permutation (e.g.
        # ``Topological Sorting`` may also drop dead samples — its DFS
        # from the return statement skips statements that aren't a
        # transitive dependency of the return), fall back to admit.
        if app.transform_name in _REORDER_TRANSFORMS:
            before_hoisted = _normalize_for_ec(
                copy.deepcopy(app.game_before),
                external_module_types,
                method_return_types,
            )
            after_hoisted = _normalize_for_ec(
                copy.deepcopy(app.game_after),
                external_module_types,
                method_return_types,
            )
            swaps = _permutation_swaps(
                before_hoisted, after_hoisted, reversed_dir=reversed_dir
            )
            if swaps is not None and _swaps_align_rendered(
                swaps,
                modules,
                left_state,
                right_state,
                external_module_types,
                method_return_types,
                flat_params,
            ):
                return [
                    _res_tag(
                        SYNTH_PARAM,
                        transform=app.transform_name,
                        entry=tactic_registry.ENTRY_PERM_SWAP_SIM,
                    ),
                    "proc.",
                    *swaps,
                    "sim.",
                ]
            # The raw transform-application ASTs are normalized differently from
            # the rendered flat-state modules the micro lemma relates (the engine
            # stores a separately-canonicalized ``game_before``), so the raw-AST
            # ``_permutation_swaps`` above can miss a reorder EC actually sees
            # between the two rendered states. Recompute it from the rendered
            # modules -- but only when the reorder preserves every module's own
            # call subsequence, i.e. it is purely *cross-module* (EC ``swap`` is
            # rejected on two same-module abstract calls; those take the
            # det-functional route at the head of this function instead).
            if _reorder_cross_module_safe(left_state, right_state):
                ec_swaps = _rendered_state_swaps(
                    modules,
                    left_state,
                    right_state,
                    external_module_types,
                    method_return_types,
                    flat_params,
                )
                if ec_swaps:
                    return [
                        _res_tag(
                            SYNTH_PARAM,
                            transform=app.transform_name,
                            entry=tactic_registry.ENTRY_RENDERED_SWAP_SIM,
                        ),
                        "proc.",
                        *[f"{s}." for s in ec_swaps],
                        "sim.",
                    ]
            # Not a whole-body permutation: the reorder pass may instead have
            # dropped one or more dead, independent samples (e.g.
            # ``Topological Sorting``'s DFS prunes statements the return
            # doesn't depend on). Synthesize a one-sided lossless-sample drop.
            drop = _dead_sample_drop(
                before_hoisted, after_hoisted, types, eq_args_strong, reversed_dir
            )
            if drop is not None:
                return [
                    _res_tag(
                        SYNTH_PARAM,
                        transform=app.transform_name,
                        entry=tactic_registry.ENTRY_DEAD_SAMPLE_DROP,
                    ),
                    *drop,
                ]
            cached = _layer2_lookup(app, reversed_dir)
            if cached is not None:
                return [
                    _res_tag(CACHED_UNGUIDED, transform=app.transform_name),
                    *cached,
                ]
            return [
                _res_tag(ADMIT_UNGUIDED, transform=app.transform_name),
                *_layer3_admit(app, bucket, reversed_dir),
            ]
        # Try the parametric synthesizer first when registered — its
        # output is tuned to the specific AST and takes precedence over
        # the multi-module ``proc; sp; wp; sim.`` fallback below.
        # ``tactic_body`` would silently fall back to the static canned
        # body when the synthesizer declines (returns None), so call
        # the synthesizer directly here to distinguish "synthesized" vs
        # "fell back to static".
        synth = PARAMETRIC_TACTIC.get(app.transform_name)
        if synth is not None:

            def _render_state(mod_name: str, game: frog_ast.Game) -> str:
                # Render an auxiliary flat-state module (e.g. the partial-split
                # ``Mid``/``Aug`` intermediates) with the same functor signature
                # and body translation as the surrounding chain's state modules,
                # so a synthesizer can build a helper module from a state AST.
                return _render_flat_state(
                    modules,
                    mod_name,
                    game,
                    external_module_types,
                    method_return_types,
                    flat_params,
                )

            synthesized = synth(
                app,
                types,
                helpers=helpers,
                name_prefix=name_prefix,
                module_param_sig=module_param_sig,
                module_param_args=module_param_args,
                left_module_ref=left_module_ref,
                right_module_ref=right_module_ref,
                eq_args_strong=eq_args_strong,
                eq_post_strong=eq_post_strong,
                external_module_types=external_module_types,
                method_return_types=method_return_types,
                reversed_dir=reversed_dir,
                render_state=_render_state,
            )
            if synthesized is not None:
                # The ``Inline Single-Use Variables`` synthesizer emits a
                # lockstep ``call (_: true)`` per call; its raw-AST callee
                # guard is blind to a data-flow relabel of interchangeable
                # same-module calls (the standardization reorder it bundles).
                # When the rendered states need such a reorder, the lockstep
                # coupling leaves ``={res}`` open, so fall back to an admit and
                # let the dispatch route it through the stateless ``Ideal``
                # reorder (``_try_stateless`` -> ``_synth_stateless_reorder``).
                if (
                    app.transform_name == "Inline Single-Use Variables"
                    and _stateless_ok
                    and _needs_data_aware_reorder(left_state, right_state)
                ):
                    return [
                        _res_tag(ADMIT_UNGUIDED, transform=app.transform_name),
                        *_layer3_admit(app, bucket, reversed_dir),
                    ]
                return [
                    _res_tag(
                        SYNTH_PARAM,
                        transform=app.transform_name,
                        entry=tactic_registry.param_entry_id(app.transform_name),
                    ),
                    *synthesized,
                ]
        body = tactic_body(app.transform_name, app, types)
        if multi_module and bucket == Bucket.CANNED and body:
            # A reorder that transposes two abstract calls of the *same* single
            # declared module is not plain-``swap``-safe: the two calls share
            # ``glob`` so EC rejects the swap. Detect it (the rendered call-
            # callee subsequence changes) and fall through to an admit so the
            # stateless ``Ideal`` route (``_try_stateless``) closes it instead;
            # ``swap`` past a glob-independent sample keeps the canned path.
            if _stateless_ok and _crosses_single_module_calls(left_state, right_state):
                return [
                    _res_tag(ADMIT_UNGUIDED, transform=app.transform_name),
                    *_layer3_admit(app, bucket, reversed_dir),
                ]
            # Compare hoisted forms, not raw FrogLang ASTs: the engine's
            # ``Inline Single-Use Variables`` produces a nested call
            # expression (single statement) that the EC hoister later
            # flattens into separate ``<@`` statements. The flat form is
            # what EC actually sees, so the swap-detection must operate
            # on it.
            before_hoisted = _normalize_for_ec(
                copy.deepcopy(app.game_before),
                external_module_types,
                method_return_types,
            )
            after_hoisted = _normalize_for_ec(
                copy.deepcopy(app.game_after),
                external_module_types,
                method_return_types,
            )
            swaps = _permutation_swaps(
                before_hoisted, after_hoisted, reversed_dir=reversed_dir
            )
            if swaps is not None and swaps:
                return [
                    _res_tag(
                        SYNTH_PARAM,
                        transform=app.transform_name,
                        entry=tactic_registry.ENTRY_PERM_SWAP_SPWPSIM,
                    ),
                    "proc.",
                    *swaps,
                    "sp; wp; sim.",
                ]
            # The raw transform-application ASTs are normalized differently
            # from the rendered flat-state modules the micro lemma actually
            # relates (separately-canonicalized ``game_before``; nested
            # ``return`` only hoisted at render time). Recompute the reorder
            # from the rendered modules -- what EC sees -- so an abstract-call-
            # past-independent-sample swap (e.g. ``Inline Single-Use
            # Variables`` reordering ``E.keygen()`` past ``mPrime <$ d``) is
            # detected even when the raw-AST check above missed it.
            ec_swaps = _rendered_state_swaps(
                modules,
                left_state,
                right_state,
                external_module_types,
                method_return_types,
                flat_params,
            )
            if ec_swaps:
                return [
                    _res_tag(
                        SYNTH_PARAM,
                        transform=app.transform_name,
                        entry=tactic_registry.ENTRY_RENDERED_SWAP_SPWPSIM,
                    ),
                    "proc.",
                    *[f"{s}." for s in ec_swaps],
                    "sp; wp; sim.",
                ]
            # The swap checks above demand a whole-statement permutation, which
            # ``Inline Single-Use Variables`` defeats: it removes deterministic
            # single-use assignments, so before/after differ in statement count.
            # When the inlining also exposed an independent different-module call
            # reorder, the static ``sp; wp; sim`` below silently leaves ``={res}``
            # open. Try a calls-only alignment + bottom-up call-walker, which
            # ignores the count-differing assignments (the walker's ``wp`` absorbs
            # them) and aligns just the calls.
            if app.transform_name == "Inline Single-Use Variables" and (
                left_state is not None and right_state is not None
            ):
                isuv_walk = _synth_isuv_walk(
                    _flat_state_module(
                        modules,
                        "_isuv_probe_left",
                        left_state,
                        external_module_types,
                        method_return_types,
                        flat_params,
                    ),
                    _flat_state_module(
                        modules,
                        "_isuv_probe_right",
                        right_state,
                        external_module_types,
                        method_return_types,
                        flat_params,
                    ),
                )
                if isuv_walk is not None:
                    return _with_provenance(
                        isuv_walk,
                        app.transform_name,
                        tactic_registry.ENTRY_ISUV_WALK,
                    )
            # Generic multi-module static fallback. ``sp; wp; sim`` is right for
            # most reorder-ish CANNED micros, but a ``Symbolic Computation``
            # (or ``Normalize Commutative Chains``) micro whose two sides render
            # byte-identically -- the int args were sympy-canonicalized on both
            # sides, so the transform is an EC no-op -- makes ``sp`` strengthen
            # past the leading abstract calls in a way that leaves ``sim`` unable
            # to "infer the set of equalities". Plain ``sim`` closes the identical
            # bodies directly. ``((sp; wp; sim) || sim)`` keeps the first branch
            # for every shape that already worked and falls back to ``sim`` only
            # when ``sp; wp; sim`` *errors* -- strictly more robust (it can add a
            # closure, never remove one), mirroring the wrapper/flat bridge.
            return [
                _res_tag(
                    SYNTH_STATIC,
                    transform=app.transform_name,
                    entry=tactic_registry.ENTRY_MULTI_MODULE_STATIC,
                ),
                "proc; ((sp; wp; sim) || sim).",
            ]
        if body:
            return [
                _res_tag(
                    SYNTH_STATIC,
                    transform=app.transform_name,
                    entry=tactic_registry.ENTRY_CANNED,
                ),
                *body,
            ]
        cached = _layer2_lookup(app, reversed_dir)
        if cached is not None:
            return [_res_tag(CACHED_UNGUIDED, transform=app.transform_name), *cached]
        return [
            _res_tag(ADMIT_UNGUIDED, transform=app.transform_name),
            *_layer3_admit(app, bucket, reversed_dir),
        ]

    # Stateless-scheme reorder synthesis. When a micro that would otherwise
    # admit is a reorder of abstract calls of a single declared stateless
    # scheme, route it through the all-``Ideal`` instantiation (see
    # ``_synth_stateless_reorder``). Only supported for a single declared
    # module (the common ``declare module E`` shape).
    stateless_modules: set[tuple[str, str]] = set()
    emitted_m_modules: set[str] = set()

    # Deterministic same-module-reorder route (functional-module transitivity):
    # ``det_methods`` maps a declared module name to its set of deterministic EC
    # method names; ``_clone_of`` resolves a declared module to its clone alias
    # (the ``ev_<m>`` op prefix). ``emitted_fdet_modules`` dedups the emitted
    # ``F_left``/``F_right`` twin modules across micros.
    _det_methods = det_methods or {}
    _clone_aliases = {p.name: p.module_type.split(".")[0] for p in flat_params}
    emitted_fdet_modules: set[str] = set()

    def _det_pred(module: str, method: str) -> bool:
        return method.lower() in _det_methods.get(module, set())

    def _clone_of(module: str) -> str | None:
        return _clone_aliases.get(module)

    _stateless_ok = len(flat_params) == 1
    _sm_name = ""
    _clone_alias = ""
    _ideal_suffix = ""
    if _stateless_ok:
        _sm_name = flat_params[0].name
        _clone_alias = flat_params[0].module_type.split(".")[0]
        _ideal_suffix = f"({_clone_alias}.Ideal)"

    def _is_admit(tac: list[str]) -> bool:
        return bool(tac) and "admit-unguided" in tac[0]

    def _crosses_single_module_calls(
        left_state: frog_ast.Game | None, right_state: frog_ast.Game | None
    ) -> bool:
        """True if the rendered micro transposes two same-module abstract calls.

        For the single-declared-module case, every call is to that module, so a
        changed call-callee subsequence between the two rendered flat states
        means a call/call transposition -- not plain-``swap``-safe.
        """
        if left_state is None or right_state is None:
            return False
        left_mod = _flat_state_module(
            modules,
            "_call_probe_left",
            left_state,
            external_module_types,
            method_return_types,
            flat_params,
        )
        right_mod = _flat_state_module(
            modules,
            "_call_probe_right",
            right_state,
            external_module_types,
            method_return_types,
            flat_params,
        )
        if not left_mod.procs or not right_mod.procs:
            return False
        return _ec_call_callees(left_mod.procs[0].body) != _ec_call_callees(
            right_mod.procs[0].body
        )

    def _reorder_cross_module_safe(
        left_state: frog_ast.Game | None, right_state: frog_ast.Game | None
    ) -> bool:
        """True if the rendered reorder is a same-multiset, purely *cross-module*
        call permutation -- every declared module's own call subsequence is
        identical on both sides, so the reorder only transposes calls of
        *different* modules (independent ``glob``s), which EC ``swap`` accepts.

        A same-module call transposition shares ``glob`` and is rejected by EC's
        ``swap``; it takes the det-functional-twin route at the head of
        :func:`_tactic_for` instead, so this guard keeps the rendered-swap
        fallback from emitting an EC-invalid ``swap``.
        """
        if left_state is None or right_state is None:
            return False
        left_mod = _flat_state_module(
            modules,
            "_xmod_probe_left",
            left_state,
            external_module_types,
            method_return_types,
            flat_params,
        )
        right_mod = _flat_state_module(
            modules,
            "_xmod_probe_right",
            right_state,
            external_module_types,
            method_return_types,
            flat_params,
        )
        if not left_mod.procs or not right_mod.procs:
            return False
        lc = _ec_call_callees(left_mod.procs[0].body)
        rc = _ec_call_callees(right_mod.procs[0].body)
        if sorted(lc) != sorted(rc):
            return False
        for mod in {c.split(".")[0] for c in lc if "." in c}:
            if [c for c in lc if c.startswith(mod + ".")] != [
                c for c in rc if c.startswith(mod + ".")
            ]:
                return False
        return True

    def _needs_data_aware_reorder(
        left_state: frog_ast.Game | None, right_state: frog_ast.Game | None
    ) -> bool:
        """True if the rendered micro needs a *data-aware* call reorder/relabel.

        A lockstep parametric/canned tactic (``call (_: true)`` / ``sp; wp;
        sim``) couples the two sides' abstract calls position-by-position. When
        the rendered before/after bodies share a callee subsequence but are a
        data-flow *permutation* (e.g. two ``E.enc`` whose message args are
        transposed, so the surviving result moves position), that lockstep
        coupling cannot prove ``={res}`` -- the micro must route through the
        stateless ``Ideal`` reorder instead. ``_ec_perm_swaps`` (callee-only)
        is blind to this relabel; ``_ec_reorder_swaps`` (data-aware) catches it.
        """
        if left_state is None or right_state is None:
            return False
        left_mod = _flat_state_module(
            modules,
            "_reorder_probe_left",
            left_state,
            external_module_types,
            method_return_types,
            flat_params,
        )
        right_mod = _flat_state_module(
            modules,
            "_reorder_probe_right",
            right_state,
            external_module_types,
            method_return_types,
            flat_params,
        )
        if not left_mod.procs or not right_mod.procs:
            return False
        m_body, _ = _ec_tuple_inline(left_mod.procs[0].body)
        return bool(_ec_reorder_swaps(m_body, right_mod.procs[0].body))

    def _try_stateless(
        app: TransformApplication,
        state_before: frog_ast.Game,
        state_after: frog_ast.Game,
        name_before: str,
        name_after: str,
        reversed_dir: bool,
    ) -> _StatelessSynth | None:
        if not _stateless_ok:
            return None
        before_module = _flat_state_module(
            modules,
            name_before,
            state_before,
            external_module_types,
            method_return_types,
            flat_params,
        )
        after_module = _flat_state_module(
            modules,
            name_after,
            state_after,
            external_module_types,
            method_return_types,
            flat_params,
        )
        # The tuple-inline route always qualifies (the local tuple is dropped
        # and its projections rewritten -- ``Inline Local Tuple Literal`` and
        # its expansion sibling ``Expand Tuples``). Otherwise (e.g. ``Inline
        # Single-Use Variables`` regrouping ``keygen``/``enc``) route through
        # ``Ideal`` only when the micro reorders abstract calls of the single
        # declared module -- a plain ``swap`` is unsound there (the calls share
        # ``glob``), so the canned path's swap would be EC-rejected.
        if app.transform_name not in _TUPLE_INLINE_TRANSFORMS:
            if not before_module.procs or not after_module.procs:
                return None
            if _ec_call_callees(before_module.procs[0].body) == _ec_call_callees(
                after_module.procs[0].body
            ):
                # Same callee subsequence: route to ``Ideal`` only when a
                # *data-aware* reorder (a relabel of interchangeable same-callee
                # results) is still needed; otherwise keep the canned path.
                m_body, _ = _ec_tuple_inline(before_module.procs[0].body)
                if not _ec_reorder_swaps(m_body, after_module.procs[0].body):
                    return None
        return _synth_stateless_reorder(
            before_module,
            after_module,
            name_before,
            name_after,
            _ideal_suffix,
            _sm_name,
            _clone_alias,
            oracle_name,
            eq_args_strong,
            eq_post_strong,
            reversed_dir,
        )

    def _apply_stateless(syn: _StatelessSynth | None) -> list[str] | None:
        if syn is None:
            return None
        stateless_modules.add(syn.request)
        if (
            syn.module_text
            and syn.module_name is not None
            and syn.module_name not in emitted_m_modules
        ):
            chunks.append(syn.module_text)
            emitted_m_modules.add(syn.module_name)
        return syn.tactic

    # Pure-local tuple-congruence synthesis (the multi-module analogue of the
    # single-module stateless route): when an ``Inline Local Tuple Literal``
    # micro that would otherwise admit is the pure-local-tuple shape, close it
    # name-independently with per-method congruence lemmas. Tried only after the
    # stateless route declines, so single-declared-module behavior is unchanged.
    congruence_methods: set[tuple[str, str]] = set()
    _declared_names = {p.name for p in flat_params}

    def _try_congruence(
        app: TransformApplication,
        state_before: frog_ast.Game,
        state_after: frog_ast.Game,
        name_before: str,
        name_after: str,
        reversed_dir: bool,
    ) -> _CongruenceSynth | None:
        if app.transform_name != "Inline Local Tuple Literal":
            return None
        tuple_module = _flat_state_module(
            modules,
            name_before,
            state_before,
            external_module_types,
            method_return_types,
            flat_params,
        )
        other_module = _flat_state_module(
            modules,
            name_after,
            state_after,
            external_module_types,
            method_return_types,
            flat_params,
        )
        return _synth_tuple_congruence(
            tuple_module, other_module, _declared_names, reversed_dir
        )

    def _apply_congruence(syn: _CongruenceSynth | None) -> list[str] | None:
        if syn is None:
            return None
        congruence_methods.update(syn.methods)
        return syn.tactic

    # Dead-abstract-call-drop synthesis: a ``Topological Sorting`` (or sibling
    # reorder) micro that prunes dead abstract scheme calls closes one-sided via
    # ``<M>_<m>_pres`` glob-preservation axioms. Tried only after the other
    # synthesizers decline.
    pres_methods: set[tuple[str, str]] = set()

    def _try_dead_call_drop(
        app: TransformApplication,
        state_before: frog_ast.Game,
        state_after: frog_ast.Game,
        name_before: str,
        name_after: str,
        reversed_dir: bool,
    ) -> _DeadCallDrop | None:
        if app.transform_name not in _REORDER_TRANSFORMS:
            return None
        before_module = _flat_state_module(
            modules,
            name_before,
            state_before,
            external_module_types,
            method_return_types,
            flat_params,
        )
        after_module = _flat_state_module(
            modules,
            name_after,
            state_after,
            external_module_types,
            method_return_types,
            flat_params,
        )
        return _synth_dead_call_drop(
            before_module, after_module, _declared_names, eq_args_strong, reversed_dir
        )

    def _apply_dead_call_drop(syn: _DeadCallDrop | None) -> list[str] | None:
        if syn is None:
            return None
        pres_methods.update(syn.methods)
        return syn.tactic

    # Entangled-tuple call-walker (the projection-only-in-glue shape the
    # congruence route declines). No emitted helpers; tried after congruence so
    # the multi-module pure-local case still routes through congruence.
    def _try_tuple_walk(
        app: TransformApplication,
        state_before: frog_ast.Game,
        state_after: frog_ast.Game,
        name_before: str,
        name_after: str,
        reversed_dir: bool,
    ) -> list[str] | None:
        if app.transform_name not in _TUPLE_INLINE_TRANSFORMS:
            return None
        tuple_module = _flat_state_module(
            modules,
            name_before,
            state_before,
            external_module_types,
            method_return_types,
            flat_params,
        )
        other_module = _flat_state_module(
            modules,
            name_after,
            state_after,
            external_module_types,
            method_return_types,
            flat_params,
        )
        # The tuple side (``state_before``) is the lemma's left when forward and
        # its right when reversed; the non-tuple ``other`` side is the opposite,
        # and that is where the alignment swaps must land.
        other_side = 1 if reversed_dir else 2
        return _synth_tuple_walk(tuple_module, other_module, other_side)

    # Deterministic same-module-reorder route. Any reorder transform (``Inline
    # Single-Use Variables``, ``Inline Local Tuple Literal``, ``Topological
    # Sorting``, ``Stabilize Independent Statements``, ...) can sink a
    # deterministic abstract call past another call of the SAME declared module;
    # EC rejects ``swap`` on two same-``glob`` calls, so the swap-based routes
    # (``_permutation_swaps`` / ``_synth_isuv_walk`` / ``_synth_tuple_walk``)
    # emit an EC-rejected ``swap``. Functionalize the det calls (``ev_<m>`` via
    # ``<M>_<m>_det``) and route ``left ~ right`` through ev-functional F-twin
    # modules. Tried at the head of ``_tactic_for`` so it preempts every swap
    # route uniformly; its gate (:func:`_has_same_module_det_reorder`) declines
    # on cross-module-only reorders and non-reorders, leaving those byte-identical.
    def _try_det_reorder(
        state_left: frog_ast.Game,
        state_right: frog_ast.Game,
        name_left: str,
        name_right: str,
        allow_cross_module: bool,
        allow_plumbing: bool = False,
    ) -> _DetReorderSynth | None:
        left_mod = _flat_state_module(
            modules,
            name_left,
            state_left,
            external_module_types,
            method_return_types,
            flat_params,
        )
        right_mod = _flat_state_module(
            modules,
            name_right,
            state_right,
            external_module_types,
            method_return_types,
            flat_params,
        )
        return _synth_det_reorder(
            left_mod,
            right_mod,
            name_left,
            name_right,
            inst_suffix,
            oracle_name,
            eq_args_strong,
            eq_post_strong,
            _det_pred,
            _clone_of,
            allow_cross_module,
            allow_plumbing,
        )

    def _apply_det_reorder(syn: _DetReorderSynth | None) -> list[str] | None:
        if syn is None:
            return None
        for m_name, m_text in zip(syn.module_names, syn.module_texts):
            if m_name not in emitted_fdet_modules:
                chunks.append(m_text)
                emitted_fdet_modules.add(m_name)
        return syn.tactic

    # Deduplicate-deterministic-calls finisher (``<M>_<m>_det`` axiom). No
    # emitted helpers (the det axioms are always present for declared modules).
    def _try_dedup_det(
        app: TransformApplication,
        state_before: frog_ast.Game,
        state_after: frog_ast.Game,
        name_before: str,
        name_after: str,
        reversed_dir: bool,
    ) -> list[str] | None:
        if app.transform_name != "Deduplicate Deterministic Calls":
            return None
        before_module = _flat_state_module(
            modules,
            name_before,
            state_before,
            external_module_types,
            method_return_types,
            flat_params,
        )
        after_module = _flat_state_module(
            modules,
            name_after,
            state_after,
            external_module_types,
            method_return_types,
            flat_params,
        )
        return _synth_dedup_det(
            before_module, after_module, _declared_names, reversed_dir
        )

    micros_left: list[_MicroLemma] = []
    for k, app in enumerate(left_apps):
        bucket = classify(app.transform_name)
        micro_name = f"micro_{hop_index}_left_{k}"
        helpers: list[str] = []
        left_ref = mod_ref(left_mods[k])
        right_ref = mod_ref(left_mods[k + 1])
        _key_mark = len(requested_keys)
        body = _tactic_for(
            app,
            bucket,
            helpers=helpers,
            name_prefix=micro_name,
            left_module_ref=left_ref,
            right_module_ref=right_ref,
            left_state=left_states[k],
            right_state=left_states[k + 1],
        )
        if _is_admit(body):
            synth = (
                _apply_stateless(
                    _try_stateless(
                        app,
                        left_states[k],
                        left_states[k + 1],
                        left_mods[k],
                        left_mods[k + 1],
                        reversed_dir=False,
                    )
                )
                or _apply_congruence(
                    _try_congruence(
                        app,
                        left_states[k],
                        left_states[k + 1],
                        left_mods[k],
                        left_mods[k + 1],
                        reversed_dir=False,
                    )
                )
                or _apply_dead_call_drop(
                    _try_dead_call_drop(
                        app,
                        left_states[k],
                        left_states[k + 1],
                        left_mods[k],
                        left_mods[k + 1],
                        reversed_dir=False,
                    )
                )
                or _try_tuple_walk(
                    app,
                    left_states[k],
                    left_states[k + 1],
                    left_mods[k],
                    left_mods[k + 1],
                    reversed_dir=False,
                )
                or _try_dedup_det(
                    app,
                    left_states[k],
                    left_states[k + 1],
                    left_mods[k],
                    left_mods[k + 1],
                    reversed_dir=False,
                )
            )
            if synth is not None:
                body = synth
                # Drop the cache miss this micro recorded before synthesis won.
                del requested_keys[_key_mark:]
        for h in helpers:
            chunks.append(h)
        micro = _MicroLemma(
            name=micro_name,
            left_module=left_ref,
            right_module=right_ref,
            transform_name=app.transform_name,
            body=body,
            bucket=bucket,
        )
        micros_left.append(micro)
        chunks.append(
            "\n".join(
                _render_micro_lemma(micro, oracle_name, eq_args_strong, eq_post_strong)
            )
        )

    micros_right_rev: list[_MicroLemma] = []
    for k, app in enumerate(right_apps):
        bucket = classify(app.transform_name)
        fwd_name = f"micro_{hop_index}_right_{k}_fwd"
        rev_name = f"micro_{hop_index}_right_{k}_rev"
        right_left_ref = mod_ref(right_mods[k])
        right_right_ref = mod_ref(right_mods[k + 1])
        helpers_fwd: list[str] = []
        helpers_rev: list[str] = []
        _key_mark = len(requested_keys)
        fwd_body = _tactic_for(
            app,
            bucket,
            reversed_dir=False,
            helpers=helpers_fwd,
            name_prefix=fwd_name,
            left_module_ref=right_left_ref,
            right_module_ref=right_right_ref,
            left_state=right_states[k],
            right_state=right_states[k + 1],
        )
        if _is_admit(fwd_body):
            synth = (
                _apply_stateless(
                    _try_stateless(
                        app,
                        right_states[k],
                        right_states[k + 1],
                        right_mods[k],
                        right_mods[k + 1],
                        reversed_dir=False,
                    )
                )
                or _apply_congruence(
                    _try_congruence(
                        app,
                        right_states[k],
                        right_states[k + 1],
                        right_mods[k],
                        right_mods[k + 1],
                        reversed_dir=False,
                    )
                )
                or _apply_dead_call_drop(
                    _try_dead_call_drop(
                        app,
                        right_states[k],
                        right_states[k + 1],
                        right_mods[k],
                        right_mods[k + 1],
                        reversed_dir=False,
                    )
                )
                or _try_tuple_walk(
                    app,
                    right_states[k],
                    right_states[k + 1],
                    right_mods[k],
                    right_mods[k + 1],
                    reversed_dir=False,
                )
                or _try_dedup_det(
                    app,
                    right_states[k],
                    right_states[k + 1],
                    right_mods[k],
                    right_mods[k + 1],
                    reversed_dir=False,
                )
            )
            if synth is not None:
                fwd_body = synth
                del requested_keys[_key_mark:]
        _key_mark = len(requested_keys)
        rev_body = _tactic_for(
            app,
            bucket,
            reversed_dir=True,
            helpers=helpers_rev,
            name_prefix=rev_name,
            left_module_ref=right_right_ref,
            right_module_ref=right_left_ref,
            left_state=right_states[k + 1],
            right_state=right_states[k],
        )
        if _is_admit(rev_body):
            synth = (
                _apply_stateless(
                    _try_stateless(
                        app,
                        right_states[k],
                        right_states[k + 1],
                        right_mods[k],
                        right_mods[k + 1],
                        reversed_dir=True,
                    )
                )
                or _apply_congruence(
                    _try_congruence(
                        app,
                        right_states[k],
                        right_states[k + 1],
                        right_mods[k],
                        right_mods[k + 1],
                        reversed_dir=True,
                    )
                )
                or _apply_dead_call_drop(
                    _try_dead_call_drop(
                        app,
                        right_states[k],
                        right_states[k + 1],
                        right_mods[k],
                        right_mods[k + 1],
                        reversed_dir=True,
                    )
                )
                or _try_tuple_walk(
                    app,
                    right_states[k],
                    right_states[k + 1],
                    right_mods[k],
                    right_mods[k + 1],
                    reversed_dir=True,
                )
                or _try_dedup_det(
                    app,
                    right_states[k],
                    right_states[k + 1],
                    right_mods[k],
                    right_mods[k + 1],
                    reversed_dir=True,
                )
            )
            if synth is not None:
                rev_body = synth
                del requested_keys[_key_mark:]
        for h in helpers_fwd:
            chunks.append(h)
        fwd = _MicroLemma(
            name=fwd_name,
            left_module=right_left_ref,
            right_module=right_right_ref,
            transform_name=app.transform_name,
            body=fwd_body,
            bucket=bucket,
        )
        for h in helpers_rev:
            chunks.append(h)
        rev = _MicroLemma(
            name=rev_name,
            left_module=right_right_ref,
            right_module=right_left_ref,
            transform_name=app.transform_name + " (reversed)",
            body=rev_body,
            bucket=bucket,
        )
        micros_right_rev.append(rev)
        chunks.append(
            "\n".join(
                _render_micro_lemma(fwd, oracle_name, eq_args_strong, eq_post_strong)
            )
        )
        chunks.append(
            "\n".join(
                _render_micro_lemma(rev, oracle_name, eq_args_strong, eq_post_strong)
            )
        )

    bridge_name = f"canon_bridge_{hop_index}"
    chunks.append(
        "\n".join(
            _render_lemma_block(
                bridge_name,
                mod_ref(left_mods[-1]),
                mod_ref(right_mods[-1]),
                oracle_name,
                eq_args_strong,
                ["proc; sim."],
                postcondition=eq_post_strong,
            )
        )
    )

    chain_lemma_name = f"hop_{hop_index}_chain"
    chain_body = _render_chain_body(
        [mod_ref(n) for n in left_mods],
        [mod_ref(n) for n in right_mods],
        micros_left,
        micros_right_rev,
        bridge_name,
        oracle_name,
        eq_args_strong,
        eq_post_strong,
    )
    chunks.append(
        "\n".join(
            _render_lemma_block(
                chain_lemma_name,
                mod_ref(left_mods[0]),
                mod_ref(right_mods[0]),
                oracle_name,
                eq_args_strong,
                chain_body,
                postcondition=eq_post_strong,
            )
        )
    )

    # The outer hop_<i> tactic body uses the same strengthened spec in
    # all transitivity middle-specs and as its own lemma's spec (set via
    # ``pre_override``/``post_override`` on the returned HopChainInfo).
    # Both bridge subgoals (wrapper ↔ flat-state) are within the
    # section's abstract-module scope. ``proc; inline*; sp; wp; sim``
    # closes the common shape: ``sp`` absorbs the leading parameter
    # aliases that inlining introduces (e.g. ``s0 <- s``); ``wp`` absorbs
    # the trailing ``_r0 <- <expr>; return _r0;`` shape that wrapping a
    # value-returning oracle adds; ``sim`` then matches the residual
    # symmetric call sequence. But when the wrapper/scheme round-trips a
    # value through a tuple (``rsp <- (ss, ct); ss <- rsp.`1`` straddling
    # an abstract call), ``sp``/``wp`` over-substitute the projections and
    # ``sim`` then "cannot infer the set of equalities" -- whereas plain
    # ``sim`` (which back-matches the whole symmetric body in one pass)
    # closes it. So try the ``sp; wp`` preprocessing first and fall back to
    # bare ``sim`` via ``||`` (EC alternation: the fallback runs only when
    # the first branch *errors*, so this is strictly more robust than
    # ``sp; wp; sim`` alone -- it can add closures, never remove them).
    bridge_tactic = "proc; inline *; ((sp; wp; sim) || sim)"
    tactic = [
        "(* Per-transform: bridge wrappers to flat states, chain through. *)",
        f"transitivity {mod_ref(left_mods[0])}.{oracle_name} "
        f"({eq_args_strong} ==> {eq_post_strong}) "
        f"({eq_args_strong} ==> {eq_post_strong}); "
        f"[ smt() | smt() | {bridge_tactic} |].",
        f"transitivity {mod_ref(right_mods[0])}.{oracle_name} "
        f"({eq_args_strong} ==> {eq_post_strong}) "
        f"({eq_args_strong} ==> {eq_post_strong}); "
        f"[ smt() | smt() | apply {chain_lemma_name} | {bridge_tactic} ].",
        "qed.",
    ]
    # Whole-hop suppression -- ONLY for a genuinely untranslatable
    # intermediate state. If any flat-state body translation fell back to
    # ``return witness;`` (a FrogLang construct the EC expression
    # translator doesn't yet handle), the chain cannot be composed through
    # that malformed module, so discard the chain artifacts and replace
    # the outer hop's proof body with ``admit.`` plus a structured comment
    # (ladder rung 6, ``admit-unguided``). This trigger is also partly
    # load-bearing for soundness (``_partial_split_admit`` bails here
    # rather than emit an unsound concat axiom).
    #
    # We deliberately do NOT suppress on a per-micro ``admit.``: an admit
    # micro keeps its own (admitted) lemma, and the chain's ``apply
    # micro_*`` still composes through it, so a synthesizable sibling in
    # the same hop lands as synth-param even when an unrelated micro
    # admits. The old ``has_micro_admit`` suppression masked partial
    # progress (a correctness hop is a chain of ~7 transforms; closing one
    # synthesizer left the whole hop suppressed until the LAST admit was
    # gone). Its protective job -- guarding against a 0-visible-admit file
    # EC still rejects because a *silently-failing* sibling tactic runs
    # but doesn't close its goal -- is now covered by the dashboard's real
    # EC compilation of every exported ``.ec``.
    has_stub_body = any("return witness;" in chunk for chunk in chunks)
    if has_stub_body:
        reason = (
            "at least one intermediate-state body could not be "
            "translated to EC (the engine produced a FrogLang "
            "construct the expression translator does not yet "
            "handle)"
        )
        admit_tactic = [
            _res_tag(ADMIT_UNGUIDED),
            f"(* per-transform chain unrenderable: {reason}.",
            "   Falling back to admit; the chain artifacts are omitted",
            "   from the file. *)",
            "admit.",
            "qed.",
        ]
        return HopChainInfo(
            extra_decls=[],
            tactic_body=admit_tactic,
            pre_override=eq_args_strong if multi_module else None,
            post_override=eq_post_strong if multi_module else None,
            requested_keys=requested_keys,
            # Chain discarded: the synthesized foundations are unused, so don't
            # request the (now-orphan) statelessness / congruence / pres specs.
            stateless_modules=set(),
        )
    return HopChainInfo(
        extra_decls=chunks,
        tactic_body=tactic,
        pre_override=eq_args_strong if multi_module else None,
        post_override=eq_post_strong if multi_module else None,
        requested_keys=requested_keys,
        stateless_modules=stateless_modules,
        congruence_methods=congruence_methods,
        pres_methods=pres_methods,
    )


# ---------------------------------------------------------------------------
# Multi-oracle per-oracle chain emission (P3 Part B)
#
# A multi-oracle, stateful hop (``Initialize`` lifted into the wrapper's
# ``main()``, plus one or more post-init oracles that read the state it set)
# cannot be discharged by the single-oracle ``hop_<i>`` + chain: that proves
# exactly one oracle. Instead each oracle gets its OWN per-transform chain,
# and every chain spec carries the relational state-coupling invariant
# ``(glob L){1} = (glob R){2}`` (idea 2 of the validated template
# ``tests/integration/ec_templates/multi_oracle_indist.ec``) so that the init
# oracle ESTABLISHES the coupling (pre ``true``) and each post-init oracle
# PRESERVES it.
#
# The flat-state modules (``Step_<i>{L,R}_state_k``) are full multi-oracle
# games -- emitted ONCE and shared across every oracle's chain; only the
# micro/canon_bridge/chain lemmas are oracle-suffixed (``micro_<i>_<m>_*``,
# ``canon_bridge_<i>_<m>``, ``hop_<i>_<m>_chain``).
#
# Scope (identical-state first cut, per the multi-oracle foundation plan, §3):
# each chain step's micro tactic is ``proc; sim`` when that oracle's body is
# unchanged across the step (``sim`` carries the untouched-state coupling), a
# synthesized ``proc; swap...; sim`` for a pure top-level reorder of that
# oracle's body, and otherwise the whole oracle routes to a coupling-pending
# admit. The wrapper<->flat bridge and differently-named-field correspondence
# remain the coupling-synthesis research piece (P5). Every multi-oracle proof
# in the corpus has an independent companion blocker, so this path has no
# EC-compiling target yet -- it is validated by unit tests on the emitted
# shape and lands such proofs as Blocked (automation-ladder rung 7) rather
# than crashing.
# ---------------------------------------------------------------------------


@dataclass
class MultiOracleHopChainInfo:
    """Per-oracle chain output for one multi-oracle interchangeability hop.

    ``extra_decls`` are the shared flat-state modules (emitted ONCE) followed
    by every per-oracle chain artifact. ``tactic_body_by_oracle`` maps each
    oracle name to the tactic body for that oracle's outer ``hop_<i>_<m>``
    equiv lemma; Part A's :func:`proof_translator._multi_oracle_hop_lemmas`
    declares those lemmas (names, coupling pre/post) and this supplies their
    bodies via the ``oracle_body_for_hop`` callback. An oracle absent from the
    dict (callback returned its body as ``None``) is skipped by Part A.
    """

    extra_decls: list[str]
    tactic_body_by_oracle: dict[str, list[str]]
    pres_methods: set[tuple[str, str]] = field(default_factory=set)
    # (module, method) joint-injectivity axioms the challenge case-split route
    # requests (mirrors ``pres_methods``); consumed by ``inj_method_requests``.
    inj_methods: set[tuple[str, str]] = field(default_factory=set)
    # (module, method, bitstring type, clone alias) for an injective ENDO-map
    # whose BIJECTIVITY the KDF-key-substitution route needs. Implies the
    # matching ``inj_methods`` entry; consumed by ``bij_method_requests``, which
    # DERIVES the bijectivity rather than assuming it.
    bij_methods: set[tuple[str, str, str, str]] = field(default_factory=set)
    # Concrete scheme names whose ``<Scheme>_decaps_val`` phoare lemma the
    # challenge route references; the exporter synthesizes them into section
    # scope from the scheme's translated ``decaps`` proc.
    decaps_val_schemes: set[str] = field(default_factory=set)
    # Section-level aux lemma text (``slice4_first`` + ``kdf_col_ss``) the seedbased
    # WRAPPER challenge route emits; the exporter splices these lemmas in ahead of
    # the hop lemmas (after the slice/inj axioms they depend on).
    aux_lemmas: list[str] = field(default_factory=list)
    # Modules the chain INTERPOSES that hold state of their own (a reprogramming
    # twin). The adversary and every abstract scheme must be write-separated
    # from them, exactly as from a helper game -- otherwise EC concludes
    # "module <NG> can write <Twin>.<field>". Reported explicitly rather than
    # scraped from ``extra_decls``: those also carry the per-hop flat-state
    # modules, which are NOT state holders in this sense, and registering them
    # rewrites the restriction lists of nearly every export.
    state_modules: set[str] = field(default_factory=set)


def _glob_coupling(left_ref: str, right_ref: str) -> str:
    """``(glob L){1} = (glob R){2}`` -- the identical-state coupling invariant.

    Matches :func:`proof_translator.coupling_invariant`; duplicated here to
    keep ``chain_emitter`` free of a proof-translator import.
    """
    return f"(glob {left_ref})" "{1}" f" = (glob {right_ref})" "{2}"


# A coupling builder: ``(left_ref, right_ref) -> relational-invariant string``.
# ``_glob_coupling`` is the identical-state default; the chain emitter passes a
# field-aware closure (:func:`_field_aware_coupling`) for hops whose two sides
# have structurally different module state (wall 4).
CouplingFn = Callable[[str, str], str]


def _ref_base(ref: str) -> str:
    """Base module name of a functor-applied ref: ``Step_0R_state_5(K)`` -> ``Step_0R_state_5``."""
    return ref.split("(", 1)[0].strip()


def _top_level_args(module_expr: str) -> list[str]:
    """Top-level argument expressions of a functor application.

    ``R(K, K_c.LEAK_BIND_K_CT_Breakable(K))`` -> ``["K",
    "K_c.LEAK_BIND_K_CT_Breakable(K)"]``. Splits on top-level commas inside the
    outermost parentheses, respecting nesting; returns ``[]`` when the expression
    has no argument list.
    """
    open_idx = module_expr.find("(")
    if open_idx == -1:
        return []
    depth = 0
    inner = ""
    for ch in module_expr[open_idx:]:
        if ch == "(":
            depth += 1
            if depth == 1:
                continue
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        inner += ch
    args: list[str] = []
    depth = 0
    cur = ""
    for ch in inner:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def _ec_module_fields(game: frog_ast.Game) -> list[str]:
    """Module-level EC ``glob`` field names of a flat-state game, in order.

    Mirrors :meth:`ModuleTranslator.translate_flat_game`'s field emission
    (``emit_state_vars``): each game-level field becomes one module-level ``var``,
    under the same ``_ec_field_name`` lowercasing.
    """
    # pylint: disable=protected-access
    return [mt._ec_field_name(f.name) for f in game.fields]


def _glob_signature(
    module_text: str, param_names: list[str]
) -> tuple[tuple[tuple[str, str], ...], frozenset[str]]:
    """EC ``glob`` signature of a rendered flat-state module: the exact shape
    EC compares when it typechecks ``(glob M){1} = (glob M'){2}``.

    Returns ``(fields, used_params)`` where ``fields`` is the module-var
    ``(name, type)`` list sorted by NAME (EC orders ``glob`` alphabetically), and
    ``used_params`` is the set of module parameters the body actually CALLS -- a
    param whose methods are never invoked is absent from ``(glob M)`` (EC drops
    unused functor args). Two states' whole-glob equality typechecks iff their
    signatures are identical; a param NOT in the shared used-set must not appear
    in a ``={glob P}`` coupling conjunct (it would bind a middle-memory
    existential over an abstract module glob that ``smt`` cannot witness).

    Read off the RENDERED module -- the authoritative source for EC's ``(glob)``.
    Module vars are the ``var`` lines BEFORE the first ``proc`` (proc-local vars
    come after). ``\\bP\\.`` (word boundary) not substring: ``NG.`` contains the
    substring ``G.``, so a substring probe would falsely mark ``G`` used."""
    head = module_text.split("proc ", 1)[0]
    fields = tuple(sorted(re.findall(r"var (\w+) : (.+)", head)))
    used = frozenset(
        p for p in param_names if re.search(rf"\b{re.escape(p)}\.", module_text)
    )
    return fields, used


def _chain_survivor_map(states: list[frog_ast.Game]) -> dict[str, str]:
    """Map each redundant-copy field to its surviving source, chain-wide.

    A field removed by "Remove redundant variables for fields" was redundant
    because ``initialize`` set it ``r <- s`` from a surviving field ``s`` (e.g.
    ``dk0 <- challenger_dk0``). Scanning every flat state's ``initialize`` for a
    direct field-to-field assignment recovers ``{r: s}`` -- the invariant ``r=s``
    holds in every state that still carries ``r``, so it can ride a coupling that
    relates a state-with-``r`` to a state where ``r`` was removed. Recovery is
    name-independent (read off the AST, no ``inline``-name prediction); when a
    removed field has no such recoverable survivor the coupling simply omits the
    invariant, and the affected micro fails loudly (honest gating) rather than
    admitting a false lemma.
    """
    # pylint: disable=protected-access
    survivor: dict[str, str] = {}
    for game in states:
        field_ec = {f.name: mt._ec_field_name(f.name) for f in game.fields}
        init = next(
            (m for m in game.methods if m.signature.name.lower() == "initialize"),
            None,
        )
        if init is None:
            continue
        for stmt in init.block.statements:
            if (
                isinstance(stmt, frog_ast.Assignment)
                and isinstance(stmt.var, frog_ast.Variable)
                and isinstance(stmt.value, frog_ast.Variable)
                and stmt.var.name in field_ec
                and stmt.value.name in field_ec
            ):
                survivor[field_ec[stmt.var.name]] = field_ec[stmt.value.name]
    return survivor


def _chain_role_map(
    left_states: list[frog_ast.Game],
    right_states: list[frog_ast.Game],
    survivor: dict[str, str],
) -> dict[str, str]:
    """Map each ``glob`` field name to a canonical role representative, chain-wide.

    Two field names share a *role* when they denote the same live value across the
    chain's flat states. Roles unify by two name-independent relations:

    * **survivor** (``r <- s`` in some ``initialize``): a redundant copy ``r`` has
      the same value as its source ``s`` (recovered by :func:`_chain_survivor_map`);
    * **positional rename** (an alpha-rename / canonicalization step ``dk0``->
      ``field1``): between two adjacent flat states with the SAME field count, the
      i-th field of one is the i-th field of the other -- sound by the
      canonicalizer's positional field renaming.

    The role map lets a cardinality-differing coupling relate fields that share no
    NAME (e.g. a canonical endpoint ``field1`` to the anchor's ``dk0``): they are
    the same role, so the coupling pairs them. Union-find over the field-name set;
    the returned map sends each name to its role's representative name.
    """
    # pylint: disable=protected-access
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(a: str, b: str) -> None:
        parent[find(a)] = find(b)

    def fields_of(game: frog_ast.Game) -> list[str]:
        return [mt._ec_field_name(f.name) for f in game.fields]

    for game in list(left_states) + list(right_states):
        for f in fields_of(game):
            find(f)
    for r, s in survivor.items():
        union(r, s)
    # Cross-adjacency field correspondence (a same-cardinality alpha-rename /
    # reorder step). Prefer a DATA-FLOW match -- pair two fields that each side's
    # ``initialize`` assigns from the identical source expression (``v1[1]``) -- so a
    # canonical rename that also REORDERS the field declarations (e.g. decaps keys
    # sorted before encaps keys) still corresponds fields by role, not by
    # declaration slot. A positional zip mispairs such a reorder by TYPE (an
    # EncapsKey field to a DecapsKey field -> EC "no matching operator `='": the PK
    # role-map field-type wall). Fall back to the positional zip only when the
    # data-flow match is not a complete unambiguous bijection -- so with field order
    # preserved (the common case) the two agree and every working chain is
    # byte-identical.
    for states in (left_states, right_states):
        for before, after in zip(states, states[1:]):
            fb, fa = fields_of(before), fields_of(after)
            if len(fb) != len(fa):
                continue
            pairs = _dataflow_field_pairs(before, after, fb, fa)
            for x, y in pairs if pairs is not None else zip(fb, fa):
                union(x, y)
    return {name: find(name) for name in parent}


def _init_source_map(game: frog_ast.Game) -> dict[str, str]:
    """Map each field to the string form of its defining ``initialize`` RHS.

    A data-flow fingerprint used to correspond fields across an adjacent
    same-cardinality flat-state pair: two fields that ``initialize`` assigns from
    the *same* source expression hold the same value, so they share a role even when
    a canonicalization step renamed AND reordered the field declarations (where a
    positional zip would mispair them). Keyed by the EC field name; last write wins
    (matches EC's final-value semantics). The source strings are stable across a
    field-only rename/reorder step (they name locals + projections, not the renamed
    fields), so identical strings denote identical values.
    """
    # pylint: disable=protected-access
    field_ec = {f.name: mt._ec_field_name(f.name) for f in game.fields}
    init = next(
        (m for m in game.methods if m.signature.name.lower() == "initialize"),
        None,
    )
    out: dict[str, str] = {}
    if init is None:
        return out
    for stmt in init.block.statements:
        if (
            isinstance(stmt, frog_ast.Assignment)
            and isinstance(stmt.var, frog_ast.Variable)
            and stmt.var.name in field_ec
        ):
            out[field_ec[stmt.var.name]] = str(stmt.value)
    return out


def _init_packed_components(game: frog_ast.Game) -> dict[str, list[str]]:
    """Each field whose ``initialize`` source is a TUPLE LITERAL, mapped to its
    components' source strings.

    ``ctStar <- [v1[1], v2]`` says the field HOLDS that pair, so a state that
    keeps the two components in SEPARATE fields holds the same value split in
    two -- and, because the components are named by their own source
    expressions, the two states can be related without guessing. Only a literal
    tuple counts; any other source names no components.

    Keyed by EC field name and last-write-wins, exactly like
    :func:`_init_source_map`, whose strings these are compared against. A field
    later reassigned from a non-tuple loses its entry rather than keeping a
    stale one.
    """
    # pylint: disable=protected-access
    field_ec = {f.name: mt._ec_field_name(f.name) for f in game.fields}
    init = next(
        (m for m in game.methods if m.signature.name.lower() == "initialize"),
        None,
    )
    out: dict[str, list[str]] = {}
    if init is None:
        return out
    for stmt in init.block.statements:
        if (
            isinstance(stmt, frog_ast.Assignment)
            and isinstance(stmt.var, frog_ast.Variable)
            and stmt.var.name in field_ec
        ):
            name = field_ec[stmt.var.name]
            if isinstance(stmt.value, frog_ast.Tuple) and len(stmt.value.values) > 1:
                out[name] = [str(v) for v in stmt.value.values]
            else:
                out.pop(name, None)
    return out


def _dataflow_field_pairs(
    before: frog_ast.Game,
    after: frog_ast.Game,
    fb: list[str],
    fa: list[str],
) -> list[tuple[str, str]] | None:
    """Correspond ``before``'s fields to ``after``'s by their ``initialize`` source.

    Returns a ``[(before_field, after_field)]`` bijection when the two states'
    field-defining source expressions form a complete, unambiguous match (every
    field on both sides is defined, its source is unique on its side, and the two
    source sets are equal); otherwise ``None`` (the caller falls back to the
    positional zip). Complete + unique guarantees the pairing is exact: identical
    source expression => identical value, so a matched pair genuinely shares a role.
    """
    sb, sa = _init_source_map(before), _init_source_map(after)
    if len(sb) != len(fb) or len(sa) != len(fa):
        return None
    if len(set(sb.values())) != len(fb) or len(set(sa.values())) != len(fa):
        return None
    if set(sb.values()) != set(sa.values()):
        return None
    by_source_after = {src: name for name, src in sa.items()}
    return [(f, by_source_after[sb[f]]) for f in fb]


def _make_field_aware_coupling(
    fields_by_base: dict[str, list[str]],
    survivor: dict[str, str],
    glob_params: list[str],
    role_of: dict[str, str] | None = None,
    qualified_ref_by_base: dict[str, dict[str, str]] | None = None,
    canonical_by_base: dict[str, dict[str, str]] | None = None,
    glob_info_by_base: (
        dict[str, tuple[tuple[tuple[str, str], ...], frozenset[str]]] | None
    ) = None,
    ro_by_arrow: dict[str, str] | None = None,
    ro_challenger_by_base: dict[str, list[tuple[str, str]]] | None = None,
    lazyro_cross: tuple[str, str, frozenset[str]] | None = None,
    type_sig_by_base: dict[str, tuple[str, ...]] | None = None,
    outer_globs: frozenset[str] | None = None,
    hoist_conjuncts: dict[str, list[str]] | None = None,
    init_source_by_base: dict[str, dict[str, str]] | None = None,
    packed_components_by_base: dict[str, dict[str, list[str]]] | None = None,
) -> CouplingFn:
    """Build a coupling closure that is field-aware for cardinality-differing states.

    When the two modules' ``glob`` field sets have the SAME cardinality (identical
    names, or a pure positional rename such as ``dk0``->``field1``), the whole-glob
    tuple equality ``(glob L){1}=(glob R){2}`` is well-typed and sound, and is
    emitted verbatim -- so every currently-clean proof (which never differs in
    cardinality) stays byte-identical. When the cardinalities DIFFER (a field was
    removed on one side), the whole-glob equality is ill-typed; the coupling is
    then synthesized field-wise:

    * **cross-side correspondence** -- pair each left field with a right field of
      the same role, preferring a same-NAME partner, else a same-ROLE partner
      (``role_of``, recovered from survivor + positional-rename relations). This is
      what lets a canonical endpoint ``field1`` couple to the anchor's ``dk0`` even
      though they share no name (the P5 rename role-correspondence).
    * **within-side survivor invariants** -- for each side, when two of that side's
      own fields share a role (a redundant copy such as ``dk0 = challenger_dk0``),
      relate the copy to its role representative. Emitted CONSISTENTLY on every
      cardinality-differing coupling in the chain (not only where a field was
      removed across the pair), so the invariant threads unbroken from the outer
      coupling through every intermediate -- otherwise ``smt`` cannot introduce it
      mid-chain at a transitivity side-condition (the composition wall).

    All conjuncts are prefixed with ``={glob <param>}`` for each abstract module
    parameter ``glob_params`` (e.g. the scheme ``K``): the field-aware coupling
    names the game state explicitly and so, unlike the whole-glob form, must carry
    the abstract module's own glob for the ``call (_: true)`` peel to couple its
    calls (validated: ``ec_templates/field_removal_coupling.ec``).

    ``qualified_ref_by_base`` handles a **composite** base -- a reduction wrapper
    ``R(K, Challenger)`` whose ``glob`` spans two modules (``R``'s own fields plus
    the inner ``Challenger``'s). Its entry maps each role-field name to the fully
    qualified ``glob`` ref (e.g. ``dk0`` -> ``R.dk0``, ``challenger_dk0`` ->
    ``Chal.dk0``), so a coupling to that wrapper relates each flat field to the
    module that actually holds it (wall 7). For a composite base the whole-glob
    shortcut is skipped even at equal cardinality: the two globs list their fields
    in different module order, so a positional whole-glob equality would mispair
    them (a false coupling). A base absent from the map qualifies as ``base.field``.
    """
    roles = role_of or {}
    qualified = qualified_ref_by_base or {}
    canonical = canonical_by_base or {}
    ginfo = glob_info_by_base or {}
    ro_arrow = ro_by_arrow or {}
    ro_challenger = ro_challenger_by_base or {}
    type_sigs = type_sig_by_base or {}
    init_src = init_source_by_base or {}
    packed_comp = packed_components_by_base or {}
    composite = set(qualified)

    def role(f: str) -> str:
        return roles.get(f, f)

    def ftype(base: str, f: str) -> str | None:
        """EC type of stable field ``f`` in ``base``, via its canonical name and
        the glob signature. ``None`` when unknown (no signature)."""
        cname = canonical.get(base, {}).get(f, f)
        for name, typ in ginfo.get(base, ((), frozenset()))[0]:
            if name == cname:
                return typ
        return None

    def qualify(base: str, f: str) -> str:
        # Role/survivor unification runs on the STABLE ``_ec_field_name`` names
        # (``dk``, ``ctStar``) -- they are consistent across a chain's states,
        # unlike the per-state canonical ``f<NN>`` var names. Map the stable
        # name to the module's actual declared var only at this final qualify
        # step: a flat state emitted with a canonical ``f<NN>`` var block (the
        # multi-oracle ``emit_state_vars`` path) declares ``base.f03``, not
        # ``base.dk``. Composite reduction wrappers keep their explicit
        # qualified ref (``R.dk0`` / ``Chal.dk0``); a base with no canonical map
        # (a reduction/challenger module using stable names) qualifies verbatim.
        if base in qualified:
            return qualified[base].get(f, f"{base}.{f}")
        return f"{base}.{canonical.get(base, {}).get(f, f)}"

    def coupling(left_ref: str, right_ref: str) -> str:
        lb, rb = _ref_base(left_ref), _ref_base(right_ref)
        fl, fr = fields_by_base.get(lb), fields_by_base.get(rb)
        is_composite = lb in composite or rb in composite
        li, ri = ginfo.get(lb), ginfo.get(rb)
        # Whole-glob `(glob L){1}=(glob R){2}` typechecks ONLY when the two
        # globs have the SAME shape. With glob signatures available (ROM), take
        # the shortcut only on an EXACT signature match (field name+type list AND
        # used-param set); a mere equal field COUNT is insufficient -- two states
        # can share a count yet differ in a field type or a used param, which EC
        # rejects with "no matching operator `='". Without signatures (binding /
        # correctness) keep the historical count test, so those stay
        # byte-identical.
        if ginfo and li is not None and ri is not None:
            same_glob = li == ri
        elif ro_arrow and ((li is None) != (ri is None)):
            # Wrapper<->flat leg with a shared RO global module: only ONE side
            # (the flat state) has a glob signature; the wrapper is registered
            # by field count alone. A shared RO holder module (``RO_H``) lands at
            # a DIFFERENT offset in the wrapper's ``glob`` (right after the scheme
            # param globs) than in the flat state's (after its own fields), so the
            # whole-glob tuple equality is ill-typed even at equal field
            # cardinality ("no matching operator `='"). Force the field-wise
            # coupling, which separates ``={glob RO_H}`` from the field pairings.
            # Validated: ``.ec-tmp/trip_glob.ec``.
            same_glob = False
        else:
            same_glob = fl is not None and fr is not None and len(fl) == len(fr)
            if same_glob and type_sigs:
                sl, sr = type_sigs.get(lb), type_sigs.get(rb)
                if sl is not None and sr is not None and sl != sr:
                    # same cardinality but a RENAMED+REORDERED field block: the
                    # glob tuples' type sequences differ, so the whole-glob
                    # equality is ill-typed -- take the field-wise coupling.
                    same_glob = False
        if fl is None or fr is None or (same_glob and not is_composite):
            return _glob_coupling(left_ref, right_ref)
        setr = set(fr)
        fields_conj: list[str] = []
        # Cross-side: same-name preferred, then same-role (declaration-order rep).
        # Reserve every same-name right partner up front so the same-role fallback
        # cannot steal a right field that a (later-in-order) same-name left field
        # owns -- otherwise a copy field and its survivor would both pair to the
        # same right field (a redundant, order-dependent conjunct).
        paired_r: set[str] = {f for f in fl if f in setr}
        for f in fl:
            if f in setr:
                fields_conj.append(
                    f"{qualify(lb, f)}" "{1}" f" = {qualify(rb, f)}" "{2}"
                )
            else:
                # Same-role fallback -- but ONLY pair fields of the SAME EC type.
                # A cardinality-differing state (redundant tuple fields shift the
                # type-rank) can put an ``f04:bs_kem_pq_nss`` in the same role as
                # an ``f01:KEMPQDecapsKeySpace``; pairing them emits an ill-typed
                # ``=`` EC rejects ("no matching operator"). A missing pairing is
                # recoverable (``sim`` frames the untouched field); a type-clash
                # pairing is a hard block. When no signature is available (binding
                # / correctness) ``ftype`` is ``None`` on both -> unchanged.
                lt = ftype(lb, f)
                g = next(
                    (
                        h
                        for h in fr
                        if h not in paired_r
                        and role(h) == role(f)
                        and ftype(rb, h) == lt
                    ),
                    None,
                )
                if g is not None:
                    fields_conj.append(
                        f"{qualify(lb, f)}" "{1}" f" = {qualify(rb, g)}" "{2}"
                    )
                    paired_r.add(g)
        # PACKED value against its COMPONENTS. A canonicalization step that
        # splits a tuple-valued field into one field per component leaves the
        # two adjacent states with no field in common for it, so neither the
        # same-name nor the same-role pairing above relates it -- and a
        # ``decaps`` that tests ``ct = ctStar`` on one side against
        # ``ct = (ctStar_0, ctStar_1)`` on the other then cannot be shown to
        # take the same branch.
        #
        # DERIVED, not matched by name or shape: the packed field's own
        # ``initialize`` source must be a literal tuple, and each of its
        # components must be the source of EXACTLY ONE field on the other side
        # (:func:`_init_packed_components` against :func:`_init_source_map`).
        # Anything short of that -- a component no field holds, a source two
        # fields share, a repeated partner, or a packed name the other side also
        # declares -- refuses, because each of those would make the choice of
        # partner a guess rather than a reading.
        for pbase, pside, cbase, cside, pfields, cfields in (
            (lb, "1", rb, "2", fl, fr),
            (rb, "2", lb, "1", fr, fl),
        ):
            for f in pfields:
                comps = packed_comp.get(pbase, {}).get(f)
                if not comps or f in cfields:
                    continue
                csrc = init_src.get(cbase, {})
                parts: list[str] = []
                for comp in comps:
                    owners = [h for h in cfields if csrc.get(h) == comp]
                    if len(owners) != 1:
                        parts = []
                        break
                    parts.append(owners[0])
                if not parts or len(set(parts)) != len(parts):
                    continue
                tup = "(" + ", ".join(qualify(cbase, g) for g in parts) + ")"
                packed_ref = f"{qualify(pbase, f)}{{{pside}}}"
                comp_ref = f"{tup}{{{cside}}}"
                fields_conj.append(
                    f"{packed_ref} = {comp_ref}"
                    if pside == "1"
                    else f"{comp_ref} = {packed_ref}"
                )
        # Within-side survivor invariants, both sides, emitted CONSISTENTLY (for
        # every field whose survivor source is also present on that side, not only
        # where a field was removed across this pair). The survivor map -- not the
        # role map -- is authoritative for "these two of a side's own fields are
        # equal copies"; role is only for the cross-side rename pairing above.
        # Consistency is what lets the invariant thread unbroken from the outer
        # coupling through every intermediate (the composition fix).
        for side, base, fields in (("1", lb, fl), ("2", rb, fr)):
            present = set(fields)
            for f in fields:
                s = survivor.get(f)
                if s is not None and s != f and s in present:
                    fields_conj.append(
                        f"{qualify(base, f)}"
                        f"{{{side}}}"
                        f" = {qualify(base, s)}"
                        f"{{{side}}}"
                    )
        # Hoist-pair cache invariants (Phase-2 Move 3c): one-sided
        # ``<base>.<h>{s} = ev_<m>(<args>{s})`` for every base registered as
        # carrying a Hoist cache field. Emitted with the same consistency
        # discipline as the survivor invariants above, which is what lets
        # the transitivity side conditions witness/thread the conjunct
        # (probe: ``.ec-tmp/move3/hoist_chain_probe.ec``). Empty registry
        # (every chain without a Hoist pair) is byte-identical.
        for side, base in (("1", lb), ("2", rb)):
            for tmpl in (hoist_conjuncts or {}).get(base, ()):
                fields_conj.append(tmpl.replace("__SIDE__", "{" + side + "}"))
        # A materialized-RO field (arrow-typed, assigned ``<- RO_H.h``) equals
        # the shared RO on its side. Emit ``base.f{side} = RO_H.h{side}`` so a hop
        # that DROPS this field and reverts to ``RO_H.h`` (the lazy-RO Honest
        # eager-RF materialization) can thread ``res`` equality. Read the field's
        # arrow TYPE off the glob signature (canonical name + type). SUPPRESSED for
        # the lazy-RO Honest hop: there the reduction-flat RO field is NOT equal to
        # any holder same-side (it is a fresh sample the flat state owns); its
        # identity threads via the same-name field pairing (reduction-flat legs) and
        # the seam cross below, so a same-side ``f{s}=holder{s}`` is a false conjunct
        # that also over-generates a transitivity existential (wall 3n-CT-b).
        if ro_arrow and lazyro_cross is None:
            for side, base in (("1", lb), ("2", rb)):
                for cname, ctype in ginfo.get(base, ((), frozenset()))[0]:
                    ro_ref = ro_arrow.get(ctype)
                    if ro_ref is not None:
                        fields_conj.append(
                            f"{base}.{cname}{{{side}}} = {ro_ref}{{{side}}}"
                        )
        # Lazy-RO Honest hop: a leg that CROSSES the game<->reduction seam couples
        # the two sides' DISTINCT RO references directly. Each base's RO ref: the
        # shared ``RO_G_RO.h`` (game side), the flat state's own arrow field
        # ``<base>.f0N`` (a reduction FLAT state), or the challenger ``<Chal>.h`` (the
        # reduction WRAPPER). Same-side legs need no cross (game legs thread via
        # ``={glob RO_G_RO}``; reduction legs via the field pairing).
        if lazyro_cross is not None:
            _shared, _chal_h, _red_bases = lazyro_cross

            def _lazy_ro_ref(b: str) -> str:
                if b not in _red_bases:
                    return _shared
                for cn, ct in ginfo.get(b, ((), frozenset()))[0]:
                    if ct in ro_arrow:
                        return f"{b}.{cn}"
                return _chal_h

            if (lb in _red_bases) != (rb in _red_bases):
                fields_conj.append(f"{_lazy_ro_ref(lb)}{{1}} = {_lazy_ro_ref(rb)}{{2}}")
        else:
            # A COMPOSITE wrapper's inner challenger holds an RO-materialized arrow
            # field (``<Challenger>.rF = RO_H.h``) that lives in the wrapper's glob
            # but NOT in the flat-state ``ginfo`` signature above, so emit it here
            # from the detected ``(qualified-ref, RO-ref)`` pairs. Threads ``RO_H.h
            # = rF`` into the wrapper<->flat transitivity precondition (the lazy-RO
            # delegating hops); byte-identical when no composite RO challenger.
            for side, base in (("1", lb), ("2", rb)):
                for chal_ref, ro_ref in ro_challenger.get(base, []):
                    fields_conj.append(f"{chal_ref}{{{side}}} = {ro_ref}{{{side}}}")
        # No relatable field across these two states (different cardinality AND
        # no shared name / recoverable role -- a cross-game correspondence we do
        # not yet resolve). Never emit a vacuous coupling (a bare ``={glob K}``
        # with no state correspondence could let ``smt()`` discharge a
        # transitivity side-condition that a real correspondence should have
        # carried -- the false-confidence trap). Fall back to the whole-glob
        # equality, which is ill-typed here and makes EC reject the file loudly
        # (honest gating -- blocked, never a false accept).
        if not fields_conj:
            return _glob_coupling(left_ref, right_ref)
        # ``={glob P}`` for EVERY declared param, used by these two states or not.
        #
        # This used to intersect the two states' used-param sets when signatures
        # were available (ROM), on the reasoning that a param absent from a
        # state's ``(glob)`` binds a middle-memory existential ``smt`` cannot
        # witness. That reasoning had the diagnosis right and the fix backwards.
        # The OUTER hop lemma coupled every declared module, so a narrowed chain
        # coupling could not discharge the transitivity's post-implication: it had
        # to produce ``={glob G}`` from two intermediate specs that never mentioned
        # ``G``. Underivable, and the resulting bare ``smt()`` failure looked
        # exactly like the one the narrowing was meant to cure.
        #
        # The existential IS witnessable -- the witness list is parsed back out of
        # these very conjuncts and sorted (see the ``functor_globs`` comment), so
        # widening here widens the witnesses in the same order. The historical
        # "mistypes the first slot" symptom was a witness the coupling never named,
        # not an unwitnessable one. Verified end to end: `hop_8_hash` of
        # `CG_seedbased_INDCCA_T` -- the entire ROM wall -- closes admit-free with
        # the param set widened at the specs, the witnesses, and the chain lemma
        # together.
        # Match the OUTER hop lemma's glob set exactly. Both a wider and a
        # narrower set are provably wrong, and each failure mode was measured:
        #   too NARROW -- the transitivity's post-implication must produce a
        #     ``={glob P}`` the intermediate specs never mention (underivable by
        #     any tactic; `CG_seedbased_INDCCA_T` `hop_8_hash`);
        #   too WIDE -- the pre-implication binds a middle-memory existential
        #     over a param the outer coupling never constrains, and `smt` cannot
        #     witness it (`CG_expanded_INDCCA_T` `hop_4_hash`, which passes at
        #     the narrower set and fails at the wider one).
        # The outer set is `live_abstract_modules + ro_holder_modules`; the two
        # CFRG `_T` families genuinely differ in it, which is why no fixed rule
        # -- intersection of used params, or all params -- can serve both.
        # Confined to the path that has per-state signatures (ROM), which is
        # where the mismatch arises and where the old intersection lived; every
        # binding / correctness proof keeps all ``glob_params`` and so stays
        # byte-identical.
        if ginfo and li is not None and ri is not None and outer_globs:
            gparams = [p for p in glob_params if p in outer_globs]
        else:
            gparams = glob_params
        # LAZY-RO Honest hop: ``={glob RO_G_RO}`` (i.e. ``RO_G_RO.h{1}=RO_G_RO.h{2}``)
        # holds ONLY between two game-side states (both read the shared RO). On any
        # leg touching a reduction-derived base the reduction reads the challenger's
        # fresh RO, never the shared one, so ``={glob RO_G_RO}`` is either false (the
        # seam) or unthreadable baggage (reduction<->reduction: the outer coupling
        # carries no RO_G_RO equality to compose it through). Drop it there; the RO
        # identity threads via the seam cross and the reduction field pairing.
        # Dropping only the conjunct -- not the param from the signature -- avoids
        # perturbing the ``same_glob`` shortcut (a whole-glob equality on mismatched
        # states is a type error).
        if lazyro_cross is not None:
            _shared, _chal_h, _red_bases = lazyro_cross
            if (lb in _red_bases) or (rb in _red_bases):
                ro_holder = _shared.rsplit(".", 1)[0]
                gparams = [p for p in gparams if p != ro_holder]
        return " /\\ ".join([f"={{glob {p}}}" for p in gparams] + fields_conj)

    return coupling


def _coupling_spec(
    left_ref: str,
    right_ref: str,
    is_init: bool,
    eq_args: str,
    coupling: CouplingFn = _glob_coupling,
) -> str:
    """``(<pre> ==> ={res} /\\ <coupling>)`` for a transitivity middle-spec.

    The init oracle establishes the coupling from ``true``; a post-init oracle
    additionally requires its argument equality (``eq_args``) in the
    precondition. ``coupling`` defaults to the identical-state ``_glob_coupling``;
    the chain emitter supplies a field-aware closure for non-identical-state hops.
    """
    cpl = coupling(left_ref, right_ref)
    if is_init:
        pre = "true"
    else:
        pre = cpl if eq_args == "true" else f"{eq_args} /\\ {cpl}"
    return f"({pre} ==> ={{res}} /\\ {cpl})"


_MICRO_FIELD_PAIR_RE = re.compile(
    r"([A-Za-z_][A-Za-z0-9_.']*)\.([A-Za-z_][A-Za-z0-9_']*)\{1\}"
    r"\s*=\s*"
    r"([A-Za-z_][A-Za-z0-9_.']*)\.([A-Za-z_][A-Za-z0-9_']*)\{2\}"
)


def _split_conjuncts(text: str) -> list[str]:
    """Split a rendered pRHL formula on its TOP-LEVEL ``/\\``."""
    out: list[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and text.startswith("/\\", i):
            out.append(text[start:i].strip())
            i += 2
            start = i
            continue
        i += 1
    out.append(text[start:].strip())
    return [c for c in out if c]


def _coupling_defeats_sim(micro_pre_text: str) -> bool:
    """True when the coupling carries a SAME-MEMORY conjunct.

    ``sim`` builds its invariant by reading the postcondition as a set of
    equalities BETWEEN the two memories; a conjunct that mentions only one
    memory (``S.f09{1} = S.f08{1}`` -- the survivor-consistency /
    hoist-cache facts a broken chain's coupling threads) is not such an
    equality and EasyCrypt gives up with *cannot infer the set of
    equalities*. Measured on ``CK_seedbased_LEAK_BIND_K_PK``
    ``micro_2_hashg_left_22``: dropping exactly the two same-memory conjuncts
    from that lemma makes the identical ``proc; sim.`` close. Cross-NAMED
    two-memory pairs (``S1.a{1} = S2.b{2}``, a ``Standardize Field Names``
    rename) are fine and stay on ``sim``.
    """
    for conj in _split_conjuncts(micro_pre_text):
        if "=" not in conj:
            continue
        if ("{1}" in conj) != ("{2}" in conj):
            return True
    return False


def _project_to_method(game: frog_ast.Game, oracle_name: str) -> frog_ast.Game | None:
    """Deepcopy ``game`` keeping only the method named ``oracle_name`` (lower)."""
    chosen = [m for m in game.methods if m.signature.name.lower() == oracle_name]
    if not chosen:
        return None
    proj = copy.deepcopy(game)
    proj.methods = [copy.deepcopy(chosen[0])]
    return proj


@dataclass
class MicroRequests:
    """Axiom/lemma requests one micro leg's tactic references (Phase 2, (c)).

    Mirrors the request families of :class:`MultiOracleHopChainInfo` so a
    per-transform micro can request the same licensed foundations the
    whole-oracle routes thread today: ``pres`` — ``<M>_<m>_pres``
    glob-preservation axioms; ``inj`` — ``<M>_<m>_inj`` joint-injectivity
    axioms; ``bij`` — ``(module, method, bitstring type, clone alias)``
    bijectivity derivations; ``decaps_val`` — concrete-scheme
    ``<Scheme>_decaps_val`` phoare lemmas. Two validation-only families
    (never emitted, only checked): ``det`` — the always-emitted
    ``<M>_<m>_det`` axioms a drain references, recorded so tripwires can
    assert a leg touches only licensed axioms; ``slice_types`` — registered
    concat-triple keys a slice cascade uses (an unregistered triple must
    DECLINE the move, never mint an axiom — fail closed).
    """

    pres: set[tuple[str, str]] = field(default_factory=set)
    inj: set[tuple[str, str]] = field(default_factory=set)
    bij: set[tuple[str, str, str, str]] = field(default_factory=set)
    decaps_val: set[str] = field(default_factory=set)
    det: set[tuple[str, str]] = field(default_factory=set)
    slice_types: set[str] = field(default_factory=set)


class _LocalBinderScan(Visitor[None]):
    """Ordered scan of one method body for the rename-equality gate (Move 1).

    Collects the typed local binders (``Assignment``/``Sample``/
    ``UniqueSample`` with a type annotation and a ``Variable`` LHS) in
    traversal order, plus everything that makes a *name-based* positional
    renaming unsafe: duplicate binder names, a binder name already seen
    before its binding (a use-before-decl reads the OUTER scope, which Alpha
    Rename preserves per-occurrence while a name substitution cannot), a
    self-reference inside the binder's own annotation/RHS, and the binders a
    substitution over ``Variable`` nodes cannot rename at their binding site
    (``VariableDeclaration`` / loop binders, which bind plain strings).
    """

    def __init__(self) -> None:
        self.binders: list[tuple[str, frog_ast.Type]] = []
        self._binder_names: set[str] = set()
        self.seen: set[str] = set()
        self.fixed_binders: set[str] = set()
        self.unsafe = False

    def result(self) -> None:
        return None

    def _maybe_bind(
        self,
        the_type: frog_ast.Type | None,
        var: frog_ast.Expression,
        *own_reads: frog_ast.ASTNode | None,
    ) -> None:
        if the_type is None or not isinstance(var, frog_ast.Variable):
            return
        name = var.name
        if (
            name in self._binder_names
            or name in self.seen
            or name in self._names_in(the_type, *own_reads)
        ):
            self.unsafe = True
        self._binder_names.add(name)
        self.binders.append((name, the_type))

    def visit_assignment(self, node: frog_ast.Assignment) -> None:
        self._maybe_bind(node.the_type, node.var, node.value)

    def visit_sample(self, node: frog_ast.Sample) -> None:
        self._maybe_bind(node.the_type, node.var, node.sampled_from)

    def visit_unique_sample(self, node: frog_ast.UniqueSample) -> None:
        self._maybe_bind(node.the_type, node.var, node.sampled_from, node.unique_set)

    def visit_variable_declaration(self, node: frog_ast.VariableDeclaration) -> None:
        self.fixed_binders.add(node.name)

    def visit_numeric_for(self, node: frog_ast.NumericFor) -> None:
        self.fixed_binders.add(node.name)

    def visit_generic_for(self, node: frog_ast.GenericFor) -> None:
        self.fixed_binders.add(node.var_name)

    def visit_variable(self, node: frog_ast.Variable) -> None:
        self.seen.add(node.name)

    @staticmethod
    def _names_in(*nodes: frog_ast.ASTNode | None) -> set[str]:
        out: set[str] = set()
        for node in nodes:
            if node is None:
                continue
            collector = VariableCollectionVisitor()
            collector.visit(node)
            out |= {v.name for v in collector.result()}
        return out


def _rename_equal_projection(pb: frog_ast.Game, pa: frog_ast.Game) -> bool:
    """Move 1: equal modulo a positional renaming of typed local binders.

    True only when fields, game parameters, and the method signature are
    byte-identical and the two bodies become AST-equal after renaming each
    side's typed local binders positionally to the same fresh ``__mv<i>__``
    names. That guarantees ``proc; sim.`` closes (identical modulo local
    names — the probe-validated ``leg_alpha_rename`` shape), so this is
    never a maybe-tactic. Any shadowing hazard DECLINES instead: duplicate
    or use-before-binding binder names, a binder colliding with a
    field/param/string-bound binder, or a ``__mv`` collision. Covers the
    ``Alpha Rename`` / ``Variable Standardization`` legs (and any other
    rename-only residue); field renames stay with the role-map machinery.
    """
    if pb.fields != pa.fields or pb.parameters != pa.parameters:
        return False
    mb, ma = pb.methods[0], pa.methods[0]
    if mb.signature != ma.signature:
        return False
    scan_b, scan_a = _LocalBinderScan(), _LocalBinderScan()
    scan_b.visit(mb.block)
    scan_a.visit(ma.block)
    if scan_b.unsafe or scan_a.unsafe:
        return False
    if len(scan_b.binders) != len(scan_a.binders):
        return False
    names_b = [n for n, _ in scan_b.binders]
    names_a = [n for n, _ in scan_a.binders]
    reserved = (
        {f.name for f in pb.fields}
        | {p.name for p in mb.signature.parameters}
        | scan_b.fixed_binders
        | scan_a.fixed_binders
    )
    if any(n in reserved for n in names_b + names_a):
        return False
    if "__mv" in str(mb) or "__mv" in str(ma):
        return False

    def canonicalize(method: frog_ast.Method, names: list[str]) -> frog_ast.ASTNode:
        replace_map: frog_ast.ASTMap[frog_ast.ASTNode] = frog_ast.ASTMap(identity=False)
        for i, name in enumerate(names):
            replace_map.set(frog_ast.Variable(name), frog_ast.Variable(f"__mv{i}__"))
        return SubstitutionTransformer(replace_map).transform(copy.deepcopy(method))

    return canonicalize(mb, names_b) == canonicalize(ma, names_a)


def _init_determines_whole_state(
    proj: frog_ast.Game,
    modules: mt.ModuleTranslator,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
    use_canonical_fields: bool,
) -> bool:
    """Does this ``Initialize`` WRITE every field of its state?

    An init leg's precondition is ``true`` -- there is no incoming state to
    relate -- while its postcondition asserts the coupling. That is provable
    exactly when the two bodies determine the coupled state between them, so
    every coupled field has to be written by ``Initialize``. A field it never
    writes (a random-oracle table, which the hash oracle fills lazily) holds
    an arbitrary value that nothing relates across the two memories, and the
    coupling is underivable: EasyCrypt answers *cannot save an incomplete
    proof*, measured on `CG_expanded_INDCCA_T` `micro_8_initialize_left_0`.

    Rendered with the chain's own field naming so the names compared here
    are the emitted ones.
    """
    mod = _flat_state_module(
        modules,
        "Step_it",
        proj,
        external_module_types,
        method_return_types,
        flat_params,
        emit_state_vars=True,
        use_canonical_fields=use_canonical_fields,
    )
    if not mod.procs:
        return False
    fields = {v.name for v in mod.module_vars}
    if not fields:
        return True
    written = {
        stmt.var
        for stmt in _flatten_stmts(mod.procs[0].body)
        if isinstance(stmt, (ec_ast.Assign, ec_ast.Sample, ec_ast.Call)) and stmt.var
    }
    return fields <= written


def _oracle_step_tactic(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    state_before: frog_ast.Game,
    state_after: frog_ast.Game,
    oracle_name: str,
    transform_name: str,
    reversed_dir: bool,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    modules: mt.ModuleTranslator,
    flat_params: list[ec_ast.ModuleParam],
    det_methods: dict[str, set[str]],
    micro_pre_text: str = "true",
    left_ref: str = "",
    right_ref: str = "",
    clone_alias: dict[str, str] | None = None,
    use_canonical_fields: bool = False,
    is_init: bool = False,
) -> tuple[list[str], MicroRequests, str, str] | None:
    """Tactic for one chain step's micro lemma, restricted to ``oracle_name``.

    ``micro_pre_text`` is the exact precondition the caller will state on
    this micro's lemma (``micro_pre(lref, rref)``); Move 2's guard-site
    closer restates it inside its ``seq`` invariant, and declines when it is
    ``"true"`` (an init leg -- nothing to re-establish the guard equality
    from). ``left_ref``/``right_ref`` are the emitted lemma's two module
    reference texts (for field pins); ``clone_alias`` maps a declared module
    to its per-module theory alias (``KEM_T`` -> ``KEM_T_c``, for ``ev_*``
    qualification);
    ``use_canonical_fields`` is the chain-wide flat-state field-naming
    decision (see :func:`_emit_one_oracle_chain`) -- a route whose tactic
    NAMES a state field must render its own copy of the state under the
    same setting, or it emits a field name the emitted module has not got.

    Selection is transform-keyed per the ratified architecture: each move
    runs only for a ``transform_name`` registered for its entry id in
    :mod:`tactic_registry` (the sim/swap moves are universal — the
    bystander rule — and the survivor peel / hoist pair are registered
    for their transform classes). Returns
    ``(tactic, requests, rung, entry_id)`` where ``requests`` is the
    :class:`MicroRequests` record of axiom families the tactic
    references, ``rung`` is the automation-ladder token, and
    ``entry_id`` is the registered entry the caller tags the micro's
    provenance with; or ``None`` when no registered move applies (the
    caller falls to the transform-keyed cache, then an honest admit).
    The tactic is:

    * ``["proc; sim."]`` when that oracle's body is unchanged across the step
      (``sim`` preserves the coupling on untouched state), or unchanged
      modulo a renaming of typed local binders (Move 1,
      :func:`_rename_equal_projection` — the Alpha Rename / Variable
      Standardization legs);
    * a ``proc; swap...; sim`` sequence when the step is a pure top-level
      reorder of that oracle's body;
    * a backbone peel when the step is a "Remove redundant variables for
      fields" removal (the two states differ in ``glob`` cardinality, so the
      oracle reads a removed field via its survivor on one side and ``sim``
      cannot relate the differently-named reads -- wall 4);
    * a one-sided dead-call drop when the step drops abstract calls whose
      results the return does not use (``Absorb Redundant Early Return`` over a
      constant-return oracle -- wall 5); each dropped deterministic call is
      removed with ``call{side} (<M>_<m>_pres g)``.
    """
    pb = _project_to_method(state_before, oracle_name)
    pa = _project_to_method(state_after, oracle_name)
    if pb is None or pa is None:
        return None
    # An INIT leg is provable only when the two ``Initialize`` bodies
    # determine the coupled state between them: its precondition is ``true``,
    # so if either leaves a field unwritten nothing relates that field across
    # the two memories and no tactic can establish the coupling -- decline
    # rather than emit one that will not close. Gated on ``is_init`` and not
    # on the precondition alone: a NON-init leg can also carry a ``true``
    # precondition, and it has incoming state, so the reasoning does not
    # apply to it. See :func:`_init_determines_whole_state`.
    if (
        is_init
        and micro_pre_text == "true"
        and not all(
            _init_determines_whole_state(
                proj,
                modules,
                external_module_types,
                method_return_types,
                flat_params,
                use_canonical_fields,
            )
            for proj in (pb, pa)
        )
    ):
        return None
    # Move 3c (Phase-2): the Hoist-Deterministic-Call-to-Initialize pair.
    # MUST run before the field-cardinality branch below: a Hoist step is a
    # +1-cardinality pair whose backbones differ by the cached det call, so
    # the survivor peel would mispair the backbone (a tactic that runs but
    # does not close -- the worst case). Detection is exact (reverse
    # substitution); non-Hoist cardinality pairs fall through unchanged. A
    # detected pair is AUTHORITATIVE: if its leg builder declines, the
    # oracle takes the honest admit, never the mispairing peel.
    if tactic_registry.is_registered(transform_name, tactic_registry.ENTRY_HOIST_PAIR):
        hoist = _detect_hoist_pair(state_before, state_after, det_methods)
        if hoist is not None:
            hoist_step = _hoist_pair_step(
                hoist,
                pb,
                pa,
                state_after,
                oracle_name,
                reversed_dir,
                modules,
                external_module_types,
                method_return_types,
                flat_params,
                det_methods,
                micro_pre_text,
                left_ref,
                right_ref,
                clone_alias or {},
            )
            if hoist_step is None:
                return None
            tac, reqs, rung = hoist_step
            return tac, reqs, rung, tactic_registry.ENTRY_HOIST_PAIR
    # Field-removal step: the field-aware coupling carries a survivor invariant
    # (``dk0 = challenger_dk0``); peel the (structurally identical) call/sample
    # backbone with ``call (_: true)``/``rnd`` so ``auto; smt()`` discharges each
    # abstract-call arg equality from that invariant. ``sim`` cannot -- it has no
    # way to use the relational fact to equate ``K.decaps(challenger_dk0){1}``
    # with ``K.decaps(dk0){2}``. Validated: ``ec_templates/field_removal_coupling.ec``.
    if len(state_before.fields) != len(state_after.fields):
        # A cardinality-differing pair is only closable by the survivor
        # peel, and only the field-set-changing transforms are registered
        # for it; any other transform's leg declines to an honest admit.
        if not tactic_registry.is_registered(
            transform_name, tactic_registry.ENTRY_SURVIVOR_PEEL
        ):
            return None
        amod = _flat_state_module(
            modules,
            "Step_rm",
            pa,
            external_module_types,
            method_return_types,
            flat_params,
        )
        bmod = _flat_state_module(
            modules,
            "Step_rm_before",
            pb,
            external_module_types,
            method_return_types,
            flat_params,
        )
        if not amod.procs or not bmod.procs:
            return None
        body = amod.procs[0].body
        # HONEST GATE. The peel below emits one ``call``/``rnd`` per backbone
        # entry with NOTHING between them, so it only applies when the backbone
        # is an unbroken TAIL of the body: EasyCrypt's ``call`` requires the
        # last instruction of both programs to be a procedure call, and a
        # deterministic assignment sitting BETWEEN two abstract calls (e.g.
        # ``__a26__ <- __a25__.`1;`` between ``KEM_PQ.derivekeypair`` and
        # ``KEM_PQ.decaps``) makes the next ``call`` fail with "invalid last
        # instruction". Both sides must also present the same kind sequence,
        # since each tactic step consumes one instruction on each side. When
        # either condition fails the leg DECLINES rather than emitting a tactic
        # that cannot close -- the caller then falls back to the whole-oracle
        # route exactly as it does for any other unhandled shape.
        #
        # A backbone that is NOT an unbroken tail is still peelable -- just not
        # by THIS tactic. One ``wp; call (_: true)`` pair per backbone entry
        # (``_backbone_peel``'s shape), closed by ``auto => /#``, absorbs each
        # interleaved deterministic run and closes the same leg; probed on the
        # exact shape in ``ec_templates/interleaved_peel.ec`` (EasyCrypt OK,
        # with a proof-level negative control that fails when the survivor
        # invariant is dropped). So the broken-tail case takes the paired peel
        # and only the kind-sequence mismatch declines.
        tail_before = _peelable_tail_backbone(bmod.procs[0].body)
        tail_after = _peelable_tail_backbone(body)
        pure_tail = tail_before is not None and tail_after is not None
        bb_before: list[tuple[str, str | None]]
        bb_after: list[tuple[str, str | None]]
        if tail_before is not None and tail_after is not None:
            bb_before, bb_after = tail_before, tail_after
        else:
            bb_before = _call_sample_backbone(bmod.procs[0].body)
            bb_after = _call_sample_backbone(body)
        if [k for k, _ in bb_before] != [k for k, _ in bb_after]:
            return None
        # SECOND HONEST GATE: the closing ``auto`` must discharge ``={res}``
        # and every field conjunct from the precondition alone, which it can do
        # exactly when the two bodies are the SAME program modulo the field
        # renaming the coupling states (the shape the validated template has:
        # one side reads ``challenger_dk0`` where the other reads ``dk0``, and
        # the coupling equates them). When they are not -- e.g. a
        # ``Split Opaque Tuple Field`` step, where one side reads a packed
        # field and the other reads its components, a relation the coupling
        # does not state -- ``auto`` runs and leaves the goal open, which is
        # the worst outcome: a file with no ``admit.`` that EasyCrypt still
        # rejects. Decline instead.
        # pylint: disable=protected-access
        names_b = {mt._ec_field_name(f.name) for f in state_before.fields}
        names_a = {mt._ec_field_name(f.name) for f in state_after.fields}
        side1, side2, f1, f2 = (
            (amod, bmod, names_a, names_b)
            if reversed_dir
            else (bmod, amod, names_b, names_a)
        )
        if not _bodies_equal_under_field_map(
            side1,
            side2,
            micro_pre_text,
            _ref_base(left_ref),
            _ref_base(right_ref),
            f1,
            f2,
        ):
            # Not the survivor shape: decline to an honest admit. (The
            # shape-keyed fallbacks that used to sit here — the
            # equal-rendered-body peel and the packed-guard descent — were
            # removed under the ratified architecture: their tactics were
            # selected by program shape with the transform out of the
            # loop. Their probes remain the rebuild's raw material.)
            return None
        # Couple each abstract call (``call (_: true)``) / sample (``rnd``) of the
        # shared backbone, tail-to-front, then close with a single ``auto.``.
        # ``auto`` performs the trailing ``wp`` and the residual arg-equality
        # ``smt`` internally -- an EXPLICIT leading ``wp`` (as in ``_backbone_peel``)
        # instead leaves a first-order residual that batch ``smt()`` cannot close
        # even though the interactive prover can (validated tactic:
        # ``ec_templates/field_removal_coupling.ec`` -- ``proc; call (_: true); auto``).
        tac = ["proc."]
        for kind, _callee in reversed(bb_after):
            if not pure_tail:
                tac.append("wp.")
            tac.append("call (_: true)." if kind == "call" else "rnd.")
        tac.append("auto." if pure_tail else "auto => /#.")
        return tac, MicroRequests(), SYNTH_PARAM, tactic_registry.ENTRY_SURVIVOR_PEEL
    # ``sim`` reads the postcondition as equalities BETWEEN the two memories,
    # so an equal-body leg whose coupling also carries a same-memory conjunct
    # ("cannot infer the set of equalities") is not a ``sim`` leg at all: it
    # takes the route below, which closes the one recoverable shape and
    # DECLINES the rest.
    if pb.methods[0] == pa.methods[0]:
        if _coupling_defeats_sim(micro_pre_text):
            # A same-memory conjunct in the coupling defeats ``sim``; the
            # crossed-coupling shape case that used to recover one shape
            # here was removed under the ratified architecture. Decline.
            return None
        return (
            ["proc; sim."],
            MicroRequests(),
            SYNTH_STATIC,
            tactic_registry.ENTRY_IDENTITY_SIM,
        )
    before_h = _normalize_for_ec(
        copy.deepcopy(pb), external_module_types, method_return_types
    )
    after_h = _normalize_for_ec(
        copy.deepcopy(pa), external_module_types, method_return_types
    )
    swaps = _permutation_swaps(before_h, after_h, reversed_dir=reversed_dir)
    if swaps is not None:
        return (
            ["proc.", *swaps, "sim."],
            MicroRequests(),
            SYNTH_PARAM,
            tactic_registry.ENTRY_PERM_SWAP_SIM,
        )
    # Move 1 (Phase-2 micro synthesizers): equal modulo local-binder renaming
    # -- the Alpha Rename / Variable Standardization legs. ``sim`` is
    # name-blind on locals, so the exact-AST gate above was the only thing
    # blocking these (probe: ``leg_alpha_rename``). Placed AFTER the existing
    # branches so any leg they close today stays byte-identical; the raw
    # projections are compared (same basis as the exact-equal gate). Same
    # same-memory-conjunct gate as the exact-equal branch: renaming the
    # LOCALS does not change what ``sim`` can infer about the memories.
    if _rename_equal_projection(pb, pa):
        if _coupling_defeats_sim(micro_pre_text):
            return None
        return (
            ["proc; sim."],
            MicroRequests(),
            SYNTH_STATIC,
            tactic_registry.ENTRY_RENAME_SIM,
        )
    # No registered move applies: decline to the transform-keyed cache,
    # then an honest admit naming the transform. The shape-keyed cases
    # that used to be tried here (rendered identity/rename, the ISUV
    # alignment, the single-site rewrite, the IES delta walk, the
    # if-fold case tree, the plumbing peel, the dead-call drop, the
    # coupled-guard descent) were removed under the ratified
    # architecture: each selected its tactic by matching the shape of
    # the two program fragments with the transform name out of the
    # loop. Their EC-validated probes and derivation records are the
    # raw material for rebuilding them as registered entries, one
    # transform at a time.
    return None


def _blank_dead_result_names(body: list[ec_ast.EcStmt]) -> list[ec_ast.EcStmt]:
    """``body`` with every CALL's result variable blanked.

    A dead call's result name is exactly what ``sim`` is allowed to ignore,
    so blanking it turns "equal modulo dead names" into plain equality and
    lets a caller check that the difference really is confined to them.
    Anything else that differs -- a commuted equality in a guard, an extra
    statement -- survives the blanking and is caught.
    """
    out: list[ec_ast.EcStmt] = []
    for stmt in body:
        if isinstance(stmt, ec_ast.Call):
            out.append(ec_ast.Call("", stmt.callee, stmt.args))
        elif isinstance(stmt, ec_ast.If):
            out.append(
                ec_ast.If(
                    stmt.guard,
                    _blank_dead_result_names(stmt.then_body),
                    _blank_dead_result_names(stmt.else_body),
                )
            )
        elif isinstance(stmt, ec_ast.While):
            out.append(ec_ast.While(stmt.guard, _blank_dead_result_names(stmt.body)))
        else:
            out.append(stmt)
    return out


def _name_sorted_vars(module: ec_ast.Module) -> ec_ast.Module:
    """``module`` with its ``var`` block sorted by variable name.

    Declaration ORDER carries no meaning in the emitted flat states, because
    the only thing the micro-lemmas read the var block through is ``glob``,
    and **EC orders a ``glob`` tuple by variable name, not by declaration
    order** -- the same fact :func:`_canonical_field_renames` is built on.
    Two states with the same ``(name, type)`` var set and the same bodies are
    therefore literally the same EC module, and ``proc; sim.`` relates it to
    itself.

    Comparing the var block as an ordered list made
    :func:`_rendered_identity_step` decline exactly that: measured on the six
    IND-CCA_T exports, every `Standardize Field Names` leg (14 in
    `CG_expanded_INDCCA_T` alone, none of which had ever closed) differs from
    its neighbour ONLY by the order of five identically-named, identically-
    typed `f<NN>` declarations. Sorting is the smallest normalization that
    sees this; it does NOT dedupe, drop, or retype anything, so a genuine var
    difference -- a rename, a type change, an added or removed field -- still
    declines. Probed first, both ways:
    ``ec_templates/glob_ignores_decl_order.ec`` is accepted by EasyCrypt and
    its body-mutated twin is rejected with *cannot save an incomplete
    proof*.
    """
    return replace(
        module,
        module_vars=sorted(module.module_vars, key=lambda v: (v.name, v.type.text)),
    )


_RENAME_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


def _modules_alpha_equal(  # pylint: disable=too-many-return-statements
    bmod: ec_ast.Module, amod: ec_ast.Module
) -> bool:
    """True when two rendered modules differ ONLY by a renaming of locals.

    Split out of :func:`_rendered_rename_step` so every guard below is unit
    testable without building a pair of FrogLang games; the tests are in
    ``tests/unit/export/test_rendered_rename_row.py``.

    The renaming is read POSITIONALLY off each proc's ``var`` block, must be
    type-preserving and injective, and is then applied to the rendered TEXT,
    which must match exactly. Text equality after substitution is what makes
    this safe: a field rename, a different callee, a different op, a changed
    literal or a reordered statement all survive the substitution and
    decline. A local whose name collides with a state var or a functor param
    declines rather than risk capture.
    """
    if not bmod.procs or not amod.procs:
        return False
    if bmod.name != amod.name or bmod.params != amod.params:
        return False
    if _name_sorted_vars(bmod).module_vars != _name_sorted_vars(amod).module_vars:
        return False
    if len(bmod.procs) != len(amod.procs):
        return False
    reserved = {v.name for v in bmod.module_vars} | {p.name for p in bmod.params}
    any_locals = False
    for bproc, aproc in zip(bmod.procs, amod.procs):
        if (
            bproc.name != aproc.name
            or bproc.params != aproc.params
            or bproc.return_type != aproc.return_type
        ):
            return False
        blocals = [st for st in bproc.body if isinstance(st, ec_ast.VarDecl)]
        alocals = [st for st in aproc.body if isinstance(st, ec_ast.VarDecl)]
        if len(blocals) != len(alocals):
            return False
        # ONE MAP PER PROC. EC procedure scopes are independent, so the same
        # local name in two procedures may legitimately correspond to two
        # different names, and a single module-wide map calls that a
        # conflict and declines. Measured on `CG_expanded_INDCCA_T`: four
        # legs lost to exactly that, e.g. `decaps`'s `ct_PQ -> __a6__`
        # against `hash`'s `ct_PQ -> __a7__`.
        rename: dict[str, str] = {}
        for bvar, avar in zip(blocals, alocals):
            if bvar.type != avar.type:
                return False
            if rename.setdefault(bvar.name, avar.name) != avar.name:
                return False
        if len(set(rename.values())) != len(rename):
            return False
        if reserved & (set(rename) | set(rename.values())):
            return False
        any_locals = any_locals or bool(rename)
        if not _procs_equal_under_rename(bmod, bproc, aproc, rename):
            return False
    return any_locals


def _procs_equal_under_rename(
    module: ec_ast.Module,
    bproc: ec_ast.Proc,
    aproc: ec_ast.Proc,
    rename: dict[str, str],
) -> bool:
    """Whether two procs render identically once ``rename`` is applied to
    ``bproc``.

    Each proc is rendered inside a one-proc copy of ``module`` so the
    renderer sees the same context it would in the real module; that context
    is identical on both sides (the caller has already compared the header,
    the functor params and the state var block), so it cancels.
    """
    btext = "\n".join(_render_module_decl(replace(module, procs=[bproc])))
    atext = "\n".join(_render_module_decl(replace(module, procs=[aproc])))
    renamed = _RENAME_TOKEN_RE.sub(lambda m: rename.get(m.group(0), m.group(0)), btext)
    return renamed == atext


def _peel_reaches_every_event(body: list[ec_ast.EcStmt]) -> bool:
    """False when ``body`` holds a ``wp``-opaque construct the TOP-LEVEL
    backbone peel can neither see nor cross.

    :func:`_call_sample_backbone` reads top-level statements only, so a call,
    a sample or a ``while`` under an ``if`` is invisible to it -- the peel
    comes out too short -- and ``wp`` cannot cross such an ``if``, so the
    next ``call`` reports *invalid last instruction*. A top-level ``while``
    blocks ``wp`` the same way.
    """

    def nested(stmts: Sequence[ec_ast.EcStmt]) -> bool:
        for s in stmts:
            if isinstance(s, (ec_ast.Call, ec_ast.Sample, ec_ast.While)):
                return True
            if isinstance(s, ec_ast.If) and (
                nested(s.then_body) or nested(s.else_body)
            ):
                return True
        return False

    for stmt in _exec_stmts(body):
        if isinstance(stmt, ec_ast.While):
            return False
        if isinstance(stmt, ec_ast.If) and (
            nested(stmt.then_body) or nested(stmt.else_body)
        ):
            return False
    return True


@dataclass(frozen=True)
class _DescentScope:
    """What one level of the guard descent inherits from the levels above it.

    Two things go wrong when a level is built from the fragment it is handed
    rather than from this record, and both were measured:

    * **Declared types.** ``_decl_types`` reads ``VarDecl``s, and only the whole
      procedure body has them -- EasyCrypt lifts an arm's declarations to the
      procedure top, so an arm carries NONE. Re-deriving them one level down
      returns ``{}``, and :func:`_type_mismatched_common_local` then compares
      its two different defaults, so EVERY common local below depth 0 looks
      type-mismatched and the split path always declines.
    * **The invariant.** ``seq n m : (I)`` DISCARDS everything about the prefix
      except ``I``. An inner level that restates only the leg's coupling throws
      away the enclosing run's locals, which are still in scope and may still be
      read; the closer is then handed a goal missing exactly those equalities.
      Probed both ways: ``.ec-tmp/nestedrun_probe.ec`` accumulates and is
      ACCEPTED, ``.ec-tmp/nestedrun_negctl.ec`` drops one enclosing local and
      EasyCrypt answers *cannot prove goal (strict)*, printing the missing
      ``a{1} = a{2}`` in the goal.

    These two are one change, not two: fixing the type lookup alone lets the
    split path fire one level down while the invariant is still un-accumulated,
    which is how the route came to admit legs EasyCrypt rejects.

    ``bound`` is every local an enclosing run binds, so the coverage gate can
    ask about all of them rather than only this level's.
    """

    types1: dict[str, str]
    types2: dict[str, str]
    invariant: str
    bound: frozenset[str]


def _decl_types(body: list[ec_ast.EcStmt]) -> dict[str, str]:
    """Each local's declared type, by name, as rendered text."""
    return {s.name: str(s.type) for s in body if isinstance(s, ec_ast.VarDecl)}


def _rename_tokens(text: str, fields: set[str], renaming: dict[str, str]) -> str:
    """``text`` with every state field replaced by its coupling-class name."""
    if not renaming:
        return text
    return _RENAME_TOKEN_RE.sub(
        lambda m: (
            renaming.get(m.group(0), m.group(0)) if m.group(0) in fields else m.group(0)
        ),
        text,
    )


def _contains_while(body: list[ec_ast.EcStmt]) -> bool:
    """Is there a ``while`` anywhere in ``body``, branch arms included?"""
    for stmt in _exec_stmts(body):
        if isinstance(stmt, ec_ast.While):
            return True
        if isinstance(stmt, ec_ast.If) and (
            _contains_while(stmt.then_body) or _contains_while(stmt.else_body)
        ):
            return True
    return False


def _token_occurrences(body: list[ec_ast.EcStmt]) -> Counter[str]:
    """How often each identifier appears in ``body``, branch arms included."""
    counts: Counter[str] = Counter()
    for stmt in _exec_stmts(body):
        counts.update(_RENAME_TOKEN_RE.findall(_stmt_all_text(stmt)))
        if isinstance(stmt, ec_ast.If):
            counts.update(_token_occurrences(stmt.then_body))
            counts.update(_token_occurrences(stmt.else_body))
    return counts


def _field_reference_order(
    body: list[ec_ast.EcStmt],
    fields: set[str],
    renaming: dict[str, str] | None = None,
) -> list[list[str]]:
    """Which state fields ``body`` mentions, per PEEL SEGMENT.

    The body is cut at each abstract call, giving alternating deterministic
    runs and calls; each segment contributes the sorted multiset of the state
    fields it mentions. Descends into ``if``/``while`` bodies so a
    branch-local reference counts where it appears.

    That granularity is the peel's own: ``wp`` collapses a whole deterministic
    run at once and ``call`` couples one call, so what has to correspond
    between the two sides is which fields each SEGMENT mentions -- not which
    statement, since a plumbing leg changes the statement count by
    construction, and not the whole body, which cannot tell a role swap from a
    commuted pair.

    So a leg that merely commutes two field operands passes (``Normalize
    Commutative Chains``: ``field7 <> field8`` against ``field8 <> field7``,
    whose goal is true because the coupling supplies both equalities), while a
    leg that swaps two fields' ROLES between two different calls is declined
    (``CG_expanded_LEAK_BIND_K_PK``, where the closer was handed
    ``concat(.., field1{1}) = concat(.., field2{2})`` against a precondition
    coupling the globs by name -- a FALSE subgoal, not a hard one).

    ``renaming`` reads each field through a coupling class map
    (:func:`_coupled_field_renaming`), which is how a leg that merely renames
    its fields is compared: two names the precondition proves equal collapse
    to one representative, so the segments agree exactly when the two
    programs read equal values in the same places. Omitted, the names are
    compared as they stand.
    """
    ren = renaming or {}
    out: list[list[str]] = []
    run: list[str] = []
    for stmt in _exec_stmts(body):
        toks = [ren.get(tok, tok) for tok in _stmt_tokens(stmt) if tok in fields]
        if isinstance(stmt, ec_ast.Call):
            out.append(sorted(run))
            out.append(sorted(toks))
            run = []
            continue
        run.extend(toks)
        if isinstance(stmt, ec_ast.If):
            for seg in _field_reference_order(stmt.then_body, fields, renaming):
                run.extend(seg)
            for seg in _field_reference_order(stmt.else_body, fields, renaming):
                run.extend(seg)
        elif isinstance(stmt, ec_ast.While):
            for seg in _field_reference_order(stmt.body, fields, renaming):
                run.extend(seg)
    out.append(sorted(run))
    return out


def _schema_reflexive(lhs: frog_ast.Expression, rhs: frog_ast.Expression) -> bool:
    """Reflexive Comparison row: ``e == e ~ true`` / ``e != e ~ false``."""
    if not isinstance(lhs, frog_ast.BinaryOperation) or not isinstance(
        rhs, frog_ast.Boolean
    ):
        return False
    if lhs.left_expression != lhs.right_expression:
        return False
    if lhs.operator == frog_ast.BinaryOperators.EQUALS:
        return rhs.bool is True
    if lhs.operator == frog_ast.BinaryOperators.NOTEQUALS:
        return rhs.bool is False
    return False


def _schema_bool_identity(lhs: frog_ast.Expression, rhs: frog_ast.Expression) -> bool:
    """Boolean Identity row: a literal-boolean AND/OR identity collapse."""
    if not isinstance(lhs, frog_ast.BinaryOperation):
        return False
    left, right = lhs.left_expression, lhs.right_expression
    lit = left if isinstance(left, frog_ast.Boolean) else None
    other = right
    if lit is None:
        lit = right if isinstance(right, frog_ast.Boolean) else None
        other = left
    if lit is None:
        return False
    if lhs.operator == frog_ast.BinaryOperators.AND:
        expected = frog_ast.Boolean(False) if lit.bool is False else other
    elif lhs.operator == frog_ast.BinaryOperators.OR:
        expected = frog_ast.Boolean(True) if lit.bool is True else other
    else:
        return False
    return rhs == expected


def _schema_simplify_nots(lhs: frog_ast.Expression, rhs: frog_ast.Expression) -> bool:
    """Simplify Nots row: ``rhs`` is exactly the SimplifyNot pass of ``lhs``.

    Reuses the engine transformer itself (context-free), so the row's
    precondition is definitionally the transform's own firing condition.
    """
    if not isinstance(lhs, frog_ast.UnaryOperation):
        return False
    simplified = SimplifyNot().transform(copy.deepcopy(lhs))
    return simplified != lhs and simplified == rhs


def _schema_tuple_neq(lhs: frog_ast.Expression, rhs: frog_ast.Expression) -> bool:
    """Tuple Equality Decompose row (v1: tuple-literal-arity gated).

    ``a != b ~ a[0] != b[0] || ... || a[k-1] != b[k-1]``. Fires only when at
    least one side of the ``!=`` is a tuple LITERAL whose arity equals the
    disjunct count -- the only case where completeness of the decomposition
    is checkable without a type map (an incomplete disjunction is not an
    equivalence). Wider arity sources are logged Phase-2 debt.
    """
    if (
        not isinstance(lhs, frog_ast.BinaryOperation)
        or lhs.operator != frog_ast.BinaryOperators.NOTEQUALS
    ):
        return False
    a, b = lhs.left_expression, lhs.right_expression

    def flatten_or(e: frog_ast.Expression) -> list[frog_ast.Expression]:
        if (
            isinstance(e, frog_ast.BinaryOperation)
            and e.operator == frog_ast.BinaryOperators.OR
        ):
            return flatten_or(e.left_expression) + flatten_or(e.right_expression)
        return [e]

    def proj(e: frog_ast.Expression, i: int) -> frog_ast.Expression:
        if isinstance(e, frog_ast.Tuple):
            values = list(e.values)
            return values[i] if i < len(values) else e
        return frog_ast.ArrayAccess(e, frog_ast.Integer(i))

    disjuncts = flatten_or(rhs)
    arity = None
    for side in (a, b):
        if isinstance(side, frog_ast.Tuple):
            arity = len(list(side.values))
            break
    if arity is None or arity != len(disjuncts) or arity < 1:
        return False
    for i, d in enumerate(disjuncts):
        if (
            not isinstance(d, frog_ast.BinaryOperation)
            or d.operator != frog_ast.BinaryOperators.NOTEQUALS
            or d.left_expression != proj(a, i)
            or d.right_expression != proj(b, i)
        ):
            return False
    return True


# Move 2's declarative row table: every schema is fact-free (closable by
# smt() / /# from the locals invariant + coupling alone). Rows needing
# semantic facts about call results (Injective Equality Simplify, Concat
# Equality Decompose -- det pins, _inj/slice lemmas) are Move 3's walk, per
# the probe finding that even their same-call-multiset variants need
# ev-form pins in the seq invariant.
_PURE_SITE_SCHEMAS: tuple[Callable[..., bool], ...] = (
    _schema_reflexive,
    _schema_bool_identity,
    _schema_simplify_nots,
    _schema_tuple_neq,
)


_EC_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class _EvEnv:  # pylint: disable=too-many-instance-attributes
    """Symbolic ev-term environment over one rendered oracle prefix.

    Maps every prefix-assigned local to a closed EC term over ``exists*``
    pins (fields/params) and ``ev_*`` ops -- the Q1 probe's invariant shape.
    Shared pin registry across both sides so identical statements produce
    identical terms.

    ``global_names`` MUST be the module-variable set of the state
    ``side_ref`` names, because every field pin is qualified against it
    (``<side_ref>.<field>{2}``). ``foreign_names`` lists field names of the
    OTHER state in the pair; a body token matching one of those cannot be
    pinned (it is not a variable of ``side_ref``), so :meth:`_subst`
    declines rather than emitting a dangling qualified name.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        det_methods: dict[str, set[str]],
        clone_alias: dict[str, str],
        param_names: set[str],
        global_names: set[str],
        side_ref: str,
        pins: dict[str, str],
        glob_pins: dict[str, str],
        foreign_names: frozenset[str] = frozenset(),
    ) -> None:
        self.det_methods = det_methods
        self.clone_alias = clone_alias
        self.param_names = param_names
        self.global_names = global_names
        self.foreign_names = foreign_names
        self.side_ref = side_ref
        self.pins = pins  # pin expression text -> pin name (shared)
        self.glob_pins = glob_pins  # module -> pin name (shared)
        self.env: dict[str, str] = {}
        self.conjuncts: list[tuple[str, str]] = []  # (local, term)
        # Per-statement drain payload in forward order: a det-axiom
        # application text ``(<M>_<m>_det gv <args>).`` for a call (the
        # caller prefixes ``call{side}``), or None for an assign (collapsed
        # into a ``wp.`` per run at emission).
        self.drains: list[str | None] = []
        self.det_used: set[tuple[str, str]] = set()

    def _subst(self, text: str) -> str | None:
        """Rewrite locals to their terms and fields/params to pins."""
        out: list[str] = []
        pos = 0
        for m in _EC_IDENT_RE.finditer(text):
            out.append(text[pos : m.start()])
            tok = m.group(0)
            if tok in self.env:
                out.append(f"({self.env[tok]})")
            elif tok in self.param_names:
                out.append(self._pin(f"{tok}{{2}}"))
            elif tok in self.global_names:
                out.append(self._pin(f"{self.side_ref}.{tok}{{2}}"))
            elif tok in self.foreign_names:
                return None  # not a variable of ``side_ref`` -- cannot pin it
            else:
                out.append(tok)
            pos = m.end()
        out.append(text[pos:])
        return "".join(out)

    def feed(self, stmt: ec_ast.EcStmt) -> bool:
        """Absorb one prefix statement; False = shape outside the row."""
        if isinstance(stmt, ec_ast.Assign):
            term = self._subst(stmt.rhs)
            if term is None:
                return False
            self.env[stmt.var] = term
            self.conjuncts.append((stmt.var, term))
            self.drains.append(None)  # an assign run collapses into one wp
            return True
        if isinstance(stmt, ec_ast.Call):
            mod, _, meth = stmt.callee.partition(".")
            if meth.lower() not in self.det_methods.get(mod, set()):
                return False
            alias = self.clone_alias.get(mod, f"{mod}_c")
            arg_terms: list[str] = []
            for arg in cc_split_top_args(stmt.args):
                term = self._subst(arg.strip())
                if term is None:
                    return False
                arg_terms.append(term)
            applied = " ".join(f"({t})" for t in arg_terms)
            ev_term = f"{alias}.ev_{meth}" + (f" {applied}" if applied else "")
            self.env[stmt.var] = ev_term
            self.conjuncts.append((stmt.var, ev_term))
            gpin = self._glob_pin(mod)
            self.drains.append(
                f"({mod}_{meth}_det {gpin}" + (f" {applied}" if applied else "") + ")."
            )
            self.det_used.add((mod, meth.lower()))
            return True
        return False

    def _pin(self, expr: str) -> str:
        if expr not in self.pins:
            self.pins[expr] = f"kv{len(self.pins)}"
        return self.pins[expr]

    def _glob_pin(self, module: str) -> str:
        if module not in self.glob_pins:
            self.glob_pins[module] = f"gv{len(self.glob_pins)}"
        return self.glob_pins[module]


@dataclass(frozen=True)
class _HoistPair:
    """A detected ``Hoist Deterministic Call to Initialize`` adjacent pair.

    ``field_name`` is the cache field the transform introduced (FrogLang
    name); ``mod``/``meth`` name the deterministic callee (rendered module +
    lowercase method, the ``<M>_<m>_det``/``ev_<m>`` key); ``call`` is the
    hoisted candidate call (before-side AST); ``consumers`` are the
    lowercase non-init method names whose bodies swapped the inline call
    for the field read (every other method is a bystander).
    """

    field_name: str
    mod: str
    meth: str
    call: frog_ast.FuncCall
    consumers: frozenset[str]


def _lhs_writes_any(block: frog_ast.ASTNode, names: set[str]) -> bool:
    """True if any assignment/sample in ``block`` writes a name in ``names``.

    Conservative: a write is any ``Assignment``/``Sample``/``UniqueSample``
    whose LHS expression mentions the name at all (tuple/projection LHS
    included), so a partial write counts.
    """

    def hits(node: frog_ast.ASTNode) -> bool:
        if not isinstance(
            node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            return False
        collector = VariableCollectionVisitor()
        collector.visit(node.var)
        return any(v.name in names for v in collector.result())

    return SearchVisitor[frog_ast.ASTNode](hits).visit(block) is not None


def _detect_hoist_pair(
    before: frog_ast.Game,
    after: frog_ast.Game,
    det_methods: dict[str, set[str]],
) -> _HoistPair | None:
    """Exact detection of a ``Hoist Deterministic Call to Initialize`` pair.

    Mirrors the transform's own output contract (inlining.py): ``after`` is
    ``before`` plus (a) one appended field, (b) one ``Initialize`` statement
    caching a deterministic call to it, and (c) every structurally-equal
    occurrence of that call replaced by the field read. Verified by REVERSE
    SUBSTITUTION: undoing (a)-(c) must reproduce ``before`` byte-for-byte,
    so any other difference declines. The transform's preservation gate
    (``_fields_mutated_outside_init``) is re-checked statically -- it is
    what makes the cache invariant a frame condition for every bystander.
    v1 declines the Function-variable callee and an alias-rewritten init
    return (the reverse substitution fails there) -- logged Phase-2 debt.
    """
    if len(after.fields) != len(before.fields) + 1:
        return None
    if after.fields[:-1] != before.fields or after.parameters != before.parameters:
        return None
    if [m.signature.name for m in after.methods] != [
        m.signature.name for m in before.methods
    ]:
        return None
    hoisted = after.fields[-1]
    init_idx = next(
        (
            i
            for i, m in enumerate(after.methods)
            if m.signature.name.lower() == "initialize"
        ),
        None,
    )
    if init_idx is None:
        return None
    a_init = after.methods[init_idx]
    cache_idxs = [
        i
        for i, s in enumerate(a_init.block.statements)
        if isinstance(s, frog_ast.Assignment)
        and isinstance(s.var, frog_ast.Variable)
        and s.var.name == hoisted.name
    ]
    if len(cache_idxs) != 1:
        return None
    cache_stmt = a_init.block.statements[cache_idxs[0]]
    assert isinstance(cache_stmt, frog_ast.Assignment)
    call = cache_stmt.value
    if not isinstance(call, frog_ast.FuncCall) or not call.args:
        return None
    func = call.func
    if not isinstance(func, frog_ast.FieldAccess) or not isinstance(
        func.the_object, frog_ast.Variable
    ):
        return None
    mod = func.the_object.name.split("@", 1)[0]
    meth = func.name.lower()
    if meth not in det_methods.get(mod, set()):
        return None
    # Stable args: the candidate's argument reads must be field reads of the
    # shared field block (the transform's ``_is_stable_arg`` residue after
    # canonicalization; params/lets decline in v1).
    field_names = {f.name for f in before.fields}
    arg_reader = VariableCollectionVisitor()
    for a in call.args:
        arg_reader.visit(a)
    arg_names = {v.name for v in arg_reader.result()}
    if not arg_names or not arg_names <= field_names:
        return None
    # The preservation gate, re-checked: no non-init method writes the cache
    # field or any arg field (this is what keeps the conjunct a frame
    # condition on every oracle leg).
    guarded = arg_names | {hoisted.name}
    for i, m in enumerate(after.methods):
        if i != init_idx and _lhs_writes_any(m.block, guarded):
            return None
    # Reverse substitution: drop the field + cache statement, put the call
    # back at every field read, and require exact equality with ``before``.
    sub: frog_ast.ASTMap[frog_ast.ASTNode] = frog_ast.ASTMap(identity=False)
    sub.set(frog_ast.Variable(hoisted.name), copy.deepcopy(call))
    consumers: set[str] = set()
    for i, (bm, am) in enumerate(zip(before.methods, after.methods)):
        restored = copy.deepcopy(am)
        if i == init_idx:
            stmts = list(restored.block.statements)
            del stmts[cache_idxs[0]]
            restored.block = frog_ast.Block(stmts)
        restored = SubstitutionTransformer(sub).transform(restored)
        if restored != bm:
            return None
        if i != init_idx and am != bm:
            consumers.add(bm.signature.name.lower())
    return _HoistPair(
        field_name=hoisted.name,
        mod=mod,
        meth=meth,
        call=call,
        consumers=frozenset(consumers),
    )


_HOIST_SIMPLE_ARG_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*(\.`\d+)*$")


def _hoist_rendered_cache_call(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    modules: mt.ModuleTranslator,
    state: frog_ast.Game,
    pair: _HoistPair,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
) -> tuple[str, str, list[str]] | None:
    """Rendered ``(callee, cache var, arg texts)`` of ``pair``'s cache call.

    Read off ``state``'s RENDERED ``initialize`` (the standing lesson: the
    tactic's terms must come from the renderer, never the raw AST). ``None``
    unless exactly one call statement assigns the cache field and every
    argument is a plain field read/projection (``dk0.`3``) -- the v1 shape;
    anything richer declines and stays an honest admit.
    """
    proj = _project_to_method(state, "initialize")
    if proj is None:
        return None
    mod_ec = _flat_state_module(
        modules,
        "Step_hz",
        proj,
        external_module_types,
        method_return_types,
        flat_params,
    )
    if not mod_ec.procs:
        return None
    h_ec = mt._ec_field_name(pair.field_name)  # pylint: disable=protected-access
    cache = [
        s for s in mod_ec.procs[0].body if isinstance(s, ec_ast.Call) and s.var == h_ec
    ]
    if len(cache) != 1 or cache[0].callee != f"{pair.mod}.{pair.meth}":
        return None
    args = [a.strip() for a in cc_split_top_args(cache[0].args)]
    field_ecs = {
        mt._ec_field_name(f.name)  # pylint: disable=protected-access
        for f in state.fields
    }
    for a in args:
        if not _HOIST_SIMPLE_ARG_RE.match(a) or a.split(".", 1)[0] not in field_ecs:
            return None
    return cache[0].callee, h_ec, args


def _hoist_state_carries(state: frog_ast.Game, pair: _HoistPair) -> bool:
    """True if ``state`` still carries ``pair``'s cache field AND its
    ``initialize`` still contains the defining cache assignment (same call,
    AST-equal) -- the per-state condition under which the cache invariant is
    emitted, consistently, in every field-wise coupling that names it."""
    if not any(f.name == pair.field_name for f in state.fields):
        return False
    init = next(
        (m for m in state.methods if m.signature.name.lower() == "initialize"),
        None,
    )
    if init is None:
        return False
    return any(
        isinstance(s, frog_ast.Assignment)
        and isinstance(s.var, frog_ast.Variable)
        and s.var.name == pair.field_name
        and s.value == pair.call
        for s in init.block.statements
    )


def _hoist_conjunct_registry(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    left_states: list[frog_ast.Game],
    right_states: list[frog_ast.Game],
    left_mods: list[str],
    right_mods: list[str],
    mod_ref: Callable[[str], str],
    modules: mt.ModuleTranslator,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
    det_methods: dict[str, set[str]],
    clone_alias: dict[str, str],
) -> dict[str, list[str]]:
    """Per-base cache-invariant conjuncts for the chain's Hoist pairs (3c).

    For every detected Hoist pair, every chain state (either side) that
    still carries the cache field + its defining init assignment gets the
    one-sided conjunct ``<base>.<h>__SIDE__ = <alias>.ev_<m> (<base>.<arg>
    __SIDE__) ...`` registered under its module base. The coupling emits it
    per side wherever that base appears in a field-wise coupling -- the
    survivor-invariant consistency discipline, which is what lets the
    transitivity's smt side conditions witness/thread it (probe:
    ``.ec-tmp/move3/hoist_chain_probe.ec``). Empty for every chain without
    a Hoist pair, so all other exports are byte-identical.
    """
    pairs: list[_HoistPair] = []
    for states in (left_states, right_states):
        for b, a in zip(states, states[1:]):
            p = _detect_hoist_pair(b, a, det_methods)
            if p is not None and p not in pairs:
                pairs.append(p)
    if not pairs:
        return {}
    registry: dict[str, list[str]] = {}
    for states, names in ((left_states, left_mods), (right_states, right_mods)):
        for state, name in zip(states, names):
            base = _ref_base(mod_ref(name))
            for pair in pairs:
                if not _hoist_state_carries(state, pair):
                    continue
                rendered = _hoist_rendered_cache_call(
                    modules,
                    state,
                    pair,
                    external_module_types,
                    method_return_types,
                    flat_params,
                )
                if rendered is None:
                    continue
                _callee, h_ec, args = rendered
                alias = clone_alias.get(pair.mod, f"{pair.mod}_c")
                applied = " ".join(f"({base}.{a}__SIDE__)" for a in args)
                text = f"{base}.{h_ec}__SIDE__ = {alias}.ev_{pair.meth}" + (
                    f" {applied}" if applied else ""
                )
                bucket = registry.setdefault(base, [])
                if text not in bucket:
                    bucket.append(text)
    return registry


def _hoist_pair_step(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-return-statements
    pair: _HoistPair,
    pb: frog_ast.Game,
    pa: frog_ast.Game,
    state_after: frog_ast.Game,
    oracle_name: str,
    reversed_dir: bool,
    modules: mt.ModuleTranslator,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
    det_methods: dict[str, set[str]],
    micro_pre_text: str,
    left_ref: str,
    right_ref: str,
    clone_alias: dict[str, str],
) -> tuple[list[str], MicroRequests, str] | None:
    """Move 3c: one oracle leg of a Hoist pair (probe-validated shapes).

    Bystander (body untouched): the plain wp-interleaved backbone peel --
    NEVER ``proc; sim``, which fails SILENTLY under the one-sided cache
    conjunct ("cannot infer the set of equalities", surfacing only at qed;
    the probed worst case). Consumer (inline call swapped for the field
    read): the dead-call-drop walk with the cached call drained one-sided
    through its ``<M>_<m>_det`` axiom -- the result is LIVE, so the drain
    PINS ``res = ev_<m>(args)`` from up-front ``exists*`` pins (licensed by
    the transform's own arg-stability gate) and the closing ``/#`` equates
    it with the field read via the coupling's cache conjunct. Probes:
    ``.ec-tmp/move3/hoist_probe.ec`` (legs) and ``hoist_chain_probe.ec``
    (chain composition + both drain directions, exact emitted text).
    """
    if micro_pre_text == "true" or not left_ref or not right_ref:
        return None
    rendered = _hoist_rendered_cache_call(
        modules,
        state_after,
        pair,
        external_module_types,
        method_return_types,
        flat_params,
    )
    if rendered is None:
        return None
    callee, h_ec, args = rendered
    alias = clone_alias.get(pair.mod, f"{pair.mod}_c")
    bmod = _flat_state_module(
        modules,
        "Step_hb",
        pb,
        external_module_types,
        method_return_types,
        flat_params,
    )
    amod = _flat_state_module(
        modules,
        "Step_ha",
        pa,
        external_module_types,
        method_return_types,
        flat_params,
    )
    if not bmod.procs or not amod.procs:
        return None
    # MEASURED DECLINE (2026-08-10). Both branches below close with a single
    # ``auto => /#`` over the coupling. That works when each field pairs with
    # its OWN name across the two states -- the shape the tripwire validates.
    # When the step also RENAMES a field (a coupling conjunct
    # ``<L>.f10{1} = <R>.f11{2}``), the two bodies still read ``f10`` on both
    # sides, so the relation the goal needs is not the one the coupling
    # states and EasyCrypt answers "cannot prove goal (strict)". Decline; the
    # oracle falls back to the whole-oracle route.
    if _coupling_has_field_rename(
        micro_pre_text, _ref_base(left_ref), _ref_base(right_ref)
    ):
        return None
    if oracle_name not in pair.consumers:
        # Bystander: identical bodies; peel the shared backbone.
        if pb.methods[0] != pa.methods[0]:
            return None
        tac = ["proc."]
        for kind, _callee in reversed(_call_sample_backbone(bmod.procs[0].body)):
            tac.append("wp.")
            tac.append("call (_: true)." if kind == "call" else "rnd.")
        tac.append("auto => /#.")
        return tac, MicroRequests(), SYNTH_PARAM
    # Consumer. Enabling-coupling gate (checked on the coupling TEXT, the
    # ``_synth_correctness_decaps_casesplit`` discipline): without the cache
    # conjunct in the pre the peel would run and leave a goal -- a BLOCKED
    # export where an honest admit was available.
    h_base = _ref_base(left_ref if reversed_dir else right_ref)
    if (
        f"{alias}.ev_{pair.meth}" not in micro_pre_text
        or f"{h_base}.{h_ec}" not in micro_pre_text
    ):
        return None
    # The inline call always sits in ``state_before`` (the longer backbone);
    # forward that is the emitted micro's side 1, reversed its side 2.
    side = "2" if reversed_dir else "1"
    pin_base = _ref_base(right_ref if reversed_dir else left_ref)
    long_body, short_body = bmod.procs[0].body, amod.procs[0].body
    # MEASURED DECLINE (2026-08-10). The walk's closer is a single
    # ``auto => /#`` over the whole call-generated post. On the validated
    # template that post is small and closes. On every corpus instance whose
    # body carries the bitstring concatenation algebra -- five nested
    # ``concat_*`` applications feeding the KDF call -- EasyCrypt answers
    # "cannot prove goal (strict)", and it is not a solver-budget effect (a
    # larger budget, introducing the quantifiers first, and ``smt()`` in place
    # of ``/#`` all fail the same way). Six of six such instances were
    # rejected. Until the closer is strengthened, decline: an oracle whose
    # chain needs this leg falls back to the whole-oracle route, which is what
    # it did before the walk existed.
    if _uses_bitstring_algebra(long_body) or _uses_bitstring_algebra(short_body):
        return None
    long_bb = _call_sample_backbone(long_body)
    short_bb = _call_sample_backbone(short_body)
    # ``long_body=None`` deliberately: the tags' dead-result condition is for
    # ``_pres`` drops, which FORGET the result; this drain pins it via
    # ``_det``, so a live result is exactly the point.
    tags = _dead_call_drop_tags(long_bb, short_bb, det_methods)
    if tags is None or not any(tags):
        return None
    events = [
        s for s in _exec_stmts(long_body) if isinstance(s, (ec_ast.Call, ec_ast.Sample))
    ]
    for idx, tagged in enumerate(tags):
        if not tagged:
            continue
        ev = events[idx]
        if not isinstance(ev, ec_ast.Call) or ev.callee != callee:
            return None
        if [a.strip() for a in cc_split_top_args(ev.args)] != args:
            return None
    # Up-front pins of the drained call's arg fields + callee glob (initial
    # memory is valid: the args are stable by the transform's own gate).
    pin_fields: list[str] = []
    for a in args:
        tok = a.split(".", 1)[0]
        if tok not in pin_fields:
            pin_fields.append(tok)
    pin_exprs = [f"{pin_base}.{f}{{{side}}}" for f in pin_fields] + [
        f"(glob {pair.mod}){{{side}}}"
    ]
    pin_names = [f"kv{i}" for i in range(len(pin_fields))] + ["gv"]
    pin_of = dict(zip(pin_fields, pin_names))
    applied = " ".join(
        f"({pin_of[a.split('.', 1)[0]]}{a[len(a.split('.', 1)[0]):]})" for a in args
    )
    tac = ["proc."]
    tac.append(
        "exists* " + ", ".join(pin_exprs) + "; elim* => " + " ".join(pin_names) + "."
    )
    for idx in reversed(range(len(long_bb))):
        kind, _bb_callee = long_bb[idx]
        tac.append("wp.")
        if tags[idx]:
            tac.append(
                f"call{{{side}}} ({pair.mod}_{pair.meth}_det gv"
                + (f" {applied}" if applied else "")
                + ")."
            )
        elif kind == "call":
            tac.append("call (_: true).")
        else:
            tac.append("rnd.")
    tac.append("auto => /#.")
    return tac, MicroRequests(det={(pair.mod, pair.meth)}), SYNTH_PARAM


def _stmt_all_text(stmt: ec_ast.EcStmt) -> str:
    """Every identifier-bearing part of one statement, as text.

    Unlike :func:`_stmt_text` (which yields only the value part) this includes
    the assignment/call TARGET and an ``if`` GUARD, so a gate asking "which
    state fields does this body touch" sees writes and guard reads too. The
    ``if`` bodies are not descended -- callers pair this with
    :func:`_flatten_stmts`, which already yields them.
    """
    if isinstance(stmt, ec_ast.Assign):
        return f"{stmt.var} {stmt.rhs}"
    if isinstance(stmt, ec_ast.Call):
        return f"{stmt.var} {stmt.callee} {stmt.args}"
    if isinstance(stmt, ec_ast.Sample):
        return f"{stmt.var} {stmt.distr}"
    if isinstance(stmt, ec_ast.Return):
        return stmt.expr
    if isinstance(stmt, ec_ast.If):
        return stmt.guard
    return ""


def _stmts_have_event(stmts: Sequence[ec_ast.EcStmt]) -> bool:
    """True if any call/sample occurs in ``stmts``, descending into ifs."""
    for s in stmts:
        if isinstance(s, (ec_ast.Call, ec_ast.Sample)):
            return True
        if isinstance(s, ec_ast.If) and (
            _stmts_have_event(s.then_body) or _stmts_have_event(s.else_body)
        ):
            return True
    return False


def _oracle_pending_admit(
    hop_index: int, oracle_name: str, coupling: str = ""
) -> list[str]:
    """Guided coupling-pending admit for one oracle of a multi-oracle hop.

    The post-init oracle's body is non-trivially transformed across the hop's
    canonicalization chain (``_oracle_step_tactic`` returns ``None`` for some
    leg), so the identical-state first cut cannot discharge it under the live
    state coupling.

    What this prints is generated from THIS hop -- its identity, its actual
    coupling, and the fields an entry must carry -- rather than the fill
    template it used to print, which was the tactic derived on KEMPRF
    `hop_0_challenge` in 2026-06 together with advice specific to that
    proof's shape. That text was stale wherever it appeared and actively
    misleading on the nineteen exports that are not KEMPRF: it named
    ``F.evaluate`` and ``encaps`` results that most of them do not have.

    The exporter cannot print the EC goal itself -- that needs EasyCrypt --
    so it prints how to get it and everything it does know.
    """
    lines = [
        _res_tag(ADMIT_GUIDED),
        f"(* multi-oracle hop {hop_index}, oracle {oracle_name!r}: the",
        "   per-transform chain has a leg no synthesizer closes, so the whole",
        "   oracle is left open rather than closed by a tactic that might run",
        "   without finishing.",
        "",
        "   to derive: locate this lemma by name in the .ec file, then",
        "     `bash scripts/easycrypt-goals.sh <ec_file> <line>`",
        "   and read the goal after `proc; inline *`.",
    ]
    if coupling:
        lines.append("")
        lines.append("   the coupling this oracle must preserve:")
        for line in coupling.split(" /\\ "):
            lines.append(f"     {line.strip()}")
    lines.append("")
    lines.append("   to CAPTURE the result, add an entry to the tactic store with")
    lines.append("   a derivation record -- the negative control is the field that")
    lines.append("   matters, because a tactic that merely runs proves nothing: *)")
    lines.append("admit.")
    lines.append("qed.")
    return lines


def _init_reorder_group_swaps(
    exec_body: list[ec_ast.EcStmt], keygen_callee: str, side: int = 1
) -> list[str]:
    """``swap{side}`` tactics that GROUP an interleaved keygen/sample backbone.

    The CFRG game init interleaves per index -- ``keygen_i; <projections>;
    seed_i <$ d; <NG calls>; <pack>`` -- while the reduction groups all keygens
    then all samples. To relate them (the middle leg of the functional-twin
    transitivity), the game side's keygens and samples are first moved to the
    front so both prob backbones read ``kg0, kg1, ..., s0, s1, ...``. A
    ``keygen`` call and a ``<$`` sample are glob-disjoint from the deterministic
    NG calls they cross (and from each other's locals), so moving them *up* is an
    EC-legal ``swap``; only the NG calls among themselves are swap-immovable
    (shared ``glob NG``) -- and those are never moved.

    Returns the ordered ``swap{side} <pos> <offset>`` strings (1-indexed
    executable positions, matching EC's post-``proc`` numbering for a flat body).
    Offsets are computed against a running simulation so successive swaps compose
    correctly. Returns ``[]`` when the backbone is already grouped.
    """
    return _init_group_backbone(exec_body, keygen_callee, side)[0]


def _init_group_backbone(
    exec_body: list[ec_ast.EcStmt], keygen_callee: str, side: int = 1
) -> tuple[list[str], list[ec_ast.EcStmt]]:
    """``(swaps, grouped_stmts)`` -- the grouping ``swap{side}``s plus the
    executable statement list (``Return`` dropped) after applying them. The core
    of :func:`_init_reorder_group_swaps`; the grouped statements feed the
    seq-split length and the suffix functionalization."""
    stmts: list[ec_ast.EcStmt] = [
        s for s in _exec_stmts(exec_body) if not isinstance(s, ec_ast.Return)
    ]

    def _is_keygen(i: int) -> bool:
        s = stmts[i]
        return isinstance(s, ec_ast.Call) and s.callee == keygen_callee

    def _is_sample(i: int) -> bool:
        return isinstance(stmts[i], ec_ast.Sample)

    swaps: list[str] = []

    def _group(pred: Callable[[int], bool], anchor_end: int) -> None:
        # Move every ``pred`` statement past ``anchor_end`` up to be contiguous
        # from ``anchor_end + 1``, preserving order; a statement at or before the
        # anchor stays put.
        insert_at = anchor_end + 1
        while True:
            src = next((i for i in range(insert_at, len(stmts)) if pred(i)), None)
            if src is None:
                break
            if src == insert_at:
                insert_at += 1
                continue
            swaps.append(f"swap{{{side}}} {src + 1} {insert_at - src}.")
            stmts.insert(insert_at, stmts.pop(src))
            insert_at += 1

    first_kg = next((i for i in range(len(stmts)) if _is_keygen(i)), None)
    if first_kg is None:
        return [], stmts
    proj_end = first_kg
    j = first_kg + 1
    while j < len(stmts) and isinstance(stmts[j], ec_ast.Assign):
        proj_end = j
        j += 1
    _group(_is_keygen, proj_end)
    # Group the samples so each after the first is contiguous with it -- anchor on
    # the first sample so an already-grouped body needs no swaps.
    first_s = next((i for i in range(len(stmts)) if _is_sample(i)), None)
    if first_s is not None:
        _group(_is_sample, first_s)
    return swaps, stmts


def _init_prefix_len(exec_stmts: list[ec_ast.EcStmt]) -> int:
    """1-indexed executable position of the last ``<$`` sample -- the ``seq``
    split point separating the probabilistic keygen/sample prefix from the
    deterministic NG suffix. 0 when there is no sample."""
    stmts = [s for s in exec_stmts if not isinstance(s, ec_ast.Return)]
    last = 0
    for i, s in enumerate(stmts):
        if isinstance(s, ec_ast.Sample):
            last = i + 1
    return last


def _init_functionalize_side(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    suffix: list[ec_ast.EcStmt],
    side: int,
    clone_alias: str,
    det_pred: Callable[[str, str], bool],
    seed_binders: dict[str, str],
    glob_binder: str,
    skip_leading_wp: bool,
) -> list[str]:
    """The ``call{side} (NG_<m>_det g <ev-args>)`` sequence that functionalizes
    one side's deterministic NG-call suffix, processed tail-to-front.

    A forward symbolic pass computes each call result's *functional value*
    (``generator`` -> ``<clone>.ev_generator``; ``randomscalar seed`` ->
    ``<clone>.ev_randomscalar (<seed binder>)``; ``exp r dt`` ->
    ``<clone>.ev_exp (<fv r>) (<fv dt>)``), so the tail-to-front peel can pass
    each call the functional values of its *actual* args (the det axiom's args
    are the functional values, per the validated tactic). A ``wp`` precedes each
    contiguous NG-call block to absorb the intervening packing assignments; the
    *leading* ``wp`` is skipped when ``skip_leading_wp`` (the second side's
    trailing packs were already cleared by the first side's ``wp``, which a
    relational ``wp`` absorbs on both sides). ``seed_binders`` maps each seed
    variable to its ``exists*`` binder; ``glob_binder`` is the ``(glob NG)``
    binder.
    """

    def _is_det_ng(stmt: ec_ast.EcStmt) -> tuple[str, str] | None:
        if not isinstance(stmt, ec_ast.Call):
            return None
        parts = _callee_parts(stmt.callee)
        if parts is not None and det_pred(parts[0], parts[1]):
            return parts
        return None

    exec_s = [s for s in _exec_stmts(suffix) if not isinstance(s, ec_ast.Return)]
    func_val: dict[str, str] = dict(seed_binders)

    def _fv(arg: str) -> str:
        return func_val.get(arg, seed_binders.get(arg, arg))

    for stmt in exec_s:
        parts = _is_det_ng(stmt)
        if parts is None:
            continue
        _mod, meth = parts
        args = _split_top_args(stmt.args)  # type: ignore[union-attr]
        if not args:
            func_val[stmt.var] = f"{clone_alias}.ev_{meth}"  # type: ignore[union-attr]
        else:
            joined = " ".join(f"({_fv(a)})" for a in args)
            func_val[stmt.var] = f"{clone_alias}.ev_{meth} {joined}"  # type: ignore[union-attr]

    lines: list[str] = []
    need_wp = False
    seen_call = False
    for stmt in reversed(exec_s):
        parts = _is_det_ng(stmt)
        if parts is None:
            need_wp = True
            continue
        mod, meth = parts
        if need_wp and not (skip_leading_wp and not seen_call):
            lines.append("wp.")
        need_wp = False
        seen_call = True
        arg_strs = [_fv(a) for a in _split_top_args(stmt.args)]  # type: ignore[union-attr]
        rendered = "".join(f" {x}" if " " not in x else f" ({x})" for x in arg_strs)
        lines.append(f"call{{{side}}} ({mod}_{meth}_det {glob_binder}{rendered}).")
    return lines


def _init_legmid_inv(  # pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
    game_prefix: list[ec_ast.EcStmt],
    red_prefix: list[ec_ast.EcStmt],
    keygen_callee: str,
    glob_names: list[str],
    red_mod: str,
    red_fields: set[str],
    include_ek_seam: bool = False,
) -> str | None:
    """The ``seq`` invariant for the middle leg ``FG_calls ~ FR_calls`` -- the
    coupling the aligned probabilistic prefix establishes and the deterministic
    suffix consumes. Read off the two flat prefixes:

    * glob equalities (``glob_names``);
    * per keygen index ``i``: the game's ek/dk (its prefix projection variable
      when the projection is in the prefix, else the raw ``<result>.`k``) coupled
      to the reduction's ``ek_PQ_i`` local and ``dk_PQ_i`` field, plus the
      challenger seam ``dk_PQ_i = challenger_dk_i`` (the reduction's packed-tuple
      component that also feeds the inner challenger);
    * per seed index: the game seed coupled to the reduction seed.

    Reduction *fields* (in ``red_fields``) are qualified ``red_mod.<f>``; locals
    are bare. Returns ``None`` if the reduction's keygen repack tuple cannot be
    identified (the shape does not match, so the caller admits)."""
    conj = [f"(glob {m}){{1}} = (glob {m}){{2}}" for m in glob_names]

    def _r2(var: str) -> str:
        return f"{red_mod}.{var}{{2}}" if var in red_fields else f"{var}{{2}}"

    def _game_ref(kv: str, comp: str) -> str:
        for s in game_prefix:
            if isinstance(s, ec_ast.Assign) and s.rhs.strip() == f"{kv}.{comp}":
                return f"{s.var}{{1}}"
        return f"{kv}{{1}}.{comp}"

    game_kgs = [
        s
        for s in game_prefix
        if isinstance(s, ec_ast.Call) and s.callee == keygen_callee
    ]
    game_seeds = [s.var for s in game_prefix if isinstance(s, ec_ast.Sample)]
    red_seeds = [s.var for s in red_prefix if isinstance(s, ec_ast.Sample)]
    n = len(game_kgs)

    def _red_ref(kv: str, comp: str) -> str:
        for s in red_prefix:
            if isinstance(s, ec_ast.Assign) and s.rhs.strip() == f"{kv}.{comp}":
                return _r2(s.var)
        return f"{kv}{{2}}.{comp}"

    pack: tuple[str, list[str]] | None = None
    for s in red_prefix:
        if isinstance(s, ec_ast.Assign):
            rhs = s.rhs.strip()
            if rhs.startswith("(") and rhs.endswith(")"):
                comps = _split_top_args(rhs[1:-1])
                if len(comps) == 2 * n:
                    pack = (s.var, comps)
                    break
    if pack is None:
        # R_KDF (hop_4) shape: the reduction runs the SAME direct keygens as the
        # game (no challenger repack tuple) and forwards to a keyless challenger
        # (no seam). Couple each game keygen's ek/dk projection to the matching
        # reduction keygen's, plus the seeds.
        red_kgs = [
            s
            for s in red_prefix
            if isinstance(s, ec_ast.Call) and s.callee == keygen_callee
        ]
        if len(red_kgs) != n:
            return None
        for i in range(n):
            gkv, rkv = game_kgs[i].var, red_kgs[i].var
            conj.append(f"{_game_ref(gkv, '`1')} = {_red_ref(rkv, '`1')}")
            conj.append(f"{_game_ref(gkv, '`2')} = {_red_ref(rkv, '`2')}")
        for gs, rs in zip(game_seeds, red_seeds):
            conj.append(f"{gs}{{1}} = {rs}{{2}}")
        return " /\\ ".join(conj)
    packvar, comps = pack

    def _red_proj(k: int) -> str | None:
        for s in red_prefix:
            if isinstance(s, ec_ast.Assign) and s.rhs.strip() == f"{packvar}.`{k}":
                return s.var
        return None

    for i in range(n):
        kv = game_kgs[i].var
        r_ek = _red_proj(2 * i + 1)
        r_dk = _red_proj(2 * i + 2)
        if r_ek is None or r_dk is None:
            return None
        chal = comps[2 * i + 1]
        conj.append(f"{_game_ref(kv, '`1')} = {_r2(r_ek)}")
        conj.append(f"{_game_ref(kv, '`2')} = {_r2(r_dk)}")
        conj.append(f"{_r2(r_dk)} = {_r2(chal)}")
        # The EK seam ``ek_PQ_i = challenger_ek_i`` (the reduction holds the
        # challenger's ENCAPS key too, as in the PK binding reduction). Only the
        # flat ``ev``-twin PK leg needs it in the invariant: the seam assignments
        # sit in the prefix (before the ``seq`` split), so the post's EK seam is
        # unrecoverable in the suffix unless carried here. Off by default so CT
        # (dk-only seam) stays byte-identical.
        if include_ek_seam:
            conj.append(f"{_r2(r_ek)} = {_r2(comps[2 * i])}")
    for gs, rs in zip(game_seeds, red_seeds):
        conj.append(f"{gs}{{1}} = {rs}{{2}}")
    return " /\\ ".join(conj)


def _init_legmid_tactic(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    game_body: list[ec_ast.EcStmt],
    red_body: list[ec_ast.EcStmt],
    keygen_callee: str,
    glob_names: list[str],
    red_mod: str,
    red_fields: set[str],
    clone_alias: str,
    det_pred: Callable[[str, str], bool],
) -> list[str] | None:
    """The middle-leg ``FG_calls ~ FR_calls`` tactic (hop_0 orientation: the
    interleaved game is side 1, the grouped reduction side 2).

    The two twins run the SAME keygen/sample/NG-call multiset but the reduction
    orders the NG calls differently (grouped, e.g. ``rs0; rs1; gen0; exp0; ...``)
    and they share ``glob NG`` (swap-immovable), so a lockstep peel would couple
    mismatched calls. Instead each side's NG calls are *functionalized* to their
    ``ev``-values (via ``<NG>_<m>_det``), after which the two are equal by the
    coupled seeds. Assembles: ``proc`` + grouping ``swap{1}``s (keygens+samples to
    the front) + ``seq``-split with the coupling invariant + the aligned prefix
    peel (``rnd``/``wp;call``/``auto``) + functionalize the grouped side first then
    the interleaved side (its leading ``wp`` skipped) + the tail closer. Returns
    ``None`` if the invariant cannot be built (caller admits)."""
    swaps, grouped_game = _init_group_backbone(game_body, keygen_callee, side=1)
    red_exec: list[ec_ast.EcStmt] = [
        s for s in _exec_stmts(red_body) if not isinstance(s, ec_ast.Return)
    ]
    game_plen = _init_prefix_len(grouped_game)
    red_plen = _init_prefix_len(red_exec)
    game_prefix, game_suffix = grouped_game[:game_plen], grouped_game[game_plen:]
    red_prefix, red_suffix = red_exec[:red_plen], red_exec[red_plen:]
    inv = _init_legmid_inv(
        game_prefix, red_prefix, keygen_callee, glob_names, red_mod, red_fields
    )
    if inv is None:
        return None
    game_seeds = [s.var for s in game_prefix if isinstance(s, ec_ast.Sample)]
    red_seeds = [s.var for s in red_prefix if isinstance(s, ec_ast.Sample)]
    n_kg = len(
        [
            s
            for s in game_prefix
            if isinstance(s, ec_ast.Call) and s.callee == keygen_callee
        ]
    )
    tac: list[str] = ["proc.", *swaps, f"seq {game_plen} {red_plen} : ({inv})."]
    tac += ["rnd."] * len(game_seeds)
    tac += ["wp.", "call (_: true)."] * n_kg
    tac += ["auto."]

    def _exists(side: int, seeds: list[str], glob: str, binders: list[str]) -> str:
        vs = ", ".join(f"{s}{{{side}}}" for s in seeds)
        return (
            f"exists* (glob NG){{{side}}}, {vs}; "
            f"elim* => {glob} {' '.join(binders)}."
        )

    es = [f"es{i}" for i in range(len(red_seeds))]
    tac.append(_exists(2, red_seeds, "g2", es))
    tac += _init_functionalize_side(
        red_suffix, 2, clone_alias, det_pred, dict(zip(red_seeds, es)), "g2", False
    )
    fs = [f"fs{i}" for i in range(len(game_seeds))]
    tac.append(_exists(1, game_seeds, "g1", fs))
    tac += _init_functionalize_side(
        game_suffix, 1, clone_alias, det_pred, dict(zip(game_seeds, fs)), "g1", True
    )
    # Substitute the exists*-bound seeds so the two functionalized NG suffixes
    # are syntactically equal, then discharge the packed-field couplings. ``sp``
    # runs the cross-module field writes; ``move=> /> *`` introduces the twins'
    # forall-result binders + their ``ev``-defining equations (subst-ing the
    # seed couplings) so the residual is ground -- ``smt`` on the flat residual
    # scales to the PK ``ek``+``dk`` packing, where a bare ``skip => /#`` on the
    # nested-forall goal does not.
    # ``sp`` runs the cross-module packing field writes; ``skip`` reduces the
    # (now empty) programs to ``forall &1 &2, <inv> => <post>``. The post is the
    # two functionalized NG suffixes as a deep right-nested
    # ``A && forall r, (r = ev ...) => ...`` chain; a bare ``skip => /#`` hands
    # that whole chain to ``smt`` at once, which does not scale past the CT
    # ``dk``-only coupling. Introduce the memories + the invariant hypothesis
    # first (``move => *``) so ``smt`` sees the nested chain with every seed
    # coupling already in context -- then it discharges the PK ``ek``+``dk``
    # packing too.
    tac += ["sp.", "skip.", "move => * /=.", "smt()."]
    return tac


def _ev_sig(stmt: ec_ast.EcStmt) -> tuple[str, str]:
    """The cross-side comparable event signature of one backbone statement.

    Same granularity as :func:`_bd_events` -- a call by its callee, a sample by
    its distribution -- but per-statement, so a selection sort can compare a
    statement against a target slot without rebuilding the whole list.
    """
    if isinstance(stmt, ec_ast.Call):
        return ("call", stmt.callee)
    return ("sample", cast(ec_ast.Sample, stmt).distr)


def _extra_det_target(  # pylint: disable=too-many-locals,too-many-branches
    keep_events: list[tuple[str, str]],
    extra_events: list[tuple[str, str]],
    det_pred: Callable[[str, str], bool],
    keep_droppable: Callable[[list[int]], bool] | None = None,
) -> tuple[list[tuple[str, str]], list[str]] | None:
    """Interleave two event lists that may EACH carry one-sided extras.

    Occurrences of the same signature are matched positionally (the k-th
    ``NG.exp`` on one side is the k-th on the other) up to the common count;
    anything past that is an extra on its own side. The two extra kinds are NOT
    symmetric, and the asymmetry is the whole point:

    * an ``extra_events``-side extra (the delegating reduction's) is dropped by
      its ``_det`` axiom, which pins the RESULT -- so its result may be live, and
      indeed the correctness challenger's ``decaps`` result IS the coupling's
      ``.`5``;
    * a ``keep_events``-side extra (the game's) is dropped by its ``_pres``
      axiom, which preserves the GLOB and says nothing about the result -- so it
      must be a deterministic call whose result is DEAD. Deadness is decided for
      the whole keep-side extra SET at once (``keep_droppable`` takes the list of
      candidate indices), because these extras form a CHAIN -- each feeds the
      next -- so no member is dead while the others are still present. Without
      that oracle, keep-side extras are refused rather than dropped on trust.

    Returns the target event order for the extra side (the keep side's order
    restricted to the COMMON events, with each extra re-inserted directly after
    the matched event it currently follows) and an execution-order op plan of
    ``match`` / ``dropL`` / ``dropR``. ``None`` when an extra is not droppable,
    when a keep-side extra precedes every matched event, or when there is no
    extra at all (that is the plain bundled-reorder route's shape, not this one).
    """

    def _det_call(ev: tuple[str, str]) -> bool:
        mod, dot, meth = ev[1].partition(".")
        return ev[0] == "call" and bool(dot) and det_pred(mod, meth)

    # COMMON occurrences: for each signature, the first min(#keep, #extra) of
    # them on each side. Anything past that is an extra on its own side.
    n_keep, n_extra_side = Counter(keep_events), Counter(extra_events)
    common_n = {
        sig: min(n_keep[sig], n_extra_side[sig]) for sig in n_keep | n_extra_side
    }
    keep_common: dict[tuple[str, str], list[int]] = {}
    keep_drop: list[int] = []
    seen_k: Counter[tuple[str, str]] = Counter()
    for k, ev in enumerate(keep_events):
        if seen_k[ev] < common_n.get(ev, 0):
            keep_common.setdefault(ev, []).append(k)
        else:
            # A keep-side extra is dropped ONE-SIDEDLY by its glob-preservation
            # axiom, which says nothing about the result -- so it must be a
            # deterministic call whose result is DEAD once the WHOLE extra set is
            # gone. Deadness is decided for the set, not per call: these form a
            # CHAIN (each feeds the next), so no member is dead on its own.
            if not _det_call(ev):
                return None
            keep_drop.append(k)
        seen_k[ev] += 1
    if keep_drop and (keep_droppable is None or not keep_droppable(keep_drop)):
        return None

    seen_e: Counter[tuple[str, str]] = Counter()
    extras_at: dict[int, list[tuple[str, str]]] = {}
    n_extra = 0
    # Walk the extra side, classifying each event as matched (its positional
    # occurrence is a COMMON one) or extra. An extra is placed after the
    # KEEP-side position of the matched event it currently follows -- not after
    # the count of matched events seen, which is a different index whenever the
    # two orders differ (and they always do here, or there would be nothing to
    # align).
    last = -1
    for ev in extra_events:
        idx = seen_e[ev]
        seen_e[ev] += 1
        where = keep_common.get(ev, [])
        if idx < len(where):
            last = where[idx]
            continue
        if not _det_call(ev):
            return None
        if last < 0:
            # An extra before every matched event: the selection sort places
            # blocks after an already-placed event, so it cannot express this.
            return None
        extras_at.setdefault(last, []).append(ev)
        n_extra += 1
    if n_extra == 0 and not keep_drop:
        return None
    # The delegate's alignment target holds only the COMMON keep events (it has
    # no counterpart for a keep-side drop), with its own extras re-inserted.
    target: list[tuple[str, str]] = []
    for k, ev in enumerate(keep_events):
        if k in set(keep_drop):
            continue
        target.append(ev)
        target.extend(extras_at.get(k, []))
    # Execution-order op plan, driven by the keep side's own order.
    ops: list[str] = []
    drop_set = set(keep_drop)
    for k, _ev in enumerate(keep_events):
        if k in drop_set:
            ops.append("dropL")
            continue
        ops.append("match")
        ops.extend(["dropR"] * len(extras_at.get(k, [])))
    return target, ops


def _delegate_mid_peel(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches,too-many-statements,too-many-return-statements
    l_exec: list[ec_ast.EcStmt],
    r_exec: list[ec_ast.EcStmt],
    mods: tuple[str, str],
    fields: tuple[set[str], set[str]],
    glob_names: list[str],
    det_pred: Callable[[str, str], bool],
    clone_alias: dict[str, str],
    game_droppable: Callable[[list[int]], bool] | None = None,
) -> tuple[list[str], set[tuple[str, str]]] | None:
    """The FLAT ``FGd ~ FRd`` middle leg for a bundled-delegate init hop.

    Side 1 is always the GAME and side 2 the delegating REDUCTION -- the caller
    normalises that (with ``symmetry.`` when the reduction is on the left), so
    this walks one orientation only.

    Applied to concrete flat-state modules (``proc.`` -- no ``inline *``), so the
    local names are exactly what EC sees; the raw-wrapper legs never need an
    inline-name prediction.

    Shape: align the reduction's events to the game's (:func:`_event_align_swaps`
    over a target from :func:`_extra_det_target`), then walk FORWARD with ``seq``
    only as far as the last one-sided drop -- functionalizing every deterministic
    call on both sides through its ``_det`` axiom -- and finish the aligned
    remainder with the plain tail-first ``(wp; couple)*`` ladder. Stopping the
    forward walk at the last drop is what keeps the running invariant small: the
    tail carries no ``ev_`` fact, so its statements never enter the accumulated
    conjunction.

    The two drop kinds differ, and the difference is load-bearing. A REDUCTION
    extra goes through its ``_det`` axiom, which pins the result -- so dropping
    it is also what STATES the ``ev_`` conjunct the coupling asserts about it. A
    GAME extra goes through its ``_pres`` axiom, which preserves the glob and
    says NOTHING about the result, so it is admissible only when that result is
    dead; ``game_droppable`` is the caller's liveness oracle and the returned set
    names the ``_pres`` axioms the tactic uses.

    Returns ``(tactic, pres_requests)``, or ``None`` off-shape (unalignable, an
    unknown clone alias, a non-assignment non-event statement) so the caller
    emits an honest admit."""
    l_mod, r_mod = mods
    l_flds, r_flds = fields
    l_events = [_ev_sig(s) for s in l_exec if _is_bb_stmt(s)]
    r_events = [_ev_sig(s) for s in r_exec if _is_bb_stmt(s)]
    got = _extra_det_target(l_events, r_events, det_pred, game_droppable)
    if got is None:
        return None
    target, ops = got
    aligned = _event_align_swaps(r_exec, target, 2)
    if aligned is None:
        return None
    swaps, r_exec = aligned

    l_names = {v for s in l_exec if (v := _stmt_var(s))} - l_flds
    r_names = {v for s in r_exec if (v := _stmt_var(s))} - r_flds

    def _ref(var: str, side: int) -> str:
        flds = l_flds if side == 1 else r_flds
        mod = l_mod if side == 1 else r_mod
        return f"{mod}.{var}{{{side}}}" if var in flds else f"{var}{{{side}}}"

    def _tag(expr: str, side: int) -> str:
        """``expr`` with every identifier it BINDS on ``side`` memory-tagged.

        A field is qualified by its flat module; a local is bare. An identifier
        the side does not bind (an operator name, a clone-qualified ``ev_``) is
        left alone -- it means the same thing in both memories.
        """
        names = (l_names | l_flds) if side == 1 else (r_names | r_flds)

        def _one(m: re.Match[str]) -> str:
            tok = m.group(0)
            return _ref(tok, side) if tok in names else tok

        return re.sub(r"[A-Za-z_]\w*", _one, expr)

    conj: list[str] = ["={" + ", ".join(f"glob {m}" for m in glob_names) + "}"]

    def _inv() -> str:
        return " /\\ ".join(conj)

    def _pr(e: str) -> str:
        e = e.strip()
        return e if e.startswith("(") and e.endswith(")") else f"({e})"

    def _det_block(stmt: ec_ast.Call, side: int, ctr: int) -> list[str] | None:
        parts = _callee_parts(stmt.callee)
        if parts is None or parts[0] not in clone_alias:
            return None
        mod, meth = parts
        cargs = _split_top_args(stmt.args)
        applied = "".join(f" {_pr(_tag(a, side))}" for a in cargs)
        conj.append(
            f"{_ref(stmt.var or '_', side)} = ({clone_alias[mod]}.ev_{meth}{applied})"
        )
        bs = [f"g{ctr}_{side}"] + [f"a{ctr}_{side}_{k}" for k in range(len(cargs))]
        cap = ", ".join(
            [f"(glob {mod}){{{side}}}"] + [f"{_pr(_tag(a, side))}" for a in cargs]
        )
        return [
            f"exists* {cap}; elim* => {' '.join(bs)}.",
            f"call{{{side}}} ({mod}_{meth}_det {' '.join(bs)}).",
        ]

    pres: set[tuple[str, str]] = set()

    def _pres_block(stmt: ec_ast.Call, ctr: int) -> list[str] | None:
        """One-sided GAME drop through the glob-preservation axiom."""
        parts = _callee_parts(stmt.callee)
        if parts is None:
            return None
        mod, meth = parts
        pres.add((mod, meth))
        return [
            f"exists* (glob {mod})" "{1}" f"; elim* => p{ctr}.",
            f"call{{1}} ({mod}_{meth}_pres p{ctr}).",
        ]

    tac: list[str] = ["proc.", *swaps]
    li = ri = 0
    ctr = 0
    op_i = 0
    n_drops_left = sum(1 for o in ops if o != "match")
    while n_drops_left > 0:
        if op_i >= len(ops):
            return None
        l_at = l_exec[li] if li < len(l_exec) else None
        r_at = r_exec[ri] if ri < len(r_exec) else None
        if isinstance(l_at, ec_ast.Assign) or isinstance(r_at, ec_ast.Assign):
            a = b = 0
            while li + a < len(l_exec) and isinstance(l_exec[li + a], ec_ast.Assign):
                st = cast(ec_ast.Assign, l_exec[li + a])
                conj.append(f"{_ref(st.var, 1)} = {_tag(st.rhs, 1)}")
                a += 1
            while ri + b < len(r_exec) and isinstance(r_exec[ri + b], ec_ast.Assign):
                st = cast(ec_ast.Assign, r_exec[ri + b])
                conj.append(f"{_ref(st.var, 2)} = {_tag(st.rhs, 2)}")
                b += 1
            tac.append(f"seq {a} {b} : ({_inv()}).")
            tac.append("+ wp; skip => /#.")
            li += a
            ri += b
            continue
        op = ops[op_i]
        if op == "dropR":
            # Reduction-side extra: the ``_det`` drop, which also states the
            # coupling's ``ev_`` fact about the dropped call's result.
            if not isinstance(r_at, ec_ast.Call):
                return None
            blk = _det_block(r_at, 2, ctr)
            if blk is None:
                return None
            ctr += 1
            n_drops_left -= 1
            op_i += 1
            ri += 1
            tac.append(f"seq 0 1 : ({_inv()}).")
            tac.append("+ " + " ".join(blk) + " skip => /#.")
            continue
        if op == "dropL":
            # Game-side extra: DEAD result (checked by the caller's oracle), so
            # the glob-preserving ``_pres`` drop is what applies.
            if not isinstance(l_at, ec_ast.Call):
                return None
            blk = _pres_block(l_at, ctr)
            if blk is None:
                return None
            ctr += 1
            n_drops_left -= 1
            op_i += 1
            li += 1
            tac.append(f"seq 1 0 : ({_inv()}).")
            tac.append("+ " + " ".join(blk) + " skip => /#.")
            continue
        if not isinstance(l_at, (ec_ast.Call, ec_ast.Sample)) or not isinstance(
            r_at, (ec_ast.Call, ec_ast.Sample)
        ):
            return None
        op_i += 1
        if isinstance(l_at, ec_ast.Sample):
            conj.append(
                f"{_ref(l_at.var, 1)} = {_ref(cast(ec_ast.Sample, r_at).var, 2)}"
            )
            tac.append(f"seq 1 1 : ({_inv()}).")
            tac.append("+ rnd; skip => /#.")
        else:
            l_call, r_call = l_at, cast(ec_ast.Call, r_at)
            parts = _callee_parts(l_call.callee)
            if parts is not None and det_pred(*parts):
                b1 = _det_block(l_call, 1, ctr)
                b2 = _det_block(r_call, 2, ctr)
                if b1 is None or b2 is None:
                    return None
                ctr += 1
                tac.append(f"seq 1 1 : ({_inv()}).")
                tac.append("+ " + " ".join(b1 + b2) + " skip => /#.")
            else:
                conj.append(
                    f"{_ref(l_call.var or '_', 1)} = {_ref(r_call.var or '_', 2)}"
                )
                tac.append(f"seq 1 1 : ({_inv()}).")
                tac.append("+ call (_: true); skip => /#.")
        li += 1
        ri += 1
    # Aligned remainder: the plain tail-first ladder. Both sides hold the same
    # events from here on, so the peel is sized off either.
    tail = [s for s in l_exec[li:] if _is_bb_stmt(s)]
    if len(tail) != len([s for s in r_exec[ri:] if _is_bb_stmt(s)]):
        return None
    for stmt in reversed(tail):
        tac.append("wp.")
        tac.append("call (_: true)." if isinstance(stmt, ec_ast.Call) else "rnd.")
    tac.append("wp.")
    tac.append("skip => /#.")
    return tac, pres


def _stmt_var(stmt: ec_ast.EcStmt) -> str:
    """The variable a statement binds, or ``""`` for one that binds none."""
    if isinstance(stmt, (ec_ast.Call, ec_ast.Sample, ec_ast.Assign)):
        return stmt.var or ""
    return ""


def _coupling_base_for(coupling: str, flds: list[str], side: int) -> str | None:
    """The module base a coupling names on ``side``, read off one of its FIELDS.

    Structural, not name-keyed: the field names come from the rendered flat
    state, and the base is whatever qualifier the coupling attaches to one of
    them. Returns ``None`` when no field of that side appears in the coupling.
    """
    for f in flds:
        m = re.search(
            rf"([A-Za-z_][\w.]*)\.{re.escape(f)}(?:\.`\d+)*\{{{side}\}}", coupling
        )
        if m is not None:
            return m.group(1)
    return None


def _all_extras_dead(
    mod: ec_ast.Module,
    own: Counter[tuple[str, str]],
    other: Counter[tuple[str, str]],
    droppable: Callable[[list[int]], bool],
) -> bool:
    """Whether every event ``mod`` has in EXCESS of ``other`` is droppable.

    The orientation test for a hop with extras on both sides: the GAME's extras
    are its dead KDF chain (droppable through ``_pres``), the REDUCTION's is the
    challenger's ``decaps``, whose result the coupling asserts about. Deciding it
    by LIVENESS rather than by name keeps the choice structural.
    """
    body = [
        t for t in _exec_stmts(mod.procs[0].body) if not isinstance(t, ec_ast.Return)
    ]
    events = [_ev_sig(t) for t in body if _is_bb_stmt(t)]
    common = {sig: min(own[sig], other[sig]) for sig in own}
    seen: Counter[tuple[str, str]] = Counter()
    extras: list[int] = []
    for k, ev in enumerate(events):
        if seen[ev] >= common.get(ev, 0):
            extras.append(k)
        seen[ev] += 1
    return bool(extras) and droppable(extras)


def _synth_delegate_correctness_init(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-return-statements
    modules: mt.ModuleTranslator,
    oracle_name: str,
    left_state0: frog_ast.Game,
    right_state0: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
    det_methods: dict[str, set[str]],
    clone_alias: dict[str, str],
    full_coupling: str,
    hop_index: int = 0,
) -> tuple[list[str], list[str], set[tuple[str, str]]] | None:
    """``RawGame ~ FGd ~ FRd ~ RawReduction`` transitivity for an init hop whose
    reduction delegates a BUNDLED block to a challenger that runs one EXTRA
    deterministic call, and whose coupling therefore asserts an ``ev_``
    characterization of that call's result.

    The IND-CCA `_PQ` correctness-reduction shape (``hop_0_initialize`` of
    ``CG_expanded_INDCCA_PQ`` and its `_PQ` siblings): the game runs
    ``keygen; <T-derivation>; encaps`` while the reduction's
    ``KEMCorrectnessWithDK`` challenger runs ``keygen; encaps; decaps`` back to
    back and the reduction then re-derives its own T scalar. So the two bodies
    are a permutation PLUS a one-sided ``decaps`` whose result is LIVE (it is the
    correctness tuple's ``.`5``) -- which is why the plain bundled-delegate
    reorder declines (it drops only DEAD samples) and why the backbone peel's
    ``_pres`` drop does not apply (``_pres`` forgets the result).

    Everything the coupling asserts functionally is proved on the FLAT twins,
    whose local names the exporter controls; the two raw-wrapper legs are the
    ordinary name-independent backbone peel. ``None`` off-shape -- so every
    other init stays byte-identical and the caller emits its honest admit."""
    if "ev_" not in full_coupling or not clone_alias:
        return None
    lproj = _project_to_method(left_state0, oracle_name)
    rproj = _project_to_method(right_state0, oracle_name)
    if lproj is None or rproj is None:
        return None
    fg_name, fr_name = f"FGd_{hop_index}", f"FRd_{hop_index}"

    def _det_pred(mod: str, meth: str) -> bool:
        return meth in det_methods.get(mod, set())

    def _build(proj: frog_ast.Game, name: str) -> ec_ast.Module:
        # ``no_shadow_fields``: a reduction whose ``Initialize`` writes a field
        # of its own (the correctness reduction's ``seed_T``) otherwise gets a
        # LOCAL of the same name declared alongside the module var, and the local
        # shadows it -- the field is then never written, so both the middle leg's
        # ``<mod>.<f>`` invariant and the outer leg's field coupling are
        # unprovable (measured: EC rejected the ``rnd`` step's ``skip => /#``).
        return _flat_state_module(
            modules,
            name,
            proj,
            external_module_types,
            method_return_types,
            flat_params,
            emit_state_vars=True,
            no_shadow_fields=True,
        )

    l_probe, r_probe = _build(lproj, "L_probe"), _build(rproj, "R_probe")
    if not l_probe.procs or not r_probe.procs:
        return None

    def _exec_of(mod: ec_ast.Module) -> list[ec_ast.EcStmt]:
        return [
            s
            for s in _exec_stmts(mod.procs[0].body)
            if not isinstance(s, ec_ast.Return)
        ]

    def _droppable_oracle(mod: ec_ast.Module) -> Callable[[list[int]], bool]:
        """``ks -> are ALL those backbone events droppable TOGETHER?``

        Set-level on purpose, and it does not hand-roll the analysis. Two traps
        made a naive check wrong, and both were measured on the game side of
        `hop_15_initialize`, whose whole KDF chain is dead:

        * :func:`_live_out` is per-statement and a dead CALL still keeps its
          arguments live (the call executes; only a pure assignment can be
          deleted). So in a chain where each call feeds the next, exactly ONE
          member tests dead in isolation and every upstream member looks live.
        * Non-event statements between them -- the `kdf_in <- concat(...)`
          plumbing -- are not dropped by the tactic, yet are themselves dead once
          the chain goes, so they must not be counted as live readers.

        Both dissolve by asking the question on the REDUCED body: delete the
        candidate calls, then let :func:`_live_out` (which already elides dead
        pure assignments, and is component-precise about `v.`k`) report what is
        live at the top. A candidate is droppable exactly when its result is not
        live there -- i.e. nothing surviving still needs it. A call whose result
        is a module FIELD is refused outright: a field is observable in the post,
        so it is never dead.
        """
        body = list(_exec_stmts(mod.procs[0].body))
        events = [t for t in body if _is_bb_stmt(t)]
        flds = {v.name for v in mod.module_vars}

        def _ok(ks: list[int]) -> bool:
            if not ks or any(k >= len(events) for k in ks):
                return False
            dropped = {id(events[k]) for k in ks}
            gone = {v for k in ks if (v := _stmt_var(events[k]))}
            if len(gone) != len(ks) or gone & flds:
                return False
            reduced: list[ec_ast.EcStmt] = [ec_ast.Assign("__pf_seed", "0")]
            reduced += [t for t in body if id(t) not in dropped]
            if flds:
                reduced.append(ec_ast.Return("(" + ", ".join(sorted(flds)) + ")"))
            live_at_top = _live_out(reduced)[0]
            return not any(
                t == v or t.startswith(f"{v}.`") for v in gone for t in live_at_top
            )

        return _ok

    l_ev = Counter(_ev_sig(s) for s in _exec_of(l_probe) if _is_bb_stmt(s))
    r_ev = Counter(_ev_sig(s) for s in _exec_of(r_probe) if _is_bb_stmt(s))
    l_extra, r_extra = l_ev - r_ev, r_ev - l_ev
    if not l_extra and not r_extra:
        return None
    # Orientation. Side 2 is always the delegating REDUCTION (``symmetry.``
    # flips it in below), and the two sides' extras are told apart by LIVENESS,
    # not by name: the reduction's extra is the challenger's ``decaps``, whose
    # result IS the coupling's correctness component, while the game's extras
    # are its dead KDF chain. With extras on ONE side only, that side is the
    # reduction -- which is exactly the c257 behaviour, so those twelve exports
    # stay byte-identical.
    if not l_extra:
        game_is_left = True
    elif not r_extra:
        game_is_left = False
    else:
        l_dead = _all_extras_dead(l_probe, l_ev, r_ev, _droppable_oracle(l_probe))
        r_dead = _all_extras_dead(r_probe, r_ev, l_ev, _droppable_oracle(r_probe))
        if l_dead == r_dead:
            return None
        game_is_left = l_dead
    game_proj, red_proj = (lproj, rproj) if game_is_left else (rproj, lproj)
    fgmod, frmod = _build(game_proj, fg_name), _build(red_proj, fr_name)
    if not fgmod.procs or not frmod.procs:
        return None
    game_body, red_body = _exec_of(fgmod), _exec_of(frmod)
    game_flds = [v.name for v in fgmod.module_vars]
    red_flds = [v.name for v in frmod.module_vars]
    glob_names = [p.name for p in flat_params]
    if not glob_names:
        return None

    def _flip_sides(s: str) -> str:
        return s.replace("{1}", "\x00").replace("{2}", "{1}").replace("\x00", "{2}")

    coupling = full_coupling if game_is_left else _flip_sides(full_coupling)
    conj = [p.strip() for p in coupling.split(" /\\ ")]
    globs = " /\\ ".join(p for p in conj if p.startswith("={glob"))
    body = " /\\ ".join(p for p in conj if not p.startswith("={glob"))
    game_base = _coupling_base_for(coupling, game_flds, 1)
    red_base = _coupling_base_for(coupling, red_flds, 2)
    # ``game_base`` may legitimately be absent: a coupling that says nothing
    # about the GAME's fields (the seedbased `_PQ` hops carry only the
    # challenger's ``ev_decaps`` invariant) needs no game-side field equalities
    # in ``q1`` -- the transitivity still composes, because everything the final
    # post asserts is about the reduction. ``red_base`` is not optional the same
    # way: ``q4`` is what carries the flat twin's fields back to the real module.
    if not globs or not body or red_base is None:
        return None
    got_mid = _delegate_mid_peel(
        game_body,
        red_body,
        (fg_name, fr_name),
        (set(game_flds), set(red_flds)),
        glob_names,
        _det_pred,
        clone_alias,
        _droppable_oracle(fgmod),
    )
    if got_mid is None:
        return None
    mid, pres = got_mid
    args = ", ".join(glob_names)
    res_eq = "res{1} = res{2}"
    q1_eqs = (
        [f"{game_base}.{f}{{1}} = {fg_name}.{f}{{2}}" for f in game_flds]
        if game_base is not None
        else []
    )
    q1 = " /\\ ".join([globs, *q1_eqs, res_eq])
    body_fg = body if game_base is None else body.replace(game_base, fg_name)
    q2 = f"{body_fg} /\\ {globs} /\\ {res_eq}"
    q3 = f"{body_fg.replace(red_base, fr_name)} /\\ {globs} /\\ {res_eq}"
    q4 = (
        f"{globs} /\\ "
        + " /\\ ".join(f"{fr_name}.{f}{{1}} = {red_base}.{f}{{2}}" for f in red_flds)
        + f" /\\ {res_eq}"
    )

    def _outer_leg(b: list[ec_ast.EcStmt]) -> list[str]:
        leg = ["proc.", "inline *.", *_backbone_peel(b)]
        if _leads_with_det(b):
            leg.append("wp.")
        leg.append("auto.")
        return leg

    outer = [
        _res_tag(SYNTH_PARAM),
        *([] if game_is_left else ["symmetry."]),
        f"transitivity {fg_name}({args}).{oracle_name} "
        f"({globs} ==> {q1}) ({globs} ==> {q2}).",
        "smt().",
        "smt().",
        *_outer_leg(game_body),
        f"transitivity {fr_name}({args}).{oracle_name} "
        f"({globs} ==> {q3}) ({globs} ==> {q4}).",
        "smt().",
        "smt().",
        *mid,
        *_outer_leg(red_body),
        "qed.",
    ]
    extra = [
        "\n".join(_render_module_decl(fgmod)),
        "\n".join(_render_module_decl(frmod)),
    ]
    return extra, outer, pres


def _synth_init_plain_reorder(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-return-statements,too-many-branches
    modules: mt.ModuleTranslator,
    oracle_name: str,
    left_state0: frog_ast.Game,
    right_state0: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
    det_methods: dict[str, set[str]],
    clone_alias: dict[str, str],
    plain_coupling: str | None,
    hop_index: int = 0,
) -> tuple[list[str], list[str], set[tuple[str, str]]] | None:
    """Plain-coupling FULLY-deterministic reorder init route (DIFFKEY
    hop_6/8_initialize). Two reductions run the SAME keygen/NG-call multiset --
    ALL of it deterministic (no abstract keygen, unlike hop_0/4) -- in interleaved
    vs grouped order, coupled by plain 1:1 field equalities (so
    ``_decomposition_coupling`` returns None and the decomposition reorder route
    declines). Structure: ``RawGame ~ FG_calls ~ FR_calls ~ RawReduction`` with the
    middle ``FG_calls ~ FR_calls`` routed through ev-twins
    ``FG_calls ~ FG_ev ~ FR_ev ~ FR_calls`` -- the outer legs backbone-peel
    (:func:`_backbone_peel`), the twin sub-legs functionalize each side's det calls
    top-down (:func:`_init_topdown_leg`, field-aware), and the flat ``FG_ev ~ FR_ev``
    middle regroups the interleaved twin's samples then ``wp; rnd*; skip`` (both
    already functionalized -- no freeze). Validated end-to-end:
    ``ec_templates`` field-reorder tripwire. Fed the hop's ``full_coupling``.
    ``None`` off-shape (caller emits the honest backbone admit)."""
    if plain_coupling is None:
        return None
    fg_name = f"FG_calls_{hop_index}"
    fr_name = f"FR_calls_{hop_index}"
    lproj = _project_to_method(left_state0, oracle_name)
    rproj = _project_to_method(right_state0, oracle_name)
    if lproj is None or rproj is None:
        return None

    def _det_pred(mod: str, meth: str) -> bool:
        return meth in det_methods.get(mod, set())

    def _all_det(body: list[ec_ast.EcStmt]) -> bool:
        for s in _exec_stmts(body):
            if isinstance(s, ec_ast.Call):
                parts = _callee_parts(s.callee)
                if parts is None or not _det_pred(*parts):
                    return False
        return True

    def _grouped(body: list[ec_ast.EcStmt]) -> bool:
        seen_call = False
        for s in _exec_stmts(body):
            if isinstance(s, ec_ast.Call):
                seen_call = True
            elif isinstance(s, ec_ast.Sample) and seen_call:
                return False
        return True

    def _build(proj: frog_ast.Game, name: str) -> ec_ast.Module | None:
        m = _flat_state_module(
            modules,
            name,
            proj,
            external_module_types,
            method_return_types,
            flat_params,
            emit_state_vars=True,
            no_shadow_fields=True,
        )
        return m if m.procs else None

    lmod = _build(lproj, fg_name)
    rmod = _build(rproj, fr_name)
    if lmod is None or rmod is None:
        return None
    l_body0, r_body0 = lmod.procs[0].body, rmod.procs[0].body
    # Both sides must be FULLY deterministic (this route's distinguishing shape --
    # the abstract-keygen reorder is the decomposition route's job) and a genuine
    # interleaved-vs-grouped reorder.
    if not _all_det(l_body0) or not _all_det(r_body0):
        return None
    l_grouped, r_grouped = _grouped(l_body0), _grouped(r_body0)
    if l_grouped == r_grouped:
        return None
    game_is_left = not l_grouped  # the interleaved side is the "game"
    if game_is_left:
        fgmod, frmod = lmod, rmod
    else:
        fg = _build(rproj, fg_name)
        fr = _build(lproj, fr_name)
        if fg is None or fr is None:
            return None
        fgmod, frmod = fg, fr
    game_body, red_body = fgmod.procs[0].body, frmod.procs[0].body
    ng_mod = next(
        (
            _callee_parts(c)[0]  # type: ignore[index]
            for k, c in _call_sample_backbone(game_body)
            if k == "call"
            and c is not None
            and (p := _callee_parts(c)) is not None
            and _det_pred(*p)
        ),
        None,
    )
    if ng_mod is None or ng_mod not in clone_alias:
        return None

    def _flip_sides(s: str) -> str:
        return s.replace("{1}", "\x00").replace("{2}", "{1}").replace("\x00", "{2}")

    coupling = plain_coupling if game_is_left else _flip_sides(plain_coupling)
    conj = [p.strip() for p in coupling.split(" /\\ ")]
    globs = " /\\ ".join(p for p in conj if p.startswith("={glob"))
    if not globs:
        return None
    if any(re.match(r"^\S+\{1\} = \(.+\)\{2\}$", cj) for cj in conj):
        return None  # a packed-key decomposition is the other route's shape
    game_base: str | None = None
    red_base: str | None = None
    for cj in conj:
        m = re.match(r"^([\w.]+)\.\w+\{2\} = ([\w.]+)\.\w+\{1\}$", cj)
        if m is not None:
            red_base, game_base = m.group(1), m.group(2)
            break
    if game_base is None or red_base is None:
        return None
    game_flds = [v.name for v in fgmod.module_vars]
    red_flds = [v.name for v in frmod.module_vars]
    glob_names = [p.name for p in flat_params]
    # ``glob_items`` seeds the topdown-leg seq invariant. It must carry EVERY
    # coupled glob module (not just the functor params): globs like the shared RO
    # ``Hybrid_c.RO_G_RO`` are in the leg post (via ``globs``) and untouched by the
    # init, so their coupling has to ride the invariant or the final ``skip`` can't
    # discharge it. Parse them from ``globs`` rather than ``flat_params``.
    glob_items = [f"glob {m}" for m in re.findall(r"=\{glob ([\w.]+)\}", globs)]
    args = ", ".join(glob_names)
    res_eq = "res{1} = res{2}"

    def _fg(s: str) -> str:
        return s.replace(game_base, fg_name)

    def _fr(s: str) -> str:
        return _fg(s).replace(red_base, fr_name)

    # The RAW reduction modules (``game_base``/``red_base``) hold only their own
    # fields; the flat states additionally carry ``challenger_<f>`` fields (the
    # inlined challenger's state), which the raw modules lack. Couple only the
    # own fields at the raw<->flat seam (q1/q4); the ``challenger_`` fields are
    # flat-state-internal and are threaded within the flat twins (qa/qd).
    game_own = [f for f in game_flds if not f.startswith("challenger_")]
    red_own = [f for f in red_flds if not f.startswith("challenger_")]
    q1_eqs = " /\\ ".join(
        f"{game_base}.{f}{{1}} = {fg_name}.{f}{{2}}" for f in game_own
    )
    q4_eqs = " /\\ ".join(f"{fr_name}.{f}{{1}} = {red_base}.{f}{{2}}" for f in red_own)
    # Partition the coupling by memory side. A conjunct touching ONLY ``{1}`` is a
    # game-side (raw memory-1) fact -- e.g. the challenger seam ``game.s{1} =
    # chal.dk{1}``; it belongs in ``q1`` (established by the RawGame~FG_calls leg),
    # NOT in the cross-side body: renamed into the middle memory it would reference
    # the uncoupled challenger glob at ``{m}``. Symmetrically ``{2}``-only facts go
    # in ``q4``. Cross-side (``{1}`` and ``{2}``) conjuncts thread through q2/q3.
    non_glob = [p for p in conj if not p.startswith("={glob")]
    seam1 = [cj for cj in non_glob if "{1}" in cj and "{2}" not in cj]
    seam2 = [cj for cj in non_glob if "{2}" in cj and "{1}" not in cj]
    cross = " /\\ ".join(cj for cj in non_glob if "{1}" in cj and "{2}" in cj)
    q1 = " /\\ ".join([p for p in [globs, q1_eqs] if p] + seam1 + [res_eq])
    q4 = " /\\ ".join([p for p in [globs, q4_eqs] if p] + seam2 + [res_eq])
    q2 = " /\\ ".join([p for p in [_fg(cross)] if p] + seam2 + [globs, res_eq])
    q3 = " /\\ ".join(
        [p for p in [_fr(cross)] if p] + [_fr(c) for c in seam2] + [globs, res_eq]
    )

    # Nested middle ``FG_calls ~ FR_calls`` via ev-twins.
    fgev_name = f"FG_ev_{hop_index}"
    frev_name = f"FR_ev_{hop_index}"

    def _clone_of(m: str) -> str | None:
        return clone_alias.get(m)

    fgev = _ev_twin_module(fgmod, fgev_name, _det_pred, _clone_of)
    frev = _ev_twin_module(frmod, frev_name, _det_pred, _clone_of)
    qa = (
        globs
        + "".join(f" /\\ {fg_name}.{f}{{1}} = {fgev_name}.{f}{{2}}" for f in game_flds)
        + f" /\\ {res_eq}"
    )
    qd = (
        globs
        + "".join(f" /\\ {frev_name}.{f}{{1}} = {fr_name}.{f}{{2}}" for f in red_flds)
        + f" /\\ {res_eq}"
    )
    qb = q3.replace(fg_name, fgev_name)
    qc = qb.replace(fr_name, frev_name)
    ctr = [0]
    leg_a = _init_topdown_leg(
        game_body,
        1,
        glob_items,
        _det_pred,
        ctr,
        fg_name,
        fgev_name,
        set(game_flds),
        closer="skip => /#.",
    )
    leg_c = _init_topdown_leg(
        red_body,
        2,
        glob_items,
        _det_pred,
        ctr,
        frev_name,
        fr_name,
        set(red_flds),
        closer="skip => /#.",
    )
    # ``FG_ev`` (interleaved, does KeyGen) and ``FR_ev`` (grouped, samples the key
    # directly) hold the SAME sample DISTRIBUTIONS but in different orders AND under
    # different variable names (``KeyGen_seed0`` vs ``s_PQ_0``, both the KEM seed
    # distribution). A positional ``rnd`` pairs incompatible supports; instead align
    # ``FG_ev``'s samples to ``FR_ev``'s DISTRIBUTION order with the stable,
    # dexcepted-normalizing front-hoist, then peel: ``wp`` clears the ev glue, one
    # ``rnd`` per (now distribution-aligned) sample couples them.
    fg_samples = [
        (s.var, s.distr)
        for s in _exec_stmts(fgev.procs[0].body)
        if isinstance(s, ec_ast.Sample)
    ]
    fr_target = [
        s.distr for s in _exec_stmts(frev.procs[0].body) if isinstance(s, ec_ast.Sample)
    ]
    align_swaps = _front_swaps_stable(fg_samples, fr_target, 1)
    if align_swaps is None:
        return None
    mid = [
        "proc.",
        *align_swaps,
        "wp.",
        *(["rnd."] * len(fg_samples)),
        "skip => /#.",
    ]
    legmid = [
        f"transitivity {fgev_name}({args}).initialize "
        f"({globs} ==> {qa}) ({globs} ==> {qb}).",
        "smt().",
        "smt().",
        *leg_a,
        f"transitivity {frev_name}({args}).initialize "
        f"({globs} ==> {qc}) ({globs} ==> {qd}).",
        "smt().",
        "smt().",
        *mid,
        *leg_c,
    ]

    def _hoare_arm(mem: list[str], b: list[ec_ast.EcStmt]) -> list[str]:
        # Close a conseq hoare arm. A TRIVIAL (``true``) side is a degenerate
        # phoare that ``proc`` rejects -- close it directly with ``auto``. A real
        # seam side is ``hoare[body : _ ==> seam]``: ``proc; inline*``, then peel
        # (``auto`` clears the deterministic runs + samples, ``call (_: true)`` each
        # abstract call -- the seam field-equality is independent of the results).
        if not mem:
            return ["auto."]
        # Count-INDEPENDENT peel: ``do!`` repeats ``call (_: true); auto`` until no
        # abstract call remains (EC's inlined call count can differ from the flat
        # state's, so a fixed count over/under-peels and spills into the next goal).
        del b  # kept for signature parity
        return ["proc.", "inline *.", "auto.", "do! (call (_: true); auto)."]

    def _outer_leg(
        b: list[ec_ast.EcStmt], relational: str, mem1: list[str], mem2: list[str]
    ) -> list[str]:
        # RawGame IS the inlined flat state, so ``proc; inline*; sim`` proves the
        # RELATIONAL cross-module field couplings (incl. ``={res}``) directly -- no
        # monster, no smt-size wall. A single-memory SEAM (``game.s{1} =
        # challenger.dk{1}``) defeats ``sim``, so split it off with ``conseq
        # <equiv> <hoare_left> <hoare_right>``: ``sim`` the relational equiv,
        # discharge each seam as a one-sided hoare. The ``conseq`` runs after a bare
        # ``proc`` (NOT ``inline*``) so ``res`` -- the returned pk tuple -- is still
        # bound in the relational post; each arm then ``inline*``s before closing.
        if not mem1 and not mem2:
            return ["proc.", "inline *.", "sim."]
        # The hoare arms are SINGLE-memory: strip the ``{1}``/``{2}`` suffixes the
        # seam conjuncts carry (they came from the relational coupling). ``conseq``
        # runs at the EQUIV level (before ``proc``) so ``res`` -- the returned pk
        # tuple -- is still bound in the relational post; each arm then ``proc;
        # inline*``s before closing (order: implication, left hoare, right hoare,
        # relational equiv).
        m1 = " /\\ ".join(c.replace("{1}", "") for c in mem1) if mem1 else "true"
        m2 = " /\\ ".join(c.replace("{2}", "") for c in mem2) if mem2 else "true"
        return [
            f"conseq (: {relational}) (: _ ==> {m1}) (: _ ==> {m2}).",
            "smt().",
            *_hoare_arm(mem1, b),
            *_hoare_arm(mem2, b),
            "proc.",
            "inline *.",
            "sim.",
        ]

    # The relational post carries ``res_eq`` (``res`` is the init's returned pk
    # tuple; ``sim`` proves it). Valid because ``_outer_leg`` applies ``conseq``
    # after a bare ``proc`` (before ``inline*``), where ``res`` is still bound.
    game_rel = " /\\ ".join([p for p in [globs, q1_eqs] if p] + [res_eq])
    red_rel = " /\\ ".join([p for p in [globs, q4_eqs] if p] + [res_eq])

    def _mirror(conj: str, base: str, flat: str, side: int) -> str | None:
        # Single-memory FLAT-STATE mirror of a seam conjunct, so BOTH conseq hoare
        # arms are real (no trivial ``true`` arm -> no losslessness obligation).
        # ``game.X{s} = chal.Y{s}`` (challenger seam) mirrors to ``flat.X =
        # flat.challenger_Y``; ``red.A{s} = red.B{s}`` (self-derived) to ``flat.A =
        # flat.B``. Both hold in the flat state and close with the same hoare peel.
        m = re.match(r"^([\w.]+)\.(\w+)\{[12]\} = ([\w.]+)\.(\w+)\{[12]\}$", conj)
        if m is None or m.group(1) != base:
            return None
        f_l, base_r, f_r = m.group(2), m.group(3), m.group(4)
        rhs = f"{flat}.{f_r}" if base_r == base else f"{flat}.challenger_{f_r}"
        return f"{flat}.{f_l}{{{side}}} = {rhs}{{{side}}}"

    _gm2 = [_mirror(c, game_base, fg_name, 2) for c in seam1]
    _rm1 = [_mirror(c, red_base, fr_name, 1) for c in seam2]
    game_mem2 = [c for c in _gm2 if c is not None] if seam1 and all(_gm2) else []
    red_mem1 = [c for c in _rm1 if c is not None] if seam2 and all(_rm1) else []
    outer = [
        _res_tag(SYNTH_PARAM),
        *([] if game_is_left else ["symmetry."]),
        f"transitivity {fg_name}({args}).initialize "
        f"({globs} ==> {q1}) ({globs} ==> {q2}).",
        "smt().",
        "smt().",
        *_outer_leg(game_body, f"{globs} ==> {game_rel}", seam1, game_mem2),
        f"transitivity {fr_name}({args}).initialize "
        f"({globs} ==> {q3}) ({globs} ==> {q4}).",
        "smt().",
        "smt().",
        *legmid,
        *_outer_leg(red_body, f"{globs} ==> {red_rel}", red_mem1, seam2),
        "qed.",
    ]
    extra = [
        "\n".join(_render_module_decl(fgmod)),
        "\n".join(_render_module_decl(frmod)),
        "\n".join(_render_module_decl(fgev)),
        "\n".join(_render_module_decl(frev)),
    ]
    return extra, outer, set()


def _branch_uses_concat(stmts: Sequence[ec_ast.EcStmt]) -> bool:
    """True when some assignment RHS or call argument in ``stmts`` (descending
    into nested ``if``s) references a ``concat_`` op."""
    for stmt in stmts:
        if isinstance(stmt, ec_ast.Assign) and "concat_" in stmt.rhs:
            return True
        if isinstance(stmt, ec_ast.Call) and "concat_" in stmt.args:
            return True
        if isinstance(stmt, ec_ast.If) and (
            _branch_uses_concat(stmt.then_body)
            or _branch_uses_concat(stmt.else_body or [])
        ):
            return True
    return False


def _collapse_all_ifs(body: list[ec_ast.EcStmt]) -> list[ec_ast.EcStmt]:
    """Flatten every ``if`` in ``body`` to its then-branch (recursively).

    Only used for the gated reprogramming-Lazy route, where every ``if`` is
    always-true-then (the reprogramming ``seed = s0`` after ``seed <- s0``, and
    the flat-state early-return ``! _r2`` after ``_r2 <- false``). Exposes the
    KEM/NG backbone that :func:`_call_sample_backbone` otherwise cannot see.
    """
    out: list[ec_ast.EcStmt] = []
    for stmt in body:
        if isinstance(stmt, ec_ast.If):
            out.extend(_collapse_all_ifs(stmt.then_body))
        else:
            out.append(stmt)
    return out


def _front_swaps_stable(
    cur_samples: list[tuple[str, str]], target_distrs: list[str], side: int
) -> list[str] | None:
    """``swap{side}`` tactics hoisting a body's samples to the front so their
    distribution sequence becomes ``target_distrs``, tolerating REPEATED
    distributions AND a forward sample DEPENDENCY (an exclusion sample
    ``seed_1 <$ d \\ pred1 seed_0`` that reads an earlier sample).

    ``cur_samples`` is the ``(var, distr)`` sequence of the body's samples in
    program order. Unlike :func:`_sample_front_swaps` (which addresses each
    sample by its distribution and so requires the distributions distinct), this
    matches the ``k``-th occurrence of a distribution to the ``k``-th occurrence
    in ``target_distrs`` -- a stable pairing, correct for the two-keypair binding
    init where both sides draw keypair-0's seeds before keypair-1's. Excluded-lambda
    distrs are normalized (``pred1 X`` -> ``pred1 _``) for MATCHING (the two sides
    name the excluded seed differently) while dependency detection keeps the RAW
    distr's var refs.

    A plain ``<$`` is glob/data-independent of everything before it, so hoisting
    it to the front (``^ <${occ} @ 0``) is always an EC-valid ``swap``. An
    EXCLUSION sample reads its predecessor and may NOT be hoisted above it: when
    the dependency is its target-adjacent predecessor (``order[p-1]``), the pair is
    placed together -- the dependency ``@ 0`` and the dependent ``@ 1`` -- then
    subsequent front hoists push the pair to its slot. Returns ``None`` on a
    non-permutation or an unhandled dependency. For DISTINCT distributions with no
    dependency it emits the identical swap list as :func:`_sample_front_swaps`.
    """

    def _norm(d: str) -> str:
        return re.sub(r"\(pred1 [^)]*\)", "(pred1 _)", d)

    cur_match = [_norm(d) for _, d in cur_samples]
    target_match = [_norm(d) for d in target_distrs]
    if sorted(cur_match) != sorted(target_match):
        return None
    if cur_match == target_match:
        return []
    target_positions_by_distr: dict[str, list[int]] = {}
    for pos, distr in enumerate(target_match):
        target_positions_by_distr.setdefault(distr, []).append(pos)
    seen: Counter[str] = Counter()
    target_pos: list[int] = []
    for distr in cur_match:
        occ_index = seen[distr]
        seen[distr] += 1
        target_pos.append(target_positions_by_distr[distr][occ_index])
    order = sorted(range(len(cur_samples)), key=lambda i: target_pos[i])
    var_to_index = {var: i for i, (var, _) in enumerate(cur_samples)}
    deps: dict[int, set[int]] = {}
    for i, (_, distr) in enumerate(cur_samples):
        refs = {
            var_to_index[m.group(0)]
            for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", distr)
            if m.group(0) in var_to_index and var_to_index[m.group(0)] != i
        }
        if refs:
            deps[i] = refs
    cur = list(range(len(cur_samples)))

    def _hoist(orig_idx: int, dest: int) -> str | None:
        occ = cur.index(orig_idx)
        if occ == dest:
            return None
        cur.insert(dest, cur.pop(occ))
        # ``dest`` is a SAMPLE slot; only 0 (front) and 1 (right below the
        # just-hoisted dependency) are ever requested. Slot 0 is ``@ 0`` (top
        # of code, same meaning on every EC). Slot 1 must be the SAMPLE-ANCHORED
        # destination ``@ ^ <${2}`` ("at the current 2nd sample" = right below
        # the dependency just hoisted to the front): the two EasyCrypt builds in
        # the toolchain disagree on numeric destinations -- the release
        # (r2026.03, the dashboard's compiler) reads ``@ n`` as a 1-indexed
        # LANDING POSITION (``@ 1`` = the very top, crossing the dependency:
        # "statements not independent ... writes seed_0"), while the
        # easycrypt-mcp fork reads it as a 0-indexed gap (``@ 1`` correct,
        # ``@ 2`` one slot too low, and ``@ > 0`` is fork-only grammar). The
        # anchored form parses on both and lands identically (at/before the 2nd
        # sample coincide for an upward move). Validated on both compilers via
        # ``.ec-tmp/probe/swap_excl*.ec``.
        at = "^ <${2}" if dest == 1 else str(dest)
        return f"swap{{{side}}} ^ <${{{occ + 1}}} @ {at}."

    swaps: list[str] = []
    placed: set[int] = set()
    for pos in reversed(range(len(order))):
        if pos in placed:
            continue
        want = order[pos]
        if want in deps:
            if pos == 0 or deps[want] != {order[pos - 1]}:
                return None
            for swap in (_hoist(order[pos - 1], 0), _hoist(want, 1)):
                if swap is not None:
                    swaps.append(swap)
            placed.add(pos - 1)
        else:
            swap = _hoist(want, 0)
            if swap is not None:
                swaps.append(swap)
    return swaps


def _has_side_local_projection(coupling: str | None) -> bool:
    """True when the threaded live-state coupling has a conjunct relating two
    references in the SAME memory through a tuple PROJECTION, e.g. the expanded
    combiners' KeyGen ek-projection ``(R.ek0{2}, R.dk0{2}) = ((R.dk0{2}.`3,
    R.dk0{2}.`4), R.dk0{2})``.

    ``sim`` only infers equalities BETWEEN the two memories, so such a conjunct
    makes ``proc; inline *; sim`` fail outright ("cannot infer the set of
    equalities"); the init backbone peel must run instead, where ``wp`` collects
    the assignments that make the projection a tautology. Cross-memory conjuncts
    (``Game.ek0{1} = R.ek0{2}``) and projection-free same-memory seams
    (``R.s_PQ_0{1} = Chal.dk0{1}``) both answer False, so every init that closes
    today keeps its tactic."""
    if not coupling:
        return False
    for part in coupling.split(" /\\ "):
        if "=" not in part or ".`" not in part:
            continue
        if len(set(re.findall(r"\{([12])\}", part))) == 1:
            return True
    return False


def _has_cross_seam_projection(coupling: str | None) -> bool:
    """True when the coupling relates a tuple PROJECTION of one module's field to
    a DIFFERENT module's field across the two memories, e.g. the stored-pair
    cross-seam conjunct ``R.pq_keys_0{1}.`2 = <Chal>.dk0{2}``.

    ``sim`` relates globals BY NAME within matching state, so it can neither
    project a packed field nor cross a module boundary: an init carrying such a
    conjunct fails "cannot infer the set of equalities" even when the two
    backbones match exactly. The backbone peel must run instead, where ``wp``
    collects the assignments that make the projection a tautology.

    Same-memory conjuncts are :func:`_has_side_local_projection`'s business;
    cross-memory conjuncts WITHOUT a projection, and projections relating the
    SAME module base on both sides, answer False -- so every init that closes
    today keeps its tactic."""
    if not coupling:
        return False
    for part in coupling.split(" /\\ "):
        if "=" not in part or ".`" not in part:
            continue
        if len(set(re.findall(r"\{([12])\}", part))) != 2:
            continue
        lhs, _, rhs = part.partition("=")
        bases = [
            m.group(1)
            for m in (re.match(r"\s*([A-Za-z_][\w.]*)\.", side) for side in (lhs, rhs))
            if m is not None
        ]
        if len(bases) == 2 and bases[0] != bases[1]:
            return True
    return False


def _rename_stmts(body: list[ec_ast.EcStmt], name: str) -> list[str]:
    """``body`` rendered with every occurrence of ``name`` replaced by a fixed
    token, so two bodies differing only in that identifier compare equal."""
    return [
        re.sub(rf"\b{re.escape(name)}\b", "#F#", _stmt_text(st))
        for st in _exec_stmts(body)
    ]


def _synth_init_backbone_peel(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    modules: mt.ModuleTranslator,
    oracle_name: str,
    left_state0: frog_ast.Game,
    right_state0: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
    det_methods: dict[str, set[str]],
    init_repacks: bool = False,
    init_decomposition: bool = False,
    require_equal_bodies: bool = False,
    side_local_coupling: bool = False,
    cross_seam_coupling: bool = False,
    ev_derivation_post: bool = False,
) -> tuple[list[str], set[tuple[str, str]], str] | None:
    """Closing tactic for an init-oracle equiv whose two endpoints have
    identical canonical bodies.

    ``require_equal_bodies`` (set when the caller reaches the peel WITHOUT the
    last-flat-state equality gate) demands the two FIRST flat-state bodies be
    identical before emitting any tactic: the backbone comparison ignores
    non-call/sample statements, so a genuinely-different body (e.g. an extra
    ``return``) can share a backbone -- ``proc; inline *; sim`` would then be a
    silently-failing (vacuous) tactic. With equal bodies, ``inline *; sim``
    provably closes.

    ``init_repacks`` is True when one side is a reduction that HOLDS the live
    field itself and therefore repacks the challenger's ``Initialize`` tuple
    result into its own globals (the case ``sim`` cannot align); it gates the
    keygen/sample-only backbone peel so stateless-delegate reductions keep the
    byte-identical ``sim``. ``init_decomposition`` is True when the hop's
    coupling is a DECOMPOSITION coupling (a game's packed key = the tuple of a
    reduction's component fields); it *also* needs the peel, because ``sim``
    cannot infer the cross-module packed-vs-components equality -- even for a
    reduction that does its OWN keygens rather than delegating a challenger
    ``Initialize`` (the ``R_KDF`` side of the CFRG expanded LEAK/HON hops).

    Returns ``(tactic, pres_requests, rung)`` -- ``pres_requests`` is the set of
    ``(module, method)`` glob-preservation axioms the tactic references (empty
    unless a dead-call drop fired), and ``rung`` is the resolution token.
    Returns ``None`` only when the backbones genuinely cannot be aligned (the
    caller then emits an honest admit).

    Backbone cases (the backbone is the ordered ``call``/``sample`` events read
    off each side's flat state via :func:`_call_sample_backbone`):

    * **No deterministic call** (equal backbones, and every call probabilistic
      -- e.g. a keygen/sample-only correctness init) -- ``sim`` aligns the whole
      symmetric body, so keep the historical ``proc; inline *; sim.``
      (``synth-static``). This is the *byte-identical* path: the peel below is
      only for inits ``sim`` cannot close.
    * **Equal backbones with a deterministic call** -- the INDCCA challenge
      embedding: a ``F.evaluate`` whose args are tuple-projections of two
      abstract ``encaps`` results ``inline *`` names differently, so ``sim``
      "cannot infer the set of equalities". Peel the backbone tail-to-front
      (``wp`` clears each deterministic run incl. the ``F.evaluate``,
      ``call (_: true)`` couples each abstract call name-independently -- ``(_:
      ={glob K})`` is rejected "module K can write K" -- ``rnd`` each sample),
      then ``skip => /#`` (``synth-param``).
    * **One side carries extra deterministic calls** -- the PRF-random final
      hop, where a wrapper still runs a now-dead ``F.evaluate`` whose result a
      later fresh sample overwrites (canonicalization dropped it, which is why
      the final bodies are equal). Each such call is a subsequence gap on the
      longer side (:func:`_dead_call_drop_tags`); if every gap call is a
      *deterministic* method (it has a ``_det`` axiom, so a glob-preserving
      ``_pres`` spec is sound) the peel drops it one-sided
      (``call{i} (<M>_<m>_pres g)``) and couples the shared backbone
      (``synth-param``).

    ``left_state0`` / ``right_state0`` are the *first* flat states (the
    FrogLang-inlined wrappers), whose backbones match what EC's ``inline *``
    exposes on the raw wrappers.
    """
    lproj = _project_to_method(left_state0, oracle_name)
    rproj = _project_to_method(right_state0, oracle_name)
    if lproj is None or rproj is None:
        return None
    lmod = _flat_state_module(
        modules, "Init_bb_L", lproj, external_module_types, method_return_types, []
    )
    rmod = _flat_state_module(
        modules, "Init_bb_R", rproj, external_module_types, method_return_types, []
    )
    del flat_params  # backbone is param-independent; kept for signature parity
    if not lmod.procs or not rmod.procs:
        return None
    l_body, r_body = lmod.procs[0].body, rmod.procs[0].body
    if require_equal_bodies and l_body != r_body:
        return None
    l_bb = _call_sample_backbone(l_body)
    r_bb = _call_sample_backbone(r_body)

    def _has_det_call(bb: list[tuple[str, str | None]]) -> bool:
        for kind, callee in bb:
            if kind != "call" or not callee or "." not in callee:
                continue
            mod, _, meth = callee.partition(".")
            if meth in det_methods.get(mod, set()):
                return True
        return False

    def _arrow_name(body: list[ec_ast.EcStmt]) -> str | None:
        return next(
            (
                st.var
                for st in _exec_stmts(body)
                if isinstance(st, ec_ast.Sample) and st.distr.startswith("dfun_")
            ),
            None,
        )

    def _arrow_rename_only() -> bool:
        """True when the two bodies are the SAME program up to the name of the
        random-function field.

        ``sim`` matches globals by NAME, so it cannot relate a game's ``rF`` to a
        challenger's -- it reports "cannot infer the set of equalities" and, worse,
        a run that leaves the goal open. The bodies being otherwise identical is
        exactly the case the explicit peel handles, so take it. The two-KEM
        IND-CCA cells reach this on their mirror hop, where both endpoints draw
        the shared secret fresh and only the field's owner differs."""
        ln, rn = _arrow_name(l_body), _arrow_name(r_body)
        if ln is None or rn is None or ln == rn:
            return False
        return _rename_stmts(l_body, ln) == _rename_stmts(r_body, rn)

    if [k for k, _ in l_bb] == [k for k, _ in r_bb]:
        if (
            not _has_det_call(l_bb)
            and not side_local_coupling
            and not cross_seam_coupling
            and not _arrow_rename_only()
        ):
            if (
                (init_repacks or init_decomposition)
                and not _same_det_structure(l_body, r_body)
                and (_has_tuple_repack(l_body) or _has_tuple_repack(r_body))
            ):
                # Field-holding-reduction init: one side does its keygens
                # directly, the other delegates ``Initialize`` to a stateful
                # inner challenger AND -- because the reduction holds its own
                # copy of the live field -- repacks the challenger's tuple
                # result into the reduction's own cross-module globals
                # (``R.dk0 <- _tup.`2``, a copy of the challenger's
                # ``LEAK.dk0``). ``sim`` cannot align those cross-module field
                # writes (nor prove the cross-module survivor invariant
                # ``L.dk0{1} = R.dk0{2}`` in the postcondition). Peel the shared
                # keygen/sample backbone tail-to-front (each ``call (_: true)``
                # couples an abstract keygen name-independently) and close the
                # residual assignment-derived field equalities with ``auto``
                # (``auto`` runs wp+smt internally -- a separate ``skip => /#``
                # leaves the field equalities open here). Validated interactively
                # on ``Generic/LEAK_implies_HON_BIND_K_CT`` hop 0 + 2.
                #
                # Gated on ``init_repacks`` (the reduction holds the live field)
                # AND the actual challenger-tuple repack fingerprint
                # (:func:`_has_tuple_repack`), so ``sim`` stays byte-identical
                # for: a STATELESS delegate that returns the challenger's result
                # directly (``KEMPRF_INDCPA hop_2_initialize``), and a
                # field-holding reduction that does its OWN keygen rather than
                # delegating a multi-field challenger ``Initialize``
                # (``KEMPRF_INDCPA hop_5_initialize`` / ``R_MultiPRF``) -- both
                # of which ``sim`` closes even with a cross-module survivor.
                #
                # TWO-KEM alignment: when the two endpoints run the SAME multiset
                # of abstract keygens but in a DIFFERENT ORDER (the two-KEM CFRG
                # binding init -- game ``[PQ, T, PQ, T]`` vs reduction
                # ``[PQ, PQ, T, T]``), the lockstep ``call (_: true)`` peel would
                # pair ``KEM_PQ.keygen{1}`` with ``KEM_T.keygen{2}`` (EC: "should
                # be equal"). Reorder side 2's calls to side 1's order with
                # ``swap{2}`` first; the flat-state exec positions match EC's
                # post-``inline *`` numbering, so the swaps land correctly. When
                # the callee orders already agree the aligner returns ``[]`` and
                # the tactic is byte-identical (Generic / CG single-KEM inits).
                l_callees = [c for k, c in l_bb if k == "call" and c is not None]
                r_callees = [c for k, c in r_bb if k == "call" and c is not None]
                swaps: list[str] = []
                if l_callees != r_callees:
                    if any(k == "sample" for k, _ in l_bb) or any(
                        k == "sample" for k, _ in r_bb
                    ):
                        # Sample-interleaved call reorder is not handled here;
                        # emit an honest admit rather than a mispairing peel.
                        return None
                    aligned = _align_call_order_swaps(_exec_stmts(r_body), l_callees, 2)
                    if aligned is None:
                        return None
                    swaps = aligned
                tac = ["proc.", "inline *.", *swaps, *_backbone_peel(l_body), "auto."]
                return (tac, set(), SYNTH_PARAM)
            # ``sim`` relates globals BY NAME, so it aligns the two inits only when
            # their call/sample backbones match exactly. A FIELD-HOLDING /
            # repacking reduction whose backbone differs from the game's -- the
            # same random-function sample bound to ``v_RF`` on the game vs
            # ``challenger_RF`` on the reduction (CK's PRF hop ``G_AllRand ~
            # R_PRF_Rev``) -- makes ``sim`` "cannot infer the set of equalities".
            # Emit an honest admit there (MAP principle 2). A pure stateless-
            # delegate reduction (``not init_repacks and not init_decomposition``)
            # keeps ``sim``: inlining its delegated init realigns the bodies
            # regardless of field renames, so those proofs stay byte-identical --
            # as does any exact-backbone init (``l_bb == r_bb``).
            if l_bb != r_bb and (init_repacks or init_decomposition):
                return None
            # ``sim`` aligns the two procedures STATEMENT-BY-STATEMENT in order; it
            # cannot reorder. When the abstract-call CALLEE SEQUENCE differs -- CK's
            # correctness-Ideal hop ``G_StoredSS_T_R ~ R_Correct_T_Ideal`` runs
            # ``KEM_PQ.keygen; KEM_T.keygen; ...`` on the game but ``KEM_T.keygen;
            # KEM_T.encaps; KEM_PQ.keygen; ...`` on the reduction (its challenger's
            # ``Compute`` does the T-KEM first) -- ``sim`` mis-pairs the calls and
            # leaves the goal open ("cannot save an incomplete proof"). Honest-admit
            # (MAP principle 2). A working ``sim`` init has matching callee order
            # (sim requires it), so this is byte-identical for every clean proof.
            if [c for k, c in l_bb if k == "call"] != [
                c for k, c in r_bb if k == "call"
            ]:
                return None
            # Identical structure, or a stateless-delegate reduction ``sim``
            # aligns: keep the historical tactic verbatim (byte-identical path
            # for the clean correctness / INDCPA / stateless-reduction inits).
            return (["proc; inline *; sim."], set(), SYNTH_STATIC)
        # The tail-to-front peel pairs the two sides' abstract calls positionally;
        # if their callees differ (the two-KEM CFRG correctness init runs
        # ``KEM_PQ.encaps`` where the other runs ``KEM_T.encaps``) the lockstep
        # ``call (_: true)`` mis-pairs them (EC "should be equal"). This
        # deterministic-call branch has no reorder machinery, so emit an honest
        # admit rather than a failing tactic (MAP principle 2). Matching callees
        # keep the historical peel (byte-identical).
        if [c for k, c in l_bb if k == "call"] != [c for k, c in r_bb if k == "call"]:
            return None
        if ev_derivation_post:
            # The post states each reduction field as an ``ev_`` DERIVATION over
            # the game's seed. This peel couples the abstract calls with
            # ``call (_: true)``, which says nothing about what they RETURNED, so
            # it provably cannot establish those conjuncts -- it would emit a
            # tactic that runs and leaves the goal open, taking the whole FILE
            # down. Decline to an honest admit (MAP principle 2); the dedicated
            # derivation peel handles the shapes it covers, and this is the
            # residue it declines (a two-keypair init, whose sample coupling it
            # does not model).
            return None
        tac = ["proc.", "inline *.", *_backbone_peel(l_body)]
        if _leads_with_det(l_body) or _leads_with_det(r_body):
            tac.append("wp.")
        tac.append("skip => /#.")
        return (tac, set(), SYNTH_PARAM)

    # Sample-reorder init (the KDF-layer ``R_PQ_Bind ~ R_KDF`` hops): the two
    # bodies run the SAME abstract calls in the SAME order and sample the SAME
    # distribution multiset, but interleave the samples differently -- one draws
    # the PQ seed first and derives immediately, the other draws all seeds up
    # front (``S,C,S,S,C,C,C`` vs ``S,S,S,C,C,C,C``). The kind sequences differ
    # (so the equal-kind block above declined) yet it is a sample PERMUTATION,
    # not a subsequence with extra det calls (so the dead-drop below declines on
    # the unmatched permuted sample). A ``<$`` is glob-independent, so hoisting
    # the non-contiguous side's samples up to the OTHER (contiguous-front) side's
    # sample order -- via occurrence-based ``swap ^ <${k} @ 0`` (position-ROBUST
    # against the tuple-unpack assigns EC's ``inline *`` interposes, which the
    # engine's flat state does not reproduce faithfully) -- makes both bodies
    # ``[samples; calls]``, and the common backbone peels. Keyed on distribution
    # (the two reductions name their samples differently), which requires the
    # distributions distinct so the ordering is determined.
    def _sample_distrs(body: list[ec_ast.EcStmt]) -> list[str]:
        return [s.distr for s in _exec_stmts(body) if isinstance(s, ec_ast.Sample)]

    def _call_callees(body: list[ec_ast.EcStmt]) -> list[str]:
        return [s.callee for s in _exec_stmts(body) if isinstance(s, ec_ast.Call)]

    def _samples_contiguous_front(body: list[ec_ast.EcStmt]) -> bool:
        seen_call = False
        for s in _exec_stmts(body):
            if isinstance(s, ec_ast.Call):
                seen_call = True
            elif isinstance(s, ec_ast.Sample) and seen_call:
                return False
        return True

    l_distrs, r_distrs = _sample_distrs(l_body), _sample_distrs(r_body)
    if (
        _call_callees(l_body) == _call_callees(r_body)
        and sorted(l_distrs) == sorted(r_distrs)
        and len(set(l_distrs)) == len(l_distrs)
        and l_distrs != r_distrs
    ):
        # Reference = the contiguous-front side (unchanged); hoist the other to
        # match its sample order, leaving both ``[samples; calls]``.
        align_swaps: list[str] | None
        if _samples_contiguous_front(r_body):
            align_swaps = _sample_front_swaps(l_body, r_distrs, 1)
        elif _samples_contiguous_front(l_body):
            align_swaps = _sample_front_swaps(r_body, l_distrs, 2)
        else:
            align_swaps = None
        if align_swaps is not None:
            ncalls, nsamples = len(_call_callees(r_body)), len(r_distrs)
            peel = ["wp.", "call (_: true)."] * ncalls + ["wp.", "rnd."] * nsamples
            tac = ["proc.", "inline *.", *align_swaps, *peel, "skip => /#."]
            return (tac, set(), SYNTH_PARAM)
    # Unequal backbones: try the dead-deterministic-call drop. The longer side's
    # backbone must be the shorter's with extra *deterministic* calls inserted.
    if len(l_bb) > len(r_bb):
        long_bb, long_body, short_body, side = l_bb, l_body, r_body, 1
    else:
        long_bb, long_body, short_body, side = r_bb, r_body, l_body, 2
    short_bb = r_bb if side == 1 else l_bb
    drops = _dead_call_drop_tags(long_bb, short_bb, det_methods, long_body)
    if drops is None:
        return None
    tac = ["proc.", "inline *."]
    pres: set[tuple[str, str]] = set()
    drop_ctr = 0
    for idx in reversed(range(len(long_bb))):
        kind, callee = long_bb[idx]
        tac.append("wp.")
        if drops[idx]:
            mod, _, meth = (callee or "").partition(".")
            binder = f"gf{drop_ctr}"
            drop_ctr += 1
            tac.append(
                f"exists* (glob {mod})" "{" f"{side}" "}" f"; elim* => {binder}."
            )
            tac.append(f"call" "{" f"{side}" "}" f" ({mod}_{meth}_pres {binder}).")
            pres.add((mod, meth))
        elif kind == "call":
            tac.append("call (_: true).")
        else:
            tac.append("rnd.")
    if _leads_with_det(long_body) or _leads_with_det(short_body):
        tac.append("wp.")
    tac.append("skip => /#.")
    return (tac, pres, SYNTH_PARAM)


def _stmt_operand(stmt: ec_ast.EcStmt) -> str:
    """The rendered expression a statement READS, or ``""``."""
    if isinstance(stmt, ec_ast.Call):
        return stmt.args
    if isinstance(stmt, ec_ast.Assign):
        return stmt.rhs
    if isinstance(stmt, ec_ast.Return):
        return stmt.expr
    return ""


def _read_tokens(expr: str) -> set[str]:
    """The variables ``expr`` reads, keeping a projection ``v.`k`` WHOLE.

    Reading one component of a tuple is not reading the tuple: keeping the
    projection as its own token is what lets :func:`_live_out` stay
    component-accurate.
    """
    out: set[str] = set()
    rest = expr
    for match in re.finditer(r"([A-Za-z_]\w*(?:\.\w+)*)\.`(\d+)", expr):
        out.add(f"{match.group(1)}.`{match.group(2)}")
        rest = rest.replace(match.group(0), " ")
    out |= set(_IDENT_TOKENS.findall(rest))
    return out


def _live_out(body: list[ec_ast.EcStmt]) -> list[set[str]]:
    """Backward liveness over variables AND tuple components: ``out[i]`` holds
    what is live after ``body[i]``.

    Whole-variable liveness is too coarse here, and this is the second time that
    has bitten on this project (the bundled-delegate sample-drop gate needed the
    same per-component treatment). The PRF-random init hop packs the droppable
    ``F.evaluate``'s result into a tuple whose OTHER component is genuinely live,
    so a whole-variable walk marks the result live, declines the hop, and turns a
    working peel into an admit. A live ``t.`2`` therefore revives only the second
    component of ``t``'s defining tuple literal.
    """
    live: set[str] = set()
    out: list[set[str]] = [set() for _ in body]
    for i in range(len(body) - 1, -1, -1):
        out[i] = set(live)
        stmt = body[i]
        written = getattr(stmt, "var", None)
        parts = (
            _top_level_tuple_parts(_stmt_operand(stmt))
            if isinstance(stmt, ec_ast.Assign)
            else None
        )
        wanted: set[str] | None = None
        if written:
            wanted = {
                tok for tok in live if tok == written or tok.startswith(f"{written}.`")
            }
            live -= wanted
        if isinstance(stmt, ec_ast.Assign) and not wanted:
            # A PURE assignment whose target is dead is itself dead: it can be
            # deleted, so its reads must not keep anything alive. (Only for
            # assignments -- a call or sample has glob effects and stays.)
            continue
        if parts is not None and written and wanted is not None:
            if written in wanted:
                for part in parts:
                    live |= _read_tokens(part)
            else:
                for tok in wanted:
                    idx = int(tok.rsplit(".`", 1)[1])
                    if 1 <= idx <= len(parts):
                        live |= _read_tokens(parts[idx - 1])
        else:
            live |= _read_tokens(_stmt_operand(stmt))
    return out


def _drop_result_dead(
    body: list[ec_ast.EcStmt], events: list[ec_ast.EcStmt], index: int
) -> bool:
    """True when the result of ``events[index]``'s call is DEAD at that point.

    Per-call, unlike the whole-body :func:`_all_calls_dead`: an init peel legally
    couples live calls and only needs the DROPPED ones to be dead. Determinism
    alone licenses the ``_pres`` axiom, which preserves the GLOB and says nothing
    about the result -- so dropping a call whose result is still live leaves that
    result universally quantified in the goal and the closing ``/#`` cannot
    discharge it. That is a tactic which RUNS WITHOUT CLOSING, the worst rung on
    the ladder because no ``admit`` marks it, and it is what kept
    `CG_seedbased_INDCCA_PQ` / `UG_seedbased_INDCCA_PQ` EC-rejected.
    """
    stmt = events[index] if index < len(events) else None
    if not isinstance(stmt, ec_ast.Call) or not stmt.var:
        return True  # a result-less call is trivially dead
    live = _live_out(body)[body.index(stmt)]
    return not any(tok == stmt.var or tok.startswith(f"{stmt.var}.`") for tok in live)


def _dead_call_drop_tags(
    long_bb: list[tuple[str, str | None]],
    short_bb: list[tuple[str, str | None]],
    det_methods: dict[str, set[str]],
    long_body: list[ec_ast.EcStmt] | None = None,
) -> list[bool] | None:
    """Tag each event of ``long_bb`` as a drop (extra) or shared, matching
    ``short_bb`` as a subsequence.

    Two events match if both are samples, or both are calls with the same
    callee. An unmatched ``long_bb`` event is a drop, accepted only when it is a
    call to a *deterministic* method (present in ``det_methods``) whose RESULT IS
    DEAD. Returns ``None`` if the subsequence match fails or any gap event fails
    either condition.

    THE LIVENESS CONDITION IS LOAD-BEARING and was missing here for a long time,
    while the post-init caller enforced it separately with
    :func:`_all_calls_dead`. Determinism alone licenses the ``_pres`` axiom,
    which preserves the GLOB -- it says nothing about the call's result. Drop a
    call whose result is still read and that result stays universally quantified
    in the goal, so the peel runs to completion and the closing ``/#`` cannot
    discharge it: a tactic that runs without closing, which is the worst
    outcome on this ladder because no ``admit`` marks it. That is exactly what
    kept `CG_seedbased_INDCCA_PQ` / `UG_seedbased_INDCCA_PQ` EC-rejected at
    `hop_23_initialize`, where the dropped `NG.exp` feeds the returned
    `ctStar`. The check lives HERE rather than at the call sites so a future
    caller cannot forget it.

    ``long_body`` is optional only so the post-init caller -- which already
    applies the stricter whole-body :func:`_all_calls_dead` -- keeps its
    existing behaviour byte-identically; every new caller should pass it.
    """

    def _match(a: tuple[str, str | None], b: tuple[str, str | None]) -> bool:
        if a[0] != b[0]:
            return False
        return a[0] == "sample" or a[1] == b[1]

    tags = [False] * len(long_bb)
    i, j = len(long_bb) - 1, len(short_bb) - 1
    while i >= 0:
        if j >= 0 and _match(long_bb[i], short_bb[j]):
            i -= 1
            j -= 1
            continue
        kind, callee = long_bb[i]
        if kind != "call" or not callee or "." not in callee:
            return None
        mod, _, meth = callee.partition(".")
        if meth not in det_methods.get(mod, set()):
            return None
        if long_body is not None and not _drop_result_dead(
            long_body,
            [s for s in long_body if isinstance(s, (ec_ast.Call, ec_ast.Sample))],
            i,
        ):
            return None
        tags[i] = True
        i -= 1
    if j >= 0:
        return None
    return tags


def _init_backbone_admit(hop_index: int, oracle_name: str) -> list[str]:
    """Honest guided admit for an init-oracle equiv whose two inlined wrappers
    have *different* probabilistic backbones (the uniform peel does not apply).

    The canonical bodies are identical, but one wrapper carries a dead
    ``F.evaluate`` (its result overwritten by a subsequent fresh sample) the
    other has already dropped -- the PRF-random final hop. Closing it needs a
    one-sided drop of the dead call (``call{i} (F_evaluate_det ...)``, whose
    result is unused) before the common ``keygen; encaps; sample`` backbone peel.
    That one-sided step is inline-name-dependent, so it is left as a targeted
    admit (ladder rung ``admit-guided``) rather than a silently-failing ``sim``.
    """
    return [
        _res_tag(ADMIT_GUIDED),
        f"(* multi-oracle hop {hop_index}, oracle {oracle_name!r}: init equiv",
        "   with a dead F.evaluate on one side (PRF-random hop). The shared",
        "   backbone is keygen; encaps; <fresh sample>, but one wrapper still",
        "   runs an F.evaluate whose result the sample overwrites. Drop it with a",
        "   one-sided phoare, then peel the common backbone:",
        "     proc. inline *.",
        "     (* drop the dead F.evaluate on the side that has it: *)",
        "     seq <k> <k+1> : (={glob K, glob F} /\\ <live coupling>).",
        "     + exists* (glob F){i}, <Fseedi>, <Finputi>; elim* => gf a0 a1;",
        "       call{i} (F_evaluate_det gf a0 a1); auto.",
        "     wp; rnd; wp; call (_: true); wp; call (_: true); skip => /#. *)",
        "admit.",
        "qed.",
    ]


# pylint: disable=too-many-locals,too-many-statements,too-many-arguments,too-many-positional-arguments
def emit_multi_oracle_chain_for_hop(
    hop_index: int,
    left_game: frog_ast.Game,
    right_game: frog_ast.Game,
    left_apps: list[TransformApplication],
    right_apps: list[TransformApplication],
    oracles: list[tuple[str, bool]],
    oracle_eq_args: dict[str, str],
    left_wrapper_expr: str,
    right_wrapper_expr: str,
    types: tc.TypeCollector,
    type_of_factory: Callable[
        [dict[str, frog_ast.Type], dict[str, str]],
        Callable[[frog_ast.Expression], frog_ast.Type],
    ],
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_module_params: list[ec_ast.ModuleParam] | None = None,
    det_methods: dict[str, set[str]] | None = None,
    inj_methods_by_module: dict[str, set[str]] | None = None,
    init_reduction_repacks: bool = False,
    init_decomposition: bool = False,
    clone_alias: dict[str, str] | None = None,
    full_coupling: str | None = None,
    use_canonical_fields: bool = False,
    stateless_wrapper_bases: frozenset[str] | set[str] | None = None,
    micro_leg_lookup: (
        Callable[[str, frog_ast.Game, frog_ast.Game, str], list[str] | None] | None
    ) = None,
    outer_globs: frozenset[str] | None = None,
) -> MultiOracleHopChainInfo:
    """Emit the per-oracle per-transform chains for one multi-oracle hop.

    ``oracles`` is the ordered ``(oracle_name, is_init)`` list (init first,
    then post-init in module-type declaration order); ``oracle_eq_args`` maps
    each oracle to its EC argument-equality string (``"true"`` or
    ``"={a, b}"``). ``left_wrapper_expr`` / ``right_wrapper_expr`` are the two
    adjacent games' wrapper module expressions (e.g.
    ``OneTimeSecrecyLR_Left(OTP)``), used to bridge the wrapper to the flat
    chain in each oracle's outer body.

    Returns the shared flat-state modules plus every oracle's chain artifacts,
    and a per-oracle outer tactic body. See the module-level note for scope.
    """
    left_states: list[frog_ast.Game] = [left_game] + [a.game_after for a in left_apps]
    right_states: list[frog_ast.Game] = [right_game] + [
        a.game_after for a in right_apps
    ]
    left_mods = [f"Step_{hop_index}L_state_{k}" for k in range(len(left_states))]
    right_mods = [f"Step_{hop_index}R_state_{k}" for k in range(len(right_states))]

    modules = mt.ModuleTranslator(types, type_of_factory)
    flat_params = list(flat_module_params) if flat_module_params else []
    inst_suffix = (
        "(" + ", ".join(p.name for p in flat_params) + ")" if flat_params else ""
    )

    def mod_ref(name: str) -> str:
        return f"{name}{inst_suffix}"

    # Canonical f<NN> field naming is a PROOF-WIDE decision (a ROM proof, from
    # its shared ``Function<D,R>`` random oracle): every ROM flat state -- incl.
    # the hash oracle's early hops that carry no ``fmap`` field yet -- names its
    # fields canonically so adjacent globs name-sort identically. Binding /
    # correctness proofs pass False, keeping stable names byte-identical.
    use_canonical = use_canonical_fields

    # Shared flat-state modules (full multi-oracle games), rendered ONCE but
    # emitted only if referenced (see the filter before the return). Record
    # each module's rendered text so the field-aware coupling can read its EC
    # ``glob`` signature (field name+type shape + actually-used params) off the
    # authoritative source (ROM only; empty otherwise -> old behavior).
    state_chunks: list[tuple[str, str]] = []
    glob_info_by_base: dict[str, tuple[tuple[tuple[str, str], ...], frozenset[str]]] = (
        {}
    )
    # The shared random-oracle holder modules (``RO_H``) are read-only globals a
    # hash oracle reads, so they couple like an abstract module param: add them
    # to the coupling param set so ``={glob RO_H}`` threads wherever an oracle
    # actually references ``RO_H.`` (the ``\bP\.`` footprint probe -- hash yes,
    # decaps no). ROM-only (``use_canonical``); binding proofs have no RO module.
    ro_module_names = (
        [m for m, _ in modules.types.function_value_modules()] if use_canonical else []
    )
    param_names = [p.name for p in flat_params] + ro_module_names
    for mod_name, state in zip(
        list(left_mods) + list(right_mods), list(left_states) + list(right_states)
    ):
        rendered = _render_flat_state(
            modules,
            mod_name,
            state,
            external_module_types,
            method_return_types,
            flat_params,
            emit_state_vars=True,
            use_canonical_fields=use_canonical,
        )
        state_chunks.append((mod_name, rendered))
        if use_canonical:
            glob_info_by_base[_ref_base(mod_ref(mod_name))] = _glob_signature(
                rendered, param_names
            )

    # Register each wrapper with its FLAT state's used-param set (empty field list:
    # the wrapper's fields still come from ``fields_by_base``, and its ``ftype`` was
    # already ``None`` when unregistered, so nothing regresses there). This makes a
    # flat<->wrapper coupling intersect to the SAME param set as the flat<->flat
    # chain coupling, so the transitivity POSTcondition composition agrees on which
    # ``={glob P}`` conjuncts appear -- without it the wrapper leg emitted ALL
    # params (``ri is None`` -> the ``glob_params`` fallback) while the chain emitted
    # the used-param intersection, and the composition then "cannot prove goal
    # (strict)" for a param the wrapper carries but the chain dropped. The empty
    # field tuple keeps the whole-glob ``li == ri`` shortcut off (field-wise).
    if use_canonical:
        for wrapper_expr, flat_mod in (
            (left_wrapper_expr, left_mods[0]),
            (right_wrapper_expr, right_mods[0]),
        ):
            flat_sig = glob_info_by_base.get(_ref_base(mod_ref(flat_mod)))
            wrapper_base = _ref_base(wrapper_expr)
            if flat_sig is not None and wrapper_base not in glob_info_by_base:
                glob_info_by_base[wrapper_base] = ((), flat_sig[1])

    bridge_tactic = "proc; inline *; ((sp; wp; sim) || sim)"
    tactic_body_by_oracle: dict[str, list[str]] = {}
    pres_methods: set[tuple[str, str]] = set()
    inj_methods: set[tuple[str, str]] = set()
    bij_methods: set[tuple[str, str, str, str]] = set()
    decaps_val_schemes: set[str] = set()
    state_modules: set[str] = set()
    aux_lemma_lines: list[str] = []
    oracle_chunks_all: list[str] = []
    for oracle_name, is_init in oracles:
        eq_args = oracle_eq_args.get(oracle_name, "true")
        oracle_chunks, outer_body, oracle_pres = _emit_one_oracle_chain(
            hop_index=hop_index,
            oracle_name=oracle_name,
            is_init=is_init,
            eq_args=eq_args,
            left_mods=left_mods,
            right_mods=right_mods,
            left_states=left_states,
            right_states=right_states,
            left_apps=left_apps,
            right_apps=right_apps,
            mod_ref=mod_ref,
            left_wrapper_expr=left_wrapper_expr,
            right_wrapper_expr=right_wrapper_expr,
            bridge_tactic=bridge_tactic,
            external_module_types=external_module_types,
            method_return_types=method_return_types,
            modules=modules,
            flat_params=flat_params,
            det_methods=det_methods or {},
            init_repacks=init_reduction_repacks,
            init_decomposition=init_decomposition,
            full_coupling=full_coupling,
            clone_alias=clone_alias or {},
            inj_acc=inj_methods,
            bij_acc=bij_methods,
            types=types,
            inj_methods_by_module=inj_methods_by_module or {},
            decaps_val_acc=decaps_val_schemes,
            aux_lemma_acc=aux_lemma_lines,
            use_canonical_fields=use_canonical,
            glob_info_by_base=glob_info_by_base,
            stateless_wrapper_bases=stateless_wrapper_bases,
            outer_globs=outer_globs,
            micro_leg_lookup=micro_leg_lookup,
        )
        oracle_chunks_all.extend(oracle_chunks)
        tactic_body_by_oracle[oracle_name] = outer_body
        pres_methods |= oracle_pres

    # Emit only the flat states some emitted artifact of THIS hop references.
    # When every oracle closes through an endpoint route or a whole-oracle
    # override, the per-transform chain is dead weight: hundreds of
    # unreferenced ``Step_*`` modules per security export (most of a
    # 40-70k-line file, and most of its EC compile time). A state is kept iff
    # its module name occurs in an oracle chunk, an outer tactic body, or an
    # aux lemma. A consumed chain references every state (each micro names its
    # adjacent pair), so chain-carried hops emit byte-identically.
    consumer_text = "\n".join(
        oracle_chunks_all
        + ["\n".join(body) for body in tactic_body_by_oracle.values()]
        + aux_lemma_lines
    )
    chunks: list[str] = [
        rendered
        for mod_name, rendered in state_chunks
        if re.search(rf"\b{re.escape(mod_name)}\b", consumer_text)
    ]
    chunks.extend(oracle_chunks_all)

    return MultiOracleHopChainInfo(
        extra_decls=chunks,
        tactic_body_by_oracle=tactic_body_by_oracle,
        pres_methods=pres_methods,
        inj_methods=inj_methods,
        bij_methods=bij_methods,
        decaps_val_schemes=decaps_val_schemes,
        state_modules=state_modules,
        aux_lemmas=aux_lemma_lines,
    )


# pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
def _emit_one_oracle_chain(
    hop_index: int,
    oracle_name: str,
    is_init: bool,
    eq_args: str,
    left_mods: list[str],
    right_mods: list[str],
    left_states: list[frog_ast.Game],
    right_states: list[frog_ast.Game],
    left_apps: list[TransformApplication],
    right_apps: list[TransformApplication],
    mod_ref: Callable[[str], str],
    left_wrapper_expr: str,
    right_wrapper_expr: str,
    bridge_tactic: str,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    modules: mt.ModuleTranslator,
    flat_params: list[ec_ast.ModuleParam],
    det_methods: dict[str, set[str]],
    init_repacks: bool = False,
    init_decomposition: bool = False,
    full_coupling: str | None = None,
    clone_alias: dict[str, str] | None = None,
    inj_acc: set[tuple[str, str]] | None = None,
    bij_acc: set[tuple[str, str, str, str]] | None = None,
    types: tc.TypeCollector | None = None,
    inj_methods_by_module: dict[str, set[str]] | None = None,
    decaps_val_acc: set[str] | None = None,
    # Unused since `_challenge_casesplit_route` was retired (2026-08-11): that
    # route was its only consumer, and it is the accumulator the route's shared
    # concat aux-lemmas were emitted through. Kept in the signature because the
    # route itself is kept as a reference and would need it back verbatim; the
    # exporter still threads it, so nothing else has to change either way.
    aux_lemma_acc: list[str] | None = None,  # pylint: disable=unused-argument
    use_canonical_fields: bool = False,
    glob_info_by_base: (
        dict[str, tuple[tuple[tuple[str, str], ...], frozenset[str]]] | None
    ) = None,
    stateless_wrapper_bases: frozenset[str] | set[str] | None = None,
    outer_globs: frozenset[str] | None = None,
    micro_leg_lookup: (
        Callable[[str, frog_ast.Game, frog_ast.Game, str], list[str] | None] | None
    ) = None,
) -> tuple[list[str], list[str], set[tuple[str, str]]]:
    """Emit one oracle's chain artifacts + outer tactic body.

    Returns ``(extra_decls, outer_body, pres_methods)`` where ``pres_methods``
    is the set of ``(module, method)`` glob-preservation axioms the outer body
    references (empty unless the init synthesizer fired a dead-call drop). If any
    chain step's micro cannot be resolved (not identity, not a pure reorder), the
    chain is discarded and the outer body is a coupling-pending admit (no
    oracle-suffixed artifacts).
    """
    # Lazy-RO Honest hashg is trivial: the game answers ``return RO_G_RO.h x`` and
    # (A lazy-RO ``hashg`` special case lived here — a construction- and
    # ORACLE-NAME-keyed closure. Removed under R9.)
    # Inline-equivalent endpoints (the P5 identical-state finding at oracle
    # granularity): when the two endpoints' CANONICAL bodies for this oracle
    # are identical, the raw wrapper modules are inline-equivalent, so a single
    # ``proc; inline *`` + backbone peel closes the lemma directly on the
    # wrappers -- sidestepping the per-transform chain (which the keygen-inlining
    # steps of ``Initialize`` defeat: an inlining step is neither identity nor a
    # pure reorder, so ``_oracle_step_tactic`` returns ``None`` and the chain
    # admits). Scoped to the init oracle.
    #
    # ``proc; inline *; sim`` closes a keygen/sample-only delegation (correctness
    # inits, INDCPA) and stays the byte-identical tactic there. But an
    # ``Initialize`` that also runs a deterministic ``F.evaluate`` challenge
    # embedding (INDCCA) defeats ``sim``: it cannot align the ``F.evaluate``
    # inputs -- tuple-projections of the two abstract ``encaps`` results, which
    # ``inline *`` names differently on the two sides -- so it silently leaves the
    # goal open (a 0-admit file EC rejects). :func:`_synth_init_backbone_peel`
    # gates on that (a deterministic call in the backbone) and, when present,
    # peels the shared probabilistic backbone tail-to-front instead
    # (``(wp; call (_: true) | rnd)*`` + ``skip => /#``, plus a one-sided
    # ``_pres`` drop for a dead ``F.evaluate``); fully name-independent, no
    # ``inline``-name prediction.
    # The per-oracle COUPLING is built here, before any whole-oracle or
    # endpoint route can return, so that every return path can still emit the
    # chain's closable legs as evidence-only lemmas (they need ``micro_pre``,
    # which needs this). Moving it earlier is otherwise behaviour-neutral: it
    # only reads the states and the caller's parameters.

    # Field-aware coupling: identical-state hops keep the whole-glob equality
    # (byte-identical for clean proofs); a hop whose two sides differ in glob
    # cardinality (a removed redundant field -- wall 4) couples shared fields +
    # survivor invariants. Built once over every flat state of this chain, using
    # the SAME ``_normalize_for_ec`` the module renderer applies -- so field
    # names match the rendered ``glob`` (``@``-mangled reduction fields like
    # ``challenger@dk0`` are sanitized to ``challenger_dk0``).
    def _normalized(game: frog_ast.Game) -> frog_ast.Game:
        return _normalize_for_ec(
            copy.deepcopy(game), external_module_types, method_return_types
        )

    norm_by_name = {
        name: _normalized(game)
        for name, game in list(zip(left_mods, left_states))
        + list(zip(right_mods, right_states))
    }
    fields_by_base = {
        _ref_base(mod_ref(name)): _ec_module_fields(game)
        for name, game in norm_by_name.items()
    }
    # Per-state EC field-type SEQUENCE (declaration order = glob order). At
    # equal field count the whole-glob shortcut is sound only when the two
    # sequences match: a same-cardinality RENAME+REORDER step (the HON micro
    # wall: [dk, scalar, elem] vs field1..3 = [elem, dk, scalar]) makes the
    # tuple equality ill-typed. Sequences equal -> shortcut unchanged (every
    # clean proof's whole-glob coupling type-checked in EC, so this is
    # byte-identity-safe by construction); differing -> field-wise coupling.
    type_sig_by_base = {
        _ref_base(mod_ref(name)): tuple(
            modules.types.translate_type(f.type).text for f in game.fields
        )
        for name, game in norm_by_name.items()
    }
    # Each flat state here is emitted with a canonical ``f<NN>`` var block
    # (``emit_state_vars`` -> :func:`_canonical_field_renames`), so a field's
    # DECLARED module var differs from its stable ``_ec_field_name``. Map the
    # stable name to the canonical var per base so the field-aware coupling
    # qualifies to the name EC actually sees (``Step_0L_state_5.f03``, not
    # ``.dk``). Keyed by stable name, valued by the same ``f<NN>`` the var
    # block uses. pylint: disable=protected-access
    # Proof-wide gate (matches the module rendering in
    # ``emit_multi_oracle_chain_for_hop``): a ROM proof names every state's
    # fields canonically, so ``qualify`` maps stable -> canonical for ALL its
    # bases; a binding/correctness proof keeps stable names (empty map ->
    # ``qualify`` verbatim, byte-identical).
    use_canonical = use_canonical_fields
    canonical_by_base = (
        {
            _ref_base(mod_ref(name)): {
                mt._ec_field_name(f.name): renames[f.name]
                for f in game.fields
                if f.name in renames
            }
            for name, game in norm_by_name.items()
            for renames in (mt._canonical_field_renames(game.fields, modules.types),)
        }
        if use_canonical
        else {}
    )
    norm_left = [norm_by_name[n] for n in left_mods]
    norm_right = [norm_by_name[n] for n in right_mods]
    survivor_map = _chain_survivor_map(list(norm_by_name.values()))

    # Wrapper<->flat bridge coupling (wall 7). Each hop's two wrapper modules
    # (``left_wrapper_expr`` / ``right_wrapper_expr``) are bridged to their
    # side's flat state-0. The whole-glob bridge is ill-typed / mispaired when
    # the wrapper's glob shape differs from that flat state. Register each
    # wrapper in ``fields_by_base`` (keyed by its base name) so the field-aware
    # coupling relates the right fields:
    #   * a REDUCTION wrapper ``R(K, Challenger)`` that both holds its OWN live
    #     field AND inlines a stateful ``Challenger`` -- its mirroring flat state
    #     carries both ``challenger@``-prefixed fields and own fields -- is
    #     COMPOSITE: its glob spans ``R`` (own) + ``Challenger`` (inner). Register
    #     with a qualified-ref map (own -> ``R.f``; ``challenger@f`` -> ``Chal.f``).
    #   * a PLAIN wrapper (no ``challenger@`` field) registers with its own field
    #     list; the default ``base.field`` qualification is the correct glob ref
    #     (its flat field names equal its module field names), which makes a
    #     cross-card bridge to the OTHER side's reduction-side flat well-typed.
    #   * a pure-DELEGATE reduction (``challenger@`` fields only, no own field) is
    #     left to the whole-glob bridge -- its glob IS the challenger's glob and
    #     the flat ``challenger@`` fields already line up positionally.
    # Clean proofs (every wrapper bridge same-cardinality) take the whole-glob
    # shortcut regardless, so they stay byte-identical.
    qualified_ref_by_base: dict[str, dict[str, str]] = {}
    for wrapper_expr, raw_state0, flat_base in (
        (left_wrapper_expr, left_states[0], _ref_base(mod_ref(left_mods[0]))),
        (right_wrapper_expr, right_states[0], _ref_base(mod_ref(right_mods[0]))),
    ):
        raw_names = [f.name for f in raw_state0.fields]
        norm_names = fields_by_base.get(flat_base, [])
        if len(raw_names) != len(norm_names):
            continue
        has_chal = any(n.startswith("challenger@") for n in raw_names)
        has_own = any(not n.startswith("challenger@") for n in raw_names)
        wrapper_base = _ref_base(wrapper_expr)
        if has_chal and has_own:
            chal_arg = next(
                (a for a in reversed(_top_level_args(wrapper_expr)) if "(" in a),
                None,
            )
            if chal_arg is None:
                continue
            chal_base = _ref_base(chal_arg)
            qmap: dict[str, str] = {}
            for raw_name, norm_name in zip(raw_names, norm_names):
                if raw_name.startswith("challenger@"):
                    own = raw_name[len("challenger@") :]
                    # pylint: disable-next=protected-access
                    qmap[norm_name] = f"{chal_base}.{mt._ec_field_name(own)}"
                else:
                    qmap[norm_name] = f"{wrapper_base}.{norm_name}"
            fields_by_base[wrapper_base] = list(norm_names)
            qualified_ref_by_base[wrapper_base] = qmap
        elif not has_chal:
            fields_by_base[wrapper_base] = list(norm_names)

    # Shared RO holder modules couple like read-only globals (see the same
    # computation in ``emit_multi_oracle_chain_for_hop``).
    ro_module_names = (
        [m for m, _ in modules.types.function_value_modules()] if use_canonical else []
    )
    ro_by_arrow = modules.types.ro_by_arrow_type() if use_canonical else {}
    # A COMPOSITE wrapper whose inner CHALLENGER holds a Function/arrow field
    # materialized as the shared RO (the lazy-RO Honest game's ``rF`` field IS the
    # shared RO -- part-10) must carry ``<Challenger>.rF{side} = RO_H.h{side}`` in
    # the coupling. Without it the wrapper<->flat transitivity's precondition
    # composition cannot derive ``RO_H.h = <Challenger>.rF`` -- the residual smt
    # cannot close (validated: ec_print_goals hop_4_hash 2nd transitivity). The
    # challenger's field surfaces as a ``challenger@<f>`` entry of the RAW flat
    # state-0; a FunctionType one whose EC arrow type is the shared RO's is
    # materialized. Sound: the LazyRO Honest ``initialize`` sets ``rF`` from the
    # shared RO. Empty for non-composite / non-ROM (byte-identical).
    # (The RO-challenger materialization DETECTOR that populated this map
    # — a lazy-RO modeling-pattern recognizer — was removed under R9
    # together with the coupling builders it fed. Left empty, the bridge
    # specs state no cross-form RO conjuncts, so they never demand a
    # relation the hop's weakened precondition cannot supply.)
    ro_challenger_by_base: dict[str, list[tuple[str, str]]] = {}

    # (The lazy-RO cross-identity coupling special case was removed under
    # R9 with the flag that fed it.)
    lazyro_cross: tuple[str, str, frozenset[str]] | None = None
    # Hoist-pair cache invariants (Move 3c). ROM chains (canonical field
    # naming) are out of the v1 scope -- their consumers then decline via
    # the enabling-coupling gate, an honest admit. Empty for every chain
    # without a Hoist pair (byte-identity).
    hoist_conjuncts = (
        {}
        if use_canonical
        else _hoist_conjunct_registry(
            left_states,
            right_states,
            left_mods,
            right_mods,
            mod_ref,
            modules,
            external_module_types,
            method_return_types,
            flat_params,
            det_methods,
            clone_alias or {},
        )
    )
    coupling = _make_field_aware_coupling(
        fields_by_base,
        survivor_map,
        [p.name for p in flat_params] + ro_module_names,
        _chain_role_map(norm_left, norm_right, survivor_map),
        qualified_ref_by_base,
        canonical_by_base,
        glob_info_by_base or {},
        ro_by_arrow,
        ro_challenger_by_base,
        lazyro_cross,
        type_sig_by_base=type_sig_by_base,
        outer_globs=outer_globs,
        hoist_conjuncts=hoist_conjuncts or None,
        init_source_by_base={
            _ref_base(mod_ref(name)): _init_source_map(game)
            for name, game in norm_by_name.items()
        },
        packed_components_by_base={
            _ref_base(mod_ref(name)): _init_packed_components(game)
            for name, game in norm_by_name.items()
        },
    )

    def micro_pre(left_ref: str, right_ref: str) -> str:
        cpl = coupling(left_ref, right_ref)
        if is_init:
            return "true"
        return cpl if eq_args == "true" else f"{eq_args} /\\ {cpl}"

    def micro_post(left_ref: str, right_ref: str) -> str:
        return f"={{res}} /\\ {coupling(left_ref, right_ref)}"

    chunks: list[str] = []
    step_pres: set[tuple[str, str]] = set()

    def _absorb_requests(reqs: MicroRequests) -> None:
        # Thread a micro leg's requests into the same accumulators the
        # whole-oracle routes populate; they flow through
        # ``MultiOracleHopChainInfo`` to the exporter's request sets
        # unchanged (design review (c) — no new exporter-side plumbing).
        step_pres.update(reqs.pres)
        if inj_acc is not None:
            inj_acc.update(reqs.inj)
        if bij_acc is not None:
            bij_acc.update(reqs.bij)
        if decaps_val_acc is not None:
            decaps_val_acc.update(reqs.decaps_val)

    def _cached_leg(
        transform_name: str, state_before: frog_ast.Game, state_after: frog_ast.Game
    ) -> tuple[list[str], MicroRequests, str] | None:
        """A captured tactic for ONE leg the synthesizers declined.

        Phase-4's attachment point for micro legs. Until the key became the
        masked changed region there was nothing to attach: a whole-game key
        could not name a single leg, so the per-transform capture mechanism
        could not catch the legs that matter most. The key here is that same
        masked shape computed on the two states PROJECTED to this oracle, so
        a leg entry and a chain-level entry for the same one-oracle change
        are the same key -- a hit across them is transfer working, not a
        collision.

        Returns ``None`` when no lookup is wired (every caller but the
        exporter) or on a miss, leaving the leg to decline exactly as before.
        """
        if micro_leg_lookup is None:
            return None
        tactic = micro_leg_lookup(
            transform_name, state_before, state_after, oracle_name
        )
        if tactic is None:
            return None
        return tactic, MicroRequests(), CACHED_UNGUIDED

    # EVIDENCE-ONLY MICRO EMISSION (see the exporter CLAUDE.md). The scan
    # below is shared by two callers. The chain path runs it and, when every
    # leg closed, goes on to build the bridge and chain lemmas. Every OTHER
    # return path -- an ``Initialize`` route, a whole-oracle route, an honest
    # admit -- runs it through :func:`_evidence_only_chunks` purely to keep
    # the legs that DID close as standalone lemmas. A leg that declines emits
    # NOTHING (never an ``admit.``), and the route still closes the hop lemma
    # exactly as before, so this can only add machine-checked statements.
    def _scan_legs(
        stateless: bool,
    ) -> tuple[
        list[str],
        list[str],
        list[str],
        bool,
        list[tuple[frog_ast.Game, frog_ast.Game, str, str, str]],
    ]:
        scan_chunks: list[str] = []
        # EVIDENCE-ONLY MICRO EMISSION. A chain whose legs do not ALL close cannot
        # carry the hop, so the oracle falls back to a whole-oracle route (or an
        # honest admit) exactly as before. But the legs that DID close are still
        # machine-checkable statements about single transform applications, and
        # dropping them threw that evidence away -- which made every move's payoff
        # all-or-nothing (a chain 37 pairs deep evidenced nothing until its last
        # pair closed). So: keep scanning after a declining leg, emit every leg
        # that closed as a standalone lemma, and emit NOTHING for a leg that
        # declined (never an ``admit.`` -- an admit-free proof stays admit-free and
        # a clean proof stays clean). The unreferenced lemmas still have to be
        # PROVEN by EasyCrypt, so accepting the file is evidence for exactly the
        # applications they name.
        chain_broken = False
        # One entry per appended micro chunk, in the same order: the two flat-state
        # games the lemma relates and its rendered precondition. Only consulted on
        # the broken-chain path (see the well-typedness filter below), so a chain
        # that closes pays nothing for it.
        evidence_meta: list[tuple[frog_ast.Game, frog_ast.Game, str, str, str]] = []

        micros_left: list[str] = []
        for k, app in enumerate(left_apps):
            if stateless:
                break
            lref, rref = mod_ref(left_mods[k]), mod_ref(left_mods[k + 1])
            step = _oracle_step_tactic(
                left_states[k],
                left_states[k + 1],
                oracle_name,
                app.transform_name,
                reversed_dir=False,
                external_module_types=external_module_types,
                method_return_types=method_return_types,
                modules=modules,
                flat_params=flat_params,
                det_methods=det_methods,
                micro_pre_text=micro_pre(lref, rref),
                left_ref=lref,
                right_ref=rref,
                clone_alias=clone_alias,
                use_canonical_fields=use_canonical,
                is_init=is_init,
            )
            entry: str | None = None
            if step is not None:
                tac, reqs, rung, entry = step
            else:
                cached = _cached_leg(
                    app.transform_name, left_states[k], left_states[k + 1]
                )
                if cached is None:
                    chain_broken = True
                    continue
                tac, reqs, rung = cached
            _absorb_requests(reqs)
            name = f"micro_{hop_index}_{oracle_name}_left_{k}"
            micros_left.append(name)
            scan_chunks.append(
                "\n".join(
                    _render_lemma_block(
                        name,
                        lref,
                        rref,
                        oracle_name,
                        micro_pre(lref, rref),
                        [
                            _res_tag(rung, transform=app.transform_name, entry=entry),
                            *tac,
                        ],
                        comment=_micro_transform_comment(app),
                        postcondition=micro_post(lref, rref),
                    )
                )
            )
            evidence_meta.append(
                (left_states[k], left_states[k + 1], lref, rref, micro_pre(lref, rref))
            )

        micros_right_rev: list[str] = []
        for k, app in enumerate(right_apps):
            if stateless:
                break
            # Reversed: proves Step_R_state_{k+1} ~ Step_R_state_k.
            lref, rref = mod_ref(right_mods[k + 1]), mod_ref(right_mods[k])
            step = _oracle_step_tactic(
                right_states[k],
                right_states[k + 1],
                oracle_name,
                app.transform_name,
                reversed_dir=True,
                external_module_types=external_module_types,
                method_return_types=method_return_types,
                modules=modules,
                flat_params=flat_params,
                det_methods=det_methods,
                micro_pre_text=micro_pre(lref, rref),
                left_ref=lref,
                right_ref=rref,
                clone_alias=clone_alias,
                use_canonical_fields=use_canonical,
                is_init=is_init,
            )
            entry = None
            if step is not None:
                tac, reqs, rung, entry = step
            else:
                cached = _cached_leg(
                    app.transform_name, right_states[k + 1], right_states[k]
                )
                if cached is None:
                    chain_broken = True
                    continue
                tac, reqs, rung = cached
            _absorb_requests(reqs)
            name = f"micro_{hop_index}_{oracle_name}_right_{k}_rev"
            micros_right_rev.append(name)
            scan_chunks.append(
                "\n".join(
                    _render_lemma_block(
                        name,
                        lref,
                        rref,
                        oracle_name,
                        micro_pre(lref, rref),
                        [
                            _res_tag(rung, transform=app.transform_name, entry=entry),
                            *tac,
                        ],
                        comment=_micro_transform_comment(app, reversed_dir=True),
                        postcondition=micro_post(lref, rref),
                    )
                )
            )
            evidence_meta.append(
                (
                    right_states[k + 1],
                    right_states[k],
                    lref,
                    rref,
                    micro_pre(lref, rref),
                )
            )

        return (
            scan_chunks,
            micros_left,
            micros_right_rev,
            chain_broken,
            evidence_meta,
        )

    def _evidence_only_chunks(stateless: bool = False) -> list[str]:
        """The closable legs of a chain this oracle does NOT take, as evidence.

        Lemmas whose STATEMENT does not typecheck are dropped: a chain the
        oracle never takes can carry a field coupling that equates fields of
        different types (``_chain_role_map`` is a union-find over bare field
        names), and EasyCrypt would reject the whole file for it.

        An ``Initialize`` leg is dropped WHOLESALE. Its precondition is
        ``true`` (there is no incoming state to relate), while its
        postcondition asserts the state coupling, so a single leg has to
        establish that coupling out of nothing -- which ``proc; sim`` cannot
        do, and EasyCrypt answers "cannot save an incomplete proof". Only the
        init chain AS A WHOLE, or the endpoint route that replaces it,
        establishes the coupling; per-leg init evidence needs a different
        statement shape and is left for a separate increment.
        """
        if is_init:
            return []
        scan, _l, _r, _broken, meta = _scan_legs(stateless)
        kept = [
            chunk
            for chunk, m in zip(scan, meta)
            if _micro_pre_well_typed(
                m,
                oracle_name,
                modules,
                external_module_types,
                method_return_types,
                flat_params,
                use_canonical,
            )
        ]
        return _mark_evidence_only(kept)

    if is_init:
        # (The exporter-computed whole-init override consumption lived
        # here; the channel was removed under R9.)
        proj_l = _project_to_method(left_states[-1], oracle_name)
        proj_r = _project_to_method(right_states[-1], oracle_name)
        last_states_match = (
            proj_l is not None
            and proj_r is not None
            and proj_l.methods[0] == proj_r.methods[0]
        )
        # (The construction-keyed init closers that stood here — the
        # ek-derivation twin, the reprogramming-lazy collapse — were
        # removed under R9.)
        # The backbone peel operates on the FIRST flat states (the raw wrappers
        # the init lemma actually relates), so it is valid even when the LAST
        # states diverge: a chain transform can unpack one side's packed key
        # (the Breakable game reads its DecapsKey components in ``Challenge`` so
        # the canonicalizer splits its field, while the reduction keeps it
        # packed) without changing the raw-wrapper init -- ``proc; inline *; sim``
        # still closes. It has its own conservative gate (matching first-state
        # backbones, pure delegate), so it declines to ``None`` where a real
        # coupling is needed and every other init stays byte-identical.
        peel = _synth_init_backbone_peel(
            modules,
            oracle_name,
            left_states[0],
            right_states[0],
            external_module_types,
            method_return_types,
            flat_params,
            det_methods,
            init_repacks=init_repacks,
            init_decomposition=init_decomposition,
            require_equal_bodies=not last_states_match,
            side_local_coupling=_has_side_local_projection(full_coupling),
            cross_seam_coupling=_has_cross_seam_projection(full_coupling),
            ev_derivation_post=bool(full_coupling and "ev_" in full_coupling),
        )
        if peel is not None:
            tactic, pres, rung = peel
            return _evidence_only_chunks(), [_res_tag(rung), *tactic, "qed."], pres
        # Bundled-delegate reorder: the two endpoints run the SAME abstract
        # calls but one gets a block of them from a delegate ``Challenger``
        # (``keygen; encaps`` back to back) while the other splits them around
        # its own sampling chain. The backbone peel declines because the
        # backbones are not equal; this route makes them equal with one
        # ``swap`` and then peels. ``None`` off-shape, so every other init is
        # byte-identical.
        # Its two one-sided dead draws are COUPLED rather than dropped where a
        # declared injective endo-map relates them (the mirror of the KDF-key
        # substitution hop -- see ``_DeadDrawBij``). ``None`` off-shape, and the
        # coupled path additionally needs the conjunct to be in the coupling, so
        # every hop the exporter does not state it for keeps the old drop-peel
        # byte-identical.
        dd_bij = _dead_draw_bij_spec(
            modules,
            oracle_name,
            left_states[0],
            right_states[0],
            external_module_types,
            method_return_types,
            det_methods,
            inj_methods_by_module or {},
            clone_alias or {},
            types,
            left_wrapper_expr,
            right_wrapper_expr,
        )
        # ORIENTATION-BLIND, because the exporter's own dedup is: a
        # correspondence another builder already emitted the other way round is
        # kept in ITS orientation, and an exact-string check would then read the
        # conjunct as absent and decline a route whose premise is in fact stated.
        if dd_bij is not None and not (
            full_coupling
            and all(
                _unordered_conj(c)
                in {_unordered_conj(x) for x in full_coupling.split(" /\\ ")}
                for c in dd_bij.conjuncts
            )
        ):
            dd_bij = None
        reorder = _synth_bundled_delegate_reorder(
            modules,
            oracle_name,
            left_states[0],
            right_states[0],
            external_module_types,
            method_return_types,
            ev_post=bool(full_coupling and "ev_" in full_coupling),
            coupling=full_coupling or "",
            bij=dd_bij,
        )
        if reorder is not None:
            if dd_bij is not None and reorder[0].startswith("have "):
                bij_methods_out = (
                    dd_bij.mod_name,
                    dd_bij.meth,
                    dd_bij.bs_name,
                    dd_bij.alias,
                )
                if bij_acc is not None:
                    bij_acc.add(bij_methods_out)
            return (
                _evidence_only_chunks(),
                [_res_tag(SYNTH_PARAM), *reorder, "qed."],
                set(),
            )
        # (The KDF-substitution init closers that stood here were
        # removed under R9.)
        # (The divergent-last-state ek-twin fallback was removed under R9.)
        if last_states_match:
            # (The construction-keyed twin-reorder init closer was
            # removed under R9.)
            if full_coupling is not None and clone_alias:
                plain = _synth_init_plain_reorder(
                    modules,
                    oracle_name,
                    left_states[0],
                    right_states[0],
                    external_module_types,
                    method_return_types,
                    flat_params,
                    det_methods,
                    clone_alias,
                    full_coupling,
                    hop_index=hop_index,
                )
                if plain is not None:
                    return plain
            # Backbones cannot be aligned (an extra call that is not a droppable
            # deterministic method): the peel does not apply. Emit a targeted,
            # honest admit rather than a silently-failing ``sim``.
            # Bundled delegate that runs an EXTRA deterministic call whose
            # result is LIVE (the correctness challenger's ``decaps``, stored as
            # the tuple's ``.`5``): the reorder above drops only DEAD samples and
            # the backbone peel's ``_pres`` drop forgets the result, so both
            # decline. Route through flat twins and drop the extra through its
            # ``_det`` axiom, which is what states the coupling's ``ev_`` fact
            # about it. ``None`` off-shape -> the honest admit below.
            if full_coupling is not None and clone_alias:
                deleg = _synth_delegate_correctness_init(
                    modules,
                    oracle_name,
                    left_states[0],
                    right_states[0],
                    external_module_types,
                    method_return_types,
                    flat_params,
                    det_methods,
                    clone_alias,
                    full_coupling,
                    hop_index=hop_index,
                )
                if deleg is not None:
                    return deleg
            # (The RO-reprogramming init closer was removed under R9.)
            return (
                _evidence_only_chunks(),
                _init_backbone_admit(hop_index, oracle_name),
                set(),
            )

    # (The per-oracle tactic-override consumption lived here — the
    # exporter-computed whole-oracle bodies. The channel was removed
    # under R9: the exporter knows languages, not cryptography.)

    # ALL TWELVE WHOLE-ORACLE ENDPOINT ROUTES ARE RETIRED (2026-08-11).
    #
    # The dispatch that stood here tried, in order, a dozen bespoke
    # whole-oracle tactics before the per-transform chain was allowed to run.
    # Each is still DEFINED in this module and kept as a reference for a
    # tactic shape known to work; none of them is called any more. The
    # per-transform chain is the architecture, and a whole-oracle closure
    # hides every leg of the chain it stands in for -- so where one of these
    # used to close an oracle the chain now runs, and where the chain does not
    # complete the oracle takes an honest admit. That is the accepted cost of
    # the change, not a regression.
    #
    # Retired in the order the per-route closure census priced them, each its
    # own increment with its own sweep, EasyCrypt compile and dashboard:
    #
    #    1st  `_challenge_reorder_route`              7 closures /  6 proofs
    #    2nd  `_synth_ro_reprogram_oracle`            4 closures /  4 proofs
    #    3rd  `_synth_kdf_substitution_decaps`        8 closures /  4 proofs
    #    4th  `_challenge_lazyro_route`              12 closures /  6 proofs
    #    5th  `_challenge_casesplit_route`           12 closures / 12 proofs
    #    6th  `_challenge_hop2_route`                12 closures / 12 proofs
    #    7th  `_challenge_single_r_route`            12 closures / 12 proofs
    #    8th  `_synth_sim_field_rename`              16 closures / 13 proofs
    #    9th  `_synth_forwarded_oracle_peel`         24 closures / 12 proofs
    #   10th  `_synth_correctness_decaps_casesplit`  24 closures / 12 proofs
    #   11th  `_synth_structural_if_peel`            24 closures / 12 proofs
    #   12th  `_challenge_falsefalse_route`          24 closures / 24 proofs
    #
    # Two of the twelve are worth remembering for what they taught. Retiring
    # the SECOND exposed `_synth_sim_field_rename` to a coupling that is a
    # quantified implication rather than an equality set: it ran without
    # closing, which turned four proofs from clean to REJECTED until that
    # route was gated (`_coupling_has_implication`). Retiring the TENTH is the
    # only one that moved the evidence number -- +1040 transform applications,
    # because the chain that took over those oracles got far enough for a
    # thousand of its legs to close. The LAST was left until last on purpose:
    # its oracles are `Unbreakable` challenges returning `false` on both
    # sides, so it traded a one-line closure for an admit on the most trivial
    # oracle in the corpus. That is a reason to do it last, not a reason to
    # keep it.

    if qualified_ref_by_base:
        bridge_peel = _composite_bridge_tactic(
            modules,
            left_states[0],
            oracle_name,
            external_module_types,
            method_return_types,
            flat_params,
        )
        if bridge_peel is not None:
            bridge_tactic = bridge_peel

    # A stateless ROM oracle collapses the whole chain to ``proc; auto`` on the
    # endpoints (see the chain-lemma assembly below), so its per-step micros and
    # canon-bridge lemma are never referenced -- skip emitting them (they would
    # otherwise still have to compile, and their own ``sim``-based tactics fail
    # on the cross-name field couplings a stateless oracle's endpoints carry).
    # WHOLE-CHAIN purity (non-ROM route). The ROM gate above reads only the two
    # ENDPOINT states, which is safe there because a ROM ``hash`` is stateless by
    # construction in every state. Off the ROM path the same collapse needs a
    # strictly stronger structural test: in EVERY flat state of the chain the
    # oracle must be a PURE function of its arguments -- no field touched, no
    # module called, and no sampling. Then every intermediate body reduces to its
    # return expression under ``wp``, the transitivity has nothing to compose,
    # and the chain collapses to the endpoint lemma. This dissolves the
    # chain-composition wall for a constant-return oracle (a binding
    # ``Unbreakable.Challenge`` ``return false``, whose 30+ intermediate states
    # differ only in fields the oracle never reads) instead of threading a
    # coupling through it. The no-sampling clause is load-bearing: a body with
    # even a DEAD ``<$`` is not closable by ``auto`` (it needs a one-sided ``rnd``
    # plus losslessness), so such an oracle must keep its chain. Purely
    # structural -- no proof/game names -- and EC-gated: the collapsed
    # ``proc; auto => /#`` either closes the endpoint lemma or the file is
    # rejected.
    all_states_pure = not is_init and all(
        _oracle_is_pure_of_args(g, oracle_name) for g in (*left_states, *right_states)
    )
    rom_stateless_oracle = (
        use_canonical
        and not is_init
        and _oracle_is_stateless(left_states[0], oracle_name)
        and _oracle_is_stateless(right_states[0], oracle_name)
    )
    stateless_oracle = all_states_pure or rom_stateless_oracle

    def _admit_fallback() -> tuple[list[str], list[str], set[tuple[str, str]]]:
        # An honest admit naming the hop and oracle. The fused whole-oracle
        # closers that used to be consulted here (the HashG reprogramming
        # route, the derivation-chain peel, the straight-line challenge
        # peel) were deleted under the ratified architecture: R6 forbids
        # fused closures outside the carve-out register, and the register
        # is empty. Re-proposable only through the register's probe +
        # sign-off process.
        return (
            [],
            _oracle_pending_admit(
                hop_index, oracle_name, micro_pre(left_wrapper_expr, right_wrapper_expr)
            ),
            set(),
        )

    (
        scan_chunks,
        micros_left,
        micros_right_rev,
        chain_broken,
        evidence_meta,
    ) = _scan_legs(stateless_oracle)
    chunks.extend(scan_chunks)

    if chain_broken:
        # The chain cannot carry the hop: take the same fallback as before
        # (whole-oracle route, else honest admit) and keep the closed legs as
        # standalone evidence lemmas. The fallback emits no chunks of its own,
        # and its ``pres`` requests are unioned with the ones the surviving
        # legs asked for so every axiom an emitted lemma names is declared.
        #
        # Filter out any lemma whose STATEMENT does not typecheck. A chain that
        # never closed can carry a field coupling that pairs fields of
        # different types (the chain-wide role map is a union-find over bare
        # field names, so one mispairing anywhere can equate unrelated roles);
        # its own chain lemma is never emitted, but an evidence lemma built on
        # the same coupling would be, and EasyCrypt would reject the whole file
        # with "no matching operator `='". Dropping those keeps evidence-only
        # emission strictly additive: it can never turn an accepted export into
        # a rejected one.
        kept = [
            chunk
            for chunk, meta in zip(chunks, evidence_meta)
            if _micro_pre_well_typed(
                meta,
                oracle_name,
                modules,
                external_module_types,
                method_return_types,
                flat_params,
                use_canonical,
            )
        ]
        _, fb_body, fb_pres = _admit_fallback()
        return _mark_evidence_only(kept), fb_body, step_pres | fb_pres

    bridge_name = f"canon_bridge_{hop_index}_{oracle_name}"
    bl, br = mod_ref(left_mods[-1]), mod_ref(right_mods[-1])
    if not stateless_oracle:
        chunks.append(
            "\n".join(
                _render_lemma_block(
                    bridge_name,
                    bl,
                    br,
                    oracle_name,
                    micro_pre(bl, br),
                    ["proc; sim."],
                    postcondition=micro_post(bl, br),
                )
            )
        )

    chain_name = f"hop_{hop_index}_{oracle_name}_chain"
    l0, r0 = mod_ref(left_mods[0]), mod_ref(right_mods[0])
    # A STATELESS oracle (no field read/write, no module call -- e.g. a ROM
    # ``hash`` ``return H(m)``) is identical across every flat state, so the
    # whole transitivity chain collapses to ``proc; sim`` on the endpoints: it
    # relates the two identical bodies and preserves every field coupling
    # (nothing is touched), sidestepping the composition machinery AND the
    # tuple-split field-correspondence gap. Gated on ROM (``use_canonical``) so
    # binding/correctness proofs stay byte-identical.
    if stateless_oracle:
        # ``auto`` (not ``sim``): the body touches no field, so each field
        # coupling is a frame condition; ``sim`` tries to build a glob bijection
        # and fails on cross-name pairings (``f02{1}=f07{2}``), whereas ``auto``
        # discharges the return via ``wp`` and leaves the untouched fields to
        # ``smt`` (``=> /#``).
        chain_body = ["proc; auto => /#."]
    else:
        chain_body = _render_coupling_chain_body(
            oracle_name,
            is_init,
            eq_args,
            [mod_ref(n) for n in left_mods],
            [mod_ref(n) for n in right_mods],
            micros_left,
            micros_right_rev,
            bridge_name,
            coupling,
            use_canonical,
        )
    chunks.append(
        "\n".join(
            _render_lemma_block(
                chain_name,
                l0,
                r0,
                oracle_name,
                micro_pre(l0, r0),
                chain_body,
                postcondition=micro_post(l0, r0),
            )
        )
    )

    # Outer hop_<i>_<m> body: bridge the two wrappers to the flat chain ends,
    # then discharge via the chain lemma. The wrapper<->flat coupling is the
    # P5 piece; the structure mirrors the single-oracle outer tactic.
    #
    # First-goal witness (precondition composition): a ROM field-wise
    # wrapper<->flat leg (forced field-wise by the RO-module glob-offset fix)
    # exposes the middle flat state's fields + abstract module globs as separate
    # existentials ``smt`` cannot instantiate; ``_precond_witness`` supplies them
    # explicitly. A whole-glob leg (no RO) returns ``None`` -> keep ``smt()``, so
    # non-ROM proofs stay byte-identical.
    def outer_g1(cur_ref: str, nxt_ref: str, final_ref: str) -> str:
        if use_canonical and not is_init:
            w = _precond_witness(
                coupling(cur_ref, nxt_ref),
                coupling(nxt_ref, final_ref),
                eq_args,
                _ref_base(nxt_ref),
            )
            if w is not None:
                return w
        return "smt()"

    # A stateless RO oracle whose two WRAPPER bodies are IDENTICAL direct RO
    # returns (``return RO_H.h m``, e.g. a reduction that forwards ``Hash``
    # straight to the shared RO) closes by ``proc; auto => /#`` on the wrappers:
    # the coupling carries ``={glob RO_H}`` + the argument equality, and every
    # field coupling is a frame condition. This bypasses the wrapper<->flat glob
    # bridge (ill-typed when a shared RO holder shifts the glob offset). It is
    # gated on BOTH wrappers being direct-RO for this oracle: a wrapper that
    # DELEGATES the oracle to a composed challenger (``R_Wrap_Prog.hash`` ->
    # ``Challenger.direct(m)``) has a non-identical body, so it must take the
    # bridge (which ``inline *`` unfolds the challenger). Validated: ``trip_glob.ec``.
    both_wrappers_direct_ro = _oracle_is_direct_ro(
        left_states[0], oracle_name
    ) and _oracle_is_direct_ro(right_states[0], oracle_name)
    # Both outer-body shortcuts read the FLAT states as a proxy for the wrapper
    # bodies, which is faithful only on the ROM path (a direct-RO wrapper inlines
    # to a direct-RO flat state). A non-ROM constant-return oracle inlines to a
    # ``return false`` flat state from a wrapper that DELEGATES to its challenger,
    # so the proxy would wrongly claim identical wrapper bodies -- keep those
    # chains on the generic wrapper<->flat bridge and collapse only the chain
    # lemma itself.
    if rom_stateless_oracle and both_wrappers_direct_ro:
        outer_body = [
            "(* Stateless RO oracle: identical wrapper bodies, RO-coupled. *)",
            "proc; auto => /#.",
            "qed.",
        ]
    elif rom_stateless_oracle and (
        _ref_base(left_wrapper_expr) in (stateless_wrapper_bases or set())
        or _ref_base(right_wrapper_expr) in (stateless_wrapper_bases or set())
    ):
        # Stateless RO oracle where one wrapper is a STATELESS reduction (holds no
        # own state field): the wrapper<->flat glob bridge ``(glob <flat>){1} =
        # (glob <wrapper>){2}`` is ILL-TYPED because the flat state carries the
        # inlined reduction's fields while the stateless wrapper's glob has none
        # (the CFRG ROM ``R_Dist_Real ~ R_Wrap_Prog`` / ``R_Wrap_NoAbort ~ ...``
        # steps). One wrapper returns the RO directly, the other DELEGATES to its
        # composed challenger (``_r0 <@ Challenger.direct(m); return _r0``); both
        # reduce to the shared RO once the concrete challenger's ``direct``
        # (``return rF m``, with ``rF = RO_H.h`` in the coupling) is unfolded, so
        # ``proc; inline *; auto => /#`` closes the two wrappers directly, bypassing
        # the bridge. ``stateless_oracle`` guarantees both flat states (= the
        # inlined wrappers) touch no real state, so nothing but the RO return
        # survives -- symmetric in which side delegates. Gated on EITHER wrapper
        # being a genuinely stateless reduction: a STATEFUL wrapper (CG expanded's
        # ``R_Wrap_Prog`` with its own ``dk_PQ``/``ss_PQ_star``/``ct_PQ_star``
        # fields, hop_4/hop_10 hash) whose glob matches the flat state keeps the
        # byte-identical bridge; non-ROM proofs never reach here.
        outer_body = [
            "(* Stateless RO oracle, stateless wrapper: inline the RO, close. *)",
            "proc; inline *; auto => /#.",
            "qed.",
        ]
    elif all_states_pure:
        # ARGUMENT-PURE oracle (non-ROM): every flat state's body is a pure
        # function of the arguments, and a flat state IS the inlined wrapper --
        # so ``inline *`` reduces both wrapper bodies to those pure bodies and
        # ``auto`` discharges the return, leaving every field coupling as a frame
        # condition for ``/#``. This bypasses the wrapper<->flat bridge
        # transitivity entirely, which is the right move here rather than making
        # its whole-glob leg specs compose with a field-wise outer precondition:
        # the bridge exists to transport state correspondences, and this oracle
        # touches no state. Unlike the ROM shortcuts above we do NOT read the
        # flat state as a proxy for the wrapper body -- ``inline *`` runs first,
        # so a wrapper that DELEGATES the oracle to its challenger is handled
        # too. EC-gated: if a wrapper body holds a call ``inline *`` cannot
        # unfold (an abstract module), ``auto`` leaves the goal open and the file
        # is rejected.
        outer_body = [
            "(* Argument-pure oracle: inline the wrappers, close directly. *)",
            "proc; inline *; auto => /#.",
            "qed.",
        ]
    elif not _bridge_specs_compose(
        coupling,
        left_wrapper_expr,
        right_wrapper_expr,
        l0,
        r0,
        full_coupling,
        fields_by_base,
        glob_info_by_base,
    ):
        # The chain closed every leg, but its wrapper<->flat bridge cannot
        # compose with this hop's own precondition, so emitting it would
        # REPLACE an honest admission with a REJECTED FILE. Keep the admission.
        # Measured on `KEMPRF_INDCCA` `hop_3_decaps`, whose chain first
        # completed on 2026-08-13: the hop states `G_RandKey.sk{1} =
        # R_MultiPRF.sk{2}` while the two bridge legs together demand the two
        # wrappers' WHOLE globs equal, which also covers `ctStar` -- nothing
        # relates it, so EasyCrypt refuses `transitivity` outright and prints
        # the goal UNCHANGED. That is a false obligation, not a hard one, so
        # no stronger tactic rescues it.
        outer_body = _oracle_pending_admit(hop_index, oracle_name, full_coupling or "")
    else:
        outer_body = [
            "(* Per-transform: bridge wrappers to flat states, chain through. *)",
            f"transitivity {l0}.{oracle_name} "
            f"{_coupling_spec(left_wrapper_expr, l0, is_init, eq_args, coupling)} "
            f"{_coupling_spec(l0, right_wrapper_expr, is_init, eq_args, coupling)}; "
            f"[ {outer_g1(left_wrapper_expr, l0, right_wrapper_expr)} | smt() "
            f"| {bridge_tactic} |].",
            f"transitivity {r0}.{oracle_name} "
            f"{_coupling_spec(l0, r0, is_init, eq_args, coupling)} "
            f"{_coupling_spec(r0, right_wrapper_expr, is_init, eq_args, coupling)}; "
            f"[ {outer_g1(l0, r0, right_wrapper_expr)} | smt() "
            f"| apply {chain_name} | {bridge_tactic} ].",
            "qed.",
        ]
    return chunks, outer_body, step_pres


def _oracle_is_direct_ro(game: frog_ast.Game, oracle_name: str) -> bool:
    """True if ``oracle_name``'s body reads NO game field (not even a
    materialized-RO arrow field) and makes no module call -- i.e. it returns the
    SHARED RO applied to its argument directly (``return H(m)`` -> ``RO_H.h m``).

    Stricter than :func:`_oracle_is_stateless`, which treats a materialized RO
    arrow field (``RF <- RO_H.h``) as RO-stateless. Here that field READ counts:
    a wrapper that forwards ``Hash`` straight to the shared RO has a direct-RO
    body on BOTH the wrapper and its (identical) flat state, so ``proc; auto =>
    /#`` closes it on the wrappers directly. A wrapper that instead DELEGATES the
    oracle to a composed challenger (``R_Wrap_Prog.hash`` -> ``Challenger.direct``,
    whose flat state materializes ``RF m``) reads a field -> returns False -> the
    outer body takes the wrapper<->flat bridge, which ``inline *`` unfolds the
    challenger. Read off the flat state, a faithful proxy: a direct-RO wrapper
    inlines to a direct-RO flat state; a delegating one to a field-reading one."""
    method = next(
        (m for m in game.methods if m.signature.name.lower() == oracle_name), None
    )
    if method is None:
        return False
    field_names = {f.name for f in game.fields}
    has_call = (
        SearchVisitor[frog_ast.FuncCall](
            lambda n: isinstance(n, frog_ast.FuncCall)
            and isinstance(n.func, frog_ast.FieldAccess)
        ).visit(method.block)
        is not None
    )
    has_field = (
        SearchVisitor[frog_ast.Variable](
            lambda n: isinstance(n, frog_ast.Variable) and n.name in field_names
        ).visit(method.block)
        is not None
    )
    return not has_call and not has_field


def _oracle_is_stateless(game: frog_ast.Game, oracle_name: str) -> bool:
    """True if ``game``'s ``oracle_name`` method reads/writes NO module field and
    makes NO module call -- a pure function of its arguments (e.g. a ROM ``hash``
    oracle ``return H(m)``: ``H`` is a shared-op RO value, not a module).

    Such an oracle is IDENTICAL across every flat state of a hop, so the whole
    ``hop_<i>_<oracle>_chain`` -- a long transitivity through the intermediate
    states -- collapses to a single ``proc; sim`` on the endpoints: ``sim``
    relates the two identical bodies and PRESERVES every field-coupling
    invariant (nothing is touched). This sidesteps the transitivity-composition
    machinery entirely, and in particular the tuple-split field-correspondence
    gap: a stateless oracle's chain never needs to thread a ctStar it doesn't
    read. A module call is a ``FuncCall`` whose ``func`` is a ``FieldAccess``
    (``E.m(...)``); a field reference is a ``Variable`` naming one of
    ``game.fields``."""
    method = next(
        (m for m in game.methods if m.signature.name.lower() == oracle_name), None
    )
    if method is None:
        return False
    # A ``Function``-typed field is a MATERIALIZED shared RO (``f06 <- RO_H.h``,
    # coupled ``f06 = RO_H.h``), not real state -- reading it is reading the RO.
    # So a lazy-RO Honest ``hash`` ``return f06 m`` is still RO-stateless: its
    # chain collapses to ``proc; auto => /#`` (``={glob RO_H}`` + ``f06=RO_H.h``
    # close ``={res}``). Only a NON-arrow field counts as real state.
    non_ro_fields = {
        f.name for f in game.fields if not isinstance(f.type, frog_ast.FunctionType)
    }
    has_call = (
        SearchVisitor[frog_ast.FuncCall](
            lambda n: isinstance(n, frog_ast.FuncCall)
            and isinstance(n.func, frog_ast.FieldAccess)
        ).visit(method.block)
        is not None
    )
    has_field = (
        SearchVisitor[frog_ast.Variable](
            lambda n: isinstance(n, frog_ast.Variable) and n.name in non_ro_fields
        ).visit(method.block)
        is not None
    )
    return not has_call and not has_field


def _oracle_is_pure_of_args(game: frog_ast.Game, oracle_name: str) -> bool:
    """True if ``oracle_name``'s body is a PURE function of its arguments in
    ``game``: no module field touched, no module call, and no sampling.

    Strictly stronger than :func:`_oracle_is_stateless`, which permits sampling
    (harmless on the ROM path, where the collapse it gates only ever sees a
    ``return H(m)`` body). Off that path the extra clause is load-bearing: a body
    carrying even a DEAD ``<$`` is not closable by ``auto`` -- it needs a
    one-sided ``rnd`` and a losslessness fact -- so the chain-collapse route must
    decline there and let the oracle keep its per-transform chain. Unlike
    :func:`_oracle_is_stateless` a ``Function``-typed (materialized-RO) field
    read also counts as state here: this predicate is used off the ROM path,
    where no such materialization is in play."""
    method = next(
        (m for m in game.methods if m.signature.name.lower() == oracle_name), None
    )
    if method is None:
        return False
    field_names = {f.name for f in game.fields}
    has_call = (
        SearchVisitor[frog_ast.FuncCall](
            lambda n: isinstance(n, frog_ast.FuncCall)
            and isinstance(n.func, frog_ast.FieldAccess)
        ).visit(method.block)
        is not None
    )
    has_field = (
        SearchVisitor[frog_ast.Variable](
            lambda n: isinstance(n, frog_ast.Variable) and n.name in field_names
        ).visit(method.block)
        is not None
    )
    has_sample = (
        SearchVisitor[frog_ast.Statement](
            lambda n: isinstance(n, (frog_ast.Sample, frog_ast.UniqueSample))
        ).visit(method.block)
        is not None
    )
    return not has_call and not has_field and not has_sample


def _bridge_specs_compose(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    coupling: CouplingFn,
    left_wrapper: str,
    right_wrapper: str,
    first_flat: str,
    last_flat: str,
    full_coupling: str | None,
    fields_by_base: dict[str, list[str]],
    glob_info_by_base: (
        dict[str, tuple[tuple[tuple[str, str], ...], frozenset[str]]] | None
    ) = None,
) -> bool:
    """Can the chain's wrapper<->flat bridge compose with the hop's own spec?

    The outer hop lemma is proved by two ``transitivity`` steps through the
    chain's endpoint flat states. Composing their middle specs yields, at the
    seam, exactly the coupling the bridge states between the two WRAPPERS. So
    the hop's own precondition has to be at least that strong.

    When the two flat states have the same field set the bridge coupling is
    the WHOLE-GLOB equality, and composing the legs demands the two wrappers'
    whole globs equal. A hop whose own coupling is FIELD-WISE -- because the
    two wrappers hold different fields -- does not supply that, and the
    obligation is FALSE rather than hard: EasyCrypt refuses ``transitivity``
    and reprints the goal unchanged. Emitting the chain there converts an
    honest admission into a rejected file, which is the worst state this
    exporter has, so the caller keeps the admission instead.

    The test is therefore whether the hop's coupling relates EVERY field the
    chain's endpoint states carry. That distinction was measured, not guessed,
    on the two cases that separate it:

    * ``7_13_Backward`` is CLEAN today. Each of its wrappers holds one field
      and the hop couples it -- ``E_c.INDCPA_MultiChal_Left.k{1} =
      E_c.Challenge_Left.k{2}`` -- so its field-wise coupling says everything
      the whole-glob equality does and the legs compose. An earlier version of
      this gate compared conjuncts syntactically instead, declined here, and
      would have taken that proof from 0 admissions to 3.
    * ``KEMPRF_INDCCA`` states ``G_RandKey.sk{1} = R_MultiPRF.sk{2}`` while
      those states also carry ``ctStar``. One field is left unrelated, so the
      obligation is false.

    True (compose) whenever the bridge is NOT whole-glob -- a field-wise
    bridge gets its explicit witnesses from :func:`_precond_witness` -- or
    when every endpoint field is mentioned by the hop's coupling. An absent
    hop coupling answers True, so this only ever declines a shape it has
    positively identified.
    """
    if not full_coupling:
        return True
    # FIELD COVERAGE of the two wrapper<->flat bridges. A FIELD-WISE
    # bridge whose spec leaves an endpoint flat field unmentioned states
    # an obligation nothing supplies: the flat state carries the field
    # (e.g. a challenger-absorbed ``Function`` value) but no conjunct
    # relates it to the wrapper side, so the bridge leg's closing tactic
    # runs and leaves the goal open -- a 0-new-admit file EasyCrypt
    # rejects. Declining keeps the honest admission instead. Erring
    # toward declining is the safe direction: a false decline adds a
    # visible admission; a false accept rejects the whole file.
    # WHOLE-GLOB middle spec between endpoint flat states whose glob
    # SIGNATURES differ is ILL-TYPED (EC: "no matching operator, named
    # `='" -- a typing failure that reads like a solver one). Refuse.
    if glob_info_by_base is not None:
        sig_l = glob_info_by_base.get(_ref_base(first_flat))
        sig_r = glob_info_by_base.get(_ref_base(last_flat))
        if (
            sig_l is not None
            and sig_r is not None
            and sig_l != sig_r
            and _WHOLE_GLOB_EQ_RE.fullmatch(coupling(first_flat, last_flat).strip())
        ):
            return False
    left_bridge = coupling(left_wrapper, first_flat).strip()
    right_bridge = coupling(last_flat, right_wrapper).strip()
    # PACKED-vs-COMPONENT seam: when the hop's own coupling PROJECTS a
    # wrapper field's components (``ek0{1}.`1 = ...``) the field is a
    # product the chain has split; a bridge conjunct that pairs the same
    # field UNPROJECTED with one flat field is ill-typed (EC: "no
    # matching operator, named `='"). The relation between the packed
    # value and its components was the deleted builders' content, so
    # decline to the honest admit.
    projected = set(
        re.findall(r"\.(\w+)\{\d\}\.`\d", full_coupling)
        + re.findall(r"\.(\w+)\.`\d\{\d\}", full_coupling)
    )
    if projected:
        for text in (left_bridge, right_bridge):
            for packed_field in projected:
                if re.search(r"\." + re.escape(packed_field) + r"\{\d\}(?!\.`)", text):
                    return False
    for flat_ref, bridge_text in (
        (first_flat, left_bridge),
        (last_flat, right_bridge),
    ):
        if _WHOLE_GLOB_EQ_RE.fullmatch(bridge_text):
            continue
        mentioned_bridge = set(_RENAME_TOKEN_RE.findall(bridge_text))
        if any(
            f not in mentioned_bridge and f.rsplit("_", 1)[-1] not in mentioned_bridge
            for f in fields_by_base.get(_ref_base(flat_ref), ())
        ):
            return False
    if not _WHOLE_GLOB_EQ_RE.fullmatch(left_bridge):
        return True
    needed = set(fields_by_base.get(_ref_base(first_flat), ())) | set(
        fields_by_base.get(_ref_base(last_flat), ())
    )
    mentioned = set(_RENAME_TOKEN_RE.findall(full_coupling))
    # A flat state MANGLES a field it absorbed from a composed challenger
    # (``challenger_k``), while the hop's coupling names that same field
    # through its owning module (``E_c.Challenge_Left.k{2}``) -- the two spell
    # one field across the game/challenger seam. Matching the trailing
    # component as well as the whole name is what stops the gate declining
    # ``7_13_Backward``, whose only unmatched name was exactly that. Erring
    # permissive is the safe direction here: a missed catch leaves today's
    # behaviour, while a false catch would add admissions to a clean proof.
    return all(f in mentioned or f.rsplit("_", 1)[-1] in mentioned for f in needed)


# ``.*`` rather than ``[^)]*``: a flat state is a FUNCTOR reference and carries
# its own parentheses (``glob Step_3L_state_0(K, F)``), so a paren-excluding
# class stops at the wrong one and the match silently fails -- which would make
# the gate answer "composes" for exactly the shape it exists to catch.
_WHOLE_GLOB_EQ_RE = re.compile(r"\(glob .*\)\{1\} = \(glob .*\)\{2\}")


def _precond_witness(
    pre1: str,
    pre2: str,
    eq_args: str,
    nxt_base: str,
) -> str | None:
    """Explicit-witness discharge for a FIELD-WISE transitivity's precondition
    goal, or ``None`` for a whole-glob leg (keep ``smt()``).

    EC's ``transitivity`` precondition obligation is
    ``pre => exists <MIDDLE-memory globs>, pre1{1,m} /\\ pre2{m,2}`` where the
    middle module is ``nxt``. For a whole-glob middle predicate EC threads the
    single glob-tuple witness automatically; a FIELD-WISE predicate exposes each
    ``={glob P}`` and each ``nxt`` field as a SEPARATE existential var -- and the
    module-glob ones (``P0:(glob P)``) are over an abstract sort ``smt`` cannot
    instantiate, so plain ``smt()`` fails "cannot prove goal (strict)". Provide
    the witnesses explicitly.

    The exists ranges over EVERY ``nxt`` field mentioned in pre1 OR pre2, so BOTH
    couplings must be parsed:
    * pre1 = ``coupling(cur, nxt)`` has ``cur.X{1} = nxt.Y{2}`` -> witness
      ``nxt.Y`` by its side-1 partner ``cur.X{1}``.
    * pre2 = ``coupling(nxt, final)`` has ``nxt.Y{1} = final.Z{2}`` -> for a
      ``nxt`` field NOT pinned by pre1, witness ``nxt.Y`` by the side-2 value
      ``final.Z{2}`` (pre1 leaves it free; pre2 fixes it to the endpoint).
    Order matches EC's exists layout (verified against the printed goal):
    USED-param globs ``(glob P){1}`` ALPHABETICAL (EC orders glob by name), then
    every ``nxt`` field sorted by name, then ``arg{1}`` if the oracle takes
    arguments. Within-side survivor conjuncts (``base.a{s}=base.b{s}``, same side)
    are not exists vars. Returns ``None`` when no ``nxt`` field is pinned across
    the pair (a whole-glob leg)."""
    fld = re.compile(r"(\w[\w.]*)\.(\w+)\{(\d)\} = (\w[\w.]*)\.(\w+)\{(\d)\}")
    params: list[str] = []
    field_wit: dict[str, str] = {}  # nxt field name -> witness expr
    ro_side: dict[str, str] = {}  # RO-holder glob -> witness side ("1" default)
    pre1_fieldwise = False

    def _note_ro_side(coupling_text: str) -> None:
        # A cross-form RO coupling ``<cur/outer-field>{1} = <RO>.h{2}`` (the RO
        # holder on side 2, coupled to a field that is NOT the middle's own)
        # pins the MIDDLE's shared RO to side 2's value, so its exists witness
        # must be ``<RO>.h{2}`` -- not the default ``{1}``. This is the lazyro
        # Honest chain-to-game leg (``Step_L.f03{1} = RO_G_RO.h{2}``); the
        # materialized-RF hops (``nxt.f{1} = RO.h{1}``) keep side 1.
        for part in (p.strip() for p in coupling_text.split("/\\")):
            fm = fld.fullmatch(part)
            if (
                fm
                and fm.group(3) == "1"
                and fm.group(6) == "2"
                and fm.group(4).split(".")[-1].startswith("RO_")
                and fm.group(1) != nxt_base
            ):
                ro_side[fm.group(4)] = "2"

    for part in (p.strip() for p in pre1.split("/\\")):
        gm = re.fullmatch(r"=\{glob ([\w.]+)\}", part)
        if gm:
            params.append(gm.group(1))
            pre1_fieldwise = True
            continue
        fm = fld.fullmatch(part)
        if fm and fm.group(3) == "1" and fm.group(6) == "2" and fm.group(4) == nxt_base:
            field_wit.setdefault(fm.group(5), f"{fm.group(1)}.{fm.group(2)}{{1}}")
            pre1_fieldwise = True
        # RO-materialized field: ``nxt.f06{2} = RO_H.h{2}`` (within-side). The
        # middle's arrow field EQUALS the shared RO, so its exists witness is
        # ``RO_H.h{1}`` (``={glob RO_H}`` makes {1}/{m} agree). Without this the
        # arrow field is absent from the witness and the exists mistypes.
        elif (
            fm
            and fm.group(3) == "2"
            and fm.group(6) == "2"
            and fm.group(1) == nxt_base
            and fm.group(4).split(".")[-1].startswith("RO_")
        ):
            field_wit.setdefault(fm.group(2), f"{fm.group(4)}.{fm.group(5)}{{1}}")
            pre1_fieldwise = True
    # Only pre1's shape decides field-wise vs whole-glob: a whole-glob pre1
    # (``(glob L){1}=(glob R){2}``, no ``={glob P}`` / field conjunct) leaves EC
    # to thread the single glob-tuple witness -- keep ``smt()`` even if pre2
    # happens to be field-wise.
    if not pre1_fieldwise:
        return None
    for part in (p.strip() for p in pre2.split("/\\")):
        gm = re.fullmatch(r"=\{glob ([\w.]+)\}", part)
        if gm:
            # A param appears as an existential over the middle module iff SOME
            # coupling of the pair constrains its glob -- i.e. iff the middle uses
            # it. ``coupling(cur, nxt)`` and ``coupling(nxt, final)`` each carry the
            # used-param INTERSECTION of their two endpoints, so a param the middle
            # uses but ``cur`` does not (e.g. ``G`` for ``Step_4R``) is dropped from
            # pre1 yet present in pre2; union the two so the witness covers exactly
            # what EC's exists quantifies (the middle's own used-param set).
            params.append(gm.group(1))
            continue
        fm = fld.fullmatch(part)
        if fm and fm.group(3) == "1" and fm.group(6) == "2" and fm.group(1) == nxt_base:
            field_wit.setdefault(fm.group(2), f"{fm.group(4)}.{fm.group(5)}{{2}}")
        # RO-materialized field on the pre2 side (``nxt.f06{1} = RO_H.h{1}``).
        elif (
            fm
            and fm.group(3) == "1"
            and fm.group(6) == "1"
            and fm.group(1) == nxt_base
            and fm.group(4).split(".")[-1].startswith("RO_")
        ):
            field_wit.setdefault(fm.group(2), f"{fm.group(4)}.{fm.group(5)}{{1}}")
    if not field_wit:
        return None
    # EC's exists layout for the middle module's globs is, IN ORDER:
    #   [the middle's USED-param globs, alphabetical]  (EC includes a functor arg's
    #     glob iff the module actually uses it -- an UNused param, e.g. ``G`` for the
    #     ``Step_4L`` flat state, is NOT in the module's ``(glob)`` and so is NOT an
    #     existential; providing it mistypes the first slot "(glob G) vs (glob
    #     KEM_PQ)")
    #   [the module's OWN fields, in field order]
    #   [referenced GLOBAL-module globs (the shared RO holder), AFTER the fields]
    #   [the oracle argument, last]
    # The used-param set is exactly the UNION of the two couplings' ``={glob P}``
    # conjuncts (parsed above into ``params``): each coupling carries the used-param
    # intersection of its endpoints, so a param the middle uses but one endpoint
    # does not is dropped from one coupling yet present in the other, and the union
    # recovers the middle's own set. A shared-RO holder glob (``<clone>.RO_H``) is a
    # REFERENCED global, not a functor param, so it sorts AFTER the fields;
    # mis-ordering shifts every later witness one slot -> a value lands in the
    # arrow-typed RO slot ("no matching operator"). Verified: ec_print_goals on
    # hop_4_hash (both transitivities).
    ro_globs = sorted({p for p in params if p.split(".")[-1].startswith("RO_")})
    functor_globs = sorted(
        {p for p in params if not p.split(".")[-1].startswith("RO_")}
    )
    witnesses = [f"(glob {p}){{1}}" for p in functor_globs]
    witnesses += [field_wit[y] for y in sorted(field_wit)]
    # The RO holder's exists var is its single ``h`` field (an arrow), so witness
    # it as ``<clone>.RO_H.h{s}`` -- the explicit field, not the opaque
    # ``(glob <clone>.RO_H){s}`` (which ``smt`` does not always see as equal to
    # the arrow field ``f06 = h`` in a materialized-RF middle state). The side
    # ``s`` is 1 by default (materialized-RF hops) but 2 for a cross-form RO
    # coupling (the lazyro Honest chain-to-game leg; see ``_note_ro_side``).
    _note_ro_side(pre1)
    _note_ro_side(pre2)
    witnesses += [f"{p}.h{{{ro_side.get(p, '1')}}}" for p in sorted(ro_globs)]
    if eq_args != "true":
        witnesses.append("arg{1}")
    # ``;``-chained, not ``.``-separated: this is ONE goal-slot inside a
    # ``transitivity ...; [ g1 | smt() | ... ]`` bracket, where a ``.`` would end
    # the whole sentence and mis-parse.
    return f"move=> &1 &2 hpre; exists {' '.join(witnesses)}; move: hpre; smt()"


def _render_coupling_chain_body(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    oracle_name: str,
    is_init: bool,
    eq_args: str,
    left_refs: list[str],
    right_refs: list[str],
    micros_left: list[str],
    micros_right_rev: list[str],
    bridge_name: str,
    coupling: CouplingFn = _glob_coupling,
    use_witness: bool = False,
) -> list[str]:
    """Transitivity chain body with per-step coupling specs.

    Walks ``L0 -> ... -> Ln --bridge--> Rn -> ... -> R0`` applying each
    oracle-suffixed micro. Unlike the single-oracle :func:`_render_chain_body`
    (uniform ``={res}`` spec), every transitivity middle-spec couples the
    current intermediate module to the relevant endpoint, because the coupling
    invariant references the actual module names. ``coupling`` is the field-aware
    builder (defaults to the identical-state ``_glob_coupling``).
    """
    final_right = right_refs[0]

    def spec(a_ref: str, b_ref: str) -> str:
        return _coupling_spec(a_ref, b_ref, is_init, eq_args, coupling)

    def g1(a_ref: str, b_ref: str) -> str:
        # First transitivity goal (precondition composition). A ROM field-wise
        # leg needs explicit middle-memory witnesses (``smt`` can't instantiate
        # the abstract module-glob existentials); a whole-glob leg keeps ``smt()``
        # (``_precond_witness`` returns None). Init legs (``pre = true``) keep
        # ``smt()``. Non-ROM proofs pass ``use_witness=False`` -> byte-identical.
        # ``b_ref`` is the middle module ``nxt``; the exists ranges over its
        # fields as pinned by pre1 = ``coupling(a,b)`` and pre2 = ``coupling(b,
        # final)``.
        if use_witness and not is_init:
            w = _precond_witness(
                coupling(a_ref, b_ref),
                coupling(b_ref, final_right),
                eq_args,
                _ref_base(b_ref),
            )
            if w is not None:
                return w
        return "smt()"

    body = ["(* Chain through per-transform micro-lemmas (coupling-preserving). *)"]
    cur = left_refs[0]
    for i, micro in enumerate(micros_left):
        nxt = left_refs[i + 1]
        body.append(
            f"transitivity {nxt}.{oracle_name} "
            f"{spec(cur, nxt)} {spec(nxt, final_right)}; "
            f"[ {g1(cur, nxt)} | smt() | apply {micro} |]."
        )
        cur = nxt
    if micros_right_rev:
        rn = right_refs[-1]
        body.append(
            f"transitivity {rn}.{oracle_name} "
            f"{spec(cur, rn)} {spec(rn, final_right)}; "
            f"[ {g1(cur, rn)} | smt() | apply {bridge_name} |]."
        )
        for i in reversed(range(len(micros_right_rev))):
            rev = micros_right_rev[i]
            if i == 0:
                body.append(f"apply {rev}.")
            else:
                target = right_refs[i]
                body.append(
                    f"transitivity {target}.{oracle_name} "
                    f"{spec(right_refs[i + 1], target)} {spec(target, final_right)}; "
                    f"[ {g1(right_refs[i + 1], target)} | smt() | apply {rev} |]."
                )
    else:
        body.append(f"apply {bridge_name}.")
    return body


# ---------------------------------------------------------------------------
# Statement-reorder detection (for ``swap`` tactic synthesis)
# ---------------------------------------------------------------------------


def _permutation_swaps(
    before: frog_ast.Game,
    after: frog_ast.Game,
    reversed_dir: bool = False,
) -> list[str] | None:
    """Decompose a reordering of top-level statements into ``swap`` tactics.

    Compares the top-level statement signatures of the single oracle
    method in ``before`` vs ``after`` modulo local variable names. If
    the two are permutations of each other, returns a list of EC
    ``swap{side} pos delta.`` tactic strings that reorder the lemma's
    LEFT side (= ``before`` in the forward direction, ``after`` in the
    reverse direction) to match the lemma's RIGHT side. The micro
    lemma's LEFT is always the first module argument of the equiv, so
    ``side`` is always ``1`` — we never need ``swap{2}``.

    Returns ``None`` if (a) signatures don't match as multisets (the
    transform isn't a pure reordering), (b) games have multiple
    methods, or (c) any other structural mismatch. The caller then
    falls back to the no-swap canned tactic.

    The signature comparison ignores assigned-variable names (synthetic
    ``_r0``/``_r1``/``v_X_Y_z`` from the hoist pass) so cosmetic
    renames don't suppress the match — see :func:`_stmt_signature`.
    """
    if len(before.methods) != 1 or len(after.methods) != 1:
        return None
    if reversed_dir:
        before, after = after, before
    b_stmts = list(before.methods[0].block.statements)
    a_stmts = list(after.methods[0].block.statements)
    if len(b_stmts) != len(a_stmts):
        return None

    b_sigs = [_stmt_signature(s) for s in b_stmts]
    a_sigs = [_stmt_signature(s) for s in a_stmts]
    if sorted(b_sigs, key=repr) != sorted(a_sigs, key=repr):
        return None

    # Bubble-sort current to match target. ``current`` holds the
    # signature of each statement at each position; we walk left to
    # right, and at each target position, find the earliest later
    # position that matches and move it via a single ``swap``.
    current = list(b_sigs)
    swaps: list[str] = []
    for target, target_sig in enumerate(a_sigs):
        if current[target] == target_sig:
            continue
        src = None
        for i in range(target + 1, len(current)):
            if current[i] == target_sig:
                src = i
                break
        if src is None:
            return None
        delta = target - src
        # EC: ``swap{1} <pos> <delta>`` moves the statement at 1-based
        # ``pos`` by ``delta`` positions (negative = toward the start).
        swaps.append(f"swap{{1}} {src + 1} {delta}.")
        current.insert(target, current.pop(src))
    return swaps


@dataclass
class _DeadDropPlan:
    """A detected dead-sample-drop diff between two single-oracle games.

    ``side`` is the EC side (1 or 2) carrying the extra dead samples;
    ``long_stmts`` is that side's full top-level statement list; ``drops``
    are the dead ``Sample`` statements to remove, in their ``long_stmts``
    order.
    """

    side: int
    long_stmts: list[frog_ast.Statement]
    drops: list[frog_ast.Sample]


def _subsequence_complement(
    long: list[frog_ast.Statement], short: list[frog_ast.Statement]
) -> list[frog_ast.Statement] | None:
    """Return the ``long`` statements not consumed when matching ``short``
    as an order-preserving subsequence (by statement signature), or ``None``
    if ``short`` is not a subsequence of ``long``.

    Matching is greedy (earliest match for each ``short`` element). When
    signatures repeat this may attribute a different statement to the
    complement than a human would, but the caller then requires every
    complement statement to be a dead sample, so a mis-attribution simply
    declines (falls back to cache/admit) rather than emitting a wrong swap.
    """
    short_sigs = [_stmt_signature(s) for s in short]
    j = 0
    complement: list[frog_ast.Statement] = []
    for stmt in long:
        if j < len(short_sigs) and _stmt_signature(stmt) == short_sigs[j]:
            j += 1
        else:
            complement.append(stmt)
    if j != len(short_sigs):
        return None
    return complement


def _stmt_uses_name(stmt: frog_ast.Statement, name: str) -> bool:
    """True if ``name`` is referenced anywhere in ``stmt`` (any position)."""
    return any(v.name == name for v in VariableCollectionVisitor().visit(stmt))


def _dead_sample_drop_plan(
    before: frog_ast.Game, after: frog_ast.Game, reversed_dir: bool = False
) -> _DeadDropPlan | None:
    """Detect a pure dead-sample-drop diff between two single-oracle games.

    Returns a plan when one side is exactly the other with one or more
    independent, never-used ``<$`` samples removed (a subsequence drop, not
    a reorder). ``reversed_dir`` follows the :func:`_permutation_swaps`
    convention: it swaps which game is the lemma's left side. Returns
    ``None`` for equal-length diffs (those are reorders — owned by
    :func:`_permutation_swaps`), non-subsequence diffs, or when any dropped
    statement is not a dead sample. Purely structural; the distribution's
    losslessness is verified by :func:`_dead_sample_drop`.
    """
    if len(before.methods) != 1 or len(after.methods) != 1:
        return None
    if reversed_dir:
        before, after = after, before
    b_stmts = list(before.methods[0].block.statements)
    a_stmts = list(after.methods[0].block.statements)
    if len(b_stmts) == len(a_stmts):
        return None
    if len(b_stmts) > len(a_stmts):
        long, short, side = b_stmts, a_stmts, 1
    else:
        long, short, side = a_stmts, b_stmts, 2
    complement = _subsequence_complement(long, short)
    if not complement:
        return None
    drops: list[frog_ast.Sample] = []
    for stmt in complement:
        if not isinstance(stmt, frog_ast.Sample) or stmt.the_type is None:
            return None
        if not isinstance(stmt.var, frog_ast.Variable):
            return None
        idx = next(i for i, s in enumerate(long) if s is stmt)
        if any(_stmt_uses_name(later, stmt.var.name) for later in long[idx + 1 :]):
            return None
        drops.append(stmt)
    return _DeadDropPlan(side, long, drops)


def _dead_sample_drop(
    before: frog_ast.Game,
    after: frog_ast.Game,
    types: tc.TypeCollector,
    eq_args: str,
    reversed_dir: bool = False,
) -> list[str] | None:
    """Synthesize an EC tactic dropping dead, lossless ``<$`` samples from
    one side of a per-transform micro hop.

    Returns the full tactic body (``proc.`` ... ``sim.``) or ``None`` when
    the diff is not a pure dead-sample-drop, or a dropped sample's
    distribution is not a simple (non-product) lossless ``d<Type>`` (every
    such distribution the exporter emits carries a ``d<Type>_ll`` axiom).
    The recipe moves each dead sample to the front (``swap{side}``), splits
    it off (``seq``), discharges it one-sided (``rnd{side}; auto;
    smt(<distr>_ll)``), then closes the identical remainder with ``sim``.
    Validated against ``tests/integration/ec_templates/dead_sample_drop.ec``.
    """
    plan = _dead_sample_drop_plan(before, after, reversed_dir)
    if plan is None:
        return None
    distrs: list[str] = []
    for sample in plan.drops:
        assert sample.the_type is not None  # guaranteed by the planner
        try:
            distr = types.distr_for(types.translate_type(sample.the_type))
        except NotImplementedError:
            return None
        if "`*`" in distr:  # product distribution — out of scope
            return None
        distrs.append(distr)
    side = plan.side
    seq_tac = "seq 1 0" if side == 1 else "seq 0 1"
    body = ["proc."]
    remaining: list[frog_ast.Statement] = list(plan.long_stmts)
    for sample, distr in zip(plan.drops, distrs):
        pos = next(i for i, s in enumerate(remaining) if s is sample) + 1
        if pos > 1:
            body.append(f"swap{{{side}}} {pos} -{pos - 1}.")
        body.append(f"{seq_tac} : ({eq_args}).")
        body.append(f"+ rnd{{{side}}}; auto; smt({distr}_ll).")
        remaining = [s for s in remaining if s is not sample]
    body.append("sim.")
    return body


def _stmt_signature(stmt: frog_ast.Statement) -> tuple[object, ...]:
    """Compact structural signature ignoring local variable names.

    Two statements have the same signature iff they have the same
    syntactic shape modulo variable-name choices. For a module-call
    assignment ``x <@ E.method(args)``, the signature is
    ``("call", "E", "method", args_signature)``; for a non-call
    deterministic assignment, ``("assign", value_signature)``; for a
    sample, ``("sample", sampled_signature)``; etc.

    The comparison is conservative: anything we can't reduce to a
    structural form falls back to comparing the raw statement strings
    (which catches identical statements but conservatively rejects
    near-misses). This means we only synthesize ``swap`` for clear
    adjacent-transposition diffs; otherwise we drop back to the
    no-swap canned chain.
    """
    if isinstance(stmt, (frog_ast.Assignment, frog_ast.Sample)):
        value = (
            stmt.value if isinstance(stmt, frog_ast.Assignment) else stmt.sampled_from
        )
        # For samples we keep the bound variable name in the signature
        # so a reorder that swaps two samples of the SAME distribution
        # (e.g. ``r0_0 <$ d; r0_1 <$ d;`` ↔ ``r0_1 <$ d; r0_0 <$ d;``)
        # is detected as a permutation. Without the name, the two
        # statements have identical signatures and ``_permutation_swaps``
        # returns no swaps — but EC's ``sim`` then fails because the
        # downstream uses are tied to specific variable names. Hoist-
        # renames are deterministic given the AST shape, so the same
        # statement at the same position in the before/after gets the
        # same name.
        bound_name = stmt.var.name if isinstance(stmt.var, frog_ast.Variable) else None
        if (
            isinstance(value, frog_ast.FuncCall)
            and isinstance(value.func, frog_ast.FieldAccess)
            and isinstance(value.func.the_object, frog_ast.Variable)
        ):
            return (
                "call",
                value.func.the_object.name,
                value.func.name,
                _expr_signature(value.args),
            )
        kind = "assign" if isinstance(stmt, frog_ast.Assignment) else "sample"
        if kind == "sample":
            return (kind, bound_name, _expr_signature(value))
        return (kind, _expr_signature(value))
    if isinstance(stmt, frog_ast.ReturnStatement):
        return ("return", _expr_signature(stmt.expression))
    if isinstance(stmt, frog_ast.VariableDeclaration):
        return ("decl", str(stmt.type))
    return ("other", repr(stmt))


def _expr_signature(
    expr: frog_ast.Expression | list[frog_ast.Expression],
) -> tuple[object, ...]:
    """Recursive structural signature for an expression.

    Variable names are mapped to ``"var"`` so name renames don't show
    up as differences. Everything else is reproduced structurally.
    """
    if isinstance(expr, list):
        return tuple(_expr_signature(e) for e in expr)
    if isinstance(expr, frog_ast.Variable):
        return ("var",)
    if isinstance(expr, frog_ast.FieldAccess):
        return ("field", _expr_signature(expr.the_object), expr.name)
    if isinstance(expr, frog_ast.FuncCall):
        return ("call", _expr_signature(expr.func), _expr_signature(expr.args))
    if isinstance(expr, frog_ast.BinaryOperation):
        return (
            "bin",
            str(expr.operator),
            _expr_signature(expr.left_expression),
            _expr_signature(expr.right_expression),
        )
    if isinstance(expr, frog_ast.Tuple):
        return ("tup", tuple(_expr_signature(v) for v in expr.values))
    if isinstance(expr, frog_ast.Type):
        # ``frog_ast`` types (e.g. ``BitStringType``) lack ``__repr__``
        # overrides, so a bare ``repr`` includes the object's memory
        # address — which makes two structurally-equal types compare
        # unequal across deepcopies. Use ``str`` (which all types
        # implement structurally) so sample/declaration signatures with
        # bitstring types match by shape rather than identity.
        return ("type", str(expr))
    return ("other", repr(expr))


# ---------------------------------------------------------------------------
# Flat-state rendering
# ---------------------------------------------------------------------------


def _flat_state_module(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    modules: mt.ModuleTranslator,
    mod_name: str,
    game: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    module_params: list[ec_ast.ModuleParam],
    emit_state_vars: bool = False,
    use_canonical_fields: bool = False,
    no_shadow_fields: bool = False,
) -> ec_ast.Module:
    """Translate one intermediate flat-state game to an EC ``Module`` AST."""
    prepared = _normalize_for_ec(
        copy.deepcopy(game), external_module_types, method_return_types
    )
    return modules.translate_flat_game(
        prepared,
        mod_name,
        external_module_types,
        module_params=module_params,
        emit_state_vars=emit_state_vars,
        use_canonical_fields=use_canonical_fields,
        no_shadow_fields=no_shadow_fields,
    )


def _render_flat_state(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    modules: mt.ModuleTranslator,
    mod_name: str,
    game: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    module_params: list[ec_ast.ModuleParam],
    emit_state_vars: bool = False,
    use_canonical_fields: bool = False,
) -> str:
    """Render one intermediate flat-state game as an EC module source string."""
    ec_module = _flat_state_module(
        modules,
        mod_name,
        game,
        external_module_types,
        method_return_types,
        module_params,
        emit_state_vars=emit_state_vars,
        use_canonical_fields=use_canonical_fields,
    )
    return "\n".join(_render_module_decl(ec_module))


_RE_LADDER = (
    "(   (split; [ by smt() | move => ? ? ? [-> ->] ])"
    " || (split; [ by smt() | move => ? ? ? [-> ?] ])"
    " || (split; [ by smt() | move => ? ? ? [? ->] ])"
    " || (split; [ by smt() | move => ? ? ? [? ?] ])"
    " || (move => ? ? [-> ->])"
    " || (move => ? ? [-> ?])"
    " || (move => ? ? [? ->])"
    " || (move => ? ? [? ?]))"
)


_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


# ---------------------------------------------------------------------------
# EC source rendering helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Stateless-scheme reorder synthesis
#
# Some canonicalization steps (notably ``Inline Local Tuple Literal``) inline a
# tuple literal whose components are abstract scheme calls. At the FrogLang
# level this is a pure inline, but the EC flat-state renderer hoists the two
# nestings differently, so the before/after EC modules differ by a *reorder of
# abstract scheme calls* (``KeyGen;KeyGen;Enc;Enc`` vs ``KeyGen;Enc;KeyGen;Enc``).
# EC's ``swap`` rejects reordering two abstract calls (they conflict on
# ``glob E``), and the reorder is genuinely unsound for a *stateful* scheme.
#
# It is sound here because the scheme is stateless (ProofFrog only validated the
# reorder for that reason). We route the equiv through the all-``Ideal``
# (stateless, hence swap-able) instantiation via a 4-hop transitivity, using the
# section-scope ``<E>_<m>_sem`` statelessness axioms emitted by the exporter:
#
#   state_1(E)      ~ state_1(Ideal)   (* leg1: call-by-call sem axioms       *)
#   state_1(Ideal)  ~ M(Ideal)         (* leg_a: EC tuple inline, same order   *)
#   M(Ideal)        ~ state_2(Ideal)   (* leg_b: pure call-level reorder       *)
#   state_2(Ideal)  ~ state_2(E)       (* leg3: symmetry + sem axioms         *)
#
# where M is ``state_1`` with the tuple literal inlined at the EC level (so it
# matches state_2 modulo the call order). See the design doc
# ``extras/docs/plans/in-progress/2026-06-01-scheme-statelessness-foundation.md``.
# ---------------------------------------------------------------------------


@dataclass
class _StatelessSynth:
    """Synthesized stateless-reorder proof for one micro."""

    module_text: str | None  # the M intermediate module (None if no tuple)
    module_name: str | None
    tactic: list[str]
    request: tuple[str, str]  # (declared module name, clone alias)


def _split_top_tuple(rhs: str) -> list[str] | None:
    """Split a top-level EC tuple literal ``(e0, e1, ...)`` into components."""
    s = rhs.strip()
    if not (s.startswith("(") and s.endswith(")")):
        return None
    depth = 0
    parts: list[str] = []
    cur = ""
    for ch in s[1:-1]:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    return parts if len(parts) >= 2 else None


def _split_top_args(args: str) -> list[str]:
    """Split a rendered EC argument list on top-level commas.

    ``"seed, ct"`` -> ``["seed", "ct"]``; respects ``(`` / ``[`` nesting so a
    tuple or nested call argument is not split mid-expression. Empty arg list
    returns ``[]``.
    """
    s = args.strip()
    if not s:
        return []
    depth = 0
    parts: list[str] = []
    cur = ""
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    return [p for p in parts if p]


def _mem_expr(expr: str, side: int) -> str:
    """``expr`` annotated at memory ``side``; bare identifiers need no parens."""
    e = expr.strip()
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", e):
        return f"{e}{{{side}}}"
    return f"({e}){{{side}}}"


def _proj_re(var: str) -> "re.Pattern[str]":
    return re.compile(r"\b" + re.escape(var) + r"\.`(\d+)")


def _has_bare_use(var: str, text: str) -> bool:
    """True if ``var`` appears in ``text`` other than as a projection ``var.`i``."""
    total = len(re.findall(r"\b" + re.escape(var) + r"\b", text))
    projs = len(_proj_re(var).findall(text))
    return total > projs


def _stmt_text(stmt: ec_ast.EcStmt) -> str:
    if isinstance(stmt, ec_ast.Assign):
        return stmt.rhs
    if isinstance(stmt, ec_ast.Call):
        return stmt.args
    if isinstance(stmt, ec_ast.Return):
        return stmt.expr
    return ""


def _subst_proj(stmt: ec_ast.EcStmt, var: str, comps: list[str]) -> ec_ast.EcStmt:
    def repl(m: "re.Match[str]") -> str:
        idx = int(m.group(1)) - 1
        return comps[idx] if 0 <= idx < len(comps) else m.group(0)

    pat = _proj_re(var)
    if isinstance(stmt, ec_ast.Assign):
        return ec_ast.Assign(stmt.var, pat.sub(repl, stmt.rhs))
    if isinstance(stmt, ec_ast.Call):
        return ec_ast.Call(stmt.var, stmt.callee, pat.sub(repl, stmt.args))
    if isinstance(stmt, ec_ast.Return):
        return ec_ast.Return(pat.sub(repl, stmt.expr))
    return stmt


def _ec_tuple_inline(
    body: list[ec_ast.EcStmt],
) -> tuple[list[ec_ast.EcStmt], bool]:
    """Inline tuple-literal local assignments at the EC level.

    For ``k <- (e0, e1, ...)`` whose later uses are all projections ``k.`i``,
    drop the assignment (and ``k``'s var decl) and replace ``k.`i`` with the
    corresponding component everywhere after. Mirrors
    ``InlineLocalTupleLiteralTransformer`` but on the rendered EC module so the
    inlined intermediate keeps the *un-hoisted* call order.
    """
    rest_text = "\n".join(_stmt_text(s) for s in body)
    inline_map: dict[str, list[str]] = {}
    inlined: set[str] = set()
    out: list[ec_ast.EcStmt] = []
    changed = False
    for idx, stmt in enumerate(body):
        if isinstance(stmt, ec_ast.Assign):
            comps = _split_top_tuple(stmt.rhs)
            if comps is not None:
                later = "\n".join(_stmt_text(s) for s in body[idx + 1 :])
                if not _has_bare_use(stmt.var, later):
                    inline_map[stmt.var] = comps
                    inlined.add(stmt.var)
                    changed = True
                    continue
        for var, comps in inline_map.items():
            stmt = _subst_proj(stmt, var, comps)
        out.append(stmt)
    out = [s for s in out if not (isinstance(s, ec_ast.VarDecl) and s.name in inlined)]
    _ = rest_text
    return out, changed


def _exec_stmts(body: list[ec_ast.EcStmt]) -> list[ec_ast.EcStmt]:
    return [s for s in body if not isinstance(s, ec_ast.VarDecl)]


def _flatten_stmts(body: list[ec_ast.EcStmt]) -> list[ec_ast.EcStmt]:
    """Every statement in ``body``, descending into both arms of each ``If``.

    For gates that ask "does this oracle contain such a call anywhere", where a
    branch-local occurrence counts as much as a top-level one -- a case-splitting
    ``decaps`` puts its encoding call inside the challenge branch.
    """
    out: list[ec_ast.EcStmt] = []
    for stmt in _exec_stmts(body):
        out.append(stmt)
        if isinstance(stmt, ec_ast.If):
            out.extend(_flatten_stmts(stmt.then_body))
            out.extend(_flatten_stmts(stmt.else_body))
    return out


def _ec_sig(stmt: ec_ast.EcStmt) -> tuple[str, ...]:
    if isinstance(stmt, ec_ast.Call):
        return ("call", stmt.callee)
    if isinstance(stmt, ec_ast.Sample):
        return ("sample",)
    if isinstance(stmt, ec_ast.Assign):
        return ("assign",)
    if isinstance(stmt, ec_ast.Return):
        return ("return",)
    return ("?",)


def _ec_perm_swaps(
    before: list[ec_ast.EcStmt], after: list[ec_ast.EcStmt]
) -> list[str] | None:
    """``swap{1}`` tactics reordering ``before``'s exec statements to ``after``.

    Matches statements by a rename-invariant signature (call callee / sample /
    assign / return) with a stable bubble sort, so same-callee statements keep
    their relative order. Returns ``None`` when the two are not a permutation.
    """
    b = _exec_stmts(before)
    a = _exec_stmts(after)
    if len(b) != len(a):
        return None
    bsig = [_ec_sig(s) for s in b]
    asig = [_ec_sig(s) for s in a]
    if sorted(map(str, bsig)) != sorted(map(str, asig)):
        return None
    cur = list(bsig)
    swaps: list[str] = []
    for target, sig in enumerate(asig):
        if cur[target] == sig:
            continue
        src = next((i for i in range(target + 1, len(cur)) if cur[i] == sig), None)
        if src is None:
            return None
        delta = target - src
        swaps.append(f"swap{{1}} {src + 1} {delta}")
        cur.insert(target, cur.pop(src))
    return swaps


def _ec_full_perm_swaps(
    before: list[ec_ast.EcStmt], after: list[ec_ast.EcStmt]
) -> list[str] | None:
    """``swap{1}`` tactics reordering ``before``'s exec statements to ``after``.

    Matches by the *full* statement signature (kind, lhs, callee, data) so each
    statement is uniquely identified -- unlike :func:`_ec_perm_swaps`, which
    matches by coarse kind/callee and so cannot distinguish two assignments.
    Used for the deterministic functional-twin middle leg, where the two fully
    functionalized bodies are statement-permutations and must be aligned exactly
    before ``sim``. Returns ``None`` when the two are not a duplicate-free
    permutation (the caller then declines the whole route).

    The left-to-right bubble sort emits only EC-acceptable swaps: both bodies are
    topological orderings of the same dependency DAG, so when statement
    ``after[target]`` is moved left to ``target``, every statement it crosses is
    a not-yet-placed ``after[k>target]`` that cannot depend on it (it currently
    precedes it in a valid order), and all of its own dependencies are already
    placed in ``[0, target)``.
    """
    b = _exec_stmts(before)
    a = _exec_stmts(after)
    if len(b) != len(a):
        return None
    bsig = [_stmt_full_sig(s) for s in b]
    asig = [_stmt_full_sig(s) for s in a]
    if len(set(bsig)) != len(bsig) or sorted(map(str, bsig)) != sorted(map(str, asig)):
        return None
    cur = list(bsig)
    swaps: list[str] = []
    for target, sig in enumerate(asig):
        if cur[target] == sig:
            continue
        src = next((i for i in range(target + 1, len(cur)) if cur[i] == sig), None)
        if src is None:
            return None
        swaps.append(f"swap{{1}} {src + 1} {target - src}.")
        cur.insert(target, cur.pop(src))
    return swaps


_LOSSLESS_DISTR_FAMILIES = ("dbs_", "dfun_")


def _app_head(expr: str) -> tuple[str, str]:
    """``(head token, rest)`` of a function application, else ``(expr, "")``."""
    stripped = expr.strip()
    match = re.match(r"([A-Za-z_][\w.]*)\s+(.*)", stripped, re.S)
    return (match.group(1), match.group(2)) if match else (stripped, "")


def _ws(expr: str) -> str:
    """``expr`` with parentheses dropped and whitespace runs collapsed.

    For comparing an EC term a route BUILDS against the same term as it appears
    in a coupling STRING, where the two differ only in whether the argument of a
    prefix application is parenthesized (``ev_m (X)`` vs ``ev_m X``) -- both are
    emitted, by the tactic builder and the coupling builder respectively.
    """
    return " ".join(expr.replace("(", " ").replace(")", " ").split())


def _unordered_conj(conjunct: str) -> frozenset[str]:
    """A conjunct's two sides as an unordered pair, whitespace- and
    paren-normalized -- for comparing what a route DERIVES against what the
    coupling STATES, which may carry the same fact the other way round."""
    return frozenset(_ws(p) for p in conjunct.split(" = "))


def _strip_outer_parens(expr: str) -> str:
    """``expr`` with one balanced enclosing paren pair removed, if any."""
    stripped = expr.strip()
    while stripped.startswith("(") and stripped.endswith(")"):
        depth = 0
        for pos, char in enumerate(stripped):
            depth += (char == "(") - (char == ")")
            if depth == 0 and pos != len(stripped) - 1:
                return stripped
        stripped = stripped[1:-1].strip()
    return stripped


def _app_args(rest: str) -> list[str]:
    """Split an application's argument text at TOP-LEVEL whitespace."""
    args: list[str] = []
    depth = 0
    cur = ""
    for char in rest:
        depth += (char == "(") - (char == ")")
        if char.isspace() and depth == 0:
            if cur:
                args.append(cur)
                cur = ""
            continue
        cur += char
    if cur:
        args.append(cur)
    return args


def _concat_chain(expr: str, op_names: set[str]) -> tuple[list[str], list[str]] | None:
    """``(ops, leaves)`` for a LEFT-NESTED concat chain, innermost op first.

    ``c3 (c2 (c1 a b) c) d`` -> ``(["c1","c2","c3"], ["a","b","c","d"])``.
    ``None`` when the expression is not such a chain -- a leaf, a different
    head, or an arity that is not two.
    """
    ops: list[str] = []
    leaves: list[str] = []
    cur = _strip_outer_parens(expr)
    for _ in range(32):
        head, rest = _app_head(cur)
        if head not in op_names:
            return None
        args = _app_args(rest)
        if len(args) != 2:
            return None
        ops.insert(0, head)
        leaves.insert(0, _strip_outer_parens(args[1]))
        inner = _strip_outer_parens(args[0])
        if _app_head(inner)[0] in op_names:
            cur = inner
            continue
        leaves.insert(0, inner)
        return ops, leaves
    return None


# The delegate object a FrogLang ``Reduction`` body composes against is always
# spelled ``challenger`` -- it is bound by the language, not declared by the
# proof (``proof_engine`` and ``semantic_analysis`` both hard-code the name), so
# the canonicalizer's ``challenger_<f>`` flat-state fields are a LANGUAGE
# constant rather than a proof-, game-, or file-specific name.
_DELEGATE_PREFIX = "challenger_"


def _module_head(expr: str) -> str:
    """The module name of an applied module expression: ``R(a, b)`` -> ``R``."""
    return expr.split("(", 1)[0].strip()


def _wrapper_delegate(expr: str) -> str:
    """The module name of a wrapper's LAST argument -- its inner challenger.

    ``RB(KEM_PQ, ..., KEM_PQ_c.KEM_INDCCA_Random(KEM_PQ))`` ->
    ``KEM_PQ_c.KEM_INDCCA_Random``. Empty when the expression takes no
    arguments.
    """
    head, _, rest = expr.partition("(")
    if not rest or not head:
        return ""
    depth = 0
    args: list[str] = []
    cur = ""
    for char in rest[:-1] if rest.endswith(")") else rest:
        if char == "," and depth == 0:
            args.append(cur)
            cur = ""
            continue
        depth += (char == "(") - (char == ")")
        cur += char
    if cur:
        args.append(cur)
    return _module_head(args[-1]) if args else ""


def _flat_name_map(
    state: frog_ast.Game, red_base: str, chal_base: str
) -> tuple[dict[str, str], str]:
    """``rendered flat field -> post-`inline *` name``, plus the delegate tag.

    The canonicalizer flattens a reduction's own state and its inlined
    delegate's into ONE field list, marking the delegate's ``<obj>@<f>`` (the
    same ``@`` convention the composite-reduction routes read); the EC renderer
    turns that into ``<obj>_<f>``. EasyCrypt, in contrast, keeps the two
    qualified by their owning MODULE. The flat states therefore give the
    structure but never the names, and this is the bridge:
    ``challenger@k`` -> ``<Chal>.k``, ``ss_PQ`` -> ``<Red>.ss_PQ``.

    Also returns the delegate object's name, which is what marks a delegate
    LOCAL -- EasyCrypt renames those outright, so no correspondence for them is
    recoverable and the caller must drop any conjunct that would need one.
    """
    out: dict[str, str] = {}
    delegate = ""
    for fld in state.fields:
        raw = fld.name
        rendered = _lower_initial(raw.replace("@", "_"))
        if "@" in raw:
            owner, own = raw.split("@", 1)
            delegate = owner
            out[rendered] = f"{chal_base}.{_lower_initial(own)}"
        else:
            out[rendered] = f"{red_base}.{rendered}"
    return out, delegate


def _lower_initial(name: str) -> str:
    """EC module globals are lowercase-initial (``RF`` -> ``rF``), matching
    ``module_translator``'s own field rename."""
    return name[0].lower() + name[1:] if name[:1].isupper() else name


def _real_name(var: str, name_map: dict[str, str], delegate: str) -> str | None:
    """The post-``inline *`` name of a flat-state variable, or ``None``.

    A flat FIELD resolves through :func:`_flat_name_map`. A flat LOCAL keeps its
    name -- unless it came from the inlined delegate, which EasyCrypt renames,
    in which case there is nothing to return and the caller must drop the
    conjunct rather than guess.
    """
    if var in name_map:
        return name_map[var]
    return None if delegate and var.startswith(f"{delegate}_") else var


_PROJ_ARG = re.compile(r"[A-Za-z_]\w*(?:\.`\d+)*")


def dead_draw_bijection_conjunct(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    oracle_name: str,
    left_game: frog_ast.Game,
    right_game: frog_ast.Game,
    left_wrapper_expr: str,
    right_wrapper_expr: str,
    types: tc.TypeCollector,
    type_of_factory: Callable[
        [dict[str, frog_ast.Type], dict[str, str]],
        Callable[[frog_ast.Expression], frog_ast.Type],
    ],
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    det_methods: dict[str, set[str]] | None = None,
    inj_methods_by_module: dict[str, set[str]] | None = None,
    clone_alias: dict[str, str] | None = None,
) -> list[str]:
    """The state-level conjuncts of a hop whose two dead draws a bijection can
    pair; ``[]`` off-shape.

    The MIRROR of :func:`kdf_substitution_key_conjunct`, and it exists for the
    same reason: the establishing ``initialize`` route can prove this
    correspondence but only if the hop's coupling asks for it, and the coupling
    is built before any tactic runs. Here the dependency runs the other way too
    -- the route DROPS the two draws unless the conjunct is stated, because
    dropping them closes the hop just as well and is what it did before.
    """
    spec = _dead_draw_bij_spec(
        mt.ModuleTranslator(types, type_of_factory),
        oracle_name,
        left_game,
        right_game,
        external_module_types,
        method_return_types,
        det_methods or {},
        inj_methods_by_module or {},
        clone_alias or {},
        types,
        left_wrapper_expr,
        right_wrapper_expr,
    )
    return list(spec.conjuncts) if spec is not None else []


# A qualified identifier. The dot must be FOLLOWED by a word character: an EC
# tuple projection is ``t.`k``, so a pattern ending in ``[\w.]*`` swallows the
# dot and turns ``_tup.`2`` into a lookup of ``_tup.`` -- which silently misses,
# leaving the projection unresolved and every downstream correspondence blind.
_IDENT_TOKENS = re.compile(r"[A-Za-z_]\w*(?:\.\w+)*")


@dataclass(frozen=True)
class _DeadDrawBij:
    """How to COUPLE two one-sided dead draws instead of dropping them.

    The mirror of the KDF-key-substitution `initialize` hop. There, the encoding
    call still sits in ``initialize`` and :func:`_synth_kdf_key_substitution`
    pairs the two draws through it. By the mirror hop the challenge KDF output
    has been replaced by a fresh sample, so ``initialize`` no longer contains the
    encoding and holds only two ONE-SIDED draws of the same distribution -- which
    the bundled-delegate reorder aligns by dropping each one-sidedly. That is
    sound (the hop's own post never mentions them) and it is exactly what
    destroys the correspondence the hop's ``decaps`` counterpart needs, because
    the two values are related by the encoding, not equal.

    ``enc_side`` is the side whose draw is the ENCODED one -- read off a
    POST-INIT oracle, where that side passes its field to the ``deterministic
    injective`` method and the other side uses its own field raw. Deriving it
    from the consumer is what makes the choice correct rather than merely
    provable: ANY bijection would make some coupling provable (the ``rnd`` map
    can be chosen to match), so the compiler cannot catch a wrong one -- only the
    oracle that consumes it can.
    """

    enc_side: int
    mod_name: str
    meth: str
    bs_name: str
    alias: str
    distr: str
    conjunct: str
    # Field-to-field correspondences the same peel proves alongside the coupled
    # draw. The KDF input of a two-component combiner carries more than the key
    # -- an ENCAPSULATION key on the UG cells -- and the consuming oracle needs
    # every one of them, not only the one the bijection relates.
    extra: tuple[str, ...] = ()

    @property
    def conjuncts(self) -> tuple[str, ...]:
        return (self.conjunct,) + self.extra

    @property
    def ev_op(self) -> str:
        return f"{self.alias}.ev_{self.meth}"


def _event_labelled_canonical(
    prefix: list[ec_ast.EcStmt], events: list[ec_ast.EcStmt]
) -> dict[str, str]:
    """``var -> value`` over a vocabulary that is comparable across two
    UNALIGNED backbones: each event result is replaced by its callee (or
    distribution) plus its OCCURRENCE INDEX among events of that identity.

    :func:`_kdf_canonical` labels by backbone POSITION, which is only
    cross-side meaningful once the two backbones have been aligned. The hop this
    serves is precisely one where they have NOT been -- one endpoint draws its
    key before its key generation and the other after its encapsulation -- so a
    positional label pairs a ciphertext with a decapsulation key. MEASURED: it
    did, and EasyCrypt rejected the resulting conjunct as ill-typed.

    The occurrence label is sound here because the route's own precondition is
    that the two sides run the same CALL MULTISET: the k-th ``KEM_PQ.keygen``
    on one side is the k-th on the other, whatever order they run in.
    """
    env = _assign_env(prefix)
    seen: Counter[str] = Counter()
    slots: dict[str, str] = {}
    for stmt in events:
        if isinstance(stmt, ec_ast.Call):
            key = f"call:{stmt.callee}"
        elif isinstance(stmt, ec_ast.Sample):
            key = f"sample:{stmt.distr}"
        else:
            continue
        slots[stmt.var] = f"#{key}#{seen[key]}"
        seen[key] += 1
    for stmt in prefix:
        if isinstance(stmt, (ec_ast.Call, ec_ast.Sample)):
            env.setdefault(stmt.var, stmt.var)
    out: dict[str, str] = {}
    for var, val in env.items():
        out[var] = _IDENT_TOKENS.sub(lambda m: slots.get(m.group(0), m.group(0)), val)
    for var, slot in slots.items():
        out[var] = slot
    return out


def _sample_holding_fields(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    modules: mt.ModuleTranslator,
    name: str,
    state: frog_ast.Game,
    init_oracle: str,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    wrapper_expr: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]] | None:
    """``({field -> distribution it was drawn from}, {field -> EC name},
    {variable -> canonical value})`` for this side's ``initialize``.

    Correspondence is by the backbone EVENT that produced the value
    (:func:`_kdf_canonical`), never by name: the draw lands in a delegate-inlined
    LOCAL and is copied into the reduction's own field under a different name.
    The canonical map is returned too, because the same vocabulary is what pairs
    the two sides' remaining FIELDS -- a mirror hop's consumer needs those as
    much as it needs the coupled draw.
    """
    proj = _project_to_method(state, init_oracle)
    if proj is None:
        return None
    mod = _flat_state_module(
        modules, name, proj, external_module_types, method_return_types, []
    )
    if not mod.procs:
        return None
    body: list[ec_ast.EcStmt] = [
        s for s in _exec_stmts(mod.procs[0].body) if not isinstance(s, ec_ast.Return)
    ]
    events: list[ec_ast.EcStmt] = [s for s in body if _is_bb_stmt(s)]
    canon = _event_labelled_canonical(body, events)
    nmap, deleg = _flat_name_map(
        state, _module_head(wrapper_expr), _wrapper_delegate(wrapper_expr)
    )
    if not deleg:
        return None
    holders: dict[str, str] = {}
    for stmt in events:
        if not isinstance(stmt, ec_ast.Sample):
            continue
        slot = canon.get(stmt.var)
        if slot is None:
            continue
        for fld in sorted(nmap):
            if canon.get(fld) == slot:
                holders[fld] = stmt.distr
    return holders, nmap, canon


def _dead_draw_bij_spec(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-return-statements,too-many-branches
    modules: mt.ModuleTranslator,
    init_oracle: str,
    left_state0: frog_ast.Game,
    right_state0: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    det_methods: dict[str, set[str]],
    inj_methods_by_module: dict[str, set[str]],
    clone_alias: dict[str, str],
    types: tc.TypeCollector | None,
    left_wrapper_expr: str,
    right_wrapper_expr: str,
) -> _DeadDrawBij | None:
    """The bijection pairing this hop's two one-sided dead draws, or ``None``.

    Read off a POST-INIT oracle, which is the only place that says which of the
    two draws is the ENCODED one: exactly one side passes a field holding its own
    ``initialize`` draw to a ``deterministic injective`` single-argument method,
    and the other side uses its corresponding field raw. Requiring that call to
    be UNIQUE across both sides is what keeps the route off a body that merely
    happens to encode something else -- the sibling hop's `decaps` also calls the
    same method, on a decapsulated secret rather than on a stored draw.

    Every remaining gate fails CLOSED: the method must be an ENDO-map whose
    result type is the very type the two draws are sampled from (checked through
    the type's own registered distribution, not by name surgery on ``d<t>``), and
    both sides must hold their draw in a nameable FIELD.
    """
    if types is None:
        return None
    sides = []
    for nm, state, wrap in (
        ("Bij_L", left_state0, left_wrapper_expr),
        ("Bij_R", right_state0, right_wrapper_expr),
    ):
        got = _sample_holding_fields(
            modules,
            nm,
            state,
            init_oracle,
            external_module_types,
            method_return_types,
            wrap,
        )
        if got is None:
            return None
        sides.append(got)
    hits: list[tuple[int, str, str, str, str]] = []
    for idx, (state, wrap) in enumerate(
        ((left_state0, left_wrapper_expr), (right_state0, right_wrapper_expr))
    ):
        holders, _nmap, _canon = sides[idx]
        for meth_node in state.methods:
            oracle = meth_node.signature.name.lower()
            if oracle == init_oracle:
                continue
            proj = _project_to_method(state, oracle)
            if proj is None:
                continue
            mod = _flat_state_module(
                modules,
                f"Bij_{idx}_{oracle}",
                proj,
                external_module_types,
                method_return_types,
                [],
            )
            if not mod.procs:
                continue
            decl_ty = {
                d.name: d.type.text
                for d in mod.procs[0].body
                if isinstance(d, ec_ast.VarDecl)
            }
            for stmt in _flatten_stmts(mod.procs[0].body):
                if not isinstance(stmt, ec_ast.Call) or "." not in stmt.callee:
                    continue
                mod_name, meth = stmt.callee.rsplit(".", 1)
                if meth not in det_methods.get(mod_name, set()):
                    continue
                if meth not in inj_methods_by_module.get(mod_name, set()):
                    continue
                args = _split_top_args(stmt.args)
                if len(args) != 1:
                    continue
                arg = args[0].strip()
                res_ty = decl_ty.get(stmt.var)
                if arg in holders and res_ty is not None:
                    hits.append((idx + 1, mod_name, meth, arg, res_ty))
    if len(set(hits)) != 1:
        return None
    enc_side, mod_name, meth, enc_field, bs_name = hits[0]
    alias = clone_alias.get(mod_name)
    if alias is None:
        return None
    enc_holders, enc_map, enc_canon = sides[enc_side - 1]
    oth_holders, oth_map, oth_canon = sides[2 - enc_side]
    distr = enc_holders.get(enc_field)
    # The result type must be the very type the two draws are sampled from. This
    # is a CHECK against the exporter's own ``bs_<w>`` / ``dbs_<w>`` naming, not
    # a derivation from it: a method that is injective but not an ENDO-map on the
    # sampled type has no bijectivity lemma, and the route must decline rather
    # than name one that will not exist.
    if distr is None or distr != f"d{bs_name}":
        return None
    oth_cands = sorted(f for f, d in oth_holders.items() if d == distr)
    if len(oth_cands) != 1:
        return None
    oth_side = 3 - enc_side
    conjunct = (
        f"{oth_map[oth_cands[0]]}{{{oth_side}}} = "
        f"{alias}.ev_{meth} {enc_map[enc_field]}{{{enc_side}}}"
    )
    # The remaining FIELD-to-FIELD correspondences, paired by canonical value --
    # whole, or a field against a COMPONENT of the other side's bundled one
    # (a reduction that runs its own key generation keeps the whole ``(ek, dk)``
    # pair in one field where the delegating side keeps only what its challenger
    # stored). MEASURED on the UG cells: their consumer needs the encapsulation
    # correspondence exactly as much as it needs the coupled draw, and without it
    # the residual goal is a CONJUNCTION -- which surfaces as "nothing to
    # rewrite" rather than as a failure to close.
    extra: list[str] = []
    drawn = set(enc_holders) | {enc_field}
    for f_e, val in sorted(enc_canon.items()):
        if f_e not in enc_map or f_e in drawn:
            continue
        hit = next(
            (k for k in sorted(oth_canon) if oth_canon[k] == val and k in oth_map),
            None,
        )
        if hit is not None:
            extra.append(f"{enc_map[f_e]}{{{enc_side}}} = {oth_map[hit]}{{{oth_side}}}")
            continue
        pm = re.fullmatch(r"(.*?)((?:\.`\d+)+)", val)
        if pm is None:
            continue
        head = next(
            (
                k
                for k in sorted(oth_canon)
                if oth_canon[k] == pm.group(1) and k in oth_map
            ),
            None,
        )
        if head is not None:
            extra.append(
                f"{enc_map[f_e]}{{{enc_side}}} = "
                f"{oth_map[head]}{{{oth_side}}}{pm.group(2)}"
            )
    return _DeadDrawBij(
        extra=tuple(dict.fromkeys(extra)),
        enc_side=enc_side,
        mod_name=mod_name,
        meth=meth,
        bs_name=bs_name,
        alias=alias,
        distr=distr,
        conjunct=conjunct,
    )


def _synth_bundled_delegate_reorder(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-return-statements
    modules: mt.ModuleTranslator,
    oracle_name: str,
    left_state0: frog_ast.Game,
    right_state0: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    ev_post: bool = False,
    coupling: str = "",
    bij: _DeadDrawBij | None = None,
) -> list[str] | None:
    """Closing tactic for a BUNDLED-DELEGATE vs EXPLICIT init hop, or ``None``.

    The CFRG `_PQ` IND-CCA shape at five instantiations (hops 2, 3, 10, 12, 13
    of ``CG_expanded_INDCCA_PQ`` and its siblings). One endpoint gets a block of
    abstract calls from a delegate ``Challenger.initialize()`` / ``.compute()``
    -- which runs ``keygen; encaps`` back to back -- while the other runs those
    same calls itself, split around its own sampling chain. So the two bodies
    are a PERMUTATION, not an alignment, and ``_synth_init_backbone_peel``
    declines (unequal backbones; its own reorder path bails outright once a
    backbone contains a sample).

    This works entirely off the FIRST FLAT STATES, which already have the
    delegate inlined -- they ARE the post-``inline *`` bodies, name for name and
    position for position -- so nothing has to model how many statements the
    challenger contributes:

    1. read both backbones; decline unless the CALL sequences are a non-trivial
       permutation of each other;
    2. try to reorder each side's calls into the other's order
       (:func:`_bundled_reorder_swaps`), each call travelling with its feeding
       and unpacking assignments;
    3. require the reordered backbones to align modulo one-sided SAMPLES
       (:func:`_sample_drop_alignment`) -- the delegates draw a shared secret /
       PRF key the other side has no counterpart for -- AND require every
       dropped sample to be DEAD for the goal (:func:`_bd_sample_dead`),
       without which the DP silently proposes dropping a merely-REORDERED draw
       on both sides and the emitted tactic runs without closing;
    4. peel tail-first: ``wp`` then ``call (_: true)`` or ``rnd`` per matched
       event, ``rnd{i}`` per one-sided sample.

    A one-sided ``rnd{i}`` leaves ``is_lossless d``, so the close is
    ``skip`` + ``smt`` naming each dropped distribution's ``_ll``; with no drops
    it is the plain ``skip => /#``. Declines when a dropped distribution is
    outside the families for which the exporter always emits an ``_ll``, and
    when the coupling carries an ``ev_`` derivation conjunct (this peel proves
    ``={res}`` per call, not a functional characterization) -- an honest admit
    beats a tactic that runs without closing.
    """
    # An ``ev_`` conjunct in the coupling normally means an honest decline: the
    # drop-and-peel proves ``={res}`` per call, never a functional
    # characterization. The one exception is the conjunct THIS route establishes
    # when it couples its two dead draws -- checked by identity, not by the mere
    # presence of ``ev_``, so any other derivation conjunct still declines.
    if ev_post and not (
        bij is not None
        and all(
            _ws(c) == _ws(bij.conjunct) for c in coupling.split(" /\\ ") if "ev_" in c
        )
    ):
        return None
    lproj = _project_to_method(left_state0, oracle_name)
    rproj = _project_to_method(right_state0, oracle_name)
    if lproj is None or rproj is None:
        return None
    lmod = _flat_state_module(
        modules, "Init_bd_L", lproj, external_module_types, method_return_types, []
    )
    rmod = _flat_state_module(
        modules, "Init_bd_R", rproj, external_module_types, method_return_types, []
    )
    if not lmod.procs or not rmod.procs:
        return None

    def _body(mod: ec_ast.Module) -> tuple[list[ec_ast.EcStmt], str]:
        # EC numbers the statements a ``proc.`` exposes; the trailing ``return``
        # is folded into the postcondition and is NOT one of them -- but its
        # expression is what the goal OBSERVES, so keep it for the liveness gate.
        body = _exec_stmts(mod.procs[0].body)
        ret = next((s.expr for s in body if isinstance(s, ec_ast.Return)), "")
        return [s for s in body if not isinstance(s, ec_ast.Return)], ret

    (l_exec, l_ret), (r_exec, r_ret) = _body(lmod), _body(rmod)
    return _bundled_reorder_core(l_exec, l_ret, r_exec, r_ret, coupling, bij)


def _couple_dead_draws(
    lb: list[ec_ast.EcStmt],
    l_bb: list[tuple[str, str]],
    r_bb: list[tuple[str, str]],
    ops: list[tuple[str, int, int]],
    distr: str,
) -> tuple[str, list[tuple[str, int, int]], int, list[ec_ast.EcStmt]] | None:
    """``(swap tactic, all-match ops, coupled ops index, moved left body)`` when
    the alignment's two one-sided drops are the SAME-distribution draws a
    bijection can pair, or ``None``.

    The two draws sit at different points in the two programs -- one endpoint's
    challenger draws its key before its key generation, the other's after its
    encapsulation -- and EC's ``rnd`` couples the two sides' LAST statements, so
    they have to be brought to the same aligned position first. A sample is
    data-independent of everything it crosses here (nothing between reads a value
    that has not been drawn, and nothing else writes its variable), so the move
    is an ordinary ``swap`` and EC validates the independence itself.

    Only the case where the LEFT draw moves DOWN is emitted; every other
    arrangement declines, so the route falls back to the one-sided drops it did
    before rather than guessing a swap direction.
    """
    drops = [(k, i, j) for k, i, j in ops if k != "match"]
    if len(drops) != 2 or {k for k, _, _ in drops} != {"dropL", "dropR"}:
        return None
    il = next(i for k, i, _ in drops if k == "dropL")
    jr = next(j for k, _, j in drops if k == "dropR")
    if l_bb[il] != ("sample", distr) or r_bb[jr] != ("sample", distr):
        return None
    l_events = [s for s in lb if _is_bb_stmt(s)]
    sample = l_events[il]
    rest = l_events[:il] + l_events[il + 1 :]
    if jr == 0 or jr > len(rest):
        return None
    anchor = rest[jr - 1]
    si, ai = lb.index(sample), lb.index(anchor)
    if si >= ai:
        return None
    moved = lb[:si] + lb[si + 1 : ai + 1] + [sample] + lb[ai + 1 :]
    new_ops = _sample_drop_alignment(_bd_events(moved), r_bb)
    if new_ops is None or any(k != "match" for k, _, _ in new_ops):
        return None
    coupled = next((n for n, (_k, _i, j) in enumerate(new_ops) if j == jr), None)
    if coupled is None:
        return None
    return f"swap{{1}} {si + 1} {ai - si}.", new_ops, coupled, moved


def _bundled_reorder_core(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
    l_exec: list[ec_ast.EcStmt],
    l_ret: str,
    r_exec: list[ec_ast.EcStmt],
    r_ret: str,
    coupling: str,
    bij: _DeadDrawBij | None = None,
) -> list[str] | None:
    """The bundled-delegate reorder tactic for two already-rendered bodies.

    Split out of :func:`_synth_bundled_delegate_reorder` so a caller that has to
    SYNTHESIZE one of the bodies -- the decaps-free-twin transitivity, whose
    first leg relates the game to the reduction at a twin the exporter renders
    but no flat state exists for -- can reuse it verbatim instead of
    reimplementing the swap/align/peel.
    """
    l_bb, r_bb = _bd_events(l_exec), _bd_events(r_exec)
    l_callees = [c for k, c in l_bb if k == "call"]
    r_callees = [c for k, c in r_bb if k == "call"]
    if l_callees == r_callees or sorted(l_callees) != sorted(r_callees):
        # Same call order (the plain peel's business) or not a permutation at
        # all (a one-sided call -- a different route's shape).
        return None
    for side, stmts, target in ((1, l_exec, r_callees), (2, r_exec, l_callees)):
        got = _bundled_reorder_swaps(stmts, target, side)
        if got is None:
            continue
        swaps, moved = got
        moved_bb = _bd_events(moved)
        new_l, new_r = (moved_bb, r_bb) if side == 1 else (l_bb, moved_bb)
        ops = _sample_drop_alignment(new_l, new_r)
        if ops is None:
            continue
        # COUPLE the two dead draws rather than dropping them, when a bijection
        # relates them. The drops are sound but lossy: the hop's own post never
        # mentions the draws, so it closes either way, while its ``decaps``
        # counterpart needs the correspondence and cannot recover it afterwards.
        if bij is not None:
            got2 = _couple_dead_draws(
                moved if side == 1 else l_exec, new_l, new_r, ops, bij.distr
            )
            if got2 is not None:
                align, c_ops, coupled, c_left = got2
                c_bb = _bd_events(c_left)
                f, finv = (
                    (bij.ev_op, "_bij_g")
                    if bij.enc_side == 1
                    else ("_bij_g", bij.ev_op)
                )
                c_peel: list[str] = []
                for n, (_k, i, _j) in reversed(list(enumerate(c_ops))):
                    c_peel.append("wp.")
                    if n == coupled:
                        c_peel.append(f"rnd {f} {finv}.")
                    else:
                        c_peel.append(
                            "call (_: true)." if c_bb[i][0] == "call" else "rnd."
                        )
                # The reorder may have been applied to EITHER side; the
                # alignment swap always moves the LEFT draw, and the body it is
                # computed against is the left one whichever side was reordered.
                return [
                    f"have [_bij_g [_bij_can _bij_inv]] := "
                    f"{bij.mod_name}_{bij.meth}_bij.",
                    "proc.",
                    "inline *.",
                    *swaps,
                    align,
                    *c_peel,
                    "skip => /#.",
                ]
        l_events = [s for s in (moved if side == 1 else l_exec) if _is_bb_stmt(s)]
        r_events = [s for s in (r_exec if side == 1 else moved) if _is_bb_stmt(s)]
        dropped: list[ec_ast.Sample] = []
        peel: list[str] = []
        for kind, i, j in reversed(ops):
            peel.append("wp.")
            if kind == "match":
                peel.append("call (_: true)." if new_l[i][0] == "call" else "rnd.")
                continue
            side_stmts, ret = (
                (moved if side == 1 else l_exec, l_ret)
                if kind == "dropL"
                else (r_exec if side == 1 else moved, r_ret)
            )
            events = l_events if kind == "dropL" else r_events
            stmt = events[i if kind == "dropL" else j]
            if not isinstance(stmt, ec_ast.Sample):
                return None
            if not _bd_sample_dead(side_stmts, side_stmts.index(stmt), ret, coupling):
                return None
            dropped.append(stmt)
            peel.append("rnd{1}." if kind == "dropL" else "rnd{2}.")
        if not dropped:
            return ["proc.", "inline *.", *swaps, *peel, "skip => /#."]
        distrs = sorted({s.distr for s in dropped})
        if not all(d.startswith(_LOSSLESS_DISTR_FAMILIES) for d in distrs):
            return None
        lls = " ".join(f"{d}_ll" for d in distrs)
        return ["proc.", "inline *.", *swaps, *peel, "skip.", f"smt({lls})."]
    return None


def _same_shape(a: list[ec_ast.EcStmt], b: list[ec_ast.EcStmt]) -> bool:
    """Whether two bodies have IDENTICAL statement STRUCTURE -- same kinds in the
    same order, same callee per call, same if-nesting -- differing only in the
    EXPRESSIONS statements carry.

    This is what makes the structural peel applicable and ``sim`` not: ``sim``
    relates globals by name, so a body reading ``R.corr.`3`` cannot be matched
    against one reading ``G.kem_ct`` however the coupling relates them, while a
    peel walks the shared skeleton and hands each differing expression to the
    closing ``smt`` with the coupling in scope.
    """
    a_e, b_e = _exec_stmts(a), _exec_stmts(b)
    if len(a_e) != len(b_e):
        return False
    for x, y in zip(a_e, b_e):
        if type(x) is not type(y):  # pylint: disable=unidiomatic-typecheck
            return False
        if isinstance(x, ec_ast.Call) and x.callee != cast(ec_ast.Call, y).callee:
            return False
        if isinstance(x, ec_ast.Sample) and x.distr != cast(ec_ast.Sample, y).distr:
            return False
        if isinstance(x, ec_ast.If):
            y_if = cast(ec_ast.If, y)
            if not _same_shape(x.then_body, y_if.then_body) or not _same_shape(
                x.else_body, y_if.else_body
            ):
                return False
    return True


def _straight_peel(body: list[ec_ast.EcStmt]) -> list[str]:
    """Tail-first ``wp``/couple peel for a branch-free run of statements.

    Each round's leading ``wp`` absorbs the deterministic assignments below the
    coupled statement, so a trailing assignment needs no separate step -- but a
    run with NO call or sample has no ``wp`` at all, and ``skip`` would then hit
    a non-empty statement list. Those close with ``auto``.
    """
    tac: list[str] = []
    for stmt in reversed(_exec_stmts(body)):
        if isinstance(stmt, ec_ast.Call):
            tac.append("wp; call (_: true).")
        elif isinstance(stmt, ec_ast.Sample):
            tac.append("wp; rnd.")
    if not tac:
        return ["auto."]
    # The TRAILING ``wp`` is not decoration. Each round's ``wp`` runs BEFORE its
    # coupling, so it absorbs the assignments BELOW that statement -- but an
    # assignment ABOVE the first call (``ct_PQ <- ct.`1``, present in the
    # two-KEM combiners' `decaps` and absent in the one-KEM ones) is left
    # standing, and ``skip`` then fails with "left instruction list is not
    # empty". Measured on CK/UK `_expanded_INDCCA_PQ`/`_T` while CG/UG passed.
    tac.append("wp; skip => /#.")
    return tac


def _sim_leaf(body: list[ec_ast.EcStmt]) -> list[str]:
    """Leaf finisher for the RENAMED-FIELD peel: ``wp; sim``.

    Unlike ``_straight_peel``'s per-call ladder this tolerates the two sides
    holding DIFFERENT NUMBERS of deterministic assignments, which is exactly
    what ``inline *`` creates when one side reaches a value through a delegate
    call the other has folded into an expression (the KDF-PRF hops:
    ``rest0 <- rest; _r13 <- rF rest0; _r7 <- Some _r13`` against a lone
    ``_r7 <- Some (rF rest)``). ``wp`` absorbs both runs whatever their length,
    leaving the two lock-step abstract calls for ``sim``; and ``sim`` DOES relate
    differently-owned globals -- ``Mpv2.of_form`` accepts any ``pv{1} = pv{2}``
    pair -- so the coupling's ``G.seed_T{2} = R.seed_T{1}`` is usable by it.

    A branch with no call or sample has nothing for ``sim`` to align and its
    post is no longer an equality set once ``wp`` has run (``sim`` then fails
    with "cannot infer the set of equalities"); those close with ``auto``.
    """
    if not any(isinstance(s, (ec_ast.Call, ec_ast.Sample)) for s in _exec_stmts(body)):
        return ["auto."]
    return ["wp; sim."]


def _guard_loop(chal_side: str) -> str:
    """Eliminate however many DEAD guards ``inline *`` exposed on ``chal_side``.

    A reduction that FORWARDS an oracle to its challenger gains, once inlined,
    the challenger's own refusal test (``ct = ctStar``, false under the enclosing
    branch) and the reduction's option handling (a literal ``if (false)``).
    Neither exists on the game side.

    Written as a ZERO-or-more loop over a code-position PATTERN, which is what
    makes it safe to emit at every leaf: ``do ?`` is a no-op where there are no
    dead guards, ``^if`` needs no index, and a guard that is NOT provably false
    fails the side goal and stops the loop rather than being wrongly discarded.
    So this never has to know how many guards there are -- which matters,
    because the flat states do not model them faithfully (the flat body carries
    three ``if``s where the rendered module has two).
    """
    return f"do ? (rcondf{{{chal_side}}} ^if; first by move=> &m; auto => /#)."


def _loop_leaf(body: list[ec_ast.EcStmt], chal_side: str) -> list[str]:
    """Leaf finisher for the FORWARDING peel: dead-guard loop, then couple.

    Uses the ``do !`` call loop rather than ``_straight_peel``'s one line per
    call so the two sides need not hold the same NUMBER of calls -- after the
    guard loop they do here, but the loop form does not depend on it. A leaf
    carrying a sample falls back to ``_straight_peel``, which knows to ``rnd``.
    """
    stmts = _exec_stmts(body)
    if not any(isinstance(s, (ec_ast.Call, ec_ast.Sample)) for s in stmts):
        # No coupled statement, so no dead guard can be in the way either: this
        # is the ``ct = ctStar -> None`` branch, identical on both sides. Emitting
        # the guard loop here is what the validated script does NOT do, and the
        # probe that said it was harmless turned out to be unfaithful (see
        # ``_synth_forwarded_oracle_peel``), so match the script exactly.
        return ["auto."]
    if any(isinstance(s, ec_ast.Sample) for s in stmts):
        return [_guard_loop(chal_side), *_straight_peel(stmts)]
    return [
        _guard_loop(chal_side),
        "do ! (wp; call (_: true)).",
        "wp; skip => /#.",
    ]


def _if_prefixes_agree(
    game_body: list[ec_ast.EcStmt], red_body: list[ec_ast.EcStmt]
) -> bool:
    """Whether the REDUCTION side splits where the GAME side does, at the same
    index, everywhere the game splits.

    This is what licenses the forwarding peel's NUMERIC ``seq idx idx``. It is
    deliberately ASYMMETRIC, because the route exists precisely for bodies that
    differ: once the game reaches a leaf, the reduction may have any number of
    extra ``if``s there (the inlined challenger's dead guards) and that is fine
    -- the leaf's guard loop eliminates them and its length-independent closers
    do not care. What must line up is only the run of statements BEFORE each
    branch the peel actually splits on.

    A symmetric version of this check declines every real case: the reduction's
    else-branch always has the extra guards.
    """
    # Drop leading ``<var> <- witness`` SEEDS first. ``_initialize_conditional_
    # result`` adds one where EC cannot see that an oracle assigns its result on
    # every path, and it lands in the FLAT state on one side only -- the rendered
    # module does not carry it (the validated script's ``if`` applies straight
    # after ``inline *``). Counting it would offset every index below by one.
    g_e = _drop_witness_seeds(_exec_stmts(game_body))
    r_e = _drop_witness_seeds(_exec_stmts(red_body))
    gi = next((i for i, s in enumerate(g_e) if isinstance(s, ec_ast.If)), None)
    if gi is None:
        # GAME LEAF. The leaf closes with ``do ! (wp; call (_: true)); wp; skip
        # => /#``, which couples the two sides' calls PAIRWISE -- so if the
        # reduction's matching leaf is branch-free (hence faithfully modelled
        # here) it must hold the SAME NUMBER of calls. MEASURED: a
        # `CK_expanded_INDCCA_T` `decaps` leaf has 4 calls against the
        # reduction's 5, the loop cannot align them, and the trailing
        # ``skip => /#`` fails -- a BLOCKED export where an admit was honest.
        #
        # Only checked when the reduction leaf has NO ``if``: where it does, the
        # flat state is not a faithful model (it carries dead guards the rendered
        # module lacks) and the guard loop handles it, so a count taken there
        # would be meaningless.
        if not any(isinstance(s, ec_ast.If) for s in r_e):
            g_calls = sum(1 for s in g_e if isinstance(s, ec_ast.Call))
            r_calls = sum(1 for s in r_e if isinstance(s, ec_ast.Call))
            if g_calls != r_calls:
                return False
        return True
    ri = next((i for i, s in enumerate(r_e) if isinstance(s, ec_ast.If)), None)
    if ri != gi:
        return False
    g_if, r_if = cast(ec_ast.If, g_e[gi]), cast(ec_ast.If, r_e[gi])
    return _if_prefixes_agree(g_if.then_body, r_if.then_body) and _if_prefixes_agree(
        g_if.else_body, r_if.else_body
    )


def _left_driven_peel(
    game_body: list[ec_ast.EcStmt], chal_side: str
) -> list[str] | None:
    """The forwarding peel, driven ENTIRELY by the GAME body's ``if``-tree.

    Deliberately never inspects the reduction's body. The reduction side differs
    from the game by dead guards that ``inline *`` exposes, and the flat state
    mis-models them, so anything counted there would be wrong; instead every
    position is a PATTERN (``seq ^if ^if``, ``rcondf{i} ^if``) and the dead
    guards are eliminated by a loop that lets EasyCrypt decide how many there
    are. Validated end to end in ``ec_templates/
    indcca_decaps_oracle_forwarding_NOTES.txt``.
    """
    l_e = _exec_stmts(game_body)
    idx = next((i for i, s in enumerate(l_e) if isinstance(s, ec_ast.If)), None)
    if idx is None:
        return _loop_leaf(l_e, chal_side)
    if any(isinstance(s, ec_ast.If) for s in l_e[idx + 1 :]):
        # A second branch after the first is a shape this route has not been
        # validated on; decline rather than emit a peel that may not close.
        return None
    l_if = cast(ec_ast.If, l_e[idx])
    then_tac = _left_driven_peel(l_if.then_body, chal_side)
    else_tac = _left_driven_peel(l_if.else_body, chal_side)
    if then_tac is None or else_tac is None:
        return None
    inner = ["if; 1: smt().", *then_tac, *else_tac]
    if idx == 0:
        return inner
    prefix = l_e[:idx]
    bound = {
        s.var
        for s in prefix
        if isinstance(s, (ec_ast.Assign, ec_ast.Sample, ec_ast.Call))
    }
    live = sorted(_branch_reads(l_if) & bound)
    inv = "#pre" + (f" /\\ ={{{', '.join(live)}}}" if live else "")
    # NUMERIC ``seq idx idx``, not the ``seq ^if ^if`` pattern. The pattern form
    # compiled on every cut-down probe and then FAILED in the real export ("invalid
    # last instruction" on the ``call`` right after it): it resolves to a different
    # split point there, leaving the branch itself in the first part. The
    # game-side index is what the hand-validated script used, and the two sides'
    # prefixes agree at this point -- ``_synth_forwarded_oracle_peel`` checks that
    # rather than assuming it.
    return [f"seq {idx} {idx} : ({inv}).", *_straight_peel(prefix), *inner]


def _shape_peel(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    l_body: list[ec_ast.EcStmt],
    r_body: list[ec_ast.EcStmt],
    *,
    sim_leaves: bool = False,
    forbid: frozenset[str] = frozenset(),
    extra_inv: str = "",
    leaf: Callable[[list[ec_ast.EcStmt]], list[str] | None] | None = None,
) -> list[str] | None:
    """The peel for two same-shape bodies, recursing through ``if``s.

    A leading branch-free run before an ``if`` is split off with ``seq``, whose
    invariant is ``#pre`` plus equality of the locals the branch actually reads
    -- the only names emitted, and they are the module's OWN rendered locals.

    ``sim_leaves`` swaps the branch-free finisher from ``_straight_peel``'s
    per-call ladder to ``_sim_leaf``; ``forbid`` names identifiers that must not
    appear in a ``seq`` prefix. Both exist for the renamed-field variant, which
    prefixes the peel with ``inline *`` -- see ``_synth_sim_field_rename`` for
    why ``forbid`` is what keeps the ``seq`` INDICES honest.

    ``extra_inv`` is appended to every ``seq`` invariant, and ``leaf`` may claim
    a branch-free run and finish it itself. Both exist for the RO-reprogramming
    variant, whose coupling is an implication rather than an equality set: the
    branch that reads the random function has to discharge that implication's
    hypothesis, which needs facts a bare ``#pre`` drops. Callers that pass none
    of the four get the historical behaviour verbatim.
    """
    l_e, r_e = _exec_stmts(l_body), _exec_stmts(r_body)
    idx = next((i for i, s in enumerate(l_e) if isinstance(s, ec_ast.If)), None)
    if idx is None:
        claimed = leaf(l_e) if leaf is not None else None
        if claimed is not None:
            return claimed
        return _sim_leaf(l_e) if sim_leaves else _straight_peel(l_e)
    if any(isinstance(s, ec_ast.If) for s in l_e[idx + 1 :]):
        # A second branch after the first is a shape this route has not been
        # validated on; decline rather than emit a peel that may not close.
        return None
    l_if, r_if = cast(ec_ast.If, l_e[idx]), cast(ec_ast.If, r_e[idx])
    kw = {
        "sim_leaves": sim_leaves,
        "forbid": forbid,
        "extra_inv": extra_inv,
        "leaf": leaf,
    }
    then_tac = _shape_peel(l_if.then_body, r_if.then_body, **kw)  # type: ignore[arg-type]
    else_tac = _shape_peel(l_if.else_body, r_if.else_body, **kw)  # type: ignore[arg-type]
    if then_tac is None or else_tac is None:
        return None
    inner = ["if; 1: smt().", *then_tac, *else_tac]
    if idx == 0:
        return inner
    prefix = l_e[:idx]
    if forbid and any(
        forbid & set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", _shape_stmt_text(s)))
        for s in prefix + r_e[:idx]
    ):
        return None
    bound = {
        s.var
        for s in prefix
        if isinstance(s, (ec_ast.Assign, ec_ast.Sample, ec_ast.Call))
    }
    live = sorted(_branch_reads(l_if) & bound)
    inv = "#pre" + (f" /\\ ={{{', '.join(live)}}}" if live else "") + extra_inv
    return [f"seq {idx} {idx} : ({inv}).", *_straight_peel(prefix), *inner]


def _branch_reads(node: ec_ast.If) -> set[str]:
    """Every identifier the guard or either branch of ``node`` mentions."""
    out = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", node.guard))
    for stmt in _exec_stmts(node.then_body) + _exec_stmts(node.else_body):
        if isinstance(stmt, ec_ast.If):
            out |= _branch_reads(stmt)
            continue
        out |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", _stmt_text(stmt)))
    return out


def _shape_stmt_text(stmt: ec_ast.EcStmt) -> str:
    """``_stmt_text`` extended through ``if`` guards and branches, so a scan for
    packed-field projections sees the ones inside a branch."""
    if isinstance(stmt, ec_ast.If):
        inner = _exec_stmts(stmt.then_body) + _exec_stmts(stmt.else_body)
        return " ".join([stmt.guard] + [_shape_stmt_text(s) for s in inner])
    return _stmt_text(stmt)


def _differing_tokens(
    l_body: list[ec_ast.EcStmt], r_body: list[ec_ast.EcStmt]
) -> set[str]:
    """Identifiers appearing in one body's statement but not its counterpart.

    Walks the two SAME-SHAPE bodies in lockstep (guards and both branches of an
    ``if`` included) and returns the symmetric difference of each statement
    pair's tokens -- i.e. exactly the references the closing ``smt`` must bridge
    from the coupling, which is also what the arrow-typed-field gate inspects.
    """
    out: set[str] = set()
    for x, y in zip(_exec_stmts(l_body), _exec_stmts(r_body)):
        if isinstance(x, ec_ast.If) and isinstance(y, ec_ast.If):
            gx = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", x.guard))
            gy = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", y.guard))
            out |= gx ^ gy
            out |= _differing_tokens(x.then_body, y.then_body)
            out |= _differing_tokens(x.else_body, y.else_body)
            continue
        tx = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", _stmt_text(x)))
        ty = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", _stmt_text(y)))
        out |= tx ^ ty
    return out


class _ShapePair(NamedTuple):
    """The two rendered same-shape bodies of one oracle, plus what the routes
    over them gate on."""

    l_body: list[ec_ast.EcStmt]
    r_body: list[ec_ast.EcStmt]
    diff: set[str]
    fn_fields: set[str]
    field_names: set[str]


class _ReprogramFacts(NamedTuple):
    """The RO-reprogramming conjunct of a hop's coupling, taken apart.

    The consuming oracle has to discharge that conjunct's HYPOTHESIS -- "the
    queried KDF input is off the challenge one" -- and everything it needs to do
    so is already written in the conjunct, so it is read back rather than
    re-derived."""

    dom: str
    enc_op: str
    ct_arg: str
    ct_comp: int
    ct_mem: str


def _coupling_has_implication(coupling: str) -> bool:
    """True when ``coupling`` is not a plain set of equalities.

    ``sim`` infers its equality set from the coupling and refuses anything
    else -- interactively it answers *cannot recognize ... as a set of
    equalities*, and inside a whole-oracle body it fails later with *cannot
    infer the set of equalities*. A quantifier or an implication is the
    signature: the random-oracle reprogramming conjunct is
    ``forall (p : ...), <guard> => rF{1} p = rF{2} p``.

    Any route whose leaves are ``sim`` must consult this, or it emits a tactic
    that runs and leaves the goal open.
    """
    return "forall" in coupling or "=>" in coupling


class _GuardedBody(NamedTuple):
    """A ``decaps``-shaped oracle body: one top-level refusal guard, one branch."""

    guard: str
    body: list[ec_ast.EcStmt]


def _bd_sample_dead(
    stmts: list[ec_ast.EcStmt], pos: int, ret: str, coupling: str
) -> bool:
    """Whether the sample at ``stmts[pos]`` cannot influence anything the hop's
    goal observes -- its ``return`` expression or its coupling.

    THIS IS THE SOUNDNESS GATE OF THE ONE-SIDED ``rnd{i}`` DROP, and it exists
    because distribution and position do not distinguish the two cases:

    * a genuinely DEAD draw the other side simply does not make (the KDF
      challenger's PRF key, the KEM challenger's overwritten shared secret) --
      dropping it one-sidedly is right;
    * the SAME draw, merely REORDERED across some calls. A monotone alignment
      cannot match it, so the min-drops DP proposes dropping it on BOTH sides;
      that runs, but leaves a residual demanding two independent draws be equal.
      Measured on ``CK_expanded_INDCCA_T`` ``hop_9_initialize``: EC rejects it
      three different closers deep, because the goal is false, not hard.

    Forward-taint the sampled variable through every later statement that reads
    it, then require the taint to touch neither the return expression nor the
    coupling text. Textual and therefore conservative: a name that merely looks
    like a tainted one declines the route, which costs an admit, never a wrong
    tactic.

    Taint is tracked PER TUPLE COMPONENT, and that precision is load-bearing
    rather than an optimization. The delegates repack their whole result into
    one tuple (``_tup <- (ek, ssStar, ctStar)``) and the reduction then projects
    every component out of it, so whole-variable taint marks a dead shared
    secret as reaching the encapsulation key and declines every genuine case.
    """
    seed = stmts[pos]
    if not isinstance(seed, ec_ast.Sample):
        return False
    tainted = {seed.var}
    # ``var -> tainted 1-based component indices`` for a tuple-literal assign.
    parts: dict[str, set[int]] = {}

    def _reads(stmt: ec_ast.EcStmt) -> set[str]:
        return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", _stmt_text(stmt)))

    for stmt in stmts[pos + 1 :]:
        if not isinstance(stmt, (ec_ast.Assign, ec_ast.Sample, ec_ast.Call)):
            continue
        if isinstance(stmt, ec_ast.Assign):
            lit = _top_level_tuple_parts(stmt.rhs)
            if lit is not None:
                hit = {
                    k
                    for k, part in enumerate(lit, start=1)
                    if set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", part)) & tainted
                    or any(
                        idx in parts.get(name, set())
                        for name, idx in _projections(part)
                    )
                }
                if hit:
                    parts[stmt.var] = hit
                continue
            proj = _projections(stmt.rhs)
            if proj and not (_reads(stmt) - {stmt.var} - {n for n, _ in proj}):
                if any(idx in parts.get(name, set()) for name, idx in proj):
                    tainted.add(stmt.var)
                if not _reads(stmt) & tainted:
                    continue
        if _reads(stmt) & tainted:
            tainted.add(stmt.var)
    observed = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", f"{ret} {coupling}"))
    if tainted & observed:
        return False
    # A tuple variable that is itself observed leaks every tainted component.
    return not any(idxs for name, idxs in parts.items() if name in observed)


def _top_level_tuple_parts(rhs: str) -> list[str] | None:
    """The components of a top-level tuple literal ``(a, b, c)``, else ``None``."""
    text = rhs.strip()
    if not (text.startswith("(") and text.endswith(")")):
        return None
    # ``_top_level_args`` takes the WHOLE parenthesized expression and finds its
    # own outermost parens -- handing it the already-stripped inner text makes
    # it return ``[]``.
    parts = _top_level_args(text)
    return parts if len(parts) > 1 else None


def _projections(expr: str) -> list[tuple[str, int]]:
    """``(base, 1-based index)`` for each ``t.`k`` projection in ``expr``."""
    return [
        (m.group(1), int(m.group(2)))
        for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\.`([0-9]+)", expr)
    ]


def _bd_events(stmts: list[ec_ast.EcStmt]) -> list[tuple[str, str]]:
    """The backbone of ``stmts`` as CROSS-SIDE comparable events: a call by its
    callee, a sample by its DISTRIBUTION.

    :func:`_call_sample_backbone` tags a sample by its bound VARIABLE, which is
    a within-side signal (it detects a sample reorder on one side). Across two
    sides the same draw carries different local names, so matching on the
    variable never succeeds -- but matching on the bare kind is WRONG in the
    other direction: it happily pairs a seed draw with a shared-secret draw,
    emitting an `rnd` whose distribution-equality side condition is false. The
    distribution is the right granularity.
    """
    out: list[tuple[str, str]] = []
    for stmt in stmts:
        if isinstance(stmt, ec_ast.Call):
            out.append(("call", stmt.callee))
        elif isinstance(stmt, ec_ast.Sample):
            out.append(("sample", stmt.distr))
    return out


def _is_bb_stmt(stmt: ec_ast.EcStmt) -> bool:
    """Whether ``stmt`` contributes a :func:`_bd_events` event."""
    return isinstance(stmt, (ec_ast.Call, ec_ast.Sample))


def _stmt_travel_block(
    stmts: list[ec_ast.EcStmt], pos: int, local_vars: set[str]
) -> tuple[int, int]:
    """The contiguous block that must travel with the call at ``stmts[pos]``.

    Extends BACKWARDS over immediately-preceding assignments whose written
    variable the block reads (they define the call's arguments -- moving the
    call alone would leave it reading an undefined local) and FORWARDS over
    immediately-following assignments that read what the block writes (they
    unpack its tuple result). Anything else -- a sample, another call -- stops
    the extension.
    """
    start = pos
    while start > 0 and isinstance(stmts[start - 1], ec_ast.Assign):
        written = _ec_stmt_rw(stmts[start - 1], local_vars)[1]
        if any(written & _ec_stmt_rw(s, local_vars)[0] for s in stmts[start : pos + 1]):
            start -= 1
        else:
            break
    end = pos
    while end + 1 < len(stmts) and isinstance(stmts[end + 1], ec_ast.Assign):
        reads = _ec_stmt_rw(stmts[end + 1], local_vars)[0]
        if any(reads & _ec_stmt_rw(s, local_vars)[1] for s in stmts[pos : end + 1]):
            end += 1
        else:
            break
    return start, end


def _bundled_reorder_swaps(
    stmts: list[ec_ast.EcStmt], target_callees: list[str], side: int
) -> tuple[list[str], list[ec_ast.EcStmt]] | None:
    """``swap{side} [a..b] d`` tactics putting ``stmts``' abstract calls into
    ``target_callees`` order, each call travelling with its feeding and
    unpacking assignments (:func:`_stmt_travel_block`).

    A selection sort that only ever moves a block UP, to sit immediately after
    the previously-placed target call -- so every crossed statement is one the
    block does not yet depend on. Each move is additionally ``_ec_indep``
    -validated against every crossed statement, so a data conflict or a
    same-module call declines the route (``None``) rather than emitting a swap
    EasyCrypt will reject. Returns the swaps and the reordered statements.

    EC accepts a swap that commutes two ABSTRACT module calls as long as the
    modules are mutually restricted, which the exporter's ``declare module``
    chain already emits; ``_ec_indep``'s same-module test is what keeps the two
    calls of ONE module in order. Tripwire:
    ``ec_templates/bundled_delegate_encaps_reorder.ec``.
    """
    local = _ec_local_vars(stmts)
    cur = list(stmts)
    swaps: list[str] = []
    for slot, want in enumerate(target_callees):
        calls = [(i, s.callee) for i, s in enumerate(cur) if isinstance(s, ec_ast.Call)]
        if len(calls) != len(target_callees):
            return None
        if calls[slot][1] == want:
            continue
        src = next((i for i, c in calls[slot + 1 :] if c == want), None)
        if src is None:
            return None
        b_0, b_1 = _stmt_travel_block(cur, src, local)
        ins = 0 if slot == 0 else calls[slot - 1][0] + 1
        if ins > b_0:
            return None
        block, crossed = cur[b_0 : b_1 + 1], cur[ins:b_0]
        if not all(_ec_indep(m, x, local) for m in block for x in crossed):
            return None
        swaps.append(f"swap{{{side}}} [{b_0 + 1}..{b_1 + 1}] {ins - b_0}.")
        del cur[b_0 : b_1 + 1]
        cur[ins:ins] = block
    return swaps, cur


def _sample_drop_alignment(
    l_bb: list[tuple[str, str]], r_bb: list[tuple[str, str]]
) -> list[tuple[str, int, int]] | None:
    """Align two backbones allowing only whole SAMPLES to be dropped one-sidedly.

    Returns the ordered op list (``match`` / ``dropL`` / ``dropR``) using the
    fewest drops, or ``None`` when no such alignment exists -- notably when a
    CALL is one-sided, which needs a glob-preservation drop this route does not
    do. A dropped sample becomes a one-sided ``rnd{i}``, which EC discharges
    from the distribution's losslessness; that is sound whether or not the draw
    is really dead, because a LIVE one leaves a residual EC then refuses to
    close (a visible reject, never a false accept).
    """
    l_k, r_k = l_bb, r_bb
    n, m = len(l_k), len(r_k)
    inf = n + m + 1
    dp = [[inf] * (m + 1) for _ in range(n + 1)]
    dp[n][m] = 0
    for i in range(n, -1, -1):
        for j in range(m, -1, -1):
            if i == n and j == m:
                continue
            best = inf
            if i < n and j < m and l_k[i] == r_k[j]:
                best = min(best, dp[i + 1][j + 1])
            if i < n and l_k[i][0] == "sample":
                best = min(best, 1 + dp[i + 1][j])
            if j < m and r_k[j][0] == "sample":
                best = min(best, 1 + dp[i][j + 1])
            dp[i][j] = best
    if dp[0][0] >= inf:
        return None
    ops: list[tuple[str, int, int]] = []
    i = j = 0
    while i < n or j < m:
        if i < n and j < m and l_k[i] == r_k[j] and dp[i][j] == dp[i + 1][j + 1]:
            ops.append(("match", i, j))
            i += 1
            j += 1
        elif i < n and l_k[i][0] == "sample" and dp[i][j] == 1 + dp[i + 1][j]:
            ops.append(("dropL", i, -1))
            i += 1
        elif j < m and r_k[j][0] == "sample" and dp[i][j] == 1 + dp[i][j + 1]:
            ops.append(("dropR", -1, j))
            j += 1
        else:  # pragma: no cover -- unreachable once dp says an alignment exists
            return None
    return ops


def _align_call_order_swaps(
    exec_stmts: list[ec_ast.EcStmt],
    target_callees: list[str],
    side: int,
) -> list[str] | None:
    """``swap{side}`` tactics reordering ``exec_stmts``' abstract calls so their
    callee sequence becomes ``target_callees``, leaving every non-call statement
    in place.

    Used by the init-backbone peel when the two endpoints run the SAME multiset
    of abstract keygens but in a DIFFERENT ORDER -- the two-KEM CFRG binding
    init: the game interleaves ``[KEM_PQ, KEM_T, KEM_PQ, KEM_T]`` (hybrid
    keypair 0 then keypair 1) while the reduction blocks
    ``[KEM_PQ, KEM_PQ, KEM_T, KEM_T]`` (its inner PQ challenger does both PQ
    keygens, then it does both T keygens). ``call (_: true)`` couples the two
    sides' current *last* calls, so it requires them to be the same procedure;
    aligning the callee order first makes the lockstep peel pair like with like
    (otherwise EC rejects ``KEM_PQ.keygen`` ~ ``KEM_T.keygen`` -- "should be
    equal").

    Each move slides a call UP to its target slot (selection sort). A keygen call
    has no result-reading predecessor, so moving it up only crosses statements
    that neither read its not-yet-defined result nor are read by it; the move is
    additionally ``_ec_indep``-validated against every crossed statement (a
    same-module call, or a genuine data conflict, is rejected -> ``None``). The
    executable-statement positions of a rendered flat-state body match EC's
    post-``inline *`` numbering verbatim (validated against ``CK_expanded_LEAK``
    hop_0_initialize), so the emitted ``swap{side} p k`` land on the intended
    statements. Returns ``[]`` when the calls are already in ``target_callees``
    order (the byte-identical same-order path), and ``None`` when the callees are
    not a permutation of ``target_callees`` or a required move is not
    independent. Tripwire: ``ec_templates/two_kem_init_reorder.ec``.
    """
    stmts = list(exec_stmts)
    local_vars = _ec_local_vars(stmts)

    def _call_slots() -> list[tuple[int, str]]:
        return [
            (i, s.callee) for i, s in enumerate(stmts) if isinstance(s, ec_ast.Call)
        ]

    if sorted(c for _, c in _call_slots()) != sorted(target_callees):
        return None
    swaps: list[str] = []
    for slot, want in enumerate(target_callees):
        calls = _call_slots()
        pos = calls[slot][0]
        if calls[slot][1] == want:
            continue
        src = next((i for i, c in calls[slot + 1 :] if c == want), None)
        if src is None:
            return None
        moving = stmts[src]
        if not all(_ec_indep(moving, stmts[j], local_vars) for j in range(pos, src)):
            return None
        swaps.append(f"swap{{{side}}} {src + 1} {pos - src}.")
        stmts.insert(pos, stmts.pop(src))
    return swaps


def _ec_local_vars(exec_stmts: list[ec_ast.EcStmt]) -> set[str]:
    """The set of variables bound (written) anywhere in ``exec_stmts``.

    A token in a statement's data is a *variable read* only if it names a
    local bound here; operator names (``slice_*``/``concat_*``), module
    names and numeric constants are not.
    """
    return {
        s.var
        for s in exec_stmts
        if isinstance(s, (ec_ast.Assign, ec_ast.Sample, ec_ast.Call))
    }


def _ec_stmt_rw(
    stmt: ec_ast.EcStmt, local_vars: set[str]
) -> tuple[set[str], set[str], str | None]:
    """``(reads, writes, module)`` for ``stmt`` -- the data and glob footprint
    EC uses to decide whether two statements are independent.

    ``reads`` is restricted to ``local_vars`` (so pure operators and constants
    don't manufacture false dependencies). ``module`` is the called module for
    a ``Call`` (whose ``glob`` it touches), else ``None``."""
    reads = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", _stmt_text(stmt))) & local_vars
    writes: set[str] = set()
    module: str | None = None
    if isinstance(stmt, (ec_ast.Assign, ec_ast.Sample, ec_ast.Call)):
        writes = {stmt.var}
    if isinstance(stmt, ec_ast.Call):
        module = stmt.callee.split(".", 1)[0]
    return reads, writes, module


def _ec_indep(a: ec_ast.EcStmt, b: ec_ast.EcStmt, local_vars: set[str]) -> bool:
    """Whether ``a`` and ``b`` may be exchanged -- no read/write data conflict
    on a local, and not two calls sharing a module ``glob`` (EC rejects the
    latter)."""
    ra, wa, ma = _ec_stmt_rw(a, local_vars)
    rb, wb, mb = _ec_stmt_rw(b, local_vars)
    if wa & (rb | wb) or wb & ra:
        return False
    if ma is not None and ma == mb:
        return False
    return True


def _swaps_dep_valid(exec_stmts: list[ec_ast.EcStmt], swaps: list[str]) -> bool:
    """Whether every ``swap{1} pos delta`` in ``swaps`` moves a statement only
    across statements independent of it -- i.e. EC will accept the sequence.

    Simulates the moves on a copy of ``exec_stmts``. A coarse-signature bubble
    sort (:func:`_ec_perm_swaps`) can emit a swap that crosses a data
    dependency when duplicate signatures make it pick the wrong source; this
    catches that so the caller can retry with the full-signature sort."""
    cur = list(exec_stmts)
    local = _ec_local_vars(exec_stmts)
    for sw in swaps:
        m = re.match(r"swap\{1\}\s+(\d+)\s+(-?\d+)", sw)
        if m is None:
            return False
        pos = int(m.group(1)) - 1
        delta = int(m.group(2))
        new = pos + delta
        if not (0 <= pos < len(cur) and 0 <= new < len(cur)):
            return False
        moved = cur[pos]
        crossed = cur[new:pos] if delta < 0 else cur[pos + 1 : new + 1]
        if any(not _ec_indep(moved, c, local) for c in crossed):
            return False
        cur.insert(new, cur.pop(pos))
    return True


def _stmt_tokens(stmt: ec_ast.EcStmt) -> list[str]:
    """Identifier/number tokens in a statement's data content (sans callee)."""
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+", _stmt_text(stmt))


def _ec_call_callees(body: list[ec_ast.EcStmt]) -> list[str]:
    """The ordered callee list of the abstract calls in ``body``."""
    return [s.callee for s in _exec_stmts(body) if isinstance(s, ec_ast.Call)]


def _ec_reorder_swaps(
    before: list[ec_ast.EcStmt], after: list[ec_ast.EcStmt]
) -> list[str] | None:
    """``swap{1}`` tactics reordering ``before`` to *data-flow*-match ``after``.

    Unlike :func:`_ec_perm_swaps` (which matches statements by callee signature
    only), this is data-aware: it finds a permutation of ``before``'s exec
    statements whose data-flow graph is isomorphic to ``after``'s, so it also
    recovers a *relabel* of interchangeable same-callee call results that
    signature matching cannot see (e.g. two ``E.keygen()`` whose results feed
    swapped ``E.enc`` arguments). Two stateless same-distribution calls are
    exchangeable, so the reordered ``before`` couples to ``after`` under
    ``sim``. Returns side-``1`` ``swap{1} <pos> <delta>`` strings (no trailing
    period), ``[]`` when already aligned, or ``None`` when no data-flow
    isomorphism exists. Small straight-line bodies only (backtracking match).
    """
    b = _exec_stmts(before)
    a = _exec_stmts(after)
    n = len(a)
    if len(b) != n:
        return None
    _varying = (ec_ast.Assign, ec_ast.Sample, ec_ast.Call)
    aprod = {s.var: i for i, s in enumerate(a) if isinstance(s, _varying)}
    bprod = {s.var: i for i, s in enumerate(b) if isinstance(s, _varying)}
    perm = [-1] * n  # perm[i] = before-index matched to after-position i
    used = [False] * n

    def consistent(ai: int, bi: int) -> bool:
        if _ec_sig(a[ai]) != _ec_sig(b[bi]):
            return False
        ta, tb = _stmt_tokens(a[ai]), _stmt_tokens(b[bi])
        if len(ta) != len(tb):
            return False
        for x, y in zip(ta, tb):
            xa, yb = aprod.get(x), bprod.get(y)
            if (xa is None) != (yb is None):
                return False  # produced var vs literal/param mismatch
            if xa is None:
                if x != y:
                    return False  # literals/params must match exactly
            elif perm[xa] != yb:
                return False  # producers must already be matched to each other
        return True

    def backtrack(i: int) -> bool:
        if i == n:
            return True
        for bi in range(n):
            if used[bi] or not consistent(i, bi):
                continue
            perm[i], used[bi] = bi, True
            if backtrack(i + 1):
                return True
            perm[i], used[bi] = -1, False
        return False

    if not backtrack(0):
        return None
    swaps: list[str] = []
    cur = list(range(n))
    for target in range(n):
        src = cur.index(perm[target])
        if src == target:
            continue
        swaps.append(f"swap{{1}} {src + 1} {target - src}")
        cur.insert(target, cur.pop(src))
    return swaps


def _mask_idents(text: str) -> str:
    """Replace every identifier run in ``text`` with ``ID``, keeping all
    structural punctuation/operators/digits.

    Used to derive a *shape* of an assignment's RHS that is blind to which
    variables it references (so a consistent ``_rN`` renaming is invisible)
    but keeps the structure that distinguishes genuinely different
    assignments -- a tuple literal ``(ID, ID, ID)``, a projection ``ID.`1``
    vs ``ID.`2``, an operator application, etc."""
    return re.sub(r"[A-Za-z_][A-Za-z0-9_]*", "ID", text)


def _reorder_sig(stmt: ec_ast.EcStmt) -> tuple[str, ...]:
    """Rename-tolerant statement signature for *validating* a reorder: a sample
    by its distribution, a call by its callee, an assign by its rename-masked
    RHS *shape*, a return by kind. Unlike :func:`_ec_sig` it distinguishes
    samples of different distributions (so a mis-ordered ``<$`` of a distinct
    distribution is caught) and assignments of different RHS shape (so a
    reorder that leaves two distinct assigns -- e.g. ``ct2 <- _tup_2.`2`` and
    ``_tup_1 <- (..., ..., ...)`` -- mis-ordered is caught, where ``sim`` would
    otherwise be left open); unlike :func:`_stmt_full_sig` it masks
    bound-variable names and call arguments, so a consistent ``_rN`` renaming
    does not make a correct alignment look wrong (both sides mask to the same
    shape)."""
    if isinstance(stmt, ec_ast.Call):
        return ("call", stmt.callee)
    if isinstance(stmt, ec_ast.Sample):
        return ("sample", stmt.distr)
    if isinstance(stmt, ec_ast.Assign):
        return ("assign", _mask_idents(stmt.rhs))
    if isinstance(stmt, ec_ast.Return):
        return ("return",)
    return ("?",)


def _apply_swaps(
    exec_list: list[ec_ast.EcStmt], swaps: list[str]
) -> list[ec_ast.EcStmt] | None:
    """Apply a ``swap{1} <pos> <delta>`` sequence to ``exec_list`` (EC's move-by-
    delta semantics, the same model :func:`_ec_perm_swaps` emits), returning the
    reordered list or ``None`` on an out-of-range / unparsable swap."""
    cur = list(exec_list)
    for swap in swaps:
        match = re.fullmatch(r"swap\{1\} (\d+) (-?\d+)\.?", swap)
        if match is None:
            return None
        src = int(match.group(1)) - 1
        target = src + int(match.group(2))
        if not 0 <= src < len(cur) or not 0 <= target < len(cur):
            return None
        cur.insert(target, cur.pop(src))
    return cur


def _swaps_realign(
    swaps: list[str],
    left_exec: list[ec_ast.EcStmt],
    right_exec: list[ec_ast.EcStmt],
) -> bool:
    """True if applying ``swaps`` to ``left_exec`` reproduces ``right_exec`` up to
    :func:`_reorder_sig` (samples by distribution, calls by callee, rename-
    tolerant). A swap sequence that matches only a coarser signature (e.g. one
    that leaves two distinct-distribution samples mis-ordered) fails here, so the
    caller can fall back to a finer alignment instead of emitting a ``sim`` EC
    leaves open."""
    moved = _apply_swaps(left_exec, swaps)
    if moved is None or len(moved) != len(right_exec):
        return False
    return [_reorder_sig(s) for s in moved] == [_reorder_sig(s) for s in right_exec]


def _swaps_align_rendered(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    swaps: list[str],
    modules: mt.ModuleTranslator,
    left_state: frog_ast.Game | None,
    right_state: frog_ast.Game | None,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
) -> bool:
    """True if applying ``swaps`` to the *rendered* left flat-state body yields
    the rendered right body (modulo renaming).

    The raw-AST :func:`_permutation_swaps` is normalized differently from the
    rendered modules the micro lemma actually relates, so it can return a
    non-empty swap sequence that does **not** align the rendered bodies -- then
    ``sim`` is left with an open reorder (a 0-admit file EC rejects). Validate
    the raw swaps against the rendered bodies before trusting them; on failure
    the caller recomputes the permutation from the rendered states.
    """
    if left_state is None or right_state is None:
        return False
    left_mod = _flat_state_module(
        modules,
        "_swap_check_left",
        left_state,
        external_module_types,
        method_return_types,
        flat_params,
    )
    right_mod = _flat_state_module(
        modules,
        "_swap_check_right",
        right_state,
        external_module_types,
        method_return_types,
        flat_params,
    )
    if not left_mod.procs or not right_mod.procs:
        return False
    return _swaps_realign(
        swaps,
        _exec_stmts(left_mod.procs[0].body),
        _exec_stmts(right_mod.procs[0].body),
    )


def _rendered_state_swaps(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    modules: mt.ModuleTranslator,
    left_state: frog_ast.Game | None,
    right_state: frog_ast.Game | None,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
) -> list[str] | None:
    """``swap{1}`` tactics computed from the *rendered* flat-state EC modules.

    A per-transform micro lemma relates the two rendered flat-state modules
    (``Step_*_state_k`` / ``Step_*_state_{k+1}``), not ``app.game_before`` /
    ``app.game_after``. Those are not the same ASTs: the engine records a
    separately-canonicalized ``game_before`` for each application, and
    transforms like ``Inline Single-Use Variables`` leave a *nested* ``return``
    expression that only the EC hoister flattens (at render time). So an
    abstract-call-past-independent-sample reorder that EC sees between the two
    rendered modules is invisible to :func:`_permutation_swaps` run on the raw
    transform-application ASTs (length/normalization mismatch -> ``None``).

    This recomputes the permutation from the exact EC bodies the lemma
    relates. ``left_state`` is the lemma's left side (module argument 1), so
    the synthesized swaps always target side ``1`` -- no ``reversed_dir``
    handling is needed (the caller passes the states in lemma order). Returns
    the ``swap{1} <pos> <delta>`` strings (no trailing period, matching
    :func:`_ec_perm_swaps`) or ``None`` when the two bodies are not a
    permutation of each other (the caller then keeps the canned tactic).
    """
    if left_state is None or right_state is None:
        return None
    left_mod = _flat_state_module(
        modules,
        "_swap_probe_left",
        left_state,
        external_module_types,
        method_return_types,
        flat_params,
    )
    right_mod = _flat_state_module(
        modules,
        "_swap_probe_right",
        right_state,
        external_module_types,
        method_return_types,
        flat_params,
    )
    if not left_mod.procs or not right_mod.procs:
        return None
    left_body = left_mod.procs[0].body
    right_body = right_mod.procs[0].body
    left_exec = _exec_stmts(left_body)
    right_exec = _exec_stmts(right_body)
    # The coarse-signature bubble sort matches statements by kind/callee only,
    # so duplicate signatures (two ``x <- __determ_1__`` assigns, repeated
    # same-callee calls, or two ``<$`` samples of *different* distributions) can
    # make it (a) pick a source whose single move crosses a data dependency -- a
    # ``swap`` EC rejects -- or (b) leave two distinct samples mis-ordered while
    # still matching the coarse sequence (``sim`` then left open). Keep coarse
    # only when it is dependency-valid AND actually realigns the bodies up to
    # :func:`_reorder_sig`; otherwise retry with the full-signature sort, which
    # identifies each statement uniquely (so distinct samples are distinguished)
    # and (both bodies being topological orderings of one DAG) emits only
    # EC-acceptable swaps.
    coarse = _ec_perm_swaps(left_body, right_body)
    if (
        coarse is not None
        and _swaps_dep_valid(left_exec, coarse)
        and _swaps_realign(coarse, left_exec, right_exec)
    ):
        return coarse
    full = _ec_full_perm_swaps(left_body, right_body)
    if full is not None:
        stripped = [s.rstrip(".") for s in full]
        if _swaps_dep_valid(left_exec, stripped) and _swaps_realign(
            stripped, left_exec, right_exec
        ):
            return stripped
    return (
        coarse if coarse is not None and _swaps_dep_valid(left_exec, coarse) else None
    )


def _leg_sem_calls(body: list[ec_ast.EcStmt], module_name: str) -> str:
    """Bottom-up ``proc; wp; call <E>_<m>_sem; ...; auto`` tactic for a leg.

    Walks the executable statements in reverse: each abstract call becomes
    ``call <module>_<method>_sem``; a maximal run of deterministic statements
    before a call becomes one ``wp``. Closes the residual with ``auto``. This
    discharges ``state(E) ~ state(Ideal)`` (identical bodies, ``E`` vs ``Ideal``).
    """
    seq = ["proc"]
    need_wp = True
    for stmt in reversed(_exec_stmts(body)):
        if isinstance(stmt, ec_ast.Call):
            if need_wp:
                seq.append("wp")
                need_wp = False
            method = stmt.callee.split(".")[-1]
            seq.append(f"call {module_name}_{method}_sem")
        else:
            need_wp = True
    seq.append("auto")
    return "; ".join(seq)


def _synth_stateless_reorder(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    before_module: ec_ast.Module,
    after_module: ec_ast.Module,
    before_name: str,
    after_name: str,
    ideal_suffix: str,
    module_name: str,
    clone_alias: str,
    oracle: str,
    pre: str,
    post: str,
    reversed_dir: bool,
) -> _StatelessSynth | None:
    """Synthesize the transitivity-through-``Ideal`` proof for a reorder micro.

    Returns ``None`` when the diff is not a stateless-scheme reorder (e.g. not
    a permutation, or no abstract calls involved), so the caller falls back to
    the normal cache/admit path.
    """
    if not before_module.procs or not after_module.procs:
        return None
    before_body = before_module.procs[0].body
    after_body = after_module.procs[0].body
    if not any(isinstance(s, ec_ast.Call) for s in _exec_stmts(before_body)):
        return None
    m_body, did_inline = _ec_tuple_inline(before_body)
    # Data-aware reorder: recovers both a callee-order permutation *and* a
    # relabel of interchangeable same-callee call results (two ``E.keygen()``
    # feeding swapped ``E.enc`` args), which signature-only matching misses and
    # would leave ``sim`` facing an unprovable crossed-result post.
    swaps = _ec_reorder_swaps(m_body, after_body)
    if swaps is None:
        return None

    spec = f"({pre} ==> {post}) ({pre} ==> {post})"
    leg1 = _leg_sem_calls(before_body, module_name)
    leg3 = "symmetry; " + _leg_sem_calls(after_body, module_name)
    leg_b = "proc; " + "; ".join(swaps + ["sim"]) if swaps else "proc; sim"

    module_text: str | None = None
    m_name: str | None = None
    if did_inline:
        m_name = before_name + "b"
        leg_a = "proc; inline*; auto"
        body_lines = [
            f"transitivity {before_name}{ideal_suffix}.{oracle} {spec};",
            f"  [ smt() | smt() | {leg1} | ].",
            f"transitivity {m_name}{ideal_suffix}.{oracle} {spec};",
            f"  [ smt() | smt() | {leg_a} | ].",
            f"transitivity {after_name}{ideal_suffix}.{oracle} {spec};",
            f"  [ smt() | smt() | {leg_b} | {leg3} ].",
        ]
        proc0 = before_module.procs[0]
        m_proc = ec_ast.Proc(proc0.name, proc0.params, proc0.return_type, m_body)
        m_module = ec_ast.Module(
            name=m_name, procs=[m_proc], params=before_module.params
        )
        module_text = "\n".join(_render_module_decl(m_module))
    else:
        body_lines = [
            f"transitivity {before_name}{ideal_suffix}.{oracle} {spec};",
            f"  [ smt() | smt() | {leg1} | ].",
            f"transitivity {after_name}{ideal_suffix}.{oracle} {spec};",
            f"  [ smt() | smt() | {leg_b} | {leg3} ].",
        ]

    tactic = [_res_tag(SYNTH_PARAM)]
    if reversed_dir:
        tactic.append("symmetry.")
    tactic.extend(body_lines)
    return _StatelessSynth(
        module_text=module_text,
        module_name=m_name,
        tactic=tactic,
        request=(module_name, clone_alias),
    )


# ---------------------------------------------------------------------------
# Pure-local tuple-congruence synthesis
#
# ``Inline Local Tuple Literal`` (and its projection-vs-name siblings) over a
# *multi-module* scheme (``Key = [S.Key, T.Key]``) eliminates a local
# ``k <- (key1, key2)`` -- built from values already produced by abstract
# scheme calls -- and rewrites ``k.`1``/``k.`2`` (fed into abstract ``S.enc`` /
# ``T.enc``) to the components. The single-declared-module ``Ideal`` route
# (``_synth_stateless_reorder``) does not cover this (two declared modules), and
# ``proc; sim`` leaves it open (``sim``'s syntactic arg-match cannot bridge
# ``k.`1`` vs ``key1``), while two-sided ``call (_: ={glob M})`` on an abstract
# module is rejected (``module T can write T``).
#
# The working close turns each projection arg-equality into an
# smt-dischargeable side goal via a generic per-method congruence lemma
# (``<M>_<m>_eq : equiv[ M.m ~ M.m : ={glob M, arg} ==> ={glob M, res} ]``,
# proved by ``proc true; auto``). The micro tactic reorders the inlined side's
# calls to the tuple side's order (``swap``), peels every abstract call from the
# back with its congruence lemma (``call <M>_<m>_eq``, reverse program order),
# absorbs the deterministic tuple assignment (``wp``), and discharges the
# residual projection equalities (``skip => /#``). Every quantity is computed
# from the rendered EC bodies, so this is ``synth-param``. Validated end-to-end
# on ``GeneralDoubleSymEnc_INDOT$`` hop_0 (EC EXIT 0, admit-free).
#
# Scope: the PURE-LOCAL shape only -- the tuple is built from already-coupled
# values and is not separated from its use by an abstract call whose *result*
# round-trips through it. The KEMPRF-style entangled residue
# (``rsp<-(ss0,ctxt); ss<-rsp.1`` with ``K.encaps`` between construction and
# use) is detected out of scope here (a non-call executable statement survives,
# or the call sequences are not a permutation) -- it is closed instead by the
# entangled-tuple call-walker (``_synth_tuple_walk``, the next route tried).
# ---------------------------------------------------------------------------


@dataclass
class _CongruenceSynth:
    """Synthesized pure-local tuple-congruence proof for one micro."""

    tactic: list[str]
    methods: set[tuple[str, str]]  # (declared module var, method name)


def _callee_parts(callee: str) -> tuple[str, str] | None:
    """Split an EC callee ``M.m`` into ``(M, m)``; ``None`` if not dotted."""
    parts = callee.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def _congr_lemma_name(mod: str, meth: str) -> str:
    return f"{mod}_{meth}_eq"


def congruence_lemma_block(mod: str, meth: str) -> str:
    """Render the ``<M>_<m>_eq`` per-method congruence lemma as EC source.

    ``equiv[ M.m ~ M.m : ={glob M, arg} ==> ={glob M, res} ]`` proved by
    ``proc true; auto`` -- valid for any arity (``arg`` is unit for a no-param
    procedure). Emitted once per distinct ``(M, m)`` in section scope, before
    the per-transform chain that ``call``s it.
    """
    name = _congr_lemma_name(mod, meth)
    return "\n".join(
        [
            f"lemma {name} :",
            f"  equiv [ {mod}.{meth} ~ {mod}.{meth} :",
            f"          ={{glob {mod}, arg}} ==> ={{glob {mod}, res}} ].",
            "proof. proc true; auto. qed.",
        ]
    )


def _synth_tuple_congruence(  # pylint: disable=too-many-return-statements,too-many-locals
    tuple_module: ec_ast.Module,
    other_module: ec_ast.Module,
    declared_names: set[str],
    reversed_dir: bool,
) -> _CongruenceSynth | None:
    """Synthesize a per-method congruence proof for a pure-local tuple micro.

    ``tuple_module`` is the rendered ``state_k`` side (it physically builds the
    local tuple and projects it); ``other_module`` is the rendered
    ``state_{k+1}`` side (the tuple inlined, abstract calls possibly reordered).
    ``reversed_dir`` follows the chain-emitter convention: the lemma's left side
    is the tuple side when forward and the inlined side when reversed.

    Returns ``None`` (caller falls through to cache/admit) when the diff is not
    the pure-local-tuple shape: no inlinable tuple, a non-call executable
    statement survives after inlining (sample / residual assign / round-tripped
    result), a callee is not a dotted call to a declared module, or the two call
    sequences are not a permutation of each other.
    """
    if not tuple_module.procs or not other_module.procs:
        return None
    tuple_body = tuple_module.procs[0].body
    other_body = other_module.procs[0].body
    inlined, did_inline = _ec_tuple_inline(tuple_body)
    if not did_inline:
        return None

    def _calls_only(body: list[ec_ast.EcStmt]) -> list[ec_ast.Call] | None:
        out: list[ec_ast.Call] = []
        for stmt in _exec_stmts(body):
            if isinstance(stmt, ec_ast.Return):
                continue
            if not isinstance(stmt, ec_ast.Call):
                return None
            out.append(stmt)
        return out

    inlined_calls = _calls_only(inlined)
    other_calls = _calls_only(other_body)
    if not inlined_calls or other_calls is None:
        return None
    methods: set[tuple[str, str]] = set()
    for call in inlined_calls:
        parts = _callee_parts(call.callee)
        if parts is None or parts[0] not in declared_names:
            return None
        methods.add(parts)
    for call in other_calls:
        if _callee_parts(call.callee) is None:
            return None
    # Reorder the OTHER (inlined) side's calls to match the tuple side's order.
    swaps = _ec_perm_swaps(other_body, inlined)
    if swaps is None:
        return None
    other_side = 1 if reversed_dir else 2
    body: list[str] = ["proc."]
    for sw in swaps:
        body.append(sw.replace("{1}", "{" + str(other_side) + "}") + ".")
    # Reverse-walk the tuple side's physical statements: peel each abstract call
    # with its congruence lemma; flush one ``wp`` per run of deterministic
    # assignments (the tuple literal + any copies).
    walk = [s for s in tuple_body if not isinstance(s, (ec_ast.VarDecl, ec_ast.Return))]
    pending_wp = False
    for stmt in reversed(walk):
        if isinstance(stmt, ec_ast.Call):
            if pending_wp:
                body.append("wp.")
                pending_wp = False
            parts = _callee_parts(stmt.callee)
            if parts is None:
                return None
            body.append(f"call {_congr_lemma_name(*parts)}.")
        elif isinstance(stmt, ec_ast.Assign):
            pending_wp = True
        else:
            return None
    if pending_wp:
        body.append("wp.")
    body.append("skip => /#.")
    return _CongruenceSynth(tactic=[_res_tag(SYNTH_PARAM), *body], methods=methods)


# ---------------------------------------------------------------------------
# Entangled-tuple call-walker synthesis
#
# The pure-local tuple-congruence route above declines the KEMPRF-style
# entangled residue: the tuple round-trips an abstract-call *result*
# (``encaps_result <- (_r0, c0); ct <- encaps_result.`2`` with ``F.evaluate``
# producing ``_r0``), so a non-call statement (the projection copy ``ct <- c0``)
# survives inlining and ``_calls_only`` returns ``None``. But here the tuple's
# projections feed only deterministic assignments and the return -- never an
# abstract-call argument -- so after inlining the tuple side the abstract-call
# subsequence (callee + rendered args) is IDENTICAL to the other side, and the
# only diffs are deterministic glue (the dissolved tuple plus a copy that may be
# hoisted across a call boundary). ``proc; sim`` does NOT close it (``sim``
# cannot infer the equalities once a copy is hoisted across a call boundary).
# The close is the ISUV-style call-walker: ``proc.`` then, bottom-up, ``wp``
# (absorbs each side's -- possibly asymmetric -- trailing deterministic block,
# including the dissolved tuple) and ``call (_: true)`` to peel each abstract
# call, finishing with ``skip => /#`` (smt discharges the surviving tuple
# projections, which ``=> />`` cannot). Distinct from the congruence case, where
# a projection feeds a call arg (``k.`1`` vs ``key1``) and the calls do not align
# 1:1. Validated on KEMPRF_Correctness (4 tuple micros across hop_0/hop_2,
# EC EXIT 0).
# ---------------------------------------------------------------------------


def _stmt_full_sig(stmt: ec_ast.EcStmt) -> tuple[str, str | None, str | None, str]:
    """Full structural signature (kind, lhs var, callee, data) of a statement.

    Unlike :func:`_stmt_text` (data content only) this distinguishes a Call from
    a same-rhs Assign and a renamed call result, so identical-prefix matching is
    exact.
    """
    return (
        type(stmt).__name__,
        getattr(stmt, "var", None),
        getattr(stmt, "callee", None),
        _stmt_text(stmt),
    )


def _calls_only_target(
    other_body: list[ec_ast.EcStmt], inlined_body: list[ec_ast.EcStmt]
) -> list[ec_ast.EcStmt] | None:
    """``other_body``'s executable statements with its *calls* reordered to
    ``inlined_body``'s callee order (assignments kept in place).

    Same-callee calls keep their relative order. Returns ``None`` when the
    callees do not match up.
    """
    o_exec = _exec_stmts(other_body)
    i_calls = [s for s in _exec_stmts(inlined_body) if isinstance(s, ec_ast.Call)]
    o_calls = [s for s in o_exec if isinstance(s, ec_ast.Call)]
    if len(o_calls) != len(i_calls):
        return None
    used = [False] * len(o_calls)
    target_calls: list[ec_ast.Call] = []
    for ic in i_calls:
        match = next(
            (
                j
                for j, oc in enumerate(o_calls)
                if not used[j] and oc.callee == ic.callee
            ),
            None,
        )
        if match is None:
            return None
        used[match] = True
        target_calls.append(o_calls[match])
    target_exec: list[ec_ast.EcStmt] = []
    ti = 0
    for stmt in o_exec:
        if isinstance(stmt, ec_ast.Call):
            target_exec.append(target_calls[ti])
            ti += 1
        else:
            target_exec.append(stmt)
    return target_exec


def _calls_only_alignment_invalid(
    before_body: list[ec_ast.EcStmt], after_body: list[ec_ast.EcStmt]
) -> bool:
    """True if aligning ``before_body``'s calls to ``after_body``'s order (with
    assignments kept fixed) is a use-before-def -- the data-invalid reorder EC
    rejects ("statements not independent"). Happens when a reordered call is
    pushed past an assignment that reads its result; the signature-only
    ``_ec_perm_swaps`` does not catch it, so the swap routes mis-fire and the
    deterministic functional-twin route must take over.

    Tuple literals are inlined first (``_ec_tuple_inline``): a tuple round-tripping
    an abstract-call result (the KEMPRF shape) makes the *raw* alignment look
    invalid, but the tuple-walk dissolves the tuple and that reorder is a valid
    swap -- so it must stay on the byte-identical swap path, not preempted here.
    """
    before_body, _ = _ec_tuple_inline(before_body)
    after_body, _ = _ec_tuple_inline(after_body)
    target = _calls_only_target(before_body, after_body)
    if target is None:
        return False
    def_index: dict[str, int] = {}
    for i, stmt in enumerate(target):
        var = getattr(stmt, "var", None)
        if var is not None and var not in def_index:
            def_index[var] = i
    for i, stmt in enumerate(target):
        own = getattr(stmt, "var", None)
        for tok in _stmt_tokens(stmt):
            if tok == own:
                continue
            origin = def_index.get(tok)
            if origin is not None and origin > i:
                return True
    return False


def _same_callee_arg_crossing(
    a_body: list[ec_ast.EcStmt], b_body: list[ec_ast.EcStmt]
) -> bool:
    """True when the two bodies call one callee with the same ARGUMENTS in a
    DIFFERENT order -- a reordering :func:`_calls_only_align_swaps` cannot see.

    That routine aligns calls by CALLEE and, by its own documentation, "leaves
    interchangeable same-callee results for the walker". Two calls to the same
    callee are only interchangeable when their arguments agree. When they do
    not, the alignment pairs the wrong ones and the peel that follows emits an
    equiv obligation relating unrelated results.

    Measured on ``CG_expanded_LEAK_BIND_K_PK`` ``micro_2_challenge_left_39``, a
    ``Stabilize Independent Statements`` leg: the left body runs
    ``NG.exp(v7, field9)`` then ``NG.exp(v10, field10)`` and the right runs them
    the other way round (``v7 <- ct0.`2``, ``v10 <- ct1.`2``). ``L.get`` also
    moves, and the emitted ``swap{2} 9 -5`` realigns THAT, which is why the leg
    looks aligned. Reading the residual goal shows what the closer is handed:
    ``(v7_L, field9{1}).`1 = (v10{2}, field10{2}).`1``, i.e. the oracle's two
    input ciphertexts must be equal, against a precondition offering only
    ``={ct0, ct1}``. The lemma is true; the SUBGOAL the strategy manufactured
    is false, so no closer, larger budget or smarter solver could discharge it.

    Declining is the only honest answer, not merely the safe one: EC's ``swap``
    refuses to reorder two abstract-module calls, so the crossing cannot be
    repaired by adding swaps either. The oracle takes its admit.

    The trigger is deliberately narrow -- same callee, same argument MULTISET,
    different SEQUENCE -- so a leg whose two sides merely rename their locals
    has mismatched multisets and is untouched.
    """
    a_calls = [
        (st.callee, st.args)
        for st in _exec_stmts(a_body)
        if isinstance(st, ec_ast.Call)
    ]
    b_calls = [
        (st.callee, st.args)
        for st in _exec_stmts(b_body)
        if isinstance(st, ec_ast.Call)
    ]
    for callee in {c for c, _ in a_calls}:
        left = [args for c, args in a_calls if c == callee]
        right = [args for c, args in b_calls if c == callee]
        if len(left) > 1 and left != right and sorted(left) == sorted(right):
            return True
    return False


def _calls_only_align_swaps(
    other_body: list[ec_ast.EcStmt],
    inlined_body: list[ec_ast.EcStmt],
) -> list[str] | None:
    """``swap{1}`` strings reordering ``other_body``'s *calls* to ``inlined_body``'s
    call order.

    Returns ``[]`` when the call orders already agree, the swap list when
    ``other_body``'s calls are a callee-permutation of ``inlined_body``'s, or
    ``None`` when the callees do not match up. Only calls are permuted (assigns
    stay put, absorbed by the walker's ``wp``); same-callee calls keep their
    relative order, so an independent different-module reorder the inline exposed
    (e.g. ``K.decaps`` past ``F.evaluate``) is recovered while interchangeable
    same-callee results are left for the walker.

    The coarse-signature bubble sort (:func:`_ec_perm_swaps`) over the *whole*
    exec list can slide a call past an independent assignment and then bubble
    that assignment back across the call's result write -- a dependency-crossing
    ``swap`` EC rejects ("the two statements are not independent"). So the coarse
    swaps are dependency-validated (:func:`_swaps_dep_valid`); on failure they are
    recomputed by moving only the calls (:func:`_calls_only_move_swaps`), leaving
    every assignment in place. A clean proof's swaps are already valid, so it
    keeps the coarse result byte-identical.

    A same-callee argument crossing (:func:`_same_callee_arg_crossing`) is
    DECLINED outright: the alignment is blind to it, and every route built on
    top of this one would peel the wrong pairing into a false obligation.
    """
    if _same_callee_arg_crossing(other_body, inlined_body):
        return None
    target_exec = _calls_only_target(other_body, inlined_body)
    if target_exec is None:
        return None
    o_exec = _exec_stmts(other_body)
    swaps = _ec_perm_swaps(o_exec, target_exec)
    if swaps is not None and _swaps_dep_valid(o_exec, swaps):
        return swaps
    return _calls_only_move_swaps(o_exec, inlined_body)


def _calls_only_move_swaps(
    o_exec: list[ec_ast.EcStmt],
    inlined_body: list[ec_ast.EcStmt],
) -> list[str] | None:
    """``swap{1}`` strings aligning ``o_exec``'s calls to ``inlined_body``'s call
    order by moving *only* the calls.

    Each call is slid left to its target slot across the intervening statements,
    leaving assignments where they are (the walker's ``wp`` absorbs them). Because
    slots fill left to right, a call only ever moves left, and every move is
    dependency-validated (:func:`_ec_indep`). Returns ``None`` if a call cannot
    reach its slot without crossing a statement it depends on -- the caller then
    declines, falling to the deterministic functional-twin route.
    """
    i_calls = [s for s in _exec_stmts(inlined_body) if isinstance(s, ec_ast.Call)]
    o_calls = [s for s in o_exec if isinstance(s, ec_ast.Call)]
    if len(o_calls) != len(i_calls):
        return None
    used = [False] * len(o_calls)
    order: list[ec_ast.Call] = []
    for ic in i_calls:
        match = next(
            (
                j
                for j, oc in enumerate(o_calls)
                if not used[j] and oc.callee == ic.callee
            ),
            None,
        )
        if match is None:
            return None
        used[match] = True
        order.append(o_calls[match])
    cur: list[ec_ast.EcStmt] = list(o_exec)
    local = _ec_local_vars(cur)
    swaps: list[str] = []
    for i, want in enumerate(order):
        positions = [j for j, s in enumerate(cur) if isinstance(s, ec_ast.Call)]
        src = next(j for j in positions if cur[j] is want)
        dst = positions[i]
        if src == dst:
            continue
        crossed = cur[dst:src]
        if any(not _ec_indep(want, c, local) for c in crossed):
            return None
        swaps.append(f"swap{{1}} {src + 1} {dst - src}")
        cur.insert(dst, cur.pop(src))
    return swaps


def _synth_tuple_walk(
    tuple_module: ec_ast.Module,
    other_module: ec_ast.Module,
    other_side: int,
) -> list[str] | None:
    """Call-walker close for an entangled ``Inline Local Tuple Literal`` micro.

    Inlines ``tuple_module``'s local tuple, aligns ``other_module``'s calls to
    that call order with ``swap{other_side}`` (an independent different-module
    reorder the inline exposed, e.g. ``K.decaps`` past ``F.evaluate``; ``[]`` when
    already aligned), then peels the ``n`` now-aligned calls bottom-up (``wp``
    then ``call (_: true)`` each) and finishes ``skip => /#`` (smt discharges the
    surviving tuple projections, which ``=> />`` cannot). Returns ``None`` (caller
    falls through) when there is no inlinable tuple or the calls are not a
    callee-permutation. Validated on KEMPRF_Correctness (6 tuple micros across
    hop_0/hop_2, including the two ``K.decaps``/``F.evaluate`` reorders, EC EXIT 0).
    """
    if not tuple_module.procs or not other_module.procs:
        return None
    inlined, did_inline = _ec_tuple_inline(tuple_module.procs[0].body)
    if not did_inline:
        return None
    n_calls = len([s for s in _exec_stmts(inlined) if isinstance(s, ec_ast.Call)])
    if n_calls == 0:
        return None
    swaps = _calls_only_align_swaps(other_module.procs[0].body, inlined)
    if swaps is None:
        return None
    body = [_res_tag(SYNTH_PARAM), "proc."]
    for sw in swaps:
        body.append(sw.replace("{1}", "{" + str(other_side) + "}") + ".")
    body.extend(_backbone_peel(inlined))
    body.append("skip => /#.")
    return body


def _synth_isuv_walk(
    left_module: ec_ast.Module,
    right_module: ec_ast.Module,
) -> list[str] | None:
    """Swap-aligned call-walker for an ``Inline Single-Use Variables`` micro
    whose inlining also exposed an independent (different-module) call reorder.

    ``Inline Single-Use Variables`` removes deterministic single-use assignments,
    so the before/after bodies differ in statement *count* -- the whole-statement
    permutation check (:func:`_ec_perm_swaps`, via ``_permutation_swaps`` /
    ``_rendered_state_swaps``) rejects them as non-permutations and the canned
    ``proc; sp; wp; sim`` runs but silently leaves ``={res}`` open whenever the
    inlining also let two independent calls of *different* declared modules swap
    (e.g. ``K_PQ.encodesharedsecret`` past ``K_T.decaps``): ``sim`` can't align
    the calls at mismatched positions. Align ``right_module``'s *calls* (only --
    the count-differing deterministic assignments stay for the walker's ``wp``)
    to ``left_module``'s call order with ``swap{2}``, then peel the ``n`` now-
    aligned calls bottom-up (``wp`` then ``call (_: true)`` each) and finish
    ``skip => /#`` (smt discharges the surviving projections the inlining left in
    the call args; ``=> />`` is too weak). Returns ``None`` (caller keeps the
    canned tactic) when the calls are not a callee-permutation or are already
    aligned (no reorder -> the canned ``sim`` route handles it). Validated on
    CK_expanded_Correctness micro_0_left_2 (EC EXIT 0).
    """
    if not left_module.procs or not right_module.procs:
        return None
    l_body = left_module.procs[0].body
    r_body = right_module.procs[0].body
    n_calls = len([s for s in _exec_stmts(l_body) if isinstance(s, ec_ast.Call)])
    if n_calls == 0:
        return None
    swaps = _calls_only_align_swaps(r_body, l_body)
    # No reorder (``swaps == []``) means the calls already line up, so the canned
    # ``sim`` route closes it -- only fire when an actual alignment is needed.
    if not swaps:
        return None
    body = [_res_tag(SYNTH_PARAM), "proc."]
    for sw in swaps:
        body.append(sw.replace("{1}", "{2}") + ".")
    body.extend(_backbone_peel(l_body))
    body.append("skip => /#.")
    return body


# ---------------------------------------------------------------------------
# Deterministic same-module-reorder synthesis (functional-module transitivity)
#
# ``Inline Single-Use Variables`` (and other reorder passes) can sink a
# *deterministic* abstract call past other calls of the *same* declared module
# (e.g. ``KEM_T.decaps`` past ``KEM_T.encodeciphertext``). EC rejects ``swap``
# on two same-module calls (shared ``glob``), so the ``_synth_isuv_walk``
# swap-aligned route emits an EC-rejected ``swap{2}``. The reorder is sound only
# because the methods are *deterministic* -- so we functionalize every det call
# to its ``ev_<m>`` form via the ``<M>_<m>_det`` axioms (always emitted for
# declared modules' deterministic methods), after which the reorder is trivial.
#
# We route ``left ~ right`` through two ``ev``-functionalized twin modules
# ``F_left`` / ``F_right`` (the state bodies with det calls replaced by ``x <-
# <clone>.ev_<m> a`` assignments, probabilistic calls kept) via transitivity:
#
#   left      ~ F_left   (* leg1: top-down ``seq 1 1`` peel, program order      *)
#   F_left    ~ F_right  (* leg_mid: pure-det reorder -- wp + call (_: true)     *)
#   F_right   ~ right     (* leg3: top-down ``seq 1 1`` peel                      *)
#
# The legs MUST run top-down (``seq 1 1`` per statement, uniform ``={vars}``
# couplings since F mirrors the state's structure) so a det call's args are
# functionalized *before* a later statement inlines its result -- bottom-up
# ``exists*`` peeling would freeze the inlined intermediate (an ISUV-inlined
# ``H.evaluate(concat(_r1, ...))`` arg) before ``_r1`` is pinned to its ``ev``
# value, breaking the close. Verified end-to-end on ``CK_expanded_Correctness``
# ``micro_0_right_2_fwd`` (EC EXIT 0).
# ---------------------------------------------------------------------------


@dataclass
class _DetReorderSynth:
    """Synthesized deterministic-reorder proof + the F-twin modules to emit."""

    module_texts: list[str]
    module_names: list[str]
    tactic: list[str]


def _det_app(clone_alias: str, method: str, args: str) -> str:
    """Functional form ``<clone>.ev_<m> (a0) (a1) ...`` of a det call."""
    app = f"{clone_alias}.ev_{method}"
    for arg in _split_top_args(args):
        app += f" ({arg})"
    return app


def _ec_functionalize(
    body: list[ec_ast.EcStmt],
    det_pred: Callable[[str, str], bool],
    clone_of: Callable[[str], str | None],
) -> list[ec_ast.EcStmt]:
    """Replace each deterministic abstract call with its ``ev_<m>`` assignment.

    ``x <@ M.m(a)`` with ``m`` deterministic becomes ``x <- <clone of M>.ev_m
    (a)``; probabilistic calls and every other statement (incl. ``VarDecl``)
    are kept verbatim.
    """
    out: list[ec_ast.EcStmt] = []
    for stmt in body:
        if isinstance(stmt, ec_ast.Call):
            parts = _callee_parts(stmt.callee)
            alias = clone_of(parts[0]) if parts is not None else None
            if parts is not None and alias is not None and det_pred(parts[0], parts[1]):
                out.append(
                    ec_ast.Assign(stmt.var, _det_app(alias, parts[1], stmt.args))
                )
                continue
        out.append(stmt)
    return out


def _det_topdown_leg(
    call_body: list[ec_ast.EcStmt],
    call_side: int,
    glob_items: list[str],
    det_pred: Callable[[str, str], bool],
    ctr: list[int],
    proc_params: list[str] | None = None,
) -> list[str]:
    """Top-down ``seq 1 1`` peel functionalizing the call-side's det calls.

    ``call_body`` is the *state* body (with abstract calls); the other side is
    its ``ev_*``-functionalized twin (assignments threaded by ``wp``). Each
    statement is split off with ``seq 1 1 : (={<globs>, <params>, <vars so far>})``
    and proved: a det call peeled one-sided (``exists*`` + ``call{side} (M_m_det
    ...)``), a probabilistic call coupled (``call (_: true)``), an assignment by
    ``auto``. Program order keeps a det call's args already-functionalized.

    The procedure parameters (``proc_params``) seed the coupling: they are equal
    by the lemma precondition, and a det call consuming a parameter (e.g.
    ``K.decaps(sk, ct)``) needs ``={sk}`` to discharge its determinism axiom's
    result equality (``ev_decaps sk{1} ct = ev_decaps sk{2} ct``). Omitting them
    leaves an undischarged ``forall &1 &2`` goal the next ``seq`` cannot apply to.
    """
    tac: list[str] = ["proc."]
    coupled = list(proc_params or []) + list(glob_items)
    for stmt in _exec_stmts(call_body):
        if isinstance(stmt, ec_ast.Return):
            break
        var = getattr(stmt, "var", None)
        if var:
            coupled.append(var)
        tac.append("seq 1 1 : (={" + ", ".join(coupled) + "}).")
        if isinstance(stmt, ec_ast.Call):
            parts = _callee_parts(stmt.callee)
            if parts is not None and det_pred(parts[0], parts[1]):
                mod, meth = parts
                args = _split_top_args(stmt.args)
                names = " ".join(
                    [f"g{ctr[0]}"] + [f"a{ctr[0]}_{k}" for k in range(len(args))]
                )
                cap = ", ".join(
                    [f"(glob {mod}){{{call_side}}}"]
                    + [f"({a}){{{call_side}}}" for a in args]
                )
                tac.append("wp.")
                tac.append(f"exists* {cap}; elim* => {names}.")
                tac.append(f"call{{{call_side}}} ({mod}_{meth}_det {names}).")
                tac.append("auto.")
                ctr[0] += 1
            else:
                tac.append("call (_: true); auto.")
        else:
            tac.append("auto.")
    tac.append("skip => /#.")
    return tac


def _init_topdown_leg(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    state_body: list[ec_ast.EcStmt],
    call_side: int,
    glob_items: list[str],
    det_pred: Callable[[str, str], bool],
    ctr: list[int],
    left_mod: str,
    right_mod: str,
    field_names: set[str],
    closer: str = "skip => /#.",
) -> list[str]:
    """Field-aware top-down ``seq 1 1`` peel functionalizing ``call_side``'s det
    calls -- the init variant of :func:`_det_topdown_leg`.

    ``closer`` is the final tactic (default ``skip => /#``). The plain-reorder
    route overrides it: its leg post carries the returned pk TUPLE whose
    component equalities are all in the invariant, but the plain ``/#`` smt does
    not scale to the deep pair-nesting -- ``skip => /> /#`` (progressive simplify
    then smt) closes it.

    An init flat state packs its NG-derived results into *module fields* mid-body
    (``ek0 <- _tup.`1`` interspersed between keygen blocks), and a module field
    cannot appear bare in an ``={...}`` coupling (``unknown variable ek0``). So a
    statement whose ``var`` is a field is coupled as an explicit qualified
    equality ``<left>.<f>{1} = <right>.<f>{2}`` while locals stay in the bare
    ``={...}`` set. ``left_mod``/``right_mod`` are the side-1/side-2 module names;
    ``field_names`` is the flat state's field set. Otherwise identical to
    :func:`_det_topdown_leg` (det call peeled one-sided, prob call coupled,
    assignment by ``auto``), closing ``skip => /#``."""
    tac: list[str] = ["proc."]
    locs: list[str] = list(glob_items)
    field_eqs: list[str] = []
    # The module whose procedure runs on ``call_side`` -- its fields must be
    # qualified when referenced in ``exists*`` captures (a bare field name is
    # ``unknown variable``).
    call_mod = left_mod if call_side == 1 else right_mod

    def _q(a: str) -> str:
        return f"{call_mod}.{a}" if a in field_names else a

    def _inv() -> str:
        parts = (["={" + ", ".join(locs) + "}"] if locs else []) + field_eqs
        return " /\\ ".join(parts)

    for stmt in _exec_stmts(state_body):
        if isinstance(stmt, ec_ast.Return):
            break
        var = getattr(stmt, "var", None)
        if var:
            if var in field_names:
                field_eqs.append(f"{left_mod}.{var}{{1}} = {right_mod}.{var}{{2}}")
            else:
                locs.append(var)
        tac.append(f"seq 1 1 : ({_inv()}).")
        if isinstance(stmt, ec_ast.Call):
            parts = _callee_parts(stmt.callee)
            if parts is not None and det_pred(parts[0], parts[1]):
                mod, meth = parts
                args = _split_top_args(stmt.args)
                names = " ".join(
                    [f"g{ctr[0]}"] + [f"a{ctr[0]}_{k}" for k in range(len(args))]
                )
                cap = ", ".join(
                    [f"(glob {mod}){{{call_side}}}"]
                    + [f"({_q(a)}){{{call_side}}}" for a in args]
                )
                tac.append("wp.")
                tac.append(f"exists* {cap}; elim* => {names}.")
                tac.append(f"call{{{call_side}}} ({mod}_{meth}_det {names}).")
                tac.append("auto.")
                ctr[0] += 1
            else:
                tac.append("call (_: true); auto.")
        else:
            tac.append("auto.")
    tac.append(closer)
    return tac


def _call_sample_backbone(
    body: list[ec_ast.EcStmt],
) -> list[tuple[str, str | None]]:
    """Ordered backbone of the ``wp``-opaque statements: each abstract call (by
    callee) and each ``<$`` sample, in program order.

    ``wp`` can absorb deterministic assignments but neither a ``call`` nor a
    ``rnd`` sample, so the middle-leg peel must couple these explicitly. The
    backbone is what two functionalized twins must share (same calls and samples,
    same interleaving) for the identical-order ``(wp; couple)*`` peel to apply.

    A sample is tagged by its *bound variable*, not a bare ``"sample"`` marker:
    two twins whose samples were *reordered* (e.g. ``Topological Sorting`` swaps
    ``seed_T0 <$ d; seed_E9 <$ d``) then have differing backbones, so the peel
    declines (identity ``rnd`` would couple the wrong seeds) and the caller falls
    to the ``swap``+``sim`` branch, which reorders the glob-independent samples
    into position. Same-order samples (dedup/plumbing) keep matching names and
    stay on the peel.
    """
    out: list[tuple[str, str | None]] = []
    for stmt in _exec_stmts(body):
        if isinstance(stmt, ec_ast.Call):
            out.append(("call", stmt.callee))
        elif isinstance(stmt, ec_ast.Sample):
            out.append(("sample", getattr(stmt, "var", None)))
    return out


def _coupling_has_field_rename(pre_text: str, base1: str, base2: str) -> bool:
    """True if some cross-side conjunct pairs two DIFFERENTLY-named fields.

    A coupling that renames a field (``<L>.f10{1} = <R>.f11{2}``) does not
    relate the field each side's body actually reads under its own name, so a
    route whose closer relies on the coupling reading through by name cannot
    close. Only cross-side (``{1} = {2}``) conjuncts count; a same-side
    equation is a survivor/cache invariant, not a rename.
    """
    return any(
        f != g
        for mb1, f, mb2, g in _FIELD_PAIR_RE.findall(pre_text)
        if mb1 == base1 and mb2 == base2
    )


def _uses_bitstring_algebra(body: list[ec_ast.EcStmt]) -> bool:
    """True if any statement applies an emitted bitstring ``concat``/``slice`` op.

    These are ``op [smt_opaque]`` declarations, so a goal that has to equate two
    nested applications of them is discharged by congruence alone -- which the
    solver reliably fails to find once the surrounding post is large. Routes
    whose closer is a single whole-post ``smt`` use this to decline rather than
    emit a tactic that runs and leaves the goal open.
    """
    # pylint: disable=protected-access
    for stmt in _exec_stmts(body):
        try:
            text = ec_ast._render_stmt(stmt)
        except TypeError:
            return True
        if "concat_" in text or "slice_" in text:
            return True
    return False


def _peelable_tail_backbone(
    body: list[ec_ast.EcStmt],
) -> list[tuple[str, str | None]] | None:
    """The call/sample backbone, but ONLY when it forms an unbroken tail.

    A peel that emits consecutive ``call``/``rnd`` steps with no ``wp`` between
    them consumes one instruction per step from the end of the program, so it
    is applicable exactly when every executable statement from the first
    abstract call or sample onward is itself a call or a sample. Deterministic
    statements are fine BEFORE that point (the trailing ``auto`` clears them);
    one sitting between two calls is not, and EasyCrypt rejects the next
    ``call`` with "invalid last instruction". A ``return`` is transparent here:
    EasyCrypt treats it as part of the procedure, not as an instruction, so a
    body ending ``_r9 <@ H.evaluate(...); return _r9;`` still has a call as its
    last instruction. Returns ``None`` for a broken tail so the caller can
    decline instead of emitting a tactic that cannot close.
    """
    stmts = [s for s in _exec_stmts(body) if not isinstance(s, ec_ast.Return)]
    first = next(
        (i for i, s in enumerate(stmts) if isinstance(s, (ec_ast.Call, ec_ast.Sample))),
        None,
    )
    if first is None:
        return []
    out: list[tuple[str, str | None]] = []
    for stmt in stmts[first:]:
        if isinstance(stmt, ec_ast.Call):
            out.append(("call", stmt.callee))
        elif isinstance(stmt, ec_ast.Sample):
            out.append(("sample", getattr(stmt, "var", None)))
        else:
            return None
    return out


def _strip_decls(body: list[ec_ast.EcStmt]) -> list[ec_ast.EcStmt]:
    """``body`` with its ``var`` declarations removed -- the executable core.

    Two constant-return oracle bodies that differ only in unused local
    declarations (a dead-decl cleanup step) have equal stripped cores, which is
    what makes ``proc; sim`` sound for them; an added/removed *statement* does
    not, so it must not be mistaken for a cleanup.
    """
    return [s for s in body if not isinstance(s, ec_ast.VarDecl)]


def _all_calls_dead(body: list[ec_ast.EcStmt]) -> bool:
    """True if every abstract-call result in ``body`` is unused -- no other
    statement's rendered operand nor the ``return`` references it.

    This is the ``Absorb Redundant Early Return`` dead-decapsulation shape: a
    constant-return oracle (the binding ``Unbreakable`` challenge returns
    ``false``) whose abstract calls compute nothing the result depends on, so
    each is glob-preservingly droppable. It is False when *any* call feeds a
    later operand or the return (a live embedding such as KEMPRF's
    ``F.evaluate`` challenge), which must keep its own tactic. Returns False for
    a call-free body (nothing to drop or realign here).
    """
    call_vars = [s.var for s in body if isinstance(s, ec_ast.Call) and s.var]
    if not call_vars:
        return False
    operands: list[str] = []

    def collect(stmts: Sequence[ec_ast.EcStmt]) -> None:
        # ``if`` guards and branch bodies are reads too: a result consumed
        # only inside a guard used to be misjudged dead, and the branch
        # then emitted ``proc; sim`` over structurally different bodies (a
        # doomed tactic where an honest decline was available -- surfaced
        # by Move 4's early-return-lowering shapes, whose guards read the
        # deterministic results).
        for stmt in stmts:
            if isinstance(stmt, ec_ast.Call):
                operands.append(stmt.args)
            elif isinstance(stmt, ec_ast.Assign):
                operands.append(stmt.rhs)
            elif isinstance(stmt, ec_ast.Sample):
                operands.append(stmt.distr)
            elif isinstance(stmt, ec_ast.Return):
                operands.append(stmt.expr)
            elif isinstance(stmt, ec_ast.If):
                operands.append(stmt.guard)
                collect(stmt.then_body)
                collect(stmt.else_body)

    collect(body)
    blob = " ".join(operands)
    return not any(re.search(rf"\b{re.escape(v)}\b", blob) for v in call_vars)


def _leads_with_det(body: list[ec_ast.EcStmt]) -> bool:
    """True if ``body``'s first executable statement is a deterministic
    assignment (a ``wp``-absorbable leading run the final ``wp`` must clear).

    A leading call or sample is coupled by the peel loop itself, so only a
    leading assignment needs the trailing ``wp``.
    """
    execs = _exec_stmts(body)
    return bool(execs) and isinstance(execs[0], ec_ast.Assign)


def _is_tuple_literal(rhs: str) -> bool:
    """True when ``rhs`` renders as a top-level tuple constructor ``(a, b, ...)``.

    A parenthesized expression with a top-level comma inside the outermost
    parens -- as opposed to a projection ``t.`1`` or a parenthesized single
    expression. Used to spot the challenger-tuple repack an inlined reduction
    ``Initialize`` leaves behind (``_tup <- (ek0, C.dk0, ek1, C.dk1)``)."""
    s = rhs.strip()
    if not (s.startswith("(") and s.endswith(")")):
        return False
    depth = 0
    for ch in s[1:-1]:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            return True
    return False


def _has_tuple_repack(body: list[ec_ast.EcStmt]) -> bool:
    """True when ``body`` assigns a tuple-constructor literal to a local.

    The fingerprint of a field-holding reduction's inlined ``Initialize``: the
    inner challenger's multi-field ``Initialize`` return (``(ek0, dk0, ek1,
    dk1)``) is inlined to a tuple literal that the reduction then unpacks into
    its own globals. A direct-keygen init (``k <@ K.keygen(); pk <- k.`1``) and
    a stateless single-value delegate never build such a literal, so ``sim``
    aligns them -- this separates the peel case from the byte-identical ``sim``
    case even among field-holding reductions (``KEMPRF_INDCPA`` ``R_MultiPRF``
    holds ``pk`` but does its own keygen, so it keeps ``sim``)."""
    return any(
        isinstance(s, ec_ast.Assign) and _is_tuple_literal(s.rhs)
        for s in _exec_stmts(body)
    )


def _same_det_structure(
    left_body: list[ec_ast.EcStmt], right_body: list[ec_ast.EcStmt]
) -> bool:
    """True when the two bodies have the SAME deterministic statement structure.

    Compares the full executable statement lists under the rename-tolerant
    :func:`_reorder_sig` (a call by callee, a sample by distribution, an assign
    by its identifier-masked RHS *shape*, a return by kind). Two bodies that
    ``inline *; sim`` can align have identical such structure; a reduction-init
    body that delegates to a stateful inner challenger and repacks its tuple
    result carries extra assignments (a ``(ID, ID, ID, ID)`` pack + per-field
    ``ID.`k`` unpacks) absent on the direct-keygen side, so its signature list
    differs. Used to keep the byte-identical ``proc; inline *; sim`` init tactic
    for the clean inits while routing the reduction-init case to the peel.
    """
    return [_reorder_sig(s) for s in _exec_stmts(left_body)] == [
        _reorder_sig(s) for s in _exec_stmts(right_body)
    ]


def _paren_if_applied(text: str) -> str:
    """Parenthesize ``text`` if it is a top-level APPLICATION, else leave it.

    Substituting a variable whose value is ``f a b`` into an argument position
    would otherwise splice three arguments where one was written -- the outer
    application then parses with the wrong arity and every structural read of it
    fails for a reason that looks nothing like the cause.
    """
    stripped = text.strip()
    return f"({stripped})" if len(_app_args(stripped)) > 1 else stripped


def _fold_tuple_projections(expr: str) -> str:
    """``(a, b, c).`2`` -> ``b``, wherever it occurs in ``expr``.

    :func:`_projections` only recognises a BARE identifier base, which is the
    right granularity for reading a flat state's plumbing but not for resolving
    it: substituting a tuple-valued variable into ``t.`2`` produces a
    PARENTHESIZED base, and leaving that unfolded strands the resolution one
    step short of the backbone event it is meant to reach.
    """
    out = expr
    for _ in range(32):
        hit = re.search(r"\)\.`([0-9]+)", out)
        if hit is None:
            return out
        close = hit.start()
        depth = 0
        open_at = -1
        for pos in range(close, -1, -1):
            depth += (out[pos] == ")") - (out[pos] == "(")
            if depth == 0:
                open_at = pos
                break
        if open_at < 0:
            return out
        parts = _top_level_tuple_parts(out[open_at : close + 1])
        idx = int(hit.group(1))
        if parts is None or not 1 <= idx <= len(parts):
            return out
        out = out[:open_at] + parts[idx - 1].strip() + out[hit.end() :]
    return out


def _resolve_expr(expr: str, env: dict[str, str]) -> str:
    """``expr`` with every assigned local replaced by its defining expression and
    every top-level tuple projection folded.

    Used to decide two structural questions name-independently: whether a
    one-sided call's argument IS a particular sampled value (it resolves to that
    sample's variable), and which pairs of state variables hold the same value
    (their resolutions coincide). Both would otherwise need the exporter to
    recognise a variable by name.

    Bounded: substitution stops after a fixed number of rounds, so a cyclic
    ``env`` (which cannot arise from straight-line code, but must not hang the
    exporter if it did) falls out rather than looping.
    """
    cur = expr.strip()
    for _ in range(32):
        nxt = _IDENT_TOKENS.sub(
            lambda m: _paren_if_applied(env.get(m.group(0), m.group(0))), cur
        )
        folded = _fold_tuple_projections(nxt)
        if folded == cur:
            return cur
        cur = folded
    return cur


def _assign_env(stmts: list[ec_ast.EcStmt]) -> dict[str, str]:
    """``var -> resolved defining expression`` for the assignments in ``stmts``.

    Calls and samples are the LEAVES: their result variables are left
    unresolved, so every resolution bottoms out at a backbone event -- which is
    exactly the cross-side-comparable vocabulary.
    """
    env: dict[str, str] = {}
    for stmt in stmts:
        if isinstance(stmt, ec_ast.Assign):
            env[stmt.var] = _resolve_expr(stmt.rhs, env)
        elif isinstance(stmt, (ec_ast.Call, ec_ast.Sample)):
            env.pop(stmt.var, None)
    return env


def _event_align_swaps(
    stmts: list[ec_ast.EcStmt], target: list[tuple[str, str]], side: int
) -> tuple[list[str], list[ec_ast.EcStmt]] | None:
    """``swap{side}`` tactics putting ``stmts``' whole BACKBONE -- calls *and*
    samples -- into ``target`` order, or ``None``.

    :func:`_bundled_reorder_swaps` sorts calls only, which is enough when the
    two sides differ by a call reorder; the KDF-key substitution needs a SAMPLE
    to move as well (one side draws the key before its key generation, the other
    after its encapsulation), so the selection sort runs over
    :func:`_bd_events`. Same discipline: blocks only ever move UP, each travels
    with its feeding/unpacking assignments, and every crossed statement is
    ``_ec_indep``-validated -- so a data conflict declines rather than emitting a
    swap EasyCrypt will reject.
    """
    local = _ec_local_vars(stmts)
    cur = list(stmts)
    swaps: list[str] = []
    for slot, want in enumerate(target):
        events = [(i, s) for i, s in enumerate(cur) if _is_bb_stmt(s)]
        if len(events) != len(target):
            return None
        if _bd_events([events[slot][1]])[0] == want:
            continue
        src = next(
            (i for i, s in events[slot + 1 :] if _bd_events([s])[0] == want), None
        )
        if src is None:
            return None
        b_0, b_1 = _stmt_travel_block(cur, src, local)
        ins = 0 if slot == 0 else events[slot - 1][0] + 1
        if ins > b_0:
            return None
        block, crossed = cur[b_0 : b_1 + 1], cur[ins:b_0]
        if not all(_ec_indep(m, x, local) for m in block for x in crossed):
            return None
        if crossed:
            span = f"{b_0 + 1}" if b_0 == b_1 else f"[{b_0 + 1}..{b_1 + 1}]"
            swaps.append(f"swap{{{side}}} {span} -{b_0 - ins}.")
        cur = cur[:ins] + block + crossed + cur[b_1 + 1 :]
    return swaps, cur


def _equal_body_peel_tactic(
    body: list[ec_ast.EcStmt], micro_pre_text: str = "true"
) -> list[str] | None:
    """The peel for a leg whose two sides run the SAME program, or ``None``.

    Two shapes, both closing with ``auto => /#`` over the coupling:

    * the backbone is reachable from the top level -- the ordinary
      ``(wp; couple)*`` peel;
    * the body is a single top-level ``if`` and each arm's backbone is
      reachable -- **descend into the branch**. ``if`` on an equiv goal
      yields three goals in order (the guards' equivalence, the ``then``
      pair, the ``else`` pair). Because the two sides are the SAME program
      the two guards are the same expression, so the first closes from the
      coupling alone.

    The second shape is why this row exists at all: measured over the four
    census proofs, ALL 43 equal-body legs are blocked from the top-level
    peel, every one of them by calls under an ``if``'s else-arm (39 with two
    calls, 4 with seven). Their common source shape is a decapsulation
    oracle refusing the challenge ciphertext --
    ``if (ct = ctStar) { r <- None; } else { <calls>; r <- Some (..); }``.
    Probe: ``.ec-tmp/bystander/branchpeel_probe.ec``, with a proof-level
    negative control that drops the challenge-ciphertext coupling and is
    rejected with *cannot prove goal (strict)* at the guard step.

    Anything else -- a top-level ``while``, an arm holding a nested ``if``
    over a call, more than one top-level ``if`` -- returns ``None``: the
    peel would be too short and EasyCrypt would answer *invalid last
    instruction*.
    """
    if _peel_reaches_every_event(body):
        return ["proc.", *_backbone_peel(body), "auto => /#."]
    stmts = _exec_stmts(body)
    inner = _branch_descent(stmts, micro_pre_text, [])
    return None if inner is None else ["proc.", *inner]


def _branch_descent(
    stmts: list[ec_ast.EcStmt], micro_pre_text: str, bound: list[str]
) -> list[str] | None:
    """The descent for ``<leading run>? ; if (..) {..} else {..}``, recursive.

    One level emits, in EasyCrypt's own goal order:

    * when a leading run precedes the branch, ``seq n n : (<invariant>)``
      splitting it off, then that run's own peel. ``if`` is a
      FIRST-instruction rule, so without the split it is refused outright --
      *invalid first instruction*, measured on the corpus legs whose arm is
      ``[Assign, Call, If]``;
    * ``if``, whose first goal is the guards' equivalence. The two sides run
      the SAME program, so the two guards are the same expression and it
      closes from the coupling;
    * the ``then`` arm -- peeled under its own bullet, or, when it
      BRANCHES too, its whole descent nested there (EasyCrypt's bullets
      nest, so the sub-descent's bullets sit one level in). Measured need:
      the residual corpus legs branch on the then-side at level three, and
      a ``then`` arm carrying its own ``if`` is not peelable;
    * the ``else`` arm -- peeled if its backbone is reachable, else
      DESCENDED INTO, which is where this recurses.

    ``bound`` accumulates the locals every leading run has bound so far, and
    each level's invariant is those locals' equality plus the leg's coupling
    -- exactly what the next guard and its arms read. The names are read off
    the statements' own targets rather than predicted, so nothing depends on
    EasyCrypt's inline renaming.

    Measured need for the recursion: the corpus legs nest three deep (outer
    branch; a leading run and a branch; another branch inside that arm).
    Probes ``.ec-tmp/bystander/branchpeel_probe.ec`` (one level),
    ``branchpeel_seq_probe.ec`` (two) and ``branchpeel3_probe.ec`` (three),
    each with a proof-level negative control that is rejected at a guard.
    """
    core: list[ec_ast.EcStmt] = [s for s in stmts if not isinstance(s, ec_ast.Return)]
    branches = [s for s in core if isinstance(s, ec_ast.If)]
    if len(branches) != 1 or core[-1] is not branches[0]:
        return None
    lead: list[ec_ast.EcStmt] = core[:-1]
    branch = branches[0]
    out: list[str] = []
    if lead:
        # The invariant IS the coupling, so there is nothing to carry across
        # the split when the precondition is ``true``.
        if micro_pre_text == "true" or not _peel_reaches_every_event(lead):
            return None
        for stmt in lead:
            target = getattr(stmt, "var", None)
            if not isinstance(target, str) or not target:
                return None
            head = _RENAME_TOKEN_RE.match(target)
            if head is None or head.group(0) != target:
                return None
            if target not in bound:
                bound.append(target)
        if not bound:
            return None
        n = len(lead)
        out.append(f"seq {n} {n} : (={{{', '.join(bound)}}} /\\ {micro_pre_text}).")
        out.append("+ " + " ".join([*_backbone_peel(lead), "auto => /#."]))
    out.append("if.")
    out.append("+ move => &1 &2 /#.")
    # The `then` goal is closed under its own bullet. A `then` arm that
    # BRANCHES gets its whole descent nested there, indented -- EasyCrypt's
    # bullets nest, so the sub-descent's own bullets sit one level in.
    if _peel_reaches_every_event(branch.then_body):
        out.append("+ " + " ".join([*_backbone_peel(branch.then_body), "auto => /#."]))
    else:
        nested = _branch_descent(branch.then_body, micro_pre_text, list(bound))
        if nested is None:
            return None
        out.append("+ " + nested[0])
        out.extend("  " + line for line in nested[1:])
    if _peel_reaches_every_event(branch.else_body):
        return [*out, *_backbone_peel(branch.else_body), "auto => /#."]
    rest = _branch_descent(branch.else_body, micro_pre_text, bound)
    return None if rest is None else [*out, *rest]


def _same_memory_conjunct_fields(pre_text: str, fields: set[str]) -> set[str]:
    """State fields named in a SAME-MEMORY conjunct of the coupling.

    A conjunct mentioning only one of the two memories -- a survivor or
    hoist-cache invariant such as ``<S>.h{2} = M_c.ev_f (<S>.k{2})`` -- is a
    fact about one side that the postcondition demands back. A peel carries
    it through the frame only while the body leaves those fields alone, so a
    route relying on the frame must know which fields they are.
    """
    out: set[str] = set()
    for conj in _split_conjuncts(pre_text):
        if ("{1}" in conj) == ("{2}" in conj):
            continue
        out |= {tok for tok in _RENAME_TOKEN_RE.findall(conj) if tok in fields}
    return out


def _written_state_fields(body: list[ec_ast.EcStmt], fields: set[str]) -> set[str]:
    """The state fields ``body`` ASSIGNS to, branches included.

    :func:`_field_reference_order` deliberately skips the assignment target,
    so it answers "what does this body consume"; this is the other half, for
    a gate that must reason about what the body DISTURBS.
    """
    out: set[str] = set()
    for stmt in _flatten_stmts(body):
        target = getattr(stmt, "var", None)
        if not isinstance(target, str) or not target:
            continue
        head = _RENAME_TOKEN_RE.match(target)
        if head is not None and head.group(0) in fields:
            out.add(head.group(0))
    return out


def _backbone_peel(body: list[ec_ast.EcStmt]) -> list[str]:
    """The ``(wp; couple)*`` peel over ``body``'s call+sample backbone,
    tail-to-front.

    ``wp`` clears the deterministic run below the current backbone event, then
    ``call (_: true)`` couples a trailing abstract call and ``rnd`` a trailing
    ``<$`` sample. A body with no samples yields exactly the historical
    ``(wp; call (_: true))*`` (one round per call), so sample-free micros are
    byte-identical. Callers append any leading ``wp`` and the closing tactic.
    """
    tac: list[str] = []
    for kind, _callee in reversed(_call_sample_backbone(body)):
        tac.append("wp.")
        tac.append("call (_: true)." if kind == "call" else "rnd.")
    return tac


def _composite_bridge_tactic(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    modules: mt.ModuleTranslator,
    state: frog_ast.Game,
    oracle_name: str,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
) -> str | None:
    """Per-oracle wrapper<->flat bridge tactic for a composite-wrapper hop.

    Peels the oracle's shared call+sample backbone
    (``proc; inline *; (wp; couple)*; auto``) rather than ``sim``: a composite
    reduction-wrapper coupling relates a flat state's fields to a *different*
    module's fields (the reduction's own + its inner challenger's), and ``sim``
    cannot infer that cross-module equality set. ``call (_: true)`` couples each
    abstract call name-independently and ``auto`` discharges its argument
    equality from the coupling -- the same peel :func:`_synth_init_backbone_peel`
    uses for the init oracle. Sized to the oracle's post-``inline`` backbone,
    read off ``state`` (a flat state whose oracle body has the same call count as
    the wrapper's inlined body). Returns ``None`` if the body cannot be rendered.
    """
    proj = _project_to_method(state, oracle_name)
    if proj is None:
        return None
    mod = _flat_state_module(
        modules,
        "_bridge_peel",
        proj,
        external_module_types,
        method_return_types,
        flat_params,
    )
    if not mod.procs:
        return None
    body = mod.procs[0].body
    steps = ["proc", "inline *", *(s.rstrip(".") for s in _backbone_peel(body))]
    if _leads_with_det(body):
        steps.append("wp")
    steps.append("auto")
    return "; ".join(steps)


def _sample_reorder_swaps(
    left_body: list[ec_ast.EcStmt], right_body: list[ec_ast.EcStmt]
) -> list[str] | None:
    """``swap{1}`` tactics reordering ``left_body``'s samples to match
    ``right_body``'s call+sample backbone, leaving every non-sample anchor in
    place.

    Returns ``None`` unless the two backbones have an *identical probabilistic-
    call subsequence* and an *equal sample multiset* but differ only in the
    *order of the samples* (so the deterministic-functional middle leg can align
    them with sample ``swap``s, then peel the now-common backbone). A ``<$``
    sample is glob- and data-independent of every statement that currently
    precedes it (none can read a not-yet-sampled variable), so moving it *up* is
    always an EC-acceptable ``swap`` -- which is why a left-to-right selection
    that only ever hoists a sample is sound. This dodges the ``_rN`` renaming a
    reorder bundles in (``DeriveKeyPair`` becomes ``_r0`` on one side and ``_r1``
    on the other when its program-order index shifts), which defeats the
    full-signature :func:`_ec_full_perm_swaps`; ``wp`` dissolves those renamed
    deterministic locals during the subsequent peel.
    """

    def _bb_key(stmt: ec_ast.EcStmt) -> tuple[str, str | None] | None:
        if isinstance(stmt, ec_ast.Sample):
            return ("sample", getattr(stmt, "var", None))
        if isinstance(stmt, ec_ast.Call):
            return ("call", stmt.callee)
        return None

    lexec = _exec_stmts(left_body)
    rexec = _exec_stmts(right_body)
    l_bb = [k for s in lexec if (k := _bb_key(s)) is not None]
    r_bb = [k for s in rexec if (k := _bb_key(s)) is not None]
    if l_bb == r_bb:
        return None  # identical backbone -- handled by the plain peel
    if [e for e in l_bb if e[0] == "call"] != [e for e in r_bb if e[0] == "call"]:
        return None  # a probabilistic-call reorder, not a pure sample reorder
    if sorted(e[1] or "" for e in l_bb if e[0] == "sample") != sorted(
        e[1] or "" for e in r_bb if e[0] == "sample"
    ):
        return None  # sample multisets differ -- not a permutation of samples

    def _nth_bb_index(stmts: list[ec_ast.EcStmt], n: int) -> int | None:
        seen = 0
        for i, s in enumerate(stmts):
            if _bb_key(s) is not None:
                if seen == n:
                    return i
                seen += 1
        return None

    cur = list(lexec)
    swaps: list[str] = []
    for target, key in enumerate(r_bb):
        pos = _nth_bb_index(cur, target)
        if pos is None or _bb_key(cur[pos]) == key:
            continue
        src = next(
            (j for j in range(pos + 1, len(cur)) if _bb_key(cur[j]) == key), None
        )
        if src is None:
            return None
        swaps.append(f"swap{{1}} {src + 1} {pos - src}.")
        cur.insert(pos, cur.pop(src))
    return swaps


def _det_reorder_leg(
    left_body: list[ec_ast.EcStmt],
    right_body: list[ec_ast.EcStmt],
    allow_sample_reorder: bool = False,
) -> list[str] | None:
    """``F_left ~ F_right`` leg: both fully functional, differ by a reorder.

    Returns ``None`` when the leg cannot be synthesized (the caller then declines
    the whole functional-twin route).

    Two shapes, distinguished by whether the probabilistic calls are in the same
    order on both sides:

    - **Same probabilistic-call order** (the original same-module-det-reorder
      case): the sides hold the same probabilistic calls in the same order plus
      pure ``ev`` assignments distributed differently. EC's ``wp`` requires both
      sides' tails to be deterministic, so a ``wp`` before *every* ``call (_:
      true)`` clears whichever side currently trails in assignments (the reorder
      can put an assign at one side's tail and a call at the other's). The number
      of ``(wp; call)`` rounds is the abstract-call count (identical on both
      sides). A final ``wp`` clears any *leading* assignment run (before the
      first call) -- emitted only when a side actually leads with assignments,
      since ``wp`` on an already-empty program is rejected. ``skip => /#``
      discharges the functional equality.

    - **Reordered probabilistic calls** (the cross-module probabilistic reorder
      bundled with a same-module det reorder, e.g. ``Topological Sorting``):
      ``(wp; call)`` peeling would try to couple two different calls. Instead
      reorder ``F_left``'s statements to exactly match ``F_right`` with
      ``swap{1}`` (every reordered probabilistic pair is cross-module, hence
      EC-independent -- the gate guarantees per-module probabilistic order is
      preserved) and close the now-identical bodies with ``sim``.
    """
    left_bb = _call_sample_backbone(left_body)
    if left_bb == _call_sample_backbone(right_body):
        # Both twins share the same call+sample backbone (same interleaving),
        # differing only in the deterministic ``ev`` glue between events. Peel
        # the backbone tail-to-front: a ``wp`` clears the deterministic run below
        # the current event, then ``call (_: true)`` couples a trailing abstract
        # call and ``rnd`` couples a trailing ``<$`` sample (the same distribution
        # on both sides). ``wp`` can absorb neither, which is why each backbone
        # event needs an explicit coupling. A final ``wp`` clears any leading
        # deterministic run, then ``skip => /#`` discharges the ``ev`` equalities.
        tac = ["proc.", *_backbone_peel(left_body)]
        if _leads_with_det(left_body) or _leads_with_det(right_body):
            tac.append("wp.")
        tac.append("skip => /#.")
        return tac
    swaps = _ec_full_perm_swaps(left_body, right_body)
    if swaps is not None:
        return ["proc.", *swaps, "sim."]
    # Full-signature alignment declined -- typically a consistent ``_rN``
    # renaming bundled with the reorder (when two calls swap program order their
    # auto-numbered result vars swap too), so the before/after full-sig multisets
    # don't match. If the backbones differ only by *sample* order (the
    # probabilistic-call subsequence is identical), reorder the samples with
    # ``swap`` (glob-independent) and peel the now-common backbone -- ``wp``
    # dissolves the renamed deterministic locals, so the rename never surfaces.
    # Gated on ``allow_sample_reorder`` (set only when functionalization actually
    # turned some det call into an ``ev`` assignment): with no det calls the twin
    # is identical to the original module, so the simpler swap routes downstream
    # close it -- preempting them here would needlessly rewrite clean proofs.
    if not allow_sample_reorder:
        return None
    sample_swaps = _sample_reorder_swaps(left_body, right_body)
    if sample_swaps is not None:
        tac = ["proc.", *sample_swaps, *_backbone_peel(right_body)]
        if _leads_with_det(left_body) or _leads_with_det(right_body):
            tac.append("wp.")
        tac.append("skip => /#.")
        return tac
    return None


def _prob_callees(
    body: list[ec_ast.EcStmt], det_pred: Callable[[str, str], bool]
) -> list[str]:
    """Ordered callees of the *probabilistic* abstract calls in ``body``."""
    out: list[str] = []
    for stmt in _exec_stmts(body):
        if isinstance(stmt, ec_ast.Call):
            parts = _callee_parts(stmt.callee)
            if parts is None or not det_pred(parts[0], parts[1]):
                out.append(stmt.callee)
    return out


def _callee_is_det(callee: str, det_pred: Callable[[str, str], bool]) -> bool:
    """True if ``callee`` (a ``Module.method`` string) is a deterministic call."""
    parts = _callee_parts(callee)
    return parts is not None and det_pred(parts[0], parts[1])


def _has_det_call(
    body: list[ec_ast.EcStmt], det_pred: Callable[[str, str], bool]
) -> bool:
    """True if ``body`` contains at least one deterministic abstract call (so
    functionalizing it is non-trivial)."""
    return any(
        isinstance(s, ec_ast.Call) and _callee_is_det(s.callee, det_pred)
        for s in _exec_stmts(body)
    )


def _backbones_differ_only_by_samples(
    before_body: list[ec_ast.EcStmt],
    after_body: list[ec_ast.EcStmt],
    det_pred: Callable[[str, str], bool],
) -> bool:
    """True if the two bodies' *probabilistic* backbones (probabilistic calls +
    ``<$`` samples, deterministic calls excluded -- they functionalize away)
    differ *only* in the order of the samples: identical probabilistic-call
    subsequence and equal sample multiset, but a differing interleaving."""

    def _bb(body: list[ec_ast.EcStmt]) -> list[tuple[str, str | None]]:
        out: list[tuple[str, str | None]] = []
        for s in _exec_stmts(body):
            if isinstance(s, ec_ast.Call):
                if not _callee_is_det(s.callee, det_pred):
                    out.append(("call", s.callee))
            elif isinstance(s, ec_ast.Sample):
                out.append(("sample", getattr(s, "var", None)))
        return out

    lb = _bb(before_body)
    rb = _bb(after_body)
    if lb == rb:
        return False
    if [e for e in lb if e[0] == "call"] != [e for e in rb if e[0] == "call"]:
        return False
    return sorted(e[1] or "" for e in lb if e[0] == "sample") == sorted(
        e[1] or "" for e in rb if e[0] == "sample"
    )


def _det_call_sigs(
    body: list[ec_ast.EcStmt], det_pred: Callable[[str, str], bool]
) -> list[tuple[str, str]]:
    """Ordered ``(callee, args)`` signatures of the *deterministic* abstract calls
    in ``body`` (probabilistic calls and non-calls dropped).

    Used to spot a same-module reorder of two *same-callee* det calls -- e.g.
    ``NG.Encode(v8); NG.Encode(v5)`` swapping -- that the callee-name sequence
    (:func:`_ec_call_callees`) cannot see because both calls share the callee
    name. Probabilistic calls are excluded: a same-callee probabilistic reorder
    has no functional form (functionalization leaves it a call, and the middle
    leg would couple two differently-argued samples), so it must not route here.
    """
    out: list[tuple[str, str]] = []
    for stmt in _exec_stmts(body):
        if isinstance(stmt, ec_ast.Call):
            parts = _callee_parts(stmt.callee)
            if parts is not None and det_pred(parts[0], parts[1]):
                out.append((stmt.callee, stmt.args))
    return out


def _is_contiguous_dedup(
    before_body: list[ec_ast.EcStmt], after_body: list[ec_ast.EcStmt]
) -> bool:
    """True if the diff is the *contiguous-tail* dedup shape ``_synth_dedup_det``
    closes (``N>=2`` identical trailing calls collapsing to one). Orientation-
    independent: the longer body is the duplicating side. Mirrors the shape test
    in :func:`_synth_dedup_det` so the functional-twin route can decline it and
    leave that path (clean ``KEMPRF_Correctness``) byte-identical.
    """
    ea = _exec_stmts(before_body)
    eb = _exec_stmts(after_body)
    dup, single = (ea, eb) if len(ea) >= len(eb) else (eb, ea)
    prefix = 0
    while (
        prefix < len(dup)
        and prefix < len(single)
        and _stmt_full_sig(dup[prefix]) == _stmt_full_sig(single[prefix])
    ):
        prefix += 1
    dup_tail = [s for s in dup[prefix:] if not isinstance(s, ec_ast.Return)]
    single_tail = [s for s in single[prefix:] if not isinstance(s, ec_ast.Return)]
    if len(single_tail) != 1 or not isinstance(single_tail[0], ec_ast.Call):
        return False
    dup_calls = [s for s in dup_tail if isinstance(s, ec_ast.Call)]
    if not dup_tail or len(dup_calls) != len(dup_tail):
        return False
    canon = single_tail[0]
    return all((s.callee, s.args) == (canon.callee, canon.args) for s in dup_calls)


def _is_dedup_rewire(
    before_body: list[ec_ast.EcStmt],
    after_body: list[ec_ast.EcStmt],
    det_pred: Callable[[str, str], bool],
) -> bool:
    """True if before/after differ as a *non-contiguous* deduplication of
    deterministic calls (the rewire shape).

    The probabilistic calls must be untouched (same ordered sequence -- a dedup
    only removes a deterministic call), and the deterministic-call multisets must
    differ by genuine duplicates (the smaller is a sub-multiset of the larger and
    every removed callee still survives in the smaller). The *contiguous*-tail
    dedup (the ``_synth_dedup_det`` shape) is excluded so that path stays
    byte-identical.
    """
    bc = _ec_call_callees(before_body)
    ac = _ec_call_callees(after_body)
    if sorted(bc) == sorted(ac):
        return False
    if _prob_callees(before_body, det_pred) != _prob_callees(after_body, det_pred):
        return False
    det_b = Counter(c for c in bc if _callee_is_det(c, det_pred))
    det_a = Counter(c for c in ac if _callee_is_det(c, det_pred))
    larger, smaller = (
        (det_b, det_a) if det_b.total() >= det_a.total() else (det_a, det_b)
    )
    extra = larger - smaller
    if not extra or any(c not in smaller for c in extra):
        return False
    return not _is_contiguous_dedup(before_body, after_body)


def _needs_det_functional_reorder(
    before_body: list[ec_ast.EcStmt],
    after_body: list[ec_ast.EcStmt],
    det_pred: Callable[[str, str], bool],
    allow_cross_module: bool,
    allow_plumbing: bool = False,
) -> bool:
    """True if a deterministic reorder needs the functional-twin route (no
    EC-acceptable swap exists for it).

    Requires the same multiset of abstract callees and an identical
    probabilistic-call subsequence (kept aligned by the ``F_left ~ F_right``
    leg). Then fires when either:

    - **same-module** -- some declared module's own call order differs, so EC
      rejects any ``swap`` (shared ``glob``); the swap routes always fail. Fires
      for any transform.
    - **cross-module data-invalid** (only when ``allow_cross_module``) -- the
      ``_synth_isuv_walk`` swap route reorders the *right* (``after``) side's
      calls to the *left* (``before``) order keeping assignments fixed, and that
      alignment is a use-before-def (e.g. ``L.get`` pushed past the ``kdf_in_d``
      concat that reads it) the signature-only ``_ec_perm_swaps`` does not catch,
      so EC rejects it ("statements not independent"). ``allow_cross_module`` is
      False for ``Inline Local Tuple Literal`` micros: the tuple-walk aligns the
      non-tuple side to the (inlined) tuple side -- a different, valid direction
      (KEMPRF ``K.decaps`` past ``F.evaluate``) -- so those stay byte-identical
      on the swap path.
    - **plumbing rewrite** (only when ``allow_plumbing``) -- the abstract-call
      sequence is *identical* on both sides (no reorder at all); the diff is a
      deterministic tuple-projection/construction rewrite. The identical-order
      middle leg closes it. ``allow_plumbing`` is set only for the tuple-
      projection transforms in a multi-declared-module body (single-module
      proofs keep their tuple-walk / stateless route).
    """
    bc = _ec_call_callees(before_body)
    ac = _ec_call_callees(after_body)
    if not bc:
        return False
    if allow_plumbing and bc == ac:
        # No call reorder at all -- the abstract-call sequence is byte-identical
        # on both sides (same callees, same order). The diff is a deterministic
        # tuple-projection/construction plumbing rewrite (a ``Collapse Single-
        # Index Tuple Access`` / ``Expand Tuples`` micro: ``t <@ KeyGen(); x =
        # t[0]`` <-> ``r <@ KeyGen(); t = r[0]; x = t``). Functionalizing leaves
        # both twins with the *same* probabilistic calls in the same order, so
        # the identical-order ``(wp; call)*`` middle leg discharges the plumbing
        # via ``wp`` + ``skip => /#``. Fire only when the bodies genuinely differ
        # (a true EC no-op needs no twin and closes with plain ``sim``).
        return [_stmt_full_sig(s) for s in _exec_stmts(before_body)] != [
            _stmt_full_sig(s) for s in _exec_stmts(after_body)
        ]
    if sorted(bc) != sorted(ac):
        # Unequal call multisets are not a plain reorder. The one exception the
        # functional-twin route handles is a *deterministic-call deduplication*
        # whose surviving call is non-contiguously rewired (a duplicate ``L.get``
        # removed, its use rewired to an earlier ``L.get`` that the transform also
        # hoists). After functionalization every det call becomes an ``ev_<m>``
        # assignment, so both twins hold the *same* abstract (probabilistic) calls
        # and the ``(wp; call)*`` middle leg closes them; the redundant ``ev_*``
        # assignment on the dup side is absorbed by ``wp``. Restricted to non-tuple
        # transforms (tuple micros keep their tuple-walk) and to the rewire shape
        # (the contiguous-tail dedup stays on ``_synth_dedup_det`` -- byte-identical
        # for clean ``KEMPRF_Correctness``).
        return allow_cross_module and _is_dedup_rewire(
            before_body, after_body, det_pred
        )
    # The probabilistic calls must be the same multiset, and *each module's*
    # probabilistic-call subsequence must be preserved. The ``F_left ~ F_right``
    # leg aligns the functionalized twins by ``swap``; a probabilistic reorder is
    # only EC-swappable when it is cross-module (independent ``glob``s). A
    # same-module probabilistic reorder has neither a swap nor a functional form,
    # so decline it here (falls through to the swap walker / cache / admit).
    before_prob = _prob_callees(before_body, det_pred)
    after_prob = _prob_callees(after_body, det_pred)
    if sorted(before_prob) != sorted(after_prob):
        return False
    for mod in {c.split(".")[0] for c in before_prob if "." in c}:
        if [c for c in before_prob if c.startswith(mod + ".")] != [
            c for c in after_prob if c.startswith(mod + ".")
        ]:
            return False
    mods = {c.split(".")[0] for c in bc if "." in c}
    for mod in mods:
        if [c for c in bc if c.startswith(mod + ".")] != [
            c for c in ac if c.startswith(mod + ".")
        ]:
            return True
    # The per-module callee-name order matches, but two *same-callee*
    # deterministic calls of one module may still be reordered (differing only in
    # arguments, e.g. ``NG.Encode(v8); NG.Encode(v5)`` <-> the swap, from
    # ``Stabilize Independent Statements``). EC's ``swap`` rejects it (shared
    # ``glob``); functionalizing both calls to ``ev_*`` assignments leaves the
    # probabilistic-call order identical, so the same-order middle leg closes it.
    # Equal multiset + differing order == a genuine reorder; a differing multiset
    # would be a rename (leave it to the swap walker / cache).
    b_det = _det_call_sigs(before_body, det_pred)
    a_det = _det_call_sigs(after_body, det_pred)
    for mod in mods:
        bm = [sig for sig in b_det if sig[0].startswith(mod + ".")]
        am = [sig for sig in a_det if sig[0].startswith(mod + ".")]
        if sorted(bm) == sorted(am) and bm != am:
            return True
    if (
        allow_cross_module
        and bc != ac
        # The ISUV swap walker aligns right->left, so check that direction:
        # pass the *after* body as the alignment source and *before* as target.
        and _calls_only_alignment_invalid(
            before_body=after_body, after_body=before_body
        )
    ):
        return True
    # Cross-module reorder whose only *probabilistic-backbone* difference is the
    # order of the samples (a deterministic call shifting across other-module
    # calls, dragging its consumed sample with it -- e.g. ``Stabilize
    # Independent Statements`` moving ``KEM_PQ.derivekeypair`` and its seed
    # across the ``NG`` calls). EC ``swap`` would accept the reorder, BUT only
    # when no ``_rN`` renaming rides along: two calls that swap program order get
    # their auto-numbered result vars reassigned, and that rename pervades the
    # downstream call arguments, so neither the var-blind swap route's ``sim``
    # nor the full-signature swap can close it. Detect the rename as
    # ``_ec_full_perm_swaps`` declining despite the bodies being a reorder, and
    # route those through the functional twins (``wp`` in the sample-reorder
    # middle leg dissolves the renamed locals). Rename-free reorders keep their
    # existing, shorter swap close. Requires det calls to functionalize.
    if (
        allow_cross_module
        and _has_det_call(before_body, det_pred)
        and _backbones_differ_only_by_samples(before_body, after_body, det_pred)
        and _ec_full_perm_swaps(before_body, after_body) is None
    ):
        return True
    return False


def _synth_det_reorder(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    left_module: ec_ast.Module,
    right_module: ec_ast.Module,
    left_name: str,
    right_name: str,
    inst_suffix: str,
    oracle: str,
    pre: str,
    post: str,
    det_pred: Callable[[str, str], bool],
    clone_of: Callable[[str], str | None],
    allow_cross_module: bool,
    allow_plumbing: bool = False,
) -> _DetReorderSynth | None:
    """Synthesize the functional-module transitivity for a deterministic reorder.

    Returns ``None`` when the diff is not a deterministic reorder that needs the
    functional-twin route (so the caller falls through to the swap walker / cache
    / admit). See :func:`_needs_det_functional_reorder` for the firing criterion.
    """
    if not left_module.procs or not right_module.procs:
        return None
    left_body = left_module.procs[0].body
    right_body = right_module.procs[0].body
    if not _needs_det_functional_reorder(
        left_body, right_body, det_pred, allow_cross_module, allow_plumbing
    ):
        return None
    glob_items = [f"glob {p.name}" for p in left_module.params]

    fl_name = left_name + "_fdet"
    fr_name = right_name + "_fdet"
    fl_body = _ec_functionalize(left_body, det_pred, clone_of)
    fr_body = _ec_functionalize(right_body, det_pred, clone_of)
    lp = left_module.procs[0]
    rp = right_module.procs[0]
    fl_mod = ec_ast.Module(
        name=fl_name,
        procs=[ec_ast.Proc(lp.name, lp.params, lp.return_type, fl_body)],
        params=left_module.params,
    )
    fr_mod = ec_ast.Module(
        name=fr_name,
        procs=[ec_ast.Proc(rp.name, rp.params, rp.return_type, fr_body)],
        params=right_module.params,
    )

    # Functionalization is non-trivial iff it turned a det call into an ``ev``
    # assignment (shrinking the call backbone). Only then is the functional-twin
    # route's sample-reorder fallback worth preempting the simpler swap routes
    # with -- a body of only probabilistic calls keeps its existing close.
    funct_meaningful = _call_sample_backbone(fl_body) != _call_sample_backbone(
        left_body
    ) or _call_sample_backbone(fr_body) != _call_sample_backbone(right_body)
    leg_mid = _det_reorder_leg(fl_body, fr_body, allow_sample_reorder=funct_meaningful)
    if leg_mid is None:
        return None
    spec = f"({pre} ==> {post}) ({pre} ==> {post})"
    ctr = [0]
    l_params = [p.name for p in lp.params]
    r_params = [p.name for p in rp.params]
    leg1 = _det_topdown_leg(left_body, 1, glob_items, det_pred, ctr, l_params)
    leg3 = _det_topdown_leg(right_body, 2, glob_items, det_pred, ctr, r_params)

    tactic: list[str] = [_res_tag(SYNTH_PARAM)]
    tactic.append(f"transitivity {fl_name}{inst_suffix}.{oracle} {spec}.")
    tactic.append("smt().")
    tactic.append("smt().")
    tactic.extend(leg1)
    tactic.append(f"transitivity {fr_name}{inst_suffix}.{oracle} {spec}.")
    tactic.append("smt().")
    tactic.append("smt().")
    tactic.extend(leg_mid)
    tactic.extend(leg3)
    return _DetReorderSynth(
        module_texts=[
            "\n".join(_render_module_decl(fl_mod)),
            "\n".join(_render_module_decl(fr_mod)),
        ],
        module_names=[fl_name, fr_name],
        tactic=tactic,
    )


# ---------------------------------------------------------------------------
# Deduplicate-deterministic-calls synthesis
#
# ``Deduplicate Deterministic Calls`` collapses N>=2 identical calls to a
# deterministic scheme method (same callee, same args) into one, rewriting the
# return to reuse the single result (``_r0 <@ F.evaluate(ss,ct); _r1 <@
# F.evaluate(ss,ct); return (..,_r0,_r1)`` -> ``__d <@ F.evaluate(ss,ct);
# return (..,__d,__d)``). ``sim`` cannot align the asymmetric call counts. The
# close: ``seq P P`` past the identical prefix (``sim``), capture ``glob M`` and
# the shared call args with ``exists*``, then peel every call (N on the dup
# side, 1 on the other) with the ``<M>_<m>_det`` determinism axiom -- which
# pins each result to ``ev_<m> args`` -- so all results coincide and
# ``skip => /#`` discharges the return equality. Every quantity (prefix length,
# coupling vars, args, axiom name) is read off the rendered EC bodies, so this
# is ``synth-param``. The ``_det`` axioms are emitted unconditionally for every
# declared module's deterministic methods. Validated on KEMPRF_Correctness
# hop_2 (EC EXIT 0).
# ---------------------------------------------------------------------------


def _synth_dedup_det(  # pylint: disable=too-many-return-statements,too-many-locals,too-many-branches
    before_module: ec_ast.Module,
    after_module: ec_ast.Module,
    declared_names: set[str],
    reversed_dir: bool,
) -> list[str] | None:
    """Synthesize the determinism-axiom finisher for a dedup micro.

    ``before_module`` is the rendered state with the duplicated calls;
    ``after_module`` the deduplicated state. The dup side is 1 when forward
    (``before`` is the lemma's left) and 2 when reversed. Returns ``None`` when
    the diff is not ``N>=1`` identical trailing deterministic calls to one
    declared module collapsing to a single call.
    """
    if not before_module.procs or not after_module.procs:
        return None
    b_exec = _exec_stmts(before_module.procs[0].body)
    a_exec = _exec_stmts(after_module.procs[0].body)
    # Longest identical executable prefix. ``_stmt_text`` alone is only the
    # data content (a Call's args, an Assign's rhs), so a deduplicated call
    # whose args match its predecessor would be swept into the prefix -- compare
    # the full signature (kind + lhs var + callee + data) instead.
    prefix = 0
    while (
        prefix < len(a_exec)
        and prefix < len(b_exec)
        and _stmt_full_sig(a_exec[prefix]) == _stmt_full_sig(b_exec[prefix])
    ):
        prefix += 1
    b_tail = [s for s in b_exec[prefix:] if not isinstance(s, ec_ast.Return)]
    a_tail = [s for s in a_exec[prefix:] if not isinstance(s, ec_ast.Return)]
    if len(a_tail) != 1 or not isinstance(a_tail[0], ec_ast.Call):
        return None
    if not b_tail or not all(isinstance(s, ec_ast.Call) for s in b_tail):
        return None
    canon = a_tail[0]
    b_calls = [s for s in b_tail if isinstance(s, ec_ast.Call)]
    if any((s.callee, s.args) != (canon.callee, canon.args) for s in b_calls):
        return None
    parts = _callee_parts(canon.callee)
    if parts is None or parts[0] not in declared_names:
        return None
    mod, meth = parts
    det = f"{mod}_{meth}_det"
    arg_exprs = _split_top_args(canon.args)
    # Coupling carried across the ``seq`` split: globs of every declared module
    # plus each variable produced in the (identical) prefix. ``sim`` proves them
    # all (the prefix is syntactically equal); extra equalities are harmless.
    prefix_vars: list[str] = []
    for stmt in b_exec[:prefix]:
        var = getattr(stmt, "var", None)
        if var and var not in prefix_vars:
            prefix_vars.append(var)
    coupling_items = [f"glob {m}" for m in sorted(declared_names)] + prefix_vars
    coupling = "={" + ", ".join(coupling_items) + "}"
    dup_side = 2 if reversed_dir else 1
    other_side = 1 if reversed_dir else 2
    names = " ".join(["g"] + [f"a{i}" for i in range(len(arg_exprs))])
    apply_args = names
    capture = ", ".join(
        [f"(glob {mod}){{{dup_side}}}"] + [_mem_expr(e, dup_side) for e in arg_exprs]
    )
    body = [
        _res_tag(SYNTH_PARAM),
        "proc.",
        f"seq {prefix} {prefix} : ({coupling}).",
        "sim.",
        f"exists* {capture}; elim* => {names}.",
    ]
    body.extend(f"call{{{dup_side}}} ({det} {apply_args})." for _ in b_tail)
    body.append(f"call{{{other_side}}} ({det} {apply_args}).")
    body.append("skip => /#.")
    return body


# ---------------------------------------------------------------------------
# Dead-abstract-call-drop synthesis
#
# ``Topological Sorting`` prunes statements the return does not transitively
# depend on. When the pruned statements are *abstract scheme calls* (e.g. a
# reduction's ``S.keygen(); S.enc(...)`` whose results feed nothing once the
# challenger oracle is the ``Random`` one), EC cannot simply drop them: an
# abstract call may write ``glob S``, so dropping it on one side would violate
# the ``={glob S}`` postcondition. It IS sound here because ProofFrog only
# prunes a call under its stateless-scheme model -- the call has no observable
# effect. We make that assumption explicit with a ``<M>_<m>_pres`` glob-
# preservation phoare axiom (the result-agnostic sibling of ``<M>_<m>_det``) and
# drop each dead call one-sided: ``seq <ndrop> 0 : (<pre>); call{1} (<m>_pres
# g); ...; auto; sim``. Validated end-to-end on ``GeneralDoubleSymEnc_INDOT$``
# hop_2 (EC EXIT 0).
#
# Scope: the dead calls must be a CONTIGUOUS PREFIX of the longer side, all
# abstract calls to declared modules, and none of their results used by a
# surviving statement. Anything else falls through to cache/admit.
# ---------------------------------------------------------------------------


@dataclass
class _DeadCallDrop:
    """Synthesized dead-abstract-call-drop proof for one micro."""

    tactic: list[str]
    methods: set[tuple[str, str]]  # (declared module var, EC method name)


def _pres_lemma_name(mod: str, meth: str) -> str:
    return f"{mod}_{meth}_pres"


def _synth_dead_call_drop(  # pylint: disable=too-many-return-statements,too-many-locals,too-many-branches
    before_module: ec_ast.Module,
    after_module: ec_ast.Module,
    declared_names: set[str],
    eq_args: str,
    reversed_dir: bool,
) -> _DeadCallDrop | None:
    """Synthesize a one-sided drop of dead abstract calls for a prune micro.

    ``before_module`` is the rendered longer state (it makes the dead calls);
    ``after_module`` is the rendered pruned state. The lemma's drop side is 1
    when forward (``before`` is the left) and 2 when reversed.

    Returns ``None`` (caller falls through) when the diff is not a contiguous
    prefix of dead abstract calls to declared modules whose results no surviving
    statement uses.
    """
    if not before_module.procs or not after_module.procs:
        return None
    b_exec = _exec_stmts(before_module.procs[0].body)
    a_exec = _exec_stmts(after_module.procs[0].body)
    if len(b_exec) <= len(a_exec):
        return None
    ndrop = len(b_exec) - len(a_exec)
    dropped = b_exec[:ndrop]
    surviving = b_exec[ndrop:]
    # The surviving suffix must match the pruned side exactly (by signature).
    if [_ec_sig(s) for s in surviving] != [_ec_sig(s) for s in a_exec]:
        return None
    methods: set[tuple[str, str]] = set()
    mods_in_order: list[str] = []
    dropped_vars: set[str] = set()
    dropped_calls: list[tuple[str, str, ec_ast.Call]] = []
    for stmt in dropped:
        if not isinstance(stmt, ec_ast.Call):
            return None
        parts = _callee_parts(stmt.callee)
        if parts is None or parts[0] not in declared_names:
            return None
        methods.add(parts)
        dropped_calls.append((parts[0], parts[1], stmt))
        if parts[0] not in mods_in_order:
            mods_in_order.append(parts[0])
        if stmt.var:
            dropped_vars.add(stmt.var)
    # Soundness: no surviving statement may use a dropped call's result.
    surv_text = "\n".join(_stmt_text(s) for s in surviving)
    for var in dropped_vars:
        if re.search(r"\b" + re.escape(var) + r"\b", surv_text):
            return None
    drop_side = 2 if reversed_dir else 1
    seq_tac = f"seq {ndrop} 0" if drop_side == 1 else f"seq 0 {ndrop}"
    sub: list[str] = []
    for mod in mods_in_order:
        sub.append(f"exists* (glob {mod}){{{drop_side}}}; elim* => g_{mod}.")
    # Peel dead calls from the back of the dropped block (reverse program order).
    for mod, meth, _stmt in reversed(dropped_calls):
        sub.append(f"call{{{drop_side}}} ({_pres_lemma_name(mod, meth)} g_{mod}).")
    sub.append("auto.")
    body = [_res_tag(SYNTH_PARAM), "proc.", f"{seq_tac} : ({eq_args})."]
    body.append("+ " + sub[0])
    body.extend("  " + line for line in sub[1:])
    body.append("sim.")
    return _DeadCallDrop(tactic=body, methods=methods)


def _render_module_decl(module: ec_ast.Module) -> list[str]:
    """Render a single Module as EC source lines.

    Bypasses the file-level pretty-printer so we can return a string
    chunk that gets dropped into ``chain_extra_decls`` alongside other
    raw EC fragments.
    """
    # pylint: disable=import-outside-toplevel
    from .ec_ast import pretty_print, EcFile

    rendered = pretty_print(EcFile(requires=[], decls=[module]))
    # Strip the auto-generated header and trailing blank.
    lines = rendered.splitlines()
    # Drop the "(* Auto-generated... *)" header and any blank lines around.
    while lines and (
        lines[0].startswith("(* Auto-generated") or lines[0].strip() == ""
    ):
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    return lines


def _micro_transform_comment(
    app: TransformApplication, reversed_dir: bool = False
) -> str:
    """The ``(* transform: ... *)`` header one chain micro carries.

    Identical in shape to the single-oracle path's (:func:`_render_micro_lemma`,
    via ``_MicroLemma.transform_name``/``bucket``), including the
    ``(reversed)`` marker on a right-chain micro, so the dashboard's
    comment/resolution-tag pairing counts multi-oracle micros exactly the way it
    counts single-oracle ones. Purely an EC comment -- it is what makes each
    micro attributable to the transform application it machine-checks.
    """
    name = app.transform_name + (" (reversed)" if reversed_dir else "")
    return f"(* transform: {name} (bucket={classify(app.transform_name).value}) *)"


_FIELD_PAIR_RE = re.compile(r"(\w+)\.(\w+)\{1\}\s*=\s*(\w+)\.(\w+)\{2\}")


_FIELD_EQ_RE = re.compile(r"(\w+)\.(\w+)\{(\d)\}\s*=\s*(\w+)\.(\w+)\{(\d)\}")


def _coupled_field_renaming(
    pre_text: str, side1_base: str, side2_base: str
) -> dict[str, str]:
    """Map each field name to a representative of its coupling-equal class.

    Every ``<Mod>.<f>{i} = <Mod>.<g>{j}`` conjunct naming one of the lemma's two
    modules says the two fields hold the same value, so either may be
    substituted for the other when comparing the two programs. BOTH orientations
    matter: the cross-side pairs (``{1} = {2}``) carry a rename, and the
    SAME-side pairs (the survivor invariant ``dk0 = challenger_dk0``, stated on
    one side) carry the redundant-copy identity that the field-removal shape is
    entirely about. Union-find over the names, mapping each to the smallest
    member of its class.
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    bases = {side1_base, side2_base}
    for mb1, f, _s1, mb2, g, _s2 in _FIELD_EQ_RE.findall(pre_text):
        if mb1 not in bases or mb2 not in bases:
            continue
        ra, rb = find(f), find(g)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return {name: find(name) for name in parent}


_PACKED_LEFT_RE = re.compile(r"([\w.]+)\.(\w+)\{\d\} = \(([^()]+)\)\{\d\}")
_PACKED_RIGHT_RE = re.compile(r"\(([^()]+)\)\{\d\} = ([\w.]+)\.(\w+)\{\d\}")
_QUALIFIED_FIELD_RE = re.compile(r"^([\w.]+)\.(\w+)$")


def _coupled_packed_expansion(
    pre_text: str, side1_base: str, side2_base: str, renaming: dict[str, str]
) -> dict[str, str]:
    """Map each PACKED field to the text of its component tuple.

    A conjunct ``<L>.ctStar{1} = (<R>.ctStar_0, <R>.ctStar_1){2}`` says the one
    field holds exactly what the two fields hold, so a read of the packed field
    may be REWRITTEN as the tuple when comparing the two programs -- which is
    what makes ``ct = ctStar`` and ``ct = (ctStar_0, ctStar_1)`` the same test.
    Unlike :func:`_coupled_field_renaming` this is an expansion rather than a
    rename, so it is kept separate and merged only by the route that needs it.

    Components are spelled through the renaming already in force, so the two
    sides normalize to the same text. A packed name that ALSO appears in a plain
    field equality is left alone: that says the name denotes a field on both
    sides, so expanding it would rewrite the wrong side's read as well, and it
    says some other route already related the two.
    """
    bases = {side1_base, side2_base}
    related_plainly = {
        name
        for mb1, f, _s1, mb2, g, _s2 in _FIELD_EQ_RE.findall(pre_text)
        if mb1 in bases and mb2 in bases
        for name in (f, g)
    }
    out: dict[str, str] = {}
    for part in (p.strip() for p in pre_text.split("/\\")):
        left = _PACKED_LEFT_RE.fullmatch(part)
        right = _PACKED_RIGHT_RE.fullmatch(part)
        if left is not None:
            packed_base, packed, components = (
                left.group(1),
                left.group(2),
                left.group(3),
            )
        elif right is not None:
            packed_base, packed, components = (
                right.group(2),
                right.group(3),
                right.group(1),
            )
        else:
            continue
        if packed_base not in bases:
            continue
        names: list[str] = []
        for component in (c.strip() for c in components.split(",")):
            match = _QUALIFIED_FIELD_RE.fullmatch(component)
            if match is None or match.group(1) not in bases:
                names = []
                break
            names.append(match.group(2))
        if not names or packed in related_plainly:
            continue
        out[packed] = "(" + ", ".join(renaming.get(n, n) for n in names) + ")"
    return out


def _bodies_equal_under_field_map(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    side1: ec_ast.Module,
    side2: ec_ast.Module,
    pre_text: str,
    side1_base: str,
    side2_base: str,
    fields1: set[str],
    fields2: set[str],
) -> bool:
    """True if the two oracle bodies are the same program modulo the coupling.

    The field-cardinality survivor peel couples each abstract call with
    ``call (_: true)`` and closes with one ``auto``, which discharges the
    result equality and the field conjuncts from the precondition. That is
    sound exactly when the two programs become the SAME program once every
    field is replaced by a representative of the class the coupling proves it
    equal to (:func:`_coupled_field_renaming`): then each call receives equal
    arguments under the invariant and the results agree. The validated shape
    is exactly this -- ``K.decaps(challenger_dk0, ct)`` against
    ``K.decaps(dk0, ct)`` with ``dk0 = challenger_dk0`` in the coupling. Any
    residual difference -- a field the coupling does not relate, a
    differently-shaped read such as a packed field against its components --
    means ``auto`` cannot finish, so the caller must decline.

    Names are substituted token-wise and only where the token is a declared
    field of the module being rendered, so a local is never rewritten.
    """
    # pylint: disable=protected-access
    if not side1.procs or not side2.procs:
        return False
    classes = _coupled_field_renaming(pre_text, side1_base, side2_base)
    ren1 = {k: v for k, v in classes.items() if k in fields1}
    ren2 = {k: v for k, v in classes.items() if k in fields2}

    def rendered(mod: ec_ast.Module, mapping: dict[str, str]) -> list[str]:
        out: list[str] = []
        for stmt in _exec_stmts(mod.procs[0].body):
            try:
                text = ec_ast._render_stmt(stmt)
            except TypeError:
                return []
            if mapping:
                text = re.sub(
                    r"\b\w+\b",
                    lambda m: mapping.get(m.group(0), m.group(0)),
                    text,
                )
            out.append(text)
        return out

    b1, b2 = rendered(side1, ren1), rendered(side2, ren2)
    return bool(b1) and b1 == b2


def _micro_pre_well_typed(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    meta: tuple[frog_ast.Game, frog_ast.Game, str, str, str],
    oracle_name: str,
    modules: mt.ModuleTranslator,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    flat_params: list[ec_ast.ModuleParam],
    use_canonical_fields: bool = False,
) -> bool:
    """True unless the micro's precondition is ill-typed as a STATEMENT.

    ``meta`` is ``(left_state, right_state, left_ref, right_ref, pre_text)``.
    Two ways a broken chain's coupling can fail to typecheck, both of which
    would make EasyCrypt reject the whole file:

    * a ``<Mod>.<f>{1} = <Mod>.<g>{2}`` conjunct equating differently-typed
      fields (``_chain_role_map`` is a union-find over bare field names, so
      an unrelated state's identically-named field can merge roles). A
      conjunct naming a module other than this lemma's two endpoints is
      skipped rather than judged;
    * a WHOLE-GLOB conjunct ``(glob A){1} = (glob B){2}`` between two states
      whose glob signatures differ. EasyCrypt compares globs by name and
      type, so a step that adds or removes a field (``Inline Single-Use
      Field``) makes the equality itself ill-typed: *no matching operator,
      named `=`* on the lemma statement, measured on
      ``UG_expanded_LEAK_BIND_K_PK`` ``micro_2_challenge_left_11``.

    ``use_canonical_fields`` must be the chain's own field-naming decision,
    or the signatures compared here are not the emitted ones. Used only to
    filter EVIDENCE-ONLY lemmas, so a mistake here can lose evidence but can
    never change a chain that carries its hop.
    """
    left_state, right_state, lref, rref, pre_text = meta
    lproj = _project_to_method(left_state, oracle_name)
    rproj = _project_to_method(right_state, oracle_name)
    if lproj is None or rproj is None:
        return True
    lbase, rbase = _ref_base(lref), _ref_base(rref)
    lmod = _flat_state_module(
        modules,
        lbase,
        lproj,
        external_module_types,
        method_return_types,
        flat_params,
        emit_state_vars=True,
        use_canonical_fields=use_canonical_fields,
    )
    rmod = _flat_state_module(
        modules,
        rbase,
        rproj,
        external_module_types,
        method_return_types,
        flat_params,
        emit_state_vars=True,
        use_canonical_fields=use_canonical_fields,
    )
    if f"(glob {lref}){{1}} = (glob {rref}){{2}}" in pre_text:
        # Compare the signature of the modules AS EMITTED -- the whole flat
        # state, not this oracle's projection -- and compare it with
        # :func:`_glob_signature`, which is what the emitter itself uses.
        # Both corrections are load-bearing, and each was measured:
        #
        # * the FIELD list of a projection can agree while the emitted
        #   modules' differs, since a field only another oracle reads is
        #   dropped by the projection;
        # * ``glob F(A, B)`` contains ``glob A`` only when ``F``'s body
        #   actually CALLS ``A`` (EC drops unused functor args), so two
        #   states whose ``initialize`` differs in which parameters it calls
        #   have DIFFERENT glob types even with identical field lists. That
        #   is not a solver problem and not a tactic problem: the STATEMENT
        #   does not typecheck, and EasyCrypt rejects the whole file with
        #   *no matching operator, named `='* naming no parameter types at
        #   all. Probed standalone in ``.ec-tmp/diag/param_glob_probe.ec``
        #   (two functors over one abstract module, one calling it and one
        #   not) and measured as the single cause of all four proofs that
        #   evidence-only emission was breaking, each goal read separately.
        param_names = [p.name for p in flat_params]
        if use_canonical_fields:
            param_names += [m for m, _ in modules.types.function_value_modules()]
        lfull = _render_flat_state(
            modules,
            lbase,
            left_state,
            external_module_types,
            method_return_types,
            flat_params,
            emit_state_vars=True,
            use_canonical_fields=use_canonical_fields,
        )
        rfull = _render_flat_state(
            modules,
            rbase,
            right_state,
            external_module_types,
            method_return_types,
            flat_params,
            emit_state_vars=True,
            use_canonical_fields=use_canonical_fields,
        )
        if _glob_signature(lfull, param_names) != _glob_signature(rfull, param_names):
            return False
    ltypes = {v.name: str(v.type) for v in lmod.module_vars}
    rtypes = {v.name: str(v.type) for v in rmod.module_vars}
    for mb1, f, mb2, g in _FIELD_PAIR_RE.findall(pre_text):
        if mb1 != lbase or mb2 != rbase:
            continue
        if f in ltypes and g in rtypes and ltypes[f] != rtypes[g]:
            return False
    return True


EVIDENCE_ONLY_HEADER = (
    "(* evidence-only: this leg closed but its chain did not; the hop is "
    "carried by the whole-oracle route below. *)"
)


def _mark_evidence_only(chunks: list[str]) -> list[str]:
    """Prefix each emitted micro lemma with the evidence-only banner.

    Purely an EasyCrypt comment. The banner sits ABOVE the
    ``(* transform: ... *)`` header so the dashboard's comment/resolution-tag
    pairing (which keys on the transform comment immediately preceding the
    lemma name) is untouched, and it tells a reader why these lemmas are not
    referenced by any chain.
    """
    return [f"{EVIDENCE_ONLY_HEADER}\n{c}" for c in chunks]


def _render_micro_lemma(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    micro: _MicroLemma,
    oracle_name: str,
    eq_args: str,
    postcondition: str = "={res}",
) -> list[str]:
    return _render_lemma_block(
        micro.name,
        micro.left_module,
        micro.right_module,
        oracle_name,
        eq_args,
        micro.body,
        comment=f"(* transform: {micro.transform_name} (bucket={micro.bucket.value}) *)",
        postcondition=postcondition,
    )


def _render_lemma_block(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    name: str,
    left_module: str,
    right_module: str,
    oracle_name: str,
    eq_args: str,
    body: list[str],
    comment: str | None = None,
    postcondition: str = "={res}",
) -> list[str]:
    out: list[str] = []
    if comment:
        out.append(comment)
    out.append(f"lemma {name} :")
    out.append(
        f"  equiv [ {left_module}.{oracle_name} ~ {right_module}.{oracle_name} :"
    )
    out.append(f"          {eq_args} ==> {postcondition} ].")
    out.append("proof.")
    for line in body:
        out.append(f"  {line}")
    out.append("qed.")
    return out


def _render_chain_body(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    left_modules: list[str],
    right_modules: list[str],
    micros_left: list[_MicroLemma],
    micros_right_rev: list[_MicroLemma],
    bridge_name: str,
    oracle_name: str,
    eq_args: str,
    postcondition: str = "={res}",
) -> list[str]:
    """Emit the transitivity chain body for the top-level hop_<i>_chain lemma.

    The chain goes:
        left[0] --micros_left--> left[N] --bridge--> right[M] --micros_right_rev--> right[0]

    ``micros_right_rev`` are the *reversed* right-side micro lemmas
    (each proves ``right[i+1] ~ right[i]``), used in forward order during
    chain walking so we never need ``symmetry``.
    """
    body: list[str] = []
    body.append("(* Chain through per-transform micro-lemmas. *)")
    spec = f"({eq_args} ==> {postcondition})"
    for i, micro in enumerate(micros_left):
        next_mod = left_modules[i + 1]
        body.append(
            f"transitivity {next_mod}.{oracle_name} "
            f"{spec} {spec}; "
            f"[ smt() | smt() | apply {micro.name} |]."
        )
    if micros_right_rev:
        body.append(
            f"transitivity {right_modules[-1]}.{oracle_name} "
            f"{spec} {spec}; "
            f"[ smt() | smt() | apply {bridge_name} |]."
        )
        for i in reversed(range(len(micros_right_rev))):
            target_mod = right_modules[i]
            rev = micros_right_rev[i]
            if i == 0:
                body.append(f"apply {rev.name}.")
            else:
                body.append(
                    f"transitivity {target_mod}.{oracle_name} "
                    f"{spec} {spec}; "
                    f"[ smt() | smt() | apply {rev.name} |]."
                )
    else:
        body.append(f"apply {bridge_name}.")
    return body


@dataclass(frozen=True)
class _RoReprogram:
    """The RO-REPROGRAMMING ``initialize`` shape, read off the two first flat
    states.

    One endpoint READS its random function at a KDF input it computes
    (``ss <- rF rest``); the other DRAWS that value FRESH (``ss <$ d``). The two
    draws of the function itself agree, but the READ makes full function equality
    UNESTABLISHABLE -- it would force an independent draw to equal a function of
    another draw -- so the hop's coupling can only ask for agreement OFF the
    challenge point, and the hop becomes a reprogramming argument.

    Keyed entirely on the shape: an arrow-typed state field APPLIED on one side
    against a SAMPLE of the codomain distribution on the other, at the same
    position of the returned tuple. The mirror hop, where BOTH sides draw fresh,
    does not match -- and must not, since there full equality holds and the stock
    ladder already proves it.
    """

    reader_side: int
    reader_rf: str
    sampler_rf: str
    dfun_op: str
    cod_distr: str
    dom_ty: str
    cod_ty: str
    muf: str
    pin_var: str
    read_var: str
    sample_var: str
    ct_field: str
    ct_component: int
    kem_field: str
    kem_component: int
    enc_op: str
    enc_callee: str
    enc_res: str
    slice_steps: tuple[tuple[str, str, str], ...]
    pin_path: tuple[tuple[str, bool], ...]
    # A KEYED random function's domain is a PAIR (``rF (key2, rest)``): the
    # extra KEY component's variable, and ``None`` for the flat shape -- every
    # flat-path consumer is byte-identical when this is None.
    pin_key_var: str | None = None

    @property
    def pin_expr(self) -> str:
        """The reprogramming point as the twin spells it: the rest variable
        alone (flat), or the ``(key, rest)`` tuple (keyed)."""
        if self.pin_key_var is None:
            return self.pin_var
        return f"({self.pin_key_var}, {self.pin_var})"

    @property
    def proj_arg_of(self) -> Callable[[str], str]:
        """Where the separation projection READS: the point itself (flat) or
        its rest COMPONENT (keyed)."""

        def go(expr: str) -> str:
            return expr if self.pin_key_var is None else f"{expr}.`2"

        return go

    @property
    def proj_slices_of(self) -> Callable[[str], str]:
        """The bare slice chain over a REST-typed expression, outer-first --
        what the helper lemma and the legs' hproj facts apply (they hold the
        rest component directly)."""

        def go(expr: str) -> str:
            for op, lo, hi in self.slice_steps:
                expr = f"{op} {cc_paren(expr)} {cc_paren(lo)} {cc_paren(hi)}"
            return expr

        return go

    @property
    def proj_of(self) -> Callable[[str], str]:
        """The slice chain that pulls the challenge ciphertext's ENCODING out of a
        KDF input POINT -- through the rest component first when keyed."""

        def go(expr: str) -> str:
            return self.proj_slices_of(self.proj_arg_of(expr))

        return go


def _split_app(text: str) -> list[str]:
    """Split a rendered APPLICATION on top-level whitespace (nesting-aware).

    ``challenge_common.split_top_args`` splits on top-level COMMAS, which is what
    a tuple needs and the opposite of what ``op a b`` needs."""
    out: list[str] = []
    depth = 0
    cur = ""
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch.isspace() and depth == 0:
            if cur.strip():
                out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _strip_parens(text: str) -> str:
    """``text`` with any redundant enclosing parenthesis pairs removed."""
    text = text.strip()
    while text.startswith("(") and text.endswith(")"):
        depth = 0
        for k, ch in enumerate(text):
            depth += ch in "(["
            depth -= ch in ")]"
            if depth == 0 and k < len(text) - 1:
                return text
        text = text[1:-1].strip()
    return text


def _concat_tree(text: str, types: tc.TypeCollector) -> object:
    """``(op, left, right)`` for a rendered concat application, nested; the bare
    token otherwise. Uses the REGISTERED concat ops, so a leaf that merely looks
    like an application is not mistaken for one."""
    text = _strip_parens(text)
    parts = _split_app(text)
    if len(parts) == 3 and types.concat_components(parts[0]) is not None:
        return (
            parts[0],
            _concat_tree(parts[1], types),
            _concat_tree(parts[2], types),
        )
    return text


def _concat_path_to(tree: object, leaf: str) -> list[tuple[str, bool]] | None:
    """``[(concat_op, take_right)]`` outer-first from ``tree`` down to ``leaf``."""
    if isinstance(tree, str):
        return [] if tree == leaf else None
    op, left, right = cast(tuple[str, object, object], tree)
    down = _concat_path_to(left, leaf)
    if down is not None:
        return [(op, False)] + down
    down = _concat_path_to(right, leaf)
    if down is not None:
        return [(op, True)] + down
    return None


class RoReprogramCoupling(NamedTuple):
    """What an RO-REPROGRAMMING hop's coupling must say instead of full function
    equality.

    ``reader_ref`` names the READING endpoint's random function, which the flat
    state resolves cleanly because it is an inlined delegate FIELD. The drawing
    endpoint's is a flat LOCAL, whose post-``inline *`` name no flat state knows
    -- so rather than guess it, this asks the caller to find the conjunct that
    already equates the two and read the other side off it. That keeps the
    replacement spelled exactly as the rest of the coupling spells it, whichever
    builder produced it.

    ``add_fmt`` are the replacement conjuncts, each with one ``{rf}`` slot for
    that name."""

    reader_ref: str
    add_fmt: tuple[str, ...]


_NON_IDENT = re.compile(r"\W+")


def _ev_twin_module(
    base: ec_ast.Module,
    new_name: str,
    det_pred: Callable[[str, str], bool],
    clone_of: Callable[[str], str | None],
) -> ec_ast.Module:
    """A copy of ``base`` renamed to ``new_name`` whose single procedure has its
    deterministic NG calls replaced by their ``ev_<m>`` assignments (via
    :func:`_ec_functionalize`). The ``ev``-assignment twin of an NG-calling flat
    state; keeps the fields, params, and interface identical so it plugs into the
    same transitivity chain."""
    proc = base.procs[0]
    ev_body = _ec_functionalize(proc.body, det_pred, clone_of)
    ev_proc = ec_ast.Proc(proc.name, proc.params, proc.return_type, ev_body)
    return ec_ast.Module(
        new_name,
        [ev_proc],
        list(base.params),
        base.implements,
        list(base.module_vars),
    )


def _drop_witness_seeds(stmts: list[ec_ast.EcStmt]) -> list[ec_ast.EcStmt]:
    """``stmts`` without its leading ``<var> <- witness`` seeds."""
    i = 0
    while (
        i < len(stmts)
        and isinstance(stmts[i], ec_ast.Assign)
        and cast(ec_ast.Assign, stmts[i]).rhs.strip() == "witness"
    ):
        i += 1
    return stmts[i:]


def _sample_front_swaps(
    body: list[ec_ast.EcStmt], target_distrs: list[str], side: int
) -> list[str] | None:
    """``swap{side}`` tactics hoisting ``body``'s samples to the front in
    ``target_distrs`` order.

    Two bodies drawing the same multiset of samples in different positions
    must be positionally distribution-aligned before a tail-to-front ``rnd``
    coupling; a ``<$`` draw is glob/data-independent of everything
    before it, so hoisting it up is always an EC-valid ``swap``.

    Each swap addresses a sample by its *occurrence* among the samples
    (``^ <${k}`` -- the k-th sample, a code-position pattern) and moves it to
    gap ``0`` (the block front). This is position-ROBUST: it depends only on the
    sample ordering, not on how many deterministic tuple-unpack assigns EC's
    ``inline *`` interposes (which the engine's flat state does not reproduce
    faithfully). Hoisting in *reverse* target order lands the samples at the
    front in target order. Requires ``target_distrs`` distinct (so the ordering
    is determined by distribution); returns ``None`` if it cannot align.
    """
    cur = [s.distr for s in _exec_stmts(body) if isinstance(s, ec_ast.Sample)]
    if cur == target_distrs:
        return []
    swaps: list[str] = []
    for distr in reversed(target_distrs):
        if distr not in cur:
            return None
        occ = cur.index(distr) + 1  # 1-indexed occurrence among current samples
        swaps.append(f"swap{{{side}}} ^ <${{{occ}}} @ 0.")
        cur.insert(0, cur.pop(occ - 1))
    if cur != target_distrs:
        return None
    return swaps
