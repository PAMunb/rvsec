# modules/rvandroid-tool/src/rvandroid_tool/tools/rvandroid/tool.py
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVAndroidToolError
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_llm import OllamaLLM, FrontierModel
from rv_llm.llm.constants import ContextMode
from rvandroid_tool.llm.service.action_service import LLMActionService
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.commands.command import Command
from typing import Dict, List, Any, Optional, Tuple
import os
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rvandroid_tool.constants import RVANDROID_TOOL_NAME, RVANDROID_DESCRIPTION
from rvandroid_tool.constants import DEFAULT_SERVER_PORT
from rvandroid_tool.server.lifecycle import ServerLifecycleManager

class RVAndroidTool(AbstractTool):
    """
    LLM-based Android testing tool with DroidBot integration for monitored operations testing.
    
    ### Architectural Role:
    - Implements AbstractTool interface for seamless platform integration
    - Coordinates LLM service, HTTP server, and DroidBot policy execution
    - Manages application state analysis and action generation pipeline
    - Provides configurable LLM backends and prompt strategies
    
    ### System Integration:
    - Registered via rv-experiment module respecting module hierarchy
    - Uses rv-android-core error handling and logging infrastructure
    - Integrates with rv-llm for language model backends
    - Connects with rv-screen-parser for UI state analysis
    
    ### Tool Execution Flow:
    1. Initialize LLM service with configured backend and strategy
    2. Start HTTP server for DroidBot communication
    3. Launch DroidBot with RVAndroid policy pointing to server
    4. Process state requests and generate testing actions via LLM
    5. Handle server lifecycle and cleanup on completion
    """
    
    # Required by AbstractTool interface
    TOOL_SPEC = ToolSpec(
        name=RVANDROID_TOOL_NAME,
        description=RVANDROID_DESCRIPTION,
        url="https://github.com/rv-android/rvandroid-tool",
        version="1.0.0",
        process_pattern="rvandroid_tool"
    )

    def __init__(self):
        """
        Initialize RVAndroid tool with LLM-based testing capabilities.
        
        ### Initialization Strategy:
        - Inherits from AbstractTool for consistent tool behavior
        - Sets up logging with component-specific context
        - Prepares for configuration-based LLM and server setup
        """
        # Initialize base class with tool spec parameters
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern
        )
        
        # Initialize component logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvandroid_tool.tools.rvandroid",
            {CONTEXT_COMPONENT: "RVAndroidTool"}
        )
        
        # Configuration will be set through configure() method
        self._tool_config: Optional[RvAndroidToolConfig] = None
        self._server_port = DEFAULT_SERVER_PORT
        self._debug_mode = False
        
        self.logger.info("RVAndroid tool initialized")

    @classmethod
    def get_tool_spec(cls):
        """
        Get tool specification for registration.
        
        Returns:
            ToolSpec instance with tool metadata
        """
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available RVAndroid variants with LLM and prompt strategy configurations.
        
        ### RVAndroid Variants Overview:
        Each variant represents a complete configuration for LLM backend, prompt strategy,
        and tool-specific parameters optimized for different testing scenarios.
        
        ### Variant Categories:
        - default: Balanced configuration for general-purpose testing
        - llama_batch_detailed: LLaMA model with batch action strategy and detailed analysis
        - gpt4_standard_basic: GPT-4 model with single action strategy and basic configuration
        - ollama_standard_detailed: Ollama backend with single action strategy and detailed visitor
        - vision: Optimized vision strategy with coordinate support and compact prompts
        
        Returns:
            Dictionary mapping variant names to RVAndroid configuration parameters
        """
        from rv_llm.llm.constants import LLMType, PromptStrategyType
        from rv_screen_parser.constants import ScreenParserType, VisitorType
        
        variants = {
            "default": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.GEMMA,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 800,
                "vision": True,
                "prompt_strategy": PromptStrategyType.SINGLE,
                "parser_type": ScreenParserType.DROIDBOT,
                "visitor_type": VisitorType.DETAILED,
                "server_port": DEFAULT_SERVER_PORT,
                "debug_mode": False
            },
            "claude": {
                "llm_type": LLMType.FRONTIER,
                "llm_model": FrontierModel.CLAUDE_SONNET,
                "temperature": 0.2,
                "top_p": 0.8,
                "max_tokens": 3000,
                "prompt_strategy": PromptStrategyType.SINGLE,
                "parser_type": ScreenParserType.DROIDBOT,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.RICH,
                "context_window_size": ContextMode.WINDOW_SIZE_DEFAULT,
                "context_compression": True,
                "debug_mode": False
            },
            "vision": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.GEMMA,
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 500,
                "vision": True,
                "prompt_strategy": PromptStrategyType.VISION,
                "parser_type": ScreenParserType.DROIDBOT,
                "visitor_type": VisitorType.DEFAULT,
                "server_port": DEFAULT_SERVER_PORT,
                "context_mode": ContextMode.STATELESS,
                "debug_mode": False
            },
            "vision_ctx": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.GEMMA,
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 500,
                "vision": True,
                "prompt_strategy": PromptStrategyType.VISION,
                "parser_type": ScreenParserType.DROIDBOT,
                "visitor_type": VisitorType.DEFAULT,
                "server_port": DEFAULT_SERVER_PORT,
                "context_mode": ContextMode.RICH,
                "context_window_size": ContextMode.WINDOW_SIZE_DEFAULT,
                "context_compression": True,
                "debug_mode": False
            }
        }
        
        
        return variants
        
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure RVAndroid tool with resolved variant parameters.
        
        ### Configuration Architecture:
        This method handles both typed RvAndroidToolConfig instances and
        dictionary-based configurations from variant resolution, providing
        flexibility for different configuration sources.
        
        Args:
            config: Either RvAndroidToolConfig instance or configuration dictionary
            
        Raises:
            ConfigurationError: If configuration is invalid or incomplete
        """
        from rv_android_core.util.error.exceptions import ConfigurationError
        
        if isinstance(config, RvAndroidToolConfig):
            # Direct typed configuration
            self._tool_config = config
        elif isinstance(config, dict):
            # Create typed configuration from dictionary
            try:
                self._tool_config = RvAndroidToolConfig.create_from_variant(config)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to create RvAndroidToolConfig from variant: {e}"
                )
        else:
            raise ConfigurationError(
                f"Invalid configuration type: {type(config)}. "
                f"Expected RvAndroidToolConfig or Dict[str, Any]"
            )
        
        # Extract tool-specific parameters
        self._server_port = self._tool_config.server_port
        self._debug_mode = self._tool_config.debug_mode
        
        # Validate configuration
        is_valid, error_msg = self._tool_config.validate()
        if not is_valid:
            raise ConfigurationError(f"Invalid RVAndroid configuration: {error_msg}")
        
        self.logger.info(
            f"Configured RVAndroid tool - LLM: {self._tool_config.llm_config.llm_type}, "
            f"Strategy: {self._tool_config.prompt_config.strategy_type}, "
            f"Port: {self._server_port}"
        )

    @classmethod
    def create_tool_config(
        cls,
        variant_config: Dict[str, Any],
        override_params: Dict[str, Any] = None
    ) -> RvAndroidToolConfig:
        """
        Create typed RvAndroidToolConfig from variant configuration.
        
        ### Factory Method Architecture:
        This class method provides clean typed configuration creation for RVAndroid tool,
        enabling proper integration with the variant system while maintaining type safety.
        
        Args:
            variant_config: Base configuration from variant registry
            override_params: Parameter overrides from experiment configuration
            
        Returns:
            Configured RvAndroidToolConfig instance
            
        Raises:
            ConfigurationError: If configuration creation fails
        """
        return RvAndroidToolConfig.create_from_variant(variant_config, override_params)

    @ErrorHandler.handle_errors(
        component="RVAndroidTool",
        operation="execute_tool_specific_logic"
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute RVAndroid tool with LLM-guided testing approach.
        
        ### Execution Architecture:
        - Follows AbstractTool interface contract for consistent behavior
        - Implements complete LLM + Server + DroidBot coordination
        - Manages server lifecycle with context manager pattern
        - Handles external navigation and system actions
        
        ### Key Components:
        - LLMActionService: Coordinates LLM-based action generation
        - ServerLifecycleManager: Manages HTTP server for DroidBot communication
        - DroidBot: Executes generated actions on target application
        
        Args:
            task: Task configuration with execution parameters
            app: Target application information
        """
        self.logger.info(f"Starting RVAndroid execution for app: {app.package_name}")
        
        # Validate configuration before execution
        if not self._tool_config:
            raise RVAndroidToolError("Tool configuration required - call configure() first")
        
        # Use dynamic server_port for parallel execution if available
        actual_port = self._server_port  # default
        
        if (hasattr(task.config.tool_config, 'additional_params') and 
            task.config.tool_config.additional_params and
            'server_port' in task.config.tool_config.additional_params):
            actual_port = task.config.tool_config.additional_params['server_port']
            self.logger.info(f"Using dynamic server port: {actual_port}")
        else:
            self.logger.info(f"Using default server port: {actual_port}")
        
        # LLMActionService initialization (preserved)
        service = LLMActionService(
            static_data=task.static_data,
            tool_config=self._tool_config,
            app_package=app.package_name
        )
        
        # Context Manager for robust server lifecycle
        with ServerLifecycleManager(service, actual_port) as server:
            # Build and execute DroidBot command following AbstractTool pattern
            command = self._build_droidbot_command(task, app, actual_port)
            self._execute_and_check_command(command)
        
        self.logger.info("RVAndroid execution completed")

    def _build_droidbot_command(self, task: Task, app: App, server_port: int) -> Command:
        """
        Build DroidBot command with RVAndroid policy configuration.
        
        ### Command Construction Strategy:
        - Uses task configuration for DroidBot parameters
        - Configures RVAndroid policy with server URL and LLM settings
        - Includes app-specific targeting and output directory setup
        - Passes screenshot flag based on LLM multimodal capabilities
        
        Args:
            task: Task execution configuration
            app: Target application details
            server_port: HTTP server port for communication
            
        Returns:
            Command object for DroidBot execution
        """
        cmd_args = [
            "run", "droidbot",
            "-a", str(app.path),
            "-policy", "rvandroid",
            "-o", os.path.join(task.results_dir, "rvandroid_output"),
            "-timeout", str(task.config.timeout),
            "--rvandroid_url", f"http://localhost:{server_port}/api/get_actions"
        ]
        
        # Add screenshot flag based on LLM multimodal capabilities
        if self._tool_config and hasattr(self._tool_config.llm_config, 'vision') and self._tool_config.llm_config.vision:
            cmd_args.extend(["--rvandroid_screenshots", "true"])
            self.logger.info("Enabling screenshots for multimodal LLM")
        else:
            cmd_args.extend(["--rvandroid_screenshots", "false"])
            self.logger.info("Disabling screenshots for text-only LLM")
        
        # Add dynamic device_serial for parallel execution
        device_serial = None
        
        # First check if device_serial is in additional_params (parallel execution)
        if (hasattr(task.config.tool_config, 'additional_params') and 
            task.config.tool_config.additional_params and
            'device_serial' in task.config.tool_config.additional_params):
            device_serial = task.config.tool_config.additional_params['device_serial']
        # Fallback to task.device_serial if available
        elif hasattr(task, 'device_serial') and task.device_serial:
            device_serial = task.device_serial
            
        if device_serial:
            cmd_args.extend(["-d", device_serial])
            self.logger.info(f"Using device serial: {device_serial}")
            
        return Command("poetry", cmd_args, task.config.timeout)
