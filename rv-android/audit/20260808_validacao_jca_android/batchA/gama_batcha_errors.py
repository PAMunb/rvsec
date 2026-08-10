#!/usr/bin/env python3
"""GAMA batch A - errors.csv stratification restricted to the 5 batch-A specs.

Freeze precondition (verified before running, command recorded in report):
  sha256sum errors.csv == 78023defec078353bbd1f64331edb7992a2c34e29570e6ceb064fb57f37dea69

Units reported separately (protocol section 12): lines, unique_msg, APKs, sites.
The CSV is PRE-GH100/GH101: hypothesis generator only. Zero rows != conformance.
"""
import csv
import hashlib
import sys
from collections import defaultdict

CSV_PATH = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv"
EXPECTED_SHA = "78023defec078353bbd1f64331edb7992a2c34e29570e6ceb064fb57f37dea69"

SPECS = [
    "DHGenParameterSpecSpec",
    "HMACParameterSpecSpec",
    "PBEParameterSpecSpec",
    "IvParameterSpecSpec",
    "SecretKeySpecSpec",
]
# Monitored classes: any *caller-side* row could still reference them in class/method/message.
CLASS_TOKENS = [
    "DHGenParameterSpec",
    "HMACParameterSpec",
    "PBEParameterSpec",
    "IvParameterSpec",
    "SecretKeySpec",
]

h = hashlib.sha256()
with open(CSV_PATH, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
digest = h.hexdigest()
print(f"sha256 = {digest}")
if digest != EXPECTED_SHA:
    print("FREEZE FAIL - aborting")
    sys.exit(1)
print("freeze check PASS\n")

rows = 0
per_spec = {s: {"lines": 0, "umsg": set(), "apks": set(), "sites": set(),
                "tools": defaultdict(int), "cats": defaultdict(int)} for s in SPECS}
all_specs = defaultdict(int)
token_hits = {t: {"lines": 0, "specs": defaultdict(int)} for t in CLASS_TOKENS}
executions_total = set()

with open(CSV_PATH, newline="") as f:
    r = csv.DictReader(f)
    for row in r:
        rows += 1
        spec = row["spec"]
        all_specs[spec] += 1
        executions_total.add((row["apk"], row["rep"], row["timeout"], row["tool"]))
        if spec in per_spec:
            d = per_spec[spec]
            d["lines"] += 1
            d["umsg"].add(row["unique_msg"])
            d["apks"].add(row["apk"])
            d["sites"].add((row["apk"], row["class"], row["method"], spec))
            d["tools"][row["tool"]] += 1
            parts = row["unique_msg"].split(":::")
            cat = parts[3] if len(parts) == 5 else "MALFORMED"
            d["cats"][cat] += 1
        # token scan across class/method/message/unique_msg (caller-side residue)
        blob = ":::".join((row["class"], row["method"], row["message"], row["unique_msg"]))
        for t in CLASS_TOKENS:
            if t in blob:
                # avoid counting SecretKeySpec inside SecretKeySpecSpec spec-name echo only
                token_hits[t]["lines"] += 1
                token_hits[t]["specs"][spec] += 1

print(f"total data lines = {rows}")
print(f"total executions (apk,rep,timeout,tool) = {len(executions_total)}")
print(f"distinct spec values in dataset = {len(all_specs)}")
print()
print("=== Batch A specs: four units, stratified ===")
print(f"{'spec':28s} {'lines':>7s} {'unique_msg':>10s} {'APKs':>5s} {'sites':>6s}")
for s in SPECS:
    d = per_spec[s]
    print(f"{s:28s} {d['lines']:7d} {len(d['umsg']):10d} {len(d['apks']):5d} {len(d['sites']):6d}")
    if d["lines"]:
        print(f"   tools: {dict(d['tools'])}")
        print(f"   categories: {dict(d['cats'])}")
print()
print("=== Token scan (monitored-class names anywhere in class/method/message/unique_msg) ===")
for t in CLASS_TOKENS:
    print(f"{t:22s} lines={token_hits[t]['lines']:6d}  by spec={dict(token_hits[t]['specs'])}")
print()
print("=== All spec values with line counts (context; NOT batch A scope) ===")
for s, n in sorted(all_specs.items(), key=lambda kv: -kv[1]):
    print(f"{s:30s} {n:7d}")
