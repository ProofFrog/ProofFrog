import sys
from colorama import init
from . import proof_engine, frog_parser, latex_output


def usage() -> None:
    print("Incorrect Arguments", file=sys.stderr)
    print("Usage: proof_frog parse [primitive|game|scheme|proof] <file>")
    print("Usage: proof_frog prove <file.proof>")
    print("Usage: proof_frog print <file>")
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
        engine = proof_engine.ProofEngine(argv[2], len(argv) > 3 and argv[3] == "-v")
        engine.prove()
    elif argv[1] == "print":
        file_name = argv[2]
        root = frog_parser.parse_file_from_name(file_name)
        latex_output.LatexVisitor().visit(root)
    else:
        usage()


if __name__ == "__main__":
    main()
