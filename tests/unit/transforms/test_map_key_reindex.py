"""Tests for the MapKeyReindex transform pass (design §3)."""

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.map_reindex import MapKeyReindex
from proof_frog.visitors import NameTypeMap


_TRAPDOOR_PRIMITIVE = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    deterministic injective Image Eval(Input x);
}
"""


_NON_INJECTIVE_PRIMITIVE = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    deterministic Image Eval(Input x);
}
"""


_NON_DETERMINISTIC_PRIMITIVE = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    injective Image Eval(Input x);
}
"""


def _ctx_with_primitive(primitive_src: str = _TRAPDOOR_PRIMITIVE) -> PipelineContext:
    ctx = PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )
    if primitive_src:
        prim = frog_parser.parse_string(primitive_src, frog_ast.FileType.PRIMITIVE)
        ctx.proof_namespace[prim.name] = prim
        ctx.proof_namespace["TT"] = prim
    return ctx


def _apply(game_src: str, ctx: PipelineContext) -> frog_ast.Game:
    game = frog_parser.parse_game(game_src)
    return MapKeyReindex().apply(game, ctx)


def _apply_and_expect(
    game_src: str,
    expected_src: str,
    ctx: PipelineContext | None = None,
) -> None:
    ctx = ctx or _ctx_with_primitive()
    got = _apply(game_src, ctx)
    expected = frog_parser.parse_game(expected_src)
    assert got == expected, f"\nGOT:\n{got}\n\nEXPECTED:\n{expected}"


def _apply_and_expect_unchanged(
    game_src: str, ctx: PipelineContext | None = None
) -> None:
    ctx = ctx or _ctx_with_primitive()
    original = frog_parser.parse_game(game_src)
    got = MapKeyReindex().apply(original, ctx)
    assert got == original, f"\nGOT:\n{got}\n\nEXPECTED UNCHANGED:\n{original}"


def test_declines_raw_write_with_wrapped_read() -> None:
    """``M[a]`` stores at ``a`` and the read looks up ``Eval(a2)``. Re-keying
    the write alone would make the read hit when ``a2 = a``, not when
    ``Eval(a2) = a``."""
    _apply_and_expect_unchanged(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[a] = s;
            }
            BitString<16>? Lookup(TT.Input a2) {
                if (TT.Eval(a2) in M) {
                    return M[TT.Eval(a2)];
                }
                return None;
            }
        }
        """,
    )


def test_retypes_map_when_every_key_access_is_wrapped() -> None:
    """With no raw key to wrap and no loop to strip, only the key type
    changes."""
    _apply_and_expect(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[TT.Eval(a)] = s;
            }
            BitString<16>? Lookup(TT.Input a2) {
                if (TT.Eval(a2) in M) {
                    return M[TT.Eval(a2)];
                }
                return None;
            }
        }
        """,
        """
        Game G(T TT) {
            Map<TT.Image, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[TT.Eval(a)] = s;
            }
            BitString<16>? Lookup(TT.Input a2) {
                if (TT.Eval(a2) in M) {
                    return M[TT.Eval(a2)];
                }
                return None;
            }
        }
        """,
    )


def test_reindex_with_scan_loop() -> None:
    _apply_and_expect(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[a] = s;
            }
            BitString<16>? Scan(TT.Image y) {
                for ([TT.Input, BitString<16>] e in M.entries) {
                    if (TT.Eval(e[0]) == y) {
                        return e[1];
                    }
                }
                return None;
            }
        }
        """,
        """
        Game G(T TT) {
            Map<TT.Image, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[TT.Eval(a)] = s;
            }
            BitString<16>? Scan(TT.Image y) {
                for ([TT.Image, BitString<16>] e in M.entries) {
                    if (e[0] == y) {
                        return e[1];
                    }
                }
                return None;
            }
        }
        """,
    )


def test_declines_when_f_not_injective() -> None:
    _apply_and_expect_unchanged(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
            BitString<16>? Lookup(TT.Input a) {
                if (TT.Eval(a) in M) { return M[TT.Eval(a)]; }
                return None;
            }
        }
        """,
        _ctx_with_primitive(_NON_INJECTIVE_PRIMITIVE),
    )


def test_declines_when_f_not_deterministic() -> None:
    _apply_and_expect_unchanged(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
            BitString<16>? Lookup(TT.Input a) {
                if (TT.Eval(a) in M) { return M[TT.Eval(a)]; }
                return None;
            }
        }
        """,
        _ctx_with_primitive(_NON_DETERMINISTIC_PRIMITIVE),
    )


def test_declines_when_key_used_as_raw_A() -> None:
    _apply_and_expect_unchanged(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
            TT.Input Leak() {
                for ([TT.Input, BitString<16>] e in M.entries) {
                    return e[0];
                }
                return 0;
            }
        }
        """,
    )


# ---------------------------------------------------------------------------
# Multi-arg f: f(Secret sk, Input x) with sk a read-only post-Initialize field
# ---------------------------------------------------------------------------


_MULTIARG_PRIMITIVE = """
Primitive T(Set I, Set Y, Set K) {
    Set Input = I;
    Set Image = Y;
    Set Secret = K;
    deterministic injective Image Eval(Secret sk, Input x);
}
"""


def test_declines_raw_write_with_wrapped_read_multi_arg() -> None:
    _apply_and_expect_unchanged(
        """
        Game G(T TT) {
            TT.Secret sk;
            Map<TT.Input, BitString<16>> M;
            Void Initialize() {
                sk <- TT.Secret;
            }
            Void Store(TT.Input a, BitString<16> s) {
                M[a] = s;
            }
            BitString<16>? Lookup(TT.Input a) {
                if (TT.Eval(sk, a) in M) {
                    return M[TT.Eval(sk, a)];
                }
                return None;
            }
        }
        """,
        ctx=_ctx_with_primitive(_MULTIARG_PRIMITIVE),
    )


def test_reindex_multi_arg_with_scan_loop() -> None:
    _apply_and_expect(
        """
        Game G(T TT) {
            TT.Secret sk;
            Map<TT.Input, BitString<16>> M;
            Void Initialize() {
                sk <- TT.Secret;
            }
            Void Store(TT.Input a, BitString<16> s) {
                M[a] = s;
            }
            BitString<16>? Scan(TT.Image y) {
                for ([TT.Input, BitString<16>] e in M.entries) {
                    if (TT.Eval(sk, e[0]) == y) {
                        return e[1];
                    }
                }
                return None;
            }
        }
        """,
        """
        Game G(T TT) {
            TT.Secret sk;
            Map<TT.Image, BitString<16>> M;
            Void Initialize() {
                sk <- TT.Secret;
            }
            Void Store(TT.Input a, BitString<16> s) {
                M[TT.Eval(sk, a)] = s;
            }
            BitString<16>? Scan(TT.Image y) {
                for ([TT.Image, BitString<16>] e in M.entries) {
                    if (e[0] == y) {
                        return e[1];
                    }
                }
                return None;
            }
        }
        """,
        ctx=_ctx_with_primitive(_MULTIARG_PRIMITIVE),
    )


def test_declines_when_context_arg_assigned_outside_initialize() -> None:
    _apply_and_expect_unchanged(
        """
        Game G(T TT) {
            TT.Secret sk;
            Map<TT.Input, BitString<16>> M;
            Void Initialize() {
                sk <- TT.Secret;
            }
            Void Rotate() {
                sk <- TT.Secret;
            }
            Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
            BitString<16>? Lookup(TT.Input a) {
                if (TT.Eval(sk, a) in M) {
                    return M[TT.Eval(sk, a)];
                }
                return None;
            }
        }
        """,
        ctx=_ctx_with_primitive(_MULTIARG_PRIMITIVE),
    )


def test_declines_when_call_sites_disagree_on_context_arg() -> None:
    _apply_and_expect_unchanged(
        """
        Game G(T TT) {
            TT.Secret sk;
            TT.Secret sk2;
            Map<TT.Input, BitString<16>> M;
            Void Initialize() {
                sk <- TT.Secret;
                sk2 <- TT.Secret;
            }
            Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
            BitString<16>? Lookup1(TT.Input a) {
                if (TT.Eval(sk, a) in M) { return M[TT.Eval(sk, a)]; }
                return None;
            }
            BitString<16>? Lookup2(TT.Input a) {
                if (TT.Eval(sk2, a) in M) { return M[TT.Eval(sk2, a)]; }
                return None;
            }
        }
        """,
        ctx=_ctx_with_primitive(_MULTIARG_PRIMITIVE),
    )


# ---------------------------------------------------------------------------
# A key access that already applies the wrapper blocks re-keying
# ---------------------------------------------------------------------------


_SAME_TYPE_PRIMITIVE = """
Primitive T() {
    deterministic injective BitString<8> Eval(BitString<8> x);
}
"""


_WRAPPED_READS = [
    "Bool Has(BitString<8> b) { return TT.Eval(b) in M; }",
    "BitString<16> Get(BitString<8> b) { return M[TT.Eval(b)]; }",
]


_WRAPPED_WRITES = [
    "Void Put(BitString<8> b, BitString<16> s) { M[TT.Eval(b)] = s; }",
    "Void Fill(BitString<8> b) { M[TT.Eval(b)] <- BitString<16>; }",
]


_RAW_STORE = "Void Store(BitString<8> a, BitString<16> s) { M[a] = s; }"


_SCAN = """
    BitString<16>? Scan(BitString<8> y) {
        for ([BitString<8>, BitString<16>] e in M.entries) {
            if (TT.Eval(e[0]) == y) {
                return e[1];
            }
        }
        return None;
    }
"""


def _same_type_game(*methods: str) -> str:
    body = "\n".join(methods)
    return f"""
        Game G(T TT) {{
            Map<BitString<8>, BitString<16>> M;
            {body}
        }}
        """


def test_declines_raw_write_with_wrapped_constant_key() -> None:
    """After ``Put(0b00)``, ``Get(0b00)`` is true only if
    ``Tag(0b00) = 0b00``. Wrapping the write as ``e[S.Tag(pk)]`` would make
    it always true."""
    ctx = _ctx_with_primitive("""
        Primitive P() {
            deterministic injective BitString<2> Tag(BitString<2> x0);
        }
        """)
    ctx.proof_namespace["S"] = ctx.proof_namespace["P"]
    _apply_and_expect_unchanged(
        """
        Game Left(P S) {
            Map<BitString<2>, Bool> e;
            Bool Initialize() {
                return false;
            }
            Void Put(BitString<2> pk) {
                e[pk] = true;
            }
            Bool Get(BitString<2> pk) {
                if ((S.Tag(0^2) in e)) {
                    return e[S.Tag(0^2)];
                }
                return false;
            }
        }
        """,
        ctx,
    )


@pytest.mark.parametrize("access", _WRAPPED_READS, ids=["membership", "lookup"])
def test_declines_raw_write_with_wrapped_access(access: str) -> None:
    _apply_and_expect_unchanged(
        _same_type_game(_RAW_STORE, access),
        _ctx_with_primitive(_SAME_TYPE_PRIMITIVE),
    )


@pytest.mark.parametrize("store", [_RAW_STORE, ""], ids=["raw-write", "no-raw-write"])
@pytest.mark.parametrize(
    "access",
    _WRAPPED_READS + _WRAPPED_WRITES,
    ids=["membership", "lookup", "assignment", "sample"],
)
def test_declines_scan_with_wrapped_access(store: str, access: str) -> None:
    """Stripping ``Eval(e[0])`` in the loop re-keys every entry, so an access
    that already applies ``Eval`` would need it twice."""
    _apply_and_expect_unchanged(
        _same_type_game(store, access, _SCAN),
        _ctx_with_primitive(_SAME_TYPE_PRIMITIVE),
    )


def test_reindexes_raw_writes_with_scan_and_size() -> None:
    _apply_and_expect(
        _same_type_game(
            _RAW_STORE,
            "Void Fill(BitString<8> a) { M[a] <- BitString<16>; }",
            "Int Size() { return |M|; }",
            _SCAN,
        ),
        _same_type_game(
            "Void Store(BitString<8> a, BitString<16> s) { M[TT.Eval(a)] = s; }",
            "Void Fill(BitString<8> a) { M[TT.Eval(a)] <- BitString<16>; }",
            "Int Size() { return |M|; }",
            """
            BitString<16>? Scan(BitString<8> y) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == y) {
                        return e[1];
                    }
                }
                return None;
            }
            """,
        ),
        _ctx_with_primitive(_SAME_TYPE_PRIMITIVE),
    )
