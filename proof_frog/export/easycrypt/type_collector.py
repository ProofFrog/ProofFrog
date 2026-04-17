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

    def __init__(self, aliases: dict[str, frog_ast.Type] | None = None) -> None:
        self._names: list[str] = []  # ordered, unique
        self._seen: set[str] = set()
        self._aliases: dict[str, frog_ast.Type] = dict(aliases) if aliases else {}

    def resolve(self, t: frog_ast.Type) -> frog_ast.Type:
        """Resolve type aliases by name; unwrap OptionalType."""
        if isinstance(t, frog_ast.OptionalType):
            return self.resolve(t.the_type)
        if isinstance(t, frog_ast.Variable):
            if t.name in self._aliases:
                return self.resolve(self._aliases[t.name])
        if isinstance(t, frog_ast.FieldAccess):
            if t.name in self._aliases:
                return self.resolve(self._aliases[t.name])
        return t

    def translate_type(self, t: frog_ast.Type) -> ec_ast.EcType:
        """Translate a FrogLang type to an EC type, registering it."""
        resolved = self.resolve(t)
        if isinstance(resolved, frog_ast.BitStringType):
            name = self._bitstring_name(resolved)
            if name not in self._seen:
                self._seen.add(name)
                self._names.append(name)
            return ec_ast.EcType(name)
        raise NotImplementedError(
            f"Type translation not implemented for {type(resolved).__name__}: "
            f"{resolved}"
        )

    @staticmethod
    def _bitstring_name(t: frog_ast.BitStringType) -> str:
        length_str = str(t.parameterization) if t.parameterization else ""
        sanitized = _sanitize(length_str)
        return f"bs_{sanitized}" if sanitized else "bs"

    def distr_for(self, ec_type: ec_ast.EcType) -> str:
        """Return the distribution op name for a bitstring type, e.g. 'dbs_lambda'."""
        assert ec_type.text.startswith("bs_") or ec_type.text == "bs"
        suffix = ec_type.text.removeprefix("bs")
        return f"dbs{suffix}"

    def emit(self) -> list[ec_ast.EcTopDecl]:
        """Produce top-level EC declarations for every registered type."""
        decls: list[ec_ast.EcTopDecl] = []
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
