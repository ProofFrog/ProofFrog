import sys
from colorama import init
from . import frog_parser
from . import proof_engine
from . import semantic_analysis


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
        file = argv[2]
        try:
            root = frog_parser.parse_file(file)
            print(root)
        except ValueError:
            usage(argv[0])

    elif argv[1] == "prove":
        engine = proof_engine.ProofEngine(argv[2], len(argv) > 3 and argv[3] == "-v")
        engine.prove()
    elif argv[1] == "check":
        file = argv[2]
        try:
            root = frog_parser.parse_file(file)
            semantic_analysis.check_well_formed(root)
            print(f"{file} is well-formed.")
        except ValueError:
            usage(argv[0])
    else:
        usage()


if __name__ == "__main__":
    main()
