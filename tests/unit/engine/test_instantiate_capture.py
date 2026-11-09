"""F-341: instantiation must be capture-avoiding.

``proof_engine.instantiate`` replaces a game's / scheme's parameters with the
instantiation arguments, then ``InstantiationTransformer`` replaces
namespace names and field aliases, all by name and across method bodies. A
method parameter, typed local or ``for`` binder that shares a name with one of
those (or with a free name of an argument) used to be rewritten or to capture
the substituted name, and a game field could capture an argument's name.
Each test's docstring gives the distinguisher the capture would hide.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proof_frog import frog_ast, frog_parser, proof_engine, visitors
from proof_frog.proof_engine import InstantiationCaptureError, instantiate


def _lam() -> list[frog_ast.Expression]:
    return [frog_ast.Variable("lambda")]


def _oracle(game: frog_ast.Game, name: str = "O") -> frog_ast.Method:
    return next(m for m in game.methods if m.signature.name == name)


def _returned(method: frog_ast.Method) -> frog_ast.Expression:
    ret = method.block.statements[-1]
    assert isinstance(ret, frog_ast.ReturnStatement)
    return ret.expression


def test_f341_argument_not_captured_by_method_parameter() -> None:
    """`O(Int lambda) { return n; }` with n := lambda must still return the
    outer lambda, not its argument (else O(0), O(1) differ only on one side)."""
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int O(Int lambda) { return n; }
        }
        """)
    out = instantiate(game, _lam(), {})
    oracle = _oracle(out)
    assert oracle.signature.parameters[0].name != "lambda"
    assert _returned(oracle) == frog_ast.Variable("lambda")


def test_f341_parameter_shadowing_game_parameter_keeps_its_reads() -> None:
    """`O(Int n) { return n; }` echoes its argument; substituting the game
    parameter n := lambda must not turn it into a constant."""
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int O(Int n) { return n; }
        }
        """)
    oracle = _oracle(instantiate(game, _lam(), {}))
    param = oracle.signature.parameters[0].name
    assert _returned(oracle) == frog_ast.Variable(param)
    assert param != "lambda"


def test_f341_for_binder_and_typed_local_not_captured() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int O() {
                Int acc = n;
                for (Int lambda = 0 to 3) {
                    acc = acc + lambda;
                }
                Int lambda = 1;
                return acc + lambda + n;
            }
        }
        """)
    text = str(instantiate(game, _lam(), {}))
    # The substituted game parameter is the only `lambda` left.
    assert "Int acc = lambda;" in text
    assert "for (Int lambda" not in text
    assert "Int lambda = 1;" not in text
    assert text.count("lambda") == 2  # `acc = lambda` and the trailing `+ lambda`


def test_f341_game_field_not_capturing_argument() -> None:
    """A game field named `lambda` must not capture the argument `lambda`: O
    returns the let value, not the field's 5."""
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int lambda;
            Void Initialize() { lambda = 5; }
            Int O() { return n; }
        }
        """)
    out = instantiate(game, _lam(), {})
    assert "lambda" not in {f.name for f in out.fields}
    assert _returned(_oracle(out)) == frog_ast.Variable("lambda")
    init = _oracle(out, "Initialize")
    assert "lambda =" not in str(init)


def test_f341_no_collision_leaves_names_alone() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Int k;
            Int O(Int z) {
                Int t = z + n;
                return t;
            }
        }
        """)
    text = str(instantiate(game, _lam(), {}))
    assert "__i" not in text
    assert "Int O(Int z)" in text and "Int t = z + lambda;" in text


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text)
    return str(path)


_PRIM = "Primitive P() {\n    Int f(Int n);\n}\n"


def test_f341_scheme_field_alias_not_substituted_into_parameter(
    tmp_path: Path,
) -> None:
    """Scheme field `Int n = 5` must not replace the reads of a method
    parameter `n`: f echoes its argument."""
    _write(tmp_path, "P.primitive", _PRIM)
    scheme = frog_parser.parse_file(
        _write(
            tmp_path,
            "S.scheme",
            "import 'P.primitive';\n"
            "Scheme S() extends P {\n"
            "    Int n = 5;\n"
            "    Int f(Int n) { return n; }\n"
            "}\n",
        )
    )
    assert isinstance(scheme, frog_ast.Scheme)
    out = instantiate(scheme, [], {})
    f = out.methods[0]
    assert _returned(f) == frog_ast.Variable(f.signature.parameters[0].name)


def test_f341_scheme_field_capturing_argument_is_refused(tmp_path: Path) -> None:
    """A scheme field cannot be renamed (it is read as `S.lambda`), so a
    non-trivial collision with an argument name is refused."""
    _write(tmp_path, "P.primitive", _PRIM)
    scheme = frog_parser.parse_file(
        _write(
            tmp_path,
            "S.scheme",
            "import 'P.primitive';\n"
            "Scheme S(Int n) extends P {\n"
            "    Int lambda = 7;\n"
            "    Int f(Int m) { return n; }\n"
            "}\n",
        )
    )
    assert isinstance(scheme, frog_ast.Scheme)
    with pytest.raises(InstantiationCaptureError):
        instantiate(scheme, _lam(), {})


def test_f341_scheme_field_reexporting_argument_is_allowed(tmp_path: Path) -> None:
    """The common `Int lambda = lambda;` pattern, instantiated with `lambda`,
    is a self-alias and stays allowed."""
    _write(tmp_path, "P.primitive", _PRIM)
    scheme = frog_parser.parse_file(
        _write(
            tmp_path,
            "S.scheme",
            "import 'P.primitive';\n"
            "Scheme S(Int lambda) extends P {\n"
            "    Int lambda = lambda;\n"
            "    Int f(Int m) { return m + lambda; }\n"
            "}\n",
        )
    )
    assert isinstance(scheme, frog_ast.Scheme)
    out = instantiate(scheme, _lam(), {})
    assert "return m + lambda;" in str(out)


# F-361: a game field named like a namespace (proof ``let:``) name. The
# engine resolves proof steps with ``rename_namespace_fields=True``.


_SHADOWING_GAME = """
    Game G(Int n) {
        Int t;
        Void Put(Int v) { t = v; }
        Int O() { return t + n; }
    }
    """


def test_f361_game_field_named_like_namespace_name_is_renamed() -> None:
    """Field `t` and a `let:` `t` the game is not passed must stay apart:
    otherwise later passes read the field with the let's type, and inlined
    scheme code reading the let `t` would read the field."""
    game = frog_parser.parse_game(_SHADOWING_GAME)
    out = instantiate(game, _lam(), {"t": None}, rename_namespace_fields=True)
    (field,) = out.fields
    assert field.name != "t" and field.name.startswith("__i")
    assert _returned(_oracle(out)) == frog_parser.parse_expression(
        f"{field.name} + lambda"
    )
    assert f"{field.name} = v;" in str(_oracle(out, "Put"))
    assert "t" not in visitors.referenced_variable_names(out)


def test_f361_namespace_rename_is_opt_in() -> None:
    """The type checker instantiates without the flag and keeps the name."""
    game = frog_parser.parse_game(_SHADOWING_GAME)
    out = instantiate(game, _lam(), {"t": None})
    assert [field.name for field in out.fields] == ["t"]


def test_f361_set_alias_field_named_like_namespace_name_is_kept() -> None:
    """A `Set` alias field is substituted into every use, so nothing is left
    to collide; renaming it would leave its type-position uses dangling."""
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Set K = BitString<n>;
            K O(K x) { return x; }
        }
        """)
    out = instantiate(game, _lam(), {"K": None}, rename_namespace_fields=True)
    assert [field.name for field in out.fields] == ["K"]
    assert "BitString<lambda> O(BitString<lambda>" in str(out)


def test_f361_renamed_field_initializers_keep_outer_references() -> None:
    """A field's own initializer and the earlier ones are evaluated before
    the field is bound, so their `t` is the parameter; later initializers
    and the methods read the renamed field."""
    game = frog_parser.parse_game("""
        Game G(Int t) {
            Int a = t;
            Int t = t;
            Int b = t;
            Int O() { return a + t + b; }
        }
        """)
    out = instantiate(game, _lam(), {"t": None}, rename_namespace_fields=True)
    names = [field.name for field in out.fields]
    assert names[0] == "a" and names[2] == "b" and names[1].startswith("__i")
    # Every initializer, and so every read, comes out as the argument.
    assert [str(field.value) for field in out.fields] == ["lambda"] * 3
    assert _returned(_oracle(out)) == frog_parser.parse_expression(
        "lambda + lambda + lambda"
    )


def test_f361_instantiated_field_names_matches_instantiate() -> None:
    """Step assumptions name a field as written; the lookup must give the
    name `instantiate` gives it."""
    game = frog_parser.parse_game(_SHADOWING_GAME)
    names = proof_engine.instantiated_field_names(game, _lam(), {"t": None})
    out = instantiate(game, _lam(), {"t": None}, rename_namespace_fields=True)
    assert names == {"t": out.fields[0].name}
    assert not proof_engine.instantiated_field_names(game, _lam(), {})
