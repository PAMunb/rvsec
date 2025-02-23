from ... import constants, utils
from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.server import Server
import logging as logging_api
from ..tool_spec import AbstractTool


# TODO run humanoid container before using this tool
# docker run -d -p 50405:50405 phtcosta/humanoid:1.0

logging = logging_api.getLogger(__name__)

class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("rvandroid", """rv-android""", "br.unb.cic.rvsec")

    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        server = Server(port=5000)
        humanoid_url = ""
        try:
            if server.start():
                logging.info("Server started successfully")
                with open(log_file, "wb") as trace:
                    exec_cmd = Command("droidbot", [
                        "-d",
                        "emulator-5554",
                        "-a",
                        app.path,
                        "-humanoid",
                        humanoid_url,
                        "-policy",
                        "dfs_greedy",
                        "-is_emulator",
                    ], timeout)
                    exec_cmd.invoke(stdout=trace)   
            else:
                logging.error("Server failed to start")
        finally:
            logging.info("Stopping server")
            server.stop()
        
        rvandroid_url = utils.get_env_or_default(constants.ENV_HUMANOID_URL, "127.0.0.1:50405")
        with open(log_file, "wb") as trace:
            exec_cmd = Command("droidbot", [
                "-d",
                "emulator-5554",
                "-a",
                app.path,
                "-humanoid",
                humanoid_url,
                "-policy",
                "dfs_greedy",
                "-is_emulator",
            ], timeout)
            exec_cmd.invoke(stdout=trace)
