#!/usr/bin/env python3
"""J1-D — judge walk test, batch D (MAC, MDG, KPG, SRD, SIG).

Hash-asserts the five frozen RuntimeMonitor.java round artifacts, machine-parses
their effective transition tables and category states, verifies them against the
tables the agents published, checks structural facts (KPG @fail without reset;
MAC f3 root-map dispatch), and walks decisive traces with each trace's CrySL
status labeled (reading A of ORDER, D-piloto-1; verdicts over the effective
automaton, D-piloto-3).

Set BATCHD_GEN to the directory containing gen_<Spec>/out. Deterministic; inputs
identified by sha256.
"""
import hashlib, os, re, sys

GEN = os.environ.get("BATCHD_GEN", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

EXPECT_SHA = {
    "MacSpec": "de080e29df10f0d690079b10603f1bd17f8b4125ef0fa689ccb09c280829c5e4",
    "MessageDigestSpec": "6239fd2c1d55e680a3ca8376284c56754d153f4ee4001a78deeaa9b04b30f9ca",
    "KeyPairGeneratorSpec": "9bc45d18a63ae019937b4b1f7f5cbbaea32f6ae6169207064d4fa8d510c85bdf",
    "SecureRandomSpec": "cfed51687cf0138a6c78ead44470b85a31d16ca103a7a6329b726f28ff7bb799",
    "SignatureSpec": "21be928258d11ccf6ac79582908c5570fa699f88754e0a87428f5d707b0856b1",
}

# tables as published (Gama report §1b; Alfa language results summary)
PUBLISHED = {
    "MacSpec": {"fail": 4, "match": [3], "rows": {
        "g1": [2,4,4,4,4], "g2": [2,4,4,4,4], "g3": [0,4,4,4,4],
        "i1": [4,4,1,4,4], "i2": [4,4,1,4,4],
        "uArr": [4,1,4,4,4], "uByte": [4,1,4,4,4], "uBuf": [4,1,4,4,4],
        "f1": [4,3,4,4,4], "f2": [4,3,4,4,4], "f3": [4,3,4,4,4]}},
    "MessageDigestSpec": {"fail": 4, "match": [1], "rows": {
        "g1": [3,4,4,4,4], "g2": [3,4,4,4,4], "g3": [3,4,4,4,4], "g4": [0,4,4,4,4],
        "update": [4,2,2,2,4], "d1": [4,4,1,4,4], "d2": [4,1,1,1,4], "d3": [4,4,1,4,4]}},
    "KeyPairGeneratorSpec": {"fail": 4, "match": [1], "rows": {
        "g1": [2,4,4,4,4], "g2": [2,4,4,4,4], "g3": [0,4,4,4,4],
        "init1": [4,4,3,4,4], "init2": [4,4,3,4,4], "init3": [4,4,3,4,4], "init4": [4,4,3,4,4],
        "initError": [4,4,2,3,4], "gen": [4,4,4,1,4]}},
    "SecureRandomSpec": {"fail": 4, "match": [2], "rows": {
        "c1": [2,4,2,4,4], "c2": [2,4,4,4,4], "c3": [1,4,4,4,4],
        "g1": [2,4,4,4,4], "g2": [2,4,4,4,4], "g3": [2,4,4,4,4], "g4": [1,4,4,4,4],
        "setSeed1": [4,1,3,3,4], "setSeed2": [4,1,3,3,4], "setSeed3": [4,1,3,3,4],
        "genSeed": [4,1,3,3,4], "next1": [4,1,3,3,4],
        "next2": [4,1,3,4,4],   # the missing end-row: end(3) -> fail(4)
        "next3": [4,1,3,3,4], "ints": [4,1,3,3,4]}},
    "SignatureSpec": {"fail": 8, "match": [4,6], "rows": {}},  # rows parsed, fail/match checked
}

checks, failures = 0, 0
def check(name, ok, detail=""):
    global checks, failures
    checks += 1
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures += 1

TABLES = {}
for spec, sha in EXPECT_SHA.items():
    path = os.path.join(GEN, f"gen_{spec}", "out", f"{spec}RuntimeMonitor.java")
    src = open(path, encoding="utf-8").read()
    check(f"{spec} sha256 frozen", hashlib.sha256(src.encode()).hexdigest() == sha)
    rows = {m.group(1): [int(x) for x in m.group(2).split(",")]
            for m in re.finditer(r"Prop_1_transition_(\w+)\[\] = \{([\d, ]+)\}", src)}
    fail_states, match_states = set(), set()
    for m in re.finditer(r"Category_fail = ((?:(?:Prop_1_state|nextstate) == \d+(?:\s*\|\|\s*)?)+)", src):
        fail_states.update(int(x) for x in re.findall(r"== (\d+)", m.group(1)))
    for m in re.finditer(r"Category_match\w* = ((?:(?:Prop_1_state|nextstate) == \d+(?:\s*\|\|\s*)?)+)", src):
        match_states.update(int(x) for x in re.findall(r"== (\d+)", m.group(1)))
    TABLES[spec] = rows
    pub = PUBLISHED[spec]
    check(f"{spec} fail-state = {pub['fail']}", fail_states == {pub["fail"]}, f"parsed {sorted(fail_states)}")
    check(f"{spec} match-state(s) = {pub['match']}", match_states == set(pub["match"]), f"parsed {sorted(match_states)}")
    if pub["rows"]:
        diff = {e: (r, pub["rows"].get(e)) for e, r in rows.items() if pub["rows"].get(e) != r}
        check(f"{spec} transition tables == published ({len(rows)} events)", not diff, str(diff) if diff else "")
    # structural facts
    if spec == "KeyPairGeneratorSpec":
        check("KPG @fail has NO this.reset() (absorbing fail)", "this.reset();" not in src)
    else:
        check(f"{spec} @fail has this.reset()", "this.reset();" in src)
    if spec == "MacSpec":
        f3 = src[src.index("public static final void MacSpec_f3Event"):]
        f3 = f3[:f3.index("RVMLock.unlock")]
        check("MAC f3Event dispatches on global root (matchedEntry = MacSpec__Map)",
              "matchedEntry = MacSpec__Map" in f3 and "event_f3" in f3)

# ---------- walks (CrySL status per reading A; monitor over parsed tables) ----------
def walk(spec, trace, fail=4):
    st = 0
    events = []
    for e in trace:
        nxt = TABLES[spec][e][st]
        events.append((e, st, nxt))
        st = 0 if nxt == fail else nxt   # __RESET re-arms at start after fail (except KPG: absorbing)
        if spec == "KeyPairGeneratorSpec" and nxt == fail:
            st = fail  # no __RESET: absorbing
    return events

def run_walk(name, spec, trace, crysl, expect_fail_at, expect_end_match=None, fail=4):
    ev = walk(spec, trace, fail)
    fails = [i for i, (e, s, n) in enumerate(ev) if n == fail]
    ok = fails == expect_fail_at
    det = " ".join(f"{e}:{s}->{n}" for e, s, n in ev)
    if expect_end_match is not None:
        final = ev[-1][2]
        ok = ok and ((final in PUBLISHED[spec]["match"]) == expect_end_match)
        det += f" | final={final} match={final in PUBLISHED[spec]['match']}"
    check(f"walk {name} [CrySL: {crysl}]", ok, det + f" | fails at {fails}, expected {expect_fail_at}")

print("\n== decisive walks ==")
# SRD — both inclusions (judge's own product check on the separating traces)
run_walk("SRD c1 nB nB nB (canonical repeated nextBytes)", "SecureRandomSpec",
         ["c1","next2","next2","next2"], "CONFORMANT (Ins, Ends*)", [2,3])
run_walk("SRD c1 setSeed1 nB (canonical seeded usage)", "SecureRandomSpec",
         ["c1","setSeed1","next2"], "CONFORMANT (Ins, Seeds?, Ends*)", [2])
run_walk("SRD c1 next1 nB (nextInt then nextBytes)", "SecureRandomSpec",
         ["c1","next1","next2"], "extra-alphabet prefix; nB-after-End CONFORMANT", [2])
run_walk("SRD c1 nB setSeed1 (Seeds AFTER Ends)", "SecureRandomSpec",
         ["c1","next2","setSeed1"], "VIOLATING (Seeds? precedes Ends*) — monitor silent = FN", [])
run_walk("SRD control: c1 next1 next1 next1 (nextInt only)", "SecureRandomSpec",
         ["c1","next1","next1","next1"], "extra-alphabet control — clean isolates next2 row", [])
run_walk("SRD g4 unsafe then consumers (unsafeInit sink)", "SecureRandomSpec",
         ["g4","next2","next2","setSeed1"], "VIOLATING (constraint) — no sequence pairing by design", [])
# KPG — both inclusions
run_walk("KPG g1 initError gen (bad size then generate)", "KeyPairGeneratorSpec",
         ["g1","initError","gen"], "ORDER-COMPLETE (i3 bad size IS an Inits; constraint misuse only)", [2])
run_walk("KPG g1 initError init1 gen (correction route)", "KeyPairGeneratorSpec",
         ["g1","initError","init1","gen"], "VIOLATING? no — correction adds 2nd Inits: rule single-Inits VIOLATED; monitor match", [], expect_end_match=True)
run_walk("KPG g1 init1 init1 gen (two valid Inits)", "KeyPairGeneratorSpec",
         ["g1","init1","init1","gen"], "VIOLATING (exactly one Inits) — monitor fails AND cascades (absorbing fail)", [2,3])
run_walk("KPG fail-sink: g3-unsafe init1 then events cascade", "KeyPairGeneratorSpec",
         ["g3","init1","gen","gen"], "constraint misuse; monitor accuses every event after first fail", [1,2,3])
# MAC
run_walk("MAC carrier g3(unsafe) i1 uArr f1", "MacSpec",
         ["g3","i1","uArr","f1"], "ORDER-CONFORMANT (Gets,Inits,Updates+,Finals); constraint misuse only", [1,2,3])
run_walk("MAC safe path g1 i1 uArr f1", "MacSpec",
         ["g1","i1","uArr","f1"], "CONFORMANT", [], expect_end_match=True)
run_walk("MAC key-gate: g1 [i1 suppressed] f1 (unmarked key)", "MacSpec",
         ["g1","f1"], "CONFORMANT trace (rule has NO generatedKey REQUIRES); i1 suppressed by extra-oracle gate", [1])
run_walk("MAC invisible creation: i1 as first event", "MacSpec",
         ["i1","uArr","f1"], "CONFORMANT via (String,Provider) Gets the spec cannot see", [0,1,2])
# MDG
run_walk("MDG carrier g4(unsafe) update d2", "MessageDigestSpec",
         ["g4","update","d2"], "ORDER-CONFORMANT; digestAlg constraint misuse only", [1,2])
run_walk("MDG safe reuse: g1 update d1 update d1", "MessageDigestSpec",
         ["g1","update","d1","update","d1"], "CONFORMANT (Gets,(Updates+,Digests)+)", [], expect_end_match=True)
run_walk("MDG d1 without update fails both oracles", "MessageDigestSpec",
         ["g1","d1"], "VIOLATING (Digests need Updates+ unless DWOU=d2) — consistent fail", [1])
# SIG
run_walk("SIG carrier g3(unsafe) i4 update v1", "SignatureSpec",
         ["g3","i4","update","v1"], "ORDER-CONFORMANT verify branch; alg constraint misuse only", [1,2,3], fail=8)
run_walk("SIG verify branch safe: g1 i4 update v1", "SignatureSpec",
         ["g1","i4","update","v1"], "CONFORMANT", [], expect_end_match=True, fail=8)
run_walk("SIG sign branch: g1 i1 update s1 — s1 event exists in table but pointcut is DEAD", "SignatureSpec",
         ["g1","i1","update","s1"], "CONFORMANT sign flow; on the real platform s1 never fires (byte vs byte[])", [], expect_end_match=True, fail=8)
run_walk("SIG sign flow as the platform sees it (s1 unobservable): g1 i1 update", "SignatureSpec",
         ["g1","i1","update"], "CONFORMANT complete flow truncated at sign — never accepts, SIGNED never written", [], expect_end_match=False, fail=8)

print(f"\n{checks} checks, {failures} failures")
sys.exit(1 if failures else 0)
