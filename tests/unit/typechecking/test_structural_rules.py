"""Syntactic well-formedness rules (``proof_frog/structural_rules.py``).

A length, modulus or size in a type, and the length of ``0^n`` / ``1^n``, may
name only parameters, proof ``let:`` entries and variables never written
after their declaration, so that a type means the same thing throughout an
execution. A scheme's method may not write a field of the scheme."""

import pytest

from proof_frog import frog_ast, frog_parser, structural_rules


def _messages(source: str) -> list[str]:
    game = frog_parser.parse_game(source)
    return [v.message for v in structural_rules.check_structural_rules(game)]


def _rejected(source: str, fragment: str) -> None:
    messages = _messages(source)
    assert any(fragment in m for m in messages), messages


def _scheme_messages(source: str) -> list[str]:
    scheme = frog_parser.parse_string(source, frog_ast.FileType.SCHEME)
    return [v.message for v in structural_rules.check_structural_rules(scheme)]


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


class TestWrittenGroups:
    """F-390: the group a ``GroupElem<..>`` type names is fixed too. The
    engine reads a group element in the group its type names (Generator
    Power Field To Exponent and Offset Fusion rebuild ``A.generator`` from
    the field's type at each read), so a write to that group would change
    what an element already stored means."""

    def test_written_group_parameter(self) -> None:
        _rejected(
            """
            Game G(Group A, Group B) {
                GroupElem<A> P;
                Void Initialize() { P = A.generator; }
                Void Swap() { A = B; }
                GroupElem<A> GetP() { return P; }
            }""",
            "The group in GroupElem<A> names parameter 'A', which is assigned"
            " or sampled",
        )

    def test_written_group_local(self) -> None:
        _rejected(
            """
            Game G(Group A, Group B) {
                Bool Test() {
                    Group C = A;
                    GroupElem<C> x = C.generator;
                    C = B;
                    return x == x;
                }
            }""",
            "The group in GroupElem<C> names local 'C'",
        )

    def test_written_group_in_a_signature(self) -> None:
        _rejected(
            """
            Game G(Group A, Group B) {
                Void Swap() { A = B; }
                GroupElem<A> Gen() { return A.generator; }
            }""",
            "The group in GroupElem<A> names parameter 'A'",
        )

    def test_group_of_a_member_access_is_checked_through_its_object(self) -> None:
        # ``E.G`` reads ``E``: a write to ``E`` changes the group too.
        _rejected(
            """
            Game G(Group A, Group B) {
                Group E = A;
                Void Swap() { E = B; }
                GroupElem<E> Gen() { return E.generator; }
            }""",
            "names field 'E'",
        )

    @pytest.mark.parametrize(
        "source",
        [
            # A group parameter read, never written.
            """
            Game G(Group A) {
                GroupElem<A> P;
                Void Initialize() { P = A.generator; }
                GroupElem<A> GetP() { return P; }
            }""",
            # A written group no GroupElem type names: only its values read it.
            """
            Game G(Group A, Group B) {
                Group C = A;
                Void Swap() { C = B; }
                Bool Same() { return C.order == A.order; }
            }""",
            # A local of the same name in another block is another variable.
            """
            Game G(Group A, Group B) {
                GroupElem<A> Gen() {
                    if (true) {
                        Group A = B;
                        A = B;
                    }
                    return A.generator;
                }
            }""",
        ],
    )
    def test_never_written_groups_are_allowed(self, source: str) -> None:
        assert not _messages(source)


class TestSchemeFieldWrites:
    """F-031 (ruling of 2026-06-28): a scheme's fields are fixed once it is
    instantiated, so a scheme's method may not write one; mutable state is
    game state. The engine reads a scheme field as its initializer and
    inlines the scheme's methods into games, where a written field would be
    a bare name of the calling game (dropped as dead, or captured by a game
    field of the same name)."""

    def test_scheme_field_assigned(self) -> None:
        messages = _scheme_messages("""
            Scheme CounterImpl(Int q) extends Counter {
                Int c = q;
                Int Next() {
                    c = c + 1;
                    return c;
                }
            }""")
        assert messages == [
            "Method Next writes the scheme field 'c': a scheme field may not be"
            " written in a method body; keep mutable state in a game"
        ]

    @pytest.mark.parametrize(
        "body, field",
        [
            # A draw into the field.
            ("k <- BitString<n>;", "k"),
            # An element write.
            ("M[k] = k;", "M"),
            # A draw into an element.
            ("M[k] <- BitString<n>;", "M"),
            # '<-uniq[S]' inserts the draw into S.
            ("BitString<n> r <-uniq[S] BitString<n>;", "S"),
            # A write inside a branch and a loop.
            ("if (true) { for (Int i = 0 to n) { u = !u; } }", "u"),
        ],
    )
    def test_every_write_form_is_refused(self, body: str, field: str) -> None:
        messages = _scheme_messages(f"""
            Scheme S(Int n) extends P {{
                BitString<n> k;
                Map<BitString<n>, BitString<n>> M;
                Set<BitString<n>> S;
                Bool u;
                Void Step() {{
                    {body}
                }}
            }}""")
        assert any(
            f"Method Step writes the scheme field '{field}'" in m for m in messages
        ), messages

    @pytest.mark.parametrize(
        "source",
        [
            # A field read but never written.
            """
            Scheme ConstCounterImpl(Int q) extends Counter {
                Int c = q;
                Int Next() { return c + 1; }
            }""",
            # A local of the field's name is another variable.
            """
            Scheme S(Int q) extends Counter {
                Int c = q;
                Int Next() {
                    Int c = 0;
                    c = c + 1;
                    return c;
                }
            }""",
            # So is a method parameter of the field's name.
            """
            Scheme S(Int q) extends Counter {
                Int c = q;
                Int Next(Int c) {
                    c = c + 1;
                    return c;
                }
            }""",
        ],
    )
    def test_writes_to_other_variables_are_allowed(self, source: str) -> None:
        assert not _scheme_messages(source)

    def test_game_field_writes_are_allowed(self) -> None:
        assert not _messages("""
            Game G(Int q) {
                Int c = q;
                Int Next() {
                    c = c + 1;
                    return c;
                }
            }""")
