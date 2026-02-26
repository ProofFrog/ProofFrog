import io
import os
import re
import socket
import threading
import webbrowser
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from antlr4 import error
from flask import Flask, request, jsonify, send_file

from . import frog_parser, frog_ast, proof_engine

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


def _find_free_port(start: int = 5173) -> int:
    port = start
    while port < start + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    raise RuntimeError("Could not find a free port")


def _safe_path(base: str, rel: str) -> Path | None:
    try:
        base_resolved = Path(base).resolve()
        abs_path = (base_resolved / rel).resolve()
        if not str(abs_path).startswith(str(base_resolved)):
            return None
        return abs_path
    except Exception:
        return None


def _capture_parse(file_path: str) -> tuple[str, bool]:
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            root = frog_parser.parse_file(file_path)
            print(root)
        return _strip_ansi(buf.getvalue()), True
    except ValueError as e:
        return _strip_ansi(buf.getvalue()) + f"\nError: {e}", False
    except error.Errors.ParseCancellationException as e:
        return _strip_ansi(buf.getvalue()) + f"\nParse error: {e}", False
    except Exception as e:
        return _strip_ansi(buf.getvalue()) + f"\nError: {e}", False


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip(".")
    return frog_ast.FileType(extension)


def _capture_prove(file_path: str) -> tuple[str, bool]:
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            proof_file = frog_parser.parse_proof_file(file_path)
            engine = proof_engine.ProofEngine(False)

            for imp in proof_file.imports:
                file_type = _get_file_type(imp.filename)
                match file_type:
                    case frog_ast.FileType.PRIMITIVE:
                        root = frog_parser.parse_primitive_file(imp.filename)
                    case frog_ast.FileType.SCHEME:
                        root = frog_parser.parse_scheme_file(imp.filename)
                    case frog_ast.FileType.GAME:
                        root = frog_parser.parse_game_file(imp.filename)
                    case _:
                        raise TypeError(f"Cannot import {file_type}")
                name = imp.rename if imp.rename else root.get_export_name()
                engine.add_definition(name, root)

            try:
                engine.prove(proof_file)
            except proof_engine.FailedProof:
                return _strip_ansi(buf.getvalue()), False

        return _strip_ansi(buf.getvalue()), True
    except error.Errors.ParseCancellationException as e:
        return _strip_ansi(buf.getvalue()) + f"\nParse error: {e}", False
    except Exception as e:
        return _strip_ansi(buf.getvalue()) + f"\nError: {e}", False


def _build_tree(path: Path, base: Path) -> dict:
    if path.is_dir():
        children = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        return {
            "name": path.name,
            "path": str(path.relative_to(base)),
            "type": "directory",
            "children": [
                _build_tree(child, base)
                for child in children
                if not child.name.startswith(".")
            ],
        }
    return {
        "name": path.name,
        "path": str(path.relative_to(base)),
        "type": "file",
    }


def create_app(directory: str) -> Flask:
    app = Flask(__name__)
    static_dir = Path(__file__).parent / "web"

    @app.route("/")
    def index():  # type: ignore[return-value]
        return send_file(static_dir / "index.html")

    @app.route("/api/files")
    def list_files():  # type: ignore[return-value]
        tree = _build_tree(Path(directory), Path(directory))
        return jsonify(tree)

    @app.route("/api/file", methods=["GET"])
    def get_file():  # type: ignore[return-value]
        rel_path = request.args.get("path", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        try:
            content = abs_path.read_text(encoding="utf-8")
            return jsonify({"content": content})
        except FileNotFoundError:
            return jsonify({"error": "File not found"}), 404

    @app.route("/api/file", methods=["PUT"])
    def save_file():  # type: ignore[return-value]
        rel_path = request.args.get("path", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        data = request.get_json()
        content = data.get("content", "") if data else ""
        abs_path.write_text(content, encoding="utf-8")
        return jsonify({"success": True})

    @app.route("/api/parse", methods=["POST"])
    def run_parse():  # type: ignore[return-value]
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        output, success = _capture_parse(str(abs_path))
        return jsonify({"output": output, "success": success})

    @app.route("/api/prove", methods=["POST"])
    def run_prove():  # type: ignore[return-value]
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        output, success = _capture_prove(str(abs_path))
        return jsonify({"output": output, "success": success})

    return app


def start_server(directory: str) -> None:
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a directory", flush=True)
        return

    app = create_app(directory)
    port = _find_free_port(5173)
    url = f"http://127.0.0.1:{port}"

    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    print(f"ProofFrog Web UI: {url}")
    print(f"Working directory: {directory}")
    print("Press Ctrl+C to stop.")

    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app.run(host="127.0.0.1", port=port, debug=False)
