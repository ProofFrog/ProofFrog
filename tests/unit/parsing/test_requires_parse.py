"""Tests for parsing the proof-level ``requires:`` block."""

from proof_frog import frog_ast, frog_parser


_MINIMAL_SRC_TEMPLATE = """
Game Dummy(Group G) {{
    BitString<1> Oracle() {{
        return 0^1;
    }}
}}

proof:
let:
    Group G;
assume:

{requires_block}

theorem:
    Dummy(G);

games:
    Dummy(G) against Dummy(G).Adversary;
"""


def _parse(requires_block: str) -> frog_ast.ProofFile:
    src = _MINIMAL_SRC_TEMPLATE.format(requires_block=requires_block)
    ast = frog_parser.parse_string(src, frog_ast.FileType.PROOF)
    assert isinstance(ast, frog_ast.ProofFile)
    return ast


def test_parse_no_requires_block() -> None:
    ast = _parse("")
    assert ast.requirements == []


def test_parse_requires_prime() -> None:
    ast = _parse("requires:\n    G.order is prime;\n")
    assert len(ast.requirements) == 1
    req = ast.requirements[0]
    assert isinstance(req, frog_ast.StructuralRequirement)
    assert req.kind == "prime"
    assert isinstance(req.target, frog_ast.FieldAccess)
    assert req.target.name == "order"


def test_parse_multiple_requires_entries() -> None:
    ast = _parse("requires:\n    G.order is prime;\n    G.order is prime;\n")
    assert len(ast.requirements) == 2
    assert all(r.kind == "prime" for r in ast.requirements)


def test_str_roundtrip_emits_requires_block() -> None:
    ast = _parse("requires:\n    G.order is prime;\n")
    text = str(ast)
    assert "requires:" in text
    assert "G.order is prime" in text
