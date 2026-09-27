"""Lemma-bound inlining: a verified lemma's bound replaces its opaque term."""

import sympy

from proof_frog import advantage, frog_ast, frog_parser, proof_engine


def _game(name: str, *args: str) -> frog_ast.ParameterizedGame:
    return frog_ast.ParameterizedGame(name, [frog_ast.Variable(a) for a in args])


def _call(oracle: str) -> frog_ast.FuncCall:
    return frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("challenger"), oracle), []
    )


def _reduction(name: str, methods: dict[str, list[str]]) -> frog_ast.Reduction:
    return frog_ast.Reduction(
        (
            name,
            [],
            [],
            [
                frog_ast.Method(
                    frog_ast.MethodSignature(m, frog_ast.Void(), []),
                    frog_ast.Block([_call(c) for c in calls]),
                )
                for m, calls in methods.items()
            ],
        ),
        _game("N"),
        _game("Th"),
    )


def _hop(kind: str, notion: frog_ast.ParameterizedGame, reduction: str | None):
    return proof_engine.HopResult(
        step_num=1,
        valid=True,
        kind=kind,
        depth=0,
        current_desc="",
        next_desc="",
        justification=notion,
        reduction=_game(reduction, "S") if reduction else None,
    )


def _lets(src: str) -> list[frog_ast.Field]:
    pf = frog_parser.parse_string(
        f"proof:\nlet:\n{src}\ntheorem:\n    N(S);\ngames:\n    N(S).L against N(S).Adversary;\n",
        frog_ast.FileType.PROOF,
    )
    return pf.lets


def _lemma(
    theorem: frog_ast.ParameterizedGame,
    terms: list[tuple[frog_ast.ParameterizedGame, str | None, sympy.Expr | None]],
    lets: list[frog_ast.Field],
) -> advantage.LemmaBound:
    hops = [
        advantage.HopInfo(
            kind="by_assumption",
            notion=notion,
            reduction=_game(red) if red else None,
            statistical=stat,
        )
        for notion, red, stat in terms
    ]
    return advantage.LemmaBound(
        theorem=theorem, bound=advantage.synthesize_from_hops(hops), lets=lets
    )


def test_opaque_term_renamed_into_parent() -> None:
    lemma = _lemma(_game("N", "T"), [(_game("P", "T"), "R_in", None)], _lets("    Set T;"))
    bound = advantage.synthesize_from_hop_results(
        [_hop("by_lemma", _game("N", "S"), "R_out")],
        definition_lookup={"R_out": _reduction("R_out", {"O": ["X"]})},
        lemma_bounds={"N(S)": lemma},
    )
    assert bound.render() == "Adv^P(S)(B1)"


def test_counts_rederived_through_parent_reduction() -> None:
    count_x = sympy.Symbol("count_X", nonnegative=True)
    t_size = sympy.Symbol("|T|", positive=True)
    lemma = _lemma(
        _game("N", "T"),
        [(_game("H", "T"), "R_in", count_x / t_size)],
        _lets("    Set T;"),
    )
    bound = advantage.synthesize_from_hop_results(
        [_hop("by_lemma", _game("N", "S"), "R_out")],
        definition_lookup={"R_out": _reduction("R_out", {"CTXT": ["X", "X"]})},
        lemma_bounds={"N(S)": lemma},
    )
    assert bound.render() == "2*count_CTXT/|S|"


def test_upto_reveal_count_pinned_to_one() -> None:
    count_reveal = sympy.Symbol("count___reveal", nonnegative=True)
    lemma = _lemma(
        _game("P#event#bad", "T"),
        [(_game("H", "T"), None, count_reveal / 4)],
        _lets("    Set T;"),
    )
    bound = advantage.synthesize_from_hop_results(
        [_hop("by_upto", _game("P#event#bad", "S"), "R_out")],
        definition_lookup={"R_out": _reduction("R_out", {"O": ["X"]})},
        lemma_bounds={"P#event#bad(S)": lemma},
    )
    assert bound.render() == "1/4"


def test_unmapped_lemma_local_keeps_term_opaque() -> None:
    # |BitString<k>| names a lemma-local parameter the theorem does not fix.
    size = sympy.Symbol("|BitString<k>|", positive=True)
    lemma = _lemma(
        _game("N", "T"),
        [(_game("H", "T"), None, 1 / size)],
        _lets("    Set T;\n    Int k;"),
    )
    bound = advantage.synthesize_from_hop_results(
        [_hop("by_lemma", _game("N", "S"), None)],
        definition_lookup={},
        lemma_bounds={"N(S)": lemma},
    )
    assert bound.render() == "Adv^N(S)(A)"
    assert any("k" in note for note in bound.notes)


def test_primitive_parameters_mapped_through_instantiations() -> None:
    size = sympy.Symbol("|BitString<k>|", positive=True)
    lemma = _lemma(
        _game("N", "G"),
        [(_game("H", "G"), None, 1 / size)],
        _lets("    Int k;\n    PRG G = PRG(k);"),
    )
    bound = advantage.synthesize_from_hop_results(
        [_hop("by_lemma", _game("N", "G2"), None)],
        definition_lookup={},
        lemma_bounds={"N(G2)": lemma},
        parent_lets=_lets("    Int m;\n    PRG G2 = PRG(m);"),
    )
    assert bound.render() == "1/|BitString<m>|"


def test_raw_form_without_lemma_bounds_is_unchanged() -> None:
    bound = advantage.synthesize_from_hop_results(
        [_hop("by_lemma", _game("N", "S"), "R_out")],
        definition_lookup={},
    )
    assert bound.render() == "Adv^N(S)(B1)"
