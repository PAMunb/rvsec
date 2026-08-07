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

    def fake_run_cli(args, **kwargs):  # kwargs: log_path
        # Look at the APK arg (positional after "instrument")
        apk = Path(args[1])
        if apk.name == "bad.apk":
            raise subprocess.TimeoutExpired(cmd=["java", "-jar", "x"], timeout=1)
        # good.apk: simulate CLI writing the output APK
        (results_dir / "good.apk").write_bytes(b"signed")

    # Contract: apk_paths items are complete paths (not basenames).
    good_path = str(apks_dir / "good.apk")
    bad_path = str(apks_dir / "bad.apk")
    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch.object(DexlibInstrumentation, "_run_cli", side_effect=fake_run_cli),
    ):
        res = inst.instrument_apks(
            apks_dir=apks_dir,
            results_dir=results_dir,
            apk_paths=[good_path, bad_path],
        )

    assert res.success_count == 1, "good.apk should still succeed"
    assert bad_path in res.errors, "bad.apk should be demoted to error"
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

    def fake_run_cli(args, **kwargs):  # kwargs: log_path
        (results_dir / "ok.apk").write_bytes(b"signed")

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch.object(DexlibInstrumentation, "_run_cli", side_effect=fake_run_cli),
    ):
        inst.instrument_apks(
            apks_dir=apks_dir,
            results_dir=results_dir,
            # Contract: apk_paths items are complete paths (not basenames).
            apk_paths=[str(apks_dir / "ok.apk")],
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

    # Contract: apk_paths items are complete paths (not basenames).
    apk_path = str(apks_dir / "cryptoapp.apk")
    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch.object(DexlibInstrumentation, "_run_cli", return_value=None),
    ):
        res = inst.instrument_apks(
            apks_dir=apks_dir,
            results_dir=results_dir,
            apk_paths=[apk_path],
        )
    assert res.success_count == 0
    assert apk_path in res.errors
    assert "not created" in res.errors[apk_path].message


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

    def write_apk(args, **kwargs):  # kwargs: log_path
        # Simulate the CLI writing the output APK
        (results_dir / "cryptoapp.apk").write_bytes(b"PK\x03\x04stub-apk-out")

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch.object(DexlibInstrumentation, "_run_cli", side_effect=write_apk),
    ):
        res = inst.instrument_apks(
            apks_dir=apks_dir,
            results_dir=results_dir,
            # Contract: apk_paths items are complete paths (not basenames).
            apk_paths=[str(apks_dir / "cryptoapp.apk")],
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


# --- gh86 apk_paths complete-path contract ---------------------------------
# apk_paths items are complete paths. The wrapper resolves them as-is and must
# NOT re-join with apks_dir (which duplicated the directory prefix, e.g.
# apks_examples/apks_examples/cryptoapp.apk). The success cross-check computes
# the output as results_dir/<basename>, so an absolute or relative input path
# can no longer discard results_dir and defeat the silent-failure guard.


@pytest.mark.parametrize("absolute", [False, True])
def test_apk_paths_complete_path_no_duplicate_prefix(
    tmp_workspace, monkeypatch, absolute
):
    """Regression (gh86): a complete apk_paths item resolves as-is (no
    duplicated apks_dir segment) and the output cross-check lands at
    results_dir/<basename>. Covers a relative-prefixed path (resolved against
    a controlled cwd) and an absolute path."""
    _seed_descriptor(tmp_workspace)
    root = tmp_workspace["root"]
    # A named input dir so a duplicated re-join would be visible in the path.
    apks_dir = root / "apks_examples"
    apks_dir.mkdir()
    (apks_dir / "cryptoapp.apk").write_bytes(b"PK\x03\x04stub")
    results_dir = root / "results"
    results_dir.mkdir()

    if absolute:
        apk_arg = str(apks_dir / "cryptoapp.apk")
    else:
        # Relative-prefixed path resolves against cwd; pin cwd to root so the
        # bare "apks_examples/cryptoapp.apk" points at the seeded file.
        monkeypatch.chdir(root)
        apk_arg = "apks_examples/cryptoapp.apk"

    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    inst = DexlibInstrumentation(cfg)

    captured = {}

    def fake_run_cli(args, **kwargs):  # kwargs: log_path
        # The wrapper passes the resolved input path as argv[1] to instr-cli.
        captured["apk_arg"] = args[1]
        # Simulate the CLI writing the output APK by basename.
        (results_dir / "cryptoapp.apk").write_bytes(b"signed")

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch.object(DexlibInstrumentation, "_run_cli", side_effect=fake_run_cli),
    ):
        res = inst.instrument_apks(
            apks_dir=apks_dir,
            results_dir=results_dir,
            apk_paths=[apk_arg],
        )

    # Input resolved as-is — no duplicated apks_examples/ segment.
    assert captured["apk_arg"] == apk_arg
    assert "apks_examples/apks_examples" not in captured["apk_arg"]
    # Success is credited only if the output cross-check found the APK at
    # results_dir/<basename>; the buggy results_dir/<name> would look under
    # results_dir/apks_examples/ (relative) and demote to error.
    assert res.success_count == 1
    assert res.errors == {}
    assert (results_dir / "cryptoapp.apk").is_file()


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
        "rv-monitor-rt-0.9.3-SNAPSHOT.jar",
        "rvsec-core-0.9.3-SNAPSHOT.jar",
        "rvsec-logger-logcat-0.9.3-SNAPSHOT.jar",
        "aspectjrt-1.9.7.jar",
    ]
    with patch("subprocess.run", side_effect=_fake_mvn_writes(mvn_jars)):
        inst.prepare_instrumentation()

    classpath_names = {p.name for p in cfg.extra_classpath}
    assert classpath_names == {
        "rv-monitor-rt-0.9.3-SNAPSHOT.jar",
        "rvsec-core-0.9.3-SNAPSHOT.jar",
        "rvsec-logger-logcat-0.9.3-SNAPSHOT.jar",
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
        "rv-monitor-rt-0.9.3-SNAPSHOT.jar",
        "rvsec-core-0.9.3-SNAPSHOT.jar",
        "rvsec-logger-logcat-0.9.3-SNAPSHOT.jar",
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
        "rv-monitor-rt-0.9.3-SNAPSHOT.jar",
        "rvsec-core-0.9.3-SNAPSHOT.jar",
        "rvsec-logger-logcat-0.9.3-SNAPSHOT.jar",
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


# --- gh100: weaver counters reach Python on the production path -------------
# The `apk_paths` branch is what rv-experiment actually runs, and it used to
# invoke `instrument` without --results-json — an option that existed only on
# `batch`. The file was therefore never written, which is why a results tree
# holds instrument_errors.json files and no instrument_results.json at all
# (INV-INS-105). These tests pin the repaired path end to end on the Python
# side: argv carries the flag, the per-APK files are merged, and the counters
# survive into InstrumentationResults.


def _fake_per_apk_run(results_dir, counts_by_apk, land_apk=True):
    """Build a `subprocess.run` stub that mimics the Java `instrument` CLI.

    Writes the results JSON at whatever path argv names and, unless
    ``land_apk`` is False, drops the output APK into ``results_dir`` so the
    wrapper's silent-failure guard is satisfied.
    """

    def fake_run(cmd, **kwargs):
        apk_path = Path(cmd[cmd.index("instrument") + 1])
        out_json = Path(cmd[cmd.index("--results-json") + 1])
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(
            json.dumps(
                {
                    "variant": "dexlib2",
                    "results": [
                        {
                            "apkName": apk_path.name,
                            "success": True,
                            "message": "instrumented + signed",
                            "phase": "signed",
                            "weaveCounts": counts_by_apk[apk_path.name],
                        }
                    ],
                }
            )
        )
        if land_apk:
            results_dir.mkdir(parents=True, exist_ok=True)
            (results_dir / apk_path.name).write_bytes(b"woven")

        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        return _R()

    return fake_run


def _apk_paths_workspace(tmp_workspace, names):
    _seed_descriptor(tmp_workspace)
    apks_dir = tmp_workspace["root"] / "apks"
    apks_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in names:
        apk = apks_dir / name
        apk.write_bytes(b"stub")
        paths.append(str(apk))
    cfg = DexlibInstrumentationConfig(
        cli_jar_path=tmp_workspace["cli_jar"],
        monitor_output_dir=tmp_workspace["monitors"],
        instrumented_dir=tmp_workspace["instrumented"],
        working_dir=tmp_workspace["work"],
    )
    return DexlibInstrumentation(cfg), apks_dir, paths


def test_apk_paths_argv_carries_results_json(tmp_workspace):
    inst, apks_dir, paths = _apk_paths_workspace(tmp_workspace, ["one.apk"])
    results_dir = tmp_workspace["root"] / "results"
    captured = {}

    fake = _fake_per_apk_run(results_dir, {"one.apk": {"matchesApplied": 5}})

    def spy(cmd, **kwargs):
        captured["cmd"] = cmd
        return fake(cmd, **kwargs)

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch("subprocess.run", side_effect=spy),
    ):
        inst.instrument_apks(apks_dir, results_dir, apk_paths=paths)

    cmd = captured["cmd"]
    assert "instrument" in cmd
    assert "--results-json" in cmd, (
        "the production single-APK path must request the weaver's counters; "
        "without the flag the Java CLI writes nothing (INV-INS-105)"
    )
    # One file per APK — a shared path would have each run overwrite the last.
    named = Path(cmd[cmd.index("--results-json") + 1])
    assert named.parent == results_dir / "instrument_results.d"
    assert named.name == "one.apk.json".replace(".apk", "")


def test_apk_paths_merges_per_apk_results_and_counters(tmp_workspace):
    inst, apks_dir, paths = _apk_paths_workspace(
        tmp_workspace, ["one.apk", "two.apk"]
    )
    results_dir = tmp_workspace["root"] / "results"
    counts = {
        "one.apk": {"matchesApplied": 5, "plansSkippedHighRegister": 0},
        "two.apk": {"matchesApplied": 9, "plansSkippedHighRegister": 2},
    }

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch("subprocess.run", side_effect=_fake_per_apk_run(results_dir, counts)),
    ):
        results = inst.instrument_apks(apks_dir, results_dir, apk_paths=paths)

    merged = results_dir / "instrument_results.json"
    assert merged.is_file(), (
        "the apk_paths path must leave the same artefact the batch path does"
    )
    body = json.loads(merged.read_text())
    assert body["variant"] == "dexlib2"
    assert {e["apkName"] for e in body["results"]} == {"one.apk", "two.apk"}

    assert results.success_count == 2
    assert results.total_count == 2
    assert results.errors == {}
    assert results.weave_counts == counts
    # The counter task 6.4 reads, to tell whether emitting N invokes instead
    # of 1 pushed any site over its register budget.
    assert results.weave_counts["two.apk"]["plansSkippedHighRegister"] == 2


def test_apk_paths_keeps_counters_for_an_apk_that_never_landed(tmp_workspace):
    """A run the guard demotes is the one whose counters matter most."""
    inst, apks_dir, paths = _apk_paths_workspace(tmp_workspace, ["ghost.apk"])
    results_dir = tmp_workspace["root"] / "results"
    counts = {"ghost.apk": {"matchesApplied": 3}}

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch(
            "subprocess.run",
            side_effect=_fake_per_apk_run(results_dir, counts, land_apk=False),
        ),
    ):
        results = inst.instrument_apks(apks_dir, results_dir, apk_paths=paths)

    # The CLI claimed success but no APK landed: the wrapper's cross-check
    # demotes it, and the counters still come through.
    assert results.success_count == 0
    assert results.total_count == 1
    # The apk_paths loop keys errors by the caller's path string, while the
    # weaver keys its counters by APK basename. Both are pinned here because
    # the two maps genuinely use different keys.
    assert results.errors and all("ghost.apk" in k for k in results.errors)
    assert results.weave_counts == counts


def test_parse_results_json_carries_weave_counts(tmp_workspace):
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
                        "apkName": "a.apk",
                        "success": True,
                        "message": "ok",
                        "phase": "signed",
                        "weaveCounts": {"matchesApplied": 7},
                    },
                    {
                        "apkName": "b.apk",
                        "success": False,
                        "message": "boom",
                        "phase": "io_error",
                        "weaveCounts": {"matchesApplied": 0},
                    },
                ],
            }
        )
    )
    results = inst._parse_results_json(path)
    assert results.success_count == 1
    assert results.total_count == 2
    assert results.weave_counts == {
        "a.apk": {"matchesApplied": 7},
        "b.apk": {"matchesApplied": 0},
    }


def test_demote_silent_failures_preserves_weave_counts(tmp_workspace):
    from rv_instrumentation_core import InstrumentationResults
    from rv_instrumentation_dexlib2.dexlib_instrumentation import (
        _demote_silent_failures,
    )

    results_dir = tmp_workspace["instrumented"]
    (results_dir / "instrument_results.json").write_text(
        json.dumps(
            {
                "variant": "dexlib2",
                "results": [
                    {"apkName": "gone.apk", "success": True, "phase": "signed"}
                ],
            }
        )
    )
    before = InstrumentationResults(
        success_count=1,
        total_count=1,
        errors={},
        weave_counts={"gone.apk": {"matchesApplied": 4}},
        variant="dexlib2",
    )

    after = _demote_silent_failures(before, results_dir)

    assert after.success_count == 0
    assert "gone.apk" in after.errors
    assert after.weave_counts == {"gone.apk": {"matchesApplied": 4}}


def test_apk_paths_persists_the_cli_log(tmp_workspace):
    """The weaver's stdout is the only place the resolved android.jar appears.

    ``capture_output=True`` takes it out of the terminal, so unless the wrapper
    writes it down the platform jar a weave actually used is unrecoverable
    afterwards — which is what the android.jar log line exists to prevent.
    """
    inst, apks_dir, paths = _apk_paths_workspace(tmp_workspace, ["one.apk"])
    results_dir = tmp_workspace["root"] / "results"
    base = _fake_per_apk_run(results_dir, {"one.apk": {"matchesApplied": 1}})

    def fake(cmd, **kwargs):
        proc = base(cmd, **kwargs)
        proc.stdout = "[dexlib2] one.apk: android.jar = /sdk/platforms/android-34/android.jar"
        return proc

    with (
        patch.object(DexlibInstrumentation, "prepare_instrumentation"),
        patch("subprocess.run", side_effect=fake),
    ):
        inst.instrument_apks(apks_dir, results_dir, apk_paths=paths)

    log = results_dir / "instrument_results.d" / "one.log"
    assert log.is_file(), "the CLI output must survive the subprocess"
    assert "android.jar = /sdk/platforms/android-34/android.jar" in log.read_text()
