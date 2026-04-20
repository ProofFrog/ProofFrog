"""End-to-end exporter: ProofFile path -> EasyCrypt source string."""

from __future__ import annotations

from typing import Callable

from . import ec_ast
from . import module_translator as mt
from . import proof_translator as pt
from . import scheme_instances as si
from . import tactic_generator as tgen
from . import type_collector as tc
from ... import frog_ast
from ... import frog_parser
from ... import proof_engine as pe


def _distr_binding_for(
    distr: str,
    abstract_types_map: dict[str, str],
    concretized_fields: dict[str, frog_ast.Type],
    top_types: tc.TypeCollector,
) -> tuple[str, str] | None:
    """Compute the clone op-binding for a primitive distribution symbol.

    For a scalar concretized field, returns ``(distr, d<concrete>)``.
    For a :class:`~proof_frog.frog_ast.ProductType`, returns
    ``(distr, "d1 `*` d2 ...")`` using EC's ``dprod`` notation. Returns
    ``None`` when no binding is applicable (e.g. nested products).
    """
    abstract_type = distr[1:]
    for pf_name, abs_name in abstract_types_map.items():
        if abs_name != abstract_type or pf_name not in concretized_fields:
            continue
        concrete_field = concretized_fields[pf_name]
        if isinstance(concrete_field, frog_ast.ProductType):
            component_distrs: list[str] = []
            for sub in concrete_field.types:
                sub_ec = top_types.translate_type(sub)
                if " * " in sub_ec.text:
                    return None
                component_distrs.append(top_types.distr_for(sub_ec))
            if not component_distrs:
                return None
            return (distr, " `*` ".join(component_distrs))
        ec_concrete = top_types.translate_type(concrete_field)
        return (distr, top_types.distr_for(ec_concrete))
    return None


def _is_assumption_hop(a: frog_ast.Step, b: frog_ast.Step) -> bool:
    """Detect a hop that flips a security side under the same reduction."""
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


# pylint: disable=too-many-locals,too-many-statements,too-many-branches
def export_proof_file(proof_path: str) -> str:
    """Parse ``proof_path`` and return the EC source as a string.

    The exporter wraps the primitive + game-file interfaces inside an
    ``abstract theory`` and then emits a ``clone`` binding for the
    scheme's concrete types. Every reference to the cloned theory's
    contents (oracle types, adversary types, eps ops, advantage axiom,
    assumption-game wrappers) is qualified through the clone alias.
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

    # Collect scheme-instance descriptors. Each let-binding of the form
    # ``<Scheme> X = <Scheme>(...);`` produces one instance, which in
    # turn produces one clone of the primitive theory.
    instances = si.collect(proof, primitive, scheme)
    if not instances:
        raise ValueError(
            "Exporter requires at least one scheme instance in the proof's "
            "let block."
        )
    # "Primary" instance: the one whose scheme matches the theorem's
    # target. For OTPSecure this is ``E`` (OTP); for CES it is ``CE``
    # (ChainedEncryption). Used for scheme-body translation and as the
    # clone alias threaded through the existing single-scheme code paths.
    primary_opt: si.SchemeInstance | None = None
    for inst in instances:
        # An instance is "primary" when its let type matches scheme.name
        # and it is the last declared (so CE comes after E1/E2).
        for let in proof.lets:
            if (
                let.name == inst.let_name
                and isinstance(let.type, frog_ast.Variable)
                and let.type.name == scheme.name
            ):
                primary_opt = inst
    if primary_opt is None:
        raise ValueError(
            "No scheme instance found matching the main scheme "
            f"{scheme.name!r} in proof lets."
        )
    primary: si.SchemeInstance = primary_opt

    # ``Set X;`` let-bindings declare top-level abstract EC types
    # (``type X.``). Record their names so the TypeCollector accepts
    # bare ``Variable(X)`` type references and emits them verbatim.
    known_abstract_types: set[str] = {
        let.name
        for let in proof.lets
        if isinstance(let.type, frog_ast.SetType) and let.value is None
    }

    # Build the top-level alias map. Entries:
    #   * qualified ``"<inst>.<Field>"`` -> concretized Type (for
    #     resolving ``E1.Key`` FieldAccess types in reductions, etc.)
    #   * bare ``"<Field>"`` -> concretized Type for the primary
    #     instance (for resolving bare ``Key``/``Message`` types in
    #     the main scheme's method signatures).
    top_aliases: dict[str, frog_ast.Type] = {}
    for inst in instances:
        for fname, ftype in inst.concretized_fields.items():
            top_aliases[f"{inst.let_name}.{fname}"] = ftype
    for fname, ftype in primary.concretized_fields.items():
        top_aliases[fname] = ftype
    top_types = tc.TypeCollector(
        aliases=top_aliases, known_abstract_types=known_abstract_types
    )

    # Primitive field names that act as abstract types inside the theory.
    # For each primitive field whose value is a Type expression (e.g.
    # ``Set Key = KeySpace;``), expose an abstract EC type named by the
    # lowercase form of the FrogLang field name.
    abstract_types_map: dict[str, str] = {}
    for pf in primitive.fields:
        if isinstance(pf.value, frog_ast.Type) or pf.value is None:
            abstract_types_map[pf.name] = pf.name.lower()
    theory_types = tc.TypeCollector(abstract_types=abstract_types_map)

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

    theory_modules = mt.ModuleTranslator(theory_types, type_of_factory)
    top_modules = mt.ModuleTranslator(top_types, type_of_factory)

    # Clone alias of the primary instance; threaded through the
    # existing single-scheme code paths (assumption wrappers, game
    # wrappers, reductions, lemmas).
    clone_alias = primary.clone_alias

    # Names used across the refactor
    theory_name = f"{primitive.name}_Theory"
    scheme_type_name = "Scheme"
    scheme_param_name = "Em"  # scheme-typed module param inside theory wrappers

    # === Theory contents ===

    ec_primitive = theory_modules.translate_primitive(primitive, name=scheme_type_name)

    theory_game_decls: list[ec_ast.EcTopDecl] = []
    oracle_type_by_game_file: dict[str, str] = {}
    module_name_by_concrete_game: dict[tuple[str, str], str] = {}
    adv_type_by_game_file: dict[str, str] = {}
    for gf in game_files:
        oracle_type_name = f"{gf.name}_Oracle"
        oracle_type_by_game_file[gf.name] = oracle_type_name
        theory_game_decls.append(
            theory_modules.translate_game_file_oracle(gf, oracle_type_name)
        )
        for side in gf.games:
            mod_name = f"{gf.name}_{side.name}"
            module_name_by_concrete_game[(gf.name, side.name)] = mod_name
            theory_game_decls.append(
                theory_modules.translate_game(
                    side,
                    mod_name,
                    primitive.name,
                    implements=oracle_type_name,
                    emitted_param_type=scheme_type_name,
                )
            )
        adv = theory_modules.translate_adversary_type(gf, oracle_type_name)
        adv_type_by_game_file[gf.name] = adv.name
        theory_game_decls.append(adv)

    assumed_gf_names: set[str] = {
        a.name for a in proof.assumptions if a.name in oracle_type_by_game_file
    }

    theory_assumption_decls: list[ec_ast.EcTopDecl] = []
    assumption_wrapper_names: dict[tuple[str, str], str] = {}
    for gf in game_files:
        if gf.name not in assumed_gf_names:
            continue
        adv_type_name = adv_type_by_game_file[gf.name]
        for side in gf.games:
            wrapper_name = f"Game_{gf.name}_{side.name}"
            assumption_wrapper_names[(gf.name, side.name)] = wrapper_name
            side_mod_name = module_name_by_concrete_game[(gf.name, side.name)]
            theory_assumption_decls.append(
                theory_modules.translate_theory_game_wrapper(
                    wrapper_name=wrapper_name,
                    scheme_param_name=scheme_param_name,
                    scheme_type_name=scheme_type_name,
                    adversary_type_name=adv_type_name,
                    side_module_name=side_mod_name,
                )
            )
        real_side = gf.games[0].name
        random_side = gf.games[1].name
        theory_assumption_decls.extend(
            pt.translate_assumption_axioms_theory(
                assumption_name=gf.name,
                adversary_type_name=adv_type_name,
                scheme_type_name=scheme_type_name,
                scheme_param_name=scheme_param_name,
                real_wrapper_name=assumption_wrapper_names[(gf.name, real_side)],
                random_wrapper_name=assumption_wrapper_names[(gf.name, random_side)],
            )
        )

    # Abstract types + distributions populated during game translation above.
    theory_head = theory_types.emit_abstract()

    # === Top-level contents ===

    qualified_scheme_type = f"{clone_alias}.{scheme_type_name}"

    # For a scheme that takes module-typed parameters (e.g.
    # ``ChainedEncryption(SymEnc E1, SymEnc E2)``), emit them on the EC
    # functor. Map each scheme parameter to the clone alias of the
    # corresponding scheme instance (resolved through the primary's
    # let-binding arguments). Parameters whose type is not module-typed
    # (e.g. ``Int lambda``) are dropped — they act as abstract compile-
    # time indices and are baked into the concrete types at the clone
    # bindings.
    scheme_module_params: list[ec_ast.ModuleParam] = []
    scheme_module_param_types: dict[str, str] = {}
    instances_by_let_name = {inst.let_name: inst for inst in instances}
    primary_let = next(let for let in proof.lets if let.name == primary.let_name)
    if isinstance(primary_let.value, frog_ast.FuncCall):
        for sp, arg in zip(scheme.parameters, primary_let.value.args):
            if not isinstance(sp.type, frog_ast.Variable):
                continue
            if sp.type.name != primitive.name:
                continue
            if not isinstance(arg, frog_ast.Variable):
                continue
            inst_opt = instances_by_let_name.get(arg.name)
            if inst_opt is None:
                continue
            inst = inst_opt
            scheme_module_params.append(
                ec_ast.ModuleParam(
                    name=sp.name,
                    module_type=f"{inst.clone_alias}.{scheme_type_name}",
                )
            )
            scheme_module_param_types[sp.name] = primitive.name

    ec_scheme = top_modules.translate_scheme(
        scheme,
        qualified_scheme_type,
        module_params=scheme_module_params or None,
        module_param_types=scheme_module_param_types or None,
    )

    # Per-instance module expression. For a primitive instance
    # (``E1 = SymEnc(...)``) this is just the let-name itself (which,
    # inside the section wrap, will correspond to a ``declare module``).
    # For the scheme instance (``CE = ChainedEncryption(E1, E2)``) this
    # is the functor application ``ChainedEncryption(E1, E2)``.
    instance_module_expr: dict[str, str] = {}
    for inst in instances:
        if inst is primary and scheme_module_params:
            applied_args = ", ".join(p.name for p in scheme_module_params)
            instance_module_expr[inst.let_name] = f"{scheme.name}({applied_args})"
        elif inst is primary:
            instance_module_expr[inst.let_name] = scheme.name
        else:
            instance_module_expr[inst.let_name] = inst.let_name

    # Module expression used to apply the primary scheme wherever the
    # legacy code paths expect a single bare scheme name. For CES this
    # is ``ChainedEncryption(E1, E2)``.
    primary_module_expr = instance_module_expr[primary.let_name]

    # Adversary separation footprint. EC's ``A <: T {-X, -Y}`` modifier
    # takes one or more module names. For a single-scheme proof (OTP)
    # the footprint is the scheme module itself; for a multi-scheme
    # proof it must name the abstract instances the functor depends on
    # (``-E1, -E2``), not the functor application.
    if scheme_module_params:
        primary_footprint = ", ".join(f"-{p.name}" for p in scheme_module_params)
    else:
        primary_footprint = f"-{scheme.name}"

    # Which clone each reduction's composed assumption targets. For
    # ``R1 compose OneTimeSecrecy(E1)`` the challenger oracle lives in
    # the ``E1_c`` clone; similarly for R2/E2.
    reduction_clone_alias: dict[str, str] = {}
    for helper in proof.helpers:
        if not isinstance(helper, frog_ast.Reduction):
            continue
        target_clone = clone_alias
        if helper.to_use.args and isinstance(helper.to_use.args[0], frog_ast.Variable):
            target_inst = instances_by_let_name.get(helper.to_use.args[0].name)
            if target_inst is not None:
                target_clone = target_inst.clone_alias
        reduction_clone_alias[helper.name] = target_clone

    ec_reductions: list[ec_ast.EcTopDecl] = []
    oracle_params_by_reduction: dict[str, list[str]] = {}
    for helper in proof.helpers:
        if not isinstance(helper, frog_ast.Reduction):
            continue
        inner_oracle = oracle_type_by_game_file[helper.to_use.name]
        target_clone = reduction_clone_alias[helper.name]
        qualified_inner_oracle = f"{target_clone}.{inner_oracle}"
        # Register the qualified oracle name as a method_return_types
        # key so that type_of calls during reduction-body translation
        # resolve ``challenger.<M>(...)`` through the clone-qualified
        # oracle type.
        for game_method in (
            next(g for g in game_files if g.name == helper.to_use.name).games[0].methods
        ):
            method_return_types[
                (qualified_inner_oracle, game_method.signature.name)
            ] = game_method.signature.return_type
        renames = {
            p.name: f"{p.name}m" for p in helper.parameters if p.name == clone_alias
        }
        # Per-reduction-parameter module type: match each param.name to
        # the clone of the same-named scheme instance. For OTP this is
        # a no-op; for CES it gives each of ``CE``/``E1``/``E2`` the
        # correct per-clone ``.Scheme`` type.
        per_param_mod_types: dict[str, str] = {}
        for p in helper.parameters:
            p_inst = instances_by_let_name.get(p.name)
            if p_inst is not None:
                per_param_mod_types[p.name] = f"{p_inst.clone_alias}.{scheme_type_name}"
        ec_reductions.append(
            top_modules.translate_reduction(
                helper,
                primitive_name=primitive.name,
                oracle_type_name=qualified_inner_oracle,
                emitted_primitive_type=qualified_scheme_type,
                param_renames=renames,
                param_module_types=per_param_mod_types or None,
            )
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

    # Resolver produces qualified E.<Gf>_<Side> module names so step
    # module expressions reference the cloned theory contents.
    qualified_module_names: dict[tuple[str, str], str] = {
        key: f"{clone_alias}.{name}"
        for key, name in module_name_by_concrete_game.items()
    }
    # Per-instance qualified module names. For each instance/game/side
    # combination, resolve through that instance's own clone so the
    # step module expression reads e.g. ``E1_c.OneTimeSecrecy_Real(E1)``
    # for the E1 hop and ``CE_c.OneTimeSecrecy_Real(ChainedEncryption
    # (E1, E2))`` for the outer-scheme hop.
    module_name_by_instance_game: dict[tuple[str, str, str], str] = {}
    for inst in instances:
        for (gf_name, side_name), name in module_name_by_concrete_game.items():
            module_name_by_instance_game[(inst.let_name, gf_name, side_name)] = (
                f"{inst.clone_alias}.{name}"
            )
    declared_module_names = [inst.let_name for inst in instances if inst is not primary]
    resolver = pt.StepResolver(
        module_name_by_concrete_game=qualified_module_names,
        oracle_name_by_game_file=oracle_name_by_game_file,
        oracle_params_by_game_file=oracle_params_by_game_file,
        oracle_params_by_reduction=oracle_params_by_reduction,
        primitive_name=primitive.name,
        scheme_name=primary_module_expr,
        instance_module_expr_by_let_name=instance_module_expr,
        module_name_by_instance_game=module_name_by_instance_game,
        declared_module_names=declared_module_names,
    )

    # Validate proof via the engine (same as before).
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
        multi = step_a.reduction is not None or step_b.reduction is not None
        return tgen.generate(
            left_trace=left_trace,
            right_trace=right_trace,
            left_ast=left_ast,
            right_ast=right_ast,
            method_name=method_name,
            has_multi_module=multi and len(instances) > 1,
        )

    lemmas = pt.translate_hops(resolver, proof.steps, _body_for_hop)

    qualified_adv_type_by_game_file: dict[str, str] = {
        name: f"{clone_alias}.{adv}" for name, adv in adv_type_by_game_file.items()
    }
    outer_game_file_name = proof.theorem.name
    qualified_outer_adv = qualified_adv_type_by_game_file[outer_game_file_name]

    # Module params for non-primary instances used as ``declare module``
    # inside the section. Reduction-adversary wrappers need these as
    # explicit parameters so EC doesn't complain about depending on
    # declared modules.
    declared_instance_params: list[ec_ast.ModuleParam] = [
        ec_ast.ModuleParam(
            name=inst.let_name,
            module_type=f"{inst.clone_alias}.{scheme_type_name}",
        )
        for inst in instances
        if inst is not primary
    ]

    ec_reduction_advs: list[ec_ast.EcTopDecl] = []
    for helper in proof.helpers:
        if not isinstance(helper, frog_ast.Reduction):
            continue
        inner_oracle = oracle_type_by_game_file[helper.to_use.name]
        target_clone = reduction_clone_alias[helper.name]
        # Each reduction-arg position gets the module expression for
        # the instance of that name — e.g. R1's parameter list
        # ``(CE, E1, E2)`` maps to
        # ``[ChainedEncryption(E1, E2), E1, E2]``.
        red_arg_exprs = [
            instance_module_expr.get(p.name, p.name) for p in helper.parameters
        ]
        ec_reduction_advs.append(
            top_modules.translate_reduction_adversary(
                reduction=helper,
                outer_adversary_type_name=qualified_outer_adv,
                inner_oracle_type_name=f"{target_clone}.{inner_oracle}",
                scheme_module_expr=primary_module_expr,
                reduction_arg_exprs=red_arg_exprs,
                extra_module_params=declared_instance_params or None,
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
            adv_type = qualified_adv_type_by_game_file[step_game_file]
        else:
            adv_type = qualified_outer_adv
        ec_game_wrappers.append(
            top_modules.translate_game_wrapper(
                wrapper_name=f"Game_step_{i}",
                adversary_type_name=adv_type,
                oracle_module_expr=resolved_step.module_expr,
                extra_module_params=declared_instance_params or None,
            )
        )

    ec_pr_lemmas: list[ec_ast.EcTopDecl] = []
    hop_kinds: list[pt.HopKind] = []
    assumption_names_by_hop: dict[int, str] = {}
    assumption_clone_by_hop: dict[int, str] = {}
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
            # Per-hop clone target: which instance's advantage axiom
            # bounds this hop. For a reduction ``R1 compose
            # OneTimeSecrecy(E1)`` hop this is ``E1_c``.
            hop_clone = reduction_clone_alias.get(reduction_name, clone_alias)
            assumption_clone_by_hop[i] = hop_clone
            # The scheme argument to the assumption wrapper is the
            # module expression for the instance that ``R1`` argues
            # about. E.g. for hop on ``E1``, pass the module ``E1`` to
            # ``E1_c.Game_OneTimeSecrecy_Real``.
            assumption_target_let = (
                step_a.challenger.game.args[0].name
                if step_a.challenger.game.args
                and isinstance(step_a.challenger.game.args[0], frog_ast.Variable)
                else primary.let_name
            )
            assumption_scheme_expr = instance_module_expr.get(
                assumption_target_let, primary_module_expr
            )
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
            reverse_direction = left_side == gf_a.games[1].name
            ec_pr_lemmas.append(
                pt.translate_assumption_hop_pr_lemma(
                    hop_index=i,
                    adversary_type_name=qualified_outer_adv,
                    scheme_module_expr=assumption_scheme_expr,
                    left_wrapper_name=left_wrapper,
                    right_wrapper_name=right_wrapper,
                    assumption_name=assumption_game_file_name,
                    reduction_adv_name=f"{reduction_name}_Adv",
                    left_assumption_wrapper=left_assumption_wrapper,
                    right_assumption_wrapper=right_assumption_wrapper,
                    reverse_direction=reverse_direction,
                    clone_alias=hop_clone,
                    scheme_footprint=primary_footprint,
                    reduction_adv_extra_args=[p.name for p in declared_instance_params]
                    or None,
                    wrapper_extra_args=[p.name for p in declared_instance_params]
                    or None,
                )
            )
        else:
            hop_kinds.append(pt.HopKind.INLINING)
            ec_pr_lemmas.append(
                pt.translate_inlining_hop_pr_lemma(
                    hop_index=i,
                    adversary_type_name=qualified_outer_adv,
                    scheme_module_expr=primary_module_expr,
                    left_wrapper_name=left_wrapper,
                    right_wrapper_name=right_wrapper,
                    scheme_footprint=primary_footprint,
                    wrapper_extra_args=[p.name for p in declared_instance_params]
                    or None,
                )
            )

    # === Assemble the file ===

    # Build one clone per scheme instance. For each instance, every
    # primitive abstract type (``message``/``key``/``ciphertext``)
    # binds to the instance's concretized field type at the top level.
    def _instance_clone(inst: si.SchemeInstance) -> ec_ast.Clone:
        type_bindings_: list[tuple[str, str]] = []
        for pf_name, abs_name in abstract_types_map.items():
            if pf_name in inst.concretized_fields:
                ec_concrete = top_types.translate_type(inst.concretized_fields[pf_name])
                type_bindings_.append((abs_name, ec_concrete.text))
        op_bindings_: list[tuple[str, str]] = []
        for distr in theory_types.abstract_distrs_seen:
            binding = _distr_binding_for(
                distr, abstract_types_map, inst.concretized_fields, top_types
            )
            if binding is not None:
                op_bindings_.append(binding)
        return ec_ast.Clone(
            source_theory=theory_name,
            alias=inst.clone_alias,
            type_bindings=type_bindings_,
            op_bindings=op_bindings_,
        )

    theory = ec_ast.AbstractTheory(
        name=theory_name,
        decls=[
            *theory_head,
            ec_primitive,
            *theory_game_decls,
            *theory_assumption_decls,
        ],
    )

    clones: list[ec_ast.EcTopDecl] = [_instance_clone(inst) for inst in instances]

    # Process ``requires`` clauses to discover type equalities.
    # ``requires E2.Key subsets E1.Message`` implies that the
    # abstract types bound to those fields are equal; emit one as
    # a type alias of the other so EC sees them as the same type.
    type_aliases: dict[str, str] = {}  # alias_name -> canonical_name
    if scheme.requirements:
        param_to_let: dict[str, str] = {}
        if isinstance(primary_let.value, frog_ast.FuncCall):
            for sp, arg in zip(scheme.parameters, primary_let.value.args):
                if isinstance(arg, frog_ast.Variable):
                    param_to_let[sp.name] = arg.name
        for req in scheme.requirements:
            if not (
                isinstance(req, frog_ast.BinaryOperation)
                and req.operator == frog_ast.BinaryOperators.SUBSETS
            ):
                continue
            lhs, rhs = req.left_expression, req.right_expression
            names: list[str] = []
            req_side: frog_ast.Expression
            for req_side in (lhs, rhs):
                if not (
                    isinstance(req_side, frog_ast.FieldAccess)
                    and isinstance(req_side.the_object, frog_ast.Variable)
                ):
                    break
                param_name = req_side.the_object.name
                field_name = req_side.name
                let_name = param_to_let.get(param_name, param_name)
                found_inst = instances_by_let_name.get(let_name)
                if found_inst is None:
                    break
                resolved_field = found_inst.concretized_fields.get(field_name)
                if resolved_field is None or not isinstance(
                    resolved_field, frog_ast.Variable
                ):
                    break
                names.append(resolved_field.name)
            if len(names) == 2 and names[0] != names[1]:
                set_let_order = [
                    let.name
                    for let in proof.lets
                    if isinstance(let.type, frog_ast.SetType) and let.value is None
                ]
                idx0 = (
                    set_let_order.index(names[0])
                    if names[0] in set_let_order
                    else len(set_let_order)
                )
                idx1 = (
                    set_let_order.index(names[1])
                    if names[1] in set_let_order
                    else len(set_let_order)
                )
                if idx0 < idx1:
                    type_aliases[names[1]] = names[0]
                else:
                    type_aliases[names[0]] = names[1]

    # Abstract-set let-bindings (e.g. ``Set KeySpace1;``) emit as
    # top-level EC type declarations before any clone that may bind
    # scheme instances to them. Types unified by ``requires`` clauses
    # emit as aliases (``type X = Y.``) instead of abstract types.
    set_let_decls: list[ec_ast.EcTopDecl] = []
    for let in proof.lets:
        if isinstance(let.type, frog_ast.SetType) and let.value is None:
            if let.name in type_aliases:
                set_let_decls.append(
                    ec_ast.TypeDecl(let.name, definition=type_aliases[let.name])
                )
            else:
                set_let_decls.append(ec_ast.TypeDecl(let.name))

    # Non-primary primitive instances become ``declare module`` names
    # inside a ``section Main``. For CES this yields
    # ``declare module E1 <: E1_c.Scheme.`` and ``E2 <: E2_c.Scheme.``.
    declare_modules: list[ec_ast.DeclareModule] = []
    for inst in instances:
        if inst is primary:
            continue
        disjoint = [d.name for d in declare_modules]
        declare_modules.append(
            ec_ast.DeclareModule(
                name=inst.let_name,
                module_type=f"{inst.clone_alias}.{scheme_type_name}",
                disjoint_from=disjoint,
            )
        )

    n_hops = len(proof.steps) - 1
    main_theorem: ec_ast.ProbLemma | None = None
    if n_hops > 0:
        main_theorem = pt.translate_main_theorem(
            adversary_type_name=qualified_outer_adv,
            scheme_module_expr=primary_module_expr,
            first_wrapper_name="Game_step_0",
            last_wrapper_name=f"Game_step_{n_hops}",
            hop_kinds=hop_kinds,
            assumption_names_by_hop=assumption_names_by_hop,
            n_hops=n_hops,
            clone_alias=clone_alias,
            assumption_clone_by_hop=assumption_clone_by_hop,
            scheme_footprint=primary_footprint,
            wrapper_extra_args=[p.name for p in declared_instance_params] or None,
        )

    proof_decls: list[ec_ast.EcTopDecl] = []
    proof_decls.extend(ec_reductions)
    proof_decls.extend(ec_reduction_advs)
    proof_decls.extend(ec_game_wrappers)
    proof_decls.extend(lemmas)
    proof_decls.extend(ec_pr_lemmas)
    if main_theorem is not None:
        proof_decls.append(main_theorem)

    decls: list[ec_ast.EcTopDecl] = []
    # Abstract type declarations (e.g. ``type CiphertextSpace1.``)
    # must precede any op declarations that reference them (e.g. the
    # ``dCiphertextSpace1 : CiphertextSpace1 distr`` that ``top_types.
    # emit()`` produces).
    decls.extend(set_let_decls)
    decls.extend(top_types.emit())
    decls.append(theory)
    decls.extend(clones)
    if scheme.requirements:
        decls.append(
            "(* NOTE: the FrogLang scheme has `requires` clauses that are "
            "not enforced by the EC export. The scheme module below may "
            "fail EC type-checking because cross-clone type equalities "
            "implied by the `requires` are not expressed in the clones. "
            "Deferred to Phase 5D. *)"
        )
    decls.append(ec_scheme)
    if declare_modules:
        decls.append(
            ec_ast.Section(
                name="Main",
                decls=[*declare_modules, *proof_decls],
            )
        )
    else:
        decls.extend(proof_decls)

    ec_file = ec_ast.EcFile(
        requires=["AllCore", "Distr"],
        decls=decls,
    )
    return ec_ast.pretty_print(ec_file)
