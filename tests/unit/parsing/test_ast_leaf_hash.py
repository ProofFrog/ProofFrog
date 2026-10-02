"""Structural hashes of scalar AST leaves follow semantic equality."""

import copy
import pickle

import pytest

from proof_frog import frog_ast


def test_leaf_hash_tracks_semantic_mutation_but_ignores_source_position() -> None:
    left = frog_ast.Variable("x")
    right = frog_ast.Variable("x")
    original_hash = left.structural_hash()
    left.line_num = 42
    assert left.structural_hash() == original_hash
    assert left == right

    left.name = "y"
    assert left.structural_hash() != original_hash
    assert left != right


def test_leaf_hash_preserves_malformed_node_key_check() -> None:
    complete = frog_ast.Integer(1)
    incomplete = frog_ast.Integer(1)
    incomplete.structural_hash()
    del incomplete.num
    assert complete != incomplete
    assert incomplete != complete


def test_leaf_hash_is_not_serialized_to_workers() -> None:
    variable = frog_ast.Variable("x")
    variable.structural_hash()
    restored = pickle.loads(pickle.dumps(variable))
    assert "_structural_hash" not in vars(restored)
    assert restored == variable


def _leaves() -> list[frog_ast.ASTNode]:
    return [
        frog_ast.Variable("x"),
        frog_ast.Integer(7),
        frog_ast.Boolean(True),
        frog_ast.NoneExpression(),
        frog_ast.BinaryNum(5, 4),
        frog_ast.IntType(),
        frog_ast.BoolType(),
        frog_ast.Void(),
        frog_ast.GroupType(),
    ]


def _has_cached_hash(node: frog_ast.ASTNode) -> bool:
    return getattr(node, "_structural_hash", None) is not None


def test_leaf_hash_covers_exactly_the_scalar_leaf_classes() -> None:
    # pylint: disable=protected-access
    assert {type(leaf) for leaf in _leaves()} == set(frog_ast._HASHABLE_LEAF_TYPES)


def test_cached_hash_is_not_an_instance_attribute() -> None:
    """`vars(node)` is the generic attribute view every walker uses; the cache
    must never show up in it, on a hashed node or an unhashed one."""
    for leaf, twin, fresh in zip(_leaves(), _leaves(), _leaves()):
        assert leaf == twin
        assert _has_cached_hash(leaf) and _has_cached_hash(twin)
        assert "_structural_hash" not in vars(leaf)
        assert "_structural_hash" not in vars(twin)
        assert vars(leaf) == vars(fresh)


def test_copies_of_a_hashed_leaf_carry_no_cached_hash() -> None:
    for leaf in _leaves():
        leaf.structural_hash()
        for clone in (copy.copy(leaf), copy.deepcopy(leaf)):
            assert type(clone) is type(leaf)
            assert not _has_cached_hash(clone)
            assert vars(clone) == vars(leaf)
            assert clone == leaf and leaf == clone


def test_copy_of_a_hashed_leaf_can_be_mutated_independently() -> None:
    original = frog_ast.Variable("x")
    original.structural_hash()
    for clone in (copy.copy(original), copy.deepcopy(original)):
        clone.name = "y"
        assert clone != original
        assert clone == frog_ast.Variable("y")
        assert original == frog_ast.Variable("x")


def test_pickle_round_trip_drops_the_cached_hash() -> None:
    for leaf in _leaves():
        leaf.structural_hash()
        for protocol in range(2, pickle.HIGHEST_PROTOCOL + 1):
            restored = pickle.loads(pickle.dumps(leaf, protocol=protocol))
            assert type(restored) is type(leaf)
            assert not _has_cached_hash(restored)
            assert vars(restored) == vars(leaf)
            assert restored == leaf


def test_hashed_leaves_inside_a_tree_survive_deepcopy_and_pickle() -> None:
    def build() -> frog_ast.BinaryOperation:
        return frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.ADD, frog_ast.Variable("a"), frog_ast.Integer(1)
        )

    tree = build()
    assert tree == build()
    assert _has_cached_hash(tree.left_expression)
    for clone in (copy.deepcopy(tree), pickle.loads(pickle.dumps(tree))):
        assert not _has_cached_hash(clone.left_expression)
        assert not _has_cached_hash(clone.right_expression)
        assert clone == tree
        clone.right_expression.num = 2
        assert clone != tree
        assert tree == build()


def test_mutation_and_deletion_invalidate_the_cached_hash() -> None:
    integer = frog_ast.Integer(1)
    assert integer == frog_ast.Integer(1)
    integer.num = 2
    assert integer != frog_ast.Integer(1)
    assert integer == frog_ast.Integer(2)

    binary = frog_ast.BinaryNum(5, 4)
    assert binary == frog_ast.BinaryNum(5, 4)
    binary.length = 8
    assert binary != frog_ast.BinaryNum(5, 4)
    assert binary == frog_ast.BinaryNum(5, 8)

    boolean = frog_ast.Boolean(True)
    assert boolean == frog_ast.Boolean(True)
    del boolean.bool
    assert not _has_cached_hash(boolean)
    assert boolean != frog_ast.Boolean(True)
    assert frog_ast.Boolean(True) != boolean


def test_equal_hash_never_stands_in_for_the_field_comparison() -> None:
    """The hash is an early reject only: a leaf whose cached hash was forced
    equal to another's still compares by its fields."""
    left = frog_ast.Variable("x")
    right = frog_ast.Variable("y")
    object.__setattr__(right, "_structural_hash", left.structural_hash())
    assert left != right
    assert right != left


def test_composite_nodes_never_hash() -> None:
    composites: list[frog_ast.ASTNode] = [
        frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.ADD, frog_ast.Variable("a"), frog_ast.Integer(1)
        ),
        frog_ast.Tuple([frog_ast.Integer(1)]),
        frog_ast.BitStringType(frog_ast.Integer(8)),
        frog_ast.ReturnStatement(frog_ast.Variable("a")),
        frog_ast.Block([]),
    ]
    for node in composites:
        with pytest.raises(TypeError):
            node.structural_hash()
        assert node == copy.deepcopy(node)
        assert not _has_cached_hash(node)
        assert "_structural_hash" not in vars(node)
