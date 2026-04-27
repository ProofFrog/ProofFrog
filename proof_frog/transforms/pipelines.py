"""Declarative pipeline definitions for game canonicalization.

CORE_PIPELINE is the fixed-point transformation loop applied to games.
STANDARDIZATION_PIPELINE runs once after convergence to normalize names.
"""

from __future__ import annotations

from ._base import TransformPass
from .symbolic import SymbolicComputation
from .sampling import (
    SimplifySplice,
    SliceOfInlineConcat,
    MergeUniformSamples,
    MergeProductSamples,
)
from .sampling import (
    SplitUniformSamples,
    SingleCallFieldToLocal,
    CounterGuardedFieldToLocal,
    SinkUniformSample,
    LocalizeInitOnlyFieldSample,
)
from .random_functions import (
    ExtractRFCalls,
    UniqueRFSimplification,
    ChallengeExclusionRFToUniform,
    LocalRFToUniform,
    DistinctConstRFToUniform,
    FreshInputRFToUniform,
    LazyMapToSampledFunction,
    LazyMapPairToSampledFunction,
    LocalFunctionFieldToLet,
)
from .map_iteration import LazyMapScan
from .map_reindex import MapKeyReindex
from .inlining import (
    RedundantCopy,
    IfSplitBranchAssignment,
    InlineSingleUseVariable,
    DeduplicateDeterministicCalls,
    CrossMethodFieldAlias,
    HoistDeterministicCallToInitialize,
    SplitOpaqueTupleField,
    InlineSingleUseField,
    HoistGroupExpToInitialize,
    RefactorGroupElemFieldExp,
    ForwardExpressionAlias,
    InlineLocalTupleLiteral,
    HoistFieldPureAlias,
    ExtractRepeatedTupleAccess,
    InlineMultiUsePureExpression,
    CollapseAssignment,
    RedundantFieldCopy,
)
from .algebraic import (
    UniformXorSimplification,
    UniformModIntSimplification,
    UniformGroupElemSimplification,
    SimplifyNotPass,
    BooleanIdentity,
    BooleanAbsorption,
    XorCancellation,
    XorIdentity,
    ModIntSimplification,
    NormalizeCommutativeChains,
    FlattenConcatChain,
    ReflexiveComparison,
    InjectiveEqualitySimplify,
    ConcatEqualityDecompose,
    TupleEqualityDecompose,
    GroupElemSimplification,
    GroupElemCancellation,
    GroupElemExponentCombination,
)
from .structural import (
    TopologicalSort,
    RemoveDuplicateFields,
    RemoveUnnecessaryFields,
    UniformBijectionElimination,
)
from .control_flow import (
    IfConditionAliasSubstitution,
    RedundantConditionalReturn,
    AbsorbRedundantEarlyReturn,
    IfFalseReturnToConjunction,
    FoldEquivalentReturnBranch,
    BranchElimination,
    UniqExclusionBranchElimination,
    ElseUnwrap,
    SimplifyReturn,
    SimplifyIf,
    RemoveUnreachable,
)
from .types import DeadNullGuardElimination, SubsetTypeNormalization
from .tuples import (
    FoldTupleIndex,
    ExpandTuple,
    SimplifyTuple,
    CollapseSingleIndexTuple,
)
from .standardization import (
    VariableStandardize,
    StandardizeFieldNames,
    FieldLexMinByRHS,
    BubbleSortFieldAssignments,
    StabilizeIndependentStatements,
)

CORE_PIPELINE: list[TransformPass] = [
    SingleCallFieldToLocal(),
    CounterGuardedFieldToLocal(),
    SymbolicComputation(),
    SimplifySplice(),
    SliceOfInlineConcat(),
    MergeUniformSamples(),
    MergeProductSamples(),
    SplitUniformSamples(),
    UniformBijectionElimination(),
    FoldTupleIndex(),
    ExtractRepeatedTupleAccess(),
    LazyMapScan(),
    MapKeyReindex(),
    LazyMapToSampledFunction(),
    LazyMapPairToSampledFunction(),
    LocalFunctionFieldToLet(),
    ExtractRFCalls(),
    UniqueRFSimplification(),
    ChallengeExclusionRFToUniform(),
    LocalRFToUniform(),
    DistinctConstRFToUniform(),
    FreshInputRFToUniform(),
    RedundantCopy(),
    IfSplitBranchAssignment(),
    InlineSingleUseVariable(),
    DeduplicateDeterministicCalls(),
    ForwardExpressionAlias(),
    UniformXorSimplification(),
    UniformModIntSimplification(),
    UniformGroupElemSimplification(),
    TopologicalSort(),
    HoistFieldPureAlias(),
    RemoveDuplicateFields(),
    CrossMethodFieldAlias(),
    HoistDeterministicCallToInitialize(),
    SplitOpaqueTupleField(),
    IfConditionAliasSubstitution(),
    RedundantConditionalReturn(),
    UniqExclusionBranchElimination(),
    BranchElimination(),
    InlineLocalTupleLiteral(),
    ElseUnwrap(),
    InlineSingleUseField(),
    LocalizeInitOnlyFieldSample(),
    RemoveUnnecessaryFields(),
    CollapseAssignment(),
    SimplifyReturn(),
    SinkUniformSample(),
    SimplifyIf(),
    DeadNullGuardElimination(),
    SubsetTypeNormalization(),
    CollapseSingleIndexTuple(),
    ExpandTuple(),
    SimplifyNotPass(),
    BooleanIdentity(),
    BooleanAbsorption(),
    XorCancellation(),
    XorIdentity(),
    ModIntSimplification(),
    HoistGroupExpToInitialize(),
    RefactorGroupElemFieldExp(),
    GroupElemSimplification(),
    GroupElemCancellation(),
    GroupElemExponentCombination(),
    NormalizeCommutativeChains(),
    FlattenConcatChain(),
    ReflexiveComparison(),
    InjectiveEqualitySimplify(),
    ConcatEqualityDecompose(),
    TupleEqualityDecompose(),
    InlineMultiUsePureExpression(),
    RedundantFieldCopy(),
    SimplifyTuple(),
    RemoveUnreachable(),
    AbsorbRedundantEarlyReturn(),
    IfFalseReturnToConjunction(),
    FoldEquivalentReturnBranch(),
]

STANDARDIZATION_PIPELINE: list[TransformPass] = [
    VariableStandardize(),
    StandardizeFieldNames(),
    NormalizeCommutativeChains(),
    BubbleSortFieldAssignments(),
    StabilizeIndependentStatements(),
    VariableStandardize(),
    # Run Phase-3 lex-min with the FINAL local-variable names visible
    # (RHS sort keys depend on names), then re-run statement reordering
    # so field-assignment statements settle on the post-Phase-3 names.
    FieldLexMinByRHS(),
    BubbleSortFieldAssignments(),
    StabilizeIndependentStatements(),
]
