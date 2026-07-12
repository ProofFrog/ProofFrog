"""Parsing checks for a proof file's ``bound:`` clause (Tier-3 claimed bound)."""

from proof_frog import frog_ast, frog_parser


def _proof(bound_line: str = "") -> frog_ast.ProofFile:
    clause = f"bound:\n  {bound_line};\n" if bound_line else ""
    return frog_parser.parse_proof_file(
        "proof:\n"
        "theorem:\n"
        "  Foo(E);\n"
        f"{clause}"
        "games:\n"
        "  Foo(E).Left against Foo(E).Adversary;\n"
    )


def test_absent_bound_is_none() -> None:
    assert _proof().claimed_bound is None


def test_reduction_reference_parses() -> None:
    pf = _proof("advantage(PRFSecurity(F) compose R_PRF(E, F))")
    assert pf.claimed_bound is not None
    ref = pf.claimed_bound.bound
    assert isinstance(ref, frog_ast.AdvantageReference)
    assert str(ref.notion) == "PRFSecurity(F)"
    assert ref.reduction is not None
    assert str(ref.reduction) == "R_PRF(E, F)"


def test_bare_reduction_name_parses_and_roundtrips() -> None:
    pf = _proof("advantage(PRGSec(G) compose R_PRG_L)")
    assert pf.claimed_bound is not None
    ref = pf.claimed_bound.bound
    assert isinstance(ref, frog_ast.AdvantageReference)
    assert ref.reduction is not None
    assert ref.reduction.name == "R_PRG_L"
    assert ref.reduction.args == []
    # A bare reduction prints without empty parens and re-parses unchanged.
    assert str(ref) == "advantage(PRGSec(G) compose R_PRG_L)"
    reparsed = _proof(str(ref))
    assert str(reparsed.claimed_bound.bound) == str(ref)


def test_direct_reference_has_no_reduction() -> None:
    pf = _proof("advantage(DDH(G))")
    assert pf.claimed_bound is not None
    ref = pf.claimed_bound.bound
    assert isinstance(ref, frog_ast.AdvantageReference)
    assert ref.reduction is None


def test_full_arithmetic_bound_roundtrips() -> None:
    src = (
        "advantage(PRFSecurity(F) compose R_PRF(E, F))"
        " + count_CTXT * (count_CTXT - 1) / |BitString<F.in>|"
    )
    pf = _proof(src)
    assert pf.claimed_bound is not None
    assert str(pf.claimed_bound.bound) == src
    # str(ProofFile) renders the clause so it re-parses to the same claim.
    reparsed = frog_parser.parse_proof_file(str(pf))
    assert reparsed.claimed_bound is not None
    assert str(reparsed.claimed_bound.bound) == src
