import logging as logging_api

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.config.component_config import ComponentConfig
from rvandroid.experiment.task import Task
from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
from rvandroid.parser.screen.visitor.text_visitor import EnhancedTextVisitor
from rvandroid.server import Server
from rvandroid.service.llm_action_service import LLMActionService
from settings import RVANDROID_URL
from ..tool_spec import AbstractTool

logging = logging_api.getLogger(__name__)


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("rvandroid", """rv-android""", "br.unb.cic.rvsec")

    def execute_tool_specific_logic(self, task: Task, app: App):
        rvandroid_url = RVANDROID_URL

        # TODO arrumar a configuracao
        config = ComponentConfig()
        config.set_strategy(BasicPromptStrategy001)
        config.set_visitor(EnhancedTextVisitor)

        service = LLMActionService(task.tracker.static_data, component_config=config)

        server = Server(service, port=5000)
        try:
            if server.start():
                logging.info("Server started successfully")
                with open(task.log_file, "wb") as trace:
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
                    ], task.timeout)
                    exec_cmd.invoke(stdout=trace)
            else:
                logging.error("Server failed to start")
        finally:
            logging.info("Stopping server")
            server.stop()
