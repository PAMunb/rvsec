"""Tests for consolidate_cal.py (CONSOLIDATE) and verify_iteration.py (VERIFY).

The fixture builds a synthetic 2-arm × 2-APK results tree under ``tmp_path`` that
deliberately embeds the three failure modes the scaffold must survive:

  * a DUPLICATE identity — two ``tasks.json`` records for the same
    ``(apk, tool, variant, rep, timeout)`` after a "resume", the second one zeroed. It must
    be counted exactly once (and the zeroed copy must not drag the rep average down).
  * a MISSING-ARM APK — ``app.bravo`` runs in ``aperv:cal_a1`` but never in ``aperv:cal_a2``,
    so it must be excluded from the paired set with the missing arm named.
  * a DIVERGENT count — after consolidation, one ``per_apk_paired.csv`` cell is tampered so
    it disagrees with the raw-logcat re-derivation; VERIFY (independent) must catch it and
    quarantine, citing the identity and both values.
"""

from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

import consolidate_cal
import verify_iteration

# --- arms + apks under test ------------------------------------------------------------
ARM_A = ("aperv", "cal_a1")  # label "aperv:cal_a1"
ARM_B = ("aperv", "cal_a2")  # label "aperv:cal_a2"
TIMEOUT = 300

# A config manifest both arms echo on their [APE-LLM-CONFIG] trace line, matched by the
# fixture manifest's expected_config_ack so the config gate passes.
_CONFIG = {
    "model": "Qwen/Qwen3-VL-4B-Instruct",
    "temperature": "0",
    "top_p": "0.6",
    "top_k": "50",
    "timeout_ms": "15000",
    "prompt_variant": "v13",
    "llm_percentage": "0.7",
    "on_new_state": "true",
    "on_stagnation": "true",
    "url": "http://10.0.2.2:30000/v1",
}


def _config_line() -> str:
    kv = " ".join(f"{k}={v}" for k, v in _CONFIG.items())
    return f"[APE] [APE-LLM-CONFIG] {kv} max_tokens=1024 stagnation_threshold=200"


def _logcat_text(n_mop: int, n_cov: int) -> str:
    """A raw logcat with ``n_mop`` RVSEC MOP lines and ``n_cov`` distinct RVSEC-COV lines."""
    lines = ["01-01 00:00:00.000  1000  1000 I System: boot"]
    for i in range(n_mop):
        lines.append(
            f"01-01 00:00:0{i}.100  1000  1000 I RVSEC: CipherSpec,com.x.Foo,doIt{i},misuse"
        )
    for i in range(n_cov):
        lines.append(
            f"01-01 00:00:0{i}.200  1000  1000 I RVSEC-COV: com.x.Foo->method{i}()"
        )
    return "\n".join(lines) + "\n"


def _trace_text(time_ms: int = 1500, matched: int = 3, no_match: int = 1) -> str:
    return (
        "\n".join(
            [
                _config_line(),
                "[APE-LLM-TEL] step=1 mode=new-state action=click result=matched "
                "tokens_in=100 tokens_out=10 time_ms=500",
                "[APE-LLM-TEL] step=2 mode=stagnation action=click result=no_match "
                "reason=degenerate tokens_in=100 tokens_out=10 time_ms=500",
                f"[APE-RV] LLM Summary calls={matched + no_match} tokens_in=1000 tokens_out=100 "
                f"time_ms={time_ms} matched={matched} llm_tap=0 no_match={no_match} timeout=0 "
                "http_error=0 conn_error=0 parse_error=0 image_error=0 internal_error=0 "
                "screenshot_failed=0 breaker_trips=0",
            ]
        )
        + "\n"
    )


def _task_record(
    apk,
    tool,
    variant,
    rep,
    cov_method,
    cov_act,
    cov_mop,
    total_errors,
    crashes,
    state="COMPLETED",
):
    return {
        "task_id": f"{apk}-{tool}-{variant}-{rep}",
        "config": {
            "apk_name": apk,
            "repetition": rep,
            "timeout": TIMEOUT,
            "tool_config": {"name": tool, "variant": variant},
        },
        "result": {
            "state": state,
            "coverage_metrics": {
                "method_coverage": cov_method,
                "activities_coverage": cov_act,
                "methods_mop_reachable_coverage": cov_mop,
                "total_errors": total_errors,
            },
            "detected_errors_count": crashes,
        },
    }


def _write_container(iter_dir: Path, name: str, tasks, files):
    """Write one container's tasks.json + its co-located logcat/trace files.

    ``files`` maps ``(apk, rep, toolfrag)`` -> ``(n_mop, n_cov, trace_time_ms_or_None)``.
    """
    base = iter_dir / "results" / name / name
    base.mkdir(parents=True, exist_ok=True)
    (base / "tasks.json").write_text(json.dumps({"tasks": tasks}))
    for (apk, rep, frag), (n_mop, n_cov, trace_ms) in files.items():
        apk_dir = base / apk
        apk_dir.mkdir(exist_ok=True)
        stem = f"{apk}__{rep}__{TIMEOUT}__{frag}"
        (apk_dir / f"{stem}.logcat").write_text(_logcat_text(n_mop, n_cov))
        if trace_ms is not None:
            (apk_dir / f"{stem}.trace").write_text(_trace_text(time_ms=trace_ms))


def _write_manifest(iter_dir: Path):
    """A minimal manifest whose arms + expected_config_ack match the fixture traces."""
    expected = {k: v for k, v in _CONFIG.items()}
    # Normalise numeric-looking strings to the JSON-native types the real manifest stores.
    expected["temperature"] = 0
    expected["top_p"] = 0.6
    expected["top_k"] = 50
    expected["timeout_ms"] = 15000
    expected["llm_percentage"] = 0.7
    expected["on_new_state"] = True
    expected["on_stagnation"] = True
    manifest = {
        "iteration": 1,
        "phase": "calfix",
        "arms": [
            {
                "role": "A1",
                "tool": "aperv",
                "variant": "cal_a1",
                "rv_tools_token": "aperv:cal_a1",
                "expected_config_ack": expected,
            },
            {
                "role": "A2",
                "tool": "aperv",
                "variant": "cal_a2",
                "rv_tools_token": "aperv:cal_a2",
                "expected_config_ack": expected,
            },
        ],
    }
    (iter_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def _build_fixture(tmp_path: Path) -> Path:
    """Assemble the 2-arm × 2-APK iteration tree; return the iteration dir."""
    iter_dir = tmp_path / "iter1"
    iter_dir.mkdir()
    _write_manifest(iter_dir)

    # Container 00: arm A (cal_a1) — app.alpha (2 reps + a zeroed resume duplicate of rep 1)
    # and app.bravo (present ONLY in arm A -> missing-arm case).
    c00_tasks = [
        _task_record("app.alpha", "aperv", "cal_a1", 1, 50.0, 40.0, 30.0, 3, 0),
        _task_record("app.alpha", "aperv", "cal_a1", 2, 60.0, 40.0, 30.0, 3, 0),
        # resume duplicate of (app.alpha, aperv, cal_a1, 1): zeroed, must be discarded.
        _task_record("app.alpha", "aperv", "cal_a1", 1, 0.0, 0.0, 0.0, 0, 0),
        _task_record("app.bravo", "aperv", "cal_a1", 1, 70.0, 50.0, 20.0, 2, 0),
    ]
    c00_files = {
        ("app.alpha", 1, "aperv:cal_a1"): (3, 5, 1500),
        ("app.alpha", 2, "aperv:cal_a1"): (3, 5, 1500),
        ("app.bravo", 1, "aperv:cal_a1"): (2, 4, 1500),
    }
    _write_container(iter_dir, "calfix_00", c00_tasks, c00_files)

    # Container 01: arm B (cal_a2) — app.alpha only (app.bravo intentionally absent).
    c01_tasks = [
        _task_record("app.alpha", "aperv", "cal_a2", 1, 55.0, 45.0, 25.0, 2, 0),
    ]
    c01_files = {
        ("app.alpha", 1, "aperv:cal_a2"): (2, 6, 1500),
    }
    _write_container(iter_dir, "calfix_01", c01_tasks, c01_files)

    return iter_dir


def _read_paired(iter_dir: Path):
    with open(iter_dir / "per_apk_paired.csv", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)
    return header, rows


# --- tests -----------------------------------------------------------------------------
def test_consolidate_dedup_and_pairing(tmp_path):
    iter_dir = _build_fixture(tmp_path)
    consolidate_cal.consolidate(iter_dir)

    header, rows = _read_paired(iter_dir)
    # One row per APK.
    apks = [r[0] for r in rows]
    assert apks == ["app.alpha", "app.bravo"]

    # Both arm column groups present.
    assert "aperv:cal_a1__cov_method" in header
    assert "aperv:cal_a2__cov_method" in header

    hidx = {name: i for i, name in enumerate(header)}
    alpha = rows[apks.index("app.alpha")]

    # Duplicate identity counted once + reps averaged: (50 + 60) / 2 = 55, NOT
    # (50 + 60 + 0) / 3 = 36.67 (which is what a failure to dedup would give).
    assert float(alpha[hidx["aperv:cal_a1__cov_method"]]) == 55.0
    # mop_total is averaged from the raw logcats (rep1=3, rep2=3 -> 3.0).
    assert float(alpha[hidx["aperv:cal_a1__mop_total"]]) == 3.0
    # arm B cell for app.alpha is filled from its own single rep.
    assert float(alpha[hidx["aperv:cal_a2__cov_method"]]) == 55.0

    # app.bravo has arm A filled and arm B empty (missing-arm gap).
    bravo = rows[apks.index("app.bravo")]
    assert float(bravo[hidx["aperv:cal_a1__cov_method"]]) == 70.0
    assert bravo[hidx["aperv:cal_a2__cov_method"]] == ""

    # tel_proxies: one row per arm×apk×rep with a trace. arm A: alpha rep1, alpha rep2,
    # bravo rep1 (3); arm B: alpha rep1 (1) -> 4 rows.
    with open(iter_dir / "tel_proxies.csv", newline="") as fh:
        tel = list(csv.DictReader(fh))
    assert len(tel) == 4
    a_alpha = [r for r in tel if r["arm"] == "aperv:cal_a1" and r["apk"] == "app.alpha"]
    assert len(a_alpha) == 2
    assert all(int(r["matched"]) == 3 for r in a_alpha)
    assert all(int(r["no_match_degenerate"]) == 1 for r in a_alpha)
    assert all(int(r["mode_new_state"]) == 1 for r in a_alpha)


def test_verify_gates_on_fixtures(tmp_path):
    iter_dir = _build_fixture(tmp_path)
    consolidate_cal.consolidate(iter_dir)

    # Tamper one cell so it disagrees with the raw-logcat re-derivation: app.alpha's arm-A
    # mop_total is genuinely 3.0 (both reps), overwrite it with 99.0.
    header, rows = _read_paired(iter_dir)
    hidx = {name: i for i, name in enumerate(header)}
    for row in rows:
        if row[0] == "app.alpha":
            row[hidx["aperv:cal_a1__mop_total"]] = "99.0"
    with open(iter_dir / "per_apk_paired.csv", "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)

    result = verify_iteration.verify(iter_dir, sample_size=10, seed=42)

    # Divergence -> quarantine, citing the identity and both values.
    assert result["verdict"] == "quarantine"
    divs = [d for d in result["divergences"] if d["metric"] == "mop_total"]
    assert divs, "expected a mop_total divergence"
    d = divs[0]
    assert d["apk"] == "app.alpha" and d["arm"] == "aperv:cal_a1"
    assert _num(d["csv_value"]) == 99.0 and d["rederived"] == 3.0
    # The offending identity is named.
    assert any("app.alpha" in i and "cal_a1" in i for i in d["identities"])

    # Missing-arm APK excluded from the paired set with the missing arm named.
    assert "app.bravo" not in result["paired_apks"]
    assert "app.alpha" in result["paired_apks"]
    excl = {e["apk"]: e["missing_arms"] for e in result["exclusions"]}
    assert "app.bravo" in excl
    assert "aperv:cal_a2" in excl["app.bravo"]

    # The written report cites the identity and both divergent values, and names the
    # excluded arm.
    report = verify_iteration.render_report(iter_dir, result)
    assert "app.alpha" in report
    assert "99.0" in report and "3.0" in report
    assert "app.bravo" in report and "aperv:cal_a2" in report


def test_verify_admissible_without_tamper(tmp_path):
    # Sanity: an untampered consolidation is admissible (only exclusions/notes, no gate fail).
    iter_dir = _build_fixture(tmp_path)
    consolidate_cal.consolidate(iter_dir)
    result = verify_iteration.verify(iter_dir, sample_size=10, seed=42)
    assert result["verdict"] == "admissible", result["quarantine_reasons"]
    assert not result["divergences"]
    assert not result["config_findings"]


def test_verify_import_independence():
    # INV-CAL-04: the verifier shares no code with the producers. Parse its AST and assert
    # no import (either form) names the forbidden modules.
    src = Path(verify_iteration.__file__).read_text()
    tree = ast.parse(src)
    forbidden = {"consolidate_cal", "consolidate_compare", "analyze_cmpv2_llm"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert forbidden.isdisjoint(
        imported
    ), f"verifier imports forbidden module(s): {forbidden & imported}"


def _num(value):
    return float(value)
