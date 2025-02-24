import logging
import sys

from rvandroid.parser.droidbot import droidbot_state_parser as state_parser

import logging
import sys

from rvandroid.parser.static import reach_parser
import logging
import os
import sys

from rvandroid.app import App
from rvandroid.parser.static import static_analysis_parser
from rvandroid.model.classes import Classes
from rvandroid.model.window import Windows
# from rvandroid.llm.prompt_generator import PromptGenerator
from rvandroid.llm.prompt_generator02 import PromptGenerator
# from rvandroid.parser.droidbot.state_parser import StateParser
import rvandroid.parser.droidbot.droidbot_state_parser_novo as parser
import json


def read_droidbot_state(filename):
    with open(filename, 'r') as file:
        return json.load(file)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    logging.info("Starting...")
    
    static_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static"
    apk = "cryptoapp.apk"    
    screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk"
    info_file = screenshot_folder+"/001.state"
    screen_info = read_droidbot_state(info_file)
    
    windows = Windows()
    classes = Classes()
    app = App(os.path.join(static_folder, apk))
    package = app.package_name
    
        
    static_data = static_analysis_parser.read_static_analysis_files(static_folder, apk, package)
    
    screen_description = parser.parse(screen_info, static_data)
    print(f"screen_description={screen_description}")
