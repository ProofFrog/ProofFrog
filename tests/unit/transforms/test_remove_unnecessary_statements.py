import copy
import pytest
from proof_frog import dependencies, frog_parser


@pytest.mark.parametrize(
    "method,expected,fields",
    [
        (
            """
            Int f(Int x) {
                return x;
            }
            """,
            """
            Int f(Int x) {
                return x;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                Int y = 1;
                return y;
            }
            """,
            """
            Int f(Int x) {
                Int y = 1;
                return y;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                Int y = 1;
                return x;
            }
            """,
            """
            Int f(Int x) {
                return x;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                Int y <- Int;
                return x + y;
            }
            """,
            """
            Int f(Int x) {
                Int y <- Int;
                return x + y;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                Int a = 5;
                Int b = a;
                Int c = a;
                Int d = 1;
                return c;
            }
            """,
            """
            Int f(Int x) {
                Int a = 5;
                Int c = a;
                return c;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                Int y = 5;
                if (True) {
                    y = 2;
                }
                return x;
            }
            """,
            """
            Int f(Int x) {
                if (True) {
                }
                return x;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                if (True) {
                    x = 2;
                }
                return x;
            }
            """,
            """
            Int f(Int x) {
                if (True) {
                    x = 2;
                }
                return x;
            }
            """,
            [],
        ),
    ],
)
def test_unnecessary_statements(method: str, expected: str, fields: list[str]) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    print("EXPECTED", expected_ast)
    transformed_block = dependencies.remove_unnecessary_statements(
        fields, method_ast.block
    )
    new_method = copy.deepcopy(method_ast)
    new_method.block = transformed_block
    print("TRANSFORMED", new_method)
    assert expected_ast == new_method


def test_dead_exclusion_draws_survive_unless_domain_known_non_empty() -> None:
    """A dead-target ``<-uniq[S]`` draw has an observable side effect (it
    inserts the drawn value into S, visible via |S|), so it must NOT be deleted
    as dead code (F-004). The set-minus form ``<- T \\ S`` performs no
    insertion, but S may cover T, and then the draw does not complete, so it is
    not dead either (F-318). Excluding a set literal smaller than T leaves a
    non-empty domain, and that dead draw IS removable."""
    method = frog_parser.parse_method(
        """
        Int f(BitString<8> y) {
            BitString<8> a <-uniq[S] BitString<8>;
            BitString<8> b <- BitString<8> \\ S;
            BitString<8> c <- BitString<8> \\ {y};
            return 1;
        }
        """
    )
    transformed = dependencies.remove_unnecessary_statements(["S"], method.block)
    text = str(transformed)
    assert "<-uniq[S]" in text, f"dead uniq draw was wrongly removed:\n{text}"
    assert "\\ S" in text, f"possibly-empty dead draw was wrongly removed:\n{text}"
    assert "{y}" not in text, f"dead draw from a non-empty domain was kept:\n{text}"
