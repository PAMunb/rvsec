"""aperv's question on option 1: a stamped class listed in `handlers` wins in MopData.lookup even
with no pair (source STAMP), so the widget's id key is no longer consulted. Per APK: widgets
(resource-id) whose steps had dec.mops = i in the control, and how their steps resolve in the
treatment (mops i / s / none; with or without dec.mopd).

Usage: python -I scripts/id_key_loss.py
"""
import gzip, json, re
from collections import Counter, defaultdict
from pathlib import Path

RES = Path(__file__).resolve().parent.parent / "results"
ARMS = {"control": ("stampcb_con_a", "stampcb_con_b"), "treatment": ("stampcb_tre_a", "stampcb_tre_b")}
RID = re.compile(r"resource-id=([^;]+);")

per = defaultdict(lambda: defaultdict(Counter))  # arm -> (apk, rid) -> Counter
for arm, cs in ARMS.items():
    for c in cs:
        for t in (RES / c / c).glob("*/*.trace.ndjson.gz"):
            apk = t.parent.name
            for line in gzip.open(t, "rt", errors="replace"):
                if not line.startswith('{"s"'):
                    continue
                dec = json.loads(line)["dec"]
                m = RID.search(dec["a"])
                if not m:
                    continue
                k = per[arm][apk, m.group(1)]
                k["steps"] += 1
                k["mops_" + str(dec.get("mops"))] += 1
                k["mopd_" + str(dec.get("mops"))] += "mopd" in dec
id_widgets = {w for w, c in per["control"].items() if c["mops_i"]}
by_apk = defaultdict(Counter)
for w in id_widgets:
    con, tre = per["control"][w], per["treatment"].get(w, Counter())
    a = by_apk[w[0]]
    a["widgets"] += 1
    a["con_steps"] += con["steps"]; a["con_i"] += con["mops_i"]; a["con_i_mopd"] += con["mopd_i"]
    a["tre_steps"] += tre["steps"]; a["tre_i"] += tre["mops_i"]; a["tre_i_mopd"] += tre["mopd_i"]
    a["tre_s"] += tre["mops_s"]; a["tre_s_mopd"] += tre["mopd_s"]
    a["lost"] += tre["steps"] > 0 and tre["mops_i"] == 0 and tre["mops_s"] > 0
tot = Counter()
for apk, a in sorted(by_apk.items()):
    tot.update(a)
    print(apk, dict(a))
print("ALL", dict(tot))
