"""Expand Tuple: field initializers and names that hide a split variable (F-399).

Expand Tuple splits a product field or local ``v`` into component variables
and rewrites ``v[i]`` to the component.

(1) Field initializers. The fields are rewritten in declaration order, so a
later field's initializer (and type) reads the components of a field split
before it; it used to keep reading ``w[1]`` after ``w`` was gone, so two
games whose ``w`` differed met in one canonical form. A field read by its
own initializer or by an earlier field's is not split (that initializer
runs before the field's own), nor is a field whose initializer is not a
tuple literal (it used to crash the pass).

(2) Hiding. A declaration of ``v`` that is not split (a typed local, a bare
declaration, a method parameter, a ``for`` binder) brings a new variable
into scope: an outer split ``v`` is hidden there, so the new variable's
reads and writes are not sent to the outer variable's components.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.tuples import ExpandTuple, SplitBareTupleDeclarations
from proof_frog.visitors import NameTypeMap, SearchVisitor

_PAIR = "[BitString<8>, BitString<8>]"


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _expand(source: str) -> frog_ast.Game:
    return ExpandTuple().apply(frog_parser.parse_game(source), _ctx())


def _fields(game: frog_ast.Game) -> list[str]:
    return [str(field) for field in game.fields]


def _method(game: frog_ast.Game, name: str) -> list[str]:
    method = next(m for m in game.methods if m.signature.name == name)
    return [" ".join(str(s).split()) for s in method.block.statements]


def _names_variable(node: frog_ast.ASTNode, name: str) -> bool:
    return (
        SearchVisitor(
            lambda n: isinstance(n, frog_ast.Variable) and n.name == name
        ).visit(node)
        is not None
    )


# --- (1) field initializers --------------------------------------------------


def test_f399_later_field_initializer_reads_the_component() -> None:
    # x stays a field (Q writes it); its initializer reads w[1], which must
    # become the component w@1, declared before x. Left at w[1], it named a
    # field that no longer exists.
    result = _expand(f"""
        Game T() {{
            {_PAIR} w = [0^8, 1^8];
            BitString<8> x = w[1];
            BitString<8> Q() {{
                BitString<8> r = x;
                x = 0^8;
                return r;
            }}
        }}
        """)
    assert _fields(result) == [
        "BitString<8> w@0 = 0^8;",
        "BitString<8> w@1 = 1^8;",
        "BitString<8> x = w@1;",
    ]
    assert not _names_variable(result, "w")


def test_f399_component_initializers_read_earlier_split_fields() -> None:
    # w's components and z's are initialized from u's, split before them; z
    # reads u whole, which stands for the tuple of u's components.
    result = _expand(f"""
        Game T() {{
            {_PAIR} u = [0^8, 1^8];
            {_PAIR} w = [u[1], u[0]];
            {_PAIR} z = u;
            {_PAIR} Q() {{
                return [w[0], z[1]];
            }}
        }}
        """)
    assert _fields(result) == [
        "BitString<8> u@0 = 0^8;",
        "BitString<8> u@1 = 1^8;",
        "BitString<8> w@0 = u@1;",
        "BitString<8> w@1 = u@0;",
        "BitString<8> z@0 = u@0;",
        "BitString<8> z@1 = u@1;",
    ]
    assert _method(result, "Q") == ["return [w@0, z@1];"]


def test_f399_later_field_type_reads_the_component() -> None:
    result = _expand("""
        Game T() {
            [Int, Int] w = [8, 8];
            BitString<w[0]> x;
            BitString<w[0]> Q() {
                return x;
            }
        }
        """)
    assert _fields(result) == [
        "Int w@0 = 8;",
        "Int w@1 = 8;",
        "BitString<w@0> x;",
    ]
    assert not _names_variable(result, "w")


def test_f399_field_read_by_an_earlier_initializer_is_not_split() -> None:
    # x's initializer runs before w's, so it reads w's starting value; it
    # cannot read a component declared after it. The split used to leave
    # x = w[1] naming a removed field.
    source = f"""
        Game T() {{
            BitString<8> x = w[1];
            {_PAIR} w = [0^8, 1^8];
            BitString<8> Q() {{
                BitString<8> r = x;
                x = 0^8;
                return r + w[0];
            }}
        }}
        """
    game = frog_parser.parse_game(source)
    assert ExpandTuple().apply(game, _ctx()) == game


def test_f399_field_read_by_its_own_initializer_is_not_split() -> None:
    game = frog_parser.parse_game(f"""
        Game T() {{
            {_PAIR} w = [w[1], 0^8];
            BitString<8> Q() {{
                return w[0];
            }}
        }}
        """)
    assert ExpandTuple().apply(game, _ctx()) == game


def test_f399_field_with_a_non_literal_initializer_is_not_split() -> None:
    # A product field initialized by a call (or by another product field
    # that is not split) has no components to give each new field; the pass
    # used to fail an assertion here.
    game = frog_parser.parse_game(f"""
        Game T() {{
            {_PAIR} w = P.Pair();
            BitString<8> Q() {{
                return w[0];
            }}
        }}
        """)
    assert ExpandTuple().apply(game, _ctx()) == game


# --- (2) a declaration that is not split hides the split variable -----------


def test_f399_typed_local_named_like_a_split_field_gets_its_own_components() -> None:
    # The local v declared in Q is a new variable: its initializer must not
    # be written into the field's components (S35's probe E4).
    result = _expand(f"""
        Game T() {{
            {_PAIR} v;
            Void Initialize() {{
                v = [0^8, 0^8];
            }}
            {_PAIR} Q() {{
                BitString<8> a = v[0];
                {_PAIR} v = [1^8, 1^8];
                return [a, v[0]];
            }}
        }}
        """)
    statements = _method(result, "Q")
    assert statements[0] == "BitString<8> a = v@0;"
    local0 = statements[1].split()[1]
    local1 = statements[2].split()[1]
    assert {local0, local1}.isdisjoint({"v@0", "v@1"})
    assert statements[1:] == [
        f"BitString<8> {local0} = 1^8;",
        f"BitString<8> {local1} = 1^8;",
        f"return [a, {local0}];",
    ]


def test_f399_typed_local_in_a_branch_does_not_write_the_field() -> None:
    # The branch's local v is never read, so it is not split; it used to be
    # rewritten into writes of the field's components.
    result = _expand(f"""
        Game T() {{
            {_PAIR} v;
            Void Initialize() {{
                v = [0^8, 0^8];
            }}
            BitString<8> Q(Bool c) {{
                if (c) {{
                    {_PAIR} v = [1^8, 1^8];
                }}
                return v[0];
            }}
        }}
        """)
    assert _method(result, "Q") == [
        f"if (c) {{ {_PAIR} v = [1^8, 1^8]; }}",
        "return v@0;",
    ]


def test_f399_inner_bare_local_keeps_its_reads_and_writes() -> None:
    # The inner bare v is not split (the outer read after the block names
    # v); it hides the field inside its block, and the read after the block
    # is the field's again (S35's probe E8).
    result = _expand(f"""
        Game T() {{
            {_PAIR} v;
            Void Initialize() {{
                v = [0^8, 0^8];
            }}
            {_PAIR} Q(Bool c) {{
                BitString<8> a = 0^8;
                if (c) {{
                    {_PAIR} v;
                    v = [1^8, 1^8];
                    a = v[1];
                }}
                return [a, v[1]];
            }}
        }}
        """)
    assert _method(result, "Q") == [
        "BitString<8> a = 0^8;",
        f"if (c) {{ {_PAIR} v; v = [1^8, 1^8]; a = v[1]; }}",
        "return [a, v@1];",
    ]


def test_f399_method_parameter_hides_the_split_field() -> None:
    result = _expand(f"""
        Game T() {{
            {_PAIR} v;
            Void Initialize() {{
                v = [0^8, 0^8];
            }}
            BitString<8> Q({_PAIR} v) {{
                return v[0];
            }}
            BitString<8> R() {{
                return v[1];
            }}
        }}
        """)
    assert _fields(result) == ["BitString<8> v@0;", "BitString<8> v@1;"]
    assert _method(result, "Q") == ["return v[0];"]
    assert _method(result, "R") == ["return v@1;"]


def test_f399_loop_binders_hide_the_split_field() -> None:
    result = _expand(f"""
        Game T() {{
            {_PAIR} v;
            [Int, Int] k;
            Void Initialize() {{
                v = [0^8, 0^8];
                k = [1, 2];
            }}
            BitString<8> Q(Set<{_PAIR}> S) {{
                BitString<8> a = 0^8;
                for ({_PAIR} v in S) {{
                    a = v[0];
                }}
                return a + v[1];
            }}
            Int R() {{
                Int a = 0;
                for (Int k = 0 to 3) {{
                    a = a + k;
                }}
                return a + k[1];
            }}
        }}
        """)
    assert _method(result, "Q") == [
        "BitString<8> a = 0^8;",
        f"for ({_PAIR} v in S) {{ a = v[0]; }}",
        "return a + v@1;",
    ]
    assert _method(result, "R") == [
        "Int a = 0;",
        "for (Int k = 0 to 3) { a = a + k; }",
        "return a + k@1;",
    ]


def test_f399_split_bare_local_is_hidden_by_an_inner_binder() -> None:
    # Split Bare Tuple Declarations: the bare local b is split; the inner
    # loop binder b is another variable and keeps its reads.
    game = frog_parser.parse_game(f"""
        Game T() {{
            BitString<8> Q(Set<BitString<8>> S) {{
                {_PAIR} b;
                b = [0^8, 1^8];
                BitString<8> a = 0^8;
                for (BitString<8> b in S) {{
                    a = a + b;
                }}
                return a + b[1];
            }}
        }}
        """)
    result = SplitBareTupleDeclarations().apply(game, _ctx())
    assert _method(result, "Q") == [
        "BitString<8> b@0;",
        "BitString<8> b@1;",
        "b@0 = 0^8;",
        "b@1 = 1^8;",
        "BitString<8> a = 0^8;",
        "for (BitString<8> b in S) { a = a + b; }",
        "return a + b@1;",
    ]
