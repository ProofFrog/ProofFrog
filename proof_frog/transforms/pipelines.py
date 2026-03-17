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
    ForwardExpressionAlias,
    HoistFieldPureAlias,
    InlineMultiUsePureExpression,
    CollapseAssignment,
    RedundantFieldCopy,
)
from .algebraic import (
    UniformXorSimplification,
    UniformModIntSimplification,
    SimplifyNotPass,
    XorCancellation,
    XorIdentity,
    ModIntSimplification,
    ReflexiveComparison,
)
from .structural import (
    TopologicalSort,
    RemoveDuplicateFields,
    RemoveUnnecessaryFields,
    TrivialEncodingElimination,
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
    TrivialEncodingElimination(),
    FoldTupleIndex(),
    ExtractRFCalls(),
    UniqueRFSimplification(),
    ChallengeExclusionRFToUniform(),
    LocalRFToUniform(),
    RedundantCopy(),
    InlineSingleUseVariable(),
    ForwardExpressionAlias(),
    UniformXorSimplification(),
    UniformModIntSimplification(),
    TopologicalSort(),
    HoistFieldPureAlias(),
    RemoveDuplicateFields(),
    IfConditionAliasSubstitution(),
    RedundantConditionalReturn(),
    BranchElimination(),
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
    XorCancellation(),
    XorIdentity(),
    ModIntSimplification(),
    ReflexiveComparison(),
    InlineMultiUsePureExpression(),
    RedundantFieldCopy(),
    SimplifyTuple(),
    RemoveUnreachable(),
]

STANDARDIZATION_PIPELINE: list[TransformPass] = [
    VariableStandardize(),
    StandardizeFieldNames(),
    BubbleSortFieldAssignments(),
    StabilizeIndependentStatements(),
    VariableStandardize(),
]
