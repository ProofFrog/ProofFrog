"""Regression test: ExtractRepeatedTupleAccess slice-bound purity (F-235).

A slice `v[A:B]` whose bounds contain a non-deterministic call
(`v[P.Cut():P.Cut()+n]`) must NOT be deduplicated with a structurally-equal
sibling: each occurrence draws fresh, so merging them into one shared local
correlates independent i.i.d. draws (ruling 7.A.6).

Calls in slice bounds are not source-parseable, so the shape is built by
substituting `P.Cut()` for a placeholder variable, mirroring the audit's
pass-level harness.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.visitors import SubstitutionTransformer
from proof_frog.transforms.inlining import ExtractRepeatedTupleAccessTransformer


def _cut_ns():
    prim = frog_parser.parse_primitive_file("Primitive Cutter() { Int Cut(); }")
    return {"P": prim}


def _sub_cut_for_c(game: frog_ast.Game) -> frog_ast.Game:
    call = frog_ast.FuncCall(frog_ast.FieldAccess(frog_ast.Variable("P"), "Cut"), [])
    ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
    ast_map.set(frog_ast.Variable("c"), call)
    return SubstitutionTransformer(ast_map).transform(game)


def test_f235_declines_dedup_of_nondet_slice_bounds() -> None:
    # `v[c:c+n]` twice, with `c` -> P.Cut() (non-deterministic).
    game = frog_parser.parse_game("""
        Game G(Cutter P, Int n) {
            [BitString<n>, BitString<n>] O(BitString<n> v, Int c) {
                BitString<n> x = v[c : c + n];
                BitString<n> y = v[c : c + n];
                return [x, y];
            }
        }
        """)
    game = _sub_cut_for_c(game)
    out = str(
        ExtractRepeatedTupleAccessTransformer(proof_namespace=_cut_ns()).transform(game)
    )
    # The two slices must remain separate (each keeps its own P.Cut() draws).
    assert "__cse_slice" not in out
    assert out.count("v[P.Cut() : P.Cut() + n]") == 2


def test_f235_still_dedups_deterministic_slice_bounds() -> None:
    # Plain deterministic bounds -> the repeated slice IS extracted.
    game = frog_parser.parse_game("""
        Game G(Int n) {
            [BitString<n>, BitString<n>] O(BitString<n> v) {
                BitString<n> x = v[0 : n];
                BitString<n> y = v[0 : n];
                return [x, y];
            }
        }
        """)
    out = str(ExtractRepeatedTupleAccessTransformer().transform(game))
    assert "__cse_slice" in out


def test_f231_declines_merge_across_bound_reassignment() -> None:
    """F-231: two structurally-equal `v[t:t+n]` slices separated by `t = n`
    span DIFFERENT ranges (t changed), so they must not be merged into one
    shared local. The reassignment guard now covers the bound variables, not
    just the base."""
    game = frog_parser.parse_game(
        """
        Game G(Int n) {
            Bool O(BitString<n + n + n> v, Int t) {
                BitString<n> x = v[t : t + n];
                t = n;
                BitString<n> y = v[t : t + n];
                return x == y;
            }
        }
        """
    )
    out = str(ExtractRepeatedTupleAccessTransformer().transform(game))
    assert "__cse_slice" not in out  # not merged


def test_f234_declines_merge_across_forbinder_bound() -> None:
    """F-234: two `v[j-n:j]` slices in sibling `for` loops share a bound
    variable `j` that is a per-loop binder; they must not be hoisted/merged
    across the binders (the shared reassigns_or_rebinds detects for-binders)."""
    game = frog_parser.parse_game(
        """
        Game G(Int n) {
            BitString<n> O(BitString<n + n + n> v) {
                BitString<n> acc = 0^n;
                for (Int j = n to n + n) { acc = v[j - n : j]; }
                for (Int j = n to n + n) { acc = v[j - n : j]; }
                return acc;
            }
        }
        """
    )
    out = str(ExtractRepeatedTupleAccessTransformer().transform(game))
    assert "__cse_slice" not in out  # not merged across the for-binders


def test_f231_stable_bounds_still_merge() -> None:
    """Positive control: constant bounds with no reassignment still merge."""
    game = frog_parser.parse_game(
        """
        Game G(Int n) {
            Bool O(BitString<n + n + n> v) {
                BitString<n> x = v[0 : n];
                BitString<n> y = v[0 : n];
                return x == y;
            }
        }
        """
    )
    out = str(ExtractRepeatedTupleAccessTransformer().transform(game))
    assert "__cse_slice" in out  # merged
