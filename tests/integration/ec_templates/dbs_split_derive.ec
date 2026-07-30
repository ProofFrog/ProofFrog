(* Tripwire: the exporter's split-distribution axiom family
   (``dbs_<n1+n2> = dmap (dbs_n1 `*` dbs_n2) concat``) DERIVED from EC's
   DList.dlist_add over the bool-list representation -- companion to
   slice_concat_derive.ec / xor_derive.ec. *)
require import AllCore List Distr DList DBool.

op n1 : int.
axiom ge0_n1 : 0 <= n1.
op n2 : int.
axiom ge0_n2 : 0 <= n2.

op dbs (n : int) : bool list distr = dlist dbool n.

lemma dbs_split :
  dbs (n1 + n2) =
  dmap (dbs n1 `*` dbs n2) (fun (p : bool list * bool list) => p.`1 ++ p.`2).
proof. by rewrite /dbs dlist_add // ?ge0_n1 ?ge0_n2. qed.

(* the ll/fu/uni facts the exporter also axiomatizes follow from dlist +
   dbool stdlib lemmas at CONCRETE size predicates: *)
lemma dbs_ll (n : int) : is_lossless (dbs n).
proof. by rewrite /dbs dlist_ll dbool_ll. qed.
