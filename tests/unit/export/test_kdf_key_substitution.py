"""Unit tests for the KDF-key-substitution route's pure planners.

``_synth_kdf_key_substitution`` closes the IND-CCA `initialize` hop where one
endpoint derives the KDF key by ENCODING a challenger-drawn shared secret and
the other draws it directly. Everything structural about that hop is read off
the first flat states; the NAMES are not, and the pieces tested here are the
ones that bridge the two worlds plus the ones that were quietly wrong the first
time round.

Each test below corresponds to a defect the real export exposed and a unit test
would have caught earlier:

* ``_resolve_expr`` swallowed the dot in ``t.`2`` (its identifier pattern ended
  ``[\\w.]*``), so every projection stayed unresolved -- a SILENT miss, since a
  failed lookup just leaves the token in place;
* it also could not fold a projection whose base was a substituted tuple
  LITERAL, because ``_projections`` only recognises a bare identifier base;
* substituting a variable whose value was an application spliced that
  application's arguments into the enclosing one, changing its arity;
* ``_flat_name_map`` is the flat-state-to-EasyCrypt bridge: the canonicalizer
  flattens a reduction's state and its inlined delegate's into one field list
  (marking the delegate's ``<obj>@<f>``) while EasyCrypt keeps them qualified by
  owning module.

End-to-end rendering + EC compilation is covered by the pinned script
``ec_templates/PARKED_indcca_hop5_kdf_key_substitution.ec.txt`` and by compiling
the real `CG_expanded_INDCCA_PQ` / `UG_expanded_INDCCA_PQ` exports.
"""

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _app_args,
    _assign_env,
    _concat_chain,
    _flat_name_map,
    _kdf_holder,
    _module_head,
    _real_name,
    _resolve_expr,
    _wrapper_delegate,
)


# --- the resolver -----------------------------------------------------------


def test_resolve_folds_a_projection_of_a_substituted_tuple() -> None:
    """``ss_PQ`` -> ``_tup.`2`` -> ``(ek, ssStar, ct).`2`` -> ``ssStar``.

    This is the exact chain the real hop needs: the coupled draw reaches the
    encoding call through a tuple repack, and stopping anywhere short of
    ``ssStar`` leaves the route unable to find the sample it must couple.
    """
    env = {"_tup": "(ek, ssStar, ct)", "ss_PQ": "_tup.`2"}
    assert _resolve_expr("ss_PQ", _resolve_env(env)) == "ssStar"


def _resolve_env(raw: dict[str, str]) -> dict[str, str]:
    """Resolve an env the way :func:`_assign_env` does, in insertion order."""
    out: dict[str, str] = {}
    for var, rhs in raw.items():
        out[var] = _resolve_expr(rhs, out)
    return out


def test_resolve_does_not_swallow_the_dot_before_a_projection() -> None:
    """A qualified-identifier pattern ending ``[\\w.]*`` matches ``_tup.`` and so
    looks up a key that never exists -- the miss is silent."""
    env = {"_tup": "(a, b)"}
    assert _resolve_expr("_tup.`1", env) == "a"


def test_resolve_parenthesizes_a_substituted_application() -> None:
    """Splicing ``f x y`` into an argument position must not change the arity of
    the enclosing application."""
    env = _resolve_env({"rest": "cat3 (cat2 s e1) e2"})
    got = _resolve_expr("pre k rest", env)
    assert _app_args(got) == ["pre", "k", "(cat3 (cat2 s e1) e2)"]


def test_assign_env_leaves_backbone_results_unresolved() -> None:
    """Calls and samples are the LEAVES: resolution must bottom out at a
    backbone event, which is the only cross-side-comparable vocabulary."""
    env = _assign_env(
        [
            ec_ast.Call("t", "K.keygen", ""),
            ec_ast.Assign("ek", "t.`1"),
            ec_ast.Sample("s", "dbs"),
            ec_ast.Assign("packed", "(ek, s)"),
        ]
    )
    assert env["ek"] == "t.`1"
    assert env["packed"] == "(t.`1, s)"
    assert "t" not in env and "s" not in env


# --- the concat chain -------------------------------------------------------


def test_concat_chain_reads_a_left_nested_bracketing() -> None:
    ops = {"c1", "c2", "c3"}
    got = _concat_chain("c3 (c2 (c1 a b) c) d", ops)
    assert got == (["c1", "c2", "c3"], ["a", "b", "c", "d"])


def test_concat_chain_declines_a_bare_leaf() -> None:
    assert _concat_chain("x", {"c1"}) is None


def test_concat_chain_declines_a_foreign_head() -> None:
    """A route that accepted any head would request a regrouping law for an
    expression that is not a concat chain at all."""
    assert _concat_chain("h (c1 a b) c", {"c1"}) is None


# --- the flat-state to EasyCrypt name bridge --------------------------------


def _state(field_names: list[str]) -> frog_ast.Game:
    """A flat state carrying only what the name bridge reads: its field list."""
    fields = [
        frog_ast.Field(frog_ast.BoolType(), n, None)
        for n in field_names
    ]
    return frog_ast.Game(("Flat", [], fields, []))


def test_flat_name_map_splits_reduction_state_from_delegate_state() -> None:
    """``challenger@k`` belongs to the inlined delegate and is qualified by the
    CHALLENGER module; a bare field belongs to the reduction."""
    mapping, delegate = _flat_name_map(
        _state(["ss_PQ", "challenger@k"]), "RB", "H_c.KDFPRFSec_Real"
    )
    assert mapping == {
        "ss_PQ": "RB.ss_PQ",
        "challenger_k": "H_c.KDFPRFSec_Real.k",
    }
    assert delegate == "challenger"


def test_real_name_declines_a_delegate_local() -> None:
    """EasyCrypt renames the delegate's inlined LOCALS outright, so there is no
    correspondence to return -- the route must drop the conjunct rather than
    emit a name that will not resolve."""
    mapping, delegate = _flat_name_map(_state(["challenger@k"]), "RB", "C")
    assert _real_name("challenger_Initialize_ssStar0", mapping, delegate) is None
    assert _real_name("ss_T", mapping, delegate) == "ss_T"


def test_real_name_keeps_reduction_locals_unchanged() -> None:
    """A reduction's own locals survive ``inline *`` under their own names, so
    they need no qualification."""
    mapping, delegate = _flat_name_map(_state(["seed_T"]), "RD", "C")
    assert _real_name("_r3", mapping, delegate) == "_r3"
    assert _real_name("seed_T", mapping, delegate) == "RD.seed_T"


def test_flat_name_map_lowercases_an_uppercase_initial() -> None:
    """EC module globals are lowercase-initial, matching the field rename
    ``module_translator`` already applies (``RF`` -> ``rF``)."""
    mapping, _ = _flat_name_map(_state(["RF", "challenger@K"]), "R", "C")
    assert mapping == {"rF": "R.rF", "challenger_K": "C.k"}


# --- the wrapper expression -------------------------------------------------


def test_wrapper_bases_come_from_the_module_expression() -> None:
    expr = "RB(KEM_PQ, NG, CG(KEM_PQ, NG), KEM_PQ_c.KEM_INDCCA_Random(KEM_PQ))"
    assert _module_head(expr) == "RB"
    assert _wrapper_delegate(expr) == "KEM_PQ_c.KEM_INDCCA_Random"


def test_wrapper_delegate_ignores_nested_argument_commas() -> None:
    """The delegate is the LAST top-level argument; a nested application's
    commas must not split it."""
    assert _wrapper_delegate("R(A, B(c, d), Chal(e, f))") == "Chal"


def test_wrapper_delegate_empty_for_an_unapplied_module() -> None:
    assert _wrapper_delegate("R") == ""


# --- the nameable holder ----------------------------------------------------


def test_holder_picks_a_nameable_variable_over_a_delegate_local() -> None:
    """The coupled draw itself is a delegate local; the value it produced is
    also held by a reduction field, and that is what the coupling must name.

    Note the fixture carries an ``@`` field: that is the ONLY thing that reveals
    the delegate's name, and without it the two kinds of local are
    indistinguishable -- which is why the route declines outright in that case
    (see :func:`test_holder_cannot_reject_a_local_without_an_at_field`).
    """
    canon = {"challenger_Initialize_ssStar0": "#2", "ss_PQ": "#2", "other": "#3"}
    mapping, delegate = _flat_name_map(_state(["ss_PQ", "challenger@dk"]), "RB", "C")
    assert (
        _kdf_holder(canon, "#2", lambda v: _real_name(v, mapping, delegate))
        == "RB.ss_PQ"
    )


def test_holder_is_none_when_only_delegate_locals_hold_the_value() -> None:
    """Honest gating: with nothing nameable holding the coupled value the route
    has to decline, not guess a name."""
    canon = {"challenger_Initialize_ssStar0": "#2"}
    mapping, delegate = _flat_name_map(_state(["challenger@k"]), "RB", "C")
    assert _kdf_holder(canon, "#2", lambda v: _real_name(v, mapping, delegate)) is None


def test_holder_cannot_reject_a_local_without_an_at_field() -> None:
    """Pins WHY the route requires an ``@``-marked field on both sides.

    With no delegate field the prefix is unknown, so a delegate-inlined local
    resolves to itself -- a name EasyCrypt does not have. The route's gate turns
    that into a decline; this test exists so that gate is not quietly dropped as
    redundant.
    """
    mapping, delegate = _flat_name_map(_state(["ss_PQ"]), "RB", "C")
    assert delegate == ""
    assert (
        _real_name("challenger_Initialize_ssStar0", mapping, delegate)
        == "challenger_Initialize_ssStar0"
    )
