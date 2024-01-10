from proof_frog import frog_parser, proof_engine


def test_inlining() -> None:
    oracle = """
    Int oracle(int a) {
        Int x = 0;
        Int y = x + a;
        return y;
    }
"""

    called = """
    Game Test() {
        Int using() {
            Int x = 1;
            Int c = challenger.oracle();
            return c;
        }
    }
"""
    method = frog_parser.parse_method(oracle)
    method_lookup = {}
    method_lookup[("challenger", "oracle")] = method

    result = proof_engine.inline_calls(method_lookup, frog_parser.parse_game(called))

    print(result)
    assert False
