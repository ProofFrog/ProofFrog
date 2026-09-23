"""HoistDeterministicCallToInitialize sees through stable oracle locals.

CSE leaves ``NGElementSpace g = NG.Generator();`` in an oracle and reuses
``g`` in ``NG.Exp(g, x)``. Before this fix such a call was never hoisted
(its argument ``g`` is a local, not a field), while the same call was
aliased to an existing field by CrossMethodFieldAlias when some other
method happened to cache it; the two sides of a hop could therefore
canonicalize differently (one side with ``NG.Encode(ek_T)`` hoisted into a
field, the other recomputing it). The pass now expands top-level
single-assignment stable locals, hoists the expanded call, and rewrites
the oracle occurrence.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import (
    HoistDeterministicCallToInitializeTransformer,
)


def _make_group_namespace() -> frog_ast.Namespace:
    prim = frog_parser.parse_primitive_file("""
        Primitive NominalGroup(Set ElementSpace, Set ScalarSpace) {
            Set Element = ElementSpace;
            Set Scalar = ScalarSpace;
            deterministic Element Exp(Element base, Scalar exp);
            deterministic Element Generator();
        }
        """)
    return {"NominalGroup": prim, "NG": prim}


def _hoisted_field(result: frog_ast.Game, original: frog_ast.Game) -> str | None:
    original_names = {f.name for f in original.fields}
    new = [f.name for f in result.fields if f.name not in original_names]
    assert len(new) <= 1
    return new[0] if new else None


def test_call_through_stable_local_alias_is_hoisted() -> None:
    """``g = NG.Generator(); return NG.Exp(g, x);`` caches ``NG.Exp(NG.Generator(), x)``."""
    game = frog_parser.parse_game("""
        Game Foo(NominalGroup NG) {
            NG.Scalar x;
            Void Initialize() {
                x <- NG.Scalar;
            }
            NG.Element Get() {
                NG.Element g = NG.Generator();
                return NG.Exp(g, x);
            }
        }
        """)
    result = HoistDeterministicCallToInitializeTransformer(
        proof_namespace=_make_group_namespace()
    ).transform(game)

    name = _hoisted_field(result, game)
    assert name is not None
    init = result.methods[0]
    last = init.block.statements[-1]
    assert isinstance(last, frog_ast.Assignment)
    assert last.var == frog_ast.Variable(name)
    # Hoisted in alias-expanded form: Initialize must not mention the
    # oracle-local ``g``.
    assert last.value == frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("NG"), "Exp"),
        [
            frog_ast.FuncCall(frog_ast.FieldAccess(frog_ast.Variable("NG"), "Generator"), []),
            frog_ast.Variable("x"),
        ],
    )
    ret = result.methods[1].block.statements[-1]
    assert isinstance(ret, frog_ast.ReturnStatement)
    assert ret.expression == frog_ast.Variable(name)


def test_existing_field_through_initialize_alias_is_not_rehoisted() -> None:
    """Initialize already caches the call through its own local alias."""
    game = frog_parser.parse_game("""
        Game Foo(NominalGroup NG) {
            NG.Scalar x;
            NG.Element ek;
            Void Initialize() {
                NG.Element g = NG.Generator();
                x <- NG.Scalar;
                ek = NG.Exp(g, x);
            }
            NG.Element Get() {
                NG.Element h = NG.Generator();
                return NG.Exp(h, x);
            }
        }
        """)
    result = HoistDeterministicCallToInitializeTransformer(
        proof_namespace=_make_group_namespace()
    ).transform(game)
    # ``ek`` already holds NG.Exp(NG.Generator(), x); reusing it is
    # CrossMethodFieldAlias's job, so no new field is created here.
    assert _hoisted_field(result, game) is None


def test_sampled_local_is_not_a_stable_alias() -> None:
    """A per-call sampled local is coin-dependent: the call must stay put."""
    game = frog_parser.parse_game("""
        Game Foo(NominalGroup NG) {
            NG.Scalar x;
            Void Initialize() {
                x <- NG.Scalar;
            }
            NG.Element Get() {
                NG.Element g <- NG.Element;
                return NG.Exp(g, x);
            }
        }
        """)
    result = HoistDeterministicCallToInitializeTransformer(
        proof_namespace=_make_group_namespace()
    ).transform(game)
    assert _hoisted_field(result, game) is None


def test_reassigned_local_is_not_a_stable_alias() -> None:
    """A local written twice is not an alias, even if both RHSs are stable."""
    game = frog_parser.parse_game("""
        Game Foo(NominalGroup NG) {
            NG.Scalar x;
            NG.Element h;
            Void Initialize() {
                x <- NG.Scalar;
                h <- NG.Element;
            }
            NG.Element Get(Bool b) {
                NG.Element g = NG.Generator();
                if (b) {
                    g = h;
                }
                return NG.Exp(g, x);
            }
        }
        """)
    result = HoistDeterministicCallToInitializeTransformer(
        proof_namespace=_make_group_namespace()
    ).transform(game)
    assert _hoisted_field(result, game) is None
