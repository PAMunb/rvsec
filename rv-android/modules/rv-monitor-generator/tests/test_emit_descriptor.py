"""Tests for the emit_descriptor flag added by gh52-instr-dexlib2.

Covers tasks 11.4 and 11.5: verify that the flag defaults to True, that
it appears in the JavaMOP command only when enabled, and that the
generation summary reports the descriptor count independently of the
flag's current value (the summary simply counts *.MonitorAspect.json
files in the output directory).

Spec-set agnostic — the same emit_descriptor path runs for both JCA
and Generic specification sets. The tests below use JCA fixtures only
because that is what the existing test infrastructure already carries;
a generic-set variation is a pure parameterization away.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from rv_monitor_generator.config import RVGeneratorConfig
from rv_monitor_generator.runtime_verification_generator import (
    RuntimeVerificationGenerator,
)


@pytest.fixture
def minimal_config(tmp_path):
    """Construct a config by mocking path resolution — no real RVSEC_HOME required."""
    javamop = tmp_path / "javamop"
    rvmonitor = tmp_path / "rvmonitor"
    specs = tmp_path / "specs"
    aspects = tmp_path / "aspects"
    for p in (javamop, rvmonitor):
        p.write_text("#!/bin/sh\nexit 0\n")
        p.chmod(0o755)
    specs.mkdir()
    (specs / "Dummy.mop").write_text("DummySpec() {}")
    aspects.mkdir()
    (aspects / "Coverage.aj").write_text("aspect Coverage {}")

    with patch(
        "rv_monitor_generator.config.RVGeneratorConfig._validate_tool_functionality"
    ):
        cfg = RVGeneratorConfig(
            javamop_bin=str(javamop),
            rvmonitor_bin=str(rvmonitor),
            mop_specs_dir=str(specs),
            aspects_dir=str(aspects),
        )
    return cfg


def test_emit_descriptor_defaults_to_true(minimal_config):
    assert minimal_config.emit_descriptor is True


def test_emit_descriptor_can_be_disabled(tmp_path):
    javamop = tmp_path / "javamop"
    rvmonitor = tmp_path / "rvmonitor"
    specs = tmp_path / "specs"
    aspects = tmp_path / "aspects"
    for p in (javamop, rvmonitor):
        p.write_text("#!/bin/sh\nexit 0\n")
        p.chmod(0o755)
    specs.mkdir()
    (specs / "Dummy.mop").write_text("DummySpec() {}")
    aspects.mkdir()
    with patch(
        "rv_monitor_generator.config.RVGeneratorConfig._validate_tool_functionality"
    ):
        cfg = RVGeneratorConfig(
            javamop_bin=str(javamop),
            rvmonitor_bin=str(rvmonitor),
            mop_specs_dir=str(specs),
            aspects_dir=str(aspects),
            emit_descriptor=False,
        )
    assert cfg.emit_descriptor is False


@patch("rv_monitor_generator.runtime_verification_generator.utils.execute_command")
def test_javamop_command_includes_emit_descriptor_when_enabled(
    mock_exec, minimal_config, tmp_path
):
    out = tmp_path / "out"
    out.mkdir()
    gen = RuntimeVerificationGenerator(minimal_config)
    gen._execute_javamop(str(out))

    # One call to JavaMOP; its args must contain --emit-descriptor.
    assert mock_exec.called, "JavaMOP was not invoked"
    cmd = mock_exec.call_args[0][0]
    assert "--emit-descriptor" in cmd.args, (
        "emit_descriptor=True MUST pass --emit-descriptor; got " + repr(cmd.args)
    )
    # Sanity: -d and -merge still present.
    assert "-d" in cmd.args
    assert "-merge" in cmd.args


@patch("rv_monitor_generator.runtime_verification_generator.utils.execute_command")
def test_javamop_command_omits_emit_descriptor_when_disabled(mock_exec, tmp_path):
    javamop = tmp_path / "javamop"
    rvmonitor = tmp_path / "rvmonitor"
    specs = tmp_path / "specs"
    aspects = tmp_path / "aspects"
    for p in (javamop, rvmonitor):
        p.write_text("#!/bin/sh\nexit 0\n")
        p.chmod(0o755)
    specs.mkdir()
    (specs / "Dummy.mop").write_text("DummySpec() {}")
    aspects.mkdir()
    with patch(
        "rv_monitor_generator.config.RVGeneratorConfig._validate_tool_functionality"
    ):
        cfg = RVGeneratorConfig(
            javamop_bin=str(javamop),
            rvmonitor_bin=str(rvmonitor),
            mop_specs_dir=str(specs),
            aspects_dir=str(aspects),
            emit_descriptor=False,
        )
    out = tmp_path / "out"
    out.mkdir()
    gen = RuntimeVerificationGenerator(cfg)
    gen._execute_javamop(str(out))
    cmd = mock_exec.call_args[0][0]
    assert "--emit-descriptor" not in cmd.args, (
        "emit_descriptor=False MUST NOT pass the flag; got " + repr(cmd.args)
    )


def test_summary_counts_descriptor_files(minimal_config, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    # Fabricate descriptor files so the summary counter finds them.
    (out / "MultiSpec_1MonitorAspect.json").write_text("{}")
    (out / "MultiSpec_2MonitorAspect.json").write_text("{}")
    (out / "OtherFile.txt").write_text("ignored")

    gen = RuntimeVerificationGenerator(minimal_config)
    summary = gen.get_generation_summary(str(out))
    assert summary["descriptors"] == 2, (
        "descriptors count must include only *.MonitorAspect.json files; "
        "got " + repr(summary)
    )


def test_summary_descriptors_zero_when_absent(minimal_config, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    gen = RuntimeVerificationGenerator(minimal_config)
    summary = gen.get_generation_summary(str(out))
    assert summary["descriptors"] == 0
