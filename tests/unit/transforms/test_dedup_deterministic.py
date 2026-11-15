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
    written_before_reached_within,
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


def _make_det_int_namespace() -> frog_ast.Namespace:
    """Namespace with primitive G: ``evaluate`` and ``evalInt`` deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive G(Int n) {
            deterministic BitString<n> evaluate(BitString<n> x);
            deterministic BitString<n> evalInt(Int c);
        }
        """)
    return {"G": prim}


def _dedup(source: str) -> frog_ast.Method:
    return DeduplicateDeterministicCallsTransformer(
        proof_namespace=_make_det_int_namespace()
    ).transform(frog_parser.parse_method(source))


class TestDedupWriteInsideHoldingStatement:
    """F-385: the merged call is placed before the first statement holding a
    call, so a write that can run between that place and any call breaks the
    merge, including writes inside the statements that hold the calls."""

    def test_f385_both_calls_in_loop_writing_argument_not_deduped(self) -> None:
        """Both calls in one loop body that writes ``k`` between them: the
        second call reads the new ``k``. Nothing is merged, at the loop's
        level (above the loop) or inside its body (F-201)."""
        source = """
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = k;
                BitString<n> b = k;
                for (Int i = 0 to 1) {
                    a = G.evaluate(k);
                    k = a;
                    b = G.evaluate(k);
                }
                return [a, b];
            }
            """
        assert _dedup(source) == frog_parser.parse_method(source)

    def test_f385_loop_writing_argument_after_both_calls_not_deduped(self) -> None:
        """A write after both calls in the loop body still runs before the
        next iteration's calls."""
        source = """
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = k;
                BitString<n> b = k;
                for (Int i = 0 to 2) {
                    a = G.evaluate(k);
                    b = G.evaluate(k);
                    k = b;
                }
                return [a, b];
            }
            """
        expected = frog_parser.parse_method("""
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = k;
                BitString<n> b = k;
                for (Int i = 0 to 2) {
                    BitString<n> __determ_0__ = G.evaluate(k);
                    a = __determ_0__;
                    b = __determ_0__;
                    k = b;
                }
                return [a, b];
            }
            """)
        # Not hoisted above the loop; merged inside the body, where k is
        # stable between the two calls.
        assert _dedup(source) == expected

    def test_f385_last_statement_loop_writes_argument_not_deduped(self) -> None:
        """The first call is before the loop, the second inside a loop that
        writes ``k`` after it: the statement holding the last call is
        scanned too."""
        source = """
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = G.evaluate(k);
                BitString<n> b = k;
                for (Int i = 0 to 2) {
                    b = G.evaluate(k);
                    k = b;
                }
                return [a, b];
            }
            """
        assert _dedup(source) == frog_parser.parse_method(source)

    def test_f385_uniq_insertion_between_calls_not_deduped(self) -> None:
        """``x <-uniq[S] T;`` adds ``x`` to ``S``, so ``|S|`` changes between
        the calls."""
        source = """
            [BitString<n>, BitString<n>] f(Set<BitString<n>> S) {
                BitString<n> a = G.evalInt(|S|);
                BitString<n> x <-uniq[S] BitString<n>;
                BitString<n> b = G.evalInt(|S|);
                return [a, b];
            }
            """
        assert _dedup(source) == frog_parser.parse_method(source)

    def test_f385_loop_binder_argument_not_hoisted(self) -> None:
        """An argument naming the loop binder is not hoisted out of the loop
        (it would leave the binder's scope); the calls merge inside the
        body."""
        expected = frog_parser.parse_method("""
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = k;
                BitString<n> b = k;
                for (Int i = 0 to 1) {
                    BitString<n> __determ_0__ = G.evalInt(i);
                    a = __determ_0__;
                    b = __determ_0__;
                }
                return [a, b];
            }
            """)
        assert _dedup("""
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = k;
                BitString<n> b = k;
                for (Int i = 0 to 1) {
                    a = G.evalInt(i);
                    b = G.evalInt(i);
                }
                return [a, b];
            }
            """) == expected

    def test_f385_loop_local_argument_not_hoisted(self) -> None:
        """An argument naming a local declared in the loop body is not hoisted
        above the loop."""
        expected = frog_parser.parse_method("""
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = k;
                BitString<n> b = k;
                for (Int i = 0 to 1) {
                    BitString<n> x = k + a;
                    BitString<n> __determ_0__ = G.evaluate(x);
                    a = __determ_0__;
                    b = __determ_0__;
                }
                return [a, b];
            }
            """)
        assert _dedup("""
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = k;
                BitString<n> b = k;
                for (Int i = 0 to 1) {
                    BitString<n> x = k + a;
                    a = G.evaluate(x);
                    b = G.evaluate(x);
                }
                return [a, b];
            }
            """) == expected

    def test_f385_loop_without_write_still_deduped(self) -> None:
        """Positive control: a loop that never writes ``k`` keeps both calls
        on one value, so they merge above the loop."""
        expected = frog_parser.parse_method("""
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = k;
                BitString<n> b = k;
                BitString<n> __determ_0__ = G.evaluate(k);
                for (Int i = 0 to 1) {
                    a = __determ_0__;
                    b = __determ_0__;
                }
                return [a, b];
            }
            """)
        assert _dedup("""
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = k;
                BitString<n> b = k;
                for (Int i = 0 to 1) {
                    a = G.evaluate(k);
                    b = G.evaluate(k);
                }
                return [a, b];
            }
            """) == expected

    def test_f385_write_after_last_call_in_its_statement_still_deduped(
        self,
    ) -> None:
        """Positive control: a simple statement evaluates its calls before its
        own write, so ``k = G.evaluate(k) + G.evaluate(k);`` and a last call
        in ``k = G.evaluate(k);`` still merge."""
        expected = frog_parser.parse_method("""
            BitString<n> f(BitString<n> k) {
                BitString<n> __determ_0__ = G.evaluate(k);
                k = __determ_0__ + __determ_0__;
                return k;
            }
            """)
        assert _dedup("""
            BitString<n> f(BitString<n> k) {
                k = G.evaluate(k) + G.evaluate(k);
                return k;
            }
            """) == expected
        expected = frog_parser.parse_method("""
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> __determ_0__ = G.evaluate(k);
                BitString<n> a = __determ_0__;
                k = __determ_0__;
                return [a, k];
            }
            """)
        assert _dedup("""
            [BitString<n>, BitString<n>] f(BitString<n> k) {
                BitString<n> a = G.evaluate(k);
                k = G.evaluate(k);
                return [a, k];
            }
            """) == expected

    def test_f385_branch_write_after_condition_call_still_deduped(self) -> None:
        """Positive control: a branch body runs after its ``if`` condition, so
        a write there does not reach the condition's call when the if is the
        last statement holding a call."""
        expected = frog_parser.parse_method("""
            BitString<n> f(BitString<n> k, BitString<n> t) {
                BitString<n> __determ_0__ = G.evaluate(k);
                BitString<n> a = __determ_0__;
                if (__determ_0__ == t) {
                    k = t;
                }
                return a + k;
            }
            """)
        assert _dedup("""
            BitString<n> f(BitString<n> k, BitString<n> t) {
                BitString<n> a = G.evaluate(k);
                if (G.evaluate(k) == t) {
                    k = t;
                }
                return a + k;
            }
            """) == expected


def _first_statement(source: str) -> frog_ast.Statement:
    return frog_parser.parse_method(source).block.statements[0]


def _holds_eval(node: frog_ast.ASTNode) -> bool:
    return "G.evaluate" in str(node)


class TestWrittenBeforeReachedWithin:
    """The region helper shared by Deduplicate Deterministic Calls (F-385)
    and Inline Single-Use Variables (F-149)."""

    def test_block_write_before_last_point(self) -> None:
        """In a block, a write between two points runs before the second
        (here ``k = a;``, and the declaration of ``a``); the last statement's
        own write (``b``) runs after its point."""
        stmt = _first_statement("""
            Void f(BitString<n> k) {
                if (true) {
                    BitString<n> a = G.evaluate(k);
                    k = a;
                    BitString<n> b = G.evaluate(k);
                }
            }
            """)
        assert written_before_reached_within(stmt, _holds_eval, {"k"})
        assert written_before_reached_within(stmt, _holds_eval, {"a"})
        assert not written_before_reached_within(stmt, _holds_eval, {"b"})

    def test_block_write_after_last_point(self) -> None:
        """A write after every point in a block reaches none of them."""
        stmt = _first_statement("""
            Void f(BitString<n> k) {
                if (true) {
                    BitString<n> a = G.evaluate(k);
                    BitString<n> b = G.evaluate(k);
                    k = b;
                }
            }
            """)
        assert not written_before_reached_within(stmt, _holds_eval, {"k"})

    def test_if_points_in_two_branches(self) -> None:
        """Only one branch runs: a write in one branch reaches only the
        points after it in that branch."""
        stmt = _first_statement("""
            Void f(Bool c, BitString<n> k) {
                if (c) {
                    k = 0^n;
                } else {
                    BitString<n> a = G.evaluate(k);
                    k = a;
                }
            }
            """)
        assert not written_before_reached_within(stmt, _holds_eval, {"k"})
        stmt = _first_statement("""
            Void f(Bool c, BitString<n> k) {
                if (c) {
                    BitString<n> a = G.evaluate(k);
                } else {
                    k = 0^n;
                    BitString<n> b = G.evaluate(k);
                }
            }
            """)
        assert written_before_reached_within(stmt, _holds_eval, {"k"})

    def test_loop_write_anywhere(self) -> None:
        """In a loop, a write after the point runs before the next
        iteration's point."""
        stmt = _first_statement("""
            Void f(BitString<n> k) {
                for (Int i = 0 to 2) {
                    BitString<n> a = G.evaluate(k);
                    k = a;
                }
            }
            """)
        assert written_before_reached_within(stmt, _holds_eval, {"k"})
        assert written_before_reached_within(stmt, _holds_eval, {"i"})
