"""The authoritative run record: `tasks.json`, read by identity.

A campaign's `tasks.json` is the only artefact that remembers the runs that
failed. The consolidated CSVs are written from the successes alone — on cmp162
`performance.csv` holds 1455 rows and every one of them is
`TaskState.COMPLETED`, against 1458 identities the campaign actually attempted —
so an analysis that starts from the CSVs starts from a denominator that has
already been silently trimmed of exactly the runs worth explaining.

Three properties of the file drive everything this module does.

**A resume appends; it never overwrites.** When rv-platform retries a task it
writes a *new* record with a fresh UUID beside the old one. The consequence is
that `task_id` is not the run: cmp162 carries 1486 records for 1458 runs. The
key is therefore the identity `(apk, tool, variant, repetition, timeout)`
(INV-CAN-03), and the 28 extra records are superseded attempts, not extra runs.
That number is worth keeping distinct from the retry census below, because
1486 − 1458 = 28 counts *records dropped in favour of a better one*, while the
retries are counted per `ERROR` record and per identity and come to 31 and 24.

**`COMPLETED` appears inside a record as well as on it.** Every record carries a
`state_transitions[]` list of the states it moved through, and those entries
carry the same vocabulary as the record's own `state`. Over cmp162's eight files
there are 7430 such entries, so `grep -c COMPLETED` returns 2910 against 1455
real completions — off by a factor of two, in the direction that looks
plausible. `state_transitions[]` is counted here as transitions and never as
records; the file is parsed, never grepped.

**`experiment.current_status` says nothing about the data.** It reads `running`
in all eight cmp162 files, written when the batch started and never updated by
whatever stopped it. It is surfaced by the reader and used as a gate by nothing:
a gate on it would discard a finished campaign entire.

## The collision policy

An identity holding more than one record is resolved, never averaged and never
taken last-wins:

- If any record `COMPLETED`, the `COMPLETED` record with the larger
  `method_coverage` wins and the collision is counted. Only `COMPLETED` records
  compete, which matters because an `ERROR` record can legitimately carry the
  *larger* number: `com.daniebeler.pfpixelix_40.apk / ape / rep 2` holds an
  `ERROR` at 181 s with `method_coverage=9.667` and the `COMPLETED` retry at
  360 s with 9.483. The failed attempt explored more before it died; it is still
  the attempt that did not finish.
- Two `COMPLETED` records tying on coverage with different payloads raise
  `IdentityCollisionUnresolved` naming both. There is no defensible automatic
  answer, and picking one silently would make the analysis depend on file order.
- An identity with no `COMPLETED` record — a dead identity — keeps its last
  record. The last attempt is the one that decided the run's fate.

## The two failure classes are not the same event

`ERROR` records split into two classes that must not be added together, because
they differ in whether the application ran at all (measured over cmp162's 31
`ERROR` records on 2026-08-15):

| class | records | duration | coverage |
|---|---|---|---|
| `install_failure` | 18 | 51–69 s | `0.0 / 0.0` — the application never started |
| `tool_execution_failure` | 13 | 127–298 s | non-zero — it ran and the component died |

The second class is why the collision policy exists at all: both of its records
carry a plausible coverage number, so "keep the last" and "keep the largest"
give different answers on real data. It is also why an install failure and a
mid-exploration death cannot share a denominator — one is an infrastructure
event about the harness, the other an observation about the run.

Nothing is dropped in silence (INV-CAN-04): superseded records, retries, dead
identities, unidentifiable records and transition entries all leave in
`TaskDiagnostics`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import pandas as pd

from aperv_tool.analysis import run_identity
from aperv_tool.analysis.run_identity import arm_label

#: The identity columns of the returned frame, in the order a caller groups by.
#: Imported, never redeclared: `gates` once kept its own tuple with a different
#: spelling of the replica column and no real frame could satisfy both.
IDENTITY_COLUMNS = run_identity.IDENTITY_COLUMNS

#: Every column the frame carries, so an empty file still returns a usable
#: shape rather than a frame with no columns for the caller to concatenate.
COLUMNS = IDENTITY_COLUMNS + (
    "tool_name",
    "tool_variant",
    "state",
    "error_class",
    "error_message",
    "execution_time_s",
    "start_time",
    "end_time",
    "tool_execution_start",
    "method_coverage",
    "activities_coverage",
    "methods_mop_reachable_coverage",
    "total_errors",
    "total_method_calls",
    "detected_errors_count",
    "trace_file",
    "logcat_file",
    "task_id",
    "records",
    "error_records",
)

#: The state a finished run carries. Everything else is a failure of some class.
COMPLETED = "COMPLETED"

#: The `error_message` fragments that separate the two failure classes. Matching
#: on the message rather than on a code is what the record allows: rv-platform
#: writes one `TaskExecutionError` wrapper around both causes and distinguishes
#: them only in prose.
_INSTALL_MARKER = "Failed to install app"
_TOOL_EXECUTION_MARKER = "Component ToolExecutionComponent execution failed"

#: Class labels. `""` marks a record that did not fail, so the column stays a
#: string and a groupby never has to handle a null level.
INSTALL_FAILURE = "install_failure"
TOOL_EXECUTION_FAILURE = "tool_execution_failure"
OTHER_FAILURE = "other"
NO_FAILURE = ""


class IdentityCollisionUnresolved(Exception):
    """Two `COMPLETED` records for one identity, tied on coverage and different.

    Raised rather than resolved. The author decides which attempt the campaign
    meant to keep; code that picked one would make every downstream number
    depend on the order records happen to sit in the file.

    Attributes:
        identity: The `(apk, tool, variant, repetition, timeout)` tuple.
        task_ids: The two colliding record ids, in file order.
    """

    def __init__(
        self, identity: Tuple[Any, ...], task_ids: Tuple[str, str], coverage: float
    ) -> None:
        super().__init__(
            f"identity {identity!r} has two COMPLETED records tied at "
            f"method_coverage={coverage!r} with different payloads: "
            f"{task_ids[0]!r} and {task_ids[1]!r}"
        )
        self.identity = identity
        self.task_ids = task_ids


@dataclass(frozen=True, slots=True)
class TaskDiagnostics:
    """What the file held, and what resolving it to identities cost.

    Attributes:
        lines: Records in `tasks` — the file is a JSON document, so these are
            objects rather than physical lines, and `state_transitions[]`
            entries are never among them.
        identities: Distinct runs, after the collision policy.
        completed_identities: Identities whose kept record is `COMPLETED`.
        dead_identities: Identities with no `COMPLETED` record in any attempt.
            On cmp162 there are three, all `com.ds.avare_404.apk` on
            `aperv:mop_on_llm_off`, retried three times each.
        collisions: Identities that carried more than one record.
        superseded_records: Records dropped in favour of a better one for the
            same identity. `lines - identities`, and *not* the retry count.
        error_records: Records whose state is not `COMPLETED`.
        recovered_retries: `ERROR` records belonging to an identity that later
            completed — a transient failure the campaign recovered from.
        recovered_identities: How many identities those retries fall across.
            Lower than `recovered_retries` whenever one identity failed twice.
        error_records_by_class: `(class, count)` pairs over `error_records`,
            keeping install failures and mid-exploration deaths apart.
        unidentifiable_records: Records with no usable identity — a truncated or
            malformed entry. Counted, never silently skipped.
        state_transition_entries: Entries inside `state_transitions[]`, the
            quantity a grep over this file would confuse with records.
        current_status: `experiment.current_status` as written. Reported so a
            caller can print it; never read as a gate.
        dead_identity_keys: `(apk, arm, rep, timeout)` per dead identity, so the
            caller can name them rather than only count them.
    """

    lines: int = 0
    identities: int = 0
    completed_identities: int = 0
    dead_identities: int = 0
    collisions: int = 0
    superseded_records: int = 0
    error_records: int = 0
    recovered_retries: int = 0
    recovered_identities: int = 0
    error_records_by_class: Tuple[Tuple[str, int], ...] = ()
    unidentifiable_records: int = 0
    state_transition_entries: int = 0
    current_status: str | None = None
    dead_identity_keys: Tuple[Tuple[str, str, int, int], ...] = field(default=())


def classify_error(message: str | None) -> str:
    """The failure class of an `ERROR` record's message.

    Args:
        message: `result.error_message`, possibly absent.

    Returns:
        `install_failure` when the application never installed,
        `tool_execution_failure` when the exploration component died mid-run,
        `other` for an unrecognised message, `""` for no failure at all.
    """
    if not message:
        return NO_FAILURE
    if _INSTALL_MARKER in message:
        return INSTALL_FAILURE
    if _TOOL_EXECUTION_MARKER in message:
        return TOOL_EXECUTION_FAILURE
    return OTHER_FAILURE


def _records_of(document: Any) -> List[Dict[str, Any]]:
    """The record list, whichever of the two shapes the file uses.

    rv-platform writes `{"version": …, "tasks": [...]}`; older batches wrote the
    bare list. Both are read, because a reader that handled one would report a
    whole campaign as empty rather than as unreadable.
    """
    if isinstance(document, Mapping):
        records = document.get("tasks")
    else:
        records = document
    return [record for record in records or [] if isinstance(record, Mapping)]


def _identity(record: Mapping[str, Any]) -> Tuple[Any, ...] | None:
    """`(apk, tool, variant, repetition, timeout)`, or `None` if unusable.

    The raw `tool_config` pair keys the identity (INV-CAN-03), not the collapsed
    arm label: the label is a presentation of that pair, and keying on a
    presentation makes the key depend on a display rule.
    """
    config = record.get("config") or {}
    tool_config = config.get("tool_config") or {}
    apk = config.get("apk_name")
    tool = tool_config.get("name")
    repetition = config.get("repetition")
    timeout = config.get("timeout")
    if apk is None or tool is None or repetition is None or timeout is None:
        return None
    return (apk, tool, tool_config.get("variant"), repetition, timeout)


def _coverage_rank(record: Mapping[str, Any]) -> float:
    """The scalar the collision policy orders `COMPLETED` records by.

    `method_coverage` is the campaign's primary coverage metric — the one its
    per-application aggregate is built on — and the one that is zero exactly
    when the application never ran. A record that carries no number at all ranks
    below every record that carries one, rather than being treated as zero,
    because "not measured" and "measured as nothing" are different runs.
    """
    metrics = record.get("coverage_metrics") or {}
    value = metrics.get("method_coverage")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return float("-inf")
    return float(value)


# Fields a retry changes by construction, and which therefore say nothing about
# whether two attempts observed different things.
_RETRY_VOLATILE = frozenset({"state_transitions", "write_errors"})


def _payload(record: Mapping[str, Any]) -> Tuple[Any, Any]:
    """The record's content, minus what a retry changes by construction.

    The id differs between any two records; `state_transitions[]` records
    wall-clock instants; and `write_errors` counts rows this run's result
    processing failed to write — per-run I/O noise, not an observation about the
    application. Two tied `COMPLETED` records differing only in `write_errors`
    would otherwise raise `IdentityCollisionUnresolved` and abort the whole load,
    on the strength of a disk hiccup. What is left is what a tie has to be judged
    on.
    """
    result = {
        key: value
        for key, value in (record.get("result") or {}).items()
        if key not in _RETRY_VOLATILE
    }
    return (record.get("config"), result)


def _resolve(
    identity: Tuple[Any, ...], records: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any]:
    """The one record that represents this identity.

    Args:
        identity: The identity tuple, used only in the error message.
        records: Its records, in file order.

    Returns:
        The `COMPLETED` record with the largest `method_coverage`, or — when
        none completed — the last attempt.

    Raises:
        IdentityCollisionUnresolved: Two `COMPLETED` records tie on coverage and
            differ in payload.
    """
    completed = [
        r for r in records if (r.get("result") or {}).get("state") == COMPLETED
    ]
    if not completed:
        return records[-1]

    best = completed[0]
    for candidate in completed[1:]:
        best_rank = _coverage_rank(best.get("result") or {})
        candidate_rank = _coverage_rank(candidate.get("result") or {})
        if candidate_rank > best_rank:
            best = candidate
        elif candidate_rank == best_rank and _payload(candidate) != _payload(best):
            raise IdentityCollisionUnresolved(
                identity,
                (str(best.get("id")), str(candidate.get("id"))),
                candidate_rank,
            )
    return best


def _row(
    identity: Tuple[Any, ...], record: Mapping[str, Any], records: int, errors: int
) -> Dict[str, Any]:
    """One frame row from the kept record."""
    apk, tool, variant, repetition, timeout = identity
    result = record.get("result") or {}
    metrics = result.get("coverage_metrics") or {}
    state = result.get("state")
    return {
        "apk": apk,
        "arm": arm_label(tool, variant),
        "rep": int(repetition),
        "timeout_s": int(timeout),
        "tool_name": tool,
        "tool_variant": variant,
        "state": state,
        "error_class": (
            NO_FAILURE
            if state == COMPLETED
            else classify_error(result.get("error_message"))
        ),
        "error_message": result.get("error_message"),
        "execution_time_s": result.get("execution_time_seconds"),
        "start_time": result.get("start_time"),
        "end_time": result.get("end_time"),
        "tool_execution_start": result.get("tool_execution_start"),
        "method_coverage": metrics.get("method_coverage"),
        "activities_coverage": metrics.get("activities_coverage"),
        "methods_mop_reachable_coverage": metrics.get("methods_mop_reachable_coverage"),
        "total_errors": metrics.get("total_errors"),
        "total_method_calls": metrics.get("total_method_calls"),
        "detected_errors_count": result.get("detected_errors_count"),
        "trace_file": result.get("trace_file"),
        "logcat_file": result.get("logcat_file"),
        "task_id": record.get("id"),
        "records": records,
        "error_records": errors,
    }


def load(tasks_json: Path | str) -> Tuple[pd.DataFrame, TaskDiagnostics]:
    """Read one batch's `tasks.json` into one row per identity.

    Args:
        tasks_json: The batch's `tasks.json`. Read-only.

    Returns:
        The frame — one row per identity, sorted by identity, with the columns
        of `COLUMNS` — and the `TaskDiagnostics` describing what resolving the
        file to identities cost.

    Raises:
        IdentityCollisionUnresolved: Two `COMPLETED` records for one identity
            tie on coverage and differ in payload.
    """
    path = Path(tasks_json)
    document = json.loads(path.read_text())
    records = _records_of(document)

    current_status = None
    if isinstance(document, Mapping):
        current_status = (document.get("experiment") or {}).get("current_status")

    by_identity: Dict[Tuple[Any, ...], List[Mapping[str, Any]]] = {}
    unidentifiable = 0
    transitions = 0
    error_records = 0
    by_class: Dict[str, int] = {}

    for record in records:
        result = record.get("result") or {}
        transitions += len(result.get("state_transitions") or [])
        if result.get("state") != COMPLETED:
            error_records += 1
            label = classify_error(result.get("error_message"))
            by_class[label] = by_class.get(label, 0) + 1
        identity = _identity(record)
        if identity is None:
            unidentifiable += 1
            continue
        by_identity.setdefault(identity, []).append(record)

    rows: List[Dict[str, Any]] = []
    collisions = 0
    superseded = 0
    dead_keys: List[Tuple[str, str, int, int]] = []
    recovered_retries = 0
    recovered_identities = 0

    for identity, attempts in by_identity.items():
        kept = _resolve(identity, attempts)
        failures = sum(
            1 for r in attempts if (r.get("result") or {}).get("state") != COMPLETED
        )
        if len(attempts) > 1:
            collisions += 1
            superseded += len(attempts) - 1
        row = _row(identity, kept, len(attempts), failures)
        if row["state"] != COMPLETED:
            dead_keys.append((row["apk"], row["arm"], row["rep"], row["timeout_s"]))
        elif failures:
            recovered_retries += failures
            recovered_identities += 1
        rows.append(row)

    frame = pd.DataFrame.from_records(rows, columns=list(COLUMNS))
    if not frame.empty:
        frame = frame.sort_values(list(IDENTITY_COLUMNS)).reset_index(drop=True)

    diagnostics = TaskDiagnostics(
        lines=len(records),
        identities=len(by_identity),
        completed_identities=len(by_identity) - len(dead_keys),
        dead_identities=len(dead_keys),
        collisions=collisions,
        superseded_records=superseded,
        error_records=error_records,
        recovered_retries=recovered_retries,
        recovered_identities=recovered_identities,
        error_records_by_class=tuple(sorted(by_class.items())),
        unidentifiable_records=unidentifiable,
        state_transition_entries=transitions,
        current_status=current_status,
        dead_identity_keys=tuple(sorted(dead_keys)),
    )
    return frame, diagnostics
