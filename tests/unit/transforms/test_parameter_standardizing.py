"""Tests for StandardizeParameters / _ParameterStandardizer.

Oracle/method parameter names are not adversary-observable (FrogLang calls
are positional), so canonicalization normalizes them to arg1..argN. Two games
identical up to a parameter name must then produce identical canonical forms.
This closes a real soundness-adjacent gap: before the pass, renaming an oracle
parameter (e.g. Decaps(c) -> Decaps(ct)) changed a game's canonical form and
could reject an otherwise-valid interchangeability hop.
"""

from proof_frog import frog_parser
from proof_frog.transforms.standardization import _ParameterStandardizer


def test_params_renamed_positionally() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Bool Oracle(BitString<n> foo, BitString<n> bar) {
                return foo == bar;
            }
        }
        """
    )
    out = _ParameterStandardizer().rename_game(game)
    sig = out.methods[0].signature
    assert [p.name for p in sig.parameters] == ["arg1", "arg2"]
    # Body references follow the rename.
    assert str(out.methods[0].block).replace(" ", "").find("arg1==arg2") != -1


def test_two_games_differing_only_in_param_name_become_identical() -> None:
    a = frog_parser.parse_game(
        """
        Game G() {
            Bool Oracle(BitString<n> c) { return c == c; }
        }
        """
    )
    b = frog_parser.parse_game(
        """
        Game G() {
            Bool Oracle(BitString<n> ct) { return ct == ct; }
        }
        """
    )
    std = _ParameterStandardizer()
    assert std.rename_game(a) == std.rename_game(b)


def test_local_shadowing_param_is_not_renamed() -> None:
    # A typed local `x` shadows the parameter `x` from its declaration point.
    # References before the declaration resolve to the parameter (-> arg1);
    # references at/after resolve to the local (left untouched).
    game = frog_parser.parse_game(
        """
        Game G() {
            BitString<n> Oracle(BitString<n> x) {
                BitString<n> y = x;
                BitString<n> x = foo();
                return x + y;
            }
        }
        """
    )
    out = _ParameterStandardizer().rename_game(game)
    body = str(out.methods[0].block)
    # The pre-declaration read of the parameter became arg1...
    assert "= arg1" in body
    # ...and the post-declaration local `x` was NOT renamed to arg1.
    assert "BitString<n> x = foo()" in body
    assert "arg1 + y" not in body


def test_loop_binder_shadowing_param_is_masked() -> None:
    # A generic-for binder with the same name as a parameter masks it in the
    # loop body; the loop-body reference must stay the binder, not become argN.
    game = frog_parser.parse_game(
        """
        Game G() {
            Bool Oracle(Set q) {
                for (Int q in q) {
                    return q == q;
                }
                return false;
            }
        }
        """
    )
    out = _ParameterStandardizer().rename_game(game)
    body = str(out.methods[0].block)
    # The loop iterates over the parameter (arg1) but the body's `q` is the
    # binder, unchanged.
    assert "in arg1" in body
    assert "q == q" in body


def test_pass_is_idempotent() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Bool Oracle(BitString<n> foo, BitString<n> bar) { return foo == bar; }
        }
        """
    )
    std = _ParameterStandardizer()
    once = std.rename_game(game)
    twice = std.rename_game(once)
    assert once == twice


def test_no_params_is_noop() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            BitString<n> Oracle() {
                BitString<n> r <- BitString<n>;
                return r;
            }
        }
        """
    )
    out = _ParameterStandardizer().rename_game(game)
    assert out == game
