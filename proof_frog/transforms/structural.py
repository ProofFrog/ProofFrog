"""Structural passes: topological sort, remove duplicate/unnecessary fields.

These passes operate on the game structure as a whole rather than individual
expressions or blocks.
"""

from __future__ import annotations

import copy
import functools

from .. import frog_ast
from .. import visitors
from .. import dependencies
from .control_flow import RemoveStatementTransformer
from ._base import TransformPass, PipelineContext, NearMiss, _lookup_primitive_method


def _is_qualifying_bijection_call(
    var_name: str,
    bs_type: frog_ast.BitStringType,
    proof_namespace: frog_ast.Namespace,
    node: frog_ast.ASTNode,
) -> bool:
    """Check if *node* is ``Prim.Method(Variable(var_name))`` where Method is
    deterministic, injective, and has signature ``BitString<n> -> BitString<n>``
    matching *bs_type*.
    """
    if not isinstance(node, frog_ast.FuncCall):
        return False
    if len(node.args) != 1:
        return False
    arg = node.args[0]
    if not (isinstance(arg, frog_ast.Variable) and arg.name == var_name):
        return False
    method_sig = _lookup_primitive_method(node.func, proof_namespace)
    if method_sig is None:
        return False
    if not method_sig.deterministic or not method_sig.injective:
        return False
    if len(method_sig.parameters) != 1:
        return False
    param_type = method_sig.parameters[0].type
    ret_type = method_sig.return_type
    return (
        isinstance(param_type, frog_ast.BitStringType)
        and isinstance(ret_type, frog_ast.BitStringType)
        and param_type == ret_type
        and param_type == bs_type
    )


def _get_func_key(func_call: frog_ast.FuncCall) -> tuple[str, str]:
    """Return ``(prim_name, method_name)`` for a qualifying FuncCall."""
    assert isinstance(func_call.func, frog_ast.FieldAccess)
    assert isinstance(func_call.func.the_object, frog_ast.Variable)
    return (func_call.func.the_object.name, func_call.func.name)


class _BijectionReplacer(visitors.Transformer):
    """Replace qualifying ``f(x)`` calls with ``x`` for eligible variables."""

    def __init__(
        self,
        eligible: dict[str, tuple[str, str]],
        proof_namespace: frog_ast.Namespace,
    ) -> None:
        self.eligible = eligible
        self.proof_namespace = proof_namespace

    def transform_func_call(self, func_call: frog_ast.FuncCall) -> frog_ast.ASTNode:
        new_func = self.transform(func_call.func)
        new_args = [self.transform(arg) for arg in func_call.args]

        if (
            len(new_args) == 1
            and isinstance(new_args[0], frog_ast.Variable)
            and new_args[0].name in self.eligible
        ):
            var_name = new_args[0].name
            prim_name, method_name = self.eligible[var_name]
            if (
                isinstance(new_func, frog_ast.FieldAccess)
                and isinstance(new_func.the_object, frog_ast.Variable)
                and new_func.the_object.name == prim_name
                and new_func.name == method_name
            ):
                return new_args[0]

        result = copy.deepcopy(func_call)
        result.func = new_func
        result.args = new_args
        return result


def remove_duplicate_fields(game: frog_ast.Game) -> frog_ast.Game:
    """Remove fields that have the same type and always contain the same value."""
    for field in game.fields:
        for other_field in game.fields:
            if field.type == other_field.type and field.name < other_field.name:
                duplicated_statements = visitors.SameFieldVisitor(
                    (field.name, other_field.name)
                ).visit(game)
                if duplicated_statements is not None:
                    new_game = copy.deepcopy(game)
                    new_game.fields = [
                        the_field
                        for the_field in game.fields
                        if the_field.name != other_field.name
                    ]
                    ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                    ast_map.set(
                        frog_ast.Variable(other_field.name),
                        frog_ast.Variable(field.name),
                    )
                    return visitors.SubstitutionTransformer(ast_map).transform(
                        RemoveStatementTransformer(duplicated_statements).transform(
                            new_game
                        )
                    )
    return game


class TopologicalSort(TransformPass):
    name = "Topological Sorting"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        if ctx.sort_game_fn is None:
            return game
        return ctx.sort_game_fn(game)


class RemoveDuplicateFields(TransformPass):
    name = "Remove Duplicate Fields"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return remove_duplicate_fields(game)


class RemoveUnnecessaryFields(TransformPass):
    name = "Remove unnecessary statements and fields"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return dependencies.remove_unnecessary_fields(game)


class UniformBijectionElimination(TransformPass):
    """Replace ``f(x)`` with ``x`` when *x* is a uniform ``BitString<n>`` sample
    and *f* is a deterministic injective ``BitString<n> -> BitString<n>`` method.

    A deterministic injective function on a finite set of the same size is a
    bijection.  Applying a bijection to a uniform random variable preserves
    the uniform distribution, so ``f(x)`` and ``x`` are distributionally
    equivalent.

    The transform fires only when **every** read-use of *x* in the game is
    as the sole argument of the **same** qualifying function *f*.  If some
    uses are bare ``x`` and others are ``f(x)``, the joint distribution would
    change, so the transform correctly declines.
    """

    name = "Uniform Bijection Elimination"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        # Collect all uniform BitString<n> sample statements in the game.
        samples: list[tuple[str, frog_ast.BitStringType, frog_ast.Sample]] = []
        for method in game.methods:
            for sample in _collect_samples(method.block):
                if isinstance(sample.var, frog_ast.Variable) and isinstance(
                    sample.sampled_from, frog_ast.BitStringType
                ):
                    samples.append((sample.var.name, sample.sampled_from, sample))

        if not samples:
            return game

        # Deduplicate by variable name (a field may only be sampled once in
        # well-formed games; if sampled more than once, skip conservatively).
        seen: dict[str, tuple[frog_ast.BitStringType, frog_ast.Sample]] = {}
        duplicates: set[str] = set()
        for var_name, bs_type, sample_stmt in samples:
            if var_name in seen:
                duplicates.add(var_name)
            else:
                seen[var_name] = (bs_type, sample_stmt)

        eligible: dict[str, tuple[str, str]] = {}

        for var_name, (bs_type, sample_stmt) in seen.items():
            if var_name in duplicates:
                continue

            # Count total read-uses of var_name across the entire game.
            # Mask the defining Sample's LHS so it is not counted.
            total_uses = _count_var_reads(game, var_name)
            if total_uses == 0:
                continue

            # Count qualifying FuncCall wraps and check function consistency.
            wrap_count, func_key = _count_qualifying_wraps(
                game, var_name, bs_type, ctx.proof_namespace
            )

            if wrap_count == total_uses and func_key is not None:
                eligible[var_name] = func_key
            elif wrap_count > 0:
                ctx.near_misses.append(
                    NearMiss(
                        transform_name="Uniform Bijection Elimination",
                        reason=(
                            f"Bijection elimination did not fire for "
                            f"'{var_name}': {wrap_count} of {total_uses} "
                            f"uses are qualifying bijection wraps "
                            f"(need all uses to be wrapped)"
                        ),
                        location=sample_stmt.origin,
                        suggestion=(
                            f"Ensure every use of '{var_name}' is wrapped "
                            f"in the same deterministic injective function"
                        ),
                        variable=var_name,
                        method=None,
                    )
                )

        if not eligible:
            return game

        return _BijectionReplacer(eligible, ctx.proof_namespace).transform(game)


def _collect_samples(block: frog_ast.Block) -> list[frog_ast.Sample]:
    """Collect all Sample statements from a block, recursing into if-blocks."""
    result: list[frog_ast.Sample] = []
    for stmt in block.statements:
        if isinstance(stmt, frog_ast.Sample):
            result.append(stmt)
        elif isinstance(stmt, frog_ast.IfStatement):
            for branch_block in stmt.blocks:
                result.extend(_collect_samples(branch_block))
    return result


def _count_var_reads(
    game: frog_ast.Game,
    var_name: str,
) -> int:
    """Count read-uses of *var_name* in *game*, excluding the LHS of
    the defining Sample statement.
    """

    def _is_var(name: str, node: frog_ast.ASTNode) -> bool:
        return isinstance(node, frog_ast.Variable) and node.name == name

    # Mask the defining sample's LHS so it is not counted as a read.
    masked_game = copy.deepcopy(game)
    placeholder = frog_ast.Variable(var_name + "__def_masked__")
    masked_game = visitors.ReplaceTransformer(
        _find_sample_lhs(masked_game, var_name),
        placeholder,
    ).transform(masked_game)

    count = 0
    counting_game = masked_game
    while True:
        found = visitors.SearchVisitor(functools.partial(_is_var, var_name)).visit(
            counting_game
        )
        if found is None:
            break
        count += 1
        counting_game = visitors.ReplaceTransformer(
            found, frog_ast.Variable(var_name + "__counted__")
        ).transform(counting_game)
    return count


def _find_sample_lhs(
    game: frog_ast.Game,
    var_name: str,
) -> frog_ast.ASTNode:
    """Find the Variable node on the LHS of the first matching Sample in *game*.

    Used on a deep-copied game to locate the node corresponding to the defining
    sample's LHS so it can be masked before counting read-uses.
    """
    for method in game.methods:
        for sample in _collect_samples(method.block):
            if (
                isinstance(sample.var, frog_ast.Variable)
                and sample.var.name == var_name
                and isinstance(sample.sampled_from, frog_ast.BitStringType)
            ):
                return sample.var
    # Fallback: return a dummy that won't match anything.
    return frog_ast.Variable(var_name + "__not_found__")


def _count_qualifying_wraps(
    game: frog_ast.Game,
    var_name: str,
    bs_type: frog_ast.BitStringType,
    proof_namespace: frog_ast.Namespace,
) -> tuple[int, tuple[str, str] | None]:
    """Count FuncCall nodes wrapping *var_name* that qualify as bijections.

    Returns ``(wrap_count, func_key)`` where *func_key* is
    ``(prim_name, method_name)`` if all wraps use the same function, or
    ``None`` if functions are inconsistent.
    """
    predicate = functools.partial(
        _is_qualifying_bijection_call, var_name, bs_type, proof_namespace
    )

    count = 0
    func_key: tuple[str, str] | None = None
    consistent = True
    counting_game = copy.deepcopy(game)
    while True:
        found = visitors.SearchVisitor(predicate).visit(counting_game)
        if found is None:
            break
        assert isinstance(found, frog_ast.FuncCall)
        count += 1
        this_key = _get_func_key(found)
        if func_key is None:
            func_key = this_key
        elif func_key != this_key:
            consistent = False
            break
        counting_game = visitors.ReplaceTransformer(
            found, frog_ast.Variable(var_name + "__wrap_counted__")
        ).transform(counting_game)

    if not consistent:
        return (count, None)
    return (count, func_key)
