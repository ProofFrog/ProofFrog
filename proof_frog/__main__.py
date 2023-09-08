import sys
from antlr4 import FileStream, CommonTokenStream
from parsing.PrimitiveLexer import PrimitiveLexer
from parsing.PrimitiveParser import PrimitiveParser
from primitive_ast_generator import PrimitiveASTGenerator


def main(argv):
    input_stream = FileStream(argv[1])
    lexer = PrimitiveLexer(input_stream)
    parser = PrimitiveParser(CommonTokenStream(lexer))
    tree = parser.program()
    my_ast = PrimitiveASTGenerator().visit(tree)
    print(my_ast)


if __name__ == '__main__':
    main(sys.argv)
