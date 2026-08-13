(* Probe: the plain deterministic-plumbing peel across a leg where one side
   carries DEAD copies of state fields.

   Item 4's shape. `Remove Redundant Copies` drops assignments of the form
   `__a18__ <- challenger_ek0;` whose target is never read again. Those lines
   mention a state field, so they change the multiset the peel's field gate
   compares, and the leg declines -- even though the peel's `wp` sweeps a
   dead local away without it ever reaching the goal.

   This asks whether the ordinary bottom-up backbone peel closes when one
   side carries such assignments and the other does not, so that ignoring
   provably-dead assignments when comparing is a sound widening.

   The coupling here is WHOLE-GLOB over identical field names, which is the
   coupling this class was measured to carry. *)

require import AllCore.

type bs.

module type Kem = { proc decaps(k : bs, c : bs) : bs }.
module type Hash = { proc evaluate(x : bs) : bs }.

op comb : bs -> bs -> bs.

(* Left state: four dead copies of fields, in two different peel segments. *)
module S_L (K : Kem, H : Hash) = {
  var dk0 : bs
  var dk1 : bs
  var ek0 : bs
  var ek1 : bs

  proc challenge(ct : bs) : bs = {
    var r0, r1, r2 : bs;
    var a0, a1, a2, a3 : bs;
    a0 <- ek0;
    a1 <- ek1;
    r0 <@ K.decaps(dk0, ct);
    a2 <- ek0;
    a3 <- dk1;
    r1 <@ K.decaps(dk1, ct);
    r2 <@ H.evaluate(comb r0 r1);
    return r2;
  }
}.

(* Right state: the same program with the dead copies removed. *)
module S_R (K : Kem, H : Hash) = {
  var dk0 : bs
  var dk1 : bs
  var ek0 : bs
  var ek1 : bs

  proc challenge(ct : bs) : bs = {
    var r0, r1, r2 : bs;
    r0 <@ K.decaps(dk0, ct);
    r1 <@ K.decaps(dk1, ct);
    r2 <@ H.evaluate(comb r0 r1);
    return r2;
  }
}.

section.

declare module K <: Kem {-S_L, -S_R}.
declare module H <: Hash {-S_L, -S_R, -K}.

lemma dead_assign_peel :
  equiv [ S_L(K, H).challenge ~ S_R(K, H).challenge :
          ={ct} /\ ={glob K} /\ ={glob H}
          /\ S_L.dk0{1} = S_R.dk0{2}
          /\ S_L.dk1{1} = S_R.dk1{2}
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
