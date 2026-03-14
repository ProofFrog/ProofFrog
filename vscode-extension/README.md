# ProofFrog VSCode Extension

Language support for [ProofFrog](https://github.com/ProofFrog/ProofFrog)'s FrogLang cryptographic proof DSL.

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
  pip install -e .
  ```
- The extension connects to a Python LSP server (`python -m proof_frog lsp`), so ProofFrog must be installed in the Python environment that the extension uses.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `prooffrog.pythonPath` | `python3` | Path to the Python interpreter with ProofFrog installed |

If you use a virtual environment, set this to the full path:

```json
{
  "prooffrog.pythonPath": "/path/to/ProofFrog/.venv/bin/python"
}
```

## Building from source

From the repository root:

```bash
# Build the extension
make vscode-extension

# Package as .vsix
make vscode-vsix
```

Then install the `.vsix` in VSCode: Extensions > `...` menu > "Install from VSIX..."

## Development

To run the extension in development mode:

1. Open the `vscode-extension/` folder in VSCode
2. Run `npm install`
3. Press F5 to launch an Extension Development Host window
4. Open a ProofFrog project in the new window

Check **Output > ProofFrog** for LSP server logs.
