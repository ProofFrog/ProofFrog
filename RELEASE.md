# Release Notes — v0.4.0

This is a major release with significant language additions, many engine soundness fixes and new transforms, a redesigned web interface, and new tooling features.

## Language

- Added built-in `Function<D, R>` type replacing `RandomFunctions`, with random oracle model (ROM) support (#177).
- Added built-in `Group` type and group algebra engine transforms (#176).
- Added `deterministic` and `injective` method annotations for primitives and schemes, with typechecker enforcement of consistency (#179).
- Added support for type equality constraints between abstract and concrete types (#165).
- Added multi-line block comment syntax (`/* ... */`).
- Removed `Phase` support from the grammar and engine.

## Proof Engine

- Parallelized proof hop verification for faster proof checking.
- Added lemma support for modular proof composition via `lemma:` sections (#166).
- Added diagnostic engine for proof failure explanations, including diff classification, near-miss matching, and engine limitation detection (#162).
- Added multi-level verbosity to the `prove` command and web UI (#163).
- Fixed over 30 soundness bugs across numerous transforms, including `CrossMethodFieldAlias`, `HoistFieldPureAlias`, `RedundantFieldCopy`, `InlineSingleUseField`, `CounterGuardedFieldToLocal`, `SimplifyReturn`, `ApplyAssumptions`, and others.

### New and Extended Transforms

- `DeduplicateDeterministicCalls` and `CrossMethodFieldAlias` for deterministic method optimization (#164).
- `NormalizeCommutativeChains` for canonical ordering of `+` and `*` operators.
- `BooleanIdentity` for AND/OR constant folding (#173).
- `DistinctConstRFToUniform` with length-carrying `BinaryNum` refactor (#187).
- `UniformBijectionElimination` replacing the unsound `TrivialEncodingElimination`.
- `ChallengeExclusionRFToUniform` extended for slice-based guards.
- `FreshInputRFToUniform` extended for tuple and concatenation arguments.
- Replaced bubble sort with canonical topological sort in `StabilizeIndependentStatements`.
- Replaced `str()`-based sort keys with structural AST sort keys (#190).

## CLI

- Added `version` command.
- Added `download-examples` command for fetching example files (#193).
- Added `--skip-lemmas` flag for bypassing lemma verification.
- Improved error messages for parse and check commands, including typo suggestions for field access errors (#161).

## Web Interface

- Redesigned toolbar with Insert dropdown and engine introspection actions (Describe, Inlined Game).
- Added wizard system with server-side scaffolding for intermediate games, reductions, and reduction hops.
- Added help menu with links to manual pages.

## MCP Server

- Updated language reference to cover full FrogLang syntax.
