#!/usr/bin/env python3
"""Set-phase descriptor lint over the merged 23-spec artifacts (EXEC-SET half).

Inputs (frozen scratch, hashes in set_exec_hashes.txt):
  merge_run1/out/MultiSpec_1MonitorAspect.json   (descriptor consumed by dexlib2)
  merge_run1/out/MultiSpec_1MonitorAspect.aj     (aspect consumed by ajc)
  merge_run1/out/MultiSpec_1RuntimeMonitor.java  (monitor both variants call)
  perspec/gen_*/out/*MonitorAspect.json          (per-spec descriptors)

Checks:
  L1 descriptor<->aspect 1:1 (advice count; every descriptor expression appears in .aj)
  L2 monitorCalls -> RuntimeMonitor method existence + arity
  L3 per-spec advice/monitorCall counts (table)
  L4 known per-spec defect mechanisms as they stand in the MERGED descriptor:
     MAC f3 unbound target(m); SIG sign return-type; SSL createSSLEngine void;
     KST getEntry/setEntry nested types; first-disjunct call(...)||call(...) rows;
     args() narrowing under trailing '..'; declared-only-index candidates (inherited members)
"""
import json, re, collections, sys, pathlib

SP = pathlib.Path(__file__).parent
out = SP / "merge_run1" / "out"
m = json.load(open(out / "MultiSpec_1MonitorAspect.json"))
aj = open(out / "MultiSpec_1MonitorAspect.aj").read()
rm = open(out / "MultiSpec_1RuntimeMonitor.java").read()
adv = m["advices"]

print("### L1 descriptor <-> aspect 1:1")
aj_advices = re.findall(r"^\s*(before|after)\s*\(([^)]*)\)\s*(returning\s*(\([^)]*\))?)?\s*:", aj, re.M)
print(f"descriptor advices: {len(adv)}; .aj advice headers: {len(aj_advices)}")
missing_expr = []
for a in adv:
    # the .aj concatenates the same expression inside the advice header; whitespace may fold
    expr = a["expression"]
    if re.sub(r"\s+", " ", expr) not in re.sub(r"\s+", " ", aj):
        missing_expr.append((a["name"], expr))
print(f"descriptor expressions not found verbatim in .aj: {len(missing_expr)}")
for n, e in missing_expr[:10]:
    print("  MISSING-IN-AJ:", n, "|", e[:120])

print("\n### L2 monitorCalls -> RuntimeMonitor methods")
methods = set(re.findall(r"public static (?:final )?void (\w+)\s*\(", rm))
sigs = {}
for mm in re.finditer(r"public static (?:final )?void (\w+)\s*\(([^)]*)\)", rm):
    name, params = mm.group(1), mm.group(2).strip()
    arity = 0 if not params else len(re.split(r",(?![^<]*>)", params))
    sigs.setdefault(name, set()).add(arity)
bad = []
n_calls = 0
for a in adv:
    for mc in a["monitorCalls"]:
        n_calls += 1
        cls, meth = mc["method"].split(".")
        if cls != "MultiSpec_1RuntimeMonitor" or meth not in methods:
            bad.append((a["name"], mc["method"], "method missing"))
            continue
        if len(mc["args"]) not in sigs[meth]:
            bad.append((a["name"], mc["method"],
                        f"arity {len(mc['args'])} not in {sigs[meth]}"))
print(f"monitorCalls: {n_calls}; unresolved/misarity: {len(bad)}")
for b in bad:
    print("  BAD:", b)

print("\n### L3 per-spec advice/monitorCall counts")
by = collections.defaultdict(list)
for a in adv:
    by[a["specName"]].append(a)
for s in sorted(by):
    print(f"  {s:28s} {len(by[s]):3d} advices {sum(len(a['monitorCalls']) for a in by[s]):3d} monitorCalls")
print("distinct specs:", len(by))

print("\n### L4 known defect mechanisms in the MERGED descriptor")
def show(tag, pred):
    rows = [a for a in adv if pred(a)]
    print(f"-- {tag}: {len(rows)} advice(s)")
    for a in rows:
        params = {p["name"] for p in a["parameters"]}
        print(f"   {a['name']:26s} params={sorted(params)} pos={a['position']} ret={a['returning']}")
        print(f"     expr: {a['expression']}")

# 4a MAC f3 unbound target(m)
show("MAC f3 (unbound target)", lambda a: a["name"] == "MacSpec_f3")
# 4b SIG sign return type
show("SIG sign advices", lambda a: a["specName"] == "SignatureSpec" and "sign" in a["expression"] and "Signature.sign" in a["expression"])
# 4c SSL createSSLEngine
show("SSL createSSLEngine", lambda a: "createSSLEngine" in a["expression"])
# 4d KST nested types
show("KST getEntry/setEntry (nested types)", lambda a: a["specName"] == "KeyStoreSpec" and ("getEntry" in a["expression"] or "setEntry" in a["expression"]))
# 4e first-disjunct rows: expression with >=2 call(...) disjuncts
def ncalls(a): return len(re.findall(r"call\(", a["expression"]))
rows = [a for a in adv if ncalls(a) >= 2]
print(f"-- first-disjunct exposure (expressions with >=2 call() disjuncts): {len(rows)}")
for a in rows:
    print(f"   {a['name']:26s} [{a['specName']}] {ncalls(a)} call() disjuncts")
    print(f"     expr: {a['expression']}")
# 4f args() narrowing with trailing '..' in call signature
rows = [a for a in adv if re.search(r"call\([^)]*\.\.\s*\)", a["expression"]) and "args(" in a["expression"]]
print(f"-- args() present alongside 'call(..(..))' wildcard-arity rows: {len(rows)}")
for a in rows:
    print(f"   {a['name']:26s} [{a['specName']}] expr: {a['expression']}")
# 4g inherited-member candidates (declared-only index): SecureRandom methods inherited from java.util.Random
rows = [a for a in adv if a["specName"] == "SecureRandomSpec" and re.search(r"\b(nextInt|nextLong|nextDouble|nextFloat|nextBoolean|ints|longs|doubles)\b", a["expression"])]
print(f"-- SRD inherited-member (declared-only index) candidates: {len(rows)}")
for a in rows:
    print(f"   {a['name']:26s} expr: {a['expression']}")
