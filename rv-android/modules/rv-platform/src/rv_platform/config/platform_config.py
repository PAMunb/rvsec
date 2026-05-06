# rv_platform/config/platform_config.py
"""
Configuration schema for rv-platform.

This module defines the configuration structure for the rv-platform module,
providing validation and loading capabilities for platform execution parameters.
"""

import json
from pathlib import Path
from typing import List, Optional

from pydantic import ConfigDict, Field, field_validator
from rv_android_core.domain.task import ToolConfig
from rv_android_core.util.validation.base import BaseValidatedModel


class PlatformConfig(BaseValidatedModel):
    """
    Configuration schema for rv-platform execution.

    ### Architectural Decisions:
    - Uses Pydantic for validation and serialization
    - Provides sensible defaults for optional parameters
    - Supports both file and object-based configuration loading
    - Uses constants from rv-android-core for consistency

    ### Role in the System:
    - Defines the complete set of parameters for platform execution
    - Validates configuration before execution begins
    - Supports serialization for persistence and debugging
    - Enables reproducible platform execution

    ### Key Features:
    - Field validators ensure apks_dir exists, tools are non-empty, repetitions
      and timeouts are positive, and log_level is a standard Python level.
    - File-based loading (from_file) and saving (to_file) for JSON configs.
    - get_total_tasks() calculates the Cartesian product size of APKs x tools
      x repetitions x timeouts.

    ### Integration Points:
    - Platform.__init__ receives this config and calls validate_dependencies().
    - rv-experiment creates PlatformConfig and passes it to Platform.
    - ToolConfig instances (from rv-android-core) are embedded in the tools list.
    """

    # gh55 INV-CORE-32: explicit declaration at the boundary class so the
    # entrypoint allow-list + ENV_* registry contract is auditable here, not
    # only via the BaseValidatedModel ancestor.
    model_config = ConfigDict(extra="forbid")

    # Required parameters — these define the experiment's Cartesian product:
    # total_tasks = len(APKs) x len(tools) x repetitions x len(timeouts)
    apks_dir: str = Field(description="Directory containing APK files")
    tools: List[ToolConfig] = Field(description="List of tools to execute")
    repetitions: int = Field(default=1, description="Number of repetitions per task")
    timeouts: List[int] = Field(
        default_factory=lambda: [60], description="Timeout values in seconds"
    )

    # Optional parameters with defaults.
    # max_parallel_tasks > 1 enables parallel execution via ExecutionController
    # (in rv-experiment), where each task runs in a separate Docker container
    # with its own emulator on a unique port.
    max_parallel_tasks: int = Field(
        default=1, description="Maximum number of parallel tasks"
    )
    no_window: bool = Field(default=False, description="Run in headless mode")
    results_dir: str = Field(
        default="results", description="Output directory for results"
    )
    task_storage_file: str = Field(
        default="tasks.json", description="Task persistence file"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    # When True, CSV/JSON generation is skipped after execution. Useful for
    # debugging (faster iteration) or when result processing will be run
    # standalone later via `rv-platform run --process-results <dir>`.
    skip_result_processing: bool = Field(
        default=False, description="Skip result processing after execution"
    )
    # Filter file allows running experiments on a subset of APKs without
    # reorganizing the APK directory. The file contains one APK filename per
    # line (e.g., "com.example.app_1.apk"). Only APKs matching these filenames
    # are included in task generation.
    apks_filter_file: Optional[str] = Field(
        default=None,
        description="Path to text file listing APK filenames to process (one per line)",
    )

    @field_validator("apks_dir")
    @classmethod
    def validate_apks_dir(cls, v):
        if not v or not v.strip():
            raise ValueError("APKs directory cannot be empty")
        path = Path(v.strip())
        if not path.exists():
            raise ValueError(f"APKs directory does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"APKs directory is not a directory: {path}")
        return str(path)

    @field_validator("tools")
    @classmethod
    def validate_tools(cls, v):
        if not v:
            raise ValueError("At least one tool must be specified")
        return v

    @field_validator("repetitions")
    @classmethod
    def validate_repetitions(cls, v):
        if v < 1:
            raise ValueError("Repetitions must be at least 1")
        return v

    @field_validator("timeouts")
    @classmethod
    def validate_timeouts(cls, v):
        if not v:
            raise ValueError("At least one timeout must be specified")
        for timeout in v:
            if timeout < 1:
                raise ValueError(f"Timeout must be at least 1 second: {timeout}")
        return v

    @field_validator("max_parallel_tasks")
    @classmethod
    def validate_max_parallel_tasks(cls, v):
        if v < 1:
            raise ValueError("Max parallel tasks must be at least 1")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @classmethod
    def from_file(cls, config_path: str) -> "PlatformConfig":
        """
        Load configuration from a JSON file.

        Args:
            config_path: Path to the configuration file

        Returns:
            PlatformConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            return cls(**config_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")

    def to_file(self, config_path: str) -> None:
        """
        Save configuration to a JSON file.

        Args:
            config_path: Path where to save the configuration
        """
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

    def get_total_tasks(self) -> int:
        """
        Calculate the total number of tasks that will be generated.

        Compute the Cartesian product: APK count x tool count x repetitions
        x timeout count.

        Returns:
            Total number of tasks based on current configuration.
        """
        # Count APK files
        apks_path = Path(self.apks_dir)
        apk_count = len(list(apks_path.glob("*.apk")))

        # Each ToolConfig represents exactly one (tool, variant) combination
        tool_count = len(self.tools)

        return apk_count * tool_count * self.repetitions * len(self.timeouts)

    def validate_dependencies(self) -> bool:
        """
        Validate that all required runtime dependencies are available.

        Check that the APKs directory contains at least one .apk file and
        that all tool names are non-empty. Called by Platform.__init__ before
        task generation begins.

        Returns:
            True if all dependencies are valid.

        Raises:
            ValueError: If no APK files exist in apks_dir or any tool has an
                empty name.
        """
        # Check APKs directory has APK files
        apks_path = Path(self.apks_dir)
        apk_files = list(apks_path.glob("*.apk"))
        if not apk_files:
            raise ValueError(f"No APK files found in directory: {self.apks_dir}")

        # Validate tools (basic check - detailed validation happens at runtime)
        for tool in self.tools:
            if not tool.name.strip():
                raise ValueError("Tool name cannot be empty")

        return True
