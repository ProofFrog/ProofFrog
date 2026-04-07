import atexit
import copy
import io
import json
import logging
import os
import queue
import re
import socket
import tempfile
import threading
import time
import webbrowser
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Any

from sympy import Symbol
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from flask import Flask, request, jsonify, send_file, send_from_directory, Response

from . import frog_parser, frog_ast, proof_engine, semantic_analysis
from . import describe as describe_module

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


def _capture_parse(
    file_path: str,
) -> tuple[str, bool, int | None, int | None]:
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            root = frog_parser.parse_file(file_path)
            print(root)
        return _strip_ansi(buf.getvalue()), True, None, None
    except ValueError as e:
        return _strip_ansi(buf.getvalue()) + f"\nError: {e}", False, None, None
    except frog_parser.ParseError as e:
        line = e.line if e.line >= 0 else None
        col = e.column if e.column >= 0 else None
        return _strip_ansi(buf.getvalue()) + f"\n{e}", False, line, col
    except FileNotFoundError as e:
        return _strip_ansi(buf.getvalue()) + f"\n{e}", False, None, None
    except Exception as e:  # pylint: disable=broad-exception-caught
        return _strip_ansi(buf.getvalue()) + f"\nError: {e}", False, None, None


def _capture_check(
    file_path: str, allowed_root: str | None = None
) -> tuple[str, bool, int | None, int | None]:
    buf = io.StringIO()
    try:
        root = frog_parser.parse_file(file_path)
        with redirect_stdout(buf), redirect_stderr(buf):
            semantic_analysis.check_well_formed(
                root, file_path, allowed_root=allowed_root
            )
        return f"{file_path} is well-formed.", True, None, None
    except frog_parser.ParseError as e:
        line = e.line if e.line >= 0 else None
        col = e.column if e.column >= 0 else None
        return str(e), False, line, col
    except FileNotFoundError as e:
        return str(e), False, None, None
    except semantic_analysis.FailedTypeCheck:
        msg = _strip_ansi(buf.getvalue()) or "Type check failed."
        return msg, False, None, None
    except Exception as e:  # pylint: disable=broad-exception-caught
        return f"Error: {e}", False, None, None


def _capture_describe(file_path: str) -> tuple[str, bool]:
    try:
        return describe_module.describe_file(file_path), True
    except (ValueError, frog_parser.ParseError, FileNotFoundError) as e:
        return str(e), False
    except Exception as e:  # pylint: disable=broad-exception-caught
        return f"Error: {e}", False


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip(".")
    return frog_ast.FileType(extension)


def _build_minimal_proof(proof_text: str, step_text: str) -> str | None:
    """Build a minimal parseable proof containing only one game step.

    Extracts imports, intermediate Game definitions, Reduction definitions,
    and the let:/assume:/theorem: blocks from *proof_text*, then wraps
    *step_text* as the only step (listed twice so the grammar's two-game
    requirement is met).

    Returns the minimal proof as a string, or None if a theorem could not be
    extracted from *proof_text*.
    """
    # Import lines
    import_lines = "\n".join(
        re.findall(r"^import\s+'[^']+'(?:\s+as\s+\w+)?\s*;", proof_text, re.MULTILINE)
    )

    # Top-level Game and Reduction blocks. We must include Reductions because
    # *step_text* may reference them via `compose ... compose Reduction(...)`.
    game_defs: list[str] = []
    for match in re.finditer(r"^(Game|Reduction)\s+", proof_text, re.MULTILINE):
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


def _setup_engine_for_proof(
    file_path: str, allowed_root: str | None = None
) -> tuple[proof_engine.ProofEngine, frog_ast.ProofFile]:
    """Parse a proof file, set up an engine with its namespace, and return both.

    Caller is responsible for suppressing stdout/stderr if needed.
    """
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
            definition = copy.deepcopy(engine.definition_namespace[let.value.func.name])
            if isinstance(definition, (frog_ast.Primitive, frog_ast.Scheme)):
                engine.proof_namespace[let.name] = proof_engine.instantiate(
                    definition, let.value.args, engine.proof_namespace
                )
            else:
                raise TypeError("Must instantiate either a Primitive or Scheme")
        else:
            engine.proof_namespace[let.name] = copy.deepcopy(let.value)
            if isinstance(let.type, frog_ast.IntType):
                if let.value is not None:
                    engine.variables[let.name] = let.value
                else:
                    engine.variables[let.name] = Symbol(let.name)  # type: ignore
    if proof_file.max_calls is not None:
        if isinstance(proof_file.max_calls, frog_ast.Integer):
            engine.max_calls = proof_file.max_calls.num
        elif isinstance(proof_file.max_calls, frog_ast.Variable):
            val = engine.variables.get(proof_file.max_calls.name)
            if isinstance(val, frog_ast.Integer):
                engine.max_calls = val.num
    engine.get_method_lookup()
    return engine, proof_file


def _resolve_game_reference(
    engine: proof_engine.ProofEngine,
    parameterized_game: frog_ast.ParameterizedGame,
) -> dict[str, Any]:
    """Resolve a ParameterizedGame against the engine's import namespace.

    Returns a dict with `name` (str), `args` (list[str]), and `sides`
    (list[str]). `sides` is empty when the game cannot be resolved (e.g. the
    name is not in the namespace, or it resolves to something other than a
    GameFile). The lookup respects `import '...' as Alias;` and `export as
    Name;` because both end up keyed under their final name in
    `engine.definition_namespace`.
    """
    name = parameterized_game.name
    args = [str(a) for a in parameterized_game.args]
    sides: list[str] = []
    resolved = engine.definition_namespace.get(name)
    if isinstance(resolved, frog_ast.GameFile):
        sides = [g.name for g in resolved.games]
    return {"name": name, "args": args, "sides": sides}


def _resolve_step_game(
    engine: proof_engine.ProofEngine,
    proof_file: frog_ast.ProofFile,
    step_index: int,
) -> tuple[frog_ast.Game | None, str]:
    """Get the inlined game AST for a proof step.  Returns (game, error)."""
    if step_index < 0 or step_index >= len(proof_file.steps):
        return None, (
            f"Step index {step_index} out of range "
            f"(proof has {len(proof_file.steps)} steps)"
        )
    step = proof_file.steps[step_index]
    if not isinstance(step, frog_ast.Step):
        return None, "This step is an assumption, not a game step."
    suppress = io.StringIO()
    with redirect_stdout(suppress), redirect_stderr(suppress):
        # pylint: disable=protected-access
        game = engine._get_game_ast(step.challenger, step.reduction)
        # pylint: enable=protected-access
    return game, ""


def _capture_inline(
    file_path: str,
    step_index: int,
    allowed_root: str | None = None,
) -> tuple[str, str, bool, bool, str, str, str]:
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            engine, proof_file = _setup_engine_for_proof(file_path, allowed_root)

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


# ---------------------------------------------------------------------------
# Canonicalization debugging capture functions
# ---------------------------------------------------------------------------


def _capture_canonicalization_trace(
    file_path: str, step_index: int, allowed_root: str | None = None
) -> dict[str, Any]:
    """Return a trace of which transforms fired per iteration for a step."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            engine, proof_file = _setup_engine_for_proof(file_path, allowed_root)
        game, err = _resolve_step_game(engine, proof_file, step_index)
        if game is None:
            return {"success": False, "error": err}
        suppress = io.StringIO()
        with redirect_stdout(suppress), redirect_stderr(suppress):
            _canon, trace = engine.canonicalize_game_with_trace(copy.deepcopy(game))
        trace["success"] = True
        return trace
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "success": False,
            "error": _strip_ansi(buf.getvalue()) + f"\nError: {e}",
        }


def _capture_step_after_transform(
    file_path: str,
    step_index: int,
    transform_name: str,
    allowed_root: str | None = None,
) -> dict[str, Any]:
    """Return game AST after applying transforms up to the named one."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            engine, proof_file = _setup_engine_for_proof(file_path, allowed_root)
        game, err = _resolve_step_game(engine, proof_file, step_index)
        if game is None:
            return {"success": False, "error": err}
        suppress = io.StringIO()
        with redirect_stdout(suppress), redirect_stderr(suppress):
            result_game, changed, available = engine.canonicalize_until_transform(
                copy.deepcopy(game), transform_name
            )
        if transform_name not in available:
            return {
                "success": False,
                "error": f"Unknown transform '{transform_name}'",
                "available_transforms": available,
            }
        return {
            "success": True,
            "output": str(result_game),
            "transform_applied": changed,
            "available_transforms": available,
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "success": False,
            "error": _strip_ansi(buf.getvalue()) + f"\nError: {e}",
        }


def _capture_prove(
    file_path: str,
    allowed_root: str | None = None,
    verbosity: proof_engine.Verbosity = proof_engine.Verbosity.QUIET,
    skip_lemmas: bool = False,
) -> tuple[str, bool, list[dict[str, object]], bool, int | None, int | None]:
    buf = io.StringIO()
    engine = proof_engine.ProofEngine(verbosity, skip_lemmas=skip_lemmas)
    proof_succeeded = False
    has_induction = False
    try:
        proof_file = frog_parser.parse_proof_file(file_path)
        has_induction = any(
            isinstance(step, frog_ast.Induction) for step in proof_file.steps
        )

        # Run semantic analysis before proof verification
        check_output, check_ok, check_err_line, check_err_col = _capture_check(
            file_path, allowed_root=allowed_root
        )
        if not check_ok:
            return (
                check_output,
                False,
                [],
                has_induction,
                check_err_line,
                check_err_col,
            )

        with redirect_stdout(buf), redirect_stderr(buf):
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
                engine.prove(proof_file, file_path)
                proof_succeeded = True
            except proof_engine.FailedProof:
                pass

        hop_results: list[dict[str, object]] = [
            {
                "step_num": r.step_num,
                "valid": r.valid,
                "kind": r.kind,
                "current_desc": r.current_desc,
                "next_desc": r.next_desc,
                "failure_detail": r.failure_detail,
                "diagnosis": proof_engine.serialize_diagnosis(r.diagnosis),
            }
            for r in engine.hop_results
            if r.depth == 0 and r.kind != "induction_rollover"
        ]
        return (
            _strip_ansi(buf.getvalue()),
            proof_succeeded,
            hop_results,
            has_induction,
            None,
            None,
        )
    except frog_parser.ParseError as e:
        line = e.line if e.line >= 0 else None
        col = e.column if e.column >= 0 else None
        return (
            _strip_ansi(buf.getvalue()) + f"\n{e}",
            False,
            [],
            False,
            line,
            col,
        )
    except FileNotFoundError as e:
        return (
            _strip_ansi(buf.getvalue()) + f"\n{e}",
            False,
            [],
            False,
            None,
            None,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        return (
            _strip_ansi(buf.getvalue()) + f"\nError: {e}",
            False,
            [],
            False,
            None,
            None,
        )


_IGNORED_DIRS = {"node_modules", "__pycache__", ".venv", "venv"}


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
                if not child.name.startswith(".") and child.name not in _IGNORED_DIRS
            ],
        }
    return {
        "name": path.name,
        "path": str(path.relative_to(base)),
        "type": "file",
    }


_WATCHED_EXTENSIONS = {".primitive", ".scheme", ".game", ".proof", ".md"}
_DEBOUNCE_SECONDS = 0.3


class _FileEventBroker:
    """Thread-safe broker that distributes filesystem events to SSE subscribers."""

    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[dict[str, str]]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[dict[str, str]]:
        q: queue.Queue[dict[str, str]] = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[dict[str, str]]) -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def publish(self, event: dict[str, str]) -> None:
        with self._lock:
            for q in self._subscribers:
                q.put(event)


class _FrogFileHandler(FileSystemEventHandler):
    """Debounced handler that publishes file change events to a broker."""

    def __init__(self, broker: _FileEventBroker, base: Path) -> None:
        super().__init__()
        self._broker = broker
        self._base = base
        self._last_events: dict[str, float] = {}
        self._lock = threading.Lock()

    def _should_handle(self, path_str: str, *, check_extension: bool = True) -> bool:
        p = Path(path_str)
        if check_extension and p.suffix not in _WATCHED_EXTENSIONS:
            return False
        try:
            rel = p.relative_to(self._base)
        except ValueError:
            return False
        return not any(part.startswith(".") for part in rel.parts)

    def _debounced_publish(self, event_type: str, src_path: str) -> None:
        now = time.monotonic()
        key = f"{event_type}:{src_path}"
        with self._lock:
            last = self._last_events.get(key, 0.0)
            if now - last < _DEBOUNCE_SECONDS:
                return
            self._last_events[key] = now
        try:
            rel = str(Path(src_path).relative_to(self._base))
        except ValueError:
            return
        self._broker.publish({"type": event_type, "path": rel})

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._should_handle(
            str(event.src_path), check_extension=False
        ):
            self._debounced_publish("file_changed", str(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._should_handle(str(event.src_path)):
            self._debounced_publish("file_created", str(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._should_handle(str(event.src_path)):
            self._debounced_publish("file_deleted", str(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        src = str(event.src_path)
        dest = str(getattr(event, "dest_path", ""))
        if not event.is_directory:
            if self._should_handle(src):
                self._debounced_publish("file_deleted", src)
            if dest and self._should_handle(dest):
                self._debounced_publish("file_created", dest)


def create_app(directory: str, *, watch: bool = True) -> tuple[Flask, Any]:
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
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
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

    @app.route("/api/version")
    def api_version() -> Any:
        # pylint: disable=import-outside-toplevel
        from importlib.metadata import version as pkg_version

        return jsonify({"version": pkg_version("proof_frog")})

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

    @app.route("/api/file", methods=["POST"])
    def create_file() -> Any:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        if abs_path.exists():
            return jsonify({"error": "File already exists"}), 409
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text("", encoding="utf-8")
        return jsonify({"success": True})

    @app.route("/api/directories")
    def list_directories() -> Any:
        dirs: list[str] = [""]
        base = Path(directory)
        for dirpath, dirnames, _ in os.walk(base):
            dirnames[:] = [
                d for d in dirnames if not d.startswith(".") and d not in _IGNORED_DIRS
            ]
            dirnames.sort(key=str.lower)
            p = Path(dirpath)
            if p != base:
                dirs.append(str(p.relative_to(base)))
        dirs.sort(key=str.lower)
        return jsonify(dirs)

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
        output, success, error_line, error_column = _capture_parse(str(abs_path))
        resp: dict[str, object] = {"output": output, "success": success}
        if error_line is not None:
            resp["error_line"] = error_line
        if error_column is not None:
            resp["error_column"] = error_column
        return jsonify(resp)

    @app.route("/api/check", methods=["POST"])
    def run_check() -> Any:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        output, success, error_line, error_column = _capture_check(
            str(abs_path), allowed_root=directory
        )
        resp: dict[str, object] = {"output": output, "success": success}
        if error_line is not None:
            resp["error_line"] = error_line
        if error_column is not None:
            resp["error_column"] = error_column
        return jsonify(resp)

    @app.route("/api/prove", methods=["POST"])
    def run_prove() -> Any:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        verbosity_val = data.get("verbosity", 0)
        verbosity = proof_engine.Verbosity(
            max(0, min(int(verbosity_val), 2))
            if isinstance(verbosity_val, (int, float))
            else 0
        )
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        output, success, hop_results, has_induction, error_line, error_column = (
            _capture_prove(str(abs_path), allowed_root=directory, verbosity=verbosity)
        )
        prove_resp: dict[str, object] = {
            "output": output,
            "success": success,
            "hop_results": hop_results,
            "has_induction": has_induction,
        }
        if error_line is not None:
            prove_resp["error_line"] = error_line
        if error_column is not None:
            prove_resp["error_column"] = error_column
        return jsonify(prove_resp)

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

    @app.route("/api/describe", methods=["POST"])
    def run_describe() -> Any:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        output, success = _capture_describe(str(abs_path))
        return jsonify({"output": output, "success": success})

    @app.route("/api/inlined-game", methods=["POST"])
    def run_inlined_game() -> Any:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        step_text = data.get("step_text", "")
        if not isinstance(step_text, str) or not step_text.strip():
            return jsonify({"error": "Missing or empty step_text"}), 400
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        try:
            abs_path.write_text(content, encoding="utf-8")
            minimal = _build_minimal_proof(content, step_text)
            if minimal is None:
                return (
                    jsonify(
                        {"error": "Could not extract theorem: block from proof file."}
                    ),
                    400,
                )
            # Dot-prefixed name so the file watcher ignores this transient
            # file (otherwise its create + delete would cause the file tree
            # in connected web clients to refresh and lose expansion state).
            fd, tmp_path = tempfile.mkstemp(
                prefix=".inlinedgame_",
                suffix=".proof",
                dir=os.path.dirname(str(abs_path)),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(minimal)
                (
                    output,
                    canonical,
                    success,
                    has_reduction,
                    reduction,
                    challenger,
                    scheme,
                ) = _capture_inline(tmp_path, 0, allowed_root=directory)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
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
        except Exception as e:  # pylint: disable=broad-exception-caught
            return jsonify({"error": f"Error: {e}"}), 400

    def _file_metadata_response(abs_path: Path) -> Any:
        file_path_str = str(abs_path)
        try:
            file_type = _get_file_type(file_path_str)
        except ValueError:
            return jsonify({"error": "Unsupported file type"}), 400

        def _params(params: list[frog_ast.Parameter]) -> list[dict[str, str]]:
            return [{"type": str(p.type), "name": p.name} for p in params]

        def _fields(fields: list[frog_ast.Field]) -> list[dict[str, str]]:
            return [{"type": str(f.type), "name": f.name} for f in fields]

        try:
            result: dict[str, object]
            if file_type == frog_ast.FileType.PRIMITIVE:
                prim = frog_parser.parse_primitive_file(file_path_str)
                result = {
                    "type": "primitive",
                    "name": prim.name,
                    "parameters": _params(prim.parameters),
                    "fields": _fields(prim.fields),
                    "methods": [str(m) for m in prim.methods],
                }
            elif file_type == frog_ast.FileType.SCHEME:
                scheme = frog_parser.parse_scheme_file(file_path_str)
                result = {
                    "type": "scheme",
                    "name": scheme.name,
                    "parameters": _params(scheme.parameters),
                    "primitive_name": scheme.primitive_name,
                    "fields": _fields(scheme.fields),
                    "methods": [str(m.signature) for m in scheme.methods],
                }
            elif file_type == frog_ast.FileType.GAME:
                game_file = frog_parser.parse_game_file(file_path_str)
                result = {
                    "type": "game",
                    "export_name": game_file.name,
                    "sides": [g.name for g in game_file.games],
                    "games": [
                        {
                            "name": g.name,
                            "parameters": _params(g.parameters),
                            "fields": _fields(g.fields),
                            "methods": [str(m.signature) for m in g.methods],
                        }
                        for g in game_file.games
                    ],
                }
            elif file_type == frog_ast.FileType.PROOF:
                proof_file = frog_parser.parse_proof_file(file_path_str)
                # Try to set up the engine to resolve assumption/theorem game
                # references through the proof's import namespace. This handles
                # `import '...' as Alias;` clauses and `export as Name;` cases
                # uniformly. If engine setup fails (broken imports, missing
                # dependencies, etc.) we still return the string-only metadata.
                assumption_details: list[dict[str, Any]] = []
                theorem_details: dict[str, Any] | None = None
                try:
                    suppress = io.StringIO()
                    with redirect_stdout(suppress), redirect_stderr(suppress):
                        engine, _ = _setup_engine_for_proof(
                            file_path_str, allowed_root=directory
                        )
                    for assumption in proof_file.assumptions:
                        assumption_details.append(
                            _resolve_game_reference(engine, assumption)
                        )
                    if proof_file.theorem is not None:
                        theorem_details = _resolve_game_reference(
                            engine, proof_file.theorem
                        )
                except Exception:  # pylint: disable=broad-exception-caught
                    # Leave details empty/None — caller still gets string forms.
                    pass
                # Top-level Reduction declarations: name + formal parameters.
                # The Insert Reduction Hop wizard uses this to populate the
                # reduction dropdown and pre-fill argument placeholders.
                reductions: list[dict[str, Any]] = []
                for helper in proof_file.helpers:
                    if isinstance(helper, frog_ast.Reduction):
                        reductions.append(
                            {
                                "name": helper.name,
                                "parameters": _params(helper.parameters),
                            }
                        )
                result = {
                    "type": "proof",
                    "lets": [str(let) for let in proof_file.lets],
                    "assumptions": [str(a) for a in proof_file.assumptions],
                    "assumption_details": assumption_details,
                    "theorem": str(proof_file.theorem),
                    "theorem_details": theorem_details,
                    "reductions": reductions,
                    "steps": [str(s) for s in proof_file.steps],
                }
            else:
                return jsonify({"error": "Unsupported file type"}), 400
            return jsonify(result)
        except (
            frog_parser.ParseError,
            FileNotFoundError,
            semantic_analysis.FailedTypeCheck,
        ) as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:  # pylint: disable=broad-exception-caught
            return jsonify({"error": f"Error: {e}"}), 400

    @app.route("/api/file-metadata")
    def file_metadata() -> Any:
        rel_path = request.args.get("path", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        return _file_metadata_response(abs_path)

    @app.route("/api/file-metadata", methods=["POST"])
    def file_metadata_post() -> Any:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        return _file_metadata_response(abs_path)

    @app.route("/api/scaffold/intermediate-game", methods=["POST"])
    def scaffold_intermediate_game_endpoint() -> Any:
        # pylint: disable=import-outside-toplevel
        from . import scaffolding

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        name = (data.get("name") or "").strip()
        params_override = data.get("params")
        if not name:
            return jsonify({"error": "Name is required"}), 400
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        try:
            suppress = io.StringIO()
            with redirect_stdout(suppress), redirect_stderr(suppress):
                engine, proof_file = _setup_engine_for_proof(
                    str(abs_path), allowed_root=directory
                )
                result = scaffolding.scaffold_intermediate_game(
                    engine, proof_file, name, params_override
                )
            return jsonify({"block": result.block, "params_used": result.params_used})
        except (
            frog_parser.ParseError,
            FileNotFoundError,
            semantic_analysis.FailedTypeCheck,
            ValueError,
        ) as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:  # pylint: disable=broad-exception-caught
            return jsonify({"error": f"Error: {e}"}), 400

    @app.route("/api/scaffold/reduction", methods=["POST"])
    def scaffold_reduction_endpoint() -> Any:
        # pylint: disable=import-outside-toplevel
        from . import scaffolding

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        name = (data.get("name") or "").strip()
        security_game_name = (data.get("security_game_name") or "").strip()
        side = (data.get("side") or "").strip()
        params = data.get("params") or ""
        compose_args = data.get("compose_args") or ""
        if not name:
            return jsonify({"error": "Name is required"}), 400
        if not security_game_name:
            return jsonify({"error": "Security game name is required"}), 400
        if not side:
            return jsonify({"error": "Side is required"}), 400
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        try:
            suppress = io.StringIO()
            with redirect_stdout(suppress), redirect_stderr(suppress):
                engine, proof_file = _setup_engine_for_proof(
                    str(abs_path), allowed_root=directory
                )
                result = scaffolding.scaffold_reduction(
                    engine,
                    proof_file,
                    name,
                    security_game_name,
                    side,
                    params,
                    compose_args,
                )
            return jsonify({"block": result.block})
        except (
            frog_parser.ParseError,
            FileNotFoundError,
            semantic_analysis.FailedTypeCheck,
            ValueError,
        ) as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:  # pylint: disable=broad-exception-caught
            return jsonify({"error": f"Error: {e}"}), 400

    @app.route("/api/scaffold/reduction-hop", methods=["POST"])
    def scaffold_reduction_hop_endpoint() -> Any:
        # pylint: disable=import-outside-toplevel
        from . import scaffolding

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        rel_path = data.get("path", "")
        content = data.get("content", "")
        assumption_index = data.get("assumption_index")
        side1 = (data.get("side1") or "").strip()
        side2 = (data.get("side2") or "").strip()
        reduction_name = (data.get("reduction_name") or "").strip()
        if not isinstance(assumption_index, int):
            return jsonify({"error": "assumption_index must be an integer"}), 400
        if not side1 or not side2:
            return jsonify({"error": "side1 and side2 are required"}), 400
        if not reduction_name:
            return jsonify({"error": "reduction_name is required"}), 400
        abs_path = _safe_path(directory, rel_path)
        if abs_path is None:
            return jsonify({"error": "Invalid path"}), 403
        abs_path.write_text(content, encoding="utf-8")
        try:
            suppress = io.StringIO()
            with redirect_stdout(suppress), redirect_stderr(suppress):
                engine, proof_file = _setup_engine_for_proof(
                    str(abs_path), allowed_root=directory
                )
                result = scaffolding.scaffold_reduction_hop(
                    engine,
                    proof_file,
                    assumption_index,
                    side1,
                    side2,
                    reduction_name,
                )
            return jsonify({"lines": result.lines})
        except (
            frog_parser.ParseError,
            FileNotFoundError,
            semantic_analysis.FailedTypeCheck,
            ValueError,
        ) as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:  # pylint: disable=broad-exception-caught
            return jsonify({"error": f"Error: {e}"}), 400

    # ── File watcher + SSE ──────────────────────────────────────────────────

    broker = _FileEventBroker()
    observer: Any = None
    if watch:
        base_path = Path(directory).resolve()
        handler = _FrogFileHandler(broker, base_path)
        observer = Observer()
        observer.schedule(handler, str(base_path), recursive=True)
        observer.start()

    @app.route("/api/events")
    def sse_events() -> Any:
        def _stream() -> Any:
            q = broker.subscribe()
            try:
                while True:
                    try:
                        event = q.get(timeout=15)
                        yield f"data: {json.dumps(event)}\n\n"
                    except queue.Empty:
                        # Heartbeat to keep connection alive
                        yield ": heartbeat\n\n"
            except GeneratorExit:
                broker.unsubscribe(q)

        return Response(
            _stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return app, observer


def start_server(directory: str) -> None:
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a directory", flush=True)
        return

    app, observer = create_app(directory)
    atexit.register(observer.stop)
    port = _find_free_port(5173)
    url = f"http://127.0.0.1:{port}"

    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    print(f"ProofFrog Web UI: {url}")
    print(f"Working directory: {directory}")
    print("Press Ctrl+C to stop.")

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    try:
        app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
    finally:
        observer.stop()
        observer.join()
