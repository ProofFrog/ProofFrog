"""Hardening of the algebra normalizer (F-370 part (e)).

Each case was reproduced at pass level only: no parsed, well-typed proof is
known to reach it. The tests apply one pass (or helper) to a hand-written
game and check that it declines, next to a control on which it still fires.
"""

import copy

from proof_frog import frog_ast
from proof_frog.transforms._algebra import Normalizer
from proof_frog.visitors import NameTypeMap


# --- (e) the normalizer's generator symbol ------------------------------------


def test_f370e_generators_of_groups_that_print_alike_stay_apart() -> None:
    # A Variable named "E.G" and the access E.G print alike; the generator
    # of the second must not be rebuilt as the first's.
    dotted = frog_ast.Variable("E.G")
    accessed = frog_ast.FieldAccess(frog_ast.Variable("E"), "G")
    q = frog_ast.Variable("q")
    types = NameTypeMap()
    types.set(
        "H1",
        frog_ast.FunctionType(frog_ast.GroupElemType(dotted), frog_ast.ModIntType(q)),
    )
    types.set(
        "H2",
        frog_ast.FunctionType(frog_ast.GroupElemType(accessed), frog_ast.ModIntType(q)),
    )
    first = frog_ast.FuncCall(
        frog_ast.Variable("H1"), [frog_ast.GroupGenerator(dotted)]
    )
    second = frog_ast.FuncCall(
        frog_ast.Variable("H2"),
        [
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EXPONENTIATE,
                frog_ast.GroupGenerator(accessed),
                frog_ast.Integer(1),
            )
        ],
    )
    out = Normalizer(types).canonical(
        frog_ast.BinaryOperation(frog_ast.BinaryOperators.ADD, first, second)
    )
    rebuilt = out.right_expression.args[0]
    assert rebuilt == frog_ast.FieldAccess(copy.deepcopy(accessed), "generator")
