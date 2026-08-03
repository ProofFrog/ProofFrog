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

module type NG = {
  proc rs (s : key) : key
  proc enc (k : key) : dig
}.

module RedP (S : SCHEME, N : NG) = {
  var k : key
  var d : key
  proc initialize () : key = {
    var s : key;
    s <$ dkey;
    k <@ S.keygen();
    d <$ dkey;
    return d;
  }
}.

module GameP (S : SCHEME, N : NG) = {
  var k : key
  var d : key
  proc initialize () : key = {
    var s : key;
    var dead0 : key;
    var dead1 : dig;
    s <$ dkey;
    k <@ S.keygen();
    dead0 <@ N.rs(k);          (* DEAD: nothing below reads dead0/dead1 *)
    dead1 <@ N.enc(dead0);
    d <$ dkey;
    return d;
  }
}.

section Main.

declare module S <: SCHEME {-Red, -Game, -RedP, -GameP}.

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


(* --- the REAL shape: shared prefix, one-sided DEAD tail, shared suffix ------
 * The CFRG IND-CCA `initialize` hops look like
 *     side 1:  s <$ d ; <shared calls> ;                    ss <$ d
 *     side 2:  s <$ d ; <shared calls> ; <DEAD KDF chain> ; ss <$ d
 * where the dead chain's result is overwritten by the final sample. The
 * exporter peels back-to-front and drops the dead chain one-sided with
 * `_pres`, which puts the freeze at the top of the procedure and leaves the
 * SHARED PREFIX owing "glob unchanged since entry" -- false, because the
 * shared calls are stateful.
 *
 * The fix generalises cleanly, and the reason it does is worth stating: for a
 * DEAD-call drop the hop's own postcondition is established by the prefix
 * alone (that is what dead means), so the `seq` invariant the split needs is
 * already computed -- it is the hop's coupling. No new invariant synthesis.
 *)




declare module N <: NG {-Red, -Game, -RedP, -GameP, -S}.

declare axiom N_rs_pres (g : (glob N)) :
  phoare[ N.rs : (glob N) = g ==> (glob N) = g ] = 1%r.
declare axiom N_enc_pres (g : (glob N)) :
  phoare[ N.enc : (glob N) = g ==> (glob N) = g ] = 1%r.

lemma pres_drop_real_shape :
  equiv [ RedP(S, N).initialize ~ GameP(S, N).initialize :
          ={glob S, glob N} ==>
          ={res} /\ ={glob S, glob N} /\ RedP.k{1} = GameP.k{2} ].
proof.
proc.
(* split the SHARED prefix off first -- invariant is the hop's own coupling,
   which the prefix already establishes because the dropped tail is dead *)
seq 2 2 : (={glob S, glob N} /\ RedP.k{1} = GameP.k{2}).
+ call (_: true); rnd; skip => />.
(* peel the SHARED suffix first (it is the last instruction on both sides),
   then drop the dead tail. The judgment now starts at the split point, so the
   freeze binds the glob just before the dead calls -- which is the whole fix. *)
rnd.
exists* (glob N){2}; elim* => gn.
call{2} (N_enc_pres gn).
call{2} (N_rs_pres gn).
skip => />.
qed.

end section Main.
