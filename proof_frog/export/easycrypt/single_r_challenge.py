"""Synthesizer for the CFRG single-reduction seedbased binding *challenge* hop_0.

The UG/UK seedbased LEAK-BIND-K-CT proofs use ONE reduction ``R`` that derives
its component keys as locals from a single seed field and forwards a KDF-input
collision straight to a (stateless) KDF collision challenger:

    Challenge(ct0, ct1):
      <derive keys from seed0; compute kdf_in_0, kdf_in_1>
      if (ct0 = ct1) return false;
      return challenger.Challenge(kdf_in_0, kdf_in_1)   (* H(x0)=H(x1) && x0<>x1 *)

``hop_0`` relates the game ``Hybrid_Breakable.challenge`` (``decaps ct0; decaps
ct1; k0=k1 && ct0<>ct1``) to this. Under ``ct0 <> ct1`` the challenger's extra
``kdf_in_0 <> kdf_in_1`` conjunct is redundant: the KDF input binds both
ciphertext components (``EncodeCiphertext(ct_PQ)`` + ``Encode(ct_T)``), so
``kdf_in_0 = kdf_in_1`` forces ``ct0 = ct1`` (contradiction). This module emits
the closing tactic; the redundancy is discharged by navigating the (arbitrary
depth) left-nested KDF concat to the two ciphertext leaves and applying encoding
injectivity. The seedbased KDF has 7 leaves / 6 concats, so the navigation is
generic (:func:`slice_to_leaf`), unlike the fixed 5-leaf two-KEM ``ConcatShape``.
"""

# ``SingleRHopSpec`` and ``binding_challenge.ChallengeHopSpec`` describe two
# different routes over the same problem domain, so their field *names* coincide
# (val_lemma_name, game_glob_mods, ct_params, red_base, ...) even though the
# fields mean different things -- ``red_base`` is the two-KEM ``R_PQ_Bind`` there
# and the single reduction ``R`` here, and the single-R spec carries seed fields
# the two-KEM one has no analogue for. Merging them into a shared base would
# couple two independent synthesizers to keep a name table in sync. The genuinely
# shared *code* lives in ``challenge_common``.
# pylint: disable=duplicate-code

from __future__ import annotations

from dataclasses import dataclass, field

from . import ec_ast
from .binding_challenge import _game_glob_elim, _peel_stmts, _prefix_and_if
from .challenge_common import kdf_freeze_and_evaluate, walk_env
from .challenge_common import paren as _paren
from .challenge_common import split_top_args as _split_top_args
from .challenge_common import subst as _subst


def parse_left_nested_concat(term: str) -> tuple[list[str], list[str]] | None:
    """Parse a left-nested concat ``(cOut (... (cIn l0 l1) ...) lN)`` into its
    concat op names (outer-first) and its leaves (``[l0, l1, ..., lN]``).

    Returns ``None`` if ``term`` is not a parenthesised ``(op left right)``
    application chain (e.g. a bare leaf)."""
    ops: list[str] = []
    right_leaves: list[str] = []  # collected outer-first, i.e. [lN, ..., l2]
    cur = term.strip()
    while True:
        # The outermost concat is the raw assignment RHS (unparenthesised);
        # nested concats are parenthesised ev-substituted sub-terms.
        if cur.startswith("(") and cur.endswith(")"):
            inner = cur[1:-1].strip()
        elif cur.startswith("concat_"):
            inner = cur
        else:
            return None
        head, _, rest = inner.partition(" ")
        if not head.startswith("concat_") or not rest:
            return None
        args = _split_top_args_space(rest)
        if len(args) != 2:
            return None
        ops.append(head)
        left, right = args
        right_leaves.append(right)
        # Descend into the left operand; stop when it is a bare (non-concat) leaf.
        if left.startswith("(concat_"):
            cur = left
            continue
        # innermost: left is l0, right (already appended) is l1
        leaves = [left] + list(reversed(right_leaves))
        return ops, leaves


def _split_top_args_space(rest: str) -> list[str]:
    """Split ``rest`` into two top-level tokens (a concat's ``left right``),
    nesting-aware over ``()`` and ``[]`` and ``\\``` `-projections."""
    depth = 0
    for i, ch in enumerate(rest):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == " " and depth == 0:
            left = rest[:i].strip()
            right = rest[i + 1 :].strip()
            # right may itself have trailing tokens only if malformed; a concat
            # has exactly two operands, so treat the remainder as the right arg.
            return [left, right]
    return [rest.strip()]


def slice_to_leaf(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    ops: list[str],
    leaves0: list[str],
    leaves1: list[str],
    target: int,
    from_hyp: str,
    tag: str,
) -> tuple[list[str], str]:
    """Emit the ``have`` chain deriving ``leaves0[target] = leaves1[target]`` from
    ``from_hyp : <full0> = <full1>`` (the KDF-input equality). Returns the lines
    plus the name of the final leaf-equality hypothesis.

    The KDF is left-nested: ``full = (ops[0] (ops[1] ... (ops[n-1] l0 l1) ...
    l_{n-1}) l_n)`` with ``n = len(ops)``. Leaf ``k`` is the RIGHT operand of the
    concat ``ops[n-k]`` (for ``k >= 1``); descend ``slice_concat_left`` through
    ``ops[0..n-k-1]`` to that sub-concat, then extract with ``slice_concat_right``
    (or, for ``k == 0``, ``slice_concat_left``)."""
    n = len(ops)  # number of concats; n + 1 leaves

    def term(side_leaves: list[str], k: int) -> str:
        """The concat of leaves ``0..k`` (``k >= 1``): ``(ops[n-k] term(k-1)
        l_k)``; ``term(0)`` is the bare ``l0``."""
        if k == 0:
            return side_leaves[0]
        return f"({ops[n - k]} {term(side_leaves, k - 1)} {side_leaves[k]})"

    def left_ax(op: str) -> str:
        return "slice_concat_left_" + op[len("concat_") :].replace("_to_", "_", 1)

    def right_ax(op: str) -> str:
        return "slice_concat_right_" + op[len("concat_") :].replace("_to_", "_", 1)

    lines: list[str] = []
    prev = from_hyp
    # Descend from the full term (k=n) down to the sub-concat holding the leaf.
    # After descending through ops[0..d-1] we hold term(n-d).
    stop_level = target if target >= 1 else 1  # term level whose op adds the leaf
    d = 0
    while n - d > stop_level:
        op = ops[d]
        cur_level = n - d - 1  # the left operand we are extracting
        hname = f"h{tag}_{d}"
        t0 = term(leaves0, cur_level)
        t1 = term(leaves1, cur_level)
        r0 = leaves0[cur_level + 1]
        r1 = leaves1[cur_level + 1]
        lines.append(
            f"have {hname} : {t0} = {t1} "
            f"by rewrite -({left_ax(op)} {t0} {r0}) -({left_ax(op)} {t1} {r1}) {prev}."
        )
        prev = hname
        d += 1
    # Now ``prev`` proves term(stop_level)_0 = term(stop_level)_1, whose op is
    # ops[n - stop_level] = ops[n - target] and whose right operand is leaf target
    # (target >= 1) or whose left operand is leaf 0.
    leaf_h = f"h{tag}_leaf"
    op = ops[n - stop_level]
    base0 = term(leaves0, stop_level - 1)
    base1 = term(leaves1, stop_level - 1)
    if target >= 1:
        lines.append(
            f"have {leaf_h} : {leaves0[target]} = {leaves1[target]} "
            f"by rewrite -({right_ax(op)} {base0} {leaves0[target]}) "
            f"-({right_ax(op)} {base1} {leaves1[target]}) {prev}."
        )
    else:  # leaf 0 is the innermost LEFT operand
        lines.append(
            f"have {leaf_h} : {leaves0[0]} = {leaves1[0]} "
            f"by rewrite -({left_ax(op)} {leaves0[0]} {leaves0[1]}) "
            f"-({left_ax(op)} {leaves1[0]} {leaves1[1]}) {prev}."
        )
    return lines, leaf_h


# ---------------------------------------------------------------------------
# hop_0 tactic
# ---------------------------------------------------------------------------


@dataclass
class SingleRHopSpec:
    """Everything the single-R hop_0 tactic needs, derived from the game+reduction
    flat-state ASTs."""

    val_lemma_name: str
    game_glob_mods: list[str]  # val-lemma glob-binder order
    game_key_refs: list[str]  # the game DecapsKey field glob refs (SAMEKEY: 1)
    ct_params: list[str]  # ["ct0", "ct1"]
    red_base: str  # "R"
    red_glob_mods: list[str]  # reduction-prefix callee mods (subset of game mods)
    seed_fields: list[str]  # reduction seed fields, one per game key (SAMEKEY: 1)
    clone_alias: dict[str, str]
    h_module: str  # KDF module, "H"
    red_proc: ec_ast.Proc  # reduction challenge proc (with the trailing if)
    sync_mods: list[str]  # every module needing (glob M){1}=(glob M){2}
    # Which DISTINCT seed/key each ciphertext site decapsulates under. ``[0, 0]``
    # SAMEKEY; ``[0, 1]`` DIFFKEY.
    ct_seed_idx: list[int]
    # PK-binding (LEAK-BIND-K-PK) extras. Empty on the CT path (byte-identical).
    # ``guard_ek_refs`` = the reduction's own EncapsKey FIELD names (the guard
    # ``ek0 == ek1`` operands, one per seed); ``game_ek_refs`` = the game's
    # EncapsKey field glob-refs (the win term ``ek0 <> ek1``). When non-empty the
    # tactic cases on the reduction ek-guard, closes the ``ek0 == ek1`` branch via
    # the ek seams, and discharges the ``ek0 <> ek1`` branch by the redundancy
    # ``kdf0 = kdf1 => ek0 = ek1`` through the two EncodeEncapsKey KDF leaves.
    guard_ek_refs: list[str] = field(default_factory=list)
    game_ek_refs: list[str] = field(default_factory=list)


def _seed_env(
    prefix: list[ec_ast.EcStmt],
    base: dict[str, str],
    clone_alias: dict[str, str],
) -> dict[str, str]:
    """Forward walk over a reduction prefix building ``local -> ev-value``,
    seeded by ``base`` (the seed field + ct params bound to their glob refs or
    elim names)."""
    return walk_env(prefix, base, clone_alias)


def _ct_leaves(
    leaves: list[str], ct_param: str, clone_alias: dict[str, str]
) -> list[tuple[int, str, str, str]]:
    """Find the KDF leaves that encode a ciphertext component: the
    ``ev_encodeciphertext`` leaf (ct_PQ) and the ``ev_encode`` leaf whose argument
    references the ciphertext param (ct_T, vs the encaps-key ``ev_encode``).

    Returns ``[(leaf_idx, module, method, ct_projection_arg), ...]`` -- the
    injective encoding module/method (``<module>_<method>_inj`` is the axiom) and
    the inner ciphertext projection it yields (e.g. ``ct0{2}.\\`1``)."""
    out: list[tuple[int, str, str, str]] = []
    clone_to_mod = {c: m for m, c in clone_alias.items()}
    for idx, leaf in enumerate(leaves):
        e = leaf.strip()
        if not (e.startswith("(") and e.endswith(")")):
            continue
        head, _, arg = e[1:-1].strip().partition(" ")
        if ".ev_" not in head:
            continue
        clone, method = head.split(".ev_", 1)
        module = clone_to_mod.get(clone, clone)
        arg = arg.strip()
        is_encct = method == "encodeciphertext"
        is_ct_encode = method == "encode" and ct_param in arg
        if is_encct or is_ct_encode:
            out.append((idx, module, method, arg))
    return out


# The KDF leaf ops that serialize a component EncapsKey (the PK win term). A KEM
# component's public key is serialized by ``EncodeEncapsKey``; a nominal-group
# component's public key is a group element serialized by the group's ``Encode``.
# Both are declared ``injective`` in their primitive (KEM.primitive /
# NominalGroup.primitive), so both drive a faithful ``<M>_<m>_inj`` axiom, gated
# on the ``sig.injective`` modifier in the exporter -- and the leaf shape + the
# injectivity discharge are identical. The group ``Encode`` also serializes the
# component CIPHERTEXT (both are group elements), so an ``encode`` leaf is an
# encaps-key leaf only when its argument does NOT reference a ciphertext param
# (that split mirrors ``_ct_leaves``); ``encodeencapskey`` is unambiguous.
_EK_ENCODE_METHODS = ("encodeencapskey", "encode")


def ek_leaves(
    leaves: list[str], clone_alias: dict[str, str], ct_refs: tuple[str, ...] = ()
) -> list[tuple[int, str, str, str]]:
    """Find the KDF leaves that encode a component EncapsKey: the two encaps-key
    encoding leaves (``ev_encodeencapskey`` for a KEM component; the group
    ``ev_encode`` for a nominal-group component) -- the PK win term.

    ``ct_refs`` are the ciphertext-param reference strings in this leaf set's
    rendering (e.g. ``("ct0{2}", "ct1{2}")`` reduction-side, ``("C0", "C1")`` in
    the goal env); an ``ev_encode`` leaf whose argument references one is the
    component ciphertext encoding, not the encaps key, so it is excluded.

    Returns ``[(leaf_idx, module, method, ek_ev_arg), ...]`` where
    ``<module>_<method>_inj`` is the injectivity axiom and ``ek_ev_arg`` is the
    seed-derived encaps-key ev-form, which is exactly the component of the
    ek-derivation coupling."""
    out: list[tuple[int, str, str, str]] = []
    clone_to_mod = {c: m for m, c in clone_alias.items()}
    for idx, leaf in enumerate(leaves):
        e = leaf.strip()
        if not (e.startswith("(") and e.endswith(")")):
            continue
        head, _, arg = e[1:-1].strip().partition(" ")
        if ".ev_" not in head:
            continue
        clone, method = head.split(".ev_", 1)
        if method not in _EK_ENCODE_METHODS:
            continue
        arg = arg.strip()
        if method == "encode" and any(cr in arg for cr in ct_refs):
            continue
        module = clone_to_mod.get(clone, clone)
        out.append((idx, module, method, arg))
    return out


def single_r_hop0_tactic(
    spec: SingleRHopSpec,
) -> tuple[list[str], list[tuple[str, str]]] | None:
    """Emit the full ``hop_0_challenge`` tactic for the single-R direct-to-KDF
    shape, plus the ``(module, method)`` injectivity requests. ``None`` if the
    reduction body is not the expected ``if ct0=ct1`` split."""
    split = _prefix_and_if(spec.red_proc.body)
    if split is None:
        return None
    prefix, _red_if = split
    prefix = [s for s in prefix if not isinstance(s, ec_ast.VarDecl)]
    gmods = spec.game_glob_mods
    gge = _game_glob_elim(gmods)
    gargs = " ".join(gge)
    ct0, ct1 = spec.ct_params
    # Ciphertext-param references, used to exclude the component-ciphertext group
    # ``encode`` leaves from the encaps-key ones: reduction-side the KDF renders
    # ct params as ``ctN{2}``, the goal env as ``C0``/``C1`` (see below).
    red_ct_refs = (f"{ct0}" "{2}", f"{ct1}" "{2}")
    nkeys = len(spec.game_key_refs)
    seed_refs = [f"{spec.red_base}.{sf}" "{2}" for sf in spec.seed_fields]
    dkey = [f"D{i}" for i in range(nkeys)]
    i0, i1 = spec.ct_seed_idx

    # Reduction KDF ev-terms (side {2}), in terms of R.seedN{2} + ctN{2}.
    inv_env = _seed_env(
        prefix,
        {sf: seed_refs[j] for j, sf in enumerate(spec.seed_fields)}
        | {ct0: f"{ct0}" "{2}", ct1: f"{ct1}" "{2}"},
        spec.clone_alias,
    )
    if "kdf_in_0" not in inv_env or "kdf_in_1" not in inv_env:
        return None
    kdf_r0, kdf_r1 = inv_env["kdf_in_0"], inv_env["kdf_in_1"]
    kdf_rs = [kdf_r0, kdf_r1]
    is_pk = bool(spec.guard_ek_refs)
    # Shape gate: the KDF input must parse as a left-nested concat. CT binding
    # needs exactly two ciphertext-encoding leaves; PK binding needs exactly two
    # EncodeEncapsKey leaves (the win term).
    parsed0 = parse_left_nested_concat(kdf_r0)
    if parsed0 is None or parse_left_nested_concat(kdf_r1) is None:
        return None
    if is_pk:
        if len(ek_leaves(parsed0[1], spec.clone_alias, red_ct_refs)) != 2:
            return None
    elif len(_ct_leaves(parsed0[1], f"{ct0}" "{2}", spec.clone_alias)) != 2:
        return None

    # PK ek-derivation coupling (per seed): ``(R.ek_j, R.seed_j) = ((ek_PQ_ev,
    # ek_T_ev), R.seed_j)`` where the two ev-forms are the EncodeEncapsKey KDF-leaf
    # inners over R.seed_j -- exactly the coupling in the lemma pre
    # (``_self_keygen_multikey_coupling``), which the ``seq`` invariant must carry
    # (``seq`` forgets state not in its invariant). Also the game/reduction ek
    # SEAMS ``game.ek_j{1} = R.ek_j{2}``.
    ek_coupling_conj: list[str] = []
    ek_seam_conj: list[str] = []
    if is_pk:
        for j in range(nkeys):
            ks = [k for k in range(2) if spec.ct_seed_idx[k] == j]
            parsed_j = parse_left_nested_concat(kdf_rs[ks[0]]) if ks else None
            eklv = (
                ek_leaves(parsed_j[1], spec.clone_alias, red_ct_refs)
                if parsed_j
                else []
            )
            if len(eklv) != 2:
                return None
            pq_ev, t_ev = eklv[0][3], eklv[1][3]
            ek_ref = f"{spec.red_base}.{spec.guard_ek_refs[j]}" "{2}"
            ek_coupling_conj.append(
                f"({ek_ref}, {seed_refs[j]}) = (({pq_ev}, {t_ev}), {seed_refs[j]})"
            )
            ek_seam_conj.append(f"{spec.game_ek_refs[j]}" "{1}" f" = {ek_ref}")

    # -- game side: functionalize both decaps via the val-lemma (per-ct key) ----
    game_ex = (
        [f"(glob {m})" "{1}" for m in gmods]
        + [f"{r}" "{1}" for r in spec.game_key_refs]
        + [f"{ct0}" "{1}", f"{ct1}" "{1}"]
    )
    lines = [
        "proof.",
        "  proc.",
        f"  exists* {', '.join(game_ex)};",
        f"  elim* => {gargs} {' '.join(dkey)} C0 C1.",
        f"  call{{1}} ({spec.val_lemma_name} {gargs} {dkey[i1]} C1).",
        f"  call{{1}} ({spec.val_lemma_name} {gargs} {dkey[i0]} C0).",
    ]

    # -- invariant + reduction-prefix functionalization ------------------------
    glob_eqs = (
        [f"(glob {m})" "{1}" f" = {gge[i]}" for i, m in enumerate(gmods)]
        + [f"(glob {m})" "{2}" f" = {gge[i]}" for i, m in enumerate(gmods)]
        + [
            f"(glob {m})" "{1}" " = " f"(glob {m})" "{2}"
            for m in spec.sync_mods
            if m not in gmods
        ]
    )
    inv = " /\\ ".join(
        glob_eqs
        + [f"{dkey[j]} = {r}" "{1}" for j, r in enumerate(spec.game_key_refs)]
        + [f"{r}" "{1}" f" = {seed_refs[j]}" for j, r in enumerate(spec.game_key_refs)]
        + ek_seam_conj
        + ek_coupling_conj
        + [
            f"C0 = {ct0}" "{1}",
            f"C1 = {ct1}" "{1}",
            f"{ct0}" "{1}" f" = {ct0}" "{2}",
            f"{ct1}" "{1}" f" = {ct1}" "{2}",
            f"kdf_in_0" "{2}" f" = {kdf_r0}",
            f"kdf_in_1" "{2}" f" = {kdf_r1}",
        ]
    )
    lines.append(f"  seq 0 {len(prefix)} : ({inv}).")

    rge = [f"gr{i}" for i in range(len(spec.red_glob_mods))]
    glob_of = dict(zip(spec.red_glob_mods, rge))
    selim = [f"S{j}" for j in range(nkeys)]
    blk_env = _seed_env(
        prefix,
        {sf: selim[j] for j, sf in enumerate(spec.seed_fields)}
        | {ct0: "c0", ct1: "c1"},
        spec.clone_alias,
    )
    peel = _peel_stmts(prefix, blk_env, glob_of, "{2}")
    red_ex = (
        [f"(glob {m})" "{2}" for m in spec.red_glob_mods]
        + seed_refs
        + [f"{ct0}" "{2}", f"{ct1}" "{2}"]
    )
    # ``/>`` establishes the KDF-input equalities + globs + the per-key ``Dj =
    # Sj`` couplings (each game key is coupled to its seed in the lemma pre, for
    # any number of keys), closing the subgoal.
    lines += [
        "  + sp.",
        f"    exists* {', '.join(red_ex)};",
        f"    elim* => {' '.join(rge + selim)} c0 c1.",
        *[f"    {ln}" for ln in peel],
        "    skip => />.",
    ]

    # -- case on the reduction guard -------------------------------------------
    # CT: ``ct0 = ct1``; PK: the reduction's own ek fields ``ek0 = ek1``.
    if is_pk:
        guard = (
            f"{spec.red_base}.{spec.guard_ek_refs[0]}"
            "{2}"
            f" = {spec.red_base}.{spec.guard_ek_refs[1]}"
            "{2}"
        )
    else:
        guard = f"{ct0}" "{2}" f" = {ct1}" "{2}"
    lines.append(f"  case ({guard}).")
    # then: R returns false; the game predicate is false too. CT: ct0{1}=ct1{1}
    # via the ct couplings + branch guard. PK: game.ek0{1}=game.ek1{1} via the ek
    # seams + branch guard (the win term ``ek0<>ek1`` is then false), so ``smt``
    # closes it after ``/>`` collapses the memories.
    if is_pk:
        lines += [
            "  + rcondt{2} 1; first by auto.",
            "    wp. skip => />.",
        ]
    else:
        lines += [
            "  + rcondt{2} 1; first by auto.",
            "    wp. skip => />.",
        ]
    # else: R forwards to the KDF Breakable challenger (H(x0)=H(x1) && x0<>x1).
    # After ``skip => />`` the couplings collapse both sides' KDF inputs to the
    # SAME terms over the game elims ``D_j``/``C0``/``C1``. CT: the residual is
    # ``C0<>C1 => (ev K0 = ev K1) = ((ev K0 = ev K1) && K0<>K1)``. PK: the game's
    # win term is ``ek0<>ek1``, which the ek-derivation coupling has rewritten to
    # ``(ek_PQ_ev0, ek_T_ev0) <> (ek_PQ_ev1, ek_T_ev1)`` -- the extra ``K0<>K1``
    # conjunct is redundant because ``K0=K1`` forces both EncodeEncapsKey leaves
    # equal, hence both ek ev-forms equal.
    hm = spec.h_module
    goal_env = _seed_env(
        prefix,
        {sf: dkey[j] for j, sf in enumerate(spec.seed_fields)} | {ct0: "C0", ct1: "C1"},
        spec.clone_alias,
    )
    gparse0 = parse_left_nested_concat(goal_env.get("kdf_in_0", ""))
    gparse1 = parse_left_nested_concat(goal_env.get("kdf_in_1", ""))
    if gparse0 is None or gparse1 is None:
        return None
    gops, gleaves0 = gparse0
    _gops1, gleaves1 = gparse1
    if is_pk:
        goal_ct_refs = ("C0", "C1")
        gkey_leaves0 = ek_leaves(gleaves0, spec.clone_alias, goal_ct_refs)
        gkey_leaves1 = ek_leaves(gleaves1, spec.clone_alias, goal_ct_refs)
    else:
        gkey_leaves0 = _ct_leaves(gleaves0, "C0", spec.clone_alias)
        gkey_leaves1 = _ct_leaves(gleaves1, "C1", spec.clone_alias)
    if len(gkey_leaves0) != 2 or len(gkey_leaves1) != 2:
        return None
    lines += [
        "  rcondf{2} 1; first by (auto; smt()).",
        "  inline{2} 1.",
        "  sp.",
        *kdf_freeze_and_evaluate(hm, "{2}", ("gh2", "ki0", "ki1")),
        "  skip => />. move => hne.",
    ]
    inj_reqs: list[tuple[str, str]] = []
    if is_pk:
        # PK redundancy: ``kdf0 = kdf1 => (ek_PQ_ev0 = ek_PQ_ev1 /\ ek_T_ev0 =
        # ek_T_ev1)`` -- the conjunction the coupling-rewritten win term ``hne``
        # negates. Each conjunct comes from an EncodeEncapsKey leaf + inj.
        concl = " /\\ ".join(
            f"{gkey_leaves0[i][3]} = {gkey_leaves1[i][3]}" for i in range(2)
        )
        lines.append(
            f"  have hkek : {goal_env['kdf_in_0']} = {goal_env['kdf_in_1']} "
            f"=> ({concl})."
        )
        lines.append("  + move => h.")
        for i in range(2):
            idx, module, method, inner0 = gkey_leaves0[i]
            inner1 = gkey_leaves1[i][3]
            peel_lines, leaf_h = slice_to_leaf(
                gops, gleaves0, gleaves1, idx, "h", f"ek{i}"
            )
            lines += [f"    {ln}" for ln in peel_lines]
            lines.append(
                f"    have hekeq{i} : {inner0} = {inner1} "
                f"by apply ({module}_{method}_inj _ _ {leaf_h})."
            )
            inj_reqs.append((module, method))
        lines.append("    smt().")
        lines.append("  smt().")
        lines.append("  qed.")
        return lines, inj_reqs
    # CT redundancy: K0 = K1 forces C0 = C1 (both ct components are bound in the
    # KDF input), so with the guard C0 <> C1 the extra K0 <> K1 conjunct is true.
    lines.append(
        f"  have hkct : {goal_env['kdf_in_0']} = {goal_env['kdf_in_1']} => C0 = C1."
    )
    lines.append("  + move => h.")
    for i, (idx, module, method, proj) in enumerate(gkey_leaves0):
        peel_lines, leaf_h = slice_to_leaf(gops, gleaves0, gleaves1, idx, "h", f"c{i}")
        lines += [f"    {ln}" for ln in peel_lines]
        proj1 = proj.replace("C0", "C1")
        lines.append(
            f"    have hcteq{i} : {proj} = {proj1} "
            f"by apply ({module}_{method}_inj _ _ {leaf_h})."
        )
        inj_reqs.append((module, method))
    lines.append("    smt().")
    lines.append("  smt().")
    lines.append("  qed.")
    return lines, inj_reqs
