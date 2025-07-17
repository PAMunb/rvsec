"""
RVAndroid Tool Implementation with Unified Configuration Support

This module provides AI-guided exploration of Android applications using large
language models for intelligent action generation and monitored operations detection,
with unified configuration management for consistent tool behavior.

### Architectural Overview:
This tool provides AI-guided exploration of Android applications using unified
configuration that combines LLM backend settings with prompt strategy configuration,
ensuring consistent behavior across all tool components.

### Key Components:
- LLMActionService: Processes application states and generates actions
- Server: REST API for DroidBot integration
- RvAndroidToolConfig: Unified configuration management
- DroidBot Integration: Executes generated actions on Android emulator

### Execution Flow:
1. Configure with unified RvAndroidToolConfig
2. Initialize LLMActionService with unified configuration
3. Start server for DroidBot communication
4. Execute DroidBot with rvandroid policy
5. Process states and generate actions through LLM
6. Clean up resources and stop server

### Configuration Support:
- Unified Configuration: Single configuration object for all components
- Multiple LLM backends (Ollama, OpenAI, etc.)
- Configurable prompt strategies (BATCH_ACTION, STANDARD)
- Parser and visitor type selection through composition
- Multi-instance support with independent configurations
"""

import os
from typing import Dict, Any, Optional

from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.domain.task import Task
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.error.exceptions import RVAndroidToolError, ConfigurationError
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rvandroid_tool.constants import DEFAULT_SERVER_PORT
from rvandroid_tool.config.tool_config import RvAndroidToolConfig


class RVAndroidTool(AbstractTool):
    """
    RVAndroid tool implementation with unified configuration support.
    
    ### Architectural Overview:
    This tool provides AI-guided exploration of Android applications using unified
    configuration that combines LLM backend settings with prompt strategy configuration,
    ensuring consistent behavior across all tool components.
    
    ### Key Components:
    - LLMActionService: Processes application states and generates actions
    - Server: REST API for DroidBot integration
    - RvAndroidToolConfig: Unified configuration management
    - DroidBot Integration: Executes generated actions on Android emulator
    
    ### Execution Flow:
    1. Configure with unified RvAndroidToolConfig
    2. Initialize LLMActionService with unified configuration
    3. Start server for DroidBot communication
    4. Execute DroidBot with rvandroid policy
    5. Process states and generate actions through LLM
    6. Clean up resources and stop server
    
    ### Configuration Support:
    - Unified Configuration: Single configuration object for all components
    - Multiple LLM backends (Ollama, OpenAI, etc.)
    - Configurable prompt strategies (BATCH_ACTION, STANDARD)
    - Parser and visitor type selection through composition
    - Multi-instance support with independent configurations
    """

    def __init__(self):
        """Initialize RVAndroid tool with unified configuration support."""
        super().__init__()
        
        # Initialize logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rvandroid_tool.tools.rvandroid.tool",
            {CONTEXT_COMPONENT: "RVAndroidTool"}
        )

        # Tool configuration (will be populated via configure())
        self.config = {
            "server_port": DEFAULT_SERVER_PORT,
            "debug_mode": False,
            "timeout": 600
        }

        # Unified configuration (injected via configure())
        self._tool_config: Optional[RvAndroidToolConfig] = None
        self._llm_config = None
        self._prompt_config = None

        self.logger.info("RVAndroid tool initialized successfully")

    @ErrorHandler.handle_errors(
        component="RVAndroidTool",
        operation="configure"
    )
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure RVAndroid tool with unified configuration.
        
        This method configures the tool instance with unified configuration
        containing both LLM and prompt settings, ensuring consistent behavior
        across all tool components.
        
        ### Configuration Strategy:
        The method expects a unified RvAndroidToolConfig instance containing
        all necessary configuration for tool execution, eliminating the need
        for separate configuration parameters.
        
        ### Configuration Validation:
        - Validates presence of required configuration
        - Checks configuration consistency
        - Prepares tool for execution with validated settings
        
        Args:
            config: Configuration dictionary containing unified tool configuration
            
        Raises:
            ConfigurationError: If configuration is invalid or incomplete
        """
        if not config:
            return

        try:
            # Extract unified tool configuration
            if 'tool_config' in config:
                self._tool_config = config['tool_config']
                
                # Validate configuration
                if not isinstance(self._tool_config, RvAndroidToolConfig):
                    raise ConfigurationError("Invalid tool configuration type")
                
                # Store configuration components for easy access
                self._llm_config = self._tool_config.llm_config
                self._prompt_config = self._tool_config.prompt_config
                
                # Configure tool-specific settings
                self.config.update({
                    'server_port': self._tool_config.server_port,
                    'debug_mode': self._tool_config.debug_mode,
                    **self._tool_config.additional_params
                })
                
                # Validate server port against constants
                if self._tool_config.server_port < 1024 or self._tool_config.server_port > 65535:
                    raise ConfigurationError(f"Invalid server port: {self._tool_config.server_port}")
                
                self.logger.info(
                    f"RVAndroid tool configured with unified configuration - "
                    f"LLM: {self._llm_config.llm_type}:{self._llm_config.model}, "
                    f"Strategy: {self._prompt_config.strategy_type}, "
                    f"Parser: {self._prompt_config.parser_type}, "
                    f"Visitor: {self._prompt_config.visitor_type}, "
                    f"Server Port: {self._tool_config.server_port}"
                )
                
            else:
                # Legacy configuration support (deprecated)
                self.logger.warning("Using legacy configuration format - consider upgrading to unified configuration")
                
                # Extract individual configuration components
                if 'llm_config' in config:
                    self._llm_config = config['llm_config']
                
                # Update basic configuration
                self.config.update({
                    'server_port': config.get('server_port', DEFAULT_SERVER_PORT),
                    'debug_mode': config.get('debug_mode', False),
                    'timeout': config.get('timeout', 600)
                })
                
                self.logger.info(
                    f"RVAndroid tool configured with legacy configuration - "
                    f"LLM: {self._llm_config.llm_type if self._llm_config else 'None'}, "
                    f"Server Port: {self.config['server_port']}"
                )

        except Exception as e:
            self.logger.error(f"Configuration failed: {e}")
            raise ConfigurationError(f"Tool configuration failed: {e}")

    @ErrorHandler.handle_errors(
        component="RVAndroidTool",
        operation="execute"
    )
    def execute(self, app: App, task: Task) -> Any:
        """
        Execute RVAndroid tool with unified configuration.
        
        This method executes the tool with unified configuration, ensuring
        consistent behavior across all components.
        
        ### Execution Strategy:
        1. Validate unified configuration
        2. Initialize LLMActionService with unified configuration
        3. Start server for DroidBot communication
        4. Execute DroidBot with rvandroid policy
        5. Process states and generate actions through LLM
        6. Clean up resources and stop server
        
        Args:
            app: Application instance to test
            task: Task instance with execution parameters
            
        Returns:
            Execution results
            
        Raises:
            RVAndroidToolError: If execution fails
        """
        if not self._tool_config:
            raise RVAndroidToolError("Tool not configured - call configure() first")
        
        self.logger.info(f"Executing RVAndroid tool for app: {app.package_name}")
        
        try:
            # Initialize LLMActionService with unified configuration
            from rvandroid_tool.llm.service.action_service import LLMActionService
            
            service = LLMActionService(
                static_data=app.static_data,
                tool_config=self._tool_config,
                app_package=app.package_name
            )
            
            # Execute tool with unified configuration
            results = self._execute_with_service(app, task, service)
            
            # Cleanup service
            service.cleanup()
            
            self.logger.info(f"RVAndroid tool execution completed for app: {app.package_name}")
            return results
            
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            raise RVAndroidToolError(f"Tool execution failed: {e}")

    def _execute_with_service(self, app: App, task: Task, service) -> Any:
        """
        Execute tool with LLM service.
        
        Args:
            app: Application instance
            task: Task instance
            service: LLMActionService instance
            
        Returns:
            Execution results
        """
        # Implementation details would go here
        # This is a placeholder for the actual execution logic
        
        self.logger.info(f"Executing tool with service configuration:")
        self.logger.info(f"  - LLM Backend: {self._llm_config.llm_type}:{self._llm_config.model}")
        self.logger.info(f"  - Prompt Strategy: {self._prompt_config.strategy_type}")
        self.logger.info(f"  - Parser: {self._prompt_config.parser_type}")
        self.logger.info(f"  - Visitor: {self._prompt_config.visitor_type}")
        self.logger.info(f"  - Server Port: {self._tool_config.server_port}")
        
        # Return placeholder results
        return {
            "status": "completed",
            "app_package": app.package_name,
            "configuration": {
                "llm_backend": f"{self._llm_config.llm_type}:{self._llm_config.model}",
                "prompt_strategy": self._prompt_config.strategy_type,
                "parser_type": self._prompt_config.parser_type,
                "visitor_type": self._prompt_config.visitor_type,
                "server_port": self._tool_config.server_port
            }
        }

    @ErrorHandler.handle_errors(
        component="RVAndroidTool",
        operation="get_configuration_info"
    )
    def get_configuration_info(self) -> Dict[str, Any]:
        """
        Get current tool configuration information.
        
        Returns:
            Dictionary containing configuration details
        """
        if not self._tool_config:
            return {"status": "not_configured"}
        
        return {
            "status": "configured",
            "llm_backend": f"{self._llm_config.llm_type}:{self._llm_config.model}",
            "prompt_strategy": self._prompt_config.strategy_type,
            "parser_type": self._prompt_config.parser_type,
            "visitor_type": self._prompt_config.visitor_type,
            "server_port": self._tool_config.server_port,
            "debug_mode": self._tool_config.debug_mode
        }

    @ErrorHandler.handle_errors(
        component="RVAndroidTool",
        operation="validate_configuration"
    )
    def validate_configuration(self) -> bool:
        """
        Validate current tool configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not self._tool_config:
            raise ConfigurationError("Tool not configured")
        
        # Validate unified configuration
        is_valid, error = self._tool_config.validate()
        if not is_valid:
            raise ConfigurationError(f"Configuration validation failed: {error}")
        
        return True

    def get_tool_spec(self) -> ToolSpec:
        """Get tool specification for registry."""
        return ToolSpec(
            name="rvandroid",
            description="AI-driven Android application testing tool",
            version="1.0.0",
            supported_variants=["batch_action", "standard", "detailed", "basic"],
            configuration_schema={
                "tool_config": "RvAndroidToolConfig",
                "server_port": "int",
                "debug_mode": "bool"
            }
        )