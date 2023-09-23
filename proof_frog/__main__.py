import sys
from antlr4 import FileStream, CommonTokenStream
from parsing.PrimitiveLexer import PrimitiveLexer
from parsing.PrimitiveParser import PrimitiveParser
from parsing.SchemeLexer import SchemeLexer
from parsing.SchemeParser import SchemeParser
from parsing.GameLexer import GameLexer
from parsing.GameParser import GameParser
from parsing.ProofLexer import ProofLexer
from parsing.ProofParser import ProofParser
from ast_generation import SchemeASTGenerator, PrimitiveASTGenerator, GameASTGenerator, ProofASTGenerator


def main(argv: list[str]) -> None:
    my_ast = None
    input_stream = FileStream(argv[2])
    lexer_functor: type[PrimitiveLexer] | type[SchemeLexer]
    parser_functor: type[PrimitiveParser] | type[SchemeParser]
    ast_generator: type[PrimitiveASTGenerator] | type[SchemeASTGenerator]

    if argv[1] == 'primitive':
        lexer_functor = PrimitiveLexer
        parser_functor = PrimitiveParser
        ast_generator = PrimitiveASTGenerator
    elif argv[1] == 'scheme':
        lexer_functor = SchemeLexer
        parser_functor = SchemeParser
        ast_generator = SchemeASTGenerator
    elif argv[1] == 'game':
        lexer_functor = GameLexer
        parser_functor = GameParser
        ast_generator = GameASTGenerator
    elif argv[1] == 'proof':
        lexer_functor = ProofLexer
        parser_functor = ProofParser
        ast_generator = ProofASTGenerator

    lexer = lexer_functor(input_stream)
    parser = parser_functor(CommonTokenStream(lexer))
    tree = parser.program()
    my_ast = ast_generator().visit(tree)
    print(my_ast)


if __name__ == '__main__':
    main(sys.argv)
