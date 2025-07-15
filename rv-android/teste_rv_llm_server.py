# teste_run_server.py
import logging
import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvandroid-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))

# Import necessary modules after path setup
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_android_core.domain.app import App
from rvandroid_tool.llm.service.action_service import LLMActionService
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rv_llm.llm.ollama_llm import OllamaLLM
from rvandroid_tool.server import Server

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
    app_folder = screenshots_folder + "/" + apk

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

    static_analysis_parser = StaticAnalysisParser()
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    # Cria configuração LLM (sem strategy_type)
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.QWEN,
        temperature=0.2,
        max_tokens=800
    )

    # Cria configuração de prompt separada
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.BATCH_ACTION,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED
    )

    # Cria configuração da ferramenta
    tool_config = RvAndroidToolConfig(
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DEFAULT,
        llm_config=llm_config
    )

    print("\n=== Configuração do RV-Android ===")
    print(f"LLM: {llm_config.llm_type}")
    print(f"Modelo: {llm_config.model}")
    print(f"Estratégia: {prompt_config.strategy_type}")
    print(f"Parser: {tool_config.parser_type}")
    print(f"Visitor: {tool_config.visitor_type}")
    print("================================\n")

    service = LLMActionService(
        static_data=static_data,
        config=llm_config,
        app_package=package,
        tool_config=tool_config
    )

    # Inicia o servidor

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
