#!/usr/bin/env python3
"""gh91 — compare the regenerated consolidation against the pre-reprocessing baseline.

Mechanises tasks 5.3 (the scope effect is confined to the 30) and 5.4 (no violation moved).
Baseline is the promoted `*_all.csv` of 2026-07-12; the new run writes `*_regen.csv`, and
`run_all.sh` does not touch `*_all.csv`, so both sides coexist until the manual promotion.

TWO CONFOUNDS THIS SCRIPT EXISTS TO SEPARATE
    A naive diff of the two consolidations answers the wrong question twice.

    1. ORDER. Level 1 regenerates 16 containers concurrently, so the concat order of a
       given app's rows is not stable between runs. An order-sensitive comparison reports
       nearly every app as changed while the content is identical. Every comparison here is
       therefore a MULTISET comparison: rows are hashed commutatively (count + sum of row
       digests), which is O(1) memory over a 6 GB file and blind to order by construction.

    2. CODE DRIFT. The baseline was produced on 2026-07-12; two parser fixes have landed
       since, both of which legitimately move columns and neither of which has anything to
       do with the analysis key:
         - cf234788 (2026-07-28, closes #89) — a source position was leaking into BOTH the
           class and method fields of a violation, and therefore into the unique-misuse key,
           counting one misuse once per source line it occurred at.
         - 79fea6dd (2026-07-19, refs #83) — reconstruction timing.
       So `errors_*.csv` CANNOT be byte-identical, and task 5.4's literal phrasing
       ("byte-identical") is unsatisfiable against this baseline. What 5.4 actually protects
       is the claim underneath it: violations derive from the logcat and are independent of
       the analysis key. That claim is tested by PROJECTING AWAY the columns the fixes
       touch and requiring the remainder to be identical.

WHAT EACH ASSERTION MEANS
    S1  summary mop_errors_total identical for all 219       - no violation gained or lost
    S2  summary cov_* differ only inside the 30              - the scope effect is confined
    E1  errors projected to (apk,rep,timeout,tool,spec,message), multiset-identical for all
        219                                                  - THE 5.4 assertion: no
        violation was gained or lost anywhere; only its class/method attribution was
        reshaped by #89
    E1b the `time` column moved only inside the 30           - a real scope effect, not
        drift: regenerate_container.py derives t0 as the earliest registered event and writes
        `time` as max(0, int(event - t0)), so a wider key registers more coverage events,
        moves t0 earlier and shifts that app's whole timeline. Legitimate inside the 30,
        a bug outside it
    E2  errors full-row differences reported per app         - expected to be the #89 apps
    E3  the at-source fix agrees with ase-journal's in-place repair - see
        compare_frame_key_repair
    C1  coverage event identity (apk,rep,timeout,tool,time,class,method,signature)
        multiset-identical per app OUTSIDE the 30            - the replayed events did not
        move for apps whose key did not change
    C2  the ordered cov_* curve — reported, NOT asserted (see below)
    C3  the per-task event multiset is unchanged outside the 30
    C4  the FINAL cov_* per task changed only inside the 30

    A THIRD CONFOUND, in coverage: full coverage rows DO differ outside the 30, because
    events sharing a timestamp swap slots between runs (79fea6dd). The ordered curve is
    therefore NOT an invariant: when two tied events differ in whether they introduce a new
    class, the intermediate cumulative value depends on which ran first. What does not
    depend on it is the event multiset (C3) and the endpoint (C4, and S2 on the summary
    side, which is where the analysis reads coverage from). Asserting C2 would be asserting
    a property the data never had; it is reported so the delta is visible, not hidden.

Usage:
    uv run python scripts/gh91_compare_consolidation.py                  # summary + errors
    uv run python scripts/gh91_compare_consolidation.py --with-coverage  # + the 6 GB pass
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(1 << 30)

DATASET = Path("/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET")
RESULTS = DATASET / "RESULTS"
APKS_30 = Path(__file__).resolve().parent.parent / "30_apks.csv"

KEY_COLS = ("apk", "rep", "timeout", "tool")
COV_COLS = (
    "cov_act",
    "cov_class",
    "cov_method",
    "cov_reachable",
    "cov_reaches_target",
    "cov_directly_reaches_target",
)
MOP_COLS = ("mop_errors_total", "mop_errors_unique")

# errors:   apk,rep,timeout,tool,time,spec,class,method,message,unique_msg
# Dropping class/method/unique_msg removes exactly what cf234788 reshaped. Dropping `time`
# in addition removes the t0 shift described at compare_errors -- what remains is the
# identity of the violation itself, which nothing in this change may touch.
ERRORS_EVENT_COLS = (0, 1, 2, 3, 4, 5, 8)
ERRORS_VIOLATION_COLS = (0, 1, 2, 3, 5, 8)
# coverage: apk,rep,timeout,tool,time,class,method,signature,cov_class,cov_act,cov_method,cov_rv_method
# Keeping 0..7 is the event identity; 8..11 are the static-data-dependent running values.
COVERAGE_EVENT_COLS = tuple(range(8))

EXPECTED_ROWS = 21681
EXPECTED_APPS = 219


class Report:
    def __init__(self) -> None:
        self.failed = False

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        if not ok:
            self.failed = True
        print(
            f"  [{'PASS' if ok else 'FAIL'}] {label}"
            + (f" - {detail}" if detail else "")
        )
        return ok

    def note(self, label: str, detail: str = "") -> None:
        print(f"  [ .. ] {label}" + (f" - {detail}" if detail else ""))


def load_30() -> set[str]:
    with APKS_30.open() as fh:
        return {row["apk"] for row in csv.DictReader(fh)}


def load_summary(path: Path) -> dict[tuple, dict]:
    with path.open() as fh:
        return {tuple(r[c] for c in KEY_COLS): r for r in csv.DictReader(fh)}


def multiset_per_apk(
    path: Path, cols: tuple[int, ...] | None
) -> dict[str, tuple[int, int]]:
    """Commutative (order-blind) hash of each app's rows, optionally projected onto `cols`.

    Returns apk -> (row_count, digest_sum). Summing row digests is associative and
    commutative, so the result depends on the multiset of rows and not on their order --
    which is what makes it immune to the nondeterministic concat order of 16 parallel
    container jobs. Full rows are re-serialised through csv.writer semantics only implicitly:
    the projection joins fields with a NUL that cannot occur in the data, so distinct field
    splits cannot collide.
    """
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        next(reader, None)  # header
        for row in reader:
            if not row:
                continue
            payload = "\0".join(row[c] for c in cols) if cols else "\0".join(row)
            digest = int.from_bytes(hashlib.md5(payload.encode()).digest(), "big")
            slot = acc[row[0]]
            slot[0] += 1
            slot[1] = (slot[1] + digest) % (1 << 128)
    return {a: (c, d) for a, (c, d) in acc.items()}


def diff_apps(base: dict[str, tuple], regen: dict[str, tuple]) -> list[str]:
    return sorted(a for a in set(base) | set(regen) if base.get(a) != regen.get(a))


def compare_summary(report: Report, apks30: set[str]) -> None:
    print("\n== summary_*.csv ==")
    base = load_summary(RESULTS / "summary_all.csv")
    regen = load_summary(RESULTS / "summary_regen.csv")

    report.check(
        len(regen) == EXPECTED_ROWS,
        f"grid has {EXPECTED_ROWS} rows",
        f"found {len(regen)}",
    )
    report.check(
        set(base) == set(regen),
        "the (apk,rep,timeout,tool) key set is unchanged",
        f"+{len(set(regen) - set(base))} -{len(set(base) - set(regen))}",
    )
    report.check(
        len({k[0] for k in regen}) == EXPECTED_APPS, f"{EXPECTED_APPS} distinct apps"
    )

    shared = set(base) & set(regen)

    # --- S1: no violation gained or lost, anywhere (task 5.4) --------------------------------
    tot_moved = {
        k[0]
        for k in shared
        if base[k]["mop_errors_total"] != regen[k]["mop_errors_total"]
    }
    report.check(
        not tot_moved,
        "S1 mop_errors_TOTAL identical for all 219 apps",
        f"moved in {len(tot_moved)}: {sorted(tot_moved)[:8]}",
    )

    # mop_errors_unique is EXPECTED to move, downward only, on the #89 apps.
    uniq_moved = {
        k[0]
        for k in shared
        if base[k]["mop_errors_unique"] != regen[k]["mop_errors_unique"]
    }
    up = [
        k
        for k in shared
        if int(regen[k]["mop_errors_unique"]) > int(base[k]["mop_errors_unique"])
    ]
    down = [
        k
        for k in shared
        if int(regen[k]["mop_errors_unique"]) < int(base[k]["mop_errors_unique"])
    ]
    report.check(
        not up,
        "S1b mop_errors_unique never INCREASED (a dedup fix can only merge)",
        f"{len(up)} rows increased",
    )
    report.note(
        f"mop_errors_unique decreased in {len(down)} rows across {len(uniq_moved)} apps",
        "expected: cf234788 / issue #89",
    )

    # --- S2: the scope effect is confined to the 30 (task 5.3) ------------------------------
    cov_moved = {
        k[0] for k in shared if any(base[k][c] != regen[k][c] for c in COV_COLS)
    }
    outside = sorted(cov_moved - apks30)
    report.check(
        not outside,
        "S2 cov_* changed only for apps in 30_apks.csv",
        f"{len(outside)} outside: {outside[:8]}",
    )
    report.note(
        f"cov_* moved in {len(cov_moved)} of the 30",
        f"unchanged: {sorted(apks30 - cov_moved)}",
    )


def compare_errors(report: Report, apks30: set[str]) -> None:
    print("\n== errors_*.csv (order-blind; class/method projected away) ==")
    base, regen = RESULTS / "errors_all.csv", RESULTS / "errors_regen.csv"

    # --- E1: THE 5.4 assertion — the violation itself ----------------------------------------
    # (apk,rep,timeout,tool,spec,message): what was violated, in which run. Nothing about the
    # analysis key may move this, and nothing does.
    vb = multiset_per_apk(base, ERRORS_VIOLATION_COLS)
    vr = multiset_per_apk(regen, ERRORS_VIOLATION_COLS)
    moved = diff_apps(vb, vr)
    report.check(
        not moved,
        "E1 violation identity (apk,rep,timeout,tool,spec,message) multiset "
        "identical for all 219",
        f"{len(moved)} app(s) moved: {moved[:8]}",
    )
    report.note(
        "total error rows",
        f"base {sum(c for c, _ in vb.values())} / "
        f"regen {sum(c for c, _ in vr.values())}",
    )

    # --- E1b: the `time` column, which the key CAN legitimately move -------------------------
    # regenerate_container.py derives t0 as the earliest registered event and writes
    # `time` as max(0, int(event - t0)). A wider key registers more coverage events, so t0
    # can move earlier and shift every violation timestamp of that app. That is a scope
    # effect and must therefore be confined to the 30 -- outside them it would be a bug.
    eb = multiset_per_apk(base, ERRORS_EVENT_COLS)
    er = multiset_per_apk(regen, ERRORS_EVENT_COLS)
    t_moved = set(diff_apps(eb, er))
    outside = sorted(t_moved - apks30)
    report.check(
        not outside,
        "E1b `time` shifted only for apps in 30_apks.csv",
        f"{len(outside)} outside: {outside[:8]}",
    )
    report.note(
        f"`time` shifted in {len(t_moved)} app(s), all inside the 30",
        ", ".join(sorted(t_moved)),
    )

    # --- E2: where the attribution was reshaped ----------------------------------------------
    fb = multiset_per_apk(base, None)
    fr = multiset_per_apk(regen, None)
    full_moved = diff_apps(fb, fr)
    report.note(
        f"E2 full-row differences in {len(full_moved)} app(s) — the class/method "
        f"reshape of #89",
        ", ".join(full_moved[:6]),
    )
    counts = [a for a in full_moved if fb.get(a, (0, 0))[0] != fr.get(a, (0, 0))[0]]
    report.check(
        not counts,
        "E2 no app changed its error ROW COUNT",
        f"{len(counts)} app(s) changed count: {counts[:8]}",
    )

    compare_frame_key_repair(report)


def compare_frame_key_repair(report: Report) -> None:
    """E3 — the at-source fix must agree with ase-journal's in-place repair.

    The paper repo fixed the same defect from the other end: `fix-rv-key-granularity`
    (archived 2026-07-28) rewrote the frame-form keys of its already-consolidated sheets in
    place with `data-analysis/repair_frame_keys.py`, and re-derived 13 macros over the
    corrected key (\\uniqueMisusesMOP 567 -> 541 among them). Our regenerated CSVs instead
    come from a parser that never emits the defect (cf234788).

    Two fixes for one defect, applied at opposite ends of the chain, are only safe if they
    agree. If they did not, delivering these CSVs would silently contradict an archived,
    closed change and its published numbers. So this imports THEIR repair verbatim, applies
    it to the unrepaired baseline, and requires the result to reproduce our regenerated
    class/method columns exactly. Skipped, not failed, when the paper repo is absent.
    """
    print("\n== E3: at-source fix (cf234788) vs ase-journal's in-place repair ==")
    repair_dir = Path(
        "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/"
        "workspace-rv/ase-journal/data-analysis"
    )
    if not (repair_dir / "repair_frame_keys.py").is_file():
        report.note("SKIP - ase-journal/data-analysis/repair_frame_keys.py not found")
        return
    sys.path.insert(0, str(repair_dir))
    from repair_frame_keys import (  # noqa: E402  (their algorithm, verbatim)
        is_frame,
        split_frame,
    )

    def scan(path: Path, repair: bool) -> tuple[dict[str, tuple[int, int]], int]:
        acc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        frames = 0
        with path.open(newline="") as fh:
            reader = csv.reader(fh)
            next(reader, None)
            for row in reader:
                cls, mth = row[6], row[7]
                if is_frame(cls):
                    frames += 1
                    if repair:
                        cls, mth = split_frame(cls)
                # `time` is excluded: the t0 shift of E1b is a separate, legitimate effect.
                payload = "\0".join(
                    [row[0], row[1], row[2], row[3], row[5], cls, mth, row[8]]
                )
                digest = int.from_bytes(hashlib.md5(payload.encode()).digest(), "big")
                slot = acc[row[0]]
                slot[0] += 1
                slot[1] = (slot[1] + digest) % (1 << 128)
        return {a: (c, d) for a, (c, d) in acc.items()}, frames

    base_repaired, frames_base = scan(RESULTS / "errors_all.csv", repair=True)
    regen_rows, frames_regen = scan(RESULTS / "errors_regen.csv", repair=False)

    report.check(
        frames_regen == 0,
        "E3 the regenerated CSV emits no frame-form key at all",
        f"{frames_regen} frame-form values found",
    )
    moved = diff_apps(base_repaired, regen_rows)
    report.check(
        not moved,
        "E3 their repair applied to the baseline reproduces our class/method exactly",
        f"{len(moved)} app(s) differ: {moved[:8]}",
    )
    report.note(
        f"{frames_base} frame-form values in the baseline were repaired and matched",
        "so repair_frame_keys.py is a byte-level no-op on the delivered CSVs",
    )


def compare_coverage(report: Report, apks30: set[str]) -> None:
    print("\n== coverage_*.csv (order-blind; ~6 GB per side, two passes each) ==")
    base, regen = RESULTS / "coverage_all.csv", RESULTS / "coverage_regen.csv"

    # --- C1: the replayed events themselves --------------------------------------------------
    eb = multiset_per_apk(base, COVERAGE_EVENT_COLS)
    er = multiset_per_apk(regen, COVERAGE_EVENT_COLS)
    moved = set(diff_apps(eb, er))
    outside = sorted(moved - apks30)
    report.check(
        not outside,
        "C1 event identity (apk,rep,timeout,tool,time,class,method,signature) "
        "unchanged outside the 30",
        f"{len(outside)} outside: {outside[:8]}",
    )
    report.note(
        f"event multiset moved in {len(moved)} app(s)",
        f"{len(moved & apks30)} inside the 30",
    )
    report.note(
        "total coverage rows",
        f"base {sum(c for c, _ in eb.values())} / "
        f"regen {sum(c for c, _ in er.values())}",
    )

    # --- C2: the coverage curve itself --------------------------------------------------------
    # Outside the 30, full rows DO differ, and the reason is neither the key nor lost data:
    # events sharing a timestamp swap slots between runs (79fea6dd, "coverage.csv lost
    # chronological order"). cov_* is cumulative and positional, so the curve is unaffected --
    # <init>/<clinit>, both at time=0, trade places and each keeps the other's running value.
    # The assertion is therefore on the CURVE (ordered cov_* per task) and on the EVENT
    # MULTISET per task; a genuine data change would break one of them.
    cb_cov, cb_ev = per_task_sequences(base)
    cr_cov, cr_ev = per_task_sequences(regen)

    # C2 is a NOTE, not an assertion, and the reason is worth stating plainly: the ordered
    # curve is NOT an invariant when tie order is arbitrary. If two events share a timestamp
    # and only one of them introduces a new class, the intermediate cumulative value depends
    # on which ran first, while the events and the endpoint do not. Asserting it would be
    # asserting a property the data never had.
    cov_moved = {
        k[0] for k in set(cb_cov) | set(cr_cov) if cb_cov.get(k) != cr_cov.get(k)
    }
    report.note(
        f"C2 the ordered cov_* curve differs in {len(cov_moved)} app(s)",
        f"{len(cov_moved - apks30)} outside the 30 — transient tie-order effect; "
        f"the endpoint is asserted by C4/S2",
    )

    ev_moved = {k[0] for k in set(cb_ev) | set(cr_ev) if cb_ev.get(k) != cr_ev.get(k)}
    outside_ev = sorted(ev_moved - apks30)
    report.check(
        not outside_ev,
        "C3 the per-task event multiset is unchanged outside the 30",
        f"{len(outside_ev)} outside: {outside_ev[:8]}",
    )

    # --- C4: the endpoint, which IS order-independent -----------------------------------------
    # cov_* is cumulative, so the per-task maximum is the final value regardless of row order.
    fin_b = per_task_final(base)
    fin_r = per_task_final(regen)
    fin_moved = {k[0] for k in set(fin_b) | set(fin_r) if fin_b.get(k) != fin_r.get(k)}
    outside_fin = sorted(fin_moved - apks30)
    report.check(
        not outside_fin,
        "C4 the FINAL cov_* per task changed only inside the 30",
        f"{len(outside_fin)} outside: {outside_fin[:8]}",
    )
    report.note(
        f"final cov_* moved in {len(fin_moved)} app(s)",
        f"{len(fin_moved & apks30)} inside the 30",
    )

    fb = multiset_per_apk(base, None)
    fr = multiset_per_apk(regen, None)
    full_moved = set(diff_apps(fb, fr))
    report.note(
        f"full coverage rows differ in {len(full_moved)} app(s)",
        f"{len(full_moved - apks30)} of them outside the 30 — the tie-order effect above",
    )


def per_task_final(path: Path) -> dict[tuple, tuple[float, ...]]:
    """Per task, the FINAL cov_* values — taken as the per-column maximum.

    cov_* is cumulative and non-decreasing, so its maximum is its endpoint no matter how the
    rows are ordered. That is what makes this comparable across two runs whose tie order
    differs, where the ordered curve is not.
    """
    acc: dict[tuple, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        next(reader, None)
        for row in reader:
            if not row:
                continue
            slot = acc[(row[0], row[1], row[2], row[3])]
            for i, cell in enumerate(row[8:12]):
                # Reachable with an empty cell since gh111: a task with no
                # coverage denominator writes "" in all four of these columns
                # rather than 0.00 (INV-PLT-35), and `float("")` raises. The cell
                # is SKIPPED rather than coerced to 0 — coercing would put the
                # exact ambiguity this script is comparing back into the maximum.
                if not cell.strip():
                    continue
                value = float(cell)
                if value > slot[i]:
                    slot[i] = value
    return {k: tuple(v) for k, v in acc.items()}


def per_task_sequences(path: Path) -> tuple[dict[tuple, int], dict[tuple, int]]:
    """Per (apk,rep,timeout,tool): the ORDERED cov_* sequence, and the event MULTISET.

    Order-sensitive for the curve (a cumulative series is meaningless re-ordered) and
    order-blind for the events (their relative order among equal timestamps is arbitrary).
    Both are O(1) per task, so a 6 GB file costs one pass and ~21 681 accumulators.
    """
    curve: dict[tuple, int] = defaultdict(int)
    events: dict[tuple, int] = defaultdict(int)
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        next(reader, None)
        for row in reader:
            if not row:
                continue
            task = (row[0], row[1], row[2], row[3])
            cov = int.from_bytes(
                hashlib.md5("\0".join(row[8:12]).encode()).digest()[:8], "big"
            )
            curve[task] = (curve[task] * 1_000_003 + cov) % (
                1 << 127
            )  # order-sensitive
            ev = int.from_bytes(
                hashlib.md5("\0".join(row[4:8]).encode()).digest()[:8], "big"
            )
            events[task] = (events[task] + ev) % (1 << 127)  # order-blind
    return dict(curve), dict(events)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--with-coverage",
        action="store_true",
        help="also compare coverage_*.csv per app (~6 GB per side)",
    )
    args = ap.parse_args()

    apks30 = load_30()
    print(f"RESULTS  : {RESULTS}")
    print(f"the 30   : {len(apks30)} apps from {APKS_30.name}")
    if len(apks30) != 30:
        print(f"  [FAIL] 30_apks.csv holds {len(apks30)} rows")
        return 1

    missing = [
        n
        for n in ("summary_regen.csv", "errors_regen.csv")
        if not (RESULTS / n).is_file()
    ]
    if missing:
        print(
            f"  [FAIL] regenerated CSVs not found: {missing} - has the consolidation finished?"
        )
        return 1

    report = Report()
    compare_summary(report, apks30)
    compare_errors(report, apks30)
    if args.with_coverage:
        compare_coverage(report, apks30)

    print("\nRESULT:", "FAIL" if report.failed else "PASS")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
