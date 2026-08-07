(* TRIPWIRE -- the IND-CCA `hop_7_initialize` distribution step, in the small.

   One endpoint draws the whole random function and READS it at the challenge
   point; the other draws the function AND an independent challenge value. The
   two are equidistributed because reprogramming one point of a `dfun` draw with
   a fresh sample is again a `dfun` draw (`MUniFinFun.dlet_dfun_update`), so the
   hop's post can relate them by

       <left>.rF{1} = <right>.rF{2}.[x0 <- res{2}]

   which is the WEAKENED conjunct the real hop needs -- full function equality
   there is provably unachievable (it would force the right's independent draw to
   be a function of its own random function).

   The exporter's shape is mirrored: `dfn` is `MUF.dfun (fun _ => dcod)` behind an
   `op [smt_opaque]`, exactly as `type_collector` emits it, so a route derived
   here transfers. `x0` stands in for the challenge KDF input, which in the real
   hop is a deterministic expression over stored fields. *)

require import AllCore Distr List FinType.

type dom, cod.

clone FinType as FT with type t <- dom.

clone MUniFinFun as MUF with
  type t <- dom,
  op FinT.enum <- FT.enum
  proof FinT.enum_spec by exact FT.enum_spec.

op dcod : cod distr.
axiom dcod_ll : is_lossless dcod.

op [smt_opaque] dfn : (dom -> cod) distr = MUF.dfun (fun _ => dcod).

lemma dfn_ll : is_lossless dfn.
proof. by rewrite /dfn; apply/MUF.dfun_ll => x; exact dcod_ll. qed.

(* The challenge point. In the real hop it is a deterministic expression over
   fields both sides store, so it is a CONSTANT of the two programs either way. *)
op x0 : dom.

module L = {
  var rF : dom -> cod

  proc init() : cod = {
    var ss : cod;
    rF <$ dfn;
    ss <- rF x0;
    return ss;
  }
}.

module R = {
  var rF : dom -> cod

  proc init() : cod = {
    var ss : cod;
    rF <$ dfn;
    ss <$ dcod;
    return ss;
  }
}.

(* ------------------------------------------------------------------ *)
(* THE MATHEMATICAL CONTENT OF THE HOP, AND IT IS PROVED.               *)
(*                                                                      *)
(* `rndsem*` folds each side's sampling into ONE draw over pairs:       *)
(*                                                                      *)
(*   left   dmap dfn (fun f => (f, f x0))                               *)
(*   right  dlet dfn (fun g => dmap dcod (fun y => (g, y)))             *)
(*                                                                      *)
(* and the hop's post says the left pair is the right pair PUSHED       *)
(* FORWARD through h (g, y) = (g.[x0 <- y], y). This lemma is that      *)
(* push-forward, i.e. exactly the claim that reprogramming one point of *)
(* a `dfun` draw with a fresh sample is again a `dfun` draw. It is      *)
(* DERIVED from `MUniFinFun.dlet_dfun_update`, so no axiom is involved. *)
(* ------------------------------------------------------------------ *)
lemma fold_eq :
    dlet dfn (fun (g : dom -> cod) => dmap dcod (fun (y : cod) => (g.[x0 <- y], y)))
  = dmap dfn (fun (f : dom -> cod) => (f, f x0)).
proof.
have -> :
    dlet dfn (fun (g : dom -> cod) => dmap dcod (fun (y : cod) => (g.[x0 <- y], y)))
  = dmap (dlet dfn (fun (g : dom -> cod) => dmap dcod (fun (y : cod) => g.[x0 <- y])))
        (fun (f : dom -> cod) => (f, f x0)).
+ rewrite dmap_dlet; apply eq_dlet => // g; rewrite dmap_comp /(\o) /=;
  apply eq_dmap => y /=; rewrite fupdate_eq //.
congr; rewrite /dfn (MUF.dlet_dfun_update (fun (_ : dom) => dcod) x0) /=.
by rewrite (dcod_ll) dscalar1.
qed.

(* ------------------------------------------------------------------ *)
(* THE OPEN STEP, and the obstruction is precise.                       *)
(*                                                                      *)
(* With `fold_eq` proved, what is left is to make EasyCrypt USE it as a *)
(* coupling. `rnd f finv` cannot: it demands a BIJECTION between the two *)
(* supports, and h is not injective -- the right's `g` carries entropy   *)
(* at `x0` that the post discards, so every `g` agreeing with f off `x0` *)
(* maps to the same left point. Measured both argument orders:           *)
(*                                                                      *)
(*   rnd h id  -> obligation `forall r in dRight, r = h r`   (false)     *)
(*   rnd id h  -> obligation `mu1 dRight l = mu1 dLeft l`    (false)     *)
(*                                                                      *)
(* The surplus has to become an EXPLICIT sample before it can be dropped *)
(* one-sided. `MUniFinFun.dfunE_dlet_fix1` is the tool:                  *)
(*                                                                      *)
(*   dfun d = dlet (d x0) (fun v => dfun d.[x0 <- dunit v])              *)
(*                                                                      *)
(* which splits the right's draw into "value at x0" + "the rest". The    *)
(* value at x0 is then genuinely unused and goes by a one-sided `rnd{2}` *)
(* under `dcod_ll`, and what remains is the PINNED form, where the map   *)
(* (f, y) |-> f.[x0 <- y] IS injective (f x0 is known, so f is           *)
(* recoverable) and `dlet_dfun_fupdate_ll` is its distribution identity. *)
(*                                                                      *)
(* NOT YET DERIVED -- this is the next thing to try here, and it is a    *)
(* tripwire question, not an exporter one.                              *)
(* ------------------------------------------------------------------ *)
equiv reprogram : L.init ~ R.init :
  true ==> ={res} /\ L.rF{1} = R.rF{2}.[x0 <- res{2}].
proof.
proc.
rndsem*{1} 0.
rndsem*{2} 0.
admit.
qed.
