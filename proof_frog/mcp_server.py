"""ProofFrog MCP server for Claude Code integration.

Exposes ProofFrog's parse, check, prove, and introspection capabilities as
MCP tools so Claude Code can interactively help write and debug proofs.

Start the server with:
    python -m proof_frog mcp [directory]

Then register it in .claude/settings.json:
    {
      "mcpServers": {
        "prooffrog": {
          "command": "python",
          "args": ["-m", "proof_frog", "mcp", "examples/"],
          "cwd": "/path/to/ProofFrog"
        }
      }
    }
"""

from __future__ import annotations
import io
import os
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import frog_parser, semantic_analysis
from . import describe as describe_module
from .web_server import _capture_parse, _capture_prove, _capture_inline, _build_tree, _strip_ansi

mcp: FastMCP = FastMCP(
    "ProofFrog",
    instructions=(
        "Tools for reading, writing, parsing, and proving ProofFrog cryptographic "
        "proof files. Use `list_files` to explore available primitives/games/schemes, "
        "`describe` to understand their interfaces, `write_file` + `prove` to verify "
        "a proof, and `get_step_detail` to diagnose failing proof steps."
    ),
)

# Working directory set by run_server(); resolved to an absolute path.
_directory: str = "."  # pylint: disable=invalid-name


def _resolve(path: str) -> str:
    """Resolve a path relative to the server's working directory."""
    if os.path.isabs(path):
        return path
    return str(Path(_directory) / path)


# ---------------------------------------------------------------------------
# File system tools
# ---------------------------------------------------------------------------


@mcp.tool()
def list_files(subdirectory: str = "") -> dict[str, Any]:
    """List all ProofFrog files in a directory tree.

    Returns a nested tree of {"name", "path", "type", "children"?} nodes.
    Files include .primitive, .game, .scheme, and .proof extensions.
    Leave subdirectory empty to list the server's root working directory.
    """
    target = _resolve(subdirectory) if subdirectory else _directory
    base = Path(_directory)
    return _build_tree(Path(target), base)


@mcp.tool()
def read_file(path: str) -> str:
    """Read the text content of a ProofFrog file.

    Path may be absolute or relative to the server's working directory.
    """
    return Path(_resolve(path)).read_text(encoding="utf-8")


@mcp.tool()
def write_file(path: str, content: str) -> dict[str, Any]:
    """Write (create or overwrite) a ProofFrog file.

    Path may be absolute or relative to the server's working directory.
    Parent directories are created automatically.
    Returns {"success": true, "path": "<absolute path>"}.
    """
    abs_path = Path(_resolve(path))
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    return {"success": True, "path": str(abs_path)}


# ---------------------------------------------------------------------------
# Introspection tools
# ---------------------------------------------------------------------------


@mcp.tool()
def describe(path: str) -> str:
    """Get a concise interface description of a ProofFrog file.

    Returns the exported name, parameters, fields, and method signatures
    WITHOUT method implementations. Much shorter than reading the raw file —
    ideal for quickly understanding what a primitive, scheme, or game provides.

    Supported: .primitive, .scheme, .game, .proof
    """
    try:
        return describe_module.describe_file(_resolve(path))
    except (ValueError, frog_parser.ParseError) as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Verification tools
# ---------------------------------------------------------------------------


@mcp.tool()
def parse(path: str) -> dict[str, Any]:
    """Parse a ProofFrog file and return its AST representation.

    Returns {"output": str, "success": bool}.
    The output is the stringified AST on success, or error message on failure.
    Useful for checking syntax in any file type before running a proof.
    """
    output, success = _capture_parse(_resolve(path))
    return {"output": output, "success": success}


@mcp.tool()
def check(path: str) -> dict[str, Any]:
    """Run semantic type-checking on a ProofFrog file.

    Returns {"output": str, "success": bool}.
    More thorough than parse — catches type mismatches, undefined names,
    signature mismatches between Left/Right games, etc.
    """
    abs_path = _resolve(path)
    buf = io.StringIO()
    try:
        root = frog_parser.parse_file(abs_path)
        with redirect_stdout(buf), redirect_stderr(buf):
            semantic_analysis.check_well_formed(root, abs_path)
        return {"output": f"{abs_path} is well-formed.", "success": True}
    except frog_parser.ParseError as e:
        return {"output": str(e), "success": False}
    except semantic_analysis.FailedTypeCheck:
        msg = _strip_ansi(buf.getvalue()) or "Type check failed."
        return {"output": msg, "success": False}
    except Exception as e:  # pylint: disable=broad-except
        return {"output": f"Error: {e}", "success": False}


@mcp.tool()
def prove(proof_path: str) -> dict[str, Any]:
    """Run proof verification on a .proof file.

    Returns:
      output      — Full verification output (all steps, simplified game forms)
      success     — True only if every game hop passed
      hop_results — List of {"step_num": int, "valid": bool, "kind": str} per hop

    Imports in the proof are resolved relative to the server's working directory.
    Use write_file first to save the proof content to disk, then call prove.
    """
    output, success, hop_results = _capture_prove(_resolve(proof_path), _directory)
    return {"output": output, "success": success, "hop_results": hop_results}


@mcp.tool()
def get_step_detail(proof_path: str, step_index: int) -> dict[str, Any]:
    """Get the canonical (fully simplified) form of one proof step.

    This is the primary diagnostic tool for failing proof steps. Compare the
    canonical forms of two adjacent steps to see exactly what differs — a failing
    step means those canonical forms are not structurally identical.

    step_index is 0-based (first game in the `games:` list is index 0).

    Returns:
      output       — Raw (pre-simplification) game AST
      canonical    — Fully simplified canonical game form (what ProofFrog compares)
      success      — False if the step index is out of range or an error occurred
      has_reduction — True if this step uses a reduction
      reduction    — The reduction game (if has_reduction)
      challenger   — The challenger game without reduction (if has_reduction)
      scheme       — The underlying scheme (if applicable)
    """
    output, canonical, success, has_reduction, reduction, challenger, scheme = (
        _capture_inline(_resolve(proof_path), step_index, _directory)
    )
    return {
        "output": output,
        "canonical": canonical,
        "success": success,
        "has_reduction": has_reduction,
        "reduction": reduction,
        "challenger": challenger,
        "scheme": scheme,
    }


# ---------------------------------------------------------------------------
# Language reference resource
# ---------------------------------------------------------------------------

_LANGUAGE_REFERENCE = """\
# ProofFrog Language Reference

## File Types
- .primitive  Abstract cryptographic interface (method signatures, no implementations)
- .scheme     Concrete implementation extending a primitive
- .game       Pair of Left/Right security games (defines a security notion)
- .proof      Game-hopping proof script

## Primitive Types
- Int, Bool, Void
- BitString<N>        Fixed-length bit string of length N (N is an Int expression)
- Set                 Abstract untyped set
- T?                  Optional type (may be None)
- T1 * T2 * ...       Product/tuple type
- Array<T, N>         Array
- Map<K, V>           Map

## Primitive Syntax
```
Primitive Name(Set Param1, Int Param2) {
    Set Field1 = Param1;
    Int Field2 = Param2;
    ReturnType MethodName(ArgType arg);   // signature only, no body
}
```

## Scheme Syntax
```
import 'path/to/Primitive.primitive';

Scheme Name(PrimType P) extends PrimitiveName {
    requires P.field1 == P.field2;   // optional precondition
    Set Field = P.SomeField;
    ReturnType MethodName(ArgType arg) {
        // full implementation
    }
}
```

## Game Syntax
```
import 'path/to/Primitive.primitive';

Game Left(PrimType E) {
    E.Key k;
    Void Initialize() { k = E.KeyGen(); }
    E.Ciphertext Oracle(E.Message mL, E.Message mR) {
        return E.Enc(k, mL);
    }
}

Game Right(PrimType E) {
    E.Key k;
    Void Initialize() { k = E.KeyGen(); }
    E.Ciphertext Oracle(E.Message mL, E.Message mR) {
        return E.Enc(k, mR);
    }
}

export as SecurityGame;
```

## Statements
- `Type name;`             Declaration (uninitialized field)
- `Type name = expr;`      Declaration + assignment
- `name = expr;`           Assignment (no type annotation)
- `Type name <- expr;`     Random sample from set (declaration)
- `name <- expr;`          Random sample (no type annotation)
- `return expr;`
- `if (cond) { ... } else if (...) { ... } else { ... }`
- `for (Int i = start to end) { ... }`   Numeric for loop
- `for (Type x in set) { ... }`          Set iteration

## Expressions
- Arithmetic:     +  -  *  /
- Comparison:     ==  !=  <  >  <=  >=
- Logical:        &&  ||  !
- XOR / add:      a + b       (BitString<N> + BitString<N> → XOR)
- Concatenation:  a || b      (BitString<M> || BitString<N> → BitString<M+N>)
- Slicing:        a[s : e]    (BitString, s and e are Int expressions)
- Size:           |a|
- Field access:   obj.field
- Array index:    arr[i]
- Tuple literal:  [a, b, c]
- Tuple index:    tup[0]
- Set literal:    {a, b, c}
- Set ops:        A union B,  A \\ B,  x in S,  A subsets B
- Optional:       None        (the None value for T? types)

## Proof Syntax
```
import 'path/to/Primitive.primitive';
import 'path/to/Game.game';
import 'path/to/Scheme.scheme';

// Optional reductions (adapters between security games)
Reduction R(PrimType E) compose ChallengerGame(E) against AdversaryGame(E).Adversary {
    ReturnType OracleMethod(ArgType arg) {
        // `challenger` calls the ChallengerGame's methods
        return challenger.SomeMethod(arg);
    }
}

proof:

let:
    Set MessageSpace;
    PrimType E = PrimType(MessageSpace, ...);
    SchemeType S = SchemeType(E);

assume:
    AssumedSecureGame(E);

theorem:
    TargetGame(S);

games:
    TargetGame(S).Left against TargetGame(S).Adversary;
    AssumedSecureGame(E).Real compose R(E) against TargetGame(S).Adversary;
    AssumedSecureGame(E).Random compose R(E) against TargetGame(S).Adversary;
    TargetGame(S).Right against TargetGame(S).Adversary;
```

## Game Hop Rules
- Consecutive steps are equivalent iff their canonical (simplified) forms match.
- A step can also be an assumed-secure transition (uses a security assumption).
- The first step must be the theorem game's Left variant.
- The last step must be the theorem game's Right variant.
- Reductions use `compose` to plug a game in as challenger for another.

## Import Paths
Paths in import statements are relative to where `proof_frog` is invoked,
NOT relative to the importing file.
"""


@mcp.resource("prooffrog://language-reference")
def language_reference() -> str:
    """Concise ProofFrog language syntax reference."""
    return _LANGUAGE_REFERENCE


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_server(directory: str) -> None:
    """Start the MCP server using stdio transport (required for Claude Code)."""
    global _directory  # pylint: disable=global-statement
    _directory = os.path.abspath(directory)
    mcp.run(transport="stdio")
