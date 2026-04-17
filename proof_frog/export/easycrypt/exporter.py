"""End-to-end exporter: ProofFile path -> EasyCrypt source string."""

from __future__ import annotations

from typing import Callable

from . import ec_ast
from . import module_translator as mt
from . import proof_translator as pt
from . import tactic_generator as tgen
from . import type_collector as tc
from ... import frog_ast
from ... import frog_parser
from ... import proof_engine as pe


def _is_assumption_hop(a: frog_ast.Step, b: frog_ast.Step) -> bool:
    """Detect a hop that flips a security side under the same reduction.

    True iff both steps have the same reduction expression and reference
    different sides of the same game file.
    """
    if a.reduction is None or b.reduction is None:
        return False
    if str(a.reduction) != str(b.reduction):
        return False
    ca, cb = a.challenger, b.challenger
    if not (
        isinstance(ca, frog_ast.ConcreteGame) and isinstance(cb, frog_ast.ConcreteGame)
    ):
        return False
    return ca.game.name == cb.game.name and ca.which != cb.which


def export_proof_file(proof_path: str) -> str:
    """Parse ``proof_path`` and return the EC source as a string.

    Phase 2 scope: one primitive, one scheme, one or more game-file
    imports, zero or more reductions. Helper games, assumptions,
    lemma references, and induction are not yet supported. Every hop
    becomes one ``admit``-bodied equiv lemma.
    """
    proof = frog_parser.parse_proof_file(proof_path)

    primitive: frog_ast.Primitive | None = None
    scheme: frog_ast.Scheme | None = None
    game_files: list[frog_ast.GameFile] = []

    for imp in proof.imports:
        resolved = frog_parser.resolve_import_path(imp.filename, proof_path)
        root = frog_parser.parse_file(resolved)
        if isinstance(root, frog_ast.Primitive):
            primitive = root
        elif isinstance(root, frog_ast.Scheme):
            scheme = root
            for sub_imp in scheme.imports:
                sub_resolved = frog_parser.resolve_import_path(
                    sub_imp.filename, resolved
                )
                sub_root = frog_parser.parse_file(sub_resolved)
                if isinstance(sub_root, frog_ast.Primitive):
                    primitive = sub_root
        elif isinstance(root, frog_ast.GameFile):
            game_files.append(root)

    if primitive is None:
        raise ValueError(
            "Exporter requires a Primitive to be imported directly or "
            "transitively through a Scheme."
        )
    if scheme is None:
        raise ValueError("Exporter requires a Scheme import.")
    if not game_files:
        raise ValueError("Exporter requires at least one GameFile import.")

    aliases: dict[str, frog_ast.Type] = {}
    for sf in scheme.fields:
        if sf.value is not None and isinstance(sf.value, frog_ast.Type):
            aliases[sf.name] = sf.value
    types = tc.TypeCollector(aliases=aliases)

    method_return_types: dict[tuple[str, str], frog_ast.Type] = {}
    for prim_sig in primitive.methods:
        method_return_types[(primitive.name, prim_sig.name)] = prim_sig.return_type
    for gf in game_files:
        oracle_type = f"{gf.name}_Oracle"
        for game_method in gf.games[0].methods:
            method_return_types[(oracle_type, game_method.signature.name)] = (
                game_method.signature.return_type
            )

    def type_of_factory(
        local_types: dict[str, frog_ast.Type],
        module_param_types: dict[str, str],
    ) -> Callable[[frog_ast.Expression], frog_ast.Type]:
        def type_of(e: frog_ast.Expression) -> frog_ast.Type:
            if isinstance(e, frog_ast.Variable):
                if e.name in local_types:
                    return local_types[e.name]
                raise KeyError(f"Unknown variable type for {e.name!r}")
            if isinstance(e, frog_ast.FuncCall) and isinstance(
                e.func, frog_ast.FieldAccess
            ):
                obj = e.func.the_object
                if (
                    isinstance(obj, frog_ast.Variable)
                    and obj.name in module_param_types
                ):
                    key = (module_param_types[obj.name], e.func.name)
                    if key in method_return_types:
                        return method_return_types[key]
            raise NotImplementedError(f"type_of not implemented for {type(e).__name__}")

        return type_of

    modules = mt.ModuleTranslator(types, type_of_factory)

    ec_primitive = modules.translate_primitive(primitive)
    ec_scheme = modules.translate_scheme(scheme, primitive.name)

    ec_game_decls: list[ec_ast.EcTopDecl] = []
    oracle_type_by_game_file: dict[str, str] = {}
    module_name_by_concrete_game: dict[tuple[str, str], str] = {}
    for gf in game_files:
        oracle_type_name = f"{gf.name}_Oracle"
        oracle_type_by_game_file[gf.name] = oracle_type_name
        ec_game_decls.append(modules.translate_game_file_oracle(gf, oracle_type_name))
        for side in gf.games:
            mod_name = f"{gf.name}_{side.name}"
            module_name_by_concrete_game[(gf.name, side.name)] = mod_name
            ec_game_decls.append(
                modules.translate_game(
                    side, mod_name, primitive.name, implements=oracle_type_name
                )
            )

    ec_reductions: list[ec_ast.EcTopDecl] = []
    oracle_params_by_reduction: dict[str, list[str]] = {}
    for helper in proof.helpers:
        if not isinstance(helper, frog_ast.Reduction):
            continue
        oracle_type = oracle_type_by_game_file[helper.to_use.name]
        ec_reductions.append(
            modules.translate_reduction(helper, primitive.name, oracle_type)
        )
        if helper.methods:
            oracle_params_by_reduction[helper.name] = [
                p.name for p in helper.methods[0].signature.parameters
            ]

    oracle_name_by_game_file: dict[str, str] = {}
    oracle_params_by_game_file: dict[str, list[str]] = {}
    for gf in game_files:
        first_method = gf.games[0].methods[0]
        oracle_name_by_game_file[gf.name] = first_method.signature.name.lower()
        oracle_params_by_game_file[gf.name] = [
            p.name for p in first_method.signature.parameters
        ]
    resolver = pt.StepResolver(
        module_name_by_concrete_game=module_name_by_concrete_game,
        oracle_name_by_game_file=oracle_name_by_game_file,
        oracle_params_by_game_file=oracle_params_by_game_file,
        oracle_params_by_reduction=oracle_params_by_reduction,
        primitive_name=primitive.name,
        scheme_name=scheme.name,
    )

    # Build a ProofEngine with the same definitions used by the prove
    # command, then call prove() to populate proof_namespace and validate
    # the proof. We refuse to emit non-admit tactic scripts for a proof
    # the engine itself cannot validate.
    engine = pe.ProofEngine(verbose=False)
    for imp in proof.imports:
        resolved = frog_parser.resolve_import_path(imp.filename, proof_path)
        root = frog_parser.parse_file(resolved)
        engine.add_definition(root.get_export_name(), root)
        if isinstance(root, frog_ast.Scheme):
            for sub_imp in root.imports:
                sub_resolved = frog_parser.resolve_import_path(
                    sub_imp.filename, resolved
                )
                sub_root = frog_parser.parse_file(sub_resolved)
                engine.add_definition(sub_root.get_export_name(), sub_root)
    engine.prove(proof, proof_path)

    def _body_for_hop(
        _i: int, step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> list[str]:
        if _is_assumption_hop(step_a, step_b):
            return ["admit. (* assumption hop *)", "qed."]
        assert isinstance(step_a.challenger, frog_ast.ConcreteGame)
        method_name = oracle_name_by_game_file[step_a.challenger.game.name]
        # pylint: disable=protected-access
        left_ast = engine._get_game_ast(step_a.challenger, step_a.reduction)
        right_ast = engine._get_game_ast(step_b.challenger, step_b.reduction)
        # pylint: enable=protected-access
        _, left_trace = engine.canonicalize_game_with_trace(left_ast)
        _, right_trace = engine.canonicalize_game_with_trace(right_ast)
        return tgen.generate(
            left_trace=left_trace,
            right_trace=right_trace,
            left_ast=left_ast,
            right_ast=right_ast,
            method_name=method_name,
        )

    lemmas = pt.translate_hops(resolver, proof.steps, _body_for_hop)

    decls: list[ec_ast.EcTopDecl] = []
    decls.extend(types.emit())
    decls.append(ec_primitive)
    decls.append(ec_scheme)
    decls.extend(ec_game_decls)
    decls.extend(ec_reductions)
    decls.extend(lemmas)

    ec_file = ec_ast.EcFile(
        requires=["AllCore", "Distr"],
        decls=decls,
    )
    return ec_ast.pretty_print(ec_file)
