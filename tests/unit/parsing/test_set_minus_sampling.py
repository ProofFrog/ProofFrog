"""Tests for surface-sugar ``<- T \\ S`` desugaring to ``<-uniq[S] T``."""

import tempfile

from proof_frog import frog_ast, frog_parser


def _parse_game(src: str) -> frog_ast.GameFile:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".game", delete=False, encoding="ascii"
    ) as f:
        f.write(src)
        path = f.name
    ast = frog_parser.parse_game_file(path)
    assert isinstance(ast, frog_ast.GameFile)
    return ast


_TEMPLATE = """Game L() {{ ModInt<5> test() {{ {stmt} return x; }} }}
Game R() {{ ModInt<5> test() {{ {stmt} return x; }} }}
export as Test;
"""


def test_sugar_with_type_desugars_to_unique_sample() -> None:
    gf = _parse_game(
        _TEMPLATE.format(stmt="ModInt<5> x <- ModInt<5> \\ {0};")
    )
    stmt = gf.games[0].methods[0].block.statements[0]
    assert isinstance(stmt, frog_ast.UniqueSample)
    assert stmt.the_type is not None
    # Exclusion is the set expression `{0}`
    assert isinstance(stmt.unique_set, frog_ast.Set)
    # sampled_from type is ModInt<5>
    assert isinstance(stmt.sampled_from, frog_ast.ModIntType)


def test_sugar_without_type_desugars_to_unique_sample() -> None:
    gf = _parse_game(
        _TEMPLATE.format(stmt="ModInt<5> x; x <- ModInt<5> \\ {0};")
    )
    stmt = gf.games[0].methods[0].block.statements[1]
    assert isinstance(stmt, frog_ast.UniqueSample)
    assert stmt.the_type is None
    assert isinstance(stmt.unique_set, frog_ast.Set)
    assert isinstance(stmt.sampled_from, frog_ast.ModIntType)


def test_sugar_roundtrips_equal_to_uniq_form() -> None:
    gf_sugar = _parse_game(
        _TEMPLATE.format(stmt="ModInt<5> x <- ModInt<5> \\ {0};")
    )
    gf_uniq = _parse_game(
        _TEMPLATE.format(stmt="ModInt<5> x <-uniq[{0}] ModInt<5>;")
    )
    s1 = gf_sugar.games[0].methods[0].block.statements[0]
    s2 = gf_uniq.games[0].methods[0].block.statements[0]
    assert s1 == s2


def test_existing_sample_without_backslash_still_parses() -> None:
    gf = _parse_game(_TEMPLATE.format(stmt="ModInt<5> x <- ModInt<5>;"))
    stmt = gf.games[0].methods[0].block.statements[0]
    assert isinstance(stmt, frog_ast.Sample)
