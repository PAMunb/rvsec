#!/usr/bin/env python3
"""JUDGE batch B — J1-B: transition-table walks over the ROUND artifacts.

Parses `Prop_1_transition_<ev>` tables directly from the five round-input
*RuntimeMonitor.java files (hash-verified against batchB/generation_manifest.md)
and walks decisive traces, modelling the verified dispatch semantics:
 - fail category per artifact: CIS/COS state 4, KPR state 2, PBK state 3
   (SKY has NO fail category; match = state in {0,1});
 - @fail handler does __RESET (state := 0) for CIS/COS/KPR/PBK (artifact-verified);
 - CIS/COS have ONE process-global monitor (no indexing tree) — the walk is over
   a single state across streams;
 - suppression (condition false) = no transition at all.

Every claim-deciding table fact of the three reports is re-derived here from the
frozen bytes, independent of the agents' scripts.
"""
import re, sys, os, hashlib

GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SPECS = {
    "CIS": ("gen_CipherInputStreamSpec/out/CipherInputStreamSpecRuntimeMonitor.java", 4, None),
    "COS": ("gen_CipherOutputStreamSpec/out/CipherOutputStreamSpecRuntimeMonitor.java", 4, None),
    "KPR": ("gen_KeyPairSpec/out/KeyPairSpecRuntimeMonitor.java", 2, 1),
    "SKY": ("gen_SecretKeySpec/out/SecretKeySpecRuntimeMonitor.java", None, (0, 1)),
    "PBK": ("gen_PBEKeySpecSpec/out/PBEKeySpecSpecRuntimeMonitor.java", 3, 2),
}
MANIFEST_SHA = {
    "CIS": "aa6e492e9c256db4e17ed96ae8ec6c3d870254d513b27b807c3b5ebf6be926c6",
    "COS": "65df35f2ea13f989fc1775483eb36134e213c70871b008000533c858f618a7dd",
    "KPR": "aa4c0f907f8eb972815916ef5b72b97d6c92a26748bb64fa0bdf00136d328362",
    "SKY": "69791c1aa9174698f9e4ef2f3472e3b68733a7be1835a4863b76b4bc7ea75b4a",
    "PBK": "30795a79621cdff1a2b0923418bf031e52bed119b318e5e07126dc8f79c9c9b8",
}

def load_tables(path, expected_sha):
    with open(path, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    assert sha == expected_sha, f"FREEZE FAIL {path}: {sha}"
    tabs = {}
    for m in re.finditer(r"Prop_1_transition_(\w+)\[\] = \{([\d, ]+)\}", data.decode()):
        tabs[m.group(1)] = [int(x) for x in m.group(2).split(",")]
    return tabs

def walk(tabs, fail_state, trace, reset_on_fail=True, start=0):
    """Returns (final_state, n_fails, log). Suppressed events written as '~ev' are skipped."""
    s, fails, log = start, 0, []
    for ev in trace:
        if ev.startswith("~"):
            log.append(f"{ev}: suppressed (no transition), state={s}")
            continue
        ns = tabs[ev][s]
        if fail_state is not None and ns == fail_state:
            fails += 1
            log.append(f"{ev}: {s}->{ns} FAIL" + (" +__RESET->0" if reset_on_fail else ""))
            s = 0 if reset_on_fail else ns
        else:
            log.append(f"{ev}: {s}->{ns}")
            s = ns
    return s, fails, log

def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        global RC; RC = 1

RC = 0
T = {k: load_tables(os.path.join(GEN, v[0]), MANIFEST_SHA[k]) for k, v in SPECS.items()}
print("Freeze: 5/5 monitors match generation_manifest.md hashes\n")

# --- CIS: process-global monitor, second legal stream cascades -----------------
cis = T["CIS"]
print("Tables CIS:", cis)
s, f, log = walk(cis, 4, ["c1", "r1", "cl1"])            # stream 1, legal
check("CIS stream1 legal, 0 fails, ends accept-state 2", f == 0 and s == 2)
s2, f2, log2 = walk(cis, 4, ["c1", "r1", "cl1"], start=s)  # stream 2, same global state
check("CIS stream2 legal -> 3 spurious fails (post-__RESET cascade)", f2 == 3, "; ".join(log2))
# after the cascade the global state is back where a 3rd stream repeats the pattern
s3, f3, _ = walk(cis, 4, ["c1", "r1", "cl1"], start=s2)
check("CIS stream3 alternation (cascade-dependent state, 0 or 3 fails)", f3 in (0, 3), f"fails={f3}")

# --- COS: flush both directions ------------------------------------------------
cos = T["COS"]
print("\nTables COS:", cos)
s, f, log = walk(cos, 4, ["c1", "fl", "cl"])
check("COS [construct,flush,close] ACCEPTED (0 fails) though rule requires Writes+ — FN witness",
      f == 0 and s == 3, "; ".join(log))
s, f, log = walk(cos, 4, ["c1", "w1", "cl", "fl"])
check("COS flush-after-close -> exactly 1 spurious fail — FP witness", f == 1, "; ".join(log))
s, f, log = walk(cos, 4, ["c1", "w1", "cl"])
check("COS legal cycle clean", f == 0 and s == 3)
s2, f2, log2 = walk(cos, 4, ["c1", "w1", "cl"], start=s)
check("COS stream2 legal -> 3 spurious fails (global-monitor cascade, = CIS shape)", f2 == 3, "; ".join(log2))

# --- KPR: co? dropped; gpu from initial state fails ----------------------------
kpr = T["KPR"]
print("\nTables KPR:", kpr)
check("KPR gpu[0] == 2 (fail): generator-obtained pair's FIRST getPublic accused",
      kpr["gpu"][0] == 2 and kpr["gpr"][0] == 2)
s, f, log = walk(kpr, 2, ["gpu"])
check("KPR walk [getPublic] (CrySL-legal under co?) -> 1 spurious fail", f == 1, "; ".join(log))
s, f, log = walk(kpr, 2, ["c1", "gpu", "gpr", "gpu"])
check("KPR constructed pair, interleaved getters legal (reading A: (pu*,pr*)* = (pu|pr)*)", f == 0)

# --- SKY: no fail category; violations silent ---------------------------------
sky = T["SKY"]
print("\nTables SKY:", sky)
s, f, log = walk(sky, None, ["d", "d"], reset_on_fail=False)
check("SKY double-destroy reaches dead state 2 with NO fail category (silent)", s == 2 and f == 0, "; ".join(log))
s, f, log = walk(sky, None, ["d", "e1"], reset_on_fail=False)
check("SKY ge-after-destroy silent (dead state, no category)", s == 2 and f == 0)
check("SKY accepting states {0,1} realize ge* d? (epsilon accepted)",
      sky["e1"][0] == 0 and sky["d"][0] == 1 and sky["e1"][1] == 2 and sky["d"][1] == 2)

# --- PBK: residue at mandatory cP; FORBIDDEN loop; valid path -----------------
pbk = T["PBK"]
print("\nTables PBK:", pbk)
check("PBK carriers f1/f2/err1/err2/err3 loop at 0 (layer-2 star prefix held)",
      all(pbk[e][0] == 0 for e in ("f1", "f2", "err1", "err2", "err3")))
s, f, log = walk(pbk, 3, ["err1", "c2"])
check("PBK violating construction then LEGAL clearPassword -> 1 spurious fail (delayed residue)",
      f == 1, "; ".join(log))
s, f, log = walk(pbk, 3, ["f1", "c2"])
check("PBK FORBIDDEN ctor then clearPassword -> spurious fail (FORBIDDEN=>c1 continuation not honored)",
      f == 1, "; ".join(log))
s, f, log = walk(pbk, 3, ["c1", "c2"])
check("PBK valid path c1,cP -> match state 2, 0 fails", f == 0 and s == 2)

print("\nRESULT:", "ALL WALKS CONFIRM THE CLAIMED TABLE PHENOMENA" if RC == 0 else "DIVERGENCE FOUND")
sys.exit(RC)
