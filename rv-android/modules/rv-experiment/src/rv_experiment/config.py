"""
Experiment configuration management.

Provide type-safe configuration for Android testing experiments using Pydantic
validation. Sub-module configurations (monitor generation, instrumentation,
static analysis) are created just-in-time when accessed, keeping initialization
lightweight and avoiding unnecessary validation of unused modules.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import rv_experiment.constants as constants
from pydantic import Field
from rv_android_core.constants import ENV_RVSEC_HOME, EXTENSION_MOP
from rv_android_core.domain.task import ToolConfig
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation import BaseValidatedModel
from rv_experiment.constants import (
    DEFAULT_APKS_DIR,
    DEFAULT_SPEC_SET,
    INSTRUMENTED_APKS_DIR,
    INSTRUMENTED_DIR,
    MONITORS_DIR,
    RESULTS_DIR,
)
from rv_instrumentation.config import ConfigurationError as InstrumentationConfigError
from rv_instrumentation.config import RVInstrumentationConfig
from rv_monitor_generator.config import ConfigurationError as MonitorConfigError
from rv_monitor_generator.config import RVGeneratorConfig
from rv_static_analysis.config import RVStaticAnalysisConfig

# Just-in-time imports - only import when needed
if TYPE_CHECKING:
    pass


class ExperimentConfig(BaseValidatedModel):
    """Central configuration for Android testing experiments.

    ### Role in the System:
    Primary configuration class used by ExperimentController, CLI, and
    configuration factory. Bridges CLI arguments to experiment orchestration
    by holding all experiment parameters and providing just-in-time
    sub-module configuration creation.

    ### Architectural Decisions:
    - Sub-module configurations (RVGeneratorConfig, RVInstrumentationConfig,
      RVStaticAnalysisConfig) are created on-demand via get_*_config() methods,
      not at initialization. This avoids validation failures when modules
      are not needed (e.g., skip-monitors flag).
    - RVSEC_HOME resolution follows a priority hierarchy: config override
      first, then environment variable, then error.
    - Pydantic validation via BaseValidatedModel provides type safety
      at system boundaries.

    ### Key Features:
    - Tool configuration with variant and parameter support
    - Three specification sets: JCA, generic, custom
    - Resume mode with automatic pre-processing skip
    - APK filtering via external file
    - Serialization to/from JSON for persistence and templates

    ### Integration Points:
    - ExperimentController: Consumes config for workflow orchestration
    - RVGeneratorConfig: Created by get_monitored_operations_config()
    - RVInstrumentationConfig: Created by get_instrumentation_config()
    - RVStaticAnalysisConfig: Created by get_static_analysis_config()
    - CLI (__main__.py): Creates config from command-line arguments
    """

    # =========================================================================
    # Field groups:
    # 1. Metadata — experiment identity and paths
    # 2. Tool configuration — which tools/variants to run
    # 3. Execution parameters — repetitions, timeouts, device config
    # 4. Processing phase flags — control which Phase 1 steps run
    # 5. Specification set — which .mop files to use for monitors
    # 6. APK sources — where to find APKs and optional filtering
    # 7. Results and resume — output directory and continuation support
    # =========================================================================

    # --- 1. Metadata ---
    name: str = ""
    description: str = ""
    output_dir: str = ""

    # Override for RVSEC_HOME. Takes priority over the environment variable.
    # Used in Docker containers where RVSEC_HOME may differ from the host.
    rvsec_root: Optional[str] = Field(
        default=None, description="Override for RVSEC_HOME environment variable"
    )

    # --- 2. Tool configuration ---
    # Each ToolConfig specifies a tool name, variant, and parameters.
    # Multi-variant CLI specs (e.g., "droidbot:dfs_greedy:bfs_greedy") are
    # expanded into separate ToolConfig entries by the CLI parser.
    tool_configs: List[ToolConfig] = Field(
        default_factory=list, description="List of tool configurations"
    )

    # --- 3. Execution parameters ---
    repetitions: int = Field(default=1, gt=0, description="Number of repetitions")
    # Multiple timeouts create a cross-product with tools and APKs:
    # total tasks = len(apks) * len(tools) * len(timeouts) * repetitions
    timeouts: List[int] = Field(
        default_factory=lambda: [60], description="List of timeout values in seconds"
    )
    no_window: bool = Field(default=True, description="Run without GUI window")
    # device_port enables parallel execution in Docker containers.
    # Each container gets a unique port (5554, 5556, ...) so multiple
    # emulators can run simultaneously on the same host.
    device_port: Optional[int] = Field(
        default=None, description="Emulator port for parallel execution"
    )

    # --- 4. Processing phase flags (Phase 1 steps) ---
    # Each flag controls one step of the pre-processing pipeline.
    # On resume, all three are forced to False by the CLI layer because
    # artifacts (monitors, instrumented APKs, static analysis JSON)
    # already exist from the first run. Re-running would overwrite them.
    generate_monitors: bool = Field(default=True, description="Generate monitors")
    instrument_apks: bool = Field(default=True, description="Instrument APKs")
    # gh52 variant switch: which instrumentation backend to use.
    #   "ajc"     — legacy dex2jar+ajc+d8 pipeline (rv-instrumentation).
    #   "dexlib2" — DEX-native pipeline (rv-instrumentation-dexlib2 wrapping
    #               the Java CLI under rvsec/rvsec-android/rvsec-instrumentation-dexlib2/).
    # Default stays "ajc" during Phase 4-5 coexistence. After Phase 5 gate
    # ratifies parity, Phase 6 flips the default to "dexlib2" and quarantines
    # the legacy module. Both variants honor the same instrument_apks contract.
    instrumentation_variant: str = Field(
        default="ajc",
        description="Instrumentation backend: 'ajc' (legacy) or 'dexlib2' (gh52 DEX-native).",
    )
    run_static_analysis: bool = Field(default=True, description="Run static analysis")
    # Controls whether Phase 2 (execution) runs. Useful for pre-processing-only
    # workflows where you want to generate artifacts without running tools.
    run_execution: bool = Field(
        default=True, description="Execute tasks after preprocessing"
    )

    # --- 5. Specification set ---
    # Determines which .mop files are used for monitor generation in Phase 1.
    # "jca" = Java Cryptography Architecture API misuse detection
    # "generic" = general API usage patterns (Iterator, Collections, Streams)
    # "custom" = user-provided .mop files via custom_specs_dir
    # The two standard sets are mutually exclusive — an experiment uses one
    # or the other, never both.
    specification_set: str = Field(
        default=DEFAULT_SPEC_SET, description="Specification set type"
    )
    custom_specs_dir: Optional[str] = Field(
        default=None, description="Custom specification directory"
    )
    custom_aspects_dir: Optional[str] = Field(
        default=None, description="Custom AspectJ aspects directory"
    )

    # --- 6. APK sources ---
    # Points to the ORIGINAL (uninstrumented) APKs. Phase 1 reads from here
    # and writes instrumented copies to output_dir/instrumented_apks/.
    # When using --skip-instrument, this directory is used directly by Phase 2.
    apks_dir: str = Field(
        default=f"./{DEFAULT_APKS_DIR}/",
        description="Source APK directory path (contains APKs to be instrumented)",
    )
    # Optional filter file: one APK filename per line. Only listed APKs are processed.
    # Useful for large APK directories where you want to run a subset.
    apks_filter: Optional[str] = Field(
        default=None,
        description="Path to text file listing APK filenames to process (one per line)",
    )

    # --- 7. Results and resume ---
    # results_dir is a flat directory (no subdirectory nesting). All artifacts
    # for an experiment live here: tasks.json, CSV reports, experiment_config.json.
    results_dir: Optional[str] = Field(
        default=None, description="Results directory path"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")

    # Resume support: when True, all Phase 1 flags are ignored (forced to False
    # by CLI layer). rv-platform loads completed tasks from tasks.json and skips
    # them, executing only new/pending tasks. Resume is triggered by:
    # - --resume-dir (explicit): points to existing results directory
    # - --name (implicit): if results/<name>/tasks.json exists, resume activates
    resume_mode: bool = Field(
        default=False, description="Enable experiment continuation mode"
    )
    status_file: Optional[str] = Field(
        default=None, description="Path to experiment status file for continuation"
    )

    def model_post_init(self, __context) -> None:
        """Apply defaults and validate after Pydantic model creation.

        Set default name from timestamp, resolve output_dir and results_dir,
        set creation timestamp, and run validation.

        State:
            name: Defaults to "experiment_YYYYMMDD_HHMMSS" if empty
            output_dir: Defaults to constants.INSTRUMENTED_DIR if empty
            results_dir: Derived from output_dir parent if not specified
            created_at: Set to current ISO timestamp if not provided
        """
        date_now = datetime.now()

        if not self.name:
            self.name = f"experiment_{date_now.strftime('%Y%m%d_%H%M%S')}"

        # output_dir defaults to "out/" — the shared pre-processing artifacts directory.
        # When --name is provided, CLI sets this to "results/<name>" instead,
        # so pre-processing artifacts and results coexist in the same directory.
        if not self.output_dir:
            self.output_dir = constants.INSTRUMENTED_DIR

        # results_dir defaults to a "results/" sibling of output_dir.
        # For CLI-created configs, results_dir is typically set explicitly
        # to the same path as output_dir (flat directory structure).
        if not self.results_dir:
            if os.path.isabs(self.output_dir):
                self.results_dir = os.path.join(
                    os.path.dirname(self.output_dir), RESULTS_DIR
                )
            else:
                self.results_dir = RESULTS_DIR

        if not self.created_at:
            self.created_at = date_now.isoformat()

        # Logger is local (not stored as instance attribute) to avoid Pydantic
        # trying to validate/serialize it — Pydantic models must only contain
        # serializable fields.
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.config", {CONTEXT_COMPONENT: "ExperimentConfig"}
        )
        self.validate()
        logger.info(f"ExperimentConfig initialized: {self.to_json()}")

    @ErrorHandler.handle_errors(
        component="ExperimentConfig",
        phase="validate",
    )
    def validate(self) -> None:
        """
        Comprehensive validation of experiment configuration.

        ### Validation Strategy:
        - Basic parameter validation (names, timeouts, repetitions)
        - Tool configuration validation
        - APK source validation with pattern matching
        - Monitored operations specification validation
        - Directory structure validation

        Raises:
            ValueError: If configuration is invalid
            ConfigurationError: If configuration structure is inconsistent
        """
        # Validate basic configuration
        if not self.name:
            raise ValueError("Experiment name cannot be empty")

        if not self.tool_configs:
            raise ValueError("At least one tool must be configured")

        if self.repetitions <= 0:
            raise ValueError("Repetitions must be positive")

        if not self.timeouts or any(t <= 0 for t in self.timeouts):
            raise ValueError("All timeouts must be positive")

        # Validate tool configurations
        for tool_config in self.tool_configs:
            if not tool_config.name:
                raise ValueError("Tool configuration must have a name")

        # Validate APK sources
        if not self._validate_apk_sources():
            raise ConfigurationError(
                "No valid APK source directory configured. Ensure apks_dir exists and contains APK files."
            )

        # Validate specification set. "jca" and "generic" map to predefined directories
        # under RVSEC_HOME; "custom" requires a user-provided path to .mop files.
        valid_spec_sets = ["jca", "generic", "custom"]
        if self.specification_set not in valid_spec_sets:
            raise ValueError(
                f"Invalid specification set '{self.specification_set}'. "
                f"Must be one of: {valid_spec_sets}"
            )

        # Validate tool variants
        self._validate_tool_variants()

        # Get logger for validation message
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.config", {CONTEXT_COMPONENT: "ExperimentConfig"}
        )
        logger.info("Configuration validation completed successfully")

    def _validate_apk_sources(self) -> bool:
        """
        Validate that APK source directory is available and contains APK files.

        Returns:
            True if valid APK sources are configured, False otherwise
        """
        # Check APK directory
        if self.apks_dir and Path(self.apks_dir).exists():
            apk_files = list(Path(self.apks_dir).glob("*.apk"))
            return len(apk_files) > 0

        return False

    @ErrorHandler.handle_errors(
        component="ExperimentConfig", phase="validate_tool_variants"
    )
    def _validate_tool_variants(self) -> None:
        """
        Validate all tool variant combinations in configuration.

        ### Variant Validation Strategy:
        - Check if tool exists in registry
        - Validate each variant exists or can be created as custom variant
        - Validate custom variants have required parameters
        - Provide helpful error messages for invalid configurations

        ### Module Hierarchy:
        This method coordinates validation across module boundaries while respecting
        the hierarchy by importing from lower-level modules only when needed.

        Raises:
            ConfigurationError: If any tool/variant combination is invalid
        """
        # Lazy import to avoid circular dependencies: rv-tools depends on rv-android-core,
        # and importing it at module level could trigger import chains during testing.
        try:
            from rv_tools import ToolRegistry
        except ImportError:
            logging_manager = LoggingManager.get_instance()
            logger = logging_manager.get_logger(
                "rv_experiment.config", {CONTEXT_COMPONENT: "ExperimentConfig"}
            )
            logger.warning("rv-tools not available - skipping tool variant validation")
            return

        # ToolRegistry is populated at import time:
        # - rv-tools registers builtin tools (monkey, droidbot, ape)
        # - rv-platform registers external tools (rvagent, rvsmart, aperv)
        # Validation runs against the current registry state.
        tool_registry = ToolRegistry.get_instance()

        for tool_config in self.tool_configs:
            tool_name = tool_config.name

            # Check if tool is registered
            if not tool_registry.is_tool_registered(tool_name):
                available_tools = tool_registry.get_all_tool_names()
                raise ConfigurationError(
                    f"Tool '{tool_name}' not found in registry. Available tools: {available_tools}"
                )

            # Validate the variant (each ToolConfig has exactly one variant)
            variant_name = tool_config.variant
            if variant_name and variant_name != "default":
                if not tool_registry.validate_tool_variant(tool_name, variant_name):
                    # Check if this is a custom variant with complete parameters
                    if not self._validate_custom_variant(tool_config, variant_name):
                        try:
                            available_variants = list(
                                tool_registry.get_tool_variants(tool_name)
                            )
                        except:
                            available_variants = ["default"]
                        raise ConfigurationError(
                            f"Invalid variant '{variant_name}' for tool '{tool_name}'. "
                            f"Available variants: {available_variants}. "
                            f"For custom variants, ensure all required parameters are provided."
                        )

    def _validate_custom_variant(
        self, tool_config: ToolConfig, variant_name: str
    ) -> bool:
        """
        Validate custom variant has required parameters for complete configuration.

        ### Custom Variant Requirements:
        For RVAndroid custom variants, required parameters are:
        - llm_type: LLM backend type
        - llm_model: Model name
        - prompt_strategy: Prompt generation strategy

        For other tools, basic validation checks for some parameters.

        Args:
            tool_config: Tool configuration with parameters
            variant_name: Name of the custom variant

        Returns:
            True if custom variant is valid, False otherwise
        """
        # Custom variants should have some parameters
        return len(tool_config.parameters) > 0

    def get_apk_list(self) -> List[str]:
        """
        Get list of APK files to process based on configuration.

        If apks_filter is set, only APKs whose filename appears in the
        filter file are included.

        Returns:
            List of APK file paths

        Raises:
            ConfigurationError: If no APK files are found
        """
        # Scan apks_dir for all .apk files, then optionally filter.
        # The filter file is a plain text list of APK filenames (one per line),
        # useful for batch processing subsets of a large APK corpus.
        apks = []

        if self.apks_dir:
            apks_dir_path = Path(self.apks_dir)
            if apks_dir_path.exists():
                apks.extend([str(p) for p in apks_dir_path.glob("*.apk")])

        if self.apks_filter:
            allowed = set(Path(self.apks_filter).read_text().strip().splitlines())
            apks = [a for a in apks if Path(a).name in allowed]

        if not apks:
            raise ConfigurationError(
                f"No APK files found in directory: {self.apks_dir}"
                + (f" (filter: {self.apks_filter})" if self.apks_filter else "")
            )

        return apks

    def validate_specs_dir(self, directory_path_str: str) -> bool:
        """Validate that a specification directory contains .mop files.

        Check directory existence and scan for at least one .mop file.
        Used by get_monitored_operations_config() to validate custom
        specification directories before monitor generation.

        Args:
            directory_path_str: Path to specification directory to validate

        Returns:
            True if directory exists and contains at least one .mop file
        """
        # Convert the string path to a Path object
        path = Path(directory_path_str)

        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger("rv_experiment.config")

        # 1. Validate if it's an existing directory
        if not path.is_dir():
            logger.info(
                f"'{directory_path_str}' is not a valid directory or does not exist."
            )
            return False

        # 2. Iterate over files in the directory and check for .mop files
        for item in path.iterdir():
            if item.is_file() and item.suffix.lower() == EXTENSION_MOP:
                logger.debug(
                    f"{EXTENSION_MOP} file found: '{item.name}' in '{directory_path_str}'"
                )
                return True

        logger.info(f"No {EXTENSION_MOP} files found in '{directory_path_str}'.")
        return False

    def get_monitored_operations_config(self) -> RVGeneratorConfig:
        """
        Just-in-time configuration for monitor generation based on specification set.

        ### Configuration Pattern:
        This method creates monitor generation configuration only when needed,
        providing flexibility while maintaining module independence.

        ### Specification Set Support:
        - **JCA**: Java Cryptography Architecture API monitoring
        - **Generic**: Generic programming patterns (Iterator, Collections, etc.)
        - **Custom**: User-defined specification sets

        ### Implementation:
        Returns a typed RVGeneratorConfig instance that provides type safety,
        validation, and integration with the configuration architecture.

        Returns:
            RVGeneratorConfig instance with monitor generation configuration

        Raises:
            ConfigurationError: If specification set is not supported
            MonitorConfigError: If RVGeneratorConfig validation fails
        """
        rvsec_root = self.get_effective_rvsec_root()

        # Map specification_set to the directory containing .mop files.
        # The directory structure under RVSEC_HOME is:
        #   rvsec/rvsec-mop/src/main/resources/
        #     jca/       <- JCA crypto API specs (.mop files)
        #     generic/   <- generic API usage specs (.mop files)
        #     aspect/    <- shared AspectJ aspects
        mop_base_dir = os.path.join(
            rvsec_root, "rvsec", "rvsec-mop", "src", "main", "resources"
        )
        if self.specification_set == "jca":
            mop_specs_dir = os.path.join(mop_base_dir, "jca")
        elif self.specification_set == "generic":
            mop_specs_dir = os.path.join(mop_base_dir, "generic")
        elif self.specification_set == "custom":
            if self.custom_specs_dir:
                mop_specs_dir = self.custom_specs_dir
                if not self.validate_specs_dir(mop_specs_dir):
                    raise ConfigurationError(f"Invalid specs dir: {mop_specs_dir}")
            else:
                raise ConfigurationError(
                    f"Unsupported specification set: {self.specification_set}"
                )
        else:
            raise ConfigurationError(
                f"Unsupported specification set: {self.specification_set}"
            )

        try:
            # Explicit paths prevent RVGeneratorConfig's internal resolver from
            # overriding mop_specs_dir with a default — we need the spec-set-specific
            # directory determined above, not whatever the config class thinks is default.
            if self.custom_aspects_dir:
                aspects_dir = self.custom_aspects_dir
            else:
                # Use standard aspects directory from RVSEC
                aspects_dir = os.path.join(
                    rvsec_root,
                    "rvsec",
                    "rvsec-mop",
                    "src",
                    "main",
                    "resources",
                    "aspect",
                )

            return RVGeneratorConfig(
                rvsec_root=rvsec_root,
                javamop_bin=os.path.join(rvsec_root, "javamop", "bin", "javamop"),
                rvmonitor_bin=os.path.join(
                    rvsec_root, "rv-monitor", "bin", "rv-monitor"
                ),
                mop_specs_dir=mop_specs_dir,
                aspects_dir=aspects_dir,
            )
        except MonitorConfigError as e:
            raise ConfigurationError(
                f"Monitor generation configuration failed: {e}"
            ) from e

    def get_instrumentation_config(self) -> RVInstrumentationConfig:
        """
        Just-in-time configuration for APK instrumentation.

        ### Just-in-Time Configuration Pattern:
        This method creates instrumentation configuration only when needed,
        deriving parameters from experiment configuration while maintaining
        module independence through simple parameter passing.

        ### Implementation:
        Returns a typed RVInstrumentationConfig instance that provides type safety,
        validation, and integration with the configuration architecture.

        Returns:
            RVInstrumentationConfig instance with instrumentation configuration

        Raises:
            ConfigurationError: If APK configuration is invalid
            InstrumentationConfigError: If RVInstrumentationConfig validation fails
        """
        rvsec_root = self.get_effective_rvsec_root()

        # working_dir must be rv-android/ (not the project root) because
        # instrumentation tools reference lib/ and tools/ relative to it.
        rv_android_dir = os.path.join(rvsec_root, "rv-android")

        # Monitors generated in Phase 1 Step 1 are consumed here.
        # The monitor_output_dir must match what _generate_monitors() writes to.
        monitor_output_dir = (
            os.path.join(self.output_dir, MONITORS_DIR) if self.output_dir else None
        )

        try:
            # Create RVInstrumentationConfig instance with tool paths
            return RVInstrumentationConfig(
                rvsec_root=rvsec_root,
                monitor_output_dir=monitor_output_dir,
                working_dir=rv_android_dir,  # Use rv-android dir where lib/ exists
                instrumented_dir=os.path.join(self.output_dir, INSTRUMENTED_APKS_DIR),
                keystore_password="password",
            )
        except InstrumentationConfigError as e:
            raise ConfigurationError(
                f"Instrumentation configuration failed: {e}"
            ) from e

    def get_rv_instrumentation_config(self) -> RVInstrumentationConfig:
        """Delegate to get_instrumentation_config().

        Alias used by PreProcessor for consistent naming with other
        get_*_config() methods.

        Returns:
            RVInstrumentationConfig instance with instrumentation configuration

        Raises:
            ConfigurationError: If APK configuration is invalid
            InstrumentationConfigError: If RVInstrumentationConfig validation fails
        """
        return self.get_instrumentation_config()

    def get_static_analysis_config(self) -> RVStaticAnalysisConfig:
        """Create static analysis configuration on demand.

        Resolve GATOR tool paths from RVSEC_HOME and configure analysis
        output directory. Supports RV_SA_TIMEOUT and RV_JVM_MEMORY env
        vars to override default timeout and JVM memory settings.

        Returns:
            RVStaticAnalysisConfig with tool paths and output directory

        Raises:
            ConfigurationError: If configuration creation fails
        """
        rvsec_root = self.get_effective_rvsec_root()

        # GATOR and its analysis client JAR live under rv-android/lib/gator/.
        # This path is fixed by the RVSEC project structure.
        rv_android_dir = os.path.join(rvsec_root, "rv-android")
        lib_dir = os.path.join(rv_android_dir, "lib")

        try:
            gator_dir = os.path.join(lib_dir, "gator")
            analysis_client_jar = os.path.join(gator_dir, "rvsec-analysis-client.jar")

            # RV_SA_TIMEOUT and RV_JVM_MEMORY env vars override SA defaults.
            # Used by preprocess_docker.py --sa-timeout/--jvm-memory for retry runs.
            # GATOR static analysis can be very slow on large APKs (>30 min),
            # so the timeout override allows per-APK tuning in batch runs.
            kwargs = {}
            sa_timeout = os.environ.get("RV_SA_TIMEOUT")
            if sa_timeout:
                kwargs["analysis_timeout"] = int(sa_timeout)
            jvm_memory = os.environ.get("RV_JVM_MEMORY")
            if jvm_memory:
                kwargs["jvm_memory"] = jvm_memory

            return RVStaticAnalysisConfig(
                rvsec_root=rvsec_root,
                lib_dir=lib_dir,
                gator_dir=gator_dir,
                analysis_client_jar=analysis_client_jar,
                output_dir=self.output_dir,
                working_dir=self.output_dir,
                validate_on_init=False,
                **kwargs,
            )
        except Exception as e:
            raise ConfigurationError(
                f"Static analysis configuration failed: {e}"
            ) from e

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary via Pydantic model_dump.

        Returns:
            Configuration as dictionary with all fields serialized
        """
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """Serialize configuration to JSON string.

        Args:
            indent: JSON indentation level for formatting

        Returns:
            Configuration as formatted JSON string
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentConfig":
        """Create configuration from dictionary with ToolConfig conversion.

        Convert raw dict entries in tool_configs to ToolConfig instances
        before constructing the model.

        Args:
            data: Configuration dictionary from storage or API

        Returns:
            Validated ExperimentConfig instance
        """
        # Handle tool configurations using ToolConfig.from_dict() with current field names
        if "tool_configs" in data and isinstance(data["tool_configs"], list):
            data["tool_configs"] = [
                ToolConfig.from_dict(tc) if isinstance(tc, dict) else tc
                for tc in data["tool_configs"]
            ]

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "ExperimentConfig":
        """Parse JSON string into validated ExperimentConfig.

        Args:
            json_str: JSON configuration string

        Returns:
            Validated ExperimentConfig instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, file_path: str) -> "ExperimentConfig":
        """Load and validate configuration from JSON file.

        Args:
            file_path: Path to configuration file (JSON format)

        Returns:
            Validated ExperimentConfig instance

        Raises:
            FileNotFoundError: If configuration file does not exist
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(path, "r") as f:
            data = json.load(f)

        return cls.from_dict(data)

    def save_to_file(self, file_path: str) -> None:
        """Save configuration to JSON file, creating parent directories.

        Args:
            file_path: Destination path for the JSON configuration file
        """
        path = Path(file_path)

        # Create parent directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save configuration as JSON
        with open(path, "w") as f:
            f.write(self.to_json())

        # Get logger for save message
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.config", {CONTEXT_COMPONENT: "ExperimentConfig"}
        )
        logger.info(f"Configuration saved to: {file_path}")

    def get_module_config(self, module_name: str) -> Union[
        RVGeneratorConfig,
        RVInstrumentationConfig,
        RVStaticAnalysisConfig,
        Dict[str, Any],
    ]:
        """Get module-specific configuration by module name.

        Dispatch to the appropriate get_*_config() method based on module name.
        Return empty dict for unrecognized modules.

        Args:
            module_name: One of "rv-monitor-generator", "rv-instrumentation",
                or "rv-static-analysis"

        Returns:
            Typed configuration instance for known modules, empty dict otherwise
        """
        if module_name == "rv-monitor-generator":
            return self.get_monitored_operations_config()
        elif module_name == "rv-instrumentation":
            return self.get_instrumentation_config()
        elif module_name == "rv-static-analysis":
            return self.get_static_analysis_config()
        else:
            return {}

    def get_instrumented_dir(self) -> str:
        """Return the standard instrumented APKs directory constant.

        Returns:
            Path to instrumented APKs directory
        """
        return INSTRUMENTED_DIR

    def get_timestamp_string(self) -> str:
        """Return current timestamp as YYYYMMDD_HHMMSS string.

        Returns:
            Formatted timestamp string
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @ErrorHandler.handle_errors(
        component="ExperimentConfig", phase="rvsec_root_hierarchy"
    )
    def get_effective_rvsec_root(self) -> str:
        """
        Get RVSEC_HOME with configuration hierarchy support.

        ### Configuration Hierarchy:
        1. Priority 1: Configuration override (self.rvsec_root) - enables experiment-specific paths
        2. Priority 2: Environment variable (ENV_RVSEC_HOME) - system default
        3. Priority 3: Error if neither defined - required for operation

        ### Role in the System:
        - Provides centralized RVSEC_HOME resolution for all module configurations
        - Enables experiment-specific path overrides for isolated execution
        - Maintains backward compatibility with environment variable usage
        - Validates path existence regardless of source

        Returns:
            Effective RVSEC_HOME path

        Raises:
            ConfigurationError: If RVSEC_HOME not found in configuration or environment
        """
        # Priority 1: Configuration override takes precedence
        if self.rvsec_root:
            if not os.path.exists(self.rvsec_root):
                raise ConfigurationError(
                    f"Configured rvsec_root path does not exist: {self.rvsec_root}"
                )
            return self.rvsec_root

        # Priority 2: Environment variable fallback
        env_value = os.getenv(ENV_RVSEC_HOME)
        if env_value:
            if not os.path.exists(env_value):
                raise ConfigurationError(
                    f"RVSEC_HOME environment path does not exist: {env_value}"
                )
            return env_value

        # Priority 3: Error for required configuration
        raise ConfigurationError(
            "RVSEC_HOME not found in configuration or environment. "
            "Set rvsec_root field in configuration or RVSEC_HOME environment variable"
        )
