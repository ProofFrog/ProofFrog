(* Tripwire for _rendered_identity_step's var-block comparison.        *)
(* The route closes a leg with `proc; sim.` when two adjacent flat      *)
(* states render to the same module. It compares the var block SORTED   *)
(* BY NAME rather than in declaration order, because declaration order  *)
(* is not observable: the micros read the var block only through        *)
(* `glob`, and EC orders a `glob` tuple by variable NAME. This file is  *)
(* the machine-checked record of that fact. If EasyCrypt ever REJECTS   *)
(* it, the widening is unsound and must be reverted.                    *)
(* The matching negative control lives in the same test: mutating one   *)
(* body makes EasyCrypt answer `cannot save an incomplete proof`.       *)

require import AllCore.

(* Two modules with the SAME (name, type) variable set and the SAME body,
   differing ONLY in the ORDER the vars are declared in. If EC ordered
   `glob` by declaration order, `glob A` would be `int * bool` and
   `glob B` would be `bool * int` and the equality below would not even
   typecheck. *)

module A = {
  var x : int
  var y : bool
  proc f(n : int) : int = { x <- x + n; y <- true; return x; }
}.

module B = {
  var y : bool
  var x : int
  proc f(n : int) : int = { x <- x + n; y <- true; return x; }
}.

lemma decl_order_is_irrelevant :
  equiv [ A.f ~ B.f :
          ={n} /\ (glob A){1} = (glob B){2} ==>
          ={res} /\ (glob A){1} = (glob B){2} ].
proof.
  proc; sim.
qed.
