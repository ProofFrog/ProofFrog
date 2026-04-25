"""Tests for the SplitOpaqueTupleField transform."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import SplitOpaqueTupleFieldTransformer


def _make_kem_namespace() -> frog_ast.Namespace:
    """Namespace with a primitive that returns a tuple from a deterministic call."""
    prim = frog_parser.parse_primitive_file("""
        Primitive K(Int n) {
            deterministic [BitString<n>, BitString<n>] Gen(BitString<n> seed);
        }
        """)
    return {"K": prim}


def _field_names(game: frog_ast.Game) -> list[str]:
    return [f.name for f in game.fields]


def _field_type(game: frog_ast.Game, name: str) -> frog_ast.Type:
    for f in game.fields:
        if f.name == name:
            return f.type
    raise KeyError(name)


class TestSplitOpaqueTupleField:
    """Positive and negative cases for SplitOpaqueTupleField."""

    def test_two_tuple_both_components_used_split(self) -> None:
        """KeyGen-style two-tuple, [0] read in Init, [1] read in Decaps -> split."""
        game = frog_parser.parse_game("""
            Game Foo() {
                [BitString<n>, BitString<n>] keys;
                Void Initialize() {
                    keys = External.Gen();
                }
                BitString<n> UseInit() {
                    return keys[0];
                }
                BitString<n> Decaps(BitString<n> c) {
                    return keys[1];
                }
            }
            """)
        result = SplitOpaqueTupleFieldTransformer().transform(game)
        names = _field_names(result)
        assert "keys" not in names
        assert "keys_0" in names
        assert "keys_1" in names
        # Per-index field types must match the corresponding tuple slot.
        for k in (0, 1):
            ty = _field_type(result, f"keys_{k}")
            assert isinstance(ty, frog_ast.BitStringType)
        # UseInit/Decaps now read the new fields directly.
        for m in result.methods:
            if m.signature.name == "UseInit":
                ret = m.block.statements[0]
                assert isinstance(ret, frog_ast.ReturnStatement)
                assert isinstance(ret.expression, frog_ast.Variable)
                assert ret.expression.name == "keys_0"
            elif m.signature.name == "Decaps":
                ret = m.block.statements[0]
                assert isinstance(ret, frog_ast.ReturnStatement)
                assert isinstance(ret.expression, frog_ast.Variable)
                assert ret.expression.name == "keys_1"

    def test_two_tuple_only_index_one_used(self) -> None:
        """Only [1] is read; only one new field is introduced (for index 1)."""
        game = frog_parser.parse_game("""
            Game Foo() {
                [BitString<n>, BitString<n>] keys;
                Void Initialize() {
                    keys = External.Gen();
                }
                BitString<n> Decaps(BitString<n> c) {
                    return keys[1];
                }
            }
            """)
        result = SplitOpaqueTupleFieldTransformer().transform(game)
        names = _field_names(result)
        assert "keys" not in names
        assert "keys_1" in names
        assert "keys_0" not in names

    def test_five_tuple_mixed_projections(self) -> None:
        """5-tuple from a deterministic method, indices 0/2/4 read across methods."""
        game = frog_parser.parse_game("""
            Game Foo() {
                [BitString<n>, BitString<n>, BitString<n>, BitString<n>, BitString<n>] corr;
                Void Initialize() {
                    corr = External.Compute();
                }
                BitString<n> A() {
                    return corr[0];
                }
                BitString<n> B() {
                    return corr[2];
                }
                BitString<n> C() {
                    return corr[4];
                }
            }
            """)
        result = SplitOpaqueTupleFieldTransformer().transform(game)
        names = _field_names(result)
        assert "corr" not in names
        for k in (0, 2, 4):
            assert f"corr_{k}" in names
        for k in (1, 3):
            assert f"corr_{k}" not in names

    def test_negative_tuple_literal_rhs(self) -> None:
        """Tuple literal RHS must NOT trigger; TupleIndexFolding handles it."""
        game = frog_parser.parse_game("""
            Game Foo() {
                [BitString<n>, BitString<n>] keys;
                Void Initialize() {
                    keys = [0^n, 0^n];
                }
                BitString<n> A() {
                    return keys[0];
                }
                BitString<n> B() {
                    return keys[1];
                }
            }
            """)
        result = SplitOpaqueTupleFieldTransformer().transform(game)
        assert result == game

    def test_negative_non_projection_use(self) -> None:
        """A whole-tuple read (e.g. `return keys;`) disqualifies the field."""
        game = frog_parser.parse_game("""
            Game Foo() {
                [BitString<n>, BitString<n>] keys;
                Void Initialize() {
                    keys = External.Gen();
                }
                [BitString<n>, BitString<n>] Whole() {
                    return keys;
                }
                BitString<n> A() {
                    return keys[0];
                }
            }
            """)
        result = SplitOpaqueTupleFieldTransformer().transform(game)
        assert result == game

    def test_negative_runtime_index(self) -> None:
        """A runtime-index projection disqualifies the field."""
        game = frog_parser.parse_game("""
            Game Foo() {
                [BitString<n>, BitString<n>] keys;
                Void Initialize() {
                    keys = External.Gen();
                }
                BitString<n> A(Int i) {
                    return keys[i];
                }
            }
            """)
        result = SplitOpaqueTupleFieldTransformer().transform(game)
        assert result == game

    def test_negative_multiple_top_level_assignments(self) -> None:
        """Multiple top-level assignments to the field disqualify the trigger."""
        game = frog_parser.parse_game("""
            Game Foo() {
                [BitString<n>, BitString<n>] keys;
                Void Initialize() {
                    keys = External.Gen();
                    keys = External.Gen();
                }
                BitString<n> A() {
                    return keys[0];
                }
            }
            """)
        result = SplitOpaqueTupleFieldTransformer().transform(game)
        assert result == game
