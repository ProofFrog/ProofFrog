require import AllCore Distr.

type bs_lam, bs_pq, bs_t, bs_full.
op concat : bs_pq -> bs_t -> bs_full.

module RL = {
  var s0 : bs_lam  var y0_pq : bs_pq  var y0_t : bs_t  var h : bs_lam -> bs_full
  proc hashg(x : bs_lam) : bs_full = {
    var x0 : bs_lam; var r0 : bs_full;
    x0 <- x;
    if (x0 = s0) { r0 <- concat y0_pq y0_t; } else { r0 <- h x0; }
    return r0;
  }
}.
module RR = {
  var seed_0 : bs_lam  var dk_PQ_0 : bs_pq  var s_T_0 : bs_t  var h : bs_lam -> bs_full
  proc hashg(x : bs_lam) : bs_full = {
    var r0 : bs_full;
    if (x = seed_0) { r0 <- concat dk_PQ_0 s_T_0; } else { r0 <- h x; }
    return r0;
  }
}.

lemma hashg_eq :
  equiv [ RL.hashg ~ RR.hashg :
    ={x} /\ RL.h{1} = RR.h{2} /\ RL.s0{1} = RR.seed_0{2}
    /\ RL.y0_pq{1} = RR.dk_PQ_0{2} /\ RL.y0_t{1} = RR.s_T_0{2}
    ==> ={res} /\ RL.h{1} = RR.h{2} /\ RL.s0{1} = RR.seed_0{2}
    /\ RL.y0_pq{1} = RR.dk_PQ_0{2} /\ RL.y0_t{1} = RR.s_T_0{2} ].
proof.
  proc.
  seq 1 0 : (={x} /\ x0{1} = x{1} /\ RL.h{1} = RR.h{2} /\ RL.s0{1} = RR.seed_0{2}
             /\ RL.y0_pq{1} = RR.dk_PQ_0{2} /\ RL.y0_t{1} = RR.s_T_0{2}).
  + auto.
  if; auto.
qed.
