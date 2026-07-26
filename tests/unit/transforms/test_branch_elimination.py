import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import BranchEliminiationTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Two that are the same
        (
            """
            Int f() {
                Int x = 1;
                if (true) {
                    x = 2;
                }
                return x;
            }
            """,
            """
            Int f() {
                Int x = 1;
                x = 2;
                return x;
            }
            """,
        ),
        (
            """
            Int f() {
                Int x = 1;
                if (false) {
                    x = 2;
                }
                return x;
            }
            """,
            """
            Int f() {
                Int x = 1;
                return x;
            }
            """,
        ),
        (
            """
            Int f() {
                Int x = 1;
                if (true) {
                    x = 2;
                } else if (false) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
            """
            Int f() {
                Int x = 1;
                x = 2;
                return x;
            }
            """,
        ),
        (
            """
            Int f(Int y) {
                Int x = 1;
                if (y == 1) {
                    x = 2;
                } else if (true) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
            """
            Int f(Int y) {
                Int x = 1;
                if (y == 1) {
                    x = 2;
                } else {
                    x = 3;
                }
                return x;
            }
            """,
        ),
        (
            """
            Int f(Int y) {
                Int x = 1;
                if (false) {
                    x = 2;
                } else if (y == 1) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
            """
            Int f(Int y) {
                Int x = 1;
                if (y == 1) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
        ),
        (
            """
            Int f() {
                Int x = 1;
                if (false) {
                    x = 2;
                } else if (false) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
            """
            Int f() {
                Int x = 1;
                x = 4;
                return x;
            }
            """,
        ),
        # false then true: the true branch body must be preserved
        (
            """
            Int f() {
                Int x = 1;
                if (false) {
                    x = 2;
                } else if (true) {
                    x = 3;
                }
                return x;
            }
            """,
            """
            Int f() {
                Int x = 1;
                x = 3;
                return x;
            }
            """,
        ),
        # false then true with else: true branch inlined, else dropped
        (
            """
            Int f() {
                Int x = 1;
                if (false) {
                    x = 2;
                } else if (true) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
            """
            Int f() {
                Int x = 1;
                x = 3;
                return x;
            }
            """,
        ),
    ],
)
def test_branch_elimination(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    print("EXPECTED: ", expected_ast)
    transformed_ast = BranchEliminiationTransformer().transform(game_ast)
    print("TRANSFORMED: ", transformed_ast)
    assert expected_ast == transformed_ast


def test_f125_malformed_empty_conditions_splices_else() -> None:
    """F-125: for an ``IfStatement([], [b1, b2])`` (no conditions -- malformed,
    only directly constructible) the executing block is the else that
    ``has_else_block()`` designates, i.e. ``blocks[-1]``. The pass previously
    spliced ``blocks[0]``, running the wrong block and dropping the else."""
    from proof_frog import frog_ast

    def asn(name: str, num: int) -> frog_ast.Assignment:
        return frog_ast.Assignment(None, frog_ast.Variable(name), frog_ast.Integer(num))

    malformed = frog_ast.IfStatement(
        [], [frog_ast.Block([asn("x", 1)]), frog_ast.Block([asn("y", 2)])]
    )
    block = frog_ast.Block([malformed, frog_ast.ReturnStatement(frog_ast.Integer(0))])
    out = str(BranchEliminiationTransformer().transform(block))
    assert "y" in out and "x" not in out  # else (blocks[-1]) executed, not blocks[0]


def test_f125_if_false_else_still_splices_else() -> None:
    """Control: the reachable ``if (false) { x } else { y }`` still eliminates to
    the else (blocks[-1] == blocks[0] after paired deletion)."""
    from proof_frog import frog_ast

    def asn(name: str, num: int) -> frog_ast.Assignment:
        return frog_ast.Assignment(None, frog_ast.Variable(name), frog_ast.Integer(num))

    stmt = frog_ast.IfStatement(
        [frog_ast.Boolean(False)],
        [frog_ast.Block([asn("x", 1)]), frog_ast.Block([asn("y", 2)])],
    )
    block = frog_ast.Block([stmt, frog_ast.ReturnStatement(frog_ast.Integer(0))])
    out = str(BranchEliminiationTransformer().transform(block))
    assert "y" in out and "x" not in out
