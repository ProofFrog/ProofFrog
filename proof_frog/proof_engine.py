from __future__ import annotations
import copy
import dataclasses
import difflib
import functools
import os
import shutil
import warnings
from enum import Enum, IntEnum
from collections import namedtuple
from typing import TypeAlias, Tuple, Dict, Optional, TypeVar, Union
import z3
from colorama import Fore
from sympy import Symbol
from . import frog_ast
from . import visitors
from . import dependencies
from . import diagnostics
from .transforms._base import (
    NearMiss,
    PipelineContext,
    deduplicate_near_misses,
    run_pipeline,
    run_pipeline_until,
    run_pipeline_with_trace,
    run_standardization,
    _MAX_FIXED_POINT_ITERATIONS,
)
from .transforms.pipelines import CORE_PIPELINE, STANDARDIZATION_PIPELINE
from .transforms.assumptions import ApplyAssumptions
from .transforms.structural import (  # pylint: disable=unused-import
    remove_duplicate_fields,
)
from .transforms.standardization import (  # pylint: disable=unused-import
    standardize_field_names,
)

MethodLookup: TypeAlias = Dict[Tuple[str, str], frog_ast.Method]


class WhichGame(Enum):
    NEXT = "next"
    CURRENT = "current"


ProcessedAssumption = namedtuple("ProcessedAssumption", ["assumption", "which"])


@dataclasses.dataclass
class EquivalenceResult:
    """Result of an equivalence check between two games."""

    valid: bool
    failure_detail: str = ""
    diagnosis: diagnostics.Diagnosis | None = None


@dataclasses.dataclass
class HopResult:
    """Result of a single hop in a game-hopping proof."""

    step_num: int
    valid: bool
    kind: str
    depth: int
    current_desc: str
    next_desc: str
    failure_detail: str = ""
    diagnosis: diagnostics.Diagnosis | None = None


class FailedProof(Exception):
    pass


def serialize_diagnosis(
    diag: diagnostics.Diagnosis | None,
) -> dict[str, object] | None:
    """Serialize a Diagnosis to a JSON-compatible dict."""
    if diag is None:
        return None
    return {
        "summary": diag.summary,
        "explanations": [
            {
                "source_description": e.source_description,
                "reason": e.reason,
                "suggestion": e.suggestion,
                "engine_limitation": e.engine_limitation,
            }
            for e in diag.explanations
        ],
        "engine_limitations": diag.engine_limitations,
    }


def _build_equivalence_diff(current: frog_ast.Game, next_game: frog_ast.Game) -> str:
    """Build a human-readable diagnostic showing how two canonical games differ."""
    lines: list[str] = []

    # Compare fields
    if current.fields != next_game.fields:
        lines.append("Fields differ:")
        current_fields = [str(f) for f in current.fields]
        next_fields = [str(f) for f in next_game.fields]
        for diff_line in difflib.unified_diff(
            current_fields,
            next_fields,
            lineterm="",
            fromfile="current",
            tofile="next",
        ):
            lines.append(f"  {diff_line}")

    # Compare methods
    current_methods = {m.signature.name: m for m in current.methods}
    next_methods = {m.signature.name: m for m in next_game.methods}
    all_method_names = list(
        dict.fromkeys(list(current_methods.keys()) + list(next_methods.keys()))
    )

    differing: list[str] = []
    for name in all_method_names:
        if name not in current_methods:
            differing.append(name)
            lines.append(f"Method {name}: only in next game")
        elif name not in next_methods:
            differing.append(name)
            lines.append(f"Method {name}: only in current game")
        elif current_methods[name] != next_methods[name]:
            differing.append(name)

    if differing:
        lines.insert(0, f"Methods that differ: {', '.join(differing)}")

    # Show diff for each differing method present in both games
    for name in differing:
        if name in current_methods and name in next_methods:
            current_lines = str(current_methods[name]).splitlines()
            next_lines = str(next_methods[name]).splitlines()
            lines.append("")
            lines.append(f"--- {name} (current)")
            lines.append(f"+++ {name} (next)")
            for diff_line in difflib.unified_diff(
                current_lines,
                next_lines,
                lineterm="",
                fromfile=f"{name} (current)",
                tofile=f"{name} (next)",
                n=3,
            ):
                # Skip the --- and +++ lines since we already printed them
                if diff_line.startswith("---") or diff_line.startswith("+++"):
                    continue
                lines.append(f"  {diff_line}")

    if not lines:
        lines.append("Canonical forms differ but no specific method differences found")

    return "\n".join(lines)


def _print_failure_detail(detail: str) -> None:
    """Print failure diagnostic detail with indentation and dimmed color."""
    for line in detail.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            print(f"    {Fore.GREEN}{line}{Fore.RESET}")
        elif line.startswith("-") and not line.startswith("---"):
            print(f"    {Fore.RED}{line}{Fore.RESET}")
        elif line.startswith("@@"):
            print(f"    {Fore.CYAN}{line}{Fore.RESET}")
        else:
            print(f"    {line}")


class _AllTrueTransformer(visitors.Transformer):
    def transform_if_statement(
        self, stmt: frog_ast.IfStatement
    ) -> frog_ast.IfStatement:
        return frog_ast.IfStatement(
            [frog_ast.Boolean(True)] * len(stmt.conditions), stmt.blocks
        )


class Verbosity(IntEnum):
    """Verbosity levels for proof engine output."""

    QUIET = 0  # Default: summary table only
    NORMAL = 1  # Show intermediate games (step headers, game forms)
    VERBOSE = 2  # Show every transform applied


class ProofEngine:
    def __init__(
        self,
        verbose: bool | Verbosity = False,
        no_diagnose: bool = False,
        skip_lemmas: bool = False,
    ) -> None:
        self.definition_namespace: frog_ast.Namespace = {}
        self.proof_namespace: frog_ast.Namespace = {}
        self.proof_let_types: visitors.NameTypeMap = visitors.NameTypeMap()
        self.subsets_pairs: list[tuple[frog_ast.Type, frog_ast.Type]] = []

        if isinstance(verbose, bool):
            self.verbosity = Verbosity.VERBOSE if verbose else Verbosity.QUIET
        else:
            self.verbosity = verbose
        self.no_diagnose = no_diagnose
        self.skip_lemmas = skip_lemmas
        self.step_assumptions: list[ProcessedAssumption] = []
        self.hop_results: list[HopResult] = []
        self.variables: dict[str, Symbol | frog_ast.Expression] = {}
        self.method_lookup: MethodLookup = {}
        self.max_calls: Optional[int] = None
        self._total_steps = 0
        self._current_step = 0

    def add_definition(self, name: str, root: frog_ast.Root) -> None:
        self.definition_namespace[name] = root

    @staticmethod
    def _step_display(step: frog_ast.Step) -> str:
        """Format a step for display, omitting the adversary and semicolon."""
        if step.reduction:
            return f"{step.challenger} compose {step.reduction}"
        return str(step.challenger)

    @staticmethod
    def _count_hops(steps: list[frog_ast.ProofStep]) -> int:
        """Count the number of hops in a list of proof steps."""
        count = 0
        for i in range(len(steps) - 1):
            if isinstance(steps[i], frog_ast.StepAssumption):
                continue
            # Skip past any assumptions between this step and the next
            j = i + 1
            while j < len(steps) and isinstance(steps[j], frog_ast.StepAssumption):
                j += 1
            if j < len(steps):
                count += 1
                # If the next step is an induction, count its internal hops
                # plus the induction rollover
                next_step = steps[j]
                if isinstance(next_step, frog_ast.Induction):
                    count += ProofEngine._count_hops(next_step.steps)
                    count += 1  # induction rollover
        return count

    def prove(self, proof_file: frog_ast.ProofFile, proof_path: str = "") -> None:
        for game in proof_file.helpers:
            self.definition_namespace[game.name] = game

        # Here, we are substituting the lets with the parameters they are given
        for let in proof_file.lets:
            self.proof_let_types.set(let.name, let.type)
            if isinstance(let.value, frog_ast.FuncCall) and isinstance(
                let.value.func, frog_ast.Variable
            ):
                definition = copy.deepcopy(
                    self.definition_namespace[let.value.func.name]
                )
                # Necessary because mypy doesn't allow for union types with typevar functions
                if isinstance(definition, frog_ast.Primitive):
                    self.proof_namespace[let.name] = instantiate(
                        definition, let.value.args, self.proof_namespace
                    )
                elif isinstance(definition, frog_ast.Scheme):
                    self.proof_namespace[let.name] = instantiate(
                        definition, let.value.args, self.proof_namespace
                    )
                else:
                    raise TypeError("Must instantiate either a Primitive or Scheme ")
            else:
                self.proof_namespace[let.name] = copy.deepcopy(let.value)
                if isinstance(let.type, frog_ast.IntType):
                    if let.value is not None:
                        self.variables[let.name] = let.value
                    else:
                        sympy_symbol: Symbol = Symbol(let.name)  # type: ignore
                        self.variables[let.name] = sympy_symbol

        if proof_file.max_calls is not None:
            if isinstance(proof_file.max_calls, frog_ast.Integer):
                self.max_calls = proof_file.max_calls.num
            elif isinstance(proof_file.max_calls, frog_ast.Variable):
                val = self.variables.get(proof_file.max_calls.name)
                if isinstance(val, frog_ast.Integer):
                    self.max_calls = val.num

        self.get_method_lookup()
        self._extract_subsets_pairs()

        first_step = proof_file.steps[0]
        final_step = proof_file.steps[-1]

        assert isinstance(first_step, frog_ast.Step)
        assert isinstance(final_step, frog_ast.Step)
        assert isinstance(first_step.challenger, frog_ast.ConcreteGame)
        assert isinstance(final_step.challenger, frog_ast.ConcreteGame)

        assert isinstance(first_step.challenger, frog_ast.ConcreteGame)
        assert isinstance(final_step.challenger, frog_ast.ConcreteGame)

        if first_step.challenger.game != proof_file.theorem:
            print(
                Fore.RED
                + "Proof must start with a game matching the theorem's security game"
            )
            print(Fore.RED + f"  Theorem expects: {proof_file.theorem}")
            print(
                Fore.RED
                + f"  First step uses: {first_step.challenger.game}"
                + Fore.RESET
            )

        # Process lemmas: verify each lemma proof and add its theorem as an assumption
        effective_assumptions = list(proof_file.assumptions)
        lemma_games: set[str] = set()
        for lemma in proof_file.lemmas:
            if self.skip_lemmas:
                print(
                    f"{Fore.CYAN}Lemma: {lemma.game} "
                    f"by '{lemma.proof_path}' ... skipped{Fore.RESET}\n"
                )
                effective_assumptions.append(lemma.game)
                lemma_games.add(str(lemma.game))
                continue

            lemma_path = os.path.join(os.path.dirname(proof_path), lemma.proof_path)
            print(f"Lemma: {lemma.game} by '{lemma.proof_path}'")
            try:
                verify_proof_file(
                    lemma_path,
                    verbosity=self.verbosity,
                    no_diagnose=True,
                    skip_lemmas=self.skip_lemmas,
                )
                print(f"{Fore.GREEN}Lemma verified.{Fore.RESET}\n")
            except (FailedProof, Exception) as e:
                print(f"{Fore.RED}Lemma FAILED: {e}{Fore.RESET}")
                raise FailedProof(f"Lemma {lemma.game} failed verification") from e

            effective_assumptions.append(lemma.game)
            lemma_games.add(str(lemma.game))

        print(f"Theorem: {proof_file.theorem}\n")

        self.hop_results = []
        self._total_steps = self._count_hops(proof_file.steps)
        self._current_step = 0
        self.prove_steps(
            proof_file.steps,
            effective_assumptions,
            lemma_games=lemma_games if lemma_games else None,
        )

        print()
        self._print_summary_table()
        print()

        # Level 2: Print full diagnostics for failed hops
        if not self.no_diagnose:
            self._print_diagnostics()

        failed_steps = [r for r in self.hop_results if not r.valid]
        if failed_steps:
            step_nums = ", ".join(str(r.step_num) for r in failed_steps)
            print(
                Fore.RED
                + f"Proof Failed! ({len(failed_steps)} step(s) failed: {step_nums})"
                + Fore.RESET
            )
            raise FailedProof()

        if (
            first_step.challenger.game == final_step.challenger.game
            and first_step.challenger.which != final_step.challenger.which
            and first_step.adversary == final_step.adversary
        ):
            print(Fore.GREEN + "Proof Succeeded!" + Fore.RESET)
            return

        reasons: list[str] = []
        if first_step.challenger.game != final_step.challenger.game:
            reasons.append(
                f"first and last steps use different games "
                f"({first_step.challenger.game} vs {final_step.challenger.game})"
            )
        elif first_step.challenger.which == final_step.challenger.which:
            reasons.append(
                f"first and last steps use the same side "
                f"({first_step.challenger.which})"
            )
        if first_step.adversary != final_step.adversary:
            reasons.append(
                f"first and last steps use different adversaries "
                f"({first_step.adversary} vs {final_step.adversary})"
            )
        reason_str = "; ".join(reasons) if reasons else "unknown reason"
        print(
            Fore.YELLOW
            + f"Proof Succeeded, but is incomplete: {reason_str}"
            + Fore.RESET
        )
        raise FailedProof()

    def _print_step_status(self, hop_desc: str, result: str, color: str) -> None:
        """Print a single-line step status."""
        width = len(str(self._total_steps))
        step_str = f"Step {self._current_step:>{width}}/{self._total_steps}"
        prefix = f"  {step_str}  "
        suffix = f" ... {color}{result}{Fore.RESET}"
        line = f"{prefix}{hop_desc}{suffix}"
        terminal_width = shutil.get_terminal_size().columns
        if len(prefix) + len(hop_desc) + len(f" ... {result}") > terminal_width:
            indent = " " * len(prefix)
            hop_desc = hop_desc.replace(" -> ", f"\n{indent}-> ")
            print(f"{prefix}{hop_desc}{suffix}")
        else:
            print(line)

    def _print_summary_table(self) -> None:
        """Print a summary table of all hop results."""
        # Filter to top-level steps only
        results = [r for r in self.hop_results if r.depth == 0]
        if not results:
            return

        # Compute column widths
        step_width = max(len(str(r.step_num)) for r in results)
        step_width = max(step_width, 4)  # minimum "Step" header width

        hop_descs: list[str] = []
        for r in results:
            hop_descs.append(f"{r.current_desc} -> {r.next_desc}")

        type_labels: list[str] = []
        for r in results:
            if r.kind == "by_assumption":
                type_labels.append("assumption")
            elif r.kind == "by_lemma":
                type_labels.append("lemma")
            elif r.kind == "induction_rollover":
                type_labels.append("rollover")
            else:
                type_labels.append("equivalence")
        type_width = max(len(t) for t in type_labels)
        type_width = max(type_width, 4)  # minimum "Type" header width

        result_width = 6  # "Result" header width

        # Determine hop column width, capping to fit terminal
        terminal_width = shutil.get_terminal_size().columns
        fixed_width = 2 + step_width + 2 + 2 + type_width + 2 + result_width
        max_hop_width = max(terminal_width - fixed_width, 20)
        full_hop_width = max(len(d) for d in hop_descs)
        full_hop_width = max(full_hop_width, 3)  # minimum "Hop" header width
        needs_wrap = full_hop_width > max_hop_width
        if needs_wrap:
            # Use the max width of just the first part (before ->)
            first_parts = [d.split(" -> ", 1)[0] for d in hop_descs]
            hop_width = max(len(p) for p in first_parts)
            hop_width = max(hop_width, 3)
        else:
            hop_width = full_hop_width

        # Print table
        header = (
            f"  {'Step':>{step_width}}  "
            f"{'Hop':<{hop_width}}  "
            f"{'Type':<{type_width}}  "
            f"{'Result':<{result_width}}"
        )
        separator = (
            f"  {'-' * step_width}  "
            f"{'-' * hop_width}  "
            f"{'-' * type_width}  "
            f"{'-' * result_width}"
        )

        print(header)
        print(separator)

        hop_indent = " " * (2 + step_width + 2)
        for r, hop_desc, type_label in zip(results, hop_descs, type_labels):
            if r.kind == "by_assumption":
                result_str = Fore.CYAN + "assume" + Fore.RESET
            elif r.kind == "by_lemma":
                result_str = Fore.CYAN + "lemma" + Fore.RESET
            elif r.valid:
                result_str = Fore.GREEN + "ok" + Fore.RESET
            else:
                result_str = Fore.RED + "FAILED" + Fore.RESET

            if needs_wrap and len(hop_desc) > hop_width:
                # Split at " -> " and put continuation on next line
                parts = hop_desc.split(" -> ", 1)
                first_line = parts[0]
                print(
                    f"  {r.step_num:>{step_width}}  "
                    f"{first_line:<{hop_width}}  "
                    f"{type_label:<{type_width}}  "
                    f"{result_str}"
                )
                if len(parts) > 1:
                    print(f"{hop_indent}-> {parts[1]}")
            else:
                print(
                    f"  {r.step_num:>{step_width}}  "
                    f"{hop_desc:<{hop_width}}  "
                    f"{type_label:<{type_width}}  "
                    f"{result_str}"
                )

    def _print_failure_inline(self, equiv_result: EquivalenceResult) -> None:
        """Print Level 1 inline summary and Level 3 verbose detail for a failure."""
        if equiv_result.diagnosis is not None:
            diag = equiv_result.diagnosis
            indent = "  " + " " * (len(str(self._total_steps)) * 2 + 9)
            print(f"{indent}{Fore.YELLOW}{diag.summary}{Fore.RESET}")
        if self.verbosity >= Verbosity.VERBOSE and equiv_result.failure_detail:
            _print_failure_detail(equiv_result.failure_detail)
        if self.verbosity >= Verbosity.VERBOSE and equiv_result.diagnosis is not None:
            diag = equiv_result.diagnosis
            if diag.explanations:
                print("    Near-misses:")
                for expl in diag.explanations:
                    print(f"      - {expl.reason}")

    def _print_diagnostics(self) -> None:
        """Print Level 2 diagnostic output for failed hops."""
        failed = [
            r for r in self.hop_results if not r.valid and r.diagnosis is not None
        ]
        if not failed:
            return

        for result in failed:
            assert result.diagnosis is not None
            diag = result.diagnosis
            print()
            print(
                f"  {Fore.RED}Step {result.step_num} failed:{Fore.RESET} "
                f"{result.current_desc} -> {result.next_desc}"
            )

            for expl in diag.explanations:
                print()
                print(f"    {expl.source_description}:")
                print(f"    {Fore.YELLOW}Possible cause:{Fore.RESET} {expl.reason}")
                if expl.suggestion:
                    print(f"    {Fore.CYAN}Possible fix:{Fore.RESET} {expl.suggestion}")

            for limitation in diag.engine_limitations:
                print()
                print(
                    f"    {Fore.MAGENTA}Possible engine limitation:{Fore.RESET} "
                    f"{limitation}"
                )

    def prove_steps(
        self,
        steps: list[frog_ast.ProofStep],
        assumed_indistinguishable: list[frog_ast.ParameterizedGame],
        _depth: int = 0,
        lemma_games: set[str] | None = None,
    ) -> None:
        step_num = 0

        for i in range(0, len(steps) - 1):  # pylint: disable=too-many-nested-blocks
            assumptions: list[frog_ast.StepAssumption] = []
            if isinstance(steps[i], frog_ast.StepAssumption):
                continue

            step_num += 1
            current_step = steps[i]
            i += 1
            assumption = steps[i]
            while isinstance(assumption, frog_ast.StepAssumption):
                assumptions.append(assumption)
                i += 1
                if i >= len(steps):
                    return
                assumption = steps[i]

            next_step = steps[i]
            self._current_step += 1

            if self.verbosity >= Verbosity.NORMAL:
                print(f"===STEP {step_num}===")

            current_game_ast: frog_ast.Game
            next_game_ast: frog_ast.Game

            if isinstance(current_step, frog_ast.Step) and isinstance(
                next_step, frog_ast.Step
            ):
                if self._is_by_indistinguishability(
                    current_step, next_step, assumed_indistinguishable
                ):
                    current_desc = self._step_display(current_step)
                    next_desc = self._step_display(next_step)
                    # Determine if this hop is justified by a lemma or an axiom
                    is_lemma = (
                        lemma_games is not None
                        and isinstance(current_step.challenger, frog_ast.ConcreteGame)
                        and str(current_step.challenger.game) in lemma_games
                    )
                    hop_label = "by lemma" if is_lemma else "by assumption"
                    hop_kind = "by_lemma" if is_lemma else "by_assumption"
                    if self.verbosity >= Verbosity.NORMAL:
                        print(f"Current: {current_desc}")
                        print(f"Hop To: {next_desc}\n")
                        print(f"Valid {hop_label}")
                    hop_desc = f"{current_desc} -> {next_desc}"
                    self._print_step_status(hop_desc, hop_label, Fore.CYAN)
                    self.hop_results.append(
                        HopResult(
                            step_num=step_num,
                            valid=True,
                            kind=hop_kind,
                            depth=_depth,
                            current_desc=current_desc,
                            next_desc=next_desc,
                        )
                    )
                    continue
                current_game_ast = self._get_game_ast(
                    current_step.challenger, current_step.reduction
                )
                next_game_ast = self._get_game_ast(
                    next_step.challenger, next_step.reduction
                )
            elif isinstance(current_step, frog_ast.Step) and isinstance(
                next_step, frog_ast.Induction
            ):
                current_game_ast = self._get_game_ast(
                    current_step.challenger, current_step.reduction
                )
                first_inductive_step = next_step.steps[0]
                assert isinstance(first_inductive_step, frog_ast.Step)
                ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                ast_map.set(frog_ast.Variable(next_step.name), next_step.start)
                first_inductive_step = visitors.SubstitutionTransformer(
                    ast_map
                ).transform(first_inductive_step)
                next_game_ast = self._get_game_ast(
                    first_inductive_step.challenger, first_inductive_step.reduction
                )
                next_step = first_inductive_step
            elif isinstance(current_step, frog_ast.Induction) and isinstance(
                next_step, frog_ast.Step
            ):
                next_game_ast = self._get_game_ast(
                    next_step.challenger, next_step.reduction
                )
                last_inductive_step = next(
                    step
                    for step in current_step.steps[::-1]
                    if isinstance(step, frog_ast.Step)
                )
                assert isinstance(last_inductive_step, frog_ast.Step)
                ast_map = frog_ast.ASTMap(identity=False)
                ast_map.set(frog_ast.Variable(current_step.name), current_step.end)
                last_inductive_step = visitors.SubstitutionTransformer(
                    ast_map
                ).transform(last_inductive_step)
                current_game_ast = self._get_game_ast(
                    last_inductive_step.challenger, last_inductive_step.reduction
                )
                current_step = last_inductive_step

            assert isinstance(current_step, frog_ast.Step)
            assert isinstance(next_step, frog_ast.Step)
            current_desc = self._step_display(current_step)
            next_desc = self._step_display(next_step)

            if self.verbosity >= Verbosity.NORMAL:
                print(f"Current: {current_desc}")
                print(f"Hop To: {next_desc}\n")

            assert isinstance(current_step, frog_ast.Step)
            assert isinstance(next_step, frog_ast.Step)

            self.set_up_assumptions(assumptions, current_step, next_step)

            equiv_result = self.check_equivalent(current_game_ast, next_game_ast)
            hop_desc = f"{current_desc} -> {next_desc}"
            if equiv_result.valid:
                self._print_step_status(hop_desc, "ok", Fore.GREEN)
            else:
                self._print_step_status(hop_desc, "FAILED", Fore.RED)
                self._print_failure_inline(equiv_result)
            self.hop_results.append(
                HopResult(
                    step_num=step_num,
                    valid=equiv_result.valid,
                    kind="equivalent",
                    depth=_depth,
                    current_desc=current_desc,
                    next_desc=next_desc,
                    failure_detail=equiv_result.failure_detail,
                    diagnosis=equiv_result.diagnosis,
                )
            )
            if isinstance(steps[i], frog_ast.Induction):
                the_induction = steps[i]
                assert isinstance(the_induction, frog_ast.Induction)
                self.proof_let_types.set(the_induction.name, frog_ast.IntType())
                self.prove_steps(
                    the_induction.steps,
                    assumed_indistinguishable,
                    _depth=_depth + 1,
                    lemma_games=lemma_games,
                )
                # Check induction roll over
                first_step = the_induction.steps[0]
                assert isinstance(first_step, frog_ast.Step)
                assumptions = []
                last_step: frog_ast.Step
                for step in the_induction.steps[::-1]:
                    if isinstance(step, frog_ast.StepAssumption):
                        assumptions.append(step)
                    elif isinstance(step, frog_ast.Step):
                        last_step = step
                        break
                ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                ast_map.set(
                    frog_ast.Variable(the_induction.name),
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.ADD,
                        frog_ast.Variable(the_induction.name),
                        frog_ast.Integer(1),
                    ),
                )
                first_step = visitors.SubstitutionTransformer(ast_map).transform(
                    first_step
                )
                first_step_ast = self._get_game_ast(
                    first_step.challenger, first_step.reduction
                )
                last_step_ast = self._get_game_ast(
                    last_step.challenger, last_step.reduction
                )
                self._current_step += 1
                rollover_current_desc = self._step_display(last_step)
                rollover_next_desc = self._step_display(first_step)
                if self.verbosity >= Verbosity.NORMAL:
                    print("CHECKING INDUCTION ROLLOVER")
                    print(f"Current: {rollover_current_desc}")
                    print(f"Hop To: {rollover_next_desc}\n")
                self.set_up_assumptions(assumptions, last_step, first_step)
                rollover_result = self.check_equivalent(last_step_ast, first_step_ast)
                rollover_hop = (
                    f"[rollover] {rollover_current_desc} -> {rollover_next_desc}"
                )
                if rollover_result.valid:
                    self._print_step_status(rollover_hop, "ok", Fore.GREEN)
                else:
                    self._print_step_status(rollover_hop, "FAILED", Fore.RED)
                    self._print_failure_inline(rollover_result)
                self.hop_results.append(
                    HopResult(
                        step_num=step_num,
                        valid=rollover_result.valid,
                        kind="induction_rollover",
                        depth=_depth,
                        current_desc=rollover_current_desc,
                        next_desc=rollover_next_desc,
                        failure_detail=rollover_result.failure_detail,
                        diagnosis=rollover_result.diagnosis,
                    )
                )
                self.proof_let_types.remove(the_induction.name)

    def set_up_assumptions(
        self,
        assumptions: list[frog_ast.StepAssumption],
        current_step: frog_ast.Step,
        next_step: frog_ast.Step,
    ) -> None:
        self.step_assumptions = []
        for assumption in assumptions:
            expression = assumption.expression

            def found_field_access(
                games: tuple[
                    frog_ast.ConcreteGame | frog_ast.ParameterizedGame,
                    frog_ast.ParameterizedGame | None,
                    frog_ast.ConcreteGame | frog_ast.ParameterizedGame,
                    frog_ast.ParameterizedGame | None,
                ],
                node: frog_ast.ASTNode,
            ) -> bool:
                return (
                    isinstance(node, frog_ast.FieldAccess) and node.the_object in games
                )

            found_field_access_partial = functools.partial(
                found_field_access,
                (
                    current_step.challenger,
                    current_step.reduction,
                    next_step.challenger,
                    next_step.reduction,
                ),
            )

            assumption_field = visitors.SearchVisitor[frog_ast.FieldAccess](
                found_field_access_partial
            ).visit(expression)
            applies_to = WhichGame.CURRENT
            while assumption_field is not None:
                new_var = frog_ast.Variable(
                    get_challenger_field_name(assumption_field.name)
                    if (
                        assumption_field.the_object == current_step.challenger
                        and current_step.reduction
                    )
                    or (
                        assumption_field.the_object == next_step.challenger
                        and next_step.reduction
                    )
                    else assumption_field.name
                )
                if assumption_field.the_object in (
                    next_step.challenger,
                    next_step.reduction,
                ):
                    applies_to = WhichGame.NEXT
                expression = visitors.ReplaceTransformer(
                    assumption_field, new_var
                ).transform(expression)
                assumption_field = visitors.SearchVisitor[frog_ast.FieldAccess](
                    found_field_access_partial
                ).visit(expression)
            self.step_assumptions.append(
                ProcessedAssumption(assumption=expression, which=applies_to)
            )

    def _build_context(self) -> PipelineContext:
        return PipelineContext(
            variables=self.variables,
            proof_let_types=self.proof_let_types,
            proof_namespace=self.proof_namespace,
            subsets_pairs=self.subsets_pairs,
            sort_game_fn=self.sort_game,
            max_calls=self.max_calls,
        )

    def check_equivalent(
        self, current_game_ast: frog_ast.Game, next_game_ast: frog_ast.Game
    ) -> EquivalenceResult:
        ctx = self._build_context()
        current_near_misses: list[NearMiss] = []
        next_near_misses: list[NearMiss] = []

        for index, game in enumerate((current_game_ast, next_game_ast)):
            which = WhichGame.CURRENT if index == 0 else WhichGame.NEXT
            ctx.near_misses = []  # Reset for each game

            if self.verbosity >= Verbosity.VERBOSE:
                label = "CURRENT" if index == 0 else "NEXT"
                print(f"SIMPLIFYING {label} GAME")
                print(game)

            pipeline = list(CORE_PIPELINE) + [
                ApplyAssumptions(self.step_assumptions, which, self.proof_let_types)
            ]
            game = run_pipeline(
                game,
                pipeline,
                ctx,
                verbose=self.verbosity >= Verbosity.VERBOSE,
            )
            game = run_standardization(game, STANDARDIZATION_PIPELINE, ctx)

            if index == 0:
                current_game_ast = game
                current_near_misses = deduplicate_near_misses(ctx.near_misses)
            else:
                next_game_ast = game
                next_near_misses = deduplicate_near_misses(ctx.near_misses)

        if self.verbosity >= Verbosity.NORMAL:
            print("CURRENT")
            print(current_game_ast)
            print("NEXT")
            print(next_game_ast)

        if current_game_ast == next_game_ast:
            if self.verbosity >= Verbosity.NORMAL:
                print("Inline Success!")
            return EquivalenceResult(valid=True)

        z3_result = self._z3_conditional_equivalence(current_game_ast, next_game_ast)
        if z3_result.valid:
            return z3_result

        # Build diagnostic: combine Z3 reason with method-by-method diff
        parts: list[str] = []
        if z3_result.failure_detail:
            parts.append(z3_result.failure_detail)
        diff_text = _build_equivalence_diff(current_game_ast, next_game_ast)
        parts.append(diff_text)

        diagnosis: diagnostics.Diagnosis | None = None
        if not self.no_diagnose:
            diagnosis = diagnostics.diagnose_failure(
                diff_text, current_near_misses, next_near_misses
            )

        return EquivalenceResult(
            valid=False,
            failure_detail="\n".join(parts),
            diagnosis=diagnosis,
        )

    def _z3_conditional_equivalence(
        self,
        current_game_ast: frog_ast.Game,
        next_game_ast: frog_ast.Game,
    ) -> EquivalenceResult:
        all_true_current = _AllTrueTransformer().transform(current_game_ast)
        all_true_next = _AllTrueTransformer().transform(next_game_ast)
        if all_true_current != all_true_next:
            return EquivalenceResult(
                valid=False,
                failure_detail=(
                    "Games differ structurally (not just in if-conditions)"
                ),
            )

        found_ifs: list[frog_ast.IfStatement] = []

        def search_for_if(
            found_ifs: list[frog_ast.IfStatement], node: frog_ast.ASTNode
        ) -> bool:
            return isinstance(node, frog_ast.IfStatement) and node not in found_ifs

        while True:
            partial = functools.partial(search_for_if, found_ifs)
            if_current = visitors.SearchVisitor[frog_ast.IfStatement](partial).visit(
                current_game_ast
            )
            if_next = visitors.SearchVisitor[frog_ast.IfStatement](partial).visit(
                next_game_ast
            )
            if if_current is None or if_next is None:
                break
            found_ifs.append(if_current)
            found_ifs.append(if_next)
            for i, condition in enumerate(if_current.conditions):
                if condition == if_next.conditions[i]:
                    continue

                first_if_formula = visitors.Z3FormulaVisitor(
                    visitors.GetTypeMapVisitor(condition).visit(current_game_ast)
                    + self.proof_let_types
                ).visit(condition)
                next_if_formula = visitors.Z3FormulaVisitor(
                    visitors.GetTypeMapVisitor(if_next.conditions[i]).visit(
                        next_game_ast
                    )
                    + self.proof_let_types
                ).visit(if_next.conditions[i])
                if first_if_formula is None or next_if_formula is None:
                    return EquivalenceResult(
                        valid=False,
                        failure_detail=(
                            "Could not convert if-condition to Z3 formula: "
                            f"{condition} vs {if_next.conditions[i]}"
                        ),
                    )
                solver = z3.Solver()
                solver.set("timeout", 30000)
                solver.add(z3.Not(first_if_formula == next_if_formula))
                if solver.check() != z3.unsat:
                    return EquivalenceResult(
                        valid=False,
                        failure_detail=(
                            "Could not prove equivalence of if-conditions: "
                            f"{condition} vs {if_next.conditions[i]}"
                        ),
                    )
        if self.verbosity >= Verbosity.NORMAL:
            print("Inline Success!")
        return EquivalenceResult(valid=True)

    def canonicalize_game(self, game: frog_ast.Game) -> frog_ast.Game:
        """Apply the same simplification pipeline as check_equivalent() (without
        step-specific assumptions) and the final standardization steps, returning
        the canonical form of the game as printed by the prove command."""
        ctx = self._build_context()
        game = run_pipeline(game, CORE_PIPELINE, ctx)
        game = run_standardization(game, STANDARDIZATION_PIPELINE, ctx)
        return game

    def canonicalize_game_with_trace(
        self, game: frog_ast.Game
    ) -> tuple[frog_ast.Game, dict[str, object]]:
        """Same pipeline as canonicalize_game, but records which transforms
        fired at each iteration of the fixed-point loop."""
        ctx = self._build_context()
        game, trace = run_pipeline_with_trace(game, CORE_PIPELINE, ctx)
        game = run_standardization(game, STANDARDIZATION_PIPELINE, ctx)
        return game, {
            "iterations": [
                {
                    "iteration": it.iteration,
                    "transforms_applied": it.transforms_applied,
                }
                for it in trace.iterations
            ],
            "total_iterations": len(trace.iterations),
            "converged": trace.converged,
        }

    def canonicalize_until_transform(
        self, game: frog_ast.Game, transform_name: str
    ) -> tuple[frog_ast.Game, bool, list[str]]:
        """Apply transforms up to and including *transform_name* (first
        iteration only) and return the resulting game."""
        ctx = self._build_context()
        return run_pipeline_until(
            game, CORE_PIPELINE, STANDARDIZATION_PIPELINE, ctx, transform_name
        )

    def apply_reduction(
        self,
        challenger: frog_ast.Game,
        reduction: frog_ast.Reduction,
    ) -> frog_ast.Game:
        name = "Inlined"
        parameters = challenger.parameters
        new_fields = [
            frog_ast.Field(
                field.type, get_challenger_field_name(field.name), field.value
            )
            for field in challenger.fields
        ]
        fields = new_fields + copy.deepcopy(reduction.fields)
        phases = challenger.phases
        methods = copy.deepcopy(reduction.methods)
        reduced_game = frog_ast.Game((name, parameters, fields, methods, phases))

        if challenger.has_method("Initialize") and not reduced_game.has_method(
            "Initialize"
        ):
            reduced_game.methods.insert(0, challenger.get_method("Initialize"))
        elif challenger.has_method("Initialize"):
            # Must combine two methods together
            # Do so by inserting a challenger.Initialize() call at the beginning
            # and then using the inline transformer
            challenger_initialize = challenger.get_method("Initialize")
            reduction_initialize = reduced_game.get_method("Initialize")
            call_initialize = frog_ast.FuncCall(
                frog_ast.FieldAccess(frog_ast.Variable("challenger"), "Initialize"),
                [],
            )

            # Check if the reduction already calls challenger.Initialize()
            def _has_challenger_init_call(node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(node, frog_ast.FuncCall)
                    and isinstance(node.func, frog_ast.FieldAccess)
                    and isinstance(node.func.the_object, frog_ast.Variable)
                    and node.func.the_object.name == "challenger"
                    and node.func.name == "Initialize"
                )

            already_calls = (
                visitors.SearchVisitor(_has_challenger_init_call).visit(
                    reduction_initialize
                )
                is not None
            )

            if already_calls:
                # Reduction already calls challenger.Initialize() — just inline it
                pass
            elif isinstance(challenger_initialize.signature.return_type, frog_ast.Void):
                # Case A: Challenger returns Void — call as statement
                reduction_initialize.block = (
                    frog_ast.Block([call_initialize]) + reduction_initialize.block
                )
            elif reduction_initialize.signature.parameters:
                # Case B: Challenger returns non-Void and reduction has a
                # parameter to receive it (existing convention)
                param = reduction_initialize.signature.parameters[0]
                reduction_initialize.block = (
                    frog_ast.Block(
                        [
                            frog_ast.Assignment(
                                param.type,
                                frog_ast.Variable(param.name),
                                call_initialize,
                            )
                        ]
                    )
                    + reduction_initialize.block
                )
                reduction_initialize.signature.parameters = (
                    reduction_initialize.signature.parameters[1:]
                )
                reduction_initialize.signature.return_type = (
                    challenger_initialize.signature.return_type
                )
            else:
                # Case C: Challenger returns non-Void but reduction has no
                # parameters — assign to temp variable and discard
                reduction_initialize.block = (
                    frog_ast.Block(
                        [
                            frog_ast.Assignment(
                                copy.deepcopy(
                                    challenger_initialize.signature.return_type
                                ),
                                frog_ast.Variable("_init_result"),
                                call_initialize,
                            )
                        ]
                    )
                    + reduction_initialize.block
                )
            reduction_initialize = visitors.InlineTransformer(
                {("challenger", "Initialize"): challenger_initialize}
            ).transform(reduction_initialize)
            reduced_game.methods[0] = reduction_initialize

        return reduced_game

    # Takes in a game from a proof step, and returns the AST associated with that game
    def _get_game_ast(
        self,
        challenger: frog_ast.ParameterizedGame | frog_ast.ConcreteGame,
        reduction: Optional[frog_ast.ParameterizedGame] = None,
    ) -> frog_ast.Game:
        game: frog_ast.Game
        if isinstance(challenger, frog_ast.ConcreteGame):
            game_file = self.definition_namespace[challenger.game.name]
            assert isinstance(game_file, frog_ast.GameFile)
            game = instantiate(
                game_file.get_game(challenger.which),
                challenger.game.args,
                self.proof_namespace,
            )
        else:
            game_node = self.definition_namespace[challenger.name]
            assert isinstance(game_node, frog_ast.Game)
            game = instantiate(game_node, challenger.args, self.proof_namespace)

        lookup = copy.deepcopy(self.method_lookup)
        if reduction:
            reduction_ast = self._get_game_ast(reduction)
            assert isinstance(reduction_ast, frog_ast.Reduction)
            # Ensure independent methods list before mutation
            game = copy.copy(game)
            game.methods = list(game.methods)
            for index, method in enumerate(game.methods):
                ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                for field in game.fields:
                    ast_map.set(
                        frog_ast.Variable(field.name),
                        frog_ast.Variable(get_challenger_field_name(field.name)),
                    )
                game.methods[index] = visitors.SubstitutionTransformer(
                    ast_map
                ).transform(method)
            lookup.update(get_challenger_method_lookup(game))
            game = self.apply_reduction(game, reduction_ast)

        for _iteration in range(_MAX_FIXED_POINT_ITERATIONS):
            new_game = visitors.InlineTransformer(lookup).transform(copy.deepcopy(game))
            if game != new_game:
                game = new_game
            else:
                break
        else:
            warnings.warn(
                "Inlining did not converge within "
                f"{_MAX_FIXED_POINT_ITERATIONS} iterations",
                stacklevel=2,
            )
        return game

    def get_method_lookup(self) -> None:
        self.method_lookup = {}

        for name, node in self.proof_namespace.items():
            if isinstance(node, frog_ast.Scheme):
                rewritten = rewrite_this_in_scheme(name, copy.deepcopy(node))
                for method in rewritten.methods:
                    self.method_lookup[(name, method.signature.name)] = method

    def _extract_subsets_pairs(self) -> None:
        """Extract subsets constraint pairs from all schemes in the proof."""
        for node in self.proof_namespace.values():
            if isinstance(node, frog_ast.Scheme):
                for req in node.requirements:
                    if (
                        isinstance(req, frog_ast.BinaryOperation)
                        and req.operator == frog_ast.BinaryOperators.SUBSETS
                        and isinstance(req.left_expression, frog_ast.Type)
                        and isinstance(req.right_expression, frog_ast.Type)
                    ):
                        self.subsets_pairs.append(
                            (req.left_expression, req.right_expression)
                        )

    def _is_by_indistinguishability(
        self,
        current_step: frog_ast.Step,
        next_step: frog_ast.Step,
        assumed_indistinguishable: list[frog_ast.ParameterizedGame],
    ) -> bool:
        if not isinstance(
            current_step.challenger, frog_ast.ConcreteGame
        ) or not isinstance(next_step.challenger, frog_ast.ConcreteGame):
            return False
        return bool(
            current_step.challenger.game == next_step.challenger.game
            and current_step.adversary == next_step.adversary
            and current_step.challenger.game in assumed_indistinguishable
            and (
                not current_step.reduction
                or (
                    current_step.reduction
                    and current_step.reduction == next_step.reduction
                )
            )
        )

    def sort_game(self, game: frog_ast.Game) -> frog_ast.Game:
        new_game = copy.deepcopy(game)
        for method in new_game.methods:
            method.block = self.sort_block(game, method.block)
        return new_game

    def sort_block(self, game: frog_ast.Game, block: frog_ast.Block) -> frog_ast.Block:
        graph = dependencies.generate_dependency_graph(
            block, game.fields, self.proof_namespace
        )

        def is_return(node: frog_ast.ASTNode) -> bool:
            return node in block.statements and isinstance(
                node, frog_ast.ReturnStatement
            )

        dfs_stack: list[dependencies.Node] = []
        # Use identity-keyed visited set to handle duplicate statements
        dfs_visited_ids: set[int] = set()
        dfs_sorted_statements: list[frog_ast.Statement] = []

        def do_dfs() -> None:
            while dfs_stack:
                node = dfs_stack.pop()
                stmt_id = id(node.statement)
                if stmt_id not in dfs_visited_ids:
                    dfs_sorted_statements.append(node.statement)
                    dfs_visited_ids.add(stmt_id)
                    for neighbour in node.in_neighbours:
                        dfs_stack.append(neighbour)

        return_node = graph.find_node(is_return)
        if return_node is not None:
            dfs_stack.append(return_node)
            do_dfs()

        dfs_sorted_statements.reverse()

        for statement in block.statements:

            def uses_field(node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.Variable) and node.name in [
                    field.name for field in game.fields
                ]

            found = visitors.SearchVisitor(uses_field).visit(statement)
            if id(statement) not in dfs_visited_ids and found is not None:
                dfs_stack.append(graph.get_node(statement))
                do_dfs()

        sorted_statements: list[frog_ast.Statement] = []
        stack: list[dependencies.Node] = []

        for statement in dfs_sorted_statements:
            if not graph.get_node(statement).in_neighbours:
                stack.insert(0, graph.get_node(statement))

        while stack:
            node = stack.pop()
            sorted_statements.append(node.statement)
            for other_node in graph.nodes:
                if node in other_node.in_neighbours:
                    other_node.in_neighbours.remove(node)
                    if not other_node.in_neighbours:
                        stack.insert(0, other_node)

        return frog_ast.Block(sorted_statements)


# I want to be able to instantiate primitives and schemes
# What does this entail? For primitives, all I have are fields and
# method signatures. So I'd like to:
# 1 - Set fields to values gotten from the proof namespace
# 2 - Change method signatures: either those that rely on external values,
#     or those that refer to the fields
# 3 - For schemes, might need to change things in the method bodies.

T = TypeVar("T", bound=Union[frog_ast.Primitive, frog_ast.Scheme, frog_ast.Game])


def instantiate(
    root: T,
    args: list[frog_ast.Expression],
    namespace: frog_ast.Namespace,
) -> T:
    ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
    for index, parameter in enumerate(root.parameters):
        ast_map.set(frog_ast.Variable(parameter.name), copy.deepcopy(args[index]))
    new_root = visitors.SubstitutionTransformer(ast_map).transform(root)
    # Ensure independent copy before mutation — transform may share lists
    new_root = copy.copy(new_root)
    new_root.parameters = []
    return visitors.InstantiationTransformer(namespace).transform(new_root)


def rewrite_this_in_scheme(name: str, scheme: frog_ast.Scheme) -> frog_ast.Scheme:
    """Rewrite Variable('this') to Variable(name) in all method bodies."""
    ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
    ast_map.set(frog_ast.Variable("this"), frog_ast.Variable(name))
    for index, method in enumerate(scheme.methods):
        scheme.methods[index] = visitors.SubstitutionTransformer(ast_map).transform(
            method
        )
    return scheme


def get_challenger_method_lookup(challenger: frog_ast.Game) -> MethodLookup:
    return dict(
        zip(
            (("challenger", method.signature.name) for method in challenger.methods),
            challenger.methods,
        )
    )


def get_challenger_field_name(name: str) -> str:
    return f"challenger@{name}"


def _get_file_type_for_import(file_name: str) -> frog_ast.FileType:
    """Determine the file type from a file's extension."""
    extension = os.path.splitext(file_name)[1].strip(".")
    return frog_ast.FileType(extension)


def verify_proof_file(
    proof_path: str,
    verbosity: Verbosity = Verbosity.QUIET,
    no_diagnose: bool = True,
    skip_lemmas: bool = False,
) -> frog_ast.ProofFile:
    """Parse, load imports, and verify a proof file. Returns the ProofFile on success."""
    # pylint: disable=import-outside-toplevel,cyclic-import
    from . import frog_parser, semantic_analysis

    proof_file = frog_parser.parse_proof_file(proof_path)
    semantic_analysis.check_well_formed(proof_file, proof_path)

    engine = ProofEngine(verbosity, no_diagnose=no_diagnose, skip_lemmas=skip_lemmas)

    for imp in proof_file.imports:
        resolved = frog_parser.resolve_import_path(imp.filename, proof_path)
        file_type = _get_file_type_for_import(resolved)
        root: frog_ast.Root
        match file_type:
            case frog_ast.FileType.PRIMITIVE:
                root = frog_parser.parse_primitive_file(resolved)
            case frog_ast.FileType.SCHEME:
                root = frog_parser.parse_scheme_file(resolved)
            case frog_ast.FileType.GAME:
                root = frog_parser.parse_game_file(resolved)
            case _:
                raise FailedProof(f"Cannot import {resolved} in lemma proof")
        name = imp.rename if imp.rename else root.get_export_name()
        engine.add_definition(name, root)

    engine.prove(proof_file, proof_path)
    return proof_file
