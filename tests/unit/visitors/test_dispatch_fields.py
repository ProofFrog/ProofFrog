"""Visitor dispatch and structural child traversal regressions."""

import gc
import weakref

from proof_frog import frog_ast, visitors


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


def test_dispatch_falls_back_to_node_base_class() -> None:
    reduction = frog_ast.Reduction(
        ("R", [], [], []),
        frog_ast.ParameterizedGame("G", []),
        frog_ast.ParameterizedGame("A", []),
    )
    assert _GameNames().visit(reduction) == ["R"]


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
    table = next(iter(visitors._VISITOR_METHODS_CACHE.values()))
    assert isinstance(table[frog_ast.Variable][0], weakref.ReferenceType)

    for _ in range(1000):
        visitors.referenced_variables_in_order(node)
    gc.collect()
    assert (
        sum(len(table) for table in visitors._VISITOR_METHODS_CACHE.values())
        == first_entries
    )


def test_dispatch_caches_bound_transient_classes(monkeypatch) -> None:
    monkeypatch.setattr(visitors, "_VISITOR_METHODS_CACHE_LIMIT", 8)
    monkeypatch.setattr(visitors, "_TRANSFORM_CACHE_LIMIT", 8)
    monkeypatch.setattr(visitors, "_TRANSFORM_FALLBACK_CACHE_LIMIT", 8)
    visitors._VISITOR_METHODS_CACHE.clear()
    visitors._TRANSFORM_CACHE.clear()
    visitors._TRANSFORM_FALLBACK_CACHE.clear()
    node = frog_ast.Variable("x")
    integer = frog_ast.Integer(1)
    first_visitor = None
    first_transformer = None

    for _ in range(24):

        class _TransientVisitor(visitors.Visitor[None]):
            def result(self) -> None:
                pass

            def visit_variable(self, var: frog_ast.Variable) -> None:
                super().should_descend(var)

        class _TransientTransformer(visitors.Transformer):
            def transform_variable(self, var: frog_ast.Variable) -> frog_ast.Variable:
                return super()._transform_children(var)

            def transform_ast_node(self, _node: frog_ast.ASTNode) -> None:
                return None

        _TransientVisitor().visit(node)
        _TransientTransformer().transform(node)
        _TransientTransformer().transform(integer)
        if first_visitor is None:
            first_visitor = weakref.ref(_TransientVisitor)
            first_transformer = weakref.ref(_TransientTransformer)

    gc.collect()
    assert len(visitors._VISITOR_METHODS_CACHE) == 8
    assert len(visitors._TRANSFORM_CACHE) == 8
    assert len(visitors._TRANSFORM_FALLBACK_CACHE) == 8
    assert first_visitor() is None
    assert first_transformer() is None
    assert any(
        isinstance(method, weakref.ReferenceType)
        for table in visitors._VISITOR_METHODS_CACHE.values()
        for methods in table.values()
        for method in methods
    )
    assert any(
        isinstance(method, weakref.ReferenceType)
        for method in visitors._TRANSFORM_CACHE.values()
    )
    assert all(
        isinstance(method, weakref.ReferenceType)
        for method in visitors._TRANSFORM_FALLBACK_CACHE.values()
    )


def test_every_frog_ast_node_class_has_child_fields() -> None:
    """A built-in node missing from the map falls back to the slower walk."""
    unmapped = [
        name
        for name, cls in vars(frog_ast).items()
        if isinstance(cls, type)
        and issubclass(cls, frog_ast.ASTNode)
        and cls.__module__ == frog_ast.__name__
        and cls not in visitors._CHILD_FIELDS  # pylint: disable=protected-access
    ]
    assert not unmapped
