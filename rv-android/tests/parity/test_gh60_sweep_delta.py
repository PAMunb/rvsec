"""Unit tests for `scripts/check_gh60_sweep_delta.py`.

The comparator encodes three pieces of gate semantics that need pinning
down before we trust the verdict on a real 380-APK sweep:

    1. Naming-scheme transparency — counts must come out the same whether
       the per-APK JSON uses `reachesMop` (pre-gh60) or `reachesTarget`
       (post-gh60). The whole point of the sweep is to detect *semantic*
       drift, not key renames.
    2. Relative delta math at base=0 — `_rel_delta(0, 0)` should be 0.0
       (vacuously fine); `_rel_delta(0, 1)` returns None and the row is
       flagged as an outlier (growth from nothing is suspicious).
    3. Gate aggregation — G1..G4 must all PASS for the script to exit 0.

Each test below plants a fixture sweep tree under `tmp_path` and walks
the comparator against it, asserting both the per-row deltas and the
final summary verdict. Fast (no GATOR), deterministic, runs in <1s.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_gh60_sweep_delta.py"


def _load_comparator():
    spec = importlib.util.spec_from_file_location("_gh60_delta", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_gh60_delta"] = module
    spec.loader.exec_module(module)
    return module


comp = _load_comparator()


def _write_apk_json(
    sweep_root: Path,
    apk_name: str,
    *,
    reach_methods: int = 0,
    direct_methods: int = 0,
    n_windows: int = 0,
    n_transitions: int = 0,
    complete: bool | None = True,
    legacy_keys: bool = False,
    methods_total: int | None = None,
) -> None:
    """Plant a per-APK JSON in sweep_root/<pkg>/<apk_name>.json.

    legacy_keys=True writes `reachesMop`/`directlyReachesMop` (pre-gh60
    baseline); False writes the post-rename keys. This is exactly what
    the comparator's naming-scheme transparency invariant pins down.
    """
    if methods_total is None:
        methods_total = max(reach_methods, direct_methods, 1)
    reach_key = "reachesMop" if legacy_keys else "reachesTarget"
    direct_key = "directlyReachesMop" if legacy_keys else "directlyReachesTarget"

    methods = []
    for i in range(methods_total):
        methods.append({
            "name": f"m{i}",
            "signature": f"<com.app.X: void m{i}()>",
            "reachable": True,
            reach_key: i < reach_methods,
            direct_key: i < direct_methods,
        })

    payload = {
        "package": "com.app",
        "mainActivity": "com.app.MainActivity",
        "reachability": [{"className": "com.app.X", "methods": methods}],
        "windows": [{"id": i, "name": f"w{i}", "type": "ACTIVITY"} for i in range(n_windows)],
        "transitions": [{"sourceId": 0, "targetId": 1, "events": []} for _ in range(n_transitions)],
    }
    if complete is not None:
        payload["complete"] = complete

    pkg_dir = sweep_root / "com.app"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / f"{apk_name}.json").write_text(json.dumps(payload), encoding="utf-8")


# ── _count_apk + scan_sweep_dir ────────────────────────────────────────


def test_legacy_keys_count_the_same_as_renamed(tmp_path: Path) -> None:
    """Naming-scheme transparency: `reachesMop` counted identically to `reachesTarget`."""
    legacy_dir = tmp_path / "legacy"
    new_dir = tmp_path / "new"
    _write_apk_json(legacy_dir, "foo.apk", reach_methods=7, direct_methods=3,
                    n_windows=5, n_transitions=4, legacy_keys=True)
    _write_apk_json(new_dir, "foo.apk", reach_methods=7, direct_methods=3,
                    n_windows=5, n_transitions=4, legacy_keys=False)

    legacy = comp._scan_sweep_dir(legacy_dir)
    new = comp._scan_sweep_dir(new_dir)

    assert legacy["foo.apk"].reaches_target == new["foo.apk"].reaches_target == 7
    assert legacy["foo.apk"].directly_reaches_target == new["foo.apk"].directly_reaches_target == 3
    assert legacy["foo.apk"].windows == new["foo.apk"].windows == 5
    assert legacy["foo.apk"].transitions == new["foo.apk"].transitions == 4


def test_scan_skips_aux_directories(tmp_path: Path) -> None:
    """`_progress/`, `_backup/`, `_logs/`, `delta_report/` must be ignored.

    These dirs carry sweep auxiliary state — counting them as APK results
    would double-report and inflate the denominator.
    """
    _write_apk_json(tmp_path, "real.apk", reach_methods=2)
    # Plant a JSON inside _progress with the same shape; it must be skipped.
    progress = tmp_path / "_progress"
    progress.mkdir()
    (progress / "real.apk.json").write_text(
        json.dumps({"reachability": [{"className": "x",
                                       "methods": [{"reachesTarget": True}]}]}),
        encoding="utf-8",
    )

    out = comp._scan_sweep_dir(tmp_path)
    assert set(out.keys()) == {"real.apk"}


# ── _rel_delta math ────────────────────────────────────────────────────


def test_rel_delta_base_zero_new_zero_is_zero() -> None:
    """No signal, no drift — vacuously fine, must not be flagged as outlier."""
    assert comp._rel_delta(0, 0) == 0.0


def test_rel_delta_base_zero_new_positive_is_none() -> None:
    """Growth from nothing → cannot normalise; flagged separately."""
    assert comp._rel_delta(0, 1) is None
    assert comp._rel_delta(0, 100) is None


def test_rel_delta_symmetric_for_growth_and_shrinkage() -> None:
    """|new - base| / base — direction of drift doesn't matter for the gate."""
    assert comp._rel_delta(100, 110) == pytest.approx(0.10)
    assert comp._rel_delta(100, 90) == pytest.approx(0.10)


def test_rel_delta_threshold_boundary() -> None:
    """Exactly at threshold passes; over threshold fails."""
    threshold = 0.05
    assert comp._rel_delta(100, 105) == pytest.approx(threshold)  # at boundary
    assert comp._rel_delta(100, 106) > threshold


# ── end-to-end: per-row + summary verdict ──────────────────────────────


def _build_pair(tmp_path: Path, *, drift: dict) -> tuple[Path, Path]:
    """Create a baseline vs new pair where each APK can be configured.

    `drift` is a dict apk_name → (base_reach, new_reach, complete). Windows
    and transitions are kept identical so the per-row test only exercises
    the reach_target dimension unless overridden inline.
    """
    base = tmp_path / "baseline"
    new = tmp_path / "new"
    for apk, (b, n, complete) in drift.items():
        _write_apk_json(base, apk, reach_methods=b, n_windows=2, n_transitions=2,
                        complete=True, legacy_keys=True)
        _write_apk_json(new, apk, reach_methods=n, n_windows=2, n_transitions=2,
                        complete=complete, legacy_keys=False)
    return base, new


def test_within_threshold_pair_is_pass(tmp_path: Path) -> None:
    base, new = _build_pair(tmp_path, drift={
        "good_a.apk": (100, 100, True),
        "good_b.apk": (100, 104, True),  # 4% drift, under 5%
    })

    rc = comp.main(["--baseline-dir", str(base), "--new-dir", str(new)])
    assert rc == 0

    summary = json.loads((new / "delta_report" / "summary.json").read_text())
    assert summary["pass"] is True
    assert summary["n_outliers"] == 0
    assert summary["complete_rate"] == 1.0


def test_drift_beyond_threshold_flagged(tmp_path: Path) -> None:
    base, new = _build_pair(tmp_path, drift={
        "ok.apk":   (100, 100, True),
        "drift.apk": (100, 120, True),  # 20% drift, breaks gate
    })

    rc = comp.main(["--baseline-dir", str(base), "--new-dir", str(new)])
    assert rc == 1

    summary = json.loads((new / "delta_report" / "summary.json").read_text())
    assert summary["pass"] is False
    assert summary["gates"]["G1_reaches_target_within_threshold"] is False
    assert "drift.apk" in summary["outlier_apks"]
    assert "ok.apk" not in summary["outlier_apks"]


def test_complete_rate_below_floor_fails(tmp_path: Path) -> None:
    # Three APKs, only one with complete=True → 33% rate, below 80% floor.
    base, new = _build_pair(tmp_path, drift={
        "a.apk": (10, 10, True),
        "b.apk": (10, 10, False),
        "c.apk": (10, 10, None),  # missing sentinel — treated as not-complete
    })

    rc = comp.main(["--baseline-dir", str(base), "--new-dir", str(new)])
    assert rc == 1

    summary = json.loads((new / "delta_report" / "summary.json").read_text())
    assert summary["gates"]["G4_complete_rate_above_floor"] is False
    assert summary["complete_rate"] == pytest.approx(1 / 3)


def test_apk_present_only_on_one_side_is_reported_not_flagged(tmp_path: Path) -> None:
    """Asymmetric coverage surfaces in only_baseline/only_new, not outliers.

    The gate is about *semantic drift on shared APKs* — a dataset change
    (APK added/removed between runs) is operator-visible but not a
    regression of the rename itself.
    """
    base = tmp_path / "baseline"
    new = tmp_path / "new"
    _write_apk_json(base, "shared.apk", reach_methods=10, legacy_keys=True)
    _write_apk_json(base, "only_old.apk", reach_methods=10, legacy_keys=True)
    _write_apk_json(new, "shared.apk", reach_methods=10, legacy_keys=False)
    _write_apk_json(new, "only_new.apk", reach_methods=10, legacy_keys=False)

    rc = comp.main(["--baseline-dir", str(base), "--new-dir", str(new)])
    assert rc == 0  # shared apk has zero drift; one-sided don't count

    summary = json.loads((new / "delta_report" / "summary.json").read_text())
    assert summary["only_baseline_apks"] == ["only_old.apk"]
    assert summary["only_new_apks"] == ["only_new.apk"]
    assert summary["n_outliers"] == 0
    assert summary["pass"] is True


def test_growth_from_zero_flagged_as_outlier(tmp_path: Path) -> None:
    """Baseline had 0 reach-target hits, new has some → cannot normalise.

    The script flags this row because growth-from-nothing is exactly the
    pattern a rename bug would produce (a stale matcher hits where it
    shouldn't). Operator can examine the outliers.csv and decide whether
    the change is legitimate (new MOP spec entries) or regression.
    """
    base, new = _build_pair(tmp_path, drift={
        "zero_to_some.apk": (0, 5, True),
    })

    rc = comp.main(["--baseline-dir", str(base), "--new-dir", str(new)])
    assert rc == 1

    summary = json.loads((new / "delta_report" / "summary.json").read_text())
    assert "zero_to_some.apk" in summary["outlier_apks"]


def test_unparseable_json_does_not_crash(tmp_path: Path) -> None:
    """Broken JSON in either sweep dir → row counted but no exception."""
    base = tmp_path / "baseline"
    new = tmp_path / "new"
    base.mkdir()
    new.mkdir()
    # Plant valid baseline + broken new
    _write_apk_json(base, "broken.apk", reach_methods=10, legacy_keys=True)
    pkg = new / "com.app"
    pkg.mkdir()
    (pkg / "broken.apk.json").write_text("{ malformed", encoding="utf-8")

    rc = comp.main(["--baseline-dir", str(base), "--new-dir", str(new)])
    # Verdict: broken side has reaches_target=0, baseline has 10 → 100%
    # shrinkage → outlier → FAIL (1).
    assert rc == 1
