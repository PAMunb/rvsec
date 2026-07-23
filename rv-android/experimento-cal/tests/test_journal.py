"""Tests for the append-only provenance journal (journal.py, INV-CAL-11).

Run with the CI flags (conftest puts experimento-cal/scripts/ on sys.path):

    uv run pytest experimento-cal/tests/test_journal.py --import-mode=importlib -o "addopts="
"""

from __future__ import annotations

import hashlib
import json

import journal


def test_journal_append_schema(tmp_path):
    """One append writes exactly one schema-correct line whose sha256 is the artifact's
    real hash, and a second append leaves the first line byte-for-byte unchanged."""
    journal_path = tmp_path / "journal.jsonl"

    artifact = tmp_path / "verification_report.md"
    content = b"# verification report\nadmissible\n"
    artifact.write_bytes(content)
    expected_sha = hashlib.sha256(content).hexdigest()

    rc = journal.main(
        [
            "append",
            "--state",
            "VERIFY",
            "--iter",
            "1",
            "--artifact",
            str(artifact),
            "--journal",
            str(journal_path),
        ]
    )
    assert rc == 0

    # Exactly one line, parses as JSON, exact key set.
    lines_after_first = journal_path.read_text(encoding="utf-8").splitlines()
    assert len(lines_after_first) == 1
    record = json.loads(lines_after_first[0])
    assert set(record) == {"ts", "iter", "state", "artifact", "sha256"}
    assert record["iter"] == 1
    assert record["state"] == "VERIFY"
    assert record["artifact"] == str(artifact)
    assert record["sha256"] == expected_sha

    # Capture the exact bytes of the first line to prove append-only afterwards.
    first_line_bytes = (json.dumps(record) + "\n").encode("utf-8")
    raw_after_first = journal_path.read_bytes()
    assert raw_after_first == first_line_bytes

    # A second append (a different transition) must not rewrite the first line.
    second_artifact = tmp_path / "analysis.md"
    second_artifact.write_bytes(b"# analysis\n")
    rc2 = journal.main(
        [
            "append",
            "--state",
            "ANALYZE",
            "--iter",
            "1",
            "--artifact",
            str(second_artifact),
            "--journal",
            str(journal_path),
        ]
    )
    assert rc2 == 0

    raw_after_second = journal_path.read_bytes()
    # The first line's bytes are a prefix of the file after the second append.
    assert raw_after_second.startswith(first_line_bytes)
    lines_after_second = raw_after_second.decode("utf-8").splitlines()
    assert len(lines_after_second) == 2
    assert lines_after_second[0] == json.dumps(record)
