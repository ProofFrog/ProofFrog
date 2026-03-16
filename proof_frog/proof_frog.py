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
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.option("--json", "-j", "json_output", is_flag=True, help="Output JSON.")
def prove(file: str, verbose: bool, json_output: bool) -> None:
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
    engine = proof_engine.ProofEngine(verbose)
    proof_file: frog_ast.ProofFile
    try:
        proof_file = frog_parser.parse_proof_file(file)
    except (frog_parser.ParseError, FileNotFoundError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    try:
        semantic_analysis.check_well_formed(proof_file, file)
    except semantic_analysis.FailedTypeCheck:
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

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
        engine.prove(proof_file)
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
