"""
RVAndroid tool implementation for AI-driven monitored operations testing.

This module provides integration with the RVAndroid testing framework,
enabling AI-guided exploration of Android applications for monitored operations detection.
"""

import os
from typing import Dict, Any, List

from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_TOOL_NAME, CONTEXT_COMPONENT
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolCategory


class RVAndroidTool(ConfigurableTool):
    """
    RVAndroid AI-driven testing tool for monitored operations testing.

    ### Architectural Decisions:
    - Extends ConfigurableTool to leverage standardized configuration management
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
    - Generates detailed trace files for comprehensive result analysis and debugging

    ### Key Considerations:
    - Uses server-based architecture for real-time LLM communication and action generation
    - Implements configurable prompt strategies for different testing objectives and scenarios
    - Supports multiple LLM backends including Ollama, OpenAI, and Hugging Face models
    - Provides comprehensive state management for long-running exploration sessions
    - Handles both emulator and real device execution environments with adaptive strategies
    - Integrates with DroidBot framework for standardized execution and comprehensive tracing

    ### Integration Strategy:
    - Compatible with experiment task execution system for automated workflows
    - Supports configuration inheritance from experiment and variant specifications
    - Enables result collection and analysis through standardized trace file format
    - Provides clear extension points for custom prompt strategies and LLM configurations
    - Facilitates integration with coverage analysis and behavioral pattern recognition systems
    - Supports plugin-based architecture for external tool ecosystem integration

    ### Performance and Scalability:
    - Optimized for AI-driven interaction speed with configurable response timeouts
    - Supports configurable server startup and shutdown mechanisms
    - Enables parallel execution across multiple device instances and applications
    - Provides intelligent caching strategies to minimize LLM API calls
    - Scales effectively for large-scale experiment execution scenarios
    - Adaptable to different APK complexity and AI model capabilities

    ### AI-Driven Testing Features:
    - Large language model integration for intelligent action generation
    - Natural language understanding for UI content analysis and interaction planning
    - Adaptive exploration strategies that learn from application behavior patterns
    - Context-aware navigation and goal-oriented testing scenarios
    - Advanced prompt engineering for optimal testing coverage and efficiency
    - Real-time decision making based on screen analysis and application state
    """

    # RVAndroid tool specification with comprehensive metadata
    TOOL_SPEC = ToolSpec.create_external_spec(
        name="rvandroid",
        description="RVAndroid AI-driven testing tool using large language models for intelligent exploration",
        category=ToolCategory.AI_GUIDED,
        dependencies=["rv-android-core", "rv-screen-parser", "rv-llm", "rv-tools"],
        capabilities=[
            "ai_guided_testing",
            "llm_integration",
            "natural_language_understanding",
            "adaptive_exploration",
            "intelligent_action_generation",
            "context_aware_navigation",
            "real_time_decision_making",
            "server_based_architecture",
            "trace_generation",
            "monitored_operations_testing"
        ],
        author="RV-Android Team"
    )

    def __init__(self):
        """
        Initialize the RVAndroid tool with default configuration.
        
        Sets up tool metadata, default parameters, and establishes
        integration with rv-android-core and rv-tools infrastructure.
        """
        super().__init__(
            name=self.TOOL_SPEC.name,
            description=self.TOOL_SPEC.description,
            process_pattern="rvandroid"
        )

        # Initialize logging and error handling
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()

        # Default tool configuration
        self.default_config = {
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

        # Merge default configuration with current tool configuration
        self.tool_config = self.default_config.copy()

        self.logger.info("RVAndroid tool initialized successfully")

    def configure_tool_specific(self, config: Dict[str, Any]) -> None:
        """
        Configure RVAndroid-specific parameters and validate settings.

        Args:
            config: Configuration dictionary with tool-specific parameters

        Raises:
            ValueError: If configuration parameters are invalid
        """
        self.logger.debug("Configuring RVAndroid-specific parameters")

        try:
            # Server configuration
            if 'server_url' in config:
                server_url = config['server_url']
                if not isinstance(server_url, str) or not server_url.strip():
                    raise ValueError("server_url must be a non-empty string")
                self.tool_config['server_url'] = server_url.strip()

            if 'server_port' in config:
                port = config['server_port']
                if not isinstance(port, int) or not (1024 <= port <= 65535):
                    raise ValueError("server_port must be an integer between 1024 and 65535")
                self.tool_config['server_port'] = port

            # Policy configuration
            if 'policy' in config:
                policy = config['policy']
                valid_policies = ['rvandroid', 'dfs_greedy', 'bfs_greedy', 'random']
                if policy not in valid_policies:
                    raise ValueError(f"policy must be one of: {valid_policies}")
                self.tool_config['policy'] = policy

            # Timeout configuration
            if 'timeout' in config:
                timeout = config['timeout']
                if not isinstance(timeout, int) or timeout < 1:
                    raise ValueError("timeout must be a positive integer")
                self.tool_config['timeout'] = timeout

            # Device configuration
            if 'device_id' in config:
                self.tool_config['device_id'] = str(config['device_id'])

            # LLM configuration
            if 'llm_backend' in config:
                backend = config['llm_backend']
                valid_backends = ['ollama', 'openai', 'huggingface']
                if backend not in valid_backends:
                    raise ValueError(f"llm_backend must be one of: {valid_backends}")
                self.tool_config['llm_backend'] = backend

            if 'llm_model' in config:
                self.tool_config['llm_model'] = str(config['llm_model'])

            if 'llm_base_url' in config:
                self.tool_config['llm_base_url'] = str(config['llm_base_url'])

            if 'llm_temperature' in config:
                temp = config['llm_temperature']
                if not isinstance(temp, (int, float)) or not (0.0 <= temp <= 2.0):
                    raise ValueError("llm_temperature must be between 0.0 and 2.0")
                self.tool_config['llm_temperature'] = temp

            if 'llm_max_tokens' in config:
                tokens = config['llm_max_tokens']
                if not isinstance(tokens, int) or tokens < 1:
                    raise ValueError("llm_max_tokens must be a positive integer")
                self.tool_config['llm_max_tokens'] = tokens

            # Strategy configuration
            if 'prompt_strategy' in config:
                strategy = config['prompt_strategy']
                valid_strategies = ['standard', 'batch_action', 'context_aware']
                if strategy not in valid_strategies:
                    raise ValueError(f"prompt_strategy must be one of: {valid_strategies}")
                self.tool_config['prompt_strategy'] = strategy

            if 'screen_parser' in config:
                parser = config['screen_parser']
                valid_parsers = ['droidbot', 'uiautomator']
                if parser not in valid_parsers:
                    raise ValueError(f"screen_parser must be one of: {valid_parsers}")
                self.tool_config['screen_parser'] = parser

            if 'visitor_type' in config:
                visitor = config['visitor_type']
                valid_visitors = ['default', 'enhanced', 'basic']
                if visitor not in valid_visitors:
                    raise ValueError(f"visitor_type must be one of: {valid_visitors}")
                self.tool_config['visitor_type'] = visitor

            # Timeout configuration
            if 'server_startup_timeout' in config:
                timeout = config['server_startup_timeout']
                if not isinstance(timeout, int) or timeout < 1:
                    raise ValueError("server_startup_timeout must be a positive integer")
                self.tool_config['server_startup_timeout'] = timeout

            if 'server_shutdown_timeout' in config:
                timeout = config['server_shutdown_timeout']
                if not isinstance(timeout, int) or timeout < 1:
                    raise ValueError("server_shutdown_timeout must be a positive integer")
                self.tool_config['server_shutdown_timeout'] = timeout

            # Trace level configuration
            if 'trace_level' in config:
                level = config['trace_level']
                valid_levels = ['minimal', 'standard', 'detailed', 'comprehensive']
                if level not in valid_levels:
                    raise ValueError(f"trace_level must be one of: {valid_levels}")
                self.tool_config['trace_level'] = level

            # Boolean flags
            boolean_flags = [
                'is_emulator', 'enable_learning', 'memory_enabled', 'debug_mode'
            ]
            
            for flag in boolean_flags:
                if flag in config:
                    self.tool_config[flag] = bool(config[flag])

            self.logger.info("RVAndroid tool configuration completed successfully")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "configure_tool_specific",
                    "tool": "rvandroid",
                    "component": "RVAndroidTool"
                }
            )
            raise

    def execute_tool_specific_logic(self, task: Any, app: App) -> None:
        """
        Execute RVAndroid-specific testing logic with AI-guided exploration.
        
        This method implements the core RVAndroid execution workflow including
        server startup, LLM service initialization, DroidBot execution with
        RVAndroid policy, and comprehensive trace generation.
        
        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with path and metadata
        """
        try:
            self.logger.info(f"Executing RVAndroid tool for app: {app.name}")
            self.logger.debug(f"Server URL: {self.tool_config['server_url']}")
            self.logger.debug(f"LLM Backend: {self.tool_config['llm_backend']}")
            self.logger.debug(f"LLM Model: {self.tool_config['llm_model']}")
            self.logger.debug(f"Prompt Strategy: {self.tool_config['prompt_strategy']}")

            # Validate execution environment
            if not self.validate_execution_environment(app):
                raise RuntimeError("RVAndroid execution environment validation failed")

            # Get task configuration timeout
            task_config = {"timeout": getattr(task.config, 'timeout', self.tool_config['timeout'])}
            
            # Determine output file from task
            output_file = getattr(task.result, 'trace_file', None)
            if not output_file:
                raise ValueError("No output trace file specified in task result")

            # Start RVAndroid server and execute testing
            self._execute_with_server(task, app, output_file, task_config)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "execute_tool_specific_logic",
                    "app_name": app.name,
                    "tool": "rvandroid",
                    "component": "RVAndroidTool"
                }
            )
            raise

    def _execute_with_server(self, task: Any, app: App, output_file: str, task_config: Dict[str, Any]) -> None:
        """
        Execute RVAndroid testing with server startup and management.
        
        Args:
            task: Task instance with configuration and metadata
            app: Application under test
            output_file: Path to output trace file
            task_config: Task-specific configuration parameters
        """
        server = None
        try:
            # Import RVAndroid server (dynamically to avoid import issues)
            from rvandroid_tool.server import Server
            
            # Create and configure LLM service
            service = self._create_llm_service(task, app)
            
            # Create server instance
            server = Server(service, port=self.tool_config['server_port'])
            
            # Start server
            self.logger.info(f"Starting RVAndroid server on port {self.tool_config['server_port']}")
            if not server.start():
                raise RuntimeError("Failed to start RVAndroid server")
            
            self.logger.info("RVAndroid server started successfully")
            
            # Create and execute DroidBot command
            command = self.get_execution_command(app, output_file, task_config)
            
            self.logger.info(f"Starting RVAndroid execution with timeout: {task_config['timeout']} seconds")
            
            # Execute the command and capture output
            with open(output_file, 'wb') as trace_file:
                result = command.invoke(stdout=trace_file)
                
                # Process execution result
                execution_result = self.process_execution_result(result, app, output_file)
                
                # Log execution summary
                if execution_result.get('success', False):
                    self.logger.info(f"RVAndroid execution completed successfully for app: {app.name}")
                    self.logger.info(f"AI actions generated: {execution_result.get('ai_actions_generated', 0)}")
                    self.logger.info(f"Monitored operations detected: {execution_result.get('monitored_operations_detected', 0)}")
                else:
                    self.logger.warning(f"RVAndroid execution failed for app: {app.name}")
                    if execution_result.get('timeout_occurred', False):
                        self.logger.warning("Execution terminated due to timeout")
                    
                    error_details = execution_result.get('error_details', '')
                    if error_details:
                        self.logger.error(f"Error details: {error_details}")

        finally:
            # Cleanup server
            if server:
                self.logger.info("Stopping RVAndroid server")
                server.stop()

    def _create_llm_service(self, task: Any, app: App) -> Any:
        """
        Create and configure the LLM service for RVAndroid.
        
        Args:
            task: Task instance with configuration
            app: Application under test
            
        Returns:
            Configured LLM service instance
        """
        try:
            # Import required components dynamically
            from rvandroid.llm.service.action_service import LLMActionService
            from rv_llm.config.component_configurator import ComponentConfigurator
            from rv_llm.llm.constants import PromptStrategyType, ScreenParserType
            from rv_screen_parser.parser.screen.visitor.visitor_factory import VisitorFactory
            
            # Create component configurator
            configurator = ComponentConfigurator(task.static_data)
            
            # Configure LLM backend
            configurator.set_llm(
                llm_type=self.tool_config['llm_backend'],
                model=self.tool_config['llm_model'],
                base_url=self.tool_config['llm_base_url'],
                temperature=self.tool_config['llm_temperature'],
                max_tokens=self.tool_config['llm_max_tokens']
            )
            
            # Configure strategy and parser
            strategy_map = {
                'standard': PromptStrategyType.STANDARD,
                'batch_action': PromptStrategyType.BATCH_ACTION,
                'context_aware': PromptStrategyType.STANDARD  # Map to available strategy
            }
            configurator.set_strategy(strategy_map.get(self.tool_config['prompt_strategy'], PromptStrategyType.STANDARD))
            
            parser_map = {
                'droidbot': ScreenParserType.DROIDBOT,
                'uiautomator': ScreenParserType.UIAUTOMATOR
            }
            configurator.set_parser(parser_map.get(self.tool_config['screen_parser'], ScreenParserType.DROIDBOT))
            
            # Configure visitor
            configurator.set_visitor(VisitorFactory.DEFAULT)
            
            # Create LLM service
            service = LLMActionService(
                task.static_data,
                config=configurator,
                app_package=app.package_name
            )
            
            self.logger.info("LLM service created and configured successfully")
            return service
            
        except Exception as e:
            self.logger.error(f"Failed to create LLM service: {str(e)}")
            raise

    def build_command_args(self, app: App, output_file: str, task_config: Dict[str, Any]) -> List[str]:
        """
        Build command arguments for RVAndroid execution through DroidBot.

        Args:
            app: Application instance containing APK information
            output_file: Path to output trace file
            task_config: Task-specific configuration parameters

        Returns:
            List of command arguments for tool execution
        """
        try:
            self.logger.debug(f"Building RVAndroid command arguments for app: {app.name}")

            # Base DroidBot arguments with RVAndroid integration
            args = [
                "-d", self.tool_config['device_id'],
                "-a", app.path,
                "--rvandroid_url", self.tool_config['server_url'],
                "-policy", self.tool_config['policy']
            ]

            # Timeout configuration
            timeout_seconds = task_config.get('timeout', self.tool_config['timeout'])
            args.extend(["-timeout", str(timeout_seconds)])

            # Emulator flag
            if self.tool_config['is_emulator']:
                args.append("-is_emulator")

            # Debug mode
            if self.tool_config['debug_mode']:
                args.append("-debug")

            self.logger.debug(f"RVAndroid command arguments: {args}")
            return args

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "build_command_args",
                    "app_name": app.name,
                    "tool": "rvandroid",
                    "component": "RVAndroidTool"
                }
            )
            raise

    def validate_execution_environment(self, app: App) -> bool:
        """
        Validate that the execution environment is properly configured for RVAndroid.

        Args:
            app: Application instance to validate against

        Returns:
            True if environment is valid, False otherwise
        """
        try:
            self.logger.debug("Validating RVAndroid execution environment")

            # Check if DroidBot is available (required for RVAndroid integration)
            try:
                droidbot_check = Command("droidbot", ["--help"], timeout=10)
                result = droidbot_check.invoke()
                if result.returncode != 0:
                    self.logger.error("DroidBot is not available (required for RVAndroid)")
                    return False
            except Exception as e:
                self.logger.error(f"DroidBot validation failed: {str(e)}")
                return False

            # Check if ADB is available
            try:
                adb_check = Command("adb", ["devices"], timeout=10)
                result = adb_check.invoke()
                if result.returncode != 0:
                    self.logger.error("ADB is not available or not responding")
                    return False
            except Exception as e:
                self.logger.error(f"ADB validation failed: {str(e)}")
                return False

            # Validate APK file
            if not os.path.exists(app.path):
                self.logger.error(f"APK file not found: {app.path}")
                return False

            # Check device connectivity
            device_id = self.tool_config['device_id']
            try:
                device_check = Command("adb", ["-s", device_id, "shell", "echo", "test"], timeout=10)
                result = device_check.invoke()
                if result.returncode != 0:
                    self.logger.error(f"Device not accessible: {device_id}")
                    return False
            except Exception as e:
                self.logger.error(f"Device connectivity check failed: {str(e)}")
                return False

            # Validate server port availability (basic check)
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', self.tool_config['server_port']))
                sock.close()
                if result == 0:
                    self.logger.warning(f"Port {self.tool_config['server_port']} is already in use")
                    # Don't fail validation, just warn - server startup will handle this
            except Exception:
                pass  # Port check is optional

            self.logger.info("RVAndroid execution environment validation successful")
            return True

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "validate_execution_environment",
                    "app_name": app.name,
                    "tool": "rvandroid",
                    "component": "RVAndroidTool"
                }
            )
            return False

    def get_execution_command(self, app: App, output_file: str, task_config: Dict[str, Any]) -> Command:
        """
        Create the execution command for RVAndroid tool.

        Args:
            app: Application instance
            output_file: Path to output trace file
            task_config: Task-specific configuration

        Returns:
            Configured Command instance for execution
        """
        try:
            # Build command arguments
            args = self.build_command_args(app, output_file, task_config)
            
            # Calculate timeout with buffer
            timeout_seconds = task_config.get('timeout', self.tool_config['timeout'])
            execution_timeout = timeout_seconds + 60  # Add 60 second buffer for server startup/shutdown

            # Create command with comprehensive configuration
            command = Command(
                executable="droidbot",
                args=args,
                timeout=execution_timeout
            )

            self.logger.info(f"RVAndroid execution command created for app: {app.name}")
            return command

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "get_execution_command",
                    "app_name": app.name,
                    "tool": "rvandroid",
                    "component": "RVAndroidTool"
                }
            )
            raise

    def process_execution_result(self, result, app: App, output_file: str) -> Dict[str, Any]:
        """
        Process the execution result and extract relevant metrics.

        Args:
            result: Command execution result
            app: Application instance
            output_file: Path to output trace file

        Returns:
            Dictionary containing execution metrics and status information
        """
        try:
            self.logger.debug(f"Processing RVAndroid execution result for app: {app.name}")

            # Base result information
            execution_result = {
                "tool": "rvandroid",
                "app_name": app.name,
                "execution_time": getattr(result, 'execution_time', 0),
                "return_code": result.returncode,
                "success": result.returncode == 0,
                "output_file": output_file,
                "trace_generated": os.path.exists(output_file) if output_file else False
            }

            # Add tool-specific metrics
            if result.returncode == 0:
                execution_result.update({
                    "exploration_completed": True,
                    "timeout_occurred": False,
                    "policy_used": self.tool_config['policy'],
                    "llm_backend": self.tool_config['llm_backend'],
                    "llm_model": self.tool_config['llm_model'],
                    "prompt_strategy": self.tool_config['prompt_strategy'],
                    "ai_actions_generated": self._analyze_trace_for_ai_actions(output_file),
                    "monitored_operations_detected": self._analyze_trace_for_monitored_operations(output_file),
                    "server_based_execution": True
                })
            else:
                execution_result.update({
                    "exploration_completed": False,
                    "timeout_occurred": result.returncode == 124,  # Standard timeout return code
                    "error_details": getattr(result, 'stderr', ''),
                    "policy_used": self.tool_config['policy'],
                    "llm_backend": self.tool_config['llm_backend'],
                    "ai_actions_generated": 0,
                    "monitored_operations_detected": 0
                })

            # Extract additional metrics from trace file
            if output_file and os.path.exists(output_file):
                execution_result.update(self._extract_trace_metrics(output_file))

            self.logger.info(f"RVAndroid execution result processed for app: {app.name}")
            return execution_result

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "process_execution_result",
                    "app_name": app.name,
                    "tool": "rvandroid",
                    "component": "RVAndroidTool"
                }
            )
            
            # Return basic error result
            return {
                "tool": "rvandroid",
                "app_name": app.name,
                "success": False,
                "error": f"Result processing failed: {str(e)}"
            }

    def _analyze_trace_for_ai_actions(self, trace_file: str) -> int:
        """
        Analyze trace file for AI-generated action patterns.

        Args:
            trace_file: Path to the trace file

        Returns:
            Number of AI-generated actions detected
        """
        try:
            if not os.path.exists(trace_file):
                return 0

            # Simple analysis - count lines that might indicate AI actions
            ai_actions = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Look for patterns that indicate AI-generated actions
                    if any(keyword in line.lower() for keyword in [
                        'rvandroid', 'llm', 'ai', 'generated', 'intelligent',
                        'action_service', 'prompt', 'response'
                    ]):
                        ai_actions += 1

            return ai_actions

        except Exception as e:
            self.logger.warning(f"Failed to analyze trace file for AI actions: {str(e)}")
            return 0

    def _analyze_trace_for_monitored_operations(self, trace_file: str) -> int:
        """
        Analyze trace file for monitored operations occurrences.

        Args:
            trace_file: Path to the trace file

        Returns:
            Number of monitored operations detected
        """
        try:
            if not os.path.exists(trace_file):
                return 0

            # Simple analysis - count lines that might indicate monitored operations
            monitored_count = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Look for patterns that indicate monitored operations
                    if any(keyword in line.lower() for keyword in [
                        'cipher', 'encrypt', 'decrypt', 'hash', 'signature',
                        'monitored', 'violation', 'specification'
                    ]):
                        monitored_count += 1

            return monitored_count

        except Exception as e:
            self.logger.warning(f"Failed to analyze trace file for monitored operations: {str(e)}")
            return 0

    def _extract_trace_metrics(self, trace_file: str) -> Dict[str, Any]:
        """
        Extract additional metrics from the trace file.

        Args:
            trace_file: Path to the trace file

        Returns:
            Dictionary containing trace-based metrics
        """
        try:
            if not os.path.exists(trace_file):
                return {}

            # Get basic file information
            file_size = os.path.getsize(trace_file)
            
            # Count lines in trace file
            line_count = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)

            return {
                "trace_file_size": file_size,
                "trace_line_count": line_count,
                "trace_file_exists": True,
                "trace_level": self.tool_config['trace_level']
            }

        except Exception as e:
            self.logger.warning(f"Failed to extract trace metrics: {str(e)}")
            return {"trace_file_exists": False}

    def get_tool_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the RVAndroid tool.

        Returns:
            Dictionary containing tool metadata and configuration
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": "ai_guided",
            "category": "ai_guided",
            "version": "1.0.0",
            "capabilities": self.TOOL_SPEC.capabilities,
            "dependencies": self.TOOL_SPEC.dependencies,
            "configuration": dict(self.tool_config),
            "execution_pattern": self.process_pattern,
            "requires_adb": True,
            "requires_droidbot": True,
            "requires_server": True,
            "server_url": self.tool_config.get('server_url'),
            "llm_backend": self.tool_config.get('llm_backend'),
            "llm_model": self.tool_config.get('llm_model'),
            "ai_guided_testing_support": True,
            "server_based_architecture": True,
            "monitored_operations_support": True
        }

    def __str__(self) -> str:
        """String representation of the RVAndroid tool."""
        return f"RVAndroidTool(name='{self.name}', configured={bool(self.tool_config)})"

    def __repr__(self) -> str:
        """Detailed string representation of the RVAndroid tool."""
        return (f"RVAndroidTool(name='{self.name}', description='{self.description}', "
                f"server_url='{self.tool_config.get('server_url')}', "
                f"llm_backend='{self.tool_config.get('llm_backend')}', "
                f"config_keys={list(self.tool_config.keys())})")