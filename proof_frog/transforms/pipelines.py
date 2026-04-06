"""Declarative pipeline definitions for game canonicalization.

CORE_PIPELINE is the fixed-point transformation loop applied to games.
STANDARDIZATION_PIPELINE runs once after convergence to normalize names.
"""

from __future__ import annotations

from ._base import TransformPass
from .symbolic import SymbolicComputation
from .sampling import SimplifySplice, MergeUniformSamples, MergeProductSamples
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
)
from .inlining import (
    RedundantCopy,
    InlineSingleUseVariable,
    DeduplicateDeterministicCalls,
    CrossMethodFieldAlias,
    InlineSingleUseField,
    ForwardExpressionAlias,
    HoistFieldPureAlias,
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
    XorCancellation,
    XorIdentity,
    ModIntSimplification,
    NormalizeCommutativeChains,
    ReflexiveComparison,
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
    BranchElimination,
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
    BubbleSortFieldAssignments,
    StabilizeIndependentStatements,
)

CORE_PIPELINE: list[TransformPass] = [
    SingleCallFieldToLocal(),
    CounterGuardedFieldToLocal(),
    SymbolicComputation(),
    SimplifySplice(),
    MergeUniformSamples(),
    MergeProductSamples(),
    SplitUniformSamples(),
    UniformBijectionElimination(),
    FoldTupleIndex(),
    ExtractRFCalls(),
    UniqueRFSimplification(),
    ChallengeExclusionRFToUniform(),
    LocalRFToUniform(),
    RedundantCopy(),
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
    IfConditionAliasSubstitution(),
    RedundantConditionalReturn(),
    BranchElimination(),
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
    XorCancellation(),
    XorIdentity(),
    ModIntSimplification(),
    GroupElemSimplification(),
    GroupElemCancellation(),
    GroupElemExponentCombination(),
    NormalizeCommutativeChains(),
    ReflexiveComparison(),
    InlineMultiUsePureExpression(),
    RedundantFieldCopy(),
    SimplifyTuple(),
    RemoveUnreachable(),
]

STANDARDIZATION_PIPELINE: list[TransformPass] = [
    VariableStandardize(),
    StandardizeFieldNames(),
    NormalizeCommutativeChains(),
    BubbleSortFieldAssignments(),
    StabilizeIndependentStatements(),
    VariableStandardize(),
]
