"""`RV_SPEC_SET` must reach the `run` command body — the only route into the containers.

The `jca_android` value landed in the `--specification-set` `click.Choice` with gh101, and
`test_config_validation.py` / `test_config_jit.py` already cover config-level resolution. Neither
covers the **environment route**, and that is the one the campaign actually uses:
`instrument/compose.py` sets `environment:` only, and `docker-entrypoint.sh:101` execs
`rv-experiment run` with **no** `--specification-set` flag. A config-level test would therefore
pass while the CLI route rejected the value, and the whole batch would be woven with the wrong
specification set while the funnel recorded `jca_android` — the failure mode the campaign notes
call "the silent killer", because nothing errors.

The option is resolved by Click's own `envvar=ENV_SPEC_SET`, so this exercises Click's
resolution rather than a hand-rolled parser.

`rv-experiment run` is NEVER invoked for real here: it would start an emulator, whose lifecycle
belongs to `rv-platform`. The config factory is patched and raises before anything is set up, so
the assertion is on what Click resolved and handed over.
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from rv_android_core.constants import ENV_SPEC_SET
from rv_experiment.__main__ import _create_experiment_config_from_cli as _orig_factory
from rv_experiment.__main__ import cli

_FACTORY_SIG = inspect.signature(_orig_factory)
VALID_SETS = ["jca", "jca_android", "generic", "custom"]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def captured_args():
    """Capture what Click passed to the config factory, then abort before any setup."""
    captured: dict = {}

    class _StopRun(Exception):
        """Sentinel to abort run() once the resolved args are captured."""

    def _capture(*args, **kwargs):
        bound = _FACTORY_SIG.bind(*args, **kwargs).arguments
        captured["specification_set"] = bound["specification_set"]
        raise _StopRun()

    with patch(
        "rv_experiment.__main__._create_experiment_config_from_cli",
        side_effect=_capture,
    ):
        yield captured


def _invoke(runner: CliRunner, args: list[str], env: dict[str, str] | None = None):
    """Invoke `rv-experiment run`, clearing an inherited `RV_SPEC_SET` first.

    Click deletes keys whose value is `None`, so the leading entry removes the variable from
    the developer's own shell — otherwise the default-path test would fail for whoever exports
    it (and this repository's own campaign shells do).
    """
    return runner.invoke(
        cli,
        ["run", *args],
        env={ENV_SPEC_SET: None, **(env or {})},
        catch_exceptions=True,
    )


def test_env_var_name_is_the_one_the_containers_set():
    """`compose.py` writes this exact name; a rename here would break the route silently."""
    assert ENV_SPEC_SET == "RV_SPEC_SET"


def test_env_selects_jca_android(runner, captured_args):
    """The route the campaign depends on: no flag, value supplied by the environment."""
    _invoke(runner, [], env={ENV_SPEC_SET: "jca_android"})
    assert captured_args["specification_set"] == "jca_android"


@pytest.mark.parametrize("value", ["jca", "jca_android", "generic"])
def test_every_self_sufficient_set_survives_the_env_route(runner, captured_args, value):
    """`custom` is excluded on purpose — it needs a companion flag; see below."""
    _invoke(runner, [], env={ENV_SPEC_SET: value})
    assert captured_args["specification_set"] == value


def test_custom_via_env_still_requires_its_directory(runner, captured_args):
    """INV-EXP-04: `custom` alone is refused, by the env route exactly as by the flag.

    This is the documented contract, not a gap in the env route — `run()` raises a
    `ClickException` naming `--custom-specs-dir` before any setup happens.

    The assertion is on *not reaching the run body* and on the message, deliberately NOT on the
    exit code. Observed here and left alone as out of scope: the `ErrorHandler.handle_errors`
    decorator swallows that `ClickException`, so the process exits **0** even though the run
    was refused. That is a real defect worth reporting upstream — a failed run reporting
    success — but it belongs to `rv-experiment`'s error handling, not to this change, which is
    permitted to add this test file and nothing else.
    """
    result = _invoke(runner, [], env={ENV_SPEC_SET: "custom"})
    assert "specification_set" not in captured_args, "must be refused before the run body"
    assert "--custom-specs-dir" in result.output


def test_custom_via_env_reaches_the_body_with_its_directory(runner, captured_args, tmp_path):
    """With the companion flag supplied, the env route delivers `custom` like any other."""
    _invoke(runner, ["--custom-specs-dir", str(tmp_path)], env={ENV_SPEC_SET: "custom"})
    assert captured_args["specification_set"] == "custom"


def test_flag_overrides_the_env(runner, captured_args):
    _invoke(runner, ["--specification-set", "jca"], env={ENV_SPEC_SET: "jca_android"})
    assert captured_args["specification_set"] == "jca"


def test_unknown_env_value_fails_and_enumerates_the_valid_sets(runner, captured_args):
    """A wrong value must stop the run, not fall back to a default.

    Falling back is the dangerous outcome: the batch would be woven with some other set while
    the funnel recorded the one that was asked for.
    """
    result = _invoke(runner, [], env={ENV_SPEC_SET: "jca_android_bug_predicate"})

    assert result.exit_code != 0
    for name in VALID_SETS:
        assert name in result.output, f"the error must name {name!r} as a valid choice"
    assert "specification_set" not in captured_args, "must fail before reaching the run body"


def test_unknown_flag_value_also_fails(runner, captured_args):
    result = _invoke(runner, ["--specification-set", "nope"])
    assert result.exit_code != 0
    assert "specification_set" not in captured_args
