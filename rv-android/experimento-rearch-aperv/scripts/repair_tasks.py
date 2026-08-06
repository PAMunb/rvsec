#!/usr/bin/env python3
"""REPAIR — return an inadmissible task to the queue, after preserving its evidence.

**This script is remedial, not permanent machinery, and it is expected to find nothing.**
It exists because this campaign's records were written by code that reported a run
successful on the strength of the process having returned. INV-APV-60 now makes `tool.py`
raise when an exploration comes back materially short of its budget, so a truncated run is
stored `ERROR` with a message and the ordinary resume re-executes it with no operator
involved. Every campaign after this one self-heals that class; this script is here for the
records already on disk, and running it on a healthy tree is its regression test.

What it does, per identity judged inadmissible by `verify.admissibility_by_identity`:

1. Copies the run's `.logcat`, `.trace`, `.trace.ndjson.gz` and the container's original
   `tasks.json` to ``backup/gh97-truncated-runs/<container>/`` and writes a `SHA256SUMS`.
   **This is not caution.** The re-execution writes to the same filenames, so without the
   copy the evidence of the defect is destroyed by the act of repairing it.
2. Sets that record's ``result.state`` to the string ``"ERROR"`` — the enum *name*, which
   is what ``TaskState[...]`` reads back (``rv_android_core/domain/task.py``) — with an
   ``error_message`` naming the criterion that failed, so the record stops claiming a
   success and the next `docker compose up -d` re-executes the identity.

Nothing is mutated without ``--apply``. The dry run is also usable as a gate: it exits 1
when anything is inadmissible and 0 when the tree is clean.

The admissibility predicate is **imported from `verify.py` and never re-implemented here**.
INV-CAL-04 forbids `verify.py` sharing derivation with the *consolidator*; a repair tool
downstream of the verifier does not touch that, and two copies of the criteria would let a
run be repaired under a rule the gate does not apply.

Judging is per identity — best record first — never per record: a resume APPENDS a task
record rather than overwriting the failed one, so a record-wise scan double-counts every
recovery it has already fixed.

Usage (from the campaign directory):
    uv run python scripts/repair_tasks.py --iter-dir .              # dry run, mutates nothing
    uv run python scripts/repair_tasks.py --iter-dir . --apply      # preserve, then rewrite

`results/*/tasks.json` is written by the containers and is root-owned. When the host user
cannot write it, run the same command through the campaign image, which is how the two
repairs of 2026-08-06 were performed:

    docker run --rm -u 0 -v "$PWD:/w" -w /w --entrypoint python3 \
        phtcosta/rvandroid:0.9.3-rearch scripts/repair_tasks.py --iter-dir . --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify  # noqa: E402

# The artifacts a run leaves beside its trace. All three are copied because the defect is
# only legible across them: the trace says how far the exploration got, the logcat says what
# the application did, and the .gz is what offline consolidation reads.
ARTIFACT_SUFFIXES = ("logcat", "trace", "trace.ndjson.gz")

# Where the preserved evidence goes. `backup/` is NOT gitignored in this tree despite the
# top-level CLAUDE.md saying so, so it must never be `git add`ed.
DEFAULT_BACKUP_DIR = Path("backup/gh97-truncated-runs")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_sha256sums(directory: Path) -> None:
    """(Re)write SHA256SUMS over everything in the directory, in `sha256sum` format.

    Rewritten wholesale rather than appended so a second repair in the same container
    leaves one consistent manifest rather than two partial ones.
    """
    entries = sorted(p for p in directory.iterdir() if p.is_file() and p.name != "SHA256SUMS")
    lines = [f"{_sha256(p)}  {p.name}" for p in entries]
    (directory / "SHA256SUMS").write_text("\n".join(lines) + "\n")


def preserve(rec: Dict[str, Any], backup_dir: Path) -> List[str]:
    """Copy this run's artifacts and its container's tasks.json under `backup_dir`.

    Returns the names copied. A missing artifact is reported rather than fatal: a run that
    produced no trace at all is itself a finding, and refusing to preserve the rest of its
    evidence over the absence would lose what there is.
    """
    container = rec["base"].parent.name
    destination = backup_dir / container
    destination.mkdir(parents=True, exist_ok=True)

    copied: List[str] = []
    for suffix in ARTIFACT_SUFFIXES:
        source = verify.artifact_path(rec, suffix)
        if source.exists():
            shutil.copy2(source, destination / source.name)
            copied.append(source.name)

    # The container's whole tasks.json, once, before any record in it is rewritten. A
    # second repair in the same container must not overwrite the pre-repair copy with an
    # already-mutated one.
    before = destination / "tasks.json.before-repair"
    if not before.exists():
        shutil.copy2(rec["tasks_json"], before)
        copied.append(before.name)

    _write_sha256sums(destination)
    return copied


def rewrite(rec: Dict[str, Any], failures: List[Dict[str, Any]]) -> None:
    """Set this record's state to ERROR, naming the criteria it failed.

    The record is located by file and position, because a resume appends and position is
    the only thing that distinguishes two records of one identity. Its identity is
    re-checked against the loaded record before the write: rewriting the wrong record would
    corrupt a run that is fine, which is worse than the defect being repaired.
    """
    tasks_json = Path(rec["tasks_json"])
    payload = json.loads(tasks_json.read_text())
    task = payload["tasks"][rec["index"]]

    config = task.get("config") or {}
    if (config.get("apk_name"), config.get("repetition")) != (rec["apk"], rec["rep"]):
        raise SystemExit(
            f"refusing to write: {tasks_json} record {rec['index']} is "
            f"{config.get('apk_name')} rep {config.get('repetition')}, "
            f"expected {rec['apk']} rep {rec['rep']}"
        )

    criteria = ", ".join(f"{f['criterion']} ({f['detail']})" for f in failures)
    # The enum NAME, not its value: TaskState[...] reads the name back.
    task["result"]["state"] = "ERROR"
    task["result"]["error_message"] = f"inadmissible under Gate 6: {criteria}"

    temporary = tasks_json.with_suffix(".json.repair-tmp")
    temporary.write_text(json.dumps(payload, indent=2))
    temporary.replace(tasks_json)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--iter-dir", required=True, help="path to the campaign tree (holding results/)"
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help=(
            "where preserved evidence goes "
            f"(default: <iter-dir>/../{DEFAULT_BACKUP_DIR})"
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="preserve the evidence and rewrite the records; without it nothing is written",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report only — the default, accepted so it can be stated explicitly",
    )
    args = parser.parse_args(argv)

    if args.apply and args.dry_run:
        sys.stderr.write("--apply and --dry-run contradict each other\n")
        return 2

    iter_dir = Path(args.iter_dir).resolve()
    if not (iter_dir / "results").is_dir():
        sys.stderr.write(f"no results/ under {iter_dir}\n")
        return 2
    backup_dir = (
        Path(args.backup_dir).resolve()
        if args.backup_dir
        else iter_dir.parent / DEFAULT_BACKUP_DIR
    )

    scanned = verify.admissibility_by_identity(iter_dir)
    findings = [
        (ident, entry) for ident, entry in scanned.items() if entry["failures"]
    ]
    findings.sort(key=lambda item: tuple(str(x) for x in item[0]))

    print(f"identities scanned: {len(scanned)}")
    print(f"inadmissible: {len(findings)}")
    if not findings:
        print("nothing to repair — every identity is admissible under Gate 6")
        return 0

    for ident, entry in findings:
        rec = entry["record"]
        criteria = ", ".join(
            f"{f['criterion']} ({f['detail']})" for f in entry["failures"]
        )
        print(f"  {rec['base'].parent.name}  {ident}  fails {criteria}")

    if not args.apply:
        print("\ndry run — nothing was written. Re-run with --apply to repair.")
        return 1

    for _ident, entry in findings:
        rec = entry["record"]
        copied = preserve(rec, backup_dir)
        rewrite(rec, entry["failures"])
        print(f"repaired {rec['apk']} rep {rec['rep']}; preserved: {', '.join(copied)}")

    print(f"\n{len(findings)} record(s) set to ERROR; evidence under {backup_dir}")
    print("Re-execute them with: docker compose up -d <container>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
