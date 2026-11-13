"""F-383: a game parameter the game writes is a variable of the game's own.

A parameter receives its argument by value, so inside a game it is the
game's own variable, starting out at the argument's value.
``proof_engine.instantiate`` used to substitute the argument for the
parameter everywhere, written positions included: in ``Void Bump() { n = n +
1; }`` the write went to the caller's name (and was then dropped as dead),
while every read of ``n`` kept reading the argument. Now a game or reduction
parameter that one of the root's methods writes becomes a game field
initialized with the argument, like a parameter whose argument the store
would convert (F-374), and a scheme that writes its own parameter is
refused. A field whose initializer reads such a parameter holds the
parameter's starting value, so it is not read as its initializer either.
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.proof_engine import WrittenParameterError, instantiate


def _m() -> frog_ast.Variable:
    return frog_ast.Variable("m")


def _method(root: frog_ast.Game | frog_ast.Scheme, name: str) -> frog_ast.Method:
    return next(m for m in root.methods if m.signature.name == name)


def _returned(root: frog_ast.Game | frog_ast.Scheme, name: str) -> frog_ast.Expression:
    ret = _method(root, name).block.statements[-1]
    assert isinstance(ret, frog_ast.ReturnStatement)
    return ret.expression


def _fields(root: frog_ast.Game) -> list[tuple[str, str, str]]:
    return [(str(f.type), f.name, str(f.value)) for f in root.fields]


_COUNTER = """
    Game G(Int n) {
        Void Bump() { n = n + 1; }
        Int Get() { return n; }
    }
    """


def test_f383_written_game_parameter_is_bound_as_a_field() -> None:
    out = instantiate(frog_parser.parse_game(_COUNTER), [_m()], {"m": None})
    assert not out.parameters
    assert _fields(out) == [("Int", "n", "m")]
    assert str(_method(out, "Bump").block).strip() == "n = n + 1;"
    assert _returned(out, "Get") == frog_ast.Variable("n")


def test_f383_written_parameter_named_like_its_argument_is_renamed() -> None:
    """With the argument ``n`` the field must not read as the caller's ``n``."""
    out = instantiate(frog_parser.parse_game(_COUNTER), [frog_ast.Variable("n")], {})
    assert len(out.fields) == 1
    field = out.fields[0]
    assert field.name != "n"
    assert field.value == frog_ast.Variable("n")
    assert _returned(out, "Get") == frog_ast.Variable(field.name)
    assert str(_method(out, "Bump").block).strip() == (
        f"{field.name} = {field.name} + 1;"
    )


def test_f383_read_only_parameter_is_still_substituted() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int Get() { return n + 1; }
        }
        """)
    out = instantiate(game, [_m()], {"m": None})
    assert not out.fields
    assert _returned(out, "Get") == frog_parser.parse_expression("m + 1")


@pytest.mark.parametrize(
    "params,write",
    [
        ("Int n", "Void Initialize() { n = 0; }"),
        ("BitString<8> n", "Void Redraw() { n <- BitString<8>; }"),
        ("Map<Int, Int> n", "Void Put(Int k) { n[k] = 1; }"),
        (
            "Set<BitString<8>> n",
            "Void Fresh() { BitString<8> x <-uniq[n] BitString<8>; }",
        ),
        ("Int n", "Void Bump(Bool b) { if (b) { n = n + 1; } }"),
    ],
    ids=["initialize", "draw", "element", "uniq_insert", "nested"],
)
def test_f383_every_kind_of_write_binds_the_parameter(params: str, write: str) -> None:
    game = frog_parser.parse_game(f"""
        Game G({params}) {{
            {write}
            Bool Peek() {{ return n == n; }}
        }}
        """)
    out = instantiate(game, [_m()], {"m": None})
    assert [(f.name, f.value) for f in out.fields] == [("n", _m())]
    assert _returned(out, "Peek") == frog_parser.parse_expression("n == n")


def test_f383_write_to_a_shadowing_local_is_not_a_parameter_write() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int Count() {
                Int n = 5;
                n = n + 1;
                return n;
            }
            Int Get() { return n; }
        }
        """)
    out = instantiate(game, [_m()], {"m": None})
    assert not out.fields
    assert _returned(out, "Get") == _m()


def test_f383_write_to_a_shadowing_method_parameter_is_not_a_parameter_write() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int Twice(Int n) {
                n = n + n;
                return n;
            }
            Int Get() { return n; }
        }
        """)
    out = instantiate(game, [_m()], {"m": None})
    assert not out.fields
    assert _returned(out, "Get") == _m()


def test_f383_field_initialized_from_a_written_parameter_stays_a_field() -> None:
    """``a`` holds n's starting value; read as its initializer it would
    follow ``Bump``'s writes to ``n``."""
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int a = n;
            Void Bump() { n = n + 1; }
            Int Get() { return a; }
        }
        """)
    out = instantiate(game, [_m()], {"m": None})
    assert _fields(out) == [("Int", "n", "m"), ("Int", "a", "n")]
    assert _returned(out, "Get") == frog_ast.Variable("a")


def test_f383_field_initialized_from_a_read_only_parameter_is_read_as_it() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int a = n;
            Int Get() { return a; }
        }
        """)
    out = instantiate(game, [_m()], {"m": None})
    assert _returned(out, "Get") == _m()


def test_f383_written_reduction_parameter_is_bound_as_a_field() -> None:
    reduction = frog_parser.parse_reduction("""
        Reduction R(Int n) compose P(n) against Q(n).Adversary {
            Void Bump() { n = n + 1; }
            Int Get() { return n; }
        }
        """)
    out = instantiate(reduction, [_m()], {"m": None})
    assert isinstance(out, frog_ast.Reduction)
    assert _fields(out) == [("Int", "n", "m")]
    assert _returned(out, "Get") == frog_ast.Variable("n")


def test_f383_written_and_converting_parameter_is_bound_once() -> None:
    game = frog_parser.parse_game("""
        Game G(Int q, ModInt<q> x) {
            Void Bump() { x = x + x; }
            ModInt<q> Get() { return x; }
        }
        """)
    out = instantiate(
        game,
        [frog_ast.Variable("q"), frog_ast.Variable("q")],
        {"q": None},
        arg_types=[frog_ast.IntType(), frog_ast.IntType()],
    )
    assert _fields(out) == [("ModInt<q>", "x", "q")]


def _scheme(body: str) -> frog_ast.Scheme:
    return frog_parser.parse_scheme_file(
        f"Scheme S(Int n) extends P {{\n    {body}\n}}\n"
    )


def test_f383_scheme_writing_its_parameter_is_refused() -> None:
    with pytest.raises(WrittenParameterError, match="'n'"):
        instantiate(_scheme("Int Next() { n = n + 1; return n; }"), [_m()], {"m": None})


def test_f383_scheme_writing_a_shadowing_local_is_substituted() -> None:
    out = instantiate(
        _scheme(
            "Int Next() { Int n = 0; n = n + 1; return n; } Int Get() { return n; }"
        ),
        [_m()],
        {"m": None},
    )
    assert _returned(out, "Get") == _m()


def test_f383_scheme_reading_its_parameter_is_substituted() -> None:
    out = instantiate(_scheme("Int Get() { return n + 1; }"), [_m()], {"m": None})
    assert _returned(out, "Get") == frog_parser.parse_expression("m + 1")
