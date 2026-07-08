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
from dataclasses import dataclass, field
from typing import Callable

from ... import frog_ast
from ...transforms._base import TransformApplication
from ...visitors import VariableCollectionVisitor
from . import ec_ast
from . import module_translator as mt
from . import type_collector as tc
from .canonical_form import _normalize_for_ec, canonical_text
from .resolution import (
    ADMIT_GUIDED,
    ADMIT_UNGUIDED,
    CACHED_UNGUIDED,
    SYNTH_PARAM,
    SYNTH_STATIC,
)
from .resolution import tag as _res_tag
from .tactic_cache import TacticCache
from .transform_buckets import PARAMETRIC_TACTIC, Bucket, classify, tactic_body

# Engine passes that are pure structural reorderings (modulo dead-code
# drops): we synthesize ``swap{1} pos delta.`` tactics from the AST diff
# instead of relying on a canned tactic body. If the diff isn't a clean
# permutation (e.g. ``Topological Sorting`` may drop dead samples — its
# DFS from the return ignores statements not transitively used by it),
# we fall back to ``admit.``.
_REORDER_TRANSFORMS = frozenset(
    {
        "Topological Sorting",
        "Bubble Sort Field Assignments",
        "Stabilize Independent Statements",
    }
)

# Transforms that drop a local tuple and rewrite its projections to the
# components. Their micro relates a tuple-bearing flat state to its
# tuple-free successor; the stateless ``Ideal`` route's ``_ec_tuple_inline``
# handles them name-independently (see ``_synth_stateless_reorder``).
_TUPLE_INLINE_TRANSFORMS = frozenset(
    {
        "Inline Local Tuple Literal",
        "Expand Tuples",
    }
)

# Deterministic tuple-projection rewrites whose micro keeps the *whole* abstract-
# call sequence identical (same callees, same order, same multiset) and only
# rearranges deterministic tuple-construction/projection plumbing (e.g.
# ``t <@ KeyGen(); x = t[0]`` <-> ``r <@ KeyGen(); t = r[0]; x = t``, or a tuple
# literal ``ek = (a, b)`` <-> its expanded components ``ek_0 = a; ek_1 = b``).
# There is no call reorder at all, so the swap routes have nothing to do and the
# stateless/tuple-walk routes are single-module only; in a multi-declared-module
# body these fall through to ``admit``. The functional-twin route closes them: in
# the twins every det call is an ``ev_*`` assignment, so both sides hold the same
# probabilistic calls in the same order and the identical-order ``(wp; call)*``
# middle leg discharges the plumbing difference via ``wp`` + ``skip => /#``.
_PLUMBING_REWRITE_TRANSFORMS = frozenset(
    {
        "Collapse Single-Index Tuple Access",
        "Expand Tuples",
        "Inline Single-Use Variables",
        # Inlining a *pure multi-use expression* into its use sites: a local
        # ``label <- concat ... ; F.evaluate(.., label)`` (used twice) becomes
        # ``F.evaluate(.., concat ...)`` at each site. The abstract-call sequence
        # is identical; only a deterministic assignment is dropped and its
        # expression substituted into call args -- the identical-order ``(wp;
        # call)*`` middle leg discharges the residual arg equality (``wp``
        # collects the inlined assignment, ``skip => /#`` equates the substituted
        # expressions). The static ``sp; wp; sim`` leaves that equality open.
        "Inline Multi-Use Pure Expressions",
        # The dual rewrite: a repeated deterministic tuple access
        # (``v.`1`` used several times) is extracted to a CSE local
        # (``__cse_v_0__ <- v.`1``) and the uses rewired to it. Again the
        # abstract-call sequence is identical; the diff is the extra CSE
        # assignments plus the rewired tuple-construction RHS, both absorbed by
        # ``wp`` with ``skip => /#`` closing the construction equality.
        "Extract Repeated Tuple Access",
        # A deterministic copy-alias rewrite that swaps a call argument for its
        # definitional equal (``encodeencapskey(__determ_4__.`1)`` <->
        # ``encodeencapskey(tup_01)`` given ``tup_01 <- __determ_4__.`1``). The
        # abstract-call *sequence* is identical (only one argument expression
        # changed), so the identical-order ``(wp; call)*`` middle leg closes it:
        # ``wp`` collects the alias assignment and ``skip => /#`` discharges the
        # residual argument equality. The static ``sp; wp; sim`` otherwise leaves
        # that equality open (a 0-admit file EC rejects).
        "Forward Expression Alias",
    }
)


# Transforms whose micros are closed by a synthesizer that lives at the
# chain-emitter level (the ``_try_*`` routes in ``emit_chain_for_hop``), not by
# a ``transform_buckets`` ``CANNED_TACTIC``/``PARAMETRIC_TACTIC`` entry. These
# reach ``synth-param`` when their shape matches and fall through to cache/admit
# otherwise -- i.e. they "degrade" like the reorder transforms. The dashboard
# reads this set so its capability column credits them (the bucket tables alone
# cannot see chain-emitter synthesis). Keep in sync with the ``_try_*`` gates:
# ``_TUPLE_INLINE_TRANSFORMS`` (tuple-walk / congruence / stateless),
# ``_PLUMBING_REWRITE_TRANSFORMS`` (the identical-call-sequence functional-twin
# route) and ``Deduplicate Deterministic Calls`` (``_synth_dedup_det``). The
# reorder transforms (``_synth_dead_call_drop``) are already credited via their
# empty ``CANNED_TACTIC`` entry, so they are not repeated here.
CHAIN_EMITTER_SYNTH_TRANSFORMS = frozenset(
    _TUPLE_INLINE_TRANSFORMS
    | _PLUMBING_REWRITE_TRANSFORMS
    | {"Deduplicate Deterministic Calls"}
)


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
        before_text = canonical_text(
            before_game, external_module_types, method_return_types
        )
        after_text = canonical_text(
            after_game, external_module_types, method_return_types
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
        before_text = canonical_text(
            before_game, external_module_types, method_return_types
        )
        after_text = canonical_text(
            after_game, external_module_types, method_return_types
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
                return det_re
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
                return [_res_tag(SYNTH_PARAM), "proc.", *swaps, "sim."]
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
                        _res_tag(SYNTH_PARAM),
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
                return [_res_tag(SYNTH_PARAM), *drop]
            cached = _layer2_lookup(app, reversed_dir)
            if cached is not None:
                return [_res_tag(CACHED_UNGUIDED), *cached]
            return [_res_tag(ADMIT_UNGUIDED), *_layer3_admit(app, bucket, reversed_dir)]
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
                        _res_tag(ADMIT_UNGUIDED),
                        *_layer3_admit(app, bucket, reversed_dir),
                    ]
                return [_res_tag(SYNTH_PARAM), *synthesized]
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
                    _res_tag(ADMIT_UNGUIDED),
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
                return [_res_tag(SYNTH_PARAM), "proc.", *swaps, "sp; wp; sim."]
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
                    _res_tag(SYNTH_PARAM),
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
                    return isuv_walk
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
            return [_res_tag(SYNTH_STATIC), "proc; ((sp; wp; sim) || sim)."]
        if body:
            return [_res_tag(SYNTH_STATIC), *body]
        cached = _layer2_lookup(app, reversed_dir)
        if cached is not None:
            return [_res_tag(CACHED_UNGUIDED), *cached]
        return [_res_tag(ADMIT_UNGUIDED), *_layer3_admit(app, bucket, reversed_dir)]

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
    # Positional-rename unions along each side's adjacency (same-cardinality only).
    for states in (left_states, right_states):
        for before, after in zip(states, states[1:]):
            fb, fa = fields_of(before), fields_of(after)
            if len(fb) == len(fa):
                for x, y in zip(fb, fa):
                    union(x, y)
    return {name: find(name) for name in parent}


def _make_field_aware_coupling(
    fields_by_base: dict[str, list[str]],
    survivor: dict[str, str],
    glob_params: list[str],
    role_of: dict[str, str] | None = None,
    qualified_ref_by_base: dict[str, dict[str, str]] | None = None,
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
    composite = set(qualified)

    def role(f: str) -> str:
        return roles.get(f, f)

    def qualify(base: str, f: str) -> str:
        return qualified.get(base, {}).get(f, f"{base}.{f}")

    def coupling(left_ref: str, right_ref: str) -> str:
        lb, rb = _ref_base(left_ref), _ref_base(right_ref)
        fl, fr = fields_by_base.get(lb), fields_by_base.get(rb)
        is_composite = lb in composite or rb in composite
        if fl is None or fr is None or (len(fl) == len(fr) and not is_composite):
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
                g = next(
                    (h for h in fr if h not in paired_r and role(h) == role(f)),
                    None,
                )
                if g is not None:
                    fields_conj.append(
                        f"{qualify(lb, f)}" "{1}" f" = {qualify(rb, g)}" "{2}"
                    )
                    paired_r.add(g)
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
        return " /\\ ".join([f"={{glob {p}}}" for p in glob_params] + fields_conj)

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


def _project_to_method(game: frog_ast.Game, oracle_name: str) -> frog_ast.Game | None:
    """Deepcopy ``game`` keeping only the method named ``oracle_name`` (lower)."""
    chosen = [m for m in game.methods if m.signature.name.lower() == oracle_name]
    if not chosen:
        return None
    proj = copy.deepcopy(game)
    proj.methods = [copy.deepcopy(chosen[0])]
    return proj


def _oracle_step_tactic(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    state_before: frog_ast.Game,
    state_after: frog_ast.Game,
    oracle_name: str,
    reversed_dir: bool,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    modules: mt.ModuleTranslator,
    flat_params: list[ec_ast.ModuleParam],
) -> list[str] | None:
    """Tactic for one chain step's micro lemma, restricted to ``oracle_name``.

    ``["proc; sim."]`` when that oracle's body is unchanged across the step
    (``sim`` preserves the coupling on untouched state); a ``proc; swap...;
    sim`` sequence when the step is a pure top-level reorder of that oracle's
    body; a backbone peel when the step is a "Remove redundant variables for
    fields" removal (the two states differ in ``glob`` cardinality, so the
    oracle reads a removed field via its survivor on one side and ``sim`` cannot
    relate the differently-named reads -- wall 4); ``None`` when none applies
    (the caller routes the whole oracle to a coupling-pending admit).
    """
    pb = _project_to_method(state_before, oracle_name)
    pa = _project_to_method(state_after, oracle_name)
    if pb is None or pa is None:
        return None
    # Field-removal step: the field-aware coupling carries a survivor invariant
    # (``dk0 = challenger_dk0``); peel the (structurally identical) call/sample
    # backbone with ``call (_: true)``/``rnd`` so ``auto; smt()`` discharges each
    # abstract-call arg equality from that invariant. ``sim`` cannot -- it has no
    # way to use the relational fact to equate ``K.decaps(challenger_dk0){1}``
    # with ``K.decaps(dk0){2}``. Validated: ``ec_templates/field_removal_coupling.ec``.
    if len(state_before.fields) != len(state_after.fields):
        amod = _flat_state_module(
            modules,
            "Step_rm",
            pa,
            external_module_types,
            method_return_types,
            flat_params,
        )
        if not amod.procs:
            return None
        body = amod.procs[0].body
        # Couple each abstract call (``call (_: true)``) / sample (``rnd``) of the
        # shared backbone, tail-to-front, then close with a single ``auto.``.
        # ``auto`` performs the trailing ``wp`` and the residual arg-equality
        # ``smt`` internally -- an EXPLICIT leading ``wp`` (as in ``_backbone_peel``)
        # instead leaves a first-order residual that batch ``smt()`` cannot close
        # even though the interactive prover can (validated tactic:
        # ``ec_templates/field_removal_coupling.ec`` -- ``proc; call (_: true); auto``).
        tac = ["proc."]
        for kind, _callee in reversed(_call_sample_backbone(body)):
            tac.append("call (_: true)." if kind == "call" else "rnd.")
        tac.append("auto.")
        return tac
    if pb.methods[0] == pa.methods[0]:
        return ["proc; sim."]
    before_h = _normalize_for_ec(
        copy.deepcopy(pb), external_module_types, method_return_types
    )
    after_h = _normalize_for_ec(
        copy.deepcopy(pa), external_module_types, method_return_types
    )
    swaps = _permutation_swaps(before_h, after_h, reversed_dir=reversed_dir)
    if swaps is not None:
        return ["proc.", *swaps, "sim."]
    return None


def _oracle_pending_admit(hop_index: int, oracle_name: str) -> list[str]:
    """Guided coupling-pending admit body for one oracle of a multi-oracle hop.

    The post-init oracle's body is non-trivially transformed across the hop's
    canonicalization chain (``_oracle_step_tactic`` returns ``None``), so the
    identical-state first cut (``proc; sim`` / pure reorder) cannot discharge
    it under the live-state coupling. Synthesizing a closing tactic is blocked
    on EC's ``inline *``-generated variable names (the determinism finisher's
    ``exists*`` captures and the ``seq`` invariant relating the two abstract
    ``encaps`` results both need those names, which the exporter cannot predict
    -- confirmed 2026-06-06: unification holes fail with "cannot infer all
    placeholders", and ``sim`` cannot align the ``F.evaluate`` inputs because
    they are tuple-projections of the differently-named ``encaps`` results).

    Rather than a bare admit, emit the VALIDATED fill template (rung
    ``admit-guided``): the determinism-axiom finisher derived end-to-end on
    KEMPRF hop_0_challenge (EC EXIT 0). The ``<...>`` placeholders are this
    hop's EC inline names -- read them off ``ec_print_goals`` and fill, or
    cache the filled tactic in the proof's ``.tactics.toml`` sidecar (the
    established mechanism for these name-dependent det finishers; cf. 5_8).
    """
    return [
        _res_tag(ADMIT_GUIDED),
        f"(* multi-oracle hop {hop_index}, oracle {oracle_name!r}: post-init",
        "   body transformed along the chain; not closed by proc; sim / reorder.",
        "   VALIDATED fill template (det-axiom finisher; KEMPRF hop_0_challenge",
        "   compiles EC EXIT 0). Fill <...> with this hop's EC inline names:",
        "     proc. inline *. sp. wp.",
        "     seq 1 1 : (={glob K, glob F} /\\ <encapsResL>{1} = <encapsResR>{2}",
        "                /\\ <live-state coupling>).",
        "     + sim.                          (* relate the abstract encaps calls *)",
        "     sp. wp.",
        "     exists* (glob F){1}, <FseedL>{1}, <FinputL>{1}; elim* => gf1 a0 a1.",
        "     call{1} (F_evaluate_det gf1 a0 a1).",
        "     exists* (glob F){2}, <FseedR>{2}, <FinputR>{2}; elim* => gf2 b0 b1.",
        "     call{2} (F_evaluate_det gf2 b0 b1).",
        "     skip => /#.",
        "   A reusable name-independent helper for the F.evaluate step (derive",
        "   once per primitive from F_evaluate_det; lets 'wp. call F_evaluate_equiv'",
        "   replace the two exists*/call blocks):",
        "     lemma F_evaluate_equiv : equiv[ F.evaluate ~ F.evaluate :",
        "       ={glob F, seed, input} ==> ={res, glob F} ].",
        "     proof. proc*; exists* (glob F){1}, seed{1}, input{1}; elim* => g s i;",
        "       call{1} (F_evaluate_det g s i); call{2} (F_evaluate_det g s i);",
        "       skip => /#. qed.",
        "   Per-shape variants (the body transform differs by hop):",
        "   - distribution swap (e.g. dsharedsecret <-> dbs_lambda under the",
        "     requires-equality alias): couple the two uniform samples with rnd,",
        "     discharging the distribution equality from is_funiform + is_full;",
        "   - sample/encaps order swap: swap{i} to align, then the det finisher;",
        "   - dead F.evaluate: call{i} (F_evaluate_det ...) to drop it, then sim. *)",
        "admit.",
        "qed.",
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
) -> tuple[list[str], set[tuple[str, str]], str] | None:
    """Closing tactic for an init-oracle equiv whose two endpoints have
    identical canonical bodies.

    ``init_repacks`` is True when one side is a reduction that HOLDS the live
    field itself and therefore repacks the challenger's ``Initialize`` tuple
    result into its own globals (the case ``sim`` cannot align); it gates the
    keygen/sample-only backbone peel so stateless-delegate reductions keep the
    byte-identical ``sim``.

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

    if [k for k, _ in l_bb] == [k for k, _ in r_bb]:
        if not _has_det_call(l_bb):
            if (
                init_repacks
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
                tac = ["proc.", "inline *.", *_backbone_peel(l_body), "auto."]
                return (tac, set(), SYNTH_PARAM)
            # Identical structure, or a stateless-delegate reduction ``sim``
            # aligns: keep the historical tactic verbatim (byte-identical path
            # for the clean correctness / INDCPA / stateless-reduction inits).
            return (["proc; inline *; sim."], set(), SYNTH_STATIC)
        tac = ["proc.", "inline *.", *_backbone_peel(l_body)]
        if _leads_with_det(l_body) or _leads_with_det(r_body):
            tac.append("wp.")
        tac.append("skip => /#.")
        return (tac, set(), SYNTH_PARAM)
    # Unequal backbones: try the dead-deterministic-call drop. The longer side's
    # backbone must be the shorter's with extra *deterministic* calls inserted.
    if len(l_bb) > len(r_bb):
        long_bb, long_body, short_body, side = l_bb, l_body, r_body, 1
    else:
        long_bb, long_body, short_body, side = r_bb, r_body, l_body, 2
    short_bb = r_bb if side == 1 else l_bb
    drops = _dead_call_drop_tags(long_bb, short_bb, det_methods)
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


def _dead_call_drop_tags(
    long_bb: list[tuple[str, str | None]],
    short_bb: list[tuple[str, str | None]],
    det_methods: dict[str, set[str]],
) -> list[bool] | None:
    """Tag each event of ``long_bb`` as a drop (extra) or shared, matching
    ``short_bb`` as a subsequence.

    Two events match if both are samples, or both are calls with the same
    callee. An unmatched ``long_bb`` event is a drop; it is only accepted if it
    is a call to a *deterministic* method (present in ``det_methods``), so the
    glob-preserving one-sided ``_pres`` drop is sound. Returns ``None`` if the
    subsequence match fails or a gap event is not a droppable deterministic call.
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
    init_reduction_repacks: bool = False,
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

    # Shared flat-state modules (full multi-oracle games) emitted ONCE.
    chunks: list[str] = []
    for mod_name, state in zip(left_mods, left_states):
        chunks.append(
            _render_flat_state(
                modules,
                mod_name,
                state,
                external_module_types,
                method_return_types,
                flat_params,
                emit_state_vars=True,
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
                emit_state_vars=True,
            )
        )

    bridge_tactic = "proc; inline *; ((sp; wp; sim) || sim)"
    tactic_body_by_oracle: dict[str, list[str]] = {}
    pres_methods: set[tuple[str, str]] = set()
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
        )
        chunks.extend(oracle_chunks)
        tactic_body_by_oracle[oracle_name] = outer_body
        pres_methods |= oracle_pres

    return MultiOracleHopChainInfo(
        extra_decls=chunks,
        tactic_body_by_oracle=tactic_body_by_oracle,
        pres_methods=pres_methods,
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
) -> tuple[list[str], list[str], set[tuple[str, str]]]:
    """Emit one oracle's chain artifacts + outer tactic body.

    Returns ``(extra_decls, outer_body, pres_methods)`` where ``pres_methods``
    is the set of ``(module, method)`` glob-preservation axioms the outer body
    references (empty unless the init synthesizer fired a dead-call drop). If any
    chain step's micro cannot be resolved (not identity, not a pure reorder), the
    chain is discarded and the outer body is a coupling-pending admit (no
    oracle-suffixed artifacts).
    """
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
    if is_init:
        proj_l = _project_to_method(left_states[-1], oracle_name)
        proj_r = _project_to_method(right_states[-1], oracle_name)
        if (
            proj_l is not None
            and proj_r is not None
            and proj_l.methods[0] == proj_r.methods[0]
        ):
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
            )
            if peel is not None:
                tactic, pres, rung = peel
                return [], [_res_tag(rung), *tactic, "qed."], pres
            # Backbones cannot be aligned (an extra call that is not a droppable
            # deterministic method): the peel does not apply. Emit a targeted,
            # honest admit rather than a silently-failing ``sim``.
            return [], _init_backbone_admit(hop_index, oracle_name), set()

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

    coupling = _make_field_aware_coupling(
        fields_by_base,
        survivor_map,
        [p.name for p in flat_params],
        _chain_role_map(norm_left, norm_right, survivor_map),
        qualified_ref_by_base,
    )

    # Composite-wrapper bridge tactic (wall 7). When the hop has a composite
    # reduction wrapper, the wrapper<->flat bridges carry a cross-module field
    # coupling that ``sim`` cannot infer ("cannot infer the set of equalities").
    # Peel the oracle's shared call backbone instead -- the same tactic the init
    # backbone peel uses -- discharging each abstract call's argument equality
    # from the coupling. Gated on a composite wrapper being present, so every
    # non-composite bridge (all clean proofs) keeps the byte-identical ``sim``
    # fallback below.
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

    def micro_pre(left_ref: str, right_ref: str) -> str:
        cpl = coupling(left_ref, right_ref)
        if is_init:
            return "true"
        return cpl if eq_args == "true" else f"{eq_args} /\\ {cpl}"

    def micro_post(left_ref: str, right_ref: str) -> str:
        return f"={{res}} /\\ {coupling(left_ref, right_ref)}"

    chunks: list[str] = []
    micros_left: list[str] = []
    for k, _app in enumerate(left_apps):
        tac = _oracle_step_tactic(
            left_states[k],
            left_states[k + 1],
            oracle_name,
            reversed_dir=False,
            external_module_types=external_module_types,
            method_return_types=method_return_types,
            modules=modules,
            flat_params=flat_params,
        )
        if tac is None:
            return [], _oracle_pending_admit(hop_index, oracle_name), set()
        name = f"micro_{hop_index}_{oracle_name}_left_{k}"
        lref, rref = mod_ref(left_mods[k]), mod_ref(left_mods[k + 1])
        micros_left.append(name)
        chunks.append(
            "\n".join(
                _render_lemma_block(
                    name,
                    lref,
                    rref,
                    oracle_name,
                    micro_pre(lref, rref),
                    tac,
                    postcondition=micro_post(lref, rref),
                )
            )
        )

    micros_right_rev: list[str] = []
    for k, _app in enumerate(right_apps):
        tac = _oracle_step_tactic(
            right_states[k],
            right_states[k + 1],
            oracle_name,
            reversed_dir=True,
            external_module_types=external_module_types,
            method_return_types=method_return_types,
            modules=modules,
            flat_params=flat_params,
        )
        if tac is None:
            return [], _oracle_pending_admit(hop_index, oracle_name), set()
        name = f"micro_{hop_index}_{oracle_name}_right_{k}_rev"
        # Reversed: proves Step_R_state_{k+1} ~ Step_R_state_k.
        lref, rref = mod_ref(right_mods[k + 1]), mod_ref(right_mods[k])
        micros_right_rev.append(name)
        chunks.append(
            "\n".join(
                _render_lemma_block(
                    name,
                    lref,
                    rref,
                    oracle_name,
                    micro_pre(lref, rref),
                    tac,
                    postcondition=micro_post(lref, rref),
                )
            )
        )

    bridge_name = f"canon_bridge_{hop_index}_{oracle_name}"
    bl, br = mod_ref(left_mods[-1]), mod_ref(right_mods[-1])
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
    outer_body = [
        "(* Per-transform: bridge wrappers to flat states, chain through. *)",
        f"transitivity {l0}.{oracle_name} "
        f"{_coupling_spec(left_wrapper_expr, l0, is_init, eq_args, coupling)} "
        f"{_coupling_spec(l0, right_wrapper_expr, is_init, eq_args, coupling)}; "
        f"[ smt() | smt() | {bridge_tactic} |].",
        f"transitivity {r0}.{oracle_name} "
        f"{_coupling_spec(l0, r0, is_init, eq_args, coupling)} "
        f"{_coupling_spec(r0, right_wrapper_expr, is_init, eq_args, coupling)}; "
        f"[ smt() | smt() | apply {chain_name} | {bridge_tactic} ].",
        "qed.",
    ]
    return chunks, outer_body, set()


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

    body = ["(* Chain through per-transform micro-lemmas (coupling-preserving). *)"]
    cur = left_refs[0]
    for i, micro in enumerate(micros_left):
        nxt = left_refs[i + 1]
        body.append(
            f"transitivity {nxt}.{oracle_name} "
            f"{spec(cur, nxt)} {spec(nxt, final_right)}; "
            f"[ smt() | smt() | apply {micro} |]."
        )
        cur = nxt
    if micros_right_rev:
        rn = right_refs[-1]
        body.append(
            f"transitivity {rn}.{oracle_name} "
            f"{spec(cur, rn)} {spec(rn, final_right)}; "
            f"[ smt() | smt() | apply {bridge_name} |]."
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
                    f"[ smt() | smt() | apply {rev} |]."
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
    )


def _render_flat_state(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    modules: mt.ModuleTranslator,
    mod_name: str,
    game: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    module_params: list[ec_ast.ModuleParam],
    emit_state_vars: bool = False,
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
    )
    return "\n".join(_render_module_decl(ec_module))


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
    """
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
