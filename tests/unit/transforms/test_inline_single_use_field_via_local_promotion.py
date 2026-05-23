"""Tests for the local-promotion branch of ``InlineSingleUseFieldTransformer``.

When a field's RHS references Initialize-locals, the cross-method inlining
path can promote those locals to fields first, enabling the inlining to
proceed.  See
``extras/docs/transforms/inlining/InlineSingleUseFieldViaLocalPromotion.md``.

Promotion is gated to fields whose RHS is a top-level bitstring
concatenation (``||`` chain) — the shape used for Hash-input layouts
that downstream passes then match slice-wise.  Other shapes remain
unchanged to avoid perturbing canonical forms that already work via
other routes.
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import InlineSingleUseFieldTransformer


def _transform_and_compare(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = InlineSingleUseFieldTransformer().transform(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


def _transform_no_change(source: str) -> None:
    _transform_and_compare(source, source)


# ---------------------------------------------------------------------------
# Positive cases (concat-shaped field RHS)
# ---------------------------------------------------------------------------


def test_promotes_sampled_local_in_concat_field_rhs() -> None:
    """Field RHS is a concatenation referencing a sampled local used
    only inside the field RHS.  Promotion + inlining removes the field
    and the original local becomes a field referenced at the inlined
    use site."""
    source = """
    Game Test(Int n) {
        BitString<2 * n> fieldA;
        Void Initialize() {
            BitString<n> r <- BitString<n>;
            fieldA = r || r;
        }
        BitString<2 * n> Query() {
            return fieldA;
        }
    }
    """
    expected = """
    Game Test(Int n) {
        BitString<n> _promoted_r_0;
        Void Initialize() {
            _promoted_r_0 <- BitString<n>;
        }
        BitString<2 * n> Query() {
            return _promoted_r_0 || _promoted_r_0;
        }
    }
    """
    _transform_and_compare(source, expected)


def test_promotes_local_defined_by_nondeterministic_call_in_concat() -> None:
    """Field RHS concatenation references a local defined by a typed
    non-deterministic assignment.  Because the defining statement runs
    once in Initialize, promotion is still sound."""
    source = """
    Game Test(Int n) {
        BitString<2 * n> fieldA;
        Void Initialize() {
            BitString<n> v = F.evaluate(0);
            fieldA = v || v;
        }
        BitString<2 * n> Query() {
            return fieldA;
        }
    }
    """
    expected = """
    Game Test(Int n) {
        BitString<n> _promoted_v_0;
        Void Initialize() {
            _promoted_v_0 = F.evaluate(0);
        }
        BitString<2 * n> Query() {
            return _promoted_v_0 || _promoted_v_0;
        }
    }
    """
    _transform_and_compare(source, expected)


def test_promotes_two_distinct_locals_in_concat() -> None:
    """Field RHS concatenation references two distinct promotable
    locals; both get promoted so cross-method inlining succeeds."""
    source = """
    Game Test(Int n) {
        BitString<2 * n> fieldA;
        Void Initialize() {
            BitString<n> r <- BitString<n>;
            BitString<n> s <- BitString<n>;
            fieldA = r || s;
        }
        BitString<2 * n> Query() {
            return fieldA;
        }
    }
    """
    expected = """
    Game Test(Int n) {
        BitString<n> _promoted_r_0;
        BitString<n> _promoted_s_0;
        Void Initialize() {
            _promoted_r_0 <- BitString<n>;
            _promoted_s_0 <- BitString<n>;
        }
        BitString<2 * n> Query() {
            return _promoted_r_0 || _promoted_s_0;
        }
    }
    """
    _transform_and_compare(source, expected)


def test_promotes_local_used_elsewhere_in_initialize() -> None:
    """Field RHS concatenation references a local that is also used
    elsewhere in Initialize; those other uses also get rewritten to
    the promoted field name."""
    source = """
    Game Test(Int n) {
        BitString<2 * n> fieldA;
        BitString<n> fieldB;
        Void Initialize() {
            BitString<n> r <- BitString<n>;
            fieldB = r;
            fieldA = r || r;
        }
        BitString<2 * n> Query() {
            return fieldA;
        }
    }
    """
    # Key behavior: ``r`` is promoted, and all references (both in
    # ``fieldB = r`` and in the concatenation) are rewritten to the
    # promoted field name.  ``fieldA`` is then inlined away; ``fieldB``
    # persists (a later pass such as RemoveUnnecessaryFields would drop
    # it).
    expected = """
    Game Test(Int n) {
        BitString<n> fieldB;
        BitString<n> _promoted_r_0;
        Void Initialize() {
            _promoted_r_0 <- BitString<n>;
            fieldB = _promoted_r_0;
        }
        BitString<2 * n> Query() {
            return _promoted_r_0 || _promoted_r_0;
        }
    }
    """
    _transform_and_compare(source, expected)


# ---------------------------------------------------------------------------
# Negative cases (no change)
# ---------------------------------------------------------------------------


def test_non_concat_field_rhs_not_promoted() -> None:
    """Gate: non-concat RHS shapes are not eligible for promotion, so
    even though the local would be a valid candidate, the game is
    unchanged."""
    source = """
    Game Test(Int n) {
        BitString<n> fieldA;
        Void Initialize() {
            BitString<n> r <- BitString<n>;
            fieldA = r;
        }
        BitString<n> Query() {
            return fieldA;
        }
    }
    """
    _transform_no_change(source)


def test_local_reassigned_same_method_not_promoted() -> None:
    source = """
    Game Test(Int n) {
        BitString<2 * n> fieldA;
        Void Initialize() {
            BitString<n> r <- BitString<n>;
            r = 0^n;
            fieldA = r || r;
        }
        BitString<2 * n> Query() {
            return fieldA;
        }
    }
    """
    _transform_no_change(source)


def test_local_reassigned_in_oracle_not_promoted() -> None:
    source = """
    Game Test(Int n) {
        BitString<2 * n> fieldA;
        Void Initialize() {
            BitString<n> r <- BitString<n>;
            fieldA = r || r;
        }
        BitString<2 * n> Query() {
            r = 0^n;
            return fieldA;
        }
    }
    """
    _transform_no_change(source)


def test_field_with_nondeterministic_multi_use_still_blocked() -> None:
    # Multi-use field with a non-deterministic call RHS: the existing
    # purity guard blocks inlining before the local-promotion branch is
    # reached, so the game is unchanged even though no local would be
    # eligible for promotion anyway.
    source = """
    Game Test(Int n) {
        BitString<n> fieldA;
        Void Initialize() {
            fieldA = F.evaluate(0);
        }
        BitString<n> Query1() {
            return fieldA;
        }
        BitString<n> Query2() {
            return fieldA;
        }
    }
    """
    _transform_no_change(source)
