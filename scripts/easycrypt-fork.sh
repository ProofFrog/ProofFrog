#!/usr/bin/env bash
# Run the namasikanam/easycrypt fork in a Docker container.
# Generic pass-through: forwards any subcommand (compile, cli, llm, ...)
# and arguments to the binary. File arguments that exist on the host are
# auto-mounted into /work in the container.
#
# Usage:
#   scripts/easycrypt-fork.sh compile [opts...] <file.ec>
#   scripts/easycrypt-fork.sh llm <file.ec> -upto <line>
#   scripts/easycrypt-fork.sh cli                           # interactive REPL
#
# Build the image first:
#   (cd scripts/easycrypt-mcp && docker build --platform linux/amd64 -t easycrypt-fork:local .)

set -euo pipefail

EC_IMAGE="${EC_IMAGE:-easycrypt-fork:local}"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <subcommand> [args...]" >&2
    echo "       $0 <file.ec>            (legacy: implies compile)" >&2
    exit 1
fi

# If the first argument is a file, treat as legacy: scripts/easycrypt-fork.sh <file> [opts]
# becomes scripts/easycrypt-fork.sh compile <file> [opts].
if [ -f "$1" ] && [[ "$1" != -* ]]; then
    set -- compile "$@"
fi

SUBCMD="$1"
shift

# Walk the remaining args. The first one that exists as a file on the host
# determines what directory to mount as /work. Replace its path with the
# in-container path.
NEW_ARGS=()
MOUNT_DIR=""
for arg in "$@"; do
    if [ -z "$MOUNT_DIR" ] && [ -f "$arg" ]; then
        FILE_ABS="$(cd "$(dirname "$arg")" && pwd)/$(basename "$arg")"
        MOUNT_DIR="$(dirname "$FILE_ABS")"
        NEW_ARGS+=("/work/$(basename "$FILE_ABS")")
    else
        NEW_ARGS+=("$arg")
    fi
done

DOCKER_OPTS=(--rm --platform linux/amd64)

# cli mode needs stdin to stay open for the REPL (pexpect drives it).
if [ "$SUBCMD" = "cli" ]; then
    DOCKER_OPTS+=(-i)
fi

if [ -n "$MOUNT_DIR" ]; then
    DOCKER_OPTS+=(-v "$MOUNT_DIR:/work")
fi

exec docker run "${DOCKER_OPTS[@]}" "$EC_IMAGE" \
    bash -c 'eval $(opam env) && exec easycrypt "$@"' -- "$SUBCMD" ${NEW_ARGS[@]+"${NEW_ARGS[@]}"}
