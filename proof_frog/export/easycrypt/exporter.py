"""End-to-end exporter: ProofFile path -> EasyCrypt source string."""

from __future__ import annotations

from typing import Callable

from . import ec_ast
from . import module_translator as mt
from . import proof_translator as pt
from . import type_collector as tc
from ... import frog_ast
from ... import frog_parser


def export_proof_file(proof_path: str) -> str:
    """Parse ``proof_path`` and return the EC source as a string.

    Walking-skeleton scope: one primitive import, one scheme import, one
    game-file import, zero assumptions, zero reductions, no lemmas/
    induction, no helper games. All hops are interchangeability hops.
    """
    proof = frog_parser.parse_proof_file(proof_path)

    primitive: frog_ast.Primitive | None = None
    scheme: frog_ast.Scheme | None = None
    game_file: frog_ast.GameFile | None = None

    for imp in proof.imports:
        resolved = frog_parser.resolve_import_path(imp.filename, proof_path)
        root = frog_parser.parse_file(resolved)
        if isinstance(root, frog_ast.Primitive):
            primitive = root
        elif isinstance(root, frog_ast.Scheme):
            scheme = root
            for sub_imp in scheme.imports:
                sub_resolved = frog_parser.resolve_import_path(
                    sub_imp.filename, resolved
                )
                sub_root = frog_parser.parse_file(sub_resolved)
                if isinstance(sub_root, frog_ast.Primitive):
                    primitive = sub_root
        elif isinstance(root, frog_ast.GameFile):
            game_file = root

    if primitive is None:
        raise ValueError(
            "Skeleton exporter requires a Primitive to be imported directly "
            "or transitively through a Scheme."
        )
    if scheme is None:
        raise ValueError("Skeleton exporter requires a Scheme import.")
    if game_file is None:
        raise ValueError("Skeleton exporter requires a GameFile import.")

    aliases: dict[str, frog_ast.Type] = {}
    for sf in scheme.fields:
        if sf.value is not None and isinstance(sf.value, frog_ast.Type):
            aliases[sf.name] = sf.value
    types = tc.TypeCollector(aliases=aliases)

    def type_of_factory(
        local_types: dict[str, frog_ast.Type],
    ) -> Callable[[frog_ast.Expression], frog_ast.Type]:
        def type_of(e: frog_ast.Expression) -> frog_ast.Type:
            if isinstance(e, frog_ast.Variable):
                if e.name in local_types:
                    return local_types[e.name]
                raise KeyError(f"Unknown variable type for {e.name!r}")
            raise NotImplementedError(f"type_of not implemented for {type(e).__name__}")

        return type_of

    modules = mt.ModuleTranslator(types, type_of_factory)

    ec_primitive = modules.translate_primitive(primitive)
    ec_scheme = modules.translate_scheme(scheme, primitive.name)
    left_game = game_file.games[0]
    right_game = game_file.games[1]
    left_module_name = f"{game_file.name}_{left_game.name}"
    right_module_name = f"{game_file.name}_{right_game.name}"
    ec_left = modules.translate_game(left_game, left_module_name, primitive.name)
    ec_right = modules.translate_game(right_game, right_module_name, primitive.name)

    assert len(left_game.methods) == 1 and len(right_game.methods) == 1
    left_ref = pt.GameSideRef(
        left_module_name, left_game.methods[0].signature.name.lower()
    )
    right_ref = pt.GameSideRef(
        right_module_name, right_game.methods[0].signature.name.lower()
    )
    game_refs = {left_game.name: left_ref, right_game.name: right_ref}

    proofs = pt.ProofTranslator(primitive.name)
    lemmas = proofs.translate_hops(game_refs, proof.steps)

    decls: list[ec_ast.EcTopDecl] = []
    decls.extend(types.emit())
    decls.append(ec_primitive)
    decls.append(ec_scheme)
    decls.append(ec_left)
    decls.append(ec_right)
    decls.extend(lemmas)

    ec_file = ec_ast.EcFile(
        requires=["AllCore", "Distr"],
        decls=decls,
    )
    return ec_ast.pretty_print(ec_file)
