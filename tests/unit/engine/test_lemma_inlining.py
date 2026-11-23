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
    name_map: dict[str, str] | None = None,
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
        theorem=theorem,
        bound=advantage.synthesize_from_hops(hops),
        lets=lets,
        name_map={k: frog_ast.Variable(v) for k, v in (name_map or {}).items()},
    )


def test_opaque_term_renamed_into_parent() -> None:
    lemma = _lemma(
        _game("N", "T"), [(_game("P", "T"), "R_in", None)], _lets("    Set T;"), {"T": "S"}
    )
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
        {"T": "S"},
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
        {"T": "S"},
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
        {"T": "S"},
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
        {"G": "G2", "k": "m"},
    )
    bound = advantage.synthesize_from_hop_results(
        [_hop("by_lemma", _game("N", "G2"), None)],
        definition_lookup={},
        lemma_bounds={"N(G2)": lemma},
    )
    assert bound.render() == "1/|BitString<m>|"


def test_raw_form_without_lemma_bounds_is_unchanged() -> None:
    bound = advantage.synthesize_from_hop_results(
        [_hop("by_lemma", _game("N", "S"), "R_out")],
        definition_lookup={},
    )
    assert bound.render() == "Adv^N(S)(B1)"


def _instantiate(lemma_lets: str, lemma_args: list[str], parent_lets: str, parent_args: list[str]):
    return advantage.lemma_instantiation(
        [frog_ast.Variable(a) for a in lemma_args],
        _lets(lemma_lets),
        frozenset(),
        [frog_ast.Variable(a) for a in parent_args],
        _lets(parent_lets),
        frozenset(),
    )


def test_instantiation_maps_abstract_parameters() -> None:
    result = _instantiate("    Set T;", ["T"], "    Set S;", ["S"])
    assert isinstance(result, advantage.LemmaInstantiation)
    assert str(result.name_map["T"]) == "S"


def test_instantiation_through_primitive_with_expression_arguments() -> None:
    result = _instantiate(
        "    Int n;\n    Set C;\n    KEM K = KEM(n, BitString<n>, C);",
        ["K"],
        "    Int m;\n    Set D;\n    KEM K2 = KEM(m, BitString<m>, D);",
        ["K2"],
    )
    assert isinstance(result, advantage.LemmaInstantiation)
    assert {k: str(v) for k, v in result.name_map.items()} == {
        "K": "K2",
        "n": "m",
        "C": "D",
    }
    assert result.callees == {"KEM"}


def test_instantiation_rejects_shape_mismatch() -> None:
    # The lemma is only about KEMs whose shared secrets are bitstrings.
    result = _instantiate(
        "    Int n;\n    Set C;\n    KEM K = KEM(n, BitString<n>, C);",
        ["K"],
        "    Int m;\n    Set D;\n    Set E;\n    KEM K2 = KEM(m, E, D);",
        ["K2"],
    )
    assert isinstance(result, str)


def test_instantiation_rejects_diagonal() -> None:
    result = _instantiate("    Set T;", ["T", "T"], "    Set A;\n    Set B;", ["A", "B"])
    assert isinstance(result, str)


def test_instantiation_rejects_concrete_lemma_parameter() -> None:
    result = _instantiate("    Set U = BitString<8>;", ["U"], "    Set S;", ["S"])
    assert isinstance(result, str)


def test_instantiation_rejects_abstract_parent_for_instantiated_lemma() -> None:
    # The lemma holds only for KEM(n); an arbitrary parent KEM is not an instance.
    result = _instantiate("    Int n;\n    KEM K = KEM(n);", ["K"], "    KEM K2;", ["K2"])
    assert isinstance(result, str)


def test_instantiation_binds_set_parameter_to_type() -> None:
    result = _instantiate(
        "    Int n;\n    Set C;\n    KEM K = KEM(n, C);",
        ["K"],
        "    Int m;\n    KEM K2 = KEM(m, BitString<m>);",
        ["K2"],
    )
    assert isinstance(result, advantage.LemmaInstantiation), result
    assert str(result.name_map["C"]) == "BitString<m>"


def _instantiate_sampled(lemma_lets, lemma_sampled, lemma_args, parent_lets, parent_sampled, parent_args):
    return advantage.lemma_instantiation(
        [frog_ast.Variable(a) for a in lemma_args],
        _lets(lemma_lets),
        frozenset(lemma_sampled),
        [frog_ast.Variable(a) for a in parent_args],
        _lets(parent_lets),
        frozenset(parent_sampled),
    )


def test_instantiation_rejects_merging_independent_sampled_parameters() -> None:
    """Two independently sampled lemma functions cannot both be one parent
    function: the lemma says nothing about the correlated case."""
    result = _instantiate_sampled(
        "    Function<Int, Int> F1;\n    Function<Int, Int> F2;",
        {"F1", "F2"},
        ["F1", "F2"],
        "    Function<Int, Int> H;",
        {"H"},
        ["H", "H"],
    )
    assert isinstance(result, str)


def test_instantiation_rejects_abstract_parameter_depending_on_sampled() -> None:
    """An abstract lemma parameter ranges over values independent of the
    lemma's random functions; the parent's image built from one is not."""
    result = _instantiate_sampled(
        "    Function<Int, Int> F1;\n    Int E;",
        {"F1"},
        ["F1", "E"],
        "    Function<Int, Int> H;\n    Int k;",
        {"H"},
        ["H", "k"],
    )
    assert isinstance(result, advantage.LemmaInstantiation)
    bad = advantage.lemma_instantiation(
        [frog_ast.Variable("F1"), frog_ast.Variable("E")],
        _lets("    Function<Int, Int> F1;\n    Int E;"),
        frozenset({"F1"}),
        [
            frog_ast.Variable("H"),
            frog_ast.FuncCall(frog_ast.Variable("H"), [frog_ast.Integer(0)]),
        ],
        _lets("    Function<Int, Int> H;"),
        frozenset({"H"}),
    )
    assert isinstance(bad, str)


def test_instantiation_maps_sampled_parameters_one_to_one() -> None:
    result = _instantiate_sampled(
        "    Function<Int, Int> F1;\n    Function<Int, Int> F2;",
        {"F1", "F2"},
        ["F1", "F2"],
        "    Function<Int, Int> H1;\n    Function<Int, Int> H2;",
        {"H1", "H2"},
        ["H1", "H2"],
    )
    assert isinstance(result, advantage.LemmaInstantiation)


def _literal_lets(literal: int, name: str) -> list[frog_ast.Field]:
    return _lets(f"    Int n;\n    Set C;\n    KEM {name} = KEM(n, BitString<{literal}>, C);")


def _hash_literal(lets: list[frog_ast.Field]) -> frog_ast.Integer:
    """Compare the literal of ``BitString<literal>`` once, which caches its
    structural hash, as any earlier ``==`` in the lemma's own run would."""
    value = lets[2].value
    assert isinstance(value, frog_ast.FuncCall)
    bitstring = value.args[1]
    assert isinstance(bitstring, frog_ast.BitStringType)
    literal = bitstring.parameterization
    assert isinstance(literal, frog_ast.Integer)
    assert literal == frog_ast.Integer(literal.num)
    return literal


def test_instantiation_ignores_cached_leaf_hash_on_lemma_side() -> None:
    """A lemma-side literal whose structural hash is cached must still match
    the parent's equal literal, whose hash is not: the cache is not an
    attribute of the node, so the generic attribute walk must not see it."""
    lemma_lets = _literal_lets(2, "K")
    parent_lets = _literal_lets(2, "K2")
    _hash_literal(lemma_lets)
    result = advantage.lemma_instantiation(
        [frog_ast.Variable("K")],
        lemma_lets,
        frozenset(),
        [frog_ast.Variable("K2")],
        parent_lets,
        frozenset(),
    )
    assert isinstance(result, advantage.LemmaInstantiation), result


def test_instantiation_ignores_cached_leaf_hash_on_parent_side() -> None:
    lemma_lets = _literal_lets(2, "K")
    parent_lets = _literal_lets(2, "K2")
    _hash_literal(parent_lets)
    result = advantage.lemma_instantiation(
        [frog_ast.Variable("K")],
        lemma_lets,
        frozenset(),
        [frog_ast.Variable("K2")],
        parent_lets,
        frozenset(),
    )
    assert isinstance(result, advantage.LemmaInstantiation), result


def test_instantiation_still_rejects_different_literals_when_hashed() -> None:
    for hash_lemma, hash_parent in [(False, False), (True, False), (True, True)]:
        lemma_lets = _literal_lets(2, "K")
        parent_lets = _literal_lets(3, "K2")
        if hash_lemma:
            _hash_literal(lemma_lets)
        if hash_parent:
            _hash_literal(parent_lets)
        result = advantage.lemma_instantiation(
            [frog_ast.Variable("K")],
            lemma_lets,
            frozenset(),
            [frog_ast.Variable("K2")],
            parent_lets,
            frozenset(),
        )
        assert isinstance(result, str)
        assert "does not match" in result


def _instantiate_nodes(
    lemma_lets: str,
    lemma_args: list[str],
    parent_lets: str,
    parent_args: list[frog_ast.Expression],
):
    return advantage.lemma_instantiation(
        [frog_ast.Variable(a) for a in lemma_args],
        _lets(lemma_lets),
        frozenset(),
        parent_args,
        _lets(parent_lets),
        frozenset(),
    )


def test_instantiation_rejects_optional_type_for_abstract_set() -> None:
    """F-417: a lemma proved for an abstract set reads its values as never
    None, so it holds only for sets without None."""
    result = _instantiate(
        "    Int n;\n    Set C;\n    KEM K = KEM(n, C);",
        ["K"],
        "    Int m;\n    KEM K2 = KEM(m, BitString<m>?);",
        ["K2"],
    )
    assert isinstance(result, str)
    assert "its set C would stand for the optional type BitString<m>?" in result


def test_instantiation_rejects_optional_type_through_parent_alias() -> None:
    result = _instantiate(
        "    Int n;\n    Set C;\n    KEM K = KEM(n, C);",
        ["K"],
        "    Int m;\n    Set D = BitString<m>?;\n    KEM K2 = KEM(m, D);",
        ["K2"],
    )
    assert isinstance(result, str)
    assert "its set C would stand for the optional type BitString<m>?" in result


def test_instantiation_rejects_optional_component_for_abstract_set() -> None:
    """A set bound inside a product type: the product is not optional, but
    the component the lemma's set stands for is."""
    result = _instantiate(
        "    Int n;\n    Set C;\n    KEM K = KEM(n, [C, Bool]);",
        ["K"],
        "    Int m;\n    KEM K2 = KEM(m, [BitString<m>?, Bool]);",
        ["K2"],
    )
    assert isinstance(result, str)
    assert "its set C would stand for the optional type BitString<m>?" in result


def test_instantiation_binds_set_to_type_with_optional_component() -> None:
    """A product with an optional component is not itself optional."""
    result = _instantiate(
        "    Int n;\n    Set C;\n    KEM K = KEM(n, C);",
        ["K"],
        "    Int m;\n    KEM K2 = KEM(m, [BitString<m>?, Bool]);",
        ["K2"],
    )
    assert isinstance(result, advantage.LemmaInstantiation), result


def test_instantiation_rejects_constant_of_a_wider_type() -> None:
    """F-419: the lemma holds for every c of type J; with J = Bool, the
    parent's c2 of type Bool? may be None, which no c of type Bool is."""
    result = _instantiate_nodes(
        "    Set J;\n    J c;",
        ["J", "c"],
        "    Bool? c2;",
        [frog_ast.BoolType(), frog_ast.Variable("c2")],
    )
    assert isinstance(result, str)
    assert "its constant c of type J would stand for c2 of type Bool?" in result


def test_instantiation_rejects_constant_of_a_wider_type_bound_first() -> None:
    """The same, with the constant matched before the set it is typed by."""
    result = _instantiate_nodes(
        "    Set J;\n    J c;",
        ["c", "J"],
        "    Bool? c2;",
        [frog_ast.Variable("c2"), frog_ast.BoolType()],
    )
    assert isinstance(result, str)


def test_instantiation_rejects_set_bound_to_optional_through_a_constant() -> None:
    """A set that only a constant's type binds: J would stand for Bool?."""
    result = _instantiate_nodes(
        "    Set J;\n    J c;",
        ["c"],
        "    Bool? c2;",
        [frog_ast.Variable("c2")],
    )
    assert isinstance(result, str)
    assert "its set J would stand for the optional type Bool?" in result


def test_instantiation_rejects_constant_bound_to_other_expression() -> None:
    result = _instantiate_nodes(
        "    Set J;\n    J c;",
        ["J", "c"],
        "",
        [frog_ast.BoolType(), frog_ast.NoneExpression()],
    )
    assert isinstance(result, str)
    assert "its constant c would stand for None" in result


def test_instantiation_maps_constant_of_the_same_type() -> None:
    result = _instantiate_nodes(
        "    Set J;\n    J c;",
        ["J", "c"],
        "    Bool c2;",
        [frog_ast.BoolType(), frog_ast.Variable("c2")],
    )
    assert isinstance(result, advantage.LemmaInstantiation), result
    assert {k: str(v) for k, v in result.name_map.items()} == {
        "J": "Bool",
        "c": "c2",
    }


def test_instantiation_binds_through_a_constant_type() -> None:
    """A constant's type binds the lemma names it mentions."""
    result = _instantiate(
        "    Int n;\n    BitString<n> b;",
        ["b"],
        "    Int m;\n    BitString<m> b2;",
        ["b2"],
    )
    assert isinstance(result, advantage.LemmaInstantiation), result
    assert {k: str(v) for k, v in result.name_map.items()} == {"b": "b2", "n": "m"}


def test_instantiation_reads_parent_constant_type_through_alias() -> None:
    result = _instantiate(
        "    Int n;\n    BitString<n> b;",
        ["b"],
        "    Int m;\n    Set K = BitString<m>;\n    K b2;",
        ["b2"],
    )
    assert isinstance(result, advantage.LemmaInstantiation), result


def test_instantiation_maps_int_constant_to_integer_expression() -> None:
    """An Int constant may stand for an integer expression of the parent:
    every such expression is an Int."""
    result = _instantiate_nodes(
        "    Int n;\n    KEM K = KEM(n);",
        ["K"],
        "    Int m;\n    KEM K2 = KEM(m + 1);",
        [frog_ast.Variable("K2")],
    )
    assert isinstance(result, advantage.LemmaInstantiation), result
    assert str(result.name_map["n"]) == "m + 1"
    literal = _instantiate_nodes(
        "    Int n;\n    KEM K = KEM(n);",
        ["K"],
        "    KEM K2 = KEM(128);",
        [frog_ast.Variable("K2")],
    )
    assert isinstance(literal, advantage.LemmaInstantiation), literal


def test_instantiation_maps_group_constant() -> None:
    result = _instantiate("    Group G;", ["G"], "    Group H;", ["H"])
    assert isinstance(result, advantage.LemmaInstantiation), result


def test_instantiation_rejects_none_for_abstract_set() -> None:
    """F-421: `None` is a value, not a type; a lemma proved for an abstract
    set reads its values as never None."""
    result = _instantiate(
        "    Int n;\n    Set C;\n    KEM K = KEM(n, C);",
        ["K"],
        "    Int m;\n    KEM K2 = KEM(m, None);",
        ["K2"],
    )
    assert isinstance(result, str)
    assert "its set C would stand for None" in result
