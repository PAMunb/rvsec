import logging
import os
import sys
from typing import Type

# Fixed imports - using new module structure
from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_screen_parser.constants import ScreenParserType
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rv_screen_parser.parser.screen.visitor.enhanced_visitor import EnhancedTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

def read_file(filename: str):
    with open(filename, 'r') as file:
        return file.read()

def main(dump_file: str, static_data: StaticAnalysisData, visitor: Type[AbstractScreenVisitor], activity: str):
    screen_info = read_file(dump_file)
    parser = ParserFactory.create(ScreenParserType.UIAUTOMATOR, visitor)

    # Pass both hierarchy and activity in state_data
    state_data = {
        "hierarchy": screen_info,
        "activity": activity
    }

    screen_description: ScreenDescription = parser.parse_screen(state_data, static_data)
    print("\n" + "="*80)
    print("UIAUTOMATOR PARSER OUTPUT:")
    print("="*80)
    print(screen_description)
    print("="*80)
    return screen_description

def show_screen_description(s: ScreenDescription):
    print(f"Activity: {s.activity}")
    for item in s.items:
        print(f"   - : {item}")
        for action in item.actions:
            print(f"      - {action}")

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    logging.info("Starting...")

    apk = "cryptoapp.apk"
    prefix = "001"
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"

    app_folder = os.path.join(screenshots_folder, apk)
    apk_path = os.path.join(app_folder, apk)
    reach_file = os.path.join(app_folder, apk + ".reach")
    gator_file = os.path.join(app_folder, apk + ".wtg")
    gesda_file = os.path.join(app_folder, apk + ".gesda")
    screenshot_path = os.path.join(app_folder, prefix + ".png")
    dump_file = os.path.join(app_folder, prefix + ".uiautomator")

    print(f"📂 Test files:")
    print(f"  • APK: {apk}")
    print(f"  • State: {prefix}")
    print(f"  • Screenshot: {screenshot_path}")

    # Get package name using App class
    app = App(app_path=apk_path)
    package = app.package_name
    print(f"  • Package: {package}")

    print("\n📊 Parsing static analysis data...")
    static_analysis_parser = StaticAnalysisParser()
    static_data = static_analysis_parser.parse(reach_file, gator_file, gesda_file, package)
    print(f"  ✅ Static data parsed")

    # Get activity name from DroidBot state file for comparison
    import json
    state_file = os.path.join(app_folder, prefix + ".state")
    with open(state_file, 'r') as f:
        state = json.load(f)
    activity = state.get("activity", "")
    print(f"  • Activity from DroidBot state: {activity}")

    print("\n🔍 Testing UIAutomator parser with DefaultTextVisitor...")
    main(dump_file, static_data, DefaultTextVisitor, activity)
