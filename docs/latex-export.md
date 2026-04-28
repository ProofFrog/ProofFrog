# LaTeX Export

ProofFrog can render FrogLang files (`.primitive`, `.scheme`, `.game`,
`.proof`) to LaTeX using the
[`cryptocode`](https://www.ctan.org/pkg/cryptocode) pseudocode package.

## Usage

```bash
python -m proof_frog export-latex path/to/file.proof
# Writes path/to/file.tex
```

Options:

- `-o`, `--output PATH` — override the output path.
- `--backend NAME` — pseudocode package backend. v1 ships only
  `cryptocode`.

The tool emits a self-contained `\documentclass{article}` document with
`\usepackage[...]{cryptocode}` (and `amsmath`, `amssymb`) plus a macro
preamble for every algorithm/scheme/game/property name encountered.

## Customizing macros

Algorithm names like `Enc`, `KeyGen`, `PRF` are emitted as
`\providecommand{\Enc}{\mathsf{Enc}}` etc. Because `\providecommand` is
a no-op when the command is already defined, you can override the
rendering of any name by adding a `\newcommand` *before* `\input`-ing
the generated file:

```latex
\newcommand{\Enc}{\mathsf{Encrypt}}
\input{my-proof.tex}
```

Names that collide with LaTeX builtins (`\Pr`, `\log`, `\det`, ...) are
emitted with a `Frog` prefix (e.g. `\FrogPr`) to avoid clobbering them.

## v1 limitations

- Single backend (`cryptocode`). A `Backend` Protocol exists in
  `proof_frog/export/latex/backends/base.py` so other pseudocode
  packages can be plugged in later.
- No diff highlighting between adjacent games.
- The generated proof document is a *scaffold*. Each game step gets a
  `\paragraph{Game $G_i$.} \todo{commentary}` placeholder — narrative
  prose is left to the author.
- XOR rendering: `+` between two `BitString` operands renders as
  `\oplus` only when the orchestrator passes a `type_of` map to the
  expression renderer. The proof orchestrator does not yet populate
  this from semantic analysis, so XOR currently renders as `+` in
  exported proof bodies. The hook is in place — see
  `ExprRenderer.__init__`.

## Architecture

The package layout (in `proof_frog/export/latex/`):

- `exporter.py` — top-level entry point, dispatches on file extension.
- `macros.py` — `MacroRegistry` collects identifiers and emits a
  `\providecommand` preamble.
- `ir.py` — backend-neutral pseudocode IR (`Sample`, `Assign`,
  `Return`, `If`/`Else`/`EndIf`, `For`/`EndFor`, `Comment`, `Raw`,
  plus `ProcedureBlock`/`VStack`/`Figure` containers).
- `expr_renderer.py`, `stmt_renderer.py`, `type_renderer.py` —
  FrogLang AST → math/IR.
- `module_renderer.py` — Primitive/Scheme/Game → IR + LaTeX fragments.
- `proof_renderer.py` — orchestrator that emits a full `.tex` document
  for `.proof` files.
- `backends/base.py` — `Backend` Protocol + `PackageSpec`.
- `backends/cryptocode.py` — IR → cryptocode (`\procedure`,
  `\begin{pcvstack}`, etc.).

## Future work

- Type-aware expression rendering across full files (XOR detection,
  modular arithmetic).
- Additional backends (e.g. `algorithm2e`, `algpseudocode`).
- Game-diff highlighting between adjacent steps.
- Optional inclusion of source `.scheme`/`.game`/`.primitive` text in a
  Construction appendix.
