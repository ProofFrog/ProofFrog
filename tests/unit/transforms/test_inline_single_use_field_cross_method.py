"""Regression test: cross-method field inlining requires the def in Initialize.

InlineSingleUseField substitutes a single-assignment field's definition into
its uses. When the use is in a DIFFERENT method, that is sound only if the
definition runs before any oracle can observe the field -- i.e. it is in
Initialize. A definition in an oracle can be observed uninitialized if the
adversary calls the using-oracle first (audit F-216).
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import InlineSingleUseFieldTransformer


def _after(src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(InlineSingleUseFieldTransformer().transform(game))


def test_f216_declines_cross_method_when_def_in_oracle() -> None:
    # `b = 5` in Store, `return b` in Get. A Get-before-Store call reads an
    # uninitialized b, so `return b` must NOT be inlined to `return 5`.
    after = _after(
        """
        Game G() {
            Int b;
            Void Initialize() { }
            Int Store() { b = 5; return 0; }
            Int Get() { return b; }
        }
        """
    )
    assert "b = 5" in after  # field survives; not inlined


def test_f216_inlines_cross_method_when_def_in_initialize() -> None:
    # `b = 5` in Initialize (runs before any oracle) -> inlining `return b`
    # to `return 5` is sound. Positive control.
    after = _after(
        """
        Game G() {
            Int b;
            Void Initialize() { b = 5; }
            Int Get() { return b; }
        }
        """
    )
    assert "return 5" in after
    assert "b = 5" not in after


def test_f349_declines_cross_method_when_initialize_may_return_before_def() -> None:
    # Initialize can return before `G = 5`, leaving G at its initial value 0,
    # so `return G` in O must NOT be inlined to `return 5` (audit F-349).
    after = _after(
        """
        Game G() {
            Int G = 0;
            Bool Initialize() {
                Bool c <- Bool;
                if (c) { return true; }
                G = 5;
                return false;
            }
            Int O() { return G; }
        }
        """
    )
    assert "G = 5" in after
    assert "return G;" in after


def test_f349_inlines_cross_method_when_return_follows_def() -> None:
    # A return AFTER the definition cannot skip it. Positive control.
    after = _after(
        """
        Game G() {
            Int G = 0;
            Bool Initialize() {
                G = 5;
                Bool c <- Bool;
                if (c) { return true; }
                return false;
            }
            Int O() { return G; }
        }
        """
    )
    assert "return 5;" in after
