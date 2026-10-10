"""Per-APK approximation of the format-2 `handlers` table (gh122) from the final .apk.json.

Handler methods follow HANDLER_METHOD_PATTERN of aperv-tool derive_mop_artifact.py:
onClick(View), onLongClick(View), Object invoke()/invoke(Object). Counted per class.
Usage: handler_table_stats.py <final_dir> <out_csv> [workers]
"""
import csv, os, re, sys
from multiprocessing import Pool
import ijson

PAT = re.compile(r"^<(?P<cls>[^:]+): (?P<ret>\S+) (?P<name>onClick|onLongClick|invoke)\((?P<params>[^)]*)\)>$")


def is_handler(sig):
    m = PAT.match(sig)
    if not m:
        return False
    n, p = m["name"], m["params"]
    if n in ("onClick", "onLongClick"):
        return p == "android.view.View"
    return m["ret"] == "java.lang.Object" and p in ("", "java.lang.Object")


def stats(path):
    cls = {}  # class -> [reaches, dmin, is_invoke]
    with open(path, "rb") as f:
        for c in ijson.items(f, "reachability.item"):
            for m in c["methods"]:
                s = m["signature"]
                if not is_handler(s):
                    continue
                k = PAT.match(s)["cls"]
                td = m.get("targetDistances")
                d = min(x for _, x in td) if td else None
                e = cls.setdefault(k, [False, None, "invoke(" in s])
                e[0] |= bool(m["reachesTarget"])
                if d is not None:
                    e[1] = d if e[1] is None else min(e[1], d)
    r = {"h_classes": len(cls)}
    for tag, sel in (("all", lambda v: True), ("invoke", lambda v: v[2]), ("view", lambda v: not v[2])):
        vs = [v for v in cls.values() if sel(v)]
        r[f"h_{tag}"] = len(vs)
        r[f"h_{tag}_rt"] = sum(v[0] for v in vs)
        r[f"h_{tag}_dist"] = sum(v[1] is not None for v in vs)
        r[f"h_{tag}_le3"] = sum(v[1] is not None and v[1] <= 3 for v in vs)
    return os.path.basename(path)[: -len(".json")], r


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    files = sorted((os.path.join(src, f) for f in os.listdir(src) if f.endswith(".apk.json")), key=os.path.getsize, reverse=True)
    with Pool(int(sys.argv[3]) if len(sys.argv) > 3 else 10) as p:
        rows = [{"apk": a, **r} for a, r in p.imap_unordered(stats, files)]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(sorted(rows, key=lambda x: x["apk"]))
