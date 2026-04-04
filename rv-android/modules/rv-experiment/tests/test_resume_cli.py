# tests/test_resume_cli.py
"""
Unit tests for rv-experiment CLI resume detection.

Tests U11-U14 from the resume-docker change design.md Testing Strategy.
These test already-implemented logic and should all pass.
"""

import json
from unittest.mock import MagicMock

from rv_android_core.domain.task import ToolConfig
from rv_experiment.__main__ import CLIContext, _create_experiment_config_from_cli
from rv_experiment.constants import RESULTS_DIR

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cli_context():
    """Create a minimal CLIContext mock with a working logger.

    The mock must configure parse_tool_specification to return a list of
    ToolConfig instances because _create_experiment_config_from_cli uses
    tool_configs.extend(ctx.parse_tool_specification(...)).
    """
    ctx = MagicMock(spec=CLIContext)
    ctx.logger = MagicMock()
    ctx.tool_registry = MagicMock()
    ctx.parse_tool_specification = MagicMock(
        return_value=[ToolConfig(name="monkey", variant="default", parameters={})]
    )
    return ctx


def _call_create_config(
    ctx, tmp_path, name=None, resume_dir=None, tools="monkey", apks_dir=None
):
    """Call _create_experiment_config_from_cli with sensible defaults.

    The function has many parameters; this helper provides defaults for all
    of them so tests only need to specify the parameters they care about.
    """
    if apks_dir is None:
        # Create a temp apks dir with a fake APK
        apks = tmp_path / "apks"
        apks.mkdir(exist_ok=True)
        (apks / "test.apk").write_bytes(b"fake")
        apks_dir = str(apks)

    return _create_experiment_config_from_cli(
        ctx=ctx,
        tools=tools,
        timeout=60,
        repetitions=1,
        apks_dir=apks_dir,
        specification_set="jca",
        custom_specs_dir=None,
        custom_aspects_dir=None,
        generate_monitors=True,
        instrument_apks=True,
        static_analysis=True,
        output_dir=None,
        no_window=True,
        run_execution=True,
        device_port=None,
        apks_filter=None,
        name=name,
        resume_dir=resume_dir,
    )


# ---------------------------------------------------------------------------
# U11: --resume-dir sets skip flags
# ---------------------------------------------------------------------------


class TestResumeDir:

    def test_cli_resume_dir_sets_skip_flags(self, tmp_path, monkeypatch):
        """U11: --resume-dir auto-sets all 3 skip flags to True."""
        monkeypatch.chdir(tmp_path)

        # Create a fake results directory (--resume-dir requires it to exist)
        resume_path = tmp_path / "results" / "old_experiment"
        resume_path.mkdir(parents=True)
        # Write a tasks.json so it looks like a real results dir
        (resume_path / "tasks.json").write_text(
            json.dumps({"version": 3, "tasks": [], "experiment": {}, "statistics": {}})
        )

        ctx = _make_cli_context()
        config = _call_create_config(ctx, tmp_path, resume_dir=str(resume_path))

        assert config.resume_mode is True
        assert config.generate_monitors is False
        assert config.instrument_apks is False
        assert config.run_static_analysis is False


# ---------------------------------------------------------------------------
# U12: --name detects existing results
# ---------------------------------------------------------------------------


class TestResumeName:

    def test_cli_name_detects_existing_results(self, tmp_path, monkeypatch):
        """U12: --name with existing tasks.json triggers resume mode."""
        monkeypatch.chdir(tmp_path)

        # Create the results directory that --name would look for
        results_path = tmp_path / RESULTS_DIR / "my_experiment"
        results_path.mkdir(parents=True)
        (results_path / "tasks.json").write_text(
            json.dumps({"version": 3, "tasks": [], "experiment": {}, "statistics": {}})
        )

        ctx = _make_cli_context()
        config = _call_create_config(ctx, tmp_path, name="my_experiment")

        assert config.resume_mode is True
        assert config.generate_monitors is False
        assert config.instrument_apks is False
        assert config.run_static_analysis is False

        # Verify the log message was emitted
        ctx.logger.info.assert_any_call(
            "Resuming experiment 'my_experiment' — auto-skipping pre-processing"
        )


# ---------------------------------------------------------------------------
# U13: --name first run (no existing results)
# ---------------------------------------------------------------------------


class TestNameFirstRun:

    def test_cli_name_first_run_no_resume(self, tmp_path, monkeypatch):
        """U13: --name without existing results is a fresh experiment."""
        monkeypatch.chdir(tmp_path)

        # Do NOT create the results directory — this is a first run
        ctx = _make_cli_context()
        config = _call_create_config(ctx, tmp_path, name="new_experiment")

        assert config.resume_mode is False
        # Skip flags should retain their original values (True from test defaults)
        assert config.generate_monitors is True
        assert config.instrument_apks is True
        assert config.run_static_analysis is True


# ---------------------------------------------------------------------------
# U14: --resume-dir overrides --name
# ---------------------------------------------------------------------------


class TestResumeDirOverridesName:

    def test_cli_resume_dir_overrides_name(self, tmp_path, monkeypatch):
        """U14: --resume-dir takes precedence over --name."""
        monkeypatch.chdir(tmp_path)

        # Create a resume directory
        resume_path = tmp_path / "results" / "old_experiment"
        resume_path.mkdir(parents=True)
        (resume_path / "tasks.json").write_text(
            json.dumps({"version": 3, "tasks": [], "experiment": {}, "statistics": {}})
        )

        ctx = _make_cli_context()
        config = _call_create_config(
            ctx,
            tmp_path,
            name="new_experiment",
            resume_dir=str(resume_path),
        )

        # resume_dir takes precedence
        assert config.resume_mode is True
        assert config.results_dir == str(resume_path)
        # Name should be overridden by resume_dir's directory name
        assert config.name == "old_experiment"
