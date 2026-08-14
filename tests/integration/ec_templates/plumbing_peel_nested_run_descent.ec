(* EC-VALIDATED TEMPLATE: a case split nested inside an arm that ALSO has work
   before it.

   The sibling template `plumbing_peel_nested_guard_descent.ec` has the inner
   branch as the arm's FIRST instruction, so it never exercises the split path
   one level down. That path peels the inner run with its own `seq n m`, and
   `seq` DISCARDS everything about the prefix except the invariant it is given:
   an inner level that restates only the leg's coupling throws away the
   enclosing run's locals, which are still in scope and still read below.

   The proof body below is EMITTED BY THE SYNTHESIZER -- a lockstep unit test
   asserts they are equal, so the template and the route cannot drift. The
   inner `seq` invariant accumulates `={a}` from the enclosing level; the inner
   else-arm reads `a`. Dropping that one conjunct makes EasyCrypt answer
   *cannot prove goal (strict)*, printing the missing `a{1} = a{2}` (control:
   `.ec-tmp/nestedrun_negctl.ec`). *)

require import AllCore.

type bs.
type ct_t = bs * bs.

module type Kem = { proc decaps(k : bs, c : bs) : bs }.

op f : bs -> bs.
op g : bs -> bs.

module S_L (K : Kem) = {
  var dk0 : bs
  var ctStar_0 : bs
  var ctStar_1 : bs
  var alt : bs

  proc decaps(ct : ct_t) : bs = {
    var a, b, r0, out : bs;
    a <- f ct.`1;
    if (ct = (ctStar_0, ctStar_1)) {
      out <- witness;
    } else {
      b <- g a;
      if (b = alt) {
        r0 <@ K.decaps(dk0, ct.`2);
        out <- r0;
      } else {
        r0 <@ K.decaps(dk0, a);
        out <- r0;
      }
    }
    return out;
  }
}.

module S_R (K : Kem) = {
  var dk0 : bs
  var field2 : bs
  var field4 : bs
  var field6 : bs

  proc decaps(ct : ct_t) : bs = {
    var a, b, r0, out : bs;
    a <- f ct.`1;
    if (ct = (field2, field4)) {
      out <- witness;
    } else {
      b <- g a;
      if (b = field6) {
        r0 <@ K.decaps(dk0, ct.`2);
        out <- r0;
      } else {
        r0 <@ K.decaps(dk0, a);
        out <- r0;
      }
    }
    return out;
  }
}.

section Template.

declare module K <: Kem {-S_L, -S_R}.

lemma nested_run_descent :
  equiv [ S_L(K).decaps ~ S_R(K).decaps :
          ={ct} /\ ={glob K} /\ S_L.dk0{1} = S_R.dk0{2} /\ S_L.ctStar_0{1} = S_R.field2{2} /\ S_L.ctStar_1{1} = S_R.field4{2} /\ S_L.alt{1} = S_R.field6{2}
          ==> ={res} /\ ={glob K} /\ S_L.dk0{1} = S_R.dk0{2} /\ S_L.ctStar_0{1} = S_R.field2{2} /\ S_L.ctStar_1{1} = S_R.field4{2} /\ S_L.alt{1} = S_R.field6{2} ].
proof.
proc.
seq 1 1 : (={a} /\ ={ct} /\ ={glob K} /\ S_L.dk0{1} = S_R.dk0{2} /\ S_L.ctStar_0{1} = S_R.field2{2} /\ S_L.ctStar_1{1} = S_R.field4{2} /\ S_L.alt{1} = S_R.field6{2}).
+ auto => /#.
+ if.
  + move => &1 &2 /#.
  + auto => /#.
  + seq 1 1 : (={b} /\ ={a} /\ ={ct} /\ ={glob K} /\ S_L.dk0{1} = S_R.dk0{2} /\ S_L.ctStar_0{1} = S_R.field2{2} /\ S_L.ctStar_1{1} = S_R.field4{2} /\ S_L.alt{1} = S_R.field6{2}).
    + auto => /#.
    + if.
      + move => &1 &2 /#.
      + wp.
        call (_: true).
        auto => /#.
      + wp.
        call (_: true).
        auto => /#.
qed.

end section Template.
