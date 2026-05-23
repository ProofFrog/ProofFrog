# pylint: disable=duplicate-code
"""Per-transform EasyCrypt exporter.

Emits one EC module per intermediate state of the engine's
canonicalization pipeline and chains them together via per-transform
``micro_*`` lemmas plus a top-level ``hop_<i>_chain`` lemma.

The per-transform exporter is a thin wrapper that delegates to the
unified pipeline in
:func:`proof_frog.export.easycrypt.exporter.export_proof_file` with
``mode="per-transform"``. The chain artifacts for each interchangeability
hop are emitted by :func:`emit_chain_for_hop`, which uses the shared
per-hop translators (``TypeCollector`` / ``ModuleTranslator``) to render
each flat intermediate-state module. A small pre-pass mangles synthetic
identifiers (``E.KeyGen@k0``) and hoists nested module calls so the
shared statement translator can consume the canonical AST.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable

from ... import frog_ast
from ...transforms._base import TransformApplication
from ..easycrypt import ec_ast
from ..easycrypt import module_translator as mt
from ..easycrypt import type_collector as tc
from .canonical_form import _normalize_for_ec, canonical_text
from .tactic_cache import TacticCache
from .transform_buckets import Bucket, classify, tactic_body

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


@dataclass
class _MicroLemma:
    name: str
    left_module: str
    right_module: str
    transform_name: str
    body: list[str]
    bucket: Bucket


def export_proof_file_per_transform(proof_path: str) -> str:
    """Export the proof in per-transform mode.

    Thin wrapper that delegates to the unified pipeline in
    ``proof_frog.export.easycrypt.exporter.export_proof_file`` with
    ``mode="per-transform"``. The unified pipeline produces the same
    structured EC output as ``per-hop`` mode (theory clone, reduction
    modules, reduction-as-adversary lifts, game-step wrappers,
    assumption-hop axiom appeals, main theorem), and additionally
    emits per-transform chain artifacts (flat-state modules,
    micro-lemmas, ``hop_<i>_chain`` lemmas) for each interchangeability
    hop. Each ``hop_<i>`` equiv lemma's proof body is then a short
    ``transitivity`` bridge that funnels through the chain.
    """
    # pylint: disable=import-outside-toplevel,cyclic-import
    from ..easycrypt.exporter import export_proof_file

    return export_proof_file(proof_path, mode="per-transform")


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
        """Layer 2: consult the sidecar tactic cache.

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
        """Layer 3: ``admit.`` with a Claude-targeted diagnostic comment.

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

    def _tactic_for(
        app: TransformApplication, bucket: Bucket, reversed_dir: bool = False
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
                return ["proc.", *swaps, "sim."]
            cached = _layer2_lookup(app, reversed_dir)
            if cached is not None:
                return cached
            return _layer3_admit(app, bucket, reversed_dir)
        body = tactic_body(app.transform_name, app)
        if multi_module and bucket == Bucket.CANNED and body:
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
                return ["proc.", *swaps, "sp; wp; sim."]
            return ["proc; sp; wp; sim."]
        if body:
            return body
        cached = _layer2_lookup(app, reversed_dir)
        if cached is not None:
            return cached
        return _layer3_admit(app, bucket, reversed_dir)

    micros_left: list[_MicroLemma] = []
    for k, app in enumerate(left_apps):
        bucket = classify(app.transform_name)
        body = _tactic_for(app, bucket)
        micro = _MicroLemma(
            name=f"micro_{hop_index}_left_{k}",
            left_module=mod_ref(left_mods[k]),
            right_module=mod_ref(left_mods[k + 1]),
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
        fwd_body = _tactic_for(app, bucket, reversed_dir=False)
        rev_body = _tactic_for(app, bucket, reversed_dir=True)
        fwd = _MicroLemma(
            name=f"micro_{hop_index}_right_{k}_fwd",
            left_module=mod_ref(right_mods[k]),
            right_module=mod_ref(right_mods[k + 1]),
            transform_name=app.transform_name,
            body=fwd_body,
            bucket=bucket,
        )
        rev = _MicroLemma(
            name=f"micro_{hop_index}_right_{k}_rev",
            left_module=mod_ref(right_mods[k + 1]),
            right_module=mod_ref(right_mods[k]),
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
    # Both ``proc; inline *; sim`` subgoals (wrapper ↔ flat-state) are
    # within the section's abstract-module scope; ``sim`` can prove
    # them because the wrappers inline to syntactically-identical
    # call sequences plus the strengthened ``={glob ...}`` pre/post.
    tactic = [
        "(* Per-transform: bridge wrappers to flat states, chain through. *)",
        f"transitivity {mod_ref(left_mods[0])}.{oracle_name} "
        f"({eq_args_strong} ==> {eq_post_strong}) "
        f"({eq_args_strong} ==> {eq_post_strong}); "
        f"[ smt() | smt() | proc; inline *; sim |].",
        f"transitivity {mod_ref(right_mods[0])}.{oracle_name} "
        f"({eq_args_strong} ==> {eq_post_strong}) "
        f"({eq_args_strong} ==> {eq_post_strong}); "
        f"[ smt() | smt() | apply {chain_lemma_name} | proc; inline *; sim ].",
        "qed.",
    ]
    return HopChainInfo(
        extra_decls=chunks,
        tactic_body=tactic,
        pre_override=eq_args_strong if multi_module else None,
        post_override=eq_post_strong if multi_module else None,
        requested_keys=requested_keys,
    )


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
    return ("other", repr(expr))


# ---------------------------------------------------------------------------
# Flat-state rendering
# ---------------------------------------------------------------------------


def _render_flat_state(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    modules: mt.ModuleTranslator,
    mod_name: str,
    game: frog_ast.Game,
    external_module_types: dict[str, str],
    method_return_types: dict[tuple[str, str], frog_ast.Type],
    module_params: list[ec_ast.ModuleParam],
) -> str:
    """Render one intermediate flat-state game as an EC module source string."""
    prepared = _normalize_for_ec(
        copy.deepcopy(game), external_module_types, method_return_types
    )
    ec_module = modules.translate_flat_game(
        prepared, mod_name, external_module_types, module_params=module_params
    )
    return "\n".join(_render_module_decl(ec_module))


# ---------------------------------------------------------------------------
# EC source rendering helpers
# ---------------------------------------------------------------------------


def _render_module_decl(module: ec_ast.Module) -> list[str]:
    """Render a single Module as EC source lines.

    Bypasses the file-level pretty-printer so we can return a string
    chunk that gets dropped into ``chain_extra_decls`` alongside other
    raw EC fragments.
    """
    # pylint: disable=import-outside-toplevel
    from ..easycrypt.ec_ast import pretty_print, EcFile

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
