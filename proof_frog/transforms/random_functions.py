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
from ._base import TransformPass, PipelineContext


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
        return LocalRFToUniformTransformer().transform(game)
