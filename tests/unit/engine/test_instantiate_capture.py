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

from proof_frog import frog_ast, frog_parser
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
