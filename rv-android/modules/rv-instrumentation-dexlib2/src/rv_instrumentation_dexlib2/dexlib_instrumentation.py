"""``DexlibInstrumentation`` — Python wrapper for the DEX-native weaver Java CLI."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from rv_android_core.constants import ENV_RVSEC_HOME
from rv_android_core.domain.app import App
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_instrumentation_core import (
    InstrumentationError,
    InstrumentationResults,
    Instrumenter,
)
from rv_instrumentation_dexlib2.config import DexlibInstrumentationConfig
from rv_instrumentation_dexlib2.errors import MissingDescriptorError


class DexlibInstrumentation(Instrumenter):
    """DEX-native instrumentation backend, variant ``dexlib2``.

    Shells out to the Java CLI (``rvsec-instrumentation-dexlib2/cli``) whose
    fat jar is auto-copied to ``../../lib/instr-cli.jar`` by the Maven build
    (design D9). Implements the ``Instrumenter`` ABC from
    ``rv-instrumentation-core``; ``rv-experiment`` dispatches to either variant
    through ``rv_instrumentation.get_instrumenter(variant, config)``.

    Spec-set agnostic — the underlying weaver handles JCA and Generic
    specifications identically; no branching on spec-set here.
    """

    def __init__(self, config: DexlibInstrumentationConfig) -> None:
        self.config = config
        # Per-APK observability — paridade com AjcInstrumentation. Without
        # this, batch failures bury per-APK context in a single traceback.
        self._logger = LoggingManager.get_instance().get_logger(
            "rv_instrumentation_dexlib2.DexlibInstrumentation",
            {CONTEXT_COMPONENT: "DexlibInstrumentation"},
        )

    # --- public API -------------------------------------------------------

    def prepare_instrumentation(self) -> None:
        """Validate config + populate runtime classpath via shared Template Method.

        Pre-conditions checked:

        - At least one descriptor JSON is present in ``monitor_output_dir``
          (rv-monitor-generator has run with ``emit_descriptor=True``).
        - The Java CLI fat jar exists at ``cli_jar_path`` (Maven build
          ``rvsec-android/rvsec-instrumentation-dexlib2/cli`` produced it).

        After the pre-conditions, runtime jars are resolved via the ABC's
        ``_resolve_runtime_libs`` Template Method (paridade com AJC). The
        Java CLI dexes ``--classpath`` jars into the final APK
        (``MonitorBuilder.java:114-129``), so the runtime classes
        (``com.runtimeverification.rvmonitor.java.rt.*``,
        ``br.unb.cic.mop.*``, ``br.unb.cic.mop.eh.ErrorCollector``) end up
        in the instrumented APK's DEX. ``aspectjrt`` is filtered out —
        rv-monitor-emitted ``MultiSpec_*RuntimeMonitor.java`` does not
        import any AspectJ types; the ``.aj`` aspect file is consumed only
        by the AJC variant.

        Raises:
            MissingDescriptorError: INV-INS-50 — no descriptor JSON found.
            FileNotFoundError: instr-cli jar missing OR rv-android/pom.xml
                missing (cannot resolve runtime libs).
            RuntimeError: ``mvn dependency:copy-dependencies`` failed.
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

        # Populate runtime classpath via the ABC's Template Method (shared
        # with AJC's prepare_instrumentation). The Template Method runs
        # ``mvn dependency:copy-dependencies`` against rv-android/pom.xml,
        # which pulls in 13+ jars (rv-monitor-rt, rvsec-core,
        # rvsec-logger-logcat, aspectjrt, aspectjweaver, aspectjtools,
        # kotlin-stdlib, surefire-*, annotations…). The Java CLI dexes
        # every classpath entry into the final APK
        # (``MonitorBuilder.java:114-129``), so we MUST narrow the list
        # to what dexlib2-instrumented APKs actually call at runtime.
        # rv-monitor-emitted ``MultiSpec_*RuntimeMonitor.java`` references
        # only:
        #   - ``com.runtimeverification.rvmonitor.java.rt.*`` (rv-monitor-rt.jar)
        #   - ``br.unb.cic.mop.*`` (rvsec-core.jar)
        #   - ``br.unb.cic.mop.eh.ErrorCollector`` (rvsec-logger-logcat.jar)
        # AspectJ runtime/tools/weaver are consumed only by the AJC
        # variant. kotlin-stdlib + surefire jars come along as transitive
        # noise from the test scope and would either inflate the APK by
        # 18 MB or trigger d8 ``Type defined multiple times`` errors.
        # Allowlist keeps the classpath tight and the APK lean.
        rvsec_root = _resolve_rvsec_root_or_raise()
        lib_tmp = self.config.working_dir / "lib_tmp"
        all_jars = self._resolve_runtime_libs(rvsec_root, lib_tmp)
        # ``rv-android/pom.xml`` configures stripVersion=true, so jars land
        # as ``rv-monitor-rt.jar`` (no version). Match that exact name OR a
        # version-suffixed variant defensively in case stripVersion changes.
        allowed_artifacts = (
            "rv-monitor-rt",
            "rvsec-core",
            "rvsec-logger-logcat",
        )

        def _matches_allowed(jar_name: str) -> bool:
            for art in allowed_artifacts:
                if jar_name == f"{art}.jar" or jar_name.startswith(f"{art}-"):
                    return True
            return False

        runtime_jars = [jar for jar in all_jars if _matches_allowed(jar.name)]
        if not runtime_jars:
            raise RuntimeError(
                f"Template Method returned {len(all_jars)} jars but none "
                f"matched the dexlib2 allowlist {allowed_artifacts!r}; "
                f"available: {[j.name for j in all_jars]}"
            )
        # Append (não overwrite) — caller may have set extra_classpath manually.
        self.config.extra_classpath = list(self.config.extra_classpath) + runtime_jars

    def instrument(self, app: App, result_dir: Path) -> Path:
        """Instrument a single APK.

        Returns the path to the signed output APK. Subprocess failures
        surface as ``CommandException`` (from rv-android-core) populated with
        the Java CLI's stderr + exit code.
        """
        self._run_cli(
            [
                "instrument",
                str(app.apk_path),
                *self._common_cli_args(result_dir),
            ]
        )
        return result_dir / f"{app.name}.apk"

    def instrument_apks(
        self,
        apks_dir,
        results_dir,
        force_instrumentation: bool = False,
        apk_paths: Optional[List[str]] = None,
    ) -> InstrumentationResults:
        """Instrument every ``.apk`` under ``apks_dir`` in one subprocess call.

        Signature comes from the ``Instrumenter`` ABC so rv-experiment's
        PreProcessor can dispatch to either variant via the same kwargs.

        Args:
            apks_dir: Directory containing the APKs to instrument.
            results_dir: Where the signed instrumented APKs land.
            force_instrumentation: Reserved — the Java CLI always re-runs;
                idempotency is the caller's responsibility (rv-experiment
                deletes the results dir on resume rather than relying on
                this flag).
            apk_paths: Optional subset of basenames to process. When set,
                each named APK is run through the single-APK ``instrument``
                subcommand (one JVM per APK). When ``None``, the ``batch``
                subcommand processes the entire ``apks_dir`` in one JVM.

        Emits the batch summary to ``results_dir/instrument_results.json``
        per the Java CLI's ``--results-json`` flag, then parses it into an
        ``InstrumentationResults`` tagged with ``variant="dexlib2"``.
        """
        from pathlib import Path

        self.prepare_instrumentation()
        apks_dir = Path(apks_dir)
        results_dir = Path(results_dir)
        results_json = results_dir / "instrument_results.json"
        results_dir.mkdir(parents=True, exist_ok=True)

        if apk_paths:
            # Per-APK invocation. The Java CLI's batch path filters by
            # globbing the directory, so to honor a strict subset we
            # invoke single-APK runs and aggregate the results manually.
            # Slower (1 JVM per APK) but the only way to respect apk_paths
            # without staging a symlink farm.
            from rv_instrumentation_core import (
                InstrumentationError,
                InstrumentationResults,
            )

            total = len(apk_paths)
            self._logger.info(
                f"Starting batch instrumentation: {total} APKs (apk_paths mode)",
                extra={
                    "pipeline_stage": "batch_start",
                    "total_apks": total,
                    "results_dir": str(results_dir),
                },
            )
            success = 0
            errors: dict[str, InstrumentationError] = {}
            for idx, name in enumerate(apk_paths, start=1):
                apk = apks_dir / name
                self._logger.info(
                    f"Processing APK {idx}/{total}: {name}",
                    extra={
                        "pipeline_stage": "apk_start",
                        "app_name": name,
                        "apk_index": idx,
                        "total_apks": total,
                    },
                )
                if not apk.is_file():
                    errors[name] = InstrumentationError(
                        code=2,
                        phase="apk_lookup",
                        tool="instr-cli",
                        message=f"APK not found at {apk}",
                    )
                    self._logger.error(
                        f"APK not found at {apk}",
                        extra={
                            "pipeline_stage": "apk_lookup",
                            "app_name": name,
                        },
                    )
                    continue
                apk_start = time.time()
                try:
                    self._run_cli(
                        [
                            "instrument",
                            str(apk),
                            *self._common_cli_args(results_dir),
                        ]
                    )
                    # Cross-check: the single-APK ``instrument`` subcommand
                    # of instr-cli prints compilation errors to stdout but
                    # exits 0 — so a clean exit alone is NOT proof of
                    # success. Verify the APK actually landed in
                    # results_dir before crediting the run.
                    output_apk = results_dir / name
                    if not output_apk.is_file():
                        raise RuntimeError(
                            f"instr-cli reported success but {output_apk} "
                            f"was not created — silent javac/d8 failure; "
                            f"inspect cli stdout for compilation errors"
                        )
                    success += 1
                    apk_elapsed = time.time() - apk_start
                    self._logger.info(
                        f"Instrumented {name} in {apk_elapsed:.1f}s",
                        extra={
                            "pipeline_stage": "apk_done",
                            "app_name": name,
                            "elapsed_seconds": round(apk_elapsed, 1),
                        },
                    )
                except (RuntimeError, subprocess.SubprocessError) as ex:
                    # Defense in depth: catch SubprocessError as well as
                    # RuntimeError. Even though we removed the wallclock
                    # timeout (so ``TimeoutExpired`` should no longer fire),
                    # any future re-introduction of timeout=, or a
                    # ``CalledProcessError`` from check=True, must still
                    # demote per-APK rather than abort the entire batch.
                    apk_elapsed = time.time() - apk_start
                    errors[name] = InstrumentationError(
                        code=1,
                        phase="dexlib2_pipeline",
                        tool="instr-cli",
                        message=str(ex),
                    )
                    self._logger.error(
                        f"Failed to instrument {name} after {apk_elapsed:.1f}s: {ex}",
                        extra={
                            "pipeline_stage": "apk_failed",
                            "app_name": name,
                            "elapsed_seconds": round(apk_elapsed, 1),
                            "error_type": type(ex).__name__,
                        },
                    )
            results = InstrumentationResults(
                success_count=success,
                total_count=total,
                errors=errors,
                variant="dexlib2",
            )
            self._logger.info(
                f"Batch complete: {success}/{total} successful, "
                f"{len(errors)} errors",
                extra={
                    "pipeline_stage": "batch_done",
                    "success_count": success,
                    "total_count": total,
                    "error_count": len(errors),
                },
            )
            self._persist_errors_json(results, results_dir)
            return results

        self._logger.info(
            f"Starting batch instrumentation (batch mode) — apks_dir={apks_dir}",
            extra={
                "pipeline_stage": "batch_start",
                "apks_dir": str(apks_dir),
                "results_dir": str(results_dir),
            },
        )
        self._run_cli(
            [
                "batch",
                str(apks_dir),
                *self._common_cli_args(results_dir),
                "--results-json",
                str(results_json),
            ]
        )
        results = self._parse_results_json(results_json)
        # Cross-check: the CLI's batch subcommand can mark an APK as
        # ``success: true`` in the JSON even when the post-javac/d8 steps
        # silently dropped the APK (same root cause as the single-APK
        # path's exit-0-without-output bug). Demote to error any apkName
        # that the JSON claims succeeded but is missing from results_dir.
        results = _demote_silent_failures(results, results_dir)
        self._logger.info(
            f"Batch complete: {results.success_count}/{results.total_count} "
            f"successful, {len(results.errors)} errors",
            extra={
                "pipeline_stage": "batch_done",
                "success_count": results.success_count,
                "total_count": results.total_count,
                "error_count": len(results.errors),
            },
        )
        self._persist_errors_json(results, results_dir)
        return results

    def _persist_errors_json(
        self, results: InstrumentationResults, results_dir: Path
    ) -> None:
        """Write per-APK errors to ``results_dir/instrument_errors.json``.

        Paridade com AjcInstrumentation (``ajc_instrumentation.py:340-360``).
        Allows post-mortem of a batch run without re-tailing logs. Mirrors
        the AJC schema: ``{<apk_name>: {"code": ..., "tool": ..., "message":
        ..., "phase": ...}, ...}``. Empty errors writes ``{}`` so consumers
        can rely on the file existing.
        """
        errors_path = Path(results_dir) / "instrument_errors.json"
        payload = {name: error.model_dump() for name, error in results.errors.items()}
        try:
            errors_path.write_text(json.dumps(payload, indent=2))
            self._logger.info(
                f"Error report saved to: {errors_path}",
                extra={"errors_file": str(errors_path)},
            )
        except OSError as ex:
            self._logger.error(
                f"Failed to write {errors_path}: {ex}",
                extra={"errors_file": str(errors_path)},
            )

    def _common_cli_args(self, output_dir: Path) -> List[str]:
        """CLI args shared between ``instrument`` and ``batch`` subcommands.

        ``--monitor-src-dir`` points at the rv-monitor-generator output (the
        same directory holding the descriptor JSON + ``mop/*RuntimeMonitor.java``
        + ``mop/MonitorWrappers.java``). MonitorBuilder walks it recursively
        for .java sources. With it set, the Java CLI runs the full
        compile+merge+sign pipeline; without it the CLI stops at written
        DEXes (phase=dex_only).
        """
        args = [
            "--descriptor",
            str(self._first_descriptor()),
            "--output",
            str(output_dir),
            "--work-dir",
            str(self.config.working_dir),
            "--monitor-src-dir",
            str(self.config.monitor_output_dir),
        ]
        if self.config.keystore_file is not None:
            args += ["--keystore", str(self.config.keystore_file)]
        if self.config.keystore_password is not None:
            args += ["--keystore-pass", self.config.keystore_password]
        if self.config.keystore_alias is not None:
            args += ["--key-alias", self.config.keystore_alias]
        # Java CLI defaults --key-pass to the keystore password when omitted,
        # but the legacy bundled keystore uses the same secret for both, so we
        # forward keystore_password as key_password when the latter is unset.
        kpass = self.config.key_password or self.config.keystore_password
        if kpass is not None:
            args += ["--key-pass", kpass]
        if self.config.extra_classpath:
            args += [
                "--classpath",
                ",".join(str(p) for p in self.config.extra_classpath),
            ]
        return args

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
        # Truncate cmd preview for log (full classpath bloats log lines).
        subcmd = cli_args[0] if cli_args else "?"
        self._logger.info(
            f"Invoking instr-cli ({subcmd}) — argv length {len(cmd)}",
            extra={"pipeline_stage": "instr_cli_invoke", "subcommand": subcmd},
        )
        start = time.time()
        # No wallclock timeout — instrumentation is a build operation. Weave
        # time scales with method count (cf. coverageInstrumented=80160 for
        # 249k-method APKs) and is bounded only by APK content. Parity with
        # AJC's mvn/dex2jar/ajc/d8/jarsigner invocations (no timeout). Real
        # APKs from the JCA-400 corpus legitimately need 10-30+ min.
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=_build_subprocess_env(env_extras),
        )
        elapsed = time.time() - start
        self._logger.info(
            f"instr-cli ({subcmd}) returned exit={proc.returncode} in {elapsed:.1f}s",
            extra={
                "pipeline_stage": "instr_cli_done",
                "subcommand": subcmd,
                "exit_code": proc.returncode,
                "elapsed_seconds": round(elapsed, 1),
            },
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
                errors={
                    "__run__": InstrumentationError(
                        code=2,
                        phase="dexlib2_pipeline",
                        tool="instr-cli",
                        message=f"results JSON not written at {path}",
                    )
                },
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


def _build_subprocess_env(extras: Optional[dict] = None) -> dict:
    """Build an explicit subprocess env for the Java CLI (gh55 D9).

    Forwards only the OS-level variables the Java toolchain genuinely needs:
    PATH (executable lookup), HOME, JAVA_HOME (toolchain location),
    ANDROID_HOME (SDK paths), RVSEC_HOME (rvsec workspace root). Wholesale
    propagation of os.environ is forbidden by INV-EXP-30 — it would leak
    user-facing RV_* values past Layer Purity boundaries into the Java process.

    Args:
        extras: optional caller-supplied additional env entries (e.g.,
            CLASSPATH overrides) layered on top of the forwarded set.

    Returns:
        Dict suitable for ``subprocess.run(..., env=...)``.
    """
    import os

    forwarded_keys = ("PATH", "HOME", "JAVA_HOME", "ANDROID_HOME", ENV_RVSEC_HOME)
    forwarded = {k: os.environ[k] for k in forwarded_keys if k in os.environ}
    if extras:
        forwarded.update(extras)
    return forwarded


def _demote_silent_failures(
    results: InstrumentationResults, results_dir: Path
) -> InstrumentationResults:
    """Replace JSON-claimed successes whose APK is missing on disk with errors.

    The Java CLI's batch subcommand may report ``success: true`` for an APK
    even when the downstream javac/d8/sign pipeline silently dropped its
    output. Without this guard the wrapper would credit phantom successes,
    which is exactly how the gh53 dexlib2 smoke produced 0% coverage on
    cryptoapp despite the wrapper reporting success.

    The function rebuilds ``InstrumentationResults`` with each missing-APK
    entry moved from the success counter to the errors map. Total count and
    variant tag are preserved.
    """
    # Reconstruct the per-APK pass/fail picture from the existing results:
    # we know how many succeeded but not which ones, so we cannot
    # distinguish "claimed success" from "claimed failure" without parsing
    # the original JSON again. The caller (instrument_apks batch path)
    # passes the results returned by ``_parse_results_json`` which already
    # discarded the success/failure flags; re-derive by listing the APKs
    # the JSON claimed (all minus those already in errors) and verify each.
    if results.total_count == 0:
        return results
    # APKs in the errors map are already accounted for as failures.
    explicit_failures = set(results.errors.keys())
    # The CLI's instrument_results.json rooted in results_dir is the source
    # of truth for "claimed success" set.
    json_path = results_dir / "instrument_results.json"
    if not json_path.is_file():
        return results
    body = json.loads(json_path.read_text())
    new_errors = dict(results.errors)
    new_success = results.success_count
    for entry in body.get("results", []):
        apk_name = entry.get("apkName", "")
        if not entry.get("success") or apk_name in explicit_failures:
            continue
        if not (results_dir / apk_name).is_file():
            new_errors[apk_name] = InstrumentationError(
                code=1,
                phase="dexlib2_pipeline",
                tool="instr-cli",
                message=(
                    f"CLI reported success but APK not created at "
                    f"{results_dir / apk_name} — silent javac/d8 failure"
                ),
            )
            new_success -= 1
    return InstrumentationResults(
        success_count=max(0, new_success),
        total_count=results.total_count,
        errors=new_errors,
        variant=results.variant,
    )


def _resolve_rvsec_root_or_raise() -> Path:
    """Resolve the rvsec workspace root from the ``RVSEC_HOME`` env variable.

    The rv-android workspace requires ``RVSEC_HOME`` to be set for monitor
    generation, static analysis and (now) dexlib2 runtime-library resolution.
    See CLAUDE.md "Environment Variables".
    """
    rvsec_home = os.environ.get(ENV_RVSEC_HOME)
    if not rvsec_home:
        raise RuntimeError(
            "RVSEC_HOME environment variable is not set; cannot resolve "
            "runtime libraries (rv-monitor-rt, rvsec-core, ...). Set RVSEC_HOME "
            "to the rvsec workspace root (the directory containing rv-android/)."
        )
    return Path(rvsec_home)
