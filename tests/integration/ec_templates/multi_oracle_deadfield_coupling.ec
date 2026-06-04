(* ============================================================ *)
(* Multi-oracle LIVE-STATE coupling for NON-identical-state      *)
(* endpoints -- VALIDATED EC TEMPLATE (regression tripwire).     *)
(*                                                               *)
(* Supersedes the identical-state `(glob L){1} = (glob R){2}`    *)
(* coupling of multi_oracle_indist.ec for the realistic case     *)
(* where the two adjacent multi-oracle games have STRUCTURALLY    *)
(* DIFFERENT module state. This is the actual shape of every      *)
(* KEMPRF equivalence hop: the left endpoint is a reduction       *)
(* R(Chal) that delegates to an assumption challenger holding     *)
(* pk + a DEAD sk (INDCPA never reads sk); the right endpoint is  *)
(* a bare intermediate game GR that holds only pk. Their globs    *)
(* differ in shape, so (glob R(Chal)){1} = (glob GR){2} is        *)
(* ILL-TYPED (EC: "no matching operator =") -- this is the M5     *)
(* line-1334 blocker.                                            *)
(*                                                               *)
(* THE FIX (load-bearing): couple on the shared LIVE state only,  *)
(* naming it directly -- here `Chal.pk{1} = GR.pk{2}`. Two        *)
(* lessons this template pins:                                   *)
(*  L1. A field-level coupling on the live state is well-typed    *)
(*      and discharges even when one side carries a dead field    *)
(*      the other lacks. The dead `sk` simply never appears in    *)
(*      the invariant, so the glob-shape mismatch is irrelevant.  *)
(*  L2. For a COMPOSED endpoint (reduction with no own state),    *)
(*      the live state lives in the SUB-MODULE (Chal), and it is  *)
(*      nameable: the lemma is about R(Chal) but the invariant    *)
(*      references `Chal.pk`. `proc; inline *; auto` unfolds the  *)
(*      delegation so the sub-module state is visible.            *)
(*                                                               *)
(* The Pr lemma is unchanged in structure from the identical-     *)
(* state template (byequiv; proc; call (_: COUPLING); conseq      *)
(* hop_<oracle>; call hop_init; auto) -- only the COUPLING string  *)
(* changes from a glob-equality to a live-state field equality.   *)
(* That is the single seam the exporter must compute.            *)
(* ============================================================ *)

require import AllCore Distr.

type pkey, skey, ss, ct, output.
op dkp : (pkey * skey) distr.
axiom dkp_ll : is_lossless dkp.
op denc : pkey -> (ss * ct) distr.
axiom denc_ll : forall pk, is_lossless (denc pk).
op drand : ss distr.
axiom drand_ll : is_lossless drand.
op g : ss -> ct -> output.

module type Oracle = {
  proc init() : pkey
  proc challenge() : output * ct
}.

(* Adversary gets the lifted init result; only the post-init oracle. *)
module type Adv (O : Oracle) = {
  proc distinguish(pk : pkey) : bool {O.challenge}
}.

(* The assumption-challenger: holds pk + DEAD sk. *)
module Chal = {
  var pk : pkey
  var sk : skey
  proc cinit() : pkey = { var kp; kp <$ dkp; pk <- kp.`1; sk <- kp.`2; return pk; }
  proc cchallenge() : ss * ct = { var x; var r; x <$ denc pk; r <$ drand; return (r, x.`2); }
}.

(* The reduction endpoint: NO own state, delegates to Chal. *)
module R : Oracle = {
  proc init() : pkey = { var pk; pk <@ Chal.cinit(); return pk; }
  proc challenge() : output * ct = {
    var rsp; rsp <@ Chal.cchallenge(); return (g rsp.`1 rsp.`2, rsp.`2);
  }
}.

(* The intermediate-game endpoint: only pk. *)
module GR : Oracle = {
  var pk : pkey
  proc init() : pkey = { var kp; kp <$ dkp; pk <- kp.`1; return pk; }
  proc challenge() : output * ct = {
    var x; var r; x <$ denc pk; r <$ drand; return (g r x.`2, x.`2);
  }
}.

module Game (O : Oracle, A : Adv) = {
  proc main() : bool = {
    var b : bool;
    var pk : pkey;
    pk <@ O.init();
    b <@ A(O).distinguish(pk);
    return b;
  }
}.

(* COUPLING = live-state equality, NOT a glob equality. *)
lemma hop_init :
  equiv [ R.init ~ GR.init : true ==> ={res} /\ Chal.pk{1} = GR.pk{2} ].
proof. proc; inline *; auto. qed.

lemma hop_challenge :
  equiv [ R.challenge ~ GR.challenge :
    Chal.pk{1} = GR.pk{2} ==> ={res} /\ Chal.pk{1} = GR.pk{2} ].
proof. proc; inline *; auto. qed.

lemma main_eq (A <: Adv {-Chal, -GR}) &m :
  Pr[Game(R, A).main() @ &m : res] = Pr[Game(GR, A).main() @ &m : res].
proof.
byequiv (_: ={glob A} ==> ={res}) => //.
proc.
call (_: Chal.pk{1} = GR.pk{2}).
+ conseq hop_challenge.
call hop_init.
auto.
qed.
