"""L1, L2, L3, timestamp inversions, midnight crossing, app-event fallback, C4-direct — from lc_stats.tsv + best.json."""
import csv, json, os, collections, statistics
from datetime import datetime
SP = os.environ.get("VALIDACAO_DIR", ".")
best = json.load(open(f"{SP}/best.json"))
by_logcat = {}
for k, v in best.items():
    c = v["container"]; by_logcat["data/" + v["logcat"].replace(f"results/{c}/", f"results/{c}/{c}/", 1)] = k
st = {}
for r in csv.DictReader(open(f"{SP}/lc_stats.tsv"), delimiter="\t"):
    st[r["file"]] = {k: (int(v) if k not in ("file", "first", "last") else v) for k, v in r.items()}
print("rows:", len(st), "| mapped to identities:", sum(1 for f in st if f in by_logcat))
def tool_secs(v):
    return (datetime.fromisoformat(v["end"]) - datetime.fromisoformat(v["tool_start"])).total_seconds()
# L2
hdr = collections.Counter(s["hdr"] for s in st.values()); print("== L2 headers per file:", dict(hdr), "| chatty lines total:", sum(s["chatty"] for s in st.values()))
rot = [f for f, s in st.items() if s["hdr"] > 3]; print("   files with >3 'beginning of' headers (rotation signature):", len(rot), rot[:5])
# timestamps
inv = [(f, s["inv"], s["maxinv_ms"]) for f, s in st.items() if s["inv"] > 0]
print("== timestamp inversions: files with >=1 negative delta:", len(inv), "| total inversions:", sum(x[1] for x in inv))
print("   max |inversion| ms distribution:", sorted(collections.Counter(min(x[2] // 100 * 100, 5000) for x in inv).items())[:12])
print("   midnight crossings (|delta|>1h):", sum(1 for s in st.values() if s["midnight"] > 0))
big = [x for x in inv if x[2] > 1000]; print("   inversions >1 s:", len(big), big[:5])
# L1 max gap relative to budget
print("== L1 max gap between consecutive timestamps (s), by budget: p50/p90/p99/max and #files gap>budget/2")
byb = collections.defaultdict(list)
for f, s in st.items():
    if f in by_logcat: byb[int(by_logcat[f].split("|")[3])].append((s["maxgap_ms"] / 1000, f))
for b, xs in sorted(byb.items()):
    g = sorted(x[0] for x in xs); n = len(g)
    print(f"   {b:4}: p50={g[n//2]:.1f} p90={g[int(n*.9)]:.1f} p99={g[int(n*.99)]:.1f} max={g[-1]:.1f} | gap>budget/2: {sum(1 for x in g if x > b/2)}")
# app events by arm
ev = collections.defaultdict(lambda: [0, 0, 0, 0])
for f, s in st.items():
    if f not in by_logcat: continue
    arm = by_logcat[f].split("|")[1]; e = ev[arm]; e[0] += s["fatal"] > 0; e[1] += s["anr"] > 0; e[2] += s["died"] > 0; e[3] += 1
print("== app-event fallback (identities with >=1 line): arm  FATAL  ANR  'has died'  n")
for a, e in sorted(ev.items()): print(f"   {a:22}{e[0]:6}{e[1]:5}{e[2]:9}{e[3]:6}")
# C4-direct and L3
zero_cov = [by_logcat[f] for f, s in st.items() if f in by_logcat and s["cov"] == 0]
print("== C4-direct: identities with zero RVSEC-COV lines:", len(zero_cov), collections.Counter(i.split("|")[1] for i in zero_cov))
cells = collections.defaultdict(dict)
for f, s in st.items():
    if f not in by_logcat: continue
    apk, arm, rep, to = by_logcat[f].split("|"); v = best[by_logcat[f]]
    ts = tool_secs(v); cells[(apk, arm, int(to))][int(rep)] = (s["cov"] / ts if ts > 0 else 0, s["cov"], ts)
low = []
for cell, reps in cells.items():
    if len(reps) < 3: continue
    for r, (rate, cov, ts) in reps.items():
        sis = [reps[o][0] for o in reps if o != r]; med = statistics.median(sis)
        if med > 0 and rate < 0.25 * med and cov > 0: low.append((cell, r, round(rate, 1), round(med, 1), cov, round(ts)))
print("== L3: identities whose RVSEC-COV rate (lines/s of tool time) < 25% of sister median (cov>0):", len(low))
print("   by arm:", collections.Counter(c[0][1] for c in low)); print("   by budget:", collections.Counter(c[0][2] for c in low))
for x in sorted(low, key=lambda x: x[2] / x[3])[:12]: print("   ", x)
json.dump(low, open(f"{SP}/l3_low.json", "w"))
