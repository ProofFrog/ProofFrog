"""Tests for FieldInvariantElimination and GeneratorPowerFieldToExponent.

The negative cases are the soundness-critical ones: a relation that holds
after Initialize but that some oracle breaks (or may break) must never be
used to remove a field.
"""

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.state_relations import (
    FieldInvariantElimination,
    GeneratorPowerFieldToExponent,
)
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    lets = NameTypeMap()
    group = frog_ast.Variable("G")
    lets.set("G", frog_ast.GroupType())
    lets.set(
        "H",
        frog_ast.FunctionType(
            frog_ast.GroupElemType(group),
            frog_ast.ModIntType(frog_ast.FieldAccess(group, "order")),
        ),
    )
    return PipelineContext(
        variables={}, proof_let_types=lets, proof_namespace={}, subsets_pairs=[]
    )


def _game(body: str) -> frog_ast.Game:
    return frog_parser.parse_game(f"Game T(Group G) {{\n{body}\n}}")


_KEYPAIR = """
    GroupElem<G> pk;
    ModInt<G.order> sk;

    GroupElem<G> Initialize() {
        ModInt<G.order> x <- ModInt<G.order>;
        pk = G.generator ^ x;
        sk = x;
        return pk;
    }

    ModInt<G.order> Reveal() {
        return sk;
    }
"""


def _field_names(game: frog_ast.Game) -> set[str]:
    return {field.name for field in game.fields}


# --- FieldInvariantElimination ---------------------------------------------


def test_eliminates_public_key_kept_in_step() -> None:
    game = _game(
        _KEYPAIR
        + """
    GroupElem<G> Upd(ModInt<G.order> d) {
        pk = pk * G.generator ^ d;
        sk = sk + d;
        return pk;
    }
    """
    )
    result = FieldInvariantElimination().apply(game, _ctx())
    assert _field_names(result) == {"sk"}


def test_eliminates_through_a_masked_update_token() -> None:
    # The secret moves by d recovered from a token masked with H(pk^u):
    # equal to d only because pk == g^sk.
    game = _game(
        _KEYPAIR
        + """
    GroupElem<G> Upd(ModInt<G.order> d, ModInt<G.order> u) {
        ModInt<G.order> v = d + H(pk ^ u);
        sk = sk + (v - H((G.generator ^ u) ^ sk));
        pk = pk * G.generator ^ d;
        return pk;
    }
    """
    )
    result = FieldInvariantElimination().apply(game, _ctx())
    assert _field_names(result) == {"sk"}


def test_keeps_field_when_an_oracle_breaks_the_relation() -> None:
    game = _game(
        _KEYPAIR
        + """
    GroupElem<G> Upd(ModInt<G.order> d) {
        pk = pk * G.generator ^ d;
        sk = sk + d + 1;
        return pk;
    }
    """
    )
    ctx = _ctx()
    result = FieldInvariantElimination().apply(game, ctx)
    assert result == game
    assert any(nm.transform_name == "Field Invariant Elimination" for nm in ctx.near_misses)


def test_keeps_field_when_one_branch_breaks_the_relation() -> None:
    game = _game(
        _KEYPAIR
        + """
    GroupElem<G> Upd(ModInt<G.order> d, Bool b) {
        if (b) {
            pk = pk * G.generator ^ d;
            sk = sk + d;
        } else {
            sk = sk + d;
        }
        return pk;
    }
    """
    )
    assert FieldInvariantElimination().apply(game, _ctx()) == game


def test_keeps_field_resampled_by_an_oracle() -> None:
    game = _game(
        _KEYPAIR
        + """
    GroupElem<G> Upd() {
        pk <- GroupElem<G>;
        return pk;
    }
    """
    )
    assert FieldInvariantElimination().apply(game, _ctx()) == game


def test_keeps_field_when_only_one_side_is_updated() -> None:
    game = _game(
        _KEYPAIR
        + """
    Void Upd(ModInt<G.order> d) {
        sk = sk + d;
    }
    GroupElem<G> Pk() {
        return pk;
    }
    """
    )
    assert FieldInvariantElimination().apply(game, _ctx()) == game


def test_keeps_field_when_relation_uses_a_loop_written_value() -> None:
    game = _game(
        _KEYPAIR
        + """
    GroupElem<G> Upd(ModInt<G.order> d, Int n) {
        for (Int i = 0 to n) {
            sk = sk + d;
        }
        pk = pk * G.generator ^ d;
        return pk;
    }
    """
    )
    assert FieldInvariantElimination().apply(game, _ctx()) == game


def test_eliminates_equal_flags() -> None:
    game = _game(
        """
    Bool done;
    Bool revealed;

    Void Initialize() {
        done = false;
        revealed = false;
    }

    Bool Reveal() {
        if (revealed) {
            return done;
        }
        done = true;
        revealed = true;
        return done;
    }
    """
    )
    result = FieldInvariantElimination().apply(game, _ctx())
    assert len(result.fields) == 1


def test_keeps_flags_that_diverge() -> None:
    game = _game(
        """
    Bool done;
    Bool revealed;

    Void Initialize() {
        done = false;
        revealed = false;
    }

    Bool Reveal() {
        revealed = true;
        return done;
    }

    Bool Finish() {
        done = true;
        return revealed;
    }
    """
    )
    assert FieldInvariantElimination().apply(game, _ctx()) == game


def test_does_not_use_a_nondeterministic_relation() -> None:
    # pk = F.Derive(x) with F not known to be deterministic: two calls may
    # differ, so pk == F.Derive(sk) is not a relation the pass may assume.
    game = _game(
        """
    GroupElem<G> pk;
    ModInt<G.order> sk;

    GroupElem<G> Initialize() {
        ModInt<G.order> x <- ModInt<G.order>;
        pk = F.Derive(x);
        sk = x;
        return pk;
    }

    GroupElem<G> Upd() {
        sk = sk;
        pk = F.Derive(sk);
        return pk;
    }
    """
    )
    assert FieldInvariantElimination().apply(game, _ctx()) == game


# --- GeneratorPowerFieldToExponent -----------------------------------------


def test_generator_power_field_becomes_exponent() -> None:
    game = _game(
        """
    GroupElem<G> pk;

    GroupElem<G> Initialize() {
        ModInt<G.order> x <- ModInt<G.order>;
        pk = G.generator ^ x;
        return pk;
    }

    GroupElem<G> Upd(ModInt<G.order> d) {
        pk = pk * G.generator ^ d;
        return pk;
    }
    """
    )
    result = GeneratorPowerFieldToExponent().apply(game, _ctx())
    (field,) = result.fields
    assert isinstance(field.type, frog_ast.ModIntType)
    assert "pk = " not in str(result)


def test_non_generator_factor_is_not_an_exponent_update() -> None:
    game = _game(
        """
    GroupElem<G> pk;

    GroupElem<G> Initialize() {
        ModInt<G.order> x <- ModInt<G.order>;
        pk = G.generator ^ x;
        return pk;
    }

    GroupElem<G> Upd(GroupElem<G> c) {
        pk = pk * c;
        return pk;
    }
    """
    )
    assert GeneratorPowerFieldToExponent().apply(game, _ctx()) == game


def test_squaring_is_not_an_exponent_update() -> None:
    game = _game(
        """
    GroupElem<G> pk;

    GroupElem<G> Initialize() {
        ModInt<G.order> x <- ModInt<G.order>;
        pk = G.generator ^ x;
        return pk;
    }

    GroupElem<G> Upd() {
        pk = pk * pk;
        return pk;
    }
    """
    )
    assert GeneratorPowerFieldToExponent().apply(game, _ctx()) == game


def test_read_before_initialization_blocks_conversion() -> None:
    # pk's default value is read before Initialize sets it; g^p would read
    # p's default instead, which is a different value.
    game = _game(
        """
    GroupElem<G> pk;
    GroupElem<G> old;

    GroupElem<G> Initialize() {
        old = pk;
        ModInt<G.order> x <- ModInt<G.order>;
        pk = G.generator ^ x;
        return old;
    }

    GroupElem<G> Upd(ModInt<G.order> d) {
        pk = pk * G.generator ^ d;
        return pk;
    }
    """
    )
    assert GeneratorPowerFieldToExponent().apply(game, _ctx()) == game


def test_sampled_group_field_is_not_converted() -> None:
    game = _game(
        """
    GroupElem<G> pk;

    GroupElem<G> Initialize() {
        pk <- GroupElem<G>;
        return pk;
    }

    GroupElem<G> Upd(ModInt<G.order> d) {
        pk = pk * G.generator ^ d;
        return pk;
    }
    """
    )
    assert GeneratorPowerFieldToExponent().apply(game, _ctx()) == game


def test_branch_conditions_rule_out_impossible_paths() -> None:
    # drawn == revealed. Past the guard revealed is false, so the then-branch
    # of `if (drawn)` cannot run; ignoring the condition would reach an exit
    # with drawn unchanged but revealed set.
    game = _game(
        """
    Bool drawn;
    Bool revealed;

    Void Initialize() {
        drawn = false;
        revealed = false;
    }

    Bool Draw() {
        if (revealed) {
            return false;
        }
        if (drawn) {
        } else {
            drawn = true;
        }
        revealed = true;
        return true;
    }
    """
    )
    result = FieldInvariantElimination().apply(game, _ctx())
    assert len(result.fields) == 1


def test_branch_condition_that_breaks_the_relation_is_kept() -> None:
    game = _game(
        """
    Bool drawn;
    Bool revealed;

    Void Initialize() {
        drawn = false;
        revealed = false;
    }

    Bool Close() {
        if (revealed) {
            drawn = false;
        }
        revealed = true;
        drawn = true;
        return true;
    }

    Bool Reopen() {
        if (revealed) {
            drawn = false;
            return true;
        }
        return false;
    }
    """
    )
    assert FieldInvariantElimination().apply(game, _ctx()) == game


# --- ForwardLiteralFieldWrite ----------------------------------------------


def test_literal_write_is_forwarded_to_later_reads() -> None:
    from proof_frog.transforms.state_relations import ForwardLiteralFieldWrite

    game = _game(
        """
    ModInt<G.order> D;
    ModInt<G.order> s;

    Void Initialize() {
        D = 0;
        ModInt<G.order> a <- ModInt<G.order>;
        s = a + D;
    }
    """
    )
    result = ForwardLiteralFieldWrite().apply(game, _ctx())
    assert "s = a + 0;" in str(result)


def test_literal_write_not_forwarded_past_a_write() -> None:
    from proof_frog.transforms.state_relations import ForwardLiteralFieldWrite

    game = _game(
        """
    ModInt<G.order> D;
    ModInt<G.order> s;

    Void Initialize() {
        D = 0;
        D = D + 1;
        s = D;
    }

    Void Bump(Bool b) {
        D = 0;
        if (b) {
            D = 5;
        }
        s = D;
    }
    """
    )
    result = ForwardLiteralFieldWrite().apply(game, _ctx())
    assert "s = D;" in str(result.methods[0])
    assert "s = D;" in str(result.methods[1])


def _zero_probe(use: str) -> frog_ast.Game:
    return _game(
        f"""
    ModInt<G.order> D;
    ModInt<G.order> s;
    Bool b;

    Void Probe(Int n, ModInt<G.order> a) {{
        D = 0;
        {use}
    }}
    """
    )


@pytest.mark.parametrize(
    "use",
    [
        # The Int 0 would be the base of an Int power (0 ^ 0 is the Int 1).
        "s = D ^ n;",
        # Both operands become Int, so the sum is the Int 0 + 0.
        "s = (D + D) ^ n;",
        "s = -D;",
        "s = a * D;",
        "s = D - a;",
        "b = D == s;",
        "s = D;",
    ],
)
def test_f379_modint_zero_kept_where_an_int_would_change_the_operation(
    use: str,
) -> None:
    # F-379: an integer literal is an Int, so the field's ModInt zero may
    # become the literal 0 only where the result keeps the ModInt type and
    # value: an operand of + (or the right operand of -) next to a ModInt
    # operand that does not read the field.
    from proof_frog.transforms.state_relations import ForwardLiteralFieldWrite

    game = _zero_probe(use)
    assert ForwardLiteralFieldWrite().apply(game, _ctx()) == game


@pytest.mark.parametrize(
    "use,forwarded",
    [
        ("s = a + D;", "s = a + 0;"),
        ("s = D + a;", "s = 0 + a;"),
        ("s = a - D;", "s = a - 0;"),
        ("s = (a + D) ^ n;", "s = (a + 0) ^ n;"),
    ],
)
def test_f379_modint_zero_forwarded_next_to_a_modint_operand(
    use: str, forwarded: str
) -> None:
    from proof_frog.transforms.state_relations import ForwardLiteralFieldWrite

    result = ForwardLiteralFieldWrite().apply(_zero_probe(use), _ctx())
    assert str(result.methods[0].block.statements[1]) == forwarded


def test_f379_int_zero_still_forwarded_into_a_power_base() -> None:
    # An Int field holds the Int literal exactly, wherever it is read.
    from proof_frog.transforms.state_relations import ForwardLiteralFieldWrite

    game = _game(
        """
    Int c;
    Int t;

    Void Probe(Int n) {
        c = 0;
        t = c ^ n;
    }
    """
    )
    result = ForwardLiteralFieldWrite().apply(game, _ctx())
    assert str(result.methods[0].block.statements[1]) == "t = 0 ^ n;"


# --- Shadowing (found by review: passes applied on their own) ---------------


def test_offset_fusion_refuses_a_parameter_named_like_the_offset() -> None:
    from proof_frog.transforms.state_relations import OffsetFusion

    game = _game(
        """
    GroupElem<G> P;
    ModInt<G.order> D;

    GroupElem<G> Initialize() {
        D = 0;
        ModInt<G.order> a <- ModInt<G.order>;
        P = G.generator ^ a;
        return P;
    }

    GroupElem<G> Shift(ModInt<G.order> d) {
        D = D + d;
        return P * G.generator ^ D;
    }

    GroupElem<G> Peek(ModInt<G.order> D) {
        return P;
    }
    """
    )
    assert OffsetFusion().apply(game, _ctx()) == game


def test_bare_local_declaration_shadows_a_group_field() -> None:
    game = _game(
        """
    GroupElem<G> P;

    GroupElem<G> Initialize() {
        ModInt<G.order> x <- ModInt<G.order>;
        P = G.generator ^ x;
        return P;
    }

    GroupElem<G> Upd(ModInt<G.order> d) {
        P = P * G.generator ^ d;
        return P;
    }

    GroupElem<G> Local(ModInt<G.order> y) {
        GroupElem<G> P;
        P = G.generator ^ y;
        return P;
    }
    """
    )
    assert GeneratorPowerFieldToExponent().apply(game, _ctx()) == game
