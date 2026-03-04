import copy
import io
import logging
import os
import re
import socket
import threading
import webbrowser
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Any

from flask import Flask, request, jsonify, send_file, send_from_directory

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
        if not abs_path.is_relative_to(base_resolved):
            return None
        # Block access to dotfiles/dotdirs (e.g. .git)
        rel_to_base = abs_path.relative_to(base_resolved)
        if any(part.startswith(".") for part in rel_to_base.parts):
            return None
        return abs_path
    except Exception:  # pylint: disable=broad-exception-caught
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
    except (frog_parser.ParseError, FileNotFoundError) as e:
        return _strip_ansi(buf.getvalue()) + f"\n{e}", False
    except Exception as e:  # pylint: disable=broad-exception-caught
        return _strip_ansi(buf.getvalue()) + f"\nError: {e}", False


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip(".")
    return frog_ast.FileType(extension)


def _build_minimal_proof(proof_text: str, step_text: str) -> str | None:
    """Build a minimal parseable proof containing only one game step.

    Extracts imports, intermediate Game definitions (skipping Reduction stubs),
    the let:/assume:/theorem: blocks from *proof_text*, then wraps *step_text*
    as the only step (listed twice so the grammar's two-game requirement is met).

    Returns the minimal proof as a string, or None if a theorem could not be
    extracted from *proof_text*.
    """
    # Import lines
    import_lines = "\n".join(
        re.findall(r"^import\s+'[^']+'(?:\s+as\s+\w+)?\s*;", proof_text, re.MULTILINE)
    )

    # Intermediate Game blocks (skip Reduction blocks)
    game_defs: list[str] = []
    for match in re.finditer(r"^Game\s+", proof_text, re.MULTILINE):
        start = match.start()
        brace_start = proof_text.find("{", start)
        if brace_start == -1:
            continue
        depth = 0
        for i in range(brace_start, len(proof_text)):
            if proof_text[i] == "{":
                depth += 1
            elif proof_text[i] == "}":
                depth -= 1
                if depth == 0:
                    game_defs.append(proof_text[start : i + 1])
                    break

    # let: block
    let_match = re.search(
        r"\blet\s*:\s*((?:.|\n)*?)(?=\bassume\b|\btheorem\b|\bgames\b)", proof_text
    )
    let_block = "let:\n" + let_match.group(1).rstrip() if let_match else ""

    # assume: block
    assume_match = re.search(
        r"\bassume\s*:\s*((?:.|\n)*?)(?=\btheorem\b|\bgames\b)", proof_text
    )
    assume_block = "assume:\n" + assume_match.group(1).rstrip() if assume_match else ""

    # theorem: (required)
    theorem_match = re.search(r"\btheorem\s*:\s*((?:.|\n)*?);", proof_text)
    if not theorem_match:
        return None
    theorem_block = "theorem:\n    " + theorem_match.group(1).strip() + ";"

    parts: list[str] = []
    if import_lines:
        parts.append(import_lines)
    parts.extend(game_defs)
    parts.append("proof:")
    if let_block:
        parts.append(let_block)
    if assume_block:
        parts.append(assume_block)
    parts.append(theorem_block)
    parts.append(f"games:\n    {step_text};\n    {step_text};")
    return "\n\n".join(parts) + "\n"


def _capture_inline(
    file_path: str,
    step_index: int,
    allowed_root: str | None = None,
) -> tuple[str, str, bool, bool, str, str, str]:
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            proof_file = frog_parser.parse_proof_file(file_path)
            engine = proof_engine.ProofEngine(False)
            for imp in proof_file.imports:
                imp_path = frog_parser.resolve_import_path(
                    imp.filename, file_path, allowed_root=allowed_root
                )
                file_type = _get_file_type(imp_path)
                root: frog_ast.Primitive | frog_ast.Scheme | frog_ast.GameFile
                match file_type:
                    case frog_ast.FileType.PRIMITIVE:
                        root = frog_parser.parse_primitive_file(imp_path)
                    case frog_ast.FileType.SCHEME:
                        root = frog_parser.parse_scheme_file(imp_path)
                    case frog_ast.FileType.GAME:
                        root = frog_parser.parse_game_file(imp_path)
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
            return (
                f"Step index {step_index} out of range (proof has {len(proof_file.steps)} steps)",
                "",
                False,
                False,
                "",
                "",
                "",
            )
        step = proof_file.steps[step_index]
        if not isinstance(step, frog_ast.Step):
            return (
                "This step is an assumption, not a game step.",
                "",
                False,
                False,
                "",
                "",
                "",
            )

        suppress = io.StringIO()
        with redirect_stdout(suppress), redirect_stderr(suppress):
            # pylint: disable=protected-access
            game = engine._get_game_ast(step.challenger, step.reduction)
            # pylint: enable=protected-access
            canon = engine.canonicalize_game(copy.deepcopy(game))

        has_reduction = step.reduction is not None
        reduction_str = ""
        challenger_str = ""
        scheme_str = ""
        if has_reduction:
            assert step.reduction is not None
            suppress2 = io.StringIO()
            with redirect_stdout(suppress2), redirect_stderr(suppress2):
                # pylint: disable=protected-access
                reduction_game = engine._get_game_ast(step.reduction)
                challenger_only = engine._get_game_ast(step.challenger)
                # pylint: enable=protected-access
            reduction_str = str(reduction_game)
            challenger_str = str(challenger_only)

            # Find the underlying scheme from the challenger's args
            challenger_args = (
                step.challenger.game.args
                if isinstance(step.challenger, frog_ast.ConcreteGame)
                else step.challenger.args
            )
            for arg in challenger_args:
                if (
                    isinstance(arg, frog_ast.Variable)
                    and arg.name in engine.proof_namespace
                ):
                    candidate = engine.proof_namespace[arg.name]
                    if isinstance(candidate, frog_ast.Scheme):
                        scheme_str = str(candidate)
                        break

        return (
            str(game),
            str(canon),
            True,
            has_reduction,
            reduction_str,
            challenger_str,
            scheme_str,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        return (
            _strip_ansi(buf.getvalue()) + f"\nError: {e}",
            "",
            False,
            False,
            "",
            "",
            "",
        )


def _capture_prove(
    file_path: str, allowed_root: str | None = None
) -> tuple[str, bool, list[dict[str, object]]]:
    buf = io.StringIO()
    engine = proof_engine.ProofEngine(False)
    proof_succeeded = False
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            proof_file = frog_parser.parse_proof_file(file_path)

            for imp in proof_file.imports:
                imp_path = frog_parser.resolve_import_path(
                    imp.filename, file_path, allowed_root=allowed_root
                )
                file_type = _get_file_type(imp_path)
                root2: frog_ast.Primitive | frog_ast.Scheme | frog_ast.GameFile
                match file_type:
                    case frog_ast.FileType.PRIMITIVE:
                        root2 = frog_parser.parse_primitive_file(imp_path)
                    case frog_ast.FileType.SCHEME:
                        root2 = frog_parser.parse_scheme_file(imp_path)
                    case frog_ast.FileType.GAME:
                        root2 = frog_parser.parse_game_file(imp_path)
                    case _:
                        raise TypeError(f"Cannot import {file_type}")
                name = imp.rename if imp.rename else root2.get_export_name()
                engine.add_definition(name, root2)

            try:
                engine.prove(proof_file)
                proof_succeeded = True
            except proof_engine.FailedProof:
                pass

        hop_results: list[dict[str, object]] = [
            {"step_num": r.step_num, "valid": r.valid, "kind": r.kind}
            for r in engine.hop_results
            if r.depth == 0 and r.kind != "induction_rollover"
        ]
        return _strip_ansi(buf.getvalue()), proof_succeeded, hop_results
    except (frog_parser.ParseError, FileNotFoundError) as e:
        return _strip_ansi(buf.getvalue()) + f"\n{e}", False, []
    except Exception as e:  # pylint: disable=broad-exception-caught
        return _strip_ansi(buf.getvalue()) + f"\nError: {e}", False, []


def _build_tree(path: Path, base: Path) -> dict[str, object]:
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
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
    static_dir = Path(__file__).parent / "web"

    @app.before_request
    def _check_origin() -> Any:
        if request.method in ("POST", "PUT", "DELETE"):
            origin = request.headers.get("Origin", "")
            if not origin:
                return jsonify({"error": "Missing Origin header"}), 403
            if not origin.startswith(f"http://127.0.0.1:{request.host.split(':')[-1]}"):
                return jsonify({"error": "Origin not allowed"}), 403
        return None

    @app.after_request
    def _add_security_headers(response: Any) -> Any:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdnjs.cloudflare.com; "
            "style-src 'self' https://cdnjs.cloudflare.com; "
            "img-src 'self'; "
            "connect-src 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.route("/")
    def index() -> Any:
        return send_file(static_dir / "index.html")

    @app.route("/prooffrog.png")
    def logo() -> Any:
        return send_file(static_dir / "prooffrog.png")

    @app.route("/static/<path:filename>")
    def serve_static(filename: str) -> Any:
        return send_from_directory(str(static_dir), filename)

    @app.route("/api/files")
    def list_files() -> Any:
        tree = _build_tree(Path(directory), Path(directory))
        return jsonify(tree)

    @app.route("/api/file", methods=["GET"])
    def get_file() -> Any:
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
    def save_file() -> Any:
        rel_path = request.args.get("path", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        data = request.get_json()
        content = data.get("content", "") if data else ""
        abs_path.write_text(content, encoding="utf-8")
        return jsonify({"success": True})

    @app.route("/api/parse", methods=["POST"])
    def run_parse() -> Any:
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
    def run_prove() -> Any:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        output, success, hop_results = _capture_prove(
            str(abs_path), allowed_root=directory
        )
        return jsonify(
            {"output": output, "success": success, "hop_results": hop_results}
        )

    @app.route("/api/inline", methods=["POST"])
    def run_inline() -> Any:
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
        output, canonical, success, has_reduction, reduction, challenger, scheme = (
            _capture_inline(str(abs_path), step_index, allowed_root=directory)
        )
        return jsonify(
            {
                "output": output,
                "canonical": canonical,
                "success": success,
                "has_reduction": has_reduction,
                "reduction": reduction,
                "challenger": challenger,
                "scheme": scheme,
            }
        )

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

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app.run(host="127.0.0.1", port=port, debug=False)
