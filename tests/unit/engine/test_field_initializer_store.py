"""F-356: a field initializer is a store into the field.

``ModInt<q> f = q;`` with ``q : Int`` holds ``q`` reduced modulo ``q``, not
``q``. ``proof_engine.instantiate`` used to register every never-written
field's initializer for substitution into the field's reads (and to read
``S.f`` as the scheme field's initializer), which dropped that reduction.
It may now read a field as its initializer only when the store keeps the
value: the initializer has the field's type, or the field holds no
``ModInt``. An integer literal is an ``Int``, so it converts too, even one
the modulus represents as itself (``ModInt<2> f = 1;``): replaced by the
literal, a read would be ``Int`` arithmetic (``f + f == f - f`` would become
the false ``1 + 1 == 1 - 1``). A game field that converts stays a field; a
scheme field that converts is refused, since its scheme's methods would
carry the field's name into every game they are inlined into.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proof_frog import frog_ast, frog_parser, visitors
from proof_frog.proof_engine import instantiate


def _q() -> frog_ast.Variable:
    return frog_ast.Variable("q")


def _test_return(root: frog_ast.Game | frog_ast.Scheme) -> frog_ast.Expression:
    method = next(m for m in root.methods if m.signature.name == "Test")
    ret = method.block.statements[-1]
    assert isinstance(ret, frog_ast.ReturnStatement)
    return ret.expression


def _field(root: frog_ast.Game | frog_ast.Scheme, name: str) -> frog_ast.Field:
    return next(f for f in root.fields if f.name == name)


def test_f356_game_field_with_int_initializer_is_not_read_as_it() -> None:
    """`ModInt<q> f = q;` holds q mod q = 0, so `f + f == f` always holds;
    read as q it would be the integer q + q == q."""
    game = frog_parser.parse_game("""
        Game G(Int q) {
            ModInt<q> f = q;
            Bool Test() { return f + f == f; }
        }
        """)
    out = instantiate(game, [_q()], {"q": None})
    assert _test_return(out) == frog_parser.parse_expression("f + f == f")
    assert _field(out, "f").value == _q()


def test_f356_game_field_with_initializer_of_its_type_is_read_as_it() -> None:
    game = frog_parser.parse_game("""
        Game G(Int q, ModInt<q> x) {
            ModInt<q> f = x;
            Bool Test() { return f + f == f; }
        }
        """)
    out = instantiate(
        game,
        [_q(), frog_ast.Variable("y")],
        {"q": None, "y": None},
        arg_types=[frog_ast.IntType(), frog_ast.ModIntType(_q())],
    )
    assert _test_return(out) == frog_parser.parse_expression("y + y == y")


def test_f356_game_field_with_literal_zero_is_read_as_it() -> None:
    """A field that holds no ``ModInt`` is still read as a literal
    initializer. A ``ModInt`` field is not (the next test)."""
    game = frog_parser.parse_game("""
        Game G(Int q) {
            Int f = 0;
            Bool Test() { return f + f == f; }
        }
        """)
    out = instantiate(game, [_q()], {"q": None})
    assert _test_return(out) == frog_parser.parse_expression("0 + 0 == 0")


@pytest.mark.parametrize(
    "field_type, literal",
    [("ModInt<q>", "0"), ("ModInt<2>", "1"), ("ModInt<5>", "3"), ("ModInt<q>?", "0")],
)
def test_f356_game_field_with_int_literal_is_not_read_as_it(
    field_type: str, literal: str
) -> None:
    """The literal is an ``Int``: read in place of the field, ``f + f`` would
    no longer be taken modulo the modulus, so the field stays a field."""
    game = frog_parser.parse_game(f"""
        Game G(Int q) {{
            {field_type} f = {literal};
            Bool Test() {{ return f + f == f; }}
        }}
        """)
    out = instantiate(game, [_q()], {"q": None})
    assert _test_return(out) == frog_parser.parse_expression("f + f == f")
    assert _field(out, "f").value == frog_parser.parse_expression(literal)


def test_f356_int_field_is_still_read_as_its_initializer() -> None:
    game = frog_parser.parse_game("""
        Game G(Int q) {
            Int n = q;
            Int Test() { return n + 1; }
        }
        """)
    out = instantiate(game, [_q()], {"q": None})
    assert _test_return(out) == frog_parser.parse_expression("q + 1")


def test_f356_tuple_field_with_int_component_is_not_read_as_it() -> None:
    """The first component lands in a ModInt<q> slot and is reduced."""
    game = frog_parser.parse_game("""
        Game G(Int q) {
            [ModInt<q>, Int] t = [q, q];
            Bool Test() { return t[0] + t[0] == t[0]; }
        }
        """)
    out = instantiate(game, [_q()], {"q": None})
    assert _test_return(out) == frog_parser.parse_expression("t[0] + t[0] == t[0]")


def test_f356_field_of_a_set_parameter_resolving_to_mod_int() -> None:
    """The field's type S is only known to be ModInt<q> once instantiated."""
    game = frog_parser.parse_game("""
        Game G(Set S, Int q) {
            S f = q;
            Bool Test() { return f + f == f; }
        }
        """)
    mod_q = frog_ast.ModIntType(_q())
    out = instantiate(game, [frog_ast.Variable("T"), _q()], {"T": mod_q, "q": None})
    assert _field(out, "f").type == mod_q
    assert _test_return(out) == frog_parser.parse_expression("f + f == f")


def test_f356_field_of_a_set_parameter_typed_initializer_is_read_as_it() -> None:
    game = frog_parser.parse_game("""
        Game G(Set S, S x) {
            S f = x;
            Bool Test() { return f + f == f; }
        }
        """)
    mod_q = frog_ast.ModIntType(_q())
    out = instantiate(
        game,
        [frog_ast.Variable("T"), frog_ast.Variable("y")],
        {"T": mod_q, "y": None},
        arg_types=[None, frog_ast.Variable("T")],
    )
    assert _test_return(out) == frog_parser.parse_expression("y + y == y")


def test_f356_unknown_initializer_type_is_not_read_as_it() -> None:
    """Without the initializer types instantiate supplies, a ModInt field's
    initializer type is unknown, so it is not substituted (fail closed)."""
    game = frog_parser.parse_game("""
        Game G() {
            ModInt<q> f = x;
            Bool Test() { return f + f == f; }
        }
        """)
    out = visitors.InstantiationTransformer({}).transform(game)
    assert _test_return(out) == frog_parser.parse_expression("f + f == f")


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text)
    return str(path)


_PRIM = "Primitive P(Int q) {\n    Bool Test();\n}\n"


def _scheme(tmp_path: Path, params: str, field: str) -> frog_ast.Scheme:
    _write(tmp_path, "P.primitive", _PRIM)
    scheme = frog_parser.parse_file(
        _write(
            tmp_path,
            "S.scheme",
            "import 'P.primitive';\n"
            f"Scheme S({params}) extends P {{\n"
            f"    {field}\n"
            "    Bool Test() { return f + f == f; }\n"
            "}\n",
        )
    )
    assert isinstance(scheme, frog_ast.Scheme)
    return scheme


def test_f356_scheme_field_with_int_initializer_is_refused(tmp_path: Path) -> None:
    scheme = _scheme(tmp_path, "Int q", "ModInt<q> f = q;")
    with pytest.raises(visitors.ConvertingFieldInitializerError, match="'f'"):
        instantiate(scheme, [_q()], {"q": None})


@pytest.mark.parametrize(
    "field", ["ModInt<q> f = 0;", "ModInt<2> f = 1;", "ModInt<5> f = 3;"]
)
def test_f356_scheme_field_with_int_literal_is_refused(
    tmp_path: Path, field: str
) -> None:
    scheme = _scheme(tmp_path, "Int q", field)
    with pytest.raises(visitors.ConvertingFieldInitializerError, match="'f'"):
        instantiate(scheme, [_q()], {"q": None})


def test_f356_scheme_field_with_initializer_of_its_type_is_read_as_it(
    tmp_path: Path,
) -> None:
    scheme = _scheme(tmp_path, "Int q, ModInt<q> x", "ModInt<q> f = x;")
    out = instantiate(
        scheme,
        [_q(), frog_ast.Variable("y")],
        {"q": None, "y": None},
        arg_types=[frog_ast.IntType(), frog_ast.ModIntType(_q())],
    )
    assert _test_return(out) == frog_parser.parse_expression("y + y == y")


def _scheme_with_fields(*fields: frog_ast.Field) -> frog_ast.Scheme:
    scheme = frog_parser.parse_scheme_file(
        "Scheme S() extends P {\n    Bool Test() { return true; }\n}\n"
    )
    scheme.fields = list(fields)
    return scheme


def test_f356_scheme_field_access_with_int_initializer_is_kept() -> None:
    """`S.f` for a scheme field `ModInt<q> f = q;` holds q mod q, not q, and
    `S.z` for `ModInt<q> z = 0;` is not the Int 0."""
    scheme = _scheme_with_fields(
        frog_ast.Field(frog_ast.ModIntType(_q()), "f", _q()),
        frog_ast.Field(frog_ast.IntType(), "n", _q()),
        frog_ast.Field(frog_ast.ModIntType(_q()), "z", frog_ast.Integer(0)),
    )
    transformer = visitors.InstantiationTransformer({"S": scheme})
    access = frog_parser.parse_expression("S.f")
    assert transformer.transform(access) == access
    assert transformer.transform(frog_parser.parse_expression("S.n")) == _q()
    zero_access = frog_parser.parse_expression("S.z")
    assert transformer.transform(zero_access) == zero_access


@pytest.mark.parametrize(
    "target, value, value_type, keeps",
    [
        ("ModInt<q>", "0", "Int", False),
        ("ModInt<2>", "1", "Int", False),
        ("ModInt<q>", "x", "ModInt<q>", True),
        ("ModInt<q>", "x", None, False),
        ("ModInt<q>?", "None", None, True),
        ("Int", "0", "Int", True),
        ("[ModInt<q>, Int]", "[0, 0]", "[Int, Int]", False),
    ],
)
def test_f356_store_keeps_value_of_type_requires_the_slot_type(
    target: str, value: str, value_type: str | None, keeps: bool
) -> None:
    """The rule instantiation applies: a ``ModInt`` part of the slot keeps
    its value only from a value of a ``ModInt`` type, never from an Int,
    literal or not."""

    def parse_type(src: str) -> frog_ast.Type:
        game = frog_parser.parse_game(
            f"Game T() {{ {src} slot; Void Initialize() {{ }} }}"
        )
        return game.fields[0].type

    result = visitors.store_keeps_value_of_type(
        parse_type(target),
        frog_parser.parse_expression(value),
        lambda: None if value_type is None else parse_type(value_type),
    )
    assert result is keeps
