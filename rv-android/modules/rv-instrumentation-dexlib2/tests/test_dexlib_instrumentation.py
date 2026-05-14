"""Unit tests for the DexlibInstrumentation Python wrapper.

End-to-end tests against a real fixture APK + real Java CLI are covered by
integration tests under task 9.5. The tests here exercise only the Python
side: config shape, error paths, results-JSON parsing, and the CLI argv
contract (task 12.7 — wrapper-side parity check, no real subprocess).
"""

import json
import subprocess
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
    # timeout_seconds was removed in 9.22g (parity with AJC, which has no
    # wallclock timeout on dex2jar/ajc/d8/jarsigner). The CLI subprocess
    # now runs to completion regardless of duration.
    assert not hasattr(cfg, "timeout_seconds")


def test_subprocess_run_does_not_receive_timeout_kwarg(tmp_workspace):
    """Regression guard: ``_run_cli`` must NOT pass ``timeout=`` to
    ``subprocess.run``. Re-introducing a wallclock cap would silently
    break large APKs from the JCA-400 corpus (the original Phase 5 bug)."""
    _seed_descriptor(tmp_workspace)
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    captured_kwargs = {}

    def fake_run(cmd, **kwargs):
        captured_kwargs.update(kwargs)

        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        return _R()

    with patch("subprocess.run", side_effect=fake_run):
        inst._run_cli(["instrument", "/dev/null"])

    assert "timeout" not in captured_kwargs, (
        "subprocess.run called with timeout=; remove it — instrumentation "
        "is a build operation, weave time is bounded only by APK content."
    )


def test_subprocess_error_demoted_per_apk_not_propagated(tmp_workspace):
    """Defense in depth: if any ``SubprocessError`` (incl. TimeoutExpired
    from a hypothetical re-introduction) escapes ``_run_cli``, the wrapper
    must demote that single APK to error and continue with the rest, NOT
    abort the entire batch."""
    _seed_descriptor(tmp_workspace)
    apks_dir = tmp_workspace["root"] / "apks_in"
    apks_dir.mkdir()
    (apks_dir / "good.apk").write_bytes(b"PK\x03\x04stub")
    (apks_dir / "bad.apk").write_bytes(b"PK\x03\x04stub")
    results_dir = tmp_workspace["root"] / "results"
    results_dir.mkdir()

    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    def fake_run_cli(args):
        # Look at the APK arg (positional after "instrument")
        apk = Path(args[1])
        if apk.name == "bad.apk":
            raise subprocess.TimeoutExpired(cmd=["java", "-jar", "x"], timeout=1)
        # good.apk: simulate CLI writing the output APK
        (results_dir / "good.apk").write_bytes(b"signed")

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch.object(DexlibInstrumentation, "_run_cli", side_effect=fake_run_cli),
    ):
        res = inst.instrument_apks(
            apks_dir=apks_dir,
            results_dir=results_dir,
            apk_paths=["good.apk", "bad.apk"],
        )

    assert res.success_count == 1, "good.apk should still succeed"
    assert "bad.apk" in res.errors, "bad.apk should be demoted to error"
    assert res.total_count == 2


def test_persist_errors_json_writes_file(tmp_workspace):
    """``instrument_apks`` should persist ``instrument_errors.json`` to
    ``results_dir`` (paridade com AJC). Allows post-mortem of a batch run
    without re-tailing logs."""
    _seed_descriptor(tmp_workspace)
    apks_dir = tmp_workspace["root"] / "apks_in"
    apks_dir.mkdir()
    (apks_dir / "ok.apk").write_bytes(b"PK\x03\x04stub")
    results_dir = tmp_workspace["root"] / "results"
    results_dir.mkdir()

    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    def fake_run_cli(args):
        (results_dir / "ok.apk").write_bytes(b"signed")

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch.object(DexlibInstrumentation, "_run_cli", side_effect=fake_run_cli),
    ):
        inst.instrument_apks(
            apks_dir=apks_dir,
            results_dir=results_dir,
            apk_paths=["ok.apk"],
        )

    errors_file = results_dir / "instrument_errors.json"
    assert errors_file.is_file(), "instrument_errors.json must be persisted"
    payload = json.loads(errors_file.read_text())
    assert payload == {}, "successful run should produce empty errors map"


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
    path.write_text(
        json.dumps(
            {
                "variant": "dexlib2",
                "results": [
                    {
                        "apkName": "one.apk",
                        "success": True,
                        "message": "ok",
                        "phase": "dexlib2_pipeline",
                        "weaveCounts": {},
                    },
                    {
                        "apkName": "two.apk",
                        "success": False,
                        "message": "parse failed",
                        "phase": "descriptor_read",
                        "weaveCounts": {},
                    },
                ],
            }
        )
    )
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

    # prepare_instrumentation is exercised separately; this test pins only
    # the argv contract going INTO instr-cli. Stub it out so the new
    # mvn-driven runtime-libs resolution doesn't run during the argv check.
    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch("subprocess.run", side_effect=fake_run),
    ):
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
    assert (
        "--keystore-pass" in cmd
    ), "keystore_password set but --keystore-pass not forwarded"
    i = cmd.index("--keystore")
    assert Path(cmd[i + 1]) == keystore


# --- 9.22f4 wrapper guard: silent CLI failure detection -------------------
# The Java CLI's ``instrument`` subcommand can exit 0 even when javac/d8
# silently dropped the APK. Without the guard, the wrapper credits phantom
# successes (root cause of gh53 dexlib2 smoke producing 0% coverage).


def _seed_apk(workspace, apk_name="cryptoapp.apk"):
    apks_dir = workspace["root"] / "apks_in"
    apks_dir.mkdir(exist_ok=True)
    apk = apks_dir / apk_name
    apk.write_bytes(b"PK\x03\x04stub-apk")
    return apks_dir, apk


def test_wrapper_guard_apk_paths_demotes_when_apk_missing(tmp_workspace):
    """_run_cli succeeds (mock) but no APK is written → success_count=0."""
    _seed_descriptor(tmp_workspace)
    apks_dir, _apk = _seed_apk(tmp_workspace)
    results_dir = tmp_workspace["root"] / "results"
    results_dir.mkdir()
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch.object(DexlibInstrumentation, "_run_cli", return_value=None),
    ):
        res = inst.instrument_apks(
            apks_dir=apks_dir,
            results_dir=results_dir,
            apk_paths=["cryptoapp.apk"],
        )
    assert res.success_count == 0
    assert "cryptoapp.apk" in res.errors
    assert "not created" in res.errors["cryptoapp.apk"].message


def test_wrapper_guard_apk_paths_succeeds_when_apk_present(tmp_workspace):
    """_run_cli succeeds AND CLI 'wrote' the APK → success_count=1."""
    _seed_descriptor(tmp_workspace)
    apks_dir, _apk = _seed_apk(tmp_workspace)
    results_dir = tmp_workspace["root"] / "results"
    results_dir.mkdir()
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    def write_apk(args):
        # Simulate the CLI writing the output APK
        (results_dir / "cryptoapp.apk").write_bytes(b"PK\x03\x04stub-apk-out")

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch.object(DexlibInstrumentation, "_run_cli", side_effect=write_apk),
    ):
        res = inst.instrument_apks(
            apks_dir=apks_dir,
            results_dir=results_dir,
            apk_paths=["cryptoapp.apk"],
        )
    assert res.success_count == 1
    assert res.errors == {}


def test_wrapper_guard_batch_path_demotes_when_results_json_lies(tmp_workspace):
    """JSON says success: true but APK isn't there → demote to error."""
    _seed_descriptor(tmp_workspace)
    apks_dir = tmp_workspace["root"] / "apks_in"
    apks_dir.mkdir()
    results_dir = tmp_workspace["root"] / "results"
    results_dir.mkdir()

    # Simulate the CLI writing the results JSON with claimed success but
    # without producing the APK on disk.
    (results_dir / "instrument_results.json").write_text(
        json.dumps(
            {
                "variant": "dexlib2",
                "results": [
                    {
                        "apkName": "ghost.apk",
                        "success": True,
                        "phase": "signed",
                        "message": "ok",
                        "weaveCounts": {},
                    }
                ],
            }
        )
    )

    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch.object(DexlibInstrumentation, "_run_cli", return_value=None),
    ):
        res = inst.instrument_apks(
            apks_dir=apks_dir,
            results_dir=results_dir,
            # no apk_paths → batch path
        )
    assert res.success_count == 0
    assert "ghost.apk" in res.errors
    assert "not created" in res.errors["ghost.apk"].message


# --- 9.22f3 prepare_instrumentation Template Method integration -----------


def _seed_rvsec_root(tmp_path):
    """Create a minimal rvsec workspace layout that satisfies pom-existence checks."""
    rvsec_root = tmp_path / "rvsec_root"
    (rvsec_root / "rv-android").mkdir(parents=True)
    (rvsec_root / "rv-android" / "pom.xml").touch()
    return rvsec_root


def _fake_mvn_writes(jar_names):
    """side_effect that emulates ``mvn copy-dependencies`` populating the output dir."""

    def _run(cmd, **kwargs):
        out_dir = next(
            Path(a.split("=", 1)[1]) for a in cmd if a.startswith("-DoutputDirectory=")
        )
        for name in jar_names:
            (out_dir / name).touch()

        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        return _R()

    return _run


def test_prepare_instrumentation_appends_runtime_jars_to_extra_classpath(
    tmp_workspace, monkeypatch
):
    """prepare_instrumentation appends the 3 runtime jars (no aspectjrt)."""
    _seed_descriptor(tmp_workspace)
    rvsec_root = _seed_rvsec_root(tmp_workspace["root"])
    monkeypatch.setenv("RVSEC_HOME", str(rvsec_root))

    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    mvn_jars = [
        "rv-monitor-rt-0.9.0-SNAPSHOT.jar",
        "rvsec-core-0.9.0-SNAPSHOT.jar",
        "rvsec-logger-logcat-0.9.0-SNAPSHOT.jar",
        "aspectjrt-1.9.7.jar",
    ]
    with patch("subprocess.run", side_effect=_fake_mvn_writes(mvn_jars)):
        inst.prepare_instrumentation()

    classpath_names = {p.name for p in cfg.extra_classpath}
    assert classpath_names == {
        "rv-monitor-rt-0.9.0-SNAPSHOT.jar",
        "rvsec-core-0.9.0-SNAPSHOT.jar",
        "rvsec-logger-logcat-0.9.0-SNAPSHOT.jar",
    }


def test_prepare_instrumentation_allowlists_runtime_jars_regression(
    tmp_workspace, monkeypatch
):
    """Regression: dexlib2 keeps ONLY rv-monitor-rt + rvsec-core +
    rvsec-logger-logcat in extra_classpath. Everything else (aspectjrt,
    aspectjweaver, aspectjtools, kotlin-stdlib, surefire-*, annotations)
    pulled by ``mvn copy-dependencies`` is dropped — the Java CLI dexes
    every classpath entry into the APK, so noise jars would either
    inflate the APK or trigger d8 "Type defined multiple times" errors."""
    _seed_descriptor(tmp_workspace)
    rvsec_root = _seed_rvsec_root(tmp_workspace["root"])
    monkeypatch.setenv("RVSEC_HOME", str(rvsec_root))

    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    # Mirror the realistic mvn output captured from a real run (13 jars).
    mvn_jars = [
        "annotations-13.0.jar",
        "aspectjrt-1.9.25.1.jar",
        "aspectjtools-1.9.25.1.jar",
        "aspectjweaver-1.9.25.1.jar",
        "kotlin-stdlib-2.0.21.jar",
        "rv-monitor-rt-0.9.0-SNAPSHOT.jar",
        "rvsec-core-0.9.0-SNAPSHOT.jar",
        "rvsec-logger-logcat-0.9.0-SNAPSHOT.jar",
        "surefire-api-3.0.0-M7.jar",
        "surefire-booter-3.0.0-M7.jar",
        "surefire-extensions-spi-3.0.0-M7.jar",
        "surefire-logger-api-3.0.0-M7.jar",
        "surefire-shared-utils-3.0.0-M7.jar",
    ]
    with patch("subprocess.run", side_effect=_fake_mvn_writes(mvn_jars)):
        inst.prepare_instrumentation()

    names = {p.name for p in cfg.extra_classpath}
    assert names == {
        "rv-monitor-rt-0.9.0-SNAPSHOT.jar",
        "rvsec-core-0.9.0-SNAPSHOT.jar",
        "rvsec-logger-logcat-0.9.0-SNAPSHOT.jar",
    }


def test_prepare_instrumentation_calls_resolve_runtime_libs(tmp_workspace, monkeypatch):
    """Confirm that prepare_instrumentation routes through the ABC's Template Method."""
    _seed_descriptor(tmp_workspace)
    rvsec_root = _seed_rvsec_root(tmp_workspace["root"])
    monkeypatch.setenv("RVSEC_HOME", str(rvsec_root))

    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    sentinel_jars = [tmp_workspace["work"] / "lib_tmp" / "rv-monitor-rt-stub.jar"]
    with patch.object(
        DexlibInstrumentation, "_resolve_runtime_libs", return_value=sentinel_jars
    ) as spy:
        inst.prepare_instrumentation()
    assert spy.called
    args = spy.call_args.args
    # Args: (rvsec_root, lib_tmp_dir)
    assert args[0] == rvsec_root
    assert args[1] == tmp_workspace["work"] / "lib_tmp"
