(* ============================================================ *)
(* Equal-rendered-body leg, peeled THROUGH a branch --            *)
(* VALIDATED EC TEMPLATE (regression tripwire).                   *)
(*                                                                *)
(* The two sides run the SAME program while their two states      *)
(* differ only in the field set, so the coupling is field-wise    *)
(* and neither equal-body row can take the leg:                   *)
(* _rendered_identity_step compares whole MODULES (var block      *)
(* included) and _plain_plumbing_peel_step requires the bodies to *)
(* DIFFER. _equal_rendered_body_peel takes it.                    *)
(*                                                                *)
(* A top-level backbone peel cannot reach the calls, which sit    *)
(* under the else-arm, so the tactic descends: `if` on an equiv   *)
(* goal yields the guards' equivalence, the then pair and the     *)
(* else pair, in that order. The two sides being the same program *)
(* makes the two guards the same expression, so the first goal    *)
(* closes from the coupling alone.                                *)
(*                                                                *)
(* Negative control (validated by mutating THIS file): dropping   *)
(* the challenge-ciphertext coupling from the precondition makes  *)
(* EasyCrypt reject at the guard step with "cannot prove goal     *)
(* (strict)".                                                     *)
(*                                                                *)
(* REFUTED, do not retry: a SECOND `if` applied straight after    *)
(* this one, for the measured 39 legs whose else-arm is           *)
(* [Assign, Call, If]. EasyCrypt answers "invalid first           *)
(* instruction" -- `if` is a first-instruction rule and the arm   *)
(* opens with a deterministic assignment and a call. That case    *)
(* needs a `seq` split whose invariant relates the arm's locals.  *)
(*                                                                *)
(* The tactic text is asserted in lockstep with the synthesizer   *)
(* by tests/unit/export/test_equal_body_branch_peel.py.           *)
(* ============================================================ *)

require import AllCore Distr.

type dkey, ct_t, ss.

module type Scheme = {
  proc keygen() : dkey
  proc decaps(dk : dkey, c : ct_t) : ss
  proc combine(a : ss, b : ss) : ss
}.

module SB0 (K : Scheme) = {
  var dk_0, dk_1 : dkey
  var ctStar : ct_t
  var dead : dkey
  proc decaps(ct : ct_t) : ss option = {
    var r : ss option;
    var a, b, c : ss;
    if (ct = ctStar) {
      r <- None;
    } else {
      a <@ K.decaps(dk_0, ct);
      b <@ K.decaps(dk_1, ct);
      c <@ K.combine(a, b);
      r <- Some (c);
    }
    return r;
  }
}.

(* Same program; the state has lost the dead field. *)
module SB1 (K : Scheme) = {
  var dk_0, dk_1 : dkey
  var ctStar : ct_t
  proc decaps(ct : ct_t) : ss option = {
    var r : ss option;
    var a, b, c : ss;
    if (ct = ctStar) {
      r <- None;
    } else {
      a <@ K.decaps(dk_0, ct);
      b <@ K.decaps(dk_1, ct);
      c <@ K.combine(a, b);
      r <- Some (c);
    }
    return r;
  }
}.

section.

declare module K <: Scheme {-SB0, -SB1}.

lemma micro_branch :
  equiv [ SB0(K).decaps ~ SB1(K).decaps :
          ={ct} /\ ={glob K}
          /\ SB0.dk_0{1} = SB1.dk_0{2}
          /\ SB0.dk_1{1} = SB1.dk_1{2}
          /\ SB0.ctStar{1} = SB1.ctStar{2}
          ==> ={res} /\ ={glob K}
          /\ SB0.dk_0{1} = SB1.dk_0{2}
          /\ SB0.dk_1{1} = SB1.dk_1{2}
          /\ SB0.ctStar{1} = SB1.ctStar{2} ].
proof.
  proc.
  if.
  (* guard equivalence *)
  + move => &1 &2 /#.
  (* then-branch: no calls *)
  + auto => /#.
  (* else-branch: the ordinary backbone peel *)
  wp.
  call (_: true).
  wp.
  call (_: true).
  wp.
  call (_: true).
  auto => /#.
qed.

end section.
