# ProofFrog Dev — Claude Instructions

## Dev Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Commands

- **Run tests**: `pytest` (runs in parallel via `pytest-xdist` `-n auto` by default; use `-n0` to disable)
- **All CI checks**: `make lint` — runs `black --check`, `mypy`, and `pylint` in sequence (must all pass before committing)
- **Auto-format**: `make format` — runs `black` to reformat in place, then re-run `make lint`
- **CLI**: `python -m proof_frog [parse|check|prove|describe|step-detail|inlined-game|canonicalization-trace|step-after-transform|web|lsp|mcp] <file>`
- **Build VSCode extension**: `make vscode-extension`
- **Package VSCode extension**: `make vscode-vsix`
- **Regenerate parser**: `make parser` — regenerates ANTLR parsing code from grammar files into `proof_frog/parsing/`

## CI Checks (must pass before committing)

The CI runs three checks on every push/PR to `main`. Always run `make lint` locally first.

- `black --check proof_frog` — enforces formatting (Python 3.10 compatible style)
- `mypy proof_frog --no-warn-unused-ignores` — strict type checking
- `pylint proof_frog` — style/quality linting (target: 10.00/10)
- `cd vscode-extension && npx tsc --noEmit` — TypeScript type checking for the VSCode extension

### Patterns for suppressions
- ANTLR-generated `ErrorListener` subclasses need `# type: ignore[misc]` on the class line and `# type: ignore[override, no-untyped-def]` on `syntaxError`
- Flask route functions inside `create_app` should use `-> Any:` return type (avoids `no-untyped-def` and `return-value` errors)
- Intentional broad `except Exception` catches in web/server code: `# pylint: disable=broad-exception-caught`
- Accesses to `_`-prefixed engine methods from outside the class: use a `# pylint: disable=protected-access` / `# pylint: enable=protected-access` block
- Lazy imports inside a function body (e.g. CLI subcommands): add `# pylint: disable=import-outside-toplevel` as the first line inside the function
- Cross-file duplicate-code warnings between related modules: add `# pylint: disable=duplicate-code` at module level with an explanatory comment
- `match` blocks that assign a union type: declare `var: TypeA | TypeB | TypeC` before the `match` so mypy doesn't infer the type from the first case only

## Architecture

- `proof_frog/proof_frog.py` — CLI entry point (`parse`, `check`, `prove`, `describe`, `step-detail`, `inlined-game`, `canonicalization-trace`, `step-after-transform`, `web`, `lsp`, `mcp` commands)
- `proof_frog/frog_ast.py` — AST node definitions
- `proof_frog/frog_parser.py` — ANTLR-based parser
- `proof_frog/proof_engine.py` — Proof verification (Z3 + SymPy)
- `proof_frog/semantic_analysis.py` — Type checking / semantic analysis
- `proof_frog/visitors.py` — AST visitor/transformer base classes (`Visitor[U]`, `Transformer`, `BlockTransformer`) and core utility visitors/transformers (substitution, inlining, Z3/SymPy conversion, type maps)
- `proof_frog/transforms/` — Modular canonicalization pipeline; each file defines `TransformPass` subclasses in a specific domain (algebraic, sampling, control flow, inlining, symbolic, types, tuples, structural, standardization, assumptions). `pipelines.py` assembles passes into `CORE_PIPELINE` (fixed-point canonicalization) and `STANDARDIZATION_PIPELINE` (post-canonicalization normalization). `_base.py` provides `TransformPass`, `PipelineContext`, and the `run_pipeline()`/`run_standardization()` runners.
- `proof_frog/diagnostics.py` — Diagnostic engine for proof hop failures (diff classification, near-miss matching, explanation generation, engine limitation detection)
- `proof_frog/describe.py` — Human-readable descriptions of primitives/schemes/games
- `proof_frog/dependencies.py` — Dependency resolution for proof files
- `proof_frog/mcp_server.py` — MCP server for tool-based proof interaction
- `proof_frog/web_server.py` — Flask web server (`web` command, branch `ds-web`)
- `proof_frog/lsp/` — Language Server Protocol implementation (`lsp` command)
  - `server.py` — pygls-based LSP server, feature registration, event handlers
  - `document_state.py` — per-document state tracking (AST, source, parse errors)
  - `diagnostics.py` — parse and semantic analysis error reporting
  - `navigation.py` — go-to-definition, hover, import resolution
  - `completion.py` — completion items, let-binding resolution, signature help
  - `symbols.py` — document symbol provider (Outline panel)
  - `rename.py` — rename support (F2) for local symbols
  - `folding.py` — folding ranges for code blocks and comment groups
  - `proof_features.py` — proof verification, code lens, proof hops tree view
- `vscode-extension/` — VSCode extension (TypeScript) for syntax highlighting and LSP client
- `proof_frog/parsing/` — ANTLR-generated code; do not edit manually

## File Types

- `.primitive` — cryptographic primitive definitions
- `.scheme` — cryptographic scheme definitions
- `.game` — game definitions
- `.proof` — game-hopping proof scripts

## Conventions

- **Never commit to git unless explicitly asked by the user.**
- Python 3.11+, built with Flit (`pyproject.toml`)
- `parsing/` directory is excluded from black, mypy, and pylint
- Proof imports use paths relative to the directory where the CLI is invoked
- Tests live in `tests/`, organized into `tests/integration/` (proof runs, CLI, AST checks) and `tests/unit/` (by area: engine, transforms, typechecking, visitors, parsing, other); `tests/integration/test_proofs.py` runs all `examples/**/*.proof` files as subprocesses
- Only use ASCII characters in primitive/scheme/game/proof files.
- LSP server uses `pygls` and communicates over stdio; uses full document sync (`TextDocumentSyncKind.Full`)
- The LSP caches a `last_good_ast` per document so completion/hover work even when the file has syntax errors
- When adding or modifying a `TransformPass` in `proof_frog/transforms/`, also add near-miss instrumentation: at key precondition-failure points where the transform almost fires but doesn't, append a `NearMiss` to `ctx.near_misses` (from `PipelineContext`). Update the engine limitation registry in `proof_frog/diagnostics.py` if the transform has known gaps. Add unit tests for near-miss reporting in `tests/unit/transforms/test_near_misses.py`.
- When making changes that affect architecture, commands, test structure, or conventions, update CLAUDE.md to reflect those changes.

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
- `RandomFunctions<D, R>` — lazily-evaluated truly random function (consistent on repeated inputs, independent across distinct inputs)
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
- `RandomFunctions<D, R> RF <- RandomFunctions<D, R>;` — instantiate a fresh random function

**Non-determinism default:** Scheme method calls (e.g., `F.evaluate(k, x)`) are **non-deterministic by default** — each invocation may return a different result even with the same arguments.

**Method annotations:** Primitive method declarations support `deterministic` and `injective` modifiers (e.g., `deterministic injective BitString<n> Encode(GroupElem g);`). `deterministic` tells the engine the method always returns the same output for the same inputs (enabling expression aliasing, field hoisting, tuple folding through function calls, same-method call deduplication via `DeduplicateDeterministicCalls`, and cross-method field alias propagation via `CrossMethodFieldAlias`). `injective` tells the engine the method maps distinct inputs to distinct outputs (enabling the `ChallengeExclusionRFToUniform` transform to see through encoding wrappers). Methods without these annotations are treated conservatively.

**What the engine considers semantics-preserving:**
- XOR/ModInt with uniform: `u <- BitString<n>; return u + m;` ≡ `u <- BitString<n>; return u;` (when `u` used once)
- XOR cancellation: `x + x` → `0^n`; XOR identity: `x + 0^n` → `x`
- Sample merge: independent `BitString<n>` and `BitString<m>` used only via concatenation → single `BitString<n+m>`
- Sample split: `BitString<n>` accessed only via non-overlapping slices → independent samples per slice
- Random function on distinct inputs (via unique sampling) → independent uniform samples
- Dead code elimination, constant folding, single-use variable inlining, branch elimination, tuple index folding

### Guidelines for creating FrogLang files

- **Naming**: Use naming conventions from the cryptographic literature rather than sequentially naming variables `v0`, `v1`, etc.
- **Proofs**: Write out what the intermediate games are intended to be before creating the reductions that hop between games. Use comments at the top of the file to describe: the main result, the high-level proof idea, and descriptions of the sequence of games. For each reduction or intermediate game, add a comment explaining its main idea.
- **Scope discipline**: Do exactly what is asked and nothing more. If asked to add an intermediate game, add it — do not also think ahead about what reductions will be needed or comment on upcoming proof steps. Work on reductions only when explicitly asked to.
- **MCP**: Read `CLAUDE_MCP.md` at the start of any session involving ProofFrog proof work. It contains the full MCP tool usage guide, including how to write intermediate games, reductions, and diagnose failing steps. A MCP server exists to allow Claude to interact with the ProofFrog engine to check if code parses and type checks, and see which steps of a game hopping proof are valid. Key tools: `get_step_detail(proof_path, step_index)` returns the canonical form of a game step in an existing proof — read the `canonical` field, not `output` (which has mangled internal names). `get_inlined_game(proof_path, step_text)` returns the canonical form of an arbitrary game step using the proof's let:/assume: context, without the step needing to appear in the proof yet. **If the MCP server is stale** (e.g. because the proof engine was modified during the session), use the equivalent CLI commands (`step-detail`, `inlined-game`, `canonicalization-trace`, `step-after-transform`) instead — they always use the currently installed engine. See the "CLI fallback" section in `CLAUDE_MCP.md`.
- **Writing intermediate games**: To write an intermediate game that matches how a game step canonicalizes, use `get_step_detail` (if the step is already in the proof's games: list) or `get_inlined_game` (to evaluate any step text against the proof's let block). Write a `Game` definition whose body matches the returned `canonical` form. Prefer type aliases like `E.Ciphertext` and `BitString<G.lambda>` over raw sizes for readability.
- **Engine limitations**: The ProofFrog engine is fairly limited and may have bugs. If a step where certain pieces of code should canonicalize to each other doesn't validate, pause and tell the user so they can investigate whether the engine should be fixed.
- **Assumptions**: If the user specifies a particular set of security assumptions to use, stick to those unless stuck. It is okay to suggest or automatically add assumptions from `examples/Games/Misc`, as these are helper assumptions that hold statistically or work around engine limitations.
- **Assumption hops are bidirectional**: An assumption hop in the games list can go Real→Random or Random→Real; indistinguishability is symmetric so both directions are valid. Sometimes, in the forward (left) half of a symmetric proof the hop goes Real→Random and in the reverse (right) half it goes Random→Real.
- **Reduction parameter rule**: A reduction's parameter list must include every parameter needed to instantiate the composed security game, even if that parameter is not referenced in the reduction body.
- **Standard four-step pattern for a reduction hop**: Each use of a reduction in the games sequence occupies four consecutive entries — two interchangeability hops flanking one assumption hop:
  ```
  G_A against Adversary;                          // interchangeability with Security.Side1 compose R
  Security.Side1 compose R against Adversary;      // interchangeability
  Security.Side2 compose R against Adversary;      // by assumption (Side1 -> Side2)
  G_B against Adversary;                          // interchangeability with Security.Side2 compose R
  ```
