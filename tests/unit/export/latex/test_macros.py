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


# --- A3: more base-LaTeX letter-command collisions are renamed ---


def test_additional_letter_command_collisions_are_renamed() -> None:
    # \NG \ng \DJ \dj are base-LaTeX text-mode letter commands that
    # \providecommand cannot override, so they must be renamed.
    r = MacroRegistry()
    for name in ["NG", "ng", "DJ", "dj"]:
        tok = r.register_algorithm(name)
        assert tok != "\\" + name, f"{name} collided with a LaTeX builtin"


# --- A2: LaTeX specials in displayed macro bodies are escaped ---


def _no_bare_dollar(s: str) -> bool:
    return "$" not in s.replace(r"\$", "")


def test_register_algorithm_escapes_dollar_in_body() -> None:
    r = MacroRegistry()
    r.register_algorithm("INDOT$")
    assert _no_bare_dollar(r.preamble())


def test_register_security_notion_escapes_dollar_in_body() -> None:
    r = MacroRegistry()
    r.register_security_notion("INDCPA$")
    assert _no_bare_dollar(r.preamble())


def test_register_algorithm_escapes_specials_with_underscore() -> None:
    # An underscore-bearing name with a special in the subscript portion must
    # still produce a well-formed mathsf body.
    r = MacroRegistry()
    r.register_algorithm("IND_CPA$")
    assert _no_bare_dollar(r.preamble())


# --- Digit-bearing names must get distinct macro tokens ---


def test_digit_suffixed_names_get_distinct_tokens() -> None:
    # \Decaps macro names may contain only letters, so stripping the digit made
    # Decaps0 and Decaps1 collide on \Decaps; the first \providecommand won and
    # both oracles rendered as "Decaps". Distinct names must get distinct tokens.
    r = MacroRegistry()
    assert r.register_algorithm("Decaps0") != r.register_algorithm("Decaps1")


def test_digit_suffixed_name_distinct_from_undigited() -> None:
    r = MacroRegistry()
    assert r.register_algorithm("Decaps0") != r.register_algorithm("Decaps")


def test_digit_suffixed_names_render_distinct_bodies() -> None:
    # Both providecommands must survive into the preamble with their own bodies,
    # so the two oracle titles render distinctly.
    r = MacroRegistry()
    r.register_algorithm("Decaps0")
    r.register_algorithm("Decaps1")
    pre = r.preamble()
    assert r"\mathsf{Decaps0}" in pre
    assert r"\mathsf{Decaps1}" in pre
