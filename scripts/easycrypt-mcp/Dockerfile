# EasyCrypt with the namasikanam fork that adds -upto and -lastgoals flags
# (used by easycrypt-mcp: https://github.com/namasikanam/easycrypt-mcp).
#
# Built on top of ghcr.io/easycrypt/ec-test-box:release so we inherit all
# SMT solvers (alt-ergo, cvc4/5, z3) and the why3 detection.

FROM ghcr.io/easycrypt/ec-test-box:release

ARG EC_FORK_URL=https://github.com/namasikanam/easycrypt.git
ARG EC_FORK_REV=main

RUN opam pin remove -n easycrypt 2>/dev/null || true && \
    opam pin add -n easycrypt ${EC_FORK_URL}#${EC_FORK_REV} && \
    opam install -v --confirm-level=unsafe-yes easycrypt && \
    rm -rf .opam/packages.dev/*

# Sanity check that the new flags are available
RUN opam exec -- easycrypt compile --help 2>&1 | grep -qE -- '-(upto|lastgoals)' || \
    (echo "ERROR: expected -upto/-lastgoals flags from the fork are missing" && exit 1)
