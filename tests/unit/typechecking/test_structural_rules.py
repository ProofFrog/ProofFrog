"""Syntactic well-formedness rules (``proof_frog/structural_rules.py``).

A length, modulus or size in a type, and the length of ``0^n`` / ``1^n``, may
name only parameters, proof ``let:`` entries and variables never written
after their declaration, so that a type means the same thing throughout an
execution."""

import pytest

from proof_frog import frog_parser, structural_rules


def _messages(source: str) -> list[str]:
    game = frog_parser.parse_game(source)
    return [v.message for v in structural_rules.check_structural_rules(game)]


def _rejected(source: str, fragment: str) -> None:
    messages = _messages(source)
    assert any(fragment in m for m in messages), messages


class TestWrittenSizes:
    def test_field_written_in_another_method(self) -> None:
        _rejected(
            """
            Game G(Int n) {
                Int m = n;
                Void Grow() { m = m + 1; }
                BitString<m> Samp() {
                    BitString<m> r <- BitString<m>;
                    return r;
                }
            }""",
            "names field 'm', which is assigned or sampled",
        )

    def test_local_written_after_declaration(self) -> None:
        _rejected(
            """
            Game G(Int n) {
                Bool Test() {
                    Int k = n;
                    k = k + 1;
                    return 0^k == 0^k;
                }
            }""",
            "The size in 0^k names local 'k'",
        )

    def test_bare_declaration_assigned_later(self) -> None:
        _rejected(
            """
            Game G(Int n) {
                Bool Test() {
                    Int k;
                    k = n;
                    BitString<k> x = 0^k;
                    return x == x;
                }
            }""",
            "names local 'k'",
        )

    def test_written_method_parameter(self) -> None:
        _rejected(
            """
            Game G(Int n) {
                Bool Test(Int k) {
                    k = k + 1;
                    ModInt<k> x = 0;
                    return x == x;
                }
            }""",
            "The size in ModInt<k> names parameter 'k'",
        )

    def test_field_assigned_in_initialize_in_array_size(self) -> None:
        _rejected(
            """
            Game G(Int n) {
                Int c;
                Void Initialize() { c = n; }
                Bool Test() {
                    Array<Bool, c> a;
                    return true;
                }
            }""",
            "The size in Array<Bool, c> names field 'c'",
        )

    def test_field_write_seen_past_a_shadowing_local(self) -> None:
        # The write m = 5 is to the field; the inner local m is another
        # variable, so the field is still written.
        _rejected(
            """
            Game G(Int n) {
                Int m = n;
                Bool F() {
                    m = 5;
                    if (true) { Int m = 3; }
                    return true;
                }
                Bool H() {
                    BitString<m> x = 0^m;
                    return x == x;
                }
            }""",
            "names field 'm'",
        )

    @pytest.mark.parametrize(
        "source",
        [
            # A parameter, a field never written, a local never written.
            """
            Game G(Int n) {
                Int m = n;
                BitString<m> F(Int k) {
                    Int j = k + m;
                    BitString<j> pad = 0^j;
                    Array<BitString<n>, k> a;
                    BitString<m> r <- BitString<m>;
                    return r;
                }
            }""",
            # A written local of the same name in another block is another
            # variable: the field it shadows is never written.
            """
            Game G(Int n) {
                Int m = n;
                Bool F() {
                    if (true) {
                        Int m = 3;
                        m = m + 1;
                    }
                    BitString<m> x = 0^m;
                    return x == x;
                }
            }""",
            # A loop binder is not assigned.
            """
            Game G(Int n) {
                Bool F() {
                    for (Int i = 0 to n) {
                        BitString<i> x = 0^i;
                    }
                    return true;
                }
            }""",
        ],
    )
    def test_never_written_names_are_allowed(self, source: str) -> None:
        assert not _messages(source)
