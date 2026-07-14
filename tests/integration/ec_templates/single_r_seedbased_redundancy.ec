(* Tripwire: generic N-leaf (here 7) slice navigation for the single-R seedbased
   KDF redundancy. The KDF input is a left-nested 6-concat:
     u6 = c0(c1(c2(c3(c4(c5(la,lb),lc),ld),le),lf),lg)
   (c0 outermost = || label, c5 innermost = ss_PQ || ss_T). Leaf lc = encct(ct_PQ)
   at index 2, ld = encode(ct_T) at index 3. Goal: from u6_0 = u6_1 derive
   ct_PQ_0 = ct_PQ_1 and ct_T_0 = ct_T_1 (the redundancy kdf0=kdf1 => ct0=ct1). *)

require import AllCore.

(* leaf + intermediate types *)
type la_t. type lb_t. type ctpq_t. type ctt_t. type le_t. type lf_t. type lg_t.
type lc_t. type ld_t.
type u1_t. type u2_t. type u3_t. type u4_t. type u5_t. type u6_t.

(* leaf encodings (the two we invert) *)
op encct : ctpq_t -> lc_t.
op encode : ctt_t -> ld_t.
axiom encct_inj (x y : ctpq_t) : encct x = encct y => x = y.
axiom encode_inj (x y : ctt_t) : encode x = encode y => x = y.

(* concat ops, outer-first c0..c5 *)
op c5 : la_t -> lb_t -> u1_t.
op c4 : u1_t -> lc_t -> u2_t.
op c3 : u2_t -> ld_t -> u3_t.
op c2 : u3_t -> le_t -> u4_t.
op c1 : u4_t -> lf_t -> u5_t.
op c0 : u5_t -> lg_t -> u6_t.

(* slice_concat_left/right round-trips (one pair per level) *)
op sl0 : u6_t -> u5_t. op sr0 : u6_t -> lg_t.
op sl1 : u5_t -> u4_t. op sr1 : u5_t -> lf_t.
op sl2 : u4_t -> u3_t. op sr2 : u4_t -> le_t.
op sl3 : u3_t -> u2_t. op sr3 : u3_t -> ld_t.
op sl4 : u2_t -> u1_t. op sr4 : u2_t -> lc_t.
op sl5 : u1_t -> la_t. op sr5 : u1_t -> lb_t.

axiom slc0 (a : u5_t) (b : lg_t) : sl0 (c0 a b) = a.
axiom slc1 (a : u4_t) (b : lf_t) : sl1 (c1 a b) = a.
axiom slc2 (a : u3_t) (b : le_t) : sl2 (c2 a b) = a.
axiom slc3 (a : u2_t) (b : ld_t) : sl3 (c3 a b) = a.
axiom slc4 (a : u1_t) (b : lc_t) : sl4 (c4 a b) = a.
axiom src3 (a : u2_t) (b : ld_t) : sr3 (c3 a b) = b.
axiom src4 (a : u1_t) (b : lc_t) : sr4 (c4 a b) = b.

(* The redundancy: full equality forces both ciphertext components equal. *)
lemma redundancy (la0 la1 : la_t) (lb0 lb1 : lb_t)
                 (ctpq0 ctpq1 : ctpq_t) (ctt0 ctt1 : ctt_t)
                 (le0 le1 : le_t) (lf0 lf1 : lf_t) (lg0 lg1 : lg_t) :
  c0 (c1 (c2 (c3 (c4 (c5 la0 lb0) (encct ctpq0)) (encode ctt0)) le0) lf0) lg0 =
  c0 (c1 (c2 (c3 (c4 (c5 la1 lb1) (encct ctpq1)) (encode ctt1)) le1) lf1) lg1 =>
  ctpq0 = ctpq1 /\ ctt0 = ctt1.
proof.
  move => h.
  (* descend to u5 *)
  have h1 : c1 (c2 (c3 (c4 (c5 la0 lb0) (encct ctpq0)) (encode ctt0)) le0) lf0
          = c1 (c2 (c3 (c4 (c5 la1 lb1) (encct ctpq1)) (encode ctt1)) le1) lf1
    by rewrite -(slc0 (c1 (c2 (c3 (c4 (c5 la0 lb0) (encct ctpq0)) (encode ctt0)) le0) lf0) lg0)
                -(slc0 (c1 (c2 (c3 (c4 (c5 la1 lb1) (encct ctpq1)) (encode ctt1)) le1) lf1) lg1) h.
  (* descend to u4 *)
  have h2 : c2 (c3 (c4 (c5 la0 lb0) (encct ctpq0)) (encode ctt0)) le0
          = c2 (c3 (c4 (c5 la1 lb1) (encct ctpq1)) (encode ctt1)) le1
    by rewrite -(slc1 (c2 (c3 (c4 (c5 la0 lb0) (encct ctpq0)) (encode ctt0)) le0) lf0)
                -(slc1 (c2 (c3 (c4 (c5 la1 lb1) (encct ctpq1)) (encode ctt1)) le1) lf1) h1.
  (* descend to u3 *)
  have h3 : c3 (c4 (c5 la0 lb0) (encct ctpq0)) (encode ctt0)
          = c3 (c4 (c5 la1 lb1) (encct ctpq1)) (encode ctt1)
    by rewrite -(slc2 (c3 (c4 (c5 la0 lb0) (encct ctpq0)) (encode ctt0)) le0)
                -(slc2 (c3 (c4 (c5 la1 lb1) (encct ctpq1)) (encode ctt1)) le1) h2.
  (* ct_T = right of c3 *)
  have hd : encode ctt0 = encode ctt1
    by rewrite -(src3 (c4 (c5 la0 lb0) (encct ctpq0)) (encode ctt0))
                -(src3 (c4 (c5 la1 lb1) (encct ctpq1)) (encode ctt1)) h3.
  (* descend to u2 for ct_PQ *)
  have h4 : c4 (c5 la0 lb0) (encct ctpq0) = c4 (c5 la1 lb1) (encct ctpq1)
    by rewrite -(slc3 (c4 (c5 la0 lb0) (encct ctpq0)) (encode ctt0))
                -(slc3 (c4 (c5 la1 lb1) (encct ctpq1)) (encode ctt1)) h3.
  have hc : encct ctpq0 = encct ctpq1
    by rewrite -(src4 (c5 la0 lb0) (encct ctpq0))
                -(src4 (c5 la1 lb1) (encct ctpq1)) h4.
  split.
  + by apply (encct_inj _ _ hc).
  by apply (encode_inj _ _ hd).
qed.
