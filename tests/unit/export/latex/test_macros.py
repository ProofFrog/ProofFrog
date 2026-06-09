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
    assert r"\providecommand{\KeyGen}{\ensuremath{\mathsf{KeyGen}}}" in pre


def test_collision_with_latex_builtin_is_suffixed() -> None:
    r = MacroRegistry()
    tok = r.register_algorithm("Pr")
    assert tok != r"\Pr"


def test_single_letter_builtin_collisions_are_renamed() -> None:
    # \S (section sign), \H (Hungarian umlaut), \P (pilcrow), \O (slashed O),
    # \c (cedilla), \d (dot-under) are all base-LaTeX commands that
    # \providecommand cannot override, so they must be renamed.
    r = MacroRegistry()
    for name in ["S", "H", "P", "O", "L", "c", "d", "i", "j", "t"]:
        tok = r.register_algorithm(name)
        assert tok != "\\" + name, f"{name} collided with a LaTeX builtin"


def test_renamed_collision_still_displays_original_name() -> None:
    r = MacroRegistry()
    r.register_algorithm("S")
    pre = r.preamble()
    # The token is renamed, but the rendered body still shows S.
    assert r"\providecommand{\S}" not in pre
    assert r"\mathsf{S}" in pre


def test_non_colliding_single_letter_keeps_macro() -> None:
    # \G, \E, \F are not base-LaTeX commands, so the readable token is kept.
    r = MacroRegistry()
    assert r.register_algorithm("G") == r"\G"
    assert r.register_algorithm("E") == r"\E"
