# ProofFrog VSCode Extension

**[ProofFrog](https://github.com/ProofFrog/ProofFrog) is a tool for checking transitions in cryptographic game-hopping proofs.**

This VSCode extension provides language support for ProofFrog's domain-specific language, FrogLang.

## About ProofFrog

ProofFrog checks the validity of game hops for cryptographic game-hopping proofs in the reduction-based security paradigm: it checks that the starting and ending games match the security definition, and that each adjacent pair of games is either interchangeable (by code equivalence) or justified by a stated assumption. Proofs are written in FrogLang, a small C/Java-style domain-specific language designed to look like a pen-and-paper proof. ProofFrog can be used from the command line, a browser-based editor, or an MCP server for integration with AI coding assistants. ProofFrog is suitable for introductory level proofs, but is not as expressive for advanced concepts as other verification tools like EasyCrypt.

## Features

- **Syntax highlighting** for `.primitive`, `.scheme`, `.game`, and `.proof` files
- **Parse error diagnostics** shown as squiggles on save
- **Semantic analysis** (type checking) diagnostics on save
- **Go-to-definition** for import paths (Cmd/Ctrl+click)
- **Hover** information for imported names
- **Completion** for scheme and primitive members (type `.` after an import alias)
- **Code lens** annotations on `.proof` files showing pass/fail for each game hop
- **Proof hops tree view** in the Explorer sidebar when viewing a `.proof` file

## Requirements

- Python 3.11+ with ProofFrog installed:
  ```bash
  pip install prooffrog
  ```
- The extension connects to a Python LSP server (`python -m proof_frog lsp`), so ProofFrog must be installed in the Python environment that the extension uses.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `prooffrog.pythonPath` | `python3` | Path to the Python interpreter with ProofFrog installed |

If you use a virtual environment, set this to the full path:

```json
{
  "prooffrog.pythonPath": "/path/to/venv/bin/python"
}
```
