# ProofFrog
A work in progress

## Installation:

```
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt
```

## Commands:

To use the proof engine: `python3 proof_frog prove [proof_file]`. As of right now, the only proofs working are 'examples/Proofs/SymEnc/OTUC=>OTS.proof' and 'examples/Proofs/SymEnc/CPA$=>CPA.proof'.

You can also parse any type of file (scheme, proof, game, or primitive) using `python3 proof_frog parse [file]`. It will read the file, transform it into an internal AST representation, stringify the representation, and print it back out to the screen.

The bash files `testParsing.sh` ensures that the ANTLR grammar can parse each file in the examples folder. `testAST.sh` parses each file with proof_frog, strips the whitespace, and diffs it with the original file to ensure that the AST output matches the file input.

## Jupyter Notebook

We have a custom kernel that allows a user to interact with proof_frog via a Jupyter notebook. To do so, run the following commands from the base directory.

```
docker build -f jupyter/Dockerfile -t proof_frog .
docker run -p 8888:8888 proof_frog
```

The output from the `docker run` command will contain a `localhost:8888` URL containing a token that will allow you to view the jupyter notebook.
