# Writing ProofFrog proofs — workflow rules

Instruction-style guidance for an agent authoring or editing a `.proof`
file. For the language reference see [FROGLANG_REFERENCE.md](FROGLANG_REFERENCE.md);
for engine capabilities see [TRANSFORMS.md](TRANSFORMS.md); for MCP tool
usage see [MCP_GUIDE.md](MCP_GUIDE.md). Human-facing tutorials and
worked examples live at <https://prooffrog.github.io>.

## Background recap (one paragraph)

A game-hopping proof shows that a target scheme satisfies a security
property, assuming certain properties of underlying primitives. The
`.proof` file's `let:` block declares schemes and parameters; `assume:`
lists assumed security games; `lemma:` cites other proven proofs;
`theorem:` states what's being proved; `games:` is the sequence of
games from the left side of the property to the right. Each hop between
adjacent games is either an **interchangeability hop** (the engine
canonicalizes both sides to the same form) or a **reduction-based hop**
(four-step pattern, below).

## FrogLang quick reference

The day-to-day essentials. Full semantics in [FROGLANG_REFERENCE.md](FROGLANG_REFERENCE.md).

**Types:**
- `Int`, `Bool`, `Void`
- `BitString<n>` (cardinality `2^n`), `ModInt<q>`
- `Array<T, n>`, `Map<K, V>` (initially empty; absent-key access undefined),
  `Set<T>`, `Function<D, R>`
- `T?` (optional), `[T1, ..., Tn]` (tuple; constant-index access)

**Operators (gotchas):**
- `+` on `BitString<n>` is **XOR**, not addition.
- `||` is overloaded: logical OR on `Bool`, concatenation on `BitString`.
- `^` is right-associative exponentiation.
- `|x|` — cardinality/length.
- Bitstring slicing: `a[i : j]` yields `BitString<j - i>`.

**Sampling:**
- `Type x <- Type;` — uniform.
- `Type x <-uniq[S] Type;` — uniform from `Type \ S` (rejection).
- `M[k] <- Type;` — sample into a map entry.
- `Function<D, R> H <- Function<D, R>;` — sample a random function (ROM).

**Non-determinism default:** Scheme method calls (`F.evaluate(k, x)`) are
non-deterministic by default. To tell the engine "same input → same
output", annotate the primitive method with `deterministic` (or
`deterministic injective`). When a scheme extends a primitive, the
modifiers must match exactly.

**`Function<D, R>` in proofs:** In `let:`, `Function<D, R> H;` is a known
deterministic function (standard model); `Function<D, R> H <- Function<D, R>;`
is a random function (ROM). The engine treats `Function` calls as
deterministic and applies random-function simplifications only to
sampled Functions.

**What the engine considers semantics-preserving** (non-exhaustive — see
[TRANSFORMS.md](TRANSFORMS.md)):
- XOR/ModInt with uniform: `u <- BitString<n>; return u + m;` ≡ `return u;` (when `u` used once)
- XOR cancellation `x + x` → `0^n`; identity `x + 0^n` → `x`
- Sample merge of independent BitStrings used only via concatenation; split when accessed only via non-overlapping slices
- Random function on distinct inputs (via `<-uniq` sampling) → independent uniforms
- Dead-code elimination, constant folding, single-use variable inlining, branch elimination, tuple-index folding

## File-authoring conventions

- **ASCII only** in `.primitive`/`.scheme`/`.game`/`.proof` files.
- **Names from the literature**, not `v0, v1, ...`.
- Top-of-file comments describe: the main result, the high-level proof
  idea, and one-line summaries of the game sequence. Each reduction or
  intermediate game gets a comment explaining its idea.
- **Scope discipline**: do exactly what was asked. Asked for an
  intermediate game? Add it; don't also sketch the upcoming reductions.
  Work on reductions only when explicitly asked.

## Writing an intermediate game

To write a game that matches how a step canonicalizes, use the engine —
don't guess.

1. If the step is already in `games:`: `get_step_detail(proof, step_index)`
   and read the `canonical` field (NOT `output`, which has mangled names).
2. To evaluate an arbitrary step expression against the proof's `let:`
   without adding it to `games:` yet:
   `get_inlined_game(proof, "OneTimeSecrecy(E).Left")`.

Write a `Game` whose body matches the returned form. Use literature
names; prefer type aliases like `E.Ciphertext` and `BitString<G.lambda>`
over raw sizes.

## The standard four-step pattern for a reduction hop

Each use of a reduction in `games:` occupies four consecutive entries —
two interchangeability hops flanking one assumption hop:

```
G_A against Adversary;                       // interchangeable with Security.Side1 compose R
Security.Side1 compose R against Adversary;  // interchangeable
Security.Side2 compose R against Adversary;  // by assumption (Side1 -> Side2)
G_B against Adversary;                       // interchangeable with Security.Side2 compose R
```

When writing the reduction:

1. Use `get_inlined_game` to see the canonical forms of `G_A` and `G_B`.
2. Identify what the reduction delegates to the challenger versus
   computes itself.
3. Write the reduction; then `prove` and check that all four hops fire.

### Reduction parameter rule

A reduction's parameter list must include every parameter needed to
instantiate the composed security game, even if it isn't referenced in
the reduction body.

### Assumption hops are bidirectional

An assumption hop can go Real→Random or Random→Real; indistinguishability
is symmetric. In the forward half of a symmetric proof the hop often
goes Real→Random; in the reverse half it goes Random→Real.

## Assumption hygiene

- If the user specifies a particular set of security assumptions to use,
  stick to those unless genuinely stuck.
- **Helper assumptions** from `examples/Games/Helpers/` (e.g.
  `Probability/UniqueSampling.game`) encode statistical facts that hold
  unconditionally; OK to add them silently when needed.
- **Genuine cryptographic assumptions** about specific primitives (e.g.
  `examples/Games/Hash/Regularity.game`) should be introduced only when
  the user agrees — they're real security assumptions, not free facts.

### Assumption-game oracle bodies should inline the semantic contract

When writing an assumption game (e.g. `GapTest`) whose helper oracle
witnesses a relation like "does `y = Eval(sk, x)`?", write the oracle
body as the relation itself (`return y == T.Eval(sk, x);`), not as an
opaque primitive call. This makes the contract visible to the engine's
inlining + `LazyMapScan` / `MapKeyReindex` pipeline instead of relying
on the injective-call recognition fallback.

## Diagnosing a failing step

1. `get_step_detail` on both the failing step and its neighbor — read
   `canonical` for each, eyeball the diff. The diff usually shows
   exactly what the engine cannot simplify.
2. If the diff is unclear: `get_canonicalization_trace` shows which
   transforms fired per fixed-point iteration.
3. To inspect intermediate AST: `get_step_after_transform(proof, step,
   "TransformName")`.

## When to escalate

The engine is limited. If a step that *should* canonicalize doesn't
validate, pause and report it to the user rather than papering over with
an extra reduction or a stronger assumption — the engine may have a real
bug. Cross-check the relevant pass in [TRANSFORMS.md](TRANSFORMS.md);
if its description covers the case at hand, the engine likely should
fire and isn't.

## Never commit without explicit ask

Do not run `git commit` unless the user has explicitly requested it.
