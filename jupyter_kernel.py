import io
from contextlib import redirect_stdout
from ipykernel.kernelbase import Kernel
from proof_frog import proof_engine
from proof_frog import frog_parser


class FrogKernel(Kernel):
    implementation = "Proof Frog Kernel"
    implementation_version = "1.0"
    language = "no-op"
    language_version = "0.1"
    language_info = {
        "name": "Any text",
        "mimetype": "text/plain",
        "file_extension": ".txt",
    }
    banner = "Proof Frog Kernel"
    engine = proof_engine.ProofEngine(False)

    def do_execute(
        self, code, silent, store_history=True, user_expressions=None, allow_stdin=False
    ):

        return_val = "I dunno!"
        if "proof:" in code:
            proof = frog_parser.parse_proof_file(code)
            with io.StringIO() as buffer, redirect_stdout(buffer):
                self.engine.prove(proof)
                return_val = buffer.getvalue()

        elif "Primitive" in code:
            primitive = frog_parser.parse_primitive_file(code)
            self.engine.add_definition(primitive.name, primitive)
            return_val = "Successfully parsed primitive"
        elif "Scheme" in code:
            scheme = frog_parser.parse_scheme_file(code)
            self.engine.add_definition(scheme.name, scheme)
            return_val = "Successfully parsed scheme"
        elif "Game" in code:
            game = frog_parser.parse_game_file(code)
            self.engine.add_definition(game.name, game)
            return_val = "Successfully parsed game"

        if not silent:
            stream_content = {"name": "stdout", "text": return_val}
            self.send_response(self.iopub_socket, "stream", stream_content)

        return {
            "status": "ok",
            # The base class increments the execution count
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }


if __name__ == "__main__":
    from ipykernel.kernelapp import IPKernelApp

    IPKernelApp.launch_instance(kernel_class=FrogKernel)
