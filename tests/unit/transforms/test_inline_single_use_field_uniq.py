"""Regression test: InlineSingleUseField counts `<-uniq[S]` insertion (F-212/213).

A `<-uniq[S]` draw implicitly inserts the drawn value into the exclusion set
`S`, so a set field used as a uniq domain is mutated on every draw. The
single-use-field check counted only lvalue writes, so it treated such a set as
single-assignment and either eliminated it -- rewriting `<-uniq[S]` to
`<-uniq[{}]` and destroying distinctness (F-212) -- or inlined a stale snapshot
of it across methods (F-213).
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import InlineSingleUseFieldTransformer


def _after(src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(InlineSingleUseFieldTransformer().transform(game))


def test_f212_uniq_exclusion_set_not_eliminated() -> None:
    # S is assigned once (`S = {}`) and used as a uniq exclusion set. The draw
    # grows S, so S is NOT single-assignment and must not be inlined to `{}`.
    after = _after(
        """
        Game G(Int n) {
            Set<BitString<n>> S;
            Void Initialize() { S = {}; }
            BitString<n> Draw() {
                BitString<n> x <-uniq[S] BitString<n>;
                return x;
            }
        }
        """
    )
    # S survives; the draw still excludes S (not rewritten to `<-uniq[{}]`).
    assert "Set<BitString<n>> S" in after
    assert "<-uniq[{}]" not in after
    assert "<-uniq[S]" in after


def test_f213_uniq_set_snapshot_not_inlined_cross_method() -> None:
    # A = S in Initialize, then S grows via a uniq draw in another oracle.
    # Inlining A's snapshot of S cross-method would read a stale (empty) S.
    after = _after(
        """
        Game G(Int n) {
            Set<BitString<n>> S;
            Set<BitString<n>> A;
            Void Initialize() { S = {}; A = S; }
            BitString<n> Draw() {
                BitString<n> x <-uniq[S] BitString<n>;
                return x;
            }
            Int Count() { return |A|; }
        }
        """
    )
    # A is not eliminated (its snapshot is not a stable single value).
    assert "A = S" in after
