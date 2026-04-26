"""Tests for CrossMethodFieldAlias transform.

Verifies that deterministic calls stored in fields are propagated to other
methods, while calls with local arguments, non-deterministic calls, and
calls without field assignments are left alone.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import (
    CrossMethodFieldAliasTransformer,
)


def _make_det_namespace() -> frog_ast.Namespace:
    """Namespace with primitive G whose ``evaluate`` is deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive G(Int n) {
            deterministic BitString<n> evaluate(BitString<n> x);
        }
        """)
    return {"G": prim}


def _make_nondet_namespace() -> frog_ast.Namespace:
    """Namespace with primitive G whose ``evaluate`` is NOT deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive G(Int n) {
            BitString<n> evaluate(BitString<n> x);
        }
        """)
    return {"G": prim}


class TestCrossMethodFieldAlias:
    """Tests for CrossMethodFieldAliasTransformer."""

    def test_field_assignment_replaces_call_in_other_method(self) -> None:
        """field = GG.evaluate(k) in Initialize, GG.evaluate(k) in Oracle -> replaced."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    stored = GG.evaluate(k);
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # Oracle should now return the field, not the call
        oracle = result.methods[1]
        ret = oracle.block.statements[0]
        assert isinstance(ret, frog_ast.ReturnStatement)
        assert isinstance(ret.expression, frog_ast.Variable)
        assert ret.expression.name == "stored"

    def test_no_field_assignment_no_replacement(self) -> None:
        """Without field = det_call, no replacement even if call appears twice."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                Void Initialize() {
                    BitString<n> local = GG.evaluate(k);
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # No change -- Initialize has a typed local assignment, not a field assignment
        assert result == game

    def test_nondeterministic_field_not_aliased(self) -> None:
        """Non-deterministic field assignment should not be aliased."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    stored = GG.evaluate(k);
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """)
        ns = _make_nondet_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        assert result == game

    def test_does_not_replace_in_same_method(self) -> None:
        """Field alias should only replace in OTHER methods."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    stored = GG.evaluate(k);
                    BitString<n> x = GG.evaluate(k);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # Same method -- should not replace (that's DeduplicateDeterministicCalls' job)
        assert result == game

    def test_field_reassigned_after_alias_no_replacement(self) -> None:
        """If the alias field is overwritten after the det call, don't replace."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    stored = GG.evaluate(k);
                    BitString<n> zero = 0^n;
                    stored = zero;
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # stored is overwritten -- must not replace
        assert result == game

    def test_field_reassigned_in_other_method_no_replacement(self) -> None:
        """If the alias field is assigned in a different method, don't replace."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    stored = GG.evaluate(k);
                }
                Void Reset() {
                    BitString<n> zero = 0^n;
                    stored = zero;
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # stored may be overwritten by Reset -- must not replace
        assert result == game

    def test_arg_field_modified_in_other_method_no_replacement(self) -> None:
        """If an argument field is modified by another method, don't replace."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    stored = GG.evaluate(k);
                }
                Void Modify() {
                    BitString<n> k2 <- BitString<n>;
                    k = k2;
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # k may be changed by Modify -- must not replace
        assert result == game

    def test_arg_field_reassigned_after_alias_no_replacement(self) -> None:
        """If an argument field is reassigned after the alias, don't replace."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> k2;
                BitString<n> stored;
                Void Initialize() {
                    stored = GG.evaluate(k);
                    BitString<n> fresh <- BitString<n>;
                    k = fresh;
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # k is reassigned after stored = GG.evaluate(k) -- must not replace
        assert result == game

    def test_field_reassigned_in_conditional_no_replacement(self) -> None:
        """If alias field is reassigned inside a conditional, don't replace."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Bool flag;
                Void Initialize() {
                    stored = GG.evaluate(k);
                    if (flag) {
                        BitString<n> zero = 0^n;
                        stored = zero;
                    }
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # stored may be overwritten in the if-branch -- must not replace
        assert result == game

    def test_immutable_field_still_replaced(self) -> None:
        """Normal case: field and args never modified -> replacement is sound."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    BitString<n> key <- BitString<n>;
                    k = key;
                    stored = GG.evaluate(k);
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # k and stored are not reassigned after the alias and not in other methods
        oracle = result.methods[1]
        ret = oracle.block.statements[0]
        assert isinstance(ret, frog_ast.ReturnStatement)
        assert isinstance(ret.expression, frog_ast.Variable)
        assert ret.expression.name == "stored"

    def test_alias_in_oracle_not_initialize_no_replacement(self) -> None:
        """If the alias is in an oracle (not Initialize), don't replace."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> stored;
                Void Initialize() {
                }
                Void Setup() {
                    stored = GG.evaluate(0^n);
                }
                BitString<n> Oracle() {
                    return GG.evaluate(0^n);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # Alias is in Setup (oracle), not Initialize -- adversary might
        # call Oracle before Setup, reading uninitialized stored
        assert result == game

    def test_arg_field_mutated_via_array_access_no_replacement(self) -> None:
        """If an argument field is mutated via element assignment, don't replace."""
        prim = frog_parser.parse_primitive_file("""
            Primitive H(Int n) {
                Set DataArray = Array<BitString<n>, 2>;
                deterministic BitString<n> hash(DataArray d);
            }
            """)
        ns: frog_ast.Namespace = {"H": prim, "HH": prim}
        game = frog_parser.parse_game("""
            Game Foo(H HH) {
                Array<BitString<n>, 2> data;
                BitString<n> stored;
                Void Initialize() {
                    stored = HH.hash(data);
                }
                Void Modify() {
                    BitString<n> x <- BitString<n>;
                    data[0] = x;
                }
                BitString<n> Oracle() {
                    return HH.hash(data);
                }
            }
            """)
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # data is mutated via data[0] = x in Modify -- must not replace
        assert result == game

    def test_alias_field_mutated_via_array_access_no_replacement(self) -> None:
        """If the alias field is mutated via element assignment, don't replace."""
        prim = frog_parser.parse_primitive_file("""
            Primitive H(Int n) {
                Set DataArray = Array<BitString<n>, 2>;
                deterministic DataArray compute(BitString<n> x);
            }
            """)
        ns: frog_ast.Namespace = {"H": prim, "HH": prim}
        game = frog_parser.parse_game("""
            Game Foo(H HH) {
                BitString<n> k;
                Array<BitString<n>, 2> stored;
                Void Initialize() {
                    stored = HH.compute(k);
                }
                Void Modify() {
                    BitString<n> x <- BitString<n>;
                    stored[0] = x;
                }
                Array<BitString<n>, 2> Oracle() {
                    return HH.compute(k);
                }
            }
            """)
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # stored is mutated via stored[0] = x in Modify -- must not replace
        assert result == game


def _make_pair_namespace() -> frog_ast.Namespace:
    """Namespace with primitive G whose ``compute`` is deterministic and takes
    two args: a BitString and a key derived from another deterministic call.
    Used to test alias-aware matching of CSE'd locals."""
    prim = frog_parser.parse_primitive_file("""
        Primitive G(Int n) {
            deterministic BitString<n> base();
            deterministic BitString<n> compute(BitString<n> a, BitString<n> b);
        }
        """)
    return {"G": prim, "GG": prim}


class TestCrossMethodFieldAliasAliasAware:
    """Tests for alias-aware matching: CSE'd local that aliases a deterministic
    call should be expanded so a structurally-different call (with the literal
    deterministic call inlined) still matches."""

    def test_cse_local_in_init_matches_inline_call_in_oracle(self) -> None:
        """field_x = G.compute(local, k) where local = G.base(), and
        Oracle has G.compute(G.base(), k) directly -> Oracle's call replaced."""
        ns = _make_pair_namespace()
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    BitString<n> g = GG.base();
                    stored = GG.compute(g, k);
                }
                BitString<n> Oracle() {
                    return GG.compute(GG.base(), k);
                }
            }
            """)
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        oracle = result.methods[1]
        ret = oracle.block.statements[0]
        assert isinstance(ret, frog_ast.ReturnStatement)
        assert isinstance(ret.expression, frog_ast.Variable)
        assert ret.expression.name == "stored"

    def test_cse_local_on_both_sides(self) -> None:
        """field_x = G.compute(g_init, k) with g_init = G.base() in Init,
        and Oracle has g_oracle = G.base(); G.compute(g_oracle, k);
        Oracle's call replaced (after expansion both sides match)."""
        ns = _make_pair_namespace()
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    BitString<n> g_init = GG.base();
                    stored = GG.compute(g_init, k);
                }
                BitString<n> Oracle() {
                    BitString<n> g_oracle = GG.base();
                    BitString<n> v = GG.compute(g_oracle, k);
                    return v;
                }
            }
            """)
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        oracle = result.methods[1]
        # The GG.compute(g_oracle, k) call in Oracle's `v = ...` should be
        # replaced with `stored`.
        assign = oracle.block.statements[1]
        assert isinstance(assign, frog_ast.Assignment)
        assert isinstance(assign.value, frog_ast.Variable)
        assert assign.value.name == "stored"

    def test_alias_to_sample_not_treated_as_stable(self) -> None:
        """If the local alias references a sampled var, don't treat it as
        stable: sampled values change across method invocations.

        Soundness Gap B: a local that depends on a sample is not invariant.
        """
        prim = frog_parser.parse_primitive_file("""
            Primitive G(Int n) {
                deterministic BitString<n> compute(BitString<n> a);
            }
            """)
        ns: frog_ast.Namespace = {"G": prim, "GG": prim}
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> stored;
                Void Initialize() {
                    BitString<n> r <- BitString<n>;
                    BitString<n> alias = r;
                    stored = GG.compute(alias);
                }
                BitString<n> Oracle() {
                    BitString<n> r2 <- BitString<n>;
                    return GG.compute(r2);
                }
            }
            """)
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # `alias` is bound to a sampled `r`, not stable. The field RHS uses
        # `alias`, which is non-stable, so the field should NOT be treated as
        # an alias source.
        assert result == game

    def test_alias_reassigned_local_no_expansion(self) -> None:
        """A local re-bound twice is not stable.

        Soundness Gap B variant: only single-assignment locals qualify.
        """
        ns = _make_pair_namespace()
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    BitString<n> g = GG.base();
                    g = 0^n;
                    stored = GG.compute(g, k);
                }
                BitString<n> Oracle() {
                    return GG.compute(GG.base(), k);
                }
            }
            """)
        result = CrossMethodFieldAliasTransformer(proof_namespace=ns).transform(game)
        # `g` is assigned twice in Initialize; alias map must reject it. So
        # the field RHS `GG.compute(g, k)` has a non-stable local `g`, and
        # the transform should leave the game unchanged.
        assert result == game
