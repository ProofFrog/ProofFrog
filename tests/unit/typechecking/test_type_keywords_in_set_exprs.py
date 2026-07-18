"""Bare type keywords must type-check in expression position, e.g. as
components of a tuple-set field initializer like
``Set State = [Bool, Message, Message];``.

``CheckTypeVisitor`` records a type node in the AST type map from its
``leave_*`` handler; a type node with no handler makes the enclosing
product fail with ``Could not determine type of <T>``. ``Bool``, ``Int``
and ``T?`` had no handler."""

from pathlib import Path

from proof_frog import frog_parser, semantic_analysis


def _check_primitive(tmp_path: Path, source: str) -> None:
    file_path = tmp_path / "Test.primitive"
    file_path.write_text(source)
    root = frog_parser.parse_file(str(file_path))
    semantic_analysis.check_well_formed(root, str(file_path))


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
