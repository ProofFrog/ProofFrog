# LazyMapScan Transform: Implementation Plan

> **Status (2026-04-20): Implemented.** `LazyMapScan` landed in
> `proof_frog/transforms/map_iteration.py` and is registered in
> `CORE_PIPELINE` immediately before `LazyMapToSampledFunction`. All 1158
> unit tests pass; `make lint` clean (black, mypy, pylint 10/10, tsc). Not
> merged — branch `feat/genericfor-map-array-typing`.
>
> **Next step:** write the §4.1 (`DecapsIter` CCA) and §4.3 (Hashed ElGamal
> CCA) FrogLang artifacts and run them through `prove` end-to-end. This
> validates §5.1 + §5.2 + §5.3 as a set before taking on the harder §5.4
> oracle-patching plan. Any gap in the §5.2 rewrite surfaces here rather
> than compounding under §5.4.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `TransformPass` `LazyMapScan` that recognizes the loop shape `for ([K, V] e in M.entries) { if (e[0] == key) { return Body(e); } } <tail>` and rewrites it to the semantically equivalent direct lookup `if (key in M) { return Body[e := [key, M[key]]]; } <tail>`. This is the MVP §5.2 of the Lazy-ROM CCA case-study design: shape recognition for literal-equality predicates, leveraging map-key uniqueness. The injective-challenger-call variant (S2) is deferred to the §5.4 oracle-patching plan.

**Architecture:** Single new pass `LazyMapScan` placed in a new file `proof_frog/transforms/map_iteration.py` (keeps iteration-specific shape recognition isolated from `random_functions.py`). Statement-level rewrite: walk each method's block, find any `GenericFor` whose `over` is `M.entries` for some map field `M`, whose body is exactly one `IfStatement` matching the literal-equality shape `e[0] == key_expr` (with `key_expr` not referencing `e`) and whose block is a single `ReturnStatement`. On match, replace the `GenericFor` with a fresh `IfStatement` whose condition is `key_expr in M` and whose single-statement body is the rewritten return, substituting occurrences of `e` in the return expression with the tuple `[key_expr, M[key_expr]]` (and folding tuple-index accesses `e[0] → key_expr`, `e[1] → M[key_expr]`). Near-miss instrumentation covers S1 (body shape), the "key references loop variable" failure, and the "`over` is not `.entries`" failure when the user clearly meant to match.

**Tech Stack:** Python 3.11+, ANTLR-parsed AST (`proof_frog/frog_ast.py`), existing `TransformPass` / `PipelineContext` / `NearMiss` framework (`proof_frog/transforms/_base.py`), `visitors.BlockTransformer` / `SubstitutionTransformer` for statement-level rewriting, pytest.

**Out of scope for this plan:**
- The injective-challenger-call uniqueness form of S2 (belongs to §5.4 oracle-patching).
- Loop unrolling or general symbolic execution over `for` loops.
- Any cross-method analysis — `LazyMapScan` operates on one loop at a time inside a single method.
- Grammar / parser changes (the `GenericFor`-over-`Map.entries` syntax already typechecks after the landed §5.1 plan on this branch).

**Preconditions on the environment (all already landed on `feat/genericfor-map-array-typing`):**
- `for ([K, V] e in M.entries)` typechecks with `e : [K, V]` (§5.1 plan commit `e699fb3`).
- `LazyMapToSampledFunction` (§5.3) already in `CORE_PIPELINE` immediately before `ExtractRFCalls`. A map iterated via `.entries` does not satisfy §5.3's S3(c), so that pass leaves iterated maps untouched; `LazyMapScan` therefore always sees the raw `MapType` field.

---

## File Structure

**Create:**
- `proof_frog/transforms/map_iteration.py` — new module holding `LazyMapScan` and its helpers. Keep this file focused on iteration-shape recognition so future shape recognizers (e.g., `LazyArrayScan`) slot in naturally.
- `tests/unit/transforms/test_lazy_map_scan.py` — positive/negative unit tests.

**Modify:**
- `proof_frog/transforms/pipelines.py` — import and register `LazyMapScan` in `CORE_PIPELINE`. Placement: immediately **before** `LazyMapToSampledFunction()` (line 98 in current `pipelines.py`). Rationale: `LazyMapScan` needs the raw `MapType`; `LazyMapToSampledFunction` won't touch iterated maps, but the early placement makes the ordering explicit and removes any concern about pipeline interactions.
- `tests/unit/transforms/test_near_misses.py` — one near-miss assertion per instrumented failure site (S1 body-shape violation, key-references-loop-variable violation, malformed-`over` violation).
- `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md` — append a §7.1 implementation note mirroring the note for `LazyMapToSampledFunction`.

**No changes** to `proof_frog/frog_ast.py`, `proof_frog/semantic_analysis.py`, `proof_frog/frog_parser.py`, `proof_frog/diagnostics.py`, grammar files, or the VSCode extension.

---

## Preliminaries

- [ ] **Step 0a: Confirm clean working tree and baseline tests pass**

Run: `cd /Users/dstebila/Dev/ProofFrog/ProofFrog && git status && pytest tests/unit/transforms/ -q`
Expected: branch `feat/genericfor-map-array-typing` with `LazyMapToSampledFunction` already landed (commit `ef101e8`), and all transform unit tests passing.

- [ ] **Step 0b: Re-read design spec §5.2, §S1, §S2 and the §7.1 implementation note**

Open `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md` and read lines covering §5.2 (the LazyMapScan shape) and S1/S2 (soundness). Confirm:
- §5.2's pattern: `for ([K, V] e in M.entries) { if (Pred(e[0])) { return Body(e); } } return Default;`.
- S1 requires the loop body has the exact shape (single `if`, no else, body is single `return`).
- S2 uniqueness follows either from **literal equality** on `e[0]` (map keys are unique — the MVP path) OR from an `injective` challenger-oracle contract (deferred to §5.4).
- §7.1 already records that `LazyMapToSampledFunction` runs before `ExtractRFCalls`. This plan's §7.1 note will record `LazyMapScan` running just before `LazyMapToSampledFunction`.

- [ ] **Step 0c: Skim `LazyMapToSampledFunction` as the closest pattern reference**

Open `proof_frog/transforms/random_functions.py` around line 1846 (`class LazyMapToSampledFunction`) and `proof_frog/transforms/_base.py` for `TransformPass` and `NearMiss`. Reuse the same emission-helper shape (`_emit_near_miss`), same `ctx.near_misses.append(NearMiss(...))` idiom, same `copy.deepcopy` discipline when constructing the rewritten game.

---

## Task 1: Create test scaffold

**Files:**
- Create: `tests/unit/transforms/test_lazy_map_scan.py`

- [ ] **Step 1: Create the test file with shared helpers**

Exact content:

```python
"""Tests for the LazyMapScan transform pass (design spec §5.2)."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.map_iteration import LazyMapScan
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(game_src: str) -> frog_ast.Game:
    game = frog_parser.parse_game(game_src)
    return LazyMapScan().apply(game, _ctx())


def _apply_and_expect(game_src: str, expected_src: str) -> None:
    got = _apply(game_src)
    expected = frog_parser.parse_game(expected_src)
    assert got == expected, f"\nGOT:\n{got}\n\nEXPECTED:\n{expected}"


def _apply_and_expect_unchanged(game_src: str) -> None:
    original = frog_parser.parse_game(game_src)
    got = LazyMapScan().apply(original, _ctx())
    assert got == original, f"\nGOT:\n{got}\n\nEXPECTED UNCHANGED:\n{original}"
```

- [ ] **Step 2: Run pytest on the new file to confirm it loads (expected: ImportError)**

Run: `pytest tests/unit/transforms/test_lazy_map_scan.py -q`
Expected: collection error / ImportError on `from proof_frog.transforms.map_iteration import LazyMapScan` — module doesn't exist yet. This is the intended failing state before Task 2.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/transforms/test_lazy_map_scan.py
git commit -m "test: scaffold LazyMapScan tests"
```

---

## Task 2: Minimal positive rewrite — literal-equality scan → direct lookup

**Files:**
- Create: `proof_frog/transforms/map_iteration.py`
- Test: `tests/unit/transforms/test_lazy_map_scan.py`

This task handles the base shape with no trailing statements after the loop body's `return` is guaranteed to fire (the `<tail>` below runs when no key matches). The simplest positive case: one loop at the top of a method, no trailing statements after the `for`, method has a default return that follows the loop.

### The canonical input shape

```
Game G() {
    Map<K, V> M;
    R Oracle(..., K arg, ...) {
        for ([K, V] e in M.entries) {
            if (e[0] == arg) {
                return e[1];
            }
        }
        return Default;
    }
}
```

Canonical output:

```
Game G() {
    Map<K, V> M;
    R Oracle(..., K arg, ...) {
        if (arg in M) {
            return M[arg];
        }
        return Default;
    }
}
```

### Pattern match requirements (MVP)

Given a `frog_ast.GenericFor` node `gf`:

1. `gf.var_type` is a tuple type `[K, V]` (parser produces `frog_ast.Tuple` or `frog_ast.ProductType` with two element types — either is acceptable as long as it has length 2).
2. `gf.over` is a `frog_ast.FieldAccess` with `name == "entries"` and `the_object` a `frog_ast.Variable(M)` where `M` is a field of type `MapType(K, V)`.
3. `gf.block.statements` is exactly one statement, an `IfStatement` with one condition, one block, no else.
4. The `IfStatement.conditions[0]` is a `BinaryOperation` with operator `BinaryOperators.EQUALS`, left side is `ArrayAccess(Variable(e), Integer(0))` where `e == gf.var_name`, right side `key_expr` does **not** syntactically reference `Variable(e)` anywhere.
5. The `IfStatement.blocks[0].statements` is exactly one `ReturnStatement`, call its expression `body_expr`. `body_expr` may reference `e` only via `ArrayAccess(Variable(e), Integer(0))` (→ `key_expr`) or `ArrayAccess(Variable(e), Integer(1))` (→ `ArrayAccess(Variable(M), key_expr)`). Any other reference to `Variable(e)` disqualifies (S1 body shape is violated: we cannot substitute `e` safely).

On match, the rewrite replaces the `GenericFor` with:

```
IfStatement(
    conditions=[BinaryOperation(IN, key_expr, Variable(M))],
    blocks=[Block([ReturnStatement(rewritten_body_expr)])],
)
```

where `rewritten_body_expr` is `body_expr` with every `ArrayAccess(Variable(e), Integer(0))` substituted by `copy.deepcopy(key_expr)` and every `ArrayAccess(Variable(e), Integer(1))` substituted by `ArrayAccess(Variable(M), copy.deepcopy(key_expr))`.

### Confirm AST shapes before writing

- [ ] **Step 1: Spot-check AST shapes for the constructs we'll match**

Run this one-liner to print the parsed form of the canonical input and make sure the shapes match the assumptions above:

```bash
.venv/bin/python - <<'PY'
from proof_frog import frog_parser
src = """
Game G() {
    Map<BitString<8>, BitString<16>> M;
    BitString<16> Oracle(BitString<8> arg) {
        for ([BitString<8>, BitString<16>] e in M.entries) {
            if (e[0] == arg) {
                return e[1];
            }
        }
        return 0b0000000000000000;
    }
}
"""
g = frog_parser.parse_game(src)
m = g.methods[0]
for i, s in enumerate(m.block.statements):
    print(i, type(s).__name__, repr(s))
    if hasattr(s, "var_type"):
        print("    var_type:", type(s.var_type).__name__, s.var_type)
    if hasattr(s, "over"):
        print("    over:", type(s.over).__name__, s.over)
PY
```

Expected output: the first statement is a `GenericFor` with `var_type` a 2-element tuple / `ProductType`, `over` a `FieldAccess` with `name == "entries"`. If `var_type` turns out to be e.g. `Tuple` vs. `ProductType`, note it — the matcher needs the right `isinstance` check. If `e[0]` parses as an `ArrayAccess` with index of type `Integer`, confirm the integer-valued index class name (`Integer`, `IntLiteral`, or `Int`) in `proof_frog/frog_ast.py`. Update the pattern match code below to use whichever names the actual AST uses.

- [ ] **Step 2: Write the failing positive test**

Append to `tests/unit/transforms/test_lazy_map_scan.py`:

```python
def test_basic_scan_to_direct_lookup() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """,
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                if (arg in M) {
                    return M[arg];
                }
                return 0b0000000000000000;
            }
        }
        """,
    )
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/unit/transforms/test_lazy_map_scan.py::test_basic_scan_to_direct_lookup -v`
Expected: FAIL with `ModuleNotFoundError: proof_frog.transforms.map_iteration`.

- [ ] **Step 4: Create `proof_frog/transforms/map_iteration.py` with the pass**

Create the file with the exact content below. `VAR_TYPE_MATCHES_PAIR_TUPLE`, `MATCH_E_INDEX`, and the integer-literal class name must reflect what Step 1 showed — the placeholders below assume `frog_ast.Tuple` (two-element), `frog_ast.Integer(0)` / `Integer(1)`. If Step 1 revealed `ProductType` or `IntLiteral`, replace those two names consistently throughout the file.

```python
"""Iteration-shape canonicalization (design spec §5.2).

Currently contains:
    - LazyMapScan: rewrite
        for ([K, V] e in M.entries) { if (e[0] == key) { return Body(e); } }
        <tail>
      to
        if (key in M) { return Body[e[0]:=key, e[1]:=M[key]]; }
        <tail>

      under the soundness preconditions S1 (body shape) and implicit
      map-key uniqueness (no injective annotation required for literal
      equality — at most one entry[0] equals `key`).

The injective-challenger-call variant of S2 is handled in the §5.4
oracle-patching plan, not here.
"""

from __future__ import annotations

import copy

from .. import frog_ast
from ..visitors import SearchVisitor
from ._base import NearMiss, PipelineContext, TransformPass


_LAZY_MAP_SCAN_NAME = "Lazy Map Scan"


def _is_var(expr: frog_ast.ASTNode, name: str) -> bool:
    return isinstance(expr, frog_ast.Variable) and expr.name == name


def _is_tuple_index(
    expr: frog_ast.ASTNode, var_name: str, idx: int
) -> bool:
    """True iff *expr* is ``var_name[idx]`` with ``idx`` a literal integer."""
    if not isinstance(expr, frog_ast.ArrayAccess):
        return False
    if not _is_var(expr.the_array, var_name):
        return False
    i = expr.index
    # Integer literal class name — confirm against frog_ast.py in Task 2 Step 1.
    return isinstance(i, frog_ast.Integer) and i.num == idx


def _references_var(node: frog_ast.ASTNode, var_name: str) -> bool:
    """True iff *node* syntactically references ``Variable(var_name)``."""

    def matcher(n: frog_ast.ASTNode) -> bool:
        return isinstance(n, frog_ast.Variable) and n.name == var_name

    return SearchVisitor(matcher).visit(node) is not None


def _is_entries_access(
    expr: frog_ast.ASTNode, field_names: set[str]
) -> str | None:
    """If *expr* is ``<M>.entries`` where M is in *field_names*, return M.
    Else None."""
    if not isinstance(expr, frog_ast.FieldAccess):
        return None
    if expr.name != "entries":
        return None
    if not isinstance(expr.the_object, frog_ast.Variable):
        return None
    if expr.the_object.name not in field_names:
        return None
    return expr.the_object.name


def _substitute_tuple_var(
    expr: frog_ast.Expression,
    var_name: str,
    zero_repl: frog_ast.Expression,
    one_repl: frog_ast.Expression,
) -> frog_ast.Expression:
    """Return a deep copy of *expr* with every ``var_name[0]`` replaced by
    ``zero_repl`` and every ``var_name[1]`` replaced by ``one_repl``.

    Precondition: *expr* contains no bare ``Variable(var_name)`` reference —
    only tuple-index accesses. The caller verifies this before calling.
    """
    from ..visitors import Transformer  # pylint: disable=import-outside-toplevel

    class _Sub(Transformer):
        def leave_array_access(
            self, node: frog_ast.ArrayAccess
        ) -> frog_ast.Expression:
            if _is_tuple_index(node, var_name, 0):
                return copy.deepcopy(zero_repl)
            if _is_tuple_index(node, var_name, 1):
                return copy.deepcopy(one_repl)
            return node

    return _Sub().transform(copy.deepcopy(expr))


def _match_scan_body(
    gf: frog_ast.GenericFor, map_name: str
) -> tuple[frog_ast.Expression, frog_ast.Expression] | str:
    """Check S1 body shape. Return (key_expr, body_expr) on success, or a
    string describing the first failure (for near-miss reasons)."""
    stmts = gf.block.statements
    if len(stmts) != 1 or not isinstance(stmts[0], frog_ast.IfStatement):
        return "body is not exactly a single if-statement"
    if_stmt = stmts[0]
    if len(if_stmt.conditions) != 1 or len(if_stmt.blocks) != 1:
        return "if-statement has else/else-if branches"
    cond = if_stmt.conditions[0]
    if not (
        isinstance(cond, frog_ast.BinaryOperation)
        and cond.operator == frog_ast.BinaryOperators.EQUALS
    ):
        return "if condition is not a literal equality"
    e_name = gf.var_name
    # The equality may be written as e[0] == key OR key == e[0]; normalize.
    left, right = cond.left_expression, cond.right_expression
    if _is_tuple_index(left, e_name, 0):
        key_expr = right
    elif _is_tuple_index(right, e_name, 0):
        key_expr = left
    else:
        return "if condition is not of the form e[0] == <expr>"
    if _references_var(key_expr, e_name):
        return "key expression references the loop variable"
    body = if_stmt.blocks[0].statements
    if len(body) != 1 or not isinstance(body[0], frog_ast.ReturnStatement):
        return "if body is not a single return"
    body_expr = body[0].expression
    # body_expr may only reference e via e[0] or e[1]; bare references forbid.
    if _bare_references(body_expr, e_name):
        return "return expression references loop variable outside e[0]/e[1]"
    _ = map_name  # reserved for richer diagnostics
    return key_expr, body_expr


def _bare_references(
    expr: frog_ast.Expression, var_name: str
) -> bool:
    """True iff *expr* contains a ``Variable(var_name)`` reference that is
    NOT the array-base of an ``ArrayAccess(Variable(var_name), Integer(k))``
    for some literal integer k.
    """
    # Walk expr, flagging bare Variable(var_name) references.
    from ..visitors import SearchVisitor  # pylint: disable=import-outside-toplevel

    # Collect ArrayAccess nodes whose base is Variable(var_name) with
    # an integer literal index — those uses are *allowed*.
    allowed_ids: set[int] = set()

    def _collect(n: frog_ast.ASTNode) -> bool:
        if (
            isinstance(n, frog_ast.ArrayAccess)
            and _is_var(n.the_array, var_name)
            and isinstance(n.index, frog_ast.Integer)
        ):
            allowed_ids.add(id(n.the_array))
        return False

    SearchVisitor(_collect).visit(expr)

    def _is_bare(n: frog_ast.ASTNode) -> bool:
        return (
            isinstance(n, frog_ast.Variable)
            and n.name == var_name
            and id(n) not in allowed_ids
        )

    return SearchVisitor(_is_bare).visit(expr) is not None


class LazyMapScan(TransformPass):
    """Rewrite literal-equality scan loops over ``M.entries`` to direct
    lookups (design spec §5.2 / S1)."""

    name = _LAZY_MAP_SCAN_NAME

    def apply(
        self, game: frog_ast.Game, ctx: PipelineContext
    ) -> frog_ast.Game:
        map_fields = {
            f.name for f in game.fields if isinstance(f.type, frog_ast.MapType)
        }
        if not map_fields:
            return game
        new_game = copy.deepcopy(game)
        changed = False
        for method in new_game.methods:
            new_stmts, method_changed = self._rewrite_block(
                method.block.statements, map_fields, method.signature.name, ctx
            )
            if method_changed:
                method.block = frog_ast.Block(new_stmts)
                changed = True
        return new_game if changed else game

    def _rewrite_block(
        self,
        stmts: list[frog_ast.Statement],
        map_fields: set[str],
        method_name: str,
        ctx: PipelineContext,
    ) -> tuple[list[frog_ast.Statement], bool]:
        """Rewrite top-level scan loops in *stmts*. Returns (new_stmts, changed).

        Does NOT recurse into nested blocks in the MVP — nested scans are
        uncommon in ROM/CCA reductions, and handling them safely requires
        awareness of surrounding if/for context that the MVP does not need.
        """
        out: list[frog_ast.Statement] = []
        changed = False
        for stmt in stmts:
            if not isinstance(stmt, frog_ast.GenericFor):
                out.append(stmt)
                continue
            map_name = _is_entries_access(stmt.over, map_fields)
            if map_name is None:
                out.append(stmt)
                continue
            match = _match_scan_body(stmt, map_name)
            if isinstance(match, str):
                self._emit_near_miss(ctx, match, stmt, map_name, method_name)
                out.append(stmt)
                continue
            key_expr, body_expr = match
            # Construct: if (key in M) { return Body[e]; }
            rewritten_body = _substitute_tuple_var(
                body_expr,
                stmt.var_name,
                key_expr,
                frog_ast.ArrayAccess(
                    frog_ast.Variable(map_name), copy.deepcopy(key_expr)
                ),
            )
            new_if = frog_ast.IfStatement(
                [
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.IN,
                        copy.deepcopy(key_expr),
                        frog_ast.Variable(map_name),
                    )
                ],
                [frog_ast.Block([frog_ast.ReturnStatement(rewritten_body)])],
            )
            out.append(new_if)
            changed = True
        return out, changed

    def _emit_near_miss(
        self,
        ctx: PipelineContext,
        reason: str,
        stmt: frog_ast.GenericFor,
        map_name: str,
        method_name: str,
    ) -> None:
        ctx.near_misses.append(
            NearMiss(
                transform_name=_LAZY_MAP_SCAN_NAME,
                reason=(
                    f"Loop over '{map_name}.entries' in method "
                    f"'{method_name}' does not match LazyMapScan's literal-"
                    f"equality shape: {reason}"
                ),
                location=getattr(stmt, "origin", None),
                suggestion=(
                    "LazyMapScan fires only on loops whose body is exactly "
                    "`if (e[0] == <key-expr>) { return <body-expr>; }` with "
                    "the key expression not referencing the loop variable "
                    "and the body referencing the loop variable only via "
                    "e[0] / e[1]."
                ),
                variable=map_name,
                method=method_name,
            )
        )
```

Notes for the implementer:
- If `frog_ast.BinaryOperators.EQUALS` is named differently (grep `BinaryOperators` in `proof_frog/frog_ast.py`: common names are `EQUALS`, `EQ`, `IS_EQUAL`), use the correct constant.
- `frog_ast.IfStatement`'s constructor may take `(conditions, blocks)` or `(conditions, blocks, else_block)`; grep a few existing sites (e.g., `proof_frog/transforms/inlining.py`) for the idiomatic construction and mirror it.
- `frog_ast.Block([...])` accepts a list of statements — confirm with `proof_frog/frog_ast.py` `class Block`.
- If `Transformer.leave_array_access` isn't the right hook name, find the `Transformer` base class in `proof_frog/visitors.py` and use the correct `leave_*` / `transform_*` method name. The intent is: transform every `ArrayAccess` node in a bottom-up walk.

- [ ] **Step 5: Run the positive test**

Run: `pytest tests/unit/transforms/test_lazy_map_scan.py::test_basic_scan_to_direct_lookup -v`
Expected: PASS.

Likely failure modes and fixes:
- `AttributeError: module 'proof_frog.frog_ast' has no attribute 'Integer'` — look up the correct integer-literal class (probably `frog_ast.Int` or `frog_ast.IntLiteral`). Update `_is_tuple_index` and `_bare_references` accordingly.
- `ASTs not equal` — print `got` and `expected` and diff. Usually a constructor mismatch in `IfStatement` (missing third arg) or `BinaryOperation` (positional order). Do NOT change the expected source; fix the builder to produce the AST that `parse_game` produces from the canonical form.
- Transformer hook name: if `leave_array_access` doesn't trigger, grep `leave_` in `proof_frog/visitors.py` for the right convention; alternatively inline a manual recursion with `isinstance(node, frog_ast.ArrayAccess)` in a `SearchVisitor`-style walk, or use `copy.replace` patterns already used elsewhere in transforms.

- [ ] **Step 6: Run the whole transforms test suite**

Run: `pytest tests/unit/transforms/ -q`
Expected: all tests PASS. No regressions possible since `LazyMapScan` is not yet wired into `CORE_PIPELINE`.

- [ ] **Step 7: Commit**

```bash
git add proof_frog/transforms/map_iteration.py tests/unit/transforms/test_lazy_map_scan.py
git commit -m "feat(transforms): add LazyMapScan pass (literal-equality scan, MVP)"
```

---

## Task 3: Positive tests for variations that MUST fire

**Files:**
- Test: `tests/unit/transforms/test_lazy_map_scan.py`

All of these should already pass given Task 2's implementation. The goal is to pin the accepted surface.

- [ ] **Step 1: Append positive tests**

```python
def test_equality_reversed_order() -> None:
    # arg == e[0] instead of e[0] == arg
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (arg == e[0]) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """,
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                if (arg in M) {
                    return M[arg];
                }
                return 0b0000000000000000;
            }
        }
        """,
    )


def test_body_returns_e0() -> None:
    # Return e[0] instead of e[1] — should substitute e[0] -> arg.
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<8> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[0];
                    }
                }
                return 0b00000000;
            }
        }
        """,
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<8> Oracle(BitString<8> arg) {
                if (arg in M) {
                    return arg;
                }
                return 0b00000000;
            }
        }
        """,
    )


def test_trailing_statements_preserved() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                }
                BitString<16> s <- BitString<16>;
                return s;
            }
        }
        """,
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                if (arg in M) {
                    return M[arg];
                }
                BitString<16> s <- BitString<16>;
                return s;
            }
        }
        """,
    )


def test_two_maps_only_one_iterated() -> None:
    # Two map fields, only M iterated — N is left alone and doesn't disqualify.
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            Map<BitString<8>, BitString<16>> N;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """,
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            Map<BitString<8>, BitString<16>> N;
            BitString<16> Oracle(BitString<8> arg) {
                if (arg in M) {
                    return M[arg];
                }
                return 0b0000000000000000;
            }
        }
        """,
    )
```

- [ ] **Step 2: Run**

Run: `pytest tests/unit/transforms/test_lazy_map_scan.py -v`
Expected: all PASS. If `test_equality_reversed_order` fails, verify the left/right branch in `_match_scan_body` correctly handles both orderings. If `test_body_returns_e0` fails, the substitution logic for `e[0]` is broken — the substitution must replace the `ArrayAccess` node, not `Variable(e)`.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/transforms/test_lazy_map_scan.py
git commit -m "test: LazyMapScan positive variations (reversed equality, body variants, tails)"
```

---

## Task 4: Negative tests — shapes that MUST NOT fire

**Files:**
- Test: `tests/unit/transforms/test_lazy_map_scan.py`

Lock in the preconditions. No implementation changes expected; if a test fails because the pass fired, tighten `_match_scan_body`.

- [ ] **Step 1: Append negative tests**

```python
def test_body_has_multiple_statements_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                    BitString<16> z <- BitString<16>;
                }
                return 0b0000000000000000;
            }
        }
        """
    )


def test_if_has_else_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    } else {
                        return 0b0000000000000000;
                    }
                }
                return 0b0000000000000000;
            }
        }
        """
    )


def test_non_equality_predicate_fails() -> None:
    # `in` or a function call instead of ==
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            Set<BitString<8>> S;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] in S) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """
    )


def test_key_references_loop_var_fails() -> None:
    # e[0] == e[1] — "key" depends on loop variable, not a single-key lookup.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<8>> M;
            BitString<8> Oracle() {
                for ([BitString<8>, BitString<8>] e in M.entries) {
                    if (e[0] == e[1]) {
                        return e[0];
                    }
                }
                return 0b00000000;
            }
        }
        """
    )


def test_bare_loop_var_in_body_fails() -> None:
    # Body references bare `e` (not just e[0]/e[1]); can't safely substitute.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            [BitString<8>, BitString<16>] Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e;
                    }
                }
                return [0b00000000, 0b0000000000000000];
            }
        }
        """
    )


def test_iteration_over_keys_not_entries_fails() -> None:
    # MVP handles only .entries; .keys/.values deferred.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            Bool Oracle(BitString<8> arg) {
                for (BitString<8> k in M.keys) {
                    if (k == arg) {
                        return true;
                    }
                }
                return false;
            }
        }
        """
    )


def test_iteration_over_non_map_field_fails() -> None:
    # `.entries` on a Set (nonsense) — must leave alone.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Set<BitString<8>> S;
            Bool Oracle(BitString<8> arg) {
                for (BitString<8> k in S) {
                    if (k == arg) {
                        return true;
                    }
                }
                return false;
            }
        }
        """
    )
```

- [ ] **Step 2: Run**

Run: `pytest tests/unit/transforms/test_lazy_map_scan.py -v`
Expected: all negative tests PASS (game unchanged by the pass). If `test_if_has_else_fails` fails because the matcher accepted an if-with-else, fix the `len(if_stmt.blocks) != 1` check to also verify absence of an `else_block` field (depending on how `IfStatement` encodes else — confirm in `frog_ast.py`). The robust check is: if the AST tracks `has_else_block()`, call it; else ensure `len(blocks) == len(conditions)`.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/transforms/test_lazy_map_scan.py
git commit -m "test: negative cases for LazyMapScan preconditions"
```

---

## Task 5: Wire into `CORE_PIPELINE`

**Files:**
- Modify: `proof_frog/transforms/pipelines.py`

- [ ] **Step 1: Add the import**

Edit `proof_frog/transforms/pipelines.py`. After the existing imports from `.random_functions`, add a new import block:

```python
from .map_iteration import LazyMapScan
```

Place it alphabetically sensibly — after the `.random_functions` import block (around line 27 in current `pipelines.py`).

- [ ] **Step 2: Register in `CORE_PIPELINE`**

In the `CORE_PIPELINE` list (starts at line 87 in current `pipelines.py`), insert `LazyMapScan(),` immediately before `LazyMapToSampledFunction(),`:

```python
    ExtractRepeatedTupleAccess(),
    LazyMapScan(),
    LazyMapToSampledFunction(),
    ExtractRFCalls(),
```

- [ ] **Step 3: Run the transforms test suite**

Run: `pytest tests/unit/transforms/ -q`
Expected: all tests PASS.

- [ ] **Step 4: Run the full test suite**

Run: `pytest -q`
Expected: all tests PASS.

If any `tests/integration/test_proofs.py` cases fail, the pass fired on a proof it shouldn't have — most likely because the literal-equality scan pattern appears in an existing proof and rewrites it to a form some later pass doesn't expect. In that case:
1. Inspect the failing proof with `python -m proof_frog canonicalization-trace <proof-path>` on the pre-change codebase vs. post-change — identify which step first diverges.
2. If the rewrite is sound (it should be), the test was asserting an exact intermediate canonical form that shifted. Update the test's expectation.
3. If the rewrite destabilized a later pass (e.g., `BranchElimination` now misbehaves on the new `if (key in M)` shape), file the issue and consider moving `LazyMapScan` later in the pipeline, or gating it more narrowly.

Do NOT silently disable the pass.

- [ ] **Step 5: Integration test through the pipeline**

Append to `tests/unit/transforms/test_lazy_map_scan.py`:

```python
def test_integration_via_core_pipeline() -> None:
    """Run the full CORE_PIPELINE over a game containing the scan pattern
    and confirm the GenericFor is gone after canonicalization."""
    # pylint: disable=import-outside-toplevel
    from proof_frog.transforms._base import run_pipeline
    from proof_frog.transforms.pipelines import CORE_PIPELINE

    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """
    )
    result = run_pipeline(game, CORE_PIPELINE, _ctx())

    class _FindGenericFor(SearchVisitor):
        pass

    from proof_frog.visitors import SearchVisitor  # pylint: disable=import-outside-toplevel

    found = SearchVisitor(
        lambda n: isinstance(n, frog_ast.GenericFor)
    ).visit(result)
    assert found is None, f"GenericFor should be eliminated, got:\n{result}"
```

Simplify the import if convenient — the `_FindGenericFor` stub is unused, delete it if the one-liner `SearchVisitor(...)` suffices.

- [ ] **Step 6: Run the integration test**

Run: `pytest tests/unit/transforms/test_lazy_map_scan.py::test_integration_via_core_pipeline -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add proof_frog/transforms/pipelines.py tests/unit/transforms/test_lazy_map_scan.py
git commit -m "feat(transforms): wire LazyMapScan into CORE_PIPELINE"
```

---

## Task 6: Near-miss instrumentation tests

**Files:**
- Test: `tests/unit/transforms/test_near_misses.py`

The emission path is already present in `_match_scan_body` + `_emit_near_miss` from Task 2. This task locks in the observable near-miss behavior for three failure modes, one test per S1-adjacent precondition.

- [ ] **Step 1: Append near-miss tests**

Append to `tests/unit/transforms/test_near_misses.py`:

```python
from proof_frog.transforms.map_iteration import LazyMapScan


def _lazy_scan_ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def test_lazy_scan_near_miss_if_with_else() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    } else {
                        return 0b0000000000000000;
                    }
                }
                return 0b0000000000000000;
            }
        }
        """
    )
    ctx = _lazy_scan_ctx()
    result = LazyMapScan().apply(game, ctx)
    assert result == game
    assert any(
        nm.transform_name == "Lazy Map Scan"
        and nm.method == "Oracle"
        and nm.variable == "M"
        and "else" in nm.reason
        for nm in ctx.near_misses
    )


def test_lazy_scan_near_miss_key_references_loop_var() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<8>> M;
            BitString<8> Oracle() {
                for ([BitString<8>, BitString<8>] e in M.entries) {
                    if (e[0] == e[1]) {
                        return e[0];
                    }
                }
                return 0b00000000;
            }
        }
        """
    )
    ctx = _lazy_scan_ctx()
    LazyMapScan().apply(game, ctx)
    assert any(
        nm.transform_name == "Lazy Map Scan"
        and nm.method == "Oracle"
        and "loop variable" in nm.reason
        for nm in ctx.near_misses
    )


def test_lazy_scan_no_near_miss_when_no_scan() -> None:
    # Map exists but no GenericFor over .entries: silent, no near-miss noise.
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            Int Size() {
                return |M|;
            }
        }
        """
    )
    ctx = _lazy_scan_ctx()
    LazyMapScan().apply(game, ctx)
    assert not any(
        nm.transform_name == "Lazy Map Scan" for nm in ctx.near_misses
    )
```

- [ ] **Step 2: Run the near-miss tests**

Run: `pytest tests/unit/transforms/test_near_misses.py -v`
Expected: all tests PASS (new and pre-existing).

If `test_lazy_scan_near_miss_if_with_else` fails because no near-miss was emitted, confirm that `_match_scan_body` distinguishes "if has else" from the other failure modes and returns a reason string containing the word `else`. Update the reason string if needed (the test looks for `"else"` as a substring).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/transforms/test_near_misses.py
git commit -m "test: near-miss assertions for LazyMapScan precondition failures"
```

---

## Task 7: Lint, type-check, format

**Files:**
- Any touched files.

- [ ] **Step 1: Run the full lint pipeline**

Run: `make lint`
Expected: `black --check`, `mypy --no-warn-unused-ignores`, `pylint` (target 10.00/10) all pass.

Common fixes:
- `black` failure → run `make format`, then re-run `make lint`.
- `mypy` missing types on e.g. `frog_ast.IfStatement` construction → check that arguments match the declared signature in `frog_ast.py`. If the `Transformer` subclass triggers `misc`/`no-untyped-def` warnings from the `leave_array_access` hook, follow the suppression pattern the project already uses for visitors: `# type: ignore[override]` on the overriding method.
- `pylint` complaints about too-many-locals / too-many-branches in `_rewrite_block` → extract the scan-match + build-if portion into a private helper `_try_rewrite_scan` returning `IfStatement | None`.
- `pylint` `import-outside-toplevel` on the lazy `from ..visitors import Transformer` inside `_substitute_tuple_var` — add `# pylint: disable=import-outside-toplevel` as the first line inside the function body (this matches the convention noted in CLAUDE.md).

- [ ] **Step 2: Run the full test suite once more**

Run: `pytest -q`
Expected: all tests pass.

- [ ] **Step 3: Commit any formatting/lint-driven fixes**

```bash
git add -u
git commit -m "chore: apply black and lint fixes for LazyMapScan"
```

Skip if the working tree is clean.

---

## Task 8: Spec implementation note + self-review

**Files:**
- Modify: `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md`

- [ ] **Step 1: Append implementation note to §7.1**

Append a new bullet to the existing "Implementation notes" subsection (§7.1) in `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md` (after the `LazyMapToSampledFunction` note), using the same shape as the existing entry. Suggested content (edit to match what actually landed):

```markdown
- **§5.2 `LazyMapScan` (landed <DATE>):** registered in `CORE_PIPELINE`
  immediately before `LazyMapToSampledFunction`. MVP handles the
  literal-equality scan shape `for ([K, V] e in M.entries) { if (e[0] ==
  key) { return Body(e); } }` → `if (key in M) { return Body[e[0]:=key,
  e[1]:=M[key]]; }`. Soundness: S1 (body shape) verified syntactically;
  S2 uniqueness comes from map-key uniqueness in this MVP — no
  `injective` annotation required. The injective-challenger-call
  variant of S2 remains for the §5.4 oracle-patching plan, which will
  extend `LazyMapScan` (or add a sibling pass) to also match
  `challenger.TestOracle(arg, e[0])` predicates when `Test` is
  annotated `deterministic injective`. Near-miss instrumentation covers
  body-shape, key-references-loop-variable, and else-branch violations;
  the pass emits no near-miss when no scan-over-`.entries` pattern is
  present (silent skip). No entry added to `proof_frog/diagnostics.py`
  — near-miss path is sufficient.
```

Replace `<DATE>` with today's (`2026-04-20` or the date the work lands).

- [ ] **Step 2: Self-review: spec-coverage audit**

Confirm each §5.2 / S1 / S5 requirement is covered:

- §5.2 pattern match: `test_basic_scan_to_direct_lookup`, `test_equality_reversed_order`, `test_trailing_statements_preserved`.
- S1 body shape: `test_body_has_multiple_statements_fails`, `test_if_has_else_fails`, `test_non_equality_predicate_fails`.
- S5 near-miss completeness: `test_lazy_scan_near_miss_if_with_else`, `test_lazy_scan_near_miss_key_references_loop_var`, `test_lazy_scan_no_near_miss_when_no_scan`.
- S2 injective-challenger variant: **explicitly deferred to §5.4 plan** (recorded in §7.1 note above and in the "Out of scope" block at the top of this plan).

Confirm nothing out-of-scope crept in:
- No cross-method analysis (each scan is rewritten purely in-method).
- No changes to `proof_frog/frog_ast.py`, `proof_frog/semantic_analysis.py`, grammar files, parser, or `proof_frog/diagnostics.py`.
- No new entries in `STANDARDIZATION_PIPELINE` — this pass belongs in `CORE_PIPELINE` only.

- [ ] **Step 3: Self-review: placeholder scan**

Grep the new source files for TBD / TODO / "implement later":

```bash
grep -nE "TBD|TODO|FIXME|implement later|fill in" proof_frog/transforms/map_iteration.py tests/unit/transforms/test_lazy_map_scan.py
```

Expected: no matches. Any match must be resolved before the next commit.

- [ ] **Step 4: Commit spec note**

```bash
git add docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md
git commit -m "docs(spec): record LazyMapScan implementation note in §7.1"
```

Skip if the spec wasn't modified (e.g., the note was added in Task 5 or earlier).

---

## Success criteria

When every task above is complete:

- A game that contains `for ([K, V] e in M.entries) { if (e[0] == key) { return Body(e); } }` canonicalizes to the same game with the loop replaced by `if (key in M) { return Body[e[0]:=key, e[1]:=M[key]]; }`. Trailing statements after the loop are preserved.
- Shapes that violate S1 (non-singleton body, non-equality predicate, else branches, key references the loop variable, body references the loop variable outside `e[0]`/`e[1]`) leave the game unchanged and, when the surrounding shape was a clear near-match, emit a structured `NearMiss`.
- `LazyMapScan` is registered in `CORE_PIPELINE` immediately before `LazyMapToSampledFunction`.
- `make lint` and `pytest -q` pass.
- Spec §7.1 records the implementation note, mirroring the note for `LazyMapToSampledFunction`.

The next sub-plan (§5.4 oracle-patching) can assume the literal-equality scan shape has already been eliminated by `LazyMapScan`, and will need to extend (or parallel) this pass to handle the `challenger.TestOracle(arg, e[0])` variant under the `deterministic injective` annotation on `Test`.
