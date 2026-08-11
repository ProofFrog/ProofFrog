(* ============================================================ *)
(* Move 6 ISUV calls-alignment walker -- the BRANCH-LOCAL CALL    *)
(* shape it must DECLINE. This file is a REJECTING template: the  *)
(* test that owns it asserts EasyCrypt REFUSES it.                *)
(*                                                                *)
(* The tactic below is the one the walker used to emit here,      *)
(* composed from the very same helpers (_calls_only_align_swaps   *)
(* then _backbone_peel then auto => /#). Both read TOP-LEVEL      *)
(* statements only, so the call inside the trailing `if` is       *)
(* invisible to the backbone (the peel comes out too short) and   *)
(* unreachable by it (`wp` cannot cross an `if` whose branches    *)
(* call). EasyCrypt stops at the first `call` with                *)
(*                                                                *)
(*     invalid last instruction                                   *)
(*                                                                *)
(* Measured on seven binding-proof `challenge` legs whose lowered *)
(* body ends in the binding case-split (e.g.                      *)
(* CG_expanded_LEAK_BIND_K_PK micro_0_challenge_right_28_rev) and *)
(* on the lazy-random-oracle `hash` legs of the three INDCCA_T    *)
(* exports, whose miss branch is a `while` over the table.        *)
(* _isuv_align_step now declines the shape                        *)
(* (_peel_reaches_every_event); the positive tripwire for the     *)
(* walker itself is isuv_align_walk.ec. Unit test:                *)
(* tests/unit/export/test_isuv_align_walk.py.                     *)
(* ============================================================ *)

require import AllCore Distr.

theory K_c.
type bs_lambda.
module type Scheme = {
  proc decaps(dk : bs_lambda, ct : bs_lambda) : bs_lambda
  proc enc(ss : bs_lambda) : bs_lambda
}.
end K_c.
import K_c.
type bs_lambda = K_c.bs_lambda.

section.

module SB (K : K_c.Scheme) = {
  var dk0 : bs_lambda
  var dk1 : bs_lambda
  proc challenge(ct0 : bs_lambda) : bs_lambda = {
    var _r0 : bs_lambda;
    var t : bs_lambda;
    var a0 : bs_lambda;
    var a1 : bs_lambda;
    var out : bs_lambda;
    var _r1 : bool;
    _r0 <- witness;
    t <- ct0;
    a0 <@ K.decaps(dk0, t);
    a1 <@ K.enc(dk1);
    out <- a0;
    _r1 <- false;
    if (a0 = a1) {
      out <@ K.enc(a0);
    }
    if (! _r1) {
      _r0 <- out;
    }
    return _r0;
  }
}.

module SA (K : K_c.Scheme) = {
  var dk0 : bs_lambda
  var dk1 : bs_lambda
  proc challenge(ct0 : bs_lambda) : bs_lambda = {
    var _r0 : bs_lambda;
    var a0 : bs_lambda;
    var a1 : bs_lambda;
    var out : bs_lambda;
    var _r1 : bool;
    _r0 <- witness;
    a0 <@ K.decaps(dk0, ct0);
    a1 <@ K.enc(dk1);
    out <- a0;
    _r1 <- false;
    if (a0 = a1) {
      out <@ K.enc(a0);
    }
    if (! _r1) {
      _r0 <- out;
    }
    return _r0;
  }
}.

declare module K <: K_c.Scheme {-SB, -SA}.

lemma micro_isuv_branch_local_call :
  equiv [ SB(K).challenge ~ SA(K).challenge :
          ={ct0} /\ (glob SB(K)){1} = (glob SA(K)){2} ==> ={res} /\ (glob SB(K)){1} = (glob SA(K)){2} ].
proof.
  proc.
  wp.
  call (_: true).
  wp.
  call (_: true).
  auto => /#.
qed.

end section.
