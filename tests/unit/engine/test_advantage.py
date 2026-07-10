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


# --- Tier 2: per-oracle count derivation --------------------------------------

_HELPER_GAME_FILE = """
Game Replacement(Set S) {
    S Samp() { S val <- S; return val; }
}
Game NoReplacement(Set S) {
    Set<S> seen;
    S Samp() { S val <-uniq[seen] S; return val; }
}
advantage <= count_Samp * (count_Samp - 1) / (2 * |S|);
export as DistinctSampling;
"""

_ORDER_HELPER_FILE = """
Game MaybeZero(Int order) {
    ModInt<order> Samp() { ModInt<order> v <- ModInt<order>; return v; }
}
Game Nonzero(Int order) {
    Set<ModInt<order>> seen;
    ModInt<order> Samp() { ModInt<order> v <-uniq[seen] ModInt<order>; return v; }
}
advantage <= count_Samp / order;
export as NonzeroSampling;
"""


def _challenger_call(oracle: str) -> frog_ast.FuncCall:
    return frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("challenger"), oracle), []
    )


def _reduction(name: str, methods: dict[str, list[str]]) -> frog_ast.Reduction:
    """A reduction whose method `m` calls each challenger oracle in methods[m]."""
    method_nodes = [
        frog_ast.Method(
            frog_ast.MethodSignature(mname, frog_ast.Void(), []),
            frog_ast.Block([_challenger_call(c) for c in calls]),
        )
        for mname, calls in methods.items()
    ]
    return frog_ast.Reduction(
        (name, [], [], method_nodes),
        frog_ast.ParameterizedGame("H", []),
        frog_ast.ParameterizedGame("Th", []),
    )


def _lookup(**reductions: dict[str, list[str]]) -> dict[str, object]:
    from proof_frog import frog_parser

    lk: dict[str, object] = {
        "DistinctSampling": frog_parser.parse_game_file(_HELPER_GAME_FILE),
        "NonzeroSampling": frog_parser.parse_game_file(_ORDER_HELPER_FILE),
    }
    for name, methods in reductions.items():
        lk[name] = _reduction(name, methods)
    return lk


def _birthday_hop(reduction: str = "R") -> proof_engine.HopResult:
    return _hop_result(
        1,
        "by_assumption",
        notion=_game("DistinctSampling", "Message"),
        reduction=_game(reduction),
    )


class TestOracleCountDerivation:
    def test_oracle_count_becomes_theorem_query_count(self) -> None:
        # Reduction's CTXT oracle calls Samp once -> count_Samp = count_CTXT.
        bound = advantage.synthesize_from_hop_results(
            [_birthday_hop()],
            definition_lookup=_lookup(R={"CTXT": ["Samp"]}),
        )
        assert bound.render() == "count_CTXT*(count_CTXT - 1)/(2*|Message|)"

    def test_initialize_sampling_is_a_constant(self) -> None:
        # Samp fired once in Initialize (runs once) -> count_Samp = 1 -> term 0.
        bound = advantage.synthesize_from_hop_results(
            [_birthday_hop()],
            definition_lookup=_lookup(R={"Initialize": ["Samp"]}),
        )
        assert bound.render() == "0"

    def test_multiple_call_sites_multiply(self) -> None:
        # Two Samp calls per CTXT invocation -> count_Samp = 2 * count_CTXT.
        bound = advantage.synthesize_from_hop_results(
            [_birthday_hop()],
            definition_lookup=_lookup(R={"CTXT": ["Samp", "Samp"]}),
        )
        assert bound.render() == "count_CTXT*(2*count_CTXT - 1)/|Message|"

    def test_integer_calls_cap_pins_count(self) -> None:
        # A concrete `calls <= 1` pins count_CTXT -> 1, so the birthday term is 0.
        bound = advantage.synthesize_from_hop_results(
            [_birthday_hop()],
            definition_lookup=_lookup(R={"CTXT": ["Samp"]}),
            max_calls=frog_ast.Integer(1),
        )
        assert bound.render() == "0"

    def test_two_reductions_collapse_into_one_sum(self) -> None:
        bound = advantage.synthesize_from_hop_results(
            [_birthday_hop("R1"), _birthday_hop("R2")],
            definition_lookup=_lookup(
                R1={"CTXT": ["Samp"]}, R2={"CTXT": ["Samp"]}
            ),
        )
        assert bound.render() == "count_CTXT*(count_CTXT - 1)/|Message|"

    def test_direct_hop_leaves_count_symbolic(self) -> None:
        # No reduction: the helper's own oracle count survives as count_Samp.
        results = [
            _hop_result(
                1, "by_assumption", notion=_game("DistinctSampling", "Message")
            )
        ]
        bound = advantage.synthesize_from_hop_results(
            results, definition_lookup=_lookup()
        )
        assert bound.render() == "count_Samp*(count_Samp - 1)/(2*|Message|)"

    def test_order_param_helper_with_field_access(self) -> None:
        notion = frog_ast.ParameterizedGame(
            "NonzeroSampling", [frog_ast.FieldAccess(frog_ast.Variable("G"), "order")]
        )
        results = [
            proof_engine.HopResult(
                step_num=1,
                valid=True,
                kind="by_assumption",
                depth=0,
                current_desc="",
                next_desc="",
                justification=notion,
                reduction=_game("R"),
            )
        ]
        bound = advantage.synthesize_from_hop_results(
            results,
            definition_lookup=_lookup(R={"Initialize": ["Samp"]}),
        )
        assert bound.render() == "1/G.order"

    def test_crypto_assumption_without_clause_stays_opaque(self) -> None:
        results = [
            _hop_result(
                1,
                "by_assumption",
                notion=_game("PRFSecurity", "F"),
                reduction=_game("R"),
            )
        ]
        bound = advantage.synthesize_from_hop_results(
            results, definition_lookup=_lookup(R={"CTXT": ["Samp"]})
        )
        assert bound.render() == "Adv^PRFSecurity(F)(B1)"

    def test_mixed_and_substituted_expression(self) -> None:
        results = [
            _hop_result(
                1, "by_assumption", notion=_game("PRFSecurity", "F"),
                reduction=_game("Rp"),
            ),
            _birthday_hop("R"),
        ]
        bound = advantage.synthesize_from_hop_results(
            results, definition_lookup=_lookup(R={"CTXT": ["Samp"]})
        )
        assert bound.render() == (
            "Adv^PRFSecurity(F)(B1) + count_CTXT*(count_CTXT - 1)/(2*|Message|)"
        )
        substituted = str(bound.substituted_expression())
        assert "Adv_0" in substituted
        assert "count_CTXT" in substituted
