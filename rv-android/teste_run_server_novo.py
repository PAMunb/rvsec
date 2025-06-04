# start_rvandroid_server.py

"""
Enhanced RVAndroid Server Startup Script for IDE Execution

This script provides a robust startup mechanism for the RVAndroid server designed
for direct execution from IDEs like PyCharm and VSCode. All configuration parameters
are hardcoded for easy modification and immediate execution without command-line
arguments.

Features:
    - Direct IDE execution without command-line arguments
    - Support for multiple LLM providers (Ollama, OpenAI, Anthropic, etc.)
    - Comprehensive logging and error handling
    - Health monitoring and graceful shutdown capabilities
    - Integration with existing RV-Android infrastructure
    - Performance monitoring and metrics collection

Architecture:
    The startup script implements a layered initialization approach with proper
    dependency injection, configuration validation, and component lifecycle
    management. It provides clean separation between configuration, initialization,
    and execution phases.

Usage:
    Simply modify the configuration section below and run the script directly
    from your IDE. No command-line arguments required.

Created: 2025-06-02
Authors: RV-Android Team
Version: 2.0.0
"""

import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import PromptStrategyType, ScreenParserType
from rvandroid.llm.frontier_models import FrontierModel
from rvandroid.llm.huggingface_llm import HuggingFaceLLM
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.parser.screen.visitor.visitor_factory import VisitorFactory
from rvandroid.parser.static import static_analysis_parser
from rvandroid.server_novo import RVAndroidServer
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.logging.constants import CONTEXT_COMPONENT


# ============================================================================
# CONFIGURATION SECTION - MODIFY THESE PARAMETERS AS NEEDED
# ============================================================================

class ServerConfiguration:
    """
    Centralized configuration for RVAndroid server.
    Modify these parameters according to your deployment requirements.
    """

    # Server configuration
    HOST = "localhost"  # "0.0.0.0" for external access
    PORT = 5000
    MAX_TEMP_FILES = 10

    # Application configuration
    APP_FOLDER = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out"
    APK_NAME = "cryptoapp.apk"

    # Preset configuration - Choose one of the following presets:
    # "ollama", "batch_action", "huggingface", "dspy", "claude", "openai", "amazon", "google", "custom"
    PRESET = "batch_action"  # Change this to use different presets

    # Custom LLM configuration (used when PRESET = "custom")
    CUSTOM_LLM_TYPE = OllamaLLM.NAME
    CUSTOM_MODEL = OllamaLLM.QWEN
    CUSTOM_BASE_URL = "http://localhost:11434"
    CUSTOM_PROVIDER = None
    CUSTOM_API_KEY = None
    CUSTOM_TEMPERATURE = 0.3

    # Custom strategy and parser configuration (used when PRESET = "custom")
    CUSTOM_STRATEGY = PromptStrategyType.BATCH_ACTION
    CUSTOM_PARSER_TYPE = ScreenParserType.DROIDBOT
    CUSTOM_VISITOR_TYPE = VisitorFactory.DEFAULT

    # API Keys (set these if using cloud-based LLMs)
    ANTHROPIC_API_KEY = None  # or os.environ.get("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = None  # or os.environ.get("OPENAI_API_KEY")
    GOOGLE_API_KEY = None  # or os.environ.get("GOOGLE_API_KEY")

    # AWS Configuration (for Amazon Bedrock)
    AWS_REGION = "us-east-1"

    # Operational configuration
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
    DEBUG = True  # Enable debug logging

    @classmethod
    def get_api_key_for_preset(cls, preset: str) -> Optional[str]:
        """Get API key for the specified preset."""
        if preset == "claude":
            return cls.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY")
        elif preset == "openai":
            return cls.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        elif preset == "google":
            return cls.GOOGLE_API_KEY or os.environ.get("GOOGLE_API_KEY")
        return None

    @classmethod
    def validate(cls):
        """Validate configuration parameters."""
        if not os.path.exists(cls.APP_FOLDER):
            raise ValueError(f"Application folder not found: {cls.APP_FOLDER}")

        apk_path = os.path.join(cls.APP_FOLDER, cls.APK_NAME)
        if not os.path.exists(apk_path):
            raise ValueError(f"APK file not found: {apk_path}")

        if cls.PORT <= 0 or cls.PORT > 65535:
            raise ValueError("Port must be between 1 and 65535")

        # Validate API keys for cloud presets
        if cls.PRESET in ["claude", "openai", "google"]:
            api_key = cls.get_api_key_for_preset(cls.PRESET)
            if not api_key:
                raise ValueError(
                    f"API key required for {cls.PRESET}. Set the appropriate API key in the configuration.")

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging."""
        return {
            "server": {
                "host": cls.HOST,
                "port": cls.PORT,
                "max_temp_files": cls.MAX_TEMP_FILES
            },
            "application": {
                "app_folder": cls.APP_FOLDER,
                "apk_name": cls.APK_NAME
            },
            "preset": cls.PRESET,
            "operational": {
                "log_level": cls.LOG_LEVEL,
                "debug": cls.DEBUG
            }
        }


class PresetConfigurator:
    """
    Handles preset configuration application to component configurator.

    This class encapsulates all preset configurations for different LLM providers
    and strategies, making it easy to switch between different setups.
    """

    def __init__(self, config_class):
        """
        Initialize preset configurator.

        Args:
            config_class: Configuration class containing parameters
        """
        self.config = config_class
        self.logger = logging.getLogger(f"{__name__}.PresetConfigurator")

    def apply_preset(self, configurator: ComponentConfigurator):
        """
        Apply the configured preset to the component configurator.

        Args:
            configurator: Component configurator to configure
        """
        preset = self.config.PRESET.lower()

        self.logger.info(f"Applying preset configuration: {preset}")

        if preset == "ollama":
            self._apply_ollama_preset(configurator)
        elif preset == "batch_action":
            self._apply_batch_action_preset(configurator)
        elif preset == "huggingface":
            self._apply_huggingface_preset(configurator)
        elif preset == "dspy":
            self._apply_dspy_preset(configurator)
        elif preset == "claude":
            self._apply_claude_preset(configurator)
        elif preset == "openai":
            self._apply_openai_preset(configurator)
        elif preset == "amazon":
            self._apply_amazon_preset(configurator)
        elif preset == "google":
            self._apply_google_preset(configurator)
        elif preset == "custom":
            self._apply_custom_configuration(configurator)
        else:
            raise ValueError(f"Unknown preset: {preset}")

        # Log configuration summary
        config_summary = configurator.describe_configuration()
        self.logger.info("=== RV-Android Configuration ===")
        self.logger.info(f"LLM: {config_summary['llm']['type']}")
        self.logger.info(f"Model: {config_summary['llm']['model']}")
        self.logger.info(f"Strategy: {config_summary['strategy']}")
        self.logger.info(f"Parser: {config_summary['parser']}")
        self.logger.info(f"Visitor: {config_summary['visitor']}")
        self.logger.info("================================")

    def _apply_ollama_preset(self, configurator: ComponentConfigurator):
        """Apply Ollama preset configuration for standard single actions."""
        configurator.set_llm(
            llm_type=OllamaLLM.NAME,
            model=OllamaLLM.LLAMA,
            base_url="http://localhost:11434",
            temperature=0.3
        )
        configurator.set_strategy(PromptStrategyType.STANDARD)
        configurator.set_parser(ScreenParserType.DROIDBOT)
        configurator.set_visitor(VisitorFactory.DEFAULT)

    def _apply_batch_action_preset(self, configurator: ComponentConfigurator):
        """Apply batch action preset configuration for multi-action strategies."""
        configurator.set_llm(
            llm_type=OllamaLLM.NAME,
            model=OllamaLLM.LLAMA,
            base_url="http://localhost:11434",
            temperature=0.3
        )
        configurator.set_strategy(PromptStrategyType.BATCH_ACTION)
        configurator.set_parser(ScreenParserType.DROIDBOT)
        configurator.set_visitor(VisitorFactory.DEFAULT)

    def _apply_huggingface_preset(self, configurator: ComponentConfigurator):
        """Apply Hugging Face preset configuration."""
        configurator.set_llm(
            llm_type=HuggingFaceLLM.NAME,
            model=HuggingFaceLLM.LLAMA,
            temperature=0.3
        )
        configurator.set_strategy(PromptStrategyType.STANDARD)
        configurator.set_parser(ScreenParserType.DROIDBOT)
        configurator.set_visitor(VisitorFactory.DEFAULT)

    def _apply_dspy_preset(self, configurator: ComponentConfigurator):
        """Apply DSPy preset configuration."""
        configurator.set_llm(
            llm_type="dspy",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            provider="ollama",
            temperature=0.3
        )
        configurator.set_strategy("dspy")
        configurator.set_parser(ScreenParserType.DROIDBOT)
        configurator.set_visitor(VisitorFactory.DEFAULT)

    def _apply_claude_preset(self, configurator: ComponentConfigurator):
        """Apply Claude (Anthropic) preset configuration."""
        api_key = self.config.get_api_key_for_preset("claude")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY required for Claude preset")

        configurator.set_llm(
            llm_type="frontier",
            model=FrontierModel.CLAUDE_SONNET,
            provider="anthropic",
            api_key=api_key,
            temperature=0.2
        )
        configurator.set_strategy("frontier")
        configurator.set_parser(ScreenParserType.DROIDBOT)
        configurator.set_visitor(VisitorFactory.DEFAULT)

    def _apply_openai_preset(self, configurator: ComponentConfigurator):
        """Apply OpenAI preset configuration."""
        api_key = self.config.get_api_key_for_preset("openai")
        if not api_key:
            raise ValueError("OPENAI_API_KEY required for OpenAI preset")

        configurator.set_llm(
            llm_type="frontier",
            model=FrontierModel.GPT_4,
            provider="openai",
            api_key=api_key,
            temperature=0.2
        )
        configurator.set_strategy("frontier")
        configurator.set_parser(ScreenParserType.DROIDBOT)
        configurator.set_visitor(VisitorFactory.DEFAULT)

    def _apply_amazon_preset(self, configurator: ComponentConfigurator):
        """Apply Amazon Bedrock preset configuration."""
        configurator.set_llm(
            llm_type="frontier",
            model=FrontierModel.NOVA_SONNET,
            provider="amazon",
            region=self.config.AWS_REGION,
            temperature=0.2
        )
        configurator.set_strategy("frontier")
        configurator.set_parser(ScreenParserType.DROIDBOT)
        configurator.set_visitor(VisitorFactory.DEFAULT)

    def _apply_google_preset(self, configurator: ComponentConfigurator):
        """Apply Google preset configuration."""
        api_key = self.config.get_api_key_for_preset("google")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY required for Google preset")

        configurator.set_llm(
            llm_type="frontier",
            model=FrontierModel.GEMINI_PRO,
            provider="google",
            api_key=api_key,
            temperature=0.2
        )
        configurator.set_strategy("frontier")
        configurator.set_parser(ScreenParserType.DROIDBOT)
        configurator.set_visitor(VisitorFactory.DEFAULT)

    def _apply_custom_configuration(self, configurator: ComponentConfigurator):
        """Apply custom configuration from parameters."""
        configurator.set_llm(
            llm_type=self.config.CUSTOM_LLM_TYPE,
            model=self.config.CUSTOM_MODEL,
            base_url=self.config.CUSTOM_BASE_URL,
            provider=self.config.CUSTOM_PROVIDER,
            api_key=self.config.CUSTOM_API_KEY,
            temperature=self.config.CUSTOM_TEMPERATURE
        )
        configurator.set_strategy(self.config.CUSTOM_STRATEGY)
        configurator.set_parser(self.config.CUSTOM_PARSER_TYPE)
        configurator.set_visitor(self.config.CUSTOM_VISITOR_TYPE)


class ServerManager:
    """
    Comprehensive server lifecycle management with monitoring and control.

    This class handles the complete lifecycle of the RVAndroid server including
    initialization, startup, monitoring, and graceful shutdown with proper
    resource cleanup and error handling.
    """

    def __init__(self):
        """Initialize server manager with configuration."""
        self.config = ServerConfiguration
        self.server: Optional[RVAndroidServer] = None
        self.action_service: Optional[LLMActionService] = None
        self.shutdown_requested = False

        # Set up logging
        self._setup_logging()
        self.logger = logging.getLogger(f"{__name__}.ServerManager")

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_logging(self):
        """Set up comprehensive logging configuration."""
        # Configure logging level
        log_level = logging.DEBUG if self.config.DEBUG else getattr(logging, self.config.LOG_LEVEL.upper())

        # Basic logging configuration
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stdout
        )

        # Suppress verbose third-party logging
        logging.getLogger("androguard").setLevel(logging.WARNING)
        logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
        logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
        logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

    def initialize_and_start_server(self) -> bool:
        """
        Initialize all components and start the RVAndroid server.

        Returns:
            True if server started successfully
        """
        try:
            self.logger.info("=== Initializing RVAndroid Server ===")
            self.logger.info(f"Configuration: {self.config.to_dict()}")

            # Load application and static data
            app, static_data = self._load_application_data()
            if not app or not static_data:
                return False

            # Create and configure component configurator
            configurator = self._create_configurator(static_data)
            if not configurator:
                return False

            # Create LLM Action Service
            self.action_service = self._create_action_service(static_data, configurator, app.package_name)
            if not self.action_service:
                return False

            # Create and start server
            self.server = self._create_server(self.action_service)
            if not self.server:
                return False

            # Start server
            if not self.server.start():
                self.logger.error("Failed to start RVAndroid server")
                return False

            self.logger.info(f"RVAndroid server started successfully on http://{self.config.HOST}:{self.config.PORT}")
            self.logger.info("Server is ready to accept connections from DroidBot policies")
            return True

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ServerManager",
                    "operation": "initialize_and_start_server"
                }
            )
            self.logger.error(f"Error initializing server: {e}", exc_info=True)
            return False

    def _load_application_data(self) -> tuple[Optional[App], Optional[Any]]:
        """
        Load application and static analysis data.

        Returns:
            Tuple of (App instance, static data) or (None, None) if loading fails
        """
        try:
            self.logger.info("Loading application data")

            # Create app instance
            apk_path = os.path.join(self.config.APP_FOLDER, self.config.APK_NAME)
            app = App(apk_path)
            package = app.package_name

            self.logger.info(f"Loaded application: {package}")

            # Load static analysis data
            static_data = static_analysis_parser.read_static_analysis_files(
                self.config.APP_FOLDER,
                self.config.APK_NAME,
                package
            )

            if static_data:
                self.logger.info("Static analysis data loaded successfully")
            else:
                self.logger.warning("No static analysis data available")

            return app, static_data

        except Exception as e:
            self.logger.error(f"Error loading application data: {e}", exc_info=True)
            return None, None

    def _create_configurator(self, static_data: Any) -> Optional[ComponentConfigurator]:
        """
        Create and configure component configurator.

        Args:
            static_data: Static analysis data

        Returns:
            Configured ComponentConfigurator or None if creation fails
        """
        try:
            self.logger.info("Creating component configurator")

            # Initialize configurator
            configurator = ComponentConfigurator(static_data)

            # Apply preset configuration
            preset_configurator = PresetConfigurator(self.config)
            preset_configurator.apply_preset(configurator)

            return configurator

        except Exception as e:
            self.logger.error(f"Error creating configurator: {e}", exc_info=True)
            return None

    def _create_action_service(self, static_data: Any, configurator: ComponentConfigurator, package_name: str) -> \
    Optional[LLMActionService]:
        """
        Create LLM Action Service with proper configuration.

        Args:
            static_data: Static analysis data
            configurator: Configured component configurator
            package_name: Application package name

        Returns:
            Configured LLMActionService or None if creation fails
        """
        try:
            self.logger.info("Creating LLM Action Service")

            # Create action service
            action_service = LLMActionService(static_data, configurator, package_name)

            self.logger.info("LLM Action Service created successfully")
            return action_service

        except Exception as e:
            self.logger.error(f"Error creating action service: {e}", exc_info=True)
            return None

    def _create_server(self, action_service: LLMActionService) -> Optional[RVAndroidServer]:
        """
        Create RVAndroid server instance.

        Args:
            action_service: Configured LLM Action Service

        Returns:
            RVAndroidServer instance or None if creation fails
        """
        try:
            self.logger.info("Creating RVAndroid server")

            # Create server instance
            server = RVAndroidServer(
                action_service=action_service,
                host=self.config.HOST,
                port=self.config.PORT,
                max_temp_files=self.config.MAX_TEMP_FILES
            )

            self.logger.info("RVAndroid server created successfully")
            return server

        except Exception as e:
            self.logger.error(f"Error creating server: {e}", exc_info=True)
            return None

    def run_server(self):
        """
        Run server with monitoring and graceful shutdown handling.

        This method implements the main server loop with health monitoring,
        graceful shutdown handling, and comprehensive error recovery.
        """
        try:
            self.logger.info("Starting server monitoring loop")
            self.logger.info("Press Ctrl+C to shutdown the server gracefully")

            # Main server loop
            while not self.shutdown_requested:
                # Check server health
                if self.server and not self.server.is_healthy():
                    self.logger.warning("Server health check failed")

                # Sleep and check for shutdown
                time.sleep(5)

            self.logger.info("Shutdown requested, stopping server")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ServerManager",
                    "operation": "run_server"
                }
            )
            self.logger.error(f"Error in server monitoring loop: {e}", exc_info=True)

        finally:
            self._shutdown_server()

    def _shutdown_server(self):
        """
        Perform graceful server shutdown with comprehensive cleanup.

        This method handles the complete shutdown process including server
        stopping, resource cleanup, and final status reporting.
        """
        try:
            self.logger.info("Shutting down RVAndroid server")

            # Stop server
            if self.server:
                success = self.server.stop()
                if success:
                    self.logger.info("Server stopped successfully")
                else:
                    self.logger.warning("Server shutdown encountered issues")

            # Clean up action service
            if self.action_service and hasattr(self.action_service, 'cleanup'):
                try:
                    self.action_service.cleanup()
                    self.logger.info("Action service cleaned up")
                except Exception as e:
                    self.logger.warning(f"Error cleaning up action service: {e}")

            self.logger.info("Server shutdown completed")

        except Exception as e:
            self.logger.error(f"Error during server shutdown: {e}", exc_info=True)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals for graceful termination."""
        self.logger.info(f"Received signal {signum}, requesting graceful shutdown")
        self.shutdown_requested = True


def main():
    """
    Main entry point for RVAndroid server startup.

    This function orchestrates the complete server startup process including
    configuration validation, component initialization, and server execution
    with comprehensive error handling.
    """
    try:
        # Validate configuration
        ServerConfiguration.validate()

        print("=== RVAndroid Enhanced Server v2.0.0 ===")
        print(f"Starting server with preset: {ServerConfiguration.PRESET}")
        print(f"Server will be available at: http://{ServerConfiguration.HOST}:{ServerConfiguration.PORT}")

        # Create and start server
        server_manager = ServerManager()

        # Initialize and start server
        if not server_manager.initialize_and_start_server():
            print("ERROR: Failed to initialize and start server")
            return False

        print("\n=== Server is running ===")
        print("You can now run the test script in another terminal or IDE.")
        print("Press Ctrl+C to shutdown the server.")

        # Run server with monitoring
        server_manager.run_server()

        return True

    except KeyboardInterrupt:
        print("\nServer startup interrupted by user")
        return False

    except Exception as e:
        print(f"Unexpected error during server startup: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """
    Entry point for IDE execution.

    To use this script:
    1. Modify the configuration parameters in the ServerConfiguration class above
    2. Ensure your LLM service (Ollama, etc.) is running if using local models
    3. Set API keys in the configuration if using cloud-based LLMs
    4. Run this script directly from your IDE (PyCharm, VSCode, etc.)

    The script will automatically:
    - Validate configuration
    - Load application data
    - Initialize LLM Action Service
    - Start the RVAndroid server
    - Monitor server health
    - Handle graceful shutdown

    Available Presets:
    - "ollama": Standard Ollama configuration with single actions
    - "batch_action": Ollama with batch action support
    - "huggingface": Hugging Face local models
    - "dspy": DSPy framework integration
    - "claude": Anthropic Claude (requires API key)
    - "openai": OpenAI GPT models (requires API key)
    - "amazon": Amazon Bedrock (requires AWS credentials)
    - "google": Google Gemini (requires API key)
    - "custom": Custom configuration using CUSTOM_* parameters
    """
    success = main()
    if not success:
        sys.exit(1)