"""
Unit tests for NavigationGuidance.

Tests the unified abstraction for algorithm and LLM navigation guidance.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.services.navigation_guidance import ExplorationContext, NavigationGuidance
from rv_agent.services.transition_manager import TransitionManager
from rv_android_core.domain.static import StaticAnalysisData
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_static_analysis.parser.static.static_analysis_parser import parse_file

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fixtures_path():
    """Path to test fixtures."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def static_analysis_path(fixtures_path):
    """Path to static analysis fixtures."""
    return fixtures_path / "static_analysis" / "cryptoapp"


@pytest.fixture
def static_data(static_analysis_path) -> StaticAnalysisData:
    """Load real static analysis data from unified JSON."""
    json_file = str(static_analysis_path / "cryptoapp.apk.json")
    return parse_file(json_file)


@pytest.fixture
def dynamic_graph():
    """Create empty dynamic state graph."""
    return DynamicStateGraph()


@pytest.fixture
def transition_manager(static_data, dynamic_graph):
    """Create TransitionManager with static data."""
    return TransitionManager(static_data, dynamic_graph)


@pytest.fixture
def navigation_guidance(transition_manager):
    """Create NavigationGuidance with TransitionManager."""
    return NavigationGuidance(transition_manager)


@pytest.fixture
def mock_screen_description():
    """Create mock ScreenDescription for testing."""
    screen_desc = MagicMock(spec=ScreenDescription)
    screen_desc.activity = "br.unb.cic.cryptoapp.MainActivity"
    screen_desc.items = []
    screen_desc.events_by_id = {}
    return screen_desc


# =============================================================================
# Test: ExplorationContext
# =============================================================================


class TestExplorationContext:
    """Test ExplorationContext dataclass."""

    def test_default_context_has_no_guidance(self):
        """Default context has no guidance."""
        context = ExplorationContext()

        assert context.has_guidance is False
        assert context.unvisited_screens == []
        assert context.suggested_actions == []
        assert context.priority_targets == []

    def test_has_unvisited_property(self):
        """has_unvisited property works correctly."""
        context_empty = ExplorationContext()
        context_with_screens = ExplorationContext(
            unvisited_screens=["ActivityA", "ActivityB"]
        )

        assert context_empty.has_unvisited is False
        assert context_with_screens.has_unvisited is True

    def test_coverage_percent_property(self):
        """coverage_percent property extracts from exploration_progress."""
        context = ExplorationContext(exploration_progress={"coverage_percent": 45.5})

        assert context.coverage_percent == 45.5

    def test_coverage_percent_defaults_to_zero(self):
        """coverage_percent defaults to 0 when not set."""
        context = ExplorationContext()

        assert context.coverage_percent == 0.0


# =============================================================================
# Test: NavigationGuidance Initialization
# =============================================================================


class TestNavigationGuidanceInit:
    """Test NavigationGuidance initialization."""

    def test_init_with_transition_manager(self, transition_manager):
        """Guidance initializes with TransitionManager."""
        guidance = NavigationGuidance(transition_manager)

        assert guidance.transition_manager is transition_manager
        assert guidance.is_enabled is True

    def test_init_without_transition_manager(self):
        """Guidance initializes gracefully without TransitionManager."""
        guidance = NavigationGuidance(None)

        assert guidance.transition_manager is None
        assert guidance.is_enabled is False

    def test_is_enabled_property(self, transition_manager):
        """is_enabled property reflects TransitionManager availability."""
        guidance_enabled = NavigationGuidance(transition_manager)
        guidance_disabled = NavigationGuidance(None)

        assert guidance_enabled.is_enabled is True
        assert guidance_disabled.is_enabled is False


# =============================================================================
# Test: Get Context
# =============================================================================


class TestGetContext:
    """Test get_context method."""

    def test_get_context_returns_exploration_context(
        self, navigation_guidance, mock_screen_description
    ):
        """get_context returns ExplorationContext."""
        context = navigation_guidance.get_context(mock_screen_description)

        assert isinstance(context, ExplorationContext)

    def test_get_context_with_static_data_has_guidance(
        self, navigation_guidance, mock_screen_description
    ):
        """get_context with static data has guidance flag."""
        context = navigation_guidance.get_context(mock_screen_description)

        # MainActivity should have transitions
        assert context.has_guidance is True

    def test_get_context_finds_unvisited_screens(
        self, navigation_guidance, mock_screen_description
    ):
        """get_context finds unvisited screens from WTG."""
        context = navigation_guidance.get_context(mock_screen_description)

        # MainActivity should have transitions to other screens
        assert len(context.unvisited_screens) > 0

    def test_get_context_disabled_returns_empty_context(self, mock_screen_description):
        """get_context when disabled returns empty context."""
        guidance = NavigationGuidance(None)
        context = guidance.get_context(mock_screen_description)

        assert context.has_guidance is False
        assert context.unvisited_screens == []

    def test_get_context_error_handling(self, transition_manager):
        """get_context handles errors gracefully."""
        guidance = NavigationGuidance(transition_manager)

        # Create screen_desc that might cause errors
        bad_screen = MagicMock(spec=ScreenDescription)
        bad_screen.activity = None  # Invalid activity
        bad_screen.items = []
        bad_screen.events_by_id = {}

        context = guidance.get_context(bad_screen)

        # Should return empty context instead of raising
        assert isinstance(context, ExplorationContext)


# =============================================================================
# Test: Format for LLM
# =============================================================================


class TestFormatForLLM:
    """Test format_for_llm method."""

    def test_format_empty_context_returns_empty_string(self, navigation_guidance):
        """format_for_llm with empty context returns empty string."""
        context = ExplorationContext(has_guidance=False)

        result = navigation_guidance.format_for_llm(context)

        assert result == ""

    def test_format_with_unvisited_screens(self, navigation_guidance):
        """format_for_llm includes unvisited screens."""
        context = ExplorationContext(
            has_guidance=True, unvisited_screens=["SettingsActivity", "HelpActivity"]
        )

        result = navigation_guidance.format_for_llm(context)

        assert "Navigation guidance:" in result
        assert "Unvisited screens reachable:" in result
        assert "SettingsActivity" in result or "Settings" in result

    def test_format_limits_unvisited_screens_to_three(self, navigation_guidance):
        """format_for_llm limits displayed screens to 3."""
        context = ExplorationContext(
            has_guidance=True, unvisited_screens=[f"Activity{i}" for i in range(10)]
        )

        result = navigation_guidance.format_for_llm(context)

        # Should show "+7 more"
        assert "+7 more" in result

    def test_format_includes_priority_targets(self, navigation_guidance):
        """format_for_llm includes priority targets (monitored operations)."""
        context = ExplorationContext(
            has_guidance=True,
            unvisited_screens=["ActivityA"],
            priority_targets=["CipherActivity"],
        )

        result = navigation_guidance.format_for_llm(context)

        assert "Priority targets (monitored operations):" in result
        assert "CipherActivity" in result or "Cipher" in result

    def test_format_includes_suggested_action(self, navigation_guidance):
        """format_for_llm includes suggested action."""
        context = ExplorationContext(
            has_guidance=True,
            unvisited_screens=["SettingsActivity"],
            suggested_actions=[
                {
                    "action_type": "click",
                    "action_text": "Settings button",
                    "target_activity": "SettingsActivity",
                }
            ],
        )

        result = navigation_guidance.format_for_llm(context)

        assert "Suggested:" in result
        assert "Settings" in result

    def test_format_includes_exploration_progress(self, navigation_guidance):
        """format_for_llm includes exploration progress."""
        context = ExplorationContext(
            has_guidance=True,
            unvisited_screens=["ActivityA"],
            exploration_progress={"coverage_percent": 33.3},
        )

        result = navigation_guidance.format_for_llm(context)

        assert "Exploration progress:" in result
        assert "33%" in result


# =============================================================================
# Test: Format for LLM Compact
# =============================================================================


class TestFormatForLLMCompact:
    """Test format_for_llm_compact method."""

    def test_compact_format_empty_context(self, navigation_guidance):
        """Compact format returns empty for empty context."""
        context = ExplorationContext(has_guidance=False)

        result = navigation_guidance.format_for_llm_compact(context)

        assert result == ""

    def test_compact_format_with_screens(self, navigation_guidance):
        """Compact format returns one-line hint."""
        context = ExplorationContext(
            has_guidance=True, unvisited_screens=["SettingsActivity", "HelpActivity"]
        )

        result = navigation_guidance.format_for_llm_compact(context)

        assert "Hint:" in result
        assert "2 unvisited screens" in result

    def test_compact_format_with_suggested_action(self, navigation_guidance):
        """Compact format includes action text when available."""
        context = ExplorationContext(
            has_guidance=True,
            unvisited_screens=["SettingsActivity"],
            suggested_actions=[
                {"action_text": "Settings", "target_activity": "SettingsActivity"}
            ],
        )

        result = navigation_guidance.format_for_llm_compact(context)

        assert "Settings" in result
        assert "leads to" in result


# =============================================================================
# Test: Get Summary
# =============================================================================


class TestGetSummary:
    """Test get_summary method."""

    def test_summary_when_disabled(self):
        """Summary returns enabled=False when disabled."""
        guidance = NavigationGuidance(None)

        summary = guidance.get_summary()

        assert summary == {"enabled": False}

    def test_summary_when_enabled(self, navigation_guidance, mock_screen_description):
        """Summary includes exploration metrics when enabled."""
        # Get context first to populate visited activities
        navigation_guidance.get_context(mock_screen_description)

        summary = navigation_guidance.get_summary()

        assert summary["enabled"] is True
        assert "visited_count" in summary or "visited_activities" in summary


# =============================================================================
# Test: Activity Name Formatting
# =============================================================================


class TestActivityNameFormatting:
    """Test _format_activity_name helper."""

    def test_format_full_activity_name(self, navigation_guidance):
        """Formats full activity path to simple name."""
        result = navigation_guidance._format_activity_name(
            "com.example.app.settings.SettingsActivity"
        )

        assert result == "SettingsActivity"

    def test_format_relative_activity_name(self, navigation_guidance):
        """Formats relative activity name."""
        result = navigation_guidance._format_activity_name(".MainActivity")

        assert result == "MainActivity"

    def test_format_empty_activity(self, navigation_guidance):
        """Handles empty activity name."""
        result = navigation_guidance._format_activity_name("")

        assert result == "unknown"

    def test_format_none_activity(self, navigation_guidance):
        """Handles None activity name."""
        result = navigation_guidance._format_activity_name(None)

        assert result == "unknown"


# =============================================================================
# Test: Integration with Real Data
# =============================================================================


class TestIntegrationWithRealData:
    """Integration tests with real static analysis data."""

    def test_full_workflow(self, navigation_guidance, mock_screen_description):
        """Test complete workflow: get context, format for LLM."""
        # Get context
        context = navigation_guidance.get_context(mock_screen_description)

        # Should have guidance from real static data
        assert context.has_guidance is True
        assert len(context.unvisited_screens) > 0

        # Format for LLM
        llm_text = navigation_guidance.format_for_llm(context)

        # Should produce valid guidance text
        assert "Navigation guidance:" in llm_text
        assert "Unvisited screens" in llm_text

    def test_consecutive_contexts(self, navigation_guidance, mock_screen_description):
        """Test getting context multiple times."""
        # First context
        context1 = navigation_guidance.get_context(mock_screen_description)

        # Second context (activity marked as visited)
        context2 = navigation_guidance.get_context(mock_screen_description)

        # Both should succeed
        assert isinstance(context1, ExplorationContext)
        assert isinstance(context2, ExplorationContext)
