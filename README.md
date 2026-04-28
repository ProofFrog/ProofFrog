<p align="center">
  <img src="https://github.com/ProofFrog/ProofFrog/blob/main/proof_frog/web/prooffrog.png?raw=true" alt="ProofFrog logo" width="120"/>
</p>

# ProofFrog

[![Tests](https://github.com/ProofFrog/ProofFrog/actions/workflows/test.yml/badge.svg)](https://github.com/ProofFrog/ProofFrog/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/proof_frog)](https://pypi.org/project/proof_frog/)
[![Python](https://img.shields.io/pypi/pyversions/proof_frog)](https://pypi.org/project/proof_frog/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/ProofFrog/ProofFrog/blob/main/LICENSE)

**A tool for checking transitions in cryptographic game-hopping proofs.**

ProofFrog checks the validity of game hops for cryptographic game-hopping proofs in the reduction-based security paradigm: it checks that the starting and ending games match the security definition, and that each adjacent pair of games is either interchangeable (by code equivalence) or justified by a stated assumption. Proofs are written in FrogLang, a small C/Java-style domain-specific language designed to look like a pen-and-paper proof. ProofFrog can be used from the command line, a browser-based editor, or an MCP server for integration with AI coding assistants. ProofFrog is suitable for introductory level proofs, but is not as expressive for advanced concepts as other verification tools like EasyCrypt.

![ProofFrog web interface](https://raw.githubusercontent.com/ProofFrog/ProofFrog/refs/heads/main/media/screenshot-web.png)

## Installation

Requires **Python 3.11+**.

### From PyPI

```
python3 -m venv .venv
source .venv/bin/activate
pip install proof_frog
```

After installing, download the examples repository:

```
proof_frog download-examples
```

### From source

```
git clone https://github.com/ProofFrog/ProofFrog
cd ProofFrog
git submodule update --init
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Documentation

Full documentation is available at [prooffrog.github.io](https://prooffrog.github.io/), including:

- [Tutorial](https://prooffrog.github.io/manual/tutorial/) — hands-on introduction to writing and checking proofs, and additional [worked examples](https://prooffrog.github.io/manual/worked-examples/)
- [Language reference](https://prooffrog.github.io/manual/language-reference/) — complete FrogLang reference
- [Examples](https://prooffrog.github.io/examples/) — catalogue of example proofs, largely adapted from [*The Joy of Cryptography*](https://joyofcryptography.com/)
- [CLI reference](https://prooffrog.github.io/manual/cli-reference/) — command-line usage
- [Web editor](https://prooffrog.github.io/manual/web-editor/) — browser-based editing and proof checking
- Information about [editor plugins](https://prooffrog.github.io/manual/editor-plugins/) and [proving with AI assistants](https://prooffrog.github.io/researchers/gen-ai/)
- [LaTeX export](docs/latex-export.md) — render FrogLang files to LaTeX (cryptocode pseudocode) via `python -m proof_frog export-latex`

## License

ProofFrog is released under the [MIT License](https://github.com/ProofFrog/ProofFrog/blob/main/LICENSE).

## Acknowledgements

ProofFrog was created by Ross Evans and Douglas Stebila, building on the pygamehop tool created by Douglas Stebila and Matthew McKague. For more information about ProofFrog's design, see [Ross Evans' master's thesis](https://uwspace.uwaterloo.ca/bitstream/handle/10012/20441/Evans_Ross.pdf) and [eprint 2025/418](https://eprint.iacr.org/2025/418).

ProofFrog's syntax and approach to modelling is heavily inspired by Mike Rosulek's excellent book [*The Joy of Cryptography*](https://joyofcryptography.com/).

We acknowledge the support of the Natural Sciences and Engineering Research Council of Canada (NSERC).

<img src="https://github.com/ProofFrog/ProofFrog/blob/main/media/NSERC.jpg?raw=true" alt="NSERC logo" width="750"/>

Includes icons from the [vscode-codicons](https://github.com/microsoft/vscode-codicons) project.
