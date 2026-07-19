"""Collect types used by an export and emit the corresponding EC declarations.

Walking skeleton scope: handles only BitString<expr> types. The length
expression is stringified via str() and sanitized to produce a valid EC
identifier.
"""

from __future__ import annotations

import re

from . import ec_ast
from ... import frog_ast


class TypeCollector:
    """Accumulates bitstring types seen during translation.

    Call ``translate_type(t)`` to get the EC type expression and register
    the type for later emission. Call ``emit()`` at the end to produce
    the corresponding top-level declarations.

    A type alias map lets the collector resolve ``Variable(name)`` and
    ``FieldAccess(obj, name)`` types by looking up ``name`` in the map.
    This is used to concretize primitive type aliases (``Key``,
    ``Ciphertext``) and game parameter types (``E.Key``) through the
    scheme's field definitions.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        aliases: dict[str, frog_ast.Type] | None = None,
        abstract_types: dict[str, str] | None = None,
        known_abstract_types: set[str] | None = None,
        strip_field_prefixes: set[str] | None = None,
        theory_mode: bool = False,
        prime_group_names: set[str] | None = None,
        ro_module_prefix: str = "",
    ) -> None:
        # Qualifier prepended to the random-oracle holder module name in REF
        # sites (``function_value_ref``/``function_value_modules``/
        # ``ro_by_arrow_type``) -- e.g. ``"Hybrid_c."`` so a top-level collector
        # references the SINGLE holder module the theorem-primitive theory clone
        # owns (``Hybrid_c.RO_H``) rather than declaring a distinct top-level copy.
        # A collector with a non-empty prefix does NOT emit the holder itself
        # (see :meth:`emit`); the abstract-theory collector (prefix ``""``) emits
        # it once. This keeps the RO a SINGLE shared module across the
        # theory/top-level boundary (a module cannot be clone-instantiated, so two
        # separately-emitted holders never unify). Set post-construction once the
        # theorem primitive's clone alias is known.
        self.ro_module_prefix: str = ro_module_prefix
        # Set by the statement translator when it emits an exclusion draw
        # (``x <- T \ {..}`` -> EC ``d \ P``), so the preamble emits
        # ``require import Dexcepted``. Conditional -> non-exclusion proofs stay
        # byte-identical.
        self.needs_dexcepted: bool = False
        # ``theory_mode``: when True, every distinct bitstring type seen
        # is registered as an abstract type inside the primitive's
        # abstract theory rather than as a top-level concrete type. Each
        # such type carries its original parameterization expression
        # (post-prefix-strip), so the exporter can compute per-instance
        # type bindings for each clone (e.g. ``G_c.bs_lambda_stretch <-
        # bs_2_lambda`` when G's stretch = lambda).
        self._theory_mode: bool = theory_mode
        # (abstract_name, original_parameterization) for each bitstring
        # registered while in theory mode. Order-preserving, deduped.
        self._abstract_bitstrings: list[tuple[str, frog_ast.Expression]] = []
        self._abstract_bitstring_names: set[str] = set()
        self._names: list[str] = []  # ordered, unique
        self._seen: set[str] = set()
        # Standalone ``ModInt<q>`` clone aliases (e.g. ``ModInt_q``), each
        # emitting one ``clone ZModP.ZModRing as <alias> with op p <- <q>``.
        # The EC type is ``<alias>.zmod``; ring ops + uniform distr come from
        # the stdlib (no per-type axioms). Order-preserving, deduped.
        self._modints: list[str] = []
        self._modint_set: set[str] = set()
        # Group clone aliases (the FrogLang ``Group <G>`` name, e.g. ``G``).
        # Each emits a ``clone CyclicGroup as <G>`` plus an exponent-ring
        # clone (prime: ``<G>.PowZMod``/``FDistr``; general: ``ZModRing as
        # <G>_Exp``). The group type is ``<G>.group``. Order-preserving,
        # deduped. ``_groupelem_exp`` records the EC exponent type
        # (``<G>_P.ZModE.exp`` prime / ``<G>_Exp.zmod`` general) per group.
        self._groupelems: list[str] = []
        self._groupelem_set: set[str] = set()
        self._groupelem_exp: dict[str, str] = {}
        # Uniform-distribution op for each registered exponent type and
        # standalone-ModInt type, keyed by the EC type string. Populated at
        # registration so ``distr_for`` resolves a sampled exponent / ModInt
        # without string surgery (prime exp -> ``<G>_FD.dt``; general exp /
        # standalone -> ``<theory>.DZmodP.dunifin``).
        self._exp_distrs: dict[str, str] = {}
        self._modint_distrs: dict[str, str] = {}
        # EC modulus expression for each standalone ``ModInt<q>`` clone,
        # keyed by clone alias (e.g. ``ModInt_q`` -> ``"q"``). Bound as the
        # ZModRing ``op p`` so the ring is Z_<modulus>, not Z_<abstract p>.
        self._modint_modulus: dict[str, str] = {}
        # Alias keys may be plain (``"Key"``) or qualified
        # (``"E1.key"``). Qualified keys resolve ``FieldAccess`` types
        # through per-instance scheme clones in multi-scheme exports.
        self._aliases: dict[str, frog_ast.Type] = dict(aliases) if aliases else {}
        # Object names whose ``FieldAccess`` prefixes should be stripped
        # from bitstring parameterization expressions. Used when emitting
        # game bodies inside the primitive's abstract theory: the game
        # parameter (e.g. ``G``) is a module parameter with no first-class
        # fields, so ``BitString<G.lambda + G.stretch>`` must collapse to
        # ``BitString<lambda + stretch>`` (= ``bs_lambda_stretch``) to
        # match the primitive-level abstract bitstring type.
        self._strip_field_prefixes: set[str] = (
            set(strip_field_prefixes) if strip_field_prefixes else set()
        )
        # Abstract-type mode: maps FrogLang type names (e.g. "Key", "Message")
        # to abstract EC identifiers (e.g. "key", "message"). Used when
        # emitting the contents of an abstract theory, where primitive-level
        # types stay abstract and are replaced at clone time.
        self._abstract_types: dict[str, str] = (
            dict(abstract_types) if abstract_types else {}
        )
        # Names of top-level abstract EC types declared outside the
        # theory (e.g. ``KeySpace1`` from a ``Set KeySpace1;`` let).
        # Referenced as ``Variable(name)`` in scheme field resolutions
        # and must translate to themselves.
        self._known_abstract_types: set[str] = (
            set(known_abstract_types) if known_abstract_types else set()
        )
        self._abstract_seen: list[str] = []
        self._abstract_distrs: list[str] = []
        # Known top-level abstract types that had a distribution
        # requested (via ``distr_for``). Each gets a ``d<name>``
        # declaration in :meth:`emit`.
        self._known_abstract_distrs: list[str] = []
        # Abstract slicing operators between bitstring types:
        # ``slice_<src>_to_<dst> : <src> -> int -> int -> <dst>``.
        # Registered on demand from the expression translator.
        # Order-preserving, deduped by (src, dst).
        self._slice_ops: list[tuple[str, str]] = []
        self._slice_op_set: set[tuple[str, str]] = set()
        # Abstract concatenation operators:
        # ``concat_<a>_<b>_to_<r> : <a> -> <b> -> <r>``.
        # Registered on demand for ``||`` on bitstring operands.
        # Order-preserving, deduped by (left, right, result).
        self._concat_ops: list[tuple[str, str, str]] = []
        self._concat_op_set: set[tuple[str, str, str]] = set()
        # Abstract 3-way concatenation operators:
        # ``concat3_<a>_<b>_<c>_to_<r> : <a> -> <b> -> <c> -> <r>``.
        # Registered on demand by the partial-split synthesizer to model
        # ``Split Uniform Samples`` applications whose two used slices
        # don't cover the full source bitstring (a third "gap" piece
        # collapses the bijection). The slice ops ``(<r>, <a>)``,
        # ``(<r>, <b>)``, ``(<r>, <c>)`` are auto-registered, and
        # :meth:`emit` produces three round-trip axioms plus a
        # dlet-form distribution-split axiom.
        # Order-preserving, deduped by (left, right, gap, result).
        self._concat3_ops: list[tuple[str, str, str, str]] = []
        self._concat3_op_set: set[tuple[str, str, str, str]] = set()
        # Per-bitstring canonical length expression string. Populated
        # whenever a bitstring is named via ``_bitstring_name``; used by
        # ``emit()`` / ``emit_abstract()`` to parameterize the
        # slice/concat round-trip axioms and distribution-split axioms
        # with the actual bit-length integer expressions.
        self._bs_lengths: dict[str, str] = {}
        # Bitstring type names that a ``requires``-equality clause unified
        # with an earlier-declared abstract type. ``emit()`` renders these
        # as ``type <name> = <definition>.`` aliases instead of fresh
        # abstract ``type <name>.`` declarations, so EC treats e.g.
        # ``bs_lambda`` and the KEM carrier ``SharedSecretSpace`` as one
        # type (the ``requires K.SharedSecret == BitString<F.lambda>`` gap).
        self._type_alias_defs: dict[str, str] = {}
        # Abstract carrier set names (e.g. ``PK1Space``) that a scheme
        # ``requires X subsets/== BitString<n>`` clause makes
        # bitstring-like, mapped to the ``BitString<n>`` type they unify
        # with. Operators defined only on bitstrings -- notably ``||``
        # concatenation -- treat such a carrier-typed operand as that
        # bitstring (the engine inlines the set->bs coercion in flat
        # states, so a concat operand can surface carrier-typed). Seeded
        # by the exporter before chain emission via
        # :meth:`register_subset_carrier` so the relationship is known when
        # flat-state bodies render (it precedes the late ``requires``
        # alias-emission pass).
        self._subset_carriers: dict[str, frog_ast.BitStringType] = {}
        # Function types ``Function<A, B>`` seen, sampled as random
        # functions (``RF <- Function<A, B>``; ``RF(x)`` applies them).
        # Each distinct (domain_ec, codomain_ec) pair gets an abstract
        # uniform distribution over the finite function space plus
        # lossless/funiform/full axioms -- the random-function analogue of
        # the bitstring ``dbs`` foundation. Sound: the uniform distribution
        # over a finite function space ``A -> B`` exists and is
        # constructible as ``dfun (fun _ => dB)`` (EC's ``MUniFinFun``);
        # the three axioms are the standard facts about it. Order-
        # preserving, deduped by (domain, codomain).
        self._function_types: list[tuple[str, str]] = []
        self._function_type_set: set[tuple[str, str]] = set()
        # Named ``Function<A,B>`` VALUES: a proof-level ``Function<D,R> H`` let /
        # game parameter is the fixed (shared) random-oracle function itself,
        # not a per-game sampled field. It is referenced as an operator (``v_H
        # m``) but, unlike a sampled ``RF`` field, no ``<$ dfun`` binds it -- so
        # its value needs an ``op`` declaration. Each entry ``(name, dom, codom)``
        # emits ``op <name> : dom -> codom`` (an abstract fixed function; the
        # random-oracle randomness the proof relies on is carried by the lazy-RO
        # assumption games, whose bounds are abstract ``eps`` ops).
        self._function_values: list[tuple[str, str, str]] = []
        self._function_value_set: set[str] = set()
        # Group names (FrogLang ``Group <G>`` parameters) for which the
        # proof declared ``requires <G>.order is prime;``. These get the
        # prime emission path (PowZMod field exponent + FDistr + a
        # ``prime <G>.order`` axiom); every other group gets the general
        # CyclicGroup + ZModRing path. Mirrors the engine's own gating
        # (``PipelineContext.has_prime_order_requirement``).
        self._prime_groups: set[str] = set(prime_group_names or ())
        # True once a FrogLang ``Map<K, V>`` type is translated (to EC's
        # ``(k, v) fmap``). Consulted so the export ``require``s ``SmtMap``
        # only when a finite map is actually used (byte-identical otherwise:
        # no map-free proof sets this).
        self._uses_map: bool = False

    def has_map(self) -> bool:
        """True if a FrogLang ``Map<K, V>`` type was translated, so the
        export must ``require import SmtMap``."""
        return self._uses_map

    def register_function_value(
        self, name: str, func_type: frog_ast.FunctionType
    ) -> None:
        """Register a named ``Function<A,B>`` VALUE (e.g. a ``Function<D,R> H``
        let / game param -- the shared random-oracle function). Translating the
        type also registers its ``dfun`` distribution; the ``op <name> : A -> B``
        declaration is emitted by :meth:`emit`. Deduped by name."""
        if name in self._function_value_set:
            return
        dom = self.translate_type(func_type.domain_type).text
        codom = self.translate_type(func_type.range_type).text
        self._function_value_set.add(name)
        self._function_values.append((name, dom, codom))

    def function_value_ref(self, fname: str) -> str | None:
        """If ``fname`` (an EC-mangled name like ``v_H``) is a registered
        random-oracle function VALUE, return its holder-module reference
        (``RO_H.h``); else ``None``. Used by the expression translator to render
        an RO application ``H(m)`` as ``RO_H.h m`` instead of the fixed-op
        ``v_H m``."""
        if fname in self._function_value_set:
            return f"{self.ro_module_prefix}{_ro_module_name(fname)}.h"
        return None

    def function_value_modules(self) -> list[tuple[str, str]]:
        """``(module_name, dfun_name)`` per registered RO function value, so the
        exporter can sample ``RO_H.h <$ dfun`` at each experiment's main."""
        return [
            (
                f"{self.ro_module_prefix}{_ro_module_name(fname)}",
                _function_distr_name(dom, codom),
            )
            for fname, dom, codom in self._function_values
        ]

    def ro_by_arrow_type(self) -> dict[str, str]:
        """``{arrow-type-text: holder-ref}`` per registered RO, e.g.
        ``{"d -> r": "RO_H.h"}``. A flat-state field of that arrow type is a
        materialized copy of the shared RO (assigned ``<- RO_H.h`` by
        :meth:`ro_ref_for_dfun`); the coupling uses this to add the within-side
        invariant ``field{side} = RO_H.h{side}`` so a hop that drops the field
        and reverts to the shared RO can thread the equality."""
        return {
            f"{dom} -> {codom}": f"{self.ro_module_prefix}{_ro_module_name(fname)}.h"
            for fname, dom, codom in self._function_values
        }

    def ro_ref_for_dfun(self, distr: str) -> str | None:
        """If ``distr`` is the function distribution of a registered shared RO,
        return that RO's holder ref (``RO_H.h``); else ``None``.

        A lazy-RO ASSUMPTION game (``LazyRO.Honest``) samples its OWN function
        field ``RF <- Function<D,R>`` and uses it as the oracle -- its "Honest
        view" IS the shared RO ``H``. So a Function-field sample from the RO's
        exact ``dfun`` is materializing the shared RO: assign ``RF <- RO_H.h``
        rather than sample independently, making ``RF = RO_H.h`` a true invariant
        (the ROM ``H``->fresh-RF rename, realized concretely). Only fires when a
        Function VALUE is registered (ROM proofs); byte-identical otherwise."""
        for mod_name, dfun in self.function_value_modules():
            if dfun == distr:
                return f"{mod_name}.h"
        return None

    def is_prime_group(self, group_name: str) -> bool:
        """True if the proof declared ``requires <group>.order is prime;``."""
        return group_name in self._prime_groups

    def has_stdlib_group_or_modint(self) -> bool:
        """True if a ``GroupElem<G>`` or standalone ``ModInt<q>`` was
        registered, so the export must ``require`` the Group/ZModP stdlib."""
        return bool(self._groupelems or self._modints)

    def resolve(
        self, t: frog_ast.Type, _visited: frozenset[str] = frozenset()
    ) -> frog_ast.Type:
        """Resolve type aliases by name; unwrap OptionalType.

        Cycle-safe: tracks visited alias names and bails out to the last
        unresolved type if a cycle is detected.
        """
        if isinstance(t, frog_ast.OptionalType):
            return self.resolve(t.the_type, _visited)
        # For FieldAccess, prefer a qualified alias key ("E1.key") over
        # the bare field name so per-instance clones resolve correctly.
        if isinstance(t, frog_ast.FieldAccess) and isinstance(
            t.the_object, frog_ast.Variable
        ):
            qualified = f"{t.the_object.name}.{t.name}"
            if qualified in self._aliases and qualified not in _visited:
                return self.resolve(self._aliases[qualified], _visited | {qualified})
        name: str | None = None
        if isinstance(t, (frog_ast.Variable, frog_ast.FieldAccess)):
            name = t.name
        if name is not None and name in self._aliases and name not in _visited:
            return self.resolve(self._aliases[name], _visited | {name})
        return t

    def translate_type(self, t: frog_ast.Type) -> ec_ast.EcType:
        """Translate a FrogLang type to an EC type, registering it."""
        # An optional type ``T?`` is EC's ``T option``. Handled first, before
        # ``resolve`` (which unwraps ``OptionalType`` for its own alias-chasing
        # purposes) would collapse it to the base ``T``. Optional-returning
        # methods (``Decaps``/``Indirect``, and the SymEnc ``Dec`` family)
        # become genuinely optional so a live ``return None`` is faithful.
        if isinstance(t, frog_ast.OptionalType):
            return ec_ast.EcType(f"{self.translate_type(t.the_type).text} option")
        # Abstract-types check runs before alias resolution so that
        # primitive-level types (Key, Message, Ciphertext) stay abstract
        # even when a scheme alias would otherwise concretize them.
        abstract = self._abstract_lookup(t)
        if abstract is not None:
            if abstract not in self._abstract_seen:
                self._abstract_seen.append(abstract)
            return ec_ast.EcType(abstract)
        resolved = self.resolve(t)
        if isinstance(resolved, frog_ast.Void):
            return ec_ast.EcType("unit")
        if isinstance(resolved, frog_ast.BoolType):
            return ec_ast.EcType("bool")
        if isinstance(resolved, frog_ast.BitStringType):
            name = self._bitstring_name(resolved)
            if self._theory_mode:
                if name not in self._abstract_bitstring_names:
                    self._abstract_bitstring_names.add(name)
                    self._abstract_bitstrings.append(
                        (name, self._stripped_parameterization(resolved))
                    )
            else:
                if name not in self._seen:
                    self._seen.add(name)
                    self._names.append(name)
            return ec_ast.EcType(name)
        if isinstance(resolved, frog_ast.ProductType):
            parts = []
            for sub in resolved.types:
                sub_txt = self.translate_type(sub).text
                # Parenthesize a component that is itself a product so EC
                # sees a *nested* tuple rather than a flattened one: a
                # FrogLang ``[[A, B], C]`` is a pair whose first element is a
                # pair (``(A * B) * C``), not a flat 3-tuple (``A * B * C``).
                # Without the parens the emitted return type disagrees with
                # the nested value expression / ``.`i`` projections the rest
                # of the export renders (e.g. KEMCombiner's
                # ``[[pk1, pk2], [sk1, sk2, pk1, pk2]]`` KeyGen result).
                if isinstance(self.resolve(sub), frog_ast.ProductType):
                    sub_txt = f"({sub_txt})"
                parts.append(sub_txt)
            return ec_ast.EcType(" * ".join(parts))
        if isinstance(resolved, frog_ast.IntType):
            return ec_ast.EcType("int")
        if isinstance(resolved, frog_ast.ModIntType):
            # Dual role: ``ModInt<G.order>`` is the exponent ring of the
            # group ``G`` -- alias it to ``G``'s cloned exponent type (no
            # independent clone) so ``g ^ a`` type-checks against the same
            # ring. A standalone ``ModInt<q>`` gets its own ``ZModRing`` clone.
            group_alias = self._group_order_modulus_alias(resolved)
            if group_alias is not None:
                # Ensure the group is registered (sets its exponent type).
                self.translate_type(
                    frog_ast.GroupElemType(frog_ast.Variable(group_alias))
                )
                return ec_ast.EcType(self._groupelem_exp[group_alias])
            alias = self._modint_name(resolved)
            if alias not in self._modint_set:
                self._modint_set.add(alias)
                self._modints.append(alias)
                self._modint_distrs[f"{alias}.zmod"] = f"{alias}.DZmodP.dunifin"
                # Bind the ZModRing modulus to the actual FrogLang expression
                # (e.g. ``q`` from an ``Int q`` let -> ``op q : int``), so the
                # ring is genuinely Z_<modulus> rather than over an unrelated
                # abstract ``p`` -- keeping ``ModInt<q>`` faithful for any
                # future proof that relates ``q`` to the ring cardinality.
                modulus = _substitute_aliases(
                    resolved.modulus, self._aliases, self._strip_field_prefixes
                )
                self._modint_modulus[alias] = _canonical_arith_str(modulus)
            return ec_ast.EcType(f"{alias}.zmod")
        if isinstance(resolved, frog_ast.GroupElemType):
            alias = self._groupelem_name(resolved)
            if alias not in self._groupelem_set:
                self._groupelem_set.add(alias)
                self._groupelems.append(alias)
                # Record the exponent type (and its uniform distr) for this
                # group: prime declares the PowZMod field, general the
                # ZModRing. Set directly (no recursive ModInt translation)
                # so ``ModInt<G.order>`` later aliases back to it.
                if self.is_prime_group(alias):
                    exp_text = f"{alias}_P.ZModE.exp"
                    self._exp_distrs[exp_text] = f"{alias}_FD.dt"
                else:
                    exp_text = f"{alias}_Exp.zmod"
                    self._exp_distrs[exp_text] = f"{alias}_Exp.DZmodP.dunifin"
                self._groupelem_exp[alias] = exp_text
            return ec_ast.EcType(f"{alias}.group")
        if (
            isinstance(resolved, frog_ast.Variable)
            and resolved.name in self._known_abstract_types
        ):
            return ec_ast.EcType(resolved.name)
        if isinstance(resolved, frog_ast.FunctionType):
            dom = self.translate_type(resolved.domain_type).text
            codom = self.translate_type(resolved.range_type).text
            key = (dom, codom)
            if key not in self._function_type_set:
                self._function_type_set.add(key)
                self._function_types.append(key)
            return ec_ast.EcType(f"{dom} -> {codom}")
        # (register_function_value defined below handles the named-value op.)
        if isinstance(resolved, frog_ast.MapType):
            # A FrogLang finite map ``Map<K, V>`` (a lazy random-oracle table
            # in the ROM games, e.g. ``Map<BitString<P.M>, BitString<n>>``)
            # translates to EC's ``SmtMap`` finite-function type ``(k, v)
            # fmap``. Register the key/value component types so they are
            # emitted, and flag map usage so the file ``require``s ``SmtMap``.
            key_txt = self.translate_type(resolved.key_type).text
            val_txt = self.translate_type(resolved.value_type).text
            self._uses_map = True
            return ec_ast.EcType(f"({key_txt}, {val_txt}) fmap")
        raise NotImplementedError(
            f"Type translation not implemented for {type(resolved).__name__}: "
            f"{resolved}"
        )

    def _abstract_lookup(self, t: frog_ast.Type) -> str | None:
        if not self._abstract_types:
            return None
        core = t.the_type if isinstance(t, frog_ast.OptionalType) else t
        if isinstance(core, (frog_ast.Variable, frog_ast.FieldAccess)):
            return self._abstract_types.get(core.name)
        return None

    def _bitstring_name(self, t: frog_ast.BitStringType) -> str:
        if t.parameterization is None:
            name = "bs_t" if self._theory_mode else "bs"
            # No length expression to record.
            return name
        expr = self._stripped_parameterization(t)
        # Canonicalize via sympy so arithmetically-equivalent forms
        # (``lambda + 2 * lambda`` and ``3 * lambda``) collapse to the
        # same EC type name. Without this, the engine's Symbolic
        # Computation transform produces intermediate states whose
        # bitstring sizes differ syntactically but agree as integers,
        # and EC then rejects the chain because the corresponding
        # ``bs_*`` types are syntactically distinct.
        length_str = _canonical_arith_str(expr)
        sanitized = _sanitize(length_str)
        # In theory mode, bitstring types are abstract type aliases
        # inside the abstract theory. EC's name lookup inside a theory
        # also sees top-level names declared in the same file, so we
        # need a distinct naming convention to avoid clashes between
        # the theory's abstract ``bs_lambda`` and a top-level concrete
        # ``bs_lambda`` (e.g. ``BitString<lambda>`` derived from a
        # ``Int lambda;`` let). Suffix theory-local names with ``_t``.
        if self._theory_mode:
            name = f"bs_{sanitized}_t" if sanitized else "bs_t"
        else:
            name = f"bs_{sanitized}" if sanitized else "bs"
        # Record the canonical length expression for the
        # slice/concat axiom emitter. The string form matches what
        # ``expr_translator._canonical_int_str`` emits in slice op
        # arguments (sympy-canonical), so axioms and expressions
        # reference the same int literals.
        self._bs_lengths[name] = length_str
        return name

    def _stripped_parameterization(
        self, t: frog_ast.BitStringType
    ) -> frog_ast.Expression:
        assert t.parameterization is not None
        return _substitute_aliases(
            t.parameterization, self._aliases, self._strip_field_prefixes
        )

    def _group_order_modulus_alias(self, t: frog_ast.ModIntType) -> str | None:
        """Group clone alias if ``t`` is ``ModInt<G.order>``, else ``None``.

        Accepts ``FieldAccess(<G>, 'order')`` or ``GroupOrder(<G>)`` with a
        ``Variable`` group, returning the (sanitized) group name so the
        exponent ring aliases that group's cloned exponent type.
        """
        modulus = _substitute_aliases(
            t.modulus, self._aliases, self._strip_field_prefixes
        )
        group_expr: frog_ast.Expression | None = None
        if (
            isinstance(modulus, frog_ast.FieldAccess)
            and modulus.name == "order"
            and isinstance(modulus.the_object, frog_ast.Variable)
        ):
            group_expr = modulus.the_object
        elif isinstance(modulus, frog_ast.GroupOrder) and isinstance(
            modulus.group, frog_ast.Variable
        ):
            group_expr = modulus.group
        if group_expr is None:
            return None
        return _sanitize(_canonical_arith_str(group_expr))

    def _modint_name(self, t: frog_ast.ModIntType) -> str:
        """EC clone alias for a standalone ``ModInt<q>`` type.

        Canonicalizes the modulus via sympy (mirroring ``_bitstring_name``)
        so arithmetically-equivalent moduli collapse to one clone. The alias
        must be EC-theory-valid (uppercase-initial), so ``ModInt<q>`` becomes
        ``ModInt_q`` (the EC type is then ``ModInt_q.zmod``).
        """
        modulus = _substitute_aliases(
            t.modulus, self._aliases, self._strip_field_prefixes
        )
        sanitized = _sanitize(_canonical_arith_str(modulus))
        return f"ModInt_{sanitized}" if sanitized else "ModInt"

    def _groupelem_name(self, t: frog_ast.GroupElemType) -> str:
        """EC group clone alias for a ``GroupElem<G>`` type.

        The alias is the (sanitized) group name itself -- the ``clone
        CyclicGroup as <G>`` alias -- so ``GroupElem<G>`` has EC type
        ``<G>.group``. Group names are uppercase-initial by FrogLang
        convention, which EC requires of a theory clone alias.
        """
        group = _substitute_aliases(t.group, self._aliases, self._strip_field_prefixes)
        sanitized = _sanitize(_canonical_arith_str(group))
        return sanitized if sanitized else "G"

    def distr_for(self, ec_type: ec_ast.EcType) -> str:
        """Return the distribution op name for a sampled type.

        In abstract mode this yields ``d<name>`` (e.g. ``dciphertext``) and
        records that distribution for later emission. In concrete mode it
        yields ``dbs...`` for bitstring types. Product EC types
        (``A * B * ...``) yield ``dA `*` dB `*` ...``.
        """
        # Function type ``A -> B``: a sampled random function. Its
        # distribution is the uniform-function-space op registered when the
        # arrow type was translated (see ``_function_types``).
        if " -> " in ec_type.text:
            dom, codom = ec_type.text.split(" -> ", 1)
            return _function_distr_name(dom.strip(), codom.strip())
        # Product type: recurse on each component.
        if " * " in ec_type.text and "(" not in ec_type.text:
            parts = [p.strip() for p in ec_type.text.split(" * ")]
            return " `*` ".join(self.distr_for(ec_ast.EcType(p)) for p in parts)
        # Stdlib group element: uniform over the finite group's enum.
        if ec_type.text.endswith(".group"):
            return f"duniform {ec_type.text[: -len('.group')]}.elems"
        # Stdlib exponent ring / standalone ModInt: the cloned uniform distr.
        if ec_type.text in self._exp_distrs:
            return self._exp_distrs[ec_type.text]
        if ec_type.text in self._modint_distrs:
            return self._modint_distrs[ec_type.text]
        if ec_type.text in self._abstract_seen:
            distr = f"d{ec_type.text}"
            if distr not in self._abstract_distrs:
                self._abstract_distrs.append(distr)
            return distr
        if ec_type.text in self._known_abstract_types:
            distr = f"d{ec_type.text}"
            if distr not in self._known_abstract_distrs:
                self._known_abstract_distrs.append(distr)
            return distr
        assert ec_type.text.startswith("bs_") or ec_type.text == "bs"
        suffix = ec_type.text.removeprefix("bs")
        distr = f"dbs{suffix}"
        if self._theory_mode and distr not in self._abstract_distrs:
            self._abstract_distrs.append(distr)
        return distr

    def emit_abstract(self) -> list[ec_ast.EcTopDecl]:
        """Produce EC decls for abstract types + distributions seen.

        Used inside an ``abstract theory``. Emits:

        * one ``type <name>.`` per abstract type (including any bitstring
          types registered while in theory mode),
        * for each distribution used: ``op d<name> : <name> distr.`` plus
          ``axiom d<name>_ll`` / ``axiom d<name>_fu`` / ``axiom d<name>_full``.

        Theory-mode slice/concat ops and their round-trip + distribution-
        split axioms are emitted by the caller via :meth:`emit` (not here)
        because slice/concat ops are registered at the top level even when
        the bitstring types live inside the theory.
        """
        decls: list[ec_ast.EcTopDecl] = []
        for name in self._abstract_seen:
            decls.append(ec_ast.TypeDecl(name))
        for name, _expr in self._abstract_bitstrings:
            decls.append(ec_ast.TypeDecl(name))
            decls.append(ec_ast.OpDecl(_zero_name(name), name))
        for distr in self._abstract_distrs:
            type_name = distr[1:]  # strip 'd'
            decls.append(ec_ast.OpDecl(distr, f"{type_name} distr"))
            decls.append(ec_ast.Axiom(f"{distr}_ll", f"is_lossless {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_fu", f"is_funiform {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_full", f"is_full {distr}"))
        # Random-function distributions for ``Function<A,B>`` fields sampled
        # inside the theory (e.g. LazyRO's ``rF <$ dfun_bs_M_t_to_bs_n_t`` over
        # the theory-mode ``bs_M_t``/``bs_n_t``). Same foundation as emit()'s
        # top-level case, but these arrow types live in the theory, so their
        # dfun op must too. Emitted after the codomain distrs above so the
        # arrow's operands are in scope.
        for dom, codom in self._function_types:
            distr = _function_distr_name(dom, codom)
            arrow = f"{dom} -> {codom}"
            decls.append(ec_ast.OpDecl(distr, f"({arrow}) distr"))
            decls.append(ec_ast.Axiom(f"{distr}_ll", f"is_lossless {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_fu", f"is_funiform {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_full", f"is_full {distr}"))
        # A ``Function<D,R> H`` game param inside the theory: the random-oracle
        # function VALUE, sampled once (not a fixed op). Emitted as a read-only
        # holder module ``module RO_H = { var h : d -> r }`` -- the abstract
        # counterpart of the concrete Main-section RO, instantiated at the clone.
        for fname, dom, codom in self._function_values:
            decls.append(
                ec_ast.Module(
                    name=_ro_module_name(fname),
                    procs=[],
                    module_vars=[
                        ec_ast.VarDecl("h", ec_ast.EcType(f"{dom} -> {codom}"))
                    ],
                )
            )
        # Slice/concat op declarations for ops registered while translating THIS
        # (theory-mode) collector's modules -- e.g. a FOREIGN primitive security
        # game whose body reconstructs a KDF input (``KDFPRFSec.lookup`` prepends
        # the key ``k`` to ``rest`` via ``concat_bs_Nkey_t_bs_Nin_Nkey_t_to_bs_Nin_t``).
        # Such a concat lands in the foreign collector (its operands are foreign-
        # theory bitstring types), yet was never emitted (only :meth:`emit`, on the
        # TOP collector, declared concats) -> "no matching operator". Declare them
        # here, inside the theory where their types live and where they are used.
        # Round-trip / distr-split axioms are length-gated (skipped for abstract
        # foreign lengths) and reference distrs that may be theory-external, so
        # only the op decls are emitted here; a foreign tactic needing the axioms
        # would surface as its own wall.
        for src_name, dst_name in self._slice_ops:
            op = _slice_op_name(src_name, dst_name)
            decls.append(ec_ast.OpDecl(op, f"{src_name} -> int -> int -> {dst_name}"))
        for left_name, right_name, result_name in self._concat_ops:
            op = _concat_op_name(left_name, right_name, result_name)
            decls.append(
                ec_ast.OpDecl(op, f"{left_name} -> {right_name} -> {result_name}")
            )
        return decls

    @property
    def abstract_types_seen(self) -> list[str]:
        return list(self._abstract_seen)

    @property
    def abstract_distrs_seen(self) -> list[str]:
        return list(self._abstract_distrs)

    def function_distrs_seen(self) -> list[tuple[str, str, str]]:
        """``(dfun_name, dom, codom)`` for each ``Function<A,B>`` distribution the
        theory samples (its ``dfun_<dom>_to_<codom>`` op). Lets a clone bind the
        theory's random-function distribution to the shared concrete RO dfun."""
        return [
            (_function_distr_name(dom, codom), dom, codom)
            for dom, codom in self._function_types
        ]

    def resolve_value_alias(
        self, obj_name: str, field_name: str
    ) -> frog_ast.Expression | None:
        """Return the concretized value expression for ``<obj>.<field>``.

        Used by the expression translator to render ``T.lambda``-style
        FieldAccess references in reduction bodies: the alias map
        carries the post-instantiation value (e.g. ``Variable("lambda")``
        or ``BinaryOperation(2, *, lambda)``), which the caller then
        renders recursively as an EC integer expression.

        Returns ``None`` when no expression-valued alias is registered
        (e.g. the field is a Set, or the obj-name is unknown).
        """
        qualified = f"{obj_name}.{field_name}"
        value = self._aliases.get(qualified)
        if isinstance(value, frog_ast.Expression):
            return value
        return None

    def register_slice(self, src_name: str, dst_name: str) -> str:
        """Register a slicing op ``src -> int -> int -> dst`` and return its name.

        The op extracts a sub-bitstring; the start/end indices are
        passed as integers. The op itself is uninterpreted (no
        ``concat/slice`` round-trip axioms emitted), which is enough
        for type checking but not for verifying that two slice-then-
        concat compositions are equivalent.
        """
        key = (src_name, dst_name)
        if key not in self._slice_op_set:
            self._slice_op_set.add(key)
            self._slice_ops.append(key)
        return _slice_op_name(src_name, dst_name)

    def register_concat(self, left_name: str, right_name: str, result_name: str) -> str:
        """Register a concat op ``left -> right -> result`` and return its name.

        The op is uninterpreted; see :meth:`register_slice` for caveats.
        Also auto-registers the two slice ops ``(result, left)`` and
        ``(result, right)`` so the slice/concat round-trip axioms emitted
        in :meth:`emit` and :meth:`emit_abstract` have both ops in scope.
        """
        key = (left_name, right_name, result_name)
        if key not in self._concat_op_set:
            self._concat_op_set.add(key)
            self._concat_ops.append(key)
        # Auto-register the inverse slice ops if not already present.
        self.register_slice(result_name, left_name)
        self.register_slice(result_name, right_name)
        return _concat_op_name(left_name, right_name, result_name)

    def register_concat3(
        self, left_name: str, right_name: str, gap_name: str, result_name: str
    ) -> str:
        """Register a 3-way concat ``left -> right -> gap -> result`` and
        return its name.

        Used by the partial-split synthesizer for ``Split Uniform Samples``
        applications where the two used slices don't cover the source
        bitstring: a third "gap" piece reconstructs a sound 3-way
        bijection. Auto-registers the three inverse slice ops so the
        round-trip axioms emitted in :meth:`emit` have all components in
        scope.
        """
        key = (left_name, right_name, gap_name, result_name)
        if key not in self._concat3_op_set:
            self._concat3_op_set.add(key)
            self._concat3_ops.append(key)
        # Auto-register the inverse slice ops if not already present.
        self.register_slice(result_name, left_name)
        self.register_slice(result_name, right_name)
        self.register_slice(result_name, gap_name)
        return _concat3_op_name(left_name, right_name, gap_name, result_name)

    def register_bs_by_length_str(self, length_str: str) -> str:
        """Register a fresh bitstring type by its canonical length string,
        returning the EC type name. Idempotent: if a bs with the same
        canonical length is already registered, returns its name.

        Used by the partial-split synthesizer to obtain a bitstring type
        for the gap piece in a 3-way concat decomposition. The length
        string should already be in sympy-canonical form (matching the
        ``_canonical_arith_str`` output used elsewhere) so the resulting
        name aligns with bs types registered via ``_bitstring_name``.
        """
        sanitized = _sanitize(length_str)
        if self._theory_mode:
            name = f"bs_{sanitized}_t" if sanitized else "bs_t"
            if name not in self._abstract_bitstring_names:
                # Cannot construct a frog_ast Expression here; leave
                # parameterization absent. Theory-mode partial splits
                # aren't currently exercised, but record the name for
                # completeness.
                self._abstract_bitstring_names.add(name)
        else:
            name = f"bs_{sanitized}" if sanitized else "bs"
            if name not in self._seen:
                self._seen.add(name)
                self._names.append(name)
        self._bs_lengths[name] = length_str
        return name

    def register_type_alias(self, bs_name: str, definition: str) -> None:
        """Mark a registered bitstring type as an alias of ``definition``.

        Used when a scheme ``requires`` clause equates a bitstring type
        (e.g. ``BitString<F.lambda>`` -> ``bs_lambda``) with an
        earlier-declared abstract carrier type (e.g. ``SharedSecretSpace``).
        :meth:`emit` then renders ``type bs_lambda = SharedSecretSpace.``
        instead of a fresh abstract ``type bs_lambda.``, so EC unifies them.
        The definition type must be declared *before* this collector's
        output (e.g. a ``Set X;`` let), which the exporter guarantees by
        making the set-let carrier the canonical side.
        """
        self._type_alias_defs[bs_name] = definition

    def register_subset_carrier(
        self, carrier_name: str, bs_type: frog_ast.BitStringType
    ) -> None:
        """Record that abstract carrier set ``carrier_name`` is bitstring-like.

        See :attr:`_subset_carriers`. Called by the exporter for each
        ``requires X subsets/== BitString<n>`` clause so ``||`` on an
        ``X``-typed operand renders as concatenation.
        """
        self._subset_carriers.setdefault(carrier_name, bs_type)

    def bitstring_carrier_type(self, name: str) -> frog_ast.BitStringType | None:
        """Return the BitString type an abstract carrier set unifies with,
        or ``None`` if ``name`` is not such a carrier.

        A scheme ``requires X subsets BitString<n>`` (or ``== BitString<n>``)
        makes the abstract carrier set ``X`` interchangeable with ``bs_n``.
        Operators defined only on bitstrings -- notably ``||``
        concatenation -- must then treat an ``X``-typed operand as a
        ``bs_n``: the engine inlines the set->bs coercion
        (``BitString<n> b = x;``) in flat states, so a ``||`` operand can
        surface carrier-typed. Returns the registered bitstring type so the
        expression translator can render the concat instead of EC's boolean
        ``||``.
        """
        return self._subset_carriers.get(name)

    def bs_length_for(self, bs_name: str) -> str | None:
        """Return the canonical length expression string for a registered
        abstract bitstring, or ``None`` if the name isn't registered.
        Used by parametric tactic synthesizers (Split/Merge Uniform
        Samples) to render the bit-length integer expressions in
        slice/concat tactic arguments.
        """
        return self._bs_lengths.get(bs_name)

    @property
    def registered_bitstring_names(self) -> list[str]:
        """Concrete bitstring type names registered so far, in emission order.

        Used by the exporter to order ``requires``-equality unifications
        between two bitstring types (the earlier-registered one is the
        canonical side, since it is declared first in :meth:`emit`).
        """
        return list(self._names)

    @property
    def abstract_bitstrings(self) -> list[tuple[str, frog_ast.Expression]]:
        """Bitstrings registered as abstract types inside the theory.

        Each tuple is ``(abstract_name, parameterization_expr)``. The
        exporter uses the expression to derive the per-instance concrete
        bitstring (substituting each instance's concretized field values)
        when emitting clone type/op bindings.
        """
        return list(self._abstract_bitstrings)

    def emit(self) -> list[ec_ast.EcTopDecl]:
        """Produce top-level EC declarations for every registered type."""
        decls: list[ec_ast.EcTopDecl] = []
        # GroupElem<G>: a clone of EC stdlib ``CyclicGroup`` (group laws
        # derived, not axiomatized) plus its exponent ring. A proof that
        # declared ``requires <G>.order is prime;`` gets the ``PowZMod``
        # field exponent + ``FDistr`` (plus an assumed ``prime <G>.order``,
        # justified by that declaration); every other group gets the general
        # ``ZModRing`` exponent (Z_<order>, leaving the stdlib ``ge2_p :
        # 2 <= <order>`` assumed -- registered with the axiom-soundness
        # audit). Emitted before standalone ModInt clones (independent) and
        # before any scheme clone referencing ``<G>.group``. Not ``import``ed
        # -- every op is qualified (``<G>.( * )`` vs ``<G>_Exp.( * )`` would
        # otherwise collide).
        for alias in self._groupelems:
            lines = [f"clone CyclicGroup as {alias}."]
            if self.is_prime_group(alias):
                lines.append(f"axiom {alias}_prime_order : IntDiv.prime {alias}.order.")
                lines.append(
                    f"clone {alias}.PowZMod as {alias}_P "
                    f"with lemma prime_order <- {alias}_prime_order."
                )
                lines.append(f"clone {alias}_P.FDistr as {alias}_FD.")
            else:
                lines.append(
                    f"clone ZModP.ZModRing as {alias}_Exp "
                    f"with op p <- {alias}.order."
                )
            decls.append("\n".join(lines))
        # Standalone ModInt<q> (e.g. the OTP additive group over Z_q): its
        # own ``ZModRing`` clone. ``+``/``-``/``*``/``zero`` and the uniform
        # ``DZmodP.dunifin`` come from the stdlib; the round-trip laws the
        # OTP ``rnd`` bijection needs are derived ``ring`` lemmas (the 3
        # former add/sub axioms dissolve). Leaves ``ge2_p : 2 <= q`` assumed.
        for alias in self._modints:
            modulus = self._modint_modulus.get(alias)
            if modulus:
                decls.append(f"clone ZModP.ZModRing as {alias} with op p <- {modulus}.")
            else:
                decls.append(f"clone ZModP.ZModRing as {alias}.")
        # Distributions over known top-level abstract types (declared
        # elsewhere via ``type X.``): emit the distribution op and
        # lossless/funiform/full axioms. The type declaration itself is
        # emitted by the caller from the ``Set X;`` let bindings.
        for distr in self._known_abstract_distrs:
            type_name = distr[1:]
            decls.append(ec_ast.OpDecl(distr, f"{type_name} distr"))
            decls.append(ec_ast.Axiom(f"{distr}_ll", f"is_lossless {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_fu", f"is_funiform {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_full", f"is_full {distr}"))
        for name in self._names:
            suffix = name.removeprefix("bs")
            distr = f"dbs{suffix}"
            alias_def = self._type_alias_defs.get(name)
            if alias_def is not None:
                decls.append(ec_ast.TypeDecl(name, definition=alias_def))
            else:
                decls.append(ec_ast.TypeDecl(name))
            decls.append(ec_ast.OpDecl(distr, f"{name} distr"))
            decls.append(ec_ast.Axiom(f"{distr}_ll", f"is_lossless {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_fu", f"is_funiform {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_full", f"is_full {distr}"))
        # Function types sampled as random functions: an abstract uniform
        # distribution over the finite function space ``A -> B`` plus
        # lossless/funiform/full axioms. The intended model is
        # ``dfun (fun _ => dB)`` (EC's ``MUniFinFun``), for which all three
        # facts hold; declaring them as a foundation keeps the export
        # name-independent (the domain bitstring stays abstract). Emitted
        # after the bitstring ``type`` declarations above so the arrow
        # type's domain/codomain are in scope.
        for dom, codom in self._function_types:
            distr = _function_distr_name(dom, codom)
            arrow = f"{dom} -> {codom}"
            decls.append(ec_ast.OpDecl(distr, f"({arrow}) distr"))
            decls.append(ec_ast.Axiom(f"{distr}_ll", f"is_lossless {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_fu", f"is_funiform {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_full", f"is_full {distr}"))
        # Emit the RO holder module ONLY when this collector owns it (empty
        # prefix). A prefixed collector references the theorem-primitive theory
        # clone's single holder (``Hybrid_c.RO_H``) instead of declaring a
        # distinct top-level copy -- the two would never unify (a module cannot be
        # clone-instantiated), leaving ``={glob RO_H}`` unable to bridge the
        # theorem-game wrapper (which reads ``Hybrid_c.RO_H``) to the flat states.
        if not self.ro_module_prefix:
            for fname, dom, codom in self._function_values:
                decls.append(
                    ec_ast.Module(
                        name=_ro_module_name(fname),
                        procs=[],
                        module_vars=[
                            ec_ast.VarDecl("h", ec_ast.EcType(f"{dom} -> {codom}"))
                        ],
                    )
                )
        for name in self._names:
            decls.append(ec_ast.OpDecl(_zero_name(name), name))
        for name in self._names:
            xor_op = _xor_name(name)
            decls.append(ec_ast.OpDecl(xor_op, f"{name} -> {name} -> {name}"))
            decls.append(
                ec_ast.Axiom(
                    f"{xor_op}_invol",
                    f"forall (a b : {name}), {xor_op} ({xor_op} a b) b = a",
                )
            )
            # Commutativity: needed by the canned tactic for
            # ``Normalize Commutative Chains`` when the engine rewrites
            # ``xor a b`` to ``xor b a``. ``sim`` alone won't close those
            # micros; ``smt(<xor>_commut)`` does.
            decls.append(
                ec_ast.Axiom(
                    f"{xor_op}_commut",
                    f"forall (a b : {name}), {xor_op} a b = {xor_op} b a",
                )
            )
            # Associativity: needed by the tactic for ``XOR Cancellation``
            # when the engine reassociates ``xor a (xor b c)`` to
            # ``xor (xor a b) c`` (e.g. DoubleOTP's chained key XOR). Not
            # derivable from involution + commutativity, so it must be a
            # standalone axiom; ``smt(<xor>_assoc)`` then closes the micro.
            decls.append(
                ec_ast.Axiom(
                    f"{xor_op}_assoc",
                    f"forall (a b c : {name}), "
                    f"{xor_op} a ({xor_op} b c) = {xor_op} ({xor_op} a b) c",
                )
            )
        for src_name, dst_name in self._slice_ops:
            op = _slice_op_name(src_name, dst_name)
            decls.append(ec_ast.OpDecl(op, f"{src_name} -> int -> int -> {dst_name}"))
        for left_name, right_name, result_name in self._concat_ops:
            op = _concat_op_name(left_name, right_name, result_name)
            decls.append(
                ec_ast.OpDecl(op, f"{left_name} -> {right_name} -> {result_name}")
            )
        # Round-trip and distribution-split axioms for each registered
        # concat triple. These let the Split/Merge Uniform Samples
        # parametric synthesizers close their per-transform micros via
        # ``rnd`` with a slice/concat bijection. Skipped when the bit
        # lengths aren't known (e.g. unparameterized ``BitString`` types).
        for left_name, right_name, result_name in self._concat_ops:
            len_l = self._bs_lengths.get(left_name)
            len_r = self._bs_lengths.get(right_name)
            if len_l is None or len_r is None:
                continue
            concat_op = _concat_op_name(left_name, right_name, result_name)
            slice_l = _slice_op_name(result_name, left_name)
            slice_r = _slice_op_name(result_name, right_name)
            len_l_p = _paren_int(len_l)
            len_sum = f"({len_l} + {len_r})"
            decls.append(
                ec_ast.Axiom(
                    f"slice_concat_left_{left_name}_{right_name}_{result_name}",
                    f"forall (a : {left_name}) (b : {right_name}),\n"
                    f"  {slice_l} ({concat_op} a b) 0 {len_l_p} = a",
                )
            )
            decls.append(
                ec_ast.Axiom(
                    f"slice_concat_right_{left_name}_{right_name}_{result_name}",
                    f"forall (a : {left_name}) (b : {right_name}),\n"
                    f"  {slice_r} ({concat_op} a b) {len_l_p} {len_sum} = b",
                )
            )
            decls.append(
                ec_ast.Axiom(
                    f"concat_slices_id_{left_name}_{right_name}_{result_name}",
                    f"forall (s : {result_name}),\n"
                    f"  {concat_op} ({slice_l} s 0 {len_l_p})"
                    f" ({slice_r} s {len_l_p} {len_sum}) = s",
                )
            )
            distr_l = f"d{left_name}"
            distr_r = f"d{right_name}"
            distr_res = f"d{result_name}"
            decls.append(
                ec_ast.Axiom(
                    f"{distr_res}_split_{left_name}_{right_name}",
                    f"{distr_res} =\n"
                    f"  dmap ({distr_l} `*` {distr_r})\n"
                    f"       (fun (p : {left_name} * {right_name}) =>"
                    f" {concat_op} p.`1 p.`2)",
                )
            )
        # 3-way concat round-trip and distribution-split axioms for
        # partial-split applications. The dlet-form distribution-split
        # axiom matches the shape produced by EC's ``rndsem*{i} 0`` when
        # folding three independent samples plus a concat3 assignment.
        for left_name, right_name, gap_name, result_name in self._concat3_ops:
            len_l = self._bs_lengths.get(left_name)
            len_r = self._bs_lengths.get(right_name)
            len_g = self._bs_lengths.get(gap_name)
            if len_l is None or len_r is None or len_g is None:
                continue
            concat3_op = _concat3_op_name(left_name, right_name, gap_name, result_name)
            slice_l = _slice_op_name(result_name, left_name)
            slice_r = _slice_op_name(result_name, right_name)
            slice_g = _slice_op_name(result_name, gap_name)
            len_l_p = _paren_int(len_l)
            len_lr = f"({len_l} + {len_r})"
            len_res = _paren_int(self._bs_lengths.get(result_name, ""))
            axiom_prefix = f"{left_name}_{right_name}_{gap_name}_{result_name}"
            decls.append(
                ec_ast.OpDecl(
                    concat3_op,
                    f"{left_name} -> {right_name} -> {gap_name} -> {result_name}",
                )
            )
            decls.append(
                ec_ast.Axiom(
                    f"slice_concat3_p1_{axiom_prefix}",
                    f"forall (a : {left_name}) (b : {right_name}) (c : {gap_name}),\n"
                    f"  {slice_l} ({concat3_op} a b c) 0 {len_l_p} = a",
                )
            )
            decls.append(
                ec_ast.Axiom(
                    f"slice_concat3_p2_{axiom_prefix}",
                    f"forall (a : {left_name}) (b : {right_name}) (c : {gap_name}),\n"
                    f"  {slice_r} ({concat3_op} a b c) {len_l_p} {len_lr} = b",
                )
            )
            decls.append(
                ec_ast.Axiom(
                    f"slice_concat3_p3_{axiom_prefix}",
                    f"forall (a : {left_name}) (b : {right_name}) (c : {gap_name}),\n"
                    f"  {slice_g} ({concat3_op} a b c) {len_lr} {len_res} = c",
                )
            )
            decls.append(
                ec_ast.Axiom(
                    f"concat3_slices_id_{axiom_prefix}",
                    f"forall (s : {result_name}),\n"
                    f"  {concat3_op} ({slice_l} s 0 {len_l_p})"
                    f" ({slice_r} s {len_l_p} {len_lr})"
                    f" ({slice_g} s {len_lr} {len_res}) = s",
                )
            )
            distr_l = f"d{left_name}"
            distr_r = f"d{right_name}"
            distr_g = f"d{gap_name}"
            distr_res = f"d{result_name}"
            decls.append(
                ec_ast.Axiom(
                    f"{distr_res}_split3_{left_name}_{right_name}_{gap_name}",
                    f"{distr_res} =\n"
                    f"  dlet {distr_l} (fun (v1 : {left_name}) =>\n"
                    f"     dlet {distr_r} (fun (v2 : {right_name}) =>\n"
                    f"        dmap {distr_g} ({concat3_op} v1 v2)))",
                )
            )
        return decls


def _substitute_aliases(
    expr: frog_ast.Expression,
    aliases: dict[str, frog_ast.Type],
    strip_prefixes: set[str],
    _visited: frozenset[str] = frozenset(),
) -> frog_ast.Expression:
    """Concretize a bitstring parameterization expression.

    For each ``FieldAccess(Variable(p), name)`` encountered:

    * If ``aliases["<p>.<name>"]`` is an ``Expression``, substitute that
      expression in. Used at the top level to expand a scheme instance's
      ``T.stretch`` to its concrete value (e.g. ``2 * lambda``).
    * Otherwise, if ``p`` is in ``strip_prefixes``, replace with
      ``Variable(name)``. Used inside the abstract theory where the game
      parameter (e.g. ``G``) has no concretization and references should
      collapse to the primitive's bare field name.

    For each bare ``Variable(name)`` encountered: if
    ``aliases[name]`` is an ``Expression``, substitute that expression
    in. Used when translating the primary scheme's body, whose method
    signatures reference fields by bare name (e.g.
    ``BitString<lambda + stretch>`` inside ``TriplingPRG.evaluate``).

    Recurses through ``BinaryOperation`` and ``UnaryOperation``. The
    ``_visited`` set guards against cycles like
    ``G.lambda -> lambda -> lambda`` (opaque let-binding).
    """
    if isinstance(expr, frog_ast.FieldAccess) and isinstance(
        expr.the_object, frog_ast.Variable
    ):
        obj_name = expr.the_object.name
        qualified = f"{obj_name}.{expr.name}"
        if qualified in _visited:
            return expr
        alias_value = aliases.get(qualified)
        if isinstance(alias_value, frog_ast.Expression):
            return _substitute_aliases(
                alias_value, aliases, strip_prefixes, _visited | {qualified}
            )
        if obj_name in strip_prefixes:
            return frog_ast.Variable(expr.name)
        return expr
    if isinstance(expr, frog_ast.Variable):
        if expr.name in _visited:
            return expr
        alias_value = aliases.get(expr.name)
        if isinstance(alias_value, frog_ast.Variable) and alias_value.name == expr.name:
            return expr
        if isinstance(alias_value, frog_ast.Expression):
            return _substitute_aliases(
                alias_value, aliases, strip_prefixes, _visited | {expr.name}
            )
        return expr
    if isinstance(expr, frog_ast.BinaryOperation):
        return frog_ast.BinaryOperation(
            expr.operator,
            _substitute_aliases(
                expr.left_expression, aliases, strip_prefixes, _visited
            ),
            _substitute_aliases(
                expr.right_expression, aliases, strip_prefixes, _visited
            ),
        )
    if isinstance(expr, frog_ast.UnaryOperation):
        return frog_ast.UnaryOperation(
            expr.operator,
            _substitute_aliases(expr.expression, aliases, strip_prefixes, _visited),
        )
    return expr


def _canonical_arith_str(expr: frog_ast.Expression) -> str:
    """Return a canonical string for a bitstring parameterization.

    Pure arithmetic expressions over integers and named variables are
    canonicalized via sympy so syntactic variants (``lambda + 2 *
    lambda`` vs ``3 * lambda``) collapse to the same string. Anything
    sympy can't represent falls back to the raw ``str(expr)``.
    """
    # pylint: disable=import-outside-toplevel
    try:
        from sympy import Symbol  # noqa: F401  (local symbol intern)
        from ... import visitors as _vis
    except ImportError:
        return str(expr)
    names: set[str] = set()
    _collect_variable_names(expr, names)
    variables = {n: Symbol(n) for n in names}
    visitor = _vis.FrogToSympyVisitor(variables)
    try:
        result = visitor.visit(expr)
    except Exception:  # pylint: disable=broad-exception-caught
        return str(expr)
    if result is None:
        return str(expr)
    return str(result)


def _collect_variable_names(expr: frog_ast.Expression, out: set[str]) -> None:
    if isinstance(expr, frog_ast.Variable):
        out.add(expr.name)
        return
    if isinstance(expr, frog_ast.BinaryOperation):
        _collect_variable_names(expr.left_expression, out)
        _collect_variable_names(expr.right_expression, out)
        return
    if isinstance(expr, frog_ast.UnaryOperation):
        _collect_variable_names(expr.expression, out)
        return
    if isinstance(expr, frog_ast.FieldAccess) and isinstance(
        expr.the_object, frog_ast.Variable
    ):
        # FieldAccess(O, name) — treat as a single opaque variable.
        out.add(f"{expr.the_object.name}__{expr.name}")


def _sanitize(s: str) -> str:
    """Turn an arbitrary expression string into a valid EC identifier suffix."""
    cleaned = re.sub(r"\W+", "_", s)
    cleaned = cleaned.strip("_")
    return cleaned


def _xor_name(bs_name: str) -> str:
    suffix = bs_name.removeprefix("bs")
    return f"xor{suffix}"


def _zero_name(bs_name: str) -> str:
    suffix = bs_name.removeprefix("bs")
    return f"zero{suffix}"


def _ring_theory(exp_type: str) -> str:
    """The EC theory qualifier of a stdlib exponent / ModInt type.

    ``Mq.zmod`` / ``G_Exp.zmod`` -> ``Mq`` / ``G_Exp`` (general ZModRing);
    ``G_P.ZModE.exp`` -> ``G_P.ZModE`` (prime PowZMod field). The ring ops
    are then ``<theory>.( + )`` etc.
    """
    if exp_type.endswith(".zmod"):
        return exp_type[: -len(".zmod")]
    if exp_type.endswith(".exp"):
        return exp_type[: -len(".exp")]
    return exp_type


def _group_theory(group_type: str) -> str:
    """The EC clone alias of a stdlib group type (``G.group`` -> ``G``)."""
    if group_type.endswith(".group"):
        return group_type[: -len(".group")]
    return group_type


def _add_name(exp_type: str) -> str:
    """Ring ``+`` op for a stdlib exponent/ModInt type (``Mq.zmod`` ->
    ``Mq.( + )``)."""
    return f"{_ring_theory(exp_type)}.( + )"


def _sub_name(exp_type: str) -> str:
    """Ring ``-`` op for a stdlib exponent/ModInt type (``Mq.zmod`` ->
    ``Mq.( - )``)."""
    return f"{_ring_theory(exp_type)}.( - )"


def _modint_mul_name(exp_type: str) -> str:
    """Ring ``*`` op for a stdlib exponent/ModInt type (``Mq.zmod`` ->
    ``Mq.( * )``)."""
    return f"{_ring_theory(exp_type)}.( * )"


def _modint_zero_name(exp_type: str) -> str:
    """Ring zero for a stdlib exponent/ModInt type (``Mq.zmod`` ->
    ``Mq.zero``)."""
    return f"{_ring_theory(exp_type)}.zero"


def _generator_name(group_type: str) -> str:
    """Generator of a stdlib group type (``G.group`` -> ``G.g``)."""
    return f"{_group_theory(group_type)}.g"


def _identity_name(group_type: str) -> str:
    """Identity of a stdlib group type (``G.group`` -> ``G.e``)."""
    return f"{_group_theory(group_type)}.e"


def _mul_name(group_type: str) -> str:
    """Group ``*`` op of a stdlib group type (``G.group`` -> ``G.( * )``)."""
    return f"{_group_theory(group_type)}.( * )"


def _div_name(group_type: str) -> str:
    """Group ``/`` op of a stdlib group type (``G.group`` -> ``G.( / )``)."""
    return f"{_group_theory(group_type)}.( / )"


def _function_distr_name(dom: str, codom: str) -> str:
    """Name for the uniform distribution over functions ``dom -> codom``."""
    return f"dfun_{_sanitize(dom)}_to_{_sanitize(codom)}"


def _ro_module_name(fname: str) -> str:
    """Holder-module name for a random-oracle function VALUE ``fname``.

    The RO is a function SAMPLED once per experiment (the ProofFrog theorem's
    ``let: Function<D,R> H <- Function<D,R>;``), not a fixed op. EC ``main()``
    takes no args and a sub-module cannot read a local of ``main``, so the
    sampled function lives in a tiny read-only holder module (``module RO_H = {
    var h : dom -> codom }``, sampled ``RO_H.h <$ dfun`` at the top of each
    ``Game_step`` main). ``v_H`` -> ``RO_H``; ``v_G`` -> ``RO_G`` (uppercase
    initial, as EC module names require)."""
    base = fname[2:] if fname.startswith("v_") else fname
    return "RO_" + base


def _slice_op_name(src_name: str, dst_name: str) -> str:
    """Name for an abstract slice op from ``src_name`` to ``dst_name``."""
    return f"slice_{src_name}_to_{dst_name}"


def _concat_op_name(left_name: str, right_name: str, result_name: str) -> str:
    """Name for an abstract concat op."""
    return f"concat_{left_name}_{right_name}_to_{result_name}"


def _concat3_op_name(
    left_name: str, right_name: str, gap_name: str, result_name: str
) -> str:
    """Name for an abstract 3-way concat op (partial-split)."""
    return f"concat3_{left_name}_{right_name}_{gap_name}_to_{result_name}"


def _paren_int(s: str) -> str:
    """Wrap an integer expression string in parens unless it's an atomic
    identifier or literal. Mirrors ``expr_translator._paren`` but tuned
    for the int-argument positions in slice/concat axioms (no whitespace
    expected in atomic forms).
    """
    if s.startswith("(") and s.endswith(")"):
        return s
    if any(op in s for op in "+-*/ "):
        return f"({s})"
    return s


def xor_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator to find the xor op name."""
    return _xor_name(ec_type.text)


def zero_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator to find the all-zero op name."""
    return _zero_name(ec_type.text)


def ring_theory_of(ec_type: ec_ast.EcType) -> str:
    """Exposed: the EC ring-theory qualifier of a stdlib exponent/ModInt
    type (``ModInt_q.zmod`` -> ``ModInt_q``; ``G_P.ZModE.exp`` ->
    ``G_P.ZModE``). Used by tactics needing the ring's ``ring``/smt lemmas."""
    return _ring_theory(ec_type.text)


def add_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator: ModInt additive ``+`` op."""
    return _add_name(ec_type.text)


def sub_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator: ModInt additive ``-`` op."""
    return _sub_name(ec_type.text)


def modint_mul_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator: ModInt ring ``*`` op."""
    return _modint_mul_name(ec_type.text)


def modint_zero_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator: ModInt additive zero."""
    return _modint_zero_name(ec_type.text)


def group_generator_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator: group generator constant."""
    return _generator_name(ec_type.text)


def group_identity_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator: group identity constant."""
    return _identity_name(ec_type.text)


def group_mul_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator: group ``*`` op."""
    return _mul_name(ec_type.text)


def group_div_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator: group ``/`` op."""
    return _div_name(ec_type.text)


def group_power_for(
    group_type: ec_ast.EcType,
    exp_type: ec_ast.EcType,
    base: str,
    exponent: str,
) -> str:
    """Render a stdlib group power ``base ^ exp`` for the translator.

    ``base``/``exponent`` are the already-rendered (and parenthesized)
    operands. Prime path uses the ergonomic field power ``<G>_P.( ^ )``;
    the general path routes through the base integer power ``<G>.( ^ )``
    over the ring representative ``<G>_Exp.asint``.
    """
    if exp_type.text.endswith(".exp"):
        # Prime field exponent type ``<G>_P.ZModE.exp``: the group power lives
        # on the PowZMod clone ``<G>_P`` (drop the trailing ``.ZModE.exp``).
        pow_theory = _ring_theory(exp_type.text).removesuffix(".ZModE")
        return f"{pow_theory}.( ^ ) {base} {exponent}"
    # General ring exponent: base integer power via the ring representative.
    group_alias = _group_theory(group_type.text)
    ring = _ring_theory(exp_type.text)
    return f"{group_alias}.( ^ ) {base} ({ring}.asint {exponent})"
