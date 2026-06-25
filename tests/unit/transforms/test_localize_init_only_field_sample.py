"""Tests for LocalizeInitOnlyFieldSample: converts field samples to local
samples when the field is only used within Initialize."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.sampling import LocalizeInitOnlyFieldSample
from proof_frog.transforms._base import PipelineContext


def _make_ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types={},
        proof_namespace={},
        subsets_pairs=set(),
        equality_pairs=set(),
    )


def _apply(source: str) -> str:
    game = frog_parser.parse_game(source)
    result = LocalizeInitOnlyFieldSample().apply(game, _make_ctx())
    return str(result)


@pytest.mark.parametrize(
    "source,expected_has_field",
    [
        # F-044 A1: the field is read BEFORE its sample inside Initialize
        # (reading its initializer value). Localizing would delete the field
        # and dangle the pre-sample read -> must DECLINE (field survives).
        (
            """
            Game Test() {
                BitString<1> myfield = 0b1;
                BitString<1> Initialize() {
                    BitString<1> x = myfield;
                    myfield <- BitString<1>;
                    return x;
                }
            }
            """,
            True,
        ),
        # F-044 A2: the field is referenced only from another field's
        # initializer expression -> deleting it would dangle that initializer
        # -> must DECLINE.
        (
            """
            Game Test() {
                BitString<1> myfield = 0b1;
                BitString<1> g = myfield;
                BitString<1> Initialize() {
                    myfield <- BitString<1>;
                    return g;
                }
            }
            """,
            True,
        ),
        # Field only used in Initialize — should become local
        (
            """
            Game Test() {
                Int myfield;
                Int Initialize() {
                    myfield <- Int;
                    return 0;
                }
                Int Query() {
                    return 42;
                }
            }
            """,
            False,
        ),
        # Field used in Query — should stay as field
        (
            """
            Game Test() {
                Int myfield;
                Void Initialize() {
                    myfield <- Int;
                }
                Int Query() {
                    return myfield;
                }
            }
            """,
            True,
        ),
        # Field used in Initialize return — should become local
        (
            """
            Game Test() {
                Int myfield;
                Int Initialize() {
                    myfield <- Int;
                    return myfield;
                }
                Int Query() {
                    return 42;
                }
            }
            """,
            False,
        ),
    ],
    ids=[
        "f044-read-before-sample",
        "f044-other-field-initializer",
        "init-only",
        "used-in-oracle",
        "init-return",
    ],
)
def test_localize_init_only_field_sample(source: str, expected_has_field: bool) -> None:
    game = frog_parser.parse_game(source)
    ctx = _make_ctx()
    result = LocalizeInitOnlyFieldSample().apply(game, ctx)
    has_field = len(result.fields) > 0 and any(
        f.name == "myfield" for f in result.fields
    )
    assert has_field == expected_has_field
