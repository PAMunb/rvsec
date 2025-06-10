# teste_ui_pattern_detector.py
import json
import logging
import os

from rvandroid.analysis.patterns.pattern_detector import UIPatternDetectorManager
from rvandroid.app import App
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.parser_factory import ParserType, ParserFactory
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.parser.static import static_analysis_parser
from rvandroid.util.logging.manager import LoggingManager


def read_state_file(filename):
    """Lê o arquivo de estado do Droidbot."""
    print(f"Lendo arquivo de estado: {filename}")
    with open(filename, 'r') as file:
        return json.load(file)


def analyze_screen_patterns(screen_description: ScreenDescription, static_data: StaticAnalysisData):
    """
    Analisa os padrões de UI na descrição da tela.

    Args:
        screen_description (ScreenDescription): Descrição da tela a ser analisada
        static_data (StaticAnalysisData): Dados da análise estática
    """
    # Cria o gerenciador de detecção de padrões
    pattern_detector_manager = UIPatternDetectorManager()

    # Detecta todos os padrões na tela
    pattern_results = pattern_detector_manager.detect_patterns(screen_description)

    # Imprime os resultados dos padrões detectados
    print("\n--- Padrões Detectados ---")
    for pattern_type, pattern_result in pattern_results.items():
        print(f"\nTipo de Padrão: {pattern_type.value}")
        print(f"Confiança: {pattern_result.confidence:.2f}")
        print(f"Número de Elementos: {pattern_result.elements_count}")
        print("Propriedades:", pattern_result.properties)

    # Obtém o padrão dominante, se houver
    dominant_pattern = pattern_detector_manager.get_dominant_pattern(screen_description)
    if dominant_pattern:
        print("\n--- Padrão Dominante ---")
        pattern_type, pattern_result = dominant_pattern
        print(f"Tipo: {pattern_type.value}")
        print(f"Confiança: {pattern_result.confidence:.2f}")


def tmp_001(screen_description: ScreenDescription, static_data: StaticAnalysisData):
    """
    Função temporária para teste de detecção de padrões.

    Args:
        screen_description (ScreenDescription): Descrição da tela a ser analisada
        static_data (StaticAnalysisData): Dados da análise estática
    """
    analyze_screen_patterns(screen_description, static_data)


if __name__ == '__main__':
    # Configuração de logging
    LoggingManager.get_instance().configure_output(console_level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.classes.Classes").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Windows").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.widget.Widget").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.static.reach").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.static.gator").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.static.gesda").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.util.utils").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.static.static_analysis_parser.read_static_analysis_files").setLevel(
        logging.WARNING)

    # Caminhos para dados do app
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "009"
    app_folder = os.path.join(screenshots_folder, apk)
    screenshot_file = os.path.join(app_folder, prefix + ".png")
    droidbot_state_file = os.path.join(app_folder, prefix + ".state")

    # Cria objeto App
    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    # Lê o estado do Droidbot
    droidbot_state = read_state_file(droidbot_state_file)

    # Cria o parser
    parser = ParserFactory.create(ParserType.DROIDBOT, BasicTextVisitor)

    # Analisa o estado e gera a descrição da tela
    screen_description = parser.parse(droidbot_state, static_data)

    # Chama a função de teste
    tmp_001(screen_description, static_data)
