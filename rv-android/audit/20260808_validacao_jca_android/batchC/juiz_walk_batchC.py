#!/usr/bin/env python3
"""J1-C: judge walk test, batch C.

Parses the transition tables and category states straight from the five FROZEN
round RuntimeMonitor.java artifacts (sha256-asserted), walks the decisive traces
over them with the verified dispatch semantics (condition suppression = no
transition; @fail => record + __RESET to start; global monitor for KST), and
labels every trace with its status under the paired CrySL rule's ORDER
(reading A, D-piloto-1) where the misuse -- if any -- is CONSTRAINT-only.

Independent of the agents' scripts; complements J2-C (juiz_JuizDriveC.java),
which drove the real compiled monitors.
"""
import hashlib, re, sys, os

GEN = os.environ.get("BATCHC_GEN") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
# BATCHC_GEN: directory containing the gen_<Spec>/out round artifacts (scratch per generation_manifest.md)

EXPECT_SHA = {
    "gen_KeyGeneratorSpec/out/KeyGeneratorSpecRuntimeMonitor.java":
        "de9e52053a47a661be3c5c687cd7fb6524969090b4b32a99990010db3fd58ecd",
    "gen_KeyManagerFactorySpec/out/KeyManagerFactorySpecRuntimeMonitor.java":
        "dca6fb3767c267fede1a71104a7a6a8169e05dd965234f0435d8d553ca82dd37",
    "gen_TrustManagerFactorySpec/out/TrustManagerFactorySpecRuntimeMonitor.java":
        "a99d7d54f423f30cc3465c2e635bdcf079ee459f0f2821d17a9113ad3e769f53",
    "gen_SSLContextSpec/out/SSLContextSpecRuntimeMonitor.java":
        "ea212b12220b1d62152b00cab92dcd36b89fd97b321e4b3bd8b2131d2df56569",
    "gen_KeyStoreSpec/out/KeyStoreSpecRuntimeMonitor.java":
        "45befd0b9ddd39cd96a4ec70ea83013454e2ef61ab2311675aeba1d94fe7ee45",
}

def load(path):
    full = os.path.join(GEN, path)
    data = open(full, "rb").read()
    h = hashlib.sha256(data).hexdigest()
    assert h == EXPECT_SHA[path], f"HASH MISMATCH {path}: {h}"
    return data.decode()

def tables(src):
    t = {}
    for m in re.finditer(r"Prop_1_transition_(\w+)\[\] = \{([\d, ]+)\}", src):
        t[m.group(1)] = [int(x) for x in m.group(2).split(",")]
    fail = set(int(x) for x in re.findall(r"Category_fail = Prop_1_state == (\d+)|Category_fail = nextstate == (\d+)", src.replace("this.", "")) for x in x if x)
    match = set(int(x) for x in re.findall(r"Category_match\w* = Prop_1_state == (\d+)|Category_match\w* = nextstate == (\d+)", src.replace("this.", "")) for x in x if x)
    return t, sorted(fail), sorted(match)

checks = []
def check(name, cond, detail=""):
    checks.append((name, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))

SPECS = {
 "KGN": "gen_KeyGeneratorSpec/out/KeyGeneratorSpecRuntimeMonitor.java",
 "KMF": "gen_KeyManagerFactorySpec/out/KeyManagerFactorySpecRuntimeMonitor.java",
 "TMF": "gen_TrustManagerFactorySpec/out/TrustManagerFactorySpecRuntimeMonitor.java",
 "SSL": "gen_SSLContextSpec/out/SSLContextSpecRuntimeMonitor.java",
 "KST": "gen_KeyStoreSpec/out/KeyStoreSpecRuntimeMonitor.java",
}
T, FAILS, MATCHES, SRC = {}, {}, {}, {}
for k, p in SPECS.items():
    SRC[k] = load(p)
    T[k], FAILS[k], MATCHES[k] = tables(SRC[k])
    print(f"{k}: fail={FAILS[k]} match={MATCHES[k]} tables={{{', '.join(f'{e}:{r}' for e, r in sorted(T[k].items()))}}}")

# --- published-table cross-check (gama_report §1b / alfa_language_results header)
check("KST table equals published", T["KST"] == {
    "g1": [4,4,5,5,5,5], "g2": [0,0,5,5,5,5], "load": [5,5,5,5,1,5],
    "store": [5,5,1,5,5,5], "ge1": [5,3,5,5,5,5], "se1": [5,2,5,5,5,5], "gk1": [5,1,5,1,5,5]})
check("KMF/TMF tables equal published", all(
    T[s]["g1"] == [1,3,1,3] and T[s]["g3"] == [0,3,3,3] and T[s]["i1"] == [3,2,3,3]
    and T[s][e] == [3,3,0,3] for s, e in (("KMF","gkm1"), ("TMF","gtm1"))))
check("SSL table equals published", T["SSL"] == {
    "g1": [2,3,3,3], "g2": [2,3,3,3], "unsafe_protocol": [0,3,3,3],
    "init": [3,3,1,3], "engine": [3,1,3,3]})
check("KGN table equals published", T["KGN"] == {
    "g1": [4,5,5,5,4,5], "g2": [3,5,5,3,5,5], "g3": [0,5,5,5,5,5],
    "i1": [5,5,5,2,2,5], "i2": [5,5,5,2,2,5], "i3": [5,5,5,2,2,5],
    "i4": [5,5,5,2,2,5], "i5": [5,5,5,2,2,5], "gk1": [5,5,1,1,1,5]})

# --- indexing shapes
check("KST is the empty-binding global Tuple2 (spec param ks bound by no event)",
      "Tuple2<KeyStoreSpecMonitor_Set, KeyStoreSpecMonitor> KeyStoreSpec__Map" in SRC["KST"]
      and "MapOfMonitor<KeyStoreSpecMonitor>" not in SRC["KST"])
check("KGN/KMF/TMF/SSL are per-object MapOfMonitor",
      all(f"MapOfMonitor<{n}Monitor> {n}_" in SRC[k] for k, n in
          (("KGN","KeyGeneratorSpec"), ("KMF","KeyManagerFactorySpec"),
           ("TMF","TrustManagerFactorySpec"), ("SSL","SSLContextSpec"))))
check("reset() clears category flags (stale-flag path benign)",
      all("Category_fail = false" in SRC[k] for k in SPECS))

def walk(spec, trace, start=0):
    """Returns (final_state, fails_at) with @fail => __RESET to 0."""
    st, fails_at = start, []
    for ev in trace:
        st = T[spec][ev][st]
        if st in FAILS[spec]:
            fails_at.append(ev)
            st = 0
    return st, fails_at

# --- decisive walks (rule status stated per trace)
st, f = walk("TMF", ["g3", "i1", "gtm1"])
check("TMF g3,i1,gtm1 (rule-ORDER-CONFORMANT, constraint-only misuse) -> fails at i1 AND gtm1",
      f == ["i1", "gtm1"], "FEN-C-CARRIER-SEQFAIL + FEN-C-DELAYED")
st, f = walk("KMF", ["g3", "i1", "gkm1"])
check("KMF same shape", f == ["i1", "gkm1"])
st, f = walk("SSL", ["unsafe_protocol", "init"])
check("SSL unsafe_protocol,init (ORDER-conformant) -> fails at init", f == ["init"])
st, f = walk("KGN", ["g3", "i1", "gk1"])
check("KGN g3,i1,gk1 (ORDER-conformant) -> fails at i1 AND gk1", f == ["i1", "gk1"])
st, f = walk("KST", ["g2", "load", "gk1"])
check("KST g2,load,gk1 (ORDER-conformant, type constraint-only) -> fails at load AND gk1",
      f == ["load", "gk1"])
st, f = walk("KST", ["g1", "g1"])
check("KST global monitor: interleaved 2nd store's g1 -> fail (two objects, one automaton)",
      f == ["g1"], "per-object each trace is legal; ere (g2* g1 load...)+ forbids g1 g1")
st, f = walk("KST", ["g1", "load", "store"])
check("KST g1,load,[skE1 unobserved],store (rule route sE,Stores broken by omission) -> fail at store",
      f == ["store"], "FEN-KST-ENTRIES-OMITIDAS displaced accusation")
st, f = walk("KST", ["g1", "load", "se1", "store"])
check("KST captured sE control g1,load,se1,store -> clean", f == [] and st == 1)
st, f = walk("KMF", ["g1", "i1", "gkm1", "gkm1"])
check("KMF 2nd getKeyManagers (genuine ORDER violation gkm?) -> fail at gkm#2", f == ["gkm1"])
st, f = walk("SSL", ["g1", "init", "engine", "engine"])
check("SSL 2nd engine (rule Engine? violation) -> SILENT (FN): engine loops at end",
      f == [] and st == 1, "FEN-SSL-ENGINE-LOOP; masked by dead pointcut FEN-SSL-ENGINE-VOID")
st, f = walk("KMF", ["g1", "i1", "gkm1"])
check("KMF complete rule word g1,i1,gkm1 ends OUTSIDE match1 (state 0)",
      f == [] and st == 0 and 2 in MATCHES["KMF"], "FEN-C-ACCEPT-END")
st, f = walk("KGN", ["g1", "i1", "gk1"])
check("KGN conformant word -> match, no fail", f == [] and st in MATCHES["KGN"])
st, f = walk("KMF", ["g1", "g2"])
check("dexlib2 merged-wrapper emission g1,g2 on ONE 1-arg getInstance(\"PKIX\") -> fail at g2",
      f == ["g2"], "FEN-SET-VARARGS-ARGS-IGNORED table-level effect (Beta DX-1/DX-2)")
st, f = walk("KST", ["load"])
check("KST creation-at-consume: load as first event -> fail (2-arg-created store)", f == ["load"])
st, f = walk("SSL", ["init"])
check("SSL creation-at-consume: init as first event -> fail ((String,Provider) overload)",
      f == ["init"])

n_fail = sum(1 for _, ok in checks if not ok)
print(f"\n{len(checks)-n_fail}/{len(checks)} checks PASS")
sys.exit(1 if n_fail else 0)
