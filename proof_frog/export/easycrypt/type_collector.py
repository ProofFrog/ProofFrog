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
    ) -> None:
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
        # Abstract-types check runs before alias resolution so that
        # primitive-level types (Key, Message, Ciphertext) stay abstract
        # even when a scheme alias would otherwise concretize them.
        abstract = self._abstract_lookup(t)
        if abstract is not None:
            if abstract not in self._abstract_seen:
                self._abstract_seen.append(abstract)
            return ec_ast.EcType(abstract)
        resolved = self.resolve(t)
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
            parts = [self.translate_type(sub).text for sub in resolved.types]
            return ec_ast.EcType(" * ".join(parts))
        if (
            isinstance(resolved, frog_ast.Variable)
            and resolved.name in self._known_abstract_types
        ):
            return ec_ast.EcType(resolved.name)
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

    def distr_for(self, ec_type: ec_ast.EcType) -> str:
        """Return the distribution op name for a sampled type.

        In abstract mode this yields ``d<name>`` (e.g. ``dciphertext``) and
        records that distribution for later emission. In concrete mode it
        yields ``dbs...`` for bitstring types. Product EC types
        (``A * B * ...``) yield ``dA `*` dB `*` ...``.
        """
        # Product type: recurse on each component.
        if " * " in ec_type.text and "(" not in ec_type.text:
            parts = [p.strip() for p in ec_type.text.split(" * ")]
            return " `*` ".join(self.distr_for(ec_ast.EcType(p)) for p in parts)
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
        for distr in self._abstract_distrs:
            type_name = distr[1:]  # strip 'd'
            decls.append(ec_ast.OpDecl(distr, f"{type_name} distr"))
            decls.append(ec_ast.Axiom(f"{distr}_ll", f"is_lossless {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_fu", f"is_funiform {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_full", f"is_full {distr}"))
        return decls

    @property
    def abstract_types_seen(self) -> list[str]:
        return list(self._abstract_seen)

    @property
    def abstract_distrs_seen(self) -> list[str]:
        return list(self._abstract_distrs)

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

    def bs_length_for(self, bs_name: str) -> str | None:
        """Return the canonical length expression string for a registered
        abstract bitstring, or ``None`` if the name isn't registered.
        Used by parametric tactic synthesizers (Split/Merge Uniform
        Samples) to render the bit-length integer expressions in
        slice/concat tactic arguments.
        """
        return self._bs_lengths.get(bs_name)

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
            decls.append(ec_ast.TypeDecl(name))
            decls.append(ec_ast.OpDecl(distr, f"{name} distr"))
            decls.append(ec_ast.Axiom(f"{distr}_ll", f"is_lossless {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_fu", f"is_funiform {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_full", f"is_full {distr}"))
        for name in self._names:
            xor_op = _xor_name(name)
            decls.append(ec_ast.OpDecl(xor_op, f"{name} -> {name} -> {name}"))
            decls.append(
                ec_ast.Axiom(
                    f"{xor_op}_invol",
                    f"forall (a b : {name}), {xor_op} ({xor_op} a b) b = a",
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
