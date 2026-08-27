#!/usr/bin/env bash
#
# Refresh `results/gh51_e2e_test/monitors` with the `.rvm` files G-PARAM reads.
#
# G-PARAM (`gh105_param_gate`) compares each specification's declared parameters
# against the `.rvm` the generator produced for it. That artifact is not what a
# normal generation leaves behind: `rv-monitor-generator generate` deletes the
# `.rvm` once rv-monitor has consumed them (`runtime_verification_generator.py`,
# `_execute_rvmonitor`), so a monitors directory built the usual way leaves the
# gate comparing nothing -- which it reports as a skip, not as a pass.
#
# What produces them is `javamop -d <out> -merge <specs>/*.mop`. That writes the
# `.rvm` beside the `.mop`, so the run happens over a SCRATCH COPY of the set:
# run against the live directory it leaves `.rvm` files inside
# `rvsec-mop/src/main/resources/jca_android`, which the next `--check` of the
# divergence record reads as untracked additions to the set.
#
# gh109 adds 24 specifications to the set, so this stops being a one-off recipe
# that lives in a test docstring and becomes the thing each group's `X.R` task
# runs before it asserts the gates.
#
# Usage:
#   scripts/gh109_refresh_rvm_fixture.sh [<set directory>]
#
# The set directory defaults to `jca_android` under $RVSEC_HOME.

set -euo pipefail

RVSEC_HOME="${RVSEC_HOME:?RVSEC_HOME must point at the rvsec reactor}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SET_DIR="${1:-$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android}"
JAVAMOP="$RVSEC_HOME/javamop/bin/javamop"
TARGET="$REPO/results/gh51_e2e_test/monitors"

[ -d "$SET_DIR" ] || { echo "no such specification set: $SET_DIR" >&2; exit 1; }
[ -x "$JAVAMOP" ] || { echo "javamop not built or not executable: $JAVAMOP" >&2; exit 1; }

scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT

cp "$SET_DIR"/*.mop "$scratch/"
out="$scratch/out"
mkdir -p "$out"

# `-merge` is the flag the production pipeline uses, so the artifact this fixture
# holds is the one the pipeline would have produced and not a second dialect.
"$JAVAMOP" -d "$out" -merge "$scratch"/*.mop

# The `.rvm` land beside the `.mop` in the scratch copy, not under `-d`.
rvm_count=$(find "$scratch" -maxdepth 1 -name '*.rvm' | wc -l)
mop_count=$(find "$scratch" -maxdepth 1 -name '*.mop' | wc -l)
if [ "$rvm_count" -eq 0 ]; then
    echo "javamop produced no .rvm; the fixture would leave G-PARAM comparing nothing" >&2
    exit 1
fi

mkdir -p "$TARGET"
rm -f "$TARGET"/*.rvm
cp "$scratch"/*.rvm "$TARGET/"

echo "$rvm_count .rvm refreshed in $TARGET (from $mop_count .mop in $SET_DIR)"
if [ "$rvm_count" -ne "$mop_count" ]; then
    echo "warning: $((mop_count - rvm_count)) specification(s) produced no .rvm --" \
         "G-PARAM will skip them; inspect the javamop output above" >&2
fi
