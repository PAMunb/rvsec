"""experimento-stampcb, step 4: control x treatment from the logcats and traces of results/.

Writes to analysis/:
- steps.csv      per (arm, apk, rep): steps, steps with dec.mopd, dec.mops = s (stamp) / i (id),
                 steps whose dec.hnd is a class the treatment derive newly gives a d <= 3 pair;
- delivery.csv   treatment `RVSEC-BIND view kind=callback` lines per APK and dispatcher family;
- callbacks.csv  each (apk, dispatcher, callback) the treatment named, lines, and in how many reps
                 of each arm RVSEC-COV saw a callback method of that class;
- direct.csv     direct JCA targets "only behind a callback" (bands 2 and 4 of mini-experimento's
                 r_direct_full.csv): reps per arm whose RVSEC-COV has the target;
- sanity.csv     per (arm, apk): FATAL EXCEPTION, frames of mop.RvsecStamp, VerifyError;
- misuses.csv    per (arm, apk): primary misuse sites (class, method, spec; label violation or
                 sequence, as extract.py), union of the reps and per rep, and RVSEC-OCC lines.

Usage: python -I scripts/analyze.py   (from the experiment directory)
"""
import csv
import gzip
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

X = Path(__file__).resolve().parent.parent
RES = X / "results"
OUT = X / "analysis"
CORPUS = Path("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/"
              "rvsec-study03-replication-package/data/raw/e6-corpus")
CODES = Path("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/"
             "rvsec-study03-replication-package/experiments/E6-campaign/config/codes.csv")
CODES_SHA256 = "a538ea4023490bae048da71485e0247b820ed7501232dfbd8ba3775a417aa724"
DIRECT = Path("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/"
              "data/e03igg_analysis/out/rp_guidance/r_direct_full.csv")
ARMS = {"control": ("stampcb_con_a", "stampcb_con_b"), "treatment": ("stampcb_tre_a", "stampcb_tre_b")}
REPS = (1, 2, 3)

# Callback method names per family, as m_callbacks.py of mini-experimento (dialog by signature).
CALLBACK_NAMES = {"onOptionsItemSelected", "onNavigationItemSelected", "onMenuItemClick", "onMenuItemSelected",
                  "onPreferenceClick", "onPreferenceChange", "onPreferenceTreeClick"}
FAMILY = [("menu_nav", re.compile(r"ActionMenuItemView|NavigationMenu|NavigationBar|Toolbar|MenuItem")),
          ("preference", re.compile(r"Preference")), ("dialog", re.compile(r"AlertController"))]
CALLBACK = re.compile(r"kind=callback .*?handler=(\S+) callback=(\S+)")
COV = re.compile(r"RVSEC-COV: (<[^:]+: .+>)\s*$")
MISUSE = re.compile(r"\bRVSEC\s*:\s*([^,\s]+,.+)$")
CODE = re.compile(r"\bcode=(\S+)")
PRIMARY = {"violation", "sequence"}


def family(handler):
    return next((f for f, rx in FAMILY if rx.search(handler)), "other")


def load_derive(path):
    spec = importlib.util.spec_from_file_location(path.parent.name + "_derive", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def near(rec):
    return any(d <= 3 for pairs in rec.get("dist", {}).values() for _, d in pairs)


def is_callback_method(cls, sig):
    """An RVSEC-COV signature that is the callback body of `cls`: a family method of the class, or
    any method of a D8/kotlinc lambda class (its single method is the callback)."""
    name = sig.split("(")[0].rsplit(" ", 1)[-1]
    if name in CALLBACK_NAMES:
        return True
    if name == "onClick" and "android.content.DialogInterface" in sig:
        return True
    return ("$$ExternalSyntheticLambda" in cls or "$$Lambda" in cls) and name not in ("<init>", "<clinit>")


def runs(arm):
    for container in ARMS[arm]:
        for logcat in sorted((RES / container / container).glob("*/*__*__300__aperv:mop.logcat")):
            apk = logcat.parent.name
            rep = int(logcat.name[len(apk) + 2:].split("__")[0])
            yield apk, rep, logcat, Path(str(logcat)[:-len(".logcat")] + ".trace.ndjson.gz")


def steps_of(trace):
    with gzip.open(trace, "rt", errors="replace") as fh:
        for line in fh:
            if line.startswith('{"s"'):
                try:
                    yield json.loads(line)["dec"]
                except (json.JSONDecodeError, KeyError):
                    continue


def write(name, rows):
    OUT.mkdir(exist_ok=True)
    with (OUT / name).open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n== {name}")
    for r in rows:
        print("  ", " ".join(f"{k}={v}" for k, v in r.items()))


def main():
    data = CODES.read_bytes()
    if hashlib.sha256(data).hexdigest() != CODES_SHA256:
        raise SystemExit("codes.csv sha256 mismatch")
    labels = {r["code"]: r["label"] for r in csv.DictReader(data.decode().splitlines())}

    apks = (X / "apks.txt").read_text().split()
    control, treatment = (load_derive(X / "mount" / a / "derive_mop_artifact.py") for a in ("control", "treatment"))
    added = {}
    for apk in apks:
        doc = json.loads((CORPUS / f"{apk}.json").read_text())
        hc, ht = control.derive(doc)["handlers"], treatment.derive(doc)["handlers"]
        added[apk] = {c for c in ht if near(ht[c]) and not (c in hc and near(hc[c]))}
        del doc

    direct = [r for r in csv.DictReader(DIRECT.open()) if r["apk"] in apks and r["band"][:2] in ("2 ", "4 ")]

    step_rows, sanity, misuse_rows = [], [], []
    deliv = Counter()
    named = Counter()  # (apk, dispatcher, callback) -> lines
    cov = defaultdict(set)  # (arm, apk, rep) -> RVSEC-COV signatures
    for arm in ARMS:
        crash = defaultdict(Counter)
        sites = defaultdict(dict)
        occ = Counter()
        for apk, rep, logcat, trace in runs(arm):
            lines = logcat.read_text(errors="replace").splitlines()
            rep_sites = set()
            for i, line in enumerate(lines):
                if "RVSEC" in line:
                    m = COV.search(line)
                    if m:
                        cov[arm, apk, rep].add(m.group(1))
                        continue
                    if "RVSEC-OCC" in line:
                        occ[apk] += 1
                        continue
                    m = CALLBACK.search(line)
                    if m:
                        deliv[apk, family(m.group(1))] += 1
                        named[apk, m.group(1), m.group(2)] += 1
                        continue
                    m = MISUSE.search(line)
                    if m:
                        p = m.group(1).split(",", 4)
                        cm = CODE.search(line)
                        if len(p) >= 4 and cm and labels.get(cm.group(1)) in PRIMARY:
                            rep_sites.add((p[1], p[3], p[0]))
                        continue
                if "FATAL EXCEPTION" in line:
                    # The app's process carries a build suffix (.debug, .dev, .beta): match the
                    # first two components of the package.
                    proc = next((x for x in lines[i + 1:i + 3] if "Process:" in x), "")
                    if "Process: " + ".".join(apk.split(".")[:2]) in proc:
                        crash[apk]["fatal"] += 1
                elif "at mop.RvsecStamp" in line:
                    crash[apk]["stamp_frame"] += 1
                elif "VerifyError" in line:
                    crash[apk]["verify_error"] += 1
            sites[apk][rep] = rep_sites

            c = Counter()
            for dec in steps_of(trace):
                c["steps"] += 1
                d = "mopd" in dec
                c["mopd"] += d
                c["mops_s"] += dec.get("mops") == "s"
                c["mops_i"] += dec.get("mops") == "i"
                c["mopd_s"] += d and dec.get("mops") == "s"
                c["src_mop"] += dec.get("src") == "mop"
                h = dec.get("hnd") in added[apk]
                c["hnd_added"] += h
                c["mopd_hnd_added"] += d and h
            step_rows.append(dict(arm=arm, apk=apk, rep=rep, **{k: c[k] for k in (
                "steps", "mopd", "mops_s", "mops_i", "mopd_s", "src_mop", "hnd_added", "mopd_hnd_added")}))
        for apk in apks:
            sanity.append(dict(arm=arm, apk=apk, fatal=crash[apk]["fatal"], stamp_frame=crash[apk]["stamp_frame"],
                               verify_error=crash[apk]["verify_error"]))
            per = [len(sites[apk].get(r, ())) for r in REPS]
            union = set().union(*sites[apk].values()) if sites[apk] else set()
            misuse_rows.append(dict(arm=arm, apk=apk, sites_union=len(union), sites_per_rep="/".join(map(str, per)),
                                    occ_lines=occ[apk]))
    write("steps.csv", step_rows)
    tot = []
    for arm in ARMS:
        for apk in apks + ["ALL"]:
            rs = [r for r in step_rows if r["arm"] == arm and (apk == "ALL" or r["apk"] == apk)]
            s = Counter()
            for r in rs:
                s.update({k: v for k, v in r.items() if isinstance(v, int) and k != "rep"})
            tot.append(dict(arm=arm, apk=apk, steps=s["steps"],
                            mopd=f'{s["mopd"]} ({100 * s["mopd"] / s["steps"]:.1f}%)',
                            mops_s=f'{s["mops_s"]} ({100 * s["mops_s"] / s["steps"]:.1f}%)',
                            mopd_s=f'{s["mopd_s"]} ({100 * s["mopd_s"] / s["steps"]:.1f}%)',
                            src_mop=s["src_mop"], hnd_added=s["hnd_added"], mopd_hnd_added=s["mopd_hnd_added"]))
    write("steps_summary.csv", tot)
    write("delivery.csv", [dict(apk=a, family=f, lines=n) for (a, f), n in sorted(deliv.items())])
    cb_rows = []
    for (apk, disp, cb), n in sorted(named.items()):
        row = dict(apk=apk, family=family(disp), dispatcher=disp, callback=cb, lines=n)
        for arm in ARMS:
            row[f"cov_reps_{arm}"] = sum(any(sig.startswith(f"<{cb}: ") and is_callback_method(cb, sig)
                                             for sig in cov[arm, apk, r]) for r in REPS)
        row["in_added"] = cb in added[apk]
        cb_rows.append(row)
    write("callbacks.csv", cb_rows)
    write("direct.csv", [dict(apk=r["apk"], target=r["target"], band=r["band"],
                              **{f"cov_reps_{arm}": sum(r["target"] in cov[arm, r["apk"], k] for k in REPS)
                                 for arm in ARMS}) for r in direct])
    write("sanity.csv", sanity)
    write("misuses.csv", misuse_rows)
    write("added_handlers.csv", [dict(apk=a, added_near=len(added[a])) for a in apks])


if __name__ == "__main__":
    main()
