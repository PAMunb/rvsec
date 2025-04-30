# teste_run_server.py
import json
import logging
import os
import sys

from rvandroid.analysis.patterns.ui_pattern_detector import UIPatternDetectorManager
from rvandroid.app import App
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.parser_factory import ParserType, ParserFactory
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.parser.static import static_analysis_parser
from rvandroid.analysis.screenshot.screenshot_action_complementor import ScreenshotActionComplementor

def read_state_file(filename):
    print(f"Lendo arquivo de estado: {filename}")
    with open(filename, 'r') as file:
        return json.load(file)


def tmp_001(screen_description: ScreenDescription, static_data: StaticAnalysisData):
    manager = UIPatternDetectorManager(static_data)
    resposta = manager.detect_patterns(screen_description, {})
    print(resposta)


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
    screenshot_file = os.path.join(app_folder, prefix+".png")
    droidbot_state_file = os.path.join(app_folder, prefix + ".state")
    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    droidbot_state = read_state_file(droidbot_state_file)
    parser = ParserFactory.create(ParserType.DROIDBOT, BasicTextVisitor)
    screen_description = parser.parse(droidbot_state, static_data)
    # print(screen_description)

    tmp_001(screen_description, static_data)
