"""Issue #255: split-declaration tuples must canonicalize like the
declaration-with-initializer spelling.

A bare product-typed local declaration (``[T, T] pair;``) followed by a
whole-variable or element-wise assignment used to survive canonicalization
unfolded (the ``Split Bare Tuple Declarations`` pass now normalizes it before
Topological Sorting prunes the declaration), so an identity hop between the
two spellings failed whenever the tuple elements were non-deterministic
calls. These tests cover the reporter's variant matrix end-to-end via
``check_equivalent``.
"""

from __future__ import annotations

from sympy import Symbol

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    """ProofEngine preloaded with a primitive exposing two distinct
    un-annotated (hence non-deterministic) methods, the shape the issue-#255
    reproduction needs: FoldTupleIndex must conservatively decline on the
    discarded element, so only the declaration split can fold the index."""
    prim = frog_parser.parse_primitive_file("""
        Primitive P(Int n) {
            BitString<n> Left(BitString<n> k);
            BitString<n> Right(BitString<n> k);
        }
        """)
    det_prim = frog_parser.parse_primitive_file("""
        Primitive D(Int n) {
            deterministic BitString<n> Left(BitString<n> k);
            deterministic BitString<n> Right(BitString<n> k);
        }
        """)
    engine = ProofEngine()
    engine.variables["n"] = Symbol("n", positive=True, integer=True)
    engine.proof_namespace["P"] = prim
    engine.proof_namespace["PP"] = prim
    engine.proof_namespace["D"] = det_prim
    engine.proof_namespace["DD"] = det_prim
    return engine


_DECL_WITH_INIT = """
    Game Post(P PP) {
        Void Initialize() {
        }
        BitString<n> Run() {
            BitString<n> a <- BitString<n>;
            BitString<n> b <- BitString<n>;
            [BitString<n>, BitString<n>] pair = [PP.Left(a), PP.Right(b)];
            return pair[1];
        }
    }
    """


def test_split_decl_whole_assignment_matches_initializer() -> None:
    """The issue's core reproduction: split declaration + whole-variable
    assignment of non-deterministic calls is an identity hop against the
    decl-with-initializer spelling."""
    pre = frog_parser.parse_game("""
        Game Pre(P PP) {
            Void Initialize() {
            }
            BitString<n> Run() {
                BitString<n> a <- BitString<n>;
                BitString<n> b <- BitString<n>;
                [BitString<n>, BitString<n>] pair;
                pair = [PP.Left(a), PP.Right(b)];
                return pair[1];
            }
        }
        """)
    post = frog_parser.parse_game(_DECL_WITH_INIT)
    result = _engine().check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_split_decl_element_writes_match_initializer() -> None:
    """Sibling spelling: the bare declaration written element-wise."""
    pre = frog_parser.parse_game("""
        Game Pre(P PP) {
            Void Initialize() {
            }
            BitString<n> Run() {
                BitString<n> a <- BitString<n>;
                BitString<n> b <- BitString<n>;
                [BitString<n>, BitString<n>] pair;
                pair[0] = PP.Left(a);
                pair[1] = PP.Right(b);
                return pair[1];
            }
        }
        """)
    post = frog_parser.parse_game(_DECL_WITH_INIT)
    result = _engine().check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_split_decl_conditional_assignment_matches_branch_form() -> None:
    """A bare declaration assigned in both arms of an ``if`` splits at the
    declaring block and the branch assignments rewrite in place."""
    pre = frog_parser.parse_game("""
        Game Pre(P PP) {
            Void Initialize() {
            }
            BitString<n> Run(Bool c) {
                BitString<n> a <- BitString<n>;
                BitString<n> b <- BitString<n>;
                [BitString<n>, BitString<n>] pair;
                if (c) {
                    pair = [PP.Left(a), PP.Right(b)];
                } else {
                    pair = [PP.Right(b), PP.Left(a)];
                }
                return pair[1];
            }
        }
        """)
    post = frog_parser.parse_game("""
        Game Post(P PP) {
            Void Initialize() {
            }
            BitString<n> Run(Bool c) {
                BitString<n> a <- BitString<n>;
                BitString<n> b <- BitString<n>;
                if (c) {
                    return PP.Right(b);
                }
                return PP.Left(a);
            }
        }
        """)
    result = _engine().check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_split_decl_plain_variables_matches_initializer() -> None:
    """Reporter's matrix: with plain variables as elements the hop already
    verified pre-fix (FoldTupleIndex folds it); it must keep verifying."""
    pre = frog_parser.parse_game("""
        Game Pre(P PP) {
            Void Initialize() {
            }
            BitString<n> Run() {
                BitString<n> a <- BitString<n>;
                BitString<n> b <- BitString<n>;
                [BitString<n>, BitString<n>] pair;
                pair = [a, b];
                return pair[1];
            }
        }
        """)
    post = frog_parser.parse_game("""
        Game Post(P PP) {
            Void Initialize() {
            }
            BitString<n> Run() {
                BitString<n> a <- BitString<n>;
                BitString<n> b <- BitString<n>;
                [BitString<n>, BitString<n>] pair = [a, b];
                return pair[1];
            }
        }
        """)
    result = _engine().check_equivalent(pre, post)
    assert result.valid, result.failure_detail


def test_split_decl_deterministic_calls_match_initializer() -> None:
    """Reporter's matrix: with ``deterministic``-annotated elements the hop
    already verified pre-fix; it must keep verifying."""
    pre = frog_parser.parse_game("""
        Game Pre(D DD) {
            Void Initialize() {
            }
            BitString<n> Run() {
                BitString<n> a <- BitString<n>;
                BitString<n> b <- BitString<n>;
                [BitString<n>, BitString<n>] pair;
                pair = [DD.Left(a), DD.Right(b)];
                return pair[1];
            }
        }
        """)
    post = frog_parser.parse_game("""
        Game Post(D DD) {
            Void Initialize() {
            }
            BitString<n> Run() {
                BitString<n> a <- BitString<n>;
                BitString<n> b <- BitString<n>;
                [BitString<n>, BitString<n>] pair = [DD.Left(a), DD.Right(b)];
                return pair[1];
            }
        }
        """)
    result = _engine().check_equivalent(pre, post)
    assert result.valid, result.failure_detail
