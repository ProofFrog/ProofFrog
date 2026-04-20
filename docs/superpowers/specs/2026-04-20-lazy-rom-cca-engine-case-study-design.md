# Design: Lazy-ROM CCA engine case study

**Date**: 2026-04-20
**Status**: design approved, awaiting implementation plan
**Related**: `extras/docs/plans/todo/2026-04-19-ug-kem-cca-sdh-via-leftright.md` (Blocker B)

## 1. Motivation

StarFortress Theorem 1 (`extras/examples/starfortress/proof/prooffrog/UG-KEM-CCA-SDH.proof`) stalls on two engine gaps when writing the SDH reduction (`Blocker B` in the referenced plan):

1. **Map iteration** in FrogLang (no syntax currently accepted by the typechecker for iterating `Map` entries).
2. **Canonicalization** of the "lazy-sample + helper-oracle patching" idiom as equivalent to "direct secret-key decryption".

These gaps are not StarFortress-specific. They recur across the textbook ROM+CCA literature: Hashed ElGamal / DHIES, Twin-DH KEM, and structurally in FO/OAEP (though FO/OAEP use re-encryption rather than an oracle helper — out of scope here).

This design specifies a minimal case study that exercises both gaps outside the StarFortress scaffolding, plus one real-world validation proof (Hashed ElGamal CCA from gap-CDH). The goal is twofold:

- **Development harness**: a small, self-contained FrogLang corpus for iterating on the engine changes.
- **Generalization validation**: evidence that investment in these engine features pays off beyond StarFortress.

## 2. Scope & deliverables

Three FrogLang artifacts in `extras/examples/engine-case-studies/lazy-rom-cca/`:

- **A. Abstract synthetic primitive `TrapdoorTest`** plus companion left/right assumption game `GapTest`. Section 3 below.
- **A1. `DecapsIter` scheme** + CCA proof: iteration happens at `Decaps` time over `Hash`-queries (Hashed-ElGamal pattern). Exercises map iteration + lazy-RF-as-Map.
- **A2. `HashIter` scheme** + CCA proof: iteration happens at `Hash` time over `Decaps`-queries (StarFortress Theorem 1 pattern). Exercises map iteration *and* oracle-patching canonicalization.
- **B. Real-world validation: Hashed ElGamal CCA from gap-CDH** — `DecapsIter` instantiated to a cyclic group with `Eval(sk, x) = x^sk` and `Test = DDH check`. Written after A verifies, confirms the synthetic version isn't missing load-bearing structure.

Plus the engine work in §5 and the soundness obligations in §6.

**Explicitly deferred** (covered in follow-up designs, not here):

- Fujisaki-Okamoto transform, OAEP: need map iteration but use re-encryption checks rather than oracle-patching. Reusing §5.1/§5.3 but needing a different (re-encryption) canonicalization.
- HPKE: composite; not a minimal example.
- Cramer-Shoup: standard model; does not need any of this.
- General `Array` iteration beyond fixed-size loops: orthogonal.

## 3. The synthetic primitive and assumption game

### 3.1 `TrapdoorTest` primitive

```
Primitive TrapdoorTest {
    Set Input;
    Set Secret;
    Set Image;

    Secret KeyGen();
    deterministic Image Eval(Secret sk, Input x);
    deterministic injective Bool Test(Input x, Image y);
}
```

The `Test` contract: given a fixed (implicit) `sk*`, `Test(x, y) = true` iff `y = Eval(sk*, x)`. The `deterministic injective` annotations are load-bearing for soundness (see §6, S2).

### 3.2 `GapTest` assumption game

Left/right game with three oracles:

- `Initialize() -> Input`: samples `sk* <- Secret`, `x* <- Input`; returns `x*`.
- `TestOracle(x, y) -> Bool`: returns `Test_{sk*}(x, y)` on **both** sides (the gap helper).
- `Solve(y) -> Bool`: on Left returns `y == Eval(sk*, x*)`; on Right returns `false`.

Modeled on `examples/Games/Group/CDH.game` and `extras/examples/starfortress/proof/prooffrog/games/SDH.game`. The distinction between sides is purely in `Solve`: on Right the challenge image is unrelated to any adversary query; on Left an adversary output matching `Eval(sk*, x*)` is detectable. This mirrors the gap-CDH pattern where DDH is a helper oracle and only `Solve` distinguishes the sides.

## 4. The two schemes and their proofs

### 4.1 `DecapsIter` scheme (Hashed-ElGamal pattern)

**Encaps**: `x <- Input; return (x, H(Eval(sk, x)))`.
**Decaps(sk, x)**: `return H(Eval(sk, x))`.

The `Hash` input is `Eval(sk, x)`, i.e., the secret image. The reduction holds `ek` but not `sk`. To answer `Decaps(x)` without `sk` it iterates previously-seen `Hash` queries and uses `TestOracle` to identify the one whose input `z` satisfies `z = Eval(sk*, x)`:

```
// Reduction.Decaps
for ([Image, BitString<n>] entry in HashTable.entries) {
    if (challenger.TestOracle(x, entry[0])) { return entry[1]; }
}
// No prior hash query matches: sample fresh, log under a pending-table
BitString<n> s <- BitString<n>;
PendingDecaps[x] = s;
return s;
```

`Hash(z)` consults `PendingDecaps` in reverse (is there some stored `(x, s)` with `Test(x, z)`?) so consistency across the two tables is maintained. Exercises **§5.1 + §5.3** of the engine work.

### 4.2 `HashIter` scheme (StarFortress pattern)

Inverted ciphertext shape. `Encaps(ek) = (c, ss)` where `c = (x, tag)` carries the `Input` directly and the shared secret is `ss = H(x || Eval(sk, x))`. `Decaps((x, tag))` returns `H(x || Eval(sk, x))`.

The reduction, not knowing `sk`, on `Decaps((x, tag))` samples `s <- BitString<n>` fresh and stores `(x, s)` in a table. On `Hash(m)` where `m = x' || y'`, it iterates the Decaps-table, calling `challenger.TestOracle(x_entry, y')` per entry; on a match, returns the stored `s`; otherwise returns `RF(m)`.

Exercises **§5.1 + §5.3 + §5.4**.

### 4.3 Hashed ElGamal CCA (validation)

Instantiate `TrapdoorTest` via:

- `Input = GroupElem<G>`, `Secret = ModInt<G.order>`, `Image = GroupElem<G>`.
- `Eval(sk, x) = x ^ sk`.
- `Test(x, y)` = "given public `ek = G.generator ^ sk*`, does `x ^ sk* = y`?" — this is the gap-DDH helper (decidable via a DDH oracle or pairing).

Instantiate `GapTest` as gap-CDH. The proof structure is identical to `DecapsIter`. Validates that the synthetic primitive is not missing group-specific structure that the engine needs to reason about.

## 5. Engine work

### 5.1 Typecheck `GenericFor` over `Map` and `Array`

The grammar already accepts `for (Type id in expression) block` (parsed as `GenericFor` in `proof_frog/frog_ast.py:545`). `proof_frog/semantic_analysis.py:1346` currently restricts the `over` expression to `Set<T>`.

Extend `leave_generic_for` to accept:

- `for (T x in A)` where `A : Array<T, n>`.
- `for (K k in M.keys)` where `M : Map<K, V>`.
- `for (V v in M.values)` where `M : Map<K, V>`.
- `for ([K, V] e in M.entries)` where `M : Map<K, V>`.

Add `.keys`, `.values`, `.entries` as field-access expressions typed `Set<K>`, `Set<V>`, `Set<[K, V]>` respectively. Iteration order over all of these is **unspecified** (consistent with `Set` per SEMANTICS.md §4.5).

Parser already accepts field-access expressions; only typing plus AST marking is needed.

### 5.2 Engine handling of iteration (shape recognition)

Two concerns, treated separately:

- **Symbolic execution**: unknown-size loops cannot be unrolled. The MVP does not attempt general loop reasoning. Instead, it recognizes specific loop *shapes* via a dedicated `TransformPass`.
- **Equivalence of two loops under body rewriting**: punted to canonicalization of the specific shapes below.

The MVP shape-recognition pass `LazyMapScan` matches:

```
for ([K, V] e in M.entries) {
    if (Pred(e[0])) { return Body(e); }
}
return Default;
```

and canonicalizes it against a semantically equivalent direct computation when the per-shape soundness preconditions (§6) hold.

### 5.3 Lazy-RF-as-Map canonicalization

Recognize that

```
Map<D, R> T; ... if (x in T) { return T[x]; } R s <- R; T[x] = s; return s;
```

is interchangeable with `Function<D, R> F <- Function<D, R>; return F(x);`. Sound by SEMANTICS.md §6.5, which defines a random function as a lazily-populated lookup table. Independently useful outside this case study.

### 5.4 Oracle-patching canonicalization (the hard one)

Recognize the cross-method pair:

- **Method α** (e.g., `Decaps`): sample `y <- Range` fresh, log `(x, y)` in some `Map<Input, Range> StoreA`, return `y`.
- **Method β** (e.g., `Hash`): scan `StoreA`, using `challenger.TestOracle(x_logged, y_query_derived_from_β's_arg)` to find a match; on match return the stored value; else return `RF(m)` (or similar fresh-sampling fallback).

…as interchangeable with the "direct" pair:

- **Method α**: return `H(x || Eval(sk*, x))` (or scheme-specific direct computation using the secret key).
- **Method β**: return `H(β's arg)`.

Sound only under the preconditions in §6 (S2, S4). Expected approach: a dedicated `TransformPass` operating on matched method pairs, analogous in spirit to `CrossMethodFieldAlias` but scanning for `LazyMapScan` + paired store shapes. Requires `deterministic injective` on `Eval`/`Test`.

If during implementation this proves too narrow to fit as a single local pass, the implementation plan will revisit — options include narrowing the pattern further, introducing a new pipeline stage in `pipelines.py`, or requiring explicit user-supplied lemmas.

### 5.5 Near-miss instrumentation and diagnostics

Per CLAUDE.md, each new `TransformPass` adds a `NearMiss` entry at each precondition-failure site, and `proof_frog/diagnostics.py` is updated with a registry entry explaining the gap. Specifics: see S5 below.

## 6. Soundness obligations

These preconditions are **load-bearing**. Each new transform pass must verify and near-miss on failure.

### S1. Iteration order

Set-like iteration order is unspecified per SEMANTICS.md §4.5; the same applies to `Map.keys/.values/.entries`. Any transform whose result depends on iteration order is unsound.

`LazyMapScan` (§5.2) fires only when:

- The body has the shape `if (Pred(e)) { return Expr(e); }` and contains no other statements.
- Under S2's match-uniqueness argument, `Pred(e)` holds for at most one `e` per execution, making order immaterial.

Both conditions must be syntactically verified. Either failure → `NearMiss`, no rewrite.

### S2. Uniqueness of match via `injective`

Oracle-patching (§5.4) is sound only when the scan identifies at most one stored entry per call. For scans using `challenger.TestOracle(x_entry, target)`, uniqueness follows from `Test`'s `injective` contract: for any fixed `sk*` and `x`, there is exactly one `y` with `Test_{sk*}(x, y) = true` (namely `Eval(sk*, x)`).

Pass preconditions:

- `Test` / the challenger oracle used in the scan is annotated `deterministic injective` at the primitive level.
- The scan predicate is a `challenger` call whose non-loop argument is deterministic across the loop body.

Stricter than `ChallengeExclusionRFToUniform`: there `injective` is used for seeing through wrappers when checking input distinctness; here `injective` is load-bearing for uniqueness of the match itself.

### S3. Distribution preservation for lazy-RF-as-Map (§5.3)

The pattern in §5.3 is equivalent to a `Function<D, R>` only when:

- (a) the map `T` is accessed *exclusively* through the lazy-sample idiom shape (i.e., no other reads/writes elsewhere in the program),
- (b) `T` is initialized empty (default per SEMANTICS.md §6.7),
- (c) `T` is not passed to any operation whose semantics depend on `|T|` (cardinality, iteration for a non-LazyMapScan purpose, etc.).

Failure → `NearMiss` citing which violation was detected, no rewrite.

### S4. Cross-method invariants for oracle-patching

The rewrite equates two *pairs* of methods. Its correctness depends on a cross-oracle invariant: for every `(x, s)` stored in method α's table, `s` equals what the direct method β would return on the corresponding input. The MVP verifies this invariant **structurally**, by requiring that:

- α's sampling shape `s <- BitString<n>; Store[x] = s; return s` matches the range and distribution of β's direct computation.
- β's fallback `return RF(m)` matches β's direct computation on "unstored" inputs — verified by the lazy-RF-as-Map shape (§5.3) applied to `RF`.

If the structural match fails, decline and emit near-miss. If the MVP turns out too narrow (e.g., the scheme's direct computation is a more elaborate expression than a single RF call), the implementation plan falls back to requiring user-supplied lemma hops for the method pair.

### S5. Near-miss completeness

For each of S1–S4, the transform pass emits a specific `NearMiss` on failure, naming the failing precondition and the offending program location (map name, method, missing annotation, witness statement violating the shape). `proof_frog/diagnostics.py` registry updated with corresponding engine-limitation entries so `check` / `prove` surface actionable messages.

### Test discipline

Every new `TransformPass` gets:

- **Positive tests** in `tests/unit/transforms/`: minimal synthetic programs where the pass must fire, asserting a specific canonical form.
- **Negative tests** in the same file plus `tests/unit/transforms/test_near_misses.py`: one variant per precondition, asserting the pass declines and emits the matching near-miss.

This matches the CLAUDE.md "positive and negative unit tests" rule and the "near-miss instrumentation" rule for new transforms.

## 7. Out of scope for this spec

Deliberately left for the implementation plan, not the design:

- Exact `TransformPass` class names, file layout within `proof_frog/transforms/`.
- Exact pipeline insertion order in `proof_frog/transforms/pipelines.py`.
- Whether §5.4 is one pass or several.
- Exact test file paths and fixture layout.

The implementation plan may need to be **split** into sub-plans, since §5.4 alone is plausibly a multi-week effort. A likely decomposition:

1. Typecheck + AST work for `GenericFor` over Map/Array (§5.1) + minimal engine unroll recognition.
2. `LazyMapScan` shape recognition (§5.2) + lazy-RF-as-Map (§5.3) with S1, S3, S5 preconditions. Enough to write `DecapsIter` and Hashed ElGamal.
3. Oracle-patching canonicalization (§5.4) with S2, S4, S5 preconditions. Unlocks `HashIter` and StarFortress Theorem 1.
4. Validation proofs: write A1, A2, B and run them through `make lint` / `pytest`.

### 7.1 Implementation notes

- **§5.3 `LazyMapToSampledFunction` (landed 2026-04-20):** registered in
  `CORE_PIPELINE` immediately before `ExtractRFCalls`. Consequence for the
  next sub-plan: by the time `LazyMapScan` (§5.2) runs in the same fixed-point
  iteration, a `Map<K, V>` field that meets the idiom shape has already been
  rewritten to a sampled `Function<K, V>`. `LazyMapScan` must therefore match
  the canonical `Function<K, V>` form (not `Map<K, V>`) when the scan shares
  a game with the lazy-lookup idiom; or, if it wants to see the `Map`, it
  must be registered before `LazyMapToSampledFunction` in `CORE_PIPELINE`.
  Near-miss instrumentation covers S3(a)–(c) (explicit Initialize touch,
  non-idiom method reference, prefix reference); the pass emits no near-miss
  when no idiom is present anywhere in the game (silent skip). No entry was
  added to `proof_frog/diagnostics.py` — the near-miss path is sufficient.

**Next step (chosen 2026-04-20):** write the §4.1 `DecapsIter` CCA proof
and the §4.3 Hashed ElGamal CCA validation proof as FrogLang artifacts
under `extras/examples/engine-case-studies/lazy-rom-cca/`, then run them
through `prove` end-to-end. This exercises §5.1 + §5.2 + §5.3 as a set and
catches any load-bearing gap in the MVP before §5.4 oracle-patching
compounds on it. §5.4 (and therefore §4.2 `HashIter` + StarFortress
Theorem 1) is deferred until the case-study proofs verify.

- **§5.2 `LazyMapScan` (landed 2026-04-20):** registered in `CORE_PIPELINE`
  immediately before `LazyMapToSampledFunction` (in
  `proof_frog/transforms/map_iteration.py`). The MVP handles the
  literal-equality scan shape
  `for ([K, V] e in M.entries) { if (e[0] == key) { return Body(e); } }` →
  `if (key in M) { return Body[e[0]:=key, e[1]:=M[key]]; }`. Soundness: S1
  (body shape) verified syntactically; S2 uniqueness comes from map-key
  uniqueness in this MVP — no `injective` annotation required. The
  injective-challenger-call variant of S2 remains for the §5.4 oracle-patching
  plan, which will extend `LazyMapScan` (or add a sibling pass) to also match
  `challenger.TestOracle(arg, e[0])` predicates when `Test` is annotated
  `deterministic injective`. Near-miss instrumentation covers body-shape,
  key-references-loop-variable, and else-branch violations; the pass emits no
  near-miss when no scan-over-`.entries` pattern is present (silent skip). No
  entry added to `proof_frog/diagnostics.py` — near-miss path is sufficient.

## 8. Success criteria

- `prove` verifies A1 (`DecapsIter` CCA proof) end-to-end after (1) and (2) land.
- `prove` verifies A2 (`HashIter` CCA proof) end-to-end after (3) lands.
- `prove` verifies B (Hashed ElGamal CCA) end-to-end after (2) lands.
- Unblocking `UG-KEM-CCA-SDH.proof` Steps 4 and 6 via the `R_SDH'` reduction (reformulated per the 2026-04-19 plan) requires exactly the features in §5.1–§5.5, with no further new machinery.
- `make lint` and `pytest` pass throughout.
- Near-miss diagnostics exercised: at least one negative proof fragment per precondition (S1–S4) produces actionable diagnostic output.
