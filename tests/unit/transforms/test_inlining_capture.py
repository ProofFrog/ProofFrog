"""Regression tests: inlining passes must not capture a free variable.

Name-based inlining is unsound when a `for` binder (or same-named local) at the
substitution site shadows a free variable of the inlined expression: after
inlining, that free variable reads the binder instead of its outer binding.
AlphaRename leaves loop binders in place, so the capture survives
canonicalization. (Audit RC4: F-150 and siblings.)
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import InlineSingleUseVariable
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(src: str) -> str:
    return str(InlineSingleUseVariable().apply(frog_parser.parse_game(src), _ctx()))


def test_f150_loop_binder_capture_declined() -> None:
    """`v = i + 1` (field i) must not inline into a `for (Int i = ...)` body:
    the binder `i` would capture the field reference."""
    out = _apply(
        """
        Game G(Int n) {
            Int i;
            Int Probe() {
                Int total = 0;
                Int v = i + 1;
                for (Int i = 0 to 2) {
                    total = total + v;
                }
                return total;
            }
        }
        """
    )
    assert "Int v = i + 1" in out  # not inlined into the loop body


def test_f150_no_capture_still_inlines() -> None:
    """Positive control: a differently-named binder does not capture, so the
    single-use variable still inlines."""
    out = _apply(
        """
        Game G(Int n) {
            Int i;
            Int Probe() {
                Int total = 0;
                Int v = i + 1;
                for (Int j = 0 to 2) {
                    total = total + v;
                }
                return total;
            }
        }
        """
    )
    assert "Int v = i + 1" not in out  # inlined
    assert "total + (i + 1)" in out


# ---------------------------------------------------------------------------
# Shadow-aware movers (RC4: F-169/F-173/F-178/F-190/F-210/F-228)
# ---------------------------------------------------------------------------

from proof_frog.transforms.inlining import (  # noqa: E402
    HoistDeterministicCallToInitialize,
    HoistDuplicateBranchCall,
    CrossMethodFieldAlias,
    SplitOpaqueTupleField,
    HoistGroupExpToInitialize,
    InlineSingleUseField,
    _method_bound_names,
    _name_shadowed_in_method,
)


def _det_ns():
    prim = frog_parser.parse_primitive_file(
        """
        Primitive P() {
            deterministic Int f(Int x);
        }
        """
    )
    return {"E": prim}


def _apply_pass(pass_obj, src, ns=None):
    game = frog_parser.parse_game(src)
    ctx = PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=ns or {},
        subsets_pairs=[],
    )
    return str(pass_obj.apply(game, ctx))


def test_method_bound_names_only_new_bindings() -> None:
    """Params, typed locals, and for-binders bind; a plain field write does
    not (it mutates the field in scope)."""
    game = frog_parser.parse_game(
        """
        Game G(Int n) {
            Int fld;
            Int O(Int p) {
                fld = 3;
                Int loc = 4;
                for (Int i = 0 to 2) { fld = fld + i; }
                return fld;
            }
        }
        """
    )
    bound = _method_bound_names(game.methods[0])
    assert "p" in bound and "loc" in bound and "i" in bound
    assert "fld" not in bound  # plain field write is not a new binding
    assert not _name_shadowed_in_method(game.methods[0], "fld")


def test_f173_stable_arg_shadowed_by_param_not_hoisted() -> None:
    """HoistDeterministicCallToInitialize must not treat `E.f(k)` as stable
    when `k` is a method parameter shadowing the field `k`."""
    out = _apply_pass(
        HoistDeterministicCallToInitialize(),
        """
        Game G() {
            Int k;
            Void Initialize() { k = 1; }
            Int Chal(Int k) { return E.f(k); }
        }
        """,
        _det_ns(),
    )
    assert "_hoisted" not in out  # the shadowed-arg call is not hoisted


def test_f178_forbinder_shadow_blocks_alias() -> None:
    """CrossMethodFieldAlias must not splice `Variable(stored)` into a method
    whose `for` binder is named `stored`."""
    out = _apply_pass(
        CrossMethodFieldAlias(),
        """
        Game G() {
            Int stored;
            Void Initialize() { stored = E.f(0); }
            Int Oracle() {
                Int acc = 0;
                for (Int stored = 0 to 2) { acc = acc + E.f(0); }
                return acc;
            }
        }
        """,
        _det_ns(),
    )
    # The oracle's E.f(0) is inside a `for (Int stored ...)`, so it is not
    # replaced by the field `stored`.
    assert "acc = acc + E.f(0)" in out


def test_f190_param_shadow_blocks_tuple_split() -> None:
    """SplitOpaqueTupleField must decline when a method parameter shadows the
    tuple field name."""
    out = _apply_pass(
        SplitOpaqueTupleField(),
        """
        Game G() {
            [Int, Int] pair;
            Void Initialize() { pair = E.pair(); }
            Int Echo([Int, Int] pair) { return pair[0]; }
            Int Use() { return pair[1]; }
        }
        """,
        {
            "E": frog_parser.parse_primitive_file(
                "Primitive P() { deterministic [Int, Int] pair(); }"
            )
        },
    )
    # `pair` is shadowed by Echo's parameter, so the field is not split.
    assert "__split" not in out and "pair_0" not in out


def test_f210_loop_binder_arg_not_hoisted_but_field_arg_is() -> None:
    """HoistDuplicateBranchCall must not hoist a call whose argument is a loop
    binder, but must still hoist one whose arg is a field."""
    declined = _apply_pass(
        HoistDuplicateBranchCall(),
        """
        Game G() {
            Int O(Bool b) {
                Int acc = 0;
                for (Int i = 0 to 2) {
                    if (b) { acc = acc + E.f(i); }
                    else { acc = acc + E.f(i); }
                }
                return acc;
            }
        }
        """,
        _det_ns(),
    )
    assert "__hoist" not in declined  # loop-binder arg: not hoisted


def test_f228_param_shadow_blocks_group_exp_hoist() -> None:
    """HoistGroupExpToInitialize must not freeze `h ^ e` when `e` is a method
    parameter shadowing the field `e`."""
    out = _apply_pass(
        HoistGroupExpToInitialize(),
        """
        Game G(Group Grp) {
            GroupElem<Grp> h;
            Int e;
            Void Initialize() { e = 1; h = Grp.generator; }
            GroupElem<Grp> Chal(Int e) { return h ^ e; }
        }
        """,
    )
    assert "_hge" not in out  # shadowed exponent not hoisted


def test_f228_route2_field_not_inlined_into_shadowed_param() -> None:
    """InlineSingleUseField must not inline field `e` into `Chal`'s `h ^ e`
    where `e` is the shadowing parameter (F-228 route 2)."""
    out = _apply_pass(
        InlineSingleUseField(),
        """
        Game G(Group Grp) {
            GroupElem<Grp> h;
            Int e;
            Void Initialize() { e = 1; h = Grp.generator; }
            GroupElem<Grp> Chal(Int e) { return h ^ e; }
        }
        """,
    )
    # The field `h` may inline (Grp.generator), but the exponent must stay the
    # parameter `e` -- the field `e`'s value (1) must NOT be substituted in.
    assert "^ e" in out
    assert "^ 1" not in out


# ---------------------------------------------------------------------------
# Cross-method call matching must be scope-aware at every site (F-338).
# F-173 checked shadowing only in the method a hoist candidate was found in;
# the replacement sites, Initialize, and the stable-alias map were name-blind.
# ---------------------------------------------------------------------------


def _det2_ns():
    prim = frog_parser.parse_primitive_file(
        """
        Primitive P() {
            deterministic Int f(Int x);
            deterministic Int g(Int a, Int b);
        }
        """
    )
    return {"E": prim}


def test_f338_hoist_not_replaced_in_shadowing_method() -> None:
    """The hoisted `E.f(k)` (field `k`) must not replace `E.f(k)` in a method
    whose parameter `k` shadows the field."""
    out = _apply_pass(
        HoistDeterministicCallToInitialize(),
        """
        Game G() {
            Int k;
            Void Initialize() { k = 1; }
            Int A() { return E.f(k); }
            Int B(Int k) { return E.f(k); }
        }
        """,
        _det_ns(),
    )
    assert "_hoisted_0 = E.f(k);" in out  # A's call is still hoisted
    assert "Int B(Int k) { \n    return E.f(k);" in out


def test_f338_hoist_declined_when_initialize_rebinds_arg() -> None:
    """A hoisted assignment is evaluated in Initialize, where a local `k`
    would capture the field `k`."""
    out = _apply_pass(
        HoistDeterministicCallToInitialize(),
        """
        Game G() {
            Int k;
            Int Initialize() { k = 1; Int k = 7; return k; }
            Int A() { return E.f(k); }
        }
        """,
        _det_ns(),
    )
    assert "_hoisted" not in out


def test_f338_hoist_initialize_return_stale_alias_not_rewritten() -> None:
    """`x = k; k = 2; return E.f(x);` must not become a read of the hoisted
    `E.f(k)`, which is evaluated after `k = 2`."""
    out = _apply_pass(
        HoistDeterministicCallToInitialize(),
        """
        Game G() {
            Int k;
            Int Initialize() { k = 1; Int x = k; k = 2; return E.f(x); }
            Int A() { return E.f(k); }
        }
        """,
        _det_ns(),
    )
    assert "return E.f(x);" in out
    assert "return _hoisted_0;\n  }\n}" in out  # A still reads the field


def test_f338_hoist_initialize_return_alias_still_rewritten() -> None:
    """Positive control: an alias whose field is not rewritten afterwards is
    still seen through in Initialize's return."""
    out = _apply_pass(
        HoistDeterministicCallToInitialize(),
        """
        Game G() {
            Int k;
            Int Initialize() { k = 1; Int x = k; return E.f(x); }
            Int A() { return E.f(k); }
        }
        """,
        _det_ns(),
    )
    assert "return _hoisted_0;" in out
    assert "return E.f(x);" not in out


def test_f338_cross_method_alias_not_applied_to_shadowed_call() -> None:
    """CrossMethodFieldAlias must not replace `E.f(k)` in a method whose
    parameter `k` shadows the field `k` cached in Initialize."""
    out = _apply_pass(
        CrossMethodFieldAlias(),
        """
        Game G() {
            Int k;
            Int c;
            Void Initialize() { k = 1; c = E.f(k); }
            Int B(Int k) { return E.f(k); }
        }
        """,
        _det_ns(),
    )
    assert "return E.f(k);" in out
    assert "return c;" not in out


def test_f338_cross_method_alias_rhs_reads_shadowing_param() -> None:
    """An oracle alias `h = E.f(k)` with `k` the method parameter is not a
    stable alias, so `E.g(h, y)` does not match Initialize's
    `E.g(E.f(k), y)` over the field `k`."""
    out = _apply_pass(
        CrossMethodFieldAlias(),
        """
        Game G() {
            Int k;
            Int y;
            Int c;
            Void Initialize() { k = 1; y = 2; c = E.g(E.f(k), y); }
            Int B(Int k) { Int h = E.f(k); return E.g(h, y); }
        }
        """,
        _det2_ns(),
    )
    assert "return E.g(h, y);" in out


def test_f338_cross_method_alias_reassigned_param_is_not_alias() -> None:
    """A parameter written once at top level is not an alias: before the write
    it still holds the caller's argument."""
    out = _apply_pass(
        CrossMethodFieldAlias(),
        """
        Game G() {
            Int k;
            Int y;
            Int c;
            Void Initialize() { k = 1; y = 2; c = E.g(y, k); }
            Int B(Int h) { Int a = E.g(h, k); h = y; return a + h; }
        }
        """,
        _det2_ns(),
    )
    assert "Int a = E.g(h, k);" in out


def test_f338_cross_method_alias_stale_initialize_alias() -> None:
    """`x = k; k = 2; c = E.f(x);` caches E.f(1), not the oracle's E.f(k)
    (which reads k = 2)."""
    out = _apply_pass(
        CrossMethodFieldAlias(),
        """
        Game G() {
            Int k;
            Int c;
            Void Initialize() { k = 1; Int x = k; k = 2; c = E.f(x); }
            Int A() { return E.f(k); }
        }
        """,
        _det_ns(),
    )
    assert "return E.f(k);" in out


def test_f338_alias_with_element_write_is_not_alias() -> None:
    """A local written again through an element write is not single-assignment."""
    from proof_frog.transforms.inlining import (  # pylint: disable=import-outside-toplevel
        _build_local_stable_alias_map,
    )

    game = frog_parser.parse_game(
        """
        Game G() {
            Array<Int, 2> k;
            Void Initialize() { k[0] = 1; }
            Int A() {
                Array<Int, 2> x = k;
                x[0] = 5;
                return E.f(x[0]);
            }
        }
        """
    )
    aliases = _build_local_stable_alias_map(
        game.methods[1], {"k"}, set(), _det_ns(), None, set()
    )
    assert "x" not in aliases


def test_f338_cross_method_alias_generator_alias_still_fires() -> None:
    """Positive control: a legitimate stable oracle alias is still seen through."""
    out = _apply_pass(
        CrossMethodFieldAlias(),
        """
        Game G() {
            Int k;
            Int y;
            Int c;
            Void Initialize() { k = 1; y = 2; c = E.g(E.f(k), y); }
            Int B(Int z) { Int h = E.f(k); return E.g(h, y) + z; }
        }
        """,
        _det2_ns(),
    )
    assert "return c + z;" in out
