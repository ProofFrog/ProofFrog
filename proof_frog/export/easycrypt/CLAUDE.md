# EasyCrypt exporter — dev instructions

This file is auto-loaded when editing under `proof_frog/export/easycrypt/`.

## What the exporter is

The exporter translates a verified ProofFrog `.proof` into an EasyCrypt
`.ec` file that EasyCrypt re-checks. What it is, and how it must work, are
set by the project's normative architecture document. Its rules and its
enforcement contract are quoted below, verbatim (its R8 governs how it may
be cited). When the document changes, this quote is replaced as a whole.

<!-- BEGIN ARCHITECTURE.md (verbatim) -->
## The rules

- **R1 — Unit of translation.** Each interchangeability hop exports as
  a chain of micro-lemmas, one per engine transform application, each
  labeled with the transform name it evidences.

- **R2 — Tactic selection.** The tactic attached to a micro-lemma MUST
  be obtained from the transform registry, looked up by that
  application's transform name, and by nothing else. A registered
  entry MAY inspect the AST or rendered bodies AFTER selection — that
  is what "parametric" means. No code path may choose a micro-lemma
  tactic from program shape without the transform name having selected
  the entry first.

- **R3 — Registry entries.** Preference order: canned (static tactic
  text), parametric (deterministic synthesizer), cached (derived
  interactively once, stored with a derivation record, keyed by
  transform + masked local shape). One implementation MAY serve
  several transforms — via one explicit registration per transform,
  never by fallthrough.

- **R4 — No entry applies means admit.** The leg emits an `admit.`
  naming its transform (guided, when a fill template exists). Never a
  tactic that might run without closing its goal; never another
  transform's entry.

- **R5 — Structural lemmas** (wrapper-to-flat bridges, chain
  composition, hop lemmas, probability lemmas) are selected by hop
  structure: oracle count, endpoint kinds. That is allowed. Nothing
  anywhere is selected by what program text happens to look like.

- **R6 — Fused closures are forbidden.** No whole-oracle or whole-hop
  closure, except carve-outs registered below with Douglas's dated
  sign-off. A carve-out closure MUST be tagged `per-hop` and scores
  zero transform evidence.

- **R7 — The headline metric is transform coverage**: how many of the
  transforms firing in the corpus have registered tactics. Evidence
  volume and clean-proof counts are secondary. A change that raises a
  secondary number while lowering coverage is a regression.

- **R8 — Change control.** This file changes only on Douglas's
  explicit instruction. Agent sessions MUST NOT edit it, MUST NOT
  summarize or restate its rules in other documents (link or quote
  verbatim only), and MUST NOT treat any other document as overriding
  it.

- **R9 — The exporter knows languages, not cryptography.** The
  exporter translates FrogLang to EasyCrypt. It may reason about
  language concepts: types, fields, samples, calls, determinism and
  injectivity declarations, oracle structure. No code path, function,
  module, or constant may be named for or keyed to a cryptographic
  construction (a KDF, a random-oracle pattern, a challenge shape,
  seed splitting, a PRG/PRF seam). Construction-specific reasoning
  enters only as data the exporter consumes: registered per-transform
  entries, cached derivations with derivation records, and the proofs
  themselves.


## Enforcement contract

The rules are enforced by machinery, not memory. The machinery MUST
provide all of the following, and weakening any of them is a
stop-and-ask item:

- **E1 — Provenance tags.** Every emitted micro-lemma tactic carries
  `(* resolution: <rung> transform="<name>" entry="<id>" *)`.
- **E2 — Conformance test.** A test over corpus exports
  (`tests/integration/test_ec_architecture_conformance.py`) FAILS on:
  a micro-lemma tactic whose entry is not registered for that lemma's
  transform; a fused closure not in the carve-out register; an emitted
  tactic with no provenance tag.
- **E3 — Single constructor.** Only the registry module constructs
  micro-lemma tactic text; the chain emitter obtains tactics
  exclusively through the registry lookup API.
- **E4 — Coverage visibility.** Every dashboard view prints the R7
  coverage number in its top line.
<!-- END ARCHITECTURE.md -->

In the quoted text, "this file" means the architecture document, and
"below" and "the carve-out register" refer to a section of it that is not
quoted here.

## Key modules

- `exporter.py` — top-level entry; orchestrates per-hop chain emission.
- `chain_emitter.py` — emits the micro-lemma chain for one hop.
- `tactic_registry.py` — the transform-keyed registry: each transform name
  and the entry ids registered for it (`TACTIC_REGISTRY`, `is_registered`,
  `is_conforming_tag`), plus the transform-set constants the gates share.
  Today it owns selection legality only: the conformance test checks each
  provenance tag against it, but the tactic bodies still live in
  `transform_buckets.py` and in the chain emitter's gated routes.
- `transform_buckets.py` — the canned tactic bodies (`CANNED_TACTIC`) and
  the parametric synthesizer table (`PARAMETRIC_TACTIC`);
  `parametric_tactics.py` holds the synthesizers.
- `resolution.py` — the rung tokens and the provenance tag the exporter
  emits at each closure.
- `tactic_cache.py` and `canonical_form.py` — the sidecar tactic cache.
  `canonical_text()` is the normative key string: whitespace or naming
  drift between it and a sidecar silently turns a hit into a miss.
- `cache_report.py` — the `make check-tactic-cache` driver.
- `oracle_model.py` — the oracle-list data model for game files.
- `proof_translator.py`, `module_translator.py`, `expr_translator.py`,
  `stmt_translator.py`, `expr_text.py`, `type_collector.py`,
  `scheme_instances.py`, `ec_ast.py` — the FrogLang to EasyCrypt
  translation.

**Not yet conforming, and not a pattern to copy.** Some single-oracle
routes still select a tactic by program shape: `_try_det_reorder` runs
before any registry lookup, and after an admit, `_try_stateless`,
`_try_congruence`, `_try_dead_call_drop`, `_try_tuple_walk` and
`_try_dedup_det` run and emit closures without a provenance tag. Whole-hop
and whole-oracle cache paths still emit the `cached-guided` and
`admit-guided` rungs (`<hop>` and `<oracle>` entries in `exporter.py`).
These are the rebuild's worklist. Do not extend them.

The tests that hold the line:
`tests/integration/test_ec_architecture_conformance.py` (the conformance
test), `tests/integration/test_tactic_cache_orphan_check.py`, and
`tests/integration/test_cfrg_hybrid_kems.py` (the CFRG correctness lock:
a fast admit-free export check and a slow, Docker-gated EasyCrypt
compile).

## Foundations

Language-level translations that hold whatever selects the tactics. Each
is gated, so a proof that does not use the feature exports byte-identically.

- **Scheme statelessness** (helpers in `module_translator`, gated emission
  in `exporter.py`). EasyCrypt cannot `swap` two abstract scheme calls. For
  a scheme whose calls a micro-lemma reorders, the exporter emits
  per-method distribution ops, an `Ideal` sampling module and
  `declare axiom <module>_<m>_sem` statelessness specs, the probabilistic
  analogue of the `declare axiom <module>_<m>_det` determinism specs. A
  single declared module only so far. (Which micro-lemmas use these is
  decided today by the `_try_stateless` route above.)
- **BitWord bitstrings** (`type_collector.emit`, `_derived_concat_laws`,
  `_derived_split_law`, `_derived_concat3_laws`). A `BitString<w>` of known
  width emits as `clone BitWord as BW_bs_<w> with op n <- <w>` and
  `type bs_<w> = BW_bs_<w>.word`; slice, concat and concat3 are defined
  through the `ofword`/`mkword` bridge and `dbs_<w>` as
  `BW_bs_<w>.DWord.dunifin`, so the round-trip laws, the distribution
  splits and the `dbs_*_ll/_fu/_full` facts are proved lemmas rather than
  axioms, with statements byte-identical to the axioms they replaced.
  Earned the hard way:
  - `op [smt_opaque]` is mandatory. A defined op left visible to `smt`
    unfolds every nested `concat` into `mkword`/`ofword`/`++` and blows
    the budget. `smt_opaque` withholds the definitional axiom but keeps
    delta-reduction, so `rewrite /<op>` still unfolds it; plain `opaque`
    blocks that too.
  - The gates fail closed: the width must be known; a type aliased to an
    abstract carrier keeps the carrier's type; a concat triple whose
    component widths do not sum to the result's keeps the
    uninterpreted-op-and-axiom form, because a defined concat would make
    its round-trip laws false.
  - Each clone owes `gt0_n : 0 < <width>`. A sum of atoms is discharged
    from per-atom `gt0_<atom>` axioms; a width that subtracts gets its own
    `gt0_bs_<w>`. Never leave it undischarged: an undischarged clone axiom
    is real but invisible in the file text, so an axiom audit cannot see
    it.
  - EasyCrypt's `++` is left-associative: `A ++ B ++ C` is
    `(A ++ B) ++ C`, and the three-way proofs need `-catA` first. A
    right-nested reading fails with "nothing to rewrite".
  - When a triple's components share a type they share a slice op, so
    naming it twice in one `rewrite` is "nothing to rewrite".
  - Tripwires (in `tests/integration/ec_templates/`):
    `bitword_slice_concat.ec`,
    `bitword_uniform_split.ec`, `bitword_concat3.ec`,
    `bitword_split_couple.ec`.
- **ModInt and groups on the EasyCrypt standard library** (`type_collector`,
  `expr_translator`, `parametric_tactics.uniform_modint_tactic`). Group and
  ring laws are derived from `Group.ec` and `ZModP.ec`, not axiomatized;
  the one assumed axiom is ZModRing's side condition
  `ge2_p : 2 <= <modulus>`.
  - `GroupElem<G>` becomes `clone CyclicGroup as <G>`, cloned rather than
    imported so that the group's and the ring's `( * )` cannot collide:
    type `<G>.group`, `G.generator`/`G.identity` as `<G>.g`/`<G>.e`, every
    op qualified.
  - The exponent ring depends on the proof's `requires <G>.order is
    prime;`. By default it is `clone ZModP.ZModRing as <G>_Exp with op p
    <- <G>.order` with powers through `<G>_Exp.asint`. A proof declaring
    the requirement gets `axiom <G>_prime_order`, `clone <G>.PowZMod as
    <G>_P` and `clone <G>_P.FDistr as <G>_FD`.
  - A `ModInt<<G>.order>` aliases the group's exponent ring
    (`type_collector._group_order_modulus_alias`); any other `ModInt<q>`
    gets its own `clone ZModP.ZModRing as ModInt_q with op p <- <q>`, bound
    to the FrogLang modulus. Its uniform distribution is
    `<T>.DZmodP.dunifin`; group elements sample from
    `duniform <G>.elems`.
  - The `Group`, `ZModP` and `List` theories are required only when a
    group or ModInt is registered (`has_stdlib_group_or_modint`).
- **Group-only export mode** (`exporter._group_only_let_name`,
  `_export_group_only`, `_group_only_scaffold`). A proof that imports only
  game files and attacks a game parameterized by a `Group` (for example
  `DDH_implies_CDH`) has no primitive theory. It is routed to its own
  branch, which emits the games at top level over `clone CyclicGroup as
  <G>` and hand-builds the step wrappers, the assumption `eps_<gf>` ops,
  the hop lemmas (admitted equalities, except a hop between the two sides
  of one assumption game) and the main theorem. Games with several
  math-structure parameters still hit `translate_game`'s single
  module-parameter assertion.
- **Random functions** (`type_collector`, `expr_translator`,
  `module_translator`). A field `RF <- Function<A, B>` becomes EasyCrypt's
  arrow type `A -> B`, sampled from an abstract uniform distribution over
  the function space (`op dfun_<dom>_to_<codom>` with `_ll`, `_fu` and
  `_full` axioms, the standard facts about `dfun (fun _ => dB)`), and
  `RF(x)` renders as `RF x`. EasyCrypt module variables must start
  lowercase, so an uppercase field is renamed at every declaration and use
  (`RF` to `rF`) through a `field_renames` map.
- **Subset carriers** (`type_collector.register_subset_carrier`,
  `bitstring_carrier_type`, `expr_translator._bitstring_type_of`). A scheme
  `requires X subsets BitString<n>` makes the carrier `X` bitstring-like.
  The engine inlines the coercion into the chain's flat states, so a `||`
  operand can surface carrier-typed; `_bitstring_type_of` maps it to its
  `BitString<n>` and renders `concat_*`, summing nested `||` structurally.
  The carrier map is seeded before chain emission; the late `requires`
  pass that emits `type bs_n = X.` runs too late for the translator.

- **Intermediate games** (`module_translator.translate_intermediate_game`,
  `proof_translator._resolve_intermediate_game`). A proof-local `Game`
  helper referenced as a bare step (`Hyb(q)`) is emitted as a concrete
  module implementing the outer theorem game's oracle type, single- or
  multi-oracle. Module-typed parameters become functor parameters;
  non-module parameters (`Int q`) are dropped from the signature and the
  module expression. The bare step's precondition comes from the outer
  game file (`={mL, mR}`), not `true`.
- **A concrete scheme for an unconditional primary** (`exporter.py`, scheme
  determination). A primitive-typed `let:` bound to a concrete scheme
  constructor, in a proof with no `assume:`, is emitted as a concrete
  module, not an abstract `declare module`: the engine inlines the scheme
  into the flat states, so the bridge needs a module `inline *` can
  unfold. Proofs with assumptions keep it abstract for the reduction.

## Evidence-only micro-lemmas

When an oracle's chain does not close, the legs that did close are still
emitted as standalone lemmas (`_scan_legs`, `_evidence_only_chunks`),
prefixed `(* evidence-only: ... *)`. A leg that declines emits nothing,
never an `admit.`, so an admit-free proof stays admit-free. EasyCrypt
still proves these lemmas, so an accepted file evidences exactly the
transform applications they name. An `Initialize` leg is never emitted
this way: its precondition is `true`, so it would have to establish the
state coupling from nothing.

What this exposes when adding or changing a registered entry:

- **Every gate now runs on shapes no closing chain reached.** An entry
  that emits a tactic it cannot guarantee closes shows up as a rejected
  export, not a silent miss (`_peelable_tail_backbone` and
  `_bodies_equal_under_field_map` exist for this reason).
- **A broken chain's coupling may not typecheck.** `_chain_role_map` is a
  union-find over bare field names, so identically named fields of
  unrelated states can merge into `A.f{1} = B.g{2}` across types;
  `_micro_pre_well_typed` drops such lemmas.
- **A whole-glob precondition typechecks only if both states' glob
  signatures agree** (`_glob_signature`: the module variables and the
  functor parameters the body actually calls). `glob F(A)` contains
  `glob A` only when `F` calls `A`, so two states with identical fields
  can differ. EasyCrypt then reports "no matching operator, named `='"
  with no parameter types, which reads like a solver failure. Compare
  whole flat states, not oracle projections: the difference usually lives
  in `initialize`. Tripwire:
  `tests/integration/ec_templates/evidence_glob_param_usage_rejects.ec`.

## The automation ladder

Every closed micro-lemma or hop body carries one rung of a single ranked
scale (`resolution.py`), best-automated first:

1. **Synthesized, static** (`synth-static`): a canned tactic body.
2. **Synthesized, parametric** (`synth-param`): a tactic computed by a
   registered synthesizer.
3. **Cached, with guidance** (`cached-guided`): a sidecar entry filled
   from a template the exporter emitted.
4. **Cached, without guidance** (`cached-unguided`): a sidecar entry a
   human derived from scratch.
5. **Admit, with guidance** (`admit-guided`): an open `admit.` with a
   fill template for this hop.
6. **Admit, without guidance** (`admit-unguided`): an open `admit.` with
   only the generic cache-miss comment.

Below them sits a proof-level state, **blocked**: the proof exports but
EasyCrypt rejects the file. The exporter cannot see that; the dashboard
measures it by compiling every export, and counts a proof clean only if
EasyCrypt accepts it and it has no admit. A tactic that silently fails to
close its goal gives a zero-admit file EasyCrypt still rejects.

How rungs relate to the registry is set by R3, R4 and R6 above. Today the
`cached-guided` and `admit-guided` rungs come only from the whole-hop and
whole-oracle paths listed under "Not yet conforming": do not add entries
there. A per-transform cache entry (rung 4) is filled as
`docs/for_agents/EASYCRYPT_TACTICS.md` describes, but that file's advice to
climb from whole-hop admits to whole-hop cache entries predates the
architecture and must not be followed.

## Things to stop and ask before doing

- **Bumping `schema_version`** in any sidecar or `tactic_cache.py`: it
  invalidates every existing entry. A maintainer decision.
- **Changing the canonicalization basis** (`canonical_text`,
  `_normalize_for_ec`, or anything in `proof_frog/transforms/` that
  changes canonical output): it silently invalidates cached entries.
- **Promoting a recurring cache recipe (rung 3 or 4) to a registered
  synthesized entry (rung 1 or 2)**: wait until at least five distinct
  proofs need the same recipe for the same transform.
- **A new kind of `declare axiom`** in the emitted files.
- **Any change to the registry API, the conformance test or the provenance
  tag format**, and anything that weakens the enforcement contract above.

## Sanity check

`make check-tactic-cache` reports per-proof `used / orphan / missing`
counts for the whole `examples/` corpus (`--strict` exits nonzero on a
missing entry). Run it after any change that affects which tactics fire
or the canonical-text basis.

## Iterating on a tactic: use the EasyCrypt MCP interactively

Work a tactic out with the `easycrypt-mcp` tools: `cli_open` the `.ec`,
`cli_step` one tactic at a time, inspect with `ec_print_goals` or
`cli_print`, and `cli_undo` to back up. Exported proofs are long and take
minutes to recheck, while stepping shows the live goal in seconds. Keep
`ec_compile` for a final whole-file check or a small self-contained
prototype. (The tools are deferred: load them with `ToolSearch
"select:mcp__easycrypt-mcp__cli_open,mcp__easycrypt-mcp__cli_step,..."`.
See `docs/for_agents/MCP_GUIDE.md` for the list.)

## The fast regression loop

A change here can only affect proofs that export; the proofs that fail
before chain emission are untouched. So, per change:

- `scripts/ec_export_regression.sh` re-exports the exporting proofs in
  parallel and lists which `.ec` outputs differ from the committed (HEAD)
  baseline. It builds the baseline by stashing your `proof_frog` changes,
  cached per HEAD SHA.
- EasyCrypt-compile only the changed exports (`ec_compile`, or
  `scripts/easycrypt.sh`): byte-identical exports compile identically.
- Run the targeted tests, not the whole suite (which spends minutes on
  engine runs an export change cannot affect):
  `pytest tests/unit/export --ignore=tests/unit/export/latex
  tests/integration/test_easycrypt_export.py
  tests/integration/test_tactic_cache_orphan_check.py
  tests/integration/test_ec_architecture_conformance.py`. The
  `test_easycrypt_export.py` cases skip without Docker; record whether
  they ran.
- [../../../docs/for_agents/EASYCRYPT_TACTICS.md](../../../docs/for_agents/EASYCRYPT_TACTICS.md)
  has the `.ec-tmp/` sandbox-mount workaround for macOS.

The full `make check-tactic-cache` and the EasyCrypt dashboard (which
compiles every `.ec`) are the heavyweight checks: run them before
declaring a milestone, not on every edit.
