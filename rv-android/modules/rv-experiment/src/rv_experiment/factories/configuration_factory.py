"""
Configuration factory for RV-Android experiments.

Provide factory methods for creating ExperimentConfig instances from different
sources: CLI arguments, dictionaries, and pre-built templates. The factory
handles tool specification DSL parsing, default generation, and validation.

Relates to Requirement "Experiment Configuration (FR15)" (build a validated
ExperimentConfig aggregating all experiment parameters) and Requirement
"CLI with Tool Specification DSL (FR16, NFR05)" (the tool-spec DSL parsing).
See openspec/specs/experiment/spec.md.

TODO(dead-code): ConfigurationFactory has no production caller — only re-exported by
factories/__init__.py and covered by tests/test_configuration_factory*.py. The live CLI
(__main__.py) uses its own DSL parser (parse_tool_specification) and ExperimentController
builds ExperimentConfig directly. Candidate for P1/P3 removal.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List

from rv_android_core.domain.task import ToolConfig
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.config import ExperimentConfig


class ConfigurationFactory:
    """Factory for creating experiment configurations.

    ### Role in the System:
    Provides factory methods for creating ExperimentConfig from CLI arguments,
    dictionaries, and pre-built templates. Relates to Requirement "Experiment
    Configuration (FR15)" and Requirement "CLI with Tool Specification DSL
    (FR16, NFR05)" (openspec/specs/experiment/spec.md).

    Note (current state): this class has no production caller — the live CLI in
    __main__.py builds ExperimentConfig via its own DSL parser, so this factory
    is exercised only by tests. See the module-level TODO(dead-code). Some
    methods below are additionally broken against the current ExperimentConfig
    model (see per-method TODOs), so do not treat this class as an authoritative
    reference for how a valid config is built.

    ### Key Methods:
    - create_cli_config(): Build config from CLI-style parameters (currently broken)
    - create_full_config(): Build config with explicit tool_configs
    - create_basic/advanced/llm_template(): Pre-built configs for common scenarios
    - parse_tool_specifications(): Parse tool DSL strings into structured dicts
    """

    def __init__(self):
        """Initialize configuration factory with logging and error handling."""
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.factories.configuration",
            {CONTEXT_COMPONENT: "ConfigurationFactory"},
        )

        self.logger.info("ConfigurationFactory initialized")

    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_cli_config",
    )
    def create_cli_config(
        self,
        tools: List[Dict[str, Any]],
        experiment_dir: str = "./out/",
        timeout: int = 300,
        repetitions: int = 1,
        apk_dir: str = "./apks_examples/",
        specification_set: str = "jca",
        **kwargs,
    ) -> ExperimentConfig:
        """
        Build a CLI-style ExperimentConfig from loose parameters.

        Intended to serve Requirement "Experiment Configuration (FR15)" by
        producing a validated ExperimentConfig from CLI-shaped inputs. It does
        NOT currently satisfy that requirement: the ExperimentConfig call below
        passes kwargs (experiment_dir, experiment_id, tools, timeout) that are
        not fields on the current model. ExperimentConfig is declared with
        model_config = ConfigDict(extra="forbid") (config.py) and its real
        fields are name/output_dir/tool_configs/timeouts (plural). Pydantic
        therefore raises ValidationError on every call, and the
        @ErrorHandler.handle_errors decorator swallows it, so this method always
        returns None. The test suite documents this current behavior.

        Args:
            tools: List of tool specifications with variants and parameters
            experiment_dir: Base experiment directory (default: ./out/)
            timeout: Execution timeout in seconds (default: 300)
            repetitions: Number of repetitions (default: 1)
            apk_dir: APK directory path (default: ./apks_examples/)
            specification_set: Monitored operations specification set (default: jca)
            **kwargs: Additional configuration parameters

        Returns:
            Intended: a configured ExperimentConfig. Actual: None (see above).
        """
        # TODO(FR16): create_cli_config passes non-existent kwargs (experiment_dir/experiment_id/
        # tools/timeout) to ExperimentConfig, which is extra="forbid" with fields
        # name/output_dir/tool_configs/timeouts → ValidationError, swallowed to None by ErrorHandler.
        # Broken against the current model; needs a separate OpenSpec change.
        try:
            # Generate unique experiment ID
            experiment_id = (
                f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            )

            # Create configuration with factory pattern
            config = ExperimentConfig(
                experiment_dir=experiment_dir,
                experiment_id=experiment_id,
                tools=tools,
                timeout=timeout,
                repetitions=repetitions,
                apks_dir=apk_dir,
                specification_set=specification_set,
                **kwargs,
            )

            # Validate configuration
            config.validate()

            self.logger.info(
                f"Created CLI configuration for experiment: {experiment_id}"
            )
            return config

        except Exception as e:
            self.logger.error(f"Failed to create CLI configuration: {e}")
            raise

    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_full_config",
    )
    def create_full_config(
        self,
        name: str,
        tool_configs: List[ToolConfig],
        output_dir: str = "",
        specification_set: str = "jca",
        **kwargs,
    ) -> ExperimentConfig:
        """
        Build an ExperimentConfig from explicit tool_configs.

        Supports Requirement "Experiment Configuration (FR15)": constructs
        ExperimentConfig with the current model fields (name, tool_configs,
        output_dir), so it is structurally valid — unlike create_cli_config.
        Has no production caller (see the module-level TODO(dead-code)).

        Args:
            name: Experiment name
            tool_configs: List of tool configurations
            output_dir: Output directory for experiment results
            specification_set: Monitored operations specification set
            **kwargs: Additional configuration parameters

        Returns:
            Configured ExperimentConfig instance
        """
        try:
            # Generate defaults if not provided
            if not output_dir:
                output_dir = f"./out/experiments/{name}"

            # Create configuration with factory pattern
            config = ExperimentConfig(
                name=name,
                tool_configs=tool_configs,
                output_dir=output_dir,
                specification_set=specification_set,
                **kwargs,
            )

            # Validate configuration
            config.validate()

            self.logger.info(f"Created full configuration for experiment: {name}")
            return config

        except Exception as e:
            self.logger.error(f"Failed to create full configuration: {e}")
            raise

    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_basic_template",
    )
    def create_basic_template(self) -> ExperimentConfig:
        """
        Return a pre-built ExperimentConfig for a single-tool (monkey) run.

        Supports Requirement "Experiment Configuration (FR15)"; uses the current
        model fields.

        Returns:
            Basic ExperimentConfig template
        """
        return ExperimentConfig(
            name="basic_experiment",
            description="Basic experiment template",
            tool_configs=[ToolConfig(name="monkey")],
            specification_set="jca",
        )

    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_advanced_template",
    )
    def create_advanced_template(self) -> ExperimentConfig:
        """
        Return a pre-built multi-tool ExperimentConfig (monkey + droidbot).

        Supports Requirement "Experiment Configuration (FR15)"; uses the current
        model fields, including a variant (singular) on the droidbot ToolConfig.

        Returns:
            Advanced ExperimentConfig template
        """
        return ExperimentConfig(
            name="advanced_experiment",
            description="Advanced experiment template",
            tool_configs=[
                ToolConfig(name="monkey"),
                ToolConfig(name="droidbot", variant="dfs_greedy"),
            ],
            repetitions=3,
            specification_set="jca",
        )

    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_llm_template",
    )
    def create_llm_template(self) -> ExperimentConfig:
        """
        Return a pre-built ExperimentConfig for an LLM-driven (rvagent) run.

        Supports Requirement "Experiment Configuration (FR15)"; uses the current
        model fields.

        Returns:
            LLM-focused ExperimentConfig template
        """
        # LLM-driven testing needs longer timeouts because the agent explores
        # the app interactively, taking screenshots and reasoning about each step.
        # 30 minutes is a reasonable default for thorough exploration.
        return ExperimentConfig(
            name="llm_experiment",
            description="LLM-driven testing experiment",
            tool_configs=[ToolConfig(name="rvagent", variant="multimode")],
            timeouts=[1800],
            specification_set="jca",
        )

    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="parse_tool_specifications",
    )
    def parse_tool_specifications(self, tool_specs: List[str]) -> List[Dict[str, Any]]:
        """
        Parse tool specification strings into structured configurations.

        Relates to Requirement "CLI with Tool Specification DSL (FR16, NFR05)":
        parses the DSL `tool_name[:variant1][:variant2][@param1=value1,...]` per
        spec. This method receives an ALREADY-SPLIT List[str] (one entry per
        tool), so it does not perform the multi-tool comma-splitting governed by
        INV-EXP-09 — that param-aware comma split is done by the live parser in
        __main__.py, not here.

        Args:
            tool_specs: List of tool specification strings

        Returns:
            List of structured tool configuration dictionaries
        """
        try:
            parsed_tools = []

            for tool_spec in tool_specs:
                # Parse tool specification using DSL
                parsed_tool = self._parse_single_tool_spec(tool_spec.strip())
                parsed_tools.append(parsed_tool)

            self.logger.info(f"Parsed {len(parsed_tools)} tool specifications")
            return parsed_tools

        except Exception as e:
            self.logger.error(f"Failed to parse tool specifications: {e}")
            raise

    def _parse_single_tool_spec(self, tool_spec: str) -> Dict[str, Any]:
        """
        Parse a single tool specification string.

        DSL format: `tool_name[:variant1][:variant2][@param1=value1,param2=value2]`,
        related to Requirement "CLI with Tool Specification DSL (FR16, NFR05)".
        This method handles commas WITHIN one already-split spec's `@params`
        section only.

        Args:
            tool_spec: Tool specification string to parse

        Returns:
            Structured tool configuration dictionary with keys name/variants/parameters.

            The "variants" key holds a PLURAL list, which is the shape that
            Requirement "Experiment Configuration (FR15)" declares unsupported:
            the current model uses ToolConfig(variant: str, singular), and per P3
            the old plural `variants: [...]` format was dropped. See TODO(FR15).
        """
        # TODO(FR15): _parse_single_tool_spec emits the {"variants": [...]} plural-list shape that
        # Requirement "Experiment Configuration (FR15)" declares unsupported — the current model uses
        # ToolConfig(variant: str, singular). Dead output shape; needs a separate OpenSpec change.
        # The DSL uses two delimiters:
        # - '@' separates tool identity from parameters
        # - ':' separates tool name from variant names
        # Parameters without '=' are treated as boolean flags (e.g., "verbose").
        try:
            if "@" in tool_spec:
                tool_part, params_part = tool_spec.split("@", 1)
                # Parse parameters
                parameters = {}
                for param in params_part.split(","):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        parameters[key.strip()] = value.strip()
                    else:
                        # Boolean flag parameter
                        parameters[param.strip()] = True
            else:
                tool_part = tool_spec
                parameters = {}

            # Split tool name and variants
            parts = tool_part.split(":")
            tool_name = parts[0].strip()
            variants = [v.strip() for v in parts[1:] if v.strip()]

            if not tool_name:
                raise ValueError("Tool name cannot be empty")

            return {"name": tool_name, "variants": variants, "parameters": parameters}

        except Exception as e:
            raise ValueError(f"Invalid tool specification '{tool_spec}': {e}")

    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_from_dict",
    )
    def create_from_dict(
        self, config_data: Dict[str, Any], config_type: str = "cli"
    ) -> ExperimentConfig:
        """
        Build an ExperimentConfig from a dictionary via ExperimentConfig.from_dict.

        Relates to Requirement "Experiment Configuration (FR15)"; delegates
        deserialization to ExperimentConfig.from_dict() then calls validate().

        Current state: the "cli" and "full" branches both call the same
        ExperimentConfig.from_dict(config_data), so config_type is not a
        behavioral distinction here — the only effect is rejecting an unknown
        value with ValueError.

        Args:
            config_data: Configuration data dictionary
            config_type: Type of configuration to create ("cli" or "full")

        Returns:
            Configured experiment configuration instance
        """
        try:
            if config_type == "cli":
                config = ExperimentConfig.from_dict(config_data)
            elif config_type == "full":
                config = ExperimentConfig.from_dict(config_data)
            else:
                raise ValueError(f"Unknown configuration type: {config_type}")

            # Validate configuration
            config.validate()

            self.logger.info(f"Created {config_type} configuration from dictionary")
            return config

        except Exception as e:
            self.logger.error(f"Failed to create configuration from dictionary: {e}")
            raise
