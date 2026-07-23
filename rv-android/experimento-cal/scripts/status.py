#!/usr/bin/env python3
"""Campaign status — the "where are we / what runs next?" view of the calibration loop.

The calibration loop is agent-driven with no daemon (design decision 9): a session walks
CONFIG-GEN → PRE-FLIGHT → SMOKE → RUN+MONITOR → CONSOLIDATE → VERIFY → ANALYZE → DECIDE,
gated by the four human gates G1–G4. Without a status view, every session would have to
reconstruct the campaign position by hand. This script answers it deterministically.

It DERIVES the position (INV-CAL-14) from three sources of truth and never a hand-maintained
checklist (a hand-kept status silently drifts from the artifacts it claims to describe):

  1. `calibracao/journal.jsonl`  — the append-only transition log (one record per state).
  2. `experimento-cal/iterN/`     — the artifacts each state produces (manifest.json,
                                    per_apk_paired.csv, verification_report.md, analysis.md,
                                    decision.md, results/).
  3. `phases/<phase>.json`        — read indirectly via each iteration's manifest.

For each iteration it renders the eight-state loop with every state marked done / current /
pending, flags any journal↔artifact inconsistency (a state journaled without its artifact, or
an artifact present without a journal record), names the pending human gate, and prints the
next action (the script to run). A cross-iteration summary lists each iteration's phase and
DECIDE verdict. The script is READ-ONLY: it opens no container, touches no emulator, writes
nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# scripts/ -> experimento-cal/ -> rv-android/ (repo root).
_SCRIPTS_DIR = Path(__file__).resolve().parent
EXPERIMENT_ROOT = _SCRIPTS_DIR.parent
REPO_ROOT = EXPERIMENT_ROOT.parent
DEFAULT_JOURNAL = REPO_ROOT / "calibracao" / "journal.jsonl"

# The canonical eight-state loop, in order.
STATES: List[str] = [
    "CONFIG-GEN",
    "PRE-FLIGHT",
    "SMOKE",
    "RUN+MONITOR",
    "CONSOLIDATE",
    "VERIFY",
    "ANALYZE",
    "DECIDE",
]

# The single artifact whose presence corroborates a state's journal record. States absent
# from this map either produce no single file (PRE-FLIGHT, SMOKE — journal-only) or are
# handled specially (RUN+MONITOR → the results/ tree).
STATE_ARTIFACT: Dict[str, str] = {
    "CONFIG-GEN": "manifest.json",
    "CONSOLIDATE": "per_apk_paired.csv",
    "VERIFY": "verification_report.md",
    "ANALYZE": "analysis.md",
    "DECIDE": "decision.md",
}

# The command a session runs to advance FROM a just-completed state. Keyed by the CURRENT
# (first not-done) state — i.e. "you are at X, do this next".
NEXT_ACTION: Dict[str, str] = {
    "CONFIG-GEN": "gen_iteration.py --phase <phase> --iter <N>",
    "PRE-FLIGHT": "preflight.py --iter-dir <iter>",
    "SMOKE": "G3 gate → compose up (smoke), then smoke_check.py --iter-dir <iter>",
    "RUN+MONITOR": "G3 launch → compose up (run), then monitor.sh <iter>",
    "CONSOLIDATE": "consolidate_cal.py --iter-dir <iter>",
    "VERIFY": "verify_iteration.py --iter-dir <iter>",
    "ANALYZE": "analyze_iteration.py --iter-dir <iter>",
    "DECIDE": "instantiate templates/decision.md as <iter>/decision.md",
}

# Journal state strings are agent-written free text; fold common spellings onto the canonical
# names so a "RUN" or "MONITOR" record still lands on RUN+MONITOR.
_STATE_ALIASES: Dict[str, str] = {
    "CONFIG-GEN": "CONFIG-GEN",
    "CONFIGGEN": "CONFIG-GEN",
    "CONFIG": "CONFIG-GEN",
    "GEN": "CONFIG-GEN",
    "PRE-FLIGHT": "PRE-FLIGHT",
    "PREFLIGHT": "PRE-FLIGHT",
    "SMOKE": "SMOKE",
    "RUN+MONITOR": "RUN+MONITOR",
    "RUN": "RUN+MONITOR",
    "MONITOR": "RUN+MONITOR",
    "RUN-MONITOR": "RUN+MONITOR",
    "CONSOLIDATE": "CONSOLIDATE",
    "VERIFY": "VERIFY",
    "ANALYZE": "ANALYZE",
    "DECIDE": "DECIDE",
}


def normalize_state(raw: str) -> Optional[str]:
    """Fold a journal state string onto a canonical STATES name, or None if unknown."""
    key = re.sub(r"\s+", "", raw.strip().upper())
    return _STATE_ALIASES.get(key)


def load_journal(journal_path: Path) -> Dict[int, Set[str]]:
    """Read the journal into {iteration -> set of canonical states recorded}.

    Malformed lines are skipped (the journal is append-only and may be mid-write); the status
    view degrades gracefully rather than crashing on a partial last line.
    """
    per_iter: Dict[int, Set[str]] = {}
    if not journal_path.exists():
        return per_iter
    for line in journal_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            it = int(rec["iter"])
            state = normalize_state(str(rec["state"]))
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            continue
        if state is not None:
            per_iter.setdefault(it, set()).add(state)
    return per_iter


def _results_has_logcats(iter_dir: Path) -> bool:
    """True when the results tree holds at least one non-empty logcat (RUN+MONITOR evidence)."""
    results = iter_dir / "results"
    if not results.is_dir():
        return False
    return any(p.stat().st_size > 0 for p in results.rglob("*.logcat"))


def artifact_present(state: str, iter_dir: Path) -> Optional[bool]:
    """Whether a state's corroborating artifact exists. None if the state produces no file
    (PRE-FLIGHT, SMOKE) — those are journal-only."""
    if state == "RUN+MONITOR":
        return _results_has_logcats(iter_dir)
    name = STATE_ARTIFACT.get(state)
    if name is None:
        return None
    return (iter_dir / name).exists()


def _phase_of(iter_dir: Path) -> Optional[str]:
    """The phase name from the iteration's manifest (None if not generated yet)."""
    manifest = iter_dir / "manifest.json"
    if not manifest.exists():
        return None
    try:
        return json.loads(manifest.read_text()).get("phase")
    except (json.JSONDecodeError, OSError):
        return None


def _decision_summary(iter_dir: Path) -> str:
    """Best-effort DECIDE verdict + promoted arms from decision.md; 'pending' if absent, and
    'template (unfilled)' if the file is still the raw template with <VERDICT> placeholders.
    """
    decision = iter_dir / "decision.md"
    if not decision.exists():
        return "pending"
    text = decision.read_text()
    if "<VERDICT>" in text or "<ARMS_PROMOTED>" in text:
        return "template (unfilled)"
    verdict = "?"
    m = re.search(r"\*\*Verdict\*\*:\s*([^\n<]+)", text)
    if m:
        verdict = m.group(1).strip()
    promoted = ""
    p = re.search(r"Promoted arms\s*\n+\s*-\s*\*\*([^*]+)\*\*", text)
    if p:
        promoted = f" — promoted: {p.group(1).strip()}"
    return f"{verdict}{promoted}"


def evaluate_iteration(
    iteration: int, iter_dir: Path, journaled: Set[str]
) -> Dict[str, Any]:
    """Derive per-state done/current/pending + inconsistencies for one iteration.

    `done` is true when the state was journaled OR its corroborating artifact is present —
    robust to imperfect journaling. A disagreement between the two (journaled without the
    artifact, or artifact without a journal record) is recorded as an inconsistency so the
    agent can reconcile it (INV-CAL-14: the journal + filesystem are the source of truth).
    """
    rows = []
    inconsistencies: List[str] = []
    current: Optional[str] = None
    for state in STATES:
        j = state in journaled
        a = artifact_present(state, iter_dir)  # None when the state has no artifact
        done = j or bool(a)
        if a is not None:
            if j and not a:
                inconsistencies.append(f"{state}: journaled but artifact missing")
            elif a and not j:
                inconsistencies.append(f"{state}: artifact present but not journaled")
        if not done and current is None:
            current = state
        rows.append({"state": state, "done": done, "journaled": j, "artifact": a})

    complete = current is None
    phase = _phase_of(iter_dir)
    gate = _pending_gate(current, phase)
    next_action = (
        "iteration complete → start the next iteration (gen_iteration.py --iter N+1) "
        "or, in a confirmation phase, record the G4 final verdict"
        if complete
        else NEXT_ACTION[current]
    )
    return {
        "iteration": iteration,
        "phase": phase,
        "rows": rows,
        "current": current,
        "complete": complete,
        "pending_gate": gate,
        "next_action": next_action,
        "inconsistencies": inconsistencies,
        "decision": _decision_summary(iter_dir),
    }


def _pending_gate(current: Optional[str], phase: Optional[str]) -> Optional[str]:
    """The human gate blocking the current state, if any. G3 gates every launch (smoke/run);
    G4 gates the final DECIDE of the confirmation phase (calc)."""
    if current in ("SMOKE", "RUN+MONITOR"):
        return "G3 (launch approval)"
    if current == "DECIDE" and phase == "calc":
        return "G4 (final verdict)"
    return None


def discover_iterations(iter_root: Path) -> List[int]:
    """Sorted iteration numbers from iterN/ directory names under the experiment root."""
    nums = []
    for p in iter_root.glob("iter*"):
        if p.is_dir():
            m = re.fullmatch(r"iter(\d+)", p.name)
            if m:
                nums.append(int(m.group(1)))
    return sorted(nums)


_MARK = {True: "✅", False: "  "}


def render(report: List[Dict[str, Any]], iter_root: Path) -> str:
    """Render the campaign status report as plain text."""
    lines: List[str] = []
    lines.append("=" * 72)
    lines.append("CALIBRATION CAMPAIGN STATUS")
    lines.append("=" * 72)
    if not report:
        lines.append("")
        lines.append("No iterations generated yet.")
        lines.append(f"  iter root: {iter_root}")
        lines.append(
            "  Next action: gen_iteration.py --phase phases/cala.json --iter 0"
        )
        lines.append("")
        return "\n".join(lines)

    latest = report[-1]
    lines.append(
        f"Iterations: {', '.join('iter' + str(r['iteration']) for r in report)}  "
        f"| current: iter{latest['iteration']} (phase {latest['phase'] or '?'})"
    )
    lines.append("")

    # Detail for the current (latest) iteration.
    lines.append(f"--- iter{latest['iteration']} — loop progress ---")
    for row in latest["rows"]:
        marker = _MARK[row["done"]]
        cur = "  ← current" if row["state"] == latest["current"] else ""
        # Annotate only the two inconsistency cases — a plainly-pending state needs no note.
        note = ""
        if row["journaled"] and row["artifact"] is False:
            note = "  ⚠ journaled, artifact missing"
        elif row["artifact"] is True and not row["journaled"]:
            note = "  ⚠ artifact present, not journaled"
        lines.append(f"  [{marker}] {row['state']:<12}{cur}{note}")
    if latest["complete"]:
        lines.append("  → all eight states done for this iteration")
    lines.append("")
    if latest["pending_gate"]:
        lines.append(f"Pending human gate: {latest['pending_gate']}")
    lines.append(f"Next action: {latest['next_action']}")
    if latest["inconsistencies"]:
        lines.append("")
        lines.append("⚠ Inconsistencies (journal ↔ artifacts):")
        for msg in latest["inconsistencies"]:
            lines.append(f"    - {msg}")
    lines.append("")

    # Cross-iteration summary.
    lines.append("--- cross-iteration summary ---")
    lines.append(f"  {'iter':<6}{'phase':<8}{'progress':<12}{'DECIDE verdict'}")
    for r in report:
        done_n = sum(1 for row in r["rows"] if row["done"])
        prog = f"{done_n}/{len(STATES)}"
        lines.append(
            f"  {('iter' + str(r['iteration'])):<6}{(r['phase'] or '?'):<8}"
            f"{prog:<12}{r['decision']}"
        )
    lines.append("")
    return "\n".join(lines)


def build_report(iter_root: Path, journal_path: Path) -> List[Dict[str, Any]]:
    """Evaluate every discovered iteration against the journal + its artifacts."""
    journal = load_journal(journal_path)
    report = []
    for n in discover_iterations(iter_root):
        report.append(
            evaluate_iteration(n, iter_root / f"iter{n}", journal.get(n, set()))
        )
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--iter-root",
        default=str(EXPERIMENT_ROOT),
        help="root containing iterN/ dirs (default: experimento-cal/)",
    )
    parser.add_argument(
        "--journal",
        default=str(DEFAULT_JOURNAL),
        help="transition journal (default: calibracao/journal.jsonl)",
    )
    args = parser.parse_args(argv)

    report = build_report(Path(args.iter_root), Path(args.journal))
    sys.stdout.write(render(report, Path(args.iter_root)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
