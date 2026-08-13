(* Probe: work BEFORE a case split, with the two sides' leading runs of
   DIFFERENT lengths.

   Measured shape of the largest remaining IND-CCA class: an arm (or a whole
   body) is `['Assign','Call','Call','If']` on one side against
   `['Assign','Assign','Call','Call','If']` on the other -- deterministic
   plumbing and abstract calls, THEN a case split. EasyCrypt's `if` is a
   FIRST-instruction rule, so the split cannot be taken until that run is
   peeled off; without the split the tactic is refused outright.

   `seq n m : (I)` splits n statements on the left against m on the right,
   which is what lets the two runs differ in length. This asks what I has to
   be: the leg's coupling, plus equality of the locals the SUFFIX goes on to
   read. The right side binds a local the left does not (`c0`), so I can only
   equate the locals COMMON to both runs -- the one-sided local has to be
   absorbed by `wp` inside the prefix goal, never mentioned in I. *)

require import AllCore.

type bs.
type ct_t = bs * bs.

module type Kem = { proc decaps(k : bs, c : bs) : bs }.
module type Hash = { proc evaluate(x : bs) : bs }.

op comb : bs -> bs -> bs.

module S_L (K : Kem, H : Hash) = {
  var dk0 : bs
  var ctStar : bs

  proc decaps(ct : ct_t) : bs = {
    var r0, r1, out : bs;
    r0 <@ K.decaps(dk0, ct.`1);
    r1 <@ H.evaluate(comb r0 ct.`2);
    if (r1 = ctStar) {
      out <- witness;
    } else {
      out <- r1;
    }
    return out;
  }
}.

module S_R (K : Kem, H : Hash) = {
  var dk0 : bs
  var field2 : bs

  proc decaps(ct : ct_t) : bs = {
    var r0, r1, c0, c1, out : bs;
    c0 <- ct.`1;
    r0 <@ K.decaps(dk0, c0);
    c1 <- comb r0 ct.`2;
    r1 <@ H.evaluate(c1);
    if (r1 = field2) {
      out <- witness;
    } else {
      out <- r1;
    }
    return out;
  }
}.

section.

declare module K <: Kem {-S_L, -S_R}.
declare module H <: Hash {-S_L, -S_R, -K}.

lemma leading_run_split :
  equiv [ S_L(K, H).decaps ~ S_R(K, H).decaps :
          ={ct} /\ ={glob K} /\ ={glob H}
          /\ S_L.dk0{1} = S_R.dk0{2}
          /\ S_L.ctStar{1} = S_R.field2{2}
          ==> ={res} /\ ={glob K} /\ ={glob H} ].
proof.
  proc.
  seq 2 4 : (={r0, r1} /\ ={glob K} /\ ={glob H}
             /\ S_L.dk0{1} = S_R.dk0{2}
             /\ S_L.ctStar{1} = S_R.field2{2}).
  + wp.
    call (_: true).
    wp.
    call (_: true).
    auto => /#.
  + if.
    + move => &1 &2 /#.
    + auto => /#.
    + auto => /#.
qed.

end section.
