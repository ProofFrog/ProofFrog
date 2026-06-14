require import AllCore Distr.

type sd.
type sd2.
type elem.
type scal.
type ek.
type dk.
type ss.
type ct.
type out.

op dsd : sd distr.
op dsd2 : sd2 distr.
axiom dsd_ll : is_lossless dsd.
axiom dsd2_ll : is_lossless dsd2.

op ev_generator : elem.
op ev_randomscalar : sd -> scal.
op ev_derivekeypair : sd2 -> ek * dk.
op ev_exp : elem -> scal -> elem.
op ev_combine : elem -> elem -> (ss * ct) -> out.

module type Encaps = {
  proc encaps(_ : ek) : ss * ct
}.

(* functionalized twin of state_9 *)
module FL (E : Encaps) = {
  proc compute() : out = {
    var __determ_0__ : elem;
    var seed_E : sd;
    var cq0 : sd2;
    var cq1 : sd;
    var sk_E : scal;
    var _r0 : ek * dk;
    var _tup : ek;
    var _r1 : scal;
    var ek_T : elem;
    var ct_T : elem;
    var _tup_0 : ss * ct;
    var z : out;
    __determ_0__ <- ev_generator;
    seed_E <$ dsd;
    cq0 <$ dsd2;
    cq1 <$ dsd;
    sk_E <- ev_randomscalar seed_E;
    _r0 <- ev_derivekeypair cq0;
    _tup <- _r0.`1;
    _r1 <- ev_randomscalar cq1;
    ek_T <- ev_exp __determ_0__ _r1;
    ct_T <- ev_exp __determ_0__ sk_E;
    _tup_0 <@ E.encaps(_tup);
    z <- ev_combine ek_T ct_T _tup_0;
    return z;
  }
}.

(* functionalized twin of state_10: sample cq1 hoisted, det stmts reordered, _r0/_r1 renamed *)
module FR (E : Encaps) = {
  proc compute() : out = {
    var cq1 : sd;
    var __determ_0__ : elem;
    var seed_E : sd;
    var cq0 : sd2;
    var _r0 : scal;
    var ek_T : elem;
    var sk_E : scal;
    var _r1 : ek * dk;
    var _tup : ek;
    var ct_T : elem;
    var _tup_0 : ss * ct;
    var z : out;
    cq1 <$ dsd;
    __determ_0__ <- ev_generator;
    seed_E <$ dsd;
    cq0 <$ dsd2;
    _r0 <- ev_randomscalar cq1;
    ek_T <- ev_exp __determ_0__ _r0;
    sk_E <- ev_randomscalar seed_E;
    _r1 <- ev_derivekeypair cq0;
    _tup <- _r1.`1;
    ct_T <- ev_exp __determ_0__ sk_E;
    _tup_0 <@ E.encaps(_tup);
    z <- ev_combine ek_T ct_T _tup_0;
    return z;
  }
}.

lemma fl_fr (E <: Encaps) :
  equiv [ FL(E).compute ~ FR(E).compute :
          ={glob E} ==> ={res, glob E} ].
proof.
proc.
swap{1} 4 -2.
wp.
call (_: true).
wp.
rnd.
wp.
rnd.
wp.
rnd.
wp.
skip => /#.
qed.
