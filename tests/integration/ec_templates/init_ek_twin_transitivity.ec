(* Validates the 3-leg transitivity for the single-R ek-derivation init:
   RawGame ~ FG_calls ~ FR_calls ~ RawReduction, outer legs by sim (identical
   modules here; `inline*; sim` in the real export), middle FG_calls~FR_calls
   functionalizes to prove the ek-derivation coupling. Confirms the qa/qd posts
   + the transitivity composition side conditions. *)
require import AllCore Distr.

type seed_t, ek_t.
op dseed : seed_t distr.
axiom dseed_ll : is_lossless dseed.
op ev_derive : seed_t -> ek_t.

module type F_t = { proc derive(s : seed_t) : ek_t }.
axiom F_derive_det (F <: F_t) (g : (glob F)) (a0 : seed_t) :
  phoare[ F.derive : (glob F) = g /\ s = a0 ==> (glob F) = g /\ res = ev_derive a0 ] = 1%r.

(* RawGame + its flat twin FG_calls: same fields (ek,dk), same body. *)
module G0 (F : F_t) = {
  var ek : ek_t
  var dk : seed_t
  proc initialize() : unit = {
    var s : seed_t; var e : ek_t; var t : ek_t * seed_t;
    s <$ dseed; e <@ F.derive(s); t <- (e, s); ek <- t.`1; dk <- t.`2;
  }
}.
module FGc (F : F_t) = {
  var ek : ek_t
  var dk : seed_t
  proc initialize() : unit = {
    var s : seed_t; var e : ek_t; var t : ek_t * seed_t;
    s <$ dseed; e <@ F.derive(s); t <- (e, s); ek <- t.`1; dk <- t.`2;
  }
}.
(* RawReduction + its flat twin FR_calls: fields (ek,seed). *)
module FRc (F : F_t) = {
  var ek : ek_t
  var seed : seed_t
  proc initialize() : unit = {
    var s : seed_t; var e : ek_t; var t : ek_t * seed_t;
    s <$ dseed; e <@ F.derive(s); t <- (e, s); ek <- t.`1; seed <- t.`2;
  }
}.
module R0 (F : F_t) = {
  var ek : ek_t
  var seed : seed_t
  proc initialize() : unit = {
    var s : seed_t; var e : ek_t; var t : ek_t * seed_t;
    s <$ dseed; e <@ F.derive(s); t <- (e, s); ek <- t.`1; seed <- t.`2;
  }
}.

lemma init_trans (F <: F_t {-G0, -FGc, -FRc, -R0}) :
  equiv [ G0(F).initialize ~ R0(F).initialize :
      ={glob F} ==>
        ={glob F}
     /\ G0.ek{1} = R0.ek{2} /\ G0.dk{1} = R0.seed{2}
     /\ (R0.ek{2}, R0.seed{2}) = (ev_derive R0.seed{2}, R0.seed{2}) ].
proof.
  transitivity FGc(F).initialize
    (={glob F} ==> ={glob F} /\ G0.ek{1} = FGc.ek{2} /\ G0.dk{1} = FGc.dk{2} /\ ={res})
    (={glob F} ==> ={glob F} /\ FGc.ek{1} = R0.ek{2} /\ FGc.dk{1} = R0.seed{2}
                /\ (R0.ek{2}, R0.seed{2}) = (ev_derive R0.seed{2}, R0.seed{2}) /\ ={res}).
  + by move => &1 &2 h; exists (glob F){1}; smt().
  + move => &1 &m &2 /=; smt().
  + proc; sim.
  transitivity FRc(F).initialize
    (={glob F} ==> ={glob F} /\ FGc.ek{1} = FRc.ek{2} /\ FGc.dk{1} = FRc.seed{2}
                /\ (FRc.ek{2}, FRc.seed{2}) = (ev_derive FRc.seed{2}, FRc.seed{2}) /\ ={res})
    (={glob F} ==> ={glob F} /\ FRc.ek{1} = R0.ek{2} /\ FRc.seed{1} = R0.seed{2} /\ ={res}).
  + by move => &1 &2 h; exists (glob F){1}; smt().
  + move => &1 &m &2 /=; smt().
  (* MIDDLE FGc ~ FRc: functionalize (controlled names) + prove ek-derivation *)
  + proc.
    seq 1 1 : (={glob F, s}).
    - rnd; skip => />.
    seq 1 1 : (={glob F, s} /\ e{1} = ev_derive s{1} /\ e{2} = ev_derive s{2}).
    - exists* (glob F){1}, s{1}; elim* => g1 a1.
      exists* (glob F){2}, s{2}; elim* => g2 a2.
      call{1} (F_derive_det F g1 a1). call{2} (F_derive_det F g2 a2). skip => />.
    seq 1 1 : (={glob F, s} /\ e{1} = ev_derive s{1} /\ e{2} = ev_derive s{2}
               /\ t{1} = (e{1}, s{1}) /\ t{2} = (e{2}, s{2})).
    - wp; skip => />.
    seq 2 2 : (={glob F, s} /\ e{1} = ev_derive s{1} /\ e{2} = ev_derive s{2}
               /\ t{1} = (e{1}, s{1}) /\ t{2} = (e{2}, s{2})
               /\ FGc.ek{1} = t{1}.`1 /\ FRc.ek{2} = t{2}.`1
               /\ FGc.dk{1} = t{1}.`2 /\ FRc.seed{2} = t{2}.`2).
    - wp; skip => />.
    skip => /#.
  (* leg FR_calls ~ RawReduction *)
  proc; sim.
qed.
