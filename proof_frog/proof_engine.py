import os
import frog_parser
import frog_ast


def prove(proof_file_name: str) -> None:
    proof_file = frog_parser.parse_proof(proof_file_name)
    proof_namespace: dict[str, frog_ast.Root] = {}

    for i in proof_file.imports:
        file_type = _get_file_type(i.filename)
        root: frog_ast.Root
        match file_type:
            case frog_ast.FileType.PRIMITIVE:
                root = frog_parser.parse_primitive(i.filename)
            case frog_ast.FileType.SCHEME:
                root = frog_parser.parse_scheme(i.filename)
            case frog_ast.FileType.GAME:
                root = frog_parser.parse_game(i.filename)
            case frog_ast.FileType.PROOF:
                raise TypeError("Cannot import proofs")

        name = i.rename if i.rename else root.get_export_name()
        proof_namespace[name] = root

    print(proof_namespace)


def _get_file_type(file_name: str) -> frog_ast.FileType:
    extension: str = os.path.splitext(file_name)[1].strip('.')
    return frog_ast.FileType(extension)
