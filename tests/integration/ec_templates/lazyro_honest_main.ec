(* Tripwire: the MAIN-experiment byequiv for the lazy-RO Honest hop (wall 3n-CT).

   The real fix is NOT in the per-oracle `hop_0_initialize` lemma (whose emitted post
   `Honest.h{2}=RO_G_RO.h{2}` is unprovable) but in the `hop_N_pr` byequiv that relates
   `Game_step_0.main ~ Game_step_1.main`. Each main samples `RO.h <$ dfun` then calls
   `initialize`. On the REDUCTION side (Game_step_1) that main-start `RO.h <$` is DEAD
   (R_LazyRO_L uses the challenger's `Honest.hh` for every RO query -- HashG forwards to
   `challenger.Hash`), while the challenger's `hh <$ dfun` (sampled inside initialize) is
   the one actually used. So the coupling is `RO.h{1} = hh{2}` (both used, both dfun),
   and side-2's dead `RO.h{2}` sample is dropped.

   This tripwire pins the exact byequiv tactic the exporter's `hop_N_pr` must emit for a
   CGLazyRO Honest hop, replacing the `auto` that (wrongly) couples the two `RO.h` samples
   and then leans on the unprovable per-oracle post. *)

require import AllCore Distr.

type bs.
type key.

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

(* GAME side (Game_step_0): the scheme reads the pre-existing RO.h (PRG = RO lookup). *)
module Game = {
  proc initialize() : bs * key = {
    var s : bs; var y : key;
    s <$ dbs;
    y <- RO.h s;
    return (s, y);
  }
}.

(* REDUCTION side (Game_step_1): derive through the Honest challenger's hh. *)
module Red = {
  proc initialize() : bs * key = {
    var s : bs; var y : key;
    s <@ Honest.init();
    y <@ Honest.hash(s);
    return (s, y);
  }
}.

(* The two experiment mains: sample RO.h up front, then initialize. The `res` is a
   deterministic function of the derived value, so equal derived values => equal res. *)
module GameMain = {
  proc main() : key = {
    var s : bs; var y : key;
    RO.h <$ dfun;
    (s, y) <@ Game.initialize();
    return y;
  }
}.

module RedMain = {
  proc main() : key = {
    var s : bs; var y : key;
    RO.h <$ dfun;                 (* DEAD on this side: Red uses Honest.hh, not RO.h *)
    (s, y) <@ Red.initialize();
    return y;
  }
}.

(* The byequiv the exporter's hop_N_pr must emit for the CGLazyRO Honest hop. *)
lemma main_eq &m :
  Pr[GameMain.main() @ &m : res = witness] = Pr[RedMain.main() @ &m : res = witness].
proof.
  byequiv (_: true ==> ={res}) => //.
  proc.
  inline *.
  (* side 1: RO.h<$dfun; s0<$dbs; y0 <- RO.h s0; ...
     side 2: RO.h<$dfun (DEAD); hh<$dfun; s1<$dbs; s0<-s1; x<-s0; y0<-hh x; ... *)
  swap{2} 1 2.                    (* move side-2's dead RO.h<$ below the two live samples *)
  seq 1 1 : (RO.h{1} = Honest.hh{2}).
  + rnd; skip => />.              (* couple RO.h{1}<$  with  hh{2}<$                 *)
  (* side 1: s0<$; y0<-RO.h s0; ...   side 2: s1<$; RO.h<$(dead); s0<-s1; x<-s0; y0<-hh x; ... *)
  wp.                            (* clear the deterministic tail on both sides       *)
  rnd{2}.                        (* drop side-2's dead RO.h<$ (lossless)             *)
  rnd.                           (* couple side-1 s0<$  with side-2 s1<$             *)
  skip => />; smt(dfun_ll).
qed.
