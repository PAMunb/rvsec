import json
import logging
import os
import sys

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.parser.screen.droidbot.droidbot_parser import DroidBotParser
from rvandroid.parser.screen.visitor.text_visitor import EnhancedTextVisitor
from rvandroid.parser.static import static_analysis_parser


def read_droidbot_state(filename):
    with open(filename, 'r') as file:
        return json.load(file)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)
    # rvandroid.parser.static.gesda_parser
    logging.info("Starting...")

    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    app_folder = screenshots_folder + "/" + apk
    info_file = app_folder + "/001.state"

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)
    screen_info = read_droidbot_state(info_file)

    # TODO agrupar tudo no component config
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=OllamaLLM.NAME,
        model=OllamaLLM.GEMMA,
        base_url="http://localhost:11434"
    )
    configurator.set_strategy("single_action")
    configurator.set_parser("droidbot")
    configurator.set_visitor("enhanced")

    config = configurator.describe_configuration()
    print("\n=== Configuração do RV-Android ===")
    print(f"LLM: {config['llm']['type']}")
    print(f"Modelo: {config['llm']['model']}")
    print(f"Estratégia: {config['strategy']}")
    print(f"Parser: {config['parser']}")
    print(f"Visitor: {config['visitor']}")
    print("================================\n")

    service = LLMActionService(static_data, configurator)

    actions = service.process_state(screen_info)
    print(f"actions={actions}")
