# Notes on `canonicalize_game()` vs `check_equivalent()`

`ProofEngine.canonicalize_game()` (added in `proof_engine.py`) is intended to replicate
what `prove` prints as "CURRENT" after its simplification pass. It omits two things that
`check_equivalent()` has, which can cause the output to differ.

---

## Omission 1: `self.variables` is empty → symbolic transformers are no-ops

`prove()` populates `self.variables` with integer-typed `let` bindings:

```python
# proof_engine.py, inside prove()
if isinstance(let.type, frog_ast.IntType):
    if let.value is not None:
        self.variables[let.name] = let.value
    else:
        self.variables[let.name] = Symbol(let.name)  # sympy symbol
```

`_capture_inline()` (in `web_server.py`) does not do this, so `self.variables` is `{}`
when `canonicalize_game()` runs. The two manipulators that use it:

- `SymbolicComputationTransformer(self.variables)` — folds arithmetic expressions
- `SimplifySpliceTransformer(self.variables)` — simplifies splice lengths

both become no-ops, leaving integer arithmetic unfolded.

**Fix (if needed):** In `_capture_inline()`, add the same integer-variable population
loop that `prove()` uses before calling `canonicalize_game()`.

---

## Omission 2: Step `assume` statements are not applied → `SimplifyRangeTransformer` never runs

Before each call to `check_equivalent()`, `prove_steps()` calls:

```python
self.set_up_assumptions(assumptions, current_step, next_step)
```

which populates `self.step_assumptions` from any `assume` annotations between two steps.
Inside the fixed-point loop, an `apply_assumptions` manipulator runs
`SimplifyRangeTransformer(self.proof_let_types, ast, assumption)` for each assumption,
which can eliminate range-dependent conditional branches.

`canonicalize_game()` omits this manipulator entirely. There is no per-step context
available in `_capture_inline()` to know which `assume` statements accompany the step
being inlined (they are interspersed as `frog_ast.StepAssumption` nodes in
`proof_file.steps` between the step and the next step).

**Fix (if needed):** Parse the assumption nodes from `proof_file.steps` that fall between
`step_index` and the following `Step`, call `engine.set_up_assumptions()`, and pass the
assumptions into `canonicalize_game()` (or have `canonicalize_game()` accept them as an
optional argument).

---

## When the outputs agree

For any proof step that:
- has no integer `let` bindings, **and**
- has no `assume` statements accompanying the step,

`canonicalize_game()` will produce output identical to what `prove` prints as "CURRENT".

---

## Relevant code locations

| Item | File | Lines |
|------|------|-------|
| `canonicalize_game()` | `proof_frog/proof_engine.py` | after `check_equivalent()` (~line 509) |
| `check_equivalent()` | `proof_frog/proof_engine.py` | ~306–507 |
| `self.variables` population | `proof_frog/proof_engine.py` | inside `prove()`, ~69–74 |
| `set_up_assumptions()` | `proof_frog/proof_engine.py` | ~241–304 |
| `_capture_inline()` | `proof_frog/web_server.py` | 64–115 |
