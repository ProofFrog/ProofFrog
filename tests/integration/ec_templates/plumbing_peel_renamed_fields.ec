(* Probe: the plain deterministic-plumbing peel across a leg whose two flat
   states name their fields DIFFERENTLY.

   The peel's field gate compares, per peel segment, the multiset of state
   fields each side mentions -- by NAME. A transform that renames fields
   (`Standardize Field Names`, `Field Lex-Min By RHS`) makes those names
   differ by construction, so the gate declines. But the micro precondition
   of such a leg is FIELD-WISE: it carries the rename as explicit
   `A.f{1} = B.g{2}` conjuncts.

   This asks whether the ordinary bottom-up backbone peel closes when the
   coupling supplies the rename -- i.e. whether reading the fields through
   the coupling before comparing is a sound widening of the gate.

   Shape under test, taken from the measured leg: two abstract calls whose
   key argument is a renamed field, plus a genuine plumbing difference (a
   projection extracted to a local on one side only) so the leg is really in
   the plumbing class and not an identity. *)

require import AllCore.

type bs.
type ct_t = bs * bs.

module type Kem = { proc decaps(k : bs, c : bs) : bs }.
module type Hash = { proc evaluate(x : bs) : bs }.

op comb : bs -> bs -> bs.

(* Left state: fields named as the scheme names them. *)
module S_L (K : Kem, H : Hash) = {
  var dk0_0 : bs
  var dk0_1 : bs

  proc challenge(ct0 : ct_t) : bs = {
    var r0, r1, r2 : bs;
    r0 <@ K.decaps(dk0_0, ct0.`1);
    r1 <@ K.decaps(dk0_1, ct0.`2);
    r2 <@ H.evaluate(comb r0 r1);
    return r2;
  }
}.

(* Right state: SAME program, fields standardized to positional names, and
   one extra deterministic assignment -- the plumbing difference. *)
module S_R (K : Kem, H : Hash) = {
  var field3 : bs
  var field4 : bs

  proc challenge(ct0 : ct_t) : bs = {
    var r0, r1, r2, c0, c1 : bs;
    c0 <- ct0.`1;
    r0 <@ K.decaps(field3, c0);
    c1 <- ct0.`2;
    r1 <@ K.decaps(field4, c1);
    r2 <@ H.evaluate(comb r0 r1);
    return r2;
  }
}.

section.

declare module K <: Kem {-S_L, -S_R}.
declare module H <: Hash {-S_L, -S_R, -K}.

(* The leg, with the field-wise coupling the exporter emits for a rename. *)
lemma rename_peel :
  equiv [ S_L(K, H).challenge ~ S_R(K, H).challenge :
          ={ct0} /\ ={glob K} /\ ={glob H}
          /\ S_L.dk0_0{1} = S_R.field3{2}
          /\ S_L.dk0_1{1} = S_R.field4{2}
          ==> ={res} /\ ={glob K} /\ ={glob H} ].
proof.
  proc.
  wp.
  call (_: true).
  wp.
  call (_: true).
  wp.
  call (_: true).
  auto => /#.
qed.

end section.
