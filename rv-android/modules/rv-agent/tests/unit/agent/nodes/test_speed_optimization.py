"""
Unit tests for speed optimization features (gh26 Group 7).

Tests screen_desc caching in parse_node:
- Cached value reused when screen hash is unchanged
- New screen_desc computed when hash changes
- Cache invalidated when force_restart_app triggers app restart

Tests RVTRACK:STRATEGY logging in decision_node:
- Strategy log emitted when routing to algorithm path
"""

import logging
import pytest
from unittest.mock import MagicMock, patch

from rv_agent.agent.nodes.parse_node import parse_ui_node
from rv_agent.agent.nodes.learn_node import learn_node


def _make_parse_agent(error_detection_enabled=False):
    """Create a mock agent for parse_node with screen_desc cache support."""
    agent = MagicMock()
    agent.config.error_detection_enabled = error_detection_enabled
    agent.config.package_name = "com.example.app"
    agent.ui_coverage = MagicMock()
    # Initialize the cache attribute (same as RVAgent.__init__)
    agent._cached_screen_desc = None
    return agent


def _make_screen_processor_result(screen_hash="hash_abc", screen_desc=None):
    """Create a standard parse_current_screen return dict."""
    if screen_desc is None:
        screen_desc = MagicMock(items=[])
    return {
        "screen_hash": screen_hash,
        "activity": "MainActivity",
        "screen_description": screen_desc,
        "ui_elements_text": "1. Button 'Submit' at (200, 400) - bounds [[100, 350], [300, 450]]",
        "is_external": False,
        "external_navigation_count": 0,
        "ui_xml": "<hierarchy></hierarchy>",
    }


def _make_learn_agent(
    error_detection_enabled=True,
    error_recovery_count=0,
    stuck_screen_count=0,
    last_screen_hash="prev_hash",
):
    """Create a mock agent for learn_node with screen_desc cache support."""
    mock_memory_coordinator = MagicMock()
    mock_memory_coordinator.update_memories.return_value = {"recent_action_window": []}
    mock_memory_coordinator.generate_summaries.return_value = {
        "action_history_summary": "",
        "exploration_summary": "",
        "memory_insights": "",
        "navigation_path": "",
    }
    mock_memory_coordinator.track_state_discovery.return_value = {
        "visited_states": [],
        "state_transitions": [],
    }
    mock_memory_coordinator.check_continuation.return_value = {"should_continue": True}

    mock_config = MagicMock()
    mock_config.error_detection_enabled = error_detection_enabled
    mock_config.error_detection_confidence = 0.7
    mock_config.error_max_indicator_size = 80
    mock_config.error_max_indicator_count = 5

    mock_agent = MagicMock()
    mock_agent.memory_coordinator = mock_memory_coordinator
    mock_agent.config = mock_config
    mock_agent.stuck_screen_count = stuck_screen_count
    mock_agent.last_screen_hash = last_screen_hash
    mock_agent.error_recovery_count = error_recovery_count
    mock_agent.BASE_STUCK_THRESHOLD = 8
    mock_agent.STUCK_THRESHOLD_FACTOR = 1.5
    mock_agent._cached_screen_desc = MagicMock()  # Start with a cached value
    return mock_agent


class TestScreenDescCacheOnSameHash:
    """Cached screen_desc is reused when screen hash is unchanged."""

    def test_screen_desc_cache_on_same_hash(self):
        """When screen_hash == previous_screen_hash and cache exists,
        the cached screen_desc is returned instead of the freshly parsed one."""
        agent = _make_parse_agent()
        cached_desc = MagicMock(items=[MagicMock(), MagicMock()])
        agent._cached_screen_desc = cached_desc

        # parse_current_screen returns a NEW screen_desc, but we expect the cached one
        fresh_desc = MagicMock(items=[MagicMock()])
        agent.screen_processor.parse_current_screen.return_value = (
            _make_screen_processor_result(
                screen_hash="same_hash", screen_desc=fresh_desc
            )
        )

        state = {
            "iteration": 5,
            "external_navigation_count": 0,
            "previous_screen_hash": "same_hash",
        }

        result = parse_ui_node(agent, state)

        # The cached description is used, not the fresh one
        assert result["screen_description"] is cached_desc
        # Cache is NOT updated (still the old value)
        assert agent._cached_screen_desc is cached_desc


class TestScreenDescCacheInvalidatedOnHashChange:
    """New screen_desc is computed when screen hash changes."""

    def test_screen_desc_cache_invalidated_on_hash_change(self):
        """When screen_hash differs from previous_screen_hash,
        the fresh screen_desc is used and cache is updated."""
        agent = _make_parse_agent()
        old_cached_desc = MagicMock(items=[])
        agent._cached_screen_desc = old_cached_desc

        fresh_desc = MagicMock(items=[MagicMock(), MagicMock(), MagicMock()])
        agent.screen_processor.parse_current_screen.return_value = (
            _make_screen_processor_result(
                screen_hash="new_hash", screen_desc=fresh_desc
            )
        )

        state = {
            "iteration": 3,
            "external_navigation_count": 0,
            "previous_screen_hash": "old_hash",
        }

        result = parse_ui_node(agent, state)

        # The fresh description is used
        assert result["screen_description"] is fresh_desc
        # Cache is updated with the fresh value
        assert agent._cached_screen_desc is fresh_desc

    def test_screen_desc_cache_populated_on_first_iteration(self):
        """On first iteration (no previous_screen_hash), cache is populated."""
        agent = _make_parse_agent()
        assert agent._cached_screen_desc is None

        fresh_desc = MagicMock(items=[MagicMock()])
        agent.screen_processor.parse_current_screen.return_value = (
            _make_screen_processor_result(
                screen_hash="first_hash", screen_desc=fresh_desc
            )
        )

        state = {
            "iteration": 0,
            "external_navigation_count": 0,
            # No previous_screen_hash
        }

        result = parse_ui_node(agent, state)

        assert result["screen_description"] is fresh_desc
        assert agent._cached_screen_desc is fresh_desc


class TestScreenDescCacheInvalidatedOnRestart:
    """force_restart_app in learn_node clears the screen_desc cache."""

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_screen_desc_cache_invalidated_on_restart(self, mock_detect):
        """When Level 2 stuck triggers force_restart_app=True,
        agent._cached_screen_desc is set to None."""
        mock_detect.return_value = None

        agent = _make_learn_agent()
        assert agent._cached_screen_desc is not None  # Pre-condition: cache exists

        # Set up Level 2 stuck recovery to trigger restart
        mock_stuck_recovery = MagicMock()
        mock_stuck_recovery.check.return_value = "restart"
        agent.stuck_recovery = mock_stuck_recovery

        # No successor_tracker -> goes straight to restart
        agent.strategy = MagicMock(spec=[])  # No successor_tracker attribute

        state = {
            "current_screen_hash": "stuck_hash",
            "current_activity": ".StuckActivity",
            "iteration": 10,
            "error_detection_screenshot": None,
        }

        result = learn_node(agent, state)

        # force_restart_app should be set
        assert result.get("force_restart_app") is True
        # Cache should be cleared
        assert agent._cached_screen_desc is None

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_cache_not_cleared_on_force_back(self, mock_detect):
        """When Level 1 stuck triggers force_back (not restart),
        cache is NOT cleared since the app is still running."""
        mock_detect.return_value = None

        agent = _make_learn_agent(
            stuck_screen_count=7,  # Just below threshold
            last_screen_hash="stuck_hash",
        )
        agent.BASE_STUCK_THRESHOLD = 8
        agent.STUCK_THRESHOLD_FACTOR = 1.5
        cached_desc = MagicMock()
        agent._cached_screen_desc = cached_desc

        # No stuck_recovery triggering restart
        agent.stuck_recovery = MagicMock()
        agent.stuck_recovery.check.return_value = None

        state = {
            "current_screen_hash": "stuck_hash",
            "current_activity": ".StuckActivity",
            "iteration": 10,
            "error_detection_screenshot": None,
            "available_actions": [],  # 0 elements -> threshold = max(8, 0) = 8
        }

        result = learn_node(agent, state)

        # force_back should be set (stuck_screen_count was 7, incremented to 8 >= threshold 8)
        assert result.get("force_back_action") is True
        # Cache should NOT be cleared (BACK does not restart the app)
        assert agent._cached_screen_desc is cached_desc


class TestStrategyTracking:
    """Tests for [RVTRACK:STRATEGY] logging in decision_node."""

    def test_strategy_log_emitted_on_algorithm_routing(self, caplog):
        """When route_decision returns 'algorithm', RVTRACK:STRATEGY is logged."""
        from rv_agent.agent.nodes.decision_node import decision_router_node

        agent = MagicMock()
        agent.routing_manager.mode = "multimode"
        agent.routing_manager.forced_back_count = 0
        agent.routing_manager.route_decision.return_value = "algorithm"

        state = {"iteration": 5}

        with caplog.at_level(logging.INFO):
            result = decision_router_node(agent, state)

        assert result["decision_path"] == "algorithm"

        # Check that RVTRACK:STRATEGY was logged
        strategy_logs = [
            r.message for r in caplog.records if "RVTRACK:STRATEGY" in r.message
        ]
        assert len(strategy_logs) == 1
        assert "iter=5" in strategy_logs[0]
        assert "mode=multimode" in strategy_logs[0]

    def test_no_strategy_log_on_llm_routing(self, caplog):
        """When route_decision returns 'llm', no RVTRACK:STRATEGY is logged."""
        from rv_agent.agent.nodes.decision_node import decision_router_node

        agent = MagicMock()
        agent.routing_manager.mode = "multimode"
        agent.routing_manager.forced_back_count = 0
        agent.routing_manager.route_decision.return_value = "llm"

        state = {"iteration": 3}

        with caplog.at_level(logging.INFO):
            result = decision_router_node(agent, state)

        assert result["decision_path"] == "llm"

        strategy_logs = [
            r.message for r in caplog.records if "RVTRACK:STRATEGY" in r.message
        ]
        assert len(strategy_logs) == 0
