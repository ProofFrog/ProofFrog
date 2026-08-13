(* ============================================================ *)
(* Equal-rendered-body leg whose branch arm itself branches --    *)
(* VALIDATED EC TEMPLATE (regression tripwire).                   *)
(*                                                                *)
(* Measured shape of 39 of the 43 such legs: the else-arm is      *)
(* [Assign, Call, If].  Applying `if` a second time straight      *)
(* after the first is REFUTED -- EasyCrypt answers "invalid first *)
(* instruction", because `if` is a FIRST-instruction rule and the *)
(* arm opens with an assignment and a call.                       *)
(*                                                                *)
(* So the arm is split with `seq` first: the leading run gets its *)
(* own goal and is peeled normally, and the residue begins at the *)
(* inner `if`, where the descent recurses. The `seq` invariant is *)
(* the leg's coupling plus equality of every local the leading    *)
(* run BINDS -- exactly what the inner guard and its arms read.   *)
(* Those names are read off the leading statements' targets, not  *)
(* predicted, so nothing depends on EasyCrypt's inline renaming.  *)
(*                                                                *)
(* Negative control (validated by mutating THIS file): dropping   *)
(* one coupling conjunct from the `seq` invariant is rejected     *)
(* with "cannot prove goal (strict)" at the inner guard.          *)
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

module SC0 (K : Scheme) = {
  var dk_0, dk_1 : dkey
  var ctStar : ct_t
  var dead : dkey
  proc decaps(ct : ct_t) : ss option = {
    var r : ss option;
    var t : ct_t;
    var a, b, c : ss;
    if (ct = ctStar) {
      r <- None;
    } else {
      t <- ct;
      a <@ K.decaps(dk_0, t);
      if (t = ctStar) {
        r <- None;
      } else {
        b <@ K.decaps(dk_1, t);
        c <@ K.combine(a, b);
        r <- Some (c);
      }
    }
    return r;
  }
}.

module SC1 (K : Scheme) = {
  var dk_0, dk_1 : dkey
  var ctStar : ct_t
  proc decaps(ct : ct_t) : ss option = {
    var r : ss option;
    var t : ct_t;
    var a, b, c : ss;
    if (ct = ctStar) {
      r <- None;
    } else {
      t <- ct;
      a <@ K.decaps(dk_0, t);
      if (t = ctStar) {
        r <- None;
      } else {
        b <@ K.decaps(dk_1, t);
        c <@ K.combine(a, b);
        r <- Some (c);
      }
    }
    return r;
  }
}.

section.

declare module K <: Scheme {-SC0, -SC1}.

lemma micro_seq_branch :
  equiv [ SC0(K).decaps ~ SC1(K).decaps :
          ={ct} /\ ={glob K}
          /\ SC0.dk_0{1} = SC1.dk_0{2}
          /\ SC0.dk_1{1} = SC1.dk_1{2}
          /\ SC0.ctStar{1} = SC1.ctStar{2}
          ==> ={res} /\ ={glob K}
          /\ SC0.dk_0{1} = SC1.dk_0{2}
          /\ SC0.dk_1{1} = SC1.dk_1{2}
          /\ SC0.ctStar{1} = SC1.ctStar{2} ].
proof.
  proc.
  if.
  + move => &1 &2 /#.
  + auto => /#.
  seq 2 2 : (={t, a} /\ ={glob K}
             /\ SC0.dk_0{1} = SC1.dk_0{2}
             /\ SC0.dk_1{1} = SC1.dk_1{2}
             /\ SC0.ctStar{1} = SC1.ctStar{2}).
  + wp. call (_: true). auto => /#.
  if.
  + move => &1 &2 /#.
  + auto => /#.
  wp.
  call (_: true).
  wp.
  call (_: true).
  auto => /#.
qed.

end section.
