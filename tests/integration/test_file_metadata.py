"""Tests for the GET /api/file-metadata endpoint."""

import os

import pytest

from proof_frog.web_server import create_app


@pytest.fixture()
def client():
    """Flask test client rooted at the examples directory."""
    examples_dir = os.path.join(os.path.dirname(__file__), "..", "..", "examples")
    app, _observer = create_app(os.path.abspath(examples_dir), watch=False)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestPrimitiveMetadata:
    def test_basic_fields(self, client):
        resp = client.get("/api/file-metadata?path=Primitives/PRG.primitive")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["type"] == "primitive"
        assert data["name"] == "PRG"

    def test_parameters(self, client):
        resp = client.get("/api/file-metadata?path=Primitives/PRG.primitive")
        data = resp.get_json()
        names = [p["name"] for p in data["parameters"]]
        assert "lambda" in names
        assert "stretch" in names
        for p in data["parameters"]:
            assert "type" in p
            assert "name" in p

    def test_fields(self, client):
        resp = client.get("/api/file-metadata?path=Primitives/PRG.primitive")
        data = resp.get_json()
        field_names = [f["name"] for f in data["fields"]]
        assert "lambda" in field_names
        assert "stretch" in field_names

    def test_methods(self, client):
        resp = client.get("/api/file-metadata?path=Primitives/PRG.primitive")
        data = resp.get_json()
        assert isinstance(data["methods"], list)
        assert len(data["methods"]) >= 1
        assert "evaluate" in data["methods"][0]


class TestSchemeMetadata:
    def test_basic_fields(self, client):
        resp = client.get("/api/file-metadata?path=Schemes/SymEnc/OTP.scheme")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["type"] == "scheme"
        assert data["name"] == "OTP"
        assert data["primitive_name"] == "SymEnc"

    def test_parameters(self, client):
        resp = client.get("/api/file-metadata?path=Schemes/SymEnc/OTP.scheme")
        data = resp.get_json()
        assert len(data["parameters"]) >= 1
        names = [p["name"] for p in data["parameters"]]
        assert "lambda" in names

    def test_fields(self, client):
        resp = client.get("/api/file-metadata?path=Schemes/SymEnc/OTP.scheme")
        data = resp.get_json()
        field_names = [f["name"] for f in data["fields"]]
        assert "Key" in field_names
        assert "Message" in field_names
        assert "Ciphertext" in field_names

    def test_methods(self, client):
        resp = client.get("/api/file-metadata?path=Schemes/SymEnc/OTP.scheme")
        data = resp.get_json()
        method_strs = data["methods"]
        assert any("KeyGen" in m for m in method_strs)
        assert any("Enc" in m for m in method_strs)
        assert any("Dec" in m for m in method_strs)


class TestGameMetadata:
    def test_basic_fields(self, client):
        resp = client.get("/api/file-metadata?path=Games/PRG/Security.game")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["type"] == "game"
        assert data["export_name"] == "Security"

    def test_sides(self, client):
        resp = client.get("/api/file-metadata?path=Games/PRG/Security.game")
        data = resp.get_json()
        assert data["sides"] == ["Real", "Random"]

    def test_games_list(self, client):
        resp = client.get("/api/file-metadata?path=Games/PRG/Security.game")
        data = resp.get_json()
        assert len(data["games"]) == 2
        game_names = [g["name"] for g in data["games"]]
        assert "Real" in game_names
        assert "Random" in game_names

    def test_game_structure(self, client):
        resp = client.get("/api/file-metadata?path=Games/PRG/Security.game")
        data = resp.get_json()
        for g in data["games"]:
            assert "name" in g
            assert "parameters" in g
            assert "fields" in g
            assert "methods" in g
            assert isinstance(g["parameters"], list)
            assert isinstance(g["methods"], list)

    def test_game_parameters(self, client):
        resp = client.get("/api/file-metadata?path=Games/PRG/Security.game")
        data = resp.get_json()
        real_game = data["games"][0]
        assert len(real_game["parameters"]) >= 1
        assert real_game["parameters"][0]["name"] == "G"

    def test_game_methods(self, client):
        resp = client.get("/api/file-metadata?path=Games/PRG/Security.game")
        data = resp.get_json()
        real_game = data["games"][0]
        assert any("Query" in m for m in real_game["methods"])


class TestProofMetadata:
    def test_basic_fields(self, client):
        resp = client.get("/api/file-metadata?path=Book/2/2_13.proof")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["type"] == "proof"

    def test_lets(self, client):
        resp = client.get("/api/file-metadata?path=Book/2/2_13.proof")
        data = resp.get_json()
        assert isinstance(data["lets"], list)
        assert len(data["lets"]) >= 1

    def test_theorem(self, client):
        resp = client.get("/api/file-metadata?path=Book/2/2_13.proof")
        data = resp.get_json()
        assert isinstance(data["theorem"], str)
        assert len(data["theorem"]) > 0

    def test_steps(self, client):
        resp = client.get("/api/file-metadata?path=Book/2/2_13.proof")
        data = resp.get_json()
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) >= 2

    def test_assumptions(self, client):
        resp = client.get("/api/file-metadata?path=Book/2/2_13.proof")
        data = resp.get_json()
        assert isinstance(data["assumptions"], list)


class TestErrorCases:
    def test_nonexistent_file(self, client):
        resp = client.get("/api/file-metadata?path=nonexistent.primitive")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_invalid_path_traversal(self, client):
        resp = client.get("/api/file-metadata?path=../../etc/passwd")
        assert resp.status_code == 403
        data = resp.get_json()
        assert "error" in data

    def test_unsupported_extension(self, client):
        resp = client.get("/api/file-metadata?path=some_file.txt")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_missing_path(self, client):
        resp = client.get("/api/file-metadata")
        # Empty path resolves to base directory, which has no extension
        assert resp.status_code == 400

    def test_dotfile_rejected(self, client):
        resp = client.get("/api/file-metadata?path=.git/config")
        assert resp.status_code == 403
