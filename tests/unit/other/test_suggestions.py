"""Tests for the shared suggestions module."""

from pathlib import Path

from proof_frog.suggestions import (
    levenshtein_distance,
    suggest_identifier,
    suggest_path,
    suggest_type,
)


class TestLevenshteinDistance:
    def test_identical_strings(self) -> None:
        assert levenshtein_distance("foo", "foo") == 0

    def test_empty_strings(self) -> None:
        assert levenshtein_distance("", "") == 0

    def test_one_empty(self) -> None:
        assert levenshtein_distance("abc", "") == 3
        assert levenshtein_distance("", "abc") == 3

    def test_single_insertion(self) -> None:
        assert levenshtein_distance("abc", "abcd") == 1

    def test_single_deletion(self) -> None:
        assert levenshtein_distance("abcd", "abc") == 1

    def test_single_substitution(self) -> None:
        assert levenshtein_distance("abc", "axc") == 1

    def test_known_pair(self) -> None:
        assert levenshtein_distance("kitten", "sitting") == 3

    def test_case_sensitive(self) -> None:
        assert levenshtein_distance("Game", "game") == 1

    def test_symmetry(self) -> None:
        assert levenshtein_distance("abc", "xyz") == levenshtein_distance("xyz", "abc")


class TestSuggestIdentifier:
    def test_close_match(self) -> None:
        assert suggest_identifier("mLt", ["mL", "mR", "k"]) == "mL"

    def test_exact_match_excluded(self) -> None:
        assert suggest_identifier("mL", ["mL", "mR"]) is None

    def test_no_close_match(self) -> None:
        assert suggest_identifier("xyz", ["alpha", "beta", "gamma"]) is None

    def test_empty_candidates(self) -> None:
        assert suggest_identifier("foo", []) is None

    def test_short_token_rejected(self) -> None:
        assert suggest_identifier("m", ["mL", "mR"]) is None

    def test_best_match_wins(self) -> None:
        assert suggest_identifier("Encr", ["Enc", "Dec", "KeyGen"]) == "Enc"

    def test_length_filter(self) -> None:
        assert suggest_identifier("ab", ["RandomFunctions"]) is None

    def test_single_char_difference(self) -> None:
        assert suggest_identifier("Kee", ["Key", "Enc"]) == "Key"


class TestSuggestType:
    def test_lowercase_int(self) -> None:
        assert suggest_type("int") == "Int"

    def test_lowercase_bool(self) -> None:
        assert suggest_type("bool") == "Bool"

    def test_lowercase_bitstring(self) -> None:
        assert suggest_type("bitstring") == "BitString"

    def test_lowercase_string_alias(self) -> None:
        assert suggest_type("string") == "BitString"

    def test_typo_bitstring(self) -> None:
        assert suggest_type("Bitstring") == "BitString"

    def test_typo_boolean(self) -> None:
        assert suggest_type("Booln") == "Bool"

    def test_no_match(self) -> None:
        assert suggest_type("Foobar") is None

    def test_already_correct(self) -> None:
        assert suggest_type("Int") is None

    def test_short_token(self) -> None:
        assert suggest_type("In") is None


class TestSuggestPath:
    def test_typo_in_filename(self, tmp_path: Path) -> None:
        (tmp_path / "SymEnc.primitive").write_text("")
        (tmp_path / "Hash.primitive").write_text("")
        result = suggest_path(str(tmp_path / "SymEn.primitive"))
        assert result is not None
        assert "SymEnc.primitive" in result

    def test_typo_in_directory(self, tmp_path: Path) -> None:
        subdir = tmp_path / "Primitives"
        subdir.mkdir()
        (subdir / "SymEnc.primitive").write_text("")
        result = suggest_path(str(tmp_path / "Primitves" / "SymEnc.primitive"))
        assert result is not None
        assert "Primitives" in result

    def test_no_match(self, tmp_path: Path) -> None:
        result = suggest_path(str(tmp_path / "nonexistent" / "file.txt"))
        assert result is None

    def test_exact_match_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("")
        result = suggest_path(str(tmp_path / "file.txt"))
        assert result is None
