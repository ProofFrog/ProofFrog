"""Engine-backed resolution context for LaTeX proof export.

Owns construction of a ``ProofEngine`` from a parsed proof file and exposes
exactly the resolution the proof renderer needs, so the renderer stays
layout-only and testable against a fake context.
"""

from __future__ import annotations

from dataclasses import dataclass

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
class Hop:
    """A hop between two consecutive game steps in a proof sequence."""

    kind: str  # "interchangeable" | "assumption"
    assumption: frog_ast.Expression | None  # set when kind == "assumption"


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

    def assumptions(self) -> list[frog_ast.ParameterizedGame]:
        return list(self.proof_file.assumptions)

    def theorem(self) -> frog_ast.ParameterizedGame:
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
        for game in [*self.proof_file.assumptions, self.proof_file.theorem]:
            if isinstance(game, frog_ast.ParameterizedGame):
                names.append(game.name)
        for step in self.proof_file.steps:
            if isinstance(step, frog_ast.Step):
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
        """Return only top-level ``Step`` nodes from the proof's games list."""
        return [s for s in self.proof_file.steps if isinstance(s, frog_ast.Step)]

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
        """One Hop per transition between consecutive game steps.

        A hop is by-assumption when EITHER (a) a ``StepAssumption`` appears
        between the two game steps (cite that expression), OR (b) the two
        steps are a *side-flip*: both challengers are ``ConcreteGame``s over
        the same underlying ``ParameterizedGame`` (same name and ``str``-equal
        args) with the same reduction (``str``-equal or both None), differing
        only in ``which`` (cite that underlying game). The side-flip is the
        middle hop of the standard four-step reduction pattern and carries no
        ``StepAssumption``, so it must be detected structurally. Otherwise the
        hop is interchangeability-based.
        """
        hops: list[Hop] = []
        steps = self.proof_file.steps
        prev_game: frog_ast.Step | None = None
        pending_assumption: frog_ast.Expression | None = None
        for s in steps:
            if isinstance(s, frog_ast.StepAssumption):
                pending_assumption = s.expression
                continue
            if isinstance(s, frog_ast.Step):
                if prev_game is not None:
                    if pending_assumption is not None:
                        hops.append(Hop("assumption", pending_assumption))
                    else:
                        flip = self._side_flip_game(prev_game, s)
                        if flip is not None:
                            hops.append(Hop("assumption", flip))
                        else:
                            hops.append(Hop("interchangeable", None))
                prev_game = s
                pending_assumption = None
        return hops

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
        assumed = {a.name for a in self.proof_file.assumptions}
        assumed |= {lemma.game.name for lemma in self.proof_file.lemmas}
        return advantage.synthesize_from_steps(self.proof_file.steps, assumed)
