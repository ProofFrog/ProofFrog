(* ============================================================ *)
(* Equal-rendered-body leg whose THEN arm branches too --         *)
(* VALIDATED EC TEMPLATE (regression tripwire).                   *)
(*                                                                *)
(* The descent used to recurse only into the else-arm. Measured   *)
(* residue in the corpus: legs that branch on the THEN side as    *)
(* well, at depth three -- and a `then` arm carrying its own `if` *)
(* is not peelable, so the leg declined.                          *)
(*                                                                *)
(* EasyCrypt's bullets NEST, so the then-arm's whole descent sits *)
(* under its own `+`, indented one level. Its guards close from   *)
(* the coupling for the same reason the outer ones do: the two    *)
(* sides run the same program, so the two guards are the same     *)
(* expression.                                                    *)
(*                                                                *)
(* Negative control (validated by mutating THIS file): dropping   *)
(* the challenge-ciphertext coupling is rejected with "cannot     *)
(* prove goal (strict)" at the guard step.                        *)
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
      if (ct = ctStar) {
        a <@ K.decaps(dk_0, ct);
        r <- Some (a);
      } else {
        r <- None;
      }
    } else {
      b <@ K.decaps(dk_1, ct);
      c <@ K.combine(b, b);
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
      if (ct = ctStar) {
        a <@ K.decaps(dk_0, ct);
        r <- Some (a);
      } else {
        r <- None;
      }
    } else {
      b <@ K.decaps(dk_1, ct);
      c <@ K.combine(b, b);
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
  + move => &1 &2 /#.
  (* THEN arm branches too: descend into it, bulleted *)
  + if.
    + move => &1 &2 /#.
    + wp. call (_: true). auto => /#.
    auto => /#.
  (* else arm: the ordinary peel *)
  wp.
  call (_: true).
  wp.
  call (_: true).
  auto => /#.
qed.

end section.
