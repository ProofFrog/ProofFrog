import io
from contextlib import redirect_stdout, redirect_stderr
from ipykernel.kernelbase import Kernel
from antlr4 import error
from proof_frog import proof_engine
from proof_frog import frog_parser
from proof_frog import frog_ast


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

        def send_output(output: str) -> None:
            stream_content = {"name": "stdout", "text": output}
            self.send_response(self.iopub_socket, "stream", stream_content)

        def parse(code: str, file_type: frog_ast.FileType):
            with io.StringIO() as buffer, redirect_stderr(buffer):
                try:
                    match file_type:
                        case frog_ast.FileType.PRIMITIVE:
                            return frog_parser.parse_primitive_file(code)
                        case frog_ast.FileType.SCHEME:
                            return frog_parser.parse_scheme_file(code)
                        case frog_ast.FileType.GAME:
                            return frog_parser.parse_game_file(code)
                        case frog_ast.FileType.PROOF:
                            return frog_parser.parse_proof_file(code)
                except error.Errors.ParseCancellationException:
                    send_output(f"Failed to parse\n{buffer.getvalue()}")
            return None

        file_type: frog_ast.FileType
        if "proof:" in code:
            file_type = frog_ast.FileType.PROOF
        elif "Primitive" in code:
            file_type = frog_ast.FileType.PRIMITIVE
        elif "Scheme" in code:
            file_type = frog_ast.FileType.SCHEME
        elif "Game" in code:
            file_type = frog_ast.FileType.GAME

        parsed_file = parse(code, file_type)
        if not parsed_file:
            return

        if file_type == frog_ast.FileType.PROOF:
            with io.StringIO() as buffer, redirect_stdout(buffer):
                try:
                    self.engine.prove(parsed_file)
                except proof_engine.FailedProof:
                    pass
                send_output(buffer.getvalue())
        else:
            self.engine.add_definition(parsed_file.name, parsed_file)
            send_output(f"Successfully parsed {file_type.value}")

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
