"""Per-transform EasyCrypt exporter (prototype).

Parallel to ``proof_frog/export/easycrypt/`` (per-hop). Emits one
EasyCrypt micro-lemma per individual ProofFrog canonicalization-transform
application, chained together via ``transitivity`` to discharge the
per-step canonicalization gap. See
``extras/docs/plans/in-progress/2026-05-23-easycrypt-export-per-transform-prototype.md``
for the design and scope.
"""

from .exporter import export_proof_file_per_transform

__all__ = ["export_proof_file_per_transform"]
