(* Mirrors the EXACT shape the exporter now emits for the Programmed lazy-RO
   Direct oracle: 3-level guard (mStar exclusion / membership / loop), a module
   call inside the while (P.pack), the found-flag match arm, fallthrough. *)
require import AllCore List FSet FMap Distr.

type query. type bs_M_t. type bs_n_t.
op dbs_n_t : bs_n_t distr.

module type PACK = { proc pack(st : bs_M_t, q : query) : bs_M_t }.

module M (P : PACK) = {
  var st : bs_M_t
  var mStar : bs_M_t
  var yStar : bs_n_t
  var hT : (bs_M_t, bs_n_t) fmap
  var qT : (query, bs_n_t) fmap

  proc direct(m : bs_M_t) : bs_n_t = {
    var _r0 : bs_n_t;
    var e : query * bs_n_t;
    var _r1 : bool;
    var _r2 : query list;
    var _r3 : int;
    var m_expected : bs_M_t;
    var r : bs_n_t;
    if (m = mStar) {
      _r0 <- yStar;
    } else {
      if (m \in hT) {
        _r0 <- (oget hT.[m]);
      } else {
        _r1 <- false;
        _r2 <- elems (fdom qT);
        _r3 <- 0;
        while (_r3 < size _r2) {
          e <- (nth witness _r2 _r3, oget qT.[nth witness _r2 _r3]);
          m_expected <@ P.pack(st, e.`1);
          if ((m = m_expected) /\ ! _r1) {
            hT <- hT.[m <- e.`2];
            _r0 <- e.`2;
            _r1 <- true;
          }
          _r3 <- _r3 + 1;
        }
        if (! _r1) {
          r <$ dbs_n_t;
          hT <- hT.[m <- r];
          _r0 <- r;
        }
      }
    }
    return _r0;
  }
}.
