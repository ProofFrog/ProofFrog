"""Generate concise interface descriptions of ProofFrog files.

Used by the `proof_frog describe` CLI command and the MCP server to give Claude
a compact view of what fields and methods a primitive, scheme, or game exports.
"""

from __future__ import annotations
import os

from . import frog_parser, frog_ast


def describe_file(file_path: str) -> str:
    """Return a concise interface description of any ProofFrog file.

    For primitives: exported name, parameters, fields, and method signatures.
    For schemes: same as above plus the primitive it extends and requirements.
    For game files: each game's fields and method signatures.
    For proof files: let bindings, assumptions, theorem, and game-hop sequence.

    Raises ValueError for unknown file types.
    Raises frog_parser.ParseError for files that fail to parse.
    """
    file_type_str = os.path.splitext(file_path)[1].strip(".")
    try:
        file_type = frog_ast.FileType(file_type_str)
    except ValueError as exc:
        raise ValueError(f"Unknown ProofFrog file type: .{file_type_str}") from exc

    match file_type:
        case frog_ast.FileType.PRIMITIVE:
            return _describe_primitive(frog_parser.parse_primitive_file(file_path))
        case frog_ast.FileType.SCHEME:
            return _describe_scheme(frog_parser.parse_scheme_file(file_path))
        case frog_ast.FileType.GAME:
            return _describe_game_file(frog_parser.parse_game_file(file_path))
        case frog_ast.FileType.PROOF:
            return _describe_proof_file(frog_parser.parse_proof_file(file_path))


def _describe_primitive(prim: frog_ast.Primitive) -> str:
    lines = [f"Primitive: {prim.name}"]
    if prim.parameters:
        lines.append("Parameters: " + ", ".join(str(p) for p in prim.parameters))
    if prim.fields:
        lines.append("Fields:")
        for field in prim.fields:
            lines.append(f"  {field.type} {field.name}")
    if prim.methods:
        lines.append("Methods:")
        for method in prim.methods:
            lines.append(f"  {method}")
    return "\n".join(lines)


def _describe_scheme(scheme: frog_ast.Scheme) -> str:
    lines = [f"Scheme: {scheme.name} (extends {scheme.primitive_name})"]
    if scheme.parameters:
        lines.append("Parameters: " + ", ".join(str(p) for p in scheme.parameters))
    if scheme.requirements:
        lines.append("Requirements:")
        for req in scheme.requirements:
            lines.append(f"  requires {req}")
    if scheme.fields:
        lines.append("Fields:")
        for field in scheme.fields:
            lines.append(f"  {field.type} {field.name}")
    if scheme.methods:
        lines.append("Methods (signatures only):")
        for method in scheme.methods:
            lines.append(f"  {method.signature}")
    return "\n".join(lines)


def _describe_game_file(game_file: frog_ast.GameFile) -> str:
    lines = [f"GameFile (export as: {game_file.name})"]
    for game in game_file.games:
        params_str = ", ".join(str(p) for p in game.parameters)
        lines.append(f"\nGame {game.name}({params_str}):")
        if game.fields:
            lines.append("  Fields:")
            for field in game.fields:
                lines.append(f"    {field.type} {field.name}")
        if game.methods:
            lines.append("  Methods:")
            for method in game.methods:
                lines.append(f"    {method.signature}")
        if game.phases:
            lines.append("  Phases:")
            for phase in game.phases:
                oracle_str = ", ".join(phase.oracles) if phase.oracles else ""
                lines.append(f"    oracles: [{oracle_str}]")
                for method in phase.methods:
                    lines.append(f"    {method.signature}")
    return "\n".join(lines)


def _describe_proof_file(proof: frog_ast.ProofFile) -> str:
    lines = ["Proof:"]
    if proof.lets:
        lines.append("Let:")
        for let in proof.lets:
            lines.append(f"  {let}")
    if proof.assumptions:
        lines.append("Assume:")
        for assumption in proof.assumptions:
            lines.append(f"  {assumption};")
    if proof.max_calls:
        lines.append(f"  calls <= {proof.max_calls};")
    lines.append(f"Theorem: {proof.theorem};")
    lines.append("Games:")
    for step in proof.steps:
        lines.append(f"  {step}")
    return "\n".join(lines)
