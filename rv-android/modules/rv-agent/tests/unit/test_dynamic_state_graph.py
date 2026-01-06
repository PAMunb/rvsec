"""
DynamicStateGraph rigorous unit tests.

Tests state tracking, coordinate-based action identification, coverage computation,
transition history, and graph reporting with comprehensive scenarios.
"""

import pytest
import time
from unittest.mock import MagicMock

from rv_agent.agent.dynamic_state_graph import (
    DynamicStateGraph,
    ScreenNode,
    Transition,
    compute_screen_hash_from_description,
)
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ScreenItem


pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def graph():
    """Fresh DynamicStateGraph instance."""
    return DynamicStateGraph()


@pytest.fixture
def empty_screen_desc():
    """Empty screen description."""
    return ScreenDescription(
        activity="com.test.app/.MainActivity",
        items=[],
        events_by_id={}
    )


@pytest.fixture
def screen_desc_with_items():
    """Screen description with interactive items."""
    items = []
    for i in range(5):
        item = MagicMock(spec=ScreenItem)
        item.view = {
            "class": "android.widget.Button",
            "resource-id": f"com.test.app:id/button_{i}",
            "package": "com.test.app",
            "clickable": True,
            "scrollable": False,
            "checkable": False,
            "enabled": True,
            "long-clickable": False,
            "editable": False,
            "bounds": [[0, i*100], [100, (i+1)*100]],
        }
        item.get_all_actions = MagicMock(return_value=[MagicMock()])
        items.append(item)

    desc = MagicMock(spec=ScreenDescription)
    desc.activity = "com.test.app/.MainActivity"
    desc.items = items
    desc.get_all_actions = MagicMock(return_value=[MagicMock() for _ in range(5)])
    return desc


# =============================================================================
# ScreenNode Tests
# =============================================================================

class TestScreenNode:
    """Test ScreenNode class."""

    def test_create_node(self):
        """ScreenNode creates with correct attributes."""
        node = ScreenNode(
            screen_hash="abc123def456",
            activity="MainActivity",
            visit_count=1,
            total_actions=10
        )

        assert node.screen_hash == "abc123def456"
        assert node.activity == "MainActivity"
        assert node.visit_count == 1
        assert node.total_actions == 10
        assert len(node.executed_actions) == 0

    def test_coverage_zero_actions(self):
        """Coverage is 0 when no actions available."""
        node = ScreenNode(
            screen_hash="test",
            activity="Main",
            total_actions=0
        )

        assert node.get_coverage() == 0.0

    def test_coverage_no_executed(self):
        """Coverage is 0 when no actions executed."""
        node = ScreenNode(
            screen_hash="test",
            activity="Main",
            total_actions=10
        )

        assert node.get_coverage() == 0.0

    def test_coverage_partial(self):
        """Coverage is correctly calculated with partial execution."""
        node = ScreenNode(
            screen_hash="test",
            activity="Main",
            total_actions=10
        )

        # Execute 3 actions
        node.record_action(((100, 200), "click"))
        node.record_action(((150, 250), "click"))
        node.record_action(((200, 300), "long_click"))

        assert node.get_coverage() == 0.3  # 3/10

    def test_coverage_full(self):
        """Coverage is 1.0 when all actions executed."""
        node = ScreenNode(
            screen_hash="test",
            activity="Main",
            total_actions=3
        )

        node.record_action(((100, 200), "click"))
        node.record_action(((150, 250), "click"))
        node.record_action(((200, 300), "click"))

        assert node.get_coverage() == 1.0

    def test_record_action_deduplication(self):
        """Same action signature is not recorded twice."""
        node = ScreenNode(
            screen_hash="test",
            activity="Main",
            total_actions=5
        )

        signature = ((100, 200), "click")

        node.record_action(signature)
        node.record_action(signature)  # Duplicate
        node.record_action(signature)  # Duplicate

        assert len(node.executed_actions) == 1
        assert node.get_coverage() == 0.2  # 1/5

    def test_is_action_executed(self):
        """is_action_executed correctly identifies executed actions."""
        node = ScreenNode(
            screen_hash="test",
            activity="Main",
            total_actions=5
        )

        sig1 = ((100, 200), "click")
        sig2 = ((150, 250), "click")

        node.record_action(sig1)

        assert node.is_action_executed(sig1) is True
        assert node.is_action_executed(sig2) is False

    def test_action_signature_includes_type(self):
        """Different action types at same coords are distinct."""
        node = ScreenNode(
            screen_hash="test",
            activity="Main",
            total_actions=5
        )

        click_sig = ((100, 200), "click")
        long_click_sig = ((100, 200), "long_click")

        node.record_action(click_sig)

        assert node.is_action_executed(click_sig) is True
        assert node.is_action_executed(long_click_sig) is False


# =============================================================================
# ScreenNode Execution Count Tests
# =============================================================================

class TestScreenNodeExecutionCount:
    """Test ScreenNode execution count tracking for continuous exploration."""

    def test_execution_count_starts_zero(self):
        """Execution count is 0 for unexecuted actions."""
        node = ScreenNode(screen_hash="test", activity="Main", total_actions=5)
        sig = ((100, 200), "click")

        assert node.get_action_execution_count(sig) == 0

    def test_execution_count_increments(self):
        """Execution count increments with each record_action call."""
        node = ScreenNode(screen_hash="test", activity="Main", total_actions=5)
        sig = ((100, 200), "click")

        node.record_action(sig)
        assert node.get_action_execution_count(sig) == 1

        node.record_action(sig)
        assert node.get_action_execution_count(sig) == 2

        node.record_action(sig)
        assert node.get_action_execution_count(sig) == 3

    def test_execution_count_independent_per_action(self):
        """Each action has independent execution count."""
        node = ScreenNode(screen_hash="test", activity="Main", total_actions=5)
        sig1 = ((100, 200), "click")
        sig2 = ((150, 250), "click")

        node.record_action(sig1)
        node.record_action(sig1)
        node.record_action(sig2)

        assert node.get_action_execution_count(sig1) == 2
        assert node.get_action_execution_count(sig2) == 1


# =============================================================================
# ScreenNode Failed Actions Tracking Tests
# =============================================================================

class TestScreenNodeFailedActionsTracking:
    """Test ScreenNode failed actions tracking for crash avoidance."""

    def test_action_not_failed_initially(self):
        """Actions are not marked as failed initially."""
        node = ScreenNode(screen_hash="test", activity="Main", total_actions=5)
        sig = ((100, 200), "click")

        assert node.is_action_failed(sig) is False
        assert node.get_action_failure_count(sig) == 0

    def test_single_failure_not_permanent(self):
        """Single failure does not mark action as permanently failed."""
        node = ScreenNode(screen_hash="test", activity="Main", total_actions=5)
        sig = ((100, 200), "click")

        node.record_action_failure(sig)

        assert node.is_action_failed(sig) is False
        assert node.get_action_failure_count(sig) == 1

    def test_two_failures_not_permanent(self):
        """Two failures still not permanent (tolerance = 3)."""
        node = ScreenNode(screen_hash="test", activity="Main", total_actions=5)
        sig = ((100, 200), "click")

        node.record_action_failure(sig)
        node.record_action_failure(sig)

        assert node.is_action_failed(sig) is False
        assert node.get_action_failure_count(sig) == 2

    def test_three_failures_marks_permanent(self):
        """Three failures marks action as permanently failed."""
        node = ScreenNode(screen_hash="test", activity="Main", total_actions=5)
        sig = ((100, 200), "click")

        node.record_action_failure(sig)
        node.record_action_failure(sig)
        node.record_action_failure(sig)

        assert node.is_action_failed(sig) is True
        assert node.get_action_failure_count(sig) == 3
        assert sig in node.failed_actions

    def test_reset_failure_clears_count(self):
        """reset_action_failure clears failure count."""
        node = ScreenNode(screen_hash="test", activity="Main", total_actions=5)
        sig = ((100, 200), "click")

        node.record_action_failure(sig)
        node.record_action_failure(sig)
        assert node.get_action_failure_count(sig) == 2

        node.reset_action_failure(sig)
        assert node.get_action_failure_count(sig) == 0

    def test_reset_failure_does_not_affect_permanent(self):
        """reset_action_failure does not remove from failed_actions set."""
        node = ScreenNode(screen_hash="test", activity="Main", total_actions=5)
        sig = ((100, 200), "click")

        # Mark as permanently failed
        for _ in range(3):
            node.record_action_failure(sig)

        assert node.is_action_failed(sig) is True

        # Reset clears count but action remains permanently failed
        node.reset_action_failure(sig)
        assert node.is_action_failed(sig) is True  # Still in failed_actions

    def test_failure_tracking_independent_per_action(self):
        """Each action has independent failure tracking."""
        node = ScreenNode(screen_hash="test", activity="Main", total_actions=5)
        sig1 = ((100, 200), "click")
        sig2 = ((150, 250), "click")

        # Fail sig1 permanently
        for _ in range(3):
            node.record_action_failure(sig1)

        # Fail sig2 once
        node.record_action_failure(sig2)

        assert node.is_action_failed(sig1) is True
        assert node.is_action_failed(sig2) is False
        assert node.get_action_failure_count(sig1) == 3
        assert node.get_action_failure_count(sig2) == 1


# =============================================================================
# DynamicStateGraph State Management Tests
# =============================================================================

class TestGraphStateManagement:
    """Test DynamicStateGraph state management."""

    def test_empty_graph(self, graph):
        """New graph has no states or transitions."""
        assert len(graph.states) == 0
        assert len(graph.transitions) == 0
        assert len(graph.current_trace) == 0

    def test_create_new_state(self, graph, empty_screen_desc):
        """get_or_create_state creates new state node."""
        node = graph.get_or_create_state(
            screen_hash="hash1",
            activity="MainActivity",
            screen_desc=empty_screen_desc
        )

        assert node.screen_hash == "hash1"
        assert node.activity == "MainActivity"
        assert node.visit_count == 1
        assert "hash1" in graph.states

    def test_get_existing_state(self, graph, empty_screen_desc):
        """get_or_create_state returns existing state and increments visit."""
        node1 = graph.get_or_create_state("hash1", "Main", empty_screen_desc)
        node2 = graph.get_or_create_state("hash1", "Main", empty_screen_desc)

        assert node1 is node2
        assert node1.visit_count == 2
        assert len(graph.states) == 1

    def test_visit_count_accumulates(self, graph, empty_screen_desc):
        """Visit count accumulates across multiple visits."""
        for i in range(5):
            graph.get_or_create_state("hash1", "Main", empty_screen_desc)

        assert graph.states["hash1"].visit_count == 5

    def test_multiple_distinct_states(self, graph, empty_screen_desc):
        """Graph tracks multiple distinct states."""
        for i in range(3):
            graph.get_or_create_state(f"hash{i}", f"Activity{i}", empty_screen_desc)

        assert len(graph.states) == 3
        assert all(f"hash{i}" in graph.states for i in range(3))

    def test_total_actions_captured(self, graph, screen_desc_with_items):
        """Total actions are captured from screen description."""
        node = graph.get_or_create_state(
            screen_hash="hash1",
            activity="Main",
            screen_desc=screen_desc_with_items
        )

        assert node.total_actions == 5


# =============================================================================
# DynamicStateGraph Action Recording Tests
# =============================================================================

class TestGraphActionRecording:
    """Test action recording in DynamicStateGraph."""

    def test_record_action_existing_state(self, graph, empty_screen_desc):
        """record_action succeeds for existing state."""
        graph.get_or_create_state("hash1", "Main", empty_screen_desc)

        graph.record_action("hash1", ((100, 200), "click"))

        node = graph.states["hash1"]
        assert ((100, 200), "click") in node.executed_actions

    def test_record_action_nonexistent_state(self, graph):
        """record_action handles nonexistent state gracefully."""
        # Should not raise exception
        graph.record_action("nonexistent", ((100, 200), "click"))

        assert "nonexistent" not in graph.states

    def test_record_action_to_trace(self, graph):
        """record_action_to_trace adds to current trace."""
        action1 = {"type": "click", "x": 100, "y": 200}
        action2 = {"type": "scroll", "direction": "down"}

        graph.record_action_to_trace(action1)
        graph.record_action_to_trace(action2)

        assert len(graph.current_trace) == 2
        assert graph.current_trace[0] == action1
        assert graph.current_trace[1] == action2


# =============================================================================
# DynamicStateGraph Transition Tests
# =============================================================================

class TestGraphTransitions:
    """Test transition recording in DynamicStateGraph."""

    def test_record_transition_basic(self, graph, empty_screen_desc):
        """record_transition creates transition with action sequence."""
        graph.get_or_create_state("hash1", "Main", empty_screen_desc)
        graph.get_or_create_state("hash2", "Detail", empty_screen_desc)

        # Add actions to trace
        graph.record_action_to_trace({"type": "click", "x": 100})
        graph.record_action_to_trace({"type": "click", "x": 200})

        graph.record_transition("hash1", "hash2")

        assert len(graph.transitions) == 1
        t = graph.transitions[0]
        assert t.from_hash == "hash1"
        assert t.to_hash == "hash2"
        assert len(t.action_sequence) == 2

    def test_record_transition_clears_trace(self, graph, empty_screen_desc):
        """record_transition clears current trace."""
        graph.get_or_create_state("hash1", "Main", empty_screen_desc)
        graph.get_or_create_state("hash2", "Detail", empty_screen_desc)

        graph.record_action_to_trace({"type": "click"})
        graph.record_transition("hash1", "hash2")

        assert len(graph.current_trace) == 0

    def test_record_transition_timestamp(self, graph, empty_screen_desc):
        """record_transition records timestamp."""
        graph.get_or_create_state("hash1", "Main", empty_screen_desc)
        graph.get_or_create_state("hash2", "Detail", empty_screen_desc)

        before = time.time()
        graph.record_transition("hash1", "hash2")
        after = time.time()

        t = graph.transitions[0]
        assert before <= t.timestamp <= after

    def test_record_transition_custom_timestamp(self, graph, empty_screen_desc):
        """record_transition accepts custom timestamp."""
        graph.get_or_create_state("hash1", "Main", empty_screen_desc)
        graph.get_or_create_state("hash2", "Detail", empty_screen_desc)

        custom_time = 1234567890.0
        graph.record_transition("hash1", "hash2", timestamp=custom_time)

        assert graph.transitions[0].timestamp == custom_time

    def test_multiple_transitions(self, graph, empty_screen_desc):
        """Graph records multiple transitions."""
        for i in range(4):
            graph.get_or_create_state(f"hash{i}", f"Activity{i}", empty_screen_desc)

        # Record transitions: 0->1, 1->2, 2->3
        graph.record_transition("hash0", "hash1")
        graph.record_transition("hash1", "hash2")
        graph.record_transition("hash2", "hash3")

        assert len(graph.transitions) == 3


# =============================================================================
# DynamicStateGraph Untested Actions Tests
# =============================================================================

class TestGraphUntestedActions:
    """Test untested action retrieval."""

    def test_get_untested_all_untested(self, graph, empty_screen_desc):
        """All actions returned when none executed."""
        graph.get_or_create_state("hash1", "Main", empty_screen_desc)

        mock_actions = [MagicMock() for _ in range(5)]
        for i, action in enumerate(mock_actions):
            action.coords_for_matching = ((i*100, 200), "click")

        untested = graph.get_untested_actions("hash1", mock_actions)

        assert len(untested) == 5

    def test_get_untested_some_executed(self, graph, empty_screen_desc):
        """Only untested actions returned."""
        graph.get_or_create_state("hash1", "Main", empty_screen_desc)

        mock_actions = [MagicMock() for _ in range(5)]
        for i, action in enumerate(mock_actions):
            action.coords_for_matching = ((i*100, 200), "click")

        # Execute first 2 actions
        graph.record_action("hash1", ((0, 200), "click"))
        graph.record_action("hash1", ((100, 200), "click"))

        untested = graph.get_untested_actions("hash1", mock_actions)

        assert len(untested) == 3

    def test_get_untested_nonexistent_state(self, graph):
        """All actions returned for nonexistent state."""
        mock_actions = [MagicMock() for _ in range(3)]

        untested = graph.get_untested_actions("nonexistent", mock_actions)

        assert len(untested) == 3

    def test_is_action_executed_check(self, graph, empty_screen_desc):
        """is_action_executed correctly queries state."""
        graph.get_or_create_state("hash1", "Main", empty_screen_desc)

        sig = ((100, 200), "click")
        graph.record_action("hash1", sig)

        assert graph.is_action_executed("hash1", sig) is True
        assert graph.is_action_executed("hash1", ((999, 999), "click")) is False
        assert graph.is_action_executed("nonexistent", sig) is False


# =============================================================================
# DynamicStateGraph Coverage and Metrics Tests
# =============================================================================

class TestGraphCoverageMetrics:
    """Test coverage computation and metrics."""

    def test_get_coverage_summary_empty(self, graph):
        """Coverage summary empty for empty graph."""
        summary = graph.get_coverage_summary()
        assert summary == {}

    def test_get_coverage_summary(self, graph, empty_screen_desc):
        """Coverage summary returns per-state coverage."""
        # Create 2 states with different coverage
        node1 = graph.get_or_create_state("hash1", "Main", empty_screen_desc)
        node1.total_actions = 10
        node1.record_action(((100, 200), "click"))  # 10%

        node2 = graph.get_or_create_state("hash2", "Detail", empty_screen_desc)
        node2.total_actions = 4
        node2.record_action(((100, 200), "click"))
        node2.record_action(((200, 300), "click"))  # 50%

        summary = graph.get_coverage_summary()

        assert abs(summary["hash1"] - 10.0) < 0.01
        assert abs(summary["hash2"] - 50.0) < 0.01

    def test_get_avg_coverage_empty(self, graph):
        """Average coverage is 0 for empty graph."""
        assert graph.get_avg_coverage() == 0.0

    def test_get_avg_coverage(self, graph, empty_screen_desc):
        """Average coverage correctly computed."""
        # State 1: 20% coverage
        node1 = graph.get_or_create_state("hash1", "Main", empty_screen_desc)
        node1.total_actions = 10
        node1.record_action(((100, 200), "click"))
        node1.record_action(((200, 300), "click"))

        # State 2: 50% coverage
        node2 = graph.get_or_create_state("hash2", "Detail", empty_screen_desc)
        node2.total_actions = 4
        node2.record_action(((100, 200), "click"))
        node2.record_action(((200, 300), "click"))

        # Average: (20 + 50) / 2 = 35%
        avg = graph.get_avg_coverage()
        assert abs(avg - 35.0) < 0.01


# =============================================================================
# DynamicStateGraph Report Generation Tests
# =============================================================================

class TestGraphReportGeneration:
    """Test report generation."""

    def test_transition_graph_report_empty(self, graph):
        """Report generation works for empty graph."""
        report = graph.get_transition_graph_report()

        assert report["total_states"] == 0
        assert report["total_transitions"] == 0
        assert report["avg_coverage"] == 0.0
        assert report["states"] == []
        assert report["transitions"] == []

    def test_transition_graph_report_complete(self, graph, empty_screen_desc):
        """Report contains all expected fields."""
        # Setup states
        node1 = graph.get_or_create_state("hash1", "Main", empty_screen_desc)
        node1.total_actions = 10
        node1.record_action(((100, 200), "click"))

        node2 = graph.get_or_create_state("hash2", "Detail", empty_screen_desc)

        # Record transition
        graph.record_action_to_trace({"type": "click", "x": 100})
        graph.record_transition("hash1", "hash2")

        report = graph.get_transition_graph_report()

        assert report["total_states"] == 2
        assert report["total_transitions"] == 1
        assert report["avg_coverage"] >= 0

        # State details
        assert len(report["states"]) == 2
        state_report = next(s for s in report["states"] if s["screen_hash"] == "hash1")
        assert state_report["activity"] == "Main"
        assert state_report["visit_count"] == 1
        assert state_report["total_actions"] == 10
        assert state_report["executed_count"] == 1

        # Transition details
        assert len(report["transitions"]) == 1
        t_report = report["transitions"][0]
        assert t_report["from"] == "hash1"
        assert t_report["to"] == "hash2"
        assert t_report["action_count"] == 1


# =============================================================================
# Screen Hash Computation Tests
# =============================================================================

class TestScreenHashComputation:
    """Test compute_screen_hash_from_description function."""

    def test_hash_deterministic(self, screen_desc_with_items):
        """Same screen description produces same hash."""
        hash1 = compute_screen_hash_from_description(screen_desc_with_items)
        hash2 = compute_screen_hash_from_description(screen_desc_with_items)

        assert hash1 == hash2

    def test_hash_length(self, screen_desc_with_items):
        """Hash is 12 characters."""
        screen_hash = compute_screen_hash_from_description(screen_desc_with_items)
        assert len(screen_hash) == 12

    def test_hash_hex_format(self, screen_desc_with_items):
        """Hash is valid hexadecimal."""
        screen_hash = compute_screen_hash_from_description(screen_desc_with_items)
        # Should not raise
        int(screen_hash, 16)

    def test_different_activities_different_hash(self):
        """Different activities produce different hashes."""
        desc1 = MagicMock(spec=ScreenDescription)
        desc1.activity = "MainActivity"
        desc1.items = []

        desc2 = MagicMock(spec=ScreenDescription)
        desc2.activity = "DetailActivity"
        desc2.items = []

        hash1 = compute_screen_hash_from_description(desc1)
        hash2 = compute_screen_hash_from_description(desc2)

        assert hash1 != hash2

    def test_different_items_different_hash(self):
        """Different UI items produce different hashes."""
        item1 = MagicMock()
        item1.view = {
            "class": "Button",
            "resource-id": "btn1",
            "package": "test",
            "clickable": True,
            "scrollable": False,
            "checkable": False,
            "enabled": True,
            "long-clickable": False,
            "editable": False,
        }

        item2 = MagicMock()
        item2.view = {
            "class": "Button",
            "resource-id": "btn2",  # Different ID
            "package": "test",
            "clickable": True,
            "scrollable": False,
            "checkable": False,
            "enabled": True,
            "long-clickable": False,
            "editable": False,
        }

        desc1 = MagicMock(spec=ScreenDescription)
        desc1.activity = "Main"
        desc1.items = [item1]

        desc2 = MagicMock(spec=ScreenDescription)
        desc2.activity = "Main"
        desc2.items = [item2]

        hash1 = compute_screen_hash_from_description(desc1)
        hash2 = compute_screen_hash_from_description(desc2)

        assert hash1 != hash2

    def test_hash_ignores_text_content(self):
        """Hash ignores text and content-desc (volatile data)."""
        item1 = MagicMock()
        item1.view = {
            "class": "TextView",
            "resource-id": "text1",
            "package": "test",
            "clickable": False,
            "scrollable": False,
            "checkable": False,
            "enabled": True,
            "long-clickable": False,
            "editable": False,
            "text": "Hello World",  # Should be ignored
            "content-desc": "Description 1",  # Should be ignored
        }

        item2 = MagicMock()
        item2.view = {
            "class": "TextView",
            "resource-id": "text1",
            "package": "test",
            "clickable": False,
            "scrollable": False,
            "checkable": False,
            "enabled": True,
            "long-clickable": False,
            "editable": False,
            "text": "Different Text",  # Should be ignored
            "content-desc": "Description 2",  # Should be ignored
        }

        desc1 = MagicMock(spec=ScreenDescription)
        desc1.activity = "Main"
        desc1.items = [item1]

        desc2 = MagicMock(spec=ScreenDescription)
        desc2.activity = "Main"
        desc2.items = [item2]

        hash1 = compute_screen_hash_from_description(desc1)
        hash2 = compute_screen_hash_from_description(desc2)

        # Same structural properties = same hash
        assert hash1 == hash2


# =============================================================================
# Transition Dataclass Tests
# =============================================================================

class TestTransitionDataclass:
    """Test Transition dataclass."""

    def test_create_transition(self):
        """Transition creates with correct attributes."""
        actions = [{"type": "click"}, {"type": "scroll"}]
        t = Transition(
            from_hash="hash1",
            to_hash="hash2",
            action_sequence=actions,
            timestamp=1234567890.0
        )

        assert t.from_hash == "hash1"
        assert t.to_hash == "hash2"
        assert len(t.action_sequence) == 2
        assert t.timestamp == 1234567890.0
