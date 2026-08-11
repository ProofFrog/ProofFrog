(* A REJECTING template: EasyCrypt must REFUSE it, and that is the point.

   An evidence-only micro lemma relates two adjacent flat states under a
   WHOLE-GLOB precondition, `(glob A){1} = (glob B){2}`. Whether that
   statement typechecks depends on something the exporter did not used to
   compare: `glob F(A)` contains `glob A` only when F's body actually CALLS
   A -- EasyCrypt drops unused functor arguments. So two flat states with
   IDENTICAL field lists have different glob TYPES as soon as one of them
   stops calling a parameter, and the lemma statement is ill-typed.

   `matched_usage` below is the control: the same statement between two
   modules that agree on which parameter they call, which EasyCrypt accepts.
   `mismatched_usage` is the shape the exporter emitted, and EasyCrypt
   answers `no matching operator, named `='` -- listing no parameter types at
   all, which is why the message reads like a solver failure rather than a
   typing one.

   Measured as the single cause of the four proofs that evidence-only micro
   emission was breaking: CG_seedbased LEAK_BIND_K_PK / K_CT_DIFFKEY /
   K_CT_SAMEKEY and CK_seedbased LEAK_BIND_K_CT_SAMEKEY, in every case the
   `Inline Multi-Use Pure Expressions` leg of hop 12 whose right-hand state's
   `initialize` no longer calls the KEM parameters. `_micro_pre_well_typed`
   now compares the emitted signature with `_glob_signature` (fields AND used
   parameters, on the whole flat state rather than the oracle projection) and
   drops such a lemma. If EasyCrypt ever accepts the second lemma, that
   filter is over-tight and should be revisited. *)

require import AllCore.

module type S = { proc f() : bool }.

(* Both call the parameter: same glob type. *)
module UsesA (K : S) = {
  proc init() : bool = { var r; r <@ K.f(); return r; }
  proc g() : bool = { return false; }
}.

module UsesB (K : S) = {
  proc init() : bool = { var r; r <@ K.f(); return r; }
  proc g() : bool = { return false; }
}.

(* Same field list (none), but never calls the parameter: smaller glob. *)
module Ignores (K : S) = {
  proc init() : bool = { return witness; }
  proc g() : bool = { return false; }
}.

section Probe.

declare module K <: S.

(* CONTROL -- must be ACCEPTED. If this one fails the template has drifted
   and the rejection below proves nothing about parameter usage. *)
lemma matched_usage :
  equiv [ UsesA(K).g ~ UsesB(K).g :
          (glob UsesA(K)){1} = (glob UsesB(K)){2} ==>
          ={res} /\ (glob UsesA(K)){1} = (glob UsesB(K)){2} ].
proof. proc; sim. qed.

(* TARGET -- must be REJECTED, at the `=` between the two globs. *)
lemma mismatched_usage :
  equiv [ UsesA(K).g ~ Ignores(K).g :
          (glob UsesA(K)){1} = (glob Ignores(K)){2} ==>
          ={res} /\ (glob UsesA(K)){1} = (glob Ignores(K)){2} ].
proof. proc; sim. qed.

end section Probe.
