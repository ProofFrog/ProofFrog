"""Primitives shared by the binding-challenge synthesizers.

A leaf module: it imports only :mod:`ec_ast`, so both
:mod:`.binding_challenge` (the two-KEM case-split route) and
:mod:`.single_r_challenge` (the single-reduction seedbased route) can depend on
it without an import cycle.

Two kinds of thing live here:

* **Symbolic evaluation** of a linear deterministic proc body into functional
  ``ev_<m>`` values -- :func:`subst`, :func:`split_top_args`, :func:`paren` and
  the forward walk :func:`walk_env` that both routes build their environments
  with.
* **Tactic fragments** emitted verbatim by both routes -- currently
  :func:`kdf_exists_elim`, the ``exists*``/``elim*`` line that freezes a KDF
  module's glob together with the two KDF inputs.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from . import ec_ast


def subst(expr: str, env: dict[str, str]) -> str:
    """Single-pass whole-word substitution of ``env`` keys in ``expr``.

    Keys are matched longest-first at word boundaries; a key never appears
    inside its own replacement in a way that would double-substitute because
    every referenced name is already fully resolved (the body is in SSA-ish
    order), so one pass suffices.
    """
    if not env:
        return expr
    keys = sorted(env, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b")
    return pattern.sub(lambda m: env[m.group(1)], expr)


def split_top_args(args: str) -> list[str]:
    """Split a rendered ``args`` string on top-level commas (nesting-aware)."""
    out: list[str] = []
    depth = 0
    cur = ""
    for ch in args:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def paren(expr: str) -> str:
    """Wrap ``expr`` in parens for use as a space-separated op argument."""
    e = expr.strip()
    if e.startswith("(") and e.endswith(")"):
        return e
    return f"({e})" if " " in e else e


def walk_env(
    stmts: Sequence[ec_ast.EcStmt],
    base: dict[str, str],
    clone_alias: dict[str, str],
    *,
    stop_at_if: bool = False,
) -> dict[str, str]:
    """Forward walk over a linear deterministic body building ``local ->
    functional value`` (SSA-ish, stable), seeded by ``base``.

    Each ``x <- e`` substitutes the prior functional values into ``e``; each
    ``x <@ M.m(a..)`` becomes ``x = (<clone(M)>.ev_m <a..>)``. Every other
    statement kind is skipped, except that ``stop_at_if`` halts the walk at the
    first :class:`~.ec_ast.If` -- the reduction-challenge routes functionalize
    only the *prefix* that precedes the collision guard.
    """
    env = dict(base)
    for stmt in stmts:
        if stop_at_if and isinstance(stmt, ec_ast.If):
            break
        if isinstance(stmt, ec_ast.Assign):
            env[stmt.var] = subst(stmt.rhs, env)
        elif isinstance(stmt, ec_ast.Call):
            module, _, method = stmt.callee.partition(".")
            args = [subst(a, env) for a in split_top_args(stmt.args)]
            ev = f"{clone_alias[module]}.ev_{method}"
            applied = "".join(f" {paren(a)}" for a in args)
            env[stmt.var] = f"({ev}{applied})"
    return env


def kdf_exists_elim(
    h_module: str,
    side: str,
    elim_names: tuple[str, str, str],
    indent: str = "  ",
) -> str:
    """The ``exists*``/``elim*`` line freezing the KDF module's glob and its two
    KDF inputs on one memory side.

    Renders ``<indent>exists* (glob <H>)<side>, kdf_in_0<side>, kdf_in_1<side>;
    elim* => <g> <k0> <k1>.`` -- the standard preamble before discharging the
    two ``H.evaluate`` calls with ``<H>_evaluate_det``. ``side`` is the EC memory
    annotation, ``"{1}"`` or ``"{2}"``.
    """
    glob_name, in0, in1 = elim_names
    return (
        f"{indent}exists* (glob {h_module}){side}"
        f", kdf_in_0{side}"
        f", kdf_in_1{side}"
        f"; elim* => {glob_name} {in0} {in1}."
    )


def kdf_freeze_and_evaluate(
    h_module: str,
    side: str,
    elim_names: tuple[str, str, str],
    indent: str = "  ",
) -> list[str]:
    """Freeze the KDF glob + inputs (:func:`kdf_exists_elim`) and discharge the
    two ``H.evaluate(kdf_in_i)`` calls with ``<H>_evaluate_det``.

    The calls are peeled back-to-front (``kdf_in_1`` first), which is the order
    ``wp`` leaves them in. This is the whole no-collision-branch body shared by
    the two-KEM case-split route and the single-reduction route.
    """
    glob_name, in0, in1 = elim_names
    return [
        kdf_exists_elim(h_module, side, elim_names, indent),
        f"{indent}wp.",
        f"{indent}call{side} ({h_module}_evaluate_det {glob_name} {in1}).",
        f"{indent}call{side} ({h_module}_evaluate_det {glob_name} {in0}).",
    ]


def split_app(text: str) -> tuple[str, list[str]] | None:
    """Split a rendered prefix application into ``(head, args)``.

    ``"(f (g a) b)"`` -> ``("f", ["(g a)", "b"])``; ``"x"`` -> ``("x", [])``.
    Returns ``None`` for anything that is not a head-then-arguments term
    (an infix expression, a projection, a parenthesised tuple, ...), which is
    the signal to treat the term as an opaque leaf.
    """
    t = text.strip()
    while t.startswith("(") and t.endswith(")"):
        depth = 0
        for i, ch in enumerate(t):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(t) - 1:
                    return None  # not a single parenthesised term
        t = t[1:-1].strip()
    parts: list[str] = []
    depth = 0
    cur = ""
    for ch in t:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == " " and depth == 0:
            if cur:
                parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        parts.append(cur)
    if not parts:
        return None
    head = parts[0]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", head):
        return None
    return head, parts[1:]


def concat_collision_peel(
    term: str,
    inj_of_ev: dict[str, tuple[str, str]],
    hyp: str = "h",
) -> tuple[list[str], set[str], set[tuple[str, str]]]:
    """Peel a nested-``concat_*`` term down to its leaves, TERM-FREE.

    ``term`` is one side's rendered KDF-input value; only its *structure* is
    read, never its text. Each internal ``concat_<L>_<R>_to_<Res>`` node emits

    ``have h<k> := <op>_injL _ _ _ _ <parent-hyp>.``

    (and the ``_injR`` twin), whose four ``_``s let EC unify the component terms
    off the parent hypothesis. That is what makes this usable after
    ``skip => />``, which normalises the goal to a MIX of memory annotations no
    statically-built term text can match -- the failure mode that defeated every
    term-based peel here.

    A leaf ``<alias>.ev_<method> <arg>`` whose method is declared ``injective``
    additionally emits ``have h<k> := <M>_<m>_inj _ _ <hyp>.``, stripping the
    encoding.

    Returns ``(lines, concat_ops_used, inj_methods_requested)``. The ops need
    their ``_injL``/``_injR`` lemmas emitted (``TypeCollector.request_concat_inj``)
    and the methods their ``_inj`` axioms (``inj_method_requests``).
    """
    lines: list[str] = []
    ops: set[str] = set()
    injs: set[tuple[str, str]] = set()
    counter = [0]

    def fresh() -> str:
        counter[0] += 1
        return f"hcp{counter[0]}"

    def walk(node: str, parent: str) -> None:
        split = split_app(node)
        if split is None:
            return
        head, args = split
        if head.startswith("concat_") and len(args) == 2:
            ops.add(head)
            left, right = fresh(), fresh()
            lines.append(f"have {left} := {head}_injL _ _ _ _ {parent}.")
            lines.append(f"have {right} := {head}_injR _ _ _ _ {parent}.")
            walk(args[0], left)
            walk(args[1], right)
            return
        if len(args) == 1 and head in inj_of_ev:
            module, method = inj_of_ev[head]
            injs.add((module, method))
            lines.append(f"have {fresh()} := {module}_{method}_inj _ _ {parent}.")

    walk(term, hyp)
    return lines, ops, injs
