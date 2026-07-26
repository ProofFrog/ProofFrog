"""Tests for UniformGroupElemSimplification (uniform * anything = uniform).

Includes the F-279 loop-multiplicity regression: a single syntactic use of a
uniform GroupElem inside a loop body is dynamically evaluated once per
iteration, so the uniform is combined with a fresh partner each time and the
absorption `u * g^i -> u` is unsound.
"""

from proof_frog import frog_parser
from proof_frog.transforms.algebraic import UniformGroupElemSimplificationTransformer


def test_f279_declines_single_use_inside_loop() -> None:
    method = frog_parser.parse_method(
        """
        GroupElem<G> Run(Group G) {
            Map<Int, GroupElem<G>> arr;
            GroupElem<G> u <- GroupElem<G>;
            for (Int i = 0 to 2) {
                arr[i] = u * G.generator ^ i;
            }
            return arr[0] / arr[1];
        }
        """
    )
    out = UniformGroupElemSimplificationTransformer().transform(method)
    # `u * G.generator ^ i` must NOT collapse to `u` inside the loop.
    assert "u * G.generator ^ i" in str(out)


def test_f279_still_fires_single_use_no_loop() -> None:
    """Positive control: the same product outside a loop still absorbs."""
    method = frog_parser.parse_method(
        """
        GroupElem<G> Run(Group G, GroupElem<G> m) {
            GroupElem<G> u <- GroupElem<G>;
            return u * m;
        }
        """
    )
    out = UniformGroupElemSimplificationTransformer().transform(method)
    assert "u * m" not in str(out)
    assert "return u" in str(out)
