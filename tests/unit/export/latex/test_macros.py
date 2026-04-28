from proof_frog.export.latex.macros import MacroRegistry


def test_register_returns_macro_token() -> None:
    r = MacroRegistry()
    assert r.register_algorithm("Enc") == r"\Enc"


def test_register_is_idempotent() -> None:
    r = MacroRegistry()
    r.register_algorithm("Enc")
    r.register_algorithm("Enc")
    assert r.preamble().count(r"\providecommand{\Enc}") == 1


def test_preamble_uses_providecommand_and_mathsf() -> None:
    r = MacroRegistry()
    r.register_algorithm("KeyGen")
    pre = r.preamble()
    assert r"\providecommand{\KeyGen}{\mathsf{KeyGen}}" in pre


def test_collision_with_latex_builtin_is_suffixed() -> None:
    r = MacroRegistry()
    tok = r.register_algorithm("Pr")
    assert tok != r"\Pr"
