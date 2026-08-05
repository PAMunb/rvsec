"""End-to-end: from the CLI flag to the `codePackage=` argument GATOR receives.

The unit tests around this change each cover one seam. This file follows a
single decision across all of them — argparse flag, `RV_PACKAGE_DETECTOR`,
`App`, `StaticAnalyzer`, `RVStaticAnalysisConfig.get_tool_command` — and asserts
on the real argv list, not on a mock's call record.

Only androguard is stubbed. An APK fixture cannot be committed (the corpora live
outside the repo and are gitignored), so `APK` is replaced by a stub declaring a
chosen package; every other component in the chain is the production one,
including the config that assembles the command line.

Two fixtures, matching the two cases the change exists for:

- a Godot game declaring `ir.hsn6.trans` whose implementation classes live under
  `org.godotengine.godot` — the case that justifies keeping the detector;
- `org.fossify.calendar_20.apk` declaring `org.fossify.calendar.debug` — the
  case that justifies the manifest default. Verified against the real APK of the
  gh91 dataset: the declared value carries the `.debug` suffix, the default
  returns it verbatim, and the detector elects `org.fossify`.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.util.android.package_detector import PackageDetectionResult
from rv_static_analysis.__main__ import main
from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer
from rv_static_analysis.config import RVStaticAnalysisConfig

GODOT_MANIFEST = "ir.hsn6.trans"
GODOT_CODE = "org.godotengine.godot"
SUFFIXED_MANIFEST = "org.fossify.calendar.debug"


@pytest.fixture
def analysis_config(tmp_path: Path) -> RVStaticAnalysisConfig:
    """A real config over a skeleton tree, so `get_tool_command` runs for real."""
    lib_dir = tmp_path / "lib"
    gator_dir = lib_dir / "gator"
    gator_dir.mkdir(parents=True)
    launcher = gator_dir / "gator"
    launcher.touch()
    launcher.chmod(0o755)
    client_jar = gator_dir / "rvsec-analysis-client.jar"
    client_jar.touch()

    android_platforms = tmp_path / "android" / "platforms"
    android_jar = android_platforms / "android-29" / "android.jar"
    android_jar.parent.mkdir(parents=True)
    android_jar.touch()

    mop_dir = tmp_path / "specs" / "jca"
    mop_dir.mkdir(parents=True)
    (mop_dir / "test.mop").touch()

    return RVStaticAnalysisConfig(
        lib_dir=str(lib_dir),
        android_platforms_dir=str(android_platforms),
        android_jar=str(android_jar),
        mop_dir=str(mop_dir),
        output_dir=str(tmp_path / "output"),
        working_dir=str(tmp_path / "working"),
        gator_dir=str(gator_dir),
        analysis_client_jar=str(client_jar),
    )


@pytest.fixture
def apk_file(tmp_path: Path) -> Path:
    """A file that passes the CLI's path checks; androguard never reads it."""
    apk = tmp_path / "org.fossify.calendar_20.apk"
    apk.write_bytes(b"PK\x03\x04")
    return apk


def _apk_stub(manifest_package: str) -> MagicMock:
    apk = MagicMock()
    apk.get_package.return_value = manifest_package
    return apk


def _detector_stub(manifest_package: str, elected: str) -> MagicMock:
    detector_cls = MagicMock()
    detector_cls.return_value.detect_package.return_value = PackageDetectionResult(
        manifest_package=manifest_package,
        code_package=elected,
        confidence="high",
        detection_method="game_engine",
        game_engine="godot",
    )
    return detector_cls


def _run_cli(argv, env, apk_file, analysis_config, manifest_package, detector_stub):
    """Drive `rv-static-analysis analyze` and return the argv GATOR would get.

    `Command` is intercepted at the point of invocation, so the assertion is on
    the list the production config actually built.
    """
    captured: dict = {}

    def _capture_command(executable, args, timeout=None):
        captured["argv"] = [executable, *args]
        instance = MagicMock()
        instance.invoke.return_value = MagicMock(code=0, stdout="", stderr="")
        return instance

    with (
        patch(
            "sys.argv",
            [
                "rv-static-analysis",
                "analyze",
                "--apk",
                str(apk_file),
                "--output",
                analysis_config.output_dir,
                *argv,
            ],
        ),
        patch.dict("os.environ", env, clear=True),
        patch(
            "rv_static_analysis.__main__.create_config_from_args",
            return_value=analysis_config,
        ),
        patch(
            "rv_android_core.domain.app.APK", return_value=_apk_stub(manifest_package)
        ),
        patch("rv_android_core.domain.app.PackageDetector", detector_stub),
        patch(
            "rv_static_analysis.analysis.static.static_analysis.Command",
            side_effect=_capture_command,
        ),
        patch("os.path.isfile", return_value=True),
    ):
        exit_code = main()

    return exit_code, captured.get("argv", [])


def _client_param(argv: list[str], name: str) -> str | None:
    """Return the value of a `-clientParam <name>=<value>` pair, if present."""
    prefix = f"{name}="
    for flag, value in zip(argv, argv[1:]):
        if flag == "-clientParam" and value.startswith(prefix):
            return value[len(prefix) :]
    return None


# ---------------------------------------------------------------------------
# 7.1 — declared package differs from the implementation package
# ---------------------------------------------------------------------------


def test_default_sends_the_declared_package_to_gator(
    apk_file, analysis_config, tmp_path
):
    """No flag, no variable: GATOR filters on what the APK calls itself."""
    exit_code, argv = _run_cli(
        [],
        {},
        apk_file,
        analysis_config,
        GODOT_MANIFEST,
        _detector_stub(GODOT_MANIFEST, GODOT_CODE),
    )

    assert exit_code == 0
    assert _client_param(argv, "codePackage") == GODOT_MANIFEST


def test_flag_sends_the_elected_package_to_gator(apk_file, analysis_config):
    """`--package-detector`: GATOR filters on the heuristic election."""
    exit_code, argv = _run_cli(
        ["--package-detector"],
        {},
        apk_file,
        analysis_config,
        GODOT_MANIFEST,
        _detector_stub(GODOT_MANIFEST, GODOT_CODE),
    )

    assert exit_code == 0
    assert _client_param(argv, "codePackage") == GODOT_CODE


def test_env_var_reaches_gator_on_a_standalone_invocation(apk_file, analysis_config):
    """A standalone run is a run: it honours RV_PACKAGE_DETECTOR itself (D4)."""
    exit_code, argv = _run_cli(
        [],
        {"RV_PACKAGE_DETECTOR": "true"},
        apk_file,
        analysis_config,
        GODOT_MANIFEST,
        _detector_stub(GODOT_MANIFEST, GODOT_CODE),
    )

    assert exit_code == 0
    assert _client_param(argv, "codePackage") == GODOT_CODE


def test_negative_flag_beats_the_environment_all_the_way_to_gator(
    apk_file, analysis_config
):
    exit_code, argv = _run_cli(
        ["--no-package-detector"],
        {"RV_PACKAGE_DETECTOR": "true"},
        apk_file,
        analysis_config,
        GODOT_MANIFEST,
        _detector_stub(GODOT_MANIFEST, GODOT_CODE),
    )

    assert exit_code == 0
    assert _client_param(argv, "codePackage") == GODOT_MANIFEST


# ---------------------------------------------------------------------------
# 7.2 — a build-type suffix survives untouched
# ---------------------------------------------------------------------------


def test_a_suffixed_application_id_reaches_gator_verbatim(apk_file, analysis_config):
    """No segment is stripped: normalization belongs to the corpus, not the tool."""
    exit_code, argv = _run_cli(
        [],
        {},
        apk_file,
        analysis_config,
        SUFFIXED_MANIFEST,
        _detector_stub(SUFFIXED_MANIFEST, "org.fossify"),
    )

    assert exit_code == 0
    assert _client_param(argv, "codePackage") == SUFFIXED_MANIFEST


def test_the_run_records_the_suffixed_key_and_its_origin(apk_file, analysis_config):
    """The result states the key, because the artefact cannot (INV-ANA-58).

    The analyzer runs for real; it is only observed, by keeping the instance the
    CLI built so its result can be inspected after the command returns.
    """
    built: list[StaticAnalyzer] = []

    def _spy(*args, **kwargs):
        analyzer = StaticAnalyzer(*args, **kwargs)
        built.append(analyzer)
        return analyzer

    with patch("rv_static_analysis.__main__.StaticAnalyzer", _spy):
        exit_code, argv = _run_cli(
            [],
            {},
            apk_file,
            analysis_config,
            SUFFIXED_MANIFEST,
            _detector_stub(SUFFIXED_MANIFEST, "org.fossify"),
        )

    assert exit_code == 0
    result = built[0].result
    assert result.code_package == SUFFIXED_MANIFEST
    assert result.code_package_source == "manifest"
    # The recorded key is the one GATOR was given, not a second opinion.
    assert _client_param(argv, "codePackage") == result.code_package
