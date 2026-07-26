"""Unit tests for the shared inlining write-detector `_stmt_mutates_var`.

It is the single source of truth for "does this statement mutate variable X"
across the inlining passes' interference / stability scans. It must see both
blind spots the private scanners historically missed:

  - element/slice/field writes (`M[k]=v`, `X.f=v`) -- audit A.1;
  - `<-uniq[S]` implicit insertion growing the exclusion set S -- audit A.2
    (F-154/167/175/180/186/208), while the `\\`-set-minus form does NOT grow
    its set.
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import _stmt_mutates_var


def _stmt(src: str):
    # Parse a one-statement method and return its single statement.
    method = frog_parser.parse_method("Void f() { " + src + " }")
    return method.block.statements[0]


def test_direct_assignment_detected() -> None:
    assert _stmt_mutates_var(_stmt("M = N;"), "M")


def test_element_write_detected() -> None:
    assert _stmt_mutates_var(_stmt("M[0] = 1;"), "M")


def test_field_write_detected() -> None:
    assert _stmt_mutates_var(_stmt("X.f = 1;"), "X")


def test_uniq_draw_grows_exclusion_set() -> None:
    # `x <-uniq[S] BitString<n>` implicitly inserts into S -> writes S.
    stmt = _stmt("BitString<n> x <-uniq[S] BitString<n>;")
    assert _stmt_mutates_var(stmt, "S")
    # It does NOT write an unrelated name.
    assert not _stmt_mutates_var(stmt, "T")


def test_set_minus_form_does_not_grow_its_set() -> None:
    # `x <- BitString<n> \ E` samples from the complement but does NOT insert
    # into E, so E is not mutated.
    stmt = _stmt("BitString<n> x <- BitString<n> \\ E;")
    assert not _stmt_mutates_var(stmt, "E")


def test_plain_read_not_a_write() -> None:
    assert not _stmt_mutates_var(_stmt("Int y = M[0];"), "M")


def test_numeric_for_binder_detected() -> None:
    # F-183/F-188: a `for (Int i = ...)` binder rebinds `i`, shadowing it in
    # the loop body -- an interference scan must treat it as a write.
    assert _stmt_mutates_var(_stmt("for (Int i = 0 to 3) { }"), "i")
    assert not _stmt_mutates_var(_stmt("for (Int i = 0 to 3) { }"), "j")


def test_generic_for_binder_detected() -> None:
    # F-183/F-188: a `for (T e in S)` binder rebinds `e`.
    assert _stmt_mutates_var(_stmt("for (Int e in S) { }"), "e")
    assert not _stmt_mutates_var(_stmt("for (Int e in S) { }"), "S_unrelated")
