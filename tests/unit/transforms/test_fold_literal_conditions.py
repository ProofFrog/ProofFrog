"""Unit tests for FoldLiteralConditions."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import (
    BranchEliminiationTransformer,
    FoldLiteralConditionsTransformer,
)


def _fold(source: str) -> str:
    expr = frog_parser.parse_expression(source)
    return str(FoldLiteralConditionsTransformer().transform(expr))


@pytest.mark.parametrize(
    "source,expected",
    [
        # Negation of a boolean literal.
        ("!false", "true"),
        ("!true", "false"),
        ("!(!(false))", "false"),
        # Relational comparison of integer literals.
        ("0 >= 1", "false"),
        ("1 >= 1", "true"),
        ("0 > 1", "false"),
        ("2 > 1", "true"),
        ("0 < 1", "true"),
        ("3 <= 2", "false"),
        # Equal integer literals.
        ("1 == 1", "true"),
        ("1 != 1", "false"),
        # Boolean literal equality.
        ("true == false", "false"),
        ("true != false", "true"),
        ("false == false", "true"),
        # None against syntactically non-None literals, both orders.
        ("None == [1, true, None]", "false"),
        ("[1, true, None] == None", "false"),
        ("None != [[1, x], [a, b]]", "true"),
        ("None == {1, 2}", "false"),
        ("None == 0", "false"),
        ("None == true", "false"),
        ("None == 0b101", "false"),
        ("None == 0^8", "false"),
        ("1^8 != None", "true"),
        # Folds nest so an enclosing connective sees the literal.
        ("!(false) && 0 >= 1", "true && false"),
    ],
)
def test_folds(source: str, expected: str) -> None:
    assert _fold(source) == str(frog_parser.parse_expression(expected))


@pytest.mark.parametrize(
    "source",
    [
        # Non-literal operands are left alone.
        "!x",
        "x >= 1",
        "0 >= y",
        "b == true",
        # Distinct integer literals may be equal mod q in a ModInt slot.
        "0 == 1",
        "0 != 1",
        # None against a variable, call, or expression needs types.
        "None == v",
        "v != None",
        "None == F.f(x)",
        "None == x + y",
        "None == M[k]",
        # A literal whose evaluation makes a call or indexes stays.
        "None == [F.f(x), 1]",
        "None == [M[k], 1]",
        "None == [s[0 : 2], 1]",
        # None == None is ReflexiveComparison's job.
        "None == None",
    ],
)
def test_does_not_fold(source: str) -> None:
    assert _fold(source) == str(frog_parser.parse_expression(source))


def test_fold_then_branch_elimination() -> None:
    method = frog_parser.parse_method("""
        Int f(Int a) {
            if (None == [1, a]) {
                return 0;
            }
            if (!(false)) {
                a = a + 1;
            } else {
                if (0 >= 1) {
                    a = 5;
                } else {
                    a = 6;
                }
            }
            return a;
        }
        """)
    expected = frog_parser.parse_method("""
        Int f(Int a) {
            a = a + 1;
            return a;
        }
        """)
    result = FoldLiteralConditionsTransformer().transform(method)
    # BranchElimination rewrites one if-statement per call.
    for _ in range(3):
        result = BranchEliminiationTransformer().transform(result)
    assert result == expected
