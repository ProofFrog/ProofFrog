(* ============================================================ *)
(* Multi-oracle stateful indistinguishability — VALIDATED EC     *)
(* TEMPLATE (regression tripwire).                               *)
(*                                                               *)
(* This is the hand-derived, EasyCrypt-compiling target shape    *)
(* the EasyCrypt exporter must emit for a hop between two         *)
(* adjacent MULTI-ORACLE, STATEFUL games (e.g. KEM_INDCCA's      *)
(* Initialize + Decaps, INDCPA_MultiChal's Initialize +          *)
(* Challenge).  The single-oracle hop_<i> + `call (_: inv);      *)
(* conseq hop_<i>` pattern discharges only one oracle.           *)
(*                                                               *)
(* The four load-bearing ideas:                                  *)
(*  1. Initialize is LIFTED into the game wrapper's main(); its  *)
(*     result is passed to the adversary as an argument.  The    *)
(*     adversary is given ONLY the post-init oracles.  This is   *)
(*     what makes the state-coupling invariant establishable     *)
(*     before the adversary runs (coupling it in the byequiv     *)
(*     precondition instead yields an unprovable single-memory   *)
(*     side goal GL.k{m} = GR.k{m}).                             *)
(*  2. The relational invariant couples the two games' module    *)
(*     state: (glob GL){1} = (glob GR){2} (well-formed when the  *)
(*     two adjacent games have structurally identical globals).  *)
(*  3. One per-oracle equiv lemma each: hop_init establishes the *)
(*     coupling from `true`; each post-init oracle preserves it. *)
(*  4. The Pr lemma: byequiv => //; proc; call (_: COUPLING);    *)
(*     one `conseq hop_<oracle>` per post-init oracle (in module *)
(*     -type declaration order); then `call hop_init; auto`.     *)
(* ============================================================ *)

require import AllCore Distr.

type key, input, output, pubkey.
op dkey : key distr.
axiom dkey_ll : is_lossless dkey.
op f : key -> input -> output.
op pk_of : key -> pubkey.

module type Oracle = {
  proc init() : pubkey
  proc eval(x : input) : output
  proc chk(x : input) : bool
}.

(* Adversary receives the init result as input; only post-init oracles. *)
module type Adv (O : Oracle) = {
  proc distinguish(pk : pubkey) : bool {O.eval, O.chk}
}.

module GL : Oracle = {
  var k : key
  proc init() : pubkey = { k <$ dkey; return pk_of k; }
  proc eval(x : input) : output = { return f k x; }
  proc chk(x : input) : bool = { return f k x = f k x; }
}.

module GR : Oracle = {
  var k : key
  proc init() : pubkey = { k <$ dkey; return pk_of k; }
  proc eval(x : input) : output = { return f k x; }
  proc chk(x : input) : bool = { return f k x = f k x; }
}.

module Game (O : Oracle, A : Adv) = {
  proc main() : bool = {
    var b : bool;
    var pk : pubkey;
    pk <@ O.init();
    b <@ A(O).distinguish(pk);
    return b;
  }
}.

lemma hop_init :
  equiv [ GL.init ~ GR.init :
    true ==> ={res} /\ (glob GL){1} = (glob GR){2} ].
proof. proc; auto. qed.

lemma hop_eval :
  equiv [ GL.eval ~ GR.eval :
    ={x} /\ (glob GL){1} = (glob GR){2}
    ==> ={res} /\ (glob GL){1} = (glob GR){2} ].
proof. proc; auto. qed.

lemma hop_chk :
  equiv [ GL.chk ~ GR.chk :
    ={x} /\ (glob GL){1} = (glob GR){2}
    ==> ={res} /\ (glob GL){1} = (glob GR){2} ].
proof. proc; auto. qed.

lemma main_eq (A <: Adv {-GL, -GR}) &m :
  Pr[Game(GL, A).main() @ &m : res] = Pr[Game(GR, A).main() @ &m : res].
proof.
byequiv (_: ={glob A} ==> ={res}) => //.
proc.
call (_: (glob GL){1} = (glob GR){2}).
+ conseq hop_eval.
+ conseq hop_chk.
call hop_init.
auto.
qed.
