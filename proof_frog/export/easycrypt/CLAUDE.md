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
  `expr_translator` + `parametric_tactics.uniform_modint_tactic` +
  `exporter.type_of` FieldAccess): **migrated to EC stdlib clones (2026-06-29)**,
  replacing the former uninterpreted-ops+axioms backend. Group + ring laws are now
  *derived* from `Group.ec`/`ZModP.ec`, not axiomatized (principle 4's ideal). The
  one new assumed axiom is `ge2_p : 2 <= <modulus>` (ZModRing's own
  well-definedness side-condition) — registered + justified in the axiom-soundness
  plan.
  - **`GroupElem<G>` -> `clone CyclicGroup as <G>`** (not `import`ed — every op is
    qualified, since the group's `( * )` and the ring's `( * )` would otherwise
    collide). Type `<G>.group`; `G.generator`/`G.identity` -> `<G>.g`/`<G>.e`;
    `*`/`/` -> `<G>.( * )`/`<G>.( / )` (rendered prefix: `<G>.( * ) a b`).
  - **Exponent ring, gated on the per-proof `requires <G>.order is prime;`**
    (threaded as `prime_group_names` -> `TypeCollector.is_prime_group`):
    *general path* (default) clones `ZModP.ZModRing as <G>_Exp with op p <- <G>.order`
    (exp type `<G>_Exp.zmod`, power `<G>.( ^ ) base (<G>_Exp.asint exp)` via the base
    integer power); *prime path* (declaring proofs only) emits
    `axiom <G>_prime_order : IntDiv.prime <G>.order` + `clone <G>.PowZMod as <G>_P` +
    `clone <G>_P.FDistr as <G>_FD` (exp type `<G>_P.ZModE.exp`, ergonomic field power
    `<G>_P.( ^ ) base exp`). Only `HashedElGamalKEM_INDCCA` declares it today.
  - **`ModInt<q>` dual role** (`type_collector._group_order_modulus_alias`): a
    `ModInt<<G>.order>` *aliases* the group's exponent ring (no independent clone); a
    standalone `ModInt<q>` gets its own `clone ZModP.ZModRing as ModInt_q with op p
    <- <q>` (type `ModInt_q.zmod`) — the modulus is *bound* to the FrogLang
    expression so the ring is genuinely Z_<q>, not over an unrelated abstract `p`. `+`/`-`/`*`/zero render to `<T>.( + )`/`( - )`/`( * )`/`zero`;
    the uniform distr is `<T>.DZmodP.dunifin` (group element samples use a direct
    `duniform <G>.elems`). `Uniform ModInt Simplification` closes via an `rnd`
    bijection whose cancellation is now a derived `ring` fact (discharge
    `... smt(<distr>_fu <distr>_funi @<ring-theory>)`), with the 3 former round-trip
    axioms dissolved into `ring` lemmas.
  - **Verified:** `ModOTP_INDOT` -> clean (0 admits) and `ElGamal_Correctness` ->
    EC-accepted at 1 admit (⚠), both on the stdlib backend (`ec_compile` OK).
    Op-name helpers (`group_*_name_for`, `add`/`sub`/`modint_mul`/`modint_zero_name_for`,
    `ring_theory_of`, `group_power_for`) derive the qualified op by stripping the EC
    type suffix (`.group`/`.zmod`/`.exp`). Non-group/modint proofs are byte-identical
    (all emission gated on group/modint registration). The `requires Group ZModP List`
    preamble is added only when `has_stdlib_group_or_modint()`. The DDH/ElGamal
    MultiChal family still needs the separate `Group`-parameterized assumption-game
    skeleton (Phase B, `exporter.py:635`/`:759`) to export at all. Three general
    emission fixes that landed with the old GroupElem foundation remain: `==`/`!=` ->
    `=`/`<>`; a `Sample` with no type annotation takes the sampled variable's type;
    `type_of` types `G.generator`/`G.identity` as `GroupElem<G>`.
- **Random-function foundation for `Function<A,B>`** (in `type_collector`
  `translate_type`/`distr_for`/`emit` + `expr_translator` FuncCall +
  `module_translator._ec_field_name`/`_field_renames_for`): a game field
  `RF <- Function<A,B>` (sampled as a whole random function, applied as
  `RF(x)`) translates to EC's native arrow type `A -> B`; the sample draws
  from an abstract uniform distribution over the finite function space
  (`op dfun_<dom>_to_<codom> : (A -> B) distr` + `_ll`/`_fu`/`_full` axioms,
  emitted *after* the domain/codomain bitstring `type` decls so the arrow's
  operands are in scope), and `RF(x)` renders as application `RF x`. The
  three axioms are the standard facts about `dfun (fun _ => dB)` (EC's
  `MUniFinFun`), so the foundation is sound and in principle derivable —
  register it with the axiom-soundness audit. Because EC module-global
  variables must be lowercase-initial, an uppercase field name like `RF` is
  renamed (`RF` -> `rF`, first char only) at every decl + reference site via
  a `field_renames` map threaded through `_translate_method` into the
  expression translator; lowercase fields are unchanged, so every existing
  export is byte-identical. Unblocks the 12 KDF-PRF track-A INDCCA proofs to
  *export* (the 4 CG/UG `_T` variants then hit the separate `Variable: D`
  ROM wall; the rest advance to a theory-mode `concat` structural blocker —
  both out of scope here). Validated: foundation + rename parse and
  typecheck in EC (`dfun` op accepted); export regression byte-identical.
- **Subset-carrier concatenation** (in `type_collector.register_subset_carrier`
  / `bitstring_carrier_type` + `expr_translator._bitstring_type_of` + an early
  `exporter.py` pass): a scheme `requires X subsets/== BitString<n>` makes an
  abstract carrier set `X` (e.g. GHP18's `KEM1.PublicKey` = `PK1Space`)
  bitstring-like. The engine inlines the `BitString<n> b = x;` coercion into the
  chain flat states, so a `||` operand surfaces *carrier-typed* — `pk1 :
  PK1Space`, not `bs_pk1len` — and the old `||` path emitted EC's boolean `||`
  ("no matching operator ||"). `_bitstring_type_of` now maps a carrier operand
  to its `BitString<n>` and renders `concat_*`; nested `||` is summed
  *structurally* (the engine's recorded type for an inlined concat node can be a
  single carrier, not the summed bitstring). The carrier→bitstring map is seeded
  on `top_types` *before* chain emission (an emission-neutral pass — it registers
  no bitstring type, so `top_types.emit()` order is unchanged); the late
  `requires` pass that emits `type bs_n = X.` runs *after* the flat states
  render, too late for the translator. Cleared GHP18's §2.3 wall: the proof now
  type-checks fully (boolean `||` gone). Regression: only the 3 KEMCombiner
  proofs re-export.
- **GHP18_Correctness → clean (three coordinated fixes; the last correctness
  `⛔`).** After the subset-carrier wall fell, GHP18 EC-rejected; three fixes
  take it to EC-accepted, 0 admits:
  1. **`_calls_only_align_swaps` dependency validation.** Its coarse-signature
     bubble (`_ec_perm_swaps`) over the *whole* exec list slid a call to the
     front (valid) and then bubbled an independent assignment back across the
     call's result write to "match" the target layout — a dependency-crossing
     `swap{2}` EC rejects ("statements not independent"). The coarse swaps are
     now dependency-validated (`_swaps_dep_valid`); on failure they are
     recomputed by `_calls_only_move_swaps`, which slides *only the calls* left
     to their slots (assignments stay; the walker's `wp` absorbs them) and
     validates each move with `_ec_indep`. A clean proof's swaps already
     validate, so it keeps the coarse result byte-identical. Fixed the
     `R_KEM2` reduction-side ISUV micro `micro_2_right_2_fwd` (was emitting a
     spurious second `swap{2} 3 -1`).
  2. **`Inline Multi-Use Pure Expressions` + `Extract Repeated Tuple Access`
     added to `_PLUMBING_REWRITE_TRANSFORMS`.** Both keep the abstract-call
     sequence identical and differ only by deterministic assignment plumbing
     (a pure `label <- concat ...` inlined into its two `F.evaluate` use sites;
     a repeated `v.\`1` extracted to a `__cse_*` local). The functional-twin
     identical-order `(wp; call)*` middle leg discharges them — `wp` collects
     the dropped/added assignment and `skip => /#` equates the substituted
     expressions. Closed 6 of GHP18's 7 admits.
  3. **`type_of` handles `ArrayAccess` (tuple projection).** GHP18's `hop_0`
     flat states inline a tuple projection (`sk[2]` where `sk : SK1Space *
     SK2Space * PK1Space * PK2Space`) directly into a `||` concat operand, so
     the concat detector (`_bitstring_type_of`) called `type_of` on an
     `ArrayAccess` and hit `NotImplementedError` → the whole body fell back to
     `return witness;` → the hop chain was unrenderable → `admit`. The
     exporter's `type_of` factory now types `t[i]` as the i-th component of
     `t`'s `ProductType`. Cleared the last admit (`hop_0`).

  Regression: only `GHP18_Correctness` re-exports (byte-identical clean set);
  `ec_compile` OK at 0 admits.
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
  **Sample-aware peel (2026-06-13).** The middle leg, `_synth_isuv_walk`, and
  `_synth_tuple_walk` no longer stall on `<$` samples: `_backbone_peel` walks the
  call+sample backbone tail-to-front, coupling a sample with `rnd` and a call with
  `call (_: true)` (sample-free micros stay byte-identical). The same-callee det
  reorder (`NG.Encode(v8)`/`NG.Encode(v5)` — `Stabilize Independent Statements`) is
  caught by `_det_call_sigs` (per-module `(callee,args)` order, det calls only).
  `_det_topdown_leg` now seeds its `seq` invariant with the **proc parameters**
  (`={pk,sk}`) — a det call consuming a parameter (`K.decaps(sk,ct)`) otherwise
  leaves an undischarged `forall &1 &2`. `Inline Single-Use Variables` is in
  `_PLUMBING_REWRITE_TRANSFORMS` so its count-differing inlined-tail shape routes
  here instead of the canned `(sp;wp;sim)||sim` (which ran but left the goal open).
  Verified: KEMPRF / CK_expanded / UK_expanded / GeneralDoubleSymEnc /
  ChainedEncryptionSecure all still `ec_compile` OK. A same-distribution *sample
  reorder* (two `<$` seeds swapped by `Topological Sorting`) must NOT take the
  identity-`rnd` peel: `_call_sample_backbone` tags each sample by its bound
  variable, so a reordered-sample backbone differs and the leg falls to the
  `swap`+`sim` branch (samples are glob-independent, so EC `swap` reorders them
  into position). This route is emitted but **its EC compilation is not yet
  confirmed** (CG7 export not compiled) — the next thing to verify. **Dedup
  extension** (`Deduplicate Deterministic
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
  **Plumbing-rewrite extension** (`Collapse Single-Index Tuple Access`,
  `Expand Tuples` — a deterministic tuple-projection/construction rewrite that
  keeps the *whole* abstract-call sequence identical, e.g. `t <@ KeyGen(); x =
  t[0]` <-> `r <@ KeyGen(); t = r[0]; x = t`): there is **no call reorder at
  all** (`bc == ac`), so the swap routes have nothing to do and the
  single-module tuple-walk / stateless route does not apply — in a
  multi-declared-module body these fall through to `admit`. The gate also fires
  when `allow_plumbing and bc == ac` and the bodies differ; after
  functionalization both twins hold the same probabilistic calls in the same
  order, so the **identical-order `(wp; call)*` middle leg** discharges the
  plumbing difference (`wp` absorbs the extra projection assignments,
  `skip => /#` closes the nested concat args). `allow_plumbing` is set only for
  `_PLUMBING_REWRITE_TRANSFORMS` in a multi-module body (`len(flat_params) > 1`),
  so single-module clean proofs keep their tuple-walk byte-identical. Validated
  on `CK`/`UK_expanded_Correctness` (**9 -> 0 admits, `ec_compile` OK — both
  flip to clean**).
- **Pure cross-module reorder fallback in the `_REORDER_TRANSFORMS` branch**
  (`_tactic_for`): `_permutation_swaps` runs on the raw `app.game_before/after`
  ASTs, which are normalized differently from the rendered flat-state modules
  the lemma relates, so it can miss a reorder EC actually sees. When it declines,
  recompute from the rendered modules via `_rendered_state_swaps` →
  `_ec_perm_swaps`, gated by `_reorder_cross_module_safe` (every module's own
  call subsequence preserved → purely cross-module → EC-`swap`-safe; same-module
  reorders take the det route above). Closes the `L.get`-past-`KeyGen`
  `Topological Sorting` micros.
- **Sample-reorder closes for the functional-twin and swap routes** (three
  coordinated fixes; validated end-to-end on `UG_seedbased_Correctness` →
  clean). When a reorder, after functionalizing every det call, leaves the two
  twins differing *only* in the order of their `<$` samples (probabilistic-call
  subsequence identical), the existing middle-leg routes break: `_ec_full_perm_swaps`
  chokes on the `_rN` renaming a reorder drags in (two calls that swap program
  order get their auto-numbered result vars reassigned), and the coarse swap
  routes can't tell two same- or distinct-distribution samples apart.
  - `_det_reorder_leg` (functional-twin middle leg) gains a fallback after
    `_ec_full_perm_swaps` declines: `_sample_reorder_swaps` emits `swap{1}`s
    reordering the samples (a sample is glob/data-independent of everything
    before it, so hoisting it up is always EC-valid), then the existing
    `_backbone_peel` discharges the now-common backbone — `wp` dissolves the
    renamed deterministic locals, so the rename never surfaces. Gated on
    `allow_sample_reorder` (set only when functionalization actually turned a det
    call into an `ev` assignment), so pure-probabilistic bodies keep their
    simpler swap close. Tripwire:
    `tests/integration/ec_templates/sample_reorder_twin.ec`. Closes the
    `micro_*_right_9` `Topological Sorting` micros where a same-module call order
    also differs.
  - `_needs_det_functional_reorder` gains a clause routing a *cross-module*
    reorder through the twins when its only probabilistic-backbone difference is
    sample order AND a rename is present (detected as `_ec_full_perm_swaps` on
    the rendered bodies declining) AND there are det calls to functionalize.
    Rename-free reorders keep their shorter swap close (EC `swap` aligns them and
    `sim` finishes). Closes the `Stabilize Independent Statements` micro
    (`derivekeypair` shifting across the `NG` calls with `_r0`/`_r1` swapped).
  - The `_REORDER_TRANSFORMS` swap branch now *validates* its swaps against the
    rendered bodies (`_swaps_align_rendered` / `_swaps_realign` via `_reorder_sig`
    — samples by distribution, calls by callee, rename-tolerant) before trusting
    them: the raw-AST `_permutation_swaps` can return non-empty-but-wrong swaps
    (raw vs rendered normalization mismatch), and `_rendered_state_swaps`'s coarse
    `_ec_perm_swaps` conflates distinct-distribution samples. Both now require the
    swaps to actually realign; `_rendered_state_swaps` falls through to the
    full-signature sort (which distinguishes the samples by var) when coarse
    doesn't realign. Closes the no-rename `micro_12_right_9` sample swap.
  - **Rename-masked assign shape in `_reorder_sig`** (the validation signature
    `_swaps_realign` uses): it previously collapsed *every* `Assign` to
    `("assign",)`, so a swap sequence that left two distinct assigns
    (`ct2 <- _tup_2.\`2` vs `_tup_1 <- (...)` vs `ct1 <- _tup_1.\`1`) mis-ordered
    still validated — `sim` was then left open (a 0-admit file EC rejects). Now
    an assign's signature includes its **rename-masked RHS shape** (`_mask_idents`
    replaces every identifier run with `ID`, keeping punctuation/indices/arity):
    finer than before (distinguishes `ID.\`1` / `ID.\`2` / `(ID, ID, ID)`) yet
    still `_rN`-rename-tolerant (both sides mask alike). Strictly safe — it can
    only *reject* a genuinely-misaligned swap set, falling back to the exact
    full-signature sort (`_ec_full_perm_swaps`, dep-validated); a correct swap set
    still passes (moved == right ⇒ equal masked shapes). Fixed GHP18's
    `Topological Sorting` `micro_2_left_3` (raw `_permutation_swaps` returned only
    2 of the 3 needed swaps and coarse-validated). Regression: `UK_seedbased`
    gains one extra dep-valid `swap` (its `micro_0_left_13` was similarly
    under-swapped; still `ec_compile` OK).
- **Marginal partial-split `Split Uniform Samples` synthesizer**
  (`parametric_tactics._marginal_split_helpers`, reached from the
  `_has_module_call_tail` branch of `split_uniform_samples_tactic`): the
  PRG-stretch shape where one big sample `orig <$ d_RES` is consumed *only* via two
  non-overlapping slices that feed a **complex downstream tail** (module calls +
  assignments, not a return-concat), and `|L| + |R| < |RES|` (tail-gap). The simple
  `_partial_split_helpers` Mid/Aug `query` templates can't capture the long tail.
  Instead this route builds `Mid`/`Aug` as **surgical copies of the actual
  flat-state modules** — the whole tail rendered verbatim by a `render_state`
  callback `chain_emitter` passes in (a closure over `_render_flat_state`), with
  only the sampling prefix patched: `Mid` = whole-side state with `orig <$ d_RES`
  replaced by `a <$ d_L; b <$ d_R; _gap <$ d_GAP; orig <- concat3 a b _gap`;
  `Aug` = two-sample state with a dead `_gap <$ d_GAP`. It chains
  `whole ~ Mid ~ Aug ~ two-sample`: `left_to_mid` = `rndsem*{2}` + `rnd`-identity
  bijection + `d_RES_split3` (couple the one big sample to the 3-sample form), then
  `sim` the identical tail; `mid_to_aug` = `seq` establishing the `slice_concat3`
  round-trips `slice_L orig{1} = a{2}` / `slice_R orig{1} = b{2}`, then peel the
  whole tail call-by-call (`(wp; (call (_:true) || rnd))*` — `sim` can't use a
  relational fact to equate the two slice-consuming head calls' args, but the
  generic peel discharges them from the invariant); `aug_to_right` = drop the dead
  gap via `rnd{1}` + `d_GAP_ll`, then `sim`. `reversed_dir` prepends `symmetry.`.
  Common deterministic prefix (e.g. `L.get()`) is peeled with `seq c c; first sim`.
  Only fires where the old code admitted, so clean proofs stay byte-identical;
  mid-gap and reversed orientation (`swap_split`) fall back to admit. Validated:
  `CK_seedbased` / `UK_seedbased` (EC OK, 0 admits → clean). Standalone skeleton
  is the regression tripwire `tests/integration/ec_templates/marginal_split.ec`.
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

## Iterating on a tactic — use the EC MCP interactively (not edit + full compile)

When working out or debugging an EasyCrypt tactic, drive the proof **interactively**
with the `easycrypt-mcp` tools: `cli_open` the `.ec`, `cli_step` one tactic at a
time, inspect with `ec_print_goals`/`cli_print`, `cli_undo` to back up. Do **not**
default to the edit-file-then-`ec_compile`-the-whole-thing loop — the real exported
proofs are ~50k lines and take minutes to recheck, while stepping shows the live
goal in seconds. Reserve `ec_compile` for a final whole-file confirmation or a small
self-contained prototype. (The tools are deferred — `ToolSearch
"select:mcp__easycrypt-mcp__cli_open,mcp__easycrypt-mcp__cli_step,..."` to load
their schemas. See `docs/for_agents/MCP_GUIDE.md` for the full list.)

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
