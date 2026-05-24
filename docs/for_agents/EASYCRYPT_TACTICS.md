# EasyCrypt tactics for ProofFrog exports

This document covers two related concerns for an agent session working
on the EasyCrypt side:

1. **The per-transform tactic cache** — how to fill in cache entries
   for `admit.` lines emitted by the exporter (the main body).
2. **Running EasyCrypt** and known EC tactic gotchas (appendix sections
   at the end).

For interactive REPL workflow (which EC MCP tools to load and how to
drive `cli_step`), see [MCP_GUIDE.md](MCP_GUIDE.md#easycrypt-mcp).

## Per-transform tactic cache

The exporter always emits a per-transform canonicalization chain for each
interchangeability hop; this section covers how the tactic cache fills
in the micro-lemmas that chain produces.

## When to read this doc

Read this whenever the user asks something like:

- "close the remaining admits in `<proof>`'s EasyCrypt export"
- "derive cached tactics for the Topological Sorting hops"
- "fill in the tactic cache for X"
- "investigate the EasyCrypt export of X"

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
`proof_frog.export.easycrypt.canonical_form.canonical_text`
emits — exactly what shows up in the Layer-3 diagnostic. **Copy that
text verbatim into the sidecar.** Any whitespace or naming drift
silently turns a hit into a miss.

## Step-by-step workflow

```
1. Re-export the proof:
   .venv/bin/python -c "from proof_frog.export.easycrypt.exporter \
     import export_proof_file; \
     open('/tmp/export.ec', 'w').write(
       export_proof_file('<path-to-proof>'))"

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
`PYTHONPATH=. .venv/bin/python -m proof_frog.export.easycrypt.cache_report --strict`)
to exit nonzero if any proof has missing entries.

---

## Appendix: running EasyCrypt

EasyCrypt is invoked via `scripts/easycrypt.sh <file.ec>`. The script
runs EasyCrypt inside the `ghcr.io/easycrypt/ec-test-box:release`
Docker image. Exit 0 = type-check success; parse/type errors print to
stderr with a `[critical] [/work/<name>: line N (col-col)] ...` prefix.

**Sandbox gotcha (Claude Code).** The default sandbox blocks the Docker
socket, so any `bash scripts/easycrypt.sh ...` call must be run with
`dangerouslyDisableSandbox: true`. When the sandbox is disabled,
`$TMPDIR` resolves to the real macOS `/var/folders/...` path (not
`/tmp/claude-501/...`), and Docker Desktop's default shared-paths config
does not mount `/var/folders/...`. Put `.ec` files under a subdirectory
of the repo (e.g. `.ec-tmp/` at the repo root) so Docker can mount them
successfully, and clean that directory up afterward — it is not tracked.

Test fixtures: `tests/integration/test_easycrypt_export.py` has EC
type-check tests that are gated on a `_docker_available()` probe
(`docker info`), so they SKIP when Docker is not reachable, including
in the sandbox.

For interactive iteration, prefer the EC MCP tools (see
[MCP_GUIDE.md](MCP_GUIDE.md#easycrypt-mcp)). The MCP-relevant quirks of
`cli_step` are documented there too.

## Appendix: EC tactic gotchas (observed in this codebase)

### `eager proc` on abstract calls leaves an args-binding obligation

When using `eager call (: I ==> ...)` followed by `eager proc inv => //`
on an abstract adversary call like `A(O).distinguish(arg1, arg2)`,
EasyCrypt produces a side condition of the form

```
forall &1 &2, callsite-pre =>
  (s0{1} = s0{2} /\ s1{1} = s1{2}) /\ ...
```

where `s0`, `s1` are the formal parameters of `A.distinguish`. The
`forall` ranges over memories with **no constraint linking the formals
to the call-site args**, so even when `={glob G}` at the call site
implies `={arg1, arg2}` (e.g. both sides call with `(G.s0g, G.s1g)`),
smt cannot discharge the args equality.

**Why:** The EC `process_fun_abs` rule expects pre = `I /\ ={glob A,
A.f.params}`, but the formal-parameter equality is not auto-derived
from the call-site arg equality in this version of EC.

**Workarounds tried (in this codebase):**

- Wrapping `A.distinguish(args)` in a 0-arg helper proc `AdvW.d`
  clears the *outer* result-passing issue (so the outer eager call can
  thread `={res}` cleanly), but the abstract call's args-binding
  obligation reappears as soon as you `eager proc` into `AdvW.d`.
- `conseq` is not available on eager judgments.

The leftover admit can be discharged either with an EC patch that links
formals to call-site args, or by routing the proof through transitivity
to a 0-arg presentation where the args are read from globals at the
inside-the-adversary level — which requires defining a wrapper
*adversary*, not just a wrapper proc.

Canonical example:
`examples/applications/cfrg-hybrid-kems/easycrypt/LazyROTwoSeeded.ec`
(`lazyW_huniqW`).

### `byphoare` seq with a `1%r` bound auto-discharges that sub-goal

`byphoare`'s `seq N : (P) p1 q1 p2 q2 (R)`: when a bound is `1%r`, that
sub-goal is auto-discharged — don't write a `+ ...` block for it. So
`seq N : P p _ _ 0%r (R)` produces 3 visible sub-goals (R, p1, q_n),
not 4.

### Cloning `Dexcepted.TwoStepSampling`

Use `op dt _ <- dseed`, not `op dt <- (fun _ => dseed)` — beta-reduction
issues otherwise.

### `dexcepted_ll` requires `mu d P < 1%r`

For the `pseed = 1` case, the proof needs a separate trivial branch.
