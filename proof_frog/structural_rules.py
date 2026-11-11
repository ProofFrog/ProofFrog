"""Syntactic well-formedness rules checked on every parsed file.

These rules need names and scopes but no types, so name resolution runs them
on each file (the file being checked and every file it imports) before the
type checker:

- A length, modulus or size in a type (``BitString<n>``, ``ModInt<q>``,
  ``Array<T, n>``) and the length of a literal ``0^n`` / ``1^n`` may not name
  a variable that is assigned or drawn anywhere: only parameters, proof
  ``let:`` entries and variables never written after their declaration.  So a
  type means the same thing throughout an execution.

``check_structural_rules`` returns the violations in source order; the caller
reports them.
"""

from typing import Optional

from . import frog_ast
from . import visitors


class Violation:
    """A rule violation at an AST node."""

    def __init__(self, node: frog_ast.ASTNode, message: str) -> None:
        self.node = node
        self.message = message


class _Binding:
    """One declaration of a name (a parameter, field, local or binder)."""

    def __init__(self, name: str, kind: str) -> None:
        self.name = name
        self.kind = kind


class _SizeNameVisitor(visitors.Visitor[list[tuple[frog_ast.ASTNode, str]]]):
    """Every variable named by a length, modulus or size inside a node: the
    parameter of ``BitString<..>``, ``ModInt<..>``, ``Array<T, ..>`` and the
    length of ``0^..`` / ``1^..``, with the node of that type or literal."""

    def __init__(self) -> None:
        self.found: list[tuple[frog_ast.ASTNode, str]] = []

    def result(self) -> list[tuple[frog_ast.ASTNode, str]]:
        return self.found

    def _add(self, node: frog_ast.ASTNode, size: Optional[frog_ast.ASTNode]) -> None:
        if size is None:
            return
        for name in _variable_names(size):
            self.found.append((node, name))

    def visit_bit_string_type(self, node: frog_ast.BitStringType) -> None:
        self._add(node, node.parameterization)

    def visit_mod_int_type(self, node: frog_ast.ModIntType) -> None:
        self._add(node, node.modulus)

    def visit_array_type(self, node: frog_ast.ArrayType) -> None:
        self._add(node, node.count)

    def visit_bit_string_literal(self, node: frog_ast.BitStringLiteral) -> None:
        self._add(node, node.length)


class _VariableNameVisitor(visitors.Visitor[list[str]]):
    """The names of all variables in an expression, the object of a member
    access included (``E.lambda`` names ``E``)."""

    def __init__(self) -> None:
        self.names: list[str] = []

    def result(self) -> list[str]:
        return self.names

    def visit_variable(self, node: frog_ast.Variable) -> None:
        if node.name not in self.names:
            self.names.append(node.name)


def _variable_names(node: frog_ast.ASTNode) -> list[str]:
    return _VariableNameVisitor().visit(node)


def _sizes_in(node: Optional[frog_ast.ASTNode]) -> list[tuple[frog_ast.ASTNode, str]]:
    if node is None:
        return []
    return _SizeNameVisitor().visit(node)


def _written_base(target: frog_ast.ASTNode) -> Optional[str]:
    """The variable a write to ``target`` changes: ``x`` for ``x``,
    ``x[i]`` and ``x[i][j]``; None for anything else."""
    while isinstance(target, (frog_ast.ArrayAccess, frog_ast.Slice)):
        target = target.the_array
    if isinstance(target, frog_ast.Variable):
        return target.name
    return None


class _ComponentChecker:
    """Walks one game, reduction, scheme or primitive with its scopes."""

    def __init__(self) -> None:
        self.scopes: list[dict[str, _Binding]] = []
        self.written: set[int] = set()
        self.size_uses: list[tuple[frog_ast.ASTNode, str, _Binding]] = []
        self.violations: list[Violation] = []

    def _lookup(self, name: str) -> Optional[_Binding]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _record_sizes(self, node: Optional[frog_ast.ASTNode]) -> None:
        for use_node, name in _sizes_in(node):
            binding = self._lookup(name)
            if binding is not None:
                self.size_uses.append((use_node, name, binding))

    def _write(self, target: frog_ast.ASTNode) -> None:
        if isinstance(target, frog_ast.Tuple):
            for value in target.values:
                self._write(value)
            return
        name = _written_base(target)
        if name is None:
            return
        binding = self._lookup(name)
        if binding is not None:
            self.written.add(id(binding))

    def _declare(self, _node: frog_ast.ASTNode, name: str) -> None:
        self.scopes[-1][name] = _Binding(name, "local")

    def check(self, component: frog_ast.ASTNode) -> list[Violation]:
        parameters: list[frog_ast.Parameter] = getattr(component, "parameters", [])
        fields: list[frog_ast.Field] = getattr(component, "fields", [])
        methods: list[frog_ast.Method | frog_ast.MethodSignature] = getattr(
            component, "methods", []
        )
        self.scopes = [{}]
        for param in parameters:
            self._record_sizes(param.type)
            self.scopes[0][param.name] = _Binding(param.name, "parameter")
        for field in fields:
            self._record_sizes(field.type)
            self._record_sizes(field.value)
            self.scopes[0][field.name] = _Binding(field.name, "field")
        for method in methods:
            if isinstance(method, frog_ast.MethodSignature):
                self._check_signature(method)
            else:
                self._check_method(method)
        for use_node, name, binding in self.size_uses:
            if id(binding) in self.written:
                self.violations.append(
                    Violation(
                        use_node,
                        f"The size in {use_node} names {binding.kind} '{name}',"
                        " which is assigned or sampled: a length, modulus or"
                        " size in a type may name only parameters, let entries"
                        " and variables never written after their declaration",
                    )
                )
        return self.violations

    def _check_signature(self, signature: frog_ast.MethodSignature) -> None:
        self._record_sizes(signature.return_type)
        self.scopes.append({})
        for param in signature.parameters:
            self._record_sizes(param.type)
            self.scopes[-1][param.name] = _Binding(param.name, "parameter")
        self.scopes.pop()

    def _check_method(self, method: frog_ast.Method) -> None:
        signature = method.signature
        self._record_sizes(signature.return_type)
        params: dict[str, _Binding] = {}
        for param in signature.parameters:
            self._record_sizes(param.type)
            params[param.name] = _Binding(param.name, "parameter")
        self.scopes.append(dict(params))
        self._check_block(method.block)
        self.scopes.pop()

    def _check_block(self, block: frog_ast.Block) -> None:
        self.scopes.append({})
        for statement in block.statements:
            self._check_statement(statement)
        self.scopes.pop()

    def _check_statement(self, statement: frog_ast.Statement) -> None:
        # pylint: disable=too-many-branches
        if isinstance(statement, frog_ast.Block):
            self._check_block(statement)
        elif isinstance(statement, frog_ast.IfStatement):
            for condition in statement.conditions:
                self._record_sizes(condition)
            for block in statement.blocks:
                self._check_block(block)
        elif isinstance(statement, frog_ast.NumericFor):
            self._record_sizes(statement.start)
            self._record_sizes(statement.end)
            self.scopes.append({})
            self._declare(statement, statement.name)
            self._check_block(statement.block)
            self.scopes.pop()
        elif isinstance(statement, frog_ast.GenericFor):
            self._record_sizes(statement.var_type)
            self._record_sizes(statement.over)
            self.scopes.append({})
            self._declare(statement, statement.var_name)
            self._check_block(statement.block)
            self.scopes.pop()
        elif isinstance(statement, frog_ast.VariableDeclaration):
            self._record_sizes(statement.type)
            self._declare(statement, statement.name)
        elif isinstance(
            statement, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            self._record_sizes(statement.the_type)
            if isinstance(statement, frog_ast.Assignment):
                self._record_sizes(statement.value)
            else:
                self._record_sizes(statement.sampled_from)
            if isinstance(statement, frog_ast.UniqueSample):
                self._record_sizes(statement.unique_set)
                if statement.surface_form == "uniq":
                    # '<-uniq[S]' inserts the draw into S.
                    self._write(statement.unique_set)
            if statement.the_type is not None and isinstance(
                statement.var, frog_ast.Variable
            ):
                self._declare(statement, statement.var.name)
            else:
                self._record_sizes(statement.var)
                self._write(statement.var)
        else:
            self._record_sizes(statement)


def _components(root: frog_ast.ASTNode) -> list[frog_ast.ASTNode]:
    if isinstance(root, (frog_ast.Primitive, frog_ast.Scheme, frog_ast.Game)):
        return [root]
    if isinstance(root, frog_ast.GameFile):
        return list(root.games)
    if isinstance(root, frog_ast.ProofFile):
        return [
            helper
            for helper in root.helpers
            if isinstance(helper, (frog_ast.Game, frog_ast.Scheme))
        ]
    return []


def check_structural_rules(root: frog_ast.ASTNode) -> list[Violation]:
    """The violations of this module's rules in a parsed file."""
    violations: list[Violation] = []
    for component in _components(root):
        violations.extend(_ComponentChecker().check(component))
    return violations
