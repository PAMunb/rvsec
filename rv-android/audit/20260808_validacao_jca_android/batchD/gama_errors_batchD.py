#!/usr/bin/env python3
"""GAMA batch D - errors.csv stratification for MacSpec, MessageDigestSpec,
KeyPairGeneratorSpec, SecureRandomSpec, SignatureSpec.

Protocol 12 discipline: freeze hash verified IN-SCRIPT before any read;
four units (lines / unique_msg / APKs / sites) always reported separately;
historical data are PRE-GH100/GH101 -> hypothesis generator ONLY.
"""
import hashlib
import sys
from collections import Counter, defaultdict

import pandas as pd

CSV = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv"
EXPECTED = "78023defec078353bbd1f64331edb7992a2c34e29570e6ceb064fb57f37dea69"

h = hashlib.sha256()
with open(CSV, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
digest = h.hexdigest()
print(f"sha256(errors.csv) = {digest}")
if digest != EXPECTED:
    print("FREEZE CHECK FAILED - ABORT")
    sys.exit(1)
print("freeze check PASS (== manifesto 78023def...)")

df = pd.read_csv(CSV, dtype=str)
df["time"] = pd.to_numeric(df["time"], errors="coerce")

SPECS = ["MacSpec", "MessageDigestSpec", "KeyPairGeneratorSpec",
         "SecureRandomSpec", "SignatureSpec"]

# error type lives only inside unique_msg (field 4 of 5, ::: separated)
parts = df["unique_msg"].str.split(":::", expand=True)
df["etype"] = parts[3]
df["umsg_message"] = parts[4]

print("\n== A. global sanity (must equal pilot) ==")
print(f"lines={len(df)}  unique_msg={df['unique_msg'].nunique()}  "
      f"apks={df['apk'].nunique()}  "
      f"sites={df.groupby(['apk','class','method','spec']).ngroups}  "
      f"executions={df.groupby(['apk','rep','timeout','tool']).ngroups}")

print("\n== B. batch D specs: four units, by spec ==")
for s in SPECS:
    d = df[df["spec"] == s]
    print(f"{s}: lines={len(d)} unique_msg={d['unique_msg'].nunique()} "
          f"apks={d['apk'].nunique()} "
          f"sites={d.groupby(['apk','class','method']).ngroups}")

print("\n== C. category x spec (lines / unique_msg / apks / sites) ==")
for s in SPECS:
    d = df[df["spec"] == s]
    for et, g in d.groupby("etype"):
        print(f"{s} | {et}: lines={len(g)} umsg={g['unique_msg'].nunique()} "
              f"apks={g['apk'].nunique()} "
              f"sites={g.groupby(['apk','class','method']).ngroups}")

print("\n== D. message literals per spec (all distinct, with line counts) ==")
for s in SPECS:
    d = df[df["spec"] == s]
    for msg, n in d["message"].value_counts().items():
        m = msg if len(msg) <= 110 else msg[:107] + "..."
        print(f"{s} | {n:6d} | {m!r}")

print("\n== E. H4: 'but found .' (empty label) lines per spec, and their sites ==")
for s in SPECS:
    d = df[(df["spec"] == s) & (df["message"].str.endswith("but found .", na=False))]
    print(f"{s}: empty-label lines={len(d)} umsg={d['unique_msg'].nunique()} "
          f"apks={d['apk'].nunique()} "
          f"sites={d.groupby(['apk','class','method']).ngroups}")
    for (apk, cls, met), g in d.groupby(["apk", "class", "method"]):
        print(f"    site {cls}#{met} ({apk[:40]}): {len(g)} lines")

print("\n== F. H2 pairing cells per spec: (apk,rep,timeout,tool,class,method) "
      "cells with BOTH specific and InvalidSeq / only generic / only specific ==")
CELL = ["apk", "rep", "timeout", "tool", "class", "method"]
for s in SPECS:
    d = df[df["spec"] == s]
    if d.empty:
        print(f"{s}: no lines")
        continue
    gen = d[d["etype"] == "InvalidSequenceOfMethodCalls"].groupby(CELL).ngroups
    spec_d = d[d["etype"] != "InvalidSequenceOfMethodCalls"]
    cells = d.groupby(CELL)["etype"].agg(
        lambda x: ("g" if "InvalidSequenceOfMethodCalls" in set(x) else "") +
                  ("s" if any(t != "InvalidSequenceOfMethodCalls" for t in set(x)) else ""))
    c = Counter(cells)
    print(f"{s}: cells={len(cells)} both={c.get('gs',0)} only_generic={c.get('g',0)} "
          f"only_specific={c.get('s',0)}")

print("\n== G. site-level method-name profile (top 15 sites by lines) ==")
for s in SPECS:
    d = df[df["spec"] == s]
    if d.empty:
        continue
    print(f"-- {s}")
    top = d.groupby(["class", "method"]).size().sort_values(ascending=False).head(15)
    for (cls, met), n in top.items():
        cats = df[(df["spec"] == s) & (df["class"] == cls) & (df["method"] == met)]["etype"].value_counts().to_dict()
        print(f"    {n:6d}  {cls}#{met}  {cats}")

print("\n== H. KeyPairGeneratorSpec: full dump (16 lines expected) ==")
d = df[df["spec"] == "KeyPairGeneratorSpec"]
for _, r in d.iterrows():
    print(f"    {r['apk'][:45]} rep={r['rep']} to={r['timeout']} tool={r['tool']} "
          f"{r['class']}#{r['method']} :: {r['etype']} :: {r['message'][:60]}")

print("\n== I. SecureRandomSpec: H-SRD-1 probe - method-name tokens ==")
d = df[df["spec"] == "SecureRandomSpec"]
print("distinct (class,method) sites:", d.groupby(["class", "method"]).ngroups)
mtok = Counter()
for met, n in d.groupby("method").size().items():
    mtok[met] += n
for met, n in sorted(mtok.items(), key=lambda kv: -kv[1]):
    print(f"    {n:6d}  method={met}")
print("categories:", d["etype"].value_counts().to_dict())
print("messages:", d["message"].value_counts().to_dict())

print("\n== J. per-site line-count parity probe (SecureRandomSpec sites) ==")
for (apk, cls, met), g in d.groupby(["apk", "class", "method"]):
    n_exec = g.groupby(["rep", "timeout", "tool"]).ngroups
    print(f"    {cls}#{met} ({apk[:35]}): lines={len(g)} execs_with_lines={n_exec} "
          f"lines/exec={len(g)/max(n_exec,1):.1f}")

print("\n== K. MessageDigest oracle-realignment exposure: unsafe-algorithm "
      "literals that become SAFE under the api30 rule (MD5, SHA-1, aliases) ==")
d = df[(df["spec"] == "MessageDigestSpec") & (df["etype"] == "UnsafeAlgorithm")]
for msg, n in d["message"].value_counts().items():
    print(f"    {n:6d}  {msg[:100]!r}")

print("\n== L. tool distribution for batch D lines (pseudoreplication control) ==")
for s in SPECS:
    d = df[df["spec"] == s]
    if d.empty:
        continue
    print(f"{s}: {d['tool'].value_counts().to_dict()}")
