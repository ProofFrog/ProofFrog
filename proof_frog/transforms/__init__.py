"""Pipeline-as-Data transformation infrastructure for ProofFrog.

This package provides a declarative transformation pipeline for
canonicalizing game ASTs during proof verification.
"""

from ._base import TransformPass, PipelineContext, run_pipeline, run_standardization
from .pipelines import CORE_PIPELINE, STANDARDIZATION_PIPELINE

__all__ = [
    "TransformPass",
    "PipelineContext",
    "run_pipeline",
    "run_standardization",
    "CORE_PIPELINE",
    "STANDARDIZATION_PIPELINE",
]
