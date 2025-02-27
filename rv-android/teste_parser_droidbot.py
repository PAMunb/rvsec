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
# from rvandroid.llm.prompt_generator02 import PromptGenerator
import rvandroid.parser.droidbot.droidbot_state_parser as parser
import json


def read_droidbot_state(filename):
    with open(filename, 'r') as file:
        return json.load(file)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    logging.info("Starting...")
    
    apk = "cryptoapp.apk"    
    screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/"+apk
    info_file = screenshot_folder+"/002.state"
    
    # apk = "t20kdc.offlinepuzzlesolver_4.apk"    
    # screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/"+apk
    # info_file = screenshot_folder+"/009.state"
    
    
    screen_info = read_droidbot_state(info_file)

    app = App(os.path.join(screenshot_folder, apk))
    package = app.package_name

    static_data = static_analysis_parser.read_static_analysis_files(screenshot_folder, apk, package)
    
    screen_description = parser.parse(screen_info, static_data)
    print(f"screen_description=\n{screen_description}")
