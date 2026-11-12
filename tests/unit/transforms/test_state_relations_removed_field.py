"""A pass that removes a field leaves no unbound reference to it (F-359, F-360).

Field Invariant Elimination, Generator Power Field To Exponent and Offset
Fusion each remove a field and rewrite the reads of it they understand. Any
other occurrence of the name (another field's type or initializer, a
signature, a type or literal length outside the locals the pass declares)
would afterwards name something else, such as a proof ``let:`` entry of the
same name, so the pass must keep the field. Field Invariant Elimination's
symbolic executor must also read ``1^c`` with the current value of ``c``.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.state_relations import (
    FieldInvariantElimination,
    GeneratorPowerFieldToExponent,
    OffsetFusion,
    _replace_names,
    _unbound_reference,
)
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    lets = NameTypeMap()
    lets.set("G", frog_ast.GroupType())
    lets.set("n", frog_ast.IntType())
    return PipelineContext(
        variables={}, proof_let_types=lets, proof_namespace={}, subsets_pairs=[]
    )


def _game(params: str, body: str) -> frog_ast.Game:
    return frog_parser.parse_game(f"Game T({params}) {{\n{body}\n}}")


def _field_names(game: frog_ast.Game) -> list[str]:
    return [field.name for field in game.fields]


def _reasons(ctx: PipelineContext, transform: str) -> list[str]:
    return [nm.reason for nm in ctx.near_misses if nm.transform_name == transform]


# --- Generator Power Field To Exponent (F-359) ------------------------------

_GPFE_BODY = """
    GroupElem<G> h;
    GroupElem<G> Q = {init};

    Void Initialize() {{
        ModInt<G.order> e <- ModInt<G.order>;
        h = G.generator ^ e;
    }}

    GroupElem<G> Upd(ModInt<G.order> d) {{
        h = h * G.generator ^ d;
        Q = Q * G.generator;
        return h;
    }}

    GroupElem<G> GetQ() {{
        return Q;
    }}
"""


def test_f359_gpfe_keeps_a_field_another_field_is_initialized_from() -> None:
    # Q starts at h's default value. With h replaced by h@exp, Q's
    # initializer would name a field that no longer exists (and read a
    # proof let entry h, if there is one).
    game = _game("Group G", _GPFE_BODY.format(init="h"))
    ctx = _ctx()
    assert GeneratorPowerFieldToExponent().apply(game, ctx) == game
    (reason,) = _reasons(ctx, "Generator Power Field To Exponent")
    assert "field 'Q'" in reason


def test_f359_gpfe_still_fires_when_no_other_field_names_it() -> None:
    game = _game("Group G, GroupElem<G> pub", _GPFE_BODY.format(init="pub"))
    result = GeneratorPowerFieldToExponent().apply(game, _ctx())
    assert _field_names(result) == ["h@exp", "Q"]
    assert _unbound_reference(result, "h") is None


# --- Offset Fusion (F-359) ---------------------------------------------------

_FUSION_BODY = """
    GroupElem<G> h;
    ModInt<G.order> D;
    GroupElem<G> Q = {init};

    Void Initialize() {{
        ModInt<G.order> e <- ModInt<G.order>;
        h = G.generator ^ e;
        D = 0;
    }}

    GroupElem<G> Shift(ModInt<G.order> r) {{
        D = D + r;
        Q = Q * G.generator;
        return h * G.generator ^ D;
    }}

    GroupElem<G> GetQ() {{
        return Q;
    }}
"""


def test_f359_offset_fusion_keeps_a_fixed_key_another_field_is_initialized_from() -> (
    None
):
    game = _game("Group G", _FUSION_BODY.format(init="h"))
    ctx = _ctx()
    assert OffsetFusion().apply(game, ctx) == game
    assert any("field 'Q'" in r for r in _reasons(ctx, "Offset Fusion"))


def test_f359_offset_fusion_still_fires_when_no_other_field_names_it() -> None:
    game = _game("Group G, GroupElem<G> pub", _FUSION_BODY.format(init="pub"))
    result = OffsetFusion().apply(game, _ctx())
    assert "h" not in _field_names(result)
    assert "h@fused" in _field_names(result)
    assert _unbound_reference(result, "h") is None


# --- Field Invariant Elimination (F-359, F-360) ------------------------------


def test_f359_fie_keeps_a_field_another_field_is_initialized_from() -> None:
    # a == b + 1 holds at every call boundary, but q's initializer runs
    # before Initialize, when a holds its default: it cannot become b + 1.
    game = _game(
        "Int n",
        """
    Int a;
    Int b;
    Int q = a;

    Void Initialize(Int s) {
        b = s;
        a = s + 1;
    }

    Int Step() {
        a = a + 1;
        b = b + 1;
        return a + q;
    }
    """,
    )
    ctx = _ctx()
    assert FieldInvariantElimination().apply(game, ctx) == game
    (reason,) = _reasons(ctx, "Field Invariant Elimination")
    assert "field 'q'" in reason


def test_f360_fie_keeps_a_field_named_in_a_signature() -> None:
    # The return type names a.
    game = _game(
        "Int n",
        """
    Int a;
    Int b;

    Void Initialize(Int s) {
        b = s;
        a = s + 1;
    }

    BitString<a * a + 1> Samp() {
        BitString<a * a + 1> x <- BitString<a * a + 1>;
        a = a + 1;
        b = b + 1;
        return x;
    }
    """,
    )
    ctx = _ctx()
    assert FieldInvariantElimination().apply(game, ctx) == game
    (reason,) = _reasons(ctx, "Field Invariant Elimination")
    assert "signature of 'Samp'" in reason


def test_f360_fie_keeps_a_field_named_in_a_sample_type_before_its_local() -> None:
    # The draw precedes the first write of a, so it sits in the prefix that
    # reads a@entry; its type is not rewritten and would name nothing.
    game = _game(
        "Int n",
        """
    Int a;
    Int b;

    Void Initialize(Int s) {
        b = s;
        a = s + 1;
    }

    Int Samp() {
        BitString<a * a + 1> x <- BitString<a * a + 1>;
        a = a + 1;
        b = b + 1;
        return |x|;
    }
    """,
    )
    ctx = _ctx()
    assert FieldInvariantElimination().apply(game, ctx) == game
    (reason,) = _reasons(ctx, "Field Invariant Elimination")
    assert "a statement of 'Samp'" in reason


def test_f360_fie_keeps_a_field_named_in_another_fields_type() -> None:
    game = _game(
        "Int n",
        """
    Int a;
    Int b;
    BitString<a> z;

    Void Initialize(Int s) {
        b = s;
        a = s + 1;
    }

    Int Step() {
        a = a + 1;
        b = b + 1;
        return a;
    }
    """,
    )
    assert FieldInvariantElimination().apply(game, _ctx()) == game


def test_f360_fie_keeps_a_set_field_sampled_from_before_its_local() -> None:
    # The draw y <- a reads the removed Set field before its first write. The
    # pass keeps a; it may still remove b (== a), read only as a value.
    game = _game(
        "Int n",
        """
    Set<BitString<n>> a;
    Set<BitString<n>> b;
    Set<BitString<n>> c;

    Void Initialize(BitString<n> s, BitString<n> t) {
        b = {s};
        c = {t};
        a = b;
    }

    BitString<n> Draw(BitString<n> x) {
        BitString<n> y <- a;
        a = a union {x};
        b = b union {x};
        c = c union {x};
        return y;
    }
    """,
    )
    ctx = _ctx()
    result = FieldInvariantElimination().apply(game, ctx)
    assert _field_names(result) == ["a", "c"]
    assert _unbound_reference(result, "b") is None
    (reason,) = _reasons(ctx, "Field Invariant Elimination")
    assert "Removing field 'a'" in reason and "'Draw'" in reason


def test_f360_fie_type_after_the_new_local_still_fires() -> None:
    # After its first write, a is the local holding the field's value, so a
    # type naming a there reads that local.
    game = _game(
        "Int n",
        """
    Int a;
    Int b;

    Void Initialize(Int s) {
        b = s;
        a = s + 1;
    }

    Int Samp() {
        a = a + 1;
        b = b + 1;
        BitString<a> x <- BitString<a>;
        return |x|;
    }
    """,
    )
    result = FieldInvariantElimination().apply(game, _ctx())
    assert _field_names(result) == ["b"]
    assert _unbound_reference(result, "a") is None


def test_f360_fie_rewrites_a_literal_length_read_before_the_first_write() -> None:
    # 0^a before a's first write reads the entry value b + 1.
    game = _game(
        "Int n",
        """
    Int a;
    Int b;

    Void Initialize(Int s) {
        b = s;
        a = s + 1;
    }

    Bool Test(BitString<n> y) {
        Bool r = y == 0^a;
        a = a + 1;
        b = b + 1;
        return r;
    }
    """,
    )
    result = FieldInvariantElimination().apply(game, _ctx())
    assert _field_names(result) == ["b"]
    assert "0^(b + 1)" in str(result)
    assert _unbound_reference(result, "a") is None


_LITERAL_LENGTH_BODY = """
    BitString<n> a;
    BitString<n> b;
    Int c;

    Void Initialize() {{
        a = 0^n;
        b = 0^n;
        c = 1;
    }}

    Void Upd() {{
        {upd}
    }}

    BitString<n> GetA() {{
        return a;
    }}

    BitString<n> GetB() {{
        return b;
    }}
"""


def test_f360_fie_reads_a_literal_length_at_its_current_value() -> None:
    # a is set from 1^c before c = c + 1 and b after it,
    # so a != b after Upd. Copying 1^c without mapping c proved a == b.
    game = _game(
        "Int n",
        _LITERAL_LENGTH_BODY.format(
            upd="a = (1^c || 0^n)[0 : n]; c = c + 1; b = (1^c || 0^n)[0 : n];"
        ),
    )
    ctx = _ctx()
    assert FieldInvariantElimination().apply(game, ctx) == game
    assert any("'Upd'" in r for r in _reasons(ctx, "Field Invariant Elimination"))


def test_f360_fie_literal_length_of_one_value_still_fires() -> None:
    # a and b are both set from the same value of c.
    game = _game(
        "Int n",
        _LITERAL_LENGTH_BODY.format(
            upd="a = (1^c || 0^n)[0 : n]; b = (1^c || 0^n)[0 : n]; c = c + 1;"
        ),
    )
    result = FieldInvariantElimination().apply(game, _ctx())
    assert len(result.fields) == 2


# --- The helpers ---------------------------------------------------------------


def test_f360_replace_names_reaches_literal_lengths_and_groups() -> None:
    expr = frog_parser.parse_expression("0^c || 1^(c + 1)")
    replaced = _replace_names(expr, {"c": frog_ast.Variable("d")})
    assert str(replaced) == "0^d || 1^(d + 1)"
    generator = frog_ast.GroupGenerator(frog_ast.Variable("G"))
    replaced = _replace_names(generator, {"G": frog_ast.Variable("H")})
    assert replaced == frog_ast.GroupGenerator(frog_ast.Variable("H"))


def test_f360_unbound_reference_follows_block_scope() -> None:
    # A local declared inside an if block does not bind the read after it.
    game = _game(
        "Int n",
        """
    Int b;

    Int Branch(Bool t) {
        if (t) {
            Int a = b;
            b = a;
        }
        return a;
    }
    """,
    )
    assert _unbound_reference(game, "a") == ("a statement of 'Branch'", "Branch")
    bound = _game(
        "Int n",
        """
    Int b;

    Int Straight() {
        Int a = b;
        BitString<a> x <- BitString<a>;
        return |x|;
    }
    """,
    )
    assert _unbound_reference(bound, "a") is None
    own = _game(
        "Int n",
        """
    Int b;

    Int Own() {
        BitString<a> a <- BitString<a>;
        return b;
    }
    """,
    )
    assert _unbound_reference(own, "a") == ("a statement of 'Own'", "Own")
