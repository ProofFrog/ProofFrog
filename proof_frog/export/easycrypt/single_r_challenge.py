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

from __future__ import annotations

from dataclasses import dataclass

from . import ec_ast
from .binding_challenge import (
    _game_glob_elim,
    _paren,
    _peel_stmts,
    _prefix_and_if,
    _split_top_args,
    _subst,
)


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


def slice_to_leaf(
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


def _seed_env(
    prefix: list[ec_ast.EcStmt],
    base: dict[str, str],
    clone_alias: dict[str, str],
) -> dict[str, str]:
    """Forward walk over a reduction prefix building ``local -> ev-value``,
    seeded by ``base`` (the seed field + ct params bound to their glob refs or
    elim names)."""
    env = dict(base)
    for stmt in prefix:
        if isinstance(stmt, ec_ast.Assign):
            env[stmt.var] = _subst(stmt.rhs, env)
        elif isinstance(stmt, ec_ast.Call):
            module, _, method = stmt.callee.partition(".")
            args = [_subst(a, env) for a in _split_top_args(stmt.args)]
            ev = f"{clone_alias[module]}.ev_{method}"
            applied = "".join(f" {_paren(a)}" for a in args)
            env[stmt.var] = f"({ev}{applied})"
    return env


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
    # Shape gate: the KDF input must parse as a left-nested concat with exactly
    # two ciphertext-encoding leaves (the redundancy itself uses the game-elim
    # form below).
    parsed0 = parse_left_nested_concat(kdf_r0)
    if parsed0 is None or parse_left_nested_concat(kdf_r1) is None:
        return None
    if len(_ct_leaves(parsed0[1], f"{ct0}" "{2}", spec.clone_alias)) != 2:
        return None

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

    # -- case on the reduction guard ``ct0 = ct1`` -----------------------------
    lines.append(f"  case ({ct0}" "{2}" f" = {ct1}" "{2}).")
    # then: R returns false; the game predicate is false too (ct0{1}=ct1{1}
    # follows from the ct couplings + the branch guard, so ``/>`` closes it).
    lines += [
        "  + rcondt{2} 1; first by auto.",
        "    wp. skip => />.",
    ]
    # else: R forwards to the KDF Breakable challenger (H(x0)=H(x1) && x0<>x1).
    # After ``skip => />`` the coupling ``D0 = seed0{2}`` + ``C_i = ct_i`` collapse
    # both sides' KDF inputs to the SAME terms over the game elims ``D0``/``C0``/
    # ``C1``, and the branch guard simplifies the game's ``ct0<>ct1`` to true; the
    # residual is ``C0<>C1 => (ev K0 = ev K1) = ((ev K0 = ev K1) && K0<>K1)``.
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
    gct_leaves = _ct_leaves(gleaves0, "C0", spec.clone_alias)
    if len(gct_leaves) != 2:
        return None
    lines += [
        "  rcondf{2} 1; first by (auto; smt()).",
        "  inline{2} 1.",
        "  sp.",
        f"  exists* (glob {hm})"
        "{2}"
        ", kdf_in_0"
        "{2}"
        ", kdf_in_1"
        "{2}"
        "; elim* => gh2 ki0 ki1.",
        "  wp.",
        f"  call{{2}} ({hm}_evaluate_det gh2 ki1).",
        f"  call{{2}} ({hm}_evaluate_det gh2 ki0).",
        "  skip => />. move => hne.",
    ]
    # redundancy: K0 = K1 forces C0 = C1 (both ct components are bound in the KDF
    # input), so with the guard C0 <> C1 the extra K0 <> K1 conjunct is true.
    lines.append(
        f"  have hkct : {goal_env['kdf_in_0']} = {goal_env['kdf_in_1']} => C0 = C1."
    )
    lines.append("  + move => h.")
    inj_reqs: list[tuple[str, str]] = []
    for i, (idx, module, method, proj) in enumerate(gct_leaves):
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
