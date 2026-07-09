require import AllCore Distr.

type encapskey.
type decapskey.
type ciphertext.
type sharedsecret.

module type Scheme = {
  proc keygen() : encapskey * decapskey
  proc decaps(dk : decapskey, ct : ciphertext) : sharedsecret
}.

section Main.

module Before (K : Scheme) = {
  var cdk0 : decapskey
  var cdk1 : decapskey
  var dk0 : decapskey
  var dk1 : decapskey
  proc initialize() : encapskey * encapskey = {
    var t0 : encapskey * decapskey;
    var t1 : encapskey * decapskey;
    t0 <@ K.keygen();
    cdk0 <- t0.`2;
    dk0 <- t0.`2;
    t1 <@ K.keygen();
    cdk1 <- t1.`2;
    dk1 <- t1.`2;
    return (t0.`1, t1.`1);
  }
  proc decaps0(ct : ciphertext) : sharedsecret = {
    var r : sharedsecret;
    r <@ K.decaps(dk0, ct);
    return r;
  }
  proc decaps1(ct : ciphertext) : sharedsecret = {
    var r : sharedsecret;
    r <@ K.decaps(dk1, ct);
    return r;
  }
  proc challenge(ct0 : ciphertext, ct1 : ciphertext) : bool = {
    var a7 : sharedsecret;
    var a8 : sharedsecret;
    a7 <@ K.decaps(cdk0, ct0);
    a8 <@ K.decaps(cdk1, ct1);
    return false;
  }
}.

module After (K : Scheme) = {
  var cdk0 : decapskey
  var cdk1 : decapskey
  var dk0 : decapskey
  var dk1 : decapskey
  proc initialize() : encapskey * encapskey = {
    var t0 : encapskey * decapskey;
    var t1 : encapskey * decapskey;
    t0 <@ K.keygen();
    cdk0 <- t0.`2;
    dk0 <- t0.`2;
    t1 <@ K.keygen();
    cdk1 <- t1.`2;
    dk1 <- t1.`2;
    return (t0.`1, t1.`1);
  }
  proc decaps0(ct : ciphertext) : sharedsecret = {
    var r : sharedsecret;
    r <@ K.decaps(dk0, ct);
    return r;
  }
  proc decaps1(ct : ciphertext) : sharedsecret = {
    var r : sharedsecret;
    r <@ K.decaps(dk1, ct);
    return r;
  }
  proc challenge(ct0 : ciphertext, ct1 : ciphertext) : bool = {
    var a7 : sharedsecret;
    var a8 : sharedsecret;
    return false;
  }
}.

declare module K <: Scheme {-Before, -After}.

declare axiom K_decaps_pres (g : (glob K)) :
  phoare[ K.decaps : (glob K) = g ==> (glob K) = g ] = 1%r.

(* Forward direction (left chain): drop on side 1. *)
lemma micro_left :
  equiv [ Before(K).challenge ~ After(K).challenge :
          ={ct0, ct1} /\ (glob Before(K)){1} = (glob After(K)){2} ==>
          ={res} /\ (glob Before(K)){1} = (glob After(K)){2} ].
proof.
  proc.
  wp.
  exists* (glob K){1}; elim* => gd0.
  call{1} (K_decaps_pres gd0).
  wp.
  exists* (glob K){1}; elim* => gd1.
  call{1} (K_decaps_pres gd1).
  skip => /#.
qed.

(* Rename step: both sides have the two dead calls, different (dead) LHS names. *)
module Before2 (K : Scheme) = {
  var cdk0 : decapskey
  var cdk1 : decapskey
  var dk0 : decapskey
  var dk1 : decapskey
  proc initialize() : encapskey * encapskey = {
    var t0 : encapskey * decapskey;
    var t1 : encapskey * decapskey;
    t0 <@ K.keygen();
    cdk0 <- t0.`2;
    dk0 <- t0.`2;
    t1 <@ K.keygen();
    cdk1 <- t1.`2;
    dk1 <- t1.`2;
    return (t0.`1, t1.`1);
  }
  proc decaps0(ct : ciphertext) : sharedsecret = {
    var r : sharedsecret;
    r <@ K.decaps(dk0, ct);
    return r;
  }
  proc decaps1(ct : ciphertext) : sharedsecret = {
    var r : sharedsecret;
    r <@ K.decaps(dk1, ct);
    return r;
  }
  proc challenge(ct0 : ciphertext, ct1 : ciphertext) : bool = {
    var k00 : sharedsecret;
    var k10 : sharedsecret;
    k00 <@ K.decaps(cdk0, ct0);
    k10 <@ K.decaps(cdk1, ct1);
    return false;
  }
}.

declare module K2 <: Scheme {-Before, -Before2}.

lemma micro_rename :
  equiv [ Before(K2).challenge ~ Before2(K2).challenge :
          ={ct0, ct1} /\ (glob Before(K2)){1} = (glob Before2(K2)){2} ==>
          ={res} /\ (glob Before(K2)){1} = (glob Before2(K2)){2} ].
proof.
  proc; sim.
qed.

(* Reversed direction (right chain): drop on side 2. *)
lemma micro_right :
  equiv [ After(K).challenge ~ Before(K).challenge :
          ={ct0, ct1} /\ (glob After(K)){1} = (glob Before(K)){2} ==>
          ={res} /\ (glob After(K)){1} = (glob Before(K)){2} ].
proof.
  proc.
  wp.
  exists* (glob K){2}; elim* => gd0.
  call{2} (K_decaps_pres gd0).
  wp.
  exists* (glob K){2}; elim* => gd1.
  call{2} (K_decaps_pres gd1).
  skip => /#.
qed.

end section Main.
