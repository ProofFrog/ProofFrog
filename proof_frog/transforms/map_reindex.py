"""Map key re-indexing under an injective deterministic function (design §3).

:class:`MapKeyReindex` rewrites a ``Map<A, V>`` field to ``Map<B, V>`` when every
use of the map's keys is through a ``deterministic injective`` primitive method
``f : A -> B``.  After this pass, scans whose predicate is ``e[0] == f(a)``
become ``e[0] == a`` (under substitution), which the literal-equality
``LazyMapScan`` can then fold to a direct lookup.

Soundness argument: see design spec §3.3 (value preservation, non-collision,
iteration preservation, adversary-invisibility of internal state).
"""

from __future__ import annotations

from .. import frog_ast
from ._base import PipelineContext, TransformPass

_NAME = "Map Key Reindex"


class MapKeyReindex(TransformPass):
    """Re-index a ``Map<A, V>`` field to ``Map<B, V>`` under a ``deterministic
    injective`` primitive method ``f : A -> B`` (design §3)."""

    name = _NAME

    def apply(
        self, game: frog_ast.Game, ctx: PipelineContext
    ) -> frog_ast.Game:  # pylint: disable=unused-argument
        return game  # implemented in subsequent tasks
