(* ============================================================ *)
(* Multi-oracle ASSUMPTION-HOP reduction-adversary lift.         *)
(*  EC-VALIDATED 2026-06-06 (Docker, exit 0). Regression test:    *)
(*  test_multi_oracle_reduction_adversary_template_compiles.      *)
(*                                                               *)
(* Encodes the shape the exporter's blocker-B fix emits (see       *)
(* proof_frog/export/easycrypt/module_translator.py                *)
(* translate_reduction_adversary, the forward-pk path). Compiling  *)
(* KEMPRF_INDCPA.ec end-to-end confirmed this advances EC past the *)
(* line-1403 reduction-adversary interface rejection.             *)
(* ------------------------------------------------------------ *)
(*                                                               *)
(* THE CLAIM. In the Initialize-lifted multi-oracle design, the   *)
(* assumption game's main() runs the inner Initialize and threads  *)
(* its result into the adversary as `pk`. When the adversary IS a  *)
(* reduction-lift R_Adv (an outer adversary A composed with a      *)
(* reduction R whose Initialize is a PURE FORWARD of               *)
(* challenger.Initialize), R_Adv.distinguish must NOT re-run       *)
(* R.initialize -- that would call C.init a second time, and the   *)
(* restricted adversary interface `Adv(O) = distinguish(pk)        *)
(* {O.challenge}` forbids O.init in distinguish. Instead R_Adv     *)
(* forwards the received `pk` straight to A. This template pins     *)
(* that R_Adv ascribes to the inner adversary type and that        *)
(* Game(C, R_Adv(E, A)) typechecks.                                *)
(* ============================================================ *)

require import AllCore Distr.

type pkey, skey, ss, ct, output.
op dkp : (pkey * skey) distr.
axiom dkp_ll : is_lossless dkp.
op g : ss -> output.

module type Scheme = {
  proc encaps(pk : pkey) : ss * ct
}.

(* Inner == outer oracle shape here: R_KEM forwards Initialize, so the inner
   KEM_INDCPA_MultiChal game and the outer KEM_INDCPA_MultiChal game share the
   pubkey-returning Initialize and a post-init challenge. *)
module type Oracle = {
  proc init() : pkey
  proc challenge() : output * ct
}.

(* The Initialize-lifted, post-init-restricted adversary interface. *)
module type Adv (O : Oracle) = {
  proc distinguish(pk : pkey) : bool {O.challenge}
}.

(* Assumption challenger (the inner game's Real side): holds pk + dead sk. *)
module Chal (E : Scheme) : Oracle = {
  var pk : pkey
  var sk : skey
  proc init() : pkey = { var kp; kp <$ dkp; pk <- kp.`1; sk <- kp.`2; return pk; }
  proc challenge() : output * ct = {
    var rsp; rsp <@ E.encaps(pk); return (g rsp.`1, rsp.`2);
  }
}.

(* The reduction R, played against the inner Oracle, exposing the outer Oracle
   to A. Its init is a PURE FORWARD: it returns C.init() unchanged. *)
module R (E : Scheme, C : Oracle) : Oracle = {
  proc init() : pkey = { var pk; pk <@ C.init(); return pk; }
  proc challenge() : output * ct = {
    var rsp; rsp <@ C.challenge(); return rsp;
  }
}.

(* The reduction adversary. Blocker-B shape: distinguish FORWARDS the received
   pk to A and never calls C.init. So as an adversary against the inner game it
   touches only {C.challenge} (reached transitively through A and R), matching
   the restricted Adv interface. *)
(* No `: Adv` ascription on the 3-param functor itself -- the partial
   application R_Adv(E, A) is the one-Oracle adversary EC checks at the
   Game(...) application site below. This mirrors the exporter, which emits
   `module R_KEM_Adv (K, F, A, C) = { ... }` with no type ascription. *)
module R_Adv (E : Scheme, A : Adv, C : Oracle) = {
  proc distinguish(pk : pkey) : bool = {
    var b; b <@ A(R(E, C)).distinguish(pk); return b;
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

section Test.
declare module E <: Scheme {-Chal}.

(* The load-bearing typecheck: the reduction adversary R_Adv(E, A) is accepted
   as the adversary against the inner assumption game Chal(E). If R_Adv re-ran
   R.initialize (-> C.init), EC would reject this with
   "procedure `distinguish' is not allowed to use C.init". *)
lemma reduction_adv_typechecks (A <: Adv {-Chal, -E}) &m :
  Pr[Game(Chal(E), R_Adv(E, A)).main() @ &m : res] =
  Pr[Game(Chal(E), R_Adv(E, A)).main() @ &m : res].
proof. trivial. qed.

end section Test.
