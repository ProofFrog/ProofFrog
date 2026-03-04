# ProofFrog

ProofFrog is a work-in-progress tool for verifying game transitions in cryptographic game-hopping proofs. All security properties in ProofFrog are written via pairs of indistinguishable games. More info can be found on [the ProofFrog website](https://prooffrog.github.io/)

## Installation

There are two ways of installing ProofFrog: from the published Python package, or by cloning the ProofFrog repository and running that version. If you want the latest features of ProofFrog, you should use the second approach.

### From PyPI (recommended)

Install ProofFrog into a virtual environment:

```
python3 -m venv .venv
source .venv/bin/activate
pip install proof_frog
```

Once installed, the `proof_frog` command is available directly:

```
proof_frog web examples/ # or whatever other directory you want
proof_frog prove [proof_file]
```

### From source (local development)

Clone the repository and install in editable mode:

```
git clone https://github.com/ProofFrog/ProofFrog
cd ProofFrog
git checkout ds-web # currently the main dev branch
git submodule update --init
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

Run commands via the module:

```
proof_frog web examples/ # or whatever other directory you want
python3 -m proof_frog prove [proof_file]
```

## Web Interface

ProofFrog includes a browser-based editor for interactively editing and verifying proof files.

```
proof_frog web [directory]
```

This starts a local web server (default port 5173) and opens the interface in your browser. The `[directory]` argument specifies the working directory for proof files; it defaults to the current directory. From the interface you can browse, edit, parse, and prove files without using the command line.

## Command-Line Interface

To use the proof engine, run `proof_frog prove [proof_file]` (PyPI install) or `python3 -m proof_frog prove [proof_file]` (local install). The [examples repo](https://github.com/ProofFrog/examples/) contains a list of examples largely adapted from [The Joy of Cryptography](https://joyofcryptography.com/). See also the [examples and tutorials on our website](https://prooffrog.github.io/).

You can also parse any type of file (scheme, proof, game, or primitive) using `proof_frog parse [file]`. It will read the file, transform it into an internal AST representation, stringify the representation, and print it back out to the screen.

<!-- ## Jupyter Notebook

We have a custom kernel that allows a user to interact with proof_frog via a Jupyter notebook. To do so, run the following commands from the base directory.

```
docker build -f jupyter/Dockerfile -t proof_frog .
docker run -p 8888:8888 proof_frog
```

The output from the `docker run` command will contain a `localhost:8888` URL containing a token that will allow you to view the jupyter notebook. -->

## Plugin for JetBrains IDE-s

There's a plugin available for JetBrains IDE-s which provides syntax validation and highlighting, custom color settings, 
import statement file path references, context-menu actions and other features for the ProofFrog language. 
You can obtain the plugin from the JetBrains Marketplace inside the IDE. 
The project is hosted in [this GitHub repository](https://github.com/aabmets/proof-frog-ide-plugin).


# Acknowledgements
<img src="media/NSERC.jpg" alt="NSERC signature" width="750"/> 

We acknowledge the support of the Natural Sciences and Engineering Research Council of Canada (NSERC).

Nous remercions le Conseil de recherches en sciences naturelles et en génie du Canada (CRSNG) de son soutien.
