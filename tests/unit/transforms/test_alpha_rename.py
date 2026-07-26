"""Unit tests for the AlphaRename pass.

AlphaRename gives every typed local binder a fresh ``__aN__`` name under
position-sensitive block scoping, leaving fields, parameters, and proof-level
names untouched.  These tests pin the scope invariants directly on the AST.
"""

from __future__ import annotations

from proof_frog import frog_parser
from proof_frog.transforms.alpha_rename import AlphaRename
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(AlphaRename().apply(game, _ctx()))


def test_position_sensitive_use_before_decl_binds_outer() -> None:
    # `Int out = x;` reads the FIELD x (the local x is declared on the next
    # line); only uses from the declaration point onward bind to the local.
    out = _apply("""
        Game G() {
            Int x;
            Int O() {
                Int out = x;
                Int x = 0;
                return out + x;
            }
        }
        """)
    # The field read `x` survives verbatim on the RHS of the first decl ...
    assert "= x;" in out
    # ... and the shadowing local + its later use are renamed to a fresh name.
    assert "Int x = 0;" not in out
    assert "__a" in out


def test_fields_and_parameters_are_not_renamed() -> None:
    out = _apply("""
        Game G() {
            Int counter;
            Int O(Int p) {
                Int local = p + counter;
                return local;
            }
        }
        """)
    assert "counter" in out  # field untouched
    assert "Int O(Int p)" in out  # parameter untouched
    assert "Int p + counter" in out or "p + counter" in out  # param/field reads
    assert "Int local" not in out  # local renamed


def test_nested_block_local_distinct_from_outer() -> None:
    # An if-body local `y` that shadows an outer local `y` must get a distinct
    # fresh name, so a later splice cannot capture the outer `return y`.
    out = _apply("""
        Game G() {
            BitString<8> O() {
                BitString<8> y = 0^8;
                if (true) {
                    BitString<8> y <- BitString<8>;
                }
                return y;
            }
        }
        """)
    # Two distinct fresh names must appear (outer y and inner y differ).
    import re  # pylint: disable=import-outside-toplevel

    names = set(re.findall(r"__a\d+__", out))
    assert len(names) >= 2


def test_idempotent() -> None:
    src = """
        Game G() {
            Int x;
            Int O() {
                Int a = x;
                Int b = a + 1;
                return b;
            }
        }
        """
    once = _apply(src)
    twice = str(AlphaRename().apply(frog_parser.parse_game(once), _ctx()))
    assert once == twice


def test_f237_underscore_prefixed_user_binder_is_renamed() -> None:
    # A user local named `__x` must be renamed to a fresh `__aN__` name -- the
    # old code skipped every `__`-prefixed binder, leaving the capture that
    # AlphaRename exists to prevent (audit F-237/F-290/F-323). Only the
    # engine's own `__aN__` names are exempt (for convergence).
    out = _apply("""
        Game G() {
            Int __x;
            Int O() {
                Int __x = 5;
                return __x;
            }
        }
        """)
    # The local `__x = 5` and its return are freshened; no `__x` binder/read
    # survives in O to be captured.
    assert "Int __a0__ = 5" in out
    assert "return __a0__" in out


def test_f238_f239_sampled_from_and_type_follow_shadowed_local() -> None:
    # A local `n` shadows the field `n`; the local's own draw and type
    # annotation reference `n`. After renaming the local to a fresh name, the
    # exclusion set (already handled), the sampled_from domain type (F-238),
    # and the `the_type` annotation (F-239) must ALL bind to the fresh name --
    # not silently re-bind to the field `n`.
    out = _apply("""
        Game G(Int lambda) {
            Int n;
            Void Initialize() { n = 2; }
            Bool O() {
                Int n = 1;
                BitString<n> x <- BitString<n> \\ {1^n};
                return x == 0^n;
            }
        }
        """)
    # Grab O's body (after Initialize). The renamed local drives everything.
    body = out.split("Bool O()", 1)[1]
    # The local `n` is renamed; no bare `<n>` (field re-bind) remains in O.
    assert "BitString<n>" not in body
    # The type annotation, sampled_from, and exclusion all use the fresh name.
    assert "BitString<__a" in body
