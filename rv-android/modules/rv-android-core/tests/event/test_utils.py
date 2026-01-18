
import pytest
from datetime import datetime, timedelta
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
    find_unique_experiment_ids,
)
from rv_android_core.event.models import (
    Event, EventType, TaskEvent, ExperimentEvent
)
from pydantic import Field

# Mock AnalysisEvent for testing purposes
class AnalysisEvent(Event):
    related_task_id: str = Field(...)

# Mock Events
@pytest.fixture
def sample_events():
    now = datetime.now()
    return [
        TaskEvent(type=EventType.TASK_STARTED, task_id="1", timestamp=now, source="test"),
        TaskEvent(type=EventType.TASK_COMPLETED, task_id="2", timestamp=now + timedelta(seconds=1), source="test"),
        ExperimentEvent(type=EventType.EXPERIMENT_STARTED, experiment_id="A", affected_tasks=["1"], timestamp=now + timedelta(seconds=2), source="exp"),
        AnalysisEvent(type=EventType.ANALYSIS_COMPLETED, related_task_id="1", timestamp=now + timedelta(seconds=3), source="analyzer"),
        Event(type=EventType.CUSTOM, timestamp=now + timedelta(seconds=4), source="system"),
    ]

def test_filter_events_by_task(sample_events):
    filtered = filter_events_by_task(sample_events, "1")
    assert len(filtered) == 1
    assert filtered[0].task_id == "1"

def test_filter_events_by_experiment(sample_events):
    filtered = filter_events_by_experiment(sample_events, "A")
    assert len(filtered) == 1
    assert filtered[0].experiment_id == "A"

def test_filter_events_by_type(sample_events):
    filtered = filter_events_by_type(sample_events, EventType.TASK_STARTED)
    assert len(filtered) == 1

def test_filter_events_by_source(sample_events):
    filtered = filter_events_by_source(sample_events, "exp")
    assert len(filtered) == 1
    assert isinstance(filtered[0], ExperimentEvent)

def test_filter_events_by_time_range(sample_events):
    now = sample_events[0].timestamp
    filtered = filter_events_by_time_range(sample_events, start_time=now + timedelta(seconds=1), end_time=now + timedelta(seconds=3))
    assert len(filtered) == 3

def test_group_events_by_type(sample_events):
    grouped = group_events_by_type(sample_events)
    assert len(grouped[EventType.TASK_STARTED]) == 1
    assert len(grouped[EventType.TASK_COMPLETED]) == 1
    assert len(grouped[EventType.EXPERIMENT_STARTED]) == 1
    assert len(grouped[EventType.ANALYSIS_COMPLETED]) == 1
    assert len(grouped[EventType.CUSTOM]) == 1

def test_find_related_task_events(sample_events):
    related = find_related_task_events(sample_events, "1")
    assert len(related) == 2

def test_extract_task_timeline(sample_events):
    timeline = extract_task_timeline(sample_events, "1")
    assert len(timeline) == 2
    assert timeline[0].timestamp < timeline[1].timestamp

def test_find_unique_task_ids(sample_events):
    task_ids = find_unique_task_ids(sample_events)
    assert task_ids == {"1", "2"}

def test_find_unique_experiment_ids(sample_events):
    exp_ids = find_unique_experiment_ids(sample_events)
    assert exp_ids == {"A"}
