"""Group 6 measurements of gh-tbd-gator-distance-paths.

Reads the baseline full documents (old jar) and the new documents (full, compact,
compact+paths, full+paths) and prints:
- per APK effect sizes, baseline full against new full (6.3);
- the cases of targets63.csv in the measured APKs, before and after (6.2);
- the EmptySiteEdges log lines (6.3);
- the path invariants INV-ANA-90, -91, -92, -93 (6.4).

Run: uv run python -I experimento-gtpaths/scripts/compare.py  (from rv-android/ of the worktree)
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "baseline" / "full"
NEW = ROOT / "new"
APKS = [
    "cryptoapp",
    "net.gaast.giggity_769",
    "org.cry.otp_31",
    "org.fedorahosted.freeotp_48",
    "com.vrem.wifianalyzer_71",
    "systems.sieber.droid_scep_7",
]
PATH_KEYS = ("pathMethods", "distancePaths")


def doc(cfg_dir: Path, apk: str) -> Path:
    return cfg_dir / f"{apk}.apk.d" / f"{apk}.apk.json"


def load(p: Path) -> dict:
    with p.open() as f:
        return json.load(f)


def methods(d: dict) -> dict:
    return {m["signature"]: m for c in d.get("reachability", []) for m in c.get("methods", [])}


def flags(ms: dict) -> dict:
    return {
        "reachable": sum(bool(m.get("reachable")) for m in ms.values()),
        "reachesTarget": sum(bool(m.get("reachesTarget")) for m in ms.values()),
        "directlyReachesTarget": sum(bool(m.get("directlyReachesTarget")) for m in ms.values()),
        "pairs": sum(len(m.get("targetDistances") or []) for m in ms.values()),
    }


def effect_sizes() -> None:
    print("## 6.3 effect sizes (baseline full -> new full)")
    for apk in APKS:
        b, n = load(doc(BASE, apk)), load(doc(NEW / "full", apk))
        fb, fn = flags(methods(b)), flags(methods(n))
        tb = [(t["signature"], t["kind"]) for t in b["distanceTargets"]]
        tn = [(t["signature"], t["kind"]) for t in n["distanceTargets"]]
        drt_b = {s for s, m in methods(b).items() if m.get("directlyReachesTarget")}
        drt_n = {s for s, m in methods(n).items() if m.get("directlyReachesTarget")}
        print(
            f"{apk}: "
            + ", ".join(f"{k} {fb[k]}->{fn[k]}" for k in fb)
            + f"; distanceTargets equal={tb == tn}; directlyReachesTarget set equal={drt_b == drt_n}"
            + f"; windows {len(b.get('windows', []))}->{len(n.get('windows', []))}"
            + f"; transitions {len(b.get('transitions', []))}->{len(n.get('transitions', []))}"
        )


def cases() -> None:
    print("\n## 6.2 cases of targets63.csv in the measured APKs")
    with (ROOT / "targets63.csv").open() as f:
        rows = [r for r in csv.DictReader(f) if r["in_e2e_set"] == "True"]
    for r in rows:
        apk = r["apk"][: -len(".apk")]
        mb, mn = methods(load(doc(BASE, apk))), methods(load(doc(NEW / "full", apk)))
        sig = r["target"]

        def show(m):
            if m is None:
                return "absent"
            return f"reachable={m.get('reachable')} reachesTarget={m.get('reachesTarget')}"

        print(f"{apk} i={r['i']} misuse={r['misuse']} {sig}\n   before: {show(mb.get(sig))}\n   after:  {show(mn.get(sig))}")


def empty_site_lines() -> None:
    print("\n## 6.3 EmptySiteEdges (new full logs)")
    for apk in APKS:
        log = (NEW / "full" / f"{apk}.apk.d" / "analysis.log").read_text(errors="replace")
        lines = [ln for ln in log.splitlines() if "[EmptySiteEdges]" in ln]
        print(f"{apk}:")
        for ln in lines:
            print("   " + ln[ln.index("[EmptySiteEdges]"):][:300])


def chains(d: dict) -> tuple[int, int, int]:
    """INV-ANA-91 and -93: rebuild every written pair's chain from the steps.

    Returns (pairs checked, steps, steps on no chain); raises on a broken chain.
    """
    pm, steps, targets = d["pathMethods"], d["distancePaths"], d["distanceTargets"]
    nxt = {}
    for i, v, n in steps:
        assert (i, v) not in nxt, f"two steps for {(i, v)}"
        nxt[(i, v)] = n
    assert [s[:2] for s in steps] == sorted(s[:2] for s in steps), "steps not sorted by (i, v)"
    assert pm == sorted(pm), "pathMethods not sorted"
    idx = {s: k for k, s in enumerate(pm)}
    used = set()
    checked = 0
    for sig, m in methods(d).items():
        for i, dist in m.get("targetDistances") or []:
            checked += 1
            if dist == 0:
                continue
            v = idx[sig]
            for _ in range(dist):
                used.add((i, v))
                v = nxt[(i, v)]
            assert pm[v] == targets[i]["signature"], f"chain of {sig} for {i} ends at {pm[v]}"
    return checked, len(steps), len(set(nxt) - used)


def strip_paths(p: Path) -> bytes:
    """The document's bytes without the two path members (compact form: no whitespace)."""
    # The members sit between reachability and windows; signatures hold "[]", so cut by the
    # member names rather than by bracket matching.
    raw = p.read_bytes()
    start = raw.index(b',"pathMethods":')
    end = raw.index(b',"windows":', start)
    assert raw.find(b',"distancePaths":', start, end) > start
    return raw[:start] + raw[end:]


def path_checks() -> None:
    print("\n## 6.4 path invariants")
    for apk in APKS:
        a, b = doc(NEW / "compact", apk), doc(NEW / "compact-paths", apk)
        same = strip_paths(b) == a.read_bytes()
        d = load(b)
        print(f"{apk}: INV-ANA-90 compact+paths minus members == compact: {same}; "
              f"sizes {a.stat().st_size} / {b.stat().st_size} B; "
              f"(pairs, steps, steps on no chain) = {chains(d)}")
    for apk in ("cryptoapp", "org.cry.otp_31"):
        p = doc(NEW / "full-paths", apk)
        print(f"{apk} full+paths: {p.stat().st_size} B; (pairs, steps, off-chain) = {chains(load(p))}")
    a, b = doc(NEW / "compact-paths", "org.cry.otp_31"), doc(NEW / "compact-paths-rerun", "org.cry.otp_31")
    da, db = load(a), load(b)
    print("org.cry.otp_31 INV-ANA-92 rerun: pathMethods/distancePaths equal = "
          f"{all(da[k] == db[k] for k in PATH_KEYS)}; whole file equal = {a.read_bytes() == b.read_bytes()}")


def transition_keys(d: dict) -> set:
    """Transitions as a set of (src window, tgt window, event type, handler); ids map to names."""
    names = {w["id"]: w["name"] for w in d.get("windows", [])}
    return {
        (names.get(t["sourceId"], t["sourceId"]), names.get(t["targetId"], t["targetId"]), e["type"], e["handler"])
        for t in d.get("transitions", [])
        for e in t["events"]
    }


def client_end(log: Path) -> str:
    lines = [ln for ln in log.read_text(errors="replace").splitlines() if "[RvsecAnalysisClient] End:" in ln]
    return lines[-1].rsplit("End:", 1)[1].strip() if lines else "?"


def rerun_55() -> None:
    """6.7: the 5.5 jar keeps the empty-site edges out of the WTG and nothing else moves."""
    print("## 6.7 full with the 5.5 jar (WTG against baseline, reachability against the 5.3 run)")
    for apk in APKS:
        b, n, r = (load(doc(c, apk)) for c in (BASE, NEW / "full", NEW / "full-5.5"))
        tb, tr = transition_keys(b), transition_keys(r)
        mn, mr = methods(n), methods(r)
        reach_eq = all(
            {s: m.get(k) for s, m in mn.items()} == {s: m.get(k) for s, m in mr.items()}
            for k in ("reachable", "reachesTarget", "directlyReachesTarget", "targetDistances")
        )
        log = NEW / "full-5.5" / f"{apk}.apk.d" / "analysis.log"
        removed = [ln[ln.index("Empty-site"):] for ln in log.read_text(errors="replace").splitlines()
                   if "Empty-site edges removed" in ln]
        print(
            f"{apk}: windows == baseline: {b['windows'] == r['windows']}; "
            f"transitions as set == baseline: {tb == tr} ({len(tb)} keys, +{len(tr - tb)} -{len(tb - tr)}); "
            f"reachability fields == 5.3 full: {reach_eq}; distanceTargets == 5.3: {n['distanceTargets'] == r['distanceTargets']}; "
            f"flags {flags(mr)}; client End: baseline {client_end(doc(BASE, apk).parent / 'analysis.log')} / "
            f"5.3 {client_end(doc(NEW / 'full', apk).parent / 'analysis.log')} / 5.5 {client_end(log)} s; "
            f"{removed}"
        )


if __name__ == "__main__":
    for part in sys.argv[1:] or ["effect", "cases", "empty", "paths"]:
        {"effect": effect_sizes, "cases": cases, "empty": empty_site_lines, "paths": path_checks,
         "rerun55": rerun_55}[part]()
