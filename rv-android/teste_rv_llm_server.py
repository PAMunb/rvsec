#!/usr/bin/env python3
"""
Manual test for RVAndroid LLM server functionality.

This script tests the LLM Action Service and HTTP server components
for standalone testing without the full experiment framework.
"""

import logging
import os
import sys
import time
from pathlib import Path

# Setup paths following teste_rv_experiment.py pattern
current_directory = os.getcwd()
parent_directory = os.path.dirname(current_directory)

# Add the modules to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvandroid-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))

# Import constants and set RVSEC_HOME
from rv_android_core import constants
os.environ[constants.ENV_RVSEC_HOME] = parent_directory

# Import necessary modules after path setup
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_android_core.domain.app import App
from rvandroid_tool.llm.service.action_service import LLMActionService
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rv_llm.llm.ollama_llm import OllamaLLM
from rvandroid_tool.server.server import Server

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

    app = App(app_path=os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

    static_analysis_parser = StaticAnalysisParser()
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    # Cria configuração unificada usando RvAndroidToolConfig
    tool_config = RvAndroidToolConfig.create_from_variant({
        "llm_type": LLMType.OLLAMA,
        "llm_model": OllamaLLM.GEMMA,
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 500,
        "vision": True,
        "prompt_strategy": PromptStrategyType.STANDARD,
        "parser_type": ScreenParserType.DROIDBOT,
        "visitor_type": VisitorType.DEFAULT,
        "server_port": 5000,
        "debug_mode": True
    })

    print("\n=== Configuração do RV-Android ===")
    print(f"LLM: {tool_config.llm_config.llm_type}")
    print(f"Modelo: {tool_config.llm_config.model}")
    print(f"Estratégia: {tool_config.prompt_config.strategy_type}")
    print(f"Parser: {tool_config.prompt_config.parser_type}")
    print(f"Visitor: {tool_config.prompt_config.visitor_type}")
    print("================================\n")

    service = LLMActionService(
        static_data=static_data,
        tool_config=tool_config,
        app_package=package
    )

    # Inicia o servidor
    print("Starting RVAndroid HTTP server...")
    server = Server(service, port=5000)
    try:
        server.start()
        print("Server started successfully on port 5000")
        print("Press Ctrl+C to stop the server")
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if server.is_running():
            server.stop()
        print("Server stopped.")
