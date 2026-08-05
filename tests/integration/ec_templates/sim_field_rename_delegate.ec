(* TRIPWIRE for `chain_emitter._synth_sim_field_rename`.

   Companion to `sim_field_rename.ec`, which already pins the half of the story
   that is easy to get wrong in the other direction: `proc; sim` DOES relate two
   structurally identical modules whose FIELDS have different names. `sim` is
   not blind to differently-owned globals -- `Mpv2.of_form`/`needed_eq` accept
   any `pv{1} = pv{2}` pair, so a coupling written `GameR.ctStar{2} =
   RedL.ctStar{1}` drives it directly.

   THIS FILE PINS WHAT ACTUALLY DEFEATS `sim` ON THE KDF-PRF HOPS: not the
   rename, but a difference in expression SHAPE that `inline *` manufactures.
   The reduction reaches the random function through a DELEGATE module, so

       v <@ Chal.lookup(lbl)     inlines to    x <- lbl; v <- Chal.rF x

   while the game has already folded the same step to `r <- Some (GameR.rF lbl)`.
   EC's `s_eqobs_in` then tries `add_eqs (Some v) (Some (rF lbl))`, hits `Evar`
   against `Eapp`, and raises `EqObsInError` -- which `t_eqobs_inS` does not
   catch, so it surfaces as an INTERNAL ANOMALY rather than a failed tactic.
   (That anomaly is why the sibling `_synth_structural_if_peel` declines an
   arrow-typed differing field. It is a route mismatch, not a soundness guard.)

   THE FIX. Both sides of that mismatch are pure assignments, so a leading `wp`
   absorbs them whatever their length and leaves the lock-step abstract calls
   for `sim`. Hence the leaf `wp; sim` -- and `auto` for a call-free branch,
   where after `wp` the post is no longer an equality set and `sim` would fail
   with "cannot infer the set of equalities".

   THE INDEX HAZARD this pins. The exporter computes the peel from the FLAT
   states, where the delegate call is already folded to ONE assignment, but the
   tactic runs after `inline *`, where it is TWO. A `seq n n` split whose prefix
   contained that statement would be off by one, so the route declines when a
   `seq` prefix mentions a delegate-owned field. Here the delegate call sits
   inside the inner `then`, below every split point -- the layout the gate
   admits. *)

require import AllCore Distr.

type inp, out, ct_t.

module type Absr = {
  proc get () : inp
}.

(* The delegate the reduction forwards to: it holds the random function. *)
module Chal = {
  var rF : inp -> out

  proc lookup (x : inp) : out = {
    return rF x;
  }
}.

(* LEFT: reduction. Owns ctStar/kem_ct; reaches rF through Chal.lookup. *)
module RedL (A : Absr) = {
  var ctStar : ct_t
  var kem_ct : ct_t

  proc decaps (ct : ct_t) : out option = {
    var r : out option;
    var lbl : inp;
    var v : out;

    if (ct = ctStar) {
      r <- None;
    } else {
      lbl <@ A.get();
      if (ct = kem_ct) {
        v <@ Chal.lookup(lbl);
        r <- Some v;
      } else {
        r <- None;
      }
    }
    return r;
  }
}.

(* RIGHT: game. Same body, its OWN field names, rF applied inline. *)
module GameR (A : Absr) = {
  var rF : inp -> out
  var ctStar : ct_t
  var kem_ct : ct_t

  proc decaps (ct : ct_t) : out option = {
    var r : out option;
    var lbl : inp;

    if (ct = ctStar) {
      r <- None;
    } else {
      lbl <@ A.get();
      if (ct = kem_ct) {
        r <- Some (rF lbl);
      } else {
        r <- None;
      }
    }
    return r;
  }
}.

(* The emitted tactic, in exactly the shape `_synth_sim_field_rename` builds:
     proc. inline *. <if-tree peel with `wp; sim` / `auto` leaves> qed.

   Both leaf kinds are exercised: the two call-free branches take `auto`, the
   delegate branch takes `wp; sim`. *)
lemma sim_field_rename_delegate (A <: Absr {-Chal, -RedL, -GameR}) :
  equiv [ RedL(A).decaps ~ GameR(A).decaps :
          ={ct} /\ ={glob A} /\
          GameR.ctStar{2} = RedL.ctStar{1} /\
          GameR.kem_ct{2} = RedL.kem_ct{1} /\
          GameR.rF{2} = Chal.rF{1}
          ==>
          ={res} /\ ={glob A} /\
          GameR.ctStar{2} = RedL.ctStar{1} /\
          GameR.kem_ct{2} = RedL.kem_ct{1} /\
          GameR.rF{2} = Chal.rF{1} ].
proof.
proc.
inline *.
if; 1: smt().
auto.
seq 1 1 : (#pre /\ ={lbl}).
wp; call (_: true).
wp; skip => /#.
if; 1: smt().
wp; sim.
auto.
qed.
