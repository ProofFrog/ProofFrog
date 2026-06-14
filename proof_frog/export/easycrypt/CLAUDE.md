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
  template. Verified end-to-end by
  `examples/Proofs/SymEnc/ModOTP_INDOT.proof` (ec_compile OK).
- **Intermediate-game body emission** (in `exporter.py` intermediate-game loop
  + `module_translator.translate_intermediate_game` + `proof_translator.
  _resolve_intermediate_game`): a proof-local `Game` helper referenced as a
  bare `ParameterizedGame` step (`Hyb(q)`, `G_RandKey(K, F)`) is emitted as a
  concrete EC module implementing the *outer* theorem game's oracle type. Both
  single- and multi-oracle helpers are emitted. Module-typed (scheme-instance)
  params become EC functor params; non-module params (`Int q` compile-time
  indices) are dropped from the signature *and* the module expression, so
  `Hyb(q)` renders as a bare `Hyb`. The bare step's precondition is keyed off
  the outer game file (`={mL, mR}`), not `true`.
- **Concrete scheme for unconditional primitive-typed primaries** (in
  `exporter.py` scheme determination): `SymEnc E = ModOTP(q)` (a primitive-
  typed let bound to a concrete *scheme* ctor) with **no** `assume:` is emitted
  as a concrete `module ModOTP`, not an abstract `declare module E` -- the
  engine inlines the scheme into the flat states, so the wrapper-to-flat bridge
  needs a module `inline *` can unfold. Gated on `not proof.assumptions`
  (assumption proofs keep E abstract for the reduction). The scheme is resolved
  from the RHS ctor, not the declared interface type; the primary instance is
  keyed off the theorem-target let-name.
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
- **ISUV swap-aligned call-walker** (`chain_emitter._synth_isuv_walk`, wired in
  `_tactic_for`'s `Inline Single-Use Variables` canned branch): the whole-
  statement permutation checks (`_permutation_swaps`/`_rendered_state_swaps` ->
  `_ec_perm_swaps`) decline on an ISUV micro because inlining removes single-use
  assignments, so before/after differ in statement *count* (not a permutation).
  When the inlining also exposed an independent *different-module* call reorder
  (e.g. `KEM_PQ.encodesharedsecret` past `KEM_T.decaps`), the canned
  `proc; sp; wp; sim` runs but silently leaves `={res}` open (a 0-admit file EC
  rejects). This route aligns the right side's *calls only* to the left's call
  order with `swap{2}` (`_calls_only_align_swaps`; the count-differing det
  assigns stay for the walker's `wp`), then peels the calls bottom-up
  (`(wp; call (_: true))*`) and closes `skip => /#`. It fires only when an
  actual reorder exists (`swaps != []`), so it never preempts a working static
  `sim`; clean proofs are unaffected (a clean ISUV micro with a real call
  reorder would already be EC-rejected by the static `sim`, hence not clean).
  Same-*module* reorders take the deterministic functional-twin route below.
  Validated on `CK_expanded_Correctness` micro_0_left_2 (EC EXIT 0).
- **Deterministic-reorder synthesizer** (`chain_emitter._synth_det_reorder`,
  hooked at the head of `_tactic_for` so it preempts every swap-based route):
  when before/after differ by a deterministic reorder EC's `swap` can't do, it
  **functionalizes** every det call to its `ev_<m>` form (via the always-emitted
  `<M>_<m>_det` axioms) and routes `left ~ right` through two `ev`-functional
  **twin modules** `<state>_fdet` via 3-leg transitivity: `left ~ F_left`
  (top-down `seq 1 1` peel, program order — dodges the `exists*` freeze on
  ISUV-inlined call args), `F_left ~ F_right` (the *middle leg*,
  `_det_reorder_leg`), `F_right ~ right` (top-down peel). The gate
  `_needs_det_functional_reorder` (same call multiset + **each module's own
  probabilistic-call order preserved**) fires when **(a)** some declared
  module's own call order differs (same-module → EC rejects any `swap`, shared
  `glob`; any transform), or **(b)** for non-tuple transforms, the cross-module
  right→left calls-only alignment is **data-invalid**
  (`_calls_only_alignment_invalid`: a reordered call pushed past an assignment
  reading its result, e.g. `L.get` past the `kdf_in_d` concat — the
  `_synth_isuv_walk` swap EC rejects as "statements not independent"). The
  **middle leg** has two shapes: identical functionalized abstract-call order →
  the `(wp; call (_: true))*` peel; *reordered* abstract calls (the
  `Topological Sorting` shape — a same-module det reorder bundled with a
  **cross-module probabilistic** reorder, e.g. `KEM_T.KeyGen` past
  `KEM_PQ.Encaps`) → reorder `F_left`'s statements to exactly match `F_right`
  with `swap{1}` (`_ec_full_perm_swaps`, full-signature bubble sort; sound
  because both functionalized bodies are topological orderings of the same DAG,
  so each left-to-right move crosses only not-yet-placed independent statements)
  then `sim`. Tuple transforms (`allow_cross_module=False`) keep their
  tuple-walk, which aligns to the *inlined tuple* side — a valid direction
  (KEMPRF `K.decaps` past `F.evaluate`). Cross-module *valid* reorders and
  non-reorders decline, so clean proofs stay byte-identical. Determinism is
  threaded from the exporter as a per-declared-module `det_methods` map.
  Validated end-to-end on `CK_expanded_Correctness` / `UK_expanded_Correctness`
  (all 11 `Topological Sorting` micros close; `ec_compile` OK at 19 admits).
  **Caveat:** the `(wp; call)*` middle leg and `_synth_isuv_walk` both stall on
  `<$` samples (`wp` can't absorb a sample) — this is the open `CG`/`UG_expanded`
  wall (NIKE-group schemes); the fix is to make those routes sample-aware
  (swap+`sim`), not yet landed. **Dedup extension** (`Deduplicate Deterministic
  Calls`, the non-contiguous *rewire* shape — a duplicate det call like `L.get`
  removed and its survivor hoisted): the gate also fires when the call multisets
  *differ* by a deterministic deduplication (`_is_dedup_rewire`: prob calls
  untouched, det multiset shrank by genuine duplicates, **not** the contiguous-tail
  `_synth_dedup_det` shape — `_is_contiguous_dedup`). After functionalization the
  dedup'd det call is an `ev_*` assignment, so both twins hold the same abstract
  calls and the existing `(wp; call)*` middle leg closes them (the redundant
  `ev_*` assignment is absorbed by `wp`). Gated on `allow_cross_module` and the
  non-contiguous shape so clean `KEMPRF_Correctness` (contiguous-tail dedup via
  `_synth_dedup_det`, plus its tuple-walk) stays byte-identical. Validated on
  `CK`/`UK_expanded_Correctness` (19 -> 9 admits, `ec_compile` OK).
- **Pure cross-module reorder fallback in the `_REORDER_TRANSFORMS` branch**
  (`_tactic_for`): `_permutation_swaps` runs on the raw `app.game_before/after`
  ASTs, which are normalized differently from the rendered flat-state modules
  the lemma relates, so it can miss a reorder EC actually sees. When it declines,
  recompute from the rendered modules via `_rendered_state_swaps` →
  `_ec_perm_swaps`, gated by `_reorder_cross_module_safe` (every module's own
  call subsequence preserved → purely cross-module → EC-`swap`-safe; same-module
  reorders take the det route above). Closes the `L.get`-past-`KeyGen`
  `Topological Sorting` micros.
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

**Fast regression loop (do this — don't run the full suite).** A change here can
only affect proofs that *export*; the ~60 that fail before chain emission
(type/skeleton/import, FailedProof engine runs — several are the slowest proofs
in the corpus) are untouched. So:

- `scripts/ec_export_regression.sh` — re-exports just the ~44 exporting proofs
  **in parallel** and diffs the working tree against the committed (HEAD)
  baseline, printing exactly which `.ec` outputs changed. ~35s (cached baseline)
  vs **minutes** for a sequential full-corpus sweep. It stashes/restores your
  `proof_frog` changes to build the baseline; the baseline is cached per HEAD
  SHA so iteration runs don't re-stash.
- Compile **only the changed** proofs in EasyCrypt (`mcp ec_compile`, or
  `scripts/easycrypt.sh`). Byte-identical exports are guaranteed to compile
  identically, so unchanged ones need no EC run.
- Targeted tests only — NOT `pytest` (the full suite runs `test_proofs.py`,
  ~9 min of engine runs irrelevant to an export change):
  `pytest tests/unit/export tests/integration/test_easycrypt_export.py
  tests/integration/test_tactic_cache_orphan_check.py`. The
  `test_easycrypt_export.py` cases skip if Docker isn't available but exercise
  real EC compilation when it is.
- See
  [../../../docs/for_agents/EASYCRYPT_TACTICS.md](../../../docs/for_agents/EASYCRYPT_TACTICS.md)
  for the `.ec-tmp/` sandbox-mount workaround on macOS.

The full-corpus `make check-tactic-cache` (sequential, all 106) and the
EasyCrypt **dashboard** (compiles every `.ec`) are the heavyweight,
publish-the-numbers checks — run them before declaring a milestone, not on every
edit.
