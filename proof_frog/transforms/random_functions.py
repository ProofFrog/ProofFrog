"""Random-function simplification pass.

When every call to a ``Function`` field ``RF`` in a game uses an
argument that was uniquely sampled (via ``<-uniq``) from a consistent set,
each ``z = RF(r)`` can be replaced with ``z <- R``.

Soundness: unique sampling from a consistent set guarantees every RF query
is on a distinct, previously-unseen input, so each result is an independent
uniform sample from the range type.
"""

# _ast_to_sympy duplicates semantic_analysis._ast_to_sympy to avoid a
# cyclic import (proof_engine -> pipelines -> random_functions -> semantic_analysis).
# pylint: disable=duplicate-code

from __future__ import annotations

import copy
import functools
from dataclasses import dataclass, field
from sympy import Rational, Symbol, simplify as sympy_simplify

from .. import frog_ast
from ..visitors import BlockTransformer, SearchVisitor, ReplaceTransformer, Transformer
from ._base import (
    TransformPass,
    PipelineContext,
    NearMiss,
    _lookup_primitive_method,
    has_nondeterministic_call,
)


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


def _exclusion_set_modified(game: frog_ast.Game, set_name: str) -> bool:
    """Check if the exclusion set is explicitly assigned in any method.

    FrogLang semantics implicitly maintain exclusion sets used in
    ``<-uniq[S]`` statements.  If user code explicitly assigns to the
    set variable, the implicit maintenance is compromised.

    For dotted names like ``RF.domain``, the domain is implicitly
    maintained by the random function's own semantics (querying RF(r)
    adds r to RF.domain).  The RF itself may be initialized via a
    Sample statement — that is not a modification.  Only plain set
    fields (non-dotted names) are checked for modifications.

    Returns True if a problematic modification is found.
    """
    # RF.domain sets are implicitly maintained by the RF's semantics.
    # The RF initialization (Sample) is not a modification.
    if "." in set_name:
        return False

    def _is_set_assign(node: frog_ast.ASTNode) -> bool:
        if not isinstance(
            node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            return False
        var = node.var
        # Direct assignment: S = ...
        if isinstance(var, frog_ast.Variable) and var.name == set_name:
            # Typed declaration (field initializer) is OK — that's the
            # initial empty set.  Untyped assignment is a modification.
            if isinstance(node, frog_ast.Assignment) and node.the_type is not None:
                return False
            return True
        # Element assignment: S[k] = ...
        if isinstance(var, frog_ast.ArrayAccess) and isinstance(
            var.the_array, frog_ast.Variable
        ):
            if var.the_array.name == set_name:
                return True
        return False

    for method in game.methods:
        if SearchVisitor(_is_set_assign).visit(method.block) is not None:
            return True
    return False


def _analyze_rf_eligibility(
    game: frog_ast.Game,
    rf_types: dict[str, frog_ast.FunctionType],
) -> dict[str, _RFAnalysis]:
    """Check whether each RF field's calls are all guarded by <-uniq on a
    consistent set.

    Returns a dict mapping RF field name to its analysis result.
    """
    analysis: dict[str, _RFAnalysis] = {name: _RFAnalysis() for name in rf_types}
    field_names = {f.name for f in game.fields}

    for method in game.methods:
        _analyze_block(method.block, analysis, rf_types, field_names)

    # Post-analysis: reject RFs where any argument variable is used more
    # than once across call sites (RF is a function, so same input must
    # produce same output — replacing with independent samples is wrong).
    for rf_analysis in analysis.values():
        if not rf_analysis.eligible:
            continue
        seen_args: set[str] = set()
        for site in rf_analysis.call_sites:
            if site.arg_name in seen_args:
                rf_analysis.eligible = False
                break
            seen_args.add(site.arg_name)

    # Post-analysis: reject RFs whose exclusion set is explicitly modified.
    # FrogLang semantics implicitly maintain exclusion sets (<-uniq[S] adds
    # the sampled value to S automatically). If user code explicitly assigns
    # to S, the implicit maintenance is compromised and cross-call uniqueness
    # is not guaranteed.
    for rf_analysis in analysis.values():
        if not rf_analysis.eligible or rf_analysis.unique_set_name is None:
            continue
        set_name = rf_analysis.unique_set_name
        if _exclusion_set_modified(game, set_name):
            rf_analysis.eligible = False

    return analysis


def _analyze_block(
    block: frog_ast.Block,
    analysis: dict[str, _RFAnalysis],
    rf_types: dict[str, frog_ast.FunctionType],
    field_names: set[str] | None = None,
) -> None:
    """Analyze a block for RF calls and their <-uniq guards."""
    # Build map: variable name -> unique set name (from <-uniq in this block)
    uniq_guards: dict[str, str] = {}

    for statement in block.statements:
        # Track <-uniq bindings
        if isinstance(statement, frog_ast.UniqueSample) and isinstance(
            statement.var, frog_ast.Variable
        ):
            set_name = _get_unique_set_name(statement.unique_set)
            # The unique set must be a game field (persistent across oracle
            # calls) to guarantee cross-call distinctness.  A local set
            # resets each call, so the same value could be drawn across calls.
            if field_names is not None:
                raw_name = set_name.split(".")[0] if "." in set_name else set_name
                if raw_name not in field_names:
                    # Local set — don't trust it for cross-call uniqueness.
                    # Mark any RF whose calls use this argument as ineligible
                    # (handled below by not adding to uniq_guards).
                    continue
            uniq_guards[statement.var.name] = set_name

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
                _analyze_block(nested_block, analysis, rf_types, field_names)
        elif isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
            _analyze_block(statement.block, analysis, rf_types, field_names)


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
        rf_types: dict[str, frog_ast.FunctionType],
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
        eligible_rfs: dict[str, frog_ast.FunctionType],
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
        rf_types: dict[str, frog_ast.FunctionType] = {}
        for stmt in block.statements:
            if (
                isinstance(stmt, frog_ast.Sample)
                and isinstance(stmt.sampled_from, frog_ast.FunctionType)
                and isinstance(stmt.var, frog_ast.Variable)
            ):
                rf_types[stmt.var.name] = stmt.sampled_from

        if not rf_types:
            return block

        # Run analysis directly on this block (no field-scope check
        # since this standalone transformer is used for unit tests
        # where RF is declared locally in the same block).
        analysis: dict[str, _RFAnalysis] = {name: _RFAnalysis() for name in rf_types}
        _analyze_block(block, analysis, rf_types)
        eligible = {
            name: rf_types[name] for name, result in analysis.items() if result.eligible
        }

        if not eligible:
            return block

        return _RFCallReplacer(eligible).transform_block(block)


class UniqueRFSimplification(TransformPass):
    name = "Unique RF Simplification"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        rf_types: dict[str, frog_ast.FunctionType] = {}
        for rf_field in game.fields:
            if isinstance(rf_field.type, frog_ast.FunctionType):
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
        rf_types: dict[str, frog_ast.FunctionType] = {}
        for rf_field in game.fields:
            if isinstance(rf_field.type, frog_ast.FunctionType):
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

    A ``Function`` variable that is sampled locally and called once on
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
                and isinstance(stmt.sampled_from, frog_ast.FunctionType)
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
                    and isinstance(s.type, frog_ast.FunctionType)
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
# Local RF called on distinct literal constants -> independent uniform samples
# ---------------------------------------------------------------------------


def _literal_key(expr: frog_ast.Expression) -> tuple[str, ...] | None:
    """Return a canonical key for a literal bitstring expression.

    The key is a tuple ``("bits", length_str, value_str)`` where:

    - ``length_str`` stringifies the bit length (concrete integer or
      symbolic expression).
    - ``value_str`` stringifies the integer value that the literal
      represents as an unsigned big-endian bitstring.

    This unifies the two source-level literal forms:

    - ``BinaryNum(num, length)`` directly provides the integer value.
    - ``BitStringLiteral(bit=0, length=n)`` is the all-zero n-bit string,
      integer value 0.
    - ``BitStringLiteral(bit=1, length=n)`` is the all-one n-bit string,
      integer value ``2^n - 1`` when ``n`` is a concrete integer.  When
      ``n`` is symbolic (e.g. ``0^lambda``), the all-one value is also
      symbolic; we encode it as ``"allones:<length_str>"`` to keep the
      namespace disjoint from concrete values.

    Two literals at the same call site have equal keys iff they represent
    the same bitstring (the typechecker has already ensured they live in
    the same type, so distinct keys imply distinct bitstring values).

    Returns ``None`` if *expr* is not a recognized literal form.
    """
    if isinstance(expr, frog_ast.BinaryNum):
        return ("bits", str(expr.length), str(expr.num))
    if isinstance(expr, frog_ast.BitStringLiteral):
        length_str = str(expr.length)
        if expr.bit == 0:
            return ("bits", length_str, "0")
        # All-ones: if length is a concrete Integer literal, compute
        # 2^n - 1; otherwise keep the symbolic marker so it does not
        # collide with any numeric value.
        if isinstance(expr.length, frog_ast.Integer):
            value = (1 << expr.length.num) - 1
            return ("bits", length_str, str(value))
        return ("bits", length_str, f"allones:{length_str}")
    return None


def _collect_rf_call_args(
    block: frog_ast.Block, rf_name: str
) -> list[frog_ast.Expression] | None:
    """Collect every argument expression passed to ``rf_name`` in *block*.

    Returns ``None`` if the RF is referenced in any non-call position (e.g.,
    ``RF.domain``, bare variable reference), which would block the transform.
    """
    args: list[frog_ast.Expression] = []
    call_count, field_access_count = _count_rf_calls(block, rf_name)
    if field_access_count > 0:
        return None

    # Walk the block to collect arguments in order.
    def walk(node: frog_ast.ASTNode) -> bool:
        if (
            isinstance(node, frog_ast.FuncCall)
            and isinstance(node.func, frog_ast.Variable)
            and node.func.name == rf_name
        ):
            if len(node.args) == 1:
                args.append(node.args[0])
            # Return False so SearchVisitor continues searching elsewhere,
            # but the call's own children will also be visited.  We tolerate
            # that because the Variable child just gets ignored here — the
            # conservative bare-reference check is handled separately below.
            return False
        return False

    SearchVisitor(walk).visit(block)
    if len(args) != call_count:
        # Some call had a non-1-argument shape (should not happen for a
        # Function<D, R> type, but guard defensively).
        return None

    # Ensure there are no bare references to the RF outside of FuncCall
    # positions.  Every Variable("RF") inside the block is either the
    # ``func`` field of a FuncCall we just collected (total ``call_count``
    # of these) or a bare reference (which blocks us).
    bare_refs = _count_variable_refs(block, rf_name)
    if bare_refs != call_count:
        return None

    return args


def _count_variable_refs(block: frog_ast.Block, name: str) -> int:
    """Count every ``Variable(name)`` node appearing in *block*."""
    count = [0]

    def visitor(node: frog_ast.ASTNode) -> bool:
        if isinstance(node, frog_ast.Variable) and node.name == name:
            count[0] += 1
        return False

    SearchVisitor(visitor).visit(block)
    return count[0]


class _DistinctConstRFTransformer(BlockTransformer):
    """Replace ``RF(c1), RF(c2), ..., RF(ck)`` with independent uniform
    samples when RF is a locally-sampled random function, the ``ci`` are
    pairwise-distinct literal constants, and RF has no other references.

    Soundness: a freshly sampled ``Function<D, R>`` evaluated on *k*
    pairwise-distinct domain points is distributed identically to *k*
    independent uniform draws from ``R``.  The preconditions ensure this
    equivalence:

    - Local sample (not a field): each method invocation re-samples, so we
      cannot violate consistency across oracle calls.
    - No references other than the *k* call sites: the RF does not escape.
    - No calls inside loop bodies: a single syntactic call inside a loop
      would execute multiple times with the same input, yielding a single
      shared value — independent samples would be unsound.
    - All arguments are literal constants (``BinaryNum`` or
      ``BitStringLiteral``) with pairwise-distinct canonical keys.  Both
      forms carry explicit bit lengths in the AST (``BinaryNum.length`` from
      the parser, ``BitStringLiteral.length`` from the source syntax), so
      pairwise distinctness of keys is decided purely from the AST.  Since
      typechecking has already enforced that every argument at the same
      call site has the same width, distinct keys always represent distinct
      bitstrings.
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _transform_block_wrapper(
        self, block: frog_ast.Block
    ) -> frog_ast.Block:  # pylint: disable=too-many-locals,too-many-branches
        for sample_idx, stmt in enumerate(block.statements):
            if not (
                isinstance(stmt, frog_ast.Sample)
                and isinstance(stmt.sampled_from, frog_ast.FunctionType)
                and isinstance(stmt.var, frog_ast.Variable)
            ):
                continue

            rf_name = stmt.var.name
            rf_type = stmt.sampled_from

            if stmt.the_type is None:
                has_decl = any(
                    isinstance(s, frog_ast.VariableDeclaration)
                    and s.name == rf_name
                    and isinstance(s.type, frog_ast.FunctionType)
                    for s in block.statements[:sample_idx]
                )
                if not has_decl:
                    continue

            remaining = frog_ast.Block(block.statements[sample_idx + 1 :])

            call_args = _collect_rf_call_args(remaining, rf_name)
            if call_args is None:
                continue

            # Need at least 2 calls to be interesting (k=1 is handled by
            # LocalRFToUniform).
            if len(call_args) < 2:
                continue

            if _rf_call_in_loop(remaining, rf_name):
                continue

            # All args must be literal constants with pairwise-distinct keys.
            # Also require that every literal's declared length expression is
            # structurally identical to every other: the typechecker has
            # already accepted the call, so they should unify, but different
            # structural forms could coincidentally represent the same length
            # (e.g. `0^lambda` and `0^(F.in)` with `requires lambda == F.in`).
            # Reject such cases conservatively since the equality check on
            # the _literal_key value assumes a shared length namespace.
            keys: list[tuple[str, ...]] = []
            all_literal = True
            literal_lengths: list[frog_ast.Expression] = []
            for arg in call_args:
                key = _literal_key(arg)
                if key is None:
                    all_literal = False
                    break
                keys.append(key)
                if isinstance(arg, frog_ast.BinaryNum):
                    literal_lengths.append(frog_ast.Integer(arg.length))
                else:
                    assert isinstance(arg, frog_ast.BitStringLiteral)
                    literal_lengths.append(arg.length)
            if all_literal and literal_lengths:
                first_length = literal_lengths[0]
                if not all(length == first_length for length in literal_lengths[1:]):
                    if self.ctx is not None:
                        self.ctx.near_misses.append(
                            NearMiss(
                                transform_name="Distinct Const RF To Uniform",
                                reason=(
                                    f"RF '{rf_name}' called with literal "
                                    "arguments whose declared bit lengths "
                                    "are not structurally identical"
                                ),
                                location=stmt.origin,
                                suggestion=None,
                                variable=rf_name,
                                method=None,
                            )
                        )
                    continue
            if not all_literal:
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Distinct Const RF To Uniform",
                            reason=(
                                f"RF '{rf_name}' called multiple times but at "
                                "least one argument is not a literal constant"
                            ),
                            location=stmt.origin,
                            suggestion=(
                                "Use literal constants (e.g., 0b0, 0b1) as RF "
                                "arguments so distinctness can be decided "
                                "syntactically"
                            ),
                            variable=rf_name,
                            method=None,
                        )
                    )
                continue

            if len(set(keys)) != len(keys):
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Distinct Const RF To Uniform",
                            reason=(
                                f"RF '{rf_name}' called on duplicate literal "
                                "arguments — cannot replace with independent "
                                "samples"
                            ),
                            location=stmt.origin,
                            suggestion=None,
                            variable=rf_name,
                            method=None,
                        )
                    )
                continue

            # No overflow guard is needed here: the typechecker assigns
            # every BinaryNum its concrete source-level width, every
            # BitStringLiteral its declared length, and the well-formedness
            # of the call site guarantees every argument typechecks against
            # the RF's declared domain type.  Two arguments at the same call
            # site therefore always have the same bit width, and pairwise
            # distinct keys always represent pairwise distinct bitstrings.

            # Extract every RF call into a standalone assignment so that
            # _RFCallReplacer can rewrite them uniformly into fresh samples.
            extracted = _RFCallExtractor({rf_name}, {rf_name: rf_type}).transform(
                remaining
            )
            replaced = _RFCallReplacer({rf_name: rf_type}).transform(extracted)

            if replaced == remaining:
                continue

            # Drop the original RF sample (now dead) and splice in replaced.
            new_stmts = list(block.statements[:sample_idx]) + list(replaced.statements)
            return self.transform_block(frog_ast.Block(new_stmts))

        return block


class DistinctConstRFToUniform(TransformPass):
    """Replace locally-sampled RFs called on distinct literal constants with
    independent uniform samples.

    Generalizes :class:`LocalRFToUniform` from k=1 to arbitrary k when the
    arguments are syntactically-distinct literal constants (currently
    ``BinaryNum`` only).
    """

    name = "Distinct Const RF To Uniform"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _DistinctConstRFTransformer(ctx).transform(game)


# ---------------------------------------------------------------------------
# RF on fresh random local input -> uniform sample
# ---------------------------------------------------------------------------


def _count_var_uses(block: frog_ast.Block, var_name: str) -> int:
    """Count all references to a variable name in a block."""
    count: list[int] = [0]

    def counter(node: frog_ast.ASTNode) -> bool:
        if isinstance(node, frog_ast.Variable) and node.name == var_name:
            count[0] += 1
        return False

    SearchVisitor(counter).visit(block)
    return count[0]


def _find_rf_call_of_var(
    block: frog_ast.Block,
    var_name: str,
    rf_names: set[str],
) -> frog_ast.FuncCall | None:
    """Find ``RF(v)``, ``RF([..., v, ...])``, or ``RF(... || v || ...)``
    where *v* is the given variable and RF is a known RF."""

    def _arg_contains_var(arg: frog_ast.Expression) -> bool:
        """Check if the RF argument contains the target variable."""
        if isinstance(arg, frog_ast.Variable):
            return arg.name == var_name
        if isinstance(arg, frog_ast.Tuple):
            return any(
                isinstance(elem, frog_ast.Variable) and elem.name == var_name
                for elem in arg.values
            )
        if (
            isinstance(arg, frog_ast.BinaryOperation)
            and arg.operator == frog_ast.BinaryOperators.OR
        ):
            return any(
                isinstance(leaf, frog_ast.Variable) and leaf.name == var_name
                for leaf in _flatten_concat(arg)
            )
        return False

    def matcher(node: frog_ast.ASTNode) -> bool:
        return (
            isinstance(node, frog_ast.FuncCall)
            and isinstance(node.func, frog_ast.Variable)
            and node.func.name in rf_names
            and len(node.args) == 1
            and _arg_contains_var(node.args[0])
        )

    result = SearchVisitor(matcher).visit(block)
    if result is not None:
        assert isinstance(result, frog_ast.FuncCall)
    return result  # type: ignore[return-value]


class _FreshInputRFTransformer(BlockTransformer):
    """Replace ``RF(v)`` (or ``RF([..., v, ...])`` / ``RF(... || v || ...)``)
    with ``z <- RangeType`` when *v* is a ``<-uniq[S]`` sampled variable used
    only in that one RF call.

    The exclusion set ``S`` guarantees that *v* differs from all inputs on
    which the RF has been queried elsewhere (e.g., via an adversary oracle).
    When *v* appears inside a tuple or concatenation, varying *v* produces a
    distinct composite argument, so the RF output is still an independent
    uniform draw.
    """

    def __init__(
        self,
        rf_types: dict[str, frog_ast.FunctionType],
        ctx: PipelineContext | None = None,
    ) -> None:
        self.rf_types = rf_types
        self.ctx = ctx
        self._loop_depth = 0

    def transform_numeric_for(  # type: ignore[override]
        self, node: frog_ast.NumericFor
    ) -> frog_ast.NumericFor:
        """Track loop depth so _transform_block_wrapper skips loop bodies."""
        self._loop_depth += 1
        new_block = self.transform_block(node.block)
        self._loop_depth -= 1
        if new_block is node.block:
            return node
        new_node = copy.copy(node)
        new_node.block = new_block
        return new_node

    def transform_generic_for(  # type: ignore[override]
        self, node: frog_ast.GenericFor
    ) -> frog_ast.GenericFor:
        """Track loop depth so _transform_block_wrapper skips loop bodies."""
        self._loop_depth += 1
        new_block = self.transform_block(node.block)
        self._loop_depth -= 1
        if new_block is node.block:
            return node
        new_node = copy.copy(node)
        new_node.block = new_block
        return new_node

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        # Don't transform inside loop bodies — the same <-uniq sample
        # would be evaluated multiple times per game execution.
        if self._loop_depth > 0:
            return block
        for sample_idx, stmt in enumerate(block.statements):
            # Look for unique samples: T v <-uniq[S] T;
            # Only <-uniq inputs are eligible — the exclusion set guarantees
            # the input hasn't been queried on the RF elsewhere, making the
            # replacement exactly sound.  Plain uniform samples (T v <- T)
            # would introduce a security loss that must be accounted for
            # explicitly via a UniqueSampling assumption hop.
            if not isinstance(stmt, frog_ast.UniqueSample):
                continue
            if not isinstance(stmt.var, frog_ast.Variable):
                continue

            var_name = stmt.var.name
            remaining = frog_ast.Block(block.statements[sample_idx + 1 :])

            # Variable must be used exactly once in the remaining block
            if _count_var_uses(remaining, var_name) != 1:
                continue

            # That single use must be as the sole argument to an RF call
            rf_call = _find_rf_call_of_var(
                remaining, var_name, set(self.rf_types.keys())
            )
            if rf_call is None:
                continue

            assert isinstance(rf_call.func, frog_ast.Variable)
            rf_name = rf_call.func.name

            # Don't simplify if the RF call is inside a loop
            if _rf_call_in_loop(remaining, rf_name):
                continue

            range_type = copy.deepcopy(self.rf_types[rf_name].range_type)

            # Replace the RF call node with a fresh variable, and add a
            # Sample statement for it — effectively RF(v) -> z <- Range.
            result_var_name = f"__fresh_rf_{var_name}__"
            result_var = frog_ast.Variable(result_var_name)
            new_remaining = ReplaceTransformer(rf_call, result_var).transform(remaining)

            sample_stmt = frog_ast.Sample(
                range_type,  # type: ignore[arg-type]
                frog_ast.Variable(result_var_name),
                copy.deepcopy(range_type),  # type: ignore[arg-type]
            )

            # Drop the original v sample (now dead) and prepend the
            # fresh-result sample.
            new_stmts = (
                list(block.statements[:sample_idx])
                + [sample_stmt]
                + list(new_remaining.statements)
            )
            return self.transform_block(frog_ast.Block(new_stmts))

        return block


class FreshInputRFToUniform(TransformPass):
    """Replace RF(v) with uniform when v is a ``<-uniq`` single-use local.

    Handles bare variables, tuples containing the variable, and
    concatenations containing the variable.

    When the input is sampled via ``<-uniq[S]``, the exclusion set
    guarantees it differs from all other RF inputs.  This makes the
    replacement exactly sound — no guessing loss.
    """

    name = "Fresh Input RF To Uniform"

    @staticmethod
    def _sampled_function_fields(game: frog_ast.Game) -> set[str]:
        """Return names of Function fields that are sampled in Initialize."""
        sampled: set[str] = set()
        for method in game.methods:
            if method.signature.name != "Initialize":
                continue
            for stmt in method.block.statements:
                if (
                    isinstance(stmt, frog_ast.Sample)
                    and isinstance(stmt.var, frog_ast.Variable)
                    and isinstance(stmt.sampled_from, frog_ast.FunctionType)
                ):
                    sampled.add(stmt.var.name)
        return sampled

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        # Collect RF types from sampled game fields and sampled proof-level
        # Functions.  Only Functions that are explicitly sampled (via <-)
        # are random functions; unsampled ones are known deterministic.
        rf_types: dict[str, frog_ast.FunctionType] = {}
        sampled_fields = self._sampled_function_fields(game)
        for rf_field in game.fields:
            if (
                isinstance(rf_field.type, frog_ast.FunctionType)
                and rf_field.name in sampled_fields
            ):
                rf_types[rf_field.name] = rf_field.type
        for entry in ctx.proof_let_types.type_map:
            if (
                isinstance(entry.type, frog_ast.FunctionType)
                and entry.name in ctx.sampled_let_names
            ):
                rf_types[entry.name] = entry.type

        if not rf_types:
            return game

        return _FreshInputRFTransformer(rf_types, ctx).transform(game)


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


@dataclass
class _GuardInfo:
    """Result of finding a challenge exclusion guard in an oracle method."""

    challenge_fields: set[str]
    guard_lhs_vars: set[str]
    guard_idx: int
    # For slice guards: param[start:end] == field
    slice_param: str | None = None
    slice_start: frog_ast.Expression | None = None
    slice_end: frog_ast.Expression | None = None

    @property
    def is_slice_guard(self) -> bool:
        """True if this guard uses a slice comparison."""
        return self.slice_param is not None


def _find_challenge_guard(
    method: frog_ast.Method,
    field_names: list[str],
) -> _GuardInfo | None:
    """Find a challenge exclusion guard at the top of an oracle method.

    Looks for the pattern:
        if (param_expr == [field_a, field_b, ...]) { return None/value; }
    or:
        if (param_expr == field_a) { return None/value; }
    or (slice guard):
        if (param[start:end] == field_a) { return None/value; }

    at the start of the method body (possibly after local assignments).

    Returns a ``_GuardInfo`` describing the guard, or ``None``.
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

        lhs = cond.left_expression

        # Check for slice guard: param[start:end] == field
        if challenge_fields and isinstance(lhs, frog_ast.Slice):
            if isinstance(lhs.the_array, frog_ast.Variable):
                return _GuardInfo(
                    challenge_fields=challenge_fields,
                    guard_lhs_vars={lhs.the_array.name},
                    guard_idx=idx,
                    slice_param=lhs.the_array.name,
                    slice_start=lhs.start,
                    slice_end=lhs.end,
                )

        # Extract LHS variable names (non-field variables constrained by guard)
        guard_lhs_vars = _extract_non_field_vars(lhs, field_names)

        if challenge_fields:
            return _GuardInfo(
                challenge_fields=challenge_fields,
                guard_lhs_vars=guard_lhs_vars,
                guard_idx=idx,
            )

    return None


def _build_local_assignments(
    block: frog_ast.Block,
) -> dict[str, frog_ast.Expression]:
    """Build a map of ``{var_name: rhs}`` for simple local assignments."""
    result: dict[str, frog_ast.Expression] = {}
    for stmt in block.statements:
        if isinstance(stmt, frog_ast.Assignment) and isinstance(
            stmt.var, frog_ast.Variable
        ):
            result[stmt.var.name] = stmt.value
    return result


def _resolve_var_aliases(
    expr: frog_ast.Expression,
    aliases: dict[str, frog_ast.Expression],
    stop_names: set[str],
    _depth: int = 0,
) -> frog_ast.Expression:
    """Resolve variable references through local assignments.

    Replaces Variable references with their assigned RHS, recursively
    (up to a depth limit).  Variables whose names are in *stop_names*
    and variables without an assignment are left as-is.
    """
    if _depth > 10:
        return expr
    if isinstance(expr, frog_ast.Variable):
        if expr.name not in stop_names and expr.name in aliases:
            return _resolve_var_aliases(
                aliases[expr.name], aliases, stop_names, _depth + 1
            )
        return expr
    if isinstance(expr, frog_ast.BinaryOperation):
        new_left = _resolve_var_aliases(
            expr.left_expression, aliases, stop_names, _depth + 1
        )
        new_right = _resolve_var_aliases(
            expr.right_expression, aliases, stop_names, _depth + 1
        )
        if new_left is expr.left_expression and new_right is expr.right_expression:
            return expr
        return frog_ast.BinaryOperation(expr.operator, new_left, new_right)
    if isinstance(expr, frog_ast.ArrayAccess):
        new_arr = _resolve_var_aliases(expr.the_array, aliases, stop_names, _depth + 1)
        if new_arr is expr.the_array:
            return expr
        return frog_ast.ArrayAccess(new_arr, expr.index)
    return expr


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


def _flatten_concat(expr: frog_ast.Expression) -> list[frog_ast.Expression]:
    """Flatten nested concatenation (OR) expressions into leaves."""
    if (
        isinstance(expr, frog_ast.BinaryOperation)
        and expr.operator == frog_ast.BinaryOperators.OR
    ):
        return _flatten_concat(expr.left_expression) + _flatten_concat(
            expr.right_expression
        )
    return [expr]


def _ast_to_sympy(  # pylint: disable=too-many-return-statements
    node: frog_ast.ASTNode,
) -> Symbol | int | None:
    """Convert an AST numeric expression to a SymPy expression."""
    if isinstance(node, frog_ast.Integer):
        return node.num
    if isinstance(node, frog_ast.Variable):
        return Symbol(node.name)
    if isinstance(node, frog_ast.FieldAccess):
        if isinstance(node.the_object, frog_ast.Variable):
            return Symbol(f"{node.the_object.name}.{node.name}")
        return None
    if isinstance(node, frog_ast.BinaryOperation):
        left = _ast_to_sympy(node.left_expression)
        right = _ast_to_sympy(node.right_expression)
        if left is None or right is None:
            return None
        if node.operator == frog_ast.BinaryOperators.ADD:
            return left + right
        if node.operator == frog_ast.BinaryOperators.SUBTRACT:
            return left - right
        if node.operator == frog_ast.BinaryOperators.MULTIPLY:
            return left * right
        if node.operator == frog_ast.BinaryOperators.DIVIDE:
            return Rational(left, right)
        return None
    if isinstance(node, frog_ast.UnaryOperation):
        if node.operator == frog_ast.UnaryOperators.MINUS:
            val = _ast_to_sympy(node.expression)
            if val is not None:
                return -val
        return None
    return None


def _leaf_bitstring_width(
    leaf: frog_ast.Expression,
    field_types: dict[str, frog_ast.Type],
    proof_namespace: frog_ast.Namespace,
) -> Symbol | int | None:
    """Return the SymPy bit-width of a concatenation leaf, or None."""
    # Variable: look up in game fields
    if isinstance(leaf, frog_ast.Variable) and leaf.name in field_types:
        ft = field_types[leaf.name]
        if isinstance(ft, frog_ast.BitStringType) and ft.parameterization:
            return _ast_to_sympy(ft.parameterization)
    # FuncCall to a primitive method: use return type
    if isinstance(leaf, frog_ast.FuncCall):
        sig = _lookup_primitive_method(leaf.func, proof_namespace)
        if sig is not None and isinstance(sig.return_type, frog_ast.BitStringType):
            if sig.return_type.parameterization:
                return _ast_to_sympy(sig.return_type.parameterization)
    return None


# pylint: disable=too-many-arguments,too-many-positional-arguments
def _slice_guard_excludes(
    init_arg: frog_ast.Expression,
    oracle_arg: frog_ast.Expression,
    guard: _GuardInfo,
    field_names: list[str],
    field_types: dict[str, frog_ast.Type] | None = None,
    proof_namespace: frog_ast.Namespace | None = None,
) -> bool:
    """Check if a slice guard ensures the oracle RF arg differs from init.

    This handles the case where the oracle RF argument IS the guarded
    parameter (e.g., ``RF(m)`` with guard ``m[start:end] == challengeField``).
    The guard guarantees that the sub-range of ``m`` covering the challenge
    leaf does NOT match the challenge field, so the full RF inputs differ.

    Returns True if the slice guard proves the arguments differ.
    """
    if not guard.is_slice_guard:
        return False

    # Oracle RF arg must be the guarded parameter itself
    if not isinstance(oracle_arg, frog_ast.Variable):
        return False
    if oracle_arg.name != guard.slice_param:
        return False

    # Flatten Init arg into concatenation leaves
    init_leaves = _flatten_concat(init_arg)
    if len(init_leaves) <= 1:
        return False

    # Need type info to compute leaf widths
    if field_types is None or proof_namespace is None:
        return False

    # Convert slice bounds to SymPy
    assert guard.slice_start is not None and guard.slice_end is not None
    slice_start_sym = _ast_to_sympy(guard.slice_start)
    slice_end_sym = _ast_to_sympy(guard.slice_end)
    if slice_start_sym is None or slice_end_sym is None:
        return False

    # Compute cumulative leaf positions and find which leaf the slice covers
    cum_start: Symbol | int = 0
    for leaf in init_leaves:
        width = _leaf_bitstring_width(leaf, field_types, proof_namespace)
        if width is None:
            return False
        cum_end = cum_start + width

        # Check if the slice exactly covers this leaf
        if (
            sympy_simplify(cum_start - slice_start_sym) == 0
            and sympy_simplify(cum_end - slice_end_sym) == 0
        ):
            # This leaf is at the guarded position — check if it's a
            # challenge field variable
            if isinstance(leaf, frog_ast.Variable) and leaf.name in field_names:
                if leaf.name in guard.challenge_fields:
                    return True
            return False

        cum_start = cum_end

    return False


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
        ctx: PipelineContext | None = None,
    ) -> frog_ast.Game:
        """Transform a game, replacing qualifying RF calls with uniform samples."""
        if proof_namespace is None:
            proof_namespace = {}
        field_names = [f.name for f in game.fields]
        field_types: dict[str, frog_ast.Type] = {f.name: f.type for f in game.fields}
        rf_fields: dict[str, frog_ast.FunctionType] = {}
        for f in game.fields:
            if isinstance(f.type, frog_ast.FunctionType):
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

            # Resolve local variable aliases in the Init RF arg so that
            # intermediate cast variables (e.g. bct2 = ct2Star) are traced
            # back to their field references.
            init_aliases = _build_local_assignments(init_method.block)
            field_name_set = set(field_names)
            resolved_init_arg = _resolve_var_aliases(
                init_arg, init_aliases, field_name_set
            )

            # Check that Init arg references at least one challenge field
            init_field_refs = _collect_field_vars(resolved_init_arg, field_names)

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

                guard = guard_result
                challenge_fields = guard.challenge_fields
                guard_lhs_vars = guard.guard_lhs_vars
                guard_idx = guard.guard_idx

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

                # Resolve oracle local aliases once for structural comparison.
                # Stop at field names AND guard variables so that guard-
                # constrained variables (like ct2) are preserved as leaves
                # for _check_leaf_pair to recognize.
                oracle_aliases = _build_local_assignments(oracle_method.block)
                oracle_stop = field_name_set | guard_lhs_vars

                for call in all_post_calls:
                    if len(call.args) != 1:
                        all_oracle_ok = False
                        break

                    resolved_oracle_arg = _resolve_var_aliases(
                        call.args[0], oracle_aliases, oracle_stop
                    )

                    # For slice guards where the oracle RF arg IS the
                    # guarded parameter (e.g., RF(m) with guard on
                    # m[start:end]), use slice-based exclusion check
                    if guard.is_slice_guard and _slice_guard_excludes(
                        resolved_init_arg,
                        resolved_oracle_arg,
                        guard,
                        field_names,
                        field_types,
                        proof_namespace,
                    ):
                        continue

                    differs = _rf_args_structurally_differ(
                        resolved_init_arg,
                        resolved_oracle_arg,
                        challenge_fields,
                        field_names,
                        guard_lhs_vars,
                        proof_namespace,
                    )
                    if not differs:
                        if ctx is not None and guard.is_slice_guard:
                            ctx.near_misses.append(
                                NearMiss(
                                    transform_name=(
                                        "Challenge Exclusion RF To Uniform"
                                    ),
                                    reason=(
                                        f"Slice guard on '{guard.slice_param}' "
                                        f"detected but RF arg structural "
                                        f"difference could not be verified in "
                                        f"'{oracle_method.signature.name}'"
                                    ),
                                    location=call.origin,
                                    suggestion=(
                                        "Check that the oracle RF input is the "
                                        "guarded parameter and the slice aligns "
                                        "with a single concatenation leaf"
                                    ),
                                    variable=rf_name,
                                    method=oracle_method.signature.name,
                                )
                            )
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
            game, proof_namespace=ctx.proof_namespace, ctx=ctx
        )


# ---------------------------------------------------------------------------
# Lazy map -> sampled Function canonicalization (design spec §5.3)
# ---------------------------------------------------------------------------


_LAZY_MAP_NAME = "Lazy Map To Sampled Function"


def _is_idiom_if_expr(
    stmt: frog_ast.ASTNode,
    map_name: str,
    key_expr: frog_ast.Expression,
) -> bool:
    """Return True if *stmt* is ``if (key_expr in map) return map[key_expr];``
    with no else and a single-statement body.  Structural equality is used
    between the ``in``-check's left operand and the embedded ``M[.]``'s
    index, and both must equal *key_expr*."""
    if not isinstance(stmt, frog_ast.IfStatement):
        return False
    if len(stmt.conditions) != 1 or len(stmt.blocks) != 1:
        return False
    cond = stmt.conditions[0]
    if not (
        isinstance(cond, frog_ast.BinaryOperation)
        and cond.operator == frog_ast.BinaryOperators.IN
        and cond.left_expression == key_expr
        and isinstance(cond.right_expression, frog_ast.Variable)
        and cond.right_expression.name == map_name
    ):
        return False
    body = list(stmt.blocks[0].statements)
    if len(body) != 1 or not isinstance(body[0], frog_ast.ReturnStatement):
        return False
    ret = body[0].expression
    return (
        isinstance(ret, frog_ast.ArrayAccess)
        and isinstance(ret.the_array, frog_ast.Variable)
        and ret.the_array.name == map_name
        and ret.index == key_expr
    )


def _expr_references_any(expr: frog_ast.Expression, names: set[str]) -> bool:
    """Return True if *expr* syntactically references any ``Variable`` whose
    name is in *names*."""

    def matcher(n: frog_ast.ASTNode) -> bool:
        return isinstance(n, frog_ast.Variable) and n.name in names

    return SearchVisitor(matcher).visit(expr) is not None


def _match_idiom_suffix(
    method: frog_ast.Method,
    map_name: str,
    value_type: frog_ast.Type,
    ctx: PipelineContext | None = None,
) -> tuple[int, frog_ast.Expression, str] | None:
    """Match the 4-statement lazy-lookup idiom suffix of *method*'s body.

    The *key* is any expression ``e`` appearing identically (by structural
    equality) at all three sites:

    - the ``in`` check's left operand,
    - the ``M[.]`` index inside the check's embedded return, and
    - the ``M[.]`` index of the assign statement.

    The key expression must (a) reference at least one parameter of
    *method*, and (b) contain no non-deterministic calls (checked when
    *ctx* is supplied).
    """
    stmts = list(method.block.statements)
    if len(stmts) < 4:
        return None
    if_idx = len(stmts) - 4
    if_stmt, sample_stmt, assign_stmt, ret_stmt = stmts[if_idx:]

    if not (
        isinstance(sample_stmt, frog_ast.Sample)
        and isinstance(sample_stmt.var, frog_ast.Variable)
        and sample_stmt.the_type is not None
        and sample_stmt.the_type == value_type
        and sample_stmt.sampled_from == value_type
    ):
        return None
    sample_var = sample_stmt.var.name

    if not (
        isinstance(assign_stmt, frog_ast.Assignment)
        and isinstance(assign_stmt.var, frog_ast.ArrayAccess)
        and isinstance(assign_stmt.var.the_array, frog_ast.Variable)
        and assign_stmt.var.the_array.name == map_name
        and isinstance(assign_stmt.value, frog_ast.Variable)
        and assign_stmt.value.name == sample_var
    ):
        return None
    key_expr = assign_stmt.var.index

    if not (
        isinstance(ret_stmt, frog_ast.ReturnStatement)
        and isinstance(ret_stmt.expression, frog_ast.Variable)
        and ret_stmt.expression.name == sample_var
    ):
        return None

    if not _is_idiom_if_expr(if_stmt, map_name, key_expr):
        return None

    # The key expression must reference at least one method parameter: a
    # constant (field-only) key would mean the idiom samples once per game
    # rather than once per caller input, which is a different semantics.
    param_names = {p.name for p in method.signature.parameters}
    if not _expr_references_any(key_expr, param_names):
        return None

    # Purity: if any embedded FuncCall is non-deterministic, rewriting the
    # three occurrences of the key into one is unsound.
    if ctx is not None and has_nondeterministic_call(
        key_expr, ctx.proof_namespace, ctx.proof_let_types
    ):
        return None

    # Defensive: if `sample_var` appeared syntactically in `key_expr`, the
    # three structural occurrences of `key_expr` would straddle the sample
    # statement (if-condition pre-sample, assign-index post-sample), and the
    # Variable(sample_var) occurrences would refer to different bindings —
    # collapsing them to one evaluation would be unsound.  Not reachable from
    # well-typed FrogLang (the sample is a declaration; no block shadowing),
    # but guarded at the AST level.
    if _expr_references_any(key_expr, {sample_var}):
        return None

    return if_idx, key_expr, sample_var


def _references_map(node: frog_ast.ASTNode, map_name: str) -> bool:
    """Return True if *node* syntactically references ``Variable(map_name)``."""

    def matcher(n: frog_ast.ASTNode) -> bool:
        return isinstance(n, frog_ast.Variable) and n.name == map_name

    return SearchVisitor(matcher).visit(node) is not None


class LazyMapToSampledFunction(TransformPass):
    """Rewrite a ``Map<K, V>`` field used exclusively as a lazy lookup
    table into a sampled ``Function<K, V>`` field.

    Preconditions (design spec §S3):

    - (a) Every reference to the map field lies inside the idiom suffix of
      some method.
    - (b) The map field is not explicitly initialized in ``Initialize``
      (maps default to empty per SEMANTICS.md §6.7).
    - (c) No method uses ``|M|``, ``M.keys``, ``M.values``, or ``M.entries``
      (follows from (a)).

    On success:

    1. Change the field type from ``Map<K, V>`` to ``Function<K, V>``.
    2. Prepend ``M <- Function<K, V>;`` to ``Initialize`` (creating the
       method if absent).
    3. Replace each idiom suffix with ``return M(key);``.
    """

    name = _LAZY_MAP_NAME

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        for fld in game.fields:
            if not isinstance(fld.type, frog_ast.MapType):
                continue
            rewritten = self._try_rewrite(game, fld, ctx)
            if rewritten is not None:
                return rewritten
        return game

    def _try_rewrite(
        self,
        game: frog_ast.Game,
        fld: frog_ast.Field,
        ctx: PipelineContext,
    ) -> frog_ast.Game | None:
        map_name = fld.name
        assert isinstance(fld.type, frog_ast.MapType)
        key_type = fld.type.key_type
        value_type = fld.type.value_type

        any_idiom = any(
            _match_idiom_suffix(m, map_name, value_type, ctx) is not None
            for m in game.methods
        )

        if self._initialize_touches_map(game, map_name, value_type, ctx):
            return None

        rewrites = self._collect_method_rewrites(
            game, map_name, value_type, any_idiom, ctx
        )
        if rewrites is None:
            return None

        return self._build_rewritten_game(
            game, map_name, key_type, value_type, rewrites
        )

    def _emit_near_miss(
        self,
        ctx: PipelineContext,
        reason: str,
        location: frog_ast.SourceOrigin | None,
        variable: str,
        method_name: str | None,
        suggestion: str | None = None,
    ) -> None:
        ctx.near_misses.append(
            NearMiss(
                transform_name=_LAZY_MAP_NAME,
                reason=reason,
                location=location,
                suggestion=suggestion,
                variable=variable,
                method=method_name,
            )
        )

    def _initialize_touches_map(
        self,
        game: frog_ast.Game,
        map_name: str,
        value_type: frog_ast.Type,
        ctx: PipelineContext,
    ) -> bool:
        """Return True (and optionally emit a near-miss) if Initialize
        explicitly touches the map field."""
        for method in game.methods:
            if method.signature.name != "Initialize":
                continue
            for stmt in method.block.statements:
                if not isinstance(stmt, (frog_ast.Assignment, frog_ast.Sample)):
                    continue
                v = stmt.var
                target_var: frog_ast.Variable | None = None
                if isinstance(v, frog_ast.Variable):
                    target_var = v
                elif isinstance(v, frog_ast.ArrayAccess) and isinstance(
                    v.the_array, frog_ast.Variable
                ):
                    target_var = v.the_array
                if target_var is None or target_var.name != map_name:
                    continue
                if any(
                    _match_idiom_suffix(m, map_name, value_type, ctx) is not None
                    for m in game.methods
                ):
                    self._emit_near_miss(
                        ctx,
                        (
                            f"Map '{map_name}' is explicitly initialized in "
                            "Initialize; lazy-map canonicalization requires "
                            "an empty initial map"
                        ),
                        stmt.origin,
                        map_name,
                        "Initialize",
                    )
                return True
        return False

    def _collect_method_rewrites(
        self,
        game: frog_ast.Game,
        map_name: str,
        value_type: frog_ast.Type,
        any_idiom: bool,
        ctx: PipelineContext,
    ) -> list[tuple[int, int, frog_ast.Expression]] | None:
        """For each non-Initialize method, classify as idiom / disqualifying /
        unrelated, and return the list of ``(method_idx, if_idx, key_name)``
        rewrite sites.  Returns None if a disqualifying use is found."""
        rewrites: list[tuple[int, int, frog_ast.Expression]] = []
        found_any = False
        for m_idx, method in enumerate(game.methods):
            method_name = method.signature.name
            if method_name == "Initialize":
                for stmt in method.block.statements:
                    if _references_map(stmt, map_name):
                        if any_idiom:
                            self._emit_near_miss(
                                ctx,
                                (
                                    f"Map '{map_name}' is referenced in "
                                    "Initialize outside the lazy-lookup idiom"
                                ),
                                stmt.origin,
                                map_name,
                                "Initialize",
                            )
                        return None
                continue
            match = _match_idiom_suffix(method, map_name, value_type, ctx)
            if match is None:
                for stmt in method.block.statements:
                    if _references_map(stmt, map_name):
                        if any_idiom:
                            self._emit_near_miss(
                                ctx,
                                (
                                    f"Map '{map_name}' is referenced in "
                                    f"method '{method_name}' outside the "
                                    "lazy-lookup idiom"
                                ),
                                stmt.origin,
                                map_name,
                                method_name,
                            )
                        return None
                continue
            if_idx, key_expr, _sv = match
            for stmt in method.block.statements[:if_idx]:
                if _references_map(stmt, map_name):
                    if any_idiom:
                        self._emit_near_miss(
                            ctx,
                            (
                                f"Map '{map_name}' is referenced in method "
                                f"'{method_name}' outside the lazy-lookup "
                                "idiom"
                            ),
                            stmt.origin,
                            map_name,
                            method_name,
                        )
                    return None
            rewrites.append((m_idx, if_idx, key_expr))
            found_any = True
        if not found_any:
            return None
        return rewrites

    def _build_rewritten_game(
        self,
        game: frog_ast.Game,
        map_name: str,
        key_type: frog_ast.Type,
        value_type: frog_ast.Type,
        rewrites: list[tuple[int, int, frog_ast.Expression]],
    ) -> frog_ast.Game:
        new_game = copy.deepcopy(game)

        for f in new_game.fields:
            if f.name == map_name:
                f.type = frog_ast.FunctionType(
                    copy.deepcopy(key_type), copy.deepcopy(value_type)
                )
                break

        sample_stmt = frog_ast.Sample(
            None,
            frog_ast.Variable(map_name),
            frog_ast.FunctionType(
                copy.deepcopy(key_type), copy.deepcopy(value_type)
            ),  # type: ignore[arg-type]
        )
        init_method: frog_ast.Method | None = None
        for m in new_game.methods:
            if m.signature.name == "Initialize":
                init_method = m
                break
        if init_method is None:
            init_sig = frog_ast.MethodSignature("Initialize", frog_ast.Void(), [])
            init_method = frog_ast.Method(init_sig, frog_ast.Block([sample_stmt]))
            new_game.methods = [init_method] + list(new_game.methods)
        else:
            init_method.block = frog_ast.Block(
                [sample_stmt] + list(init_method.block.statements)
            )

        for m_idx, if_idx, key_expr in rewrites:
            target_name = game.methods[m_idx].signature.name
            target = next(
                m for m in new_game.methods if m.signature.name == target_name
            )
            new_return = frog_ast.ReturnStatement(
                frog_ast.FuncCall(
                    frog_ast.Variable(map_name),
                    [copy.deepcopy(key_expr)],
                )
            )
            target.block = frog_ast.Block(
                list(target.block.statements[:if_idx]) + [new_return]
            )
        return new_game


_LAZY_MAP_PAIR_NAME = "Lazy Map Pair to Sampled Function"


@dataclass(frozen=True)
class _PairIdiomMatch:
    if_idx: int  # index of the if-statement in method.block.statements
    key_name: str  # parameter name k
    writes_to: str  # "M1" or "M2"


def _match_pair_idiom_suffix(
    method: frog_ast.Method,
    map1: str,
    map2: str,
    value_type: frog_ast.Type,
) -> _PairIdiomMatch | None:
    """Recognize the 4-statement guarded-pair lazy-lookup idiom suffix.

    Matches a suffix of the method block starting at some index ``j``:

    1. ``if (k in M1) { return M1[k]; } else if (k in M2) { return M2[k]; }``
       (no else-block)
    2. ``V s <- V;``
    3. ``Mi[k] = s;`` for ``i in {1, 2}``
    4. ``return s;``
    """
    stmts = list(method.block.statements)
    if len(stmts) < 4:
        return None
    if_idx = len(stmts) - 4
    if_stmt = stmts[if_idx]
    if not isinstance(if_stmt, frog_ast.IfStatement):
        return None
    if len(if_stmt.conditions) != 2 or len(if_stmt.blocks) != 2:
        return None
    if if_stmt.has_else_block():
        return None

    def _extract_in(cond: frog_ast.Expression, map_name: str) -> str | None:
        if not (
            isinstance(cond, frog_ast.BinaryOperation)
            and cond.operator == frog_ast.BinaryOperators.IN
            and isinstance(cond.right_expression, frog_ast.Variable)
            and cond.right_expression.name == map_name
            and isinstance(cond.left_expression, frog_ast.Variable)
        ):
            return None
        return cond.left_expression.name

    k1 = _extract_in(if_stmt.conditions[0], map1)
    k2 = _extract_in(if_stmt.conditions[1], map2)
    if k1 is None or k2 is None or k1 != k2:
        return None
    k = k1

    def _is_return_map_k(block: frog_ast.Block, map_name: str) -> bool:
        if len(block.statements) != 1:
            return False
        s = block.statements[0]
        if not isinstance(s, frog_ast.ReturnStatement) or s.expression is None:
            return False
        e = s.expression
        return (
            isinstance(e, frog_ast.ArrayAccess)
            and isinstance(e.the_array, frog_ast.Variable)
            and e.the_array.name == map_name
            and isinstance(e.index, frog_ast.Variable)
            and e.index.name == k
        )

    if not _is_return_map_k(if_stmt.blocks[0], map1):
        return None
    if not _is_return_map_k(if_stmt.blocks[1], map2):
        return None

    sample = stmts[if_idx + 1]
    if not isinstance(sample, frog_ast.Sample):
        return None
    if not isinstance(sample.var, frog_ast.Variable):
        return None
    s_name = sample.var.name
    if sample.the_type != value_type:
        return None
    if sample.sampled_from != value_type:
        return None

    asgn = stmts[if_idx + 2]
    if not isinstance(asgn, frog_ast.Assignment):
        return None
    target = asgn.var
    if not (
        isinstance(target, frog_ast.ArrayAccess)
        and isinstance(target.the_array, frog_ast.Variable)
        and target.the_array.name in (map1, map2)
        and isinstance(target.index, frog_ast.Variable)
        and target.index.name == k
    ):
        return None
    writes_to = target.the_array.name
    if not (isinstance(asgn.value, frog_ast.Variable) and asgn.value.name == s_name):
        return None

    ret = stmts[if_idx + 3]
    if not (
        isinstance(ret, frog_ast.ReturnStatement)
        and isinstance(ret.expression, frog_ast.Variable)
        and ret.expression.name == s_name
    ):
        return None

    param_names = {p.name for p in method.signature.parameters}
    if k not in param_names:
        return None

    return _PairIdiomMatch(if_idx=if_idx, key_name=k, writes_to=writes_to)


def _method_references_maps(method: frog_ast.Method, m1: str, m2: str) -> bool:
    """Return True if any statement in *method* references either map name."""
    return any(
        _references_map(stmt, m1) or _references_map(stmt, m2)
        for stmt in method.block.statements
    )


def _stmt_references_maps(stmt: frog_ast.ASTNode, m1: str, m2: str) -> bool:
    """Return True if *stmt* references either map name."""
    return _references_map(stmt, m1) or _references_map(stmt, m2)


def _fresh_field_name(game: frog_ast.Game, base: str) -> str:
    existing = {f.name for f in game.fields}
    if base not in existing:
        return base
    i = 1
    while f"{base}{i}" in existing:
        i += 1
    return f"{base}{i}"


class LazyMapPairToSampledFunction(TransformPass):
    """Generalize LazyMapToSampledFunction to a pair of maps with
    mutually-disjoint lazy-lookup guards (design §4).

    Preconditions (P2-1 .. P2-5 from design §4.2): see docstring of
    ``_try_rewrite_pair``.
    """

    name = _LAZY_MAP_PAIR_NAME

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        # Find all Map<K, V> fields; try every unordered pair with matching
        # key/value types.
        map_fields = [f for f in game.fields if isinstance(f.type, frog_ast.MapType)]
        for i, m1 in enumerate(map_fields):
            for m2 in map_fields[i + 1 :]:
                if m1.type != m2.type:
                    # (P2-3) Key/value type mismatch. Emit a near-miss only
                    # if both maps individually look like lazy-lookup
                    # candidates (single-map idiom) -- otherwise the pair is
                    # unrelated to this pass.
                    if self._both_have_single_map_idiom(game, m1, m2, ctx):
                        self._emit_near_miss(
                            ctx,
                            (
                                f"Maps '{m1.name}' and '{m2.name}' have "
                                "mismatched key/value types; lazy-map-pair "
                                "canonicalization requires the same type"
                            ),
                            m1.origin,
                            m1.name,
                            None,
                        )
                    continue
                rewritten = self._try_rewrite_pair(game, m1, m2, ctx)
                if rewritten is not None:
                    return rewritten
                # If no pair-idiom match but both maps individually look
                # like single-map idioms, that's the "missing disjointness
                # guard" shape -- emit a near-miss.
                self._maybe_emit_missing_guard(game, m1, m2, ctx)
        return game

    @staticmethod
    def _both_have_single_map_idiom(
        game: frog_ast.Game,
        m1: frog_ast.Field,
        m2: frog_ast.Field,
        ctx: PipelineContext,
    ) -> bool:
        assert isinstance(m1.type, frog_ast.MapType)
        assert isinstance(m2.type, frog_ast.MapType)
        v1 = m1.type.value_type
        v2 = m2.type.value_type
        has_m1 = any(
            _match_idiom_suffix(meth, m1.name, v1, ctx) is not None
            for meth in game.methods
            if meth.signature.name != "Initialize"
        )
        has_m2 = any(
            _match_idiom_suffix(meth, m2.name, v2, ctx) is not None
            for meth in game.methods
            if meth.signature.name != "Initialize"
        )
        return has_m1 and has_m2

    def _maybe_emit_missing_guard(
        self,
        game: frog_ast.Game,
        m1: frog_ast.Field,
        m2: frog_ast.Field,
        ctx: PipelineContext,
    ) -> None:
        """If no pair-idiom fired but each map is individually used in a
        single-map lazy-lookup idiom, emit a near-miss pointing out the
        missing disjointness guard."""
        assert isinstance(m1.type, frog_ast.MapType)
        value_type = m1.type.value_type
        any_pair = any(
            _match_pair_idiom_suffix(meth, m1.name, m2.name, value_type) is not None
            for meth in game.methods
            if meth.signature.name != "Initialize"
        )
        if any_pair:
            return
        if not self._both_have_single_map_idiom(game, m1, m2, ctx):
            return
        self._emit_near_miss(
            ctx,
            (
                f"Maps '{m1.name}' and '{m2.name}' look like a lazy-map pair "
                "but each method's idiom lacks the disjointness guard "
                "'k in <other map>' needed to merge them into a sampled "
                "Function"
            ),
            m1.origin,
            m1.name,
            None,
        )

    def _emit_near_miss(
        self,
        ctx: PipelineContext,
        reason: str,
        location: frog_ast.SourceOrigin | None,
        variable: str,
        method_name: str | None,
        suggestion: str | None = None,
    ) -> None:
        ctx.near_misses.append(
            NearMiss(
                transform_name=_LAZY_MAP_PAIR_NAME,
                reason=reason,
                location=location,
                suggestion=suggestion,
                variable=variable,
                method=method_name,
            )
        )

    def _try_rewrite_pair(
        self,
        game: frog_ast.Game,
        m1: frog_ast.Field,
        m2: frog_ast.Field,
        ctx: PipelineContext,
    ) -> frog_ast.Game | None:
        """Attempt to merge ``m1``, ``m2`` into a single sampled Function.

        Preconditions (design §4.2):

        - (P2-1) Every reference to ``m1`` or ``m2`` lies inside the
          guarded-pair idiom suffix of some method.
        - (P2-2) Neither map is explicitly initialized in ``Initialize``.
        - (P2-3) Both maps share the same key and value types.
        - (P2-4) Each method that references either map matches the
          guarded-pair idiom, and the write inside that method lands on one
          of the two maps with the same key parameter used in the guards.
        - (P2-5) At least one method matches the idiom.
        """
        assert isinstance(m1.type, frog_ast.MapType)
        assert isinstance(m2.type, frog_ast.MapType)
        key_type = m1.type.key_type
        value_type = m1.type.value_type

        # Precompute whether any method is a pair-idiom candidate; gate
        # near-miss emissions on this so we don't spam for unrelated pairs.
        any_idiom = any(
            _match_pair_idiom_suffix(m, m1.name, m2.name, value_type) is not None
            for m in game.methods
            if m.signature.name != "Initialize"
        )

        matches: dict[str, _PairIdiomMatch] = {}
        for method in game.methods:
            method_name = method.signature.name
            if method_name == "Initialize":
                # (P2-2) Initialize must not reference either map.
                for stmt in method.block.statements:
                    if _stmt_references_maps(stmt, m1.name, m2.name):
                        if any_idiom:
                            self._emit_near_miss(
                                ctx,
                                (
                                    f"Maps '{m1.name}'/'{m2.name}' are "
                                    "referenced in Initialize; lazy-map-pair "
                                    "canonicalization requires empty initial "
                                    "maps"
                                ),
                                stmt.origin,
                                m1.name,
                                "Initialize",
                            )
                        return None
                continue
            match = _match_pair_idiom_suffix(method, m1.name, m2.name, value_type)
            if match is None:
                # (P2-1) Methods that don't match must not reference
                # either map.
                if _method_references_maps(method, m1.name, m2.name):
                    if any_idiom:
                        self._emit_near_miss(
                            ctx,
                            (
                                f"Maps '{m1.name}'/'{m2.name}' are referenced "
                                f"in method '{method_name}' outside the "
                                "lazy-lookup idiom"
                            ),
                            method.block.origin,
                            m1.name,
                            method_name,
                        )
                    return None
                continue
            # (P2-1) No references to either map before the idiom suffix.
            for stmt in method.block.statements[: match.if_idx]:
                if _stmt_references_maps(stmt, m1.name, m2.name):
                    if any_idiom:
                        self._emit_near_miss(
                            ctx,
                            (
                                f"Maps '{m1.name}'/'{m2.name}' are referenced "
                                f"in method '{method_name}' outside the "
                                "lazy-lookup idiom"
                            ),
                            stmt.origin,
                            m1.name,
                            method_name,
                        )
                    return None
            matches[method_name] = match
        if not matches:
            return None
        _ = key_type  # forwarded to the builder below
        return self._build_rewritten_game(
            game, m1.name, m2.name, key_type, value_type, matches
        )

    def _build_rewritten_game(
        self,
        game: frog_ast.Game,
        m1_name: str,
        m2_name: str,
        key_type: frog_ast.Type,
        value_type: frog_ast.Type,
        matches: dict[str, _PairIdiomMatch],
    ) -> frog_ast.Game:
        new_game = copy.deepcopy(game)

        # 1. Replace the two map fields with a single Function<K, V> field.
        f_name = _fresh_field_name(new_game, "F")
        new_fields: list[frog_ast.Field] = []
        seen = False
        for fld in new_game.fields:
            if fld.name in (m1_name, m2_name):
                if not seen:
                    new_fields.append(
                        frog_ast.Field(
                            frog_ast.FunctionType(
                                copy.deepcopy(key_type),
                                copy.deepcopy(value_type),
                            ),
                            f_name,
                            None,
                        )
                    )
                    seen = True
                continue
            new_fields.append(fld)
        new_game.fields = new_fields

        # 2. Prepend ``F <- Function<K, V>;`` to Initialize (create if absent).
        sample_stmt = frog_ast.Sample(
            None,
            frog_ast.Variable(f_name),
            frog_ast.FunctionType(
                copy.deepcopy(key_type), copy.deepcopy(value_type)
            ),  # type: ignore[arg-type]
        )
        init: frog_ast.Method | None = None
        for m in new_game.methods:
            if m.signature.name == "Initialize":
                init = m
                break
        if init is None:
            init_sig = frog_ast.MethodSignature("Initialize", frog_ast.Void(), [])
            init = frog_ast.Method(init_sig, frog_ast.Block([sample_stmt]))
            new_game.methods = [init] + list(new_game.methods)
        else:
            init.block = frog_ast.Block([sample_stmt] + list(init.block.statements))

        # 3. Replace each matched method's suffix with ``return F(k);``.
        for method in new_game.methods:
            match = matches.get(method.signature.name)
            if match is None:
                continue
            new_return = frog_ast.ReturnStatement(
                frog_ast.FuncCall(
                    frog_ast.Variable(f_name),
                    [frog_ast.Variable(match.key_name)],
                )
            )
            method.block = frog_ast.Block(
                list(method.block.statements[: match.if_idx]) + [new_return]
            )
        return new_game


# ---------------------------------------------------------------------------
# Unify game-local sampled Function<K, V> with let-bound sampled H
# ---------------------------------------------------------------------------

_LOCAL_FN_TO_LET_NAME = "Local Function Field To Let"


def _resolve_fn_type(
    t: frog_ast.FunctionType, proof_namespace: frog_ast.Namespace
) -> frog_ast.FunctionType:
    """Return a FunctionType with domain/range resolved through primitive
    type aliases reachable via *proof_namespace*.  Leaves unresolvable
    sub-types untouched."""
    return frog_ast.FunctionType(
        _resolve_type_ref(t.domain_type, proof_namespace),
        _resolve_type_ref(t.range_type, proof_namespace),
    )


def _type_sym_equal(
    a: frog_ast.Type, b: frog_ast.Type, proof_namespace: frog_ast.Namespace
) -> bool:
    """Semantic type equality that, for BitString parameterizations,
    resolves FieldAccess nodes through the namespace and compares the
    resulting index expressions via sympy. Falls back to AST ``==`` for
    other shapes."""
    if isinstance(a, frog_ast.FunctionType) and isinstance(b, frog_ast.FunctionType):
        return _type_sym_equal(
            a.domain_type, b.domain_type, proof_namespace
        ) and _type_sym_equal(a.range_type, b.range_type, proof_namespace)
    if isinstance(a, frog_ast.BitStringType) and isinstance(b, frog_ast.BitStringType):
        if a.parameterization is None or b.parameterization is None:
            return a.parameterization is None and b.parameterization is None
        a_expr = _resolve_expr_ref(a.parameterization, proof_namespace)
        b_expr = _resolve_expr_ref(b.parameterization, proof_namespace)
        a_sym = _ast_to_sympy(a_expr)
        b_sym = _ast_to_sympy(b_expr)
        if a_sym is not None and b_sym is not None:
            try:
                return bool(sympy_simplify(a_sym - b_sym) == 0)
            except (TypeError, AttributeError):
                pass
        return a == b
    return a == b


def _resolve_expr_ref(
    e: frog_ast.ASTNode,
    proof_namespace: frog_ast.Namespace,
) -> frog_ast.ASTNode:
    """Recursively resolve ``FieldAccess`` / ``Variable`` references through
    ``proof_namespace`` into their concrete values.  Used to normalize the
    index expression inside ``BitString<...>`` so that a let-bound H's
    symbolic ``K.Nss + ...`` matches a field's expanded ``kem_nss + ...``.
    """
    if isinstance(e, frog_ast.FieldAccess) and isinstance(
        e.the_object, frog_ast.Variable
    ):
        obj = proof_namespace.get(e.the_object.name)
        if isinstance(obj, (frog_ast.Primitive, frog_ast.Scheme)):
            for fld in obj.fields:
                if fld.name == e.name and fld.value is not None:
                    return _resolve_expr_ref(fld.value, proof_namespace)
        return e
    if isinstance(e, frog_ast.Variable):
        val = proof_namespace.get(e.name)
        if (
            val is not None
            and isinstance(val, frog_ast.ASTNode)
            and not isinstance(
                val,
                (
                    frog_ast.Primitive,
                    frog_ast.Scheme,
                    frog_ast.Game,
                    frog_ast.Type,
                ),
            )
        ):
            return _resolve_expr_ref(val, proof_namespace)
        return e
    if isinstance(e, frog_ast.BinaryOperation):
        new_left = _resolve_expr_ref(e.left_expression, proof_namespace)
        new_right = _resolve_expr_ref(e.right_expression, proof_namespace)
        if isinstance(new_left, frog_ast.Expression) and isinstance(
            new_right, frog_ast.Expression
        ):
            return frog_ast.BinaryOperation(e.operator, new_left, new_right)
    if isinstance(e, frog_ast.UnaryOperation):
        new_operand = _resolve_expr_ref(e.expression, proof_namespace)
        if isinstance(new_operand, frog_ast.Expression):
            return frog_ast.UnaryOperation(e.operator, new_operand)
    return e


def _resolve_type_ref(
    t: frog_ast.Type,
    proof_namespace: frog_ast.Namespace,
    _seen: frozenset[str] = frozenset(),
) -> frog_ast.Type:
    """Recursively resolve ``FieldAccess(Variable(P), name)`` via a
    Primitive's field definitions in *proof_namespace*.  Falls through
    on any unsupported shape."""
    if isinstance(t, frog_ast.FieldAccess) and isinstance(
        t.the_object, frog_ast.Variable
    ):
        obj = proof_namespace.get(t.the_object.name)
        if isinstance(obj, (frog_ast.Primitive, frog_ast.Scheme)):
            for fld in obj.fields:
                if fld.name == t.name and fld.value is not None:
                    value = fld.value
                    if isinstance(value, frog_ast.Type):
                        return _resolve_type_ref(value, proof_namespace, _seen)
    if isinstance(t, frog_ast.BitStringType) and t.parameterization is not None:
        new_param = _resolve_expr_ref(t.parameterization, proof_namespace)
        if isinstance(new_param, frog_ast.Expression):
            return frog_ast.BitStringType(new_param)
    if isinstance(t, frog_ast.FunctionType):
        return frog_ast.FunctionType(
            _resolve_type_ref(t.domain_type, proof_namespace, _seen),
            _resolve_type_ref(t.range_type, proof_namespace, _seen),
        )
    if isinstance(t, frog_ast.MapType):
        return frog_ast.MapType(
            _resolve_type_ref(t.key_type, proof_namespace, _seen),
            _resolve_type_ref(t.value_type, proof_namespace, _seen),
        )
    if isinstance(t, frog_ast.ArrayType):
        return frog_ast.ArrayType(
            _resolve_type_ref(t.element_type, proof_namespace, _seen), t.count
        )
    if isinstance(t, frog_ast.OptionalType):
        return frog_ast.OptionalType(
            _resolve_type_ref(t.the_type, proof_namespace, _seen)
        )
    if isinstance(t, frog_ast.ProductType):
        return frog_ast.ProductType(
            [_resolve_type_ref(s, proof_namespace, _seen) for s in t.types]
        )
    return t


class LocalFunctionFieldToLet(TransformPass):
    """Unify a game-local sampled ``Function<K, V>`` field with a let-bound
    sampled ``H : Function<K, V>`` of identical type.

    Preconditions (plan §2):

    - P-1. The field ``F`` is sampled exactly once in ``Initialize`` via
      ``F <- Function<K, V>;``.
    - P-2. ``F`` is not otherwise assigned anywhere in the game body.
    - P-3. Every reference to ``F`` outside its defining sample is the
      callee of a ``FuncCall``.
    - P-4. The proof's ``let:`` namespace contains a sampled name ``H``
      with type ``Function<K', V'>`` equal to ``(K, V)``.
    - P-5. ``H`` does not appear syntactically anywhere in the game body.

    Soundness: a uniform random function is observably characterized by
    its outputs on queried inputs; under P-5, no prior observation of
    ``H`` constrains its distribution in this game, so calls to ``F``
    and calls to ``H`` on the same inputs are identically distributed.
    See SEMANTICS.md §6.5 and §9.3.
    """

    name = _LOCAL_FN_TO_LET_NAME

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        # Candidate let targets: sampled Function-typed let bindings.  We
        # resolve type aliases through the proof namespace so that a let
        # declared as ``Function<T.Image, BitString<n>>`` matches a field
        # typed ``Function<ImageSet, BitString<n>>`` (where the primitive
        # ``T`` has ``Set Image = ImageSet``).
        let_candidates: dict[str, frog_ast.FunctionType] = {}
        for entry in ctx.proof_let_types.type_map:
            if (
                isinstance(entry.type, frog_ast.FunctionType)
                and entry.name in ctx.sampled_let_names
            ):
                resolved = _resolve_fn_type(entry.type, ctx.proof_namespace)
                let_candidates[entry.name] = resolved

        for fld in game.fields:
            if not isinstance(fld.type, frog_ast.FunctionType):
                continue
            rewritten = self._try_rewrite(game, fld, let_candidates, ctx)
            if rewritten is not None:
                return rewritten
        return game

    def _emit_near_miss(
        self,
        ctx: PipelineContext,
        reason: str,
        location: frog_ast.SourceOrigin | None,
        variable: str,
        method_name: str | None,
        suggestion: str | None = None,
    ) -> None:
        ctx.near_misses.append(
            NearMiss(
                transform_name=_LOCAL_FN_TO_LET_NAME,
                reason=reason,
                location=location,
                suggestion=suggestion,
                variable=variable,
                method=method_name,
            )
        )

    def _try_rewrite(
        self,
        game: frog_ast.Game,
        fld: frog_ast.Field,
        let_candidates: dict[str, frog_ast.FunctionType],
        ctx: PipelineContext,
    ) -> frog_ast.Game | None:
        f_name = fld.name
        assert isinstance(fld.type, frog_ast.FunctionType)
        f_type = _resolve_fn_type(fld.type, ctx.proof_namespace)

        # P-1, P-2: find unique `F <- Function<K, V>;` sample in Initialize
        # and check there are no other assignments/samples to F anywhere.
        init_sample_idx = self._locate_initialize_sample(game, f_name, f_type, ctx)
        if init_sample_idx is None:
            return None
        if self._has_other_assignments(game, f_name, init_sample_idx, ctx):
            return None

        # P-3: every non-defining reference to F is a call callee.
        if not self._only_call_shaped(game, f_name, init_sample_idx, ctx):
            return None

        # P-4: find a sampled let-bound H with matching type.
        h_name = self._find_matching_let(f_name, f_type, let_candidates, ctx)
        if h_name is None:
            return None

        # P-5: H must not appear anywhere in the game body.
        if self._h_referenced_in_game(game, h_name, ctx, f_name):
            return None

        return self._build_rewritten_game(game, f_name, h_name, init_sample_idx)

    def _locate_initialize_sample(
        self,
        game: frog_ast.Game,
        f_name: str,
        f_type: frog_ast.FunctionType,
        ctx: PipelineContext,
    ) -> int | None:
        """Return the index of the unique ``F <- Function<K, V>;`` in
        Initialize, or None."""
        init: frog_ast.Method | None = None
        for m in game.methods:
            if m.signature.name == "Initialize":
                init = m
                break
        if init is None:
            return None
        found_idx: int | None = None
        for idx, stmt in enumerate(init.block.statements):
            if (
                isinstance(stmt, frog_ast.Sample)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name == f_name
            ):
                if not isinstance(stmt.sampled_from, frog_ast.FunctionType):
                    self._emit_near_miss(
                        ctx,
                        (
                            f"Field '{f_name}' is sampled from a non-Function "
                            "type; LocalFunctionFieldToLet requires "
                            "sampling from Function<K, V>"
                        ),
                        stmt.origin,
                        f_name,
                        "Initialize",
                    )
                    return None
                if not _type_sym_equal(
                    _resolve_fn_type(stmt.sampled_from, ctx.proof_namespace),
                    f_type,
                    ctx.proof_namespace,
                ):
                    self._emit_near_miss(
                        ctx,
                        (
                            f"Field '{f_name}' sampled-from type does not "
                            "match field type"
                        ),
                        stmt.origin,
                        f_name,
                        "Initialize",
                    )
                    return None
                if found_idx is not None:
                    self._emit_near_miss(
                        ctx,
                        (
                            f"Field '{f_name}' is sampled more than once in "
                            "Initialize"
                        ),
                        stmt.origin,
                        f_name,
                        "Initialize",
                    )
                    return None
                found_idx = idx
        return found_idx

    def _has_other_assignments(
        self,
        game: frog_ast.Game,
        f_name: str,
        init_sample_idx: int,
        ctx: PipelineContext,
    ) -> bool:
        """Check for any assignment-like use of F other than the
        Initialize sample at ``init_sample_idx``."""
        for method in game.methods:
            is_init = method.signature.name == "Initialize"
            for idx, stmt in enumerate(method.block.statements):
                if is_init and idx == init_sample_idx:
                    continue
                if self._stmt_writes_to(stmt, f_name):
                    self._emit_near_miss(
                        ctx,
                        (
                            f"Field '{f_name}' is assigned outside the "
                            "unique Initialize sample; "
                            "LocalFunctionFieldToLet requires a single sample"
                        ),
                        stmt.origin,
                        f_name,
                        method.signature.name,
                    )
                    return True
        return False

    @staticmethod
    def _stmt_writes_to(stmt: frog_ast.Statement, name: str) -> bool:
        """Return True if *stmt* assigns/samples into a target named
        ``name`` (direct variable, or array/field access on it)."""
        if isinstance(stmt, (frog_ast.Assignment, frog_ast.Sample)):
            return LocalFunctionFieldToLet._target_touches(stmt.var, name)
        if isinstance(stmt, frog_ast.UniqueSample):
            return LocalFunctionFieldToLet._target_touches(stmt.var, name)
        return False

    @staticmethod
    def _target_touches(target: frog_ast.Expression, name: str) -> bool:
        if isinstance(target, frog_ast.Variable):
            return target.name == name
        if isinstance(target, frog_ast.ArrayAccess) and isinstance(
            target.the_array, frog_ast.Variable
        ):
            return target.the_array.name == name
        if isinstance(target, frog_ast.FieldAccess) and isinstance(
            target.the_object, frog_ast.Variable
        ):
            return target.the_object.name == name
        return False

    def _only_call_shaped(
        self,
        game: frog_ast.Game,
        f_name: str,
        init_sample_idx: int,
        ctx: PipelineContext,
    ) -> bool:
        """Return True iff every occurrence of ``Variable(f_name)``
        outside the defining sample appears as ``FuncCall.func``."""
        call_count, field_access_count = _count_rf_calls(
            self._body_excluding_init_sample(game, init_sample_idx), f_name
        )
        if field_access_count > 0:
            self._emit_near_miss(
                ctx,
                (
                    f"Field '{f_name}' is used via field access; "
                    "LocalFunctionFieldToLet requires only call-shaped uses"
                ),
                None,
                f_name,
                None,
            )
            return False
        bare_refs = _count_variable_refs(
            self._body_excluding_init_sample(game, init_sample_idx), f_name
        )
        if bare_refs != call_count:
            self._emit_near_miss(
                ctx,
                (
                    f"Field '{f_name}' is referenced in a non-call position; "
                    "LocalFunctionFieldToLet requires only call-shaped uses"
                ),
                None,
                f_name,
                None,
            )
            return False
        return True

    @staticmethod
    def _body_excluding_init_sample(
        game: frog_ast.Game, init_sample_idx: int
    ) -> frog_ast.Block:
        """Return a Block concatenating every method body, replacing the
        Initialize method body with a copy that has the sample stmt
        elided.  Used for non-defining-reference accounting."""
        stmts: list[frog_ast.Statement] = []
        for method in game.methods:
            if method.signature.name == "Initialize":
                for idx, s in enumerate(method.block.statements):
                    if idx == init_sample_idx:
                        continue
                    stmts.append(s)
            else:
                stmts.extend(method.block.statements)
        return frog_ast.Block(stmts)

    def _find_matching_let(
        self,
        f_name: str,
        f_type: frog_ast.FunctionType,
        let_candidates: dict[str, frog_ast.FunctionType],
        ctx: PipelineContext,
    ) -> str | None:
        matches = [
            name
            for name, t in let_candidates.items()
            if _type_sym_equal(t, f_type, ctx.proof_namespace)
        ]
        if not matches:
            # Record near-miss if a same-named let declared but not sampled.
            declared_but_not_sampled = [
                entry.name
                for entry in ctx.proof_let_types.type_map
                if isinstance(entry.type, frog_ast.FunctionType)
                and entry.type == f_type
                and entry.name not in ctx.sampled_let_names
            ]
            if declared_but_not_sampled:
                self._emit_near_miss(
                    ctx,
                    (
                        f"Let binding(s) {declared_but_not_sampled} match the "
                        f"type of field '{f_name}' but are declared (known "
                        "deterministic) rather than sampled; "
                        "LocalFunctionFieldToLet requires a sampled let"
                    ),
                    None,
                    f_name,
                    None,
                )
            return None
        # Deterministic pick: first by type_map order.
        for entry in ctx.proof_let_types.type_map:
            if entry.name in matches:
                return entry.name
        return matches[0]

    def _h_referenced_in_game(
        self,
        game: frog_ast.Game,
        h_name: str,
        ctx: PipelineContext,
        f_name: str,
    ) -> bool:
        for method in game.methods:
            if _count_variable_refs(method.block, h_name) > 0:
                self._emit_near_miss(
                    ctx,
                    (
                        f"Candidate let binding '{h_name}' is referenced in "
                        f"method '{method.signature.name}'; "
                        "LocalFunctionFieldToLet requires H to be unused in "
                        "the game body"
                    ),
                    method.block.origin,
                    f_name,
                    method.signature.name,
                )
                return True
        return False

    def _build_rewritten_game(
        self,
        game: frog_ast.Game,
        f_name: str,
        h_name: str,
        init_sample_idx: int,
    ) -> frog_ast.Game:
        new_game = copy.deepcopy(game)

        # 1. Drop the field F.
        new_game.fields = [f for f in new_game.fields if f.name != f_name]

        # 2. Drop the `F <- Function<...>;` from Initialize.
        for method in new_game.methods:
            if method.signature.name != "Initialize":
                continue
            method.block = frog_ast.Block(
                [
                    s
                    for idx, s in enumerate(method.block.statements)
                    if idx != init_sample_idx
                ]
            )
            break

        # 3. Rewrite every remaining reference to F (all of which, under
        #    P-3, are in FuncCall callee position) to H.
        for method in new_game.methods:
            method.block = _RenameVariableTransformer(f_name, h_name).transform(
                method.block
            )

        return new_game


class _RenameVariableTransformer(Transformer):
    """Rename every ``Variable(from_name)`` occurrence to
    ``Variable(to_name)``.  Intended for cases where the caller has
    already verified that every such occurrence is semantically a
    reference that should be renamed (e.g. after P-3 has confirmed all
    non-defining uses are call-position)."""

    def __init__(self, from_name: str, to_name: str) -> None:
        self.from_name = from_name
        self.to_name = to_name

    def transform_variable(self, node: frog_ast.Variable) -> frog_ast.Variable:
        if node.name == self.from_name:
            return frog_ast.Variable(self.to_name)
        return node
