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

import inspect
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from rv_experiment.__main__ import _create_experiment_config_from_cli as _orig_factory
from rv_experiment.__main__ import (
    cli,
)
from rv_experiment.constants import DEFAULT_TIMEOUT

# Resolve params by name via inspect.signature — robust to the (already
# flagged-for-refactor) 21-parameter ordering of _create_experiment_config_from_cli.
# Caught in the gh55 §8.5 code review: the previous index-based access (`args[1]`,
# `args[2]`) would silently break on any reordering.
_FACTORY_SIG = inspect.signature(_orig_factory)


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
        bound = _FACTORY_SIG.bind(*args, **kwargs).arguments
        captured["tools"] = bound["tools"]
        captured["timeouts"] = bound["timeouts"]
        captured["instrumentation_variant"] = bound["instrumentation_variant"]
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
    assert captured_args["timeouts"] == [DEFAULT_TIMEOUT]


def test_timeouts_env_only(runner, captured_args):
    _invoke(runner, [], env={"RV_TIMEOUTS": "180"})
    assert captured_args["timeouts"] == [180]


def test_timeouts_cli_overrides_env(runner, captured_args):
    _invoke(runner, ["--timeouts", "60"], env={"RV_TIMEOUTS": "180"})
    assert captured_args["timeouts"] == [60]


def test_timeouts_list_via_env(runner, captured_args):
    # RV_TIMEOUTS="60,300" must yield two arms, not crash on int("60,300").
    _invoke(runner, [], env={"RV_TIMEOUTS": "60,300"})
    assert captured_args["timeouts"] == [60, 300]


def test_timeouts_list_cli_overrides_env(runner, captured_args):
    _invoke(runner, ["--timeouts", "60,120"], env={"RV_TIMEOUTS": "300"})
    assert captured_args["timeouts"] == [60, 120]


def test_timeouts_invalid_token_fails_fast(runner, captured_args):
    result = _invoke(runner, ["--timeouts", "60,abc"])
    assert result.exit_code == 2
    assert "timeouts must be" in result.output


def test_old_scalar_timeout_flag_rejected(runner, captured_args):
    result = _invoke(runner, ["--timeout", "300"])
    assert result.exit_code == 2
    assert "--timeout" in result.output


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
