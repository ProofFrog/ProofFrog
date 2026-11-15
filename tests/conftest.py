"""Suite-wide test configuration."""

import os

# The verified-hop cache (`prove --cache`, PROOFFROG_HOP_CACHE) skips hops an
# earlier run verified. The test suite must always check every hop, including
# in the `prove` subprocesses it spawns, so a developer's opt-in is dropped
# here. Tests of the cache itself enable it explicitly.
os.environ.pop("PROOFFROG_HOP_CACHE", None)
