"""`sim` takes only a set of equalities, so a route with `sim` leaves must
decline a coupling that is not one.

The random-oracle reprogramming conjunct is a quantified IMPLICATION --
``forall (p : ...), <guard> => rF{1} p = rF{2} p`` -- and EasyCrypt refuses it
as an equality set: interactively *cannot recognize ... as a set of
equalities*, and inside a whole-oracle body *cannot infer the set of
equalities*.

`_synth_sim_field_rename` used to be shielded from that shape because
`_synth_ro_reprogram_oracle` ran ahead of it and took those oracles. With that
route retired the shape reaches the rename route, and without this gate it
emitted a tactic that RUNS WITHOUT CLOSING -- the worst state this exporter
can be in, since it yields a zero-admit file EasyCrypt rejects. Measured on
all four `INDCCA_PQ` proofs of the CG and UG frameworks, which went clean ->
REJECTED rather than clean -> accepted-with-admits until the gate was added.
"""

from proof_frog.export.easycrypt.chain_emitter import _coupling_has_implication

EQUALITIES = (
    "={ct} /\\ (glob KEM_PQ){1} = (glob KEM_PQ){2} /\\ "
    "GameFreshSS.seed_T{2} = RD.seed_T{1}"
)

REPROGRAMMING = EQUALITIES + (
    " /\\ forall (p : bs_2_ng_nelem_ng_nss_nlabel), "
    "slice_x p <> NG_c.ev_encode GameFreshSS.ctStar{2}.`2 => "
    "H_c.KDFPRFSec_Random.rF{1} p = GameFreshSS.rF{2} p"
)


def test_a_plain_equality_set_is_accepted() -> None:
    """The control the gate must not over-reach on: every coupling that is a
    conjunction of equalities is exactly what `sim` wants."""
    assert not _coupling_has_implication(EQUALITIES)


def test_the_reprogramming_conjunct_is_refused() -> None:
    assert _coupling_has_implication(REPROGRAMMING)


def test_a_bare_implication_is_refused() -> None:
    """Quantifier-free but still not an equality set."""
    assert _coupling_has_implication("a{1} = a{2} => b{1} = b{2}")


def test_a_bare_quantifier_is_refused() -> None:
    """A quantified equality is not an equality set either: `sim` needs
    program-variable pairs, not a fact about all inputs."""
    assert _coupling_has_implication("forall (p : t), f{1} p = f{2} p")
