"""
``--full-output`` CLI plumbing for ``-clientParam fullOutput=true``.

GATOR writes the compact document unless the client parameter asks for the full
one, so the command carries ``fullOutput`` only when the operator asked for it:

  (a) ``full_output=True``          -> ``-clientParam fullOutput=true`` in the cmd
  (b) default                        -> no ``fullOutput`` anywhere in the cmd
  (c) ``--full-output`` on ``analyze`` and on ``batch`` -> ``config.full_output``

Path validations are bypassed with ``validate_on_init=False`` (or ``--dry-run``
through the CLI) so the tests need no GATOR install or Android SDK.
"""

from pathlib import Path

import pytest
from rv_static_analysis.__main__ import create_config_from_args, setup_argument_parser
from rv_static_analysis.config import RVStaticAnalysisConfig


def _config(tmp_path: Path, **overrides) -> RVStaticAnalysisConfig:
    return RVStaticAnalysisConfig(
        validate_on_init=False,
        rvsec_root=str(tmp_path),
        gator_dir=str(tmp_path / "gator"),
        analysis_client_jar=str(tmp_path / "gator" / "client.jar"),
        mop_dir=str(tmp_path / "mop"),
        output_dir=str(tmp_path / "out"),
        **overrides,
    )


def _client_params(cmd: list[str]) -> list[str]:
    return [cmd[i + 1] for i, v in enumerate(cmd) if v == "-clientParam"]


def test_full_output_appends_client_param(tmp_path: Path) -> None:
    cmd = _config(tmp_path, full_output=True).get_tool_command(
        "analysis", "/test/app.apk", "/test/output.json"
    )
    assert "fullOutput=true" in _client_params(cmd)


def test_default_command_has_no_full_output(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cmd = config.get_tool_command("analysis", "/test/app.apk", "/test/output.json")
    assert config.full_output is False
    assert not any("fullOutput" in v for v in cmd)


_SUBCOMMANDS = {
    "analyze": ["analyze", "--apk", "/tmp/x.apk", "--output", "/tmp/out"],
    "batch": ["batch", "--apks-dir", "/tmp/apks", "--output", "/tmp/out"],
}


@pytest.mark.parametrize("subcommand", sorted(_SUBCOMMANDS))
def test_full_output_flag_reaches_config(subcommand: str) -> None:
    args = setup_argument_parser().parse_args(
        _SUBCOMMANDS[subcommand] + ["--full-output", "--dry-run"]
    )
    assert args.full_output is True
    assert create_config_from_args(args).full_output is True


@pytest.mark.parametrize("subcommand", sorted(_SUBCOMMANDS))
def test_full_output_flag_absent_keeps_compact(subcommand: str) -> None:
    args = setup_argument_parser().parse_args(_SUBCOMMANDS[subcommand] + ["--dry-run"])
    assert args.full_output is False
    assert create_config_from_args(args).full_output is False
