#!/usr/bin/env bash
# Run an EasyCrypt file through the EasyCrypt Docker image.
# Usage: scripts/easycrypt.sh <file.ec> [easycrypt-options...]
#
# The file path may be absolute or relative to the current directory.
# Any extra arguments are forwarded to the easycrypt command.
#
# WALL-CLOCK BUDGET. The compile is bounded by EC_TIMEOUT seconds (default
# below); on expiry the container is killed and the script exits 124, the same
# code `timeout(1)` uses. Set EC_TIMEOUT=0 to disable the bound.
#
# Two defects motivated this, both observed: a wedged compile ran for 15 HOURS
# because nothing bounded it, and killing the *client* does not stop the
# container -- `docker run` without a name leaves an orphan holding a CPU. So the
# container is named and killed from a trap as well as from the budget. Note the
# trap cannot fire on SIGKILL: a caller that enforces its own deadline with
# `subprocess.run(timeout=...)` (which sends SIGKILL) still needs EC_TIMEOUT here
# to be the SHORTER of the two, or it will leak a container.
#
# The bound is deliberately generous. The slowest CFRG export compiles in well
# under a minute unloaded and a few minutes under load; anything approaching the
# default is wedged, not slow. It is a backstop, not a scheduling knob -- if you
# need many compiles at once, limit CONCURRENCY, because the trigger here was
# oversubscription (four EasyCrypt containers plus a test suite on one box).

set -euo pipefail

EC_IMAGE="ghcr.io/easycrypt/ec-test-box:release"
EC_TIMEOUT="${EC_TIMEOUT:-1800}"

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

# Unique, and identifiable in `docker ps` if one ever does escape.
CONTAINER="ec-$$-$(date +%s)-${BASENAME%.ec}"
CONTAINER="$(printf '%s' "$CONTAINER" | tr -c 'A-Za-z0-9_.-' '_')"

cleanup() { docker kill "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup INT TERM

docker run --rm --name "$CONTAINER" --platform linux/amd64 \
    -v "$DIR":/work \
    "$EC_IMAGE" \
    bash -c 'eval $(opam env) && exec easycrypt compile "$@"' -- "/work/$BASENAME" "$@" &
ec_pid=$!

if [ "$EC_TIMEOUT" != "0" ]; then
    elapsed=0
    while kill -0 "$ec_pid" 2>/dev/null; do
        sleep 5
        elapsed=$((elapsed + 5))
        # Re-test liveness BEFORE declaring a timeout. A compile that finishes
        # during the sleep window would otherwise be reported as 124 -- a false
        # timeout on a run that actually succeeded, which is worse than no bound
        # at all because it looks like a hang.
        kill -0 "$ec_pid" 2>/dev/null || break
        if [ "$elapsed" -ge "$EC_TIMEOUT" ]; then
            cleanup
            wait "$ec_pid" 2>/dev/null || true
            echo "easycrypt.sh: TIMEOUT after ${EC_TIMEOUT}s on $BASENAME" \
                 "(container killed; raise EC_TIMEOUT or set it to 0 to disable)" >&2
            exit 124
        fi
    done
fi

# `set -e` must not pre-empt the explicit exit code -- a nonzero EasyCrypt status
# is a normal, reportable outcome here, not a script error.
rc=0
wait "$ec_pid" || rc=$?
trap - INT TERM
exit "$rc"
