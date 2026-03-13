"""Tests for ModInt<q> grammar, AST nodes, and parser visitors (Phases 1-3)."""

from pathlib import Path

from proof_frog import frog_ast, frog_parser

# ---------------------------------------------------------------------------
# Phase 2: AST node tests -- ModIntType
# ---------------------------------------------------------------------------


class TestModIntTypeNode:
    def test_str_simple_variable(self) -> None:
        t = frog_ast.ModIntType(frog_ast.Variable("q"))
        assert str(t) == "ModInt<q>"

    def test_str_integer_modulus(self) -> None:
        t = frog_ast.ModIntType(frog_ast.Integer(7))
        assert str(t) == "ModInt<7>"

    def test_str_compound_modulus(self) -> None:
        t = frog_ast.ModIntType(
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.MULTIPLY,
                frog_ast.Integer(2),
                frog_ast.Variable("lambda"),
            )
        )
        assert str(t) == "ModInt<2 * lambda>"

    def test_eq_same_modulus(self) -> None:
        t1 = frog_ast.ModIntType(frog_ast.Variable("q"))
        t2 = frog_ast.ModIntType(frog_ast.Variable("q"))
        assert t1 == t2

    def test_eq_different_modulus(self) -> None:
        t1 = frog_ast.ModIntType(frog_ast.Variable("p"))
        t2 = frog_ast.ModIntType(frog_ast.Variable("q"))
        assert t1 != t2

    def test_eq_modint_vs_int(self) -> None:
        t1 = frog_ast.ModIntType(frog_ast.Variable("q"))
        t2 = frog_ast.IntType()
        assert t1 != t2


# ---------------------------------------------------------------------------
# Phase 2: AST node tests -- BinaryOperators (EXPONENTIATE and DIVIDE)
# ---------------------------------------------------------------------------


class TestBinaryOperatorsModInt:
    def test_exponentiate_value(self) -> None:
        assert frog_ast.BinaryOperators.EXPONENTIATE.value == "^"

    def test_divide_value(self) -> None:
        assert frog_ast.BinaryOperators.DIVIDE.value == "/"

    def test_exponentiate_precedence_higher_than_multiply(self) -> None:
        exp_prec = frog_ast.BinaryOperators.EXPONENTIATE.precedence()
        mul_prec = frog_ast.BinaryOperators.MULTIPLY.precedence()
        assert exp_prec > mul_prec

    def test_divide_precedence_same_as_multiply(self) -> None:
        div_prec = frog_ast.BinaryOperators.DIVIDE.precedence()
        mul_prec = frog_ast.BinaryOperators.MULTIPLY.precedence()
        assert div_prec == mul_prec

    def test_multiply_precedence_higher_than_add(self) -> None:
        mul_prec = frog_ast.BinaryOperators.MULTIPLY.precedence()
        add_prec = frog_ast.BinaryOperators.ADD.precedence()
        assert mul_prec > add_prec


# ---------------------------------------------------------------------------
# Phase 2: AST node tests -- BinaryOperation.__str__ for ^ and /
# ---------------------------------------------------------------------------


class TestBinaryOperationStrExpDiv:
    def test_flat_exponentiation(self) -> None:
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE,
            frog_ast.Variable("a"),
            frog_ast.Variable("n"),
        )
        assert str(expr) == "a ^ n"

    def test_flat_division(self) -> None:
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.DIVIDE,
            frog_ast.Variable("a"),
            frog_ast.Variable("b"),
        )
        assert str(expr) == "a / b"

    def test_exp_right_associative_no_parens(self) -> None:
        # a ^ (b ^ c) should print as "a ^ b ^ c" (right-associative)
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE,
            frog_ast.Variable("a"),
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EXPONENTIATE,
                frog_ast.Variable("b"),
                frog_ast.Variable("c"),
            ),
        )
        assert str(expr) == "a ^ b ^ c"

    def test_exp_left_nested_gets_parens(self) -> None:
        # (a ^ b) ^ c should print as "(a ^ b) ^ c"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE,
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EXPONENTIATE,
                frog_ast.Variable("a"),
                frog_ast.Variable("b"),
            ),
            frog_ast.Variable("c"),
        )
        assert str(expr) == "(a ^ b) ^ c"

    def test_multiply_inside_exp_gets_parens(self) -> None:
        # a ^ (b * c) -- since * has lower precedence than ^, right operand needs parens
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE,
            frog_ast.Variable("a"),
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.MULTIPLY,
                frog_ast.Variable("b"),
                frog_ast.Variable("c"),
            ),
        )
        assert str(expr) == "a ^ (b * c)"

    def test_exp_inside_multiply_no_parens_left(self) -> None:
        # (a ^ n) * b -- exp has higher prec than *, no parens needed
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.MULTIPLY,
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EXPONENTIATE,
                frog_ast.Variable("a"),
                frog_ast.Variable("n"),
            ),
            frog_ast.Variable("b"),
        )
        assert str(expr) == "a ^ n * b"

    def test_add_inside_divide_gets_parens(self) -> None:
        # a / (b + c) -- + has lower prec than /
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.DIVIDE,
            frog_ast.Variable("a"),
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.ADD,
                frog_ast.Variable("b"),
                frog_ast.Variable("c"),
            ),
        )
        assert str(expr) == "a / (b + c)"

    def test_divide_left_associative_no_extra_parens(self) -> None:
        # (a / b) / c -> "a / b / c"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.DIVIDE,
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.DIVIDE,
                frog_ast.Variable("a"),
                frog_ast.Variable("b"),
            ),
            frog_ast.Variable("c"),
        )
        assert str(expr) == "a / b / c"

    def test_divide_right_nested_gets_parens(self) -> None:
        # a / (b / c) -> "a / (b / c)"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.DIVIDE,
            frog_ast.Variable("a"),
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.DIVIDE,
                frog_ast.Variable("b"),
                frog_ast.Variable("c"),
            ),
        )
        assert str(expr) == "a / (b / c)"


# ---------------------------------------------------------------------------
# Phase 1+3: Parser -- ModInt<q> as a type in games
# ---------------------------------------------------------------------------


class TestModIntTypeParsing:
    def test_modint_as_field_type(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Int q) {
                ModInt<q> state;
                Void Initialize() { }
            }
            """)
        assert isinstance(game.fields[0].type, frog_ast.ModIntType)
        assert game.fields[0].type == frog_ast.ModIntType(frog_ast.Variable("q"))

    def test_modint_as_parameter_type(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Int q) {
                Void Test(ModInt<q> x) { }
            }
            """)
        param_type = game.methods[0].signature.parameters[0].type
        assert isinstance(param_type, frog_ast.ModIntType)
        assert param_type == frog_ast.ModIntType(frog_ast.Variable("q"))

    def test_modint_as_return_type(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Int q) {
                ModInt<q> Test() {
                    ModInt<q> r <- ModInt<q>;
                    return r;
                }
            }
            """)
        return_type = game.methods[0].signature.return_type
        assert isinstance(return_type, frog_ast.ModIntType)

    def test_modint_compound_modulus(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Int lambda) {
                ModInt<2 * lambda> state;
                Void Initialize() { }
            }
            """)
        field_type = game.fields[0].type
        assert isinstance(field_type, frog_ast.ModIntType)
        expected_modulus = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.MULTIPLY,
            frog_ast.Integer(2),
            frog_ast.Variable("lambda"),
        )
        assert field_type == frog_ast.ModIntType(expected_modulus)

    def test_array_of_modint(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Int q, Int n) {
                Array<ModInt<q>, n> state;
                Void Initialize() { }
            }
            """)
        field_type = game.fields[0].type
        assert isinstance(field_type, frog_ast.ArrayType)
        assert isinstance(field_type.element_type, frog_ast.ModIntType)


# ---------------------------------------------------------------------------
# Phase 1+3: Parser -- exponentiation expression
# ---------------------------------------------------------------------------


class TestExponentiationParsing:
    def test_simple_exponentiation(self) -> None:
        expr = frog_parser.parse_expression("a ^ n")
        assert isinstance(expr, frog_ast.BinaryOperation)
        assert expr.operator == frog_ast.BinaryOperators.EXPONENTIATE
        assert expr.left_expression == frog_ast.Variable("a")
        assert expr.right_expression == frog_ast.Variable("n")

    def test_exp_integer_exponent(self) -> None:
        expr = frog_parser.parse_expression("g ^ 3")
        assert isinstance(expr, frog_ast.BinaryOperation)
        assert expr.operator == frog_ast.BinaryOperators.EXPONENTIATE
        assert expr.right_expression == frog_ast.Integer(3)

    def test_exp_negative_one(self) -> None:
        expr = frog_parser.parse_expression("a ^ (-1)")
        assert isinstance(expr, frog_ast.BinaryOperation)
        assert expr.operator == frog_ast.BinaryOperators.EXPONENTIATE
        assert isinstance(expr.right_expression, frog_ast.UnaryOperation)
        assert expr.right_expression.operator == frog_ast.UnaryOperators.MINUS

    def test_exp_right_associative(self) -> None:
        # a ^ b ^ c should parse as a ^ (b ^ c)
        expr = frog_parser.parse_expression("a ^ b ^ c")
        assert isinstance(expr, frog_ast.BinaryOperation)
        assert expr.operator == frog_ast.BinaryOperators.EXPONENTIATE
        assert isinstance(expr.right_expression, frog_ast.BinaryOperation)
        assert expr.right_expression.operator == frog_ast.BinaryOperators.EXPONENTIATE

    def test_exp_binds_tighter_than_multiply(self) -> None:
        # a * b ^ c should parse as a * (b ^ c)
        expr = frog_parser.parse_expression("a * b ^ c")
        assert isinstance(expr, frog_ast.BinaryOperation)
        assert expr.operator == frog_ast.BinaryOperators.MULTIPLY
        assert isinstance(expr.right_expression, frog_ast.BinaryOperation)
        assert expr.right_expression.operator == frog_ast.BinaryOperators.EXPONENTIATE

    def test_exp_binds_tighter_than_add(self) -> None:
        # a + b ^ c should parse as a + (b ^ c)
        expr = frog_parser.parse_expression("a + b ^ c")
        assert isinstance(expr, frog_ast.BinaryOperation)
        assert expr.operator == frog_ast.BinaryOperators.ADD
        assert isinstance(expr.right_expression, frog_ast.BinaryOperation)
        assert expr.right_expression.operator == frog_ast.BinaryOperators.EXPONENTIATE

    def test_exp_in_method(self) -> None:
        method = frog_parser.parse_method("""
            ModInt<q> Test(ModInt<q> g, Int n) {
                return g ^ n;
            }
            """)
        stmt = method.block.statements[0]
        assert isinstance(stmt, frog_ast.ReturnStatement)
        assert isinstance(stmt.expression, frog_ast.BinaryOperation)
        assert stmt.expression.operator == frog_ast.BinaryOperators.EXPONENTIATE

    def test_zeros_caret_still_bitstring_literal(self) -> None:
        # 0^n must still parse as a BitStringLiteral, not exponentiation
        expr = frog_parser.parse_expression("0^n")
        assert isinstance(expr, frog_ast.BitStringLiteral)
        assert expr.bit == 0

    def test_ones_caret_still_bitstring_literal(self) -> None:
        # 1^n must still parse as a BitStringLiteral, not exponentiation
        expr = frog_parser.parse_expression("1^n")
        assert isinstance(expr, frog_ast.BitStringLiteral)
        assert expr.bit == 1

    def test_exp_str_roundtrip(self) -> None:
        expr = frog_parser.parse_expression("a ^ n")
        reparsed = frog_parser.parse_expression(str(expr))
        assert expr == reparsed

    def test_exp_negative_one_str_roundtrip(self) -> None:
        expr = frog_parser.parse_expression("a ^ (-1)")
        reparsed = frog_parser.parse_expression(str(expr))
        assert expr == reparsed


# ---------------------------------------------------------------------------
# Phase 1+3: Parser -- division expression
# ---------------------------------------------------------------------------


class TestDivisionParsing:
    def test_simple_division(self) -> None:
        expr = frog_parser.parse_expression("a / b")
        assert isinstance(expr, frog_ast.BinaryOperation)
        assert expr.operator == frog_ast.BinaryOperators.DIVIDE
        assert expr.left_expression == frog_ast.Variable("a")
        assert expr.right_expression == frog_ast.Variable("b")

    def test_division_in_method(self) -> None:
        method = frog_parser.parse_method("""
            ModInt<q> Test(ModInt<q> a, ModInt<q> b) {
                return a / b;
            }
            """)
        stmt = method.block.statements[0]
        assert isinstance(stmt, frog_ast.ReturnStatement)
        assert isinstance(stmt.expression, frog_ast.BinaryOperation)
        assert stmt.expression.operator == frog_ast.BinaryOperators.DIVIDE

    def test_division_left_associative(self) -> None:
        # a / b / c parses as (a / b) / c
        expr = frog_parser.parse_expression("a / b / c")
        assert isinstance(expr, frog_ast.BinaryOperation)
        assert expr.operator == frog_ast.BinaryOperators.DIVIDE
        assert isinstance(expr.left_expression, frog_ast.BinaryOperation)
        assert expr.left_expression.operator == frog_ast.BinaryOperators.DIVIDE

    def test_exp_binds_tighter_than_divide(self) -> None:
        # a / b ^ c parses as a / (b ^ c)
        expr = frog_parser.parse_expression("a / b ^ c")
        assert isinstance(expr, frog_ast.BinaryOperation)
        assert expr.operator == frog_ast.BinaryOperators.DIVIDE
        assert isinstance(expr.right_expression, frog_ast.BinaryOperation)
        assert expr.right_expression.operator == frog_ast.BinaryOperators.EXPONENTIATE

    def test_division_str_roundtrip(self) -> None:
        expr = frog_parser.parse_expression("a / b")
        reparsed = frog_parser.parse_expression(str(expr))
        assert expr == reparsed


# ---------------------------------------------------------------------------
# Phase 1+3: Parser -- ModInt<q> sampling syntax
# ---------------------------------------------------------------------------


class TestModIntSamplingParsing:
    def test_uniform_random_sampling_parses(self) -> None:
        # ModInt<q> r <- ModInt<q>; is uniform random sampling (the <- operator)
        game = frog_parser.parse_game("""
            Game G(Int q) {
                Void Initialize() {
                    ModInt<q> r <- ModInt<q>;
                }
            }
            """)
        stmt = game.methods[0].block.statements[0]
        assert isinstance(stmt, frog_ast.Sample)
        # Declared type on the LHS is ModIntType
        assert isinstance(stmt.the_type, frog_ast.ModIntType)
        # The distribution sampled from on the RHS is also ModIntType
        assert isinstance(stmt.sampled_from, frog_ast.ModIntType)


# ---------------------------------------------------------------------------
# Phase 1+3: Parser -- primitive with ModInt types
# ---------------------------------------------------------------------------


class TestModIntInPrimitive:
    def test_primitive_modint_field_and_method(self, tmp_path: Path) -> None:
        prim_file = tmp_path / "Group.primitive"
        prim_file.write_text(
            "Primitive Group(Int q) {\n"
            "    Int q = q;\n"
            "\n"
            "    ModInt<q> multiply(ModInt<q> a, ModInt<q> b);\n"
            "    ModInt<q> exponentiate(ModInt<q> base, Int exp);\n"
            "}\n",
            encoding="utf-8",
        )
        prim = frog_parser.parse_primitive_file(str(prim_file))
        # Check return type of first method (Primitive.methods are MethodSignatures)
        assert isinstance(prim.methods[0].return_type, frog_ast.ModIntType)
        # Check parameter type of first method
        assert isinstance(prim.methods[0].parameters[0].type, frog_ast.ModIntType)
