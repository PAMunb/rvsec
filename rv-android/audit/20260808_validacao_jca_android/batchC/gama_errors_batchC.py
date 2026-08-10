#!/usr/bin/env python3
"""GAMA batch C - errors.csv stratification (KGN, KMF, TMF, SSL, KST).

Freeze-checked hypothesis generator ONLY (pre-GH100/GH101 data).
Units always separated: lines != unique_msg != APKs != sites (protocol section 12).
"""
import csv
import hashlib
import sys
from collections import Counter, defaultdict

CSV = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv"
EXPECTED_SHA = "78023defec078353bbd1f64331edb7992a2c34e29570e6ceb064fb57f37dea69"

h = hashlib.sha256()
with open(CSV, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
digest = h.hexdigest()
if digest != EXPECTED_SHA:
    print(f"ABORT: sha256 mismatch {digest}")
    sys.exit(1)
print(f"freeze check PASS sha256={digest}")

SPECS = ["KeyGeneratorSpec", "KeyManagerFactorySpec", "TrustManagerFactorySpec",
         "SSLContextSpec", "KeyStoreSpec"]

rows = []
with open(CSV, newline="") as f:
    r = csv.DictReader(f)
    for row in r:
        rows.append(row)
print(f"total data lines: {len(rows)}")

def etype(row):
    parts = row["unique_msg"].split(":::")
    return parts[3] if len(parts) == 5 else "MALFORMED"

def msg(row):
    parts = row["unique_msg"].split(":::")
    return parts[4] if len(parts) == 5 else row["message"]

# A. Global sanity (must match pilot)
print("\n== A. global units ==")
print("lines", len(rows))
print("unique_msg", len({r['unique_msg'] for r in rows}))
print("APKs", len({r['apk'] for r in rows}))
print("sites", len({(r['apk'], r['class'], r['method'], r['spec']) for r in rows}))
print("executions", len({(r['apk'], r['rep'], r['timeout'], r['tool']) for r in rows}))

# B. Per-spec four units + categories
print("\n== B. batch C per-spec strata ==")
for s in SPECS:
    sr = [r for r in rows if r["spec"] == s]
    print(f"\n--- {s} ---")
    print("lines", len(sr),
          "| unique_msg", len({r['unique_msg'] for r in sr}),
          "| APKs", len({r['apk'] for r in sr}),
          "| sites", len({(r['apk'], r['class'], r['method']) for r in sr}))
    if not sr:
        continue
    cat = Counter(etype(r) for r in sr)
    print("categories (lines):", dict(cat))
    for c in cat:
        cs = [r for r in sr if etype(r) == c]
        print(f"  {c}: unique_msg={len({r['unique_msg'] for r in cs})} "
              f"APKs={len({r['apk'] for r in cs})} "
              f"sites={len({(r['apk'], r['class'], r['method']) for r in cs})}")
    unk = sum(1 for r in sr if r["message"] == "unknown")
    print("message=='unknown' lines:", unk, f"({100*unk/len(sr):.1f}%)")
    # empty 'but found' label
    empty = [r for r in sr if "but found ." in msg(r)]
    print("'but found .' (empty label) lines:", len(empty),
          "| unique_msg", len({r['unique_msg'] for r in empty}),
          "| APKs", len({r['apk'] for r in empty}),
          "| sites", len({(r['apk'], r['class'], r['method']) for r in empty}))
    # non-empty specific labels
    lits = Counter(msg(r) for r in sr if etype(r) != "InvalidSequenceOfMethodCalls")
    print("top specific-message literals:")
    for m, n in lits.most_common(8):
        print(f"   {n:6d}  {m[:110]}")

# C. Pairing cells: execution x site cells having BOTH a specific category and InvalidSeq
print("\n== C. pairing (specific + InvalidSeq) per execution x site cell ==")
for s in SPECS:
    sr = [r for r in rows if r["spec"] == s]
    if not sr:
        print(f"{s}: no lines")
        continue
    cells = defaultdict(set)
    for r in sr:
        cells[(r['apk'], r['rep'], r['timeout'], r['tool'], r['class'], r['method'])].add(etype(r))
    both = sum(1 for v in cells.values()
               if "InvalidSequenceOfMethodCalls" in v and len(v) > 1)
    only_generic = sum(1 for v in cells.values() if v == {"InvalidSequenceOfMethodCalls"})
    only_specific = sum(1 for v in cells.values() if "InvalidSequenceOfMethodCalls" not in v)
    print(f"{s}: cells={len(cells)} both={both} only_generic={only_generic} only_specific={only_specific}")

# D. TMF deep stratification (pilot H2 headline)
print("\n== D. TMF deep dive ==")
tmf = [r for r in rows if r["spec"] == "TrustManagerFactorySpec"]
print("per-tool lines:", dict(Counter(r['tool'] for r in tmf)))
print("top sites (apk|class|method, lines):")
for k, n in Counter((r['apk'], r['class'], r['method']) for r in tmf).most_common(10):
    print(f"   {n:6d}  {k[0][:40]} | {k[1][:50]} | {k[2]}")
ua = [r for r in tmf if etype(r) == "UnsafeAlgorithm"]
print("UnsafeAlgorithm literals:", dict(Counter(msg(r) for r in ua)))

# E. SSL deep dive
print("\n== E. SSLContextSpec deep dive ==")
ssl = [r for r in rows if r["spec"] == "SSLContextSpec"]
up = [r for r in ssl if etype(r) == "UnsafeProtocol"]
print("UnsafeProtocol literals (top 10):")
for m, n in Counter(msg(r) for r in up).most_common(10):
    print(f"   {n:6d}  {m[:110]}")

# F. KST deep dive
print("\n== F. KeyStoreSpec deep dive ==")
kst = [r for r in rows if r["spec"] == "KeyStoreSpec"]
it = [r for r in kst if etype(r) == "InvalidKeyStoreType"]
print("InvalidKeyStoreType literals:", dict(Counter(msg(r) for r in it)))
print("KST top sites:")
for k, n in Counter((r['apk'], r['class'], r['method']) for r in kst).most_common(8):
    print(f"   {n:6d}  {k[0][:40]} | {k[1][:50]} | {k[2]}")

# G. zero-line specs of the batch: token search across all fields
print("\n== G. token search for zero-line specs ==")
for tok in ["KeyGenerator", "KeyManagerFactory"]:
    n = sum(1 for r in rows if any(tok in (r[c] or "") for c in r))
    specn = sum(1 for r in rows if tok + "Spec" == r["spec"])
    print(f"token '{tok}': lines with token anywhere={n}; spec=={tok}Spec lines={specn}")
