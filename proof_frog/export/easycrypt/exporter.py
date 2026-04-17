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
    ) -> list[str] | None:
        if _is_assumption_hop(step_a, step_b):
            return None
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

    ec_adversary_types: list[ec_ast.EcTopDecl] = []
    adv_type_name_by_game_file: dict[str, str] = {}
    for gf in game_files:
        oracle_type_name = oracle_type_by_game_file[gf.name]
        adv = modules.translate_adversary_type(gf, oracle_type_name)
        adv_type_name_by_game_file[gf.name] = adv.name
        ec_adversary_types.append(adv)

    ec_reduction_advs: list[ec_ast.EcTopDecl] = []
    outer_game_file_name = proof.theorem.name
    outer_adv_type_name = adv_type_name_by_game_file[outer_game_file_name]
    for helper in proof.helpers:
        if not isinstance(helper, frog_ast.Reduction):
            continue
        inner_oracle_type = oracle_type_by_game_file[helper.to_use.name]
        ec_reduction_advs.append(
            modules.translate_reduction_adversary(
                reduction=helper,
                outer_adversary_type_name=outer_adv_type_name,
                inner_oracle_type_name=inner_oracle_type,
                scheme_module_expr=scheme.name,
            )
        )

    ec_game_wrappers: list[ec_ast.EcTopDecl] = []
    for i, step in enumerate(proof.steps):
        if not isinstance(step, frog_ast.Step):
            raise NotImplementedError("Induction steps not supported yet.")
        resolved_step = resolver.resolve(step)
        assert isinstance(step.challenger, frog_ast.ConcreteGame)
        if step.reduction is None:
            step_game_file = step.challenger.game.name
            adv_type = adv_type_name_by_game_file[step_game_file]
        else:
            adv_type = outer_adv_type_name
        ec_game_wrappers.append(
            modules.translate_game_wrapper(
                wrapper_name=f"Game_step_{i}",
                adversary_type_name=adv_type,
                oracle_module_expr=resolved_step.module_expr,
            )
        )

    ec_assumption_wrappers: list[ec_ast.EcTopDecl] = []
    assumption_wrapper_names: dict[tuple[str, str], str] = {}
    for assumption in proof.assumptions:
        game_file_name = assumption.name
        if game_file_name not in oracle_type_by_game_file:
            continue
        adv_type = adv_type_name_by_game_file[game_file_name]
        gf = next(g for g in game_files if g.name == game_file_name)
        for side in gf.games:
            side_name = side.name
            wrapper_name = f"Game_{game_file_name}_{side_name}"
            oracle_module_expr = (
                f"{module_name_by_concrete_game[(game_file_name, side_name)]}"
                f"({scheme.name})"
            )
            ec_assumption_wrappers.append(
                modules.translate_game_wrapper(
                    wrapper_name=wrapper_name,
                    adversary_type_name=adv_type,
                    oracle_module_expr=oracle_module_expr,
                )
            )
            assumption_wrapper_names[(game_file_name, side_name)] = wrapper_name

    ec_axioms: list[ec_ast.EcTopDecl] = []
    for assumption in proof.assumptions:
        game_file_name = assumption.name
        if game_file_name not in oracle_type_by_game_file:
            continue
        adv_type = adv_type_name_by_game_file[game_file_name]
        gf = next(g for g in game_files if g.name == game_file_name)
        real_side, random_side = gf.games[0].name, gf.games[1].name
        real_wrapper = assumption_wrapper_names[(game_file_name, real_side)]
        random_wrapper = assumption_wrapper_names[(game_file_name, random_side)]
        ec_axioms.extend(
            pt.translate_assumption_axioms(
                assumption_name=game_file_name,
                adversary_type_name=adv_type,
                scheme_module_expr=scheme.name,
                real_wrapper_name=real_wrapper,
                random_wrapper_name=random_wrapper,
            )
        )

    decls: list[ec_ast.EcTopDecl] = []
    decls.extend(types.emit())
    decls.append(ec_primitive)
    decls.append(ec_scheme)
    decls.extend(ec_game_decls)
    decls.extend(ec_reductions)
    decls.extend(ec_adversary_types)
    decls.extend(ec_reduction_advs)
    decls.extend(ec_game_wrappers)
    decls.extend(ec_assumption_wrappers)
    decls.extend(ec_axioms)
    decls.extend(lemmas)

    ec_pr_lemmas: list[ec_ast.EcTopDecl] = []
    hop_kinds: list[pt.HopKind] = []
    assumption_names_by_hop: dict[int, str] = {}
    for i in range(len(proof.steps) - 1):
        step_a = proof.steps[i]
        step_b = proof.steps[i + 1]
        assert isinstance(step_a, frog_ast.Step)
        assert isinstance(step_b, frog_ast.Step)
        left_wrapper = f"Game_step_{i}"
        right_wrapper = f"Game_step_{i + 1}"
        if _is_assumption_hop(step_a, step_b):
            assert step_a.reduction is not None
            reduction_name = step_a.reduction.name
            assert isinstance(step_a.challenger, frog_ast.ConcreteGame)
            assumption_game_file_name = step_a.challenger.game.name
            hop_kinds.append(pt.HopKind.ASSUMPTION)
            assumption_names_by_hop[i] = assumption_game_file_name
            gf_a = next(g for g in game_files if g.name == assumption_game_file_name)
            left_side = step_a.challenger.which
            assert isinstance(step_b.challenger, frog_ast.ConcreteGame)
            right_side = step_b.challenger.which
            left_assumption_wrapper = assumption_wrapper_names[
                (assumption_game_file_name, left_side)
            ]
            right_assumption_wrapper = assumption_wrapper_names[
                (assumption_game_file_name, right_side)
            ]
            # The advantage axiom is stated as |Pr[side0] - Pr[side1]|;
            # if this hop goes side1 -> side0 we must normalize.
            reverse_direction = left_side == gf_a.games[1].name
            ec_pr_lemmas.append(
                pt.translate_assumption_hop_pr_lemma(
                    hop_index=i,
                    adversary_type_name=outer_adv_type_name,
                    scheme_module_expr=scheme.name,
                    left_wrapper_name=left_wrapper,
                    right_wrapper_name=right_wrapper,
                    assumption_name=assumption_game_file_name,
                    reduction_adv_name=f"{reduction_name}_Adv",
                    left_assumption_wrapper=left_assumption_wrapper,
                    right_assumption_wrapper=right_assumption_wrapper,
                    reverse_direction=reverse_direction,
                )
            )
        else:
            hop_kinds.append(pt.HopKind.INLINING)
            ec_pr_lemmas.append(
                pt.translate_inlining_hop_pr_lemma(
                    hop_index=i,
                    adversary_type_name=outer_adv_type_name,
                    scheme_module_expr=scheme.name,
                    left_wrapper_name=left_wrapper,
                    right_wrapper_name=right_wrapper,
                )
            )
    decls.extend(ec_pr_lemmas)

    n_hops = len(proof.steps) - 1
    if n_hops > 0:
        main_theorem = pt.translate_main_theorem(
            adversary_type_name=outer_adv_type_name,
            scheme_module_expr=scheme.name,
            first_wrapper_name="Game_step_0",
            last_wrapper_name=f"Game_step_{n_hops}",
            hop_kinds=hop_kinds,
            assumption_names_by_hop=assumption_names_by_hop,
            n_hops=n_hops,
        )
        decls.append(main_theorem)

    ec_file = ec_ast.EcFile(
        requires=["AllCore", "Distr"],
        decls=decls,
    )
    return ec_ast.pretty_print(ec_file)
