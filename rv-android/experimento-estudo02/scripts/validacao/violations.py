"""I2, I3, I5 (and R3-alt) over every RVSEC line of the corpus (rv_lines.txt) joined with best.json."""
import re, json, glob, collections, os, csv, statistics
SP = os.environ.get("VALIDACAO_DIR", ".")
MOP = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android"
emitted = set()
for f in glob.glob(f"{MOP}/*.mop"):
    emitted |= set(re.findall(r'ErrorDescription\(\s*ErrorType\.\w+\s*,\s*"([^"]+)"', open(f).read()))
print("== I2: spec names emitted by the 47 .mop files:", len(emitted))
best = json.load(open(f"{SP}/best.json"))
by_logcat = {}
for k, v in best.items():
    c = v["container"]; by_logcat["data/" + v["logcat"].replace(f"results/{c}/", f"results/{c}/{c}/", 1)] = k
LINE = re.compile(r'RVSEC\s*:\s*(.*)$')
POS = re.compile(r'\([^()]+:\d+\)$')
per = collections.defaultdict(lambda: {"n": 0, "k4": set(), "k5": set(), "k7": set()})
spec_count = collections.Counter(); unknown = collections.Counter(); short = 0; i3_hits = []; i3_fields = collections.Counter()
weird_method = collections.Counter()
for raw in open(f"{SP}/rv_lines.txt", errors="ignore"):
    path, _, rest = raw.partition(".logcat:"); path += ".logcat"
    m = LINE.search(rest)
    if not m: continue
    p = m.group(1).rstrip("\n").split(",", 6)
    if len(p) < 7: short += 1; continue
    spec, cls, _, meth, loc, et, msg = p
    spec_count[spec] += 1
    if spec not in emitted: unknown[spec] += 1
    for name, val in (("class", cls), ("method", meth)):
        if POS.search(val): i3_hits.append((path, name, val)); i3_fields[name] += 1
    if re.search(r'[$\- ]', meth): weird_method[meth.split("$")[0] + "$…" if "$" in meth else meth] += 1
    code = ev = "UNSPECIFIED"
    if msg.startswith("v=1 "):
        mc = re.search(r'(?:^|\s)code=(\S+)', msg); me = re.search(r'(?:^|\s)ev=(\S+)', msg)
        if mc: code = mc.group(1)
        if me: ev = me.group(1)
    ident = by_logcat.get(path)
    if ident is None: unknown["<unmapped file>"] += 1; continue
    d = per[ident]; d["n"] += 1
    d["k4"].add((cls, meth, spec)); d["k5"].add((cls, meth, spec, et, msg)); d["k7"].add((cls, meth, spec, et, code, ev, msg))
print("specs observed:", len(spec_count), "| not in emitted set:", dict(unknown), "| short lines:", short)
print("== I3: class/method fields carrying a source position '(File:line)':", len(i3_hits), dict(i3_fields))
for h in i3_hits[:5]: print("   ", h[1], h[2][:120])
print("   method names with $/-/space (top):", weird_method.most_common(8))
print("== I5 / R3-alt: per-identity keys vs tasks.json total_errors")
rows = []; mismatch = []
for ident, v in best.items():
    d = per.get(ident); mu = (v["cm"] or {}).get("total_errors") or 0
    n, k4, k5, k7 = (d["n"], len(d["k4"]), len(d["k5"]), len(d["k7"])) if d else (0, 0, 0, 0)
    if k7 != mu: mismatch.append((ident, mu, n, k4, k5, k7))
    apk, arm, rep, to = ident.split("|")
    rows.append(dict(apk=apk, arm=arm, rep=int(rep), timeout=int(to), lines=n, k4=k4, k5=k5, k7=k7, mop_unique_tasks=mu))
print(f"identities={len(rows)} | k7 != total_errors: {len(mismatch)}")
for x in mismatch[:10]: print("   ", x)
with open(f"{SP}/i5_per_identity.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
agg = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
for r in rows:
    a = agg[(r["arm"], r["timeout"])]; a[0] += r["lines"]; a[1] += r["k4"]; a[2] += r["k5"]; a[3] += r["k7"]; a[4] += 1
print(f"{'arm':22}{'to':>5}{'lines':>9}{'k4':>8}{'k5':>8}{'k7':>8}{'k7/k4':>7}")
for (arm, to), a in sorted(agg.items()):
    print(f"{arm:22}{to:>5}{a[0]:>9}{a[1]:>8}{a[2]:>8}{a[3]:>8}{(a[3]/a[1] if a[1] else 0):>7.2f}")
T = [sum(r[k] for r in rows) for k in ("lines", "k4", "k5", "k7")]
print("TOTAL lines/k4/k5/k7:", T, "| k7/k4 = %.2f" % (T[3] / T[1]))
# article-style: distinct (apk, class, method, spec) over the whole campaign and per arm
glob4 = set(); glob4_arm = collections.defaultdict(set)
for ident, d in per.items():
    apk, arm, *_ = ident.split("|")
    for k in d["k4"]: glob4.add((apk,) + k); glob4_arm[arm].add((apk,) + k)
print("campaign-level distinct (apk,class,method,spec):", len(glob4), "| per arm:", {a: len(s) for a, s in sorted(glob4_arm.items())})
print("identities with >0 violations:", sum(1 for r in rows if r["k7"] > 0), "of", len(rows))
print("top specs:", spec_count.most_common(25))
