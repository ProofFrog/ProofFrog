"""RC1 soundness regressions for MapKeyReindex (F-134, F-135, F-136).

MapKeyReindex re-keys a map under an injective wrapper. It is sound only when
the wrapper is consistently applied at every access AND the reindexing cannot
change an observable: a direct ``M.keys`` view exposes the original keys
(F-134), an element write to a "read-only" context-arg field violates the
read-only assumption (F-135), and a group-exponent wrapper needs a genuinely
nonzero exponent field (F-136).
"""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser, visitors
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.map_reindex import MapKeyReindex
from proof_frog.transforms._requirements import is_known_nonzero
from proof_frog.transforms._wrappers import _GroupExpShape

_PRIM = """
Primitive T() {
    deterministic injective BitString<8> Eval(BitString<8> x);
}
"""


def _ctx(namespace: dict | None = None) -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=visitors.NameTypeMap(),
        proof_namespace=namespace or {},
        subsets_pairs=[],
    )


def test_keys_view_blocks_reindex() -> None:
    """F-134: a ``M.keys`` view read exposes the raw keys, so reindexing under
    ``Eval`` would change the observed key set. The pass must decline."""
    prim = frog_parser.parse_string(_PRIM, frog_ast.FileType.PRIMITIVE)
    game = frog_parser.parse_game("""
        Game Pre(T TT) {
            Map<BitString<8>, BitString<16>> M;
            Void Store(BitString<8> a, BitString<16> s) {
                M[a] = s;
            }
            BitString<16>? Lookup(BitString<8> a2) {
                if (TT.Eval(a2) in M) {
                    return M[TT.Eval(a2)];
                }
                return None;
            }
            BitString<8> Leak() {
                for (BitString<8> k in M.keys) {
                    return k;
                }
                return 0b00000000;
            }
        }
        """)
    result = MapKeyReindex().apply(game, _ctx({"T": prim, "TT": prim}))
    assert result == game, "a M.keys view must block key reindexing (F-134)"


def test_context_arg_element_write_blocks_reindex() -> None:
    """F-135: an element write ``sk[0] = v`` to a context-arg field mutates a
    value the wrapper treats as read-only; the readonly check must catch the
    element write (not just a whole-variable assignment) and decline."""
    prim = frog_parser.parse_string(_PRIM, frog_ast.FileType.PRIMITIVE)
    game = frog_parser.parse_game("""
        Game Pre(T TT) {
            Map<BitString<8>, BitString<16>> M;
            Array<BitString<8>, 1> sk;
            Void Initialize() {
                sk[0] = 0b00000000;
            }
            Void Store(BitString<8> a, BitString<16> s) {
                M[TT.Eval(sk[0])] = s;
            }
            Void Rotate(BitString<8> v) {
                sk[0] = v;
            }
            BitString<16>? Lookup(BitString<8> a2) {
                if (TT.Eval(sk[0]) in M) {
                    return M[TT.Eval(sk[0])];
                }
                return None;
            }
        }
        """)
    result = MapKeyReindex().apply(game, _ctx({"T": prim, "TT": prim}))
    assert result == game, "element write to a context arg must block reindex (F-135)"


def _nonzero_game(body: str) -> frog_ast.Game:
    return frog_parser.parse_game(f"""
        Game Pre(Group G) {{
            ModInt<G.order> k;
            {body}
        }}
        """)


def test_is_known_nonzero_positive() -> None:
    """A field sampled nonzero in Initialize and never overwritten is known
    nonzero."""
    game = _nonzero_game("""
        Void Initialize() {
            k <-uniq[{0}] ModInt<G.order>;
        }
        """)
    assert is_known_nonzero("k", game)


def test_is_known_nonzero_reassigned_to_zero() -> None:
    """F-136 variant A: a later ``k = 0`` voids the nonzero guarantee."""
    game = _nonzero_game("""
        Void Initialize() {
            k <-uniq[{0}] ModInt<G.order>;
            k = 0;
        }
        """)
    assert not is_known_nonzero("k", game)


def test_is_known_nonzero_sample_outside_initialize() -> None:
    """F-136 variant B: a uniq sample in a non-Initialize oracle (which may
    never run) does not establish the field as nonzero."""
    game = _nonzero_game("""
        Void Unrelated() {
            k <-uniq[{0}] ModInt<G.order>;
        }
        """)
    assert not is_known_nonzero("k", game)


def test_is_known_nonzero_rejects_parameter() -> None:
    """An adversary-supplied parameter of the same name is not known nonzero."""
    game = frog_parser.parse_game("""
        Game Pre(Group G) {
            ModInt<G.order> k;
            Void Initialize() {
                k <-uniq[{0}] ModInt<G.order>;
            }
            ModInt<G.order> Use(ModInt<G.order> k) {
                return k;
            }
        }
        """)
    assert not is_known_nonzero("k", game)


# --- F-139 / F-140: group-exponent nonzero/coprime preconditions -------------

_G = frog_ast.Variable("G")


def _prime_ctx() -> PipelineContext:
    """A ctx that declares ``G.order is prime`` so ``precondition_misses``
    only flags the exponent (isolating the F-139/F-140 checks)."""
    ctx = _ctx()
    ctx.requirements.append(
        frog_ast.StructuralRequirement(
            "prime", frog_ast.FieldAccess(frog_ast.Variable("G"), "order")
        )
    )
    return ctx


def _exp_misses(k_expr: frog_ast.Expression) -> list[str]:
    shape = _GroupExpShape(group_expr=_G, k_expr=k_expr)
    game = frog_parser.parse_game("Game Pre(Group G) { Int O() { return 0; } }")
    return shape.precondition_misses(game, _prime_ctx())


def test_group_exp_literal_one_allowed() -> None:
    """A literal exponent of +/-1 is coprime to every prime order, so it is the
    only literal the reindex may accept."""
    assert _exp_misses(frog_ast.Integer(1)) == []
    assert _exp_misses(frog_ast.Integer(-1)) == []


def test_group_exp_literal_three_blocks_reindex() -> None:
    """F-139: a literal exponent k=3 is rejected -- under a *symbolic* prime
    order q the instantiation q=3 makes x^3 = G.identity for all x, collapsing
    every key. Only the old ``k == 0`` check passed it."""
    misses = _exp_misses(frog_ast.Integer(3))
    assert misses, "literal exponent 3 must be rejected for symbolic prime order"


def test_group_exp_literal_zero_blocks_reindex() -> None:
    """A literal exponent 0 is non-injective (x^0 = identity); still rejected."""
    assert _exp_misses(frog_ast.Integer(0))


def test_group_exp_compound_exponent_blocks_reindex() -> None:
    """F-140: a compound exponent (e.g. ``k1 * k2``) is neither Integer nor
    Variable; the dispatch previously had no else branch and silently passed.
    The product of two plain uniform samples can be 0, collapsing every key."""
    compound = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.MULTIPLY,
        frog_ast.Variable("k1"),
        frog_ast.Variable("k2"),
    )
    misses = _exp_misses(compound)
    assert misses, "a compound exponent must be rejected (F-140)"
