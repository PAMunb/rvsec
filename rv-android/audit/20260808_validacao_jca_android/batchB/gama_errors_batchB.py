#!/usr/bin/env python3
"""GAMA batch B - errors.csv stratification restricted to the five batch-B specs.

Freeze-first: aborts unless sha256 of errors.csv equals the manifest hash.
All counts reported in FOUR separate units: lines / unique_msg / APKs / sites.
PRE-GH100/GH101 data: hypothesis generator ONLY (protocol section 12).
"""
import csv
import hashlib
import sys
from collections import defaultdict

CSV_PATH = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv"
EXPECTED_SHA = "78023defec078353bbd1f64331edb7992a2c34e29570e6ceb064fb57f37dea69"

BATCH_B_SPECS = [
    "CipherInputStreamSpec",
    "CipherOutputStreamSpec",
    "KeyPairSpec",
    "SecretKeySpec",       # spec name as declared (target class javax.crypto.SecretKey)
    "PBEKeySpecSpec",
]
# class-name tokens of the five monitored classes (+ the KeyPair generator flow,
# reported separately so KeyPair != KeyPairGenerator is never conflated)
TOKENS = [
    "CipherInputStream",
    "CipherOutputStream",
    "KeyPair",            # matches KeyPairGenerator too -> refined below
    "SecretKey",          # matches SecretKeySpec(Spec) too -> refined below
    "PBEKeySpec",
    "getPublic",
    "getPrivate",
    "getEncoded",
    "clearPassword",
]

h = hashlib.sha256()
with open(CSV_PATH, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
digest = h.hexdigest()
print(f"sha256(errors.csv) = {digest}")
if digest != EXPECTED_SHA:
    print("FREEZE CHECK FAILED - aborting before any read")
    sys.exit(1)
print("freeze check PASS (== fase0 manifest)\n")

rows = []
with open(CSV_PATH, newline="") as f:
    r = csv.DictReader(f)
    fields = r.fieldnames
    for row in r:
        rows.append(row)
print(f"schema: {fields}")
print(f"data lines total: {len(rows)}")

# global four units (sanity vs pilot)
u_lines = len(rows)
u_umsg = len({row["unique_msg"] for row in rows})
u_apks = len({row["apk"] for row in rows})
u_sites = len({(row["apk"], row["class"], row["method"], row["spec"]) for row in rows})
u_exec = len({(row["apk"], row["rep"], row["timeout"], row["tool"]) for row in rows})
print(f"global units: lines={u_lines} unique_msg={u_umsg} apks={u_apks} "
      f"sites={u_sites} executions={u_exec} (pilot: 97018/225/113/454/8147)\n")

print("=" * 78)
print("A. Per batch-B spec (unit: lines / unique_msg / APKs / sites)")
print("=" * 78)
for spec in BATCH_B_SPECS:
    sel = [row for row in rows if row["spec"] == spec]
    lines = len(sel)
    umsg = len({row["unique_msg"] for row in sel})
    apks = len({row["apk"] for row in sel})
    sites = len({(row["apk"], row["class"], row["method"]) for row in sel})
    print(f"{spec:26s} lines={lines:6d} unique_msg={umsg:3d} apks={apks:3d} sites={sites:3d}")

print()
print("=" * 78)
print("B. KeyPairSpec deep stratification (the only non-zero batch-B spec)")
print("=" * 78)
kpr = [row for row in rows if row["spec"] == "KeyPairSpec"]
if kpr:
    # unique_msg = class:::method:::spec:::error_type:::message
    def um(row):
        return row["unique_msg"].split(":::")

    by_cat = defaultdict(lambda: [0, set(), set(), set()])
    for row in kpr:
        parts = um(row)
        et = parts[3] if len(parts) == 5 else "MALFORMED"
        agg = by_cat[et]
        agg[0] += 1
        agg[1].add(row["unique_msg"])
        agg[2].add(row["apk"])
        agg[3].add((row["apk"], row["class"], row["method"]))
    print("\nB.1 by error_type (lines/unique_msg/apks/sites):")
    for et, agg in sorted(by_cat.items()):
        print(f"  {et:32s} {agg[0]:6d} / {len(agg[1]):3d} / {len(agg[2]):3d} / {len(agg[3]):3d}")

    print("\nB.2 by message literal (field 5 of unique_msg) (lines/apks/sites):")
    by_msg = defaultdict(lambda: [0, set(), set()])
    for row in kpr:
        parts = um(row)
        msg = parts[4] if len(parts) == 5 else "MALFORMED"
        agg = by_msg[msg]
        agg[0] += 1
        agg[1].add(row["apk"])
        agg[2].add((row["apk"], row["class"], row["method"]))
    for msg, agg in sorted(by_msg.items(), key=lambda kv: -kv[1][0]):
        print(f"  {agg[0]:6d} lines / {len(agg[1]):2d} apks / {len(agg[2]):2d} sites : {msg!r}")

    print("\nB.3 sites (apk :: class :: method) with lines and error_types:")
    by_site = defaultdict(lambda: [0, set()])
    for row in kpr:
        parts = um(row)
        et = parts[3] if len(parts) == 5 else "MALFORMED"
        key = (row["apk"], row["class"], row["method"])
        by_site[key][0] += 1
        by_site[key][1].add(et)
    for (apk, cl, me), (n, ets) in sorted(by_site.items(), key=lambda kv: -kv[1][0]):
        print(f"  {n:6d}  {apk}  {cl}:::{me}  {sorted(ets)}")

    print("\nB.4 by tool (lines / executions with >=1 KPR line):")
    by_tool = defaultdict(lambda: [0, set()])
    for row in kpr:
        by_tool[row["tool"]][0] += 1
        by_tool[row["tool"]][1].add((row["apk"], row["rep"], row["timeout"]))
    for tool, (n, execs) in sorted(by_tool.items(), key=lambda kv: -kv[1][0]):
        print(f"  {tool:22s} {n:6d} lines / {len(execs):3d} apk-rep-timeout cells")

    # H2 pairing test at execution x site granularity, restricted to KeyPairSpec
    print("\nB.5 H2 pairing (cells (apk,rep,timeout,tool,class,method)):")
    cells = defaultdict(set)
    for row in kpr:
        parts = um(row)
        et = parts[3] if len(parts) == 5 else "MALFORMED"
        cells[(row["apk"], row["rep"], row["timeout"], row["tool"],
               row["class"], row["method"])].add(et)
    both = sum(1 for ets in cells.values()
               if "InvalidSequenceOfMethodCalls" in ets and len(ets) > 1)
    only_seq = sum(1 for ets in cells.values() if ets == {"InvalidSequenceOfMethodCalls"})
    only_specific = sum(1 for ets in cells.values()
                        if "InvalidSequenceOfMethodCalls" not in ets)
    print(f"  cells total={len(cells)} both-specific-and-InvalidSeq={both} "
          f"only-InvalidSeq={only_seq} only-specific={only_specific}")

    # H4 empty label
    h4 = [row for row in kpr if "but found ." in row["unique_msg"] or row["message"].strip().endswith("but found .")]
    print(f"\nB.6 H4 'but found .' lines within KeyPairSpec: {len(h4)}")

    # message column == unknown share
    unk = sum(1 for row in kpr if row["message"] == "unknown")
    print(f"B.7 message=='unknown' lines: {unk}/{len(kpr)}")

print()
print("=" * 78)
print("C. Token scan over ALL fields of ALL 97,018 lines (lines/apks per token)")
print("=" * 78)
tok_lines = {t: 0 for t in TOKENS}
tok_apks = {t: set() for t in TOKENS}
tok_specs = {t: defaultdict(int) for t in TOKENS}
for row in rows:
    blob = ",".join(row.values())
    for t in TOKENS:
        if t in blob:
            tok_lines[t] += 1
            tok_apks[t].add(row["apk"])
            tok_specs[t][row["spec"]] += 1
for t in TOKENS:
    print(f"  {t:20s} lines={tok_lines[t]:6d} apks={len(tok_apks[t]):3d} "
          f"specs={dict(tok_specs[t])}")

# refine: 'KeyPair' excluding 'KeyPairGenerator'; 'SecretKey' excluding 'SecretKeySpec'
def refined(token, excl):
    n = 0
    apks = set()
    for row in rows:
        blob = ",".join(row.values())
        if token in blob and token in blob.replace(excl, ""):
            n += 1
            apks.add(row["apk"])
    return n, len(apks)

n, a = refined("KeyPair", "KeyPairGenerator")
print(f"\n  'KeyPair' with 'KeyPairGenerator' occurrences removed: lines={n} apks={a}")
n, a = refined("SecretKey", "SecretKeySpec")
print(f"  'SecretKey' with 'SecretKeySpec' occurrences removed:  lines={n} apks={a}")
