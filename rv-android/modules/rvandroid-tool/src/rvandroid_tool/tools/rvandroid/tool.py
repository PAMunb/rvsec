"""
RVAndroid tool implementation for AI-driven monitored operations testing.

This module provides integration with the RVAndroid testing framework,
enabling AI-guided exploration of Android applications for monitored operations detection.
"""

import os
from typing import Dict, Any, List

from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.domain.task import Task
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec


class RVAndroidTool(AbstractTool):
    """
    RVAndroid AI-driven testing tool for monitored operations testing.

    ### Architectural Decisions:
    - Inherits directly from AbstractTool for simplified architecture
    - Implements AI-guided exploration strategies using large language models
    - Provides comprehensive server-based architecture for real-time action generation
    - Uses DroidBot framework integration for efficient execution and trace generation
    - Supports configurable LLM backends and prompt strategies for adaptive testing
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as an AI-guided testing tool for monitored operations using language models
    - Provides intelligent action generation based on screen analysis and application context
    - Enables adaptive exploration that learns from application behavior and UI patterns
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates natural language understanding for complex UI interaction scenarios

    ### Key Features:
    - Large language model integration for intelligent action generation
    - Natural language understanding for UI content analysis and interaction planning
    - Adaptive exploration strategies that learn from application behavior patterns
    - Context-aware navigation and goal-oriented testing scenarios
    - Advanced prompt engineering for optimal testing coverage and efficiency
    - Real-time decision making based on screen analysis and application state

    ### Tool Variants:
    RVAndroid supports multiple dimensions of configuration as variants:
    - LLM Backend: ollama, openai, huggingface
    - LLM Model: llama3.2:3b, gpt-4, etc.
    - Prompt Strategy: standard, batch_action, context_aware
    - Visitor Type: default, enhanced, basic
    - Screen Parser: droidbot, uiautomator
    """

    # Simplified tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="rvandroid",
        description="RVAndroid AI-driven testing tool using large language models for intelligent exploration",
        url="https://github.com/pedro-abundio-wang/rvandroid",
        version="1.0.0",
        process_pattern="rvandroid"
    )

    def __init__(self, name: str = None, description: str = None, process_pattern: str = None):
        """
        Initialize the RVAndroid tool with default configuration.
        """
        super().__init__(
            name=name or self.TOOL_SPEC.name,
            description=description or self.TOOL_SPEC.description,
            process_pattern=process_pattern or self.TOOL_SPEC.process_pattern
        )

        # Initialize logging and error handling
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_tools.builtin.rvandroid",
            {CONTEXT_COMPONENT: "RVAndroidTool"}
        )

        # Default tool configuration
        self.config = {
            "server_url": "http://127.0.0.1:5000",
            "server_port": 5000,
            "policy": "rvandroid",
            "timeout": 600,  # 10 minutes
            "device_id": "emulator-5554",
            "is_emulator": True,
            "llm_backend": "ollama",
            "llm_model": "llama3.2:3b",
            "llm_base_url": "http://localhost:11434",
            "llm_temperature": 0.2,
            "llm_max_tokens": 500,
            "prompt_strategy": "standard",
            "screen_parser": "droidbot",
            "visitor_type": "default",
            "enable_learning": True,
            "memory_enabled": True,
            "debug_mode": False,
            "trace_level": "detailed",
            "server_startup_timeout": 30,
            "server_shutdown_timeout": 10
        }

        self.logger.info("RVAndroid tool initialized successfully")

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure RVAndroid-specific parameters and validate settings.

        Supported configuration options:
        - llm_backend: LLM backend (ollama, openai, huggingface)
        - llm_model: LLM model name
        - llm_temperature: Temperature for LLM responses
        - prompt_strategy: Prompt strategy (standard, batch_action, context_aware)
        - visitor_type: Visitor type (default, enhanced, basic)
        - screen_parser: Screen parser (droidbot, uiautomator)
        - server_port: Server port for RVAndroid service
        - timeout: Execution timeout in seconds
        - device_id: Target device identifier

        Args:
            config: Configuration dictionary with tool-specific parameters
        """
        if not config:
            return

        self.logger.debug("Configuring RVAndroid-specific parameters")

        try:
            # Server configuration
            if 'server_url' in config:
                server_url = config['server_url']
                if not isinstance(server_url, str) or not server_url.strip():
                    self.logger.warning("server_url must be a non-empty string")
                else:
                    self.config['server_url'] = server_url.strip()

            if 'server_port' in config:
                try:
                    port = int(config['server_port'])
                    if 1024 <= port <= 65535:
                        self.config['server_port'] = port
                        self.logger.debug(f"Set server port to: {port}")
                    else:
                        self.logger.warning("server_port must be between 1024 and 65535")
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid server_port value: {config['server_port']}")

            # Policy configuration
            if 'policy' in config:
                policy = config['policy']
                valid_policies = ['rvandroid', 'dfs_greedy', 'bfs_greedy', 'random']
                if policy in valid_policies:
                    self.config['policy'] = policy
                    self.logger.debug(f"Set policy to: {policy}")
                else:
                    self.logger.warning(f"Invalid policy '{policy}'. Valid options: {valid_policies}")

            # Timeout configuration
            if 'timeout' in config:
                try:
                    timeout = int(config['timeout'])
                    if timeout > 0:
                        self.config['timeout'] = timeout
                        self.logger.debug(f"Set timeout to: {timeout}s")
                    else:
                        self.logger.warning("timeout must be positive")
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid timeout value: {config['timeout']}")

            # Device configuration
            if 'device_id' in config:
                self.config['device_id'] = str(config['device_id'])
                self.logger.debug(f"Set device_id to: {config['device_id']}")

            # LLM configuration
            if 'llm_backend' in config:
                backend = config['llm_backend']
                valid_backends = ['ollama', 'openai', 'huggingface']
                if backend in valid_backends:
                    self.config['llm_backend'] = backend
                    self.logger.debug(f"Set LLM backend to: {backend}")
                else:
                    self.logger.warning(f"Invalid LLM backend '{backend}'. Valid options: {valid_backends}")

            if 'llm_model' in config:
                self.config['llm_model'] = str(config['llm_model'])
                self.logger.debug(f"Set LLM model to: {config['llm_model']}")

            if 'llm_base_url' in config:
                self.config['llm_base_url'] = str(config['llm_base_url'])
                self.logger.debug(f"Set LLM base URL to: {config['llm_base_url']}")

            if 'llm_temperature' in config:
                try:
                    temp = float(config['llm_temperature'])
                    if 0.0 <= temp <= 2.0:
                        self.config['llm_temperature'] = temp
                        self.logger.debug(f"Set LLM temperature to: {temp}")
                    else:
                        self.logger.warning("llm_temperature must be between 0.0 and 2.0")
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid llm_temperature value: {config['llm_temperature']}")

            if 'llm_max_tokens' in config:
                try:
                    tokens = int(config['llm_max_tokens'])
                    if tokens > 0:
                        self.config['llm_max_tokens'] = tokens
                        self.logger.debug(f"Set LLM max tokens to: {tokens}")
                    else:
                        self.logger.warning("llm_max_tokens must be positive")
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid llm_max_tokens value: {config['llm_max_tokens']}")

            # Strategy configuration
            if 'prompt_strategy' in config:
                strategy = config['prompt_strategy']
                valid_strategies = ['standard', 'batch_action', 'context_aware']
                if strategy in valid_strategies:
                    self.config['prompt_strategy'] = strategy
                    self.logger.debug(f"Set prompt strategy to: {strategy}")
                else:
                    self.logger.warning(f"Invalid prompt strategy '{strategy}'. Valid options: {valid_strategies}")

            if 'screen_parser' in config:
                parser = config['screen_parser']
                valid_parsers = ['droidbot', 'uiautomator']
                if parser in valid_parsers:
                    self.config['screen_parser'] = parser
                    self.logger.debug(f"Set screen parser to: {parser}")
                else:
                    self.logger.warning(f"Invalid screen parser '{parser}'. Valid options: {valid_parsers}")

            if 'visitor_type' in config:
                visitor = config['visitor_type']
                valid_visitors = ['default', 'enhanced', 'basic']
                if visitor in valid_visitors:
                    self.config['visitor_type'] = visitor
                    self.logger.debug(f"Set visitor type to: {visitor}")
                else:
                    self.logger.warning(f"Invalid visitor type '{visitor}'. Valid options: {valid_visitors}")

            # Boolean flags
            boolean_flags = ['is_emulator', 'enable_learning', 'memory_enabled', 'debug_mode']
            for flag in boolean_flags:
                if flag in config:
                    self.config[flag] = bool(config[flag])
                    self.logger.debug(f"Set {flag} to: {self.config[flag]}")

            # Timeout configuration
            if 'server_startup_timeout' in config:
                try:
                    timeout = int(config['server_startup_timeout'])
                    if timeout > 0:
                        self.config['server_startup_timeout'] = timeout
                        self.logger.debug(f"Set server startup timeout to: {timeout}s")
                    else:
                        self.logger.warning("server_startup_timeout must be positive")
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid server_startup_timeout value: {config['server_startup_timeout']}")

            if 'server_shutdown_timeout' in config:
                try:
                    timeout = int(config['server_shutdown_timeout'])
                    if timeout > 0:
                        self.config['server_shutdown_timeout'] = timeout
                        self.logger.debug(f"Set server shutdown timeout to: {timeout}s")
                    else:
                        self.logger.warning("server_shutdown_timeout must be positive")
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid server_shutdown_timeout value: {config['server_shutdown_timeout']}")

        except Exception as e:
            self.logger.error(f"Error during RVAndroid configuration: {e}")

    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute RVAndroid testing with configured parameters using unified architecture.
        
        This method starts the RVAndroid server and executes AI-driven testing
        based on the configured LLM backend and parameters.
        
        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        self.logger.info(f"Executing RVAndroid tool for {app.package_name}")
        self.logger.debug(f"LLM Backend: {self.config['llm_backend']}")
        self.logger.debug(f"LLM Model: {self.config['llm_model']}")
        self.logger.debug(f"Prompt Strategy: {self.config['prompt_strategy']}")

        # Get timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', self.config['timeout'])
        
        self.logger.info(f"RVAndroid execution timeout: {timeout_in_seconds} seconds")

        # Create output directory for RVAndroid results
        output_dir = os.path.join(os.path.dirname(task.result.trace_file), "rvandroid_output")
        os.makedirs(output_dir, exist_ok=True)

        # Build RVAndroid command
        rvandroid_cmd = self._build_rvandroid_command(app, output_dir, timeout_in_seconds)
        
        # Build command string for logging
        cmd_str = f"{rvandroid_cmd.command} {' '.join(rvandroid_cmd.args)}"
        self.logger.debug(f"RVAndroid command: {cmd_str}")

        # Execute RVAndroid testing with centralized error handling
        self.logger.info(f"Starting RVAndroid execution for {app.package_name}")
        
        with open(task.result.trace_file, 'wb') as trace_file:
            # Use centralized command execution with error handling
            result = self._execute_and_check_command(rvandroid_cmd, stdout=trace_file)
            
            # Append success information to trace file
            success_info = f"\n--- RVAndroid Execution Completed ---\n"
            success_info += f"LLM Backend: {self.config['llm_backend']}\n"
            success_info += f"LLM Model: {self.config['llm_model']}\n"
            success_info += f"Prompt Strategy: {self.config['prompt_strategy']}\n"
            success_info += f"Visitor Type: {self.config['visitor_type']}\n"
            success_info += f"Output directory: {output_dir}\n"
            success_info += f"Command: {cmd_str}\n"
            trace_file.write(success_info.encode('utf-8'))
        
        self.logger.info("RVAndroid execution completed successfully")

    def _build_rvandroid_command(self, app: App, output_dir: str, timeout_seconds: int) -> Command:
        """
        Build the RVAndroid command with configured parameters.
        
        Args:
            app: Application under test
            output_dir: Output directory for RVAndroid results
            timeout_seconds: Command execution timeout
            
        Returns:
            Configured Command object for RVAndroid execution
        """
        # Start building command arguments
        cmd_args = [
            "-a", app.apk_path,
            "-o", output_dir,
            "-policy", self.config["policy"],
            "-timeout", str(self.config["timeout"]),
            "-device", self.config["device_id"],
            "-llm_backend", self.config["llm_backend"],
            "-llm_model", self.config["llm_model"],
            "-prompt_strategy", self.config["prompt_strategy"],
            "-visitor_type", self.config["visitor_type"],
            "-screen_parser", self.config["screen_parser"]
        ]

        # Add LLM configuration
        if self.config["llm_base_url"]:
            cmd_args.extend(["-llm_base_url", self.config["llm_base_url"]])
            
        cmd_args.extend(["-llm_temperature", str(self.config["llm_temperature"])])
        cmd_args.extend(["-llm_max_tokens", str(self.config["llm_max_tokens"])])

        # Add server configuration
        cmd_args.extend(["-server_port", str(self.config["server_port"])])

        # Add boolean flags
        if self.config["is_emulator"]:
            cmd_args.append("-is_emulator")
            
        if self.config["enable_learning"]:
            cmd_args.append("-enable_learning")
            
        if self.config["memory_enabled"]:
            cmd_args.append("-memory_enabled")
            
        if self.config["debug_mode"]:
            cmd_args.append("-debug")

        return Command("rvandroid_server", cmd_args, timeout_seconds)

    def get_available_backends(self) -> List[str]:
        """Get list of available LLM backends."""
        return ['ollama', 'openai', 'huggingface']

    def get_available_strategies(self) -> List[str]:
        """Get list of available prompt strategies."""
        return ['standard', 'batch_action', 'context_aware']

    def get_available_visitors(self) -> List[str]:
        """Get list of available visitor types."""
        return ['default', 'enhanced', 'basic']

    def get_tool_info(self) -> dict:
        """
        Get comprehensive RVAndroid tool information.
        
        Returns:
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "available_backends": self.get_available_backends(),
            "available_strategies": self.get_available_strategies(),
            "available_visitors": self.get_available_visitors(),
            "current_backend": self.config["llm_backend"],
            "current_model": self.config["llm_model"],
            "current_strategy": self.config["prompt_strategy"],
            "current_visitor": self.config["visitor_type"],
            "version": self.TOOL_SPEC.version,
            "url": self.TOOL_SPEC.url
        })
        return info


# Função para registrar variantes do RVAndroid
def register_rvandroid_variants(registry):
    """
    Register RVAndroid variants in the tool registry.
    
    Args:
        registry: ToolRegistry instance
    """
    # Register LLM backend variants
    backend_variants = {
        "ollama": {"llm_backend": "ollama"},
        "openai": {"llm_backend": "openai"},
        "huggingface": {"llm_backend": "huggingface"}
    }
    
    for variant_name, config in backend_variants.items():
        registry.register_variant("rvandroid", variant_name, config)
    
    # Register model-specific variants
    model_variants = {
        "llama": {"llm_backend": "ollama", "llm_model": "llama3.2:3b"},
        "gpt4": {"llm_backend": "openai", "llm_model": "gpt-4"},
        "codellama": {"llm_backend": "ollama", "llm_model": "codellama:7b"}
    }
    
    for variant_name, config in model_variants.items():
        registry.register_variant("rvandroid", variant_name, config)
    
    # Register strategy variants
    strategy_variants = {
        "standard": {"prompt_strategy": "standard"},
        "batch": {"prompt_strategy": "batch_action"},
        "context": {"prompt_strategy": "context_aware"}
    }
    
    for variant_name, config in strategy_variants.items():
        registry.register_variant("rvandroid", variant_name, config)
    
    # Register combined variants
    combined_variants = {
        "llama_batch": {"llm_backend": "ollama", "llm_model": "llama3.2:3b", "prompt_strategy": "batch_action"},
        "gpt4_context": {"llm_backend": "openai", "llm_model": "gpt-4", "prompt_strategy": "context_aware"},
        "ollama_standard": {"llm_backend": "ollama", "prompt_strategy": "standard", "visitor_type": "enhanced"}
    }
    
    for variant_name, config in combined_variants.items():
        registry.register_variant("rvandroid", variant_name, config)