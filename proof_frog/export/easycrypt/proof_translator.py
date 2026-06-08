"""Translate proof hop structure into EC lemmas.

Phase 2 scope: plain steps (``Game(E).Side``) and composed steps
(``Game(E).Side compose R(args)``). Every hop becomes one
``admit``-bodied equiv lemma. Induction is not supported.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Callable

from . import ec_ast
from . import oracle_model
from ... import frog_ast


class HopKind(enum.Enum):
    INLINING = "inlining"
    ASSUMPTION = "assumption"


@dataclass
class ResolvedStep:
    """The EC module expression and oracle name referenced by a step."""

    module_expr: str
    oracle_name: str


@dataclass
class MultiOraclePrSpec:
    """Per-oracle data a multi-oracle hop's Pr lemma needs (P4).

    A multi-oracle hop (``Initialize`` lifted into ``main`` plus one or more
    post-init oracles) discharges ``Pr[L] = Pr[R]`` via the validated section
    2.4 body of the multi-oracle foundation template
    (``tests/integration/ec_templates/multi_oracle_indist.ec``): one
    ``conseq hop_<i>_<m>`` per post-init oracle (in module-type declaration
    order) under a single ``call (_: <coupling>)``, then ``call
    hop_<i>_<init>; auto``.

    - ``coupling`` -- the relational state-coupling invariant string
      ``(glob L){1} = (glob R){2}`` (built by :func:`coupling_invariant` from
      the two wrappers' oracle module expressions; the *same* string the
      per-oracle equiv lemmas carry).
    - ``init_oracle`` -- EC name of the lifted ``Initialize`` oracle (the
      ``call hop_<i>_<init>`` target).
    - ``post_init_oracles`` -- EC names of the adversary-facing oracles, in
      module-type declaration order (one ``conseq`` bullet each).
    - ``byequiv_pre`` -- the ``byequiv`` precondition. Defaults to ``={glob A}``;
      when the post-init oracles call abstract scheme modules (e.g. KEMPRF's
      ``challenge`` calls ``K.encaps`` / ``F.evaluate``) it is strengthened to
      ``={glob A, glob K, glob F}`` so the per-oracle equiv lemmas' coupling
      (which carries ``={glob K} /\\ ={glob F}``) is established at ``main``
      entry. ``sim`` cannot relate two abstract calls without ``={glob}`` on the
      called module.
    """

    coupling: str
    init_oracle: str
    post_init_oracles: list[str]
    byequiv_pre: str = "={glob A}"


def coupling_invariant(left_module_expr: str, right_module_expr: str) -> str:
    """Return the relational state-coupling invariant for a multi-oracle hop.

    The two adjacent multi-oracle games carry mutable module state (set by
    the lifted ``Initialize``, read by the post-init oracles). The per-oracle
    equiv lemmas couple that state across the two equiv sides with
    ``(glob L){1} = (glob R){2}`` (idea 2 of the validated template,
    ``tests/integration/ec_templates/multi_oracle_indist.ec``): ``hop_<i>_init``
    establishes it from ``true`` and every post-init oracle preserves it.

    This is the **identical-state** (easy) form of the coupling -- correct
    precisely when the two games' globals line up field-by-field (e.g. both
    sides are the same game with one oracle body transformed). The
    differently-named-field correspondence for inlining hops between
    non-identical-state games is the coupling-synthesis research piece (P5,
    section 3 of the multi-oracle foundation plan); until it lands those hops
    stay on guided admit.
    """
    return f"(glob {left_module_expr})" "{1}" f" = (glob {right_module_expr})" "{2}"


def module_base_name(module_expr: str) -> str:
    """Return a module expression's base name (everything before its args).

    ``G_RandKey(K, F)`` -> ``G_RandKey``;
    ``R_KEM(K, F, KEMPRF(K, F), K_c.X(K))`` -> ``R_KEM``;
    ``R_MultiPRF`` (no args) -> ``R_MultiPRF``. The base name keeps any clone
    qualifier (``KF_c.KEM_INDCPA_MultiChal_Real``); only the outermost
    argument list is stripped.
    """
    head, _, _ = module_expr.partition("(")
    return head.strip()


def last_module_arg(module_expr: str) -> str:
    """Return the last top-level argument of ``module_expr``'s outermost args.

    Used to reach the challenger sub-module of a stateless reduction endpoint
    (``R_KEM(..., K_c.KEM_INDCPA_MultiChal_Random(K))`` ->
    ``K_c.KEM_INDCPA_MultiChal_Random(K)``). Splits on the top-level comma
    inside the outermost parentheses, respecting nested parens.
    """
    open_idx = module_expr.find("(")
    if open_idx == -1:
        return module_expr.strip()
    # Find the matching close for the outermost open paren.
    depth = 0
    inner = ""
    for ch in module_expr[open_idx:]:
        if ch == "(":
            depth += 1
            if depth == 1:
                continue
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        inner += ch
    # Split ``inner`` on top-level commas.
    args: list[str] = []
    depth = 0
    cur = ""
    for ch in inner:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur)
            cur = ""
        else:
            cur += ch
    args.append(cur)
    return args[-1].strip()


def live_state_coupling(left_field_ref: str, right_field_ref: str) -> str:
    """Return the live-state field coupling ``<L>{1} = <R>{2}``.

    Unlike :func:`coupling_invariant` (a whole-``glob`` equality, ill-typed
    when the two endpoints carry structurally different module state), this
    couples only the shared *live* state by naming the field directly on the
    module that holds it -- well-typed even when one side carries a dead field
    the other lacks (validated EC template
    ``tests/integration/ec_templates/multi_oracle_deadfield_coupling.ec``).
    ``left_field_ref``/``right_field_ref`` are field-qualified module
    references such as ``K_c.KEM_INDCPA_MultiChal_Random.pk`` or
    ``G_RandKey.pk``.
    """
    return f"{left_field_ref}" "{1}" f" = {right_field_ref}" "{2}"


class StepResolver:
    """Resolve a FrogLang proof step to its EC module expression.

    Lemmas are specialized to the concrete scheme (passed as
    ``scheme_name``) rather than parameterized over an abstract primitive
    module. This is required because the engine's canonicalization
    inlines scheme methods, and EC-level tactics (``rnd``, ``auto``)
    cannot reason about abstract primitive calls.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        module_name_by_concrete_game: dict[tuple[str, str], str],
        oracle_name_by_game_file: dict[str, str],
        primitive_name: str,
        scheme_name: str,
        oracle_params_by_game_file: dict[str, list[str]] | None = None,
        oracle_params_by_reduction: dict[str, list[str]] | None = None,
        instance_module_expr_by_let_name: dict[str, str] | None = None,
        module_name_by_instance_game: dict[tuple[str, str, str], str] | None = None,
        declared_module_names: list[str] | None = None,
        outer_oracle_name: str | None = None,
        oracle_model_by_game_file: (
            dict[str, oracle_model.GameOracleModel] | None
        ) = None,
        oracle_params_by_oracle: dict[str, dict[str, list[str]]] | None = None,
        outer_game_file_name: str | None = None,
    ) -> None:
        self._module_names = module_name_by_concrete_game
        self._oracle_names = oracle_name_by_game_file
        self._primitive_name = primitive_name
        self._scheme_name = scheme_name
        self._oracle_params = oracle_params_by_game_file or {}
        self._reduction_params = oracle_params_by_reduction or {}
        # In multi-primitive proofs a composed reduction
        # ``R compose <Inner>`` exposes the OUTER (theorem game's) oracle
        # method, not the inner challenger's. ``outer_oracle_name`` lets
        # the resolver emit the right method name for composed steps. For
        # plain (non-composed) steps the per-game-file oracle is correct
        # and ``outer_oracle_name`` is ignored. ``None`` preserves the
        # legacy single-primitive behavior where inner == outer.
        self._outer_oracle_name = outer_oracle_name
        # Multi-instance mode: when these are provided, ``resolve`` uses
        # per-instance clone-qualified module names and instance module
        # expressions.
        self._instance_module_expr = instance_module_expr_by_let_name or {}
        self._module_name_by_instance_game = module_name_by_instance_game or {}
        # Names of section-level ``declare module`` parameters. Reserved
        # for future multi-module tactic emission (``glob X`` equalities
        # and wrapper-level call invariants); not used by the current
        # precondition/postcondition emission.
        self._declared_modules = declared_module_names or []  # noqa: F841
        # Full oracle data model per game file (ordered names + init/post-init
        # split; see ``oracle_model``). Consumed by ``oracle_model_for`` to
        # drive the multi-oracle per-oracle equiv-lemma emission (P3); the
        # single-oracle resolution still keys off the scalar
        # ``oracle_name_by_game_file``.
        self._oracle_models = oracle_model_by_game_file or {}
        # Per-oracle precondition parameters: game file -> oracle name ->
        # ordered EC parameter names. Used by ``precondition_for`` when an
        # ``oracle_name`` is supplied (multi-oracle post-init oracles each
        # have their own argument signature, unlike the single-oracle path
        # which uses the first method's params). Empty -> ``precondition_for``
        # falls back to the scalar (first-method) params, so single-oracle
        # output is unchanged.
        self._oracle_params_by_oracle = oracle_params_by_oracle or {}
        # Theorem (outer) game file name. A composed step (``Game.Side compose
        # R``) and a bare intermediate game (``ParameterizedGame``) are both
        # played against the OUTER adversary, so their multi-oracle-ness is
        # the theorem game's, not the inner challenger's (which may be
        # single-oracle, e.g. PRFSecurity_MultiKey, or unregistered, e.g. a
        # synthetic intermediate game). Mirrors ``_wrapper_game_file_for`` in
        # the exporter, keeping ``oracle_model_for`` consistent with the
        # multi-oracle Pr-lemma builder.
        self._outer_game_file_name = outer_game_file_name

    def precondition_for(
        self, step: frog_ast.Step, oracle_name: str | None = None
    ) -> str:
        """Return the EC precondition: ``={arg1, arg2, ...}`` or ``true``.

        A composed step ``Game.Side compose R`` exposes the reduction's
        outer signature; use the reduction's params. A plain step
        ``Game.Side`` exposes the game's own signature.

        ``oracle_name`` selects a specific oracle's argument signature for
        the multi-oracle per-oracle equiv lemmas (P3): each post-init oracle
        has its own parameters, so ``hop_<i>_<m>``'s precondition uses
        ``m``'s params, not the first method's. When ``oracle_name`` is
        ``None`` (the single-oracle path) or no per-oracle params are
        registered for it, the legacy first-method params apply, so
        single-oracle output is unchanged.
        """
        if step.reduction is not None:
            params = self._reduction_params.get(step.reduction.name, [])
        else:
            concrete = step.challenger
            if isinstance(concrete, frog_ast.ParameterizedGame):
                # Bare intermediate game: played against the outer adversary,
                # so it exposes the theorem game's oracle signature. Keying the
                # precondition off the *outer* game file (rather than returning
                # ``true``) keeps ``={mL, mR, ...}`` in scope through the hop's
                # micro-lemma chain -- a uniform-simplification ``rnd`` bijection
                # on a message-dependent ciphertext needs the message equal on
                # both sides.
                game_key = self._outer_game_file_name
                if game_key is None:
                    return "true"
            elif not isinstance(concrete, frog_ast.ConcreteGame):
                return "true"
            else:
                game_key = concrete.game.name
            per_oracle = self._oracle_params_by_oracle.get(game_key, {})
            if oracle_name is not None and oracle_name in per_oracle:
                params = per_oracle[oracle_name]
            else:
                params = self._oracle_params.get(game_key, [])
        if not params:
            return "true"
        return "={" + ", ".join(params) + "}"

    def oracle_model_for(
        self, step: frog_ast.Step
    ) -> oracle_model.GameOracleModel | None:
        """Return the oracle data model for a step's game file, if known.

        Used by :func:`translate_hops` to decide whether a hop is
        multi-oracle (``Initialize`` lifted into ``main`` plus post-init
        oracles) and, if so, which per-oracle equiv lemmas to emit.

        The model must match what the step's ``Game_step_<i>`` wrapper lifts
        (see ``_wrapper_game_file_for`` in the exporter):

        - A **plain** step (``ConcreteGame`` with no reduction) exposes its
          own game file's oracle, so it is keyed by that game file.
        - A **composed** step (``ConcreteGame`` with a reduction) and a bare
          **intermediate game** (``ParameterizedGame``) are both played
          against the OUTER (theorem) adversary, so they are keyed by the
          theorem game file. The inner challenger may be single-oracle (e.g.
          ``PRFSecurity_MultiKey``) or unregistered (a synthetic intermediate
          game), so keying off it would wrongly route these hops to the
          single-oracle path -- inconsistent with the multi-oracle Pr lemma
          that references their per-oracle ``hop_<i>_<m>`` lemmas.

        Returns ``None`` for any other step or a game with no registered
        model -- both of which take the single-oracle path.
        """
        concrete = step.challenger
        if isinstance(concrete, frog_ast.ParameterizedGame):
            # Bare intermediate game: played against the outer adversary.
            if self._outer_game_file_name is not None:
                return self._oracle_models.get(self._outer_game_file_name)
            return self._oracle_models.get(concrete.name)
        if not isinstance(concrete, frog_ast.ConcreteGame):
            return None
        if step.reduction is not None and self._outer_game_file_name is not None:
            # Composed step: the wrapper lifts the theorem game's oracle.
            return self._oracle_models.get(self._outer_game_file_name)
        return self._oracle_models.get(concrete.game.name)

    @property
    def primitive_name(self) -> str:
        return self._primitive_name

    @property
    def scheme_name(self) -> str:
        return self._scheme_name

    def resolve(self, step: frog_ast.Step) -> ResolvedStep:
        concrete = step.challenger
        if isinstance(concrete, frog_ast.ParameterizedGame):
            return self._resolve_intermediate_game(concrete)
        if not isinstance(concrete, frog_ast.ConcreteGame):
            raise NotImplementedError(
                f"Only ConcreteGame steps are supported; got {type(concrete).__name__}"
            )
        game_file_name = concrete.game.name
        side = concrete.which
        # Composed steps expose the outer (theorem game's) oracle. Plain
        # steps expose their own game's oracle.
        if step.reduction is not None and self._outer_oracle_name is not None:
            oracle = self._outer_oracle_name
        else:
            oracle = self._oracle_names[game_file_name]

        if self._instance_module_expr:
            # Multi-instance mode.
            if not concrete.game.args or not isinstance(
                concrete.game.args[0], frog_ast.Variable
            ):
                raise ValueError(
                    f"Step's challenger {concrete.game.name} has no instance argument."
                )
            inst_let_name = concrete.game.args[0].name
            inst_expr = self._instance_module_expr[inst_let_name]
            key3 = (inst_let_name, game_file_name, side)
            if key3 not in self._module_name_by_instance_game:
                raise ValueError(
                    f"Step references unknown instance/game side: "
                    f"{inst_let_name}/{game_file_name}.{side}"
                )
            module_name = self._module_name_by_instance_game[key3]
            game_module_expr = f"{module_name}({inst_expr})"
            if step.reduction is None:
                return ResolvedStep(module_expr=game_module_expr, oracle_name=oracle)
            red = step.reduction
            # Only module-instance arguments are passed to the reduction
            # functor; value arguments (``Int pk1len`` compile-time indices,
            # literals) are dropped, mirroring ``_resolve_intermediate_game``
            # and the reduction's own module-typed-param functor signature
            # (see ``module_translator.translate_reduction``).
            red_arg_exprs: list[str] = [
                self._instance_module_expr[a.name]
                for a in red.args
                if isinstance(a, frog_ast.Variable)
                and a.name in self._instance_module_expr
            ]
            module_expr = f"{red.name}({', '.join(red_arg_exprs)}, {game_module_expr})"
            return ResolvedStep(module_expr=module_expr, oracle_name=oracle)

        key = (game_file_name, side)
        if key not in self._module_names:
            raise ValueError(
                f"Step references unknown game side: {game_file_name}.{side}"
            )
        game_module_expr = f"{self._module_names[key]}({self._scheme_name})"

        if step.reduction is None:
            return ResolvedStep(module_expr=game_module_expr, oracle_name=oracle)

        red = step.reduction
        module_expr = f"{red.name}({self._scheme_name}, {game_module_expr})"
        return ResolvedStep(module_expr=module_expr, oracle_name=oracle)

    def _resolve_intermediate_game(
        self, game: frog_ast.ParameterizedGame
    ) -> ResolvedStep:
        """Resolve a bare intermediate-game step (``G_RandKey(K, F)``).

        An intermediate game has no ``.Real``/``.Random`` side and carries no
        reduction: it is a synthetic game (defined in the proof's ``helpers``)
        played directly against the **outer (theorem) adversary**, so it
        exposes the theorem game's oracle interface. Its EC module is a functor
        applied to its primitive-instance arguments only: each ``Variable`` arg
        bound to a known scheme instance is routed through the instance table;
        non-instance arguments (``Int q`` compile-time indices, literals) are
        dropped, mirroring the scheme functor-param convention. A game with no
        module arguments (e.g. ``Hyb(q)``) therefore renders as a bare module
        reference (``Hyb``).
        """
        arg_exprs: list[str] = [
            self._instance_module_expr[a.name]
            for a in game.args
            if isinstance(a, frog_ast.Variable) and a.name in self._instance_module_expr
        ]
        module_expr = f"{game.name}({', '.join(arg_exprs)})" if arg_exprs else game.name
        # Played against the outer adversary -> the theorem game's oracle. Fall
        # back to a per-game-file scalar name (single-primitive intermediate
        # games with no outer-oracle override).
        oracle = self._outer_oracle_name or self._oracle_names.get(game.name, "main")
        return ResolvedStep(module_expr=module_expr, oracle_name=oracle)


def translate_assumption_axioms_theory(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    assumption_name: str,
    adversary_type_name: str,
    scheme_type_name: str,
    scheme_param_name: str,
    real_wrapper_name: str,
    random_wrapper_name: str,
) -> list[ec_ast.EcTopDecl]:
    """Emit Style B advantage axiom declarations for inside-theory use.

    The advantage axiom quantifies over the abstract scheme instance
    (``<scheme_param_name> <: <scheme_type_name>``) and the adversary, so
    that after the theory is cloned the axiom applies to any concrete
    scheme the clone binds.

    ProofFrog primitives model functional cryptographic operations
    (PRGs, hash functions, encryption schemes) whose abstract module
    type carries no mutable globals — the adversary is allowed to
    compute the primitive itself on inputs of its choosing in the
    cryptographic literature. So we do NOT impose a ``{-<scheme>}``
    separation restriction on the adversary inside the axiom; that
    restriction would block legitimate reductions (e.g. PRG hybrids
    where the reduction evaluates the PRG itself for un-hybridized
    positions) without adding any cryptographic content. Per-lemma
    ``{-<scheme>}`` restrictions on the *lemma's* adversary remain in
    place where the lemma's byequiv-sim chain needs them.

    Returns ``[op eps_<name>, axiom eps_<name>_pos, axiom <name>_advantage]``.
    """
    eps_name = f"eps_{assumption_name}"
    advantage_name = f"{assumption_name}_advantage"
    pos_axiom_name = f"{eps_name}_pos"
    formula = (
        f"`| Pr[{real_wrapper_name}({scheme_param_name}, A).main() @ &m : res]"
        f" - Pr[{random_wrapper_name}({scheme_param_name}, A).main() @ &m : res] |"
        f" <= {eps_name}"
    )
    return [
        ec_ast.OpDecl(name=eps_name, signature="real"),
        ec_ast.Axiom(
            name=pos_axiom_name,
            formula=f"0%r <= {eps_name}",
        ),
        ec_ast.Axiom(
            name=advantage_name,
            formula=formula,
            module_args=[
                ec_ast.ModuleParam(
                    name=scheme_param_name, module_type=scheme_type_name
                ),
                ec_ast.ModuleParam(name="A", module_type=adversary_type_name),
            ],
            memory_args=["&m"],
        ),
    ]


def _wrap_apply(wrapper: str, extra_args: list[str] | None) -> str:
    """Return ``Wrapper(E1, E2, A)`` when extra args present, else ``Wrapper(A)``."""
    if extra_args:
        return f"{wrapper}({', '.join(extra_args)}, A)"
    return f"{wrapper}(A)"


def translate_inlining_hop_pr_lemma(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    hop_index: int,
    adversary_type_name: str,
    scheme_module_expr: str,
    left_wrapper_name: str,
    right_wrapper_name: str,
    scheme_footprint: str | None = None,
    wrapper_extra_args: list[str] | None = None,
    glob_invariant_modules: list[str] | None = None,
    multi_oracle: MultiOraclePrSpec | None = None,
    adv_state_restrictions: list[str] | None = None,
) -> ec_ast.ProbLemma:
    """Emit a ``hop_<i>_pr`` lemma for an inlining hop.

    The proof discharges ``Pr[L] = Pr[R]`` via ``byequiv`` over the
    existing ``hop_<i>`` equiv lemma.

    When ``glob_invariant_modules`` is non-empty (multi-module proofs
    where ``hop_<i>``'s spec is strengthened with ``={glob X1, ...}``),
    the adversary ``call`` is given ``(_: ={glob X1, ...})`` as its
    preserved invariant so the resulting oracle subgoal has the
    strengthened pre/post that ``conseq hop_<i>`` can directly unify
    with.

    **Multi-oracle hops (P4).** When ``multi_oracle`` is supplied the hop is
    a lifted-``Initialize`` multi-oracle hop and the body is the validated
    section-2.4 template: one ``call (_: <coupling>)`` over the adversary,
    one ``conseq hop_<i>_<m>`` per post-init oracle (module-type declaration
    order), then ``call hop_<i>_<init>; auto`` for the lifted init. This
    references the per-oracle equiv lemmas that :func:`translate_hops` emits
    (``hop_<i>_<oracle>``) rather than the single-oracle ``hop_<i>``.
    ``multi_oracle`` takes precedence over ``glob_invariant_modules`` (a
    multi-oracle hop never also takes the single-oracle ``={glob X}``-
    strengthened path).

    **Abstract-scheme footprint (M5 blocker A).** When ``adv_state_restrictions``
    is supplied (only on the multi-oracle path), each named state-holding module
    is added to the adversary's footprint (``{-K, -F, -G_RandKey, ...}``). The
    multi-oracle Pr body's ``call (_: <live-state coupling>)`` is rejected by EC
    unless the adversary is restricted from the modules whose fields the coupling
    names -- an unrestricted abstract adversary is assumed to write every in-scope
    global. Validated by
    ``tests/integration/ec_templates/multi_oracle_abstract_call_coupling.ec``.
    """
    left_app = _wrap_apply(left_wrapper_name, wrapper_extra_args)
    right_app = _wrap_apply(right_wrapper_name, wrapper_extra_args)
    statement = (
        f"Pr[{left_app}.main() @ &m : res]" f" = Pr[{right_app}.main() @ &m : res]"
    )
    if multi_oracle is not None:
        body = [
            f"byequiv (_: {multi_oracle.byequiv_pre} ==> ={{res}}) => //.",
            "proc.",
            f"call (_: {multi_oracle.coupling}).",
            *[f"+ conseq hop_{hop_index}_{m}." for m in multi_oracle.post_init_oracles],
            f"call hop_{hop_index}_{multi_oracle.init_oracle}.",
            "auto.",
            "qed.",
        ]
        footprint = (
            scheme_footprint
            if scheme_footprint is not None
            else f"-{scheme_module_expr}"
        )
        if adv_state_restrictions:
            footprint = (
                footprint + ", " + ", ".join(f"-{m}" for m in adv_state_restrictions)
            )
        return ec_ast.ProbLemma(
            name=f"hop_{hop_index}_pr",
            module_args=[
                ec_ast.ModuleParam(
                    name="A",
                    module_type=f"{adversary_type_name} {{{footprint}}}",
                )
            ],
            memory_args=["&m"],
            statement=statement,
            body=body,
        )
    if glob_invariant_modules:
        invariant = "={" + ", ".join(f"glob {m}" for m in glob_invariant_modules) + "}"
        # Force the byequiv-introduced precondition to include each
        # declared-module ``glob`` even when EC's heuristic would omit
        # it (e.g. the right-hand module discards the parameter). Without
        # this, ``call (_: ={glob X1, ..., glob Xn})`` is unprovable in
        # the byequiv side condition.
        byequiv_pre = (
            "={glob A, " + ", ".join(f"glob {m}" for m in glob_invariant_modules) + "}"
        )
        byequiv_step = f"byequiv (_: {byequiv_pre} ==> ={{res}}) => //; proc."
        call_step = f"call (_: {invariant}); first by conseq hop_{hop_index}."
    else:
        byequiv_step = "byequiv => //; proc."
        call_step = f"call (_: true); first by conseq hop_{hop_index}."
    body = [
        byequiv_step,
        call_step,
        "auto.",
        "qed.",
    ]
    footprint = (
        scheme_footprint if scheme_footprint is not None else f"-{scheme_module_expr}"
    )
    return ec_ast.ProbLemma(
        name=f"hop_{hop_index}_pr",
        module_args=[
            ec_ast.ModuleParam(
                name="A",
                module_type=f"{adversary_type_name} {{{footprint}}}",
            )
        ],
        memory_args=["&m"],
        statement=statement,
        body=body,
    )


def translate_assumption_hop_pr_lemma(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    hop_index: int,
    adversary_type_name: str,
    scheme_module_expr: str,
    left_wrapper_name: str,
    right_wrapper_name: str,
    assumption_name: str,
    reduction_adv_name: str,
    left_assumption_wrapper: str,
    right_assumption_wrapper: str,
    reverse_direction: bool,
    clone_alias: str | None = None,
    scheme_footprint: str | None = None,
    reduction_adv_extra_args: list[str] | None = None,
    wrapper_extra_args: list[str] | None = None,
    multi_oracle: MultiOraclePrSpec | None = None,
    adv_state_restrictions: list[str] | None = None,
) -> ec_ast.ProbLemma:
    """Emit a ``hop_<i>_pr`` lemma for an assumption hop.

    The proof rewrites each side to the corresponding assumption-game
    wrapper instantiated on the reduction-adversary lift, then applies
    the advantage axiom. When ``reverse_direction`` is true the hop goes
    Random->Real (opposite of the axiom) and we normalize via absolute-
    value symmetry before applying the axiom.

    ``reduction_adv_extra_args`` supplies extra module arguments that
    the reduction-adversary wrapper takes before ``A`` (e.g. declared
    module instances ``E1, E2``).

    **Multi-oracle hops (P4/M5).** When ``multi_oracle`` is supplied the two
    wrapper-rewrite bridges (``hL``/``hR``) relate a lifted-``Initialize``
    multi-oracle game wrapper (``Game_step_i``) to its assumption-game wrapper
    instantiated on the reduction-adversary lift. Despite the conservative
    "differently-named state" framing of earlier phases, the bridge is in fact
    *name-independent*: after ``inline *`` both sides reduce to the literally
    same state module (the reduction ``R`` forwards into / is the only stateful
    holder, shared by both wrappers), so ``byequiv (_: <pre> ==> ={res}) => //;
    proc; inline *; sim`` closes it with no inline-generated names in the
    tactic. The one requirement is that ``A`` be separated from those state
    modules (see ``adv_state_restrictions`` below); EC otherwise assumes the
    abstract adversary may write the challenger's globals and rejects the
    ``sim`` frame. Validated end-to-end on ``KEMPRF_INDCPA`` (both the
    ``KEM_INDCPA_MultiChal`` and ``PRFSecurity_MultiKey`` hops close to ``qed``,
    EC exit 0). This is the M5 "clean" close -- the lemma is admit-free.

    **Abstract-scheme footprint (M5).** When ``adv_state_restrictions`` is
    supplied (only on the multi-oracle path), each named state-holding module is
    added to the adversary's footprint, mirroring
    :func:`translate_inlining_hop_pr_lemma`. The bridge's ``sim`` is rejected by
    EC unless the adversary is restricted from the challenger/reduction state
    modules. ``main_theorem`` already restricts ``A`` from the full set, so the
    widened footprint here is a subset and the ``have h<i> := hop_<i>_pr A``
    application still typechecks.
    """
    prefix = f"{clone_alias}." if clone_alias else ""
    eps_ref = f"{prefix}eps_{assumption_name}"
    advantage_ref = f"{prefix}{assumption_name}_advantage"
    left_wrapper_ref = f"{prefix}{left_assumption_wrapper}"
    right_wrapper_ref = f"{prefix}{right_assumption_wrapper}"
    extra = ", ".join(reduction_adv_extra_args) if reduction_adv_extra_args else ""
    adv_applied = (
        f"{reduction_adv_name}({extra}, A)" if extra else f"{reduction_adv_name}(A)"
    )
    # When the scheme instance is a concretized functor application (e.g.
    # ``PseudoOTP(G)``), it must be parenthesized where it is passed as a
    # bare proof-term module argument to the advantage axiom — otherwise EC
    # parses ``PseudoOTP`` (the functor) as the argument and ``(G)`` as the
    # next one ("incompatible module type"). A plain module name is left as-is.
    scheme_module_arg = (
        f"({scheme_module_expr})" if "(" in scheme_module_expr else scheme_module_expr
    )
    left_app = _wrap_apply(left_wrapper_name, wrapper_extra_args)
    right_app = _wrap_apply(right_wrapper_name, wrapper_extra_args)
    statement = (
        f"`| Pr[{left_app}.main() @ &m : res]"
        f" - Pr[{right_app}.main() @ &m : res] |"
        f" <= {eps_ref}"
    )
    if multi_oracle is not None:
        bridge_close = (
            f"  by byequiv (_: {multi_oracle.byequiv_pre} ==> ={{res}}) => //; "
            "proc; inline *; sim."
        )
        body = [
            f"have hL : Pr[{left_app}.main() @ &m : res]",
            f"        = Pr[{left_wrapper_ref}({scheme_module_expr}, "
            f"{adv_applied}).main() @ &m : res]",
            bridge_close,
            f"have hR : Pr[{right_app}.main() @ &m : res]",
            f"        = Pr[{right_wrapper_ref}({scheme_module_expr}, "
            f"{adv_applied}).main() @ &m : res]",
            bridge_close,
            "rewrite hL hR.",
        ]
    else:
        body = [
            f"have hL : Pr[{left_app}.main() @ &m : res]",
            f"        = Pr[{left_wrapper_ref}({scheme_module_expr}, "
            f"{adv_applied}).main() @ &m : res]",
            "  by byequiv => //; proc; inline *; sim.",
            f"have hR : Pr[{right_app}.main() @ &m : res]",
            f"        = Pr[{right_wrapper_ref}({scheme_module_expr}, "
            f"{adv_applied}).main() @ &m : res]",
            "  by byequiv => //; proc; inline *; sim.",
            "rewrite hL hR.",
        ]
    if reverse_direction:
        body.extend(
            [
                f"have H := {advantage_ref} {scheme_module_arg} "
                f"({adv_applied}) &m.",
                "smt().",
            ]
        )
    else:
        body.append(
            f"apply ({advantage_ref} {scheme_module_arg} " f"({adv_applied}) &m)."
        )
    body.append("qed.")
    footprint = (
        scheme_footprint if scheme_footprint is not None else f"-{scheme_module_expr}"
    )
    if multi_oracle is not None and adv_state_restrictions:
        footprint = (
            footprint + ", " + ", ".join(f"-{m}" for m in adv_state_restrictions)
        )
    return ec_ast.ProbLemma(
        name=f"hop_{hop_index}_pr",
        module_args=[
            ec_ast.ModuleParam(
                name="A",
                module_type=f"{adversary_type_name} {{{footprint}}}",
            )
        ],
        memory_args=["&m"],
        statement=statement,
        body=body,
    )


def translate_main_theorem(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    adversary_type_name: str,
    scheme_module_expr: str,
    first_wrapper_name: str,
    last_wrapper_name: str,
    hop_kinds: list[HopKind],
    assumption_names_by_hop: dict[int, str],
    n_hops: int,
    clone_alias: str | None = None,
    assumption_clone_by_hop: dict[int, str] | None = None,
    scheme_footprint: str | None = None,
    wrapper_extra_args: list[str] | None = None,
    adv_state_restrictions: list[str] | None = None,
) -> ec_ast.ProbLemma:
    """Emit the chained main theorem for a sequence of hops.

    The bound is the sum of ``eps_<name>`` for each assumption hop;
    inlining hops contribute zero. If there are no assumption hops, the
    statement is an equality (``Pr[L] = Pr[R]``) rather than a bound.

    ``adv_state_restrictions`` (multi-oracle path only) adds the state-holding
    modules named in the per-hop live-state couplings to ``A``'s footprint, so
    that ``A`` satisfies the (stronger) restriction each ``hop_<i>_pr`` requires
    of its adversary -- otherwise ``have h<i> := hop_<i>_pr A`` is rejected
    because ``main_theorem``'s ``A`` could use a coupled state module.
    """
    default_prefix = f"{clone_alias}." if clone_alias else ""
    per_hop_clones = assumption_clone_by_hop or {}

    def _prefix_for(hop_index: int) -> str:
        override = per_hop_clones.get(hop_index)
        if override:
            return f"{override}."
        return default_prefix

    eps_terms: list[str] = []
    for i, kind in enumerate(hop_kinds):
        if kind is HopKind.ASSUMPTION:
            eps_terms.append(f"{_prefix_for(i)}eps_{assumption_names_by_hop[i]}")

    first_app = _wrap_apply(first_wrapper_name, wrapper_extra_args)
    last_app = _wrap_apply(last_wrapper_name, wrapper_extra_args)
    have_lines = [f"have h{i} := hop_{i}_pr A &m." for i in range(n_hops)]
    if not eps_terms:
        statement = (
            f"Pr[{first_app}.main() @ &m : res]" f" = Pr[{last_app}.main() @ &m : res]"
        )
        body = [*have_lines, "smt().", "qed."]
    else:
        bound = " + ".join(eps_terms)
        statement = (
            f"`| Pr[{first_app}.main() @ &m : res]"
            f" - Pr[{last_app}.main() @ &m : res] |"
            f" <= {bound}"
        )
        pos_args_set = {
            f"{_prefix_for(i)}eps_{assumption_names_by_hop[i]}_pos"
            for i, kind in enumerate(hop_kinds)
            if kind is HopKind.ASSUMPTION
        }
        pos_args = " ".join(sorted(pos_args_set))
        body = [*have_lines, f"smt({pos_args}).", "qed."]

    footprint = (
        scheme_footprint if scheme_footprint is not None else f"-{scheme_module_expr}"
    )
    if adv_state_restrictions:
        footprint = (
            footprint + ", " + ", ".join(f"-{m}" for m in adv_state_restrictions)
        )
    return ec_ast.ProbLemma(
        name="main_theorem",
        module_args=[
            ec_ast.ModuleParam(
                name="A",
                module_type=f"{adversary_type_name} {{{footprint}}}",
            )
        ],
        memory_args=["&m"],
        statement=statement,
        body=body,
    )


def translate_hops(  # pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
    resolver: StepResolver,
    steps: list[frog_ast.ProofStep],
    body_for_hop: Callable[[int, frog_ast.Step, frog_ast.Step], list[str] | None],
    spec_overrides: dict[int, tuple[str, str]] | None = None,
    oracle_body_for_hop: (
        Callable[[int, frog_ast.Step, frog_ast.Step, str, bool], list[str] | None]
        | None
    ) = None,
    coupling_for_hop: Callable[[frog_ast.Step, frog_ast.Step], str] | None = None,
    glob_invariant: str = "",
) -> list[ec_ast.Lemma]:
    """Produce the equiv lemma(s) per adjacent-step pair.

    ``body_for_hop(i, step_a, step_b)`` returns the list of tactic lines
    (ending with ``"qed."``) for hop ``i``, or ``None`` to skip the
    equiv lemma entirely for that hop (e.g. for assumption hops whose
    two sides are genuinely non-equivalent).

    ``spec_overrides[i] = (precondition, postcondition)`` (if present)
    replaces the default ``={oracle_params}``/``={res}`` for hop ``i``.
    The per-transform exporter sets this in multi-module proofs to
    strengthen the spec with ``={glob E1, glob E2, ...}``.

    **Multi-oracle hops (P3).** When ``oracle_body_for_hop`` is supplied
    *and* the hop's game file is multi-oracle (an ``Initialize`` lifted into
    ``main`` plus one or more post-init oracles -- see
    :meth:`StepResolver.oracle_model_for`), the hop emits **one equiv lemma
    per oracle** instead of the single ``hop_<i>``:

    - ``hop_<i>_<init>`` establishes the state-coupling invariant
      ``(glob L){1} = (glob R){2}`` from ``true`` (postcondition
      ``={res} /\\ <coupling>``);
    - each ``hop_<i>_<m>`` (post-init oracle ``m``, in module-type
      declaration order) *preserves* it (pre and post both carry the
      coupling, pre also carries ``m``'s argument equality).

    ``oracle_body_for_hop(i, a, b, oracle_name, is_init)`` returns that
    oracle's tactic body (or ``None`` to skip the lemma). Single-oracle
    hops -- and every hop when ``oracle_body_for_hop`` is ``None`` -- take
    the legacy single-lemma path, so single-oracle output is unchanged.

    ``coupling_for_hop(a, b)`` (if supplied) returns the per-hop state-coupling
    invariant string used in the per-oracle equiv lemmas, overriding the
    default whole-``glob`` :func:`coupling_invariant`. The exporter passes a
    *live-state* coupling here (a field equality on the shared live state) so
    the lemmas typecheck even when the two endpoints carry structurally
    different module state (M5; validated EC template
    ``tests/integration/ec_templates/multi_oracle_deadfield_coupling.ec``).

    ``glob_invariant`` (if supplied) is the abstract-scheme glob equality
    (e.g. ``={glob K} /\\ ={glob F}``) used as the init oracle's precondition
    in place of ``true``. ``sim`` needs ``={glob}`` on each called abstract
    module to relate its calls; ``Initialize`` calls ``K.keygen`` so its
    precondition must carry it. The post-init oracles' preconditions get it via
    ``coupling_for_hop`` (which folds the same glob equality into the coupling).
    """
    # NOTE: keep the original dict identity — the caller may mutate it
    # during ``body_for_hop`` calls (per-transform mode populates the
    # override during the per-hop chain emission). ``spec_overrides or {}``
    # would substitute a fresh empty dict if the caller passed in an
    # empty one, losing later mutations.
    overrides = spec_overrides if spec_overrides is not None else {}
    lemmas: list[ec_ast.Lemma] = []
    for i in range(len(steps) - 1):
        a, b = steps[i], steps[i + 1]
        if not isinstance(a, frog_ast.Step) or not isinstance(b, frog_ast.Step):
            raise NotImplementedError(
                "Only simple Step entries are supported (no Induction)."
            )
        model = (
            resolver.oracle_model_for(a) if oracle_body_for_hop is not None else None
        )
        if (
            oracle_body_for_hop is not None
            and model is not None
            and model.is_multi_oracle
        ):
            lemmas.extend(
                _multi_oracle_hop_lemmas(
                    resolver,
                    i,
                    a,
                    b,
                    model,
                    oracle_body_for_hop,
                    coupling_for_hop,
                    glob_invariant,
                )
            )
            continue
        body = body_for_hop(i, a, b)
        if body is None:
            continue
        ra = resolver.resolve(a)
        rb = resolver.resolve(b)
        pre, post = overrides.get(i, (resolver.precondition_for(a), "={res}"))
        lemmas.append(
            ec_ast.Lemma(
                name=f"hop_{i}",
                module_args=[],
                left=f"{ra.module_expr}.{ra.oracle_name}",
                right=f"{rb.module_expr}.{rb.oracle_name}",
                precondition=pre,
                postcondition=post,
                body=body,
            )
        )
    return lemmas


def _multi_oracle_hop_lemmas(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    resolver: StepResolver,
    hop_index: int,
    step_a: frog_ast.Step,
    step_b: frog_ast.Step,
    model: oracle_model.GameOracleModel,
    oracle_body_for_hop: Callable[
        [int, frog_ast.Step, frog_ast.Step, str, bool], list[str] | None
    ],
    coupling_for_hop: Callable[[frog_ast.Step, frog_ast.Step], str] | None = None,
    glob_invariant: str = "",
) -> list[ec_ast.Lemma]:
    """Emit the per-oracle equiv lemmas for one multi-oracle hop (P3).

    See :func:`translate_hops` for the lemma shapes. The init oracle is
    emitted first (establishes the coupling from ``true``), then each
    post-init oracle in declaration order (preserves the coupling).
    ``coupling_for_hop`` (if supplied) computes the live-state coupling
    string, overriding the default whole-``glob`` coupling.
    """
    ra = resolver.resolve(step_a)
    rb = resolver.resolve(step_b)
    if coupling_for_hop is not None:
        coupling = coupling_for_hop(step_a, step_b)
    else:
        coupling = coupling_invariant(ra.module_expr, rb.module_expr)
    # init first, then post-init oracles in module-type declaration order.
    assert model.init_name is not None  # is_multi_oracle guarantees this
    ordered: list[tuple[str, bool]] = [(model.init_name, True)]
    ordered += [(m, False) for m in model.post_init_names]
    lemmas: list[ec_ast.Lemma] = []
    for oracle_name, is_init in ordered:
        body = oracle_body_for_hop(hop_index, step_a, step_b, oracle_name, is_init)
        if body is None:
            continue
        if is_init:
            pre = glob_invariant if glob_invariant else "true"
        else:
            eq_args = resolver.precondition_for(step_a, oracle_name)
            pre = coupling if eq_args == "true" else f"{eq_args} /\\ {coupling}"
        lemmas.append(
            ec_ast.Lemma(
                name=f"hop_{hop_index}_{oracle_name}",
                module_args=[],
                left=f"{ra.module_expr}.{oracle_name}",
                right=f"{rb.module_expr}.{oracle_name}",
                precondition=pre,
                postcondition=f"={{res}} /\\ {coupling}",
                body=body,
            )
        )
    return lemmas
