(* ============================================================ *)
(* TRIPWIRE: field-removal coupling where a DETERMINISTIC        *)
(* ASSIGNMENT sits BETWEEN the two abstract calls.                *)
(* sits BETWEEN the two abstract calls.                           *)
(*                                                                *)
(* The original survivor peel emits consecutive `call (_: true)`  *)
(* with nothing between them and closes with one `auto`. It cannot *)
(* apply here: after the first `call` the last instruction is      *)
(* `x <- r`, an assignment, and EasyCrypt answers "invalid last    *)
(* instruction". The generic backbone peel -- one `wp; call`       *)
(* pair per backbone entry, closed by `auto => /#` -- DOES close   *)
(* it, which is what lets the exporter emit this shape instead of  *)
(* declining it. Pinned here so the tactic and the shape cannot    *)
(* drift apart silently.                                           *)
(* ============================================================== *)

require import AllCore Distr.

type dkey, ct, ss.

module type Scheme = {
  proc keygen() : dkey
  proc decaps(dk : dkey, c : ct) : ss
  proc post(s : ss) : ss
}.

(* Full field set: d0 is a redundant copy of c0. *)
module T4 (K : Scheme) = {
  var c0, c1 : dkey
  var d0 : dkey
  proc initialize() : unit = {
    c0 <@ K.keygen();
    c1 <@ K.keygen();
    d0 <- c0;
  }
  proc decaps0(c : ct) : ss = {
    var r, s, x;
    r <@ K.decaps(d0, c);
    x <- r;
    s <@ K.post(x);
    return s;
  }
}.

(* d0 removed; its read rewritten to the survivor c0. *)
module T5 (K : Scheme) = {
  var c0, c1 : dkey
  proc initialize() : unit = {
    c0 <@ K.keygen();
    c1 <@ K.keygen();
  }
  proc decaps0(c : ct) : ss = {
    var r, s, x;
    r <@ K.decaps(c0, c);
    x <- r;
    s <@ K.post(x);
    return s;
  }
}.

section Probe.

declare module K <: Scheme { -T4, -T5 }.

(* The generic backbone peel: `wp; call` per backbone entry, closed by
   `auto => /#`. If EasyCrypt accepts this, the interleaved-assignment
   shape is recoverable and the exporter can re-aim the peel at it. *)
lemma peel_interleaved :
  equiv [ T5(K).decaps0 ~ T4(K).decaps0 :
          ={c} /\ ={glob K} /\ T5.c0{1} = T4.c0{2} /\ T5.c1{1} = T4.c1{2} /\
          T4.d0{2} = T4.c0{2} ==>
          ={res} /\ ={glob K} /\ T5.c0{1} = T4.c0{2} /\ T5.c1{1} = T4.c1{2} /\
          T4.d0{2} = T4.c0{2} ].
proof.
  proc.
  wp.
  call (_: true).
  wp.
  call (_: true).
  auto => /#.
qed.

(* NEGATIVE CONTROL, PROOF LEVEL (kept commented -- it must NOT compile).
   Dropping the survivor invariant `T4.d0{2} = T4.c0{2}` from the
   precondition leaves the two `K.decaps` arguments unrelatable, and the very
   same tactic then fails with "cannot prove goal (strict)" (verified
   2026-08-10). So the invariant is load-bearing and the lemma above is not a
   vacuous strengthening:

     lemma peel_interleaved_control :
       equiv [ T5(K).decaps0 ~ T4(K).decaps0 :
               ={c} /\ ={glob K} /\ T5.c0{1} = T4.c0{2} /\
               T5.c1{1} = T4.c1{2} ==>
               ={res} /\ ={glob K} /\ T5.c0{1} = T4.c0{2} /\
               T5.c1{1} = T4.c1{2} ].
     proof. proc. wp. call (_: true). wp. call (_: true). auto => /#. qed.
*)

end section Probe.
