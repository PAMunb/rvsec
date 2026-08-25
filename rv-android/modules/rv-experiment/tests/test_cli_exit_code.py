"""The CLI's exit code answers to what the experiment actually did (FR16).

`execute_with_config()` is declared `-> bool` and returns the `False` that
`ExperimentController.run()` produces when Phase 2 reports failure without
raising. That return was discarded, so `✅ Experiment completed successfully!`
printed unconditionally and `sys.exit(1)` happened only inside the `except`.

It matters beyond cosmetics because both Docker entrypoints `exec` this CLI, so
the container's exit code is the CLI's, and `experimento-20260604/scripts/
run_smoke.sh` aborts on a non-zero code — a smoke pass with a failed Phase 2
used to be indistinguishable from a clean one.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner
from rv_experiment.__main__ import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _invoke(runner: CliRunner, apks_dir: str, outcome: bool):
    """Run the command with Phase 2's verdict forced to `outcome`.

    Only `execute_with_config` is patched: everything upstream of it — argument
    parsing, config construction, `validate()` — runs for real, so the test
    exercises the same path the operator does.
    """
    with patch(
        "rv_experiment.__main__.execute_with_config", return_value=outcome
    ) as mock_exec:
        result = runner.invoke(
            cli,
            ["run", "--tools", "monkey", "--apks-dir", apks_dir, "--timeouts", "60"],
            catch_exceptions=False,
        )
    return result, mock_exec


def test_failed_phase_two_exits_non_zero(runner, tmp_apk_dir):
    """A `False` verdict: no success message, non-zero exit."""
    result, mock_exec = _invoke(runner, tmp_apk_dir, outcome=False)

    assert mock_exec.called, "the CLI must reach the controller"
    assert result.exit_code != 0, (
        "the experiment reported failure and the CLI exited 0 — this is the code "
        f"the Docker container returns. Output:\n{result.output}"
    )
    # The exact banner, not a substring: unrelated INFO logs carry the words
    # "completed successfully" ("Configuration validation completed successfully").
    assert "✅ Experiment completed successfully!" not in result.output
    assert "❌ Experiment failed" in result.output


def test_successful_run_exits_zero(runner, tmp_apk_dir):
    """A `True` verdict still exits 0 and still says so."""
    result, _ = _invoke(runner, tmp_apk_dir, outcome=True)

    assert result.exit_code == 0, result.output
    assert "✅ Experiment completed successfully!" in result.output
