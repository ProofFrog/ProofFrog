"""GetTypeMapVisitor infers a local's type from a literal assignment when no
declaration recorded it (the pipeline prunes bare declarations)."""

from proof_frog import frog_ast, frog_parser, visitors


def _type_of(name: str, method_src: str) -> frog_ast.Type | None:
    method = frog_parser.parse_method(method_src)
    # The stopping point must not occur in the tree, so the whole method is walked.
    return visitors.GetTypeMapVisitor(frog_ast.Integer(0)).visit(method).get(name)


def test_boolean_literal_assignment_types_the_name() -> None:
    src = """
    BitString<n> Oracle(BitString<n> x) {
        flag = true;
        if (flag) {
            return x;
        }
        return 0^n;
    }
    """
    assert isinstance(_type_of("flag", src), frog_ast.BoolType)


def test_integer_literal_assignment_types_the_name() -> None:
    src = """
    Int Oracle() {
        n = 3;
        return n;
    }
    """
    assert isinstance(_type_of("n", src), frog_ast.IntType)


def test_declared_type_wins_over_literal_inference() -> None:
    src = """
    Int Oracle() {
        BitString<3> v = 0b101;
        v = 0b111;
        return 1;
    }
    """
    assert isinstance(_type_of("v", src), frog_ast.BitStringType)


def test_non_literal_assignment_leaves_name_untyped() -> None:
    src = """
    Int Oracle(Int k) {
        m = k + 1;
        return m;
    }
    """
    assert _type_of("m", src) is None
