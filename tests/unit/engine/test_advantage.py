"""Unit tests for advantage-bound synthesis (proof_frog.advantage)."""

import sympy

from proof_frog import advantage, frog_ast, frog_parser, proof_engine


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
            definition_lookup=_lookup(R1={"CTXT": ["Samp"]}, R2={"CTXT": ["Samp"]}),
        )
        assert bound.render() == "count_CTXT*(count_CTXT - 1)/|Message|"

    def test_direct_hop_leaves_count_symbolic(self) -> None:
        # No reduction: the helper's own oracle count survives as count_Samp.
        results = [
            _hop_result(1, "by_assumption", notion=_game("DistinctSampling", "Message"))
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
                1,
                "by_assumption",
                notion=_game("PRFSecurity", "F"),
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


# --- Tier 2: monotonicity guardrail -------------------------------------------


def _clause(bound_src: str) -> frog_ast.Expression:
    from proof_frog import frog_parser

    gf = frog_parser.parse_game_file(
        "Game A(Set S) { S Samp() { S v <- S; return v; } }\n"
        "Game B(Set S) { Set<S> seen; S Samp() { S v <-uniq[seen] S; return v; } }\n"
        f"advantage <= {bound_src};\nexport as D;"
    )
    assert gf.advantage is not None
    return gf.advantage.bound


class TestMonotonicityGuardrail:
    def test_birthday_is_monotone(self) -> None:
        assert (
            advantage.count_monotonicity_issue(
                _clause("count_Samp * (count_Samp - 1) / (2 * |S|)")
            )
            is None
        )

    def test_linear_and_constant_are_monotone(self) -> None:
        assert advantage.count_monotonicity_issue(_clause("count_Samp / |S|")) is None
        assert advantage.count_monotonicity_issue(_clause("0")) is None
        assert advantage.count_monotonicity_issue(_clause("1 / (2 ^ |S|)")) is None

    def test_decreasing_bound_flagged_as_provably_decreasing(self) -> None:
        assert advantage.count_monotonicity_issue(_clause("1 / (count_Samp + 1)")) == (
            "count_Samp",
            True,
        )
        assert advantage.count_monotonicity_issue(_clause("|S| - count_Samp")) == (
            "count_Samp",
            True,
        )

    def test_non_monotone_helper_left_opaque_with_note(self) -> None:
        from proof_frog import frog_parser

        weird = frog_parser.parse_game_file(
            "Game A(Set S) { S Samp() { S v <- S; return v; } }\n"
            "Game B(Set S) { Set<S> seen; S Samp() { S v <-uniq[seen] S; return v; } }\n"
            "advantage <= 1 / (count_Samp + 1);\nexport as Weird;"
        )
        results = [
            _hop_result(
                1,
                "by_assumption",
                notion=_game("Weird", "Message"),
                reduction=_game("R"),
            )
        ]
        bound = advantage.synthesize_from_hop_results(
            results,
            definition_lookup={
                "Weird": weird,
                "R": _reduction("R", {"CTXT": ["Samp"]}),
            },
        )
        assert bound.render() == "Adv^Weird(Message)(B1)"
        assert len(bound.notes) == 1
        assert "decreases in count_Samp" in bound.notes[0]


def _parse_claim(src: str) -> frog_ast.Expression:
    """Parse a ``bound:`` expression via a minimal (parse-only) proof file."""
    pf = frog_parser.parse_proof_file(
        "proof:\n"
        "theorem:\n"
        "  Foo(E);\n"
        "bound:\n"
        f"  {src};\n"
        "games:\n"
        "  Foo(E).Left against Foo(E).Adversary;\n"
    )
    assert pf.claimed_bound is not None
    return pf.claimed_bound.bound


def _prf_reduction() -> frog_ast.ParameterizedGame:
    return frog_ast.ParameterizedGame(
        "R_PRF", [frog_ast.Variable("E"), frog_ast.Variable("F")]
    )


def _mixed_bound() -> advantage.AdvantageBound:
    """A synthesized bound: one opaque crypto term plus one birthday term.

    ``Adv^PRFSecurity(F)(R_PRF) + count_CTXT*(count_CTXT - 1)/|BitString<F.in>|``.
    """
    count = sympy.Symbol("count_CTXT", nonnegative=True)
    card = sympy.Symbol("|BitString<F.in>|", positive=True)
    birthday = count * (count - 1) / card
    prf_hop = advantage.HopInfo(
        "by_assumption", notion=_game("PRFSecurity", "F"), reduction=_prf_reduction()
    )
    birthday_hop = advantage.HopInfo(
        "by_assumption",
        notion=_game("DistinctSampling", "BitStringFin"),
        reduction=_game("R_Uniq", "E", "F"),
        statistical=birthday,
    )
    return advantage.synthesize_from_hops([prf_hop, birthday_hop])


class TestCheckClaimedBound:
    _ADV = "advantage(PRFSecurity(F) compose R_PRF(E, F))"
    _BIRTHDAY = "count_CTXT * (count_CTXT - 1) / |BitString<F.in>|"

    def test_exact_claim_verified(self) -> None:
        claim = _parse_claim(f"{self._ADV} + {self._BIRTHDAY}")
        assert advantage.check_claimed_bound(claim, _mixed_bound()).status == "verified"

    def test_bare_reduction_name_matches(self) -> None:
        # The synthesized reduction is R_PRF(E, F); a bare `R_PRF` in the claim
        # matches it by name.
        claim = _parse_claim(
            f"advantage(PRFSecurity(F) compose R_PRF) + {self._BIRTHDAY}"
        )
        assert advantage.check_claimed_bound(claim, _mixed_bound()).status == "verified"

    def test_loose_coefficient_verified(self) -> None:
        claim = _parse_claim(f"3 * {self._ADV} + {self._BIRTHDAY}")
        assert advantage.check_claimed_bound(claim, _mixed_bound()).status == "verified"

    def test_loose_statistical_verified(self) -> None:
        # count^2/|S| >= count(count-1)/|S|, so the claim is a valid upper bound.
        claim = _parse_claim(f"{self._ADV} + count_CTXT ^ 2 / |BitString<F.in>|")
        assert advantage.check_claimed_bound(claim, _mixed_bound()).status == "verified"

    def test_missing_statistical_term_not_verified(self) -> None:
        result = advantage.check_claimed_bound(_parse_claim(self._ADV), _mixed_bound())
        assert result.status == "not_verified"
        assert result.witness  # a concrete counterexample assignment

    def test_missing_advantage_term_not_verified(self) -> None:
        result = advantage.check_claimed_bound(
            _parse_claim(self._BIRTHDAY), _mixed_bound()
        )
        assert result.status == "not_verified"

    def test_unmatched_reference_is_slack_not_a_free_pass(self) -> None:
        # Referencing an adversary the proof never constructs adds slack but
        # cannot cover the omitted PRFSecurity term, so the claim fails.
        claim = _parse_claim(
            f"advantage(Other(X) compose R_PRF(E, F)) + {self._BIRTHDAY}"
        )
        assert (
            advantage.check_claimed_bound(claim, _mixed_bound()).status
            == "not_verified"
        )

    def test_symbolic_exponent_is_undecided(self) -> None:
        claim = _parse_claim(f"{self._ADV} + 2 ^ count_CTXT")
        assert advantage.check_claimed_bound(claim, _mixed_bound()).status == "undecided"

    def test_cardinality_name_mismatch_not_verified(self) -> None:
        # A differently-named cardinality does not cancel the synthesized term.
        claim = _parse_claim(f"{self._ADV} + count_CTXT * (count_CTXT - 1) / |S|")
        assert (
            advantage.check_claimed_bound(claim, _mixed_bound()).status != "verified"
        )

    def test_unsupported_synthesized_bound_is_undecided(self) -> None:
        unsupported = advantage.AdvantageBound(
            expression=sympy.Integer(0), terms={}, supported=False, note="inductive"
        )
        result = advantage.check_claimed_bound(_parse_claim(self._ADV), unsupported)
        assert result.status == "undecided"
