(* Probe: descend through a case split whose two GUARDS differ, and are equal
   only under the coupling.

   The IND-CCA `decaps` oracle refuses the challenge ciphertext, so its body
   is one case split whose arms both call. A top-level peel cannot reach
   those calls -- EasyCrypt answers "invalid last instruction" -- so the leg
   declines.
   Descending needs the two arms PAIRED, which needs the two guards
   equivalent -- and measured over the family they are never syntactically
   equal: a transform has renamed the fields the guard reads
   (`ct = (ctStar_0, ctStar_1)` against `ct = (field2, field4)`).

   The coupling states that rename. This asks whether `if.` splits such a
   leg -- whether its first goal, the guard equivalence, is dischargeable
   from the coupling, and whether each arm then peels normally despite a
   plumbing difference inside it. *)

require import AllCore.

type bs.
type ct_t = bs * bs.

module type Kem = { proc decaps(k : bs, c : bs) : bs }.
module type Hash = { proc evaluate(x : bs) : bs }.

op comb : bs -> bs -> bs.

(* Left state: the guard reads ctStar_0 / ctStar_1. *)
module S_L (K : Kem, H : Hash) = {
  var dk0 : bs
  var ctStar_0 : bs
  var ctStar_1 : bs

  proc decaps(ct : ct_t) : bs = {
    var r0, r1, out : bs;
    if (ct = (ctStar_0, ctStar_1)) {
      out <- witness;
    } else {
      r0 <@ K.decaps(dk0, ct.`1);
      r1 <@ H.evaluate(comb r0 ct.`2);
      out <- r1;
    }
    return out;
  }
}.

(* Right state: same program, the guard's fields renamed, and a plumbing
   difference inside the else arm. *)
module S_R (K : Kem, H : Hash) = {
  var dk0 : bs
  var field2 : bs
  var field4 : bs

  proc decaps(ct : ct_t) : bs = {
    var r0, r1, c0, out : bs;
    if (ct = (field2, field4)) {
      out <- witness;
    } else {
      c0 <- ct.`1;
      r0 <@ K.decaps(dk0, c0);
      r1 <@ H.evaluate(comb r0 ct.`2);
      out <- r1;
    }
    return out;
  }
}.

section.

declare module K <: Kem {-S_L, -S_R}.
declare module H <: Hash {-S_L, -S_R, -K}.

lemma guard_coupled_descent :
  equiv [ S_L(K, H).decaps ~ S_R(K, H).decaps :
          ={ct} /\ ={glob K} /\ ={glob H}
          /\ S_L.dk0{1} = S_R.dk0{2}
          /\ S_L.ctStar_0{1} = S_R.field2{2}
          /\ S_L.ctStar_1{1} = S_R.field4{2}
          ==> ={res} /\ ={glob K} /\ ={glob H} ].
proof.
  proc.
  if.
  + move => &1 &2 /#.
  + auto => /#.
  + wp.
    call (_: true).
    wp.
    call (_: true).
    auto => /#.
qed.

end section.
