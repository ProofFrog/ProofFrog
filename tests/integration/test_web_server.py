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
