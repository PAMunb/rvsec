"""
PostProcessor and ResultManager tests.

Tests cover:
- INV-EXP-11: PostProcessor generates instrument_errors.json (even if empty)
"""

import json
import os
import pytest
from unittest.mock import MagicMock

from rv_experiment.experiment.workflow.result_manager import ResultManager


class TestResultManager:
    """INV-EXP-11: ResultManager generates instrumentation errors JSON."""

    def test_no_completed_tasks_early_return(self, tmp_results_dir):
        """INV-EXP-11: no completed tasks → early return, no file written."""
        mock_storage = MagicMock()
        mock_storage.get_tasks.return_value = []

        manager = ResultManager(tmp_results_dir, mock_storage)
        manager.generate_reports()

        # No completed tasks → early return before file creation
        errors_file = os.path.join(tmp_results_dir, "instrument_errors.json")
        assert not os.path.exists(errors_file)

    def test_generates_empty_errors_file(self, tmp_results_dir):
        """INV-EXP-11: completed tasks with no errors → empty JSON object."""
        from rv_android_core.domain.task import TaskState

        mock_task = MagicMock()
        mock_task.result.state = TaskState.COMPLETED
        mock_task.result.instrument_errors = None
        mock_task.config.apk_name = "app1.apk"
        mock_task.config.tool_config.get_full_tool_name.return_value = "monkey:default"

        mock_storage = MagicMock()
        mock_storage.get_tasks.return_value = [mock_task]

        manager = ResultManager(tmp_results_dir, mock_storage)
        manager.generate_reports()

        errors_file = os.path.join(tmp_results_dir, "instrument_errors.json")
        assert os.path.exists(errors_file)

        with open(errors_file) as f:
            data = json.load(f)
        assert data == {}

    def test_generates_errors_with_actual_errors(self, tmp_results_dir):
        """INV-EXP-11: instrument_errors.json contains APK-keyed errors."""
        from rv_android_core.domain.task import TaskState

        mock_task = MagicMock()
        mock_task.result.state = TaskState.COMPLETED
        mock_task.result.instrument_errors = {"error": "compilation failed"}
        mock_task.config.apk_name = "app1.apk"
        mock_task.config.tool_config.get_full_tool_name.return_value = "monkey:default"

        mock_storage = MagicMock()
        mock_storage.get_tasks.return_value = [mock_task]

        manager = ResultManager(tmp_results_dir, mock_storage)
        manager.generate_reports()

        errors_file = os.path.join(tmp_results_dir, "instrument_errors.json")
        assert os.path.exists(errors_file)

        with open(errors_file) as f:
            data = json.load(f)
        assert "app1.apk" in data
        assert data["app1.apk"]["error"] == "compilation failed"

    def test_get_experiment_metadata_initially_empty(self, tmp_results_dir):
        """ResultManager metadata is empty before generate_reports."""
        mock_storage = MagicMock()
        mock_storage.get_tasks.return_value = []

        manager = ResultManager(tmp_results_dir, mock_storage)
        assert manager.get_experiment_metadata() == {}

    def test_results_dir_created_if_missing(self, tmp_path):
        """ResultManager creates results_dir if it doesn't exist."""
        new_dir = str(tmp_path / "new_results")
        mock_storage = MagicMock()
        mock_storage.get_tasks.return_value = []

        manager = ResultManager(new_dir, mock_storage)
        assert os.path.isdir(new_dir)
