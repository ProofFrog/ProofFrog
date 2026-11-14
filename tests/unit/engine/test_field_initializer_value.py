"""F-384: a field initializer runs once, so a field is read as its
initializer only when evaluating the initializer again gives the same value.

Every field starts at its type's default, then the initializers run once, in
declaration order, each reading the current values of the fields declared
before it. ``InstantiationTransformer`` used to read every field that no
method writes as its initializer, so ``GroupElem<G> Q = P;`` became a
permanent alias of the current ``P``, and ``BitString<n> k = S.Draw();``
called ``S.Draw`` again at every read. Now a game or reduction field whose
initializer reads a field some method writes, or calls a method, stays a
field holding the value it was given, and a scheme with such a field is
refused. Before the passes run, ``visitors.snapshot_starting_values`` gives
each written field that an initializer reads a snapshot ``P@start`` that no
method writes, holding P's starting value, and the initializers read it, so
no initializer reads a written field. A challenger's field initializers
follow the ``challenger@`` rename when a reduction is composed with it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proof_frog import frog_ast, frog_parser, visitors
from proof_frog.proof_engine import instantiate
from proof_frog.web_server import _setup_engine_for_proof

_FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "integration"
    / "soundness_regression_fixtures"
    / "F_384"
)


def _method(root: frog_ast.Game | frog_ast.Scheme, name: str) -> frog_ast.Method:
    return next(m for m in root.methods if m.signature.name == name)


def _returned(root: frog_ast.Game | frog_ast.Scheme, name: str) -> frog_ast.Expression:
    ret = _method(root, name).block.statements[-1]
    assert isinstance(ret, frog_ast.ReturnStatement)
    return ret.expression


def _expr(text: str) -> frog_ast.Expression:
    return frog_parser.parse_expression(text)


# --- the predicate -----------------------------------------------------------


@pytest.mark.parametrize(
    "initializer, written, expected",
    [
        ("P", {"P"}, True),
        ("P + 1", {"P"}, True),
        ("P", {"R"}, False),
        ("n + 1", set(), False),
        ("S.Draw()", set(), True),
        ("[S.Draw(), 1]", set(), True),
        # A call of a Function value is deterministic.
        ("H(x)", set(), False),
        # ... and one held in a field a method writes is a read of that field.
        ("H(x)", {"H"}, True),
        ("E.lambda + 1", set(), False),
    ],
)
def test_f384_initializer_may_change(
    initializer: str, written: set[str], expected: bool
) -> None:
    assert visitors.initializer_may_change(_expr(initializer), written) is expected


def test_f384_scheme_instantiation_in_an_initializer_is_not_a_call() -> None:
    """A parameter replaced by its argument ``UG(K, NG)`` turns ``K.EncapsKey``
    into ``UG(K, NG).EncapsKey``: an instantiation, which evaluates nothing."""
    instance = frog_ast.FuncCall(
        frog_ast.Variable("UG"), [frog_ast.Variable("K"), frog_ast.Variable("NG")]
    )
    member = frog_ast.FieldAccess(instance, "EncapsKey")
    assert not visitors.initializer_may_change(member, set())
    method_call = frog_ast.FuncCall(frog_ast.FieldAccess(instance, "Encaps"), [])
    assert visitors.initializer_may_change(method_call, set())


def test_f384_written_field_names_include_fields_without_initializer() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Int a;
            Int b = 0;
            Int c = 1;
            Map<Int, Int> M;
            Void Upd() { a = 1; b = b + 1; M[0] = 1; }
            Int Get() { return c; }
        }
        """)
    assert visitors.written_field_names(game) == {"a", "b", "M"}


# --- games: instantiation keeps the field --------------------------------------


_ALIAS_REDRAW = """
    Game G() {
        Int P;
        Int Q = P;
        Void Initialize() { P = 5; }
        Void Upd() { P = P + 1; }
        Int GetQ() { return Q; }
    }
    """


def _snapshot(game: frog_ast.Game) -> frog_ast.Game:
    return visitors.snapshot_starting_values(instantiate(game, [], {}))


def test_f384_field_reading_a_written_field_stays_a_field() -> None:
    out = instantiate(frog_parser.parse_game(_ALIAS_REDRAW), [], {})
    assert [(f.name, str(f.value)) for f in out.fields] == [
        ("P", "None"),
        ("Q", "P"),
    ]
    assert _returned(out, "GetQ") == frog_ast.Variable("Q")


def test_f384_field_reading_a_written_initialized_field_stays_a_field() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Int c = 0;
            Int start = c;
            Void Bump() { c = c + 1; }
            Int Get() { return start; }
        }
        """)
    out = instantiate(game, [], {})
    assert _returned(out, "Get") == frog_ast.Variable("start")


def test_f384_element_write_counts_as_a_write() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Map<Int, Int> M;
            Map<Int, Int> N = M;
            Void Put(Int k) { M[k] = 1; }
            Map<Int, Int> Get() { return N; }
        }
        """)
    out = instantiate(game, [], {})
    assert _returned(out, "Get") == frog_ast.Variable("N")


def test_f384_field_initialized_by_a_method_call_stays_a_field() -> None:
    game = frog_parser.parse_game("""
        Game G(Src S) {
            BitString<8> k = S.Draw();
            BitString<8> Get() { return k; }
        }
        """)
    out = instantiate(game, [frog_ast.Variable("T")], {"T": None})
    assert [(f.name, str(f.value)) for f in out.fields] == [("k", "T.Draw()")]
    assert _returned(out, "Get") == frog_ast.Variable("k")


def test_f384_field_reading_an_unwritten_field_is_still_read_as_it() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int P = n;
            Int Q = P;
            Int R;
            Int S = R;
            Int GetQ() { return Q; }
            Int GetS() { return S; }
        }
        """)
    out = instantiate(game, [frog_ast.Variable("m")], {"m": None})
    assert _returned(out, "GetQ") == frog_ast.Variable("m")
    assert _returned(out, "GetS") == frog_ast.Variable("R")


def test_f384_field_reading_a_kept_field_is_read_as_it() -> None:
    """Q is kept (it reads the written P) but no method writes Q, so Q holds
    one value for the whole game and Q2 = Q may be read as Q."""
    game = frog_parser.parse_game("""
        Game G() {
            Int P;
            Int Q = P;
            Int Q2 = Q;
            Void Upd() { P = P + 1; }
            Int Get() { return Q2; }
        }
        """)
    out = instantiate(game, [], {})
    assert _returned(out, "Get") == frog_ast.Variable("Q")


def test_f384_field_initialized_by_a_function_value_is_read_as_the_call() -> None:
    game = frog_parser.parse_game("""
        Game G(Function<Int, Int> H) {
            Int y = H(3);
            Int Get() { return y; }
        }
        """)
    out = instantiate(game, [frog_ast.Variable("F")], {"F": None})
    assert _returned(out, "Get") == _expr("F(3)")


def test_f384_field_calling_a_sampled_function_field_stays_a_field() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Function<Int, Int> H;
            Int y = H(3);
            Void Initialize() { H <- Function<Int, Int>; }
            Int Get() { return y; }
        }
        """)
    out = instantiate(game, [], {})
    assert _returned(out, "Get") == frog_ast.Variable("y")


def test_f384_reduction_field_reading_a_written_field_stays_a_field() -> None:
    reduction = frog_parser.parse_reduction("""
        Reduction R() compose C() against T().Adversary {
            Int c = 0;
            Int start = c;
            Void Bump() { c = c + 1; }
            Int Get() { return start; }
        }
        """)
    out = instantiate(reduction, [], {})
    assert _returned(out, "Get") == frog_ast.Variable("start")


# --- games: the engine snapshots starting values -------------------------------


def test_f384_snapshot_of_a_field_without_initializer() -> None:
    out = _snapshot(frog_parser.parse_game(_ALIAS_REDRAW))
    assert [(f.name, str(f.value)) for f in out.fields] == [
        ("P@start", "None"),
        ("P", "None"),
        ("Q", "P@start"),
    ]
    assert _returned(out, "GetQ") == frog_ast.Variable("P@start")
    assert str(_method(out, "Upd").block).strip() == "P = P + 1;"


def test_f384_snapshot_of_an_initialized_field_reads_its_start() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Int c = 0;
            Int start = c;
            Void Bump() { c = c + 1; }
            Int Get() { return start; }
            Int GetC() { return c; }
        }
        """)
    out = _snapshot(game)
    assert _returned(out, "Get") == frog_ast.Integer(0)
    assert _returned(out, "GetC") == frog_ast.Variable("c")
    assert {f.name: str(f.value) for f in out.fields}["c"] == "0"


def test_f384_snapshot_of_an_element_written_map() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Map<Int, Int> M;
            Map<Int, Int> N = M;
            Void Put(Int k) { M[k] = 1; }
            Map<Int, Int> Get() { return N; }
        }
        """)
    assert _returned(_snapshot(game), "Get") == frog_ast.Variable("M@start")


def test_f384_snapshot_for_a_written_field_reading_a_written_field() -> None:
    """``a = n`` with both written: a starts at n's starting value 7, not at
    whatever n holds when a pass looks (Inline Single-Use Field used to drop
    n, which no method reads, leaving ``a = n`` naming nothing)."""
    game = frog_parser.parse_game("""
        Game G() {
            Int n = 7;
            Int a = n;
            Void SetN(Int x) { n = x; }
            Void Bump() { a = a + 1; }
            Int Get() { return a; }
        }
        """)
    assert {f.name: str(f.value) for f in _snapshot(game).fields}["a"] == "7"


def test_f384_snapshot_for_a_written_parameter() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int a = n;
            Void Bump() { n = n + 1; }
            Int Get() { return a; }
        }
        """)
    out = visitors.snapshot_starting_values(
        instantiate(game, [frog_ast.Variable("m")], {"m": None})
    )
    assert [(f.name, str(f.value)) for f in out.fields] == [
        ("n@start", "m"),
        ("n", "m"),
        ("a", "m"),
    ]
    assert _returned(out, "Get") == frog_ast.Variable("m")


def test_f384_snapshot_of_a_call_initializer_draws_once() -> None:
    """A written field initialized by a call keeps that one call in its
    snapshot; the field and its copy both start from the snapshot."""
    game = frog_parser.parse_game("""
        Game G(Src S) {
            BitString<8> k = S.Draw();
            BitString<8> k2 = k;
            Void Redraw() { k = S.Draw(); }
            BitString<8> Get() { return k2; }
        }
        """)
    out = visitors.snapshot_starting_values(
        instantiate(game, [frog_ast.Variable("T")], {"T": None})
    )
    assert [(f.name, str(f.value)) for f in out.fields] == [
        ("k@start", "T.Draw()"),
        ("k", "k@start"),
        ("k2", "k@start"),
    ]
    assert _returned(out, "Get") == frog_ast.Variable("k@start")


def test_f384_snapshot_of_a_sampled_function_field() -> None:
    """y = H(3) runs before Initialize draws H, so y is the default function
    of its type at 3: a call of H's snapshot, which no method writes and no
    pass takes for a random function."""
    game = frog_parser.parse_game("""
        Game G() {
            Function<Int, Int> H;
            Int y = H(3);
            Void Initialize() { H <- Function<Int, Int>; }
            Int Get() { return y; }
        }
        """)
    assert _returned(_snapshot(game), "Get") == frog_ast.FuncCall(
        frog_ast.Variable("H@start"), [frog_ast.Integer(3)]
    )


def test_f384_snapshot_of_a_reduction_field() -> None:
    reduction = frog_parser.parse_reduction("""
        Reduction R() compose C() against T().Adversary {
            Int c = 0;
            Int start = c;
            Void Bump() { c = c + 1; }
            Int Get() { return start; }
        }
        """)
    out = visitors.snapshot_starting_values(instantiate(reduction, [], {}))
    assert isinstance(out, frog_ast.Reduction)
    assert _returned(out, "Get") == frog_ast.Integer(0)


def test_f384_no_snapshot_when_no_initializer_reads_a_written_field() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Int P;
            Int Q = 3;
            Void Upd() { P = P + 1; }
            Int Get() { return P + Q; }
        }
        """)
    instantiated = instantiate(game, [], {})
    assert visitors.snapshot_starting_values(instantiated) is instantiated


def test_f384_snapshot_name_avoids_a_taken_name() -> None:
    game = instantiate(frog_parser.parse_game(_ALIAS_REDRAW), [], {})
    taken = frog_ast.Field(frog_ast.IntType(), "P@start", None)
    game.fields = [taken] + list(game.fields)
    out = visitors.snapshot_starting_values(game)
    assert [f.name for f in out.fields] == ["P@start", "P@start1", "P", "Q"]
    assert _returned(out, "GetQ") == frog_ast.Variable("P@start1")


# --- schemes -------------------------------------------------------------------


def _scheme(fields: str, body: str) -> frog_ast.Scheme:
    return frog_parser.parse_scheme_file(
        f"Scheme S(Src T) extends P {{\n    {fields}\n    {body}\n}}\n"
    )


def test_f384_scheme_field_reading_a_written_field_is_refused() -> None:
    scheme = _scheme(
        "Int c = 0; Int start = c;", "Int Next() { c = c + 1; return start; }"
    )
    with pytest.raises(visitors.ChangingFieldInitializerError, match="'start'"):
        instantiate(scheme, [frog_ast.Variable("U")], {"U": None})


def test_f384_scheme_field_initialized_by_a_method_call_is_refused() -> None:
    scheme = _scheme("BitString<8> k = T.Draw();", "BitString<8> Get() { return k; }")
    with pytest.raises(visitors.ChangingFieldInitializerError, match="'k'"):
        instantiate(scheme, [frog_ast.Variable("U")], {"U": None})


def test_f384_scheme_field_reading_an_unwritten_field_is_read_as_it() -> None:
    scheme = _scheme("Int a = 4; Int b = a + 1;", "Int Get() { return b; }")
    out = instantiate(scheme, [frog_ast.Variable("U")], {"U": None})
    assert _returned(out, "Get") == _expr("4 + 1")


def test_f384_scheme_field_access_is_not_read_as_a_method_call() -> None:
    """``S.k`` read from outside, on a scheme definition (the
    ``UG(K, NG).EncapsKey`` path), is not replaced by a call initializer."""
    scheme = _scheme("BitString<8> k = T.Draw();", "BitString<8> Get() { return k; }")
    # pylint: disable=protected-access
    assert visitors._field_alias_value(scheme, "k") is None
    # pylint: enable=protected-access
    plain = _scheme("Int a = 4;", "Int Get() { return a; }")
    # pylint: disable=protected-access
    assert visitors._field_alias_value(plain, "a") == frog_ast.Integer(4)
    # pylint: enable=protected-access


# --- composition ---------------------------------------------------------------


def test_f384_challenger_field_initializer_follows_the_rename() -> None:
    engine, proof_file = _setup_engine_for_proof(
        str(_FIXTURES / "challenger_initializer.proof")
    )
    step = proof_file.steps[1]  # Starting(S).Real compose R(S)
    game = engine.resolve_step_game(step.challenger, step.reduction)
    values = {f.name: f.value for f in game.fields}
    assert values["challenger@C"] == frog_ast.Variable("challenger@D")
    assert values["D"] is not None  # R's own field, not read by challenger@C
