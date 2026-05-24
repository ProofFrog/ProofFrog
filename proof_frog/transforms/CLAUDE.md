# Engine / transforms — dev instructions

This file is auto-loaded when editing under `proof_frog/transforms/`.

## Soundness mindset

A transform is sound only if, for every input game, its output is
*interchangeable* with the input under FrogLang semantics — i.e. induces
the same distribution over all possible adversary outputs across every
sequence of oracle calls. The bar is high.

- Be skeptical. Try to construct an adversarial sequence that
  distinguishes the input from the output before convincing yourself
  the transform is sound.
- The full FrogLang semantics reference is at
  [../../docs/for_agents/FROGLANG_REFERENCE.md](../../docs/for_agents/FROGLANG_REFERENCE.md).

## When you add or modify a `TransformPass`

1. **Tests** — add both positive (transform fires when it should) and
   negative (transform does NOT fire on adjacent unsound shapes) unit
   tests in `tests/unit/transforms/`.

2. **Near-miss instrumentation** — at each key precondition-failure
   point where the transform *almost* fires but doesn't, append a
   `NearMiss` to `ctx.near_misses` (from `PipelineContext`). This feeds
   the diagnostic engine's explanation of why a hop didn't validate.
   Add unit tests for near-miss reporting in
   `tests/unit/transforms/test_near_misses.py`.

3. **Engine limitation registry** — if the transform has known gaps
   (cases it ought to handle but doesn't), update the registry in
   `proof_frog/diagnostics.py`.

4. **Public transform index** — update `docs/for_agents/TRANSFORMS.md`
   (the link-free capability list, shipped via `download-examples`) with
   the new pass name and a one-line description.

5. **Pipeline placement** — `pipelines.py` controls ordering of
   `CORE_PIPELINE` (fixed-point loop) and `STANDARDIZATION_PIPELINE`
   (one-shot after convergence). Think about ordering effects before
   inserting a new pass.

## Verifying changes mid-session

The `prooffrog` MCP server is a long-running process and **caches the
engine code at startup**. After editing under `proof_frog/transforms/`
(or any other engine module), do not trust MCP `prove` / `check` /
`get_step_detail` results. Use the CLI instead:

- `.venv/bin/python -m proof_frog prove <file>`
- `.venv/bin/python -m proof_frog step-detail <file> <step_index>`
- `.venv/bin/python -m proof_frog canonicalization-trace <file> <step_index>`
- `.venv/bin/python -m proof_frog step-after-transform <file> <step_index> "<TransformName>"`

All accept `--json`/`-j`. With an editable install (`pip install -e .`)
the CLI picks up `.py` edits without reinstalling. See
[../../docs/for_agents/MCP_GUIDE.md](../../docs/for_agents/MCP_GUIDE.md)
for the full CLI-fallback table.

## Sanity check

Before declaring a transform done, run the full integration suite:

```
.venv/bin/python -m pytest tests/integration/test_proofs.py
```

This re-runs every `examples/**/*.proof` and is the best protection
against unsoundness regressions that pass unit tests but break a real
example.
