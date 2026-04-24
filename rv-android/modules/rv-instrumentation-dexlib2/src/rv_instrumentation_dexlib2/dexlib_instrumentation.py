"""``DexlibInstrumentation`` — Python wrapper for the DEX-native weaver Java CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Optional

from rv_android_core.domain.app import App
from rv_instrumentation.config import (
    InstrumentationError,
    InstrumentationResults,
)

from rv_instrumentation_dexlib2.config import DexlibInstrumentationConfig
from rv_instrumentation_dexlib2.errors import MissingDescriptorError


class DexlibInstrumentation:
    """DEX-native instrumentation backend, variant ``dexlib2``.

    Shells out to the Java CLI (``rvsec-instrumentation-dexlib2/cli``) whose
    fat jar is auto-copied to ``../../lib/instr-cli.jar`` by the Maven build
    (design D9). Exposes the same ``instrument_apks(apks_dir, results_dir) →
    InstrumentationResults`` contract as the legacy ``rv-instrumentation``
    so ``rv-experiment`` can dispatch to either variant via a single config flag.

    Spec-set agnostic — the underlying weaver handles JCA and Generic
    specifications identically; no branching on spec-set here.
    """

    def __init__(self, config: DexlibInstrumentationConfig) -> None:
        self.config = config

    # --- public API -------------------------------------------------------

    def prepare_instrumentation(self) -> None:
        """Validate config and confirm at least one descriptor is present.

        Raises:
            MissingDescriptorError: INV-INS-13 — no descriptor JSON found in
                ``monitor_output_dir``. The error names the directory and
                instructs the caller to rerun rv-monitor-generator with
                ``emit_descriptor=True`` (default since gh52).
            FileNotFoundError: the CLI jar is missing — fat jar build did not
                run, or the Maven copy-resources step was skipped.
        """
        descriptors = sorted(
            self.config.monitor_output_dir.glob(self.config.descriptor_glob)
        )
        if not descriptors:
            raise MissingDescriptorError(
                f"no {self.config.descriptor_glob} under "
                f"{self.config.monitor_output_dir}; rerun rv-monitor-generator "
                f"with emit_descriptor=True (see gh52 task 11.x)"
            )
        if not self.config.cli_jar_path.is_file():
            raise FileNotFoundError(
                f"instr-cli jar not found at {self.config.cli_jar_path}; "
                f"run 'mvn -pl rvsec-android/rvsec-instrumentation-dexlib2/cli -am package' "
                f"from the rvsec/ root to produce it"
            )

    def instrument(self, app: App, result_dir: Path) -> Path:
        """Instrument a single APK.

        Returns the path to the signed output APK. Subprocess failures
        surface as ``CommandException`` (from rv-android-core) populated with
        the Java CLI's stderr + exit code.
        """
        self._run_cli([
            "instrument",
            str(app.apk_path),
            "--descriptor",
            str(self._first_descriptor()),
            "--output",
            str(result_dir),
            "--work-dir",
            str(self.config.working_dir),
        ])
        return result_dir / f"{app.name}.apk"

    def instrument_apks(
        self, apks_dir: Path, results_dir: Path
    ) -> InstrumentationResults:
        """Instrument every ``.apk`` under ``apks_dir`` in one subprocess call.

        Emits the batch summary to ``results_dir/instrument_results.json`` per
        the Java CLI's ``--results-json`` flag, then parses it into an
        ``InstrumentationResults`` tagged with ``variant="dexlib2"``.
        """
        self.prepare_instrumentation()
        results_json = results_dir / "instrument_results.json"
        results_dir.mkdir(parents=True, exist_ok=True)

        self._run_cli([
            "batch",
            str(apks_dir),
            "--descriptor",
            str(self._first_descriptor()),
            "--output",
            str(results_dir),
            "--work-dir",
            str(self.config.working_dir),
            "--results-json",
            str(results_json),
        ])
        return self._parse_results_json(results_json)

    # --- internals --------------------------------------------------------

    def _first_descriptor(self) -> Path:
        """Pick the first descriptor that matches the glob.

        The corpus emits one merged descriptor per spec-set run, so "first" is
        canonical. When callers need multi-descriptor support that extension
        can land alongside the cli's batch integration (task 9.5).
        """
        matches = sorted(
            self.config.monitor_output_dir.glob(self.config.descriptor_glob)
        )
        if not matches:
            raise MissingDescriptorError(
                f"descriptor vanished between prepare and instrument — "
                f"no match for {self.config.descriptor_glob} in "
                f"{self.config.monitor_output_dir}"
            )
        return matches[0]

    def _run_cli(self, cli_args: List[str]) -> subprocess.CompletedProcess[str]:
        cmd = [
            "java",
            *self.config.extra_java_args,
            "-jar",
            str(self.config.cli_jar_path),
            *cli_args,
        ]
        env_extras = self._env_extras()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.timeout_seconds,
            env={**_os_env(), **env_extras},
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"instr-cli exited with code {proc.returncode}\n"
                f"stderr:\n{proc.stderr}"
            )
        return proc

    def _env_extras(self) -> dict:
        extras: dict = {}
        if self.config.keystore_file is not None:
            extras["RVSEC_KEYSTORE"] = str(self.config.keystore_file)
        if self.config.keystore_password is not None:
            extras["RVSEC_KEYSTORE_PASS"] = self.config.keystore_password
        return extras

    def _parse_results_json(self, path: Path) -> InstrumentationResults:
        if not path.is_file():
            # The Java CLI runs batch even when every APK fails; an absent
            # JSON means the subprocess died before writing it.
            return InstrumentationResults(
                success_count=0,
                total_count=0,
                errors={"__run__": InstrumentationError(
                    code=2,
                    phase="dexlib2_pipeline",
                    tool="instr-cli",
                    message=f"results JSON not written at {path}",
                )},
                variant="dexlib2",
            )
        body = json.loads(path.read_text())
        entries = body.get("results", [])
        success = sum(1 for e in entries if e.get("success"))
        errors: dict[str, InstrumentationError] = {}
        for e in entries:
            if not e.get("success"):
                errors[e.get("apkName", "<unknown>")] = InstrumentationError(
                    code=1,
                    phase=e.get("phase", "dexlib2_pipeline"),
                    tool="instr-cli",
                    message=e.get("message", "unknown failure"),
                )
        return InstrumentationResults(
            success_count=success,
            total_count=len(entries),
            errors=errors,
            variant="dexlib2",
        )


def _os_env() -> dict:
    """Return a shallow copy of os.environ — lazy import avoids polluting module scope."""
    import os
    return dict(os.environ)
