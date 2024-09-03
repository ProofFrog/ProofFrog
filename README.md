# ProofFrog
ProofFrog is a work-in-progress tool for verifying cryptographic game-hopping proofs. All security properties in ProofFrog are written via pairs of indistinguishable games. More info can be found on our [wiki](https://prooffrog.github.io/)

## Installation:

```
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt
```

## Commands:

To use the proof engine: `python3 -m proof_frog prove [proof_file]`. The [examples repo](https://github.com/ProofFrog/examples/]) contains a list of examples largely adapated from [The Joy of Cryptography](https://joyofcryptography.com/). See also our [examples page](https://github.com/ProofFrog/examples) on our wiki.

You can also parse any type of file (scheme, proof, game, or primitive) using `python3 -m proof_frog parse [file]`. It will read the file, transform it into an internal AST representation, stringify the representation, and print it back out to the screen.

The bash files `testParsing.sh` ensures that the ANTLR grammar can parse each file in the examples folder. `testAST.sh` parses each file with proof_frog, strips the whitespace, and diffs it with the original file to ensure that the AST output matches the file input. Finally, `testProofs.sh` runs both the suite of examples and the pytest unit tests.

## Jupyter Notebook

We have a custom kernel that allows a user to interact with proof_frog via a Jupyter notebook. To do so, run the following commands from the base directory.

```
docker build -f jupyter/Dockerfile -t proof_frog .
docker run -p 8888:8888 proof_frog
```

The output from the `docker run` command will contain a `localhost:8888` URL containing a token that will allow you to view the jupyter notebook.

# Acknowledgements
<img src="media/NSERC.jpg" alt="NSERC signature" width="750"/> 

We acknowledge the support of the Natural Sciences and Engineering Research Council of Canada (NSERC).

Nous remercions le Conseil de recherches en sciences naturelles et en génie du Canada (CRSNG) de son soutien.
