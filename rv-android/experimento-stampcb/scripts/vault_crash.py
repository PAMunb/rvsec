"""Each FATAL EXCEPTION of se.arctosoft.vault (arms _b) matched to the last APE step before it,
with the btnUnlock clicks and BACK steps from the unlocked state (g0s3) per rep.

Usage: python -I scripts/vault_crash.py results
"""
import sys, json, gzip, re, glob, datetime, collections
R = sys.argv[1]
for arm in ("con_b", "tre_b"):
    for rep in (1, 2, 3):
        base = glob.glob(f"{R}/stampcb_{arm}/*/se.arctosoft*/*__{rep}__300__aperv:mop.logcat")[0][:-len(".logcat")]
        steps, t0 = [], None
        for l in gzip.open(base + ".trace.ndjson.gz", "rt"):
            if not l.startswith("{"): continue
            try: d = json.loads(l)
            except Exception: continue
            if d.get("type") == "RUN_START": t0 = d["t0"]
            elif "s" in d and "dec" in d: steps.append(d)
        unlock = sum("btnUnlock" in s["dec"]["a"] for s in steps)
        mopsrc = sum(1 for s in steps if s["dec"].get("src") == "mop")
        crashes = []
        lines = open(base + ".logcat", errors="replace").read().splitlines()
        year = 2026
        for i, l in enumerate(lines):
            if "FATAL EXCEPTION" in l:
                sig = next((x for x in lines[i+1:i+4] if "Exception" in x and "AndroidRuntime" in x), "")
                ts = datetime.datetime.strptime(f"{year}-" + l[:18], "%Y-%m-%d %H:%M:%S.%f")
                ms = ts.timestamp() * 1000 - t0
                prev = [s for s in steps if s["t"] <= ms]
                p = prev[-1] if prev else None
                kind = "DirHash" if "DirHash" in sig else ("notAttached" if "not attached" in sig else sig.split("AndroidRuntime: ")[-1][:40])
                pa = re.sub(r"^.*?@", "", p["dec"]["a"])[:90] if p else "-"
                crashes.append((kind, p["s"] if p else None, p["dec"].get("src") if p else None, p["dec"].get("mops") if p else None, pa))
        print(f"{arm} rep{rep}: steps={len(steps)} src=mop:{mopsrc} btnUnlock_clicks={unlock} crashes={len(crashes)}")
        for c in crashes: print("   ", c)
