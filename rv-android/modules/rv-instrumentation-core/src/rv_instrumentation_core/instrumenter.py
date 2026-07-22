import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from rv_instrumentation_core.results import InstrumentationResults


class Instrumenter(ABC):
    """Contract every instrumentation variant MUST satisfy.

    Concrete variants (e.g. ``AjcInstrumentation`` in ``rv-instrumentation-ajc``,
    ``DexlibInstrumentation`` in ``rv-instrumentation-dexlib2``) implement
    ``instrument_apks`` according to their pipeline. Variant-specific helpers
    (``check_if_instrumented``, ``instrument`` for single APKs, etc.) are NOT
    part of the ABC — consumers needing them import the concrete class directly.

    The ABC also provides ``_resolve_runtime_libs`` as a Template Method:
    both AJC and dexlib2 need ``mvn dependency:copy-dependencies`` to populate
    their runtime classpath (rv-monitor-rt, rvsec-core, rvsec-logger-logcat,
    aspectjrt). Centralising the Maven invocation here keeps the variants
    free of duplicated logic. Each variant owns its own ``lib_tmp/`` (variants
    are alternatives, never run side by side) and decides which jars to keep
    (e.g. dexlib2 filters out aspectjrt because its monitors do not import
    AspectJ types).
    """

    @abstractmethod
    def instrument_apks(
        self,
        apks_dir,
        results_dir,
        force_instrumentation: bool = False,
        apk_paths: Optional[List[str]] = None,
    ) -> InstrumentationResults:
        """Instrument a batch of APKs, returning aggregate results."""
        ...

    def _resolve_runtime_libs(
        self,
        rvsec_root: Path,
        lib_tmp_dir: Path,
        timeout_seconds: int = 600,
    ) -> List[Path]:
        """Resolve runtime verification libraries via Maven copy-dependencies.

        Runs ``mvn dependency:copy-dependencies`` on ``rv-android/pom.xml``
        (which declares rv-monitor-rt, rvsec-core, rvsec-logger-logcat and
        aspectjrt as runtime deps), populating ``lib_tmp_dir`` with the
        corresponding jars and returning their absolute paths.

        Both variants consume the result:

        - AJC merges the .class files extracted from these jars into the
          final APK via ``__merge_support_classes`` so runtime monitor
          dependencies resolve at execution time.
        - dexlib2 forwards the jar paths to the Java CLI's ``--classpath``;
          the CLI then runs javac AND d8 against them
          (``MonitorBuilder.java:114-129``), so the runtime classes end up in
          the APK's DEX. dexlib2 typically filters out ``aspectjrt-*.jar``
          because the rv-monitor-emitted ``MultiSpec_*RuntimeMonitor.java``
          imports neither AspectJ runtime nor weaver types.

        Args:
            rvsec_root: Path to the rvsec workspace root (must contain
                ``rv-android/pom.xml``).
            lib_tmp_dir: Directory where Maven copies the jars. Created if
                missing. Each variant uses its own directory so a session
                running one variant does not depend on the other having
                run first.
            timeout_seconds: How long to wait for Maven before giving up
                (default 10 minutes — first run downloads deps from the
                Maven repository which can be slow).

        Returns:
            Absolute paths to the jars now sitting in ``lib_tmp_dir``,
            sorted alphabetically.

        Raises:
            FileNotFoundError: ``rv-android/pom.xml`` does not exist below
                ``rvsec_root``.
            RuntimeError: Maven exited non-zero, or exited zero but produced
                no jars (dependency configuration is wrong).
        """
        rv_android_pom = rvsec_root / "rv-android" / "pom.xml"
        if not rv_android_pom.is_file():
            raise FileNotFoundError(
                f"rv-android/pom.xml not found at {rv_android_pom}; cannot "
                f"resolve runtime libs (rv-monitor-rt, rvsec-core, ...). "
                f"Set RVSEC_HOME to the rvsec workspace root, or invoke "
                f"with the correct rvsec_root."
            )
        lib_tmp_dir.mkdir(parents=True, exist_ok=True)
        # ``-Dmdep.stripVersion=true`` mirrors the ``<stripVersion>true</stripVersion>``
        # configuration in ``rv-android/pom.xml`` (process-resources execution
        # of the dependency plugin). Both AJC's __merge_support_classes and
        # dexlib2's allowlist look up jars by base artifactId
        # (e.g. ``rv-monitor-rt.jar``); without the flag, the copied jars
        # carry the version suffix and the lookups fail.
        cmd = [
            "mvn",
            "-f",
            str(rv_android_pom),
            "-q",
            "dependency:copy-dependencies",
            f"-DoutputDirectory={lib_tmp_dir.resolve()}",
            "-DincludeScope=runtime",
            "-Dmdep.stripVersion=true",
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"mvn copy-dependencies failed (exit {proc.returncode}):\n"
                f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
            )
        jars = sorted(lib_tmp_dir.glob("*.jar"))
        if not jars:
            raise RuntimeError(
                f"mvn ran but {lib_tmp_dir} contains no jars — "
                f"copy-dependencies output may have gone elsewhere or the "
                f"runtime scope is empty; inspect mvn output:\n{proc.stdout}"
            )
        return jars
