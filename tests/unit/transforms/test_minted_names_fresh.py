"""Names a pass creates are fresh (F-369, F-370 part (b)).

Split Product Sample (``v@i``) adds new locals to a game. Such a name
must not already be bound or mentioned in the game: a new local named like
an existing field captures the field's reads, and an existing local named
like the new one captures the rewritten reads. The parser cannot produce
``@`` names, but other passes do (Expand Tuple makes ``v@0`` from a product
field ``v``, Split Bare Tuple Declarations a bare ``T v@0;``), so these
tests build such games by renaming a parsed name. On a clash the pass picks
another name (``fresh_name``) and the game keeps its meaning.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext, fresh_name, game_names
from proof_frog.transforms.sampling import SplitProductSample
from proof_frog.visitors import NameTypeMap, SearchVisitor


def _ctx() -> PipelineContext:
    lets = NameTypeMap()
    lets.set("G", frog_ast.GroupType())
    return PipelineContext(
        variables={}, proof_let_types=lets, proof_namespace={}, subsets_pairs=[]
    )


def _game(source: str, renames: dict[str, str]) -> frog_ast.Game:
    """Parse *source*, then rename fields, variables and bare declarations
    per *renames* (to names the parser cannot read, such as ``v@0``)."""
    game = frog_parser.parse_game(source)
    for field in game.fields:
        field.name = renames.get(field.name, field.name)

    def visit(node: frog_ast.ASTNode) -> bool:
        if isinstance(node, (frog_ast.Variable, frog_ast.VariableDeclaration)):
            node.name = renames.get(node.name, node.name)
        return False

    SearchVisitor(visit).visit(game)
    return game


def _method(game: frog_ast.Game, name: str) -> frog_ast.Method:
    return next(m for m in game.methods if m.signature.name == name)


def _declared(block: frog_ast.Block) -> list[str]:
    """Names declared by typed statements and bare declarations, in order."""
    names: list[str] = []

    def visit(node: frog_ast.ASTNode) -> bool:
        if (
            isinstance(node, (frog_ast.Assignment, frog_ast.Sample))
            and node.the_type is not None
            and isinstance(node.var, frog_ast.Variable)
        ):
            names.append(node.var.name)
        elif isinstance(node, frog_ast.VariableDeclaration):
            names.append(node.name)
        return False

    SearchVisitor(visit).visit(block)
    return names


def _return_value(method: frog_ast.Method) -> frog_ast.Expression:
    last = method.block.statements[-1]
    assert isinstance(last, frog_ast.ReturnStatement)
    return last.expression


# --- the shared helpers -----------------------------------------------------


def test_fresh_name_keeps_a_free_base() -> None:
    taken = {"a", "b"}
    assert fresh_name("v@0", taken) == "v@0"
    assert "v@0" in taken


def test_fresh_name_avoids_taken_names_and_its_own_results() -> None:
    taken = {"v@0", "v@0@fresh1"}
    first = fresh_name("v@0", taken)
    second = fresh_name("v@0", taken)
    assert first == "v@0@fresh2"
    assert second == "v@0@fresh3"
    assert {first, second} <= taken


def test_game_names_covers_every_kind_of_binding_and_reference() -> None:
    game = frog_parser.parse_game("""
        Game T(Int n, Group G) {
            BitString<n> f;
            Set S = BitString<n>;
            Void Initialize() {
                f <- BitString<n>;
            }
            BitString<n> Q(BitString<n> m, Bool c) {
                BitString<n> bare;
                BitString<n> local = m;
                for (Int i = 0 to n) {
                    local = local + f;
                }
                if (c) {
                    bare = 0^n;
                }
                return E.Enc(bare, local);
            }
        }
        """)
    names = game_names(game)
    # parameters, fields, method parameters, bare and typed locals, a loop
    # binder, and free names (a scheme, a type name, a group parameter)
    assert {"n", "G", "f", "S", "m", "c", "bare", "local", "i", "E"} <= names


# --- Split Product Sample (F-369) -------------------------------------------

_PAIR = "[BitString<8>, BitString<8>]"


def test_f369_split_does_not_capture_a_field_named_like_a_component() -> None:
    # A field v@0 (Expand Tuple's name for component 0 of a product field v)
    # is read after a product draw of the local v. The component of the
    # draw must not be named v@0, or the read of the field becomes a read
    # of the fresh sample.
    game = _game(
        f"""
        Game T() {{
            BitString<8> vAT0;
            Void Initialize() {{
                vAT0 <- BitString<8>;
            }}
            BitString<8> Q() {{
                {_PAIR} v <- {_PAIR};
                return v[0] + vAT0;
            }}
        }}
        """,
        {"vAT0": "v@0"},
    )
    result = SplitProductSample().apply(game, _ctx())
    q = _method(result, "Q")
    declared = _declared(q.block)
    assert len(declared) == 2 and "v@0" not in declared
    assert str(_return_value(q)) == f"{declared[0]} + v@0"
    assert [f.name for f in result.fields] == ["v@0"]


def test_f369_split_does_not_capture_a_bare_declaration() -> None:
    # A bare declaration T v@0; (Split Bare Tuple Declarations' name) in the
    # same method: the component must not redeclare it.
    game = _game(
        f"""
        Game T() {{
            BitString<8> Q(Bool c) {{
                BitString<8> vAT0;
                if (c) {{
                    vAT0 = 0^8;
                }}
                {_PAIR} v <- {_PAIR};
                return v[0] + vAT0;
            }}
        }}
        """,
        {"vAT0": "v@0"},
    )
    result = SplitProductSample().apply(game, _ctx())
    q = _method(result, "Q")
    declared = _declared(q.block)
    assert declared.count("v@0") == 1
    component = declared[1]
    assert component != "v@0"
    assert str(_return_value(q)) == f"{component} + v@0"


def test_f369_split_keeps_the_usual_names_without_a_clash() -> None:
    game = _game(
        f"""
        Game T() {{
            BitString<8> Q() {{
                {_PAIR} v <- {_PAIR};
                return v[0] + v[1];
            }}
        }}
        """,
        {},
    )
    result = SplitProductSample().apply(game, _ctx())
    q = _method(result, "Q")
    assert _declared(q.block) == ["v@0", "v@1"]
    assert str(_return_value(q)) == "v@0 + v@1"
