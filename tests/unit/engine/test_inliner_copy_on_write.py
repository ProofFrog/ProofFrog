"""Method inlining leaves its input game available for later proof hops.

`InlineTransformer` shares every subtree it does not rewrite with its input
(the engine no longer deep-copies the game before each inlining pass), so it
must never write into a node of the input game or of the method lookup.
"""

import copy

from proof_frog import frog_ast, frog_parser, proof_engine, visitors

_Lookup = dict[tuple[str, str], frog_ast.Method]


def test_inline_transformer_does_not_mutate_input_game() -> None:
    helper = frog_ast.Method(
        frog_ast.MethodSignature("Helper", frog_ast.IntType(), []),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Integer(42))]),
    )
    call = frog_ast.FuncCall(frog_ast.FieldAccess(frog_ast.Variable("S"), "Helper"), [])
    assignment = frog_ast.Assignment(frog_ast.IntType(), frog_ast.Variable("x"), call)
    game = frog_ast.Game(
        (
            "G",
            [],
            [],
            [
                frog_ast.Method(
                    frog_ast.MethodSignature("Run", frog_ast.IntType(), []),
                    frog_ast.Block(
                        [assignment, frog_ast.ReturnStatement(frog_ast.Variable("x"))]
                    ),
                )
            ],
        )
    )
    original = str(game)

    result = visitors.InlineTransformer({("S", "Helper"): helper}).transform(game)

    assert str(game) == original
    assert isinstance(assignment.value, frog_ast.FuncCall)
    assert result != game


def _lookup() -> _Lookup:
    """S.Draw() samples a local and returns it; S.Pick(b) returns early."""
    draw = frog_parser.parse_method("""
        BitString<8> Draw() {
            BitString<8> r <- BitString<8>;
            return r;
        }
        """)
    pick = frog_parser.parse_method("""
        BitString<8> Pick(Bool b) {
            if (b) {
                return 0^8;
            }
            BitString<8> r <- BitString<8>;
            return r;
        }
        """)
    return {("S", "Draw"): draw, ("S", "Pick"): pick}


class _Snapshot:
    """Everything observable about a tree before a transform runs on it: a
    deep copy, its printed form, and the identity of every block's statement
    list and of the statements in it."""

    def __init__(self, *roots: frog_ast.ASTNode) -> None:
        self.roots = roots
        self.copies = copy.deepcopy(roots)
        self.text = [str(root) for root in roots]
        self.blocks = [
            (block, block.statements, list(block.statements))
            for root in roots
            for block in _blocks(root)
        ]

    def assert_unchanged(self) -> None:
        for root, snapshot, text in zip(self.roots, self.copies, self.text):
            assert str(root) == text
            assert root == snapshot
        for block, statements, items in self.blocks:
            assert block.statements is statements
            assert len(statements) == len(items)
            assert all(now is then for now, then in zip(statements, items))


def _blocks(root: object) -> list[frog_ast.Block]:
    found: list[frog_ast.Block] = []
    stack: list[object] = [root]
    while stack:
        current = stack.pop()
        if isinstance(current, frog_ast.ASTNode):
            if isinstance(current, frog_ast.Block):
                found.append(current)
            stack.extend(v for k, v in vars(current).items() if k != "origin")
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return found


def _calls(root: frog_ast.ASTNode, method: str) -> int:
    def is_call(node: frog_ast.ASTNode) -> bool:
        return (
            isinstance(node, frog_ast.FuncCall)
            and isinstance(node.func, frog_ast.FieldAccess)
            and node.func.name == method
        )

    count = 0
    stack: list[object] = [root]
    while stack:
        current = stack.pop()
        if isinstance(current, frog_ast.ASTNode):
            count += is_call(current)
            stack.extend(v for k, v in vars(current).items() if k != "origin")
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return count


def _inline_once(game: frog_ast.Game, lookup: _Lookup) -> frog_ast.Game:
    return visitors.InlineTransformer(lookup).transform(game)


def _inline_to_fixed_point(game: frog_ast.Game, lookup: _Lookup) -> frog_ast.Game:
    """The engine's loop (`resolve_step_game`): no copy between passes."""
    for _ in range(20):
        new_game = _inline_once(game, lookup)
        if new_game == game:
            return game
        game = new_game
    raise AssertionError("inlining did not converge")


_NESTED_IF = """
Game G() {
    BitString<8> Run(Bool c) {
        BitString<8> acc = 0^8;
        if (c) {
            BitString<8> x = S.Draw();
            acc = acc + x;
        } else {
            acc = 1^8;
        }
        return acc;
    }
    BitString<8> Other() {
        return 1^8;
    }
}
"""

_NESTED_LOOP = """
Game G() {
    BitString<8> Run() {
        BitString<8> acc = 0^8;
        for (Int i = 0 to 3) {
            BitString<8> x = S.Draw();
            acc = acc + x;
        }
        return acc;
    }
    BitString<8> Other() {
        return 1^8;
    }
}
"""

_TWO_SITES = """
Game G() {
    BitString<8> Run(Bool c) {
        BitString<8> x = S.Draw();
        if (c) {
            BitString<8> y = S.Draw();
            return x + y;
        }
        BitString<8> z = S.Pick(c);
        return x + z;
    }
    BitString<8> Other() {
        BitString<8> w = S.Draw();
        return w;
    }
}
"""


def test_call_nested_in_if_block_leaves_input_unchanged() -> None:
    game = frog_parser.parse_game(_NESTED_IF)
    lookup = _lookup()
    snapshot = _Snapshot(game, *lookup.values())

    result = _inline_once(game, lookup)

    snapshot.assert_unchanged()
    assert _calls(game, "Draw") == 1
    assert _calls(result, "Draw") == 0
    assert result != game
    # The rewritten path is fresh; everything off it is shared.
    assert result.methods[0] is not game.methods[0]
    assert result.methods[0].block is not game.methods[0].block
    assert result.methods[1] is game.methods[1]
    old_if = game.methods[0].block.statements[1]
    new_if = result.methods[0].block.statements[1]
    assert isinstance(old_if, frog_ast.IfStatement)
    assert isinstance(new_if, frog_ast.IfStatement)
    assert new_if is not old_if
    assert new_if.blocks[0] is not old_if.blocks[0]
    assert new_if.blocks[1] is old_if.blocks[1]
    assert result.methods[0].block.statements[0] is game.methods[0].block.statements[0]


def test_call_nested_in_loop_block_leaves_input_unchanged() -> None:
    game = frog_parser.parse_game(_NESTED_LOOP)
    lookup = _lookup()
    snapshot = _Snapshot(game, *lookup.values())

    result = _inline_once(game, lookup)

    snapshot.assert_unchanged()
    assert _calls(game, "Draw") == 1
    assert _calls(result, "Draw") == 0
    old_loop = game.methods[0].block.statements[1]
    new_loop = result.methods[0].block.statements[1]
    assert isinstance(old_loop, frog_ast.NumericFor)
    assert isinstance(new_loop, frog_ast.NumericFor)
    assert new_loop is not old_loop
    assert new_loop.block is not old_loop.block
    assert len(old_loop.block.statements) == 2
    assert len(new_loop.block.statements) == 3
    assert result.methods[1] is game.methods[1]


def test_no_call_returns_the_input_itself() -> None:
    game = frog_parser.parse_game(_NESTED_IF)
    lookup = _lookup()
    inlined = _inline_to_fixed_point(game, lookup)
    snapshot = _Snapshot(inlined)

    assert _inline_once(inlined, lookup) is inlined
    snapshot.assert_unchanged()


def test_same_method_inlined_at_several_call_sites() -> None:
    game = frog_parser.parse_game(_TWO_SITES)
    lookup = _lookup()
    snapshot = _Snapshot(game, *lookup.values())
    reference = copy.deepcopy(game)

    # Every intermediate game is the input of the next pass and must survive it.
    current = game
    intermediate: list[_Snapshot] = []
    for _ in range(20):
        step_snapshot = _Snapshot(current)
        new_game = _inline_once(current, lookup)
        step_snapshot.assert_unchanged()
        if new_game == current:
            break
        intermediate.append(step_snapshot)
        current = new_game
    result = current

    snapshot.assert_unchanged()
    for step_snapshot in intermediate:
        step_snapshot.assert_unchanged()
    assert len(intermediate) == 4  # three Draw sites and one Pick site
    assert _calls(game, "Draw") == 3 and _calls(game, "Pick") == 1
    assert _calls(result, "Draw") == 0 and _calls(result, "Pick") == 0

    # Each call site got its own copy of the method body: no statement object
    # of the lookup, and none twice, appears in the result.
    lookup_statements = {
        id(statement)
        for method in lookup.values()
        for block in _blocks(method)
        for statement in block.statements
    }
    seen: set[int] = set()
    for block in _blocks(result):
        for statement in block.statements:
            assert id(statement) not in lookup_statements
            assert id(statement) not in seen
            seen.add(id(statement))

    # Sharing changes nothing about the outcome: same result as the
    # deep-copy-per-pass loop the engine used before.
    for _ in range(20):
        new_reference = _inline_once(copy.deepcopy(reference), lookup)
        if new_reference == reference:
            break
        reference = new_reference
    assert result == reference
    assert str(result) == str(reference)


def test_inlined_game_survives_canonicalization_of_the_result() -> None:
    """The inlined game shares subtrees with its input, so a pipeline pass
    that wrote into its own input would corrupt the original game too."""
    engine = proof_engine.ProofEngine(verbose=False)
    for source in (_NESTED_IF, _NESTED_LOOP, _TWO_SITES):
        game = frog_parser.parse_game(source)
        lookup = _lookup()
        original = _Snapshot(game, *lookup.values())

        inlined = _inline_to_fixed_point(game, lookup)
        inlined_snapshot = _Snapshot(inlined)
        canonical = engine.canonicalize_game(inlined)

        original.assert_unchanged()
        inlined_snapshot.assert_unchanged()
        assert canonical != game
        # Canonicalizing an unshared copy gives the same canonical form.
        assert str(engine.canonicalize_game(copy.deepcopy(inlined))) == str(canonical)
