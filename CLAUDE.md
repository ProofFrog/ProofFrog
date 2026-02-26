# ProofFrog Dev — Claude Instructions

## Dev Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pip install -r requirements-dev.txt
```

## Commands

- **Run tests**: `pytest` (runs in parallel via `pytest-xdist` `-n auto` by default; use `-n0` to disable)
- **Lint**: `pylint proof_frog/` and `mypy proof_frog/`
- **Format**: `black proof_frog/`
- **CLI**: `python -m proof_frog [parse|check|prove|web] <file>`

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
