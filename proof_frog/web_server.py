import copy
import io
import os
import re
import socket
import threading
import webbrowser
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

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
    except frog_parser.ParseError as e:
        return _strip_ansi(buf.getvalue()) + f"\n{e}", False
    except Exception as e:
        return _strip_ansi(buf.getvalue()) + f"\nError: {e}", False


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip(".")
    return frog_ast.FileType(extension)


def _capture_inline(file_path: str, step_index: int) -> tuple[str, str, bool]:
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
            for game in proof_file.helpers:
                engine.definition_namespace[game.name] = game
            for let in proof_file.lets:
                engine.proof_let_types.set(let.name, let.type)
                if isinstance(let.value, frog_ast.FuncCall) and isinstance(
                    let.value.func, frog_ast.Variable
                ):
                    definition = copy.deepcopy(
                        engine.definition_namespace[let.value.func.name]
                    )
                    if isinstance(definition, (frog_ast.Primitive, frog_ast.Scheme)):
                        engine.proof_namespace[let.name] = proof_engine.instantiate(
                            definition, let.value.args, engine.proof_namespace
                        )
                    else:
                        raise TypeError("Must instantiate either a Primitive or Scheme")
                else:
                    engine.proof_namespace[let.name] = copy.deepcopy(let.value)
            engine.get_method_lookup()

        if step_index < 0 or step_index >= len(proof_file.steps):
            return f"Step index {step_index} out of range (proof has {len(proof_file.steps)} steps)", "", False
        step = proof_file.steps[step_index]
        if not isinstance(step, frog_ast.Step):
            return "This step is an assumption, not a game step.", "", False

        suppress = io.StringIO()
        with redirect_stdout(suppress), redirect_stderr(suppress):
            game = engine._get_game_ast(step.challenger, step.reduction)
            canon = engine.canonicalize_game(copy.deepcopy(game))
        return str(game), str(canon), True
    except Exception as e:
        return _strip_ansi(buf.getvalue()) + f"\nError: {e}", "", False


def _capture_prove(file_path: str) -> tuple[str, bool, list[dict]]:
    buf = io.StringIO()
    engine = proof_engine.ProofEngine(False)
    proof_succeeded = False
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            proof_file = frog_parser.parse_proof_file(file_path)

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
                proof_succeeded = True
            except proof_engine.FailedProof:
                pass

        hop_results = [
            {"step_num": r.step_num, "valid": r.valid, "kind": r.kind}
            for r in engine.hop_results
            if r.depth == 0 and r.kind != "induction_rollover"
        ]
        return _strip_ansi(buf.getvalue()), proof_succeeded, hop_results
    except frog_parser.ParseError as e:
        return _strip_ansi(buf.getvalue()) + f"\n{e}", False, []
    except Exception as e:
        return _strip_ansi(buf.getvalue()) + f"\nError: {e}", False, []


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

    @app.route("/prooffrog.png")
    def logo():  # type: ignore[return-value]
        return send_file(static_dir / "prooffrog.png")

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
        output, success, hop_results = _capture_prove(str(abs_path))
        return jsonify({"output": output, "success": success, "hop_results": hop_results})

    @app.route("/api/inline", methods=["POST"])
    def run_inline():  # type: ignore[return-value]
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        step_index = data.get("step_index", 0)
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        output, canonical, success = _capture_inline(str(abs_path), step_index)
        return jsonify({"output": output, "canonical": canonical, "success": success})

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
