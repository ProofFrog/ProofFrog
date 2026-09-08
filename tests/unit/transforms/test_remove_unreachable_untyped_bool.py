"""RemoveUnreachable must not crash on a Bool condition whose only type
information is an untyped literal assignment (the shape main's tuple
splitting leaves after pruning ``Bool hit;``)."""

from proof_frog import frog_parser
from proof_frog.transforms.control_flow import RemoveUnreachableTransformer

GAME = """
Game G(Function<BitString<m>, BitString<k>> H) {
    BitString<m> sStar;
    BitString<k> v;

    Void Initialize() {
        sStar <- BitString<m>;
        v <- BitString<k>;
    }

    BitString<k> HashH(BitString<m> x) {
        if (sStar == x) {
            hit = true;
            if (hit) {
                return v;
            }
            return H(x);
        }
        hit = false;
        if (hit) {
            return 0^k;
        }
        return H(x);
    }
}
"""


def test_untyped_bool_guard_does_not_crash() -> None:
    game = frog_parser.parse_game(GAME)
    result = RemoveUnreachableTransformer(game).transform(game)
    assert result is not None
