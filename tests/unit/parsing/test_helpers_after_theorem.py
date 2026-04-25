"""Tests for placing reductions/games after the proof block."""

from proof_frog import frog_ast, frog_parser


_HELPER_GAME = """
Game Dummy(Group G) {
    BitString<1> Oracle() {
        return 0^1;
    }
}
"""

_PROOF_BLOCK = """
proof:
let:
    Group G;
assume:

theorem:
    Dummy(G);

games:
    Dummy(G) against Dummy(G).Adversary;
"""


def _parse(src: str) -> frog_ast.ProofFile:
    ast = frog_parser.parse_string(src, frog_ast.FileType.PROOF)
    assert isinstance(ast, frog_ast.ProofFile)
    return ast


def test_helpers_before_theorem() -> None:
    ast = _parse(_HELPER_GAME + _PROOF_BLOCK)
    assert len(ast.helpers) == 1
    assert ast.helpers_after_theorem_count == 0


def test_helpers_after_theorem() -> None:
    ast = _parse(_PROOF_BLOCK + _HELPER_GAME)
    assert len(ast.helpers) == 1
    assert ast.helpers_after_theorem_count == 1


def test_helpers_split_before_and_after() -> None:
    helper_a = _HELPER_GAME.replace("Dummy", "DummyA")
    helper_b = _HELPER_GAME.replace("Dummy", "DummyB")
    ast = _parse(helper_a + _PROOF_BLOCK + helper_b)
    assert len(ast.helpers) == 2
    assert ast.helpers_after_theorem_count == 1
    assert ast.helpers[0].name == "DummyA"
    assert ast.helpers[1].name == "DummyB"


def test_str_roundtrip_preserves_helpers_after() -> None:
    ast = _parse(_PROOF_BLOCK + _HELPER_GAME)
    text = str(ast)
    proof_idx = text.index("proof:")
    helper_idx = text.index("Game Dummy")
    assert helper_idx > proof_idx
    ast2 = _parse(text)
    assert ast2.helpers_after_theorem_count == 1
