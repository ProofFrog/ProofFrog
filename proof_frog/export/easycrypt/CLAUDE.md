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
- `tactic_cache.py` — sidecar TOML cache (the *Cached* band of the
  automation ladder; see below).
- `transform_buckets.py` — groups transforms by EC tactic shape; holds
  the static `CANNED_TACTIC` bodies and the `PARAMETRIC_TACTIC`
  synthesizers (the *Synthesized* band of the ladder).
- `resolution.py` — the automation ladder: rung tokens, display names,
  and the `(* resolution: <rung> *)` tag the exporter emits at each
  resolved transform/hop so the dashboard can tally exactly how each
  closed.
- `cache_report.py` — `make check-tactic-cache` driver.
- **Scheme-statelessness foundation** (in `chain_emitter._synth_stateless_reorder`
  + `module_translator` helpers + gated emission in `exporter.py`): when a
  micro reorders two *abstract scheme calls* (e.g. `Inline Local Tuple
  Literal` over `Enc(KeyGen())`), EC can't `swap` them. The exporter emits
  per-method distribution ops + an `Ideal` sampling module + `declare axiom
  <E>_<m>_sem` statelessness specs (the probabilistic analogue of the
  `E_dec_det` determinism foundation), and routes the micro through a 4-hop
  transitivity over the all-`Ideal` instantiation. Gated: only emitted for
  schemes whose calls are actually reordered. Single declared module only so
  far. Design + extensions:
  `extras/docs/plans/in-progress/2026-06-01-scheme-statelessness-foundation.md`.
- **ModInt additive-group foundation** (in `type_collector` +
  `expr_translator` + `parametric_tactics.uniform_modint_tactic`):
  `ModInt<q>` translates to an abstract finite additive group
  (`modint_q` + uniform full `dmodint_q` + `add_q`/`sub_q` ops +
  round-trip/commutativity axioms). `+`/`-` on ModInt operands render to
  `add_q`/`sub_q`, and `Uniform ModInt Simplification` (`u +/- m -> u`)
  closes via an `rnd` bijection over add/sub — the additive analogue of
  the bitstring `xor` foundation. The GroupElem multiplicative analogue
  (`Uniform GroupElem Simplification`) is still INTERACTIVE; this is its
  template. Verified end-to-end by `examples/joy/.../ModOTPSecure.proof`.
- **Reorder swap synthesizers** (in `chain_emitter`): a micro lemma relates
  two *rendered* flat-state modules, which are normalized differently from
  the raw `app.game_before`/`app.game_after` (the engine stores a
  separately-canonicalized `game_before`; `Inline Single-Use Variables`
  leaves a nested `return` only the EC hoister flattens). `_permutation_swaps`
  runs on the raw ASTs; `_rendered_state_swaps` (the fallback for the
  multi-module `Bucket.CANNED` branch) recomputes the permutation from the
  rendered EC bodies via `_ec_perm_swaps`, which is what catches an
  abstract-call-past-independent-sample reorder (e.g. `E.keygen()` past
  `mPrime <$ d`) that the raw-AST check misses. A sample is glob-independent,
  so EC's `swap` accepts it (unlike two abstract calls, which need the
  stateless `Ideal` machinery). Template:
  `tests/integration/ec_templates/call_past_sample_swap.ec`.
- `proof_translator.py`, `module_translator.py`, `expr_translator.py`,
  `stmt_translator.py`, `type_collector.py`, `scheme_instances.py`,
  `ec_ast.py` — FrogLang→EC translation primitives.

## Automation ladder (how each resolution closes)

Every closed transform micro-lemma or whole-hop body is labelled with
one rung of a single ranked scale — *how much of the proof is
attributable to the exporter's own machinery*. The exporter emits a
machine-readable `(* resolution: <rung> *)` tag (see `resolution.py`)
at each site so the dashboard tallies the ladder exactly. Best-automated
first:

1. **Synthesized — static** (`synth-static`): a fixed canned tactic from
   `CANNED_TACTIC`; no per-instance logic. Promote a recipe here only
   after ≥5 distinct proofs hit the same shape.
2. **Synthesized — parametric** (`synth-param`): the tactic is *computed*
   from the hop's AST (a `PARAMETRIC_TACTIC` synthesizer, a swap
   sequence, a cascade). Still fully automatic — no human, no cache.
3. **Cached — with guidance** (`cached-guided`): closed from a sidecar
   entry that the exporter *scaffolded* (it emitted a `STRATEGY`/`TO
   CACHE` guided template that a human filled and we stored). Currently
   the whole-hop `transform = "<hop>"` entries.
4. **Cached — without guidance** (`cached-unguided`): closed from a
   sidecar entry the exporter did *not* scaffold — a human derived the
   tactic from scratch and we captured it. The per-transform cache hits.
5. **Admit — with guidance** (`admit-guided`): an open `admit.`, but the
   exporter emitted a targeted fill template for this exact hop (the
   unfilled form of rung 3 — cheap to promote).
6. **Admit — without guidance** (`admit-unguided`): an open `admit.`
   with only the generic `(* tactic-cache miss ... *)` comment.

Below the per-resolution ladder sits a seventh, **proof-level** state —
**Blocked** (`blocked`): the proof exports to `.ec` but EasyCrypt rejects
the result (a structural gap upstream of hop resolution, or a canned/synth
tactic that doesn't actually close its goal). The *exporter* can't detect
non-compilation, but the **dashboard measures it**: `easycrypt_dashboard.py`
compiles every exported `.ec` in EasyCrypt, and a proof is `clean` only if
EasyCrypt accepts it AND it is admit-free. "0 admits" alone is not clean —
a canned tactic that silently fails to close its goal (without emitting
`admit.`) yields a 0-admit file EasyCrypt still rejects (this is how
`2_14_Forward`/`2_14_Backward` were once miscounted clean). The dashboard
fails loudly if EasyCrypt/Docker is unavailable rather than emit unverified
counts.

Resolution order in the emitter is rung 1 → 2 → (3/4 via the cache) →
(5/6 admit). **Automated = rungs 1–4** (no open hole); **Open = rungs
5–6**; **Blocked = rung 7**. The sub-splits (static-vs-parametric,
guided-vs-unguided) sit in different closure bands, so this is one
ladder rather than two axes.

Workflow for adding cache entries — i.e. promoting a rung-5 *guided
admit* to a rung-3 *cached-guided*, or filling a rung-6 admit into a
rung-4 *cached-unguided* — is in
[../../../docs/for_agents/EASYCRYPT_TACTICS.md](../../../docs/for_agents/EASYCRYPT_TACTICS.md).

## Things to stop and ask before doing

- **Bumping `schema_version`** in any sidecar or `tactic_cache.py`
  invalidates every existing entry — maintainer-only decision.
- **Modifying the canonicalization basis** (`canonical_text`,
  `_normalize_for_ec`, or anything in `proof_frog/transforms/` that
  changes canonical output) silently invalidates cached entries.
  Coordinate with the user before changing.
- **Promoting a recurring cache shape (rung 3/4) to a `synth-static` /
  `synth-param` tactic (rung 1/2)** — wait until at least 5 distinct
  proofs hit the same recipe.

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
