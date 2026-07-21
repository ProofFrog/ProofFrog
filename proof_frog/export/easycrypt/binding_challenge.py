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


def keygen_derived_ev(
    derivekeypair_proc: ec_ast.Proc,
    seed_value: str,
    clone_alias: dict[str, str],
) -> str | None:
    """Symbolically evaluate a seedbased ``DeriveKeyPair(seed)`` with its single
    seed parameter bound to ``seed_value``, returning the ev-form of the WHOLE
    ``[EncapsKey, DecapsKey]`` return tuple.

    Used by the self-keygen multi-key coupling to give a reduction's OPAQUE held
    ``EncapsKey`` field its seed-derived functional form: the caller couples the
    reduction's ``(ek_field, seed_field)`` pair to this result (return order is
    ``[EncapsKey, DecapsKey]`` = ``[ek, seed]``). ``None`` if the body is not the
    linear deterministic sequence :func:`model_from_proc` handles, or the proc is
    not single-parameter (a non-seedbased scheme declines -> byte-identical)."""
    if len(derivekeypair_proc.params) != 1:
        return None
    param_rename = {derivekeypair_proc.params[0].name: seed_value}
    model = model_from_proc(derivekeypair_proc, param_rename, clone_alias)
    return model.result if model is not None else None


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
    # For a group T component (CG), the T "decaps" is ``NG.Exp(ct_T, dk_T)`` --
    # ciphertext-first, vs a KEM's ``KEM_T.Decaps(dk_T, ct_T)`` (key-first).
    t_decaps_ct_first: bool = False

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
        if self.t_decaps_ct_first:
            t = f"({self.ev_encss_t} ({self.ev_decaps_t} {ct}.`2 {t_key}))"
        else:
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
    # Which DISTINCT game key / reduction component group each of the two
    # ciphertext sites decapsulates under. ``[0, 1]`` = DIFFKEY (two independent
    # keys); ``[0, 0]`` = SAMEKEY (both ciphertexts under one key). ``game_key_refs``,
    # ``red_component_fields``, and ``challenger_key_fields`` hold the DISTINCT keys.
    ct_key_idx: list[int] = field(default_factory=lambda: [0, 1])
    # -- PK-shape extras (encaps-key binding); all empty/False for CT ----------
    win_is_ek: bool = False  # win term is the packed encaps key, not the ct params
    ek_component_fields: list[list[str]] = field(
        default_factory=list
    )  # [[ek_PQ_0, ek_T_0], [ek_PQ_1, ek_T_1]]
    ek_inj_axiom: str = ""  # "<T>_encodeencapskey_inj"
    challenger_ek_fields: list[str] = field(
        default_factory=list
    )  # challenger's encaps-key field names ["ek0", "ek1"]
    # -- WRAPPER-shape extras (seedbased: game decaps is a SeededKEMWrapper =
    # ``derivekeypair; inner-decaps``, so the game side is functionalized IN PLACE
    # via a side-1 peel instead of the atomic ``<Scheme>_decaps_val`` phoare, whose
    # single ``res = <boolean>`` post inlines the concat to a megabyte term). All
    # empty/None for the bare-decaps (expanded) shape -> byte-identical.
    game_proc: ec_ast.Proc | None = None  # game challenge proc, for the in-place peel
    wrapper_expr: str = (
        ""  # scheme wrapper module expr, e.g. SeededKEMWrapper(KEM_PQ_inner)
    )
    game_base: str = ""  # game reduction base, e.g. R_KG_L
    game_fields: list[str] = field(
        default_factory=list
    )  # game field bare names, exists* order
    inner_pq_module: str = ""  # inner KEM module (challenger's wrapper decaps callee)
    extra_field_couplings: list[str] = field(default_factory=list)  # e.g. s_T_0/seed_0
    base_type: str = ""  # innermost/encss bitstring type, for the aux lemma
    kdf_col_lemma: str = "kdf_col_ss"  # aux lemma name (concat_eq => decaps_eq)


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
    dkey = [f"D{i}" for i in range(len(spec.game_key_refs))]
    game_elim = gge + dkey + ["C0", "C1"]
    gargs = " ".join(gge)
    lines = [
        "proof.",
        "  proc.",
        f"  exists* {', '.join(game_ex)};",
        f"  elim* => {' '.join(game_elim)}.",
        f"  call{{1}} ({spec.val_lemma_name} {gargs} {dkey[spec.ct_key_idx[1]]} C1).",
        f"  call{{1}} ({spec.val_lemma_name} {gargs} {dkey[spec.ct_key_idx[0]]} C0).",
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


def slice_inj_lemmas(shape: ConcatShape, base_type: str, inj_axiom: str) -> list[str]:
    """Emit the ``slice4_first`` + ``kdf_col_ss`` aux lemmas for the wrapper
    collision branch (section-level, before the hop lemma).

    ``slice4_first`` peels the N concat layers (``slice_concat_left_*``) to the
    innermost equality; ``kdf_col_ss`` wraps it with ``encodesharedsecret``
    injectivity, giving the clean forward implication ``<full concat over
    encss x_i> equal ==> x0 = x1`` that closes the ``progress``-unfolded game
    forall-nest leaf. Component types are recovered by parsing the concat-op
    chain: each layer's ``concat_<left>_<right>_to_<result>`` has ``left`` = the
    inner layer's ``result`` (innermost = ``base_type``), so ``right`` = the
    layer's own component type.
    """
    ops_inner = list(reversed(shape.concat_ops))  # inner-first
    sl_outer = shape.slice_axioms()  # outer-first
    comps: list[str] = []
    left = base_type
    for op in ops_inner:
        lr, _, result = op[len("concat_") :].rpartition("_to_")
        comps.append(lr[len(left) + 1 :])
        left = result
    n = len(ops_inner)
    cn = [f"a{i}" for i in range(n)]

    def nest(head: str, sfx: str) -> str:
        term = head
        for op, comp in zip(ops_inner, cn):
            term = f"{op} {_paren(term)} {comp}{sfx}"
        return term

    def partial(depth: int, sfx: str) -> str:
        term = f"e{sfx}"
        for j in range(depth):
            term = f"{ops_inner[j]} {_paren(term)} {cn[j]}{sfx}"
        return term

    qty = [f"(e0 e1 : {base_type})"] + [
        f"({cn[i]}0 {cn[i]}1 : {comps[i]})" for i in range(n)
    ]
    lines = [
        f"  lemma slice4_first {' '.join(qty)} :",
        f"    {nest('e0', '0')} =",
        f"    {nest('e1', '1')} =>",
        "    e0 = e1.",
        "  proof.",
        "    move => H.",
    ]
    prev = "H"
    for k in range(n - 1):
        depth = n - 1 - k
        comp = cn[n - 1 - k]
        t0, t1 = partial(depth, "0"), partial(depth, "1")
        hyp = f"H{depth}"
        lines.append(f"    have {hyp} : {t0} = {t1}")
        lines.append(
            f"      by rewrite -({sl_outer[k]} {_paren(t0)} {comp}0)"
            f" -({sl_outer[k]} {_paren(t1)} {comp}1) {prev}."
        )
        prev = hyp
    lines.append(
        f"    by rewrite -({sl_outer[n - 1]} e0 {cn[0]}0)"
        f" -({sl_outer[n - 1]} e1 {cn[0]}1) {prev}."
    )
    lines.append("  qed.")
    qty2 = [f"(x0 x1 : {base_type})"] + [
        f"({cn[i]}0 {cn[i]}1 : {comps[i]})" for i in range(n)
    ]
    unders = " ".join("_" for _ in range(2 * (n + 1)))
    lines += [
        f"  lemma kdf_col_ss {' '.join(qty2)} :",
        f"    {nest(f'({shape.ev_encss_pq} x0)', '0')} =",
        f"    {nest(f'({shape.ev_encss_pq} x1)', '1')} =>",
        "    x0 = x1.",
        f"  proof. move => H. apply ({inj_axiom} _ _ (slice4_first {unders} H)). qed.",
    ]
    return lines


def _wp_before_calls(lines: list[str]) -> list[str]:
    """Insert a ``wp.`` before every ``call`` line. The in-place game peel needs
    a leading ``wp`` to absorb the game's trailing return expression (the KDF
    boolean) before its ``H.evaluate`` calls; the extra ``wp``s before later calls
    are no-ops. Matches the validated harness peel exactly."""
    out: list[str] = []
    for ln in lines:
        if ln.startswith("call"):
            out.append("wp.")
        out.append(ln)
    return out


def _env_over(
    body: Sequence[ec_ast.EcStmt], base: dict[str, str], clone_alias: dict[str, str]
) -> dict[str, str]:
    """Functional env over a raw statement list (like :func:`_build_env` but not
    tied to a :class:`ec_ast.Proc`): ``x <- e`` substitutes; ``x <@ M.m(a..)``
    becomes ``x = (<clone>.ev_m <a..>)``. ``VarDecl``/``Return`` pass through."""
    env = dict(base)
    for stmt in body:
        if isinstance(stmt, ec_ast.Assign):
            env[stmt.var] = _subst(stmt.rhs, env)
        elif isinstance(stmt, ec_ast.Call):
            module, _, method = stmt.callee.partition(".")
            args = [_subst(a, env) for a in _split_top_args(stmt.args)]
            ev = f"{clone_alias[module]}.ev_{method}"
            applied = "".join(f" {_paren(a)}" for a in args)
            env[stmt.var] = f"({ev}{applied})"
    return env


def challenge_tactic_wrapper(spec: ChallengeHopSpec) -> list[str] | None:
    """Wrapper (seedbased) variant of :func:`challenge_tactic`.

    The game's ``decaps`` is a ``SeededKEMWrapper`` (``derivekeypair;
    inner-decaps``), so the atomic ``<Scheme>_decaps_val`` phoare -- whose single
    ``res = <boolean>`` post inlines the KDF concat to a megabyte term -- does not
    apply. Instead functionalize the game side IN PLACE with a side-1 ``_peel_stmts``
    (order-independent: the two sides compute the KDF in different orders, so
    ``sim`` cannot couple them). The collision branch's game ``forall``-nest is
    unfolded by ``progress`` to a clean leaf, closed by the ``kdf_col_ss`` aux
    lemma applied to the (progress-named) collision hyp ``H``.
    """
    assert spec.game_proc is not None
    split = _prefix_and_if(spec.red_proc.body)
    if split is None:
        return None
    prefix_raw, _red_if = split
    prefix = [s for s in prefix_raw if not isinstance(s, ec_ast.VarDecl)]
    gmods = spec.game_glob_mods
    gge = _game_glob_elim(gmods)
    ct0, ct1 = spec.ct_params
    gfe = [f"D{i}" for i in range(len(spec.game_fields))]

    # -- game side: in-place peel (inline wrapper, functionalize side 1) --------
    game_ex = (
        [f"(glob {m})" "{1}" for m in gmods]
        + [f"{spec.game_base}.{f}" "{1}" for f in spec.game_fields]
        + [f"{c}" "{1}" for c in spec.ct_params]
    )
    grename = dict(zip(spec.game_fields, gfe))
    grename[ct0] = "C0"
    grename[ct1] = "C1"
    genv = _env_over(spec.game_proc.body, grename, spec.clone_alias)
    gbody = [
        s
        for s in spec.game_proc.body
        if not isinstance(s, (ec_ast.VarDecl, ec_ast.Return))
    ]
    lines = [
        "proof.",
        "  proc.",
        f"  inline{{1}} {spec.wrapper_expr}.decaps {spec.wrapper_expr}.encodesharedsecret.",
        f"  exists* {', '.join(game_ex)};",
        f"  elim* => {' '.join(gge + gfe + ['C0', 'C1'])}.",
        *[
            f"  {ln}"
            for ln in _wp_before_calls(
                _peel_stmts(gbody, genv, dict(zip(gmods, gge)), "{1}")
            )
        ],
    ]

    # -- invariant (bare INV + extra field couplings + game-field couplings) ----
    inv_env = _red_env(spec, rename="inv")
    inv_kdf = [
        "kdf_in_0" "{2}" f" = {inv_env['kdf_in_0']}",
        "kdf_in_1" "{2}" f" = {inv_env['kdf_in_1']}",
    ]
    glob_eqs = (
        [f"(glob {m})" "{1}" f" = {gge[i]}" for i, m in enumerate(gmods)]
        + [f"(glob {m})" "{2}" f" = {gge[i]}" for i, m in enumerate(gmods)]
        + [
            f"(glob {m})" "{1}" " = " f"(glob {m})" "{2}"
            for m in spec.extra_glob_sync_mods
        ]
    )
    field_ct_eqs = (
        [f"D{i} = {spec.game_base}.{f}" "{1}" for i, f in enumerate(spec.game_fields)]
        + [f"C{i} = {c}" "{1}" for i, c in enumerate(spec.ct_params)]
        + [f"{c}" "{1}" f" = {c}" "{2}" for c in spec.ct_params]
    )
    # The reduction's leading ct-component assigns (``ct_PQ_0 <- ct0.`1`` ..) as
    # side-2 couplings: needed so the collision branch's ``rcondt`` (whose EC guard
    # is over the ``ct_PQ_*`` locals) discharges from the ``case`` condition.
    ct_annot = {ct0: f"{ct0}" "{2}", ct1: f"{ct1}" "{2}"}
    ct_couplings: list[str] = []
    for s in prefix:  # leading contiguous ct-projection assigns only
        if not isinstance(s, ec_ast.Assign):
            break
        ct_couplings.append(f"{s.var}" "{2}" f" = {_subst(s.rhs, ct_annot)}")
    inv = " /\\ ".join(
        glob_eqs
        + spec.decomp_coupling
        + spec.challenger_coupling
        + spec.extra_field_couplings
        + field_ct_eqs
        + ct_couplings
        + inv_kdf
    )
    n_wrap = sum(
        1
        for s in prefix
        if isinstance(s, ec_ast.Call)
        and s.callee == f"{spec.inner_pq_module}.derivekeypair"
    )
    lines.append(f"  seq 0 {len(prefix) - 3 * n_wrap} : ({inv}).")

    # -- reduction prefix peel (inline wrapper on side 2, then functionalize) ---
    rge = [f"g{i}2" for i in range(len(spec.red_glob_mods))]
    flat_fields = [f for grp in spec.red_component_fields for f in grp]
    rfe = [f"rf{i}" for i in range(len(flat_fields))]
    red_ex = (
        [f"(glob {m})" "{2}" for m in spec.red_glob_mods]
        + [f"{spec.red_base}.{f}" "{2}" for f in flat_fields]
        + [f"{c}" "{2}" for c in spec.ct_params]
    )
    blk_env = _red_env(spec, rename="blk", field_elim=rfe)
    glob_of_blk = dict(zip(spec.red_glob_mods, rge))
    lines += [
        f"  + inline{{2}} {spec.wrapper_expr}.decaps {spec.wrapper_expr}.encodesharedsecret. sp.",
        f"    exists* {', '.join(red_ex)};",
        f"    elim* => {' '.join(rge + rfe + ['c0', 'c1'])}.",
        *[
            f"    {ln}"
            for ln in _wp_before_calls(
                _peel_stmts(_drop_leading_assigns(prefix), blk_env, glob_of_blk, "{2}")
            )
        ],
        "    skip => />.",
    ]

    # -- case split + branches -------------------------------------------------
    # Match the EC guard's own locals (``ct_PQ_0`` .. not ``ct0.`1``): annotate the
    # reduction ``if`` guard with ``{2}`` so ``rcondt``'s ``by auto`` discharges.
    guard = re.sub(r"\b([a-zA-Z_]\w*)\b", r"\1{2}", str(_red_if.guard)).replace(
        "&&", "/\\"
    )
    lines.append(f"  case ({guard}).")
    lines += _if_branch_wrapper(spec)
    lines += _else_branch(spec)
    lines.append("  qed.")
    return lines


def _if_branch_wrapper(spec: ChallengeHopSpec) -> list[str]:
    """Collision branch (wrapper): inline the challenger's ``SeededKEMWrapper``
    decaps, functionalize it, then ``progress`` unfolds the game ``forall``-nest
    to a clean leaf ``(H(c0)=H(c1) && c0<>c1) = (decaps(c0)=decaps(c1))`` (all in
    the challenger's ``bd0``/``c0``/``c1`` vars -- progress substitutes the game's
    key via the couplings). The ``kdf_col_ss`` aux lemma applied to the collision
    hyp ``H`` gives the decaps equality; ``smt`` finishes."""
    inner = spec.inner_pq_module
    ct0, ct1 = spec.ct_params
    red_if = next(s for s in spec.red_proc.body if isinstance(s, ec_ast.If))
    then_body = [s for s in red_if.then_body if not isinstance(s, ec_ast.VarDecl)]
    dkp_calls = [
        s
        for s in then_body
        if isinstance(s, ec_ast.Call) and s.callee == f"{inner}.derivekeypair"
    ]
    dec_calls = [
        s
        for s in then_body
        if isinstance(s, ec_ast.Call) and s.callee == f"{inner}.decaps"
    ]
    dk_field = _split_top_args(dkp_calls[0].args)[0]  # challenger key local
    tenv_base = {dk_field: "bd0"}
    for i, dc in enumerate(dec_calls):
        tenv_base[_split_top_args(dc.args)[1]] = f"c{i}.`1"  # ct_PQ_i -> c_i.`1
    tpeel = _wp_before_calls(
        _peel_stmts(
            then_body,
            _env_over(then_body, tenv_base, spec.clone_alias),
            {inner: "gp3"},
            "{2}",
        )
    )
    chal_keys = "".join(
        f", {spec.challenger_ref}.{ck}" "{2}" for ck in spec.challenger_key_fields
    )
    bd = " ".join(f"bd{i}" for i in range(len(spec.challenger_key_fields)))
    n_under = " ".join("_" for _ in range(2 * (len(spec.shape.concat_ops) + 1)))
    return [
        "  + rcondt{2} 1; first by auto.",
        "    inline{2} 1.",
        f"    inline{{2}} {spec.wrapper_expr}.decaps.",
        "    sp.",
        f"    exists* (glob {inner})"
        "{2}"
        f"{chal_keys}, {ct0}"
        "{2}"
        f", {ct1}"
        "{2}"
        f"; elim* => gp3 {bd} c0 c1.",
        *[f"    {ln}" for ln in tpeel],
        f"    skip => />. progress; (try (have Hd := {spec.kdf_col_lemma} {n_under} H;"
        " smt()); smt()).",
    ]


def _field_elim_names(groups: list[list[str]]) -> list[str]:
    """Per-index reduction-field elim names: ``[[..0], [..1]]`` -> ``[dp0, dt0,
    ek0, dp1, dt1, ek1]``."""
    out: list[str] = []
    for i, _ in enumerate(groups):
        out += [f"dp{i}", f"dt{i}", f"ek{i}"]
    return out


def _drop_leading_assigns(
    stmts: Sequence[ec_ast.EcStmt],
) -> list[ec_ast.EcStmt]:
    """Drop the leading assignment run (the ciphertext projections ``sp`` peels
    before the reduction-prefix functionalization)."""
    i = 0
    while i < len(stmts) and isinstance(stmts[i], ec_ast.Assign):
        i += 1
    return list(stmts[i:])


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
    i0, i1 = spec.ct_key_idx
    g0 = spec.red_component_fields[i0]
    g1 = spec.red_component_fields[i1]
    bd = [f"bd{i}" for i in range(len(spec.challenger_key_fields))]
    bind0 = (
        bd[i0],
        f"{spec.red_base}.{g0[1]}" "{2}",
        f"{spec.red_base}.{g0[2]}" "{2}",
        "c0",
    )
    bind1 = (
        bd[i1],
        f"{spec.red_base}.{g1[1]}" "{2}",
        f"{spec.red_base}.{g1[2]}" "{2}",
        "c1",
    )
    peel = slice_peel(spec.shape, bind0, bind1)
    chal_keys = "".join(
        f", {spec.challenger_ref}.{ck}" "{2}" for ck in spec.challenger_key_fields
    )
    return [
        "  + rcondt{2} 1; first by auto.",
        "    inline{2} 1.",
        "    sp.",
        f"    exists* (glob {pqm})"
        "{2}"
        f"{chal_keys}"
        f", {ct0}"
        "{2}"
        f", {ct1}"
        "{2}"
        f"; elim* => gp3 {' '.join(bd)} c0 c1.",
        "    wp.",
        f"    call{{2}} ({pqm}_decaps_det gp3 {bd[i1]} c1.`1).",
        f"    call{{2}} ({pqm}_decaps_det gp3 {bd[i0]} c0.`1).",
        "    skip => />. move => &2 h hn.",
        *[f"    {ln}" for ln in peel],
        f"    have hd : {pqc}.ev_decaps {bd[i0]} c0.`1 = {pqc}.ev_decaps {bd[i1]} c1.`1"
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
    # DISTINCT-key site map; ``[0, 1]`` DIFFKEY, ``[0, 0]`` SAMEKEY. See
    # :class:`ChallengeHopSpec`.
    ct_key_idx: list[int] = field(default_factory=lambda: [0, 1])
    # Single-R seedbased shape: the reduction derives its component keys as
    # LOCALS from seed fields (one per game key) rather than holding
    # ``dk_PQ``/``dk_T``/``ek_T`` as fields. When set, the prefix functionalizes
    # FORWARD from the seeds (``exists* R.seedN``, seeded by ``{seedN: SN}``) and
    # the decomp coupling is ``game.dkN = R.seedN``.
    seed_fields: list[str] = field(default_factory=list)
    # PK binding (ek-guard): the hop post threads the ek seams
    # (``game.ekN{2} = R.ekN{1}``) + the ek-derivation coupling
    # (``(R.ekN{1}, R.seedN{1}) = (ev-form, R.seedN{1})``). Both are preserved by
    # the (ek/seed-untouching) prefix, so the ``seq`` invariant must RE-STATE them
    # to reach the post, and each branch closes under ``=> /#`` (CT has no such
    # coupling -> ``/>`` closes bare). Empty on the CT path (byte-identical).
    ek_inv_conj: list[str] = field(default_factory=list)


def _blk_env_hop4(spec: Hop4Spec, field_elim: list[str]) -> dict[str, str]:
    """Functional env of the reduction prefix under the ``exists*`` elim names
    (fields -> ``dp0``.. ; cts -> the game ct elims ``C0``/``C1``, since hop_4
    reuses the game ciphertexts via the ``={ct}`` invariant rather than binding
    separate reduction ct vars). Single-R: base on ``{seedN: SN}`` and let the
    prefix walk derive every component local functionally."""
    if spec.seed_fields:
        env: dict[str, str] = {sf: f"S{j}" for j, sf in enumerate(spec.seed_fields)}
    else:
        flat = [f for grp in spec.red_component_fields for f in grp]
        env = dict(zip(flat, field_elim))
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
        + spec.ek_inv_conj
    )
    lines = ["proof.", "  proc.", f"  seq {red_len} 2 : ({inv})."]

    # first subgoal: sp; exists* game globs+keys+ct + reduction fields;
    # functionalize the game decaps (call{2} val-lemma) and the reduction prefix
    # (call{1} _det peel).  The reduction peel reuses the game glob elims (the
    # ``={glob}`` invariant makes the two sides' globs equal).
    if spec.seed_fields:
        # Single-R: bind the seed fields; the prefix walk derives the rest.
        field_elim = [f"S{j}" for j in range(len(spec.seed_fields))]
        red_ex = [f"{spec.red_base}.{sf}" "{1}" for sf in spec.seed_fields]
    else:
        field_elim = _field_elim_names(spec.red_component_fields)
        red_ex = [
            f"{spec.red_base}.{f}" "{1}"
            for grp in spec.red_component_fields
            for f in grp
        ]
    game_ex = (
        [f"(glob {m})" "{2}" for m in gmods]
        + [f"{r}" "{2}" for r in spec.game_key_refs]
        + [f"{c}" "{2}" for c in spec.ct_params]
        + red_ex
    )
    dkey = [f"D{i}" for i in range(len(spec.game_key_refs))]
    elim = gge + dkey + ["C0", "C1"] + field_elim
    gargs = " ".join(gge)
    blk_env = _blk_env_hop4(spec, field_elim)
    glob_of = {m: gge[gmods.index(m)] for m in spec.red_glob_mods}
    peel = _peel_stmts(_drop_leading_assigns(prefix), blk_env, glob_of, "{1}")
    lines += [
        "  + sp.",
        f"    exists* {', '.join(game_ex)};",
        f"    elim* => {' '.join(elim)}.",
        f"    call{{2}} ({spec.val_lemma_name} {gargs} {dkey[spec.ct_key_idx[1]]} C1).",
        f"    call{{2}} ({spec.val_lemma_name} {gargs} {dkey[spec.ct_key_idx[0]]} C0).",
        *[f"    {ln}" for ln in peel],
        "    skip => />.",
    ]

    # both sides return false; select the branch on the reduction's if guard
    # (CT: ``ct0 = ct1``; PK: ``ek0 = ek1`` over the packed encaps keys). PK's
    # post threads the ek-derivation coupling, so each branch leaves a residual
    # ek equality ``smt`` must close (CT's ``/>`` closes bare).
    del ct0, ct1
    # PK: the post threads the ek-derivation coupling, so ``skip => />`` leaves a
    # residual ek equality (``R.ek1 = ev-form``, chained via the branch guard) that
    # keeps the pre hypotheses only under ``=> /#`` (``=> />`` discharges them and
    # ``smt`` is then left a premise-free goal). CT has no such coupling.
    then_tail = "    wp. skip => /#." if spec.ek_inv_conj else "    wp. skip => />."
    else_skip = "  skip => /#." if spec.ek_inv_conj else "  skip => />."
    lines += [
        f"  case ({spec.guard_annot}).",
        "  + rcondt{1} 1; first by auto.",
        then_tail,
        "  rcondf{1} 1; first by (auto; smt()).",
        "  inline{1} 1.",
        "  wp.",
        else_skip,
        "  qed.",
    ]
    return lines


def challenge_tactic_hop8_barefalse(
    spec: Hop4Spec, wrapper_expr: str, inv: str
) -> list[str] | None:
    """Emit the ``hop_<i>_challenge`` tactic for the false/BARE-false shape.

    LEFT (side ``{1}``) is the single-R case-split reduction whose every branch
    returns ``false``; RIGHT (side ``{2}``) has been pruned to a bare ``return
    false`` (its dead decaps absorbed).  Unlike :func:`challenge_tactic_hop4`
    there is nothing to functionalize on the game side and no ``={glob}``
    coupling.  As in :func:`challenge_tactic_wrapper` the reduction's ``decaps``
    is a ``SeededKEMWrapper`` (``derivekeypair; inner-decaps``), so ``inline{1}``
    the wrapper first (the real proc holds ONE wrapper call; the peel is built
    from the engine-inlined flat state) and size the ``seq`` split by the
    EC-inlined instruction count ``len(prefix) - 3 * n_wrap``.  Split the LEFT's
    dead deterministic prefix off with ``seq <n> 0 : (true)``, peel it ONE-SIDED
    (freezing the reduction's OWN globs via ``exists* (glob M){1}``), then
    collapse the trivial ``if`` (both branches ``false``) so both sides return
    ``false``."""
    if len(spec.ct_params) != 2 or not spec.seed_fields:
        return None
    split = _prefix_and_if(spec.red_proc.body)
    if split is None:
        return None
    prefix_raw, _if = split
    prefix = [s for s in prefix_raw if not isinstance(s, ec_ast.VarDecl)]
    n_wrap = sum(
        1
        for s in prefix
        if isinstance(s, ec_ast.Call) and s.callee.endswith(".derivekeypair")
    )
    seq_n = len(prefix) - 3 * n_wrap

    field_elim = [f"S{j}" for j in range(len(spec.seed_fields))]
    red_ex = [f"{spec.red_base}.{sf}" "{1}" for sf in spec.seed_fields]
    gmods = spec.red_glob_mods
    gge = [f"g{j}" for j in range(len(gmods))]
    glob_ex = [f"(glob {m})" "{1}" for m in gmods]
    glob_of = {m: gge[i] for i, m in enumerate(gmods)}
    ct_ex = [f"{c}" "{1}" for c in spec.ct_params]

    blk_env = _blk_env_hop4(spec, field_elim)
    peel = _wp_before_calls(
        _peel_stmts(_drop_leading_assigns(prefix), blk_env, glob_of, "{1}")
    )

    lines = [
        "proof.",
        "  proc.",
        f"  seq {seq_n} 0 : ({inv}).",
        f"  + inline{{1}} {wrapper_expr}.decaps {wrapper_expr}.encodesharedsecret. sp.",
        f"    exists* {', '.join(glob_ex + ct_ex + red_ex)};",
        f"    elim* => {' '.join(gge + ['C0', 'C1'] + field_elim)}.",
        *[f"    {ln}" for ln in peel],
        "    skip => /#.",
        f"  case ({spec.guard_annot}).",
        "  + rcondt{1} 1; first by auto.",
        "    wp. skip => /#.",
        "  rcondf{1} 1; first by (auto; smt()).",
        "  inline{1} 1.",
        "  wp.",
        "  skip => /#.",
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
    l_challenger_key_fields: list[str]  # DISTINCT: ["dk0", "dk1"] / ["dk0"] SAMEKEY
    ect_inj_axiom: str  # "KEM_PQ_encodeciphertext_inj"
    # DISTINCT-key site map; ``[0, 1]`` DIFFKEY, ``[0, 0]`` SAMEKEY. The
    # ``*_component_fields`` and ``l_challenger_key_fields`` hold DISTINCT keys.
    ct_key_idx: list[int] = field(default_factory=lambda: [0, 1])
    # -- PK-shape extras (encaps-key binding); empty/False for CT --------------
    win_is_ek: bool = False
    l_ek_component_fields: list[list[str]] = field(
        default_factory=list
    )  # [[ek_PQ_0, ek_T_0], [ek_PQ_1, ek_T_1]] (left)
    r_ek_component_fields: list[list[str]] = field(default_factory=list)  # right
    l_challenger_ek_fields: list[str] = field(
        default_factory=list
    )  # the L challenger's encaps-key field names ["ek0", "ek1"]
    l_guard: str = ""  # left reduction if-guard, raw ("kdf_in_0 = kdf_in_1")
    r_guard: str = ""  # right reduction if-guard, raw ("ek0 = ek1")
    # -- WRAPPER-shape extras (seedbased hop_6: both reductions' PQ decaps is a
    # ``SeededKEMWrapper`` = ``derivekeypair; inner-decaps``, so both prefixes are
    # functionalized via the EXPANDED flat-state bodies + an ``inline{i} <wrapper>``
    # instead of the atomic ``<pq>_decaps_det``; the LHS collision challenger also
    # re-decapsulates through the wrapper). All empty/None for the bare shape ->
    # ``challenge_tactic_hop2`` unchanged (byte-identical). ----------------------
    wrapper_expr: str = ""  # e.g. "SeededKEMWrapper(KEM_PQ_inner)"
    inner_pq_module: str = ""  # inner KEM module, e.g. "KEM_PQ_inner"
    kdf_col_lemma: str = "kdf_col_ss"  # aux lemma (concat_eq => decaps_eq)
    l_own_fields: list[str] = field(
        default_factory=list
    )  # reduction own fields, exists*
    l_red_proc: ec_ast.Proc | None = None  # LHS reduction proc (collision then-body)


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
    i0, i1 = spec.ct_key_idx
    xdp = [f"xdp{i}" for i in range(len(spec.l_challenger_key_fields))]

    l_fe = [f"l{n}" for n in _field_elim_names(spec.l_component_fields)]
    r_fe = [f"r{n}" for n in _field_elim_names(spec.r_component_fields)]

    # -- invariant -----------------------------------------------------------
    def _s2(ref: str) -> str:
        return ref + "{2}"

    rg0 = spec.r_component_fields[i0]
    rg1 = spec.r_component_fields[i1]
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
            f"{spec.l_base}.{lg[0]}" "{1}" f" = {lchal}.{ck}" "{1}"
            for lg, ck in zip(spec.l_component_fields, spec.l_challenger_key_fields)
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
        + "".join(f", {lchal}.{ck}" "{1}" for ck in spec.l_challenger_key_fields)
        + f", {ct0}"
        "{1}"
        f", {ct1}"
        "{1}"
        f"; elim* => gp3 {' '.join(xdp)} xc0 xc1.",
        "    exists* (glob "
        f"{hm})"
        "{2}"
        ", kdf_in_0"
        "{2}"
        ", kdf_in_1"
        "{2}"
        "; elim* => gh2 ki0 ki1.",
        f"    wp. call{{2}} ({hm}_evaluate_det gh2 ki1). call{{2}} ({hm}_evaluate_det gh2 ki0).",
        f"    call{{1}} ({spec.pq_module}_decaps_det gp3 {xdp[i1]} xc1.`1). "
        f"call{{1}} ({spec.pq_module}_decaps_det gp3 {xdp[i0]} xc0.`1).",
        "    skip => />; smt().",
    ]

    # -- no-collision else: both are the hybrid predicate. The RHS's extra
    # ``kdf_in_0 <> kdf_in_1`` conjunct is redundant: ``kdf_in_0 = kdf_in_1``
    # forces (encodeciphertext right-slice + injectivity) the two ciphertexts'
    # T-components equal; with the negated LEFT guard (``kdf`` equal =>
    # PQ-components equal) the two full ciphertexts coincide, contradicting
    # ``ct0 <> ct1``. Derive it with an explicit ``have`` chain (smt cannot
    # navigate the 4-deep concat unaided).
    rg0b = spec.r_component_fields[i0]
    rg1b = spec.r_component_fields[i1]
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


def challenge_tactic_hop2_wrapper(  # pylint: disable=too-many-locals,too-many-statements
    spec: Hop2Spec,
) -> list[str] | None:
    """hop_6 both-case-split (``R_PQ_Bind ~ R_KDF``) with a SeededKEMWrapper PQ decaps.

    Like :func:`challenge_tactic_hop2` but both reductions' PQ ``decaps`` is a
    ``SeededKEMWrapper`` (``derivekeypair; inner-decaps``).  The flat-state
    prefixes are ALREADY expanded (single-var tuple + projections), so the generic
    ``_blk_env``/``_peel_stmts`` functionalize them via the inner KEM's
    ``derivekeypair``/``decaps`` det axioms -- but the EC goal must first
    ``inline{i} <wrapper>.decaps <wrapper>.encodesharedsecret`` to expose those
    inner calls (matching the expanded flat state), and the LHS collision
    challenger re-decapsulates through the wrapper too.  Every KDF-input term
    binds the PQ decaps key to the seed-derived ``(ev_derivekeypair seed).`2`` and
    the T encaps key to the recomputed ``ev_exp(ev_generator, dk_T)`` (group T).
    ``spec.l_own_fields`` are the reduction's own PQ-seed + T-scalar fields (in that
    order); ``spec.l_red_proc`` is the LHS reduction proc (collision then-body).
    """
    if spec.l_red_proc is None or not spec.wrapper_expr or not spec.inner_pq_module:
        return None
    if len(spec.l_own_fields) != 2 or len(spec.l_challenger_key_fields) != 1:
        return None
    ct0, ct1 = spec.ct_params
    seed_f, tkey_f = spec.l_own_fields  # PQ seed (decaps key), T scalar
    gm = spec.glob_mods
    gge = [f"gg{i}" for i in range(len(gm))]
    glob_of = dict(zip(gm, gge))
    hm = spec.h_module
    lchal = spec.l_challenger_ref
    wrapper = spec.wrapper_expr
    inner = spec.inner_pq_module
    inner_c = spec.clone_alias.get(inner, inner + "_c")
    t_clone = spec.shape.ev_decaps_t.split(".", 1)[0]
    ck = spec.l_challenger_key_fields[0]  # SAMEKEY single challenger key
    l_len = len([s for s in spec.l_prefix if not isinstance(s, ec_ast.VarDecl)])
    r_len = len([s for s in spec.r_prefix if not isinstance(s, ec_ast.VarDecl)])

    def _wbind(ct: str) -> tuple[str, str, str, str]:
        """KDF-input bindings at ct: seed-derived PQ decaps key, T scalar, the
        recomputed group encaps key (``ev_exp(ev_generator, dk_T)``), ct."""
        pq_key = f"({inner_c}.ev_derivekeypair {spec.r_base}.{seed_f}" "{2}).`2"
        t_key = f"{spec.r_base}.{tkey_f}" "{2}"
        ek = f"({spec.shape.ev_decaps_t} ({t_clone}.ev_generator) {t_key})"
        return (pq_key, t_key, ek, f"{ct}" "{2}")

    kdf0_term = spec.shape.kdf_in(*_wbind(ct0))
    kdf1_term = spec.shape.kdf_in(*_wbind(ct1))

    # -- invariant -----------------------------------------------------------
    inv_terms = (
        [f"{c}" "{1}" f" = {c}" "{2}" for c in spec.ct_params]
        + ["kdf_in_0{1} = kdf_in_0{2}", "kdf_in_1{1} = kdf_in_1{2}"]
        + [f"(glob {m})" "{1}" f" = (glob {m})" "{2}" for m in spec.sync_mods]
        + [f"{spec.l_base}.{seed_f}" "{1}" f" = {lchal}.{ck}" "{1}"]
        + [
            f"{spec.l_base}.{f}" "{1}" f" = {spec.r_base}.{f}" "{2}"
            for f in spec.l_own_fields
        ]
        + ["kdf_in_0" "{2}" f" = {kdf0_term}", "kdf_in_1" "{2}" f" = {kdf1_term}"]
    )
    inv = " /\\ ".join(inv_terms)
    lines = [
        "proof.",
        "  proc.",
        f"  inline{{1}} {wrapper}.decaps {wrapper}.encodesharedsecret.",
        f"  inline{{2}} {wrapper}.decaps {wrapper}.encodesharedsecret.",
        f"  seq {l_len} {r_len} : ({inv}).",
    ]

    # -- prefix functionalization subgoal (both sides, expanded flat state) ---
    own = spec.l_own_fields
    l_fe = [f"lf{i}" for i in range(len(own))]
    r_fe = [f"rf{i}" for i in range(len(own))]
    l_ex = (
        [f"(glob {m})" "{1}" for m in gm]
        + [f"{spec.l_base}.{f}" "{1}" for f in own]
        + [f"{c}" "{1}" for c in spec.ct_params]
        + [f"{spec.r_base}.{f}" "{2}" for f in own]
    )
    l_elim = gge + l_fe + ["lc0", "lc1"] + r_fe
    l_env = _blk_env(
        spec.l_base,
        [own],
        l_fe,
        spec.ct_params,
        ("lc0", "lc1"),
        [s for s in spec.l_prefix if not isinstance(s, ec_ast.VarDecl)],
        spec.clone_alias,
    )
    r_env = _blk_env(
        spec.r_base,
        [own],
        r_fe,
        spec.ct_params,
        ("lc0", "lc1"),
        [s for s in spec.r_prefix if not isinstance(s, ec_ast.VarDecl)],
        spec.clone_alias,
    )
    l_peel = _wp_before_calls(
        _peel_stmts(_drop_leading_assigns(spec.l_prefix), l_env, glob_of, "{1}")
    )
    r_peel = _wp_before_calls(
        _peel_stmts(_drop_leading_assigns(spec.r_prefix), r_env, glob_of, "{2}")
    )
    lines += [
        "  + sp.",
        f"    exists* {', '.join(l_ex)};",
        f"    elim* => {' '.join(l_elim)}.",
        *[f"    {ln}" for ln in r_peel],
        *[f"    {ln}" for ln in l_peel],
        "    skip => />.",
    ]

    # -- outer case: RHS ct-equality guard (H.evaluate only; no wrapper) ------
    lines += [
        f"  case ({ct0}" "{2}" f" = {ct1}" "{2}).",
        "  + rcondt{2} 1; first by auto.",
        "    rcondf{1} 1; first by (auto; smt()).",
        "    exists* (glob "
        f"{hm})"
        "{1}, kdf_in_0{1}, kdf_in_1{1}; elim* => gh ki0 ki1.",
        f"    wp. call{{1}} ({hm}_evaluate_det gh ki1). call{{1}} ({hm}_evaluate_det gh ki0).",
        "    skip => />.",
        "  rcondf{2} 1; first by (auto; smt()).",
        "  inline{2} 1.",
        "  sp.",
    ]

    # -- inner case: LHS PQ-collision guard (wrapper challenger re-decaps) ----
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
        f"    inline{{1}} {wrapper}.decaps.",
        "    sp.",
        f"    exists* (glob {inner})"
        "{1}"
        f", {lchal}.{ck}"
        "{1}"
        f", {ct0}"
        "{1}"
        f", {ct1}"
        "{1}"
        "; elim* => gp3 xsd xc0 xc1.",
        "    exists* (glob "
        f"{hm})"
        "{2}, kdf_in_0{2}, kdf_in_1{2}; elim* => gh2 ki0 ki1.",
        f"    wp. call{{2}} ({hm}_evaluate_det gh2 ki1). call{{2}} ({hm}_evaluate_det gh2 ki0).",
        f"    wp. call{{1}} ({inner}_decaps_det gp3 ({inner_c}.ev_derivekeypair xsd).`2 xc1.`1)."
        f" call{{1}} ({inner}_derivekeypair_det gp3 xsd).",
        f"    wp. call{{1}} ({inner}_decaps_det gp3 ({inner_c}.ev_derivekeypair xsd).`2 xc0.`1)."
        f" call{{1}} ({inner}_derivekeypair_det gp3 xsd).",
        "    skip => />; smt().",
    ]

    # -- no-collision else: both compute the predicate; slice-peel the KDF
    # equality to the T-ciphertext (right slice) + injectivity, at the
    # seed-derived wrapper bindings (PQ leaf = ev_decaps (ev_dkp seed).`2 ct). --
    bind0 = _wbind(ct0)
    bind1 = _wbind(ct1)
    kdf0 = spec.shape.kdf_in(*bind0)
    kdf1 = spec.shape.kdf_in(*bind1)
    peel = slice_peel_to_ect(spec.shape, bind0, bind1)
    lines += [
        "  rcondf{1} 1; first by (auto; smt()).",
        "  exists* (glob "
        f"{hm})"
        "{1}, kdf_in_0{1}, kdf_in_1{1}; elim* => gh ki0 ki1.",
        "  exists* (glob "
        f"{hm})"
        "{2}, kdf_in_0{2}, kdf_in_1{2}; elim* => gh2 ri0 ri1.",
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


def _annot_guard(guard: str, side: str) -> str:
    """Annotate a simple ``a = b`` equality guard with a memory side."""
    parts = guard.split(" = ")
    if len(parts) != 2:
        return f"({guard}){side}"
    return f"{parts[0].strip()}{side} = {parts[1].strip()}{side}"


def _hop2_pk_hkeval(hm: str, side: str, gname: str) -> list[str]:
    """Functionalize one side's two ``H.evaluate(kdf_in_i)`` calls (last = kdf1).
    Assumes a preceding ``wp`` absorbed the trailing result assignment."""
    return [
        f"    exists* (glob {hm})"
        f"{side}"
        ", kdf_in_0"
        f"{side}"
        ", kdf_in_1"
        f"{side}"
        f"; elim* => {gname} {gname}i0 {gname}i1.",
        f"    call{side} ({hm}_evaluate_det {gname} {gname}i1).",
        f"    call{side} ({hm}_evaluate_det {gname} {gname}i0).",
    ]


def _hop2_pk_drop_decaps(spec: Hop2Spec) -> list[str]:
    """Peel the LEFT (inlined) Unbreakable challenger's two dead ``decaps`` --
    glob-preserving, result unused (the challenger returns ``false``). Assumes a
    preceding ``inline{1} 1; sp; wp`` reduced the then-branch to the two calls."""
    pqm = spec.pq_module
    lchal = spec.l_challenger_ref
    ck0, ck1 = spec.l_challenger_key_fields
    ct0, ct1 = spec.ct_params
    return [
        f"    exists* (glob {pqm})"
        "{1}"
        f", {lchal}.{ck0}"
        "{1}"
        f", {lchal}.{ck1}"
        "{1}"
        f", {ct0}"
        "{1}"
        f", {ct1}"
        "{1}"
        "; elim* => gpq bd0 bd1 lcc0 lcc1.",
        f"    call{{1}} ({pqm}_decaps_det gpq bd1 lcc1.`1).",
        f"    call{{1}} ({pqm}_decaps_det gpq bd0 lcc0.`1).",
    ]


def challenge_tactic_hop2_pk(spec: Hop2Spec) -> list[str] | None:
    """Emit the hop_2 tactic for the PK (encaps-key) both-case-split shape.

    ``R_PQ_Bind o Unbreakable`` (LEFT, guards on ``kdf_in_0 = kdf_in_1``) ~
    ``R_KDF o Breakable`` (RIGHT, guards on ``ek0 = ek1``).  No injectivity is
    needed: both results are the SAME boolean ``(kdf0<>kdf1) /\\ H(kdf0)=H(kdf1)
    /\\ (ek0<>ek1)`` (the guards are asymmetric, so a 4-leaf case split relates
    them).  Each leaf opens both ``if``s, drops the LEFT dead challenger decaps,
    functionalizes the live ``H.evaluate``s, and closes with ``smt``.
    """
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
    le0, le1 = spec.l_ek_component_fields
    re0, re1 = spec.r_ek_component_fields
    # distinct component field names (dk 3-tuple + ek 2-tuple share ek_T)
    l_all_fields: list[str] = []
    for grp in (*spec.l_component_fields, *spec.l_ek_component_fields):
        for f in grp:
            if f not in l_all_fields:
                l_all_fields.append(f)
    r_all_fields: list[str] = []
    for grp in (*spec.r_component_fields, *spec.r_ek_component_fields):
        for f in grp:
            if f not in r_all_fields:
                r_all_fields.append(f)
    inv_terms = (
        [f"{c}" "{1}" f" = {c}" "{2}" for c in spec.ct_params]
        + ["kdf_in_0{1} = kdf_in_0{2}", "kdf_in_1{1} = kdf_in_1{2}"]
        + [f"(glob {m})" "{1}" f" = (glob {m})" "{2}" for m in spec.sync_mods]
        + [
            f"{spec.l_base}.{lg0[0]}" "{1}" f" = {lchal}.{ck0}" "{1}",
            f"{spec.l_base}.{lg1[0]}" "{1}" f" = {lchal}.{ck1}" "{1}",
        ]
        + [
            f"{spec.l_base}.{le0[0]}"
            "{1}"
            f" = {lchal}.{spec.l_challenger_ek_fields[0]}"
            "{1}",
            f"{spec.l_base}.{le1[0]}"
            "{1}"
            f" = {lchal}.{spec.l_challenger_ek_fields[1]}"
            "{1}",
        ]
        + [
            f"{spec.l_base}.{lf}" "{1}" f" = {spec.r_base}.{rf}" "{2}"
            for lf, rf in zip(l_all_fields, r_all_fields)
        ]
        + ["kdf_in_0" "{2}" f" = {kdf0_term}", "kdf_in_1" "{2}" f" = {kdf1_term}"]
        + [
            f"ek0" "{2}" f" = ({spec.r_base}.{re0[0]}, {spec.r_base}.{re0[1]})" "{2}",
            f"ek1" "{2}" f" = ({spec.r_base}.{re1[0]}, {spec.r_base}.{re1[1]})" "{2}",
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

    # -- 4-leaf branch: outer case on R's ek guard, inner on L's kdf guard ----
    # After ``seq`` both sides are at their trailing ``if``. Each leaf opens both
    # ``if``s (rcondt/rcondf), then ``sp`` (substitute leading ct projections /
    # ek packings, consume the dead-``false`` side) + ``wp`` (absorb the trailing
    # result assigns on both sides), then peels the live calls (the LEFT dead
    # challenger decaps and/or the ``H.evaluate``s) and closes with ``smt``.
    e_guard = _annot_guard(spec.r_guard, "{2}")  # "ek0{2} = ek1{2}"
    k_guard = _annot_guard(spec.l_guard, "{1}")  # "kdf_in_0{1} = kdf_in_1{1}"
    lines += [f"  case ({e_guard})."]
    # E true: R returns false. L: case on K.
    lines += [
        "  + rcondt{2} 1; first by (auto; smt()).",
        f"    case ({k_guard}).",
        # K true: L then (inline -> dead decaps + false); both false.
        "    + rcondt{1} 1; first by (auto; smt()).",
        "      inline{1} 1. sp. wp.",
        *_hop2_pk_drop_decaps(spec),
        "      skip => />.",
        # K false: L else (H.eval + (h0=h1)&&(ek0<>ek1)); E => L false = R false.
        "    rcondf{1} 1; first by (auto; smt()).",
        "    sp. wp.",
        *_hop2_pk_hkeval(hm, "{1}", "gh"),
        "    skip => />; smt().",
    ]
    # E false: R else forwards to the (un-inlined) KDF Breakable challenger;
    # inline it to expose ``H.evaluate(kdf0)``/``H.evaluate(kdf1)``. L: case on K.
    lines += [
        "  rcondf{2} 1; first by (auto; smt()).",
        "  inline{2} 1.",
        f"  case ({k_guard}).",
        # K true: L then false; R's kdf0<>kdf1 is false (K) => R false.
        "  + rcondt{1} 1; first by (auto; smt()).",
        "    inline{1} 1. sp. wp.",
        *_hop2_pk_drop_decaps(spec),
        *_hop2_pk_hkeval(hm, "{2}", "gh2"),
        "    skip => />; smt().",
        # K false: both = (h0=h1) (both extra conjuncts hold under !E, !K).
        "  rcondf{1} 1; first by (auto; smt()).",
        "  sp. wp.",
        *_hop2_pk_hkeval(hm, "{1}", "gh"),
        *_hop2_pk_hkeval(hm, "{2}", "gh2"),
        "  skip => />; smt().",
        "  qed.",
    ]
    return lines
