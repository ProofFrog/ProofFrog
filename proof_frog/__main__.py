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
                usage(argv[0])
    elif argv[1] == "prove":
        proof_engine.prove(argv[2], len(argv) > 3 and argv[3] == "-v")
    else:
        usage(argv[0])


if __name__ == "__main__":
    init(autoreset=True)
    main(sys.argv)
