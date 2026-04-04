"""Random-function simplification pass.

When every call to a ``RandomFunctions`` field ``RF`` in a game uses an
argument that was uniquely sampled (via ``<-uniq``) from a consistent set,
each ``z = RF(r)`` can be replaced with ``z <- R``.

Soundness: unique sampling from a consistent set guarantees every RF query
is on a distinct, previously-unseen input, so each result is an independent
uniform sample from the range type.
"""

from __future__ import annotations

import copy
import functools
from dataclasses import dataclass, field

from .. import frog_ast
from ..visitors import BlockTransformer, SearchVisitor, ReplaceTransformer
from ._base import TransformPass, PipelineContext, NearMiss, _lookup_primitive_method


@dataclass
class _RFCallSite:
    """A call ``z = RF(r)`` found during analysis."""

    rf_name: str
    arg_name: str
    unique_set_name: str


@dataclass
class _RFAnalysis:
    """Per-RF analysis result."""

    eligible: bool = True
    call_sites: list[_RFCallSite] = field(default_factory=list)
    unique_set_name: str | None = None


def _get_unique_set_name(expr: frog_ast.Expression) -> str:
    """Return a canonical string for the set used in a <-uniq statement."""
    if isinstance(expr, frog_ast.Variable):
        return expr.name
    if isinstance(expr, frog_ast.FieldAccess) and isinstance(
        expr.the_object, frog_ast.Variable
    ):
        return f"{expr.the_object.name}.{expr.name}"
    return str(expr)


def _analyze_rf_eligibility(
    game: frog_ast.Game,
    rf_types: dict[str, frog_ast.RandomFunctionType],
) -> dict[str, _RFAnalysis]:
    """Check whether each RF field's calls are all guarded by <-uniq on a
    consistent set.

    Returns a dict mapping RF field name to its analysis result.
    """
    analysis: dict[str, _RFAnalysis] = {name: _RFAnalysis() for name in rf_types}

    for method in game.methods:
        _analyze_block(method.block, analysis, rf_types)

    return analysis


def _analyze_block(
    block: frog_ast.Block,
    analysis: dict[str, _RFAnalysis],
    rf_types: dict[str, frog_ast.RandomFunctionType],
) -> None:
    """Analyze a block for RF calls and their <-uniq guards."""
    # Build map: variable name -> unique set name (from <-uniq in this block)
    uniq_guards: dict[str, str] = {}

    for statement in block.statements:
        # Track <-uniq bindings
        if isinstance(statement, frog_ast.UniqueSample) and isinstance(
            statement.var, frog_ast.Variable
        ):
            uniq_guards[statement.var.name] = _get_unique_set_name(statement.unique_set)

        # Check RF calls in assignments
        if (
            isinstance(statement, frog_ast.Assignment)
            and isinstance(statement.value, frog_ast.FuncCall)
            and isinstance(statement.value.func, frog_ast.Variable)
            and statement.value.func.name in rf_types
            and len(statement.value.args) == 1
        ):
            rf_name = statement.value.func.name
            rf_analysis = analysis[rf_name]
            arg = statement.value.args[0]

            if not isinstance(arg, frog_ast.Variable):
                rf_analysis.eligible = False
                continue

            if arg.name not in uniq_guards:
                rf_analysis.eligible = False
                continue

            set_name = uniq_guards[arg.name]

            # If RF.domain is the set, verify it matches this RF
            if "." in set_name:
                obj_name, field_name = set_name.split(".", 1)
                if field_name == "domain" and obj_name != rf_name:
                    rf_analysis.eligible = False
                    continue

            # Check set consistency across all call sites
            if rf_analysis.unique_set_name is None:
                rf_analysis.unique_set_name = set_name
            elif rf_analysis.unique_set_name != set_name:
                rf_analysis.eligible = False
                continue

            rf_analysis.call_sites.append(
                _RFCallSite(
                    rf_name=rf_name,
                    arg_name=arg.name,
                    unique_set_name=set_name,
                )
            )

        # Recurse into nested blocks
        if isinstance(statement, frog_ast.IfStatement):
            for nested_block in statement.blocks:
                _analyze_block(nested_block, analysis, rf_types)
        elif isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
            _analyze_block(statement.block, analysis, rf_types)


class _RFCallExtractor(BlockTransformer):
    """Extract RF calls embedded in expressions into separate assignments.

    Transforms ``return [v1, m + RF(v1)]`` into::

        RangeType __rf_extract_0 = RF(v1);
        return [v1, m + __rf_extract_0];

    This enables ``_RFCallReplacer`` to detect and simplify the call.
    """

    def __init__(
        self,
        rf_names: set[str],
        rf_types: dict[str, frog_ast.RandomFunctionType],
    ) -> None:
        self.rf_names = rf_names
        self.rf_types = rf_types
        self.counter = 0

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            # Skip assignments where the value IS the RF call (already handled)
            if (
                isinstance(statement, frog_ast.Assignment)
                and isinstance(statement.value, frog_ast.FuncCall)
                and isinstance(statement.value.func, frog_ast.Variable)
                and statement.value.func.name in self.rf_names
            ):
                continue

            def is_rf_call(node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(node, frog_ast.FuncCall)
                    and isinstance(node.func, frog_ast.Variable)
                    and node.func.name in self.rf_names
                )

            found = SearchVisitor(is_rf_call).visit(statement)
            if found is None:
                continue

            assert isinstance(found, frog_ast.FuncCall)
            assert isinstance(found.func, frog_ast.Variable)
            rf_name = found.func.name
            range_type = copy.deepcopy(self.rf_types[rf_name].range_type)

            var_name = f"__rf_extract_{self.counter}__"
            self.counter += 1

            new_assignment = frog_ast.Assignment(
                range_type,  # type: ignore[arg-type]
                frog_ast.Variable(var_name),
                copy.deepcopy(found),
            )

            new_statement = ReplaceTransformer(
                found, frog_ast.Variable(var_name)
            ).transform(statement)

            new_stmts = (
                list(block.statements[:index])
                + [new_assignment, new_statement]
                + list(block.statements[index + 1 :])
            )
            return self.transform_block(frog_ast.Block(new_stmts))

        return block


class _RFCallReplacer(BlockTransformer):
    """Replace ``z = RF(r)`` with ``z <- R`` for eligible RF fields."""

    def __init__(
        self,
        eligible_rfs: dict[str, frog_ast.RandomFunctionType],
    ) -> None:
        self.eligible_rfs = eligible_rfs

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not (
                isinstance(statement, frog_ast.Assignment)
                and isinstance(statement.value, frog_ast.FuncCall)
                and isinstance(statement.value.func, frog_ast.Variable)
                and statement.value.func.name in self.eligible_rfs
            ):
                continue

            rf_name = statement.value.func.name
            range_type = self.eligible_rfs[rf_name].range_type

            # Type is used as Expression in sampling (DSL convention)
            new_sample = frog_ast.Sample(
                statement.the_type,
                copy.deepcopy(statement.var),
                copy.deepcopy(range_type),  # type: ignore[arg-type]
            )

            new_stmts = (
                list(block.statements[:index])
                + [new_sample]
                + list(block.statements[index + 1 :])
            )
            return self.transform_block(frog_ast.Block(new_stmts))

        return block


class UniqueRFSimplificationTransformer(BlockTransformer):
    """Standalone variant that resolves RF types from Sample statements
    in the same block.  Used in unit tests where RF is declared locally."""

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        # Discover RF types from Sample statements in this block
        rf_types: dict[str, frog_ast.RandomFunctionType] = {}
        for stmt in block.statements:
            if (
                isinstance(stmt, frog_ast.Sample)
                and isinstance(stmt.sampled_from, frog_ast.RandomFunctionType)
                and isinstance(stmt.var, frog_ast.Variable)
            ):
                rf_types[stmt.var.name] = stmt.sampled_from

        if not rf_types:
            return block

        # Build a temporary game to run analysis on
        dummy_game = frog_ast.Game(
            (
                "_Dummy",
                [],
                [],
                [
                    frog_ast.Method(
                        frog_ast.MethodSignature("f", frog_ast.Void(), []),
                        block,
                    )
                ],
                [],
            )
        )
        analysis = _analyze_rf_eligibility(dummy_game, rf_types)
        eligible = {
            name: rf_types[name] for name, result in analysis.items() if result.eligible
        }

        if not eligible:
            return block

        return _RFCallReplacer(eligible).transform_block(block)


class UniqueRFSimplification(TransformPass):
    name = "Unique RF Simplification"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        rf_types: dict[str, frog_ast.RandomFunctionType] = {}
        for rf_field in game.fields:
            if isinstance(rf_field.type, frog_ast.RandomFunctionType):
                rf_types[rf_field.name] = rf_field.type

        if not rf_types:
            return game

        analysis = _analyze_rf_eligibility(game, rf_types)
        eligible = {
            name: rf_types[name] for name, result in analysis.items() if result.eligible
        }

        if not eligible:
            return game

        return _RFCallReplacer(eligible).transform(game)


class ExtractRFCalls(TransformPass):
    """Extract RF field calls embedded in expressions into separate assignments."""

    name = "Extract RF Calls"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        rf_types: dict[str, frog_ast.RandomFunctionType] = {}
        for rf_field in game.fields:
            if isinstance(rf_field.type, frog_ast.RandomFunctionType):
                rf_types[rf_field.name] = rf_field.type

        if not rf_types:
            return game

        return _RFCallExtractor(set(rf_types.keys()), rf_types).transform(game)


# ---------------------------------------------------------------------------
# Local RF single-call -> uniform sample
# ---------------------------------------------------------------------------


def _rf_call_in_loop(block: frog_ast.Block, rf_name: str) -> bool:
    """Return True if an RF call to *rf_name* appears inside a loop body."""
    for stmt in block.statements:
        if isinstance(stmt, (frog_ast.NumericFor, frog_ast.GenericFor)):

            def is_rf_call(name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(node, frog_ast.FuncCall)
                    and isinstance(node.func, frog_ast.Variable)
                    and node.func.name == name
                )

            if (
                SearchVisitor(functools.partial(is_rf_call, rf_name)).visit(stmt.block)
                is not None
            ):
                return True
        elif isinstance(stmt, frog_ast.IfStatement):
            for branch_block in stmt.blocks:
                if _rf_call_in_loop(branch_block, rf_name):
                    return True
    return False


def _count_rf_calls(block: frog_ast.Block, rf_name: str) -> tuple[int, int]:
    """Count RF calls and non-call references to *rf_name* in a block.

    Returns ``(call_count, field_access_count)``.  Field accesses are
    references like ``RF.domain`` that prevent simplification.  The
    ``Variable("RF")`` inside ``FuncCall(RF, x)`` is not counted separately.
    """
    counts: list[int] = [0, 0]  # [calls, field_accesses]

    def counter(name: str, node: frog_ast.ASTNode) -> bool:
        if (
            isinstance(node, frog_ast.FuncCall)
            and isinstance(node.func, frog_ast.Variable)
            and node.func.name == name
        ):
            counts[0] += 1
            return False
        if (
            isinstance(node, frog_ast.FieldAccess)
            and isinstance(node.the_object, frog_ast.Variable)
            and node.the_object.name == name
        ):
            counts[1] += 1
            return False
        return False

    SearchVisitor(functools.partial(counter, rf_name)).visit(block)
    return counts[0], counts[1]


class LocalRFToUniformTransformer(BlockTransformer):
    """Replace a locally-sampled RF called exactly once with a uniform sample.

    A ``RandomFunctions`` variable that is sampled locally and called once on
    any input produces a uniform sample from its range type, because a fresh
    random function evaluated on a single input is an independent uniform draw.

    Conditions:

    - RF is declared via a local ``Sample`` (has ``the_type``, not a bare
      field sample)
    - RF is called exactly once in the remaining block (including branches)
    - RF is not referenced in any other context (e.g., ``RF.domain``)
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for sample_idx, stmt in enumerate(block.statements):
            if not (
                isinstance(stmt, frog_ast.Sample)
                and isinstance(stmt.sampled_from, frog_ast.RandomFunctionType)
                and isinstance(stmt.var, frog_ast.Variable)
            ):
                continue

            rf_name = stmt.var.name
            rf_type = stmt.sampled_from

            # Verify this is a local RF (typed sample, or bare sample preceded
            # by a matching VariableDeclaration)
            if stmt.the_type is None:
                has_decl = any(
                    isinstance(s, frog_ast.VariableDeclaration)
                    and s.name == rf_name
                    and isinstance(s.type, frog_ast.RandomFunctionType)
                    for s in block.statements[:sample_idx]
                )
                if not has_decl:
                    continue

            remaining = frog_ast.Block(block.statements[sample_idx + 1 :])

            call_count, other_ref_count = _count_rf_calls(remaining, rf_name)

            if call_count != 1 or other_ref_count > 0:
                if self.ctx is not None and call_count > 0:
                    if call_count != 1:
                        reason = (
                            f"Random function call not simplified: "
                            f"RF '{rf_name}' called {call_count} times "
                            f"(need exactly 1)"
                        )
                    else:
                        reason = (
                            "Random function call not simplified: "
                            f"RF '{rf_name}' has other non-call references"
                        )
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Local RF To Uniform",
                            reason=reason,
                            location=stmt.origin,
                            suggestion=None,
                            variable=rf_name,
                            method=None,
                        )
                    )
                continue

            # Reject if the RF call is inside a loop (the single syntactic
            # call would execute multiple times per RF instantiation)
            if _rf_call_in_loop(remaining, rf_name):
                continue

            # Try _RFCallReplacer (handles z = RF(x) in assignments)
            new_remaining = _RFCallReplacer({rf_name: rf_type}).transform(remaining)

            if new_remaining == remaining:
                # Also handle RF calls in return statements and other
                # embedded positions by extracting then replacing
                new_remaining = _RFCallExtractor(
                    {rf_name}, {rf_name: rf_type}
                ).transform(remaining)
                if new_remaining != remaining:
                    new_remaining = _RFCallReplacer({rf_name: rf_type}).transform(
                        new_remaining
                    )

            if new_remaining != remaining:
                new_stmts = list(block.statements[: sample_idx + 1]) + list(
                    new_remaining.statements
                )
                return self.transform_block(frog_ast.Block(new_stmts))

        return block


class LocalRFToUniform(TransformPass):
    """Replace locally-sampled RFs called once with uniform samples."""

    name = "Local RF To Uniform"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return LocalRFToUniformTransformer(ctx).transform(game)


# ---------------------------------------------------------------------------
# Challenge exclusion: RF(unique_input) -> uniform in Initialize
# ---------------------------------------------------------------------------


def _extract_field_names_from_expr(
    expr: frog_ast.Expression, field_names: list[str]
) -> set[str]:
    """Extract field variable names from an expression (recursing into tuples)."""
    result: set[str] = set()
    if isinstance(expr, frog_ast.Variable) and expr.name in field_names:
        result.add(expr.name)
    elif isinstance(expr, frog_ast.Tuple):
        for v in expr.values:
            result.update(_extract_field_names_from_expr(v, field_names))
    return result


def _extract_non_field_vars(
    expr: frog_ast.Expression, field_names: list[str]
) -> set[str]:
    """Extract non-field variable names from an expression (recursing into tuples)."""
    result: set[str] = set()
    if isinstance(expr, frog_ast.Variable) and expr.name not in field_names:
        result.add(expr.name)
    elif isinstance(expr, frog_ast.Tuple):
        for v in expr.values:
            result.update(_extract_non_field_vars(v, field_names))
    return result


def _find_challenge_guard(
    method: frog_ast.Method,
    field_names: list[str],
) -> tuple[set[str], set[str], int] | None:
    """Find a challenge exclusion guard at the top of an oracle method.

    Looks for the pattern:
        if (param_expr == [field_a, field_b, ...]) { return None/value; }
    or:
        if (param_expr == field_a) { return None/value; }

    at the start of the method body (possibly after local assignments).

    Returns (challenge field names, guard LHS variable names,
    index of the if-statement) or None.
    """
    for idx, stmt in enumerate(method.block.statements):
        if not isinstance(stmt, frog_ast.IfStatement):
            continue
        if not stmt.conditions:
            continue
        cond = stmt.conditions[0]
        if not isinstance(cond, frog_ast.BinaryOperation):
            continue
        if cond.operator != frog_ast.BinaryOperators.EQUALS:
            continue

        # Check if the guard returns early (return in the first block)
        if not stmt.blocks[0].statements:
            continue
        if not isinstance(stmt.blocks[0].statements[-1], frog_ast.ReturnStatement):
            continue

        # Extract challenge fields from the right side of the comparison
        rhs = cond.right_expression
        challenge_fields = _extract_field_names_from_expr(rhs, field_names)

        # Extract LHS variable names (non-field variables constrained by guard)
        lhs = cond.left_expression
        guard_lhs_vars = _extract_non_field_vars(lhs, field_names)

        if challenge_fields:
            return challenge_fields, guard_lhs_vars, idx

    return None


def _collect_field_vars(expr: frog_ast.Expression, field_names: list[str]) -> set[str]:
    """Collect all field variable names referenced in an expression."""
    found: set[str] = set()

    def searcher(node: frog_ast.ASTNode) -> bool:
        if isinstance(node, frog_ast.Variable) and node.name in field_names:
            found.add(node.name)
        return False

    SearchVisitor(searcher).visit(expr)
    return found


def _collect_rf_call_sites(
    block: frog_ast.Block,
    rf_name: str,
) -> list[frog_ast.FuncCall]:
    """Collect all RF call sites in a block (recursing into sub-blocks)."""
    sites: list[frog_ast.FuncCall] = []

    def finder(node: frog_ast.ASTNode) -> bool:
        if (
            isinstance(node, frog_ast.FuncCall)
            and isinstance(node.func, frog_ast.Variable)
            and node.func.name == rf_name
        ):
            sites.append(node)
        return False

    SearchVisitor(finder).visit(block)
    return sites


def _is_injective_call(
    func: frog_ast.Expression,
    proof_namespace: frog_ast.Namespace,
) -> bool:
    """Check if a FuncCall targets a primitive method marked ``injective``."""
    m = _lookup_primitive_method(func, proof_namespace)
    return m is not None and m.injective


# pylint: disable=too-many-arguments,too-many-positional-arguments
def _rf_args_structurally_differ(
    init_arg: frog_ast.Expression,
    oracle_arg: frog_ast.Expression,
    challenge_fields: set[str],
    field_names: list[str],
    guard_vars: set[str],
    proof_namespace: frog_ast.Namespace,
) -> bool:
    """Check if Init and oracle RF args differ at a challenge field position.

    For tuple arguments, checks each position. For concatenation sub-expressions,
    flattens and checks leaf operands. For calls to injective functions, recurses
    into arguments.
    """

    def _flatten_concat(expr: frog_ast.Expression) -> list[frog_ast.Expression]:
        if (
            isinstance(expr, frog_ast.BinaryOperation)
            and expr.operator == frog_ast.BinaryOperators.OR
        ):
            return _flatten_concat(expr.left_expression) + _flatten_concat(
                expr.right_expression
            )
        return [expr]

    def _check_leaf_pair(
        init_leaf: frog_ast.Expression, oracle_leaf: frog_ast.Expression
    ) -> bool:
        """True if init_leaf is a challenge field and oracle_leaf is a
        guard-constrained non-field variable."""
        if not isinstance(init_leaf, frog_ast.Variable):
            return False
        if init_leaf.name not in challenge_fields:
            return False
        # Oracle leaf must be a non-field variable that is constrained by the guard
        if isinstance(oracle_leaf, frog_ast.Variable):
            return (
                oracle_leaf.name not in field_names and oracle_leaf.name in guard_vars
            )
        return False

    def _check_exprs(
        init_e: frog_ast.Expression, oracle_e: frog_ast.Expression
    ) -> bool:
        # Direct leaf comparison
        if _check_leaf_pair(init_e, oracle_e):
            return True
        # Tuple: check each position
        if isinstance(init_e, frog_ast.Tuple) and isinstance(oracle_e, frog_ast.Tuple):
            if len(init_e.values) == len(oracle_e.values):
                return any(
                    _check_exprs(a, b) for a, b in zip(init_e.values, oracle_e.values)
                )
        # FuncCall to same injective function: recurse into arguments
        if isinstance(init_e, frog_ast.FuncCall) and isinstance(
            oracle_e, frog_ast.FuncCall
        ):
            if (
                init_e.func == oracle_e.func
                and len(init_e.args) == len(oracle_e.args)
                and _is_injective_call(init_e.func, proof_namespace)
            ):
                if any(_check_exprs(a, b) for a, b in zip(init_e.args, oracle_e.args)):
                    return True
        # Concatenation: flatten and check recursively
        init_leaves = _flatten_concat(init_e)
        oracle_leaves = _flatten_concat(oracle_e)
        if len(init_leaves) > 1 and len(init_leaves) == len(oracle_leaves):
            return any(_check_exprs(a, b) for a, b in zip(init_leaves, oracle_leaves))
        return False

    return _check_exprs(init_arg, oracle_arg)


class ChallengeExclusionRFToUniformTransformer:
    """Replace an RF field call in Initialize with a uniform sample when the
    call's input is guaranteed distinct from all oracle RF calls by a
    challenge exclusion guard.

    See docs/plans/2026-03-16-rf-challenge-exclusion-design.md for the full
    design and soundness argument.
    """

    def transform(
        self,
        game: frog_ast.Game,
        proof_namespace: frog_ast.Namespace | None = None,
    ) -> frog_ast.Game:
        """Transform a game, replacing qualifying RF calls with uniform samples."""
        if proof_namespace is None:
            proof_namespace = {}
        field_names = [f.name for f in game.fields]
        rf_fields: dict[str, frog_ast.RandomFunctionType] = {}
        for f in game.fields:
            if isinstance(f.type, frog_ast.RandomFunctionType):
                rf_fields[f.name] = f.type

        if not rf_fields:
            return game

        # Identify Initialize method
        init_method = None
        oracle_methods: list[frog_ast.Method] = []
        for method in game.methods:
            if method.signature.name == "Initialize":
                init_method = method
            else:
                oracle_methods.append(method)

        if init_method is None:
            return game

        for rf_name, rf_type in rf_fields.items():
            # Collect Init RF call sites (only standalone assignments)
            init_calls: list[tuple[int, frog_ast.Assignment]] = []
            for idx, stmt in enumerate(init_method.block.statements):
                if (
                    isinstance(stmt, frog_ast.Assignment)
                    and isinstance(stmt.value, frog_ast.FuncCall)
                    and isinstance(stmt.value.func, frog_ast.Variable)
                    and stmt.value.func.name == rf_name
                    and len(stmt.value.args) == 1
                ):
                    init_calls.append((idx, stmt))

            if len(init_calls) != 1:
                continue

            init_idx, init_stmt = init_calls[0]
            assert isinstance(init_stmt.value, frog_ast.FuncCall)
            init_arg = init_stmt.value.args[0]

            # Check that Init arg references at least one challenge field
            init_field_refs = _collect_field_vars(init_arg, field_names)

            # Check each oracle method
            all_oracle_ok = True
            for oracle_method in oracle_methods:
                guard_result = _find_challenge_guard(oracle_method, field_names)
                if guard_result is None:
                    # No guard -- check if there are any RF calls at all
                    oracle_rf_calls = _collect_rf_call_sites(
                        oracle_method.block, rf_name
                    )
                    if oracle_rf_calls:
                        all_oracle_ok = False
                        break
                    continue

                challenge_fields, guard_lhs_vars, guard_idx = guard_result

                # Extend guard vars with variables derived from guard LHS
                # (e.g., v4 = c[0] where c is the guard parameter)
                for post_stmt in oracle_method.block.statements[guard_idx + 1 :]:
                    if (
                        isinstance(post_stmt, frog_ast.Assignment)
                        and isinstance(post_stmt.var, frog_ast.Variable)
                        and isinstance(post_stmt.value, frog_ast.ArrayAccess)
                        and isinstance(post_stmt.value.the_array, frog_ast.Variable)
                        and post_stmt.value.the_array.name in guard_lhs_vars
                    ):
                        guard_lhs_vars.add(post_stmt.var.name)

                # Init arg must reference at least one challenge field
                if not init_field_refs & challenge_fields:
                    all_oracle_ok = False
                    break

                # All oracle RF calls must be AFTER the guard
                pre_guard_block = frog_ast.Block(
                    list(oracle_method.block.statements[:guard_idx])
                )
                pre_guard_calls = _collect_rf_call_sites(pre_guard_block, rf_name)
                if pre_guard_calls:
                    all_oracle_ok = False
                    break

                # Check structural difference for post-guard RF calls
                post_guard_block = frog_ast.Block(
                    list(oracle_method.block.statements[guard_idx + 1 :])
                )
                guard_stmt = oracle_method.block.statements[guard_idx]
                assert isinstance(guard_stmt, frog_ast.IfStatement)

                # Check inside the guard's return-early block (blocks[0]).
                # If RF is called there, the input equals the challenge field
                # (guard condition is true), matching the Initialize RF input.
                guard_body_calls = _collect_rf_call_sites(guard_stmt.blocks[0], rf_name)
                if guard_body_calls:
                    all_oracle_ok = False
                    break

                # Also check inside the guard's else/else-if blocks
                extra_blocks = list(guard_stmt.blocks[1:])

                all_post_calls = _collect_rf_call_sites(post_guard_block, rf_name)
                for eb in extra_blocks:
                    all_post_calls.extend(_collect_rf_call_sites(eb, rf_name))

                for call in all_post_calls:
                    if len(call.args) != 1:
                        all_oracle_ok = False
                        break
                    if not _rf_args_structurally_differ(
                        init_arg,
                        call.args[0],
                        challenge_fields,
                        field_names,
                        guard_lhs_vars,
                        proof_namespace,
                    ):
                        all_oracle_ok = False
                        break

                if not all_oracle_ok:
                    break

            if not all_oracle_ok:
                continue

            # Pattern matched -- replace Init RF call with uniform sample
            new_game = copy.deepcopy(game)
            new_init = None
            for m in new_game.methods:
                if m.signature.name == "Initialize":
                    new_init = m
                    break
            assert new_init is not None

            old_stmt = new_init.block.statements[init_idx]
            assert isinstance(old_stmt, frog_ast.Assignment)
            new_sample = frog_ast.Sample(
                old_stmt.the_type,
                copy.deepcopy(old_stmt.var),
                copy.deepcopy(rf_type.range_type),  # type: ignore[arg-type]
            )
            new_stmts = (
                list(new_init.block.statements[:init_idx])
                + [new_sample]
                + list(new_init.block.statements[init_idx + 1 :])
            )
            new_init.block = frog_ast.Block(new_stmts)
            return new_game

        return game


class ChallengeExclusionRFToUniform(TransformPass):
    """Replace RF field calls in Initialize with uniform samples when excluded."""

    name = "Challenge Exclusion RF To Uniform"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ChallengeExclusionRFToUniformTransformer().transform(
            game, proof_namespace=ctx.proof_namespace
        )
