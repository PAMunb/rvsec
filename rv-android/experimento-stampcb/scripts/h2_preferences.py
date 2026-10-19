"""experimento-stampcb, hypothesis H2: do preference callbacks dilute the MOP guidance?

Definitions (every one read from the traces, the logcats or the offline derive):

- Guided step: a step record whose `dec` carries `mopd` (a distance weight).
- Family of a step (H2.1):
    * `preference`, `menu_nav` or `dialog` when `dec.mops = s` and `dec.hnd` is a class that the
      same task's `RVSEC-BIND view kind=callback` lines name as `callback=`; the family is the
      one of the dispatcher on those lines (analyze.FAMILY). A class named under two families is
      `ambiguous`.
    * `stamp_orig` when `dec.mops = s` and `dec.hnd` never appears as a callback in that task (the
      gh121/gh124 stamp path). `id` when `dec.mops = i` (the jar writes `dec.hnd` only for `s`).
    `stamp_orig` + `id` is the "original path".
- Weighted targets of a guided step (H2.2): the pairs `[i, d]` with `d == dec.mopd` of the record
  that gave the weight. For `mops = s`: `handlers[dec.hnd].dist[event]` of the arm's own derive
  (control or treatment `derive(doc)` on the corpus JSON), `event` = click or longclick from the
  action type. For `mops = i`: `widgets[activity][shortId].dist[event]` (falling back to the union
  of the widget's events), with the activity from `act` -> `ACT.name` and the short id from the
  action's resource-id. [inferred for `i`: the jar's weight node may be a descendant of the action's
  node; a step whose record is not found is `unresolved`.] Retired pairs are not removed: d* is the
  smallest unretired distance, so every pair at d* that is retired is also listed (an upper bound).
- Execution: `RVSEC-COV: <sig>` of a weighted target's signature (`distanceTargets[i].signature`).
  RVSEC-COV logs a method the first time per process, so a target already logged by the same pid
  before the step cannot show again; those steps are counted apart (`already`).
- Window: COV lines whose time falls in [t_s, t_{s+1+N}), t_x the step records' `t`, logcat time
  mapped to the trace clock by the median offset of the `ApeRvHb : s= t=` heartbeats. N = 0 is the
  step's own interval: a click's callback runs on the UI thread before APE's next step, so a
  target the callback reaches synchronously at d <= 3 logs there. N = 2 adds two steps for the
  paths that need a follow-up (a dialog confirm, a fragment that loads after a transition).
- Preference screen (H2.3): a step on an APE state (`st`, per task) that holds an androidx
  preference row. The stamp logs `RVSEC-BIND view kind=click handler=androidx.preference.Preference$1`
  (both arms) when a row's listener is bound, not at every dump; the bind falls in the interval
  [t_{s-1}, t_s) of the step s that first sees the screen. Every state of such a step s is a
  preference state, and every step of the task on it counts. [inferred: a row rebound while
  another screen is current would mark that screen; the check column
  `guided_pref_family_on_pref_screen` measures how many preference-family steps the rule finds.]
- Retirement (H2.4): the jar (2cfa8ee2, MopRetirement / StatefulAgent.recordMopInteraction)
  counts, on the first interaction of an (activity, xpath|ActionType) key with weight > 0, one per
  target at d* of the weight's lookup; a target with a count >= ape.mopRetireAfter (3, jar default;
  the A/B does not override it) retires and is listed in that step's `dec.ret`. For each retired
  target: the family of the retiring step, and the guided steps of other families in the same task
  whose weighted targets include it, before and after the retirement.

- Novel targets (H2.2): the distinct targets a family's guided steps were followed by (N = 2),
  and how many of them RVSEC-COV logged in no control rep of the same APK.
- Sanity: the MOP_DATA record of each trace (handlers, targets) against the offline derive.

Writes to analysis/: h2_followed.csv (H2.1 + H2.2), h2_followed_by_d.csv (H2.2 by dec.mopd: at
d = 0 the weighted target is the clicked handler itself), h2_novel.csv (H2.2), h2_screens.csv (H2.3),
h2_retired.csv (H2.4).
Usage: python -I scripts/h2_preferences.py   (from any directory)
"""
import csv
import gzip
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze  # noqa: E402  (reuses the paths, ARMS, FAMILY and load_derive)

X, RES, OUT, CORPUS = analyze.X, analyze.RES, analyze.OUT, analyze.CORPUS
FAMILIES = ("preference", "menu_nav", "dialog", "stamp_orig", "id", "ambiguous")
WINDOWS = (0, 2)
TS = re.compile(r"^(\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\s+(\d+)\s+\d+\s")
HB = re.compile(r"ApeRvHb\s*: s=(\d+) t=(\d+)")
RID = re.compile(r"resource-id=([^;]+);")


def naive_ms(stamp):
    return datetime.strptime("2026-" + stamp, "%Y-%m-%d %H:%M:%S.%f").timestamp() * 1000


def read_trace(path):
    acts, steps = {}, []
    with gzip.open(path, "rt", errors="replace") as fh:
        for line in fh:
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") == "ACT":
                acts[d["id"]] = d["name"]
            elif d.get("type") == "MOP_DATA":
                acts["MOP_DATA"] = d
            elif "s" in d and "dec" in d:
                steps.append(d)
    return acts, steps


def read_logcat(path):
    """COV lines (rel ms, pid, sig), callback lines (rel ms, callback, family), via the heartbeats."""
    raw_cov, raw_cb, raw_pref, offsets = [], [], [], []
    for line in path.read_text(errors="replace").splitlines():
        m = TS.match(line)
        if not m:
            continue
        ms = naive_ms(m.group(1))
        if "RVSEC-COV" in line:
            c = analyze.COV.search(line)
            if c:
                raw_cov.append((ms, m.group(2), c.group(1)))
        elif "kind=callback" in line:
            c = analyze.CALLBACK.search(line)
            if c:
                raw_cb.append((ms, c.group(2), analyze.family(c.group(1))))
        elif "kind=click" in line and "handler=androidx.preference.Preference$1" in line:
            raw_pref.append(ms)
        elif "ApeRvHb" in line:
            h = HB.search(line)
            if h:
                offsets.append(int(h.group(2)) - ms)
    off = statistics.median(offsets)
    return ([(ms + off, pid, sig) for ms, pid, sig in raw_cov], [(ms + off, cb, f) for ms, cb, f in raw_cb],
            [ms + off for ms in raw_pref])


def event_of(action):
    return "longclick" if "MODEL_LONG_CLICK" in action else "click"


def weighted(dec, art, activity):
    """(target indices at d == mopd, how resolved) for a guided step."""
    d, ev = dec["mopd"], event_of(dec["a"])
    if dec.get("mops") == "s":
        rec = art["handlers"].get(dec.get("hnd"))
        if rec is None:
            return set(), "unresolved"
        pairs = rec.get("dist", {}).get(ev, [])
    else:
        m = RID.search(dec["a"])
        w = art["widgets"].get(activity, {}).get(m.group(1).split("/")[-1]) if m else None
        if w is None:
            return set(), "unresolved"
        pairs = w.get("dist", {}).get(ev) or [p for ps in w.get("dist", {}).values() for p in ps]
    idx = {i for i, dd in pairs if dd == d}
    return idx, ("ok" if idx else "unresolved")


def bisect_step(times, t):
    """Index of the last step with time <= t (or -1)."""
    lo, hi = 0, len(times)
    while lo < hi:
        mid = (lo + hi) // 2
        if times[mid] <= t:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1


def main():
    apks = (X / "apks.txt").read_text().split()
    derives = {a: analyze.load_derive(X / "mount" / a / "derive_mop_artifact.py") for a in ("control", "treatment")}
    arts, sigs = {}, {}
    for apk in apks:
        doc = json.loads((CORPUS / f"{apk}.json").read_text())
        sigs[apk] = [t["signature"] for t in doc["distanceTargets"]]
        for a, mod in derives.items():
            arts[a, apk] = mod.derive(doc)
        del doc

    fam_rows, fol, byd = [], Counter(), Counter()
    mismatch = []  # tasks whose MOP_DATA disagrees with the offline derive
    hits = defaultdict(set)  # (arm, apk, family) -> targets newly covered within N = 2
    cov_any = defaultdict(set)  # (arm, apk) -> every RVSEC-COV signature of the 3 reps
    per_task = []  # kept for H2.3 / H2.4
    for arm in ("treatment", "control"):
        for apk, rep, logcat, trace in analyze.runs(arm):
            acts, steps = read_trace(trace)
            cov, cbs, pref = read_logcat(logcat)
            art = arts[arm, apk]
            md = acts.pop("MOP_DATA")
            if (md["handlers"], md["targets"]) != (len(art["handlers"]), art["targets"]):
                mismatch.append((arm, apk, rep, md["handlers"], len(art["handlers"]), md["targets"], art["targets"]))
            cov_any[arm, apk].update(c[2] for c in cov)
            cbfam = defaultdict(set)
            for _, cb, f in cbs:
                cbfam[cb].add(f)
            times = [s["t"] for s in steps]
            pref_states = {steps[k]["st"] for k in (bisect_step(times, t) + 1 for t in pref) if k < len(steps)}
            on_pref = {k for k, s in enumerate(steps) if s["st"] in pref_states}
            cov_sorted = sorted(cov)
            cov_t = [c[0] for c in cov_sorted]
            fams = []
            for k, s in enumerate(steps):
                dec = s["dec"]
                if dec.get("mops") == "s":
                    fs = cbfam.get(dec.get("hnd"), set())
                    fam = "stamp_orig" if not fs else (next(iter(fs)) if len(fs) == 1 else "ambiguous")
                elif dec.get("mops") == "i":
                    fam = "id"
                else:
                    fam = None
                fams.append(fam)
                if "mopd" not in dec:
                    continue
                tg, how = weighted(dec, art, acts.get(s["act"]))
                key = (arm, apk, fam)
                fol[key + ("guided",)] += 1
                byd[arm, fam, dec["mopd"], "guided"] += 1
                if how == "unresolved":
                    fol[key + ("unresolved",)] += 1
                    byd[arm, fam, dec["mopd"], "unresolved"] += 1
                    continue
                tsig = {sigs[apk][i] for i in tg}
                j0 = bisect_step(cov_t, s["t"] - 0.001) + 1  # first COV at or after t_s
                # Covered before the step in the pid that is current at the step.
                pid = cov_sorted[j0 - 1][1] if j0 > 0 else None
                before = {sig for tt, p, sig in cov_sorted[:j0] if p == pid}
                if tsig and tsig <= before:
                    fol[key + ("already",)] += 1
                    byd[arm, fam, dec["mopd"], "already"] += 1
                    continue
                for n in WINDOWS:
                    end = steps[k + 1 + n]["t"] if k + 1 + n < len(steps) else float("inf")
                    got = {sig for tt, _, sig in cov_sorted[j0:] if tt < end and sig in tsig}
                    fol[key + (f"hit_n{n}",)] += bool(got)
                    byd[arm, fam, dec["mopd"], f"hit_n{n}"] += bool(got)
                    if n == 2:
                        hits[arm, apk, fam] |= got
            per_task.append((arm, apk, rep, acts, steps, fams, art, on_pref))

    for arm in ("control", "treatment"):
        for apk in apks + ["ALL"]:
            for fam in FAMILIES:
                ks = [apk] if apk != "ALL" else apks
                g = sum(fol[arm, a, fam, "guided"] for a in ks)
                if not g:
                    continue
                row = dict(arm=arm, apk=apk, family=fam, guided=g)
                for col in ("unresolved", "already", "hit_n0", "hit_n2"):
                    row[col] = sum(fol[arm, a, fam, col] for a in ks)
                tested = g - row["unresolved"] - row["already"]
                row["tested"] = tested
                for n in WINDOWS:
                    row[f"pct_n{n}"] = f'{100 * row[f"hit_n{n}"] / tested:.1f}' if tested else ""
                fam_rows.append(row)

    # H2.3: steps and guided steps on preference screens, per APK and arm.
    scr = []
    for arm in ("control", "treatment"):
        for apk in apks + ["ALL"]:
            c = Counter()
            for a2, ap, rep, acts, steps, fams, _, on_pref in per_task:
                if a2 != arm or (apk != "ALL" and ap != apk):
                    continue
                for k, (s, fam) in enumerate(zip(steps, fams)):
                    on = k in on_pref
                    g = "mopd" in s["dec"]
                    c["steps"] += 1
                    c["steps_pref_screen"] += on
                    c["guided"] += g
                    c["guided_pref_screen"] += g and on
                    c["guided_pref_family"] += g and fam == "preference"
                    c["guided_pref_family_on_pref_screen"] += g and fam == "preference" and on
                    c["guided_non_pref_family"] += g and fam != "preference"
                    c["guided_non_pref_family_off_screen"] += g and fam != "preference" and not on
            scr.append(dict(arm=arm, apk=apk, **c))

    # H2.4: retirements.
    ret_rows = []
    for arm, apk, rep, acts, steps, fams, art, _ in per_task:
        wt = []  # per guided step: (k, fam, hnd or rid, targets)
        for k, (s, fam) in enumerate(zip(steps, fams)):
            if "mopd" in s["dec"]:
                tg, _ = weighted(s["dec"], art, acts.get(s["act"]))
                who = s["dec"].get("hnd") or (RID.search(s["dec"]["a"]) or [None, None])[1]
                wt.append((k, fam, who, tg))
        for k, (s, fam) in enumerate(zip(steps, fams)):
            for i in s["dec"].get("ret", []):
                others_b = [w for w in wt if w[0] < k and i in w[3] and w[1] != fam]
                others_a = [w for w in wt if w[0] > k and i in w[3] and w[1] != fam]
                ret_rows.append(dict(arm=arm, apk=apk, rep=rep, step=s["s"], target=i,
                                     target_sig=sigs[apk][i], retiring_family=fam,
                                     retiring_src=s["dec"].get("src"), retiring_hnd=s["dec"].get("hnd", ""),
                                     other_family_guided_before=len(others_b),
                                     other_family_guided_after=len(others_a),
                                     other_families=";".join(sorted({w[1] or "" for w in others_b + others_a}))))

    def write(name, rows):
        with (OUT / name).open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\n== {name} ({len(rows)} rows)")
        for r in rows[:80]:
            print("  ", " ".join(f"{k}={v}" for k, v in r.items()))

    nov = []
    for apk in apks + ["ALL"]:
        for fam in FAMILIES:
            ks = [apk] if apk != "ALL" else apks
            got = {(a, x) for a in ks for x in hits["treatment", a, fam]}
            if got:
                nov.append(dict(arm="treatment", apk=apk, family=fam, distinct_targets=len(got),
                                not_in_control=sum(x not in cov_any["control", a] for a, x in got),
                                not_in_control_sigs=";".join(sorted(x for a, x in got if x not in cov_any["control", a]))))
    print("MOP_DATA mismatches:", mismatch or "none")
    drows = []
    for (arm, fam, d, col) in sorted({k[:3] + ("guided",) for k in byd}, key=str):
        g = byd[arm, fam, d, "guided"]
        r = dict(arm=arm, family=fam, mopd=d, guided=g,
                 **{c: byd[arm, fam, d, c] for c in ("unresolved", "already", "hit_n0", "hit_n2")})
        r["tested"] = g - r["unresolved"] - r["already"]
        drows.append(r)
    write("h2_followed_by_d.csv", drows)
    write("h2_followed.csv", fam_rows)
    write("h2_novel.csv", nov)
    write("h2_screens.csv", scr)
    write("h2_retired.csv", ret_rows)


if __name__ == "__main__":
    main()
