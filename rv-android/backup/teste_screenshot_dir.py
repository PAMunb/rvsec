import logging
import sys
import os
import json
from time import sleep

from rvandroid.app import App
from rvandroid.constants import EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH
from rvandroid.parser.screen.parser_factory import ParserFactory, ParserType
from rvandroid.parser.screen.visitor.model import ScreenItem
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rvandroid.parser.screen.visitor.enhanced_visitor import EnhancedTextVisitor
from rvandroid.parser.screen.visitor.visitor_factory import VisitorFactory
from rvandroid.parser.screen.droidbot.droidbot_parser import DroidBotParser
from rvandroid.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rvandroid.parser.static import static_analysis_parser


# Função auxiliar para ler estados do DroidBot
def read_droidbot_state(filename):
    print(f"read_droidbot_state: {filename}")
    with open(filename, 'r') as file:
        return json.load(file)


# Função auxiliar para ler dados XML do UIAutomator
def read_uiautomator_xml(filename):
    print(f"read_uiautomator_xml: {filename}")
    with open(filename, 'r') as file:
        return file.read()


class ScreenInfo:
    def __init__(self, number, base_dir):
        self.number = number
        self.screenshot = os.path.join(base_dir, f"{number}.png")
        self.droidbot_state = os.path.join(base_dir, f"{number}.state")
        self.uiautomator_dump = os.path.join(base_dir, f"{number}.uiautomator.xml")
        self.__validate()
        self.activity = read_droidbot_state(self.droidbot_state)["activity"].replace("/", "")
        print(f"Activity: {self.activity}")

    def __validate(self):
        if not os.path.exists(self.screenshot):
            raise FileNotFoundError(f"Screenshot not found: {self.screenshot}")
        if not os.path.exists(self.droidbot_state):
            raise FileNotFoundError(f"DroidBot state not found: {self.droidbot_state}")
        if not os.path.exists(self.uiautomator_dump):
            raise FileNotFoundError(f"UIAutomator dump not found: {self.uiautomator_dump}")


class Application:
    def __init__(self, apk, screenshot_folder):
        self.apk = apk
        self.base_dir = os.path.join(screenshot_folder, apk)
        self.apk_path = os.path.join(self.base_dir, apk)
        self.app = App(self.apk_path)
        self.package_name = self.app.package_name
        self.gesda_file = os.path.join(self.base_dir, apk+EXTENSION_GESDA)
        self.gator_file = os.path.join(self.base_dir, apk+EXTENSION_GATOR)
        self.reach_file = os.path.join(self.base_dir, apk+EXTENSION_REACH)
        self.screens = self.__get_screens()
        self.__validate()

    def __get_screens(self):
        screens = []
        for file in os.listdir(self.base_dir):
            if file.endswith('.png'):
                number = os.path.splitext(file)[0]
                screens.append(ScreenInfo(number, self.base_dir))
        return sorted(screens, key=lambda screen: screen.number)

    def __validate(self):
        if not os.path.exists(self.apk_path):
            raise FileNotFoundError(f"APK not found: {self.apk_path}")
        if not os.path.exists(self.gesda_file):
            raise FileNotFoundError(f"GESDA file not found: {self.gesda_file}")
        if not os.path.exists(self.gator_file):
            raise FileNotFoundError(f"GATOR file not found: {self.gator_file}")
        if not os.path.exists(self.reach_file):
            raise FileNotFoundError(f"REACH file not found: {self.reach_file}")


class ScreenshotManager:
    def __init__(self, screenshot_folder):
        self.screenshot_folder = screenshot_folder
        self.applications = self.__get_applications()

    def __get_applications(self):
        applications = []
        for apk in os.listdir(self.screenshot_folder):
            if apk.endswith('.apk'):
                app = Application(apk, self.screenshot_folder)
                applications.append(app)
        return sorted(applications, key=lambda app: app.apk)


def tmp_001(screenshot_folder):
    manager = ScreenshotManager(screenshot_folder)
    for app in manager.applications:
        logging.info(f"\nAPK: {app.apk}")
        static_data = static_analysis_parser.read_static_analysis_files(app.base_dir, app.apk, app.package_name)
        for screen in app.screens:
            # logging.info(f"\n  Screen: {screen.number}, screenshot: {screen.screenshot}")
            logging.info(f"\n  Screen: {screen.number}, activity: {screen.activity}")
            doirdbot_state = read_droidbot_state(screen.droidbot_state)
            uiautomator_dump = read_uiautomator_xml(screen.uiautomator_dump)

            print("   - DroidBot:")
            print(ParserFactory.create(ParserType.DROIDBOT, BasicTextVisitor).parse(doirdbot_state, static_data))
            print("   - Uiautomator:")
            print(ParserFactory.create(ParserType.UIAUTOMATOR, BasicTextVisitor).parse(uiautomator_dump, static_data, activity=screen.activity))
            # sleep(1)
            input("Pressione Enter para continuar...")


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    logging.info("Iniciando exemplos de parsers...")

    # Definir caminhos para os arquivos
    screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"

    tmp_001(screenshot_folder)
