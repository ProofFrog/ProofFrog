# prooffrog-mode.el

An Emacs major mode for editing [ProofFrog](https://github.com/ProofFrog/ProofFrog) cryptographic proof language files (`.primitive`, `.scheme`, `.game`, and `.proof`).

## Features

### Syntax Highlighting

- **Declaration keywords:** `Primitive`, `Scheme`, `Game`, `Reduction`, `Phase`
- **Proof structure:** `proof:`, `let:`, `assume:`, `theorem:`, `games:`
- **Control flow:** `if`, `else`, `for`, `return`, `to`, `in`
- **Language keywords:** `import`, `as`, `export`, `extends`, `requires`, `compose`, `against`, `Adversary`, `oracles`, `calls`, `union`, `subsets`
- **Built-in types:** `Bool`, `Void`, `Int`, `BitString`, `Set`, `Map`, `Array`
- **Constants:** `true`, `false`, `None`, binary literals (`0b101`), integers
- **Sampling operator:** `<-`
- **Import paths** in single quotes
- **Definition names** (e.g. `Game Left` highlights `Left` as a function name)

### Indentation

Automatic brace-based indentation with awareness of proof section labels (`let:`, `assume:`, `theorem:`, `games:`). Configurable via `prooffrog-indent-offset` (default: 4 spaces).

### Comment Support

`//` single-line comments, with standard Emacs commenting commands (`M-;`).

### Electric Pairs

Auto-closing of `{}`, `[]`, and `<>`.

### Imenu

`M-x imenu` to jump to `Primitive`, `Scheme`, `Game`, and `Reduction` definitions.

### LSP Support

Full Language Server Protocol integration providing:

- **Diagnostics** — parse errors and type-checking warnings inline
- **Completion** — context-aware completions for types, methods, and identifiers
- **Hover** — documentation and type information on hover
- **Go to definition** — jump to definitions of imported primitives, schemes, and games
- **Rename** — rename local symbols across the file
- **Code lens** — proof verification status inline
- **Document symbols** — outline of definitions in the file
- **Folding** — collapsible code blocks
- **Signature help** — parameter hints for method calls

The LSP client starts automatically when you open a ProofFrog file. It works with either:

- **eglot** (built-in since Emacs 29, recommended)
- **lsp-mode** (install from MELPA)

### File Association

Automatically activates for `.primitive`, `.scheme`, `.game`, and `.proof` files.

## Installation

### From MELPA (recommended)

Once available on MELPA:

```elisp
(use-package prooffrog-mode
  :ensure t)
```

### From NonGNU ELPA

Once available on NonGNU ELPA:

```elisp
(use-package prooffrog-mode
  :ensure t)
```

### Manual

Add to your Emacs config:

```elisp
(add-to-list 'load-path "/path/to/ProofFrog/emacs")
(require 'prooffrog-mode)
```

Or with `use-package`:

```elisp
(use-package prooffrog-mode
  :load-path "/path/to/ProofFrog/emacs")
```

### With lsp-mode instead of eglot

If you prefer `lsp-mode` over the built-in `eglot`:

```elisp
(use-package prooffrog-mode
  :ensure t
  :hook (prooffrog-mode . lsp))
```

## Customization

```elisp
;; Change indentation width (default: 4)
(setq prooffrog-indent-offset 2)

;; Change the Python interpreter used for the LSP server
(setq prooffrog-python-path "/path/to/venv/bin/python3")

;; Disable automatic LSP startup
(setq prooffrog-lsp-enabled nil)
```

You can manually start the LSP client with `M-x prooffrog-start-lsp`.

## Development

Run the linting checks locally:

```bash
cd emacs
make          # byte-compile + package-lint + checkdoc
make compile  # byte-compile only
make lint     # package-lint only
make package  # build .tar for distribution
```

CI runs byte-compilation, package-lint, and checkdoc on Emacs 27.2, 28.2, and 29.4 for every push/PR that touches `emacs/`.

## Publishing

### MELPA

Submit a recipe to the [MELPA repository](https://github.com/melpa/melpa). The recipe for this package:

```elisp
(prooffrog-mode :fetcher github
                :repo "ProofFrog/ProofFrog"
                :files ("emacs/*.el"))
```

MELPA automatically builds and publishes on every upstream commit.

### NonGNU ELPA

Add an entry to the [NonGNU ELPA `elpa-packages`](https://git.savannah.gnu.org/cgit/emacs/nongnu.git/tree/elpa-packages) file:

```elisp
(prooffrog-mode :url "https://github.com/ProofFrog/ProofFrog"
                :ignored-files ("*" "!emacs/*"))
```

### Release workflow

Pushing a tag matching `v*` (e.g. `v0.3.1`) will:

1. Run lint checks
2. Update the version in the elisp header
3. Build a `.tar` package
4. Create a GitHub release with the tarball attached

## Requirements

- Emacs 26.1 or later (27+ recommended for best LSP support)
- ProofFrog installed (`pip install -e ".[dev]"`)
- `eglot` (Emacs 29+ built-in) or `lsp-mode` for LSP features
