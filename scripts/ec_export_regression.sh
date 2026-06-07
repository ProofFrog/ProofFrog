#!/usr/bin/env bash
#
# Fast EC-exporter regression check: "did my uncommitted change alter any
# exported .ec, and which ones?"
#
# Why it's fast:
#  * SCOPE -- a change confined to the EasyCrypt exporter
#    (proof_frog/export/easycrypt/) can only affect proofs that actually EXPORT.
#    The ~60 proofs that fail before chain emission (type/skeleton/import errors,
#    FailedProof engine runs) are untouched, and several are the slowest things
#    in the corpus. So the regression surface is just the ~44 exporting proofs.
#  * PARALLELISM -- exports run concurrently (xargs -P). The engine itself is
#    forced sequential (PROOFFROG_SEQUENTIAL=1), but the proofs are independent
#    processes, so on a 12-core box the sweep is ~35s vs several MINUTES for a
#    sequential full-corpus run.
#
# It diffs the working tree against the committed (HEAD) baseline. The baseline
# is built once per HEAD SHA by stashing your proof_frog changes, exporting, and
# restoring (cached afterward, so iteration runs don't re-stash). Editable
# install: PYTHONPATH can't shadow proof_frog, so a stash -- not a worktree -- is
# how we get HEAD's code.
#
# Usage:   extras/scripts/ec_export_regression.sh
# Env:     PF_PARALLEL  xargs parallelism (default 10)
#          PF_WORK      scratch dir (default $TMPDIR/ec_regress)
#
# After it lists the changed proofs, compile JUST those in EasyCrypt
# (mcp ec_compile, or scripts/easycrypt.sh). Byte-identical exports are
# guaranteed to compile identically, so only the changed ones need EC.
#
# This does NOT replace the targeted test run. For an exporter change also run
# (NOT the full suite -- test_proofs.py is ~9min of engine runs, irrelevant):
#   pytest tests/unit/export tests/integration/test_easycrypt_export.py \
#          tests/integration/test_tactic_cache_orphan_check.py
set -euo pipefail

# This script lives at <ProofFrog>/scripts/; resolve the repo root by path.
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
PY="$REPO/.venv/bin/python"
P="${PF_PARALLEL:-10}"
WORK="${PF_WORK:-${TMPDIR:-/tmp}/ec_regress}"
BSHA="$(git rev-parse --short HEAD)"
BASE_DIR="$WORK/baseline-$BSHA"
NEW_DIR="$WORK/worktree"
LIST="$WORK/export_list-$BSHA.txt"
mkdir -p "$WORK"

# One proof export; reads OUT, PY from the environment. macOS xargs -I has a
# tiny per-command buffer, so keep the xargs command short (exported function).
_ec_export_one() {
  local p="$1" rel
  rel="${p//\//__}"
  if PROOFFROG_SEQUENTIAL=1 timeout 120 \
       "$PY" -m proof_frog export "$p" -o "$OUT/$rel.ec" >/dev/null 2>&1 \
     && [ -f "$OUT/$rel.ec" ]; then
    echo "OK $(shasum "$OUT/$rel.ec" | cut -d' ' -f1) $p"
  else
    echo "FAIL - $p"
  fi
}
export -f _ec_export_one

sweep() {  # $1=outdir  $2=proof-list
  local out="$1" list="$2"
  mkdir -p "$out"
  OUT="$out" PY="$PY" \
    xargs -P "$P" -I{} <"$list" bash -c '_ec_export_one "$@"' _ {} \
    | sort > "$out/_results.txt"
}

# 1. Build the HEAD baseline once per SHA (cached). Stash proof_frog changes so
#    the export reflects committed code; a trap guarantees they're restored.
if [[ ! -s "$LIST" || ! -s "$BASE_DIR/_results.txt" ]]; then
  stashed=0
  if ! git diff --quiet -- proof_frog; then
    echo ">> stashing working proof_frog changes to build the HEAD baseline ..." >&2
    git stash push -q -m "ec_export_regression-baseline" -- proof_frog
    stashed=1
    # shellcheck disable=SC2064
    trap 'if [[ "${stashed:-0}" == 1 ]]; then echo ">> RESTORING stashed proof_frog changes" >&2; git stash pop -q || echo "!! git stash pop FAILED -- recover with: git stash pop"; fi' EXIT INT TERM
  fi
  echo ">> building baseline at HEAD ($BSHA) ..." >&2
  find examples -name '*.proof' | sort > "$WORK/_all_proofs.txt"
  sweep "$BASE_DIR" "$WORK/_all_proofs.txt"
  if [[ "$stashed" == 1 ]]; then
    git stash pop -q
    stashed=0
    trap - EXIT INT TERM
  fi
  awk '$1=="OK"{print $3}' "$BASE_DIR/_results.txt" > "$LIST"
  echo ">> $(wc -l < "$LIST") proofs export at baseline (cached for SHA $BSHA)" >&2
fi

# 2. Export the same set from the working tree (the change under test).
echo ">> exporting working tree ..." >&2
sweep "$NEW_DIR" "$LIST"

# 3. Diff hashes.
"$PY" - "$BASE_DIR/_results.txt" "$NEW_DIR/_results.txt" <<'PYEOF'
import sys
def load(p):
    d = {}
    for line in open(p):
        a = line.split()
        if len(a) >= 3:
            d[a[2]] = (a[0], a[1])
    return d
base, new = load(sys.argv[1]), load(sys.argv[2])
changed = []
for k in sorted(set(base) & set(new)):
    if base[k] != new[k]:
        changed.append((k, base[k][0], new[k][0]))
if not changed:
    print("OK: no export changed vs baseline (working tree == HEAD for all exports).")
else:
    print(f"{len(changed)} export(s) changed vs HEAD:")
    for k, b, n in changed:
        tag = "" if b == n == "OK" else f"  [{b} -> {n}]"
        print(f"  {k}{tag}  -> compile this one in EasyCrypt (ec_compile)")
PYEOF
