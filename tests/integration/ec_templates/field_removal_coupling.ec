(* ============================================================ *)
(* Wall-4: FIELD-AWARE coupling for a within-chain               *)
(* "Remove redundant variables for fields" step                  *)
(* -- VALIDATED EC TEMPLATE (regression tripwire).               *)
(*                                                               *)
(* Models the real Step_0R_state_4 -> state_5 boundary of the    *)
(* CFRG Generic LEAK=>HON binding proof (and every binding proof *)
(* whose reduction side carries a redundant decaps-key copy):    *)
(*                                                               *)
(*   state_4 (full):    var challenger_dk0, challenger_dk1,      *)
(*                          dk0, dk1                              *)
(*             init sets dk0 <- challenger_dk0 (redundant copy)  *)
(*             decaps0 reads K.decaps(dk0, ct)                   *)
(*   state_5 (reduced): var challenger_dk0, challenger_dk1       *)
(*             (dk0/dk1 removed; reads rewritten to survivor)    *)
(*             decaps0 reads K.decaps(challenger_dk0, ct)        *)
(*                                                               *)
(* (glob S5){1} = (glob S4){2} is ILL-TYPED (2-tuple vs 4-tuple; *)
(* EC: "no matching operator =") -- this is exporter WALL 4, the *)
(* general non-identical-state coupling-synthesis piece (the     *)
(* S3/M5/P5 problem of the multi-oracle foundation), of which    *)
(* the single-live-field case is multi_oracle_deadfield_coupling.*)
(*                                                               *)
(* THE FIX (load-bearing): replace the whole-glob equality with  *)
(* a FIELD-AWARE coupling --                                     *)
(*   for each field f in BOTH modules (by name = by role, per    *)
(*     the canonicalizer's positional renaming):  L.f{1}=R.f{2}  *)
(*   for each removed-redundant field r (its init has            *)
(*     `r <- rhs` over surviving fields): add the SURVIVOR       *)
(*     INVARIANT r{side} = rhs{side}.                            *)
(* Here:                                                          *)
(*   challenger_dk0{1}=challenger_dk0{2} /\ challenger_dk1 ...   *)
(*   /\ dk0{2}=challenger_dk0{2} /\ dk1{2}=challenger_dk1{2}     *)
(*                                                               *)
(* Lessons pinned:                                               *)
(*  L1. init micro: the survivor invariant is ESTABLISHED --     *)
(*      `wp` reduces dk0{2}=challenger_dk0{2} to reflexivity     *)
(*      (via the `dk0 <- challenger_dk0` assignment), and the    *)
(*      two abstract keygen() calls are coupled name-            *)
(*      independently with `call (_: true)` (NOT ={glob K},      *)
(*      which EC rejects "module K can write K").                *)
(*  L2. decaps micro: the survivor invariant FEEDS the           *)
(*      K.decaps arg equality challenger_dk0{1}=dk0{2}           *)
(*      (= challenger_dk0{1}=challenger_dk0{2}=dk0{2}), so       *)
(*      `call (_: true); auto` closes it.                        *)
(*  L3. NON-VACUITY: dropping the survivor invariant makes the   *)
(*      decaps micro UNPROVABLE (the arg equality is no longer   *)
(*      derivable) -- see the commented `decaps0_micro_bad`      *)
(*      below. So the invariant is required, not a vacuous       *)
(*      strengthening that would let a wrong coupling admit a    *)
(*      false lemma.                                             *)
(* ============================================================ *)

require import AllCore Distr.

type dkey, ct, ss.

module type Scheme = {
  proc keygen() : dkey
  proc decaps(dk : dkey, c : ct) : ss
}.

(* state_4: full field set; dk0/dk1 are redundant copies of challenger_dk*. *)
module S4 (K : Scheme) = {
  var challenger_dk0, challenger_dk1 : dkey
  var dk0, dk1 : dkey
  proc initialize() : unit = {
    challenger_dk0 <@ K.keygen();
    challenger_dk1 <@ K.keygen();
    dk0 <- challenger_dk0;
    dk1 <- challenger_dk1;
  }
  proc decaps0(c : ct) : ss = { var r; r <@ K.decaps(dk0, c); return r; }
  proc decaps1(c : ct) : ss = { var r; r <@ K.decaps(dk1, c); return r; }
}.

(* state_5: dk0/dk1 removed, reads rewritten to the survivor challenger_dk*. *)
module S5 (K : Scheme) = {
  var challenger_dk0, challenger_dk1 : dkey
  proc initialize() : unit = {
    challenger_dk0 <@ K.keygen();
    challenger_dk1 <@ K.keygen();
  }
  proc decaps0(c : ct) : ss = { var r; r <@ K.decaps(challenger_dk0, c); return r; }
  proc decaps1(c : ct) : ss = { var r; r <@ K.decaps(challenger_dk1, c); return r; }
}.

(* L1: init micro ESTABLISHES the full field-aware coupling (survivor incl.). *)
lemma init_micro (K <: Scheme {-S4, -S5}) :
  equiv [ S5(K).initialize ~ S4(K).initialize :
     ={glob K} ==>
       ={glob K}
    /\ S5.challenger_dk0{1} = S4.challenger_dk0{2}
    /\ S5.challenger_dk1{1} = S4.challenger_dk1{2}
    /\ S4.dk0{2} = S4.challenger_dk0{2}
    /\ S4.dk1{2} = S4.challenger_dk1{2} ].
proof. proc. wp. call (_: true). call (_: true). auto. qed.

(* L2: decaps0 micro CLOSES; survivor invariant feeds the K.decaps arg equality. *)
lemma decaps0_micro (K <: Scheme {-S4, -S5}) :
  equiv [ S5(K).decaps0 ~ S4(K).decaps0 :
       ={c, glob K}
    /\ S5.challenger_dk0{1} = S4.challenger_dk0{2}
    /\ S4.dk0{2} = S4.challenger_dk0{2}
       ==>
       ={res, glob K}
    /\ S5.challenger_dk0{1} = S4.challenger_dk0{2}
    /\ S4.dk0{2} = S4.challenger_dk0{2} ].
proof. proc. call (_: true). auto. qed.

(* L3 (non-vacuity): the following is NOT provable -- WITHOUT the survivor
   invariant, arg equality challenger_dk0{1}=dk0{2} is not derivable, and
   `proc; call (_: true); auto` leaves "cannot save an incomplete proof".
   Kept commented so the tripwire compiles; uncomment to reconfirm it fails.

lemma decaps0_micro_bad (K <: Scheme {-S4, -S5}) :
  equiv [ S5(K).decaps0 ~ S4(K).decaps0 :
       ={c, glob K} /\ S5.challenger_dk0{1} = S4.challenger_dk0{2}
       ==> ={res} ].
proof. proc. call (_: true). auto. qed.
*)
