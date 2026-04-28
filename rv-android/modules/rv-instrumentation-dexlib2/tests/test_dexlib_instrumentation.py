"""Unit tests for the DexlibInstrumentation Python wrapper.

End-to-end tests against a real fixture APK + real Java CLI are covered by
integration tests under task 9.5. The tests here exercise only the Python
side: config shape, error paths, results-JSON parsing, and the CLI argv
contract (task 12.7 — wrapper-side parity check, no real subprocess).
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from rv_instrumentation_dexlib2 import (
    DexlibInstrumentation,
    DexlibInstrumentationConfig,
    MissingDescriptorError,
)


@pytest.fixture
def tmp_workspace(tmp_path):
    monitors = tmp_path / "monitors"
    instrumented = tmp_path / "instrumented"
    work = tmp_path / "work"
    monitors.mkdir()
    instrumented.mkdir()
    work.mkdir()
    cli_jar = tmp_path / "lib" / "instr-cli.jar"
    cli_jar.parent.mkdir()
    cli_jar.write_bytes(b"stub")
    return {
        "root": tmp_path,
        "monitors": monitors,
        "instrumented": instrumented,
        "work": work,
        "cli_jar": cli_jar,
    }


def test_config_variant_default_matches_ajc(tmp_workspace):
    # Smoke: config model accepts the minimal field set without errors.
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    assert cfg.descriptor_glob == "MultiSpec_*MonitorAspect.json"
    assert cfg.timeout_seconds == 600


def test_prepare_raises_when_no_descriptor(tmp_workspace):
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)
    with pytest.raises(MissingDescriptorError) as ex:
        inst.prepare_instrumentation()
    assert "emit_descriptor" in str(ex.value)


def test_prepare_raises_when_cli_jar_missing(tmp_workspace):
    # Drop a descriptor but delete the jar to trigger the second gate.
    desc = tmp_workspace["monitors"] / "MultiSpec_1MonitorAspect.json"
    desc.write_text("{}")
    tmp_workspace["cli_jar"].unlink()
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)
    with pytest.raises(FileNotFoundError):
        inst.prepare_instrumentation()


def test_parse_results_json_success(tmp_workspace):
    desc = tmp_workspace["monitors"] / "MultiSpec_1MonitorAspect.json"
    desc.write_text("{}")
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)
    path = tmp_workspace["instrumented"] / "instrument_results.json"
    path.write_text(json.dumps({
        "variant": "dexlib2",
        "results": [
            {"apkName": "one.apk", "success": True, "message": "ok",
             "phase": "dexlib2_pipeline", "weaveCounts": {}},
            {"apkName": "two.apk", "success": False, "message": "parse failed",
             "phase": "descriptor_read", "weaveCounts": {}},
        ],
    }))
    results = inst._parse_results_json(path)
    assert results.variant == "dexlib2"
    assert results.success_count == 1
    assert results.total_count == 2
    assert "two.apk" in results.errors
    assert results.errors["two.apk"].phase == "descriptor_read"


def test_parse_results_json_absent(tmp_workspace):
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)
    path = tmp_workspace["instrumented"] / "nope.json"
    results = inst._parse_results_json(path)
    assert results.variant == "dexlib2"
    assert results.success_count == 0
    assert "__run__" in results.errors


# --- task 12.7: wrapper → Java CLI argv contract ----------------------------
# The wrapper assembles the argv passed to instr-cli; these tests pin the
# contract so a future refactor cannot silently drop --monitor-src-dir or
# --keystore (which would downgrade the pipeline to phase=dex_only without
# any error surfacing).


def _seed_descriptor(workspace):
    desc = workspace["monitors"] / "MultiSpec_1MonitorAspect.json"
    desc.write_text("{}")
    return desc


def test_batch_argv_includes_monitor_src_dir(tmp_workspace):
    _seed_descriptor(tmp_workspace)
    results_dir = tmp_workspace["root"] / "results"
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        # Synthesize the results JSON the wrapper expects to parse.
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "instrument_results.json").write_text(
            json.dumps({"variant": "dexlib2", "results": []})
        )
        class _R:
            returncode = 0
            stderr = ""
            stdout = ""
        return _R()

    with patch("subprocess.run", side_effect=fake_run):
        inst.instrument_apks(tmp_workspace["root"] / "apks", results_dir)

    cmd = captured["cmd"]
    assert "batch" in cmd
    # Critical: --monitor-src-dir must point at monitor_output_dir, otherwise
    # the Java CLI stops at phase=dex_only and never produces a signed APK.
    i = cmd.index("--monitor-src-dir")
    assert Path(cmd[i + 1]) == tmp_workspace["monitors"]
    # --descriptor + --output + --work-dir + --results-json must also be present.
    for flag in ("--descriptor", "--output", "--work-dir", "--results-json"):
        assert flag in cmd, f"{flag} dropped from argv"


def test_instrument_argv_includes_keystore_when_configured(tmp_workspace):
    _seed_descriptor(tmp_workspace)
    keystore = tmp_workspace["root"] / "debug.keystore"
    keystore.write_bytes(b"stub")
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
        keystore_file=keystore,
        keystore_password="android",
    )
    inst = DexlibInstrumentation(cfg)

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        class _R:
            returncode = 0
            stderr = ""
            stdout = ""
        return _R()

    # Build a minimal App-shaped object — the wrapper only reads .apk_path
    # and .name, so a SimpleNamespace suffices.
    from types import SimpleNamespace
    app = SimpleNamespace(
        apk_path=tmp_workspace["root"] / "fake.apk",
        name="fake",
    )
    with patch("subprocess.run", side_effect=fake_run):
        inst.instrument(app, tmp_workspace["instrumented"])

    cmd = captured["cmd"]
    assert "--keystore" in cmd, "keystore_file set but --keystore not forwarded"
    assert "--keystore-pass" in cmd, "keystore_password set but --keystore-pass not forwarded"
    i = cmd.index("--keystore")
    assert Path(cmd[i + 1]) == keystore
