"""Unit tests for the DexlibInstrumentation Python wrapper.

End-to-end tests against a real fixture APK + real Java CLI are covered by
integration tests under task 9.5. The tests here exercise only the Python
side: config shape, error paths, and results-JSON parsing.
"""

import json
from pathlib import Path

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
