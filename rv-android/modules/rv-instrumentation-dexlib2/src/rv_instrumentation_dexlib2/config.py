"""Configuration for the DEX-native weaver Python wrapper.

Mirrors the shape of ``RVInstrumentationConfig`` so downstream callers
(``rv-experiment``) can swap variants without field renaming.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


def _default_cli_jar() -> Path:
    """Resolve the fat jar auto-copied by the Maven build (design D9).

    The Maven ``cli`` module copies ``instr-cli.jar`` to this directory via
    ``maven-resources-plugin:copy-resources``. The path is relative to the
    Python wrapper module's install location so no environment variable or
    absolute path configuration is needed.
    """
    return Path(__file__).resolve().parent.parent.parent / "lib" / "instr-cli.jar"


class DexlibInstrumentationConfig(BaseModel):
    """Configuration for ``DexlibInstrumentation``.

    Minimal surface: the Java CLI resolves most tool paths from
    ``ANDROID_HOME`` / ``JAVA_HOME`` on its own (``ConfigResolver`` in the
    Java side). This Python config carries only what the wrapper itself
    needs — the CLI jar location, the descriptor directory, and the
    instrumented-APK output directory.
    """

    cli_jar_path: Path = Field(
        default_factory=_default_cli_jar,
        description=(
            "Path to the instr-cli fat jar. Defaults to ../../lib/instr-cli.jar "
            "which is where the Maven build copies it (design D9). Override to "
            "point at a development build or a Docker-mounted jar."
        ),
    )
    monitor_output_dir: Path = Field(
        description=(
            "Directory containing MultiSpec_*MonitorAspect.json + "
            "MultiSpec_*RuntimeMonitor.java + Coverage.aj + MonitorWrappers.java."
        ),
    )
    descriptor_glob: str = Field(
        default="MultiSpec_*MonitorAspect.json",
        description="Glob identifying descriptor JSON files in monitor_output_dir.",
    )
    instrumented_dir: Path = Field(
        description="Where signed instrumented APKs land.",
    )
    working_dir: Path = Field(
        description="Scratch directory for intermediate artifacts.",
    )
    keystore_file: Optional[Path] = Field(
        default=None,
        description=(
            "Signing keystore. When None, the Java CLI falls back to "
            "RVSEC_KEYSTORE env var or the canonical rv-android keystore."
        ),
    )
    keystore_password: Optional[str] = Field(
        default=None,
        description="Keystore password (fallback env: RVSEC_KEYSTORE_PASS).",
    )
    extra_java_args: List[str] = Field(
        default_factory=list,
        description="Additional -D / -X / -J args passed to the Java CLI runtime.",
    )
    timeout_seconds: int = Field(
        default=600,
        gt=0,
        description="Per-APK subprocess timeout. 10 min is enough for the largest observed APKs.",
    )

    model_config = {"arbitrary_types_allowed": True}
