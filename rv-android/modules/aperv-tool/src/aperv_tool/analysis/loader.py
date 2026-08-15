"""One or many batch directories into one tidy frame at the run grain.

This is the entry point of the analysis layer: every question downstream starts
from the frame this module returns, one row per identity
`(apk, rep, timeout, arm)`, carrying what the campaign recorded about that run
in `tasks.json` and in the two consolidated CSVs written at the same grain.

## What it joins, and what it refuses to

`tasks_record` supplies the run's own record and is the authority on which runs
exist — it is the only artefact that remembers a failure. `summary.csv` supplies
the coverage payload and `performance.csv` the observed duration and state, both
keyed `(apk, rep, timeout, tool)`, which is this frame's grain under another set
of column names. They are joined left onto the identities, never the other way
round: on cmp162 the two CSVs hold 1455 rows against 1458 identities, so a join
in the other direction would delete the three dead runs and leave a denominator
that looks complete.

`errors.csv`, `coverage.csv` and `app_events.csv` are event streams at a finer
grain — one row per violation, per covered method, per crash — and joining them
here would multiply the run grain by their cardinality. They belong to the
stream readers, and this module neither reads nor counts them.

## The arm table is what decomposes an arm

`tasks_record` keys identities on the raw `tool_config` pair and labels them with
the campaign's own collapse (`ape` rather than `ape:default`). That label is what
the CSVs and the filenames carry. The analysis-facing `(tool, variant)` pair
comes from the caller's arm table instead (INV-CAN-02), so an arm the caller did
not declare raises `UnknownArm` here rather than silently entering an analysis
as its own group. Both pairs stay on the frame: `tool_name`/`tool_variant` say
what the orchestrator wrote, `tool`/`variant` say what the analysis calls it,
and the difference between them is a real property of the campaign rather than
an inconsistency to be smoothed over.

## The double nesting is tolerated, not corrected

cmp162's batches sit at `results/<batch>/<batch>/`, a bind-mount artefact of the
container that wrote them. A root is therefore searched to a bounded depth for
`tasks.json`, and the directory holding one is a batch. The same call works when
the caller names the batch itself, the outer directory, or the results root, and
nothing has to be renamed on disk to make a campaign readable.

## `.trace.ndjson.gz` is not a second stream

Each run leaves a `.trace` and a `.logcat`, and `aperv` runs also leave a
`.trace.ndjson.gz` — a byte-identical gzip of the sibling `.trace`. A walk that
treats it as an artefact in its own right counts two traces per run and about
1.5 GB of redundancy per campaign as data. It is counted here as what it is, a
compressed sibling, and is never a run's `trace_path`.

Nothing is dropped in silence (INV-CAN-04). A missing CSV keeps every run with a
`NaN` payload and names the file; a CSV row matching no identity is counted; an
identity appearing in two batches is counted and named; a run with no trace is
counted. Read-only over every artefact, no device (INV-APV-35).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import pandas as pd

from aperv_tool.analysis import tasks_record
from aperv_tool.analysis.run_identity import decompose_arm, try_parse_run_filename

#: The record every batch is discovered by and read from.
TASKS_JSON = "tasks.json"

#: The consolidated CSVs written at the run grain, and the column each one
#: contributes nothing but. `summary.csv` carries the coverage payload;
#: `performance.csv` carries the duration and state as the CSV side saw them,
#: prefixed on the frame so a disagreement with `tasks.json` stays visible
#: rather than being resolved by whichever was merged last.
SUMMARY_CSV = "summary.csv"
PERFORMANCE_CSV = "performance.csv"
IDENTITY_CSVS = (SUMMARY_CSV, PERFORMANCE_CSV)

#: `performance.csv`'s columns, renamed on the frame.
_PERFORMANCE_RENAME = {
    "execution_time_seconds": "perf_execution_time_s",
    "task_state": "perf_task_state",
    "timestamp": "perf_timestamp",
}

#: What each identity-grain CSV contributes, as rv-platform writes it. The list
#: is declared rather than discovered because the promise on a missing file is a
#: `NaN` payload, and a payload of no columns at all would move the failure from
#: this module to whichever consumer indexed a column that stopped existing.
#: A campaign writing extra columns keeps them; the join is not restricted.
_PAYLOAD_COLUMNS = {
    SUMMARY_CSV: (
        "cov_act",
        "cov_class",
        "cov_method",
        "cov_reachable",
        "cov_reaches_target",
        "cov_directly_reaches_target",
        "mop_errors_total",
        "mop_errors_unique",
    ),
    PERFORMANCE_CSV: tuple(_PERFORMANCE_RENAME.values()),
}

#: How deep under a root a batch may sit. Three covers a campaign root
#: (`results/<batch>/<batch>/`), the results root, the outer directory and the
#: batch itself; an unbounded walk would descend into every run's `ape_output`.
_MAX_DEPTH = 3

#: The per-run streams, by the suffix that identifies them. `.trace.ndjson.gz`
#: is deliberately not among them.
_TRACE_SUFFIX = ".trace"
_LOGCAT_SUFFIX = ".logcat"
_COMPRESSED_TRACE_SUFFIX = ".trace.ndjson.gz"


@dataclass(frozen=True, slots=True)
class LoadDiagnostics:
    """What the load found, and everything it did not put on the frame.

    Attributes:
        roots: The roots as given.
        batches: The batch directories discovered, relative to their root.
        roots_without_batches: Roots holding no `tasks.json` at any admissible
            depth — a mistyped path, reported rather than returned as emptiness.
        task_records: Records read across every `tasks.json`.
        identities: Rows on the frame.
        completed_identities: Identities whose kept record is `COMPLETED`.
        dead_identities: Identities that never completed in any attempt.
        error_records: Records whose state is not `COMPLETED`.
        recovered_retries: `ERROR` records on identities that later completed.
        recovered_identities: Identities those retries fall across.
        superseded_records: Records dropped in favour of a better one.
        collisions: Identities that carried more than one record.
        unidentifiable_records: Records with no usable identity.
        duplicate_identities: Identities seen in more than one batch, named. The
            first is kept; a campaign that partitions its applications across
            batches produces none, and one appearing means two batches ran the
            same work.
        missing_files: `<batch>/<file>` for each identity-grain CSV absent. The
            runs survive with a `NaN` payload of the declared columns.
        payload_missing: `(csv, identities)` for identities left with a `NaN`
            payload — because the CSV had no row for them, as cmp162's three
            dead runs have in no consolidated CSV, or because the file itself
            was absent, in which case it is every identity of that batch.
        unmatched_csv_rows: `(csv, rows)` for CSV rows matching no identity. A
            non-zero count means the CSV and the record disagree about which
            runs exist.
        trace_files: `.trace` files found.
        logcat_files: `.logcat` files found.
        compressed_trace_siblings: `.trace.ndjson.gz` files found — counted,
            never a stream.
        identities_without_trace: Identities with no `.trace` on disk.
        identities_without_logcat: Identities with no `.logcat` on disk.
        artefacts_without_identity: Artefact names that parse as a run identity
            no record claims, and names that do not parse at all.
        current_status: `(batch, experiment.current_status)` as written, for
            reporting. Never a gate: cmp162 reads `running` in all eight.
    """

    roots: Tuple[str, ...] = ()
    batches: Tuple[str, ...] = ()
    roots_without_batches: Tuple[str, ...] = ()
    task_records: int = 0
    identities: int = 0
    completed_identities: int = 0
    dead_identities: int = 0
    error_records: int = 0
    recovered_retries: int = 0
    recovered_identities: int = 0
    superseded_records: int = 0
    collisions: int = 0
    unidentifiable_records: int = 0
    duplicate_identities: Tuple[str, ...] = ()
    missing_files: Tuple[str, ...] = ()
    payload_missing: Tuple[Tuple[str, int], ...] = ()
    unmatched_csv_rows: Tuple[Tuple[str, int], ...] = ()
    trace_files: int = 0
    logcat_files: int = 0
    compressed_trace_siblings: int = 0
    identities_without_trace: int = 0
    identities_without_logcat: int = 0
    artefacts_without_identity: Tuple[str, ...] = ()
    current_status: Tuple[Tuple[str, str | None], ...] = ()


def find_batches(root: Path | str) -> List[Path]:
    """The batch directories under `root`, in a stable order.

    A batch is a directory holding a `tasks.json`. The search is bounded rather
    than recursive so that a campaign root does not descend into every run's
    output directory, and it tolerates cmp162's `results/<batch>/<batch>/`
    double nesting without special-casing it.

    Args:
        root: A batch directory, a results root, or a campaign root.

    Returns:
        The batch directories, deduplicated and sorted.
    """
    base = Path(root)
    found: Dict[Path, None] = {}
    for depth in range(_MAX_DEPTH + 1):
        pattern = "/".join(["*"] * depth + [TASKS_JSON]) if depth else TASKS_JSON
        for path in sorted(base.glob(pattern)):
            found.setdefault(path.parent.resolve(), None)
    return sorted(found)


def _read_identity_csv(path: Path, name: str) -> pd.DataFrame | None:
    """One identity-grain CSV, renamed onto the frame's column names.

    Returns `None` when the file is absent, which the caller turns into a
    counted omission rather than into an empty join.
    """
    if not path.is_file():
        return None
    frame = pd.read_csv(path)
    frame = frame.rename(columns={"timeout": "timeout_s", "tool": "arm"})
    if name == PERFORMANCE_CSV:
        frame = frame.rename(columns=_PERFORMANCE_RENAME)
    return frame


def _artefacts(
    batch: Path,
) -> Tuple[Dict[Tuple[Any, ...], Dict[str, Path]], Dict[str, int], List[str]]:
    """The per-run streams of one batch, keyed by identity.

    Each application has its own directory beside the CSVs. Only that directory
    is listed — never walked — so a run's `ape_output/` subtree costs nothing
    and no `.mop.json` is ever opened (INV-CAN-24).

    Returns:
        The identity → `{"trace": path, "logcat": path}` map, the counts
        (`trace_files`, `logcat_files`, `compressed_trace_siblings`), and the
        artefact names that carry no parsable identity.
    """
    streams: Dict[Tuple[Any, ...], Dict[str, Path]] = {}
    counts = {"trace_files": 0, "logcat_files": 0, "compressed_trace_siblings": 0}
    unparsed: List[str] = []

    for entry in sorted(batch.iterdir()):
        if not entry.is_dir():
            continue
        for artefact in sorted(entry.iterdir()):
            name = artefact.name
            if name.endswith(_COMPRESSED_TRACE_SUFFIX):
                counts["compressed_trace_siblings"] += 1
                continue
            if name.endswith(_TRACE_SUFFIX):
                kind, counter = "trace", "trace_files"
            elif name.endswith(_LOGCAT_SUFFIX):
                kind, counter = "logcat", "logcat_files"
            else:
                continue
            counts[counter] += 1
            key = try_parse_run_filename(artefact)
            if key is None:
                unparsed.append(name)
                continue
            streams.setdefault((key.apk, key.arm, key.repetition, key.timeout_s), {})[
                kind
            ] = artefact

    return streams, counts, unparsed


def _batch_frame(
    batch: Path,
) -> Tuple[pd.DataFrame, tasks_record.TaskDiagnostics, Dict[str, Any]]:
    """One batch: identities, their CSV payload, their artefact paths."""
    frame, task_diagnostics = tasks_record.load(batch / TASKS_JSON)
    notes: Dict[str, Any] = {
        "missing_files": [],
        "payload_missing": {},
        "unmatched_csv_rows": {},
    }

    for name in IDENTITY_CSVS:
        payload = _read_identity_csv(batch / name, name)
        if payload is None:
            notes["missing_files"].append(f"{batch.name}/{name}")
            for column in _PAYLOAD_COLUMNS[name]:
                frame[column] = float("nan")
            notes["payload_missing"][name] = len(frame)
            notes["unmatched_csv_rows"][name] = 0
            continue
        keys = list(tasks_record.IDENTITY_COLUMNS)
        merged = frame.merge(payload, on=keys, how="left", indicator=True)
        notes["payload_missing"][name] = int((merged["_merge"] == "left_only").sum())
        matched = payload.merge(frame[keys], on=keys, how="left", indicator=True)
        notes["unmatched_csv_rows"][name] = int(
            (matched["_merge"] == "left_only").sum()
        )
        frame = merged.drop(columns="_merge")

    streams, counts, unparsed = _artefacts(batch)
    identities = list(
        zip(frame["apk"], frame["arm"], frame["rep"], frame["timeout_s"])
        if not frame.empty
        else []
    )
    frame["trace_path"] = [
        (
            str(streams.get(key, {}).get("trace"))
            if streams.get(key, {}).get("trace")
            else None
        )
        for key in identities
    ]
    frame["logcat_path"] = [
        (
            str(streams.get(key, {}).get("logcat"))
            if streams.get(key, {}).get("logcat")
            else None
        )
        for key in identities
    ]
    # The trace's size, beside its path. It is the one artefact fact `liveness`
    # needs that no stream reader has to be run to obtain — the file has already
    # been resolved here, and a `stat` is what separates a run that produced
    # nothing from one that produced nothing *this reader looked at*. Without it
    # the corpse gate cannot fire on a bare Layer-0 frame, which is exactly the
    # gate whose absence let an 864-byte trace be read as a legitimate zero.
    # None, never 0: a zero here would assert an empty file was measured.
    frame["trace_bytes"] = [
        (path.stat().st_size if (path := streams.get(key, {}).get("trace")) else None)
        for key in identities
    ]
    frame.insert(0, "batch", batch.name)

    claimed = set(identities)
    notes["artefacts_without_identity"] = list(unparsed) + [
        f"{key[0]}__{key[2]}__{key[3]}__{key[1]}"
        for key in sorted(streams)
        if key not in claimed
    ]
    notes["counts"] = counts
    return frame, task_diagnostics, notes


def load(
    roots: Path | str | Iterable[Path | str],
    arm_table: Mapping[str, Tuple[str, str]],
) -> Tuple[pd.DataFrame, LoadDiagnostics]:
    """Read a campaign into one tidy frame at `(apk, rep, timeout, arm)`.

    Args:
        roots: One root or many. Each may be a batch directory, a results root
            or a campaign root; the double nesting is tolerated.
        arm_table: The campaign's arm roster as data, arm label →
            `(tool, variant)`. An arm on disk that is absent from it raises.

    Returns:
        The frame — one row per identity, with the task record's columns, the
        `summary.csv` payload, `performance.csv`'s duration and state under a
        `perf_` prefix, the arm table's `(tool, variant)` and the run's
        `trace_path` / `logcat_path` — and the `LoadDiagnostics`.

    Raises:
        UnknownArm: An arm present in the records is absent from `arm_table`.
        IdentityCollisionUnresolved: Propagated from `tasks_record`.
    """
    if isinstance(roots, (str, Path)):
        given: Sequence[Path] = [Path(roots)]
    else:
        given = [Path(root) for root in roots]

    frames: List[pd.DataFrame] = []
    batches: List[str] = []
    empty_roots: List[str] = []
    status: List[Tuple[str, str | None]] = []
    totals = {
        "task_records": 0,
        "error_records": 0,
        "recovered_retries": 0,
        "recovered_identities": 0,
        "superseded_records": 0,
        "collisions": 0,
        "unidentifiable_records": 0,
        "trace_files": 0,
        "logcat_files": 0,
        "compressed_trace_siblings": 0,
    }
    missing_files: List[str] = []
    payload_missing: Dict[str, int] = {}
    unmatched: Dict[str, int] = {}
    orphan_artefacts: List[str] = []

    for root in given:
        found = find_batches(root)
        if not found:
            empty_roots.append(str(root))
        for batch in found:
            frame, diagnostics, notes = _batch_frame(batch)
            frames.append(frame)
            batches.append(batch.name)
            status.append((batch.name, diagnostics.current_status))
            totals["task_records"] += diagnostics.lines
            totals["error_records"] += diagnostics.error_records
            totals["recovered_retries"] += diagnostics.recovered_retries
            totals["recovered_identities"] += diagnostics.recovered_identities
            totals["superseded_records"] += diagnostics.superseded_records
            totals["collisions"] += diagnostics.collisions
            totals["unidentifiable_records"] += diagnostics.unidentifiable_records
            for key, value in notes["counts"].items():
                totals[key] += value
            missing_files.extend(notes["missing_files"])
            for name, count in notes["payload_missing"].items():
                payload_missing[name] = payload_missing.get(name, 0) + count
            for name, count in notes["unmatched_csv_rows"].items():
                unmatched[name] = unmatched.get(name, 0) + count
            orphan_artefacts.extend(notes["artefacts_without_identity"])

    frame = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=["batch", *tasks_record.COLUMNS])
    )

    keys = list(tasks_record.IDENTITY_COLUMNS)
    duplicates: List[str] = []
    if not frame.empty:
        repeated = frame.duplicated(subset=keys, keep="first")
        duplicates = [
            "__".join(str(part) for part in row)
            for row in frame.loc[repeated, keys].itertuples(index=False)
        ]
        frame = frame.loc[~repeated].reset_index(drop=True)

        decomposed = {
            arm: decompose_arm(arm, arm_table) for arm in sorted(set(frame["arm"]))
        }
        frame["tool"] = [decomposed[arm][0] for arm in frame["arm"]]
        frame["variant"] = [decomposed[arm][1] for arm in frame["arm"]]
        frame = frame.sort_values(keys).reset_index(drop=True)

    completed = (
        int((frame["state"] == tasks_record.COMPLETED).sum()) if not frame.empty else 0
    )
    missing_trace = int(frame["trace_path"].isna().sum()) if not frame.empty else 0
    missing_logcat = int(frame["logcat_path"].isna().sum()) if not frame.empty else 0

    diagnostics = LoadDiagnostics(
        roots=tuple(str(root) for root in given),
        batches=tuple(batches),
        roots_without_batches=tuple(empty_roots),
        task_records=totals["task_records"],
        identities=len(frame),
        completed_identities=completed,
        dead_identities=len(frame) - completed,
        error_records=totals["error_records"],
        recovered_retries=totals["recovered_retries"],
        recovered_identities=totals["recovered_identities"],
        superseded_records=totals["superseded_records"],
        collisions=totals["collisions"],
        unidentifiable_records=totals["unidentifiable_records"],
        duplicate_identities=tuple(duplicates),
        missing_files=tuple(missing_files),
        payload_missing=tuple(sorted(payload_missing.items())),
        unmatched_csv_rows=tuple(sorted(unmatched.items())),
        trace_files=totals["trace_files"],
        logcat_files=totals["logcat_files"],
        compressed_trace_siblings=totals["compressed_trace_siblings"],
        identities_without_trace=missing_trace,
        identities_without_logcat=missing_logcat,
        artefacts_without_identity=tuple(orphan_artefacts),
        current_status=tuple(status),
    )
    return frame, diagnostics
