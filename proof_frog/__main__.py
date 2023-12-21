import sys
from colorama import init
from . import frog_parser
from . import proof_engine


def usage(module_name: str) -> None:
    print("Incorrect Arguments", file=sys.stderr)
    print(f"Usage: {module_name} parse [primitive|game|scheme|proof] <file>")
    print(f"Usage: {module_name} prove <file.proof>")
    sys.exit(1)


def main(argv: list[str]) -> None:
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
    else:
        usage(argv[0])


if __name__ == "__main__":
    init(autoreset=True)
    main(sys.argv)
