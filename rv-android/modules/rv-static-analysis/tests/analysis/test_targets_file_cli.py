"""
End-to-end CLI plumbing for ``--targets-file``.

Verify that an analyze invocation with a synthetic targets file produces a
GATOR command line carrying ``-clientParam targetsFile=<path>`` (and NOT
``-clientParam mopDir=...``). Path validations are bypassed by constructing
the config with ``validate_on_init=False`` and a real targets file on disk.
"""

from pathlib import Path

from rv_static_analysis.config import RVStaticAnalysisConfig


def _make_config(tmp_path: Path, targets_file: Path) -> RVStaticAnalysisConfig:
    gator_dir = tmp_path / "gator"
    gator_dir.mkdir()
    (gator_dir / "gator").write_text("# stub launcher\n")
    (gator_dir / "rvsec-analysis-client.jar").write_text("stub")
    return RVStaticAnalysisConfig(
        validate_on_init=False,
        rvsec_root=str(tmp_path),
        gator_dir=str(gator_dir),
        analysis_client_jar=str(gator_dir / "rvsec-analysis-client.jar"),
        targets_file=str(targets_file),
        output_dir=str(tmp_path / "out"),
    )


def test_targets_file_emits_targetsFile_client_param(tmp_path: Path) -> None:
    sig = tmp_path / "demo-targets.txt"
    sig.write_text("<javax.crypto.Cipher: void init(int,java.security.Key)>\n")

    cfg = _make_config(tmp_path, sig)
    cmd = cfg.get_tool_command(
        "analysis",
        apk_path="/tmp/x.apk",
        output_file=str(tmp_path / "out.json"),
    )

    # find the client-param for the target source
    target_params = [
        cmd[i + 1]
        for i, tok in enumerate(cmd)
        if tok == "-clientParam"
        and (cmd[i + 1].startswith("targetsFile=") or cmd[i + 1].startswith("mopDir="))
    ]
    assert (
        len(target_params) == 1
    ), f"Expected exactly one target-source clientParam, got {target_params}"
    assert target_params[0].startswith("targetsFile=")
    assert target_params[0].endswith(str(sig))


def test_mop_dir_emits_mopDir_client_param(tmp_path: Path) -> None:
    gator_dir = tmp_path / "gator"
    gator_dir.mkdir()
    (gator_dir / "gator").write_text("# stub\n")
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
    )
    cmd = cfg.get_tool_command(
        "analysis",
        apk_path="/tmp/x.apk",
        output_file=str(tmp_path / "out.json"),
    )

    target_params = [
        cmd[i + 1]
        for i, tok in enumerate(cmd)
        if tok == "-clientParam"
        and (cmd[i + 1].startswith("targetsFile=") or cmd[i + 1].startswith("mopDir="))
    ]
    assert len(target_params) == 1
    assert target_params[0].startswith("mopDir=")
    assert target_params[0].endswith(str(mop_dir))
