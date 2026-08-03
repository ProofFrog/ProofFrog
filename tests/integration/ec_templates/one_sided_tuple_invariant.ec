(* Tripwire: ONE-SIDED INVARIANT conjuncts in a hop coupling.
 *
 * Every conjunct the exporter's coupling synthesizer emits today is a
 * CROSS-SIDE EQUALITY (`Game.x{1} = Red.y{2}`). The CFRG IND-CCA `_PQ` hops
 * need something it cannot express: a property of ONE side alone.
 *
 * The reduction stores the correctness challenger's returned 5-tuple in a
 * field `corr`, and its `decaps` case-splits -- on the already-encapsulated
 * ciphertext it returns the STORED shared secret `corr.`5` instead of calling
 * `K.decaps`. The game side always calls `K.decaps`. Relating them needs
 *
 *     corr.`5 = ev_decaps corr.`2 corr.`3
 *
 * which is not a relation between the two sides at all.
 *
 * The fact is STRUCTURAL, not an assumption: the challenger's own `compute()`
 * computes its 5th component as `K.decaps(dk, ct)` on exactly the 2nd and 3rd.
 * (The correctness ASSUMPTION is that this challenger and the FromEncaps one
 * differ negligibly; that eps is carried by the assumption hop BETWEEN them,
 * not inside either hop.) So the conjunct needs no new axiom.
 *
 * What this tripwire settles:
 *   1. the init equiv can ESTABLISH the one-sided conjunct (`init_establishes`);
 *   2. the decaps equiv can CONSUME it to close the case split
 *      (`decaps_consumes`);
 *   3. without it the case-split branch is NOT provable (`decaps_without` is
 *      left admitted, with the false residual spelled out).
 *)

require import AllCore Distr.

type ek_t, dk_t, ct_t, ss_t.

(* deterministic value of decaps, the `ev_` form the exporter already emits *)
op ev_decaps : dk_t -> ct_t -> ss_t.

module type SCHEME = {
  proc keygen () : ek_t * dk_t
  proc encaps (ek : ek_t) : ss_t * ct_t
  proc decaps (dk : dk_t, c : ct_t) : ss_t
}.

module type CHAL = {
  proc compute () : ek_t * dk_t * ct_t * ss_t * ss_t
}.

(* The FromDecaps correctness challenger: its 5th component IS decaps of its
   2nd and 3rd. This is the whole source of the invariant. *)
module ChalFromDecaps (K : SCHEME) : CHAL = {
  proc compute () : ek_t * dk_t * ct_t * ss_t * ss_t = {
    var t : ek_t * dk_t;
    var u : ss_t * ct_t;
    var ssd : ss_t;
    t <@ K.keygen();
    u <@ K.encaps(t.`1);
    ssd <@ K.decaps(t.`2, u.`2);
    return (t.`1, t.`2, u.`2, u.`1, ssd);
  }
}.

module G (K : SCHEME) = {
  var dk : dk_t

  proc initialize () : ek_t = {
    var t : ek_t * dk_t;
    var u : ss_t * ct_t;
    t <@ K.keygen();
    dk <- t.`2;
    u <@ K.encaps(t.`1);
    return t.`1;
  }

  proc decaps (c : ct_t) : ss_t = {
    var s : ss_t;
    s <@ K.decaps(dk, c);
    return s;
  }
}.

module R (K : SCHEME, C : CHAL) = {
  var corr : ek_t * dk_t * ct_t * ss_t * ss_t

  proc initialize () : ek_t = {
    corr <@ C.compute();
    return corr.`1;
  }

  proc decaps (c : ct_t) : ss_t = {
    var s : ss_t;
    if (c = corr.`3) {
      s <- corr.`5;               (* stored: NO call *)
    } else {
      s <@ K.decaps(corr.`2, c);
    }
    return s;
  }
}.

(* --- the REAL decaps shape -------------------------------------------------
 * The CFRG `decaps` is richer than `G`/`R` above in two ways that matter:
 *   - an OUTER challenge guard `c = ctStar` present on BOTH sides, so the
 *     case split is nested inside an else-branch rather than at the top;
 *   - a shared DETERMINISTIC tail after the branch (the KDF `H.evaluate`),
 *     so the branch result flows into a further call before the return.
 * Both are exactly the things a tripwire can accidentally omit.
 *)

module type KDF = {
  proc eval (s : ss_t) : ss_t
}.

op ev_eval : ss_t -> ss_t.

module G2 (K : SCHEME, HH : KDF) = {
  var dk : dk_t
  var ctStar : ct_t

  proc decaps (c : ct_t) : ss_t option = {
    var r : ss_t option;
    var s : ss_t;
    var h : ss_t;
    if (c = ctStar) {
      r <- None;
    } else {
      s <@ K.decaps(dk, c);
      h <@ HH.eval(s);
      r <- Some h;
    }
    return r;
  }
}.

module R2 (K : SCHEME, HH : KDF, C : CHAL) = {
  var corr : ek_t * dk_t * ct_t * ss_t * ss_t
  var ctStar : ct_t

  proc decaps (c : ct_t) : ss_t option = {
    var r : ss_t option;
    var s : ss_t;
    var h : ss_t;
    if (c = ctStar) {
      r <- None;
    } else {
      if (c = corr.`3) {
        s <- corr.`5;             (* stored: NO call *)
      } else {
        s <@ K.decaps(corr.`2, c);
      }
      h <@ HH.eval(s);
      r <- Some h;
    }
    return r;
  }
}.

section Main.

declare module K <: SCHEME {-G, -R, -G2, -R2}.

declare module HD <: KDF {-G, -R, -G2, -R2, -K}.

declare axiom K_decaps_det (g : (glob K)) (a : dk_t) (b : ct_t) :
  phoare[ K.decaps :
    (glob K) = g /\ dk = a /\ c = b ==>
    (glob K) = g /\ res = ev_decaps a b ] = 1%r.

(* --- 1. the init equiv ESTABLISHES the one-sided conjunct ----------------
   The exporter's init hop currently proves only `={globs}` plus cross-side
   field equalities. The extra conjunct below is exactly what the build spec
   asks it to add, and it comes straight out of the challenger's body: after
   `inline *`, `corr.`5` is the result of `K.decaps` applied to `corr.`2` and
   `corr.`3`, which the `_det` axiom turns into the `ev_` form. *)
lemma init_establishes :
  equiv [ G(K).initialize ~ R(K, ChalFromDecaps(K)).initialize :
          ={glob K} ==>
          ={res} /\ ={glob K} /\ G.dk{1} = R.corr{2}.`2 /\
          R.corr{2}.`5 = ev_decaps R.corr{2}.`2 R.corr{2}.`3 ].
proof.
proc.
inline R(K, ChalFromDecaps(K)).initialize.
inline ChalFromDecaps(K).compute.
(* Split the SHARED keygen/encaps prefix FIRST. `exists*` freezes at the
   CURRENT judgment's initial memory, so freezing `t`/`u` at the top of the
   procedure would bind them BEFORE the calls that assign them -- the
   freeze-position trap recorded in `pres_drop_freeze_position.ec`. After the
   `seq` the continuation's initial memory is the point just before the
   one-sided decaps, which is where the freeze belongs. *)
seq 3 2 : (={glob K} /\ ={t, u} /\ G.dk{1} = t{1}.`2).
+ call (_: true); wp; call (_: true); skip => />.
(* the one-sided `K.decaps` on {2} is the statement that MAKES the invariant
   true; the det axiom turns its result into the `ev_` form *)
wp.
exists* (glob K){2}, t{2}.`2, u{2}.`2; elim* => g a b.
call{2} (K_decaps_det g a b).
skip => />.
qed.

(* --- 2. the decaps equiv CONSUMES it to close the case split -------------
   The `c = corr.`3` branch has a call on {1} and none on {2}: side 1 computes
   `ev_decaps corr.`2 corr.`3`, side 2 returns the stored `corr.`5`, and the
   carried invariant is precisely what equates them. *)
lemma decaps_consumes :
  equiv [ G(K).decaps ~ R(K, ChalFromDecaps(K)).decaps :
          ={c} /\ ={glob K} /\ G.dk{1} = R.corr{2}.`2 /\
          R.corr{2}.`5 = ev_decaps R.corr{2}.`2 R.corr{2}.`3 ==>
          ={res} /\ ={glob K} ].
proof.
proc.
case (c{2} = R.corr{2}.`3).
+ rcondt{2} 1; first by auto.
  exists* (glob K){1}, G.dk{1}, c{1}; elim* => g a b.
  call{1} (K_decaps_det g a b).
  by auto => /#.
rcondf{2} 1; first by auto.
by call (_: true); auto.
qed.

(* --- 3. WITHOUT the invariant the branch is NOT provable -----------------
   Same statement minus the one-sided conjunct. Left admitted deliberately:
   the residual is `ev_decaps corr.`2 corr.`3 = corr.`5` with nothing in the
   context to discharge it, and `corr` is an arbitrary tuple. This is the
   counterexample that justifies building the conjunct rather than hunting
   for a better decaps tactic. *)
lemma decaps_without :
  equiv [ G(K).decaps ~ R(K, ChalFromDecaps(K)).decaps :
          ={c} /\ ={glob K} /\ G.dk{1} = R.corr{2}.`2 ==>
          ={res} /\ ={glob K} ].
proof.
proc.
case (c{2} = R.corr{2}.`3).
+ rcondt{2} 1; first by auto.
  exists* (glob K){1}, G.dk{1}, c{1}; elim* => g a b.
  call{1} (K_decaps_det g a b).
  auto => />.
  (* residual: ev_decaps R.corr.`2 R.corr.`3 = R.corr.`5 -- unprovable here *)
  admit.
rcondf{2} 1; first by auto.
by call (_: true); auto.
qed.

(* --- 4. the REAL shape: outer guard + shared deterministic tail ----------
   Same invariant, but the case split is nested and its result feeds a further
   call. The extra work over `decaps_consumes` is only structural: `rcondf`
   BOTH sides on the outer guard (it is shared), then the same one-sided det
   drop inside, then the shared tail couples with a plain `call (_: true)`.
   `s{1} = s{2}` must reach that tail, which is exactly what the invariant
   buys -- so the tail is coupled, not re-proved. *)
lemma decaps_real_shape :
  equiv [ G2(K, HD).decaps ~ R2(K, HD, ChalFromDecaps(K)).decaps :
          ={c} /\ ={glob K, glob HD} /\ G2.ctStar{1} = R2.ctStar{2} /\
          G2.dk{1} = R2.corr{2}.`2 /\
          R2.corr{2}.`5 = ev_decaps R2.corr{2}.`2 R2.corr{2}.`3 ==>
          ={res} /\ ={glob K, glob HD} ].
proof.
proc.
case (c{1} = G2.ctStar{1}).
+ rcondt{1} 1; first by auto.
  rcondt{2} 1; first by auto.
  by auto.
rcondf{1} 1; first by auto.
rcondf{2} 1; first by auto.
(* the shared deterministic tail couples once `s` agrees *)
wp.
call (_: true).
(* now the one-sided branch: same invariant as `decaps_consumes` *)
case (c{2} = R2.corr{2}.`3).
+ rcondt{2} 1; first by auto.
  exists* (glob K){1}, G2.dk{1}, c{1}; elim* => g a b.
  call{1} (K_decaps_det g a b).
  by auto => /#.
rcondf{2} 1; first by auto.
by call (_: true); auto.
qed.

end section Main.
