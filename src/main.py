import sys
from antlr4 import FileStream, CommonTokenStream
from parsing.PrimitiveLexer import PrimitiveLexer
from parsing.PrimitiveParser import PrimitiveParser
from PrimitiveASTGenerator import PrimitiveASTGenerator


def main(argv):
    input_stream = FileStream(argv[1])
    lexer = PrimitiveLexer(input_stream)
    parser = PrimitiveParser(CommonTokenStream(lexer))
    tree = parser.program()
    myAST = PrimitiveASTGenerator().visit(tree)
    print(myAST)


if __name__ == '__main__':
    main(sys.argv)
