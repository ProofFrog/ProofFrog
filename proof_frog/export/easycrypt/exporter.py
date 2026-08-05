"""End-to-end exporter: ProofFile path -> EasyCrypt source string."""

# pylint: disable=duplicate-code  # shares the comparison/logical BinaryOperators
# enumeration with export/latex/stmt_renderer.py by coincidence, not by design

from __future__ import annotations

import copy
import pathlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Callable, cast

from . import binding_challenge as bch
from .challenge_common import concat_collision_peel as cc_concat_peel
from .challenge_common import paren as cc_paren
from .challenge_common import split_top_args as cc_split_args
from .challenge_common import subst as cc_subst
from . import canonical_form
from . import ec_ast
from . import expr_translator
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


def _own_call_counter(acc: list[int]) -> Callable[[frog_ast.ASTNode], bool]:
    """A :class:`~...visitors.SearchVisitor` predicate that counts a reduction's
    OWN abstract calls (everything not routed at ``challenger``) into ``acc[0]``.

    A factory rather than a nested closure so the accumulator is bound as a
    parameter -- the caller builds one per loop iteration, and a closure over the
    loop's own variable would bind late.
    """

    def _count(node: frog_ast.ASTNode) -> bool:
        if (
            isinstance(node, frog_ast.FuncCall)
            and isinstance(node.func, frog_ast.FieldAccess)
            and isinstance(node.func.the_object, frog_ast.Variable)
            and node.func.the_object.name != "challenger"
        ):
            acc[0] += 1
        return False

    return _count


def _qualify_method_return_type(
    rt: frog_ast.Type,
    inst: str,
    int_qual_map: dict[str, frog_ast.ASTNode],
) -> frog_ast.Type:
    """Qualify a primitive method's raw return type by the calling instance.

    A method-signature return type names carriers/lengths in the primitive's own
    namespace (``[EncapsKey, DecapsKey]`` from ``KEM.DeriveKeyPair``, ``Element``
    from ``NG.Exp``, ``BitString<Nss>`` from an encode). Resolving those bare
    names goes through whichever scheme registered that alias -- in a
    multi-primitive proof the hybrid ``CG_seedbased`` re-registers bare
    ``EncapsKey``/``DecapsKey`` as ITS carriers, so an inner ``KEM_PQ_inner``
    call's result mistypes as the hybrid pk/seed. Qualifying each carrier to the
    receiver (``EncapsKey`` -> ``inst.EncapsKey`` -> the instance's alias) and
    each bitstring length to the receiver's int field pins the type to the
    RECEIVER. Surfaces on a hoisted call temp (the ``the_type``-carrying
    top-level assignment path is already engine-qualified); a single-primitive
    proof's bare alias already resolves to the sole instance, so the qualified
    form translates to the same EC type -- byte-identical.
    """
    if isinstance(rt, frog_ast.Variable):
        return frog_ast.FieldAccess(frog_ast.Variable(inst), rt.name)
    if isinstance(rt, frog_ast.BitStringType) and rt.parameterization is not None:
        qualified_param = _QualifyFields(inst, int_qual_map).transform(
            copy.deepcopy(rt.parameterization)
        )
        return frog_ast.BitStringType(qualified_param)
    if isinstance(rt, frog_ast.ProductType):
        return frog_ast.ProductType(
            [_qualify_method_return_type(c, inst, int_qual_map) for c in rt.types]
        )
    return rt


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


def _endo_bijectivity_lemmas(
    module_name: str, method: str, bs_name: str, clone_prefix: str
) -> str:
    """``<M>_<m>_surj`` + ``<M>_<m>_bij``, DERIVED from the ``_inj`` axiom.

    A ``deterministic injective`` method whose argument and result share one
    BitWord-backed type is an injective ENDO-map on a FINITE type, so it is
    surjective by pigeonhole and hence bijective -- which is what lets a hop
    couple ``ev_<m>(x)`` for a uniform ``x`` with a directly-drawn uniform
    value. Injectivity alone gives uniformity only on the IMAGE; finiteness of
    the shared carrier is what closes the gap, and it comes from the clone's own
    ``FinType``, adding nothing to the trusted base.

    NAMING TRAP: ``Word.eca`` does ``clone include FinType ... rename [op]
    "enum" as "words"``, so the OP is ``<BW>.words`` while the LEMMAS keep
    ``<BW>.enumP`` / ``<BW>.enum_uniq``. The rename is ops-only.

    The ``size_map`` rewrite must be given its function EXPLICITLY: ``words`` is
    itself defined through a ``map``, so a bare ``rewrite size_map`` fires
    inside that definition instead of on the goal's own map.

    Validated in ``ec_templates/bitword_injective_bijective.ec``.
    """
    ev = f"{clone_prefix}.ev_{method}"
    bw = f"BW_{bs_name}"
    inj = f"{module_name}_{method}_inj"
    surj = f"{module_name}_{method}_surj"
    return "\n".join(
        [
            f"  local lemma {surj} (y : {bs_name}) : exists x, {ev} x = y.",
            "  proof.",
            f"  have huniq : uniq (map {ev} {bw}.words).",
            f"  + apply/map_inj_in_uniq; last exact {bw}.enum_uniq.",
            f"    by move=> p q _ _; apply {inj}.",
            f"  have hsub : forall z, z \\in map {ev} {bw}.words"
            f" => z \\in {bw}.words.",
            f"  + by move=> z _; apply {bw}.enumP.",
            f"  have hsize : size {bw}.words <= size (map {ev} {bw}.words).",
            f"  + by rewrite (size_map {ev}).",
            f"  have [hmem _] := leq_size_perm (map {ev} {bw}.words)"
            f" {bw}.words huniq hsub hsize.",
            f"  have : y \\in map {ev} {bw}.words"
            f" by rewrite hmem; apply {bw}.enumP.",
            "  by move/mapP => [x [_ hx]]; exists x; rewrite hx.",
            "  qed.",
            "",
            f"  local lemma {module_name}_{method}_bij : bijective {ev}.",
            "  proof.",
            f"  pose g := fun y => choiceb (fun x => {ev} x = y) witness.",
            "  exists g; split.",
            "  + move=> x; rewrite /g.",
            f"    have := choicebP (fun z => {ev} z = {ev} x) witness _.",
            "    + by exists x.",
            f"    by apply {inj}.",
            "  move=> y; rewrite /g.",
            f"  by apply (choicebP (fun z => {ev} z = y) witness); apply {surj}.",
            "  qed.",
        ]
    )


def _reprogramming_lazy_ro_field(game: frog_ast.Game) -> str | None:
    """Return the reprogramming RO Function-field name if ``game`` is a lazy-RO
    *reprogramming* game, else ``None``.

    A reprogramming game (the ``Lazy`` side of a ``CGLazyRO*Seeded`` assumption)
    has a ``Function<...>`` field ``H`` AND a hash method whose body branches on
    the exposed seed (``if (x == s0) { return y0_pq || y0_t; } return H(x);``) --
    i.e. an ``IfStatement`` in a method that reads the Function field. The
    ``Honest`` side is a plain ``return H(x)`` with no branch and is excluded, so
    the Honest-hop machinery (its fresh-RO drop) is untouched. Name-independent:
    keyed off the AST shape, not the game name.
    """
    func_fields = {
        f.name for f in game.fields if isinstance(f.type, frog_ast.FunctionType)
    }
    if not func_fields:
        return None

    def _all_statements(
        block: frog_ast.Block,
    ) -> "list[frog_ast.Statement]":
        out: list[frog_ast.Statement] = []
        for stmt in block.statements:
            out.append(stmt)
            if isinstance(stmt, frog_ast.IfStatement):
                for sub in stmt.blocks:
                    out.extend(_all_statements(sub))
        return out

    for method in game.methods:
        if any(
            isinstance(s, frog_ast.IfStatement) for s in _all_statements(method.block)
        ):
            reads = {
                v.name for v in visitors.VariableCollectionVisitor().visit(method.block)
            }
            hit = func_fields & reads
            if hit:
                return sorted(hit)[0]
    return None


def _ro_dead_drop_spec(
    repro_game: frog_ast.Game,
    mat_glob: str,
    lazy_glob: str,
    dfun_ll: str,
    peel_count: int,
) -> "pt.RoDeadDropSpec | None":
    """Build the ROM Lazy-side dead-shared-RO drop spec for a reprogramming game.

    Returns ``None`` off-shape (no reprogramming ``Function`` field, or no
    ``Initialize``), so a non-reprogramming (Honest / binding / forward) side is
    unaffected and stays on its existing bridge close byte-identically.

    The rendered reduction (e.g. ``R_LazyRO_L_Adv``) shows the *shared* RO
    ``RO_G_RO.h`` is re-sampled on the assumption side but never used there -- the
    KeyGen and the ``HashG`` oracle both read the *challenger's own* ``h`` (the Lazy
    game's field). So on the assumption side the shared-RO sample is DEAD, while the
    challenger's ``h`` is LIVE (observed through ``HashG``). The bridge therefore
    couples EVERY challenger field ``Mat.f{1} = Lazy.f{2}`` -- including the
    ``Function`` field ``h`` (materialized ``= RO_G_RO.h`` on the theorem side,
    fresh on the assumption side; equated by coupling the theorem-side eager RO
    sample to the assumption-side fresh ``h`` sample) -- and DROPS the dead
    assumption-side shared-RO sample. The ``h`` coupling makes ``HashG``'s
    reprogramming ``if`` agree on both the then- and else-branches, so ``proc; sim``
    closes each oracle. Validated on ``.ec-tmp/rom_hr_hashg.ec`` (live ``HashG``).
    """
    dead_field = _reprogramming_lazy_ro_field(repro_game)
    if dead_field is None:
        return None
    init = next(
        (m for m in repro_game.methods if m.signature.name == "Initialize"),
        None,
    )
    if init is None:
        return None
    # ``UniqueSample`` (the exclusion draw ``s1 <- BitString \\ {s0}``) renders
    # as a ``<$`` too -- the TwoSeeded assumption games carry one; missing it
    # left the ``seq`` prefix one short of ``y1_t`` and its (unprovable-early)
    # coupling ("cannot prove goal" at the hop_1_pr bridge bullet).
    n_samples = sum(
        1
        for s in init.block.statements
        if isinstance(s, (frog_ast.Sample, frog_ast.UniqueSample))
    )
    coupled = [
        (f.name[0].lower() + f.name[1:] if f.name[:1].isupper() else f.name)
        for f in repro_game.fields
    ]
    return pt.RoDeadDropSpec(
        n_samples=n_samples,
        dfun_ll=dfun_ll,
        mat_glob=mat_glob,
        lazy_glob=lazy_glob,
        coupled_fields=coupled,
        peel_count=peel_count,
    )


def _is_reprogram_hash_if(node: frog_ast.ASTNode) -> bool:
    """True if ``node`` is a lazy-RO reprogramming ``HashG`` branch:
    ``if (x == <seed>) { return <a> || <b>; } ...`` -- an equality guard whose
    then-branch returns the concatenation of the two reprogrammed halves."""
    if not isinstance(node, frog_ast.IfStatement):
        return False
    if not node.conditions or not isinstance(
        node.conditions[0], frog_ast.BinaryOperation
    ):
        return False
    if node.conditions[0].operator != frog_ast.BinaryOperators.EQUALS:
        return False
    if not node.blocks or not node.blocks[0].statements:
        return False
    ret = node.blocks[0].statements[0]
    return (
        isinstance(ret, frog_ast.ReturnStatement)
        and isinstance(ret.expression, frog_ast.BinaryOperation)
        and ret.expression.operator == frog_ast.BinaryOperators.OR
    )


def _is_inline_challenger_hash(node: frog_ast.ASTNode) -> bool:
    """A nested ``challenger.Hash(seed)`` call. CK/UK inline it into the
    ``DeriveKeyPair`` slice args instead of factoring ``y = challenger.Hash(seed)``
    (CG/UG factor it out)."""
    return (
        isinstance(node, frog_ast.FuncCall)
        and isinstance(node.func, frog_ast.FieldAccess)
        and isinstance(node.func.the_object, frog_ast.Variable)
        and node.func.the_object.name == "challenger"
        and node.func.name.lower() == "hash"
    )


class _InlineHashSliceCollector(visitors.Visitor[list[frog_ast.Slice]]):
    """Collect every ``Slice`` whose array is an inline ``challenger.Hash(seed)``."""

    def __init__(self) -> None:
        self.slices: list[frog_ast.Slice] = []

    def result(self) -> list[frog_ast.Slice]:
        return self.slices

    def leave_slice(self, node: frog_ast.Slice) -> None:
        if _is_inline_challenger_hash(node.the_array):
            self.slices.append(node)


def _hoist_inline_challenger_hashes(init: frog_ast.Method) -> frog_ast.Method:
    """Return a copy of ``init`` with each distinct inline ``challenger.Hash(seed)``
    hoisted into a synthetic typed ``__hash_k <- challenger.Hash(seed)`` assignment,
    the nested occurrences rewritten to ``__hash_k`` so the lazy-RO coupling
    extraction's hash-var model sees them (CK/UK inline these; CG/UG already factor
    them out). No-op -- the caller keeps the original ``init`` -- when the source
    already has a top-level ``y <- Hash(seed)`` (CG/UG stay byte-identical) or when a
    hash's full seed-expansion width can't be uniquely determined (=> the coupling
    stays admit rather than wrong). The width is the slice ``end`` that is NOT also a
    slice ``start``: the last partition of a seed expansion covers its full length."""
    if any(
        isinstance(s, frog_ast.Assignment) and _is_inline_challenger_hash(s.value)
        for s in init.block.statements
    ):
        return init
    new_init = copy.deepcopy(init)
    collector = _InlineHashSliceCollector()
    collector.visit(new_init.block)
    slices = collector.result()
    if not slices:
        return init
    by_key: dict[str, list[frog_ast.Slice]] = {}
    for sl in slices:
        by_key.setdefault(str(sl.the_array), []).append(sl)
    # key -> (synthetic var, its full-seed BitString type, the hash call to hoist)
    info: dict[str, tuple[str, frog_ast.Type, frog_ast.Expression]] = {}
    for i, (key, group) in enumerate(by_key.items()):
        starts = {str(sl.start) for sl in group}
        width_ends = [sl.end for sl in group if str(sl.end) not in starts]
        if len(width_ends) != 1:
            return init
        info[key] = (
            f"__hash_{i}",
            frog_ast.BitStringType(copy.deepcopy(width_ends[0])),
            copy.deepcopy(group[0].the_array),
        )
    block = new_init.block
    for sl in slices:
        new_sl = frog_ast.Slice(
            frog_ast.Variable(info[str(sl.the_array)][0]), sl.start, sl.end
        )
        block = visitors.ReplaceTransformer(sl, new_sl).transform(block)
    hoisted: list[frog_ast.Statement] = [
        frog_ast.Assignment(ty, frog_ast.Variable(var), call)
        for (var, ty, call) in info.values()
    ]
    new_init.block = frog_ast.Block(hoisted + list(block.statements))
    return new_init


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
                # pylint: disable=protected-access
                mangled = canonical_form._ec_ident(e.name)
                # pylint: enable=protected-access
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
    bitword_imports, bitword_abstract = _bitword_requires(
        top_types.needs_bitword, stdlib_requires
    )
    ec_file = ec_ast.EcFile(
        requires=[
            "AllCore",
            "Distr",
            "DProd",
            "DMap",
            *stdlib_requires,
            *dexcepted_requires,
            *bitword_imports,
        ],
        decls=decls,
        abstract_requires=bitword_abstract,
    )
    return ec_ast.pretty_print(ec_file)


def _bitword_requires(
    needs_bitword: bool, stdlib_requires: list[str]
) -> tuple[list[str], list[str]]:
    """``(extra imports, abstract requires)`` for the ``BitWord`` foundation.

    ``BitWord`` is required ABSTRACTLY: importing it would bring its ``n`` and
    ``word`` to top level, where they collide. ``List`` is imported because the
    derived round-trip proofs are ordinary list lemmas (``take_size_cat``,
    ``drop_size_cat``, ``cat_take_drop``); it is skipped when the stdlib
    group/ModInt preamble already imports it.
    """
    if not needs_bitword:
        return [], []
    imports = [] if "List" in stdlib_requires else ["List"]
    return imports, ["BitWord"]


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
    # ``<clone>.ev_<m>`` -> ``(<declared module>, <m>)`` for every method the
    # primitive declares ``injective``. Lets a route recognise an ENCODING leaf
    # by its head op and request the licensed ``<M>_<m>_inj`` axiom, without
    # naming any method. (A non-deterministic method has no ``ev_<m>``, so the
    # map is intersected with the deterministic set.)
    inj_methods_by_module: dict[str, set[str]] = {}
    inj_ev_ops: dict[str, tuple[str, str]] = {}
    for _inst in instances:
        _prim = primitives_by_name.get(_inst.primitive_name)
        if _prim is None:
            continue
        for _m in _prim.methods:
            if _m.injective and _m.deterministic:
                inj_ev_ops[f"{_inst.clone_alias}.ev_{_m.name.lower()}"] = (
                    _inst.let_name,
                    _m.name.lower(),
                )
                inj_methods_by_module.setdefault(_inst.let_name, set()).add(
                    _m.name.lower()
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
                # pylint: disable=protected-access
                mangled = canonical_form._ec_ident(e.name)
                # pylint: enable=protected-access
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
                        return _qualify_method_return_type(
                            method_return_types[key], obj.name, int_qual_map
                        )
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
            if isinstance(e, frog_ast.Tuple):
                # A tuple LITERAL ``(a, b, ...)``: the product of its components'
                # types -- the dual of the projection case above. Canonicalization
                # can leave an UNTYPED assignment of a repacked key tuple
                # (``__a6__ <- (__a4__, f04)``), and the flat-state module's
                # missing-declaration backfill types such a local by ``type_of`` on
                # its RHS; without this the backfill silently skips it and EC
                # rejects the module ("unknown module-level variable").
                return frog_ast.ProductType([type_of(v) for v in e.values])
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
    foreign_game_decls: list[ec_ast.EcTopDecl] = []
    oracle_type_by_game_file: dict[str, str] = {}
    module_name_by_concrete_game: dict[tuple[str, str], str] = {}
    adv_type_by_game_file: dict[str, str] = {}
    # Top-level MATERIALIZED challengers for reprogramming-Lazy games (wall 3o):
    # a `_Mat` copy whose RO Function field is assigned `<clone>.RO_G_RO.h`
    # (materialized) instead of sampled. Emitted AFTER the clones (so the shared
    # RO is in scope). Empty for non-reprogramming proofs (byte-identical).
    mat_challenger_decls: list[ec_ast.EcTopDecl] = []
    # (game-file name, side name) of each reprogramming-Lazy game that got a
    # ``_Mat`` copy: the resolver reroutes these steps' challenger to the Mat.
    reprogramming_lazy_games: set[tuple[str, str]] = set()
    # Per-let-name scheme-instance map (clone_alias/primitive_name are set at
    # ``collect_all`` above, so this is available before the top-level
    # ``instances_by_let_name`` is built). Used to give a MULTI-primitive game's
    # params their own per-clone types.
    inst_by_name = {inst.let_name: inst for inst in instances}
    # Backbone events of each rendered assumption-game ``initialize``, keyed
    # by (game-file, side). Read off the RENDERED module because a game whose
    # ``Initialize`` returns a call-bearing expression hoists those calls into
    # their own statements -- the FrogLang AST undercounts them.
    rendered_init_events_by_game: dict[tuple[str, str], list[str]] = {}
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
            _side_mod = theory_modules.translate_game(
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
            if isinstance(_side_mod, ec_ast.Module):
                rendered_init_events_by_game[(gf.name, side.name)] = (
                    mt.rendered_init_events(_side_mod)
                )
            theory_game_decls.append(_side_mod)
            # WALL 3o STEP B: for a reprogramming-Lazy game, emit a TOP-LEVEL
            # materialized copy via top_modules (concrete types + ``h <-
            # <primary>.RO_G_RO.h`` via ro_ref_for_dfun). The challenger is
            # referenced through the FIRST module-param instance's clone (the
            # reduction's ``Challenger : KEM_PQ_c.<gf>_Oracle``), so both the
            # implemented oracle type and the dead scheme param carry that clone
            # prefix (its concrete types match top_modules' render of the game).
            if _reprogramming_lazy_ro_field(side) is not None and gf_module_typed:
                chal_clone = inst_by_name[gf_module_typed[0].name].clone_alias
                reprogramming_lazy_games.add((gf.name, side.name))
                mat_challenger_decls.append(
                    top_modules.translate_game(
                        side,
                        f"{mod_name}_Mat",
                        primitive.name,
                        implements=f"{chal_clone}.{oracle_type_name}",
                        emitted_param_type=f"{chal_clone}.{scheme_type_name}",
                        emit_state_vars=True,
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
    # 1-based index of the adversary `distinguish` call in each assumption
    # game wrapper's `main`, for the `inline{2} <pos>` in the hop_<i>_pr
    # bridges.  `translate_theory_game_wrapper` emits the wrapper's
    # `Initialize` call ONLY when the game is Initialize-lifted, so a game
    # whose `Initialize` takes parameters (the ROM
    # `LazyROTwoViewsExcludedProgrammed`, whose `Initialize` is an ordinary
    # oracle) has `distinguish` as its FIRST statement, not its second.
    assumption_adv_pos_by_gf: dict[str, int] = {}
    for gf in primary_game_files:
        if gf.name not in assumed_gf_names:
            continue
        gf_id = _ec_ident(gf.name)
        adv_type_name = adv_type_by_game_file[gf.name]
        gf_multi_oracle = theory_modules.multi_oracle_spec(
            gf, oracle_model_by_game_file[gf.name]
        )
        assumption_adv_pos_by_gf[gf.name] = 1 if gf_multi_oracle is None else 2
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
                fp_game_mod = fp_theory_modules.translate_game(
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
                fp_decls.append(fp_game_mod)
                if isinstance(fp_game_mod, ec_ast.Module):
                    rendered_init_events_by_game[(gf.name, side.name)] = (
                        mt.rendered_init_events(fp_game_mod)
                    )
                # Also visible to the challenge-tactic routes, which look a
                # forwarded challenger's own proc up by module name: a reduction
                # can forward to a game of a FOREIGN primitive (the KDF-collision
                # challenger), whose modules never reach ``theory_game_decls``.
                foreign_game_decls.append(fp_game_mod)
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
            assumption_adv_pos_by_gf[gf.name] = 1 if gf_multi_oracle is None else 2
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
        # A scheme wrapping a sub-primitive (``KEM_PQ = SeededKEMWrapper(
        # KEM_PQ_inner)``) refers to its PARAM's carrier fields qualified in the
        # body (``[K_inner.EncapsKey, K_inner.DecapsKey] = K_inner.DeriveKeyPair(
        # seed)``). ``K_inner.DecapsKey`` must resolve to the INNER instance's
        # carrier (``KEM_PQ_inner.DecapsKey`` -> ``KEMPQDecapsKeySpace``), NOT the
        # wrapper's own same-named ``DecapsKey`` field (``BitString<Nseed>`` = the
        # seed, a genuinely different type -- the wrapper re-derives the inner key
        # from the seed then forwards to ``K_inner.Decaps``). Bind each param to
        # its instantiation arg and alias ``<param>.<field>`` to the arg's
        # already-resolved carrier (the ``<arg>.<field>`` qualified alias). The
        # collector's ``resolve`` prefers this qualified key over the bare
        # fallback. Carrier-fields analogue of wall-3d's ``<param>.<int>`` fix.
        if isinstance(foreign_let.value, frog_ast.FuncCall):
            for wrap_param, wrap_arg in zip(
                foreign_scheme.parameters, foreign_let.value.args
            ):
                if not isinstance(wrap_arg, frog_ast.Variable):
                    continue
                wrap_arg_prefix = f"{wrap_arg.name}."
                for tk, tv in top_aliases.items():
                    if tk.startswith(wrap_arg_prefix):
                        foreign_aliases[
                            f"{wrap_param.name}.{tk[len(wrap_arg_prefix):]}"
                        ] = tv
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
        # An applied arg that is ITSELF a concrete scheme instance (``G =
        # CGRandomOraclePRG(KEM_PQ, NG)`` where ``KEM_PQ =
        # SeededKEMWrapper(KEM_PQ_inner)``) must render as that instance's module
        # EXPRESSION, not its let-name: the derived ``KEM_PQ`` is not a declared
        # module, so a bare ``CGRandomOraclePRG(KEM_PQ, NG)`` is an ``unknown
        # module: KEM_PQ``. Instances are processed in declaration order, so a
        # prior concrete instance already has its ``concrete_module_expr`` entry;
        # substitute it. A plain abstract/primitive arg (``NG``) has no entry and
        # stays its let-name, so single-level exports are byte-identical.
        applied_resolved = [concrete_module_expr.get(a, a) for a in applied]
        concrete_module_expr[inst.let_name] = (
            f"{inst.ctor_name}({', '.join(applied_resolved)})"
            if applied_resolved
            else inst.ctor_name
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
                # A reduction may open with a bare ``challenger.Initialize();``
                # whose Void result is discarded. Without this the statement
                # raises and the WHOLE method silently degrades to
                # ``return witness;`` -- an empty body EC accepts as a module
                # but which no hop lemma over it can ever prove. Only methods
                # containing such a statement change; every other reduction is
                # byte-identical.
                allow_void_call=True,
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
            # WALL 3o STEP C: route a reprogramming-Lazy step's challenger to its
            # TOP-LEVEL materialized `_Mat` copy (unqualified -- it lives at top
            # level, not in a clone). Every consumer that derives the challenger
            # from ``resolver.resolve(step).module_expr`` then sees the Mat, so
            # the ``<Mat>.h = RO_G_RO.h`` coupling holds by materialization.
            if (gf_name, side_name) in reprogramming_lazy_games:
                module_name_by_instance_game[(inst.let_name, gf_name, side_name)] = (
                    f"{name}_Mat"
                )
            else:
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
    # (declared module, EC method, bitstring type, clone alias) for a
    # ``deterministic injective`` UNARY method whose argument and result share a
    # BitWord-backed type -- an injective ENDO-map, hence bijective, hence
    # carrying that type's uniform distribution to itself. The exporter DERIVES
    # the bijectivity from the ``_inj`` axiom above (a request here implies the
    # ``_inj`` request), so this grows no trusted base. Empty for proofs with no
    # such tactic, so they are untouched.
    bij_method_requests: set[tuple[str, str, str, str]] = set()
    # Concrete scheme names whose ``<Scheme>_decaps_val`` functional-value phoare
    # lemma the binding challenge case-split tactic references; the exporter
    # synthesizes each from the scheme's translated ``decaps`` proc. Empty for
    # proofs with no such tactic, so they are untouched.
    decaps_val_requests: set[str] = set()
    # Section-level aux lemma text (``slice4_first`` + ``kdf_col_ss``) the seedbased
    # wrapper binding-challenge route emits; spliced in ahead of the hop lemmas.
    aux_lemma_lines: list[str] = []
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

    def _reduction_init_queries_challenger(reduction_name: str) -> bool:
        """True when the named reduction's ``Initialize`` calls ANY method of its
        composed challenger (``challenger.<m>(..)``) -- the QUERY-delegate shape
        (the HON_BIND ``R_PRG``/``R_KG_PQ`` family: ``challenger.Query()`` /
        ``challenger.Generate()`` feeds a self-derivation into the reduction's
        own fields). Distinct from :func:`_reduction_init_delegates` (a strict
        ``Initialize`` delegate); a self-keygen reduction that never touches the
        challenger in ``Initialize`` answers False."""
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
            and isinstance(n.func.the_object, frog_ast.Variable)
            and n.func.the_object.name == "challenger"
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

        def _arity(t: frog_ast.Type) -> int:
            return len(t.types) if isinstance(t, frog_ast.ProductType) else 1

        # WHICH SIDE DOES THE PACKING? This route was written for the GAME
        # holding a packed key and the reduction holding it decomposed, and the
        # component matching below runs ONLY in the opposite direction -- a
        # reduction holding one wide tuple (the correctness challenger's
        # ``corr``, arity 5) against a game holding the pieces separately
        # (``pq_keys``/``kem_ct``/``ss_PQ``, arity <= 2). Comparing the widest
        # field on each side is what tells the two apart, and gating on it keeps
        # every packed-GAME proof -- the whole binding layer -- byte-identical.
        # Without the gate 36 exports changed, 15 of them admit-free.
        red_packed = max(
            (_arity(f.type) for f in red.fields if f.name not in game_field_names),
            default=0,
        ) > max((_arity(f.type) for f in game.fields), default=0)

        def _consume_red_source(ty: frog_ast.Type, emitted: list[str]) -> str | None:
            """A reduction source of EC type ``ty`` not already paired, else
            ``None``.

            Pairing the same source with two game fields would be a coupling the
            establishing hop cannot prove (two distinct fields cannot both equal
            one component), so a source already used is skipped rather than
            reused. Checked against what has actually been emitted, so the
            existing derivation path's pairings count too.
            """
            if not red_packed:
                return None
            src = red_source_by_type.get(top_types.translate_type(ty).text)
            if src is None or any(src in c for c in emitted):
                return None
            return src

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
                # SCALAR game field the reduction holds INSIDE a packed field.
                # The CFRG `_PQ` correctness-reduction hops: the reduction keeps
                # its challenger's whole 5-tuple in one ``corr`` field while the
                # game holds ``kem_ct``/``ss_PQ`` separately. Dropping these left
                # the ``decaps`` lemma UNPROVABLE -- its two bodies differ in
                # exactly those references, and no tactic can bridge an equality
                # the precondition does not carry.
                #
                # ``red_source_by_type`` is already built component-wise, and
                # first-declaration-wins is what makes the choice right here: the
                # 5-tuple's two same-typed shared secrets are the ENCAPS result
                # (``.`4``) and the DECAPS result (``.`5``), and the game's
                # ``ss_PQ`` is the encaps one.
                src = _consume_red_source(gf.type, conj)
                if src is not None:
                    conj.append(f"{game_base}.{ec_gf}{{{gs}}} = {src}")
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
                # No concrete scheme whose ``KeyGen`` returns a tuple of this
                # arity, so no derivation structure to read -- but the reduction
                # may still hold each component inside a packed field
                # (``GameCaseSplitReal.pq_keys`` against
                # ``R_Correct_Real.corr.`1``/``.`2``). Couple the components it
                # does hold; a component with no unpaired source is left alone.
                for i, ct in enumerate(comp_types):
                    src = _consume_red_source(ct, conj)
                    if src is not None:
                        conj.append(f"{game_base}.{ec_gf}.`{i + 1}{{{gs}}} = {src}")
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

    def _keygen_ek_key_pairs(red: frog_ast.Reduction) -> list[tuple[str, str]]:
        """``(ek_field, dk_field)`` pairs from each ``[ek, dk] = hybrid.KeyGen()``
        destructure in a self-keygen reduction's ``Initialize``.

        Desugars to a temp assign (``_tup = hybrid.KeyGen()``) + two
        ``ArrayAccess`` element assigns (``ek = _tup[0]; dk = _tup[1]``); the
        scheme ``KeyGen`` return is ``[EncapsKey, DecapsKey]`` so element 0 is the
        EncapsKey, element 1 the DecapsKey. Only pairs where BOTH targets are
        declared reduction FIELDS are returned -- a reduction that discards the
        EncapsKey (CT binding: ``ek`` is a local) yields nothing."""
        init = _find_init(red)
        if init is None:
            return []
        field_names = {f.name for f in red.fields}
        keygen_tmps: list[str] = []  # ordered by Initialize statement order
        ek_of: dict[str, str] = {}
        dk_of: dict[str, str] = {}
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
                    dk_of[val.the_array.name] = stmt.var.name
        return [(ek_of[t], dk_of[t]) for t in keygen_tmps if t in ek_of and t in dk_of]

    def _keygen_ek_seed_pairs(red: frog_ast.Reduction) -> list[tuple[str, str]]:
        """:func:`_keygen_ek_key_pairs` restricted to pairs whose held DecapsKey
        is a ``BitString`` SEED.

        The ek-derivation coupling for these functionalizes ``DeriveKeyPair(seed)``
        = ``G.evaluate(seed) -> slice -> ...``, which is only well-typed when the
        held DecapsKey IS the seed (the *seedbased* combiners, whose ``KeyGen``
        samples a seed and stores it as the DecapsKey). The *expanded* combiners
        hold a packed component-key tuple as the DecapsKey and call the component
        KeyGens directly (no seed, no ``DeriveKeyPair``), so ``G.evaluate`` cannot
        apply -- excluding them keeps their coupling free of the ill-typed
        ``ev_evaluate <packed key>``; they take the projection path instead (see
        :func:`_keygen_ek_packed_pairs`)."""
        seed_fields = {
            f.name for f in red.fields if isinstance(f.type, frog_ast.BitStringType)
        }
        return [p for p in _keygen_ek_key_pairs(red) if p[1] in seed_fields]

    def _keygen_ek_packed_pairs(red: frog_ast.Reduction) -> list[tuple[str, str]]:
        """:func:`_keygen_ek_key_pairs` restricted to pairs whose held DecapsKey
        is NOT a ``BitString`` seed -- the complement of
        :func:`_keygen_ek_seed_pairs`, i.e. the packed component-tuple DecapsKey
        of the *expanded* combiners. Whether that packed key really exposes the
        EncapsKey components is decided structurally by
        :func:`_keygen_ek_dk_projection`."""
        seed_fields = {
            f.name for f in red.fields if isinstance(f.type, frog_ast.BitStringType)
        }
        return [p for p in _keygen_ek_key_pairs(red) if p[1] not in seed_fields]

    def _keygen_ek_dk_projection(sch: frog_ast.Scheme) -> list[int] | None:
        """The 1-based tuple projections locating a scheme ``KeyGen``'s EncapsKey
        components inside the DecapsKey it returns alongside them.

        An *expanded*-form combiner's ``KeyGen`` ends
        ``return [[ek_a, ek_b], [dk_a, ek_a, dk_b, ek_b]];`` -- every EncapsKey
        component is also a DecapsKey component, so the held EncapsKey is a pure
        projection of the held DecapsKey (``ek = (dk.`2, dk.`4)``). Returns those
        indices, or ``None`` when the return is not two tuples of plain variables
        or some EncapsKey component is absent from the DecapsKey (the *seedbased*
        form, whose DecapsKey is the raw seed)."""
        keygen = next((m for m in sch.methods if m.signature.name == "KeyGen"), None)
        if keygen is None:
            return None
        ret = next(
            (
                s
                for s in reversed(keygen.block.statements)
                if isinstance(s, frog_ast.ReturnStatement)
            ),
            None,
        )
        if ret is None or not isinstance(ret.expression, frog_ast.Tuple):
            return None
        elems = ret.expression.values
        if len(elems) != 2:
            return None
        ek_t, dk_t = elems
        if not isinstance(ek_t, frog_ast.Tuple) or not isinstance(dk_t, frog_ast.Tuple):
            return None
        if not all(isinstance(v, frog_ast.Variable) for v in ek_t.values):
            return None
        if not all(isinstance(v, frog_ast.Variable) for v in dk_t.values):
            return None
        dk_names = [v.name for v in dk_t.values if isinstance(v, frog_ast.Variable)]
        proj: list[int] = []
        for comp in ek_t.values:
            assert isinstance(comp, frog_ast.Variable)
            if comp.name not in dk_names:
                return None
            proj.append(dk_names.index(comp.name) + 1)
        return proj or None

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

    def _wrapper_challenger_coupling(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> str:
        """Within-side ``red.<seed>{s} = <challenger>.<dk>{s}`` couplings for a
        reduction whose ``Initialize`` repacks a challenger ``Initialize`` result
        into a DIFFERENTLY-NAMED own field (the seedbased binding reduction:
        ``[ek, s_PQ_0] = challenger.Initialize()`` -> ``s_PQ_0`` IS the
        challenger's ``dk0``). The composite-seam path (``_live_state_coupling_base``)
        couples these by field NAME, so it MISSES the rename; the seedbased wrapper
        challenge tactic needs the equality in the byequiv pre to unify the game's
        decaps key with the inlined challenger's. Emitted only for the name-mismatch
        case (empty otherwise -> byte-identical; same-name is handled by composite).
        """
        conj: list[str] = []
        for step, side in ((step_a, "1"), (step_b, "2")):
            if step.reduction is None:
                continue
            red = _get_reduction(step.reduction.name)
            # pylint: disable=protected-access
            chal_ast = engine._get_game_ast(step.challenger, None)
            # pylint: enable=protected-access
            if red is None or chal_ast is None:
                continue
            # SEEDBASED signal: a ``Function<>`` (seed-derivation RO) parameter.
            # The seedbased binding reduction derives its PQ decaps key from the
            # repacked SEED (via ``derivekeypair``), so its collision branch needs
            # ``seed = challenger.dk0`` to unify with the inlined challenger. The
            # atomic (expanded) reduction lacks the Function param and decapsulates
            # with the challenger's key DIRECTLY, so it needs no coupling.
            #
            # The ``Function<>`` param was a PROXY for "seedbased wrapper", and it
            # is the wrong test: measured on CK_seedbased_HON_BIND_K_PK, NO
            # reduction there carries one, yet ``R_PQ_Bind`` repacks the
            # challenger's ``initialize`` result into differently-named fields
            # exactly as the LEAK cells' does -- so the HON hops silently lost a
            # conjunct that is both needed and true. Gate instead on the condition
            # that actually makes the conjunct meaningful AND derivable: a
            # challenger-source map with a genuine RENAME.
            # ``_challenger_source_map`` reads that repacking off the reduction's
            # own ``Initialize``, so every emitted conjunct stays structurally
            # derived rather than guessed.
            src = _challenger_source_map(red, chal_ast)
            if not any(rf != cf for rf, cf in src.items()):
                continue
            module_expr = resolver.resolve(step).module_expr
            red_base = pt.module_base_name(module_expr)
            chal_base = pt.module_base_name(pt.last_module_arg(module_expr))
            for red_fld, chal_fld in src.items():
                if red_fld == chal_fld:
                    continue  # same name: the composite name-match path handles it
                # pylint: disable=protected-access
                rf = mt._ec_field_name(red_fld)
                cf = mt._ec_field_name(chal_fld)
                # pylint: enable=protected-access
                conj.append(f"{red_base}.{rf}{{{side}}} = {chal_base}.{cf}{{{side}}}")
        return " /\\ ".join(conj)

    def _wrapper_stored_dk_coupling(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> str:
        """Within-side ``red.<dk>{s} = red.<seed>{s}`` couplings for a reduction
        whose Initialize STORES a wrapper-derived decaps key
        (``_tup <@ KEM.derivekeypair(s_PQ_0); dk_PQ_0 <- _tup[1]``).  For the
        concrete ``SeededKEMWrapper``, ``derivekeypair(seed)`` returns
        ``(ek, seed)`` so the stored decaps key EQUALS the seed -- the fact the
        hop_6 challenge tactic needs to unify R_KDF's ``decaps(dk_PQ_0, .)`` with
        R_PQ_Bind's ``decaps(s_PQ_0, .)`` (their KDF inputs coincide).  The by-name
        composite coupling misses it (``dk_PQ_0`` is only on the R_KDF side).
        Gated on a ``Function<>`` (seedbased = wrapper) param so every non-seedbased
        proof is byte-identical; EC-gated at the (clean) init hop, which establishes
        ``dk = seed`` by inlining the concrete wrapper's ``derivekeypair``.
        """
        conj: list[str] = []
        for step, side in ((step_a, "1"), (step_b, "2")):
            if step.reduction is None:
                continue
            red = _get_reduction(step.reduction.name)
            if red is None:
                continue
            if not any(
                isinstance(p.type, frog_ast.FunctionType) for p in red.parameters
            ):
                continue
            init = _find_init(red)
            if init is None:
                continue
            red_fields = {f.name for f in red.fields}
            fld_ty = {f.name: top_types.translate_type(f.type).text for f in red.fields}
            tup_seed: dict[str, str] = {}
            for stmt in init.block.statements:
                if (
                    isinstance(stmt, frog_ast.Assignment)
                    and isinstance(stmt.var, frog_ast.Variable)
                    and isinstance(stmt.value, frog_ast.FuncCall)
                    and isinstance(stmt.value.func, frog_ast.FieldAccess)
                    and stmt.value.func.name.lower() == "derivekeypair"
                    and len(stmt.value.args) == 1
                    and isinstance(stmt.value.args[0], frog_ast.Variable)
                    and stmt.value.args[0].name in red_fields
                ):
                    tup_seed[stmt.var.name] = stmt.value.args[0].name
            red_base = pt.module_base_name(resolver.resolve(step).module_expr)
            for stmt in init.block.statements:
                if (
                    isinstance(stmt, frog_ast.Assignment)
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name in red_fields
                    and isinstance(stmt.value, frog_ast.ArrayAccess)
                    and isinstance(stmt.value.the_array, frog_ast.Variable)
                    and stmt.value.the_array.name in tup_seed
                    and isinstance(stmt.value.index, frog_ast.Integer)
                    and stmt.value.index.num == 1
                ):
                    seed_fld = tup_seed[stmt.value.the_array.name]
                    # ``dk = seed`` holds ONLY for a SeededKEMWrapper (dk IS the
                    # seed) -- necessarily the SAME EC type.  A REAL KEM's T-side
                    # ``derivekeypair`` (CK/CK two-KEM) returns a distinct decaps key
                    # (``dk_T_0 : DecapsKeySpace`` != ``s_T_0 : bs_..._nseed``); emit
                    # only when the types match, else the coupling is ill-typed.
                    if fld_ty.get(stmt.var.name) != fld_ty.get(seed_fld):
                        continue
                    # pylint: disable=protected-access
                    df = mt._ec_field_name(stmt.var.name)
                    sf = mt._ec_field_name(seed_fld)
                    # pylint: enable=protected-access
                    if df != sf:
                        conj.append(
                            f"{red_base}.{df}{{{side}}} = {red_base}.{sf}{{{side}}}"
                        )
        return " /\\ ".join(conj)

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
        # ek-PROJECTION coupling (expanded PK binding): the *expanded* combiners'
        # ``KeyGen`` returns the EncapsKey components INSIDE the DecapsKey tuple,
        # so the held EncapsKey is a projection of the held DecapsKey rather than
        # a seed derivation. Same purpose as the branch above -- give the OPAQUE
        # held ``R.ek`` a form linking it to the component keys the KDF input
        # binds -- and equally SOUND, read straight off the scheme's own
        # ``KeyGen`` return AST. Emitted in the seedbased branch's ``(ek, key)``
        # pair shape so the challenge route's ``seq`` invariant restates it
        # verbatim. Declines (``None``) for a seed DecapsKey -> byte-identical.
        packed_pairs = _keygen_ek_packed_pairs(red)
        if packed_pairs and scheme is not None:
            ek_proj = _keygen_ek_dk_projection(scheme)
            if ek_proj is not None:
                for ek_f, key_f in packed_pairs:
                    # pylint: disable=protected-access
                    key_ref = f"{red_base}.{mt._ec_field_name(key_f)}{{{rs}}}"
                    ek_ref = f"{red_base}.{mt._ec_field_name(ek_f)}{{{rs}}}"
                    # pylint: enable=protected-access
                    comps = ", ".join(f"{key_ref}.`{i}" for i in ek_proj)
                    conj.append(f"({ek_ref}, {key_ref}) = (({comps}), {key_ref})")
        body = " /\\ ".join(conj)
        return f"{glob_invariant_conj} /\\ {body}" if glob_invariant_conj else body

    def _dkp_ret_elems(  # pylint: disable=too-many-return-statements
        game_step: frog_ast.Step, seed_ref: str
    ) -> list[str] | None:
        """The rendered ``derivekeypair``'s return, symbolically evaluated at
        ``seed_ref`` and split into its top-level tuple elements; ``None`` if the
        proc is not a linear chain of ev-able calls ending in a tuple return."""
        dkp_proc = (
            next((pr for pr in ec_scheme.procs if pr.name == "derivekeypair"), None)
            if ec_scheme is not None
            else None
        )
        if dkp_proc is None or len(dkp_proc.params) != 1:
            return None
        game_scheme_expr = pt.last_module_arg(resolver.resolve(game_step).module_expr)
        inner = (
            game_scheme_expr[
                game_scheme_expr.index("(") + 1 : game_scheme_expr.rindex(")")
            ]
            if "(" in game_scheme_expr
            else ""
        )
        args = [pt.module_base_name(a) for a in cc_split_args(inner)] if inner else []
        if not args:
            return None
        pmap = (
            {p.name: a for p, a in zip(ec_scheme.params, args)}
            if ec_scheme is not None
            else {}
        )

        def _ret_elems(seed_ref_inner: str) -> list[str] | None:
            env: dict[str, str] = {dkp_proc.params[0].name: seed_ref_inner}

            def _sub(text: str) -> str:
                for k in sorted(env, key=len, reverse=True):
                    text = re.sub(rf"\b{re.escape(k)}\b", env[k], text)
                return text

            for st in dkp_proc.body:
                if isinstance(st, ec_ast.VarDecl):
                    continue
                if isinstance(st, ec_ast.Return):
                    ret = _sub(st.expr).strip()
                    while ret.startswith("(") and ret.endswith(")"):
                        stripped = ret[1:-1]
                        if len(cc_split_args(stripped)) > 1:
                            return [e.strip() for e in cc_split_args(stripped)]
                        ret = stripped.strip()
                    return None
                if isinstance(st, ec_ast.Assign):
                    env[st.var] = f"({_sub(st.rhs)})"
                    continue
                if not isinstance(st, ec_ast.Call):
                    return None
                mod, dot, meth = st.callee.partition(".")
                alias = clone_alias_by_module.get(pmap.get(mod, mod)) if dot else None
                if alias is None:
                    return None
                applied = (
                    " ".join(f"({_sub(a)})" for a in cc_split_args(st.args))
                    if st.args.strip()
                    else ""
                )
                env[st.var] = f"({alias}.ev_{meth}{(' ' + applied) if applied else ''})"
            return None

        return _ret_elems(seed_ref)

    def _game_derived_field_conjuncts(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
        game: frog_ast.Game,
        game_step: frog_ast.Step,
        seed_holder: str,
        seed_flds: list[frog_ast.Field],
        gs: str,
    ) -> list[str]:
        """``<Game>.<pub_k>{gs} = <ev-form over the k-th seed>`` for every game
        field that is a NON-SEED projection of the same ``KeyGen`` its seed came
        from; ``[]`` when the shape does not hold.

        Read structurally off the game's own ``Initialize``: the parser expands
        ``[ek, dk] = K.KeyGen()`` into ``t = K.KeyGen(); ek = t[0]; dk = t[1]``,
        so the k-th ``KeyGen`` call's projections name the k-th keypair's fields.
        The seed sits at the projection index :func:`_prg_query_game_coupling`
        already validated (``DeriveKeyPair``'s seed-returning position); every
        OTHER projection is derived, and its value is the same-index element of
        the rendered ``derivekeypair`` evaluated symbolically at the seed.

        Returning ``[]`` rather than declining the whole coupling keeps every
        game without this shape exactly as it was."""
        init = next(
            (m for m in game.methods if m.signature.name.lower() == "initialize"), None
        )
        dkp_proc = (
            next((pr for pr in ec_scheme.procs if pr.name == "derivekeypair"), None)
            if ec_scheme is not None
            else None
        )
        if init is None or dkp_proc is None or len(dkp_proc.params) != 1:
            return []
        field_names = {f.name for f in game.fields}
        # The game AST here is fully INLINED: ``KeyGen`` is gone and each keypair
        # surfaces as ``t = [<derived pair>, <sampled seed>]; ek = t[0]; dk =
        # t[1]``. So the k-th keypair is the k-th such tuple local, and the SEED
        # position is the element that is exactly a sampled variable -- every
        # other element is derived material whose value is the same-index element
        # of ``derivekeypair`` at that seed.
        sampled = {
            st.var.name
            for st in init.block.statements
            if isinstance(st, frog_ast.Sample) and isinstance(st.var, frog_ast.Variable)
        }
        tuple_seed_idx: dict[str, int] = {}
        projections: list[tuple[int, int, str]] = []  # (keypair ordinal, index, field)
        for st in init.block.statements:
            if not isinstance(st, frog_ast.Assignment) or not isinstance(
                st.var, frog_ast.Variable
            ):
                continue
            val = st.value
            if isinstance(val, frog_ast.Tuple):
                idx = next(
                    (
                        i
                        for i, e in enumerate(val.values)
                        if isinstance(e, frog_ast.Variable) and e.name in sampled
                    ),
                    None,
                )
                if idx is not None:
                    tuple_seed_idx[st.var.name] = idx
            elif (
                isinstance(val, frog_ast.ArrayAccess)
                and isinstance(val.the_array, frog_ast.Variable)
                and val.the_array.name in tuple_seed_idx
                and isinstance(val.index, frog_ast.Integer)
                and st.var.name in field_names
            ):
                projections.append(
                    (
                        list(tuple_seed_idx).index(val.the_array.name),
                        val.index.num,
                        st.var.name,
                    )
                )
        if not projections:
            return []
        seed_idxs = set(tuple_seed_idx.values())
        seed_order = [f.name for f in seed_flds]
        seed_idx = (
            next(iter(seed_idxs))
            if len(seed_idxs) == 1
            and [f for k, j, f in sorted(projections) if j == next(iter(seed_idxs))]
            == seed_order
            else None
        )
        if seed_idx is None:
            return []
        # pylint: disable=protected-access
        out: list[str] = []
        for ordinal, idx, fname in sorted(projections):
            if idx == seed_idx:
                continue
            seed_name = next(
                (
                    f
                    for k, j, f in sorted(projections)
                    if k == ordinal and j == seed_idx
                ),
                None,
            )
            if seed_name is None:
                return []
            elems = _dkp_ret_elems(
                game_step, f"{seed_holder}.{mt._ec_field_name(seed_name)}{{{gs}}}"
            )
            if elems is None or idx >= len(elems):
                return []
            out.append(
                f"{seed_holder}.{mt._ec_field_name(fname)}{{{gs}}} = {elems[idx]}"
            )
        # pylint: enable=protected-access
        return out

    def _prg_query_game_coupling(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> str | None:
        """Derivation-chain coupling for a HON_BIND hop relating the plain
        theorem game to a PRG QUERY-delegate reduction (``R_PRG``): the game's
        decaps key IS the seedbased master seed (the scheme's KeyGen returns
        ``this.DeriveKeyPair(seed)`` whose decaps position is the seed param),
        while the reduction stores the DERIVED material its challenger's
        RO-backed PRG expansion produced. Couple each reduction field to its
        ev-derivation over the shared RO applied to the game's seed
        (``R.pq_keys_0{2} = KEM_PQ_c.ev_derivekeypair (slice_pq (RO.h{1}
        Game.dk0{1}))`` ...), read off the RENDERED reduction init with the
        challenger query substituted -- TRUE under the init lemma's seed
        rnd-coupling (the challenger's Real query is the same RO expansion of a
        coupled fresh seed). Pure string construction (no live_state_holders
        side effects). ``None`` off-shape -- every other proof byte-identical."""
        if step_a.reduction is None and step_b.reduction is not None:
            game_step, red_step, gs, rs = step_a, step_b, "1", "2"
        elif step_b.reduction is None and step_a.reduction is not None:
            game_step, red_step, gs, rs = step_b, step_a, "2", "1"
        else:
            return None
        assert red_step.reduction is not None
        rname = red_step.reduction.name
        if _reduction_init_delegates(rname) or not _reduction_init_queries_challenger(
            rname
        ):
            return None
        red = _get_reduction(rname)
        # pylint: disable=protected-access
        game = engine._get_game_ast(game_step.challenger, None)
        # pylint: enable=protected-access
        if red is None or game is None or not red.fields:
            return None
        # The theorem game must be the seedbased shape: scheme KeyGen returns
        # ``this.DeriveKeyPair(seed)`` (a call on a sampled seed), and the game
        # holds [ek0, dk0] with dk0 = the seed (DeriveKeyPair's decaps-position
        # return element is the seed parameter).
        scheme_name = pt.module_base_name(
            pt.last_module_arg(resolver.resolve(game_step).module_expr)
        )
        scheme_def = schemes_by_name.get(scheme_name)
        if scheme_def is None:
            return None
        keygen = next(
            (m for m in scheme_def.methods if m.signature.name.lower() == "keygen"),
            None,
        )
        dkp = next(
            (
                m
                for m in scheme_def.methods
                if m.signature.name.lower() == "derivekeypair"
            ),
            None,
        )
        if keygen is None or dkp is None or len(dkp.signature.parameters) != 1:
            return None
        kg_ret = _return_elems(keygen)
        if (
            kg_ret is None
            or len(kg_ret) != 1
            or not isinstance(kg_ret[0], frog_ast.FuncCall)
            or not isinstance(kg_ret[0].func, frog_ast.FieldAccess)
            or kg_ret[0].func.name.lower() != "derivekeypair"
        ):
            return None
        dkp_ret = _return_elems(dkp)
        seed_param = dkp.signature.parameters[0].name
        if (
            dkp_ret is None
            or len(dkp_ret) != 2
            or not isinstance(dkp_ret[1], frog_ast.Variable)
            or dkp_ret[1].name != seed_param
        ):
            return None
        # game field holding the seed = the decaps-position keygen projection:
        # the game init destructures keygen's pair into [ek0, dk0] -- the second
        # field is the seed. Identify it as the game field whose type resolves
        # to a BitString (the seed space); require exactly one.
        seed_flds = [
            f
            for f in game.fields
            if isinstance(
                (
                    top_types.resolve(f.type)
                    if not isinstance(f.type, frog_ast.BitStringType)
                    else f.type
                ),
                frog_ast.BitStringType,
            )
        ]
        if not seed_flds:
            return None
        # n KEYPAIRS (unparked 2026-07-31). The ordinal machinery below pairs
        # the k-th ``Challenger.query()`` with the k-th game seed field. The two
        # tactics it newly reaches were generalized with it: the post-init
        # derivation peel now substitutes each coupled field by its ev-FORM
        # instead of freezing it (so both sides' obligations are the same terms),
        # and ``_prg_query_init_tac`` stays gated to a single challenger query --
        # a two-keypair ``initialize`` is an honest admit until its n-sample
        # coupling is built.
        seed_holder = pt.module_base_name(resolver.resolve(game_step).module_expr)
        # ORDINAL, declaration order: the k-th ``Challenger.query()`` in the
        # reduction's init derives the k-th keypair, so it expands the k-th game
        # seed field. A single-keypair game has one of each and behaves exactly
        # as before; a TWO-keypair binding game (PK / CT_DIFFKEY) holds dk0/dk1
        # and its reduction queries twice, which the old ``exactly one seed``
        # gate rejected outright -- leaving those hops a glob-only coupling and
        # every post-init oracle on them an admit.
        # pylint: disable=protected-access
        seed_refs = [
            f"{seed_holder}.{mt._ec_field_name(f.name)}{{{gs}}}" for f in seed_flds
        ]
        # pylint: enable=protected-access
        # The expansion value the challenger's query returns, at the coupled
        # seed: an RO-materialized PRG applies the shared RO; an ABSTRACT PRG
        # (the HON proofs' `={glob G}` shape) functionalizes to its ev op, with
        # the method name read off the challenger game's query body.
        ro_map = top_types.ro_by_arrow_type()
        if ro_map:
            q_vals = [f"({next(iter(ro_map.values()))}{{{gs}}} {r})" for r in seed_refs]
        else:
            chal_expr = pt.last_module_arg(resolver.resolve(red_step).module_expr)
            prg_mod = pt.module_base_name(pt.last_module_arg(chal_expr))
            prg_alias = clone_alias_by_module.get(prg_mod)
            # pylint: disable=protected-access
            chal_ast = engine._get_game_ast(red_step.challenger, None)
            # pylint: enable=protected-access
            if prg_alias is None or chal_ast is None:
                return None
            # The challenger's query body holds exactly ONE PRG call (the game
            # side's parameters list is empty -- params live on the game file --
            # so match any FieldAccess call and require it unique by method).
            calls: list[frog_ast.FuncCall] = []

            def _collect(n: frog_ast.ASTNode) -> bool:
                if (
                    isinstance(n, frog_ast.FuncCall)
                    and isinstance(n.func, frog_ast.FieldAccess)
                    and isinstance(n.func.the_object, frog_ast.Variable)
                ):
                    calls.append(n)
                return False

            for m in chal_ast.methods:
                visitors.SearchVisitor(_collect).visit(m.block)
            meths = {cast(frog_ast.FieldAccess, c.func).name.lower() for c in calls}
            if len(meths) != 1:
                return None
            q_meth = meths.pop()
            q_vals = [f"({prg_alias}.ev_{q_meth} {r})" for r in seed_refs]
        # Walk the RENDERED reduction init: challenger query -> the RO applied
        # to the game seed; assigns substitute; calls to abstract modules
        # functionalize to their ev form. Field targets become conjuncts.
        red_mod = next(
            (
                d
                for d in ec_reductions
                if isinstance(d, ec_ast.Module) and d.name == rname
            ),
            None,
        )
        red_init = (
            next((pr for pr in red_mod.procs if pr.name == "initialize"), None)
            if red_mod is not None
            else None
        )
        if red_init is None:
            return None
        field_names = {f.name for f in red.fields}
        red_base = pt.module_base_name(resolver.resolve(red_step).module_expr)
        env: dict[str, str] = {}
        conj: list[str] = []
        n_queries = 0

        def _sub_tokens(s: str) -> str:
            for k in sorted(env, key=len, reverse=True):
                s = re.sub(rf"\b{re.escape(k)}\b", env[k], s)
            return s

        chal_param = (
            red_mod.params[-1].name if red_mod is not None and red_mod.params else None
        )
        for st in red_init.body:
            if isinstance(st, (ec_ast.VarDecl, ec_ast.Return)):
                continue
            if isinstance(st, ec_ast.Sample):
                return None  # off-shape (the PRG reduction derives, not samples)
            if isinstance(st, ec_ast.Assign):
                val = _sub_tokens(st.rhs)
            elif isinstance(st, ec_ast.Call):
                mod, dot, meth = st.callee.partition(".")
                if not dot:
                    return None
                if mod == chal_param:
                    if n_queries >= len(q_vals):
                        return None  # more queries than the game holds seeds
                    val = q_vals[n_queries]
                    n_queries += 1
                else:
                    alias = clone_alias_by_module.get(mod)
                    if alias is None:
                        return None
                    args = (
                        " ".join(f"({_sub_tokens(a)})" for a in cc_split_args(st.args))
                        if st.args.strip()
                        else ""
                    )
                    val = f"({alias}.ev_{meth}{(' ' + args) if args else ''})"
            else:
                return None
            env[st.var] = val
            if st.var in field_names:
                # pylint: disable=protected-access
                conj.append(f"{red_base}.{mt._ec_field_name(st.var)}{{{rs}}} = {val}")
                # pylint: enable=protected-access
        if not conj or len(conj) != len(field_names):
            return None
        if n_queries != len(q_vals):
            return None  # a seed the reduction never expands -> off-shape
        # -- the GAME's OWN derived fields ------------------------------------
        # A binding game holds not just the seed but the PUBLIC half of each
        # keypair (``ek0``/``ek1``), and a post-init oracle that reads them
        # (``Challenge``: ``ek0 != ek1``) needs them related to the reduction's
        # RECOMPUTED packed encaps keys. Without this the derivation peel leaves
        # exactly ``(ss_eq && ek0 <> ek1) = (ss_eq && !(pk = pk' /\ ekT = ekT'))``
        # with ``ek0``/``ek1`` opaque -- measured on the real goal
        # (``EV1.ec:58872``). Each such field IS derivable: it is the non-seed
        # projection of the same ``DeriveKeyPair`` the seed came from, so state it
        # in ev-form over the seed. TRUE and PROVEN, not assumed -- the hop's own
        # ``initialize`` lemma has to establish it or EC rejects the file.
        conj += _game_derived_field_conjuncts(
            game, game_step, seed_holder, seed_flds, gs
        )
        # The emitted conjuncts read the GAME challenger's seed field
        # (``<Game>.dk0{1}``) inside a post that must survive each abstract
        # scheme call the init peel steps over. EC refuses ``call (_: true)``
        # under such a post unless the abstract module is declared write-disjoint
        # from that challenger ("module KEM_PQ can write <Game>.dk0"), so the
        # holder has to reach the ``declare module`` restriction lists. Register
        # ONLY the two bases this coupling actually names, and only once it
        # fires -- the earlier attempt that widened ``_composite_reduction_step``
        # to get the same effect cascaded into 15+ exports' restriction lists.
        live_state_holders.update({seed_holder, red_base})
        globs = " /\\ ".join(f"={{glob {m}}}" for m in declared_module_names)
        body = " /\\ ".join(conj)
        return f"{globs} /\\ {body}" if globs else body

    def _split_conjuncts(guard: str) -> list[str]:
        """Split an EC boolean guard on its TOP-LEVEL ``&&`` (paren-aware)."""
        out: list[str] = []
        depth = 0
        cur = ""
        i = 0
        while i < len(guard):
            ch = guard[i]
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth -= 1
            if depth == 0 and guard.startswith("&&", i):
                out.append(cur.strip())
                cur = ""
                i += 2
                continue
            cur += ch
            i += 1
        if cur.strip():
            out.append(cur.strip())
        return out

    def _module_pmap(mod: ec_ast.Module, applied: str) -> dict[str, str]:
        """Map a module's FORMAL parameter names to the instances it is applied
        to (``R(KEM_PQ, KEM_T, ...)`` -> ``{K: KEM_PQ, ...}``). A rendered proc
        body calls its formal parameter, so this is what turns a callee into the
        declared module whose ``_det`` axiom discharges it."""
        inner = (
            applied[applied.index("(") + 1 : applied.rindex(")")]
            if "(" in applied
            else ""
        )
        args = [pt.module_base_name(a) for a in cc_split_args(inner)] if inner else []
        return {p.name: a for p, a in zip(mod.params, args)}

    def _twin_collision_branch(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements,too-many-arguments,too-many-positional-arguments
        split_step: frog_ast.Step,
        lproc: ec_ast.Proc,
        split_if: ec_ast.If,
        plain_tail: list[ec_ast.EcStmt],
        plain_pmap: dict[str, str],
        env: dict[str, str],
        ps: str,
        os_: str,
    ) -> list[str] | None:
        """The twin case-split's COLLISION branch, or ``None`` off-shape.

        Shape: the splitting side forwards the collision to its inner binding
        challenger with a single un-inlined functor call, while the plain side
        recomputes the game boolean from deterministic calls. The branch
        ``inline{os}``s that call (``inline *`` does NOT reach a functor
        application), functionalises BOTH sides' deterministic tails with their
        ``_det`` axioms, and then reduces the two win conditions to each other
        by inverting the KDF-input concat -- term-free, see
        :func:`challenge_common.concat_collision_peel`.

        Everything is read off the ASTs: the challenger's own rendered proc
        supplies the calls to peel, its module application supplies the
        formal->instance map, and the concat NESTING supplies the peel depth.
        """
        then_exec = [
            s
            for s in split_if.then_body
            if not isinstance(s, (ec_ast.VarDecl, ec_ast.Return))
        ]
        if len(then_exec) != 1 or not isinstance(then_exec[0], ec_ast.Call):
            return None
        chal_call = then_exec[0]
        chal_expr = pt.last_module_arg(resolver.resolve(split_step).module_expr)
        chal_qual = pt.module_base_name(chal_expr)
        chal_mod = next(
            (
                d
                for d in theory_game_decls + foreign_game_decls
                if isinstance(d, ec_ast.Module)
                and d.name == chal_qual.rpartition(".")[2]
            ),
            None,
        )
        if chal_mod is None:
            return None
        cproc = next(
            (
                p
                for p in chal_mod.procs
                if p.name == chal_call.callee.rpartition(".")[2]
            ),
            None,
        )
        if cproc is None:
            return None
        cpmap = _module_pmap(chal_mod, chal_expr)
        cargs = cc_split_args(chal_call.args) if chal_call.args.strip() else []
        if len(cargs) != len(cproc.params):
            return None
        param_sub = {p.name: a for p, a in zip(cproc.params, cargs)}
        # pylint: disable-next=protected-access
        field_names = {f.name for f in chal_mod.module_vars}
        wrapper_params = {p.name for p in lproc.params}
        ident = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

        def _peelable(
            stmts: list[ec_ast.EcStmt], pmap: dict[str, str], resolve_args: bool
        ) -> tuple[list[tuple[str, str, list[str]]], list[str], list[str]] | None:
            """``(calls, glob modules, free arg terms)`` for a deterministic tail."""
            calls: list[tuple[str, str, list[str]]] = []
            mods: list[str] = []
            frees: list[str] = []
            for st in stmts:
                if isinstance(st, (ec_ast.VarDecl, ec_ast.Return, ec_ast.Assign)):
                    continue  # declarations, and assigns absorbed by ``sp``/``wp``
                if not isinstance(st, ec_ast.Call):
                    return None
                mod, dot, meth = st.callee.partition(".")
                mod = pmap.get(mod, mod)
                if not dot or meth not in det_methods_by_module.get(mod, set()):
                    return None
                if mod not in mods:
                    mods.append(mod)
                args = cc_split_args(st.args) if st.args.strip() else []
                out_args: list[str] = []
                for arg in args:
                    term = cc_subst(arg, param_sub) if resolve_args else arg
                    for name in ident.findall(term):
                        if resolve_args and name not in field_names | wrapper_params:
                            return None
                        if name not in frees:
                            frees.append(name)
                    out_args.append(term)
                calls.append((mod, meth, out_args))
            return calls, mods, frees

        chal_side = _peelable(list(cproc.body), cpmap, True)
        plain_side = _peelable(plain_tail, plain_pmap, False)
        if chal_side is None or plain_side is None or not chal_side[0]:
            return None
        c_calls, c_mods, c_frees = chal_side
        p_calls, p_mods, _p_free = plain_side
        # The plain side's call ARGUMENTS are frozen whole (they are the KDF
        # inputs -- locals whose value the seq invariant already pins), not by
        # identifier, so a compound argument still freezes.
        p_args: list[str] = []
        for _m, _me, args in p_calls:
            for arg in args:
                if arg not in p_args:
                    p_args.append(arg)

        cg = {m: f"cgv{i}" for i, m in enumerate(c_mods)}
        cf = {n: f"cfv{i}" for i, n in enumerate(c_frees)}
        pg = {m: f"pgv{i}" for i, m in enumerate(p_mods)}
        pa = {a: f"pav{i}" for i, a in enumerate(p_args)}
        frozen = (
            [f"(glob {m})" "{" f"{os_}" "}" for m in c_mods]
            + [
                (
                    f"{chal_qual}.{n}" "{" f"{os_}" "}"
                    if n in field_names
                    else f"{n}" "{" f"{os_}" "}"
                )
                for n in c_frees
            ]
            + [f"(glob {m})" "{" f"{ps}" "}" for m in p_mods]
            + [f"{a}" "{" f"{ps}" "}" for a in p_args]
        )
        binders = (
            [cg[m] for m in c_mods]
            + [cf[n] for n in c_frees]
            + [pg[m] for m in p_mods]
            + [pa[a] for a in p_args]
        )
        # -- the term-free concat peel + encoding injectivity -----------------
        # The guard may be a CONJUNCTION (the CT binding reductions forward only
        # when the KDF inputs collide AND the PQ ciphertexts differ). Peel the
        # conjunct that is a KDF-input equality; the others are side conditions
        # the leaf's ``smt`` gets from the same hypothesis.
        collision_eq = None
        for conjunct in _split_conjuncts(split_if.guard):
            lhs, sep, rhs = conjunct.strip().strip("()").partition(" = ")
            if sep and lhs.strip() in env and rhs.strip() in env:
                collision_eq = lhs.strip()
                break
        if collision_eq is None:
            return None
        peel, concat_ops, inj_methods = cc_concat_peel(env[collision_eq], inj_ev_ops)
        if not peel or not concat_ops:
            return None
        for op in sorted(concat_ops):
            top_types.request_concat_inj(op)
        inj_method_requests.update(inj_methods)
        return [
            f"+ rcondt{{{os_}}} 1; first by auto.",
            f"  inline{{{os_}}} 1.",
            "  sp.",
            f"  exists* {', '.join(frozen)}.",
            f"  elim* => {' '.join(binders)}.",
            "  wp.",
            *[
                f"  call{{{ps}}} ({m}_{me}_det {pg[m]}"
                + "".join(f" {pa[a]}" for a in args)
                + ")."
                for m, me, args in reversed(p_calls)
            ],
            *[
                f"  call{{{os_}}} ({m}_{me}_det {cg[m]}"
                + "".join(f" {cc_subst(a, cf)}" for a in args)
                + ")."
                for m, me, args in reversed(c_calls)
            ],
            "  skip => />. move => &1 &2 h.",
            *[f"  {ln}" for ln in peel],
            "  smt().",
        ]

    def _chal_proc_of(
        step: frog_ast.Step, meth: str
    ) -> tuple[str, ec_ast.Proc, dict[str, str]] | None:
        """``(<qualified challenger module expr>, <its proc>, <its param map>)``
        for the inner challenger a reduction step forwards to.

        The param map is the CHALLENGER's own, not the reduction's: a game module
        calls its own formal scheme parameter (``K.decaps``), which the
        reduction's map does not mention."""
        expr = pt.last_module_arg(resolver.resolve(step).module_expr)
        base = pt.module_base_name(expr).rpartition(".")[2]
        mod = next(
            (
                d
                for d in theory_game_decls + foreign_game_decls
                if isinstance(d, ec_ast.Module) and d.name == base
            ),
            None,
        )
        if mod is None:
            return None
        proc = next((p for p in mod.procs if p.name == meth), None)
        return None if proc is None else (expr, proc, _module_pmap(mod, expr))

    def _twin_both_split_tail(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements,too-many-arguments,too-many-positional-arguments
        split_step: frog_ast.Step,
        plain_step: frog_ast.Step,
        split_if: ec_ast.If,
        plain_tail: list[ec_ast.EcStmt],
        split_pmap: dict[str, str],
        ps: str,
        os_: str,
        guard_at_os: str,
    ) -> list[str] | None:
        """The 2x2 tail: BOTH sides case-split, on DIFFERENT guards.

        The last binding hop pits ``R o <Bind>_Unbreakable`` (splitting on the
        KDF-input collision; its forward returns a constant after dead decaps)
        against ``R' o KDFCollisionResistance_Breakable`` (splitting on the
        encaps-key collision; its forward recomputes the KDF outputs). Both
        sides denote ``H k0 = H k1 /\\ ek0 <> ek1 /\\ k0 <> k1``, but neither
        says so syntactically, so four leaves are needed.

        Every leaf is a one-sided ``_det`` peel of whichever calls survive it;
        the two constants meet by ``=> />``, the mixed leaves by ``/#`` from the
        seq invariant's couplings. ``None`` off-shape.
        """
        # -- the splitting side: forward in the THEN branch, recompute in ELSE --
        then_exec = [
            s
            for s in split_if.then_body
            if not isinstance(s, (ec_ast.VarDecl, ec_ast.Return))
        ]
        if len(then_exec) != 1 or not isinstance(then_exec[0], ec_ast.Call):
            return None
        s_call = then_exec[0]
        s_chal = _chal_proc_of(split_step, s_call.callee.rpartition(".")[2])
        if s_chal is None:
            return None
        s_expr, s_proc, s_cpmap = s_chal
        s_args = cc_split_args(s_call.args) if s_call.args.strip() else []
        if len(s_args) != len(s_proc.params):
            return None
        s_qual = pt.module_base_name(s_expr)
        # pylint: disable-next=protected-access
        s_mod_fields = {
            f.name: f"{s_qual}.{f.name}"
            for d in theory_game_decls + foreign_game_decls
            if isinstance(d, ec_ast.Module) and d.name == s_qual.rpartition(".")[2]
            for f in d.module_vars
        }
        g1 = _calls_freeze_peel(
            list(s_proc.body),
            s_cpmap,
            os_,
            {p.name: a for p, a in zip(s_proc.params, s_args)},
            s_mod_fields,
            "sq",
        )
        # -- the plain side: assigns then an ``if`` (constant / forward) --------
        p_if = next((s for s in plain_tail if isinstance(s, ec_ast.If)), None)
        if p_if is None or any(
            not isinstance(s, (ec_ast.Assign, ec_ast.If)) for s in plain_tail
        ):
            return None
        p_calls = [
            s
            for b in (p_if.then_body, p_if.else_body)
            for s in b
            if isinstance(s, ec_ast.Call)
        ]
        if len(p_calls) != 1:
            return None
        p_chal = _chal_proc_of(plain_step, p_calls[0].callee.rpartition(".")[2])
        if p_chal is None:
            return None
        p_expr, p_proc, p_cpmap = p_chal
        p_args = cc_split_args(p_calls[0].args) if p_calls[0].args.strip() else []
        if len(p_args) != len(p_proc.params):
            return None
        g2 = _calls_freeze_peel(
            list(p_proc.body),
            p_cpmap,
            ps,
            {p.name: a for p, a in zip(p_proc.params, p_args)},
            {},
            "pq",
        )
        # -- the splitting side's ELSE branch (its own recomputation) ----------
        g3 = _calls_freeze_peel(list(split_if.else_body), split_pmap, os_, {}, {}, "eq")
        if g1 is None or g2 is None or g3 is None:
            return None
        s_inline = f"inline{{{os_}}} {s_expr}.{s_call.callee.rpartition('.')[2]}."
        p_inline = f"inline{{{ps}}} {p_expr}.{p_calls[0].callee.rpartition('.')[2]}."
        return [
            # ``sp`` BEFORE the case, so BOTH branches get the plain side's
            # leading encaps-key packing consumed (after the case it would apply
            # to the first goal only).
            "sp.",
            f"case ({guard_at_os}).",
            # A: the KDF inputs collide -> the splitting side forwards, and its
            # challenger yields the constant. The plain side's own split decides
            # nothing (its forward's ``k0 <> k1`` conjunct is false here), so
            # both of ITS branches must be shown constant too.
            f"+ rcondt{{{os_}}} 1; first by auto.",
            f"  {s_inline}",
            f"  {p_inline}",
            f"  if{{{ps}}}.",
            f"  + exists* {', '.join(g1[0])}.",
            f"    elim* => {' '.join(g1[1])}.",
            "    wp.",
            *[f"    {ln}" for ln in g1[2]],
            "    wp; skip => />.",
            f"  exists* {', '.join(g1[0] + g2[0])}.",
            f"  elim* => {' '.join(g1[1] + g2[1])}.",
            "  wp.",
            *[f"  {ln}" for ln in g1[2]],
            *[f"  {ln}" for ln in g2[2]],
            "  wp; skip => /#.",
            # B: no KDF collision -> the splitting side recomputes. Now the
            # PLAIN side's split decides: equal encaps keys give the constant on
            # both sides (through the hop's coupling), unequal ones give the same
            # recomputation twice, which couples two-sided.
            f"rcondf{{{os_}}} 1; first by auto.",
            f"{p_inline}",
            f"if{{{ps}}}.",
            "+ wp.",
            f"  exists* {', '.join(g3[0])}.",
            f"  elim* => {' '.join(g3[1])}.",
            *[f"  {ln}" for ln in g3[2]],
            "  wp; skip => /#.",
            "wp.",
            "do ! (wp; call (_: true)).",
            "wp; skip => /#.",
        ]

    def _twin_challenge_one_oracle(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
        step_a: frog_ast.Step,
        step_b: frog_ast.Step,
        lproc: ec_ast.Proc,
        rproc: ec_ast.Proc,
    ) -> list[str] | None:
        """One oracle's twin-prefix case-split tactic, or ``None`` off-shape."""

        def _exec(proc: ec_ast.Proc) -> list[ec_ast.EcStmt]:
            return [
                st
                for st in proc.body
                if not isinstance(st, (ec_ast.VarDecl, ec_ast.Return))
            ]

        lst, rst = _exec(lproc), _exec(rproc)
        l_ifs = [st for st in lst if isinstance(st, ec_ast.If)]
        r_ifs = [st for st in rst if isinstance(st, ec_ast.If)]
        # At most one ``if`` per side, and the SPLIT side's is its LAST statement
        # (the collision forward). The other side may itself case-split further
        # on (the last hop of a binding chain has BOTH sides splitting, on
        # different guards); its ``if`` then lands in the tail, past the twin
        # prefix, which is where the tail builder deals with it.
        if len(l_ifs) > 1 or len(r_ifs) > 1 or not (l_ifs or r_ifs):
            return None

        def _twin_prefix(
            plain: list[ec_ast.EcStmt], split: list[ec_ast.EcStmt]
        ) -> bool:
            """Is ``split``'s trailing ``if`` the case split, with a twin prefix?

            TWIN check: index-wise same statement KIND. A ``Call`` may differ in
            callee (that is the delegation), an ``Assign`` may differ in RHS (the
            encaps-key repack) -- both reconciled by the hop's coupling.
            """
            if not split or not isinstance(split[-1], ec_ast.If):
                return False
            pre_s, pre_p = split[:-1], plain[: len(split) - 1]
            if len(pre_p) != len(pre_s) or not pre_p:
                return False
            for a, b in zip(pre_p, pre_s):
                if isinstance(a, ec_ast.Call) != isinstance(b, ec_ast.Call):
                    return False
                if not isinstance(a, (ec_ast.Call, ec_ast.Assign)):
                    return False
            return True

        # Orientation is DERIVED, not assumed: when both sides split, only the
        # one whose ``if`` closes a twin prefix qualifies (the other's prefix is
        # longer by the statements it packs before its own ``if``, so the
        # index-wise check runs off the end of this one).
        if _twin_prefix(rst, lst):
            plain_stmts, split_stmts, ps, iss = rst, lst, "2", "1"
        elif _twin_prefix(lst, rst):
            plain_stmts, split_stmts, ps, iss = lst, rst, "1", "2"
        else:
            return None
        split_if = split_stmts[-1]
        assert isinstance(split_if, ec_ast.If)
        prefix_split = split_stmts[:-1]
        prefix_plain = plain_stmts[: len(prefix_split)]

        # -- formal-param -> declared-instance maps, per side -----------------
        _pmap = _module_pmap

        plain_step = step_a if ps == "1" else step_b
        split_step = step_b if ps == "1" else step_a
        assert plain_step.reduction is not None and split_step.reduction is not None
        plain_mod = next(
            (
                d
                for d in ec_reductions
                if isinstance(d, ec_ast.Module) and d.name == plain_step.reduction.name
            ),
            None,
        )
        if plain_mod is None:
            return None
        plain_expr = resolver.resolve(plain_step).module_expr
        pmap = _pmap(plain_mod, plain_expr)
        plain_base = pt.module_base_name(plain_expr)
        split_base = pt.module_base_name(resolver.resolve(split_step).module_expr)

        # -- ev-form environments, built from the PLAIN side only --------------
        # TWO of them: the seq invariant must name PROGRAM variables, while a
        # ``call`` argument is a proof term and must name the ``exists*`` binder.
        # Same walk, different seeds.
        def _walk(
            seed: dict[str, str],
        ) -> tuple[dict[str, str], list[str], dict[str, str]] | None:
            env = dict(seed)
            globs: dict[str, str] = {}
            terms: list[str] = []  # per prefix index; "" for assigns

            def _sub(text: str) -> str:
                if not env:
                    return text
                pat = "|".join(re.escape(k) for k in sorted(env, key=len, reverse=True))
                return re.sub(rf"\b({pat})\b", lambda m: env[m.group(1)], text)

            for st in prefix_plain:
                if isinstance(st, ec_ast.Assign):
                    env[st.var] = f"({_sub(st.rhs)})"
                    terms.append("")
                    continue
                assert isinstance(st, ec_ast.Call)
                mod, dot, meth = st.callee.partition(".")
                mod = pmap.get(mod, mod)
                if not dot or meth not in det_methods_by_module.get(mod, set()):
                    return None  # a probabilistic call has no ``_det`` axiom
                alias = clone_alias_by_module.get(mod)
                if alias is None:
                    return None
                args = (
                    [_sub(a) for a in cc_split_args(st.args)] if st.args.strip() else []
                )
                globs.setdefault(mod, f"g_{mod}")
                applied = "".join(f" ({a})" for a in args)
                terms.append(f"{mod}_{meth}_det {globs[mod]}{applied}")
                env[st.var] = (
                    f"({alias}.ev_{meth}" + "".join(f" ({a})" for a in args) + ")"
                    if args
                    else f"({alias}.ev_{meth})"
                )
            return env, terms, globs

        # pylint: disable=protected-access
        prog_seed = {
            f.name: f"{plain_base}.{f.name}" "{" f"{ps}" "}"
            for f in plain_mod.module_vars
        }
        # pylint: enable=protected-access
        prog_seed.update({p.name: f"{p.name}" "{" f"{ps}" "}" for p in lproc.params})
        # pylint: disable=protected-access
        term_seed = {f.name: f"fv_{f.name}" for f in plain_mod.module_vars}
        # pylint: enable=protected-access
        term_seed.update({p.name: f"av_{p.name}" for p in lproc.params})
        prog_walk = _walk(prog_seed)
        term_walk = _walk(term_seed)
        if prog_walk is None or term_walk is None:
            return None
        env = prog_walk[0]
        call_terms, glob_of = term_walk[1], term_walk[2]
        if not glob_of:
            return None

        def _peel_side(side: str) -> list[str]:
            lines: list[str] = []
            for term in reversed(call_terms):
                if not term:
                    continue
                lines.append("wp.")
                lines.append(f"call{{{side}}} ({term}).")
            return lines

        # -- the seq invariant: every prefix local, in ev-form, on BOTH sides ---
        # Same ev text for the two memories: that IS the twin property, and the
        # hop's coupling is what makes it true.
        locals_l = {d.name for d in lproc.body if isinstance(d, ec_ast.VarDecl)}
        locals_r = {d.name for d in rproc.body if isinstance(d, ec_ast.VarDecl)}
        carried = [
            st.var
            for st in prefix_plain
            if isinstance(st, (ec_ast.Assign, ec_ast.Call))
            and st.var in locals_l
            and st.var in locals_r
        ]
        globs = " /\\ ".join(f"={{glob {m}}}" for m in declared_module_names)
        params_eq = (
            "={" + ", ".join(p.name for p in lproc.params) + "}" if lproc.params else ""
        )
        # The hop's OWN couplings must ride through the `seq` too. Measured on the
        # real else leaf: its post demands `pq_keys_0{1}.`1 = <PQchal>.ek0{2}` and
        # the splitting side's `ek_PQ_0{2}` to agree with it, and NOTHING in the
        # post-prefix program establishes either -- so without them that branch is
        # unprovable. They hold on entry and the prefix writes none of those
        # fields, so carrying them is free.
        hop_coupling = [
            c
            for c in _live_state_coupling(step_a, step_b).split(" /\\ ")
            if not c.startswith("={")
        ]
        inv_parts = (
            [g for g in (globs, params_eq) if g]
            + [
                f"{v}" "{" f"{sd}" "}" f" = {env[v]}"
                for v in carried
                for sd in ("1", "2")
            ]
            + hop_coupling
        )
        frozen = (
            [f"(glob {m})" "{" f"{ps}" "}" for m in glob_of]
            # pylint: disable-next=protected-access
            + [f"{plain_base}.{f.name}" "{" f"{ps}" "}" for f in plain_mod.module_vars]
            + [f"{p.name}" "{" f"{ps}" "}" for p in lproc.params]
        )
        binders = (
            list(glob_of.values())
            # pylint: disable-next=protected-access
            + [f"fv_{f.name}" for f in plain_mod.module_vars]
            + [f"av_{p.name}" for p in lproc.params]
        )
        # -- the case split ----------------------------------------------------
        # ``case`` on the splitting side's own ``if`` guard, then:
        #   * COLLISION branch -- ``_twin_collision_branch`` (``inline{os} 1`` the
        #     forwarded challenger, functionalise both tails, invert the KDF
        #     concat term-free);
        #   * ELSE branch -- both sides run the same recomputation, so the plain
        #     two-sided call peel closes it from the seq invariant's couplings.
        # If the collision branch is off-shape the whole split is left open: a
        # tactic that provably fails turns an EC-ACCEPTED proof into a rejected
        # one, which is strictly worse than a tagged admit.
        os_ = "2" if ps == "1" else "1"
        del split_base, iss
        collision = _twin_collision_branch(
            split_step,
            lproc,
            split_if,
            plain_stmts[len(prefix_split) :],
            pmap,
            env,
            ps,
            os_,
        )
        # ``case`` on the splitting side's own guard, with EVERY name it reads
        # qualified to that memory. Qualifying just the two sides of a plain
        # ``a = b`` is not enough: the CT reductions guard on a CONJUNCTION that
        # also mentions the proc's parameters (``ct0.`1 <> ct1.`1``).
        split_proc = lproc if ps == "2" else rproc
        split_names = {
            d.name for d in split_proc.body if isinstance(d, ec_ast.VarDecl)
        } | {p.name for p in split_proc.params}
        guard_at_os = re.sub(
            r"\b[A-Za-z_][A-Za-z0-9_]*\b",
            lambda m: (
                m.group(0) + "{" + os_ + "}"
                if m.group(0) in split_names
                else m.group(0)
            ),
            split_if.guard,
        )
        both = (
            None
            if collision is not None
            else _twin_both_split_tail(
                split_step,
                plain_step,
                split_if,
                plain_stmts[len(prefix_split) :],
                _module_pmap(
                    next(
                        d
                        for d in ec_reductions
                        if isinstance(d, ec_ast.Module)
                        and split_step.reduction is not None
                        and d.name == split_step.reduction.name
                    ),
                    resolver.resolve(split_step).module_expr,
                ),
                ps,
                os_,
                guard_at_os,
            )
        )
        tail: list[str] = (
            [
                f"case ({guard_at_os}).",
                *collision,
                f"rcondf{{{os_}}} 1; first by move => &m; skip.",
                "do ! (wp; call (_: true)).",
                "wp; skip => /#.",
            ]
            if collision is not None
            else (
                list(both)
                if both is not None
                else [
                    # Neither tail shape could be built from the ASTs (the
                    # forwarded call, a challenger's own tail, or the KDF concat
                    # nesting did not match). Stay honest rather than guess.
                    "admit.",
                ]
            )
        )
        return [
            f"seq {len(prefix_plain)} {len(prefix_split)} : ({' /\\ '.join(inv_parts)}).",
            "+ inline *.",
            f"exists* {', '.join(frozen)}.",
            f"elim* => {' '.join(binders)}.",
            *_peel_side(ps),
            *_peel_side(os_),
            "wp; skip => />.",
            *tail,
        ]

    def _calls_freeze_peel(  # pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
        stmts: list[ec_ast.EcStmt],
        pmap: dict[str, str],
        side: str,
        param_sub: dict[str, str],
        qualify: dict[str, str],
        tag: str,
    ) -> tuple[list[str], list[str], list[str]] | None:
        """``(frozen, binders, peel lines)`` for peeling a deterministic call
        list ONE-SIDED with the callees' ``<M>_<m>_det`` axioms.

        ``param_sub`` rewrites a callee proc's FORMAL parameter names into the
        call-site expressions (needed when the statements come from an inlined
        challenger); ``qualify`` maps a bare identifier to the EC reference that
        names it at ``side`` (a challenger field needs its module prefix).
        ``None`` if any statement is not a deterministic call.
        """
        calls: list[tuple[str, str, list[str]]] = []
        mods: list[str] = []
        frees: list[str] = []
        ident = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
        for st in stmts:
            if isinstance(st, (ec_ast.VarDecl, ec_ast.Return, ec_ast.Assign)):
                continue
            if not isinstance(st, ec_ast.Call):
                return None
            mod, dot, meth = st.callee.partition(".")
            mod = pmap.get(mod, mod)
            if not dot or meth not in det_methods_by_module.get(mod, set()):
                return None
            if mod not in mods:
                mods.append(mod)
            args = [
                cc_subst(a, param_sub)
                for a in (cc_split_args(st.args) if st.args.strip() else [])
            ]
            for arg in args:
                for name in ident.findall(arg):
                    if name not in frees:
                        frees.append(name)
            calls.append((mod, meth, args))
        if not calls:
            return None
        gb = {m: f"{tag}g{i}" for i, m in enumerate(mods)}
        vb = {n: f"{tag}v{i}" for i, n in enumerate(frees)}
        frozen = [f"(glob {m})" "{" f"{side}" "}" for m in mods] + [
            f"{qualify.get(n, n)}" "{" f"{side}" "}" for n in frees
        ]
        binders = [gb[m] for m in mods] + [vb[n] for n in frees]
        peel: list[str] = []
        for mod, meth, args in reversed(calls):
            peel.append(
                f"call{{{side}}} ({mod}_{meth}_det {gb[mod]}"
                + "".join(f" ({cc_subst(a, vb)})" for a in args)
                + ")."
            )
        return frozen, binders, peel

    def _dead_branch_inlines(
        branch_if: ec_ast.If,
        chal_expr: str,
        pmap: dict[str, str],
        side: str,
    ) -> list[str] | None:
        """The ``inline{side}`` lines needed to make an ``if`` whose branches are
        constant-or-forwarded-call crossable by ``wp``; ``None`` if some branch
        does real work.

        ``inline *`` does NOT reach a functor application, so the forwarded
        challenger has to be named explicitly.
        """
        chal_base = pt.module_base_name(chal_expr)
        lines: list[str] = []
        for branch in (branch_if.then_body, branch_if.else_body):
            for inner in branch:
                if isinstance(inner, ec_ast.Assign):
                    continue
                if not isinstance(inner, ec_ast.Call):
                    return None
                callee_base = inner.callee.partition(".")[0]
                if (
                    pt.module_base_name(inner.callee) != chal_base
                    and not inner.callee.startswith(f"{chal_base}.")
                    and pmap.get(callee_base) is None
                ):
                    return None
                line = (
                    f"inline{{{side}}} {chal_expr}.{inner.callee.rpartition('.')[2]}."
                )
                if line not in lines:
                    lines.append(line)
        return lines

    def _dead_side_oracle_tac(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
        step_a: frog_ast.Step,
        step_b: frog_ast.Step,
        lproc: ec_ast.Proc,
        rproc: ec_ast.Proc,
    ) -> list[str] | None:
        """One oracle where the two sides agree because BOTH are constant, but
        only one of them says so syntactically; ``None`` off-shape.

        The last hop of a binding chain relates a reduction whose oracle has
        already collapsed to ``return <const>;`` against one that still runs the
        whole deterministic KDF computation and an ``if`` whose branches BOTH
        yield that same constant (one directly, one by forwarding to an
        Unbreakable challenger that returns it). ``sim`` cannot relate them --
        one side has abstract calls the other does not -- and it is not a
        reorder, so the whole oracle used to fall to a guided admit.

        The route: inline the forwarded challenger (``inline{i} <expr>.<proc>``;
        ``inline *`` does not reach a functor application), which turns the
        ``if`` into pure assignments that ``wp`` can cross, then drop the live
        side's deterministic calls ONE-SIDED with their glob-preserving
        ``<M>_<m>_det`` axioms, back to front.
        """
        if step_a.reduction is None or step_b.reduction is None:
            return None

        def _exec(proc: ec_ast.Proc) -> list[ec_ast.EcStmt]:
            return [
                st
                for st in proc.body
                if not isinstance(st, (ec_ast.VarDecl, ec_ast.Return))
            ]

        lst, rst = _exec(lproc), _exec(rproc)
        # Exactly one side is already the bare constant.
        if bool(lst) == bool(rst):
            return None
        live_proc, live_step, ls = (lproc, step_a, "1") if lst else (rproc, step_b, "2")
        live = lst or rst
        live_mod = next(
            (
                d
                for d in ec_reductions
                if isinstance(d, ec_ast.Module)
                and live_step.reduction is not None
                and d.name == live_step.reduction.name
            ),
            None,
        )
        if live_mod is None:
            return None
        live_expr = resolver.resolve(live_step).module_expr
        pmap = _module_pmap(live_mod, live_expr)
        live_base = pt.module_base_name(live_expr)
        chal_expr = pt.last_module_arg(live_expr)

        # -- ev-form environment over the live body, and the calls to peel -----
        env: dict[str, str] = {f.name: f"fdv_{f.name}" for f in live_mod.module_vars}
        env.update({p.name: f"adv_{p.name}" for p in live_proc.params})
        calls: list[tuple[str, str, list[str]]] = []
        glob_of: dict[str, str] = {}
        inlines: list[str] = []
        for st in live:
            if isinstance(st, ec_ast.Assign):
                env[st.var] = f"({cc_subst(st.rhs, env)})"
                continue
            if isinstance(st, ec_ast.If):
                # Every branch must yield a CONSTANT, reached either directly or
                # through a forwarded challenger call. A branch that computes
                # anything else is a different shape -- decline.
                branch_inline = _dead_branch_inlines(st, chal_expr, pmap, ls)
                if branch_inline is None:
                    return None
                for line in branch_inline:
                    if line not in inlines:
                        inlines.append(line)
                continue
            if not isinstance(st, ec_ast.Call):
                return None
            mod, dot, meth = st.callee.partition(".")
            mod = pmap.get(mod, mod)
            if not dot or meth not in det_methods_by_module.get(mod, set()):
                return None
            alias = clone_alias_by_module.get(mod)
            if alias is None:
                return None
            args = (
                [cc_subst(a, env) for a in cc_split_args(st.args)]
                if st.args.strip()
                else []
            )
            glob_of.setdefault(mod, f"gdv{len(glob_of)}")
            calls.append((mod, meth, args))
            env[st.var] = (
                f"({alias}.ev_{meth}" + "".join(f" ({a})" for a in args) + ")"
                if args
                else f"({alias}.ev_{meth})"
            )
        if not calls or not inlines:
            return None

        frozen = (
            [f"(glob {m})" "{" f"{ls}" "}" for m in glob_of]
            # pylint: disable-next=protected-access
            + [f"{live_base}.{f.name}" "{" f"{ls}" "}" for f in live_mod.module_vars]
            + [f"{p.name}" "{" f"{ls}" "}" for p in live_proc.params]
        )
        binders = (
            list(glob_of.values())
            # pylint: disable-next=protected-access
            + [f"fdv_{f.name}" for f in live_mod.module_vars]
            + [f"adv_{p.name}" for p in live_proc.params]
        )
        peel: list[str] = []
        for mod, meth, args in reversed(calls):
            peel.append("wp.")
            peel.append(
                f"call{{{ls}}} ({mod}_{meth}_det {glob_of[mod]}"
                + "".join(f" ({a})" for a in args)
                + ")."
            )
        return [
            *inlines,
            f"exists* {', '.join(frozen)}.",
            f"elim* => {' '.join(binders)}.",
            *peel,
            "wp; skip => />.",
        ]

    def _twin_challenge_oracle_tacs(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> dict[str, list[str]] | None:
        """Whole-oracle tactics for a TWIN-PREFIX binding ``Challenge``
        case-split between two reductions, keyed by oracle name; ``None``
        off-shape.

        Shape: both endpoints run the same expanded KDF backbone, but one
        delegates part of it to an inner binding challenger and forwards a
        KDF-input collision to that challenger's own ``Challenge``. The two
        rendered bodies are statement-wise TWINS up to the ``if``.

        Built here rather than in the chain emitter because EC's ``seq`` and
        ``rcondt``/``rcondf`` count RENDERED WRAPPER statements, and the flat
        states cannot supply those indices once the engine has inlined a
        challenger oracle (one flat statement, three under EC's ``inline``).

        The inner challenger's rendered module is never consulted: the ev-form
        environment is built from the PLAIN side's prefix and asserted for BOTH
        sides -- that IS the twin property, and the hop's coupling is what
        justifies it. A challenger-delegated call is peeled with the det axiom of
        the callee the plain side uses at that index, its key argument supplied as
        the plain side's coupled term; EC discharges the resulting equality from
        the coupling. Validated shape:
        ``ec_templates/binding_challenge_twin_casesplit.ec``.
        """
        if step_a.reduction is None or step_b.reduction is None:
            return None
        mods: list[ec_ast.Module] = []
        for st in (step_a, step_b):
            assert st.reduction is not None
            mod = next(
                (
                    d
                    for d in ec_reductions
                    if isinstance(d, ec_ast.Module) and d.name == st.reduction.name
                ),
                None,
            )
            if mod is None:
                return None
            mods.append(mod)
        if len(mods) != 2:
            return None
        lmod, rmod = mods[0], mods[1]
        out: dict[str, list[str]] = {}
        for lproc in lmod.procs:
            rproc = next((p for p in rmod.procs if p.name == lproc.name), None)
            if rproc is None or lproc.name == "initialize":
                continue
            tac = _twin_challenge_one_oracle(step_a, step_b, lproc, rproc)
            if tac is None:
                tac = _dead_side_oracle_tac(step_a, step_b, lproc, rproc)
            if tac is not None:
                out[lproc.name] = tac
        return out or None

    def _keygenequiv_init_tac(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> list[str] | None:
        """Whole-init tactic for a KeyGenEquiv hop (CK hop_4 / hop_14), or
        ``None`` off-shape.

        Both reductions build the same n keypairs but INTERLEAVE differently:
        one alternates ``challenger.Generate(); sample; derivekeypair; <projections>``
        per keypair, the other runs all its own keygens first and then all its
        challenger generates. The hop's post carries the cross-stage conjunct
        ``t_keys_k{2} = ev_derivekeypair (seed_T_k{1})``, so closing this lemma is
        what turns that coupling from ASSUMED into EC-checked.

        Recipe validated at real statement counts by
        ``ec_templates/keygenequiv_init_swap.ec``: align with ``swap`` (EC allows
        it -- the two abstract probabilistic calls write disjoint globs), then one
        ``seq`` per keypair on the UN-INLINED bodies with ``inline *`` INSIDE each
        bullet, so every inlined local keeps its bare source name.
        """
        mods: list[ec_ast.Module] = []
        for st in (step_a, step_b):
            if st.reduction is None:
                return None
            mod = next(
                (
                    d
                    for d in ec_reductions
                    if isinstance(d, ec_ast.Module) and d.name == st.reduction.name
                ),
                None,
            )
            if mod is None:
                return None
            mods.append(mod)
        if len(mods) != 2:
            return None

        def _init_exec(mod: ec_ast.Module) -> list[ec_ast.EcStmt] | None:
            proc = next((p for p in mod.procs if p.name == "initialize"), None)
            if proc is None:
                return None
            return [
                st
                for st in proc.body
                if not isinstance(st, (ec_ast.VarDecl, ec_ast.Return))
            ]

        execs = [_init_exec(m) for m in mods]
        if execs[0] is None or execs[1] is None:
            return None
        chal_of = [m.params[-1].name if m.params else None for m in mods]

        def _is_chal(st: ec_ast.EcStmt, chal: str | None) -> bool:
            return (
                isinstance(st, ec_ast.Call)
                and chal is not None
                and st.callee.partition(".")[0] == chal
            )

        # -- which side ALTERNATES and which side GROUPS ----------------------
        def _alt_segments(
            body: list[ec_ast.EcStmt], chal: str | None
        ) -> list[list[ec_ast.EcStmt]] | None:
            """``[chal-call, sample, det-call, assign*]`` repeated, else None."""
            cuts = [i for i, st in enumerate(body) if _is_chal(st, chal)]
            if not cuts or cuts[0] != 0:
                return None
            segs = [body[a:b] for a, b in zip(cuts, cuts[1:] + [len(body)])]
            for seg in segs:
                if len(seg) < 3 or not isinstance(seg[1], ec_ast.Sample):
                    return None
                if not isinstance(seg[2], ec_ast.Call) or _is_chal(seg[2], chal):
                    return None
                if any(not isinstance(x, ec_ast.Assign) for x in seg[3:]):
                    return None
            return segs

        def _alt_batched(
            body: list[ec_ast.EcStmt], chal: str | None
        ) -> tuple[list[list[ec_ast.EcStmt]], list[list[ec_ast.EcStmt]]] | None:
            """The BATCHED presentation of the same side (hop_12).

            ``[chal]*n ++ [sample]*n ++ n blocks of (det call, assign*)``. Same
            operation multiset as :func:`_alt_segments`, just grouped by KIND
            instead of by keypair, so it needs regrouping before each segment is
            the validated shape. Returns ``(segments, blocks)``; ``blocks`` is
            what the regrouping swap chain is computed from.
            """
            n = 0
            while n < len(body) and _is_chal(body[n], chal):
                n += 1
            if n < 1 or len(body) < 2 * n:
                return None
            samples = body[n : 2 * n]
            if any(not isinstance(st, ec_ast.Sample) for st in samples):
                return None
            rest = body[2 * n :]
            cuts = [i for i, st in enumerate(rest) if isinstance(st, ec_ast.Call)]
            if len(cuts) != n or not cuts or cuts[0] != 0:
                return None
            blocks = [rest[a:b] for a, b in zip(cuts, cuts[1:] + [len(rest)])]
            for blk in blocks:
                if _is_chal(blk[0], chal):
                    return None
                if any(not isinstance(x, ec_ast.Assign) for x in blk[1:]):
                    return None
            return [[body[k], samples[k], *blocks[k]] for k in range(n)], blocks

        def _grouped(body: list[ec_ast.EcStmt], chal: str | None) -> int | None:
            """``n`` non-challenger calls then ``n`` challenger calls, else None."""
            if not body or any(not isinstance(st, ec_ast.Call) for st in body):
                return None
            flags = [_is_chal(st, chal) for st in body]
            if len(body) % 2 or any(flags[: len(body) // 2]):
                return None
            if not all(flags[len(body) // 2 :]):
                return None
            return len(body) // 2

        alt_side: (
            tuple[int, list[list[ec_ast.EcStmt]], int, list[list[ec_ast.EcStmt]] | None]
            | None
        ) = None
        for idx in (0, 1):
            other = 1 - idx
            n_grp = _grouped(execs[other] or [], chal_of[other])
            if n_grp is None:
                continue
            segs = _alt_segments(execs[idx] or [], chal_of[idx])
            if segs is not None and n_grp == len(segs):
                alt_side = (idx, segs, n_grp, None)
                break
            batched = _alt_batched(execs[idx] or [], chal_of[idx])
            if batched is not None and n_grp == len(batched[0]):
                alt_side = (idx, batched[0], n_grp, batched[1])
                break
        if alt_side is None:
            return None
        ai, segs, n, alt_blocks = alt_side
        if n not in (1, 2):
            # Only n = 1 and n = 2 are tripwire-validated
            # (``ec_templates/keygenequiv_init_swap.ec`` carries both). Decline
            # rather than emit an untested interleaving for n > 2.
            return None
        am, bm = ("1", "2") if ai == 0 else ("2", "1")
        alt_expr = resolver.resolve(step_a if ai == 0 else step_b).module_expr
        a_base = pt.module_base_name(alt_expr)
        # -- the pieces the tactic names ---------------------------------------
        coupling = _query_delegate_pair_coupling(step_a, step_b)
        if coupling is None:
            return None
        conj = [c for c in coupling.split(" /\\ ") if not c.startswith("={")]
        if len(conj) != 2 * n:
            return None
        # The pair coupling emits shared fields in declaration order, then the
        # cross-stage ones in declaration order, so conjunct i belongs to keypair
        # ``i % n`` -- declaration order IS keypair order.
        by_kp: list[list[str]] = [[] for _ in range(n)]
        for i, c in enumerate(conj):
            by_kp[i % n].append(c)
        globs = " /\\ ".join(f"={{glob {m}}}" for m in declared_module_names)

        # side A's det call -> its ``_det`` axiom and ``ev_`` op
        alt_mod = mods[ai]
        alt_inner = (
            alt_expr[alt_expr.index("(") + 1 : alt_expr.rindex(")")]
            if "(" in alt_expr
            else ""
        )
        pmap_a = {
            p.name: pt.module_base_name(a)
            for p, a in zip(alt_mod.params, cc_split_args(alt_inner))
        }
        det_stmt = segs[0][2]
        assert isinstance(det_stmt, ec_ast.Call)
        det_mod_raw, _, det_meth = det_stmt.callee.partition(".")
        det_mod = pmap_a.get(det_mod_raw, det_mod_raw)
        det_alias = clone_alias_by_module.get(det_mod)
        if det_alias is None or det_meth not in det_methods_by_module.get(
            det_mod, set()
        ):
            return None

        # side B's challenger samples internally; its local keeps its bare source
        # name because ``inline *`` runs INSIDE each segment bullet.
        # pylint: disable=protected-access
        chal_ast = engine._get_game_ast(
            (step_b if ai == 0 else step_a).challenger, None
        )
        # pylint: enable=protected-access
        if chal_ast is None:
            return None
        chal_sample = next(
            (
                st.var.name
                for m in chal_ast.methods
                for st in m.block.statements
                if isinstance(st, frog_ast.Sample)
                and isinstance(st.var, frog_ast.Variable)
            ),
            None,
        )
        if chal_sample is None:
            return None

        a_base = pt.module_base_name(
            resolver.resolve(step_a if ai == 0 else step_b).module_expr
        )
        # pylint: disable=protected-access
        # At n = 1 the two interleavings are ALREADY aligned, so the alignment
        # swap has nothing to do -- and would be out of range on the grouped
        # side's two-statement body. Validated by ``keygenequiv_init_n1``.
        lines = ["proc."] + ([f"swap{{{bm}}} 2 1."] if n == 2 else [])
        if alt_blocks is not None:
            # The alternating side is BATCHED (hop_12): regroup it per keypair
            # first, with the same chain the split-seed route computes for the
            # identical layout. Validated by ``keygenequiv_init_batched``.
            lines += _regroup_swaps(n, alt_blocks, am)
        done: list[str] = []
        for k, seg in enumerate(segs):
            sample_stmt = seg[1]
            assert isinstance(sample_stmt, ec_ast.Sample)
            seed_ref = f"{a_base}.{mt._ec_field_name(sample_stmt.var)}{{{am}}}"
            ev = f"({det_alias}.ev_{det_meth} ({seed_ref}))"
            det_res = det_stmt.var if k == 0 else seg[2].var  # type: ignore[union-attr]
            carried = [f"{det_res}{{{am}}} = {ev}"]
            for proj in seg[3:]:
                assert isinstance(proj, ec_ast.Assign)
                carried.append(f"{proj.var}{{{am}}} = ({ev}{proj.rhs[len(det_res):]})")
            kp_conj = by_kp[k]
            inv = " /\\ ".join([globs] + done + kp_conj + carried)
            inv_kg = " /\\ ".join([globs] + done + [kp_conj[0]])
            inv_sm = inv_kg + f" /\\ {seed_ref} = {chal_sample}{{{bm}}}"
            a_cnt, b_cnt = (len(seg), 2) if am == "1" else (2, len(seg))
            lines += [
                f"seq {a_cnt} {b_cnt} : ({inv}).",
                "+ inline *.",
                f"seq {2 if am == '1' else 1} {1 if am == '1' else 2} : ({inv_kg}).",
                "- wp; call (_: true); skip => />.",
                f"seq 1 1 : ({inv_sm}).",
                "- rnd; skip => />.",
                f"exists* (glob {det_mod}){{{am}}}, {seed_ref}.",
                "elim* => gT sv.",
                "wp.",
                f"call{{{bm}}} ({det_mod}_{det_meth}_det gT sv).",
                f"call{{{am}}} ({det_mod}_{det_meth}_det gT sv).",
                "skip => />.",
            ]
            done += kp_conj + carried
        # pylint: enable=protected-access
        lines.append("skip => />.")
        return lines[1:]  # the caller prepends ``proc.``

    def _split_seed_shape(execs: list[list[Any]], chal_of: list[str | None]) -> (
        tuple[
            int,
            int,
            list[ec_ast.Sample],
            list[list[ec_ast.EcStmt]],
            list[list[ec_ast.EcStmt]],
            bool,
        ]
        | None
    ):
        """Classify a hop as GROUPED-seed side vs SPLIT-seed side.

        Returns
        ``(grouped_index, n, samples, grouped_blocks, split_blocks, batched)``,
        where ``batched`` says the grouped side runs all its challenger calls
        first (so it needs regrouping) rather than being per-keypair already.

        The grouped side runs ``n`` challenger calls, then ``n`` own samples,
        then ``n`` blocks of ``[det call, projection*]``. The split side runs
        ``n`` blocks of ``[challenger query, slice, slice, call, call]`` -- one
        full seed per keypair, cut into the two halves the other side sampled
        independently.
        """

        def _is_chal(st: ec_ast.EcStmt, chal: str | None) -> bool:
            return (
                isinstance(st, ec_ast.Call)
                and chal is not None
                and st.callee.partition(".")[0] == chal
            )

        def _grouped_interleaved(
            body: list[ec_ast.EcStmt], chal: str | None
        ) -> tuple[int, list[ec_ast.Sample], list[list[ec_ast.EcStmt]]] | None:
            """``[chal call, sample, <derivation>]`` repeated.

            The derivation is either ``[det call, projection*]`` (the CK shape,
            whose result the post states in ``ev_`` form) or a run of abstract
            calls (the CG shape, whose derivation chain also runs verbatim on
            the split side). Which one it is decides the segment closer; both
            are classified here.

            The hop_2 layout: the grouped side is ALREADY per-keypair, so there
            is nothing to regroup and the swap chain comes out empty. For n = 1
            this coincides with the batched layout, which is harmless -- both
            produce the same segments and no swaps.
            """
            cuts = [i for i, st in enumerate(body) if _is_chal(st, chal)]
            if not cuts or cuts[0] != 0:
                return None
            segs = [body[a:b] for a, b in zip(cuts, cuts[1:] + [len(body)])]
            samples: list[ec_ast.Sample] = []
            blocks: list[list[ec_ast.EcStmt]] = []
            for seg in segs:
                if len(seg) < 3 or not isinstance(seg[1], ec_ast.Sample):
                    return None
                if not isinstance(seg[2], ec_ast.Call) or _is_chal(seg[2], chal):
                    return None
                tail = seg[3:]
                proj_tail = all(isinstance(x, ec_ast.Assign) for x in tail)
                call_tail = all(
                    isinstance(x, ec_ast.Call) and not _is_chal(x, chal) for x in tail
                )
                if not proj_tail and not call_tail:
                    return None
                samples.append(seg[1])
                blocks.append(seg[2:])
            return len(segs), samples, blocks

        def _grouped(
            body: list[ec_ast.EcStmt], chal: str | None
        ) -> tuple[int, list[ec_ast.Sample], list[list[ec_ast.EcStmt]]] | None:
            n = 0
            while n < len(body) and _is_chal(body[n], chal):
                n += 1
            if n < 1 or len(body) < 2 * n:
                return None
            samples = body[n : 2 * n]
            if any(not isinstance(st, ec_ast.Sample) for st in samples):
                return None
            rest = body[2 * n :]
            cuts = [i for i, st in enumerate(rest) if isinstance(st, ec_ast.Call)]
            if len(cuts) != n or not cuts or cuts[0] != 0:
                return None
            blocks = [rest[a:b] for a, b in zip(cuts, cuts[1:] + [len(rest)])]
            for blk in blocks:
                if _is_chal(blk[0], chal):
                    return None
                if any(not isinstance(x, ec_ast.Assign) for x in blk[1:]):
                    return None
            return n, [cast(ec_ast.Sample, s) for s in samples], blocks

        def _split(
            body: list[ec_ast.EcStmt], chal: str | None
        ) -> list[list[ec_ast.EcStmt]] | None:
            cuts = [i for i, st in enumerate(body) if _is_chal(st, chal)]
            if not cuts or cuts[0] != 0:
                return None
            blocks = [body[a:b] for a, b in zip(cuts, cuts[1:] + [len(body)])]
            for blk in blocks:
                if len(blk) < 5:
                    return None
                if not isinstance(blk[1], ec_ast.Assign) or not isinstance(
                    blk[2], ec_ast.Assign
                ):
                    return None
                if any(
                    not isinstance(x, ec_ast.Call) or _is_chal(x, chal) for x in blk[3:]
                ):
                    return None
            return blocks

        for gi in (0, 1):
            spl = _split(execs[1 - gi], chal_of[1 - gi])
            if spl is None:
                continue
            grp = _grouped(execs[gi], chal_of[gi])
            if grp is not None and len(spl) == grp[0]:
                return gi, grp[0], grp[1], grp[2], spl, True
            grp = _grouped_interleaved(execs[gi], chal_of[gi])
            if grp is not None and len(spl) == grp[0]:
                return gi, grp[0], grp[1], grp[2], spl, False
        return None

    def _regroup_swaps(
        n: int, blocks: list[list[ec_ast.EcStmt]], mem: str
    ) -> list[str]:
        """``swap`` sequence regrouping the grouped side per keypair.

        The body is ``[chal]*n ++ [sample]*n ++ block_0 ++ ... ++ block_{n-1}``
        and the target is ``[chal_k, sample_k, *block_k]`` for each ``k``. Each
        emitted move lifts keypair ``k``'s material past keypair ``j>k``'s,
        which is independent of it, so every move is one EC accepts. Indices are
        exact because this is the UN-INLINED body the exporter rendered itself.
        """
        target: list[int] = []
        off = 2 * n
        starts: list[int] = []
        for blk in blocks:
            starts.append(off)
            off += len(blk)
        for k in range(n):
            target.append(k + 1)
            target.append(n + k + 1)
            target.extend(starts[k] + j + 1 for j in range(len(blocks[k])))
        return _bubble_swaps(target, off, mem)

    def _bubble_swaps(target: list[int], total: int, mem: str) -> list[str]:
        """``swap{mem}`` sequence realising ``target`` as a statement order.

        ``target`` lists the 1-based ORIGINAL positions in the order they should
        end up. Each emitted move lifts one statement earlier past statements
        not yet placed, so a caller that only reorders mutually independent
        material gets moves EC accepts.
        """
        cur = list(range(1, total + 1))
        out: list[str] = []
        for tgt, orig in enumerate(target, start=1):
            pos = cur.index(orig) + 1
            if pos != tgt:
                out.append(f"swap{{{mem}}} {pos} -{pos - tgt}.")
                cur.insert(tgt - 1, cur.pop(pos - 1))
        return out

    def _split_seed_init_tac(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> list[str] | None:
        """Whole-init tactic for a SPLIT-SEED hop (the CFRG HON_BIND hop_14
        ``initialize``), or ``None`` off-shape.

        The two reductions do not merely interleave differently -- they have
        different RANDOMNESS STRUCTURE. One draws each keypair's two seeds
        INDEPENDENTLY (the pq seed inside its ``KeyGenEquiv`` challenger's
        ``generate``, the t seed itself); the other draws ONE full seed per
        keypair from a PRG query challenger and SLICES it into the two halves.
        Coupling them is exactly the split-uniform law
        ``d_full = dlet d_pq (fun a => dmap d_t (fun b => concat a b))``.

        That law is not emitted for a type the source only ever slices, so this
        route ASKS for it via :meth:`TypeCollector.request_virtual_concat`. A
        request is not an assertion: both soundness gates still run at emission
        time (prefix/suffix order read from the recorded slice OFFSETS, and a
        symbolic length-sum check that FAILS CLOSED), and decline silently if
        they do not hold. Any proof whose admits fall because of this is
        CLEAN-PENDING-AXIOM-REVIEW, never clean -- see PROVISIONAL-AXIOMS.

        Recipe validated at the real statement counts, with the real
        offset-carrying slice ops, by
        ``ec_templates/prg_vs_keygen_init_segmented.ec``: regroup the grouped
        side per keypair on the UN-INLINED body, one ``seq`` per keypair with
        ``inline *`` INSIDE the bullet (so no inline collision suffix is ever
        predicted), then per keypair couple the samples, peel the pq
        derivekeypair two-sided, and peel the t derivekeypair ONE-SIDED with its
        ``_det`` axiom so the post learns the VALUE.
        """
        mods: list[ec_ast.Module] = []
        for st in (step_a, step_b):
            if st.reduction is None:
                return None
            mod = next(
                (
                    d
                    for d in ec_reductions
                    if isinstance(d, ec_ast.Module) and d.name == st.reduction.name
                ),
                None,
            )
            if mod is None:
                return None
            mods.append(mod)

        def _init_proc(mod: ec_ast.Module) -> ec_ast.Proc | None:
            return next((p for p in mod.procs if p.name == "initialize"), None)

        procs = [_init_proc(m) for m in mods]
        if procs[0] is None or procs[1] is None:
            return None
        execs = [
            [st for st in p.body if not isinstance(st, (ec_ast.VarDecl, ec_ast.Return))]
            for p in procs
            if p is not None
        ]
        chal_of = [m.params[-1].name if m.params else None for m in mods]
        shape = _split_seed_shape(execs, chal_of)
        if shape is None:
            return None
        gi, n, samples, blocks_g, blocks_s, batched = shape

        # COMMON-TAIL variant: the grouped side's whole derivation chain runs
        # verbatim on the split side too, right after that side's own pq call.
        # Then nothing needs functionalizing -- once the seeds are coupled the
        # chain couples TWO-SIDED with `call (_: true)`. Validated by
        # ``ec_templates/prg_vs_keygen_init_common_tail.ec``. Restricted to the
        # already-per-keypair layout: the batched+common-tail combination has no
        # tripwire, so it declines rather than emitting an unvalidated chain.
        def _callee(st: ec_ast.EcStmt) -> str | None:
            return st.callee if isinstance(st, ec_ast.Call) else None

        common_tail = not batched and all(
            len(bs) == 4 + len(bg)
            and all(_callee(x) is not None for x in bg)
            and [_callee(x) for x in bg] == [_callee(x) for x in bs[4:]]
            for bg, bs in zip(blocks_g, blocks_s)
        )
        if n not in (1, 2):
            # Only n = 1 (the CT_SAMEKEY cells) and n = 2 (every other CFRG
            # cell) are VALIDATED by the tripwire. The regrouping swap chain is
            # derived generally, but "it should generalize" is not validation --
            # decline rather than emit an untested chain.
            return None
        # The whole body below is written with the GROUPED side as {1}, which is
        # the only orientation the bijection and closer are validated for. When
        # the hop presents them the other way round (hop_2), `symmetry` swaps the
        # sides AND the memory tags in pre/post, so the identical body applies
        # underneath -- no mirrored bijection, no mirrored closer. It must come
        # AFTER `proc.`, which the chain emitter hardcodes ahead of this body.
        mirrored = gi != 0
        gm, sm = "1", "2"
        g_step, s_step = (step_b, step_a) if mirrored else (step_a, step_b)
        g_base = pt.module_base_name(resolver.resolve(g_step).module_expr)

        # -- both challengers must have the shape whose INLINED LENGTH the
        #    per-segment indices below assume ------------------------------
        # pylint: disable=protected-access
        g_chal = engine._get_game_ast(g_step.challenger, None)
        s_chal = engine._get_game_ast(s_step.challenger, None)
        # pylint: enable=protected-access
        if g_chal is None or s_chal is None:
            return None

        def _chal_method(
            chal: frog_ast.Game, call: ec_ast.EcStmt
        ) -> list[frog_ast.Statement] | None:
            if not isinstance(call, ec_ast.Call):
                return None
            meth = call.callee.partition(".")[2]
            m = next(
                (x for x in chal.methods if x.signature.name.lower() == meth.lower()),
                None,
            )
            return list(m.block.statements) if m is not None else None

        g_stmts = _chal_method(g_chal, execs[gi][0])
        s_stmts = _chal_method(s_chal, blocks_s[0][0])
        if g_stmts is None or s_stmts is None:
            return None
        # grouped challenger: `sample; return <one call on it>` -> EC renders
        # [Sample, Call, Return], so an inlined copy is THREE statements and the
        # keypair's own seed sample lands at index 4.
        if (
            len(g_stmts) != 2
            or not isinstance(g_stmts[0], frog_ast.Sample)
            or not isinstance(g_stmts[0].var, frog_ast.Variable)
            or not isinstance(g_stmts[1], frog_ast.ReturnStatement)
        ):
            return None
        g_call = g_stmts[1].expression
        if (
            not isinstance(g_call, frog_ast.FuncCall)
            or len(g_call.args) != 1
            or not isinstance(g_call.args[0], frog_ast.Variable)
            or g_call.args[0].name != g_stmts[0].var.name
        ):
            return None
        chal_sample = g_stmts[0].var.name
        # split challenger: `sample; return it` -> EC renders [Sample, Return],
        # so an inlined copy is TWO statements and the segment's split side has
        # sample + result-assign + the two slice assigns = 4 before its calls.
        if (
            len(s_stmts) != 2
            or not isinstance(s_stmts[0], frog_ast.Sample)
            or not isinstance(s_stmts[0].var, frog_ast.Variable)
            or not isinstance(s_stmts[1], frog_ast.ReturnStatement)
            or not isinstance(s_stmts[1].expression, frog_ast.Variable)
            or s_stmts[1].expression.name != s_stmts[0].var.name
        ):
            return None

        # -- the deterministic (t) derivekeypair and its ev/det names ---------
        det_stmt = blocks_g[0][0]
        if not isinstance(det_stmt, ec_ast.Call):
            return None
        det_mod_raw, _, det_meth = det_stmt.callee.partition(".")
        g_expr = resolver.resolve(g_step).module_expr
        g_inner = (
            g_expr[g_expr.index("(") + 1 : g_expr.rindex(")")] if "(" in g_expr else ""
        )
        pmap = {
            p.name: pt.module_base_name(a)
            for p, a in zip(mods[gi].params, cc_split_args(g_inner))
        }
        det_mod = pmap.get(det_mod_raw, det_mod_raw)
        det_alias = clone_alias_by_module.get(det_mod)
        if not common_tail and (
            det_alias is None
            or det_meth not in det_methods_by_module.get(det_mod, set())
        ):
            # The common-tail closer never functionalizes, so it needs neither
            # the ``ev_`` alias nor a determinism licence for the chain.
            return None
        # The regrouping swaps move this call past the OTHER keypair's
        # challenger call; that is only independent if the challenger drives a
        # different module. Decline instead of emitting a swap EC rejects.
        if not common_tail and pt.module_base_name(
            pt.last_module_arg(pt.last_module_arg(g_expr))
        ) == (det_mod):
            return None

        # -- the split side's per-keypair slice locals, by ROLE ---------------
        s_proc = procs[1 - gi]
        if s_proc is None:
            return None
        s_decl = {d.name: d.type for d in s_proc.body if isinstance(d, ec_ast.VarDecl)}
        s_expr = resolver.resolve(s_step).module_expr
        s_inner = (
            s_expr[s_expr.index("(") + 1 : s_expr.rindex(")")] if "(" in s_expr else ""
        )
        s_pmap = {
            p.name: pt.module_base_name(a)
            for p, a in zip(mods[1 - gi].params, cc_split_args(s_inner))
        }
        pq_local: list[str] = []
        t_local: list[str] = []
        full_ty: set[str] = set()
        left_ty: set[str] = set()
        right_ty: set[str] = set()
        for blk in blocks_s:
            chal_call, asn_a, asn_b = blk[0], blk[1], blk[2]
            if (
                not isinstance(chal_call, ec_ast.Call)
                or not isinstance(asn_a, ec_ast.Assign)
                or not isinstance(asn_b, ec_ast.Assign)
                or any(not isinstance(x, ec_ast.Call) for x in blk[3:])
            ):
                return None
            by_var = {asn_a.var: asn_a, asn_b.var: asn_b}
            if common_tail:
                # The pq call is the one the tail does NOT contain: it is the
                # single statement between the slices and the shared chain.
                pq_call = cast(ec_ast.Call, blk[3])
                if pq_call.args not in by_var:
                    return None
                t_args = [v for v in by_var if v != pq_call.args]
                if len(t_args) != 1:
                    return None
                t_arg = t_args[0]
            else:
                call_x, call_y = cast(ec_ast.Call, blk[3]), cast(ec_ast.Call, blk[4])
                if len(blk) != 5:
                    return None
                t_calls = [
                    c
                    for c in (call_x, call_y)
                    if s_pmap.get(
                        c.callee.partition(".")[0], c.callee.partition(".")[0]
                    )
                    == det_mod
                ]
                if len(t_calls) != 1:
                    return None
                t_call = t_calls[0]
                pq_call = call_y if t_call is call_x else call_x
                if t_call.args not in by_var or pq_call.args not in by_var:
                    return None
                t_arg = t_call.args
            # The emitted split axiom orders the halves by their recorded
            # OFFSETS: the prefix is the slice starting at 0. The `rndsem` fold
            # produces `dlet d_<first sampled> (dmap d_<second> ...)`, and the
            # grouped side samples its challenger's pq seed FIRST -- so the pq
            # half must be the PREFIX or the two forms will not match.
            if by_var[pq_call.args].rhs.split()[2:3] != ["0"]:
                return None
            pq_local.append(pq_call.args)
            t_local.append(t_arg)
            full_ty.add(s_decl[chal_call.var].text if chal_call.var in s_decl else "")
            left_ty.add(s_decl[pq_call.args].text if pq_call.args in s_decl else "")
            right_ty.add(s_decl[t_arg].text if t_arg in s_decl else "")
        if len(full_ty) != 1 or len(left_ty) != 1 or len(right_ty) != 1:
            return None
        src_name, left_name, right_name = (
            full_ty.pop(),
            left_ty.pop(),
            right_ty.pop(),
        )
        if not src_name or not left_name or not right_name:
            return None
        len_l = top_types.bs_length_for(left_name)
        len_r = top_types.bs_length_for(right_name)
        if len_l is None or len_r is None:
            return None

        # -- the hop's post, partitioned per keypair --------------------------
        coupling = _live_state_coupling(step_a, step_b)
        globs = " /\\ ".join(
            c for c in coupling.split(" /\\ ") if c.startswith("={glob ")
        )
        conj = [c for c in coupling.split(" /\\ ") if not c.startswith("={")]
        if not globs:
            return None
        if common_tail:
            # Nothing is functionalized, so an ``ev_`` conjunct would be
            # unprovable by the two-sided peel -- decline rather than emit it.
            if len(conj) < n or len(conj) % n != 0 or any("ev_" in c for c in conj):
                return None
        elif len(conj) != 2 * n:
            return None
        if mirrored:
            # The coupling is stated with step_a as {1}; under `symmetry` the
            # grouped side becomes {1}, so every conjunct's memory tags flip.
            conj = [
                c.replace("{1}", "\x00").replace("{2}", "{1}").replace("\x00", "{2}")
                for c in conj
            ]
        by_kp: list[list[str]] = [[] for _ in range(n)]
        for i, c in enumerate(conj):
            by_kp[i % n].append(c)
        if not common_tail:
            # conjunct order is <shared fields> then <cross-stage ev-forms>, so
            # each keypair's pair is (shared, ev). Check that, don't assume it.
            if any("ev_" in kp[0] or "ev_" not in kp[1] for kp in by_kp):
                return None
        # The common-tail closer establishes the pq coupling on its own before
        # the chain peel, so it must know WHICH conjunct that is -- located by
        # the grouped side's own challenger-call result var, never by name.
        g_chal_vars = [
            st.var
            for st in execs[gi]
            if isinstance(st, ec_ast.Call)
            and st.callee.partition(".")[0] == chal_of[gi]
        ]
        pq_conj: list[str] = []
        if common_tail:
            if len(g_chal_vars) != n:
                return None
            for k in range(n):
                hits = [c for c in by_kp[k] if f".{g_chal_vars[k]}{{" in c]
                if len(hits) != 1:
                    return None
                pq_conj.append(hits[0])

        # Demand-driven: only now, with the whole shape confirmed, ask for the
        # split/round-trip laws over the full seed type.
        top_types.request_virtual_concat(src_name)

        # pylint: disable=protected-access
        concat_op = tc._concat_op_name(left_name, right_name, src_name)
        slice_l = tc._slice_op_name(src_name, left_name)
        slice_r = tc._slice_op_name(src_name, right_name)
        len_l_p = tc._paren_int(len_l)
        # pylint: enable=protected-access
        len_sum = f"({len_l} + {len_r})"
        ax_left = f"slice_concat_left_{left_name}_{right_name}_{src_name}"
        ax_right = f"slice_concat_right_{left_name}_{right_name}_{src_name}"
        ax_id = f"concat_slices_id_{left_name}_{right_name}_{src_name}"
        ax_dlet = f"d{src_name}_split_dlet_{left_name}_{right_name}"
        ax_hint = f"{ax_left} {ax_right} {ax_id}"

        def _couple_lines(inv: str) -> list[str]:
            """The split-uniform coupling, verbatim from the tripwire."""
            return [
                f"seq {2 if gm == '1' else 4} {4 if gm == '1' else 2} : ({inv}).",
                "- wp.",
                f"rndsem*{{{gm}}} 0.",
                f"rnd (fun (p : {left_name} * {right_name}) =>"
                f" {concat_op} p.`1 p.`2)",
                f"    (fun (sf : {src_name}) => ({slice_l} sf 0 {len_l_p},"
                f" {slice_r} sf {len_l_p} {len_sum})).",
                "skip => />.",
                f"rewrite {ax_dlet}.",
                "split.",
                f"* move => sf hsf; rewrite {ax_id} //.",
                "move => _; split.",
                "* move => sf hsf.",
                "  rewrite !dlet1E; congr; apply fun_ext => a /=.",
                "  rewrite !dmap1E /(\\o) /pred1 /=.",
                "  congr; apply mu_eq => b /=.",
                f"  by rewrite eqboolP; smt({ax_hint}).",
                "move => _ p hp.",
                f"have h1 : p.`1 \\in d{left_name} by smt(supp_dlet supp_dmap).",
                f"have h2 : p.`2 \\in d{right_name} by smt(supp_dlet supp_dmap).",
                "split.",
                # Two shapes, one emission. Over ABSTRACT bitstrings the first
                # `rnd` obligation is the support side condition, discharged by
                # the explicit dlet/dmap witnesses. Over BITWORD-backed ones the
                # distribution is `DWord.dunifin` and EC has already discharged
                # support by the time we get here, leaving the round-trip
                # equality -- where the witness `rewrite` is "nothing to
                # rewrite". `||` takes whichever applies; both are validated
                # (`ec_templates/split_uniform_couple.ec` and
                # `ec_templates/bitword_split_couple.ec`).
                "* by (rewrite supp_dlet; exists p.`1; rewrite h1 /=;",
                "      rewrite supp_dmap; exists p.`2; rewrite h2)",
                f"     || smt({ax_left} {ax_right}).",
                f"move => _; smt({ax_left} {ax_right}).",
            ]

        # pylint: disable=protected-access
        lines: list[str] = ["symmetry."] if mirrored else []
        if batched:
            lines += _regroup_swaps(n, blocks_g, gm)
        g_proc = procs[gi]
        if g_proc is None:
            return None
        g_locals = {d.name for d in g_proc.body if isinstance(d, ec_ast.VarDecl)}
        done: list[str] = []
        for k in range(n):
            # The grouped side's t seed is a module field on the CK shape (the
            # post names it) and a proc local on the common-tail shape; read
            # which from the rendered proc rather than assuming either.
            seed_ref = (
                f"{samples[k].var}{{{gm}}}"
                if samples[k].var in g_locals
                else f"{g_base}.{mt._ec_field_name(samples[k].var)}{{{gm}}}"
            )
            kp = by_kp[k]
            carried: list[str] = []
            if not common_tail:
                ev = f"({det_alias}.ev_{det_meth} ({seed_ref}))"
                det_res = cast(ec_ast.Call, blocks_g[k][0]).var
                carried = [f"{det_res}{{{gm}}} = {ev}"]
                for proj in blocks_g[k][1:]:
                    assert isinstance(proj, ec_ast.Assign)
                    carried.append(
                        f"{proj.var}{{{gm}}} = ({ev}{proj.rhs[len(det_res):]})"
                    )
            inv_seg = " /\\ ".join([globs] + done + kp + carried)
            inv_smp = " /\\ ".join(
                [globs]
                + done
                + [
                    f"{chal_sample}{{{gm}}} = {pq_local[k]}{{{sm}}}",
                    f"{seed_ref} = {t_local[k]}{{{sm}}}",
                ]
            )
            inv_pq = " /\\ ".join(
                [globs]
                + done
                + [
                    f"{seed_ref} = {t_local[k]}{{{sm}}}",
                    pq_conj[k] if common_tail else kp[0],
                ]
            )
            g_cnt = 2 + len(blocks_g[k])
            if common_tail:
                # after the pq peel both sides hold the SAME chain -- couple it
                # back-to-front, two-sided, with no determinism hypothesis
                closer = ["wp; call (_: true)." for _ in blocks_g[k]] + ["skip => />."]
            else:
                closer = [
                    f"exists* (glob {det_mod}){{{gm}}}, {seed_ref}.",
                    "elim* => gT sv.",
                    "wp.",
                    f"call{{{sm}}} ({det_mod}_{det_meth}_det gT sv).",
                    f"call{{{gm}}} ({det_mod}_{det_meth}_det gT sv).",
                    "skip => />.",
                ]
            lines += [
                f"seq {g_cnt} {len(blocks_s[k])} : ({inv_seg}).",
                "+ inline *.",
                # one `generate` inlined here (3 statements), so the keypair's
                # own seed sample is at 4 and one swap makes the pair adjacent.
                f"swap{{{gm}}} 4 -2.",
                *_couple_lines(inv_smp),
                f"seq 2 1 : ({inv_pq}).",
                "- wp; call (_: true); skip => />.",
                *closer,
            ]
            done += kp + carried
        # pylint: enable=protected-access
        lines.append("skip => />.")
        return lines

    def _batched_align_init_tac(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> list[str] | None:
        """Whole-init tactic for two reductions that build the same keypairs
        with the same BACKBONE but a different LAYOUT, or ``None`` off-shape.

        The CFRG HON_BIND hop_4 / hop_8 ``initialize`` shape. Each side runs, per
        keypair, one pq-key source and then a ``<$`` seed plus an identical run
        of abstract calls; what differs is only whether the n pq sources are
        BATCHED up front or INTERLEAVED with the per-keypair blocks. The pq
        source may itself be a challenger call -- a ``KeyGenEquiv`` whose
        ``Generate`` is a bare ``return K.KeyGen();`` (one backbone call), or a
        binding challenger whose ``Initialize`` runs all n keygens itself (n
        backbone calls) -- so after ``inline *`` both sides run exactly the same
        abstract-call/sample sequence.

        Hence no coupling law and no determinism hypothesis: batch the
        interleaved side with one ``swap`` per keypair on the UN-INLINED body,
        ``inline *``, then peel the common backbone back-to-front. There is no
        ``seq`` and no invariant, so no inlined local is ever named and EC's
        collision suffixes are irrelevant.

        The route fires ONLY when a side is actually interleaved: when both are
        already batched the generic init peel handles the hop, and preempting it
        would churn a working export. Validated at the real statement counts by
        ``ec_templates/regrouped_common_init.ec`` (both the plain and the
        binding-challenger variants, n = 2 and n = 1).
        """
        mods: list[ec_ast.Module] = []
        for st in (step_a, step_b):
            if st.reduction is None:
                return None
            mod = next(
                (
                    d
                    for d in ec_reductions
                    if isinstance(d, ec_ast.Module) and d.name == st.reduction.name
                ),
                None,
            )
            if mod is None:
                return None
            mods.append(mod)
        execs: list[list[ec_ast.EcStmt]] = []
        for m in mods:
            proc = next((p for p in m.procs if p.name == "initialize"), None)
            if proc is None:
                return None
            execs.append(
                [
                    st
                    for st in proc.body
                    if not isinstance(st, (ec_ast.VarDecl, ec_ast.Return))
                ]
            )
        chal_of = [m.params[-1].name if m.params else None for m in mods]

        def _parse(
            body: list[ec_ast.EcStmt],
        ) -> tuple[int, list[ec_ast.EcStmt], int, bool] | None:
            """``(n, pq_part, tail_len, interleaved)`` for one side.

            Cut at the ``<$`` samples: what precedes the first one is the pq
            material, and each sample opens a block. A BATCHED side's blocks all
            have the same length; an INTERLEAVED side's non-final blocks carry
            exactly one extra trailing statement -- the next keypair's pq call.
            """
            sample_ix = [
                i for i, st in enumerate(body) if isinstance(st, ec_ast.Sample)
            ]
            if not sample_ix:
                return None
            n_kp = len(sample_ix)
            pre = body[: sample_ix[0]]
            rests = [
                body[a + 1 : b] for a, b in zip(sample_ix, sample_ix[1:] + [len(body)])
            ]
            t_len = len(rests[-1])
            if t_len < 1:
                return None
            if all(len(r) == t_len for r in rests):
                pq_part, interleaved = pre, False
            elif (
                n_kp > 1
                and all(len(r) == t_len + 1 for r in rests[:-1])
                and all(isinstance(r[-1], ec_ast.Call) for r in rests[:-1])
                and len(pre) == 1
                and isinstance(pre[0], ec_ast.Call)
            ):
                pq_part = [pre[0]] + [r[-1] for r in rests[:-1]]
                interleaved = True
            else:
                return None
            if any(
                not isinstance(x, ec_ast.Call) for r in rests for x in r[:t_len]
            ) or any(not isinstance(x, (ec_ast.Call, ec_ast.Assign)) for x in pq_part):
                return None
            return n_kp, pq_part, t_len, interleaved

        parsed = [_parse(e) for e in execs]
        if parsed[0] is None or parsed[1] is None:
            return None
        n, _, tail_len, _ = parsed[0]
        if parsed[1][0] != n or parsed[1][2] != tail_len:
            return None
        if n not in (1, 2):
            # only n = 1 and n = 2 are tripwire-validated; the swap chain is
            # derived generally but "it should generalize" is not validation
            return None
        if not parsed[0][3] and not parsed[1][3]:
            # both already batched -- the generic init peel owns this hop
            return None
        # the two per-keypair chains must be the same calls in the same order
        for k in range(n):
            a_tail = _tail_of(execs[0], parsed[0], k)
            b_tail = _tail_of(execs[1], parsed[1], k)
            if [c.callee for c in a_tail] != [c.callee for c in b_tail]:
                return None

        # -- both sides must contribute the SAME number of pq backbone calls --
        def _pq_backbone(side: int) -> int | None:
            total = 0
            for st in cast(list[ec_ast.EcStmt], parsed[side][1]):  # type: ignore[index]
                if isinstance(st, ec_ast.Assign):
                    continue
                assert isinstance(st, ec_ast.Call)
                mod_name, _, meth = st.callee.partition(".")
                if mod_name != chal_of[side]:
                    total += 1
                    continue
                # pylint: disable=protected-access
                chal = engine._get_game_ast(
                    (step_a if side == 0 else step_b).challenger, None
                )
                # pylint: enable=protected-access
                if chal is None:
                    return None
                cnt = mt.method_module_call_count(chal, meth)
                if cnt < 1:
                    return None
                total += cnt
            return total

        if _pq_backbone(0) != n or _pq_backbone(1) != n:
            return None
        # An ``ev_`` conjunct needs a functionalizing closer; this peel proves
        # only ``={res}`` per call, so decline rather than emit a tactic that
        # runs without closing.
        coupling = _live_state_coupling(step_a, step_b)
        if "ev_" in coupling:
            return None

        lines: list[str] = []
        for side in (0, 1):
            if not parsed[side][3]:  # type: ignore[index]
                continue
            seg = tail_len + 2
            target = [k * seg + 1 for k in range(n)] + [
                k * seg + 2 + j for k in range(n) for j in range(seg - 1)
            ]
            lines += _bubble_swaps(target, n * seg, str(side + 1))
        lines.append("inline *.")
        for _ in range(n):
            lines += ["wp; call (_: true)."] * tail_len
            lines.append("rnd.")
        lines += ["wp; call (_: true)."] * n
        lines.append("skip => />.")
        return lines

    def _tail_of(
        body: list[ec_ast.EcStmt],
        parsed: tuple[int, list[ec_ast.EcStmt], int, bool],
        k: int,
    ) -> list[ec_ast.Call]:
        """Keypair ``k``'s chain of abstract calls, from a ``_parse`` result."""
        _, _, t_len, _ = parsed
        sample_ix = [i for i, st in enumerate(body) if isinstance(st, ec_ast.Sample)]
        start = sample_ix[k] + 1
        return [cast(ec_ast.Call, st) for st in body[start : start + t_len]]

    def _prg_query_init_tac(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> list[str] | None:
        """The COMPLETE init tactic for a PRG QUERY-delegate hop (the HON_BIND
        ``game ~ R_PRG`` hop_0/hop_12 ``initialize``), or ``None`` off-shape.

        The generic init backbone peel proves ``={res}`` with ``call (_: true)``
        per abstract call, which learns NOTHING about what those calls returned
        -- so the derivation-chain postcondition
        :func:`_prg_query_game_coupling` emits (each reduction field = the
        ``ev_`` form over the game's seed) is unprovable and the closing
        ``skip => /#`` fails.

        Both sides run the SAME shape: ONE leading sample, then a linear tail of
        deterministic abstract calls. So: split the sample off with ``seq 1 1``
        and couple it with ``rnd``; freeze the post-sample memory (each callee's
        glob + the coupled seed) with ``exists*``; then peel BOTH tails
        ONE-SIDED back-to-front with the ``<M>_<m>_det`` phoare axioms, each
        applied to its arguments' ``ev_`` values over the frozen seed. After the
        ``seq`` nothing is coupled two-sidedly, so the two sides' call
        interleaving is irrelevant. Validated on both toolchains by
        ``ec_templates/hon_prg_init_derivation.ec`` and, on the real goal, by a
        hand-spliced ``CG_seedbased_HON_BIND_K_CT_SAMEKEY`` compile.

        The ``seq`` invariant names the two EC-inlined sample locals. EC's
        ``inline`` keeps the target proc's own locals and suffixes each COLLIDING
        inlined local with the smallest fresh integer, in inline order; both
        seeds here are first-and-only occurrences of their source names, so each
        is its bare source name (the game's from the scheme ``KeyGen``'s sampled
        var, the reduction's from the challenger ``Query``'s). A collision on
        either name declines rather than guessing.
        """
        if step_a.reduction is None and step_b.reduction is not None:
            game_step, red_step, gs, rs = step_a, step_b, "1", "2"
        elif step_b.reduction is None and step_a.reduction is not None:
            game_step, red_step, gs, rs = step_b, step_a, "2", "1"
        else:
            return None
        # Shape gate: reuse the coupling builder -- it fires exactly on this hop
        # class, and its ``ev_`` conjuncts are what the tactic has to prove.
        coupling = _prg_query_game_coupling(step_a, step_b)
        if coupling is None or "ev_" not in coupling:
            return None
        # -- the coupling, partitioned per keypair ----------------------------
        # Each `seq`'s invariant is the PREFIX of the final post covering the
        # keypairs established so far. A conjunct belongs to keypair k iff it
        # mentions the k-th game seed ref -- true of both the reduction's stored
        # fields and the game's own derived public half, since every one of them
        # is stated as an ev-form over that seed.
        seed_holder_name = pt.module_base_name(resolver.resolve(game_step).module_expr)
        # pylint: disable=protected-access
        game_ast_for_seeds = engine._get_game_ast(game_step.challenger, None)
        # pylint: enable=protected-access
        if game_ast_for_seeds is None:
            return None
        # pylint: disable=protected-access
        seed_refs_init = [
            f"{seed_holder_name}.{mt._ec_field_name(f.name)}{{{gs}}}"
            for f in game_ast_for_seeds.fields
            if isinstance(
                (
                    top_types.resolve(f.type)
                    if not isinstance(f.type, frog_ast.BitStringType)
                    else f.type
                ),
                frog_ast.BitStringType,
            )
        ]
        # pylint: enable=protected-access
        coupling_groups: list[list[str]] = [[] for _ in seed_refs_init]
        for conj_part in coupling.split(" /\\ "):
            if conj_part.startswith("={"):
                continue
            owners = [k for k, r in enumerate(seed_refs_init) if r in conj_part]
            if len(owners) != 1:
                return None  # a conjunct spanning keypairs has no segment
            coupling_groups[owners[0]].append(conj_part)
        if not seed_refs_init or any(not g for g in coupling_groups):
            return None
        assert red_step.reduction is not None
        rname = red_step.reduction.name
        red_mod = next(
            (
                d
                for d in ec_reductions
                if isinstance(d, ec_ast.Module) and d.name == rname
            ),
            None,
        )
        red_init = (
            next((pr for pr in red_mod.procs if pr.name == "initialize"), None)
            if red_mod is not None
            else None
        )
        dkp_proc = (
            next((pr for pr in ec_scheme.procs if pr.name == "derivekeypair"), None)
            if ec_scheme is not None
            else None
        )
        kg_proc = (
            next((pr for pr in ec_scheme.procs if pr.name == "keygen"), None)
            if ec_scheme is not None
            else None
        )
        if red_mod is None or red_init is None or dkp_proc is None or kg_proc is None:
            return None
        if len(dkp_proc.params) != 1:
            return None
        # -- the two EC-inlined sample names ---------------------------------
        game_seed = next(
            (s.var for s in kg_proc.body if isinstance(s, ec_ast.Sample)), None
        )
        # pylint: disable=protected-access
        chal_ast = engine._get_game_ast(red_step.challenger, None)
        # pylint: enable=protected-access
        if game_seed is None or chal_ast is None:
            return None
        red_seeds = [
            st.var.name
            for m in chal_ast.methods
            for st in m.block.statements
            if isinstance(st, frog_ast.Sample) and isinstance(st.var, frog_ast.Variable)
        ]
        if len(red_seeds) != 1:
            return None
        red_seed = red_seeds[0]
        # EC suffixes an inlined local only when its name COLLIDES with one
        # already in scope; a formal PARAMETER is substituted, not renamed (the
        # game seed keeps its bare name even though ``derivekeypair``'s own
        # parameter shares it -- confirmed on the real goal). So the collision
        # test is against the DECLARED locals inlined alongside each seed;
        # decline rather than predict a suffix when one clashes.
        if any(
            isinstance(d, ec_ast.VarDecl) and d.name == game_seed for d in dkp_proc.body
        ) or any(
            isinstance(d, ec_ast.VarDecl) and d.name == red_seed for d in red_init.body
        ):
            return None
        # -- the PRG the challenger's query delegates to ----------------------
        chal_expr = pt.last_module_arg(resolver.resolve(red_step).module_expr)
        prg_mod = pt.module_base_name(pt.last_module_arg(chal_expr))
        chal_calls: list[frog_ast.FuncCall] = []

        def _collect_chal_call(n: frog_ast.ASTNode) -> bool:
            if isinstance(n, frog_ast.FuncCall) and isinstance(
                n.func, frog_ast.FieldAccess
            ):
                chal_calls.append(n)
            return False

        for m in chal_ast.methods:
            visitors.SearchVisitor(_collect_chal_call).visit(m.block)
        prg_meths = {
            cast(frog_ast.FieldAccess, c.func).name.lower() for c in chal_calls
        }
        if len(prg_meths) != 1 or prg_mod not in det_methods_by_module:
            return None
        prg_meth = prg_meths.pop()
        chal_param = red_mod.params[-1].name if red_mod.params else None
        # -- per-keypair SEGMENTATION of both UN-inlined bodies ---------------
        # The lemma relates the two WRAPPERS, whose bodies the exporter rendered
        # itself, so every statement index here is exact -- unlike the
        # post-``inline *`` body, which would have to model EC's expansion. The
        # game wrapper runs `keygen; <field projections>` per keypair and the
        # reduction `query; <derivations>` per keypair, so ONE `seq` per keypair
        # cuts each side at its own boundary and leaves a subgoal that is exactly
        # the single-keypair shape (one sample per side). Inside one segment each
        # inlined local is a first-and-only occurrence again, so the two sample
        # names are their bare source names -- the collision the n=1 gate above
        # declines on cannot arise. Design tripwire (EC exit 0, 0 admits):
        # ``tests/integration/ec_templates/hon_prg_init_nseed.ec``.
        game_mod = next(
            (
                d
                for d in theory_game_decls
                if isinstance(d, ec_ast.Module)
                and d.name == seed_holder_name.rpartition(".")[2]
            ),
            None,
        )
        game_init = (
            next((pr for pr in game_mod.procs if pr.name == "initialize"), None)
            if game_mod is not None
            else None
        )
        if game_init is None:
            return None

        def _segments(
            body: list[ec_ast.EcStmt], boundary: Callable[[ec_ast.EcStmt], bool]
        ) -> list[list[ec_ast.EcStmt]] | None:
            """Split ``body`` into one group per boundary statement, dropping a
            trailing ``return``. ``None`` unless the body STARTS at a boundary
            and holds nothing after the last group but that return."""
            stmts: list[ec_ast.EcStmt] = [
                st for st in body if not isinstance(st, ec_ast.VarDecl)
            ]
            if stmts and isinstance(stmts[-1], ec_ast.Return):
                stmts = stmts[:-1]
            if any(isinstance(st, (ec_ast.Return, ec_ast.If)) for st in stmts):
                return None
            cuts = [i for i, st in enumerate(stmts) if boundary(st)]
            if not cuts or cuts[0] != 0:
                return None
            return [stmts[a:b] for a, b in zip(cuts, cuts[1:] + [len(stmts)])]

        def _is_keygen_call(st: ec_ast.EcStmt) -> bool:
            return (
                isinstance(st, ec_ast.Call)
                and st.callee.partition(".")[2] == kg_proc.name
            )

        def _is_query_call(st: ec_ast.EcStmt) -> bool:
            return (
                isinstance(st, ec_ast.Call)
                and st.callee.partition(".")[0] == chal_param
            )

        # A game LOCAL assigned inside a segment but READ after it (the CT
        # binding games return their encaps key straight from a local, never
        # storing it) has no coupling conjunct naming it, so a `seq` that cuts it
        # off leaves `={res}` unprovable -- measured on CG_CT_DIFFKEY. Carry such
        # locals in that segment's invariant, valued by the same symbolic
        # `derivekeypair` evaluation the game-derived conjuncts use.
        def _carried_locals(
            segs: list[list[ec_ast.EcStmt]], body: list[ec_ast.EcStmt]
        ) -> list[list[str]] | None:
            decls = {d.name for d in body if isinstance(d, ec_ast.VarDecl)}
            tail_text = [
                str(getattr(st, "rhs", "")) + str(getattr(st, "expr", ""))
                for st in body
                if isinstance(st, ec_ast.Return)
            ]
            vals: dict[str, str] = {}
            out: list[list[str]] = []
            for k, seg in enumerate(segs):
                carried: list[str] = []
                for st in seg:
                    if isinstance(st, ec_ast.Call):
                        elems = _dkp_ret_elems(game_step, seed_refs_init[k])
                        if elems is None:
                            return None
                        vals[st.var] = "(" + ", ".join(elems) + ")"
                        continue
                    if not isinstance(st, ec_ast.Assign):
                        return None
                    proj = re.match(r"^\s*([A-Za-z_]\w*)\.`(\d+)\s*$", st.rhs)
                    if proj is None or proj.group(1) not in vals:
                        return None
                    src = vals[proj.group(1)].strip()
                    parts = (
                        cc_split_args(src[1:-1])
                        if src.startswith("(") and src.endswith(")")
                        else []
                    )
                    pos = int(proj.group(2))
                    if pos > len(parts):
                        return None
                    vals[st.var] = parts[pos - 1].strip()
                    if st.var in decls and any(
                        re.search(rf"\b{re.escape(st.var)}\b", t) for t in tail_text
                    ):
                        carried.append(f"{st.var}{{{gs}}} = {vals[st.var]}")
                out.append(carried)
            return out

        game_segs = _segments(list(game_init.body), _is_keygen_call)
        red_segs = _segments(list(red_init.body), _is_query_call)
        if game_segs is None or red_segs is None:
            return None
        if len(game_segs) != len(red_segs) or len(game_segs) != len(coupling_groups):
            return None
        carried_by_seg = _carried_locals(game_segs, list(game_init.body))
        if carried_by_seg is None:
            return None

        # -- formal-param -> declared-instance maps ---------------------------
        # A rendered scheme/reduction proc calls its own FORMAL parameter names
        # (``CG_seedbased(K, NG, G, H, L)`` calls ``K.derivekeypair``), but the
        # ``<M>_<m>_det`` axioms and the ``glob`` binders name the DECLARED
        # instances. Map one to the other off each side's applied module
        # expression, positionally.
        def _split_top_args(expr: str) -> list[str]:
            inner = expr[expr.index("(") + 1 : expr.rindex(")")] if "(" in expr else ""
            args, depth, cur = [], 0, ""
            for ch in inner:
                if ch == "," and depth == 0:
                    args.append(cur.strip())
                    cur = ""
                    continue
                depth += (ch == "(") - (ch == ")")
                cur += ch
            if cur.strip():
                args.append(cur.strip())
            return args

        def _param_map(mod: ec_ast.Module, applied_expr: str) -> dict[str, str] | None:
            args = [pt.module_base_name(a) for a in _split_top_args(applied_expr)]
            if len(args) < len(mod.params):
                return None
            return {p.name: a for p, a in zip(mod.params, args)}

        game_scheme_expr = pt.last_module_arg(resolver.resolve(game_step).module_expr)
        gmap = _param_map(ec_scheme, game_scheme_expr) if ec_scheme else None
        rmap = _param_map(red_mod, resolver.resolve(red_step).module_expr)
        if gmap is None or rmap is None:
            return None

        # -- peel builder ------------------------------------------------------
        called: list[str] = []

        def _subst_env(text: str, env: dict[str, str]) -> str:
            """Substitute each known local by its functional value (longest name
            first, whole-identifier match only)."""
            for k in sorted(env, key=len, reverse=True):
                text = re.sub(rf"\b{re.escape(k)}\b", env[k], text)
            return text

        def _peel(
            body: list[ec_ast.EcStmt],
            env0: dict[str, str],
            side: str,
            pmap: dict[str, str],
        ) -> list[str] | None:
            """Reverse-walk ``body`` emitting one ``call{side} (<M>_<m>_det ...)``
            per call and one ``wp.`` per contiguous assignment run."""
            env = dict(env0)
            events: list[tuple[str, ...]] = []
            for st in body:
                if isinstance(st, (ec_ast.VarDecl, ec_ast.Return)):
                    continue
                if isinstance(st, ec_ast.Assign):
                    env[st.var] = _subst_env(st.rhs, env)
                    events.append(("assign",))
                    continue
                if not isinstance(st, ec_ast.Call):
                    return None
                mod, dot, meth = st.callee.partition(".")
                if not dot:
                    return None
                if mod == chal_param:
                    mod, meth, argvals = prg_mod, prg_meth, ["sv"]
                else:
                    mod = pmap.get(mod, mod)
                    argvals = [
                        _subst_env(a, env)
                        for a in (cc_split_args(st.args) if st.args.strip() else [])
                    ]
                if meth not in det_methods_by_module.get(mod, set()):
                    return None  # a probabilistic call has no ``_det`` axiom
                alias = clone_alias_by_module.get(mod)
                if alias is None:
                    return None
                if mod not in called:
                    called.append(mod)
                applied = "".join(f" ({v})" for v in argvals)
                events.append(("call", f"{mod}_{meth}_det g_{mod}{applied}"))
                env[st.var] = (
                    f"({alias}.ev_{meth}" f"{''.join(f' ({v})' for v in argvals)})"
                    if argvals
                    else f"({alias}.ev_{meth})"
                )
            lines: list[str] = []
            pending = False
            for ev in reversed(events):
                if ev[0] == "assign":
                    pending = True
                    continue
                if pending:
                    lines.append("wp.")
                    pending = False
                lines.append(f"call{{{side}}} ({ev[1]}).")
            if pending:
                lines.append("wp.")
            return lines

        game_peel = _peel(
            list(dkp_proc.body), {dkp_proc.params[0].name: "sv"}, gs, gmap
        )
        red_peels = [_peel(list(seg), {}, rs, rmap) for seg in red_segs]
        if game_peel is None or any(rp is None for rp in red_peels) or not called:
            return None
        globs = " /\\ ".join(f"={{glob {m}}}" for m in declared_module_names)
        frozen = ", ".join(f"(glob {m}){{{gs}}}" for m in called)
        binders = " ".join(f"g_{m}" for m in called)
        lines: list[str] = []
        # Only the keypairs BEFORE the last get their own ``seq``: the final one
        # stays in the main goal so the closing ``skip => />`` still sees the
        # whole tail. A game whose encaps key is a proc LOCAL rather than a field
        # (the CT binding games return it directly) has no coupling conjunct
        # naming it, so a ``seq`` that cut it off would leave ``={res}``
        # unprovable -- measured on CG_CT_SAMEKEY. With one keypair there is no
        # ``seq`` at all and the emission is exactly what it was before.
        for k, red_peel in enumerate(red_peels):
            assert red_peel is not None
            last = k == len(red_peels) - 1
            done = [c for grp in coupling_groups[:k] for c in grp] + [
                c for grp in carried_by_seg[:k] for c in grp
            ]
            inner_inv = " /\\ ".join(
                ([globs] if globs else [])
                + done
                + [f"{game_seed}{{{gs}}} = {red_seed}{{{rs}}}"]
            )
            if not last:
                outer_inv = " /\\ ".join(
                    ([globs] if globs else [])
                    + done
                    + coupling_groups[k]
                    + carried_by_seg[k]
                )
                a_cnt, b_cnt = len(game_segs[k]), len(red_segs[k])
                if gs != "1":
                    a_cnt, b_cnt = b_cnt, a_cnt
                lines += [f"seq {a_cnt} {b_cnt} : ({outer_inv}).", "+ inline *."]
            else:
                lines.append("inline *.")
            lines += [
                f"seq 1 1 : ({inner_inv}).",
                f"{'-' if not last else '+'} rnd; skip => />.",
                f"exists* {frozen}, {game_seed}{{{gs}}}.",
                f"elim* => {binders} sv.",
                "wp.",
                *game_peel,
                *red_peel,
                "skip => />.",
            ]
        return lines

    def _cross_stage_field_coupling(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-arguments,too-many-positional-arguments
        step_a: frog_ast.Step,
        step_b: frog_ast.Step,
        rest_a: list[frog_ast.Field],
        rest_b: list[frog_ast.Field],
        base_a: str,
        base_b: str,
    ) -> list[str] | None:
        """Conjuncts for two reductions holding the SAME logical material at
        DIFFERENT derivation stages; ``None`` off-shape.

        The CK HON ``R_PRG_L ~ R_KG_PQ_L`` decaps hops: one side stores the
        derived T keypair (``t_keys_k``), the other the seed it derives from
        (``seed_T_k``). Same-name/same-type fields couple by equality (the caller
        does that); these do not, so the per-oracle lemmas were left with a
        glob-only coupling and were unprovable as stated -- the two sides' decaps
        read differently-owned keys with nothing relating them.

        Shape required, checked structurally: the two unshared lists have equal
        length; each side-A field's rendered ``initialize`` value is a SINGLE
        ev-application of one argument; each side-B field is an ANCHOR (its value
        is a bare atom -- a sample, or a single challenger call). Pair the two
        lists ORDINALLY (declaration order on both sides) and restate side A's
        field as its ev-application over the paired side-B field.

        SOUNDNESS: the conjunct is true exactly when side A's argument and side
        B's field carry the same value, which is what the hop's own assumption
        provides (a PRG-random slice against a fresh uniform sample). It is
        PROVEN by the hop's ``initialize`` lemma or EC rejects the file -- but on
        the cells this currently fires for, that lemma still admits, so until it
        closes the conjunct is ASSUMED. Flagged in the plan as such."""
        if len(rest_a) != len(rest_b) or not rest_a:
            return None
        red_mods: list[ec_ast.Module] = []
        for st in (step_a, step_b):
            if st.reduction is None:
                return None
            mod = next(
                (
                    d
                    for d in ec_reductions
                    if isinstance(d, ec_ast.Module) and d.name == st.reduction.name
                ),
                None,
            )
            if mod is None:
                return None
            red_mods.append(mod)

        def _init_values(mod: ec_ast.Module) -> dict[str, str] | None:
            """Each field's functional value off the RENDERED ``initialize``:
            calls functionalize to their ``ev_`` form, assigns substitute, and a
            sample or challenger call stays an opaque atom named for its var."""
            proc = next((p for p in mod.procs if p.name == "initialize"), None)
            if proc is None:
                return None
            env: dict[str, str] = {}

            def _sub(text: str) -> str:
                if not env:
                    return text
                pat = "|".join(re.escape(k) for k in sorted(env, key=len, reverse=True))
                return re.sub(rf"\b({pat})\b", lambda m: env[m.group(1)], text)

            chal = mod.params[-1].name if mod.params else None
            for st in proc.body:
                if isinstance(st, (ec_ast.VarDecl, ec_ast.Return)):
                    continue
                if isinstance(st, ec_ast.Sample):
                    env[st.var] = f"@sample:{st.var}"
                    continue
                if isinstance(st, ec_ast.Assign):
                    env[st.var] = f"({_sub(st.rhs)})"
                    continue
                if not isinstance(st, ec_ast.Call):
                    return None
                mod_name, dot, meth = st.callee.partition(".")
                if not dot:
                    return None
                if mod_name == chal:
                    env[st.var] = f"@chal:{meth}"
                    continue
                alias = clone_alias_by_module.get(mod_name)
                if alias is None:
                    return None
                if meth not in det_methods_by_module.get(mod_name, set()):
                    # A PROBABILISTIC call has no ``ev_`` value; marking it as one
                    # would let a bogus derivation reach a conjunct.
                    env[st.var] = f"@prob:{st.var}"
                    continue
                args = (
                    [_sub(a) for a in cc_split_args(st.args)] if st.args.strip() else []
                )
                env[st.var] = (
                    f"({alias}.ev_{meth}" + "".join(f" ({a})" for a in args) + ")"
                    if args
                    else f"({alias}.ev_{meth})"
                )
            return env

        vals_a, vals_b = _init_values(red_mods[0]), _init_values(red_mods[1])
        if vals_a is None or vals_b is None:
            return None

        # pylint: disable=protected-access
        def _emit(
            derived: list[frog_ast.Field],
            anchors: list[frog_ast.Field],
            dvals: dict[str, str],
            avals: dict[str, str],
            dbase: str,
            abase: str,
            dmem: str,
            amem: str,
        ) -> list[str] | None:
            out: list[str] = []
            for fd, fan in zip(derived, anchors):
                vd, van = dvals.get(fd.name), avals.get(fan.name)
                if vd is None or van is None or not van.startswith("@"):
                    return None  # the anchor side must be an undecomposed atom
                m = re.fullmatch(r"\((\S+\.ev_\w+) \((.+)\)\)", vd.strip())
                if m is None or "@atom:" in m.group(1):
                    return None  # the derived side must be ONE ev-application
                out.append(
                    f"{dbase}.{mt._ec_field_name(fd.name)}{{{dmem}}} = "
                    f"({m.group(1)} ({abase}.{mt._ec_field_name(fan.name)}{{{amem}}}))"
                )
            return out

        # Either orientation: the derived side is whichever one holds the
        # ev-application. The CK chain alternates -- hop_2/hop_12 derive on the
        # left, hop_4/hop_14 on the right -- so fixing one orientation would
        # silently decline half the class.
        # When NEITHER side holds an ev-application (both are undecomposed
        # atoms), the relation comes from the CHALLENGER's own body instead.
        def _chal_derivation_op(  # pylint: disable=too-many-return-statements
            step: frog_ast.Step, meth: str
        ) -> str | None:
            """``<clone>.ev_<m>`` when ``step``'s challenger answers ``meth`` by
            sampling a seed and returning ONE call on it -- the KeyGenEquiv
            ``FromDeriveKeyPair`` shape. Read off the challenger game's own AST;
            NEVER inferred from the two field types, since several ops can share
            a signature and a wrong pick is a wrong-but-well-typed coupling."""
            # pylint: disable=protected-access
            chal = engine._get_game_ast(step.challenger, None)
            # pylint: enable=protected-access
            if chal is None:
                return None
            meth_ast = next(
                (x for x in chal.methods if x.signature.name.lower() == meth.lower()),
                None,
            )
            if meth_ast is None:
                return None
            stmts = list(meth_ast.block.statements)
            if (
                len(stmts) != 2
                or not isinstance(stmts[0], frog_ast.Sample)
                or not isinstance(stmts[0].var, frog_ast.Variable)
                or not isinstance(stmts[1], frog_ast.ReturnStatement)
            ):
                return None
            call = stmts[1].expression
            if (
                not isinstance(call, frog_ast.FuncCall)
                or not isinstance(call.func, frog_ast.FieldAccess)
                or len(call.args) != 1
                or not isinstance(call.args[0], frog_ast.Variable)
                or call.args[0].name != stmts[0].var.name
            ):
                return None
            # The challenger AST is already INSTANTIATED, so the call names the
            # declared module directly (``KEM_T.DeriveKeyPair``) -- no need to
            # walk the reduction's module expression to recover it.
            obj = call.func.the_object
            if not isinstance(obj, frog_ast.Variable):
                return None
            alias = clone_alias_by_module.get(obj.name)
            if alias is None or call.func.name.lower() not in det_methods_by_module.get(
                obj.name, set()
            ):
                return None  # a probabilistic derivation has no ``ev_`` value
            return f"{alias}.ev_{call.func.name.lower()}"

        def _emit_both_anchor(  # pylint: disable=too-many-arguments,too-many-positional-arguments
            fields_c: list[frog_ast.Field],
            fields_s: list[frog_ast.Field],
            vals_c: dict[str, str],
            vals_s: dict[str, str],
            step_c: frog_ast.Step,
            base_c: str,
            base_s: str,
            mem_c: str,
            mem_s: str,
        ) -> list[str] | None:
            out: list[str] = []
            for fc, fs in zip(fields_c, fields_s):
                vc, vs = vals_c.get(fc.name), vals_s.get(fs.name)
                if vc is None or vs is None:
                    return None
                if not vc.startswith("@chal:") or not vs.startswith("@sample:"):
                    return None
                op = _chal_derivation_op(step_c, vc[len("@chal:") :])
                if op is None:
                    return None
                out.append(
                    f"{base_c}.{mt._ec_field_name(fc.name)}{{{mem_c}}} = "
                    f"({op} ({base_s}.{mt._ec_field_name(fs.name)}{{{mem_s}}}))"
                )
            return out

        return (
            _emit(rest_a, rest_b, vals_a, vals_b, base_a, base_b, "1", "2")
            or _emit(rest_b, rest_a, vals_b, vals_a, base_b, base_a, "2", "1")
            or _emit_both_anchor(
                rest_a, rest_b, vals_a, vals_b, step_a, base_a, base_b, "1", "2"
            )
            or _emit_both_anchor(
                rest_b, rest_a, vals_b, vals_a, step_b, base_b, base_a, "2", "1"
            )
        )
        # pylint: enable=protected-access

    def _query_delegate_pair_coupling(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> str | None:
        """Same-named field equalities for a red<->red hop where NEITHER
        reduction delegates its ``Initialize`` to a challenger: each derives every
        stored field itself, whether from a challenger ORACLE
        (``challenger.Query()``/``.Generate()`` -- the HON_BIND ``R_PRG ~
        R_KG_PQ`` pairs) or straight from the scheme (``R_KDF``'s
        ``KEM_PQ.keygen()``). The composite (wall-7) path correctly declines
        there -- nothing repacks a challenger ``Initialize`` result -- leaving
        glob-ONLY couplings, i.e. per-oracle lemmas that are unprovable as
        stated because the two sides' ``decaps`` calls read differently-owned
        keys with nothing relating them.

        Both sides hold the SAME logical derived material under the SAME field
        names and types, so the coupling is the pairwise field equality set. The
        conjuncts are PROVEN, not assumed: the hop's own ``initialize`` lemma has
        to establish them, and EC rejects the file if it cannot.

        The gate is "neither side delegates ``Initialize``" rather than "both
        sides query a challenger": requiring a challenger query excluded the
        self-keygen side of the HON ``R_KDF ~ R_KG_PQ_R`` hop, whose fields are
        identically named and typed all the same. Pure string construction, no
        ``live_state_holders`` side effects (a first attempt that widened
        ``_composite_reduction_step``'s gate instead cascaded into the
        module-restriction lists of 15+ exports). ``None`` off-shape."""
        if step_a.reduction is None or step_b.reduction is None:
            return None
        names = (step_a.reduction.name, step_b.reduction.name)
        if any(_reduction_init_delegates(n) for n in names):
            return None
        helpers_by = {
            h.name: h for h in proof.helpers if isinstance(h, frog_ast.Reduction)
        }
        ha, hb = helpers_by.get(names[0]), helpers_by.get(names[1])
        if ha is None or hb is None or not ha.fields or not hb.fields:
            return None
        b_types = {f.name: f.type for f in hb.fields}
        shared = [
            f.name for f in ha.fields if f.name in b_types and b_types[f.name] == f.type
        ]
        if not shared:
            return None
        base_a = pt.module_base_name(resolver.resolve(step_a).module_expr)
        base_b = pt.module_base_name(resolver.resolve(step_b).module_expr)
        globs = " /\\ ".join(f"={{glob {m}}}" for m in declared_module_names)
        # pylint: disable=protected-access
        conj = [
            f"{base_a}.{mt._ec_field_name(f)}{{1}} = {base_b}.{mt._ec_field_name(f)}{{2}}"
            for f in shared
        ]
        # pylint: enable=protected-access
        rest_a = [f for f in ha.fields if f.name not in shared]
        rest_b = [f for f in hb.fields if f.name not in shared]
        if rest_a or rest_b:
            cross = _cross_stage_field_coupling(
                step_a, step_b, rest_a, rest_b, base_a, base_b
            )
            if cross is None:
                return None
            conj += cross
        fields = " /\\ ".join(conj)
        return f"{globs} /\\ {fields}" if globs else fields

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
        query_coupling = _query_delegate_pair_coupling(step_a, step_b)
        if query_coupling is not None:
            return query_coupling
        prg_coupling = _prg_query_game_coupling(step_a, step_b)
        if prg_coupling is not None:
            return prg_coupling

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

        def _field_or_component_ref(  # pylint: disable=too-many-arguments
            target_ty: str,
            mod_fields: list[frog_ast.Field],
            base: str,
            side: str,
            prefer: str,
            *,
            occurrence: int = 0,
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
            #
            # ``occurrence`` allocates ORDINALLY among same-typed candidates: the
            # k-th caller-side field of a given type takes the k-th matching
            # field/component here (both in declaration order). First-match-only
            # (the old behavior, = ``occurrence 0``) paired a two-keypair game's
            # BOTH reduction eks to ``ek0`` -- a duplicated, unestablishable
            # coupling that made the PK/DIFFKEY ``hop_0_challenge`` goal false
            # (the wall parked as "smt scale" 2026-07-29). Out-of-range ->
            # ``None`` (the field stays uncoupled) rather than a wrong reuse.
            # pylint: disable=protected-access
            def _matches(f: frog_ast.Field) -> list[str]:
                out: list[str] = []
                if _ec_ty(f.type) == target_ty:
                    out.append(f"{base}.{mt._ec_field_name(f.name)}{{{side}}}")
                if isinstance(f.type, frog_ast.ProductType):
                    for i, comp in enumerate(f.type.types):
                        if _ec_ty(comp) == target_ty:
                            out.append(
                                f"{base}.{mt._ec_field_name(f.name)}.`{i + 1}{{{side}}}"
                            )
                return out

            # pylint: enable=protected-access
            pref = next((f for f in mod_fields if f.name == prefer), None)
            if pref is not None:
                pref_hits = _matches(pref)
                if pref_hits:
                    return pref_hits[0]
            candidates: list[str] = []
            for other in mod_fields:
                if other.name != prefer:
                    candidates.extend(_matches(other))
            return candidates[occurrence] if occurrence < len(candidates) else None

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
            # Ordinal slots: the k-th reduction field of a given EC type takes
            # the k-th same-typed game field/component (see
            # ``_field_or_component_ref``); counted in ``fields`` order (the
            # reduction's field declaration order -- derivation order for the
            # CFRG reductions, keypair 0 before keypair 1).
            seen_ty: dict[str, int] = {}
            for fld in fields:
                ec_f = mt._ec_field_name(fld)  # pylint: disable=protected-access
                red_ty = red_type_by_name.get(fld)
                if other_game_ast is not None and red_ty is not None:
                    # Game endpoint: it may hold the reduction's field PACKED under
                    # a different name; match by type/component.
                    ty_key = _ec_ty(red_ty)
                    occ = seen_ty.get(ty_key, 0)
                    seen_ty[ty_key] = occ + 1
                    other_ref = _field_or_component_ref(
                        ty_key,
                        list(other_game_ast.fields),
                        other_base,
                        other_side,
                        fld,
                        occurrence=occ,
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
            seen_chal_ty: dict[str, int] = {}
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
                # reduction side by the challenger field's type. Ordinal slots as
                # in the game-endpoint loop above.
                if chal_ty is not None and red_ast is not None:
                    ty_key = _ec_ty(chal_ty)
                    occ = seen_chal_ty.get(ty_key, 0)
                    seen_chal_ty[ty_key] = occ + 1
                    red_ref = _field_or_component_ref(
                        ty_key,
                        list(red_ast.fields),
                        red_base,
                        red_side,
                        fld,
                        occurrence=occ,
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
            #
            # GAME-ENDPOINT ONLY: in a reduction<->reduction hop (the two-keypair
            # binding ``R_KDF ~ R_KG_R`` KDF hops), ``other_step.challenger`` is
            # the OTHER reduction's assumption game, and pairing the two
            # challengers' same-named SOURCE fields emits references the
            # materialized EC challenger modules do not hold
            # (``KDFCollisionResistance_Unbreakable.ek0`` /
            # ``KeyGenEquiv_FromKeyGen.ek0`` -- "unknown variable"). The
            # forwarded seam only makes sense when the other endpoint IS the
            # theorem game whose live field the reduction forwards.
            # pylint: disable=protected-access
            other_game = (
                engine._get_game_ast(other_step.challenger, None)
                if other_step.reduction is None
                else None
            )
            chal_game = engine._get_game_ast(red_step.challenger, None)
            # pylint: enable=protected-access
            held = set(fields)
            chal_fields = {f.name for f in chal_game.fields}
            if other_game is not None:
                for fld in (f.name for f in other_game.fields):
                    if fld in held or fld not in chal_fields:
                        continue
                    if not _field_read_post_init(other_game, fld):
                        continue
                    ec_f = mt._ec_field_name(fld)  # pylint: disable=protected-access
                    conj.append(
                        f"{other_base}.{ec_f}{{{other_side}}} = "
                        f"{chal_base}.{ec_f}{{{red_side}}}"
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

        # A reduction endpoint that neither holds nor renames the live field
        # resolves its ``_live_state_ref`` to ``<Chal>.<field>``; when the
        # challenger game does not DECLARE that field either, the ref names no
        # module variable (EC "unknown variable ..." -- the reduction<->
        # reduction KDF hops, whose challengers are the field-less
        # KDFCollisionResistance / KeyGenEquiv oracles).
        # ``_packed_decomposition_coupling`` diverts the one-game version of
        # this (``fallback_to_stateless_chal``), but a red<->red hop has no
        # game endpoint to divert on. Drop the field conjunct -- the wrapper
        # couplings above already carry the cross-side state correspondence --
        # keeping the abstract-scheme glob equality. A challenger that DOES
        # declare the field (GHP18's MultiChal ``pk``) keeps its valid,
        # load-bearing conjunct byte-identically.
        def _invalid_live_ref(step: frog_ast.Step) -> bool:
            if step.reduction is None:
                return False
            # pylint: disable=protected-access
            chal_ast = engine._get_game_ast(step.challenger, None)
            # pylint: enable=protected-access
            lf = _live_state_field_name()
            return (
                chal_ast is not None
                and all(f.name != lf for f in chal_ast.fields)
                and not _reduction_holds_field(step.reduction.name, lf)
                and _reduction_renamed_live_field(step.reduction.name, lf) is None
            )

        if _invalid_live_ref(step_a) or _invalid_live_ref(step_b):
            return glob_invariant_conj
        field = pt.live_state_coupling(_live_state_ref(step_a), _live_state_ref(step_b))
        # Prefix the abstract-scheme glob equality so ``sim`` can relate the
        # post-init oracles' abstract calls (``K.encaps`` / ``F.evaluate``)
        # under this coupling. ``glob_invariant_conj`` is empty for proofs with
        # no declared abstract scheme module (output unchanged there).
        return f"{glob_invariant_conj} /\\ {field}" if glob_invariant_conj else field

    def _is_lazyro_honest_hop(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> tuple[str, str, str, str, str] | None:
        """When one hop endpoint is a plain game that reads the shared RO and the
        other is a delegating reduction whose challenger is the CGLazyRO *Honest*
        game (its ``Initialize`` samples a FRESH RO the reduction then uses for
        every RO query -- HashG forwards to ``challenger.Hash``), the same-side
        ``<chal>.h{2} = RO.h{2}`` coupling is UNPROVABLE: the reduction samples the
        challenger RO and the game RO independently, so they are independent
        uniforms on the reduction side. Return ``(game_side, red_side, chal_base,
        chal_field, ro_ref)`` so the pr-lemma instead couples ``RO.h{game_side} =
        <chal>.h{red_side}`` (both live) and drops the dead ``RO.h{red_side}``
        sample (the validated ``ec_templates/lazyro_honest_main{,_calls}.ec``
        tactic). ``None`` off-shape, so every other hop is byte-identical."""
        # pylint: disable=protected-access
        ro_ref = next(iter(top_types.ro_by_arrow_type().values()), None)
        if ro_ref is None:
            return None
        game_sides = [
            side for st, side in ((step_a, "1"), (step_b, "2")) if st.reduction is None
        ]
        red_pairs = [
            (st, side)
            for st, side in ((step_a, "1"), (step_b, "2"))
            if st.reduction is not None and _reduction_init_delegates(st.reduction.name)
        ]
        if len(game_sides) != 1 or len(red_pairs) != 1:
            return None
        red_step, red_side = red_pairs[0]
        chal_base = pt.module_base_name(
            pt.last_module_arg(resolver.resolve(red_step).module_expr)
        )
        if "Honest" not in chal_base:
            return None
        chal_game = engine._get_game_ast(red_step.challenger, None)
        chal_field = next(
            (
                mt._ec_field_name(cf.name)
                for cf in (chal_game.fields if chal_game else [])
                if isinstance(cf.type, frog_ast.FunctionType)
            ),
            None,
        )
        if chal_field is None:
            return None
        # pylint: enable=protected-access
        return (game_sides[0], red_side, chal_base, chal_field, ro_ref)

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
        lazy = _is_lazyro_honest_hop(step_a, step_b)
        if lazy is not None:
            l_game_side, l_red_side, l_chal_base, l_chal_field, l_ro_ref = lazy
            live_state_holders.add(l_chal_base)
            return (
                f"{l_ro_ref}{{{l_game_side}}} = "
                f"{l_chal_base}.{l_chal_field}{{{l_red_side}}}"
            )
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

    def _keygen_decapskey_fields(game: frog_ast.Game | None) -> list[str]:
        """The game's DECAPS-KEY state fields, in ``Initialize`` program order.

        Read off the ``[ek, dk] = K.KeyGen()`` destructures: the KeyGen return is
        ``[EncapsKey, DecapsKey]``, so a field assigned element 1 of a KeyGen temp
        is a DecapsKey. A CT-binding game holds ONLY those (its EncapsKeys are
        locals), so this returns the same list its declaration order gives and the
        caller is unchanged; a PK-binding game also holds ``ek0``/``ek1`` for its
        win term, and those must not be mistaken for seeds -- the lazy-RO coupling
        applies the random oracle to them, and the RO's domain is the seed.
        Returns ``[]`` off-shape, so the caller keeps its declaration-order list."""
        if game is None:
            return []
        init = _find_init(game)
        if init is None:
            return []
        field_names = {f.name for f in game.fields}
        keygen_tmps: list[str] = []
        out: list[str] = []
        for stmt in init.block.statements:
            if not isinstance(stmt, frog_ast.Assignment) or not isinstance(
                stmt.var, frog_ast.Variable
            ):
                continue
            value = stmt.value
            if isinstance(value, frog_ast.FuncCall):
                func = value.func
                if isinstance(func, frog_ast.FieldAccess) and func.name == "KeyGen":
                    keygen_tmps.append(stmt.var.name)
            elif (
                isinstance(value, frog_ast.ArrayAccess)
                and isinstance(value.the_array, frog_ast.Variable)
                and value.the_array.name in keygen_tmps
                and isinstance(value.index, frog_ast.Integer)
                and value.index.num == 1
                and stmt.var.name in field_names
            ):
                out.append(stmt.var.name)
        return out

    def _game_keygen_field_pairs(
        game: frog_ast.Game | None,
    ) -> list[tuple[str, str]]:
        """``(ek_field, dk_field)`` per ``[ek, dk] = K.KeyGen()`` destructure of
        the game's ``Initialize``, in program order, keeping only destructures
        whose BOTH elements land in state fields. A CT-binding game stores only
        the decaps key (its EncapsKey is a local) -> no pair -> callers that
        gate on pairs leave it byte-identical."""
        if game is None:
            return []
        init = _find_init(game)
        if init is None:
            return []
        field_names = {f.name for f in game.fields}
        tmp_ek: dict[str, str] = {}
        tmp_dk: dict[str, str] = {}
        order: list[str] = []
        for stmt in init.block.statements:
            if not isinstance(stmt, frog_ast.Assignment) or not isinstance(
                stmt.var, frog_ast.Variable
            ):
                continue
            value = stmt.value
            if isinstance(value, frog_ast.FuncCall):
                func = value.func
                if isinstance(func, frog_ast.FieldAccess) and func.name == "KeyGen":
                    order.append(stmt.var.name)
            elif (
                isinstance(value, frog_ast.ArrayAccess)
                and isinstance(value.the_array, frog_ast.Variable)
                and value.the_array.name in order
                and isinstance(value.index, frog_ast.Integer)
                and value.index.num in (0, 1)
                and stmt.var.name in field_names
            ):
                dst = tmp_ek if value.index.num == 0 else tmp_dk
                dst[value.the_array.name] = stmt.var.name
        return [(tmp_ek[t], tmp_dk[t]) for t in order if t in tmp_ek and t in tmp_dk]

    def _lazyro_preprocess_derivekeypair(dkp: ec_ast.Proc) -> ec_ast.Proc | None:
        """The theorem scheme's ``derivekeypair`` EC proc rewritten so
        :func:`bch.keygen_derived_ev` can render it in the ROM instantiation.

        Three rewrites, each structural: (a) the seed-EXPANSION call (its single
        arg is the proc's seed parameter; in a ROM proof that callee is a
        concrete RO-PRG module with no ``ev_`` clone) becomes a pure assign of
        the placeholder application ``(__ROH__ <seed>)`` -- the caller
        substitutes the real ``RO.h{s}`` reference; (b) every other callee is
        renamed to its applied let-name so ``clone_alias`` resolves it; (c) a
        callee whose let names a CONCRETIZED WRAPPER scheme
        (``foreign_concrete_modules``) is inlined ONE level -- the wrapper's own
        concrete EC body is walked with its module params bound to the
        instance's args and its locals freshened -- so the render names the
        INNER module's ``ev_`` ops, the forms the pr-init's fully-inlined game
        actually establishes. ``None`` on any non-linear shape."""
        if ec_scheme is None or len(dkp.params) != 1:
            return None
        seed_param = dkp.params[0].name
        param_to_arg = dict(
            zip((p.name for p in ec_scheme.params), scheme_applied_args)
        )

        def _rn(s: str, mapping: dict[str, str]) -> str:
            for k in sorted(mapping, key=len, reverse=True):
                s = re.sub(rf"\b{re.escape(k)}\b", mapping[k], s)
            return s

        out: list[ec_ast.EcStmt] = []
        fresh = 0
        for stmt in dkp.body:
            if isinstance(stmt, (ec_ast.Sample, ec_ast.If)):
                return None
            if not isinstance(stmt, ec_ast.Call):
                out.append(stmt)
                continue
            mod, dot, meth = stmt.callee.partition(".")
            if not dot:
                return None
            let = param_to_arg.get(mod, mod)
            if stmt.args.strip() == seed_param:
                out.append(ec_ast.Assign(stmt.var, f"(__ROH__ {seed_param})"))
                continue
            wrapper = foreign_concrete_modules.get(let)
            if wrapper is None:
                out.append(ec_ast.Call(stmt.var, f"{let}.{meth}", stmt.args))
                continue
            wproc = next((p for p in wrapper.procs if p.name == meth), None)
            wlet = next((l for l in proof.lets if l.name == let), None)
            if (
                wproc is None
                or len(wproc.params) != 1
                or wlet is None
                or not isinstance(wlet.value, frog_ast.FuncCall)
            ):
                return None
            wargs = [
                a.name for a in wlet.value.args if isinstance(a, frog_ast.Variable)
            ]
            if len(wargs) != len(wrapper.params):
                return None
            sub: dict[str, str] = dict(zip((p.name for p in wrapper.params), wargs))
            sub[wproc.params[0].name] = stmt.args.strip()
            pfx = f"_w{fresh}_"
            fresh += 1
            ret_expr: str | None = None
            for ws in wproc.body:
                if isinstance(ws, ec_ast.VarDecl):
                    continue
                if isinstance(ws, ec_ast.Return):
                    ret_expr = _rn(ws.expr, sub)
                    break
                if isinstance(ws, ec_ast.Assign):
                    rhs = _rn(ws.rhs, sub)
                    sub[ws.var] = pfx + ws.var
                    out.append(ec_ast.Assign(pfx + ws.var, rhs))
                elif isinstance(ws, ec_ast.Call):
                    wm, wd, wmeth = ws.callee.partition(".")
                    if not wd:
                        return None
                    args = _rn(ws.args, sub)
                    callee_mod = sub.get(wm, wm)
                    sub[ws.var] = pfx + ws.var
                    out.append(ec_ast.Call(pfx + ws.var, f"{callee_mod}.{wmeth}", args))
                else:
                    return None
            if ret_expr is None:
                return None
            out.append(ec_ast.Assign(stmt.var, ret_expr))
        return ec_ast.Proc(dkp.name, dkp.params, dkp.return_type, out)

    def _lazyro_derived_key_coupling(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> str:
        """``<red>.<field>{rs} = <fn of RO[<game_dk0>]{gs}>`` for each stored key
        of a lazy-RO Honest reduction (``R_LazyRO_L``) that DERIVES its keys from
        ``challenger.Hash(seed_0)`` but DISCARDS ``seed_0`` (a local, returned as
        the decaps key).  The game stores only its seed ``dk0`` and re-derives the
        SAME keys IN-challenge via the shared RO; the reduction's stored keys are
        functions of ``RO[dk0]`` (``Hash(seed_0) = RO[seed_0] = RO[dk0]`` under the
        RO coupling + init seed equality).  The per-oracle RO-only coupling can't
        relate them, so the challenge peel (leg ii) needs THIS relation in its pre;
        the pr-lemma's inline init establishes it and challenge/hashg preserve it
        (neither writes the keys or the RO).  Each field's derivation is read off
        the reduction's ``Initialize``: a direct ``<field> <@ <M>.<m>(<slice of
        y_0>)`` -> ``<M>_c.ev_<m> (<slice, y_0 -> RO[dk0]>)``; a wrapper-passthrough
        ``derivekeypair`` whose result IS the seed (field type == slice-result
        type) -> the slice directly.  ``""`` off-shape (byte-identical for every
        non-lazy-RO proof).  EC-GATED: the coupling is PROVEN (established at init,
        consumed at challenge), never admitted, so a wrong text makes EC reject."""
        lazy = _is_lazyro_honest_hop(step_a, step_b)
        if lazy is None:
            return ""
        game_side, red_side, _cb, _cf, ro_ref = lazy
        game_step = step_a if step_a.reduction is None else step_b
        red_step = step_b if step_a.reduction is None else step_a
        if red_step.reduction is None:
            return ""
        red = _get_reduction(red_step.reduction.name)
        if red is None:
            return ""
        init = _find_init(red)
        if init is None:
            return ""
        init = _hoist_inline_challenger_hashes(init)
        red_base = pt.module_base_name(resolver.resolve(red_step).module_expr)
        # pylint: disable=protected-access
        fld_ty = {f.name: top_types.translate_type(f.type).text for f in red.fields}
        type_map: dict[str, frog_ast.Type] = {f.name: f.type for f in red.fields}
        for stmt in init.block.statements:
            mt._seed_type_map(stmt, type_map)
        for nm, t in list(type_map.items()):
            if isinstance(t, (frog_ast.Variable, frog_ast.FieldAccess)):
                resolved = top_types.resolve(t)
                if isinstance(resolved, frog_ast.ProductType):
                    type_map[nm] = resolved
        exprs = expr_translator.ExpressionTranslator(
            top_types, type_of_factory(type_map, {})
        )
        # The hash-result locals (``y_0``, ``y_1``, ... one per stored seed): each
        # is the var assigned ``challenger.Hash(seed_i)``, in program order. A
        # DIFFKEY/two-keypair reduction hashes TWO seeds, deriving keypair-0 from
        # ``y_0`` and keypair-1 from ``y_1``; the game stores TWO seeds ``dk0``,
        # ``dk1`` and re-derives each in-challenge via ``RO[dk_i]``. So the i-th
        # hash result couples to ``RO[game seed field i]`` (both draw keypair-0
        # before keypair-1: the reduction hashes ``seed_0`` first and the game
        # declares ``dk0`` first). A single-keypair (SAMEKEY) reduction has one
        # hash var and one game field, so this reduces to ``RO[dk0]`` for every
        # field -- byte-identical.
        hash_vars: list[str] = []
        val: dict[str, frog_ast.Expression] = {}
        for stmt in init.block.statements:
            if isinstance(stmt, frog_ast.Assignment) and isinstance(
                stmt.var, frog_ast.Variable
            ):
                val[stmt.var.name] = stmt.value
                if (
                    isinstance(stmt.value, frog_ast.FuncCall)
                    and isinstance(stmt.value.func, frog_ast.FieldAccess)
                    and stmt.value.func.name.lower() == "hash"
                ):
                    hash_vars.append(stmt.var.name)
        if not hash_vars:
            return ""
        # ``_live_state_ref`` yields ``<holder>.dk0`` (game field 0) and records the
        # holder in ``live_state_holders``; the game's remaining seed fields are its
        # siblings on the same holder, in declaration order (matching the hash
        # order). Bail (admit) if the game does not expose one seed field per hash.
        #
        # Restrict to the fields the RO can actually be APPLIED to -- those whose
        # type matches the hashed seed's. A CT-binding game holds only DecapsKeys,
        # so every field qualifies and this is a no-op; a PK-binding game ALSO
        # holds the EncapsKeys it compares (``ek0, ek1, dk0, dk1``), and taking
        # them in bare declaration order made the coupling read ``RO[ek0]`` -- an
        # EncapsKey where the RO's domain is the seed, which EC rejects outright
        # ("this expression has type").
        game_ref0 = _live_state_ref(game_step)
        game_holder = game_ref0.rsplit(".", 1)[0]
        outer_gf = game_file_by_name.get(proof.theorem.name)
        all_game_fields = (
            list(outer_gf.games[0].fields)
            if outer_gf is not None and outer_gf.games
            else []
        )
        game_seed_fields = _keygen_decapskey_fields(
            outer_gf.games[0] if outer_gf is not None and outer_gf.games else None
        ) or [f.name for f in all_game_fields]
        if len(game_seed_fields) < len(hash_vars):
            return ""
        # Per-hash-var: its translated EC form and its ``RO[game seed field i]``.
        hv_ec = {hv: exprs.translate(frog_ast.Variable(hv)) for hv in hash_vars}
        hv_lookup = {
            hv: f"({ro_ref}{{{game_side}}} {game_holder}.{game_seed_fields[i]}"
            f"{{{game_side}}})"
            for i, hv in enumerate(hash_vars)
        }
        hash_var_set = set(hash_vars)

        def _slice_of_hash(e: frog_ast.Expression) -> frog_ast.Slice | None:
            if (
                isinstance(e, frog_ast.Slice)
                and isinstance(e.the_array, frog_ast.Variable)
                and e.the_array.name in hash_var_set
            ):
                return e
            return None

        def _render_slice(sl: frog_ast.Slice) -> str:
            hv = sl.the_array.name  # type: ignore[attr-defined]
            return re.sub(
                rf"\b{re.escape(hv_ec[hv])}\b", hv_lookup[hv], exprs.translate(sl)
            )

        conj: list[str] = []

        def _slice_result_ty(sl: frog_ast.Slice) -> str:
            return top_types.translate_type(
                frog_ast.BitStringType(
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.SUBTRACT, sl.end, sl.start
                    )
                )
            ).text

        def _deref(name: str) -> frog_ast.Expression | None:
            e: frog_ast.Expression | None = val.get(name)
            hops = 0
            while isinstance(e, frog_ast.Variable) and e.name in val and hops < 4:
                e = val[e.name]
                hops += 1
            return e

        def _kp_slice(arr: str) -> frog_ast.Slice | None:
            """The RO slice arg of ``arr <@ <M>.derivekeypair(<slice of y_i>)``."""
            t = val.get(arr)
            if (
                isinstance(t, frog_ast.FuncCall)
                and isinstance(t.func, frog_ast.FieldAccess)
                and isinstance(t.func.the_object, frog_ast.Variable)
                and t.func.name.lower() == "derivekeypair"
                and len(t.args) == 1
            ):
                return _slice_of_hash(t.args[0])
            return None

        # Tuple vars whose ``derivekeypair`` is a GENUINE keypair (its ``.`2`` decaps
        # key is stored in a NON-slice-typed field -> not the SeededKEMWrapper seed
        # passthrough). For these, BOTH projections need coupling (the KDF reads the
        # ``.`1`` encaps key too); the wrapper's ``.`1`` stays uncoupled (CG/UG byte-
        # identical), since only its slice-typed ``.`2`` is coupled below.
        genuine_kp: set[str] = set()
        for fld in red.fields:
            v = _deref(fld.name)
            if (
                isinstance(v, frog_ast.ArrayAccess)
                and isinstance(v.the_array, frog_ast.Variable)
                and isinstance(v.index, frog_ast.Integer)
                and v.index.num == 1
                and (sl := _kp_slice(v.the_array.name)) is not None
                and fld_ty.get(fld.name) != _slice_result_ty(sl)
            ):
                genuine_kp.add(v.the_array.name)

        for fld in red.fields:
            v = _deref(fld.name)
            if v is None:
                continue
            efld = mt._ec_field_name(fld.name)
            # (b) direct functionalized call ``<M>.<m>(<slice of y_i>)``.
            if (
                isinstance(v, frog_ast.FuncCall)
                and isinstance(v.func, frog_ast.FieldAccess)
                and isinstance(v.func.the_object, frog_ast.Variable)
                and len(v.args) == 1
                and (sl := _slice_of_hash(v.args[0])) is not None
            ):
                conj.append(
                    f"{red_base}.{efld}{{{red_side}}} = "
                    f"{v.func.the_object.name}_c.ev_{v.func.name.lower()} "
                    f"({_render_slice(sl)})"
                )
                continue
            if not (
                isinstance(v, frog_ast.ArrayAccess)
                and isinstance(v.the_array, frog_ast.Variable)
                and isinstance(v.index, frog_ast.Integer)
                and (tup := val.get(v.the_array.name)) is not None
                and isinstance(tup, frog_ast.FuncCall)
                and isinstance(tup.func, frog_ast.FieldAccess)
                and isinstance(tup.func.the_object, frog_ast.Variable)
                and (sl := _kp_slice(v.the_array.name)) is not None
            ):
                continue
            mod = tup.func.the_object.name
            if v.index.num == 1 and fld_ty.get(fld.name) == _slice_result_ty(sl):
                # (a) wrapper-passthrough ``_tup[1]`` IS the seed -> the slice itself.
                conj.append(f"{red_base}.{efld}{{{red_side}}} = {_render_slice(sl)}")
            elif v.the_array.name in genuine_kp and v.index.num in (0, 1):
                # (c) genuine (RAW-KEM, e.g. two-KEM ``KEM_T``) keypair projection:
                # ``.`1`` (stored encaps key read by the KDF) or ``.`2`` (decaps key).
                conj.append(
                    f"{red_base}.{efld}{{{red_side}}} = "
                    f"({mod}_c.ev_derivekeypair ({_render_slice(sl)}))"
                    f".`{v.index.num + 1}"
                )
        # Game-side ek-DERIVATION invariant (two-keypair PK binding): the
        # reduction ENCODES its stored encaps-key components while the game
        # RE-DERIVES them in-challenge from ``RO[dk_i]``, so ``={res}`` needs
        # the game's own ``(ek_i, dk_i) = DeriveKeyPair_ev(RO[dk_i])`` linking
        # its STORED ``ek_i`` to the derived form -- without it the challenge
        # residual compares ``ev_encode <stored>`` against ``ev_encode
        # <derived>`` and is unprovable. Read off the theorem scheme's own
        # ``derivekeypair`` (:func:`_lazyro_preprocess_derivekeypair`), seeded
        # with ``RO[game dk_i]``; pairs come from the game's own ``[ek, dk] =
        # KeyGen()`` destructures, so keypair order is the game's own. Gated on
        # >= 2 pairs (the two-keypair wall class), so every single-keypair
        # lazy-RO proof stays byte-identical. Established at the pr-init like
        # every other conjunct here (EC-GATED: wrong text -> reject). Validated
        # on ``tests/integration/ec_templates/two_keypair_lazyro_challenge.ec``.
        ek_pairs = _game_keygen_field_pairs(
            outer_gf.games[0] if outer_gf is not None and outer_gf.games else None
        )
        if len(ek_pairs) >= 2:
            dkp = (
                next((p for p in ec_scheme.procs if p.name == "derivekeypair"), None)
                if ec_scheme is not None
                else None
            )
            pre_proc = (
                _lazyro_preprocess_derivekeypair(dkp) if dkp is not None else None
            )
            ek_conj: list[str] = []
            if pre_proc is not None:
                for ek_f, dk_f in ek_pairs:
                    seed_ref = (
                        f"{game_holder}.{mt._ec_field_name(dk_f)}"  # pylint: disable=protected-access
                        f"{{{game_side}}}"
                    )
                    ev = bch.keygen_derived_ev(
                        pre_proc, seed_ref, clone_alias_by_module
                    )
                    if ev is None:
                        ek_conj = []
                        break
                    ev = ev.replace("__ROH__", f"{ro_ref}{{{game_side}}}")
                    ek_ref = (
                        f"{game_holder}.{mt._ec_field_name(ek_f)}"  # pylint: disable=protected-access
                        f"{{{game_side}}}"
                    )
                    ek_conj.append(f"({ek_ref}, {seed_ref}) = {ev}")
            conj.extend(ek_conj)
        # pylint: enable=protected-access
        return " /\\ ".join(conj)

    def _lazyro_two_keypair_init_tac(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
        lazy_hop: tuple[str, str, str, str, str],
        red_step: frog_ast.Step,
        game_step: frog_ast.Step,
        chal_init: frog_ast.Method,
        dfun_ll: str,
    ) -> list[str] | None:
        """The COMPLETE init-tail tactic for a TWO-KEYPAIR lazy-RO Honest
        pr-lemma (PK / two-keypair DIFFKEY hop_0/12), or ``None`` off-shape.

        The game INTERLEAVES per-keypair derivations while the reduction
        BATCHES per-op; every derivation call is an abstract module call, so
        EC ``swap`` cannot reorder them and the ordered ``call (_: true)``
        peel mispairs ("NG.randomscalar and NG.exp should be equal"). Route
        (validated on BOTH compilers,
        ``ec_templates/two_keypair_lazyro_pr_init.ec``): hoist the game's
        buried second keygen seed to the front (all-``@ 0`` sample hoists --
        legal: hop_0's seeds are INDEPENDENT draws, no exclusion; portable:
        numeric ``@ 0`` means top on both ECs); sink the reduction's dead
        shared-RO sample; ``seq (n+1) (n+1)`` couples [RO~hh, seed_i~s_i]
        positionally; drop the dead RO (``rnd{rs}`` + losslessness); then
        ``exists*``-freeze the POST-SAMPLE memory -- which dissolves the old
        "freeze binds initial memory" obstruction -- and peel every
        deterministic call ONE-SIDEDLY (order-independent), closing with the
        bounded ladder ``24db0e2`` validated at 44 levels.

        Peel sources: game side = the theorem scheme's ``derivekeypair``
        preprocessed for the ROM instantiation
        (:func:`_lazyro_preprocess_derivekeypair`), run once per keypair with
        the seed bound to its frozen name; reduction side = the RENDERED
        reduction module's ``initialize`` with challenger calls rewritten to
        frozen-name assigns and wrapper callees inlined one level. Both give
        ordered call lists via ``bch.model_from_proc``. Gated on the
        challenger returning >= 2 seeds, so single-keypair proofs keep the
        existing branches byte-identically."""
        game_side, red_side_l, chal_base, chal_field, ro_ref = lazy_hop
        rret = _return_elems(chal_init)
        if rret is None or len(rret) < 2:
            return None
        if not all(isinstance(v, frog_ast.Variable) for v in rret):
            return None
        n_kp = len(rret)
        assert red_step.reduction is not None
        # -- the game's keygen-seed inline names: the scheme keygen's sampled
        # seed, first inline instance bare, later instances dedup-suffixed
        # ``<name><k-1>`` (EC inline convention, confirmed on the real goal).
        scheme_name = pt.module_base_name(
            pt.last_module_arg(resolver.resolve(game_step).module_expr)
        )
        scheme_def = schemes_by_name.get(scheme_name)
        if scheme_def is None:
            return None
        keygen = next(
            (m for m in scheme_def.methods if m.signature.name.lower() == "keygen"),
            None,
        )
        if keygen is None:
            return None
        gseed_base = next(
            (
                s.var.name
                for s in keygen.block.statements
                if isinstance(s, frog_ast.Sample)
                and isinstance(s.var, frog_ast.Variable)
            ),
            None,
        )
        if gseed_base is None:
            return None
        gseeds = [gseed_base if i == 0 else f"{gseed_base}{i - 1}" for i in range(n_kp)]
        rseeds = [cast(frog_ast.Variable, v).name for v in rret]
        # -- game-side peel model: the preprocessed scheme derivekeypair, one
        # run per keypair with the seed bound to its frozen elim name.
        dkp = (
            next((pr for pr in ec_scheme.procs if pr.name == "derivekeypair"), None)
            if ec_scheme is not None
            else None
        )
        pre_dkp = _lazyro_preprocess_derivekeypair(dkp) if dkp is not None else None
        if pre_dkp is None or len(pre_dkp.params) != 1:
            return None
        gmodels = []
        for i in range(n_kp):
            m = bch.model_from_proc(
                pre_dkp,
                {pre_dkp.params[0].name: f"gsd{i}"},
                clone_alias_by_module,
            )
            if m is None:
                return None
            gmodels.append(m)
        # -- reduction-side peel model: the rendered reduction module's init,
        # challenger calls rewritten to frozen-name assigns, wrapper callees
        # inlined one level.
        red_name = red_step.reduction.name
        red_mod = next(
            (
                d
                for d in ec_reductions
                if isinstance(d, ec_ast.Module) and d.name == red_name
            ),
            None,
        )
        if red_mod is None:
            return None
        red_proc = next((pr for pr in red_mod.procs if pr.name == "initialize"), None)
        if red_proc is None:
            return None
        chal_param = red_mod.params[-1].name if red_mod.params else None

        def _rn_tok(s: str, mapping: dict[str, str]) -> str:
            for k in sorted(mapping, key=len, reverse=True):
                s = re.sub(rf"\b{re.escape(k)}\b", mapping[k], s)
            return s

        rbody: list[ec_ast.EcStmt] = []
        fresh = 0
        for stmt in red_proc.body:
            if isinstance(stmt, (ec_ast.Sample, ec_ast.If)):
                return None
            if not isinstance(stmt, ec_ast.Call):
                rbody.append(stmt)
                continue
            mod, dot, meth = stmt.callee.partition(".")
            if not dot:
                return None
            if mod == chal_param:
                if meth == "initialize":
                    tup = ", ".join(f"rsd{i}" for i in range(n_kp))
                    rbody.append(ec_ast.Assign(stmt.var, f"({tup})"))
                    continue
                if meth == "hash":
                    rbody.append(ec_ast.Assign(stmt.var, f"(hoh {stmt.args.strip()})"))
                    continue
                return None
            wrapper = foreign_concrete_modules.get(mod)
            if wrapper is None:
                rbody.append(stmt)
                continue
            wproc = next((pr for pr in wrapper.procs if pr.name == meth), None)
            wlet = next((l for l in proof.lets if l.name == mod), None)
            if (
                wproc is None
                or len(wproc.params) != 1
                or wlet is None
                or not isinstance(wlet.value, frog_ast.FuncCall)
            ):
                return None
            wargs = [
                a.name for a in wlet.value.args if isinstance(a, frog_ast.Variable)
            ]
            if len(wargs) != len(wrapper.params):
                return None
            sub: dict[str, str] = dict(zip((pp.name for pp in wrapper.params), wargs))
            sub[wproc.params[0].name] = stmt.args.strip()
            pfx = f"_tw{fresh}_"
            fresh += 1
            ret_expr: str | None = None
            for ws in wproc.body:
                if isinstance(ws, ec_ast.VarDecl):
                    continue
                if isinstance(ws, ec_ast.Return):
                    ret_expr = _rn_tok(ws.expr, sub)
                    break
                if isinstance(ws, ec_ast.Assign):
                    rhs = _rn_tok(ws.rhs, sub)
                    sub[ws.var] = pfx + ws.var
                    rbody.append(ec_ast.Assign(pfx + ws.var, rhs))
                elif isinstance(ws, ec_ast.Call):
                    wm, wd, wmeth = ws.callee.partition(".")
                    if not wd:
                        return None
                    args = _rn_tok(ws.args, sub)
                    callee_mod = sub.get(wm, wm)
                    sub[ws.var] = pfx + ws.var
                    rbody.append(
                        ec_ast.Call(pfx + ws.var, f"{callee_mod}.{wmeth}", args)
                    )
                else:
                    return None
            if ret_expr is None:
                return None
            rbody.append(ec_ast.Assign(stmt.var, ret_expr))
        rmodel = bch.model_from_proc(
            ec_ast.Proc(
                "initialize", [], red_proc.return_type, rbody + [ec_ast.Return("tt")]
            ),
            {},
            clone_alias_by_module,
        )
        if rmodel is None or not rmodel.calls:
            return None
        # -- freeze list + elim names (post-sample memory, both sides)
        g_mods: list[str] = []
        for m in gmodels:
            for gm in m.glob_modules:
                if gm not in g_mods:
                    g_mods.append(gm)
        r_mods = list(rmodel.glob_modules)
        honest_ref = f"{chal_base}.{chal_field}"
        exs = (
            [f"(glob {m}){{{game_side}}}" for m in g_mods]
            + [f"{ro_ref}{{{game_side}}}"]
            + [f"{gs}{{{game_side}}}" for gs in gseeds]
            + [f"(glob {m}){{{red_side_l}}}" for m in r_mods]
            + [f"{honest_ref}{{{red_side_l}}}"]
            + [f"{rs}{{{red_side_l}}}" for rs in rseeds]
        )
        g_glob_elim = {m: f"zgg{i}" for i, m in enumerate(g_mods)}
        r_glob_elim = {m: f"zgr{i}" for i, m in enumerate(r_mods)}
        elims = (
            [g_glob_elim[m] for m in g_mods]
            + ["roh"]
            + [f"gsd{i}" for i in range(n_kp)]
            + [r_glob_elim[m] for m in r_mods]
            + ["hoh"]
            + [f"rsd{i}" for i in range(n_kp)]
        )

        def _peel(calls: list[Any], side: str, glob_elim: dict[str, str]) -> list[str]:
            lines: list[str] = []
            for c in reversed(calls):
                args = "".join(f" {cc_paren(a)}" for a in c.arg_values)
                lines.append(
                    f"call{{{side}}} ({c.module}_{c.method}_det "
                    f"{glob_elim[c.module]}{args})."
                )
                lines.append("wp.")
            return lines

        gpeel: list[str] = []
        for m in reversed(gmodels):
            gpeel += _peel(m.calls, game_side, g_glob_elim)
        rpeel = _peel(rmodel.calls, red_side_l, r_glob_elim)
        n_levels = sum(len(m.calls) for m in gmodels) + len(rmodel.calls)
        gpeel = [ln.replace("__ROH__", "roh") for ln in gpeel]
        rpeel = [ln.replace("__ROH__", "roh") for ln in rpeel]
        # -- the seq coupling invariant: globs + RO couple + seed couples ONLY
        # (field couplings are NOT provable at sample time; they are
        # established by the final wp/ladder from the derivations).
        seed_conj = " /\\ ".join(
            f"{g}{{{game_side}}} = {r}{{{red_side_l}}}" for g, r in zip(gseeds, rseeds)
        )
        # ``={glob <RO holder>}`` is UNPROVABLE at the seq point: the game
        # side's RO was just sampled while the reduction side's copy is the
        # DEAD sample still below the boundary (probe evidence: the prefix
        # bullet leaves ``hL = RO_G_RO.h{2}``). Strip it -- the same reason
        # ``_live_state_coupling`` strips it from lazyro-hop couplings; the
        # cross-side ``RO{gs} = Honest.h{rs}`` conjunct is the real coupling.
        inv_globs = glob_invariant_conj
        for _ro_m in ro_holder_modules:
            inv_globs = inv_globs.replace(f" /\\ ={{glob {_ro_m}}}", "").replace(
                f"={{glob {_ro_m}}} /\\ ", ""
            )
        inv = (
            "={glob A}"
            + (f" /\\ {inv_globs}" if inv_globs else "")
            + f" /\\ {ro_ref}{{{game_side}}} = {honest_ref}{{{red_side_l}}}"
            + f" /\\ {seed_conj}"
        )
        n_samp = n_kp + 1
        dead_seq = "0 1" if red_side_l == "2" else "1 0"
        ladder = (
            "(   (split; [ by smt() | move => ? ? ? [-> ->] ])"
            " || (split; [ by smt() | move => ? ? ? [-> ?] ])"
            " || (split; [ by smt() | move => ? ? ? [? ->] ])"
            " || (split; [ by smt() | move => ? ? ? [? ?] ])"
            " || (move => ? ? [-> ->])"
            " || (move => ? ? [-> ?])"
            " || (move => ? ? [? ->])"
            " || (move => ? ? [? ?]))"
        )
        return [
            *([f"swap{{{game_side}}} ^ <${{{n_samp}}} @ 0."] * n_samp),
            f"swap{{{red_side_l}}} 1 {n_samp}.",
            f"seq {n_samp} {n_samp} : ({inv}).",
            "+ " + "rnd; " * n_samp + "skip => />.",
            f"seq {dead_seq} : ({inv}).",
            f"+ rnd{{{red_side_l}}}; auto => />; smt({dfun_ll}).",
            f"exists* {', '.join(exs)};",
            f"elim* => {' '.join(elims)}.",
            "wp.",
            *gpeel,
            *rpeel,
            "skip; move => &1 &2 H.",
            f"do {n_levels}! (simplify; {ladder}).",
            "simplify.",
            "smt().",
        ]

    def _reprogram_equiv_emit(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
        mat_side: str,
        kg_side: str,
        mat_ref: str,
        kg_red_ref: str,
        mat_init: ec_ast.Proc,
        kg_init: ec_ast.Proc,
        seed_flds: list[str],
        y_pairs: list[tuple[str, str]],
        concat_op: str,
        chal_locals: list[str],
        lams: tuple[str, str],
        t_seeds: list[str],
    ) -> list[str] | None:
        """Emit the validated reprogram-equiv init tactic (see
        :func:`_reprogram_equiv_init_tac`) from the derived datums."""
        n_kp = len(seed_flds)
        lam0, lam1 = lams
        # -- hash sites + peel model from the RENDERED mat reduction init ----
        chal_param = None
        var_pos: dict[str, int] = {}
        site_idx: list[int] = []
        rbody: list[ec_ast.EcStmt] = []
        hash_of: dict[str, int] = {}
        for st in mat_init.body:
            if isinstance(st, (ec_ast.Sample, ec_ast.If)):
                return None
            if isinstance(st, ec_ast.Assign):
                m = re.match(r"^(\w+)\.`(\d+)$", st.rhs.strip())
                if m is not None and m.group(1) in hash_of and hash_of[m.group(1)] < 0:
                    # seed destructure off the challenger-init tuple
                    var_pos[st.var] = int(m.group(2)) - 1
                rbody.append(st)
                continue
            if not isinstance(st, ec_ast.Call):
                rbody.append(st)
                continue
            mod, dot, meth = st.callee.partition(".")
            if not dot:
                return None
            if chal_param is None and meth in ("initialize", "hash"):
                chal_param = mod
            if mod == chal_param:
                if meth == "initialize":
                    hash_of[st.var] = -1  # marks the seed tuple
                    rbody.append(ec_ast.Assign(st.var, "(__SEEDS__)"))
                    continue
                if meth == "hash":
                    k = var_pos.get(st.args.strip())
                    if k is None or not 0 <= k < n_kp:
                        return None
                    site_idx.append(k)
                    rbody.append(ec_ast.Assign(st.var, f"({concat_op} zy{k}p zy{k}t)"))
                    continue
                return None
            wrapper = foreign_concrete_modules.get(mod)
            if wrapper is None:
                rbody.append(st)
                continue
            wproc = next((pr for pr in wrapper.procs if pr.name == meth), None)
            wlet = next((l for l in proof.lets if l.name == mod), None)
            if (
                wproc is None
                or len(wproc.params) != 1
                or wlet is None
                or not isinstance(wlet.value, frog_ast.FuncCall)
            ):
                return None
            wargs = [
                a.name for a in wlet.value.args if isinstance(a, frog_ast.Variable)
            ]
            if len(wargs) != len(wrapper.params):
                return None
            sub: dict[str, str] = dict(zip((pp.name for pp in wrapper.params), wargs))
            sub[wproc.params[0].name] = st.args.strip()

            def _rn_tok(s: str, mapping: dict[str, str]) -> str:
                for kk in sorted(mapping, key=len, reverse=True):
                    s = re.sub(rf"\b{re.escape(kk)}\b", mapping[kk], s)
                return s

            pfx = f"_rw{len(rbody)}_"
            ret_expr: str | None = None
            for ws in wproc.body:
                if isinstance(ws, ec_ast.VarDecl):
                    continue
                if isinstance(ws, ec_ast.Return):
                    ret_expr = _rn_tok(ws.expr, sub)
                    break
                if isinstance(ws, ec_ast.Assign):
                    rhs = _rn_tok(ws.rhs, sub)
                    sub[ws.var] = pfx + ws.var
                    rbody.append(ec_ast.Assign(pfx + ws.var, rhs))
                elif isinstance(ws, ec_ast.Call):
                    wm, wd, wmeth = ws.callee.partition(".")
                    if not wd:
                        return None
                    args = _rn_tok(ws.args, sub)
                    callee_mod = sub.get(wm, wm)
                    sub[ws.var] = pfx + ws.var
                    rbody.append(
                        ec_ast.Call(pfx + ws.var, f"{callee_mod}.{wmeth}", args)
                    )
                else:
                    return None
            if ret_expr is None:
                return None
            rbody.append(ec_ast.Assign(st.var, ret_expr))
        if len(site_idx) != 2 * n_kp or chal_param is None:
            return None
        mmodel = bch.model_from_proc(
            ec_ast.Proc("initialize", [], mat_init.return_type, rbody),
            {},
            clone_alias_by_module,
        )
        if mmodel is None or len(mmodel.calls) != 2 * n_kp:
            return None
        # KG-side calls: the challenger's per-keypair wrapper keygens expose the
        # inner PQ derivekeypair at the frozen chal-local seeds; the reduction's
        # own T derivekeypairs at the frozen t-seed fields. Read the T callee
        # off the rendered kg init; the inner PQ module off the mat model.
        t_callee = next(
            (
                st.callee
                for st in kg_init.body
                if isinstance(st, ec_ast.Call) and st.callee.endswith(".derivekeypair")
            ),
            None,
        )
        pq_callee = next(
            (
                f"{c.module}.{c.method}"
                for c in mmodel.calls
                if c.method == "derivekeypair"
                and t_callee is not None
                and c.module != t_callee.split(".", 1)[0]
            ),
            None,
        )
        if t_callee is None or pq_callee is None:
            return None
        t_mod = t_callee.split(".", 1)[0]
        pq_mod = pq_callee.split(".", 1)[0]
        # a GROUP-T proof has no T derivekeypair (the CG shape closes via the
        # existing reprogram route): require BOTH modules distinct
        if t_mod == pq_mod:
            return None
        # -- rcond selectors --------------------------------------------------
        tac: list[str] = ["inline *."]
        first = True
        for k in site_idx:
            for sel in ["rcondf"] * k + ["rcondt"]:
                tac.append(f"{sel}{{{mat_side}}} ^if.")
                if first:
                    tac.append("+ auto.")
                    first = False
                elif sel == "rcondf":
                    tac.append(
                        "+ auto; do? (call (_: true); auto); smt(supp_dexcepted)."
                    )
                else:
                    tac.append("+ auto; do? (call (_: true); auto).")
        # -- sample hoists (KG side) -----------------------------------------
        # EC order: challenger-inline locals first, then the reduction's own;
        # target = the Mat sample order [lam0, lam1, (chal_k, t_k)*].
        cur = chal_locals + [lam0, lam1] + t_seeds
        target = [lam0, lam1] + [
            v for k in range(n_kp) for v in (chal_locals[k], t_seeds[k])
        ]
        order = [cur.index(v) for v in target]
        pos = list(range(len(cur)))

        def _hoist(orig: int, dest: int) -> str | None:
            occ = pos.index(orig)
            if occ == dest:
                return None
            pos.insert(dest, pos.pop(occ))
            at = "^ <${2}" if dest == 1 else "0"
            return f"swap{{{kg_side}}} ^ <${{{occ + 1}}} @ {at}."

        lam1_orig = cur.index(lam1)
        placed: set[int] = set()
        for p in reversed(range(len(order))):
            if p in placed:
                continue
            want = order[p]
            if want == lam1_orig:
                if p == 0 or order[p - 1] != cur.index(lam0):
                    return None
                for sw in (_hoist(order[p - 1], 0), _hoist(want, 1)):
                    if sw is not None:
                        tac.append(sw)
                placed.add(p - 1)
            else:
                sw = _hoist(want, 0)
                if sw is not None:
                    tac.append(sw)
        # -- seq + invariant --------------------------------------------------
        n_s = 2 + 2 * n_kp
        seq_counts = f"{n_s + 1} {n_s}" if mat_side == "1" else f"{n_s} {n_s + 1}"
        ro_ref = next(iter(top_types.ro_by_arrow_type().values()), None)
        if ro_ref is None:
            return None
        ro_holder = ro_ref.rsplit(".", 1)[0]
        globs = " /\\ ".join(
            [f"={{glob {m}}}" for m in declared_module_names]
            + [f"={{glob {ro_holder}}}"]
        )
        pair_map = (
            list(zip([lam0, lam1], seed_flds))
            + [(chal_locals[k], y_pairs[k][0]) for k in range(n_kp)]
            + [(t_seeds[k], y_pairs[k][1]) for k in range(n_kp)]
        )
        kg_field_names = {s.var for s in kg_init.body if isinstance(s, ec_ast.Sample)}

        def _kg_ref(v: str) -> str:
            return f"{kg_red_ref}.{v}" if v in kg_field_names else v

        couples = " /\\ ".join(
            f"{mat_ref}.{mf}{{{mat_side}}} = {_kg_ref(kv)}{{{kg_side}}}"
            for kv, mf in pair_map
        )
        inv = (
            f"{globs}"
            f" /\\ {mat_ref}.h{{{mat_side}}} = {ro_ref}{{{mat_side}}}"
            f" /\\ {couples}"
            f" /\\ {mat_ref}.{seed_flds[0]}{{{mat_side}}} <> "
            f"{mat_ref}.{seed_flds[1]}{{{mat_side}}}"
        )
        tac.append(f"seq {seq_counts} : ({inv}).")
        tac.append("+ " + "rnd. " * n_s + "auto => />; smt(supp_dexcepted).")
        # -- freeze + one-sided det peels -------------------------------------
        y_flat = [y for pr_ in y_pairs for y in pr_]
        exs = (
            [f"(glob {pq_mod}){{{mat_side}}}", f"(glob {t_mod}){{{mat_side}}}"]
            + [f"(glob {pq_mod}){{{kg_side}}}", f"(glob {t_mod}){{{kg_side}}}"]
            + [f"{mat_ref}.{y}{{{mat_side}}}" for y in y_flat]
            + [f"{c}{{{kg_side}}}" for c in chal_locals]
            + [f"{kg_red_ref}.{ts}{{{kg_side}}}" for ts in t_seeds]
        )
        y_elims = [e for k in range(n_kp) for e in (f"zy{k}p", f"zy{k}t")]
        elims = (
            ["gpqm", "gtm", "gpqo", "gto"]
            + y_elims
            + [f"zs{k}" for k in range(n_kp)]
            + [f"zt{k}" for k in range(n_kp)]
        )
        tac.append(f"exists* {', '.join(exs)};")
        tac.append(f"elim* => {' '.join(elims)}.")
        tac.append("wp.")
        glob_elim = {pq_mod: "gpqm", t_mod: "gtm"}
        for c in reversed(mmodel.calls):
            args = "".join(f" {cc_paren(a)}" for a in c.arg_values)
            tac.append(
                f"call{{{mat_side}}} ({c.module}_{c.method}_det "
                f"{glob_elim[c.module]}{args})."
            )
            tac.append("wp.")
        for k in reversed(range(n_kp)):
            tac.append(f"call{{{kg_side}}} ({t_mod}_derivekeypair_det gto zt{k}).")
            tac.append("wp.")
        for k in reversed(range(n_kp)):
            tac.append(f"call{{{kg_side}}} ({pq_mod}_derivekeypair_det gpqo zs{k}).")
            tac.append("wp.")
        n_lv = 4 * n_kp
        mid = concat_op[len("concat_") : concat_op.index("_to_")]
        zed = concat_op[concat_op.index("_to_") + len("_to_") :]
        ladder = (
            "(   (split; [ by smt() | move => ? ? ? [-> ->] ])"
            " || (split; [ by smt() | move => ? ? ? [-> ?] ])"
            " || (split; [ by smt() | move => ? ? ? [? ->] ])"
            " || (split; [ by smt() | move => ? ? ? [? ?] ])"
            " || (move => ? ? [-> ->])"
            " || (move => ? ? [-> ?])"
            " || (move => ? ? [? ->])"
            " || (move => ? ? [? ?]))"
        )
        tac += [
            "skip; move => &1 &2 H.",
            f"do {n_lv}! (simplify; {ladder}).",
            "simplify.",
            f"smt(slice_concat_left_{mid}_{zed} slice_concat_right_{mid}_{zed}).",
        ]
        return tac

    def _reprogram_equiv_init_tac(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
        step_a: frog_ast.Step,
        step_b: frog_ast.Step,
    ) -> list[str] | None:
        """The COMPLETE init tactic for the TWO-KEM reprogram-equiv hop
        (CK-class hop_2/hop_10: ``R_LazyRO ~ R_KG``), or ``None`` off-shape.

        The Mat side reprograms the RO inside always-decidable ``if`` chains and
        interleaves per-keypair PQ/T derivations; the KeyGen side batches
        per-module -- the call orders differ ([PQ,T,PQ,T] vs [PQ,PQ,T,T]) so no
        two-sided peel aligns, and the flat-state view's if-count/positions
        diverge from the EC ``inline *`` body (measured: 9 vs 6 decidable ifs).
        This builder works off the RENDERED modules only. Validated by hand on
        both toolchains (CK_DK3.ec / CK_PK2.ec, 2026-07-30): exact rcond
        selectors ([f]*i_k + [t] per hash site, seed indices from the rendered
        destructure), anchored sample hoists, positional ``seq`` coupling +
        the exclusion disequality, exists* freeze, 8 ONE-SIDED det peels (the
        order mismatch dissolves), bounded ladder + slice_concat smt."""
        if step_a.reduction is None or step_b.reduction is None:
            return None
        sides = []
        for st, side in ((step_a, "1"), (step_b, "2")):
            base = pt.module_base_name(
                pt.last_module_arg(resolver.resolve(st).module_expr)
            )
            sides.append((st, side, base))
        mats = [s for s in sides if s[2].endswith("_Mat")]
        if len(mats) != 1:
            return None
        mat_step, mat_side, mat_name = mats[0]
        kg_step, kg_side, _ = next(s for s in sides if s[2] != mat_name)

        # -- rendered reduction inits ---------------------------------------
        def _red_init(st: frog_ast.Step) -> ec_ast.Proc | None:
            assert st.reduction is not None
            mod = next(
                (
                    d
                    for d in ec_reductions
                    if isinstance(d, ec_ast.Module) and d.name == st.reduction.name
                ),
                None,
            )
            if mod is None:
                return None
            return next((pr for pr in mod.procs if pr.name == "initialize"), None)

        mat_init = _red_init(mat_step)
        kg_init = _red_init(kg_step)
        if mat_init is None or kg_init is None:
            return None
        # -- the rendered Mat module: reprogram field names + concat op -----
        mat_mod = next(
            (
                d
                for d in mat_challenger_decls
                if isinstance(d, ec_ast.Module) and d.name == mat_name
            ),
            None,
        )
        if mat_mod is None:
            return None
        hash_proc = next((pr for pr in mat_mod.procs if pr.name == "hash"), None)
        init_proc = next((pr for pr in mat_mod.procs if pr.name == "initialize"), None)
        if hash_proc is None or init_proc is None:
            return None
        # per-keypair reprogram branches: guard fields (seed order) + concat args
        seed_flds: list[str] = []
        y_pairs: list[tuple[str, str]] = []
        concat_op: str | None = None

        def _walk_hash(stmts: list[ec_ast.EcStmt]) -> None:
            nonlocal concat_op
            for s in stmts:
                if not isinstance(s, ec_ast.If):
                    continue
                mg = re.match(r"^\s*\S+\s*=\s*(\S+)\s*$", s.guard)
                then_assign = next(
                    (
                        a
                        for a in s.then_body
                        if isinstance(a, ec_ast.Assign)
                        and a.rhs.strip().startswith("concat_")
                    ),
                    None,
                )
                if mg is not None and then_assign is not None:
                    toks = then_assign.rhs.strip().split()
                    if len(toks) == 3:
                        concat_op = toks[0]
                        seed_flds.append(mg.group(1))
                        y_pairs.append((toks[1], toks[2]))
                _walk_hash(s.else_body or [])

        _walk_hash(hash_proc.body)
        n_kp = len(seed_flds)
        if n_kp < 2 or concat_op is None or len(y_pairs) != n_kp:
            return None
        # Mat's rendered init: the RO-materialization assign + the real samples
        mat_samps = [s.var for s in init_proc.body if isinstance(s, ec_ast.Sample)]
        mat_assigns = sum(1 for s in init_proc.body if isinstance(s, ec_ast.Assign))
        n_samp = len(mat_samps)
        if n_samp != 2 + 2 * n_kp or mat_assigns < 1:
            return None
        # field name -> its position among the Mat samples; require the guard
        # seeds and concat y's to BE the sampled fields
        if set(seed_flds + [y for p in y_pairs for y in p]) != set(mat_samps):
            return None
        mat_ref = mat_name
        # -- the KG side: challenger-inline sample locals + own samples -----
        kg_chal = engine._get_game_ast(  # pylint: disable=protected-access
            kg_step.challenger, None
        )
        if kg_chal is None:
            return None
        chal_svars: list[str] = []
        for m in kg_chal.methods:
            for s in m.block.statements:
                if isinstance(s, (frog_ast.Sample, frog_ast.UniqueSample)) and (
                    isinstance(s.var, frog_ast.Variable)
                ):
                    chal_svars.append(s.var.name)
        if len(set(chal_svars)) != 1:
            return None
        cbase = chal_svars[0]
        chal_locals = [cbase if i == 0 else f"{cbase}{i - 1}" for i in range(n_kp)]
        kg_samp_stmts = [s for s in kg_init.body if isinstance(s, ec_ast.Sample)]
        if len(kg_samp_stmts) != 2 + n_kp:
            return None
        # the exclusion pair: the sample whose distr names another sample var
        kg_svars = [s.var for s in kg_samp_stmts]
        excl = next(
            (
                (i, s)
                for i, s in enumerate(kg_samp_stmts)
                if any(
                    re.search(rf"\b{re.escape(v)}\b", s.distr)
                    for v in kg_svars
                    if v != s.var
                )
            ),
            None,
        )
        if excl is None or excl[0] < 1:
            return None
        lam1_i = excl[0]
        lam0 = next(
            v
            for v in kg_svars
            if v != kg_samp_stmts[lam1_i].var
            and re.search(rf"\b{re.escape(v)}\b", kg_samp_stmts[lam1_i].distr)
        )
        lam1 = kg_samp_stmts[lam1_i].var
        t_seeds = [v for v in kg_svars if v not in (lam0, lam1)]
        if len(t_seeds) != n_kp or kg_step.reduction is None:
            return None
        kg_red_ref = kg_step.reduction.name
        return _reprogram_equiv_emit(
            mat_side,
            kg_side,
            mat_ref,
            kg_red_ref,
            mat_init,
            kg_init,
            seed_flds,
            y_pairs,
            concat_op,
            chal_locals,
            (lam0, lam1),
            t_seeds,
        )

    def _lazyro_derived_init_fields(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        step_a: frog_ast.Step,
        step_b: frog_ast.Step,
        lazy_hop: tuple[str, str, str, str, str],
        red: frog_ast.Reduction | None,
        red_init: frog_ast.Method,
        chal_init: frog_ast.Method,
    ) -> dict[str, Any]:
        """Fields for :class:`pt.LazyroInitSpec`'s DERIVED-coupling init tactic, or
        ``{}`` (=> the OLD tactic runs, byte-identical). Mirrors
        :func:`_lazyro_derived_key_coupling`'s translator setup. Extracts: the
        game's keygen seed sample name + the challenger's returned seed sample name
        (for the ``<gseed>{gs}=<rseed>{rs}`` seq-2-2 coupling); the ``randomscalar``
        slice args RO-substituted per side (game reads ``RO[gseed]``, reduction
        ``Honest.h[rseed]``); the NG determinism lemma; and randomscalar's position
        among the abstract calls (peel counts). Any extraction miss returns ``{}``
        so the hop keeps the old (RO-only-coupling) init."""
        game_side, red_side_l, chal_base, chal_field, ro_ref = lazy_hop
        honest_ref = f"{chal_base}.{chal_field}"
        rret = _return_elems(chal_init)
        if red is None or not rret or not isinstance(rret[0], frog_ast.Variable):
            return {}
        rseed = rret[0].name
        # gseed: the game's scheme keygen samples the decaps-key seed. The EC
        # scheme module uses SOURCE var names (as ``rseed`` does via chal_init), NOT
        # the engine-canonicalized ``v1`` names -- so read the SOURCE scheme keygen,
        # not the canonicalized game init.
        game_step = step_b if step_a.reduction is not None else step_a
        scheme_name = pt.module_base_name(
            pt.last_module_arg(resolver.resolve(game_step).module_expr)
        )
        scheme_def = schemes_by_name.get(scheme_name)
        if scheme_def is None:
            return {}
        keygen = next(
            (m for m in scheme_def.methods if m.signature.name.lower() == "keygen"),
            None,
        )
        if keygen is None:
            return {}
        # pylint: disable=protected-access
        gseed = next(
            (
                s.var.name
                for s in keygen.block.statements
                if isinstance(s, frog_ast.Sample)
                and isinstance(s.var, frog_ast.Variable)
                and s.the_type is not None
                and isinstance(top_types.resolve(s.the_type), frog_ast.BitStringType)
            ),
            None,
        )
        if gseed is None:
            return {}
        # Which abstract call must be FUNCTIONALIZED: the one whose ``ev_`` form
        # the hop's derived-key coupling names (``NG.RandomScalar`` for the
        # nominal-group combiners, ``KEM_T.DeriveKeyPair`` for the two-KEM ones).
        # Read off the coupling rather than matched by method name, so the route
        # is not tied to one primitive's vocabulary. Its argument is the RO-derived
        # SLICE, which is what makes the two sides' arguments equal.
        derived_coupling = _lazyro_derived_key_coupling(step_a, step_b) or ""
        clone_to_mod = {c: m for m, c in clone_alias_by_module.items()}
        ev_targets = {
            (clone_to_mod.get(cl, cl), meth)
            for cl, meth in re.findall(r"(\w+)\.ev_(\w+)", derived_coupling)
        }
        if not ev_targets:
            return {}
        # CK/UK inline ``challenger.Hash(seed)`` straight into the slice; hoist it
        # into a synthetic local so the slice's array is a Variable the expression
        # translator can render (CG/UG already factor it out -> no-op there).
        red_init = _hoist_inline_challenger_hashes(red_init)

        def _is_target(n: frog_ast.ASTNode) -> bool:
            return (
                isinstance(n, frog_ast.FuncCall)
                and isinstance(n.func, frog_ast.FieldAccess)
                and isinstance(n.func.the_object, frog_ast.Variable)
                and (n.func.the_object.name, n.func.name.lower()) in ev_targets
                and bool(n.args)
                and isinstance(n.args[0], frog_ast.Slice)
            )

        rs_finder: visitors.SearchVisitor[frog_ast.FuncCall] = visitors.SearchVisitor(
            _is_target
        )
        rs_call = rs_finder.visit(red_init.block)
        if (
            rs_call is None
            or not rs_call.args
            or not isinstance(rs_call.args[0], frog_ast.Slice)
            or not isinstance(rs_call.args[0].the_array, frog_ast.Variable)
            or not isinstance(rs_call.func, frog_ast.FieldAccess)
            or not isinstance(rs_call.func.the_object, frog_ast.Variable)
        ):
            return {}
        ng_mod = rs_call.func.the_object.name
        type_map: dict[str, frog_ast.Type] = {f.name: f.type for f in red.fields}
        for stmt in red_init.block.statements:
            mt._seed_type_map(stmt, type_map)
        exprs = expr_translator.ExpressionTranslator(
            top_types, type_of_factory(type_map, {})
        )
        slice_ec = exprs.translate(rs_call.args[0])
        y_ec = exprs.translate(rs_call.args[0].the_array)
        lhs = re.sub(
            rf"\b{re.escape(y_ec)}\b",
            f"({ro_ref}{{{game_side}}} {gseed}{{{game_side}}})",
            slice_ec,
        )
        rhs = re.sub(
            rf"\b{re.escape(y_ec)}\b",
            f"({honest_ref}{{{red_side_l}}} {rseed}{{{red_side_l}}})",
            slice_ec,
        )
        order: list[frog_ast.FuncCall] = []

        def _collect(n: frog_ast.ASTNode) -> bool:
            if (
                isinstance(n, frog_ast.FuncCall)
                and isinstance(n.func, frog_ast.FieldAccess)
                and isinstance(n.func.the_object, frog_ast.Variable)
                and n.func.the_object.name != "challenger"
            ):
                order.append(n)
            return False

        visitors.SearchVisitor(_collect).visit(red_init.block)
        # Locate the target by IDENTITY, not by name: a two-KEM reduction derives
        # BOTH component keypairs with the same method (``DeriveKeyPair``), so a
        # name lookup would pick the wrong occurrence and mis-size the peel.
        idx = next((i for i, c in enumerate(order) if c is rs_call), None)
        if idx is None:
            return {}
        # pylint: enable=protected-access
        full = _live_state_coupling(step_a, step_b)
        derived = derived_coupling or None
        base = full.replace(f" /\\ {derived}", "") if derived else full
        return {
            "game_side": game_side,
            "seq_inv": (
                f"={{glob A}} /\\ {base} /\\ "
                f"{gseed}{{{game_side}}} = {rseed}{{{red_side_l}}}"
            ),
            "rs_lhs_arg": lhs,
            "rs_rhs_arg": rhs,
            "rs_mod": ng_mod,
            "ng_det": f"{ng_mod}_{rs_call.func.name.lower()}_det",
            "n_after_rs": len(order) - idx - 1,
            "n_before_rs": idx,
        }

    hop_live_abstract_memo: dict[tuple[int, int], frozenset[str]] = {}

    def _hop_live_abstract_modules(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> frozenset[str]:
        """Abstract-scheme modules referenced in BOTH of the hop's canonicalized
        flat states.

        Mirrors the field-aware leg coupling's ``li[1] & ri[1]`` intersection
        (:func:`chain_emitter._glob_signature`): a module used by neither state's
        surviving methods is absent from its EC ``(glob)``, so a ``={glob P}``
        coupling conjunct over it cannot be threaded through the per-oracle
        transitivity. Read off the canonicalized ASTs (the same source the
        chain-emission renders), memoized per hop."""
        key = (id(step_a), id(step_b))
        if key in hop_live_abstract_memo:
            return hop_live_abstract_memo[key]
        # pylint: disable=protected-access
        la = engine._get_game_ast(step_a.challenger, step_a.reduction)
        lb = engine._get_game_ast(step_b.challenger, step_b.reduction)
        # pylint: enable=protected-access
        lc, _ = engine.canonicalize_game_with_states(
            copy.deepcopy(la), skip_passes=_EXPORT_SKIP_PASSES
        )
        rc, _ = engine.canonicalize_game_with_states(
            copy.deepcopy(lb), skip_passes=_EXPORT_SKIP_PASSES
        )

        def _refs(game: frog_ast.Game, mod: str) -> bool:
            finder: visitors.SearchVisitor[frog_ast.FieldAccess] = (
                visitors.SearchVisitor(
                    lambda n: isinstance(n, frog_ast.FieldAccess)
                    and isinstance(n.the_object, frog_ast.Variable)
                    and n.the_object.name == mod
                )
            )
            return finder.visit(game) is not None

        live = frozenset(
            m for m in abstract_scheme_modules if _refs(lc, m) and _refs(rc, m)
        )
        hop_live_abstract_memo[key] = live
        return live

    def _reprogram_side(
        step: frog_ast.Step,
    ) -> tuple[str, list[str]] | None:
        """``(module, [guard, concat1, concat2])`` reprogramming-field names for a
        reprogramming-Lazy hop endpoint, or ``None`` off-shape.

        Every seedbased-hybrid reduction/challenger answers ``HashG`` by
        reprogramming the RO at a fresh seed: ``if (x == <seed>) return <a> || <b>;
        return H(x);``. A reduction that reprograms itself (``R_KG_L``,
        ``R_PQ_Bind``, ``R_KDF``) carries that ``if`` in its own ``HashG``; a
        reduction that delegates to the materialized ``_Mat`` Lazy challenger
        (``R_LazyRO_L``) carries it in the challenger game's ``Hash`` (fields
        ``s0``/``y0_pq``/``y0_t``). Both are found by the same shape probe."""

        def _extract_one(
            iff: frog_ast.IfStatement, pname: str | None
        ) -> list[str] | None:
            cond = iff.conditions[0]
            if not isinstance(cond, frog_ast.BinaryOperation):
                return None
            ops = [cond.left_expression, cond.right_expression]
            # A reprogramming guard compares the method's own INPUT against the
            # stored seed (``if (x == s0)``): require exactly one operand to be
            # the parameter, the other is the seed field. Without this, any
            # ``if (a == b) return c || d`` false-positives -- the KDF-collision
            # game's collision test made ``_reprogram_field_coupling`` pair the
            # two challengers' SOURCE fields (``KDFCollisionResistance_
            # Unbreakable.ek0 = KeyGenEquiv_FromKeyGen.ek0``), references the
            # materialized EC modules don't hold ("unknown variable", the CG PK
            # hop_8 wall).
            is_param = [
                isinstance(o, frog_ast.Variable) and o.name == pname for o in ops
            ]
            if pname is None or sum(is_param) != 1:
                return None
            guard = ops[is_param.index(False)]
            ret = iff.blocks[0].statements[0]
            if not isinstance(ret, frog_ast.ReturnStatement) or not isinstance(
                ret.expression, frog_ast.BinaryOperation
            ):
                return None
            left, right = (
                ret.expression.left_expression,
                ret.expression.right_expression,
            )
            if (
                isinstance(guard, frog_ast.Variable)
                and isinstance(left, frog_ast.Variable)
                and isinstance(right, frog_ast.Variable)
            ):
                return [guard.name, left.name, right.name]
            return None

        def _collect(
            stmts: Sequence[frog_ast.Statement],
            pname: str | None,
            collected: list[str],
        ) -> None:
            # ``pname``/``collected`` are passed explicitly rather than captured:
            # ``_extract`` calls this once per method, and a closure over the loop
            # variables would bind late.
            for s in stmts:
                if not isinstance(s, frog_ast.IfStatement):
                    continue
                if _is_reprogram_hash_if(s):
                    fields = _extract_one(s, pname)
                    if fields is not None:
                        collected.extend(fields)
                for blk in s.blocks[1:]:
                    _collect(blk.statements, pname, collected)

        def _extract(methods: list[frog_ast.Method]) -> list[str] | None:
            # Collect EVERY reprogramming ``if`` -- the two-seed challenger/reduction
            # reprograms at BOTH seeds (``if x=s0 return y0_pq||y0_t; if x=s1 return
            # y1_pq||y1_t; return H(x)``), so its ``HashG`` equiv needs the s0- AND
            # s1-field correspondences. A single-seed reduction yields one triple ->
            # byte-identical. Sequential (each returns) or nested (else-branch) ifs
            # are both handled.
            for m in methods:
                params = m.signature.parameters
                pname = params[0].name if params else None
                collected: list[str] = []
                _collect(m.block.statements, pname, collected)
                if collected:
                    return collected
            return None

        # pylint: disable=protected-access
        red = _get_reduction(step.reduction.name) if step.reduction else None
        if red is not None:
            fields = _extract(red.methods)
            if fields is not None:
                return (
                    pt.module_base_name(resolver.resolve(step).module_expr),
                    fields,
                )
        chal_game = engine._get_game_ast(step.challenger, None)
        if chal_game is not None:
            fields = _extract(chal_game.methods)
            if fields is not None:
                chal_base = pt.module_base_name(
                    pt.last_module_arg(resolver.resolve(step).module_expr)
                )
                return (chal_base, fields)
        # pylint: enable=protected-access
        return None

    def _reprogram_field_coupling(step_a: frog_ast.Step, step_b: frog_ast.Step) -> str:
        """Cross-side reprogramming-field coupling for a reprogramming-Lazy hop.

        Both endpoints reprogram the RO at a fresh seed with a KEM/NG seed pair;
        their ``HashG`` returns are provably equal only when the reprogrammed
        fields correspond. The chain's ``initialize`` couples the two reductions'
        stored fields but not the ``_Mat`` challenger's reprogram fields, so the
        ``HashG`` equiv's guard/then-branch is otherwise unprovable. Emit
        ``<A>.<guard>{1}=<B>.<guard>{2} /\\ <A>.<c1>{1}=<B>.<c1>{2} /\\
        <A>.<c2>{1}=<B>.<c2>{2}`` (positionally matched off each side's
        reprogramming ``if``). Empty off-shape (either side lacks a reprogramming
        ``HashG`` -- e.g. a Honest-hop endpoint) so every other hop is
        byte-identical."""
        la = _reprogram_side(step_a)
        lb = _reprogram_side(step_b)
        if la is None or lb is None:
            return ""
        (ma, fa), (mb, fb) = la, lb
        # pylint: disable=protected-access
        return " /\\ ".join(
            f"{ma}.{mt._ec_field_name(fa[i])}"
            "{1}"
            f" = {mb}.{mt._ec_field_name(fb[i])}"
            "{2}"
            for i in range(min(len(fa), len(fb)))
        )
        # pylint: enable=protected-access

    def _stored_pair_vs_chal_field_coupling(
        step_a: frog_ast.Step, step_b: frog_ast.Step
    ) -> str:
        """Cross-seam conjuncts for a MIXED delegate pair: one reduction STORES a
        packed key it obtained from a challenger ORACLE, the other DELEGATES its
        ``Initialize`` to a challenger that stores the corresponding component
        itself. Empty string off-shape.

        The HON_BIND ``hop_4``/``hop_8`` class: ``R_KG_PQ_L`` does
        ``pq_keys_0 <@ Challenger.generate()`` and holds the whole ``(ek, dk)``
        pair, while ``R_PQ_Bind`` does ``ek_PQ_0 <@ Challenger.initialize()`` and
        holds NO PQ field -- its inner binding challenger holds ``dk0``. Neither
        existing builder bridges that seam: ``_query_delegate_pair_coupling``
        needs BOTH sides to be query-delegates with equal field sets, and the
        wall-7 composite path needs the field-holding side to delegate
        ``Initialize``. The result was a coupling carrying only the same-named
        ``dk_T_0``/``ek_T_0``, which leaves the per-oracle lemmas UNPROVABLE as
        stated: both ``decaps0`` bodies differ exactly by
        ``KEM_PQ.decaps(pq_keys_0.`2, ..)`` vs the challenger's
        ``decaps0(..)`` = ``KEM_PQ.decaps(<Chal>.dk0, ..)``, so the two calls'
        arguments cannot be equated.

        Emit ``<stored>.<field>{s}.`k = <Chal>.<f>{t}`` for each challenger field
        that a UNIQUE component of the stored packed field type-matches. Sound by
        construction: both sides' PQ keypair comes from the hop's own challenger,
        which is what the assumption hop's ``pr`` lemma relates.
        """
        if step_a.reduction is None or step_b.reduction is None:
            return ""
        helpers_by = {
            h.name: h for h in proof.helpers if isinstance(h, frog_ast.Reduction)
        }
        for stored_step, deleg_step, ss, ts in (
            (step_a, step_b, "1", "2"),
            (step_b, step_a, "2", "1"),
        ):
            assert (
                stored_step.reduction is not None and deleg_step.reduction is not None
            )
            # The delegating side: holds fields AND delegates Initialize.
            comp = _composite_reduction_step(deleg_step)
            if comp is None:
                continue  # try the mirrored orientation
            _deleg_base, chal_base, _own = comp
            # ... and its challenger must itself DECLARE state.
            # pylint: disable=protected-access
            chal_ast = engine._get_game_ast(deleg_step.challenger, None)
            # pylint: enable=protected-access
            if chal_ast is None or not chal_ast.fields:
                continue
            # The storing side must NOT delegate (else the composite path owns
            # this hop) and must hold a PRODUCT-typed field.
            if _reduction_init_delegates(stored_step.reduction.name):
                continue
            stored_red = helpers_by.get(stored_step.reduction.name)
            if stored_red is None:
                continue
            stored_base = pt.module_base_name(resolver.resolve(stored_step).module_expr)
            conj: list[str] = []
            # ORDINAL same-type pairing, both sides in DECLARATION order: the
            # k-th challenger field of an EC type takes the k-th same-typed
            # component of the stored packed fields. A single keypair has one
            # candidate each and pairs as before; a TWO-keypair binding game
            # (PK/DIFFKEY) holds ek0/ek1/dk0/dk1 against pq_keys_0/pq_keys_1, so
            # every type has two candidates and a uniqueness test would decline
            # exactly where the coupling is needed. Same ordinal-slot discipline
            # as ``_field_or_component_ref``.
            comps_by_type: dict[str, list[str]] = {}
            for sf in stored_red.fields:
                st_ty = top_types.resolve(sf.type)
                if not isinstance(st_ty, frog_ast.ProductType):
                    continue
                for k, comp_ty in enumerate(st_ty.types):
                    # pylint: disable=protected-access
                    comps_by_type.setdefault(
                        top_types.translate_type(comp_ty).text, []
                    ).append(
                        f"{stored_base}.{mt._ec_field_name(sf.name)}"
                        f"{{{ss}}}.`{k + 1}"
                    )
                    # pylint: enable=protected-access
            used: dict[str, int] = {}
            for cf in chal_ast.fields:
                ctext = top_types.translate_type(cf.type).text
                slot = used.get(ctext, 0)
                cands = comps_by_type.get(ctext, [])
                if slot >= len(cands):
                    continue  # challenger holds more of this type than we store
                used[ctext] = slot + 1
                # pylint: disable=protected-access
                conj.append(
                    f"{cands[slot]} = {chal_base}.{mt._ec_field_name(cf.name)}{{{ts}}}"
                )
                # pylint: enable=protected-access
            if conj:
                live_state_holders.add(chal_base)
                return " /\\ ".join(conj)
        return ""

    def _tuple_component_relations(
        proc: ec_ast.Proc, fld: str, alias: str, dets: set[str]
    ) -> list[str]:
        """Intra-tuple relations a challenger's own body establishes.

        Reads the RETURNED tuple of ``proc`` and relates its components to each
        other, two ways: a component that repeats an earlier one, and a
        component produced by a DETERMINISTIC call whose arguments are
        themselves components (rendered in ``ev_`` form). Both are structural
        facts about how the challenger built its own result -- not assumptions.
        """
        ret = next(
            (s for s in reversed(proc.body) if isinstance(s, ec_ast.Return)), None
        )
        if ret is None:
            return []
        expr = ret.expr.strip()
        if not (expr.startswith("(") and expr.endswith(")")):
            return []
        comps = [c.strip() for c in cc_split_args(expr[1:-1])]
        if len(comps) < 2:
            return []
        idx_of: dict[str, int] = {}
        for k, c in enumerate(comps):
            idx_of.setdefault(c, k + 1)
        out: list[str] = []
        for k, c in enumerate(comps):
            first = idx_of.get(c)
            if first is not None and first < k + 1:
                out.append(f"{fld}.`{k + 1} = {fld}.`{first}")
        for st in proc.body:
            if not isinstance(st, ec_ast.Call) or not st.var:
                continue
            slot = idx_of.get(st.var)
            if slot is None:
                continue
            _m, dot, meth = st.callee.partition(".")
            if not dot or meth not in dets:
                continue
            refs: list[str] = []
            ok = True
            for a in cc_split_args(st.args) if st.args.strip() else []:
                pos = idx_of.get(a.strip())
                if pos is None:
                    ok = False
                    break
                refs.append(f"({fld}.`{pos})")
            if not ok:
                continue
            applied = (" " + " ".join(refs)) if refs else ""
            out.append(f"{fld}.`{slot} = {alias}.ev_{meth}{applied}")
        return out

    def _stored_tuple_invariants(step_a: frog_ast.Step, step_b: frog_ast.Step) -> str:
        """ONE-SIDED invariant conjuncts for a reduction that STORES a
        challenger oracle's returned tuple in a field. Empty off-shape.

        Every other coupling builder emits CROSS-SIDE equalities. The IND-CCA
        correctness reductions need something none of them can express: a
        property of one side alone. ``R_Correct_*`` stores
        ``corr <@ Challenger.compute()`` and its ``decaps`` case-splits, using
        the stored ``corr.`5`` instead of calling ``decaps`` on the
        already-encapsulated ciphertext. Relating that to the game side needs
        ``corr.`5 = ev_decaps corr.`2 corr.`3`` -- not a relation between the
        two sides at all, so the hop's precondition never carried it and no
        decaps tactic could close.

        The fact is STRUCTURAL, not the correctness assumption:
        ``KEMCorrectnessWithDK_FromDecaps.compute`` literally computes its 5th
        component as ``K.decaps`` of its 2nd and 3rd, and ``_FromEncaps``
        returns the encaps shared secret in both slots. Correctness is the claim
        that those two challengers differ negligibly, and that epsilon rides on
        the assumption hop BETWEEN them -- not inside either hop. So no axiom.

        Validated end to end on ``ec_templates/one_sided_tuple_invariant.ec``:
        the init equiv can establish these conjuncts, the oracle equiv can
        consume them to close the case split, and without them the branch is
        not provable.
        """
        conj: list[str] = []
        for step, side in ((step_a, "1"), (step_b, "2")):
            if step.reduction is None:
                continue
            red_mod = next(
                (
                    d
                    for d in ec_reductions
                    if isinstance(d, ec_ast.Module) and d.name == step.reduction.name
                ),
                None,
            )
            if red_mod is None:
                continue
            init = next((p for p in red_mod.procs if p.name == "initialize"), None)
            if init is None:
                continue
            resolved = resolver.resolve(step).module_expr
            chal_expr = pt.last_module_arg(resolved)
            chal_base = pt.module_base_name(chal_expr).rpartition(".")[2]
            chal_mod = next(
                (
                    d
                    for lst in (theory_game_decls, foreign_game_decls)
                    for d in lst
                    if isinstance(d, ec_ast.Module) and d.name == chal_base
                ),
                None,
            )
            if chal_mod is None:
                continue
            # the challenger's single scheme argument names the instance whose
            # clone alias carries the ``ev_`` ops and whose determinism map says
            # which methods HAVE one
            inner = (
                chal_expr[chal_expr.find("(") + 1 : chal_expr.rfind(")")]
                if "(" in chal_expr
                else ""
            )
            args = [a.strip() for a in cc_split_args(inner) if a.strip()]
            if len(args) != 1:
                continue
            alias = clone_alias_by_module.get(args[0])
            if alias is None:
                continue
            dets = det_methods_by_module.get(args[0], set())
            red_base = pt.module_base_name(resolved)
            for st in init.body:
                if not isinstance(st, ec_ast.Call) or not st.var:
                    continue
                _m, dot, meth = st.callee.partition(".")
                if not dot:
                    continue
                proc = next((p for p in chal_mod.procs if p.name == meth), None)
                if proc is None:
                    continue
                # pylint: disable=protected-access
                fld = f"{red_base}.{mt._ec_field_name(st.var)}{{{side}}}"
                # pylint: enable=protected-access
                conj.extend(_tuple_component_relations(proc, fld, alias, dets))
        return " /\\ ".join(conj)

    def _live_state_coupling(step_a: frog_ast.Step, step_b: frog_ast.Step) -> str:
        base = _live_state_coupling_base(step_a, step_b)
        extra = _ro_challenger_materialization(step_a, step_b)
        if _is_lazyro_honest_hop(step_a, step_b) is not None:
            # The reduction side's shared-RO holder (RO_G_RO) is DEAD (it uses the
            # Honest challenger's RO for every query), so ``={glob RO_G_RO}`` cannot
            # hold post-init (the pr-lemma drops the dead sample). Strip it from the
            # base -- the cross-side ``RO_G_RO.h{game}=<chal>.h{red}`` in ``extra`` is
            # the real RO coupling the per-oracle lemmas need.
            #
            # ALSO strip ``={glob P}`` for an abstract module ``P`` DEAD in this
            # hop's flat states: the ROM game's ``Challenge`` returns a constant
            # (``Unbreakable`` = ``false``), so its KDF/label calls are dropped and
            # ``H``/``L`` fall out of the flat states' ``(glob)``. The field-aware
            # leg couplings then intersect them away (chain_emitter's ``li & ri``),
            # so a ``={glob H}`` the wrapper still carries (its live ``Challenge``)
            # in the OUTER lemma cannot thread the H-free intermediate states -- the
            # transitivity post-composition "cannot prove goal (strict)". Match the
            # legs by dropping the dead modules here too. Gated to lazyro-honest
            # hops, so every other proof stays byte-identical.
            live = _hop_live_abstract_modules(step_a, step_b)
            dead = list(ro_holder_modules) + [
                m for m in abstract_scheme_modules if m not in live
            ]
            for m in dead:
                base = base.replace(f" /\\ ={{glob {m}}}", "").replace(
                    f"={{glob {m}}} /\\ ", ""
                )
        coupled = f"{base} /\\ {extra}" if extra else base
        # Seedbased binding wrapper: couple the reduction's seed field to the
        # inlined challenger's decaps key when the reduction's Initialize repacks
        # it under a different name (``s_PQ_0`` = challenger's ``dk0``). The
        # composite seam couples by name and misses the rename. Empty off-shape.
        wchal = _wrapper_challenger_coupling(step_a, step_b)
        if wchal:
            # DEDUP against what is already stated. Widening this builder's gate
            # (it used to key on a ``Function<>`` param, a proxy no HON reduction
            # satisfies) makes it fire on reductions whose repack the composite
            # seam ALREADY couples by name, and a repeated conjunct changes the
            # emitted bytes of proofs that are clean today. Scoped to this
            # builder on purpose: other pairs of builders also overlap, but
            # those duplicates predate this change and normalising them would
            # churn six clean exports for a cosmetic gain.
            have = set(coupled.split(" /\\ "))
            fresh = [c for c in wchal.split(" /\\ ") if c not in have]
            if fresh:
                coupled = f"{coupled} /\\ " + " /\\ ".join(fresh)
        # MIXED delegate pair (HON_BIND hop_4/hop_8 class): the storing side's
        # packed key component <-> the delegating side's challenger field.
        spc = _stored_pair_vs_chal_field_coupling(step_a, step_b)
        if spc:
            coupled = f"{coupled} /\\ {spc}"
        # Seedbased self-keygen reduction (R_KDF): couple its wrapper-derived stored
        # decaps key to the seed it was derived from (``dk_PQ_0 = s_PQ_0``, since the
        # concrete wrapper's derivekeypair returns the seed). Empty off-shape.
        wdk = _wrapper_stored_dk_coupling(step_a, step_b)
        if wdk:
            coupled = f"{coupled} /\\ {wdk}"
        # Lazy-RO Honest hop: couple the reduction's stored keys to the RO
        # evaluated at the game's stored seed (``dk_PQ_0 = slice(RO[dk0])``,
        # ``dk_T_0 = ev_randomscalar(slice(RO[dk0]))``) -- the derived relation the
        # LazyRO challenge peel needs (the reduction discards its seed). Empty
        # off-shape -> byte-identical.
        lzk = _lazyro_derived_key_coupling(step_a, step_b)
        if lzk:
            coupled = f"{coupled} /\\ {lzk}"
        # Reprogramming-Lazy hop: carry the cross-side reprogramming-field
        # correspondences so the per-oracle ``HashG`` equiv's guard/then-branch is
        # provable (the init couples the reductions' stored fields but not the
        # ``_Mat`` challenger's reprogram fields). Empty off-shape -> byte-identical.
        reprog = _reprogram_field_coupling(step_a, step_b)
        # ONE-SIDED invariants last: intra-tuple relations a challenger's own
        # body establishes about a tuple the reduction stores. Every conjunct
        # above is a CROSS-SIDE equality; this is the only builder that states
        # a property of one side alone, which is what a case-splitting oracle
        # needs (see ``_stored_tuple_invariants``). Empty off-shape.
        tup = _stored_tuple_invariants(step_a, step_b)
        if tup:
            coupled = f"{coupled} /\\ {tup}"
        return f"{coupled} /\\ {reprog}" if reprog else coupled

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
        if _is_init and _is_lazyro_honest_hop(step_a, step_b) is not None:
            # The init lemma is unprovable for a lazy-RO Honest hop (the challenger
            # samples a fresh RO the game reads pre-existing) AND unused -- the
            # pr-lemma inlines the init and couples the samples directly. Skip it.
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
            # Two-KEM reprogram-equiv hop (CK-class hop_2/hop_10): the whole
            # init tactic is computed here off the RENDERED modules; the same
            # flag switches the challenge closer to the bounded ladder.
            reprogram_override = _reprogram_equiv_init_tac(step_a, step_b)
            # PRG query-delegate hop (HON_BIND hop_0/hop_12 ``initialize``): the
            # derivation-chain post needs the calls FUNCTIONALIZED, which the
            # generic ``call (_: true)`` peel cannot do. Tried only where the
            # reprogram builder declines; ``None`` off-shape, so every other init
            # is byte-identical.
            if reprogram_override is None:
                reprogram_override = _prg_query_init_tac(step_a, step_b)
            if reprogram_override is None:
                reprogram_override = _keygenequiv_init_tac(step_a, step_b)
            # Split-seed hop (HON_BIND hop_14 ``initialize``): one side samples
            # each keypair's two seeds independently, the other slices one full
            # seed. ``None`` off-shape, so every other init is byte-identical.
            if reprogram_override is None:
                reprogram_override = _split_seed_init_tac(step_a, step_b)
            # Same-backbone / different-LAYOUT hop (HON_BIND hop_4 / hop_8
            # ``initialize``): batch the interleaved side, then peel. ``None``
            # off-shape, and it declines outright when both sides are already
            # batched, so every other init is byte-identical.
            if reprogram_override is None:
                reprogram_override = _batched_align_init_tac(step_a, step_b)

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
                inj_methods_by_module=inj_methods_by_module,
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
                is_lazyro_honest=_is_lazyro_honest_hop(step_a, step_b) is not None,
                drop_globs=(
                    frozenset(
                        m
                        for m in abstract_scheme_modules
                        if m not in _hop_live_abstract_modules(step_a, step_b)
                    )
                    if _is_lazyro_honest_hop(step_a, step_b) is not None
                    else frozenset()
                ),
                both_reductions=(
                    step_a.reduction is not None and step_b.reduction is not None
                ),
                init_tac_override=reprogram_override,
                oracle_tac_override=_twin_challenge_oracle_tacs(step_a, step_b),
            )
            chain_extra_decls.extend(info.extra_decls)
            pres_method_requests.update(info.pres_methods)
            inj_method_requests.update(info.inj_methods)
            bij_method_requests.update(info.bij_methods)
            inj_method_requests.update((m, x) for m, x, _bs, _a in info.bij_methods)
            decaps_val_requests.update(info.decaps_val_schemes)
            if info.aux_lemmas and not aux_lemma_lines:
                aux_lemma_lines.extend(info.aux_lemmas)
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

    def _consume_pk_challenger_events(
        scheme_expr: str, game: frog_ast.Game, gf_name: str
    ) -> list[str] | None:
        """Structural challenger-init event list for the consume-pk peel, or
        ``None`` (=> the flat per-keygen "call" model, byte-identical).

        Only a CONCRETIZED-WRAPPER challenger scheme diverges from the flat
        model: its keygens inline to their real [sample; call] shape (the
        seedbased wrapper draws a seed then calls the inner ``derivekeypair``),
        and a ROM proof's shared-RO sample leads the block (both byequiv sides
        hold it up front after the emitted ``swap{2} ^ <${1} @ 0`` hoist)."""
        sch_base = pt.module_base_name(scheme_expr)
        wrap_mod = next(
            (m for m in foreign_concrete_modules.values() if m.name == sch_base),
            None,
        )
        kg = (
            next((pr for pr in wrap_mod.procs if pr.name == "keygen"), None)
            if wrap_mod is not None
            else None
        )
        if kg is None:
            # No concretized keygen wrapper: the challenger is a plain game
            # whose own ``Initialize`` IS the block the peel must consume, so
            # read it directly rather than falling back to the flat per-keygen
            # "call" model. That model assumes exactly one keygen seed; a
            # challenger drawing its own samples (``RandomScalarDist``: two
            # seeds, then two ``randomscalar`` calls) leaves the ladder short,
            # which EC reports as "left instruction list is not empty" at 99%
            # of the file.
            # RENDERED events first: a game whose ``Initialize`` returns a
            # call-bearing expression (``return (G^x, G^y);``) hoists those
            # calls into their own statements, which the FrogLang AST does not
            # show. Sizing the challenger block from the AST left the SDH_SS
            # bridges' rungs mis-aligned ("invalid last instruction").
            own = rendered_init_events_by_game.get(
                (gf_name, game.name)
            ) or mt.init_backbone_events(game)
            if not own:
                return None
            return (["sample"] if ro_holder_modules else []) + own
        assert wrap_mod is not None  # kg is None above unless wrap_mod exists
        kg_events: list[str] = []
        for st in kg.body:
            if isinstance(st, ec_ast.Sample):
                kg_events.append("sample")
            elif isinstance(st, ec_ast.Call):
                _m, _d, _meth = st.callee.partition(".")
                if not _d:
                    sub = next(
                        (pr for pr in wrap_mod.procs if pr.name == st.callee), None
                    )
                    for ss in sub.body if sub is not None else []:
                        if isinstance(ss, ec_ast.Sample):
                            kg_events.append("sample")
                        elif isinstance(ss, ec_ast.Call):
                            kg_events.append("call")
                else:
                    kg_events.append("call")
        if not kg_events:
            return None
        n_kg = mt.init_module_call_count(game)
        return (["sample"] if ro_holder_modules else []) + kg_events * n_kg

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
        lazyro: pt.LazyroInitSpec | None = None
        lazy_hop = _is_lazyro_honest_hop(step_a, step_b)
        if lazy_hop is not None:
            # The reduction (delegating to the Honest challenger) may be on
            # EITHER side: forward hop -> side 2, reverse-direction hop -> side 1.
            # The dead-RO swap/drop must act on this side (``red_side``).
            red_side = lazy_hop[1]
            red_step = step_a if step_a.reduction is not None else step_b
            assert red_step.reduction is not None
            red = _get_reduction(red_step.reduction.name)
            # pylint: disable=protected-access
            chal_game = engine._get_game_ast(red_step.challenger, None)
            # pylint: enable=protected-access
            chal_init = _find_init(chal_game) if chal_game is not None else None
            red_init = _find_init(red) if red is not None else None
            dfun = next((d for _m, d in top_types.function_value_modules()), None)
            if chal_init is not None and red_init is not None and dfun is not None:
                swap_below = sum(
                    isinstance(s, (frog_ast.Sample, frog_ast.UniqueSample))
                    for s in chal_init.block.statements
                )
                # Count EVERY abstract-scheme call (nested included -- ``inline *``
                # hoists a nested ``NG.Generator()`` inside ``NG.Exp(...)`` into its
                # own ``<@`` statement, so the post-inline peel-round count is the
                # total call count, not the top-level assignment count).
                _n = [0]

                def _count_call(n: frog_ast.ASTNode) -> bool:
                    if (
                        isinstance(n, frog_ast.FuncCall)
                        and isinstance(n.func, frog_ast.FieldAccess)
                        and isinstance(n.func.the_object, frog_ast.Variable)
                        and n.func.the_object.name != "challenger"
                    ):
                        _n[0] += 1
                    return False

                visitors.SearchVisitor(_count_call).visit(red_init.block)
                n_calls = _n[0]
                # Two-keypair lazy-RO hop (PK / two-keypair DIFFKEY): the
                # game interleaves per-keypair derivations while the reduction
                # batches per-op, so neither single-keypair branch closes.
                # Compute the whole init tail here; ``None`` off-shape keeps
                # the single-keypair paths byte-identical.
                game_step_l = step_a if step_a.reduction is None else step_b
                override = _lazyro_two_keypair_init_tac(
                    lazy_hop, red_step, game_step_l, chal_init, f"{dfun}_ll"
                )
                derived_kw = (
                    {}
                    if override is not None
                    else _lazyro_derived_init_fields(
                        step_a, step_b, lazy_hop, red, red_init, chal_init
                    )
                )
                lazyro = pt.LazyroInitSpec(
                    swap_below=swap_below,
                    n_calls=n_calls,
                    dfun_ll=f"{dfun}_ll",
                    red_side=red_side,
                    init_tac_override=override,
                    **derived_kw,
                )
        return pt.MultiOraclePrSpec(
            coupling=_live_state_coupling(step_a, step_b),
            init_oracle=model.init_name,
            post_init_oracles=list(model.post_init_names),
            byequiv_pre=multi_oracle_byequiv_pre,
            lazyro=lazyro,
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
        # The THEOREM GAME's challenger holds live state too (a binding game's
        # ``ek0``/``dk0``...), and every per-oracle lemma about it needs the
        # abstract scheme modules write-separated from it -- otherwise EC rejects
        # even a glob-only lemma with "module <K> can write <Game>.<field>",
        # because it cannot know the abstract call leaves the game's own state
        # alone between the assignment and the return. Some couplings already
        # register it as a side effect of NAMING it (the PRG derivation chain
        # does); this covers the hops whose coupling is glob-only, where nothing
        # names it and the restriction was simply missing. Gated on
        # ``live_state_holders`` being non-empty (a multi-oracle proof) and on
        # the challenger actually declaring fields, so single-oracle and
        # stateless-challenger proofs are unaffected.
        for _st in proof.steps:
            if not isinstance(_st, frog_ast.Step) or _st.reduction is not None:
                continue
            # pylint: disable-next=protected-access
            _chal_ast = engine._get_game_ast(_st.challenger, None)
            if _chal_ast is not None and _chal_ast.fields:
                live_state_holders.add(
                    pt.module_base_name(resolver.resolve(_st).module_expr)
                )
    live_state_modules = sorted(live_state_holders)
    # ROM Lazy-side dead-drop: the reprogramming challenger's cross-named fields
    # ride the ``call (_: inv)`` invariant, so the adversary must be write-separated
    # from that (clone-qualified) challenger module. Accumulate the globs across
    # hops; each dead-drop pr-lemma restricts A from its OWN challenger (a subset),
    # and ``main_theorem`` from the full set (a superset) so ``hop_i_pr A`` still
    # typechecks. Empty for non-ROM proofs (byte-identical).
    repro_chal_globs: set[str] = set()

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
            # ROM bridge: the RO-align + sim close is VALIDATED (cont-91) only for the
            # ``Honest`` side of a lazy-RO assumption (``CGLazyRO*Seeded``) -- the side
            # whose SIBLING game REPROGRAMS the RO but which itself does not. The Lazy
            # (reprogramming) side has the materialized-vs-fresh RO asymmetry (dead-drop,
            # deferred). A non-lazy-RO assumption (a binding/KeyGenEquiv challenger) does
            # NOT close with plain sim (its repack is richer), so gate on the file having
            # a reprogramming sibling. The sim-closeable side flips by hop.
            # Is the assumption game Initialize-LIFTED (a no-arg ``Initialize``
            # the wrapper's ``main`` runs before the adversary)?  When it is not
            # -- ``Initialize`` takes parameters and stays an ordinary oracle --
            # two things change: the challenger contributes NO events at the
            # FRONT of the bridge backbone (its ``Initialize`` is invoked from
            # inside the reduction instead, so its events are spliced in at that
            # position), and the RO-align + plain ``sim`` close does not apply
            # (it was validated only for the lifted shape, where both sides run
            # the challenger init up front).
            _init_lifted = (
                assumption_adv_pos_by_gf.get(assumption_game_file_name, 2) > 1
            )
            _gf_a_has_reprogram = any(
                _reprogramming_lazy_ro_field(g) is not None for g in gf_a.games
            )
            # The "sim shape" is the side of a reprogramming assumption whose
            # own game holds the whole-Function RO field (so the RO is
            # materializable rather than lazily tabulated). Under the LIFTED
            # wrapper shape that side closes with RO-align + plain ``sim``
            # (validated cont-91). Under the NON-lifted shape it has no
            # validated close at all: the peel runs to the end but the final
            # `/#` cannot discharge the residual, because the lazy side samples
            # a single stand-in (`yStar <$`) where the theorem side carries a
            # whole function, and relating them IS the hop's real content, not
            # plumbing. Honest-gate it: a tagged admit beats a tactic that
            # rejects the whole file (cont-40).
            _sim_shape_l = _gf_a_has_reprogram and (
                _reprogramming_lazy_ro_field(
                    next(g for g in gf_a.games if g.name == left_side)
                )
                is None
            )
            _sim_shape_r = _gf_a_has_reprogram and (
                _reprogramming_lazy_ro_field(
                    next(g for g in gf_a.games if g.name == right_side)
                )
                is None
            )
            left_ro_sim_ok = _init_lifted and _sim_shape_l
            right_ro_sim_ok = _init_lifted and _sim_shape_r
            left_bridge_admit = (not _init_lifted) and _sim_shape_l
            right_bridge_admit = (not _init_lifted) and _sim_shape_r
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
            # ROM Lazy-side dead-``h`` drop spec, computed PER SIDE for the
            # reprogramming (non-sim-ok) side of a lazy-RO consume-pk hop. The
            # materialized ``_Mat`` challenger is a top-level module ``<gf>_<side>_Mat``
            # (side {1}); the plain reprogramming challenger is the clone-qualified
            # ``<clone>.<gf>_<side>`` (side {2}) -- the same string passed as
            # ``consume_pk_<side>_challenger_glob``. ``_ro_dead_drop_spec`` returns
            # ``None`` for a non-reprogramming (Honest / binding / forward) game, so
            # those sides keep their existing close byte-identically.
            ro_dead_drop_left: pt.RoDeadDropSpec | None = None
            ro_dead_drop_right: pt.RoDeadDropSpec | None = None
            if consume_pk_bridge and ro_holder_modules:
                # The DROPPED sample is the dead SHARED RO ``RO_G_RO.h`` (re-sampled
                # but unused on the assumption side), whose distribution is the
                # top-level RO holder's dfun (``function_value_modules``) -- NOT the
                # challenger's own (theory) ``h``, which stays LIVE and coupled.
                _fv_mods = top_types.function_value_modules()
                _dfun_ll = f"{_fv_mods[0][1]}_ll" if _fv_mods else ""
                # Peel count = the reduction's OWN (non-challenger) abstract calls
                # in ``Initialize``. After the ``rcondt`` collapses the challenger
                # ``hash``, the pre-adversary residual holds exactly these (each
                # ``inline *`` also hoists a nested ``NG.Generator()`` inside
                # ``NG.Exp(...)`` into its own ``<@`` -- so count nested too).
                _red_init = _find_init(reduction_helper) if reduction_helper else None
                _peel_n = [0]
                if _red_init is not None:
                    visitors.SearchVisitor(_own_call_counter(_peel_n)).visit(
                        _red_init.block
                    )
                _peel_ct = _peel_n[0]
                # ONLY when the materialized copy was actually emitted. The
                # ``_Mat`` name is built from the game name, but the copy is
                # emitted only for a reprogramming-Lazy side of a PRIMARY game
                # file; an ROM helper assumption living in a secondary clone
                # (``P_c.LazyROTwoViewsExcludedProgrammed_Honest``) never gets
                # one, and naming it anyway emits an unknown-variable reference
                # that rejects the WHOLE file. Declining leaves the plain
                # consume-pk close, which is at worst a visible tactic failure.
                if not left_ro_sim_ok and (gf_a.name, left_side) in (
                    reprogramming_lazy_games
                ):
                    ro_dead_drop_left = _ro_dead_drop_spec(
                        next(g for g in gf_a.games if g.name == left_side),
                        mat_glob=f"{gf_a_id}_{left_side}_Mat",
                        lazy_glob=f"{hop_clone}.{gf_a_id}_{left_side}",
                        dfun_ll=_dfun_ll,
                        peel_count=_peel_ct,
                    )
                if not right_ro_sim_ok and (gf_a.name, right_side) in (
                    reprogramming_lazy_games
                ):
                    ro_dead_drop_right = _ro_dead_drop_spec(
                        next(g for g in gf_a.games if g.name == right_side),
                        mat_glob=f"{gf_a_id}_{right_side}_Mat",
                        lazy_glob=f"{hop_clone}.{gf_a_id}_{right_side}",
                        dfun_ll=_dfun_ll,
                        peel_count=_peel_ct,
                    )
            # Restrict A from each dead-drop side's reprogramming challenger (its
            # cross-named fields ride the ``call (_: inv)`` invariant). This hop
            # gets its own subset; ``main_theorem`` accumulates the full set.
            hop_restrictions = list(live_state_modules)
            for _spec in (ro_dead_drop_left, ro_dead_drop_right):
                if _spec is not None and _spec.lazy_glob not in hop_restrictions:
                    hop_restrictions.append(_spec.lazy_glob)
                    repro_chal_globs.add(_spec.lazy_glob)

            # Challenger-init events PER SIDE, not per assumption: the two
            # games of one assumption can have different ``Initialize``
            # backbones (``RandomScalarDist`` derives its scalars from seeds on
            # the Honest side and samples them directly on the Random side), so
            # a ladder sized from one side is wrong for the other.
            _chal_events_l: list[str] | None = None
            _chal_events_r: list[str] | None = None
            # Events the challenger's own ``Initialize`` contributes where the
            # reduction calls it (non-lifted assumption games only).
            _chal_inline_l: list[str] | None = None
            _chal_inline_r: list[str] | None = None
            if consume_pk_bridge and reduction_helper is not None and not _init_lifted:
                _chal_events_l = ["sample"] if ro_holder_modules else []
                _chal_events_r = list(_chal_events_l)
                _gl = next((g for g in gf_a.games if g.name == left_side), None)
                _gr = next((g for g in gf_a.games if g.name != left_side), None)
                if _gl is not None:
                    _chal_inline_l = rendered_init_events_by_game.get(
                        (gf_a.name, _gl.name)
                    ) or mt.init_backbone_events(_gl)
                if _gr is not None:
                    _chal_inline_r = rendered_init_events_by_game.get(
                        (gf_a.name, _gr.name)
                    ) or mt.init_backbone_events(_gr)
            elif consume_pk_bridge and reduction_helper is not None:
                _g_l = next((g for g in gf_a.games if g.name == left_side), None)
                _g_r = next((g for g in gf_a.games if g.name != left_side), None)
                if _g_l is not None:
                    _chal_events_l = _consume_pk_challenger_events(
                        assumption_scheme_expr, _g_l, gf_a.name
                    )
                if _g_r is not None:
                    _chal_events_r = _consume_pk_challenger_events(
                        assumption_scheme_expr, _g_r, gf_a.name
                    )
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
                    adv_state_restrictions=sorted(hop_restrictions) or None,
                    assumption_adv_pos=assumption_adv_pos_by_gf.get(
                        assumption_game_file_name, 2
                    ),
                    consume_pk_bridge=consume_pk_bridge,
                    # Peel the FULL init backbone: the challenger's own init
                    # calls PLUS the reduction's own backbone (CFRG ``R_PQ_Bind``'s
                    # ``KEM_T.keygen`` calls and/or NominalGroup seed samples).
                    # Event-aware so a seed ``<$`` peels with ``rnd``; empty own
                    # backbone (Generic) reduces to the challenger-only peel.
                    # The two byequiv bridges peel DIFFERENT backbones when the
                    # assumption's two games differ in their own ``Initialize``
                    # -- ``KEM_INDCCA.Random`` draws a fresh shared secret that
                    # ``.Real`` does not. Size each side from its own game.
                    consume_pk_peel_events_right=(
                        mt.consumed_pk_peel_events(
                            reduction_helper,
                            mt.init_module_call_count(gf_a.games[0]),
                            f"{gf_a_id}_Oracle",
                            method_return_types,
                            challenger_events=_chal_events_r,
                            challenger_inline_events=_chal_inline_r,
                        )
                        if consume_pk_bridge and reduction_helper is not None
                        else None
                    ),
                    consume_pk_peel_events=(
                        mt.consumed_pk_peel_events(
                            reduction_helper,
                            mt.init_module_call_count(gf_a.games[0]),
                            # The reduction's OWN Initialize backbone may itself
                            # call the challenger (a seedbased ``R_PQ_Bind`` queries
                            # ``challenger.Hash(seed_0)`` and slices the result), so
                            # the hoist needs the challenger's oracle type to type
                            # that nested call. The reduction composes ``gf_a`` as
                            # its challenger, so its oracle is ``{gf_a_id}_Oracle``.
                            f"{gf_a_id}_Oracle",
                            method_return_types,
                            challenger_events=_chal_events_l,
                            challenger_inline_events=_chal_inline_l,
                        )
                        if consume_pk_bridge and reduction_helper is not None
                        else None
                    ),
                    # True whenever the peel events are STRUCTURAL -- either
                    # from the concretized-wrapper builder or from the per-side
                    # fallback that reads each assumption game's own
                    # ``Initialize`` backbone. Both already account for every
                    # front sample, so the historical fixed two-``rnd``
                    # compensation would double-count them. Leaving this False
                    # while the fallback supplied structural events is what made
                    # the cycle-104 attempt overshoot ("invalid last
                    # instruction") after its count had been corrected.
                    consume_pk_events_cover_ro=True,
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
                    left_ro_sim_ok=left_ro_sim_ok,
                    left_bridge_admit=left_bridge_admit,
                    right_bridge_admit=right_bridge_admit,
                    right_ro_sim_ok=right_ro_sim_ok,
                    ro_dead_drop_left=ro_dead_drop_left,
                    ro_dead_drop_right=ro_dead_drop_right,
                    # Re-init-forward shape: a STATELESS assumption challenger (no
                    # ``Initialize``, e.g. KeyGenEquiv's ``Generate`` /
                    # KDFCollisionResistance's ``Challenge``) makes the wrapper
                    # ``main`` a single ``b <@ A(chal).distinguish()`` -- the
                    # reduction re-inits internally, and the shared RO sits at the
                    # FRONT of ``distinguish`` on both sides. Then ``proc; inline{2}
                    # 1; inline *; sim`` closes (no swap, no dead-drop -- the two
                    # sides are identical modulo the RO being eager vs first-in-
                    # distinguish). A stateful challenger (LEAK_BIND's Initialize)
                    # keeps the consume-pk / dead-drop / admit routes.
                    ro_forward_shape=bool(ro_holder_modules)
                    and not consume_pk_bridge
                    and not any(
                        m.signature.name == "Initialize"
                        for g in gf_a.games
                        for m in g.methods
                    ),
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

    # Fold the ROM dead-drop reprogramming challengers into the shared restriction
    # set so ``main_theorem`` (and every later consumer) separates A from the full
    # set -- a superset of each per-hop pr-lemma restriction.
    if repro_chal_globs:
        live_state_modules = sorted(set(live_state_modules) | repro_chal_globs)

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
        # Random-function distributions ``dfun_<D>_to_<C>`` (a lazy-RO
        # challenger's ``h <$ dfun``): bind the theory's dfun to the SHARED
        # concrete RO distribution when the concretized domain/codomain match a
        # registered RO holder's dfun. Then a lazy-RO Honest challenger samples
        # the very distribution the game's RO does, so the pr-lemma's ``rnd``
        # couples them with no unprovable ``mu1 d1 = mu1 d2`` side-condition (the
        # two abstract dfun ops were otherwise distinct). Skip (leave abstract)
        # when no matching concrete RO dfun exists -- non-ROM proofs stay
        # byte-identical.
        tb_map = dict(type_bindings_)
        # Every dfun the TOP LEVEL declares is a candidate, not only those with a
        # registered RO-holder module. The holder-only gate missed the common
        # case where the random function is a scheme PARAMETER sampled inside
        # the theory (the KDF ``H`` of the CFRG combiners): the concrete
        # ``dfun_<D>_to_<C>`` op exists, but no holder module does, so the two
        # ops stayed distinct and every ``rnd`` coupling them was left with a
        # ``mu1 d1 = mu1 d2`` + support obligation for ``smt`` to grind through.
        # That obligation is what makes the init peel's closing ``skip => /#``
        # load-sensitive (goal-probed, cycle 122). Binding removes it rather
        # than discharging it, and is sound for the same reason the holder case
        # is: both ops ARE the uniform distribution on the same arrow type, and
        # the domain/codomain still have to match after concretization.
        known_dfuns = {dfn for _, dfn in top_types.function_value_modules()}
        known_dfuns |= {name for name, _, _ in top_types.function_distrs_seen()}
        for dfun_name, d_t, c_t in src_theory_types.function_distrs_seen():
            concrete_dfun = f"dfun_{tb_map.get(d_t, d_t)}_to_{tb_map.get(c_t, c_t)}"
            if concrete_dfun in known_dfuns and concrete_dfun != dfun_name:
                op_bindings_.append((dfun_name, concrete_dfun))
        # Concat ops ``concat_<L>_<R>_to_<Res>``: a theory concat and the SAME
        # concatenation registered at top level (e.g. a materialized ``_Mat`` lazy-RO
        # challenger) are otherwise DISTINCT uninterpreted ops, so a top-level module
        # cannot relate to a theory module through them (the ROM dead-drop bridge).
        # Bind the theory concat to the concretized top-level one when it exists --
        # sound (same concatenation), and guarded on registration so a proof with no
        # matching top-level concat stays byte-identical.
        known_concats = top_types.concat_op_names()
        for concat_name, l_t, r_t, res_t in src_theory_types.concat_ops_seen():
            concrete_concat = (
                f"concat_{tb_map.get(l_t, l_t)}_{tb_map.get(r_t, r_t)}"
                f"_to_{tb_map.get(res_t, res_t)}"
            )
            if concrete_concat in known_concats and concrete_concat != concat_name:
                op_bindings_.append((concat_name, concrete_concat))
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
            # Non-distribution op-bindings (a bound ``concat_``/``slice_`` function
            # op, threaded through the same clone ``op_bindings`` list) are NOT
            # distributions -- ``is_funiform``/``is_lossless`` are ill-typed on them.
            if concrete_distr.startswith(("concat_", "slice_")):
                continue
            for suffix, predicate, source_suffix in (
                ("funi", "is_funiform", "fu"),
                ("ll", "is_lossless", "ll"),
            ):
                axiom_name = f"{inst.let_name}_{concrete_distr}_{suffix}"
                if axiom_name in seen_axiom_names:
                    continue
                seen_axiom_names.add(axiom_name)
                # DERIVED, not assumed. These are verbatim restatements, under a
                # clone-local name, of facts the distribution already carries --
                # ``<distr>_fu`` / ``<distr>_ll`` are emitted for every
                # distribution that can reach here (bitstring, abstract-carrier,
                # random-function). Restating them as axioms doubled the count a
                # reviewer has to work through for nothing. ``exact`` works
                # whichever standing the source has, so this is unconditional.
                clone_axioms.append(
                    ec_ast.ProvedLemma(
                        axiom_name,
                        f"{predicate} {concrete_distr}",
                        [f"  exact {concrete_distr}_{source_suffix}."],
                    )
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
    if mat_challenger_decls:
        decls.append(_section_header("Materialized reprogramming-Lazy challengers"))
        decls.extend(mat_challenger_decls)
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
    # ``slice4_first`` + ``kdf_col_ss`` aux lemmas for the seedbased WRAPPER
    # binding-challenge collision branch (peel the KDF concat + apply encoding
    # injectivity). They depend on the slice/inj axioms emitted above.
    if aux_lemma_lines:
        det_axiom_decls += [
            _section_header("Binding-collision slice/injectivity aux lemmas"),
            "\n".join(aux_lemma_lines),
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
    # Bijectivity of an injective ENDO-map on a BitWord-backed type, DERIVED
    # (not axiomatized) from the ``_inj`` axiom just emitted plus the type's own
    # finiteness. Sits here because it consumes a ``declare axiom`` and so must
    # be section-local, after that axiom and before the hop lemmas that use it.
    if bij_method_requests:
        det_axiom_decls += [
            _section_header("Injective endo-map bijectivity (derived)"),
            *(
                _endo_bijectivity_lemmas(mod, meth, bs_name, alias)
                for mod, meth, bs_name, alias in sorted(bij_method_requests)
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
    bitword_imports, bitword_abstract = _bitword_requires(
        top_types.needs_bitword, stdlib_requires
    )
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
            *bitword_imports,
        ],
        decls=decls,
        abstract_requires=bitword_abstract,
    )
    return ec_ast.pretty_print(ec_file)
