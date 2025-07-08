# tests/event/test_utils.py
"""
Tests for event utility functions.

This module tests the utility functions that provide event filtering,
grouping, search, and analysis capabilities across the event system.
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from rv_android_core.event.models import Event, EventType, TaskEvent, ExperimentEvent, AnalysisEvent
from rv_android_core.event.utils import (
    filter_events_by_task,
    filter_events_by_experiment,
    filter_events_by_type,
    filter_events_by_source,
    filter_events_by_time_range,
    group_events_by_type,
    find_related_task_events,
    extract_task_timeline,
    find_unique_task_ids,
    find_unique_experiment_ids
)


class TestEventFiltering:
    """Test cases for event filtering functions."""

    def setup_method(self):
        """Set up test events for filtering tests."""
        self.base_time = datetime.now()
        
        # Create test events
        self.task_events = [
            TaskEvent(
                type=EventType.TASK_STARTED,
                task_id="task-1",
                source="executor",
                timestamp=self.base_time
            ),
            TaskEvent(
                type=EventType.TASK_COMPLETED,
                task_id="task-1",
                source="executor",
                timestamp=self.base_time + timedelta(minutes=5)
            ),
            TaskEvent(
                type=EventType.TASK_STARTED,
                task_id="task-2",
                source="manager",
                timestamp=self.base_time + timedelta(minutes=10)
            ),
            TaskEvent(
                type=EventType.TASK_FAILED,
                task_id="task-2",
                source="executor",
                timestamp=self.base_time + timedelta(minutes=15)
            )
        ]
        
        self.experiment_events = [
            ExperimentEvent(
                type=EventType.EXPERIMENT_STARTED,
                experiment_id="exp-1",
                affected_tasks=["task-1", "task-2"],
                source="controller",
                timestamp=self.base_time - timedelta(minutes=5)
            ),
            ExperimentEvent(
                type=EventType.EXPERIMENT_COMPLETED,
                experiment_id="exp-1",
                affected_tasks=["task-1"],
                source="controller",
                timestamp=self.base_time + timedelta(minutes=20)
            )
        ]
        
        self.analysis_events = [
            AnalysisEvent(
                type=EventType.COVERAGE_UPDATED,
                related_task_id="task-1",
                data={"coverage": 85.5},
                source="analyzer",
                timestamp=self.base_time + timedelta(minutes=7)
            ),
            AnalysisEvent(
                type=EventType.MOP_ERROR_DETECTED,
                related_task_id="task-2",
                data={"error_type": "timeout"},
                source="monitor",
                timestamp=self.base_time + timedelta(minutes=12)
            )
        ]
        
        self.all_events = self.task_events + self.experiment_events + self.analysis_events

    def test_filter_events_by_task(self):
        """Test filtering events by specific task ID."""
        # Filter for task-1
        task_1_events = filter_events_by_task(self.all_events, "task-1")
        
        assert len(task_1_events) == 2
        assert all(isinstance(event, TaskEvent) for event in task_1_events)
        assert all(event.task_id == "task-1" for event in task_1_events)
        
        # Filter for task-2
        task_2_events = filter_events_by_task(self.all_events, "task-2")
        
        assert len(task_2_events) == 2
        assert all(event.task_id == "task-2" for event in task_2_events)
        
        # Filter for non-existent task
        empty_result = filter_events_by_task(self.all_events, "task-999")
        assert len(empty_result) == 0

    def test_filter_events_by_experiment(self):
        """Test filtering events by specific experiment ID."""
        # Filter for exp-1
        exp_1_events = filter_events_by_experiment(self.all_events, "exp-1")
        
        assert len(exp_1_events) == 2
        assert all(isinstance(event, ExperimentEvent) for event in exp_1_events)
        assert all(event.experiment_id == "exp-1" for event in exp_1_events)
        
        # Filter for non-existent experiment
        empty_result = filter_events_by_experiment(self.all_events, "exp-999")
        assert len(empty_result) == 0

    def test_filter_events_by_type(self):
        """Test filtering events by event type."""
        # Filter for TASK_STARTED events
        started_events = filter_events_by_type(self.all_events, EventType.TASK_STARTED)
        
        assert len(started_events) == 2
        assert all(event.type == EventType.TASK_STARTED for event in started_events)
        
        # Filter for COVERAGE_UPDATED events
        coverage_events = filter_events_by_type(self.all_events, EventType.COVERAGE_UPDATED)
        
        assert len(coverage_events) == 1
        assert coverage_events[0].type == EventType.COVERAGE_UPDATED
        
        # Filter for non-existent event type
        config_events = filter_events_by_type(self.all_events, EventType.CONFIG_LOADED)
        assert len(config_events) == 0

    def test_filter_events_by_source(self):
        """Test filtering events by source."""
        # Filter for executor events
        executor_events = filter_events_by_source(self.all_events, "executor")
        
        assert len(executor_events) == 3
        assert all(event.source == "executor" for event in executor_events)
        
        # Filter for controller events
        controller_events = filter_events_by_source(self.all_events, "controller")
        
        assert len(controller_events) == 2
        assert all(event.source == "controller" for event in controller_events)
        
        # Filter for non-existent source
        empty_result = filter_events_by_source(self.all_events, "unknown_source")
        assert len(empty_result) == 0

    def test_filter_events_by_time_range(self):
        """Test filtering events by time range."""
        # Filter for events in first 10 minutes
        start_time = self.base_time - timedelta(minutes=1)
        end_time = self.base_time + timedelta(minutes=10)
        
        early_events = filter_events_by_time_range(
            self.all_events, 
            start_time=start_time, 
            end_time=end_time
        )
        
        # Count events that should be in this range:
        # exp_start(-5), task_1_start(0), task_1_complete(+5), coverage_update(+7), task_2_start(+10)
        # But exp_start is at -5, which is before start_time (-1), so it won't be included
        # So we expect: task_1_start(0), task_1_complete(+5), coverage_update(+7), task_2_start(+10) = 4 events
        assert len(early_events) == 4
        
        # Filter with only start time
        recent_events = filter_events_by_time_range(
            self.all_events,
            start_time=self.base_time + timedelta(minutes=10)
        )
        
        assert len(recent_events) == 4  # task_2_start, error_detected, task_2_failed, experiment_completed
        
        # Filter with only end time
        old_events = filter_events_by_time_range(
            self.all_events,
            end_time=self.base_time + timedelta(minutes=5)
        )
        
        assert len(old_events) == 3  # experiment_start, task_1_start, task_1_complete
        
        # Filter for empty range
        empty_range = filter_events_by_time_range(
            self.all_events,
            start_time=self.base_time + timedelta(hours=1),
            end_time=self.base_time + timedelta(hours=2)
        )
        
        assert len(empty_range) == 0


class TestEventGrouping:
    """Test cases for event grouping functions."""

    def setup_method(self):
        """Set up test events for grouping tests."""
        self.events = [
            Event(type=EventType.TASK_STARTED, source="test"),
            Event(type=EventType.TASK_STARTED, source="test"),
            Event(type=EventType.TASK_COMPLETED, source="test"),
            Event(type=EventType.EXPERIMENT_STARTED, source="test"),
            Event(type=EventType.COVERAGE_UPDATED, source="test"),
            Event(type=EventType.COVERAGE_UPDATED, source="test"),
            Event(type=EventType.COVERAGE_UPDATED, source="test"),
        ]

    def test_group_events_by_type(self):
        """Test grouping events by their EventType."""
        grouped = group_events_by_type(self.events)
        
        assert len(grouped) == 4  # 4 different event types
        
        # Check TASK_STARTED group
        assert EventType.TASK_STARTED in grouped
        assert len(grouped[EventType.TASK_STARTED]) == 2
        
        # Check TASK_COMPLETED group
        assert EventType.TASK_COMPLETED in grouped
        assert len(grouped[EventType.TASK_COMPLETED]) == 1
        
        # Check EXPERIMENT_STARTED group
        assert EventType.EXPERIMENT_STARTED in grouped
        assert len(grouped[EventType.EXPERIMENT_STARTED]) == 1
        
        # Check COVERAGE_UPDATED group
        assert EventType.COVERAGE_UPDATED in grouped
        assert len(grouped[EventType.COVERAGE_UPDATED]) == 3

    def test_group_events_by_type_empty_list(self):
        """Test grouping empty event list."""
        grouped = group_events_by_type([])
        assert len(grouped) == 0
        assert isinstance(grouped, dict)


class TestEventSearch:
    """Test cases for event search and analysis functions."""

    def setup_method(self):
        """Set up complex test events for search tests."""
        self.base_time = datetime.now()
        
        self.events = [
            # Task 1 events
            TaskEvent(
                type=EventType.TASK_STARTED,
                task_id="task-1",
                source="executor",
                timestamp=self.base_time
            ),
            TaskEvent(
                type=EventType.TASK_COMPLETED,
                task_id="task-1",
                source="executor",
                timestamp=self.base_time + timedelta(minutes=5)
            ),
            
            # Task 2 events
            TaskEvent(
                type=EventType.TASK_STARTED,
                task_id="task-2",
                source="executor",
                timestamp=self.base_time + timedelta(minutes=10)
            ),
            TaskEvent(
                type=EventType.TASK_FAILED,
                task_id="task-2",
                source="executor",
                timestamp=self.base_time + timedelta(minutes=15)
            ),
            
            # Experiment events
            ExperimentEvent(
                type=EventType.EXPERIMENT_STARTED,
                experiment_id="exp-1",
                affected_tasks=["task-1", "task-2"],
                source="controller",
                timestamp=self.base_time - timedelta(minutes=5)
            ),
            ExperimentEvent(
                type=EventType.EXPERIMENT_COMPLETED,
                experiment_id="exp-2",
                affected_tasks=["task-1"],
                source="controller",
                timestamp=self.base_time + timedelta(minutes=20)
            ),
            
            # Analysis events
            AnalysisEvent(
                type=EventType.COVERAGE_UPDATED,
                related_task_id="task-1",
                data={"coverage": 85.5},
                source="analyzer",
                timestamp=self.base_time + timedelta(minutes=7)
            ),
            AnalysisEvent(
                type=EventType.MOP_ERROR_DETECTED,
                related_task_id="task-2",
                data={"error_type": "timeout"},
                source="monitor",
                timestamp=self.base_time + timedelta(minutes=12)
            ),
            AnalysisEvent(
                type=EventType.STATIC_ANALYSIS_COMPLETED,
                related_task_id=None,
                data={"methods_found": 150},
                source="static_analyzer",
                timestamp=self.base_time + timedelta(minutes=25)
            )
        ]

    def test_find_related_task_events(self):
        """Test finding all events related to a specific task."""
        # Find events related to task-1
        task_1_related = find_related_task_events(self.events, "task-1")
        
        # Should include: TaskEvents for task-1, AnalysisEvent for task-1, ExperimentEvents affecting task-1
        # Let's count what should be included:
        # - 2 TaskEvents (STARTED, COMPLETED)  
        # - 1 AnalysisEvent (COVERAGE_UPDATED)
        # - 2 ExperimentEvents (both exp-1 and exp-2 affect task-1)
        assert len(task_1_related) == 5
        
        # Verify event types
        task_events = [e for e in task_1_related if isinstance(e, TaskEvent)]
        analysis_events = [e for e in task_1_related if isinstance(e, AnalysisEvent)]
        experiment_events = [e for e in task_1_related if isinstance(e, ExperimentEvent)]
        
        assert len(task_events) == 2  # STARTED and COMPLETED
        assert len(analysis_events) == 1  # COVERAGE_UPDATED
        assert len(experiment_events) == 2  # Both EXPERIMENT_STARTED and EXPERIMENT_COMPLETED affect task-1

    def test_find_related_task_events_with_multiple_relationships(self):
        """Test finding events for task that appears in multiple experiment events."""
        # Find events related to task-2
        task_2_related = find_related_task_events(self.events, "task-2")
        
        # Should include: TaskEvents for task-2, AnalysisEvent for task-2, ExperimentEvent affecting task-2
        # Let's count what should be included:
        # - 2 TaskEvents (STARTED, FAILED)
        # - 1 AnalysisEvent (MOP_ERROR_DETECTED)
        # - 1 ExperimentEvent (exp-1 affects task-2)
        assert len(task_2_related) == 4
        
        # Check specific events
        task_events = [e for e in task_2_related if isinstance(e, TaskEvent)]
        analysis_events = [e for e in task_2_related if isinstance(e, AnalysisEvent)]
        experiment_events = [e for e in task_2_related if isinstance(e, ExperimentEvent)]
        
        assert len(task_events) == 2  # STARTED and FAILED
        assert len(analysis_events) == 1  # MOP_ERROR_DETECTED
        assert len(experiment_events) == 1  # EXPERIMENT_STARTED affects task-2

    def test_extract_task_timeline(self):
        """Test extracting chronological timeline for a task."""
        timeline = extract_task_timeline(self.events, "task-1")
        
        # Should be sorted chronologically
        timestamps = [event.timestamp for event in timeline]
        assert timestamps == sorted(timestamps)
        
        # Check timeline content - should include all task-1 related events
        # exp_start(-5), task_1_start(0), task_1_complete(+5), coverage_update(+7), exp_complete(+20)
        assert len(timeline) == 5
        
        # First event should be experiment start (earliest timestamp)
        assert timeline[0].type == EventType.EXPERIMENT_STARTED
        
        # Last event should be experiment completion (latest timestamp)
        assert timeline[-1].type == EventType.EXPERIMENT_COMPLETED

    def test_extract_task_timeline_empty_result(self):
        """Test extracting timeline for non-existent task."""
        timeline = extract_task_timeline(self.events, "task-999")
        assert len(timeline) == 0

    def test_find_unique_task_ids(self):
        """Test finding all unique task IDs mentioned in events."""
        task_ids = find_unique_task_ids(self.events)
        
        assert isinstance(task_ids, set)
        assert len(task_ids) == 2
        assert "task-1" in task_ids
        assert "task-2" in task_ids

    def test_find_unique_task_ids_with_none_values(self):
        """Test finding task IDs when some events have None task IDs."""
        # Add an analysis event without task ID
        events_with_none = self.events.copy()
        
        task_ids = find_unique_task_ids(events_with_none)
        
        # Should only include actual task IDs, not None values
        assert len(task_ids) == 2
        assert "task-1" in task_ids
        assert "task-2" in task_ids
        assert None not in task_ids

    def test_find_unique_experiment_ids(self):
        """Test finding all unique experiment IDs mentioned in events."""
        experiment_ids = find_unique_experiment_ids(self.events)
        
        assert isinstance(experiment_ids, set)
        assert len(experiment_ids) == 2
        assert "exp-1" in experiment_ids
        assert "exp-2" in experiment_ids

    def test_find_unique_experiment_ids_empty_list(self):
        """Test finding experiment IDs from empty event list."""
        experiment_ids = find_unique_experiment_ids([])
        
        assert isinstance(experiment_ids, set)
        assert len(experiment_ids) == 0


class TestUtilityFunctionEdgeCases:
    """Test edge cases and error scenarios for utility functions."""

    def test_functions_with_empty_lists(self):
        """Test all utility functions with empty event lists."""
        empty_events = []
        
        # Filtering functions
        assert len(filter_events_by_task(empty_events, "task-1")) == 0
        assert len(filter_events_by_experiment(empty_events, "exp-1")) == 0
        assert len(filter_events_by_type(empty_events, EventType.TASK_STARTED)) == 0
        assert len(filter_events_by_source(empty_events, "source")) == 0
        assert len(filter_events_by_time_range(empty_events, datetime.now())) == 0
        
        # Grouping functions
        assert len(group_events_by_type(empty_events)) == 0
        
        # Search functions
        assert len(find_related_task_events(empty_events, "task-1")) == 0
        assert len(extract_task_timeline(empty_events, "task-1")) == 0
        assert len(find_unique_task_ids(empty_events)) == 0
        assert len(find_unique_experiment_ids(empty_events)) == 0

    def test_functions_with_mixed_event_types(self):
        """Test functions with mixed event types including base Event objects."""
        mixed_events = [
            Event(type=EventType.CONFIG_LOADED, source="config"),
            TaskEvent(type=EventType.TASK_STARTED, task_id="task-1", source="executor"),
            ExperimentEvent(type=EventType.EXPERIMENT_STARTED, experiment_id="exp-1", 
                           affected_tasks=["task-1"], source="controller"),
            AnalysisEvent(type=EventType.COVERAGE_UPDATED, related_task_id="task-1", 
                         data={}, source="analyzer")
        ]
        
        # Test filtering functions work with mixed types
        task_events = filter_events_by_task(mixed_events, "task-1")
        assert len(task_events) == 1
        assert isinstance(task_events[0], TaskEvent)
        
        # Test grouping works with mixed types
        grouped = group_events_by_type(mixed_events)
        assert len(grouped) == 4
        
        # Test search functions work with mixed types
        related = find_related_task_events(mixed_events, "task-1")
        assert len(related) == 3  # TaskEvent, ExperimentEvent, AnalysisEvent
        
        task_ids = find_unique_task_ids(mixed_events)
        assert len(task_ids) == 1
        assert "task-1" in task_ids

    def test_time_filtering_edge_cases(self):
        """Test time filtering with edge cases."""
        now = datetime.now()
        events = [
            Event(type=EventType.TASK_STARTED, source="test", timestamp=now),
            Event(type=EventType.TASK_COMPLETED, source="test", timestamp=now + timedelta(seconds=1))
        ]
        
        # Test exact timestamp boundaries
        exact_match = filter_events_by_time_range(events, start_time=now, end_time=now)
        assert len(exact_match) == 1
        
        # Test microsecond precision
        precise_match = filter_events_by_time_range(
            events, 
            start_time=now + timedelta(microseconds=1),
            end_time=now + timedelta(seconds=1)
        )
        assert len(precise_match) == 1