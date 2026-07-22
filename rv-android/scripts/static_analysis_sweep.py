#!/usr/bin/env python3
"""Static-analysis sweep across an APK directory with resume + cross-validation.

Validates the gh51-gator-soot-upgrade change (Soot 4.7.1 + defensive options +
write-first JSON) by running the unified GATOR analysis client on a directory
of APKs in parallel, classifying each by completeness of the produced JSON,
and producing a per-APK + aggregated CSV report.

Design: see docs/20260428_executar_analise_estatica.md

Usage:
    python scripts/static_analysis_sweep.py \\
        --apks-dir /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs \\
        --output ./out/sweep_jca400 \\
        --planilha /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/PLANILHA.csv \\
        --timeout 900 --workers 8

The script is one-shot and meant to be deleted after gh51 validation completes.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import shutil
import signal
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Status taxonomy
STATUS_COMPLETE = "complete"
STATUS_PARTIAL_NO_COMPONENTS = "partial_no_components"
STATUS_PARTIAL_NO_TRANSITIONS = "partial_no_transitions"
STATUS_PARTIAL_REACHABILITY_ONLY = "partial_reachability_only"
STATUS_PARTIAL_EMPTY_REACHABILITY = "partial_empty_reachability"
STATUS_UNPARSEABLE = "unparseable"
STATUS_FAILED_NO_JSON = "failed_no_json"
STATUS_FAILED_TIMEOUT_NO_JSON = "failed_timeout_no_json"
STATUS_FAILED_EXCEPTION = "failed_exception"
STATUS_SKIPPED_NO_JAVA_CODE = "skipped_no_java_code"
STATUS_NOT_STARTED = "not_started"

# Status reprocessed by default when sweep is rerun with a higher timeout.
# complete/failed_no_json/failed_exception/skipped_no_java_code are NOT in this set:
#   - complete: nothing to gain
#   - failed_no_json/failed_exception: non-temporal crash; raising timeout won't help
#   - skipped_no_java_code: APK genuinely has no Java bytecode
DEFAULT_RETRY_STATUSES: Set[str] = {
    STATUS_PARTIAL_NO_COMPONENTS,
    STATUS_PARTIAL_NO_TRANSITIONS,
    STATUS_PARTIAL_REACHABILITY_ONLY,
    STATUS_PARTIAL_EMPTY_REACHABILITY,
    STATUS_UNPARSEABLE,
    STATUS_FAILED_TIMEOUT_NO_JSON,
}

CSV_COLUMNS = [
    "apk_name", "code_package", "status",
    "timeout_used_seconds", "analysis_seconds",
    "sections_present",
    "methods_total", "methods_reachable",
    "methods_reach_mop", "methods_directly_reach_mop",
    "windows_count", "transitions_count", "components_count",
    "gator_reaches_target", "gator_directly_reaches_target",
    "androguard_reaches_target", "androguard_directly_reaches_target",
    "androguard_methods_reaches_target", "androguard_methods_directly_reaches_target",
    "agreement_reaches_target", "agreement_directly_reaches_target",
    "json_size_bytes", "last_pass_id", "last_run_finished", "error_message",
]


@dataclass
class AndroguardEntry:
    """Subset of PLANILHA.csv columns used for pre-filter and cross-validation."""

    dex_count: int = 0
    reaches_target: Optional[bool] = None
    directly_reaches_target: Optional[bool] = None
    methods_reaches_target: int = 0
    methods_directly_reaches_target: int = 0


@dataclass
class ProgressMetrics:
    """Metrics derived from parsing the GATOR analysis JSON."""

    sections_present: List[str] = field(default_factory=list)
    methods_total: int = 0
    methods_reachable: int = 0
    methods_reach_mop: int = 0
    methods_directly_reach_mop: int = 0
    windows_count: int = 0
    transitions_count: int = 0
    components_count: int = 0


@dataclass
class ProgressEntry:
    """Per-APK status snapshot — written atomically after each worker run."""

    apk_name: str = ""
    code_package: str = ""
    package_name: str = ""
    status: str = STATUS_NOT_STARTED
    timeout_used_seconds: int = 0
    last_run_started: str = ""
    last_run_finished: str = ""
    analysis_seconds: float = 0.0
    json_size_bytes: int = 0
    sections_present: List[str] = field(default_factory=list)
    methods_total: int = 0
    methods_reachable: int = 0
    methods_reach_mop: int = 0
    methods_directly_reach_mop: int = 0
    windows_count: int = 0
    transitions_count: int = 0
    components_count: int = 0
    gator_reaches_target: Optional[bool] = None
    gator_directly_reaches_target: Optional[bool] = None
    androguard_reaches_target: Optional[bool] = None
    androguard_directly_reaches_target: Optional[bool] = None
    androguard_methods_reaches_target: Optional[int] = None
    androguard_methods_directly_reaches_target: Optional[int] = None
    agreement_reaches_target: Optional[bool] = None
    agreement_directly_reaches_target: Optional[bool] = None
    last_pass_id: str = ""
    error_message: Optional[str] = None


def parse_bool_flexible(value: Any) -> Optional[bool]:
    """Convert PLANILHA-style bool strings ('True'/'False'/''/None) to bool|None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def parse_int_flexible(value: Any) -> int:
    """Convert PLANILHA-style int strings to int, falling back to 0 on empty/invalid."""
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def load_planilha(planilha_path: Path) -> Dict[str, AndroguardEntry]:
    """Read the Joao Androguard CSV into a dict keyed by apk_filename.

    Args:
        planilha_path: Path to PLANILHA.csv.

    Returns:
        Dict mapping APK basename (e.g. 'com.foo_42.apk') to AndroguardEntry.
        Empty dict if the file does not exist (caller decides behavior).
    """
    out: Dict[str, AndroguardEntry] = {}
    if not planilha_path.is_file():
        return out
    with open(planilha_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            apk_filename = (row.get("apk_filename") or "").strip()
            if not apk_filename:
                continue
            out[apk_filename] = AndroguardEntry(
                dex_count=parse_int_flexible(row.get("dex_count")),
                reaches_target=parse_bool_flexible(row.get("sa_reaches_target")),
                directly_reaches_target=parse_bool_flexible(row.get("sa_directly_reaches_target")),
                methods_reaches_target=parse_int_flexible(row.get("sa_num_methods_reaches_target")),
                methods_directly_reaches_target=parse_int_flexible(
                    row.get("sa_num_methods_directly_reaches_target")
                ),
            )
    return out


def load_existing_progress(output_dir: Path) -> Dict[str, ProgressEntry]:
    """Scan _progress/*.json and rebuild the in-memory status map.

    Args:
        output_dir: Sweep output directory containing _progress/ subdir.

    Returns:
        Dict mapping apk_name (basename including .apk) to ProgressEntry.
    """
    out: Dict[str, ProgressEntry] = {}
    progress_dir = output_dir / "_progress"
    if not progress_dir.is_dir():
        return out
    for path in progress_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            entry = ProgressEntry(**{k: v for k, v in data.items()
                                     if k in ProgressEntry.__dataclass_fields__})
            out[entry.apk_name] = entry
        except Exception as e:
            # Corrupted progress file — log and ignore (will be re-classified)
            logging.warning("Failed to read progress file %s: %s", path, e)
    return out


def write_progress_atomic(path: Path, entry: ProgressEntry) -> None:
    """Write ProgressEntry as JSON atomically (tmp + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(asdict(entry), indent=2, default=str))
    os.replace(tmp, path)


def try_json_or_recover(text: str) -> Optional[Dict[str, Any]]:
    """Try plain json.loads; on truncation, retry with bracket-recovery heuristic.

    The GATOR client writes sections incrementally with flush. A timeout/SIGKILL
    can leave the JSON truncated mid-write. We try the same recovery approach
    used by StaticAnalysisParser (INV-ANA-06): find the last '},' in an array,
    truncate, close brackets, retry.
    """
    if not text.strip():
        return None
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        pass

    # Recovery: find last complete array element and close the JSON.
    # The GATOR top-level shape is always { "reachability": [...], "windows": [...], ... }.
    # If truncated mid-array, we want to close that array and the top-level object.
    last_close_array = text.rfind("]")
    last_open_array = text.rfind("[")
    if last_close_array > last_open_array:
        # Cut after last closed array, then close any open arrays and the object.
        candidate = text[:last_close_array + 1]
        # Count unclosed brackets after our cut
        opens = candidate.count("[") - candidate.count("]")
        for _ in range(opens):
            candidate += "]"
        opens_obj = candidate.count("{") - candidate.count("}")
        for _ in range(opens_obj):
            candidate += "}"
        try:
            result = json.loads(candidate)
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            return None

    # Last resort: try truncating at last ',' inside the top-level object
    last_comma = text.rfind(",")
    if last_comma > 0:
        candidate = text[:last_comma]
        opens_arr = candidate.count("[") - candidate.count("]")
        for _ in range(opens_arr):
            candidate += "]"
        opens_obj = candidate.count("{") - candidate.count("}")
        for _ in range(opens_obj):
            candidate += "}"
        try:
            result = json.loads(candidate)
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def derive_metrics_from_raw(raw: Dict[str, Any]) -> ProgressMetrics:
    """Compute counts directly from the recovered raw JSON dict.

    We do this from the raw dict (not the parsed StaticAnalysisData) because:
    1. The raw counts are robust to parser filtering by code_package
       (StaticAnalysisParser drops classes whose name does not contain code_package,
       which can hide methods we still want to count for diagnostics).
    2. The recovery path may produce incomplete StaticAnalysisData; the raw
       counts are still meaningful.

    Args:
        raw: Recovered top-level JSON dict.

    Returns:
        ProgressMetrics with sections_present, methods_total, methods_reachable,
        methods_reach_mop, methods_directly_reach_mop, windows_count,
        transitions_count, components_count.
    """
    metrics = ProgressMetrics()

    section_keys = ["reachability", "windows", "transitions", "components"]
    for key in section_keys:
        if key in raw:
            metrics.sections_present.append(key)

    # Reachability: methods_total / methods_reachable / methods_reach_mop / directly
    reach = raw.get("reachability") or []
    if isinstance(reach, list):
        for class_entry in reach:
            if not isinstance(class_entry, dict):
                continue
            methods = class_entry.get("methods") or []
            for m in methods:
                if not isinstance(m, dict):
                    continue
                metrics.methods_total += 1
                if m.get("reachable"):
                    metrics.methods_reachable += 1
                if m.get("reachesTarget"):
                    metrics.methods_reach_mop += 1
                if m.get("directlyReachesTarget"):
                    metrics.methods_directly_reach_mop += 1

    windows = raw.get("windows") or []
    if isinstance(windows, list):
        metrics.windows_count = len(windows)

    transitions = raw.get("transitions") or []
    if isinstance(transitions, list):
        metrics.transitions_count = len(transitions)

    components = raw.get("components") or {}
    if isinstance(components, dict):
        metrics.components_count = (
            len(components.get("activities") or [])
            + len(components.get("receivers") or [])
            + len(components.get("services") or [])
            + len(components.get("providers") or [])
        )

    return metrics


def classify_status(metrics: ProgressMetrics, json_exists: bool,
                    timed_out: bool) -> str:
    """Map (sections_present, methods_total, file existence, timeout) to a status."""
    if not json_exists:
        return STATUS_FAILED_TIMEOUT_NO_JSON if timed_out else STATUS_FAILED_NO_JSON

    sections = set(metrics.sections_present)
    # Empty reachability is the most informative early-failure signal:
    # classify FIRST regardless of which other sections happen to be present.
    if "reachability" in sections and metrics.methods_total == 0:
        return STATUS_PARTIAL_EMPTY_REACHABILITY

    if sections == {"reachability", "windows", "transitions", "components"}:
        return STATUS_COMPLETE  # methods_total > 0 already guaranteed above
    if sections == {"reachability", "windows", "transitions"}:
        return STATUS_PARTIAL_NO_COMPONENTS
    if sections == {"reachability", "windows"}:
        return STATUS_PARTIAL_NO_TRANSITIONS
    if sections == {"reachability"}:
        return STATUS_PARTIAL_REACHABILITY_ONLY
    if not sections:
        return STATUS_UNPARSEABLE
    # Unexpected combinations (e.g., 'windows' without 'reachability') —
    # not possible with FIX 4c.1 write-first, but classify defensively.
    return STATUS_UNPARSEABLE


def apply_androguard_overlay(entry: ProgressEntry,
                             ag: Optional[AndroguardEntry]) -> ProgressEntry:
    """Populate androguard_* and agreement_* fields on the entry.

    Args:
        entry: Mutated in-place and also returned.
        ag: Androguard data for this APK (None if PLANILHA not provided or
            APK not found in PLANILHA).
    """
    if ag is None:
        return entry
    entry.androguard_reaches_target = ag.reaches_target
    entry.androguard_directly_reaches_target = ag.directly_reaches_target
    entry.androguard_methods_reaches_target = ag.methods_reaches_target
    entry.androguard_methods_directly_reaches_target = ag.methods_directly_reaches_target

    # Agreement only computable if BOTH sides have a definitive bool
    # (gator side is None when worker didn't run or status didn't yield a boolean).
    if entry.gator_reaches_target is not None and ag.reaches_target is not None:
        entry.agreement_reaches_target = (entry.gator_reaches_target == ag.reaches_target)
    if entry.gator_directly_reaches_target is not None and ag.directly_reaches_target is not None:
        entry.agreement_directly_reaches_target = (
            entry.gator_directly_reaches_target == ag.directly_reaches_target
        )
    return entry


def worker(apk_path_str: str, output_dir_str: str, config_kwargs: Dict[str, Any],
           timeout_s: int, pass_id: str) -> Dict[str, Any]:
    """Analyze a single APK in a child process.

    Returns a serializable dict (not a ProgressEntry) to keep the inter-process
    payload trivial. The main process reconstructs ProgressEntry from this dict.
    """
    # Imports inside the worker so the parent doesn't pay startup cost
    # for child-only deps (rv-android modules pull in heavy stuff).
    from rv_android_core.domain.app import App
    from rv_static_analysis import RVStaticAnalysisConfig, StaticAnalyzer

    apk_path = Path(apk_path_str)
    output_dir = Path(output_dir_str)
    apk_name = apk_path.name
    apk_stem = apk_path.stem

    started_at = datetime.now()
    error_message: Optional[str] = None
    timed_out = False
    code_package = ""
    package_name = ""
    apk_output_dir: Optional[Path] = None
    json_path: Optional[Path] = None

    try:
        # Build config and app
        config_kwargs = dict(config_kwargs)
        config_kwargs["analysis_timeout"] = timeout_s
        config = RVStaticAnalysisConfig(**config_kwargs)
        app = App(str(apk_path))
        package_name = app.package_name
        code_package = app.code_package

        apk_output_dir = output_dir / package_name
        apk_output_dir.mkdir(parents=True, exist_ok=True)
        # StaticAnalyzer writes the JSON as f"{app.name}{EXTENSION_STATIC_ANALYSIS}"
        # where app.name = basename WITH the .apk suffix and EXTENSION = ".json".
        # So the actual file ends up as e.g. "app.cclauncher_1290.apk.json".
        json_path = apk_output_dir / f"{apk_name}.json"

        # Backup previous JSON (if any) and bypass StaticAnalyzer cache (INV-ANA-11)
        if json_path.exists():
            backup_dir = output_dir / "_backup"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
            try:
                shutil.copy2(json_path, backup_dir / f"{ts}_{json_path.name}")
            except Exception as e:
                # Backup failure is logged but doesn't abort — the new analysis
                # may still succeed and produce valuable data.
                error_message = f"backup_failed: {e}"
            json_path.unlink()

        # Redirect GATOR stdout/stderr to per-APK log file
        log_dir = output_dir / "_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{apk_stem}.log"

        # The StaticAnalyzer pipes subprocess stdout to sys.stdout; we
        # redirect sys.stdout in this process to the log file for the duration
        # of the analyze() call.
        analyzer = StaticAnalyzer(app=app, config=config, output_dir=str(apk_output_dir))
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        with open(log_path, "w") as logf:
            sys.stdout = logf
            sys.stderr = logf
            try:
                result = analyzer.analyze()
            finally:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
        timed_out = result.timed_out
        if result.errors and error_message is None:
            error_message = "; ".join(result.errors)[:500]

    except Exception as e:
        error_message = (error_message or "") + (
            f"{type(e).__name__}: {e} | {traceback.format_exc(limit=3)}"
        )[:500]

    finished_at = datetime.now()

    # Classify based on whatever JSON ended up on disk
    metrics = ProgressMetrics()
    json_exists = json_path is not None and json_path.exists()
    json_size = json_path.stat().st_size if json_exists else 0

    if json_exists:
        try:
            raw = try_json_or_recover(json_path.read_text())
            if raw is not None:
                metrics = derive_metrics_from_raw(raw)
        except Exception as e:
            error_message = (error_message or "") + f"; classify_read_error: {e}"

    # If we crashed before even computing apk_output_dir, treat as exception
    if apk_output_dir is None:
        status = STATUS_FAILED_EXCEPTION
    else:
        status = classify_status(metrics, json_exists=json_exists, timed_out=timed_out)
        # If python wrapper raised but JSON exists with valid sections, prefer
        # the parsed status — error_message is preserved for diagnostics.

    entry = ProgressEntry(
        apk_name=apk_name,
        code_package=code_package or "",
        package_name=package_name or "",
        status=status,
        timeout_used_seconds=timeout_s,
        last_run_started=started_at.isoformat(timespec="seconds"),
        last_run_finished=finished_at.isoformat(timespec="seconds"),
        analysis_seconds=(finished_at - started_at).total_seconds(),
        json_size_bytes=json_size,
        sections_present=metrics.sections_present,
        methods_total=metrics.methods_total,
        methods_reachable=metrics.methods_reachable,
        methods_reach_mop=metrics.methods_reach_mop,
        methods_directly_reach_mop=metrics.methods_directly_reach_mop,
        windows_count=metrics.windows_count,
        transitions_count=metrics.transitions_count,
        components_count=metrics.components_count,
        gator_reaches_target=(metrics.methods_reach_mop > 0) if json_exists and metrics.methods_total > 0 else None,
        gator_directly_reaches_target=(metrics.methods_directly_reach_mop > 0) if json_exists and metrics.methods_total > 0 else None,
        last_pass_id=pass_id,
        error_message=error_message[:500] if error_message else None,
    )
    return asdict(entry)


def decide_to_process(apk_files: List[Path],
                      progress: Dict[str, ProgressEntry],
                      planilha: Dict[str, AndroguardEntry],
                      retry_statuses: Set[str]) -> Tuple[List[Path], List[Tuple[Path, str]]]:
    """Split APKs into (process_now, skip_with_status) lists.

    Skip reasons (in order):
      1. APK has dex_count==0 in PLANILHA → STATUS_SKIPPED_NO_JAVA_CODE
      2. APK already has progress entry with status not in retry_statuses → skip
      3. Otherwise → process

    Args:
        apk_files: All .apk paths from --apks-dir.
        progress: Existing progress entries keyed by apk_name (basename).
        planilha: Androguard data keyed by apk_name (basename).
        retry_statuses: Set of statuses to reprocess.

    Returns:
        (to_process, [(apk_path, reason_status), ...])
    """
    to_process: List[Path] = []
    to_skip: List[Tuple[Path, str]] = []

    for apk in apk_files:
        ag = planilha.get(apk.name)
        existing = progress.get(apk.name)

        # Pre-filter: native-only APK
        if ag is not None and ag.dex_count == 0:
            if existing is None or existing.status != STATUS_SKIPPED_NO_JAVA_CODE:
                to_skip.append((apk, STATUS_SKIPPED_NO_JAVA_CODE))
            else:
                to_skip.append((apk, "already_skipped"))
            continue

        # Skip if already in a non-retry status
        if existing is not None and existing.status not in retry_statuses:
            to_skip.append((apk, f"keep_{existing.status}"))
            continue

        to_process.append(apk)

    return to_process, to_skip


def write_skipped_no_java_code(apk: Path, output_dir: Path,
                               planilha: Dict[str, AndroguardEntry],
                               pass_id: str) -> ProgressEntry:
    """Build and persist a STATUS_SKIPPED_NO_JAVA_CODE entry without invoking GATOR."""
    ag = planilha.get(apk.name)
    now = datetime.now().isoformat(timespec="seconds")
    entry = ProgressEntry(
        apk_name=apk.name,
        code_package="",
        package_name="",
        status=STATUS_SKIPPED_NO_JAVA_CODE,
        timeout_used_seconds=0,
        last_run_started=now,
        last_run_finished=now,
        analysis_seconds=0.0,
        last_pass_id=pass_id,
        error_message="dex_count==0 in PLANILHA — APK has no Java bytecode",
    )
    entry = apply_androguard_overlay(entry, ag)
    write_progress_atomic(output_dir / "_progress" / f"{apk.stem}.json", entry)
    return entry


def regenerate_csv(output_dir: Path, apk_files: List[Path],
                   planilha: Dict[str, AndroguardEntry]) -> Path:
    """Regenerate progress.csv from _progress/*.json + APKs not yet processed.

    Args:
        output_dir: Sweep output dir (must contain _progress/).
        apk_files: All APKs in scope (used to add not_started rows for unseen APKs).
        planilha: Androguard data (used to overlay androguard_* / agreement_* on
                  not_started rows when available).

    Returns:
        Path to the generated CSV.
    """
    progress = load_existing_progress(output_dir)
    csv_path = output_dir / "progress.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    seen: Set[str] = set()
    rows: List[Dict[str, Any]] = []

    for apk in sorted(apk_files):
        seen.add(apk.name)
        entry = progress.get(apk.name)
        if entry is None:
            entry = ProgressEntry(apk_name=apk.name, status=STATUS_NOT_STARTED)
        entry = apply_androguard_overlay(entry, planilha.get(apk.name))
        rows.append(_entry_to_csv_row(entry))

    # Include orphan progress entries that don't match any APK currently in the dir
    # (e.g., APK was removed between runs). They appear at the end.
    for apk_name, entry in sorted(progress.items()):
        if apk_name in seen:
            continue
        entry = apply_androguard_overlay(entry, planilha.get(apk_name))
        rows.append(_entry_to_csv_row(entry))

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return csv_path


def _entry_to_csv_row(entry: ProgressEntry) -> Dict[str, Any]:
    """Serialize ProgressEntry into a CSV row dict matching CSV_COLUMNS."""
    return {
        "apk_name": entry.apk_name,
        "code_package": entry.code_package,
        "status": entry.status,
        "timeout_used_seconds": entry.timeout_used_seconds,
        "analysis_seconds": f"{entry.analysis_seconds:.2f}",
        "sections_present": "|".join(entry.sections_present),
        "methods_total": entry.methods_total,
        "methods_reachable": entry.methods_reachable,
        "methods_reach_mop": entry.methods_reach_mop,
        "methods_directly_reach_mop": entry.methods_directly_reach_mop,
        "windows_count": entry.windows_count,
        "transitions_count": entry.transitions_count,
        "components_count": entry.components_count,
        "gator_reaches_target": _bool_or_empty(entry.gator_reaches_target),
        "gator_directly_reaches_target": _bool_or_empty(entry.gator_directly_reaches_target),
        "androguard_reaches_target": _bool_or_empty(entry.androguard_reaches_target),
        "androguard_directly_reaches_target": _bool_or_empty(entry.androguard_directly_reaches_target),
        "androguard_methods_reaches_target": _int_or_empty(entry.androguard_methods_reaches_target),
        "androguard_methods_directly_reaches_target": _int_or_empty(entry.androguard_methods_directly_reaches_target),
        "agreement_reaches_target": _bool_or_empty(entry.agreement_reaches_target),
        "agreement_directly_reaches_target": _bool_or_empty(entry.agreement_directly_reaches_target),
        "json_size_bytes": entry.json_size_bytes,
        "last_pass_id": entry.last_pass_id,
        "last_run_finished": entry.last_run_finished,
        "error_message": (entry.error_message or "")[:500],
    }


def _bool_or_empty(v: Optional[bool]) -> str:
    return "" if v is None else ("True" if v else "False")


def _int_or_empty(v: Optional[int]) -> str:
    return "" if v is None else str(v)


def kill_orphan_java_processes() -> int:
    """Defensively kill leftover GATOR Java processes after SIGINT or shutdown.

    ProcessPoolExecutor terminates worker children, but the Java grandchildren
    spawned by Command.invoke() may survive. We match by command line.

    Returns:
        Number of processes killed.
    """
    try:
        import psutil
    except ImportError:
        return 0
    killed = 0
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if "rvsec-analysis-client.jar" in cmdline:
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed


def kill_all_descendants(timeout: float = 3.0) -> int:
    """SIGKILL every descendant process of this process, return count killed.

    Used by the SIGINT/SIGTERM handler. Works because psutil walks the actual
    process tree (children, grandchildren, ...), so it gets the pool workers
    AND their GATOR Java grandchildren in one shot.

    Args:
        timeout: Seconds to wait for descendants to actually exit after SIGKILL.

    Returns:
        Number of descendants attempted to kill.
    """
    try:
        import psutil
    except ImportError:
        return 0
    me = psutil.Process(os.getpid())
    descendants = me.children(recursive=True)
    for proc in descendants:
        try:
            proc.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(descendants, timeout=timeout)
    return len(descendants)


# Module-level state populated by install_signal_handlers — read from the
# signal handler since signal handlers must be top-level functions.
_shutdown_state: Dict[str, Any] = {"shutting_down": False}


def _signal_handler(signum, frame):  # noqa: ARG001
    """SIGINT/SIGTERM handler: kill descendants, save state, os._exit.

    First signal: graceful — kill descendants, regen CSV, append sweep_runs entry.
    Second signal (escalation): nuclear — kill descendants and exit immediately.

    Uses os._exit(130) to bypass ProcessPoolExecutor.__exit__ which calls
    shutdown(wait=True), blocking until running GATOR analyses complete (could
    be the full 30min timeout per worker). os._exit also bypasses the normal
    finally block, so the CSV regen happens here explicitly.
    """
    log = logging.getLogger("sweep")
    if _shutdown_state["shutting_down"]:
        log.warning("Second signal %d received — exiting NOW", signum)
        kill_all_descendants(timeout=1.0)
        os._exit(130)
    _shutdown_state["shutting_down"] = True
    log.warning("Signal %d received — killing descendants", signum)
    n_killed = kill_all_descendants(timeout=3.0)
    log.warning("Killed %d descendant process(es)", n_killed)

    # Best-effort: regen CSV + record sweep_runs entry before exiting.
    output_dir = _shutdown_state.get("output_dir")
    apk_files = _shutdown_state.get("apk_files")
    planilha = _shutdown_state.get("planilha")
    pass_id = _shutdown_state.get("pass_id", "")
    if output_dir and apk_files is not None and planilha is not None:
        try:
            csv_path = regenerate_csv(output_dir, apk_files, planilha)
            log.info("CSV regenerated on shutdown: %s", csv_path)
        except Exception as e:
            log.error("CSV regen on shutdown failed: %s", e)
        try:
            record_sweep_run(output_dir, {
                "pass_id": pass_id,
                "interrupted": True,
                "interrupted_at": datetime.now().isoformat(timespec="seconds"),
                "killed_descendants": n_killed,
                "signal": signum,
            })
        except Exception:
            pass
    log.warning("Exiting with code 130 (interrupted)")
    os._exit(130)


def install_signal_handlers(output_dir: Path, apk_files: List[Path],
                            planilha: Dict[str, AndroguardEntry],
                            pass_id: str) -> None:
    """Install SIGINT/SIGTERM handlers BEFORE the pool starts.

    Stash state in _shutdown_state so the (top-level) handler can access it.
    """
    _shutdown_state["output_dir"] = output_dir
    _shutdown_state["apk_files"] = apk_files
    _shutdown_state["planilha"] = planilha
    _shutdown_state["pass_id"] = pass_id
    _shutdown_state["shutting_down"] = False
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def record_sweep_run(output_dir: Path, summary: Dict[str, Any]) -> None:
    """Append a JSON line per sweep invocation into sweep_runs.jsonl."""
    path = output_dir / "sweep_runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary, default=str) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Static-analysis sweep with resume + Androguard cross-validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--apks-dir", required=True, type=Path,
                        help="Directory containing .apk files")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output directory (JSONs, _progress/, _backup/, _logs/, progress.csv)")
    parser.add_argument("--timeout", type=int, default=900,
                        help="Per-APK analysis timeout in seconds (default: 900 = 15min)")
    parser.add_argument("--workers", type=int, default=8,
                        help="Parallel workers (default: 8)")
    parser.add_argument("--rvsec-root", type=str, default=None,
                        help="RVSEC installation root (default: $RVSEC_HOME)")
    parser.add_argument("--jvm-memory", type=str, default="12g",
                        help="JVM heap size for GATOR (default: 12g)")
    parser.add_argument("--cg-algorithm", choices=["spark", "cha", "rta", "vta"],
                        default="spark",
                        help="Call graph algorithm (default: spark)")
    parser.add_argument("--skip-wtg", action="store_true",
                        help="Skip WTG construction (propagated as -clientParam "
                             "skipWtg=true). Saves wall-clock on APKs where WTG "
                             "is guaranteed to time out. Partial JSON still has "
                             "reachability + windows[].")
    parser.add_argument("--cg-delegation", choices=["true", "false"], default=None,
                        help="Propagated as -cgDelegation <bool>. When 'true', "
                             "FlowgraphRebuilder queries Scene.v().getCallGraph() "
                             "(SPARK) for virtual dispatch in the WTG build. When "
                             "'false', uses the legacy points-to + CHA fallback path. "
                             "Default: GATOR's baked-in (false post-M3; opt-in to "
                             "true for apps without hybrid-framework dispatch).")
    parser.add_argument("--planilha", type=Path, default=None,
                        help="Path to PLANILHA.csv (Joao Androguard reference). "
                             "Enables dex_count==0 pre-filter and cross-validation columns.")
    default_retry_help = ",".join(sorted(DEFAULT_RETRY_STATUSES))
    parser.add_argument("--retry-statuses", type=str, default=None,
                        help=f"Comma-separated statuses to reprocess. "
                             f"Default: {default_retry_help}")
    parser.add_argument("--regen-csv-only", action="store_true",
                        help="Skip analysis; only regenerate progress.csv from _progress/")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done without running analyses")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N APKs after pre-filter (smoke testing)")
    return parser.parse_args()


def build_config_kwargs(args: argparse.Namespace) -> Dict[str, Any]:
    """Build a dict of RVStaticAnalysisConfig kwargs (passed to workers as dict)."""
    kwargs: Dict[str, Any] = {
        "jvm_memory": args.jvm_memory,
        "cg_algorithm": args.cg_algorithm,
        "analysis_timeout": args.timeout,
        "skip_wtg": getattr(args, "skip_wtg", False),
        # validate_on_init True is desirable in workers — fail loud on missing JAR/SDK.
        "validate_on_init": True,
    }
    cg_del = getattr(args, "cg_delegation", None)
    if cg_del is not None:
        kwargs["cg_delegation"] = (cg_del == "true")
    if args.rvsec_root:
        kwargs["rvsec_root"] = args.rvsec_root
    return kwargs


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("sweep")

    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "_progress").mkdir(exist_ok=True)
    (output_dir / "_backup").mkdir(exist_ok=True)
    (output_dir / "_logs").mkdir(exist_ok=True)

    # Discover APKs
    apk_files = sorted(args.apks_dir.glob("*.apk"))
    if not apk_files:
        log.error("No .apk files found in %s", args.apks_dir)
        return 1
    log.info("Found %d APK(s) in %s", len(apk_files), args.apks_dir)

    # Load PLANILHA (optional)
    planilha: Dict[str, AndroguardEntry] = {}
    if args.planilha:
        planilha = load_planilha(args.planilha)
        log.info("Loaded %d entries from %s", len(planilha), args.planilha)

    # Regen CSV mode — short-circuit
    if args.regen_csv_only:
        csv_path = regenerate_csv(output_dir, apk_files, planilha)
        log.info("Regenerated CSV: %s", csv_path)
        return 0

    # Validate config eagerly so we fail fast on missing JAR/SDK
    config_kwargs = build_config_kwargs(args)
    try:
        from rv_static_analysis import RVStaticAnalysisConfig  # noqa: F401
        # Trigger validation in main process before forking workers
        RVStaticAnalysisConfig(**config_kwargs)
    except Exception as e:
        log.error("Config validation failed: %s", e)
        return 1

    # Load existing progress + decide what to (re)process
    progress = load_existing_progress(output_dir)
    log.info("Existing progress entries: %d", len(progress))

    retry_statuses = (
        set(s.strip() for s in args.retry_statuses.split(",") if s.strip())
        if args.retry_statuses
        else set(DEFAULT_RETRY_STATUSES)
    )
    log.info("Retry statuses: %s", sorted(retry_statuses))

    to_process, to_skip = decide_to_process(apk_files, progress, planilha, retry_statuses)

    pass_id = f"pass_{datetime.now().strftime('%Y%m%dT%H%M%S')}_t{args.timeout}"
    new_skip_count = sum(1 for _, r in to_skip if r == STATUS_SKIPPED_NO_JAVA_CODE)

    # Apply --limit AFTER pre-filtering (so --limit 5 actually runs 5 analyses)
    if args.limit is not None:
        to_process = to_process[: args.limit]

    log.info("To process: %d | To skip: %d (incl. %d new skipped_no_java_code)",
             len(to_process), len(to_skip), new_skip_count)

    if args.dry_run:
        log.info("DRY RUN — would process:")
        for apk in to_process[:20]:
            log.info("  %s", apk.name)
        if len(to_process) > 20:
            log.info("  ... and %d more", len(to_process) - 20)
        log.info("DRY RUN — would skip:")
        from collections import Counter
        skip_reasons = Counter(reason for _, reason in to_skip)
        for reason, count in skip_reasons.most_common():
            log.info("  %d × %s", count, reason)
        return 0

    # Persist SKIPPED_NO_JAVA_CODE entries (those won't run in the pool).
    # Done AFTER the dry-run gate so --dry-run never touches disk.
    new_skips = 0
    for apk, reason in to_skip:
        if reason == STATUS_SKIPPED_NO_JAVA_CODE:
            write_skipped_no_java_code(apk, output_dir, planilha, pass_id)
            new_skips += 1

    if not to_process:
        log.info("Nothing to process. Regenerating CSV.")
        regenerate_csv(output_dir, apk_files, planilha)
        return 0

    # Install signal handlers BEFORE creating the pool, so SIGINT/SIGTERM
    # received during pool construction or worker submission are handled
    # cleanly (kill descendants + os._exit, bypassing pool.shutdown(wait=True)
    # which would otherwise block 30+min waiting for in-flight workers).
    install_signal_handlers(output_dir, apk_files, planilha, pass_id)
    log.info("Signal handlers installed (SIGINT/SIGTERM kill the process tree)")

    # Write pidfile so user can kill reliably:  kill -INT $(cat <output>/sweep.pid)
    # This avoids the `uv run`/`$!` PID confusion where backgrounding the wrapper
    # captures uv's transient PID instead of the actual python script's PID.
    pidfile = output_dir / "sweep.pid"
    pidfile.write_text(str(os.getpid()) + "\n")
    log.info("PID %d written to %s", os.getpid(), pidfile)

    if getattr(args, "skip_wtg", False):
        log.info("[SWEEP] skipWtg=true active for this run")

    # Run analyses in parallel
    started_at = datetime.now()
    counters = {"complete": 0, "partial": 0, "failed": 0, "skipped": 0}
    completed = 0

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(worker, str(apk), str(output_dir), config_kwargs,
                        args.timeout, pass_id): apk
            for apk in to_process
        }
        for fut in as_completed(futures):
            apk = futures[fut]
            try:
                entry_dict = fut.result()
            except Exception as e:
                log.error("[%s] worker raised: %s", apk.name, e)
                entry_dict = asdict(ProgressEntry(
                    apk_name=apk.name,
                    status=STATUS_FAILED_EXCEPTION,
                    timeout_used_seconds=args.timeout,
                    last_pass_id=pass_id,
                    error_message=f"{type(e).__name__}: {e}"[:500],
                ))

            # Reconstruct, overlay Androguard, persist
            entry = ProgressEntry(**{k: v for k, v in entry_dict.items()
                                      if k in ProgressEntry.__dataclass_fields__})
            entry = apply_androguard_overlay(entry, planilha.get(apk.name))
            write_progress_atomic(output_dir / "_progress" / f"{apk.stem}.json", entry)

            completed += 1
            if entry.status == STATUS_COMPLETE:
                counters["complete"] += 1
            elif entry.status.startswith("partial_"):
                counters["partial"] += 1
            elif entry.status.startswith("failed_"):
                counters["failed"] += 1
            elif entry.status == STATUS_SKIPPED_NO_JAVA_CODE:
                counters["skipped"] += 1

            log.info("[%d/%d] %s -> %s (%.0fs, methods=%d, mop=%d)",
                     completed, len(to_process), apk.name, entry.status,
                     entry.analysis_seconds, entry.methods_total,
                     entry.methods_reach_mop)

    # Normal completion path: regenerate CSV + record sweep run.
    # Signal-driven shutdown skips this (handler does its own save via os._exit).
    finished_at = datetime.now()
    try:
        csv_path = regenerate_csv(output_dir, apk_files, planilha)
        log.info("CSV regenerated: %s", csv_path)
    except Exception as e:
        log.error("CSV regeneration failed: %s", e)

    record_sweep_run(output_dir, {
        "pass_id": pass_id,
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "wall_seconds": (finished_at - started_at).total_seconds(),
        "timeout_seconds": args.timeout,
        "workers": args.workers,
        "cg_algorithm": args.cg_algorithm,
        "jvm_memory": args.jvm_memory,
        "to_process": len(to_process),
        "completed": completed,
        "counters": counters,
        "skipped_no_java_code_new": new_skips,
        "interrupted": False,
    })

    # Clean up pidfile on normal completion (signal handler doesn't bother — the
    # operator already knows the sweep stopped if they sent the signal).
    try:
        pidfile.unlink(missing_ok=True)
    except Exception:
        pass

    log.info("Summary: %s", counters)
    return 0


if __name__ == "__main__":
    sys.exit(main())
