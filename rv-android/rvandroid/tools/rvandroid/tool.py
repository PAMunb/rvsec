import logging as logging_api

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.config.configuration import Configuration
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.task_model import Task
from rvandroid.server import Server
from rvandroid.service.llm_action_service import LLMActionService
from ..tool_spec import AbstractTool

logging = logging_api.getLogger(__name__)


class ToolSpec(AbstractTool):
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
