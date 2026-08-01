(* Probe: the ONE remaining unknown before the hop_14 `initialize` tripwire.
 *
 * The split-uniform coupling itself is validated (ec_templates/split_uniform_couple.ec).
 * To USE it on hop_14 the two samples that correspond to one full seed must be
 * made ADJACENT on the four-sample side, because `rndsem*{i} 0` folds only
 * CONSECUTIVE samples. Side 1 draws them in the order
 *   pq_seed_0, pq_seed_1, t_seed_0, t_seed_1
 * with abstract derivekeypair calls interleaved, and the pairing needed is
 * (pq_seed_0, t_seed_0) / (pq_seed_1, t_seed_1).
 *
 * So: can `swap` lift a SAMPLE up past an abstract probabilistic call and
 * another sample? Cycle 64 established that `swap` reorders two abstract
 * probabilistic calls with disjoint globs; this asks the adjacent question for a
 * sample crossing a call. If yes, the hop_14 tripwire is mechanical.
 *)

require import AllCore Distr.

type pqs, ts, pkt, skt.

op dpqs : pqs distr.
op dts  : ts distr.

module type KEMP = { proc derivekeypair (s : pqs) : pkt * skt }.

(* the four-sample side, in its natural order *)
module A (P : KEMP) = {
  proc f () : (pkt * skt) * (pkt * skt) * ts * ts = {
    var s0, s1 : pqs;
    var t0, t1 : ts;
    var k0, k1 : pkt * skt;
    s0 <$ dpqs;
    k0 <@ P.derivekeypair(s0);
    s1 <$ dpqs;
    k1 <@ P.derivekeypair(s1);
    t0 <$ dts;
    t1 <$ dts;
    return (k0, k1, t0, t1);
  }
}.

(* the same, with each t-sample lifted next to its pq-sample *)
module B (P : KEMP) = {
  proc f () : (pkt * skt) * (pkt * skt) * ts * ts = {
    var s0, s1 : pqs;
    var t0, t1 : ts;
    var k0, k1 : pkt * skt;
    s0 <$ dpqs;
    t0 <$ dts;
    k0 <@ P.derivekeypair(s0);
    s1 <$ dpqs;
    t1 <$ dts;
    k1 <@ P.derivekeypair(s1);
    return (k0, k1, t0, t1);
  }
}.

section Probe.

declare module P <: KEMP.

lemma swap_sample_past_call :
  equiv [ A(P).f ~ B(P).f : ={glob P} ==> ={res} /\ ={glob P} ].
proof.
  proc.
  (* ORDER MATTERS and is easy to get backwards: lift t0 FIRST (stmt 5, up 3,
     landing after s0), THEN t1 (now stmt 6, up 1, landing after s1). Doing t1
     first swaps the two t-samples' roles and `sim` will not close. *)
  swap{1} 5 -3.
  swap{1} 6 -1.
  sim.
qed.

end section Probe.
