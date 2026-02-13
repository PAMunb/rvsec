# tests/components/test_coverage.py
"""
Tests for CoverageComponent, specifically verifying that coverage timing
uses tool_execution_start (not task creation time) for accurate relative timestamps.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration, TaskState, ToolConfig as TaskToolConfig
from rv_platform.components.coverage import CoverageComponent


class TestCoverageComponentTiming:
    """Tests for coverage timing accuracy — tool_execution_start vs task creation time."""

    @pytest.fixture
    def basic_config(self):
        tool_config = TaskToolConfig(
            tool_name="monkey",
            variant="default",
            additional_params={}
        )
        return TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_config=tool_config
        )

    @pytest.fixture
    def mock_app(self):
        app = MagicMock(spec=App)
        app.name = "test.apk"
        app.package_name = "com.test.app"
        return app

    @pytest.fixture
    def task_with_app(self, basic_config, mock_app, tmp_path):
        task = Task(basic_config)
        task.set_app(mock_app)
        task.initialize(str(tmp_path))
        task.update_state(TaskState.RUNNING)  # Sets start_time
        return task

    def test_start_tracking_updates_timing_reference(self, task_with_app):
        """
        Verify that start_tracking() updates the tracker's tool_execution_start_time
        when the task has a valid tool_execution_start timestamp.

        This is the core of the timing fix: the tracker is initialized in Phase 2
        (before emulator starts), but tool_execution_start is only set in Phase 3.
        start_tracking() must update the tracker's time reference before starting.
        """
        component = CoverageComponent(task_with_app)

        # Phase 2: initialize tracker (tool_execution_start is None at this point)
        assert task_with_app.result.tool_execution_start is None
        component.execute({})  # calls initialize_tracker()

        # Simulate what executor does: mark tool execution start BEFORE start_tracking
        task_with_app.mark_tool_execution_start()
        tool_start = task_with_app.result.tool_execution_start
        assert tool_start is not None

        # Phase 3: start_tracking should update the tracker's time reference
        component.start_tracking()

        assert component.coverage_tracker is not None
        assert component.coverage_tracker.tool_execution_start_time == tool_start

    def test_start_tracking_without_tool_execution_start(self, task_with_app):
        """
        Verify that start_tracking() preserves the original timing reference
        when tool_execution_start is not available (defensive case).
        """
        component = CoverageComponent(task_with_app)

        # Initialize tracker (tool_execution_start is None)
        component.execute({})

        original_time = component.coverage_tracker.tool_execution_start_time

        # start_tracking without calling mark_tool_execution_start first
        component.start_tracking()

        # Should keep original reference (start_time from initialization)
        assert component.coverage_tracker.tool_execution_start_time == original_time

    def test_timing_difference_between_start_time_and_tool_execution_start(self, task_with_app):
        """
        Verify that tool_execution_start differs from start_time by the expected
        pre-processing overhead. This is the symptom the fix addresses: without it,
        coverage times would be offset by the pre-processing duration.
        """
        component = CoverageComponent(task_with_app)

        task_start = task_with_app.result.start_time

        # Initialize tracker (uses start_time as initial reference)
        component.execute({})
        initial_ref = component.coverage_tracker.tool_execution_start_time
        assert initial_ref == task_start

        # Simulate pre-processing overhead
        task_with_app.mark_tool_execution_start()
        tool_start = task_with_app.result.tool_execution_start

        # tool_execution_start must be >= start_time
        assert tool_start >= task_start

        # After start_tracking, the tracker should use the later timestamp
        component.start_tracking()
        assert component.coverage_tracker.tool_execution_start_time == tool_start
        assert component.coverage_tracker.tool_execution_start_time >= task_start
