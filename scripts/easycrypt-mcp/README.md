# EasyCrypt fork image for goal inspection

Builds a Docker image with [namasikanam/easycrypt](https://github.com/namasikanam/easycrypt)
on top of `ghcr.io/easycrypt/ec-test-box:release`. The fork adds two flags
that the standard release lacks:

- `-upto LINE[:COL]` — compile up to a position and print goals there.
- `-lastgoals` — print the last unproven goals on failure.

These power [easycrypt-mcp](https://github.com/namasikanam/easycrypt-mcp)
(an MCP server for interactive goal inspection) and the goal-printing
helper script in this repo.

## Build

```sh
cd scripts/easycrypt-mcp
docker build --platform linux/amd64 -t easycrypt-fork:local .
```

The build re-pins the `easycrypt` opam package to the fork's `main` branch
and reinstalls; SMT solvers and `why3` config are inherited from the
upstream test-box so the build is fast (~40s).

## Use

Two convenience wrappers in `scripts/`:

- `easycrypt-fork.sh <file.ec> [opts...]` — drop-in replacement for
  `easycrypt.sh` that runs against the fork image.
- `easycrypt-goals.sh <file.ec> <line>[:<col>]` — print the proof goal
  at a specific position. Useful for figuring out what state you are in
  the middle of a partially-admitted proof.

```sh
# Print goal at line 219 (currently inside an `admit`d lemma)
scripts/easycrypt-goals.sh examples/.../LazyROTwoSeeded.ec 219
```

Override the image tag with `EC_IMAGE=...` if you want to swap in a
different build.

## Why not just the upstream image?

The upstream `ec-test-box` doesn't have `-upto`/`-lastgoals`, and the
`cli` interactive mode is awkward to drive from a script (you have to
pipe the whole proof prelude on stdin and parse `[N|check]>` prompts).
The fork's `llm` subcommand is single-shot: give it a file and a
position, get the goals, exit.
