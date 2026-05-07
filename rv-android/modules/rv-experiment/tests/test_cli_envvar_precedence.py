"""CLI > env > default precedence for `@click.option(envvar=...)` resolution.

gh55 §9 GAMBIARRA — see `openspec/changes/gh55-env-purity-avd-api30/design.md`
"Known Limitations (Gambiarra)" section.

This test exercises the Click-side env→flag bridge added in gh55 §9. It does NOT
test the broader env-var architecture; that lives in the follow-up change at
`openspec/changes/gh-tbd-env-vars-architecture/`.

Coverage: three representative options (`RV_TOOLS`, `RV_TIMEOUTS`,
`RV_INSTRUMENTATION_VARIANT`) × three modes (CLI only, env only, neither →
default). For each case the test runs the real Click command up to (and
including) the body of `run()`, intercepting `_create_experiment_config_from_cli`
to capture the values Click actually passed in.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from rv_experiment.__main__ import cli
from rv_experiment.constants import DEFAULT_TIMEOUT


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def captured_args():
    """Patch `_create_experiment_config_from_cli` to capture Click's resolved
    args without running an actual experiment. Returns a dict that the test
    populates and inspects."""
    captured: dict = {}

    class _StopRun(Exception):
        """Sentinel to abort run() once Click args are captured."""

    def _capture(*args, **kwargs):
        # The call site at __main__.py uses positional args for the first 18
        # params (ctx, tools, timeout, repetitions, apks_dir, specification_set,
        # custom_specs_dir, custom_aspects_dir, generate_monitors,
        # instrument_apks, static_analysis, output_dir, no_window, run_execution,
        # device_port, apks_filter, name, resume_dir) and keyword args for the
        # rest (instrumentation_variant, enable_quarantine, analysis_timeout,
        # jvm_memory). Use generic *args/**kwargs to avoid coupling to that
        # ordering — index by position for positionals, key for kwargs.
        captured["tools"] = args[1]
        captured["timeout"] = args[2]
        captured["instrumentation_variant"] = kwargs["instrumentation_variant"]
        raise _StopRun()

    with patch(
        "rv_experiment.__main__._create_experiment_config_from_cli",
        side_effect=_capture,
    ):
        yield captured


def _invoke(runner: CliRunner, args: list[str], env: dict[str, str] | None = None):
    """Invoke `rv-experiment run`, returning the Click result. The fixture
    raises `_StopRun` after capturing args; CliRunner reports it as a non-zero
    exit but the assertions look at `captured_args`, not the exit code."""
    return runner.invoke(cli, ["run", *args], env=env or {}, catch_exceptions=True)


def test_tools_default_when_neither_cli_nor_env(runner, captured_args):
    _invoke(runner, [])
    assert captured_args["tools"] == "monkey"  # DEFAULT


def test_tools_env_only(runner, captured_args):
    _invoke(runner, [], env={"RV_TOOLS": "ape,fastbot"})
    assert captured_args["tools"] == "ape,fastbot"


def test_tools_cli_overrides_env(runner, captured_args):
    _invoke(
        runner,
        ["--tools", "monkey,droidbot"],
        env={"RV_TOOLS": "ape,fastbot"},
    )
    assert captured_args["tools"] == "monkey,droidbot"


def test_timeouts_default_when_neither_cli_nor_env(runner, captured_args):
    _invoke(runner, [])
    assert captured_args["timeout"] == DEFAULT_TIMEOUT


def test_timeouts_env_only(runner, captured_args):
    _invoke(runner, [], env={"RV_TIMEOUTS": "180"})
    assert captured_args["timeout"] == 180


def test_timeouts_cli_overrides_env(runner, captured_args):
    _invoke(runner, ["--timeout", "60"], env={"RV_TIMEOUTS": "180"})
    assert captured_args["timeout"] == 60


def test_instrumentation_variant_default_when_neither_cli_nor_env(
    runner, captured_args
):
    _invoke(runner, [])
    assert captured_args["instrumentation_variant"] == "ajc"


def test_instrumentation_variant_env_only(runner, captured_args):
    _invoke(runner, [], env={"RV_INSTRUMENTATION_VARIANT": "dexlib2"})
    assert captured_args["instrumentation_variant"] == "dexlib2"


def test_instrumentation_variant_cli_overrides_env(runner, captured_args):
    _invoke(
        runner,
        ["--instrumentation-variant", "ajc"],
        env={"RV_INSTRUMENTATION_VARIANT": "dexlib2"},
    )
    assert captured_args["instrumentation_variant"] == "ajc"
