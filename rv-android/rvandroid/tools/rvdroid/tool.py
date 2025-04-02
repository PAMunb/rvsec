# rvandroid/tools/rvdroid/tool.py
"""
RVDroid tool implementation with configuration support.
"""
import os

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.task.task_model import Task
from rvandroid.rvdroid.core.service import RVDroidService
from rvandroid.tools.configurable_tool import ConfigurableTool
from rvandroid.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_TOOL_NAME, CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ToolSpec(ConfigurableTool):
    """
    A specialized tool implementation for RVDroid, a UIAutomator2-based testing tool integrated with RV-Android.

    ### Architectural Decisions:
    - Extends ConfigurableTool for standardized configuration handling
    - Integrates with ComponentConfigurator for flexible AI configuration
    - Provides a modular interface to UIAutomator2-based testing

    ### Role in the System:
    - Serves as the main entry point for UIAutomator2-based testing in RV-Android
    - Integrates AI-guided testing with UIAutomator2 capabilities
    - Provides a bridge between RV-Android and UIAutomator2 testing
    - Enables intelligent, adaptive test exploration in native Android environments
    """

    def __init__(self):
        """Initialize the RVDroid tool with default configuration."""
        super().__init__(
            "rvdroid",
            "UIAutomator2-based Android testing tool with AI-guided exploration",
            "br.unb.cic.rvsec"
        )

        # Initialize component configurator
        self.component_config = ComponentConfigurator()

        # Set defaults
        self.component_config.set_parser("uiautomator")
        self.component_config.set_visitor("enhanced")

        # Default configuration
        self.config = {
            "use_llm": False  # Default to no LLM guidance
        }

    def configure_tool_specific(self, config):
        """Configure RVDroid-specific parameters."""
        # Update parameters if specified
        if "use_llm" in config:
            self.config["use_llm"] = bool(config["use_llm"])

    def execute_tool_specific_logic(self, task: Task, app: App):
        """Execute RVDroid with the configured parameters."""
        # Set up logging using LoggingManager
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            'tools.rvdroid',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: app.name,
                CONTEXT_TOOL_NAME: self.name,
                CONTEXT_COMPONENT: 'RVDroidTool'
            }
        )

        # Get event bus for publishing events
        event_bus = EventBus.get_instance()

        # Log configuration
        logger.info(f"RVDroid tool initialized with configuration: {self.component_config.describe_configuration()}")

        # Publish tool start event
        event_bus.publish_task_event(
            EventType.TOOL_STARTED,
            task_id=task.id,
            details={"tool": "rvdroid"},
            source="RVDroidTool"
        )

        try:
            # Create and start RVDroid service
            service = RVDroidService(task.static_data, config=self.component_config)

            # Prepare UIAutomator2 server setup
            logger.info("Starting UIAutomator2 server")

            # Start UIAutomator2 server and initialize
            start_server_cmd = Command("adb", [
                "shell",
                "am",
                "instrument",
                "-w",
                "io.appium.uiautomator2.server.test/androidx.test.runner.AndroidJUnitRunner"
            ])
            start_server_cmd.invoke()

            # Execute RVDroid test with UIAutomator2
            with open(task.result.trace_file, "wb") as trace:
                exec_cmd = Command("python", [
                    "-m", "rvandroid.rvdroid.runner",
                    "--app", app.path,
                    "--package", app.package_name,
                    "--device", task.config.device_id,
                    "--timeout", str(task.config.timeout),
                    "--output", os.path.dirname(task.result.trace_file),
                    "--llm" if self.config["use_llm"] else ""
                ], task.config.timeout)

                exec_cmd.invoke(stdout=trace)

            # Process results and generate coverage information
            service.process_results(task.result.trace_file)

            # Cleanup resources
            service.cleanup()

            logger.info("RVDroid execution completed successfully")

        except Exception as e:
            logger.error(f"Error running RVDroid tool: {e}", exc_info=True)
            raise
        finally:
            # Publish tool end event
            event_bus.publish_task_event(
                EventType.TOOL_STOPPED,
                task_id=task.id,
                details={"tool": "rvdroid"},
                source="RVDroidTool"
            )

            # Ensure UIAutomator2 server is stopped
            try:
                stop_server_cmd = Command("adb", [
                    "shell",
                    "am",
                    "force-stop",
                    "io.appium.uiautomator2.server"
                ])
                stop_server_cmd.invoke()
            except Exception as e:
                logger.warning(f"Error stopping UIAutomator2 server: {e}")
