(* Tripwire: WHERE a one-sided `_pres` drop may freeze the glob.
 *
 * The init backbone peel drops a dead one-sided call with
 *     exists* (glob X){2}; elim* => g. call{2} (X_pres g).
 * `exists*` binds `g` to the glob in the CURRENT judgment's INITIAL memory --
 * i.e. at the top of the procedure. `call{2} (X_pres g)` then leaves the
 * preceding program owing `(glob X){2} = g` at ITS end. So the idiom is sound
 * only when everything before the dropped call preserves X's glob.
 *
 * That holds when the dropped call sits at the front, or behind deterministic
 * `_det`/`_pres` calls -- which is every case the route was validated on. It
 * FAILS the moment a genuinely stateful call (an abstract `keygen`) precedes
 * the dropped one: the obligation becomes "the glob after keygen equals the
 * glob before it", which is false for an abstract scheme. EasyCrypt reports it
 * not at the `call` but at the final `skip => /#`, as "cannot prove goal
 * (strict)" -- which is why this was mis-read as an smt-capacity problem.
 *
 * `bad` below reproduces the failure shape and is deliberately left as the
 * counterexample (proved by `admit`, with the real obligation spelled out).
 * `good` is the fix: `seq` off the prefix FIRST, so the freeze happens in a
 * judgment whose initial memory really is the point just before the call.
 *)

require import AllCore Distr.

type key, ct, dig.

op dkey : key distr.
axiom dkey_ll : is_lossless dkey.

module type SCHEME = {
  proc keygen () : key          (* stateful: may write its own glob *)
  proc encode (k : key) : dig   (* deterministic + glob preserving *)
}.

module Red (S : SCHEME) = {
  var k : key
  proc initialize () : key = {
    var d : dig;
    k <@ S.keygen();
    d <@ S.encode(k);   (* result DEAD -- nothing below reads `d` *)
    return k;
  }
}.

module Game (S : SCHEME) = {
  var k : key
  proc initialize () : key = {
    k <@ S.keygen();
    return k;
  }
}.

section Main.

declare module S <: SCHEME {-Red, -Game}.

declare axiom S_encode_pres (g : (glob S)) :
  phoare[ S.encode : (glob S) = g ==> (glob S) = g ] = 1%r.

(* --- the WRONG freeze position ------------------------------------------
   `exists*` here binds `gf` to the glob at the TOP of the procedure, so after
   `call{2}` the residual owes `(glob S){1} = gf` AFTER `S.keygen()` has run.
   That is exactly the false obligation; `admit` stands in for it so the file
   still compiles and the shape stays on the record. *)
lemma pres_drop_bad :
  equiv [ Red(S).initialize ~ Game(S).initialize :
          ={glob S} ==> ={res} /\ ={glob S} /\ Red.k{1} = Game.k{2} ].
proof.
proc.
exists* (glob S){1}; elim* => gf.
call{1} (S_encode_pres gf).
wp.
call (_: true).
skip => />.
(* residual: `forall (gL gR : (glob S)), gL = gR => gL = gf` -- i.e. the glob
   AFTER keygen equals the glob BEFORE it. False for an abstract S. *)
admit.
qed.

(* --- the FIX: split the prefix first ------------------------------------
   `seq 1 1` makes the keygen its own judgment. In the continuation the
   initial memory IS the point just before the dead call, so `exists*` freezes
   the right value and the residual obligation is `gf = gf`. *)
lemma pres_drop_good :
  equiv [ Red(S).initialize ~ Game(S).initialize :
          ={glob S} ==> ={res} /\ ={glob S} /\ Red.k{1} = Game.k{2} ].
proof.
proc.
seq 1 1 : (={glob S} /\ Red.k{1} = Game.k{2}).
+ call (_: true); skip => />.
exists* (glob S){1}; elim* => gf.
call{1} (S_encode_pres gf).
skip => />.
qed.

end section Main.
