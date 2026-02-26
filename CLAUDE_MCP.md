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

There is also a **language reference resource** (`prooffrog://language-reference`)
that Claude can fetch to remind itself of proof DSL syntax without reading through
example files.

---

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
