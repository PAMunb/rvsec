"""
ADR-6 sentinel — parser-side behavior.

Verify that:
  (a) A JSON file ending with ``"complete": true`` parses to
      ``StaticAnalysisData.complete is True``.
  (b) A JSON file missing the key (legacy gh57 / pre-sentinel writer
      output) parses to ``complete is False`` without raising.
  (c) A truncated JSON file recovered via the
      ``_recover_truncated_json`` bracket fix parses to
      ``complete is False`` (the sentinel was never reached on disk).
"""

import json
from pathlib import Path

import pytest

from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser


def _minimal_json() -> dict:
    """Smallest valid analysis report the parser can ingest."""
    return {
        "package": "com.app",
        "mainActivity": "com.app.MainActivity",
        "reachability": [],
        "windows": [],
        "transitions": [],
        "components": {
            "activities": [],
            "receivers": [],
            "services": [],
            "providers": [],
        },
    }


def test_complete_true_propagates_to_static_analysis_data(tmp_path: Path) -> None:
    payload = _minimal_json()
    payload["complete"] = True
    p = tmp_path / "with_sentinel.json"
    p.write_text(json.dumps(payload))

    data = StaticAnalysisParser().parse_file(str(p))
    assert data.complete is True


def test_complete_false_when_explicitly_false(tmp_path: Path) -> None:
    payload = _minimal_json()
    payload["complete"] = False
    p = tmp_path / "incomplete_sentinel.json"
    p.write_text(json.dumps(payload))

    data = StaticAnalysisParser().parse_file(str(p))
    assert data.complete is False


def test_legacy_gh57_json_without_sentinel_parses_with_complete_false(
    tmp_path: Path,
) -> None:
    # The 78.8% complete-but-empty bucket from the gh57 sweep (see
    # Phase 1 task-zero verdict): JSON is fully written but the writer
    # did not yet emit the sentinel (pre-C1e binary).
    payload = _minimal_json()
    # No "complete" key.
    p = tmp_path / "legacy.json"
    p.write_text(json.dumps(payload))

    data = StaticAnalysisParser().parse_file(str(p))
    assert data.complete is False, (
        "Pre-sentinel JSONs MUST parse to complete=False — the sentinel's "
        "ABSENCE is exactly the signal consumers use to exclude the sample."
    )


def test_truncated_recovery_yields_complete_false(tmp_path: Path) -> None:
    # A WTG-timeout produces a file that ends mid-array. The parser's
    # _recover_truncated_json closes the bracket and reparses; the recovered
    # JSON cannot contain "complete":true because the sentinel is emitted
    # AFTER all sections by JsonReportWriter.
    raw = """\
{
  "package": "com.app",
  "mainActivity": "com.app.MainActivity",
  "reachability": [],
  "windows": [{"id": 1, "name": "MainActivity", "type": "ACTIVITY", "isMain": true, "widgets": []}],
  "transitions": ["""
    p = tmp_path / "truncated.json"
    p.write_text(raw)

    data = StaticAnalysisParser().parse_file(str(p))
    # The load-bearing assertion: a truncation-recovered JSON CANNOT
    # contain the sentinel, because JsonReportWriter emits the sentinel
    # AFTER all sections and only on the success path. Whether the
    # recovered partial windows section yields 0 or 1 windows depends on
    # exactly where the bracket-recovery truncation cut — the sentinel
    # contract holds either way.
    assert data.complete is False
