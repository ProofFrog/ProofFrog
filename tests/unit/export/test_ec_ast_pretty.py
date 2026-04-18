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


def test_pretty_abstract_theory() -> None:
    th = ec_ast.AbstractTheory(
        name="SymEnc_Theory",
        decls=[
            ec_ast.TypeDecl("key"),
            ec_ast.ModuleType(
                "Scheme",
                procs=[ec_ast.ProcSig("keygen", [], ec_ast.EcType("key"))],
            ),
        ],
    )
    out = ec_ast.pretty_print(ec_ast.EcFile(requires=[], decls=[th]))
    assert "abstract theory SymEnc_Theory." in out
    assert "end SymEnc_Theory." in out
    assert "  type key." in out
    assert "  module type Scheme = {" in out


def test_pretty_clone_with_type_bindings() -> None:
    c = ec_ast.Clone(
        source_theory="SymEnc_Theory",
        alias="E",
        type_bindings=[
            ("key", "bs_lambda"),
            ("message", "bs_lambda"),
            ("ciphertext", "bs_lambda"),
        ],
    )
    out = ec_ast.pretty_print(ec_ast.EcFile(requires=[], decls=[c]))
    assert "clone SymEnc_Theory as E with" in out
    assert "  type key <- bs_lambda," in out
    assert "  type ciphertext <- bs_lambda." in out


def test_pretty_clone_empty() -> None:
    c = ec_ast.Clone(source_theory="SymEnc_Theory", alias="E", type_bindings=[])
    out = ec_ast.pretty_print(ec_ast.EcFile(requires=[], decls=[c]))
    assert "clone SymEnc_Theory as E." in out


def test_pretty_clone_with_op_bindings() -> None:
    c = ec_ast.Clone(
        source_theory="SymEnc_Theory",
        alias="E",
        type_bindings=[("key", "bs_lambda")],
        op_bindings=[("dkey", "dbs_lambda")],
    )
    out = ec_ast.pretty_print(ec_ast.EcFile(requires=[], decls=[c]))
    assert "  type key <- bs_lambda," in out
    assert "  op dkey <- dbs_lambda." in out


def test_qualified_helper() -> None:
    assert ec_ast.qualified("E", "Scheme") == "E.Scheme"


def test_declare_module_renders() -> None:
    dm = ec_ast.DeclareModule(name="E1", module_type="E1_c.Scheme")
    rendered = "\n".join(ec_ast._render_decl(dm))
    assert rendered == "declare module E1 <: E1_c.Scheme."


def test_section_renders_with_name() -> None:
    sec = ec_ast.Section(
        name="Main",
        decls=[
            ec_ast.DeclareModule("E1", "E1_c.Scheme"),
            ec_ast.DeclareModule("E2", "E2_c.Scheme"),
            ec_ast.TypeDecl("dummy"),
        ],
    )
    out = ec_ast.pretty_print(ec_ast.EcFile(requires=[], decls=[sec]))
    assert "section Main." in out
    assert "  declare module E1 <: E1_c.Scheme." in out
    assert "  declare module E2 <: E2_c.Scheme." in out
    assert "  type dummy." in out
    assert "end section Main." in out


def test_section_renders_without_name() -> None:
    sec = ec_ast.Section(name=None, decls=[ec_ast.TypeDecl("x")])
    out = ec_ast.pretty_print(ec_ast.EcFile(requires=[], decls=[sec]))
    assert "section." in out
    assert "end section." in out


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
