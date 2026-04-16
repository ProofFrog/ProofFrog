# Release Notes — v0.4.1

This release focuses on proof engine improvements, adding new canonicalization transforms and fixing correctness bugs in the inliner and type resolver. The main driver is a complete IND-CCA proof of the CK hybrid KEM combiner from the StarHunters paper, which required extending the engine to handle tuple reasoning, cross-scope dead branch elimination, and deterministic call hoisting.

## New canonicalization transforms

- **`HoistDeterministicCallToInitialize`** (#206): Hoists a repeated deterministic call out of oracle methods into `Initialize`, caching the result in a new field. Enables proofs where the reduction caches a challenger response while the scheme re-expands it at each oracle site.
- **`ExtractRepeatedTupleAccess`** (#204): Extracts repeated `variable[constant]` tuple accesses into named locals, normalizing explicit tuple destructuring against inline access.
- **`IfSplitBranchAssignment`** (#204): Moves subsequent code into if/else branches when all branches assign the same variable.
- **`ElseUnwrap`** (#204): Unwraps else blocks when the if-branch unconditionally returns.

## Engine improvements

- **Z3 tuple support** (#204): Z3 can now reason about tuple equality, opaque types, and array access.
- **Nested dead branch elimination** (#204): `RemoveUnreachableTransformer` now propagates path constraints into nested blocks, eliminating branches that require cross-scope reasoning.
- Extended `IfConditionAliasSubstitution` to accept `parameter[constant]` patterns (#204).
- Extended `ChallengeExclusionRFToUniform` to resolve local aliases through intermediate cast variables (#204).
- Extended `DeadNullGuardElimination` to handle provably non-nullable expressions (not just variables) (#204).

## Bug fixes

- **Fix inliner early-return handling** (#204): The inliner leaked bare `ReturnStatement` nodes from callees with early returns into the caller's block. Now correctly normalizes early returns via else-branch folding.
- **Fix `_resolve_type_alias` for tuple-of-types** (#203): Tuple arguments substituted for game parameters caused false type mismatches on `FieldAccess` nodes; fixed by adding a `Tuple` case that normalizes to `ProductType`.

## Tooling

- **Dev builds annotated with git SHA** (#205): `proof_frog version` now appends the short commit SHA to dev builds (e.g. `0.4.1.dev0+d3de90e`).

## New examples

- **CK hybrid KEM combiner** (#204): Complete IND-CCA proof for the CK hybrid KEM combiner from the StarHunters paper, verifying all 17 game hops.
