"""Engine-backed resolution context for LaTeX proof export.

Owns construction of a ``ProofEngine`` from a parsed proof file and exposes
exactly the resolution the proof renderer needs, so the renderer stays
layout-only and testable against a fake context.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TypeAlias

from ... import advantage, frog_ast, frog_parser, proof_engine, visitors


@dataclass
class StepRender:
    """Symbolic-mode rendering inputs for a game step.

    ``challenger`` is the step's challenger node (rendered as a reference);
    ``reduction_ref`` is the composed reduction node (or None); ``novel`` is
    the game AST to actually draw (a reduction or an explicit intermediate
    game), or None for a start/end step that only references definitions.
    """

    challenger: frog_ast.Expression
    reduction_ref: frog_ast.ParameterizedGame | None
    novel: frog_ast.Game | None


@dataclass
class Loop:
    """An ``induction`` block: a hybrid over ``name`` from ``start`` to ``end``.

    ``outer`` lists the enclosing loops, outermost first. ``first`` and
    ``last`` number the block's first and last games.
    """

    name: str
    start: frog_ast.Expression
    end: frog_ast.Expression
    outer: list[Loop]
    first: int = 0
    last: int = 0


@dataclass
class GameRef:
    """Game ``G_number``, at one index per enclosing loop (outermost first)."""

    number: int
    indices: list[frog_ast.Expression] = field(default_factory=list)


@dataclass
class GameEntry:
    """A game step and the reference that labels it."""

    step: frog_ast.Step
    ref: GameRef


@dataclass
class Hop:
    """A hop from game ``source`` to game ``target``."""

    kind: str  # "interchangeable" | "assumption" | "lemma" | "upto"
    # The licensing game (kinds "assumption", "lemma") or event (kind "upto").
    assumption: frog_ast.Expression | None
    source: GameRef
    target: GameRef
    # The proof file of the licensing lemma (kind "lemma", or "upto" by lemma).
    lemma_path: str | None = None
    # Step assumptions (``assume e;`` in ``games:``) stated for this hop.
    conditions: list[frog_ast.Expression] = field(default_factory=list)
    # The hop repeats for each value of these loops' variables.
    loops: list[Loop] = field(default_factory=list)
    # The rollover of ``loops[-1]``: from index i to i + 1, for i < end.
    rollover: bool = False


SequenceEntry: TypeAlias = GameEntry | Hop | Loop


class ProofContext:
    """Resolves a proof file's games against its import namespace."""

    def __init__(self, path: str) -> None:
        self.path = path
        # Symbolic-mode rendering reads helper (reduction / intermediate game)
        # bodies straight off this AST, so keep tuple-destructuring bindings
        # intact (desugar=False) for faithful output. The engine only
        # understands core statements (it inlines helpers in inlined mode), so
        # it is set up from a separately-desugared parse of the same file.
        self.proof_file = frog_parser.parse_proof_file(path, desugar=False)
        self.engine = proof_engine.ProofEngine(False)
        self._load_imports(self.engine, desugar=True)
        self.engine.set_up_proof_context(frog_parser.parse_proof_file(path))
        # Render engine: a second, never-proven engine populated from
        # non-desugared parses. Its namespaces feed the Definitions
        # (security_game_files) and Construction (let_constructions) sections,
        # so imported games and instantiated schemes that destructure render as
        # tuple-LHS lines instead of the engine's desugared `_tup` temporaries.
        # The proving engine above stays desugared (inlined-mode resolution
        # needs core statements); only render-side reads use this copy.
        self._render_engine = proof_engine.ProofEngine(False)
        self._load_imports(self._render_engine, desugar=False)
        self._render_engine.set_up_proof_context(self.proof_file)
        self._sequence: list[SequenceEntry] | None = None

    # pylint: disable=duplicate-code
    # (import-loading mirrors web_server._setup_engine_for_proof; kept local
    #  so the export package does not import the Flask web module.)
    def _load_imports(self, engine: proof_engine.ProofEngine, *, desugar: bool) -> None:
        for imp in self.proof_file.imports:
            imp_path = frog_parser.resolve_import_path(imp.filename, self.path)
            # pylint: disable=protected-access
            file_type = frog_parser._get_file_type(imp_path)
            # pylint: enable=protected-access
            root: frog_ast.Root
            match file_type:
                case frog_ast.FileType.PRIMITIVE:
                    # Primitives have no method bodies, so never desugar.
                    root = frog_parser.parse_primitive_file(imp_path)
                case frog_ast.FileType.SCHEME:
                    root = frog_parser.parse_scheme_file(imp_path, desugar=desugar)
                case frog_ast.FileType.GAME:
                    root = frog_parser.parse_game_file(imp_path, desugar=desugar)
                case _:
                    raise TypeError(f"Cannot import {file_type}")
            name = imp.rename if imp.rename else root.get_export_name()
            engine.add_definition(name, root)

    # pylint: enable=duplicate-code

    def assumptions(self) -> list[frog_ast.Notion]:
        return list(self.proof_file.assumptions)

    def lemmas(self) -> list[frog_ast.Lemma]:
        return list(self.proof_file.lemmas)

    def lemma_path(self, notion: frog_ast.Expression) -> str | None:
        """The proof file of the lemma entry for ``notion``, or None."""
        for lemma in self.proof_file.lemmas:
            if str(lemma.game) == str(notion):
                return lemma.proof_path
        return None

    def theorem(self) -> frog_ast.Notion:
        return self.proof_file.theorem

    def claimed_bound(self) -> frog_ast.Expression | None:
        """The proof's author-claimed advantage bound, or None if absent.

        This is the optional ``bound:`` clause -- a numeric expression over
        ``advantage(...)`` references, per-oracle counts, cardinalities, and
        parameters. When present it is the bound the theorem statement should
        display (the author's intended, human-readable form); otherwise the
        renderer falls back to the synthesized bound.
        """
        claimed = self.proof_file.claimed_bound
        return None if claimed is None else claimed.bound

    def _referenced_game_names(self) -> list[str]:
        names: list[str] = []
        for notion in [*self.proof_file.assumptions, self.proof_file.theorem]:
            names.append(frog_ast.notion_game(notion).name)
        for step in self.game_steps():
            challenger = step.challenger
            if isinstance(challenger, frog_ast.ConcreteGame):
                names.append(challenger.game.name)
            elif isinstance(challenger, frog_ast.ParameterizedGame):
                names.append(challenger.name)
        return names

    def security_game_files(self) -> list[frog_ast.GameFile]:
        seen: set[str] = set()
        result: list[frog_ast.GameFile] = []
        for name in self._referenced_game_names():
            if name in seen:
                continue
            seen.add(name)
            # Read from the non-desugared render engine so destructuring
            # bindings render faithfully (Part 2.5).
            resolved = self._render_engine.definition_namespace.get(name)
            if isinstance(resolved, frog_ast.GameFile):
                result.append(resolved)
        return result

    def let_types(self) -> visitors.NameTypeMap:
        """Name->Type map of the proof's let bindings.

        Fed to the renderer as base scope types so operands referencing
        let-bound variables (e.g. a ``BitString`` let) disambiguate
        ``+``/``||``. Desugaring does not affect let types, so the proving
        engine's map is reused.
        """
        return self.engine.proof_let_types

    def let_constructions(self) -> list[tuple[str, frog_ast.Root]]:
        result: list[tuple[str, frog_ast.Root]] = []
        for let in self.proof_file.lets:
            # Read from the non-desugared render engine (Part 2.5).
            resolved = self._render_engine.proof_namespace.get(let.name)
            if isinstance(resolved, (frog_ast.Scheme, frog_ast.Primitive)):
                result.append((let.name, resolved))
        return result

    def game_steps(self) -> list[frog_ast.Step]:
        """Every ``Step`` of the games list, inductions' included, in order."""
        return [e.step for e in self.sequence() if isinstance(e, GameEntry)]

    def _helper(self, name: str) -> frog_ast.Game | None:
        """Look up a named helper (reduction or intermediate game) by name."""
        for game in self.proof_file.helpers:
            if game.name == name:
                return game
        return None

    def resolve_inlined(self, step: frog_ast.Step) -> frog_ast.Game:
        """Resolve a game step to a fully-inlined AST via the engine."""
        return self.engine.resolve_step_game(step.challenger, step.reduction)

    def resolve_symbolic(self, step: frog_ast.Step) -> StepRender:
        """Return symbolic-mode rendering inputs for a game step.

        The ``novel`` field is the helper game (reduction or explicit
        intermediate game) that should be drawn in the figure.  It is
        ``None`` for start/end steps that only reference definitions.
        """
        novel: frog_ast.Game | None = None
        if step.reduction is not None:
            novel = self._helper(step.reduction.name)
        elif isinstance(step.challenger, frog_ast.ParameterizedGame):
            # A challenger naming a proof helper is an explicit intermediate
            # game (not an imported security game).
            novel = self._helper(step.challenger.name)
        return StepRender(
            challenger=step.challenger,
            reduction_ref=step.reduction,
            novel=novel,
        )

    def hop_kinds(self) -> list[Hop]:
        """Every hop of the games list, in reading order."""
        return [e for e in self.sequence() if isinstance(e, Hop)]

    def sequence(self) -> list[SequenceEntry]:
        """The games list as games, hops and hybrids, in reading order.

        An ``induction`` block contributes its ``Loop``, the entry hop into its
        first game at ``start``, its body at the loop variable, and the
        rollover hop from index i to i + 1; the next hop leaves its last game
        at ``end``. As in the engine, a step assumption is a condition of the
        hop after it, and only a side flip between two steps is a reduction
        hop: both challengers are ``ConcreteGame``s over the same underlying
        game with the same reduction, differing only in ``which``.
        """
        if self._sequence is None:
            self._sequence = []
            self._add_steps(
                self.proof_file.steps, [], self._sequence, itertools.count()
            )
        return self._sequence

    def _add_steps(
        self,
        steps: list[frog_ast.ProofStep],
        loops: list[Loop],
        out: list[SequenceEntry],
        numbers: Iterator[int],
    ) -> tuple[GameEntry | None, GameEntry | None, list[frog_ast.Expression]]:
        """Append one nesting level of ``steps`` to ``out``.

        Returns the level's first and last games, which the engine's entry,
        rollover and exit hops use, and its trailing step assumptions.
        """
        indices: list[frog_ast.Expression] = [
            frog_ast.Variable(outer.name) for outer in loops
        ]
        first: GameEntry | None = None
        last: GameEntry | None = None
        prev: frog_ast.Step | None = None  # a side flip needs two adjacent steps
        source: GameRef | None = None
        conditions: list[frog_ast.Expression] = []
        for step in steps:
            if isinstance(step, frog_ast.StepAssumption):
                conditions.append(step.expression)
                continue
            if isinstance(step, frog_ast.Step):
                entry = GameEntry(step, GameRef(next(numbers), list(indices)))
                if source is not None:
                    kind, assumption = self._justify(prev, step)
                    out.append(
                        Hop(
                            kind,
                            assumption,
                            source,
                            entry.ref,
                            lemma_path=(
                                None
                                if assumption is None
                                else self.lemma_path(assumption)
                            ),
                            conditions=conditions,
                            loops=loops,
                        )
                    )
                out.append(entry)
                first = first or entry
                last = entry
                prev, source = step, entry.ref
            else:
                loop = Loop(step.name, step.start, step.end, loops)
                body: list[SequenceEntry] = []
                body_first, body_last, trailing = self._add_steps(
                    step.steps, [*loops, loop], body, numbers
                )
                if body_first is None or body_last is None:
                    continue
                loop.first, loop.last = body_first.ref.number, body_last.ref.number
                out.append(loop)
                if source is not None:
                    target = GameRef(loop.first, [*indices, step.start])
                    out.append(
                        Hop(
                            "interchangeable",
                            None,
                            source,
                            target,
                            conditions=conditions,
                            loops=loops,
                        )
                    )
                out.extend(body)
                var = frog_ast.Variable(step.name)
                successor = frog_ast.BinaryOperation(
                    frog_ast.BinaryOperators.ADD, var, frog_ast.Integer(1)
                )
                out.append(
                    Hop(
                        "interchangeable",
                        None,
                        GameRef(loop.last, [*indices, var]),
                        GameRef(loop.first, [*indices, successor]),
                        conditions=trailing,
                        loops=[*loops, loop],
                        rollover=True,
                    )
                )
                prev, source = None, GameRef(loop.last, [*indices, step.end])
            conditions = []
        return first, last, conditions

    def _justify(
        self, prev: frog_ast.Step | None, step: frog_ast.Step
    ) -> tuple[str, frog_ast.Expression | None]:
        """The kind of the hop into ``step`` and what licenses it.

        A side flip from ``prev`` is licensed by an event in scope, a lemma or
        an assumption; any other hop is an interchangeability hop.
        """
        flip = self._side_flip_game(prev, step) if prev is not None else None
        if flip is None:
            return "interchangeable", None
        event = self.events_in_scope().get(str(flip))
        if event is not None:
            return "upto", event
        if self.lemma_path(flip) is not None:
            return "lemma", flip
        return "assumption", flip

    def events_in_scope(self) -> dict[str, frog_ast.EventTheorem]:
        """Assumed and lemma events keyed by ``str(pair)``, as the engine keys them.

        A side flip over such a pair is an identical-until-bad hop.
        """
        notions: list[frog_ast.Notion] = [
            *self.proof_file.assumptions,
            *(lemma.game for lemma in self.proof_file.lemmas),
        ]
        return {str(n.game): n for n in notions if isinstance(n, frog_ast.EventTheorem)}

    @staticmethod
    def _side_flip_game(
        a: frog_ast.Step, b: frog_ast.Step
    ) -> frog_ast.ParameterizedGame | None:
        """Return the shared underlying game if (a, b) is a side-flip, else None.

        Delegates to :func:`advantage.side_flip_game` so the exporter and the
        bound synthesizer agree on what counts as an indistinguishability hop.
        """
        return advantage.side_flip_game(a, b)

    def advantage_bound(self) -> advantage.AdvantageBound:
        """Synthesize the advantage bound this proof establishes.

        Assumed (and lemma) security games license loss terms; every other
        hop is a perfect equivalence. Mirrors the engine's synthesis so the
        LaTeX theorem statement and the CLI report the same bound.
        """
        assumed = {frog_ast.notion_key(a).name for a in self.proof_file.assumptions}
        assumed |= {
            frog_ast.notion_key(lemma.game).name for lemma in self.proof_file.lemmas
        }
        events = {key: e.notion() for key, e in self.events_in_scope().items()}
        return advantage.synthesize_from_steps(
            self.proof_file.steps, assumed, event_notions=events
        )
