# pylint: disable=duplicate-code
# The block-local scope-guard count helpers (_count_var_refs / _count_var_decls)
# and the _local_escapes_block logic mirror the structurally identical helpers in
# transforms.sampling (SinkUniformSample's F-042 guard); each transform module
# keeps its own copy rather than coupling the two modules for a few small pure
# functions.
"""Tuple-related passes: expand and simplify tuples.

Product-typed values are expanded into individual components for
canonicalization, then collapsed back when possible.
"""

from __future__ import annotations

import copy

from .. import frog_ast
from ..visitors import (
    BlockTransformer,
    NameTypeMap,
    Transformer,
    Visitor,
    SearchVisitor,
    ReplaceTransformer,
    AllConstantFieldAccesses,
    GetTypeMapVisitor,
    lvalue_base_name,
)
from ._base import (
    TransformPass,
    PipelineContext,
    has_nondeterministic_call,
    NearMiss,
)

# ---------------------------------------------------------------------------
# Transformer classes (moved from visitors.py)
# ---------------------------------------------------------------------------


def _count_var_refs(node: frog_ast.ASTNode, name: str) -> int:
    """Count occurrences of *name* as a variable reference in *node*."""
    count = [0]

    def _p(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, frog_ast.Variable) and n.name == name:
            count[0] += 1
        return False

    SearchVisitor(_p).visit(node)
    return count[0]


def _has_self_referencing_whole_assignment(node: frog_ast.ASTNode, name: str) -> bool:
    """Return True iff *node* contains a whole-variable assignment to *name*
    whose right-hand side also references *name* (e.g. a swap
    ``v = [v[1], v[0]];``).

    F-321: ``ExpandTupleTransformer`` rewrites a whole-tuple assignment into
    *sequential* per-component assignments. That is only faithful when the
    right-hand side does not read the tuple being assigned: the RHS of
    ``v = [v[1], v[0]];`` evaluates to a value before the assignment happens,
    but the sequential expansion ``v@0 = v@1; v@1 = v@0;`` makes later
    components read already-overwritten ones. Expansion must decline on any
    such self-referencing whole-variable assignment.
    """

    def _p(n: frog_ast.ASTNode) -> bool:
        return (
            isinstance(n, frog_ast.Assignment)
            and isinstance(n.var, frog_ast.Variable)
            and n.var.name == name
            and _count_var_refs(n.value, name) > 0
        )

    return SearchVisitor(_p).visit(node) is not None


def _count_var_decls(node: frog_ast.ASTNode, name: str) -> int:
    """Count local declarations that bind *name* in *node* (typed
    sample/assignment/declaration, or a loop binder)."""
    count = [0]

    def _p(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, frog_ast.VariableDeclaration) and n.name == name:
            count[0] += 1
        elif (
            isinstance(n, (frog_ast.Sample, frog_ast.Assignment, frog_ast.UniqueSample))
            and n.the_type is not None
            and isinstance(n.var, frog_ast.Variable)
            and n.var.name == name
        ):
            count[0] += 1
        elif isinstance(n, frog_ast.NumericFor) and n.name == name:
            count[0] += 1
        elif isinstance(n, frog_ast.GenericFor) and n.var_name == name:
            count[0] += 1
        return False

    SearchVisitor(_p).visit(node)
    return count[0]


class ExpandTupleTransformer(Transformer):
    """Expands product-typed variables into individual component variables.

    A field or local of type ``T1 * T2`` is split into ``T1 v@0`` and
    ``T2 v@1``.  Locals are handled both as declarations with an
    initializer (``[T1, T2] v = [e0, e1];``) and as bare declarations
    (``[T1, T2] v;``) later written by whole-variable or element
    assignments (issue #255).  Index accesses like ``v[0]`` are rewritten
    to the corresponding component variable.  Only applies when all
    accesses use constant indices and no whole-variable reassignment
    reads the variable in its own right-hand side (checked via
    ``AllConstantFieldAccesses`` and
    ``_has_self_referencing_whole_assignment``).
    """

    def __init__(
        self,
        ctx: PipelineContext | None = None,
        bare_locals_only: bool = False,
        pass_name: str = "Expand Tuples",
    ) -> None:
        self.ctx = ctx
        # ``bare_locals_only`` restricts the transformer to splitting bare
        # product-typed local declarations (issue #255). It is used by the
        # early ``Split Bare Tuple Declarations`` pass, which must run before
        # Topological Sorting prunes bare declarations and Collapse Assignment
        # folds their assignments away. Fields and decl-with-initializer
        # locals keep their existing late-pipeline route (the full
        # ``Expand Tuples`` pass) so their canonical routes are unchanged.
        self.bare_locals_only = bare_locals_only
        self.pass_name = pass_name
        self.to_transform: list[str] = []
        self.lengths: list[int] = []
        self._current_method: frog_ast.Method | None = None

    def _near_miss(
        self,
        reason: str,
        suggestion: str | None,
        variable: str,
        location: frog_ast.SourceOrigin | None = None,
    ) -> None:
        if self.ctx is None:
            return
        self.ctx.near_misses.append(
            NearMiss(
                transform_name=self.pass_name,
                reason=reason,
                location=location,
                suggestion=suggestion,
                variable=variable,
                method=(
                    self._current_method.signature.name
                    if self._current_method is not None
                    else None
                ),
            )
        )

    def transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        # Capture the enclosing method so the F-324 scope guard can tell whether
        # a block-local tuple declaration escapes the block being expanded.
        self._current_method = method
        result = self._transform_children(method)
        assert isinstance(result, frog_ast.Method)
        return result

    def _local_escapes_block(self, block: frog_ast.Block, name: str) -> bool:
        """F-324 scope guard (mirrors the SinkUniformSample F-042 guard).

        A block-local product declaration is expanded in place, splitting
        ``v`` into ``v@k`` components only within this block (a local's entry
        in ``to_transform`` is popped when the block finishes). For well-typed
        input a block-local is never referenced outside its block, so the
        existing within-block ``_has_reference`` guard is exact. But on a
        malformed, out-of-scope AST where ``v`` is also read in an enclosing
        block, expanding here would leave that outer ``v[k]`` access unrewritten
        (dangling). Decline when ``name`` is referenced in the method outside
        ``block`` with no governing outer declaration."""
        method = self._current_method
        if method is None:
            return False
        refs_in_method = _count_var_refs(method.block, name)
        refs_in_block = _count_var_refs(block, name)
        if refs_in_method <= refs_in_block:
            return False  # no references outside this block -> safe
        decls_in_method = _count_var_decls(method.block, name)
        decls_in_block = _count_var_decls(block, name)
        return decls_in_method <= decls_in_block

    def _is_transformable_tuple(
        self, the_type: frog_ast.Type, name: str, search_space: frog_ast.ASTNode
    ) -> bool:
        if not isinstance(the_type, frog_ast.ProductType):
            return False
        if not AllConstantFieldAccesses(name).visit(search_space):
            self._near_miss(
                reason=(
                    f"product-typed '{name}' was not split into components: "
                    "an access uses a non-constant index, a whole-variable "
                    "write is not a tuple literal, or the whole variable is "
                    "sampled"
                ),
                suggestion=(
                    f"Access '{name}' only at constant indices and write it "
                    "either element-wise or as a whole-variable tuple literal"
                ),
                variable=name,
            )
            return False
        # F-321: a whole-variable reassignment whose RHS reads the variable
        # itself (e.g. a swap ``v = [v[1], v[0]];``) cannot be split into
        # sequential component assignments -- later components would read
        # already-overwritten values instead of the pre-assignment ones.
        if _has_self_referencing_whole_assignment(search_space, name):
            self._near_miss(
                reason=(
                    f"product-typed '{name}' was not split into components: "
                    f"a whole-variable assignment reads '{name}' in its "
                    "right-hand side, and sequential component assignments "
                    "would overwrite components the right-hand side still "
                    "needs"
                ),
                suggestion=(
                    f"Copy '{name}' into a temporary variable and build the "
                    "reassigned tuple from the temporary"
                ),
                variable=name,
            )
            return False
        return True

    @staticmethod
    def _has_reference(name: str, block: frog_ast.Block) -> bool:
        """Return True iff *name* is referenced (as a Variable) in *block*."""

        def is_named_variable(node: frog_ast.ASTNode) -> bool:
            return isinstance(node, frog_ast.Variable) and node.name == name

        return SearchVisitor(is_named_variable).visit(block) is not None

    def _can_expand_bare_declaration(
        self,
        statement: frog_ast.VariableDeclaration,
        block: frog_ast.Block,
        stmt_idx: int,
    ) -> bool:
        """Decide whether a bare product-typed local ``[T0, T1] v;`` may be
        split into per-component declarations (issue #255: the split-decl
        spelling must canonicalize like the decl-with-initializer one).

        Carries the same guards as the decl-with-initializer branch: the
        variable must be referenced in the remainder of THIS block (otherwise
        the use site is in an enclosing scope, or the decl is dead code),
        every access must pass ``_is_transformable_tuple``, and the F-324
        scope guard must not trip.
        """
        if not isinstance(statement.type, frog_ast.ProductType):
            return False
        if not self._has_reference(
            statement.name,
            frog_ast.Block(list(block.statements[stmt_idx + 1 :])),
        ):
            return False
        if not self._is_transformable_tuple(statement.type, statement.name, block):
            # near-miss emitted by _is_transformable_tuple
            return False
        if self._local_escapes_block(block, statement.name):
            self._near_miss(
                reason=(
                    f"product-typed '{statement.name}' was not split into "
                    "components: it is referenced outside the block that "
                    "declares it, and splitting would leave those references "
                    "dangling"
                ),
                suggestion=(
                    f"Declare '{statement.name}' in the block where it is " "used"
                ),
                variable=statement.name,
                location=statement.origin,
            )
            return False
        return True

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        if self.bare_locals_only:
            return frog_ast.Game(
                (
                    game.name,
                    game.parameters,
                    list(game.fields),
                    [self.transform(method) for method in game.methods],
                )
            )
        new_fields = []
        for field in game.fields:
            if self._is_transformable_tuple(field.type, field.name, game):
                assert isinstance(field.type, frog_ast.ProductType)
                unfolded_types = field.type.types
                for index, the_type in enumerate(unfolded_types):
                    expression = None
                    if field.value:
                        field_values = frog_ast.tuple_literal_values(field.value)
                        assert field_values is not None
                        expression = field_values[index]
                    new_fields.append(
                        frog_ast.Field(the_type, f"{field.name}@{index}", expression)
                    )
                self.to_transform.append(field.name)
                self.lengths.append(len(unfolded_types))
            else:
                new_fields.append(field)
        return frog_ast.Game(
            (
                game.name,
                game.parameters,
                new_fields,
                [self.transform(method) for method in game.methods],
            )
        )

    def transform_block(self, block: frog_ast.Block) -> frog_ast.Block:
        new_statements: list[frog_ast.Statement] = []
        expanded_tuple_count = 0
        for stmt_idx, statement in enumerate(block.statements):
            # Assigning to the tuple means assigning each individual value
            if (
                isinstance(statement, frog_ast.Assignment)
                and isinstance(statement.var, frog_ast.Variable)
                and statement.var.name in self.to_transform
            ):
                stmt_values = frog_ast.tuple_literal_values(statement.value)
                assert stmt_values is not None
                for index, tuple_value in enumerate(stmt_values):
                    new_statements.append(
                        frog_ast.Assignment(
                            None,
                            frog_ast.Variable(f"{statement.var}@{index}"),
                            tuple_value,
                        )
                    )
            # Asssigning to a tuple element means assigning to that one element
            elif (
                isinstance(statement, (frog_ast.Assignment, frog_ast.Sample))
                and isinstance(statement.var, frog_ast.ArrayAccess)
                and isinstance(statement.var.the_array, frog_ast.Variable)
                and statement.var.the_array.name in self.to_transform
            ):
                assert isinstance(statement.var.index, frog_ast.Integer)
                new_statement = copy.deepcopy(statement)
                new_statement.var = frog_ast.Variable(
                    f"{statement.var.the_array.name}@{statement.var.index.num}",
                )
                new_statements.append(new_statement)
            elif (
                not self.bare_locals_only
                and isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.var, frog_ast.Variable)
                and self._is_transformable_tuple(
                    statement.the_type, statement.var.name, block
                )
                # Refuse to fire on a local-decl whose variable is not
                # referenced in subsequent statements of THIS block: the
                # use site is in an enclosing scope (e.g. this block is
                # the body of an if-branch), and expanding here would
                # split the decl into v@k components without rewriting
                # the outer-scope ``v[k]`` access, leaving it dangling.
                # The decl's own LHS does not count as a reference.
                and self._has_reference(
                    statement.var.name,
                    frog_ast.Block(list(block.statements[stmt_idx + 1 :])),
                )
                # F-324: also decline when the local escapes this block (an
                # outer-scope ``v[k]`` would be left dangling by the split).
                and not self._local_escapes_block(block, statement.var.name)
            ):
                assert isinstance(statement.the_type, frog_ast.ProductType)
                unfolded_types = statement.the_type.types
                stmt_values = frog_ast.tuple_literal_values(statement.value)
                assert stmt_values is not None
                for index, the_type in enumerate(unfolded_types):
                    new_statements.append(
                        frog_ast.Assignment(
                            the_type,
                            frog_ast.Variable(f"{statement.var.name}@{index}"),
                            stmt_values[index],
                        )
                    )
                self.to_transform.append(statement.var.name)
                self.lengths.append(len(unfolded_types))
                expanded_tuple_count += 1
            # A bare product-typed declaration ``[T0, T1] v;`` (issue #255)
            # is split into per-component declarations; the later
            # whole-variable / element assignments and accesses are then
            # handled by the branches above and by transform_array_access.
            elif isinstance(
                statement, frog_ast.VariableDeclaration
            ) and self._can_expand_bare_declaration(statement, block, stmt_idx):
                assert isinstance(statement.type, frog_ast.ProductType)
                unfolded_decl_types = statement.type.types
                for index, the_type in enumerate(unfolded_decl_types):
                    new_statements.append(
                        frog_ast.VariableDeclaration(
                            the_type, f"{statement.name}@{index}"
                        )
                    )
                self.to_transform.append(statement.name)
                self.lengths.append(len(unfolded_decl_types))
                expanded_tuple_count += 1
            else:
                new_statements.append(statement)
        new_block = frog_ast.Block(
            [self.transform(statement) for statement in new_statements]
        )
        self.to_transform = (
            self.to_transform[:-expanded_tuple_count]
            if expanded_tuple_count > 0
            else self.to_transform
        )
        self.lengths = (
            self.lengths[:-expanded_tuple_count]
            if expanded_tuple_count > 0
            else self.lengths
        )
        return new_block

    def transform_array_access(
        self, array_access: frog_ast.ArrayAccess
    ) -> frog_ast.Expression:
        if (
            not isinstance(array_access.the_array, frog_ast.Variable)
            or array_access.the_array.name not in self.to_transform
        ):
            return frog_ast.ArrayAccess(
                self.transform(array_access.the_array),
                self.transform(array_access.index),
            )
        assert isinstance(array_access.index, frog_ast.Integer)
        return frog_ast.Variable(
            f"{array_access.the_array.name}@{array_access.index.num}"
        )

    def transform_variable(self, var: frog_ast.Variable) -> frog_ast.Expression:
        if var.name not in self.to_transform:
            return var
        length = self.lengths[self.to_transform.index(var.name)]
        return frog_ast.Tuple(
            [frog_ast.Variable(f"{var.name}@{index}") for index in range(length)]
        )


class FoldTupleIndexTransformer(Transformer):
    """Constant-folds indexing a tuple literal: ``[e0, e1, ...][i]`` → ``e_i``.

    Only applies when the index is a constant integer and every discarded
    element (``e_j`` for ``j != i``) contains no non-deterministic function
    calls, ensuring that no randomised computation is silently removed.
    """

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: NameTypeMap | None = None,
    ) -> None:
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types = proof_let_types

    def transform_array_access(
        self, array_access: frog_ast.ArrayAccess
    ) -> frog_ast.Expression:
        arr = self.transform(array_access.the_array)
        idx = self.transform(array_access.index)

        if not (isinstance(arr, frog_ast.Tuple) and isinstance(idx, frog_ast.Integer)):
            return frog_ast.ArrayAccess(arr, idx)

        i = idx.num
        if i < 0 or i >= len(arr.values):
            return frog_ast.ArrayAccess(arr, idx)

        # Check that every DISCARDED element is pure (no non-deterministic calls)
        for j, elem in enumerate(arr.values):
            if j == i:
                continue
            if has_nondeterministic_call(
                elem, self._proof_namespace, self._proof_let_types
            ):
                return frog_ast.ArrayAccess(arr, idx)

        return arr.values[i]


class SimplifyTupleTransformer(Transformer):
    """Collapses a tuple literal back into the original variable.

    When a tuple ``[v[0], v[1], ...]`` reconstructs every element of a
    product-typed variable ``v`` in order, it is simplified to just ``v``.
    """

    def __init__(self, ast: frog_ast.ASTNode) -> None:
        self.ast = ast

    def transform_tuple(self, the_tuple: frog_ast.Tuple) -> frog_ast.Expression:
        if not all(
            isinstance(value, frog_ast.ArrayAccess) for value in the_tuple.values
        ):
            return the_tuple
        if not all(
            isinstance(value.index, frog_ast.Integer) for value in the_tuple.values  # type: ignore
        ):
            return the_tuple
        if not all(
            value.index.num == index for index, value in enumerate(the_tuple.values)  # type: ignore
        ):
            return the_tuple
        if not all(
            isinstance(value.the_array, frog_ast.Variable) for value in the_tuple.values  # type: ignore
        ):
            return the_tuple
        tuple_val_name = the_tuple.values[0].the_array.name  # type: ignore
        if not all(
            value.the_array.name == tuple_val_name for value in the_tuple.values  # type: ignore
        ):
            return the_tuple

        type_map = GetTypeMapVisitor(the_tuple).visit(self.ast)
        tuple_type = type_map.get(tuple_val_name)
        assert isinstance(tuple_type, frog_ast.ProductType)
        if len(tuple_type.types) == len(the_tuple.values):
            return frog_ast.Variable(tuple_val_name)
        return the_tuple


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class ExpandTuple(TransformPass):
    name = "Expand Tuples"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ExpandTupleTransformer(ctx).transform(game)


class SplitBareTupleDeclarations(TransformPass):
    """Splits a bare product-typed local declaration ``[T0, T1] v;`` into
    per-component declarations, rewriting the later whole-variable / element
    assignments and constant-index accesses (issue #255).

    Runs EARLY in the pipeline: by the time the full ``Expand Tuples`` pass
    runs, Topological Sorting has pruned bare declarations and Collapse
    Assignment has folded their assignments into use sites, leaving a
    ``[e0, e1][i]`` shape that ``Fold Tuple Literal Indexing`` must
    conservatively decline when a discarded element is non-deterministic.
    Splitting the declaration first lets the split-declaration spelling
    canonicalize exactly like the declaration-with-initializer spelling.
    """

    name = "Split Bare Tuple Declarations"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ExpandTupleTransformer(
            ctx, bare_locals_only=True, pass_name=self.name
        ).transform(game)


class FoldTupleIndex(TransformPass):
    name = "Fold Tuple Literal Indexing"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return FoldTupleIndexTransformer(
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


class SimplifyTuple(TransformPass):
    name = "Simplify tuples that are copies of their fields"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SimplifyTupleTransformer(game).transform(game)


class CollapseSingleIndexTupleTransformer(BlockTransformer):
    """Collapses a product-typed variable accessed at a single constant index.

    When a typed local ``[T0, T1] v = expr`` (where *expr* is not a tuple
    literal) is only ever used as ``v[i]`` for one fixed index *i*, it is
    rewritten to ``Ti v = expr[i]`` and every ``v[i]`` is replaced with ``v``.

    This normalises composed-game canonical forms where a function call
    returning a product is only partially used, matching the form produced
    when a scheme-inlined game drops unused components.
    """

    def __init__(self) -> None:
        self._multi_assigned: set[str] = set()

    def transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        # A variable assigned in more than one place within the method
        # (e.g. a phi-like variable declared in both arms of an if after
        # If-Split Branch Assignment) must NOT be collapsed: rewriting one
        # declaration to ``Ti v = expr[i]`` while leaving a sibling
        # ``[T0,T1] v = expr2`` produces an inconsistently-typed variable,
        # and a later inlining then substitutes the whole tuple in place of
        # ``v`` (dropping the index). Precompute the set of names with two
        # or more assignments in this method and skip them. Counting is
        # per-method so a name reused as an independent local in another
        # method is not affected.
        counts: dict[str, int] = {}

        def _count(node: frog_ast.ASTNode) -> bool:
            if isinstance(
                node,
                (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
            ):
                base = lvalue_base_name(node.var)
                if base is not None:
                    counts[base] = counts.get(base, 0) + 1
            return False

        SearchVisitor(_count).visit(method.block)
        saved = self._multi_assigned
        self._multi_assigned = {n for n, c in counts.items() if c > 1}
        try:
            new_block = self.transform(method.block)
        finally:
            self._multi_assigned = saved
        if new_block is method.block:
            return method
        return frog_ast.Method(method.signature, new_block)

    @staticmethod
    def _analyse_uses(var_name: str, block: frog_ast.Block) -> tuple[bool, set[int]]:
        """Return (has_bare_use, indices_used) for *var_name* in *block*.

        A "bare use" is any ``Variable(var_name)`` that is NOT the
        ``the_array`` child of an ``ArrayAccess`` node.
        """

        class _UsageVisitor(Visitor[None]):
            """Count total Variable refs and ArrayAccess refs."""

            def __init__(self, name: str) -> None:
                self.name = name
                self.total_var_refs = 0
                self.array_access_refs = 0
                self.non_constant_access = False
                self.indices: set[int] = set()

            def result(self) -> None:
                pass

            def visit_variable(self, var: frog_ast.Variable) -> None:
                if var.name == self.name:
                    self.total_var_refs += 1

            def visit_array_access(self, aa: frog_ast.ArrayAccess) -> None:
                if (
                    isinstance(aa.the_array, frog_ast.Variable)
                    and aa.the_array.name == self.name
                ):
                    self.array_access_refs += 1
                    if isinstance(aa.index, frog_ast.Integer):
                        self.indices.add(aa.index.num)
                    else:
                        self.non_constant_access = True

        visitor = _UsageVisitor(var_name)
        visitor.visit(block)
        # Bare uses = total Variable refs minus those inside ArrayAccess
        has_bare = visitor.total_var_refs > visitor.array_access_refs
        # If any access uses a non-constant index, treat as bare use
        # to prevent collapsing (the variable index may access any element)
        if visitor.non_constant_access:
            has_bare = True
        return has_bare, visitor.indices

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for stmt_idx, statement in enumerate(block.statements):
            if not (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.the_type, frog_ast.ProductType)
                and isinstance(statement.var, frog_ast.Variable)
                and frog_ast.tuple_literal_values(statement.value) is None
            ):
                continue

            var_name = statement.var.name
            if var_name in self._multi_assigned:
                continue
            remaining = frog_ast.Block(list(block.statements[stmt_idx + 1 :]))

            has_bare, indices_used = self._analyse_uses(var_name, remaining)
            if has_bare or len(indices_used) != 1:
                continue

            idx = next(iter(indices_used))
            assert isinstance(statement.the_type, frog_ast.ProductType)
            element_type = statement.the_type.types[idx]

            # Rewrite the declaration to extract just one element
            new_decl = frog_ast.Assignment(
                element_type,
                frog_ast.Variable(var_name),
                frog_ast.ArrayAccess(
                    copy.deepcopy(statement.value),
                    frog_ast.Integer(idx),
                ),
            )

            # F-313: the collapse decision is based ONLY on uses in the suffix
            # (``remaining``), where ``v`` is this declaration's binding. Rewrite
            # ``v[idx] -> v`` ONLY in the suffix. A ``v[idx]`` in the prefix
            # refers to an outer/shadowed ``v`` (a different binding), and the
            # new declaration's own RHS must also stay intact; rewriting the
            # whole reconstructed block would collapse those unrelated accesses.
            suffix_block = frog_ast.Block(list(block.statements[stmt_idx + 1 :]))
            target = frog_ast.ArrayAccess(
                frog_ast.Variable(var_name), frog_ast.Integer(idx)
            )
            while True:
                found = SearchVisitor(
                    lambda n, t=target: (  # type: ignore[misc]
                        isinstance(n, frog_ast.ArrayAccess) and n == t
                    )
                ).visit(suffix_block)
                if found is None:
                    break
                suffix_block = ReplaceTransformer(
                    found, frog_ast.Variable(var_name)
                ).transform(suffix_block)

            new_block = frog_ast.Block(
                list(block.statements[:stmt_idx])
                + [new_decl]
                + list(suffix_block.statements)
            )
            return self.transform(new_block)

        return block


class CollapseSingleIndexTuple(TransformPass):
    name = "Collapse Single-Index Tuple Access"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return CollapseSingleIndexTupleTransformer().transform(game)


class _ProductLiteralValueRewriter(Transformer):
    """Rewrites ``ProductType`` tuple literals into ``Tuple`` nodes inside a
    single VALUE expression.

    Instantiation and inlining substitute namespace values for variables, and
    convert a ``Tuple`` whose members all satisfy ``isinstance(_, Type)`` into
    a ``ProductType`` so that Set-alias substitutions land in type positions
    as genuine types. Because ``Variable`` (and ``FieldAccess``) are both
    ``Expression`` and ``Type``, this also mangles ordinary tuple literals of
    bare variables (e.g. an inlined oracle argument ``[ss, ct]``) into
    ``ProductType`` nodes in expression positions, which downstream passes
    (``FoldTupleIndex``, ``TupleEqualityDecompose``) and ``Z3FormulaVisitor``
    do not recognize as tuple literals.

    This rewriter is applied only to expression slots that cannot hold a
    type (if-conditions, assignment/return values, loop bounds/iterables,
    map indices), so any ``ProductType`` it meets is a literal. Two guarded
    positions are left untouched because a bare ``ProductType`` there
    legitimately denotes a *space* rather than a literal: the operand of the
    cardinality operator ``|...|``, and the right-hand side of
    ``in``/``subsets``.
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def transform_product_type(self, node: frog_ast.ProductType) -> frog_ast.ASTNode:
        values = frog_ast.tuple_literal_values(node)
        if values is not None and all(
            isinstance(v, frog_ast.Expression) for v in values
        ):
            return frog_ast.Tuple([self.transform(v) for v in values])
        if self.ctx is not None:
            self.ctx.near_misses.append(
                NearMiss(
                    transform_name="Normalize Product-Literal Tuples",
                    reason=(
                        "ProductType found in an expression position but not "
                        "converted to a tuple literal: not all members are "
                        "expressions"
                    ),
                    location=None,
                    suggestion=None,
                    variable=str(node),
                    method=None,
                )
            )
        # F-316: a ProductType that is NOT a literal (values is None, or some
        # member is a genuine type) denotes a *space*, not a tuple value. Do NOT
        # descend with `_transform_children`: that recurses into `node.types` and
        # converts any nested literal member into a `Tuple`, grafting a `Tuple`
        # into `ProductType.types` -- a mixed-representation node that downstream
        # passes and the Z3 visitor mis-read. Leave the space untouched.
        return node

    def transform_unary_operation(
        self, node: frog_ast.UnaryOperation
    ) -> frog_ast.ASTNode:
        # `|X|` may take a space (type) operand: cardinality of a product
        # space must stay a ProductType (a Tuple there would mean length).
        if node.operator == frog_ast.UnaryOperators.SIZE:
            return node
        return self._transform_children(node)

    def transform_binary_operation(
        self, node: frog_ast.BinaryOperation
    ) -> frog_ast.ASTNode:
        # The RHS of `in` / `subsets` may be a space (type); leave it alone.
        if node.operator in (
            frog_ast.BinaryOperators.IN,
            frog_ast.BinaryOperators.SUBSETS,
        ):
            new_left = self.transform(node.left_expression)
            if new_left is node.left_expression:
                return node
            return frog_ast.BinaryOperation(
                node.operator, new_left, node.right_expression
            )
        return self._transform_children(node)


class NormalizeProductLiteralTransformer(BlockTransformer):
    """Applies ``_ProductLiteralValueRewriter`` to every method-body
    expression slot that can only hold a value, never a type. Declared types
    (``the_type``, sample spaces, loop variable types) are never touched."""

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _value(self, expr: frog_ast.Expression) -> frog_ast.Expression:
        result: frog_ast.Expression = _ProductLiteralValueRewriter(self.ctx).transform(
            expr
        )
        return result

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        new_statements: list[frog_ast.Statement] = []
        changed = False
        for statement in block.statements:
            new_statement = self._rewrite_statement(statement)
            changed = changed or new_statement is not statement
            new_statements.append(new_statement)
        return frog_ast.Block(new_statements) if changed else block

    def _rewrite_statement(self, statement: frog_ast.Statement) -> frog_ast.Statement:
        if isinstance(statement, frog_ast.Assignment):
            # `Set S = ...;` binds a type alias; leave its RHS alone.
            if isinstance(statement.the_type, frog_ast.SetType):
                return statement
            new_var = self._value(statement.var)
            new_value = self._value(statement.value)
            if new_var is statement.var and new_value is statement.value:
                return statement
            return frog_ast.Assignment(statement.the_type, new_var, new_value)
        if isinstance(statement, frog_ast.Sample):
            new_var = self._value(statement.var)
            if new_var is statement.var:
                return statement
            return frog_ast.Sample(statement.the_type, new_var, statement.sampled_from)
        if isinstance(statement, frog_ast.UniqueSample):
            new_var = self._value(statement.var)
            new_unique_set = self._value(statement.unique_set)
            if new_var is statement.var and new_unique_set is statement.unique_set:
                return statement
            return frog_ast.UniqueSample(
                statement.the_type,
                new_var,
                new_unique_set,
                statement.sampled_from,
                statement.surface_form,
            )
        if isinstance(statement, frog_ast.ReturnStatement):
            new_expression = self._value(statement.expression)
            if new_expression is statement.expression:
                return statement
            return frog_ast.ReturnStatement(new_expression)
        if isinstance(statement, frog_ast.IfStatement):
            new_conditions = [self._value(cond) for cond in statement.conditions]
            if all(
                new is old for new, old in zip(new_conditions, statement.conditions)
            ):
                return statement
            return frog_ast.IfStatement(new_conditions, list(statement.blocks))
        if isinstance(statement, frog_ast.NumericFor):
            new_start = self._value(statement.start)
            new_end = self._value(statement.end)
            if new_start is statement.start and new_end is statement.end:
                return statement
            return frog_ast.NumericFor(
                statement.name, new_start, new_end, statement.block
            )
        if isinstance(statement, frog_ast.GenericFor):
            new_over = self._value(statement.over)
            if new_over is statement.over:
                return statement
            return frog_ast.GenericFor(
                statement.var_type,
                statement.var_name,
                new_over,
                statement.block,
            )
        return statement


class NormalizeProductLiteral(TransformPass):
    name = "Normalize Product-Literal Tuples"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return NormalizeProductLiteralTransformer(ctx).transform(game)
