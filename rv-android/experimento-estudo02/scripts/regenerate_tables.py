#!/usr/bin/env python3
"""Regenerate the result tables of ONE estudo02 container, offline and bounded in memory.

Why this exists: the live exporter (`rv_platform.components.result_processor`)
runs six whole-campaign passes — coverage, errors, app_events, summary,
results.json, performance — and each pass keeps every task's reconstructed
`LogcatRepository` and parsed `StaticAnalysisData` alive until the end. With
~1 600 identities per container that is more than the 10 GiB the container
had, and every estudo02 container was OOM-killed inside the FIRST pass:
`coverage.csv` is a truncated prefix and the other five files never existed.

What this does differently is only the loop shape. The rows are written by the
exporter's own per-task methods (`_write_task_coverage_data`,
`_write_task_error_data`, `_write_task_app_events`, `_write_task_summary_data`,
`_extract_task_data`) and the headers are written by its own `_generate_*_csv`
methods, so the schema cannot drift from the live one: nothing here knows a
column name. The loop is task-major instead of file-major — all writers run
for one task, then that task's repository and static data are dropped — and
the static-analysis model is parsed once per APK, not once per task. Memory
is therefore one APK model plus one logcat.

Identity is `(apk, tool, variant, repetition, timeout)`. The resume protocol
appends a new record per attempt, so `tasks.json` may hold several records for
one identity; the COMPLETED record with the latest `end_time` wins, and tables
are counted per identity, never per record.

Usage:
    PYTHONHASHSEED=0 uv run python experimento-estudo02/scripts/regenerate_tables.py \\
        data/results/estudo02_00/estudo02_00 [--out-dir DIR] [--limit N]

Pin PYTHONHASHSEED. `Class.methods` is a set, so the repository's insertion
order — and with it the order of coverage.csv rows that share one second, and
the progressive `cov_*` values of those rows — follows the hash seed. The live
exporter has the same dependency; the pin only makes two runs of this script
agree byte for byte.

Output (in the container directory, or `--out-dir`): coverage.csv, errors.csv,
app_events.csv, summary.csv, results.json, performance.csv. When writing in
place, the OOM-truncated `coverage.csv` is renamed to `coverage.csv.oom-partial`
first and never deleted.
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

from rv_android_core.domain.task import Task, TaskState
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.components.performance_processor import PerformanceProcessorComponent
from rv_platform.components.result_processor import ResultProcessorComponent

Identity = Tuple[str, str, int, int]


class _CountingWriter:
    """A csv.writer that counts the rows the exporter's methods hand it.

    The per-task writers return nothing, and re-reading a 200 MB CSV at the end
    just to count lines would double the I/O on a disk that is the bottleneck.
    """

    def __init__(self, writer: Any):
        self._writer = writer
        self.rows = 0

    def writerow(self, row: List[Any]) -> None:
        self._writer.writerow(row)
        self.rows += 1


def load_identities(tasks_file: str) -> List[Task]:
    """One Task per identity: the COMPLETED record with the latest end_time.

    Sorted by (apk, tool, repetition, timeout) so that every task of an APK is
    contiguous — that is what lets the static-data cache hold a single entry.
    """
    with open(tasks_file, "r", encoding="utf-8") as f:
        records = json.load(f)["tasks"]

    best: Dict[Identity, Task] = {}
    for record in records:
        task = Task.from_dict(record)
        if task is None or task.result.state != TaskState.COMPLETED:
            continue
        key = (
            task.config.apk_name,
            task.config.tool_config.get_full_tool_name(),
            task.config.repetition,
            task.config.timeout,
        )
        current = best.get(key)
        if current is None or (task.result.end_time or datetime.min) > (
            current.result.end_time or datetime.min
        ):
            best[key] = task

    return [best[key] for key in sorted(best)]


def host_logcat_path(container_dir: str, logcat_file: str) -> str:
    """Map the container-relative logcat path to the host.

    tasks.json was written inside Docker, where the results root was
    `results/<container>/`; on the host that root is `container_dir`. Only the
    last two components (`<apk>/<file>`) are the task's own, so those are kept
    and everything before them is replaced.
    """
    return os.path.join(container_dir, *logcat_file.split("/")[-2:])


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("container_dir", help="e.g. data/results/estudo02_00/estudo02_00")
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Write the tables here instead of into container_dir (parity tests).",
    )
    ap.add_argument(
        "--limit", type=int, default=0, help="Process only the first N identities."
    )
    args = ap.parse_args()

    container_dir = os.path.abspath(args.container_dir)
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else container_dir
    tasks_file = os.path.join(container_dir, "tasks.json")
    if not os.path.isfile(tasks_file):
        print(f"ERROR: no tasks.json in {container_dir}", file=sys.stderr)
        return 2
    os.makedirs(out_dir, exist_ok=True)
    if not os.access(out_dir, os.W_OK):
        # Fail before parsing anything: the container directories are created by
        # Docker as root, and a silent fallback would hide where the tables went.
        print(f"ERROR: output directory is not writable: {out_dir}", file=sys.stderr)
        return 2

    # The exporter's `_generate_coverage_csv` opens coverage.csv with "w". Only
    # the in-place run meets the OOM-truncated live file there; a coverage.csv in
    # a separate --out-dir is a previous run of this script and carries no
    # evidence worth keeping.
    if out_dir == container_dir:
        live_partial = os.path.join(out_dir, "coverage.csv")
        preserved = live_partial + ".oom-partial"
        if os.path.isfile(live_partial) and not os.path.exists(preserved):
            os.rename(live_partial, preserved)
            print(f"preserved OOM-partial coverage.csv as {preserved}", flush=True)

    # Console at WARNING: Task construction logs one INFO line per record and the
    # reconstruction one per task; the warnings (unresolved static data, logcat
    # missing, parse failures) are the lines worth reading in a 1 600-task log.
    LoggingManager.get_instance().configure_output(console_level=logging.WARNING)

    started = time.monotonic()
    tasks = load_identities(tasks_file)
    if args.limit > 0:
        tasks = tasks[: args.limit]
    print(f"[{container_dir}] {len(tasks)} identities to process", flush=True)

    processor = ResultProcessorComponent(tasks, out_dir)

    # Header-only files from the exporter's own generators: an empty task list
    # writes the header and nothing else, so the header is the live one by
    # construction. The files are then reopened for append.
    processor._generate_coverage_csv([])
    processor._generate_errors_csv([])
    processor._generate_app_events_csv([])
    processor._generate_summary_csv([])
    for name in ("coverage.csv", "errors.csv", "app_events.csv", "summary.csv"):
        if os.path.getsize(os.path.join(out_dir, name)) == 0:
            # The generators are wrapped by ErrorHandler and absorb exceptions;
            # an empty file is the only trace that the header was not written.
            print(f"ERROR: header not written for {name}", file=sys.stderr)
            return 1

    def _open(name: str):
        return open(os.path.join(out_dir, name), "a", newline="", encoding="utf-8")

    # results.json nesting is the exporter's (`_generate_results_json`):
    # apk -> repetitions -> rep -> timeouts -> timeout -> tools -> tool.
    results_data: Dict[str, Any] = {}
    static_cache: Dict[str, Any] = {}
    unresolved_static = 0

    with (
        _open("coverage.csv") as fc,
        _open("errors.csv") as fe,
        _open("app_events.csv") as fa,
        _open("summary.csv") as fs,
    ):
        wc = _CountingWriter(csv.writer(fc))
        we = _CountingWriter(csv.writer(fe))
        wa = _CountingWriter(csv.writer(fa))
        ws = _CountingWriter(csv.writer(fs))

        for n, task in enumerate(tasks, 1):
            apk = task.config.apk_name
            task.result.logcat_file = host_logcat_path(
                container_dir, task.result.logcat_file
            )

            # `_resolve_static_data` treats a non-None `task.static_data` as its
            # parse memo and never re-parses. The first task of an APK arrives
            # with None, so the exporter parses the JSON exactly as it would live;
            # the parsed model is then handed to the APK's remaining tasks.
            # Tasks are sorted by APK, so one entry is the whole cache.
            if apk in static_cache:
                task.static_data = static_cache[apk]

            # Same order as `execute()`. The coverage writer reconstructs the
            # repository from the logcat and stores it on the task; the other
            # writers reuse it.
            processor._write_task_coverage_data(wc, task)
            processor._write_task_error_data(we, task)
            processor._write_task_app_events(wa, task)
            processor._write_task_summary_data(ws, task)

            rep, timeout = str(task.config.repetition), str(task.config.timeout)
            tool_name = task.config.tool_config.get_full_tool_name()
            results_data.setdefault(apk, {"repetitions": {}})["repetitions"].setdefault(
                rep, {"timeouts": {}}
            )["timeouts"].setdefault(timeout, {"tools": {}})["tools"][tool_name] = (
                processor._extract_task_data(task)
            )

            if task.static_data is not None:
                if apk not in static_cache:
                    static_cache = {apk: task.static_data}
                if not task.static_data.classes.classes:
                    unresolved_static += 1

            # Drop the reconstructed model: this is the whole point of the script.
            task.repository = None
            task.static_data = None

            if n % 100 == 0 or n == len(tasks):
                print(
                    f"  {n}/{len(tasks)} identities, {time.monotonic() - started:.0f}s",
                    flush=True,
                )

    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)

    # Timing only, no repository needed: the live delegate is cheap enough to call.
    PerformanceProcessorComponent(tasks, out_dir).generate()

    write_errors = sum(sum(t.result.write_errors.values()) for t in tasks)
    print(
        f"[{container_dir}] OK identities={len(tasks)} coverage_rows={wc.rows} "
        f"errors_rows={we.rows} app_events_rows={wa.rows} summary_rows={ws.rows} "
        f"unresolved_static={unresolved_static} write_errors={write_errors} "
        f"seconds={time.monotonic() - started:.0f} out={out_dir}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
