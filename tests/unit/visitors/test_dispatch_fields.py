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

_AST_CLASSES = [
    cls
    for cls in vars(frog_ast).values()
    if isinstance(cls, type)
    and issubclass(cls, frog_ast.ASTNode)
    and cls.__module__ == frog_ast.__name__
]

# Set by ASTNode.__init__ on every node: source position and provenance.
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


def _is_self_attribute(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )


def _is_super_init_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "__init__"
        and isinstance(node.func.value, ast.Call)
        and isinstance(node.func.value.func, ast.Name)
        and node.func.value.func.id == "super"
    )


def _class_definitions() -> dict[str, ast.ClassDef]:
    module = ast.parse(inspect.getsource(frog_ast))
    return {
        node.name: node for node in ast.walk(module) if isinstance(node, ast.ClassDef)
    }


def _own_init(class_def: ast.ClassDef) -> Optional[ast.FunctionDef]:
    for item in class_def.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            return item
    return None


def _constructor_attributes(
    cls: type, definitions: dict[str, ast.ClassDef]
) -> tuple[str, ...]:
    """Attributes ``cls()`` sets on ``self``, in the order it first sets them.

    Read from the ``__init__`` source of each class along the MRO, following
    ``super().__init__(...)`` calls where they occur.  Anything the reading
    cannot account for (dynamic attribute writes, attributes first set outside
    a constructor) is an assertion failure rather than a silent gap.
    """
    mro = [klass for klass in cls.__mro__ if klass.__name__ in definitions]
    assert all(
        "__init__" not in vars(klass)
        for klass in cls.__mro__
        if klass not in mro and klass is not object
    ), f"{cls.__name__} inherits a constructor defined outside frog_ast"
    attributes: list[str] = []

    def record(name: str) -> None:
        if name not in attributes:
            attributes.append(name)

    def walk(node: ast.AST, start: int) -> None:
        if _is_super_init_call(node):
            run_constructor(start + 1)
            return
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in (
                "setattr",
                "vars",
            ), f"{cls.__name__}: dynamic attribute write in a constructor"
        if isinstance(node, ast.Attribute) and _is_self_attribute(node):
            assert node.attr != "__dict__", f"{cls.__name__}: constructor uses __dict__"
            if isinstance(node.ctx, ast.Store):
                record(node.attr)
        for child in ast.iter_child_nodes(node):
            walk(child, start)

    def run_constructor(start: int) -> None:
        for index in range(start, len(mro)):
            init = _own_init(definitions[mro[index].__name__])
            if init is not None:
                for statement in init.body:
                    walk(statement, index)
                return

    run_constructor(0)

    # An attribute first set by some other method would not be seen above.
    for klass in mro:
        for node in ast.walk(definitions[klass.__name__]):
            if (
                isinstance(node, ast.Attribute)
                and _is_self_attribute(node)
                and isinstance(node.ctx, ast.Store)
            ):
                assert (
                    node.attr in attributes
                ), f"{klass.__name__} sets self.{node.attr} outside its constructor"
    return tuple(attributes)


def _child_fields_problems(child_fields: dict[type, tuple[str, ...]]) -> list[str]:
    """Every way *child_fields* disagrees with the frog_ast constructors."""
    definitions = _class_definitions()
    problems = []
    for cls in _AST_CLASSES:
        if cls not in child_fields:
            problems.append(f"{cls.__name__}: no _CHILD_FIELDS entry")
            continue
        attributes = _constructor_attributes(cls, definitions)
        assert attributes[: len(_POSITION_ATTRIBUTES)] == _POSITION_ATTRIBUTES
        scalars = _SCALAR_ATTRIBUTES.get(cls, ())
        stale = [name for name in scalars if name not in attributes]
        if stale:
            problems.append(f"{cls.__name__}: scalar allowlist names unset {stale}")
        both = [name for name in scalars if name in child_fields[cls]]
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
    definitions = _class_definitions()
    expected_attributes: dict[type, tuple[str, ...]] = {}
    problems: dict[str, str] = {}  # problem -> first file showing it
    seen: set[type] = set()
    for label, root in roots:
        for node in _every_node(root):
            cls = type(node)
            seen.add(cls)
            if cls not in expected_attributes:
                expected_attributes[cls] = _constructor_attributes(cls, definitions)
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
