(* ============================================================ *)
(* RANDOM-FUNCTION DISTRIBUTION, DERIVED FROM EC's MUniFinFun     *)
(*   -- VALIDATED EC TEMPLATE (regression tripwire), admit-free.  *)
(*                                                               *)
(* The exporter emits, for a game field `RF <- Function<A,B>`, an *)
(* ABSTRACT distribution with three axioms:                       *)
(*                                                               *)
(*   op    dfun_A_to_B : (A -> B) distr.                          *)
(*   axiom dfun_A_to_B_ll   : is_lossless dfun_A_to_B.            *)
(*   axiom dfun_A_to_B_fu   : is_funiform dfun_A_to_B.            *)
(*   axiom dfun_A_to_B_full : is_full     dfun_A_to_B.            *)
(*                                                               *)
(* This file shows all three are DERIVABLE once the op is defined *)
(* as `MUniFinFun.dfun (fun _ => dcodom)`. Two consequences:      *)
(*                                                               *)
(*  1. TCB: three axioms PER random function become lemmas.       *)
(*  2. IND-CCA `hop_7_initialize` needs a fact those three do NOT *)
(*     give -- that applying the function at a POINT is uniform,  *)
(*     independent of the rest (`ss <- rF rest` vs `ss <$ d`).    *)
(*     Bound to `MUniFinFun`, that becomes reachable from         *)
(*     `dfun1E` / `dfunE` / `dfun_dmap` instead of needing a      *)
(*     fourth axiom.                                              *)
(*                                                               *)
(* THREE TRAPS, each cost a round:                                *)
(*  - `FinType.enum_spec` is `count (pred1 x) enum = 1` --        *)
(*    membership AND uniqueness -- so a BitWord clone's `enumP`   *)
(*    alone is too weak; `count_uniq_mem` + `enum_uniq` bridge it.*)
(*  - `with op enum <- e` SUBSTITUTES the operator away, leaving  *)
(*    `FinT.enum` undefined, so a standalone `FinType` clone      *)
(*    cannot then be handed to `theory FinT <- ...`. Realize the  *)
(*    NESTED parameter (`op FinT.enum <- ...`) instead.           *)
(*  - `dfun_funi` needs pointwise uniformity AND pointwise        *)
(*    fullness, not just `dunifin_funi`.                          *)
(*                                                               *)
(* Widths kept SYMBOLIC, as the exporter's are.                   *)
(* ============================================================ *)

require import AllCore Distr List FinType.
require BitWord.

op nd, nc : int.
axiom gt0_nd : 0 < nd.
axiom gt0_nc : 0 < nc.

clone BitWord as WD with op n <- nd proof gt0_n by exact gt0_nd.
clone BitWord as WC with op n <- nc proof gt0_n by exact gt0_nc.

type dom = WD.word.
type codom = WC.word.

op dcodom : codom distr = WC.DWord.dunifin.

(* Clone `MUniFinFun` directly and realize its nested `FinT` parameter, rather
   than building a separate `FinType` first: `with op enum <- e` SUBSTITUTES the
   operator away, so a standalone clone leaves `FinT.enum` undefined and
   `theory FinT <- ...` cannot bind it. The nested-parameter form keeps it an
   operator. *)
clone import MUniFinFun with
  type t <- dom,
  op FinT.enum <- WD.words
  proof FinT.enum_spec.
(* `enum_spec` is `count (pred1 x) enum = 1` -- membership AND uniqueness, so
   `enumP` alone is too weak. `count_uniq_mem` turns the count into
   `b2i (x \in words)`, which `enumP` then settles. *)
realize FinT.enum_spec.
proof. by move=> x; rewrite count_uniq_mem 1:WD.enum_uniq WD.enumP. qed.

(* The exporter's op, DEFINED rather than abstract. *)
op dfun_dom_to_codom : (dom -> codom) distr = dfun (fun _ => dcodom).

(* --- the three emitted axioms, now as LEMMAS ---------------------------- *)

lemma dfun_dom_to_codom_ll : is_lossless dfun_dom_to_codom.
proof. by apply/dfun_ll => x; exact WC.DWord.dunifin_ll. qed.

(* `dfun_funi` needs BOTH pointwise uniformity and pointwise fullness; the
   BitWord clone supplies `dunifin_funi` and `dunifin_fu`, and `funi_uni`
   weakens the first to `is_uniform`. *)
lemma dfun_dom_to_codom_fu : is_funiform dfun_dom_to_codom.
proof.
apply/dfun_funi.
- by move=> x; apply/funi_uni/WC.DWord.dunifin_funi.
by move=> x; exact WC.DWord.dunifin_fu.
qed.

lemma dfun_dom_to_codom_full : is_full dfun_dom_to_codom.
proof. by apply/dfun_fu => x; exact WC.DWord.dunifin_fu. qed.
