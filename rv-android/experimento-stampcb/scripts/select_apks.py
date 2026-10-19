"""Rank A/B candidates: view-only/mixed APKs whose logcat bound library dispatchers of the
menu/navigation, preference or dialog family (e03igg), and whose treatment artifact gives a
d <= 3 record to a callback the patched stamp can name: an activity's onOptionsItemSelected,
or a navigation/menu-click/menu-provider/preference/DialogInterface listener. A fragment's
onOptionsItemSelected is left out: the stamp names the activity, not the fragment.

Usage: python -I select_apks.py <mount-dir> <corpus-dir> <m_callbacks_per_apk.csv> <out.csv>
"""
import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

mount, corpus, per_apk, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
spec = importlib.util.spec_from_file_location("treatment_derive", mount / "treatment" / "derive_mop_artifact.py")
derive = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = derive
spec.loader.exec_module(derive)

NAMEABLE = {"onNavigationItemSelected", "onMenuItemClick", "onMenuItemSelected", "onPreferenceClick",
            "onPreferenceChange", "onPreferenceTreeClick"}
SIG = re.compile(r"^<(?P<cls>[^:]+): \S+ (?P<name>\w+)\((?P<params>[^)]*)\)>$")

rows = []
for r in csv.DictReader(open(per_apk)):
    lib = int(r["bind_lib_menu_nav"]) + int(r["bind_lib_preference"]) + int(r["bind_lib_dialog"])
    if r["ui_tech"] not in ("view-only", "mixed") or lib == 0:
        continue
    path = corpus / f"{r['apk']}.json"
    if path.stat().st_size > 50_000_000:
        continue
    doc = json.loads(path.read_text())
    handlers = derive.derive(doc)["handlers"]
    activities = {e.get("className") for e in doc.get("reachability", []) if e.get("componentType") == "activity"}
    names = {}
    for e in doc.get("reachability", []):
        for m in e.get("methods", []):
            s = SIG.match(m.get("signature", ""))
            if not s or derive.CALLBACK_PARAMS.get(s["name"]) != s["params"]:
                continue
            ok = s["name"] in NAMEABLE or s["name"] == "onClick" or (
                s["name"] == "onOptionsItemSelected" and s["cls"] in activities)
            rec = handlers.get(s["cls"], {})
            near = any(d <= 3 for pairs in rec.get("dist", {}).values() for _, d in pairs)
            if ok and near:
                names[s["cls"] + "." + s["name"]] = True
    rows.append(dict(apk=r["apk"], ui_tech=r["ui_tech"], bind_lib_menu_nav=r["bind_lib_menu_nav"],
                     bind_lib_preference=r["bind_lib_preference"], bind_lib_dialog=r["bind_lib_dialog"],
                     nameable_near=len(names), examples=" ".join(sorted(names)[:4])))
rows.sort(key=lambda x: (-x["nameable_near"], x["apk"]))
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
for x in rows[:20]:
    print(x["apk"], x["ui_tech"], x["bind_lib_menu_nav"], x["bind_lib_preference"], x["bind_lib_dialog"], x["nameable_near"])
print("candidates with nameable_near>0:", sum(1 for x in rows if x["nameable_near"]), "of", len(rows))
