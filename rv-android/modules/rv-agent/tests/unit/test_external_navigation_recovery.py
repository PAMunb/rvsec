"""
Unit tests for external navigation recovery (gh26 Group 11).

Tests three bug fixes:
(a) _restart_app failure does not leave external_navigation_count stuck
(b) Total error limit breaks the execution loop after MAX_TOTAL_ERRORS
(c) _restart_app calls back() before stop_app/start_app to dismiss system dialogs
(d) Launcher detection triggers immediate restart
(e) None UI state returns safe fallback result
"""

import pytest
from unittest.mock import MagicMock, patch, call

from rv_agent.services.screen_analyzer import (
    ScreenProcessor,
    LAUNCHER_PACKAGES,
)
from rv_agent.agent.rv_agent import MAX_TOTAL_ERRORS
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph


def _make_ui_state(package, activity="MainActivity", xml="<hierarchy></hierarchy>"):
    """Helper to create a mock UI state dict."""
    return {
        "current_package": package,
        "current_activity": f"{package}/.{activity}",
        "xml": xml,
    }


def _make_screen_desc():
    """Helper to create a mock ScreenDescription with required attributes."""
    screen_desc = MagicMock()
    screen_desc.items = []
    screen_desc.activity = "MainActivity"
    return screen_desc


def _make_processor(device=None):
    """Helper to create a ScreenProcessor with mocked dependencies."""
    device = device or MagicMock()
    graph = DynamicStateGraph()
    with patch("rv_agent.services.screen_analyzer.ParserFactory") as mock_factory:
        mock_parser = MagicMock()
        mock_parser.parse_screen.return_value = _make_screen_desc()
        mock_factory.create.return_value = mock_parser
        processor = ScreenProcessor(device=device, dynamic_graph=graph)
    return processor


def _setup_parser_on_processor(processor):
    """Replace processor.parser with a mock that returns a proper ScreenDescription."""
    mock_parser = MagicMock()
    mock_parser.parse_screen.return_value = _make_screen_desc()
    processor.parser = mock_parser
    return mock_parser


class TestRestartAppDismissesDialogs:
    """Task 11.1 / 11.4c: _restart_app calls back() before stop/start."""

    def test_restart_app_calls_back_before_stop_and_start(self):
        """_restart_app presses BACK to dismiss system dialogs before relaunching."""
        device = MagicMock()
        processor = _make_processor(device)

        with patch("time.sleep"):
            processor._restart_app("com.example.app")

        # Verify call order: back -> stop -> start
        expected_calls = [
            call.back(),
            call.stop_app("com.example.app"),
            call.start_app("com.example.app"),
        ]
        # Filter to only the relevant calls (ignoring sleep, logger, etc.)
        actual_calls = [
            c for c in device.method_calls if c[0] in ("back", "stop_app", "start_app")
        ]
        assert actual_calls == expected_calls

    def test_restart_app_calls_back_even_if_stop_fails(self):
        """BACK is called even if stop_app raises an exception."""
        device = MagicMock()
        device.stop_app.side_effect = RuntimeError("stop failed")
        processor = _make_processor(device)

        with patch("time.sleep"):
            with pytest.raises(RuntimeError, match="stop failed"):
                processor._restart_app("com.example.app")

        device.back.assert_called_once()


class TestRestartFailureDoesNotStickCount:
    """Task 11.2 / 11.4a: _restart_app failure resets external_navigation_count."""

    def test_restart_failure_resets_count_to_zero(self):
        """When _restart_app raises, external_navigation_count is still reset to 0."""
        device = MagicMock()
        # start_app raises (simulating ResolverActivity blocking launch)
        device.start_app.side_effect = RuntimeError("launch verification failed")
        # After failed restart, re-capture returns target app state
        device.get_current_ui_state.side_effect = [
            _make_ui_state("com.other"),  # Initial: external app
            _make_ui_state("com.example"),  # Re-capture after restart attempt
        ]

        processor = _make_processor(device)
        _setup_parser_on_processor(processor)

        with patch("time.sleep"):
            result = processor.parse_current_screen(
                target_package="com.example",
                external_navigation_count=2,  # Will increment to 3 (>= max 3)
            )

        # Count must be 0 even though restart raised
        assert result["external_navigation_count"] == 0
        assert result["restart_occurred"] is True

    def test_restart_success_resets_count_to_zero(self):
        """Normal restart also resets count to 0."""
        device = MagicMock()
        device.get_current_ui_state.side_effect = [
            _make_ui_state("com.other"),
            _make_ui_state("com.example"),
        ]

        processor = _make_processor(device)
        _setup_parser_on_processor(processor)

        with patch("time.sleep"):
            result = processor.parse_current_screen(
                target_package="com.example",
                external_navigation_count=2,
            )

        assert result["external_navigation_count"] == 0
        assert result["restart_occurred"] is True


class TestTotalErrorLimit:
    """Task 11.3 / 11.4b: Total error limit breaks the loop."""

    def test_max_total_errors_constant_defined(self):
        """MAX_TOTAL_ERRORS is defined and has expected value."""
        assert MAX_TOTAL_ERRORS == 30

    @patch("rv_agent.agent.rv_agent.time")
    def test_total_errors_breaks_loop(self, mock_time):
        """Loop breaks after MAX_TOTAL_ERRORS total errors."""
        mock_time.time.return_value = 0.0
        mock_time.sleep = MagicMock()

        config = MagicMock()
        config.get_agent_mode.return_value = "pure_algorithm"
        config.package_name = "com.example"
        config.timeout = 9999
        config.strategy = "dfs"
        config.metrics_output_dir = None
        config.agent_mode = "pure_algorithm"

        device = MagicMock()
        device.launch_app.return_value = True

        dynamic_graph = MagicMock()
        strategy = MagicMock()
        image_handler = MagicMock()
        screen_processor = MagicMock()
        routing_manager = MagicMock()
        routing_manager.get_decision_counters.return_value = {
            "total_actions": 0,
            "llm_executed": 0,
            "algorithm_chosen": 0,
            "llm_percentage": 0.0,
            "algorithm_percentage": 0.0,
            "llm_validation_failed": 0,
            "forced_back": 0,
        }
        tool_executor = MagicMock()
        memory_coordinator = MagicMock()
        memory_coordinator.get_all_statistics.return_value = {}

        from rv_agent.agent.rv_agent import RVAgent

        agent = RVAgent(
            config=config,
            device=device,
            dynamic_graph=dynamic_graph,
            exploration_strategy=strategy,
            image_handler=image_handler,
            screen_processor=screen_processor,
            llm_client=None,
            routing_manager=routing_manager,
            tool_executor=tool_executor,
            memory_coordinator=memory_coordinator,
        )

        # Make graph.invoke always raise to accumulate errors
        error_count = 0

        def count_errors(*args, **kwargs):
            nonlocal error_count
            error_count += 1
            raise RuntimeError(f"Test error #{error_count}")

        agent.graph = MagicMock()
        agent.graph.invoke.side_effect = count_errors

        # time.time() returns 0.0 always (within timeout)
        mock_time.time.side_effect = [0.0] + [0.0] * (MAX_TOTAL_ERRORS + 10)

        result = agent.run()

        # Agent should have stopped after exactly MAX_TOTAL_ERRORS errors
        assert error_count == MAX_TOTAL_ERRORS
        assert result["status"] == "completed"
        assert result["iterations"] == 0  # No successful iterations


class TestLauncherDetection:
    """Task 11.6: Launcher detection triggers immediate restart."""

    def test_launcher_packages_constant(self):
        """LAUNCHER_PACKAGES contains expected launcher packages."""
        assert "com.google.android.apps.nexuslauncher" in LAUNCHER_PACKAGES
        assert "com.android.launcher3" in LAUNCHER_PACKAGES
        assert "com.android.launcher" in LAUNCHER_PACKAGES

    def test_launcher_triggers_immediate_restart(self):
        """When on launcher, restart is triggered immediately (count=1, not 3)."""
        device = MagicMock()
        device.get_current_ui_state.side_effect = [
            _make_ui_state("com.google.android.apps.nexuslauncher"),
            _make_ui_state("com.example"),
        ]

        processor = _make_processor(device)
        _setup_parser_on_processor(processor)

        with patch("time.sleep"):
            result = processor.parse_current_screen(
                target_package="com.example",
                external_navigation_count=0,  # First detection
            )

        # Should have triggered restart immediately
        assert result["restart_occurred"] is True
        assert result["external_navigation_count"] == 0
        # back() was called (part of _restart_app dismiss dialog)
        device.back.assert_called()

    def test_non_launcher_external_does_not_trigger_immediate_restart(self):
        """Non-launcher external package uses normal counter logic."""
        device = MagicMock()
        device.get_current_ui_state.return_value = _make_ui_state("com.other")

        processor = _make_processor(device)
        _setup_parser_on_processor(processor)

        result = processor.parse_current_screen(
            target_package="com.example",
            external_navigation_count=0,
        )

        # Should NOT restart on first detection
        assert result["restart_occurred"] is False
        assert result["external_navigation_count"] == 1


class TestNoneUIStateGuard:
    """Task 11.5: None UI state returns safe fallback."""

    def test_none_ui_state_returns_fallback(self):
        """When get_current_ui_state returns None, a safe fallback is returned."""
        device = MagicMock()
        device.get_current_ui_state.return_value = None

        processor = _make_processor(device)

        result = processor.parse_current_screen(
            target_package="com.example",
            external_navigation_count=0,
        )

        assert result["is_external"] is True
        assert result["restart_occurred"] is True
        assert result["screen_description"] is None
        assert result["screen_hash"] == ""

    def test_none_ui_state_after_restart_returns_fallback(self):
        """When UI state is None after restart attempt, fallback is returned."""
        device = MagicMock()
        device.get_current_ui_state.side_effect = [
            _make_ui_state("com.other"),  # External navigation detected
            None,  # Re-capture after restart returns None
        ]

        processor = _make_processor(device)

        with patch("time.sleep"):
            result = processor.parse_current_screen(
                target_package="com.example",
                external_navigation_count=2,  # Will trigger restart
            )

        assert result["is_external"] is True
        assert result["restart_occurred"] is True
        assert result["external_navigation_count"] == 0

    def test_make_external_fallback_result(self):
        """_make_external_fallback_result returns correct structure."""
        device = MagicMock()
        processor = _make_processor(device)

        result = processor._make_external_fallback_result(5)

        assert result["screen_hash"] == ""
        assert result["activity"] == "unknown"
        assert result["screen_description"] is None
        assert result["is_external"] is True
        assert result["restart_occurred"] is True
        assert result["external_navigation_count"] == 5
        assert result["ui_xml"] == ""
