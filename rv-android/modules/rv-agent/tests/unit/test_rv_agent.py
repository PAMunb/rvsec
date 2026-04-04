"""
Unit tests for RVAgent.

Tests the autonomous Android exploration agent including:
- Initialization and validation
- LangGraph workflow nodes
- Stuck state detection
- Deadlock escape
- Memory integration
- Execution loop
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.agent.nodes import (
    algorithm_node,
    capture_screenshot_node,
    decision_router_node,
    execute_node,
    learn_node,
    llm_generate_node,
    parse_ui_node,
    validate_action_node,
)
from rv_agent.agent.rv_agent import RVAgent
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.domain.action import ActionNormalizer
from rv_agent.execution.tool_executor import ToolExecutor
from rv_agent.llm.llm_client import LLMClient
from rv_agent.memory.memory_coordinator import MemoryCoordinator
from rv_agent.services.screen_analyzer import ScreenProcessor
from rv_agent.services.vision_service import ImageHandler
from rv_agent.strategies.base_strategy import ExplorationStrategy


@pytest.fixture
def agent_config():
    """Standard agent configuration."""
    config = MagicMock(spec=RVAgentConfig)
    config.get_agent_mode.return_value = "pure_algorithm"
    config.package_name = "com.example.app"
    config.strategy = "dfs"
    config.timeout = 100
    config.metrics_output_dir = None
    config.error_detection_enabled = True
    return config


@pytest.fixture
def mock_dependencies():
    """Standard mock dependencies."""
    # Create ActionNormalizer mock that properly normalizes LLM actions
    mock_action_normalizer = MagicMock(spec=ActionNormalizer)
    mock_action_normalizer.from_llm.side_effect = lambda raw: {
        "action_type": raw.get("tool_name", "CLICK").upper(),
        "x": raw.get("tool_args", {}).get("x", 0),
        "y": raw.get("tool_args", {}).get("y", 0),
        "text": raw.get("tool_args", {}).get("text", ""),
        "source": "llm",
    }

    mock_deps = {
        "device": MagicMock(spec=DeviceInterface),
        "dynamic_graph": MagicMock(spec=DynamicStateGraph),
        "exploration_strategy": MagicMock(spec=ExplorationStrategy),
        "image_handler": MagicMock(spec=ImageHandler),
        "screen_processor": MagicMock(spec=ScreenProcessor),
        "llm_client": MagicMock(spec=LLMClient),
        "routing_manager": MagicMock(),
        "tool_executor": MagicMock(spec=ToolExecutor),
        "memory_coordinator": MagicMock(spec=MemoryCoordinator),
        "action_normalizer": mock_action_normalizer,
    }
    mock_deps["routing_manager"].forced_back_count = 0
    mock_deps["routing_manager"].llm_executed = 0
    mock_deps["routing_manager"].algorithm_chosen = 0
    mock_deps["routing_manager"].llm_validation_failed = 0
    mock_deps["routing_manager"].get_decision_counters.return_value = {
        "total_actions": 0,
        "llm_executed": 0,
        "algorithm_chosen": 0,
        "llm_percentage": 0.0,
        "algorithm_percentage": 0.0,
        "llm_validation_failed": 0,
        "forced_back": 0,
        "primary_total": 0,
    }
    return mock_deps


@pytest.fixture
def agent(agent_config, mock_dependencies):
    """Pre-configured RVAgent instance."""
    return RVAgent(config=agent_config, **mock_dependencies)


class TestRVAgentInitialization:
    """Test RVAgent initialization and validation."""

    def test_initialization_stores_all_components(
        self, agent_config, mock_dependencies
    ):
        """Agent stores all injected dependencies."""
        agent = RVAgent(config=agent_config, **mock_dependencies)

        assert agent.config == agent_config
        assert agent.device == mock_dependencies["device"]
        assert agent.dynamic_graph == mock_dependencies["dynamic_graph"]
        assert agent.strategy == mock_dependencies["exploration_strategy"]
        assert agent.image_handler == mock_dependencies["image_handler"]
        assert agent.screen_processor == mock_dependencies["screen_processor"]
        assert agent.llm_client == mock_dependencies["llm_client"]
        assert agent.routing_manager == mock_dependencies["routing_manager"]
        assert agent.tool_executor == mock_dependencies["tool_executor"]
        assert agent.memory_coordinator == mock_dependencies["memory_coordinator"]

    def test_initialization_sets_detection_thresholds(
        self, agent_config, mock_dependencies
    ):
        """Agent initializes stuck and deadlock detection thresholds."""
        agent = RVAgent(config=agent_config, **mock_dependencies)

        assert agent.BASE_STUCK_THRESHOLD == 8
        assert agent.STUCK_THRESHOLD_FACTOR == 1.5
        assert agent.NO_ACTION_THRESHOLD == 3
        assert agent.stuck_screen_count == 0
        assert agent.consecutive_no_action == 0
        assert agent.last_screen_hash is None

    def test_initialization_builds_graph(self, agent_config, mock_dependencies):
        """Agent builds LangGraph workflow on init."""
        agent = RVAgent(config=agent_config, **mock_dependencies)

        assert agent.graph is not None

    def test_initialization_pure_algorithm_no_llm_client(
        self, agent_config, mock_dependencies
    ):
        """Pure algorithm mode works without LLM client."""
        mock_dependencies["llm_client"] = None

        agent = RVAgent(config=agent_config, **mock_dependencies)

        assert agent.llm_client is None

    def test_initialization_requires_llm_for_llm_only(
        self, agent_config, mock_dependencies
    ):
        """LLM-only mode requires LLM client."""
        agent_config.get_agent_mode.return_value = "llm_only"
        mock_dependencies["llm_client"] = None

        with pytest.raises(ValueError, match="LLM client required for mode: llm_only"):
            RVAgent(config=agent_config, **mock_dependencies)

    def test_initialization_requires_llm_for_multimode(
        self, agent_config, mock_dependencies
    ):
        """Multimode requires LLM client."""
        agent_config.get_agent_mode.return_value = "multimode"
        mock_dependencies["llm_client"] = None

        with pytest.raises(ValueError, match="LLM client required for mode: multimode"):
            RVAgent(config=agent_config, **mock_dependencies)

    def test_initialization_with_static_data(self, agent_config, mock_dependencies):
        """Agent accepts optional static analysis data."""
        static_data = MagicMock()

        agent = RVAgent(
            config=agent_config, static_data=static_data, **mock_dependencies
        )

        assert agent.static_data == static_data


class TestParseUINode:
    """Test parse_ui_node behavior."""

    def test_parse_ui_returns_screen_info(self, agent, mock_dependencies):
        """Parse UI extracts screen hash and activity."""
        mock_dependencies["screen_processor"].parse_current_screen.return_value = {
            "screen_hash": "hash123",
            "activity": "MainActivity",
            "screen_description": MagicMock(),
            "ui_elements_text": "1. Button 'Submit'",
            "is_external": False,
            "external_navigation_count": 0,
        }

        state = {"external_navigation_count": 0}
        result = parse_ui_node(agent, state)

        assert result["current_screen_hash"] == "hash123"
        assert result["current_activity"] == "MainActivity"
        assert result["ui_elements_text"] == "1. Button 'Submit'"
        assert result["is_external"] is False

    def test_parse_ui_detects_external_navigation(self, agent, mock_dependencies):
        """Parse UI detects external app navigation."""
        mock_dependencies["screen_processor"].parse_current_screen.return_value = {
            "screen_hash": "external_hash",
            "activity": "GooglePlay",
            "screen_description": None,
            "ui_elements_text": "",
            "is_external": True,
            "external_navigation_count": 1,
        }

        state = {"external_navigation_count": 0}
        result = parse_ui_node(agent, state)

        assert result["is_external"] is True
        assert result["external_navigation_count"] == 1

    def test_parse_ui_short_text_logs_warning(self, agent, mock_dependencies):
        """Parse UI logs warning for short UI text."""
        mock_dependencies["screen_processor"].parse_current_screen.return_value = {
            "screen_hash": "hash",
            "activity": "Empty",
            "screen_description": None,
            "ui_elements_text": "short",
            "is_external": False,
            "external_navigation_count": 0,
        }

        state = {}
        result = parse_ui_node(agent, state)

        assert len(result["ui_elements_text"]) < 50


class TestDecisionRouterNode:
    """Test decision_router_node behavior."""

    def test_routes_to_algorithm(self, agent, mock_dependencies):
        """Router returns algorithm path."""
        mock_dependencies["routing_manager"].route_decision.return_value = "algorithm"

        state = {"iteration": 1}
        result = decision_router_node(agent, state)

        assert result["decision_path"] == "algorithm"
        assert result["decision_maker"] == "algorithm"

    def test_routes_to_llm(self, agent, mock_dependencies):
        """Router returns LLM path."""
        mock_dependencies["routing_manager"].route_decision.return_value = "llm"

        state = {"iteration": 1}
        result = decision_router_node(agent, state)

        assert result["decision_path"] == "llm"
        assert result["decision_maker"] == "llm"

    def test_force_back_overrides_routing(self, agent, mock_dependencies):
        """Force back flag overrides normal routing."""
        mock_dependencies["routing_manager"].route_decision.return_value = "llm"

        state = {"iteration": 1, "force_back_action": True}
        result = decision_router_node(agent, state)

        assert result["decision_path"] == "algorithm"
        assert result["decision_maker"] == "stuck_recovery"
        # Counter is NOT incremented in decision_node (moved to algorithm_node)
        assert agent.routing_manager.forced_back_count == 0

    def test_force_back_increments_counter(self, agent, mock_dependencies):
        """Force back does NOT increment forced_back_count in decision_node.

        Counter increment was moved to algorithm_node (Group 25.4).
        decision_router_node only routes to algorithm path.
        """
        agent.routing_manager.forced_back_count = 0

        state = {"iteration": 1, "force_back_action": True}

        decision_router_node(agent, state)
        # Counter stays 0 — decision_node only routes, does not count
        assert agent.routing_manager.forced_back_count == 0

        decision_router_node(agent, state)
        # Still 0 after second call
        assert agent.routing_manager.forced_back_count == 0


class TestAlgorithmNode:
    """Test algorithm_node behavior."""

    def test_returns_action_from_strategy(self, agent, mock_dependencies):
        """Algorithm node returns action from strategy."""
        item_action = MagicMock()
        item_action.get_execution_coordinates.return_value = (100, 200)
        item_action.action_type = "CLICK"
        item_action.id = "btn_submit"
        item_action.text = "Submit"
        mock_dependencies["exploration_strategy"].select_next_action.return_value = (
            item_action
        )

        state = {"current_screen_hash": "hash1", "screen_description": MagicMock()}
        result = algorithm_node(agent, state)

        assert result["current_action"]["action_type"] == "CLICK"
        assert result["current_action"]["x"] == 100
        assert result["current_action"]["y"] == 200
        assert result["decision_maker"] == "algorithm"

    def test_force_back_returns_back_action(self, agent, mock_dependencies):
        """Force back flag generates BACK action."""
        state = {"force_back_action": True}
        result = algorithm_node(agent, state)

        assert result["current_action"]["action_type"] == "BACK"
        assert result["current_action"]["reason"] == "stuck_state_recovery"
        assert result["force_back_action"] is False  # Flag cleared

    def test_deadlock_detected_forces_back(self, agent, mock_dependencies):
        """Deadlock threshold triggers BACK action."""
        agent.consecutive_no_action = 3  # At threshold

        state = {"current_screen_hash": "hash1", "screen_description": MagicMock()}
        result = algorithm_node(agent, state)

        assert result["current_action"]["action_type"] == "BACK"
        assert result["current_action"]["reason"] == "deadlock_escape"
        assert agent.consecutive_no_action == 0

    def test_no_action_increments_counter(self, agent, mock_dependencies):
        """No action increments consecutive_no_action counter."""
        mock_dependencies["exploration_strategy"].select_next_action.return_value = None

        state = {"current_screen_hash": "hash1", "screen_description": MagicMock()}
        algorithm_node(agent, state)

        assert agent.consecutive_no_action == 1

    def test_no_coordinates_returns_end(self, agent, mock_dependencies):
        """Action without coordinates ends iteration."""
        item_action = MagicMock()
        item_action.get_execution_coordinates.return_value = None
        mock_dependencies["exploration_strategy"].select_next_action.return_value = (
            item_action
        )

        state = {"current_screen_hash": "hash1", "screen_description": MagicMock()}
        result = algorithm_node(agent, state)

        assert result["current_action"] is None
        assert result["decision_path"] == "end"

    def test_resets_deadlock_counter_on_action(self, agent, mock_dependencies):
        """Successful action resets deadlock counter."""
        agent.consecutive_no_action = 2

        item_action = MagicMock()
        item_action.get_execution_coordinates.return_value = (100, 200)
        item_action.action_type = "CLICK"
        item_action.id = "btn"
        item_action.text = ""
        mock_dependencies["exploration_strategy"].select_next_action.return_value = (
            item_action
        )

        state = {"current_screen_hash": "hash1", "screen_description": MagicMock()}
        algorithm_node(agent, state)

        assert agent.consecutive_no_action == 0


class TestCaptureScreenshotNode:
    """Test capture_screenshot_node behavior."""

    def test_captures_and_optimizes_screenshot(self, agent, mock_dependencies):
        """Captures screenshot and returns base64."""
        mock_dependencies["device"].take_screenshot.return_value = "/tmp/screenshot.png"
        mock_dependencies["image_handler"].optimize.return_value = "base64_data"

        state = {}
        result = capture_screenshot_node(agent, state)

        assert result["screenshot_b64"] == "base64_data"
        mock_dependencies["device"].take_screenshot.assert_called_once()
        mock_dependencies["image_handler"].optimize.assert_called_with(
            image_path="/tmp/screenshot.png", quality=90
        )

    def test_optimization_failure_returns_end(self, agent, mock_dependencies):
        """Optimization failure ends iteration."""
        mock_dependencies["device"].take_screenshot.return_value = "/tmp/screenshot.png"
        mock_dependencies["image_handler"].optimize.return_value = None

        state = {}
        result = capture_screenshot_node(agent, state)

        assert result["screenshot_b64"] == ""
        assert result["decision_path"] == "end"

    def test_capture_exception_returns_end(self, agent, mock_dependencies):
        """Screenshot capture exception ends iteration."""
        mock_dependencies["device"].take_screenshot.side_effect = Exception(
            "Device error"
        )

        state = {}
        result = capture_screenshot_node(agent, state)

        assert result["screenshot_b64"] == ""
        assert result["decision_path"] == "end"


class TestLLMGenerateNode:
    """Test llm_generate_node behavior."""

    def test_calls_llm_with_context(self, agent, mock_dependencies):
        """LLM node calls generate_action with context."""
        # Create a mock response object with tool_calls attribute
        mock_response = MagicMock()
        mock_response.tool_calls = [
            {"name": "click", "args": {"x": 100, "y": 200, "text": "button"}}
        ]
        mock_response.content = "Clicking the button"

        mock_dependencies["llm_client"].generate_action.return_value = {
            "response": mock_response,
            "success": True,
            "tokens_input": 1000,
            "tokens_output": 50,
            "time_ms": 500,
        }

        state = {
            "screen_description": MagicMock(),
            "screenshot_b64": "base64",
            "ui_elements_text": "Button",
            "iteration": 5,
            "action_history_summary": "Previous actions",
            "llm_tokens_input": 100,
            "llm_tokens_output": 10,
            "llm_time_ms": 200,
        }
        result = llm_generate_node(agent, state)

        assert result["llm_action"]["action_type"] == "CLICK"
        assert result["has_tool_calls"] is True
        assert result["decision_maker"] == "llm"
        assert result["llm_tokens_input"] == 1100  # 100 + 1000
        assert result["llm_tokens_output"] == 60  # 10 + 50

    def test_no_llm_client_returns_no_action(self, agent_config, mock_dependencies):
        """No LLM client returns no action (will be handled by validation)."""
        mock_dependencies["llm_client"] = None
        agent = RVAgent(config=agent_config, **mock_dependencies)

        state = {}
        result = llm_generate_node(agent, state)

        assert result["llm_action"] is None
        assert result["has_tool_calls"] is False
        assert result["decision_maker"] == "llm"


class TestValidateActionNode:
    """Test validate_action_node behavior."""

    def test_validates_llm_action(self, agent, mock_dependencies):
        """Validates LLM action through routing manager."""
        mock_dependencies["routing_manager"].validate_action.return_value = {
            "current_action": {"action_type": "CLICK", "x": 100, "y": 500},
            "loop_detected": False,
        }

        # Set device_dimensions so boundary check uses real values
        mock_dependencies["screen_processor"].device_dimensions = (1080, 1920)

        state = {
            "decision_maker": "llm",
            "llm_action": {"action_type": "CLICK", "x": 100, "y": 500},
            "recent_action_window": [],
        }
        result = validate_action_node(agent, state)

        assert result["current_action"]["action_type"] == "CLICK"
        assert result["loop_detected"] is False

    def test_validates_algorithm_action(self, agent, mock_dependencies):
        """Validates algorithm action through routing manager."""
        mock_dependencies["routing_manager"].validate_action.return_value = {
            "current_action": {"action_type": "BACK"},
            "loop_detected": False,
        }

        state = {
            "decision_maker": "algorithm",
            "current_action": {"action_type": "BACK"},
            "recent_action_window": [],
        }
        result = validate_action_node(agent, state)

        assert result["current_action"]["action_type"] == "BACK"
        assert result["decision_maker"] == "algorithm"

    def test_loop_detected_updates_flag(self, agent, mock_dependencies):
        """Loop detection updates the loop_detected flag."""
        mock_dependencies["routing_manager"].validate_action.return_value = {
            "current_action": {"action_type": "BACK", "reason": "loop_detected"},
            "loop_detected": True,
        }

        state = {
            "decision_maker": "llm",
            "llm_action": {"action_type": "CLICK", "x": 100},
            "recent_action_window": [{"action_type": "CLICK", "x": 100}] * 5,
        }
        result = validate_action_node(agent, state)

        assert result["loop_detected"] is True
        assert result["current_action"]["action_type"] == "BACK"


class TestExecuteNode:
    """Test execute_node behavior."""

    def test_executes_action(self, agent, mock_dependencies):
        """Action executed via tool executor."""
        mock_dependencies["tool_executor"].execute_action.return_value = {
            "success": True,
            "action_executed": {"action_type": "CLICK", "x": 100},
        }

        state = {
            "current_action": {"action_type": "CLICK", "x": 100},
            "decision_maker": "algorithm",
        }
        result = execute_node(agent, state)

        assert result["action_success"] is True
        mock_dependencies["tool_executor"].execute_action.assert_called_with(
            {"action_type": "CLICK", "x": 100}
        )

    def test_executes_llm_action(self, agent, mock_dependencies):
        """LLM action executed via tool executor."""
        mock_dependencies["tool_executor"].execute_action.return_value = {
            "success": True,
            "action_executed": {"action_type": "CLICK", "x": 100},
        }

        state = {
            "current_action": {"action_type": "CLICK", "x": 50},
            "decision_maker": "llm",
        }
        execute_node(agent, state)

        mock_dependencies["tool_executor"].execute_action.assert_called_with(
            {"action_type": "CLICK", "x": 50}
        )

    def test_records_transition_on_success(self, agent, mock_dependencies):
        """Records state transition on successful action."""
        mock_dependencies["tool_executor"].execute_action.return_value = {
            "success": True,
            "action_executed": {"action_type": "CLICK"},
        }
        item_action = MagicMock()

        state = {
            "current_action": {"action_type": "CLICK"},
            "decision_maker": "algorithm",
            "previous_screen_hash": "hash1",
            "current_screen_hash": "hash2",
            "current_item_action": item_action,
            "previous_action_signature": ((100, 200), "click"),
        }
        execute_node(agent, state)

        mock_dependencies["exploration_strategy"].record_transition.assert_called_once()

    def test_no_action_returns_none(self, agent, mock_dependencies):
        """No action to execute returns None."""
        state = {"current_action": None}
        result = execute_node(agent, state)

        assert result["action_executed"] is None


class TestLearnNode:
    """Test learn_node behavior."""

    def _setup_memory_mocks(self, mock_dependencies):
        """Helper to setup memory coordinator mocks."""
        mock_dependencies["memory_coordinator"].update_memories.return_value = {
            "recent_action_window": []
        }
        mock_dependencies["memory_coordinator"].generate_summaries.return_value = {
            "action_history_summary": "history",
            "exploration_summary": "exploration",
            "memory_insights": "insights",
            "navigation_path": "path",
        }
        mock_dependencies["memory_coordinator"].track_state_discovery.return_value = {
            "visited_states": ["hash1"],
            "state_transitions": [("hash0", "hash1")],
        }
        mock_dependencies["memory_coordinator"].check_continuation.return_value = {
            "should_continue": True
        }

    def test_updates_all_memories(self, agent, mock_dependencies):
        """Learn node updates all memory systems."""
        self._setup_memory_mocks(mock_dependencies)

        state = {
            "current_screen_hash": "hash1",
            "previous_screen_hash": "hash0",
            "current_activity": "Main",
            "current_action": {"action_type": "CLICK"},
            "start_time": time.time(),
            "timeout": 100,
        }
        learn_node(agent, state)

        mock_dependencies["memory_coordinator"].update_memories.assert_called_once()
        mock_dependencies["memory_coordinator"].generate_summaries.assert_called_once()
        mock_dependencies[
            "memory_coordinator"
        ].track_state_discovery.assert_called_once()

    def test_stuck_detection_increments_counter(self, agent, mock_dependencies):
        """Unchanged screen increments stuck counter."""
        self._setup_memory_mocks(mock_dependencies)
        agent.last_screen_hash = "hash1"
        agent.stuck_screen_count = 0

        state = {
            "current_screen_hash": "hash1",
            "start_time": time.time(),
            "timeout": 100,
        }
        learn_node(agent, state)

        assert agent.stuck_screen_count == 1

    def test_stuck_detection_resets_on_change(self, agent, mock_dependencies):
        """Changed screen resets stuck counter."""
        self._setup_memory_mocks(mock_dependencies)
        agent.last_screen_hash = "hash1"
        agent.stuck_screen_count = 2

        state = {
            "current_screen_hash": "hash2",
            "start_time": time.time(),
            "timeout": 100,
        }
        learn_node(agent, state)

        assert agent.stuck_screen_count == 0
        assert agent.last_screen_hash == "hash2"

    def test_stuck_threshold_triggers_force_back(self, agent, mock_dependencies):
        """Stuck threshold sets force_back_action flag."""
        self._setup_memory_mocks(mock_dependencies)
        agent.last_screen_hash = "hash1"
        agent.stuck_screen_count = 7  # Will become 8 (BASE_STUCK_THRESHOLD)

        state = {
            "current_screen_hash": "hash1",
            "start_time": time.time(),
            "timeout": 100,
        }
        result = learn_node(agent, state)

        assert result.get("force_back_action") is True
        assert agent.stuck_screen_count == 0  # Reset after triggering

    def test_returns_summaries(self, agent, mock_dependencies):
        """Learn node returns generated summaries."""
        self._setup_memory_mocks(mock_dependencies)

        state = {
            "current_screen_hash": "hash1",
            "start_time": time.time(),
            "timeout": 100,
        }
        result = learn_node(agent, state)

        assert result["action_history_summary"] == "history"
        assert result["exploration_summary"] == "exploration"
        assert result["memory_insights"] == "insights"


class TestGetMemoryStats:
    """Test get_memory_stats method."""

    def test_delegates_to_memory_coordinator(self, agent, mock_dependencies):
        """get_memory_stats delegates to MemoryCoordinator."""
        mock_dependencies["memory_coordinator"].get_all_statistics.return_value = {
            "total_actions": 50,
            "unique_states": 10,
        }

        stats = agent.get_memory_stats()

        assert stats["total_actions"] == 50
        mock_dependencies["memory_coordinator"].get_all_statistics.assert_called_once()


class TestRunMethod:
    """Test run method (main execution loop)."""

    def _setup_run_mocks(self, agent, mock_dependencies):
        """Setup mocks for run() test."""
        # Mock graph invoke
        agent.graph = MagicMock()
        agent.graph.invoke.return_value = {
            "visited_states": ["hash1", "hash2"],
            "state_transitions": [("hash1", "hash2")],
            "llm_tokens_input": 100,
            "llm_tokens_output": 50,
            "llm_time_ms": 500,
        }

        # Mock routing manager counters
        mock_dependencies["routing_manager"].get_decision_counters.return_value = {
            "total_actions": 10,
            "llm_executed": 7,
            "algorithm_chosen": 3,
            "llm_percentage": 70.0,
            "algorithm_percentage": 30.0,
            "llm_validation_failed": 0,
            "forced_back": 0,
            "primary_total": 10,
        }

        # Mock memory stats
        mock_dependencies["memory_coordinator"].get_all_statistics.return_value = {
            "total_interactions": 10
        }

    def test_launches_app_on_start(self, agent, mock_dependencies):
        """Run launches the target app."""
        self._setup_run_mocks(agent, mock_dependencies)
        agent.config.timeout = 0.1  # Short timeout

        with patch("time.sleep"):
            agent.run()

        mock_dependencies["device"].launch_app.assert_called_with("com.example.app")

    def test_respects_timeout(self, agent, mock_dependencies):
        """Run stops when timeout is reached."""
        self._setup_run_mocks(agent, mock_dependencies)
        agent.config.timeout = 0.5

        with patch("time.sleep"):
            result = agent.run()

        assert result["status"] == "completed"
        assert result["execution_time_s"] > 0

    def test_returns_metrics(self, agent, mock_dependencies):
        """Run returns comprehensive metrics."""
        self._setup_run_mocks(agent, mock_dependencies)
        agent.config.timeout = 0.1

        with patch("time.sleep"):
            result = agent.run()

        assert "iterations" in result
        assert "unique_states" in result
        assert "total_actions" in result
        assert "llm_executed" in result
        assert "llm_percentage" in result
        assert "memory_stats" in result

    def test_handles_launch_failure(self, agent, mock_dependencies):
        """Run handles app launch failure."""
        mock_dependencies["device"].launch_app.side_effect = Exception("Launch failed")

        result = agent.run()

        assert result["status"] == "error"
        assert "Launch failed" in result["error"]

    def test_handles_keyboard_interrupt(self, agent, mock_dependencies):
        """Run handles keyboard interrupt gracefully."""
        self._setup_run_mocks(agent, mock_dependencies)
        agent.graph.invoke.side_effect = KeyboardInterrupt()

        with patch("time.sleep"):
            result = agent.run()

        assert result["status"] == "completed"

    def test_handles_execution_error(self, agent, mock_dependencies):
        """Run handles execution errors."""
        self._setup_run_mocks(agent, mock_dependencies)
        agent.graph.invoke.side_effect = RuntimeError("Execution error")

        with patch("time.sleep"):
            result = agent.run()

        assert result["status"] == "completed"  # Still completes with metrics


class TestBuildAgentGraph:
    """Test _build_agent_graph method."""

    def test_creates_workflow_graph(self, agent):
        """Graph building creates valid workflow."""
        # Graph already built in constructor
        assert agent.graph is not None

    def test_graph_has_correct_nodes(self, agent_config, mock_dependencies):
        """Graph contains all expected nodes."""
        with patch("rv_agent.agent.rv_agent.StateGraph") as mock_sg:
            mock_workflow = MagicMock()
            mock_sg.return_value = mock_workflow

            RVAgent(config=agent_config, **mock_dependencies)

            # Verify nodes were added
            node_calls = [call[0][0] for call in mock_workflow.add_node.call_args_list]
            expected_nodes = [
                "parse_ui",
                "decision_router",
                "algorithm_node",
                "capture_screenshot",
                "llm_generate",
                "validate_action",
                "execute",
                "learn",
            ]
            for node in expected_nodes:
                assert node in node_calls
