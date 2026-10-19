"""Offline check of the treatment artifact: per APK, the `handlers` table of the control
and treatment derive, and the classes the patch adds with a pair at d <= 3.

Usage: python -I compare_handlers.py <mount-dir> <corpus-dir> <apk-stem>...
"""
import importlib.util
import json
import sys
from pathlib import Path


def load(path):
    spec = importlib.util.spec_from_file_location(path.parent.name + "_derive", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def near(rec):
    return any(d <= 3 for pairs in rec.get("dist", {}).values() for _, d in pairs)


mount, corpus = Path(sys.argv[1]), Path(sys.argv[2])
control = load(mount / "control" / "derive_mop_artifact.py")
treatment = load(mount / "treatment" / "derive_mop_artifact.py")
for stem in sys.argv[3:]:
    doc = json.loads((corpus / f"{stem}.apk.json").read_text())
    hc = control.derive(doc)["handlers"]
    ht = treatment.derive(doc)["handlers"]
    changed = sorted(c for c in ht if ht[c] != hc.get(c))
    added_near = [c for c in changed if near(ht[c]) and not (c in hc and near(hc[c]))]
    print(f"{stem}: handlers {len(hc)} -> {len(ht)}, changed {len(changed)}, "
          f"newly near (d<=3) {len(added_near)}")
    for c in added_near[:12]:
        print("   ", c)
