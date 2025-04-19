import json
import logging
import os
import sys

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import LLMType, PromptStrategyType, ScreenParserType, VisitorType
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.parser.static import static_analysis_parser
from ollama import Client

def read_droidbot_state(filename):
    with open(filename, 'r') as file:
        return json.load(file)


def tmp_simple():
    client = Client(host="http://192.168.0.18:11434")

    # Prepare options from config
    options = {}
    options["temperature"] = 0.2
    options["num_predict"] = 200

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of Brazil?"}
    ]

    # Call Ollama chat API synchronously
    response = client.chat(
        model=OllamaLLM.LLAMA,
        messages=messages,
        options=options
    )

    print(f"response={response}")
    print(f"*** Response: {response['message']['content']}")


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)
    # rvandroid.parser.static.gesda_parser
    logging.info("Starting...")

    # tmp_simple()
    # exit(1)

    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    app_folder = screenshots_folder + "/" + apk
    info_file = app_folder + "/001.state"

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)
    screen_info = read_droidbot_state(info_file)

    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.LLAMA,
        base_url="http://192.168.0.18:11434"
    )
    configurator.set_strategy(PromptStrategyType.STANDARD)
    configurator.set_parser(ScreenParserType.DROIDBOT)
    configurator.set_visitor(VisitorType.BASIC)

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
