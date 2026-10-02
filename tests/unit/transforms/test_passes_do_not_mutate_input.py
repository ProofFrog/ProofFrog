"""No canonicalization pass may write into the game it is given.

Passes share unchanged subtrees with their input (copy-on-write), and the
engine hands the same game object to several consumers: the inliner's result
shares nodes with the instantiated game, `RedundantCopy` and
`InlineSingleUseVariable` share the statements they do not rewrite, and a
proof step's game is canonicalized once per adjacent hop. A pass that wrote
into its input would therefore silently change a *different* game.
"""

import copy
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from proof_frog import frog_ast, frog_parser, proof_engine
from proof_frog.transforms._base import (
    PipelineContext,
    TransformPass,
    run_pipeline,
    run_standardization,
)
from proof_frog.transforms.inlining import (
    InlineSingleUseVariable,
    InlineSingleUseVariableTransformer,
    RedundantCopy,
    RedundantCopyTransformer,
)
from proof_frog.transforms.pipelines import CORE_PIPELINE, STANDARDIZATION_PIPELINE
from proof_frog.web_server import _setup_engine_for_proof

EXAMPLES = Path(__file__).parent.parent.parent.parent / "examples"


def _nodes(root: object) -> list[frog_ast.ASTNode]:
    found: list[frog_ast.ASTNode] = []
    stack: list[object] = [root]
    while stack:
        current = stack.pop()
        if isinstance(current, frog_ast.ASTNode):
            found.append(current)
            stack.extend(v for k, v in vars(current).items() if k != "origin")
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return found


class _Snapshot:
    """A tree as it was: a deep copy, its printed form, and the identity of
    every block's statement list and of the statements in it."""

    def __init__(self, root: frog_ast.ASTNode) -> None:
        self.root = root
        self.copy = copy.deepcopy(root)
        self.text = str(root)
        self.blocks = [
            (node, node.statements, list(node.statements))
            for node in _nodes(root)
            if isinstance(node, frog_ast.Block)
        ]

    def changes(self) -> list[str]:
        found = []
        if str(self.root) != self.text:
            found.append("printed form changed")
        if self.root != self.copy or self.copy != self.root:
            found.append("no longer equal to its deep copy")
        for block, statements, items in self.blocks:
            if block.statements is not statements:
                found.append("a block's statement list was replaced")
            elif len(statements) != len(items) or any(
                now is not then for now, then in zip(statements, items)
            ):
                found.append("a block's statement list was edited in place")
        return found

    def assert_unchanged(self) -> None:
        assert not self.changes()


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=None,  # type: ignore[arg-type]
        proof_namespace={},
        subsets_pairs=[],
    )


# -- RedundantCopy ----------------------------------------------------------

_COPIES = """
BitString<8> f(BitString<8> a, Bool c) {
    BitString<8> b = a;
    BitString<8> d = b;
    BitString<8> acc = d + b;
    if (c) {
        BitString<8> e = acc;
        BitString<8> g = e;
        acc = g + a;
    } else {
        BitString<8> h = a;
        return h + h;
    }
    BitString<8> k = acc;
    return k + d;
}
"""

_COPIES_EXPECTED = """
BitString<8> f(BitString<8> a, Bool c) {
    BitString<8> acc = a + a;
    if (c) {
        BitString<8> e = acc;
        acc = e + a;
    } else {
        return a + a;
    }
    return acc + a;
}
"""


def test_redundant_copy_fires_repeatedly_without_touching_its_input() -> None:
    method = frog_parser.parse_method(_COPIES)
    snapshot = _Snapshot(method)

    result = RedundantCopyTransformer().transform(method)

    snapshot.assert_unchanged()
    assert result == frog_parser.parse_method(_COPIES_EXPECTED)
    # The input is still a valid input: a second run and a run on an
    # unshared copy give the same result.
    assert RedundantCopyTransformer().transform(method) == result
    assert RedundantCopyTransformer().transform(copy.deepcopy(method)) == result
    snapshot.assert_unchanged()


def test_redundant_copy_result_can_be_rewritten_without_touching_its_input() -> None:
    """The result shares statements with the input; running the pass again
    on the result (as the fixed-point loop does) must leave both intact."""
    method = frog_parser.parse_method(_COPIES)
    snapshot = _Snapshot(method)
    once = RedundantCopyTransformer().transform(method)
    once_snapshot = _Snapshot(once)

    twice = RedundantCopyTransformer().transform(once)

    assert twice == once
    snapshot.assert_unchanged()
    once_snapshot.assert_unchanged()


def test_redundant_copy_declines_without_touching_its_input() -> None:
    """Negative: the copy source is reassigned, so nothing may change and the
    input itself comes back."""
    method = frog_parser.parse_method("""
        Int f() {
            Int a = 1;
            Int b = a;
            a = a + 1;
            return b;
        }
        """)
    snapshot = _Snapshot(method)

    result = RedundantCopyTransformer().transform(method)

    assert result == method
    snapshot.assert_unchanged()


def test_redundant_copy_pass_leaves_game_unchanged() -> None:
    game = frog_parser.parse_game(f"""
        Game G() {{
            BitString<8> s;
            {_COPIES}
            BitString<8> Other(BitString<8> x) {{
                BitString<8> y = x;
                BitString<8> z = y;
                s = z;
                return z + y;
            }}
        }}
        """)
    snapshot = _Snapshot(game)

    result = RedundantCopy().apply(game, _ctx())

    snapshot.assert_unchanged()
    assert result != game
    assert result == RedundantCopy().apply(copy.deepcopy(game), _ctx())


# -- InlineSingleUseVariable -------------------------------------------------

_SINGLE_USES = """
BitString<8> f(BitString<8> a, BitString<8> b, Bool c) {
    BitString<8> t = a + b;
    BitString<8> u = t + a;
    BitString<8> acc = u + b;
    if (c) {
        BitString<8> v = acc + a;
        BitString<8> w = v + b;
        return w + a;
    }
    BitString<8> x = acc + b;
    return x + a;
}
"""


def test_inline_single_use_fires_repeatedly_without_touching_its_input() -> None:
    method = frog_parser.parse_method(_SINGLE_USES)
    snapshot = _Snapshot(method)

    result = InlineSingleUseVariableTransformer(_ctx()).transform(method)

    snapshot.assert_unchanged()
    remaining = {
        node.var.name
        for node in _nodes(result)
        if isinstance(node, frog_ast.Assignment)
        and isinstance(node.var, frog_ast.Variable)
    }
    # t, u, v, w and x are each used once and are inlined; acc is used twice.
    assert remaining == {"acc"}
    assert InlineSingleUseVariableTransformer(_ctx()).transform(method) == result
    unshared = copy.deepcopy(method)
    assert InlineSingleUseVariableTransformer(_ctx()).transform(unshared) == result
    snapshot.assert_unchanged()


def test_inline_single_use_result_can_be_rewritten_without_touching_its_input() -> None:
    method = frog_parser.parse_method(_SINGLE_USES)
    snapshot = _Snapshot(method)
    once = InlineSingleUseVariableTransformer(_ctx()).transform(method)
    once_snapshot = _Snapshot(once)

    twice = InlineSingleUseVariableTransformer(_ctx()).transform(once)

    assert twice == once
    snapshot.assert_unchanged()
    once_snapshot.assert_unchanged()


def test_inline_single_use_declines_without_touching_its_input() -> None:
    """Negative: `t` is used twice, so nothing may change."""
    method = frog_parser.parse_method("""
        BitString<8> f(BitString<8> a, BitString<8> b) {
            BitString<8> t = a + b;
            return t + t;
        }
        """)
    snapshot = _Snapshot(method)
    ctx = _ctx()

    result = InlineSingleUseVariableTransformer(ctx).transform(method)

    assert result == method
    assert [nm.variable for nm in ctx.near_misses] == ["t"]
    snapshot.assert_unchanged()


def test_inline_single_use_pass_leaves_game_unchanged() -> None:
    game = frog_parser.parse_game(f"""
        Game G() {{
            BitString<8> s;
            {_SINGLE_USES}
            BitString<8> Other(BitString<8> p) {{
                BitString<8> q = p + s;
                BitString<8> r = q + p;
                s = r + p;
                return s;
            }}
        }}
        """)
    snapshot = _Snapshot(game)

    result = InlineSingleUseVariable().apply(game, _ctx())

    snapshot.assert_unchanged()
    assert result != game
    assert result == InlineSingleUseVariable().apply(copy.deepcopy(game), _ctx())


# -- Every pass of the pipeline ----------------------------------------------


class _Guarded(TransformPass):
    """Runs a pass and records it if its input game changed under it."""

    def __init__(self, inner: TransformPass, offenders: list[str]) -> None:
        self.inner = inner
        self.name = inner.name
        self.offenders = offenders

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        snapshot = _Snapshot(game)
        result = self.inner.apply(game, ctx)
        self.offenders.extend(f"{self.name}: {c}" for c in snapshot.changes())
        return result


def _canonicalize_guarded(
    game: frog_ast.Game, ctx: PipelineContext
) -> tuple[frog_ast.Game, list[str]]:
    offenders: list[str] = []
    core: list[TransformPass] = [_Guarded(p, offenders) for p in CORE_PIPELINE]
    standardization: list[TransformPass] = [
        _Guarded(p, offenders) for p in STANDARDIZATION_PIPELINE
    ]
    result = run_pipeline(game, core, ctx)
    result = run_standardization(result, standardization, ctx)
    return result, offenders


_SMALL_GAMES = [
    """
    Game G() {
        BitString<8> k;
        Void Initialize() {
            k <- BitString<8>;
        }
        BitString<8> Enc(BitString<8> m) {
            BitString<8> r <- BitString<8>;
            BitString<8> c = r + m;
            BitString<8> d = c;
            return d;
        }
    }
    """,
    """
    Game G() {
        Map<BitString<8>, BitString<8>> T;
        Int count;
        BitString<8> Lookup(BitString<8> x) {
            count = count + 1;
            if (x in T) {
                BitString<8> y = T[x];
                return y;
            }
            BitString<8> fresh <- BitString<8>;
            T[x] = fresh;
            BitString<8> out = T[x];
            return out;
        }
    }
    """,
    """
    Game G() {
        [BitString<8>, BitString<8>] Pair(Bool b) {
            BitString<8> a <- BitString<8>;
            BitString<8> c <- BitString<8>;
            [BitString<8>, BitString<8>] t = [a, c];
            BitString<8> first = t[0];
            if (b) {
                BitString<8> second = t[1];
                return [first, second];
            } else {
                return [first, first];
            }
        }
        BitString<16> Concat() {
            BitString<8> x <- BitString<8>;
            BitString<8> y <- BitString<8>;
            BitString<16> z = x || y;
            return z;
        }
    }
    """,
]


@pytest.mark.parametrize("source", _SMALL_GAMES, ids=["xor-copy", "map", "tuple-concat"])
def test_no_pass_mutates_its_input_on_small_games(source: str) -> None:
    game = frog_parser.parse_game(source)
    snapshot = _Snapshot(game)
    engine = proof_engine.ProofEngine(verbose=False)
    # pylint: disable=protected-access
    canonical, offenders = _canonicalize_guarded(game, engine._build_context())
    # pylint: enable=protected-access

    assert not offenders
    snapshot.assert_unchanged()
    assert canonical != game  # the pipeline did rewrite something
    assert str(canonical) == str(engine.canonicalize_game(copy.deepcopy(game)))


@pytest.mark.parametrize(
    "proof",
    [
        "Proofs/SymEnc/ModOTP_INDOT.proof",
        "Proofs/SymEnc/INDOT$_implies_INDOT.proof",
        "Proofs/PRG/TriplingPRG_PRGSecurity.proof",
    ],
)
def test_no_pass_mutates_its_input_on_proof_steps(proof: str) -> None:
    """Every step of a few small example proofs, resolved by the engine (so
    the games are the inliner's sharing output), through every pass."""
    suppress = io.StringIO()
    with redirect_stdout(suppress), redirect_stderr(suppress):
        engine, proof_file = _setup_engine_for_proof(
            str(EXAMPLES / proof), allowed_root=str(EXAMPLES)
        )
    namespaces = copy.deepcopy(
        (engine.definition_namespace, engine.proof_namespace, engine.method_lookup)
    )
    steps = [step for step in proof_file.steps if isinstance(step, frog_ast.Step)]
    assert steps
    for step in steps:
        # pylint: disable=protected-access
        game = engine._get_game_ast(step.challenger, step.reduction)
        snapshot = _Snapshot(game)
        canonical, offenders = _canonicalize_guarded(game, engine._build_context())
        # pylint: enable=protected-access
        assert not offenders, str(step)
        snapshot.assert_unchanged()
        assert str(canonical) == str(engine.canonicalize_game(copy.deepcopy(game)))
    # Resolving and canonicalizing every step left the engine's own
    # definitions, which the resolved games share nodes with, intact.
    assert namespaces == (
        engine.definition_namespace,
        engine.proof_namespace,
        engine.method_lookup,
    )
