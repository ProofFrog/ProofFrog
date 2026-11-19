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
    """The proof file imports PRFSecurity.game and references PRFSecurity(F)
    in its assume: block. The metadata must resolve this and return the
    game's side names for the Insert Reduction Hop wizard.
    """
    c, examples_root = examples_client
    rel = "Proofs/PRF/PRFSecurity_implies_PRFSecurity_MultiKey.proof"
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
    assert "Real" in prf_entry["sides"]
    assert "Random" in prf_entry["sides"]


def test_file_metadata_proof_resolves_theorem_with_export_rename(examples_client):
    """The theorem of PRFSecurity_implies_PRFSecurity_MultiKey.proof
    references PRFSecurity_MultiKey, which is the export name of the game."""
    c, examples_root = examples_client
    rel = "Proofs/PRF/PRFSecurity_implies_PRFSecurity_MultiKey.proof"
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
    assert theorem["name"] == "PRFSecurity_MultiKey"
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
    rel = "Proofs/PRG/TriplingPRG_PRGSecurity.proof"
    content = (examples_root / rel).read_text(encoding="utf-8")
    step_text = "PRGSecurity(T).Real against PRGSecurity(T).Adversary"
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
    rel = "Proofs/Group/DDHMultiChal_implies_HashedDDHMultiChal.proof"
    content = (examples_root / rel).read_text(encoding="utf-8")
    step_text = (
        "DDHMultiChal(G).Left compose R_DDH(G, n, H)"
        " against HashedDDHMultiChal(G, n, H).Adversary"
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
    rel = "Proofs/PRG/TriplingPRG_PRGSecurity.proof"
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


# A parse error in a file the checked file imports is reported with no
# position: the editor marks error_line/error_column in the checked file's
# own tab, and the message names the imported file. An error in the checked
# file keeps its position.

_GAME_POWER_IN_SIZE = """Game Left(Int k) {
    BitString<2 ^ k> Get() {
        BitString<2 ^ k> x <- BitString<2 ^ k>;
        return x;
    }
}
Game Right(Int k) {
    BitString<2 ^ k> Get() {
        BitString<2 ^ k> x <- BitString<2 ^ k>;
        return x;
    }
}
export as SizePow;
"""

_GAME_NON_PRODUCT_BINDING = """Game Left(Int k) {
    BitString<k> Get() {
        BitString<k> x <- BitString<k>;
        BitString<k> [a, b] = x;
        return a;
    }
}
Game Right(Int k) {
    BitString<k> Get() {
        BitString<k> x <- BitString<k>;
        return x;
    }
}
export as Destr;
"""

_GAME_WELL_FORMED = """Game Left(Int k) {
    BitString<k> Get() {
        BitString<k> x <- BitString<k>;
        return x;
    }
}
Game Right(Int k) {
    BitString<k> Get() {
        BitString<k> x <- BitString<k>;
        return x;
    }
}
export as Fine;
"""


def _proof_importing(file_name: str, game: str) -> str:
    return (
        f"import '{file_name}';\n"
        "proof:\n"
        "let:\n"
        "    Int kl;\n"
        "theorem:\n"
        f"    {game}(kl);\n"
        "games:\n"
        f"    {game}(kl).Left against {game}(kl).Adversary;\n"
        f"    {game}(kl).Right against {game}(kl).Adversary;\n"
    )


@pytest.fixture
def parse_error_client(tmp_path):
    (tmp_path / "SizePow.game").write_text(_GAME_POWER_IN_SIZE, encoding="utf-8")
    (tmp_path / "Destr.game").write_text(_GAME_NON_PRODUCT_BINDING, encoding="utf-8")
    (tmp_path / "Fine.game").write_text(_GAME_WELL_FORMED, encoding="utf-8")
    app, _observer = create_app(str(tmp_path), watch=False)
    app.testing = True
    with app.test_client() as c:
        yield c


def _post(client, endpoint: str, rel: str, content: str) -> dict:
    resp = client.post(
        endpoint,
        data=json.dumps({"path": rel, "content": content}),
        content_type="application/json",
        headers=POST_HEADERS,
    )
    assert resp.status_code == 200
    return resp.get_json()


@pytest.mark.parametrize("endpoint", ["/api/check", "/api/prove"])
@pytest.mark.parametrize(
    "imported, game, location",
    [
        pytest.param(
            "SizePow.game",
            "SizePow",
            "SizePow.game:2:16: parse error",
            id="syntax",
        ),
        pytest.param(
            "Destr.game", "Destr", "Destr.game:4:8: parse error", id="desugaring"
        ),
    ],
)
def test_import_parse_error_has_no_position(
    parse_error_client, endpoint, imported, game, location
):
    body = _post(
        parse_error_client,
        endpoint,
        "uses_import.proof",
        _proof_importing(imported, game),
    )
    assert body["success"] is False
    assert location in body["output"]
    assert "error_line" not in body
    assert "error_column" not in body


@pytest.mark.parametrize("endpoint", ["/api/check", "/api/prove"])
def test_own_parse_error_keeps_position(parse_error_client, endpoint):
    content = _proof_importing("Fine.game", "Fine").replace(
        "    Int kl;\n", "    Int kl = ;\n"
    )
    body = _post(parse_error_client, endpoint, "own_error.proof", content)
    assert body["success"] is False
    assert "own_error.proof:4:" in body["output"]
    assert body["error_line"] == 4
    assert "error_column" in body


@pytest.mark.parametrize("endpoint", ["/api/parse", "/api/check"])
def test_own_desugaring_error_keeps_position(parse_error_client, endpoint):
    body = _post(parse_error_client, endpoint, "Destr.game", _GAME_NON_PRODUCT_BINDING)
    assert body["success"] is False
    assert "Destr.game:4:8: parse error" in body["output"]
    assert (body["error_line"], body["error_column"]) == (4, 8)
