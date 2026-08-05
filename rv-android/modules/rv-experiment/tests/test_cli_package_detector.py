"""CLI > env > default resolution of the package policy (INV-EXP-32, INV-EXP-34).

The flag is the negatable pair `--package-detector` / `--no-package-detector`
with `default=None`, so "flag absent" is distinguishable from "flag given as
false" — the distinction the precedence needs, since `--no-package-detector`
has to beat a truthy `RV_PACKAGE_DETECTOR`.

Unlike the options covered by `test_cli_envvar_precedence.py`, this one does not
use Click's `envvar=`: the environment value is parsed by the helper both entry
points share, so this command and `rv-static-analysis` cannot drift on what a
given string means. An unparseable value aborts with a usage error rather than
resolving to a mode, because it would otherwise decide the scope of every class
the analysis catalogues.
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from rv_experiment.__main__ import _create_experiment_config_from_cli as _orig_factory
from rv_experiment.__main__ import cli

_FACTORY_SIG = inspect.signature(_orig_factory)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def captured_args():
    """Capture what Click passed to the config factory, without running anything."""
    captured: dict = {}

    class _StopRun(Exception):
        """Sentinel to abort run() once the resolved args are captured."""

    def _capture(*args, **kwargs):
        bound = _FACTORY_SIG.bind(*args, **kwargs).arguments
        captured["package_detector"] = bound["package_detector"]
        raise _StopRun()

    with patch(
        "rv_experiment.__main__._create_experiment_config_from_cli",
        side_effect=_capture,
    ):
        yield captured


def _invoke(runner: CliRunner, args: list[str], env: dict[str, str] | None = None):
    """Invoke `rv-experiment run` with a clean slate for the variable.

    Click deletes keys whose value is `None`, so the leading entry removes an
    `RV_PACKAGE_DETECTOR` inherited from the developer's own shell — otherwise
    the default-path tests would fail for whoever has it exported.
    """
    return runner.invoke(
        cli,
        ["run", *args],
        env={"RV_PACKAGE_DETECTOR": None, **(env or {})},
        catch_exceptions=True,
    )


def test_default_is_the_manifest_package(runner, captured_args):
    """Neither flag nor variable: the run reports what each APK declares."""
    _invoke(runner, [])
    assert captured_args["package_detector"] is False


def test_env_var_enables_the_detector(runner, captured_args):
    _invoke(runner, [], env={"RV_PACKAGE_DETECTOR": "true"})
    assert captured_args["package_detector"] is True


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on", " On "])
def test_env_truthy_vocabulary(runner, captured_args, value):
    """The project's convention (INV-CORE-12), case- and whitespace-insensitive."""
    _invoke(runner, [], env={"RV_PACKAGE_DETECTOR": value})
    assert captured_args["package_detector"] is True


@pytest.mark.parametrize("value", ["false", "0", "no", "off", ""])
def test_env_falsy_vocabulary(runner, captured_args, value):
    """An empty value states no preference and falls through to the default."""
    _invoke(runner, [], env={"RV_PACKAGE_DETECTOR": value})
    assert captured_args["package_detector"] is False


def test_flag_overrides_a_truthy_env(runner, captured_args):
    _invoke(runner, ["--package-detector"], env={"RV_PACKAGE_DETECTOR": "true"})
    assert captured_args["package_detector"] is True


def test_negative_flag_overrides_a_truthy_env(runner, captured_args):
    """The case `default=False` could not express: explicit false beats the env."""
    _invoke(runner, ["--no-package-detector"], env={"RV_PACKAGE_DETECTOR": "true"})
    assert captured_args["package_detector"] is False


def test_flag_overrides_a_falsy_env(runner, captured_args):
    _invoke(runner, ["--package-detector"], env={"RV_PACKAGE_DETECTOR": "false"})
    assert captured_args["package_detector"] is True


def test_unparseable_env_aborts_before_setup(runner, captured_args):
    """`maybe` is an intention the tool cannot honour, so it stops (exit 2)."""
    result = _invoke(runner, [], env={"RV_PACKAGE_DETECTOR": "maybe"})

    assert result.exit_code == 2
    assert "RV_PACKAGE_DETECTOR" in result.output
    assert "package_detector" not in captured_args


def test_unparseable_env_is_ignored_when_the_flag_decides(runner, captured_args):
    """The flag is the authority, so the variable is never consulted."""
    _invoke(runner, ["--no-package-detector"], env={"RV_PACKAGE_DETECTOR": "maybe"})
    assert captured_args["package_detector"] is False
