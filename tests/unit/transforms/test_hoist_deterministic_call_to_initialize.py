"""Tests for HoistDeterministicCallToInitialize transform."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import (
    HoistDeterministicCallToInitializeTransformer,
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
