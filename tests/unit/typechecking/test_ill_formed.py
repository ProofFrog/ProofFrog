"""Tests that ill-formed primitives and schemes are rejected by semantic analysis.

Some cases are marked xfail because check_well_formed only runs name resolution
(not full type checking) for non-proof files. These document gaps in the checker:
- Type mismatches in field assignments are not detected
- Bad if-conditions and incorrect return types are not detected
- Missing fields in schemes are not detected (has_matching_methods only checks
  methods, not fields)
"""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis

# ---------------------------------------------------------------------------
# Fixture primitives (valid files needed as imports by scheme tests)
# ---------------------------------------------------------------------------

_EMPTY_PRIMITIVE = """\
Primitive EmptyPrimitive() {

}
"""

_SIMPLE_PRIMITIVE = """\
Primitive SimplePrimitive(Set mySet) {
    Set field = mySet;

    Int f();
}
"""

_VOID_F_PRIMITIVE = """\
Primitive VoidFPrimitive() {
    Void f();
}
"""

# ---------------------------------------------------------------------------
# Ill-formed primitives
# ---------------------------------------------------------------------------

_NOT_CHECKED = pytest.mark.xfail(
    reason="check_well_formed does not run full type checking on non-proof files",
    strict=True,
)

_MISSING_FIELD_CHECK = pytest.mark.xfail(
    reason="has_matching_methods only checks methods, not fields",
    strict=True,
)

_PRIMITIVE_CASES = [
    pytest.param(
        "Primitive Repeated(Int x) {\n    Int y = x;\n    Int y = x;\n}\n",
        "Duplicated field name",
        id="repeated_field",
    ),
    pytest.param(
        "Primitive Repeated() {\n    Void f();\n    Int f();\n}\n",
        "Duplicated method name",
        id="repeated_method",
    ),
    pytest.param(
        "Primitive Repeated(Int x, Int x) {\n    Int y = x;\n}\n",
        "Duplicated parameter name",
        id="repeated_parameter",
    ),
    pytest.param(
        (
            "Primitive Repeated() {\n"
            "    Int x = 5;\n\n"
            "    Void f(Int x);\n"
            "    Void g(Int x, Int y, Bool x);\n"
            "}\n"
        ),
        "Duplicated parameter name",
        id="repeated_method_param",
    ),
    pytest.param(
        "Primitive UndefinedType(Int x) {\n    Bla test = x;\n}\n",
        "not defined",
        id="undefined_type",
    ),
    pytest.param(
        (
            "Primitive InvalidParameter(Bla x) {\n"
            "    Int x = 1;\n\n"
            "    Void f();\n"
            "}\n"
        ),
        "not defined",
        id="invalid_parameter",
    ),
    pytest.param(
        (
            "Primitive InvalidMethod(Set set1, Set set2, Set set3) {\n"
            "    Set myset1 = set1;\n"
            "    Set myset2 = set2;\n"
            "    Set myset3 = set3;\n\n"
            "    myset1 f(set2 x);\n\n"
            "    myset3 g(set4 x);\n"
            "}\n"
        ),
        "not defined",
        id="invalid_method_param_type",
    ),
    pytest.param(
        (
            "Primitive InvalidMethod(Set set1, Set set2, Set set3) {\n"
            "    Set myset1 = set1;\n"
            "    Set myset2 = set2;\n"
            "    Set myset3 = set3;\n\n"
            "    set1 f(set2 x);\n\n"
            "    set4 g(set2 x);\n"
            "}\n"
        ),
        "not defined",
        id="invalid_method_return_type",
    ),
    pytest.param(
        (
            "Primitive InvalidExpression() {\n"
            "    Set Test = bla;\n\n"
            "    Int f();\n"
            "}\n"
        ),
        "not defined",
        id="invalid_expression",
    ),
    pytest.param(
        "Primitive MismatchedType(Bool x) {\n    Int y = x;\n}\n",
        "not of type",
        id="mismatched_type",
        marks=_NOT_CHECKED,
    ),
]

# ---------------------------------------------------------------------------
# Ill-formed schemes
# ---------------------------------------------------------------------------

_SCHEME_CASES = [
    pytest.param(
        (
            "import 'fixtures/EmptyPrimitive.primitive';\n\n"
            "Scheme Repeated(Int x) extends EmptyPrimitive {\n"
            "    Int y = x;\n"
            "    Int y = x;\n"
            "}\n"
        ),
        "Duplicated field name",
        id="repeated_field",
    ),
    pytest.param(
        (
            "import 'fixtures/EmptyPrimitive.primitive';\n\n"
            "Scheme Repeated() extends EmptyPrimitive {\n"
            "    Void f() {}\n"
            "    Void f() {}\n"
            "}\n"
        ),
        "Duplicated method name",
        id="repeated_method",
    ),
    pytest.param(
        (
            "import 'fixtures/EmptyPrimitive.primitive';\n\n"
            "Scheme Repeated(Int x, Int x) extends EmptyPrimitive {\n"
            "    Int y = x;\n"
            "}\n"
        ),
        "Duplicated parameter name",
        id="repeated_parameter",
    ),
    pytest.param(
        (
            "import 'fixtures/EmptyPrimitive.primitive';\n\n"
            "Scheme Repeated() extends EmptyPrimitive {\n"
            "    Int x = 5;\n\n"
            "    Void f(Int x) {}\n"
            "    Void g(Int x, Int y, Bool x) {}\n"
            "}\n"
        ),
        "Duplicated parameter name",
        id="repeated_method_param",
    ),
    pytest.param(
        (
            "import 'fixtures/EmptyPrimitive.primitive';\n\n"
            "Scheme UndefinedType(Int x) extends EmptyPrimitive {\n"
            "    Bla test = x;\n"
            "}\n"
        ),
        "not defined",
        id="undefined_type",
    ),
    pytest.param(
        (
            "import 'fixtures/VoidFPrimitive.primitive';\n\n"
            "Scheme InvalidParameter(Bla x) extends VoidFPrimitive {\n"
            "    Int x = 1;\n\n"
            "    Void f() {}\n"
            "}\n"
        ),
        "not defined",
        id="invalid_parameter",
    ),
    pytest.param(
        (
            "import 'fixtures/VoidFPrimitive.primitive';\n\n"
            "Scheme InvalidExpression() extends VoidFPrimitive {\n"
            "    Set Test = bla;\n\n"
            "    Void f() {}\n"
            "}\n"
        ),
        "not defined",
        id="invalid_expression",
    ),
    pytest.param(
        (
            "import 'fixtures/EmptyPrimitive.primitive';\n\n"
            "Scheme MismatchedType(Bool x) extends EmptyPrimitive {\n"
            "    Int y = x;\n"
            "}\n"
        ),
        "not of type",
        id="mismatched_type",
        marks=_NOT_CHECKED,
    ),
    pytest.param(
        (
            "import 'fixtures/VoidFPrimitive.primitive';\n\n"
            "Scheme BadIf() extends VoidFPrimitive {\n"
            "    Void f() {\n"
            "        Int x = 1;\n"
            "        if (1) {\n"
            "            x = 2;\n"
            "        }\n"
            "    }\n"
            "}\n"
        ),
        "expected",
        id="bad_if",
        marks=_NOT_CHECKED,
    ),
    pytest.param(
        (
            "import 'fixtures/SimplePrimitive.primitive';\n\n"
            "Scheme IncorrectReturn(Set set1) extends SimplePrimitive {\n"
            "    Set field = set1;\n\n"
            "    Int f() {\n"
            "        return true;\n"
            "    }\n"
            "}\n"
        ),
        "expected",
        id="incorrect_return",
        marks=_NOT_CHECKED,
    ),
    pytest.param(
        "Scheme InvalidExtend() extends NonExistent {\n    Void f() {}\n}\n",
        "not defined",
        id="non_existent_extend",
    ),
    pytest.param(
        (
            "import 'fixtures/SimplePrimitive.primitive';\n\n"
            "Scheme NotOverridingMethods(Set mySet1) extends SimplePrimitive {\n"
            "    Set field = mySet1;\n\n"
            "    Void f() {}\n"
            "}\n"
        ),
        "does not correctly implement",
        id="incorrect_override",
    ),
    pytest.param(
        (
            "import 'fixtures/SimplePrimitive.primitive';\n\n"
            "Scheme NotOverridingFields() extends SimplePrimitive {\n"
            "    Int f() {\n"
            "        return 1;\n"
            "    }\n"
            "}\n"
        ),
        "does not correctly implement",
        id="not_overriding_fields",
        marks=_MISSING_FIELD_CHECK,
    ),
    pytest.param(
        (
            "import 'fixtures/SimplePrimitive.primitive';\n\n"
            "Scheme NotOverridingMethods(Set mySet1) extends SimplePrimitive {\n"
            "    Set field = mySet1;\n"
            "}\n"
        ),
        "does not correctly implement",
        id="not_overriding_methods",
    ),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("content,expected_error", _PRIMITIVE_CASES)
def test_primitive_rejects_ill_formed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    content: str,
    expected_error: str,
) -> None:
    file_path = str(tmp_path / "test.primitive")
    Path(file_path).write_text(content)
    root = frog_parser.parse_file(file_path)
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        semantic_analysis.check_well_formed(root, file_path)
    assert expected_error.lower() in capsys.readouterr().err.lower()


def _write_fixture_primitives(tmp_path: Path) -> None:
    """Write the fixture primitives that schemes import."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "EmptyPrimitive.primitive").write_text(_EMPTY_PRIMITIVE)
    (fixtures / "SimplePrimitive.primitive").write_text(_SIMPLE_PRIMITIVE)
    (fixtures / "VoidFPrimitive.primitive").write_text(_VOID_F_PRIMITIVE)


@pytest.mark.parametrize("content,expected_error", _SCHEME_CASES)
def test_scheme_rejects_ill_formed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    content: str,
    expected_error: str,
) -> None:
    _write_fixture_primitives(tmp_path)
    file_path = str(tmp_path / "test.scheme")
    Path(file_path).write_text(content)
    root = frog_parser.parse_file(file_path)
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        semantic_analysis.check_well_formed(root, file_path)
    assert expected_error.lower() in capsys.readouterr().err.lower()
