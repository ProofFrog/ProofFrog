# ProofFrog Transform Pass Index

Names and one-line descriptions of every pass in the canonicalization
pipeline. Use this as a capability list when reasoning about whether the
engine can simplify a given pattern. The pass code lives in
`proof_frog/transforms/` (in the source repo).

## Core Pipeline

The core pipeline runs in a fixed-point loop until convergence.

### Sampling (`sampling.py`)

| Pass | Description |
|---|---|
| SingleCallFieldToLocal | Pushes field-initialized uniform samples to oracle locals when max_calls=1. |
| CounterGuardedFieldToLocal | Converts fields to locals when only read inside counter-guarded branches. |
| SimplifySplice | Replaces slice accesses on concatenated variables with the original components. |
| MergeUniformSamples | Merges independent uniform BitString samples used only via concatenation. |
| MergeProductSamples | Merges independent uniform samples combined into a returned tuple. |
| SplitUniformSamples | Splits a uniform BitString sample accessed only via non-overlapping slices. |
| SinkUniformSample | Moves a uniform sample into the single if-branch that uses it. |
| LocalizeInitOnlyFieldSample | Converts field samples to local samples when the field is only used in Initialize. |
| SliceOfInlineConcat | Rewrites slice-of-concat expressions when bounds line up with the underlying concat components. |

### Symbolic (`symbolic.py`)

| Pass | Description |
|---|---|
| SymbolicComputation | Evaluates arithmetic sub-expressions symbolically using SymPy. |

### Structural (`structural.py`)

| Pass | Description |
|---|---|
| TopologicalSort | Reorders statements by dependency graph. |
| RemoveDuplicateFields | Removes fields with same type that always hold the same value. |
| RemoveUnnecessaryFields | Removes unused fields and dead statements via liveness analysis. |
| UniformBijectionElimination | Replaces `f(x)` with `x` when x is uniform and f is a deterministic injective bijection. |

### Random Functions (`random_functions.py`)

| Pass | Description |
|---|---|
| ExtractRFCalls | Extracts RF calls embedded in expressions into separate assignments. |
| UniqueRFSimplification | Replaces `z = RF(r)` with `z <- R` when all RF inputs are uniquely sampled. |
| ChallengeExclusionRFToUniform | Replaces Initialize RF calls with uniform samples when oracle guards exclude the input. |
| LocalRFToUniform | Replaces locally-sampled RFs called exactly once with uniform samples. |
| DistinctConstRFToUniform | Replaces locally-sampled RFs called on pairwise-distinct literal constants with independent uniform samples. |
| FreshInputRFToUniform | Replaces `RF(v)`, `RF([v, ...])`, or `RF(v \|\| ...)` with uniform sample when `v` is a fresh single-use `<-uniq` local. |
| LocalFunctionFieldToLet | Unifies a game-local sampled `Function<K,V>` field with a let-bound sampled `H` of identical type when `H` is otherwise unused in the game. |
| LazyMapToSampledFunction | Rewrites a `Map<K,V>` field used exclusively as a lazy random oracle into a sampled `Function<K,V>` field. |
| LazyMapPairToSampledFunction | Generalizes LazyMapToSampledFunction to a pair of maps used jointly via the guarded-pair idiom. |

### Map Iteration (`map_iteration.py`)

| Pass | Description |
|---|---|
| LazyMapScan | Rewrites a `for e in M.entries { if e[0] == k { return e[1]; } }` scan over a lazy map into a direct `M[k]` lookup under uniqueness of map keys. |

### Map Reindex (`map_reindex.py`)

| Pass | Description |
|---|---|
| MapKeyReindex | Re-indexes a lazy map whose key is a consistent injective wrapper `w(x)` to use the inner value `x` directly. |

### Inlining (`inlining.py`)

| Pass | Description |
|---|---|
| RedundantCopy | Eliminates redundant variable copies (`Type v = w` where v replaces w). |
| IfSplitBranchAssignment | Moves subsequent statements into if-else branches when all branches assign the same variable. |
| InlineSingleUseVariable | Inlines `Type v = expr` when v is used exactly once. |
| DeduplicateDeterministicCalls | Extracts duplicate deterministic primitive calls into shared variables. |
| ForwardExpressionAlias | Replaces repeated pure expressions with their named alias variable. |
| HoistFieldPureAlias | Hoists field assignments of pure expressions before their first use. |
| CrossMethodFieldAlias | Replaces deterministic calls in oracles with matching field references from Initialize. |
| HoistDeterministicCallToInitialize | Hoists a deterministic call out of oracles into Initialize and caches it in a new field. |
| SplitOpaqueTupleField | Splits a `ProductType` field whose RHS is an opaque call and whose only reads are constant-indexed projections, into one fresh field per used component. |
| HoistGroupExpToInitialize | Hoists `base ^ k` group exponentiations out of oracles into `Initialize` and caches the result in a pinned field; requires a prime-order / nonzero-exponent context. |
| RefactorGroupElemFieldExp | Rewrites `base ^ (a * b)` as `Field2 ^ b` when a pre-existing pinned field `Field2 = base ^ a` exists. |
| InlineSingleUseField | Inlines field assignments when the field is used exactly once in the same method (skips pinned fields). |
| InlineSingleUseField (cross-method) | Extends field inlining across methods when expression is pure with stable field free vars. |
| CollapseAssignment | Collapses a declaration followed by reassignment into one statement. |
| ExtractRepeatedTupleAccess | Extracts repeated `var[constant]` accesses into named local variables (CSE for tuple destructuring). |
| InlineLocalTupleLiteral | Substitutes `[T0,...] v = [e0,...]` through constant-index accesses when accesses are pure. |
| InlineMultiUsePureExpression | Inlines multi-use pure (call-free) expressions at every use site; also inlines `Function<D,R>` proof-let calls. |
| RedundantFieldCopy | Eliminates intermediate locals used only to assign to a field. |

### Algebraic (`algebraic.py`)

| Pass | Description |
|---|---|
| UniformXorSimplification | Simplifies `u + m` to `u` when u is a single-use uniform BitString sample. |
| UniformModIntSimplification | Simplifies `u +/- m` to `u` when u is a single-use uniform ModInt sample. |
| UniformGroupElemSimplification | Simplifies `u * m` or `m / u` to `u` when u is a single-use uniform GroupElem sample. |
| SimplifyNot | Rewrites `!(a == b)` as `a != b`. |
| BooleanIdentity | Simplifies boolean AND/OR with literal `true`/`false` operands. |
| BooleanAbsorption | Drops a conjunct `B` from an `A && B` chain when `A`'s flat OR-disjuncts are a subset of `B`'s. |
| XorCancellation | Cancels pairs of identical terms in XOR chains (`a + a` = `0^n`). |
| XorIdentity | Removes `0^n` terms from XOR chains. |
| ModIntSimplification | Applies algebraic identities for ModInt arithmetic (identity, zero, inverse). |
| GroupElemSimplification | Group algebra identities: power-of-power, `g^0`/`g^1`, identity element rules. |
| GroupElemCancellation | Cancels matching terms in GroupElem multiply/divide chains (`x * m / x` = `m`). |
| GroupElemExponentCombination | Combines same-base exponentiations: `g^a * g^b` = `g^(a+b)`. |
| NormalizeCommutativeChains | Sorts operands of commutative chains by structural key; also normalizes `==`/`!=` operand order. |
| FlattenConcatChain | Left-associates `\|\|` chains; sound under both Boolean OR and BitString concatenation. |
| ReflexiveComparison | Simplifies `x == x` to `true` and `x != x` to `false`. |
| InjectiveEqualitySimplify | Rewrites `f(a1,...) == f(b1,...)` to `(a1==b1) && ...` when `f` is `deterministic injective`. |
| ConcatEqualityDecompose | Decomposes `(a \|\| b \|\| ...) op other` into pairwise slice equalities when concatenation-term lengths are derivable. |
| TupleEqualityDecompose | Rewrites `a != b` between tuple-typed expressions to the per-component disjunction of `!=`. `==` is intentionally NOT decomposed. |

### Control Flow (`control_flow.py`)

| Pass | Description |
|---|---|
| IfConditionAliasSubstitution | Substitutes field references with local aliases inside equality-guarded if-branches. |
| RedundantConditionalReturn | Removes `if (c) { return X; } return X;` patterns. |
| AbsorbRedundantEarlyReturn | Absorbs `if (P) { return X; } ... if (Q) { ... } return X;` into `if (!P && Q) { ... } return X;` (outermost-block-only). |
| IfFalseReturnToConjunction | Absorbs `if (P) { return false; } ...; return Q;` into `...; return Q && !P;`. |
| BranchElimination | Eliminates branches with statically known `true`/`false` conditions. |
| UniqExclusionBranchElimination | Statically eliminates `x in S` branches when `x` was sampled via `<-uniq[S] T` and `S` has not been mutated since. |
| ElseUnwrap | Unwraps else blocks when the if-branch unconditionally returns. |
| SimplifyReturn | Inlines `Type v = expr; return v;` into `return expr;`. |
| SimplifyIf | Merges adjacent if/else-if branches with identical (alpha-equivalent) bodies. |
| RemoveUnreachable | Removes statements after all execution paths have returned (Z3-assisted). |
| FoldEquivalentReturnBranch | Folds `if (P) { return X; } return Y;` to `return Y;` when Z3 proves `P ⇒ (X ↔ Y)`. Refuses on any non-deterministic call. |

### Types (`types.py`)

| Pass | Description |
|---|---|
| DeadNullGuardElimination | Removes `if (x == None)` guards when x cannot be null. |
| SubsetTypeNormalization | Normalizes subset types to their superset equivalents. |

### Tuples (`tuples.py`)

| Pass | Description |
|---|---|
| FoldTupleIndex | Constant-folds `[e0, e1, ...][i]` to `e_i`. |
| ExpandTuple | Expands product-typed variables into individual component variables. |
| SimplifyTuple | Collapses `[v[0], v[1], ...]` back to `v`. |
| CollapseSingleIndexTuple | Collapses product-typed variable accessed at a single constant index. |

## Standardization Pipeline

The standardization pipeline runs once after the core pipeline converges.

### Standardization (`standardization.py`)

| Pass | Description |
|---|---|
| VariableStandardize | Renames local variables to canonical names (v1, v2, ...). |
| StandardizeFieldNames | Normalizes field names to canonical ordering. Two-phase: rename by oracle first-read order, then regroup by type. |
| NormalizeCommutativeChains | Re-sorts commutative chains after field/variable renaming. |
| BubbleSortFieldAssignments | Sorts field assignments into canonical dependency order. |
| StabilizeIndependentStatements | Sorts independent statements by value expression for deterministic ordering. |
| FieldLexMinByRHS | Within each same-type field group, picks the lex-smallest slot index for the field whose Initialize-RHS sort key is smallest. |

## Inlining Infrastructure (`visitors.py`)

Modifications to the `InlineTransformer` that runs during proof composition.

| Component | Description |
|---|---|
| InlinerEarlyReturnNormalization | Normalizes early returns in inlined methods so no bare `ReturnStatement` leaks into the caller. |

## Per-Step Passes

### Assumptions (`assumptions.py`)

| Pass | Description |
|---|---|
| ApplyAssumptions | Applies step-specific assumed predicates using Z3 implication checking. |

## Equivalence-engine escape hatches

NOT transforms — fallbacks invoked by the proof engine after
`CORE_PIPELINE + STANDARDIZATION_PIPELINE` runs and structural game equality fails.
Live in `proof_frog/proof_engine.py`.

| Hook | Description |
|---|---|
| `_z3_residual_equivalence` (+ `Z3FormulaVisitor.opaque_func_call_fallback`) | If two games differ only in if-conditions and/or final return expressions, neutralize both classes and re-check structural equality; otherwise assert `Not(f1 == f2)` is `unsat` via Z3 with opaque-call fallback for shapes Z3 can't mix. Refuses if either differing expression contains a non-deterministic call (Gap-F guard). |
