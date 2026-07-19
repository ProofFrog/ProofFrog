(* Tripwire: FULL lazy-RO Honest hop_N_pr byequiv, faithful to the real init
   (RO coupling PLUS the abstract-call derivation the init runs after the seed).

   Resolves the open wiring question: after the RO sample coupling
   (`RO_G_RO.h{1}=Honest.hh{2}`, seeds coupled), does the init's downstream
   ABSTRACT-CALL derivation (`derivekeypair(slice y)`, `NG.exp`, ...) close by
   `sim`, or does it need the `(wp; call (_:true))*` backbone peel? The game and
   reduction name their intermediates differently, so this tripwire models an
   abstract module `K` whose `f` both sides call on the coupled `y`. *)

require import AllCore Distr.

type bs.
type key.
type res_t.

op dbs : bs distr.
axiom dbs_ll : is_lossless dbs.

op dfun : (bs -> key) distr.
axiom dfun_ll   : is_lossless dfun.
axiom dfun_fu   : is_funiform dfun.
axiom dfun_full : is_full dfun.

module RO = { var h : bs -> key }.

module Honest = {
  var hh : bs -> key
  proc init() : bs = { var s; hh <$ dfun; s <$ dbs; return s; }
  proc hash(x : bs) : key = { return hh x; }
}.

(* The abstract derivation the KEM/NG calls stand in for. *)
module type K_t = { proc f(y : key) : res_t }.

module Game (K : K_t) = {
  proc initialize() : bs * res_t = {
    var s : bs; var y : key; var r : res_t;
    s <$ dbs;
    y <- RO.h s;             (* PRG = RO lookup *)
    r <@ K.f(y);             (* abstract derivation on y (differently-named locals) *)
    return (s, r);
  }
}.

module Red (K : K_t) = {
  proc initialize() : bs * res_t = {
    var seed : bs; var yv : key; var rr : res_t;
    seed <@ Honest.init();
    yv <@ Honest.hash(seed);
    rr <@ K.f(yv);
    return (seed, rr);
  }
}.

module GameMain (K : K_t) = {
  proc main() : res_t = {
    var s : bs; var r : res_t;
    RO.h <$ dfun;
    (s, r) <@ Game(K).initialize();
    return r;
  }
}.

module RedMain (K : K_t) = {
  proc main() : res_t = {
    var s : bs; var r : res_t;
    RO.h <$ dfun;                 (* DEAD on this side *)
    (s, r) <@ Red(K).initialize();
    return r;
  }
}.

(* The full byequiv the exporter's hop_N_pr must emit: RO coupling + the abstract
   derivation coupled by `call (_: true)` (name-independent), the rest by wp. *)
lemma main_eq (K <: K_t {-RO, -Honest}) &m :
  Pr[GameMain(K).main() @ &m : res = witness] = Pr[RedMain(K).main() @ &m : res = witness].
proof.
  byequiv (_: ={glob K} ==> ={res}) => //.
  proc.
  inline *.
  swap{2} 1 2.                          (* dead RO.h<$ below the live samples *)
  seq 1 1 : (={glob K} /\ RO.h{1} = Honest.hh{2}).
  + rnd; skip => />.
  wp.
  call (_: true).                        (* couple the abstract derivation K.f *)
  wp.
  rnd{2}.                                (* drop the dead RO.h{2} sample *)
  rnd.                                   (* couple the seed samples *)
  skip => />; smt(dfun_ll).
qed.
