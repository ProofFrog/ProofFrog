# Writing and Testing Proofs in ProofFrog

This guide walks through writing each component of a cryptographic game-hopping proof in ProofFrog's domain-specific language, **FrogLang**, and testing them with the CLI.

Proofs in ProofFrog strictly follow the distinguishing game hopping paradigm exemplified in [Mike Rosulek's *Joy of Cryptography*](https://joyofcryptography.com/).

## Overview

A game-hopping proof in ProofFrog involves four file types, each building on the previous:

1. **Primitives** (`.primitive`) -- abstract cryptographic interfaces
2. **Games** (`.game`) -- security properties defined as pairs of games
3. **Schemes** (`.scheme`) -- concrete instantiations of primitives
4. **Proofs** (`.proof`) -- game-hopping proof scripts

All files use C-style syntax with curly braces, semicolons, and `//` line comments. Only ASCII characters are allowed.

## FrogLang Type System

Before diving into file types, here is a summary of the types available in FrogLang.

### Basic types

| Type | Description |
|------|-------------|
| `Int` | Integer |
| `Bool` | Boolean |
| `Void` | No return value (used for `Initialize` methods) |
| `BitString<n>` | Bitstring of length `n` (where `n` is an integer expression) |
| `BitString` | Generic/unparameterized bitstring (used in primitive signatures) |
| `ModInt<q>` | Modular integer (integers mod `q`) |

### Composite types

| Type | Description |
|------|-------------|
| `Set<T>` | Set of elements of type `T` |
| `Map<K, V>` | Map from keys of type `K` to values of type `V` |
| `Array<T, n>` | Array of `n` elements of type `T` |
| `[T1, T2]` | Product (tuple) type |
| `T?` | Optional type (nullable) |

### Type aliases

Primitives and schemes define named sets (e.g., `Set Key = BitString<lambda>`). This can be referenced as `PrimitiveName.Key` from other files.

### Operators

| Operator | Description |
|----------|-------------|
| `+` | XOR (on bitstrings), addition (on integers/ModInt) |
| `-` | Subtraction (on integers/ModInt) |
| `*` | Multiplication (on integers/ModInt) |
| `/` | Division (on integers/ModInt) |
| `^` | Exponentiation |
| `\|\|` | Concatenation (on bitstrings) or logical OR (on booleans) |
| `&&` | Logical AND |
| `!` | Logical NOT |
| `[i : j]` | Slice from index `i` to `j` |
| `[i]` | Indexing |
| `<-` | Uniform random sampling |
| `==`, `!=`, `<`, `>`, `<=`, `>=` | Comparison |
| `in` | Membership test |
| `subsets` | Subset test |
| `union` | Set union |
| `\` | Set difference |
| `\|expr\|` | Size/cardinality |
| `0^n` | Bitstring of `n` zeros |
| `1^n` | Bitstring of `n` ones |
| `0b...` | Binary number literal (e.g., `0b1010`) |
| `None` | Null value for optional types |

## 1. Primitives

A **primitive** defines an abstract cryptographic interface: the sets involved and the method signatures, with no implementations.

### Syntax

```
Primitive Name(parameters) {
    // Field definitions (with initialization)
    Type fieldName = expression;

    // Method signatures (no bodies)
    ReturnType MethodName(ParamType param, ...);
}
```

### Parameters

Parameters can be:
- `Int name` -- an integer parameter (e.g., security parameter, key length)
- `Set name` -- a generic set parameter (for abstract message/key spaces)

### Example: Pseudorandom Generator

```
Primitive PRG(Int lambda, Int stretch) {
    Int lambda = lambda;
    Int stretch = stretch;

    BitString<lambda + stretch> evaluate(BitString<lambda> x);
}
```

A PRG takes a seed of `lambda` bits and stretches it to `lambda + stretch` bits. The field definitions expose the parameters so that schemes and games can reference `G.lambda` and `G.stretch`.

### Example: Symmetric Encryption

```
Primitive SymEnc(Set MessageSpace, Set CiphertextSpace, Set KeySpace) {
    Set Message = MessageSpace;
    Set Ciphertext = CiphertextSpace;
    Set Key = KeySpace;

    Key KeyGen();
    Ciphertext Enc(Key k, Message m);
    Message? Dec(Key k, Ciphertext c);
}
```

Note the `Message?` optional return type on `Dec` -- decryption can fail and return nothing.

### Example: Pseudorandom Function

```
Primitive PRF(Int lambda, Int in, Int out) {
    Int lambda = lambda;
    Int in = in;
    Int out = out;

    BitString<out> evaluate(BitString<lambda> seed, BitString<in> input);
}
```

### Example: Message Authentication Code

```
Primitive MAC(Set MessageSpace, Set TagSpace, Set KeySpace) {
    Set Message = MessageSpace;
    Set Tag = TagSpace;
    Set Key = KeySpace;

    Key KeyGen();
    Tag MAC(Key k, Message m);
}
```

### Testing a primitive

```bash
proof_frog parse examples/Primitives/PRG.primitive    # check syntax
proof_frog check examples/Primitives/PRG.primitive    # type-check
```

## 2. Games

A **game** file defines a **security property** as a pair of games. The adversary's goal is to distinguish between the two games.

### Syntax

```
import 'relative/path/to/Primitive.primitive';

Game SideName1(parameters) {
    // Optional state fields
    Type fieldName;

    // Optional Initialize method (run once)
    Void Initialize() { ... }

    // Oracle methods (called by the adversary)
    ReturnType OracleName(ParamType param, ...) { ... }
}

Game SideName2(parameters) {
    // Same method signatures as SideName1
    ...
}

export as SecurityPropertyName;
```

### Key rules

- A game file must contain exactly **two games** with the same method signatures.
- Common naming conventions for the two sides: `Left`/`Right`, `Real`/`Random`, or `Real`/`Fake`.
- The `export as Name;` statement at the end defines the security property's name.
- Imports use **file-relative paths** (relative to the importing file's directory).

### Statements in method bodies

```
Type var = expr;          // declare and assign
Type var <- Type;         // uniform random sampling
Type var;                 // declare without initializing
lvalue = expr;            // assignment
return expr;              // return a value
if (condition) { ... }    // conditional
if (condition) { ... } else if (condition) { ... } else { ... }
for (Int i = start to end) { ... }   // numeric for loop
for (Type x in expr) { ... }         // iteration
```

### Example: PRG Security

```
import '../../Primitives/PRG.primitive';

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

In the `Real` game, the adversary receives the output of the PRG on a random seed. In the `Random` game, the adversary receives a truly random bitstring. PRG security means these are indistinguishable.

### Example: One-Time Secrecy

```
import '../../Primitives/SymEnc.primitive';

Game Left(SymEnc E) {
    E.Ciphertext Eavesdrop(E.Message mL, E.Message mR) {
        E.Key k = E.KeyGen();
        E.Ciphertext c = E.Enc(k, mL);
        return c;
    }
}

Game Right(SymEnc E) {
    E.Ciphertext Eavesdrop(E.Message mL, E.Message mR) {
        E.Key k = E.KeyGen();
        E.Ciphertext c = E.Enc(k, mR);
        return c;
    }
}

export as OneTimeSecrecy;
```

The adversary submits two messages and receives an encryption of either the left or the right one. One-time secrecy means the adversary cannot tell which.

### Example: CPA Security (with state)

```
import '../../Primitives/SymEnc.primitive';

Game Left(SymEnc E) {
    E.Key k;
    Void Initialize() {
        k = E.KeyGen();
    }
    E.Ciphertext Eavesdrop(E.Message mL, E.Message mR) {
        return E.Enc(k, mL);
    }
}

Game Right(SymEnc E) {
    E.Key k;
    Void Initialize() {
        k = E.KeyGen();
    }
    E.Ciphertext Eavesdrop(E.Message mL, E.Message mR) {
        return E.Enc(k, mR);
    }
}

export as CPA;
```

CPA security is like one-time secrecy but the key persists across multiple queries (via the `Initialize` method and state field `k`).

### Helper games

Some games capture simple probabilistic facts rather than cryptographic security properties. These are placed in `Games/Misc/` and often appear as assumptions in proofs.

### Testing a game

```bash
proof_frog parse examples/Games/PRG/Security.game
proof_frog check examples/Games/PRG/Security.game
```

The `check` command verifies that both games have matching method signatures, correct types, and well-formed expressions.

## 3. Schemes

A **scheme** is a concrete instantiation of a primitive. It provides implementations for all methods declared in the primitive.

### Syntax

```
import 'relative/path/to/Primitive.primitive';

Scheme Name(parameters) extends PrimitiveName {
    // Optional preconditions
    requires expression;

    // Field definitions (set type aliases, integer constants)
    Set Key = BitString<lambda>;
    Int someConstant = 42;

    // Method implementations
    ReturnType MethodName(ParamType param, ...) {
        ...
    }
}
```

### Key rules

- `extends PrimitiveName` links the scheme to the primitive it instantiates.
- The scheme must implement all methods declared in the primitive.
- Parameters can include primitives (to build generic constructions), integers, and sets.
- `requires` clauses specify preconditions on parameters (e.g., matching key sizes).
- Field definitions typically assign concrete types to the abstract sets from the primitive.

### Example: One-Time Pad

```
import '../../Primitives/SymEnc.primitive';

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

The OTP scheme sets all three spaces to `BitString<lambda>`. Key generation samples a random key, encryption and decryption are both XOR.

### Example: TriplingPRG (generic construction)

```
import '../../Primitives/PRG.primitive';

Scheme TriplingPRG(PRG G) extends PRG {
    requires G.lambda == G.stretch;

    Int lambda = G.lambda;
    Int stretch = 2 * G.lambda;

    BitString<lambda + stretch> evaluate(BitString<lambda> s) {
        BitString<2 * lambda> result1 = G.evaluate(s);
        BitString<lambda> x = result1[0 : lambda];
        BitString<lambda> y = result1[lambda : 2*lambda];
        BitString<2 * lambda> result2 = G.evaluate(y);

        return x || result2;
    }
}
```

This builds a PRG with stretch `2 * lambda` from a PRG with stretch `lambda`. It applies the underlying PRG twice and concatenates parts of the results. The `requires` clause ensures the underlying PRG has equal seed length and stretch.

### Testing a scheme

```bash
proof_frog parse examples/Schemes/SymEnc/OTP.scheme
proof_frog check examples/Schemes/SymEnc/OTP.scheme
```

The `check` command verifies that the scheme correctly implements the primitive's interface and that all types are consistent.

## 4. Proofs

A **proof** file is a game-hopping proof that a scheme satisfies a security property, possibly under assumptions about underlying primitives.

### Structure

A proof file has two main sections:

1. **Proof helpers** (before the `proof:` keyword): `Reduction` and intermediate `Game` definitions
2. **Proof block** (after `proof:`): the `let:`, `assume:`, `theorem:`, and `games:` sections

```
import '...';

// Reductions and intermediate games go here (before proof:)

Reduction R1(params) compose SecurityGame(params)
    against TheoremGame(params).Adversary {
    // Oracle implementations
}

Game IntermediateGame(params) {
    // Game body
}

proof:

let:
    // Declare sets, integers, instantiate schemes
    Int lambda;
    PRG G = PRG(lambda, lambda);
    MyScheme S = MyScheme(G);

assume:
    // Security assumptions on underlying schemes
    Security(G);

theorem:
    // What we want to prove
    TargetSecurity(S);

games:
    // Sequence of game hops
    TargetSecurity(S).Left against TargetSecurity(S).Adversary;
    ...
    TargetSecurity(S).Right against TargetSecurity(S).Adversary;
```

### The `let:` section

Declares the mathematical objects used in the proof:

```
let:
    Set MessageSpace;          // abstract set
    Int lambda;                // integer parameter
    PRG G = PRG(lambda, lambda);  // scheme instantiation
    SymEnc E = OTP(lambda);       // concrete scheme
```

### The `assume:` section

Lists the security assumptions (games that are assumed to hold for underlying schemes):

```
assume:
    Security(G);                          // PRG security
```

Helper assumptions from `Games/Misc/` capture simple probabilistic facts and can be freely added as needed.

### The `theorem:` section

States the security property to prove:

```
theorem:
    OneTimeSecrecy(proofE);
```

### The `games:` section

Lists a sequence of games. The first game must be one side of the theorem's security property composed with the adversary, and the last game must be the other side.

Each adjacent pair of games must be justified as either:
- **Interchangeable**: the two games are code-equivalent (verified automatically by the ProofFrog engine)
- **An assumption hop**: one game is obtained from the other by swapping the two sides of an assumed security property

### Game step syntax

Each step in the `games:` list takes one of two forms:

```
// Direct game (no reduction)
GameProperty(params).Side against GameProperty(params).Adversary;

// Game composed with a reduction
GameProperty(params).Side compose ReductionName(params)
    against GameProperty(params).Adversary;
```

### Reductions

A **reduction** is a wrapper that composes an adversary for the theorem's security property with a game for an assumed security property. It acts as an adapter between the two interfaces.

```
Reduction R(params) compose AssumedGame(params)
    against TheoremGame(params).Adversary {
    ReturnType OracleName(params) {
        // Implement the theorem game's oracle interface
        // using challenger.Method() to call the assumed game's oracles
        return challenger.Query(...);
    }
}
```

Inside a reduction:
- `challenger` refers to the assumed security game (the one after `compose`).
- The reduction implements the oracle methods of the theorem game.
- The parameter list must include every parameter needed to instantiate the composed game, even if not directly used in the reduction body.

### The four-step reduction pattern

Each use of a reduction in the games sequence follows a standard four-step pattern:

```
games:
    ...
    // Step 1: Interchangeability
    G_A against Adversary;

    // Step 2: Interchangeability (with reduction composed with one side)
    AssumedGame.Side1 compose R against Adversary;

    // Step 3: Assumption hop (swap Side1 for Side2)
    AssumedGame.Side2 compose R against Adversary;

    // Step 4: Interchangeability (back to a direct game)
    G_B against Adversary;
    ...
```

Steps 1-2 and 3-4 are verified as interchangeable by the engine. Step 2-3 is justified by the assumption. Assumption hops are bidirectional -- you can go from `Side1` to `Side2` or from `Side2` to `Side1`.

### Example: OTUC implies One-Time Secrecy

This proof shows that if a symmetric encryption scheme has one-time uniform ciphertexts (OTUC), then it also has one-time secrecy (OTS).

```
import '../../Primitives/SymEnc.primitive';
import '../../Games/SymEnc/OneTimeSecrecy.game';
import '../../Games/SymEnc/OneTimeUniformCiphertexts.game';

// R1 forwards the left message to OTUC
Reduction R1(SymEnc se) compose OneTimeUniformCiphertexts(se)
    against OneTimeSecrecy(se).Adversary {
    se.Ciphertext Eavesdrop(se.Message mL, se.Message mR) {
        return challenger.CTXT(mL);
    }
}

// R2 forwards the right message to OTUC
Reduction R2(SymEnc se2) compose OneTimeUniformCiphertexts(se2)
    against OneTimeSecrecy(se2).Adversary {
    se2.Ciphertext Eavesdrop(se2.Message mL, se2.Message mR) {
        return challenger.CTXT(mR);
    }
}

proof:

let:
    Set ProofMessageSpace;
    Set ProofCiphertextSpace;
    Set ProofKeySpace;
    SymEnc proofE = SymEnc(ProofMessageSpace, ProofCiphertextSpace, ProofKeySpace);

assume:
    OneTimeUniformCiphertexts(proofE);

theorem:
    OneTimeSecrecy(proofE);

games:
    // Start: OTS Left game
    OneTimeSecrecy(proofE).Left against OneTimeSecrecy(proofE).Adversary;

    // Interchangeability: inline OTS.Left into R1
    OneTimeUniformCiphertexts(proofE).Real compose R1(proofE)
        against OneTimeSecrecy(proofE).Adversary;

    // By assumption: OTUC Real -> Random
    OneTimeUniformCiphertexts(proofE).Random compose R1(proofE)
        against OneTimeSecrecy(proofE).Adversary;

    // Interchangeability: R1 and R2 differ only in unused argument
    OneTimeUniformCiphertexts(proofE).Random compose R2(proofE)
        against OneTimeSecrecy(proofE).Adversary;

    // By assumption: OTUC Random -> Real
    OneTimeUniformCiphertexts(proofE).Real compose R2(proofE)
        against OneTimeSecrecy(proofE).Adversary;

    // Interchangeability: inline back to OTS Right game
    OneTimeSecrecy(proofE).Right against OneTimeSecrecy(proofE).Adversary;
```

**Proof idea**: The left and right games encrypt `mL` and `mR` respectively. By using the OTUC assumption (which says real ciphertexts are indistinguishable from random), we can replace the real ciphertext with a random one. Once the ciphertext is random, it doesn't matter whether `mL` or `mR` was "encrypted", so we can switch between them.

### Example: TriplingPRG Security

A more complex proof showing that the tripling PRG construction is secure if the underlying PRG is secure.

```
import '../../Primitives/PRG.primitive';
import '../../Schemes/PRG/TriplingPRG.scheme';
import '../../Games/PRG/Security.game';

Reduction R1(PRG G, TriplingPRG T) compose Security(G)
    against Security(T).Adversary {
    BitString<T.lambda + T.stretch> Query() {
        BitString<2 * T.lambda> result1 = challenger.Query();
        BitString<T.lambda> x = result1[0 : T.lambda];
        BitString<T.lambda> y = result1[T.lambda : 2*T.lambda];
        BitString<2 * T.lambda> result2 = G.evaluate(y);
        return x || result2;
    }
}

Reduction R3(PRG G, TriplingPRG T) compose Security(G)
    against Security(T).Adversary {
    BitString<T.lambda + T.stretch> Query() {
        BitString<T.lambda> x <- BitString<T.lambda>;
        BitString<2 * T.lambda> result2 = challenger.Query();
        return x || result2;
    }
}

proof:

let:
    Int lambda;
    PRG G = PRG(lambda, lambda);
    TriplingPRG T = TriplingPRG(G);

assume:
    Security(G);

theorem:
    Security(T);

games:
    Security(T).Real against Security(T).Adversary;

    // First PRG application: replace G.evaluate(s) with random
    Security(G).Real compose R1(G, T) against Security(T).Adversary;
    Security(G).Random compose R1(G, T) against Security(T).Adversary;

    // Second PRG application: replace G.evaluate(y) with random
    Security(G).Real compose R3(G, T) against Security(T).Adversary;
    Security(G).Random compose R3(G, T) against Security(T).Adversary;

    Security(T).Random against Security(T).Adversary;
```

**Proof idea**: The TriplingPRG applies the underlying PRG twice. We replace each PRG call with random output one at a time (using the PRG security assumption).

## Testing and Verification

### CLI commands

| Command | Description |
|---------|-------------|
| `proof_frog parse <file>` | Check syntax (works on any file type) |
| `proof_frog check <file>` | Type-check and semantic analysis |
| `proof_frog prove <file>` | Verify a proof (only for `.proof` files) |
| `proof_frog prove -v <file>` | Verbose proof output (shows canonical forms) |
| `proof_frog describe <file>` | Show interface summary |
| `proof_frog lsp` | Start Language Server Protocol server |
| `proof_frog mcp [directory]` | Start MCP server for tool-based proof interaction |

### Development workflow

1. **Write the primitive** and test with `parse` then `check`.
2. **Write the security games** and test with `parse` then `check`. The checker verifies both games have matching signatures.
3. **Write the scheme** and test with `parse` then `check`. The checker verifies the scheme correctly implements the primitive's methods.
4. **Write the proof** incrementally:
   - Start with the `let:`, `assume:`, and `theorem:` sections.
   - Add the first and last game steps (the two sides of the theorem).
   - Fill in intermediate steps and reductions one hop at a time.
   - Run `proof_frog prove <file>` after each change to see which hops pass.

### Interpreting proof output

When you run `proof_frog prove`, each hop is reported as either valid or invalid:

```
Step 1 (interchangeability): VALID
Step 2 (assumption): VALID
Step 3 (interchangeability): VALID
...
```

If a step fails, use `proof_frog prove -v` to see the canonical forms of both games. The engine simplifies each game to a canonical form and compares them structurally. Differences in the canonical forms show what needs to change.

### Web interface

For an interactive experience, launch the web editor:

```bash
proof_frog web examples/
```

This opens a browser-based editor at `http://localhost:5173` with syntax highlighting, file browsing, and buttons to parse, check, and prove files directly.

## Writing Tips

### Import paths

Imports are **file-relative**: the path is resolved relative to the directory containing the importing file. Examples from files in `examples/Proofs/SymEnc/`:

```
import '../../Primitives/SymEnc.primitive';       // up two levels, into Primitives/
import '../../Games/SymEnc/OneTimeSecrecy.game';   // up two levels, into Games/SymEnc/
```

### Reduction parameters

A reduction's parameter list must include every parameter needed to instantiate the composed security game, even if that parameter is not referenced in the reduction body.

### Common patterns

- **Symmetric proofs**: Many proofs are symmetric around a midpoint. The first half transitions from the theorem's Left/Real game toward a "neutral" middle (often with all randomness replaced), and the second half transitions from the middle to the Right/Random game.
- **Helper assumptions**: The `Games/Misc/` directory contains helper games that capture basic probabilistic facts. These can be assumed freely in proofs since they hold unconditionally.
- **Incremental development**: Build proofs one hop at a time. Write the reduction, add the corresponding game steps, and verify before moving on.

## VSCode Extension

A VSCode extension is available that provides syntax highlighting and LSP integration (go-to-definition, hover, completions, diagnostics, rename, and proof verification). See the `vscode-extension/` directory for installation instructions.

## Further Resources

- [ProofFrog website](https://prooffrog.github.io) -- documentation and examples
- The `examples/` directory in this repository contains many complete working examples
- [Mike Rosulek, *The Joy of Cryptography*](https://joyofcryptography.com/) -- the `examples/joy_old/` directory contains ProofFrog proofs corresponding to the textbook
