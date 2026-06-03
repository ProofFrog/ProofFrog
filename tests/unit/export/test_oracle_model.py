"""Unit tests for the multi-oracle data model (P1)."""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.export.easycrypt import oracle_model


def _game_file(path: str) -> frog_ast.GameFile:
    gf = frog_parser.parse_file(path)
    assert isinstance(gf, frog_ast.GameFile)
    return gf


SINGLE_ORACLE_GAME = "examples/joy_old/2_Exercises/2_14.game"
MULTI_ORACLE_INDCPA = "examples/Games/PubKeyEnc/INDCPA.game"
MULTI_ORACLE_KEM = "examples/Games/KEM/INDCCA_MultiChal.game"


def test_single_oracle_game_has_no_init() -> None:
    model = oracle_model.classify_game_file(_game_file(SINGLE_ORACLE_GAME))
    assert model.all_names == ["foo"]
    assert model.init_name is None
    assert model.post_init_names == ["foo"]
    assert not model.is_multi_oracle


def test_single_oracle_scalar_matches_legacy_first_method() -> None:
    # The scalar must equal the legacy first_method.name.lower() so the
    # single-oracle exporter stays byte-identical.
    gf = _game_file(SINGLE_ORACLE_GAME)
    model = oracle_model.classify_game_file(gf)
    legacy = gf.games[0].methods[0].signature.name.lower()
    assert model.scalar_oracle_name == legacy == "foo"


def test_multi_oracle_indcpa_init_and_post_init() -> None:
    model = oracle_model.classify_game_file(_game_file(MULTI_ORACLE_INDCPA))
    assert model.all_names == ["initialize", "challenge"]
    assert model.init_name == "initialize"
    assert model.post_init_names == ["challenge"]
    assert model.is_multi_oracle


def test_multi_oracle_kem_init_and_post_init() -> None:
    model = oracle_model.classify_game_file(_game_file(MULTI_ORACLE_KEM))
    assert model.all_names == ["initialize", "decaps"]
    assert model.init_name == "initialize"
    assert model.post_init_names == ["decaps"]
    assert model.is_multi_oracle


def test_multi_oracle_scalar_is_first_method() -> None:
    # The legacy scalar for a multi-oracle game is still the first method
    # (Initialize); the existing single-oracle path is unchanged by this model.
    model = oracle_model.classify_game_file(_game_file(MULTI_ORACLE_KEM))
    assert model.scalar_oracle_name == "initialize"


def test_init_detection_is_position_independent() -> None:
    # An Initialize method that is not first is still classified as init, and
    # post-init order preserves declaration order of the non-init methods.
    sig_a = frog_ast.MethodSignature("Eval", frog_ast.BitStringType(), [])
    sig_init = frog_ast.MethodSignature("Initialize", frog_ast.BitStringType(), [])
    sig_b = frog_ast.MethodSignature("Chk", frog_ast.BitStringType(), [])
    methods = [
        frog_ast.Method(sig_a, frog_ast.Block([])),
        frog_ast.Method(sig_init, frog_ast.Block([])),
        frog_ast.Method(sig_b, frog_ast.Block([])),
    ]
    game = frog_ast.Game(("G", [], [], methods))
    model = oracle_model.classify_game(game)
    assert model.all_names == ["eval", "initialize", "chk"]
    assert model.init_name == "initialize"
    assert model.post_init_names == ["eval", "chk"]
    assert model.scalar_oracle_name == "eval"


def test_init_detection_is_case_insensitive() -> None:
    sig = frog_ast.MethodSignature("INITIALIZE", frog_ast.BitStringType(), [])
    game = frog_ast.Game(("G", [], [], [frog_ast.Method(sig, frog_ast.Block([]))]))
    model = oracle_model.classify_game(game)
    assert model.init_name == "initialize"
    assert model.is_multi_oracle
    assert model.post_init_names == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
