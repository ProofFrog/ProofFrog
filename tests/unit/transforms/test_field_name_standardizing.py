"""Pass-level tests for ``standardize_field_names`` (F-337 / issue #252).

The pass renames game fields to canonical ``fieldN`` names.  It used to do so
with a name-keyed ``SubstitutionTransformer``, which -- because
``frog_ast.Variable`` is both an ``Expression`` and a ``Type`` -- also rewrote
occurrences of a same-named *type*.  These tests pin the two directions of the
hazard plus a positive firing probe.
"""

from __future__ import annotations

from proof_frog import frog_parser
from proof_frog.transforms.standardization import standardize_field_names


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
