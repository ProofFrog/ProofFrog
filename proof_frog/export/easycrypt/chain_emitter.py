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
            if swaps is not None:
                return [_res_tag(SYNTH_PARAM), "proc.", *swaps, "sim."]
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
            return [_res_tag(SYNTH_STATIC), "proc; sp; wp; sim."]
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
    # closes them: ``sp`` absorbs the leading parameter aliases that
    # inlining introduces (e.g. ``s0 <- s``); ``wp`` absorbs the
    # trailing ``_r0 <- <expr>; return _r0;`` shape that wrapping a
    # value-returning oracle adds; ``sim`` then matches the residual
    # symmetric call sequence.
    bridge_tactic = "proc; inline *; sp; wp; sim"
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
    # If any flat-state body translation:
    #   * fell back to ``return witness;`` (a FrogLang construct the EC
    #     expression translator doesn't yet handle), OR
    #   * has a micro whose tactic body is ``admit.`` (no canned tactic
    #     or sidecar entry covers the transform),
    # the chain can't be closed end-to-end. Discard the chain artifacts
    # and replace the outer hop's proof body with ``admit.`` plus a
    # structured comment, mirroring the per-micro unguided-admit shape
    # (ladder rung 6, ``admit-unguided``).
    #
    # NB: this whole-hop suppression is deliberately conservative -- emitting a
    # chain that still contains an ``admit.`` micro alongside a *silently-
    # failing* synth/canned sibling (e.g. ``inline_single_use_variables_tactic``
    # whose ``call (_: true)`` does not couple abstract-call results) would
    # produce a 0-error-looking file EasyCrypt still rejects. The per-transform
    # synthesizers run BEFORE this check, so a hop whose every micro now resolves
    # (e.g. ``GeneralDoubleSymEnc`` hop_0 tuple-congruence + hop_2 dead-call
    # drop) is NOT suppressed and its chain is emitted; only hops that retain a
    # genuinely-unresolved micro fall back to the whole-hop admit.
    has_stub_body = any("return witness;" in chunk for chunk in chunks)
    has_micro_admit = any(_chunk_has_micro_admit(chunk) for chunk in chunks)
    if has_stub_body or has_micro_admit:
        if has_stub_body:
            reason = (
                "at least one intermediate-state body could not be "
                "translated to EC (the engine produced a FrogLang "
                "construct the expression translator does not yet "
                "handle)"
            )
        else:
            culprits = _micro_admit_culprits(chunks)
            culprit_str = ", ".join(sorted(set(culprits))) if culprits else "<unknown>"
            reason = (
                "at least one micro lemma falls back to admit (no canned "
                "tactic or sidecar entry covers the underlying transform; "
                f"culprits: {culprit_str})"
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


def _glob_coupling(left_ref: str, right_ref: str) -> str:
    """``(glob L){1} = (glob R){2}`` -- the identical-state coupling invariant.

    Matches :func:`proof_translator.coupling_invariant`; duplicated here to
    keep ``chain_emitter`` free of a proof-translator import.
    """
    return f"(glob {left_ref})" "{1}" f" = (glob {right_ref})" "{2}"


def _coupling_spec(left_ref: str, right_ref: str, is_init: bool, eq_args: str) -> str:
    """``(<pre> ==> ={res} /\\ <coupling>)`` for a transitivity middle-spec.

    The init oracle establishes the coupling from ``true``; a post-init oracle
    additionally requires its argument equality (``eq_args``) in the
    precondition.
    """
    cpl = _glob_coupling(left_ref, right_ref)
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


def _oracle_step_tactic(
    state_before: frog_ast.Game,
    state_after: frog_ast.Game,
    oracle_name: str,
    reversed_dir: bool,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
) -> list[str] | None:
    """Tactic for one chain step's micro lemma, restricted to ``oracle_name``.

    ``["proc; sim."]`` when that oracle's body is unchanged across the step
    (``sim`` preserves the coupling on untouched state); a ``proc; swap...;
    sim`` sequence when the step is a pure top-level reorder of that oracle's
    body; ``None`` when neither applies (the caller routes the whole oracle to
    a coupling-pending admit).
    """
    pb = _project_to_method(state_before, oracle_name)
    pa = _project_to_method(state_after, oracle_name)
    if pb is None or pa is None:
        return None
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

    bridge_tactic = "proc; inline *; sp; wp; sim"
    tactic_body_by_oracle: dict[str, list[str]] = {}
    for oracle_name, is_init in oracles:
        eq_args = oracle_eq_args.get(oracle_name, "true")
        oracle_chunks, outer_body = _emit_one_oracle_chain(
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
        )
        chunks.extend(oracle_chunks)
        tactic_body_by_oracle[oracle_name] = outer_body

    return MultiOracleHopChainInfo(
        extra_decls=chunks, tactic_body_by_oracle=tactic_body_by_oracle
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
) -> tuple[list[str], list[str]]:
    """Emit one oracle's chain artifacts + outer tactic body.

    Returns ``(extra_decls, outer_body)``. If any chain step's micro cannot be
    resolved (not identity, not a pure reorder), the chain is discarded and the
    outer body is a coupling-pending admit (no oracle-suffixed artifacts).
    """
    # Inline-equivalent endpoints (the P5 identical-state finding at oracle
    # granularity): when the two endpoints' CANONICAL bodies for this oracle
    # are identical, the raw wrapper modules are inline-equivalent, so
    # ``proc; inline *; sim`` closes the lemma directly on the wrappers --
    # sidestepping the per-transform chain (which the keygen-inlining steps of
    # ``Initialize`` defeat: an inlining step is neither identity nor a pure
    # reorder, so ``_oracle_step_tactic`` returns ``None`` and the chain admits).
    # Scoped to the init oracle, where the body is a simple keygen delegation
    # that ``sim`` aligns reliably under the ``={glob K} /\\ ={glob F}`` coupling;
    # post-init oracles (tuple-plumbing / genuine body transforms) keep the
    # per-transform chain / coupling-pending admit.
    if is_init:
        proj_l = _project_to_method(left_states[-1], oracle_name)
        proj_r = _project_to_method(right_states[-1], oracle_name)
        if (
            proj_l is not None
            and proj_r is not None
            and proj_l.methods[0] == proj_r.methods[0]
        ):
            return [], [_res_tag(SYNTH_STATIC), "proc; inline *; sim.", "qed."]

    def micro_pre(left_ref: str, right_ref: str) -> str:
        cpl = _glob_coupling(left_ref, right_ref)
        if is_init:
            return "true"
        return cpl if eq_args == "true" else f"{eq_args} /\\ {cpl}"

    def micro_post(left_ref: str, right_ref: str) -> str:
        return f"={{res}} /\\ {_glob_coupling(left_ref, right_ref)}"

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
        )
        if tac is None:
            return [], _oracle_pending_admit(hop_index, oracle_name)
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
        )
        if tac is None:
            return [], _oracle_pending_admit(hop_index, oracle_name)
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
        f"{_coupling_spec(left_wrapper_expr, l0, is_init, eq_args)} "
        f"{_coupling_spec(l0, right_wrapper_expr, is_init, eq_args)}; "
        f"[ smt() | smt() | {bridge_tactic} |].",
        f"transitivity {r0}.{oracle_name} "
        f"{_coupling_spec(l0, r0, is_init, eq_args)} "
        f"{_coupling_spec(r0, right_wrapper_expr, is_init, eq_args)}; "
        f"[ smt() | smt() | apply {chain_name} | {bridge_tactic} ].",
        "qed.",
    ]
    return chunks, outer_body


def _render_coupling_chain_body(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    oracle_name: str,
    is_init: bool,
    eq_args: str,
    left_refs: list[str],
    right_refs: list[str],
    micros_left: list[str],
    micros_right_rev: list[str],
    bridge_name: str,
) -> list[str]:
    """Transitivity chain body with per-step coupling specs.

    Walks ``L0 -> ... -> Ln --bridge--> Rn -> ... -> R0`` applying each
    oracle-suffixed micro. Unlike the single-oracle :func:`_render_chain_body`
    (uniform ``={res}`` spec), every transitivity middle-spec couples the
    current intermediate module to the relevant endpoint, because the coupling
    invariant references the actual module names.
    """
    final_right = right_refs[0]

    def spec(a_ref: str, b_ref: str) -> str:
        return _coupling_spec(a_ref, b_ref, is_init, eq_args)

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


def _chunk_has_micro_admit(chunk: str) -> bool:
    """Return True if a rendered chunk has a tactic body that is ``admit.``.

    Used by the chain-renderer's fallback: if any micro lemma still
    admits, the chain can't close end-to-end, so we discard the chain
    artifacts and admit the outer hop directly. Bare ``admit`` substring
    checks would also fire on diagnostic-comment text containing the
    word, so we look only for the tactic-line form after a ``proof.``.
    """
    in_proof = False
    for line in chunk.splitlines():
        stripped = line.strip()
        if stripped == "proof.":
            in_proof = True
            continue
        if stripped == "qed.":
            in_proof = False
            continue
        if in_proof and stripped == "admit.":
            return True
    return False


_TRANSFORM_COMMENT_RE = re.compile(r"\(\* transform: (.+?) \(bucket=\w+\) \*\)")


def _micro_admit_culprits(chunks: list[str]) -> list[str]:
    """Return the transform names of micros whose tactic body is ``admit.``.

    Walks each rendered chunk; when ``admit.`` appears inside a
    ``proof. ... qed.`` block, records the most recent
    ``(* transform: NAME (bucket=...) *)`` comment in that chunk as the
    culprit. Used by the chain-renderer's fallback to name the
    responsible transform(s) in the structured admit comment so dashboards
    and human readers can attribute the admit to a specific transform.
    """
    culprits: list[str] = []
    for chunk in chunks:
        last_transform: str | None = None
        in_proof = False
        for line in chunk.splitlines():
            m = _TRANSFORM_COMMENT_RE.search(line)
            if m:
                last_transform = m.group(1)
                continue
            stripped = line.strip()
            if stripped == "proof.":
                in_proof = True
                continue
            if stripped == "qed.":
                in_proof = False
                continue
            if in_proof and stripped == "admit." and last_transform is not None:
                culprits.append(last_transform)
                last_transform = None
    return culprits


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
    return _ec_perm_swaps(left_mod.procs[0].body, right_mod.procs[0].body)


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
# use) is detected out of scope (a non-call executable statement survives, or
# the call sequences are not a permutation) and falls through to cache/admit.
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
