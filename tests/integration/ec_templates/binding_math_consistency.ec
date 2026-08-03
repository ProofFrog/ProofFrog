(* Tripwire: a SINGLE SIMULTANEOUS MODEL for the whole DERIVABLE math axiom
 * surface of a CFRG binding export -- every family proved as a lemma, all
 * under ONE interpretation.
 *
 * WHY A CONSOLIDATED FILE, when slice_concat_derive.ec / xor_derive.ec /
 * dbs_split_derive.ec / virtual_concat_consistency.ec already exist. Those show
 * each family is individually derivable. That is feasibility evidence, and it
 * is NOT consistency: four families could each be satisfiable while no single
 * interpretation satisfies all of them at once (a `concat` reading that
 * validates the slice laws need not be the reading under which `bxor`'s
 * involution holds, and so on). Consistency of the axiom SET is what protects
 * against the failure mode the ledger exists for -- EasyCrypt certifying a file
 * that proves nothing because its hypotheses cannot all be true. That needs one
 * model, which is this file.
 *
 * THE SURFACE THIS COVERS. Censused on the emitted
 * `CG_seedbased_HON_BIND_K_PK.ec` (165 axioms total):
 *     48   xor_<T>_{invol, commut, assoc}          16 bitstring types
 *     21   {slice_concat_left, slice_concat_right, concat_slices_id}_<L>_<S>_<R>
 *     14   dbs_<T>_ll
 *      7   dbs_<R>_split_<L>_<S>  (+ the virtual triple's _split_dlet)
 *   ~= 90 of the 165, i.e. the majority of a binding proof's TCB, is DERIVABLE
 *   mathematics rather than a cryptographic assumption. The rest is 13 licensed
 *   behavioural `_det`/`_inj` hypotheses about abstract schemes (checked
 *   against their FrogLang `deterministic`/`injective` modifiers by
 *   extras/scripts/axiom_modifier_audit.py) plus the inherent hardness
 *   advantages.
 *
 * THE MODEL. `bs_k` = `k`-bit bool lists; `concat` = `++`; `slice i j` =
 * `take (j-i) o drop i`; `bxor` = pointwise `^^` over `zip`; `d bs_k` =
 * `dlist dbool k`. This is the intended reading, so proving the statements here
 * shows they are not merely consistent but TRUE as meant.
 *
 * WHAT REMAINS ASSUMED after this file. Every lemma below carries its size
 * hypotheses explicitly (`size a = n1`, `size s = n1 + n2`, ...). In the
 * exported `.ec` those hypotheses are absent, because the `bs_*` types are
 * abstract and carry no length -- the lengths live only in the exporter's
 * `_bs_lengths` map. So the standing obligation is exactly: *the exporter
 * attaches the right length to the right type*. That is code
 * (`type_collector`'s symbolic length-sum gate and the slice-OFFSET ordering),
 * and it is where a review of this axiom surface should spend itself. The
 * mathematics is settled here.
 *
 * The principled fix that would dissolve the obligation entirely is to
 * translate `bs_n` to EC's sized `word` theory, where these are stdlib lemmas
 * and the lengths are carried by the type. This file is the feasibility
 * argument for that route as much as it is evidence for the ledger.
 *)

require import AllCore List Bool Distr DList DBool.

(* three lengths, so the concat laws can be stated at a genuine pair *)
op n1 : int.
op n2 : int.
axiom ge0_n1 : 0 <= n1.
axiom ge0_n2 : 0 <= n2.

op concat (a b : bool list) : bool list = a ++ b.
op slice (s : bool list) (i j : int) : bool list = take (j - i) (drop i s).
op bxor (a b : bool list) : bool list =
  map (fun (p : bool * bool) => p.`1 ^^ p.`2) (zip a b).
op dbs (n : int) : bool list distr = dlist dbool n.

(* ===================== family 1: slice / concat round-trips ============= *)

lemma m_slice_concat_left (a b : bool list) :
  size a = n1 => slice (concat a b) 0 n1 = a.
proof.
move => h; rewrite /slice /concat drop0 /=.
by rewrite -h take_size_cat.
qed.

lemma m_slice_concat_right (a b : bool list) :
  size a = n1 => size b = n2 => slice (concat a b) n1 (n1 + n2) = b.
proof.
move => ha hb; rewrite /slice /concat -ha drop_size_cat //.
have -> : size a + n2 - size a = n2 by smt().
by rewrite -hb take_size.
qed.

lemma m_concat_slices_id (s : bool list) :
  size s = n1 + n2 =>
  concat (slice s 0 n1) (slice s n1 (n1 + n2)) = s.
proof.
move => h; rewrite /slice /concat drop0 /=.
have -> : n1 + n2 - n1 = n2 by smt().
have -> : take n2 (drop n1 s) = drop n1 s
  by rewrite take_oversize // size_drop; smt(size_ge0).
by rewrite cat_take_drop.
qed.

(* ===================== family 2: XOR laws ============================== *)

lemma m_bxor_size (a b : bool list) :
  size a = size b => size (bxor a b) = size a.
proof. by move => h; rewrite /bxor size_map size_zip h. qed.

lemma m_bxor_nth (a b : bool list) (i : int) :
  size a = size b => 0 <= i < size a =>
  nth false (bxor a b) i = nth false a i ^^ nth false b i.
proof.
move => h hi; rewrite /bxor (nth_map (false, false)) ?size_zip 1:/#.
by rewrite nth_zip.
qed.

lemma m_xor_commut (a b : bool list) :
  size a = size b => bxor a b = bxor b a.
proof.
move => h; apply (eq_from_nth false); 1: by rewrite !m_bxor_size /#.
move => i; rewrite m_bxor_size // => hi.
by rewrite !m_bxor_nth 1..4:/#; smt(xorC).
qed.

lemma m_xor_invol (a b : bool list) :
  size a = size b => bxor (bxor a b) b = a.
proof.
move => h; apply (eq_from_nth false); 1: by rewrite !m_bxor_size /#.
move => i; rewrite m_bxor_size 1:m_bxor_size // => hi.
rewrite m_bxor_nth 1:m_bxor_size /#.
qed.

lemma m_xor_assoc (a b c : bool list) :
  size a = size b => size b = size c =>
  bxor a (bxor b c) = bxor (bxor a b) c.
proof.
move => hab hbc; apply (eq_from_nth false).
+ by rewrite !m_bxor_size /#.
move => i; rewrite m_bxor_size 1:/# => hi.
by rewrite !m_bxor_nth ?m_bxor_size 1..8:/#; smt(xorA).
qed.

(* ===================== family 3: uniform-distribution laws ============== *)

lemma m_dbs_ll (n : int) : is_lossless (dbs n).
proof. by rewrite /dbs dlist_ll dbool_ll. qed.

lemma m_dbs_split :
  dbs (n1 + n2) =
  dmap (dbs n1 `*` dbs n2) (fun (p : bool list * bool list) => concat p.`1 p.`2).
proof. by rewrite /dbs /concat dlist_add // ?ge0_n1 ?ge0_n2. qed.

(* the shape `rndsem*{i} 0` produces, emitted for VIRTUAL triples only *)
lemma m_dbs_split_dlet :
  dbs (n1 + n2) =
  dlet (dbs n1) (fun (v1 : bool list) =>
    dmap (dbs n2) (fun (v2 : bool list) => concat v1 v2)).
proof.
rewrite m_dbs_split dprod_dlet dmap_dlet /=.
apply eq_dlet => // a.
by rewrite dmap_comp.
qed.

(* ===================== the joint statement ==============================
   Every lemma above lives in this one file, hence under this one
   interpretation of concat / slice / bxor / dbs. EasyCrypt accepting the file
   is therefore a machine-checked witness that the derivable half of a binding
   proof's axiom set is SIMULTANEOUSLY satisfiable, and satisfied by the
   intended model -- which is the property "each family is derivable" does not
   by itself give. *)
