"""Unit tests for the rendered-identity row's var-block comparison.

`_rendered_identity_step` closes a leg with `proc; sim.` when the two adjacent
flat states render to the same EC module. It used to compare whole
`ec_ast.Module` values, which made the `var` block's DECLARATION ORDER
load-bearing -- and declaration order is not observable. The micro-lemmas read
the var block only through `glob`, and EC orders a `glob` tuple by variable
NAME, the same fact `_canonical_field_renames` is built on and the fact
`tests/integration/ec_templates/glob_ignores_decl_order.ec` machine-checks in
both directions.

The measured consequence was a whole transform class that never closed: every
`Standardize Field Names` leg of the six IND-CCA_T exports differs from its
neighbour only by the order of identically-named, identically-typed `f<NN>`
declarations.

`_name_sorted_vars` is the normalization. It sorts, and does nothing else --
no dedupe, no retyping, no dropping -- so the tests below pin both that it
sees through ordering and that every genuine var difference still declines.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import _name_sorted_vars


def _mod(*vars_: tuple[str, str]) -> ec_ast.Module:
    return ec_ast.Module(
        name="S",
        procs=[
            ec_ast.Proc(
                name="f",
                params=[],
                return_type=ec_ast.EcType(text="int"),
                body=[ec_ast.Return("f00")],
            )
        ],
        module_vars=[
            ec_ast.VarDecl(name=n, type=ec_ast.EcType(text=t)) for n, t in vars_
        ],
    )


def test_a_permuted_var_block_is_the_same_module() -> None:
    """The measured `Standardize Field Names` shape: same names, same types,
    same body, declared in a different order."""
    left = _mod(("f01", "int"), ("f03", "bool"), ("f00", "int"))
    right = _mod(("f00", "int"), ("f01", "int"), ("f03", "bool"))
    assert left != right
    assert _name_sorted_vars(left) == _name_sorted_vars(right)


def test_a_renamed_field_still_differs() -> None:
    """A rename changes the `glob` tuple, so it must NOT be normalized away."""
    left = _mod(("f01", "int"), ("f00", "int"))
    right = _mod(("f02", "int"), ("f00", "int"))
    assert _name_sorted_vars(left) != _name_sorted_vars(right)


def test_a_retyped_field_still_differs() -> None:
    """Sorting by name alone would call these equal; the key carries the type
    so it does not."""
    left = _mod(("f00", "int"))
    right = _mod(("f00", "bool"))
    assert _name_sorted_vars(left) != _name_sorted_vars(right)


def test_an_added_field_still_differs() -> None:
    left = _mod(("f00", "int"))
    right = _mod(("f00", "int"), ("f01", "int"))
    assert _name_sorted_vars(left) != _name_sorted_vars(right)


def test_a_duplicate_declaration_is_not_collapsed() -> None:
    """Sorting is not a set. A state that somehow declares a name twice must
    stay distinguishable from one that declares it once, or the row would
    equate two modules with different `glob` arities."""
    left = _mod(("f00", "int"), ("f00", "int"))
    right = _mod(("f00", "int"))
    assert _name_sorted_vars(left) != _name_sorted_vars(right)


def test_the_body_is_untouched_by_the_normalization() -> None:
    """The normalization must reach the var block ONLY -- a body difference is
    the thing the row exists to decline."""
    left = _mod(("f00", "int"))
    right = _mod(("f00", "int"))
    right.procs[0].body = [ec_ast.Return("f00 + 1")]
    assert _name_sorted_vars(left) != _name_sorted_vars(right)
