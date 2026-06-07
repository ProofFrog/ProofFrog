# Release Notes — v0.5.0

This release is driven by a large new case study: complete, machine-checked
ProofFrog analyses of the four hybrid KEM combiners from
[`draft-irtf-cfrg-hybrid-kems-10`](https://datatracker.ietf.org/doc/html/draft-irtf-cfrg-hybrid-kems-10), plus a Hashed ElGamal KEM. Writing these
proofs motivated new FrogLang features for writing proofs over hash functions
modelled as random oracles and over group-based schemes, a wave of new
canonicalization power in the engine, and several correctness fixes that make
the engine's interchangeability checks more trustworthy.

## What's new in FrogLang

These features let you write proofs that the engine previously could not check
(all part of [#211](https://github.com/ProofFrog/ProofFrog/pull/211)):

- **Random oracles via lazy maps.** A common way to model a random oracle is a
  lazily-populated map: on each query, sample a fresh value if the input is new
  and otherwise return the stored one. The engine now recognizes this idiom —
  including the case where two oracles share one table, and the case where the
  table is scanned to find a matching entry — and treats it as a sampled
  `Function<D, R>`. In practice you can now write ROM proofs in the natural
  lazy-table style instead of hand-massaging them into `Function` form.

- **Iterating over collections.** `for` loops can now range over an
  `Array<T, n>` and over a map's `keys`, `values`, or `entries`.

- **Sampling with exclusions.** New `<- T \ S` syntax samples uniformly from
  type `T` excluding the elements in set `S` (for example, sampling a challenge
  that must differ from previously-seen values).

- **Stating structural assumptions.** A proof may now include a `requires:`
  block to declare structural facts the proof depends on (for example, that a
  group has prime order). The engine uses these when justifying hops.

- **More flexible file layout.** Reductions and games may now be written after
  the `proof` block as well as before it.

## Engine improvements

The engine can now canonicalize — and therefore check the interchangeability of
— many more pairs of games, particularly for proofs involving random oracles and
group-based schemes:

- **Lazy-map / random-oracle reasoning** (see above), which underpins the new
  ROM proofs ([#211](https://github.com/ProofFrog/ProofFrog/pull/211)).
- **Group-exponent algebra.** The engine recognizes more equalities and
  rewrites involving group exponentiation (e.g. relating `g^(a*b)` to `f^b`
  when `f = g^a`), and decomposes equalities of concatenations and of injective
  functions into their component parts
  ([#211](https://github.com/ProofFrog/ProofFrog/pull/211)).
- **Control-flow normalization.** A range of new passes normalize equivalent
  but differently-written conditional code, so that games that differ only in
  how their `if`/`else` and early-return logic is arranged now canonicalize to
  the same form ([#212](https://github.com/ProofFrog/ProofFrog/pull/212)).
- **Better cross-method and inlining behavior**, plus a roughly 30% reduction in
  canonicalization time on the new proofs
  ([#211](https://github.com/ProofFrog/ProofFrog/pull/211)).

## Correctness fixes

Several fixes make the engine's "these two games are interchangeable" verdict
more trustworthy by closing cases where it could previously canonicalize two
genuinely-distinguishable games to the same form:

- **Statement reordering across an early return.** The engine could move a state
  update past an `if (...) return ...;` guard — including updates to a map or
  array entry — yielding a game an adversary could tell apart by calling the
  same oracle twice. Reordering now respects these guards as barriers
  ([#209](https://github.com/ProofFrog/ProofFrog/pull/209)).
- **A canonicalization crash** on certain function calls inside conditions has
  been fixed, along with an inlining bug that could drop a variable declaration
  when a returning call was distributed across `if` branches
  ([#212](https://github.com/ProofFrog/ProofFrog/pull/212)).
- Numerous existing transforms were hardened to decline in cases where they
  previously fired unsoundly, with clearer "near-miss" diagnostics explaining
  why a transform did not apply
  ([#211](https://github.com/ProofFrog/ProofFrog/pull/211)).

## Miscellaneous

- Diagnostic commands (`canonicalization-trace`, `step-detail`) now use the same
  proof context as `prove`, so the state they show matches what the proof
  engine actually sees ([#211](https://github.com/ProofFrog/ProofFrog/pull/211)).
- VSCode extension (0.1.1): syntax highlighting for the new `requires` clause
  ([#217](https://github.com/ProofFrog/ProofFrog/pull/217)), plus dependency
  updates ([#210](https://github.com/ProofFrog/ProofFrog/pull/210),
  [#216](https://github.com/ProofFrog/ProofFrog/pull/216)).
- Expanded test coverage, including a harness that checks each canonicalization
  preserves behavior across repeated oracle calls
  ([#211](https://github.com/ProofFrog/ProofFrog/pull/211)).

## New examples

The `examples` submodule adds two case studies
([examples #43](https://github.com/ProofFrog/examples/pull/43)):

- **Hybrid KEM combiners from [`draft-irtf-cfrg-hybrid-kems-10`](https://datatracker.ietf.org/doc/html/draft-irtf-cfrg-hybrid-kems-10)**
  (`applications/cfrg-hybrid-kems/`). FrogLang definitions and machine-checked
  proofs for all four combiners in the draft (CG, CK, UG, and UK), each in two
  variants. The proofs cover correctness, IND-CCA security (for both the
  post-quantum and traditional branches), and the LEAK-BIND and HON-BIND binding
  properties. A README documents the modelling choices, the mapping from draft
  sections to files, and the assumptions each proof relies on.
- **Hashed ElGamal KEM**: an IND-CCA proof from gap-CDH in the random oracle
  model, together with the supporting group-theory proofs and a tidied-up
  `HashedDDH` game and its reductions.

The example proofs have also been reorganized to place each proof's reductions
and intermediate games after its main `proof` block, taking advantage of the
more flexible file layout described above
([examples #44](https://github.com/ProofFrog/examples/pull/44)).
