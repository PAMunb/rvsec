import logging as logging_api

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.config.configuration import Configuration
from rvandroid.experiment.task.task_model import Task
from rvandroid.server import Server
from rvandroid.llm.service.action_service import LLMActionService
from ..tool_spec import AbstractTool
from ...experiment.event.bus import EventBus, EventType
from ...util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_TOOL_NAME, CONTEXT_COMPONENT
from ...util.logging.manager import LoggingManager

logging = logging_api.getLogger(__name__)


class ToolSpec(AbstractTool):
    """
    A specialized tool implementation for RV-Android's AI-driven test automation workflow.

    ### Architectural Decisions:
    - Implements a custom tool integration for RV-Android's AI-powered testing
    - Utilizes component configurator for flexible AI strategy configuration
    - Supports dynamic server initialization for AI action generation
    - Provides a standardized interface for AI-driven test execution

    ### Role in the System:
    - Serves as the primary tool for AI-guided Android application testing
    - Coordinates between DroidBot and RV-Android's AI action service
    - Manages server initialization and test execution workflow
    - Enables intelligent, adaptive test exploration using language models
    - Provides a bridge between test automation and AI-driven action generation

    ### Key Considerations:
    - Handles complex server and service initialization
    - Manages configuration of AI components dynamically
    - Supports flexible AI strategy selection
    - Implements robust error handling for AI-driven testing
    - Ensures seamless integration with test automation frameworks

    ### Integration Strategy:
    - Deeply integrated with RV-Android's AI and testing infrastructure
    - Compatible with DroidBot and other test automation tools
    - Supports dynamic configuration of AI models and strategies
    - Enables flexible AI action generation endpoints
    - Provides a standardized tool execution interface

    ### Performance and Scalability:
    - Designed for efficient AI-driven test execution
    - Minimizes overhead in server and service initialization
    - Supports various AI model configurations
    - Adaptable to different testing complexity levels
    - Enables intelligent, adaptive test exploration
    """
    def __init__(self):
        super(ToolSpec, self).__init__("rvandroid", """rv-android""", "br.unb.cic.rvsec")

    def execute_tool_specific_logic(self, task: Task, app: App):
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

        # Create component configurator
        component_config = ComponentConfigurator(task.static_data)

        # Configure with improved settings
        component_config.set_llm("ollama", "llama3.2:3b")  # Default to Llama 3.2 3B model
        component_config.set_strategy("composable_single_action")  # Use more advanced strategy
        component_config.set_visitor("enhanced")
        component_config.set_parser("droidbot")

        # Log configuration
        logger.info(f"RVAndroid tool using configuration: {component_config.describe_configuration()}")

        # Create service
        service = LLMActionService(task.static_data, config=component_config)

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

        except Exception as e:
            logger.error(f"Error running RVAndroid tool: {e}", exc_info=True)
            raise

        finally:
            logger.info("Stopping server")
            server.stop()

            # Clean up service resources
            service.cleanup()

            # Publish tool end event
            EventBus.get_instance().publish_task_event(
                EventType.TOOL_STOPPED,
                task_id=task.id,
                details={"tool": "rvandroid"},
                source="RVAndroidTool"
            )
