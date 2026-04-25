"""Tests for HoistDeterministicCallToInitialize transform."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import (
    HoistDeterministicCallToInitializeTransformer,
)
from proof_frog.visitors import NameTypeMap, SearchVisitor


def _walk_funccalls(node: frog_ast.ASTNode) -> list[frog_ast.FuncCall]:
    """Collect all FuncCall nodes inside *node* (for assertions)."""
    result: list[frog_ast.FuncCall] = []

    def _collect(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, frog_ast.FuncCall):
            result.append(n)
        return False

    SearchVisitor(_collect).visit(node)
    return result


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


class TestHoistDeterministicCallToInitialize:
    """Red/green cases for the Hoist Deterministic Call to Initialize pass."""

    def test_multi_oracle_call_hoisted_into_initialize(self) -> None:
        """Two oracles calling G.evaluate(seed) get a cached field."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
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
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)

        # A new field of type BitString<n> must be added.
        assert len(result.fields) == len(game.fields) + 1
        new_field_name = next(
            f.name for f in result.fields if f.name not in {"seed"}
        )

        # Initialize should end with: <new_field> = GG.evaluate(seed);
        init = result.methods[0]
        assert init.signature.name == "Initialize"
        last_stmt = init.block.statements[-1]
        assert isinstance(last_stmt, frog_ast.Assignment)
        assert isinstance(last_stmt.var, frog_ast.Variable)
        assert last_stmt.var.name == new_field_name
        assert isinstance(last_stmt.value, frog_ast.FuncCall)

        # Both oracles should return Variable(new_field_name), not the call.
        for oracle in result.methods[1:]:
            ret = oracle.block.statements[0]
            assert isinstance(ret, frog_ast.ReturnStatement)
            assert isinstance(ret.expression, frog_ast.Variable)
            assert ret.expression.name == new_field_name

    def test_initialize_with_return_not_hoisted(self) -> None:
        """If Initialize contains any ReturnStatement, hoisting would be unsound.

        Appending the hoisted assignment at the end of Initialize would be
        skipped on paths that return early, leaving the new field uninitialized
        while the oracle still reads it. Well-typed FrogLang rejects early
        returns in Void methods, but we add a defensive guard in case any
        upstream pipeline (or a future transform) ever produces such a shape.
        """
        game = frog_parser.parse_game("""
            Game Foo(G GG, Bool cond) {
                BitString<n> seed = 0^n;
                Void Initialize() {
                    seed <- BitString<n>;
                }
                BitString<n> Get() {
                    return GG.evaluate(seed);
                }
            }
            """)
        # Inject a ReturnStatement into Initialize to simulate a shape that the
        # grammar/typechecker would reject but could arise from a buggy
        # transform or a non-FrogLang frontend building the AST directly.
        init = game.methods[0]
        assert init.signature.name == "Initialize"
        injected_return = frog_ast.ReturnStatement(frog_ast.Integer(0))
        init.block = frog_ast.Block(
            [injected_return, *list(init.block.statements)]
        )

        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert result == game

    def test_single_oracle_call_hoisted(self) -> None:
        """A deterministic call in a single oracle should still be hoisted.

        This matches the canonical form produced when a reduction's Initialize
        caches challenger.Query() — the result lives in a field regardless of
        how many oracles read it.
        """
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> seed;
                Void Initialize() {
                    seed <- BitString<n>;
                }
                BitString<n> Get() {
                    return GG.evaluate(seed);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert len(result.fields) == len(game.fields) + 1
        oracle = result.methods[1]
        ret = oracle.block.statements[0]
        assert isinstance(ret, frog_ast.ReturnStatement)
        assert isinstance(ret.expression, frog_ast.Variable)

    def test_defers_to_existing_field_alias(self) -> None:
        """If an existing field in Initialize already aliases the call, do nothing.

        That case is handled by CrossMethodFieldAlias; hoisting would duplicate
        the alias as a second field.
        """
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> seed;
                BitString<n> cached;
                Void Initialize() {
                    seed <- BitString<n>;
                    cached = GG.evaluate(seed);
                }
                BitString<n> Get() {
                    return GG.evaluate(seed);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert result == game

    def test_local_arg_not_hoisted(self) -> None:
        """Calls whose arguments depend on method-local variables must not be hoisted."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                Void Initialize() {
                }
                BitString<n> Get(BitString<n> x) {
                    return GG.evaluate(x);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert result == game

    def test_field_reassigned_in_oracle_not_hoisted(self) -> None:
        """If an arg-field is reassigned in an oracle, hoisting would be unsound."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> seed;
                Void Initialize() {
                    seed <- BitString<n>;
                }
                BitString<n> Get1() {
                    return GG.evaluate(seed);
                }
                Void Reset() {
                    seed <- BitString<n>;
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert result == game

    def test_nondeterministic_call_not_hoisted(self) -> None:
        """Non-deterministic calls must not be hoisted (would change semantics)."""
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
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
            """)
        ns = _make_nondet_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert result == game


class TestHoistFunctionDRCalls:
    """Hoisting Function<D,R> variable calls (completeness extension).

    FrogLang treats a Function<D,R> variable call as deterministic: the same
    input always yields the same output, regardless of whether the function is
    sampled (ROM) or unsampled (standard-model). This test class covers the
    cases where a Function<D,R> call is hoisted into Initialize.
    """

    def test_sampled_function_field_hoisted(self) -> None:
        """Sampled Function<D,R> field: RF(seed) across two oracles is hoisted."""
        game = frog_parser.parse_game("""
            Game Foo() {
                BitString<8> seed;
                Function<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    seed <- BitString<8>;
                    RF <- Function<BitString<8>, BitString<16>>;
                }
                BitString<16> Get1() {
                    return RF(seed);
                }
                BitString<16> Get2() {
                    return RF(seed);
                }
            }
            """)
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace={}
        ).transform(game)

        # Expect one new field of type BitString<16> (the range type of RF)
        assert len(result.fields) == len(game.fields) + 1
        new_field = next(
            f for f in result.fields if f.name not in {"seed", "RF"}
        )
        assert isinstance(new_field.type, frog_ast.BitStringType)
        # Oracles should read the new field, not call RF directly
        for oracle in result.methods[1:]:
            ret = oracle.block.statements[0]
            assert isinstance(ret, frog_ast.ReturnStatement)
            assert isinstance(ret.expression, frog_ast.Variable)
            assert ret.expression.name == new_field.name

    def test_unsampled_function_from_let_types_hoisted(self) -> None:
        """Standard-model Function<D,R> from proof_let_types is hoisted."""
        game = frog_parser.parse_game("""
            Game Foo() {
                BitString<8> seed;
                Void Initialize() {
                    seed <- BitString<8>;
                }
                BitString<16> Get1() {
                    return H(seed);
                }
                BitString<16> Get2() {
                    return H(seed);
                }
            }
            """)
        let_types = NameTypeMap()
        let_types.set(
            "H",
            frog_ast.FunctionType(
                frog_ast.BitStringType(frog_ast.Integer(8)),
                frog_ast.BitStringType(frog_ast.Integer(16)),
            ),
        )
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace={}, proof_let_types=let_types
        ).transform(game)

        assert len(result.fields) == len(game.fields) + 1
        new_field = next(f for f in result.fields if f.name not in {"seed"})
        for oracle in result.methods[1:]:
            ret = oracle.block.statements[0]
            assert isinstance(ret, frog_ast.ReturnStatement)
            assert isinstance(ret.expression, frog_ast.Variable)
            assert ret.expression.name == new_field.name

    def test_function_param_hoisted(self) -> None:
        """Function<D,R> game parameter: RF(seed) is hoisted."""
        game = frog_parser.parse_game("""
            Game Foo(Function<BitString<8>, BitString<16>> RF) {
                BitString<8> seed;
                Void Initialize() {
                    seed <- BitString<8>;
                }
                BitString<16> Get1() {
                    return RF(seed);
                }
                BitString<16> Get2() {
                    return RF(seed);
                }
            }
            """)
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace={}
        ).transform(game)
        assert len(result.fields) == len(game.fields) + 1

    def test_function_call_local_arg_not_hoisted(self) -> None:
        """Function<D,R> called on a method-local must not be hoisted."""
        game = frog_parser.parse_game("""
            Game Foo() {
                Function<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    RF <- Function<BitString<8>, BitString<16>>;
                }
                BitString<16> Get(BitString<8> x) {
                    return RF(x);
                }
            }
            """)
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace={}
        ).transform(game)
        assert result == game

    def test_function_arg_field_reassigned_not_hoisted(self) -> None:
        """Arg-field reassigned in an oracle: Function<D,R> call must not hoist."""
        game = frog_parser.parse_game("""
            Game Foo() {
                BitString<8> seed;
                Function<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    seed <- BitString<8>;
                    RF <- Function<BitString<8>, BitString<16>>;
                }
                BitString<16> Get() {
                    return RF(seed);
                }
                Void Reset() {
                    seed <- BitString<8>;
                }
            }
            """)
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace={}
        ).transform(game)
        assert result == game

    def test_function_callee_field_reassigned_not_hoisted(self) -> None:
        """The Function<D,R> field itself reassigned in an oracle: no hoist.

        If the oracle re-samples RF, the cached value could stale. Soundness
        requires the callee function to be stable across oracle invocations
        just like the arguments are.
        """
        game = frog_parser.parse_game("""
            Game Foo() {
                BitString<8> seed;
                Function<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    seed <- BitString<8>;
                    RF <- Function<BitString<8>, BitString<16>>;
                }
                BitString<16> Get() {
                    return RF(seed);
                }
                Void Reset() {
                    RF <- Function<BitString<8>, BitString<16>>;
                }
            }
            """)
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace={}
        ).transform(game)
        assert result == game


def _make_group_namespace() -> frog_ast.Namespace:
    """Namespace with primitive NG whose ``Exp`` and ``Generator`` are deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive NG(Int n) {
            deterministic BitString<n> Generator();
            deterministic BitString<n> Exp(BitString<n> base, BitString<n> exponent);
        }
        """)
    return {"NG": prim}


class TestNestedDeterministicStableArgs:
    """Nested deterministic calls as stable arguments (design 2026-04-23)."""

    def test_nested_zero_arg_det_call_hoisted(self) -> None:
        """``NG.Exp(NG.Generator(), field_x)`` is hoisted into Initialize."""
        game = frog_parser.parse_game("""
            Game Foo(NG GG) {
                BitString<n> field_x;
                Void Initialize() {
                    field_x <- BitString<n>;
                }
                BitString<n> Get1() {
                    return GG.Exp(GG.Generator(), field_x);
                }
                BitString<n> Get2() {
                    return GG.Exp(GG.Generator(), field_x);
                }
            }
            """)
        ns = _make_group_namespace()
        ns["GG"] = ns["NG"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert len(result.fields) == len(game.fields) + 1
        new_field_name = next(
            f.name for f in result.fields if f.name not in {"field_x"}
        )
        init = result.methods[0]
        last_stmt = init.block.statements[-1]
        assert isinstance(last_stmt, frog_ast.Assignment)
        assert isinstance(last_stmt.var, frog_ast.Variable)
        assert last_stmt.var.name == new_field_name
        assert isinstance(last_stmt.value, frog_ast.FuncCall)
        for oracle in result.methods[1:]:
            ret = oracle.block.statements[0]
            assert isinstance(ret, frog_ast.ReturnStatement)
            assert isinstance(ret.expression, frog_ast.Variable)
            assert ret.expression.name == new_field_name

    def test_doubly_nested_det_calls_hoisted(self) -> None:
        """``F.inner(G.evaluate(field_x))`` hoists when both are deterministic."""
        ns = _make_det_namespace()
        prim_f = frog_parser.parse_primitive_file("""
            Primitive F(Int n) {
                deterministic BitString<n> inner(BitString<n> x);
            }
            """)
        ns["F"] = prim_f
        ns["FF"] = prim_f
        ns["GG"] = ns["G"]
        game = frog_parser.parse_game("""
            Game Foo(G GG, F FF) {
                BitString<n> field_x;
                Void Initialize() {
                    field_x <- BitString<n>;
                }
                BitString<n> Get1() {
                    return FF.inner(GG.evaluate(field_x));
                }
                BitString<n> Get2() {
                    return FF.inner(GG.evaluate(field_x));
                }
            }
            """)
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert len(result.fields) == len(game.fields) + 1

    def test_nested_nondet_call_not_hoisted(self) -> None:
        """A nested non-deterministic call disqualifies the outer candidate."""
        prim = frog_parser.parse_primitive_file("""
            Primitive NG(Int n) {
                BitString<n> Generator();
                deterministic BitString<n> Exp(BitString<n> base, BitString<n> exponent);
            }
            """)
        ns = {"NG": prim, "GG": prim}
        game = frog_parser.parse_game("""
            Game Foo(NG GG) {
                BitString<n> field_x;
                Void Initialize() {
                    field_x <- BitString<n>;
                }
                BitString<n> Get1() {
                    return GG.Exp(GG.Generator(), field_x);
                }
                BitString<n> Get2() {
                    return GG.Exp(GG.Generator(), field_x);
                }
            }
            """)
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert result == game

    def test_nested_field_reassigned_not_hoisted(self) -> None:
        """If a field appearing in a nested arg is reassigned, hoisting is unsound."""
        prim_f = frog_parser.parse_primitive_file("""
            Primitive F(Int n) {
                deterministic BitString<n> wrap(BitString<n> x);
            }
            """)
        ns = {"F": prim_f, "FF": prim_f}
        game = frog_parser.parse_game("""
            Game Foo(F FF) {
                BitString<n> field_x;
                Void Initialize() {
                    field_x <- BitString<n>;
                }
                BitString<n> Get1() {
                    return FF.wrap(FF.wrap(field_x));
                }
                Void Reset() {
                    field_x <- BitString<n>;
                }
            }
            """)
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert result == game

    def test_terminal_return_hoisted_with_return_rewrite(self) -> None:
        """Initialize with a terminal non-Void return: hoist + rewrite the return.

        The hoisted assignment must land *before* the terminal return, and
        any structural occurrence of the candidate in the return expression
        must be rewritten to the new field. Matches the shape of composed
        reductions where Initialize ends with ``return [..., candidate, ...];``.
        """
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<n> seed;
                BitString<n> ct;
                Void Initialize() {
                    seed <- BitString<n>;
                    ct <- BitString<n>;
                    return [ct, GG.evaluate(seed)];
                }
                BitString<n> Get() {
                    return GG.evaluate(seed);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert len(result.fields) == len(game.fields) + 1
        new_field_name = next(
            f.name for f in result.fields if f.name not in {"seed", "ct"}
        )
        init = result.methods[0]
        stmts = list(init.block.statements)
        # Terminal return still present at the end
        assert isinstance(stmts[-1], frog_ast.ReturnStatement)
        # Hoisted assignment inserted immediately before the return
        assert isinstance(stmts[-2], frog_ast.Assignment)
        assert isinstance(stmts[-2].var, frog_ast.Variable)
        assert stmts[-2].var.name == new_field_name
        # Return expression's candidate call is rewritten to the new field
        ret = stmts[-1]
        # Search the return expression for the original FuncCall — must be gone
        found_call = next(
            (
                c
                for c in _walk_funccalls(ret.expression)
                if isinstance(c.func, frog_ast.FieldAccess)
                and c.func.name == "evaluate"
            ),
            None,
        )
        assert found_call is None
        # Get oracle also rewrites the call
        oracle = result.methods[1]
        oracle_ret = oracle.block.statements[0]
        assert isinstance(oracle_ret, frog_ast.ReturnStatement)
        assert isinstance(oracle_ret.expression, frog_ast.Variable)
        assert oracle_ret.expression.name == new_field_name

    def test_early_return_in_if_still_bails(self) -> None:
        """An ``if`` block containing a ReturnStatement in Initialize: no hoist.

        The appended hoisted assignment would be skipped when the guard
        takes the early-return branch, so the pass must continue to bail.
        """
        game = frog_parser.parse_game("""
            Game Foo(G GG, Bool cond) {
                BitString<n> seed = 0^n;
                Void Initialize() {
                    seed <- BitString<n>;
                }
                BitString<n> Get() {
                    return GG.evaluate(seed);
                }
            }
            """)
        # Inject an early return inside an if block in Initialize.
        init = game.methods[0]
        assert init.signature.name == "Initialize"
        early_return_block = frog_ast.Block(
            [frog_ast.ReturnStatement(frog_ast.Integer(0))]
        )
        if_stmt = frog_ast.IfStatement(
            [frog_ast.Boolean(True)], [early_return_block]
        )
        init.block = frog_ast.Block([if_stmt, *list(init.block.statements)])
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert result == game

    def test_alias_in_return_rewritten(self) -> None:
        """``x = cand; return f(x);`` in Initialize: the alias use is rewritten.

        Without alias-aware rewriting, the hoisted field has only one use
        (in the oracle), so Inline Single-Use Field can fold it back.
        """
        ns = _make_det_namespace()
        prim_f = frog_parser.parse_primitive_file("""
            Primitive F(Int n) {
                deterministic BitString<n> wrap(BitString<n> x);
            }
            """)
        ns["F"] = prim_f
        ns["FF"] = prim_f
        ns["GG"] = ns["G"]
        game = frog_parser.parse_game("""
            Game Foo(G GG, F FF) {
                BitString<n> seed;
                Void Initialize() {
                    seed <- BitString<n>;
                    BitString<n> y = GG.evaluate(seed);
                    return FF.wrap(y);
                }
                BitString<n> Get() {
                    return GG.evaluate(seed);
                }
            }
            """)
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert len(result.fields) == len(game.fields) + 1
        new_field_name = next(
            f.name for f in result.fields if f.name not in {"seed"}
        )
        init = result.methods[0]
        stmts = list(init.block.statements)
        ret = stmts[-1]
        assert isinstance(ret, frog_ast.ReturnStatement)
        # The return expression should now reference the new field via
        # FF.wrap(new_field), not FF.wrap(y).
        assert isinstance(ret.expression, frog_ast.FuncCall)
        assert len(ret.expression.args) == 1
        arg = ret.expression.args[0]
        assert isinstance(arg, frog_ast.Variable)
        assert arg.name == new_field_name

    def test_hoist_with_slice_of_field_arg(self) -> None:
        """Call whose argument is a Slice of a field gets hoisted.

        This is the pattern that blocks hybrid-KEM seed-form Decaps from
        canonicalizing: ``DeriveKeyPair(seed_full[0 : n])`` in Decaps, with
        ``seed_full`` a field set in Initialize.
        """
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<16> seed_full;
                Void Initialize() {
                    seed_full <- BitString<16>;
                }
                BitString<8> Get() {
                    return GG.evaluate(seed_full[0 : 8]);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert len(result.fields) == len(game.fields) + 1
        new_field_name = next(
            f.name for f in result.fields if f.name not in {"seed_full"}
        )
        # Initialize gains ``<new> = GG.evaluate(seed_full[0:n]);``
        init = result.methods[0]
        last_stmt = init.block.statements[-1]
        assert isinstance(last_stmt, frog_ast.Assignment)
        assert isinstance(last_stmt.var, frog_ast.Variable)
        assert last_stmt.var.name == new_field_name
        # Get's body should no longer contain any FuncCall.
        get_body = result.methods[1].block
        assert _walk_funccalls(get_body) == []

    def test_hoist_with_array_access_of_field_arg(self) -> None:
        """Call whose argument is an ArrayAccess (tuple projection) of a
        field gets hoisted.
        """
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                [BitString<8>, BitString<8>] pair;
                Void Initialize() {
                    BitString<8> a <- BitString<8>;
                    BitString<8> b <- BitString<8>;
                    pair = [a, b];
                }
                BitString<8> Get() {
                    return GG.evaluate(pair[0]);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert len(result.fields) == len(game.fields) + 1
        new_field_name = next(
            f.name for f in result.fields if f.name not in {"pair"}
        )
        init = result.methods[0]
        stmts = list(init.block.statements)
        # The hoisted assignment should be the last statement (no terminal
        # return in this Void Initialize).
        last_stmt = stmts[-1]
        assert isinstance(last_stmt, frog_ast.Assignment)
        assert isinstance(last_stmt.var, frog_ast.Variable)
        assert last_stmt.var.name == new_field_name
        get_body = result.methods[1].block
        assert _walk_funccalls(get_body) == []

    def test_slice_of_reassigned_local_not_hoisted(self) -> None:
        """A Slice whose underlying array is a local (not a field/param)
        is not stable -- the hoist must not fire.
        """
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                Void Initialize() {
                }
                BitString<8> Get() {
                    BitString<16> x <- BitString<16>;
                    return GG.evaluate(x[0 : 8]);
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        # x is a local in Get, not a field. Slice should not be treated as
        # stable; hoist must not fire.
        assert result == game

    def test_slice_of_field_reassigned_outside_init_not_hoisted(self) -> None:
        """A Slice of a field that *is* reassigned outside Initialize must
        not be hoisted -- each oracle call would see a different slice.
        """
        game = frog_parser.parse_game("""
            Game Foo(G GG) {
                BitString<16> seed_full;
                Void Initialize() {
                    seed_full <- BitString<16>;
                }
                BitString<8> Get() {
                    return GG.evaluate(seed_full[0 : 8]);
                }
                Void Reset() {
                    seed_full <- BitString<16>;
                }
            }
            """)
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ns
        ).transform(game)
        assert result == game

    def test_nested_function_var_callee_reassigned_not_hoisted(self) -> None:
        """Nested ``RF(field_x)`` with RF reassigned outside Initialize: not hoisted."""
        game = frog_parser.parse_game("""
            Game Foo() {
                BitString<8> seed;
                Function<BitString<8>, BitString<8>> RF;
                Void Initialize() {
                    seed <- BitString<8>;
                    RF <- Function<BitString<8>, BitString<8>>;
                }
                BitString<8> Get() {
                    return RF(RF(seed));
                }
                Void Reset() {
                    RF <- Function<BitString<8>, BitString<8>>;
                }
            }
            """)
        result = HoistDeterministicCallToInitializeTransformer(
            proof_namespace={}
        ).transform(game)
        assert result == game
