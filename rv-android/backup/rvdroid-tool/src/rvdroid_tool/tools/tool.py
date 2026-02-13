"""
RVDroid Tool Implementation

### Architectural Overview:
This module implements the RVDroid testing tool as an AbstractTool plugin for
the RV-Android framework. RVDroid provides UIAutomator2-based Android testing
with optional LLM strategic guidance, maintaining its own core execution engine
while integrating with the modular architecture.

### Key Architectural Decisions:
- Implements AbstractTool interface for seamless platform integration
- Maintains separation from rvandroid-tool (no cross-references)
- Uses rv-llm framework for LLM backend abstraction
- Integrates with existing RVDroidRunner for core testing logic
- Provides guidance-based LLM integration (not action generation)

### Role in the System:
- Entry point for RVDroid execution within RV-Android framework
- Coordinates configuration resolution and tool initialization
- Manages LLM guidance service lifecycle when enabled
- Bridges framework integration with existing RVDroid components

### Design Patterns:
- Plugin Pattern: Registered via rv-tools for platform discovery
- Factory Pattern: Creates configurations from variant definitions
- Facade Pattern: Provides simplified interface to complex RVDroid system
- Strategy Pattern: Supports multiple LLM and testing configurations
"""

from typing import Dict, List, Any, Optional

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVAndroidToolError, ConfigurationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_llm import OllamaLLM

from rvdroid_tool.config.tool_config import RVDroidToolConfig
from rvdroid_tool.constants import (
    RVDROID_TOOL_NAME, RVDROID_DESCRIPTION,
    DEFAULT_DEVICE_ID, DEFAULT_EXECUTION_TIMEOUT, DEFAULT_LLM_ENABLED
)
from rvdroid_tool.runner import RVDroidRunner


class RVDroidTool(AbstractTool):
    """
    RVDroid testing tool with optional LLM strategic guidance.
    
    ### Architectural Overview:
    RVDroid is a UIAutomator2-based Android testing tool that can optionally
    use LLM guidance for strategic testing decisions. Unlike action generation
    tools, it uses LLM for high-level strategic advice while maintaining its
    own core testing execution engine.
    
    ### System Integration:
    - Implements AbstractTool interface for rv-tools plugin system
    - Registers via Poetry plugins for automatic discovery
    - Integrates with rv-experiment for orchestrated execution
    - Uses rv-llm framework for LLM backend abstraction
    - Maintains independence from other testing tools
    
    ### Tool Execution Flow:
    1. Configuration resolved from variants or direct parameters
    2. RVDroidRunner initialized with complete configuration
    3. Optional LLM guidance service activated if enabled
    4. Core testing logic executed via existing RVDroid components
    5. Results collected and cleanup performed
    
    ### Guidance Integration:
    - LLM guidance provides strategic testing advice (not actions)
    - Guidance service integrates with RVDroid strategy and memory systems
    - Compact prompts optimized for strategic decision-making
    - Optional operation - tool works fully without LLM guidance
    """
    
    # Required by AbstractTool interface
    TOOL_SPEC = ToolSpec(
        name=RVDROID_TOOL_NAME,
        description=RVDROID_DESCRIPTION,
        url="https://github.com/rv-android/rvdroid-tool",
        version="1.0.0",
        process_pattern="rvdroid_tool"
    )

    def __init__(self):
        """
        Initialize RVDroid tool with UIAutomator2 and optional LLM capabilities.
        
        ### Initialization Strategy:
        - Inherits from AbstractTool for consistent platform behavior
        - Sets up component-specific logging infrastructure
        - Prepares for configuration-based setup via configure() method
        - Initializes without external dependencies for flexibility
        """
        # Initialize base class with tool specification
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern
        )
        
        # Initialize component logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid_tool.tools.tool",
            {CONTEXT_COMPONENT: "RVDroidTool"}
        )
        
        # Configuration will be set through configure() method
        self._tool_config: Optional[RVDroidToolConfig] = None
        
        # Tool execution components (initialized on configure)
        self._runner: Optional[RVDroidRunner] = None
        
        self.logger.info("RVDroid tool initialized")

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        """
        Get tool specification for plugin registration.
        
        Returns:
            ToolSpec instance with RVDroid metadata
        """
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available RVDroid variants with testing and LLM configurations.
        
        ### RVDroid Variants Overview:
        RVDroid variants support both traditional UIAutomator2 testing and
        LLM-guided strategic testing. Each variant provides complete configuration
        for testing approach, device targeting, and optional LLM integration.
        
        ### Variant Categories:
        - default: Traditional UIAutomator2 testing without LLM guidance
        - guidance_gemma: LLM strategic guidance using Ollama Gemma model
        - guidance_llama: LLM strategic guidance using Ollama Llama model
        - guidance_vision: LLM guidance with vision capabilities for UI analysis
        
        ### Configuration Strategy:
        - Each variant includes complete tool configuration
        - LLM variants include backend and prompt strategy configuration
        - Device and timeout settings optimized for testing scenarios
        - Guidance-specific parameters for strategic decision-making
        
        Returns:
            Dictionary mapping variant names to configuration parameters
        """
        return {
            "default": {
                "llm_enabled": DEFAULT_LLM_ENABLED,
                "device_id": DEFAULT_DEVICE_ID,
                "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
                "preferred_strategy": "adaptive"
            },
            "guidance_gemma": {
                "llm_enabled": True,
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.GEMMA,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 400,  # Compact for guidance
                "vision": True,
                "prompt_strategy": PromptStrategyType.SINGLE,  # Will use guidance strategy
                "device_id": DEFAULT_DEVICE_ID,
                "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
                "preferred_strategy": "llm_guided"
            },
            "guidance_llama": {
                "llm_enabled": True,
                "llm_type": LLMType.OLLAMA,
                "llm_model": "llama3.1:8b",
                "temperature": 0.1,
                "top_p": 0.95,
                "max_tokens": 600,  # Slightly larger for Llama
                "vision": False,
                "prompt_strategy": PromptStrategyType.SINGLE,  # Will use guidance strategy
                "device_id": DEFAULT_DEVICE_ID,
                "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
                "preferred_strategy": "llm_guided"
            },
            "guidance_vision": {
                "llm_enabled": True,
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.GEMMA,
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 500,
                "vision": True,
                "prompt_strategy": PromptStrategyType.SINGLE,  # Will use guidance strategy
                "device_id": DEFAULT_DEVICE_ID,
                "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
                "preferred_strategy": "visual_guided"
            }
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure RVDroid tool with resolved variant parameters.
        
        ### Configuration Architecture:
        This method handles both typed RVDroidToolConfig instances and
        dictionary-based configurations from variant resolution, providing
        flexibility for different configuration sources while maintaining
        type safety and validation.
        
        ### Configuration Processing:
        - Accepts both direct RVDroidToolConfig instances and variant dictionaries
        - Validates configuration completeness and consistency
        - Initializes LLM configuration when guidance is enabled
        - Prepares tool for execution with validated parameters
        
        Args:
            config: Either RVDroidToolConfig instance or configuration dictionary
            
        Raises:
            ConfigurationError: If configuration is invalid or incomplete
        """
        if isinstance(config, RVDroidToolConfig):
            # Direct typed configuration
            self._tool_config = config
        elif isinstance(config, dict):
            # Create typed configuration from variant dictionary
            try:
                self._tool_config = RVDroidToolConfig.create_from_variant(config)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to create RVDroidToolConfig from variant: {e}"
                )
        else:
            raise ConfigurationError(
                f"Invalid configuration type: {type(config)}. "
                f"Expected RVDroidToolConfig or Dict[str, Any]"
            )
        
        # Validate configuration
        is_valid, error_msg = self._tool_config.validate()
        if not is_valid:
            raise ConfigurationError(f"Invalid RVDroid configuration: {error_msg}")
        
        # Log configuration details
        self.logger.info(
            f"Configured RVDroid tool - LLM Enabled: {self._tool_config.llm_enabled}, "
            f"Device: {self._tool_config.device_id}, "
            f"Timeout: {self._tool_config.execution_timeout}"
        )
        
        if self._tool_config.llm_enabled:
            self.logger.info(
                f"LLM Configuration - Type: {self._tool_config.llm_config.llm_type}, "
                f"Model: {self._tool_config.llm_config.model}, "
                f"Strategy: {self._tool_config.prompt_config.strategy_type}"
            )

    @classmethod
    def create_tool_config(
        cls,
        variant_config: Dict[str, Any],
        override_params: Optional[Dict[str, Any]] = None
    ) -> RVDroidToolConfig:
        """
        Create typed RVDroidToolConfig from variant configuration.
        
        ### Factory Method Architecture:
        This class method provides clean typed configuration creation for RVDroid,
        enabling proper integration with the variant system while maintaining
        type safety and configuration validation.
        
        Args:
            variant_config: Base configuration from variant registry
            override_params: Parameter overrides from experiment configuration
            
        Returns:
            Configured RVDroidToolConfig instance
            
        Raises:
            ConfigurationError: If configuration creation fails
        """
        return RVDroidToolConfig.create_from_variant(variant_config, override_params)

    @ErrorHandler.handle_errors(
        component="RVDroidTool",
        operation="execute_tool_specific_logic"
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute RVDroid tool with UIAutomator2 and optional LLM guidance.
        
        ### Execution Architecture:
        - Follows AbstractTool interface contract for consistent platform behavior
        - Initializes and manages RVDroidRunner for core testing execution
        - Coordinates LLM guidance integration when enabled
        - Handles tool lifecycle including initialization, execution, and cleanup
        
        ### Execution Flow:
        1. Validate tool configuration and prerequisites
        2. Initialize RVDroidRunner with complete configuration
        3. Set up component systems (memory, strategy, guidance)
        4. Execute core RVDroid testing logic
        5. Collect results and perform cleanup
        
        ### Integration Strategy:
        - Uses existing RVDroidRunner as core execution engine
        - Integrates guidance service when LLM is enabled
        - Maintains compatibility with existing RVDroid components
        - Provides structured error handling and resource management
        
        Args:
            task: Task configuration with execution parameters
            app: Target application information
            
        Raises:
            RVAndroidToolError: If tool execution fails
            ConfigurationError: If tool is not properly configured
        """
        self.logger.info(f"Starting RVDroid execution for app: {app.package_name}")
        
        # Validate configuration before execution
        if not self._tool_config:
            raise RVAndroidToolError("Tool configuration required - call configure() first")
        
        try:
            # Initialize RVDroidRunner with configuration
            self._runner = RVDroidRunner(tool_config=self._tool_config)
            
            # Initialize runner components
            if not self._runner.initialize():
                raise RVAndroidToolError("Failed to initialize RVDroidRunner")
            
            # Set up runner components (memory, strategy, guidance)
            if not self._runner.setup_components():
                raise RVAndroidToolError("Failed to set up RVDroidRunner components")
            
            # Execute core RVDroid testing logic
            results = self._runner.run(
                package_name=app.package_name,
                activity=task.config.get("activity"),  # Main activity from task config
                output_dir=task.results_dir
            )
            
            # Check execution results
            if isinstance(results, dict) and "error" in results:
                self.logger.error(f"RVDroid execution failed: {results['error']}")
                raise RVAndroidToolError(f"RVDroid execution failed: {results['error']}")
            
            # Log successful completion
            self.logger.info("RVDroid execution completed successfully")
            if isinstance(results, dict):
                self.logger.info(f"Execution results: {results}")
            
        except RVAndroidToolError:
            # Re-raise tool-specific errors
            raise
        except Exception as e:
            # Wrap unexpected errors
            self.logger.error(f"Unexpected error during RVDroid execution: {e}")
            raise RVAndroidToolError(f"RVDroid execution failed: {e}") from e
        finally:
            # Ensure cleanup is performed
            if self._runner:
                try:
                    self._runner.shutdown()
                except Exception as e:
                    self.logger.warning(f"Error during RVDroid cleanup: {e}")

    def get_supported_platforms(self) -> List[str]:
        """
        Get list of supported platforms for RVDroid.
        
        Returns:
            List of supported platform identifiers
        """
        return ["android"]

    def get_configuration_info(self) -> Dict[str, Any]:
        """
        Get current tool configuration information.
        
        Returns:
            Dictionary containing configuration details
        """
        if not self._tool_config:
            return {"configured": False}
        
        config_info = {
            "configured": True,
            "llm_enabled": self._tool_config.llm_enabled,
            "device_id": self._tool_config.device_id,
            "execution_timeout": self._tool_config.execution_timeout,
            "preferred_strategy": self._tool_config.preferred_strategy
        }
        
        if self._tool_config.llm_enabled:
            config_info.update({
                "llm_type": self._tool_config.llm_config.llm_type,
                "llm_model": self._tool_config.llm_config.model,
                "prompt_strategy": self._tool_config.prompt_config.strategy_type,
                "vision_enabled": getattr(self._tool_config.llm_config, 'vision', False)
            })
        
        return config_info