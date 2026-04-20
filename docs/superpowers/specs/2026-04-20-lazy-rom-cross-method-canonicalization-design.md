# Design: Cross-method canonicalization for oracle-patching idioms (§5.4 elaborated)

**Date:** 2026-04-20
**Status:** implemented; see `docs/superpowers/plans/2026-04-20-lazy-rom-cross-method-canonicalization.md`.
**Supersedes:** §5.4 of `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md` (which sketched the problem but did not settle the design)
**Related:**
- `docs/superpowers/plans/2026-04-20-lazy-rom-cca-case-study-proofs-blocker.md` (blocker that motivated this spec)
- `docs/superpowers/plans/2026-04-20-lazy-map-scan.md` (landed; Pass 1 here builds on it)
- `extras/docs/transforms/SEMANTICS.md` (§6.5, §6.7, §9 — semantic ground truth; §9 grows by one entry here)

## 1. Motivation

The Lazy-ROM CCA case study's §4.1 reduction (and symmetrically §4.2, StarFortress Theorem 1) needs the engine to recognize that a pair of methods using *oracle-patched, lazy-sampled* tables is interchangeable with the *direct* pair that uses the secret key. The just-landed `LazyMapScan` (literal-equality) plus its narrow injective-call recognition are insufficient: the reduction's `R.Hash` scans a map keyed by the wrong type (`T.Input` vs. `T.Image`), and the cross-method consistency between `R.Decaps`'s fresh samples and `R.Hash`'s responses is a genuinely non-local property.

This spec pins down *what* the engine must do and *why each step is sound under SEMANTICS.md*, before the implementation plan touches code. Priority: coherent, general, mathematically sound engine changes — not a fast path to §4.1.

## 2. Core design decisions

### 2.1 Direction of canonicalization: patched → direct

The canonical form of a method is its simplest direct expression. The oracle-patched idiom rewrites *toward* the direct form (the `H(Eval(sk, c))` / `H(z)` pair), not the other way. Parallels existing pipeline direction (`LazyMapToSampledFunction` rewrites the lazy idiom toward its mathematical meaning).

### 2.2 Assumption-game contract-inlining is a user convention, not an engine inference

Assumption games (e.g., `GapTest.Left`) must inline the `TestOracle`'s contract directly in its body:

```
Bool TestOracle(T.Input x, T.Image y) {
    return y == T.Eval(sk, x);
}
```

The engine does **not** synthesize "`Test(x, y) ⟺ y == Eval(sk, x)`" from primitive-level annotations. Reasons:

- A primitive is an abstract interface; it can't name the fixed `sk*` the contract depends on. Any primitive-level annotation would be declaring a fact about state the primitive doesn't reference — conceptually incoherent.
- The contract lives naturally in the game that fixes `sk*`. Writing the body explicitly makes the proof obligation visible and machine-checkable via existing inlining.

Consequence: after composing `GapTest.Left` with a reduction `R`, inlining replaces `challenger.TestOracle(c, e[0])` with `e[0] == T.Eval(sk, c)`. The scan in `R.Decaps` then has the form the landed (literal-equality) `LazyMapScan` handles. *The just-landed `LazyMapScan` injective-call extension is a safety net for opaquely-written assumption games; under this convention it is rarely load-bearing.*

### 2.3 Two small passes, not one monolithic cross-method rewrite

After §2.2's inlining, `R.Hash`'s scan has the form `z == T.Eval(sk, e[0])` — the loop variable `e[0]` is wrapped in a deterministic injective function, not a standalone key. Literal-equality `LazyMapScan` only folds `if (e[0] == K) …` where `K` is loop-invariant, so it doesn't fire. A further consequence: even if the fold happened, the stored map's key type (`T.Input`) would mismatch the query type (`T.Image`), so a downstream `if (z in PendingDecaps)` wouldn't typecheck. Two small, general passes address both issues:

- **Pass 1 (local, reusable):** re-index a `Map<A, V>` to `Map<B, V>` under an injective deterministic function `f : A → B` when every use of the map's keys is through `f`.
- **Pass 2 (cross-method, motivated-by-but-not-tailored-to §5.4):** recognize a *two-map-with-mutual-disjointness-guards* lazy-sample pair as a single sampled `Function<K, V>`, a generalization of §5.3's `LazyMapToSampledFunction`.

Rejected alternatives:
- **Monolithic "oracle-patching canonicalization" pass** (the original §5.4 sketch). Rewrites the whole `(Decaps, Hash)` pair in one step. Conflates several soundness arguments into a wall of conditions; won't generalize beyond §4.1/§4.2.
- **Pair-of-maps-as-Function view** (abstract intermediate). Would require new type machinery; too heavy for the payoff.

## 3. Pass 1 — Key re-indexing under injective deterministic function

### 3.1 Shape

Input shape (sketch):

```
Map<A, V> M;
// in some method α:
M[f(a)] = s;       // or M[a_which_equals_f_of_something] = s;
// in some other method β:
... M[f(a')] ...   // every use is of the form M[f(_)]
for (e in M.entries) { body(e[0], e[1]) }  // if present, body uses e[0] only via f(e[0])
```

Rewritten:

```
Map<B, V> M';       // B = return type of f
M'[f(a)] = s;       // unchanged stored key expression
... M'[f(a')] ...
for (e in M'.entries) { body_with_e0_substituted(e[1]) }
```

In the §4.1 case, `M = PendingDecaps`, `A = T.Input`, `B = T.Image`, `f(c) = T.Eval(sk, c)`. The store `PendingDecaps[c] = s` is the shape where the stored key is the raw parameter `c` rather than `f(c)`; the rewrite changes both the map's declared type and the stored key expression — `Map<A, V> M; M[a] = s` with all reads of `M` through `f(_)` rewrites to `Map<B, V> M'; M'[f(a)] = s`. Loop bodies with `e[0]` under `f` have their `f(e[0])` occurrences substituted by the new `e[0]` (which now holds the image value directly). *After Pass 1 fires, the §4.1 `R.Hash` scan predicate `z == T.Eval(sk, e[0])` becomes `z == e[0]`, and a subsequent fixed-point iteration of `LazyMapScan` folds it to a literal-equality lookup.*

### 3.2 Preconditions

P1-1. `f` is a primitive method annotated `deterministic injective`, or a composition of such methods applied pointwise to the key variable (MVP: single method call only).

P1-2. The non-varying arguments of `f` are game/scheme fields that are **read-only after `Initialize`** — never assigned in any oracle method body. Verified syntactically.

P1-3. **Every** syntactic use of `M` treats its keys as `f(·)`:
- Writes: `M[k] = v` where `k` is either syntactically `f(a)` for some `a`, or a loop variable `a` whose scope ensures `f(a)` can be substituted (the helper shape above).
- Reads: `M[k]`, `k in M`, iteration over `.keys` / `.entries` — each key access is inside a larger expression of form `f(·)` or `e[0]` is used only via `f(e[0])` in loop bodies.
- `|M|` reads are allowed (preserved under bijection).

P1-4. `M` is a game/scheme/reduction field (not a local variable), because re-indexing changes the declared type of the field.

Any precondition failure emits a `NearMiss` naming the specific violation (which method annotation is missing, which field is mutably reassigned, which syntactic use is not under `f`).

### 3.3 Soundness under SEMANTICS.md

For every adversary-visible behavior, the original program and the rewritten program induce identical distributions over outputs. Argument:

- **Value preservation.** For each key `a` stored, original stores `M[a] := s`; rewritten stores `M'[f(a)] := s`. By P1-1 `f` is deterministic, so `f(a)` is a single value; by P1-2 `f` is a pure function of `a` (other args fixed post-`Initialize`), so evaluations of `f(a)` at different program points with the same `a` yield the same value. Thus reads `M'[f(a)]` return `s` iff original reads `M[a]` return `s`. (§6.4: determinism semantics; §6.7: map update/lookup.)
- **Injectivity / non-collision.** Distinct `a1 ≠ a2` produce distinct `f(a1) ≠ f(a2)` by P1-1, so `M'` has the same domain-cardinality relationship to the set of stored keys as `M`. No accidental overwrites are introduced. (§6.7.)
- **`|M'| = |M|`.** Follows from bijection between `dom M` and `f(dom M)` via injectivity.
- **Iteration.** §4.5: iteration order over a map's entries is unspecified. Both original and rewritten are unspecified. P1-3 ensures the loop body's only use of `e[0]` is under `f`, so substituting `e[0] := f(e[0]_original)` yields a body with identical behavior on each matched entry.
- **Adversary-visible behavior.** `M` / `M'` are internal state (§6.3 Scope); the adversary observes only oracle return values. Since every return value is preserved by the above, distributions over adversary outputs are identical.

No new equivalence needs to land in SEMANTICS.md §9 for Pass 1 — it's a program rewrite justified by substitution plus §6.4/§6.7 as stated.

### 3.4 What Pass 1 does NOT do

- Does not apply to `Array`s (domain shape differs; out of scope).
- Does not invert `f` — we never need `f^{-1}`; we only forward-compose.
- Does not fire when `M`'s keys are sometimes used as raw `A` (e.g., an oracle returns `e[0]` to the adversary). P1-3 rules that out; near-miss fires.

## 4. Pass 2 — Disjoint-pair lazy-map-to-Function

### 4.1 Shape

Two map fields `M1 : Map<K, V>` and `M2 : Map<K, V>` (same types post-Pass-1) in the same game, each accessed via a lazy-sample idiom with guards excluding the other map's domain:

```
// in any method that reads M1:
if (k in M1) { ... use M1[k] ... }
else if (k in M2) { ... use M2[k] ... }
else { V s <- V; M1[k] = s; ... return s ... }   // or symmetric M2 write

// in any method that reads M2: symmetric
```

Canonicalizes to a single sampled function:

```
Function<K, V> F;
// and in the original program's let:/field block:
F <- Function<K, V>;
// each lazy-idiom path collapses to: return F(k);
```

(A non-sampled `Function` captures the same consistency but is semantically a known deterministic function; for the random-oracle use case we land the sampled form, `F <- Function<K, V>`, matching how §5.3 emits its canonical form.)

### 4.2 Preconditions (each failure → `NearMiss`)

P2-1. **Shape.** Each of `M1`, `M2` is accessed *only* through the lazy-idiom shape (same as §5.3 S3(a)): no cardinality reads, no iteration-for-other-purposes, no direct external reads/writes.

P2-2. **Empty on creation.** Both maps are uninitialized / unassigned in `Initialize` (inherit §6.7 empty-on-creation). Verified syntactically.

P2-3. **Mutual disjointness guards.** Every write `Mi[k] = s` (for `i ∈ {1, 2}`) is preceded in its control-flow path by a check that excludes `k` from *both* maps — i.e., `k !in M1 && k !in M2`, or equivalently the else-branch of `if (k in M1) {...} else if (k in M2) {...} else { Mi[k] = ... }`. Verified syntactically as a guarded-write shape.

P2-4. **Matching value sampling.** Each `M1[k] <- V` and `M2[k] <- V` sample from the *same* type `V` with the same sampling form. (Needed for the merged `Function<K, V>` to have a single well-defined output type.)

P2-5. **Same key type.** `M1, M2 : Map<K, V>` with identical `K` and `V`. After Pass 1 fires, this is generally true for the §4.1 case.

### 4.3 Soundness under SEMANTICS.md §6.5

Claim: under P2-1 through P2-5, the pair `(M1, M2)` accessed via the guarded lazy idiom is interchangeable with a single sampled `Function<K, V>`.

Argument:

- By P2-3, on every read path, *exactly one* of `{k in M1, k in M2, k in neither}` is true, and on-write `M1[k]` and `M2[k]` are never both populated for the same `k` simultaneously. The combined "is `k` stored in either" relation and "what value is stored" relation together define a single lazy lookup table.
- By P2-1 + P2-2, no access path depends on `|M1|`, `|M2|`, iteration order, or the partition of stored keys between `M1` and `M2`.
- By P2-4, the fresh-sample distribution is uniform over `V` (the same `V` in both maps).
- By §6.5, a lazily-populated lookup table that (a) is empty on creation, (b) on a fresh key samples uniformly from `V` and stores it, and (c) on a stored key returns the stored value, is equivalent to `Function<K, V>` sampled uniformly from all functions `K → V`.
- Adversary-visibility: §6.3 — maps are internal state; the adversary sees only oracle return values. Return values are preserved by the above.

Therefore the pair is interchangeable with `Function<K, V> F; F <- Function<K, V>; ... return F(k);` under P2.

### 4.4 SEMANTICS.md extension

Land one new bullet under §9.3 Random Function Simplification:

> **Guarded two-map lazy lookup:** Two `Map<K, V>` fields accessed only through the lazy-sample idiom, with every write guarded by membership checks excluding both maps, and matching `V`-sampling, are equivalent to a single sampled `Function<K, V>` with each lazy-path occurrence rewritten as `F(k)`. (Soundness: §6.5.)

And a brief note in §6.5 cross-referencing §9.3 for the multi-map generalization.

### 4.5 Pass 2 as new pass vs. §5.3 extension

Land **new pass**, `LazyMapPairToSampledFunction` (or similar name, TBD in plan), registered in `CORE_PIPELINE` immediately after `LazyMapToSampledFunction`. Rationale:
- Different soundness story (cross-method disjointness vs. single-method shape); keeping them separate keeps each pass's soundness obligation localized.
- Two maps → one `Function` is a distinct shape from one map → one `Function`; matcher logic doesn't share much.
- If an independent use of Pass 2 surfaces, it lands without needing `LazyMapToSampledFunction` to have cross-method behavior.

The existing `LazyMapToSampledFunction` is untouched.

## 5. Pipeline ordering

Within `CORE_PIPELINE`, ordering:

1. Inlining (existing; already runs first).
2. `LazyMapScan` (landed; literal-equality + injective-recognition).
3. **Pass 1 — `MapKeyReindex`** (new).
4. `LazyMapToSampledFunction` (landed §5.3).
5. **Pass 2 — `LazyMapPairToSampledFunction`** (new).
6. `ExtractRFCalls` and downstream (unchanged).

Rationale:
- Pass 1 must run after `LazyMapScan` so any literal-equality scans that can fold do so first (Pass 1 doesn't attempt to fold scans).
- Pass 1 must run before §5.3 so §5.3 sees the re-indexed map with the shape it already handles.
- Pass 2 runs after §5.3 so single-map cases are handled first; what reaches Pass 2 is the genuine two-map cross-method idiom.

Pipeline is a fixed-point loop, so ordering matters for which pass fires first but not for the fixed-point result (assuming confluence — a separate soundness question, addressed by each pass's local soundness).

## 6. User-facing conventions

Document in `CLAUDE.md` "Guidelines for creating FrogLang files" and in the case-study README:

> **Assumption-game oracle bodies should inline semantic contracts directly.** When writing an assumption game (e.g., `GapTest`) whose helper oracle witnesses a relation like "does `y = Eval(sk, x)`?", write the oracle body as the relation itself (`return y == T.Eval(sk, x);`), not as an opaque primitive call. This makes the contract visible to the engine's inlining + `LazyMapScan` pipeline and avoids relying on the injective-call recognition fallback.

## 7. Test strategy

Per CLAUDE.md test discipline, each new pass gets:

**Pass 1 (`MapKeyReindex`):**
- Positive unit tests in `tests/unit/transforms/test_map_key_reindex.py`:
  - Minimal two-method program: method writes `M[c] = s`, reads occur only via `M[f(c')]` or loop `e[0]` under `f`.
  - Verify canonical AST matches `M'[f(c)] = s`.
- Negative unit tests + near-miss entries in `tests/unit/transforms/test_near_misses.py`:
  - `f` not annotated `deterministic` (expect declined + specific near-miss).
  - `f` not `injective`.
  - `f`'s non-varying arg is mutably assigned outside `Initialize`.
  - Map key used as raw `A` somewhere (e.g., returned directly).

**Pass 2 (`LazyMapPairToSampledFunction`):**
- Positive unit tests in `tests/unit/transforms/test_lazy_map_pair_to_sampled_function.py`:
  - Synthetic two-method program with two `Map<K, V>` fields, both guarded-lazy-idiom, disjointness checks in place.
  - Verify canonical form is single `F <- Function<K, V>` plus `F(k)` calls.
- Negative unit tests + near-miss entries:
  - Missing disjointness guard on one write.
  - Mismatched `V` types.
  - One map used non-lazily (e.g., cardinality read).
  - Mismatched `K` types (to confirm Pass 2 declines if Pass 1 hasn't run / didn't apply).

**Integration:**
- §4.1 `DecapsIter-IND-CCA.proof` verifies end-to-end via `prove`.
- §4.3 `HashedElGamal-KEM-IND-CCA.proof` verifies end-to-end.
- These are the case-study vectors from the existing plan, gated on Pass 1 + Pass 2 landing.

## 8. Success criteria

- Pass 1 and Pass 2 land with positive + negative tests; `make lint` and `pytest` pass.
- SEMANTICS.md §9.3 gains one new bullet; §6.5 gains a cross-reference.
- §4.1 `DecapsIter-IND-CCA.proof` verifies end-to-end.
- §4.3 `HashedElGamal-KEM-IND-CCA.proof` verifies end-to-end.
- `CLAUDE.md` documents the assumption-game contract-inlining convention.
- The existing 2026-04-20 spec's §5.4 gains a forward reference to this spec.

## 9. Out of scope

- §4.2 `HashIter` / StarFortress Theorem 1: should land for free once Pass 1 + Pass 2 are in, but verifying those proofs is a follow-up plan.
- FO transform, OAEP: use re-encryption rather than oracle-patching; orthogonal canonicalization problem.
- Inferring the `TestOracle(x, y) ⟺ y == Eval(sk, x)` contract from primitive annotations: deliberately rejected (§2.2).
- `Array` re-indexing: orthogonal; `Map` is the motivating case.

## 10. Open questions left to the implementation plan

- Exact matcher representation for Pass 1's "every use is under `f`" precondition (AST walker? Visitor? Reuse an existing uses-of-field analysis?).
- Exact matcher for Pass 2's guarded-write shape — how lenient to be about the guard's exact control-flow structure (e.g., `else if` chain vs. nested `if`s with `!in` conditions).
- Whether Pass 2's "same-game" requirement needs any cross-module analysis (probably not; both maps are same-game fields).
- Whether the new passes need `PipelineContext`-level state beyond the existing near-miss list.
