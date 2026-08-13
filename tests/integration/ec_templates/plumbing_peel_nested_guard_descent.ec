(* Probe: a case split NESTED inside a branch arm.

   The coupled-guard descent pairs the two top-level branches and peels each
   arm. Measured over the IND-CCA family, 330 of the 424 branch-blocked legs
   have an arm that BRANCHES AGAIN, so that arm is not peelable and the row
   declines. Descending needs to recurse: pair the inner split too, under
   the outer arm's bullet.

   This asks whether EasyCrypt's bullets nest the way the recursion needs --
   whether an inner `if.` inside an outer bullet yields its own three goals,
   and whether the inner guards are still dischargeable from the same
   coupling after the outer split has been taken.

   Both levels rename their guard fields, which is the measured shape. *)

require import AllCore.

type bs.
type ct_t = bs * bs.

module type Kem = { proc decaps(k : bs, c : bs) : bs }.
module type Hash = { proc evaluate(x : bs) : bs }.

op comb : bs -> bs -> bs.

module S_L (K : Kem, H : Hash) = {
  var dk0 : bs
  var ctStar_0 : bs
  var ctStar_1 : bs
  var alt : bs

  proc decaps(ct : ct_t) : bs = {
    var r0, r1, out : bs;
    if (ct = (ctStar_0, ctStar_1)) {
      out <- witness;
    } else {
      if (ct.`1 = alt) {
        r0 <@ K.decaps(dk0, ct.`2);
        out <- r0;
      } else {
        r0 <@ K.decaps(dk0, ct.`1);
        r1 <@ H.evaluate(comb r0 ct.`2);
        out <- r1;
      }
    }
    return out;
  }
}.

module S_R (K : Kem, H : Hash) = {
  var dk0 : bs
  var field2 : bs
  var field4 : bs
  var field6 : bs

  proc decaps(ct : ct_t) : bs = {
    var r0, r1, c0, out : bs;
    if (ct = (field2, field4)) {
      out <- witness;
    } else {
      if (ct.`1 = field6) {
        r0 <@ K.decaps(dk0, ct.`2);
        out <- r0;
      } else {
        c0 <- ct.`1;
        r0 <@ K.decaps(dk0, c0);
        r1 <@ H.evaluate(comb r0 ct.`2);
        out <- r1;
      }
    }
    return out;
  }
}.

section.

declare module K <: Kem {-S_L, -S_R}.
declare module H <: Hash {-S_L, -S_R, -K}.

lemma nested_guard_descent :
  equiv [ S_L(K, H).decaps ~ S_R(K, H).decaps :
          ={ct} /\ ={glob K} /\ ={glob H}
          /\ S_L.dk0{1} = S_R.dk0{2}
          /\ S_L.ctStar_0{1} = S_R.field2{2}
          /\ S_L.ctStar_1{1} = S_R.field4{2}
          /\ S_L.alt{1} = S_R.field6{2}
          ==> ={res} /\ ={glob K} /\ ={glob H} ].
proof.
  proc.
  if.
  + move => &1 &2 /#.
  + auto => /#.
  + if.
    + move => &1 &2 /#.
    + wp.
      call (_: true).
      auto => /#.
    + wp.
      call (_: true).
      wp.
      call (_: true).
      auto => /#.
qed.

end section.
