(* Tripwire for the wall-4a finite-map operation shapes the EC exporter
   emits for a FrogLang ``Map<K, V>`` (a lazy random-oracle table):
     membership  k in m    -> k \in m
     read        m[k]      -> oget m.[k]      (guarded by membership)
     write       m[k] = v  -> m <- m.[k <- v]
   over ``FMap``'s finite-map type ``(k, v) fmap`` (NOT SmtMap's total
   ``map``). The ``.entries`` iteration loop (wall 4b) is not covered here. *)
require import AllCore FMap.

type k. type v.

module M = {
  var ht : (k, v) fmap

  proc direct(m : k, r : v) : v = {
    var outv : v;
    if (m \in ht) {
      outv <- (oget ht.[m]);
    } else {
      ht <- ht.[m <- r];
      outv <- r;
    }
    return outv;
  }
}.
