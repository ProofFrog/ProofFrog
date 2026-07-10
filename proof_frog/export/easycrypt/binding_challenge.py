"""Synthesizer for the CFRG binding *challenge* case-split hop.

Relates a KEM binding GAME's ``Challenge`` (two ``decaps`` calls + a boolean
compare) to the ``R_PQ_Bind`` reduction's ``Challenge`` -- a case-split that,
when the two KDF inputs collide and the PQ ciphertexts differ, forwards to the
inner KEM binding challenger, and otherwise recomputes the game's boolean. The
two are equivalent because the collision branch's precondition, via encoding
*injectivity*, forces the two component decapsulations to agree exactly when the
game's ``H``-comparison holds.

The closing tactic functionalizes every deterministic call to its ``ev_<m>``
form (the exporter's ``<M>_<m>_det`` axioms), couples the game's packed decaps
key to the reduction's decomposed component fields, splits on the reduction's
guard, and on the collision branch peels the KDF-input concatenation with the
``slice_concat_left_*`` round-trip axioms + the ``<M>_<m>_inj`` injectivity
axiom.

Validated end-to-end on ``CK_expanded_LEAK_BIND_K_CT`` hop 0 (see the tripwire
``tests/integration/ec_templates/binding_challenge_2kem_packed.ec`` and the plan
``2026-07-08-easycrypt-export-cfrg-binding.md``). This module holds the pure
code-gen; ``chain_emitter`` calls :func:`challenge_casesplit_route` and the
exporter calls :func:`decaps_val_lemma`.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from . import ec_ast

# ---------------------------------------------------------------------------
# Symbolic evaluation of a linear (deterministic) proc body into functional
# values.  Each ``x <@ M.m(a..)`` becomes ``x = <clone(M)>.ev_m <a..>``; each
# ``x <- e`` substitutes prior functional values into ``e``; projections and
# concatenations pass through as raw expression strings.
# ---------------------------------------------------------------------------


@dataclass
class _Call:
    """One deterministic call site, back-to-front peel data."""

    module: str  # "KEM_PQ"
    method: str  # "decaps"
    arg_values: list[str]  # functional-value args, e.g. ["dkv.`1", "ctv.`1"]


@dataclass
class DecapsModel:
    """Functional model of a scheme's ``decaps`` (or a reduction's inline KDF
    recomputation): the ordered call sites and the closed functional value of
    the result, both expressed over renamed formal parameters."""

    calls: list[_Call]  # program order
    result: str  # closed functional value of the returned expression
    glob_modules: list[str]  # distinct callee modules, first-appearance order


def _subst(expr: str, env: dict[str, str]) -> str:
    """Single-pass whole-word substitution of ``env`` keys in ``expr``.

    Keys are matched longest-first at word boundaries; a key never appears
    inside its own replacement in a way that would double-substitute because
    every referenced name is already fully resolved (the body is in SSA-ish
    order), so one pass suffices.
    """
    if not env:
        return expr
    keys = sorted(env, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b")
    return pattern.sub(lambda m: env[m.group(1)], expr)


def _split_top_args(args: str) -> list[str]:
    """Split a rendered ``args`` string on top-level commas (nesting-aware)."""
    out: list[str] = []
    depth = 0
    cur = ""
    for ch in args:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def model_from_proc(
    proc: ec_ast.Proc,
    param_rename: dict[str, str],
    clone_alias: dict[str, str],
) -> DecapsModel | None:
    """Build a :class:`DecapsModel` from a linear deterministic proc body.

    ``param_rename`` maps the proc's formal parameter names to the lemma-level
    universally-quantified names (``dk`` -> ``dkv``). ``clone_alias`` maps a
    callee module name to its EC clone prefix (``KEM_PQ`` -> ``KEM_PQ_c``), the
    namespace of its ``ev_<m>`` ops. Returns ``None`` if the body contains a
    construct this model does not handle (a sample, a branch, an unknown clone).
    """
    env: dict[str, str] = dict(param_rename)
    calls: list[_Call] = []
    glob_modules: list[str] = []
    result: str | None = None
    for stmt in proc.body:
        if isinstance(stmt, ec_ast.VarDecl):
            continue
        if isinstance(stmt, ec_ast.Assign):
            env[stmt.var] = _subst(stmt.rhs, env)
        elif isinstance(stmt, ec_ast.Call):
            module, _, method = stmt.callee.partition(".")
            if not method or module not in clone_alias:
                return None
            arg_values = [_subst(a, env) for a in _split_top_args(stmt.args)]
            calls.append(_Call(module, method, arg_values))
            if module not in glob_modules:
                glob_modules.append(module)
            ev = f"{clone_alias[module]}.ev_{method}"
            applied = "".join(f" {_paren(a)}" for a in arg_values)
            env[stmt.var] = f"({ev}{applied})"
        elif isinstance(stmt, ec_ast.Return):
            result = _subst(stmt.expr, env)
        else:  # Sample / If -- not a linear deterministic body
            return None
    if result is None:
        return None
    return DecapsModel(calls, result, glob_modules)


def _paren(expr: str) -> str:
    """Wrap ``expr`` in parens for use as a space-separated op argument."""
    e = expr.strip()
    if e.startswith("(") and e.endswith(")"):
        return e
    return f"({e})" if " " in e else e


# ---------------------------------------------------------------------------
# The ``<Scheme>_decaps_val`` phoare lemma: ``decaps`` returns its functional
# value with probability 1, proved by peeling each det call back-to-front with
# the corresponding ``<M>_<m>_det`` axiom.
# ---------------------------------------------------------------------------


def _glob_var(module: str) -> str:
    """Deterministic per-module glob binder name (``KEM_PQ`` -> ``g_KEM_PQ``)."""
    return f"g_{module}"


def _build_env(
    proc: ec_ast.Proc,
    param_rename: dict[str, str],
    clone_alias: dict[str, str],
) -> dict[str, str]:
    """Forward walk building ``var -> functional value`` (SSA-ish, stable)."""
    env: dict[str, str] = dict(param_rename)
    for stmt in proc.body:
        if isinstance(stmt, ec_ast.Assign):
            env[stmt.var] = _subst(stmt.rhs, env)
        elif isinstance(stmt, ec_ast.Call):
            module, _, method = stmt.callee.partition(".")
            args = [_subst(a, env) for a in _split_top_args(stmt.args)]
            ev = f"{clone_alias[module]}.ev_{method}"
            applied = "".join(f" {_paren(a)}" for a in args)
            env[stmt.var] = f"({ev}{applied})"
    return env


def _peel_stmts(
    stmts: Sequence[ec_ast.EcStmt],
    env: dict[str, str],
    glob_of: dict[str, str],
    side: str = "",
) -> list[str]:
    """Reverse-walk ``stmts`` emitting one ``call{side} (<M>_<m>_det g <args>)``
    per call and a single ``wp.`` per contiguous assignment run (no ``proc.`` /
    ``skip`` framing). ``env`` gives each local's functional value so a call
    argument functionalizes by substituting the original argument through it.
    """
    lines: list[str] = []
    pending_wp = False
    for stmt in reversed(stmts):
        if isinstance(stmt, (ec_ast.Return, ec_ast.VarDecl)):
            continue
        if isinstance(stmt, ec_ast.Assign):
            pending_wp = True
            continue
        assert isinstance(stmt, ec_ast.Call)
        if pending_wp:
            lines.append("wp.")
            pending_wp = False
        module, _, method = stmt.callee.partition(".")
        args = [_paren(_subst(a, env)) for a in _split_top_args(stmt.args)]
        applied = "".join(f" {a}" for a in args)
        lines.append(f"call{side} ({module}_{method}_det {glob_of[module]}{applied}).")
    if pending_wp:
        lines.append("wp.")
    return lines


def _peel_proof(
    proc: ec_ast.Proc,
    env: dict[str, str],
    glob_of: dict[str, str],
) -> list[str]:
    """Full ``<Scheme>_decaps_val`` peel proof: ``proc.`` + :func:`_peel_stmts`
    + ``skip => />.``.
    """
    stmts = [s for s in proc.body if not isinstance(s, ec_ast.VarDecl)]
    lines = ["proc.", *_peel_stmts(stmts, env, glob_of)]
    lines.append("skip => />.")
    return lines


def decaps_val_lemma(
    lemma_name: str,
    scheme_expr: str,
    decaps_proc: ec_ast.Proc,
    clone_alias: dict[str, str],
) -> tuple[list[str], DecapsModel] | None:
    """Synthesize the ``<Scheme>_decaps_val`` phoare lemma text.

    Returns ``(lemma_lines, model)`` -- ``model`` lets the caller (the tactic
    synthesizer) reuse the same functional structure. ``None`` if the decaps
    body is not a linear deterministic sequence this synthesizer handles.

    ``scheme_expr`` is the concrete scheme module application the lemma is
    stated over (``CK_expanded(KEM_PQ, KEM_T, G, H, L)``); ``clone_alias`` maps
    each callee module to its ``ev_<m>`` clone prefix.
    """
    if len(decaps_proc.params) != 2:
        return None
    param_rename = {p.name: f"{p.name}v" for p in decaps_proc.params}
    env = _build_env(decaps_proc, param_rename, clone_alias)
    model = model_from_proc(decaps_proc, param_rename, clone_alias)
    if model is None:
        return None
    glob_of = {m: _glob_var(m) for m in model.glob_modules}
    glob_eqs = [f"(glob {m}) = {glob_of[m]}" for m in model.glob_modules]
    glob_binders = [f"({glob_of[m]} : (glob {m}))" for m in model.glob_modules]
    key_binders = [
        f"({param_rename[p.name]} : {p.type.text})" for p in decaps_proc.params
    ]
    pre_arg_eqs = [f"{p.name} = {param_rename[p.name]}" for p in decaps_proc.params]
    pre = " /\\ ".join(glob_eqs + pre_arg_eqs)
    post = " /\\ ".join(glob_eqs + [f"res = {model.result}"])
    proof = _peel_proof(decaps_proc, env, glob_of)
    lines = [
        f"  lemma {lemma_name} {' '.join(glob_binders + key_binders)} :",
        f"    phoare[ {scheme_expr}.{decaps_proc.name} :",
        f"      {pre}",
        f"      ==> {post} ] = 1%r.",
        "  proof.",
        *[f"    {ln}" for ln in proof],
        "  qed.",
    ]
    return lines, model


# ---------------------------------------------------------------------------
# The KDF-input concatenation shape.  For the CFRG two-KEM combiners the KDF
# input is the left-nested concat
#   concatN( ... concat2( concat1( E_pq(ss_pq), E_t(ss_t) ), Ect(ct_t) ), Eek(ek_t) ), label )
# built from the (two-KEM) component encodings.  ``ConcatShape`` records the
# ordered concat op names (outer-first) + the ``ev`` component ops so both the
# collision-branch slice-peel and the KDF-input invariant term can be rebuilt
# with any key/ciphertext bindings.
# ---------------------------------------------------------------------------


@dataclass
class ConcatShape:
    """Two-KEM KDF-input concatenation, reconstructable at any bindings."""

    concat_ops: list[str]  # outer-first: [cL4, cL3, cL2, cL1]
    ev_decaps_pq: str  # e.g. "KEM_PQ_c.ev_decaps"
    ev_encss_pq: str
    ev_decaps_t: str
    ev_encss_t: str
    ev_encct_t: str
    ev_encek_t: str
    ev_label: str  # e.g. "L_c.ev_get"

    def slice_axioms(self) -> list[str]:
        """``slice_concat_left_*`` round-trip axiom names, outer-first."""
        return [
            "slice_concat_left_" + op[len("concat_") :].replace("_to_", "_", 1)
            for op in self.concat_ops
        ]

    def right_slice_axioms(self) -> list[str]:
        """``slice_concat_right_*`` round-trip axiom names, outer-first."""
        return [
            "slice_concat_right_" + op[len("concat_") :].replace("_to_", "_", 1)
            for op in self.concat_ops
        ]

    def leaves(self, pq_key: str, t_key: str, ek: str, ct: str) -> tuple[str, ...]:
        """Return ``(pq, t, b_ct, b_ek, b_label, L1, L2, L3)`` at these bindings."""
        pq = f"({self.ev_encss_pq} ({self.ev_decaps_pq} {pq_key} {ct}.`1))"
        t = f"({self.ev_encss_t} ({self.ev_decaps_t} {t_key} {ct}.`2))"
        b_ct = f"({self.ev_encct_t} {ct}.`2)"
        b_ek = f"({self.ev_encek_t} {ek})"
        b_label = self.ev_label
        _cl4, cl3, cl2, cl1 = self.concat_ops
        lvl1 = f"({cl1} {pq} {t})"
        lvl2 = f"({cl2} {lvl1} {b_ct})"
        lvl3 = f"({cl3} {lvl2} {b_ek})"
        return pq, t, b_ct, b_ek, b_label, lvl1, lvl2, lvl3

    def kdf_in(self, pq_key: str, t_key: str, ek: str, ct: str) -> str:
        """The full KDF input concat term at these bindings."""
        _pq, _t, _bc, _be, b_label, _l1, _l2, lvl3 = self.leaves(pq_key, t_key, ek, ct)
        return f"({self.concat_ops[0]} {lvl3} {b_label})"


def slice_peel(
    shape: ConcatShape,
    bind0: tuple[str, str, str, str],
    bind1: tuple[str, str, str, str],
) -> list[str]:
    """Emit the four ``have hc*/he`` slice-peel steps deriving the innermost
    PQ-encoding equality from the KDF-input equality ``h``.

    ``bind_i = (pq_key_i, t_key_i, ek_i, ct_i)``. Each level peels one concat
    with its ``slice_concat_left`` axiom applied to both sides then rewrites the
    previous level's equality.
    """
    sa4, sa3, sa2, sa1 = shape.slice_axioms()
    p0, t0, _bc0, _be0, b40, l1_0, l2_0, l3_0 = shape.leaves(*bind0)
    p1, t1, _bc1, _be1, b41, l1_1, l2_1, l3_1 = shape.leaves(*bind1)
    return [
        f"have hc3 : {l3_0} = {l3_1} by rewrite -({sa4} {l3_0} {b40}) -({sa4} {l3_1} {b41}) h.",
        f"have hc2 : {l2_0} = {l2_1} by rewrite -({sa3} {l2_0} {_be0}) -({sa3} {l2_1} {_be1}) hc3.",
        f"have hc1 : {l1_0} = {l1_1} by rewrite -({sa2} {l1_0} {_bc0}) -({sa2} {l1_1} {_bc1}) hc2.",
        f"have he : {p0} = {p1} by rewrite -({sa1} {p0} {t0}) -({sa1} {p1} {t1}) hc1.",
    ]


def slice_peel_to_ect(
    shape: ConcatShape,
    bind0: tuple[str, str, str, str],
    bind1: tuple[str, str, str, str],
) -> list[str]:
    """Emit the three ``have hc3/hc2/hect`` steps deriving the encodeciphertext-
    component equality (``ev_encct ct0 = ev_encct ct1``) from a KDF-input equality
    hypothesis ``h``. Navigates two ``slice_concat_left`` levels (the c4 label and
    c3 encapskey concats) then one ``slice_concat_right`` (the c2 ciphertext
    concat, whose RIGHT component is the encodeciphertext leaf)."""
    sa4, sa3, _sa2, _sa1 = shape.slice_axioms()
    sr2 = shape.right_slice_axioms()[2]
    _p0, _t0, bc0, be0, bl0, l1_0, l2_0, l3_0 = shape.leaves(*bind0)
    _p1, _t1, bc1, be1, bl1, l1_1, l2_1, l3_1 = shape.leaves(*bind1)
    return [
        f"have hc3 : {l3_0} = {l3_1} by rewrite -({sa4} {l3_0} {bl0}) -({sa4} {l3_1} {bl1}) h.",
        f"have hc2 : {l2_0} = {l2_1} by rewrite -({sa3} {l2_0} {be0}) -({sa3} {l2_1} {be1}) hc3.",
        f"have hect : {bc0} = {bc1} by rewrite -({sr2} {l1_0} {bc0}) -({sr2} {l1_1} {bc1}) hc2.",
    ]


def slice_peel_to_eek(
    shape: ConcatShape,
    bind0: tuple[str, str, str, str],
    bind1: tuple[str, str, str, str],
) -> list[str]:
    """Emit the two ``have hc3/heek`` steps deriving the encodeencapskey-component
    equality (``ev_encek ek0 = ev_encek ek1``) from a KDF-input equality
    hypothesis ``h``. Navigates one ``slice_concat_left`` level (the c4 label
    concat) then one ``slice_concat_right`` (the c3 encapskey concat, whose RIGHT
    component is the encodeencapskey leaf)."""
    sa4, _sa3, _sa2, _sa1 = shape.slice_axioms()
    sr3 = shape.right_slice_axioms()[1]
    _p0, _t0, _bc0, be0, bl0, _l1_0, l2_0, l3_0 = shape.leaves(*bind0)
    _p1, _t1, _bc1, be1, bl1, _l1_1, l2_1, l3_1 = shape.leaves(*bind1)
    return [
        f"have hg3 : {l3_0} = {l3_1} by rewrite -({sa4} {l3_0} {bl0}) -({sa4} {l3_1} {bl1}) h.",
        f"have heek : {be0} = {be1} by rewrite -({sr3} {l2_0} {be0}) -({sr3} {l2_1} {be1}) hg3.",
    ]


# ---------------------------------------------------------------------------
# The whole hop_<i>_challenge tactic.
# ---------------------------------------------------------------------------


@dataclass
class ChallengeHopSpec:
    """Everything the challenge-elimination tactic needs, derived from the hop's
    game/reduction ASTs and its decomposition coupling."""

    val_lemma_name: str
    game_glob_mods: list[str]  # model.glob_modules, e.g. [KEM_PQ, KEM_T, L, H]
    game_key_refs: list[str]  # 2 packed-key glob refs (no side annotation)
    ct_params: list[str]  # ["ct0", "ct1"]
    red_base: str  # "R_PQ_Bind"
    red_glob_mods: list[str]  # reduction-prefix globs, e.g. [KEM_PQ, KEM_T, L]
    red_component_fields: list[list[str]]  # [[dk_PQ_0,dk_T_0,ek_T_0], [...1]]
    clone_alias: dict[str, str]
    decomp_coupling: list[str]  # game packed key = tuple of reduction fields
    challenger_coupling: list[str]  # reduction PQ field = challenger key
    extra_glob_sync_mods: list[str]  # modules needing (glob X){1}=(glob X){2}
    challenger_ref: str  # "KEM_PQ_c.LEAK_BIND_K_CT_Breakable"
    challenger_key_fields: list[str]  # ["dk0", "dk1"]
    pq_module: str  # "KEM_PQ"
    inj_axiom: str  # "KEM_PQ_encodesharedsecret_inj"
    h_module: str  # KDF module for the else-branch, "H"
    shape: ConcatShape
    red_proc: ec_ast.Proc  # reduction challenge proc
    # -- PK-shape extras (encaps-key binding); all empty/False for CT ----------
    win_is_ek: bool = False  # win term is the packed encaps key, not the ct params
    ek_component_fields: list[list[str]] = field(
        default_factory=list
    )  # [[ek_PQ_0, ek_T_0], [ek_PQ_1, ek_T_1]]
    ek_inj_axiom: str = ""  # "<T>_encodeencapskey_inj"
    challenger_ek_fields: list[str] = field(
        default_factory=list
    )  # challenger's encaps-key field names ["ek0", "ek1"]


def _game_glob_elim(mods: list[str]) -> list[str]:
    """Fresh side-1 glob elim names, e.g. [KEM_PQ,KEM_T,L,H] -> [gg0..gg3]."""
    return [f"gg{i}" for i in range(len(mods))]


def _prefix_and_if(
    body: list[ec_ast.EcStmt],
) -> tuple[list[ec_ast.EcStmt], ec_ast.If] | None:
    """Split a challenge body into its statement prefix and its trailing ``if``."""
    prefix: list[ec_ast.EcStmt] = []
    for stmt in body:
        if isinstance(stmt, ec_ast.If):
            return prefix, stmt
        prefix.append(stmt)
    return None


def challenge_tactic(spec: ChallengeHopSpec) -> list[str] | None:
    """Emit the full ``hop_<i>_challenge`` outer tactic body (``proof.`` ..
    ``qed.``). ``None`` if the reduction body is not the expected case-split."""
    split = _prefix_and_if(spec.red_proc.body)
    if split is None:
        return None
    prefix, _if = split
    # ``var`` declarations are not executable statements -- EC's ``seq`` index
    # and ``sp`` count only the assignments/calls, so drop the decls.
    prefix = [s for s in prefix if not isinstance(s, ec_ast.VarDecl)]
    gmods = spec.game_glob_mods
    gge = _game_glob_elim(gmods)  # game glob elim names
    ct0, ct1 = spec.ct_params

    # -- game side: exists* globs + packed keys + cts, functionalize decaps ----
    game_ex = (
        [f"(glob {m})" "{1}" for m in gmods]
        + [f"{r}" "{1}" for r in spec.game_key_refs]
        + [f"{c}" "{1}" for c in spec.ct_params]
    )
    game_elim = gge + ["D0", "D1", "C0", "C1"]
    gargs = " ".join(gge)
    lines = [
        "proof.",
        "  proc.",
        f"  exists* {', '.join(game_ex)};",
        f"  elim* => {' '.join(game_elim)}.",
        f"  call{{1}} ({spec.val_lemma_name} {gargs} D1 C1).",
        f"  call{{1}} ({spec.val_lemma_name} {gargs} D0 C0).",
    ]

    # -- invariant -------------------------------------------------------------
    inv_env = _red_env(spec, rename="inv")
    inv_kdf = [
        f"kdf_in_0" "{2}" f" = {inv_env['kdf_in_0']}",
        f"kdf_in_1" "{2}" f" = {inv_env['kdf_in_1']}",
    ]
    glob_eqs = (
        [f"(glob {m})" "{1}" f" = {gge[i]}" for i, m in enumerate(gmods)]
        + [f"(glob {m})" "{2}" f" = {gge[i]}" for i, m in enumerate(gmods)]
        + [
            f"(glob {m})" "{1}" " = " f"(glob {m})" "{2}"
            for m in spec.extra_glob_sync_mods
        ]
    )
    key_ct_eqs = (
        [f"D{i} = {r}" "{1}" for i, r in enumerate(spec.game_key_refs)]
        + [f"C{i} = {c}" "{1}" for i, c in enumerate(spec.ct_params)]
        + [f"{c}" "{1}" f" = {c}" "{2}" for c in spec.ct_params]
    )
    inv = " /\\ ".join(
        glob_eqs
        + spec.decomp_coupling
        + spec.challenger_coupling
        + key_ct_eqs
        + inv_kdf
    )
    lines.append(f"  seq 0 {len(prefix)} : ({inv}).")

    # -- first subgoal: functionalize the reduction prefix ---------------------
    rge = [f"g{i}2" for i in range(len(spec.red_glob_mods))]  # reduction glob elim
    field_elim = _field_elim_names(spec.red_component_fields)
    red_ex = (
        [f"(glob {m})" "{2}" for m in spec.red_glob_mods]
        + [
            f"{spec.red_base}.{f}" "{2}"
            for grp in spec.red_component_fields
            for f in grp
        ]
        + [f"{c}" "{2}" for c in spec.ct_params]
    )
    blk_env = _red_env(spec, rename="blk", field_elim=field_elim)
    glob_of_blk = dict(zip(spec.red_glob_mods, rge))
    peel_stmts = _drop_leading_assigns(prefix)
    lines += [
        "  + sp.",
        f"    exists* {', '.join(red_ex)};",
        f"    elim* => {' '.join(rge + field_elim + ['c0', 'c1'])}.",
        *[f"    {ln}" for ln in _peel_stmts(peel_stmts, blk_env, glob_of_blk, "{2}")],
        "    skip => />.",
    ]

    # -- case split ------------------------------------------------------------
    # CT reduction guards ``kdf_in_0 = kdf_in_1 && ct_PQ_0 <> ct_PQ_1``; PK
    # guards on the KDF-input collision alone (the PK challenger checks the PQ
    # encaps-key distinctness itself).
    if spec.win_is_ek:
        guard = "kdf_in_0{2} = kdf_in_1{2}"
    else:
        guard = (
            "kdf_in_0"
            "{2}"
            " = kdf_in_1"
            "{2}"
            f" /\\ {ct0}"
            "{2}"
            ".`1 <> "
            f"{ct1}"
            "{2}"
            ".`1"
        )
    lines.append(f"  case ({guard}).")
    if spec.win_is_ek:
        lines += _if_branch_pk(spec)
        lines += _else_branch_pk(spec)
    else:
        lines += _if_branch(spec)
        lines += _else_branch(spec)
    lines.append("  qed.")
    return lines


def _field_elim_names(groups: list[list[str]]) -> list[str]:
    """Per-index reduction-field elim names: ``[[..0], [..1]]`` -> ``[dp0, dt0,
    ek0, dp1, dt1, ek1]``."""
    out: list[str] = []
    for i, _ in enumerate(groups):
        out += [f"dp{i}", f"dt{i}", f"ek{i}"]
    return out


def _drop_leading_assigns(stmts: list[ec_ast.EcStmt]) -> list[ec_ast.EcStmt]:
    """Drop the leading assignment run (the ciphertext projections ``sp`` peels
    before the reduction-prefix functionalization)."""
    i = 0
    while i < len(stmts) and isinstance(stmts[i], ec_ast.Assign):
        i += 1
    return stmts[i:]


def _red_env(
    spec: ChallengeHopSpec,
    rename: str,
    field_elim: list[str] | None = None,
) -> dict[str, str]:
    """Functional env of the reduction-challenge prefix under a rename.

    ``rename == "inv"`` expresses fields/ct as their side-2 glob refs
    (``R.dk_PQ_0{2}``, ``ct0{2}``) for the seq invariant; ``rename == "blk"``
    expresses them as the ``exists*`` elim names (``dp0``, ``c0``) for the
    prefix peel.
    """
    clone = spec.clone_alias
    base: dict[str, str] = {}
    if rename == "inv":
        for grp in spec.red_component_fields:
            for fld in grp:
                base[fld] = f"{spec.red_base}.{fld}" "{2}"
        for c in spec.ct_params:
            base[c] = f"{c}" "{2}"
    else:  # "blk"
        felim = field_elim or _field_elim_names(spec.red_component_fields)
        flat = [f for grp in spec.red_component_fields for f in grp]
        base = dict(zip(flat, felim))
        base[spec.ct_params[0]] = "c0"
        base[spec.ct_params[1]] = "c1"
    env = dict(base)
    for stmt in spec.red_proc.body:
        if isinstance(stmt, ec_ast.If):
            break
        if isinstance(stmt, ec_ast.Assign):
            env[stmt.var] = _subst(stmt.rhs, env)
        elif isinstance(stmt, ec_ast.Call):
            module, _, method = stmt.callee.partition(".")
            args = [_subst(a, env) for a in _split_top_args(stmt.args)]
            ev = f"{clone[module]}.ev_{method}"
            applied = "".join(f" {_paren(a)}" for a in args)
            env[stmt.var] = f"({ev}{applied})"
    return env


def _if_branch(spec: ChallengeHopSpec) -> list[str]:
    """Collision branch: inline the challenger, functionalize its two decaps,
    slice-peel the KDF-input equality, and collapse via encoding injectivity."""
    pqc = spec.clone_alias[spec.pq_module]
    pqm = spec.pq_module
    ct0, ct1 = spec.ct_params
    g0 = spec.red_component_fields[0]
    g1 = spec.red_component_fields[1]
    bind0 = (
        "bd0",
        f"{spec.red_base}.{g0[1]}" "{2}",
        f"{spec.red_base}.{g0[2]}" "{2}",
        "c0",
    )
    bind1 = (
        "bd1",
        f"{spec.red_base}.{g1[1]}" "{2}",
        f"{spec.red_base}.{g1[2]}" "{2}",
        "c1",
    )
    peel = slice_peel(spec.shape, bind0, bind1)
    ck0, ck1 = spec.challenger_key_fields
    return [
        "  + rcondt{2} 1; first by auto.",
        "    inline{2} 1.",
        "    sp.",
        f"    exists* (glob {pqm})"
        "{2}"
        f", {spec.challenger_ref}.{ck0}"
        "{2}"
        f", {spec.challenger_ref}.{ck1}"
        "{2}"
        f", {ct0}"
        "{2}"
        f", {ct1}"
        "{2}"
        "; elim* => gp3 bd0 bd1 c0 c1.",
        "    wp.",
        f"    call{{2}} ({pqm}_decaps_det gp3 bd1 c1.`1).",
        f"    call{{2}} ({pqm}_decaps_det gp3 bd0 c0.`1).",
        "    skip => />. move => &2 h hn.",
        *[f"    {ln}" for ln in peel],
        f"    have hd : {pqc}.ev_decaps bd0 c0.`1 = {pqc}.ev_decaps bd1 c1.`1"
        f" by apply ({spec.inj_axiom} _ _ he).",
        "    rewrite h /=. smt().",
    ]


def _if_branch_pk(spec: ChallengeHopSpec) -> list[str]:
    """PK collision branch: like the CT branch (inline the PQ binding challenger,
    functionalize its two decaps, slice-peel the shared-secret leaf, collapse
    the decaps via ``encodesharedsecret`` injectivity) PLUS an encodeencapskey
    slice-peel deriving ``ek_T_0 = ek_T_1``, so the game's packed-encaps-key
    inequality reduces to the challenger's PQ encaps-key inequality."""
    pqc = spec.clone_alias[spec.pq_module]
    pqm = spec.pq_module
    ct0, ct1 = spec.ct_params
    g0 = spec.red_component_fields[0]
    g1 = spec.red_component_fields[1]
    bind0 = (
        "bd0",
        f"{spec.red_base}.{g0[1]}" "{2}",
        f"{spec.red_base}.{g0[2]}" "{2}",
        "c0",
    )
    bind1 = (
        "bd1",
        f"{spec.red_base}.{g1[1]}" "{2}",
        f"{spec.red_base}.{g1[2]}" "{2}",
        "c1",
    )
    peel_ss = slice_peel(spec.shape, bind0, bind1)
    peel_ek = slice_peel_to_eek(spec.shape, bind0, bind1)
    e0 = spec.ek_component_fields[0]
    e1 = spec.ek_component_fields[1]
    ck0, ck1 = spec.challenger_key_fields
    return [
        "  + rcondt{2} 1; first by auto.",
        "    inline{2} 1.",
        "    sp.",
        f"    exists* (glob {pqm})"
        "{2}"
        f", {spec.challenger_ref}.{ck0}"
        "{2}"
        f", {spec.challenger_ref}.{ck1}"
        "{2}"
        f", {ct0}"
        "{2}"
        f", {ct1}"
        "{2}"
        "; elim* => gp3 bd0 bd1 c0 c1.",
        "    wp.",
        f"    call{{2}} ({pqm}_decaps_det gp3 bd1 c1.`1).",
        f"    call{{2}} ({pqm}_decaps_det gp3 bd0 c0.`1).",
        "    skip => />. move => &2 h.",
        *[f"    {ln}" for ln in peel_ss],
        f"    have hd : {pqc}.ev_decaps bd0 c0.`1 = {pqc}.ev_decaps bd1 c1.`1"
        f" by apply ({spec.inj_axiom} _ _ he).",
        *[f"    {ln}" for ln in peel_ek],
        f"    have hek : {spec.red_base}.{e0[1]}"
        "{2}"
        f" = {spec.red_base}.{e1[1]}"
        "{2}"
        f" by apply ({spec.ek_inj_axiom} _ _ heek).",
        "    smt().",
    ]


def _else_branch_pk(spec: ChallengeHopSpec) -> list[str]:
    """PK no-collision branch: functionalize the two ``H.evaluate`` calls; the
    game's and reduction's packed-encaps-key inequalities coincide under the
    decomposition coupling (``smt`` closes from the invariant)."""
    hm = spec.h_module
    return [
        "  rcondf{2} 1; first by (auto; smt()).",
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
        "  skip => />.",
    ]


def _else_branch(spec: ChallengeHopSpec) -> list[str]:
    """No-collision branch: functionalize the two ``H.evaluate`` calls."""
    hm = spec.h_module
    return [
        "  rcondf{2} 1; first by (auto; smt()).",
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
        "  skip => />.",
    ]


# ---------------------------------------------------------------------------
# hop_4: ``R_KDF o Unbreakable ~ Hybrid_Unbreakable(<Scheme>)``.  BOTH sides
# return ``false`` (the KDF Unbreakable challenger's ``challenge`` is ``false``,
# inlined in R_KDF's else-branch; the Hybrid Unbreakable game runs two concrete
# ``<Scheme>.decaps`` then returns ``false``).  Sides are MIRRORED from hop_0:
# the game is on the RIGHT, the case-split reduction on the LEFT.  No injectivity
# and no KDF-input coupling are needed -- the result is ``false`` regardless of
# the keys, so both dead prefixes are functionalized and discarded.
# ---------------------------------------------------------------------------


@dataclass
class Hop4Spec:
    """Everything the hop_4 (false/false) tactic needs, derived from the hop's
    reduction/game ASTs."""

    val_lemma_name: str  # "<Scheme>_decaps_val"
    game_glob_mods: list[str]  # val-lemma glob-binder order, e.g. [KEM_PQ,KEM_T,L,H]
    game_key_refs: list[str]  # 2 game packed-key glob refs (no side annotation)
    ct_params: list[str]  # ["ct0", "ct1"]
    sync_mods: list[str]  # every module needing (glob M){1}=(glob M){2}
    red_base: str  # "R_KDF"
    red_glob_mods: list[str]  # reduction-prefix callee mods (subset of game mods)
    red_component_fields: list[list[str]]  # [[dk_PQ_0,dk_T_0,ek_T_0], [...1]]
    clone_alias: dict[str, str]
    decomp_coupling: list[str]  # game packed key{2} = tuple of reduction fields{1}
    red_proc: ec_ast.Proc  # reduction (left) challenge proc
    guard_annot: (
        str  # the reduction if-guard, side-{1} annotated (e.g. "ek0{1} = ek1{1}")
    )


def _blk_env_hop4(spec: Hop4Spec, field_elim: list[str]) -> dict[str, str]:
    """Functional env of the reduction prefix under the ``exists*`` elim names
    (fields -> ``dp0``.. ; cts -> the game ct elims ``C0``/``C1``, since hop_4
    reuses the game ciphertexts via the ``={ct}`` invariant rather than binding
    separate reduction ct vars)."""
    flat = [f for grp in spec.red_component_fields for f in grp]
    env: dict[str, str] = dict(zip(flat, field_elim))
    env[spec.ct_params[0]] = "C0"
    env[spec.ct_params[1]] = "C1"
    for stmt in spec.red_proc.body:
        if isinstance(stmt, ec_ast.If):
            break
        if isinstance(stmt, ec_ast.Assign):
            env[stmt.var] = _subst(stmt.rhs, env)
        elif isinstance(stmt, ec_ast.Call):
            module, _, method = stmt.callee.partition(".")
            args = [_subst(a, env) for a in _split_top_args(stmt.args)]
            ev = f"{spec.clone_alias[module]}.ev_{method}"
            applied = "".join(f" {_paren(a)}" for a in args)
            env[stmt.var] = f"({ev}{applied})"
    return env


def challenge_tactic_hop4(spec: Hop4Spec) -> list[str] | None:
    """Emit the full ``hop_<i>_challenge`` tactic for the false/false shape."""
    split = _prefix_and_if(spec.red_proc.body)
    if split is None:
        return None
    prefix, _if = split
    prefix = [s for s in prefix if not isinstance(s, ec_ast.VarDecl)]
    red_len = len(prefix)
    gmods = spec.game_glob_mods
    gge = _game_glob_elim(gmods)
    ct0, ct1 = spec.ct_params

    inv = " /\\ ".join(
        [f"(glob {m})" "{1}" f" = (glob {m})" "{2}" for m in spec.sync_mods]
        + [f"{c}" "{1}" f" = {c}" "{2}" for c in spec.ct_params]
        + spec.decomp_coupling
    )
    lines = ["proof.", "  proc.", f"  seq {red_len} 2 : ({inv})."]

    # first subgoal: sp; exists* game globs+keys+ct + reduction fields;
    # functionalize the game decaps (call{2} val-lemma) and the reduction prefix
    # (call{1} _det peel).  The reduction peel reuses the game glob elims (the
    # ``={glob}`` invariant makes the two sides' globs equal).
    field_elim = _field_elim_names(spec.red_component_fields)
    game_ex = (
        [f"(glob {m})" "{2}" for m in gmods]
        + [f"{r}" "{2}" for r in spec.game_key_refs]
        + [f"{c}" "{2}" for c in spec.ct_params]
        + [
            f"{spec.red_base}.{f}" "{1}"
            for grp in spec.red_component_fields
            for f in grp
        ]
    )
    elim = gge + ["D0", "D1", "C0", "C1"] + field_elim
    gargs = " ".join(gge)
    blk_env = _blk_env_hop4(spec, field_elim)
    glob_of = {m: gge[gmods.index(m)] for m in spec.red_glob_mods}
    peel = _peel_stmts(_drop_leading_assigns(prefix), blk_env, glob_of, "{1}")
    lines += [
        "  + sp.",
        f"    exists* {', '.join(game_ex)};",
        f"    elim* => {' '.join(elim)}.",
        f"    call{{2}} ({spec.val_lemma_name} {gargs} D1 C1).",
        f"    call{{2}} ({spec.val_lemma_name} {gargs} D0 C0).",
        *[f"    {ln}" for ln in peel],
        "    skip => />.",
    ]

    # both sides return false; select the branch on the reduction's if guard
    # (CT: ``ct0 = ct1``; PK: ``ek0 = ek1`` over the packed encaps keys).
    del ct0, ct1
    lines += [
        f"  case ({spec.guard_annot}).",
        "  + rcondt{1} 1; first by auto.",
        "    wp. skip => />.",
        "  rcondf{1} 1; first by (auto; smt()).",
        "  inline{1} 1.",
        "  wp.",
        "  skip => />.",
        "  qed.",
    ]
    return lines


# ---------------------------------------------------------------------------
# hop_2: ``R_PQ_Bind o Unbreakable ~ R_KDF o Breakable``.  BOTH sides are
# case-split reductions computing the SAME KDF-input pair.  LEFT forwards a
# KDF-input collision (with differing PQ ciphertexts) to the KEM_PQ *Unbreakable*
# binding challenger (returns false); RIGHT forwards non-equal ciphertexts to the
# KDF *Breakable* collision challenger.  The equivalence's confidence-critical
# step is the no-collision branch, where the RHS's extra ``kdf_in_0 <> kdf_in_1``
# is redundant because ``kdf_in_0 = kdf_in_1`` forces (via the encodeciphertext
# right-slice + injectivity) the two ciphertexts equal, contradicting ``ct0<>ct1``.
# ---------------------------------------------------------------------------


@dataclass
class Hop2Spec:
    """Everything the hop_2 (both-case-split) tactic needs."""

    ct_params: list[str]
    sync_mods: list[str]  # every module needing (glob M){1}=(glob M){2}
    l_base: str  # "R_PQ_Bind"
    r_base: str  # "R_KDF"
    l_prefix: list[ec_ast.EcStmt]  # left reduction prefix (before its If)
    r_prefix: list[ec_ast.EcStmt]  # right reduction prefix
    glob_mods: list[str]  # peel glob elim order (KEM_PQ,KEM_T,L), first-appearance
    l_component_fields: list[list[str]]  # [[dk_PQ_0,dk_T_0,ek_T_0],[...1]] (left)
    r_component_fields: list[list[str]]  # right
    clone_alias: dict[str, str]
    shape: ConcatShape
    pq_module: str  # "KEM_PQ"
    h_module: str  # "H"
    l_challenger_ref: str  # "KEM_PQ_c.LEAK_BIND_K_CT_Unbreakable"
    l_challenger_key_fields: list[str]  # ["dk0", "dk1"]
    ect_inj_axiom: str  # "KEM_PQ_encodeciphertext_inj"


def _blk_env(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    base: str,
    component_fields: list[list[str]],
    field_elim: list[str],
    ct_params: list[str],
    ct_elim: tuple[str, str],
    red_proc_prefix: list[ec_ast.EcStmt],
    clone_alias: dict[str, str],
) -> dict[str, str]:
    """Functional env of a reduction prefix under exists* elim names."""
    del base
    flat = [f for grp in component_fields for f in grp]
    env: dict[str, str] = dict(zip(flat, field_elim))
    env[ct_params[0]] = ct_elim[0]
    env[ct_params[1]] = ct_elim[1]
    for stmt in red_proc_prefix:
        if isinstance(stmt, ec_ast.Assign):
            env[stmt.var] = _subst(stmt.rhs, env)
        elif isinstance(stmt, ec_ast.Call):
            module, _, method = stmt.callee.partition(".")
            args = [_subst(a, env) for a in _split_top_args(stmt.args)]
            ev = f"{clone_alias[module]}.ev_{method}"
            applied = "".join(f" {_paren(a)}" for a in args)
            env[stmt.var] = f"({ev}{applied})"
    return env


def challenge_tactic_hop2(spec: Hop2Spec) -> list[str] | None:
    """Emit the full ``hop_<i>_challenge`` tactic for the both-case-split shape."""
    ct0, ct1 = spec.ct_params
    l_len = len([s for s in spec.l_prefix if not isinstance(s, ec_ast.VarDecl)])
    r_len = len([s for s in spec.r_prefix if not isinstance(s, ec_ast.VarDecl)])
    gm = spec.glob_mods
    gge = [f"gg{i}" for i in range(len(gm))]
    glob_of = dict(zip(gm, gge))
    hm = spec.h_module
    lchal = spec.l_challenger_ref
    ck0, ck1 = spec.l_challenger_key_fields
    lg0, lg1 = spec.l_component_fields

    l_fe = [f"l{n}" for n in _field_elim_names(spec.l_component_fields)]
    r_fe = [f"r{n}" for n in _field_elim_names(spec.r_component_fields)]

    # -- invariant -----------------------------------------------------------
    def _s2(ref: str) -> str:
        return ref + "{2}"

    rg0, rg1 = spec.r_component_fields
    kdf0_term = spec.shape.kdf_in(
        _s2(f"{spec.r_base}.{rg0[0]}"),
        _s2(f"{spec.r_base}.{rg0[1]}"),
        _s2(f"{spec.r_base}.{rg0[2]}"),
        _s2(ct0),
    )
    kdf1_term = spec.shape.kdf_in(
        _s2(f"{spec.r_base}.{rg1[0]}"),
        _s2(f"{spec.r_base}.{rg1[1]}"),
        _s2(f"{spec.r_base}.{rg1[2]}"),
        _s2(ct1),
    )
    inv_terms = (
        [f"{c}" "{1}" f" = {c}" "{2}" for c in spec.ct_params]
        + [
            "kdf_in_0{1} = kdf_in_0{2}",
            "kdf_in_1{1} = kdf_in_1{2}",
        ]
        + [f"(glob {m})" "{1}" f" = (glob {m})" "{2}" for m in spec.sync_mods]
        + [
            f"{spec.l_base}.{lg0[0]}" "{1}" f" = {lchal}.{ck0}" "{1}",
            f"{spec.l_base}.{lg1[0]}" "{1}" f" = {lchal}.{ck1}" "{1}",
        ]
        + [
            f"{spec.l_base}.{f}" "{1}" f" = {spec.r_base}.{f}" "{2}"
            for grp in spec.l_component_fields
            for f in grp
        ]
        + [
            "kdf_in_0" "{2}" f" = {kdf0_term}",
            "kdf_in_1" "{2}" f" = {kdf1_term}",
        ]
    )
    inv = " /\\ ".join(inv_terms)
    lines = ["proof.", "  proc.", f"  seq {l_len} {r_len} : ({inv})."]

    # -- prefix functionalization subgoal ------------------------------------
    l_ex = (
        [f"(glob {m})" "{1}" for m in gm]
        + [f"{spec.l_base}.{f}" "{1}" for grp in spec.l_component_fields for f in grp]
        + [f"{c}" "{1}" for c in spec.ct_params]
        + [f"{spec.r_base}.{f}" "{2}" for grp in spec.r_component_fields for f in grp]
    )
    l_elim = gge + l_fe + ["lc0", "lc1"] + r_fe
    l_env = _blk_env(
        spec.l_base,
        spec.l_component_fields,
        l_fe,
        spec.ct_params,
        ("lc0", "lc1"),
        [s for s in spec.l_prefix if not isinstance(s, ec_ast.VarDecl)],
        spec.clone_alias,
    )
    r_env = _blk_env(
        spec.r_base,
        spec.r_component_fields,
        r_fe,
        spec.ct_params,
        ("lc0", "lc1"),
        [s for s in spec.r_prefix if not isinstance(s, ec_ast.VarDecl)],
        spec.clone_alias,
    )
    l_peel = _peel_stmts(_drop_leading_assigns(spec.l_prefix), l_env, glob_of, "{1}")
    r_peel = _peel_stmts(_drop_leading_assigns(spec.r_prefix), r_env, glob_of, "{2}")
    lines += [
        "  + sp.",
        f"    exists* {', '.join(l_ex)};",
        f"    elim* => {' '.join(l_elim)}.",
        *[f"    {ln}" for ln in r_peel],
        *[f"    {ln}" for ln in l_peel],
        "    skip => />.",
    ]

    # -- outer case: RHS ct-equality guard -----------------------------------
    lines += [
        f"  case ({ct0}" "{2}" f" = {ct1}" "{2}).",
        "  + rcondt{2} 1; first by auto.",
        "    rcondf{1} 1; first by (auto; smt()).",
        "    exists* (glob "
        f"{hm})"
        "{1}"
        ", kdf_in_0"
        "{1}"
        ", kdf_in_1"
        "{1}"
        "; elim* => gh ki0 ki1.",
        f"    wp. call{{1}} ({hm}_evaluate_det gh ki1). call{{1}} ({hm}_evaluate_det gh ki0).",
        "    skip => />.",
        "  rcondf{2} 1; first by (auto; smt()).",
        "  inline{2} 1.",
        "  sp.",
    ]

    # -- inner case: LHS PQ-collision guard ----------------------------------
    inner_guard = (
        "kdf_in_0"
        "{1}"
        " = kdf_in_1"
        "{1}"
        f" /\\ {ct0}"
        "{1}"
        ".`1 <> "
        f"{ct1}"
        "{1}"
        ".`1"
    )
    lines += [
        f"  case ({inner_guard}).",
        "  + rcondt{1} 1; first by (auto; smt()).",
        "    inline{1} 1.",
        "    sp.",
        f"    exists* (glob {spec.pq_module})"
        "{1}"
        f", {lchal}.{ck0}"
        "{1}"
        f", {lchal}.{ck1}"
        "{1}"
        f", {ct0}"
        "{1}"
        f", {ct1}"
        "{1}"
        "; elim* => gp3 xdp0 xdp1 xc0 xc1.",
        "    exists* (glob "
        f"{hm})"
        "{2}"
        ", kdf_in_0"
        "{2}"
        ", kdf_in_1"
        "{2}"
        "; elim* => gh2 ki0 ki1.",
        f"    wp. call{{2}} ({hm}_evaluate_det gh2 ki1). call{{2}} ({hm}_evaluate_det gh2 ki0).",
        f"    call{{1}} ({spec.pq_module}_decaps_det gp3 xdp1 xc1.`1). "
        f"call{{1}} ({spec.pq_module}_decaps_det gp3 xdp0 xc0.`1).",
        "    skip => />; smt().",
    ]

    # -- no-collision else: both are the hybrid predicate. The RHS's extra
    # ``kdf_in_0 <> kdf_in_1`` conjunct is redundant: ``kdf_in_0 = kdf_in_1``
    # forces (encodeciphertext right-slice + injectivity) the two ciphertexts'
    # T-components equal; with the negated LEFT guard (``kdf`` equal =>
    # PQ-components equal) the two full ciphertexts coincide, contradicting
    # ``ct0 <> ct1``. Derive it with an explicit ``have`` chain (smt cannot
    # navigate the 4-deep concat unaided).
    rg0b, rg1b = spec.r_component_fields
    b2 = "{2}"
    bind0 = (
        f"{spec.r_base}.{rg0b[0]}{b2}",
        f"{spec.r_base}.{rg0b[1]}{b2}",
        f"{spec.r_base}.{rg0b[2]}{b2}",
        f"{ct0}{b2}",
    )
    bind1 = (
        f"{spec.r_base}.{rg1b[0]}{b2}",
        f"{spec.r_base}.{rg1b[1]}{b2}",
        f"{spec.r_base}.{rg1b[2]}{b2}",
        f"{ct1}{b2}",
    )
    kdf0 = spec.shape.kdf_in(*bind0)
    kdf1 = spec.shape.kdf_in(*bind1)
    peel = slice_peel_to_ect(spec.shape, bind0, bind1)
    lines += [
        "  rcondf{1} 1; first by (auto; smt()).",
        "  exists* (glob "
        f"{hm})"
        "{1}"
        ", kdf_in_0"
        "{1}"
        ", kdf_in_1"
        "{1}"
        "; elim* => gh ki0 ki1.",
        "  exists* (glob "
        f"{hm})"
        "{2}"
        ", kdf_in_0"
        "{2}"
        ", kdf_in_1"
        "{2}"
        "; elim* => gh2 ri0 ri1.",
        f"  wp. call{{1}} ({hm}_evaluate_det gh ki1). call{{1}} ({hm}_evaluate_det gh ki0).",
        f"  call{{2}} ({hm}_evaluate_det gh2 ri1). call{{2}} ({hm}_evaluate_det gh2 ri0).",
        "  skip => />. move => &2 hne hg.",
        f"  have hkct : {kdf0} = {kdf1} => {ct0}" "{2}" f" = {ct1}" "{2}" ".",
        "  + move => h.",
        *[f"    {ln}" for ln in peel],
        f"    have hct2 : {ct0}"
        "{2}"
        f".`2 = {ct1}"
        "{2}"
        f".`2 by apply ({spec.ect_inj_axiom} _ _ hect).",
        "    smt().",
        "  smt().",
        "  qed.",
    ]
    return lines
