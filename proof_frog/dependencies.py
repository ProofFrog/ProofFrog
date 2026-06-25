from __future__ import annotations
import copy
from typing import Optional, Callable, Tuple
from . import visitors
from . import frog_ast


def generate_dependency_graph(
    block: frog_ast.Block,
    fields: list[frog_ast.Field],
    proof_namespace: frog_ast.Namespace,
    shadowed_names: set[str] | None = None,
) -> DependencyGraph:
    dependency_graph = DependencyGraph()
    for statement in block.statements:
        dependency_graph.add_node(Node(statement))

    def add_dependency(node_in_graph: Node, statement: frog_ast.Statement) -> None:
        node_in_graph.add_neighbour(dependency_graph.get_node(statement))

    field_names = [field.name for field in fields]
    # Names bound by an enclosing scope (method parameters, fields).  A bare
    # ``VariableDeclaration`` of such a name is a *shadowing binder*: every
    # later reference to the name resolves to the inner local, so the
    # declaration must not be pruned as disconnected dead code (doing so
    # rebinds those references to the outer binding -- RC1 scope-awareness,
    # SliceOfInlineConcat attack-1).  We therefore make later uses of the name
    # depend on the declaration so it is reachable from the return and ordered
    # ahead of its uses.
    shadowed = set(shadowed_names or set())

    def binds_shadowed(stmt: frog_ast.Statement, name: str) -> bool:
        return (
            isinstance(stmt, frog_ast.VariableDeclaration)
            and stmt.name == name
            and name in shadowed
        )

    def contains_return(node: frog_ast.ASTNode) -> bool:
        return isinstance(node, frog_ast.ReturnStatement)

    def mutates_field(stmt: frog_ast.Statement) -> bool:
        # A statement mutates a field if it contains ANYWHERE -- including
        # nested inside an if/for block -- a write whose l-value base is a
        # field. Checking only the top-level statement kind missed a field
        # write buried in a branch (`if (...) { F[k] = v; }`), letting a later
        # return be hoisted above the side-effecting branch (the branch then
        # looks dead and is dropped). Peel element/slice/field accesses so
        # `M[0][0] = v` and `X.f = v` to a field still count.
        def _is_field_write(node: frog_ast.ASTNode) -> bool:
            if not isinstance(
                node, (frog_ast.Sample, frog_ast.Assignment, frog_ast.UniqueSample)
            ):
                return False
            base = visitors.lvalue_base_name(node.var)
            return base is not None and base in field_names

        return visitors.SearchVisitor(_is_field_write).visit(stmt) is not None

    def writes_name(node: frog_ast.ASTNode, name: str) -> bool:
        """True if *node* contains a write whose l-value base is *name* --
        a plain, element, slice, or field write."""

        def _writes(inner: frog_ast.ASTNode) -> bool:
            if (
                isinstance(
                    inner,
                    (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                )
                and visitors.lvalue_base_name(inner.var) == name
            ):
                return True
            # `x <-uniq[S] T` implicitly inserts the draw into S, so a read of S
            # must be ordered relative to it.
            return (
                isinstance(inner, frog_ast.UniqueSample)
                and inner.surface_form == "uniq"
                and name in visitors.referenced_variable_names(inner.unique_set)
            )

        return visitors.SearchVisitor(_writes).visit(node) is not None

    for index, statement in enumerate(block.statements):
        node_in_graph = dependency_graph.get_node(statement)
        earlier_statements = list(block.statements[:index])
        earlier_statements.reverse()

        if visitors.SearchVisitor(contains_return).visit(statement):
            for preceding_statement in block.statements[:index]:
                if (
                    mutates_field(preceding_statement)
                    or visitors.SearchVisitor(contains_return).visit(
                        preceding_statement
                    )
                    is not None
                ):
                    add_dependency(node_in_graph, preceding_statement)

        if mutates_field(statement):
            for preceding_statement in block.statements[:index]:
                if (
                    visitors.SearchVisitor(contains_return).visit(preceding_statement)
                    is not None
                ):
                    add_dependency(node_in_graph, preceding_statement)

        # Complete read-set, in first-appearance order so dependency-edge order
        # is deterministic: includes variables referenced through a FieldAccess
        # (`M` in `|M.keys|`) or array/slice access, which
        # VariableCollectionVisitor drops -- without them a read of a map view
        # looks independent of a write to the map and gets reordered across it.
        statement_write_cache: dict[str, bool] = {}
        for variable in visitors.referenced_variables_in_order(statement):
            name = variable.name
            if name in proof_namespace:
                continue
            # Does *this* statement write `name`?  If so it must come after any
            # earlier statement that references `name` (WAR / WAW); otherwise it
            # only reads `name` and must come after any earlier writer (RAW).
            if name not in statement_write_cache:
                statement_write_cache[name] = writes_name(statement, name)
            statement_writes = statement_write_cache[name]
            for depends_on in earlier_statements:
                if statement_writes:
                    related = name in visitors.referenced_variable_names(depends_on)
                else:
                    related = writes_name(depends_on, name)
                # A shadowing declaration of `name` is a binder the later use
                # depends on, whether the use reads or writes.
                if not related and binds_shadowed(depends_on, name):
                    related = True
                if related:
                    add_dependency(node_in_graph, depends_on)
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
        if not neighbour in self.in_neighbours:
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

    def remove_helper(block: frog_ast.Block) -> None:
        for statement in block.statements:
            required_map.set(statement, False)
        nonlocal necessary_vars
        for statement in reversed(block.statements):
            if isinstance(
                statement, frog_ast.ReturnStatement
            ) or visitors.assigns_variable(necessary_vars, statement):
                # Complete read-set: variables reached through a FieldAccess
                # (`M` in `|M.keys|`) keep their backing writes alive too.
                all_vars = _vars_of(statement)
                necessary_vars += all_vars
                required_map.set(statement, True)
            elif isinstance(statement, frog_ast.NumericFor):
                necessary_vars += _vars_of(statement.start) + _vars_of(statement.end)
                remove_helper(statement.block)
            elif isinstance(
                statement,
                frog_ast.GenericFor,
            ):
                necessary_vars += _vars_of(statement.over)
                remove_helper(statement.block)
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
    necessary_vars = []
    for method in game.methods:
        # We pass an empty list of fields
        # so that we can determine which fields are necessary based solely on return values
        necessary_vars += unnecessary_statement_info([], method.block)[1]

    # Also include fields referenced via FieldAccess (e.g. field1.domain in
    # <-uniq expressions), which VariableCollectionVisitor skips.
    necessary_vars += _collect_field_access_refs(game)

    new_game = copy.deepcopy(game)
    new_game.fields = [
        field
        for field in game.fields
        if frog_ast.Variable(field.name) in necessary_vars
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
