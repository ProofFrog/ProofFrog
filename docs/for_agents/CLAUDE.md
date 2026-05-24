# Agent docs for ProofFrog

This directory holds instruction-style docs for AI agents (Claude Code and
similar) working with ProofFrog. Humans should read the manual at
<https://prooffrog.github.io> instead — these files are deliberately terse
and workflow-shaped.

When `proof_frog download-examples` runs, these files are also written into
the user's examples directory as `claude_docs/`, so an agent session that
has only the examples checkout still has them.

## Routing

Pick the docs that match what you're doing:

- **Writing a ProofFrog proof** (intermediate games, reductions, hops):
  read [WRITING_PROOFS.md](WRITING_PROOFS.md) and [MCP_GUIDE.md](MCP_GUIDE.md).
  Skim [TRANSFORMS.md](TRANSFORMS.md) to know what the engine can simplify.
  Pull [FROGLANG_REFERENCE.md](FROGLANG_REFERENCE.md) when stuck on a
  semantics question.
- **Closing EasyCrypt admits** in an exported proof: read
  [EASYCRYPT_TACTICS.md](EASYCRYPT_TACTICS.md) and the EasyCrypt MCP
  section of [MCP_GUIDE.md](MCP_GUIDE.md).
- **Working on the ProofFrog engine, a new transform, or the EasyCrypt
  exporter** (source repo only — not applicable from an examples-only
  checkout): the source repo has additional per-subdirectory CLAUDE.md
  files under `proof_frog/transforms/` and `proof_frog/export/easycrypt/`
  that are auto-loaded when editing under those directories.

## What's here

| File | Purpose |
|---|---|
| [WRITING_PROOFS.md](WRITING_PROOFS.md) | Workflow rules for authoring proofs (intermediate games, reductions, the four-step pattern, assumption hygiene, scope discipline). |
| [MCP_GUIDE.md](MCP_GUIDE.md) | When and how to use the `prooffrog` and `easycrypt-mcp` MCP servers; CLI fallback when MCP is stale. |
| [FROGLANG_REFERENCE.md](FROGLANG_REFERENCE.md) | Full FrogLang semantics reference. Pull when you need to answer a "is this rewrite sound?" question. |
| [TRANSFORMS.md](TRANSFORMS.md) | Names + one-line descriptions of every canonicalization pass — the engine's capability list. |
| [EASYCRYPT_TACTICS.md](EASYCRYPT_TACTICS.md) | EasyCrypt tactic-cache workflow and EC-specific gotchas (eager proc, byphoare, cli_step quirks). |
