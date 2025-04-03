# rvandroid/tools/rvdroid/tool.py
"""
RVDroid tool implementation with configuration support.
"""
import os
import json

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.task.task_model import Task
from rvandroid.rvdroid.core.service import RVDroidService
from rvandroid.rvdroid.orchestration.lifecycle import LifecycleManager, ExecutionPhase
from rvandroid.rvdroid.orchestration.recovery import RecoveryManager, ErrorSeverity, RecoveryStrategy
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
            # Create RVDroid service with configured options
            service = RVDroidService(
                static_data=task.static_data, 
                config=self.component_config,
                device_id=task.config.device_id,
                use_llm=self.config["use_llm"],
                execution_timeout=task.config.timeout
            )

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

            # Start RVDroid testing
            with open(task.result.trace_file, "wb") as trace_file:
                # Start the app and begin testing
                if service.start_testing(app.package_name):
                    logger.info(f"Successfully started testing {app.package_name}")
                    
                    # Execute the main testing loop
                    results = service.execute_testing_loop()
                    
                    # Write results to trace file
                    import json
                    trace_file.write(json.dumps(results, default=str).encode('utf-8'))
                    
                    # Stop testing and cleanup
                    service.stop_testing()
                else:
                    logger.error(f"Failed to start testing for {app.package_name}")
                    trace_file.write(b"ERROR: Failed to start testing")

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
