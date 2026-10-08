"""The handler-stamp switch of `rv-experiment run` (INV-EXP-40, gh121).

`--stamp-handlers` / `--no-stamp-handlers` is declared as `--strip-build-type-suffix`
is: `default=None` and no `envvar=`, so "flag absent" stays distinguishable from
"--no-stamp-handlers given", and `RV_STAMP_HANDLERS` is parsed by the shared
`resolve_bool_setting` helper rather than by Click's own boolean vocabulary.

The resolved value travels by value: `ExperimentConfig.stamp_handlers` →
`get_dexlib_instrumentation_config()` → `DexlibInstrumentationConfig.stamp_handlers`,
and it is recorded in `experiment_config.json`. The `ajc` variant has no stamp, so
`run` rejects the combination before pre-processing, in CLI mode and under `--config`
alike.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from helpers import make_config
from rv_android_core.constants import ENV_STAMP_HANDLERS
from rv_experiment.__main__ import _create_experiment_config_from_cli as _orig_factory
from rv_experiment.__main__ import cli
from rv_experiment.config import ExperimentConfig

_FACTORY_SIG = inspect.signature(_orig_factory)

# modules/ — this file sits at modules/rv-experiment/tests/.
_MODULES_DIR = Path(__file__).resolve().parents[2]


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
        captured["stamp_handlers"] = bound["stamp_handlers"]
        raise _StopRun()

    with patch(
        "rv_experiment.__main__._create_experiment_config_from_cli",
        side_effect=_capture,
    ):
        yield captured


def _invoke(runner: CliRunner, args: list[str], env: dict[str, str] | None = None):
    """Invoke `rv-experiment run`, removing an `RV_STAMP_HANDLERS` inherited from
    the developer's shell (Click deletes keys whose value is `None`)."""
    return runner.invoke(
        cli,
        ["run", "--instrumentation-variant", "dexlib2", *args],
        env={ENV_STAMP_HANDLERS: None, **(env or {})},
        catch_exceptions=True,
    )


# ---------------------------------------------------------------------------
# CLI > env > default
# ---------------------------------------------------------------------------


def test_default_is_off(runner, captured_args):
    """Neither flag nor variable: the run instruments as without the stamp."""
    _invoke(runner, [])
    assert captured_args["stamp_handlers"] is False


def test_flag_turns_it_on(runner, captured_args):
    _invoke(runner, ["--stamp-handlers"])
    assert captured_args["stamp_handlers"] is True


def test_env_var_turns_it_on(runner, captured_args):
    _invoke(runner, [], env={ENV_STAMP_HANDLERS: "true"})
    assert captured_args["stamp_handlers"] is True


def test_negative_flag_overrides_a_truthy_env(runner, captured_args):
    """The case `default=False` could not express: explicit false beats the env."""
    _invoke(runner, ["--no-stamp-handlers"], env={ENV_STAMP_HANDLERS: "true"})
    assert captured_args["stamp_handlers"] is False


def test_unparseable_env_is_a_usage_error_naming_the_variable(runner, captured_args):
    """`maybe` stops the command (exit 2) before any experiment setup."""
    result = _invoke(runner, [], env={ENV_STAMP_HANDLERS: "maybe"})

    assert result.exit_code == 2
    assert ENV_STAMP_HANDLERS in result.output
    assert "stamp_handlers" not in captured_args


# ---------------------------------------------------------------------------
# The ajc variant has no stamp (INV-EXP-40)
# ---------------------------------------------------------------------------


def test_ajc_with_the_flag_aborts_before_pre_processing(runner, tmp_apk_dir, tmp_path):
    """The real path down to validate(); execution must never be reached."""
    with patch("rv_experiment.__main__.execute_with_config") as mock_exec:
        result = runner.invoke(
            cli,
            [
                "run",
                "--tools",
                "monkey",
                "--apks-dir",
                tmp_apk_dir,
                "--output-dir",
                str(tmp_path / "out"),
                "--instrumentation-variant",
                "ajc",
                "--stamp-handlers",
            ],
            env={ENV_STAMP_HANDLERS: None},
            catch_exceptions=False,
        )

    assert not mock_exec.called
    assert result.exit_code != 0
    assert "--stamp-handlers" in result.output
    assert ENV_STAMP_HANDLERS in result.output
    assert "'ajc'" in result.output


def test_ajc_with_the_field_aborts_under_config(runner, tmp_apk_dir, tmp_path):
    """Under --config the file is the authority, and the check reads the resolved
    config, so a hand-edited file cannot run ajc expecting a stamp."""
    config_file = tmp_path / "experiment_config.json"
    make_config(
        tmp_apk_dir,
        output_dir=str(tmp_path / "out"),
        instrumentation_variant="ajc",
        stamp_handlers=True,
    ).save_to_file(str(config_file))

    with patch("rv_experiment.__main__.execute_with_config") as mock_exec:
        result = runner.invoke(
            cli,
            ["run", "--config", str(config_file)],
            env={ENV_STAMP_HANDLERS: None},
            catch_exceptions=False,
        )

    assert not mock_exec.called
    assert result.exit_code != 0
    assert "--stamp-handlers" in result.output


def test_dexlib2_with_the_flag_reaches_execution(runner, tmp_apk_dir, tmp_path):
    """The same real path with dexlib2: the resolved value reaches the controller."""
    with patch(
        "rv_experiment.__main__.execute_with_config", return_value=True
    ) as mock_exec:
        result = runner.invoke(
            cli,
            [
                "run",
                "--tools",
                "monkey",
                "--apks-dir",
                tmp_apk_dir,
                "--output-dir",
                str(tmp_path / "out"),
                "--instrumentation-variant",
                "dexlib2",
                "--stamp-handlers",
            ],
            env={ENV_STAMP_HANDLERS: None},
            catch_exceptions=False,
        )

    assert result.exit_code == 0, result.output
    assert mock_exec.call_args.args[0].stamp_handlers is True


# ---------------------------------------------------------------------------
# By value to the instrumenter, and into the provenance record
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [True, False])
def test_dexlib_config_carries_the_value(tmp_apk_dir, tmp_path, value):
    config = make_config(
        tmp_apk_dir,
        output_dir=str(tmp_path / "out"),
        rvsec_root=str(tmp_path),
        instrumentation_variant="dexlib2",
        stamp_handlers=value,
    )
    assert config.get_dexlib_instrumentation_config().stamp_handlers is value


@pytest.mark.parametrize("value", [True, False])
def test_experiment_config_json_records_it(tmp_apk_dir, tmp_path, value):
    config_file = tmp_path / "experiment_config.json"
    make_config(
        tmp_apk_dir, instrumentation_variant="dexlib2", stamp_handlers=value
    ).save_to_file(str(config_file))

    assert json.loads(config_file.read_text())["stamp_handlers"] is value
    assert ExperimentConfig.from_file(str(config_file)).stamp_handlers is value


# ---------------------------------------------------------------------------
# The read stays at the entry point
# ---------------------------------------------------------------------------

_LITERAL_READ = re.compile(
    r"(environ\.get\(|getenv\(|environ\[)\s*['\"]" + re.escape(ENV_STAMP_HANDLERS)
)


def _source_files():
    for src in sorted(_MODULES_DIR.glob("*/src")):
        yield from (p for p in src.rglob("*.py") if ".venv" not in p.parts)


def test_variable_is_read_only_in_rv_experiment():
    """No literal read anywhere, and the constant is used only by rv-experiment."""
    constants_file = (
        _MODULES_DIR / "rv-android-core" / "src" / "rv_android_core" / "constants.py"
    )
    rv_experiment_src = _MODULES_DIR / "rv-experiment" / "src"

    literal_reads = []
    constant_users = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        if _LITERAL_READ.search(text):
            literal_reads.append(path)
        if "ENV_STAMP_HANDLERS" in text and path != constants_file:
            constant_users.append(path)

    assert literal_reads == []
    assert constant_users, "the entry point must read the variable via the constant"
    assert all(rv_experiment_src in p.parents for p in constant_users), constant_users
