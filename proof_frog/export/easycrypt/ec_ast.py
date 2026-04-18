"""EasyCrypt AST nodes and pretty-printer.

Scope limited to what's needed for the Phase 1 walking skeleton: abstract
types, distribution operators, axioms, module types, modules (with procs),
and equiv-lemmas with admit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

# --- Type expressions ---------------------------------------------------


@dataclass(frozen=True)
class EcType:
    """A raw type expression, rendered verbatim (e.g. 'bs_lambda', 'int')."""

    text: str


# --- Top-level declarations ---------------------------------------------


@dataclass
class TypeDecl:
    """`type <name>.` or `type <name> = <definition>.`"""

    name: str
    definition: str | None = None


@dataclass
class OpDecl:
    """`op <name> : <signature>.` where signature is a raw string."""

    name: str
    signature: str


@dataclass
class Axiom:
    """``axiom <name> [(<module_args>)] [<memory_args>] : <formula>.``"""

    name: str
    formula: str
    module_args: list[ModuleParam] = field(default_factory=list)
    memory_args: list[str] = field(default_factory=list)


# --- Module type members -------------------------------------------------


@dataclass
class ProcParam:
    """A parameter to a proc: `name : type`."""

    name: str
    type: EcType


@dataclass
class ProcSig:
    """A procedure signature (used inside module types)."""

    name: str
    params: list[ProcParam]
    return_type: EcType


# --- Procedure bodies ---------------------------------------------------


@dataclass
class VarDecl:
    """`var <name> : <type>;`"""

    name: str
    type: EcType


@dataclass
class Assign:
    """`<var> <- <rhs>;` where rhs is a raw string."""

    var: str
    rhs: str


@dataclass
class Sample:
    """`<var> <$ <distr>;` where distr is a raw string."""

    var: str
    distr: str


@dataclass
class Call:
    """`<var> <@ <callee>(<args>);` where args is already rendered."""

    var: str
    callee: str
    args: str


@dataclass
class Return:
    """`return <expr>;` where expr is a raw string."""

    expr: str


EcStmt = Union[VarDecl, Assign, Sample, Call, Return]


@dataclass
class Proc:
    """A procedure implementation."""

    name: str
    params: list[ProcParam]
    return_type: EcType
    body: list[EcStmt]


# --- Modules -------------------------------------------------------------


@dataclass
class ModuleType:
    """``module type <name> [(<params>)] = { <procs> }.``"""

    name: str
    procs: list[ProcSig]
    params: list[ModuleParam] = field(default_factory=list)


@dataclass
class ModuleParam:
    """A module parameter: `(E : SymEnc)`."""

    name: str
    module_type: str


@dataclass
class Module:
    """`module <name> [(<params>)] [: <iface>] = { <procs> }.`"""

    name: str
    procs: list[Proc]
    params: list[ModuleParam] = field(default_factory=list)
    implements: str | None = None


@dataclass
class ProbLemma:
    """A lemma with module / memory params and a free-form statement.

    Renders as::

        lemma <name> [<module_args>] [<memory_args>] :
          <statement>.
        proof.
          <body line 1>
          <body line 2>
          ...

    The body must end with ``"qed."``.
    """

    name: str
    module_args: list[ModuleParam]
    memory_args: list[str]
    statement: str
    body: list[str] = field(default_factory=list)


@dataclass
class Lemma:
    """An equiv lemma.

    Renders as::

        lemma <name> [<module_args>] :
          equiv [ <left> ~ <right> : <pre> ==> <post> ].
        proof.
          <body line 1>
          <body line 2>
          ...
        qed.

    The ``body`` list contains tactic lines without the surrounding
    ``proof.`` and ``qed.``; the pretty-printer adds those. If the body
    is empty, the lemma renders ``proof. admit. qed.`` as a fallback.
    """

    name: str
    module_args: list[ModuleParam]
    left: str
    right: str
    precondition: str
    postcondition: str
    body: list[str] = field(default_factory=list)


# --- The whole file ------------------------------------------------------


@dataclass
class AbstractTheory:
    """``abstract theory <name>. <decls...> end <name>.``"""

    name: str
    decls: list[EcTopDecl] = field(default_factory=list)


@dataclass
class Clone:
    """``clone <source_theory> as <alias> [with <bindings>].``"""

    source_theory: str
    alias: str
    type_bindings: list[tuple[str, str]] = field(default_factory=list)
    op_bindings: list[tuple[str, str]] = field(default_factory=list)


def qualified(clone_alias: str, local_name: str) -> str:
    """Return ``<clone_alias>.<local_name>`` for referencing cloned names."""
    return f"{clone_alias}.{local_name}"


@dataclass
class DeclareModule:
    """``declare module <name> <: <module_type> [{-<m1>, -<m2>, ...}].``

    Only valid inside a ``Section``. At ``end section.``, EasyCrypt
    generalizes all lemmas in the section over these abstract modules.
    ``disjoint_from`` lists other declared module names whose state must
    be disjoint from this one (needed for ``swap`` to commute calls across
    modules in proofs).
    """

    name: str
    module_type: str
    disjoint_from: list[str] = field(default_factory=list)


@dataclass
class Section:
    """``section [<name>]. <decls...> end [<name>].``

    Wraps a block of declarations. Lemmas inside a section are
    generalized over any ``declare module`` names at ``end``.
    """

    name: str | None
    decls: list[EcTopDecl] = field(default_factory=list)


EcTopDecl = Union[
    TypeDecl,
    OpDecl,
    Axiom,
    ModuleType,
    Module,
    Lemma,
    ProbLemma,
    DeclareModule,
    "AbstractTheory",
    "Clone",
    "Section",
    str,
]


@dataclass
class EcFile:
    """Top-level EasyCrypt file.

    `requires` is a list of import names for the initial `require import` line.
    `decls` is the ordered list of top-level declarations. A bare `str`
    element renders as a literal line (useful for comments / blank lines).
    """

    requires: list[str]
    decls: list[EcTopDecl]


# --- Pretty-printer ------------------------------------------------------


def pretty_print(ec_file: EcFile) -> str:
    """Render an EcFile as EasyCrypt source text."""
    lines: list[str] = []
    lines.append("(* Auto-generated by ProofFrog. Do not edit. *)")
    if ec_file.requires:
        lines.append(f"require import {' '.join(ec_file.requires)}.")
    lines.append("")
    for decl in ec_file.decls:
        lines.extend(_render_decl(decl))
        lines.append("")
    return "\n".join(lines)


def _render_decl(decl: EcTopDecl) -> list[str]:
    if isinstance(decl, str):
        return [decl]
    if isinstance(decl, TypeDecl):
        if decl.definition is not None:
            return [f"type {decl.name} = {decl.definition}."]
        return [f"type {decl.name}."]
    if isinstance(decl, OpDecl):
        return [f"op {decl.name} : {decl.signature}."]
    if isinstance(decl, Axiom):
        header = f"axiom {decl.name}"
        if decl.module_args:
            args = " ".join(f"({p.name} <: {p.module_type})" for p in decl.module_args)
            header += f" {args}"
        if decl.memory_args:
            header += " " + " ".join(decl.memory_args)
        if not decl.module_args and not decl.memory_args:
            return [f"{header} : {decl.formula}."]
        return [f"{header} :", f"  {decl.formula}."]
    if isinstance(decl, ModuleType):
        header = f"module type {decl.name}"
        if decl.params:
            param_str = ", ".join(f"{p.name} : {p.module_type}" for p in decl.params)
            header += f" ({param_str})"
        out = [f"{header} = {{"]
        for proc in decl.procs:
            out.append(f"  {_render_proc_sig(proc)}")
        out.append("}.")
        return out
    if isinstance(decl, Module):
        return _render_module(decl)
    if isinstance(decl, Lemma):
        return _render_lemma(decl)
    if isinstance(decl, ProbLemma):
        return _render_prob_lemma(decl)
    if isinstance(decl, AbstractTheory):
        return _render_abstract_theory(decl)
    if isinstance(decl, Clone):
        return _render_clone(decl)
    if isinstance(decl, DeclareModule):
        suffix = ""
        if decl.disjoint_from:
            suffix = " {" + ", ".join(f"-{n}" for n in decl.disjoint_from) + "}"
        return [f"declare module {decl.name} <: {decl.module_type}{suffix}."]
    if isinstance(decl, Section):
        return _render_section(decl)
    raise TypeError(f"Unknown top-level decl: {type(decl).__name__}")


def _render_section(section: Section) -> list[str]:
    header = "section" if section.name is None else f"section {section.name}"
    out = [f"{header}."]
    for i, inner in enumerate(section.decls):
        if i > 0:
            out.append("")
        for line in _render_decl(inner):
            out.append(f"  {line}" if line else line)
    footer = "end section" if section.name is None else f"end section {section.name}"
    out.append(f"{footer}.")
    return out


def _render_abstract_theory(theory: AbstractTheory) -> list[str]:
    out = [f"abstract theory {theory.name}."]
    for i, inner in enumerate(theory.decls):
        if i > 0:
            out.append("")
        for line in _render_decl(inner):
            out.append(f"  {line}" if line else line)
    out.append(f"end {theory.name}.")
    return out


def _render_clone(clone: Clone) -> list[str]:
    bindings: list[str] = []
    for name, concrete in clone.type_bindings:
        bindings.append(f"type {name} <- {concrete}")
    for name, concrete in clone.op_bindings:
        bindings.append(f"op {name} <- {concrete}")
    if not bindings:
        return [f"clone {clone.source_theory} as {clone.alias}."]
    out = [f"clone {clone.source_theory} as {clone.alias} with"]
    for i, binding in enumerate(bindings):
        terminator = "." if i == len(bindings) - 1 else ","
        out.append(f"  {binding}{terminator}")
    return out


def _render_prob_lemma(lemma: ProbLemma) -> list[str]:
    header = f"lemma {lemma.name}"
    if lemma.module_args:
        args = " ".join(f"({p.name} <: {p.module_type})" for p in lemma.module_args)
        header += f" {args}"
    if lemma.memory_args:
        header += " " + " ".join(lemma.memory_args)
    out = [f"{header} :"]
    out.append(f"  {lemma.statement}.")
    if not lemma.body:
        out.append("proof. admit. qed.")
        return out
    out.append("proof.")
    for line in lemma.body:
        out.append(f"  {line}")
    return out


def _render_proc_sig(proc: ProcSig) -> str:
    param_str = ", ".join(f"{p.name} : {p.type.text}" for p in proc.params)
    return f"proc {proc.name}({param_str}) : {proc.return_type.text}"


def _render_module(module: Module) -> list[str]:
    header = f"module {module.name}"
    if module.params:
        param_str = ", ".join(f"{p.name} : {p.module_type}" for p in module.params)
        header += f" ({param_str})"
    if module.implements is not None:
        header += f" : {module.implements}"
    header += " = {"
    out = [header]
    for proc in module.procs:
        out.extend(_render_proc_impl(proc))
    out.append("}.")
    return out


def _render_proc_impl(proc: Proc) -> list[str]:
    param_str = ", ".join(f"{p.name} : {p.type.text}" for p in proc.params)
    out = [f"  proc {proc.name}({param_str}) : {proc.return_type.text} = {{"]
    for stmt in proc.body:
        out.append(f"    {_render_stmt(stmt)}")
    out.append("  }")
    return out


def _render_stmt(stmt: EcStmt) -> str:
    if isinstance(stmt, VarDecl):
        return f"var {stmt.name} : {stmt.type.text};"
    if isinstance(stmt, Assign):
        return f"{stmt.var} <- {stmt.rhs};"
    if isinstance(stmt, Sample):
        return f"{stmt.var} <$ {stmt.distr};"
    if isinstance(stmt, Call):
        return f"{stmt.var} <@ {stmt.callee}({stmt.args});"
    if isinstance(stmt, Return):
        return f"return {stmt.expr};"
    raise TypeError(f"Unknown statement: {type(stmt).__name__}")


def _render_lemma(lemma: Lemma) -> list[str]:
    header = f"lemma {lemma.name}"
    if lemma.module_args:
        arg_str = " ".join(f"({p.name} <: {p.module_type})" for p in lemma.module_args)
        header += f" {arg_str}"
    out = [f"{header} :"]
    out.append(f"  equiv [ {lemma.left} ~ {lemma.right} :")
    out.append(f"          {lemma.precondition} ==> {lemma.postcondition} ].")
    if not lemma.body:
        out.append("proof. admit. qed.")
        return out
    out.append("proof.")
    for line in lemma.body:
        out.append(f"  {line}")
    return out
