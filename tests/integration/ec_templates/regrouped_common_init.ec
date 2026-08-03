(* Tripwire: the REGROUPED-COMMON `initialize` shape -- the CG_seedbased
 * HON_BIND hop_8 bodies (`R_KDF ~ R_KG_PQ_R`).
 *
 * Both sides run exactly the same per-keypair work:
 *     <pq keygen> ; <t seed> <$ ; <the three-call NG derivation chain>
 * and differ only in HOW IT IS LAID OUT:
 *   - one side batches its n pq keygens up front, then the n t blocks;
 *   - the other is already per-keypair, and reaches its pq keygen through a
 *     challenger whose method is a bare `return K.KeyGen();` -- so after
 *     `inline *` the two backbones are literally the same call sequence.
 *
 * So no coupling law and no determinism hypothesis is needed at all: regroup
 * the batched side per keypair on the UN-INLINED body (the swaps are exact
 * there), inline, and peel the common backbone back-to-front. The peel proves
 * the post's cross-side field equalities from `={res}` at each call.
 *
 * The two swap facts this leans on, both already established elsewhere and
 * re-exercised here: a `<$` sample lifts past an abstract call, and two
 * abstract calls of DIFFERENT declared modules commute (disjoint globs) --
 * refuted the "swap cannot reorder abstract calls" belief in cycle 64.
 *)

require import AllCore Distr.

type ts, pkt, skt, scal, elem.

op dts : ts distr.

module type KEMP = { proc keygen () : pkt * skt }.

module type NGT = {
  proc randomscalar (s : ts) : scal
  proc generator () : elem
  proc exp (b : elem, e : scal) : elem
}.

module type KGE = { proc generate () : pkt * skt }.

(* KeyGenEquiv_FromKeyGen: a bare forward, so an inlined copy is
   [Call, Return] -- two statements, one of them the result assign *)
module KeyGenEquiv_FromKeyGen (K : KEMP) : KGE = {
  proc generate () : pkt * skt = {
    var _r0 : pkt * skt;
    _r0 <@ K.keygen();
    return _r0;
  }
}.

module RedBatched (P : KEMP, NG : NGT) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var dk_T_0, dk_T_1 : scal
  var ek_T_0, ek_T_1 : elem

  proc initialize () : (pkt * elem) * (pkt * elem) = {
    var seed_T_0 : ts;
    var _r0 : elem;
    var seed_T_1 : ts;
    var _r1 : elem;
    pq_keys_0 <@ P.keygen();
    pq_keys_1 <@ P.keygen();
    seed_T_0 <$ dts;
    dk_T_0 <@ NG.randomscalar(seed_T_0);
    _r0 <@ NG.generator();
    ek_T_0 <@ NG.exp(_r0, dk_T_0);
    seed_T_1 <$ dts;
    dk_T_1 <@ NG.randomscalar(seed_T_1);
    _r1 <@ NG.generator();
    ek_T_1 <@ NG.exp(_r1, dk_T_1);
    return ((pq_keys_0.`1, ek_T_0), (pq_keys_1.`1, ek_T_1));
  }
}.

module RedPerKp (P : KEMP, NG : NGT, Challenger : KGE) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var dk_T_0, dk_T_1 : scal
  var ek_T_0, ek_T_1 : elem

  proc initialize () : (pkt * elem) * (pkt * elem) = {
    var seed_T_0 : ts;
    var _r0 : elem;
    var seed_T_1 : ts;
    var _r1 : elem;
    pq_keys_0 <@ Challenger.generate();
    seed_T_0 <$ dts;
    dk_T_0 <@ NG.randomscalar(seed_T_0);
    _r0 <@ NG.generator();
    ek_T_0 <@ NG.exp(_r0, dk_T_0);
    pq_keys_1 <@ Challenger.generate();
    seed_T_1 <$ dts;
    dk_T_1 <@ NG.randomscalar(seed_T_1);
    _r1 <@ NG.generator();
    ek_T_1 <@ NG.exp(_r1, dk_T_1);
    return ((pq_keys_0.`1, ek_T_0), (pq_keys_1.`1, ek_T_1));
  }
}.

section Main.

declare module P <: KEMP {-RedBatched, -RedPerKp}.
declare module NG <: NGT {-RedBatched, -RedPerKp, -P}.

lemma regrouped_common_init :
  equiv [ RedBatched(P, NG).initialize
          ~ RedPerKp(P, NG, KeyGenEquiv_FromKeyGen(P)).initialize :
          ={glob P, glob NG}
          ==> ={res} /\ ={glob P, glob NG}
              /\ RedBatched.pq_keys_0{1} = RedPerKp.pq_keys_0{2}
              /\ RedBatched.pq_keys_1{1} = RedPerKp.pq_keys_1{2}
              /\ RedBatched.dk_T_0{1} = RedPerKp.dk_T_0{2}
              /\ RedBatched.dk_T_1{1} = RedPerKp.dk_T_1{2}
              /\ RedBatched.ek_T_0{1} = RedPerKp.ek_T_0{2}
              /\ RedBatched.ek_T_1{1} = RedPerKp.ek_T_1{2} ].
proof.
  proc.
  (* regroup side 1 per keypair, on the UN-INLINED body:
       1 kg0  2 kg1  3 s0<$  4 rs0  5 gen0  6 exp0  7 s1<$  8 rs1  9 gen1 10 exp1
     target [1,3,4,5,6,2,7,8,9,10] -- four one-step lifts of keypair 0's tail
     over the second keygen *)
  swap{1} 3 -1.
  swap{1} 4 -1.
  swap{1} 5 -1.
  swap{1} 6 -1.
  inline *.
  (* both backbones are now the same call/sample sequence; peel back-to-front *)
  wp; call (_: true).
  wp; call (_: true).
  wp; call (_: true).
  rnd.
  wp; call (_: true).
  wp; call (_: true).
  wp; call (_: true).
  wp; call (_: true).
  rnd.
  wp; call (_: true).
  skip => />.
qed.

(* --- n = 1: the regrouping vanishes and there is one keypair -------------- *)

module RedBatched1 (P : KEMP, NG : NGT) = {
  var pq_keys_0 : pkt * skt
  var dk_T_0 : scal
  var ek_T_0 : elem

  proc initialize () : pkt * elem = {
    var seed_T_0 : ts;
    var _r0 : elem;
    pq_keys_0 <@ P.keygen();
    seed_T_0 <$ dts;
    dk_T_0 <@ NG.randomscalar(seed_T_0);
    _r0 <@ NG.generator();
    ek_T_0 <@ NG.exp(_r0, dk_T_0);
    return (pq_keys_0.`1, ek_T_0);
  }
}.

module RedPerKp1 (P : KEMP, NG : NGT, Challenger : KGE) = {
  var pq_keys_0 : pkt * skt
  var dk_T_0 : scal
  var ek_T_0 : elem

  proc initialize () : pkt * elem = {
    var seed_T_0 : ts;
    var _r0 : elem;
    pq_keys_0 <@ Challenger.generate();
    seed_T_0 <$ dts;
    dk_T_0 <@ NG.randomscalar(seed_T_0);
    _r0 <@ NG.generator();
    ek_T_0 <@ NG.exp(_r0, dk_T_0);
    return (pq_keys_0.`1, ek_T_0);
  }
}.

declare module P1 <: KEMP {-RedBatched1, -RedPerKp1}.
declare module NG1 <: NGT {-RedBatched1, -RedPerKp1, -P1}.

lemma regrouped_common_init_n1 :
  equiv [ RedBatched1(P1, NG1).initialize
          ~ RedPerKp1(P1, NG1, KeyGenEquiv_FromKeyGen(P1)).initialize :
          ={glob P1, glob NG1}
          ==> ={res} /\ ={glob P1, glob NG1}
              /\ RedBatched1.pq_keys_0{1} = RedPerKp1.pq_keys_0{2}
              /\ RedBatched1.dk_T_0{1} = RedPerKp1.dk_T_0{2}
              /\ RedBatched1.ek_T_0{1} = RedPerKp1.ek_T_0{2} ].
proof.
  proc.
  inline *.
  wp; call (_: true).
  wp; call (_: true).
  wp; call (_: true).
  rnd.
  wp; call (_: true).
  skip => />.
qed.

(* --- the BATCHING direction, and the hop_4 shape --------------------------
 * The lemma above regroups the BATCHED side into per-keypair form. That
 * direction is not always available: on hop_4 the batched side's n keygens
 * arrive from inside an inlined challenger `Initialize`, so they cannot be
 * split apart before `inline *`. The other direction always is -- lift each
 * interleaved segment's pq call up to the front, one swap per keypair -- so
 * that is the direction the emitter uses for BOTH hops, and both are validated
 * here.
 *)

module RedIntl (P : KEMP, NG : NGT, Challenger : KGE) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var dk_T_0, dk_T_1 : scal
  var ek_T_0, ek_T_1 : elem

  proc initialize () : (pkt * elem) * (pkt * elem) = {
    var seed_T_0 : ts;
    var _r0 : elem;
    var seed_T_1 : ts;
    var _r1 : elem;
    pq_keys_0 <@ Challenger.generate();
    seed_T_0 <$ dts;
    dk_T_0 <@ NG.randomscalar(seed_T_0);
    _r0 <@ NG.generator();
    ek_T_0 <@ NG.exp(_r0, dk_T_0);
    pq_keys_1 <@ Challenger.generate();
    seed_T_1 <$ dts;
    dk_T_1 <@ NG.randomscalar(seed_T_1);
    _r1 <@ NG.generator();
    ek_T_1 <@ NG.exp(_r1, dk_T_1);
    return ((pq_keys_0.`1, ek_T_0), (pq_keys_1.`1, ek_T_1));
  }
}.

(* the binding challenger: it runs BOTH keygens itself and keeps the halves in
   its own fields, returning only the public ones -- the hop_4 batched side *)
module HON_BIND_Breakable (K : KEMP) = {
  var ek0, ek1 : pkt
  var dk0, dk1 : skt

  proc initialize () : pkt * pkt = {
    var _t0 : pkt * skt;
    var _t1 : pkt * skt;
    _t0 <@ K.keygen();
    ek0 <- _t0.`1;
    dk0 <- _t0.`2;
    _t1 <@ K.keygen();
    ek1 <- _t1.`1;
    dk1 <- _t1.`2;
    return (ek0, ek1);
  }
}.

module type BINDO = { proc initialize () : pkt * pkt }.

module RedBind (P : KEMP, NG : NGT, Challenger : BINDO) = {
  var ek_PQ_0, ek_PQ_1 : pkt
  var dk_T_0, dk_T_1 : scal
  var ek_T_0, ek_T_1 : elem

  proc initialize () : (pkt * elem) * (pkt * elem) = {
    var _tup : pkt * pkt;
    var seed_T_0 : ts;
    var _r0 : elem;
    var seed_T_1 : ts;
    var _r1 : elem;
    _tup <@ Challenger.initialize();
    ek_PQ_0 <- _tup.`1;
    ek_PQ_1 <- _tup.`2;
    seed_T_0 <$ dts;
    dk_T_0 <@ NG.randomscalar(seed_T_0);
    _r0 <@ NG.generator();
    ek_T_0 <@ NG.exp(_r0, dk_T_0);
    seed_T_1 <$ dts;
    dk_T_1 <@ NG.randomscalar(seed_T_1);
    _r1 <@ NG.generator();
    ek_T_1 <@ NG.exp(_r1, dk_T_1);
    return ((ek_PQ_0, ek_T_0), (ek_PQ_1, ek_T_1));
  }
}.

declare module P2 <: KEMP {-RedIntl, -RedBind, -HON_BIND_Breakable}.
declare module NG2 <: NGT {-RedIntl, -RedBind, -HON_BIND_Breakable, -P2}.

lemma regrouped_common_init_bind :
  equiv [ RedIntl(P2, NG2, KeyGenEquiv_FromKeyGen(P2)).initialize
          ~ RedBind(P2, NG2, HON_BIND_Breakable(P2)).initialize :
          ={glob P2, glob NG2}
          ==> ={res} /\ ={glob P2, glob NG2}
              /\ RedIntl.dk_T_0{1} = RedBind.dk_T_0{2}
              /\ RedIntl.dk_T_1{1} = RedBind.dk_T_1{2}
              /\ RedIntl.ek_T_0{1} = RedBind.ek_T_0{2}
              /\ RedIntl.ek_T_1{1} = RedBind.ek_T_1{2}
              /\ RedBind.ek_PQ_0{2} = HON_BIND_Breakable.ek0{2}
              /\ RedBind.ek_PQ_1{2} = HON_BIND_Breakable.ek1{2}
              /\ RedIntl.pq_keys_0{1}.`1 = HON_BIND_Breakable.ek0{2}
              /\ RedIntl.pq_keys_1{1}.`1 = HON_BIND_Breakable.ek1{2}
              /\ RedIntl.pq_keys_0{1}.`2 = HON_BIND_Breakable.dk0{2}
              /\ RedIntl.pq_keys_1{1}.`2 = HON_BIND_Breakable.dk1{2} ].
proof.
  proc.
  (* batch side 1: lift keypair 1's challenger generate to position 2 *)
  swap{1} 6 -4.
  inline *.
  wp; call (_: true).
  wp; call (_: true).
  wp; call (_: true).
  rnd.
  wp; call (_: true).
  wp; call (_: true).
  wp; call (_: true).
  rnd.
  wp; call (_: true).
  wp; call (_: true).
  skip => />.
qed.

(* the same batching direction on the hop_8 shape (no binding challenger):
   one swap instead of the four the first lemma needed *)
declare module P3 <: KEMP {-RedBatched, -RedIntl}.
declare module NG3 <: NGT {-RedBatched, -RedIntl, -P3}.

lemma regrouped_common_init_batchdir :
  equiv [ RedBatched(P3, NG3).initialize
          ~ RedIntl(P3, NG3, KeyGenEquiv_FromKeyGen(P3)).initialize :
          ={glob P3, glob NG3}
          ==> ={res} /\ ={glob P3, glob NG3}
              /\ RedBatched.pq_keys_0{1} = RedIntl.pq_keys_0{2}
              /\ RedBatched.pq_keys_1{1} = RedIntl.pq_keys_1{2}
              /\ RedBatched.dk_T_0{1} = RedIntl.dk_T_0{2}
              /\ RedBatched.dk_T_1{1} = RedIntl.dk_T_1{2}
              /\ RedBatched.ek_T_0{1} = RedIntl.ek_T_0{2}
              /\ RedBatched.ek_T_1{1} = RedIntl.ek_T_1{2} ].
proof.
  proc.
  swap{2} 6 -4.
  inline *.
  wp; call (_: true).
  wp; call (_: true).
  wp; call (_: true).
  rnd.
  wp; call (_: true).
  wp; call (_: true).
  wp; call (_: true).
  rnd.
  wp; call (_: true).
  wp; call (_: true).
  skip => />.
qed.

end section Main.
