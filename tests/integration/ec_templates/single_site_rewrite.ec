(* ============================================================ *)
(* Single-expression-site rewrite micros (Phase-2 Move 2) --      *)
(* VALIDATED EC TEMPLATE (regression tripwire).                   *)
(*                                                                *)
(* The two target shapes for a per-transform micro whose flat     *)
(* states are identical except at ONE expression site:            *)
(*                                                                *)
(*  RETURN-site (probe_return_site): the return expression is     *)
(*  rewritten by a provable boolean identity (here Reflexive      *)
(*  Comparison, `(c = c) && P ~ true && P`). Closer: the generic  *)
(*  backbone peel `proc; call (_: true); rnd; skip => /#` -- no   *)
(*  seq needed; row fact families replace `/#` with `smt(facts)`. *)
(*                                                                *)
(*  GUARD-site (probe_guard_site): one top-level if-guard is      *)
(*  rewritten behind an identical statement prefix (the Q1        *)
(*  leg_reflexive_comparison shape, synthetic). Closer:           *)
(*  `proc; seq N N : (<all-locals> /\ <glob coupling>); sim;      *)
(*  if; [smt(<facts>) | sim | sim]`.                              *)
(*                                                                *)
(* Negative controls (validated at derivation time, 2026-08-09,   *)
(* by mutating THIS file; a rejecting lemma cannot live here):    *)
(*  - guard falsified to a non-identity (`if (r = a)` vs          *)
(*    `if (true)`) -> smt() cannot prove guard equality, EC       *)
(*    rejects.                                                    *)
(*  - return falsified (`a <> b` vs `a = b`) -> `skip => /#`      *)
(*    leaves the residual, EC rejects.                            *)
(* Python-side decline mutations are unit-tested with the Move 2  *)
(* gate. If this stops compiling, re-derive the closers before    *)
(* trusting the synthesizer.                                      *)
(* ============================================================ *)

require import AllCore Distr.

type MessageSpace, KeySpace, CiphertextSpace.
op dMessageSpace : MessageSpace distr.

module type Scheme = {
  proc enc(k : KeySpace, m : MessageSpace) : CiphertextSpace
}.

section.

module RS0 (E : Scheme) = {
  var s : KeySpace
  proc foo(a : MessageSpace, b : MessageSpace) : bool = {
    var r : MessageSpace;
    var c : CiphertextSpace;
    r <$ dMessageSpace;
    c <@ E.enc(s, r);
    return (c = c) && (a <> b);
  }
}.

module RS1 (E : Scheme) = {
  var s : KeySpace
  proc foo(a : MessageSpace, b : MessageSpace) : bool = {
    var r : MessageSpace;
    var c : CiphertextSpace;
    r <$ dMessageSpace;
    c <@ E.enc(s, r);
    return true && (a <> b);
  }
}.

module GS0 (E : Scheme) = {
  var s : KeySpace
  proc foo(a : MessageSpace, b : MessageSpace) : CiphertextSpace = {
    var r : MessageSpace;
    var t : CiphertextSpace;
    r <$ dMessageSpace;
    if (r = r) {
      t <@ E.enc(s, r);
    } else {
      t <@ E.enc(s, a);
    }
    return t;
  }
}.

module GS1 (E : Scheme) = {
  var s : KeySpace
  proc foo(a : MessageSpace, b : MessageSpace) : CiphertextSpace = {
    var r : MessageSpace;
    var t : CiphertextSpace;
    r <$ dMessageSpace;
    if (true) {
      t <@ E.enc(s, r);
    } else {
      t <@ E.enc(s, a);
    }
    return t;
  }
}.

declare module E <: Scheme {-RS0, -RS1, -GS0, -GS1}.

lemma probe_return_site :
  equiv [ RS0(E).foo ~ RS1(E).foo :
          ={a, b} /\ (glob RS0(E)){1} = (glob RS1(E)){2} ==>
          ={res} /\ (glob RS0(E)){1} = (glob RS1(E)){2} ].
proof.
proc.
call (_: true).
rnd.
skip => /#.
qed.

lemma probe_guard_site :
  equiv [ GS0(E).foo ~ GS1(E).foo :
          ={a, b} /\ (glob GS0(E)){1} = (glob GS1(E)){2} ==>
          ={res} /\ (glob GS0(E)){1} = (glob GS1(E)){2} ].
proof.
proc.
seq 1 1 : (={r, a, b} /\ (glob GS0(E)){1} = (glob GS1(E)){2}).
sim.
if; [smt() | sim | sim].
qed.

end section.
