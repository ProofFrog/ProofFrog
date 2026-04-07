"""Scaffolding helpers for wizard-driven code generation in the web UI.

These functions take a (parsed) proof file and a request describing what to
generate, and return ready-to-insert FrogLang source text. They reuse the
proof engine's parser, AST, and substitution machinery so the generated
code is always semantically correct (rather than approximated via regex).
"""

import copy
from dataclasses import dataclass

from . import frog_ast, proof_engine, visitors


@dataclass
class IntermediateGameScaffold:
    block: str  # ready-to-insert Game block, ending with newline
    params_used: str  # the parameter list that was used (echoed or auto-derived)


def scaffold_intermediate_game(
    engine: proof_engine.ProofEngine,
    proof_file: frog_ast.ProofFile,
    name: str,
    params_override: str | None,
) -> IntermediateGameScaffold:
    """Generate a stub for an intermediate game in the given proof.

    The intermediate game's interface is cloned from the proof's theorem
    game (specifically its first side, e.g. ``Left``), with the theorem
    game's formal parameters substituted by the proof's theorem actual
    args via the proof engine's :func:`instantiate` helper.

    ``name`` is the user-supplied name for the new game.
    ``params_override``, if provided, replaces the auto-inferred parameter
    list. Otherwise, the parameter list defaults to the theorem's actual
    args typed via the proof's let-bindings.

    Raises ValueError when the theorem cannot be parsed or its game file
    cannot be found in the engine namespace.
    """
    theorem = proof_file.theorem
    if theorem is None:
        raise ValueError("Proof has no theorem.")
    theorem_name = theorem.name
    if theorem_name not in engine.definition_namespace:
        raise ValueError(f"Theorem game '{theorem_name}' not found in proof's imports.")
    game_file = engine.definition_namespace[theorem_name]
    if not isinstance(game_file, frog_ast.GameFile):
        raise ValueError(f"Theorem '{theorem_name}' does not refer to a game file.")
    side_game = game_file.games[0]
    # Substitute the theorem game's formal parameter names with the
    # theorem's actual args (e.g. CPA's formal `E` becomes `H`). We use
    # plain SubstitutionTransformer rather than proof_engine.instantiate
    # because the latter also runs InstantiationTransformer, which would
    # expand type aliases like `H.Ciphertext` into the underlying tuple
    # type — losing the readable scheme-qualified names we want in the
    # generated stub.
    ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
    for index, parameter in enumerate(side_game.parameters):
        if index < len(theorem.args):
            ast_map.set(
                frog_ast.Variable(parameter.name),
                copy.deepcopy(theorem.args[index]),
            )
    instantiated = visitors.SubstitutionTransformer(ast_map).transform(side_game)

    # Build the params string.
    if params_override is not None and params_override.strip() != "":
        params_used = params_override
    else:
        let_types: dict[str, frog_ast.Type] = {
            let.name: let.type for let in proof_file.lets
        }
        param_parts: list[str] = []
        for arg in theorem.args:
            if isinstance(arg, frog_ast.Variable) and arg.name in let_types:
                param_parts.append(f"{let_types[arg.name]} {arg.name}")
            else:
                param_parts.append(str(arg))
        params_used = ", ".join(param_parts)

    method_stubs: list[str] = []
    for method in instantiated.methods:
        if method.signature.name == "Initialize":
            continue
        method_stubs.append(f"    {method.signature} {{\n    }}")

    if method_stubs:
        body = "    Void Initialize() {\n    }\n\n" + "\n\n".join(method_stubs)
    else:
        body = "    Void Initialize() {\n    }"

    block = f"Game {name}({params_used}) {{\n{body}\n}}\n"
    return IntermediateGameScaffold(block=block, params_used=params_used)


@dataclass
class ReductionScaffold:
    block: str  # ready-to-insert Reduction block, ending with newline


def scaffold_reduction(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    engine: proof_engine.ProofEngine,
    proof_file: frog_ast.ProofFile,
    name: str,
    security_game_name: str,
    side: str,
    params: str,
    compose_args: str,
) -> ReductionScaffold:
    """Generate a stub for a reduction in the given proof.

    Builds a Reduction block whose oracle method stubs are cloned from the
    proof's theorem game (specifically its first side), with parameters
    substituted to match the theorem's actual args. This guarantees the
    cloned signatures use the theorem's actual scheme name (e.g. ``H``)
    rather than the security game's formal parameter name (e.g. ``E``).

    The reduction is composed against the proof's theorem game's adversary,
    so its oracle interface must match the theorem game's interface — even
    when the security game it composes happens to be the same primitive.

    ``security_game_name`` is the export name of the composed security
    game (looked up in the engine namespace), used only to render the
    ``compose ...`` clause; it does not influence the oracle signatures.
    ``side`` is the side of the security game being composed (e.g.
    ``Left``). ``params`` is the user's parameter list, inserted verbatim.
    ``compose_args`` is the argument list passed to the composed security
    game (e.g. ``"P"``); when empty, falls back to ``...``.

    Raises ValueError when required entries cannot be located.
    """
    if security_game_name not in engine.definition_namespace:
        raise ValueError(
            f"Security game '{security_game_name}' not found in proof's imports."
        )
    sec_file = engine.definition_namespace[security_game_name]
    if not isinstance(sec_file, frog_ast.GameFile):
        raise ValueError(f"'{security_game_name}' does not refer to a game file.")
    # Sanity check that the requested side exists in the security game.
    if not any(g.name == side for g in sec_file.games):
        valid = ", ".join(g.name for g in sec_file.games)
        raise ValueError(
            f"Side '{side}' not found in security game '{security_game_name}'."
            f" Available sides: {valid}."
        )

    theorem = proof_file.theorem
    if theorem is None:
        raise ValueError("Proof has no theorem.")
    theorem_name = theorem.name
    if theorem_name not in engine.definition_namespace:
        raise ValueError(f"Theorem game '{theorem_name}' not found in proof's imports.")
    theorem_game_file = engine.definition_namespace[theorem_name]
    if not isinstance(theorem_game_file, frog_ast.GameFile):
        raise ValueError(f"Theorem '{theorem_name}' does not refer to a game file.")
    theorem_side = theorem_game_file.games[0]

    # Substitute the theorem game's formal parameter names with the
    # theorem's actual args. We use plain SubstitutionTransformer rather
    # than proof_engine.instantiate to preserve scheme-qualified type
    # aliases (e.g. ``H.Ciphertext``) in the generated stub.
    ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
    for index, parameter in enumerate(theorem_side.parameters):
        if index < len(theorem.args):
            ast_map.set(
                frog_ast.Variable(parameter.name),
                copy.deepcopy(theorem.args[index]),
            )
    instantiated = visitors.SubstitutionTransformer(ast_map).transform(theorem_side)

    method_stubs: list[str] = []
    for method in instantiated.methods:
        if method.signature.name == "Initialize":
            continue
        method_stubs.append(f"    {method.signature} {{\n    }}")
    oracle_body = "\n\n".join(method_stubs)

    compose_arg_text = compose_args.strip() if compose_args else ""
    if compose_arg_text == "":
        compose_arg_text = "..."
    # Note: a Reduction's `compose ...` clause does NOT carry a side
    # (side selection happens at the use site in the games: list). The
    # `side` parameter here is metadata used for validation only.
    compose_clause = f"{security_game_name}({compose_arg_text})"

    theorem_text = str(theorem).rstrip(";").rstrip()
    against_clause = f"{theorem_text}.Adversary"

    if oracle_body:
        block = (
            f"Reduction {name}({params}) compose {compose_clause}"
            f" against {against_clause} {{\n{oracle_body}\n}}\n"
        )
    else:
        block = (
            f"Reduction {name}({params}) compose {compose_clause}"
            f" against {against_clause} {{\n}}\n"
        )
    return ReductionScaffold(block=block)


@dataclass
class ReductionHopScaffold:
    lines: list[str]  # exactly 2 lines (Side1 and Side2 compositions)


def scaffold_reduction_hop(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    engine: proof_engine.ProofEngine,
    proof_file: frog_ast.ProofFile,
    assumption_index: int,
    side1: str,
    side2: str,
    reduction_name: str,
) -> ReductionHopScaffold:
    """Generate the two new lines for an Insert Reduction Hop wizard.

    Returns the two ``<assumption_game>(<args>).<sideN> compose <reduction>
    against <theorem>.Adversary;`` lines that are inserted between the
    flanking interchangeability lines.

    ``assumption_index`` indexes into ``proof_file.assumptions``. ``side1``
    and ``side2`` are side names (e.g. ``"Real"``, ``"Random"``).
    ``reduction_name`` is the user-supplied reduction identifier (which may
    not exist as a top-level Reduction yet — that's intentional, the
    reduction can be created via the new-reduction wizard afterwards).

    Raises ValueError if ``assumption_index`` is out of range, the proof
    has no theorem, the assumption's game file cannot be located, or
    ``side1``/``side2`` don't match a side of that game.
    """
    if assumption_index < 0 or assumption_index >= len(proof_file.assumptions):
        raise ValueError(
            f"assumption_index {assumption_index} out of range "
            f"(proof has {len(proof_file.assumptions)} assumptions)."
        )
    assumption = proof_file.assumptions[assumption_index]

    theorem = proof_file.theorem
    if theorem is None:
        raise ValueError("Proof has no theorem.")

    if assumption.name not in engine.definition_namespace:
        raise ValueError(
            f"Assumption game '{assumption.name}' not found in proof's imports."
        )
    assumption_game_file = engine.definition_namespace[assumption.name]
    if not isinstance(assumption_game_file, frog_ast.GameFile):
        raise ValueError(
            f"Assumption '{assumption.name}' does not refer to a game file."
        )
    valid_sides = [g.name for g in assumption_game_file.games]
    for side_name in (side1, side2):
        if side_name not in valid_sides:
            raise ValueError(
                f"Side '{side_name}' not found in assumption game "
                f"'{assumption.name}'. Available sides: {', '.join(valid_sides)}."
            )

    assumption_text = str(assumption).rstrip(";").rstrip()
    theorem_text = str(theorem).rstrip(";").rstrip()
    against_clause = f"{theorem_text}.Adversary"

    line1 = (
        f"    {assumption_text}.{side1} compose {reduction_name}"
        f" against {against_clause};"
    )
    line2 = (
        f"    {assumption_text}.{side2} compose {reduction_name}"
        f" against {against_clause};"
    )
    return ReductionHopScaffold(lines=[line1, line2])
