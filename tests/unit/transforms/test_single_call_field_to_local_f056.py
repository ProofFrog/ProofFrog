"""F-056 regression: SingleCallFieldToLocal must account for sibling-method
calls when deciding whether a field's read site runs at most once."""

from proof_frog import frog_parser
from proof_frog.transforms.sampling import _single_call_field_to_local


def test_sibling_call_to_read_site_blocks_localization() -> None:
    """F-056: the field ``x`` is read in ``Helper``, which is invoked by the
    sibling ``Probe`` via ``Left.Helper()``.  One adversary call to Probe runs
    Helper an extra time, so the persistent field (read repeatedly) is not
    interchangeable with a per-call fresh local -- the pass must DECLINE."""
    game = frog_parser.parse_game("""
        Game Left(Int n) {
            BitString<n> x;
            Void Initialize() {
                x <- BitString<n>;
            }
            BitString<n> Helper() {
                return x;
            }
            BitString<n> Probe() {
                return Left.Helper();
            }
        }
        """)
    assert _single_call_field_to_local(game) == game


def test_no_sibling_call_still_localizes() -> None:
    """Positive control: with no internal call to the read site, the move still
    fires."""
    game = frog_parser.parse_game("""
        Game Left(Int n) {
            BitString<n> x;
            Void Initialize() {
                x <- BitString<n>;
            }
            BitString<n> Helper() {
                return x;
            }
        }
        """)
    expected = frog_parser.parse_game("""
        Game Left(Int n) {
            Void Initialize() {
            }
            BitString<n> Helper() {
                BitString<n> x <- BitString<n>;
                return x;
            }
        }
        """)
    assert _single_call_field_to_local(game) == expected
