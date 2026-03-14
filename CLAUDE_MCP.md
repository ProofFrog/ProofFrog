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

When the MCP server is connected, **always use the MCP tools instead of running
CLI commands via Bash**. The MCP tools return structured output that is easier to
work with and avoids parsing text. Use:

- `parse` and `check` instead of `python -m proof_frog parse/check`
- `prove` instead of `python -m proof_frog prove`
- `get_step_detail` instead of grepping prover output

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


## Starting the server manually (for debugging)

You can run the MCP server as a standalone process to check it starts cleanly:

```bash
python -m proof_frog mcp examples/
```

On success it blocks (waiting for stdio messages). Press Ctrl-C to stop. If you see
an `ImportError`, the `mcp` package is not installed in the current environment.
