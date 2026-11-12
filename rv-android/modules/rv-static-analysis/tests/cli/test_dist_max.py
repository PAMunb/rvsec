"""
``--dist-max`` CLI plumbing for ``-clientParam distMax=N``.

GATOR searches up to its own default horizon unless the client parameter sets
one, so the command carries ``distMax`` only when the operator asked for it, and
the value is refused at both Python boundaries before GATOR starts:

  (a) ``dist_max=15``                     -> ``-clientParam distMax=15`` in the cmd
  (b) default                              -> no ``distMax`` anywhere in the cmd
  (c) ``--dist-max N`` on ``analyze`` and on ``batch`` -> ``config.dist_max``
  (d) ``--dist-max`` with a value that is not an integer >= 1 -> exit status 2
  (e) ``RVStaticAnalysisConfig(dist_max=0)`` -> ``pydantic.ValidationError``

Path validations are bypassed with ``validate_on_init=False`` (or ``--dry-run``
through the CLI) so the tests need no GATOR install or Android SDK.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from rv_static_analysis.__main__ import (
    create_config_from_args,
    main,
    setup_argument_parser,
)
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


def test_dist_max_appends_client_param(tmp_path: Path) -> None:
    cmd = _config(tmp_path, dist_max=15).get_tool_command(
        "analysis", "/test/app.apk", "/test/output.json"
    )
    assert "distMax=15" in _client_params(cmd)


def test_dist_max_follows_distance_paths(tmp_path: Path) -> None:
    params = _client_params(
        _config(tmp_path, distance_paths=True, dist_max=15).get_tool_command(
            "analysis", "/test/app.apk", "/test/output.json"
        )
    )
    assert params.index("distMax=15") == params.index("distancePaths=true") + 1


def test_default_command_has_no_dist_max(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cmd = config.get_tool_command("analysis", "/test/app.apk", "/test/output.json")
    assert config.dist_max is None
    assert not any("distMax" in v for v in cmd)


@pytest.mark.parametrize("value", [0, -1])
def test_config_refuses_a_horizon_below_one(tmp_path: Path, value: int) -> None:
    with pytest.raises(ValidationError):
        _config(tmp_path, dist_max=value)


_SUBCOMMANDS = {
    "analyze": ["analyze", "--apk", "/tmp/x.apk", "--output", "/tmp/out"],
    "batch": ["batch", "--apks-dir", "/tmp/apks", "--output", "/tmp/out"],
}


@pytest.mark.parametrize("subcommand", sorted(_SUBCOMMANDS))
def test_dist_max_flag_reaches_config_and_command(subcommand: str) -> None:
    args = setup_argument_parser().parse_args(
        _SUBCOMMANDS[subcommand] + ["--dist-max", "15", "--dry-run"]
    )
    config = create_config_from_args(args)

    assert args.dist_max == 15
    assert config.dist_max == 15
    cmd = config.get_tool_command("analysis", "/test/app.apk", "/test/output.json")
    assert "distMax=15" in _client_params(cmd)


@pytest.mark.parametrize("subcommand", sorted(_SUBCOMMANDS))
def test_dist_max_flag_absent_passes_no_horizon(subcommand: str) -> None:
    args = setup_argument_parser().parse_args(_SUBCOMMANDS[subcommand] + ["--dry-run"])
    assert args.dist_max is None
    assert create_config_from_args(args).dist_max is None


@pytest.mark.parametrize("value", ["0", "-1", "ten"])
@pytest.mark.parametrize("subcommand", sorted(_SUBCOMMANDS))
def test_invalid_dist_max_exits_2_naming_the_option(
    subcommand: str, value: str, capsys
) -> None:
    with pytest.raises(SystemExit) as exited:
        setup_argument_parser().parse_args(
            _SUBCOMMANDS[subcommand] + ["--dist-max", value, "--dry-run"]
        )

    assert exited.value.code == 2
    error = capsys.readouterr().err
    assert "--dist-max" in error
    assert f"'{value}'" in error


def test_invalid_dist_max_starts_no_gator_process(monkeypatch) -> None:
    """The refusal happens while parsing, before any APK, config or command
    exists, so the analyzer never builds or invokes the GATOR command."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["rv-static-analysis"] + _SUBCOMMANDS["analyze"] + ["--dist-max", "0"],
    )
    with (
        patch("rv_static_analysis.analysis.static.static_analysis.Command") as command,
        patch("rv_static_analysis.__main__.StaticAnalyzer") as analyzer,
        pytest.raises(SystemExit) as exited,
    ):
        main()

    assert exited.value.code == 2
    analyzer.assert_not_called()
    command.assert_not_called()
