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


def parse(file_type: str, file_name: str) -> None:
    input_stream = FileStream(file_name)
    lexer_functor: type[PrimitiveLexer] | type[SchemeLexer]
    parser_functor: type[PrimitiveParser] | type[SchemeParser]
    ast_generator: type[PrimitiveASTGenerator] | type[SchemeASTGenerator]

    match file_type:
        case 'primitive':
            lexer_functor = PrimitiveLexer
            parser_functor = PrimitiveParser
            ast_generator = PrimitiveASTGenerator
        case 'scheme':
            lexer_functor = SchemeLexer
            parser_functor = SchemeParser
            ast_generator = SchemeASTGenerator
        case 'game':
            lexer_functor = GameLexer
            parser_functor = GameParser
            ast_generator = GameASTGenerator
        case 'proof':
            lexer_functor = ProofLexer
            parser_functor = ProofParser
            ast_generator = ProofASTGenerator

    lexer = lexer_functor(input_stream)
    parser = parser_functor(CommonTokenStream(lexer))
    tree = parser.program()
    my_ast = ast_generator().visit(tree)
    print(my_ast)


def main(argv: list[str]) -> None:
    if argv[1] == 'parse':
        parse(argv[2], argv[3])


if __name__ == '__main__':
    main(sys.argv)
