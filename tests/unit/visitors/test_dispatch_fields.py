"""Visitor dispatch and structural child traversal regressions."""

import ast
import gc
import inspect
from pathlib import Path
from typing import Any, Iterator, Optional

import pytest

from proof_frog import frog_ast, frog_parser, visitors

_REPO_ROOT = Path(__file__).resolve().parents[3]


class _GameNames(visitors.Visitor[list[str]]):
    def __init__(self) -> None:
        self.names: list[str] = []

    def result(self) -> list[str]:
        return self.names

    def visit_game(self, node: frog_ast.Game) -> None:
        self.names.append(node.name)


class _VariableNames(visitors.Visitor[list[str]]):
    def __init__(self) -> None:
        self.names: list[str] = []

    def result(self) -> list[str]:
        return self.names

    def visit_variable(self, node: frog_ast.Variable) -> None:
        self.names.append(node.name)


def _reduction() -> frog_ast.Reduction:
    return frog_ast.Reduction(
        ("R", [], [], []),
        frog_ast.ParameterizedGame("G", []),
        frog_ast.ParameterizedGame("A", []),
    )


def test_dispatch_falls_back_to_node_base_class() -> None:
    assert _GameNames().visit(_reduction()) == ["R"]


class _MostSpecificHook(visitors.Visitor[list[str]]):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def result(self) -> list[str]:
        return self.calls

    def visit_game(self, node: frog_ast.Game) -> None:
        self.calls.append("game:" + node.name)

    def visit_reduction(self, node: frog_ast.Reduction) -> None:
        self.calls.append("reduction:" + node.name)


def test_visitor_dispatch_prefers_the_most_specific_hook() -> None:
    assert _MostSpecificHook().visit(_reduction()) == ["reduction:R"]
    game = frog_ast.Game(("G", [], [], []))
    assert _MostSpecificHook().visit(game) == ["game:G"]


class _RenameGames(visitors.Transformer):
    def transform_game(self, node: frog_ast.Game) -> frog_ast.Game:
        return frog_ast.Game((node.name + "'", [], [], []))


class _RenameViaGenericHook(visitors.Transformer):
    def __init__(self) -> None:
        self.seen: list[str] = []

    def transform_game(self, node: frog_ast.Game) -> frog_ast.Game:
        raise AssertionError(f"transform_game called on {type(node).__name__}")

    def transform_ast_node(self, node: frog_ast.ASTNode) -> None:
        self.seen.append(type(node).__name__)


def test_transformer_dispatch_is_exact_name_with_no_base_class_fallback() -> None:
    """Unlike Visitor dispatch, ``transform_game`` does not fire on a Reduction."""
    game = frog_ast.Game(("G", [], [], []))
    assert _RenameGames().transform(game).name == "G'"

    reduction = _reduction()
    assert _RenameGames().transform(reduction) is reduction

    # The Reduction goes straight to the generic hook, then to its children.
    transformer = _RenameViaGenericHook()
    assert transformer.transform(reduction) is reduction
    assert transformer.seen == ["Reduction", "ParameterizedGame", "ParameterizedGame"]


def test_visitor_descends_through_optional_and_tuple_children() -> None:
    first = frog_ast.Game(("First", [], [], []))
    second = frog_ast.Game(("Second", [], [], []))
    game_file = frog_ast.GameFile([], (first, second), "Pair")
    assert _GameNames().visit(game_file) == ["First", "Second"]

    field = frog_ast.Field(frog_ast.IntType(), "f", None)
    assert _VariableNames().visit(field) == []
    field.value = frog_ast.Variable("x")
    assert _VariableNames().visit(field) == ["x"]


def test_custom_node_keeps_dynamic_children() -> None:
    class Extension(frog_ast.ASTNode):
        def __init__(self) -> None:
            super().__init__()
            self.child = frog_ast.Variable("x")

    node = Extension()
    assert _VariableNames().visit(node) == ["x"]
    transformed = visitors.ReplaceTransformer(
        node.child, frog_ast.Variable("y")
    ).transform(node)
    assert transformed is not node
    assert transformed.child.name == "y"


def test_repeated_reference_collection_keeps_one_dispatch_table() -> None:
    visitors._VISITOR_METHODS_CACHE.clear()
    node = frog_ast.Variable("x")

    for _ in range(1000):
        assert visitors.referenced_variables_in_order(node) == [node]
    gc.collect()
    first_entries = sum(
        len(table) for table in visitors._VISITOR_METHODS_CACHE.values()
    )
    assert len(visitors._VISITOR_METHODS_CACHE) == 1
    visitor_cls, table = next(iter(visitors._VISITOR_METHODS_CACHE.items()))
    assert table[frog_ast.Variable] == (visitor_cls.visit_variable, None)

    for _ in range(1000):
        visitors.referenced_variables_in_order(node)
    gc.collect()
    assert (
        sum(len(table) for table in visitors._VISITOR_METHODS_CACHE.values())
        == first_entries
    )


def test_transformer_dispatch_caches_do_not_grow_with_use() -> None:
    node = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.ADD, frog_ast.Variable("x"), frog_ast.Integer(1)
    )
    replacement = frog_ast.Variable("y")

    def run() -> None:
        for _ in range(200):
            visitors.ReplaceTransformer(node.left_expression, replacement).transform(
                node
            )

    run()
    sizes = (
        len(visitors._TRANSFORM_CACHE),
        len(visitors._TRANSFORM_FALLBACK_CACHE),
    )
    run()
    assert sizes == (
        len(visitors._TRANSFORM_CACHE),
        len(visitors._TRANSFORM_FALLBACK_CACHE),
    )


# Classes that are defined inside a function on purpose, as (file, class name).
# frog_parser's decorator runs once, at import, and its class is not one of
# the visitors.py bases.
_ALLOWED_LOCAL_CLASSES = {("frog_parser.py", "ModifiedClass")}


def test_proof_frog_defines_no_class_inside_a_function() -> None:
    """The dispatch caches never evict, so their keys must be a fixed set.

    A Visitor or Transformer subclass defined inside a function is a new class
    on every call; each one would leave entries in the caches for good.  The
    check is on every class, whatever its bases, so that it cannot be dodged
    through an intermediate base class: a class that is not a visitor and has
    a reason to be local can be added to ``_ALLOWED_LOCAL_CLASSES``.
    """
    package = _REPO_ROOT / "proof_frog"
    local_classes = set()
    for path in sorted(package.rglob("*.py")):
        if "parsing" in path.relative_to(package).parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in ast.walk(tree):
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for inner in ast.walk(function):
                    if isinstance(inner, ast.ClassDef):
                        local_classes.add((path.name, inner.name))
    assert local_classes <= _ALLOWED_LOCAL_CLASSES, sorted(
        local_classes - _ALLOWED_LOCAL_CLASSES
    )


def test_every_frog_ast_node_class_has_child_fields() -> None:
    """A built-in node missing from the map falls back to the slower walk."""
    unmapped = [
        cls.__name__ for cls in _AST_CLASSES if cls not in visitors._CHILD_FIELDS
    ]
    assert not unmapped


# ---------------------------------------------------------------------------
# Completeness of _CHILD_FIELDS
#
# Visitors and transformers descend only through the fields _CHILD_FIELDS
# lists.  A node-holding attribute missing from a class's entry is skipped by
# every one of them without any error, so each attribute a constructor sets
# must be accounted for: either it is a mapped child field, or it is named
# below as a scalar that never holds an AST node.
# ---------------------------------------------------------------------------


def _node_classes(namespace: dict[str, Any]) -> list[type]:
    """The public AST node classes a module defines.

    An underscore-prefixed class is a private helper or mixin, not a node type
    of its own: it needs no ``_CHILD_FIELDS`` entry, and whatever its
    constructor sets is charged to the public classes that inherit from it.
    Classes are taken from the module's own namespace, never from
    ``__subclasses__()``, so node classes defined by tests are not included.
    """
    base = namespace["ASTNode"]
    return [
        cls
        for name, cls in namespace.items()
        if isinstance(cls, type)
        and issubclass(cls, base)
        and cls.__module__ == base.__module__
        and not name.startswith("_")
    ]


_AST_CLASSES = _node_classes(vars(frog_ast))

# Source position and provenance: set on every node, by whichever constructor
# along the MRO takes care of it, and never an AST node.
_POSITION_ATTRIBUTES = ("line_num", "column_num", "origin")

# Per class, the constructor-set attributes that never hold an AST node.
# Adding an attribute to a frog_ast class means adding it either here or to
# visitors._CHILD_FIELDS; the tests below fail until one of the two is done.
_SCALAR_ATTRIBUTES: dict[type, tuple[str, ...]] = {
    frog_ast.BinaryOperation: ("operator",),
    frog_ast.UnaryOperation: ("operator",),
    frog_ast.Field: ("name",),
    frog_ast.Parameter: ("name",),
    frog_ast.MethodSignature: ("name", "deterministic", "injective"),
    frog_ast.Primitive: ("name",),
    frog_ast.Variable: ("name",),
    frog_ast.FieldAccess: ("name",),
    frog_ast.VariableDeclaration: ("name",),
    frog_ast.NumericFor: ("name",),
    frog_ast.GenericFor: ("var_name",),
    frog_ast.UniqueSample: ("surface_form",),
    frog_ast.DestructuringBinding: ("names", "kind"),
    frog_ast.Integer: ("num",),
    frog_ast.Boolean: ("bool",),
    frog_ast.BinaryNum: ("num", "length"),
    frog_ast.BitStringLiteral: ("bit",),
    frog_ast.Import: ("filename", "rename"),
    frog_ast.Scheme: ("name", "primitive_name"),
    frog_ast.Game: ("name",),
    frog_ast.ParameterizedGame: ("name",),
    frog_ast.EventTheorem: ("flag", "at_initialize"),
    frog_ast.ConcreteGame: ("which",),
    frog_ast.Reduction: ("name",),
    frog_ast.GameFile: ("name",),
    frog_ast.Induction: ("name",),
    frog_ast.Lemma: ("proof_path",),
    frog_ast.StructuralRequirement: ("kind",),
    frog_ast.ProofFile: ("sampled_let_names", "helpers_after_theorem_count"),
}

# Slot names that are part of the instance layout, not attributes of a node.
_LAYOUT_SLOTS = ("__dict__", "__weakref__")

# Type names a slot's annotation may use for the slot to count as a scalar.
_SCALAR_TYPE_NAMES = ("int", "str", "bool", "float", "bytes", "None")

# Methods that implement attribute writing itself; forwarding a name they were
# handed is not a new attribute.
_ATTRIBUTE_PROTOCOL_METHODS = ("__setattr__", "__delattr__")


def _is_self(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == "self"


def _is_self_attribute(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and _is_self(node.value)


def _is_super_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "super"
    )


def _is_super_init_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "__init__"
        and _is_super_call(node.func.value)
    )


def _is_object_setattr(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "__setattr__"
        and isinstance(node.value, ast.Name)
        and node.value.id == "object"
    )


def _is_scalar_annotation(node: ast.AST) -> bool:
    """``int | None``, ``Optional[str]`` and the like: no room for a node."""
    if isinstance(node, ast.Constant):
        return node.value is None
    if isinstance(node, ast.Name):
        return node.id in _SCALAR_TYPE_NAMES
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _is_scalar_annotation(node.left) and _is_scalar_annotation(node.right)
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        return node.value.id == "Optional" and _is_scalar_annotation(node.slice)
    return False


class _NodeSource:
    """What the node classes of a module's source set on their instances.

    Reads the source instead of running it, so that it sees every attribute a
    constructor may set (not only those one particular call happens to set)
    and the order it sets them in.  Anything it cannot account for (a write
    under a computed name, an attribute first set outside a constructor, a
    slot not declared scalar) is an assertion failure, never a silent gap.
    """

    def __init__(self, source: str, namespace: dict[str, Any]) -> None:
        module = ast.parse(source)
        self.namespace = namespace
        self.classes = {
            node.name: node for node in ast.walk(module) if isinstance(node, ast.ClassDef)
        }
        # Module-level names for the attribute-writing primitive, e.g.
        # ``_SET = object.__setattr__``: calling one is an attribute write.
        self.setattr_names = {"setattr"} | {
            target.id
            for statement in module.body
            if isinstance(statement, ast.Assign) and _is_object_setattr(statement.value)
            for target in statement.targets
            if isinstance(target, ast.Name)
        }

    def node_classes(self) -> list[type]:
        return _node_classes(self.namespace)

    def _mro(self, cls: type) -> list[type]:
        mro = [klass for klass in cls.__mro__ if klass.__name__ in self.classes]
        assert all(
            "__init__" not in vars(klass)
            for klass in cls.__mro__
            if klass not in mro and klass is not object
        ), f"{cls.__name__} inherits a constructor defined outside its module"
        return mro

    def _written_name(self, call: ast.Call) -> Optional[ast.expr]:
        """The name argument, if *call* writes an attribute of ``self``.

        Covers ``setattr(self, n, v)``, ``object.__setattr__(self, n, v)`` and
        module-level aliases of it, ``super().__setattr__(n, v)`` and
        ``self.__setattr__(n, v)``.
        """
        func, args = call.func, call.args
        explicit_self = (
            isinstance(func, ast.Name) and func.id in self.setattr_names
        ) or _is_object_setattr(func)
        if explicit_self:
            return args[1] if len(args) >= 2 and _is_self(args[0]) else None
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "__setattr__"
            and (_is_super_call(func.value) or _is_self(func.value))
        ):
            return args[0] if args else None
        return None

    def _literal_write(self, node: ast.AST, where: str) -> Optional[str]:
        """The attribute a setattr-style call writes; a computed name fails."""
        if not isinstance(node, ast.Call):
            return None
        name = self._written_name(node)
        if name is None:
            return None
        assert isinstance(name, ast.Constant) and isinstance(
            name.value, str
        ), f"{where} writes an attribute of self under a non-literal name"
        return name.value

    def constructor_attributes(self, cls: type) -> tuple[str, ...]:
        """Attributes ``cls()`` sets on ``self``, in the order it first sets them.

        Follows the ``__init__`` chain along the MRO through each
        ``super().__init__(...)`` call, at the point where it occurs.
        """
        mro = self._mro(cls)
        attributes: list[str] = []

        def record(name: str) -> None:
            if name not in attributes:
                attributes.append(name)

        def walk(node: ast.AST, start: int) -> None:
            where = f"{mro[start].__name__}.__init__"
            if _is_super_init_call(node):
                run_constructor(start + 1)
                return
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "vars", f"{where} uses vars()"
            written = self._literal_write(node, where)
            if written is not None:
                record(written)
            if isinstance(node, ast.Attribute) and _is_self_attribute(node):
                assert node.attr != "__dict__", f"{where} uses __dict__"
                if isinstance(node.ctx, ast.Store):
                    record(node.attr)
            for child in ast.iter_child_nodes(node):
                walk(child, start)

        def run_constructor(start: int) -> None:
            for index in range(start, len(mro)):
                init = self._method(mro[index], "__init__")
                if init is not None:
                    for statement in init.body:
                        walk(statement, index)
                    return

        run_constructor(0)
        for klass in mro:
            self._check_other_methods(klass, attributes)
        return tuple(attributes)

    def _method(self, klass: type, name: str) -> Optional[ast.FunctionDef]:
        for item in self.classes[klass.__name__].body:
            if isinstance(item, ast.FunctionDef) and item.name == name:
                return item
        return None

    def _check_other_methods(self, klass: type, attributes: list[str]) -> None:
        """No method may introduce an attribute the constructor did not set."""
        for method in self.classes[klass.__name__].body:
            if not isinstance(method, ast.FunctionDef):
                continue
            where = f"{klass.__name__}.{method.name}"
            for node in ast.walk(method):
                written = None
                if isinstance(node, ast.Attribute) and _is_self_attribute(node):
                    if isinstance(node.ctx, ast.Store):
                        written = node.attr
                elif method.name not in _ATTRIBUTE_PROTOCOL_METHODS:
                    written = self._literal_write(node, where)
                assert (
                    written is None or written in attributes
                ), f"{where} sets self.{written} outside the constructor"
                # self.__dict__[...] = ... and self.__dict__.update(...)
                target = None
                if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
                    target = node.value
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("update", "setdefault", "__setitem__"):
                        target = node.func.value
                assert not (
                    isinstance(target, ast.Attribute)
                    and _is_self_attribute(target)
                    and target.attr == "__dict__"
                ), f"{where} writes into self.__dict__"

    def slots(self, cls: type) -> tuple[str, ...]:
        """Slot attributes of *cls* instances; each must be declared scalar.

        A slot is storage that ``vars(node)`` does not show and that no
        ``_CHILD_FIELDS`` entry reaches, so it must never hold an AST node.
        The class that declares the slot says so with a class-level annotation
        made only of scalar types (``_cache: int | None``); a slot without
        one, or annotated with anything else, fails.
        """
        found: list[str] = []
        for klass in self._mro(cls):
            body = self.classes[klass.__name__].body
            annotations = {
                item.target.id: item.annotation
                for item in body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
            for item in body:
                if not (
                    isinstance(item, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == "__slots__"
                        for target in item.targets
                    )
                ):
                    continue
                try:
                    names = ast.literal_eval(item.value)
                except ValueError:
                    names = None
                if isinstance(names, str):
                    names = (names,)
                assert isinstance(names, (tuple, list)) and all(
                    isinstance(name, str) for name in names
                ), f"{klass.__name__}.__slots__ is not a literal tuple of names"
                for slot in names:
                    if slot in _LAYOUT_SLOTS:
                        continue
                    assert slot in annotations and _is_scalar_annotation(
                        annotations[slot]
                    ), (
                        f"{klass.__name__} slot {slot!r} is not annotated with a "
                        "scalar-only type; a slot must never hold an AST node"
                    )
                    found.append(slot)
        return tuple(found)


def _frog_ast_source() -> _NodeSource:
    return _NodeSource(inspect.getsource(frog_ast), vars(frog_ast))


def _child_fields_problems(child_fields: dict[type, tuple[str, ...]]) -> list[str]:
    """Every way *child_fields* disagrees with the frog_ast constructors."""
    source = _frog_ast_source()
    problems = []
    for cls in _AST_CLASSES:
        if cls not in child_fields:
            problems.append(f"{cls.__name__}: no _CHILD_FIELDS entry")
            continue
        attributes = source.constructor_attributes(cls)
        slots = source.slots(cls)
        unset = [name for name in _POSITION_ATTRIBUTES if name not in attributes]
        if unset:
            problems.append(f"{cls.__name__}: no constructor sets {unset}")
        scalars = _SCALAR_ATTRIBUTES.get(cls, ())
        stale = [name for name in scalars if name not in attributes]
        if stale:
            problems.append(f"{cls.__name__}: scalar allowlist names unset {stale}")
        both = [name for name in (*scalars, *slots) if name in child_fields[cls]]
        if both:
            problems.append(f"{cls.__name__}: {both} listed as scalar and as child")
        # Constructor order is the order the vars() walk used; traversal order
        # feeds canonicalization, so the entry has to reproduce it exactly.
        expected = tuple(
            name
            for name in attributes
            if name not in _POSITION_ATTRIBUTES and name not in scalars
        )
        if child_fields[cls] != expected:
            problems.append(
                f"{cls.__name__}: _CHILD_FIELDS has {child_fields[cls]}, the "
                f"constructor sets {expected} besides its declared scalars"
            )
    return problems


def test_child_fields_match_constructor_attributes() -> None:
    """Each entry is exactly the constructor's non-scalar attributes, in order.

    A field missing from an entry is skipped by every visitor and transformer;
    a field out of order changes traversal order.  Both must fail here.
    """
    assert set(_SCALAR_ATTRIBUTES) <= set(_AST_CLASSES)
    assert not _child_fields_problems(visitors._CHILD_FIELDS)


def test_completeness_check_detects_a_dropped_or_reordered_field() -> None:
    """The check above is not vacuous: break the map and it must object."""
    fields = dict(visitors._CHILD_FIELDS)
    fields[frog_ast.IfStatement] = ("conditions",)
    assert any("IfStatement" in p for p in _child_fields_problems(fields))

    fields = dict(visitors._CHILD_FIELDS)
    fields[frog_ast.Assignment] = ("the_type", "value", "var")
    assert any("Assignment" in p for p in _child_fields_problems(fields))

    fields = dict(visitors._CHILD_FIELDS)
    del fields[frog_ast.Slice]
    assert any("Slice" in p for p in _child_fields_problems(fields))


def _holds_node(value: Any) -> bool:
    if isinstance(value, frog_ast.ASTNode):
        return True
    if isinstance(value, dict):
        return any(_holds_node(k) or _holds_node(v) for k, v in value.items())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_holds_node(item) for item in value)
    return False


def _every_node(value: Any) -> Iterator[frog_ast.ASTNode]:
    """All nodes reachable from *value* through ANY attribute (not the map)."""
    if isinstance(value, frog_ast.ASTNode):
        yield value
        for child in vars(value).values():
            yield from _every_node(child)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _every_node(key)
            yield from _every_node(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _every_node(item)


def _corpus_problems(
    roots: list[tuple[str, frog_ast.ASTNode]], child_fields: dict[type, Any]
) -> tuple[list[str], set[type]]:
    source = _frog_ast_source()
    expected_attributes: dict[type, tuple[str, ...]] = {}
    slots: dict[type, tuple[str, ...]] = {}
    problems: dict[str, str] = {}  # problem -> first file showing it
    seen: set[type] = set()
    for label, root in roots:
        for node in _every_node(root):
            cls = type(node)
            seen.add(cls)
            if cls not in expected_attributes:
                expected_attributes[cls] = source.constructor_attributes(cls)
                slots[cls] = source.slots(cls)
            if tuple(vars(node)) != expected_attributes[cls]:
                problems.setdefault(
                    f"{cls.__name__} carries attributes {tuple(vars(node))}, its "
                    f"constructor sets {expected_attributes[cls]}",
                    label,
                )
            for name, value in vars(node).items():
                if name not in child_fields.get(cls, ()) and _holds_node(value):
                    problems.setdefault(
                        f"{cls.__name__}.{name} holds an AST node but is not in "
                        "_CHILD_FIELDS",
                        label,
                    )
            for name in slots[cls]:
                if _holds_node(getattr(node, name, None)):
                    problems.setdefault(
                        f"{cls.__name__} slot {name!r} holds an AST node", label
                    )
    return sorted(f"{text} (e.g. {where})" for text, where in problems.items()), seen


_CORPUS_SUFFIXES = (".primitive", ".scheme", ".game", ".proof")


def _corpus_roots() -> list[tuple[str, frog_ast.ASTNode]]:
    files = sorted(
        path
        for path in (_REPO_ROOT / "examples").rglob("*")
        if path.suffix in _CORPUS_SUFFIXES
    )
    # An even spread over the sorted tree: every directory and file type is
    # sampled, at a quarter of the cost of parsing everything.
    return [
        (str(path.relative_to(_REPO_ROOT)), frog_parser.parse_file(str(path)))
        for path in files[::4]
    ]


def test_parsed_corpus_holds_nodes_only_in_mapped_fields() -> None:
    """On real parsed files, no unmapped attribute holds an AST node.

    Complements the constructor reading above from the runtime side: it sees
    what the parser actually stores, including anything attached to a node
    after construction.
    """
    roots = _corpus_roots()
    if not roots:
        pytest.skip("examples submodule not checked out")
    assert len(roots) >= 40

    problems, seen = _corpus_problems(roots, visitors._CHILD_FIELDS)
    assert not problems
    # The corpus has to exercise the node classes for the claim to mean much.
    assert len(seen) >= 45, sorted(cls.__name__ for cls in seen)

    fields = dict(visitors._CHILD_FIELDS)
    fields[frog_ast.FuncCall] = ("func",)
    broken, _ = _corpus_problems(roots[:5], fields)
    assert any("FuncCall.args" in problem for problem in broken)


# A stand-in module for exercising the reader on constructs frog_ast may or
# may not use at any given time: a private mixin whose constructor writes the
# position attributes through an alias of object.__setattr__, a cache slot,
# and an attribute-invalidating __setattr__.
# It defers annotation evaluation, as Python 3.14 does by default, so a test
# can swap in an annotation naming a class that is not defined yet.
_SYNTHETIC_MODULE = """
from __future__ import annotations

_SET = object.__setattr__


class ASTNode:
    __slots__ = ("_cache", "__dict__")

    _cache: int | None

    def __init__(self):
        self.line_num = -1
        self.column_num = -1
        self.origin = None


class _Leaf(ASTNode):
    __slots__ = ()

    def __init__(self):
        _SET(self, "line_num", -1)
        object.__setattr__(self, "column_num", -1)
        super().__setattr__("origin", None)

    def __setattr__(self, name, value):
        _SET(self, name, value)


class Name(_Leaf):
    def __init__(self, name):
        super().__init__()
        self.name = name


class Pair(ASTNode):
    def __init__(self, left, right):
        super().__init__()
        self.left = left
        setattr(self, "right", right)
"""


def _synthetic(source: str) -> _NodeSource:
    namespace: dict[str, Any] = {"__name__": "synthetic_nodes"}
    exec(source, namespace)  # pylint: disable=exec-used
    return _NodeSource(source, namespace)


def test_reader_follows_mixins_aliases_and_slots() -> None:
    source = _synthetic(_SYNTHETIC_MODULE)
    classes = {cls.__name__: cls for cls in source.node_classes()}
    # The private mixin is not a node class of its own ...
    assert sorted(classes) == ["ASTNode", "Name", "Pair"]
    # ... but what its constructor writes belongs to the classes built on it.
    assert source.constructor_attributes(classes["Name"]) == (
        *_POSITION_ATTRIBUTES,
        "name",
    )
    assert source.constructor_attributes(classes["Pair"]) == (
        *_POSITION_ATTRIBUTES,
        "left",
        "right",
    )
    assert source.slots(classes["Name"]) == ("_cache",)


@pytest.mark.parametrize(
    "old, new, message",
    [
        # A write under a computed name could be any attribute.
        (
            'setattr(self, "right", right)',
            'setattr(self, "ri" + "ght", right)',
            "non-literal name",
        ),
        (
            '_SET(self, "line_num", -1)',
            "_SET(self, LINE, -1)",
            "non-literal name",
        ),
        ("self.left = left", "vars(self)['left'] = left", "uses vars"),
        ("self.left = left", "self.__dict__['left'] = left", "uses __dict__"),
        # An attribute the constructor never sets, introduced later.
        (
            "        self.left = left",
            "        self.left = left\n\n    def late(self, node):\n"
            "        self.extra = node",
            "sets self.extra outside the constructor",
        ),
        (
            "        self.left = left",
            "        self.left = left\n\n    def late(self, node):\n"
            '        object.__setattr__(self, "extra", node)',
            "sets self.extra outside the constructor",
        ),
        (
            "        self.left = left",
            "        self.left = left\n\n    def late(self, node):\n"
            "        self.__dict__.update(extra=node)",
            "writes into self.__dict__",
        ),
    ],
)
def test_reader_rejects_writes_it_cannot_account_for(
    old: str, new: str, message: str
) -> None:
    assert old in _SYNTHETIC_MODULE
    source = _synthetic(_SYNTHETIC_MODULE.replace(old, new))
    classes = {cls.__name__: cls for cls in source.node_classes()}
    with pytest.raises(AssertionError, match=message):
        for cls in classes.values():
            source.constructor_attributes(cls)


@pytest.mark.parametrize(
    "old, new",
    [
        ("    _cache: int | None\n", ""),  # undeclared
        ("_cache: int | None", "_cache: ASTNode | None"),  # may hold a node
        ("_cache: int | None", "_cache: object"),
        ('__slots__ = ("_cache", "__dict__")', '__slots__ = ("_cache", "_other", "__dict__")'),
    ],
)
def test_reader_rejects_a_slot_not_declared_scalar(old: str, new: str) -> None:
    assert old in _SYNTHETIC_MODULE
    source = _synthetic(_SYNTHETIC_MODULE.replace(old, new))
    classes = {cls.__name__: cls for cls in source.node_classes()}
    with pytest.raises(AssertionError, match="scalar-only type"):
        source.slots(classes["Pair"])
