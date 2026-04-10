# Using Claude Code to Help Write ProofFrog Proofs

Claude Code can interactively help you write, debug, and verify ProofFrog proofs via
an MCP (Model Context Protocol) server bundled with this package. Claude gets live
tools to read files, run proofs, and diagnose failing steps — enabling a real
iterate-and-fix loop rather than one-shot suggestions.

## Prerequisites

The MCP server requires the `mcp` Python package. Install it alongside ProofFrog:

```bash
# If you installed from source (recommended for development):
pip install -e ".[mcp]"

# Or install the extra into an existing environment:
pip install "mcp[cli]>=1.0"
```

---

## Registering the MCP Server

```
claude mcp add prooffrog /path/to/project/directory/.venv/bin/python -- -m proof_frog mcp . 2>&1
```

> **After editing either settings file, restart Claude Code** (or run `/mcp` in the
> chat to reload servers) for the changes to take effect.

---

## Verifying the Setup

In a Claude Code session, run:

```
/mcp
```

You should see `prooffrog` listed as a connected server with status `connected`. If it
shows an error, check that the python path and cwd are correct.

You can also ask Claude directly:

> "List the ProofFrog files available in the examples directory."

Claude will call `prooffrog:list_files` and return the file tree.

---

## Available Tools

| Tool | What it does |
|------|-------------|
| `list_files` | Browse .primitive/.game/.scheme/.proof files in a directory |
| `read_file` | Read the full contents of any ProofFrog file |
| `write_file` | Create or overwrite a file (Claude uses this to save proof drafts) |
| `describe` | Compact interface view — parameters, fields, method signatures only, no implementations |
| `parse` | Check a file for syntax errors |
| `check` | Full semantic type-check (catches type mismatches, undefined names, etc.) |
| `prove` | Run proof verification; returns per-hop pass/fail results |
| `get_step_detail` | Canonical (fully simplified) form of one proof step — key for diagnosing failures |
| `get_inlined_game` | Canonical form of an arbitrary game step expression evaluated against the proof's `let:` context — use when the step isn't yet in the `games:` list or when stub reductions prevent parsing |
| `get_canonicalization_trace` | Trace of which transforms fired at each iteration of the fixed-point loop for a step |
| `get_step_after_transform` | Game AST after applying transforms up to a specific named transform — for inspecting intermediate states |

There is also a **language reference resource** (`prooffrog://language-reference`)
that Claude can fetch to remind itself of proof DSL syntax without reading through
example files.

---

## MCP Tool Usage Guide for Claude

### Prefer MCP tools over CLI

When the MCP server is connected **and the proof engine has not been modified
during the current session**, always use the MCP tools instead of running CLI
commands via Bash. The MCP tools return structured output that is easier to work
with and avoids parsing text. Use:

- `parse` and `check` instead of `python -m proof_frog parse/check`
- `prove` instead of `python -m proof_frog prove`
- `get_step_detail` instead of grepping prover output

**Exception — stale MCP server**: If the proof engine or transforms have been
modified during the session, the MCP server (a separate long-running process)
will still use the old code. In that case, fall back to the CLI equivalents
described in the "CLI fallback" section below.

### Writing intermediate games

To write an intermediate game that matches the canonical form of a proof step:

1. **If the step is already in the proof's `games:` list**, call
   `get_step_detail(proof_path, step_index)` and read the `canonical` field
   (not the `output` field, which has mangled internal names).
2. **If you want to evaluate an arbitrary step expression** against the proof's
   `let:` context without adding it to the proof first, call
   `get_inlined_game(proof_path, step_text)` — e.g.
   `get_inlined_game("path/to/proof.proof", "OneTimeSecrecy(E).Left")`.

In both cases, write a `Game` definition whose body matches the returned
canonical form. Use readable variable names from the cryptographic literature
rather than the engine's `v1`, `v2` names.

### Writing reductions

When writing a reduction for a hop between games A and B via assumption S:

1. Use `get_inlined_game` to see the canonical forms of A and B.
2. Identify what the reduction needs to delegate to the challenger versus compute
   itself.
3. Write the reduction, then use `prove` to check that the four-step pattern
   validates:
   - A ↔ S.Real ∘ R (interchangeability)
   - S.Real ∘ R → S.Random ∘ R (by assumption)
   - S.Random ∘ R ↔ B (interchangeability)

### Diagnosing failing steps

When a step fails:

1. Call `get_step_detail(proof_path, step_index)` on both the current and next
   step to see their canonical forms side-by-side.
2. Compare the two canonical forms to identify the difference — this usually
   reveals what the engine cannot simplify automatically.
3. Use `get_canonicalization_trace(proof_path, step_index)` to see which
   transforms fired at each iteration — helpful for understanding the
   simplification sequence.
4. Use `get_step_after_transform(proof_path, step_index, transform_name)` to
   inspect the game AST after a specific transform — useful when you suspect a
   particular transform is misbehaving.

### Validating non-proof files

After creating or editing `.scheme`, `.primitive`, or `.game` files, call `check`
to verify they parse and type-check before using them in a proof.

## Example Workflow

Once the server is registered, you can ask Claude things like:

> "Help me prove that `OTP` satisfies `OneTimeSecrecy`. The relevant files are in
> `examples/`."

Claude will typically:

1. Call `list_files` to find relevant primitives, games, and schemes.
2. Call `describe` on each to learn their interfaces (e.g. what methods `SymEnc`
   has, what `OneTimeSecrecy` requires).
3. Draft a `.proof` file and call `write_file` to save it.
4. Call `prove` to run verification.
5. If a step fails, call `get_step_detail` on the failing step to see the canonical
   (simplified) game form and compare it to the adjacent step.
6. Adjust the reduction or game sequence, write again, and repeat.

You can also drive this manually:

> "Step 3 of my proof is failing. Run `get_step_detail` on step index 2 and step
> index 3 and tell me what differs."

---

## describe command (CLI)

The same interface introspection is available directly from the command line,
independently of Claude:

```bash
python -m proof_frog describe examples/Primitives/SymEnc.primitive
python -m proof_frog describe examples/Games/SymEnc/OneTimeSecrecy.game
python -m proof_frog describe examples/Schemes/SymEnc/OTP.scheme
python -m proof_frog describe examples/Proofs/SymEnc/OTUCimpliesOTS.proof
```

This prints the exported name, parameters, fields, and method signatures without any
implementation bodies — useful for quickly understanding what's available when reading
or planning a proof.

---


## CLI Fallback When the MCP Server Is Stale

When the proof engine or canonicalization transforms are modified during a Claude
session (e.g. fixing an engine bug), the MCP server process still runs the old
code. Rather than writing ad-hoc Python scripts, use the CLI introspection
commands — they always use the currently installed engine (after `pip install -e .`).

The CLI commands output JSON with the same fields as the corresponding MCP tools:

| CLI command | MCP equivalent | Usage |
|-------------|---------------|-------|
| `python -m proof_frog step-detail <proof> <step_index>` | `get_step_detail` | Canonical form of a proof step |
| `python -m proof_frog inlined-game <proof> "<step_text>"` | `get_inlined_game` | Canonical form of an arbitrary step expression |
| `python -m proof_frog canonicalization-trace <proof> <step_index>` | `get_canonicalization_trace` | Which transforms fired per iteration |
| `python -m proof_frog step-after-transform <proof> <step_index> "<transform_name>"` | `get_step_after_transform` | Game AST after a specific transform |

These complement the existing CLI commands (`parse`, `check`, `prove --json`,
`describe --json`) which also accept `--json`/`-j` flags for structured output.

### When to use CLI fallback

1. The proof engine or transforms were edited during this session.
2. The MCP server was not restarted after those edits.
3. You need accurate canonical forms or transform traces that reflect the latest
   engine code.

After using the CLI fallback, re-install (`pip install -e .`) if needed, then
parse the JSON output with `json.loads()` or pipe through `python -m json.tool`
for readability.

---

## Starting the server manually (for debugging)

You can run the MCP server as a standalone process to check it starts cleanly:

```bash
python -m proof_frog mcp examples/
```

On success it blocks (waiting for stdio messages). Press Ctrl-C to stop. If you see
an `ImportError`, the `mcp` package is not installed in the current environment.

---

## Domain Knowledge

ProofFrog checks the validity of transitions in a cryptographic game hopping proof (in the reduction security paradigm, part of the provable security paradigm), written in a domain-specific language called **FrogLang**.

### Components of cryptographic game hopping proofs

A **cryptographic primitive** (grammar file: `proof_frog/antlr/Primitive.g4`; extension: `.primitive`) specifies the sets and functions that define a cryptographic operation, like symmetric key encryption or digital signatures.

A **cryptographic scheme** (grammar file: `proof_frog/antlr/Scheme.g4`; extension: `.scheme`) is an instantiation of a cryptographic primitive. Often cryptographic schemes are built generically from other primitives. Scheme methods can call other methods in the same scheme using the `this` keyword (e.g., `this.DeriveKey(seed)`). During proof verification, `this` references are rewritten to the scheme's instance name so the inliner resolves them.

A **game** (grammar file: `proof_frog/antlr/Game.g4`) is a stateful set of methods, representing the adversary's interaction with a system. There are some optional state variables, an `Initialize` method that would be run once to set up the state, and then some oracle methods that the adversary would call to interact with the system.

A **cryptographic security property** (extension: `.game`) is specified as a pair of games; the two games are often called the two "sides" of the security property. In ProofFrog, security properties are specified as left/right games, where the adversary is tasked to distinguish between two games, rather than win/lose games which sometimes appear in the literature. If needed, win/lose games such as unforgeability can usually be reformulated as left/right games.

A **game hopping proof** (grammar file: `proof_frog/antlr/Proof.g4`; extension: `.proof`) is used to show that a scheme satisfies a security property, assuming certain security properties hold for underlying primitives.

- The main body of a cryptographic proof defines the sets and schemes that are involved in the proof (in a `let:` section), states the cryptographic security properties that are assumed to hold for underlying schemes (in an `assume` section), and then states a `theorem:`, which is that a particular security property holds for a target scheme. Then the proof lists a sequence of games.
- A key operation in a game hopping proof is **inlining**, in which two modules are composed together by inserting the source code of methods from one module into all the places where those methods are called in the other module.
- The first and last games in the sequence of games are the two sides of the security property composed with the target scheme.
- Subsequent games may be stated explicitly by providing an **intermediate game**, or implicitly by composing a game (for an underlying primitive) with a **reduction**.
- Each hop in the game sequence must be justified as either an **interchangeability-based hop**, in which the two adjacent games are **interchangeable** (demonstrated by code equivalence using the ProofFrog engine), or a **reduction-based hop**. A reduction-based hop is justified by exhibiting a reduction to an assumed security property and verifying that the reduction composed with each side of that property is interchangeable with the respective adjacent game.
- Reductions and intermediate games are separately written out at the top of the proof file.
- A proof may reference other proof files as **lemmas** via a `lemma:` section between `assume:` and `theorem:`. Each lemma entry has the form `SecurityProperty(params) by 'path/to/proof.proof';`. The engine verifies each lemma proof, checks that its assumptions are available, and adds the lemma's theorem to the available assumptions. Use `--skip-lemmas` on the CLI to bypass lemma verification.
- An **induction** argument in a game hopping proof involves a loop of games which gradually transition from one game to another.

### The ProofFrog engine

To check interchangeability of two games, the ProofFrog engine focuses primarily on manipulating the abstract syntax trees (ASTs) of games to arrive at a canonical form that is equivalent under the semantics of the domain-specific language. Some transformations dispatch logic to an SMT solver (Z3) or a symbolic computation tool (sympy) to reason about possible program simplifications.

When modifying the proof engine, be careful to ensure that transformations preserve the intended semantics of the domain-specific language. Introduce both positive and negative unit tests.

### FrogLang Quick Reference

The essentials for writing correct FrogLang:

**Types:**
- `Int`, `Bool`, `Void` — primitive types
- `BitString<n>` — bit strings of length `n` (cardinality `2^n`)
- `ModInt<q>` — integers mod `q` with modular arithmetic
- `Array<T, n>` — fixed-size arrays indexed `0` to `n-1`
- `Map<K, V>` — finite partial functions (initially empty; accessing an absent key is undefined)
- `Set<T>` — finite sets
- `Function<D, R>` — deterministic function from D to R; when sampled (`<-`), produces a random function (consistent on repeated inputs, independent across distinct inputs)
- `T?` — optional type (value of `T` or `None`)
- `[T1, T2, ..., Tn]` — tuples; access by constant index `t[0]`, `t[1]`

**Operators (key gotchas):**
- `+` on `BitString<n>` is **XOR**, not addition
- `||` is overloaded: logical OR on `Bool`, concatenation on `BitString`
- `^` is right-associative exponentiation
- `|x|` — cardinality/length (sets, maps, bitstrings, arrays)
- Set operations: `in`, `subsets`, `union`, `\` (difference)
- Bitstring slicing: `a[i : j]` yields `BitString<j - i>`

**Sampling:**
- `Type x <- Type;` — uniform random sample (e.g., `BitString<n> r <- BitString<n>;`)
- `Type x <-uniq[S] Type;` — sample uniformly from `Type \ S` (rejection sampling)
- `M[k] <- Type;` — sample into a map entry
- `Function<D, R> H <- Function<D, R>;` — sample a random function (ROM)

**Non-determinism default:** Scheme method calls (e.g., `F.evaluate(k, x)`) are **non-deterministic by default** — each invocation may return a different result even with the same arguments.

**Function<D, R> in proofs:** In a proof's `let:` block, `Function<D, R> H;` declares a known deterministic function (standard model — the adversary can compute it). `Function<D, R> H <- Function<D, R>;` samples a random function (ROM). The engine treats `Function` calls as deterministic (same input → same output) and only applies random-function simplifications to sampled Functions.

**Method annotations:** Primitive method declarations support `deterministic` and `injective` modifiers (e.g., `deterministic injective BitString<n> Encode(GroupElem g);`). `deterministic` tells the engine the method always returns the same output for the same inputs (enabling expression aliasing, field hoisting, tuple folding through function calls, same-method call deduplication via `DeduplicateDeterministicCalls`, and cross-method field alias propagation via `CrossMethodFieldAlias`). `injective` tells the engine the method maps distinct inputs to distinct outputs (enabling the `ChallengeExclusionRFToUniform` transform to see through encoding wrappers). Methods without these annotations are treated conservatively. When a scheme extends a primitive, the typechecker requires the scheme's implementation of each method to declare exactly the same `deterministic`/`injective` modifiers (and the same return/parameter types, with `T?` not accepted in place of `T`) as the primitive.

**What the engine considers semantics-preserving:**
- XOR/ModInt with uniform: `u <- BitString<n>; return u + m;` ≡ `u <- BitString<n>; return u;` (when `u` used once)
- XOR cancellation: `x + x` → `0^n`; XOR identity: `x + 0^n` → `x`
- Sample merge: independent `BitString<n>` and `BitString<m>` used only via concatenation → single `BitString<n+m>`
- Sample split: `BitString<n>` accessed only via non-overlapping slices → independent samples per slice
- Random function on distinct inputs (via `<-uniq` sampling) → independent uniform samples
- Random function on fresh `<-uniq` input used only in that call → independent uniform sample (`FreshInputRFToUniform`)
- Dead code elimination, constant folding, single-use variable inlining, branch elimination, tuple index folding

### Guidelines for creating FrogLang files

- **Naming**: Use naming conventions from the cryptographic literature rather than sequentially naming variables `v0`, `v1`, etc.
- **Proofs**: Write out what the intermediate games are intended to be before creating the reductions that hop between games. Use comments at the top of the file to describe: the main result, the high-level proof idea, and descriptions of the sequence of games. For each reduction or intermediate game, add a comment explaining its main idea.
- **Scope discipline**: Do exactly what is asked and nothing more. If asked to add an intermediate game, add it — do not also think ahead about what reductions will be needed or comment on upcoming proof steps. Work on reductions only when explicitly asked to.
- **MCP**: Read `CLAUDE_MCP.md` at the start of any session involving ProofFrog proof work. It contains the full MCP tool usage guide, including how to write intermediate games, reductions, and diagnose failing steps. A MCP server exists to allow Claude to interact with the ProofFrog engine to check if code parses and type checks, and see which steps of a game hopping proof are valid. Key tools: `get_step_detail(proof_path, step_index)` returns the canonical form of a game step in an existing proof — read the `canonical` field, not `output` (which has mangled internal names). `get_inlined_game(proof_path, step_text)` returns the canonical form of an arbitrary game step using the proof's let:/assume: context, without the step needing to appear in the proof yet. **If the MCP server is stale** (e.g. because the proof engine was modified during the session), use the equivalent CLI commands (`step-detail`, `inlined-game`, `canonicalization-trace`, `step-after-transform`) instead — they always use the currently installed engine. See the "CLI fallback" section in `CLAUDE_MCP.md`.
- **Writing intermediate games**: To write an intermediate game that matches how a game step canonicalizes, use `get_step_detail` (if the step is already in the proof's games: list) or `get_inlined_game` (to evaluate any step text against the proof's let block). Write a `Game` definition whose body matches the returned `canonical` form. Prefer type aliases like `E.Ciphertext` and `BitString<G.lambda>` over raw sizes for readability.
- **Engine limitations**: The ProofFrog engine is fairly limited and may have bugs. If a step where certain pieces of code should canonicalize to each other doesn't validate, pause and tell the user so they can investigate whether the engine should be fixed.
- **Assumptions**: If the user specifies a particular set of security assumptions to use, stick to those unless stuck. It is okay to suggest or automatically add helper assumptions from `examples/Games/Helpers/` (e.g. `Probability/UniqueSampling.game`), which encode statistical facts that hold unconditionally. Genuine cryptographic assumptions about specific primitives (e.g. `examples/Games/Hash/Regularity.game`) should only be introduced when the user agrees, since they are real security assumptions, not free facts.
- **Assumption hops are bidirectional**: An assumption hop in the games list can go Real→Random or Random→Real; indistinguishability is symmetric so both directions are valid. Sometimes, in the forward (left) half of a symmetric proof the hop goes Real→Random and in the reverse (right) half it goes Random→Real.
- **Reduction parameter rule**: A reduction's parameter list must include every parameter needed to instantiate the composed security game, even if that parameter is not referenced in the reduction body.
- **Standard four-step pattern for a reduction hop**: Each use of a reduction in the games sequence occupies four consecutive entries — two interchangeability hops flanking one assumption hop:
  ```
  G_A against Adversary;                          // interchangeability with Security.Side1 compose R
  Security.Side1 compose R against Adversary;      // interchangeability
  Security.Side2 compose R against Adversary;      // by assumption (Side1 -> Side2)
  G_B against Adversary;                          // interchangeability with Security.Side2 compose R
  ```