# Per-transform EasyCrypt tactic cache — Claude workflow

This document is for Claude sessions whose job is to close residual
`admit.` lines in a per-transform EasyCrypt export.

## When to read this doc

Read this whenever the user asks something like:

- "close the remaining admits in `<proof>`'s per-transform export"
- "derive cached tactics for the Topological Sorting hops"
- "fill in the tactic cache for X"
- "investigate the per-transform export of X"

Also read it before editing any `*.tactics.toml` sidecar.

## How the cache fits in

For each per-transform micro-lemma the exporter tries three layers in
order:

1. **Layer 1** — static / parametric canned tactic (built into Python).
2. **Layer 2** — sidecar cache lookup keyed on
   `(transform_name, canonical_text(game_before), canonical_text(game_after))`.
3. **Layer 3** — `admit.` plus a `(* tactic-cache miss ... *)` comment
   recording everything you need to derive a tactic.

Layer 2 is what you populate. The canonical text is what
`proof_frog.export.easycrypt_per_transform.canonical_form.canonical_text`
emits — exactly what shows up in the Layer-3 diagnostic. **Copy that
text verbatim into the sidecar.** Any whitespace or naming drift
silently turns a hit into a miss.

## Step-by-step workflow

```
1. Re-export the proof in per-transform mode:
   .venv/bin/python -c "from proof_frog.export.easycrypt_per_transform.exporter \
     import export_proof_file_per_transform; \
     open('/tmp/export.ec', 'w').write(
       export_proof_file_per_transform('<path-to-proof>'))"

2. List outstanding misses:
   grep -n "tactic-cache miss" /tmp/export.ec

3. For each miss:
   a. Read the (* tactic-cache miss ... *) comment. Extract:
      - transform name
      - sidecar path
      - expected game_before / game_after canonical text
   b. Locate the surrounding lemma by name and inspect the EC goal:
      grep -n "lemma micro_<i>_<side>_<k>" /tmp/export.ec
      bash scripts/easycrypt-goals.sh /tmp/export.ec <line>
      (or use the EC MCP if available)
   c. Iterate on a tactic until the goal closes. Standard moves:
        proc.
        swap{1} <pos> <delta>.       (* permutation hops *)
        rnd{1}; auto => />.          (* drop an unused independent sample *)
        sim.                          (* match call prefixes *)
      Per-clone distribution axioms are available as
        axiom <LetName>_<distr>_funi : is_funiform <distr>.
        axiom <LetName>_<distr>_ll   : is_lossless <distr>.
      (e.g. E1_dCiphertextSpace1_ll, E2_dCiphertextSpace2_funi).
   d. Validate the tactic by editing the generated .ec file in place
      and re-running EC:
        bash scripts/easycrypt.sh /tmp/export.ec
      Exit 0 with no parse / cannot-close errors before *any* admit
      below the one you just patched = success.
   e. Append a new [[entry]] to the sidecar TOML. **Format below.**

4. Re-export the proof. Each lemma you covered should now skip Layer 3
   and use your cached tactic.

5. Final validation: re-run scripts/easycrypt.sh /tmp/export.ec to
   confirm the chain still verifies end-to-end.
```

## Sidecar TOML entry format

Always copy `game_before` / `game_after` *verbatim* from the
`(* tactic-cache miss ... *)` comment. Indentation matters.

```toml
[[entry]]
transform = "Topological Sorting"
description = "hop 2R micro_2 — drops c2prime <$ d as unused (Bucket-2 sort-and-drop)"
added = "2026-05-23"

game_before = '''
proc enc(m : MessageSpace) : [CiphertextSpace1, CiphertextSpace2] = {
  var c1 : CiphertextSpace1;
  c1 <$ CiphertextSpace1;
  var c2prime : CiphertextSpace2;
  c2prime <$ CiphertextSpace2;
  var _r0 : E2.Key;
  _r0 <@ E2.KeyGen();
  var _r1 : E2.Ciphertext;
  _r1 <@ E2.Enc(_r0, m);
  return (c1, _r1);
}
'''

game_after = '''
proc enc(m : MessageSpace) : [CiphertextSpace1, CiphertextSpace2] = {
  var c1 : CiphertextSpace1;
  c1 <$ CiphertextSpace1;
  var _r0 : E2.Key;
  _r0 <@ E2.KeyGen();
  var _r1 : E2.Ciphertext;
  _r1 <@ E2.Enc(_r0, m);
  return (c1, _r1);
}
'''

tactic = '''
proc.
swap{1} 2 2.
rnd{1}; auto => />.
sim.
'''
```

Conventions:

- Use TOML literal multi-line strings (`'''`), not basic (`"""`); they
  don't interpret backslashes.
- Each block-field starts with a newline immediately after the opening
  delimiter (the writer in `tactic_cache.py` does this; mimic it).
- The `description` field is required by this workflow (the schema
  technically allows it to be optional). Cover: which hop / side / app
  index this is, what the diff conceptually changes, and any
  non-obvious rationale for the tactic choice.
- Use ISO dates (`YYYY-MM-DD`) in `added`.

## Partial cache hit (transform matches, pre matches, post doesn't)

Almost always means the engine pipeline has drifted and the entry is
stale. Check:

1. Is `canonical_text` itself different? (Run the new export and
   compare with the sidecar's `game_after`.)
2. If the transform's behavior really did change, update the entry's
   `game_after` (and probably the `tactic`); add a note in
   `description` about the drift.

If you're unsure whether the change is intentional, **stop and ask the
user** before mutating the sidecar.

## When to update vs. add an entry

- **Add** when the new `(transform, before, after)` triple is
  genuinely different from what's already cached.
- **Update** (delete the old entry; add the new one) when an existing
  entry's key matches the engine's new output exactly — except for a
  drift you've confirmed is the intended new behavior.

## When NOT to act unilaterally

Stop and confirm with the user before:

- Bumping `schema_version` in any sidecar (or in `tactic_cache.py`).
  That's a maintainer decision; it invalidates every existing entry.
- Modifying any canonicalization basis: `canonical_text`,
  `_normalize_for_ec`, or any code in `proof_frog/transforms/`.
- Promoting a recurring cache shape to a Layer-1 Python synthesizer.
  Wait until at least 5 distinct proofs hit the same recipe.

## Quick diagnostic check

Run `make check-tactic-cache` to see per-proof `used / orphan / missing`
counts for the whole `examples/` corpus. Use `--strict` (or pass it via
`PYTHONPATH=. .venv/bin/python -m proof_frog.export.easycrypt_per_transform.cache_report --strict`)
to exit nonzero if any proof has missing entries.
