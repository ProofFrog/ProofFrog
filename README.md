<p align="center">
  <img src="https://github.com/ProofFrog/ProofFrog/blob/main/proof_frog/web/prooffrog.png?raw=true" alt="ProofFrog logo" width="120"/>
</p>

# ProofFrog

**A tool for checking transitions in cryptographic game-hopping proofs.**

ProofFrog checks the validity of transitions in game-hopping proofs — the standard technique in provable security for showing that a cryptographic scheme satisfies a security property. Proofs are written in FrogLang, a domain-specific language for defining primitives, schemes, security games, and proofs. ProofFrog is designed to handle introductory-level proofs, trading expressivity and power for ease of use. The engine checks each hop by manipulating abstract syntax trees into a canonical form, with some help from other tools like Z3 and SymPy. ProofFrog's engine does not have any formal guarantees: the soundness of its transformations has not been verified.

ProofFrog can be used via a **command-line interface**, a **browser-based editor**, or an **MCP server** for integration with AI coding assistants. More info at [prooffrog.github.io](https://prooffrog.github.io/).

![ProofFrog web interface](https://github.com/ProofFrog/ProofFrog/blob/main/media/screenshot-web.png?raw=true)

## Installation

Requires **Python 3.11+**.

### From PyPI

```
python3 -m venv .venv
source .venv/bin/activate
pip install proof_frog
```

After installing ProofFrog via pip, you may want to download the examples repository:

```
git clone https://github.com/ProofFrog/examples
```

### From source

```
git clone https://github.com/ProofFrog/ProofFrog
cd ProofFrog
git submodule update --init
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

## Web Interface

```
proof_frog web [directory]
```

Starts a local web server (default port 5173) and opens the editor in your browser. The `[directory]` argument specifies the working directory for proof files; it defaults to the current directory.

The web interface lets you edit ProofFrog files (with syntax highlighting), validate proofs from the web editor, and explore the game state at each hop.

## Command-Line Interface

| Command | Description |
|---------|-------------|
| `proof_frog parse <file>` | Parse a file and print its AST representation |
| `proof_frog check <file>` | Type-check a file for well-formedness |
| `proof_frog prove <file>` | Verify a game-hopping proof (`-v` for verbose output) |
| `proof_frog web [dir]` | Launch the browser-based editor |

When installed from source, use `python3 -m proof_frog` instead of `proof_frog`.

## Writing a Proof in ProofFrog

Take a look at the [guide](https://github.com/ProofFrog/ProofFrog/blob/main/docs/guide.md) for writing a proof in ProofFrog.

ProofFrog uses four file types to express the components of a cryptographic proof.

### Primitives (`.primitive`)

A **primitive** defines the interface for a cryptographic operation — its parameters, types, and method signatures. Here's an example of the interface for a pseudorandom generator:

```
Primitive PRG(Int lambda, Int stretch) {
    Int lambda = lambda;
    Int stretch = stretch;

    BitString<lambda + stretch> evaluate(BitString<lambda> x);
}
```

### Schemes (`.scheme`)

A **scheme** implements a primitive. Schemes can be built generically from other primitives. Here's an example of the one-time pad symmetric encryption scheme:

```
Scheme OTP(Int lambda) extends SymEnc {
    Set Key = BitString<lambda>;
    Set Message = BitString<lambda>;
    Set Ciphertext = BitString<lambda>;

    Key KeyGen() {
        Key k <- Key;
        return k;
    }

    Ciphertext Enc(Key k, Message m) {
        return k + m;
    }

    Message Dec(Key k, Ciphertext c) {
        return k + c;
    }
}
```

### Games (`.game`)

A **security property** is defined as a pair of games (Left/Right). An adversary's inability to distinguish between the two games constitutes security. Here's an example of the security game for a PRG:

```
Game Real(PRG G) {
    BitString<G.lambda + G.stretch> Query() {
        BitString<G.lambda> s <- BitString<G.lambda>;
        return G.evaluate(s);
    }
}

Game Random(PRG G) {
    BitString<G.lambda + G.stretch> Query() {
        BitString<G.lambda + G.stretch> r <- BitString<G.lambda + G.stretch>;
        return r;
    }
}

export as Security;
```

### Proofs (`.proof`)

A **proof script** declares assumptions, states a theorem, and lists a sequence of games. Each adjacent pair must be justified as either code-equivalent (verified automatically) or a reduction to an assumed security property. The following snippet shows the basic parts of a proof:

```
proof:

let:
    SymEnc proofE = SymEnc(ProofMessageSpace, ProofCiphertextSpace, ProofKeySpace);

assume:
    OneTimeUniformCiphertexts(proofE);

theorem:
    OneTimeSecrecy(proofE);

games:
    OneTimeSecrecy(proofE).Left against OneTimeSecrecy(proofE).Adversary;
    OneTimeUniformCiphertexts(proofE).Real compose R1(proofE) against OneTimeSecrecy(proofE).Adversary;
    OneTimeUniformCiphertexts(proofE).Random compose R1(proofE) against OneTimeSecrecy(proofE).Adversary;
    OneTimeUniformCiphertexts(proofE).Random compose R2(proofE) against OneTimeSecrecy(proofE).Adversary;
    OneTimeUniformCiphertexts(proofE).Real compose R2(proofE) against OneTimeSecrecy(proofE).Adversary;
    OneTimeSecrecy(proofE).Right against OneTimeSecrecy(proofE).Adversary;
```

## Vibe-Coding a Proof

ProofFrog also provides an MCP server for integration with AI coding assistants like Claude Code. See the ProofFrog website for an [example of vibe-coding a ProofFrog proof with Claude Code](https://prooffrog.github.io/hacs-2026/vibe/).

## Examples

The [`examples/`](https://github.com/ProofFrog/examples) repository contains primitives, schemes, games, and proofs largely adapted from [*The Joy of Cryptography*](https://joyofcryptography.com/) by Mike Rosulek. See also the [examples and tutorials on the ProofFrog website](https://prooffrog.github.io/).

## License

ProofFrog is released under the [MIT License](https://github.com/ProofFrog/ProofFrog/blob/main/LICENSE).

## Acknowledgements

ProofFrog was created by Ross Evans and Douglas Stebila, building on the pygamehop tool created by Douglas Stebila and Matthew McKague. For more information about ProofFrog's design, see [Ross Evans' master's thesis](https://uwspace.uwaterloo.ca/bitstream/handle/10012/20441/Evans_Ross.pdf) and [eprint 2025/418](https://eprint.iacr.org/2025/418).

<img src="https://github.com/ProofFrog/ProofFrog/blob/main/media/NSERC.jpg?raw=true" alt="NSERC logo" width="750"/>

We acknowledge the support of the Natural Sciences and Engineering Research Council of Canada (NSERC).

Includes icons from the [vscode-codicons](https://github.com/microsoft/vscode-codicons) project.
