import sys
from colorama import init
from . import frog_parser
from . import proof_engine
from . import semantic_analysis


def usage(module_name: str) -> None:
    print("Incorrect Arguments", file=sys.stderr)
    print(f"Usage: {module_name} parse <file>")
    print(f"Usage: {module_name} prove <file.proof>")
    print(f"Usage: {module_name} check <file.proof>")
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
    elif argv[1] == "check":
        file = argv[2]
        try:
            root = frog_parser.parse_file(file)
            semantic_analysis.check_well_formed(root)
            print(f"{file} is well-formed.")
        except ValueError:
            usage(argv[0])
    else:
        usage(argv[0])


if __name__ == "__main__":
    init(autoreset=True)
    main(sys.argv)
