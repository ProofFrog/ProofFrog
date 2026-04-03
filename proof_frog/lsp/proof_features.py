"""Proof verification integration for ProofFrog LSP.

Provides code lens annotations on game hops and a custom LSP request
for the proof hops tree view in VSCode.
"""

# pylint: disable=duplicate-code
# (shares structural patterns with web_server._capture_prove)

from __future__ import annotations

import io
import os
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass

from lsprotocol import types as lsp  # type: ignore[import-untyped]

from proof_frog import frog_ast, frog_parser, proof_engine, semantic_analysis
from proof_frog.lsp.diagnostics import _parse_error_location
from proof_frog.lsp.document_state import DocumentState


@dataclass
class ProofStepResult:
    """Result for a single hop in a proof, for tree view and code lens."""

    step_num: int
    valid: bool | None  # None = assumption (not checked)
    kind: str  # "equivalent", "by_assumption", etc.
    current_desc: str
    next_desc: str
    line: int  # 1-based line number in the .proof file


def run_proof_verification(state: DocumentState) -> tuple[
    list[lsp.Diagnostic],
    list[ProofStepResult],
]:
    """Run proof verification on a .proof file and return diagnostics + step results."""
    diagnostics: list[lsp.Diagnostic] = []
    step_results: list[ProofStepResult] = []

    if state.file_type != frog_ast.FileType.PROOF:
        return diagnostics, step_results

    file_path = state.file_path
    if not os.path.isfile(file_path):
        return diagnostics, step_results

    # Parse
    try:
        proof_file = frog_parser.parse_proof_file(file_path)
    except (frog_parser.ParseError, FileNotFoundError) as e:
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=0),
                ),
                message=str(e),
                severity=lsp.DiagnosticSeverity.Error,
                source="prooffrog",
            )
        )
        return diagnostics, step_results

    # Semantic analysis
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            semantic_analysis.check_well_formed(proof_file, file_path)
    except semantic_analysis.FailedTypeCheck:
        msg = buf.getvalue().strip() or "Type check failed."
        line, col, text = _parse_error_location(msg)
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=line, character=col),
                    end=lsp.Position(line=line, character=999),
                ),
                message=text,
                severity=lsp.DiagnosticSeverity.Error,
                source="prooffrog",
            )
        )
        return diagnostics, step_results
    except Exception as e:  # pylint: disable=broad-exception-caught
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=999),
                ),
                message=f"Semantic analysis error: {e}",
                severity=lsp.DiagnosticSeverity.Error,
                source="prooffrog",
            )
        )
        return diagnostics, step_results

    # Load imports into engine
    engine = proof_engine.ProofEngine(False)
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            for imp in proof_file.imports:
                imp_path = frog_parser.resolve_import_path(imp.filename, file_path)
                parsed = frog_parser.parse_file(imp_path)
                name = imp.rename if imp.rename else parsed.get_export_name()
                engine.add_definition(name, parsed)
    except (frog_parser.ParseError, FileNotFoundError, ValueError) as e:
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=0),
                ),
                message=f"Import error: {e}",
                severity=lsp.DiagnosticSeverity.Error,
                source="prooffrog",
            )
        )
        return diagnostics, step_results

    # Run proof verification
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            engine.prove(proof_file, file_path)
    except proof_engine.FailedProof:
        pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=0),
                ),
                message=f"Proof engine error: {e}",
                severity=lsp.DiagnosticSeverity.Error,
                source="prooffrog",
            )
        )
        return diagnostics, step_results

    # Build step-to-line mapping from the AST
    step_lines = _build_step_line_map(proof_file.steps)

    # Convert hop results to step results and diagnostics
    for hop in engine.hop_results:
        if hop.depth != 0 or hop.kind == "induction_rollover":
            continue

        line = step_lines.get(hop.step_num, 1)

        step_results.append(
            ProofStepResult(
                step_num=hop.step_num,
                valid=hop.valid if hop.kind != "by_assumption" else None,
                kind=hop.kind,
                current_desc=hop.current_desc,
                next_desc=hop.next_desc,
                line=line,
            )
        )

        # Create diagnostic for failed hops
        if not hop.valid and hop.kind != "by_assumption":
            msg = (
                f"Hop {hop.step_num} failed: " f"{hop.current_desc} -> {hop.next_desc}"
            )
            if hop.failure_detail:
                msg += f"\n{hop.failure_detail}"
            diagnostics.append(
                lsp.Diagnostic(
                    range=lsp.Range(
                        start=lsp.Position(line=max(0, line - 1), character=0),
                        end=lsp.Position(line=max(0, line - 1), character=999),
                    ),
                    message=msg,
                    severity=lsp.DiagnosticSeverity.Error,
                    source="prooffrog-prove",
                )
            )

    return diagnostics, step_results


def _build_step_line_map(
    steps: list[frog_ast.ProofStep], offset: int = 0
) -> dict[int, int]:
    """Map step numbers (1-based) to line numbers in the source file."""
    result: dict[int, int] = {}
    step_num = offset
    for step in steps:
        if isinstance(step, frog_ast.Step):
            step_num += 1
            if step.line_num >= 1:
                result[step_num] = step.line_num
        elif isinstance(step, frog_ast.StepAssumption):
            # Assumptions don't increment step_num in the engine
            pass
        elif isinstance(step, frog_ast.Induction):
            # Induction contains sub-steps
            sub_map = _build_step_line_map(step.steps, step_num)
            result.update(sub_map)
            step_num = max(sub_map.keys()) if sub_map else step_num
    return result


def build_code_lenses(
    _state: DocumentState, step_results: list[ProofStepResult]
) -> list[lsp.CodeLens]:
    """Build code lenses for proof hop results."""
    lenses: list[lsp.CodeLens] = []
    for result in step_results:
        line = max(0, result.line - 1)  # Convert to 0-based

        if result.valid is None:
            # Assumption hop
            title = f"  assumption ({result.kind})"
        elif result.valid:
            title = "  interchangeability"
        else:
            title = "  interchangeability -- FAILED"

        lenses.append(
            lsp.CodeLens(
                range=lsp.Range(
                    start=lsp.Position(line=line, character=0),
                    end=lsp.Position(line=line, character=0),
                ),
                command=lsp.Command(
                    title=title,
                    command="prooffrog.showHopDetail",
                    arguments=[
                        {
                            "step_num": result.step_num,
                            "valid": result.valid,
                            "kind": result.kind,
                            "current_desc": result.current_desc,
                            "next_desc": result.next_desc,
                        }
                    ],
                ),
            )
        )
    return lenses


# Custom LSP notification and command
PROOF_STEPS_METHOD = "prooffrog/proofSteps"
PROOF_VERIFICATION_DONE = "prooffrog/verificationDone"


def get_proof_steps_response(
    step_results: list[ProofStepResult],
) -> list[dict[str, object]]:
    """Build the response for the prooffrog/proofSteps custom request."""
    return [
        {
            "step_num": r.step_num,
            "valid": r.valid,
            "kind": r.kind,
            "current_desc": r.current_desc,
            "next_desc": r.next_desc,
            "line": r.line,
        }
        for r in step_results
    ]
