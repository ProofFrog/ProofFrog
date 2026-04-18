"""Scheme-instance descriptors for EasyCrypt export.

A proof's ``let:`` block may contain multiple scheme instances. For
the single-scheme case (``OTP E = OTP(lambda);``) this is trivial.
For multi-scheme proofs (``ChainedEncryption``) each instance gets
its own clone of the primitive theory, with type-bindings resolved
through any dependent instances.

Each :class:`SchemeInstance` records:

* ``let_name`` — the FrogLang let-binding name (``E1``, ``CE``).
* ``clone_alias`` — the EC clone alias (``E1_c``, ``CE_c``).
* ``concretized_fields`` — mapping from primitive field name
  (``"Message"``, ``"Key"``, ``"Ciphertext"``) to the resolved
  FrogLang :class:`~proof_frog.frog_ast.Type` (typically a
  :class:`~proof_frog.frog_ast.Variable` pointing at a top-level
  abstract EC type, or a :class:`~proof_frog.frog_ast.ProductType`
  for tuple fields).

The ``concretized_fields`` entries feed both the clone's
``type <field> <- <concrete>`` bindings and the exporter's
qualified alias map (``"E1.Key" -> Variable("KeySpace1")``).
"""

from __future__ import annotations

from dataclasses import dataclass

from ... import frog_ast


@dataclass
class SchemeInstance:
    let_name: str
    clone_alias: str
    concretized_fields: dict[str, frog_ast.Type]


def collect(
    proof: frog_ast.ProofFile,
    primitive: frog_ast.Primitive,
    scheme: frog_ast.Scheme,
) -> list[SchemeInstance]:
    """Walk ``proof.lets`` and produce one SchemeInstance per scheme let.

    Scheme instances are processed in declaration order so that an
    instance referencing prior instances (``CE = ChainedEncryption(E1,
    E2)``) resolves correctly.
    """
    instances: list[SchemeInstance] = []
    # Map let_name -> concretized_fields for already-processed instances
    prior: dict[str, dict[str, frog_ast.Type]] = {}

    for let in proof.lets:
        if not (
            isinstance(let.type, frog_ast.Variable)
            and isinstance(let.value, frog_ast.FuncCall)
            and isinstance(let.value.func, frog_ast.Variable)
        ):
            continue
        ctor = let.value.func.name
        args = let.value.args
        if ctor == primitive.name:
            concret = _concretize_primitive(primitive, args)
        elif ctor == scheme.name:
            concret = _concretize_scheme(scheme, args, prior)
        else:
            continue
        inst = SchemeInstance(
            let_name=let.name,
            clone_alias=f"{let.name}_c",
            concretized_fields=concret,
        )
        instances.append(inst)
        prior[let.name] = concret

    return instances


def _concretize_primitive(
    primitive: frog_ast.Primitive, args: list[frog_ast.Expression]
) -> dict[str, frog_ast.Type]:
    """Substitute primitive parameters into field values.

    For ``SymEnc(IntermediateSpace, CiphertextSpace1, KeySpace1)``, the
    primitive's field ``Set Message = MessageSpace;`` (where
    ``MessageSpace`` is the first parameter) concretizes to
    ``IntermediateSpace``.
    """
    sub: dict[str, frog_ast.Expression] = {
        p.name: a for p, a in zip(primitive.parameters, args)
    }
    out: dict[str, frog_ast.Type] = {}
    for f in primitive.fields:
        if f.value is None:
            continue
        resolved = _substitute(f.value, sub, prior={})
        if isinstance(resolved, frog_ast.Type):
            out[f.name] = resolved
    return out


def _concretize_scheme(
    scheme: frog_ast.Scheme,
    args: list[frog_ast.Expression],
    prior: dict[str, dict[str, frog_ast.Type]],
) -> dict[str, frog_ast.Type]:
    """Substitute scheme parameters into field values; resolve through prior instances.

    For ``ChainedEncryption(E1, E2)``, scheme parameter ``E1`` (of
    scheme-typed parameter ``SymEnc E1``) maps to the expression
    ``Variable("E1")`` (the let-binding name), so a field value
    ``E1.Key`` becomes ``FieldAccess(Variable("E1"), "Key")``. The
    resolver then looks up ``prior["E1"]["Key"]`` to concretize.
    """
    sub: dict[str, frog_ast.Expression] = {
        p.name: a for p, a in zip(scheme.parameters, args)
    }
    out: dict[str, frog_ast.Type] = {}
    for f in scheme.fields:
        if f.value is None:
            continue
        resolved = _substitute(f.value, sub, prior)
        if isinstance(resolved, frog_ast.Type):
            out[f.name] = resolved
        elif isinstance(resolved, frog_ast.Tuple):
            # A Tuple in type-position acts as a ProductType.
            typed: list[frog_ast.Type] = [
                v for v in resolved.values if isinstance(v, frog_ast.Type)
            ]
            if len(typed) == len(resolved.values):
                out[f.name] = frog_ast.ProductType(typed)
    return out


def _substitute(
    node: frog_ast.ASTNode,
    sub: dict[str, frog_ast.Expression],
    prior: dict[str, dict[str, frog_ast.Type]],
) -> frog_ast.ASTNode:
    """Substitute ``sub`` references in ``node`` and resolve qualified
    field accesses through ``prior``.

    Handles the subset of AST shapes that appear in primitive/scheme
    field values: ``Variable``, ``FieldAccess``, ``Tuple``,
    ``ProductType``.
    """
    if isinstance(node, frog_ast.Variable):
        if node.name in sub:
            return sub[node.name]
        return node
    if isinstance(node, frog_ast.FieldAccess):
        base = _substitute(node.the_object, sub, prior)
        # Resolve <inst>.<Field> through prior instances if available.
        if isinstance(base, frog_ast.Variable) and base.name in prior:
            fields = prior[base.name]
            if node.name in fields:
                return fields[node.name]
        if base is node.the_object:
            return node
        assert isinstance(base, frog_ast.Expression)
        return frog_ast.FieldAccess(base, node.name)
    if isinstance(node, frog_ast.Tuple):
        new_vals = [_substitute(v, sub, prior) for v in node.values]
        assert all(isinstance(v, frog_ast.Expression) for v in new_vals)
        return frog_ast.Tuple(
            [v for v in new_vals if isinstance(v, frog_ast.Expression)]
        )
    if isinstance(node, frog_ast.ProductType):
        new_types: list[frog_ast.Type] = []
        for t in node.types:
            resolved = _substitute(t, sub, prior)
            assert isinstance(resolved, frog_ast.Type)
            new_types.append(resolved)
        return frog_ast.ProductType(new_types)
    return node
