# ProofFrog Dev — Claude Instructions

## Routing

Pick the docs that match your task:

- **Writing or debugging a ProofFrog proof** (intermediate games,
  reductions, hops): read [docs/for_agents/WRITING_PROOFS.md](docs/for_agents/WRITING_PROOFS.md)
  and [docs/for_agents/MCP_GUIDE.md](docs/for_agents/MCP_GUIDE.md). Skim
  [docs/for_agents/TRANSFORMS.md](docs/for_agents/TRANSFORMS.md) to know
  what the engine can simplify. Pull [docs/for_agents/FROGLANG_REFERENCE.md](docs/for_agents/FROGLANG_REFERENCE.md)
  when stuck on a semantics question.
- **Closing EasyCrypt admits** in an exported proof: read
  [docs/for_agents/EASYCRYPT_TACTICS.md](docs/for_agents/EASYCRYPT_TACTICS.md)
  and the EasyCrypt MCP section of
  [docs/for_agents/MCP_GUIDE.md](docs/for_agents/MCP_GUIDE.md).
- **Engine / new transform**: also read
  [proof_frog/transforms/CLAUDE.md](proof_frog/transforms/CLAUDE.md).
- **EasyCrypt exporter**: also read
  [proof_frog/export/easycrypt/CLAUDE.md](proof_frog/export/easycrypt/CLAUDE.md).

The rest of this file is repo-dev essentials (setup, lint, conventions,
architecture map) for any session that's editing the codebase.

## Dev Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Commands

- **Run tests**: `pytest` (runs in parallel via `pytest-xdist` `-n auto` by default; use `-n0` to disable). Don't use `--timeout`. Long-running tests are marked `slow` (e.g. the LaTeX-export pdflatex compile sweep in `tests/unit/export/latex/test_pdflatex_sweep.py`, skipped without `pdflatex` on PATH); deselect with `-m "not slow"`.
- **All CI checks**: `make lint` — runs `black --check`, `mypy`, and `pylint` in sequence (must all pass before committing)
- **Auto-format**: `make format` — runs `black` to reformat in place, then re-run `make lint`
- **CLI**: `python -m proof_frog [version|parse|check|prove|describe|step-detail|inlined-game|canonicalization-trace|step-after-transform|export-latex|download-examples|web|lsp|mcp] <file>`
- **Build package**: `make build` — regenerates parser, stamps examples pin, stamps git SHA, syncs agent docs into the package, then runs `flit build`. Always use this instead of bare `flit build`.
- **Build VSCode extension**: `make vscode-extension`
- **Package VSCode extension**: `make vscode-vsix`
- **Regenerate parser**: `make parser` — regenerates ANTLR parsing code from grammar files into `proof_frog/parsing/`
- **Stamp examples pin**: `make examples-pin` — writes `proof_frog/_examples_pin.py` with the git submodule commit SHA (used by `download-examples` command). Run automatically by `make build`.
- **Stamp git SHA**: `make git-sha` — writes `proof_frog/_git_sha.py` with the short commit SHA of `HEAD` (used by the `version` command to annotate dev builds). Run automatically by `make build`. The `version` command prefers a live `git rev-parse` and falls back to this stamped file.
- **Sync agent docs**: `make claude-docs` — copies `docs/for_agents/*.md` into `proof_frog/claude_docs/` so they ship in the wheel and can be materialized by `download-examples`. Run automatically by `make build`.

## Sandbox compatibility

Claude Code's sandbox blocks `ProcessPoolExecutor`, which the proof engine uses for parallel equivalence checking. To work around this, the engine honors the `PROOFFROG_SEQUENTIAL` environment variable: if set, `ProofEngine.__init__` forces `parallel=False` regardless of the constructor argument. This variable is set in `.claude/settings.local.json` so every command Claude spawns in this repo runs the engine sequentially. Users running the engine outside Claude are unaffected. If you need to test parallel behavior from a Claude-spawned shell, prefix the command with `env -u PROOFFROG_SEQUENTIAL`.

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

- `proof_frog/proof_frog.py` — CLI entry point (`version`, `parse`, `check`, `prove`, `describe`, `step-detail`, `inlined-game`, `canonicalization-trace`, `step-after-transform`, `download-examples`, `web`, `lsp`, `mcp` commands)
- `proof_frog/frog_ast.py` — AST node definitions
- `proof_frog/frog_parser.py` — ANTLR-based parser
- `proof_frog/proof_engine.py` — Proof verification (Z3 + SymPy). On success, `HopResult` carries per-hop advantage bookkeeping (`justification`, `reduction`, `direction`) and the engine stores the synthesized `advantage_bound`, printed after the summary table.
- `proof_frog/advantage.py` — Advantage-bound synthesis: a pure fold over a verified proof's `hop_results` (or the proof AST via `synthesize_from_steps`) that composes the triangle-inequality sum of per-hop losses into a SymPy expression over opaque `Adv_i` symbols. Equivalence hops contribute 0; assumption/lemma hops contribute one term each (repeats collapse to `k * Adv^X(B)`, distinct reductions numbered `B1`, `B2`, ...). Inductive proofs are reported as unsupported. No transforms, no Z3. **Tier 2 (helper-game bounds):** when a `by_assumption` hop's notion resolves to a helper `.game` file carrying a declared `advantage <= ...;` clause, `resolve_statistical` substitutes the clause's game parameters (from the assumption instantiation) and replaces the opaque term with the concrete statistical expression (set cardinalities `|S|` stay opaque positive symbols). The clause's free variables include per-oracle query counts written `count_<Oracle>`; each is *derived* by statically counting how many times the composed reduction invokes that oracle (`_derive_oracle_count` / `_count_calls_in_statements`: `Initialize` bodies count once, other reduction methods count `count_<method>` times = the theorem game's own per-oracle query count; loops multiply, `if` branches sum as an upper bound). So the synthesized bound is stated in the theorem game's query counts (e.g. `count_CTXT`, `count_Solve`), and Initialize-time sampling yields a constant. An integer `calls <= N` cap pins the surviving counts to `N` (sound, since statistical bounds are monotone in the counts). Genuine cryptographic assumptions carry no clause and stay symbolic. `AdvantageBound.substituted_expression()` gives the fully-inlined SymPy form (for Tier 3). **Tier 3 (check a claimed bound):** a proof may declare a `bound:` clause (between `theorem:` and `games:`) stating the bound the author believes it establishes: numeric arithmetic over `advantage(<notion> compose <reduction>)` references (the reduction is named from the proof file's declared reductions; `advantage(<notion>)` with no `compose` is a directly-played hop), per-oracle counts `count_<Oracle>` of the theorem game, cardinalities, and `let:` params. `check_claimed_bound` matches each `advantage(...)` reference to the synthesized term by exact `(notion, reduction)` identity (an unmatched reference becomes fresh nonnegative slack — safe), then decides `claimed - synthesized >= 0` over the nonnegativity region: SymPy for the easy cases, else Z3 over the reals (`_sympy_to_z3` / `_decide_nonnegative`; real region superset of the integer domain, so a `>= 0` proof there is sound; symbolic exponents / `unknown` / timeout => undecided, never verified). Three-valued: `verified` (claim is a valid upper bound), `not_verified` (provably smaller — fails `prove` unless `--skip-bound`, witness shown), `undecided` (warns only). The parser wraps the claim in `frog_ast.ClaimedBound` (kept opaque to the generic name-resolution/type-check walk via `Visitor.should_descend`, like `AdvantageClause`); `NameResolutionVisitor._check_claimed_bound` validates well-formedness (declared reduction composing the named notion, `count_` naming a real theorem oracle).
- `proof_frog/semantic_analysis.py` — Type checking / semantic analysis
- `proof_frog/visitors.py` — AST visitor/transformer base classes (`Visitor[U]`, `Transformer`, `BlockTransformer`) and core utility visitors/transformers (substitution, inlining, Z3/SymPy conversion, type maps)
- `proof_frog/transforms/` — Modular canonicalization pipeline; each file defines `TransformPass` subclasses in a specific domain (algebraic, sampling, control flow, inlining, symbolic, types, tuples, structural, standardization, assumptions, alpha-rename). `pipelines.py` assembles passes into `CORE_PIPELINE` (fixed-point canonicalization) and `STANDARDIZATION_PIPELINE` (post-canonicalization normalization). `_base.py` provides `TransformPass`, `PipelineContext`, and the `run_pipeline()`/`run_standardization()` runners. See [proof_frog/transforms/CLAUDE.md](proof_frog/transforms/CLAUDE.md) when modifying.
- `proof_frog/export/easycrypt/` — EasyCrypt exporter. See [proof_frog/export/easycrypt/CLAUDE.md](proof_frog/export/easycrypt/CLAUDE.md) when modifying.
- `proof_frog/diagnostics.py` — Diagnostic engine for proof hop failures (diff classification, near-miss matching, explanation generation, engine limitation detection)
- `proof_frog/describe.py` — Human-readable descriptions of primitives/schemes/games
- `proof_frog/dependencies.py` — Dependency resolution for proof files
- `proof_frog/mcp_server.py` — MCP server for tool-based proof interaction
- `proof_frog/web_server.py` — Flask web server (`web` command). Exposes `/api/file-metadata` (GET + POST), `/api/parse`, `/api/check`, `/api/prove`, `/api/inline`, `/api/describe`, `/api/inlined-game`, and `/api/scaffold/{intermediate-game,reduction,reduction-hop}` for the toolbar Insert dropdown
- `proof_frog/scaffolding.py` — AST-based code-generation helpers used by the web wizard scaffold endpoints. Uses `visitors.SubstitutionTransformer` to do formal-parameter substitution when cloning game/reduction stubs (avoids `proof_engine.instantiate` because that inlines field-level type aliases too eagerly)
- `proof_frog/web/` — Vanilla ES module web client. The toolbar exposes file actions, an Insert ▾ dropdown listing wizards applicable to the active file, Parse / Type Check / Run Proof, and engine introspection actions (Describe, Inlined Game). `wizard.js` registers all wizards in `wizardConfig` and provides modal HTML helpers; modal HTML lives in `index.html`; `insertion.js` has line-scanning helpers for client-side structural insertion points
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
- `proof_frog/claude_docs/` — Agent-facing docs, populated from `docs/for_agents/` by `make claude-docs`. Shipped in the wheel and materialized into the user's examples dir by `download-examples`.
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
- Proof imports and lemma paths resolve relative to the importing file's directory (`resolve_import_path` in `proof_frog/frog_parser.py`)
- Tests live in `tests/`, organized into `tests/integration/` (proof runs, CLI, AST checks, web server endpoints, wizard scaffolding) and `tests/unit/` (by area: engine, transforms, typechecking, visitors, parsing, other); `tests/integration/test_proofs.py` runs all `examples/**/*.proof` files as subprocesses; `tests/integration/test_web_server.py` covers `/api/file-metadata`; `tests/integration/test_scaffolding.py` covers wizard scaffold endpoints with smoke / parse-splice / type-check-splice levels
- Only use ASCII characters in primitive/scheme/game/proof files.
- LSP server uses `pygls` and communicates over stdio; uses full document sync (`TextDocumentSyncKind.Full`)
- The LSP caches a `last_good_ast` per document so completion/hover work even when the file has syntax errors
- When making changes that affect architecture, commands, test structure, or conventions, update CLAUDE.md to reflect those changes.
- When adding, removing, or substantially changing a transform, update `docs/for_agents/TRANSFORMS.md` (the public, link-free capability list).
