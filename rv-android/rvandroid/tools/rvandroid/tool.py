# rvandroid/tools/rvandroid/tool.py
"""
RVAndroid tool implementation with LLM configuration support.
"""
import logging as logging_api

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.config.configuration import Configuration
from rvandroid.experiment.task.task_model import Task
from rvandroid.llm.constants import PromptStrategyType, ScreenParserType
from rvandroid.parser.screen.visitor.visitor_factory import VisitorFactory
from rvandroid.server import Server
from rvandroid.tools.configurable_tool import ConfigurableTool
from rvandroid.experiment.event.bus import EventBus
from rvandroid.experiment.event.models import EventType
from rvandroid.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_TOOL_NAME, CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.error.error_handler import ErrorHandler


class ToolSpec(ConfigurableTool):
    """
    A specialized tool implementation for RV-Android's AI-driven test automation workflow.

    ### Architectural Decisions:
    - Implements a configurble tool for RV-Android's AI-powered testing
    - Utilizes component configurator for flexible AI strategy configuration
    - Supports dynamic server initialization for AI action generation
    - Provides a standardized interface for AI-driven test execution
    - Integrates with MCP framework for standardized LLM communication

    ### Role in the System:
    - Serves as the primary tool for AI-guided Android application testing
    - Coordinates between DroidBot and RV-Android's AI action service
    - Manages server initialization and test execution workflow
    - Enables intelligent, adaptive test exploration using language models
    - Provides a bridge between test automation and AI-driven action generation
    """

    def __init__(self):
        """Initialize the RVAndroid tool with default configuration."""
        super().__init__(
            "rvandroid",
            "AI-driven Android testing tool using LLM guidance",
            "br.unb.cic.rvsec"
        )

        # Default configuration already handled by ComponentConfigurator
        # Just ensure component_config is initialized
        self.component_config = ComponentConfigurator()

        # Set default LLM configuration
        self.component_config.set_llm("ollama", "llama3.2:3b")
        self.component_config.set_strategy(PromptStrategyType.BATCH_ACTION)
        self.component_config.set_parser(ScreenParserType.DROIDBOT)
        self.component_config.set_visitor(VisitorFactory.DEFAULT)

    def configure_tool_specific(self, config):
        """
        Configure RVAndroid tool with specific parameters.
        LLM configuration is handled by ToolFactory.
        """
        # Any additional RVAndroid-specific configuration can be handled here
        pass

    def execute_tool_specific_logic(self, task: Task, app: App):
        """Execute RVAndroid testing with the configured LLM and components."""
        # Get configuration
        config = Configuration.get_instance()
        rvandroid_url = config.get_str("rvandroid_url", "http://127.0.0.1:5000")

        # Set up logging using LoggingManager
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            'tools.rvandroid',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: app.name,
                CONTEXT_TOOL_NAME: self.name,
                CONTEXT_COMPONENT: 'RVAndroidTool'
            }
        )

        # Initialize error handler
        error_handler = ErrorHandler.get_instance()

        # Log configuration
        logger.info(f"RVAndroid tool using configuration: {self.component_config.describe_configuration()}")

        # Create MCP-based service
        logger.info("Creating MCP-based LLM action service")
        from rvandroid.llm.service.action_service import LLMActionService
        service = LLMActionService(task.static_data, config=self.component_config)

        # Publish tool start event
        EventBus.get_instance().publish_task_event(
            EventType.TOOL_STARTED,
            task_id=task.id,
            details={"tool": "rvandroid"},
            source="RVAndroidTool"
        )

        # Start server and run experiment
        server = Server(service, port=5000)
        try:
            if server.start():
                logger.info("Server started successfully")
                with open(task.result.trace_file, "wb") as trace:
                    exec_cmd = Command("droidbot", [
                        "-d", "emulator-5554",
                        "-a", app.path,
                        "--rvandroid_url", rvandroid_url,
                        "-policy", "rvandroid",
                        "-is_emulator",
                    ], task.config.timeout)
                    exec_cmd.invoke(stdout=trace)
            else:
                logger.error("Server failed to start")
                from rvandroid.util.exceptions import RVAndroidError
                error = RVAndroidError("Failed to start RVAndroid server")
                error_handler.handle_error(
                    error,
                    context={
                        "task_id": task.id,
                        "app_name": app.name,
                        "tool_name": self.name
                    }
                )

        except Exception as e:
            logger.error(f"Error running RVAndroid tool: {e}", exc_info=True)
            from rvandroid.util.exceptions import RVAndroidError
            error = RVAndroidError(f"RVAndroid execution error: {str(e)}")
            error_handler.handle_error(
                error,
                context={
                    "task_id": task.id,
                    "app_name": app.name,
                    "tool_name": self.name
                }
            )
            raise

        finally:
            logger.info("Stopping server")
            server.stop()

            # Clean up service resources
            if hasattr(service, 'cleanup'):
                service.cleanup()

            # Publish tool end event
            EventBus.get_instance().publish_task_event(
                EventType.TOOL_STOPPED,
                task_id=task.id,
                details={"tool": "rvandroid"},
                source="RVAndroidTool"
            )
           