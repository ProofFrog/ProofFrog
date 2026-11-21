"""Unit tests for EmptyCollectionField."""

import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.control_flow import EmptyCollectionField
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str) -> frog_ast.Game:
    return EmptyCollectionField().apply(frog_parser.parse_game(source), _ctx())


# ---------------------------------------------------------------------------
# Folds
# ---------------------------------------------------------------------------


def test_folds_membership_in_unwritten_set() -> None:
    """The corruption set of a challenger whose Corrupt is never forwarded."""
    result = _apply("""
        Game G() {
            Set<Int> C;
            Bool Challenge(Int r0, Int r1) {
                if (r0 in C || r1 in C) {
                    return false;
                }
                return true;
            }
        }
        """)
    expected = frog_parser.parse_game("""
        Game G() {
            Set<Int> C;
            Bool Challenge(Int r0, Int r1) {
                if (false || false) {
                    return false;
                }
                return true;
            }
        }
        """)
    assert result == expected


def test_folds_membership_in_unwritten_map_and_size() -> None:
    result = _apply("""
        Game G() {
            Map<Int, Bool> M;
            Set<Int> S;
            Bool Query(Int k) {
                return k in M || |S| == 0;
            }
        }
        """)
    expected = frog_parser.parse_game("""
        Game G() {
            Map<Int, Bool> M;
            Set<Int> S;
            Bool Query(Int k) {
                return false || 0 == 0;
            }
        }
        """)
    assert result == expected


def test_folds_whatever_the_element_reads() -> None:
    """Evaluation is total (FROGLANG_REFERENCE.md 6.9): dropping the
    element's evaluation is unobservable even when it indexes a map at a
    possibly absent key or reads a variable that may be unassigned."""
    result = _apply("""
        Game G() {
            Map<Int, Int> M;
            Int f;
            Set<Int> C;
            Void Store(Int k, Int v) {
                M[k] = v;
                f = v;
            }
            Bool Query(Int x, Bool c) {
                Int y;
                if (c) {
                    y = 1;
                }
                return (M[x] in C) || (y in C) || (f + 1 in C);
            }
        }
        """)
    expected = frog_parser.parse_game("""
        Game G() {
            Map<Int, Int> M;
            Int f;
            Set<Int> C;
            Void Store(Int k, Int v) {
                M[k] = v;
                f = v;
            }
            Bool Query(Int x, Bool c) {
                Int y;
                if (c) {
                    y = 1;
                }
                return false || false || false;
            }
        }
        """)
    assert result == expected


def test_folds_one_field_and_keeps_a_written_one() -> None:
    result = _apply("""
        Game G() {
            Set<Int> C;
            Set<Int> D;
            Void Corrupt(Int i) {
                D = D union {i};
            }
            Bool Query(Int x) {
                return x in C || x in D;
            }
        }
        """)
    expected = frog_parser.parse_game("""
        Game G() {
            Set<Int> C;
            Set<Int> D;
            Void Corrupt(Int i) {
                D = D union {i};
            }
            Bool Query(Int x) {
                return false || x in D;
            }
        }
        """)
    assert result == expected


# ---------------------------------------------------------------------------
# Declines: each game is returned unchanged. The comment names the
# adversary that would tell the game from its folded form.
# ---------------------------------------------------------------------------

_DECLINES = {
    # Corrupt(1); Query(1) returns true, the folded game false.
    "set_written_by_union": """
        Game G() {
            Set<Int> C;
            Void Corrupt(Int i) {
                C = C union {i};
            }
            Bool Query(Int x) {
                return x in C;
            }
        }
        """,
    # Store(1); Query(1) returns true.
    "map_element_written": """
        Game G() {
            Map<Int, Bool> M;
            Void Store(Int k) {
                M[k] = true;
            }
            Bool Query(Int k) {
                return k in M;
            }
        }
        """,
    # Store(1); Query(1) returns true.
    "map_element_sampled": """
        Game G() {
            Map<Int, Bool> M;
            Void Store(Int k) {
                M[k] <- Bool;
            }
            Bool Query(Int k) {
                return k in M;
            }
        }
        """,
    # Draw() puts its result in C; Query(Draw()) returns true.
    "set_accumulated_by_uniq_sample": """
        Game G() {
            Set<BitString<8>> C;
            BitString<8> Draw() {
                BitString<8> x <-uniq[C] BitString<8>;
                return x;
            }
            Bool Query(BitString<8> x) {
                return x in C;
            }
        }
        """,
    # The initializer makes C nonempty: Query(1) returns true.
    "field_with_initializer": """
        Game G() {
            Set<Int> C = {1};
            Bool Query(Int x) {
                return x in C;
            }
        }
        """,
    # Here C is the parameter: Query({1}, 1) returns true.
    "parameter_shadows_field": """
        Game G() {
            Set<Int> C;
            Bool Query(Set<Int> C, Int x) {
                return x in C;
            }
        }
        """,
    # Inside the loop C is the binder: Query({{1}}, 1) returns true.
    "loop_binder_shadows_field": """
        Game G() {
            Set<Int> C;
            Bool Query(Set<Set<Int>> SS, Int x) {
                for (Set<Int> C in SS) {
                    if (x in C) {
                        return true;
                    }
                }
                return false;
            }
        }
        """,
    # Under reference semantics for maps, Alias(1) writes C through D and
    # Query(1) returns true. The pass does not decide aliasing: any
    # occurrence of C other than 'e in C' / '|C|' declines.
    "copied_into_local": """
        Game G() {
            Map<Int, Bool> C;
            Void Alias(Int k) {
                Map<Int, Bool> D = C;
                D[k] = true;
            }
            Bool Query(Int k) {
                return k in C;
            }
        }
        """,
    # Dropping a call drops whatever it does: a non-deterministic method
    # may draw, a random function is sampled lazily. Conservative: kept.
    "element_makes_a_call": """
        Game G() {
            Set<Int> C;
            Bool Query(Int x) {
                return E.f(x) in C;
            }
        }
        """,
}


@pytest.mark.parametrize("source", _DECLINES.values(), ids=_DECLINES.keys())
def test_declines(source: str) -> None:
    game = frog_parser.parse_game(source)
    assert EmptyCollectionField().apply(game, _ctx()) == game


def test_field_access_spelling_is_not_folded() -> None:
    """Defensive: a field access ending in the field's name (here on a
    parameter) is a spelling the survivor check cannot see, so C stays."""
    game = frog_parser.parse_game("""
        Game G() {
            Set<Int> C;
            Bool Query(Int x, E e) {
                return x in C || x in e.C;
            }
        }
        """)
    assert EmptyCollectionField().apply(game, _ctx()) == game


def test_bare_local_declaration_is_not_folded() -> None:
    """A bare local `Set<Int> C;` stores its name as a string, so it leaves no
    occurrence for the survivor check; the name is excluded up front."""
    game = frog_parser.parse_game("""
        Game G() {
            Set<Int> C;
            Bool Query(Int x) {
                Set<Int> C;
                return x in C;
            }
        }
        """)
    assert EmptyCollectionField().apply(game, _ctx()) == game


def test_type_valued_set_field_is_not_folded() -> None:
    """`Set F;` is a field holding a type, not a collection (the type checker
    rejects it in games today; the pass does not rely on that)."""
    game = frog_parser.parse_game("""
        Game G() {
            Set F;
            Bool Query(Int x) {
                return x in F;
            }
        }
        """)
    assert EmptyCollectionField().apply(game, _ctx()) == game


def test_scheme_field_name_is_not_folded() -> None:
    """F-031 stopgap. Inlining a scheme method leaves its reads of the
    scheme's own fields as bare names, which a game field of the same name
    captures. Here the inlined game reads `S` meaning the scheme's
    `S = {1}` (kept because some scheme method writes it), so folding
    `x in S` would answer false where the game answers true for x = 1."""
    scheme = frog_parser.parse_scheme_file("""
        Scheme Sch() extends P {
            Set<Int> S = {1};
            Bool Check(Int x) {
                return x in S;
            }
            Void Add(Int x) {
                S = S union {x};
            }
        }
        """)
    game = frog_parser.parse_game("""
        Game G() {
            Set<Int> S;
            Bool Q(Int x) {
                return x in S;
            }
        }
        """)
    ctx = _ctx()
    ctx.proof_namespace["E"] = scheme
    assert EmptyCollectionField().apply(game, ctx) == game


def test_let_name_is_not_folded() -> None:
    """A field whose name is also a proof let: name is left alone."""
    game = frog_parser.parse_game("""
        Game G() {
            Set<Int> C;
            Bool Query(Int x) {
                return x in C;
            }
        }
        """)
    ctx = _ctx()
    ctx.proof_let_types.set("C", frog_ast.SetType(frog_ast.IntType()))
    assert EmptyCollectionField().apply(game, ctx) == game
