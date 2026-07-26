"""Regression test: InlineSingleUseField must see view-carried reads (F-218).

A field RHS like `0 in M.keys` reads the map `M` only through a `.keys`
FieldAccess. The old free-var scan (VariableCollectionVisitor) skipped
variables under a FieldAccess, so the read-set was EMPTY and both stability
gates became vacuous -- letting the field inline cross-method into an oracle
even though another oracle mutates `M`, so the inlined `0 in M.keys` reads the
live view instead of the Initialize-time snapshot. The FieldAccess-complete
`referenced_variable_names` now contributes `M`, so the stability gate declines.
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import InlineSingleUseFieldTransformer


def test_f218_view_carried_read_blocks_cross_method_inline() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<Int, Int> M;
            Bool A;
            Void Initialize() { A = 0 in M.keys; }
            Void Put() { M[0] = 1; }
            Bool Get() { return A; }
        }
        """
    )
    out = str(InlineSingleUseFieldTransformer().transform(game))
    # A must NOT be inlined into Get(): `M` is mutated in Put(), so the field's
    # Initialize-time value is not stable.
    assert "A = 0 in M.keys" in out
    assert "return A" in out


def test_f218_plain_stable_field_read_still_inlines() -> None:
    """Positive control: a field whose RHS reads a plain, stably-assigned field
    still inlines cross-method -- the FieldAccess-complete read-set does not
    over-decline ordinary (non-view) reads."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int x;
            Int A;
            Void Initialize() {
                x = 3;
                A = x + 1;
            }
            Int Get() { return A; }
        }
        """
    )
    out = str(InlineSingleUseFieldTransformer().transform(game))
    # A is inlined into Get() (its value flows through), so the field and its
    # `return A` are gone -- ordinary reads are not over-declined.
    assert "return A" not in out
    assert "Int A" not in out
