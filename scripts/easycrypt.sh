#!/usr/bin/env bash
# Run an EasyCrypt file through the EasyCrypt Docker image.
# Usage: scripts/easycrypt.sh <file.ec> [easycrypt-options...]
#
# The file path may be absolute or relative to the current directory.
# Any extra arguments are forwarded to the easycrypt command.

set -euo pipefail

EC_IMAGE="ghcr.io/easycrypt/ec-test-box:release"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <file.ec> [easycrypt-options...]" >&2
    exit 1
fi

FILE_ARG="$1"
shift

# Resolve to absolute path
FILE_ABS="$(cd "$(dirname "$FILE_ARG")" && pwd)/$(basename "$FILE_ARG")"
DIR="$(dirname "$FILE_ABS")"
BASENAME="$(basename "$FILE_ABS")"

docker run --rm --platform linux/amd64 \
    -v "$DIR":/work \
    "$EC_IMAGE" \
    bash -c 'eval $(opam env) && exec easycrypt compile "$@"' -- "/work/$BASENAME" "$@"
