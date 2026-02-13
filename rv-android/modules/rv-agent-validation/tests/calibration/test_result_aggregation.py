"""
Tests for summary CSV aggregation logic (T15-T18).

Validates that per-batch summary.csv files are correctly concatenated
into a single aggregated file by baseline_docker.py.
"""

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from baseline_docker import aggregate_summaries


def _create_batch_csv(tmp_path: Path, batch_num: int, n_rows: int) -> Path:
    """Helper: create a batch directory with a summary.csv file."""
    batch_dir = tmp_path / f"batch_{batch_num}" / f"batch_{batch_num}"
    batch_dir.mkdir(parents=True)
    csv_path = batch_dir / "summary.csv"

    rows = []
    for i in range(n_rows):
        rows.append({
            "apk": f"app_{batch_num}_{i}.apk",
            "tool": "rvagent",
            "cov_method": 50.0 + i,
            "errors": 3 + i,
        })
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return csv_path


def test_aggregate_multiple_batches(tmp_path):
    """T15: 3 batch CSVs with 5 rows each produce 15-row aggregated CSV."""
    for i in range(3):
        _create_batch_csv(tmp_path, i, 5)

    result = aggregate_summaries(tmp_path, 3)

    assert result is not None
    assert result.exists()
    df = pd.read_csv(result)
    assert len(df) == 15

    # D5/L2: symlink for human readability
    symlink_path = tmp_path / "aggregated_summary.csv"
    assert symlink_path.is_symlink()
    assert symlink_path.resolve() == result.resolve()


def test_aggregate_deduplicates_headers(tmp_path):
    """T16: Only one header row — no row where apk == 'apk'."""
    for i in range(3):
        _create_batch_csv(tmp_path, i, 5)

    result = aggregate_summaries(tmp_path, 3)
    df = pd.read_csv(result)

    # pd.read_csv handles headers correctly, but verify no header-as-data
    assert "apk" not in df["apk"].values


def test_aggregate_empty_batch(tmp_path):
    """T17: An empty batch directory (no summary.csv) is skipped."""
    _create_batch_csv(tmp_path, 0, 5)
    _create_batch_csv(tmp_path, 1, 5)
    # batch_2 directory exists but has no summary.csv
    (tmp_path / "batch_2" / "batch_2").mkdir(parents=True)

    result = aggregate_summaries(tmp_path, 3)

    assert result is not None
    df = pd.read_csv(result)
    assert len(df) == 10


def test_aggregate_missing_batch(tmp_path, caplog):
    """T18: A missing batch directory produces a warning but doesn't abort."""
    _create_batch_csv(tmp_path, 0, 5)
    _create_batch_csv(tmp_path, 1, 5)
    # batch_2 doesn't exist at all

    with caplog.at_level(logging.WARNING):
        result = aggregate_summaries(tmp_path, 3)

    assert result is not None
    df = pd.read_csv(result)
    assert len(df) == 10
    assert any("batch" in record.message.lower() for record in caplog.records)
