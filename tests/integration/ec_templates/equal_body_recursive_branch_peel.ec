(* ============================================================ *)
(* Equal-rendered-body leg, descent recursing THREE levels --     *)
(* VALIDATED EC TEMPLATE (regression tripwire).                   *)
(*                                                                *)
(* Measured residue after the two-level descent: an outer branch; *)
(* then a leading run and an inner branch; then another branch    *)
(* inside that arm. Each level splits its leading run off with    *)
(* `seq` (because `if` is a FIRST-instruction rule and the arm    *)
(* opens with an assignment or a call), closes the guards from    *)
(* the coupling, peels the `then` arm, and descends into `else`.  *)
(*                                                                *)
(* The `seq` invariant ACCUMULATES: each level carries equality   *)
(* of every local bound so far ({t, a}, then {t, a, b}) plus the  *)
(* leg's coupling -- exactly what the next guard and its arms     *)
(* read. Those names come from the statements' own targets, not   *)
(* from predicting EasyCrypt's inline renaming.                   *)
(*                                                                *)
(* Negative control (validated on the two-level sibling): drop a  *)
(* coupling conjunct from a `seq` invariant and EasyCrypt rejects *)
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
        if (t = ctStar) {
          r <- None;
        } else {
          c <@ K.combine(a, b);
          r <- Some (c);
        }
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
        if (t = ctStar) {
          r <- None;
        } else {
          c <@ K.combine(a, b);
          r <- Some (c);
        }
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
  (* third level: another leading run then another branch *)
  seq 1 1 : (={t, a, b} /\ ={glob K}
             /\ SC0.dk_0{1} = SC1.dk_0{2}
             /\ SC0.dk_1{1} = SC1.dk_1{2}
             /\ SC0.ctStar{1} = SC1.ctStar{2}).
  + wp. call (_: true). auto => /#.
  if.
  + move => &1 &2 /#.
  + auto => /#.
  wp.
  call (_: true).
  auto => /#.
qed.

end section.
