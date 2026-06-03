"""Oracle-list data model for EC game-file translation.

Multi-oracle foundation, phase P1
(``extras/docs/plans/in-progress/2026-06-01-easycrypt-multi-oracle-foundation.md``).

A game file's two sides expose a set of oracle *methods*. The single-oracle
exporter only ever named the *first* method
(``oracle_name_by_game_file[gf] = first_method.name.lower()``); the multi-oracle
foundation needs the full ordered list plus a classification into:

- the **init** oracle -- the one lifted into the game wrapper's ``main()``,
  whose result is passed to the adversary (in the corpus it is literally
  ``Initialize``); and
- the **post-init** oracles -- the ones the adversary may call adaptively.

Init-detection rule: a method named ``Initialize`` (case-insensitive) is the
init oracle; every other method, in declaration order, is a post-init oracle.

A game with no ``Initialize`` method is *single-oracle* (the degenerate case):
``init_name`` is ``None`` and every method is post-init (adversary-facing). This
matches the existing single-oracle emission, where the adversary calls the lone
oracle directly with nothing lifted into ``main()`` -- so ``scalar_oracle_name``
reproduces the old ``first_method.name.lower()`` exactly.

This module is pure data derived from the AST; it depends only on
``frog_ast`` and has no EC-emission side effects. The emitters that consume the
classification land in P2--P4.
"""

from __future__ import annotations

from dataclasses import dataclass

from ... import frog_ast

#: FrogLang name of the init oracle (matched case-insensitively).
INIT_ORACLE_FROG_NAME = "Initialize"


@dataclass
class GameOracleModel:
    """Ordered oracle names for one game file, with init/post-init split.

    All names are the EC-rendered (lowercased) oracle identifiers, in the
    method declaration order of the game.
    """

    all_names: list[str]
    init_name: str | None
    post_init_names: list[str]

    @property
    def is_multi_oracle(self) -> bool:
        """True iff the game has a lifted ``Initialize`` oracle.

        Single-method games and multi-method games that happen to lack an
        ``Initialize`` both report ``False`` -- there is nothing to lift into
        ``main()`` and the existing single-oracle emission path applies.
        """
        return self.init_name is not None

    @property
    def scalar_oracle_name(self) -> str:
        """Backward-compatible single oracle name (the first method).

        Equal to the legacy ``first_method.signature.name.lower()`` the
        single-oracle exporter keyed off, so single-oracle output stays
        byte-identical when this model is used to derive it.
        """
        return self.all_names[0]


def classify_game(game: frog_ast.Game) -> GameOracleModel:
    """Classify one game side's oracle methods (see module docstring)."""
    all_names = [m.signature.name.lower() for m in game.methods]
    init_idx = next(
        (
            i
            for i, m in enumerate(game.methods)
            if m.signature.name.lower() == INIT_ORACLE_FROG_NAME.lower()
        ),
        None,
    )
    if init_idx is None:
        return GameOracleModel(
            all_names=all_names,
            init_name=None,
            post_init_names=list(all_names),
        )
    return GameOracleModel(
        all_names=all_names,
        init_name=all_names[init_idx],
        post_init_names=[n for i, n in enumerate(all_names) if i != init_idx],
    )


def classify_game_file(game_file: frog_ast.GameFile) -> GameOracleModel:
    """Classify a game file from its first side.

    Both sides must expose the same oracle methods; that invariant is enforced
    where the oracle module type is emitted
    (``module_translator.translate_game_file_oracle``), so classifying from the
    first side is sufficient here.
    """
    return classify_game(game_file.games[0])
