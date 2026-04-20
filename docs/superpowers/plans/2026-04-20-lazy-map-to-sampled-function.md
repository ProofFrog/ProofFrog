# Lazy-Map-to-Sampled-Function Canonicalization: Implementation Plan

> **Status (2026-04-20): Implemented.** `LazyMapToSampledFunction` landed in
> `proof_frog/transforms/random_functions.py` and is registered in
> `CORE_PIPELINE` immediately before `ExtractRFCalls`. All 1728 tests pass;
> `make lint` clean (black, mypy, pylint 10/10, tsc).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `TransformPass` that recognizes a `Map<K, V>` field used exclusively as a lazy lookup table (the "if-in-return-else-sample-store-return" idiom) and rewrites it to a sampled `Function<K, V>` field, so downstream RF passes (`LocalRFToUniform`, `FreshInputRFToUniform`, `UniqueRFSimplification`, etc.) can continue the canonicalization.

**Architecture:** Single new pass `LazyMapToSampledFunction` in `proof_frog/transforms/random_functions.py`. Game-level scan: for each `Map<K, V>` field `M`, collect every syntactic reference to `M` and verify each lies inside a recognized idiom suffix of some method body. If every reference is accounted for and there is at least one idiom occurrence, rewrite: (1) change the field type from `Map<K, V>` to `Function<K, V>`; (2) prepend `M <- Function<K, V>;` to `Initialize` (creating `Initialize` if absent); (3) replace each idiom suffix with `return M(x);`. Near-miss instrumentation covers the three soundness preconditions S3(a)–(c) from the design spec.

**Tech Stack:** Python 3.11+, ANTLR-parsed AST (`proof_frog/frog_ast.py`), existing `TransformPass` / `PipelineContext` framework (`proof_frog/transforms/_base.py`), pytest.

**Out of scope for this plan:**
- `LazyMapScan` shape recognition (§5.2 of the design) — the scan-over-`M.entries` canonicalization. Handled in the next sub-plan on top of this one.
- Oracle-patching canonicalization (§5.4).
- Pipeline-order tuning beyond placing this pass immediately before `ExtractRFCalls`.

---

## File Structure

**Modify:**
- `proof_frog/transforms/random_functions.py` — add `LazyMapToSampledFunction` pass and its helpers.
- `proof_frog/transforms/pipelines.py` — register the new pass in `CORE_PIPELINE`.
- `proof_frog/diagnostics.py` — no change (this pass adds no engine-limitation registry entry: it succeeds or emits structured near-misses, which surface via the existing near-miss plumbing).

**Create:**
- `tests/unit/transforms/test_lazy_map_to_sampled_function.py` — positive/negative unit tests.
- Extend `tests/unit/transforms/test_near_misses.py` — one near-miss assertion per S3 precondition.

No grammar, AST, parser, or semantic-analysis changes.

---

## Preliminaries

- [x] **Step 0a: Confirm clean working tree and baseline tests pass**

Run: `cd /Users/dstebila/Dev/ProofFrog/ProofFrog && git status && pytest tests/unit/transforms/ -q`
Expected: working tree matches branch `feat/genericfor-map-array-typing` (typechecking plan already landed), and all transform unit tests pass.

- [x] **Step 0b: Read the design spec §5.3 and soundness §S3**

Read `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md` lines 142–150 (§5.3) and the S3 block (~198–207). Read `extras/docs/transforms/SEMANTICS.md` §6.5 (Random Functions) and §6.7 (Map Semantics). Confirm: a freshly sampled `Function<D, R>` is *definitionally* a lazily-populated lookup table, so the rewrite is tight — no near-equivalence, no security loss.

---

## Task 1: Create the test file scaffold

**Files:**
- Create: `tests/unit/transforms/test_lazy_map_to_sampled_function.py`

- [x] **Step 1: Create the test file with shared helpers**

Exact content:

```python
"""Tests for the LazyMapToSampledFunction transform pass."""

from proof_frog import frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.random_functions import LazyMapToSampledFunction
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(game_src: str):
    game = frog_parser.parse_game(game_src)
    return LazyMapToSampledFunction().apply(game, _ctx())


def _apply_and_expect(game_src: str, expected_src: str) -> None:
    got = _apply(game_src)
    expected = frog_parser.parse_game(expected_src)
    assert got == expected, f"\nGOT:\n{got}\n\nEXPECTED:\n{expected}"


def _apply_and_expect_unchanged(game_src: str) -> None:
    original = frog_parser.parse_game(game_src)
    got = LazyMapToSampledFunction().apply(original, _ctx())
    assert got == original, f"\nGOT:\n{got}\n\nEXPECTED UNCHANGED:\n{original}"
```

- [x] **Step 2: Run pytest on the new file to confirm it loads**

Run: `pytest tests/unit/transforms/test_lazy_map_to_sampled_function.py -q`
Expected: `no tests ran` (or "1 passed" if pytest treats `_ctx` as a test — it should not, since name starts with `_`).

- [x] **Step 3: Commit**

```bash
git add tests/unit/transforms/test_lazy_map_to_sampled_function.py
git commit -m "test: scaffold LazyMapToSampledFunction tests"
```

---

## Task 2: Recognize the idiom and emit the minimal positive rewrite

**Files:**
- Modify: `proof_frog/transforms/random_functions.py` (add new pass at the end of the file)
- Test: `tests/unit/transforms/test_lazy_map_to_sampled_function.py`

This task handles the *simplest* shape: a game with one `Map<K, V>` field used by exactly one method whose body is exactly `if (x in M) { return M[x]; } V s <- V; M[x] = s; return s;`. Later tasks generalize.

### The idiom suffix (canonical form)

Given a method body, the **idiom suffix** is the last four statements:

1. `IfStatement` with condition `BinaryOperation(IN, Variable(x), Variable(M))`, exactly one block, whose body is exactly `[ReturnStatement(ArrayAccess(Variable(M), Variable(x)))]`, and no else/else-if.
2. `Sample` with `var = Variable(s)`, `sampled_from` equal to the map's value type (compared by `==`), and either `the_type is not None` or a preceding `VariableDeclaration` for `s` of the same type.
3. `Assignment` with `var = ArrayAccess(Variable(M), Variable(x))` and `value = Variable(s)`.
4. `ReturnStatement(Variable(s))`.

The variable name `x` must match across (1a), (1b), (3-var), and the key in (1a). The variable name `s` must match across (2), (3-value), and (4). The map name `M` must match across (1a), (1b), and (3-var).

`x` must be a formal parameter or a variable assigned earlier in the same method body (not another method-local that depends on `M`). For the MVP we require `x` to be a method parameter — simplest and covers `Hash`-like oracles.

- [x] **Step 1: Write the failing positive test**

Append to `tests/unit/transforms/test_lazy_map_to_sampled_function.py`:

```python
def test_basic_hash_idiom() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> T;
            Void Initialize() {
                T <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) {
                return T(x);
            }
        }
        """,
    )
```

- [x] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/transforms/test_lazy_map_to_sampled_function.py::test_basic_hash_idiom -v`
Expected: FAIL with `ImportError: cannot import name 'LazyMapToSampledFunction' from 'proof_frog.transforms.random_functions'`.

- [x] **Step 3: Add helper functions and the pass to `random_functions.py`**

Append to `proof_frog/transforms/random_functions.py` (imports already include `copy`, `frog_ast`, `TransformPass`, `PipelineContext`, `NearMiss`):

```python
# ---------------------------------------------------------------------------
# Lazy map -> sampled Function canonicalization (design §5.3)
# ---------------------------------------------------------------------------


def _is_idiom_if(
    stmt: frog_ast.ASTNode, map_name: str, key_name: str
) -> bool:
    """Return True if *stmt* is ``if (key_name in map_name) return map_name[key_name];``
    with exactly one block, no else/else-if, and body of exactly one
    ReturnStatement returning ``map_name[key_name]``.
    """
    if not isinstance(stmt, frog_ast.IfStatement):
        return False
    if len(stmt.conditions) != 1 or len(stmt.blocks) != 1:
        return False
    cond = stmt.conditions[0]
    if not (
        isinstance(cond, frog_ast.BinaryOperation)
        and cond.operator == frog_ast.BinaryOperators.IN
        and isinstance(cond.left_expression, frog_ast.Variable)
        and cond.left_expression.name == key_name
        and isinstance(cond.right_expression, frog_ast.Variable)
        and cond.right_expression.name == map_name
    ):
        return False
    body = stmt.blocks[0].statements
    if len(body) != 1 or not isinstance(body[0], frog_ast.ReturnStatement):
        return False
    ret = body[0].expression
    return (
        isinstance(ret, frog_ast.ArrayAccess)
        and isinstance(ret.the_array, frog_ast.Variable)
        and ret.the_array.name == map_name
        and isinstance(ret.index, frog_ast.Variable)
        and ret.index.name == key_name
    )


def _match_idiom_suffix(
    method: frog_ast.Method,
    map_name: str,
    value_type: frog_ast.Type,
) -> tuple[int, str, str] | None:
    """Match the 4-statement idiom suffix of *method*'s body.

    Returns ``(start_idx, key_name, sample_var_name)`` on success, None otherwise.
    ``start_idx`` is the index of the leading ``if`` in the method block.
    """
    stmts = method.block.statements
    if len(stmts) < 4:
        return None
    if_idx = len(stmts) - 4
    if_stmt, sample_stmt, assign_stmt, ret_stmt = stmts[if_idx:]

    # Statement 2: Sample s <- value_type (with matching type)
    if not (
        isinstance(sample_stmt, frog_ast.Sample)
        and isinstance(sample_stmt.var, frog_ast.Variable)
        and sample_stmt.the_type is not None
        and sample_stmt.the_type == value_type
        and sample_stmt.sampled_from == value_type
    ):
        return None
    sample_var = sample_stmt.var.name

    # Statement 3: M[key] = s
    if not (
        isinstance(assign_stmt, frog_ast.Assignment)
        and isinstance(assign_stmt.var, frog_ast.ArrayAccess)
        and isinstance(assign_stmt.var.the_array, frog_ast.Variable)
        and assign_stmt.var.the_array.name == map_name
        and isinstance(assign_stmt.var.index, frog_ast.Variable)
        and isinstance(assign_stmt.value, frog_ast.Variable)
        and assign_stmt.value.name == sample_var
    ):
        return None
    key_name = assign_stmt.var.index.name

    # Statement 4: return s;
    if not (
        isinstance(ret_stmt, frog_ast.ReturnStatement)
        and isinstance(ret_stmt.expression, frog_ast.Variable)
        and ret_stmt.expression.name == sample_var
    ):
        return None

    # Statement 1: if (key in M) return M[key];
    if not _is_idiom_if(if_stmt, map_name, key_name):
        return None

    # key_name must be a formal parameter of this method
    param_names = {p.name for p in method.signature.parameters}
    if key_name not in param_names:
        return None

    return if_idx, key_name, sample_var


def _references_map(node: frog_ast.ASTNode, map_name: str) -> bool:
    """Return True if *node* syntactically references Variable(map_name)."""
    from ..visitors import SearchVisitor  # pylint: disable=import-outside-toplevel

    def matcher(n: frog_ast.ASTNode) -> bool:
        return isinstance(n, frog_ast.Variable) and n.name == map_name

    return SearchVisitor(matcher).visit(node) is not None


class LazyMapToSampledFunction(TransformPass):
    """Rewrite a Map field used exclusively as a lazy lookup table into a
    sampled Function field.

    Preconditions (see design spec §S3):
    - (a) Every reference to the Map field in the game body lies inside the
      recognized idiom suffix of some method.
    - (b) The Map field is not explicitly initialized in ``Initialize``
      (Maps default to empty per SEMANTICS.md §6.7).
    - (c) No method uses ``|M|``, ``M.keys``, ``M.values``, or ``M.entries``
      (follows from (a), since those references are not part of the idiom).

    On success, the pass:
    1. Changes the field type from ``Map<K, V>`` to ``Function<K, V>``.
    2. Prepends ``M <- Function<K, V>;`` to ``Initialize`` (creating an
       ``Initialize`` method if none exists).
    3. Replaces each idiom suffix with ``return M(key);``.
    """

    name = "Lazy Map To Sampled Function"

    def apply(
        self, game: frog_ast.Game, ctx: PipelineContext
    ) -> frog_ast.Game:
        for field in game.fields:
            if not isinstance(field.type, frog_ast.MapType):
                continue
            rewritten = self._try_rewrite(game, field, ctx)
            if rewritten is not None:
                return rewritten
        return game

    def _try_rewrite(
        self,
        game: frog_ast.Game,
        field: frog_ast.Field,
        ctx: PipelineContext,
    ) -> frog_ast.Game | None:
        map_name = field.name
        assert isinstance(field.type, frog_ast.MapType)
        key_type = field.type.key_type
        value_type = field.type.value_type

        # Precondition (b): no explicit Initialize assignment to M.
        for method in game.methods:
            if method.signature.name != "Initialize":
                continue
            for stmt in method.block.statements:
                if isinstance(stmt, (frog_ast.Assignment, frog_ast.Sample)):
                    v = stmt.var
                    if isinstance(v, frog_ast.Variable) and v.name == map_name:
                        return None

        # For each method, find the idiom suffix (if any) and verify no
        # references to M outside it.
        method_rewrites: list[tuple[int, int, str]] = []  # (method_idx, if_idx, key_name)
        found_any = False
        for m_idx, method in enumerate(game.methods):
            if method.signature.name == "Initialize":
                # Initialize is checked above; must not reference M.
                for stmt in method.block.statements:
                    if _references_map(stmt, map_name):
                        return None
                continue
            match = _match_idiom_suffix(method, map_name, value_type)
            if match is None:
                # Method must not reference M at all.
                for stmt in method.block.statements:
                    if _references_map(stmt, map_name):
                        return None
                continue
            if_idx, key_name, _sample_var = match
            # Prefix statements must not reference M.
            for stmt in method.block.statements[:if_idx]:
                if _references_map(stmt, map_name):
                    return None
            method_rewrites.append((m_idx, if_idx, key_name))
            found_any = True

        if not found_any:
            return None

        # Build the rewritten game.
        new_game = copy.deepcopy(game)
        # (1) Change field type.
        for f in new_game.fields:
            if f.name == map_name:
                f.type = frog_ast.FunctionType(key_type, value_type)
                break
        # (2) Prepend sample to Initialize (create if missing).
        sample_stmt = frog_ast.Sample(
            None,  # the_type=None since field already declared
            frog_ast.Variable(map_name),
            frog_ast.FunctionType(
                copy.deepcopy(key_type), copy.deepcopy(value_type)
            ),
        )
        init_method = None
        for m in new_game.methods:
            if m.signature.name == "Initialize":
                init_method = m
                break
        if init_method is None:
            init_sig = frog_ast.MethodSignature(
                "Initialize", frog_ast.VoidType(), []
            )
            init_method = frog_ast.Method(init_sig, frog_ast.Block([sample_stmt]))
            new_game.methods = [init_method] + list(new_game.methods)
        else:
            init_method.block = frog_ast.Block(
                [sample_stmt] + list(init_method.block.statements)
            )
        # (3) Rewrite each idiom suffix to `return M(key);`.
        for m_idx, if_idx, key_name in method_rewrites:
            # Locate the same method in new_game (accounting for a prepended
            # Initialize, if we just created one).
            target = None
            for m in new_game.methods:
                if (
                    m.signature.name == game.methods[m_idx].signature.name
                    and m.signature.name != "Initialize"
                ):
                    target = m
                    break
            assert target is not None
            new_return = frog_ast.ReturnStatement(
                frog_ast.FuncCall(
                    frog_ast.Variable(map_name),
                    [frog_ast.Variable(key_name)],
                )
            )
            target.block = frog_ast.Block(
                list(target.block.statements[:if_idx]) + [new_return]
            )
        _ = ctx  # near-miss handling is added in Task 5
        return new_game
```

Double-check the AST constructor names against `proof_frog/frog_ast.py` before committing: `MethodSignature`, `Method`, `Block`, `Sample`, `Assignment`, `ReturnStatement`, `FuncCall`, `Variable`, `ArrayAccess`, `BinaryOperation`, `IfStatement`, `Field`, `VoidType`, `FunctionType`, `MapType`. If any name differs, use the matching one (e.g., `Field` may be `VariableDeclaration`-like — grep `class Field` / `game.fields` to confirm).

Also confirm: `frog_ast.MethodSignature` parameter order and `frog_ast.Method` constructor signature. If the engine's existing code uses a different constructor shape (e.g., `game.fields` entries are `frog_ast.Field(name, type)` vs. `frog_ast.VariableDeclaration(type, name)`), mirror the existing shape. Grep `game.fields` in `proof_frog/transforms/` for examples.

- [x] **Step 4: Run the positive test**

Run: `pytest tests/unit/transforms/test_lazy_map_to_sampled_function.py::test_basic_hash_idiom -v`
Expected: PASS. If it fails because the emitted AST doesn't equal the expected AST, print both and compare — almost always it's a field construction mismatch (e.g., `Field` constructor argument order). Do NOT add `__eq__` overrides or normalize the expected string; fix the transform to produce the exact AST that `parse_game` produces from the expected source.

- [x] **Step 5: Run the full transforms test suite**

Run: `pytest tests/unit/transforms/ -q`
Expected: all tests pass. No regressions possible since the new pass is not yet wired into `CORE_PIPELINE`.

- [x] **Step 6: Commit**

```bash
git add proof_frog/transforms/random_functions.py tests/unit/transforms/test_lazy_map_to_sampled_function.py
git commit -m "feat(transforms): add LazyMapToSampledFunction pass (positive shape)"
```

---

## Task 3: Negative tests — idiom variations that must NOT fire

**Files:**
- Test: `tests/unit/transforms/test_lazy_map_to_sampled_function.py`

Lock in the precondition behavior. No source code changes expected — these tests should already pass given Task 2's tight matching.

- [x] **Step 1: Append negative tests**

```python
def test_extra_map_read_outside_idiom_fails() -> None:
    # M is read in a second method outside the idiom.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
            Int Count(BitString<8> x) {
                if (x in T) {
                    return 1;
                }
                return 0;
            }
        }
        """
    )


def test_map_cardinality_use_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Int Size() {
                return |T|;
            }
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )


def test_initialize_touches_map_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Void Initialize() {
                T[0b00000000] = 0b0000000000000000;
            }
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )


def test_idiom_with_prefix_statements_fails() -> None:
    # Prefix statement references the map (disallowed).
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                Int n = |T|;
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )


def test_wrong_shape_fails() -> None:
    # Fresh sample but no store back into T.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                return s;
            }
        }
        """
    )


def test_no_idiom_at_all_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Int Size() {
                return |T|;
            }
        }
        """
    )
```

- [x] **Step 2: Run**

Run: `pytest tests/unit/transforms/test_lazy_map_to_sampled_function.py -v`
Expected: all new tests PASS plus `test_basic_hash_idiom` still PASSES.

If a negative test fails because the transform fired anyway, tighten the corresponding check in `_try_rewrite`. Do NOT loosen the test — the design spec S3 requires these preconditions hold.

- [x] **Step 3: Commit**

```bash
git add tests/unit/transforms/test_lazy_map_to_sampled_function.py
git commit -m "test: negative cases for LazyMapToSampledFunction preconditions"
```

---

## Task 4: Generalize — multi-method idiom, method without Initialize, prefix stmts not touching M

**Files:**
- Modify: `proof_frog/transforms/random_functions.py`
- Test: `tests/unit/transforms/test_lazy_map_to_sampled_function.py`

Task 2 already supports these cases conceptually (the implementation scans each method). This task pins them down with tests and fixes any gap.

- [x] **Step 1: Write positive tests for generalized shapes**

Append:

```python
def test_multiple_methods_all_idiom() -> None:
    # Two oracles, both use the same map via the idiom — both rewrite.
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> HashA(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
            BitString<16> HashB(BitString<8> y) {
                if (y in T) {
                    return T[y];
                }
                BitString<16> s <- BitString<16>;
                T[y] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> T;
            Void Initialize() {
                T <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> HashA(BitString<8> x) {
                return T(x);
            }
            BitString<16> HashB(BitString<8> y) {
                return T(y);
            }
        }
        """,
    )


def test_idiom_with_prefix_not_touching_map() -> None:
    # Prefix statement unrelated to M is allowed and preserved.
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x, Int i) {
                Int j = i + 1;
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> T;
            Void Initialize() {
                T <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x, Int i) {
                Int j = i + 1;
                return T(x);
            }
        }
        """,
    )


def test_initialize_present_no_map_refs_ok() -> None:
    # Initialize exists but doesn't touch M — sample is prepended.
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Int counter;
            Void Initialize() {
                counter = 0;
            }
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> T;
            Int counter;
            Void Initialize() {
                T <- Function<BitString<8>, BitString<16>>;
                counter = 0;
            }
            BitString<16> Hash(BitString<8> x) {
                return T(x);
            }
        }
        """,
    )
```

- [x] **Step 2: Run**

Run: `pytest tests/unit/transforms/test_lazy_map_to_sampled_function.py -v`
Expected: all new tests PASS. If `test_initialize_present_no_map_refs_ok` fails, the issue is likely the Initialize-present branch of `_try_rewrite`. Fix the prepend logic so it mutates `init_method.block` rather than replacing it. If `test_multiple_methods_all_idiom` fails, check that the method-lookup in the rewrite phase doesn't short-circuit on the first match.

- [x] **Step 3: Run full transforms suite**

Run: `pytest tests/unit/transforms/ -q`
Expected: all pass.

- [x] **Step 4: Commit**

```bash
git add proof_frog/transforms/random_functions.py tests/unit/transforms/test_lazy_map_to_sampled_function.py
git commit -m "feat(transforms): handle multi-method and Initialize-present cases"
```

---

## Task 5: Near-miss instrumentation for S3 preconditions

**Files:**
- Modify: `proof_frog/transforms/random_functions.py` — emit `NearMiss` entries in `_try_rewrite` when a precondition fails in a way the user likely meant to hit.
- Test: extend `tests/unit/transforms/test_near_misses.py`

Per CLAUDE.md: new `TransformPass` subclasses add a `NearMiss` entry at each precondition-failure site. We emit near-misses only when we saw at least one idiom suffix (i.e., the user clearly intended the rewrite) but a disqualifying use blocked it. Games with no idiom at all are silent.

- [x] **Step 1: Add near-miss emission to `_try_rewrite`**

Modify `_try_rewrite` so that, before any `return None` triggered by (b) or (c), we first record what shape we would have matched. Concretely, compute `would_match = any(_match_idiom_suffix(m, map_name, value_type) for m in game.methods)` at the top. When a disqualifying use is found *and* `would_match` is true, append to `ctx.near_misses` and return None. Use distinct reasons:

- Initialize explicit assignment to M → reason `f"Map '{map_name}' is explicitly initialized in Initialize; lazy-map canonicalization requires an empty initial map"`, method=`"Initialize"`, variable=`map_name`.
- Non-idiom method reference → reason `f"Map '{map_name}' is referenced in method '{offending_method}' outside the lazy-lookup idiom"`, method=`offending_method`, variable=`map_name`.
- Prefix statement references M → same reason but with the specific method name.

Every `NearMiss` uses `transform_name="Lazy Map To Sampled Function"`. Include a `suggestion` when a concrete fix is obvious, e.g., for the `|T|` case: `"Remove the |T| reference, or use an explicit Function<K, V> field instead of lazy lookup"`; otherwise `None`.

Sketch of the change — replace the early `return None` on precondition (b) with:

```python
        for method in game.methods:
            if method.signature.name != "Initialize":
                continue
            for stmt in method.block.statements:
                if isinstance(stmt, (frog_ast.Assignment, frog_ast.Sample)):
                    v = stmt.var
                    if isinstance(v, frog_ast.Variable) and v.name == map_name:
                        if any(
                            _match_idiom_suffix(m, map_name, value_type) is not None
                            for m in game.methods
                        ):
                            ctx.near_misses.append(
                                NearMiss(
                                    transform_name="Lazy Map To Sampled Function",
                                    reason=(
                                        f"Map '{map_name}' is explicitly "
                                        "initialized in Initialize; "
                                        "lazy-map canonicalization requires "
                                        "an empty initial map"
                                    ),
                                    location=stmt.origin,
                                    suggestion=None,
                                    variable=map_name,
                                    method="Initialize",
                                )
                            )
                        return None
```

Apply the analogous wrapping around the two `_references_map` branches (Initialize with M refs, non-idiom method with M refs, idiom method with prefix M ref). Do not emit a near-miss when a method matches the idiom cleanly — only when a precondition blocks an otherwise-plausible rewrite.

- [x] **Step 2: Run the positive tests (no behavior change)**

Run: `pytest tests/unit/transforms/test_lazy_map_to_sampled_function.py -v`
Expected: all tests still PASS.

- [x] **Step 3: Add near-miss tests in `tests/unit/transforms/test_near_misses.py`**

Append to `tests/unit/transforms/test_near_misses.py`:

```python
from proof_frog.transforms.random_functions import LazyMapToSampledFunction


def _lazy_map_ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def test_lazy_map_near_miss_cardinality_use() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Int Size() {
                return |T|;
            }
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )
    ctx = _lazy_map_ctx()
    result = LazyMapToSampledFunction().apply(game, ctx)
    assert result == game
    assert any(
        nm.transform_name == "Lazy Map To Sampled Function"
        and nm.method == "Size"
        and nm.variable == "T"
        for nm in ctx.near_misses
    )


def test_lazy_map_near_miss_explicit_initialize() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Void Initialize() {
                T[0b00000000] = 0b0000000000000000;
            }
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )
    ctx = _lazy_map_ctx()
    LazyMapToSampledFunction().apply(game, ctx)
    assert any(
        nm.transform_name == "Lazy Map To Sampled Function"
        and nm.method == "Initialize"
        and nm.variable == "T"
        for nm in ctx.near_misses
    )


def test_lazy_map_no_near_miss_when_no_idiom() -> None:
    # Game with a Map but no idiom anywhere: silent, no near-miss noise.
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Int Size() {
                return |T|;
            }
        }
        """
    )
    ctx = _lazy_map_ctx()
    LazyMapToSampledFunction().apply(game, ctx)
    assert not any(
        nm.transform_name == "Lazy Map To Sampled Function"
        for nm in ctx.near_misses
    )
```

- [x] **Step 4: Run near-miss tests**

Run: `pytest tests/unit/transforms/test_near_misses.py -v`
Expected: all tests pass (including new ones).

- [x] **Step 5: Commit**

```bash
git add proof_frog/transforms/random_functions.py tests/unit/transforms/test_near_misses.py
git commit -m "feat(transforms): near-miss instrumentation for LazyMapToSampledFunction"
```

---

## Task 6: Wire into CORE_PIPELINE and add integration test

**Files:**
- Modify: `proof_frog/transforms/pipelines.py`
- Test: `tests/unit/transforms/test_lazy_map_to_sampled_function.py`

- [x] **Step 1: Import and register**

In `proof_frog/transforms/pipelines.py`, add `LazyMapToSampledFunction` to the import from `.random_functions`:

```python
from .random_functions import (
    ExtractRFCalls,
    UniqueRFSimplification,
    ChallengeExclusionRFToUniform,
    LocalRFToUniform,
    DistinctConstRFToUniform,
    FreshInputRFToUniform,
    LazyMapToSampledFunction,
)
```

Add it to `CORE_PIPELINE` immediately *before* `ExtractRFCalls` (so the Map→Function rewrite happens before downstream RF passes scan for sampled Functions). In the list defined in that file:

```python
    LazyMapToSampledFunction(),
    ExtractRFCalls(),
```

- [x] **Step 2: Run full test suite**

Run: `pytest -q`
Expected: all tests pass. If any existing `examples/**/*.proof` tests fail, the rewrite fired unexpectedly on a proof that was previously using a Map in a way we now recognize as the lazy idiom. Most likely the rewrite is sound and the expected canonical form just shifted; inspect the failing proof and decide whether to (a) mark the transform as fired (if the test was asserting an exact canonical shape that's now stale) or (b) tighten the match. Do NOT silently disable the pass.

- [x] **Step 3: Integration test through the pipeline**

Append to `tests/unit/transforms/test_lazy_map_to_sampled_function.py`:

```python
def test_integration_via_core_pipeline() -> None:
    """With LazyMapToSampledFunction in the pipeline, a lazy Hash oracle
    canonicalizes such that downstream RF passes can further simplify."""
    from proof_frog.transforms._base import run_pipeline
    from proof_frog.transforms.pipelines import CORE_PIPELINE

    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )
    result = run_pipeline(game, CORE_PIPELINE, _ctx())
    # After LazyMapToSampledFunction, Hash's body is `return T(x);` with T
    # a sampled Function field. No further rewrite is guaranteed; we just
    # assert the field type changed and Hash's body collapsed to one stmt.
    t_field = next(f for f in result.fields if f.name == "T")
    assert isinstance(t_field.type, frog_ast.FunctionType)
    hash_method = next(
        m for m in result.methods if m.signature.name == "Hash"
    )
    assert len(hash_method.block.statements) == 1
```

Add the `frog_ast` import at the top of the test file if not already present:

```python
from proof_frog import frog_ast, frog_parser
```

- [x] **Step 4: Run the integration test**

Run: `pytest tests/unit/transforms/test_lazy_map_to_sampled_function.py::test_integration_via_core_pipeline -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add proof_frog/transforms/pipelines.py tests/unit/transforms/test_lazy_map_to_sampled_function.py
git commit -m "feat(transforms): wire LazyMapToSampledFunction into CORE_PIPELINE"
```

---

## Task 7: Lint, type-check, format

**Files:**
- Any touched files.

- [x] **Step 1: Run the full lint pipeline**

Run: `make lint`
Expected: `black --check`, `mypy`, `pylint` all pass.

Common fixes:
- `black --check` failure → run `make format` and re-run `make lint`.
- `mypy` complaints about `frog_ast.FunctionType(key_type, value_type)` — the types are already concrete `Type` instances from `field.type`, but if mypy narrows incorrectly, use `copy.deepcopy` with explicit `cast(frog_ast.Type, ...)` only if strictly necessary. Prefer restructuring over `# type: ignore`.
- `pylint` complaints about too-many-locals or too-many-branches in `_try_rewrite` — extract a helper (e.g., `_find_idiom_methods`) rather than disabling the check.

- [x] **Step 2: Run the full test suite**

Run: `pytest -q`
Expected: all tests pass.

- [x] **Step 3: Commit any formatting/lint-driven fixes**

```bash
git add -u
git commit -m "chore: apply black and lint fixes for LazyMapToSampledFunction"
```

Skip if the working tree is clean.

---

## Task 8: Self-review checklist

- [x] **Step 1: Spec coverage audit (§5.3 and §S3)**

Confirm each S3 precondition is covered:

- **S3(a)** "accessed exclusively through the lazy-sample idiom shape" — `test_extra_map_read_outside_idiom_fails`, `test_idiom_with_prefix_statements_fails`, `test_lazy_map_near_miss_cardinality_use`.
- **S3(b)** "initialized empty" — `test_initialize_touches_map_fails`, `test_lazy_map_near_miss_explicit_initialize`.
- **S3(c)** "not passed to cardinality/iteration" — `test_map_cardinality_use_fails`, `test_lazy_map_near_miss_cardinality_use`.

Confirm §5.3 soundness claim (equivalence to `Function<D, R> F <- Function<D, R>`) is the exact rewrite produced.

- [x] **Step 2: Non-goals check**

Confirm nothing in this plan added:
- A `LazyMapScan` transform (§5.2 belongs to the next sub-plan).
- Any oracle-patching logic (§5.4).
- An entry in `proof_frog/diagnostics.py` `_DETECTORS` (the near-miss path suffices for user diagnostics; no new diff-shape signature).
- Changes to grammar or AST node definitions.

If any crept in, remove them.

- [x] **Step 3: Architectural note for the next plan**

Append to `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md` (at the end of §7 or in a new "Implementation notes" section): a short (2–4 sentence) note recording that `LazyMapToSampledFunction` runs before `ExtractRFCalls` in `CORE_PIPELINE`, so the next plan's `LazyMapScan` (§5.2) must *not* rely on `Map<K, V>` still being present when the scan matches in other methods of the same game. The next plan either (a) runs before `LazyMapToSampledFunction` if it wants to see the Map, or (b) matches the canonical `Function<K, V>` form after this pass has fired. Record whichever design choice was made during implementation.

Skip if the user doesn't want intermediate notes — optional.

---

## Success criteria for this plan

When all tasks above are complete:

- A game using a `Map<K, V>` field exclusively via the `if (x in T) return T[x]; s <- V; T[x] = s; return s;` idiom canonicalizes to a game with a sampled `Function<K, V>` field and a one-line oracle `return T(x);`.
- Disqualifying uses (`|T|`, `.keys`/`.values`/`.entries`, explicit Initialize assignment, references outside the idiom) prevent the rewrite.
- When a disqualifying use blocks an otherwise-plausible rewrite, a `NearMiss` is emitted citing the specific S3 precondition.
- `make lint` and `pytest -q` both pass.
- The pass is registered in `CORE_PIPELINE` immediately before `ExtractRFCalls`.

The next sub-plan (`LazyMapScan` for §5.2) can assume sampled `Function<K, V>` is the canonical form for what used to be lazy-map lookup.
