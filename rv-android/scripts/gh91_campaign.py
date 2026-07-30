#!/usr/bin/env python3
"""gh91 — the unattended re-analysis campaign: all rounds, one script, no human in the loop.

`gh91_sa_rerun.py` runs ONE round of the 30 APKs. This module owns everything above that:
which APKs a round contains, at which budget, how a failure is classified, whether it earns a
retry, and when the campaign is finished. It is launched once and reports on exit.

WHY THE ROUND LOGIC IS HERE AND NOT IN AN AGENT LOOP (design D7)
    Every round decision is deterministic and derivable from what the previous round left on
    disk, and a single APK can occupy a worker for 5400 s. An agent sitting on that is a
    worse, non-reproducible `subprocess.wait()` that also cannot survive the session. Here it
    is a plain loop that can be replayed.

WHY RE-INVOKING THIS SCRIPT IS THE RECOVERY MECHANISM (design D8)
    Durability comes from idempotence, not from detachment. `REGISTRO.md`,
    `_progress/<apk>.json` and `_campaign_state.json` are flushed after every APK, and the
    identical command re-run picks up exactly where it stopped. That survives a power cut, a
    reboot, or a bug in this script — none of which detaching the process would help with.

WHY A FAILED APK'S JSON IS MOVED ASIDE BEFORE ITS RETRY (design R5)
    The driver resumes by output-file existence, so ANY file left in place — partial, or
    complete but superseded by a retry — would make round 2 skip exactly the APK round 1
    failed, and the campaign would "converge" having analysed nothing. On the measured
    magnitude: a WTG timeout leaves a *complete* file (the pre-WTG write already fsynced it),
    and under `--skip-wtg` a timeout leaves no file at all, so a genuinely partial JSON needs
    the kill to land inside the write window. The guard stays regardless because it costs one
    `os.replace`. The superseded files are kept, not deleted: they are provenance.

WHY THE SUCCESS CRITERION IS THE SENTINEL AND NOTHING ELSE (design R5)
    Neither "it parses" nor `sa_status == complete` proves completeness. Only the
    `"complete": true` sentinel does, and bracket recovery can never synthesise it: the
    recovery closes the object at the last `]`, discarding the trailing `,"complete":true` by
    construction.

Usage:
    python scripts/gh91_campaign.py --plan       # rounds, ladder and round-1 contents
    python scripts/gh91_campaign.py --dry-run    # per-round argv; nothing is executed
    python scripts/gh91_campaign.py              # the campaign, resumable
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gh91_sa_rerun as drv  # noqa: E402  (path must be set first)

# --- Campaign policy (design D9) ---------------------------------------------------------

MAX_ROUNDS = 2

# A round IS a capacity configuration, and every APK in it runs under that configuration.
# The two are the corpus's own tiers, collapsed: everything Phase 7 ran at 12g or 32g goes
# in round 1, everything above in round 2. Concurrency falls out of the budget rather than
# being set separately — 3 x 32g = 96g fits under 100g, while a single 120g job exceeds it
# and therefore runs alone through the dispatcher's R4 exception path.
ROUND_CONFIG = {1: ("32g", 3600), 2: ("120g", 7200)}
ROUND_BUDGET_GIB = {1: 100.0, 2: 100.0}

# The tier boundary between the two rounds, in GiB of the Phase 7 `--jvm-memory`.
ROUND1_MAX_TIER_GIB = 32.0

# Round 2 is the host's memory ceiling and the last round: `--jvm-memory` is a bare `-Xmx`
# with no `-Xms` (design R4), a lazy ceiling rather than a reservation, so 120g costs nothing
# for an APK that would have been happy with 56g. Its timeout is above every pair Phase 7
# recorded (max 5400 s) because there is no round after it.


CLASS_COMPLETE = "COMPLETE"
CLASS_TRANSIENT = "TRANSIENT"
CLASS_DETERMINISTIC = "DETERMINISTIC"

# Read out of the log tail: an OOM is a transient failure that memory escalation can fix,
# and it is not visible in the return code alone.
TRANSIENT_LOG_MARKERS = ("OutOfMemoryError", "GC overhead limit", "Java heap space")

REGISTRO = drv.OUT_DIR / "REGISTRO.md"
STATE_PATH = drv.OUT_DIR / "_campaign_state.json"
SUPERSEDED_DIR = drv.OUT_DIR / "_superseded"

# The sentinel is the last top-level field, emitted immediately before `endObject`
# (`JsonReportWriter.java:111`), so it is always within the final bytes of the file.
_SENTINEL_RE = re.compile(r'"complete"\s*:\s*true\s*\}\s*$')
_TAIL_BYTES = 512


# --- Completeness ------------------------------------------------------------------------


def has_sentinel(path: Path) -> bool:
    """Whether this JSON carries `"complete": true` — the only accepted proof of a full run.

    Read from the tail rather than parsed: these files reach tens of MB, and parsing would
    additionally accept a truncated file that the bracket-recovery loader repairs.
    """
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - _TAIL_BYTES))
            tail = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return False
    return _SENTINEL_RE.search(tail.strip()) is not None


def log_tail(path: Path, lines: int = 25) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "(log unreadable)"
    return "\n".join(content.splitlines()[-lines:])


def classify(record: dict, *, complete: bool, tail: str) -> str:
    """Decide whether this outcome earns a retry (design D9).

    Retrying a deterministic failure costs hours and reproduces it exactly. `run_one` already
    folds GATOR's own timeout (rc -50/206) into `timed_out`, so both timeout paths land in
    the same branch here.
    """
    if complete:
        return CLASS_COMPLETE
    if record.get("timed_out"):
        return CLASS_TRANSIENT
    if record.get("sa_status") == drv.sa_runner.STATUS_FAILED_TIMEOUT_NO_JSON:
        return CLASS_TRANSIENT
    if any(marker in tail for marker in TRANSIENT_LOG_MARKERS):
        return CLASS_TRANSIENT
    return CLASS_DETERMINISTIC


# --- State -------------------------------------------------------------------------------


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    """Atomic, so a kill mid-write never leaves an unreadable state file."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, STATE_PATH)


# --- REGISTRO.md (design D10) ------------------------------------------------------------


def registro(text: str) -> None:
    """Append to REGISTRO.md and force it to disk.

    Flushed after every APK so that `tail REGISTRO.md` answers "where is it?" at any moment
    without touching the running process. It is the audit trail and the live progress view;
    `_progress/<apk>.json` is the machine-readable half and neither is derived from the other
    after the fact.
    """
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRO.open("a", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())


def registro_entry(record: dict, job: drv.Job, *, round_no: int, budget: float,
                   complete: bool, verdict: str, tail: str) -> None:
    json_state = "absent"
    if job.json_path.is_file():
        size_mb = job.json_path.stat().st_size / (1024 * 1024)
        json_state = f"present ({size_mb:.1f} MB), sentinel={'YES' if complete else 'NO'}"
    lines = [
        f"\n### r{round_no} · {job.apk} · **{verdict}**\n\n",
        f"- ended: {datetime.now().isoformat(timespec='seconds')}\n",
        f"- jvm_memory: `{job.jvm_memory}`  timeout: `{job.timeout}s`  "
        f"budget: `{budget:g}g`\n",
        f"- sa_status: `{record.get('sa_status')}`  rc: `{record.get('returncode')}`  "
        f"timed_out: `{record.get('timed_out')}`\n",
        f"- wall clock: {record.get('seconds')}s\n",
        f"- json: {json_state}\n",
        f"- codePackage: `{job.code_package}`\n",
        f"- argv: `{' '.join(record.get('argv', []))}`\n",
    ]
    if not complete:
        lines.append(f"- log tail:\n\n```\n{tail}\n```\n")
    registro("".join(lines))


# --- Round scheduling --------------------------------------------------------------------


def home_round(recorded: tuple[str, int]) -> int:
    """The round this APK belongs to, decided by the tier Phase 7 gave it.

    The previous run already measured what each APK needs; that measurement is the
    assignment. An APK is never run below its known requirement, and never has to discover
    it by failing first.
    """
    return 1 if drv._parse_mem_gib(recorded[0]) <= ROUND1_MAX_TIER_GIB else 2


def round_params(round_no: int) -> tuple[str, int]:
    """The `(jvm_memory, timeout)` every APK in `round_no` runs under."""
    return ROUND_CONFIG[round_no]


def supersede(job: drv.Job, attempt: int) -> list[str]:
    """Move this APK's JSON and log aside before a re-run (design R5). Never deletes.

    `run_one` pre-cleans its target JSON, so without this the previous attempt's evidence —
    its log, and whatever JSON it did manage to write — would be destroyed by the retry.
    """
    dest = SUPERSEDED_DIR / f"r{attempt}"
    dest.mkdir(parents=True, exist_ok=True)
    moved = []
    for src in (job.json_path, job.log_path):
        if src.is_file():
            os.replace(src, dest / src.name)
            moved.append(src.name)
    return moved


def retryable(jobs: list[drv.Job], state: dict) -> list[drv.Job]:
    """APKs that are neither finished nor written off, at any round.

    Distinct from `pending_for_round`, and the distinction is what makes resume work: on
    re-entry after a kill during round 2, round 1 is legitimately empty (everything was
    already attempted at that budget) while work clearly remains. Treating an empty round as
    "campaign over" would strand exactly the APKs the retry rounds exist for.
    """
    return [j for j in jobs
            if not has_sentinel(j.json_path)
            and state.get(j.apk, {}).get("verdict") != CLASS_DETERMINISTIC]


def pending_for_round(jobs: list[drv.Job], state: dict, round_no: int,
                      home: dict) -> list[drv.Job]:
    """The APKs this round must run: its own tier, plus anything promoted into it.

    An APK is finished when its JSON carries the sentinel — never because a state file says
    so, which is what makes the campaign recoverable from an inconsistent state file too.
    A DETERMINISTIC verdict removes it from every later round.

    Promotion is the `home[...] <= round_no` clause: an APK whose home is round 1 and which
    failed there has `rounds_done == 1`, so it joins round 2 and runs under round 2's larger
    configuration. It is never retried under the configuration that already failed it.
    """
    todo = []
    for job in jobs:
        entry = state.get(job.apk, {})
        if home[job.apk] > round_no:
            continue  # its tier's round has not arrived yet
        if has_sentinel(job.json_path):
            continue
        if entry.get("verdict") == CLASS_DETERMINISTIC:
            continue
        if entry.get("rounds_done", 0) >= round_no:
            continue  # already attempted at this round's configuration; resume past it
        todo.append(job)
    return todo


def run_round(jobs: list[drv.Job], home: dict, state: dict, *, round_no: int,
              grace: int) -> int:
    """Run one round; return how many APKs reached the sentinel in it."""
    todo = pending_for_round(jobs, state, round_no, home)
    budget = ROUND_BUDGET_GIB[round_no]
    if not todo:
        print(f"round {round_no}: nothing pending")
        return 0

    for job in todo:
        job.jvm_memory, job.timeout = round_params(round_no)
        job.mem_gib = drv._parse_mem_gib(job.jvm_memory)
        attempt = state.get(job.apk, {}).get("rounds_done", 0)
        moved = supersede(job, attempt)
        if moved:
            print(f"  superseded r{attempt} artefacts for {job.apk}: {', '.join(moved)}")

    registro(
        f"\n## Round {round_no} — {len(todo)} APK(s), budget {budget:g}g — "
        f"started {datetime.now().isoformat(timespec='seconds')}\n"
    )
    print(f"\n=== round {round_no}: {len(todo)} APK(s), budget {budget:g}g ===")
    for job in todo:
        print(f"  {job.apk:45} {job.jvm_memory:>5} / {job.timeout}s")

    completed = 0

    def on_done(record: dict, job: drv.Job) -> None:
        nonlocal completed
        complete = has_sentinel(job.json_path)
        tail = "" if complete else log_tail(job.log_path)
        verdict = classify(record, complete=complete, tail=tail)
        if complete:
            completed += 1
        state[job.apk] = {
            "rounds_done": round_no,
            "verdict": verdict,
            "sa_status": record.get("sa_status"),
            "jvm_memory": job.jvm_memory,
            "timeout": job.timeout,
            "seconds": record.get("seconds"),
            "complete": complete,
        }
        save_state(state)
        registro_entry(record, job, round_no=round_no, budget=budget,
                       complete=complete, verdict=verdict, tail=tail)
        print(f"  -> {job.apk}: {verdict} ({record.get('sa_status')}, "
              f"{record.get('seconds')}s)")

    drv.run_all(todo, budget=budget, grace=grace, on_done=on_done)
    print(f"=== round {round_no} done: {completed}/{len(todo)} reached the sentinel ===")
    return completed


def run_campaign(jobs: list[drv.Job], home: dict, state: dict, *, max_rounds: int,
                 grace: int) -> None:
    """Run each round in turn until the goal state is reached or the rounds run out."""
    for rnd in range(1, max_rounds + 1):
        if not retryable(jobs, state):
            print(f"round {rnd}: nothing retryable — stopping early")
            return
        if not pending_for_round(jobs, state, rnd, home):
            # Nothing left for this configuration — either it already ran (a resume landing
            # mid-campaign) or its tier is empty. Move on; do not stop.
            print(f"round {rnd}: nothing pending at this configuration")
            continue
        run_round(jobs, home, state, round_no=rnd, grace=grace)


# --- Reporting ---------------------------------------------------------------------------


def final_report(jobs: list[drv.Job], state: dict) -> tuple[int, list[str], list[str]]:
    done, transient, deterministic = [], [], []
    for job in jobs:
        if has_sentinel(job.json_path):
            done.append(job.apk)
        elif state.get(job.apk, {}).get("verdict") == CLASS_DETERMINISTIC:
            deterministic.append(job.apk)
        else:
            transient.append(job.apk)

    body = [f"\n## Final — {datetime.now().isoformat(timespec='seconds')}\n\n",
            f"- complete (sentinel): **{len(done)}/{len(jobs)}**\n"]
    if deterministic:
        body.append(f"- DETERMINISTIC, not retried: {', '.join(sorted(deterministic))}\n")
    if transient:
        body.append(f"- still incomplete after {MAX_ROUNDS} rounds: "
                    f"{', '.join(sorted(transient))}\n")
    if not deterministic and not transient:
        body.append("- goal state reached: every APK carries `\"complete\": true`. "
                    "The validation gate (task group 3) is the next step; nothing may be "
                    "copied into the corpus before it passes.\n")
    registro("".join(body))
    print("".join(body))
    return len(done), transient, deterministic


# --- Entry point -------------------------------------------------------------------------


def _print_plan(jobs: list[drv.Job], home: dict, recorded: dict, max_rounds: int) -> None:
    for rnd in range(1, max_rounds + 1):
        mem, timeout = round_params(rnd)
        budget = ROUND_BUDGET_GIB[rnd]
        members = [j for j in sorted(jobs, key=lambda j: (j.prior_seconds, j.apk))
                   if home[j.apk] == rnd]
        slots = int(budget // drv._parse_mem_gib(mem)) or 1
        print(f"\n=== round {rnd}: {mem} / {timeout}s · budget {budget:g}g · "
              f"{slots} concurrent · {len(members)} APK(s) from its own tier ===")
        print(f"{'apk':46}{'tier (Phase 7)':>16}{'took then':>12}")
        for job in members:
            rec = f"{recorded[job.apk][0]}/{recorded[job.apk][1]}s"
            print(f"{job.apk:46}{rec:>16}{job.prior_seconds:>11.0f}s")
        worst = sum(j.prior_seconds for j in members) / slots
        print(f"  Phase 7 wall clock at this concurrency: ~{worst / 3600:.1f} h "
              f"(that run included the WTG, now skipped)")
    print(f"\nAPKs that failed round 1 are promoted into round 2 and run under its "
          f"configuration; round {max_rounds} is the last.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true",
                    help="print the escalation ladder per APK and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="print each round's contents and argv; execute nothing")
    ap.add_argument("--max-rounds", type=int, default=MAX_ROUNDS,
                    help=f"cap on escalation rounds (default {MAX_ROUNDS})")
    ap.add_argument("--only", action="append", default=None, metavar="APK",
                    help="restrict the campaign to this APK id (repeatable)")
    ap.add_argument("--grace", type=int, default=drv.DEFAULT_GRACE_SECONDS,
                    help="seconds the outer kill waits past GATOR's own --timeout")
    ap.add_argument("--force", action="store_true",
                    help="start even if the round budget exceeds free RAM")
    args = ap.parse_args()

    if args.max_rounds < 1 or args.max_rounds > MAX_ROUNDS:
        raise SystemExit(f"--max-rounds must be between 1 and {MAX_ROUNDS}")

    jobs = drv.read_plan()
    if args.only:
        wanted = set(args.only)
        jobs = [j for j in jobs if j.apk in wanted]
        unknown = wanted - {j.apk for j in jobs}
        if unknown:
            raise SystemExit(f"not in 30_apks.csv: {', '.join(sorted(unknown))}")
    if not jobs:
        raise SystemExit("no APKs selected")
    # The Phase 7 pair decides which round each APK belongs to, and is captured before any
    # job is mutated by a round's configuration.
    recorded = {j.apk: (j.jvm_memory, j.timeout) for j in jobs}
    home = {apk: home_round(pair) for apk, pair in recorded.items()}

    if args.plan:
        _print_plan(jobs, home, recorded, args.max_rounds)
        return 0

    if args.dry_run:
        state = load_state()
        for rnd in range(1, args.max_rounds + 1):
            todo = pending_for_round(jobs, state, rnd, home)
            mem, timeout = round_params(rnd)
            print(f"\n=== round {rnd}: {mem}/{timeout}s · budget "
                  f"{ROUND_BUDGET_GIB[rnd]:g}g · {len(todo)} APK(s) ===")
            for job in todo:
                job.jvm_memory, job.timeout = mem, timeout
                job.mem_gib = drv._parse_mem_gib(mem)
                print(" ".join(drv.build_argv(job)))
        print("\n(dry run: nothing executed, no file written)")
        return 0

    # Pre-flight — the driver's own checks live in its `main()`, which this path bypasses.
    missing = [str(j.apk_path) for j in jobs if not j.apk_path.is_file()]
    if missing:
        raise SystemExit(f"APK(s) not found: {', '.join(missing)}")
    if not drv.ANALYSIS_CLIENT_JAR.is_file():
        raise SystemExit(f"analysis client jar not found: {drv.ANALYSIS_CLIENT_JAR}")
    mop_dir = drv._mop_dir()
    if not mop_dir.is_dir():
        raise SystemExit(f"MOP specs directory not found: {mop_dir}")
    drv._gator_env()  # fails fast if the SDK path cannot be resolved

    free = drv._free_ram_gib()
    peak_budget = max(ROUND_BUDGET_GIB[r] for r in range(1, args.max_rounds + 1))
    if free is not None and peak_budget > free and not args.force:
        raise SystemExit(f"REFUSING: peak round budget {peak_budget:g}g exceeds free RAM "
                         f"{free:.1f}g. Override with --force.")

    drv.OUT_DIR.mkdir(parents=True, exist_ok=True)
    (drv.OUT_DIR / "logs").mkdir(exist_ok=True)

    # A kill must not orphan multi-hour JVMs holding tens of GB: the children run in their
    # own sessions precisely so the outer timeout can kill their subtrees, which also means
    # they do not die with this process.
    def _shutdown(signum, _frame):
        killed = drv.kill_running()
        registro(f"\n> interrupted by signal {signum} at "
                 f"{datetime.now().isoformat(timespec='seconds')}; "
                 f"{killed} GATOR process group(s) killed. Re-run the identical command to "
                 f"resume.\n")
        print(f"\ninterrupted (signal {signum}); killed {killed} GATOR group(s). "
              f"Re-run to resume.", flush=True)
        os._exit(130)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    state = load_state()
    started = datetime.now()
    if not REGISTRO.is_file():
        registro(
            "# REGISTRO — gh91 re-analysis campaign\n\n"
            "Incremental audit trail and live progress view, flushed after every APK.\n"
            "`tail REGISTRO.md` answers \"where is it?\" without touching the running "
            "process.\n\n"
            "Completeness means one thing only: the JSON carries the `\"complete\": true` "
            "sentinel.\nNeither \"it parses\" nor `sa_status == complete` is accepted as "
            "evidence.\nEvery run is WTG-skipped (`-clientParam skipWtg=true`), which "
            "empties `sa_transitions_count` only — `sa_windows_count` is populated.\n"
        )
    registro(f"\n---\n\n> campaign invoked {started.isoformat(timespec='seconds')} · "
             f"{len(jobs)} APK(s) in scope · max {args.max_rounds} rounds\n")

    print(f"gh91 campaign: {len(jobs)} APK(s), max {args.max_rounds} rounds")
    print(f"  output:   {drv.OUT_DIR}")
    print(f"  registro: {REGISTRO}")

    t0 = time.monotonic()
    run_campaign(jobs, home, state, max_rounds=args.max_rounds, grace=args.grace)

    elapsed = time.monotonic() - t0
    print(f"\ncampaign wall clock: {elapsed / 3600:.2f} h")
    registro(f"\n> campaign finished after {elapsed / 3600:.2f} h\n")
    done, transient, deterministic = final_report(jobs, state)
    return 0 if done == len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
