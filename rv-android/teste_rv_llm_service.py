import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvandroid-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))

# Import necessary modules after path setup
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.app import App
from rvandroid_tool.llm.service.action_service import LLMActionService
from rvandroid_tool.config.tool_config import RvAndroidToolConfig


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


def tmp_001(service, state):
    actions = service.process_state(state)
    print(f"\n*** Actions: {len(actions)}")
    for action in actions:
        print(f"   - {action}")
        for key in action.keys():
            print(f"      {key}: {action[key]}")

def tmp_002(service, state):
    while True:
        input("Press Enter to continue...")
        tmp_001(service, state)


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
    prefix = "009"
    app_folder = screenshots_folder + "/" + apk
    droidbot_state_file = os.path.join(app_folder, f"{prefix}.state")
    srceenshot_file = os.path.join(app_folder, f"{prefix}.png")

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
    static_analysis_parser = StaticAnalysisParser()
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    # Cria configuração LLM (sem strategy_type)
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.QWEN,  # Using string instead of OllamaLLM.QWEN
        temperature=0.2,
        max_tokens=1200
    )

    # Cria configuração de prompt separada
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.BATCH_ACTION,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED
    )

    # Cria configuração da ferramenta
    tool_config = RvAndroidToolConfig(
        prompt_config=prompt_config,
        llm_config=llm_config
    )

    print("\n=== Configuração do RV-Android ===")
    print(f"LLM: {llm_config.llm_type}")
    print(f"Modelo: {llm_config.model}")
    print(f"Estratégia: {prompt_config.strategy_type}")
    print(f"Parser: {prompt_config.parser_type}")
    print(f"Visitor: {prompt_config.visitor_type}")
    print("================================\n")

    # Cria o serviço (com nova assinatura)
    service = LLMActionService(
        static_data=static_data,
        tool_config=tool_config
    )

    state = read_droidbot_state(droidbot_state_file)

    tmp_001(service, state)
    # tmp_002(service, state)

    # print(f"state_processing_total={PerformanceMonitor.get_instance().get_metrics_by_name("state_processing_total")}")
    # print(f"response_total_duration={PerformanceMonitor.get_instance().get_metrics_by_name("response_total_duration")}")
    # print(f"response_load_duration={PerformanceMonitor.get_instance().get_metrics_by_name("response_load_duration")}")
    # print(f"response_total_duration={PerformanceMonitor.get_instance().get_metrics_stats("response_total_duration")}")
