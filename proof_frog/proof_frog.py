# pylint: disable=duplicate-code  # CLI commands share return-dict patterns with web_server/mcp_server
import json
import os
import sys
import tempfile
from pathlib import Path

import click
from colorama import init

from . import frog_parser
from . import frog_ast
from . import proof_engine
from . import semantic_analysis


@click.group()
def cli() -> None:
    """ProofFrog — A tool for checking transitions in cryptographic game-hopping proofs."""
    init(autoreset=True)


def _resolve_git_sha() -> str | None:
    """Return a short git SHA for dev builds, or None if unavailable.

    Appends ``-dirty`` when tracked files have uncommitted changes. Prefers a
    live ``git rev-parse`` (accurate for editable installs) and falls back to
    the SHA stamped into ``_git_sha.py`` at build time (for wheels)."""
    # pylint: disable=import-outside-toplevel
    import subprocess

    try:
        pkg_dir = Path(__file__).resolve().parent
        sha_result = subprocess.run(
            ["git", "-C", str(pkg_dir), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        sha = sha_result.stdout.strip()
        if sha_result.returncode == 0 and sha:
            status_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(pkg_dir),
                    "status",
                    "--porcelain",
                    "--untracked-files=no",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
            if status_result.returncode == 0 and status_result.stdout.strip():
                sha += "-dirty"
            return sha
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        from ._git_sha import GIT_SHA

        return GIT_SHA
    except ImportError:
        return None


@cli.command()
def version() -> None:
    """Print the ProofFrog version."""
    # pylint: disable=import-outside-toplevel
    from importlib.metadata import version as pkg_version

    v = pkg_version("proof_frog")
    suffix = ""
    if "dev" in v:
        sha = _resolve_git_sha()
        if sha:
            suffix = f" ({sha})"
    click.echo(f"ProofFrog {v}{suffix}")


@cli.command()
@click.argument("file")
@click.option("--json", "-j", "json_output", is_flag=True, help="Output JSON.")
def parse(file: str, json_output: bool) -> None:
    """Parse a FrogLang file and print its AST."""
    if json_output:
        # pylint: disable=import-outside-toplevel
        from .web_server import _capture_parse

        output, success, _err_line, _err_col = _capture_parse(file)
        click.echo(json.dumps({"output": output, "success": success}))
        return
    try:
        root = frog_parser.parse_file(file)
        print(root)
    except ValueError:
        click.echo("Unsupported file type.", err=True)
        sys.exit(1)
    except (frog_parser.ParseError, FileNotFoundError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)


@cli.command()
@click.argument("file")
@click.option("--json", "-j", "json_output", is_flag=True, help="Output JSON.")
def check(file: str, json_output: bool) -> None:
    """Type-check and semantically analyze a FrogLang file."""
    if json_output:
        # pylint: disable=import-outside-toplevel
        from .web_server import _capture_check

        output, success, _err_line, _err_col = _capture_check(file)
        click.echo(json.dumps({"output": output, "success": success}))
        return
    try:
        root = frog_parser.parse_file(file)
    except ValueError:
        click.echo("Unsupported file type.", err=True)
        sys.exit(1)
    except (frog_parser.ParseError, FileNotFoundError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    try:
        semantic_analysis.check_well_formed(root, file)
        print(f"{file} is well-formed.")
    except semantic_analysis.FailedTypeCheck:
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        sys.exit(1)


@cli.command()
@click.argument("file")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (-v for games, -vv for transforms).",
)
@click.option("--json", "-j", "json_output", is_flag=True, help="Output JSON.")
@click.option(
    "--no-diagnose",
    is_flag=True,
    help="Suppress diagnostic analysis on failure (summary only).",
)
@click.option(
    "--skip-lemmas",
    is_flag=True,
    help="Skip lemma proof verification (trust without re-checking).",
)
@click.option(
    "--sequential",
    is_flag=True,
    help=(
        "Disable parallel equivalence checking (use a single process). "
        "Can also be forced via the PROOFFROG_SEQUENTIAL environment variable."
    ),
)
def prove(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    file: str,
    verbose: int,
    json_output: bool,
    no_diagnose: bool,
    skip_lemmas: bool,
    sequential: bool,
) -> None:
    """Run proof verification on a .proof file."""
    if json_output:
        # pylint: disable=import-outside-toplevel
        from .web_server import _capture_prove

        output, success, hop_results, _has_induction, _err_line, _err_col = (
            _capture_prove(file)
        )
        click.echo(
            json.dumps(
                {"output": output, "success": success, "hop_results": hop_results}
            )
        )
        return
    verbosity = proof_engine.Verbosity(min(verbose, 2))
    engine = proof_engine.ProofEngine(
        verbosity,
        no_diagnose=no_diagnose,
        skip_lemmas=skip_lemmas,
        parallel=not sequential,
    )
    proof_file: frog_ast.ProofFile
    try:
        proof_file = frog_parser.parse_proof_file(file)
    except (frog_parser.ParseError, FileNotFoundError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    click.echo("Type checking...")
    try:
        semantic_analysis.check_well_formed(proof_file, file)
    except semantic_analysis.FailedTypeCheck:
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    click.echo()

    for imp in proof_file.imports:
        resolved = frog_parser.resolve_import_path(imp.filename, file)
        file_type = _get_file_type(resolved)
        root: frog_ast.Root
        try:
            match file_type:
                case frog_ast.FileType.PRIMITIVE:
                    root = frog_parser.parse_primitive_file(resolved)
                case frog_ast.FileType.SCHEME:
                    root = frog_parser.parse_scheme_file(resolved)
                case frog_ast.FileType.GAME:
                    root = frog_parser.parse_game_file(resolved)
                case frog_ast.FileType.PROOF:
                    raise TypeError("Cannot import proofs")
        except frog_parser.ParseError as e:
            click.echo(str(e), err=True)
            sys.exit(1)
        except FileNotFoundError:
            click.echo(
                f"{file}:{imp.line_num}: imported file not found: " f"'{imp.filename}'",
                err=True,
            )
            sys.exit(1)

        name = imp.rename if imp.rename else root.get_export_name()
        engine.add_definition(name, root)

    try:
        engine.prove(proof_file, file)
    except proof_engine.FailedProof:
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        click.echo(f"Error during proof verification: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file")
@click.option("--json", "-j", "json_output", is_flag=True, help="Output JSON.")
def describe(file: str, json_output: bool) -> None:
    """Print a concise interface description of a FrogLang file."""
    if json_output:
        # pylint: disable=import-outside-toplevel
        from .web_server import _capture_describe

        output, success = _capture_describe(file)
        click.echo(json.dumps({"output": output, "success": success}))
        return
    # pylint: disable=import-outside-toplevel
    from proof_frog.describe import describe_file

    try:
        print(describe_file(file))
    except (ValueError, frog_parser.ParseError, FileNotFoundError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)


@cli.command(name="export-latex")
@click.argument("file")
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output path for the .tex file (default: alongside the input, .tex extension).",
)
@click.option(
    "--backend",
    default="cryptocode",
    type=click.Choice(["cryptocode"]),
    help="Pseudocode package backend (only 'cryptocode' in v1).",
)
def export_latex(file: str, output: str | None, backend: str) -> None:
    """Export a FrogLang file (.primitive, .scheme, .game, .proof) to LaTeX."""
    # pylint: disable=import-outside-toplevel
    from .export.latex.exporter import export_file

    try:
        source = export_file(file, backend_name=backend)
    except (frog_parser.ParseError, FileNotFoundError, ValueError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    out_path = output if output is not None else str(Path(file).with_suffix(".tex"))
    Path(out_path).write_text(source, encoding="utf-8")
    click.echo(f"Wrote {out_path}")


@cli.command("step-detail")
@click.argument("file")
@click.argument("step_index", type=click.INT)
def step_detail(file: str, step_index: int) -> None:
    """Get the canonical form of a proof step (JSON output)."""
    # pylint: disable=import-outside-toplevel
    from .web_server import _capture_inline

    output, canonical, success, has_reduction, reduction, challenger, scheme = (
        _capture_inline(file, step_index)
    )
    click.echo(
        json.dumps(
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
    )


@cli.command("inlined-game")
@click.argument("file")
@click.argument("step_text")
def inlined_game(file: str, step_text: str) -> None:
    """Get the canonical form of a game step expression against a proof's context (JSON output)."""
    # pylint: disable=import-outside-toplevel
    from .web_server import _build_minimal_proof, _capture_inline

    try:
        proof_text = Path(file).read_text(encoding="utf-8")
        minimal = _build_minimal_proof(proof_text, step_text)
        if minimal is None:
            click.echo(
                json.dumps(
                    {
                        "output": "Could not extract theorem: block from proof file.",
                        "canonical": "",
                        "success": False,
                    }
                )
            )
            return
        fd, tmp_path = tempfile.mkstemp(
            suffix=".proof", dir=os.path.dirname(os.path.abspath(file))
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(minimal)
            output, canonical, success, _, _, _, _ = _capture_inline(tmp_path, 0)
        finally:
            os.unlink(tmp_path)
        click.echo(
            json.dumps({"output": output, "canonical": canonical, "success": success})
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        click.echo(
            json.dumps({"output": f"Error: {e}", "canonical": "", "success": False})
        )


@cli.command("canonicalization-trace")
@click.argument("file")
@click.argument("step_index", type=click.INT)
def canonicalization_trace(file: str, step_index: int) -> None:
    """Show which transforms fired per iteration for a proof step (JSON output)."""
    # pylint: disable=import-outside-toplevel
    from .web_server import _capture_canonicalization_trace

    result = _capture_canonicalization_trace(file, step_index)
    click.echo(json.dumps(result))


@cli.command("step-after-transform")
@click.argument("file")
@click.argument("step_index", type=click.INT)
@click.argument("transform_name")
def step_after_transform(file: str, step_index: int, transform_name: str) -> None:
    """Get game AST after applying transforms up to a named one (JSON output)."""
    # pylint: disable=import-outside-toplevel
    from .web_server import _capture_step_after_transform

    result = _capture_step_after_transform(file, step_index, transform_name)
    click.echo(json.dumps(result))


@cli.command()
@click.argument("directory", default=".")
def web(directory: str) -> None:
    """Start the ProofFrog web interface."""
    # pylint: disable=import-outside-toplevel
    from proof_frog.web_server import start_server

    start_server(directory)


@cli.command()
def lsp() -> None:
    """Start the Language Server Protocol server."""
    # pylint: disable=import-outside-toplevel
    from proof_frog.lsp import run_server

    run_server()


@cli.command("download-examples")
@click.argument("directory", default="examples")
@click.option(
    "--force", is_flag=True, help="Overwrite the directory if it already exists."
)
@click.option(
    "--ref",
    default=None,
    help="Git ref (commit SHA, tag, or branch) to download. Defaults to the pinned version.",
)
def download_examples(directory: str, force: bool, ref: str | None) -> None:
    """Download the examples repository at the version pinned to this build."""
    # pylint: disable=import-outside-toplevel
    import io
    import shutil
    import tarfile
    import urllib.error
    import urllib.request

    examples_repo: str
    examples_ref: str
    if ref is not None:
        examples_repo = "https://github.com/ProofFrog/examples"
        examples_ref = ref
    else:
        try:
            from proof_frog._examples_pin import EXAMPLES_REPO, EXAMPLES_SHA

            examples_repo = EXAMPLES_REPO
            examples_ref = EXAMPLES_SHA
        except ImportError:
            click.echo(
                "Examples pin not found. "
                "This build was not stamped with submodule info.\n"
                "If building from source, run: make examples-pin\n"
                "Or specify a ref explicitly with --ref",
                err=True,
            )
            sys.exit(1)

    target = Path(directory)
    if target.exists() and not force:
        click.echo(
            f"Directory '{directory}' already exists. " "Use --force to overwrite.",
            err=True,
        )
        sys.exit(1)

    url = f"{examples_repo}/archive/{examples_ref}.tar.gz"
    click.echo(f"Downloading examples ({examples_ref[:12]})...")

    try:
        with urllib.request.urlopen(url) as response:  # noqa: S310
            archive_bytes = response.read()
    except urllib.error.URLError as e:
        click.echo(f"Download failed: {e}", err=True)
        sys.exit(1)

    if target.exists():
        shutil.rmtree(target)

    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
            # The archive has a top-level directory like examples-<sha>/
            # Strip it so files land directly in the target directory.
            prefix = tar.getmembers()[0].name.split("/")[0] + "/"
            for member in tar.getmembers():
                if not member.name.startswith(prefix):
                    continue
                member.name = member.name[len(prefix) :]
                if not member.name:
                    continue
                tar.extract(member, target, filter="data")
    except tarfile.TarError as e:
        click.echo(f"Extraction failed: {e}", err=True)
        sys.exit(1)

    click.echo(f"Examples downloaded to '{directory}'.")


@cli.command()
@click.argument("directory", default=".")
def mcp(directory: str) -> None:
    """Start the MCP (Model Context Protocol) server."""
    # pylint: disable=import-outside-toplevel
    try:
        from proof_frog.mcp_server import run_server
    except ImportError:
        click.echo(
            "The 'mcp' package is required for the MCP server.\n"
            "Install it with: pip install 'proof_frog[mcp]'",
            err=True,
        )
        sys.exit(1)
    run_server(directory)


main = cli


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip(".")
    return frog_ast.FileType(extension)


if __name__ == "__main__":
    main()
