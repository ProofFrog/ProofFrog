"""Unit tests for advantage-bound synthesis (proof_frog.advantage)."""

from proof_frog import advantage, frog_ast, proof_engine


def _game(name: str, *args: str) -> frog_ast.ParameterizedGame:
    return frog_ast.ParameterizedGame(name, [frog_ast.Variable(a) for a in args])


def _hop(
    kind: str, notion: str | None = None, reduction: str | None = None
) -> advantage.HopInfo:
    return advantage.HopInfo(
        kind=kind,
        notion=_game(notion) if notion is not None else None,
        reduction=_game(reduction) if reduction is not None else None,
    )


class TestSynthesizeFromHops:
    def test_all_equivalent_gives_zero(self) -> None:
        bound = advantage.synthesize_from_hops([_hop("equivalent"), _hop("equivalent")])
        assert bound.supported
        assert bound.is_trivial()
        assert bound.render() == "0"

    def test_single_assumption_hop(self) -> None:
        bound = advantage.synthesize_from_hops(
            [
                _hop("equivalent"),
                _hop("by_assumption", "PRFSecurity", "R1"),
                _hop("equivalent"),
            ]
        )
        assert bound.render() == "Adv^PRFSecurity()(B1)"

    def test_two_distinct_reductions_two_terms(self) -> None:
        bound = advantage.synthesize_from_hops(
            [
                _hop("equivalent"),
                _hop("by_assumption", "S", "R1"),
                _hop("equivalent"),
                _hop("by_assumption", "S", "R2"),
                _hop("equivalent"),
            ]
        )
        assert bound.render() == "Adv^S()(B1) + Adv^S()(B2)"

    def test_repeated_assumption_collapses_to_coefficient(self) -> None:
        # Same notion and same reduction used twice -> 2 * Adv^X(B1).
        bound = advantage.synthesize_from_hops(
            [
                _hop("by_assumption", "PRFSecurity", "R"),
                _hop("equivalent"),
                _hop("by_assumption", "PRFSecurity", "R"),
            ]
        )
        assert bound.render() == "2 * Adv^PRFSecurity()(B1)"

    def test_no_reduction_uses_direct_adversary(self) -> None:
        bound = advantage.synthesize_from_hops([_hop("by_assumption", "DDH")])
        assert bound.render() == "Adv^DDH()(A)"

    def test_lemma_hop_contributes_black_box_term(self) -> None:
        bound = advantage.synthesize_from_hops([_hop("by_lemma", "SubProperty", "R1")])
        assert bound.render() == "Adv^SubProperty()(B1)"

    def test_mixed_sequence(self) -> None:
        bound = advantage.synthesize_from_hops(
            [
                _hop("equivalent"),
                _hop("by_assumption", "S", "R1"),
                _hop("equivalent"),
                _hop("by_assumption", "S", "R1"),  # same as first -> collapses
                _hop("by_assumption", "T", "R2"),
            ]
        )
        # 2 * Adv^S(B1) + Adv^T(B2)
        assert bound.render() == "2 * Adv^S()(B1) + Adv^T()(B2)"

    def test_custom_term_renderer_and_joiner(self) -> None:
        bound = advantage.synthesize_from_hops(
            [
                _hop("by_assumption", "S", "R"),
                _hop("by_assumption", "S", "R"),
            ]
        )
        rendered = bound.render(
            term_renderer=lambda t: f"\\Adv{{{t.notion.name}}}{{{t.adversary}}}",
            mul=r" \cdot ",
            joiner=" + ",
        )
        assert rendered == r"2 \cdot \Adv{S}{B1}"


def _hop_result(step_num: int, kind: str, **kw: object) -> proof_engine.HopResult:
    return proof_engine.HopResult(
        step_num=step_num,
        valid=True,
        kind=kind,
        depth=int(kw.get("depth", 0)),  # type: ignore[arg-type]
        current_desc="",
        next_desc="",
        justification=kw.get("notion"),  # type: ignore[arg-type]
        reduction=kw.get("reduction"),  # type: ignore[arg-type]
    )


class TestSynthesizeFromHopResults:
    def test_reads_justification_and_reduction(self) -> None:
        results = [
            _hop_result(1, "equivalent"),
            _hop_result(
                2,
                "by_assumption",
                notion=_game("PRFSecurity", "F"),
                reduction=_game("R1", "F"),
            ),
            _hop_result(3, "equivalent"),
        ]
        bound = advantage.synthesize_from_hop_results(results)
        assert bound.render() == "Adv^PRFSecurity(F)(B1)"

    def test_induction_is_unsupported_via_depth(self) -> None:
        results = [
            _hop_result(1, "equivalent"),
            _hop_result(
                1, "by_assumption", depth=1, notion=_game("S"), reduction=_game("R")
            ),
        ]
        bound = advantage.synthesize_from_hop_results(results)
        assert not bound.supported
        assert "induct" in bound.note.lower()

    def test_induction_is_unsupported_via_rollover(self) -> None:
        results = [
            _hop_result(1, "equivalent"),
            _hop_result(1, "induction_rollover"),
        ]
        bound = advantage.synthesize_from_hop_results(results)
        assert not bound.supported
