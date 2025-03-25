import json
import logging
import os
import sys
from uiautomator import Device
from rvandroid.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rvandroid.app import App
from rvandroid.parser.screen.uiautomator import uiautomator_parser
from rvandroid.parser.static import static_analysis_parser

def main(static_data):
    dump = get_dump()
    parser = UIAutomator2Parser()
    screen_description = parser.parse(dump, static_data)
    print(f"screen_description: {screen_description}")


def get_dump():
    d = Device("emulator-5554")
    xml = d.dump()
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
