from __future__ import annotations
import copy
from typing import Optional, Callable, Tuple
from . import visitors
from . import frog_ast


class _StatementAccess:
    """What one statement of a block mentions and writes: everything
    the dependency graph needs to know about it, computed once per statement
    instead of once per pair of statements."""

    def __init__(self, statement: frog_ast.Statement, field_names: set[str]) -> None:
        # Complete read-set, in first-appearance order so dependency-edge order
        # is deterministic: includes variables referenced through a FieldAccess
        # (`M` in `|M.keys|`) or array/slice access, which
        # VariableCollectionVisitor drops -- without them a read of a map view
        # looks independent of a write to the map and gets reordered across it.
        # An l-value is a mention too, so this is every name the statement
        # reads or writes.
        self.mentions: list[str] = [
            variable.name
            for variable in visitors.referenced_variables_in_order(statement)
        ]
        # Names the statement may write: the l-value base of every write
        # ANYWHERE in it -- including nested inside an if/for block -- whether
        # a plain, element, slice or field write (`M[0][0] = v` and `X.f = v`
        # are writes of `M` and `X`).
        self.writes: set[str] = set()
        # A bare declaration (`T x;`) rebinds its name from here on: it is a
        # write of the name it declares, and so a mention of it.
        if isinstance(statement, frog_ast.VariableDeclaration):
            self.writes.add(statement.name)
            if statement.name not in self.mentions:
                self.mentions.insert(0, statement.name)
        self.mention_set: set[str] = set(self.mentions)
        self.contains_return = False
        # A statement mutates a field if it contains ANYWHERE a write whose
        # l-value base is a field. Checking only the top-level statement kind
        # missed a field write buried in a branch (`if (...) { F[k] = v; }`),
        # letting a later return be hoisted above the side-effecting branch
        # (the branch then looks dead and is dropped).
        self.mutates_field = False

        def collect(node: frog_ast.ASTNode) -> bool:
            if isinstance(node, frog_ast.ReturnStatement):
                self.contains_return = True
            elif isinstance(
                node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ):
                base = visitors.lvalue_base_name(node.var)
                if base is not None:
                    self.writes.add(base)
                    if base in field_names:
                        self.mutates_field = True
                # `x <-uniq[S] T` implicitly does `S = S union {x}`, so it
                # writes S even though its target `x` is a local: a read of S
                # must be ordered relative to it. And when S is a field the
                # draw mutates that field -- without this, an unused uniq draw
                # looked side-effect-free and was pruned as disconnected dead
                # code, erasing the observable insertion (F-004).
                if isinstance(node, frog_ast.UniqueSample) and (
                    node.surface_form == "uniq"
                ):
                    self.writes |= visitors.referenced_variable_names(node.unique_set)
                    if visitors.lvalue_base_name(node.unique_set) in field_names:
                        self.mutates_field = True
            return False

        visitors.SearchVisitor(collect).visit(statement)


def generate_dependency_graph(
    block: frog_ast.Block,
    fields: list[frog_ast.Field],
    _proof_namespace: frog_ast.Namespace,
) -> DependencyGraph:
    """Build the statement-ordering graph of *block*: an edge from a statement
    to every earlier statement it must stay below.

    Two statements conflict on a name when one of them writes (or rebinds) it
    and the other mentions it at all. Every reordering consumer keeps a
    statement below its in-neighbours, so the graph must connect, directly or
    through a chain, EVERY conflicting pair:

    - a statement that writes ``x`` depends on every earlier statement that
      mentions ``x`` (write-after-read and write-after-write). The nearest one
      is not enough: two earlier readers carry no edge between them, so a
      reader that is not the nearest -- typically one delayed by a dependency
      chain of its own -- could be placed after the write and read the new
      value (F-354);
    - a statement that only reads ``x`` depends on the nearest earlier writer
      of ``x`` (read-after-write). Here the nearest one IS enough, because that
      writer itself depends on every earlier mention of ``x``, earlier writers
      included.

    A bare declaration ``T x;`` is a write of ``x`` for this purpose: it
    rebinds the name from there on. That one rule gives a declaration both
    things it needs. It stays below every earlier mention of its name, which
    may refer to an outer binding (a field, a method parameter). And every
    later mention of the name reaches it, directly or through the writers in
    between, so it is ordered ahead of its uses and is reachable from the
    return whenever one of them is. Reachability is what keeps a live
    declaration from being pruned as disconnected dead code. Pruning one that
    shadows an outer name rebinds the later references to the outer binding
    (RC1 scope-awareness, SliceOfInlineConcat attack-1); pruning one that
    shadows nothing leaves its writes with no binder, as with the return slot
    the inliner declares ahead of a branching callee. Whether the declared
    name is also bound outside the block makes no difference to either, so the
    graph does not ask.

    Names are compared textually, with no scope resolution, and a statement
    with nested blocks counts as one unit that writes whatever any statement
    inside it writes; both only add edges.

    The proof namespace is unused: a name that no statement of the block writes
    produces no edge whatever it refers to, and a local or field that happens
    to share its name with a proof-level definition needs its edges like any
    other.
    """
    dependency_graph = DependencyGraph()
    for statement in block.statements:
        dependency_graph.add_node(Node(statement))
    nodes = dependency_graph.nodes

    field_names = {field.name for field in fields}
    access = [
        _StatementAccess(statement, field_names) for statement in block.statements
    ]

    for index, current in enumerate(access):
        node_in_graph = nodes[index]

        # Returns and field writes are the observable events of a method, so
        # their relative order is fixed.
        if current.contains_return:
            for earlier_index in range(index):
                earlier = access[earlier_index]
                if earlier.mutates_field or earlier.contains_return:
                    node_in_graph.add_neighbour(nodes[earlier_index])

        if current.mutates_field:
            for earlier_index in range(index):
                if access[earlier_index].contains_return:
                    node_in_graph.add_neighbour(nodes[earlier_index])

        for name in current.mentions:
            if name in current.writes:
                # WAR / WAW: below EVERY earlier mention of the name, nearest
                # first. A bare declaration is a write, and so a mention.
                for earlier_index in range(index - 1, -1, -1):
                    if name in access[earlier_index].mention_set:
                        node_in_graph.add_neighbour(nodes[earlier_index])
            else:
                # RAW: below the nearest earlier writer of the name (a bare
                # declaration included), which is itself below all the
                # earlier ones.
                for earlier_index in range(index - 1, -1, -1):
                    if name in access[earlier_index].writes:
                        node_in_graph.add_neighbour(nodes[earlier_index])
                        break

    return dependency_graph


class Node:
    def __init__(self, statement: frog_ast.Statement) -> None:
        self.in_neighbours: list[Node] = []
        self.statement = statement

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Node):
            return False
        return (
            self.in_neighbours == __value.in_neighbours
            and self.statement == __value.statement
        )

    def add_neighbour(self, neighbour: Node) -> None:
        # By identity, not ``==``: two distinct statements that happen to be
        # structurally equal (`S.Touch(f); S.Touch(f);`) are two neighbours,
        # and a write below both needs an edge to each.
        if not any(existing is neighbour for existing in self.in_neighbours):
            self.in_neighbours.append(neighbour)


class DependencyGraph:
    def __init__(self, nodes: Optional[list[Node]] = None) -> None:
        self.nodes: list[Node] = nodes if nodes else []

    def add_node(self, new_node: Node) -> None:
        self.nodes.append(new_node)

    def get_node(self, statement: frog_ast.Statement) -> Node:
        # Prefer identity match to avoid returning the wrong node when
        # two structurally-equal statements exist (e.g. duplicate
        # if-conditions).  Fall back to equality for callers that pass
        # a copy.
        for potential_node in self.nodes:
            if potential_node.statement is statement:
                return potential_node
        for potential_node in self.nodes:
            if potential_node.statement == statement:
                return potential_node
        raise ValueError("Statement not found in graph")

    def find_node(
        self, predicate: Callable[[frog_ast.Statement], bool]
    ) -> Optional[Node]:
        for node in self.nodes:
            if predicate(node.statement):
                return node
        return None

    def __str__(self) -> str:
        result = ""
        for node in self.nodes:
            result += f'{node.statement} depends on: {"nothing" if not node.in_neighbours else ""}\n'
            for neighbour in node.in_neighbours:
                result += f"  - {neighbour.statement}\n"
        return result

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, DependencyGraph):
            return False
        return self.nodes == __value.nodes


class BubbleSortFieldAssignment(visitors.BlockTransformer):
    def __init__(self) -> None:
        self.fields: list[frog_ast.Field] = []

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        new_game = copy.deepcopy(game)
        self.fields = new_game.fields
        new_game.methods = [self.transform(method) for method in new_game.methods]
        return new_game

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        # Short-circuit: a swap requires two adjacent field-assignments, so
        # if the block contains fewer than two field-assignments at the top
        # level, no swap is possible and we can skip the (expensive) graph.
        field_names = {field.name for field in self.fields}
        field_assign_count = 0
        for stmt in block.statements:
            if (
                isinstance(
                    stmt,
                    (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                )
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name in field_names
            ):
                field_assign_count += 1
                if field_assign_count >= 2:
                    break
        if field_assign_count < 2:
            return block
        graph = generate_dependency_graph(block, self.fields, {})
        new_statements = list(copy.deepcopy(block.statements))
        while True:
            swapped = False
            for i in range(1, len(new_statements)):
                first = new_statements[i - 1]
                second = new_statements[i]
                if (
                    isinstance(
                        first,
                        (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                    )
                    and isinstance(
                        second,
                        (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                    )
                    and isinstance(first.var, frog_ast.Variable)
                    and isinstance(second.var, frog_ast.Variable)
                    and first.var.name in [field.name for field in self.fields]
                    and second.var.name in [field.name for field in self.fields]
                    and first.var.name > second.var.name
                    and graph.get_node(first)
                    not in graph.get_node(second).in_neighbours
                ):
                    new_statements[i - 1] = second
                    new_statements[i] = first
                    swapped = True
            if not swapped:
                break
        return frog_ast.Block(new_statements)


def _vars_of(node: frog_ast.ASTNode) -> list[frog_ast.Variable]:
    """Complete read-set as Variable nodes -- includes variables under a
    FieldAccess/ArrayAccess/Slice that VariableCollectionVisitor drops."""
    return visitors.referenced_variables_in_order(node)


def unnecessary_statement_info(
    fields: list[str], block: frog_ast.Block
) -> Tuple[frog_ast.ASTMap[bool], list[frog_ast.Variable]]:
    required_map = frog_ast.ASTMap[bool]()

    necessary_vars = [frog_ast.Variable(field) for field in fields]

    def _run_loop_body_to_fixpoint(body: frog_ast.Block) -> None:
        # F-320: a loop body needs a liveness FIXPOINT, not a single reverse
        # pass. A loop-carried write can be marked dead when its reviving read
        # is earlier in the body TEXT but executes in a LATER iteration via the
        # back-edge (`for (...) { y = y + x; x = x + 1; }` -- the single pass
        # sees `x = x + 1` before `y = y + x` makes `x` necessary, so it deletes
        # the increment and corrupts the loop-carried value). Re-run the body
        # pass until necessary_vars stops growing; the set is monotone and
        # bounded by the variable names, so this terminates.
        nonlocal necessary_vars
        while True:
            before = {v.name for v in necessary_vars}
            remove_helper(body)
            if {v.name for v in necessary_vars} == before:
                break

    def remove_helper(block: frog_ast.Block) -> None:
        for statement in block.statements:
            required_map.set(statement, False)
        nonlocal necessary_vars
        for statement in reversed(block.statements):
            if (
                isinstance(statement, frog_ast.ReturnStatement)
                or visitors.assigns_variable(necessary_vars, statement)
                or (
                    isinstance(statement, frog_ast.VariableDeclaration)
                    and statement.name in {var.name for var in necessary_vars}
                )
                # The stateful `x <-uniq[S] T` form implicitly does
                # `S = S union {x}`, an adversary-observable mutation of S, so
                # it is NEVER dead even when its target `x` is unused; dropping
                # it would erase the insertion (F-004). The pure `x <- T \ E`
                # form has no such effect and stays removable when `x` is dead.
                or (
                    isinstance(statement, frog_ast.UniqueSample)
                    and statement.surface_form == "uniq"
                )
            ):
                # Complete read-set: variables reached through a FieldAccess
                # (`M` in `|M.keys|`) keep their backing writes alive too.
                all_vars = _vars_of(statement)
                necessary_vars += all_vars
                required_map.set(statement, True)
            elif isinstance(statement, frog_ast.NumericFor):
                necessary_vars += _vars_of(statement.start) + _vars_of(statement.end)
                _run_loop_body_to_fixpoint(statement.block)
            elif isinstance(
                statement,
                frog_ast.GenericFor,
            ):
                necessary_vars += _vars_of(statement.over)
                _run_loop_body_to_fixpoint(statement.block)
            elif isinstance(statement, frog_ast.IfStatement):
                for condition in statement.conditions:
                    necessary_vars += _vars_of(condition)
                for if_block in statement.blocks:
                    remove_helper(if_block)

    remove_helper(block)
    return (required_map, necessary_vars)


def remove_unnecessary_statements(
    fields: list[str], block: frog_ast.Block, outer_names: set[str] | None = None
) -> frog_ast.Block:
    required_map, _ = unnecessary_statement_info(fields, block)
    base_outer_names = outer_names if outer_names is not None else set()

    def _block_local_names(block: frog_ast.Block) -> set[str]:
        names: set[str] = set()
        for statement in block.statements:
            if isinstance(statement, frog_ast.VariableDeclaration):
                names.add(statement.name)
            elif isinstance(
                statement,
                (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
            ):
                base = visitors.lvalue_base_name(statement.var)
                if base is not None:
                    names.add(base)
        return names

    def construct_new(block: frog_ast.Block, enclosing: set[str]) -> frog_ast.Block:
        # Names bound by enclosing scopes (params, fields, outer-block locals).
        # A bare ``VariableDeclaration`` that shadows one of these may NOT be
        # dropped: removing it would silently rebind every subsequent reference
        # of that name to the enclosing binding (a different variable, possibly
        # of a different type/length), changing the program's meaning.  (RC1
        # scope-awareness; surfaces e.g. SliceOfInlineConcat attack-1.)
        #
        # Names bound at *this* level are visible to any nested block, so they
        # extend the enclosing set we hand to deeper recursion.
        inner_enclosing = enclosing | _block_local_names(block)
        new_statements: list[frog_ast.Statement] = []
        for statement in block.statements:
            if isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
                new_statement = copy.deepcopy(statement)
                binder = (
                    statement.name
                    if isinstance(statement, frog_ast.NumericFor)
                    else statement.var_name
                )
                new_statement.block = construct_new(
                    statement.block, inner_enclosing | {binder}
                )
                new_statements.append(new_statement)
            elif isinstance(statement, frog_ast.IfStatement):
                new_if_statement = copy.deepcopy(statement)
                new_if_statement.blocks = [
                    construct_new(b, inner_enclosing) for b in statement.blocks
                ]
                new_statements.append(new_if_statement)
            elif required_map.get(statement):
                new_statements.append(statement)
            elif (
                isinstance(statement, frog_ast.VariableDeclaration)
                and statement.name in enclosing
            ):
                # Shadowing declaration -- keep it so the inner binding (and its
                # declared type) survives.
                new_statements.append(statement)
        return frog_ast.Block(new_statements)

    return construct_new(block, set(base_outer_names))


def _collect_field_access_refs(game: frog_ast.Game) -> list[frog_ast.Variable]:
    """Collect field variables referenced via FieldAccess (e.g. field1.domain).

    VariableCollectionVisitor skips variables inside FieldAccess, so fields
    referenced only through dotted access (like <-uniq[field1.domain]) would
    otherwise be considered dead.
    """
    refs: list[frog_ast.Variable] = []

    def is_field_ref(node: frog_ast.ASTNode) -> bool:
        return (
            isinstance(node, frog_ast.FieldAccess)
            and isinstance(node.the_object, frog_ast.Variable)
            and node.the_object.name in {f.name for f in game.fields}
        )

    for method in game.methods:
        current_block = method.block
        found = visitors.SearchVisitor(is_field_ref).visit(current_block)
        while found is not None:
            assert isinstance(found, frog_ast.FieldAccess)
            assert isinstance(found.the_object, frog_ast.Variable)
            var = frog_ast.Variable(found.the_object.name)
            if var not in refs:
                refs.append(var)
            # Replace the found node and continue searching the updated tree.
            current_block = visitors.ReplaceTransformer(
                found, frog_ast.Variable("__field_access_counted__")
            ).transform(current_block)
            found = visitors.SearchVisitor(is_field_ref).visit(current_block)

    return refs


def remove_unnecessary_fields(game: frog_ast.Game) -> frog_ast.Game:
    # F-319: field necessity must be computed GAME-WIDE, to a fixpoint. Seeding
    # each method's `unnecessary_statement_info` with an EMPTY field list only
    # discovers fields needed for that method's OWN returns. A field read solely
    # in the index/key position of a write to ANOTHER field (`M[F] = v`) is
    # necessary iff that write is kept, which depends on `M` being necessary --
    # a cross-method dependency the single empty-seeded pass missed. It then
    # dropped `F` (and its setter) while `M[F] = v` survived, emitting a game
    # with a dangling reference to the undeclared `F`. Iterate: seed each pass
    # with the fields known necessary so far (so writes to a necessary field are
    # kept and their index/RHS fields harvested) until the necessary set is
    # stable. The set grows monotonically and is bounded by the fields, so this
    # terminates; a genuinely unnecessary field is still never harvested.
    all_field_names = {field.name for field in game.fields}
    field_access_field_names = {
        var.name
        for var in _collect_field_access_refs(game)
        if var.name in all_field_names
    }
    necessary_field_names: set[str] = set(field_access_field_names)
    while True:
        harvested: set[str] = set(necessary_field_names)
        seed = sorted(necessary_field_names)
        for method in game.methods:
            for var in unnecessary_statement_info(seed, method.block)[1]:
                if var.name in all_field_names:
                    harvested.add(var.name)
        if harvested == necessary_field_names:
            break
        necessary_field_names = harvested

    new_game = copy.deepcopy(game)
    new_game.fields = [
        field for field in game.fields if field.name in necessary_field_names
    ]
    actually_necessary_field_names = [field.name for field in new_game.fields]
    # Names bound outside any method body: every field (a method local may
    # shadow even a field that this pass is about to drop) plus the method's
    # own parameters.  A bare local declaration shadowing one of these must not
    # be removed (it would rebind references to the outer binding).
    all_field_names = {field.name for field in game.fields}
    for method in new_game.methods:
        param_names = {param.name for param in method.signature.parameters}
        method.block = remove_unnecessary_statements(
            actually_necessary_field_names,
            method.block,
            outer_names=all_field_names | param_names,
        )
    # Remove Void methods with empty bodies (e.g., Initialize after field removal)
    new_game.methods = [
        method
        for method in new_game.methods
        if not (
            isinstance(method.signature.return_type, frog_ast.Void)
            and not method.block.statements
        )
    ]
    return new_game
