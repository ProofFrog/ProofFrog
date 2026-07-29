(* Model of the residual goal left by a chain of one-sided
   `call{2} (<M>_<m>_det g a)` peels: at each level a leading conjunction to
   PROVE, then a `forall result glob, (glob = g /\ result = <ev term>) => ...`
   whose quantified variables are PINNED by their equations. Depth 4 here;
   the real DIFFKEY/PK hop_0_challenge goal is ~8. *)
require import AllCore.

type gl.
type va. type vb. type vc. type vd.

op fa : gl -> va.
op fb : va -> vb.
op fc : vb -> vc.
op fd : vc -> vd.

lemma monster (g : gl) :
  (g = g /\ fa g = fa g) &&
  forall (r0 : va) (g0 : gl),
    g0 = g /\ r0 = fa g =>
    (g0 = g /\ fb r0 = fb (fa g)) &&
    forall (r1 : vb) (g1 : gl),
      g1 = g0 /\ r1 = fb (fa g) =>
      (g1 = g /\ fc r1 = fc (fb (fa g))) &&
      forall (r2 : vc) (g2 : gl),
        g2 = g1 /\ r2 = fc (fb (fa g)) =>
        (g2 = g /\ fd r2 = fd (fc (fb (fa g)))) &&
        forall (r3 : vd) (g3 : gl),
          g3 = g2 /\ r3 = fd (fc (fb (fa g))) =>
          r3 = fd (fc (fb (fa g))) /\ g3 = g.
proof.
  (* The split/intro loop closes the PURE shape: at each level prove the leading
     conjunction, then introduce the two pinned binders and substitute. On the
     REAL CFRG hop_0_challenge goal this same tactic does NOT close -- the leaves
     there additionally carry the RO-derived-key coupling terms
     (`slice (RO[dk0]{1})`, `ev_randomscalar (slice ..)`) over ~40-variable
     memory contexts, and the per-level `by smt()` cannot discharge them at that
     size. See the parked-wall entry in the CFRG binding plan: the dissolution is
     to stop GENERATING this shape (functionalize both sides and relate them once)
     rather than to find a bigger hammer for it. *)
  do 4! (split; [ by smt() | move => ? ? ? [-> ->] ]).
  smt().
qed.
