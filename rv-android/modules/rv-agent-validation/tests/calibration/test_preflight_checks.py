"""
Tests for pre-flight validation logic (T24-T27).

Validates that preflight_checks() catches missing directories, files,
and low disk space before launching containers. Tests both the orchestrator
and baseline variants.
"""

import sys
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from calibration_orchestrator import preflight_checks as orchestrator_preflight
from baseline_docker import preflight_checks as baseline_preflight


@pytest.fixture(params=["orchestrator", "baseline"])
def preflight_fn(request):
    """Test both preflight implementations — they share the same contract."""
    if request.param == "orchestrator":
        # orchestrator's preflight_checks takes a third arg (agent_mode)
        def wrapper(data_dir, filter_file):
            return orchestrator_preflight(data_dir, filter_file, "pure_algorithm")
        return wrapper
    return baseline_preflight


def test_missing_data_dir(tmp_path, preflight_fn):
    """T24: Non-existent data directory raises SystemExit."""
    filter_file = tmp_path / "filter.txt"
    filter_file.write_text("app.apk\n")

    with pytest.raises(SystemExit):
        preflight_fn(
            data_dir="/nonexistent/data/dir",
            filter_file=str(filter_file),
        )


def test_missing_filter_file(tmp_path, preflight_fn):
    """T25: Non-existent filter file raises SystemExit."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    with pytest.raises(SystemExit):
        preflight_fn(
            data_dir=str(data_dir),
            filter_file="/nonexistent/filter.txt",
        )


def test_disk_space_check(tmp_path, preflight_fn):
    """T26: Insufficient disk space raises SystemExit."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    filter_file = tmp_path / "filter.txt"
    filter_file.write_text("app.apk\n")

    # Mock shutil.disk_usage to report only 1MB free
    DiskUsage = namedtuple("usage", ["total", "used", "free"])
    fake_usage = DiskUsage(100_000_000_000, 99_999_000_000, 1_000_000)
    with patch("shutil.disk_usage", return_value=fake_usage):
        with pytest.raises(SystemExit):
            preflight_fn(
                data_dir=str(data_dir),
                filter_file=str(filter_file),
            )


def test_all_checks_pass(tmp_path, preflight_fn):
    """T27: Valid inputs with sufficient disk pass without error."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    filter_file = tmp_path / "filter.txt"
    filter_file.write_text("app.apk\n")

    # Should not raise
    preflight_fn(
        data_dir=str(data_dir),
        filter_file=str(filter_file),
    )
