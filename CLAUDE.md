# ProofFrog Dev — Claude Instructions

## Dev Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pip install -r requirements-dev.txt
```

## Commands

- **Run tests**: `pytest` (runs in parallel via `pytest-xdist` `-n auto` by default; use `-n0` to disable)
- **All CI checks**: `make lint` — runs `black --check`, `mypy`, and `pylint` in sequence (must all pass before committing)
- **Auto-format**: `make format` — runs `black` to reformat in place, then re-run `make lint`
- **CLI**: `python -m proof_frog [parse|check|prove|web] <file>`

## CI Checks (must pass before committing)

The CI runs three checks on every push/PR to `main`. Always run `make lint` locally first.

- `black --check proof_frog` — enforces formatting (Python 3.10 compatible style)
- `mypy proof_frog --no-warn-unused-ignores` — strict type checking
- `pylint proof_frog` — style/quality linting (target: 10.00/10)

### Patterns for suppressions
- ANTLR-generated `ErrorListener` subclasses need `# type: ignore[misc]` on the class line and `# type: ignore[override, no-untyped-def]` on `syntaxError`
- Flask route functions inside `create_app` should use `-> Any:` return type (avoids `no-untyped-def` and `return-value` errors)
- Intentional broad `except Exception` catches in web/server code: `# pylint: disable=broad-exception-caught`
- Accesses to `_`-prefixed engine methods from outside the class: use a `# pylint: disable=protected-access` / `# pylint: enable=protected-access` block
- Lazy imports inside a function body (e.g. CLI subcommands): add `# pylint: disable=import-outside-toplevel` as the first line inside the function
- Cross-file duplicate-code warnings between related modules: add `# pylint: disable=duplicate-code` at module level with an explanatory comment
- `match` blocks that assign a union type: declare `var: TypeA | TypeB | TypeC` before the `match` so mypy doesn't infer the type from the first case only

## Architecture

- `proof_frog/proof_frog.py` — CLI entry point (`parse`, `check`, `prove`, `web` commands)
- `proof_frog/frog_parser.py` — ANTLR-based parser
- `proof_frog/proof_engine.py` — Proof verification (Z3 + SymPy)
- `proof_frog/semantic_analysis.py` — Type checking / semantic analysis
- `proof_frog/visitors.py` — AST visitor/transformer infrastructure
- `proof_frog/web_server.py` — Flask web server (`web` command, branch `ds-web`)
- `proof_frog/parsing/` — ANTLR-generated code; do not edit manually

## File Types

- `.primitive` — cryptographic primitive definitions
- `.scheme` — cryptographic scheme definitions
- `.game` — game definitions
- `.proof` — game-hopping proof scripts

## Conventions

- Python 3.11+, built with Flit (`pyproject.toml`)
- `parsing/` directory is excluded from black, mypy, and pylint
- Proof imports use paths relative to the directory where the CLI is invoked
- Tests live in `tests/`; `test_proofs.py` runs all `examples/**/*.proof` files as subprocesses
- Only use ASCII characters in primitive/scheme/game/proof files.

## Domain Knowledge

ProofFrog checks the validity of transitions in a cryptographic game hopping proof (in the reduction security paradigm, part of the provable security paradigm), written in a domain-specific language called **FrogLang**.

### Components of cryptographic game hopping proofs

A **cryptographic primitive** (grammar file: `proof_frog/antlr/Primitive.g4`; extension: `.primitive`) specifies the sets and functions that define a cryptographic operation, like symmetric key encryption or digital signatures.

A **cryptographic scheme** (grammar file: `proof_frog/antlr/Scheme.g4`; extension: `.scheme`) is an instantiation of a cryptographic primitive. Often cryptographic schemes are built generically from other primitives.

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

### Guidelines for creating FrogLang files

- **Naming**: Use naming conventions from the cryptographic literature rather than sequentially naming variables `v0`, `v1`, etc.
- **Proofs**: Write out what the intermediate games are intended to be before creating the reductions that hop between games. Use comments at the top of the file to describe: the main result, the high-level proof idea, and descriptions of the sequence of games. For each reduction or intermediate game, add a comment explaining its main idea.
- **Scope discipline**: Do exactly what is asked and nothing more. If asked to add an intermediate game, add it — do not also think ahead about what reductions will be needed or comment on upcoming proof steps. Work on reductions only when explicitly asked to.
- **MCP**: Read `CLAUDE_MCP.md` at the start of any session involving ProofFrog proof work. It contains the full MCP tool usage guide, including how to write intermediate games, reductions, and diagnose failing steps. A MCP server exists to allow Claude to interact with the ProofFrog engine to check if code parses and type checks, and see which steps of a game hopping proof are valid. Key tools: `get_step_detail(proof_path, step_index)` returns the canonical form of a game step in an existing proof — read the `canonical` field, not `output` (which has mangled internal names). `get_inlined_game(proof_path, step_text)` returns the canonical form of an arbitrary game step using the proof's let:/assume: context, without the step needing to appear in the proof yet.
- **Writing intermediate games**: To write an intermediate game that matches how a game step canonicalizes, use `get_step_detail` (if the step is already in the proof's games: list) or `get_inlined_game` (to evaluate any step text against the proof's let block). Write a `Game` definition whose body matches the returned `canonical` form. Prefer type aliases like `E.Ciphertext` and `BitString<G.lambda>` over raw sizes for readability.
- **Engine limitations**: The ProofFrog engine is fairly limited and may have bugs. If a step where certain pieces of code should canonicalize to each other doesn't validate, pause and tell the user so they can investigate whether the engine should be fixed.
- **Assumptions**: If the user specifies a particular set of security assumptions to use, stick to those unless stuck. It is okay to suggest or automatically add assumptions from `examples/Games/Misc`, as these are helper assumptions that hold statistically or work around engine limitations.
- **Assumption hops are bidirectional**: An assumption hop in the games list can go Real→Random or Random→Real; indistinguishability is symmetric so both directions are valid. Sometimes, in the forward (left) half of a symmetric proof the hop goes Real→Random and in the reverse (right) half it goes Random→Real.
- **Reduction parameter rule**: A reduction's parameter list must include every parameter needed to instantiate the composed security game, even if that parameter is not referenced in the reduction body. For example, a reduction composing with `OTPUniform(2 * G.lambda)` must take `PRG G` as a parameter even if `G` is not used inside the reduction's oracle methods.
- **Standard four-step pattern for a reduction hop**: Each use of a reduction in the games sequence occupies four consecutive entries — two interchangeability hops flanking one assumption hop:
  ```
  G_A against Adversary;                          // interchangeability with Security.Side1 compose R
  Security.Side1 compose R against Adversary;      // interchangeability
  Security.Side2 compose R against Adversary;      // by assumption (Side1 -> Side2)
  G_B against Adversary;                          // interchangeability with Security.Side2 compose R
  ```
