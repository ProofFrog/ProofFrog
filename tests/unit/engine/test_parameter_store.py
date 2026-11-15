"""F-374: a parameter receives its argument like a store.

The type checker accepts an ``Int`` argument for a ``ModInt<q>`` parameter,
and the parameter then holds the ``Int`` reduced modulo ``q``.
``proof_engine.instantiate`` used to substitute every argument for its
parameter, so ``Game Left(Int q, ModInt<q> x) { Bool Test() { return x + x
== x; } }`` instantiated with ``(q, q)`` became the integer comparison
``q + q == q``. Now a parameter whose argument the store would convert (its
type holds a ``ModInt`` and the argument's type, where the argument is
written, does not match it there, or is unknown) is not substituted: a game
or reduction parameter becomes a game field initialized with the argument,
and a scheme or primitive parameter is refused, since the scheme's methods
would carry the parameter's name into the games they are inlined into.

Also here: instantiation now sets up a reduction the way it sets up a game,
so a reduction field its methods write is not read as its initializer.
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.proof_engine import ConvertingParameterError, instantiate


def _q() -> frog_ast.Variable:
    return frog_ast.Variable("q")


def _mod_q() -> frog_ast.ModIntType:
    return frog_ast.ModIntType(_q())


def _test_return(root: frog_ast.Game | frog_ast.Scheme) -> frog_ast.Expression:
    method = next(m for m in root.methods if m.signature.name == "Test")
    ret = method.block.statements[-1]
    assert isinstance(ret, frog_ast.ReturnStatement)
    return ret.expression


_LEFT = """
    Game Left(Int q, ModInt<q> x) {
        Bool Test() { return x + x == x; }
    }
    """


def test_f374_game_parameter_given_an_int_is_bound_as_a_field() -> None:
    """``x`` holds q mod q = 0, so ``x + x == x`` always holds; substituted
    it was the integer comparison ``q + q == q``."""
    out = instantiate(
        frog_parser.parse_game(_LEFT),
        [_q(), _q()],
        {"q": None},
        arg_types=[frog_ast.IntType(), frog_ast.IntType()],
    )
    assert _test_return(out) == frog_parser.parse_expression("x + x == x")
    assert [(str(f.type), f.name, str(f.value)) for f in out.fields] == [
        ("ModInt<q>", "x", "q")
    ]
    assert not out.parameters


def test_f374_game_parameter_given_an_int_literal_is_bound_as_a_field() -> None:
    """A literal the modulus represents as itself is still an Int."""
    game = frog_parser.parse_game("""
        Game Left(ModInt<2> x) {
            Bool Test() { return x + x == x - x; }
        }
        """)
    out = instantiate(game, [frog_ast.Integer(1)], {}, arg_types=[frog_ast.IntType()])
    assert _test_return(out) == frog_parser.parse_expression("x + x == x - x")
    assert out.fields[0].value == frog_ast.Integer(1)


def test_f374_game_parameter_given_its_own_type_is_substituted() -> None:
    out = instantiate(
        frog_parser.parse_game(_LEFT),
        [_q(), frog_ast.Variable("y")],
        {"q": None, "y": None},
        arg_types=[frog_ast.IntType(), _mod_q()],
    )
    assert _test_return(out) == frog_parser.parse_expression("y + y == y")
    assert not out.fields


def test_f374_game_parameter_of_unknown_argument_type_is_bound() -> None:
    """Fail closed: without the argument's type the store may convert."""
    out = instantiate(
        frog_parser.parse_game(_LEFT),
        [_q(), frog_ast.Variable("y")],
        {"q": None, "y": None},
    )
    assert _test_return(out) == frog_parser.parse_expression("x + x == x")
    assert out.fields[0].value == frog_ast.Variable("y")


def test_f374_int_parameter_is_still_substituted() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int Test() { return n + 1; }
        }
        """)
    out = instantiate(game, [_q()], {"q": None})
    assert _test_return(out) == frog_parser.parse_expression("q + 1")


def test_f374_bound_parameter_named_like_an_argument_is_renamed() -> None:
    """Instantiated with ``(x, x)``, the first parameter's ``x`` (the
    caller's Int) and the bound second parameter must stay apart."""
    out = instantiate(
        frog_parser.parse_game("""
            Game G(Int q, ModInt<q> x) {
                Bool Test() { return x == q; }
            }
            """),
        [frog_ast.Variable("x"), frog_ast.Variable("x")],
        {"x": None},
        arg_types=[frog_ast.IntType(), frog_ast.IntType()],
    )
    (bound,) = out.fields
    assert bound.name != "x"
    assert bound.value == frog_ast.Variable("x")
    assert bound.type == frog_ast.ModIntType(frog_ast.Variable("x"))
    assert _test_return(out) == frog_parser.parse_expression(f"{bound.name} == x")


def test_f374_bound_parameter_is_read_by_a_field_initializer() -> None:
    """A field initialized from the bound parameter has its type, so it is
    read as the bound parameter's field."""
    game = frog_parser.parse_game("""
        Game G(Int q, ModInt<q> x) {
            ModInt<q> f = x;
            Bool Test() { return f + f == f; }
        }
        """)
    out = instantiate(
        game, [_q(), _q()], {"q": None}, arg_types=[frog_ast.IntType()] * 2
    )
    assert [f.name for f in out.fields] == ["x", "f"]
    assert _test_return(out) == frog_parser.parse_expression("x + x == x")


@pytest.mark.parametrize(
    "param_type, arg_type, bound",
    [
        ("[ModInt<q>, Int]", "[Int, Int]", True),
        ("[ModInt<q>, Int]", "[ModInt<q>, Int]", False),
        ("Set<ModInt<q>>", "Set<Int>", True),
        ("Map<Int, ModInt<q>>", "Map<Int, ModInt<q>>", False),
        ("Function<Int, ModInt<q>>", "Function<Int, ModInt<q>>", False),
        ("Function<Int, ModInt<q>>", "Function<Int, Int>", True),
        ("ModInt<q>?", "ModInt<q>", False),
    ],
)
def test_f374_compound_parameter_types(
    param_type: str, arg_type: str, bound: bool
) -> None:
    game = frog_parser.parse_game(f"""
        Game G(Int q, {param_type} x) {{
            Bool Test() {{ return x == x; }}
        }}
        """)
    the_arg_type = (
        frog_parser.parse_game(
            f"Game T(Int q) {{ {arg_type} slot; Void Initialize() {{ }} }}"
        )
        .fields[0]
        .type
    )
    out = instantiate(
        game,
        [_q(), frog_ast.Variable("y")],
        {"q": None, "y": None},
        arg_types=[frog_ast.IntType(), the_arg_type],
    )
    expected = "x == x" if bound else "y == y"
    assert _test_return(out) == frog_parser.parse_expression(expected)
    assert bool(out.fields) is bound


def test_f374_set_parameter_resolving_to_mod_int() -> None:
    """``x``'s type ``S`` is only known to be ``ModInt<q>`` once the
    arguments replace the parameters."""
    game = frog_parser.parse_game("""
        Game G(Set S, S x) {
            Bool Test() { return x + x == x; }
        }
        """)
    out = instantiate(
        game,
        [_mod_q(), _q()],
        {"q": None},
        arg_types=[None, frog_ast.IntType()],
    )
    assert _test_return(out) == frog_parser.parse_expression("x + x == x")
    assert out.fields[0].type == _mod_q()


def test_f374_reduction_parameter_given_an_int_is_bound_as_a_field() -> None:
    reduction = frog_parser.parse_reduction("""
        Reduction R(Int q, ModInt<q> x) compose P(q) against Q(q).Adversary {
            Bool Test() { return x + x == x; }
        }
        """)
    out = instantiate(
        reduction, [_q(), _q()], {"q": None}, arg_types=[frog_ast.IntType()] * 2
    )
    assert isinstance(out, frog_ast.Reduction)
    assert _test_return(out) == frog_parser.parse_expression("x + x == x")
    assert out.fields[0].name == "x"


def _scheme(params: str) -> frog_ast.Scheme:
    return frog_parser.parse_scheme_file(
        f"Scheme S({params}) extends P {{\n"
        "    Bool Test() { return x + x == x; }\n"
        "}\n"
    )


def test_f374_scheme_parameter_given_an_int_is_refused() -> None:
    with pytest.raises(ConvertingParameterError, match="'x'"):
        instantiate(
            _scheme("Int q, ModInt<q> x"),
            [_q(), _q()],
            {"q": None},
            arg_types=[frog_ast.IntType()] * 2,
        )


def test_f374_scheme_parameter_of_unknown_argument_type_is_refused() -> None:
    with pytest.raises(ConvertingParameterError, match="'x'"):
        instantiate(_scheme("Int q, ModInt<q> x"), [_q(), _q()], {"q": None})


def test_f374_scheme_parameter_given_its_own_type_is_substituted() -> None:
    out = instantiate(
        _scheme("Int q, ModInt<q> x"),
        [_q(), frog_ast.Variable("y")],
        {"q": None, "y": None},
        arg_types=[frog_ast.IntType(), _mod_q()],
    )
    assert _test_return(out) == frog_parser.parse_expression("y + y == y")


def test_f374_primitive_parameter_given_an_int_is_refused() -> None:
    primitive = frog_parser.parse_primitive_file(
        "Primitive P(Int q, ModInt<q> x) {\n    ModInt<q> f = x;\n}\n"
    )
    with pytest.raises(ConvertingParameterError, match="'x'"):
        instantiate(
            primitive, [_q(), _q()], {"q": None}, arg_types=[frog_ast.IntType()] * 2
        )


def _counter_reduction() -> frog_ast.Reduction:
    return frog_parser.parse_reduction("""
        Reduction R() compose P() against Q().Adversary {
            Int c = 0;
            Int Next() {
                c = c + 1;
                return challenger.Echo(c);
            }
        }
        """)


def test_reduction_written_field_is_not_read_as_its_initializer() -> None:
    """A reduction field its method writes is state, as in a game (F-045);
    it used to come out of instantiation as ``0 = 0 + 1;``."""
    reduction = _counter_reduction()
    out = instantiate(reduction, [], {})
    assert out.methods[0].block == reduction.methods[0].block


def test_reduction_constant_field_is_read_as_its_initializer() -> None:
    reduction = frog_parser.parse_reduction("""
        Reduction R() compose P() against Q().Adversary {
            Int c = 7;
            Int Next() {
                return challenger.Echo(c);
            }
        }
        """)
    out = instantiate(reduction, [], {})
    ret = out.methods[0].block.statements[0]
    assert isinstance(ret, frog_ast.ReturnStatement)
    assert ret.expression == frog_parser.parse_expression("challenger.Echo(7)")
