"""Tests for the alpha-equivalent branch merging in SimplifyIfTransformer."""

import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.control_flow import SimplifyIfTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Branches identical up to local variable names: merged
        (
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else {
                    BitString<n> b <- BitString<n>;
                    return b;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (true) {
                    BitString<n> a <- BitString<n>;
                    return a;
                }
            }
            """,
        ),
        # Two if-else-if branches identical up to local names: merged with OR
        # (the second branch body is kept after merging)
        (
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else if (x == 2) {
                    BitString<n> b <- BitString<n>;
                    return b;
                } else {
                    return x;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (x == 1 || x == 2) {
                    BitString<n> b <- BitString<n>;
                    return b;
                } else {
                    return x;
                }
            }
            """,
        ),
        # Multiple local declarations, same structure: merged
        (
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    BitString<n> c = a + m;
                    return c;
                } else {
                    BitString<n> d <- BitString<n>;
                    BitString<n> e = d + m;
                    return e;
                }
            }
            """,
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (true) {
                    BitString<n> a <- BitString<n>;
                    BitString<n> c = a + m;
                    return c;
                }
            }
            """,
        ),
        # Different structure (not just variable names): NOT merged
        (
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a + m;
                } else {
                    return m;
                }
            }
            """,
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a + m;
                } else {
                    return m;
                }
            }
            """,
        ),
        # Local names differ but reference different outer variables: NOT merged
        (
            """
            BitString<n> f(Int x, BitString<n> m, BitString<n> p) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a + m;
                } else {
                    BitString<n> b <- BitString<n>;
                    return b + p;
                }
            }
            """,
            """
            BitString<n> f(Int x, BitString<n> m, BitString<n> p) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a + m;
                } else {
                    BitString<n> b <- BitString<n>;
                    return b + p;
                }
            }
            """,
        ),
        # No local declarations, identical bodies: merged (existing behavior)
        (
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (x == 1) {
                    return m;
                } else {
                    return m;
                }
            }
            """,
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (true) {
                    return m;
                }
            }
            """,
        ),
        # Different number of local declarations: NOT merged
        (
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else {
                    return x;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else {
                    return x;
                }
            }
            """,
        ),
        # Different sample types: NOT merged
        (
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else {
                    BitString<m> b <- BitString<m>;
                    return b;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else {
                    BitString<m> b <- BitString<m>;
                    return b;
                }
            }
            """,
        ),
    ],
)
def test_alpha_simplify_if(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed_ast = SimplifyIfTransformer().transform(method_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


# F-130: the branches are compared after renaming each one's binders, in
# order, to names neither branch mentions, following position-sensitive
# scope. A name a branch reads where nothing in it binds that name keeps its
# name, so it can never be taken for a renamed local.


def _merged(game_src: str, method_name: str = "Probe") -> bool:
    game = frog_parser.parse_game(game_src)
    result = SimplifyIfTransformer().transform(game)
    before = next(m for m in game.methods if m.signature.name == method_name)
    after = next(m for m in result.methods if m.signature.name == method_name)
    return before != after


def test_f130_field_named_like_a_minted_name_is_not_a_local() -> None:
    # F-130 A2: the then-branch returns the field __alpha_1__, the else-branch
    # its own local t. Renaming t to __alpha_1__ fused the two.
    assert not _merged("""
        Game G() {
            Int __alpha_1__;
            Void SetVal(Int v) { __alpha_1__ = v; }
            Int Probe(Bool c) {
                if (c) {
                    Int t = 7;
                    return __alpha_1__;
                } else {
                    Int t = 7;
                    return t;
                }
            }
        }
        """)


def test_f130_free_name_like_a_minted_name_is_not_a_local() -> None:
    # The same with a name the game does not declare (after instantiation, a
    # proof let: entry), which no pass renames.
    assert not _merged("""
        Game G() {
            BitString<16> s;
            Void Probe(Bool b) {
                if (b) {
                    BitString<8> x <- BitString<8>;
                    s = x || x;
                } else {
                    BitString<8> y <- BitString<8>;
                    s = y || __alpha_1__;
                }
            }
        }
        """)


def test_f130_read_before_a_same_named_local_is_the_outer_name() -> None:
    # F-130 A1: `out = x` reads the field x, declared later as a local; the
    # else-branch reads the field z the same way.
    assert not _merged("""
        Game G() {
            Int x;
            Int z;
            Int Probe(Bool c) {
                if (c) {
                    Int out = x;
                    Int x = 0;
                    return out + x;
                } else {
                    Int out = z;
                    Int z = 0;
                    return out + z;
                }
            }
        }
        """)


def test_f130_read_after_the_block_declaring_a_local_is_the_outer_name() -> None:
    # After the nested block that declares the local x, `return x` reads the
    # field x again; the else-branch returns the field z.
    assert not _merged("""
        Game G() {
            Int x;
            Int z;
            Int s;
            Int Probe(Bool c, Bool d) {
                if (c) {
                    if (d) {
                        Int x = 0;
                        s = x;
                    }
                    return x;
                } else {
                    if (d) {
                        Int z = 0;
                        s = z;
                    }
                    return z;
                }
            }
        }
        """)


def test_f130_loop_binder_is_not_a_same_named_local() -> None:
    # F-129's shape at pass level: the then-branch sums the loop binder x,
    # the else-branch the local t; the local x is not the binder.
    assert not _merged("""
        Game G() {
            Int acc;
            Int Probe(Bool c) {
                acc = 0;
                if (c) {
                    Int x = 5;
                    for (Int x = 0 to 3) {
                        acc = acc + x;
                    }
                    return acc + x;
                } else {
                    Int t = 5;
                    for (Int x = 0 to 3) {
                        acc = acc + t;
                    }
                    return acc + t;
                }
            }
        }
        """)


def test_f130_minted_names_skip_a_name_both_branches_read() -> None:
    # Positive control: both branches read the field __alpha_1__ and are
    # alike up to their locals' names, so they still merge.
    assert _merged("""
        Game G() {
            Int __alpha_1__;
            Int Probe(Bool c) {
                if (c) {
                    Int t = 7;
                    return t + __alpha_1__;
                } else {
                    Int u = 7;
                    return u + __alpha_1__;
                }
            }
        }
        """)


@pytest.mark.parametrize(
    "then_body,else_body",
    [
        # Locals named the way Alpha Rename names them.
        (
            "Int __a1__ = 7; return __a1__;",
            "Int __a2__ = 7; return __a2__;",
        ),
        # A local declared in a nested block.
        (
            "if (d) { Int a = 1; s = a; } return s;",
            "if (d) { Int b = 1; s = b; } return s;",
        ),
        # Loop binders.
        (
            "for (Int i = 0 to 3) { s = s + i; } return s;",
            "for (Int j = 0 to 3) { s = s + j; } return s;",
        ),
        # A bare declaration.
        (
            "Int a; a = 3; return a;",
            "Int b; b = 3; return b;",
        ),
    ],
)
def test_f130_branches_alike_up_to_binder_names_merge(
    then_body: str, else_body: str
) -> None:
    assert _merged(f"""
        Game G() {{
            Int s;
            Int Probe(Bool c, Bool d) {{
                if (c) {{ {then_body} }} else {{ {else_body} }}
            }}
        }}
        """)


def test_f130_local_also_used_as_a_type_name_is_not_compared() -> None:
    # After `Int K = 0;` the renaming would also rewrite the type name K in
    # `K y <- K;`, so the then-branch's types (K) and the else-branch's (J)
    # would both become the minted name.
    assert not _merged("""
        Game G(Set K, Set J) {
            Int Probe(Bool c) {
                if (c) {
                    Int K = 0;
                    K y <- K;
                    return K;
                } else {
                    Int J = 0;
                    J y <- J;
                    return J;
                }
            }
        }
        """)


def test_f130_tuple_destructuring_is_not_compared() -> None:
    # A destructuring binding (kept only by the LaTeX exporter's parse) binds
    # names the renaming cannot follow.
    method = frog_parser.parse_method("""
        Int f(Bool c, [Int, Int] t) {
            if (c) {
                return 0;
            } else {
                return 0;
            }
        }
        """)
    if_statement = method.block.statements[0]
    assert isinstance(if_statement, frog_ast.IfStatement)
    for block, name in zip(if_statement.blocks, ["a", "b"]):
        binding = frog_ast.DestructuringBinding(
            frog_ast.ProductType([frog_ast.IntType(), frog_ast.IntType()]),
            [name, "u"],
            frog_ast.Variable("t"),
        )
        block.statements = [
            binding,
            frog_ast.ReturnStatement(frog_ast.Variable(name)),
        ]
    assert SimplifyIfTransformer().transform(method) == method
