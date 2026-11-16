"""Pass-level tests for ``standardize_field_names`` (F-337 / issue #252).

The pass renames game fields to canonical ``fieldN`` names.  It used to do so
with a name-keyed ``SubstitutionTransformer``, which -- because
``frog_ast.Variable`` is both an ``Expression`` and a ``Type`` -- also rewrote
occurrences of a same-named *type*.  These tests pin the two directions of the
hazard plus a positive firing probe.
"""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.standardization import (
    FieldLexMinByRHS,
    _apply_field_rename,
    standardize_field_names,
)
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def test_positive_firing_probe_renames_fields_in_first_read_order() -> None:
    """The pass must still do its job: fields get canonical ``fieldN`` names in
    first-read order across the oracle methods."""
    game = frog_parser.parse_game("""
        Game G() {
          Int alpha;
          Int beta;
          Void Initialize() {
            alpha = 1;
            beta = 2;
          }
          Int Oracle() {
            return beta + alpha;
          }
        }
        """)
    result = standardize_field_names(game)
    assert sorted(f.name for f in result.fields) == ["field1", "field2"]
    # ``beta`` is read first, so it becomes field1.
    assert "return field1 + field2;" in str(result)


def test_f337_same_named_type_survives_the_field_rename() -> None:
    """A field named ``KA`` whose declared type is a same-named set: the field
    name is standardized, the TYPE ``KA`` is left alone."""
    game = frog_parser.parse_game("""
        Game G() {
          KA KA;
          KA Get() {
            return KA;
          }
        }
        """)
    result = standardize_field_names(game)
    assert [f.name for f in result.fields] == ["field1"]
    assert str(result.fields[0].type) == "KA"
    assert str(result.methods[0].signature.return_type) == "KA"
    assert "return field1;" in str(result)


def test_f337_sampling_domain_is_not_captured_by_the_field_rename() -> None:
    """``KA <- KA`` is "sample the field KA from the set KA".  The rename may
    only touch the target, never the sampling domain."""
    game = frog_parser.parse_game("""
        Game G() {
          KA KA;
          Void Initialize() {
            KA <- KA;
          }
          Bool Get() {
            KA y <- KA;
            return y == KA;
          }
        }
        """)
    result = standardize_field_names(game)
    text = str(result)
    assert "field1 <- KA;" in text
    assert "KA y <- KA;" in text
    assert "field1 <- field1;" not in text


def test_f337_declines_when_target_name_collides_with_a_type_name() -> None:
    """Minting ``field1`` where ``field1`` already names an in-scope set would
    fuse the field with that set.  Standardization is only canonicalization, so
    the pass declines instead."""
    game = frog_parser.parse_game("""
        Game G() {
          field1 x;
          Void Initialize() {
            x <- field1;
          }
          Bool Get() {
            field1 y <- field1;
            return y == x;
          }
        }
        """)
    result = standardize_field_names(game)
    assert [f.name for f in result.fields] == ["x"]
    assert "x <- field1;" in str(result)


def test_f337_field_used_as_a_bitstring_length_is_still_renamed() -> None:
    """Length/size positions inside a type are *expressions*, not type names, so
    a field referenced there must still be renamed -- otherwise the fix would
    leave a dangling reference."""
    game = frog_parser.parse_game("""
        Game G() {
          Int n;
          Void Initialize() {
            n = 8;
          }
          Int Oracle() {
            BitString<n> v <- BitString<n>;
            return |v|;
          }
        }
        """)
    result = standardize_field_names(game)
    text = str(result)
    assert [f.name for f in result.fields] == ["field1"]
    assert "BitString<field1>" in text
    assert "BitString<n>" not in text


# ---------------------------------------------------------------------------
# F-326: the field rename respects method parameters and local binders
# ---------------------------------------------------------------------------


def _parse(source: str) -> frog_ast.Game:
    return frog_parser.parse_game(source)


def _method(game: frog_ast.Game, name: str) -> str:
    return str(next(m for m in game.methods if m.signature.name == name))


def test_f326_parameter_named_like_a_field_keeps_its_reads() -> None:
    """A parameter ``field1`` covers the whole method, so a field renamed
    away from ``field1`` does not take the parameter's reads with it."""
    game = _parse("""
        Game G() {
          Int field1;
          Int field2;
          Int Oracle(Int field1) {
            return field1;
          }
          Int Peek() {
            return field1 + field2;
          }
        }
        """)
    result = _apply_field_rename(game, {"field1": "field2", "field2": "field1"})
    assert "return field1;" in _method(result, "Oracle")
    assert "return field2 + field1;" in _method(result, "Peek")
    assert sorted(f.name for f in result.fields) == ["field1", "field2"]


def test_f326_attack_shape_keeps_the_parameter_read() -> None:
    """The F-326 attack's game: ``standardize_field_names`` and the lex-min
    pass leave Oracle returning its parameter."""
    game = _parse("""
        Game G() {
          Int x;
          Int y;
          Bool arg1;
          Void Initialize() {
            x = 1;
            y = 0;
            arg1 = true;
          }
          Int Peek() {
            return x + x + y + y;
          }
          Bool Flag() {
            return arg1;
          }
          Int Oracle(Int field1) {
            return field1;
          }
        }
        """)
    result = standardize_field_names(game)
    assert sorted(f.name for f in result.fields) == ["field1", "field2", "field3"]
    assert "return field1;" in _method(result, "Oracle")
    lex_min = FieldLexMinByRHS().apply(result, _ctx())
    assert "return field1;" in _method(lex_min, "Oracle")


def test_f326_local_binder_hides_the_field_from_its_statement_on() -> None:
    """A typed local ``x`` covers the rest of its block: reads before it are
    the field (renamed), reads after it the local (kept)."""
    game = _parse("""
        Game G() {
          Int x;
          Int Oracle() {
            Int a = x;
            Int x = a + 1;
            return x;
          }
        }
        """)
    result = _apply_field_rename(game, {"x": "field1"})
    text = _method(result, "Oracle")
    assert "Int a = field1;" in text
    assert "Int x = a + 1;" in text
    assert "return x;" in text


def test_f326_local_in_a_nested_block_does_not_hide_the_field_after_it() -> None:
    """A local declared inside an ``if`` covers that block only."""
    game = _parse("""
        Game G() {
          Int x;
          Int Oracle(Bool b) {
            if (b) {
              Int x = 5;
              return x;
            }
            return x;
          }
        }
        """)
    result = _apply_field_rename(game, {"x": "field1"})
    text = _method(result, "Oracle")
    assert "Int x = 5;" in text
    assert text.count("return x;") == 1
    assert text.count("return field1;") == 1
    assert text.index("return x;") < text.index("return field1;")


def test_f326_loop_binder_covers_the_body_only() -> None:
    """A ``for`` binder ``x`` covers the loop body; the bounds and the code
    after the loop read the field."""
    game = _parse("""
        Game G() {
          Int x;
          Int s;
          Int Oracle() {
            for (Int x = 0 to x) {
              s = s + x;
            }
            return x;
          }
        }
        """)
    result = _apply_field_rename(game, {"x": "field1", "s": "field2"})
    text = _method(result, "Oracle")
    assert "for (Int x = 0 to field1)" in text
    assert "field2 = field2 + x;" in text
    assert "return field1;" in text


def test_f326_declines_when_a_parameter_would_capture_the_renamed_field() -> None:
    """Renaming ``x`` to ``field1`` would turn Oracle's read of the field
    into a read of its parameter ``field1``: the rename is declined, with a
    near miss naming the parameter."""
    game = _parse("""
        Game G() {
          Bool x;
          Bool Oracle(Bool field1) {
            return x;
          }
        }
        """)
    ctx = _ctx()
    result = _apply_field_rename(game, {"x": "field1"}, ctx)
    assert result is game
    misses = [
        nm for nm in ctx.near_misses if nm.transform_name == "Standardize Field Names"
    ]
    assert len(misses) == 1
    assert misses[0].method == "Oracle"
    assert misses[0].variable == "field1"
    assert "renaming field 'x' to 'field1'" in misses[0].reason


def test_f326_declines_when_a_local_in_scope_would_capture_the_field() -> None:
    game = _parse("""
        Game G() {
          Int x;
          Int Oracle() {
            Int field1 = 3;
            return field1 + x;
          }
        }
        """)
    assert _apply_field_rename(game, {"x": "field1"}) is game


def test_f326_local_of_the_target_name_out_of_scope_does_not_decline() -> None:
    """A local ``field1`` in a branch does not cover the read of ``x``
    after the branch, so the rename goes ahead."""
    game = _parse("""
        Game G() {
          Int x;
          Int Oracle(Bool b) {
            if (b) {
              Int field1 = 3;
              return field1;
            }
            return x;
          }
        }
        """)
    result = _apply_field_rename(game, {"x": "field1"})
    assert result is not game
    text = _method(result, "Oracle")
    assert "Int field1 = 3;" in text
    assert text.count("return field1;") == 2
    assert [f.name for f in result.fields] == ["field1"]


def test_f326_declines_on_a_parameter_named_in_its_signature() -> None:
    """A name that is both a parameter and a field of the rename, used in
    the signature, is declined rather than guessed."""
    game = _parse("""
        Game G() {
          Int n;
          BitString<n> Oracle(Int n) {
            return 0^n;
          }
        }
        """)
    assert _apply_field_rename(game, {"n": "field1"}) is game


def test_f326_swap_still_renames_every_reference() -> None:
    """Without binders in the way, a swap of two fields renames every read,
    write and initializer at once."""
    game = _parse("""
        Game G() {
          Int a = 1;
          Int b = a;
          Void Initialize() {
            a = b;
          }
          Int Oracle() {
            Int v = b + 1;
            return v + a;
          }
        }
        """)
    result = _apply_field_rename(game, {"a": "b", "b": "a"})
    text = str(result)
    assert "Int b = 1;" in text
    assert "Int a = b;" in text
    assert "b = a;" in text
    assert "Int v = a + 1;" in text
    assert "return v + b;" in text
