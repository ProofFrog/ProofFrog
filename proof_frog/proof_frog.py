import sys
import os
from colorama import init
from antlr4 import error
from . import frog_parser
from . import frog_ast
from . import proof_engine
from . import semantic_analysis


def usage() -> None:
    print("Incorrect Arguments", file=sys.stderr)
    print("Usage: proof_frog parse <file>")
    print("Usage: proof_frog prove <file.proof>")
    sys.exit(1)


def main() -> None:
    init(autoreset=True)
    argv: list[str] = sys.argv
    root: frog_ast.Root
    if len(argv) < 2:
        usage()

    if argv[1] == "parse":
        file = argv[2]
        try:
            root = frog_parser.parse_file(file)
            print(root)
        except ValueError:
            usage()
    elif argv[1] == "check":
        file_name = argv[2]
        try:
            root = frog_parser.parse_file(file_name)
        except ValueError:
            usage()
        try:
            semantic_analysis.check_well_formed(root, file_name)
            print(f"{file_name} is well-formed.")
        except semantic_analysis.FailedTypeCheck:
            print("Failed to type check")

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
