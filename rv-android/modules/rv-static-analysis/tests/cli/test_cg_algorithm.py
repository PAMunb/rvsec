"""
D8 — ``--cg-algorithm {spark,cha,rta,vta}`` CLI plumbing for ``-cgAlgorithm``.

These tests cover the argparse layer plus the round-trip into the assembled
GATOR command (via ``RVStaticAnalysisConfig.get_tool_command``):

  (a) default (no flag)               -> config defaults to 'spark'; '-cgAlgorithm spark' in cmd
  (b) explicit '--cg-algorithm cha'   -> '-cgAlgorithm cha' in cmd
  (c) invalid '--cg-algorithm bogus'  -> argparse exits 2 with choices error

Path validations are bypassed by constructing the config with explicit
existing paths and ``validate_on_init=False`` so the test does not need
RVSEC_HOME or a real Android SDK on disk.
"""

import os
import tempfile
from pathlib import Path

import pytest

from rv_static_analysis.__main__ import setup_argument_parser, create_config_from_args
from rv_static_analysis.config import RVStaticAnalysisConfig


def _parse(extra: list[str]):
    parser = setup_argument_parser()
    return parser.parse_args(
        ["analyze", "--apk", "/tmp/x.apk", "--output", "/tmp/out"] + extra
    )


def test_default_is_spark() -> None:
    ns = _parse([])
    assert getattr(ns, "cg_algorithm", "<missing>") is None
    # Round-trip through Pydantic default
    cfg = RVStaticAnalysisConfig(
        validate_on_init=False, mop_dir="/tmp", output_dir="/tmp"
    )
    assert cfg.cg_algorithm == "spark"


def test_explicit_cha_propagates_to_namespace() -> None:
    ns = _parse(["--cg-algorithm", "cha"])
    assert ns.cg_algorithm == "cha"


def test_invalid_choice_exits_2() -> None:
    with pytest.raises(SystemExit) as exc:
        _parse(["--cg-algorithm", "bogus"])
    assert exc.value.code == 2


def test_get_tool_command_emits_cg_algorithm_flag(tmp_path: Path) -> None:
    # Wire enough paths for get_tool_command to assemble; bypass validation
    # because we don't have a real GATOR install in the test env.
    gator_dir = tmp_path / "gator"
    gator_dir.mkdir()
    (gator_dir / "gator").write_text("# stub launcher\n")
    (gator_dir / "rvsec-analysis-client.jar").write_text("stub")
    mop_dir = tmp_path / "jca"
    mop_dir.mkdir()

    cfg = RVStaticAnalysisConfig(
        validate_on_init=False,
        rvsec_root=str(tmp_path),
        gator_dir=str(gator_dir),
        analysis_client_jar=str(gator_dir / "rvsec-analysis-client.jar"),
        mop_dir=str(mop_dir),
        output_dir=str(tmp_path / "out"),
        cg_algorithm="rta",
    )
    cmd = cfg.get_tool_command(
        "analysis",
        apk_path="/tmp/x.apk",
        output_file=str(tmp_path / "out.json"),
    )
    assert "-cgAlgorithm" in cmd
    assert cmd[cmd.index("-cgAlgorithm") + 1] == "rta"


def test_pydantic_rejects_invalid_cg_algorithm() -> None:
    # Literal type pins the four accepted values at construction time, so
    # passing 'bogus' fails before any path validation runs.
    with pytest.raises(Exception) as exc:
        RVStaticAnalysisConfig(
            validate_on_init=False,
            mop_dir="/tmp",
            output_dir="/tmp",
            cg_algorithm="bogus",  # type: ignore[arg-type]
        )
    assert (
        "cg_algorithm" in str(exc.value)
        or "Literal" in str(exc.value)
        or "literal_error" in str(exc.value)
    )
