"""Unit tests for the AlphaRename pass.

AlphaRename gives every typed local binder a fresh ``__aN__`` name under
position-sensitive block scoping, leaving fields, parameters, and proof-level
names untouched.  These tests pin the scope invariants directly on the AST.
"""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser
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


# ---------------------------------------------------------------------------
# F-339: parameters and loop binders that collide with an OUTER name (field,
# game parameter, proof let / namespace name) are renamed, so no later pass
# that resolves names by field/let membership can capture them.
# ---------------------------------------------------------------------------


def test_f339_parameter_colliding_with_field_is_renamed() -> None:
    """`O(Int x)` with a field `x`: the parameter and its body reads get a
    fresh name; the field and Initialize's reads of it are untouched."""
    out = _apply("""
        Game G() {
            Int x;
            Void Initialize() { x = 1; }
            Int O(Int x) {
                x = x + 1;
                return x;
            }
        }
        """)
    assert "Int O(Int x)" not in out
    assert "Int O(Int __a" in out
    assert "x = 1;" in out  # Initialize still writes the field
    assert "return x;" not in out  # body read follows the renamed parameter


def test_f339_parameter_colliding_with_let_is_renamed() -> None:
    ctx = _ctx()
    ctx.proof_let_types.set("k", frog_ast.IntType())
    game = frog_parser.parse_game("""
        Game G() {
            Int O(Int k) { return k; }
        }
        """)
    out = str(AlphaRename().apply(game, ctx))
    assert "Int O(Int k)" not in out
    assert "return k;" not in out


def test_f339_non_colliding_parameter_unchanged() -> None:
    out = _apply("""
        Game G() {
            Int x;
            Int O(Int z) { return z + x; }
        }
        """)
    assert "Int O(Int z)" in out
    assert "z + x" in out


def test_f339_for_binder_colliding_with_field_is_renamed() -> None:
    """A `for` binder named like a field is renamed (the F-173 shape);
    the field read after the loop is untouched."""
    out = _apply("""
        Game G() {
            Int k;
            Int O() {
                Int acc = 0;
                for (Int k = 0 to 3) {
                    acc = acc + k;
                }
                return acc + k;
            }
        }
        """)
    assert "for (Int k " not in out
    assert "+ k;" in out  # the trailing field read survives


def test_f339_generic_for_binder_colliding_with_field_is_renamed() -> None:
    out = _apply("""
        Game G() {
            Int k;
            Set<Int> S;
            Int O() {
                Int acc = 0;
                for (Int k in S) {
                    acc = acc + k;
                }
                return acc + k;
            }
        }
        """)
    assert "for (Int k in" not in out
    assert "+ k;" in out


def test_f339_signature_types_keep_outer_name_when_parameter_renamed() -> None:
    """The typechecker forbids a signature's types from naming the method's own
    parameters (F-340), so a name there is an outer one, e.g. a game parameter
    instantiation substituted in. The clashing parameter is renamed; the
    signature's types keep referring to the outer name."""
    out = _apply("""
        Game G(Int n) {
            BitString<n> O(Int n, BitString<n> m) { return m; }
        }
        """)
    assert "BitString<n> O(Int __a" in out
    assert ", BitString<n> m)" in out


def test_f339_collision_renaming_is_idempotent() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Int x;
            Int O(Int x) {
                for (Int x = 0 to 2) { }
                return x;
            }
        }
        """)
    once = AlphaRename().apply(game, _ctx())
    twice = AlphaRename().apply(once, _ctx())
    assert once == twice


def test_fresh_looking_local_colliding_with_field_is_renamed() -> None:
    """A ``__aN__`` binder keeps its name so the pass converges, unless it
    shadows an outer name. Kept, the shadow can be reordered above the field
    read and conflate the two bindings."""
    game = frog_parser.parse_game("""
        Game G() {
            Int __a5__;
            Int O() {
                Int out = __a5__;
                Int __a5__;
                __a5__ = 0;
                return out + __a5__;
            }
        }
        """)
    once = AlphaRename().apply(game, _ctx())
    read_field, declaration, write, ret = once.methods[0].block.statements
    assert isinstance(declaration, frog_ast.VariableDeclaration)
    assert declaration.name != "__a5__"
    assert isinstance(read_field, frog_ast.Assignment)
    assert read_field.value == frog_ast.Variable("__a5__")
    assert isinstance(write, frog_ast.Assignment)
    assert write.var == frog_ast.Variable(declaration.name)
    assert declaration.name in str(ret)
    assert "__a5__" not in str(ret)
    assert AlphaRename().apply(once, _ctx()) == once


def test_fresh_looking_binders_colliding_with_let_names_are_renamed() -> None:
    """A typed local and a loop binder that collide with proof-let names are
    renamed, and the minted names skip the let names too."""
    ctx = PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={
            name: frog_ast.Variable(name) for name in ("__a5__", "__a6__", "__a7__")
        },
        subsets_pairs=[],
    )
    game = frog_parser.parse_game("""
        Game G() {
            Int O() {
                Int __a5__ = 1;
                for (Int __a6__ = 0 to 2) {
                    __a5__ = __a5__ + __a6__;
                }
                return __a5__;
            }
        }
        """)
    once = AlphaRename().apply(game, ctx)
    for name in ("__a5__", "__a6__", "__a7__"):
        assert name not in str(once)
    assert AlphaRename().apply(once, ctx) == once
