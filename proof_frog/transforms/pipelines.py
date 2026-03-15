"""Declarative pipeline definitions for game canonicalization.

CORE_PIPELINE is the fixed-point transformation loop applied to games.
STANDARDIZATION_PIPELINE runs once after convergence to normalize names.
"""

from __future__ import annotations

from ._base import TransformPass
from .symbolic import SymbolicComputation
from .sampling import SimplifySplice, MergeUniformSamples, MergeProductSamples
from .sampling import SplitUniformSamples
from .random_functions import UniqueRFSimplification
from .inlining import (
    RedundantCopy,
    InlineSingleUseVariable,
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
    BranchElimination,
    SimplifyReturn,
    SimplifyIf,
    RemoveUnreachable,
)
from .types import DeadNullGuardElimination, SubsetTypeNormalization
from .tuples import ExpandTuple, SimplifyTuple
from .standardization import (
    VariableStandardize,
    StandardizeFieldNames,
    BubbleSortFieldAssignments,
)

CORE_PIPELINE: list[TransformPass] = [
    SymbolicComputation(),
    SimplifySplice(),
    MergeUniformSamples(),
    MergeProductSamples(),
    SplitUniformSamples(),
    TrivialEncodingElimination(),
    UniqueRFSimplification(),
    RedundantCopy(),
    InlineSingleUseVariable(),
    UniformXorSimplification(),
    UniformModIntSimplification(),
    TopologicalSort(),
    RemoveDuplicateFields(),
    BranchElimination(),
    RemoveUnnecessaryFields(),
    CollapseAssignment(),
    SimplifyReturn(),
    SimplifyIf(),
    DeadNullGuardElimination(),
    SubsetTypeNormalization(),
    ExpandTuple(),
    SimplifyNotPass(),
    XorCancellation(),
    XorIdentity(),
    ModIntSimplification(),
    ReflexiveComparison(),
    RedundantFieldCopy(),
    SimplifyTuple(),
    RemoveUnreachable(),
]

STANDARDIZATION_PIPELINE: list[TransformPass] = [
    VariableStandardize(),
    StandardizeFieldNames(),
    BubbleSortFieldAssignments(),
]
