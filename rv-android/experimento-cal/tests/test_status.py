"""Unit tests for status.py — the derived campaign-status view."""

from __future__ import annotations

import json

import status


def _journal(tmp_path, records):
    """Write a journal.jsonl from a list of (iter, state) pairs; return its path."""
    p = tmp_path / "journal.jsonl"
    with open(p, "w") as fh:
        for it, state in records:
            fh.write(
                json.dumps(
                    {
                        "ts": "2026-07-23T00:00:00Z",
                        "iter": it,
                        "state": state,
                        "artifact": "x",
                        "sha256": "0" * 64,
                    }
                )
                + "\n"
            )
    return p


def _iter_dir(tmp_path, n, files=(), phase="cala"):
    """Build an iterN/ dir with the given artifact files; manifest carries the phase."""
    d = tmp_path / f"iter{n}"
    d.mkdir()
    if "manifest.json" not in files:
        # Always give it a manifest so _phase_of resolves (CONFIG-GEN happened).
        files = tuple(files) + ("manifest.json",)
    for f in files:
        if f == "manifest.json":
            (d / f).write_text(json.dumps({"phase": phase}))
        else:
            (d / f).write_text("x")
    return d


def test_current_state_and_next_action(tmp_path):
    # iter1: CONFIG-GEN + PRE-FLIGHT journaled, manifest present, no results yet.
    journal = _journal(tmp_path, [(1, "CONFIG-GEN"), (1, "PRE-FLIGHT")])
    _iter_dir(tmp_path, 1, files=("manifest.json",))
    report = status.build_report(tmp_path, journal)
    assert len(report) == 1
    it = report[0]
    rows = {r["state"]: r for r in it["rows"]}
    assert rows["CONFIG-GEN"]["done"] is True
    assert rows["PRE-FLIGHT"]["done"] is True
    assert rows["SMOKE"]["done"] is False
    # SMOKE is the current/next state; the launch gate G3 is pending.
    assert it["current"] == "SMOKE"
    assert it["pending_gate"] == "G3 (launch approval)"
    assert "smoke_check.py" in it["next_action"]


def test_journal_artifact_inconsistency_flagged(tmp_path):
    # VERIFY is journaled but verification_report.md is absent -> inconsistency.
    journal = _journal(
        tmp_path,
        [
            (1, "CONFIG-GEN"),
            (1, "PRE-FLIGHT"),
            (1, "SMOKE"),
            (1, "RUN+MONITOR"),
            (1, "CONSOLIDATE"),
            (1, "VERIFY"),
        ],
    )
    # per_apk_paired.csv present (CONSOLIDATE ok) but no verification_report.md.
    _iter_dir(tmp_path, 1, files=("manifest.json", "per_apk_paired.csv"))
    report = status.build_report(tmp_path, journal)
    it = report[0]
    assert any(
        "VERIFY: journaled but artifact missing" in m for m in it["inconsistencies"]
    )


def test_artifact_without_journal_flagged(tmp_path):
    # decision.md present but never journaled -> "artifact present but not journaled".
    journal = _journal(tmp_path, [(1, "CONFIG-GEN")])
    _iter_dir(tmp_path, 1, files=("manifest.json", "decision.md"))
    report = status.build_report(tmp_path, journal)
    it = report[0]
    assert any(
        "DECIDE: artifact present but not journaled" in m for m in it["inconsistencies"]
    )
    # DECIDE counts as done (artifact present) despite the missing journal record.
    rows = {r["state"]: r for r in it["rows"]}
    assert rows["DECIDE"]["done"] is True


def test_complete_iteration_next_action(tmp_path):
    journal = _journal(tmp_path, [(1, s) for s in status.STATES])
    _iter_dir(
        tmp_path,
        1,
        files=(
            "manifest.json",
            "per_apk_paired.csv",
            "verification_report.md",
            "analysis.md",
            "decision.md",
        ),
    )
    # Give it a non-empty logcat so RUN+MONITOR corroborates.
    res = tmp_path / "iter1" / "results" / "cala_00" / "cala_00" / "app_1"
    res.mkdir(parents=True)
    (res / "app_1__0__300__aperv:cal_a1.logcat").write_text("RVSEC-COV: x\n")
    report = status.build_report(tmp_path, journal)
    it = report[0]
    assert it["complete"] is True
    assert it["current"] is None
    assert "next iteration" in it["next_action"] or "gen_iteration" in it["next_action"]


def test_no_iterations_message(tmp_path):
    # Empty root + missing journal -> a friendly "nothing yet" report, not a crash.
    report = status.build_report(tmp_path, tmp_path / "journal.jsonl")
    assert report == []
    text = status.render(report, tmp_path)
    assert "No iterations generated yet" in text
    assert "gen_iteration.py" in text


def test_cross_iteration_summary_and_g4(tmp_path):
    # Two iterations; iter2 is a confirmation phase (calc) sitting at DECIDE -> G4.
    journal = _journal(
        tmp_path,
        [(1, s) for s in status.STATES]
        + [
            (2, "CONFIG-GEN"),
            (2, "PRE-FLIGHT"),
            (2, "SMOKE"),
            (2, "RUN+MONITOR"),
            (2, "CONSOLIDATE"),
            (2, "VERIFY"),
            (2, "ANALYZE"),
        ],
    )
    _iter_dir(
        tmp_path,
        1,
        files=(
            "manifest.json",
            "per_apk_paired.csv",
            "verification_report.md",
            "analysis.md",
            "decision.md",
        ),
    )
    r1 = tmp_path / "iter1" / "results" / "c" / "c" / "a"
    r1.mkdir(parents=True)
    (r1 / "a__0__300__aperv:cal_a1.logcat").write_text("x\n")
    _iter_dir(
        tmp_path,
        2,
        files=(
            "manifest.json",
            "per_apk_paired.csv",
            "verification_report.md",
            "analysis.md",
        ),
        phase="calc",
    )
    r2 = tmp_path / "iter2" / "results" / "c" / "c" / "a"
    r2.mkdir(parents=True)
    (r2 / "a__0__300__aperv:cal_a1.logcat").write_text("x\n")
    report = status.build_report(tmp_path, journal)
    assert [r["iteration"] for r in report] == [1, 2]
    latest = report[-1]
    assert latest["current"] == "DECIDE"
    assert latest["pending_gate"] == "G4 (final verdict)"
    text = status.render(report, tmp_path)
    assert "cross-iteration summary" in text
    assert "calc" in text
