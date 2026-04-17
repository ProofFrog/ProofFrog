"""Unit tests for the EC AST pretty-printer's new constructs."""

from __future__ import annotations

from proof_frog.export.easycrypt import ec_ast


def test_axiom_with_module_and_memory_params() -> None:
    axiom = ec_ast.Axiom(
        name="OneTimeSecrecy_advantage",
        formula=(
            "`| Pr[Game_OTS_Real(A).main() @ &m : res]"
            " - Pr[Game_OTS_Random(A).main() @ &m : res] |"
            " <= eps_OneTimeSecrecy"
        ),
        module_args=[ec_ast.ModuleParam("A", "OneTimeSecrecy_Adv {-OTP}")],
        memory_args=["&m"],
    )
    rendered = "\n".join(ec_ast._render_decl(axiom))
    assert "axiom OneTimeSecrecy_advantage" in rendered
    assert "(A <: OneTimeSecrecy_Adv {-OTP})" in rendered
    assert "&m" in rendered
    assert rendered.endswith(".")


def test_axiom_no_params_unchanged() -> None:
    """Backwards-compat: bare axioms still render as before."""
    axiom = ec_ast.Axiom(name="foo", formula="1 + 1 = 2")
    rendered = "\n".join(ec_ast._render_decl(axiom))
    assert rendered == "axiom foo : 1 + 1 = 2."


def test_prob_lemma_renders_correctly() -> None:
    lemma = ec_ast.ProbLemma(
        name="hop_0_pr",
        module_args=[ec_ast.ModuleParam("A", "OneTimeSecrecyLR_Adv {-OTP}")],
        memory_args=["&m"],
        statement=(
            "Pr[Game_step_0(A).main() @ &m : res]"
            " = Pr[Game_step_1(A).main() @ &m : res]"
        ),
        body=["byequiv => //; proc; call hop_0; auto.", "qed."],
    )
    rendered = "\n".join(ec_ast._render_decl(lemma))
    assert "lemma hop_0_pr" in rendered
    assert "(A <: OneTimeSecrecyLR_Adv {-OTP})" in rendered
    assert "&m" in rendered
    assert "Pr[Game_step_0(A).main() @ &m : res]" in rendered
    assert "byequiv" in rendered
    assert "qed." in rendered


def test_module_type_with_params() -> None:
    mt = ec_ast.ModuleType(
        name="OneTimeSecrecyLR_Adv",
        procs=[ec_ast.ProcSig("distinguish", [], ec_ast.EcType("bool"))],
        params=[ec_ast.ModuleParam("O", "OneTimeSecrecyLR_Oracle")],
    )
    rendered = "\n".join(ec_ast._render_decl(mt))
    assert rendered.startswith(
        "module type OneTimeSecrecyLR_Adv (O : OneTimeSecrecyLR_Oracle) = {"
    )
    assert "proc distinguish() : bool" in rendered
    assert rendered.endswith("}.")
