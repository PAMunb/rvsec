"""Per-APK static statistics over the E6 v2 final .apk.json files (streaming, low memory).

Usage: static_stats.py <final_dir> <out_csv> [workers]
"""
import csv
import os
import sys
from collections import Counter
from multiprocessing import Pool

import ijson

COMPOSER = "androidx.compose.runtime.Composer"


def head_tail(path):
    with open(path, "rb") as f:
        head = f.read(4096).decode("utf-8", "replace")
        f.seek(max(0, os.path.getsize(path) - 256))
        tail = f.read().decode("utf-8", "replace")
    complete = "absent"
    if '"complete"' in tail:
        complete = "true" if '"complete": true' in tail or '"complete":true' in tail else "false"
    return head, complete


def items(path, prefix):
    with open(path, "rb") as f:
        yield from ijson.items(f, prefix, use_float=True)


def stats(path):
    apk = os.path.basename(path)[: -len(".json")]
    _, complete = head_tail(path)
    r = Counter()
    r["complete"] = complete
    kinds = Counter(t["kind"] for t in items(path, "distanceTargets.item"))
    r["targets"] = sum(kinds.values())
    r["targets_direct"] = kinds.get("direct", 0)
    r["targets_boundary"] = kinds.get("boundary", 0)

    # method signature -> (reachesTarget, min distance or None)
    meth = {}
    for c in items(path, "reachability.item"):
        r["classes"] += 1
        if c.get("componentType"):
            r["component_classes"] += 1
        for m in c["methods"]:
            r["methods"] += 1
            sig = m["signature"]
            rt = bool(m["reachesTarget"])
            r["m_reachable"] += bool(m["reachable"])
            r["m_reachesTarget"] += rt
            r["m_direct"] += bool(m["directlyReachesTarget"])
            td = m.get("targetDistances")
            dmin = min(d for _, d in td) if td else None
            if td:
                r["m_with_dist"] += 1
                r["m_dist_le3"] += dmin <= 3
            elif rt:
                r["m_rt_no_dist"] += 1
            if COMPOSER in sig:
                r["m_composable"] += 1
                r["m_composable_rt"] += rt
            meth[sig] = (rt, dmin)

    def classify(h):
        rt, dmin = meth.get(h, (False, None))
        return rt, dmin

    wtypes = Counter()
    handlers = set()
    for w in items(path, "windows.item"):
        r["windows"] += 1
        wtypes[w["type"]] += 1
        for wd in w["widgets"]:
            r["widgets"] += 1
            if "compose" in (wd.get("type") or "").lower():
                r["widgets_composeview"] += 1
            ls = wd.get("listeners") or []
            if ls:
                r["widgets_with_listener"] += 1
            best = None
            any_rt = False
            for l in ls:
                handlers.add(l["handler"])
                rt, dmin = classify(l["handler"])
                any_rt |= rt
                if dmin is not None:
                    best = dmin if best is None else min(best, dmin)
            r["widgets_rt"] += any_rt
            r["widgets_dist"] += best is not None
            r["widgets_dist_le3"] += best is not None and best <= 3
    for t, n in wtypes.items():
        r["win_" + t] = n

    for t in items(path, "transitions.item"):
        r["transitions"] += 1
        for e in t["events"]:
            r["events"] += 1
            h = e.get("handler")
            if h:
                handlers.add(h)
                rt, _ = classify(h)
                r["events_rt"] += rt
    r["handlers"] = len(handlers)
    hs = [classify(h) for h in handlers]
    r["handlers_rt"] = sum(rt for rt, _ in hs)
    r["handlers_dist"] = sum(d is not None for _, d in hs)
    r["handlers_dist_le3"] = sum(d is not None and d <= 3 for _, d in hs)
    r["handlers_composable"] = sum(COMPOSER in h for h in handlers)
    r["json_bytes"] = os.path.getsize(path)
    return apk, dict(r)


def main():
    src, out = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    files = sorted(os.path.join(src, f) for f in os.listdir(src) if f.endswith(".apk.json"))
    files.sort(key=os.path.getsize, reverse=True)  # largest first: the 9 GB one is the long pole
    rows = []
    with Pool(workers) as p:
        for apk, r in p.imap_unordered(stats, files):
            rows.append({"apk": apk, **r})
            print(apk, r.get("methods"), file=sys.stderr, flush=True)
    cols = ["apk"] + sorted({k for row in rows for k in row} - {"apk"})
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, restval=0)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda x: x["apk"]))


if __name__ == "__main__":
    main()
