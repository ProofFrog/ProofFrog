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

    def __init__(
        self,
        aliases: dict[str, frog_ast.Type] | None = None,
        abstract_types: dict[str, str] | None = None,
        known_abstract_types: set[str] | None = None,
    ) -> None:
        self._names: list[str] = []  # ordered, unique
        self._seen: set[str] = set()
        # Alias keys may be plain (``"Key"``) or qualified
        # (``"E1.key"``). Qualified keys resolve ``FieldAccess`` types
        # through per-instance scheme clones in multi-scheme exports.
        self._aliases: dict[str, frog_ast.Type] = dict(aliases) if aliases else {}
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

    @staticmethod
    def _bitstring_name(t: frog_ast.BitStringType) -> str:
        length_str = str(t.parameterization) if t.parameterization else ""
        sanitized = _sanitize(length_str)
        return f"bs_{sanitized}" if sanitized else "bs"

    def distr_for(self, ec_type: ec_ast.EcType) -> str:
        """Return the distribution op name for a sampled type.

        In abstract mode this yields ``d<name>`` (e.g. ``dciphertext``) and
        records that distribution for later emission. In concrete mode it
        yields ``dbs...`` for bitstring types.
        """
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
        return f"dbs{suffix}"

    def emit_abstract(self) -> list[ec_ast.EcTopDecl]:
        """Produce EC decls for abstract types + distributions seen.

        Used inside an ``abstract theory``. Emits:

        * one ``type <name>.`` per abstract type,
        * for each distribution used: ``op d<name> : <name> distr.`` plus
          ``axiom d<name>_ll`` / ``axiom d<name>_fu``.
        """
        decls: list[ec_ast.EcTopDecl] = []
        for name in self._abstract_seen:
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
        return decls


def _sanitize(s: str) -> str:
    """Turn an arbitrary expression string into a valid EC identifier suffix."""
    cleaned = re.sub(r"\W+", "_", s)
    cleaned = cleaned.strip("_")
    return cleaned


def _xor_name(bs_name: str) -> str:
    suffix = bs_name.removeprefix("bs")
    return f"xor{suffix}"


def xor_name_for(ec_type: ec_ast.EcType) -> str:
    """Exposed for the expression translator to find the xor op name."""
    return _xor_name(ec_type.text)
