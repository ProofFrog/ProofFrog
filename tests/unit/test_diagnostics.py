from proof_frog.diagnostics import (
    classify_diff,
    match_near_misses,
    diagnose_failure,
    detect_commutativity_diff,
    detect_associativity_diff,
    detect_field_order_diff,
    detect_extra_temporary_diff,
    detect_if_condition_reorder_diff,
    DiffHunk,
)
from proof_frog.transforms._base import NearMiss


def test_classify_method_diff():
    diff_text = (
        "Methods that differ: Encrypt\n"
        "--- Encrypt (current)\n"
        "+++ Encrypt (next)\n"
        "  @@ -1,3 +1,3 @@\n"
        "   BitString<lambda> Encrypt(BitString<lambda> m) {\n"
        "  -    return r + m;\n"
        "  +    return r;\n"
        "   }"
    )
    hunks = classify_diff(diff_text)
    assert len(hunks) == 1
    assert hunks[0].method == "Encrypt"
    assert any("return r + m;" in line for line in hunks[0].current_lines)
    assert any("return r;" in line for line in hunks[0].next_lines)


def test_classify_multiple_methods():
    diff_text = (
        "Methods that differ: Encrypt, Decrypt\n"
        "--- Encrypt (current)\n"
        "+++ Encrypt (next)\n"
        "  @@ -1,3 +1,3 @@\n"
        "  -    return r + m;\n"
        "  +    return r;\n"
        "\n"
        "--- Decrypt (current)\n"
        "+++ Decrypt (next)\n"
        "  @@ -1,3 +1,3 @@\n"
        "  -    return ct + k;\n"
        "  +    return ct;"
    )
    hunks = classify_diff(diff_text)
    assert len(hunks) == 2
    assert hunks[0].method == "Encrypt"
    assert hunks[1].method == "Decrypt"


def test_classify_empty_diff():
    diff_text = "Canonical forms differ but no specific method differences found"
    hunks = classify_diff(diff_text)
    assert hunks == []


def test_match_near_miss_to_hunk():
    hunks = [
        DiffHunk(
            method="Encrypt",
            current_lines=["-    return r + m;"],
            next_lines=["+    return r;"],
        )
    ]
    near_misses = [
        NearMiss(
            transform_name="Uniform XOR Simplification",
            reason="XOR-with-uniform did not fire for 'r': used 2 times",
            location=None,
            suggestion="Isolate the use of 'r'",
            variable="r",
            method="Encrypt",
        )
    ]
    matched = match_near_misses(hunks, near_misses)
    assert len(matched) == 1
    assert matched[0][0] is hunks[0]
    assert matched[0][1] is near_misses[0]


def test_no_match_different_method():
    hunks = [
        DiffHunk(method="Decrypt", current_lines=["-    return r;"], next_lines=[])
    ]
    near_misses = [NearMiss("XOR", "reason", None, None, "r", "Encrypt")]
    matched = match_near_misses(hunks, near_misses)
    assert len(matched) == 0


def test_diagnose_failure_produces_summary():
    diff_text = (
        "Methods that differ: Encrypt\n"
        "--- Encrypt (current)\n"
        "+++ Encrypt (next)\n"
        "  @@ -1,3 +1,3 @@\n"
        "  -    return r + m;\n"
        "  +    return r;"
    )
    near_misses = [
        NearMiss(
            transform_name="Uniform XOR Simplification",
            reason="XOR-with-uniform did not fire for 'r': used 2 times (need exactly 1)",
            location=None,
            suggestion="Isolate the use of 'r'",
            variable="r",
            method="Encrypt",
        )
    ]
    diagnosis = diagnose_failure(diff_text, near_misses, near_misses)
    assert diagnosis.summary != ""
    assert len(diagnosis.explanations) >= 1
    assert "r" in diagnosis.explanations[0].reason


def test_detect_commutativity_or():
    """Detects operand reorder for || (not normalized by engine)."""
    hunk = DiffHunk(
        method="Query",
        current_lines=["-    return a || b;"],
        next_lines=["+    return b || a;"],
    )
    assert detect_commutativity_diff(hunk) is True


def test_detect_commutativity_add_not_detected():
    """+ is normalized by engine, so detector should NOT fire for it."""
    hunk = DiffHunk(
        method="Encrypt",
        current_lines=["-    return a + b;"],
        next_lines=["+    return b + a;"],
    )
    assert detect_commutativity_diff(hunk) is False


def test_detect_associativity_and():
    """Detects parenthesization difference for && (not normalized by engine)."""
    hunk = DiffHunk(
        method="Query",
        current_lines=["-    return (a && b) && c;"],
        next_lines=["+    return a && (b && c);"],
    )
    assert detect_associativity_diff(hunk) is True


def test_detect_associativity_add_not_detected():
    """+ is normalized by engine, so detector should NOT fire for it."""
    hunk = DiffHunk(
        method="Encrypt",
        current_lines=["-    return (a + b) + c;"],
        next_lines=["+    return a + (b + c);"],
    )
    assert detect_associativity_diff(hunk) is False


def test_detect_field_order():
    hunk = DiffHunk(
        method="Initialize",
        current_lines=["-    x = 0;", "-    y = 1;"],
        next_lines=["+    y = 1;", "+    x = 0;"],
    )
    assert detect_field_order_diff(hunk) is True


def test_detect_field_order_false_different_content():
    hunk = DiffHunk(
        method="Initialize",
        current_lines=["-    x = 0;"],
        next_lines=["+    y = 1;"],
    )
    assert detect_field_order_diff(hunk) is False


# --- Extra temporary variable detector ---


def test_detect_extra_temporary():
    """Detects assign-then-return vs direct return."""
    hunk = DiffHunk(
        method="Encrypt",
        current_lines=["-    BitString<n> ct = k + m;", "-    return ct;"],
        next_lines=["+    return k + m;"],
    )
    assert detect_extra_temporary_diff(hunk) is True


def test_detect_extra_temporary_reversed():
    """Works in either direction."""
    hunk = DiffHunk(
        method="Encrypt",
        current_lines=["-    return k + m;"],
        next_lines=["+    BitString<n> ct = k + m;", "+    return ct;"],
    )
    assert detect_extra_temporary_diff(hunk) is True


def test_detect_extra_temporary_false_both_direct():
    """Two direct returns should not match."""
    hunk = DiffHunk(
        method="Encrypt",
        current_lines=["-    return k + m;"],
        next_lines=["+    return k;"],
    )
    assert detect_extra_temporary_diff(hunk) is False


def test_detect_extra_temporary_false_both_assign():
    """Two assign-then-return patterns should not match."""
    hunk = DiffHunk(
        method="Encrypt",
        current_lines=["-    BitString<n> ct = k + m;", "-    return ct;"],
        next_lines=["+    BitString<n> ct = k;", "+    return ct;"],
    )
    assert detect_extra_temporary_diff(hunk) is False


# --- If-condition reorder detector ---


def test_detect_if_condition_reorder():
    """Detects reordered if/else-if branches."""
    hunk = DiffHunk(
        method="Query",
        current_lines=[
            "-    if (x == 0) { return a; }",
            "-    else if (x == 1) { return b; }",
        ],
        next_lines=[
            "+    if (x == 1) { return b; }",
            "+    else if (x == 0) { return a; }",
        ],
    )
    assert detect_if_condition_reorder_diff(hunk) is True


def test_detect_if_condition_reorder_false():
    """Different branch bodies should not match."""
    hunk = DiffHunk(
        method="Query",
        current_lines=[
            "-    if (x == 0) { return a; }",
            "-    else if (x == 1) { return b; }",
        ],
        next_lines=[
            "+    if (x == 0) { return c; }",
            "+    else if (x == 1) { return d; }",
        ],
    )
    assert detect_if_condition_reorder_diff(hunk) is False
