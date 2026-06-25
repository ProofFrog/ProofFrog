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
