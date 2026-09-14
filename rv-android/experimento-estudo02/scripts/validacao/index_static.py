"""Index/static detectors for estudo02: G1, G2, E3, I4-static, H4 matrix, Z3-direct, scope key."""
import json, glob, re, collections, csv, sys, os
SP = os.environ.get("VALIDACAO_DIR", ".")
EXCL = ["java.","javax.","sun.","android.","androidx.","kotlin.","kotlinx.","mop.","javamoprt.","rvmonitorrt.",
        "com.runtimeverification.","com.google.","org.aspectj.","org.apache.commons.","org.apache.geronimo.","net.sf.cglib."]
def arm(tc):
    return tc["name"] if tc.get("variant") in (None,"","default") else f'{tc["name"]}:{tc["variant"]}'
best = {}   # ident -> (record, container)
nrec = collections.Counter(); ncompleted = collections.Counter()
for tj in sorted(glob.glob("data/results/estudo02_[0-9][0-9]/estudo02_[0-9][0-9]/tasks.json")):
    cont = tj.split("/")[2]
    for t in json.load(open(tj))["tasks"]:
        c = t["config"]; r = t["result"]
        ident = (c["apk_name"], arm(c["tool_config"]), c["repetition"], c["timeout"])
        nrec[ident] += 1
        if r["state"] == "COMPLETED":
            ncompleted[ident] += 1
            if ident not in best or r["end_time"] > best[ident][0]["result"]["end_time"]:
                best[ident] = (t, cont)
print("== G1 grid")
apks = {i[0] for i in best}; arms = {i[1] for i in best}; tos = {i[3] for i in best}
print(f"identities={len(best)} apks={len(apks)} arms={len(arms)} timeouts={sorted(tos)} expected={len(apks)*len(arms)*3*len(tos)}")
cells = collections.Counter((i[0],i[1],i[3]) for i in best)
print("cells:", len(cells), "reps distribution:", collections.Counter(cells.values()))
print("== G2 duplicate COMPLETED:", sum(1 for v in ncompleted.values() if v > 1), "| multi-record identities:", sum(1 for v in nrec.values() if v > 1))

print("== E3 / scope key (163 .apk.json)")
statics = {}
bad_prefix = []; pkg_mismatch = []; zero_defs = []; incomplete = []
for j in sorted(glob.glob("data/results/estudo02_[0-9][0-9]/estudo02_[0-9][0-9]/*.apk/*.apk.json")):
    d = json.load(open(j)); apk = os.path.basename(j)[:-5]
    statics[apk] = d
    cp = d.get("codePackage") or ""
    if any(cp.startswith(p) for p in EXCL): bad_prefix.append((apk, cp))
    if d.get("package") != cp: pkg_mismatch.append((apk, d.get("package"), cp, d.get("codePackageSource")))
    if not d.get("class_defs_under_key"): zero_defs.append((apk, d.get("class_defs_under_key")))
    if not d.get("complete", True): incomplete.append(apk)
print(f"static files={len(statics)} excluded-prefix={len(bad_prefix)} {bad_prefix}")
print(f"package!=codePackage: {len(pkg_mismatch)}"); 
for x in pkg_mismatch: print("   ", x)
print(f"class_defs_under_key==0: {zero_defs}  complete=false: {incomplete}")
srcs = collections.Counter(d.get("codePackageSource") for d in statics.values()); print("codePackageSource:", dict(srcs))

print("== I4-static: '$'->'.' canonical collisions inside each .apk.json")
coll_total = 0
for apk, d in statics.items():
    names = [c["className"] for c in d.get("reachability", [])]
    canon = collections.defaultdict(set)
    for n in names: canon[n.replace("$", ".")].add(n)
    coll = {k: v for k, v in canon.items() if len(v) > 1}
    if coll:
        coll_total += len(coll); print(f"   {apk}: {len(coll)} collisions, e.g. {list(coll.items())[:2]}")
print("collisions total:", coll_total)

print("== H4 matrix (cov_method==0 per apk x arm over 9 identities)")
zero = collections.defaultdict(lambda: collections.defaultdict(int))
for i, (t, _) in best.items():
    cm = t["result"]["coverage_metrics"] or {}
    if (cm.get("method_coverage") or 0) == 0: zero[i[0]][i[1]] += 1
allzero_cells = [(a, b, n) for a, m in zero.items() for b, n in m.items() if n == 9]
print("APK x arm cells with all 9 identities at zero:", len(allzero_cells))
by_arm = collections.Counter(b for _, b, _ in allzero_cells); print("   by arm:", dict(by_arm))
apk_all = [a for a in apks if sum(zero[a].values()) == 99]
print("APKs zero under ALL 11 arms (article exclusion criterion):", apk_all)
partial = [(a, b, n) for a, m in zero.items() for b, n in m.items() if 0 < n < 9]
print("APK x arm cells with some (1-8) zero identities:", len(partial)); print("   ", sorted(partial)[:40])
total_zero_ids = sum(sum(m.values()) for m in zero.values()); print("identities with cov_method==0:", total_zero_ids)

print("== Z3-direct: total_errors (mop_unique, 7-part) vs RVSEC line count per identity (scan.tsv TOTAL)")
tot = {}
for line in open(f"{SP}/scan.tsv"):
    p = line.rstrip("\n").split("\t")
    if p[1] == "TOTAL": tot[p[0]] = int(p[3])
missing = 0; viol_a = []; viol_b = []; ok = 0
for i, (t, cont) in best.items():
    lc = t["result"]["logcat_file"]  # results/estudo02_NN/<apk>/<file>
    path = "data/" + lc.replace(f"results/{cont}/", f"results/{cont}/{cont}/", 1)
    if path not in tot: missing += 1; continue
    mu = t["result"]["coverage_metrics"].get("total_errors") or 0
    n = tot[path]
    if mu > 0 and n == 0: viol_a.append((i, mu, n))
    if mu > n: viol_b.append((i, mu, n))
    ok += 1
print(f"joined={ok} missing_logcat_in_scan={missing} | mop_unique>0 and lines==0: {len(viol_a)} | mop_unique>lines: {len(viol_b)}")
for x in (viol_a + viol_b)[:10]: print("   ", x)
json.dump({"|".join(map(str, i)): {"container": c, "logcat": t["result"]["logcat_file"], "trace": t["result"]["trace_file"],
           "elapsed": t["result"]["execution_time_seconds"], "tool_start": t["result"]["tool_execution_start"],
           "start": t["result"]["start_time"], "end": t["result"]["end_time"], "cm": t["result"]["coverage_metrics"],
           "nrec": nrec[i]} for i, (t, c) in best.items()}, open(f"{SP}/best.json", "w"))
print("wrote best.json")
