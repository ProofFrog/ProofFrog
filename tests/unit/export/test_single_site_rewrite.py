"""Unit tests for Move 2's single-site rewrite gate (pure row schemas).

Covers the four fact-free row schemas (Reflexive Comparison, Boolean
Identity, Simplify Nots, Tuple Equality Decompose) and the raw single-site
locator. The EC closers are pinned by
``tests/integration/ec_templates/single_site_rewrite.ec`` (probe-validated,
negative-controlled 2026-08-09).
"""

from proof_frog import frog_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _raw_single_site,
    _schema_bool_identity,
    _schema_reflexive,
    _schema_simplify_nots,
    _schema_tuple_neq,
)

OPS = frog_ast.BinaryOperators


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _eq(a: frog_ast.Expression, b: frog_ast.Expression) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(OPS.EQUALS, a, b)


def _neq(a: frog_ast.Expression, b: frog_ast.Expression) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(OPS.NOTEQUALS, a, b)


def _true() -> frog_ast.Boolean:
    return frog_ast.Boolean(True)


def _false() -> frog_ast.Boolean:
    return frog_ast.Boolean(False)


# --- Reflexive Comparison ---------------------------------------------------


def test_reflexive_eq_true_fires() -> None:
    assert _schema_reflexive(_eq(_var("x"), _var("x")), _true())


def test_reflexive_neq_false_fires() -> None:
    assert _schema_reflexive(_neq(_var("x"), _var("x")), _false())


def test_reflexive_declines_on_distinct_operands() -> None:
    assert not _schema_reflexive(_eq(_var("x"), _var("y")), _true())


def test_reflexive_declines_on_wrong_literal() -> None:
    assert not _schema_reflexive(_eq(_var("x"), _var("x")), _false())


# --- Boolean Identity ---------------------------------------------------------


def test_bool_identity_true_and_fires() -> None:
    lhs = frog_ast.BinaryOperation(OPS.AND, _true(), _var("p"))
    assert _schema_bool_identity(lhs, _var("p"))


def test_bool_identity_false_and_fires() -> None:
    lhs = frog_ast.BinaryOperation(OPS.AND, _var("p"), _false())
    assert _schema_bool_identity(lhs, _false())


def test_bool_identity_true_or_fires() -> None:
    lhs = frog_ast.BinaryOperation(OPS.OR, _var("p"), _true())
    assert _schema_bool_identity(lhs, _true())


def test_bool_identity_false_or_fires() -> None:
    lhs = frog_ast.BinaryOperation(OPS.OR, _false(), _var("p"))
    assert _schema_bool_identity(lhs, _var("p"))


def test_bool_identity_declines_without_literal() -> None:
    lhs = frog_ast.BinaryOperation(OPS.AND, _var("p"), _var("q"))
    assert not _schema_bool_identity(lhs, _var("p"))


def test_bool_identity_declines_on_wrong_result() -> None:
    lhs = frog_ast.BinaryOperation(OPS.AND, _true(), _var("p"))
    assert not _schema_bool_identity(lhs, _var("q"))


# --- Simplify Nots -----------------------------------------------------------


def test_simplify_nots_eq_to_neq_fires() -> None:
    lhs = frog_ast.UnaryOperation(
        frog_ast.UnaryOperators.NOT, _eq(_var("a"), _var("b"))
    )
    assert _schema_simplify_nots(lhs, _neq(_var("a"), _var("b")))


def test_simplify_nots_double_not_fires() -> None:
    inner = _eq(_var("a"), _var("b"))
    lhs = frog_ast.UnaryOperation(
        frog_ast.UnaryOperators.NOT,
        frog_ast.UnaryOperation(frog_ast.UnaryOperators.NOT, inner),
    )
    assert _schema_simplify_nots(lhs, inner)


def test_simplify_nots_declines_on_wrong_rhs() -> None:
    lhs = frog_ast.UnaryOperation(
        frog_ast.UnaryOperators.NOT, _eq(_var("a"), _var("b"))
    )
    assert not _schema_simplify_nots(lhs, _eq(_var("a"), _var("b")))


# --- Tuple Equality Decompose --------------------------------------------------


def _tup(*names: str) -> frog_ast.Tuple:
    return frog_ast.Tuple([_var(n) for n in names])


def test_tuple_neq_literal_fires() -> None:
    lhs = _neq(_var("t"), _tup("u", "v"))
    rhs = frog_ast.BinaryOperation(
        OPS.OR,
        _neq(
            frog_ast.ArrayAccess(_var("t"), frog_ast.Integer(0)), _var("u")
        ),
        _neq(
            frog_ast.ArrayAccess(_var("t"), frog_ast.Integer(1)), _var("v")
        ),
    )
    assert _schema_tuple_neq(lhs, rhs)


def test_tuple_neq_declines_on_incomplete_disjunction() -> None:
    lhs = _neq(_var("t"), _tup("u", "v"))
    rhs = _neq(frog_ast.ArrayAccess(_var("t"), frog_ast.Integer(0)), _var("u"))
    assert not _schema_tuple_neq(lhs, rhs)


def test_tuple_neq_declines_without_literal_arity_source() -> None:
    lhs = _neq(_var("t"), _var("s"))
    rhs = frog_ast.BinaryOperation(
        OPS.OR,
        _neq(
            frog_ast.ArrayAccess(_var("t"), frog_ast.Integer(0)),
            frog_ast.ArrayAccess(_var("s"), frog_ast.Integer(0)),
        ),
        _neq(
            frog_ast.ArrayAccess(_var("t"), frog_ast.Integer(1)),
            frog_ast.ArrayAccess(_var("s"), frog_ast.Integer(1)),
        ),
    )
    assert not _schema_tuple_neq(lhs, rhs)


# --- Raw single-site locator ---------------------------------------------------


def _method(statements: list[frog_ast.Statement]) -> frog_ast.Method:
    sig = frog_ast.MethodSignature("foo", _var("C"), [])
    return frog_ast.Method(sig, frog_ast.Block(statements))


def _assign(name: str, value: frog_ast.Expression) -> frog_ast.Assignment:
    return frog_ast.Assignment(_var("T"), _var(name), value)


def test_raw_single_site_return_diff() -> None:
    mb = _method([_assign("x", _var("k")), frog_ast.ReturnStatement(_true())])
    ma = _method([_assign("x", _var("k")), frog_ast.ReturnStatement(_false())])
    site = _raw_single_site(mb, ma)
    assert site is not None and site[0] == "return"


def test_raw_single_site_guard_diff() -> None:
    body = frog_ast.Block([frog_ast.ReturnStatement(_var("x"))])
    mb = _method(
        [frog_ast.IfStatement([_eq(_var("x"), _var("x"))], [body])]
    )
    ma = _method([frog_ast.IfStatement([_true()], [body])])
    site = _raw_single_site(mb, ma)
    assert site is not None and site[0] == "guard"


def test_raw_single_site_declines_on_two_diffs() -> None:
    mb = _method(
        [_assign("x", _var("k")), frog_ast.ReturnStatement(_true())]
    )
    ma = _method(
        [_assign("x", _var("j")), frog_ast.ReturnStatement(_false())]
    )
    assert _raw_single_site(mb, ma) is None


def test_raw_single_site_declines_on_branch_diff() -> None:
    body_b = frog_ast.Block([frog_ast.ReturnStatement(_var("x"))])
    body_a = frog_ast.Block([frog_ast.ReturnStatement(_var("y"))])
    mb = _method([frog_ast.IfStatement([_true()], [body_b])])
    ma = _method([frog_ast.IfStatement([_true()], [body_a])])
    assert _raw_single_site(mb, ma) is None


# --- End-to-end dispatch wiring (through _oracle_step_tactic) -----------------


from typing import Callable  # noqa: E402  pylint: disable=wrong-import-position,wrong-import-order

from proof_frog.export.easycrypt import module_translator as mt  # noqa: E402  pylint: disable=wrong-import-position
from proof_frog.export.easycrypt import type_collector as tc  # noqa: E402  pylint: disable=wrong-import-position
from proof_frog.export.easycrypt.chain_emitter import (  # noqa: E402  pylint: disable=wrong-import-position
    _oracle_step_tactic,
)


def _bs() -> frog_ast.BitStringType:
    return frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))


def _type_of_factory() -> Callable[
    [dict[str, frog_ast.Type], dict[str, str]],
    Callable[[frog_ast.Expression], frog_ast.Type],
]:
    def factory(
        _local: dict[str, frog_ast.Type], _mpt: dict[str, str]
    ) -> Callable[[frog_ast.Expression], frog_ast.Type]:
        def type_of(e: frog_ast.Expression) -> frog_ast.Type:
            if isinstance(e, frog_ast.Variable):
                return _bs()
            raise KeyError(e)

        return type_of

    return factory


def _guard_game(name: str, reflexive_guard: bool) -> frog_ast.Game:
    """Two-oracle game whose Challenge has one if whose guard is either
    ``x == x`` (before Reflexive Comparison) or ``true`` (after)."""
    field = frog_ast.Field(_bs(), "sk", None)
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", _bs(), []),
        frog_ast.Block([frog_ast.ReturnStatement(_var("sk"))]),
    )
    guard: frog_ast.Expression = (
        _eq(_var("x"), _var("x")) if reflexive_guard else _true()
    )
    chal = frog_ast.Method(
        frog_ast.MethodSignature(
            "Challenge", _bs(), [frog_ast.Parameter(_bs(), "m0")]
        ),
        frog_ast.Block(
            [
                frog_ast.Assignment(_bs(), _var("x"), _var("m0")),
                frog_ast.IfStatement(
                    [guard],
                    [
                        frog_ast.Block(
                            [frog_ast.Assignment(None, _var("x"), _var("sk"))]
                        )
                    ],
                ),
                frog_ast.ReturnStatement(_var("x")),
            ]
        ),
    )
    return frog_ast.Game((name, [], [field], [init, chal]))


def test_dispatch_fires_on_reflexive_guard_leg() -> None:
    gb, ga = _guard_game("GB", True), _guard_game("GA", False)
    step = _oracle_step_tactic(
        gb,
        ga,
        "challenge",
        False,
        {},
        {},
        modules=mt.ModuleTranslator(tc.TypeCollector(aliases={}), _type_of_factory()),
        flat_params=[],
        det_methods={},
        micro_pre_text="={m0} /\\ (glob GB){1} = (glob GA){2}",
    )
    assert step is not None
    tac, reqs, rung = step
    assert rung == "synth-param"
    assert any(t.startswith("if; [smt()") for t in tac)
    assert not reqs.pres and not reqs.inj


def test_dispatch_declines_reflexive_guard_on_init_pre() -> None:
    gb, ga = _guard_game("GB", True), _guard_game("GA", False)
    step = _oracle_step_tactic(
        gb,
        ga,
        "challenge",
        False,
        {},
        {},
        modules=mt.ModuleTranslator(tc.TypeCollector(aliases={}), _type_of_factory()),
        flat_params=[],
        det_methods={},
        micro_pre_text="true",
    )
    assert step is None
