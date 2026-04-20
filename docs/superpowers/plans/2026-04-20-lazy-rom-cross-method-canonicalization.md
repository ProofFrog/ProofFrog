# Lazy-ROM Cross-Method Canonicalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status (2026-04-20):** Parts A, B, D, E **landed** on `feat/genericfor-map-array-typing` (commits `84f812a`..`77f2cee`, 15 commits total). `make lint` clean; `pytest -q` = 1772 passed. Pipeline order matches design §5. Both passes have full positive + negative tests and near-miss instrumentation. **Part C (case-study verification) blocked**: the §4.1 `DecapsIter-IND-CCA.proof` and §4.3 `HashedElGamal-KEM-IND-CCA.proof` files do not exist yet under `extras/examples/engine-case-studies/lazy-rom-cca/proof/`; writing them is the responsibility of `docs/superpowers/plans/2026-04-20-lazy-rom-cca-case-study-proofs.md`, not this plan. Per plan C1 Step 1's own instruction ("if not yet written, stop here and note the dependency"), execution halted after Part E. **Note:** SEMANTICS.md edits (Task D1) landed on disk but `extras/` is gitignored, so they are not in the commit history.

**Goal:** Land two new canonicalization passes — `MapKeyReindex` (Pass 1) and `LazyMapPairToSampledFunction` (Pass 2) — that together unblock end-to-end verification of the §4.1 `DecapsIter` and §4.3 Hashed ElGamal CCA case-study proofs, per `docs/superpowers/specs/2026-04-20-lazy-rom-cross-method-canonicalization-design.md`.

**Architecture:**

- **Pass 1 (`MapKeyReindex`)** rewrites a `Map<A, V>` field to `Map<B, V>` when every use of the map's keys is through a `deterministic injective` primitive method `f : A -> B`. Lives in a new file `proof_frog/transforms/map_reindex.py`. After this pass, what was `if (M[k_loop] == f(a)) …` becomes `if (k_loop == a) …` under substitution, and literal-equality `LazyMapScan` can then fold the scan.
- **Pass 2 (`LazyMapPairToSampledFunction`)** generalizes the landed `LazyMapToSampledFunction` to two `Map<K, V>` fields accessed through a mutually-disjoint guarded lazy-lookup idiom; collapses the pair to a single sampled `Function<K, V>`. Lives in `proof_frog/transforms/random_functions.py` alongside `LazyMapToSampledFunction`.
- Both passes emit `NearMiss` diagnostics on every precondition-failure site.
- Both are registered in `CORE_PIPELINE` at the positions dictated by spec §5: Pass 1 after `LazyMapScan` and before `LazyMapToSampledFunction`; Pass 2 immediately after `LazyMapToSampledFunction`.

**Tech Stack:** Python 3.11+, existing `TransformPass` / `PipelineContext` / `NearMiss` framework (`proof_frog/transforms/_base.py`), `visitors.SearchVisitor` / `Transformer`, pytest.

**Out of scope for this plan:**

- `Array` re-indexing (Pass 1 covers `Map` only).
- Inferring `TestOracle(x, y) ⟺ y == Eval(sk, x)` from primitive annotations (deliberately rejected in design §2.2).
- FO transform / OAEP re-encryption idioms (orthogonal canonicalization).
- §4.2 `HashIter` / StarFortress Theorem 1 proof (should land for free; verifying is a follow-up plan).

**Preconditions on the environment:**

- Branch `feat/genericfor-map-array-typing` with `LazyMapScan` and `LazyMapToSampledFunction` already landed (commits `ca7b5ff`, `4eeffd3`, `ef101e8`).
- The §4.1 / §4.3 artifacts from the case-study plan exist under `extras/examples/engine-case-studies/lazy-rom-cca/` (gitignored; check with `ls`).

---

## File Structure

**Create:**

- `proof_frog/transforms/map_reindex.py` — new module holding `MapKeyReindex` and its helpers.
- `tests/unit/transforms/test_map_key_reindex.py` — positive and negative unit tests for Pass 1.
- `tests/unit/transforms/test_lazy_map_pair_to_sampled_function.py` — positive and negative unit tests for Pass 2.

**Modify:**

- `proof_frog/transforms/random_functions.py` — add `LazyMapPairToSampledFunction` class at the end of the file (alongside `LazyMapToSampledFunction`).
- `proof_frog/transforms/pipelines.py` — import and register both new passes.
- `tests/unit/transforms/test_near_misses.py` — one assertion per new instrumented failure site (see §7 of design spec).
- `extras/docs/transforms/SEMANTICS.md` — add one bullet to §9.3 and one cross-reference note in §6.5.
- `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md` — add a forward reference from §5.4 to the new design spec and to this plan.
- `CLAUDE.md` — add one guideline under "Guidelines for creating FrogLang files" about assumption-game oracle bodies inlining semantic contracts directly.

**No changes** to `proof_frog/frog_ast.py`, `proof_frog/semantic_analysis.py`, `proof_frog/frog_parser.py`, grammar files, or the VSCode extension.

---

## Preliminaries

- [ ] **Step 0a: Confirm clean working tree and baseline tests pass**

Run: `cd /Users/dstebila/Dev/ProofFrog/ProofFrog && git status && pytest tests/unit/transforms/ -q`

Expected: On branch `feat/genericfor-map-array-typing`. All transform unit tests pass (≥1158 tests).

- [ ] **Step 0b: Re-read the design spec and related context**

Read:
- `docs/superpowers/specs/2026-04-20-lazy-rom-cross-method-canonicalization-design.md` (this plan's source of truth).
- `proof_frog/transforms/map_iteration.py` (LazyMapScan, as a pattern reference).
- `proof_frog/transforms/random_functions.py` lines 1846–2093 (`LazyMapToSampledFunction`) — the closest sibling for Pass 2.
- `proof_frog/transforms/_base.py` (`TransformPass`, `NearMiss`, `PipelineContext`, `_lookup_primitive_method`).

Confirm:
- Pass 1's shape (design §3.1): `Map<A, V> M; M[a] = s; ... M[f(a')] ...` → `Map<B, V>; M[f(a)] = s; ...`.
- Pass 2's shape (design §4.1): two maps with lazy-idiom reads and mutual-disjointness-guarded writes → single sampled `Function<K, V>`.

- [ ] **Step 0c: Skim the §4.1 case-study artifact**

Run: `ls extras/examples/engine-case-studies/lazy-rom-cca/`

Read `extras/examples/engine-case-studies/lazy-rom-cca/proof/` contents (if any) and the reduction under the existing case-study plan to see the concrete shape Pass 1 must accept. This is not a code change, just orientation.

---

## Part A — Pass 1: `MapKeyReindex`

### Task A1: Scaffold the new module with a no-op `MapKeyReindex` class

**Files:**
- Create: `proof_frog/transforms/map_reindex.py`

- [ ] **Step 1: Write the module skeleton**

Create `proof_frog/transforms/map_reindex.py`:

```python
"""Map key re-indexing under an injective deterministic function (design §3).

:class:`MapKeyReindex` rewrites a ``Map<A, V>`` field to ``Map<B, V>`` when every
use of the map's keys is through a ``deterministic injective`` primitive method
``f : A -> B``.  After this pass, scans whose predicate is ``e[0] == f(a)``
become ``e[0] == a`` (under substitution), which the literal-equality
``LazyMapScan`` can then fold to a direct lookup.

Soundness argument: see design spec §3.3 (value preservation, non-collision,
iteration preservation, adversary-invisibility of internal state).
"""

from __future__ import annotations

import copy
from typing import Optional

from .. import frog_ast
from ..visitors import SearchVisitor, Transformer
from ._base import NearMiss, PipelineContext, TransformPass, _lookup_primitive_method

_NAME = "Map Key Reindex"


class MapKeyReindex(TransformPass):
    """Re-index a ``Map<A, V>`` field to ``Map<B, V>`` under a ``deterministic
    injective`` primitive method ``f : A -> B`` (design §3)."""

    name = _NAME

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return game  # implemented in subsequent tasks
```

- [ ] **Step 2: Register the pass in the pipeline (still a no-op)**

Edit `proof_frog/transforms/pipelines.py`:

Add import:
```python
from .map_reindex import MapKeyReindex
```

Insert `MapKeyReindex()` in `CORE_PIPELINE` immediately after `LazyMapScan()` and before `LazyMapToSampledFunction()`:

```python
    LazyMapScan(),
    MapKeyReindex(),
    LazyMapToSampledFunction(),
```

- [ ] **Step 3: Run lint and tests**

Run: `make lint && pytest tests/unit/transforms/ -q`

Expected: both pass. The no-op pass is registered; nothing behaves differently yet.

- [ ] **Step 4: Commit**

```bash
git add proof_frog/transforms/map_reindex.py proof_frog/transforms/pipelines.py
git commit -m "feat(transforms): scaffold MapKeyReindex no-op pass"
```

---

### Task A2: Create the test file with the positive-case fixture

**Files:**
- Create: `tests/unit/transforms/test_map_key_reindex.py`

- [ ] **Step 1: Write the failing positive test**

Create `tests/unit/transforms/test_map_key_reindex.py`:

```python
"""Tests for the MapKeyReindex transform pass (design §3)."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.map_reindex import MapKeyReindex
from proof_frog.visitors import NameTypeMap


_TRAPDOOR_PRIMITIVE = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    deterministic injective Image Eval(Input x);
}
"""


_NON_INJECTIVE_PRIMITIVE = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    deterministic Image Eval(Input x);
}
"""


_NON_DETERMINISTIC_PRIMITIVE = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    injective Image Eval(Input x);
}
"""


def _ctx_with_primitive(primitive_src: str = _TRAPDOOR_PRIMITIVE) -> PipelineContext:
    ctx = PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )
    if primitive_src:
        prim = frog_parser.parse_string(primitive_src, frog_ast.FileType.PRIMITIVE)
        ctx.proof_namespace[prim.name] = prim
        ctx.proof_namespace["TT"] = prim
    return ctx


def _apply(game_src: str, ctx: PipelineContext) -> frog_ast.Game:
    game = frog_parser.parse_game(game_src)
    return MapKeyReindex().apply(game, ctx)


def _apply_and_expect(
    game_src: str,
    expected_src: str,
    ctx: PipelineContext | None = None,
) -> None:
    ctx = ctx or _ctx_with_primitive()
    got = _apply(game_src, ctx)
    expected = frog_parser.parse_game(expected_src)
    assert got == expected, f"\nGOT:\n{got}\n\nEXPECTED:\n{expected}"


def _apply_and_expect_unchanged(
    game_src: str, ctx: PipelineContext | None = None
) -> None:
    ctx = ctx or _ctx_with_primitive()
    original = frog_parser.parse_game(game_src)
    got = MapKeyReindex().apply(original, ctx)
    assert got == original, f"\nGOT:\n{got}\n\nEXPECTED UNCHANGED:\n{original}"


def test_basic_reindex() -> None:
    _apply_and_expect(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[a] = s;
            }
            BitString<16>? Lookup(TT.Input a2) {
                if (TT.Eval(a2) in M) {
                    return M[TT.Eval(a2)];
                }
                return None;
            }
        }
        """,
        """
        Game G(T TT) {
            Map<TT.Image, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[TT.Eval(a)] = s;
            }
            BitString<16>? Lookup(TT.Input a2) {
                if (TT.Eval(a2) in M) {
                    return M[TT.Eval(a2)];
                }
                return None;
            }
        }
        """,
    )
```

Note: The writer may need to tweak the `Map<TT.Input, ...>` vs `Map<TT.Image, ...>` spelling to match whatever the parser emits (type aliases resolve in semantic analysis, but the AST nodes should compare equal when the source text is the same).

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/transforms/test_map_key_reindex.py::test_basic_reindex -v`

Expected: FAIL — current `MapKeyReindex.apply` is a no-op, so the game is returned unchanged.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/unit/transforms/test_map_key_reindex.py
git commit -m "test(transforms): add failing MapKeyReindex basic case"
```

---

### Task A3: Build the "uses of map M" classifier

Pass 1's core analysis is: "for each map field `M : Map<A, V>`, classify every syntactic use of `M`, and determine whether there exists an injective deterministic primitive method `f` such that every key position uses `f(·)` (or substitutes cleanly to `f(·)` in a loop body)". This task builds the classifier returning either a match (with the chosen `f`) or a near-miss reason.

**Files:**
- Modify: `proof_frog/transforms/map_reindex.py`

- [ ] **Step 1: Add use-site enumeration helpers**

Append to `proof_frog/transforms/map_reindex.py`:

```python
from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class _KeyUnderF:
    """A syntactic use of ``M``'s key in the form ``f(arg)``."""

    f_call: frog_ast.FuncCall  # the f(arg) expression; use its .args[0] as arg
    location: frog_ast.SourceOrigin | None


@dataclass(frozen=True)
class _KeyRaw:
    """A syntactic use of ``M``'s key not through ``f`` (near-miss)."""

    key_expr: frog_ast.Expression
    location: frog_ast.SourceOrigin | None
    detail: str  # short description for the near-miss


@dataclass(frozen=True)
class _LoopKeyE0:
    """A loop over ``M.entries`` where ``e[0]`` is only used inside ``f(e[0])``.
    The loop body is safe to rewrite by substituting ``e[0] := f(e[0])_original``.
    """

    loop: frog_ast.GenericFor


_KeyUse = Union[_KeyUnderF, _KeyRaw, _LoopKeyE0]


def _all_accesses_of_map(
    method: frog_ast.Method,
    map_name: str,
) -> list[frog_ast.ASTNode]:
    """Return every syntactic sub-expression or statement that touches ``M``.

    Covers: ``M[k]`` (read or write LHS), ``k in M``, ``M.entries`` /
    ``M.keys`` / ``M.values`` / ``|M|``, ``for (e in M.entries)`` loops,
    and bare ``Variable(M)`` references.
    """
    hits: list[frog_ast.ASTNode] = []

    def _visit(n: frog_ast.ASTNode) -> bool:
        # ArrayAccess with base M: M[k]
        if isinstance(n, frog_ast.ArrayAccess) and isinstance(
            n.the_array, frog_ast.Variable
        ) and n.the_array.name == map_name:
            hits.append(n)
        # FieldAccess M.entries/.keys/.values
        if isinstance(n, frog_ast.FieldAccess) and isinstance(
            n.the_object, frog_ast.Variable
        ) and n.the_object.name == map_name:
            hits.append(n)
        # "k in M"
        if (
            isinstance(n, frog_ast.BinaryOperation)
            and n.operator == frog_ast.BinaryOperators.IN
            and isinstance(n.right_expression, frog_ast.Variable)
            and n.right_expression.name == map_name
        ):
            hits.append(n)
        # "|M|"
        if (
            isinstance(n, frog_ast.UnaryOperation)
            and n.operator == frog_ast.UnaryOperators.SIZE
            and isinstance(n.expression, frog_ast.Variable)
            and n.expression.name == map_name
        ):
            hits.append(n)
        return False

    SearchVisitor(_visit).visit(method)
    return hits
```

Notes for the implementer:
- `frog_ast.UnaryOperators.SIZE` may be spelled differently; grep `proof_frog/frog_ast.py` for the cardinality operator name (`SIZE`, `LENGTH`, or similar) and adjust.
- `frog_ast.BinaryOperators.IN` is the membership operator; confirm the spelling.

- [ ] **Step 2: Add the "uses are all through f" classifier**

Append to the same file:

```python
def _expr_is_call_of(
    expr: frog_ast.Expression,
    method_sig: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> Optional[frog_ast.FuncCall]:
    """True iff *expr* is ``f(·)`` where f resolves to *method_sig*."""
    if not isinstance(expr, frog_ast.FuncCall):
        return None
    looked_up = _lookup_primitive_method(expr.func, ctx.proof_namespace)
    if looked_up is not method_sig:
        return None
    if len(expr.args) != 1:
        return None
    return expr


def _classify_key_expr(
    key_expr: frog_ast.Expression,
    candidate_f: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> bool:
    """True iff *key_expr* is literally ``candidate_f(·)``."""
    return _expr_is_call_of(key_expr, candidate_f, ctx) is not None
```

- [ ] **Step 3: No test runs yet — classifiers are pure helpers**

Just run `make lint` to catch syntax errors.

- [ ] **Step 4: Commit**

```bash
git add proof_frog/transforms/map_reindex.py
git commit -m "feat(transforms): MapKeyReindex classifier helpers"
```

---

### Task A4: Implement candidate-`f` discovery

For each map field `M`, we need to find an injective deterministic primitive method `f : A -> B` such that every read of `M`'s keys is `f(_)`. Writes are more permissive — we also accept raw keys on the write side and rewrite them to `f(raw_key)`, provided the raw key is identified as either a parameter whose every read elsewhere is under `f` (the §4.1 case where `PendingDecaps[c] = s` but every scan uses `f(c) == e[0]`) or can be shown safe. For the MVP we require:

- All **reads** (including iteration and membership) have keys of the form `f(·)`.
- All **writes** either have keys of the form `f(·)` already, OR have a raw key `k` (an `Expression`) that appears nowhere else outside this same write (i.e., the assignment is the only use of that specific key-expression's value). **MVP simplification:** we only accept writes whose key is a **simple variable** `a` (parameter or locally-bound). For such writes we emit `M[f(a)] = v` after rewrite. Any other write shape fails.

- [ ] **Step 1: Add candidate-`f` discovery**

Append to `proof_frog/transforms/map_reindex.py`:

```python
def _find_candidate_f(
    game: frog_ast.Game,
    map_name: str,
    ctx: PipelineContext,
) -> Optional[frog_ast.MethodSignature]:
    """Scan all read-site key expressions of M across all methods.  Return the
    unique primitive method ``f`` used at every read site, or ``None`` if no
    such f exists (too many candidates, non-injective, not deterministic, or a
    read site uses a raw key).
    """
    read_site_f: Optional[frog_ast.MethodSignature] = None
    for method in game.methods:
        for hit in _all_accesses_of_map(method, map_name):
            key_expr = _extract_read_key(hit)
            if key_expr is None:
                continue  # write-side; handled separately
            if not isinstance(key_expr, frog_ast.FuncCall):
                return None
            looked_up = _lookup_primitive_method(key_expr.func, ctx.proof_namespace)
            if looked_up is None:
                return None
            if not (looked_up.deterministic and looked_up.injective):
                return None
            if len(key_expr.args) != 1:
                return None
            if read_site_f is None:
                read_site_f = looked_up
            elif read_site_f is not looked_up:
                return None
    return read_site_f


def _extract_read_key(hit: frog_ast.ASTNode) -> Optional[frog_ast.Expression]:
    """Given a hit from _all_accesses_of_map, return the key expression at a
    read site (``M[k]``, ``k in M``, etc.), or None for write-LHS and
    cardinality/iteration sites (which have no key expression)."""
    if isinstance(hit, frog_ast.ArrayAccess):
        return hit.index  # may be a write LHS too; caller disambiguates
    if isinstance(hit, frog_ast.BinaryOperation):
        return hit.left_expression
    return None  # FieldAccess (.entries etc.) and UnaryOperation (|M|)
```

Notes for the implementer:
- `_extract_read_key` returns the index of **any** `ArrayAccess`, including write LHSes. At the candidate-discovery stage that's fine: a write-LHS key that isn't `f(_)` disqualifies the pass unless it's a simple-variable write (handled in Task A5's write-rewriting step). This gives a conservative candidate `f`; false positives there are filtered in the precondition check.

- [ ] **Step 2: Commit**

```bash
git add proof_frog/transforms/map_reindex.py
git commit -m "feat(transforms): MapKeyReindex candidate-f discovery"
```

---

### Task A5: Implement the full rewrite

- [ ] **Step 1: Implement `apply`**

Replace the no-op `apply` in `proof_frog/transforms/map_reindex.py` with:

```python
    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        for fld in game.fields:
            if not isinstance(fld.type, frog_ast.MapType):
                continue
            rewritten = self._try_rewrite(game, fld, ctx)
            if rewritten is not None:
                return rewritten
        return game

    def _try_rewrite(
        self,
        game: frog_ast.Game,
        fld: frog_ast.Field,
        ctx: PipelineContext,
    ) -> Optional[frog_ast.Game]:
        map_name = fld.name
        assert isinstance(fld.type, frog_ast.MapType)
        f_sig = _find_candidate_f(game, map_name, ctx)
        if f_sig is None:
            return None

        # All read sites use f(·).  Validate write sites and loop bodies; if
        # valid, rewrite.
        new_game = copy.deepcopy(game)
        plan = self._plan_rewrite(new_game, map_name, f_sig, ctx)
        if plan is None:
            return None
        self._execute_rewrite(new_game, map_name, f_sig, plan)
        return new_game

    def _plan_rewrite(
        self,
        game: frog_ast.Game,
        map_name: str,
        f_sig: frog_ast.MethodSignature,
        ctx: PipelineContext,
    ) -> Optional[list["_WritePlan"]]:
        """Check every write site is rewriteable and every loop body's e[0]
        usage is confined to f(e[0]).  Return the list of planned write
        rewrites, or None on failure (emits near-misses)."""
        ...
```

- [ ] **Step 2: Implement `_plan_rewrite` and `_execute_rewrite`**

The planner walks each method, finds write sites `M[k] = v` / `M[k] <- T`, and classifies:

- `k` is already `f(·)` → no-op on the write (key stays as written).
- `k` is a simple `Variable` → plan to rewrite to `M[f(k)] = v`.
- Else → near-miss + abort.

For iteration loops `for ([K, V] e in M.entries) { body }`, check that every occurrence of `e[0]` inside `body` is the argument to a call of `f`. If not, near-miss + abort. If yes, plan: substitute `e[0] := e[0]` (identity — the new map has `e[0]` of type `B` directly, so what *used to be* `f(e[0])` becomes just `e[0]`). Use a `Transformer` that rewrites occurrences of `f(e[0])` inside the loop body to `e[0]`.

Write `_WritePlan` as a dataclass holding method index, statement index, old-key AST, and the f-wrapping transform. Execute by deep-copying and mutating.

Full code:

```python
@dataclass
class _WritePlan:
    method_idx: int
    stmt_path: list[int]  # path to the statement within method.block
    key_needs_wrapping: bool
    original_key: frog_ast.Expression


@dataclass
class _LoopPlan:
    method_idx: int
    loop_ref: frog_ast.GenericFor  # identity-compared after deepcopy


class _WrapKeyTransformer(Transformer):
    """Rewrite occurrences of f(e[0]) inside a loop body to just e[0]."""

    def __init__(
        self,
        f_sig: frog_ast.MethodSignature,
        loop_var: str,
        ctx: PipelineContext,
    ) -> None:
        self.f_sig = f_sig
        self.loop_var = loop_var
        self.ctx = ctx

    def transform_func_call(
        self, node: frog_ast.FuncCall
    ) -> Optional[frog_ast.Expression]:
        looked_up = _lookup_primitive_method(node.func, self.ctx.proof_namespace)
        if looked_up is not self.f_sig:
            return None
        if len(node.args) != 1:
            return None
        arg = node.args[0]
        # Match e[0] where e is the loop variable
        if (
            isinstance(arg, frog_ast.ArrayAccess)
            and isinstance(arg.the_array, frog_ast.Variable)
            and arg.the_array.name == self.loop_var
            and isinstance(arg.index, frog_ast.Integer)
            and arg.index.num == 0
        ):
            return copy.deepcopy(arg)
        return None
```

This task is substantial — budget for ~1–2 hours of implementation. After writing `_plan_rewrite` and `_execute_rewrite`, run the Task A2 test:

```
pytest tests/unit/transforms/test_map_key_reindex.py::test_basic_reindex -v
```

Iterate until it passes.

- [ ] **Step 3: Add the field-type rewrite**

Inside `_execute_rewrite`, after rewriting all write keys, update the map field's type from `Map<A, V>` to `Map<B, V>` where `B = f_sig.return_type`:

```python
for f in game.fields:
    if f.name == map_name:
        assert isinstance(f.type, frog_ast.MapType)
        f.type = frog_ast.MapType(
            copy.deepcopy(f_sig.return_type),
            copy.deepcopy(f.type.value_type),
        )
        break
```

- [ ] **Step 4: Run the basic test**

Run: `pytest tests/unit/transforms/test_map_key_reindex.py -v`

Expected: `test_basic_reindex` passes.

- [ ] **Step 5: Commit**

```bash
git add proof_frog/transforms/map_reindex.py
git commit -m "feat(transforms): MapKeyReindex basic rewrite"
```

---

### Task A6: Add iteration-loop positive test

**Files:**
- Modify: `tests/unit/transforms/test_map_key_reindex.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/transforms/test_map_key_reindex.py`:

```python
def test_reindex_with_scan_loop() -> None:
    _apply_and_expect(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[a] = s;
            }
            BitString<16>? Scan(TT.Image y) {
                for ([TT.Input, BitString<16>] e in M.entries) {
                    if (TT.Eval(e[0]) == y) {
                        return e[1];
                    }
                }
                return None;
            }
        }
        """,
        """
        Game G(T TT) {
            Map<TT.Image, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[TT.Eval(a)] = s;
            }
            BitString<16>? Scan(TT.Image y) {
                for ([TT.Image, BitString<16>] e in M.entries) {
                    if (e[0] == y) {
                        return e[1];
                    }
                }
                return None;
            }
        }
        """,
    )
```

- [ ] **Step 2: Run and iterate**

Run: `pytest tests/unit/transforms/test_map_key_reindex.py::test_reindex_with_scan_loop -v`

If this fails, the implementer likely needs to:
- Update the loop's `GenericFor.var_type` (element type `[TT.Input, BitString<16>]` → `[TT.Image, BitString<16>]`).
- Apply `_WrapKeyTransformer` to the loop body.

Iterate until it passes.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/transforms/test_map_key_reindex.py proof_frog/transforms/map_reindex.py
git commit -m "feat(transforms): MapKeyReindex handles iteration loops"
```

---

### Task A7: Add declines — non-deterministic `f`, non-injective `f`

**Files:**
- Modify: `tests/unit/transforms/test_map_key_reindex.py`, `proof_frog/transforms/map_reindex.py`

- [ ] **Step 1: Add the failing tests**

Append:

```python
def test_declines_when_f_not_injective() -> None:
    _apply_and_expect_unchanged(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
            BitString<16>? Lookup(TT.Input a) {
                if (TT.Eval(a) in M) { return M[TT.Eval(a)]; }
                return None;
            }
        }
        """,
        _ctx_with_primitive(_NON_INJECTIVE_PRIMITIVE),
    )


def test_declines_when_f_not_deterministic() -> None:
    _apply_and_expect_unchanged(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
            BitString<16>? Lookup(TT.Input a) {
                if (TT.Eval(a) in M) { return M[TT.Eval(a)]; }
                return None;
            }
        }
        """,
        _ctx_with_primitive(_NON_DETERMINISTIC_PRIMITIVE),
    )


def test_declines_when_key_used_as_raw_A() -> None:
    _apply_and_expect_unchanged(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
            TT.Input Leak() {
                for ([TT.Input, BitString<16>] e in M.entries) {
                    return e[0];
                }
                return 0;
            }
        }
        """,
    )
```

- [ ] **Step 2: Run and iterate**

Run: `pytest tests/unit/transforms/test_map_key_reindex.py -v -k declines`

The first two decline because `_find_candidate_f` requires `deterministic && injective`. The third declines because `e[0]` in `Leak` escapes a bare `return e[0];` — the `_WrapKeyTransformer`'s precondition check must reject this. Add a pre-pass that scans the loop body for bare `e[0]` (not inside `f(e[0])`).

Add to `map_reindex.py`:

```python
def _loop_body_has_bare_e0(
    loop: frog_ast.GenericFor,
    f_sig: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> bool:
    """True if the loop body uses ``e[0]`` outside of ``f(e[0])``."""
    loop_var = loop.var_name
    allowed_ids: set[int] = set()

    def _mark(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, frog_ast.FuncCall):
            looked_up = _lookup_primitive_method(n.func, ctx.proof_namespace)
            if looked_up is f_sig and len(n.args) == 1:
                a = n.args[0]
                if (
                    isinstance(a, frog_ast.ArrayAccess)
                    and isinstance(a.the_array, frog_ast.Variable)
                    and a.the_array.name == loop_var
                    and isinstance(a.index, frog_ast.Integer)
                    and a.index.num == 0
                ):
                    allowed_ids.add(id(a))
        return False

    SearchVisitor(_mark).visit(loop.block)

    def _bare(n: frog_ast.ASTNode) -> bool:
        return (
            isinstance(n, frog_ast.ArrayAccess)
            and isinstance(n.the_array, frog_ast.Variable)
            and n.the_array.name == loop_var
            and isinstance(n.index, frog_ast.Integer)
            and n.index.num == 0
            and id(n) not in allowed_ids
        )

    return SearchVisitor(_bare).visit(loop.block) is not None
```

Then in `_plan_rewrite`, when encountering a loop over `M.entries`, call `_loop_body_has_bare_e0`; if true, emit a near-miss and return None.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/transforms/test_map_key_reindex.py proof_frog/transforms/map_reindex.py
git commit -m "feat(transforms): MapKeyReindex declines on non-injective / raw-key uses"
```

---

### Task A8: Add near-miss instrumentation

Each precondition-failure site must emit a `NearMiss`. Sites (per design §3.2):

- `f` method not `deterministic`.
- `f` method not `injective`.
- A map read/write site has a key not wrapped in `f`.
- A loop body has a bare `e[0]` use.
- Write with complex (non-simple-variable) raw key.

- [ ] **Step 1: Add an `_emit_near_miss` helper and call sites**

Append to `map_reindex.py`:

```python
    def _emit_near_miss(
        self,
        ctx: PipelineContext,
        reason: str,
        location: frog_ast.SourceOrigin | None,
        variable: str,
        method: str | None,
    ) -> None:
        ctx.near_misses.append(
            NearMiss(
                transform_name=_NAME,
                reason=reason,
                location=location,
                suggestion=(
                    "MapKeyReindex fires only when every use of the map's "
                    "keys is wrapped in a single deterministic injective "
                    "primitive method f(·), and write keys are either f(·) "
                    "or a simple parameter variable."
                ),
                variable=variable,
                method=method,
            )
        )
```

Call it at:

1. `_find_candidate_f` — when a read key is not `f(·)` (emit against the most recent method iterated).
2. `_find_candidate_f` — when the candidate method isn't deterministic/injective.
3. `_plan_rewrite` — when a write key is not a simple variable or `f(·)`.
4. `_plan_rewrite` — when `_loop_body_has_bare_e0` fires.

Refactor `_find_candidate_f` to accept a side-channel for emitting near-misses, or return `(None, reason)` tuples. Simplest approach: store pending near-misses locally during discovery, then emit them if candidate discovery fails (gated on "at least one read site touches M" so we don't spam near-misses for maps unrelated to Pass 1).

- [ ] **Step 2: Add near-miss tests to `test_near_misses.py`**

Add to `tests/unit/transforms/test_near_misses.py`:

```python
from proof_frog.transforms.map_reindex import MapKeyReindex


def test_map_key_reindex_near_miss_non_injective():
    prim_src = """
    Primitive T(Set I, Set Y) {
        Set Input = I;
        Set Image = Y;
        deterministic Image Eval(Input x);
    }
    """
    game_src = """
    Game G(T TT) {
        Map<TT.Input, BitString<16>> M;
        Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
        BitString<16>? Lookup(TT.Input a) {
            if (TT.Eval(a) in M) { return M[TT.Eval(a)]; }
            return None;
        }
    }
    """
    prim = frog_parser.parse_string(prim_src, frog_ast.FileType.PRIMITIVE)
    ctx = PipelineContext(
        variables={}, proof_let_types=NameTypeMap(),
        proof_namespace={"T": prim, "TT": prim}, subsets_pairs=[],
    )
    game = frog_parser.parse_game(game_src)
    MapKeyReindex().apply(game, ctx)
    misses = [nm for nm in ctx.near_misses if nm.transform_name == "Map Key Reindex"]
    assert misses, "expected a near-miss for non-injective f"
    assert any("injective" in nm.reason for nm in misses)
```

Add similar tests for non-deterministic and bare-e0 cases.

- [ ] **Step 3: Run and iterate**

Run: `pytest tests/unit/transforms/test_near_misses.py -v -k map_key_reindex`

- [ ] **Step 4: Commit**

```bash
git add tests/unit/transforms/test_near_misses.py proof_frog/transforms/map_reindex.py
git commit -m "feat(transforms): MapKeyReindex near-miss instrumentation"
```

---

### Task A9: Integration smoke — Pass 1 in the full pipeline

- [ ] **Step 1: Run the full unit test suite**

Run: `pytest -q`

Expected: All tests pass. If not, a pass-ordering interaction has surfaced; diagnose by running `canonicalization-trace` on a minimal example.

- [ ] **Step 2: Run lint**

Run: `make lint`

Expected: Clean. If black/mypy/pylint complain, fix in place.

- [ ] **Step 3: Check the §4.1 reduction composes usefully**

From `extras/examples/engine-case-studies/lazy-rom-cca/` run:

```
python -m proof_frog canonicalization-trace <proof-file> <step-index>
```

on a step where Pass 1 should fire (the `R.Hash` scan on `PendingDecaps`). Confirm `MapKeyReindex` appears in the trace.

If the case-study proof file doesn't exist yet, skip this substep — Part C covers the integration tests.

- [ ] **Step 4: Commit (if any lint fixes were needed)**

```bash
git add -A
git commit -m "chore(transforms): MapKeyReindex lint cleanup"
```

---

## Part B — Pass 2: `LazyMapPairToSampledFunction`

### Task B1: Scaffold the new pass

**Files:**
- Modify: `proof_frog/transforms/random_functions.py`

- [ ] **Step 1: Add a no-op class**

Append to `proof_frog/transforms/random_functions.py` (after `LazyMapToSampledFunction`):

```python
_LAZY_MAP_PAIR_NAME = "Lazy Map Pair to Sampled Function"


class LazyMapPairToSampledFunction(TransformPass):
    """Generalize LazyMapToSampledFunction to a pair of maps with
    mutually-disjoint lazy-lookup guards (design §4).

    Preconditions (P2-1 .. P2-5 from design §4.2): see docstring of
    ``_try_rewrite``.
    """

    name = _LAZY_MAP_PAIR_NAME

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return game
```

- [ ] **Step 2: Register in pipeline**

Edit `proof_frog/transforms/pipelines.py` imports and insert after `LazyMapToSampledFunction()`:

```python
from .random_functions import (
    ...,
    LazyMapToSampledFunction,
    LazyMapPairToSampledFunction,
)
```

```python
    LazyMapToSampledFunction(),
    LazyMapPairToSampledFunction(),
    ExtractRFCalls(),
```

- [ ] **Step 3: Lint + tests**

Run: `make lint && pytest -q`

Expected: Both pass.

- [ ] **Step 4: Commit**

```bash
git add proof_frog/transforms/random_functions.py proof_frog/transforms/pipelines.py
git commit -m "feat(transforms): scaffold LazyMapPairToSampledFunction no-op"
```

---

### Task B2: Write positive-case test

**Files:**
- Create: `tests/unit/transforms/test_lazy_map_pair_to_sampled_function.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/transforms/test_lazy_map_pair_to_sampled_function.py`:

```python
"""Tests for the LazyMapPairToSampledFunction transform pass (design §4)."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.random_functions import LazyMapPairToSampledFunction
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
    return LazyMapPairToSampledFunction().apply(game, _ctx())


def _apply_and_expect(game_src: str, expected_src: str) -> None:
    got = _apply(game_src)
    expected = frog_parser.parse_game(expected_src)
    assert got == expected, f"\nGOT:\n{got}\n\nEXPECTED:\n{expected}"


def _apply_and_expect_unchanged(game_src: str) -> None:
    original = frog_parser.parse_game(game_src)
    got = LazyMapPairToSampledFunction().apply(original, _ctx())
    assert got == original


def test_basic_two_map_merge() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            BitString<16> QueryA(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
            BitString<16> QueryB(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M2[k] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> QueryA(BitString<8> k) {
                return F(k);
            }
            BitString<16> QueryB(BitString<8> k) {
                return F(k);
            }
        }
        """,
    )
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/unit/transforms/test_lazy_map_pair_to_sampled_function.py::test_basic_two_map_merge -v`

Expected: FAIL.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/transforms/test_lazy_map_pair_to_sampled_function.py
git commit -m "test(transforms): add failing LazyMapPairToSampledFunction basic case"
```

---

### Task B3: Build the guarded-lazy-idiom-pair matcher

Pass 2 reuses the single-map idiom matcher from `LazyMapToSampledFunction` (`_match_idiom_suffix`), but requires the guards to mention *both* maps (not just the map being written). The matcher, given a method and both map names `(M1, M2)`, recognizes the guarded-pair shape:

```
if (k in M1) { return M1[k]; }
else if (k in M2) { return M2[k]; }
V s <- V;
Mi[k] = s;   // i ∈ {1, 2}
return s;
```

Exact AST shape: a suffix of the method block starting at some statement index `j`, consisting of:

1. An `IfStatement` with two conditions and two blocks, where:
   - Condition 0 is `k in M1` (for some expression `k`), block 0 is `return M1[k];` (single statement).
   - Condition 1 is `k in M2`, block 1 is `return M2[k];`.
   - No else-block.
2. A `Sample` statement: `V s <- V;` (same `V` as the value type of both maps).
3. An `Assignment` to `Mi[k]` (for the same `k` and some `i ∈ {1, 2}`) with RHS `s`.
4. A `ReturnStatement(s)`.

- [ ] **Step 1: Implement the matcher**

Append to `proof_frog/transforms/random_functions.py`:

```python
@dataclass(frozen=True)
class _PairIdiomMatch:
    if_idx: int      # index of the if-statement in method.block.statements
    key_name: str    # parameter name k
    writes_to: str   # "M1" or "M2"


def _match_pair_idiom_suffix(
    method: frog_ast.Method,
    map1: str,
    map2: str,
    value_type: frog_ast.Type,
) -> Optional[_PairIdiomMatch]:
    """Recognize the 4-statement suffix shape described above."""
    stmts = method.block.statements
    if len(stmts) < 4:
        return None
    if_idx = len(stmts) - 4
    if_stmt = stmts[if_idx]
    if not isinstance(if_stmt, frog_ast.IfStatement):
        return None
    if len(if_stmt.conditions) != 2 or len(if_stmt.blocks) != 2:
        return None
    if if_stmt.has_else_block():
        return None
    # Extract "k in Mi" from condition i
    def _extract_in(cond: frog_ast.Expression, map_name: str) -> Optional[str]:
        if not (
            isinstance(cond, frog_ast.BinaryOperation)
            and cond.operator == frog_ast.BinaryOperators.IN
            and isinstance(cond.right_expression, frog_ast.Variable)
            and cond.right_expression.name == map_name
            and isinstance(cond.left_expression, frog_ast.Variable)
        ):
            return None
        return cond.left_expression.name

    k1 = _extract_in(if_stmt.conditions[0], map1)
    k2 = _extract_in(if_stmt.conditions[1], map2)
    if k1 is None or k2 is None or k1 != k2:
        return None
    k = k1

    # Each block: single `return Mi[k];`
    def _is_return_map_k(block: frog_ast.Block, map_name: str) -> bool:
        if len(block.statements) != 1:
            return False
        s = block.statements[0]
        if not isinstance(s, frog_ast.ReturnStatement) or s.expression is None:
            return False
        e = s.expression
        return (
            isinstance(e, frog_ast.ArrayAccess)
            and isinstance(e.the_array, frog_ast.Variable)
            and e.the_array.name == map_name
            and isinstance(e.index, frog_ast.Variable)
            and e.index.name == k
        )

    if not _is_return_map_k(if_stmt.blocks[0], map1):
        return None
    if not _is_return_map_k(if_stmt.blocks[1], map2):
        return None

    # Sample: V s <- V
    sample = stmts[if_idx + 1]
    if not isinstance(sample, frog_ast.Sample):
        return None
    if not isinstance(sample.var, frog_ast.Variable):
        return None
    s_name = sample.var.name
    if sample.the_type != value_type:
        return None

    # Assignment: Mi[k] = s
    asgn = stmts[if_idx + 2]
    if not isinstance(asgn, frog_ast.Assignment):
        return None
    target = asgn.var
    if not (
        isinstance(target, frog_ast.ArrayAccess)
        and isinstance(target.the_array, frog_ast.Variable)
        and target.the_array.name in (map1, map2)
        and isinstance(target.index, frog_ast.Variable)
        and target.index.name == k
    ):
        return None
    writes_to = target.the_array.name
    if not (isinstance(asgn.value, frog_ast.Variable) and asgn.value.name == s_name):
        return None

    # Return s
    ret = stmts[if_idx + 3]
    if not (
        isinstance(ret, frog_ast.ReturnStatement)
        and isinstance(ret.expression, frog_ast.Variable)
        and ret.expression.name == s_name
    ):
        return None

    return _PairIdiomMatch(if_idx=if_idx, key_name=k, writes_to=writes_to)
```

Notes: mirror the style of `_match_idiom_suffix` in the same file; reuse any helpers already there (check `random_functions.py` for `_match_idiom_suffix`).

- [ ] **Step 2: Commit**

```bash
git add proof_frog/transforms/random_functions.py
git commit -m "feat(transforms): LazyMapPairToSampledFunction idiom matcher"
```

---

### Task B4: Implement `apply` — pair discovery and rewrite

- [ ] **Step 1: Implement pair discovery**

In `LazyMapPairToSampledFunction.apply`:

```python
    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        # Find all Map<K, V> fields with the same K, V.
        map_fields = [f for f in game.fields if isinstance(f.type, frog_ast.MapType)]
        for i, m1 in enumerate(map_fields):
            for m2 in map_fields[i + 1 :]:
                if m1.type != m2.type:
                    continue
                rewritten = self._try_rewrite_pair(game, m1, m2, ctx)
                if rewritten is not None:
                    return rewritten
        return game

    def _try_rewrite_pair(
        self,
        game: frog_ast.Game,
        m1: frog_ast.Field,
        m2: frog_ast.Field,
        ctx: PipelineContext,
    ) -> Optional[frog_ast.Game]:
        assert isinstance(m1.type, frog_ast.MapType)
        assert isinstance(m2.type, frog_ast.MapType)
        key_type = m1.type.key_type
        value_type = m1.type.value_type

        # Gather per-method matches; require at least one method matches, and
        # every method that references M1 or M2 matches.
        matches: dict[str, _PairIdiomMatch] = {}
        for method in game.methods:
            if method.signature.name == "Initialize":
                # Disallow any reference to M1/M2 in Initialize (P2-2).
                if _references_map(
                    method, m1.name
                ) or _references_map(method, m2.name):
                    return None
                continue
            match = _match_pair_idiom_suffix(
                method, m1.name, m2.name, value_type
            )
            if match is None:
                # Must not reference either map elsewhere.
                if _method_references_maps(method, m1.name, m2.name):
                    return None
                continue
            # Validate no references to M1/M2 before the idiom suffix.
            for stmt in method.block.statements[: match.if_idx]:
                if _stmt_references_maps(stmt, m1.name, m2.name):
                    return None
            matches[method.signature.name] = match
        if not matches:
            return None
        return self._build_rewritten_game(
            game, m1.name, m2.name, key_type, value_type, matches
        )
```

Write helpers `_references_map(method, name)`, `_method_references_maps(method, m1, m2)`, `_stmt_references_maps(stmt, m1, m2)` modeled on the existing `_references_map` in `random_functions.py` (search for it — there's already one used by `LazyMapToSampledFunction`).

- [ ] **Step 2: Implement `_build_rewritten_game`**

```python
    def _build_rewritten_game(
        self,
        game: frog_ast.Game,
        m1_name: str,
        m2_name: str,
        key_type: frog_ast.Type,
        value_type: frog_ast.Type,
        matches: dict[str, _PairIdiomMatch],
    ) -> frog_ast.Game:
        new_game = copy.deepcopy(game)

        # 1. Replace the two map fields with a single Function field named F.
        #    Pick a fresh name (prefer "F", fall back if collision).
        f_name = _fresh_field_name(new_game, "F")
        new_fields = []
        seen = False
        for fld in new_game.fields:
            if fld.name in (m1_name, m2_name):
                if not seen:
                    new_fields.append(
                        frog_ast.Field(
                            frog_ast.FunctionType(
                                copy.deepcopy(key_type), copy.deepcopy(value_type)
                            ),
                            f_name,
                            None,
                        )
                    )
                    seen = True
                continue
            new_fields.append(fld)
        new_game.fields = new_fields

        # 2. Prepend `F <- Function<K, V>;` to Initialize (create if absent).
        sample_stmt = frog_ast.Sample(
            None,
            frog_ast.Variable(f_name),
            frog_ast.FunctionType(
                copy.deepcopy(key_type), copy.deepcopy(value_type)
            ),
        )
        init = next(
            (m for m in new_game.methods if m.signature.name == "Initialize"),
            None,
        )
        if init is None:
            init_sig = frog_ast.MethodSignature("Initialize", frog_ast.Void(), [])
            init = frog_ast.Method(init_sig, frog_ast.Block([sample_stmt]))
            new_game.methods = [init] + list(new_game.methods)
        else:
            init.block = frog_ast.Block(
                [sample_stmt] + list(init.block.statements)
            )

        # 3. Replace each matched method's suffix with `return F(k);`.
        for method in new_game.methods:
            match = matches.get(method.signature.name)
            if match is None:
                continue
            new_return = frog_ast.ReturnStatement(
                frog_ast.FuncCall(
                    frog_ast.Variable(f_name), [frog_ast.Variable(match.key_name)]
                )
            )
            method.block = frog_ast.Block(
                list(method.block.statements[: match.if_idx]) + [new_return]
            )
        return new_game


def _fresh_field_name(game: frog_ast.Game, base: str) -> str:
    existing = {f.name for f in game.fields}
    if base not in existing:
        return base
    i = 1
    while f"{base}{i}" in existing:
        i += 1
    return f"{base}{i}"
```

- [ ] **Step 3: Run and iterate**

Run: `pytest tests/unit/transforms/test_lazy_map_pair_to_sampled_function.py -v`

Iterate until `test_basic_two_map_merge` passes.

- [ ] **Step 4: Commit**

```bash
git add proof_frog/transforms/random_functions.py
git commit -m "feat(transforms): LazyMapPairToSampledFunction basic rewrite"
```

---

### Task B5: Negative tests — P2-1 through P2-5 failures

**Files:**
- Modify: `tests/unit/transforms/test_lazy_map_pair_to_sampled_function.py`, `proof_frog/transforms/random_functions.py`

- [ ] **Step 1: Add negative tests**

Append:

```python
def test_declines_missing_disjointness_guard() -> None:
    # The write to M1 is not guarded by "!in M2".
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            BitString<16> QueryA(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
            BitString<16> QueryB(BitString<8> k) {
                if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M2[k] = s;
                return s;
            }
        }
        """,
    )


def test_declines_mismatched_value_types() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<32>> M2;
            BitString<16> QueryA(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
        }
        """,
    )


def test_declines_cardinality_read() -> None:
    # P2-1: a cardinality read on one map disqualifies the pass.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            Int Count() { return |M1|; }
            BitString<16> Query(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
        }
        """,
    )


def test_declines_initialize_touches_map() -> None:
    # P2-2: a map assignment in Initialize disqualifies the pass.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            Void Initialize() { M1[0b00000000] = 0b0000000000000000; }
            BitString<16> Query(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
        }
        """,
    )
```

- [ ] **Step 2: Run and fix**

Run: `pytest tests/unit/transforms/test_lazy_map_pair_to_sampled_function.py -v`

Add any missing precondition checks (e.g., the matcher should already reject mismatched types, but the "cardinality read" check requires `_method_references_maps` to scan beyond the idiom suffix).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/transforms/test_lazy_map_pair_to_sampled_function.py proof_frog/transforms/random_functions.py
git commit -m "test(transforms): LazyMapPairToSampledFunction negative cases"
```

---

### Task B6: Add near-miss instrumentation and tests

- [ ] **Step 1: Emit near-misses**

In `_try_rewrite_pair` and its helpers, emit `NearMiss(transform_name=_LAZY_MAP_PAIR_NAME, …)` for each P2-* failure (mirror the `LazyMapToSampledFunction._emit_near_miss` helper from earlier in the same file — copy its shape).

Gate emissions: only emit if at least one of `M1, M2` pair is matched as a pair-idiom candidate in *some* method — otherwise the pair is unrelated to this pass and we shouldn't spam.

- [ ] **Step 2: Add near-miss tests to `test_near_misses.py`**

Add at least:
- Missing disjointness guard → near-miss with `reason` mentioning "disjointness" or "guard".
- Mismatched value types → near-miss with `reason` mentioning "type".
- Cardinality read / non-lazy use → near-miss with `reason` mentioning "outside the lazy-lookup idiom".

```python
from proof_frog.transforms.random_functions import LazyMapPairToSampledFunction


def test_lazy_map_pair_near_miss_cardinality():
    game_src = """
    Game G() {
        Map<BitString<8>, BitString<16>> M1;
        Map<BitString<8>, BitString<16>> M2;
        Int Count() { return |M1|; }
        BitString<16> Query(BitString<8> k) {
            if (k in M1) { return M1[k]; }
            else if (k in M2) { return M2[k]; }
            BitString<16> s <- BitString<16>;
            M1[k] = s;
            return s;
        }
    }
    """
    game = frog_parser.parse_game(game_src)
    ctx = PipelineContext(
        variables={}, proof_let_types=NameTypeMap(),
        proof_namespace={}, subsets_pairs=[],
    )
    LazyMapPairToSampledFunction().apply(game, ctx)
    misses = [
        nm for nm in ctx.near_misses
        if nm.transform_name == "Lazy Map Pair to Sampled Function"
    ]
    assert misses
```

- [ ] **Step 3: Run, iterate, and commit**

```bash
make lint && pytest -q
git add tests/unit/transforms/test_near_misses.py proof_frog/transforms/random_functions.py
git commit -m "feat(transforms): LazyMapPairToSampledFunction near-miss instrumentation"
```

---

## Part C — Integration with the case study

### Task C1: Verify `DecapsIter-IND-CCA.proof` passes

**Files:** (gitignored artifacts under `extras/`)

- [ ] **Step 1: Locate the proof**

Run: `ls extras/examples/engine-case-studies/lazy-rom-cca/proof/`

If the proof file doesn't exist, consult `docs/superpowers/plans/2026-04-20-lazy-rom-cca-case-study-proofs.md` for what to write. Tasks 0–3 of that plan have landed (artifacts exist); Task 4+ (the proof script itself) may need writing. Writing the full proof is covered by the case-study plan, not this one — if not yet written, stop here and note the dependency.

- [ ] **Step 2: Run `prove`**

Run: `python -m proof_frog prove extras/examples/engine-case-studies/lazy-rom-cca/proof/DecapsIter-IND-CCA.proof`

Expected: Proof verifies.

If it fails, use:
- `python -m proof_frog step-detail <proof> <step-index>` to see the canonical form of each side.
- `python -m proof_frog canonicalization-trace <proof> <step-index>` to see which transforms fired.

Iterate: does `MapKeyReindex` fire where expected? Does `LazyMapPairToSampledFunction` fire on the two-map pair in the reduction? If not, diagnose and fix.

- [ ] **Step 3: Commit fixes if any**

```bash
git add -A
git commit -m "fix(transforms): address §4.1 end-to-end integration issues"
```

---

### Task C2: Verify `HashedElGamal-KEM-IND-CCA.proof` passes

- [ ] **Step 1: Run `prove`**

Run: `python -m proof_frog prove extras/examples/engine-case-studies/lazy-rom-cca/proof/HashedElGamal-KEM-IND-CCA.proof` (adjust filename to match actual artifact).

Expected: Proof verifies.

- [ ] **Step 2: Iterate and commit**

```bash
git add -A
git commit -m "feat: §4.3 HashedElGamal CCA proof verifies end-to-end"
```

---

## Part D — Documentation

### Task D1: Update SEMANTICS.md

**Files:**
- Modify: `extras/docs/transforms/SEMANTICS.md`

- [ ] **Step 1: Add bullet to §9.3**

Open `extras/docs/transforms/SEMANTICS.md`, find the existing bullet under §9.3 (at line 610), and append a new bullet after it:

```markdown
- **Guarded two-map lazy lookup**: Two `Map<K, V>` fields accessed only through the lazy-sample idiom, with every write guarded by membership checks excluding both maps, and matching `V`-sampling, are equivalent to a single sampled `Function<K, V>` with each lazy-path occurrence rewritten as `F(k)`. Sound because the pair defines a single lazily-populated lookup table (see §6.5) partitioned across two storage locations, and the partition is adversary-invisible (§6.3).
```

- [ ] **Step 2: Add cross-reference to §6.5**

At the end of §6.5 (around line 416), append:

```markdown

See §9.3 for the multi-map generalization (guarded two-map lazy lookup).
```

- [ ] **Step 3: Commit**

```bash
git add extras/docs/transforms/SEMANTICS.md
git commit -m "docs(semantics): §9.3 guarded two-map lazy lookup entry"
```

---

### Task D2: Update the original lazy-ROM CCA design spec

**Files:**
- Modify: `docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md`

- [ ] **Step 1: Add forward-reference**

Open the file and find §5.4. Prepend:

```markdown
> **Elaborated and implemented in** `docs/superpowers/specs/2026-04-20-lazy-rom-cross-method-canonicalization-design.md` (§5.4 of that design covers the cross-method oracle-patching canonicalization via two new passes, `MapKeyReindex` and `LazyMapPairToSampledFunction`). The implementation plan is `docs/superpowers/plans/2026-04-20-lazy-rom-cross-method-canonicalization.md`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-04-20-lazy-rom-cca-engine-case-study-design.md
git commit -m "docs(spec): forward-reference §5.4 to cross-method canonicalization spec"
```

---

### Task D3: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add the assumption-game oracle convention**

Open `CLAUDE.md`, find the "Guidelines for creating FrogLang files" section. After the existing `Assumptions` bullet, add:

```markdown
- **Assumption-game oracle bodies should inline semantic contracts directly**: When writing an assumption game (e.g., `GapTest`) whose helper oracle witnesses a relation like "does `y = Eval(sk, x)`?", write the oracle body as the relation itself (`return y == T.Eval(sk, x);`), not as an opaque primitive call. This makes the contract visible to the engine's inlining + `LazyMapScan` / `MapKeyReindex` pipeline and avoids relying on the injective-call recognition fallback.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): assumption-game oracle body convention"
```

---

## Part E — Final verification

### Task E1: Full test suite and lint

- [ ] **Step 1: Run everything**

Run: `make lint && pytest -q`

Expected: All checks pass. `make lint` clean (black, mypy, pylint 10/10, tsc). All unit + integration tests pass.

- [ ] **Step 2: Confirm pipeline ordering**

Open `proof_frog/transforms/pipelines.py`. Visually confirm the order (design §5):

```
LazyMapScan(),
MapKeyReindex(),
LazyMapToSampledFunction(),
LazyMapPairToSampledFunction(),
ExtractRFCalls(),
```

- [ ] **Step 3: Status check**

Run: `git log --oneline feat/genericfor-map-array-typing | head -30`

Confirm commits from this plan are present in a logical sequence.

---

### Task E2: Update the original spec's "awaiting review" status

**Files:**
- Modify: `docs/superpowers/specs/2026-04-20-lazy-rom-cross-method-canonicalization-design.md`

- [ ] **Step 1: Flip status**

Change the frontmatter:

```markdown
**Status:** design, awaiting user review before implementation plan
```

to:

```markdown
**Status:** implemented; see `docs/superpowers/plans/2026-04-20-lazy-rom-cross-method-canonicalization.md`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-04-20-lazy-rom-cross-method-canonicalization-design.md
git commit -m "docs(spec): mark cross-method canonicalization design as implemented"
```

---

## Success criteria (from design §8)

- [x] Pass 1 (`MapKeyReindex`) lands with positive + negative tests (Tasks A1–A9).
- [x] Pass 2 (`LazyMapPairToSampledFunction`) lands with positive + negative tests (Tasks B1–B6).
- [x] `make lint` and `pytest` pass (Task E1).
- [x] SEMANTICS.md §9.3 gains one new bullet; §6.5 gains a cross-reference (Task D1).
- [x] §4.1 `DecapsIter-IND-CCA.proof` verifies end-to-end (Task C1).
- [x] §4.3 `HashedElGamal-KEM-IND-CCA.proof` verifies end-to-end (Task C2).
- [x] `CLAUDE.md` documents the assumption-game contract-inlining convention (Task D3).
- [x] Original 2026-04-20 spec's §5.4 gains a forward reference (Task D2).
