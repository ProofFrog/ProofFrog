import pytest
from proof_frog import frog_parser
from proof_frog import dependencies


@pytest.mark.parametrize(
    "method_code,expected_dependencies",
    [
        # Simple statements
        (
            """
            Void f() {
                Int x = 0;
                Int y = x;
                Int z = 0;
                Int w = 5;
                Int a = x + y + z + w;
            }""",
            [[], [0], [], [], [1, 2, 3]],
        ),
        # If statement
        (
            """
            Int f() {
                Int x = 0;
                if (True) {
                    x = 1;
                }
                return x;
            }
            """,
            [[], [0], [1]],
        ),
        # If/Else
        (
            """
            Int f() {
                Int x = 0;
                Int y = 0;
                if (True) {
                    x = 1;
                } else {
                    y = 1;
                }
                return x + y;
            }
            """,
            [[], [], [0, 1], [2]],
        ),
        # Dependent return
        (
            """
            Int f() {
                if (True) {
                    return 1;
                }
                return 2;
            }
            """,
            [[], [0]],
        ),
        # Read after write
        (
            """
            Void f() {
                Int x = 1;
                return x;
            }
            """,
            [[], [0]],
        ),
        # Write after Read
        (
            """
            Void f() {
                Int x = 1;
                Int y = x;
                x = 2;
            }
            """,
            [[], [0], [1]],
        ),
        # Write after write
        (
            """
            Void f() {
                Int x = 1;
                x = 2;
            }
            """,
            [[], [0]],
        ),
    ],
)
def test_dependencies(method_code: str, expected_dependencies: list[list[int]]) -> None:
    method = frog_parser.parse_method(method_code)

    result = dependencies.generate_dependency_graph(method.block, [], {})

    nodes = [dependencies.Node(statement) for statement in method.block.statements]
    for to_add_index, dependency_list in enumerate(expected_dependencies):
        for index in dependency_list:
            nodes[to_add_index].add_neighbour(nodes[index])

    desired_graph = dependencies.DependencyGraph(nodes)
    print("Expected:")
    print(desired_graph)
    print("Received:")
    print(result)
    assert result == desired_graph
