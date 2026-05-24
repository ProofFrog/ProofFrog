# MCP guide

Two MCP servers matter to agent sessions in this project: `prooffrog`
(ProofFrog engine) and `easycrypt-mcp` (EasyCrypt interactive REPL).
Both run as separate processes outside the agent, so changes to source
code don't take effect mid-session.

## prooffrog MCP

### When to load it

Any session that will write or debug a `.proof`, `.scheme`, `.primitive`,
or `.game` file. Load the tools at session start, not when you need
them mid-task.

### Tools

| Tool | What it does |
|---|---|
| `list_files` | Browse `.primitive`/`.game`/`.scheme`/`.proof` files in a directory. |
| `read_file` | Read the full contents of any ProofFrog file. |
| `write_file` | Create or overwrite a file. |
| `describe` | Compact interface view — parameters, fields, method signatures only. |
| `parse` | Syntax check. |
| `check` | Full semantic type-check. |
| `prove` | Run proof verification; per-hop pass/fail. |
| `get_step_detail` | Canonical (fully simplified) form of one proof step — the key diagnostic. |
| `get_inlined_game` | Canonical form of an arbitrary game step against the proof's `let:` context, without needing it in `games:`. |
| `get_canonicalization_trace` | Which transforms fired at each iteration of the fixed-point loop. |
| `get_step_after_transform` | Game AST after applying transforms up to a specific named transform. |

There's also a `prooffrog://language-reference` resource the agent can
fetch.

### Key idioms

- **Reading canonical forms**: use the `canonical` field, NOT `output`
  (which has mangled internal names like `v1`, `v2`).
- **Writing intermediate games**: call `get_step_detail` (if the step is
  already in `games:`) or `get_inlined_game` (to evaluate a step
  expression that isn't yet in the proof). Write a `Game` whose body
  matches the returned canonical form. Use names from the cryptographic
  literature, not the engine's `v1`/`v2`. Prefer type aliases like
  `E.Ciphertext` over raw sizes.
- **Diagnosing a failing step**: get canonical forms of step `i` and `i+1`
  side-by-side; the diff usually shows what the engine cannot simplify.
  If that's not enough, use `get_canonicalization_trace` to see which
  transforms fired and `get_step_after_transform` to inspect intermediate
  states.
- **Validating non-proof files**: after editing a `.scheme`/`.primitive`/`.game`,
  call `check` before using it in a proof.

### CLI fallback (when MCP is stale)

The MCP server is a long-running process. If the engine source has been
modified in this session (e.g. while developing a new transform), the
MCP server still runs the old code. Use the CLI commands instead — they
always use the currently-installed engine.

| CLI command | MCP equivalent |
|---|---|
| `python -m proof_frog step-detail <proof> <step_index>` | `get_step_detail` |
| `python -m proof_frog inlined-game <proof> "<step_text>"` | `get_inlined_game` |
| `python -m proof_frog canonicalization-trace <proof> <step_index>` | `get_canonicalization_trace` |
| `python -m proof_frog step-after-transform <proof> <step_index> "<transform_name>"` | `get_step_after_transform` |
| `python -m proof_frog parse \| check \| prove \| describe` | `parse` / `check` / `prove` / `describe` |

All also accept `--json`/`-j` for structured output.

After modifying engine code, re-install (`pip install -e .`) if needed
before running. Don't write ad-hoc Python scripts to poke the engine —
the CLI introspection commands cover it.

## easycrypt-mcp

### When to load it

Any session whose job is to close `admit.` lines in an exported `.ec` file,
find a tactic that works, or debug a failing EasyCrypt proof. The EC MCP
tools are **deferred** in this project — they appear by name in the
initial `<system-reminder>` but not in the live tool list, so it's easy
to forget they exist and default to Edit cycles. **Load them first**:

```
ToolSearch select:mcp__easycrypt-mcp__cli_open,mcp__easycrypt-mcp__cli_step,mcp__easycrypt-mcp__cli_undo,mcp__easycrypt-mcp__cli_close,mcp__easycrypt-mcp__cli_print,mcp__easycrypt-mcp__ec_print_goals
```

Each Edit + docker compile cycle is ~30–60s; `cli_step` returns the new
goal in ~1s. Only fall back to `Edit` + `scripts/easycrypt.sh` for the
final end-to-end validation pass, never for tactic exploration.

### Tools

| Tool | What it does |
|---|---|
| `cli_open(path, line)` | Open a REPL session at a `proof.` line. |
| `cli_step(tactic)` | Apply one tactic; returns the new goal. |
| `cli_undo(line)` | Roll back to a line. |
| `cli_close()` | Close the REPL session. |
| `cli_print(name)`, `cli_locate(name)`, `cli_search(pat)` | Explore EC stdlib. |
| `ec_compile(path)` | Compile and return errors + last goals on failure. |
| `ec_print_goals(path, line, col?)` | Print the goal at a position without REPL state. |
| `ec_file_outline(path, upto_line?)` | Top-level declarations. |

### Quirks (real, observed)

- **"No open goals" from `cli_step` can lie** — it can mean the tactic
  was rejected and rolled back, not that the proof closed. Verify with
  an `idtac.` or `progress.` follow-up to see the true goal state.
- **Chained `;` tactics aren't always atomic** — sometimes only the first
  runs and the rest are silently dropped. Send tactics one at a time
  when iterating.
- **Sessions can land in inconsistent state** after several failed steps;
  `cli_undo` doesn't always reset cleanly. Close and reopen if behavior
  gets weird.
- **The file on disk accumulates stale tactic lines** from rolled-back
  steps (cli_step appends regardless of success). Always clean up the
  file before the final validation compile.
- **`rcondt`/`rcondf` position arithmetic is brittle** — each successful
  elimination shifts later positions down by 1, and the side reported can
  flip when both sides have the same head structure. Send an `idtac.`
  and re-read the goal when in doubt.

### When EC MCP is genuinely unavailable

If the tools fail to load and a restart isn't an option, fall back to
`scripts/easycrypt-goals.sh <file> <line>` to print the goal at a point,
then iterate with `Edit` + `scripts/easycrypt.sh`. `easycrypt.sh` runs
EC inside the upstream Docker image; exit 0 = type-check success. See
also [EASYCRYPT_TACTICS.md](EASYCRYPT_TACTICS.md) for tactic-cache
workflow.

## When the proof engine is being modified

If the session involves both engine work AND proof verification,
**don't trust the prooffrog MCP** for verification — its cached engine
won't reflect your changes. Use the CLI fallback for `prove`,
`step-detail`, etc., after each engine edit and `pip install -e .` (or
just rely on editable install picking up `.py` changes — but the
running MCP server still won't).
