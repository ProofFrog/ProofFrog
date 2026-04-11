"""Integration tests for the wizard scaffolding endpoint."""

import json
import shutil
from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis
from proof_frog.web_server import create_app


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "examples"
HYBRID_REL = "Proofs/PubKeyEnc/HybridPKEDEM_INDCPA_MultiChal.proof"
MULTIKEY_REL = "Proofs/PRF/PRFSecurity_implies_PRFSecurity_MultiKey.proof"


@pytest.fixture
def examples_root(tmp_path):
    """Copy the examples tree into a tmp_path so tests don't pollute the
    working tree (the scaffold endpoint writes to disk before parsing)."""
    dest = tmp_path / "examples"
    shutil.copytree(EXAMPLES_DIR, dest)
    return dest


@pytest.fixture
def client(examples_root):
    app, _observer = create_app(str(examples_root), watch=False)
    app.testing = True
    with app.test_client() as c:
        yield c, examples_root


def _post(client, path, payload):
    return client.post(
        path,
        data=json.dumps(payload),
        content_type="application/json",
        headers={"Origin": "http://127.0.0.1:localhost"},
    )


def test_scaffold_intermediate_game_smoke(client):
    c, examples_root = client
    content = (examples_root / HYBRID_REL).read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/intermediate-game",
        {"path": HYBRID_REL, "content": content, "name": "Test", "params": ""},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert "block" in body
    assert "Game Test(" in body["block"]
    # Substituted form: theorem game's formal `E` should have become `H`.
    assert (
        "H.Ciphertext Challenge(H.Message mL, H.Message mR)" in body["block"]
    )
    # Default param list comes from theorem args typed via let-bindings.
    assert body["params_used"] == "Hybrid H"


def test_scaffold_intermediate_game_parses_when_spliced(client):
    c, examples_root = client
    proof_path = examples_root / HYBRID_REL
    content = proof_path.read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/intermediate-game",
        {"path": HYBRID_REL, "content": content, "name": "ScaffoldTest", "params": ""},
    )
    assert resp.status_code == 200
    block = resp.get_json()["block"]

    # Splice the new block in just before "proof:". Write to a sibling
    # location of the original so relative imports resolve.
    spliced = content.replace("proof:", block + "\nproof:", 1)
    spliced_path = proof_path.with_name("Hybrid_spliced.proof")
    spliced_path.write_text(spliced, encoding="utf-8")
    frog_parser.parse_proof_file(str(spliced_path))


def test_scaffold_intermediate_game_typechecks_when_spliced(client):
    c, examples_root = client
    proof_path = examples_root / HYBRID_REL
    content = proof_path.read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/intermediate-game",
        {"path": HYBRID_REL, "content": content, "name": "ScaffoldTest2", "params": ""},
    )
    assert resp.status_code == 200
    block = resp.get_json()["block"]

    spliced = content.replace("proof:", block + "\nproof:", 1)
    spliced_path = proof_path.with_name("Hybrid_typechecked.proof")
    spliced_path.write_text(spliced, encoding="utf-8")

    parsed = frog_parser.parse_proof_file(str(spliced_path))
    # Should not raise FailedTypeCheck.
    semantic_analysis.check_well_formed(
        parsed, str(spliced_path), allowed_root=str(examples_root)
    )


def test_scaffold_intermediate_game_params_override(client):
    c, examples_root = client
    content = (examples_root / HYBRID_REL).read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/intermediate-game",
        {
            "path": HYBRID_REL,
            "content": content,
            "name": "Test",
            "params": "PubKeyEnc P",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["params_used"] == "PubKeyEnc P"
    assert "Game Test(PubKeyEnc P)" in body["block"]


def test_scaffold_intermediate_game_missing_name(client):
    c, examples_root = client
    content = (examples_root / HYBRID_REL).read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/intermediate-game",
        {"path": HYBRID_REL, "content": content, "name": "", "params": ""},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_scaffold_intermediate_game_malformed_proof(client):
    c, _ = client
    bad = "this is not valid frog\n"
    resp = _post(
        c,
        "/api/scaffold/intermediate-game",
        {"path": HYBRID_REL, "content": bad, "name": "Bad", "params": ""},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# ── Reduction stub scaffolding ──────────────────────────────────────────


def _reduction_payload(content, **overrides):
    payload = {
        "path": HYBRID_REL,
        "content": content,
        "name": "R_test",
        "security_game_name": "INDCPA_MultiChal",
        "side": "Left",
        "params": "SymEnc E, PubKeyEnc P, Hybrid H",
        "compose_args": "P",
    }
    payload.update(overrides)
    return payload


def test_scaffold_reduction_smoke(client):
    c, examples_root = client
    content = (examples_root / HYBRID_REL).read_text(encoding="utf-8")
    resp = _post(c, "/api/scaffold/reduction", _reduction_payload(content))
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert "block" in body
    block = body["block"]
    assert "Reduction R_test(SymEnc E, PubKeyEnc P, Hybrid H)" in block
    # Reduction declarations don't carry the side — that's chosen at the
    # use site in the games: list. The side argument is validated only.
    assert "compose INDCPA_MultiChal(P)" in block
    assert "against INDCPA_MultiChal(H).Adversary" in block
    # Substitution test: theorem-substituted form, not the security game's
    # formal `E`. This is the bug-fix assertion.
    assert "H.Ciphertext Challenge(H.Message mL, H.Message mR)" in block
    assert "E.Ciphertext Challenge" not in block


def test_scaffold_reduction_parses_when_spliced(client):
    c, examples_root = client
    proof_path = examples_root / HYBRID_REL
    content = proof_path.read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/reduction",
        _reduction_payload(content, name="R_spliced"),
    )
    assert resp.status_code == 200
    block = resp.get_json()["block"]

    spliced = content.replace("proof:", block + "\nproof:", 1)
    spliced_path = proof_path.with_name("Hybrid_red_spliced.proof")
    spliced_path.write_text(spliced, encoding="utf-8")
    frog_parser.parse_proof_file(str(spliced_path))


def test_scaffold_reduction_typechecks_when_spliced(client):
    c, examples_root = client
    proof_path = examples_root / HYBRID_REL
    content = proof_path.read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/reduction",
        _reduction_payload(content, name="R_typed"),
    )
    assert resp.status_code == 200
    block = resp.get_json()["block"]

    spliced = content.replace("proof:", block + "\nproof:", 1)
    spliced_path = proof_path.with_name("Hybrid_red_typed.proof")
    spliced_path.write_text(spliced, encoding="utf-8")

    parsed = frog_parser.parse_proof_file(str(spliced_path))
    semantic_analysis.check_well_formed(
        parsed, str(spliced_path), allowed_root=str(examples_root)
    )


def test_scaffold_reduction_missing_security_game(client):
    c, examples_root = client
    content = (examples_root / HYBRID_REL).read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/reduction",
        _reduction_payload(content, security_game_name="NoSuchGame"),
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_scaffold_reduction_missing_name(client):
    c, examples_root = client
    content = (examples_root / HYBRID_REL).read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/reduction",
        _reduction_payload(content, name=""),
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# ── Reduction hop scaffolding ───────────────────────────────────────────


def _reduction_hop_payload(content, **overrides):
    payload = {
        "path": MULTIKEY_REL,
        "content": content,
        "assumption_index": 0,
        "side1": "Real",
        "side2": "Random",
        "reduction_name": "R_Hybrid",
    }
    payload.update(overrides)
    return payload


def test_scaffold_reduction_hop_smoke(client):
    c, examples_root = client
    content = (examples_root / MULTIKEY_REL).read_text(encoding="utf-8")
    resp = _post(c, "/api/scaffold/reduction-hop", _reduction_hop_payload(content))
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert "lines" in body
    lines = body["lines"]
    assert len(lines) == 2
    assert (
        "PRFSecurity(F).Real compose R_Hybrid against PRFSecurity_MultiKey(F).Adversary;"
        in lines[0]
    )
    assert (
        "PRFSecurity(F).Random compose R_Hybrid against PRFSecurity_MultiKey(F).Adversary;"
        in lines[1]
    )
    # 4-space indentation matching games: block.
    assert lines[0].startswith("    ")
    assert lines[1].startswith("    ")


def test_scaffold_reduction_hop_parses_when_spliced(client):
    c, examples_root = client
    proof_path = examples_root / MULTIKEY_REL
    content = proof_path.read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/reduction-hop",
        _reduction_hop_payload(content, reduction_name="R_Hybrid(F, 1)"),
    )
    assert resp.status_code == 200
    lines = resp.get_json()["lines"]

    # Splice the two lines in just after the first existing games: line.
    marker = "PRFSecurity_MultiKey(F).Real against PRFSecurity_MultiKey(F).Adversary;"
    spliced = content.replace(
        marker,
        marker + "\n" + lines[0] + "\n" + lines[1],
        1,
    )
    spliced_path = proof_path.with_name("PRFSecurity_MultiKey_hop_spliced.proof")
    spliced_path.write_text(spliced, encoding="utf-8")
    frog_parser.parse_proof_file(str(spliced_path))


def test_scaffold_reduction_hop_typechecks_when_spliced(client):
    c, examples_root = client
    proof_path = examples_root / MULTIKEY_REL
    content = proof_path.read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/reduction-hop",
        _reduction_hop_payload(content, reduction_name="R_Hybrid(F, 1)"),
    )
    assert resp.status_code == 200
    lines = resp.get_json()["lines"]

    marker = "PRFSecurity_MultiKey(F).Real against PRFSecurity_MultiKey(F).Adversary;"
    spliced = content.replace(
        marker,
        marker + "\n" + lines[0] + "\n" + lines[1],
        1,
    )
    spliced_path = proof_path.with_name("PRFSecurity_MultiKey_hop_typed.proof")
    spliced_path.write_text(spliced, encoding="utf-8")

    parsed = frog_parser.parse_proof_file(str(spliced_path))
    semantic_analysis.check_well_formed(
        parsed, str(spliced_path), allowed_root=str(examples_root)
    )


def test_scaffold_reduction_hop_out_of_range(client):
    c, examples_root = client
    content = (examples_root / MULTIKEY_REL).read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/reduction-hop",
        _reduction_hop_payload(content, assumption_index=99),
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_scaffold_reduction_hop_invalid_side(client):
    c, examples_root = client
    content = (examples_root / MULTIKEY_REL).read_text(encoding="utf-8")
    resp = _post(
        c,
        "/api/scaffold/reduction-hop",
        _reduction_hop_payload(content, side1="Bogus"),
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()
