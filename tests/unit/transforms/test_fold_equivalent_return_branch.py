"""Soundness regression tests for FoldEquivalentReturnBranch.

RC1 / F-119: ``_count_field_assigns_recursive`` counted only writes whose
l-value is a bare ``Variable``, so an element-mutated container field
(``F1[k] = v1``) was miscounted as single-write and the pass folded a branch
that returned it -- collapsing two genuinely-different container fields.  The
counter now peels element/slice/field accesses via ``lvalue_base_name``, so an
element-written field counts as written and the fold is declined.
"""

from proof_frog import frog_parser
from proof_frog.transforms.control_flow import FoldEquivalentReturnBranch
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str) -> tuple[object, object]:
    game = frog_parser.parse_game(source)
    result = FoldEquivalentReturnBranch().apply(game, _ctx())
    return game, result


def test_element_mutated_container_fields_not_folded() -> None:
    """Two container fields that are element-written with *different* values
    must not be folded into a single return branch."""
    game, result = _apply("""
        Game Containers(Dict D) {
            Map<Int, D.V> F1;
            Map<Int, D.V> F2;

            Void Initialize() {
                F1 = D.empty();
                F2 = D.empty();
            }

            Map<Int, D.V> Oracle(Bool flag, Int k, D.V v1, D.V v2) {
                F1[k] = v1;
                F2[k] = v2;
                if (flag) {
                    return F1;
                }
                return F2;
            }
        }
        """)
    assert result == game, f"branch wrongly folded:\n{result}"


def test_positive_fold_still_fires() -> None:
    """Control: the intended sound use -- ``if (a == b) return a; return b;``
    -- must still fold."""
    game, result = _apply("""
        Game Positive() {
            Int Oracle(Int a, Int b) {
                if (a == b) {
                    return a;
                }
                return b;
            }
        }
        """)
    assert result != game, "intended fold did not fire"


# ---------------------------------------------------------------------------
# RC3 determinism guard (F-118): a field initialized from a non-deterministic
# call must not be expanded to a textual copy of that call (which would let
# the fold equate two independent draws).
# ---------------------------------------------------------------------------


def _ctx_with(**namespace) -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=dict(namespace),
        subsets_pairs=[],
    )


def test_nondeterministic_init_field_rhs_not_folded() -> None:
    """``a = F.eval()`` in Initialize is a non-deterministic field write; the
    pass must not expand ``a`` to ``F.eval()`` and fold the case-split (the
    if-body re-evaluates ``F.eval()`` independently)."""
    prim = frog_parser.parse_primitive_file(
        "Primitive P(Int n) { BitString<n> eval(); }"
    )
    game = frog_parser.parse_game("""
        Game Collapse(P F, Int n) {
            BitString<n> a;
            Void Initialize() {
                a = F.eval();
            }
            BitString<n> O(BitString<n> k) {
                if (a == k) {
                    return F.eval();
                }
                return a;
            }
        }
        """)
    ctx = _ctx_with(P=prim, F=prim)
    result = FoldEquivalentReturnBranch().apply(game, ctx)
    assert result == game  # branch not folded
    assert any(
        nm.transform_name == "Fold Equivalent Return Branch" for nm in ctx.near_misses
    )


def test_deterministic_init_field_rhs_enables_fold() -> None:
    """Control: a field set from a deterministic call CAN be expanded so the
    case-split ``if (a == k) return D.eval(k); return a;`` folds under the
    Z3 model (``a == k`` makes ``D.eval(k)`` equal to ``a`` when ``a`` is the
    same deterministic call -- here we use a directly self-consistent case)."""
    prim = frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic BitString<n> eval(BitString<n> x); }"
    )
    game = frog_parser.parse_game("""
        Game Collapse(D F, Int n) {
            BitString<n> a;
            Void Initialize() {
                a = F.eval(a);
            }
            BitString<n> O(BitString<n> k) {
                if (a == k) {
                    return a;
                }
                return a;
            }
        }
        """)
    ctx = _ctx_with(D=prim, F=prim)
    result = FoldEquivalentReturnBranch().apply(game, ctx)
    assert result != game  # the trivially-equal branch folded


def test_init_rhs_field_reassigned_in_oracle_not_folded() -> None:
    """F-120: the Init-only RHS ``G = F.eval(k)`` references the field ``k``,
    which an oracle reassigns (``k = kp``).  At the fold site ``F.eval(k)``
    denotes ``F.eval(kp)``, not the stored ``G = F.eval(k_init)``, so the
    substitution that would fold ``if (flag) return G; return F.eval(k)`` into
    ``return F.eval(k)`` is unsound -- the pass must DECLINE."""
    prim = frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic BitString<n> eval(BitString<n> x); "
        "BitString<n> KeyGen(); }"
    )
    game = frog_parser.parse_game("""
        Game Collapse(D F, Int n) {
            BitString<n> k;
            BitString<n> G;
            Void Initialize() {
                k = F.KeyGen();
                G = F.eval(k);
            }
            BitString<n> Oracle(Bool flag, BitString<n> kp) {
                k = kp;
                if (flag) {
                    return G;
                }
                return F.eval(k);
            }
        }
        """)
    ctx = _ctx_with(D=prim, F=prim)
    result = FoldEquivalentReturnBranch().apply(game, ctx)
    assert result == game, "fold wrongly fired across a reassigned RHS field"
    assert any(
        nm.transform_name == "Fold Equivalent Return Branch"
        and "reassigned outside Initialize" in nm.reason
        for nm in ctx.near_misses
    )


def test_f342_init_local_resampled_between_definitions_not_folded() -> None:
    """F-342: ``G = F.eval(x); x <- ...; H = F.eval(x);`` in Initialize.  The
    recorded definitions of G and H have the same text but name different
    values of the local ``x``, so expanding them equated G with H and folded
    ``if (flag) return G; return H;`` into ``return H;`` -- the pass must
    DECLINE."""
    prim = frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic BitString<n> eval(BitString<n> x); }"
    )
    game = frog_parser.parse_game("""
        Game Collapse(D F, Int n) {
            BitString<n> G;
            BitString<n> H;
            Void Initialize() {
                BitString<n> x <- BitString<n>;
                G = F.eval(x);
                x <- BitString<n>;
                H = F.eval(x);
            }
            BitString<n> O(Bool flag) {
                if (flag) {
                    return G;
                }
                return H;
            }
        }
        """)
    ctx = _ctx_with(D=prim, F=prim)
    result = FoldEquivalentReturnBranch().apply(game, ctx)
    assert result == game, "fold wrongly fired across a re-sampled Initialize local"
    assert any(
        nm.transform_name == "Fold Equivalent Return Branch"
        and "Initialize local" in nm.reason
        for nm in ctx.near_misses
    )


def test_f342_single_assignment_init_local_still_folds() -> None:
    """F-342 control: with a single-assignment local, both fields are the same
    deterministic image of it, and the fold still fires."""
    prim = frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic BitString<n> eval(BitString<n> x); }"
    )
    game = frog_parser.parse_game("""
        Game Collapse(D F, Int n) {
            BitString<n> G;
            BitString<n> H;
            Void Initialize() {
                BitString<n> x <- BitString<n>;
                G = F.eval(x);
                H = F.eval(x);
            }
            BitString<n> O(Bool flag) {
                if (flag) {
                    return G;
                }
                return H;
            }
        }
        """)
    ctx = _ctx_with(D=prim, F=prim)
    result = FoldEquivalentReturnBranch().apply(game, ctx)
    assert result != game


def _fold(source: str) -> tuple[object, object, PipelineContext]:
    prim = frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic BitString<n> eval(BitString<n> x); }"
    )
    game = frog_parser.parse_game(source)
    ctx = _ctx_with(D=prim, F=prim)
    return game, FoldEquivalentReturnBranch().apply(game, ctx), ctx


def test_f345_rhs_field_written_only_in_oracle_not_folded() -> None:
    """F-345: ``G = F.eval(k)`` in Initialize, but ``k`` is written (once) in
    another oracle; at the fold site ``F.eval(k)`` need not equal ``G``."""
    game, result, _ = _fold("""
        Game G(D F, Int n) {
            BitString<n> k; BitString<n> G;
            Void Initialize() { G = F.eval(k); }
            Void SetK() { k <- BitString<n>; }
            BitString<n> O(Bool flag) { if (flag) { return G; } return F.eval(k); }
        }
        """)
    assert result == game


def test_f345_rhs_field_written_after_definition_not_folded() -> None:
    """F-345: ``G = F.eval(k); k <- ...;`` -- G is the image of the old k."""
    game, result, _ = _fold("""
        Game G(D F, Int n) {
            BitString<n> k; BitString<n> G;
            Void Initialize() { G = F.eval(k); k <- BitString<n>; }
            BitString<n> O(Bool flag) { if (flag) { return G; } return F.eval(k); }
        }
        """)
    assert result == game


def test_f345_rhs_field_written_before_definition_still_folds() -> None:
    """F-345 control: ``k <- ...; G = F.eval(k);`` with no other write of k."""
    game, result, _ = _fold("""
        Game G(D F, Int n) {
            BitString<n> k; BitString<n> G;
            Void Initialize() { k <- BitString<n>; G = F.eval(k); }
            BitString<n> O(Bool flag) { if (flag) { return G; } return F.eval(k); }
        }
        """)
    assert result != game


def test_f346_rhs_local_captured_by_oracle_parameter_not_folded() -> None:
    """F-346: the Initialize local ``x`` in ``G = F.eval(x)`` has the same name
    as the oracle's parameter ``x``; expanding G at the fold site would read
    the parameter."""
    game, result, ctx = _fold("""
        Game G(D F, Int n) {
            BitString<n> G;
            Void Initialize() { BitString<n> x <- BitString<n>; G = F.eval(x); }
            BitString<n> O(BitString<n> x, Bool c) {
                if (c) { return G; }
                return F.eval(x);
            }
        }
        """)
    assert result == game
    assert any("bound in this method" in nm.reason for nm in ctx.near_misses)
