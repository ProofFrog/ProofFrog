"""End-to-end exporter: ProofFile path -> EasyCrypt source string."""

# pylint: disable=duplicate-code  # shares the comparison/logical BinaryOperators
# enumeration with export/latex/stmt_renderer.py by coincidence, not by design

from __future__ import annotations

import copy
import pathlib
import re
from dataclasses import dataclass
from typing import Any, Callable, cast

from . import binding_challenge as bch
from . import canonical_form
from . import ec_ast
from . import module_translator as mt
from . import oracle_model
from . import proof_translator as pt
from . import scheme_instances as si
from . import type_collector as tc
from .resolution import ADMIT_GUIDED, ADMIT_UNGUIDED, CACHED_GUIDED
from .resolution import tag as _res_tag
from ... import frog_ast
from ... import frog_parser
from ... import proof_engine as pe
from ... import visitors

# Standardization passes the exporter omits from a hop's canonicalization chain.
# ``Standardize Parameters`` renames oracle parameters to ``arg1..argN`` only in
# the pipeline tail; keeping the game's own parameter names throughout a chain
# lets the single per-oracle precondition string stay valid both as the
# top-level equiv spec and in synthesizers' mid-proof ``seq``/``transitivity``
# reuse. The rename is a non-observable cosmetic normalization, so every proof
# that verified still has endpoint-matching left/right chains without it.
_EXPORT_SKIP_PASSES = frozenset({"Standardize Parameters"})


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


class _QualifyFields(visitors.Transformer):
    """Qualify a bare int-field ``Variable`` in a bitstring length to a given
    instance (``Nss`` -> ``inst.Nss``), but only for names the instance
    actually has as a length field (``f"{inst}.{name}"`` in ``qualified``).

    Used to turn a primitive method's raw return length ``BitString<Nss>`` into
    the calling instance's concrete length, so it inlines through the seeded
    ``inst.Nss`` alias to the base int rather than stripping to a bare width."""

    def __init__(self, inst: str, qualified: dict[str, frog_ast.ASTNode]) -> None:
        self._inst = inst
        self._qualified = qualified

    def transform_variable(self, variable: frog_ast.Variable) -> frog_ast.ASTNode:
        if f"{self._inst}.{variable.name}" in self._qualified:
            return frog_ast.FieldAccess(frog_ast.Variable(self._inst), variable.name)
        return variable


def _param_aliased_int_qual_map(
    scheme: frog_ast.Scheme | None,
    let_value: frog_ast.Expression | None,
    int_qual_map: dict[str, frog_ast.ASTNode],
) -> dict[str, frog_ast.ASTNode]:
    """Extend ``int_qual_map`` so a scheme's PARAM length fields resolve.

    A scheme wrapping a sub-primitive (``KEM_PQ = SeededKEMWrapper(KEM_PQ_inner)``)
    has fields that reference its param's length directly (``Set DecapsKey =
    BitString<K_inner.Nseed>``). The param is not a let, so ``int_qual_map``
    (keyed ``<let>.<int>``) leaves ``K_inner.Nseed`` unresolved -> an invalid
    ``bs_K_inner_Nseed``. Bind each param to its instantiation arg and alias
    ``<param>.<int>`` to the already-resolved ``<arg>.<int>`` base value. Only
    ADDS keys, so an instance without such a param-length field is byte-identical.
    """
    if (
        scheme is None
        or not scheme.parameters
        or not isinstance(let_value, frog_ast.FuncCall)
    ):
        return int_qual_map
    out = dict(int_qual_map)
    for sp, sa in zip(scheme.parameters, let_value.args):
        if not isinstance(sa, frog_ast.Variable):
            continue
        sa_prefix = f"{sa.name}."
        for qk, qv in int_qual_map.items():
            if qk.startswith(sa_prefix):
                out[f"{sp.name}.{qk[len(sa_prefix):]}"] = qv
    return out


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
        # A scheme field like ``CG_expanded.Nss = H.Nout`` references the
        # scheme's own MODULE param name (``H`` = the KDF param), not the
        # instantiation arg (``Hkdf``). Substitute param -> arg first so the
        # chained resolution ``hybrid.Nss -> H.Nout -> Hkdf.Nout -> Nout``
        # completes (``qualified`` already holds ``Hkdf.Nout -> Nout`` from the
        # earlier-declared let); otherwise ``H.Nout`` stays unresolved and the
        # length renders as a stray ``bs_hybrid_Nss`` distinct from ``bs_Nout``.
        module_param_subst = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
        for param, arg in zip(defn.parameters, let.value.args):
            if not isinstance(getattr(param, "type", None), frog_ast.IntType):
                module_param_subst.set(
                    frog_ast.Variable(param.name), copy.deepcopy(arg)
                )
        for param, arg in zip(defn.parameters, let.value.args):
            if isinstance(getattr(param, "type", None), frog_ast.IntType):
                value = inliner.transform(arg)
                local[param.name] = value
                params_local[param.name] = value
        for fld in defn.fields:
            if isinstance(fld.type, frog_ast.IntType) and fld.value is not None:
                fld_value = visitors.SubstitutionTransformer(
                    module_param_subst
                ).transform(copy.deepcopy(fld.value))
                local[fld.name] = inliner.transform(fld_value)
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
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


# EasyCrypt reserved keywords that can collide with FrogLang let-binding
# names (e.g. ``Int in;`` from a PRF index). When a let-name lands in this
# set it must be escaped before emission as an EC ``op`` / identifier, else
# EC raises a parse error (``op in : int.`` -> "parse error"). The list is
# the subset of EC keywords a numeric/set let-name realistically hits; extend
# as new collisions surface under EC validation.
_EC_RESERVED_WORDS: frozenset[str] = frozenset(
    {
        "in",
        "as",
        "op",
        "var",
        "fun",
        "let",
        "end",
        "res",
        "if",
        "then",
        "else",
        "while",
        "return",
        "with",
        "type",
        "module",
        "proc",
        "theory",
        "clone",
        "import",
        "export",
        "axiom",
        "lemma",
        "proof",
        "qed",
        "glob",
        "hoare",
        "equiv",
        "forall",
        "exists",
    }
)


def _safe_ec_op_ident(name: str) -> str:
    """Escape a FrogLang let-name that collides with an EC reserved keyword.

    Appends a single underscore (``in`` -> ``in_``) so the emitted ``op`` /
    identifier parses; non-colliding names pass through unchanged. The mapping
    is deterministic and injective over the corpus's let-names. Apply this at
    every site that renders a let-name as an EC identifier so the declaration
    and its references stay consistent.
    """
    return f"{name}_" if name in _EC_RESERVED_WORDS else name


def _section_header(label: str) -> str:
    """Render a top-level section divider comment.

    Inserted as a bare-string ``EcTopDecl`` (the pretty-printer renders
    such elements verbatim) to break the generated EC file into
    visually-distinct sections.
    """
    return f"(* ===== {label} ===== *)"


def _prime_group_names(proof: frog_ast.ProofFile) -> set[str]:
    """Group names the proof declared ``requires <G>.order is prime;`` for.

    Mirrors ``PipelineContext.has_prime_order_requirement``: a requirement
    with ``kind == "prime"`` whose target is ``FieldAccess(<G>, 'order')``
    or ``GroupOrder(<G>)``. These groups get the prime EC emission path
    (PowZMod/ZModField + a ``prime <G>.order`` axiom); all others get the
    general CyclicGroup/ZModRing path.
    """
    names: set[str] = set()
    for req in proof.requirements:
        if req.kind != "prime":
            continue
        target = req.target
        if (
            isinstance(target, frog_ast.FieldAccess)
            and target.name == "order"
            and isinstance(target.the_object, frog_ast.Variable)
        ):
            names.add(target.the_object.name)
        elif isinstance(target, frog_ast.GroupOrder) and isinstance(
            target.group, frog_ast.Variable
        ):
            names.add(target.group.name)
    return names


def _group_only_let_name(proof: frog_ast.ProofFile) -> str | None:
    """Return the group let-name if this is a *group-only* proof, else None.

    A group-only proof (e.g. ``DDH_implies_CDH``) imports only game files --
    no ``.scheme``/``.primitive`` -- and attacks a game parameterized by a
    ``Group`` math structure: ``let: Group G;``, ``theorem: CDH(G);``. The
    theorem target's let has a :class:`~proof_frog.frog_ast.GroupType`. Such a
    proof has no primitive theory; its games/reductions are emitted at top
    level over the cloned group (see :func:`_export_group_only`). The caller
    only consults this once it knows no primitive/scheme was imported, so a
    ``Scheme ElGamal(Group G)`` proof (which DOES import a scheme) never takes
    this path -- that is the deferred Phase-C scheme-axis case.
    """
    if not (
        isinstance(proof.theorem, frog_ast.ParameterizedGame)
        and proof.theorem.args
        and isinstance(proof.theorem.args[0], frog_ast.Variable)
    ):
        return None
    target = proof.theorem.args[0].name
    for let in proof.lets:
        if let.name == target and isinstance(let.type, frog_ast.GroupType):
            return let.name
    return None


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


def _challenger_game_file_name(
    challenger: frog_ast.ConcreteGame | frog_ast.ParameterizedGame,
) -> str:
    """Game-file (or intermediate-game) name of a step's challenger.

    A ``ConcreteGame`` names an imported game file plus a ``.Real``/``.Random``
    side (``challenger.game.name``); a ``ParameterizedGame`` is a bare
    intermediate game defined in the proof (``challenger.name``).
    """
    if isinstance(challenger, frog_ast.ConcreteGame):
        return challenger.game.name
    return challenger.name


def _wrapper_game_file_for(step: frog_ast.Step, outer_game_file_name: str) -> str:
    """Game file whose ``Initialize`` / oracle interface the step's wrapper lifts.

    A **plain** step (``Game(E).Side``, no reduction) exposes its own game
    file's oracle, so its ``Game_step_<i>`` wrapper lifts that game file's
    ``Initialize``. A **composed** step (``Game(E).Side compose R``) and a
    bare **intermediate game** (``G_RandKey(K, F)``) are both played against
    the OUTER (theorem) adversary, so their wrappers lift the theorem game
    file's ``Initialize`` and use the outer adversary type.
    """
    if isinstance(step.challenger, frog_ast.ConcreteGame) and step.reduction is None:
        return step.challenger.game.name
    return outer_game_file_name


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


def _rename_proc_call_modules(proc: ec_ast.Proc, rename: dict[str, str]) -> ec_ast.Proc:
    """Return a copy of ``proc`` with each call's callee module-prefix renamed
    per ``rename`` (e.g. a scheme functor param ``K`` -> its concrete arg
    ``KEM_PQ``). Used so the synthesized ``<Scheme>_decaps_val`` lemma's ev-ops
    and ``_det`` peels resolve against the declared clones even when the scheme's
    parameter names differ from the instantiation arguments."""

    def _fix(stmt: ec_ast.EcStmt) -> ec_ast.EcStmt:
        if isinstance(stmt, ec_ast.Call):
            mod, dot, method = stmt.callee.partition(".")
            if dot and mod in rename:
                return ec_ast.Call(stmt.var, f"{rename[mod]}.{method}", stmt.args)
        return stmt

    return ec_ast.Proc(
        name=proc.name,
        params=proc.params,
        return_type=proc.return_type,
        body=[_fix(s) for s in proc.body],
    )


def _reduction_arg_expr(
    param: frog_ast.Parameter,
    instance_module_expr: dict[str, str],
    primary_ctor_name: str,
    primary_module_expr: str,
) -> str:
    """Module expression passed to a reduction parameter, in declaration order.

    A parameter whose name is itself a scheme instance (``R1(CE, E1, E2)``)
    maps to that instance's module expression. A parameter whose name is not
    an instance but whose type is the primary scheme/primitive (the
    primitive-only case ``Reduction R1(SymEnc se)`` applied as ``R1(proofE)``)
    maps to the primary module expression. Otherwise the name is emitted
    verbatim.
    """
    if param.name in instance_module_expr:
        return instance_module_expr[param.name]
    if (
        isinstance(param.type, frog_ast.Variable)
        and param.type.name == primary_ctor_name
    ):
        return primary_module_expr
    return param.name


def _ec_module_ident(name: str) -> str:
    """Uppercase-initial form of ``name`` for use as an EC module identifier.

    EC theory/module/functor-parameter names must begin with an uppercase
    letter. Identity when ``name`` already starts uppercase (so the common
    uppercase-instance corpus is untouched).
    """
    return name[:1].upper() + name[1:] if name else name


class _NameRenamer(visitors.Transformer):
    """Rename free ``Variable`` references according to a name map.

    Used to propagate scheme/primitive-instance and reduction-parameter
    renames (lowercase -> uppercase-initial) through expression positions.
    Field/Parameter/let ``name`` *strings* are renamed separately by the
    caller (they are plain attributes, not ``Variable`` nodes).
    """

    def __init__(self, rename: dict[str, str]) -> None:
        self.rename = rename

    def transform_variable(self, variable: frog_ast.Variable) -> frog_ast.ASTNode:
        renamed = self.rename.get(variable.name)
        return frog_ast.Variable(renamed) if renamed is not None else variable


def _normalize_ec_module_names(
    proof: frog_ast.ProofFile,
    primitives_by_name: dict[str, frog_ast.Primitive],
    schemes_by_name: dict[str, frog_ast.Scheme],
) -> dict[str, str]:
    """Rename lowercase EC-module identifiers in ``proof`` to uppercase-initial.

    Two families of names are emitted verbatim as EC module identifiers and so
    must start with an uppercase letter:

    * **Scheme/primitive instances** (``let`` bindings whose type names a
      scheme or primitive, e.g. ``SymEnc proofE = SymEnc(...)``). Their name
      becomes the clone alias (``proofE_c``), the section ``declare module``
      name, and the module expression threaded through games/reductions/
      wrappers. Renamed across the theorem, assumptions, steps, and other
      let values (which may reference the instance).
    * **Module-typed reduction parameters** (``Reduction R1(SymEnc se)``).
      The parameter becomes an EC functor parameter (``module R1 (se : ...)``)
      and is referenced in the reduction body / its ``compose`` + ``against``
      clauses. Renamed locally within each reduction.

    Mutates ``proof`` in place. A no-op for the all-uppercase corpus.
    """
    module_type_names = set(primitives_by_name) | set(schemes_by_name)

    # --- Instances (top-level lets whose type names a scheme/primitive) ---
    instance_rename: dict[str, str] = {}
    existing_let_names = {let.name for let in proof.lets}
    for let in proof.lets:
        if not (isinstance(let.type, frog_ast.Variable) and let.name[:1].islower()):
            continue
        if let.type.name not in module_type_names:
            continue
        new_name = _ec_module_ident(let.name)
        if new_name == let.name or new_name in existing_let_names:
            continue  # already uppercase, or would collide -- leave as-is
        instance_rename[let.name] = new_name
        existing_let_names.add(new_name)

    if instance_rename:
        renamer = _NameRenamer(instance_rename)
        for let in proof.lets:
            if let.name in instance_rename:
                let.name = instance_rename[let.name]
            if let.value is not None:
                let.value = renamer.transform(let.value)
        proof.theorem = renamer.transform(proof.theorem)
        proof.assumptions = [renamer.transform(a) for a in proof.assumptions]
        proof.steps = [renamer.transform(s) for s in proof.steps]

    # --- Module-typed reduction parameters (local to each reduction) ---
    for helper in proof.helpers:
        if not isinstance(helper, frog_ast.Reduction):
            continue
        param_rename: dict[str, str] = {}
        local_names = {p.name for p in helper.parameters}
        for param in helper.parameters:
            if not (
                isinstance(param.type, frog_ast.Variable) and param.name[:1].islower()
            ):
                continue
            if param.type.name not in module_type_names:
                continue
            new_name = _ec_module_ident(param.name)
            if new_name == param.name or new_name in local_names:
                continue
            param_rename[param.name] = new_name
            local_names.add(new_name)
        if not param_rename:
            continue
        prenamer = _NameRenamer(param_rename)
        for param in helper.parameters:
            if param.name in param_rename:
                param.name = param_rename[param.name]
        helper.to_use = prenamer.transform(helper.to_use)
        helper.play_against = prenamer.transform(helper.play_against)
        helper.methods = [prenamer.transform(m) for m in helper.methods]

    # --- Module-typed concrete-scheme parameters (local to each scheme) ---
    # A concrete scheme like ``Scheme DoubleSymEnc(SymEnc s)`` emits its own
    # parameter verbatim as an EC functor param (``module DoubleSymEnc (s :
    # ...)``) and references it in the body (``s.keygen()``). EC functor
    # params must start uppercase, so rename ``s -> S`` (mirroring the
    # reduction-parameter branch above). The argument names threaded into the
    # functor *application* are instance let-names, renamed separately, so the
    # scheme's own param rename stays local to its definition + body.
    for scheme in schemes_by_name.values():
        _normalize_scheme_module_params(scheme, module_type_names)

    return instance_rename


def _normalize_scheme_module_params(
    scheme: frog_ast.Scheme, module_type_names: set[str]
) -> None:
    """Uppercase a concrete scheme's lowercase module-typed parameters.

    Renames each parameter whose type names a primitive/scheme and whose own
    name starts lowercase (so it would emit an invalid EC functor-param
    identifier) to its uppercase-initial form, propagating the rename through
    the scheme's fields, requirements, and method bodies via ``_NameRenamer``.
    Idempotent for the all-uppercase corpus (a no-op when no param matches).
    """
    param_rename: dict[str, str] = {}
    local_names = {p.name for p in scheme.parameters}
    for param in scheme.parameters:
        if not (isinstance(param.type, frog_ast.Variable) and param.name[:1].islower()):
            continue
        if param.type.name not in module_type_names:
            continue
        new_name = _ec_module_ident(param.name)
        if new_name == param.name or new_name in local_names:
            continue
        param_rename[param.name] = new_name
        local_names.add(new_name)
    if not param_rename:
        return
    renamer = _NameRenamer(param_rename)
    for param in scheme.parameters:
        if param.name in param_rename:
            param.name = param_rename[param.name]
    scheme.fields = [renamer.transform(f) for f in scheme.fields]
    scheme.requirements = [renamer.transform(r) for r in scheme.requirements]
    scheme.methods = [renamer.transform(m) for m in scheme.methods]


def _group_only_type_of_factory(
    method_return_types: dict[tuple[str, str], frog_ast.Type],
) -> Callable[
    [dict[str, frog_ast.Type], dict[str, str]],
    Callable[[frog_ast.Expression], frog_ast.Type],
]:
    """A ``type_of`` factory covering the shapes group-only game/reduction
    bodies use: variables, oracle-method calls (``challenger.Initialize()``),
    the group constants ``G.generator``/``G.identity``, tuple projections,
    group/ring binary ops, and integer literals."""

    def type_of_factory(
        local_types: dict[str, frog_ast.Type],
        module_param_types: dict[str, str],
    ) -> Callable[[frog_ast.Expression], frog_ast.Type]:
        def type_of(e: frog_ast.Expression) -> frog_ast.Type:
            if isinstance(e, frog_ast.Variable):
                if e.name in local_types:
                    return local_types[e.name]
                # An engine-inlined / canonicalized field reference keeps its
                # raw FrogLang name (``challenger@HT``, ``QT``) while its
                # declaration was seeded under the EC-mangled form
                # (``challenger_HT``, ``v_QT``). Fall back to the mangled name
                # (``canonical_form._ec_ident`` is the mangling the flat-state
                # renamer applied). No-op for an already-valid EC identifier.
                mangled = canonical_form._ec_ident(
                    e.name
                )  # pylint: disable=protected-access
                if mangled != e.name and mangled in local_types:
                    return local_types[mangled]
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
                        rt = method_return_types[key]
                        # A bare carrier return type (``Element`` from
                        # ``NG.Exp``) must be qualified by the instance so it
                        # resolves through the alias map (``NG.Element`` ->
                        # ``NGElementSpace``); an unqualified ``Element`` has no
                        # top-level alias. Only surfaces when the call's type is
                        # needed directly (e.g. hoisting it out of an expr).
                        if isinstance(rt, frog_ast.Variable):
                            return frog_ast.FieldAccess(
                                frog_ast.Variable(obj.name), rt.name
                            )
                        return rt
            if isinstance(e, frog_ast.FieldAccess) and e.name in (
                "generator",
                "identity",
            ):
                return frog_ast.GroupElemType(e.the_object)
            if isinstance(e, frog_ast.ArrayAccess) and isinstance(
                e.index, frog_ast.Integer
            ):
                base = type_of(e.the_array)
                if isinstance(base, frog_ast.ProductType) and 0 <= e.index.num < len(
                    base.types
                ):
                    return base.types[e.index.num]
            if isinstance(e, frog_ast.BinaryOperation):
                # Group/ring ops (``*``/``/``/``^``/``+``/``-``) return their
                # left operand's type.
                return type_of(e.left_expression)
            if isinstance(e, frog_ast.Integer):
                return frog_ast.IntType()
            raise NotImplementedError(
                f"group-only type_of not implemented for {type(e).__name__}"
            )

        return type_of

    return type_of_factory


def _group_only_scaffold(  # pylint: disable=too-many-locals
    steps: list[frog_ast.Step],
    thm_adv: str,
    ch_type: str,
    assm_ids: set[str],
) -> list[str]:
    """Per-step game wrappers, assumption epsilons, admit hop lemmas, and the
    main theorem for a group-only proof.

    This is the scaffolding *around* the translator-produced games/reductions:
    each step becomes a ``Game_step_i`` presenting the theorem oracle (init then
    a single ``distinguish`` over the post-init oracle); a hop between two steps
    of the same assumption game + reduction (differing only by side) is bounded
    by that game's ``eps_<gf>`` axiom, every other hop is an admitted equality;
    the main theorem sums the assumption epsilons. Every hop body is an
    ``admit`` -- closing them is the structural-blocker cluster's job.
    """

    def _oracle_expr(step: frog_ast.Step) -> str:
        cg = step.challenger
        assert isinstance(cg, frog_ast.ConcreteGame)
        base = f"{_ec_ident(cg.game.name)}_{cg.which}"
        if step.reduction is not None:
            return f"{_ec_ident(step.reduction.name)}({base})"
        return base

    def _assumption_eps(a: frog_ast.Step, b: frog_ast.Step) -> str | None:
        ca = a.challenger
        cb = b.challenger
        if not isinstance(ca, frog_ast.ConcreteGame):
            return None
        if not isinstance(cb, frog_ast.ConcreteGame):
            return None
        if _ec_ident(ca.game.name) != _ec_ident(cb.game.name):
            return None
        ra = a.reduction.name if a.reduction else None
        rb = b.reduction.name if b.reduction else None
        if ra != rb or ca.which == cb.which:
            return None
        if _ec_ident(ca.game.name) not in assm_ids:
            return None
        return f"eps_{_ec_ident(ca.game.name)}"

    scaffold: list[str] = []
    for i, step in enumerate(steps):
        oexpr = _oracle_expr(step)
        scaffold.append(
            f"module Game_step_{i} (A : {thm_adv}) = {{\n"
            f"  proc main() : bool = {{\n"
            f"    var b : bool;\n"
            f"    var ch : {ch_type};\n"
            f"    ch <@ {oexpr}.initialize();\n"
            f"    b <@ A({oexpr}).distinguish(ch);\n"
            f"    return b;\n"
            f"  }}\n"
            f"}}."
        )

    hop_eps: list[str | None] = [
        _assumption_eps(steps[i], steps[i + 1]) for i in range(len(steps) - 1)
    ]
    eps_ids = sorted({eps for eps in hop_eps if eps is not None})
    for eps in eps_ids:
        scaffold.append(f"op {eps} : real.\naxiom {eps}_pos : 0%r <= {eps}.")

    # Each hop body is an open ``admit`` -- emitted as a *standalone* ``admit.``
    # line plus an ``admit-unguided`` resolution tag, so the dashboard counts it
    # honestly (the proof EC-compiles WITH admits -> ``warn``, never ``clean``;
    # a single-line ``proof. admit. qed.`` would slip past the admit scan and
    # mis-report the proof as clean -- principle 2's worst case).
    admit_body = f"proof.\n  {_res_tag(ADMIT_UNGUIDED)}\n  admit.\nqed."
    for i, hop in enumerate(hop_eps):
        if hop is not None:
            scaffold.append(
                f"lemma hop_{i}_pr (A <: {thm_adv}) &m :\n"
                f"  `| Pr[Game_step_{i}(A).main() @ &m : res]\n"
                f"   - Pr[Game_step_{i + 1}(A).main() @ &m : res] | <= {hop}.\n"
                f"{admit_body}"
            )
        else:
            scaffold.append(
                f"lemma hop_{i}_pr (A <: {thm_adv}) &m :\n"
                f"  Pr[Game_step_{i}(A).main() @ &m : res]\n"
                f"  = Pr[Game_step_{i + 1}(A).main() @ &m : res].\n"
                f"{admit_body}"
            )

    # The triangle-inequality bound sums one epsilon per assumption hop, *with
    # repetition* (a proof may invoke the same assumption twice, e.g. GapCDH's
    # two NonzeroSampling hops) -- distinct ``eps_ids`` are only for the op /
    # axiom declarations and smt hints.
    bound_terms = [eps for eps in hop_eps if eps is not None]
    bound = " + ".join(bound_terms) if bound_terms else "0%r"
    haves = "\n".join(f"  have h{i} := hop_{i}_pr A &m." for i in range(len(steps) - 1))
    smt_hints = " ".join(f"{eps}_pos" for eps in eps_ids)
    scaffold.append(
        f"lemma main_theorem (A <: {thm_adv}) &m :\n"
        f"  `| Pr[Game_step_0(A).main() @ &m : res]\n"
        f"   - Pr[Game_step_{len(steps) - 1}(A).main() @ &m : res] | <= {bound}.\n"
        f"proof.\n{haves}\n  smt({smt_hints}).\nqed."
    )
    return scaffold


def _export_group_only(  # pylint: disable=too-many-locals
    proof: frog_ast.ProofFile,
    game_files: list[frog_ast.GameFile],
    group_let_name: str,
) -> str:
    """Export a *group-only* proof (no scheme/primitive) to EC source.

    The games and reductions are emitted at top level over a ``clone
    CyclicGroup as <G>`` (plus the gated exponent-ring clone), with no
    ``<primitive>_Theory`` wrapper and no ``Em : Scheme`` module parameter --
    the structure validated in ``.ec-tmp/DDH_implies_CDH.target.ec`` (see the
    Group-skeleton implementation plan, Task B.0). Game/reduction *bodies* are
    faithfully translated from the FrogLang ASTs by the existing translators;
    the per-step wrappers, assumption epsilons, hop lemmas and the main theorem
    are emitted as scaffolding with guided ``admit`` hop bodies (export-only
    goal for the DDH/CDH implication family -- closing the hops is the
    structural-blocker cluster's job).
    """
    prime_groups = _prime_group_names(proof)

    # Bind each game file's non-group parameters to their instantiation
    # argument. ``RandomTargetGuessing(GroupElem<G>)`` instantiates the helper
    # game ``Real(Set S)`` with ``S = GroupElem<G>``; the bodies/signatures then
    # render ``S`` as ``G.group``. ``Group G`` params are the top-level clone,
    # never a value type, so they are skipped.
    game_file_by_id = {_ec_ident(gf.name): gf for gf in game_files}
    carrier_aliases: dict[str, frog_ast.Type] = {}
    refs: list[frog_ast.ParameterizedGame] = list(proof.assumptions)
    if isinstance(proof.theorem, frog_ast.ParameterizedGame):
        refs.append(proof.theorem)
    for ref in refs:
        gf = game_file_by_id.get(_ec_ident(ref.name))
        if gf is None:
            continue
        for param, arg in zip(gf.games[0].parameters, ref.args):
            if not isinstance(param.type, frog_ast.GroupType) and isinstance(
                arg, frog_ast.Type
            ):
                carrier_aliases[param.name] = arg

    top_types = tc.TypeCollector(
        aliases=carrier_aliases, prime_group_names=prime_groups
    )
    top_types.translate_type(frog_ast.GroupElemType(frog_ast.Variable(group_let_name)))

    # (oracle_type, method) -> return type, for the body translators' type_of.
    method_return_types: dict[tuple[str, str], frog_ast.Type] = {}
    for gf in game_files:
        oracle_type = f"{_ec_ident(gf.name)}_Oracle"
        for game_method in gf.games[0].methods:
            method_return_types[(oracle_type, game_method.signature.name)] = (
                game_method.signature.return_type
            )

    modules = mt.ModuleTranslator(
        top_types, _group_only_type_of_factory(method_return_types)
    )

    def _init_method(gf: frog_ast.GameFile) -> frog_ast.Method:
        return next(
            m for m in gf.games[0].methods if m.signature.name.lower() == "initialize"
        )

    # --- Oracle types + game modules (top level, no scheme param) ---
    game_decls: list[ec_ast.EcTopDecl] = []
    for gf in game_files:
        gf_id = _ec_ident(gf.name)
        oracle_type_name = f"{gf_id}_Oracle"
        game_decls.append(modules.translate_game_file_oracle(gf, oracle_type_name))
        for side in gf.games:
            mod = modules.translate_game(
                side,
                f"{gf_id}_{side.name}",
                param_type_name=group_let_name,
                implements=oracle_type_name,
                emitted_param_type=group_let_name,
                emit_state_vars=True,
            )
            # Drop the ``Group G`` module parameter: the group is the top-level
            # clone, referenced directly by the body, not a functor argument.
            game_decls.append(
                ec_ast.Module(
                    name=mod.name,
                    procs=mod.procs,
                    params=[],
                    implements=mod.implements,
                    module_vars=mod.module_vars,
                )
            )

    # --- Adversary type for the theorem game ---
    assert isinstance(proof.theorem, frog_ast.ParameterizedGame)
    thm_id = _ec_ident(proof.theorem.name)
    thm_gf = next(gf for gf in game_files if _ec_ident(gf.name) == thm_id)
    thm_adv = f"{thm_id}_Adv"
    thm_multi_oracle = modules.multi_oracle_spec(
        thm_gf, oracle_model.classify_game_file(thm_gf)
    )
    game_decls.append(
        modules.translate_adversary_type(
            thm_gf,
            f"{thm_id}_Oracle",
            adv_type_name=thm_adv,
            multi_oracle=thm_multi_oracle,
        )
    )

    # --- Reductions (Group param filtered out by translate_reduction) ---
    reductions = [h for h in proof.helpers if isinstance(h, frog_ast.Reduction)]
    for red in reductions:
        composed_oracle = f"{_ec_ident(red.to_use.name)}_Oracle"
        game_decls.append(
            modules.translate_reduction(
                red,
                primitive_name=group_let_name,
                oracle_type_name=composed_oracle,
                allow_void_call=True,
            )
        )

    # --- Per-step wrappers + assumption epsilons + hop lemmas + theorem ---
    steps = [s for s in proof.steps if isinstance(s, frog_ast.Step)]
    if len(steps) != len(proof.steps):
        raise ValueError(
            "group-only export does not support Induction / StepAssumption "
            "steps (out of scope -- see principle 5)."
        )
    ch_type = top_types.translate_type(_init_method(thm_gf).signature.return_type).text
    assm_ids = {_ec_ident(a.name) for a in proof.assumptions}
    scaffold = _group_only_scaffold(steps, thm_adv, ch_type, assm_ids)

    decls: list[ec_ast.EcTopDecl] = [
        *top_types.emit(),
        *game_decls,
        *scaffold,
    ]
    stdlib_requires = (
        ["Group", "ZModP", "List"] if top_types.has_stdlib_group_or_modint() else []
    )
    # ``Dexcepted`` provides the ``d \ P`` exclusion distribution for a one-shot
    # exclusion draw (``x <- T \ {..}``). Required only when one was emitted, so
    # exclusion-free exports stay byte-identical.
    dexcepted_requires = ["Dexcepted"] if top_types.needs_dexcepted else []
    ec_file = ec_ast.EcFile(
        requires=[
            "AllCore",
            "Distr",
            "DProd",
            "DMap",
            *stdlib_requires,
            *dexcepted_requires,
        ],
        decls=decls,
    )
    return ec_ast.pretty_print(ec_file)


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

    if not game_files:
        raise ValueError("Exporter requires at least one GameFile import.")

    # Group-only proofs (no scheme/primitive import; the theorem attacks a game
    # parameterized by a ``Group`` math structure -- e.g. ``DDH_implies_CDH``)
    # have no primitive theory. They take a dedicated top-level export path that
    # emits the games/reductions over the cloned group, leaving the entire
    # primitive-theory orchestration below untouched (so existing exports stay
    # byte-identical).
    if not schemes_by_name and not primitives_by_name:
        group_let_name = _group_only_let_name(proof)
        if group_let_name is not None:
            return _export_group_only(proof, game_files, group_let_name)
        raise ValueError("Exporter requires a Scheme or Primitive import.")

    # EC requires theory/module names to begin with an uppercase letter, but
    # the exporter emits scheme/primitive instance let-names and module-typed
    # reduction parameters verbatim as EC module identifiers (clone alias,
    # ``declare module``, functor parameters). Rename any lowercase such name
    # to an uppercase-initial form throughout the proof AST *before* the
    # engine inlines and the exporter emits, so every EC reference agrees.
    # Keep the PRE-rename proof for the engine validation below: the rename is
    # a purely cosmetic EC-naming pass, but it is applied to the theorem/steps
    # and NOT the reduction helpers, which leaves a reduction that holds a
    # packed scheme-typed field (Universal-combiner ``hybrid.DecapsKey``)
    # unresolvable -> the internal ``engine.prove`` FailedProofs even though the
    # proof verifies. Validate the consistent pre-rename proof instead.
    proof_for_validation = copy.deepcopy(proof)
    instance_rename = _normalize_ec_module_names(
        proof, primitives_by_name, schemes_by_name
    )

    # The primary instance is the one whose instance appears in the theorem.
    # For ``theorem: PRGSecurity(H)`` with ``PRG_5_10 H = PRG_5_10(G);``,
    # the primary let is H and the primary scheme is PRG_5_10. The primary's
    # declared *type* is usually a Scheme; for a primitive-security proof
    # (``theorem: INDOT(proofE)`` with ``SymEnc proofE = SymEnc(...)``) it is
    # a Primitive instantiated directly with its carrier sets. In that
    # primitive-only case there is no concrete scheme body to translate: the
    # primary becomes an abstract section ``declare module`` (the proof holds
    # for every primitive satisfying the assumption).
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
    primary_type_name: str | None = None
    primary_value_ctor: str | None = None
    for let in proof.lets:
        if let.name == primary_let_name and isinstance(let.type, frog_ast.Variable):
            primary_type_name = let.type.name
            if isinstance(let.value, frog_ast.FuncCall) and isinstance(
                let.value.func, frog_ast.Variable
            ):
                primary_value_ctor = let.value.func.name
            break
    scheme: frog_ast.Scheme | None
    if primary_type_name is not None and primary_type_name in schemes_by_name:
        scheme = schemes_by_name[primary_type_name]
        if scheme.primitive_name not in primitives_by_name:
            raise ValueError(
                f"Primary scheme {scheme.name!r} extends primitive "
                f"{scheme.primitive_name!r}, which was not imported."
            )
        primitive = primitives_by_name[scheme.primitive_name]
    elif (
        primary_type_name is not None
        and primary_type_name in primitives_by_name
        and not proof.assumptions
        and primary_value_ctor is not None
        and primary_value_ctor in schemes_by_name
    ):
        # Primitive-typed let bound to a *concrete scheme* constructor in an
        # unconditional proof (e.g. ``SymEnc E = ModOTP(q);`` with no
        # ``assume:``). The engine inlines the scheme body into the flat
        # states, so the wrapper-to-flat bridge needs a concrete EC module
        # (``module ModOTP``) that ``inline *`` can unfold -- an abstract
        # section ``declare module`` cannot. Treat it as a concrete-scheme
        # primary, resolving the scheme from the RHS constructor rather than
        # the declared interface type. (Assumption proofs keep E abstract: the
        # result holds for every scheme meeting the assumption.)
        scheme = schemes_by_name[primary_value_ctor]
        if scheme.primitive_name not in primitives_by_name:
            raise ValueError(
                f"Primary scheme {scheme.name!r} extends primitive "
                f"{scheme.primitive_name!r}, which was not imported."
            )
        primitive = primitives_by_name[scheme.primitive_name]
    elif primary_type_name is not None and primary_type_name in primitives_by_name:
        # Primitive-only proof: the module under attack is an abstract
        # primitive instance, not a concrete scheme.
        scheme = None
        primitive = primitives_by_name[primary_type_name]
    else:
        raise ValueError(
            f"Could not identify primary scheme or primitive from theorem "
            f"instance {primary_let_name!r}."
        )
    # In primitive-only mode the primary scheme module is emitted abstractly
    # (a section ``declare module``) rather than as a concrete EC module.
    primitive_only = scheme is None
    # The type name the primary instance's let must match to be selected as
    # the primary scheme instance (a Scheme name, or the Primitive name).
    primary_ctor_name = scheme.name if scheme is not None else primitive.name

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

    # Per-declared-module deterministic-method sets, for the chain emitter's
    # deterministic same-module-reorder route (functionalize det calls to their
    # ``ev_<m>`` form via the ``<M>_<m>_det`` axioms). Keyed by the instance
    # let-name (the declared module name that appears as an EC call callee).
    det_methods_by_module: dict[str, set[str]] = {}
    for _inst in instances:
        _prim = primitives_by_name.get(_inst.primitive_name)
        if _prim is None:
            continue
        det_methods_by_module[_inst.let_name] = {
            m.name.lower() for m in _prim.methods if m.deterministic
        }
    # let-name -> ``ev_<m>`` clone prefix (``KEM_PQ`` -> ``KEM_PQ_c``): the
    # namespace of a declared module's functional ops, for the binding challenge
    # case-split synthesizer.
    clone_alias_by_module: dict[str, str] = {
        _inst.let_name: _inst.clone_alias for _inst in instances
    }

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

    # Oracle data model per game file (multi-oracle foundation). Built here,
    # before module emission, so the adversary-type / game-wrapper emitters can
    # request a per-game-file ``MultiOracleSpec``. Single-oracle games yield no
    # spec, so their adversary types and wrappers stay byte-identical.
    oracle_model_by_game_file: dict[str, oracle_model.GameOracleModel] = {
        gf.name: oracle_model.classify_game_file(gf) for gf in game_files
    }
    game_file_by_name: dict[str, frog_ast.GameFile] = {gf.name: gf for gf in game_files}

    def multi_oracle_spec_for(
        modules: mt.ModuleTranslator,
        game_file_name: str,
        scheme_args: list[frog_ast.Expression] | None = None,
    ) -> mt.MultiOracleSpec | None:
        """``MultiOracleSpec`` for a game file in ``modules``' type scope.

        ``None`` for single-oracle game files (the emitters then take their
        byte-identical legacy path). ``scheme_args`` binds the game's formal
        scheme parameter(s) to the actual instantiation so the ``Initialize``
        return type resolves against the right scheme (see
        ``ModuleTranslator.multi_oracle_spec``) -- needed at top-level scope
        when the game's formal param name collides with a different proof let.
        """
        return modules.multi_oracle_spec(
            game_file_by_name[game_file_name],
            oracle_model_by_game_file[game_file_name],
            scheme_args=scheme_args,
        )

    # "Primary" instance: the one bound to the theorem's target let-name.
    # For OTPSecure this is ``E`` (OTP); for CES it is ``CE``
    # (ChainedEncryption). Used for scheme-body translation and as the
    # clone alias threaded through the existing single-scheme code paths.
    # Keying off the theorem target's let-name (rather than matching the
    # declared let type against ``primary_ctor_name``) handles the case where
    # the declared interface type differs from the resolved scheme ctor --
    # e.g. ``SymEnc E = ModOTP(q);`` resolves ``primary_ctor_name`` to the
    # concrete scheme ``ModOTP`` while the let type stays ``SymEnc``.
    primary_opt: si.SchemeInstance | None = None
    for inst in instances:
        if inst.let_name == primary_let_name:
            primary_opt = inst
            break
    if primary_opt is None:
        raise ValueError(
            "No scheme instance found matching the main scheme/primitive "
            f"{primary_ctor_name!r} in proof lets."
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
        #
        # A scheme wrapping a sub-primitive (``KEM_PQ = SeededKEMWrapper(
        # KEM_PQ_inner)``) has a field that references the wrapper's PARAM's
        # length directly (``Set DecapsKey = BitString<K_inner.Nseed>``). The
        # param is not a let, so ``int_qual_map`` (keyed ``<let>.<int>``) leaves
        # ``K_inner.Nseed`` unresolved -> an invalid ``bs_K_inner_Nseed`` in every
        # consumer of this field alias. Bind each scheme param to its
        # instantiation arg and alias ``<param>.<int>`` to the ALREADY-resolved
        # ``<arg>.<int>`` base value; only ADDS keys, so an instance without such
        # a param-length field reference is byte-identical.
        let_value = next((l.value for l in proof.lets if l.name == inst.let_name), None)
        aug_int_qual_map = _param_aliased_int_qual_map(
            schemes_by_name.get(inst.ctor_name), let_value, int_qual_map
        )
        inst_inliner = _LengthInliner(
            param_int_by_let.get(inst.let_name, {}), aug_int_qual_map
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
    # Qualified aliases for a concrete scheme's module-typed parameters.
    # ``Scheme DoubleSymEnc(SymEnc S)`` refers to its sub-scheme's carrier
    # types as ``S.Key``/``S.Message``/... in local var decls (``s.Key key1 =
    # s.KeyGen();``). Those must resolve to the *passed instance's* carriers
    # (``E.Key``, ...), not the scheme's own same-named field -- whose bare
    # alias (``Key`` -> the pair ``[s.Key, s.Key]``) would otherwise capture
    # ``S.Key`` via the unqualified fallback and mistype the local. Map each
    # ``<param>.<field>`` to the same carrier as the applied instance's
    # ``<arg>.<field>``.
    module_type_names = set(primitives_by_name) | set(schemes_by_name)
    primary_let_value = next(
        let.value for let in proof.lets if let.name == primary.let_name
    )
    if scheme is not None and isinstance(primary_let_value, frog_ast.FuncCall):
        for sp, arg in zip(scheme.parameters, primary_let_value.args):
            if not (
                isinstance(sp.type, frog_ast.Variable)
                and sp.type.name in module_type_names
                and isinstance(arg, frog_ast.Variable)
            ):
                continue
            arg_prefix = f"{arg.name}."
            for key in list(top_aliases):
                if key.startswith(arg_prefix):
                    field = key[len(arg_prefix) :]
                    top_aliases[f"{sp.name}.{field}"] = top_aliases[key]
    # Qualified integer-field aliases (``KEM_PQ.Nss`` -> ``kem_pq_nss``). A
    # bitstring length can surface a primitive int field when a hoisted call
    # temp is typed by a method's RAW return signature ``BitString<Nss>`` and
    # that ``Nss`` is qualified to the calling instance (``KEM_PQ.Nss``) in the
    # ``type_of`` FuncCall branch below; without this alias it would strip to a
    # bare ``bs_Nss`` and mismatch the length-inlined ``bs_kem_pq_nss`` the rest
    # of the module (and the registered concat ops) use. Qualified keys never
    # shadow a base ``Int`` let, so this is safe for every proof.
    # ``top_aliases`` holds carrier Types, but these int-length entries are
    # Expressions consumed only by ``_substitute_aliases`` (never resolved as a
    # carrier type), so casting to ``Type`` is sound (``Variable`` is both).
    # A primary scheme instance is renamed to an uppercase EC module ident
    # (``hybrid`` -> ``Hybrid``) so ``int_qual_map`` keys it as ``Hybrid.Nss``,
    # but a length FIELD ACCESS in a flat state keeps the FrogLang lowercase name
    # (``BitString<hybrid.Nss>``, a value context the module rename doesn't
    # touch). Seed the alias under the ORIGINAL name too so it inlines.
    _rev_instance_rename = {v: k for k, v in instance_rename.items()}
    for _qk, _qv in int_qual_map.items():
        if not isinstance(_qv, frog_ast.Expression):
            continue
        top_aliases.setdefault(_qk, cast(frog_ast.Type, _qv))
        _inst_part, _dot, _field_part = _qk.partition(".")
        if _dot and _inst_part in _rev_instance_rename:
            top_aliases.setdefault(
                f"{_rev_instance_rename[_inst_part]}.{_field_part}",
                cast(frog_ast.Type, _qv),
            )
    # Bare integer-field aliases (``Nss`` -> ``kem_pq_nss``) for a field owned by
    # exactly ONE instance and not itself a base ``Int`` let. A bitstring length
    # can surface a bare primitive field from many ``type_of`` paths -- a method
    # return ``BitString<Nss>``, a slice bound, a concat operand -- so qualifying
    # each site is whack-a-mole; instead inline the bare name at this single
    # choke point (the flat-state alias map) so every path renders the
    # length-inlined ``bs_kem_pq_nss`` that the registered concat ops carry,
    # never a stray ``bs_Nss``. ``int_qual_map`` values are already base-resolved
    # (no re-doubling), and excluding base-let names sidesteps the shadow hazard
    # the qualified-only map was built around. Ambiguous fields (a name two
    # instances both own) stay bare -- those need per-site qualification, out of
    # scope here.
    _base_int_lets = {
        let.name for let in proof.lets if isinstance(let.type, frog_ast.IntType)
    }
    _bare_field_bases: dict[str, list[frog_ast.Expression]] = {}
    for _qk, _qv in int_qual_map.items():
        if "." not in _qk or not isinstance(_qv, frog_ast.Expression):
            continue
        _bare_field_bases.setdefault(_qk.split(".", 1)[1], []).append(_qv)
    for _field, _vals in _bare_field_bases.items():
        if _field in _base_int_lets or _field in top_aliases or len(_vals) != 1:
            continue
        top_aliases[_field] = cast(frog_ast.Type, _vals[0])
    prime_groups = _prime_group_names(proof)
    top_types = tc.TypeCollector(
        aliases=top_aliases,
        known_abstract_types=known_abstract_types,
        prime_group_names=prime_groups,
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

    # A game file may carry ``Set``-typed formal parameters alongside its
    # primitive parameter -- the random-oracle IND-CCA game
    # ``Real(KEM K, Set D, Set R, Function<D,R> H)`` names its hash domain
    # ``D`` and range ``R`` as abstract sets. Inside the abstract theory these
    # are abstract types (``type d.`` / ``type r.``), exactly like a primitive
    # Set-field carrier; the theorem instantiation (``BitString<hybrid.Nin>``
    # etc.) binds them at the concrete-clone site. Register them here so an
    # oracle signature ``hash(m : D) : R`` translates instead of crashing on
    # ``Variable: D``. Byte-identical for every game file whose only non-Int
    # parameter is the primitive one (no Set params -> no map entries).
    for gf in primary_game_files:
        for gp in gf.games[0].parameters:
            if (
                isinstance(gp.type, frog_ast.SetType)
                and gp.name not in abstract_types_map
            ):
                abstract_types_map[gp.name] = gp.name.lower()

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

    # A ``Function<D,R> H`` game param / proof let is the shared random-oracle
    # function; it is referenced as an op (``v_H m``) but nothing samples it, so
    # its value needs an ``op`` declaration in each scope it appears. The
    # abstract theory game uses ``op v_H : d -> r`` (from the game's own
    # Function param, whose D/R resolve to the abstract ``d``/``r``); section
    # Main's concrete flat states use ``op v_H : bs_... -> bs_Nout`` (from the
    # proof's Function let, whose D/R are concrete). Register both. Byte-
    # identical for a proof with no Function-typed let (no ROM hash oracle).
    theorem_game_file = next(
        (gf for gf in game_files if gf.name == proof.theorem.name), None
    )
    # pylint: disable=protected-access
    if theorem_game_file is not None:
        for gparam in theorem_game_file.games[0].parameters:
            if isinstance(gparam.type, frog_ast.FunctionType):
                theory_types.register_function_value(
                    canonical_form._ec_ident(gparam.name), gparam.type
                )
    for proof_let in proof.lets:
        if isinstance(proof_let.type, frog_ast.FunctionType):
            top_types.register_function_value(
                canonical_form._ec_ident(proof_let.name), proof_let.type
            )
    # pylint: enable=protected-access

    # A ``Function<D,R>`` shared random oracle (a proof let or the theorem
    # game's own param) marks a ROM proof. Its multi-oracle chains get CANONICAL
    # f<NN> flat-state field naming, PROOF-WIDE: the glob-by-name misalignment
    # the rename fixes lives in the hash oracle's EARLY hops too, whose states
    # carry no ``fmap`` RO-table field yet (the table is inlined only in later
    # hops), so a per-chain "has a map field" gate would miss them. Binding /
    # correctness proofs have no Function-typed RO, so this stays False and every
    # such export is byte-identical.
    proof_uses_ro_function = any(
        isinstance(pl.type, frog_ast.FunctionType) for pl in proof.lets
    ) or (
        theorem_game_file is not None
        and any(
            isinstance(gp.type, frog_ast.FunctionType)
            for gp in theorem_game_file.games[0].parameters
        )
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
                # An engine-inlined / canonicalized field reference keeps its
                # raw FrogLang name (``challenger@HT``, ``QT``) while its
                # declaration was seeded under the EC-mangled form
                # (``challenger_HT``, ``v_QT``). Fall back to the mangled name
                # (``canonical_form._ec_ident`` is the mangling the flat-state
                # renamer applied). No-op for an already-valid EC identifier.
                mangled = canonical_form._ec_ident(
                    e.name
                )  # pylint: disable=protected-access
                if mangled != e.name and mangled in local_types:
                    return local_types[mangled]
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
                        rt = method_return_types[key]
                        # A bare carrier return type (``Element`` from
                        # ``NG.Exp``) must be qualified by the instance so it
                        # resolves through the alias map (``NG.Element`` ->
                        # ``NGElementSpace``); an unqualified ``Element`` has no
                        # top-level alias. Only surfaces when the call's type is
                        # needed directly (e.g. hoisting it out of an expr).
                        if isinstance(rt, frog_ast.Variable):
                            return frog_ast.FieldAccess(
                                frog_ast.Variable(obj.name), rt.name
                            )
                        # A ``BitString<Nss>`` return whose length is a bare
                        # primitive int field: qualify it to the calling
                        # instance (``Nss`` -> ``KEM_PQ.Nss``) so the seeded
                        # int-field aliases inline it to the base int
                        # (``kem_pq_nss``) rather than stripping to a bare
                        # ``bs_Nss`` -- which would mismatch the length-inlined
                        # ``bs_kem_pq_nss`` every other use of this width (and
                        # the registered concat ops) carries. Surfaces on a
                        # hoisted call temp typed by the method's raw signature.
                        if (
                            isinstance(rt, frog_ast.BitStringType)
                            and rt.parameterization is not None
                        ):
                            qualified_param = _QualifyFields(
                                obj.name, int_qual_map
                            ).transform(copy.deepcopy(rt.parameterization))
                            return frog_ast.BitStringType(qualified_param)
                        return rt
            if isinstance(e, frog_ast.FieldAccess) and e.name in (
                "generator",
                "identity",
            ):
                # ``G.generator`` / ``G.identity`` are the group's
                # distinguished elements -- typed ``GroupElem<G>`` so the
                # GroupElem foundation renders them as abstract constants.
                return frog_ast.GroupElemType(e.the_object)
            if isinstance(e, frog_ast.Slice):
                # A slice's static type is ``BitString<end - start>``
                # regardless of the source bitstring's length.
                return frog_ast.BitStringType(
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.SUBTRACT, e.end, e.start
                    )
                )
            if isinstance(e, frog_ast.BinaryOperation):
                # Comparison and logical operators always produce ``Bool``,
                # independent of their operand types. Without this they would
                # inherit the LHS operand's type (the fall-through below); when
                # the operands are bitstrings, an enclosing logical ``||`` whose
                # leaves are such comparisons (e.g. a win condition
                # ``a <> b || c <> d``) would then be misread as a bitstring
                # concatenation by ``_bitstring_type_of``, emitting an ill-typed
                # ``concat_* (bool) (bool)``.
                if e.operator in (
                    frog_ast.BinaryOperators.EQUALS,
                    frog_ast.BinaryOperators.NOTEQUALS,
                    frog_ast.BinaryOperators.GT,
                    frog_ast.BinaryOperators.LT,
                    frog_ast.BinaryOperators.GEQ,
                    frog_ast.BinaryOperators.LEQ,
                    frog_ast.BinaryOperators.AND,
                    frog_ast.BinaryOperators.IN,
                    frog_ast.BinaryOperators.SUBSETS,
                ):
                    return frog_ast.BoolType()
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
            if isinstance(e, frog_ast.ArrayAccess) and isinstance(
                e.index, frog_ast.Integer
            ):
                # A tuple projection ``t[i]``: the type is the i-th component of
                # ``t``'s product type. The engine inlines projections into
                # concat (``||``) operands in some flat states (e.g. GHP18's
                # ``sk[2]`` where ``sk : SK1Space * SK2Space * PK1Space *
                # PK2Space``), so the concat detector needs the component type.
                base = type_of(e.the_array)
                if isinstance(base, frog_ast.ProductType) and 0 <= e.index.num < len(
                    base.types
                ):
                    return base.types[e.index.num]
            if isinstance(e, frog_ast.Integer):
                return frog_ast.IntType()
            if isinstance(e, frog_ast.BitStringLiteral):
                return frog_ast.BitStringType(e.length)
            if isinstance(e, frog_ast.Boolean):
                return frog_ast.BoolType()
            if isinstance(e, frog_ast.FuncCall) and isinstance(
                e.func, frog_ast.Variable
            ):
                # A random-function application ``H(m)`` / ``RF(x)``: the callee
                # is a ``Function<D,R>``-typed field or param (rendered as EC's
                # native arrow ``D -> R``), so the call's type is the range
                # ``R``. Surfaces in the ROM ``Hash`` oracle, whose body applies
                # the random function directly.
                try:
                    callee_t: frog_ast.Type | None = type_of(e.func)
                except (KeyError, NotImplementedError):
                    callee_t = None
                if isinstance(callee_t, frog_ast.FunctionType):
                    return callee_t.range_type
            if isinstance(e, frog_ast.ArrayAccess):
                # A map read ``QT[k]`` / ``HT[m]``: the value type of the map.
                # (The Integer-index tuple-projection case is handled above; a
                # map key is a variable or tuple, so the two do not collide.)
                try:
                    base_t: frog_ast.Type | None = type_of(e.the_array)
                except (KeyError, NotImplementedError):
                    base_t = None
                if isinstance(base_t, frog_ast.MapType):
                    return base_t.value_type
            raise NotImplementedError(f"type_of not implemented for {type(e).__name__}")

        return type_of

    theory_modules = mt.ModuleTranslator(theory_types, type_of_factory)
    top_modules = mt.ModuleTranslator(top_types, type_of_factory)

    # Clone alias of the primary instance; threaded through the
    # existing single-scheme code paths (assumption wrappers, game
    # wrappers, reductions, lemmas).
    clone_alias = primary.clone_alias

    # The shared random-oracle holder module lives inside the theorem primitive's
    # abstract theory (emitted by ``theory_types``), so after the ``clone
    # <prim>_Theory as <clone_alias>`` it is ``<clone_alias>.RO_H``. Point the
    # top-level collector at THAT single module (rather than declaring a distinct
    # top-level ``RO_H`` that never unifies with it) so the theorem-game wrapper
    # (which reads the theory-local ``RO_H``) and the flat states / reduction /
    # ``={glob RO_H}`` couplings all name the same module. Empty prefix (non-ROM
    # proofs, no function value) leaves every existing export byte-identical.
    top_types.ro_module_prefix = f"{clone_alias}."

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
    # Per-let-name scheme-instance map (clone_alias/primitive_name are set at
    # ``collect_all`` above, so this is available before the top-level
    # ``instances_by_let_name`` is built). Used to give a MULTI-primitive game's
    # params their own per-clone types.
    inst_by_name = {inst.let_name: inst for inst in instances}
    for gf in primary_game_files:
        gf_id = _ec_ident(gf.name)
        oracle_type_name = f"{gf_id}_Oracle"
        oracle_type_by_game_file[gf.name] = oracle_type_name
        theory_game_decls.append(
            theory_modules.translate_game_file_oracle(gf, oracle_type_name)
        )
        # A game parameterized by MORE THAN ONE primitive (the seedbased ROM
        # helper ``CGLazyROTwoSeeded(KEM_PQ, NG, lambda)``) cannot live inside a
        # single primitive's abstract theory; give it per-param clone types so
        # ``translate_game`` emits it as a multi-param functor.
        gf_module_typed = [
            p
            for p in (gf.games[0].parameters if gf.games else [])
            if isinstance(p.type, frog_ast.Variable)
        ]
        is_multi_primitive = len(gf_module_typed) > 1 and all(
            p.name in inst_by_name for p in gf_module_typed
        )
        gf_param_mod_types: dict[str, str] | None = None
        gf_param_prim_types: dict[str, str] | None = None
        if is_multi_primitive:
            gf_param_mod_types = {
                p.name: f"{inst_by_name[p.name].clone_alias}.{scheme_type_name}"
                for p in gf_module_typed
            }
            gf_param_prim_types = {
                p.name: inst_by_name[p.name].primitive_name for p in gf_module_typed
            }
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
                    emit_state_vars=(
                        oracle_model_by_game_file[gf.name].is_multi_oracle
                        or (bool(side.fields) and len(side.methods) > 1)
                    ),
                    param_module_types=gf_param_mod_types,
                    param_primitive_types=gf_param_prim_types,
                )
            )
        adv = theory_modules.translate_adversary_type(
            gf,
            oracle_type_name,
            adv_type_name=f"{gf_id}_Adv",
            multi_oracle=theory_modules.multi_oracle_spec(
                gf, oracle_model_by_game_file[gf.name]
            ),
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
        gf_multi_oracle = theory_modules.multi_oracle_spec(
            gf, oracle_model_by_game_file[gf.name]
        )
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
                    multi_oracle=gf_multi_oracle,
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
                        emit_state_vars=(
                            oracle_model_by_game_file[gf.name].is_multi_oracle
                            or (bool(side.fields) and len(side.methods) > 1)
                        ),
                    )
                )
            adv = fp_theory_modules.translate_adversary_type(
                gf,
                oracle_type_name,
                adv_type_name=f"{gf_id}_Adv",
                multi_oracle=fp_theory_modules.multi_oracle_spec(
                    gf, oracle_model_by_game_file[gf.name]
                ),
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
            gf_multi_oracle = fp_theory_modules.multi_oracle_spec(
                gf, oracle_model_by_game_file[gf.name]
            )
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
                        multi_oracle=gf_multi_oracle,
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

    # Seed bitstring-carrier info for ``||`` concatenation *before* chain
    # emission. A scheme ``requires X subsets/== BitString<n>`` makes the
    # abstract carrier set ``X`` bitstring-like; the engine inlines the
    # set->bs coercion in flat states, so a ``||`` operand can surface
    # carrier-typed (e.g. ``pk1 : PK1Space`` in GHP18's KEMCombiner). The
    # late ``requires`` pass (below) emits the *type alias*
    # ``type bs_n = X.``, but that runs after the flat states render --
    # too late for the expression translator to know the carrier concats.
    # This emission-neutral pass (it registers no bitstring type, so it
    # cannot reorder ``top_types.emit()``) records the carrier->BitString
    # map up front. The carrier name is the ``Set X;`` let resolved through
    # the scheme instance; the bitstring side is taken verbatim from the
    # clause.
    if scheme is not None and scheme.requirements:
        _carrier_param_to_let: dict[str, str] = {}
        if isinstance(primary_let.value, frog_ast.FuncCall):
            for sp, arg in zip(scheme.parameters, primary_let.value.args):
                if isinstance(arg, frog_ast.Variable):
                    _carrier_param_to_let[sp.name] = arg.name

        def _carrier_set_name(side: frog_ast.Expression) -> str | None:
            if not (
                isinstance(side, frog_ast.FieldAccess)
                and isinstance(side.the_object, frog_ast.Variable)
            ):
                return None
            let_name = _carrier_param_to_let.get(
                side.the_object.name, side.the_object.name
            )
            found_inst = instances_by_let_name.get(let_name)
            if found_inst is None:
                return None
            resolved_field = found_inst.concretized_fields.get(side.name)
            if (
                isinstance(resolved_field, frog_ast.Variable)
                and resolved_field.name in known_abstract_types
            ):
                return resolved_field.name
            return None

        for req in scheme.requirements:
            if not (
                isinstance(req, frog_ast.BinaryOperation)
                and req.operator
                in (
                    frog_ast.BinaryOperators.SUBSETS,
                    frog_ast.BinaryOperators.EQUALS,
                )
            ):
                continue
            for set_side, bs_side in (
                (req.left_expression, req.right_expression),
                (req.right_expression, req.left_expression),
            ):
                carrier = _carrier_set_name(set_side)
                if carrier is not None and isinstance(bs_side, frog_ast.BitStringType):
                    top_types.register_subset_carrier(carrier, bs_side)

    scheme_module_params: list[ec_ast.ModuleParam] = []
    scheme_module_param_types: dict[str, str] = {}
    scheme_applied_args: list[str] = []
    ec_scheme: ec_ast.Module | None = None
    if not primitive_only:
        assert scheme is not None
        (
            scheme_module_params,
            scheme_module_param_types,
            scheme_applied_args,
        ) = _scheme_functor_params(
            scheme, primary_let.value, instances_by_let_name, scheme_type_name
        )

        # Hoist any nested module calls in scheme method bodies before
        # translating. EC requires module-procedure calls at statement level,
        # so a FrogLang body like ``return G.evaluate(s) + G.evaluate(0^lambda)``
        # would otherwise fall back to ``return witness;`` and break the
        # wrapper-to-flat-state bridge in the per-hop chain.
        scheme_hoisted = canonical_form.hoist_scheme_calls(scheme, method_return_types)
        # Pre-inline the scheme body's integer length references to base
        # symbols. Bare field names (e.g. ``lambda`` = the scheme's own ``Int
        # lambda``) and foreign field references (``G.lambda``) are resolved
        # one-shot so the body's bitstring types match the (base-named) clone
        # bindings. This is what ``top_types`` cannot do alone, since a bare
        # ``lambda`` there would shadow the base let.
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
        # A foreign scheme (``CGRandomOracleKDF``) is emitted at TOP LEVEL, so its
        # shared-RO reference must name the theory-owned holder ``<clone>.RO_H``,
        # exactly like the flat states -- not a bare ``RO_H`` (no top-level holder
        # exists; the single holder lives in the theorem primitive's theory clone).
        foreign_types.ro_module_prefix = f"{clone_alias}."
        # Register the RO function values so a foreign scheme body applying the
        # shared RO (``CGRandomOracleKDF.evaluate`` = ``return H(input)``) renders
        # ``<clone>.RO_H.h input``, not the fixed-op ``v_H input``. The holder
        # module is emitted once by ``theory_types``; this only affects reference
        # rendering.
        # pylint: disable=protected-access
        for pl in proof.lets:
            if isinstance(pl.type, frog_ast.FunctionType):
                foreign_types.register_function_value(
                    canonical_form._ec_ident(pl.name), pl.type
                )
        # pylint: enable=protected-access
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
        if inst is primary and primitive_only:
            # Abstract primitive primary: a section ``declare module``,
            # referenced by its let-name (like any non-primary instance).
            instance_module_expr[inst.let_name] = inst.let_name
        elif inst is primary and scheme_module_params:
            assert scheme is not None
            # Apply the functor to the *instance* args (``DoubleSymEnc(E)``),
            # not the scheme's own param names (``DoubleSymEnc(S)``). These
            # coincide for schemes whose params are named after their
            # instances (CES's ``E1``/``E2``) but differ when a scheme uses a
            # local param name (``DoubleSymEnc(SymEnc s)`` applied to ``E``).
            # A nested SCHEME-instance arg (the ROM ``CG_expanded(...,Hkdf,...)``
            # where ``Hkdf`` is itself ``CGRandomOracleKDF(...)``) is applied by
            # its concrete module expression, not its bare let-name (there is no
            # module ``Hkdf``); primitive-instance args stay their declared name.
            applied_args = ", ".join(
                concrete_module_expr.get(a, a) for a in scheme_applied_args
            )
            instance_module_expr[inst.let_name] = f"{scheme.name}({applied_args})"
        elif inst is primary:
            assert scheme is not None
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
        # Name the abstract *instances* the functor depends on (``-E``), not
        # the scheme's own param names (``-S``) -- the latter are not declared
        # modules. These coincide when params are named after their instances
        # (CES) but differ for a local param name (``DoubleSymEnc(SymEnc s)``).
        # Exclude CONCRETE scheme args: a let bound to a functor application
        # (e.g. the RO-materialized KDF ``Hkdf = CGRandomOracleKDF(...)``) is not
        # a ``declare module``, so ``-Hkdf`` names an unknown module. An abstract
        # instance maps to its own bare let-name in ``instance_module_expr``; a
        # concrete one maps to a functor application (``CGRandomOracleKDF(...)``).
        footprint_names.extend(
            a for a in scheme_applied_args if instance_module_expr.get(a, a) == a
        )
    elif not primitive_only:
        assert scheme is not None
        footprint_names.append(scheme.name)
    # In primitive-only mode the primary is itself a ``declare module`` and is
    # added by the loop below (so it is separated from the adversary too).
    for inst in instances:
        # Concretized foreign instances are top-level concrete modules, not
        # ``declare module``s, so they don't belong in the adversary's
        # separation footprint.
        if (
            (inst is not primary or primitive_only)
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
        # oracle type. Substitute the composed assumption game's formal params
        # with the composition's args -- ``LazyROTwoViewsExcludedProgrammed(P,
        # hybrid.Nss)`` binds the game's ``Int n`` to ``hybrid.Nss`` -- so a
        # parameterized oracle return type ``BitString<n>`` renders as the
        # concrete ``BitString<hybrid.Nss>`` rather than a bare ``bs_n``.
        inner_game = next(g for g in game_files if g.name == helper.to_use.name).games[
            0
        ]
        oracle_ret_subst = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
        for gp, garg in zip(inner_game.parameters, helper.to_use.args):
            oracle_ret_subst.set(frog_ast.Variable(gp.name), copy.deepcopy(garg))
        for game_method in inner_game.methods:
            method_return_types[
                (qualified_inner_oracle, game_method.signature.name)
            ] = visitors.SubstitutionTransformer(oracle_ret_subst).transform(
                copy.deepcopy(game_method.signature.return_type)
            )
        renames = {
            p.name: f"{p.name}m" for p in helper.parameters if p.name == clone_alias
        }
        # Per-reduction-parameter module type: match each param.name to
        # the clone of the same-named scheme instance. For OTP this is
        # a no-op; for CES it gives each of ``CE``/``E1``/``E2`` the
        # correct per-clone ``.Scheme`` type.
        per_param_mod_types: dict[str, str] = {}
        # Per-param *primitive type* for ``type_of`` resolution of calls on the
        # param (``NG.Encode`` -> ``NominalGroup``). A multi-primitive reduction
        # has params of different primitive types, so each maps to its own
        # instance's primitive name rather than the single primary primitive.
        per_param_prim_types: dict[str, str] = {}
        for p in helper.parameters:
            p_inst = instances_by_let_name.get(p.name)
            if p_inst is not None:
                per_param_mod_types[p.name] = f"{p_inst.clone_alias}.{scheme_type_name}"
                per_param_prim_types[p.name] = p_inst.primitive_name
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
                param_primitive_types=per_param_prim_types or None,
            )
        )
        if helper.methods:
            oracle_params_by_reduction[helper.name] = [
                p.name for p in helper.methods[0].signature.parameters
            ]

    # Scalar oracle name + params derived from the oracle model built above.
    # ``oracle_name_by_game_file`` is the first method (the legacy single-oracle
    # key) so single-oracle emission stays byte-identical; the full
    # ``oracle_model_by_game_file`` is threaded onto the resolver for the P2-P4
    # multi-oracle emitters.
    oracle_name_by_game_file: dict[str, str] = {}
    oracle_params_by_game_file: dict[str, list[str]] = {}
    # Per-oracle params (game file -> oracle name -> ordered EC param names).
    # Used by the multi-oracle per-oracle equiv lemmas (P3) so each post-init
    # ``hop_<i>_<m>`` lemma's precondition carries ``m``'s own argument
    # equality. Single-oracle resolution ignores this (it keys off the scalar
    # first-method params), so output stays byte-identical.
    oracle_params_by_oracle: dict[str, dict[str, list[str]]] = {}
    for gf in game_files:
        first_method = gf.games[0].methods[0]
        oracle_name_by_game_file[gf.name] = oracle_model_by_game_file[
            gf.name
        ].scalar_oracle_name
        oracle_params_by_game_file[gf.name] = [
            p.name for p in first_method.signature.parameters
        ]
        oracle_params_by_oracle[gf.name] = {
            m.signature.name.lower(): [p.name for p in m.signature.parameters]
            for m in gf.games[0].methods
        }

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
        oracle_model_by_game_file=oracle_model_by_game_file,
        oracle_params_by_oracle=oracle_params_by_oracle,
        outer_game_file_name=proof.theorem.name,
    )

    # Validate proof via the engine (same as before).
    def _load_definitions(eng: pe.ProofEngine) -> None:
        for imp in proof.imports:
            resolved = frog_parser.resolve_import_path(imp.filename, proof_path)
            root = frog_parser.parse_file(resolved)
            eng.add_definition(root.get_export_name(), root)
            if isinstance(root, frog_ast.Scheme):
                for sub_imp in root.imports:
                    sub_resolved = frog_parser.resolve_import_path(
                        sub_imp.filename, resolved
                    )
                    sub_root = frog_parser.parse_file(sub_resolved)
                    eng.add_definition(sub_root.get_export_name(), sub_root)

    engine = pe.ProofEngine(verbose=False)
    _load_definitions(engine)
    try:
        engine.prove(proof, proof_path)
    except pe.FailedProof:
        # The cosmetic EC-name rename (``_normalize_ec_module_names``) is applied
        # to the theorem/steps but NOT to reduction helpers, so a reduction that
        # holds a packed scheme-typed field (the Universal combiner's
        # ``hybrid.DecapsKey``) becomes unresolvable and the RENAMED proof
        # FailedProofs even though the proof is valid. ``prove`` populates the
        # engine's proof context (``set_up_proof_context``) before it verifies
        # any hop, so the main engine is still fully set up for chain emission;
        # re-validate the consistent PRE-rename proof on a throwaway engine and,
        # if it genuinely proves, let the export proceed. A truly broken proof
        # re-raises here and aborts, exactly as before.
        val_engine = pe.ProofEngine(verbose=False)
        _load_definitions(val_engine)
        val_engine.prove(proof_for_validation, proof_path)

    # Tactic-cache sidecar. Loaded once per export; consulted on every
    # micro-lemma that falls through the Synthesized rungs (1/2).
    # ``requested_cache_keys``
    # accumulates the lookup keys (used by ``cache_report.py`` for
    # orphan detection).
    # pylint: disable=import-outside-toplevel
    from .tactic_cache import (
        HOP_TRANSFORM,
        TacticCache,
        oracle_transform,
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
    # (declared module var, method) pairs for which a pure-local
    # tuple-congruence micro was synthesized in some hop's chain. The exporter
    # emits one ``<M>_<m>_eq`` congruence lemma per distinct pair, in section
    # scope before the chain decls that ``call`` them. Empty when no
    # tuple-congruence micro fired, so unaffected proofs are untouched.
    congruence_method_requests: set[tuple[str, str]] = set()
    # (declared module var, EC method) pairs for which a dead-abstract-call-drop
    # micro was synthesized. The exporter emits one ``<M>_<m>_pres`` glob-
    # preservation axiom per pair in section scope. Empty for proofs with no
    # such drop, so they are untouched.
    pres_method_requests: set[tuple[str, str]] = set()
    # (declared module, EC method) pairs whose declared ``injective`` modifier a
    # synthesized tactic relies on (the binding challenge case-split elimination:
    # its ``smt`` needs encoding-injectivity to dissolve ``ev_<m> a = ev_<m> b``
    # into ``a = b``). The exporter emits one ``<M>_<m>_inj`` axiom per pair in
    # section scope. Empty for proofs with no such tactic, so they are untouched.
    inj_method_requests: set[tuple[str, str]] = set()
    # Concrete scheme names whose ``<Scheme>_decaps_val`` functional-value phoare
    # lemma the binding challenge case-split tactic references; the exporter
    # synthesizes each from the scheme's translated ``decaps`` proc. Empty for
    # proofs with no such tactic, so they are untouched.
    decaps_val_requests: set[str] = set()
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
        if (inst is not primary or primitive_only)
        and inst.let_name not in concretizable_foreign
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
        left_gf = _challenger_game_file_name(step_a.challenger)
        right_gf = _challenger_game_file_name(step_b.challenger)
        # The cross-primitive special-casing below assumes both endpoints are
        # imported game files (``ConcreteGame`` with a ``.Real``/``.Random``
        # side) keyed in ``primitive_name_by_game_file``. A bare intermediate
        # game (``ParameterizedGame`` defined in the proof, e.g. ``G_RandKey``)
        # has no game-file primitive and is not a foreign-primitive bridge, so
        # treat such a hop as in-primitive and route it through the normal
        # per-transform chain emission ("translate it as a flat game and bridge
        # as usual").
        both_concrete = isinstance(
            step_a.challenger, frog_ast.ConcreteGame
        ) and isinstance(step_b.challenger, frog_ast.ConcreteGame)
        is_cross_primitive = (
            both_concrete
            and left_gf != right_gf
            and primitive_name_by_game_file.get(left_gf)
            != primitive_name_by_game_file.get(right_gf)
        )
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
            copy.deepcopy(left_ast), skip_passes=_EXPORT_SKIP_PASSES
        )
        _right_canon, right_apps = engine.canonicalize_game_with_states(
            copy.deepcopy(right_ast), skip_passes=_EXPORT_SKIP_PASSES
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
            det_methods=det_methods_by_module,
        )
        chain_extra_decls.extend(info.extra_decls)
        requested_cache_keys.extend(info.requested_keys)
        stateless_module_requests.update(info.stateless_modules)
        congruence_method_requests.update(info.congruence_methods)
        pres_method_requests.update(info.pres_methods)
        if info.pre_override is not None or info.post_override is not None:
            chain_spec_overrides[_i] = (
                info.pre_override or resolver.precondition_for(step_a),
                info.post_override or "={res}",
            )
        return info.tactic_body

    # --- Live-state coupling (M5) ------------------------------------------
    # A multi-oracle hop couples its two endpoint games on their shared *live*
    # state -- a field equality on the module that holds it -- not on the whole
    # ``glob`` (which is ill-typed when one endpoint is a reduction-composed
    # game carrying a dead field the other lacks). See the validated template
    # ``tests/integration/ec_templates/multi_oracle_deadfield_coupling.ec``.
    #
    # Every state-holding module named in a live-state coupling is accumulated
    # here as ``_live_state_ref`` runs (during equiv-lemma + Pr-lemma emission).
    # The abstract scheme modules and inlining-hop Pr adversaries must be
    # restricted from these (M5 blocker A: an unrestricted abstract module is
    # assumed to write every in-scope global, so EC rejects the coupling's
    # ``call (_: Chal.pk{1} = G.pk{2})``). Non-empty only for multi-oracle
    # proofs, so it gates the abstract-footprint restriction + section reorder.
    live_state_holders: set[str] = set()

    # Abstract scheme modules (``declare module K, F``) the multi-oracle oracle
    # bodies call (``K.encaps`` / ``F.evaluate``). ``sim`` can only relate two
    # calls to such a module when ``={glob <module>}`` holds, so the per-oracle
    # coupling carries ``={glob K} /\\ ={glob F}`` and the lifted-``Initialize``
    # precondition + the Pr lemma's ``byequiv`` precondition carry it too.
    # Same list as ``declare_modules`` (built below); empty in single-oracle /
    # concrete-only proofs, so their output is byte-identical.
    abstract_scheme_modules = [p.name for p in declared_instance_params]
    # A shared random-oracle HOLDER module (``RO_H``, the sampled-once ROM
    # value) is a read-only global every oracle references, so it must ride the
    # per-oracle coupling like the abstract scheme modules -- otherwise a
    # stateless RO oracle (``return RO_H.h m``) cannot prove ``={res}`` and the
    # wrapper<->flat bridge legs (which DO carry ``={glob RO_H}``) become
    # underivable from the outer coupling. Empty for non-ROM proofs
    # (``function_value_modules()`` returns none), so their output is unchanged.
    ro_holder_modules = [m for m, _ in top_types.function_value_modules()]
    # A declared abstract module that is NEVER referenced after canonicalization
    # (e.g. the PRG of an "expanded" combiner -- passed as a functor arg but its
    # methods dead-code-eliminated) is ABSENT from EC's ``glob`` of every flat
    # state (``glob (F A)`` excludes ``glob A`` when ``F`` never uses ``A``). Its
    # ``={glob m}`` in the whole-hop coupling is then a spurious frame the
    # field-wise transitivity LEG couplings cannot carry, so the postcondition
    # composition "cannot prove goal (strict)" -- ``(glob m){1} = (glob m){2}``
    # with no hypothesis relating the two sides. Drop such dead modules from the
    # invariant so outer and legs agree. ROM-gated (dead functor args only arise
    # in the canonicalized combiner flat states); non-ROM proofs keep every
    # module -> byte-identical.
    live_abstract_modules = abstract_scheme_modules
    if ro_holder_modules and abstract_scheme_modules:
        probe_step = next(
            (
                s
                for s in proof.steps
                if isinstance(s, frog_ast.Step)
                and isinstance(s.challenger, frog_ast.ConcreteGame)
            ),
            None,
        )
        if probe_step is not None:
            # pylint: disable=protected-access
            probe_ast = engine._get_game_ast(
                probe_step.challenger, probe_step.reduction
            )
            # pylint: enable=protected-access
            probe_canon, _ = engine.canonicalize_game_with_states(
                copy.deepcopy(probe_ast), skip_passes=_EXPORT_SKIP_PASSES
            )

            def _module_referenced(mod: str) -> bool:
                finder: visitors.SearchVisitor[frog_ast.FieldAccess] = (
                    visitors.SearchVisitor(
                        lambda n: isinstance(n, frog_ast.FieldAccess)
                        and isinstance(n.the_object, frog_ast.Variable)
                        and n.the_object.name == mod
                    )
                )
                return finder.visit(probe_canon) is not None

            live_abstract_modules = [
                m for m in abstract_scheme_modules if _module_referenced(m)
            ]
    glob_invariant_conj = " /\\ ".join(
        f"={{glob {m}}}" for m in live_abstract_modules + ro_holder_modules
    )
    multi_oracle_byequiv_pre = (
        "={"
        + ", ".join(["glob A"] + [f"glob {m}" for m in abstract_scheme_modules])
        + "}"
    )

    def _live_state_field_name() -> str:
        """The shared live-state field name: the field the outer (theorem)
        game's ``Initialize`` returns (its public value). For KEMPRF this is
        ``pk``. Cross-name correspondence between differently-named live fields
        on the two sides is a deferred generalization (this uses one name)."""
        outer_gf = game_file_by_name.get(proof.theorem.name)
        if outer_gf is None or not outer_gf.games:
            return ""
        game = outer_gf.games[0]
        field_names = {f.name for f in game.fields}
        init = next(
            (m for m in game.methods if m.signature.name.lower() == "initialize"),
            None,
        )
        if init is not None:
            for stmt in reversed(list(init.block.statements)):
                if (
                    isinstance(stmt, frog_ast.ReturnStatement)
                    and isinstance(stmt.expression, frog_ast.Variable)
                    and stmt.expression.name in field_names
                ):
                    return stmt.expression.name
        return game.fields[0].name if game.fields else ""

    def _reduction_holds_field(reduction_name: str, field: str) -> bool:
        """True when the named reduction declares the live field itself (so its
        ``Initialize`` stores into it, e.g. ``R_MultiPRF``); False for a
        stateless delegating reduction (``R_KEM``) whose live state lives in
        the challenger sub-module."""
        helper = next(
            (
                h
                for h in proof.helpers
                if isinstance(h, frog_ast.Reduction) and h.name == reduction_name
            ),
            None,
        )
        return bool(helper and any(f.name == field for f in helper.fields))

    def _reduction_holds_any_field(reduction_name: str) -> bool:
        """True when the named reduction declares any field of its own (so its
        ``Initialize`` stores into its own globals). Name-independent companion
        to :func:`_reduction_holds_field` -- used by the init-peel pre-gate,
        which must not depend on guessing a single live-field name when the
        reduction holds only a subset of the game's live fields."""
        helper = next(
            (
                h
                for h in proof.helpers
                if isinstance(h, frog_ast.Reduction) and h.name == reduction_name
            ),
            None,
        )
        return bool(helper and helper.fields)

    def _field_read_post_init(game: frog_ast.Game, field_name: str) -> bool:
        """True when a NON-``Initialize`` method of ``game`` references
        ``field_name``.

        Distinguishes a live forwarded field (read by some post-init oracle, e.g.
        a binding game's ``ek`` read by ``Challenge``) from a dead one (the
        ``Unbreakable`` variant's constant-``false`` ``Challenge`` reads no ek).
        ``Initialize`` is excluded: it only sets the field and returns the public
        value (coupled via ``={res}``), so an init-only field need not ride the
        state coupling."""
        for method in game.methods:
            if method.signature.name.lower() == "initialize":
                continue
            search: visitors.SearchVisitor[frog_ast.Variable] = visitors.SearchVisitor(
                lambda n: isinstance(n, frog_ast.Variable) and n.name == field_name
            )
            if search.visit(method.block) is not None:
                return True
        return False

    def _reduction_init_delegates(reduction_name: str) -> bool:
        """True when the named reduction's ``Initialize`` delegates to its inner
        challenger's ``Initialize`` (``C.Initialize()``).

        Only such a reduction writes the challenger's globals after ``inline *``
        (and, when it also holds the live field, repacks the challenger's tuple
        result into its own globals -- the case the init backbone peel handles).
        A reduction whose ``Initialize`` does its own ``keygen`` instead
        (``R_MultiPRF``) never touches the challenger's state, so the abstract
        scheme need not be restricted from it -- keeping such proofs
        byte-identical."""
        helper = next(
            (
                h
                for h in proof.helpers
                if isinstance(h, frog_ast.Reduction) and h.name == reduction_name
            ),
            None,
        )
        if helper is None:
            return False
        init = next(
            (m for m in helper.methods if m.signature.name.lower() == "initialize"),
            None,
        )
        if init is None:
            return False
        search: visitors.SearchVisitor[frog_ast.FuncCall] = visitors.SearchVisitor(
            lambda n: isinstance(n, frog_ast.FuncCall)
            and isinstance(n.func, frog_ast.FieldAccess)
            and n.func.name.lower() == "initialize"
        )
        return search.visit(init.block) is not None

    def _reduction_renamed_live_field(reduction_name: str, field: str) -> str | None:
        """The reduction's OWN field holding the game's live state under a
        different name -- a self-keygen reduction that generates the theorem
        game's key pair itself and returns its own field at the game live
        field's return position (the game returns ``dk0`` there, the reduction
        its own ``seed0``), then forwards the CHALLENGE oracle to a STATELESS
        challenger. The live state is on the reduction, not the (stateless)
        challenger, so couple to ``R.seed0`` -- ``R.<field>`` / ``challenger.dk0``
        do not exist.

        ``None`` unless the return-position element is a bare own field AND the
        reduction's return has the SAME arity as the game's (so positions
        correspond): a decomposition tuple (``dk0 = [dk_PQ_0, ...]``, the two-R
        shape), a challenger-sourced projection (``dk0 <- _tup[1]``, the
        pure-delegate shape), and an arity mismatch (the game's single composite
        ``pk`` field constructed from the reduction's ``[pk1, pk2]`` return, as in
        GHP18's ``R_PRF1``) all decline, keeping those proofs' existing coupling."""
        reduction = _get_reduction(reduction_name)
        if reduction is None:
            return None
        outer_gf = game_file_by_name.get(proof.theorem.name)
        if outer_gf is None or not outer_gf.games:
            return None
        game = outer_gf.games[0]
        idx = _game_field_positions(game).get(field)
        game_elems = _return_elems(_find_init(game))
        if idx is None or game_elems is None:
            return None
        red_elems = _return_elems(_find_init(reduction))
        if red_elems is None or len(red_elems) != len(game_elems):
            return None
        elem = red_elems[idx]
        if isinstance(elem, frog_ast.Variable) and elem.name in {
            f.name for f in reduction.fields
        }:
            return elem.name
        return None

    def _live_state_ref(step: frog_ast.Step) -> str:
        """Field-qualified EC reference to a step endpoint's live state, e.g.
        ``G_RandKey.pk`` or ``K_c.KEM_INDCPA_MultiChal_Random.pk``.

        Side effect: the holder module's base name is recorded in
        ``live_state_holders`` -- the set of state-holding modules the abstract
        scheme modules (``K``/``F``) and inlining-hop Pr-lemma adversaries must
        be restricted from (M5 blocker A; see the file-assembly reorder below)."""
        module_expr = resolver.resolve(step).module_expr
        field = _live_state_field_name()
        if step.reduction is not None:
            inner = pt.module_base_name(pt.last_module_arg(module_expr))
            if not _reduction_holds_field(step.reduction.name, field):
                # pylint: disable=protected-access
                chal_game = engine._get_game_ast(step.challenger, None)
                # pylint: enable=protected-access
                # Stateless challenger: no ``Initialize`` (holds no live state
                # across oracle calls, e.g. ``KDFCollisionResistance`` whose only
                # oracle is ``Challenge(x0, x1)``). GHP18's PRF challenger HAS an
                # ``Initialize`` (generates/stores its key) -> stateful -> excluded.
                renamed = (
                    _reduction_renamed_live_field(step.reduction.name, field)
                    if chal_game is not None and _find_init(chal_game) is None
                    else None
                )
                if renamed is not None:
                    # Self-keygen reduction forwarding to a STATELESS challenger:
                    # it generates the game key pair itself and holds the live
                    # state under its own (renamed) field (game returns ``dk0``, R
                    # its own ``seed0``), forwarding the oracle to a challenger that
                    # holds no state. The live state is therefore on the reduction,
                    # not the (stateless) challenger -- couple to ``R.<renamed>``.
                    # A STATEFUL challenger (which itself holds the live field, e.g.
                    # GHP18's PRF challenger) keeps the challenger-seam path, so
                    # those proofs stay byte-identical.
                    holder = pt.module_base_name(module_expr)
                    live_state_holders.add(holder)
                    return f"{holder}.{renamed}"
                # Stateless reduction delegates: the live state is in the
                # challenger sub-module.
                holder = inner
            else:
                holder = pt.module_base_name(module_expr)
                # A FIELD-HOLDING reduction couples on its own field, but if it
                # ALSO delegates its ``Initialize`` to the inner challenger,
                # then after ``inline *`` the challenger's own ``Initialize``
                # writes the challenger's globals before the reduction repacks
                # the tuple result into its own -- so the abstract scheme must
                # be restricted from the inner challenger too, else the init
                # backbone peel's ``wp`` is rejected ("K can write
                # <Challenger>.dk1"). Gated on actual delegation (a field-holder
                # that does its own ``keygen`` never touches the challenger's
                # state), and on the inner arg not being an abstract scheme
                # module (never restrict ``K`` from ``K``), so non-delegating
                # reductions stay byte-identical.
                if inner not in abstract_scheme_modules and _reduction_init_delegates(
                    step.reduction.name
                ):
                    live_state_holders.add(inner)
        else:
            holder = pt.module_base_name(module_expr)
        live_state_holders.add(holder)
        return f"{holder}.{field}"

    def _packed_decomposition_coupling(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> str | None:
        """Coupling for a hop where one endpoint is a plain theorem game holding a
        PACKED scheme key field (``dk : K.DecapsKey`` = a component tuple) and the
        other a delegating reduction that holds the key DECOMPOSED into separate
        fields whose names do NOT match the game's (the CFRG expanded ROM hops:
        ``R_Dist_Real`` holds ``pq_keys``/``dk_T``/``ctStar`` while the theorem game
        holds packed ``dk``/``ctStar``).

        The composite path (``_composite_reduction_step``) assumes the reduction's
        fields ARE the game's fields (emits ``Game.pq_keys`` -- nonexistent); the
        decomposition path (``_decomposition_coupling``) reads the reduction's
        RETURN tuple (the encaps key here, not the packed dk). This route relates
        the game's packed field COMPONENT-WISE to the reduction's sources,
        classified from the SCHEME's ``KeyGen``: a component built by a fresh
        keygen/sample (``dk_PQ``, ``dk_T``) type-matches a reduction field or
        tuple-field projection; a component DERIVED from another (``ek_T =
        NG.Exp(NG.Generator(), dk_T)``) is pinned by a WITHIN-side invariant
        (``dk.`3{1} = NG_c.ev_exp NG_c.ev_generator dk.`2{1}``) -- necessary because
        the decaps oracle reads it, so a coupling omitting it would be a FALSE
        (unsound) statement. ``None`` unless exactly one plain game + one
        non-subset-field reduction, keeping every other proof byte-identical."""
        if step_a.reduction is None and step_b.reduction is not None:
            game_step, red_step, gs, rs = step_a, step_b, "1", "2"
        elif step_b.reduction is None and step_a.reduction is not None:
            game_step, red_step, gs, rs = step_b, step_a, "2", "1"
        else:
            return None
        assert red_step.reduction is not None
        red = _get_reduction(red_step.reduction.name)
        # pylint: disable=protected-access
        game = engine._get_game_ast(game_step.challenger, None)
        # pylint: enable=protected-access
        if red is None or game is None:
            return None
        red_field_names = {f.name for f in red.fields}
        game_field_names = {f.name for f in game.fields}
        # Shared-name reductions take the composite/direct paths; this route is the
        # DECOMPOSED case (the reduction's fields are not a subset of the game's).
        if red_field_names <= game_field_names:
            return None

        def _prim(t: frog_ast.Type) -> str:
            return t.name if isinstance(t, frog_ast.Variable) else str(t)

        def _ev_render(
            expr: frog_ast.Expression,
            comp_ref: dict[str, str],
            subst: dict[str, str],
        ) -> str | None:
            """Deterministic FrogLang expr -> ev-functional EC string, or ``None``
            when a leaf is not another packed component / a nullary det op (that
            marks a PRIMARY component -- fresh sample or keygen projection)."""
            if isinstance(expr, frog_ast.Variable):
                return comp_ref.get(expr.name)
            if (
                isinstance(expr, frog_ast.FuncCall)
                and isinstance(expr.func, frog_ast.FieldAccess)
                and isinstance(expr.func.the_object, frog_ast.Variable)
            ):
                mod = subst.get(expr.func.the_object.name, expr.func.the_object.name)
                alias = clone_alias_by_module.get(mod)
                if alias is None:
                    return None
                ev = f"{alias}.ev_{expr.func.name.lower()}"
                parts: list[str] = []
                for arg in expr.args:
                    rendered = _ev_render(arg, comp_ref, subst)
                    if rendered is None:
                        return None
                    parts.append(f"({rendered})")
                return (ev + "".join(f" {p}" for p in parts)).strip()
            return None

        game_base = pt.module_base_name(resolver.resolve(game_step).module_expr)
        red_base = pt.module_base_name(resolver.resolve(red_step).module_expr)
        # pylint: disable=protected-access
        # Reduction sources by structural type key -- ONLY from fields the game
        # does not also hold by name (those couple directly), so a packed
        # component never mis-matches a same-name field's component.
        red_source_by_type: dict[str, str] = {}
        for fld in red.fields:
            if fld.name in game_field_names:
                continue
            ec_f = mt._ec_field_name(fld.name)
            key = top_types.translate_type(fld.type).text
            if key not in red_source_by_type:
                red_source_by_type[key] = f"{red_base}.{ec_f}{{{rs}}}"
            if isinstance(fld.type, frog_ast.ProductType):
                for i, ct in enumerate(fld.type.types):
                    ckey = top_types.translate_type(ct).text
                    if ckey not in red_source_by_type:
                        red_source_by_type[ckey] = f"{red_base}.{ec_f}.`{i + 1}{{{rs}}}"

        conj: list[str] = []
        has_derived = False
        for gf in game.fields:
            ec_gf = mt._ec_field_name(gf.name)
            if gf.name in red_field_names:
                conj.append(f"{game_base}.{ec_gf}{{{gs}}} = {red_base}.{ec_gf}{{{rs}}}")
                continue
            # The packed key surfaces as an already-RESOLVED product type
            # (``dk : KEMPQDecapsKeySpace * NGScalarSpace * NGElementSpace``); its
            # component types are matched (via ``translate_type``) against the
            # reduction's decomposed sources. The DERIVATION structure (which
            # component is recomputed) is read from the concrete scheme's
            # ``KeyGen`` -- located by name from the game's module expression.
            if not isinstance(gf.type, frog_ast.ProductType):
                continue
            comp_types = gf.type.types
            n = len(comp_types)
            modexpr_str = str(resolver.resolve(game_step).module_expr)

            def _packed_keygen_return(
                sch: frog_ast.Scheme, arity: int
            ) -> frog_ast.Tuple | None:
                kg = next(
                    (m for m in sch.methods if m.signature.name.lower() == "keygen"),
                    None,
                )
                elems = _return_elems(kg) if kg is not None else None
                if elems is None:
                    return None
                return next(
                    (
                        e
                        for e in elems
                        if isinstance(e, frog_ast.Tuple)
                        and len(e.values) == arity
                        and all(isinstance(v, frog_ast.Variable) for v in e.values)
                    ),
                    None,
                )

            scheme = next(
                (
                    sch
                    for name, sch in schemes_by_name.items()
                    if name in modexpr_str and _packed_keygen_return(sch, n) is not None
                ),
                None,
            )
            if scheme is None:
                continue
            keygen = next(
                m for m in scheme.methods if m.signature.name.lower() == "keygen"
            )
            packed = _packed_keygen_return(scheme, n)
            assert packed is not None
            comp_vars = [cast(frog_ast.Variable, v).name for v in packed.values]
            subst: dict[str, str] = {}
            for sp in scheme.parameters:
                spk = _prim(sp.type)
                match = next(
                    (rp for rp in red.parameters if _prim(rp.type) == spk), None
                )
                if match is not None:
                    subst[sp.name] = match.name
            assign_map: dict[str, frog_ast.Expression] = {
                st.var.name: st.value
                for st in keygen.block.statements
                if isinstance(st, frog_ast.Assignment)
                and isinstance(st.var, frog_ast.Variable)
            }
            comp_ref = {
                comp_vars[i]: f"{game_base}.{ec_gf}.`{i + 1}{{{gs}}}" for i in range(n)
            }
            for i in range(n):
                proj = f"{game_base}.{ec_gf}.`{i + 1}{{{gs}}}"
                defn = assign_map.get(comp_vars[i])
                other_ref = {k: v for k, v in comp_ref.items() if k != comp_vars[i]}
                derived = (
                    _ev_render(defn, other_ref, subst) if defn is not None else None
                )
                if derived is not None:
                    conj.append(f"{proj} = {derived}")
                    has_derived = True
                    continue
                key = top_types.translate_type(comp_types[i]).text
                src = red_source_by_type.get(key)
                if src is not None:
                    conj.append(f"{proj} = {src}")
        # pylint: enable=protected-access
        # Fire when the packed key has a component the reduction RECOMPUTES
        # (a within-side ev-derivation) -- the case the composite path mis-handles
        # (its ``Game.<reduction-field>`` is nonexistent AND no other path pins the
        # derived component) -- OR when the single-field fallback
        # (``_live_state_ref``) would resolve to a NONEXISTENT field on a STATELESS
        # challenger (``fallback_to_stateless_chal``). That fallback fires exactly
        # when the reduction delegates to a stateless challenger (no ``Initialize``)
        # AND does not hold the game's live field -- neither by name
        # (``_reduction_holds_field``) nor under a renamed field
        # (``_reduction_renamed_live_field``, the self-keygen case). Then
        # ``_live_state_ref`` falls to ``<Chal>.<field>`` (only a proc-local of the
        # stateless challenger's ``compute()``), so the whole-field decomposition
        # is the only type-correct coupling (CK/UK's ``_INDCCA_T`` KEM-correctness
        # reduction holds the game's ``dk`` decomposed across ``pq_keys``/``corr``,
        # so ``dk`` itself is unheld and unrenamed). This mirrors ``_live_state_ref``
        # exactly, so it is load-bearing: a self-keygen reduction forwarding to a
        # stateless challenger (the two-KEM binding ``R`` holding the game's
        # ``dk0``/``dk1`` RENAMED to ``seed0``/``seed1``) has ``_live_state_ref``
        # return the valid ``R.seed0``, so its composite path is already
        # type-correct -- firing here clobbers its working challenge-case-split
        # body. A STATEFUL challenger (which itself holds the field) is likewise
        # left to the existing single-field path, keeping every
        # non-``expanded``-ROM proof byte-identical.
        # pylint: disable=protected-access
        chal_ast = engine._get_game_ast(red_step.challenger, None)
        # pylint: enable=protected-access
        chal_stateless = chal_ast is not None and _find_init(chal_ast) is None
        live_field = _live_state_field_name()
        fallback_to_stateless_chal = (
            chal_stateless
            and red_step.reduction is not None
            and not _reduction_holds_field(red_step.reduction.name, live_field)
            and _reduction_renamed_live_field(red_step.reduction.name, live_field)
            is None
        )
        if not conj or (not has_derived and not fallback_to_stateless_chal):
            return None
        live_state_holders.update({game_base, red_base})
        body = " /\\ ".join(conj)
        return f"{glob_invariant_conj} /\\ {body}" if glob_invariant_conj else body

    def _composite_reduction_step(
        step: frog_ast.Step,
    ) -> tuple[str, str, list[str]] | None:
        """``(reduction_base, challenger_base, own_field_names)`` when ``step``'s
        endpoint is a reduction whose ``glob`` spans BOTH its own live fields AND
        a stateful inner challenger's (it holds its own fields *and* delegates
        ``Initialize`` to the challenger, repacking the result into its globals);
        else ``None``.

        This is the wall-7 composite case: a single live-field coupling is too
        weak to bridge the two wrappers (the reduction reads its own ``dk0`` in
        ``Decaps0`` but forwards ``Challenge`` to the challenger, which reads the
        challenger's ``dk0``), so the coupling must relate every live field on
        BOTH the plain-game<->reduction seam and the reduction<->challenger seam.
        A pure delegate (holds no own field) or a self-keygen reduction (holds a
        field but never delegates -- ``R_MultiPRF``) returns ``None`` and keeps
        the single-field path, so those proofs stay byte-identical."""
        if step.reduction is None:
            return None
        helper = next(
            (
                h
                for h in proof.helpers
                if isinstance(h, frog_ast.Reduction) and h.name == step.reduction.name
            ),
            None,
        )
        fields = [f.name for f in helper.fields] if helper else []
        if not fields or not _reduction_init_delegates(step.reduction.name):
            return None
        module_expr = resolver.resolve(step).module_expr
        return (
            pt.module_base_name(module_expr),
            pt.module_base_name(pt.last_module_arg(module_expr)),
            fields,
        )

    def _find_init(
        node: frog_ast.Reduction | frog_ast.Game,
    ) -> frog_ast.Method | None:
        return next(
            (m for m in node.methods if m.signature.name.lower() == "initialize"),
            None,
        )

    def _return_elems(
        method: frog_ast.Method | None,
    ) -> list[frog_ast.Expression] | None:
        if method is None:
            return None
        for stmt in reversed(list(method.block.statements)):
            if isinstance(stmt, frog_ast.ReturnStatement):
                expr = stmt.expression
                if isinstance(expr, frog_ast.Tuple):
                    return list(expr.values)
                return [expr]
        return None

    def _keygen_ek_seed_pairs(red: frog_ast.Reduction) -> list[tuple[str, str]]:
        """``(ek_field, seed_field)`` pairs from each ``[ek, seed] =
        hybrid.KeyGen()`` destructure in a self-keygen reduction's ``Initialize``.

        Desugars to a temp assign (``_tup = hybrid.KeyGen()``) + two
        ``ArrayAccess`` element assigns (``ek = _tup[0]; seed = _tup[1]``); the
        scheme ``KeyGen`` return is ``[EncapsKey, DecapsKey]`` so element 0 is the
        EncapsKey, element 1 the seed. Only pairs where BOTH targets are declared
        reduction FIELDS are returned AND the DecapsKey field is a ``BitString``
        seed: the ek-derivation coupling functionalizes ``DeriveKeyPair(seed)`` =
        ``G.evaluate(seed) -> slice -> ...``, which is only well-typed when the
        held DecapsKey IS the seed (the *seedbased* combiners, whose ``KeyGen``
        samples a seed and stores it as the DecapsKey). The *expanded* combiners
        hold a packed component-key tuple as the DecapsKey and call the component
        KeyGens directly (no seed, no ``DeriveKeyPair``), so ``G.evaluate`` cannot
        apply -- yielding no pairs keeps their coupling free of the ill-typed
        ``ev_evaluate <packed key>``. A reduction that discards the EncapsKey (CT
        binding: ``ek`` is a local) also yields nothing -> byte-identical."""
        init = _find_init(red)
        if init is None:
            return []
        field_names = {f.name for f in red.fields}
        seed_field_types = {
            f.name: f.type
            for f in red.fields
            if isinstance(f.type, frog_ast.BitStringType)
        }
        keygen_tmps: list[str] = []  # ordered by Initialize statement order
        ek_of: dict[str, str] = {}
        seed_of: dict[str, str] = {}
        for stmt in init.block.statements:
            if not isinstance(stmt, frog_ast.Assignment):
                continue
            if not isinstance(stmt.var, frog_ast.Variable):
                continue
            val = stmt.value
            if isinstance(val, frog_ast.FuncCall):
                func = val.func
                if isinstance(func, frog_ast.FieldAccess) and func.name == "KeyGen":
                    keygen_tmps.append(stmt.var.name)
            elif isinstance(val, frog_ast.ArrayAccess) and isinstance(
                val.the_array, frog_ast.Variable
            ):
                if val.the_array.name not in keygen_tmps:
                    continue
                if not isinstance(val.index, frog_ast.Integer):
                    continue
                if stmt.var.name not in field_names:
                    continue
                if val.index.num == 0:
                    ek_of[val.the_array.name] = stmt.var.name
                elif val.index.num == 1:
                    seed_of[val.the_array.name] = stmt.var.name
        return [
            (ek_of[t], seed_of[t])
            for t in keygen_tmps
            if t in ek_of and t in seed_of and seed_of[t] in seed_field_types
        ]

    def _local_field_tuples(
        init: frog_ast.Method, red_fields: set[str]
    ) -> dict[str, list[str]]:
        """Local vars assigned a tuple literal built entirely from the
        reduction's own fields (``dk0 = [dk_PQ_0, dk_T_0, ek_T_0]``)."""
        out: dict[str, list[str]] = {}
        for stmt in init.block.statements:
            if (
                isinstance(stmt, frog_ast.Assignment)
                and isinstance(stmt.var, frog_ast.Variable)
                and isinstance(stmt.value, frog_ast.Tuple)
            ):
                comps = [
                    c.name
                    for c in stmt.value.values
                    if isinstance(c, frog_ast.Variable)
                ]
                if len(comps) == len(stmt.value.values) and all(
                    c in red_fields for c in comps
                ):
                    out[stmt.var.name] = comps
        return out

    def _is_decomposition_reduction(reduction: frog_ast.Reduction) -> bool:
        """True when the reduction's ``Initialize`` repacks >=2 of its own
        component fields into a packed key it returns.

        This is the CFRG concrete-framework shape: ``R_PQ_Bind`` / ``R_KDF``
        hold decomposed ``dk_PQ_i`` / ``dk_T_i`` / ``ek_T_i`` and return
        ``dk_i = [dk_PQ_i, dk_T_i, ek_T_i]`` -- a packed hybrid decaps key the
        theorem game holds monolithically. The Generic ``LEAK=>HON`` reductions
        hold the game's packed fields directly (no tuple repack), so this is
        ``False`` there and the coupling falls through to the existing composite
        / single-field path byte-identically. Name-independent (reads the return
        + assignment structure, never a field name)."""
        red_fields = {f.name for f in reduction.fields}
        init = _find_init(reduction)
        if init is None:
            return False
        red_elems = _return_elems(init)
        if red_elems is None:
            return False
        local_tuples = _local_field_tuples(init, red_fields)
        return any(
            isinstance(e, frog_ast.Variable)
            and e.name in local_tuples
            and len(local_tuples[e.name]) >= 2
            for e in red_elems
        )

    def _game_field_positions(game: frog_ast.Game) -> dict[str, int]:
        """Each module field's index in ``Initialize``'s return tuple (the LEAK
        game returns ``[ek0, dk0, ek1, dk1]`` with fields ``dk0`` at 1,
        ``dk1`` at 3)."""
        fnames = {f.name for f in game.fields}
        elems = _return_elems(_find_init(game))
        out: dict[str, int] = {}
        if elems:
            for i, e in enumerate(elems):
                if isinstance(e, frog_ast.Variable) and e.name in fnames:
                    out[e.name] = i
        return out

    def _reduction_decomp_map(
        reduction: frog_ast.Reduction, game: frog_ast.Game
    ) -> dict[str, list[str]]:
        """Map each packed game field to the tuple of reduction component fields
        it decomposes into, read off the reduction's ``Initialize`` return at the
        game field's return position. Empty when the reduction does not repack
        into that game's fields (so non-decomposition reductions decline)."""
        positions = _game_field_positions(game)
        init = _find_init(reduction)
        if init is None or not positions:
            return {}
        red_elems = _return_elems(init)
        if red_elems is None:
            return {}
        local_tuples = _local_field_tuples(init, {f.name for f in reduction.fields})
        out: dict[str, list[str]] = {}
        for gf, idx in positions.items():
            if idx >= len(red_elems):
                continue
            e = red_elems[idx]
            if isinstance(e, frog_ast.Variable) and e.name in local_tuples:
                out[gf] = local_tuples[e.name]
        return out

    def _challenger_source_map(
        reduction: frog_ast.Reduction, chal_game: frog_ast.Game
    ) -> dict[str, str]:
        """Map each reduction field sourced from ``challenger.Initialize()`` to
        the challenger field it comes from (``dk_PQ_0 <- _tup[1]`` and the
        challenger stores its return position 1 into ``dk0`` -> ``dk_PQ_0``
        couples to the challenger's ``dk0``). Empty for a self-keygen reduction
        (``R_KDF`` draws its own PQ keys), which then gets no challenger seam."""
        init = _find_init(reduction)
        if init is None:
            return {}
        red_fields = {f.name for f in reduction.fields}
        chal_var: str | None = None
        for stmt in init.block.statements:
            if (
                isinstance(stmt, frog_ast.Assignment)
                and isinstance(stmt.value, frog_ast.FuncCall)
                and isinstance(stmt.value.func, frog_ast.FieldAccess)
                and isinstance(stmt.value.func.the_object, frog_ast.Variable)
                and stmt.value.func.the_object.name == "challenger"
                and stmt.value.func.name.lower() == "initialize"
                and isinstance(stmt.var, frog_ast.Variable)
            ):
                chal_var = stmt.var.name
                break
        if chal_var is None:
            return {}
        pos_to_field = {i: f for f, i in _game_field_positions(chal_game).items()}
        out: dict[str, str] = {}
        for stmt in init.block.statements:
            if (
                isinstance(stmt, frog_ast.Assignment)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name in red_fields
                and isinstance(stmt.value, frog_ast.ArrayAccess)
                and isinstance(stmt.value.the_array, frog_ast.Variable)
                and stmt.value.the_array.name == chal_var
                and isinstance(stmt.value.index, frog_ast.Integer)
                and stmt.value.index.num in pos_to_field
            ):
                out[stmt.var.name] = pos_to_field[stmt.value.index.num]
        return out

    def _get_reduction(name: str) -> frog_ast.Reduction | None:
        return next(
            (
                h
                for h in proof.helpers
                if isinstance(h, frog_ast.Reduction) and h.name == name
            ),
            None,
        )

    def _decomposition_coupling(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> str | None:
        """Coupling for a hop whose reduction endpoint DECOMPOSES the theorem
        game's packed key into component fields (the CFRG concrete-framework
        expanded-LEAK proofs: ``R_PQ_Bind`` / ``R_KDF`` hold ``dk_PQ_i`` /
        ``dk_T_i`` / ``ek_T_i`` while the game holds packed ``dk_i =
        [dk_PQ_i, dk_T_i, ek_T_i]``).

        The wall-7 composite path (``_composite_reduction_step``) emits
        ``other_game.f = reduction.f`` per reduction field -- correct when the
        game and reduction share field names (the Generic proofs), but ILL-TYPED
        here (``Hybrid.dk_PQ_0`` does not exist). The sound coupling relates the
        game's packed field to the TUPLE of the reduction's component fields
        (validated shape: ``ec_templates/decomposition_coupling.ec``):

        * game <-> decomposition-reduction:
          ``G.dk0{gs} = (R.dk_PQ_0, R.dk_T_0, R.ek_T_0){rs}`` per game field;
        * decomposition-reduction <-> decomposition-reduction (both hold the same
          component fields): component-wise ``R1.f{s1} = R2.f{s2}``;
        * reduction <-> its inner challenger (challenger-sourced components only):
          ``R.dk_PQ_0{rs} = C.dk0{rs}`` (the challenger holds only the PQ part).

        Returns ``None`` when neither endpoint is a decomposition reduction, so
        every non-decomposition proof keeps its existing coupling byte-identical.
        """
        if not any(
            step.reduction is not None
            and (r := _get_reduction(step.reduction.name)) is not None
            and _is_decomposition_reduction(r)
            for step in (step_a, step_b)
        ):
            return None

        def _f(name: str) -> str:
            return mt._ec_field_name(name)  # pylint: disable=protected-access

        def _desc(step: frog_ast.Step, side: str) -> dict[str, Any]:
            module_expr = resolver.resolve(step).module_expr
            reduction = (
                _get_reduction(step.reduction.name)
                if step.reduction is not None
                else None
            )
            chal_base = (
                pt.module_base_name(pt.last_module_arg(module_expr))
                if reduction is not None
                else None
            )
            # pylint: disable=protected-access
            game = engine._get_game_ast(step.challenger, None)
            # pylint: enable=protected-access
            return {
                "side": side,
                "base": pt.module_base_name(module_expr),
                "reduction": reduction,
                "chal_base": chal_base,
                "game": game,
            }

        da = _desc(step_a, "1")
        db = _desc(step_b, "2")
        conj: list[str] = []
        holders: set[str] = set()

        def _emit_chal_seam(rd: dict[str, Any]) -> None:
            src = _challenger_source_map(rd["reduction"], rd["game"])
            if not src:
                return
            holders.add(rd["chal_base"])
            for rf, cf in src.items():
                conj.append(
                    f"{rd['base']}.{_f(rf)}{{{rd['side']}}} = "
                    f"{rd['chal_base']}.{_f(cf)}{{{rd['side']}}}"
                )

        game_descs = [d for d in (da, db) if d["reduction"] is None]
        red_descs = [d for d in (da, db) if d["reduction"] is not None]

        if len(game_descs) == 1 and len(red_descs) == 1:
            gd, rd = game_descs[0], red_descs[0]
            decomp = _reduction_decomp_map(rd["reduction"], gd["game"])
            if not decomp:
                return None
            holders.update({gd["base"], rd["base"]})
            for gf, comps in decomp.items():
                tup = ", ".join(f"{rd['base']}.{_f(c)}" for c in comps)
                conj.append(
                    f"{gd['base']}.{_f(gf)}{{{gd['side']}}} = ({tup}){{{rd['side']}}}"
                )
            _emit_chal_seam(rd)
        elif len(red_descs) == 2:
            r1, r2 = red_descs
            holders.update({r1["base"], r2["base"]})
            r2_fields = {f.name for f in r2["reduction"].fields}
            for name in (f.name for f in r1["reduction"].fields if f.name in r2_fields):
                conj.append(
                    f"{r1['base']}.{_f(name)}{{{r1['side']}}} = "
                    f"{r2['base']}.{_f(name)}{{{r2['side']}}}"
                )
            _emit_chal_seam(r1)
            _emit_chal_seam(r2)
        else:
            return None

        if not conj:
            return None
        holders.discard(None)  # type: ignore[arg-type]
        live_state_holders.update(holders)
        body = " /\\ ".join(conj)
        return f"{glob_invariant_conj} /\\ {body}" if glob_invariant_conj else body

    def _self_keygen_multikey_coupling(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> str | None:
        """Coupling for a self-keygen reduction with a MULTI-key game (DIFFKEY:
        the game holds ``dk0``/``dk1``; the reduction self-generates and holds
        ``seed0``/``seed1``, returning each at the game key's ``Initialize`` return
        position, and forwards the oracle to a STATELESS challenger). The
        single-field coupling path emits only the one live field ``dk0=R.seed0``,
        leaving ``dk1=R.seed1`` unstated; emit ``game.dkj{gs} = R.seedj{rs}`` for
        every game key. Gated on >= 2 keys, so the single-key (SAMEKEY) shape keeps
        the existing single-field path byte-identically. ``None`` off-shape."""
        if step_a.reduction is None and step_b.reduction is not None:
            game_step, red_step, gs, rs = step_a, step_b, "1", "2"
        elif step_b.reduction is None and step_a.reduction is not None:
            game_step, red_step, gs, rs = step_b, step_a, "2", "1"
        else:
            return None
        assert red_step.reduction is not None
        red = _get_reduction(red_step.reduction.name)
        if red is None:
            return None
        # pylint: disable=protected-access
        chal_game = engine._get_game_ast(red_step.challenger, None)
        game = engine._get_game_ast(game_step.challenger, None)
        # pylint: enable=protected-access
        # Stateless challenger (no Initialize) + self-keygen: same gate as the
        # single-field renamed-live-field path.
        if chal_game is None or _find_init(chal_game) is not None or game is None:
            return None
        positions = _game_field_positions(game)
        red_elems = _return_elems(_find_init(red))
        if not positions or red_elems is None:
            return None
        red_field_names = {f.name for f in red.fields}
        pairs: list[tuple[str, str]] = []
        for gf, idx in positions.items():
            if idx >= len(red_elems):
                return None
            elem = red_elems[idx]
            if not (
                isinstance(elem, frog_ast.Variable) and elem.name in red_field_names
            ):
                return None
            pairs.append((gf, elem.name))
        if len(pairs) < 2:
            return None
        game_base = pt.module_base_name(resolver.resolve(game_step).module_expr)
        red_base = pt.module_base_name(resolver.resolve(red_step).module_expr)
        live_state_holders.update({game_base, red_base})
        # pylint: disable=protected-access
        conj = [
            f"{game_base}.{mt._ec_field_name(gf)}{{{gs}}} = "
            f"{red_base}.{mt._ec_field_name(rf)}{{{rs}}}"
            for gf, rf in pairs
        ]
        # pylint: enable=protected-access
        # ek-derivation coupling (seedbased PK binding): a reduction that HOLDS
        # the EncapsKey as a field leaves it OPAQUE -- the ``game.ek = R.ek``
        # pairs above don't link it to the seed-DERIVED component keys the KDF
        # binds. For each ``[ek, seed] = hybrid.KeyGen()`` destructure, couple
        # ``(R.ek, R.seed)`` to ``DeriveKeyPair(R.seed)`` (KeyGen samples the seed
        # then derives) -- SOUND, from the scheme's own ``DeriveKeyPair`` AST. The
        # init hop's ev-twin route (``_synth_init_ek_twin``) proves it. CT
        # reductions discard the EncapsKey -> ``_keygen_ek_seed_pairs`` empty ->
        # byte-identical.
        keygen_pairs = _keygen_ek_seed_pairs(red)
        if keygen_pairs and ec_scheme is not None:
            dk_proc = next(
                (p for p in ec_scheme.procs if p.name == "derivekeypair"), None
            )
            if dk_proc is not None:
                param_to_arg = dict(
                    zip((p.name for p in ec_scheme.params), scheme_applied_args)
                )
                dk_proc = _rename_proc_call_modules(dk_proc, param_to_arg)
                for ek_f, seed_f in keygen_pairs:
                    # pylint: disable=protected-access
                    seed_ref = f"{red_base}.{mt._ec_field_name(seed_f)}{{{rs}}}"
                    ek_ref = f"{red_base}.{mt._ec_field_name(ek_f)}{{{rs}}}"
                    # pylint: enable=protected-access
                    ev = bch.keygen_derived_ev(dk_proc, seed_ref, clone_alias_by_module)
                    if ev is not None:
                        conj.append(f"({ek_ref}, {seed_ref}) = {ev}")
        body = " /\\ ".join(conj)
        return f"{glob_invariant_conj} /\\ {body}" if glob_invariant_conj else body

    def _live_state_coupling_base(step_a: frog_ast.Step, step_b: frog_ast.Step) -> str:
        # CFRG concrete-framework decomposition coupling: when a reduction
        # endpoint repacks its component fields into the theorem game's packed
        # key, ``other_game.f = reduction.f`` references a nonexistent packed-key
        # component. Relate the packed field to the component tuple instead
        # (gated on a decomposition reduction; None -> existing paths run
        # byte-identically). See ``_decomposition_coupling``.
        decomp_coupling = _decomposition_coupling(step_a, step_b)
        if decomp_coupling is not None:
            return decomp_coupling
        # Packed-vs-decomposed wrapper coupling (theorem game holds a packed
        # scheme key; the delegating reduction holds it decomposed under
        # different field names). Tried before the composite path, which would
        # otherwise emit ``Game.<reduction-field>`` (a nonexistent field).
        packed_coupling = _packed_decomposition_coupling(step_a, step_b)
        if packed_coupling is not None:
            return packed_coupling

        # Wall-7 composite coupling: when one side is a field-holding delegating
        # reduction, the single live-field equality cannot bridge the two
        # wrappers. Relate every live field across BOTH seams: plain-game
        # field <-> reduction's own field, AND reduction's own field <->
        # challenger's field (the reduction repacks the challenger's Initialize
        # result into its own globals, so the two are equal). This is exactly
        # what the chain emitter's composite bridge couplings reduce to, so the
        # per-oracle transitivity glue discharges. Gated tightly (see
        # ``_composite_reduction_step``) so single-field proofs are untouched.
        def _ec_ty(t: frog_ast.Type) -> str:
            return top_types.translate_type(t).text

        def _field_or_component_ref(
            target_ty: str,
            mod_fields: list[frog_ast.Field],
            base: str,
            side: str,
            prefer: str,
        ) -> str | None:
            # PACKED<->component matching: relate ``target_ty`` (the OTHER
            # endpoint's field EC type) to a field of ``mod_fields`` -- direct
            # same-EC-type match first (``base.f``), else a component of a
            # ProductType field (``base.g.`i``). CK/UK hold a combiner key PACKED
            # on one endpoint (``t_keys:(ek_T,dk_T)`` / ``ctStar:(ct_PQ,ct_T)``)
            # and DECOMPOSED on another (``ek_T`` / ``ct_T``). The SAME-NAMED field
            # is preferred so a packed ``ctStar`` couples via its ``.`2`` component,
            # not a coincidentally same-typed ``kem_ct_T``. Same-name same-type ->
            # ``base.f`` verbatim (byte-identical for the plain-game composite
            # proofs).
            # pylint: disable=protected-access
            def _match(f: frog_ast.Field) -> str | None:
                if _ec_ty(f.type) == target_ty:
                    return f"{base}.{mt._ec_field_name(f.name)}{{{side}}}"
                if isinstance(f.type, frog_ast.ProductType):
                    for i, comp in enumerate(f.type.types):
                        if _ec_ty(comp) == target_ty:
                            return (
                                f"{base}.{mt._ec_field_name(f.name)}.`{i + 1}{{{side}}}"
                            )
                return None

            # pylint: enable=protected-access
            pref = next((f for f in mod_fields if f.name == prefer), None)
            if pref is not None:
                hit = _match(pref)
                if hit is not None:
                    return hit
            for other in mod_fields:
                if other.name != prefer:
                    hit = _match(other)
                    if hit is not None:
                        return hit
            return None

        for red_step, other_step, red_side, other_side in (
            (step_a, step_b, "1", "2"),
            (step_b, step_a, "2", "1"),
        ):
            info = _composite_reduction_step(red_step)
            if info is None:
                continue
            red_base, chal_base, fields = info
            other_base = pt.module_base_name(resolver.resolve(other_step).module_expr)
            # Preserve the abstract-scheme restriction set (mirrors the holder
            # bookkeeping ``_live_state_ref`` does on the single-field path).
            live_state_holders.update({red_base, chal_base, other_base})
            # The cross-seam term ``other.<red-field> = red.<red-field>`` assumes
            # the OTHER endpoint holds the reduction's field names -- true for a
            # plain theorem game (the original composite case: generic_ct/pk). But
            # in a reduction<->reduction hop (the CFRG ROM ``R_Dist_Real ~
            # R_Wrap_Prog`` step) the other side is itself a reduction that need
            # not store those fields: a STATELESS wrapper reduction recomputes /
            # delegates rather than storing, so ``R_Wrap_Prog.pq_keys`` is a
            # nonexistent global EC rejects. Guard the term on the other reduction
            # actually declaring the field; game endpoints stay unguarded, so every
            # existing composite proof is byte-identical.
            other_field_names: set[str] | None = None
            if other_step.reduction is not None:
                other_red = _get_reduction(other_step.reduction.name)
                other_field_names = (
                    {f.name for f in other_red.fields}
                    if other_red is not None
                    else set()
                )
            # The within-side term ``red.<field> = chal.<field>`` holds because a
            # delegating reduction REPACKS the challenger's ``Initialize`` result
            # into its own globals -- so the challenger must actually hold that
            # field. For generic_ct/pk the inner binding challenger holds the
            # reduction's decaps keys, so every field matches (byte-identical). But
            # the CFRG ROM ``R_Dist_Real`` only draws a SCALAR from its
            # ``RandomScalarDist`` challenger (which holds ``x``/``y``) and
            # self-generates ``pq_keys``/``ctStar``; those are not repacked from the
            # challenger, so ``RandomScalarDist_Uniform.pq_keys`` is a nonexistent
            # global. Guard on the challenger declaring the field.
            # pylint: disable=protected-access
            chal_game_ast = engine._get_game_ast(red_step.challenger, None)
            red_ast = (
                _get_reduction(red_step.reduction.name)
                if red_step.reduction is not None
                else None
            )
            other_game_ast = (
                engine._get_game_ast(other_step.challenger, None)
                if other_step.reduction is None
                else None
            )
            # pylint: enable=protected-access
            chal_field_names = (
                {f.name for f in chal_game_ast.fields}
                if chal_game_ast is not None
                else None
            )
            red_type_by_name = (
                {f.name: f.type for f in red_ast.fields} if red_ast is not None else {}
            )
            conj: list[str] = []
            for fld in fields:
                ec_f = mt._ec_field_name(fld)  # pylint: disable=protected-access
                red_ty = red_type_by_name.get(fld)
                if other_game_ast is not None and red_ty is not None:
                    # Game endpoint: it may hold the reduction's field PACKED under
                    # a different name; match by type/component.
                    other_ref = _field_or_component_ref(
                        _ec_ty(red_ty),
                        list(other_game_ast.fields),
                        other_base,
                        other_side,
                        fld,
                    )
                    if other_ref is None:
                        continue
                else:
                    # Reduction endpoint: keep the name-guard (byte-identical for
                    # the reduction<->reduction stateless-wrapper hops).
                    if other_field_names is not None and fld not in other_field_names:
                        continue
                    other_ref = f"{other_base}.{ec_f}{{{other_side}}}"
                conj.append(f"{other_ref} = {red_base}.{ec_f}{{{red_side}}}")
            for fld in fields:
                if chal_field_names is not None and fld not in chal_field_names:
                    continue
                ec_f = mt._ec_field_name(fld)  # pylint: disable=protected-access
                chal_ty = (
                    next(
                        (f.type for f in chal_game_ast.fields if f.name == fld),
                        None,
                    )
                    if chal_game_ast is not None
                    else None
                )
                # The reduction may hold the field PACKED (``ctStar:(ct_PQ,ct_T)``)
                # while the challenger holds the COMPONENT (``ct_T``); match the
                # reduction side by the challenger field's type.
                if chal_ty is not None and red_ast is not None:
                    red_ref = _field_or_component_ref(
                        _ec_ty(chal_ty),
                        list(red_ast.fields),
                        red_base,
                        red_side,
                        fld,
                    )
                    if red_ref is None:
                        continue
                else:
                    red_ref = f"{red_base}.{ec_f}{{{red_side}}}"
                conj.append(f"{red_ref} = {chal_base}.{ec_f}{{{red_side}}}")
            # Forwarded live fields: a game live field the reduction does NOT hold
            # (the reduction forwards the oracle reading it to the inner challenger
            # -- e.g. a PK binding game holds ek0/ek1 that its ``Challenge`` reads,
            # but the reduction holds only the decaps keys and delegates
            # ``Challenge`` to the challenger). These never touch the reduction's
            # own globals, so they couple across the game<->challenger seam
            # directly (``HON.ek0{1} = LEAK.ek0{2}``). Omitting them leaves the flat
            # bridge's ek coupling underivable from Theta (the transitivity glue's
            # ``smt`` cannot prove the ek equality). Empty when the reduction holds
            # every game field (the CT case), so single-decaps proofs stay
            # byte-identical.
            #
            # Restricted to fields a POST-INIT oracle actually reads: on the
            # ``Unbreakable`` side of a binding hop the ``Challenge`` is
            # constant-``false`` and reads no ek, so ek is dead there -- coupling it
            # would be both unnecessary AND unprovable (the per-oracle decaps chain
            # drops the dead ek field mid-chain, so the transitivity cannot thread
            # its equality). Including it only where live keeps the ek coupling on
            # the ``Breakable`` side (where ``Challenge`` reads ek) and out of the
            # ``Unbreakable`` side.
            # pylint: disable=protected-access
            other_game = engine._get_game_ast(other_step.challenger, None)
            chal_game = engine._get_game_ast(red_step.challenger, None)
            # pylint: enable=protected-access
            held = set(fields)
            chal_fields = {f.name for f in chal_game.fields}
            for fld in (f.name for f in other_game.fields):
                if fld in held or fld not in chal_fields:
                    continue
                if not _field_read_post_init(other_game, fld):
                    continue
                ec_f = mt._ec_field_name(fld)  # pylint: disable=protected-access
                conj.append(
                    f"{other_base}.{ec_f}{{{other_side}}} = {chal_base}.{ec_f}{{{red_side}}}"
                )
            body = " /\\ ".join(conj)
            # A reduction<->reduction hop can leave ``conj`` empty: neither the
            # other reduction nor the challenger holds any of the reduction's
            # fields (they share no couplable state -- the CFRG ROM
            # ``R_Dist_Real ~ R_Wrap_Prog`` step). The meaningful coupling is then
            # just the abstract-scheme globs (plus the ``={res}`` prepended
            # elsewhere); returning ``glob_invariant_conj`` avoids a trailing
            # ``/\``. Existing composite proofs hold their fields, so ``conj`` is
            # non-empty and this branch never fires for them (byte-identical).
            if not body:
                return glob_invariant_conj
            return f"{glob_invariant_conj} /\\ {body}" if glob_invariant_conj else body
        multi = _self_keygen_multikey_coupling(step_a, step_b)
        if multi is not None:
            return multi
        field = pt.live_state_coupling(_live_state_ref(step_a), _live_state_ref(step_b))
        # Prefix the abstract-scheme glob equality so ``sim`` can relate the
        # post-init oracles' abstract calls (``K.encaps`` / ``F.evaluate``)
        # under this coupling. ``glob_invariant_conj`` is empty for proofs with
        # no declared abstract scheme module (output unchanged there).
        return f"{glob_invariant_conj} /\\ {field}" if glob_invariant_conj else field

    def _ro_challenger_materialization(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> str:
        """``<Challenger>.rF{side} = RO_H.h{side}`` for each hop endpoint that is a
        composite reduction whose inner challenger holds a Function/arrow field
        materialized as the shared RO (the lazy-RO Honest game's ``rF`` field IS
        the shared RO -- part-10). Threaded into the OUTER coupling (regardless of
        which base path built it) so a wrapper<->flat transitivity's first-leg
        witness can derive ``RO_H.h = rF`` from the hop precondition. The challenger
        GAME AST's Function field type is ABSTRACT (``Function<BitString<P.M>,
        BitString<n>>``), so it does not arrow-match the CONCRETE RO; a ROM proof
        has a single RO holder and the lazy-RO challenger's ONLY Function field IS
        that RO (concrete arrows equal after instantiation), so materialize any
        FunctionType challenger field to the single RO ref. Empty when no endpoint
        has an RO-materialized challenger (byte-identical). Sound: LazyRO Honest
        ``initialize`` sets ``rF`` from the shared RO."""
        # pylint: disable=protected-access
        ro_ref = next(iter(top_types.ro_by_arrow_type().values()), None)
        if ro_ref is None:
            return ""
        conj: list[str] = []
        for step, side in ((step_a, "1"), (step_b, "2")):
            if step.reduction is None or not _reduction_init_delegates(
                step.reduction.name
            ):
                continue
            chal_base = pt.module_base_name(
                pt.last_module_arg(resolver.resolve(step).module_expr)
            )
            # A plays against this composed challenger, so it must ride A's
            # separation footprint regardless of whether it materializes the RO --
            # the ``.Ideal``/``.Lazy`` side of an assumption game (HT/QT maps, no
            # Function field) is a live state-holder too, and omitting it lets EC
            # conclude "module A can write <Lazy>.mStar". Add unconditionally; the
            # RO materialization below still fires only for Function fields.
            live_state_holders.add(chal_base)
            chal_game = engine._get_game_ast(step.challenger, None)
            for cf in chal_game.fields if chal_game else []:
                if isinstance(cf.type, frog_ast.FunctionType):
                    conj.append(
                        f"{chal_base}.{mt._ec_field_name(cf.name)}{{{side}}} = "
                        f"{ro_ref}{{{side}}}"
                    )
        # pylint: enable=protected-access
        return " /\\ ".join(conj)

    def _live_state_coupling(step_a: frog_ast.Step, step_b: frog_ast.Step) -> str:
        base = _live_state_coupling_base(step_a, step_b)
        extra = _ro_challenger_materialization(step_a, step_b)
        return f"{base} /\\ {extra}" if extra else base

    # Per-hop memo of the multi-oracle chain emission. ``translate_hops``
    # calls ``_oracle_body_for_hop`` once per oracle of a multi-oracle hop;
    # the first call for a hop runs the whole per-oracle chain emission, caches
    # it, and appends its shared flat-state modules + per-oracle artifacts to
    # ``chain_extra_decls`` exactly once. Single-oracle proofs never reach this
    # (``translate_hops`` only routes multi-oracle models here), so their
    # output is unchanged.
    multi_oracle_hop_cache: dict[int, dict[str, list[str]]] = {}
    # Per-hop memo of the canonical-text key pair (the two adjacent inlined
    # games), used for the per-oracle (``<oracle>``) cache lookup below.
    # Mirrors the ``<hop>`` site's ``(left_key, right_key)``.
    multi_oracle_game_keys: dict[int, tuple[str, str]] = {}

    def _oracle_body_for_hop(
        _i: int,
        step_a: frog_ast.Step,
        step_b: frog_ast.Step,
        oracle_name: str,
        _is_init: bool,
    ) -> list[str] | None:
        if _is_assumption_hop(step_a, step_b):
            return None
        if _i not in multi_oracle_hop_cache:
            model = resolver.oracle_model_for(step_a)
            assert model is not None and model.init_name is not None
            oracles: list[tuple[str, bool]] = [(model.init_name, True)]
            oracles += [(m, False) for m in model.post_init_names]
            oracle_eq_args = {
                name: resolver.precondition_for(step_a, name) for name, _ in oracles
            }
            # pylint: disable=protected-access
            left_ast = engine._get_game_ast(step_a.challenger, step_a.reduction)
            right_ast = engine._get_game_ast(step_b.challenger, step_b.reduction)
            # pylint: enable=protected-access
            _lc, left_apps = engine.canonicalize_game_with_states(
                copy.deepcopy(left_ast), skip_passes=_EXPORT_SKIP_PASSES
            )
            _rc, right_apps = engine.canonicalize_game_with_states(
                copy.deepcopy(right_ast), skip_passes=_EXPORT_SKIP_PASSES
            )
            external_module_types = {
                inst.let_name: inst.primitive_name for inst in instances
            }
            flat_module_params = (
                list(declared_instance_params) if declared_instance_params else None
            )
            # pylint: disable=import-outside-toplevel
            from .chain_emitter import emit_multi_oracle_chain_for_hop

            # A reduction step that HOLDS its own live fields AND delegates its
            # ``Initialize`` to the inner challenger repacks the challenger's
            # tuple result into those globals, which ``sim`` cannot align -- the
            # init backbone peel is needed there (a stateless delegate returns
            # the challenger's result directly and keeps ``sim``). This is a
            # coarse pre-gate: the precise repack fingerprint (``_has_tuple_repack``
            # / ``_same_det_structure``) discriminates inside
            # ``_synth_init_backbone_peel``, so a self-keygen field-holder
            # (``R_MultiPRF``, which does not delegate) still keeps ``sim``. The
            # gate mirrors ``_composite_reduction_step``'s own condition
            # (delegates + holds fields) so it is name-independent -- unlike a
            # single guessed live-field name, which misfires when the reduction
            # holds only a subset of the game's fields (a PK game holds ek+dk but
            # its reduction holds only dk).
            init_reduction_repacks = any(
                s.reduction is not None
                and _reduction_init_delegates(s.reduction.name)
                and _reduction_holds_any_field(s.reduction.name)
                for s in (step_a, step_b)
            )
            # A hop whose coupling is a DECOMPOSITION coupling (game packed key =
            # tuple of a reduction's component fields) also needs the init
            # backbone peel, not ``sim`` -- even when the reduction does its OWN
            # keygens rather than delegating a challenger ``Initialize`` (the
            # ``R_KDF`` side of the CFRG expanded LEAK/HON hops:
            # ``init_reduction_repacks`` is False there because it composes the
            # KDF challenger, not a KEM one, but its packed-key coupling still
            # relates cross-module component globals ``sim`` cannot infer). None
            # -> no decomposition coupling -> byte-identical.
            init_decomposition = _decomposition_coupling(step_a, step_b) is not None

            info = emit_multi_oracle_chain_for_hop(
                hop_index=_i,
                left_game=left_ast,
                right_game=right_ast,
                left_apps=left_apps,
                right_apps=right_apps,
                oracles=oracles,
                oracle_eq_args=oracle_eq_args,
                left_wrapper_expr=resolver.resolve(step_a).module_expr,
                right_wrapper_expr=resolver.resolve(step_b).module_expr,
                types=top_types,
                type_of_factory=type_of_factory,
                external_module_types=external_module_types,
                method_return_types=method_return_types,
                flat_module_params=flat_module_params,
                det_methods=det_methods_by_module,
                init_reduction_repacks=init_reduction_repacks,
                init_decomposition=init_decomposition,
                init_coupling=_decomposition_coupling(step_a, step_b),
                full_coupling=_live_state_coupling(step_a, step_b),
                clone_alias=clone_alias_by_module,
                use_canonical_fields=proof_uses_ro_function,
                stateless_wrapper_bases={
                    h.name
                    for h in proof.helpers
                    if isinstance(h, frog_ast.Reduction) and not h.fields
                },
            )
            chain_extra_decls.extend(info.extra_decls)
            pres_method_requests.update(info.pres_methods)
            inj_method_requests.update(info.inj_methods)
            decaps_val_requests.update(info.decaps_val_schemes)
            multi_oracle_hop_cache[_i] = info.tactic_body_by_oracle
            multi_oracle_game_keys[_i] = (
                canonical_form.canonical_text(
                    left_ast, external_module_types, method_return_types
                ),
                canonical_form.canonical_text(
                    right_ast, external_module_types, method_return_types
                ),
            )
        body = multi_oracle_hop_cache[_i].get(oracle_name)
        if _is_init:
            # The init oracle already closes synth-static (``proc; inline*;
            # sim``); never cache it.
            return body
        # Post-init oracle: its body is non-trivially transformed across the
        # chain, so the rung-5 guided template (``body``) is the miss path.
        # Consult the sidecar for a per-oracle (``<oracle>``) cached tactic
        # keyed on the canonical text of the hop's two adjacent games -- on a
        # hit emit it as ``cached-guided`` (rung 3); on a miss fall back to the
        # guided template. Mirrors the ``<hop>`` site exactly.
        left_key, right_key = multi_oracle_game_keys[_i]
        key = (oracle_transform(oracle_name), left_key, right_key)
        requested_cache_keys.append(key)
        cached = tactic_cache.lookup(*key)
        if cached is not None:
            return [_res_tag(CACHED_GUIDED), *cached.tactic.splitlines(), "qed."]
        return body

    lemmas = pt.translate_hops(
        resolver,
        proof.steps,
        _body_for_hop,
        spec_overrides=chain_spec_overrides,
        oracle_body_for_hop=_oracle_body_for_hop,
        coupling_for_hop=_live_state_coupling,
        glob_invariant=glob_invariant_conj,
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
        # ``[ChainedEncryption(E1, E2), E1, E2]``. A reduction parameter
        # whose name doesn't match an instance but whose type is the
        # primary scheme/primitive (e.g. ``Reduction R1(SymEnc se)`` applied
        # as ``R1(proofE)``) maps to the primary module expression.
        # Only module-typed parameters (FrogLang type is a bare ``Variable``
        # naming a primitive/scheme) become EC functor args; value parameters
        # (``Int pk1len`` etc.) are dropped from both the reduction's functor
        # signature (see ``translate_reduction``) and this application.
        red_arg_exprs = [
            _reduction_arg_expr(
                p, instance_module_expr, primary_ctor_name, primary_module_expr
            )
            for p in helper.parameters
            if isinstance(p.type, frog_ast.Variable)
        ]
        ec_reduction_advs.append(
            top_modules.translate_reduction_adversary(
                reduction=helper,
                outer_adversary_type_name=qualified_outer_adv,
                inner_oracle_type_name=f"{target_clone}.{inner_oracle}",
                scheme_module_expr=primary_module_expr,
                reduction_arg_exprs=red_arg_exprs,
                extra_module_params=declared_instance_params or None,
                inner_multi_oracle=multi_oracle_spec_for(
                    top_modules,
                    helper.to_use.name,
                    scheme_args=list(helper.to_use.args),
                ),
                outer_multi_oracle=multi_oracle_spec_for(
                    top_modules,
                    outer_game_file_name,
                    scheme_args=list(proof.theorem.args),
                ),
                method_return_types=method_return_types,
            )
        )

    # Emit a concrete EC module for each intermediate game defined in the
    # proof (e.g. ``Game G_RandKey(KEM K, PRF F)`` or the single-oracle
    # ``Game Hyb(Int q)``). A bare ``ParameterizedGame`` step (``G_RandKey(K,
    # F)`` / ``Hyb``) resolves to a reference to this module, so it must be
    # defined -- the Game_step wrapper and the per-hop equiv lemmas name it.
    # The intermediate game is played against the OUTER theorem adversary and
    # ascribes to its oracle type. Module-typed (sub-primitive instance)
    # parameters become EC functor params; non-module parameters (``Int q``
    # compile-time indices) are dropped, mirroring the scheme functor-param
    # convention and ``_resolve_intermediate_game``'s module expression.
    outer_oracle_qualified = (
        f"{clone_alias}.{oracle_type_by_game_file[outer_game_file_name]}"
    )
    ec_intermediate_games: list[ec_ast.EcTopDecl] = []
    for helper in proof.helpers:
        # ``Reduction`` subclasses ``Game``; only true intermediate games
        # (no challenger composition) are emitted here -- reductions are
        # handled by the ``ec_reductions`` loop above.
        if not isinstance(helper, frog_ast.Game) or isinstance(
            helper, frog_ast.Reduction
        ):
            continue
        module_helper_params = [
            p for p in helper.parameters if p.name in instances_by_let_name
        ]
        param_module_types = {
            p.name: f"{instances_by_let_name[p.name].clone_alias}.{scheme_type_name}"
            for p in module_helper_params
        }
        param_primitive_types = {
            p.name: instances_by_let_name[p.name].primitive_name
            for p in module_helper_params
        }
        hoisted_game = canonical_form.hoist_game_calls(helper, method_return_types)
        ec_intermediate_games.append(
            top_modules.translate_intermediate_game(
                hoisted_game,
                module_name=helper.name,
                param_module_types=param_module_types,
                param_primitive_types=param_primitive_types,
                implements=outer_oracle_qualified,
                emit_state_vars=bool(helper.fields),
            )
        )

    ec_game_wrappers: list[ec_ast.EcTopDecl] = []
    for i, step in enumerate(proof.steps):
        if not isinstance(step, frog_ast.Step):
            raise NotImplementedError("Induction steps not supported yet.")
        resolved_step = resolver.resolve(step)
        # A plain step lifts its own game file's Initialize; a composed step
        # or a bare intermediate game lifts the OUTER (theorem) game's.
        wrapper_game_file = _wrapper_game_file_for(step, outer_game_file_name)
        if wrapper_game_file == outer_game_file_name:
            adv_type = qualified_outer_adv
            # Composed / intermediate steps are played against the OUTER
            # (theorem) adversary, so the lifted Initialize result is the outer
            # game instantiated at the theorem's scheme argument(s).
            wrapper_scheme_args = list(proof.theorem.args)
        else:
            adv_type = qualified_adv_type_by_game_file[wrapper_game_file]
            # A plain step lifts its own game file's Initialize, instantiated at
            # that step's own game argument(s).
            wrapper_scheme_args = (
                list(step.challenger.game.args)
                if isinstance(step.challenger, frog_ast.ConcreteGame)
                else []
            )
        ec_game_wrappers.append(_describe_step_wrapper(i, step))
        ec_game_wrappers.append(
            top_modules.translate_game_wrapper(
                wrapper_name=f"Game_step_{i}",
                adversary_type_name=adv_type,
                oracle_module_expr=resolved_step.module_expr,
                extra_module_params=declared_instance_params or None,
                multi_oracle=multi_oracle_spec_for(
                    top_modules, wrapper_game_file, scheme_args=wrapper_scheme_args
                ),
            )
        )

    ec_pr_lemmas: list[ec_ast.EcTopDecl] = []
    hop_kinds: list[pt.HopKind] = []
    assumption_names_by_hop: dict[int, str] = {}
    assumption_clone_by_hop: dict[int, str] = {}

    def _pr_multi_oracle_for(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> pt.MultiOraclePrSpec | None:
        """Build the multi-oracle Pr-lemma spec for a hop (P4), or ``None``.

        The Pr lemma is stated over the step wrappers ``Game_step_i``, which
        lift the *wrapper game file's* ``Initialize`` (the step's own game for
        a plain step, the theorem game for a composed step -- mirroring the
        wrapper emission). A hop is multi-oracle precisely when that wrapper
        game file is multi-oracle. For an inlining hop the per-oracle equiv
        lemma names (``hop_<i>_<m>``) the section-2.4 body references are
        emitted by :func:`translate_hops` off the *same* model
        (``oracle_model_for(step_a)`` == this model for a plain step), so the
        ``conseq hop_<i>_<m>`` bullets resolve.
        """
        wrapper_gf = _wrapper_game_file_for(step_a, outer_game_file_name)
        model = oracle_model_by_game_file.get(wrapper_gf)
        if model is None or not model.is_multi_oracle:
            return None
        assert model.init_name is not None
        return pt.MultiOraclePrSpec(
            coupling=_live_state_coupling(step_a, step_b),
            init_oracle=model.init_name,
            post_init_oracles=list(model.post_init_names),
            byequiv_pre=multi_oracle_byequiv_pre,
        )

    # Warm-up: fully populate ``live_state_holders`` before the Pr loop, so the
    # inlining-hop adversary restriction below uses the COMPLETE state-module set
    # (the loop processes hops in order, so a per-hop computation would miss
    # holders introduced by later hops). ``_pr_multi_oracle_for`` populates the
    # set as a side effect of ``_live_state_coupling``; it returns ``None`` (no
    # population) for single-oracle hops, leaving the set empty there.
    for _wi in range(len(proof.steps) - 1):
        _wa, _wb = proof.steps[_wi], proof.steps[_wi + 1]
        if isinstance(_wa, frog_ast.Step) and isinstance(_wb, frog_ast.Step):
            _pr_multi_oracle_for(_wa, _wb)
    # A reduction or intermediate game can hold module-global state (var fields)
    # *other* than the live ``pk`` field tracked above -- e.g. ``R_KEM`` declares
    # only ``ctStar`` (the challenge ciphertext used by its Decaps oracle), so
    # ``_live_state_ref`` never records it as a ``pk``-holder. The abstract scheme
    # modules ``K``/``F`` and the adversary still must be write-disjoint from
    # *every* such stateful helper: when ``K.encaps``/``F.evaluate`` is related in
    # a per-oracle equiv, EC otherwise assumes the abstract call could clobber the
    # reduction's ``ctStar`` and rejects the proof ("module F can write
    # R_KEM.ctStar"). Add every stateful helper to the restriction set. Gated on
    # ``live_state_holders`` already being non-empty (a multi-oracle proof), so
    # single-oracle / concrete-only proofs stay byte-identical.
    if live_state_holders:
        for _helper in proof.helpers:
            if isinstance(_helper, frog_ast.Game) and _helper.fields:
                live_state_holders.add(_helper.name)
    live_state_modules = sorted(live_state_holders)

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
            # Consume-pk bridge: when the reduction's Initialize forwards+repacks
            # the challenger's Initialize (holding the leaked decaps keys in its
            # own fields), ``R_Adv.distinguish`` consumes the leaked ``pk``
            # instead of re-initializing (see
            # ``module_translator.reduction_repacks_challenger_init``). The
            # ``hL``/``hR`` byequiv bridges then need the init-backbone-peel
            # tactic rather than the ``sim`` close.
            reduction_helper = next(
                (
                    h
                    for h in proof.helpers
                    if isinstance(h, frog_ast.Reduction) and h.name == reduction_name
                ),
                None,
            )
            consume_pk_bridge = (
                reduction_helper is not None
                and mt.reduction_repacks_challenger_init(reduction_helper)
            )
            gf_a_id = _ec_ident(assumption_game_file_name)
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
                    multi_oracle=_pr_multi_oracle_for(step_a, step_b),
                    adv_state_restrictions=live_state_modules or None,
                    consume_pk_bridge=consume_pk_bridge,
                    # Peel the FULL init backbone: the challenger's own init
                    # calls PLUS the reduction's own backbone (CFRG ``R_PQ_Bind``'s
                    # ``KEM_T.keygen`` calls and/or NominalGroup seed samples).
                    # Event-aware so a seed ``<$`` peels with ``rnd``; empty own
                    # backbone (Generic) reduces to the challenger-only peel.
                    consume_pk_peel_events=(
                        mt.consumed_pk_peel_events(
                            reduction_helper,
                            mt.init_module_call_count(gf_a.games[0]),
                            # The ``challenger`` oracle type is irrelevant to the
                            # OWN-call hoist (only reduction-param modules gate a
                            # nested-call lift), so pass "".
                            "",
                            method_return_types,
                        )
                        if consume_pk_bridge and reduction_helper is not None
                        else None
                    ),
                    consume_pk_reduction_glob=_ec_ident(reduction_name),
                    consume_pk_scheme_glob=pt.module_base_name(assumption_scheme_expr),
                    consume_pk_left_challenger_glob=f"{hop_clone}.{gf_a_id}_{left_side}",
                    consume_pk_right_challenger_glob=(
                        f"{hop_clone}.{gf_a_id}_{right_side}"
                    ),
                    # ROM: the shared-RO sample sits at incompatible positions on
                    # the two byequiv sides (game main vs reduction-adversary
                    # distinguish), which neither the consume-pk peel nor `sim`
                    # can align -- emit an honest tagged admit. Non-ROM proofs
                    # (no RO holder) keep the working bridge byte-identical.
                    ro_bridge_admit=bool(ro_holder_modules),
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
                    multi_oracle=_pr_multi_oracle_for(step_a, step_b),
                    adv_state_restrictions=live_state_modules or None,
                )
            )

    # === Assemble the file ===

    # An assumption game can carry an extra ``Int`` param beyond its primitive
    # (``LazyROTwoViewsExcludedProgrammed(HashInputPacking P, Int n)``); a
    # reduction composing ``G(P_inst, val)`` binds that Int param. Those bindings
    # must reach the primitive theory's clone so the game's ``BitString<n>``
    # instantiates concretely (``bs_n_t <- bs_Nout``, not a bare ``bs_n``). Keyed
    # by the game's primitive name (the theory whose clone carries the game).
    game_int_bindings: dict[str, dict[str, frog_ast.Expression]] = {}
    for _helper in proof.helpers:
        if not isinstance(_helper, frog_ast.Reduction):
            continue
        _gf = next((g for g in game_files if g.name == _helper.to_use.name), None)
        if _gf is None:
            continue
        _prim_name = primitive_name_by_game_file.get(_gf.name)
        if _prim_name is None:
            continue
        for _gp, _garg in zip(_gf.games[0].parameters, _helper.to_use.args):
            if not isinstance(_gp.type, frog_ast.Variable) and isinstance(
                _garg, frog_ast.Expression
            ):
                game_int_bindings.setdefault(_prim_name, {})[_gp.name] = _garg

    # The theorem instantiates the theorem game's abstract ``Set`` params (the
    # ROM hash domain ``D`` / range ``R``) with concrete types --
    # ``KEM_INDCCA_ROM(hybrid, BitString<hybrid.Nin>, BitString<hybrid.Nss>, H)``.
    # The PRIMARY instance's clone (``Hybrid_c``) must bind the abstract ``d``/
    # ``r`` to those concrete types, or the adversary's oracle interface
    # (``hash(m : Hybrid_c.d)``) won't match the concrete reduction
    # (``hash(m : bs_...)``). Byte-identical when the theorem has no Set args.
    theorem_set_bindings: list[tuple[str, str]] = []
    _thm_gf = next((gf for gf in game_files if gf.name == proof.theorem.name), None)
    if _thm_gf is not None and proof.theorem.args:
        for _gp, _targ in zip(_thm_gf.games[0].parameters, proof.theorem.args):
            if (
                isinstance(_gp.type, frog_ast.SetType)
                and _gp.name in abstract_types_map
                and isinstance(_targ, frog_ast.Type)
            ):
                theorem_set_bindings.append(
                    (
                        abstract_types_map[_gp.name],
                        top_types.translate_type(_targ).text,
                    )
                )

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
        # The primary instance's clone binds the theorem game's abstract Set
        # params (the ROM hash domain/range ``d``/``r``) to their concrete
        # theorem instantiations.
        if inst is primary:
            type_bindings_.extend(theorem_set_bindings)
        # Build bitstring type bindings by reconstructing each abstract
        # bitstring as a BitString<...> with the instance's field values
        # substituted in, then re-translating through ``top_types`` so the
        # resulting concrete type gets registered for top-level emission.
        # Merge any assumption-game Int-param bindings (``n -> hybrid.Nss``) for
        # this primitive's theory, so a game ``BitString<n>`` instantiates via
        # the composition arg rather than staying a bare ``bs_n``.
        instantiation_fields: dict[str, frog_ast.Type] = dict(inst.concretized_fields)
        instantiation_fields.update(
            cast(
                "dict[str, frog_ast.Type]",
                game_int_bindings.get(inst.primitive_name, {}),
            )
        )
        for abs_name, abs_expr in src_theory_types.abstract_bitstrings:
            concrete_expr = _instantiate_bitstring_expr(abs_expr, instantiation_fields)
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

    # Process ``requires`` clauses to discover type equalities. A clause
    # that equates (``==``) or relates by ``subsets`` two carrier types
    # means the abstract EC types behind them must be the same. Each side is
    # either a primitive field access (``K.SharedSecret``, resolving to a
    # ``Set X;`` carrier) or a ``BitString<...>`` type (resolving to a
    # concrete ``bs_*`` type). We unify them by emitting one as an alias of
    # the other. The *canonical* side is whichever EC type is declared first:
    # ``Set X;`` carriers (emitted in the "Abstract set declarations"
    # section) precede the ``bs_*`` types (emitted by ``top_types`` in the
    # "Concrete primitive types" section), so a carrier always wins over a
    # bitstring. This expresses e.g.
    # ``requires K.SharedSecret == BitString<F.lambda>`` as
    # ``type bs_lambda = SharedSecretSpace.`` and lets the concrete scheme
    # module (whose ``encaps`` assigns a ``SharedSecretSpace`` to a
    # ``bs_lambda``) type-check.
    type_aliases: dict[str, str] = {}  # set-let alias_name -> canonical_name
    set_let_order = [
        let.name
        for let in proof.lets
        if isinstance(let.type, frog_ast.SetType) and let.value is None
    ]
    param_to_let: dict[str, str] = {}
    if scheme is not None and isinstance(primary_let.value, frog_ast.FuncCall):
        for sp, arg in zip(scheme.parameters, primary_let.value.args):
            if isinstance(arg, frog_ast.Variable):
                param_to_let[sp.name] = arg.name

    def _requires_type_name(side: frog_ast.Expression) -> str | None:
        """EC type name for one side of a ``requires`` type relation."""
        if isinstance(side, frog_ast.FieldAccess) and isinstance(
            side.the_object, frog_ast.Variable
        ):
            let_name = param_to_let.get(side.the_object.name, side.the_object.name)
            found_inst = instances_by_let_name.get(let_name)
            if found_inst is None:
                return None
            resolved_field = found_inst.concretized_fields.get(side.name)
            # Only Set carriers unify as types. An ``Int`` field (e.g.
            # TriplingPRG's ``G.lambda == G.stretch``) also resolves to a
            # ``Variable``, but it names an ``Int X;`` let, not a type --
            # excluded by the ``known_abstract_types`` (Set-let) membership.
            if (
                isinstance(resolved_field, frog_ast.Variable)
                and resolved_field.name in known_abstract_types
            ):
                return resolved_field.name
            return None
        if isinstance(side, frog_ast.BitStringType):
            try:
                return top_types.translate_type(side).text
            except NotImplementedError:
                return None
        return None

    def _canonical_rank(name: str) -> tuple[int, int]:
        """Lower rank = declared earlier = canonical side."""
        if name in set_let_order:
            return (0, set_let_order.index(name))
        bs_names = top_types.registered_bitstring_names
        idx = bs_names.index(name) if name in bs_names else len(bs_names)
        return (1, idx)

    unhandled_requires = False
    if scheme is not None and scheme.requirements:
        for req in scheme.requirements:
            if not (
                isinstance(req, frog_ast.BinaryOperation)
                and req.operator
                in (
                    frog_ast.BinaryOperators.SUBSETS,
                    frog_ast.BinaryOperators.EQUALS,
                )
            ):
                unhandled_requires = True
                continue
            n0 = _requires_type_name(req.left_expression)
            n1 = _requires_type_name(req.right_expression)
            if n0 is None or n1 is None or n0 == n1:
                unhandled_requires = True
                continue
            canonical, alias = (
                (n0, n1) if _canonical_rank(n0) < _canonical_rank(n1) else (n1, n0)
            )
            if alias in set_let_order:
                type_aliases[alias] = canonical
            else:
                top_types.register_type_alias(alias, canonical)

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
            # bodies, etc. Escape EC reserved keywords (e.g. ``Int in;`` ->
            # ``op in_ : int.``) so the declaration parses.
            set_let_decls.append(ec_ast.OpDecl(_safe_ec_op_ident(let.name), "int"))

    # Non-primary primitive instances become ``declare module`` names
    # inside a ``section Main``. For CES this yields
    # ``declare module E1 <: E1_c.Scheme.`` and ``E2 <: E2_c.Scheme.``.
    # In primitive-only mode the primary itself is declared abstractly.
    declare_modules: list[ec_ast.DeclareModule] = []
    for inst in instances:
        if inst.let_name in concretizable_foreign:
            continue
        if inst is primary and not primitive_only:
            continue
        # Restrict each abstract scheme module from the other declared modules
        # (state-disjointness for ``swap``) AND from the state-holding modules
        # named in the multi-oracle live-state couplings (M5 blocker A: without
        # this EC assumes the abstract module writes the coupling's live field
        # and rejects the Pr lemma). ``live_state_modules`` is empty for
        # single-oracle proofs, so their declarations stay byte-identical.
        disjoint = [d.name for d in declare_modules] + live_state_modules
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
            # Reflect the declared ``injective`` modifier (faithful analogue of
            # ``deterministic`` -> ``_det``): a joint-injectivity axiom over the
            # method's ``ev_<m>`` op. Emitted only when a synthesizer REQUESTS it
            # (``inj_method_requests``, e.g. the binding challenge case-split
            # elimination whose ``smt`` needs encoding injectivity) -- following
            # the ``pres_method_requests`` pattern, so every proof that does not
            # request injectivity stays byte-identical. Only meaningful for a
            # deterministic method (so ``ev_<m>`` exists) with >=1 argument.
            if (
                (dm.name, sig.name.lower()) in inj_method_requests
                and sig.injective
                and sig.name.lower() in proc_sig_by_name
            ):
                inj_axiom = mt.ModuleTranslator.injective_axiom(
                    dm.name,
                    dm_inst.clone_alias,
                    proc_sig_by_name[sig.name.lower()],
                    dm_type_binding,
                )
                if inj_axiom is not None:
                    det_axioms.append(inj_axiom)

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
            adv_state_restrictions=live_state_modules or None,
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
    if ec_intermediate_games:
        proof_decls.append(_section_header("Intermediate games"))
        proof_decls.extend(ec_intermediate_games)
    proof_decls.append(_section_header("Game-step wrappers"))
    proof_decls.extend(ec_game_wrappers)
    # The chain artifacts (flat-state modules, micro-lemmas,
    # hop_<i>_chain lemmas) must precede the hop_<i> equiv lemmas that
    # reference them via ``apply hop_<i>_chain``.
    if chain_extra_decls:
        proof_decls.append(_section_header("Per-transform canonicalization chain"))
        # Per-method congruence lemmas for pure-local tuple-congruence micros,
        # emitted once (deduped) before the chain decls that ``call`` them.
        if congruence_method_requests:
            # pylint: disable=import-outside-toplevel
            from .chain_emitter import congruence_lemma_block

            proof_decls.append(
                "(* Per-method congruence lemmas (pure-local tuple inlining) *)"
            )
            for mod, meth in sorted(congruence_method_requests):
                proof_decls.append(congruence_lemma_block(mod, meth))
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
    if scheme is not None and scheme.requirements and unhandled_requires:
        decls.append(
            "(* NOTE: the FrogLang scheme has `requires` clauses that are "
            "not enforced by the EC export. The scheme module below may "
            "fail EC type-checking because cross-clone type equalities "
            "implied by the `requires` are not expressed in the clones. "
            "Deferred to Phase 5D. *)"
        )
    if ec_scheme is not None:
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
    # ``<Scheme>_decaps_val`` functional-value phoare lemmas requested by the
    # binding challenge case-split tactic (synthesized from the concrete scheme's
    # translated ``decaps`` proc; sits after the ``_det`` axioms it peels with and
    # before every hop lemma that ``call``s it).
    if decaps_val_requests and ec_scheme is not None:
        _decaps_proc = next((p for p in ec_scheme.procs if p.name == "decaps"), None)
        if _decaps_proc is not None and ec_scheme.name in decaps_val_requests:
            # The scheme functor's parameter names may differ from the concrete
            # instantiation arguments (CG_expanded's PQ KEM param is ``K``, bound
            # to ``KEM_PQ``). Rename the decaps proc's call module-prefixes to the
            # concrete args so the val-lemma resolves against the declared clones,
            # and state the lemma over those concrete args (a no-op when the
            # scheme's param names already match, e.g. CK_expanded).
            _param_to_arg = dict(
                zip((p.name for p in ec_scheme.params), scheme_applied_args)
            )
            _decaps_proc = _rename_proc_call_modules(_decaps_proc, _param_to_arg)
            _scheme_expr = f"{ec_scheme.name}(" + ", ".join(scheme_applied_args) + ")"
            _vl = bch.decaps_val_lemma(
                f"{ec_scheme.name}_decaps_val",
                _scheme_expr,
                _decaps_proc,
                clone_alias_by_module,
            )
            if _vl is not None:
                det_axiom_decls += [
                    _section_header("Functional-value spec (decaps)"),
                    "\n".join(_vl[0]),
                ]
    if stateless_axioms:
        det_axiom_decls += [
            _section_header("Statelessness specs"),
            *stateless_axioms,
        ]
    # Glob-preservation specs for dead-abstract-call-drop micros (one
    # ``<M>_<m>_pres`` per pruned scheme method).
    if pres_method_requests:
        det_axiom_decls += [
            _section_header("Glob-preservation specs (dead-call drop)"),
            *(
                mt.ModuleTranslator.pres_axiom(mod, meth)
                for mod, meth in sorted(pres_method_requests)
            ),
        ]
    if declare_modules and live_state_modules:
        # Multi-oracle live-state coupling (M5 blocker A): the ``declare module
        # K/F`` restriction clauses name state-holding modules (reductions,
        # intermediate games, wrappers), so those module DEFINITIONS must be in
        # scope before the declarations, and the declarations must precede every
        # lemma that references the section-declared K/F. All module definitions
        # (reductions/wrappers, and the per-transform chain's flat-state modules)
        # are functors over K/F and reference no section-declared module, so they
        # can all sit first; the abstract modules + det/stateless axioms then sit
        # between the modules and the lemmas.
        #
        # A per-transform chain (e.g. the LEAK/HON binding proofs) emits its
        # flat-state MODULES and its micro-LEMMAS interleaved, both *before* the
        # "Per-hop equivalence lemmas" header, so we cannot split at that header
        # -- the chain micro-lemmas would land ahead of ``declare module`` and
        # reference an undeclared ``K``. Partition instead: every chain lemma
        # chunk moves after the declarations, and ``K`` is additionally restricted
        # from the flat-state modules its micro-lemmas couple (else EC assumes the
        # abstract ``K.<m>`` call may clobber the coupled game state and rejects
        # the coupling -- "module K can write Step_...dk0"; the call in fact only
        # touches ``glob K``, the game fields being passed as arguments). When the
        # chain is admit-only (no micro-lemmas, e.g. KEMPRF), the partition and the
        # extra restriction are both no-ops and the output stays byte-identical.
        equiv_hdr = _section_header("Per-hop equivalence lemmas")
        split_at = proof_decls.index(equiv_hdr)
        pre, post = proof_decls[:split_at], proof_decls[split_at:]

        def _is_chain_lemma(decl: ec_ast.EcTopDecl) -> bool:
            return (
                isinstance(decl, str)
                and re.search(r"(?m)^\s*lemma\s", decl) is not None
                and re.search(r"(?m)^\s*module\s", decl) is None
            )

        pre_modules = [d for d in pre if not _is_chain_lemma(d)]
        pre_lemmas = [d for d in pre if _is_chain_lemma(d)]

        section_declare_modules = declare_modules
        # Only string chunks in ``pre_modules`` are chain flat-state modules
        # (reductions/wrappers are structured ``ec_ast.Module`` objects), so this
        # collects exactly the flat-state module names to restrict from.
        flat_state_names = [
            name
            for d in pre_modules
            if isinstance(d, str)
            for name in re.findall(r"(?m)^\s*module\s+(\w+)\s*\(", d)
        ]
        # A pre-header chain micro-lemma couples every such flat-state module, so
        # the abstract modules must be restricted from all of them. But the CFRG
        # init functional-twin route couples its twin (``FG_calls``/``FR_calls``)
        # in a POST-header hop lemma via ``transitivity``, which the pre_lemmas
        # test misses -- restrict from any flat-state module used as a
        # ``transitivity`` bridge in a post lemma too (else EC rejects the peel's
        # ``call`` on the abstract ``K.<m>``: "module K can write FG_calls.dk1").
        transitivity_refs: set[str] = set()
        for d in post:
            lines = (
                d.body
                if isinstance(d, ec_ast.Lemma)
                else [d] if isinstance(d, str) else []
            )
            for line in lines:
                transitivity_refs.update(re.findall(r"\btransitivity\s+(\w+)", line))
        restrict_names = (
            list(flat_state_names)
            if pre_lemmas
            else [n for n in flat_state_names if n in transitivity_refs]
        )
        if restrict_names:
            section_declare_modules = [
                ec_ast.DeclareModule(
                    name=dm.name,
                    module_type=dm.module_type,
                    disjoint_from=dm.disjoint_from + restrict_names,
                )
                for dm in declare_modules
            ]

        decls.append(
            ec_ast.Section(
                name="Main",
                decls=[
                    *pre_modules,
                    *section_declare_modules,
                    *det_axiom_decls,
                    *pre_lemmas,
                    *post,
                ],
            )
        )
    elif declare_modules:
        decls.append(
            ec_ast.Section(
                name="Main",
                decls=[*declare_modules, *det_axiom_decls, *proof_decls],
            )
        )
    else:
        decls.extend(proof_decls)

    # ``Group`` / ``ZModP`` provide the stdlib CyclicGroup + ZModRing/ZModField
    # theories cloned for ``GroupElem<G>`` / ``ModInt<q>`` types; ``List``
    # provides ``duniform``'s enum for a uniform group element. Required only
    # when such a type was registered, so non-group exports stay byte-identical.
    stdlib_requires = (
        ["Group", "ZModP", "List"] if top_types.has_stdlib_group_or_modint() else []
    )
    # ``FMap`` provides the finite-map type ``(k, v) fmap`` (with ``\in`` /
    # ``.[k]`` / ``.[k <- v]`` / ``empty``) used for a FrogLang ``Map<K, V>``
    # (the lazy random-oracle tables of the ROM games). NB: not ``SmtMap`` --
    # that is the *total* map ``(k, v) map``. Required only when some type
    # collector translated a map, so map-free exports stay byte-identical.
    # Maps can surface in the foreign-primitive theory (a lazy-RO helper game)
    # or the primary theory, so consult every collector.
    uses_map = (
        top_types.has_map()
        or theory_types.has_map()
        or any(fs.theory_types.has_map() for fs in foreign_scopes.values())
    )
    # ``List`` + ``FSet`` supply ``size`` / ``nth`` and ``elems`` / ``fdom``
    # for the ``for e in m.entries`` map-iteration loop (lowered to a while
    # over ``elems (fdom m)``); ordered before ``FMap`` (its dependency).
    map_requires = ["List", "FSet", "FMap"] if uses_map else []
    # ``Dexcepted`` (``d \ P``) for a one-shot exclusion draw; consult every
    # collector since the exclusion can surface in a foreign-primitive/helper
    # game body. Conditional -> exclusion-free exports stay byte-identical.
    needs_dexcepted = (
        top_types.needs_dexcepted
        or theory_types.needs_dexcepted
        or any(fs.theory_types.needs_dexcepted for fs in foreign_scopes.values())
    )
    dexcepted_requires = ["Dexcepted"] if needs_dexcepted else []
    ec_file = ec_ast.EcFile(
        # ``DProd`` / ``DMap`` provide the dprod/dmap lemmas
        # (``dmap_dprodE``, ``dmap1E``, ``dmap_id``, ``supp_dprod``,
        # etc.) consumed by the slice/concat round-trip + distribution-
        # split tactics emitted for Split/Merge Uniform Samples.
        requires=[
            "AllCore",
            "Distr",
            "DProd",
            "DMap",
            *stdlib_requires,
            *map_requires,
            *dexcepted_requires,
        ],
        decls=decls,
    )
    return ec_ast.pretty_print(ec_file)
