"""
Tests for rv-experiment resume behavior at the orchestration layer.

Complements test_resume_cli.py (CLI argument parsing) by testing:
- ExperimentController passes resume flags correctly to PreProcessor
- PreProcessor.process() skips all phases when all flags are False
- ExecutionController passes results_dir to PlatformConfig on resume
- Full controller workflow: resume_mode=True → pre-processing skipped → execution → post-processing
"""

import os
from unittest.mock import MagicMock, patch

from rv_android_core.domain.task import ToolConfig
from rv_experiment.config import ExperimentConfig
from rv_experiment.experiment.experiment_controller import ExperimentController
from rv_experiment.experiment.workflow.execution_controller import ExecutionController
from rv_experiment.experiment.workflow.pre_processor import PreProcessor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_resume_config(tmp_path, **overrides):
    """Create an ExperimentConfig in resume mode."""
    results_dir = str(tmp_path / "results" / "my_exp")
    os.makedirs(results_dir, exist_ok=True)

    defaults = dict(
        name="my_exp",
        tool_configs=[ToolConfig(name="monkey")],
        apks_dir=str(tmp_path / "apks"),
        results_dir=results_dir,
        output_dir=str(tmp_path / "out"),
        resume_mode=True,
        generate_monitors=False,
        instrument_apks=False,
        run_static_analysis=False,
        repetitions=1,
        timeouts=[300],
        no_window=True,
    )
    defaults.update(overrides)

    # Create apks dir with fake APK
    apks_dir = defaults["apks_dir"]
    os.makedirs(apks_dir, exist_ok=True)
    apk_path = os.path.join(apks_dir, "app.apk")
    if not os.path.exists(apk_path):
        with open(apk_path, "wb") as f:
            f.write(b"PK\x03\x04")

    os.makedirs(defaults["output_dir"], exist_ok=True)

    return ExperimentConfig(**defaults)


def _make_fresh_config(tmp_path, **overrides):
    """Create an ExperimentConfig for a first run (not resume)."""
    return _make_resume_config(
        tmp_path,
        resume_mode=False,
        generate_monitors=True,
        instrument_apks=True,
        run_static_analysis=True,
        **overrides,
    )


# ===========================================================================
# PreProcessor — skip behavior on resume
# ===========================================================================


class TestPreProcessorResumeBehavior:
    """Verify PreProcessor.process() respects boolean flags."""

    @patch(
        "rv_experiment.experiment.workflow.pre_processor.PreProcessor._generate_monitors"
    )
    @patch(
        "rv_experiment.experiment.workflow.pre_processor.PreProcessor._instrument_apks"
    )
    @patch(
        "rv_experiment.experiment.workflow.pre_processor.PreProcessor._run_static_analysis"
    )
    def test_all_false_skips_all_phases(
        self, mock_static, mock_instrument, mock_monitors, tmp_path
    ):
        """On resume, all three flags are False → no phase executes."""
        config = _make_resume_config(tmp_path)
        pre = PreProcessor(config)

        pre.process(generate_monitors=False, instrument=False, static_analysis=False)

        mock_monitors.assert_not_called()
        mock_instrument.assert_not_called()
        mock_static.assert_not_called()

    @patch(
        "rv_experiment.experiment.workflow.pre_processor.PreProcessor._generate_monitors"
    )
    @patch(
        "rv_experiment.experiment.workflow.pre_processor.PreProcessor._instrument_apks"
    )
    @patch(
        "rv_experiment.experiment.workflow.pre_processor.PreProcessor._run_static_analysis"
    )
    def test_all_true_runs_all_phases(
        self, mock_static, mock_instrument, mock_monitors, tmp_path
    ):
        """First run: all three flags True → all phases execute."""
        config = _make_fresh_config(tmp_path)
        pre = PreProcessor(config)

        pre.process(generate_monitors=True, instrument=True, static_analysis=True)

        mock_monitors.assert_called_once()
        mock_instrument.assert_called_once()
        mock_static.assert_called_once()

    @patch(
        "rv_experiment.experiment.workflow.pre_processor.PreProcessor._generate_monitors"
    )
    @patch(
        "rv_experiment.experiment.workflow.pre_processor.PreProcessor._instrument_apks"
    )
    @patch(
        "rv_experiment.experiment.workflow.pre_processor.PreProcessor._run_static_analysis"
    )
    def test_partial_flags_selective_execution(
        self, mock_static, mock_instrument, mock_monitors, tmp_path
    ):
        """Only flagged phases execute."""
        config = _make_resume_config(tmp_path)
        pre = PreProcessor(config)

        pre.process(generate_monitors=False, instrument=True, static_analysis=False)

        mock_monitors.assert_not_called()
        mock_instrument.assert_called_once()
        mock_static.assert_not_called()


# ===========================================================================
# ExperimentController — resume wiring
# ===========================================================================


class TestExperimentControllerResume:
    """Controller passes resume config flags through to PreProcessor."""

    @patch("rv_experiment.experiment.experiment_controller.PostProcessor")
    @patch("rv_experiment.experiment.experiment_controller.ExecutionController")
    @patch("rv_experiment.experiment.experiment_controller.PreProcessor")
    @patch("rv_experiment.experiment.experiment_controller.LoggingManager")
    @patch("rv_experiment.experiment.experiment_controller.ErrorHandler")
    def test_resume_mode_passes_false_flags_to_preprocessor(
        self,
        mock_error_handler,
        mock_logging_manager,
        mock_pre_processor_cls,
        mock_exec_ctrl_cls,
        mock_post_processor_cls,
        tmp_path,
    ):
        """On resume, controller passes all False flags to pre_processor.process()."""
        config = _make_resume_config(tmp_path)
        # Disable execution so we only test pre-processing call
        config.run_execution = False

        controller = ExperimentController(config)
        controller.run()

        # Verify pre_processor.process() was called with all False
        pre_processor_instance = mock_pre_processor_cls.return_value
        pre_processor_instance.process.assert_called_once_with(
            generate_monitors=False,
            instrument=False,
            static_analysis=False,
        )

    @patch("rv_experiment.experiment.experiment_controller.PostProcessor")
    @patch("rv_experiment.experiment.experiment_controller.ExecutionController")
    @patch("rv_experiment.experiment.experiment_controller.PreProcessor")
    @patch("rv_experiment.experiment.experiment_controller.LoggingManager")
    @patch("rv_experiment.experiment.experiment_controller.ErrorHandler")
    def test_fresh_run_passes_true_flags_to_preprocessor(
        self,
        mock_error_handler,
        mock_logging_manager,
        mock_pre_processor_cls,
        mock_exec_ctrl_cls,
        mock_post_processor_cls,
        tmp_path,
    ):
        """First run passes all True flags to pre_processor.process()."""
        config = _make_fresh_config(tmp_path)
        config.run_execution = False

        controller = ExperimentController(config)
        controller.run()

        pre_processor_instance = mock_pre_processor_cls.return_value
        pre_processor_instance.process.assert_called_once_with(
            generate_monitors=True,
            instrument=True,
            static_analysis=True,
        )

    @patch("rv_experiment.experiment.experiment_controller.PostProcessor")
    @patch("rv_experiment.experiment.experiment_controller.ExecutionController")
    @patch("rv_experiment.experiment.experiment_controller.PreProcessor")
    @patch("rv_experiment.experiment.experiment_controller.LoggingManager")
    @patch("rv_experiment.experiment.experiment_controller.ErrorHandler")
    def test_resume_still_runs_execution_and_postprocessing(
        self,
        mock_error_handler,
        mock_logging_manager,
        mock_pre_processor_cls,
        mock_exec_ctrl_cls,
        mock_post_processor_cls,
        tmp_path,
    ):
        """Resume skips pre-processing but still runs execution and post-processing."""
        config = _make_resume_config(tmp_path)

        # Mock the execution chain
        mock_pre = mock_pre_processor_cls.return_value
        mock_pre.get_instrumented_apks.return_value = [MagicMock()]
        mock_exec = mock_exec_ctrl_cls.return_value
        mock_exec.run.return_value = True
        mock_post = mock_post_processor_cls.return_value

        # Mock _get_configured_tools to return a tool
        with patch.object(
            ExperimentController,
            "_get_configured_tools",
            return_value=[MagicMock(name="monkey")],
        ):
            controller = ExperimentController(config)
            result = controller.run()

        assert result is True
        # Pre-processing called with False flags
        mock_pre.process.assert_called_once_with(
            generate_monitors=False,
            instrument=False,
            static_analysis=False,
        )
        # Execution and post-processing still run
        mock_exec.setup.assert_called_once()
        mock_exec.run.assert_called_once()
        mock_post.process.assert_called_once()


# ===========================================================================
# ExecutionController — results_dir propagation
# ===========================================================================


class TestExecutionControllerResultsDir:
    """ExecutionController must pass results_dir to PlatformConfig for resume."""

    @patch("rv_experiment.experiment.workflow.execution_controller.Platform")
    def test_setup_passes_results_dir_to_platform_config(
        self, mock_platform_cls, tmp_path
    ):
        """results_dir from experiment is forwarded to PlatformConfig."""
        config = _make_resume_config(tmp_path)
        results_dir = str(tmp_path / "results" / "my_exp")

        exec_ctrl = ExecutionController(config)

        # Create instrumented_apks dir so it's used as apks_dir
        instr_dir = os.path.join(config.output_dir, "instrumented_apks")
        os.makedirs(instr_dir, exist_ok=True)
        with open(os.path.join(instr_dir, "app.apk"), "wb") as f:
            f.write(b"PK\x03\x04")

        exec_ctrl.setup(
            apks=[MagicMock(name="app.apk")],
            repetitions=1,
            timeouts=[300],
            tools=[MagicMock(name="monkey")],
            tool_configs=[ToolConfig(name="monkey")],
            no_window=True,
            results_dir=results_dir,
        )

        # Verify Platform was created with correct results_dir
        platform_config = mock_platform_cls.call_args[0][0]
        assert platform_config.results_dir == results_dir

    @patch("rv_experiment.experiment.workflow.execution_controller.Platform")
    def test_resume_results_dir_is_same_as_original(self, mock_platform_cls, tmp_path):
        """On resume, results_dir points to existing experiment directory (no nesting)."""
        resume_dir = str(tmp_path / "results" / "original_exp")
        os.makedirs(resume_dir, exist_ok=True)

        config = _make_resume_config(tmp_path, results_dir=resume_dir)
        exec_ctrl = ExecutionController(config)

        # Create instrumented_apks dir
        instr_dir = os.path.join(config.output_dir, "instrumented_apks")
        os.makedirs(instr_dir, exist_ok=True)
        with open(os.path.join(instr_dir, "app.apk"), "wb") as f:
            f.write(b"PK\x03\x04")

        exec_ctrl.setup(
            apks=[MagicMock(name="app.apk")],
            repetitions=2,
            timeouts=[300],
            tools=[MagicMock(name="monkey")],
            tool_configs=[ToolConfig(name="monkey")],
            results_dir=resume_dir,
        )

        platform_config = mock_platform_cls.call_args[0][0]
        # No nesting — flat directory
        assert platform_config.results_dir == resume_dir
        assert "original_exp/original_exp" not in platform_config.results_dir


# ===========================================================================
# ExperimentConfig — resume_mode field
# ===========================================================================


class TestExperimentConfigResumeMode:

    def test_resume_mode_defaults_false(self, tmp_path):
        """resume_mode is False by default."""
        config = _make_fresh_config(tmp_path)
        # _make_fresh_config explicitly sets resume_mode=False
        assert config.resume_mode is False

    def test_resume_mode_set_true(self, tmp_path):
        """resume_mode can be set to True."""
        config = _make_resume_config(tmp_path)
        assert config.resume_mode is True

    def test_resume_config_has_false_preprocessing_flags(self, tmp_path):
        """In resume mode, all pre-processing flags should be False."""
        config = _make_resume_config(tmp_path)
        assert config.generate_monitors is False
        assert config.instrument_apks is False
        assert config.run_static_analysis is False

    def test_resume_config_preserves_execution_params(self, tmp_path):
        """Resume preserves execution parameters (repetitions, timeouts, tools)."""
        config = _make_resume_config(
            tmp_path,
            repetitions=5,
            timeouts=[300, 600],
            tool_configs=[
                ToolConfig(name="monkey"),
                ToolConfig(name="droidbot", variant="dfs_greedy"),
            ],
        )
        assert config.repetitions == 5
        assert config.timeouts == [300, 600]
        assert len(config.tool_configs) == 2
        assert config.tool_configs[1].variant == "dfs_greedy"
