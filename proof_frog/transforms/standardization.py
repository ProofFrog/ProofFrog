"""Standardization passes: variable/field name standardization, field ordering.

These passes run once after the core fixed-point loop to assign canonical
names to variables and fields, ensuring two semantically equivalent games
produce identical ASTs.
"""

from __future__ import annotations

import copy
import heapq
import functools

from .. import frog_ast
from .. import dependencies
from ..visitors import (
    BlockTransformer,
    SearchVisitor,
    ReplaceTransformer,
    SubstitutionTransformer,
    FieldOrderingVisitor,
)
from ._base import TransformPass, PipelineContext
from ._ordering import node_sort_key

# ---------------------------------------------------------------------------
# Transformer class (moved from visitors.py)
# ---------------------------------------------------------------------------


class VariableStandardizingTransformer(BlockTransformer):
    """Renames all typed local variables to canonical names (v1, v2, v3, ...).

    Variables are numbered in declaration order across all methods.  A
    two-phase rename is used (first to collision-free intermediates, then
    to final names) to avoid conflicts when user-written names overlap
    with the v1/v2/... namespace.

    Method parameter names are collected before processing each method's
    block, and the Phase 2 numbering skips any ``vN`` name that would
    collide with a parameter.
    """

    def __init__(self) -> None:
        self.variable_counter = 0
        self._param_names: set[str] = set()

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        new_game = copy.deepcopy(game)
        new_game.methods = [self._transform_method(m) for m in new_game.methods]
        return new_game

    def _transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        self._param_names = {p.name for p in method.signature.parameters}
        return self.transform(method)

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        new_block = copy.deepcopy(block)

        # Collect typed local variable names in statement order.
        ordered_names: list[str] = []
        for statement in new_block.statements:
            if not isinstance(
                statement, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ):
                continue
            if not isinstance(statement.var, frog_ast.Variable):
                continue
            if statement.the_type is None:
                continue
            ordered_names.append(statement.var.name)

        def replace_all(blk: frog_ast.Block, old: str, new: str) -> frog_ast.Block:
            # ReplaceTransformer uses identity (`is`) comparison, so we use
            # SearchVisitor to get the actual object reference first, then
            # replace one occurrence at a time until none remain.
            def var_used(var: frog_ast.Variable, node: frog_ast.ASTNode) -> bool:
                return node == var

            while True:
                found = SearchVisitor[frog_ast.Variable](
                    functools.partial(var_used, frog_ast.Variable(old))
                ).visit(blk)
                if found is None:
                    break
                blk = ReplaceTransformer(found, frog_ast.Variable(new)).transform(blk)
            return blk

        # Phase 1: rename each typed variable to a collision-free intermediate
        # name. These names cannot conflict with any user-written "v1", "v2", ...
        # names, so this step is always safe regardless of what names already exist.
        for i, old_name in enumerate(ordered_names):
            new_block = replace_all(new_block, old_name, f"__vstandard_{i}__")

        # Phase 2: rename intermediate names to v1, v2, v3, ... in order.
        # Phase 1 guarantees each source name is unique, so no collision is
        # possible among locals.  Skip any vN that collides with a method
        # parameter to avoid shadowing.
        for i in range(len(ordered_names)):
            self.variable_counter += 1
            while f"v{self.variable_counter}" in self._param_names:
                self.variable_counter += 1
            new_block = replace_all(
                new_block, f"__vstandard_{i}__", f"v{self.variable_counter}"
            )

        return new_block


# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------


def _apply_field_rename(game: frog_ast.Game, rename: dict[str, str]) -> frog_ast.Game:
    """Apply a field-name rename map via the temp-then-final pattern.

    Using a single substitution would corrupt the AST when two field
    names swap (e.g. ``field9 → field10`` and ``field10 → field9``); the
    temp pass disambiguates.
    """
    if not rename:
        return game
    temp_map: dict[str, str] = {
        old: f"__field_temp_{i}__" for i, old in enumerate(rename)
    }
    rev_temp: dict[str, str] = {temp_map[old]: rename[old] for old in rename}

    ast_map_temp = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
    for old, tmp in temp_map.items():
        ast_map_temp.set(frog_ast.Variable(old), frog_ast.Variable(tmp))
    new_game = SubstitutionTransformer(ast_map_temp).transform(game)
    new_game = copy.copy(new_game)
    new_game.fields = [copy.copy(f) for f in new_game.fields]
    for field in new_game.fields:
        if field.name in temp_map:
            field.name = temp_map[field.name]

    ast_map_final = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
    for tmp, final in rev_temp.items():
        ast_map_final.set(frog_ast.Variable(tmp), frog_ast.Variable(final))
    new_game = SubstitutionTransformer(ast_map_final).transform(new_game)
    new_game = copy.copy(new_game)
    new_game.fields = [copy.copy(f) for f in new_game.fields]
    for field in new_game.fields:
        if field.name in rev_temp:
            field.name = rev_temp[field.name]
    new_game.fields.sort(key=lambda element: element.name)
    return new_game


def _phase3_lex_min_within_type(game: frog_ast.Game) -> frog_ast.Game:
    """Phase 3: within each contiguous same-type group of fields, swap
    field-number assignments so that the field with the lex-smaller
    ``Initialize``-body RHS gets the smaller field number.

    Stabilises canonical form across two semantically equivalent games
    that differ only in which interchangeable position holds which value
    (e.g. when KEM_PQ has two parallel keypairs whose ``[ek, dk]`` slots
    are bound in opposite orders by two reductions, leaving fields like
    ``field9 = v1[1]; field10 = v4[1]`` in one game and the swap in
    the other).
    """
    init_method: frog_ast.Method | None = None
    for m in game.methods:
        if m.signature.name == "Initialize":
            init_method = m
            break
    if init_method is None:
        return game

    field_names = {f.name for f in game.fields}
    field_rhs_key: dict[str, tuple] = {}  # type: ignore[type-arg]
    for stmt in init_method.block.statements:
        if not isinstance(
            stmt,
            (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
        ):
            continue
        if not isinstance(stmt.var, frog_ast.Variable):
            continue
        if stmt.var.name not in field_names:
            continue
        if stmt.the_type is not None:
            # Typed local with the same name as a field — not a field assignment.
            continue
        if stmt.var.name in field_rhs_key:
            # Use the FIRST assignment to a field as its canonical RHS.
            continue
        if isinstance(stmt, frog_ast.Assignment):
            field_rhs_key[stmt.var.name] = ("a",) + node_sort_key(stmt.value)
        elif isinstance(stmt, frog_ast.Sample):
            field_rhs_key[stmt.var.name] = ("s",) + node_sort_key(stmt.sampled_from)
        else:  # UniqueSample
            field_rhs_key[stmt.var.name] = ("u",) + node_sort_key(stmt.sampled_from)

    # Group fields by type (the field list may be alphabetically sorted, so
    # same-type fields aren't necessarily contiguous in the list).  Within
    # each group we re-rank by Initialize-RHS sort key.
    def _field_num(name: str) -> int:
        try:
            return int(name[len("field") :])
        except (ValueError, TypeError):
            return -1

    groups: dict[str, list[str]] = {}
    for f in game.fields:
        groups.setdefault(str(f.type), []).append(f.name)

    rename: dict[str, str] = {}
    for names in groups.values():
        if len(names) <= 1:
            continue
        # Slots: sorted ascending by their numeric suffix.  These are the
        # available field-numbers for this type group.
        slots = sorted(names, key=_field_num)
        # Sort current names by their Initialize RHS, ties broken by
        # numeric suffix (so a stable result when RHS keys tie).
        sorted_names = sorted(
            names, key=lambda n: (field_rhs_key.get(n, ()), _field_num(n))
        )
        if sorted_names == slots:
            continue
        # The k-th sorted name should occupy slots[k].
        for k, sn in enumerate(sorted_names):
            if sn != slots[k]:
                rename[sn] = slots[k]

    return _apply_field_rename(game, rename)


def standardize_field_names(game: frog_ast.Game) -> frog_ast.Game:
    """Normalize field names to canonical ordering.

    Three-phase pass:

    1. Rename fields to ``fieldN`` based on first-read order in oracle
       methods (via :class:`FieldOrderingVisitor`).
    2. Regroup the resulting fields by type so that fields of the same
       type receive consecutive numbers regardless of how oracle
       predicates end up sorting them.  Preserves Phase-1 relative
       order within each type group.
    3. Within each contiguous same-type group, sort field-number
       assignments by the lex-min sort key of the field's ``Initialize``
       RHS, so two semantically equivalent games whose interchangeable
       positions are filled in opposite orders converge to the same
       field assignment.
    """
    field_rename_map = FieldOrderingVisitor().visit(game)
    ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
    for field_name, normalized_name in field_rename_map.items():
        ast_map.set(frog_ast.Variable(field_name), frog_ast.Variable(normalized_name))

    new_game = SubstitutionTransformer(ast_map).transform(game)
    # Ensure independent copies before mutation — transform may share objects
    new_game = copy.copy(new_game)
    new_game.fields = [copy.copy(f) for f in new_game.fields]
    for field in new_game.fields:
        field.name = field_rename_map[field.name]
    new_game.fields.sort(key=lambda element: element.name)

    # Phase 2: group by type, preserving relative order within each group.
    # This re-numbers fields so that two semantically equivalent games whose
    # oracle predicates ordered conjuncts differently still end up assigning
    # the same field number to the same (type, within-type-rank) slot.
    def _field_num(name: str) -> int:
        try:
            return int(name[len("field") :])
        except (ValueError, TypeError):
            return -1

    # Sort keys: (type_key, original_field_number_within_phase_1)
    type_sorted = sorted(
        new_game.fields,
        key=lambda f: (str(f.type), _field_num(f.name)),
    )
    second_rename: dict[str, str] = {}
    for new_idx, field in enumerate(type_sorted):
        canonical = f"field{new_idx + 1}"
        if field.name != canonical:
            second_rename[field.name] = canonical
    new_game = _apply_field_rename(new_game, second_rename)

    # Phase 3 lex-min runs as a separate `FieldLexMinByRHS` pass after
    # the second `VariableStandardize`, where RHS sort keys see the
    # final local-variable names.

    return new_game


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class VariableStandardize(TransformPass):
    name = "Variable Standardization"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return VariableStandardizingTransformer().transform(game)


class StandardizeFieldNames(TransformPass):
    name = "Standardize Field Names"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return standardize_field_names(game)


class FieldLexMinByRHS(TransformPass):
    """Run only Phase-3 of field standardization (lex-min within type
    groups by Initialize RHS).  Used as a post-VariableStandardize pass
    so the RHS sort keys see the final local-variable names rather than
    the pre-rename ones."""

    name = "Field Lex-Min By RHS"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _phase3_lex_min_within_type(game)


class BubbleSortFieldAssignments(TransformPass):
    name = "Bubble Sort Field Assignments"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return dependencies.BubbleSortFieldAssignment().transform(game)


class _StabilizeIndependentStatementsTransformer(BlockTransformer):
    """Sorts independent assignment/sample statements by their value expression.

    After variable standardization, two semantically equivalent games may still
    differ in the order of independent statements (e.g.,
    ``v1 = KEM2.KeyGen(); v2 = KEM1.KeyGen()`` vs.
    ``v1 = KEM1.KeyGen(); v2 = KEM2.KeyGen()``).  This transform sorts such
    independent pairs by a key derived from the value expression (with the
    assigned variable name replaced by a placeholder), producing a canonical
    order.  A subsequent ``VariableStandardize`` pass re-normalises variable
    names after the reordering.

    Only adjacent typed declaration pairs whose values differ and that have no
    dependency between them are swapped.
    """

    def __init__(self) -> None:
        self.fields: list[str] = []

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.fields = [f.name for f in game.fields]
        new_game = copy.deepcopy(game)
        new_game.methods = [self.transform(m) for m in new_game.methods]
        return new_game

    def _value_key(self, stmt: frog_ast.Statement) -> tuple:  # type: ignore[type-arg]
        """Structural sort key for the RHS expression, ignoring the assigned name.

        Returns a tuple built from ``node_sort_key`` so that ordering is
        based on AST shape rather than ``__str__`` output.  A numeric
        prefix distinguishes field declarations (0) from locals (1) so
        that fields sort deterministically before locals.
        """
        is_field = (
            isinstance(
                stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            )
            and isinstance(stmt.var, frog_ast.Variable)
            and stmt.var.name in self.fields
        )
        prefix = (0,) if is_field else (1,)
        if isinstance(stmt, frog_ast.Assignment):
            type_key = node_sort_key(stmt.the_type) if stmt.the_type else ()
            if stmt.value is not None:
                return prefix + (type_key, node_sort_key(stmt.value))
            return ()
        if isinstance(stmt, (frog_ast.Sample, frog_ast.UniqueSample)):
            type_key = (
                node_sort_key(stmt.the_type)
                if stmt.the_type
                else node_sort_key(stmt.sampled_from)
            )
            return prefix + (type_key, node_sort_key(stmt.sampled_from))
        return ()

    def _is_typed_decl(self, stmt: frog_ast.Statement) -> bool:
        if not isinstance(
            stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            return False
        if not isinstance(stmt.var, frog_ast.Variable):
            return False
        # Include field declarations even if the_type is None (field type
        # comes from the field definition, not the statement).
        if stmt.var.name in self.fields:
            return True
        if stmt.the_type is None:
            return False
        return True

    @staticmethod
    def _collect_vars_ltr(expr: frog_ast.Expression, result: list[str]) -> None:
        """Collect variable names from *expr* in left-to-right order."""
        if isinstance(expr, frog_ast.Variable):
            if expr.name not in result:
                result.append(expr.name)
        elif isinstance(expr, frog_ast.Tuple):
            for val in expr.values:
                _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                    val, result
                )
        elif isinstance(expr, frog_ast.BinaryOperation):
            _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                expr.left_expression, result
            )
            _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                expr.right_expression, result
            )
        elif isinstance(expr, frog_ast.FuncCall):
            if isinstance(expr.func, frog_ast.Expression):
                _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                    expr.func, result
                )
            for arg in expr.args:
                _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                    arg, result
                )
        elif isinstance(expr, frog_ast.ArrayAccess):
            _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                expr.the_array, result
            )
        elif isinstance(expr, frog_ast.UnaryOperation):
            _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                expr.expression, result
            )
        elif isinstance(expr, frog_ast.Slice):
            _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                expr.the_array, result
            )

    def _compute_return_ranks(
        self,
        block: frog_ast.Block,
        stmts: list[frog_ast.Statement],
        sortable_indices: list[int],
        adj: dict[int, list[int]],
    ) -> dict[int, int]:
        """Compute a canonical rank for each sortable statement based on the
        return expression.

        Ranks are derived from the **top-level tuple position** in the
        return expression.  All variables within the same top-level tuple
        element share a rank, so value-key sorting still resolves ties.
        Ranks propagate backwards through the dependency graph so that a
        statement inherits the minimum rank of any statement that
        (transitively) depends on it.
        """
        # Find the return expression
        return_expr: frog_ast.Expression | None = None
        for s in block.statements:
            if isinstance(s, frog_ast.ReturnStatement):
                return_expr = s.expression
                break
        if return_expr is None:
            return {}

        # Split return into top-level groups; non-tuple returns are one group.
        groups: list[frog_ast.Expression]
        if isinstance(return_expr, frog_ast.Tuple):
            groups = list(return_expr.values)
        else:
            groups = [return_expr]

        if len(groups) < 2:
            # Single return value or non-tuple: every variable gets rank 0,
            # which is equivalent to no ranking (value-key decides).
            return {}

        # Collect variables from each group
        var_to_rank: dict[str, int] = {}
        for rank, group_expr in enumerate(groups):
            group_vars: list[str] = []
            self._collect_vars_ltr(group_expr, group_vars)
            for var_name in group_vars:
                if var_name not in var_to_rank:
                    var_to_rank[var_name] = rank
                else:
                    var_to_rank[var_name] = min(var_to_rank[var_name], rank)

        if not var_to_rank:
            return {}

        # Map variable names to sortable statement indices
        var_to_idx: dict[str, int] = {}
        for i in sortable_indices:
            s = stmts[i]
            if isinstance(
                s, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ) and isinstance(s.var, frog_ast.Variable):
                var_to_idx[s.var.name] = i

        # Assign direct return ranks
        ranks: dict[int, int] = {}
        for var_name, rank in var_to_rank.items():
            if var_name in var_to_idx:
                idx = var_to_idx[var_name]
                if idx not in ranks:
                    ranks[idx] = rank
                else:
                    ranks[idx] = min(ranks[idx], rank)

        # Build reverse adjacency: reverse_adj[j] = list of i that j
        # depends on (i.e. i must come before j).
        reverse_adj: dict[int, list[int]] = {i: [] for i in sortable_indices}
        for i in sortable_indices:
            for j in adj[i]:
                reverse_adj[j].append(i)

        # BFS backward propagation: if j has rank R, all statements i
        # that j depends on get min(current rank, R).
        from collections import deque  # pylint: disable=import-outside-toplevel

        queue: deque[int] = deque(idx for idx in ranks)
        while queue:
            j = queue.popleft()
            for i in reverse_adj[j]:
                new_rank = ranks[j]
                if i not in ranks or ranks[i] > new_rank:
                    ranks[i] = new_rank
                    queue.append(i)

        return ranks

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        graph = dependencies.generate_dependency_graph(
            block, [frog_ast.Field(frog_ast.Void(), f, None) for f in self.fields], {}
        )
        stmts = list(block.statements)
        # Collect sortable statement indices
        sortable_indices = [i for i, s in enumerate(stmts) if self._is_typed_decl(s)]
        if len(sortable_indices) < 2:
            return block

        # Build dependency edges among sortable statements
        # adj[i] = list of sortable indices j that depend on i
        in_deg: dict[int, int] = {i: 0 for i in sortable_indices}
        adj: dict[int, list[int]] = {i: [] for i in sortable_indices}

        def _add_edge(src: int, dst: int) -> None:
            if dst not in adj[src]:
                adj[src].append(dst)
                in_deg[dst] += 1

        for i in sortable_indices:
            node_i = graph.get_node(stmts[i])
            for j in sortable_indices:
                if i != j:
                    node_j = graph.get_node(stmts[j])
                    if node_i in node_j.in_neighbours:
                        _add_edge(i, j)

        # Non-sortable statements (if, for, return, ...) stay in place,
        # but they can *depend* on a sortable stmt that precedes them or
        # *be depended on* by a sortable stmt that follows them.  If we
        # reorder the two sortable stmts across such a barrier, the
        # non-sortable stmt ends up referencing an undefined variable.
        # Encode the constraint by adding i -> j edges whenever a
        # non-sortable stmt k with i < k < j witnesses this.
        sortable_set = set(sortable_indices)
        for k, stmt_k in enumerate(stmts):
            if k in sortable_set:
                continue
            node_k = graph.get_node(stmt_k)
            # k depends on some earlier sortable i (node_i in node_k.in_neighbours):
            # any sortable j > k must sort after i, so add i -> j.
            for i in sortable_indices:
                if i >= k:
                    continue
                if graph.get_node(stmts[i]) not in node_k.in_neighbours:
                    continue
                for j in sortable_indices:
                    if j > k:
                        _add_edge(i, j)
            # k is depended on by some later sortable j (node_k in
            # node_j.in_neighbours): any sortable i < k must sort before j.
            for j in sortable_indices:
                if j <= k:
                    continue
                node_j = graph.get_node(stmts[j])
                if node_k not in node_j.in_neighbours:
                    continue
                for i in sortable_indices:
                    if i < k:
                        _add_edge(i, j)

        # Compute return-statement-based ranks.  Statements contributing
        # to earlier return values sort first, giving a canonical order
        # independent of source-code ordering.
        return_ranks = self._compute_return_ranks(block, stmts, sortable_indices, adj)

        # Canonical topological sort (Kahn's with min-heap).
        # Primary key: return rank (earlier return position first).
        # For fields: sort by canonical field name (assigned by
        #   FieldOrderingVisitor, independent of source order).
        # For locals: sort by value expression, then variable name.
        max_rank = len(stmts)

        def _heap_key(i: int) -> tuple:  # type: ignore[type-arg]
            rank = return_ranks.get(i, max_rank)
            s = stmts[i]
            name = ""
            if isinstance(
                s, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ) and isinstance(s.var, frog_ast.Variable):
                name = s.var.name
            is_field = name in self.fields
            if is_field:
                # Field name is canonical — use it as primary tiebreaker
                return (rank, 0, name, self._value_key(stmts[i]), i)
            # Local: value key is canonical (references primitives), name
            # is secondary (will be restandardised by the next pass).
            return (rank, 1, self._value_key(stmts[i]), name, i)

        heap = [_heap_key(i) for i in sortable_indices if in_deg[i] == 0]
        heapq.heapify(heap)
        topo_order: list[int] = []
        while heap:
            _, _, _, _, idx = heapq.heappop(heap)
            topo_order.append(idx)
            for j in adj[idx]:
                in_deg[j] -= 1
                if in_deg[j] == 0:
                    heapq.heappush(heap, _heap_key(j))

        # Place sorted statements back into the positions occupied by
        # sortable statements, preserving non-sortable statement positions.
        positions = sorted(sortable_indices)
        new_stmts = list(stmts)
        for pos, orig_idx in zip(positions, topo_order):
            new_stmts[pos] = stmts[orig_idx]

        if new_stmts == stmts:
            return block
        return frog_ast.Block(new_stmts)


class StabilizeIndependentStatements(TransformPass):
    name = "Stabilize Independent Statements"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _StabilizeIndependentStatementsTransformer().transform(game)
