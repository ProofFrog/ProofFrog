# Release Notes — v0.3.0

## Web Interface (new)

- Added a browser-based web interface (`proof_frog web <directory>`) powered by Flask and CodeMirror 5.
- File explorer sidebar with expand/collapse all buttons for navigating `.primitive`, `.scheme`, `.game`, and `.proof` files.
- FrogLang syntax highlighting, light and dark (Dracula) themes.
- Parse, type-check, and run proofs directly from the browser.
- Game hop explorer: view per-hop validity results, inspect inlined and canonicalized forms of each game step in a resizable split-view panel.
- Initial setup wizard for new users.
- Security hardening: CSRF resistance, Content Security Policy headers, dotfile blocking, import path sandboxing, capped iteration limits, and XSS protections.

## MCP Server (new)

- Added a Model Context Protocol (MCP) server (`proof_frog/mcp_server.py`) for AI-assisted proof authoring.
- Tools include `parse_file`, `check_file`, `prove_file`, `get_step_detail`, `get_inlined_game`, and more.
- Documented in `CLAUDE_MCP.md` with a full usage guide.

## CLI

- Migrated CLI argument parsing from `sys.argv` to `click`.
- Improved parse and semantic error messages with source location and context.
- Better file-not-found error messages.

## Proof Engine

- `InlineSingleUseVariableTransformer`: inlines single-use variable assignments during canonicalization.
- `SimplifyReturnTransformer` and `ExpandTupleTransformer` improvements.
- Fixed redundant copy bug in `RedundantCopyTransformer`.
- Fixed naming collision in `VariableStandardizingTransformer`.
- Eliminated read-after-read dependency in analysis.
- All hops are now checked even when an earlier hop fails, with per-hop result tracking.

## Import Resolution

- Import paths in FrogLang files are now resolved relative to the importing file's directory (previously relative to the working directory).
- All example files migrated to use file-relative import paths.

## Testing

- Converted shell-based test scripts (`testAST.sh`, `testProofs.sh`) to pytest.
- Parallelized test execution via `pytest-xdist` (`-n auto` by default).
- Added new test suites: `test_inline_single_use_variable.py`, `test_variable_standardizing.py`, `test_redundant_copies.py`, `test_path_security.py`, `test_describe.py`, `test_ast.py`.

## Documentation

- Added `docs/guide.md`: a comprehensive guide for writing primitives, games, schemes, and proofs in FrogLang.
- Expanded `README.md` with documentation and FrogLang examples.
- Added `CLAUDE.md` project instructions and `CLAUDE_MCP.md` MCP tool usage guide.
- Added `Makefile` with `lint` and `format` targets.

## Other

- Added `click` and `flask` to project dependencies.
- Added ProofFrog favicon and logo assets.
