(* Tripwire + design note for the seedbased-binding LAZY-RO Honest init hop
   (wall 3n-CT / 3l / 3o -- the UNIVERSAL blocker for the CG/CK seedbased binding
   proofs).

   The hop `CGLazyRO*Seeded.Honest compose R_LazyRO_L` relates the game's
   `initialize` (derives keys from the pre-existing RO `RO.h`, read via the
   deterministic PRG `evaluate(s) = RO.h s`) to the reduction's `initialize`, which
   calls the Honest challenger. The Honest challenger SAMPLES A FRESH RO `hh <$ dfun`
   and answers `hash(x) = hh x`. The exporter emits the post `hh{2} = RO.h{2}` -- an
   equality between TWO RIGHT-SIDE globals.

   FINDING: that post is UNPROVABLE as the reduction is emitted, because the
   reduction adversary samples the game RO `RO_G_RO.h <$ dfun` and the challenger's
   `hh <$ dfun` INDEPENDENTLY (see the real export, R_LazyRO_L_Adv). So `hh` and
   `RO.h` are independent uniforms on side {2} -- never equal. The current fixed
   `(wp;call)*` peel then leaves the right's `hh <$` sample unconsumed
   ("right instruction list is not empty").

   FIX DIRECTION (a coordinated ROM transform, NOT a tactic tweak): emit the GAME
   side with an EAGER `RO.h <$ dfun` at this hop (moving the RO sampling to first
   use -- sound iff RO.h is unused before here) AND emit the reduction side TYING
   the challenger's `hh` to `RO.h` (both are the one shared RO). Then the two fresh
   samples couple with a single `rnd` and the derivation aligns. `init_equiv_recipe`
   below is that provable target. Building it means (1) the exporter emitting the
   eager sample + tie, and (2) a synthesizer producing the coupling tactic. *)

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

(* GAME side, AS EMITTED: derive from the pre-existing RO.h (PRG = RO lookup). *)
module Game = {
  proc initialize() : bs * key = {
    var s : bs; var y : key;
    s <$ dbs;
    y <- RO.h s;
    return (s, y);
  }
}.

(* REDUCTION side, AS EMITTED: fresh RO via the Honest challenger; RO.h untouched. *)
module Red = {
  proc initialize() : bs * key = {
    var s : bs; var y : key;
    s <@ Honest.init();
    y <@ Honest.hash(s);
    return (s, y);
  }
}.

(* (A) The coupling AS EMITTED -- UNPROVABLE: `Honest.hh{2}` (fresh) and `RO.h{2}`
   (untouched) are independent, so no tactic establishes their equality. Documents
   the wall; kept as `admit` because it genuinely cannot close. *)
lemma init_equiv_as_emitted :
  equiv [ Game.initialize ~ Red.initialize :
    ={glob RO} ==> ={res} /\ Honest.hh{2} = RO.h{2} ].
proof.
  proc; inline *.
  admit.  (* hh{2} independent of RO.h{2}: unprovable as emitted -- see header *)
qed.

(* (B) The FIX target -- both sides sample the ONE shared RO eagerly and the
   reduction ties the challenger's hh to it. Provable by a single coupled `rnd`.
   This is the shape the ROM transform + synthesizer must produce. *)
module GameEager = {
  proc initialize() : bs * key = {
    var s : bs; var y : key;
    RO.h <$ dfun;
    s <$ dbs;
    y <- RO.h s;
    return (s, y);
  }
}.

module RedTied = {
  proc initialize() : bs * key = {
    var s : bs; var y : key;
    RO.h <$ dfun;
    Honest.hh <- RO.h;
    s <$ dbs;
    y <- RO.h s;
    return (s, y);
  }
}.

lemma init_equiv_recipe :
  equiv [ GameEager.initialize ~ RedTied.initialize :
    true ==> ={res, glob RO} /\ Honest.hh{2} = RO.h{2} ].
proof.
  proc; auto.
qed.
