"""Tests for RandomFunctions<D, R> and <-uniq grammar, AST nodes, and parsing."""

import pytest

from proof_frog import frog_ast, frog_parser


class TestRandomFunctionTypeInFieldDeclaration:
    def test_parses_as_random_function_type(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                RandomFunctions<BitString<8>, BitString<8>> RF;
                Void Initialize() { }
            }
            """)
        assert isinstance(game.fields[0].type, frog_ast.RandomFunctionType)

    def test_correct_domain_and_range(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                Void Initialize() { }
            }
            """)
        rf_type = game.fields[0].type
        assert isinstance(rf_type, frog_ast.RandomFunctionType)
        assert rf_type.domain_type == frog_ast.BitStringType(frog_ast.Integer(8))
        assert rf_type.range_type == frog_ast.BitStringType(frog_ast.Integer(16))


class TestRandomFunctionSampleInInitialize:
    def test_parses_as_sample(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                RandomFunctions<BitString<8>, BitString<8>> RF;
                Void Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<8>>;
                }
            }
            """)
        stmt = game.methods[0].block.statements[0]
        assert isinstance(stmt, frog_ast.Sample)
        assert isinstance(stmt.sampled_from, frog_ast.RandomFunctionType)


class TestRandomFunctionCallExpression:
    def test_parses_as_func_call(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<16>>;
                }
                BitString<16> Lookup(BitString<8> x) {
                    BitString<16> z = RF(x);
                    return z;
                }
            }
            """)
        stmt = game.methods[1].block.statements[0]
        assert isinstance(stmt, frog_ast.Assignment)
        assert isinstance(stmt.value, frog_ast.FuncCall)
        assert isinstance(stmt.value.func, frog_ast.Variable)
        assert stmt.value.func.name == "RF"
        assert len(stmt.value.args) == 1


class TestRandomFunctionDomainFieldAccess:
    def test_parses_as_field_access(self) -> None:
        expr = frog_parser.parse_expression("RF.domain")
        assert isinstance(expr, frog_ast.FieldAccess)
        assert isinstance(expr.the_object, frog_ast.Variable)
        assert expr.the_object.name == "RF"
        assert expr.name == "domain"


class TestUniqueSampleStatement:
    def test_parses_as_unique_sample(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                Set<BitString<8>> Q;
                Void Initialize() {
                    BitString<8> r <-uniq[Q] BitString<8>;
                }
            }
            """)
        stmt = game.methods[0].block.statements[0]
        assert isinstance(stmt, frog_ast.UniqueSample)
        assert isinstance(stmt.var, frog_ast.Variable)
        assert stmt.var.name == "r"
        assert isinstance(stmt.unique_set, frog_ast.Variable)
        assert stmt.unique_set.name == "Q"
        assert isinstance(stmt.sampled_from, frog_ast.BitStringType)


class TestUniqueSampleWithFieldAccessSet:
    def test_parses_with_rf_domain(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<16>>;
                }
                BitString<16> Lookup(BitString<8> x) {
                    BitString<8> r <-uniq[RF.domain] BitString<8>;
                    BitString<16> z = RF(r);
                    return z;
                }
            }
            """)
        stmt = game.methods[1].block.statements[0]
        assert isinstance(stmt, frog_ast.UniqueSample)
        assert isinstance(stmt.unique_set, frog_ast.FieldAccess)
        assert stmt.unique_set.name == "domain"


class TestMalformedRandomFunctionsType:
    def test_missing_type_params_is_parse_error(self) -> None:
        with pytest.raises(frog_parser.ParseError):
            frog_parser.parse_game("""
                Game G() {
                    RandomFunctions RF;
                    Void Initialize() { }
                }
                """)

    def test_one_type_param_is_parse_error(self) -> None:
        with pytest.raises(frog_parser.ParseError):
            frog_parser.parse_game("""
                Game G() {
                    RandomFunctions<BitString<8>> RF;
                    Void Initialize() { }
                }
                """)


class TestRandomFunctionTypeStr:
    def test_str_representation(self) -> None:
        rf = frog_ast.RandomFunctionType(
            frog_ast.BitStringType(frog_ast.Integer(8)),
            frog_ast.BitStringType(frog_ast.Integer(16)),
        )
        assert str(rf) == "RandomFunctions<BitString<8>, BitString<16>>"

    def test_equality(self) -> None:
        rf1 = frog_ast.RandomFunctionType(
            frog_ast.BitStringType(frog_ast.Integer(8)),
            frog_ast.BitStringType(frog_ast.Integer(16)),
        )
        rf2 = frog_ast.RandomFunctionType(
            frog_ast.BitStringType(frog_ast.Integer(8)),
            frog_ast.BitStringType(frog_ast.Integer(16)),
        )
        assert rf1 == rf2

    def test_inequality_different_range(self) -> None:
        rf1 = frog_ast.RandomFunctionType(
            frog_ast.BitStringType(frog_ast.Integer(8)),
            frog_ast.BitStringType(frog_ast.Integer(16)),
        )
        rf2 = frog_ast.RandomFunctionType(
            frog_ast.BitStringType(frog_ast.Integer(8)),
            frog_ast.BitStringType(frog_ast.Integer(8)),
        )
        assert rf1 != rf2


class TestUniqueSampleStr:
    def test_str_representation(self) -> None:
        us = frog_ast.UniqueSample(
            frog_ast.BitStringType(frog_ast.Integer(8)),
            frog_ast.Variable("r"),
            frog_ast.FieldAccess(frog_ast.Variable("RF"), "domain"),
            frog_ast.BitStringType(frog_ast.Integer(8)),
        )
        assert str(us) == "BitString<8> r <-uniq[RF.domain] BitString<8>;"
