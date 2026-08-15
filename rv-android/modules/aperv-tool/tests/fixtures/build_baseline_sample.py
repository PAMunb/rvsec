#!/usr/bin/env python3
"""Copy and pin the baseline fixture — twelve runs of ``ape`` and ``droidbot``.

The baseline parsers have no fixture of their own in this repository: neither tool
emits NDJSON, so the golden trace fixture says nothing about them, and cmp162 has
no ``droidbot`` arm at all. Their only source of real input is the E2 raw corpus at
``/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS`` — 21,681 runs,
39.8 GB, outside any repository and read-only. A test suite that required that tree
would be unrunnable on any other machine, so a small sample is copied in and pinned
by sha256 beside the path it came from.

**Twelve runs, chosen for the cases the parsers must get right, not sampled.**

``ape`` — six runs, one per shape the parser has to survive:

* a trace with **no ``SATA begin step`` marker at all**. One in eighty sampled
  traces has none, and "no steps" is a first-class outcome rather than a bug: the
  run keeps its place in the denominator. A parser that raises here silently
  deletes a run from the analysis.
* a trace carrying a ``// NOT RESPONDING`` block, which the parser hoists to a
  run-level event attached to the preceding step index rather than parsing as a step.
* a 300 s run that produced only five steps, and four ordinary runs at 60 s.

``droidbot`` — six runs covering all four policies (``bfs_greedy``, ``bfs_naive``,
``dfs_greedy``, ``dfs_naive``), two of them at 300 s, and among those two the rare
run that reached an **orderly stop** (``INFO:DroidBot:DroidBot Stopped`` after
``Finish sending events``). Five of 150 sampled runs stop that way; every other run
is cut mid-stream by the timeout and must be flagged ``truncated``. Without one
stopped run in the fixture, ``truncated`` would be true of every input and the flag
would be untested.

The ``tasks.json`` slice carries only the records of these twelve identities. It is
what supplies the run window and outcome — no baseline trace carries an end-of-run
summary, so steps total, coverage and termination reason come from here or from
nowhere (plan §8.4 item 5).

Run from the rv-android root::

    .venv/bin/python modules/aperv-tool/tests/fixtures/build_baseline_sample.py

Read-only over the source corpus. No device, no emulator, no ``adb``
(INV-APV-35).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

SOURCE_CORPUS = Path("/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS")

# (relative trace path, why this run is in the fixture). The .logcat sibling of
# each is copied with it: the logcat is the one stream shaped identically for
# every arm, and it is where RVSEC and RVSEC-COV live for the baselines too.
SELECTED: tuple[tuple[str, str], ...] = (
    (
        "m2/results/exp_02/exp_02/com.shub39.dharmik.online_2200.apk/"
        "com.shub39.dharmik.online_2200.apk__1__60__ape.trace",
        "ape with no SATA begin step marker — 'no steps' as an outcome",
    ),
    (
        "m2/results/exp_02/exp_02/com.serwylo.retrowars_70.apk/"
        "com.serwylo.retrowars_70.apk__3__60__ape.trace",
        "ape carrying a // NOT RESPONDING block hoisted to a run-level event",
    ),
    (
        "m1/results/exp_00/exp_00/app.pwhs.universalinstaller_24.apk/"
        "app.pwhs.universalinstaller_24.apk__1__60__ape.trace",
        "ape, 50 steps at 60 s — the ordinary case, densest of the six",
    ),
    (
        "m1/results/exp_00/exp_00/at.techbee.jtx_216000015.apk/"
        "at.techbee.jtx_216000015.apk__3__300__ape.trace",
        "ape at 300 s that produced only 5 steps — a long budget, little progress",
    ),
    (
        "m1/results/exp_00/exp_00/app.eduroam.geteduroam_2685.apk/"
        "app.eduroam.geteduroam_2685.apk__3__60__ape.trace",
        "ape, single-activity application also present in cmp162",
    ),
    (
        "m1/results/exp_00/exp_00/app.plugbrain.android_154.apk/"
        "app.plugbrain.android_154.apk__2__60__ape.trace",
        "ape, second replica of a second application",
    ),
    (
        "m1/results/exp_00/exp_00/app.maskan.chat_90.apk/"
        "app.maskan.chat_90.apk__1__60__droidbot:bfs_greedy.trace",
        "droidbot bfs_greedy at 60 s — greedy prints 'Navigating to <state>' provenance",
    ),
    (
        "m1/results/exp_00/exp_00/app.maskan.chat_90.apk/"
        "app.maskan.chat_90.apk__1__60__droidbot:bfs_naive.trace",
        "droidbot bfs_naive at 60 s — naive prints 'selected a … view' provenance",
    ),
    (
        "m1/results/exp_00/exp_00/app.maskan.chat_90.apk/"
        "app.maskan.chat_90.apk__1__60__droidbot:dfs_greedy.trace",
        "droidbot dfs_greedy at 60 s",
    ),
    (
        "m1/results/exp_00/exp_00/app.maskan.chat_90.apk/"
        "app.maskan.chat_90.apk__1__60__droidbot:dfs_naive.trace",
        "droidbot dfs_naive at 60 s",
    ),
    (
        "m1/results/exp_00/exp_00/app.maskan.chat_90.apk/"
        "app.maskan.chat_90.apk__3__300__droidbot:dfs_naive.trace",
        "droidbot at 300 s that reached an orderly stop — truncated is False here alone",
    ),
    (
        "m1/results/exp_00/exp_00/app.maskan.chat_90.apk/"
        "app.maskan.chat_90.apk__3__300__droidbot:bfs_naive.trace",
        "droidbot at 300 s cut by the timeout — 109 actions, truncated",
    ),
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity_of(trace_name: str) -> tuple[str, int, int, str]:
    """``<apk>.apk__<rep>__<timeout>__<arm>`` → the identity tuple.

    Parsed here with a plain split rather than through ``run_identity`` because this
    script runs before that module exists in a fresh checkout, and a fixture builder
    that depends on the code under test is a fixture that cannot fail.
    """
    stem = trace_name[: -len(".trace")]
    apk, repetition, timeout, arm = stem.split("__", 3)
    return apk, int(repetition), int(timeout), arm


def slice_tasks(corpus: Path, wanted: set[tuple[str, int, int, str]]) -> list[dict]:
    """Extract the task records of exactly the selected identities.

    The arm label is rebuilt the way the consolidator rebuilds it — ``ape`` collapses
    its ``variant='default'`` to a bare ``ape`` — because the filename carries the
    collapsed form and the identity has to match on both sides.
    """
    batches = {Path(relative).parts[:4] for relative, _ in SELECTED}
    records: list[dict] = []
    for parts in sorted(batches):
        tasks_json = corpus.joinpath(*parts, "tasks.json")
        if not tasks_json.exists():
            continue
        document = json.loads(tasks_json.read_text())
        entries = document["tasks"] if isinstance(document, dict) else document
        for entry in entries:
            config = entry.get("config") or {}
            tool_config = config.get("tool_config") or {}
            name, variant = tool_config.get("name"), tool_config.get("variant")
            arm = "ape" if name == "ape" else f"{name}:{variant}"
            identity = (
                config.get("apk_name"),
                config.get("repetition"),
                config.get("timeout"),
                arm,
            )
            if identity in wanted:
                records.append(entry)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=SOURCE_CORPUS)
    parser.add_argument(
        "--dest", type=Path, default=Path(__file__).resolve().parent / "baseline_sample"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parent / "baseline_sample_manifest.json",
    )
    arguments = parser.parse_args()

    corpus: Path = arguments.corpus
    if not corpus.is_dir():
        raise SystemExit(f"source corpus not found: {corpus}")
    arguments.dest.mkdir(parents=True, exist_ok=True)

    runs = []
    identities: set[tuple[str, int, int, str]] = set()
    for relative, reason in SELECTED:
        trace_source = corpus / relative
        logcat_source = trace_source.with_suffix(".logcat")
        if not trace_source.exists() or not logcat_source.exists():
            raise SystemExit(f"missing pair for {relative}")

        apk, repetition, timeout, arm = identity_of(trace_source.name)
        identities.add((apk, repetition, timeout, arm))

        entry = {
            "apk": apk,
            "repetition": repetition,
            "timeout_s": timeout,
            "arm": arm,
            "tool": arm.split(":", 1)[0],
            "variant": arm.split(":", 1)[1] if ":" in arm else None,
            "reason": reason,
            "files": {},
        }
        for source in (trace_source, logcat_source):
            shutil.copy2(source, arguments.dest / source.name)
            entry["files"][source.name] = {
                "sha256": sha256_of(source),
                "bytes": source.stat().st_size,
                "source_path": str(source),
            }
        runs.append(entry)

    records = slice_tasks(corpus, identities)
    tasks_slice = arguments.dest / "tasks_slice.json"
    tasks_slice.write_text(json.dumps({"tasks": records}, indent=1) + "\n")

    manifest = {
        "fixture_class": "FIXTURE-REAL",
        "sample_of": str(corpus),
        "generated_by": "modules/aperv-tool/tests/fixtures/build_baseline_sample.py",
        "note": (
            "A hashed sample of the E2 raw corpus, copied in so the baseline parsers "
            "are testable without the 39.8 GB tree. The source corpus is read-only "
            "and is never modified; these copies are the fixture."
        ),
        "directory": "baseline_sample",
        "runs": runs,
        "tasks_slice": {
            "path": "baseline_sample/tasks_slice.json",
            "records": len(records),
            "note": (
                "No baseline trace carries an end-of-run summary — steps total, "
                "coverage and termination reason come from here, never from the trace."
            ),
        },
        "coverage": {
            "ape_runs": sum(1 for r in runs if r["tool"] == "ape"),
            "droidbot_runs": sum(1 for r in runs if r["tool"] == "droidbot"),
            "droidbot_variants": sorted(
                {r["variant"] for r in runs if r["tool"] == "droidbot"}
            ),
            "timeouts_s": sorted({r["timeout_s"] for r in runs}),
        },
    }
    arguments.manifest.write_text(json.dumps(manifest, indent=1) + "\n")

    total = sum(f["bytes"] for r in runs for f in r["files"].values())
    print(
        f"{arguments.dest}: {len(runs)} runs, {total / 1e6:.1f} MB copied; "
        f"tasks slice {len(records)} records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
