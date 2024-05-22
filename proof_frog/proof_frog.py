import sys
import os
from colorama import init
from antlr4 import error
from . import frog_parser
from . import frog_ast
from . import proof_engine


def usage() -> None:
    print("Incorrect Arguments", file=sys.stderr)
    print("Usage: proof_frog parse [primitive|game|scheme|proof] <file>")
    print("Usage: proof_frog prove <file.proof>")
    sys.exit(1)


def main() -> None:
    init(autoreset=True)
    argv: list[str] = sys.argv
    if len(argv) < 2:
        usage()

    if argv[1] == "parse":
        ast_type = argv[2]
        file = argv[3]
        match ast_type:
            case "primitive":
                print(frog_parser.parse_primitive_file(file))
            case "scheme":
                print(frog_parser.parse_scheme_file(file))
            case "game":
                print(frog_parser.parse_game_file(file))
            case "proof":
                print(frog_parser.parse_proof_file(file))
            case _:
                usage()
    elif argv[1] == "prove":
        engine = proof_engine.ProofEngine(len(argv) > 3 and argv[3] == "-v")
        proof_file: frog_ast.ProofFile
        try:
            proof_file = frog_parser.parse_proof_file(argv[2])
        except error.Errors.ParseCancellationException:
            print(f"Parse of {argv[2]} failed")
            sys.exit(1)

        for imp in proof_file.imports:
            file_type = _get_file_type(imp.filename)
            root: frog_ast.Root
            try:
                match file_type:
                    case frog_ast.FileType.PRIMITIVE:
                        root = frog_parser.parse_primitive_file(imp.filename)
                    case frog_ast.FileType.SCHEME:
                        root = frog_parser.parse_scheme_file(imp.filename)
                    case frog_ast.FileType.GAME:
                        root = frog_parser.parse_game_file(imp.filename)
                    case frog_ast.FileType.PROOF:
                        raise TypeError("Cannot import proofs")
            except error.Errors.ParseCancellationException:
                print(f"Parse of {imp.filename} failed")
                sys.exit(1)

            name = imp.rename if imp.rename else root.get_export_name()
            engine.add_definition(name, root)

        try:
            engine.prove(proof_file)
        except proof_engine.FailedProof:
            sys.exit(1)
    else:
        usage()


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip(".")
    return frog_ast.FileType(extension)


if __name__ == "__main__":
    main()
