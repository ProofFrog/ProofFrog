#!/usr/bin/env bash
# Print EasyCrypt proof goals at a given line/col using the namasikanam fork.
#
# Usage: scripts/easycrypt-goals.sh <file.ec> <line>[:<col>]
#
# Example:
#   scripts/easycrypt-goals.sh examples/.../LazyROTwoSeeded.ec 219
#
# Build the fork image first:
#   (cd scripts/easycrypt-mcp && docker build --platform linux/amd64 -t easycrypt-fork:local .)

set -euo pipefail

EC_IMAGE="${EC_IMAGE:-easycrypt-fork:local}"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <file.ec> <line>[:<col>]" >&2
    exit 1
fi

FILE_ARG="$1"
POS="$2"

FILE_ABS="$(cd "$(dirname "$FILE_ARG")" && pwd)/$(basename "$FILE_ARG")"
DIR="$(dirname "$FILE_ABS")"
BASENAME="$(basename "$FILE_ABS")"

docker run --rm --platform linux/amd64 \
    -v "$DIR":/work \
    "$EC_IMAGE" \
    bash -c 'eval $(opam env) && exec easycrypt llm "$1" -upto "$2"' \
    -- "/work/$BASENAME" "$POS"
