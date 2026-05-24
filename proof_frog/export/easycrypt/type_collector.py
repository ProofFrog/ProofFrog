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
            return "bs_t" if self._theory_mode else "bs"
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
            return f"bs_{sanitized}_t" if sanitized else "bs_t"
        return f"bs_{sanitized}" if sanitized else "bs"

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
          ``axiom d<name>_ll`` / ``axiom d<name>_fu``.
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
        """
        key = (left_name, right_name, result_name)
        if key not in self._concat_op_set:
            self._concat_op_set.add(key)
            self._concat_ops.append(key)
        return _concat_op_name(left_name, right_name, result_name)

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
        # lossless/funiform axioms. The type declaration itself is
        # emitted by the caller from the ``Set X;`` let bindings.
        for distr in self._known_abstract_distrs:
            type_name = distr[1:]
            decls.append(ec_ast.OpDecl(distr, f"{type_name} distr"))
            decls.append(ec_ast.Axiom(f"{distr}_ll", f"is_lossless {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_fu", f"is_funiform {distr}"))
        for name in self._names:
            suffix = name.removeprefix("bs")
            distr = f"dbs{suffix}"
            decls.append(ec_ast.TypeDecl(name))
            decls.append(ec_ast.OpDecl(distr, f"{name} distr"))
            decls.append(ec_ast.Axiom(f"{distr}_ll", f"is_lossless {distr}"))
            decls.append(ec_ast.Axiom(f"{distr}_fu", f"is_funiform {distr}"))
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


def xor_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator to find the xor op name."""
    return _xor_name(ec_type.text)
