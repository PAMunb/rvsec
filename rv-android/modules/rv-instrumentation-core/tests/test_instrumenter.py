"""Tests for the ``Instrumenter`` ABC contract.

Confirms fail-fast behaviour: subclasses missing ``instrument_apks`` cannot be
instantiated (``TypeError``). Concrete subclasses with the method override
instantiate cleanly and report through the shared ``InstrumentationResults``.
Also covers the ``_resolve_runtime_libs`` Template Method (Maven
copy-dependencies wrapper used by both AJC and dexlib2 variants).
"""

import inspect
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from rv_instrumentation_core import Instrumenter, InstrumentationResults


class _ConcreteInstrumenter(Instrumenter):
    """Helper subclass for tests that need to instantiate the ABC."""

    def instrument_apks(
        self, apks_dir, results_dir, force_instrumentation=False, apk_paths=None
    ):
        return InstrumentationResults()


def test_subclass_missing_instrument_apks_raises_typeerror():
    class Incomplete(Instrumenter):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_concrete_subclass_instantiates():
    class Concrete(Instrumenter):
        def instrument_apks(
            self, apks_dir, results_dir, force_instrumentation=False, apk_paths=None
        ):
            return InstrumentationResults(success_count=1, total_count=1, variant="ajc")

    instance = Concrete()
    out = instance.instrument_apks("/tmp/in", "/tmp/out")
    assert isinstance(out, InstrumentationResults)
    assert out.success_count == 1


def test_signature_preserved_on_subclass():
    class Concrete(Instrumenter):
        def instrument_apks(
            self, apks_dir, results_dir, force_instrumentation=False, apk_paths=None
        ):
            return InstrumentationResults()

    base_sig = inspect.signature(Instrumenter.instrument_apks)
    sub_sig = inspect.signature(Concrete.instrument_apks)
    assert list(base_sig.parameters) == list(sub_sig.parameters)


# Template Method: _resolve_runtime_libs ----------------------------------


def _fake_mvn_writes_jars(jar_names):
    """Build a side_effect that writes the given jars to the outputDirectory."""

    def _run(cmd, capture_output=True, text=True, timeout=None):
        # Find -DoutputDirectory=<path> in the cmd list
        out_dir = None
        for arg in cmd:
            if arg.startswith("-DoutputDirectory="):
                out_dir = Path(arg.split("=", 1)[1])
                break
        assert out_dir is not None, f"no outputDirectory in cmd: {cmd}"
        for name in jar_names:
            (out_dir / name).touch()

        class _Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Proc()

    return _run


def test_resolve_runtime_libs_runs_mvn_and_returns_jars(tmp_path):
    """ABC's `_resolve_runtime_libs` Template Method roda mvn e retorna jars."""
    rvsec_root = tmp_path / "rvsec_root"
    (rvsec_root / "rv-android").mkdir(parents=True)
    (rvsec_root / "rv-android" / "pom.xml").touch()
    lib_tmp = tmp_path / "lib_tmp"

    expected = [
        "rv-monitor-rt-0.9.1-SNAPSHOT.jar",
        "rvsec-core-0.9.1-SNAPSHOT.jar",
        "rvsec-logger-logcat-0.9.1-SNAPSHOT.jar",
        "aspectjrt-1.9.7.jar",
    ]
    instrumenter = _ConcreteInstrumenter()

    with patch("subprocess.run", side_effect=_fake_mvn_writes_jars(expected)):
        out = instrumenter._resolve_runtime_libs(rvsec_root, lib_tmp)

    assert len(out) == 4
    names = {p.name for p in out}
    assert names == set(expected)
    # Sorted alphabetically
    assert [p.name for p in out] == sorted(expected)


def test_resolve_runtime_libs_raises_filenotfound_when_pom_missing(tmp_path):
    rvsec_root = tmp_path / "rvsec_root"
    rvsec_root.mkdir()  # no rv-android/pom.xml inside
    lib_tmp = tmp_path / "lib_tmp"

    instrumenter = _ConcreteInstrumenter()
    with pytest.raises(FileNotFoundError, match="rv-android/pom.xml"):
        instrumenter._resolve_runtime_libs(rvsec_root, lib_tmp)


def test_resolve_runtime_libs_raises_runtime_when_mvn_fails(tmp_path):
    rvsec_root = tmp_path / "rvsec_root"
    (rvsec_root / "rv-android").mkdir(parents=True)
    (rvsec_root / "rv-android" / "pom.xml").touch()
    lib_tmp = tmp_path / "lib_tmp"

    class _FailedProc:
        returncode = 1
        stdout = "[INFO] Building..."
        stderr = "[ERROR] dependency resolution failed"

    instrumenter = _ConcreteInstrumenter()
    with patch("subprocess.run", return_value=_FailedProc()):
        with pytest.raises(RuntimeError, match="mvn copy-dependencies failed"):
            instrumenter._resolve_runtime_libs(rvsec_root, lib_tmp)


def test_resolve_runtime_libs_raises_runtime_when_no_jars_produced(tmp_path):
    """Maven exited 0 but produced no jars — usually a misconfigured pom."""
    rvsec_root = tmp_path / "rvsec_root"
    (rvsec_root / "rv-android").mkdir(parents=True)
    (rvsec_root / "rv-android" / "pom.xml").touch()
    lib_tmp = tmp_path / "lib_tmp"

    class _EmptyProc:
        returncode = 0
        stdout = "[INFO] BUILD SUCCESS"
        stderr = ""

    instrumenter = _ConcreteInstrumenter()
    with patch("subprocess.run", return_value=_EmptyProc()):
        with pytest.raises(RuntimeError, match="contains no jars"):
            instrumenter._resolve_runtime_libs(rvsec_root, lib_tmp)
