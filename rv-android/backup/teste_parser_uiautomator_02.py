import logging
import os
import sys

from uiautomator import Device

from rvandroid.app import App
from rvandroid.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription
from rvandroid.parser.screen.visitor.enhanced_visitor import EnhancedTextVisitor
from rvandroid.parser.screen.visitor.generic_visitor import GenericScreenVisitor
from rvandroid.parser.screen.visitor.text_visitor import TextVisitor
from rvandroid.parser.static import static_analysis_parser
import uiautomator2 as u2

def main(static_data):
    print("Executing ...")
    dump = get_dump()
    # exit(-1)
    # parser = UIAutomator2Parser(TextVisitor)
    parser = UIAutomator2Parser(GenericScreenVisitor)
    screen_description = parser.parse(dump, static_data)
    # show_screen_description(screen_description)
    print(f"screen_description:\nactivity:{screen_description.activity}\n{screen_description}")

def show_screen_description(s: ScreenDescription):
    print(f"Activity: {s.activity}")
    for item in s.items:
        print(f"   - : {item}")
        for action in item.actions:
            print(f"      - {action}")


def get_dump():
    d = u2.connect("emulator-5554")
    xml = d.dump_hierarchy()
    # d = Device("emulator-5554")
    # xml = d.dump()
    print(xml)
    return xml


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    logging.info("Starting...")

    apk = "cryptoapp.apk"
    screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk"
    app = App(os.path.join(screenshot_folder, apk))
    package = app.package_name

    static_data = static_analysis_parser.read_static_analysis_files(screenshot_folder, apk, package)

    main(static_data)
