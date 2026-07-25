"""AST-node equality hardening (audit round 2, family 8).

F-335: `Game.__eq__` used a loose `isinstance` check, so a `Reduction`
(a `Game` subclass) compared equal to a plain `Game` with the same body,
and two `Reduction`s composing different security games compared equal
because the inherited comparison ignored `to_use`/`play_against`.

F-336: `ASTNode.__eq__` iterated only the left operand's `__dict__`,
making equality partial and asymmetric on a malformed node (a degenerate
left operand subset-compared equal; the reflected direction raised
`AttributeError`).
"""

from proof_frog import frog_ast, frog_parser


def _reduction(compose: str, against: str) -> frog_ast.Reduction:
    return frog_parser.parse_reduction(
        f"""
        Reduction R() compose {compose} against {against}.Adversary {{
            Int y;
            Void Initialize() {{
                y = 2;
                return None;
            }}
            Int Run() {{
                return y;
            }}
        }}
        """
    )


def _plain_game() -> frog_ast.Game:
    return frog_parser.parse_game(
        """
        Game R() {
            Int y;
            Void Initialize() {
                y = 2;
                return None;
            }
            Int Run() {
                return y;
            }
        }
        """
    )


# ---------------------------------------------------------------------------
# F-335: Reduction equality
# ---------------------------------------------------------------------------


def test_reductions_composing_different_games_are_unequal() -> None:
    r1 = _reduction("SecA()", "Thm()")
    r2 = _reduction("SecB()", "Thm()")
    # Identical bodies and parameters; only the composed game differs.
    assert r1 != r2
    assert r2 != r1  # symmetric


def test_reductions_playing_against_different_games_are_unequal() -> None:
    r1 = _reduction("Sec()", "ThmA()")
    r2 = _reduction("Sec()", "ThmB()")
    assert r1 != r2
    assert r2 != r1


def test_identical_reductions_are_equal() -> None:
    # Positive control: same composition and body -> equal.
    assert _reduction("Sec()", "Thm()") == _reduction("Sec()", "Thm()")


def test_reduction_not_equal_to_plain_game_with_same_body() -> None:
    reduction = _reduction("Sec()", "Thm()")
    game = _plain_game()
    # Same body/parameters, but a Reduction is not a plain Game.
    assert reduction != game
    assert game != reduction  # symmetric (F-335 also fixes the reverse)


# ---------------------------------------------------------------------------
# F-336: symmetric / total base equality on malformed nodes
# ---------------------------------------------------------------------------


def test_missing_attribute_compares_unequal_both_directions() -> None:
    # A degenerate node missing a semantic attribute must compare unequal in
    # BOTH directions (fail-closed), never subset-equal and never raising.
    complete = frog_parser.parse_game(
        """
        Game G() {
            Int Run() {
                Int x = 1;
                return x;
            }
        }
        """
    ).methods[0].block.statements[0]
    assert isinstance(complete, frog_ast.Sample) or hasattr(complete, "__dict__")

    # Build a degenerate twin of the same class with one attribute removed.
    import copy

    degenerate = copy.deepcopy(complete)
    some_attr = next(
        a
        for a in vars(degenerate)
        if a not in {"line_num", "column_num", "origin"}
    )
    delattr(degenerate, some_attr)

    assert complete != degenerate
    assert degenerate != complete  # symmetric, no AttributeError


def test_well_formed_same_class_nodes_still_compare_by_value() -> None:
    # Positive control: the key-set guard does not disturb ordinary equality.
    g1 = frog_parser.parse_game(
        "Game G() { Int Run() { return 1; } }"
    )
    g2 = frog_parser.parse_game(
        "Game G() { Int Run() { return 1; } }"
    )
    g3 = frog_parser.parse_game(
        "Game G() { Int Run() { return 2; } }"
    )
    assert g1 == g2
    assert g1 != g3
