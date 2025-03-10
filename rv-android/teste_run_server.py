import json
import logging
import os
import sys
import time

from rvandroid.app import App
from rvandroid.config.component_config import ComponentConfig
from rvandroid.llm.huggingface_llm import HuggingFaceLLM
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
from rvandroid.parser.screen.droidbot.droidbot_parser import DroidBotParser
from rvandroid.parser.screen.visitor.text_visitor import EnhancedTextVisitor
from rvandroid.parser.static import static_analysis_parser
from rvandroid.server import Server
from rvandroid.service.llm_action_service import LLMActionService


def read_droidbot_state(filename):
    with open(filename, 'r') as file:
        return json.load(file)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)
#rvandroid.parser.static.gesda_parser
    logging.info("Starting...")

    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    app_folder = screenshots_folder + "/" + apk

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    # TODO agrupar tudo no component config
    config = ComponentConfig()
    config.set_strategy(BasicPromptStrategy001)
    config.set_visitor(EnhancedTextVisitor)
    config.set_parser(DroidBotParser)
    model_type = OllamaLLM.NAME
    model_name = OllamaLLM.LLAMA
    ollama_url = "http://192.168.0.18:11434"

    service = LLMActionService(static_data,
                               model_type=model_type,
                               model_name=model_name,
                               component_config=config,
                               base_url=ollama_url)

    server = Server(service)
    try:
        if server.start():
            print("Server started successfully")
            while True:
                time.sleep(5)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.stop()

    print("Server started")
