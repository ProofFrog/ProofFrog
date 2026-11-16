"""Names a pass creates are fresh (F-369, F-370 part (b), F-396).

Split Product Sample (``v@i``), Generator Power Field To Exponent (``P@exp``),
Offset Fusion (``P@fused``, ``P@exp``, ``D@next<k>``), Field Invariant
Elimination (``a@entry``), and Expand Tuple and Split Bare Tuple Declarations
(``v@i`` for the components of a product field or local) add new fields or
locals to a game. Such a name
must not already be bound or mentioned in the game: a new local named like
an existing field captures the field's reads, and an existing local named
like the new one captures the rewritten reads. The parser cannot produce
``@`` names, but other passes do (Expand Tuple makes ``v@0`` from a product
field ``v``, Split Bare Tuple Declarations a bare ``T v@0;``), so these
tests build such games by renaming a parsed name. On a clash the pass picks
another name (``fresh_name``) and the game keeps its meaning.
"""

import copy

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext, fresh_name, game_names
from proof_frog.transforms.sampling import SplitProductSample
from proof_frog.transforms.state_relations import (
    FieldInvariantElimination,
    GeneratorPowerFieldToExponent,
    _fuse,
    _initialize,
)
from proof_frog.transforms.tuples import (
    ExpandTuple,
    ExpandTupleTransformer,
    SplitBareTupleDeclarations,
)
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


# --- Generator Power Field To Exponent (F-370 (b)) --------------------------

_GPFE_SOURCE = """
Game T(Group G) {
    GroupElem<G> P;
    Void Initialize() {
        ModInt<G.order> e <- ModInt<G.order>;
        P = G.generator ^ e;
    }
    [GroupElem<G>, GroupElem<G>] Upd(ModInt<G.order> d) {
        ModInt<G.order> Pexp = 5;
        P = P * G.generator ^ d;
        return [P, G.generator ^ Pexp];
    }
}
"""


def test_f370b_gpfe_new_field_is_not_named_like_a_local() -> None:
    # Upd declares a local P@exp. The exponent field replacing P must get
    # another name, or Upd's rewritten update and read of P would use the
    # local (returning [g^(5 + d), g^(5 + d)] for [g^(e + d), g^5]).
    game = _game(_GPFE_SOURCE, {"Pexp": "P@exp"})
    result = GeneratorPowerFieldToExponent().apply(game, _ctx())
    assert result != game
    ((exponent, field_type),) = [(f.name, f.type) for f in result.fields]
    assert exponent != "P@exp"
    assert isinstance(field_type, frog_ast.ModIntType)
    upd = _method(result, "Upd")
    assert _declared(upd.block) == ["P@exp"]
    assert str(upd.block.statements[0]) == "ModInt<G.order> P@exp = 5;"
    assert str(upd.block.statements[1]) == f"{exponent} = {exponent} + d;"
    assert str(_return_value(upd)) == (
        f"[G.generator ^ {exponent}, G.generator ^ P@exp]"
    )


def test_f370b_gpfe_keeps_the_usual_name_without_a_clash() -> None:
    game = _game(_GPFE_SOURCE, {})
    result = GeneratorPowerFieldToExponent().apply(game, _ctx())
    assert [f.name for f in result.fields] == ["P@exp"]


# --- Offset Fusion (F-370 (b)) ----------------------------------------------

_FUSION_SOURCE = """
Game T(Group G) {
    GroupElem<G> P;
    ModInt<G.order> D;
    Void Initialize() {
        ModInt<G.order> e <- ModInt<G.order>;
        P = G.generator ^ e;
        D = 0;
    }
    [GroupElem<G>, GroupElem<G>] Shift(ModInt<G.order> r) {
        ModInt<G.order> mine = 7;
        D = D + r;
        return [P * G.generator ^ D, G.generator ^ mine];
    }
}
"""


def _fused(game: frog_ast.Game) -> frog_ast.Game:
    init = _initialize(game)
    assert init is not None
    fixed = next(f for f in game.fields if f.name == "P")
    offset = next(f for f in game.fields if f.name == "D")
    fused = _fuse(game, init, fixed, offset, _ctx())
    assert fused is not None
    return fused


def test_f370b_offset_temporary_is_not_named_like_a_local() -> None:
    # Shift declares a local D@next0, the name of the temporary for Shift's
    # first write of D. A second declaration of it would make the local's
    # read return D + r instead of 7.
    game = _game(_FUSION_SOURCE, {"mine": "D@next0"})
    fused = _fused(copy.deepcopy(game))
    shift = _method(fused, "Shift")
    declared = _declared(shift.block)
    assert declared.count("D@next0") == 1
    assert str(shift.block.statements[0]) == "ModInt<G.order> D@next0 = 7;"
    (temporary,) = [n for n in declared if n != "D@next0"]
    assert str(shift.block.statements[1]) == f"ModInt<G.order> {temporary} = D + r;"
    assert str(_return_value(shift)).endswith(", G.generator ^ D@next0]")


def test_f370b_offset_fusion_renames_a_taken_fused_or_exponent_name() -> None:
    # Locals named P@fused and P@exp: the new field and Initialize's
    # exponent local get other names, and the user's locals stay as they are.
    for taken in ("P@fused", "P@exp"):
        game = _game(_FUSION_SOURCE, {"mine": taken})
        fused = _fused(copy.deepcopy(game))
        new_field = next(f.name for f in fused.fields if f.name != "D")
        exponent = _declared(_method(fused, "Initialize").block)[1]
        assert taken not in (new_field, exponent)
        shift = _method(fused, "Shift")
        assert str(shift.block.statements[0]) == f"ModInt<G.order> {taken} = 7;"
        assert str(_return_value(shift)).endswith(f", G.generator ^ {taken}]")


def test_f370b_offset_fusion_keeps_the_usual_names_without_a_clash() -> None:
    fused = _fused(_game(_FUSION_SOURCE, {}))
    assert [f.name for f in fused.fields] == ["D", "P@fused"]
    assert _declared(_method(fused, "Initialize").block) == ["e", "P@exp"]
    assert _declared(_method(fused, "Shift").block) == ["mine", "D@next0"]


# --- Field Invariant Elimination (same class) -------------------------------

_FIE_SOURCE = """
Game T(Group G) {
    GroupElem<G> pk;
    ModInt<G.order> sk;
    GroupElem<G> Initialize() {
        ModInt<G.order> x <- ModInt<G.order>;
        pk = G.generator ^ x;
        sk = x;
        return pk;
    }
    [GroupElem<G>, GroupElem<G>] Upd(ModInt<G.order> d) {
        GroupElem<G> mine = G.generator;
        sk = sk + d;
        pk = pk * G.generator ^ d;
        return [pk, mine];
    }
}
"""


def test_fie_entry_local_is_not_named_like_a_local() -> None:
    # pk is removed (pk == g ^ sk). Upd reads pk's entry value after sk has
    # moved, through a local pk@entry = g ^ sk. A local of that name already
    # in Upd must not be redeclared, or pk's new value would be computed
    # from it (g * g^d instead of g^(sk + d)).
    game = _game(_FIE_SOURCE, {"mine": "pk@entry"})
    result = FieldInvariantElimination().apply(game, _ctx())
    assert [f.name for f in result.fields] == ["sk"]
    upd = _method(result, "Upd")
    declared = _declared(upd.block)
    assert declared.count("pk@entry") == 1
    (entry,) = [n for n in declared if n not in ("pk@entry", "pk")]
    statements = [str(s) for s in upd.block.statements]
    assert f"GroupElem<G> {entry} = G.generator ^ sk;" in statements
    assert "GroupElem<G> pk@entry = G.generator;" in statements
    assert f"GroupElem<G> pk = {entry} * G.generator ^ d;" in statements
    assert str(_return_value(upd)) == "[pk, pk@entry]"


def test_fie_keeps_the_usual_entry_name_without_a_clash() -> None:
    result = FieldInvariantElimination().apply(_game(_FIE_SOURCE, {}), _ctx())
    assert "pk@entry" in _declared(_method(result, "Upd").block)


# --- Expand Tuple and Split Bare Tuple Declarations (F-396) -----------------


def test_f396_expand_field_does_not_capture_a_local_named_like_a_component() -> None:
    # Q declares a local v@0 (the name Split Product Sample gives component 0
    # of a local product draw v) and reads component 0 of the product field
    # v. The field's component 0 must not be named v@0, or Q's v[0] becomes
    # a read of the local and Q returns [1^8, 1^8] instead of [0^8, 1^8].
    game = _game(
        f"""
        Game T() {{
            {_PAIR} v;
            Void Initialize() {{
                v = [0^8, 1^8];
            }}
            {_PAIR} Q() {{
                BitString<8> vAT0 = 1^8;
                return [v[0], vAT0];
            }}
        }}
        """,
        {"vAT0": "v@0"},
    )
    result = ExpandTuple().apply(game, _ctx())
    component, second = [f.name for f in result.fields]
    assert component != "v@0" and second == "v@1"
    initialize = _method(result, "Initialize")
    assert [str(s) for s in initialize.block.statements] == [
        f"{component} = 0^8;",
        "v@1 = 1^8;",
    ]
    q = _method(result, "Q")
    assert _declared(q.block) == ["v@0"]
    assert str(_return_value(q)) == f"[{component}, v@0]"


def test_f396_expand_local_does_not_redeclare_a_local_named_like_a_component() -> None:
    # A local w@0 already in Q: the split of the local product w must not
    # declare w@0 again, or the return reads w[0] where it read the local.
    game = _game(
        f"""
        Game T() {{
            {_PAIR} Q() {{
                BitString<8> wAT0 = 1^8;
                {_PAIR} w = [0^8, 0^8];
                return [w[0], wAT0];
            }}
        }}
        """,
        {"wAT0": "w@0"},
    )
    result = ExpandTuple().apply(game, _ctx())
    q = _method(result, "Q")
    declared = _declared(q.block)
    assert declared.count("w@0") == 1
    component = declared[1]
    assert component != "w@0" and declared[2] == "w@1"
    assert str(_return_value(q)) == f"[{component}, w@0]"


def test_f396_split_bare_declaration_does_not_capture_a_field_named_like_a_component() -> (
    None
):
    # A field b@0 (Expand Tuple's name for component 0 of a product field b)
    # next to a bare local [T, T] b; in Q. The local's components must not
    # be named b@0, or the read of the field becomes a read of the local.
    game = _game(
        f"""
        Game T() {{
            BitString<8> bAT0;
            Void Initialize() {{
                bAT0 = 1^8;
            }}
            {_PAIR} Q() {{
                {_PAIR} b;
                b = [0^8, 0^8];
                return [b[0], bAT0];
            }}
        }}
        """,
        {"bAT0": "b@0"},
    )
    result = SplitBareTupleDeclarations().apply(game, _ctx())
    assert [f.name for f in result.fields] == ["b@0"]
    q = _method(result, "Q")
    declared = _declared(q.block)
    assert len(declared) == 2 and "b@0" not in declared
    component = declared[0]
    assert str(q.block.statements[2]) == f"{component} = 0^8;"
    assert str(_return_value(q)) == f"[{component}, b@0]"


def test_f396_expand_keeps_the_usual_names_without_a_clash() -> None:
    game = _game(
        f"""
        Game T() {{
            {_PAIR} v;
            Void Initialize() {{
                v = [0^8, 1^8];
            }}
            {_PAIR} Q() {{
                {_PAIR} w = [1^8, 0^8];
                {_PAIR} b;
                b = [v[1], w[0]];
                return [v[0], b[1]];
            }}
        }}
        """,
        {},
    )
    result = ExpandTuple().apply(game, _ctx())
    assert [f.name for f in result.fields] == ["v@0", "v@1"]
    q = _method(result, "Q")
    assert _declared(q.block) == ["w@0", "w@1", "b@0", "b@1"]
    assert str(_return_value(q)) == "[v@0, b@1]"


def test_f396_read_before_a_local_declaration_keeps_the_outer_variable() -> None:
    # The field v is not split (R reads it at a non-constant index). Q reads
    # v[0] before declaring a local product v, which is split. That first
    # read is the field's and must stay v[0]: rewritten to the local's
    # component, it would read a variable not declared yet.
    game = _game(
        f"""
        Game T() {{
            {_PAIR} v;
            Void Initialize() {{
                v = [0^8, 0^8];
            }}
            BitString<8> R(Int i) {{
                return v[i];
            }}
            {_PAIR} Q() {{
                BitString<8> a = v[0];
                {_PAIR} v = [1^8, 1^8];
                return [a, v[0]];
            }}
        }}
        """,
        {},
    )
    result = ExpandTuple().apply(game, _ctx())
    assert [f.name for f in result.fields] == ["v"]
    q = _method(result, "Q")
    assert [str(s) for s in q.block.statements] == [
        "BitString<8> a = v[0];",
        "BitString<8> v@0 = 1^8;",
        "BitString<8> v@1 = 1^8;",
        "return [a, v@0];",
    ]


def test_f396_bare_local_named_like_a_split_field_gets_its_own_components() -> None:
    # Q reads the split field v, then declares a bare local v, which is split
    # too. The two get components with different names, and each read
    # resolves to the variable in scope where it stands: the first to the
    # field's component, the return to the local's.
    game = _game(
        f"""
        Game T() {{
            {_PAIR} v;
            Void Initialize() {{
                v = [0^8, 0^8];
            }}
            {_PAIR} Q() {{
                BitString<8> a = v[0];
                {_PAIR} v;
                v = [1^8, 1^8];
                return [a, v[0]];
            }}
        }}
        """,
        {},
    )
    result = ExpandTuple().apply(game, _ctx())
    assert [f.name for f in result.fields] == ["v@0", "v@1"]
    q = _method(result, "Q")
    statements = [str(s) for s in q.block.statements]
    assert statements[0] == "BitString<8> a = v@0;"
    local0, local1 = _declared(q.block)[1:]
    assert {local0, local1}.isdisjoint({"v@0", "v@1"})
    assert statements[3:] == [
        f"{local0} = 1^8;",
        f"{local1} = 1^8;",
        f"return [a, {local0}];",
    ]


def test_f396_method_on_its_own_avoids_its_parameter_names() -> None:
    # Transformed without its game, a method's own names are the ones a
    # component may not take: here a parameter v@0.
    method = frog_parser.parse_method(f"""
        BitString<8> Q(BitString<8> vAT0) {{
            {_PAIR} v = [0^8, 1^8];
            return v[0] + vAT0;
        }}
        """)
    method.signature.parameters[0].name = "v@0"

    def visit(node: frog_ast.ASTNode) -> bool:
        if isinstance(node, frog_ast.Variable) and node.name == "vAT0":
            node.name = "v@0"
        return False

    SearchVisitor(visit).visit(method)
    result = ExpandTupleTransformer().transform(method)
    assert isinstance(result, frog_ast.Method)
    component, second = _declared(result.block)
    assert component != "v@0" and second == "v@1"
    assert str(_return_value(result)) == f"{component} + v@0"
