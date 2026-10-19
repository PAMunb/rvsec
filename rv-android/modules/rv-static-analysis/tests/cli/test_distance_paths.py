"""
``--distance-paths`` CLI plumbing for ``-clientParam distancePaths=true``.

GATOR writes no path unless the client parameter asks for them, so the command
carries ``distancePaths`` only when the operator asked for it:

  (a) ``distance_paths=True``          -> ``-clientParam distancePaths=true`` in the cmd
  (b) default                           -> no ``distancePaths`` anywhere in the cmd
  (c) ``--distance-paths`` on ``analyze`` and on ``batch`` -> ``config.distance_paths``

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


def test_distance_paths_appends_client_param(tmp_path: Path) -> None:
    cmd = _config(tmp_path, distance_paths=True).get_tool_command(
        "analysis", "/test/app.apk", "/test/output.json"
    )
    assert "distancePaths=true" in _client_params(cmd)


def test_default_command_has_no_distance_paths(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cmd = config.get_tool_command("analysis", "/test/app.apk", "/test/output.json")
    assert config.distance_paths is False
    assert not any("distancePaths" in v for v in cmd)


_SUBCOMMANDS = {
    "analyze": ["analyze", "--apk", "/tmp/x.apk", "--output", "/tmp/out"],
    "batch": ["batch", "--apks-dir", "/tmp/apks", "--output", "/tmp/out"],
}


@pytest.mark.parametrize("subcommand", sorted(_SUBCOMMANDS))
def test_distance_paths_flag_reaches_command(subcommand: str, tmp_path: Path) -> None:
    args = setup_argument_parser().parse_args(
        _SUBCOMMANDS[subcommand] + ["--distance-paths", "--dry-run"]
    )
    config = create_config_from_args(args)
    assert config.distance_paths is True
    cmd = config.get_tool_command("analysis", "/test/app.apk", "/test/output.json")
    assert "distancePaths=true" in _client_params(cmd)


@pytest.mark.parametrize("subcommand", sorted(_SUBCOMMANDS))
def test_distance_paths_flag_absent_writes_no_path(subcommand: str) -> None:
    args = setup_argument_parser().parse_args(_SUBCOMMANDS[subcommand] + ["--dry-run"])
    config = create_config_from_args(args)
    assert config.distance_paths is False
    cmd = config.get_tool_command("analysis", "/test/app.apk", "/test/output.json")
    assert not any("distancePaths" in v for v in cmd)
