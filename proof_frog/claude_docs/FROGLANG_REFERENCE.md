# FrogLang Semantics

This document describes the formal semantics of FrogLang, the domain-specific language used by ProofFrog for expressing and verifying cryptographic game-hopping proofs.

## 1. Overview

FrogLang is a language for specifying cryptographic primitives, schemes, security definitions (as games), and game-hopping proofs. Its semantics are designed around the **provable security paradigm**, where security is formulated as the inability of any efficient adversary to distinguish between two games.

The fundamental semantic unit is the **game**: a stateful interactive system that an adversary interacts with through oracle queries. The central question FrogLang answers is whether two games are **interchangeable** — that is, whether they induce identical probability distributions over all possible adversary outputs.

## 2. Types

### 2.1 Primitive Types

- **`Int`**: Unbounded integers. Used for security parameters, lengths, loop bounds, and arithmetic.
- **`Bool`**: Boolean values `true` and `false`.
- **`Void`**: The unit type. Used only as the return type for methods that produce no value (typically `Initialize`).

### 2.2 Parameterized Types

- **`BitString<n>`**: The set of all bit strings of length `n`, where `n` is an `Int` expression. The cardinality of `BitString<n>` is `2^n`. An unparameterized `BitString` appears in primitive signatures as a placeholder to be instantiated later.

- **`ModInt<q>`**: The set of integers modulo `q`, i.e., `{0, 1, ..., q-1}` with arithmetic operations performed modulo `q`. The cardinality of `ModInt<q>` is `q`.

- **`Group`**: A finite cyclic group declaration. `Group` is a declaration type (like `Int` or `Set`) used to introduce a group parameter. A group `G` has three built-in accessors:
  - `G.order` (`Int`): the order (number of elements) of the group.
  - `G.generator` (`GroupElem<G>`): a designated generator of the group, i.e., an element whose powers enumerate every group element.
  - `G.identity` (`GroupElem<G>`): the identity element of the group, i.e., the unique element `e` such that `e * g = g * e = g` for all `g` in the group. Equivalently, `G.generator ^ 0 = G.identity`.

  The model is a **finite cyclic group**. All finite cyclic groups are abelian, so the group operation is commutative. The group is assumed to have the property that the map `G.generator ^ (·)` is a bijection from `ModInt<G.order>` to `GroupElem<G>` — this holds for any generator of a cyclic group by definition. In cryptographic applications, these are typically groups of prime order (e.g., prime-order subgroups of elliptic curve groups), though the engine's current transforms are sound for cyclic groups of any order.

  **Prime-order opt-in.** By default a group's order is unconstrained, so transforms must be sound for any cyclic order. A proof or scheme may opt into prime-order reasoning by declaring `requires <group>.order is prime;` in its `requires` block (see the `requires` clauses note in section 5.2). Under prime order every nonzero exponent is invertible modulo `G.order`, so the map `x |-> x ^ k` (for `x : GroupElem<G>`) is a bijection on the group whenever `k` is nonzero. This is what licenses treating `x ^ k` as an **injective encoding** — e.g., deciding group-element equality by comparing exponents. Transforms that rely on it (the injective-exponent rewrites) fire only when the declaration is present and the exponent is provably nonzero; otherwise they decline and emit a near-miss requesting the declaration.

- **`GroupElem<G>`**: The set of elements of the group `G`. Parameterized by a group identifier (not by order), so elements from different groups are type-incompatible even if the groups have the same order. The cardinality of `GroupElem<G>` is `G.order`.

- **`Array<T, n>`**: Fixed-size arrays of `n` elements of type `T`, indexed from `0` to `n-1`.

- **`Map<K, V>`**: Finite partial functions from keys of type `K` to values of type `V`. A map is initially empty (no keys are mapped). Map access on a key not in the domain is undefined behavior.

- **`Set<T>`**: Finite sets of elements of type `T`. An unparameterized `Set` in a primitive signature is an abstract type placeholder.

- **`Function<D, R>`**: The type of truly random functions from domain `D` to range `R`. A value of this type represents a lazily-evaluated random function: each distinct input independently maps to a uniformly random output, and repeated queries on the same input return the same result. This models the idealized random oracle / random function abstraction.

- **`T?`** (Optional): Either a value of type `T` or `None`. Used for operations that may fail (e.g., decryption may return `Message?`).

### 2.3 Product Types (Tuples)

- **`[T1, T2, ..., Tn]`**: An ordered heterogeneous collection. Tuple literals are written `[e1, e2, ..., en]` and elements are accessed by constant index: `t[0]`, `t[1]`, etc.

### 2.4 Type Aliases and Set Fields

Primitives and schemes define named `Set` fields that serve as type aliases:

```
Set Key = BitString<lambda>;
```

This makes `Key` (or `E.Key` when accessed through an instance `E`) usable as a type anywhere a type is expected. When a scheme is instantiated in a proof, these aliases resolve to concrete types.

## 3. Expressions

### 3.1 Literals

- **Integer literals**: `0`, `42`, `1024`
- **Binary literals**: `0bXYZ` where each digit is `0` or `1`. The declared bit length is the number of digits after `0b`, so `0b0` is a 1-bit literal, `0b01` is a 2-bit literal, `0b101` is a 3-bit literal. The value is the unsigned big-endian integer interpretation of the digits. Typed as `BitString<length>`. Unlike general programming languages, `0b0` is NOT length-polymorphic — for "all zeros of length $n$" (including symbolic $n$), use the bitstring-literal form below.
- **Bitstring literals**: `0^n` (n-bit string of all zeros), `1^n` (n-bit string of all ones). The length `n` is an arbitrary length expression, concrete or symbolic.
- **Boolean literals**: `true`, `false`
- **`None`**: The null value for optional types
- **`G.generator`**: The canonical generator of group `G` (type `GroupElem<G>`)
- **`G.identity`**: The identity element of group `G` (type `GroupElem<G>`)
- **Set literals**: `{e1, e2, e3}` or `{}` for the empty set
- **Tuple literals**: `[e1, e2, e3]` or `[]` for the empty tuple

### 3.2 Variables and Access

- **Variable reference**: `x` — refers to a variable in scope (local, parameter, or field)
- **Field access**: `obj.field` — accesses a named field of an object or type alias of a primitive/scheme instance
- **Array/Map access**: `a[i]` — retrieves element at index `i` (for arrays) or key `i` (for maps)
- **Slice**: `a[i : j]` — extracts a sub-bitstring from index `i` (inclusive) to `j` (exclusive), yielding a `BitString<j - i>`

### 3.3 Function Calls

- **Method call**: `obj.method(arg1, arg2, ...)` — invokes a method on a scheme, primitive, or game instance
- **Random function call**: `RF(x)` — evaluates a random function at input `x`
- **`this.method(args)`**: Within a scheme body, calls another method of the same scheme. During proof verification, `this` is rewritten to the scheme's instance name.
- **`challenger.method(args)`**: Within a reduction body, delegates to the composed security game's oracle.

### 3.4 Operators

**Arithmetic** (on `Int` and `ModInt<q>`; `ModInt` arithmetic is performed mod `q`):
- `+` (addition), `-` (subtraction), `*` (multiplication), `/` (integer division), `^` (exponentiation, right-associative)
- Unary `-` (negation)

**Group element operations** (on `GroupElem<G>`; both operands must belong to the same group):
- `*` (multiplication): the abelian group operation; `a * b` produces a `GroupElem<G>`
- `/` (division): `a / b` computes `a * b^(-1)`, yielding a `GroupElem<G>`
- `^` (exponentiation): `h ^ x` where `h` is `GroupElem<G>` and `x` is `ModInt<G.order>` or `Int`, yielding `GroupElem<G>`. This computes the scalar power of a group element.

**Bitstring operations:**
- `+` on `BitString<n>`: bitwise XOR (both operands must have the same length `n`)
- `||` on bitstrings: concatenation; `a || b` produces a `BitString<|a| + |b|>`

**Comparison** (on all comparable types):
- `==`, `!=`, `<`, `>`, `<=`, `>=`

**Logical** (on `Bool`):
- `&&` (AND), `||` (OR), `!` (NOT)

Note: `||` is overloaded — it is logical OR on `Bool` and concatenation on `BitString`.

**Algebraic properties:**

The following operators are commutative and associative:
- `+` on `Int` and `ModInt<q>` (addition)
- `+` on `BitString<n>` (XOR)
- `*` on `Int`, `ModInt<q>`, and `GroupElem<G>` (multiplication / group operation)
- `&&` on `Bool` (logical AND)
- `||` on `Bool` (logical OR)

The following are NOT commutative:
- `-` (subtraction), `/` (division), `^` (exponentiation)
- `||` on `BitString` (concatenation: `a || b` != `b || a` in general)

**Set operations:**
- `x in S` — membership test
- `A subsets B` — subset test
- `A union B` — set union
- `A \ B` — set difference

**Cardinality/size:**
- `|x|` — cardinality of a set or map, or bit-length of a bitstring, or element count of an array

**Operator precedence** (highest to lowest):
1. `^` (right-associative)
2. `*`, `/`
3. `+`, `-`
4. `==`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `subsets`
5. `&&`
6. `||`, `union`, `\`

## 4. Statements

### 4.1 Variable Declaration and Assignment

- **Declaration only**: `Type x;` — declares an uninitialized variable. The value is undefined until assigned.
- **Declaration with assignment**: `Type x = expr;` — declares and initializes.
- **Assignment**: `x = expr;` or `a[i] = expr;` — assigns to an existing variable or updates an array/map element.

### 4.2 Sampling

**Uniform sampling**: `Type x <- Type;`

Draws a value uniformly at random from the specified type's domain. Each sampling statement produces an independent draw. Examples:
- `BitString<n> r <- BitString<n>;` — sample a uniformly random n-bit string
- `ModInt<q> r <- ModInt<q>;` — sample a uniformly random element of Z_q
- `GroupElem<G> u <- GroupElem<G>;` — sample a uniformly random element of the group G
- `Function<D, R> RF <- Function<D, R>;` — instantiate a fresh random function

**Sampling from a variable**: `Type x <- someSetVariable;` — sample uniformly from the elements currently in a set or the values of a map.

**Unique sampling**: `Type x <-uniq[S] Type;`

Draws uniformly from `Type` conditioned on the result not being in the set `S`. Semantically equivalent to rejection sampling: repeatedly sample from `Type` until the result is not in `S`. This operation:
- Produces a value uniformly distributed over `Type \ S`
- Has an implicit collision/abort probability of `|S| / |Type|` per sample
- Is used when freshness guarantees are needed (e.g., no repeated nonces)

### 4.3 Return

`return expr;` — exits the current method and returns the value of `expr`. The type of `expr` must match the method's declared return type.

### 4.4 Conditional

```
if (condition) {
    ...
} else if (condition) {
    ...
} else {
    ...
}
```

Standard deterministic branching. The condition is a `Bool` expression evaluated at runtime. `else if` and `else` clauses are optional.

### 4.5 For Loops

**Numeric for**: `for (Int i = start to end) { ... }` — iterates `i` from `start` (inclusive) to `end` (exclusive), incrementing by 1.

**Generic for**: `for (Type x in collection) { ... }` — iterates over all elements of a set, array, or map keys. For sets, the iteration order is unspecified.

### 4.6 Function Call as Statement

`obj.method(args);` — invokes a method and discards the return value. Used for void methods or when the return value is not needed.

## 5. Program Components

### 5.1 Primitives

A **primitive** defines the abstract interface of a cryptographic operation:

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

Primitives declare:
- **Parameters**: Types (`Set`, `Int`, other primitives) that are provided upon instantiation.
- **Fields**: Named type aliases (e.g., `Set Key = KeySpace`) that become accessible as `E.Key`.
- **Method signatures**: Abstract method declarations with no bodies.

Primitives represent the **syntactic interface** that schemes must implement. They carry no behavioral semantics of their own.

### 5.2 Schemes

A **scheme** is a concrete implementation of a primitive:

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

    Message? Dec(Key k, Ciphertext c) {
        return c + k;
    }
}
```

Schemes provide:
- **Field definitions**: Concrete types for the primitive's abstract type aliases.
- **Method implementations**: Executable code for each method declared in the primitive.
- **`requires` clauses** (optional): Preconditions on parameters that must hold for the scheme to be well-defined (e.g., `requires F.out >= lambda;`). `requires` may express type-level equalities (`requires E.Key == BitString<n>;`) or value-level numeric equalities (`requires F.in == 1;`); the latter propagate into typechecking, so a literal `BitString<1>` can unify with a symbolic `BitString<F.in>` under such a constraint. A `requires` clause may also assert that a **group's order is prime**: `requires <group>.order is prime;`. This is the prime-order opt-in described under `Group` above — it licenses the injective-exponent canonicalizations (treating `x ^ k` as injective for known-nonzero `k`) — and is consumed by the engine's transform layer rather than by typechecking. `requires` clauses appear in both scheme definitions and proof `requires:` blocks.
- **Composition**: Schemes can take other primitives as parameters and call their methods (e.g., a scheme parameterized by `PRF F` can call `F.evaluate(k, x)`).
- **Self-reference**: Within a scheme body, `this.MethodName(args)` calls another method of the same scheme. During proof verification, `this` is resolved to the scheme's instance name.

### 5.3 Games

A **game** is a stateful interactive system:

```
Game Left(SymEnc E) {
    E.Key k;

    Void Initialize() {
        k = E.KeyGen();
    }

    E.Ciphertext Eavesdrop(E.Message mL, E.Message mR) {
        return E.Enc(k, mL);
    }
}
```

Games define:
- **Parameters**: Values provided upon instantiation.
- **State fields**: Mutable variables that persist across oracle calls. May be declared with or without initializers. Uninitialized fields have undefined values until assigned.
- **Methods**: Oracle procedures callable by the adversary.
  - **`Initialize`**: A distinguished method (when present) that is called exactly once before any other oracle. Typically has return type `Void`, though it may return a value in phased games.
  - **Other methods**: Oracles that the adversary may call in any order, any number of times.

### 5.4 Security Properties (Game Files)

A **security property** is defined as a pair of games in a `.game` file:

```
Game Left(SymEnc E) { ... }
Game Right(SymEnc E) { ... }
export as CPA;
```

The two games (typically named `Left`/`Right` or `Real`/`Random`) represent the two sides of an indistinguishability challenge. A scheme satisfies the security property if no efficient adversary can distinguish between interacting with the left game versus the right game (with more than negligible advantage).

FrogLang uses the **left/right (indistinguishability)** formulation exclusively, rather than win/lose games. Security properties from the literature that are naturally stated as win/lose (e.g., unforgeability) can be reformulated as left/right indistinguishability games.

**Advantage clause (helper games).** A `.game` file may declare its statistical distinguishing bound with an optional `advantage <= <expr>;` clause between the two games and `export as`:

```
Game Left(Set S) { ... }
Game Right(Set S) { ... }
advantage <= count_Samp * count_Samp / |S|;
export as DistinctSampling;
```

The bound is numeric arithmetic (`+ - * / ^`, `|S|` cardinality, literals) over the games' shared parameters and per-oracle query counts written `count_<Oracle>`, where `<Oracle>` names a (non-`Initialize`) method of the games. It is a *declared, unconditional* fact — the semantic checker enforces only well-formedness, and it is trusted like the helper game itself. So only helper games that encode statistical facts (e.g. `examples/Games/Helpers/`) carry a clause; genuine cryptographic assumptions get none. When such a helper is used in an assumption hop, the engine substitutes the clause to turn the hop's opaque advantage term into this concrete statistical expression, stated in the theorem game's own query counts.

### 5.5 Phases

Games may be organized into **phases** for security definitions that involve distinct stages of interaction (e.g., CCA security):

```
Phase {
    Void Initialize() {
        k = E.KeyGen();
    }
    oracles: [Enc, Dec];
}

Phase {
    E.Ciphertext Initialize(E.Message mL, E.Message mR) {
        cStar = E.Enc(k, mL);
        return cStar;
    }
    oracles: [Enc, restrainedDec];
}
```

Each phase has its own `Initialize` method (which transitions to the next phase) and a list of oracles available during that phase. The adversary interacts with one phase at a time: the first phase's `Initialize` runs, then the adversary calls the first phase's oracles, then the second phase's `Initialize` runs (triggered by the adversary), and the adversary calls the second phase's oracles, and so on.

State fields are shared across all phases.

### 5.6 Reductions

A **reduction** adapts an adversary for one security game into an adversary for another:

```
Reduction R(PRG G, TriplingPRG T) compose Security(G)
    against Security(T).Adversary {

    BitString<T.lambda + T.stretch> Query() {
        BitString<2 * T.lambda> result = challenger.Query();
        BitString<T.lambda> x = result[0 : T.lambda];
        BitString<T.lambda> y = result[T.lambda : 2 * T.lambda];
        BitString<2 * T.lambda> result2 = G.evaluate(y);
        return x || result2;
    }
}
```

A reduction specifies:
- **`compose SecurityGame(params)`**: The assumed security game whose oracles the reduction delegates to via `challenger`.
- **`against TheoremGame(params).Adversary`**: The theorem game whose adversary the reduction must simulate oracles for.
- **Body**: Methods that implement the theorem game's oracle interface, using `challenger.Method(args)` to call the assumed security game's oracles.
- **State fields** (optional): The reduction may maintain its own state across oracle calls.
- **Parameter rule**: The reduction's parameter list must include every parameter needed to instantiate the composed security game, even if some parameters are not referenced in the reduction body.

## 6. Game Execution Semantics

This section describes the semantics of executing a game in the context of an adversary. This is the core semantic model of FrogLang.

### 6.1 The Adversary Model

An **adversary** is an abstract, computationally bounded entity that interacts with a game through its oracle interface. The adversary is not explicitly represented in FrogLang — it is the implicit external entity that:

1. Receives access to the game's oracles (methods other than `Initialize`, or in phased games, the oracles listed for each phase).
2. Can call any available oracle, in any order, any number of times.
3. Can choose the arguments to each oracle call adaptively — that is, based on the results of all previous oracle calls.
4. Produces some output at the end of the interaction.

The adversary has no direct access to the game's internal state (fields). It can only observe the game through the values returned by oracle calls.

### 6.2 Game Execution Model

The execution of a game `G` with an adversary `A` proceeds as follows:

1. **Field initialization**: All state fields are initialized according to their declarations. Fields with explicit initializers (`Type x = expr;`) are set to the value of `expr`. Fields without initializers (`Type x;`) are left in an undefined state.

2. **Initialize phase**: If the game has an `Initialize` method, it is called exactly once. This typically performs setup operations like sampling cryptographic keys.

3. **Oracle interaction phase**: The adversary `A` is given access to the game's oracle methods. The adversary may:
   - Call any oracle, with any valid arguments, at any time.
   - Call oracles in any order.
   - Call each oracle any number of times (including zero times).
   - Choose arguments adaptively based on previous oracle responses.

4. **Termination**: The adversary eventually halts and produces an output value.

For **phased games**, the execution is:
1. Field initialization.
2. Phase 1's `Initialize` runs.
3. The adversary calls Phase 1's oracles (listed in `oracles: [...]`).
4. The adversary triggers Phase 2 by calling Phase 2's `Initialize`.
5. The adversary calls Phase 2's oracles.
6. (And so on for additional phases.)
7. The adversary halts and produces output.

### 6.3 State Semantics

- **Persistence**: State fields persist across all oracle calls within a game execution. A value written to a field in one oracle call is visible in subsequent calls.
- **Isolation**: Each game execution is independent. There is no state shared between different game executions.
- **Scope**: Local variables (declared within a method body) are scoped to that method invocation. Each oracle call gets fresh local variables. Parameters are scoped to the method body.

### 6.4 Non-determinism and Sampling

**Functions in FrogLang are by default non-deterministic.** When a scheme method like `F.evaluate(k, x)` is called, each invocation may in principle return a different result, even with the same arguments. This is the default semantic model because FrogLang does not assume anything about the implementation of a primitive's methods beyond their type signatures.

**Method annotations** on primitive declarations can override this default:
- `deterministic` — the method always returns the same output for the same inputs. The engine exploits this annotation in several ways:
  - **Purity for inlining/aliasing**: Deterministic calls are treated as pure expressions for expression aliasing (`ForwardExpressionAlias`), field hoisting (`HoistFieldPureAlias`), assignment collapsing (`CollapseAssignment`), field inlining (`InlineSingleUseField`), and tuple index folding (`FoldTupleIndex`).
  - **Same-method deduplication**: `DeduplicateDeterministicCalls` extracts duplicate deterministic calls with structurally equal arguments into a shared local variable. For example, `[F.evaluate(k, x), F.evaluate(k, x)]` becomes `v = F.evaluate(k, x); [v, v]`.
  - **Cross-method field alias**: `CrossMethodFieldAlias` propagates field assignments of deterministic calls to other methods. If Initialize stores `field = F.evaluate(k)` and an oracle also calls `F.evaluate(k)`, the oracle's call is replaced with the field reference.
- `injective` — the method maps distinct inputs to distinct outputs. The `ChallengeExclusionRFToUniform` transform uses this to see through encoding wrappers when checking whether RF arguments structurally differ.

Example: `deterministic injective BitString<n> Encode(GroupElem g);`

Together, these transforms eliminate the need for explicit `IsDeterministic` assumption games in proofs. Previously, proofs required workaround games (e.g., `PRFIsDeterministic` with `TwoCalls`/`OneCall` sides) to establish that calling a deterministic function twice yields the same result. The engine now handles this automatically via the `deterministic` annotation.

**Sampling statements** (`<-`) are the explicit source of randomness. Each sampling statement draws an independent, uniformly random value from the specified domain. The semantics of sampling are:

- **Independence**: Distinct sampling statements produce independent random values, even if they sample from the same type.
- **Uniformity**: The distribution is uniform over the specified domain.
- **Freshness**: Each execution of a sampling statement (including across multiple calls to the same oracle) produces a fresh independent value.

### 6.5 Random Functions

A `Function<D, R>` value represents a truly random function from `D` to `R`. Semantically:

- It is a function chosen uniformly at random from the set of all functions from `D` to `R`.
- It is **consistent**: calling `RF(x)` twice with the same `x` returns the same value.
- It is **independent across inputs**: for distinct inputs `x1 != x2`, the outputs `RF(x1)` and `RF(x2)` are independently and uniformly distributed over `R`.
- It can be thought of as a lazily-populated lookup table: the first time a new input `x` is queried, a fresh uniform value is sampled from `R` and stored; subsequent queries on `x` return the stored value.

Random functions are the standard idealization used in cryptographic proofs. They commonly appear in the "Random" side of PRF security games, where the adversary's challenge is to distinguish a PRF from a truly random function.

See §9.3 for the multi-map generalization (guarded two-map lazy lookup).

### 6.6 Unique Sampling

The statement `Type x <-uniq[S] Type;` has the following semantics:

1. Sample `x` uniformly from `Type \ S` (the elements of `Type` not in `S`).
2. The resulting `x` is guaranteed to be distinct from all elements currently in `S`.
3. Semantically, this is equivalent to rejection sampling: sample from `Type`, if the result is in `S` then resample, repeat until a fresh value is obtained.
4. The probability of needing to resample (collision probability) is `|S| / |Type|` per trial.

This is used in contexts where freshness is important, such as ensuring nonces are never reused. The `UniqueSampling` helper game captures the assumption that sampling with replacement is indistinguishable from sampling without replacement (valid when the collision probability is negligible).

### 6.7 Map Semantics

Maps (`Map<K, V>`) are finite partial functions:

- **Empty on creation**: A newly declared map has an empty domain.
- **Lookup**: `M[k]` returns the value associated with key `k`. Accessing a key not in the domain is undefined.
- **Update**: `M[k] = v;` associates key `k` with value `v`, extending or modifying the map.
- **Sampling into map**: `M[k] <- Type;` samples a uniform value from `Type` and stores it at key `k`.
- **Membership**: `k in M` tests whether `k` is in the map's domain.
- **Size**: `|M|` returns the number of key-value pairs.

### 6.8 Optional Type Semantics

Values of type `T?` are either a value of type `T` or `None`:

- **Construction**: Any expression of type `T` implicitly converts to `T?`. The literal `None` has type `T?` for any `T`.
- **Comparison**: `x == None` tests whether an optional value is null.
- **Usage**: Typically used for operations that may fail, such as decryption returning `Message?` (where `None` indicates decryption failure).

## 7. Composition Semantics

### 7.1 Game Composition with Schemes

When a security game is instantiated with a scheme, the scheme's methods become callable within the game body. For example, if `CPA(E)` is instantiated with `E = OTP(lambda)`, then calls to `E.Enc(k, m)` within the game body invoke the OTP scheme's `Enc` method.

During proof verification, these method calls are **inlined**: the call `E.Enc(k, m)` is replaced by the body of OTP's `Enc` method with parameters substituted. This is the primary mechanism by which the proof engine reduces abstract game descriptions to concrete, comparable code.

### 7.2 Game Composition with Reductions

When a game is composed with a reduction, the resulting system is a new game whose oracles are the reduction's methods. The reduction's `challenger` variable is bound to the composed security game.

For example, `Security(G).Real compose R(G, T)` produces a game where:
1. The adversary calls `R`'s oracle methods (which implement the interface of `Security(T)`).
2. Inside `R`'s methods, calls to `challenger.Query()` invoke `Security(G).Real`'s `Query` oracle.
3. The combined state includes both `R`'s fields and `Security(G).Real`'s fields.

The composition merges the `Initialize` methods:
- If both the reduction and the composed game have `Initialize`, the reduction's `Initialize` may explicitly call `challenger.Initialize()` to invoke the composed game's initialization.
- The resulting game's initialization runs both, establishing the combined initial state.

### 7.3 Inlining

**Inlining** is the process of replacing a method call with the method's body, substituting parameters with arguments. This is the key mechanism by which the proof engine transforms composed games into flat, comparable code.

When inlining `obj.method(arg1, arg2)`:
1. A fresh copy of the method body is created.
2. Each formal parameter is substituted with the corresponding argument expression.
3. Locally declared variables are renamed to avoid name collisions (using a scheme like `method@varname`).
4. The method call expression is replaced by the return expression (or the call statement is replaced by the method body for void methods).

Inlining is applied repeatedly in a fixed-point loop until no more method calls can be expanded. This converges because the call graph is finite and acyclic (recursive method calls are not supported in FrogLang).

## 8. Proof Semantics

### 8.1 Proof Structure

A proof file establishes that a target security property holds for a scheme, under stated assumptions:

```
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
    Security(G).Real compose R1(G, T) against Security(T).Adversary;
    Security(G).Random compose R1(G, T) against Security(T).Adversary;
    ...
    Security(T).Random against Security(T).Adversary;
```

- **`let:`** — Declares parameters and instantiates schemes. These definitions are in scope throughout the proof.
- **`assume:`** — Lists security properties assumed to hold for underlying primitives/schemes. These justify assumption hops.
- **`theorem:`** — The target security property to be proven.
- **`bound:`** (optional, between `theorem:` and `games:`) — the advantage bound the author claims the proof establishes. Numeric arithmetic over `advantage(<notion> compose <reduction>)` terms (the reduction named from the proof's own declarations; `advantage(<notion>)` for a directly-played hop), per-oracle counts `count_<Oracle>` of the theorem game, cardinalities `|Type|`, and `let:` parameters. After the proof verifies, the engine checks the claim is a valid upper bound on the bound it synthesizes from the hops and reports `verified` / `NOT verified` / `undecided`; a `NOT verified` claim fails `prove` unless `--skip-bound` is passed. "verified" means the claim is a valid (possibly loose) upper bound, not an independent security proof.
- **`games:`** — A sequence of game steps forming the proof.

### 8.2 The Game Sequence

The `games:` section lists a sequence of game configurations. The first game must be `Theorem.Side1 against Theorem.Adversary` and the last must be `Theorem.Side2 against Theorem.Adversary` (where Side1 and Side2 are the two sides of the theorem's security property, e.g., Left/Right or Real/Random).

Each consecutive pair of games in the sequence must be justified as either:

1. **An interchangeability hop**: The two games are code-equivalent (verified by the engine).
2. **An assumption hop**: The two games differ only in which side of an assumed security property is used, and that assumption appears in the `assume:` section.

### 8.3 Interchangeability

Two games are **interchangeable** if, for all adversaries `A`:

```
Pr[A interacting with Game1 outputs 1] = Pr[A interacting with Game2 outputs 1]
```

That is, no adversary can distinguish between the two games — they induce identical probability distributions over adversary outputs.

The ProofFrog engine verifies interchangeability by:

1. **Canonicalization**: Both games are transformed through a deterministic pipeline of semantics-preserving rewrites (inlining, algebraic simplification, dead code elimination, sampling normalization, etc.) to arrive at a canonical form.
2. **Structural comparison**: The canonical forms are compared structurally. If they are identical (up to alpha-equivalence of bound variables), the games are interchangeable.
3. **SMT-assisted comparison**: If the canonical forms differ only in the conditions of `if` statements, the engine uses Z3 to check whether the differing conditions are logically equivalent. If so, the games are interchangeable.

### 8.4 Assumption Hops

An assumption hop transitions between two game steps that differ in which side of an assumed security property is composed with a reduction:

```
Security(G).Real compose R(...) against Adversary;    // step i
Security(G).Random compose R(...) against Adversary;  // step i+1
```

This hop is justified by the assumption `Security(G)` in the `assume:` section. The direction is irrelevant — assumption hops are **bidirectional** because indistinguishability is symmetric.

### 8.5 The Standard Reduction Pattern

A typical use of a reduction in a proof follows a four-step pattern:

```
G_A against Adversary;                                  // (1) interchangeability
Security(G).Side1 compose R against Adversary;          // (2) interchangeability
Security(G).Side2 compose R against Adversary;          // (3) by assumption
G_B against Adversary;                                  // (4) interchangeability
```

- Steps 1-2: Verified as interchangeable by the engine (the game `G_A` is equivalent to composing `Security.Side1` with the reduction `R`).
- Steps 2-3: Justified by the assumption that `Security(G)` holds.
- Steps 3-4: Verified as interchangeable by the engine.

### 8.6 Induction

Proofs may use **induction** for hybrid arguments that transition through a parameterized family of games:

```
induction(i from 1 to q) {
    Security(F).Real compose R_Hybrid(F, i) against Adversary;
    Security(F).Random compose R_Hybrid(F, i) against Adversary;
}
```

This expands to `q` iterations, each replacing one oracle call with a random one (or vice versa). Induction is the mechanism for lifting single-call security (e.g., single-key PRF security) to multi-call security (e.g., multi-key PRF security).

### 8.7 Step Assumptions

`assume expr;` statements within the `games:` section assert predicates that constrain the proof context (e.g., bounding the number of oracle calls: `assume R.count >= 1;`). These are used alongside induction to express hybrid argument invariants.

## 9. Semantic Equivalences

The proof engine considers the following transformations to be semantics-preserving (i.e., they produce interchangeable games):

### 9.1 Algebraic Identities

- **XOR with uniform**: `u <- BitString<n>; return u + m;` is equivalent to `u <- BitString<n>; return u;` (XOR of a uniform value with any value is uniform), provided `u` is used only once.
- **ModInt with uniform**: `u <- ModInt<q>; return u + m;` is equivalent to `u <- ModInt<q>; return u;` (addition of a uniform element modulo `q` with any value is uniform), provided `u` is used only once.
- **GroupElem with uniform**: `u <- GroupElem<G>; return u * m;` is equivalent to `u <- GroupElem<G>; return u;` (multiplication of a uniform group element by any fixed element is uniform, since left-multiplication is a bijection on the group). Likewise for `m * u`, `m / u`. Requires `u` to be used only once.
- **XOR cancellation**: `x + x` simplifies to `0^n` (XOR is self-inverse).
- **XOR identity**: `x + 0^n` simplifies to `x`.
- **ModInt identities**: Additive/multiplicative identity, multiplicative zero, additive inverse, double negation.
- **GroupElem cancellation**: `x * m / x` simplifies to `m` (group element with its inverse cancels), when `x` is deterministic.
- **GroupElem exponentiation identities**: `g ^ 0` simplifies to `G.identity`; `g ^ 1` simplifies to `g`.
- **GroupElem multiplicative identity**: `G.identity * g` simplifies to `g`; `g * G.identity` simplifies to `g`; `g / G.identity` simplifies to `g`.
- **GroupElem power-of-power**: `(h ^ a) ^ b` simplifies to `h ^ (a * b)`, when `a` and `b` have compatible types for multiplication.
- **GroupElem exponent combination**: `g^a * g^b` simplifies to `g^(a + b)`; `g^a / g^b` simplifies to `g^(a - b)`, when the bases are structurally identical and deterministic.
- **Reflexive comparisons**: `x == x` simplifies to `true`; `x != x` to `false`.
- **Injective-call equality**: for a primitive method `f` annotated `deterministic injective`, `f(a1, ..., an) == f(b1, ..., bn)` simplifies to `(a1 == b1) && ... && (an == bn)` (and the `!=` variant to the disjunction of per-argument disequalities). Sound because `injective` guarantees that distinct input tuples map to distinct outputs, so equal outputs imply equal input tuples; `deterministic` guarantees that repeated evaluation on the same input yields the same value. Does not apply to calls through sampled `Function<D, R>` variables (a random function is not injective in general).

### 9.2 Sampling Transformations

- **Merge uniform samples**: Independent uniform samples of `BitString<n>` and `BitString<m>` that are only used via concatenation can be merged into a single `BitString<n + m>` sample. Sound because concatenation of independent uniform bitstrings is a uniform bitstring of the combined length.
- **Split uniform samples**: A single `BitString<n>` sample accessed only through non-overlapping slices can be split into independent samples of each slice's length. Sound because non-overlapping slices of a uniform bitstring are independent uniform bitstrings.
- **Sample reordering**: Independent samples can be reordered without affecting semantics.
- **Sample sinking**: A uniform sample before an if/else can be moved into the branch that uses it (when independent of the condition).

### 9.3 Random Function Simplification

- When all inputs to a `Function` field are guaranteed to be pairwise distinct (via unique sampling), each output `RF(x)` is equivalent to an independent uniform sample. Sound because a random function on distinct inputs produces independent uniform outputs.
- **Guarded two-map lazy lookup**: Two `Map<K, V>` fields accessed only through the lazy-sample idiom, with every write guarded by membership checks excluding both maps, and matching `V`-sampling, are equivalent to a single sampled `Function<K, V>` with each lazy-path occurrence rewritten as `F(k)`. Sound because the pair defines a single lazily-populated lookup table (see §6.5) partitioned across two storage locations, and the partition is adversary-invisible (§6.3).
- **Local vs. let-bound random function interchangeability**: A game field `F : Function<K, V>` sampled once in `Initialize` (`F <- Function<K, V>;`), never otherwise assigned, and used only via `F(arg)` calls, is interchangeable with a let-bound sampled `H : Function<K, V>` of identical type, provided `H` is not otherwise referenced in the game. Sound because uniform random functions with no correlated observations produce identical output distributions.

### 9.4 Code Simplifications

- **Dead code elimination**: Unreachable code (after all paths return) and unused variables/fields are removed.
- **Constant folding**: Compile-time evaluable expressions are reduced.
- **Variable inlining**: Single-use variables whose initializers are pure expressions are inlined.
- **Redundant copy elimination**: Variables that are trivial copies of other variables are eliminated.
- **Branch elimination**: `if (true)` and `if (false)` branches are simplified.
- **Tuple index folding**: `[e0, e1][1]` simplifies to `e1`.

## 10. What FrogLang Does Not Model

FrogLang is designed for a specific class of cryptographic proofs. Several aspects of real cryptographic systems are outside its scope:

- **Computational complexity**: FrogLang does not model the running time of adversaries or schemes. The notion of "efficient adversary" is implicit.
- **Negligible quantities**: Security loss and advantage bounds are not tracked quantitatively. The proof establishes qualitative reduction (if the assumption holds, the theorem holds), not tight bounds.
- **Concrete security parameters**: While type parameters like `lambda` appear, they are symbolic — no concrete instantiation or security level analysis is performed.
- **Recursive or unbounded computation**: Methods cannot call themselves recursively. The language is not Turing-complete.
- **Side channels**: Timing, power analysis, and other side-channel attacks are not modeled.
- **Concurrency**: All oracle calls are sequential. There is no concurrent or parallel execution model.
- **Explicit abort/failure**: There is no `abort` statement. Failure conditions are modeled through control flow (returning `None`, conditional returns) or implicitly through collision probabilities in unique sampling.
