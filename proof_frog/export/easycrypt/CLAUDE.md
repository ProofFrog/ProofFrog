# EasyCrypt exporter — dev instructions

This file is auto-loaded when editing under `proof_frog/export/easycrypt/`.

## Architecture (one screen)

The exporter translates a verified ProofFrog `.proof` into an EasyCrypt
`.ec` file by walking each interchangeability hop and emitting a
**per-transform canonicalization chain**: the same transforms that
fired on the FrogLang side become micro-lemmas on the EC side, each
discharging one step of the chain.

Key modules:

- `exporter.py` — top-level entry; orchestrates per-hop chain emission.
- `chain_emitter.py` — emits the per-transform chain for one hop.
- `canonical_form.py` — `canonical_text()` is the *normative* string
  used as the cache key. Whitespace/naming drift between this and the
  sidecar cache silently turns a hit into a miss.
- `tactic_cache.py` — sidecar TOML cache (Layer 2 of the three-layer
  resolution; see below).
- `parametric_tactics.py` — Layer 1 synthesizers.
- `transform_buckets.py` — groups transforms by EC tactic shape.
- `cache_report.py` — `make check-tactic-cache` driver.
- `proof_translator.py`, `module_translator.py`, `expr_translator.py`,
  `stmt_translator.py`, `type_collector.py`, `scheme_instances.py`,
  `ec_ast.py` — FrogLang→EC translation primitives.

## Three-layer tactic resolution

For each per-transform micro-lemma the exporter tries:

1. **Layer 1** — static / parametric canned tactic (Python).
   Promote a recipe to Layer 1 only after at least 5 distinct proofs
   hit the same shape.
2. **Layer 2** — sidecar cache lookup keyed on `(transform_name,
   canonical_text(game_before), canonical_text(game_after))`. The cache
   lives in `*.tactics.toml` sidecars next to the source proof.
3. **Layer 3** — `admit.` plus a `(* tactic-cache miss ... *)` comment
   recording everything needed to derive a tactic.

Workflow for adding cache entries (the agent-facing task that drives
most cache changes) is in
[../../../docs/for_agents/EASYCRYPT_TACTICS.md](../../../docs/for_agents/EASYCRYPT_TACTICS.md).

## Things to stop and ask before doing

- **Bumping `schema_version`** in any sidecar or `tactic_cache.py`
  invalidates every existing entry — maintainer-only decision.
- **Modifying the canonicalization basis** (`canonical_text`,
  `_normalize_for_ec`, or anything in `proof_frog/transforms/` that
  changes canonical output) silently invalidates cached entries.
  Coordinate with the user before changing.
- **Promoting a recurring cache shape to a Layer 1 synthesizer** — wait
  until at least 5 distinct proofs hit the same recipe.

## Sanity check

`make check-tactic-cache` reports per-proof `used / orphan / missing`
counts for the whole `examples/` corpus. Use `--strict` to exit nonzero
on missing entries. Run this after any change that affects which
tactics fire or the canonical-text basis.

## When changing the exporter, also

- Run the EC type-check integration tests (`tests/integration/test_easycrypt_export.py`)
  — they skip if Docker isn't available, but exercise real EC compilation
  when it is.
- Re-export at least one proof end-to-end and run `scripts/easycrypt.sh`
  on the result. See
  [../../../docs/for_agents/EASYCRYPT_TACTICS.md](../../../docs/for_agents/EASYCRYPT_TACTICS.md)
  for the `.ec-tmp/` sandbox-mount workaround on macOS.
