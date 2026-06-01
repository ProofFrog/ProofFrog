"""End-to-end exporter: ProofFile path -> EasyCrypt source string."""

from __future__ import annotations

import copy
import pathlib
from dataclasses import dataclass
from typing import Callable

from . import canonical_form
from . import ec_ast
from . import module_translator as mt
from . import proof_translator as pt
from . import scheme_instances as si
from . import type_collector as tc
from .resolution import ADMIT_GUIDED, ADMIT_UNGUIDED, CACHED_GUIDED
from .resolution import tag as _res_tag
from ... import frog_ast
from ... import frog_parser
from ... import proof_engine as pe
from ... import visitors


class _LengthInliner(visitors.Transformer):
    """Substitute integer field/param references in bitstring lengths with
    base-resolved expressions.

    The substitution is one-shot: ``transform_variable`` /
    ``transform_field_access`` return the replacement directly, and the base
    :class:`Transformer` does not re-visit a returned node. This is what keeps
    ``G.lambda -> lambda`` terminal -- the produced base ``lambda`` is never
    re-expanded by a same-named primary-scheme field equation (the bug that
    made one length acquire several distinct ``bs_*`` names).
    """

    def __init__(
        self,
        bare: dict[str, frog_ast.ASTNode],
        qualified: dict[str, frog_ast.ASTNode],
    ) -> None:
        self._bare = bare
        self._qualified = qualified

    def transform_variable(self, variable: frog_ast.Variable) -> frog_ast.ASTNode:
        if variable.name in self._bare:
            return copy.deepcopy(self._bare[variable.name])
        return variable

    def transform_field_access(
        self, field_access: frog_ast.FieldAccess
    ) -> frog_ast.ASTNode:
        if isinstance(field_access.the_object, frog_ast.Variable):
            key = f"{field_access.the_object.name}.{field_access.name}"
            if key in self._qualified:
                return copy.deepcopy(self._qualified[key])
        return field_access


def _base_int_length_map(
    proof: frog_ast.ProofFile,
    primitives_by_name: dict[str, frog_ast.Primitive],
    schemes_by_name: dict[str, frog_ast.Scheme],
) -> tuple[
    dict[str, frog_ast.ASTNode],
    dict[str, dict[str, frog_ast.ASTNode]],
    dict[str, dict[str, frog_ast.ASTNode]],
    dict[str, set[str]],
]:
    # pylint: disable=too-many-locals
    """Resolve every instance's integer params/fields to base ``Int`` lets.

    Returns ``(qualified, local_by_let, param_by_let, names_by_let)``:

    * ``qualified`` maps ``"<let>.<intname>"`` to a base-resolved expression.
    * ``local_by_let`` maps a let-name to its in-scope ``{intname -> base
      expr}`` (int params + int fields). Used to pre-inline a scheme *body*,
      whose bare references can be either a param or the scheme's own field.
    * ``param_by_let`` maps a let-name to its int *params* only. Used to
      base-resolve an instance's ``concretized_fields``: those length values
      reference params and foreign fields, never the instance's own bare
      field names, so re-applying the field aliases would wrongly re-expand
      an already-base symbol.
    * ``names_by_let`` maps a let-name to its set of int param/field names.

    Lets are processed in declaration order, so each instance resolves its
    field/param values through the already-resolved prior instances.
    """
    qualified: dict[str, frog_ast.ASTNode] = {}
    local_by_let: dict[str, dict[str, frog_ast.ASTNode]] = {}
    param_by_let: dict[str, dict[str, frog_ast.ASTNode]] = {}
    names_by_let: dict[str, set[str]] = {}
    for let in proof.lets:
        if not (
            isinstance(let.value, frog_ast.FuncCall)
            and isinstance(let.value.func, frog_ast.Variable)
        ):
            continue
        ctor = let.value.func.name
        defn: frog_ast.Primitive | frog_ast.Scheme | None = primitives_by_name.get(
            ctor
        ) or schemes_by_name.get(ctor)
        if defn is None:
            continue
        local: dict[str, frog_ast.ASTNode] = {}
        params_local: dict[str, frog_ast.ASTNode] = {}
        inliner = _LengthInliner(local, qualified)
        for param, arg in zip(defn.parameters, let.value.args):
            if isinstance(getattr(param, "type", None), frog_ast.IntType):
                value = inliner.transform(arg)
                local[param.name] = value
                params_local[param.name] = value
        for fld in defn.fields:
            if isinstance(fld.type, frog_ast.IntType) and fld.value is not None:
                local[fld.name] = inliner.transform(fld.value)
        local_by_let[let.name] = local
        param_by_let[let.name] = params_local
        names_by_let[let.name] = set(local.keys())
        for local_name, local_value in local.items():
            qualified[f"{let.name}.{local_name}"] = local_value
    return qualified, local_by_let, param_by_let, names_by_let


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


def _instantiate_bitstring_expr(
    expr: frog_ast.Expression,
    concretized_fields: dict[str, frog_ast.Type],
    _visited: frozenset[str] = frozenset(),
) -> frog_ast.Expression:
    """Substitute a scheme instance's concretized field values into an
    abstract bitstring parameterization expression.

    The abstract expression is post-strip (uses bare primitive field
    names like ``lambda``, ``stretch``). For each ``Variable(name)``
    encountered, if ``concretized_fields[name]`` is itself an
    ``Expression`` (the typical case for ``Int`` value fields), splice
    that value in. Otherwise leave the variable unchanged.

    Cycle-safe: a ``Variable(name)`` whose concretization is itself a
    ``Variable(name)`` (the common case for opaque let-bindings like
    ``Int lambda;`` where ``G.lambda = lambda``) is left alone rather
    than substituted into infinite regress.

    Recurses through ``BinaryOperation`` and ``UnaryOperation`` so
    expressions like ``lambda + stretch`` become ``lambda + (2 * lambda)``
    (for a TriplingPRG instance built on a length-doubling G).
    """
    if isinstance(expr, frog_ast.Variable):
        if expr.name in _visited:
            return expr
        value = concretized_fields.get(expr.name)
        if isinstance(value, frog_ast.Variable) and value.name == expr.name:
            return expr
        if isinstance(value, frog_ast.Expression):
            # Single-pass: the concretized fields are already base-resolved
            # (see ``_base_int_length_map``), so splice the value in directly.
            # Re-substituting it would let a base symbol that coincides with
            # another field name -- e.g. the ``lambda`` value of ``stretch``
            # colliding with the ``lambda`` field -- be wrongly re-expanded.
            return copy.deepcopy(value)
        return expr
    if isinstance(expr, frog_ast.BinaryOperation):
        return frog_ast.BinaryOperation(
            expr.operator,
            _instantiate_bitstring_expr(
                expr.left_expression, concretized_fields, _visited
            ),
            _instantiate_bitstring_expr(
                expr.right_expression, concretized_fields, _visited
            ),
        )
    if isinstance(expr, frog_ast.UnaryOperation):
        return frog_ast.UnaryOperation(
            expr.operator,
            _instantiate_bitstring_expr(expr.expression, concretized_fields, _visited),
        )
    return expr


def _ec_ident(s: str) -> str:
    """Sanitize a FrogLang name for use as an EC identifier.

    Replaces any character outside ``[A-Za-z0-9_]`` with ``_`` so that
    game-file names containing ``$`` (e.g. ``INDOT$``) or other punctuation
    yield valid EC names (``INDOT__Oracle``, ``eps_INDOT_`` etc.). The
    mapping is deterministic and injective for the names that actually
    appear in the corpus.
    """
    import re  # pylint: disable=import-outside-toplevel

    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def _section_header(label: str) -> str:
    """Render a top-level section divider comment.

    Inserted as a bare-string ``EcTopDecl`` (the pretty-printer renders
    such elements verbatim) to break the generated EC file into
    visually-distinct sections.
    """
    return f"(* ===== {label} ===== *)"


def _describe_step_wrapper(index: int, step: frog_ast.Step) -> str:
    """Render the per-step description comment for a ``Game_step_<i>``."""
    if not isinstance(step.challenger, frog_ast.ConcreteGame):
        return f"(* Game_step_{index} *)"
    side = step.challenger.which
    game_file = step.challenger.game.name
    if step.reduction is None:
        return f"(* Game_step_{index}: {game_file}.{side} *)"
    return (
        f"(* Game_step_{index}: {game_file}.{side} composed with "
        f"reduction {step.reduction.name} *)"
    )


def _describe_inlining_hop(index: int) -> str:
    """Render the comment introducing an interchangeability hop's Pr lemma."""
    return (
        f"(* Hop {index}: interchangeability. The two adjacent games are "
        f"equivalent (no advantage). *)"
    )


def _describe_assumption_hop(
    index: int, assumption_name: str, reduction_name: str
) -> str:
    """Render the comment introducing an assumption hop's Pr lemma."""
    return (
        f"(* Hop {index}: assumption hop. Bounded by the "
        f"{assumption_name}_advantage axiom applied to "
        f"{reduction_name}_Adv. *)"
    )


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


def _scheme_functor_params(
    scheme: frog_ast.Scheme,
    let_value: frog_ast.Expression | None,
    instances_by_let_name: "dict[str, si.SchemeInstance]",
    scheme_type_name: str,
) -> "tuple[list[ec_ast.ModuleParam], dict[str, str], list[str]]":
    """Compute the EC functor parameters for a scheme instance.

    For a scheme taking module-typed parameters (e.g.
    ``ChainedEncryption(SymEnc E1, SymEnc E2)`` or
    ``PseudoOTP(Int, Int, PRG G)``) this returns the EC ``ModuleParam``
    list, the param-name -> primitive-type map (for the body translator),
    and the ordered list of applied argument names. Non-module parameters
    (e.g. ``Int lambda``) are dropped: they act as compile-time indices
    baked into the cloned types. Each module parameter is bound to the
    clone alias of the instance passed as the corresponding constructor
    argument.
    """
    params: list[ec_ast.ModuleParam] = []
    param_types: dict[str, str] = {}
    applied: list[str] = []
    if not isinstance(let_value, frog_ast.FuncCall):
        return params, param_types, applied
    for sp, arg in zip(scheme.parameters, let_value.args):
        if not isinstance(sp.type, frog_ast.Variable):
            continue
        if not isinstance(arg, frog_ast.Variable):
            continue
        inst_opt = instances_by_let_name.get(arg.name)
        if inst_opt is None:
            continue
        params.append(
            ec_ast.ModuleParam(
                name=sp.name,
                module_type=f"{inst_opt.clone_alias}.{scheme_type_name}",
            )
        )
        param_types[sp.name] = sp.type.name
        # The functor is *defined* with parameter name ``sp.name`` (its body
        # refers to the sub-primitive by that name); it is *applied* to the
        # argument instance ``arg.name`` (e.g. ``PseudoOTP(G)`` binds the
        # declared module ``G`` to the functor's ``G`` parameter).
        applied.append(arg.name)
    return params, param_types, applied


# pylint: disable=too-many-locals,too-many-statements,too-many-branches
def export_proof_file(proof_path: str) -> str:
    """Parse ``proof_path`` and return the EC source as a string.

    The exporter wraps the primitive + game-file interfaces inside an
    ``abstract theory`` and then emits a ``clone`` binding for the
    scheme's concrete types. Every reference to the cloned theory's
    contents (oracle types, adversary types, eps ops, advantage axiom,
    assumption-game wrappers) is qualified through the clone alias.

    Each interchangeability hop emits a chain of intermediate-state
    modules and micro-lemmas (one per ProofFrog canonicalization-
    transform application), with the equiv lemma's body discharged via
    ``transitivity`` through the chain. Reductions and assumption-hop
    axiom appeals are emitted alongside.
    """
    proof = frog_parser.parse_proof_file(proof_path)

    # Collect ALL primitives and schemes by name (directly imported or
    # reached transitively through a Scheme's own imports). The primary
    # primitive/scheme is then selected from the theorem's target instance,
    # not from import order. This matters for proofs that import auxiliary
    # schemes used only by assumption hops (e.g. 5_10 imports OTP + SymEnc
    # alongside its primary PRG_5_10/PRG, because step 4 invokes the
    # INDOT$ axiom about OTP).
    primitives_by_name: dict[str, frog_ast.Primitive] = {}
    schemes_by_name: dict[str, frog_ast.Scheme] = {}
    game_files: list[frog_ast.GameFile] = []

    for imp in proof.imports:
        resolved = frog_parser.resolve_import_path(imp.filename, proof_path)
        root = frog_parser.parse_file(resolved)
        if isinstance(root, frog_ast.Primitive):
            primitives_by_name[root.name] = root
        elif isinstance(root, frog_ast.Scheme):
            schemes_by_name[root.name] = root
            for sub_imp in root.imports:
                sub_resolved = frog_parser.resolve_import_path(
                    sub_imp.filename, resolved
                )
                sub_root = frog_parser.parse_file(sub_resolved)
                if isinstance(sub_root, frog_ast.Primitive):
                    primitives_by_name[sub_root.name] = sub_root
        elif isinstance(root, frog_ast.GameFile):
            game_files.append(root)

    if not schemes_by_name:
        raise ValueError("Exporter requires a Scheme import.")
    if not game_files:
        raise ValueError("Exporter requires at least one GameFile import.")

    # The primary scheme is the one whose instance appears in the theorem.
    # For ``theorem: PRGSecurity(H)`` with ``PRG_5_10 H = PRG_5_10(G);``,
    # the primary let is H and the primary scheme is PRG_5_10.
    if not (
        isinstance(proof.theorem, frog_ast.ParameterizedGame)
        and proof.theorem.args
        and isinstance(proof.theorem.args[0], frog_ast.Variable)
    ):
        raise ValueError(
            "Exporter requires the theorem to be a ParameterizedGame whose "
            "first argument is the scheme instance under attack."
        )
    primary_let_name = proof.theorem.args[0].name
    primary_scheme_name: str | None = None
    for let in proof.lets:
        if let.name == primary_let_name and isinstance(let.type, frog_ast.Variable):
            primary_scheme_name = let.type.name
            break
    if primary_scheme_name is None or primary_scheme_name not in schemes_by_name:
        raise ValueError(
            f"Could not identify primary scheme from theorem instance "
            f"{primary_let_name!r}."
        )
    scheme = schemes_by_name[primary_scheme_name]
    if scheme.primitive_name not in primitives_by_name:
        raise ValueError(
            f"Primary scheme {scheme.name!r} extends primitive "
            f"{scheme.primitive_name!r}, which was not imported."
        )
    primitive = primitives_by_name[scheme.primitive_name]

    # Collect scheme-instance descriptors. Each let-binding of the form
    # ``<Scheme> X = <Scheme>(...);`` produces one instance, which in
    # turn produces one clone of the primitive theory.
    # ``collect_all`` walks every imported primitive/scheme so multi-
    # primitive proofs (e.g. 5_10 = PRG_5_10 + OTP) get instances for both
    # families. Each instance records its ``primitive_name`` so the
    # exporter knows which abstract theory to clone for it.
    instances = si.collect_all(proof, primitives_by_name, schemes_by_name)
    if not instances:
        raise ValueError(
            "Exporter requires at least one scheme instance in the proof's "
            "let block."
        )

    # Each game file's primitive is the type name of its first parameter
    # (e.g. ``Game Real(SymEnc E)`` → ``"SymEnc"``). Game files associated
    # with auxiliary primitives (i.e. not the primary) live in a separate
    # abstract theory.
    primitive_name_by_game_file: dict[str, str] = {}
    for gf in game_files:
        params = gf.games[0].parameters
        if not params or not isinstance(params[0].type, frog_ast.Variable):
            raise ValueError(
                f"Game file {gf.name!r}: expected first game parameter to be a "
                "primitive-typed Variable."
            )
        prim_param_name = params[0].type.name
        if prim_param_name not in primitives_by_name:
            raise ValueError(
                f"Game file {gf.name!r} references primitive {prim_param_name!r}, "
                "which was not imported."
            )
        primitive_name_by_game_file[gf.name] = prim_param_name
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

    # Foreign instances we can emit as CONCRETE EC modules (instead of an
    # abstract ``declare module``). A foreign instance qualifies when:
    #   * its constructor resolves to a concrete ``Scheme`` (so we can
    #     translate a real body), not an abstract primitive; AND
    #   * every module-typed (sub-primitive) parameter is bound to a known
    #     instance, so the scheme can be emitted as an EC functor applied to
    #     those instances.
    # A *ground* scheme (no module params, e.g. 5_10's ``P = OTP(lambda)``)
    # inlines fully to samples + XOR, so its cross-primitive wrapper-to-flat
    # bridge closes via the canned ``sim`` tactic. A *non-ground* scheme
    # (e.g. 5_8_e's ``PseudoOTP(Int, Int, PRG G)``) is emitted as a functor
    # ``module PseudoOTP (G : G_c.Scheme) : P_c.Scheme`` applied as
    # ``PseudoOTP(G)``; its body retains an abstract ``G.evaluate`` call, so
    # its cross-primitive hop needs the deterministic-method reorder cascade.
    # Those hops are routed to a *guided-template* admit (see ``_body_for_hop``)
    # — an ``admit-guided`` resolution annotated with the cascade strategy + det
    # axioms in scope, so a human/agent can fill it interactively and cache
    # the result. CES's ``E1``/``E2`` (ctor ``SymEnc``, a primitive) do NOT
    # qualify and stay abstract.
    def _module_args_resolve(inst: si.SchemeInstance) -> bool:
        scheme_def = schemes_by_name[inst.ctor_name]
        module_params = [
            sp for sp in scheme_def.parameters if isinstance(sp.type, frog_ast.Variable)
        ]
        if not module_params:
            return True
        let = next((b for b in proof.lets if b.name == inst.let_name), None)
        if let is None or not isinstance(let.value, frog_ast.FuncCall):
            return False
        known = {i.let_name for i in instances}
        resolved = sum(
            1
            for sp, arg in zip(scheme_def.parameters, let.value.args)
            if isinstance(sp.type, frog_ast.Variable)
            and isinstance(arg, frog_ast.Variable)
            and arg.name in known
        )
        return resolved == len(module_params)

    concretizable_foreign: set[str] = {
        inst.let_name
        for inst in instances
        if inst is not primary
        and inst.ctor_name in schemes_by_name
        and _module_args_resolve(inst)
    }
    # Concretized foreign instances whose scheme is *non-ground* (functor):
    # their cross-primitive hops need the deterministic reorder cascade.
    nonground_concrete: set[str] = {
        let_name
        for let_name in concretizable_foreign
        if any(
            isinstance(sp.type, frog_ast.Variable)
            for sp in schemes_by_name[
                next(i for i in instances if i.let_name == let_name).ctor_name
            ].parameters
        )
    }

    # ``Set X;`` let-bindings declare top-level abstract EC types
    # (``type X.``). Record their names so the TypeCollector accepts
    # bare ``Variable(X)`` type references and emits them verbatim.
    known_abstract_types: set[str] = {
        let.name
        for let in proof.lets
        if isinstance(let.type, frog_ast.SetType) and let.value is None
    }

    # Base-resolve every instance's bitstring lengths to the proof's base
    # ``Int`` lets BEFORE building aliases / clone bindings. A scheme like
    # ``PRG_5_8_f`` defines ``Int lambda = 2 * G.lambda`` and slices on
    # ``G.lambda``; leaving those lengths in terms of a foreign field -- or
    # exposing the primary's ``lambda`` field as a *bare* alias that shadows
    # the base ``Int lambda`` let -- makes the same length acquire several
    # distinct ``bs_*`` names (``bs_2_lambda`` vs ``bs_2_G_lambda``) and EC
    # rejects the scheme. We resolve each int param/field to a base
    # expression and rewrite the instances' concretized lengths once.
    (
        int_qual_map,
        local_int_by_let,
        param_int_by_let,
        int_names_by_let,
    ) = _base_int_length_map(proof, primitives_by_name, schemes_by_name)
    for inst in instances:
        # Resolve foreign field refs + this instance's int params, but NOT its
        # own field names: the concretized lengths are already in base/foreign
        # terms, so applying the field aliases would re-double a base symbol.
        inst_inliner = _LengthInliner(
            param_int_by_let.get(inst.let_name, {}), int_qual_map
        )
        inst.concretized_fields = {
            fname: inst_inliner.transform(ftype)
            for fname, ftype in inst.concretized_fields.items()
        }
    primary_int_names = int_names_by_let.get(primary.let_name, set())

    # Build the top-level alias map. Entries:
    #   * qualified ``"<inst>.<Field>"`` -> base-resolved Type (for resolving
    #     ``E1.Key`` FieldAccess types in reductions, etc.)
    #   * bare ``"<Field>"`` -> base-resolved Type for the primary instance's
    #     *non-int* (Set carrier) fields. The primary's int fields are
    #     deliberately NOT exposed bare: a bare ``lambda`` alias would shadow
    #     the base ``Int lambda`` let and re-double every base length when
    #     naming concrete clone bindings. The scheme *body* -- where bare
    #     ``lambda`` legitimately means the field -- is pre-inlined instead.
    top_aliases: dict[str, frog_ast.Type] = {}
    for inst in instances:
        for fname, ftype in inst.concretized_fields.items():
            top_aliases[f"{inst.let_name}.{fname}"] = ftype
    for fname, ftype in primary.concretized_fields.items():
        if fname in primary_int_names:
            continue
        top_aliases[fname] = ftype
    top_types = tc.TypeCollector(
        aliases=top_aliases, known_abstract_types=known_abstract_types
    )

    # Primitive field names that act as abstract types inside the theory.
    # Only ``Set``-typed fields (the carrier-set pattern, e.g.
    # ``Set Key = KeySpace;``) become abstract EC types. ``Int``-typed
    # scalar parameters (e.g. ``Int lambda = lambda;`` on PRG) are values,
    # not types, and stay out of the map. We can't use ``isinstance(pf.value,
    # frog_ast.Type)`` here because ``Variable`` is itself a ``Type``
    # subclass, so every field with a non-None value would match.
    abstract_types_map: dict[str, str] = {}
    for pf in primitive.fields:
        if isinstance(pf.type, frog_ast.SetType):
            abstract_types_map[pf.name] = pf.name.lower()
    # Game files associated with the primary primitive (vs. foreign-primitive
    # ones, e.g. INDOT$ when the primary is PRG_5_10/PRG). Foreign game files
    # get translated inside their own primitive's abstract theory.
    primary_game_files = [
        gf
        for gf in game_files
        if primitive_name_by_game_file[gf.name] == primitive.name
    ]

    # Each game inside the abstract theory takes a single primitive-typed
    # parameter (e.g. ``Game Real(PRG G)``). Inside the theory, that
    # parameter is just a module variable; ``G.lambda`` has no first-class
    # meaning. Strip ``G.`` prefixes from any bitstring parameterization
    # expression so ``BitString<G.lambda + G.stretch>`` collapses to
    # ``BitString<lambda + stretch>``, matching the primitive's own
    # ``BitString<lambda + stretch>`` signature.
    theory_param_prefixes = {
        gf.games[0].parameters[0].name
        for gf in primary_game_files
        if gf.games[0].parameters
    }
    theory_types = tc.TypeCollector(
        abstract_types=abstract_types_map,
        strip_field_prefixes=theory_param_prefixes,
        theory_mode=True,
    )

    # Method return types are global across ALL primitives so that
    # ``type_of`` resolves method calls like ``P.Enc(k, m)`` even when ``P``
    # is an auxiliary-primitive instance and the caller is a reduction in
    # the primary primitive's scope. Without this, a multi-primitive proof
    # whose reduction body calls into a foreign primitive would crash.
    method_return_types: dict[tuple[str, str], frog_ast.Type] = {}
    for prim in primitives_by_name.values():
        for prim_sig in prim.methods:
            method_return_types[(prim.name, prim_sig.name)] = prim_sig.return_type
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
            if isinstance(e, frog_ast.Slice):
                # A slice's static type is ``BitString<end - start>``
                # regardless of the source bitstring's length.
                return frog_ast.BitStringType(
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.SUBTRACT, e.end, e.start
                    )
                )
            if isinstance(e, frog_ast.BinaryOperation):
                # Recursively resolve through the operator. For ADD/OR
                # on two bitstrings: ADD is xor (same length as LHS);
                # OR is concat (sum of the two lengths). For arithmetic
                # on ints, the result type matches the LHS type.
                lhs_t = type_of(e.left_expression)
                if e.operator == frog_ast.BinaryOperators.ADD and isinstance(
                    lhs_t, frog_ast.BitStringType
                ):
                    return lhs_t
                if e.operator == frog_ast.BinaryOperators.OR and isinstance(
                    lhs_t, frog_ast.BitStringType
                ):
                    rhs_t = type_of(e.right_expression)
                    if (
                        isinstance(rhs_t, frog_ast.BitStringType)
                        and lhs_t.parameterization is not None
                        and rhs_t.parameterization is not None
                    ):
                        return frog_ast.BitStringType(
                            frog_ast.BinaryOperation(
                                frog_ast.BinaryOperators.ADD,
                                lhs_t.parameterization,
                                rhs_t.parameterization,
                            )
                        )
                return lhs_t
            if isinstance(e, frog_ast.Integer):
                return frog_ast.IntType()
            if isinstance(e, frog_ast.BitStringLiteral):
                return frog_ast.BitStringType(e.length)
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

    # Theory-local EC proc signatures per primitive, keyed by primitive name.
    # Used to build the section-scope deterministic-method ``declare axiom``s
    # (binder types are these proc-param types qualified by the clone prefix).
    theory_proc_sigs_by_primitive: dict[str, list[ec_ast.ProcSig]] = {
        primitive.name: ec_primitive.procs
    }

    theory_game_decls: list[ec_ast.EcTopDecl] = []
    oracle_type_by_game_file: dict[str, str] = {}
    module_name_by_concrete_game: dict[tuple[str, str], str] = {}
    adv_type_by_game_file: dict[str, str] = {}
    for gf in primary_game_files:
        gf_id = _ec_ident(gf.name)
        oracle_type_name = f"{gf_id}_Oracle"
        oracle_type_by_game_file[gf.name] = oracle_type_name
        theory_game_decls.append(
            theory_modules.translate_game_file_oracle(gf, oracle_type_name)
        )
        for side in gf.games:
            mod_name = f"{gf_id}_{side.name}"
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
        adv = theory_modules.translate_adversary_type(
            gf, oracle_type_name, adv_type_name=f"{gf_id}_Adv"
        )
        adv_type_by_game_file[gf.name] = adv.name
        theory_game_decls.append(adv)

    assumed_gf_names: set[str] = {
        a.name for a in proof.assumptions if a.name in oracle_type_by_game_file
    }

    theory_assumption_decls: list[ec_ast.EcTopDecl] = []
    assumption_wrapper_names: dict[tuple[str, str], str] = {}
    for gf in primary_game_files:
        if gf.name not in assumed_gf_names:
            continue
        gf_id = _ec_ident(gf.name)
        adv_type_name = adv_type_by_game_file[gf.name]
        for side in gf.games:
            wrapper_name = f"Game_{gf_id}_{side.name}"
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
                assumption_name=gf_id,
                adversary_type_name=adv_type_name,
                scheme_type_name=scheme_type_name,
                scheme_param_name=scheme_param_name,
                real_wrapper_name=assumption_wrapper_names[(gf.name, real_side)],
                random_wrapper_name=assumption_wrapper_names[(gf.name, random_side)],
            )
        )

    # Abstract types + distributions populated during game translation above.
    theory_head = theory_types.emit_abstract()

    # === Secondary primitive theories (multi-primitive proofs) ===
    #
    # For each non-primary primitive that's referenced by a game file or
    # by an instance, emit its own abstract theory containing the Scheme
    # module type, oracle module types, side modules, and adversary type
    # for *its* game files. Each foreign instance later clones from its
    # primitive's theory rather than the primary one.
    #
    # Cross-primitive plumbing (reductions that bridge primitives,
    # assumption-hop axioms on foreign primitives, resolver dispatch
    # through multiple theories) is built in subsequent stages.
    foreign_primitive_names: list[str] = []
    for inst in instances:
        if (
            inst.primitive_name != primitive.name
            and inst.primitive_name not in foreign_primitive_names
        ):
            foreign_primitive_names.append(inst.primitive_name)
    for gf in game_files:
        pn = primitive_name_by_game_file[gf.name]
        if pn != primitive.name and pn not in foreign_primitive_names:
            foreign_primitive_names.append(pn)

    # Per-foreign-primitive scope: TypeCollector + game/oracle decls, plus
    # the abstract-types map and theory_types reference needed later when
    # the corresponding instance is cloned.
    @dataclass
    class _ForeignScope:
        primitive: frog_ast.Primitive
        theory_name: str
        theory_types: tc.TypeCollector
        theory_modules: mt.ModuleTranslator
        abstract_types_map: dict[str, str]
        game_files: list[frog_ast.GameFile]
        theory_decls: list[ec_ast.EcTopDecl]
        oracle_type_by_game_file: dict[str, str]
        module_name_by_concrete_game: dict[tuple[str, str], str]
        adv_type_by_game_file: dict[str, str]
        assumption_wrapper_names: dict[tuple[str, str], str]

    foreign_scopes: dict[str, _ForeignScope] = {}
    for fp_name in foreign_primitive_names:
        fp = primitives_by_name[fp_name]
        fp_abstract: dict[str, str] = {}
        for pf in fp.fields:
            if isinstance(pf.type, frog_ast.SetType):
                fp_abstract[pf.name] = pf.name.lower()
        fp_game_files = [
            gf for gf in game_files if primitive_name_by_game_file[gf.name] == fp.name
        ]
        fp_param_prefixes = {
            gf.games[0].parameters[0].name
            for gf in fp_game_files
            if gf.games[0].parameters
        }
        fp_theory_types = tc.TypeCollector(
            abstract_types=fp_abstract,
            strip_field_prefixes=fp_param_prefixes,
            theory_mode=True,
        )
        fp_theory_modules = mt.ModuleTranslator(fp_theory_types, type_of_factory)
        fp_theory_name = f"{fp.name}_Theory"
        fp_ec_primitive = fp_theory_modules.translate_primitive(
            fp, name=scheme_type_name
        )
        fp_decls: list[ec_ast.EcTopDecl] = [
            fp_ec_primitive,
            *fp_theory_modules.deterministic_op_decls(fp),
        ]
        theory_proc_sigs_by_primitive[fp.name] = fp_ec_primitive.procs
        fp_oracle_by_gf: dict[str, str] = {}
        fp_modname_by_cg: dict[tuple[str, str], str] = {}
        fp_adv_by_gf: dict[str, str] = {}
        for gf in fp_game_files:
            gf_id = _ec_ident(gf.name)
            oracle_type_name = f"{gf_id}_Oracle"
            fp_oracle_by_gf[gf.name] = oracle_type_name
            fp_decls.append(
                fp_theory_modules.translate_game_file_oracle(gf, oracle_type_name)
            )
            for side in gf.games:
                mod_name = f"{gf_id}_{side.name}"
                fp_modname_by_cg[(gf.name, side.name)] = mod_name
                fp_decls.append(
                    fp_theory_modules.translate_game(
                        side,
                        mod_name,
                        fp.name,
                        implements=oracle_type_name,
                        emitted_param_type=scheme_type_name,
                    )
                )
            adv = fp_theory_modules.translate_adversary_type(
                gf, oracle_type_name, adv_type_name=f"{gf_id}_Adv"
            )
            fp_adv_by_gf[gf.name] = adv.name
            fp_decls.append(adv)
        # Assumption wrappers + axioms for each assumed foreign game file.
        fp_assumed = {a.name for a in proof.assumptions if a.name in fp_oracle_by_gf}
        fp_wrapper_names: dict[tuple[str, str], str] = {}
        for gf in fp_game_files:
            if gf.name not in fp_assumed:
                continue
            gf_id = _ec_ident(gf.name)
            adv_type_name = fp_adv_by_gf[gf.name]
            for side in gf.games:
                wrapper_name = f"Game_{gf_id}_{side.name}"
                fp_wrapper_names[(gf.name, side.name)] = wrapper_name
                side_mod_name = fp_modname_by_cg[(gf.name, side.name)]
                fp_decls.append(
                    fp_theory_modules.translate_theory_game_wrapper(
                        wrapper_name=wrapper_name,
                        scheme_param_name=scheme_param_name,
                        scheme_type_name=scheme_type_name,
                        adversary_type_name=adv_type_name,
                        side_module_name=side_mod_name,
                    )
                )
            real_side = gf.games[0].name
            random_side = gf.games[1].name
            fp_decls.extend(
                pt.translate_assumption_axioms_theory(
                    assumption_name=gf_id,
                    adversary_type_name=adv_type_name,
                    scheme_type_name=scheme_type_name,
                    scheme_param_name=scheme_param_name,
                    real_wrapper_name=fp_wrapper_names[(gf.name, real_side)],
                    random_wrapper_name=fp_wrapper_names[(gf.name, random_side)],
                )
            )
        foreign_scopes[fp.name] = _ForeignScope(
            primitive=fp,
            theory_name=fp_theory_name,
            theory_types=fp_theory_types,
            theory_modules=fp_theory_modules,
            abstract_types_map=fp_abstract,
            game_files=fp_game_files,
            theory_decls=fp_decls,
            oracle_type_by_game_file=fp_oracle_by_gf,
            module_name_by_concrete_game=fp_modname_by_cg,
            adv_type_by_game_file=fp_adv_by_gf,
            assumption_wrapper_names=fp_wrapper_names,
        )

    # Merge foreign scopes' game-file mappings into the global view used
    # by downstream code (reductions, resolver, hop translation). Keys are
    # game-file names so the same dictionaries cover both primary and
    # foreign game files.
    for fs in foreign_scopes.values():
        oracle_type_by_game_file.update(fs.oracle_type_by_game_file)
        module_name_by_concrete_game.update(fs.module_name_by_concrete_game)
        adv_type_by_game_file.update(fs.adv_type_by_game_file)
        assumption_wrapper_names.update(fs.assumption_wrapper_names)

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
    instances_by_let_name = {inst.let_name: inst for inst in instances}
    primary_let = next(let for let in proof.lets if let.name == primary.let_name)
    scheme_module_params, scheme_module_param_types, _ = _scheme_functor_params(
        scheme, primary_let.value, instances_by_let_name, scheme_type_name
    )

    # Hoist any nested module calls in scheme method bodies before
    # translating. EC requires module-procedure calls at statement level,
    # so a FrogLang body like ``return G.evaluate(s) + G.evaluate(0^lambda)``
    # would otherwise fall back to ``return witness;`` and break the
    # wrapper-to-flat-state bridge in the per-hop chain.
    scheme_hoisted = canonical_form.hoist_scheme_calls(scheme, method_return_types)
    # Pre-inline the scheme body's integer length references to base symbols.
    # Bare field names (e.g. ``lambda`` = the scheme's own ``Int lambda``) and
    # foreign field references (``G.lambda``) are resolved one-shot so the
    # body's bitstring types match the (base-named) clone bindings. This is
    # what ``top_types`` cannot do alone, since a bare ``lambda`` there would
    # shadow the base let.
    scheme_hoisted = _LengthInliner(
        local_int_by_let.get(primary.let_name, {}), int_qual_map
    ).transform(scheme_hoisted)
    ec_scheme = top_modules.translate_scheme(
        scheme_hoisted,
        qualified_scheme_type,
        module_params=scheme_module_params or None,
        module_param_types=scheme_module_param_types or None,
    )

    # Concrete foreign-scheme modules. For each foreign instance we can
    # concretize (e.g. 5_10's ``P = OTP(lambda)``), translate its scheme
    # body to a top-level EC module ascribing to its clone's ``Scheme``
    # type. Unlike the abstract ``declare module`` path, this lets EC's
    # ``inline *`` unfold the foreign primitive's methods, so the
    # cross-primitive inlining-hop bridge closes. The abstract foreign
    # theory + ``eps_<assumption>`` axiom are still emitted, so the
    # proof's advantage bound is unchanged. We seed a dedicated
    # TypeCollector that resolves the foreign scheme's bare field types
    # (e.g. ``Key``/``Message``/``Ciphertext``) to their concretized
    # carriers; those carriers (e.g. ``bs_lambda``) are emitted by
    # ``top_types`` and merely referenced here.
    foreign_concrete_modules: dict[str, ec_ast.Module] = {}
    concrete_module_expr: dict[str, str] = {}
    for inst in instances:
        if inst.let_name not in concretizable_foreign:
            continue
        foreign_scheme = schemes_by_name[inst.ctor_name]
        foreign_let = next(let for let in proof.lets if let.name == inst.let_name)
        foreign_aliases = dict(top_aliases)
        foreign_int_names = int_names_by_let.get(inst.let_name, set())
        for fname, ftype in inst.concretized_fields.items():
            if fname in foreign_int_names:
                continue  # base-shadowing int field; body is pre-inlined below
            # Direct assignment: the foreign body references bare carrier
            # names (e.g. ``Key``) that mean *its own* fields, so the foreign
            # instance's binding must take precedence over any same-named
            # bare alias inherited from the primary. Without this, OTUC's
            # foreign ``OTP(3*lambda)`` would resolve bare ``Key`` to the
            # primary PseudoOTP's ``BitString<lambda>`` (different width).
            foreign_aliases[fname] = ftype
        foreign_types = tc.TypeCollector(
            aliases=foreign_aliases, known_abstract_types=known_abstract_types
        )
        foreign_modules = mt.ModuleTranslator(foreign_types, type_of_factory)
        fmp, fmpt, applied = _scheme_functor_params(
            foreign_scheme, foreign_let.value, instances_by_let_name, scheme_type_name
        )
        foreign_hoisted = canonical_form.hoist_scheme_calls(
            foreign_scheme, method_return_types
        )
        foreign_hoisted = _LengthInliner(
            local_int_by_let.get(inst.let_name, {}), int_qual_map
        ).transform(foreign_hoisted)
        foreign_concrete_modules[inst.let_name] = foreign_modules.translate_scheme(
            foreign_hoisted,
            f"{inst.clone_alias}.{scheme_type_name}",
            module_params=fmp or None,
            module_param_types=fmpt or None,
        )
        concrete_module_expr[inst.let_name] = (
            f"{inst.ctor_name}({', '.join(applied)})" if applied else inst.ctor_name
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
        elif inst.let_name in concretizable_foreign:
            # Concrete foreign module: reference it directly (e.g. ``OTP``)
            # rather than via a section ``declare module``.
            instance_module_expr[inst.let_name] = concrete_module_expr[inst.let_name]
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
    # (``-E1, -E2``), not the functor application. For multi-primitive
    # proofs every additional ``declare module`` (foreign-primitive
    # instance such as ``P`` for 5_10) must also appear so the
    # adversary's call boundaries don't accidentally permit writes to
    # those declared modules; otherwise the byequiv side conditions of
    # the per-hop pr lemmas fail with ``module P can write A``.
    footprint_names: list[str] = []
    if scheme_module_params:
        footprint_names.extend(p.name for p in scheme_module_params)
    else:
        footprint_names.append(scheme.name)
    for inst in instances:
        # Concretized foreign instances are top-level concrete modules, not
        # ``declare module``s, so they don't belong in the adversary's
        # separation footprint.
        if (
            inst is not primary
            and inst.let_name not in concretizable_foreign
            and inst.let_name not in footprint_names
        ):
            footprint_names.append(inst.let_name)
    primary_footprint = ", ".join(f"-{n}" for n in footprint_names)

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
        # Hoist nested module calls in the reduction body before
        # translation (same motivation as the scheme-body hoisting
        # above): the source body may use a primitive/challenger call
        # as a sub-expression (e.g. ``return challenger.Query() +
        # G.evaluate(0^lambda)``), which the EC translator cannot render
        # as a single statement. Without hoisting, the body falls back
        # to ``return witness;`` and the per-hop wrapper-to-flat-state
        # bridge fails to align with the engine's already-inlined flat
        # states.
        challenger_oracle_type = f"{helper.to_use.name}_Oracle"
        hoisted_reduction = canonical_form.hoist_reduction_calls(
            helper,
            challenger_oracle_type=challenger_oracle_type,
            method_return_types=method_return_types,
        )
        ec_reductions.append(
            top_modules.translate_reduction(
                hoisted_reduction,
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
    declared_module_names = [
        inst.let_name
        for inst in instances
        if inst is not primary and inst.let_name not in concretizable_foreign
    ]
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
        outer_oracle_name=oracle_name_by_game_file[proof.theorem.name],
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

    # Tactic-cache sidecar. Loaded once per export; consulted on every
    # micro-lemma that falls through the Synthesized rungs (1/2).
    # ``requested_cache_keys``
    # accumulates the lookup keys (used by ``cache_report.py`` for
    # orphan detection).
    # pylint: disable=import-outside-toplevel
    from .tactic_cache import (
        HOP_TRANSFORM,
        TacticCache,
        relative_sidecar_path,
    )

    proof_path_obj = pathlib.Path(proof_path)
    tactic_cache = TacticCache.load(relative_sidecar_path(proof_path_obj))
    sidecar_relpath = str(relative_sidecar_path(proof_path_obj))
    requested_cache_keys: list[tuple[str, str, str]] = []
    # Published as a module-level side-channel so ``cache_report.py``
    # can diff the cache against the latest export without reshaping
    # this function's signature. Cleared at each export entry; read
    # immediately after the export call.
    globals()["_last_requested_cache_keys"] = requested_cache_keys

    # Each interchangeability hop's chain emission appends to this list;
    # the assembled file inserts the contents before ``lemmas``.
    chain_extra_decls: list[ec_ast.EcTopDecl] = []
    # (declared module name, clone alias) pairs that needed the
    # statelessness foundation (a stateless-scheme reorder micro was
    # synthesized). The theory + section foundation is emitted only for
    # these, so unaffected proofs are untouched.
    stateless_module_requests: set[tuple[str, str]] = set()
    # Per-hop precondition/postcondition overrides emitted by the chain
    # when its artifacts use strengthened specs (``={glob E1, ...}``) in
    # multi-module proofs. The outer ``hop_<i>`` lemma must use the same
    # strengthened spec or the ``apply hop_<i>_chain`` step in its
    # tactic body fails.
    chain_spec_overrides: dict[int, tuple[str, str]] = {}

    # Module params for non-primary instances used as ``declare module``
    # inside the section. Reduction-adversary wrappers need these as
    # explicit parameters so EC doesn't complain about depending on
    # declared modules. Defined here (before ``_body_for_hop``) so the
    # chain emitter can also see them.
    declared_instance_params: list[ec_ast.ModuleParam] = [
        ec_ast.ModuleParam(
            name=inst.let_name,
            module_type=f"{inst.clone_alias}.{scheme_type_name}",
        )
        for inst in instances
        if inst is not primary and inst.let_name not in concretizable_foreign
    ]

    def _det_reorder_guided_admit(
        _i: int,
        step_a: frog_ast.Step,
        step_b: frog_ast.Step,
        left_key: str,
        right_key: str,
    ) -> list[str]:
        """``admit-guided`` resolution (rung 5) for a deterministic-reorder hop.

        The hop equiv ``<left>.query ~ <right>.query`` reduces (after
        ``proc; inline*; sp; wp``) to: a fresh sample on each side, the same
        deterministic abstract calls in a different order, and an XOR of the
        results. EC's ``sim`` cannot reorder abstract calls, so we admit — but
        annotate the admit with the verified cascade strategy plus the
        determinism axioms in scope (emitted by the determinism-support pass).
        A human/agent reads the ``inline*``-generated variable names off the
        goal (``ec_print_goals <file> <line>``), instantiates the ``<...>``
        placeholders, replaces the ``admit.``, and the result can be cached.
        """
        # Determinism axioms/ops in scope: one per deterministic method of
        # each declared (abstract) module. The reorder is justified by these.
        hints: list[str] = []
        for inst in instances:
            if inst is primary or inst.let_name in concretizable_foreign:
                continue
            prim = primitives_by_name.get(inst.primitive_name)
            if prim is None:
                continue
            for sig in prim.methods:
                if sig.deterministic:
                    m = sig.name.lower()
                    hints.append(
                        f"     {inst.let_name}_{m}_det "
                        f"(g : (glob {inst.let_name})) (a0 : <T> ...) : "
                        f"phoare[ {inst.let_name}.{m} : (glob {inst.let_name})=g "
                        f"/\\ <arg>=a0 ==> (glob {inst.let_name})=g "
                        f"/\\ res = {inst.clone_alias}.ev_{m} a0 ] = 1%r"
                    )
        assert isinstance(step_a.challenger, frog_ast.ConcreteGame)
        assert isinstance(step_b.challenger, frog_ast.ConcreteGame)
        lp = primitive_name_by_game_file.get(step_a.challenger.game.name)
        rp = primitive_name_by_game_file.get(step_b.challenger.game.name)
        return [
            _res_tag(ADMIT_GUIDED),
            f"(* cross-primitive deterministic-reorder hop ({lp} <-> {rp}): a "
            "non-ground foreign scheme is concretized as a functor, so both "
            "sides make the same deterministic abstract calls in a DIFFERENT "
            "order (plus a fresh sample + XOR). EC's ``sim`` cannot reorder "
            "abstract calls; the sound fix replaces each call with its "
            "deterministic op-value via the determinism axioms below, then "
            "couples the samples. This is an ``admit-guided`` resolution "
            "(automation-ladder rung 5): fill the ``<...>`` placeholders from "
            "the goal and replace the admit below to promote it to "
            "``cached-guided`` (rung 3).",
            "",
            "   Determinism axioms in scope (justify the reorder):",
            *hints,
            "",
            "   STRATEGY (verified on 5_8_e; read names via "
            "``ec_print_goals <file> <this-line+1>``):",
            "     proc. inline *. sp. wp.",
            "     (* if a side's fresh sample isn't first, bring it there: *)",
            "     swap{2} <pos> <delta>.",
            "     (* couple the two fresh samples: *)",
            "     seq 1 1 : (<sample1>{1} = <sample2>{2}).",
            "     + rnd (fun (x : <keytype>) => x); skip => />.",
            "     (* peel + eliminate each side's HEAD abstract call (arg is a "
            "constant like zero_lambda); ``sp`` then absorbs the assigns it "
            "feeds so later call args become root vars: *)",
            "     seq 0 1 : (<carry coupling> /\\ <m2>{2} = "
            "<clone>.ev_<meth> <const>).",
            "     + exists* (glob <Mod2>){2}; elim* => g2; "
            "call{2} (<Mod2>_<meth>_det g2 <const>); auto.",
            "     sp.",
            "     (* eliminate the remaining (key-argument) calls, one side at "
            "a time, back to front; ``exists*`` the arg first, ``wp`` between "
            "calls to clear trailing assigns: *)",
            "     exists* (glob <Mod1>){1}; elim* => g1. "
            "exists* (glob <Mod2>){2}; elim* => g2.",
            "     exists* <keyarg2>{2}; elim* => k2v. "
            "call{2} (<Mod2>_<meth>_det g2 k2v).",
            "     call{1} (<Mod1>_<meth>_det g1 <const>). wp.",
            "     exists* <keyarg1>{1}; elim* => k1v. "
            "call{1} (<Mod1>_<meth>_det g1 k1v).",
            "     skip => /#.",
            "   NOTE: a reverse-direction hop may have a DEAD evaluate call "
            "(its result is discarded) — eliminate it the same way (the "
            "axiom's glob-preservation discharges it). For >1 key call or "
            "data-dependent args, repeat the eliminate step per call.",
            "",
            "   TO CACHE (once filled & ``ec_compile`` passes): add an "
            "``[[entry]]`` to the proof's ``.tactics.toml`` sidecar with "
            f"``transform = {HOP_TRANSFORM!r}``, ``tactic`` = the filled body "
            "(without the final ``qed.``), and the two canonical keys below as "
            "``game_before`` / ``game_after``. Re-export then closes this hop "
            "automatically.",
            "",
            "   game_before (canonical text of the left game):",
            *(f"     {ln}" for ln in left_key.splitlines() or [""]),
            "   game_after (canonical text of the right game):",
            *(f"     {ln}" for ln in right_key.splitlines() or [""]),
            "   *)",
            "admit.",
            "qed.",
        ]

    def _body_for_hop(
        _i: int, step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> list[str] | None:
        if _is_assumption_hop(step_a, step_b):
            return None
        assert isinstance(step_a.challenger, frog_ast.ConcreteGame)
        assert isinstance(step_b.challenger, frog_ast.ConcreteGame)
        # Cross-primitive bridge: when the two endpoints' challengers
        # are different game files on different primitives, the engine
        # inlines each side's challenger body — including external-
        # primitive method calls (``P.KeyGen()``, ``P.Enc()``) — into
        # flat samples and xor operations. EC's per-primitive abstract
        # theory keeps those primitives' methods abstract, so the bridge
        # ``proc; inline*; sp; wp; sim`` between the engine's inlined
        # flat-state module and the reduction's abstract-method body
        # cannot close: EC doesn't know that ``P.KeyGen()`` is uniform
        # without the INDOT$ assumption (which the proof treats as an
        # inlining hop here, not an assumption hop).
        #
        # When every instance of the foreign primitive(s) involved in the
        # hop is emitted CONCRETELY (see ``concretizable_foreign``), EC's
        # ``inline *`` can unfold those methods on the wrapper side, so
        # the chain bridge closes and we fall through to normal emission.
        # Otherwise (the foreign primitive stays abstract) we emit a
        # hop-level admit with a structured comment rather than producing
        # a chain whose bridge will fail. The chain itself is internally
        # consistent and would close — only the wrapper-to-flat bridge is
        # unprovable in the abstract configuration.
        left_gf = step_a.challenger.game.name
        right_gf = step_b.challenger.game.name
        is_cross_primitive = left_gf != right_gf and primitive_name_by_game_file.get(
            left_gf
        ) != primitive_name_by_game_file.get(right_gf)
        if is_cross_primitive:
            foreign_prims = {
                primitive_name_by_game_file.get(left_gf),
                primitive_name_by_game_file.get(right_gf),
            } - {primitive.name}
            foreign_insts = [
                inst for inst in instances if inst.primitive_name in foreign_prims
            ]
            # Only scheme instances (concrete bodies the engine can inline)
            # need to be concretized in EC. A foreign *primitive* instance
            # (e.g. OTUC's ``G : PRG``) has no scheme body — its methods stay
            # opaque on both sides of the hop, so ``sim`` over an abstract
            # declared module closes the bridge with ``={glob G}``. We
            # therefore restrict the concretization-required check to scheme
            # instances; a hop whose only foreign instance is a primitive is
            # not blocked.
            foreign_scheme_insts = [
                inst for inst in foreign_insts if inst.ctor_name in schemes_by_name
            ]
            foreign_all_concrete = all(
                inst.let_name in concretizable_foreign for inst in foreign_scheme_insts
            )
            foreign_has_nonground = any(
                inst.let_name in nonground_concrete for inst in foreign_insts
            )
        else:
            foreign_all_concrete = True
            foreign_has_nonground = False
        if is_cross_primitive and not foreign_all_concrete:
            return [
                _res_tag(ADMIT_UNGUIDED),
                f"(* cross-primitive inlining hop: {left_gf} and {right_gf} "
                f"live on different primitives "
                f"({primitive_name_by_game_file.get(left_gf)} vs "
                f"{primitive_name_by_game_file.get(right_gf)}). The engine's "
                "canonicalization inlines each side's primitive methods to "
                "uniform samples, but EC keeps the primitives abstract; the "
                "wrapper↔flat-state bridge ``proc; inline*; sp; wp; sim`` "
                "cannot reconcile abstract module calls with inlined samples "
                "without the indistinguishability assumption being applied as "
                "an axiom (which the proof treats as an inlining hop here). "
                "Falling back to admit at the hop level. *)",
                "admit.",
                "qed.",
            ]
        if is_cross_primitive and foreign_has_nonground:
            # Non-ground foreign scheme concretized as a functor (e.g.
            # ``PseudoOTP(G)``): the two sides make the same deterministic
            # ``G.evaluate`` calls in a different order (plus an interleaved
            # sample + XOR), which the canned ``sim`` bridge cannot reorder.
            # This whole hop is the cache unit (it bypasses the per-transform
            # chain). Consult the sidecar for a cached hop tactic keyed on the
            # canonical text of the two adjacent inlined games; on a hit emit
            # it and the hop closes on export (``cached-guided``, rung 3). On
            # a miss emit an ``admit-guided`` resolution (rung 5: the cascade
            # strategy + determinism axioms in scope) so a human/agent can
            # fill it in and add the
            # sidecar entry.
            assert isinstance(step_a.challenger, frog_ast.ConcreteGame)
            assert isinstance(step_b.challenger, frog_ast.ConcreteGame)
            # pylint: disable=protected-access
            hop_left_ast = engine._get_game_ast(step_a.challenger, step_a.reduction)
            hop_right_ast = engine._get_game_ast(step_b.challenger, step_b.reduction)
            # pylint: enable=protected-access
            emt = {inst.let_name: primitive.name for inst in instances}
            left_key = canonical_form.canonical_text(
                hop_left_ast, emt, method_return_types
            )
            right_key = canonical_form.canonical_text(
                hop_right_ast, emt, method_return_types
            )
            requested_cache_keys.append((HOP_TRANSFORM, left_key, right_key))
            cached = tactic_cache.lookup(HOP_TRANSFORM, left_key, right_key)
            if cached is not None:
                return [_res_tag(CACHED_GUIDED), *cached.tactic.splitlines(), "qed."]
            return _det_reorder_guided_admit(_i, step_a, step_b, left_key, right_key)
        # The hop equiv compares the two adjacent composed games at the
        # OUTER oracle interface (what the adversary calls). When a
        # reduction is composed, the resulting module exposes the
        # reduction's outer-method names, which match the theorem game's
        # oracle — *not* the inner challenger's. For single-primitive
        # proofs these coincide; for multi-primitive proofs (e.g. 5_10's
        # hop 4 between INDOT$(P).Real ∘ R3 and PRGSecurity(G).Real ∘ R4),
        # using the inner-challenger's method name would call a non-
        # existent procedure on the composed module.
        method_name = oracle_name_by_game_file[proof.theorem.name]
        # pylint: disable=protected-access
        left_ast = engine._get_game_ast(step_a.challenger, step_a.reduction)
        right_ast = engine._get_game_ast(step_b.challenger, step_b.reduction)
        # pylint: enable=protected-access
        # pylint: disable=import-outside-toplevel
        from .chain_emitter import emit_chain_for_hop

        _left_canon, left_apps = engine.canonicalize_game_with_states(
            copy.deepcopy(left_ast)
        )
        _right_canon, right_apps = engine.canonicalize_game_with_states(
            copy.deepcopy(right_ast)
        )
        # Each instance maps to its OWN primitive's name (not the primary's).
        # A multi-primitive proof has, e.g., ``G : PRG`` alongside ``P, E``
        # on SymEnc; method-return-type lookups for ``G.evaluate`` must
        # resolve through ``PRG``, not the primary's primitive.
        external_module_types: dict[str, str] = {
            inst.let_name: inst.primitive_name for inst in instances
        }
        # In multi-scheme proofs the flat-state modules live inside a
        # section with ``declare module E1, E2``; EC forbids
        # section-local modules from depending on declared modules
        # implicitly, so we pass them as functor parameters.
        flat_module_params = (
            list(declared_instance_params) if declared_instance_params else None
        )
        info = emit_chain_for_hop(
            hop_index=_i,
            left_game=left_ast,
            right_game=right_ast,
            left_apps=left_apps,
            right_apps=right_apps,
            oracle_name=method_name,
            eq_args=resolver.precondition_for(step_a),
            types=top_types,
            type_of_factory=type_of_factory,
            external_module_types=external_module_types,
            method_return_types=method_return_types,
            flat_module_params=flat_module_params,
            tactic_cache=tactic_cache,
            sidecar_relpath=sidecar_relpath,
        )
        chain_extra_decls.extend(info.extra_decls)
        requested_cache_keys.extend(info.requested_keys)
        stateless_module_requests.update(info.stateless_modules)
        if info.pre_override is not None or info.post_override is not None:
            chain_spec_overrides[_i] = (
                info.pre_override or resolver.precondition_for(step_a),
                info.post_override or "={res}",
            )
        return info.tactic_body

    lemmas = pt.translate_hops(
        resolver, proof.steps, _body_for_hop, spec_overrides=chain_spec_overrides
    )

    qualified_adv_type_by_game_file: dict[str, str] = {
        name: f"{clone_alias}.{adv}" for name, adv in adv_type_by_game_file.items()
    }
    outer_game_file_name = proof.theorem.name
    qualified_outer_adv = qualified_adv_type_by_game_file[outer_game_file_name]

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
        ec_game_wrappers.append(_describe_step_wrapper(i, step))
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
            assumption_names_by_hop[i] = _ec_ident(assumption_game_file_name)
            ec_pr_lemmas.append(
                _describe_assumption_hop(i, assumption_game_file_name, reduction_name)
            )
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
                    assumption_name=_ec_ident(assumption_game_file_name),
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
            ec_pr_lemmas.append(_describe_inlining_hop(i))
            # When ``chain_spec_overrides`` registers a per-hop spec
            # override for this hop (only ever happens in multi-module
            # mode where the chain emits ``={glob E1, ...}``-strengthened
            # micros and the outer ``hop_<i>`` is similarly strengthened),
            # pass the declared-module list as the ``call`` invariant
            # so the inner ``conseq hop_<i>`` can unify.
            glob_invariant_modules = (
                [p.name for p in declared_instance_params]
                if i in chain_spec_overrides and declared_instance_params
                else None
            )
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
                    glob_invariant_modules=glob_invariant_modules,
                )
            )

    # === Assemble the file ===

    # Build one clone per scheme instance. For each instance:
    #   * every primitive abstract type (``message``/``key``) binds to
    #     the instance's concretized field type at the top level;
    #   * every abstract bitstring type registered inside the theory
    #     (e.g. ``bs_lambda``, ``bs_lambda_stretch`` from PRG) binds to
    #     the concrete top-level bitstring obtained by substituting the
    #     instance's field values into the original parameterization
    #     (e.g. ``bs_lambda_stretch`` -> ``bs_2_lambda`` when the
    #     instance has lambda=lambda and stretch=lambda).
    def _instance_clone(inst: si.SchemeInstance) -> ec_ast.Clone:
        # Each instance clones the abstract theory of its primitive. For
        # primary-primitive instances that's the primary theory; for
        # foreign-primitive instances it's the corresponding foreign
        # scope's theory (with its own abstract_types_map and theory_types).
        if inst.primitive_name == primitive.name:
            src_theory_name = theory_name
            src_abstract_types_map = abstract_types_map
            src_theory_types = theory_types
        else:
            fs = foreign_scopes[inst.primitive_name]
            src_theory_name = fs.theory_name
            src_abstract_types_map = fs.abstract_types_map
            src_theory_types = fs.theory_types
        type_bindings_: list[tuple[str, str]] = []
        for pf_name, abs_name in src_abstract_types_map.items():
            if pf_name in inst.concretized_fields:
                ec_concrete = top_types.translate_type(inst.concretized_fields[pf_name])
                type_bindings_.append((abs_name, ec_concrete.text))
        # Build bitstring type bindings by reconstructing each abstract
        # bitstring as a BitString<...> with the instance's field values
        # substituted in, then re-translating through ``top_types`` so the
        # resulting concrete type gets registered for top-level emission.
        for abs_name, abs_expr in src_theory_types.abstract_bitstrings:
            concrete_expr = _instantiate_bitstring_expr(
                abs_expr, inst.concretized_fields
            )
            concrete_type = top_types.translate_type(
                frog_ast.BitStringType(concrete_expr)
            )
            type_bindings_.append((abs_name, concrete_type.text))
        op_bindings_: list[tuple[str, str]] = []
        for distr in src_theory_types.abstract_distrs_seen:
            binding = _distr_binding_for(
                distr, src_abstract_types_map, inst.concretized_fields, top_types
            )
            if binding is not None:
                op_bindings_.append(binding)
            elif distr.startswith("dbs_"):
                # Bitstring distribution bound through the abstract
                # bitstring binding: dbs_X (theory) <- dbs_<concrete>
                # (top-level) for whatever the theory's bs_X clones to.
                abs_name = distr[1:]  # strip leading 'd' -> bs_X
                for a_name, t_name in type_bindings_:
                    if a_name == abs_name and t_name.startswith("bs"):
                        concrete_distr = "d" + t_name
                        op_bindings_.append((distr, concrete_distr))
                        break
        return ec_ast.Clone(
            source_theory=src_theory_name,
            alias=inst.clone_alias,
            type_bindings=type_bindings_,
            op_bindings=op_bindings_,
        )

    # Statelessness foundation (gated): emit the per-method distribution ops,
    # the ``Ideal`` sampling module and the lossless axioms into the primary
    # theory only when a stateless-scheme reorder for one of its instances was
    # synthesized. See ``chain_emitter._synth_stateless_reorder``.
    _requested_primitive_names = {
        inst.primitive_name
        for inst in instances
        if inst.let_name in {m for (m, _) in stateless_module_requests}
    }
    stateless_theory_decls: list[ec_ast.EcTopDecl] = []
    if primitive.name in _requested_primitive_names:
        stateless_theory_decls = [
            "(* Statelessness foundation *)",
            *theory_modules.distribution_op_decls(primitive),
            *theory_modules.lossless_axiom_lines(primitive),
            theory_modules.ideal_module_text(primitive, scheme_type_name),
        ]

    theory = ec_ast.AbstractTheory(
        name=theory_name,
        decls=[
            *theory_head,
            ec_primitive,
            *theory_modules.deterministic_op_decls(primitive),
            *stateless_theory_decls,
            *theory_game_decls,
            *theory_assumption_decls,
        ],
    )

    # Foreign primitives each get their own abstract theory. The list is
    # emitted into the file in the same registration order as
    # ``foreign_primitive_names`` so output is deterministic.
    foreign_theories: list[ec_ast.AbstractTheory] = []
    for fp_name in foreign_primitive_names:
        fs = foreign_scopes[fp_name]
        foreign_theories.append(
            ec_ast.AbstractTheory(
                name=fs.theory_name,
                decls=[
                    *fs.theory_types.emit_abstract(),
                    *fs.theory_decls,
                ],
            )
        )

    clones: list[ec_ast.EcTopDecl] = [_instance_clone(inst) for inst in instances]

    # Per-clone distribution axioms. For each cloned distribution
    # ``<concrete_distr>`` bound in an instance's clone (e.g.
    # ``dciphertext -> dCiphertextSpace1`` in ``E1_c``), emit
    #
    #     axiom <let_name>_<concrete_distr>_funi : is_funiform <concrete_distr>.
    #     axiom <let_name>_<concrete_distr>_ll   : is_lossless <concrete_distr>.
    #
    # These are the hooks per-transform tactic scripts use to discharge
    # ``rnd{1}`` (drop independent sample) and related goals. They are
    # redundant in single-clone proofs (the TypeCollector already emits
    # ``<concrete_distr>_fu``/``<concrete_distr>_ll``), but the explicit
    # per-clone prefix is uniform across all proofs and immune to
    # multi-instance naming collisions in proofs with two clones over
    # the same primitive.
    clone_axioms: list[ec_ast.EcTopDecl] = []
    seen_axiom_names: set[str] = set()
    for inst in instances:
        for _, concrete_distr in next(
            (
                c.op_bindings
                for c in clones
                if isinstance(c, ec_ast.Clone) and c.alias == inst.clone_alias
            ),
            [],
        ):
            # Only emit axioms for atomic distribution ops. Product
            # distributions (``dA `*` dB``) are constructed from atomic
            # ones whose axioms are already emitted for the source
            # instances; emitting an axiom about the product would be
            # both redundant and a syntactic mess (the ``*`` in the
            # axiom name is invalid EC).
            if not concrete_distr.isidentifier():
                continue
            for suffix, predicate in (
                ("funi", "is_funiform"),
                ("ll", "is_lossless"),
            ):
                axiom_name = f"{inst.let_name}_{concrete_distr}_{suffix}"
                if axiom_name in seen_axiom_names:
                    continue
                seen_axiom_names.add(axiom_name)
                clone_axioms.append(
                    ec_ast.Axiom(axiom_name, f"{predicate} {concrete_distr}")
                )

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
        elif isinstance(let.type, frog_ast.IntType) and let.value is None:
            # Opaque ``Int X;`` let-binding -- declare as an abstract int op
            # at top level. Referenced from BitString lengths, reduction
            # bodies, etc.
            set_let_decls.append(ec_ast.OpDecl(let.name, "int"))

    # Non-primary primitive instances become ``declare module`` names
    # inside a ``section Main``. For CES this yields
    # ``declare module E1 <: E1_c.Scheme.`` and ``E2 <: E2_c.Scheme.``.
    declare_modules: list[ec_ast.DeclareModule] = []
    for inst in instances:
        if inst is primary or inst.let_name in concretizable_foreign:
            continue
        disjoint = [d.name for d in declare_modules]
        declare_modules.append(
            ec_ast.DeclareModule(
                name=inst.let_name,
                module_type=f"{inst.clone_alias}.{scheme_type_name}",
                disjoint_from=disjoint,
            )
        )

    # Deterministic-method support: for each declared module ascribing to a
    # primitive theory, emit a section-scope ``declare axiom`` asserting the
    # method is a pure, glob-preserving, total function (== the theory-level
    # ``ev_<m>`` op cloned into ``<clone>.ev_<m>``). This is what lets the
    # cross-primitive bridge reorder two deterministic abstract calls soundly
    # (FrogLang ``deterministic`` methods are pure functions of their args).
    det_axioms: list[ec_ast.Axiom] = []
    for dm in declare_modules:
        dm_inst = next(i for i in instances if i.let_name == dm.name)
        dm_prim = primitives_by_name.get(dm_inst.primitive_name)
        dm_proc_sigs = theory_proc_sigs_by_primitive.get(dm_inst.primitive_name, [])
        if dm_prim is None:
            continue
        proc_sig_by_name = {ps.name: ps for ps in dm_proc_sigs}
        # Resolve theory-local type names into the clone's scope: bound types
        # become their concrete target (``bs_lambda_t`` -> ``bs_lambda``);
        # still-abstract types fall back to ``<clone>.<name>``.
        dm_type_binding = dict(_instance_clone(dm_inst).type_bindings)
        for sig in dm_prim.methods:
            if sig.deterministic and sig.name.lower() in proc_sig_by_name:
                det_axioms.append(
                    mt.ModuleTranslator.deterministic_axiom(
                        dm.name,
                        dm_inst.clone_alias,
                        proc_sig_by_name[sig.name.lower()],
                        dm_type_binding,
                    )
                )

    # Statelessness specs: ``declare axiom <E>_<m>_sem`` per probabilistic
    # method, for each declared module that a synthesized stateless-scheme
    # reorder routed through ``Ideal``.
    stateless_axioms: list[ec_ast.Axiom] = []
    _stateless_request_names = {m for (m, _) in stateless_module_requests}
    for dm in declare_modules:
        if dm.name not in _stateless_request_names:
            continue
        dm_inst = next(i for i in instances if i.let_name == dm.name)
        dm_prim = primitives_by_name.get(dm_inst.primitive_name)
        dm_proc_sigs = theory_proc_sigs_by_primitive.get(dm_inst.primitive_name, [])
        if dm_prim is None:
            continue
        proc_sig_by_name = {ps.name: ps for ps in dm_proc_sigs}
        for sig in dm_prim.methods:
            if not sig.deterministic and sig.name.lower() in proc_sig_by_name:
                stateless_axioms.append(
                    mt.ModuleTranslator.stateless_axiom(
                        dm.name,
                        dm_inst.clone_alias,
                        proc_sig_by_name[sig.name.lower()],
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
    if ec_reductions:
        proof_decls.append(_section_header("Reductions"))
        proof_decls.extend(ec_reductions)
    if ec_reduction_advs:
        proof_decls.append(
            _section_header("Reductions lifted to assumption-adversaries")
        )
        proof_decls.extend(ec_reduction_advs)
    proof_decls.append(_section_header("Game-step wrappers"))
    proof_decls.extend(ec_game_wrappers)
    # The chain artifacts (flat-state modules, micro-lemmas,
    # hop_<i>_chain lemmas) must precede the hop_<i> equiv lemmas that
    # reference them via ``apply hop_<i>_chain``.
    if chain_extra_decls:
        proof_decls.append(_section_header("Per-transform canonicalization chain"))
        proof_decls.extend(chain_extra_decls)
    proof_decls.append(_section_header("Per-hop equivalence lemmas"))
    proof_decls.extend(lemmas)
    proof_decls.append(_section_header("Per-hop probability lemmas"))
    proof_decls.extend(ec_pr_lemmas)
    if main_theorem is not None:
        proof_decls.append(_section_header("Main theorem"))
        proof_decls.append(main_theorem)

    decls: list[ec_ast.EcTopDecl] = []
    # Abstract type declarations (e.g. ``type CiphertextSpace1.``)
    # must precede any op declarations that reference them (e.g. the
    # ``dCiphertextSpace1 : CiphertextSpace1 distr`` that ``top_types.
    # emit()`` produces).
    if set_let_decls:
        decls.append(_section_header("Abstract set declarations"))
        decls.extend(set_let_decls)
    decls.append(_section_header("Concrete primitive types"))
    decls.extend(top_types.emit())
    decls.append(
        _section_header("Abstract theory: primitive + security games + assumption")
    )
    decls.append(theory)
    for fp_theory in foreign_theories:
        decls.append(_section_header(f"Foreign primitive theory: {fp_theory.name}"))
        decls.append(fp_theory)
    decls.append(_section_header("Theory instantiation"))
    decls.extend(clones)
    if clone_axioms:
        decls.append(_section_header("Per-clone distribution axioms"))
        decls.extend(clone_axioms)
    if scheme.requirements:
        decls.append(
            "(* NOTE: the FrogLang scheme has `requires` clauses that are "
            "not enforced by the EC export. The scheme module below may "
            "fail EC type-checking because cross-clone type equalities "
            "implied by the `requires` are not expressed in the clones. "
            "Deferred to Phase 5D. *)"
        )
    decls.append(_section_header("Concrete scheme implementation"))
    decls.append(ec_scheme)
    if foreign_concrete_modules:
        decls.append(_section_header("Concrete foreign scheme implementations"))
        for inst in instances:
            if inst.let_name in foreign_concrete_modules:
                decls.append(foreign_concrete_modules[inst.let_name])
    det_axiom_decls: list[ec_ast.EcTopDecl] = (
        [_section_header("Deterministic-method specs"), *det_axioms]
        if det_axioms
        else []
    )
    if stateless_axioms:
        det_axiom_decls += [
            _section_header("Statelessness specs"),
            *stateless_axioms,
        ]
    if declare_modules:
        decls.append(
            ec_ast.Section(
                name="Main",
                decls=[*declare_modules, *det_axiom_decls, *proof_decls],
            )
        )
    else:
        decls.extend(proof_decls)

    ec_file = ec_ast.EcFile(
        # ``DProd`` / ``DMap`` provide the dprod/dmap lemmas
        # (``dmap_dprodE``, ``dmap1E``, ``dmap_id``, ``supp_dprod``,
        # etc.) consumed by the slice/concat round-trip + distribution-
        # split tactics emitted for Split/Merge Uniform Samples.
        requires=["AllCore", "Distr", "DProd", "DMap"],
        decls=decls,
    )
    return ec_ast.pretty_print(ec_file)
