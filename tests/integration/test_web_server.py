import json
import shutil
from pathlib import Path

import pytest

from proof_frog.web_server import create_app


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "examples"


@pytest.fixture
def client(tmp_path):
    # Seed a primitive file with known content
    (tmp_path / "P.primitive").write_text(
        "Primitive P() {\n    BitString<8> F(BitString<8> x);\n}\n",
        encoding="utf-8",
    )
    app, _observer = create_app(str(tmp_path), watch=False)
    app.testing = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def examples_client(tmp_path):
    """Flask client rooted at a tmp copy of the real examples tree."""
    dest = tmp_path / "examples"
    shutil.copytree(EXAMPLES_DIR, dest)
    app, _observer = create_app(str(dest), watch=False)
    app.testing = True
    with app.test_client() as c:
        yield c, dest


def test_file_metadata_post_uses_request_content(client):
    new_content = (
        "Primitive P() {\n"
        "    deterministic BitString<8> G(BitString<8> y);\n"
        "}\n"
    )
    resp = client.post(
        "/api/file-metadata",
        data=json.dumps({"path": "P.primitive", "content": new_content}),
        content_type="application/json",
        headers={"Origin": "http://127.0.0.1:localhost"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["type"] == "primitive"
    assert body["name"] == "P"
    assert any("G" in m for m in body["methods"])
    assert not any("F(" in m for m in body["methods"])


def test_file_metadata_proof_resolves_renamed_import_assumption(examples_client):
    """Regression test: an `import '...' as Alias;` clause must let the proof
    metadata resolve assumption game references via the alias and return the
    game's side names. This is what the Insert Reduction Hop wizard relies on
    to populate its Direction dropdown.

    `examples/Proofs/PRF/MultiKeyFromPRF.proof` has:
        import '../../Games/PRF/Security.game' as PRFSecurity;
        ...
        assume:
            PRFSecurity(F);

    The basename of the imported file is `Security`, but the proof references
    it via the alias `PRFSecurity`. Resolution must use the alias.
    """
    c, examples_root = examples_client
    rel = "Proofs/PRF/MultiKeyFromPRF.proof"
    content = (examples_root / rel).read_text(encoding="utf-8")
    resp = c.post(
        "/api/file-metadata",
        data=json.dumps({"path": rel, "content": content}),
        content_type="application/json",
        headers={"Origin": "http://127.0.0.1:localhost"},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["type"] == "proof"
    details = body.get("assumption_details") or []
    assert len(details) >= 1, "expected at least one assumption_details entry"
    assumption_names = [d["name"] for d in details]
    assert "PRFSecurity" in assumption_names
    prf_entry = next(d for d in details if d["name"] == "PRFSecurity")
    # The imported Security.game has Real and Random sides.
    assert "Real" in prf_entry["sides"]
    assert "Random" in prf_entry["sides"]


def test_file_metadata_proof_resolves_theorem_with_export_rename(examples_client):
    """The theorem of MultiKeyFromPRF.proof references MultiKeyPRFSecurity,
    which is the export name of MultiKey.game (filename != export name)."""
    c, examples_root = examples_client
    rel = "Proofs/PRF/MultiKeyFromPRF.proof"
    content = (examples_root / rel).read_text(encoding="utf-8")
    resp = c.post(
        "/api/file-metadata",
        data=json.dumps({"path": rel, "content": content}),
        content_type="application/json",
        headers={"Origin": "http://127.0.0.1:localhost"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    theorem = body.get("theorem_details")
    assert theorem is not None
    assert theorem["name"] == "MultiKeyPRFSecurity"
    assert "Real" in theorem["sides"]
    assert "Random" in theorem["sides"]


POST_HEADERS = {"Origin": "http://127.0.0.1:localhost"}


def test_describe_endpoint(examples_client):
    c, examples_root = examples_client
    rel = "Primitives/KEM.primitive"
    content = (examples_root / rel).read_text(encoding="utf-8")
    resp = c.post(
        "/api/describe",
        data=json.dumps({"path": rel, "content": content}),
        content_type="application/json",
        headers=POST_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]
    assert "KEM" in body["output"]


def test_describe_endpoint_missing_data(examples_client):
    c, _ = examples_client
    resp = c.post(
        "/api/describe",
        data="",
        content_type="application/json",
        headers=POST_HEADERS,
    )
    assert resp.status_code == 400


def test_describe_endpoint_invalid_path(examples_client):
    c, _ = examples_client
    resp = c.post(
        "/api/describe",
        data=json.dumps({"path": "../escape.primitive", "content": ""}),
        content_type="application/json",
        headers=POST_HEADERS,
    )
    assert resp.status_code == 403


def test_check_endpoint(examples_client):
    c, examples_root = examples_client
    rel = "Primitives/KEM.primitive"
    content = (examples_root / rel).read_text(encoding="utf-8")
    resp = c.post(
        "/api/check",
        data=json.dumps({"path": rel, "content": content}),
        content_type="application/json",
        headers=POST_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]


def test_check_endpoint_reports_failure(examples_client):
    c, examples_root = examples_client
    rel = "Primitives/KEM.primitive"
    bad_content = (
        "Primitive KEM() {\n"
        "    Bool BadMethod(NoSuchType x);\n"
        "}\n"
    )
    resp = c.post(
        "/api/check",
        data=json.dumps({"path": rel, "content": bad_content}),
        content_type="application/json",
        headers=POST_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False


def test_inlined_game_endpoint(examples_client):
    c, examples_root = examples_client
    rel = "Proofs/PRG/TriplingPRGSecure.proof"
    content = (examples_root / rel).read_text(encoding="utf-8")
    step_text = "Security(T).Real against Security(T).Adversary"
    resp = c.post(
        "/api/inlined-game",
        data=json.dumps(
            {"path": rel, "content": content, "step_text": step_text}
        ),
        content_type="application/json",
        headers=POST_HEADERS,
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body.get("success") is True, body
    assert body.get("canonical")


def test_inlined_game_endpoint_with_reduction_reference(examples_client):
    """Regression: the minimal proof must include Reduction blocks so that
    step_text expressions like `compose R_DDH(...)` resolve. Previously the
    minimal-proof builder skipped Reduction blocks and the user got an
    `Error: \\`R_DDH'` parser failure."""
    c, examples_root = examples_client
    rel = "Proofs/Group/DDHImpliesHashedDDH.proof"
    content = (examples_root / rel).read_text(encoding="utf-8")
    step_text = (
        "DDH(G).Left compose R_DDH(G, n, H) against HashedDDH(G, n, H).Adversary"
    )
    resp = c.post(
        "/api/inlined-game",
        data=json.dumps(
            {"path": rel, "content": content, "step_text": step_text}
        ),
        content_type="application/json",
        headers=POST_HEADERS,
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body.get("success") is True, body
    assert body.get("canonical")


def test_inlined_game_endpoint_missing_step_text(examples_client):
    c, examples_root = examples_client
    rel = "Proofs/PRG/TriplingPRGSecure.proof"
    content = (examples_root / rel).read_text(encoding="utf-8")
    resp = c.post(
        "/api/inlined-game",
        data=json.dumps({"path": rel, "content": content, "step_text": "   "}),
        content_type="application/json",
        headers=POST_HEADERS,
    )
    assert resp.status_code == 400


def test_inlined_game_endpoint_invalid_path(examples_client):
    c, _ = examples_client
    resp = c.post(
        "/api/inlined-game",
        data=json.dumps(
            {
                "path": "../escape.proof",
                "content": "",
                "step_text": "X against Y",
            }
        ),
        content_type="application/json",
        headers=POST_HEADERS,
    )
    assert resp.status_code == 403
