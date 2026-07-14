(* Tripwire for wall-4c: optional-return oracle. Models INDCCA_ROM.Decaps
   (return None on the excluded ct; else Some of a module call) and the lazy
   Indirect (return None; Some of a map read / loop hit / fresh sample). *)
require import AllCore List FSet FMap Distr.

type ct. type ss. type query. type bs_n_t. type bs_M_t.
op dbs : bs_n_t distr.

module type KEM = { proc decaps(c : ct) : ss }.

module D (K : KEM) = {
  var ctStar : ct

  proc decaps(c : ct) : ss option = {
    var _r0 : ss option;
    var v : ss;
    if (c = ctStar) {
      _r0 <- None;
    } else {
      v <@ K.decaps(c);
      _r0 <- Some v;
    }
    return _r0;
  }
}.

module L = {
  var qStar : query
  var qT : (query, bs_n_t) fmap

  proc indirect(q : query) : bs_n_t option = {
    var _r0 : bs_n_t option;
    var s : bs_n_t;
    if (q = qStar) {
      _r0 <- None;
    } else {
      if (q \in qT) {
        _r0 <- Some (oget qT.[q]);
      } else {
        s <$ dbs;
        qT <- qT.[q <- s];
        _r0 <- Some s;
      }
    }
    return _r0;
  }
}.
