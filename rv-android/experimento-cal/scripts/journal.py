#!/usr/bin/env python3
"""Provenance journal for the calibration loop (methodology §3.2, INV-CAL-11).

Every state transition of the calibration loop (CONFIG-GEN → PRE-FLIGHT → SMOKE →
RUN+MONITOR → CONSOLIDATE → VERIFY → ANALYZE → DECIDE) appends exactly one JSON line
to `calibracao/journal.jsonl`. Each line binds a produced artifact to the state that
produced it and to the artifact's content hash, so that any figure cited later in a
report or paper can be traced back — through the journal and the per-iteration
`iterN/` snapshots — to the raw logcat it came from.

The journal is **append-only** (INV-CAL-11): existing lines are never rewritten. A
discarded iteration keeps its journal lines as provenance, exactly like a discarded
`iterN/` directory (INV-CAL-12). This is intentional: the record of what was tried and
rejected is itself evidence.

Each record has the fixed schema:

    {"ts": <UTC ISO-8601>, "iter": <int>, "state": <str>,
     "artifact": <path str>, "sha256": <hex digest of the artifact file>}

`ts` is the wall-clock UTC instant of the append. `sha256` is the hash of the artifact
file *at append time* — the journal captures the artifact as it existed when the
transition was recorded, so a later edit to the artifact is detectable as a hash
mismatch. This is a normal Python CLI (not a hermetic Workflow script), so `datetime`
is allowed for the timestamp (contracts doc: "Normal Python CLIs ... datetime ... ARE
allowed").

The journal lives at `<repo-root>/calibracao/journal.jsonl` — the campaign-level
directory that outlives individual iterations. The directory is created on first use.
`--journal PATH` overrides the target file (used by tests to point at a tmp file).

Exit codes: 0 = the line was appended; 2 = usage error (missing artifact file).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

# scripts/ -> experimento-cal/ -> rv-android/ (repo root). The campaign-level journal
# lives under the repo root, not under experimento-cal/, because it outlives any single
# iteration (spec "Directory layout": calibracao/ holds campaign-level artifacts).
_SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPTS_DIR.parent.parent
DEFAULT_JOURNAL = REPO_ROOT / "calibracao" / "journal.jsonl"


def sha256_of(path: Path) -> str:
    """Return the hex SHA-256 digest of a file's bytes, read in chunks.

    Chunked reads keep memory flat regardless of artifact size (manifests are small,
    but a snapshot could be a multi-megabyte jar in Phase B).
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_iso() -> str:
    """Return the current UTC instant as an ISO-8601 string with a trailing 'Z'.

    A timezone-aware UTC datetime is formatted and its explicit '+00:00' offset is
    normalized to the compact 'Z' suffix, matching the manifest's `generated_utc`
    convention (contracts doc manifest schema).
    """
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def append_record(
    state: str, iteration: int, artifact: Path, journal_path: Path
) -> dict:
    """Append one provenance record and return it.

    Creates the journal's parent directory on first use (INV-CAL-11: "creating
    calibracao/ on first use"). Opens the file in append mode so no existing byte is
    ever rewritten — the append-only guarantee is enforced by the open mode, not by
    re-reading and re-writing the file.
    """
    record = {
        "ts": utc_now_iso(),
        "iter": iteration,
        "state": state,
        "artifact": str(artifact),
        "sha256": sha256_of(artifact),
    }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="journal.py",
        description="Append a provenance record to the calibration journal.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    append = sub.add_parser(
        "append",
        help="Append one JSON line recording a state transition.",
    )
    append.add_argument(
        "--state",
        required=True,
        help="Loop state that produced the artifact (e.g. CONFIG-GEN, VERIFY, DECIDE).",
    )
    append.add_argument(
        "--iter",
        dest="iteration",
        required=True,
        type=int,
        help="Iteration number N (matches iterN/).",
    )
    append.add_argument(
        "--artifact",
        required=True,
        type=Path,
        help="Path to the artifact this transition produced; its sha256 is recorded.",
    )
    append.add_argument(
        "--journal",
        type=Path,
        default=DEFAULT_JOURNAL,
        help="Journal file to append to (default: <repo-root>/calibracao/journal.jsonl).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "append":
        artifact: Path = args.artifact
        if not artifact.is_file():
            sys.stderr.write(f"artifact not found: {artifact}\n")
            return 2
        record = append_record(args.state, args.iteration, artifact, args.journal)
        # Echo the appended line so the agent-visible gate summary shows exactly what
        # was recorded (design decision 8: journal appends are auditable actions).
        print(json.dumps(record))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
