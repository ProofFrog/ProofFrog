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
#
# ORPHAN CONTAINERS -- why the deadline lives INSIDE the container.
# Every caller of this script kills only the CLIENT: the MCP server's compile
# tools use `subprocess.run(..., timeout=)` and its REPL tools use
# `pexpect.spawn(..., timeout=)` / `.kill(9)`, and both send SIGKILL. Killing
# `docker run` does not stop the container, and `--rm` only reaps a container
# that EXITS -- so a still-searching EasyCrypt keeps a core at 100% forever. That
# is exactly how four containers accumulated for 12-46 hours, stealing four cores
# from an unattended run. A host-side trap (which is what scripts/easycrypt.sh
# uses) cannot help here, because a trap cannot fire on SIGKILL. So the budget is
# enforced by `timeout` INSIDE the container, which survives losing its client.
# Exit 124 on expiry, the same convention scripts/easycrypt.sh uses, so a timeout
# is never misread as a proof failure. EC_FORK_TIMEOUT=0 disables it.
#
# The container is also NAMED and LABELLED, so any stray is identifiable and
# `docker ps --filter label=ec-fork` sweeps them.

set -euo pipefail

EC_IMAGE="${EC_IMAGE:-easycrypt-fork:local}"
# Generous by default: this is a backstop against a WEDGED container, not a
# per-call budget. Callers that know their own deadline should pass a tighter one
# (the MCP server's compile tools default to 120s).
EC_FORK_TIMEOUT="${EC_FORK_TIMEOUT:-1800}"

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

# Unique, and identifiable in `docker ps` if one ever does escape.
CONTAINER="ecfork-$$-$(date +%s)-$SUBCMD"
CONTAINER="$(printf '%s' "$CONTAINER" | tr -c 'A-Za-z0-9_.-' '_')"

DOCKER_OPTS=(--rm --name "$CONTAINER" --label ec-fork=1 --platform linux/amd64)

# cli mode needs stdin to stay open for the REPL (pexpect drives it).
if [ "$SUBCMD" = "cli" ]; then
    DOCKER_OPTS+=(-i)
fi

if [ -n "$MOUNT_DIR" ]; then
    DOCKER_OPTS+=(-v "$MOUNT_DIR:/work")
fi

exec docker run "${DOCKER_OPTS[@]}" "$EC_IMAGE" \
    bash -c 'eval $(opam env) || exit 1
             t="$1"; shift
             if [ "$t" = 0 ]; then exec easycrypt "$@"; fi
             exec timeout -k 5 "$t" easycrypt "$@"' \
    -- "$EC_FORK_TIMEOUT" "$SUBCMD" ${NEW_ARGS[@]+"${NEW_ARGS[@]}"}
