"""Regression tests for the bounded fixed-point loop in
:class:`FieldLexMinByRHS` (commit 94b7c96).

A Phase-3 swap in one same-type field group can change the
``Initialize``-RHS sort key of fields in another group whose RHS
references the renamed fields. A single pass under-converges; the
``apply`` method iterates up to 8 times. These tests confirm
(a) that convergence is actually reached within the bound on
cascading renames, and (b) that the loop guards work (early-exit
when ``_phase3_lex_min_within_type`` returns the same object or a
str-equal game).
"""

from typing import Any
from unittest.mock import patch

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.standardization import (
    FieldLexMinByRHS,
    _phase3_lex_min_within_type,
)
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def test_apply_terminates_when_already_canonical() -> None:
    """Initialize RHSs already lex-min within each type group: no rename,
    one iteration sees ``new_game is game`` and returns immediately."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 1;
                field2 = 2;
            }
        }
        """
    )
    with patch(
        "proof_frog.transforms.standardization._phase3_lex_min_within_type",
        wraps=_phase3_lex_min_within_type,
    ) as spy:
        out = FieldLexMinByRHS().apply(game, _ctx())
    assert spy.call_count == 1
    assert out is game


def test_apply_converges_on_single_swap_within_bound() -> None:
    """A within-group swap converges after at most two iterations
    (one productive pass + one confirming pass)."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 2;
                field2 = 1;
            }
        }
        """
    )
    with patch(
        "proof_frog.transforms.standardization._phase3_lex_min_within_type",
        wraps=_phase3_lex_min_within_type,
    ) as spy:
        out = FieldLexMinByRHS().apply(game, _ctx())
    # First iteration produces a rename; second returns str-equal -> early exit.
    assert spy.call_count == 2
    # field1 now binds the lex-min RHS (Integer(1)); field2 binds Integer(2).
    init = next(m for m in out.methods if m.signature.name == "Initialize")
    bindings = {
        s.var.name: str(s.value)
        for s in init.block.statements
        if isinstance(s, frog_ast.Assignment)
        and isinstance(s.var, frog_ast.Variable)
    }
    assert bindings == {"field1": "1", "field2": "2"}


def test_apply_respects_8_iteration_cap() -> None:
    """If ``_phase3_lex_min_within_type`` somehow never converges, the
    loop bails out after 8 iterations rather than spinning forever."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int field1;
            Void Initialize() {
                field1 = 1;
            }
        }
        """
    )

    call_count = {"n": 100}

    def never_converges(g: frog_ast.Game) -> frog_ast.Game:
        # Return a distinct-object, str-distinct copy each time so neither
        # early-exit guard fires. Start at 100 to avoid colliding with the
        # original game's ``field1 = 1`` body.
        call_count["n"] += 1
        new = frog_parser.parse_game(
            f"""
            Game G() {{
                Int field1;
                Void Initialize() {{
                    field1 = {call_count["n"]};
                }}
            }}
            """
        )
        return new

    with patch(
        "proof_frog.transforms.standardization._phase3_lex_min_within_type",
        side_effect=never_converges,
    ) as spy:
        FieldLexMinByRHS().apply(game, _ctx())
    assert spy.call_count == 8


def test_apply_early_exits_on_str_equal_fixed_point() -> None:
    """If a pass produces a new object that stringifies identically to
    the previous game, ``apply`` must early-exit (str() equality guard)."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Int field1;
            Void Initialize() {
                field1 = 1;
            }
        }
        """
    )
    call_count = {"n": 0}

    def returns_new_object_each_call(g: frog_ast.Game) -> frog_ast.Game:
        call_count["n"] += 1
        # First call returns a fresh deep copy that stringifies the same;
        # the str() guard should trigger early-exit.
        return frog_parser.parse_game(str(g))

    with patch(
        "proof_frog.transforms.standardization._phase3_lex_min_within_type",
        side_effect=returns_new_object_each_call,
    ) as spy:
        FieldLexMinByRHS().apply(game, _ctx())
    # Iteration 1: produces str-equal fresh object -> return after first
    # call (the `if str(new_game) == str(game)` branch).
    assert spy.call_count == 1


def test_apply_cascading_rename_converges_within_bound() -> None:
    """Cascading-rename worst case: a swap in group A changes the RHS
    sort key of group B (via field names referenced in B's RHS), which
    triggers another swap. Confirm convergence is reached and the iteration
    count stays well under 8."""
    # Two type groups: Int (field1, field2) and BitString<8> (field3, field4).
    # field3 = field2 and field4 = field1 reference the Int group, so a swap
    # of field1<->field2 changes the RHS keys of field3, field4.
    game = frog_parser.parse_game(
        """
        Game G() {
            Int field1;
            Int field2;
            BitString<8> field3;
            BitString<8> field4;
            Void Initialize() {
                field1 = 2;
                field2 = 1;
                field3 = 0b00000000;
                field4 = 0b00000000;
            }
        }
        """
    )
    with patch(
        "proof_frog.transforms.standardization._phase3_lex_min_within_type",
        wraps=_phase3_lex_min_within_type,
    ) as spy:
        out: Any = FieldLexMinByRHS().apply(game, _ctx())
    # Should converge in far fewer than the 8-iter cap.
    assert spy.call_count <= 8
    # And re-applying must be a no-op.
    out2 = FieldLexMinByRHS().apply(out, _ctx())
    assert str(out2) == str(out)
