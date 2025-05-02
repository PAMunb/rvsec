import json
import logging
import os
import sys
from typing import Dict, Any

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import PromptStrategyType, ScreenParserType, VisitorType
from rvandroid.llm.frontier_models import FrontierModel
from rvandroid.llm.huggingface_llm import HuggingFaceLLM
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.parser.static import static_analysis_parser


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


if __name__ == '__main__':
    # Configuração de logging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)

    # Caminhos para dados do app
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "001"
    app_folder = screenshots_folder + "/" + apk
    droidbot_state_file = os.path.join(app_folder, f"{prefix}.state")
    srceenshot_file = os.path.join(app_folder, f"{prefix}.png")

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    # Inicializa o configurador
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=OllamaLLM.NAME,
        model=OllamaLLM.GEMMA,
        base_url="http://127.0.0.1:11434"
    )
    configurator.set_strategy(PromptStrategyType.BATCH_ACTION)
    configurator.set_parser(ScreenParserType.DROIDBOT)
    configurator.set_visitor(VisitorType.DEFAULT)

    # Mostra a configuração
    config = configurator.describe_configuration()
    print("\n=== Configuração do RV-Android ===")
    print(f"LLM: {config['llm']['type']}")
    print(f"Modelo: {config['llm']['model']}")
    print(f"Estratégia: {config['strategy']}")
    print(f"Parser: {config['parser']}")
    print(f"Visitor: {config['visitor']}")
    print("================================\n")

    # Cria o serviço
    service = LLMActionService(static_data, configurator)

    state = read_droidbot_state(droidbot_state_file)
    actions = service.process_state(state)
    print(f"\nActions: {actions}")
