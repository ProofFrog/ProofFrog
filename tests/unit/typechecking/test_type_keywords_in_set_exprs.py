"""Bare type keywords must type-check in expression position, e.g. as
components of a tuple-set field initializer like
``Set State = [Bool, Message, Message];``.

``CheckTypeVisitor`` records a type node in the AST type map from its
``leave_*`` handler; a type node with no handler makes the enclosing
product fail with ``Could not determine type of <T>``. ``Bool``, ``Int``
and ``T?`` had no handler."""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis


def _check_primitive(tmp_path: Path, source: str) -> None:
    file_path = tmp_path / "Test.primitive"
    file_path.write_text(source)
    root = frog_parser.parse_file(str(file_path))
    semantic_analysis.check_well_formed(root, str(file_path))


def _check_primitive_fails(tmp_path: Path, source: str) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_primitive(tmp_path, source)


def test_bool_in_tuple_set_field(tmp_path: Path) -> None:
    _check_primitive(
        tmp_path,
        """
        Primitive P(Set MessageSpace) {
            Set Message = MessageSpace;
            Set State = [Bool, Message, Message];

            State Wrap(Bool choice, Message m0, Message m1);
        }
        """,
    )


def test_int_in_tuple_set_field(tmp_path: Path) -> None:
    _check_primitive(
        tmp_path,
        """
        Primitive P(Set MessageSpace) {
            Set Message = MessageSpace;
            Set Counters = [Int, Message];

            Counters Wrap(Int n, Message m);
        }
        """,
    )


def test_optional_in_tuple_set_field(tmp_path: Path) -> None:
    """``T?`` has the same missing-handler gap as ``Bool``/``Int``."""
    _check_primitive(
        tmp_path,
        """
        Primitive P(Set MessageSpace) {
            Set Message = MessageSpace;
            Set Maybe = [Message?, Bool];

            Maybe Wrap(Message? m, Bool found);
        }
        """,
    )


def test_optional_of_keyword_type_in_tuple_set_field(tmp_path: Path) -> None:
    """``Bool?`` needs both the optional and the bool handler."""
    _check_primitive(
        tmp_path,
        """
        Primitive P(Set MessageSpace) {
            Set Message = MessageSpace;
            Set Flags = [Bool?, Int?, Message];

            Flags Wrap(Bool? b, Int? n, Message m);
        }
        """,
    )


def test_tuple_component_type_is_recorded(tmp_path: Path) -> None:
    """The recorded product must be usable, not merely accepted: indexing
    ``State`` has to yield ``Bool`` at 0 and ``Message`` at 1."""
    (tmp_path / "P.primitive").write_text("""
        Primitive P(Set MessageSpace) {
            Set Message = MessageSpace;
            Set State = [Bool, Message, Message];

            State Wrap(Bool choice, Message m0, Message m1);
            Message Unwrap(State s);
        }
        """)
    scheme_path = tmp_path / "Impl.scheme"
    scheme_path.write_text("""
        import 'P.primitive';

        Scheme Impl(Set MessageSpace) extends P {
            Set Message = MessageSpace;
            Set State = [Bool, Message, Message];

            State Wrap(Bool choice, Message m0, Message m1) {
                return [choice, m0, m1];
            }

            Message Unwrap(State s) {
                if (s[0]) {
                    return s[1];
                }
                return s[2];
            }
        }
        """)
    root = frog_parser.parse_file(str(scheme_path))
    semantic_analysis.check_well_formed(root, str(scheme_path))


# Negative cases: bare `Set` and `Group` are kinds rather than types, so they
# stay rejected as tuple components -- including under a `?`, which must not
# launder a kind into a type.


def test_bare_set_in_tuple_set_field_rejected(tmp_path: Path) -> None:
    _check_primitive_fails(
        tmp_path,
        """
        Primitive P(Set MessageSpace) {
            Set Message = MessageSpace;
            Set Bad = [Set, Message];

            Bad Wrap(Message m);
        }
        """,
    )


def test_bare_group_in_tuple_set_field_rejected(tmp_path: Path) -> None:
    _check_primitive_fails(
        tmp_path,
        """
        Primitive P(Set MessageSpace) {
            Set Message = MessageSpace;
            Set Bad = [Group, Message];

            Bad Wrap(Message m);
        }
        """,
    )


def test_optional_set_in_tuple_set_field_rejected(tmp_path: Path) -> None:
    _check_primitive_fails(
        tmp_path,
        """
        Primitive P(Set MessageSpace) {
            Set Message = MessageSpace;
            Set Bad = [Set?, Message];

            Bad Wrap(Message m);
        }
        """,
    )


def test_optional_group_in_tuple_set_field_rejected(tmp_path: Path) -> None:
    """``Group?`` parses as ``OptionalType(GroupType)``, so it slips past the
    name resolution that rejects bare ``Group`` as an undefined variable."""
    _check_primitive_fails(
        tmp_path,
        """
        Primitive P(Set MessageSpace) {
            Set Message = MessageSpace;
            Set Bad = [Group?, Message];

            Bad Wrap(Message m);
        }
        """,
    )


def test_tuple_component_mismatch_still_rejected(tmp_path: Path) -> None:
    """Registering the components must not make the product permissive."""
    (tmp_path / "P.primitive").write_text("""
        Primitive P(Set MessageSpace) {
            Set Message = MessageSpace;
            Set State = [Bool, Message, Message];

            State Wrap(Bool choice, Message m0, Message m1);
        }
        """)
    scheme_path = tmp_path / "Impl.scheme"
    scheme_path.write_text("""
        import 'P.primitive';

        Scheme Impl(Set MessageSpace) extends P {
            Set Message = MessageSpace;
            Set State = [Bool, Message, Message];

            State Wrap(Bool choice, Message m0, Message m1) {
                return [m0, m0, m1];
            }
        }
        """)
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        root = frog_parser.parse_file(str(scheme_path))
        semantic_analysis.check_well_formed(root, str(scheme_path))
