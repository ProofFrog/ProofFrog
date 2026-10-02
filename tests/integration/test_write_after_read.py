"""F-354: a write must stay below EVERY earlier read of the name it writes.

The statement-dependency graph used to give a write an edge to the nearest
earlier statement mentioning its name only. A second earlier reader, held back
by a dependency chain of its own, had no edge to the write, so the topological
sort placed it after the write and it read the new value: two distinguishable
games canonicalized to the same text.

Each case is a pair of proofs over one-oracle games, run through the real CLI
(parse, type check, instantiate, canonicalize):

- the *attack*: Right moves the delayed reader ``a`` below the write, so the
  two games return different values. It must be rejected.
- the *control*: Right only swaps the two readers, both still above the write.
  The games are equal, and the engine must still say so.

``S.Draw`` and ``S.Mix`` are non-deterministic calls, opaque to the engine;
the chain ``c -> d -> e`` is what delays ``a``.
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]

PRIMITIVES = {
    "Mix": """Primitive Mixer() {
    Int Draw();
    Int Mix(Int x, Int y);
}
""",
    "BMix": """Primitive BMixer(Int n) {
    Int n = n;
    BitString<n> Draw();
    BitString<n> Mix(BitString<n> x, BitString<n> y);
}
""",
}


@dataclass(frozen=True)
class Case:  # pylint: disable=too-many-instance-attributes
    """One write-after-read shape: a shared Left oracle body and two Rights."""

    name: str
    # Fields, Initialize and any other shared methods.
    prelude: str
    signature: str
    left: str
    attack: str
    control: str
    primitive: str = "Mix"
    let: str = "Mixer S;"

    def game_file(self, right: str) -> str:
        param = "BMixer S" if self.primitive == "BMix" else "Mixer S"

        def side(label: str, body: str) -> str:
            return (
                f"Game {label}({param}) {{\n{self.prelude}\n"
                f"    {self.signature} {{\n{body}    }}\n}}\n"
            )

        return (
            f"import '{self.primitive}.primitive';\n\n"
            + side("Left", self.left)
            + "\n"
            + side("Right", right)
            + "\nexport as Pair;\n"
        )

    def proof_file(self) -> str:
        return f"""import '{self.primitive}.primitive';
import 'Pair.game';

proof:

let:
    {self.let}

assume:

theorem:
    Pair(S);

games:
    Pair(S).Left against Pair(S).Adversary;
    Pair(S).Right against Pair(S).Adversary;
"""


CASES = [
    # A plain write to a field. Left returns (7 + e) + 7, the attack's Right
    # (5 + e) + 7.
    Case(
        name="field",
        prelude="""    Int f;
    Void Initialize() { f = 7; }""",
        signature="Int O()",
        left="""        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = f + e;
        Int b = f;
        f = 5;
        return a + b;
""",
        attack="""        Int c = S.Draw();
        Int b = f;
        Int d = S.Mix(c, c);
        f = 5;
        Int e = S.Mix(d, d);
        Int a = f + e;
        return a + b;
""",
        control="""        Int b = f;
        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = f + e;
        f = 5;
        return a + b;
""",
    ),
    # A write to a method parameter. With p = 0 Left returns e + 5, the
    # attack's Right e + 10.
    Case(
        name="parameter",
        prelude="",
        signature="Int O(Int p)",
        left="""        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = p + e;
        Int b = p;
        p = 5;
        return a + b + p;
""",
        attack="""        Int c = S.Draw();
        Int b = p;
        Int d = S.Mix(c, c);
        p = 5;
        Int e = S.Mix(d, d);
        Int a = p + e;
        return a + b + p;
""",
        control="""        Int b = p;
        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = p + e;
        p = 5;
        return a + b + p;
""",
    ),
    # A sample into a field. Left mixes the old f into a, the attack's Right
    # the freshly sampled one, which it also returns.
    Case(
        name="sample",
        primitive="BMix",
        let="Int n;\n    BMixer S = BMixer(n);",
        prelude="""    BitString<S.n> f;
    Void Initialize() { f <- BitString<S.n>; }""",
        signature="[BitString<S.n>, BitString<S.n>] O()",
        left="""        BitString<S.n> c = S.Draw();
        BitString<S.n> d = S.Mix(c, c);
        BitString<S.n> e = S.Mix(d, d);
        BitString<S.n> a = S.Mix(f, e);
        BitString<S.n> b = S.Mix(f, f);
        f <- BitString<S.n>;
        return [S.Mix(a, b), f];
""",
        attack="""        BitString<S.n> c = S.Draw();
        BitString<S.n> b = S.Mix(f, f);
        BitString<S.n> d = S.Mix(c, c);
        f <- BitString<S.n>;
        BitString<S.n> e = S.Mix(d, d);
        BitString<S.n> a = S.Mix(f, e);
        return [S.Mix(a, b), f];
""",
        control="""        BitString<S.n> b = S.Mix(f, f);
        BitString<S.n> c = S.Draw();
        BitString<S.n> d = S.Mix(c, c);
        BitString<S.n> e = S.Mix(d, d);
        BitString<S.n> a = S.Mix(f, e);
        f <- BitString<S.n>;
        return [S.Mix(a, b), f];
""",
    ),
    # A typed declaration with an initializer that shadows a field. Left's
    # readers see the field, the attack's delayed reader the new local. (The
    # name is one the alpha-renamer leaves alone, so the shadowing reaches the
    # sort.)
    Case(
        name="typed_shadowing_declaration",
        prelude="""    Int __a5__;
    Void Initialize() { __a5__ = 7; }
    Void Store(Int v) { __a5__ = v; }""",
        signature="Int O()",
        left="""        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = __a5__ + e;
        Int b = __a5__;
        Int __a5__ = S.Draw();
        return S.Mix(a + b, __a5__ + __a5__);
""",
        attack="""        Int c = S.Draw();
        Int b = __a5__;
        Int d = S.Mix(c, c);
        Int __a5__ = S.Draw();
        Int e = S.Mix(d, d);
        Int a = __a5__ + e;
        return S.Mix(b + a, __a5__ + __a5__);
""",
        control="""        Int b = __a5__;
        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = __a5__ + e;
        Int __a5__ = S.Draw();
        return S.Mix(a + b, __a5__ + __a5__);
""",
    ),
    # An element write to a map field.
    Case(
        name="map_element",
        prelude="""    Map<Int, Int> M;
    Void Initialize() { M[0] = 7; }""",
        signature="Int O()",
        left="""        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = M[0] + e;
        Int b = M[0];
        M[0] = 5;
        return a + b;
""",
        attack="""        Int c = S.Draw();
        Int b = M[0];
        Int d = S.Mix(c, c);
        M[0] = 5;
        Int e = S.Mix(d, d);
        Int a = M[0] + e;
        return a + b;
""",
        control="""        Int b = M[0];
        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = M[0] + e;
        M[0] = 5;
        return a + b;
""",
    ),
    # The write sits inside a branch: the `if` statement as a whole writes f.
    Case(
        name="write_in_branch",
        prelude="""    Int f;
    Void Initialize() { f = 7; }""",
        signature="Int O()",
        left="""        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = f + e;
        Int b = f;
        if (c == 0) {
            f = 5;
        }
        return a + b;
""",
        attack="""        Int c = S.Draw();
        Int b = f;
        Int d = S.Mix(c, c);
        if (c == 0) {
            f = 5;
        }
        Int e = S.Mix(d, d);
        Int a = f + e;
        return a + b;
""",
        control="""        Int b = f;
        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = f + e;
        if (c == 0) {
            f = 5;
        }
        return a + b;
""",
    ),
    # The write sits inside a loop body.
    Case(
        name="write_in_loop",
        prelude="""    Int f;
    Void Initialize() { f = 7; }""",
        signature="Int O()",
        left="""        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = f + e;
        Int b = f;
        for (Int i = 0 to 2) {
            f = f + c;
        }
        return a + b;
""",
        attack="""        Int c = S.Draw();
        Int b = f;
        Int d = S.Mix(c, c);
        for (Int i = 0 to 2) {
            f = f + c;
        }
        Int e = S.Mix(d, d);
        Int a = f + e;
        return a + b;
""",
        control="""        Int b = f;
        Int c = S.Draw();
        Int d = S.Mix(c, c);
        Int e = S.Mix(d, d);
        Int a = f + e;
        for (Int i = 0 to 2) {
            f = f + c;
        }
        return a + b;
""",
    ),
    # The field shares its name with a proof-level `let`. The graph used to
    # skip every name found in the proof namespace, so this field's reads and
    # writes were not ordered at all: Left returns 7, the attack's Right 5.
    Case(
        name="field_named_like_a_let",
        let="Int f;\n    Mixer S;",
        prelude="""    Int f;
    Void Initialize() { f = 7; }""",
        signature="Int O()",
        left="""        Int c = S.Draw();
        Int b = f;
        f = 5;
        return b + c;
""",
        attack="""        Int c = S.Draw();
        f = 5;
        Int b = f;
        return b + c;
""",
        control="""        Int b = f;
        Int c = S.Draw();
        f = 5;
        return b + c;
""",
    ),
]


def _prove(tmp_path: Path, case: Case, right: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / f"{case.primitive}.primitive").write_text(
        PRIMITIVES[case.primitive], encoding="utf-8"
    )
    (tmp_path / "Pair.game").write_text(case.game_file(right), encoding="utf-8")
    proof = tmp_path / "pair.proof"
    proof.write_text(case.proof_file(), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", "--sequential", str(proof)],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_f354_reader_moved_below_write_is_rejected(tmp_path: Path, case: Case) -> None:
    """The delayed reader sits below the write on the right only."""
    result = _prove(tmp_path, case, case.attack)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Proof Failed!" in result.stdout, result.stdout + result.stderr


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_f354_readers_swapped_above_write_still_verify(
    tmp_path: Path, case: Case
) -> None:
    """Sound twin: the two readers trade places, both still above the write."""
    result = _prove(tmp_path, case, case.control)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Proof Succeeded!" in result.stdout, result.stdout + result.stderr
