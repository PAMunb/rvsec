"""
Configure the unified GATOR-based static analysis pipeline.

Provide path resolution, validation, and command generation for the GATOR analysis
client that produces a single JSON output containing reachability, windows, and
transitions. Path resolution follows a priority chain: explicit parameters >
rvsec_root layout > RVSEC_HOME env var > CWD parent.

### Role in the System:

- Consumed by StaticAnalyzer to build GATOR command lines and validate
  tool availability before execution
- Consumed by rv-platform's StaticAnalysisComponent for pipeline configuration
- CLI (__main__.py) creates instances from parsed command-line arguments

### Key Features:

- Priority-based path resolution with four fallback levels
- Eager validation of GATOR launcher, analysis JAR, Android SDK, and MOP dir
- Command generation for the RvsecAnalysisClient GATOR invocation
- Optional deferred validation via validate_on_init=False for dry-run mode

### Integration Points:

- Input: RVSEC_HOME and ANDROID_HOME environment variables, explicit paths
- Output: Validated paths and GATOR command lines consumed by StaticAnalyzer
- Dependencies: rv-android-core (BaseValidatedModel, ConfigurationError, constants)
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import Field
from rv_android_core.constants import ENV_ANDROID_HOME, ENV_RVSEC_HOME, EXTENSION_APK
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_android_core.util.validation import BaseValidatedModel


class RVStaticAnalysisConfig(BaseValidatedModel):
    """
    Configuration for the unified static analysis pipeline.

    The analysis runs as a single GATOR invocation with the RvsecAnalysisClient,
    producing one JSON file with reachability, windows, and transitions.

    Path resolution priority (highest to lowest):
    1. Explicit parameters
    2. rvsec_root with standard layout
    3. RVSEC_HOME environment variable
    4. Current working directory parent
    """

    rvsec_root: Optional[str] = Field(
        default=None, description="RVSEC installation root directory"
    )
    lib_dir: Optional[str] = Field(
        default=None, description="Directory containing static analysis tool JARs"
    )
    android_platforms_dir: Optional[str] = Field(
        default=None, description="Android SDK platforms directory"
    )
    android_jar: Optional[str] = Field(
        default=None, description="Android SDK JAR path (android.jar)"
    )
    mop_dir: Optional[str] = Field(
        default=None,
        description=(
            "MOP specifications directory (mutex with targets_file). "
            "When set, GATOR receives '-clientParam mopDir=<path>' and target "
            "methods are loaded via MopSpecsTargetSource (LENIENT class+name match)."
        ),
    )
    targets_file: Optional[str] = Field(
        default=None,
        description=(
            "Plain-text file listing Soot signatures of target methods, one per "
            "line (mutex with mop_dir). When set, GATOR receives "
            "'-clientParam targetsFile=<path>' and target methods are loaded via "
            "SignatureFileTargetSource (STRICT per-signature, LENIENT for wildcard "
            "entries '..' or '*'). Exactly one of {mop_dir, targets_file} MUST be "
            "set — INV-ANA-33 enforced at the CLI mutex and at this Pydantic boundary."
        ),
    )
    output_dir: Optional[str] = Field(
        default=None, description="Base output directory for analysis results"
    )
    working_dir: Optional[str] = Field(
        default=None, description="Working directory for temporary files"
    )
    gator_dir: Optional[str] = Field(
        default=None, description="GATOR tools directory (Python launcher + client JAR)"
    )
    analysis_client_jar: Optional[str] = Field(
        default=None, description="Path to rvsec-analysis-client.jar"
    )
    jvm_memory: str = Field(
        default="12g", description="JVM heap size for analysis (e.g. '12g', '20g')"
    )
    analysis_timeout: int = Field(
        default=600, description="Analysis timeout in seconds"
    )
    cg_algorithm: Literal["spark", "cha", "rta", "vta"] = Field(
        default="spark",
        description=(
            "Call graph algorithm forwarded to Soot via '-cgAlgorithm <value>'. "
            "Default 'spark' preserves gh51 D5 (full points-to gives accurate "
            "reachesMop); cha/rta/vta are faster but less precise. Pydantic-pinned "
            "to the four Soot-accepted values so an invalid string fails at config "
            "construction rather than producing a silent GATOR error mid-pipeline."
        ),
    )
    skip_wtg: bool = Field(
        default=False,
        description=(
            "When True, append -clientParam skipWtg=true so RvsecAnalysisClient "
            "writes the partial JSON (reachability + windows[] populated via "
            "wjtp.gui data) and returns without invoking WTGBuilder.build(). "
            "Use for known-slow APKs where WTG is guaranteed to time out."
        ),
    )
    cg_delegation: Optional[bool] = Field(
        default=None,
        description=(
            "When set, append -cgDelegation <bool> to the GATOR command "
            "(top-level flag, parsed by Main.java). Controls whether "
            "FlowgraphRebuilder delegates virtual dispatch to "
            "Scene.v().getCallGraph() (SPARK) instead of the legacy points-to "
            "+ CHA fallback path. None → GATOR uses its baked-in default "
            "(false post-M3 — opt-in to true for apps without hybrid-framework "
            "dispatch where SPARK delegation yields 2–23× speedup; see "
            "docs/20260515_diagnostico_paridade_cgdelegation.md)."
        ),
    )
    validate_on_init: bool = Field(
        default=True, description="Whether to validate configuration on initialization"
    )

    def model_post_init(self, __context) -> None:
        """Resolve paths and validate after Pydantic construction.

        State:
            All path fields are resolved to absolute paths. When validate_on_init
            is True, all tool paths are verified to exist on disk.
        """
        self._resolve_paths()
        if self.validate_on_init:
            self._validate_configuration()

    def _resolve_paths(self) -> None:
        """Resolve all paths using the four-level priority strategy."""
        if not self.rvsec_root:
            self.rvsec_root = os.environ.get(ENV_RVSEC_HOME)
            if not self.rvsec_root:
                self.rvsec_root = os.path.dirname(os.getcwd())

        self._apply_default_paths()
        self._normalize_paths()

    def _apply_default_paths(self) -> None:
        """Apply default paths based on rvsec_root standard directory layout."""
        rvsec_path = Path(self.rvsec_root)

        if not self.lib_dir:
            self.lib_dir = str(rvsec_path / "rv-android" / "lib")

        if not self.android_platforms_dir:
            android_home = os.environ.get(ENV_ANDROID_HOME)
            if android_home:
                self.android_platforms_dir = str(Path(android_home) / "platforms")

        if not self.android_jar and self.android_platforms_dir:
            for api_level in ["33", "29", "28", "27", "26"]:
                candidate = (
                    Path(self.android_platforms_dir)
                    / f"android-{api_level}"
                    / "android.jar"
                )
                if candidate.exists():
                    self.android_jar = str(candidate)
                    break

        # Only default mop_dir when targets_file is not set — the two are mutex
        # (INV-ANA-33). When targets_file IS set, leaving mop_dir as None lets
        # downstream code dispatch on it cleanly.
        if not self.mop_dir and not self.targets_file:
            self.mop_dir = str(
                rvsec_path
                / "rvsec"
                / "rvsec-mop"
                / "src"
                / "main"
                / "resources"
                / "jca"
            )

        if not self.output_dir:
            self.output_dir = str(rvsec_path / "out")

        lib_path = Path(self.lib_dir)

        if not self.gator_dir:
            self.gator_dir = str(lib_path / "gator")

        if not self.analysis_client_jar:
            self.analysis_client_jar = str(
                Path(self.gator_dir) / "rvsec-analysis-client.jar"
            )

    def _normalize_paths(self) -> None:
        """Convert all paths to absolute."""
        path_attributes = [
            "rvsec_root",
            "lib_dir",
            "android_platforms_dir",
            "android_jar",
            "mop_dir",
            "targets_file",
            "output_dir",
            "working_dir",
            "gator_dir",
            "analysis_client_jar",
        ]
        for attr in path_attributes:
            value = getattr(self, attr)
            if value:
                setattr(self, attr, os.path.abspath(value))

    def _validate_configuration(self) -> None:
        """Validate all paths and tools for operational readiness.

        Raises:
            ConfigurationError: When any required path is missing, any tool
                binary is not found, or the Android SDK is misconfigured.
        """
        self._validate_required_paths()
        self._validate_tool_availability()
        self._validate_android_sdk()
        self._validate_mop_directory()

    def _validate_required_paths(self) -> None:
        """Validate required paths are set."""
        required_paths = {"lib_dir": self.lib_dir, "output_dir": self.output_dir}
        for name, path in required_paths.items():
            if not path:
                raise ConfigurationError(f"Required path '{name}' is not configured")

    def _validate_tool_availability(self) -> None:
        """Validate GATOR launcher and analysis client JAR exist."""
        gator_python = str(Path(self.gator_dir) / "gator")
        if not os.path.isfile(gator_python):
            raise ConfigurationError(f"GATOR Python launcher not found: {gator_python}")

        if not os.path.isfile(self.analysis_client_jar):
            raise ConfigurationError(
                f"Analysis client JAR not found: {self.analysis_client_jar}"
            )

    def _validate_android_sdk(self) -> None:
        """Validate Android SDK configuration."""
        if not self.android_platforms_dir:
            raise ConfigurationError("Android platforms directory not configured")

        if not os.path.isdir(self.android_platforms_dir):
            raise ConfigurationError(
                f"Android platforms directory does not exist: {self.android_platforms_dir}"
            )

        if not self.android_jar:
            raise ConfigurationError("Android JAR (android_jar) not configured")

        if not os.path.isfile(self.android_jar):
            raise ConfigurationError(f"Android JAR does not exist: {self.android_jar}")

    def _validate_mop_directory(self) -> None:
        """Validate that exactly one target source is set and exists on disk.

        INV-ANA-33: exactly one of ``mop_dir`` (JavaMOP specs directory) or
        ``targets_file`` (plain-text Soot signature list) MUST be set. The CLI
        argparse mutex covers the user-facing path; this Pydantic-level check
        catches programmatic construction errors (e.g., a downstream config
        that sets both, or neither).
        """
        if self.mop_dir and self.targets_file:
            raise ConfigurationError(
                "Both mop_dir and targets_file are set — they are mutually exclusive "
                f"(INV-ANA-33). mop_dir={self.mop_dir} targets_file={self.targets_file}"
            )
        if not self.mop_dir and not self.targets_file:
            raise ConfigurationError(
                "Neither mop_dir nor targets_file is set — exactly one must be "
                "configured to drive target-method reachability (INV-ANA-33)."
            )

        if self.mop_dir:
            if not os.path.isdir(self.mop_dir):
                raise ConfigurationError(
                    f"MOP specifications directory does not exist: {self.mop_dir}"
                )
        else:
            if not os.path.isfile(self.targets_file):
                raise ConfigurationError(
                    f"Targets file does not exist: {self.targets_file}"
                )

    def validate_apk_input(self, apk_path: str) -> None:
        """Validate that the APK file exists and has .apk extension.

        Args:
            apk_path: Path to the APK file to validate.

        Raises:
            ConfigurationError: When path is empty, file does not exist,
                or file does not have .apk extension.
        """
        if not apk_path:
            raise ConfigurationError("APK path is required")
        if not os.path.isfile(apk_path):
            raise ConfigurationError(f"APK file does not exist: {apk_path}")
        if not apk_path.lower().endswith(EXTENSION_APK):
            raise ConfigurationError(f"File is not an APK: {apk_path}")

    def get_tool_command(
        self, tool_name: str, apk_path: str, output_file: str, **kwargs
    ) -> list:
        """
        Generate command line for static analysis execution.

        Args:
            tool_name: Must be 'analysis'
            apk_path: Path to APK file
            output_file: Path to output JSON file
            **kwargs: Additional arguments

        Returns:
            Command line as list of strings
        """
        if tool_name != "analysis":
            raise ConfigurationError(
                f"Unsupported tool: {tool_name}. Use 'analysis' for unified analysis."
            )

        gator_python = str(Path(self.gator_dir) / "gator")
        timeout = kwargs.get("timeout", self.analysis_timeout)

        # Use the running interpreter (sys.executable) instead of a literal "python".
        # The latter fails on systems where /usr/bin/python is absent (Debian/Ubuntu
        # without python-is-python3, clean containers, fresh shells). sys.executable
        # always resolves to a working Python 3.x with the project's deps.
        # INV-ANA-33: exactly one of mop_dir / targets_file is set. The Pydantic
        # validator already raised if both or neither were configured, so we
        # dispatch unconditionally here.
        if self.targets_file:
            target_param = f"targetsFile={self.targets_file}"
        else:
            target_param = f"mopDir={self.mop_dir}"

        cmd = [
            sys.executable,
            gator_python,
            "a",
            "-p",
            apk_path,
            "--client-jar",
            self.analysis_client_jar,
            "--out",
            output_file,
            "-client",
            "RvsecAnalysisClient",
            "-clientParam",
            target_param,
            "-cgAlgorithm",
            self.cg_algorithm,
            "--timeout",
            str(timeout),
            "--jvm-memory",
            self.jvm_memory.upper(),
        ]

        # Pass detected code package so the GATOR client filters classes
        # to app-only (excludes library classes from coverage denominator)
        code_package = kwargs.get("code_package")
        if code_package:
            cmd.extend(["-clientParam", f"codePackage={code_package}"])

        if self.skip_wtg:
            cmd.extend(["-clientParam", "skipWtg=true"])

        if self.cg_delegation is not None:
            cmd.extend(["-cgDelegation", "true" if self.cg_delegation else "false"])

        return cmd

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Return a nested dictionary summarizing all configuration values.

        Returns:
            Dictionary with sections: rvsec_integration, android_integration,
            and analysis_tool, each containing the relevant path and setting values.
        """
        return {
            "rvsec_integration": {
                "rvsec_root": self.rvsec_root,
                "lib_dir": self.lib_dir,
                "mop_dir": self.mop_dir,
                "targets_file": self.targets_file,
                "output_dir": self.output_dir,
            },
            "android_integration": {
                "android_platforms_dir": self.android_platforms_dir,
                "android_jar": self.android_jar,
            },
            "analysis_tool": {
                "gator_dir": self.gator_dir,
                "analysis_client_jar": self.analysis_client_jar,
                "jvm_memory": self.jvm_memory,
                "analysis_timeout": self.analysis_timeout,
                "cg_algorithm": self.cg_algorithm,
            },
        }

    def create_output_directories(self) -> None:
        """Create the output directory tree on disk (no-op if it exists)."""
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
