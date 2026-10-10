#!/usr/bin/env bash
# Pairs of units whose source changed in the same commit, as a volatility signal.
#
#   bash .claude/skills/rv-analyze-dependencies/scripts/cochange.sh [since] [min_pairs]
#   (defaults: "6 months ago", 3)
#
# A unit is a uv workspace module (rv-android/modules/<m>/.../src/) or a Java module of the
# parent rvsec repository (java:<m>, from src/main/ of rvsec/rvsec-*, rvsec/rvsec-android/*,
# javamop, rv-monitor). Reading the whole parent repository is the point: a GATOR or JavaMOP
# change that forces a Python change shows up here and nowhere in the import graph.
#
# Only source paths count (docs, tests and pyproject bumps would pair everything with
# everything), and commits touching more than 8 units are skipped as bulk edits.
#
# Output: <co-changes> <share> <unit-a> <-> <unit-b>, where share is co-changes divided by
# the commit count of the less active unit of the pair (100% = it never changed alone).
set -euo pipefail

since="${1:-6 months ago}"
min="${2:-3}"
prefix="$(git rev-parse --show-prefix)"

git -C "$(git rev-parse --show-toplevel)" log --since="$since" --no-merges \
    --format='format:@' --name-only |
awk -v pre="$prefix" -v min="$min" '
function unit(f,  p) {
  split(f, p, "/")
  if (index(f, pre "modules/") == 1 && f ~ /\/src\//) {
    sub("^" pre "modules/", "", f); split(f, p, "/"); return p[1]
  }
  if (f ~ /^rvsec\/rvsec-android\/[^\/]+\/.*src\/main\//) return "java:" p[3]
  if (f ~ /^rvsec\/rvsec-[^\/]+\/.*src\/main\//)          return "java:" p[2]
  if (f ~ /^(javamop|rv-monitor)\/.*src\/main\//)          return "java:" p[1]
  return ""
}
function flush(  a, b, k) {
  k = 0; for (a in s) k++
  if (k <= 8) for (a in s) { n[a]++; for (b in s) if (a < b) pair[a " " b]++ }
  delete s
}
/^@/ { flush(); next }
NF   { u = unit($0); if (u != "") s[u] = 1 }
END {
  flush()
  for (k in pair) {
    split(k, m, " "); lo = n[m[1]] < n[m[2]] ? n[m[1]] : n[m[2]]
    if (pair[k] >= min) printf "%4d %4.0f%%  %s <-> %s\n", pair[k], 100 * pair[k] / lo, m[1], m[2]
  }
}' | sort -rn
