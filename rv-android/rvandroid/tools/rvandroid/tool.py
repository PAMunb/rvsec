import logging as logging_api

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.config.configuration import Configuration
from rvandroid.experiment.task_model import Task
from rvandroid.server import Server
from rvandroid.service.llm_action_service import LLMActionService
from ..tool_spec import AbstractTool

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

        # Create component configurator
        component_config = ComponentConfigurator(task.static_data)
        component_config.set_strategy("basic")
        component_config.set_visitor("enhanced")

        # Create service
        service = LLMActionService(task.static_data, config=component_config)

        # Start server and run experiment
        server = Server(service, port=5000)
        try:
            if server.start():
                logging.info("Server started successfully")
                with open(task.result.trace_file, "wb") as trace:
                    exec_cmd = Command("droidbot", [
                        "-d",
                        "emulator-5554",
                        "-a",
                        app.path,
                        "--rvandroid_url",
                        rvandroid_url,
                        "-policy",
                        "rvandroid",
                        "-is_emulator",
                    ], task.config.timeout)
                    exec_cmd.invoke(stdout=trace)
            else:
                logging.error("Server failed to start")
        finally:
            logging.info("Stopping server")
            server.stop()
