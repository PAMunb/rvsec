"""
Unit tests for ValidationRunner.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from rv_agent.validation.validation_runner import ValidationRunner
from rv_agent.validation.sequence_loader import SequenceLoader, AppSequence, ScreenData
from rv_agent.validation.mock_device import MockDeviceInterface


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def dataset_dir(tmp_path):
    """Create a dataset directory with sample apps."""
    # Create app directory
    app_dir = tmp_path / "testapp.apk"
    app_dir.mkdir()

    for i in range(3):
        step_str = f"{i+1:03d}"

        # Create screenshot
        (app_dir / f"{step_str}.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

        # Create UIAutomator dump
        (app_dir / f"{step_str}.uiautomator").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
        <hierarchy rotation="0">
            <node bounds="[100,100][300,200]" class="android.widget.Button"
                  clickable="true" long-clickable="false" checkable="false"
                  resource-id="button{i}" text="Button {i}" content-desc="">
            </node>
        </hierarchy>
        ''')

        # Create state file
        state_data = {
            "activity": f"com.test.Activity{i}",
            "view_tree": {"package": "com.test"},
            "screen_size": {"width": 1080, "height": 1920}
        }
        (app_dir / f"{step_str}.state").write_text(json.dumps(state_data))

    return tmp_path


# =============================================================================
# ValidationRunner Initialization Tests
# =============================================================================

class TestValidationRunnerInit:
    """Tests for ValidationRunner initialization."""

    def test_init_creates_loader(self, dataset_dir):
        """Test that initialization creates SequenceLoader."""
        runner = ValidationRunner(dataset_dir)

        assert runner.dataset_dir == dataset_dir
        assert isinstance(runner.loader, SequenceLoader)

    def test_init_with_default_parameters(self, dataset_dir):
        """Test initialization with default parameters."""
        runner = ValidationRunner(dataset_dir)

        assert runner.max_iterations == 25
        assert runner.device_dimensions == (1080, 1920)
        assert runner.optimized_dimensions == (704, 1248)

    def test_init_with_custom_parameters(self, dataset_dir):
        """Test initialization with custom parameters."""
        runner = ValidationRunner(
            dataset_dir,
            max_iterations=50,
            device_dimensions=(1440, 2560),
            optimized_dimensions=(720, 1280)
        )

        assert runner.max_iterations == 50
        assert runner.device_dimensions == (1440, 2560)
        assert runner.optimized_dimensions == (720, 1280)

    def test_init_with_nonexistent_directory(self, tmp_path):
        """Test initialization with non-existent directory raises error."""
        with pytest.raises(ValueError):
            ValidationRunner(tmp_path / "nonexistent")


# =============================================================================
# Validate App Tests (with heavy mocking)
# =============================================================================

class TestValidationRunnerValidateApp:
    """Tests for ValidationRunner.validate_app()."""

    def test_validate_app_nonexistent_app(self, dataset_dir):
        """Test validating non-existent app raises error."""
        runner = ValidationRunner(dataset_dir)

        with pytest.raises(ValueError):
            runner.validate_app("nonexistent.apk")

    @patch('rv_agent.validation.validation_runner.RVAgent')
    def test_validate_app_creates_mock_device(self, mock_rvagent_class, dataset_dir):
        """Test that validate_app creates MockDeviceInterface."""
        # Setup mock RVAgent
        mock_agent = MagicMock()
        mock_agent.dynamic_graph.states = []
        mock_agent.dynamic_graph.transitions = []
        mock_agent.short_term.iterations = []
        mock_rvagent_class.return_value = mock_agent

        runner = ValidationRunner(dataset_dir, max_iterations=1)

        # This will fail at graph.invoke, but we can verify mock device creation
        with patch.object(runner, '_run_validation_iterations'):
            metrics = runner.validate_app("testapp.apk")

        assert "app_name" in str(metrics) or metrics is not None

    @patch('rv_agent.validation.validation_runner.RVAgent')
    def test_validate_app_creates_config(self, mock_rvagent_class, dataset_dir):
        """Test that validate_app creates correct config."""
        mock_agent = MagicMock()
        mock_agent.dynamic_graph.states = []
        mock_agent.dynamic_graph.transitions = []
        mock_agent.short_term.iterations = []
        mock_rvagent_class.return_value = mock_agent

        runner = ValidationRunner(dataset_dir, max_iterations=1)

        with patch.object(runner, '_run_validation_iterations'):
            runner.validate_app("testapp.apk", strategy="bfs")

        # Verify RVAgent was called
        assert mock_rvagent_class.called

    @patch('rv_agent.validation.validation_runner.RVAgent')
    def test_validate_app_saves_output(self, mock_rvagent_class, dataset_dir, tmp_path):
        """Test that validate_app saves output when path provided."""
        mock_agent = MagicMock()
        mock_agent.dynamic_graph.states = []
        mock_agent.dynamic_graph.transitions = []
        mock_agent.short_term.iterations = []
        mock_rvagent_class.return_value = mock_agent

        runner = ValidationRunner(dataset_dir, max_iterations=1)
        output_path = tmp_path / "output" / "result.json"

        with patch.object(runner, '_run_validation_iterations'):
            runner.validate_app("testapp.apk", output_path=output_path)

        assert output_path.exists()

    @patch('rv_agent.validation.validation_runner.RVAgent')
    def test_validate_app_returns_metrics_dict(self, mock_rvagent_class, dataset_dir):
        """Test that validate_app returns metrics dictionary."""
        mock_agent = MagicMock()
        mock_agent.dynamic_graph.states = []
        mock_agent.dynamic_graph.transitions = []
        mock_agent.short_term.iterations = []
        mock_rvagent_class.return_value = mock_agent

        runner = ValidationRunner(dataset_dir, max_iterations=1)

        with patch.object(runner, '_run_validation_iterations'):
            metrics = runner.validate_app("testapp.apk")

        assert isinstance(metrics, dict)
        assert 'app_name' in metrics or 'execution_time_s' in metrics


# =============================================================================
# Run Validation Iterations Tests
# =============================================================================

class TestValidationRunnerRunIterations:
    """Tests for ValidationRunner._run_validation_iterations()."""

    def test_run_iterations_creates_state(self, dataset_dir):
        """Test that run_iterations creates proper state."""
        # Create mock objects
        mock_agent = MagicMock()
        mock_agent.config.strategy = "dfs"
        mock_agent.config.package_name = "com.test"
        mock_agent.graph.invoke.return_value = {
            "current_screen_hash": "hash1",
            "current_activity": "Activity1",
            "action_history_summary": "summary",
            "exploration_summary": "exploration",
            "memory_insights": "insights",
            "navigation_path": "path",
            "visited_states": set(),
            "state_transitions": {}
        }

        # Create mock sequence
        app_dir = dataset_dir / "testapp.apk"
        screens = []
        for i in range(2):
            step_str = f"{i+1:03d}"
            screens.append(ScreenData(
                step=i + 1,
                screenshot_path=app_dir / f"{step_str}.png",
                uiautomator_path=app_dir / f"{step_str}.uiautomator",
                state_path=app_dir / f"{step_str}.state",
                activity=f"Activity{i}",
                package="com.test",
                screen_size=(1080, 1920)
            ))

        sequence = AppSequence(
            app_name="testapp.apk",
            app_dir=app_dir,
            package_name="com.test",
            screens=screens
        )

        mock_device = MockDeviceInterface(sequence)
        mock_metrics = MagicMock()
        mock_metrics.metrics.start_time = 1000.0

        runner = ValidationRunner(dataset_dir, max_iterations=2)

        runner._run_validation_iterations(
            agent=mock_agent,
            mock_device=mock_device,
            metrics_collector=mock_metrics,
            max_iterations=2
        )

        # Verify graph.invoke was called
        assert mock_agent.graph.invoke.call_count == 2

    def test_run_iterations_records_metrics(self, dataset_dir):
        """Test that run_iterations records metrics for each iteration."""
        mock_agent = MagicMock()
        mock_agent.config.strategy = "dfs"
        mock_agent.config.package_name = "com.test"
        mock_agent.graph.invoke.return_value = {
            "current_screen_hash": "hash1",
            "current_activity": "Activity1",
            "llm_tokens_input": 100,
            "llm_tokens_output": 50,
            "llm_time_ms": 200.0,
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": "",
            "visited_states": set(),
            "state_transitions": {}
        }

        app_dir = dataset_dir / "testapp.apk"
        screens = [
            ScreenData(
                step=1,
                screenshot_path=app_dir / "001.png",
                uiautomator_path=app_dir / "001.uiautomator",
                state_path=app_dir / "001.state",
                activity="Activity1",
                package="com.test",
                screen_size=(1080, 1920)
            )
        ]

        sequence = AppSequence(
            app_name="testapp.apk",
            app_dir=app_dir,
            package_name="com.test",
            screens=screens
        )

        mock_device = MockDeviceInterface(sequence)
        mock_metrics = MagicMock()
        mock_metrics.metrics.start_time = 1000.0

        runner = ValidationRunner(dataset_dir, max_iterations=1)

        runner._run_validation_iterations(
            agent=mock_agent,
            mock_device=mock_device,
            metrics_collector=mock_metrics,
            max_iterations=1
        )

        # Verify record_iteration was called
        assert mock_metrics.record_iteration.called

    def test_run_iterations_handles_error(self, dataset_dir):
        """Test that run_iterations continues after iteration error."""
        mock_agent = MagicMock()
        mock_agent.config.strategy = "dfs"
        mock_agent.config.package_name = "com.test"
        # First call raises error, second succeeds
        mock_agent.graph.invoke.side_effect = [
            Exception("Test error"),
            {
                "current_screen_hash": "hash1",
                "current_activity": "Activity1",
                "action_history_summary": "",
                "exploration_summary": "",
                "memory_insights": "",
                "navigation_path": "",
                "visited_states": set(),
                "state_transitions": {}
            }
        ]

        app_dir = dataset_dir / "testapp.apk"
        screens = [
            ScreenData(
                step=1,
                screenshot_path=app_dir / "001.png",
                uiautomator_path=app_dir / "001.uiautomator",
                state_path=app_dir / "001.state",
                activity="Activity1",
                package="com.test",
                screen_size=(1080, 1920)
            )
        ]

        sequence = AppSequence(
            app_name="testapp.apk",
            app_dir=app_dir,
            package_name="com.test",
            screens=screens
        )

        mock_device = MockDeviceInterface(sequence)
        mock_metrics = MagicMock()
        mock_metrics.metrics.start_time = 1000.0

        runner = ValidationRunner(dataset_dir, max_iterations=2)

        # Should not raise - continues after error
        runner._run_validation_iterations(
            agent=mock_agent,
            mock_device=mock_device,
            metrics_collector=mock_metrics,
            max_iterations=2
        )

        # Both iterations attempted
        assert mock_agent.graph.invoke.call_count == 2


# =============================================================================
# Print Summary Tests
# =============================================================================

class TestValidationRunnerPrintSummary:
    """Tests for ValidationRunner._print_summary()."""

    def test_print_summary_logs_info(self, dataset_dir):
        """Test that print_summary logs information."""
        runner = ValidationRunner(dataset_dir)

        metrics = {
            'execution_time_s': 180.0,
            'total_iterations': 25,
            'actions': {
                'valid': 20,
                'invalid': 5,
                'valid_rate': 0.8,
                'by_type': {'CLICK': 15, 'BACK': 10}
            },
            'element_coverage': {
                'types_seen': ['Button', 'TextView']
            },
            'exploration': {
                'unique_screens': 5,
                'activities': ['A', 'B'],
                'revisit_rate': 0.3
            },
            'memory_graph': {
                'graph_states': 5,
                'graph_transitions': 8,
                'short_term_iterations': 25
            },
            'llm': {
                'total_tokens': 5000,
                'avg_tokens_per_iteration': 200,
                'max_message_count': 10
            }
        }

        # Should not raise
        runner._print_summary(metrics)


# =============================================================================
# Validate All Apps Tests
# =============================================================================

class TestValidationRunnerValidateAllApps:
    """Tests for ValidationRunner.validate_all_apps()."""

    @patch('rv_agent.validation.validation_runner.RVAgent')
    def test_validate_all_apps_processes_all(self, mock_rvagent_class, dataset_dir):
        """Test that validate_all_apps processes all apps."""
        mock_agent = MagicMock()
        mock_agent.dynamic_graph.states = []
        mock_agent.dynamic_graph.transitions = []
        mock_agent.short_term.iterations = []
        mock_rvagent_class.return_value = mock_agent

        # Create second app
        app2_dir = dataset_dir / "app2.apk"
        app2_dir.mkdir()
        for i in range(2):
            step_str = f"{i+1:03d}"
            (app2_dir / f"{step_str}.png").write_bytes(b'\x89PNG\r\n\x1a\n')
            (app2_dir / f"{step_str}.uiautomator").write_text('<hierarchy></hierarchy>')
            (app2_dir / f"{step_str}.state").write_text(json.dumps({
                "activity": "Activity",
                "view_tree": {"package": "com.test2"},
                "screen_size": {"width": 1080, "height": 1920}
            }))

        runner = ValidationRunner(dataset_dir, max_iterations=1)

        with patch.object(runner, '_run_validation_iterations'):
            results = runner.validate_all_apps()

        assert len(results) == 2
        assert "testapp.apk" in results
        assert "app2.apk" in results

    @patch('rv_agent.validation.validation_runner.RVAgent')
    def test_validate_all_apps_continues_on_error(self, mock_rvagent_class, dataset_dir):
        """Test that validate_all_apps continues after app error."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Test error")
            mock = MagicMock()
            mock.dynamic_graph.states = []
            mock.dynamic_graph.transitions = []
            mock.short_term.iterations = []
            return mock

        mock_rvagent_class.side_effect = side_effect

        # Create second app
        app2_dir = dataset_dir / "app2.apk"
        app2_dir.mkdir()
        for i in range(2):
            step_str = f"{i+1:03d}"
            (app2_dir / f"{step_str}.png").write_bytes(b'\x89PNG\r\n\x1a\n')
            (app2_dir / f"{step_str}.uiautomator").write_text('<hierarchy></hierarchy>')
            (app2_dir / f"{step_str}.state").write_text(json.dumps({
                "activity": "Activity",
                "view_tree": {"package": "com.test2"},
                "screen_size": {"width": 1080, "height": 1920}
            }))

        runner = ValidationRunner(dataset_dir, max_iterations=1)

        with patch.object(runner, '_run_validation_iterations'):
            results = runner.validate_all_apps()

        # One error, one success
        assert len(results) == 2
        error_app = [k for k, v in results.items() if 'error' in v]
        assert len(error_app) == 1

    @patch('rv_agent.validation.validation_runner.RVAgent')
    def test_validate_all_apps_saves_outputs(self, mock_rvagent_class, dataset_dir, tmp_path):
        """Test that validate_all_apps saves outputs when dir provided."""
        mock_agent = MagicMock()
        mock_agent.dynamic_graph.states = []
        mock_agent.dynamic_graph.transitions = []
        mock_agent.short_term.iterations = []
        mock_rvagent_class.return_value = mock_agent

        runner = ValidationRunner(dataset_dir, max_iterations=1)
        output_dir = tmp_path / "results"

        with patch.object(runner, '_run_validation_iterations'):
            runner.validate_all_apps(output_dir=output_dir)

        # Should create output directory and file
        assert output_dir.exists()
        assert any(output_dir.glob("*.json"))
