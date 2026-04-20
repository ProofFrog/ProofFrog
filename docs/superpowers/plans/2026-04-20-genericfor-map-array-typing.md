# GenericFor over Map and Array: Typechecking Implementation Plan

> **Status (2026-04-20):** IMPLEMENTED on branch `feat/genericfor-map-array-typing`, commit `e699fb3`. Not merged. All tasks complete; 12 new tests pass; `make lint` clean; `tests/` suite (1534 tests) passes. Tasks 2–6 were collapsed into a single commit with the plan's overall commit message. Task 4 Step 3 (Tuple↔ProductType normalization) was NOT needed — existing `ProductType.__eq__` already compares equal to `Tuple` with matching elements (see `proof_frog/frog_ast.py:156`), so the positive test passed at Step 2. Task 8 Step 3 note below.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Extend FrogLang's typechecker to accept `for (T x in expr)` where `expr` is an `Array<T, n>`, or a `Map<K, V>` projected through `.keys` / `.values` / `.entries`, producing typed AST nodes ready for downstream engine passes.

**Architecture:** Two changes in `proof_frog/semantic_analysis.py`. First, extend the `ComputeTypeVisitor.leave_field_access` and `CheckTypeVisitor.leave_field_access` paths with a `MapType` branch so `M.keys : Set<K>`, `M.values : Set<V>`, `M.entries : Set<[K, V]>`. Second, extend `CheckTypeVisitor.leave_generic_for` so it accepts `ArrayType` in addition to `SetType`, and verifies the loop variable's declared type matches the element type of whichever set/array is being iterated. Grammar is already permissive — no parser changes needed.

**Tech Stack:** Python 3.11+, ANTLR-parsed AST (`proof_frog/frog_ast.py`), pytest, mypy, pylint, black.

**Out of scope for this plan:** All engine-level transforms (§5.2–§5.5 of the design). This plan delivers typechecking and error reporting only; subsequent plans in the series build `LazyMapScan`, lazy-RF-as-Map, and oracle-patching on top of the AST shapes this plan introduces.

---

## File Structure

**Modify:**
- `proof_frog/semantic_analysis.py` — two locations:
  - `ComputeTypeVisitor.leave_field_access` (~line 2006): type assignment for `.keys`/`.values`/`.entries` on `MapType`.
  - `CheckTypeVisitor.leave_field_access` (~line 641): error reporting for malformed Map field access.
  - `CheckTypeVisitor.leave_generic_for` (~line 1346): accept `ArrayType` and validate element type.

**Create:**
- `tests/unit/typechecking/test_generic_for_map_array.py` — all positive and negative tests for this feature.

No changes to parser, AST node definitions, or grammar files.

---

## Preliminaries

Before Task 1, verify baseline:

- [x] **Step 0a: Confirm clean working tree and baseline tests pass**

Run: `cd /Users/dstebila/Dev/ProofFrog/ProofFrog && git status && pytest tests/unit/typechecking/ -q`
Expected: clean tree (or only intentional work-in-progress), all typechecking tests pass.

- [x] **Step 0b: Read the design spec and this plan through once**

Read `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md` §3 and §5.1, and all of this plan. Confirm you understand which four iteration shapes must typecheck, and which file locations change.

---

## Task 1: Create the test file scaffold

**Files:**
- Create: `tests/unit/typechecking/test_generic_for_map_array.py`

- [x] **Step 1: Create the test file with shared helpers**

```python
"""Tests for GenericFor over Map (via .keys/.values/.entries) and Array."""

import pytest

from proof_frog import frog_parser, semantic_analysis


def _check_game(source: str) -> None:
    game = frog_parser.parse_game(source)
    visitor = semantic_analysis.CheckTypeVisitor({}, "test", {})
    visitor.visit(game)


def _check_game_fails(source: str) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_game(source)
```

- [x] **Step 2: Run pytest on the new file to confirm it loads cleanly**

Run: `pytest tests/unit/typechecking/test_generic_for_map_array.py -q`
Expected: `no tests ran` (file loads without import errors).

- [x] **Step 3: Commit**

```bash
git add tests/unit/typechecking/test_generic_for_map_array.py
git commit -m "test: scaffold typechecking tests for generic-for over Map/Array"
```

---

## Task 2: Accept `Array<T, n>` iteration in `leave_generic_for`

**Files:**
- Modify: `proof_frog/semantic_analysis.py` (the `leave_generic_for` method of `CheckTypeVisitor`, currently ~line 1346)
- Test: `tests/unit/typechecking/test_generic_for_map_array.py`

Current behavior: `leave_generic_for` errors on any `over` expression whose type is not `SetType`. We extend to also accept `ArrayType`, and we tighten: when we *do* recognize the container, we check that the loop variable's declared type matches the container's element type.

- [x] **Step 1: Write the failing test**

Append to `tests/unit/typechecking/test_generic_for_map_array.py`:

```python
class TestArrayIteration:
    def test_iterate_array_of_int(self) -> None:
        _check_game("""
            Game G() {
                Array<Int, 4> arr;
                Int Sum() {
                    Int total = 0;
                    for (Int x in arr) {
                        total = total + x;
                    }
                    return total;
                }
            }
            """)

    def test_iterate_array_wrong_element_type_fails(self) -> None:
        _check_game_fails("""
            Game G() {
                Array<Int, 4> arr;
                Void Initialize() {
                    for (Bool x in arr) {
                    }
                }
            }
            """)
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/typechecking/test_generic_for_map_array.py::TestArrayIteration -v`
Expected: `test_iterate_array_of_int` FAILS with `FailedTypeCheck` mentioning "Must iterate over finite set, got type Array<Int, 4>". `test_iterate_array_wrong_element_type_fails` may currently pass-by-accident because the Array path errors out first — that's fine.

- [x] **Step 3: Update `leave_generic_for`**

In `proof_frog/semantic_analysis.py`, replace the current `leave_generic_for` method of `CheckTypeVisitor` (~line 1346):

```python
    def leave_generic_for(self, generic_for: frog_ast.GenericFor) -> None:
        super().leave_generic_for(generic_for)
        over_type = self.get_type_from_ast(generic_for.over)
        if isinstance(over_type, frog_ast.SetType):
            element_type = over_type.parameterization
        elif isinstance(over_type, frog_ast.ArrayType):
            element_type = over_type.element_type
        else:
            self.print_error(
                generic_for,
                f"Must iterate over Set, Array, Map.keys, Map.values, or Map.entries;"
                f" got type {over_type}",
            )
            return
        if element_type is not None and not self.check_types(
            generic_for.var_type, element_type
        ):
            self.print_error(
                generic_for,
                f"Loop variable has type {generic_for.var_type},"
                f" but iteration yields elements of type {element_type}",
            )
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/typechecking/test_generic_for_map_array.py::TestArrayIteration -v`
Expected: both tests PASS.

- [x] **Step 5: Run the full typechecking suite to confirm no regressions**

Run: `pytest tests/unit/typechecking/ -q`
Expected: all tests pass. If anything regresses, it is almost certainly a test that relied on the old loose behavior (loop variable type not cross-checked against set element type). Investigate before proceeding — do not "fix" by reverting the element-type check.

- [x] **Step 6: Commit**

```bash
git add proof_frog/semantic_analysis.py tests/unit/typechecking/test_generic_for_map_array.py
git commit -m "feat(typecheck): accept generic-for over Array<T, n> with element-type check"
```

---

## Task 3: Type `M.keys` and `M.values` field accesses

**Files:**
- Modify: `proof_frog/semantic_analysis.py`:
  - `ComputeTypeVisitor.leave_field_access` (~line 2006): add a `MapType` branch that assigns `SetType(key_type)` or `SetType(value_type)`.
  - `CheckTypeVisitor.leave_field_access` (~line 641): add a `MapType` branch that only accepts `keys`, `values`, `entries` and errors otherwise, with a suggestion hint.
- Test: `tests/unit/typechecking/test_generic_for_map_array.py`

Reminder: currently, `FieldAccess(Variable("M"), "keys")` where `M : Map<K, V>` produces a type error because `MapType` is not an `InstantiableType`. We intercept before that branch.

- [x] **Step 1: Write the failing test**

Append to `tests/unit/typechecking/test_generic_for_map_array.py`:

```python
class TestMapKeysValues:
    def test_iterate_map_keys(self) -> None:
        _check_game("""
            Game G() {
                Map<Int, Bool> M;
                Int Count() {
                    Int n = 0;
                    for (Int k in M.keys) {
                        n = n + 1;
                    }
                    return n;
                }
            }
            """)

    def test_iterate_map_values(self) -> None:
        _check_game("""
            Game G() {
                Map<Int, Bool> M;
                Bool AnyTrue() {
                    for (Bool v in M.values) {
                        if (v) { return true; }
                    }
                    return false;
                }
            }
            """)

    def test_map_keys_wrong_element_type_fails(self) -> None:
        _check_game_fails("""
            Game G() {
                Map<Int, Bool> M;
                Void Initialize() {
                    for (Bool k in M.keys) {
                    }
                }
            }
            """)

    def test_map_unknown_field_fails(self) -> None:
        _check_game_fails("""
            Game G() {
                Map<Int, Bool> M;
                Void Initialize() {
                    for (Int k in M.keyz) {
                    }
                }
            }
            """)
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/typechecking/test_generic_for_map_array.py::TestMapKeysValues -v`
Expected: `test_iterate_map_keys` and `test_iterate_map_values` FAIL (field access on Map not recognized). The two `_fails` tests may pass for the wrong reason (error surfaces in field access rather than in the loop); we'll revisit in Step 5.

- [x] **Step 3: Add the MapType branch to `ComputeTypeVisitor.leave_field_access`**

In `proof_frog/semantic_analysis.py`, find `def leave_field_access(self, field_acess: frog_ast.FieldAccess) -> None:` at ~line 2006 (this is the `ComputeTypeVisitor` one that assigns types; it's the method that ends with `self.ast_type_map.set(field_acess, member)`). Insert the following block *before* the `if not isinstance(object_type, visitors.InstantiableType):` check:

```python
        if isinstance(object_type, frog_ast.MapType):
            if field_acess.name == "keys":
                self.ast_type_map.set(
                    field_acess, frog_ast.SetType(object_type.key_type)
                )
            elif field_acess.name == "values":
                self.ast_type_map.set(
                    field_acess, frog_ast.SetType(object_type.value_type)
                )
            elif field_acess.name == "entries":
                self.ast_type_map.set(
                    field_acess,
                    frog_ast.SetType(
                        frog_ast.ProductType(
                            [object_type.key_type, object_type.value_type]
                        )
                    ),
                )
            else:
                self.print_error(
                    field_acess,
                    f"Map has no field '{field_acess.name}'"
                    " (only 'keys', 'values', and 'entries' are available)",
                )
            return
```

- [x] **Step 4: Add the MapType branch to `CheckTypeVisitor.leave_field_access`**

In the same file, find the `leave_field_access` method near line 641 (the one in `CheckTypeVisitor`, which emits errors via `print_error`). This method currently has branches for `FunctionType` and `GroupType` before the `InstantiableType` check. Insert a Map branch after the `GroupType` branch (i.e., right before `if not isinstance(the_type, visitors.InstantiableType):`):

```python
        if isinstance(the_type, frog_ast.MapType):
            if field_access.name not in ("keys", "values", "entries"):
                suggestion = _suggestions.suggest_identifier(
                    field_access.name, ["keys", "values", "entries"]
                )
                hint = f"did you mean '{suggestion}'?" if suggestion else ""
                print_error(
                    field_access,
                    f"Map has no field '{field_access.name}'"
                    " (only 'keys', 'values', and 'entries' are available)",
                    self.file_name,
                    hint=hint,
                )
            return
```

Note: `_suggestions` is already imported in this file (used in the `InstantiableType` branch immediately below). If your editor flags it, confirm by grepping: the existing code at ~line 699 calls `_suggestions.suggest_identifier(...)`.

- [x] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/typechecking/test_generic_for_map_array.py::TestMapKeysValues -v`
Expected: all four tests PASS. `test_map_unknown_field_fails` now fails with the new "Map has no field 'keyz'" message (you can verify by temporarily changing the test to not use `_check_game_fails` and inspecting the error).

- [x] **Step 6: Run the full typechecking suite**

Run: `pytest tests/unit/typechecking/ -q`
Expected: all tests pass.

- [x] **Step 7: Commit**

```bash
git add proof_frog/semantic_analysis.py tests/unit/typechecking/test_generic_for_map_array.py
git commit -m "feat(typecheck): type Map.keys and Map.values as Set<K>/Set<V>"
```

---

## Task 4: Type `M.entries` and iterate via tuple destructuring

**Files:**
- Modify: `proof_frog/semantic_analysis.py` — the `MapType` branch added in Task 3 already handles `entries` by returning `SetType(ProductType([K, V]))`. What remains is to confirm that the loop-variable tuple type `[K, V]` compares equal to `ProductType([K, V])` during the element-type check added in Task 2.
- Test: `tests/unit/typechecking/test_generic_for_map_array.py`

Note: `frog_ast.ProductType.__eq__` (frog_ast.py:156) is already defined to compare equal to `frog_ast.Tuple` with matching element types, which is how `[K, V]` in a loop variable declaration surfaces after parsing. If `check_types` uses structural equality via `==`, this should work without additional code. If not, this task includes a fallback.

- [x] **Step 1: Write the failing test**

Append to `tests/unit/typechecking/test_generic_for_map_array.py`:

```python
class TestMapEntries:
    def test_iterate_map_entries(self) -> None:
        _check_game("""
            Game G() {
                Map<Int, Bool> M;
                Int CountTrue() {
                    Int n = 0;
                    for ([Int, Bool] e in M.entries) {
                        if (e[1]) { n = n + 1; }
                    }
                    return n;
                }
            }
            """)

    def test_map_entries_wrong_tuple_shape_fails(self) -> None:
        _check_game_fails("""
            Game G() {
                Map<Int, Bool> M;
                Void Initialize() {
                    for ([Bool, Int] e in M.entries) {
                    }
                }
            }
            """)
```

- [x] **Step 2: Run tests**

Run: `pytest tests/unit/typechecking/test_generic_for_map_array.py::TestMapEntries -v`
Expected: either both tests already PASS (nothing more to do — skip to Step 5) or `test_iterate_map_entries` FAILS with a "Loop variable has type [Int, Bool], but iteration yields elements of type [Int, Bool]"-style mismatch caused by `check_types` not normalizing `Tuple` vs `ProductType`.

- [x] **Step 3 (only if Step 2's positive test failed): patch `check_types`**

If the positive test failed, inspect `CheckTypeVisitor.check_types` (grep for `def check_types` in `proof_frog/semantic_analysis.py`). Add normalization so that a declared loop variable `Tuple([K, V])` compares equal to `ProductType([K, V])`. Concretely, locate the method and add, before the final `return` comparing the two types:

```python
        if isinstance(expected, frog_ast.Tuple) and isinstance(
            actual, frog_ast.ProductType
        ):
            expected = frog_ast.ProductType(list(expected.values))
        if isinstance(expected, frog_ast.ProductType) and isinstance(
            actual, frog_ast.Tuple
        ):
            actual = frog_ast.ProductType(list(actual.values))
```

(Adjust to the existing method's control flow; the intent is purely to normalize `Tuple` ↔ `ProductType` for the element-type check.)

- [x] **Step 4 (only if Step 3 was needed): rerun tests**

Run: `pytest tests/unit/typechecking/test_generic_for_map_array.py::TestMapEntries -v`
Expected: both tests PASS.

- [x] **Step 5: Run the full typechecking suite**

Run: `pytest tests/unit/typechecking/ -q`
Expected: all tests pass.

- [x] **Step 6: Commit**

```bash
git add proof_frog/semantic_analysis.py tests/unit/typechecking/test_generic_for_map_array.py
git commit -m "feat(typecheck): type Map.entries as Set<[K, V]> and allow tuple destructuring"
```

---

## Task 5: Negative tests for `leave_generic_for` rejections

**Files:**
- Test: `tests/unit/typechecking/test_generic_for_map_array.py`

Covers cases already handled by code changes so far, but worth pinning down as regressions.

- [x] **Step 1: Append negative tests**

```python
class TestRejections:
    def test_iterate_over_int_fails(self) -> None:
        _check_game_fails("""
            Game G() {
                Void Initialize() {
                    Int n = 5;
                    for (Int x in n) {
                    }
                }
            }
            """)

    def test_iterate_raw_map_fails(self) -> None:
        _check_game_fails("""
            Game G() {
                Map<Int, Bool> M;
                Void Initialize() {
                    for (Int k in M) {
                    }
                }
            }
            """)

    def test_iterate_map_entries_with_scalar_var_fails(self) -> None:
        _check_game_fails("""
            Game G() {
                Map<Int, Bool> M;
                Void Initialize() {
                    for (Int k in M.entries) {
                    }
                }
            }
            """)
```

- [x] **Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/typechecking/test_generic_for_map_array.py::TestRejections -v`
Expected: all three tests PASS (they assert `_check_game_fails`, and the code changes in Tasks 2–4 ensure each case is rejected).

- [x] **Step 3: Commit**

```bash
git add tests/unit/typechecking/test_generic_for_map_array.py
git commit -m "test: pin down rejection of ill-typed generic-for expressions"
```

---

## Task 6: Integration smoke test on a realistic game fragment

**Files:**
- Test: `tests/unit/typechecking/test_generic_for_map_array.py`

Asserts that a Decaps-style fragment from the case study typechecks end-to-end. This is a single integration test — cheap insurance that the four shapes compose.

- [x] **Step 1: Write the integration test**

```python
class TestIntegration:
    def test_decaps_iter_fragment(self) -> None:
        _check_game("""
            Game G() {
                Map<Int, Bool> HashTable;
                Bool Lookup(Int query) {
                    for ([Int, Bool] entry in HashTable.entries) {
                        if (entry[0] == query) {
                            return entry[1];
                        }
                    }
                    return false;
                }
            }
            """)
```

- [x] **Step 2: Run**

Run: `pytest tests/unit/typechecking/test_generic_for_map_array.py::TestIntegration -v`
Expected: PASS.

- [x] **Step 3: Commit**

```bash
git add tests/unit/typechecking/test_generic_for_map_array.py
git commit -m "test: integration smoke for Map.entries scan shape"
```

---

## Task 7: Lint, type-check, and format

**Files:**
- Any touched files.

- [x] **Step 1: Run the full lint pipeline**

Run: `cd /Users/dstebila/Dev/ProofFrog/ProofFrog && make lint`
Expected: all three of `black --check`, `mypy`, `pylint` pass. If `black --check` fails, run `make format` and re-run `make lint`. If `mypy` or `pylint` fail, fix the specific complaint — do not silence with blanket ignores. Common patterns: the `MapType` field-access branch may need `# type: ignore` if mypy cannot narrow `object_type.key_type`; prefer restructuring to avoid.

- [x] **Step 2: Run the full test suite**

Run: `pytest -q`
Expected: all tests pass.

- [x] **Step 3: Commit any formatting fixes (if any)**

```bash
git add -u
git commit -m "chore: apply black formatting"
```

Skip if the working tree is clean.

---

## Task 8: Self-review checklist

- [x] **Step 1: Spec coverage audit**

Re-read §5.1 of the design spec. Confirm each of the four iteration shapes is exercised by at least one positive test:
- `for (T x in A)` where `A : Array<T, n>` — Task 2 `test_iterate_array_of_int`.
- `for (K k in M.keys)` — Task 3 `test_iterate_map_keys`.
- `for (V v in M.values)` — Task 3 `test_iterate_map_values`.
- `for ([K, V] e in M.entries)` — Task 4 `test_iterate_map_entries` and Task 6 `test_decaps_iter_fragment`.

Confirm `Map` / `Array` field-access error messages surface with a hint for typos (exercised by `test_map_unknown_field_fails`).

- [x] **Step 2: Non-goals check**

Confirm nothing in this plan added:
- A new `TransformPass` (§5.2 belongs to the next plan).
- `NearMiss` instrumentation (no transforms added, so nothing to instrument).
- An entry in `proof_frog/diagnostics.py` (no engine limitation to register yet).
- Changes to `.g4` grammar files (not needed; grammar already accepts the syntax).

If any of those crept in, remove them — they belong in the next sub-plan.

- [x] **Step 3: Architectural notes for the next plan**

Append a short note (2–4 sentences) to `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md` under §7 or to a new `docs/superpowers/notes/` file if preferred, recording: the AST shape `.entries` produces (`SetType(ProductType([K, V]))`), the fact that `Tuple` vs `ProductType` normalization was / was not needed (per Task 4 outcome), and any surprises. The next plan (LazyMapScan) will consume this.

Skip if the user does not want intermediate notes — optional.

---

## Success criteria for this plan

When all tasks above are complete:

- The four iteration shapes in §5.1 of the spec typecheck without error.
- Loop variable types are cross-checked against container element types.
- Map field-access errors surface with suggestion hints.
- `make lint` and `pytest -q` both pass.
- No engine transforms or grammar changes introduced.

The next plan in the series (`LazyMapScan` + lazy-RF-as-Map, sub-project 2) can assume these AST shapes are well-typed and begin its work on canonicalization.

---

## Implementation notes (for the next plan)

- **AST shape of `M.entries`**: `ComputeTypeVisitor.leave_field_access` sets the type of `FieldAccess(M, "entries")` to `SetType(ProductType([K, V]))` when `M : MapType(K, V)`. Downstream passes iterating over `generic_for.over` where that expression is an `M.entries` `FieldAccess` can rely on this without re-checking.
- **Tuple vs ProductType normalization**: NOT needed. `frog_ast.ProductType.__eq__` (`proof_frog/frog_ast.py:156`) already compares equal to `frog_ast.Tuple` with matching element types, and `Tuple.__eq__` mirrors this (`frog_ast.py:420-424`). A declared loop variable `[K, V]` (parsed as `Tuple`) and the container's element type `ProductType([K, V])` compare equal via `check_types` → `compare_types` → `==`.
- **`leave_generic_for` behavior tightening**: previously only emitted an error when `over` was not a `SetType`. Now *also* cross-checks the loop variable's declared type against the container's element type (whether `SetType.parameterization` or `ArrayType.element_type`). Any prior test/proof relying on a loose loop-variable type would now fail — none did in the current test corpus.
- **Error-message surface**: `"Must iterate over Set, Array, Map.keys, Map.values, or Map.entries; got type <T>"` and `"Loop variable has type <V>, but iteration yields elements of type <E>"`. Map-unknown-field errors surface from both visitors; `CheckTypeVisitor` supplies the suggestion hint via `_suggestions.suggest_identifier`.
- **No `NearMiss` or diagnostics registry entry** added: this plan added zero `TransformPass` subclasses, so there is nothing to instrument.
