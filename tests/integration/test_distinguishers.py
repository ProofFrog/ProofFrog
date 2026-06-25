"""Multi-invocation distinguisher integration tests.

This file collects integration-level tests that exercise transform/engine
soundness in ways unit tests cannot easily reach: behaviour observable
across multiple oracle calls, end-to-end engine paths that mix several
transforms, and refusal-on-unsound-input checks for fallback paths.

New tests should be small, hand-built FrogLang fragments — not full
proofs — so a failure points directly at one engine path.
"""

from __future__ import annotations

from sympy import Symbol

from proof_frog import frog_parser, visitors
from proof_frog.proof_engine import ProofEngine, _z3_residual_equivalence


def _engine_with(**namespace) -> ProofEngine:
    """Build a ProofEngine with the given primitives/schemes pre-loaded
    and the bit-string length symbol ``n`` registered.

    Multi-call distinguisher tests below rely on the end-to-end pipeline
    (``check_equivalent`` runs CORE_PIPELINE + STANDARDIZATION_PIPELINE +
    Z3 residual on both sides), which needs the relevant primitive
    definitions in ``proof_namespace`` so deterministic/injective
    annotations are visible to the transforms, and any symbolic
    bit-string length used in the games (here ``n``) registered in
    ``engine.variables`` for ``FrogToSympyVisitor``.
    """
    engine = ProofEngine()
    engine.variables["n"] = Symbol("n", positive=True, integer=True)
    for name, root in namespace.items():
        engine.proof_namespace[name] = root
    return engine


# --------------------------------------------------------------------------
# Z3 escape-hatch refusal.
#
# ``_z3_check_expression_pair`` is allowed to encode FuncCall sub-
# expressions as opaque atoms only when both expressions are
# deterministic. If a non-deterministic call leaks into the return
# expression, the opaque-atom encoding would treat distinct
# invocations as equal — a soundness bug. The pre-check in
# ``_z3_check_expression_pair`` plus the in-visitor backstop added by
# ``277a104`` must refuse such inputs.
# --------------------------------------------------------------------------


def _two_prim_namespace() -> dict:
    """Namespace with a deterministic primitive H and a non-det primitive F."""
    h = frog_parser.parse_primitive_file(
        """
        Primitive H(Int n) {
            deterministic BitString<n> det(BitString<n> x);
        }
        """
    )
    f = frog_parser.parse_primitive_file(
        """
        Primitive F(Int n) {
            BitString<n> nondet(BitString<n> x);
        }
        """
    )
    return {"H": h, "F": f, "HH": h, "FF": f}


def _game(return_expr: str):
    return frog_parser.parse_game(
        f"""
        Game Foo(H HH, F FF) {{
            BitString<n> seed;
            Void Initialize() {{
                seed <- BitString<n>;
            }}
            BitString<n> Get(BitString<n> x) {{
                return {return_expr};
            }}
        }}
        """
    )


def test_z3_residual_refuses_on_nondeterministic_return() -> None:
    """If the differing return expression on either side contains a
    non-deterministic call, ``_z3_residual_equivalence`` must refuse —
    the opaque-atom encoding would silently treat distinct invocations
    as equal across the two sides."""
    current = _game("HH.det(x) + FF.nondet(seed)")
    other = _game("HH.det(x) + FF.nondet(x)")
    result = _z3_residual_equivalence(
        current, other, visitors.NameTypeMap(), _two_prim_namespace()
    )
    assert result.valid is False
    assert result.failure_detail is not None
    assert "non-deterministic call" in result.failure_detail


def test_z3_residual_refuses_when_only_one_side_is_nondeterministic() -> None:
    """Asymmetric case: only the new-side return introduces a non-det
    call. Still must refuse — the pre-check ORs the two sides."""
    current = _game("HH.det(x)")
    other = _game("FF.nondet(x)")
    result = _z3_residual_equivalence(
        current, other, visitors.NameTypeMap(), _two_prim_namespace()
    )
    assert result.valid is False
    assert result.failure_detail is not None


def test_z3_residual_allows_purely_deterministic_returns() -> None:
    """Control: when both returns are purely deterministic FuncCalls
    that happen to be syntactically distinct but Z3-equivalent under
    opaque-atom encoding (here: trivially identical), the residual
    check must succeed."""
    current = _game("HH.det(x)")
    other = _game("HH.det(x)")
    result = _z3_residual_equivalence(
        current, other, visitors.NameTypeMap(), _two_prim_namespace()
    )
    assert result.valid is True


# --------------------------------------------------------------------------
# Per-transform multi-call distinguishers.
#
# Each pair below is structured as ``pre`` (a game in the shape that a
# specific transform is meant to canonicalize) vs ``post`` (a game in the
# shape that an honest hand-rewrite of the transform's claim produces).
# The two games share a ``Initialize``-set field so the oracle's behaviour
# is observable across multiple calls (same field, same deterministic
# call ⇒ same output), which is the property the transform must preserve.
#
# ``ProofEngine.check_equivalent`` runs CORE_PIPELINE + standardization +
# Z3 residual on both sides; ``valid is True`` means the engine accepts
# pre and post as multi-call indistinguishable. If a future change broke
# the transform's cross-call reasoning (e.g. hoisted state that should
# stay per-call, or vice versa), one of these would flip to False.
# --------------------------------------------------------------------------


def test_dedup_deterministic_if_condition_multicall() -> None:
    """``DeduplicateDeterministicCalls`` (if-condition extension): a
    deterministic call on a shared ``Initialize``-set field, appearing
    in both an if-condition and the fall-through return, is observably
    identical to the hand-deduplicated form across repeated oracle
    invocations."""
    prim = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            deterministic BitString<n> evaluate(BitString<n> x);
        }
        """
    )
    pre = frog_parser.parse_game(
        """
        Game Pre(G GG) {
            BitString<n> seed;
            Void Initialize() {
                seed <- BitString<n>;
            }
            BitString<n> Get(BitString<n> x) {
                if (GG.evaluate(seed) == x) {
                    return x;
                }
                return GG.evaluate(seed);
            }
        }
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post(G GG) {
            BitString<n> seed;
            Void Initialize() {
                seed <- BitString<n>;
            }
            BitString<n> Get(BitString<n> x) {
                BitString<n> v = GG.evaluate(seed);
                if (v == x) {
                    return x;
                }
                return v;
            }
        }
        """
    )
    engine = _engine_with(G=prim, GG=prim)
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_split_opaque_tuple_field_multicall() -> None:
    """``SplitOpaqueTupleField``: a tuple-typed field initialized once
    from an opaque deterministic call and read component-wise across
    two oracles (one per index) is observably identical to the
    component-split form. The two oracles witness the multi-call
    observation — each pins one tuple slot — so an unsound split that
    re-sampled per call would diverge."""
    prim = frog_parser.parse_primitive_file(
        """
        Primitive K(Int n) {
            deterministic [BitString<n>, BitString<n>] Gen(BitString<n> seed);
        }
        """
    )
    pre = frog_parser.parse_game(
        """
        Game Pre(K KK) {
            BitString<n> seed;
            [BitString<n>, BitString<n>] keys;
            Void Initialize() {
                seed <- BitString<n>;
                keys = KK.Gen(seed);
            }
            BitString<n> GetA() {
                return keys[0];
            }
            BitString<n> GetB() {
                return keys[1];
            }
        }
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post(K KK) {
            BitString<n> seed;
            BitString<n> keys_0;
            BitString<n> keys_1;
            Void Initialize() {
                seed <- BitString<n>;
                [BitString<n>, BitString<n>] _tup = KK.Gen(seed);
                keys_0 = _tup[0];
                keys_1 = _tup[1];
            }
            BitString<n> GetA() {
                return keys_0;
            }
            BitString<n> GetB() {
                return keys_1;
            }
        }
        """
    )
    engine = _engine_with(K=prim, KK=prim)
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_flatten_concat_chain_multicall() -> None:
    """``FlattenConcatChain``: an oracle that returns a right-grouped
    concatenation of three ``Initialize``-set fields is observably
    identical, across repeated calls, to the left-associative
    flattened form. Both forms must observe the same field values per
    call — a buggy flatten that reordered the operands would
    distinguish here."""
    pre = frog_parser.parse_game(
        """
        Game Pre() {
            BitString<n> a;
            BitString<n> b;
            BitString<n> c;
            Void Initialize() {
                a <- BitString<n>;
                b <- BitString<n>;
                c <- BitString<n>;
            }
            BitString<3*n> Get() {
                return a || (b || c);
            }
        }
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post() {
            BitString<n> a;
            BitString<n> b;
            BitString<n> c;
            Void Initialize() {
                a <- BitString<n>;
                b <- BitString<n>;
                c <- BitString<n>;
            }
            BitString<3*n> Get() {
                return (a || b) || c;
            }
        }
        """
    )
    engine = _engine_with()
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_absorb_redundant_early_return_multicall() -> None:
    """``AbsorbRedundantEarlyReturn``: the ``if (P) return v; ... return v``
    shape and its absorbed form ``if (!P && Q) ...; return v`` must
    agree on every oracle call regardless of the per-call inputs ``x``,
    ``y`` and the ``Initialize``-set field ``stash``. The field makes
    one return value depend on shared state — an unsound absorption
    that dropped the early-return path would change observable
    behaviour for inputs satisfying ``P``."""
    pre = frog_parser.parse_game(
        """
        Game Pre() {
            BitString<n> stash;
            Void Initialize() {
                stash <- BitString<n>;
            }
            BitString<n> Get(BitString<n> x, BitString<n> y) {
                if (x == y) {
                    return stash;
                }
                if (x == stash) {
                    BitString<n> r <- BitString<n>;
                    return r;
                }
                return stash;
            }
        }
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post() {
            BitString<n> stash;
            Void Initialize() {
                stash <- BitString<n>;
            }
            BitString<n> Get(BitString<n> x, BitString<n> y) {
                if (x != y && x == stash) {
                    BitString<n> r <- BitString<n>;
                    return r;
                }
                return stash;
            }
        }
        """
    )
    engine = _engine_with()
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


# --------------------------------------------------------------------------
# Lazy-map and hoist families.
#
# These pairs target transforms that move state across oracle boundaries
# (Hoist*ToInitialize, LazyMap*ToSampledFunction) or that re-key / re-scan
# a shared map (LazyMapScan, MapKeyReindex, RefactorGroupElemFieldExp).
# Multi-call observability is the crux for each — a buggy hoist that
# captured per-call state, or a buggy reindex that mismatched the read
# and write key spaces, would diverge on the second invocation.
# --------------------------------------------------------------------------


def test_lazy_map_scan_multicall() -> None:
    """``LazyMapScan``: ``for e in M.entries: if e[0] == arg return e[1]``
    on a shared ``Map<K, V>`` field is observably identical to direct
    membership-test + lookup, across multiple oracle calls that read
    keys populated by earlier writes."""
    pre = frog_parser.parse_game(
        """
        Game Pre() {
            Map<BitString<8>, BitString<16>> M;
            Void Store(BitString<8> k, BitString<16> v) {
                M[k] = v;
            }
            BitString<16> Lookup(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post() {
            Map<BitString<8>, BitString<16>> M;
            Void Store(BitString<8> k, BitString<16> v) {
                M[k] = v;
            }
            BitString<16> Lookup(BitString<8> arg) {
                if (arg in M) {
                    return M[arg];
                }
                return 0b0000000000000000;
            }
        }
        """
    )
    engine = _engine_with()
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_map_key_reindex_multicall() -> None:
    """``MapKeyReindex``: when every read of ``M`` goes through an
    injective deterministic call ``TT.Eval(.)``, re-keying ``M`` on the
    Eval'd value (and rewriting writes accordingly) preserves cross-call
    observation. Store and Lookup are separate oracles so any mismatch
    between the rewritten write site and the read site would surface."""
    prim = frog_parser.parse_primitive_file(
        """
        Primitive T(Set I, Set Y) {
            Set Input = I;
            Set Image = Y;
            deterministic injective Image Eval(Input x);
        }
        """
    )
    pre = frog_parser.parse_game(
        """
        Game Pre(T TT) {
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
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post(T TT) {
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
        """
    )
    engine = _engine_with(T=prim, TT=prim)
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_lazy_map_to_sampled_function_multicall() -> None:
    """``LazyMapToSampledFunction``: the standard lazy-sampled hash idiom
    (``if x in T: return T[x]; else: sample, store, return``) is
    observably identical to a single sampled ``Function<D, R>`` lookup
    across repeated calls with both fresh and repeated keys — the
    consistency property is exactly the random-function semantics."""
    pre = frog_parser.parse_game(
        """
        Game Pre() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post() {
            Function<BitString<8>, BitString<16>> T;
            Void Initialize() {
                T <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) {
                return T(x);
            }
        }
        """
    )
    engine = _engine_with()
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_lazy_map_pair_to_sampled_function_multicall() -> None:
    """``LazyMapPairToSampledFunction``: two oracles each lazily populating
    a private map but sharing the cross-oracle "look in both" idiom
    collapse to a single sampled ``Function<D, R>`` shared by both
    oracles. The cross-oracle consistency (calling QueryA then QueryB
    on the same key) is the multi-call observation under test."""
    pre = frog_parser.parse_game(
        """
        Game Pre() {
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
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post() {
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
        """
    )
    engine = _engine_with()
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_hoist_deterministic_call_to_initialize_multicall() -> None:
    """``HoistDeterministicCallToInitialize``: two oracles both calling
    ``GG.evaluate(seed)`` on a shared ``Initialize``-sampled field can
    cache the result in a new ``Initialize``-set field. Cross-call
    observation: every call to either oracle returns the same value,
    which holds iff the cached field is computed once at Initialize and
    referenced thereafter."""
    prim = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            deterministic BitString<n> evaluate(BitString<n> x);
        }
        """
    )
    pre = frog_parser.parse_game(
        """
        Game Pre(G GG) {
            BitString<n> seed;
            Void Initialize() {
                seed <- BitString<n>;
            }
            BitString<n> Get1() {
                return GG.evaluate(seed);
            }
            BitString<n> Get2() {
                return GG.evaluate(seed);
            }
        }
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post(G GG) {
            BitString<n> seed;
            BitString<n> cached;
            Void Initialize() {
                seed <- BitString<n>;
                cached = GG.evaluate(seed);
            }
            BitString<n> Get1() {
                return cached;
            }
            BitString<n> Get2() {
                return cached;
            }
        }
        """
    )
    engine = _engine_with(G=prim, GG=prim)
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_hoist_group_exp_to_initialize_multicall() -> None:
    """``HoistGroupExpToInitialize``: a Hash oracle returning
    ``field1 ^ field2`` where ``field1 = generator ^ v1`` is set once in
    Initialize lets the power-of-power be cached. Multi-call observation:
    every Hash call returns the same group element — the caching field
    must be Initialize-computed, not re-derived per call."""
    pre = frog_parser.parse_game(
        """
        Game Pre(Group G) {
            ModInt<G.order> field2;
            GroupElem<G> field1;
            Void Initialize() {
                field2 <-uniq[{0}] ModInt<G.order>;
                ModInt<G.order> v1 <- ModInt<G.order>;
                field1 = G.generator ^ v1;
            }
            Bool Hash(GroupElem<G> z) {
                return z == field1 ^ field2;
            }
        }
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post(Group G) {
            ModInt<G.order> field2;
            GroupElem<G> field1;
            GroupElem<G> _hge_0;
            Void Initialize() {
                field2 <-uniq[{0}] ModInt<G.order>;
                ModInt<G.order> v1 <- ModInt<G.order>;
                field1 = G.generator ^ v1;
                _hge_0 = (G.generator ^ v1) ^ field2;
            }
            Bool Hash(GroupElem<G> z) {
                return z == _hge_0;
            }
        }
        """
    )
    engine = _engine_with()
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_refactor_group_elem_field_exp_multicall() -> None:
    """``RefactorGroupElemFieldExp``: when ``field2 = g ^ a`` and
    ``field1 = g ^ (a*b)``, the engine should re-express ``field1`` as
    ``field2 ^ b`` (power-of-power). A reader oracle exposes both
    fields across calls; the rewrite must agree on every call —
    otherwise a stale or per-call recomputation would diverge."""
    pre = frog_parser.parse_game(
        """
        Game Pre(Group G) {
            GroupElem<G> field1;
            GroupElem<G> field2;
            ModInt<G.order> b_pub;
            Void Initialize() {
                ModInt<G.order> a <- ModInt<G.order>;
                ModInt<G.order> b <- ModInt<G.order>;
                b_pub = b;
                field2 = G.generator ^ a;
                field1 = G.generator ^ (a * b);
            }
            GroupElem<G> GetField1() {
                return field1;
            }
            GroupElem<G> GetField2() {
                return field2;
            }
        }
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post(Group G) {
            GroupElem<G> field1;
            GroupElem<G> field2;
            ModInt<G.order> b_pub;
            Void Initialize() {
                ModInt<G.order> a <- ModInt<G.order>;
                ModInt<G.order> b <- ModInt<G.order>;
                b_pub = b;
                field2 = G.generator ^ a;
                field1 = field2 ^ b;
            }
            GroupElem<G> GetField1() {
                return field1;
            }
            GroupElem<G> GetField2() {
                return field2;
            }
        }
        """
    )
    engine = _engine_with()
    result = engine.check_equivalent(pre, post)
    assert result.valid, result.failure_detail


# --------------------------------------------------------------------------
# Negative distinguishers: the engine must REJECT genuinely distinguishable
# pairs.  Each pair below differs only in the ORDER of a state read relative
# to a state write -- `... = read(state); write(state); return ...` versus
# `write(state); return read(state)`.  These are advantage-1 distinguishable
# (the read observes different state on the two sides), so check_equivalent
# must return valid is False.  Before the RC1 reference/write-scan fixes the
# canonicalizer (TopologicalSort dependency model, RemoveUnnecessaryFields
# liveness, SimplifyReturn / the inliners) moved the read past the write on
# one side and wrongly accepted the pair.  (audit findings F-126 + the
# RC-front movers behind it.)
# --------------------------------------------------------------------------


def test_reject_read_moved_past_uniq_insertion() -> None:
    """`<-uniq[S]` inserts the draw into S, so `|S|` read before vs after the
    draw differs.  Must not be accepted as equivalent."""
    real = frog_parser.parse_game(
        """
        Game Real() {
            Set<BitString<2>> S;
            BitString<2> t;
            Void Initialize() { t = 0b00; }
            [Int, Int] O() {
                [Int, Int] s = [|S|, 0];
                BitString<2> x <-uniq[S] BitString<2>;
                t = x;
                return s;
            }
            BitString<2> Peek() { return t; }
        }
        """
    )
    random = frog_parser.parse_game(
        """
        Game Random() {
            Set<BitString<2>> S;
            BitString<2> t;
            Void Initialize() { t = 0b00; }
            [Int, Int] O() {
                BitString<2> x <-uniq[S] BitString<2>;
                t = x;
                return [|S|, 0];
            }
            BitString<2> Peek() { return t; }
        }
        """
    )
    assert not _engine_with().check_equivalent(real, random).valid


def test_reject_read_moved_past_map_write_via_fieldaccess_view() -> None:
    """`|M.keys|` reaches M only through a FieldAccess view; moving it past the
    element write `M[0]=1` changes its value.  Must not be accepted."""
    real = frog_parser.parse_game(
        """
        Game Real() {
            Map<Int, Int> M;
            [Int, Int] O() {
                [Int, Int] s = [|M.keys|, 0];
                M[0] = 1;
                return s;
            }
            Int Size() { return M[0]; }
        }
        """
    )
    random = frog_parser.parse_game(
        """
        Game Random() {
            Map<Int, Int> M;
            [Int, Int] O() {
                M[0] = 1;
                return [|M.keys|, 0];
            }
            Int Size() { return M[0]; }
        }
        """
    )
    assert not _engine_with().check_equivalent(real, random).valid


def test_reject_read_moved_past_nested_element_write() -> None:
    """A read of `M[0]` moved past the nested element write `M[0][1]=1`
    observes the mutated value.  Must not be accepted."""
    real = frog_parser.parse_game(
        """
        Game Real() {
            Map<Int, [Int, Int]> M;
            Void Initialize() { M[0] = [0, 0]; }
            [Int, Int] O() {
                [Int, Int] s = M[0];
                M[0][1] = 1;
                return s;
            }
        }
        """
    )
    random = frog_parser.parse_game(
        """
        Game Random() {
            Map<Int, [Int, Int]> M;
            Void Initialize() { M[0] = [0, 0]; }
            [Int, Int] O() {
                M[0][1] = 1;
                return M[0];
            }
        }
        """
    )
    assert not _engine_with().check_equivalent(real, random).valid


# --------------------------------------------------------------------------
# F-029 (SliceOfInlineConcat) — end-to-end soundness.
#
# `(a || b)[start:end]` may be rewritten to an operand ONLY when the slice
# bounds match that operand's TRUE length at the slice site. Several engine
# paths previously conspired to lose that length (a scope-blind length table
# in the pass, a bare-declaration drop in TopologicalSort / RemoveUnnecessary,
# a cross-scope CollapseAssignment merge, and a Z3 residual that modelled a
# slice as its width alone). Each game pair below is distinguishable; the
# engine must REJECT it. A sound control follows.
# --------------------------------------------------------------------------


def test_slice_of_concat_z3_residual_distinct_operands() -> None:
    """Z3 residual: a full-width slice `(s || b)[0:2n]` of a concat must not
    compare equal to `(s || s)[0:2n]`. The slice was previously modelled by
    its width alone (`@@@opaque@...@2 * n`), collapsing distinct operands to
    one atom. No shadowing here -- this is the bare equivalence-layer hole."""
    real = frog_parser.parse_game(
        """
        Game Real(Int n) {
            BitString<2 * n> Oracle(BitString<n> b) {
                BitString<n> s <- BitString<n>;
                return (s || b)[0 : 2 * n];
            }
        }
        """
    )
    random = frog_parser.parse_game(
        """
        Game Random(Int n) {
            BitString<2 * n> Oracle(BitString<n> b) {
                BitString<n> s <- BitString<n>;
                return (s || s)[0 : 2 * n];
            }
        }
        """
    )
    assert not _engine_with().check_equivalent(real, random).valid


def test_slice_of_concat_decl_shadow_param() -> None:
    """Attack 1: a decl-only local `BitString<n> x;` shadows the 2n-bit
    parameter `x`. The bare declaration must survive TopologicalSort /
    RemoveUnnecessary so `x` keeps its n-bit binding, and the slice must not
    be rewritten to `x` (dropping `b`)."""
    real = frog_parser.parse_game(
        """
        Game Real(Int n) {
            BitString<2 * n> Oracle(BitString<2 * n> x, BitString<n> b) {
                BitString<n> x;
                x <- BitString<n>;
                return (x || b)[0 : 2 * n];
            }
        }
        """
    )
    random = frog_parser.parse_game(
        """
        Game Random(Int n) {
            BitString<2 * n> Oracle(BitString<2 * n> x, BitString<n> b) {
                BitString<n> x;
                x <- BitString<n>;
                return (x || x)[0 : 2 * n];
            }
        }
        """
    )
    assert not _engine_with().check_equivalent(real, random).valid


def test_slice_of_concat_nested_redecl_case2() -> None:
    """Attack 3b: a nested-block redeclaration `BitString<k + m> a` shadows
    the outer `BitString<k> a`. SinkUniformSample + CollapseAssignment must
    not merge the two `a`s across the scope boundary into a mistyped
    `BitString<k> a <- BitString<k + m>`, which would let the Case 2 slice
    fold to `b`."""
    real = frog_parser.parse_game(
        """
        Game Real(Int k, Int m) {
            [BitString<m>, BitString<m>] Oracle(Bool cond, BitString<m> b) {
                BitString<k> a <- BitString<k>;
                if (cond) {
                    BitString<k + m> a <- BitString<k + m>;
                    return [(a || b)[k : k + m], b];
                }
                return [b, b];
            }
        }
        """
    )
    random = frog_parser.parse_game(
        """
        Game Random(Int k, Int m) {
            [BitString<m>, BitString<m>] Oracle(Bool cond, BitString<m> b) {
                return [b, b];
            }
        }
        """
    )
    engine = _engine_with()
    engine.variables["k"] = Symbol("k", positive=True, integer=True)
    engine.variables["m"] = Symbol("m", positive=True, integer=True)
    assert not engine.check_equivalent(real, random).valid


def test_slice_of_concat_sound_identity_still_fires() -> None:
    """Control: the genuine identity `(a || b)[0 : |a|] = a` must STILL be
    recognized -- the fixes restrict the unsound cases, not the sound one."""
    real = frog_parser.parse_game(
        """
        Game Real(Int n) {
            BitString<n> Oracle(BitString<n> a, BitString<n> b) {
                return (a || b)[0 : n];
            }
        }
        """
    )
    post = frog_parser.parse_game(
        """
        Game Post(Int n) {
            BitString<n> Oracle(BitString<n> a, BitString<n> b) {
                return a;
            }
        }
        """
    )
    assert _engine_with().check_equivalent(real, post).valid


def test_guarded_field_element_write_not_dropped() -> None:
    """F-075 / mover sweep: a field element-write nested in a guarded branch is
    observable across calls (via a later read), so it must not be dropped. The
    bug: TopologicalSort hoisted the constant `return 0` above the
    `if (x == F) { F[k] = 99; }` branch because `mutates_field` only inspected
    top-level statement kinds and missed the write nested in the if; the branch
    then looked dead and was removed, equating a persistent field mutation
    (Real) with a write to a local parameter (Random)."""
    real = frog_parser.parse_game(
        """
        Game Real() {
            Map<Int, Int> F;
            Void SetF(Int k, Int v) { F[k] = v; }
            Int Get(Int k) { return F[k]; }
            Int Test(Map<Int, Int> x, Int k) {
                if (x == F) { F[k] = 99; }
                return 0;
            }
        }
        """
    )
    random = frog_parser.parse_game(
        """
        Game Random() {
            Map<Int, Int> F;
            Void SetF(Int k, Int v) { F[k] = v; }
            Int Get(Int k) { return F[k]; }
            Int Test(Map<Int, Int> x, Int k) {
                if (x == F) { x[k] = 99; }
                return 0;
            }
        }
        """
    )
    assert not _engine_with().check_equivalent(real, random).valid
