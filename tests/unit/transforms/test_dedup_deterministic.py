"""Tests for DeduplicateDeterministicCalls transform.

Verifies that duplicate calls to deterministic primitive methods within a
single block are extracted into a fresh local variable, while non-deterministic
calls and single occurrences are left untouched.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.inlining import (
    DeduplicateDeterministicCalls,
    DeduplicateDeterministicCallsTransformer,
)
from proof_frog.visitors import NameTypeMap


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


def _make_zeroarg_det_namespace() -> frog_ast.Namespace:
    """Namespace with primitive NG whose ``Generator`` is a zero-arg deterministic call."""
    prim = frog_parser.parse_primitive_file("""
        Primitive NG(Set GroupElemSpace) {
            Set GroupElem = GroupElemSpace;
            deterministic GroupElem Generator();
        }
        """)
    return {"NG": prim}


def _make_zeroarg_nondet_namespace() -> frog_ast.Namespace:
    """Namespace with primitive NG whose ``Generator`` is zero-arg but NOT deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive NG(Set GroupElemSpace) {
            Set GroupElem = GroupElemSpace;
            GroupElem Generator();
        }
        """)
    return {"NG": prim}


class TestDeduplicateDeterministicCalls:
    """Tests for DeduplicateDeterministicCallsTransformer."""

    def test_duplicate_in_tuple(self) -> None:
        """Two identical deterministic calls in a tuple literal are extracted."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                return [G.evaluate(k), G.evaluate(k)];
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                BitString<n> __determ_0__ = G.evaluate(k);
                return [__determ_0__, __determ_0__];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_duplicate_across_statements(self) -> None:
        """Two assignments with the same deterministic call are deduplicated."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                BitString<n> a = G.evaluate(k);
                BitString<n> b = G.evaluate(k);
                return [a, b];
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                BitString<n> __determ_0__ = G.evaluate(k);
                BitString<n> a = __determ_0__;
                BitString<n> b = __determ_0__;
                return [a, b];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_triple_occurrence(self) -> None:
        """Three identical calls are all replaced with one variable."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                BitString<n> a = G.evaluate(k);
                BitString<n> b = G.evaluate(k);
                BitString<n> c = G.evaluate(k);
                return [a, b, c];
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                BitString<n> __determ_0__ = G.evaluate(k);
                BitString<n> a = __determ_0__;
                BitString<n> b = __determ_0__;
                BitString<n> c = __determ_0__;
                return [a, b, c];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_nondeterministic_not_deduped(self) -> None:
        """Non-deterministic calls should NOT be deduplicated."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                return [G.evaluate(k), G.evaluate(k)];
            }
            """)
        original = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                return [G.evaluate(k), G.evaluate(k)];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_nondet_namespace()
        ).transform(method)
        assert result == original

    def test_single_occurrence_unchanged(self) -> None:
        """A single deterministic call should not be extracted."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                return G.evaluate(k);
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                return G.evaluate(k);
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_different_args_not_deduped(self) -> None:
        """Same function with different args should not be deduplicated."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k, BitString<n> j) {
                return [G.evaluate(k), G.evaluate(j)];
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> k, BitString<n> j) {
                return [G.evaluate(k), G.evaluate(j)];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_arg_element_mutated_between_calls_not_deduped(self) -> None:
        """If an argument's element is mutated between two structurally equal
        calls, they must NOT be deduplicated (e.g., M[k] = new_val)."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                BitString<n> a = G.evaluate(k);
                k[0] = 1;
                BitString<n> b = G.evaluate(k);
                return [a, b];
            }
            """)
        original = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                BitString<n> a = G.evaluate(k);
                k[0] = 1;
                BitString<n> b = G.evaluate(k);
                return [a, b];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert (
            result == original
        ), "Calls with element-mutated argument should not be deduplicated"

    def test_arg_reassigned_between_calls_not_deduped(self) -> None:
        """If an argument is reassigned between two structurally equal calls,
        they must NOT be deduplicated (the argument has different values)."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                BitString<n> a = G.evaluate(k);
                BitString<n> k <- BitString<n>;
                BitString<n> b = G.evaluate(k);
                return [a, b];
            }
            """)
        original = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                BitString<n> a = G.evaluate(k);
                BitString<n> k <- BitString<n>;
                BitString<n> b = G.evaluate(k);
                return [a, b];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert (
            result == original
        ), "Calls with reassigned argument variable should not be deduplicated"

    def test_zero_arg_duplicate_deduped(self) -> None:
        """Two zero-arg deterministic calls in a block are extracted."""
        method = frog_parser.parse_method("""
            Void f() {
                GroupElemSpace a = NG.Generator();
                GroupElemSpace b = NG.Generator();
                return [a, b];
            }
            """)
        expected = frog_parser.parse_method("""
            Void f() {
                GroupElem __determ_0__ = NG.Generator();
                GroupElemSpace a = __determ_0__;
                GroupElemSpace b = __determ_0__;
                return [a, b];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_zeroarg_det_namespace()
        ).transform(method)
        assert result == expected

    def test_zero_arg_nondeterministic_not_deduped(self) -> None:
        """Zero-arg non-deterministic calls should NOT be deduplicated."""
        method = frog_parser.parse_method("""
            Void f() {
                GroupElemSpace a = NG.Generator();
                GroupElemSpace b = NG.Generator();
                return [a, b];
            }
            """)
        original = frog_parser.parse_method("""
            Void f() {
                GroupElemSpace a = NG.Generator();
                GroupElemSpace b = NG.Generator();
                return [a, b];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_zeroarg_nondet_namespace()
        ).transform(method)
        assert result == original

    def test_counter_advances_past_existing_names(self) -> None:
        """If the block already contains a ``__determ_N__`` declaration (e.g.
        from an earlier pipeline iteration), the fresh name must not collide
        with it, even though the transformer's counter starts at 0.
        """
        method = frog_parser.parse_method("""
            Void f(BitString<n> x, BitString<n> y) {
                BitString<n> __determ_0__ = G.evaluate(x);
                BitString<n> a = G.evaluate(y);
                BitString<n> b = G.evaluate(y);
                return [__determ_0__, a, b];
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> x, BitString<n> y) {
                BitString<n> __determ_0__ = G.evaluate(x);
                BitString<n> __determ_1__ = G.evaluate(y);
                BitString<n> a = __determ_1__;
                BitString<n> b = __determ_1__;
                return [__determ_0__, a, b];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_zero_arg_single_occurrence_unchanged(self) -> None:
        """A single zero-arg deterministic call should not be extracted."""
        method = frog_parser.parse_method("""
            Void f() {
                return NG.Generator();
            }
            """)
        expected = frog_parser.parse_method("""
            Void f() {
                return NG.Generator();
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_zeroarg_det_namespace()
        ).transform(method)
        assert result == expected

    def test_duplicate_across_if_condition_and_return(self) -> None:
        """A deterministic call appearing in an if-condition and a later
        return is deduplicated by extracting before the if-statement."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k, BitString<n> target) {
                if (G.evaluate(k) == target) {
                    return target;
                }
                return G.evaluate(k);
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> k, BitString<n> target) {
                BitString<n> __determ_0__ = G.evaluate(k);
                if (__determ_0__ == target) {
                    return target;
                }
                return __determ_0__;
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_duplicate_in_two_if_conditions(self) -> None:
        """A deterministic call appearing in two separate if-conditions is
        deduplicated."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k, BitString<n> target) {
                if (G.evaluate(k) == target) {
                    return target;
                }
                if (G.evaluate(k) == k) {
                    return k;
                }
                return target;
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> k, BitString<n> target) {
                BitString<n> __determ_0__ = G.evaluate(k);
                if (__determ_0__ == target) {
                    return target;
                }
                if (__determ_0__ == k) {
                    return k;
                }
                return target;
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_dedup_across_return_in_if_body(self) -> None:
        """Two top-level deterministic calls separated by an ``if`` whose
        body returns early. Dedup is sound: the call's value is deterministic
        and its args are unmutated, so extracting the call ahead of the
        if-statement preserves both the call's value and its evaluation
        count on every execution path (the first call always runs before
        the if; the extracted version also runs once before the if).
        """
        method = frog_parser.parse_method("""
            Void f(BitString<n> k, BitString<n> target) {
                BitString<n> first = G.evaluate(k);
                if (first == target) {
                    return target;
                }
                return G.evaluate(k);
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> k, BitString<n> target) {
                BitString<n> __determ_0__ = G.evaluate(k);
                BitString<n> first = __determ_0__;
                if (first == target) {
                    return target;
                }
                return __determ_0__;
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_if_body_writes_to_arg_blocks_dedup(self) -> None:
        """When the first call is in an if-condition and the if-body
        reassigns an argument variable, dedup must not fire (a later call
        would see the new value, not the captured one)."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k, BitString<n> target) {
                if (G.evaluate(k) == target) {
                    k = target;
                }
                return G.evaluate(k);
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> k, BitString<n> target) {
                if (G.evaluate(k) == target) {
                    k = target;
                }
                return G.evaluate(k);
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_f201_first_statement_writes_arg_not_deduped(self) -> None:
        """F-201: when the FIRST occurrence's own statement writes an argument
        variable (`k = G.evaluate(k);`), the write happens after that call is
        evaluated and before the second call, so the two calls read different
        values (`G(k0)` vs `G(G(k0))`) and must NOT be deduplicated. The
        intermediate-region scan excluded the first statement, missing this."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                k = G.evaluate(k);
                return G.evaluate(k);
            }
            """)
        expected = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                k = G.evaluate(k);
                return G.evaluate(k);
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_f201_first_statement_writes_nonarg_still_deduped(self) -> None:
        """F-201 positive control: when the first occurrence's statement writes a
        NON-argument variable (`x = G.evaluate(k);`), the argument `k` is stable
        between the two calls, so the deduplication must still fire."""
        method = frog_parser.parse_method("""
            Void f(BitString<n> k) {
                BitString<n> x = G.evaluate(k);
                BitString<n> y = G.evaluate(k);
                return [x, y];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        # The second G.evaluate(k) is replaced by a reference to the first result.
        assert str(result) != str(method), "stable-arg dedup should still fire"


def _make_draw_namespace() -> frog_ast.Namespace:
    """Namespace with primitive R: ``Det`` deterministic, ``Draw`` not."""
    prim = frog_parser.parse_primitive_file("""
        Primitive R(Int q) {
            ModInt<q> Draw();
            deterministic ModInt<q> Det(ModInt<q> x);
        }
        """)
    return {"R": prim}


def _let_function_types() -> NameTypeMap:
    """Proof let types declaring ``H`` as a ``Function<ModInt<q>, ModInt<q>>``."""
    let_types = NameTypeMap()
    mod_q = frog_ast.ModIntType(frog_ast.Variable("q"))
    let_types.set("H", frog_ast.FunctionType(mod_q, mod_q))
    return let_types


class TestDedupNondeterministicArgument:
    """F-363 / F-202: equal deterministic calls are merged only when their
    arguments are deterministic too, because each occurrence evaluates its
    own arguments."""

    def test_f363_nondeterministic_argument_not_deduped(self) -> None:
        """`[R.Det(R.Draw()), R.Det(R.Draw())]` draws twice; merging the two
        calls would make the components always equal."""
        source = """
            [ModInt<q>, ModInt<q>] f() {
                return [R.Det(R.Draw()), R.Det(R.Draw())];
            }
            """
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_draw_namespace()
        ).transform(frog_parser.parse_method(source))
        assert result == frog_parser.parse_method(source)

    def test_f202_nondeterministic_call_inside_argument_not_deduped(self) -> None:
        """The check covers the whole argument, not only its outermost node:
        `R.Draw()` nested in `R.Draw() + x` still draws once per call."""
        source = """
            [ModInt<q>, ModInt<q>] f(ModInt<q> x) {
                return [R.Det(R.Draw() + x), R.Det(R.Draw() + x)];
            }
            """
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_draw_namespace()
        ).transform(frog_parser.parse_method(source))
        assert result == frog_parser.parse_method(source)

    def test_f363_deterministic_nested_argument_still_deduped(self) -> None:
        """Positive control: a nested deterministic call in the argument does
        not block the merge."""
        method = frog_parser.parse_method("""
            [ModInt<q>, ModInt<q>] f(ModInt<q> x) {
                return [R.Det(R.Det(x)), R.Det(R.Det(x))];
            }
            """)
        expected = frog_parser.parse_method("""
            [ModInt<q>, ModInt<q>] f(ModInt<q> x) {
                ModInt<q> __determ_0__ = R.Det(R.Det(x));
                return [__determ_0__, __determ_0__];
            }
            """)
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_draw_namespace()
        ).transform(method)
        assert result == expected

    def test_f363_let_function_argument_still_deduped(self) -> None:
        """Positive control: a call to a `let:`-bound Function is
        deterministic, so equal calls taking it as an argument are merged.
        The pass reads the let types from the pipeline context."""
        game = frog_parser.parse_game("""
            Game T(Int q) {
                [ModInt<q>, ModInt<q>] f(ModInt<q> x) {
                    return [R.Det(H(x)), R.Det(H(x))];
                }
            }
            """)
        expected = frog_parser.parse_game("""
            Game T(Int q) {
                [ModInt<q>, ModInt<q>] f(ModInt<q> x) {
                    ModInt<q> __determ_0__ = R.Det(H(x));
                    return [__determ_0__, __determ_0__];
                }
            }
            """)
        ctx = PipelineContext(
            variables={},
            proof_let_types=_let_function_types(),
            proof_namespace=_make_draw_namespace(),
            subsets_pairs=[],
        )
        assert DeduplicateDeterministicCalls().apply(game, ctx) == expected

    def test_f363_function_resampled_between_calls_not_deduped(self) -> None:
        """A local Function re-sampled between the two calls changes the
        argument's value, even though calling a Function is deterministic."""
        source = """
            [ModInt<q>, ModInt<q>] f(ModInt<q> x) {
                Function<ModInt<q>, ModInt<q>> H <- Function<ModInt<q>, ModInt<q>>;
                ModInt<q> a = R.Det(H(x));
                H <- Function<ModInt<q>, ModInt<q>>;
                ModInt<q> b = R.Det(H(x));
                return [a, b];
            }
            """
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_draw_namespace(),
            proof_let_types=_let_function_types(),
        ).transform(frog_parser.parse_method(source))
        assert result == frog_parser.parse_method(source)
