# Release Notes — v0.6.0

This release allows a ProofFrog proof to state the concrete security bound it establishes, and has the engine check that claim. It also adds a LaTeX export backend, tuple-destructuring bindings, and a substantial wave of soundness fixes to the canonicalization and equivalence layers.

## Concrete advantage bounds

Previously `prove` told you a proof was valid but not what it proved quantitatively. It now synthesizes the bound ([#243](https://github.com/ProofFrog/ProofFrog/pull/243)):

- **Synthesis.** After a proof verifies, the engine folds its hop sequence into a triangle-inequality sum over the assumptions used, and prints it. Repeated uses of one assumption collapse to `k * Adv^X(B)`; distinct reductions are numbered `B1`, `B2`, and so on.
- **Statistical helper games.** A `.game` file may now declare `advantage <= ...;`. Where a hop reduces to such a game, the opaque advantage term is replaced by the declared expression, with per-oracle query counts derived by statically counting the reduction's oracle calls. So a bound comes out stated in the theorem game's own query counts rather than in symbols the reader has to chase.
- **Checking a claimed bound.** A proof may declare a `bound:` clause stating the bound its author believes it establishes. `prove` decides whether the claim is a valid upper bound on the synthesized one, using SymPy where it can and Z3 over the reals otherwise. The verdict is three-valued: a claim proved smaller than what the proof establishes fails `prove` (override with `--skip-bound`), and an undecidable comparison warns rather than failing.

## LaTeX export

`export-latex` renders primitives, schemes, games, and proofs as typeset pseudocode ([#222](https://github.com/ProofFrog/ProofFrog/pull/222), [#236](https://github.com/ProofFrog/ProofFrog/pull/236)), including name decorations, Iverson-bracket rendering of boolean returns, and upright `this`. Synthesized advantage bounds are typeset alongside ([#243](https://github.com/ProofFrog/ProofFrog/pull/243)). This is preliminary: expect to hand-adjust the output, and for the output style to change in future versions.

## What's new in FrogLang

- **Tuple-destructuring bindings**, so a tuple-returning call can bind its components in one statement ([#220](https://github.com/ProofFrog/ProofFrog/pull/220)).
- **`bound:` clauses** on proofs, and **`advantage <= ...;`** clauses on games, described above ([#243](https://github.com/ProofFrog/ProofFrog/pull/243)).

## Correctness fixes

This release closes a number of cases where the engine could canonicalize two genuinely distinguishable games to the same form, and so report a hop as an equivalence when it was not one. Anyone relying on a proof checked by v0.5.0 should re-run it under this release.

- **Variable capture.** A new global alpha-renaming pass closes a class of capture-based unsoundness, including a loop-binder capture in `SimplifyIf` ([#229](https://github.com/ProofFrog/ProofFrog/pull/229), [#230](https://github.com/ProofFrog/ProofFrog/pull/230)).
- **Passes firing without their preconditions.** Determinism and purity guards, capture-aware fresh naming, and domain-invariance guards on sample-movement passes ([#223](https://github.com/ProofFrog/ProofFrog/pull/223), [RC3](https://github.com/ProofFrog/ProofFrog/pull/226), [RC4](https://github.com/ProofFrog/ProofFrog/pull/227), [RC5](https://github.com/ProofFrog/ProofFrog/pull/228)).
- **Stale facts.** Passes that reused facts invalidated by a later reassignment or by call order ([#233](https://github.com/ProofFrog/ProofFrog/pull/233)), and reference/write-scan blindness ([#225](https://github.com/ProofFrog/ProofFrog/pull/225)).
- **Control flow.** An `if`/`else` whose branches both return could be dropped ([#224](https://github.com/ProofFrog/ProofFrog/pull/224)); branch elimination in `RemoveUnreachable` was unsound for product-typed facts ([#240](https://github.com/ProofFrog/ProofFrog/pull/240)).
- **Z3 and the equivalence layer.** Four soundness holes (F-017, F-106, F-139, F-140) ([#232](https://github.com/ProofFrog/ProofFrog/pull/232)), bitstring literals in the Z3 formula visitor ([#239](https://github.com/ProofFrog/ProofFrog/pull/239)), and the encoding of `ProductType` tuple literals in expression positions ([#244](https://github.com/ProofFrog/ProofFrog/pull/244)).
- **Surface-form conflation.** `UniqueSample` forms are no longer conflated ([#231](https://github.com/ProofFrog/ProofFrog/pull/231)), and a tuple variable declared in more than one place is no longer collapsed ([#241](https://github.com/ProofFrog/ProofFrog/pull/241)).

## Engine improvements

- **Oracle parameter names are canonicalized**, so two games that differ only in what an oracle calls its argument now canonicalize together ([#237](https://github.com/ProofFrog/ProofFrog/pull/237)).

## Miscellaneous

- **Emacs mode** for FrogLang ([#170](https://github.com/ProofFrog/ProofFrog/pull/170)).
- VSCode extension dependency updates ([#245](https://github.com/ProofFrog/ProofFrog/pull/245)).

## Examples

The `applications/cfrg-hybrid-kems/` case study, added in v0.5.0, now carries a report of the findings, a companion summarizing the advantage bound and assumptions of each of the 57 proofs, and a rewritten README describing the artifact itself. Every proof now declares a `bound:` clause, so `prove` checks the stated bound as well as the hop sequence.

Ten of those proofs reduce a hop to a statistical fact about reprogramming a random oracle, stated as one of six helper games in `games/ROM/`, each carrying a declared `advantage <= ...;` clause. Every one of those six games now ships with an EasyCrypt proof of the bound it declares (`games/ROM/*.ec`), so the numbers the helper games assert are checked by a second tool rather than taken on trust. These are written directly in EasyCrypt rather than produced by any exporter, and they cover the six helper games only, not the hybrid KEM theorems that use them.

## Not included

ProofFrog has a work-in-progress exporter that translates a proof into EasyCrypt. It is not part of this release, and no hybrid KEM theorem in the `examples` submodule has an EasyCrypt proof here; the exporter and the proofs it produces live on the `easycrypt` branches of the [engine](https://github.com/ProofFrog/ProofFrog/tree/easycrypt) and [examples](https://github.com/ProofFrog/examples/tree/easycrypt) repositories.
