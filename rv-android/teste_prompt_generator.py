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
from rvandroid.llm.prompt_generator import PromptGenerator
import rvandroid.parser.droidbot.droidbot_state_parser_novo as state_parser

import json

def read_json_to_dict(filename):
    with open(filename, 'r') as file:
        return json.load(file)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    
    logging.info("Starting...")
    static_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static"
    apk = "cryptoapp.apk"    
    # apk = "byrne.utilities.hashpass_2.apk" 
    # apk = "ca.farrelltonsolar.classic_314.apk" 
    # apk = "com.example.openpass_1.apk" 
    # apk = "com.gianlu.dnshero_40.apk"
    screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk"
    info_file = screenshot_folder+"/001.state"
    screen_info = read_json_to_dict(info_file)
    
    windows = Windows()
    classes = Classes()
    app = App(os.path.join(screenshot_folder, apk))
    package = app.package_name
        
    static_data = static_analysis_parser.read_static_analysis_files(screenshot_folder, apk, package)

    screen_description = state_parser.parse(screen_info, static_data)

    print(screen_description)
    
    prompt_generator = PromptGenerator(static_data)

    system_prompt = prompt_generator.generate_system_prompt()
    user_prompt = prompt_generator.generate_user_prompt(screen_info)

    print(f"System prompt: {system_prompt}")
    print(f"\n\nUser prompt: {user_prompt}")
    
