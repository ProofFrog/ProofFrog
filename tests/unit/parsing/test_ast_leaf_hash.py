"""Structural hashes of scalar AST leaves follow semantic equality."""

import pickle

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
