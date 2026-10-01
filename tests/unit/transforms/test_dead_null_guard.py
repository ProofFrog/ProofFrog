"""Tests for DeadNullGuardEliminator transformer."""

import pytest
from proof_frog import frog_ast, visitors, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.types import (
    DeadNullGuardElimination,
    DeadNullGuardEliminator,
)


def _transform(game_str: str) -> str:
    """Parse a game, apply DeadNullGuardEliminator, return string."""
    game = frog_parser.parse_game(game_str)
    type_map = visitors.build_game_type_map(game)
    result = DeadNullGuardEliminator(type_map).transform(game)
    return str(result)


class TestDeadNullGuardRemoval:
    """Tests for removing dead null guards where variable is non-nullable."""

    def test_removes_dead_guard_non_nullable_variable(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    if (x == None) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """)
        expected = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    return x;
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == expected

    def test_removes_dead_guard_none_equals_variable(self) -> None:
        """Test None == x form (reversed operand order)."""
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    if (None == x) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """)
        expected = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    return x;
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == expected


class TestPreservesRealNullGuards:
    """Tests that real null guards (nullable variables) are kept."""

    def test_preserves_guard_on_nullable_variable(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8>? x = None;
                    if (x == None) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == game

    def test_preserves_guard_with_else_block(self) -> None:
        """If-else is not a simple guard pattern — preserve it."""
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    if (x == None) {
                        return 0^8;
                    } else {
                        return x;
                    }
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == game

    def test_preserves_non_null_comparison(self) -> None:
        """if (x == y) is not a null guard — preserve it."""
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test(BitString<8> x, BitString<8> y) {
                    if (x == y) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == game

    def test_preserves_guard_when_nonnull_var_reassigned_to_none(self) -> None:
        """If a variable is declared from a non-nullable expr but later
        reassigned to None, the null guard is reachable and must be kept."""
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8>? Test(BitString<8> x) {
                    BitString<8>? v = x;
                    v = None;
                    if (v == None) {
                        return 0^8;
                    }
                    return v;
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert (
            result == game
        ), "Guard on variable reassigned to None should not be eliminated"


class TestNullableLocalWrites:
    """A nullable local stays nullable if any later statement may write it."""

    @pytest.mark.parametrize(
        "write",
        [
            "if (c) { v = None; }",
            "if (c) { } else { v = None; }",
            "for (Int i = 0 to 2) { v = None; }",
            "if (c) { if (c) { v = None; } }",
            "if (c) { } else if (x == 0) { v = None; }",
            "for (Int e in S) { v = None; }",
            "if (c) { for (Int e in S) { v = None; } }",
            # A loop binder named v rebinds it.
            "for (Int v = 0 to 2) { x = v; }",
            "for (Int v in S) { x = v; }",
            "if (c) { for (Int v = 0 to 2) { x = v; } }",
            # A bare redeclaration leaves v unset.  The typechecker rejects
            # this in source and AlphaRename renames it; the pass must not
            # depend on either.
            "Int? v;",
            "if (c) { Int? v; }",
            "Int? v = None;",
        ],
    )
    def test_nested_write_keeps_guard(self, write: str) -> None:
        game = frog_parser.parse_game(f"""
            Game G() {{
                Int Test(Int x, Bool c, Set<Int> S) {{
                    Int? v = x;
                    {write}
                    if (v == None) {{
                        return 0;
                    }}
                    return 1;
                }}
            }}
            """)
        assert "if (v == None)" in _transform(str(game))

    @pytest.mark.parametrize(
        "write",
        [
            "v <- BitString<8>;",
            "if (c) { v <- BitString<8>; }",
            "v <-uniq[T] BitString<8>;",
            "if (c) { v <-uniq[T] BitString<8>; }",
            "v <- BitString<8> \\ T;",
            "BitString<8>? v <- BitString<8>;",
        ],
    )
    def test_sample_keeps_guard(self, write: str) -> None:
        """A sample cannot yield None, but the pass does not reason about
        which writes are non-null: any write keeps the guard."""
        result = _transform(f"""
            Game G() {{
                Int Test(BitString<8> x, Bool c, Set<BitString<8>> T) {{
                    BitString<8>? v = x;
                    {write}
                    if (v == None) {{
                        return 0;
                    }}
                    return 1;
                }}
            }}
            """)
        assert "if (v == None)" in result

    @pytest.mark.parametrize(
        "the_type, write",
        [
            ("Map<Int, Int>", "v[0] = 1;"),
            ("Map<Int, Int>", "if (c) { v[0] = 1; }"),
            ("Map<Int, BitString<8>>", "v[0] <- BitString<8>;"),
            ("Array<Int, 4>", "v[0] = 1;"),
            ("Array<Array<Int, 4>, 4>", "v[0][1] = 1;"),
        ],
    )
    def test_element_write_keeps_guard(self, the_type: str, write: str) -> None:
        result = _transform(f"""
            Game G() {{
                Int Test({the_type} x, Bool c) {{
                    {the_type}? v = x;
                    {write}
                    if (v == None) {{
                        return 0;
                    }}
                    return 1;
                }}
            }}
            """)
        assert "if (v == None)" in result

    def test_write_with_no_variable_base_keeps_guard(self) -> None:
        """An l-value that bottoms out in something other than a variable
        cannot be shown to leave v alone."""
        game = frog_parser.parse_game("""
            Game G() {
                Int Test(Int x, Int y) {
                    Int? v = x;
                    y = 0;
                    if (v == None) {
                        return 0;
                    }
                    return 1;
                }
            }
            """)
        statements = game.methods[0].block.statements
        write = statements[1]
        assert isinstance(write, frog_ast.Assignment)
        write.var = frog_ast.Tuple([frog_ast.Variable("v"), frog_ast.Variable("y")])
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert "if (v == None)" in str(result)

    def test_destructuring_redeclaration_keeps_guard(self) -> None:
        """`[Int?, Int] [v, w] = t;` desugars to a declaration of v."""
        result = _transform("""
            Game G() {
                Int Test(Int x, [Int?, Int] t) {
                    Int? v = x;
                    [Int?, Int] [v, w] = t;
                    if (v == None) {
                        return 0;
                    }
                    return 1;
                }
            }
            """)
        assert "if (v == None)" in result

    def test_undesugared_destructuring_keeps_guard(self) -> None:
        """The engine never sees a DestructuringBinding; the scan counts one
        anyway."""
        game = frog_parser.parse_game("""
            Game G() {
                Int Test(Int x, [Int?, Int] t) {
                    Int? v = x;
                    x = 0;
                    if (v == None) {
                        return 0;
                    }
                    return 1;
                }
            }
            """)
        game.methods[0].block.statements[1] = frog_ast.DestructuringBinding(
            frog_ast.ProductType(
                [frog_ast.OptionalType(frog_ast.IntType()), frog_ast.IntType()]
            ),
            ["v", "w"],
            frog_ast.Variable("t"),
        )
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert "if (v == None)" in str(result)

    def test_guard_in_loop_body_kept_when_write_follows_it(self) -> None:
        """The scan covers the whole block, not just the statements between
        the declaration and the guard: in a loop body a statement after the
        guard also runs before it, on the next iteration.  Pinned so the scan
        is not narrowed without an argument that covers loops."""
        result = _transform("""
            Game G() {
                Int Test(Int x) {
                    for (Int i = 0 to 2) {
                        Int? v = x;
                        if (v == None) {
                            return 0;
                        }
                        v = None;
                    }
                    return 1;
                }
            }
            """)
        assert "if (v == None)" in result

    def test_guard_in_loop_body_removed_without_write(self) -> None:
        result = _transform("""
            Game G() {
                Int Test(Int x) {
                    for (Int i = 0 to 2) {
                        Int? v = x;
                        if (v == None) {
                            return 0;
                        }
                    }
                    return 1;
                }
            }
            """)
        assert "v == None" not in result

    @pytest.mark.parametrize("guard", ["v == None", "None == v"])
    def test_both_orientations(self, guard: str) -> None:
        template = """
            Game G() {{
                Int Test(Int x, Bool c) {{
                    Int? v = x;
                    {write}
                    if ({guard}) {{
                        return 0;
                    }}
                    return 1;
                }}
            }}
            """
        kept = _transform(template.format(write="if (c) { v = None; }", guard=guard))
        assert f"if ({guard})" in kept
        dropped = _transform(template.format(write="", guard=guard))
        assert "None" not in dropped.replace("Int? v", "")

    @pytest.mark.parametrize("write", ["", "if (c) { v = None; }"])
    def test_not_equals_none_untouched(self, write: str) -> None:
        """The pass only removes `== None` guards."""
        game = frog_parser.parse_game(f"""
            Game G() {{
                Int Test(Int x, Bool c) {{
                    Int? v = x;
                    {write}
                    if (v != None) {{
                        return 0;
                    }}
                    return 1;
                }}
            }}
            """)
        type_map = visitors.build_game_type_map(game)
        assert DeadNullGuardEliminator(type_map).transform(game) == game

    def test_no_write_removes_guard(self) -> None:
        result = _transform("""
            Game G() {
                Int Test(Int x, Bool c) {
                    Int? v = x;
                    if (c) { x = 0; }
                    if (v == None) {
                        return 0;
                    }
                    return 1;
                }
            }
            """)
        assert "v == None" not in result

    def test_guard_before_declaration_kept(self) -> None:
        """The guard reads the field v, not the later local."""
        result = _transform("""
            Game G() {
                Int? v;
                Int Test(Int x) {
                    if (v == None) {
                        return 0;
                    }
                    Int? v = x;
                    return 1;
                }
            }
            """)
        assert "if (v == None)" in result


class TestConflictingBindings:
    """The type map holds one type per name for a whole method.  When the
    method binds a name under two types, the map is wrong at some guard, so
    the pass must not trust it.  AlphaRename gives locals distinct names
    before the pass runs in the pipeline; these run the pass on its own."""

    @pytest.mark.parametrize(
        "fields, params, body",
        [
            # The guard reads the nullable field; the map says Int, from the
            # inner local.
            ("Int? v;", "Bool c", "if (c) { Int v = 1; } if (v == None) { return 0; }"),
            # Likewise for a nullable parameter.
            ("", "Int? v, Bool c", "if (c) { Int v = 1; } if (v == None) { return 0; }"),
            # Sibling blocks: the later declaration wins in the map.
            (
                "",
                "Bool c",
                "if (c) { Int? v = None; if (v == None) { return 0; } }"
                " else { Int v = 1; }",
            ),
            # A loop binder is not in the map at all, so the field's type
            # would be used for the guard on the binder.
            (
                "Int v;",
                "Set<Int?> S",
                "for (Int? v in S) { if (v == None) { return 0; } }",
            ),
            (
                "",
                "Int v, Set<Int?> S",
                "for (Int? v in S) { if (v == None) { return 0; } }",
            ),
            # A bare declaration and a sample as the second binding.
            ("Int? v;", "Bool c", "if (c) { Int v; } if (v == None) { return 0; }"),
            (
                "BitString<8>? v;",
                "Bool c",
                "if (c) { BitString<8> v <- BitString<8>; }"
                " if (v == None) { return 0; }",
            ),
        ],
    )
    def test_guard_kept_when_name_bound_under_two_types(
        self, fields: str, params: str, body: str
    ) -> None:
        result = _transform(f"""
            Game G() {{
                {fields}
                Int Test({params}) {{
                    {body}
                    return 1;
                }}
            }}
            """)
        assert "if (v == None)" in result

    def test_initialiser_of_conflicting_name_not_trusted(self) -> None:
        """`Int? w = v` is non-null only if the v it reads is."""
        result = _transform("""
            Game G() {
                Int? v;
                Int Test(Bool c) {
                    if (c) { Int v = 1; }
                    Int? w = v;
                    if (w == None) { return 0; }
                    return 1;
                }
            }
            """)
        assert "if (w == None)" in result

    def test_guard_removed_when_bindings_agree(self) -> None:
        """Two bindings of the same type leave the map right either way."""
        result = _transform("""
            Game G() {
                Int Test(Bool c) {
                    if (c) { Int v = 1; } else {
                        Int v = 2;
                        if (v == None) { return 0; }
                    }
                    return 1;
                }
            }
            """)
        assert "v == None" not in result

    def test_conflict_in_another_method_does_not_block(self) -> None:
        result = DeadNullGuardElimination().apply(
            frog_parser.parse_game("""
                Game G() {
                    Int A(Int v) {
                        if (v == None) { return 0; }
                        return 1;
                    }
                    Int B(Int? v) {
                        if (v == None) { return 0; }
                        return 1;
                    }
                }
                """),
            PipelineContext(
                variables={},
                proof_let_types=visitors.NameTypeMap(),
                proof_namespace={},
                subsets_pairs=[],
            ),
        )
        assert str(result).count("v == None") == 1
        assert "v == None" not in str(result.methods[0])


class TestGuardOnCall:
    """Case 3: the guarded expression is a call on a proof-namespace name."""

    _GAME = """
        Game G() {
            Int Test(Int x) {
                if (P.Eval(x) == None) {
                    return 0;
                }
                return 1;
            }
        }
        """

    def _apply(self, namespace: frog_ast.Namespace) -> frog_ast.Game:
        ctx = PipelineContext(
            variables={},
            proof_let_types=visitors.NameTypeMap(),
            proof_namespace=namespace,
            subsets_pairs=[],
        )
        game = frog_parser.parse_game(self._GAME)
        return DeadNullGuardElimination().apply(game, ctx)

    def test_guard_on_primitive_call_removed(self) -> None:
        primitive = frog_parser.parse_primitive_file("""
            Primitive P() {
                Int Eval(Int x);
            }
            """)
        assert "== None" not in str(self._apply({"P": primitive}))

    def test_guard_on_optional_primitive_call_kept(self) -> None:
        primitive = frog_parser.parse_primitive_file("""
            Primitive P() {
                Int? Eval(Int x);
            }
            """)
        assert "== None" in str(self._apply({"P": primitive}))

    def test_guard_on_game_call_kept(self) -> None:
        """A game's oracle can change the game's state, so removing the guard
        (and the call with it) would be observable: here each call to Eval
        increments a counter that a later call returns.  The engine does not
        bind games in the proof namespace; the pass does not rely on that."""
        stateful = frog_parser.parse_game("""
            Game P() {
                Int count;
                Int Eval(Int x) {
                    count = count + 1;
                    return count;
                }
            }
            """)
        assert "== None" in str(self._apply({"P": stateful}))
