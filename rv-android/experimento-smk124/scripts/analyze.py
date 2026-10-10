"""Analyse the smk124 device smoke for one APK (tasks 5.3-5.5 of gh124).

usage: analyze.py <task_dir> <apk_name> <mop.json> <instrumented.apk> <work_dir>

<task_dir> holds the task's .logcat and .trace.ndjson.gz; <mop.json> is the derived MOP
artifact of the run (its "handlers" maps binary class name -> {mop, dist?}).

Reported:
- Compose RVSEC-BIND lines by handler origin (app, androidx.compose.material*, other library)
  and every distinct app class named, with whether it is a key of "handlers";
- lines naming the shapes gh124 resolves (AbstractClickableNode$$ExternalSyntheticLambda*,
  CheckboxKt$$ExternalSyntheticLambda6, CheckboxKt$Checkbox$1$1), which must be absent;
- stampNodes / stampHits from RUN_END and decisions by src;
- every remaining androidx.compose.material* handler, by class;
- for each app class, the static facts that tell whether the Material step produced it: the
  Function arity of the class, the node classes it was stamped on, and the library calls the
  app passes it to (a crude linear def trace over `dexdump -d`, see dexidx.py of the sweep).
  The logcat records only the final class, so the Material/fallback attribution is an
  inference from these facts, not an observation;
- crashes with an mop.RvsecStamp frame and VerifyError lines.
"""
import collections
import glob
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/e03mini_a2/sweep_stamp")
sys.path.insert(0, os.path.abspath(SWEEP))
from dexidx import index  # noqa: E402

DEXDUMP = "/home/pedro/desenvolvimento/aplicativos/android/sdk/build-tools/35.0.1/dexdump"
BIND = re.compile(r"RVSEC-BIND: compose kind=(\S+) node=(\S+) semanticsId=(\S+) .*? handler=(\S+)"
                  r"(?: longClickHandler=(\S+))?")
FORBIDDEN = re.compile(r"AbstractClickableNode\$\$ExternalSyntheticLambda\d+$"
                       r"|CheckboxKt\$\$ExternalSyntheticLambda6$|CheckboxKt\$Checkbox\$1\$1$")
LIB = ("androidx.", "android.", "kotlin.", "kotlinx.", "java.", "com.google.android.material.")
TARGET_PREFIX = ("Landroidx/compose/material", "Landroidx/compose/foundation/",
                 "Landroidx/compose/ui/semantics/SemanticsPropertiesKt;.")


def origin(cls):
    if cls.startswith("androidx.compose.material"):
        return "material"
    if cls.startswith(LIB):
        return "library"
    return "app"


def bind_lines(logcat):
    out = []
    with open(logcat, errors="replace") as f:
        for line in f:
            m = BIND.search(line)
            if m:
                kind, node, sid, h, lh = m.groups()
                out.append((kind, node, sid, h))
                if lh:
                    out.append(("longClick", node, sid, lh))
    return out


def trace_facts(path):
    counters, src = {}, collections.Counter()
    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            if '"RUN_END"' in line:
                counters = json.loads(line).get("counters", {})
            for m in re.finditer(r'"src":"([A-Za-z]+)"', line):
                src[m.group(1)] += 1
    return counters, src


def static_calls(apk, work, app_classes):
    """{app class: (interfaces, [(caller, callee)...])} for library calls taking it."""
    want = {"L" + c.replace(".", "/") + ";" for c in app_classes}
    d = tempfile.mkdtemp(dir=work)
    txts = []
    with zipfile.ZipFile(apk) as z:
        for n in z.namelist():
            if n.startswith("classes") and n.endswith(".dex"):
                z.extract(n, d)
                t = os.path.join(d, n[:-4] + ".txt")
                with open(t, "w") as out:
                    subprocess.run([DEXDUMP, "-d", os.path.join(d, n)], stdout=out,
                                   stderr=subprocess.DEVNULL)
                os.remove(os.path.join(d, n))
                txts.append(t)
    classes, sites = index(txts, lambda r: r.startswith(TARGET_PREFIX))
    for t in txts:
        os.remove(t)
    os.rmdir(d)
    calls = collections.defaultdict(set)
    for s in sites:
        for a in s["args"]:
            if a.startswith("new:") and a[4:] in want:
                calls[a[4:]].add((s["cls"], s["ref"].split(":")[0]))
    res = {}
    for c in want:
        ifaces = [i for i in classes.get(c, {}).get("ifaces", []) if "kotlin/jvm/functions" in i]
        res[c[1:-1].replace("/", ".")] = (ifaces, sorted(calls.get(c, ())))
    return res


def main():
    task_dir, apk_name, mop_json, apk, work = sys.argv[1:6]
    logcat = glob.glob(os.path.join(task_dir, "*mopd_on_llm_off.logcat"))[0]
    trace = glob.glob(os.path.join(task_dir, "*mopd_on_llm_off.trace.ndjson.gz"))[0]
    handlers = json.load(open(mop_json)).get("handlers", {})
    lines = bind_lines(logcat)

    print(f"## {apk_name}\n")
    by_origin = collections.Counter(origin(h) for _, _, _, h in lines)
    print(f"RVSEC-BIND compose entries (click + longClick): {len(lines)}; by origin: {dict(by_origin)}")
    forbidden = collections.Counter(h for _, _, _, h in lines if FORBIDDEN.search(h))
    print(f"entries naming a gh124 shape (must be 0): {sum(forbidden.values())} {dict(forbidden)}")

    app = collections.defaultdict(lambda: {"n": 0, "nodes": collections.Counter()})
    for kind, node, _, h in lines:
        if origin(h) == "app":
            app[h]["n"] += 1
            app[h]["nodes"][node] += 1
    in_h = [c for c in app if c in handlers]
    print(f"distinct app classes: {len(app)}; keys of handlers: {len(in_h)}; "
          f"not keys: {sorted(set(app) - set(in_h))}")

    counters, src = trace_facts(trace)
    print(f"RUN_END counters: {counters}; decisions by src: {dict(src)}")

    mat = collections.Counter(h for _, _, _, h in lines if origin(h) == "material")
    print("\nremaining androidx.compose.material* handlers:")
    for h, n in mat.most_common():
        print(f"  {n:5d}  {h}")

    facts = static_calls(apk, work, list(app))
    print("\napp classes (entries | nodes | Function interfaces | library calls taking it):")
    for c in sorted(app, key=lambda k: -app[k]["n"]):
        ifaces, calls = facts.get(c, ([], []))
        callees = sorted({callee.split(";.")[0][1:].replace("/", ".") + "." + callee.split(";.")[1]
                          for _, callee in calls})
        print(f"  {app[c]['n']:5d} | {c} | {dict(app[c]['nodes'])} | "
              f"{[i.split('/')[-1][:-1] for i in ifaces]} | {callees} | "
              f"handlers={'yes' if c in handlers else 'NO'}")

    text = open(logcat, errors="replace").read()
    fatal = re.findall(r"FATAL EXCEPTION.*?(?=\n\S{2}-\S{2} \S+\s+\d+\s+\d+ [^E]|\Z)", text, re.S)
    stamp_crash = [b for b in fatal if "mop.RvsecStamp" in b]
    print(f"\nFATAL EXCEPTION blocks: {len(fatal)}; with mop.RvsecStamp frame: {len(stamp_crash)}; "
          f"VerifyError lines: {text.count('VerifyError')}")
    for b in fatal[:3]:
        print("  ---", "\n  ".join(b.splitlines()[:6]))


if __name__ == "__main__":
    main()
