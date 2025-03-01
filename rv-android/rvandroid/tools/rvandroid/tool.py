import logging as logging_api

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.server import Server
from ..tool_spec import AbstractTool
from ... import constants, utils

logging = logging_api.getLogger(__name__)


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("rvandroid", """rv-android""", "br.unb.cic.rvsec")

    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        # TODO precisa do service aqui .....
        service = None
        server = Server(service, port=5000)
        rvandroid_url = ""
        try:
            if server.start():
                logging.info("Server started successfully")
                with open(log_file, "wb") as trace:
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
                    ], timeout)
                    exec_cmd.invoke(stdout=trace)
            else:
                logging.error("Server failed to start")
        finally:
            logging.info("Stopping server")
            server.stop()

